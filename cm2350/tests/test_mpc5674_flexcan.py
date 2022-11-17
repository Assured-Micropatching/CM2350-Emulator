import gc
import os
import time
import random
import struct
import unittest

from .. import intc_exc
from ..peripherals import flexcan
from ..ppc_peripherals import ExternalIOClient

from .helpers import MPC5674_Test

import logging
logger = logging.getLogger(__name__)


FLEXCAN_DEVICES = (
    ('FlexCAN_A', 0XFFFC0000),
    ('FlexCAN_B', 0XFFFC4000),
    ('FlexCAN_C', 0XFFFC8000),
    ('FlexCAN_D', 0XFFFCC000),
)

FLEXCAN_MCR_OFFSET          = 0x0000
FLEXCAN_CTRL_OFFSET         = 0x0004
FLEXCAN_TIMER_OFFSET        = 0x0008
FLEXCAN_RXGMASK_OFFSET      = 0x0010
FLEXCAN_RX14MASK_OFFSET     = 0x0014
FLEXCAN_RX15MASK_OFFSET     = 0x0018
FLEXCAN_ECR_OFFSET          = 0x001C
FLEXCAN_ESR_OFFSET          = 0x0020
FLEXCAN_IMASK2_OFFSET       = 0x0024
FLEXCAN_IMASK1_OFFSET       = 0x0028
FLEXCAN_IFLAG2_OFFSET       = 0x002C
FLEXCAN_IFLAG1_OFFSET       = 0x0030
FLEXCAN_MB_OFFSET           = 0x0080
FLEXCAN_RXIMR_OFFSET        = 0x0880

# Number of
FLEXCAN_NUM_MBs             = 64

# Size of each MBx region and RXIMRx entry in bytes
FLEXCAN_MBx_SIZE            = 16
FLEXCAN_RXIMRx_SIZE         = 4

# The entire MB and RXIMR register range
FLEXCAN_MB_REGION_SIZE      = FLEXCAN_MBx_SIZE * FLEXCAN_NUM_MBs
FLEXCAN_RXIMR_REGION_SIZE   = FLEXCAN_RXIMRx_SIZE * FLEXCAN_NUM_MBs

FLEXCAN_MCR_DEFAULT         = 0x5990000F
FLEXCAN_MCR_DEFAULT_BYTES   = b'\x59\x90\x00\x0F'

# Some MCR and CTRL masks used for mode testing
FLEXCAN_MCR_MDIS_MASK       = 0x80000000
FLEXCAN_MCR_FRZ_MASK        = 0x40000000
FLEXCAN_MCR_FEN_MASK        = 0x20000000
FLEXCAN_MCR_HALT_MASK       = 0x10000000
FLEXCAN_MCR_SRX_DIS_MASK    = 0x00020000
FLEXCAN_MCR_MBFEN_MASK      = 0x00010000
FLEXCAN_MCR_IDAM_MASK       = 0x00000300
FLEXCAN_MCR_MAXMB_MASK      = 0x0000003F

FLEXCAN_CTRL_LPB_MASK       = 0x00001000
FLEXCAN_CTRL_LOM_MASK       = 0x00000008

# Some CTRL masks and shifts used for buadrate/speed testing
FLEXCAN_CTRL_PRESDIV_MASK   = 0xFF000000
FLEXCAN_CTRL_PSEG1_MASK     = 0x00380000
FLEXCAN_CTRL_PSEG2_MASK     = 0x00070000
FLEXCAN_CTRL_CLK_SRC_MASK   = 0x00002000
FLEXCAN_CTRL_PROPSEG_MASK   = 0x00000007

FLEXCAN_CTRL_PRESDIV_SHIFT  = 24
FLEXCAN_CTRL_PSEG1_SHIFT    = 19
FLEXCAN_CTRL_PSEG2_SHIFT    = 16
FLEXCAN_CTRL_CLK_SRC_SHIFT  = 13
FLEXCAN_CTRL_PROPSEG_SHIFT  = 0

# Used in the actual IO test
INTC_CPR_ADDR               = 0xFFF48008
INTC_EOIR_ADDR              = 0xFFF48018
INTC_PSRn_ADDR              = 0xFFF48040


def generate_msg(ide=None, rtr=None, min_id=0):
    """
    Returns a flexcan.CanMsg object with randomly generated ID, length and
    data contents. By default the IDE and RTR flags are also randomly
    generated, but specific values for generated messages can be specified
    with parameters.

    The flexcan.CanMsg type provides an easier to manipulate and manage object
    for sending python CAN messages across network connections.

    Parameters:
        ide (int): Flag indicating if a messages should be a standard or
                   extended CAN message.  0 == 11-bit ID, 1 == 29-bit ID
        rtr (int): Flag indicating if a messages is a remote frame or not.

    Return:
        flexcan.CanMsg object
    """
    if ide is None:
        ide = random.randrange(2)

    if rtr is None:
        rtr = random.randrange(2)

    if ide:
        arbid = random.randrange(min_id, 0x20000000)
    else:
        arbid = random.randrange(min_id, 0x800)

    length = random.randrange(9)
    data = os.urandom(length)
    return flexcan.CanMsg(rtr, ide, arbid, length, data)


def get_int_src(dev, mb):
    """
    Calculate the correct external interrupt source for a mailbox.  These
    values are from
    "Table 9-8. Interrupt Request Sources" (MPC5674FRM.pdf page 325-341)
      CANA_MB0 = 155
      CANC_MB0 = 176
      CANB_MB0 = 283
      CAND_MB0 = 311

    mailboxes 0-15 have individual interrupt sources, mailboxes 16-31 have
    a common source, and mailboxes 32-63 have a common source.

    Parameters:
        dev (int): indicating FlexCAN A (0) to D (3)
        mb  (int): the mailbox to return the interrupt source for

    Return:
        interrupt source value (int)
    """
    base = (155, 283, 176, 311)[dev]
    if mb < 16:
        src = base + mb
    elif mb < 32:
        src = base + 16
    else:
        src = base + 17

    return src


def get_int(dev, mb):
    """
    Returns an ExternalException object that corresponds to a queued exception
    associated with a specific CAN mailbox.

    Parameters:
        dev (int): indicating FlexCAN A (0) to D (3)
        mb  (int): the mailbox to return the interrupt source for

    Return:
        interrupt source value (int)
    """
    return intc_exc.ExternalException(intc_exc.INTC_SRC(get_int_src(dev, mb)))


def write_mb_data(emu, dev, mb, data):
    """
    Write data into a mailbox in 1, 2 or 4 byte chunks.

    Parameters:
        dev       (int): indicating FlexCAN A (0) to D (3)
        mb        (int): the mailbox to return the interrupt source for
        data (16 bytes): the mailbox to return the interrupt source for
    """
    baseaddr = FLEXCAN_DEVICES[dev][1]
    start = baseaddr + FLEXCAN_MB_OFFSET + (mb * FLEXCAN_MBx_SIZE)
    stop = start + FLEXCAN_MBx_SIZE

    # Randomize how this data is written to the mailbox registers,
    # it can be written in 1, 2 or 4 byte chunks.
    size = random.choice((1, 2, 4))

    data_chunks = [data[i:i+size] for i in range(0, FLEXCAN_MBx_SIZE, size)]
    for addr, chunk in zip(range(start, stop, size), data_chunks):
        emu.writeMemory(addr, chunk)


def read_mb_data(emu, dev, mb):
    """
    Read  data from a mailbox in 1, 2 or 4 byte chunks.

    Parameters:
        dev       (int): indicating FlexCAN A (0) to D (3)
        mb        (int): the mailbox to return the interrupt source for

    Return:
        16 bytes of data
    """
    baseaddr = FLEXCAN_DEVICES[dev][1]
    start = baseaddr + FLEXCAN_MB_OFFSET + (mb * FLEXCAN_MBx_SIZE)
    stop = start + FLEXCAN_MBx_SIZE

    # Randomize how this data is read from the mailbox registers, it
    # can be read in 1, 2 or 4 byte chunks.
    size = random.choice((1, 2, 4))
    return b''.join(emu.readMemory(a, size) for a in range(start, stop, size))


class MPC5674_FlexCAN_Test(MPC5674_Test):
    def set_sysclk_240mhz(self):
        # default pll clock based on the pcb params selected for these tests is
        # 60 mhz
        self.assertequal(self.emu.vw.config.project.mpc5674.fmpll.extal, 40000000)
        self.assertequal(self.emu.fmpll.f_pll(), 60000000.0)

        # the max clock for the real hardware is 764 mhz:
        #  (40 mhz * (50+16)) / ((4+1) * (1+1))
        #
        # but the more efficient clock speed used in actual hardware is 240 mhz
        # which allows a bus speed of 120 mhz.
        #  (40 mhz * (80+16)) / ((7+1) * (1+1))

        # esyncr1[emfd] = 80
        # esyncr1[eprediv] = 7
        self.emu.writememvalue(0xc3f80008, 0xf0070050, 4)
        # esyncr2[erfd] = 1
        self.emu.writememvalue(0xc3f8000c, 0x00000001, 4)
        self.assertequal(self.emu.fmpll.f_pll(), 240000000.0)

        # now set the siu peripheral configuration to allow the cpu frequency to
        # be double the peripheral speed (otherwise the maximum bus/peripheral
        # speed is 132 mhz

        # sysdiv[ipclkdiv] = 0
        # sysdiv[bypass] = 1
        self.emu.writememvalue(0xc3f909a0, 0x00000010, 4)
        self.assertequal(self.emu.siu.f_periph(), 120000000.0)

    def set_baudrates(self):
        # configure fmpll to an appropriately reasonable example valid baud rate
        self.set_sysclk_240mhz()

        # set each peripheral to different sclk rates so we can test that the
        # emulated timer runs at an appropriately simulated rate.
        ctrl_addrs = [a + flexcan_ctrl_offset for _, a in flexcan_devices]

        # flexcan_a: 1 mbps
        #   - sclk = 120000000 / (14+1)
        #   - tq = sclk / (1 + (1+1) + (2+1) + (1+1))
        val = (14 << flexcan_ctrl_presdiv_shift) | \
                (2 << flexcan_ctrl_pseg1_shift) | \
                (1 << flexcan_ctrl_pseg2_shift) | \
                (flexcan_ctrl_clk_src_mask) | \
                (1 << flexcan_ctrl_propseg_shift)
        self.emu.writememvalue(ctrl_addrs[0], val, 4)
        self.assertequal(self.emu.can[0].speed, 1000000)

        # flexcan_b: 500 kbps
        #   - sclk = 120000000 / (14+1)
        #   - tq = sclk / (1 + (4+1) + (7+1) + (1+1))
        val = (14 << flexcan_ctrl_presdiv_shift) | \
                (7 << flexcan_ctrl_pseg1_shift) | \
                (1 << flexcan_ctrl_pseg2_shift) | \
                (flexcan_ctrl_clk_src_mask) | \
                (4 << flexcan_ctrl_propseg_shift)
        self.emu.writememvalue(ctrl_addrs[1], val, 4)
        self.assertequal(self.emu.can[1].speed, 500000)

        #   flexcan_c: 250 kbps
        #   - sclk = 120000000 / (29+1)
        #   - tq = sclk / (1 + (4+1) + (7+1) + (1+1))
        val = (29 << flexcan_ctrl_presdiv_shift) | \
                (7 << flexcan_ctrl_pseg1_shift) | \
                (1 << flexcan_ctrl_pseg2_shift) | \
                (flexcan_ctrl_clk_src_mask) | \
                (4 << flexcan_ctrl_propseg_shift)
        self.emu.writememvalue(ctrl_addrs[2], val, 4)
        self.assertequal(self.emu.can[2].speed, 250000)

        # flexcan_d: 125 kbps
        #   - sclk = 120000000 / (59+1)
        #   - tq = sclk / (1 + (4+1) + (7+1) + (1+1))
        val = (59 << flexcan_ctrl_presdiv_shift) | \
                (7 << flexcan_ctrl_pseg1_shift) | \
                (1 << flexcan_ctrl_pseg2_shift) | \
                (flexcan_ctrl_clk_src_mask) | \
                (4 << flexcan_ctrl_propseg_shift)
        self.emu.writememvalue(ctrl_addrs[3], val, 4)
        self.assertequal(self.emu.can[3].speed, 125000)

    def test_flexcan_mcr_defaults(self):
        for idx in range(4):
            devname, baseaddr = flexcan_devices[idx]
            self.assertequal(self.emu.can[idx].devname, devname)

            addr = baseaddr + flexcan_mcr_offset

            self.assertequal(self.emu.readmemory(addr, 4), flexcan_mcr_default_bytes)
            self.assertequal(self.emu.readmemvalue(addr, 4), flexcan_mcr_default)
            self.assertequal(self.emu.can[idx].registers.mcr.mdis, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.frz, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.fen, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.halt, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.not_rdy, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.soft_rst, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.frz_ack, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.supv, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.wrn_en, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.mdisack, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.doze, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.srx_dis, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.mbfen, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.lprio_en, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.aen, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.idam, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.maxmb, 0x0f)

    def test_flexcan_ctrl_defaults(self):
        for idx in range(4):
            _, baseaddr = flexcan_devices[idx]
            addr = baseaddr + flexcan_ctrl_offset

            self.assertequal(self.emu.readmemory(addr, 4), b'\x00\x00\x00\x00')
            self.assertequal(self.emu.readmemvalue(addr, 4), 0x00000000)
            self.assertequal(self.emu.can[idx].registers.ctrl.presdiv, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.rjw, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.pseg1, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.pseg2, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.boff_msk, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.err_msk, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.clk_src, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.lpb, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.twrn_msk, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.rwrn_msk, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.smp, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.boff_rec, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.tsyn, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.lbuf, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.lom, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.propseg, 0)

    def test_flexcan_timer_defaults(self):
        test_addrs = [a + flexcan_timer_offset for _, a in flexcan_devices]
        for addr in test_addrs:
            self.assertequal(self.emu.readmemory(addr, 4), b'\x00\x00\x00\x00')
            self.assertequal(self.emu.readmemvalue(addr, 4), 0x00000000)

        # start the timer for each peripheral, ensure that the timer value has
        # changed and that none of the other can device timers moved

        # can a
        self.emu.can[0]._timer.start()
        time.sleep(0.1)
        self.assertnotequal(self.emu.readmemory(test_addrs[0], 4), b'\x00\x00\x00\x00')
        self.assertnotequal(self.emu.readmemvalue(test_addrs[0], 4), 0x00000000)

        self.assertequal(self.emu.readmemory(test_addrs[1], 4), b'\x00\x00\x00\x00')
        self.assertequal(self.emu.readmemvalue(test_addrs[1], 4), 0x00000000)
        self.assertequal(self.emu.readmemory(test_addrs[2], 4), b'\x00\x00\x00\x00')
        self.assertequal(self.emu.readmemvalue(test_addrs[2], 4), 0x00000000)
        self.assertequal(self.emu.readmemory(test_addrs[3], 4), b'\x00\x00\x00\x00')
        self.assertequal(self.emu.readmemvalue(test_addrs[3], 4), 0x00000000)

        self.emu.can[0]._timer.stop()
        self.assertequal(self.emu.readmemory(test_addrs[0], 4), b'\x00\x00\x00\x00')
        self.assertequal(self.emu.readmemvalue(test_addrs[0], 4), 0x00000000)

        # can b
        self.emu.can[1]._timer.start()
        time.sleep(0.1)
        self.assertnotequal(self.emu.readmemory(test_addrs[1], 4), b'\x00\x00\x00\x00')
        self.assertnotequal(self.emu.readmemvalue(test_addrs[1], 4), 0x00000000)

        self.assertequal(self.emu.readmemory(test_addrs[0], 4), b'\x00\x00\x00\x00')
        self.assertequal(self.emu.readmemvalue(test_addrs[0], 4), 0x00000000)
        self.assertequal(self.emu.readmemory(test_addrs[2], 4), b'\x00\x00\x00\x00')
        self.assertequal(self.emu.readmemvalue(test_addrs[2], 4), 0x00000000)
        self.assertequal(self.emu.readmemory(test_addrs[3], 4), b'\x00\x00\x00\x00')
        self.assertequal(self.emu.readmemvalue(test_addrs[3], 4), 0x00000000)

        self.emu.can[1]._timer.stop()
        self.assertequal(self.emu.readmemory(test_addrs[1], 4), b'\x00\x00\x00\x00')
        self.assertequal(self.emu.readmemvalue(test_addrs[1], 4), 0x00000000)

        # can c
        self.emu.can[2]._timer.start()
        time.sleep(0.1)
        self.assertnotequal(self.emu.readmemory(test_addrs[2], 4), b'\x00\x00\x00\x00')
        self.assertnotequal(self.emu.readmemvalue(test_addrs[2], 4), 0x00000000)

        self.assertequal(self.emu.readmemory(test_addrs[0], 4), b'\x00\x00\x00\x00')
        self.assertequal(self.emu.readmemvalue(test_addrs[0], 4), 0x00000000)
        self.assertequal(self.emu.readmemory(test_addrs[1], 4), b'\x00\x00\x00\x00')
        self.assertequal(self.emu.readmemvalue(test_addrs[1], 4), 0x00000000)
        self.assertequal(self.emu.readmemory(test_addrs[3], 4), b'\x00\x00\x00\x00')
        self.assertequal(self.emu.readmemvalue(test_addrs[3], 4), 0x00000000)

        self.emu.can[2]._timer.stop()
        self.assertequal(self.emu.readmemory(test_addrs[2], 4), b'\x00\x00\x00\x00')
        self.assertequal(self.emu.readmemvalue(test_addrs[2], 4), 0x00000000)

        # can d
        self.emu.can[3]._timer.start()
        time.sleep(0.1)
        self.assertnotequal(self.emu.readmemory(test_addrs[3], 4), b'\x00\x00\x00\x00')
        self.assertnotequal(self.emu.readmemvalue(test_addrs[3], 4), 0x00000000)

        self.assertequal(self.emu.readmemory(test_addrs[0], 4), b'\x00\x00\x00\x00')
        self.assertequal(self.emu.readmemvalue(test_addrs[0], 4), 0x00000000)
        self.assertequal(self.emu.readmemory(test_addrs[1], 4), b'\x00\x00\x00\x00')
        self.assertequal(self.emu.readmemvalue(test_addrs[1], 4), 0x00000000)
        self.assertequal(self.emu.readmemory(test_addrs[2], 4), b'\x00\x00\x00\x00')
        self.assertequal(self.emu.readmemvalue(test_addrs[2], 4), 0x00000000)

        self.emu.can[3]._timer.stop()
        self.assertequal(self.emu.readmemory(test_addrs[3], 4), b'\x00\x00\x00\x00')
        self.assertequal(self.emu.readmemvalue(test_addrs[3], 4), 0x00000000)

    def test_flexcan_rxgmask_defaults(self):
        for idx in range(4):
            _, baseaddr = flexcan_devices[idx]
            addr = baseaddr + flexcan_rxgmask_offset

            self.assertequal(self.emu.readmemory(addr, 4), b'\xff\xff\xff\xff')
            self.assertequal(self.emu.readmemvalue(addr, 4), 0xffffffff)
            self.assertequal(self.emu.can[idx].registers.rxgmask, 0xffffffff)

    def test_flexcan_rx14mask_defaults(self):
        for idx in range(4):
            _, baseaddr = flexcan_devices[idx]
            addr = baseaddr + flexcan_rx14mask_offset

            self.assertequal(self.emu.readmemory(addr, 4), b'\xff\xff\xff\xff')
            self.assertequal(self.emu.readmemvalue(addr, 4), 0xffffffff)
            self.assertequal(self.emu.can[idx].registers.rx14mask, 0xffffffff)

    def test_flexcan_rx15mask_defaults(self):
        for idx in range(4):
            _, baseaddr = flexcan_devices[idx]
            addr = baseaddr + flexcan_rx15mask_offset

            self.assertequal(self.emu.readmemory(addr, 4), b'\xff\xff\xff\xff')
            self.assertequal(self.emu.readmemvalue(addr, 4), 0xffffffff)
            self.assertequal(self.emu.can[idx].registers.rx15mask, 0xffffffff)

    def test_flexcan_ecr_defaults(self):
        for idx in range(4):
            _, baseaddr = flexcan_devices[idx]
            addr = baseaddr + flexcan_ecr_offset

            self.assertequal(self.emu.readmemory(addr, 4), b'\x00\x00\x00\x00')
            self.assertequal(self.emu.readmemvalue(addr, 4), 0x00000000)
            self.assertequal(self.emu.can[idx].registers.ecr.tx_err, 0)
            self.assertequal(self.emu.can[idx].registers.ecr.rx_err, 0)

    def test_flexcan_esr_defaults(self):
        for idx in range(4):
            _, baseaddr = flexcan_devices[idx]
            addr = baseaddr + flexcan_esr_offset

            self.assertequal(self.emu.readmemory(addr, 4), b'\x00\x00\x00\x00')
            self.assertequal(self.emu.readmemvalue(addr, 4), 0x00000000)
            self.assertequal(self.emu.can[idx].registers.esr.twrn_int, 0)
            self.assertequal(self.emu.can[idx].registers.esr.rwrn_int, 0)
            self.assertequal(self.emu.can[idx].registers.esr.bit1_err, 0)
            self.assertequal(self.emu.can[idx].registers.esr.bit0_err, 0)
            self.assertequal(self.emu.can[idx].registers.esr.ack_err, 0)
            self.assertequal(self.emu.can[idx].registers.esr.crc_err, 0)
            self.assertequal(self.emu.can[idx].registers.esr.frm_err, 0)
            self.assertequal(self.emu.can[idx].registers.esr.stf_err, 0)
            self.assertequal(self.emu.can[idx].registers.esr.tx_wrn, 0)
            self.assertequal(self.emu.can[idx].registers.esr.rx_wrn, 0)
            self.assertequal(self.emu.can[idx].registers.esr.idle, 0)
            self.assertequal(self.emu.can[idx].registers.esr.txrx, 0)
            self.assertequal(self.emu.can[idx].registers.esr.flt_conf, 0)
            self.assertequal(self.emu.can[idx].registers.esr.boff_int, 0)
            self.assertequal(self.emu.can[idx].registers.esr.err_int, 0)

    def test_flexcan_imask_defaults(self):
        for idx in range(4):
            _, baseaddr = flexcan_devices[idx]
            addr1 = baseaddr + flexcan_imask1_offset
            addr2 = baseaddr + flexcan_imask2_offset

            # imask1
            self.assertequal(self.emu.readmemory(addr1, 4), b'\x00\x00\x00\x00')
            self.assertequal(self.emu.readmemvalue(addr1, 4), 0x00000000)
            self.assertequal(self.emu.can[idx].registers.imask1, 0x00000000)

            self.emu.writememory(addr1, b'\xff\xff\xff\xff')
            self.assertequal(self.emu.readmemory(addr1, 4), b'\xff\xff\xff\xff')
            self.assertequal(self.emu.readmemvalue(addr1, 4), 0xffffffff)
            self.assertequal(self.emu.can[idx].registers.imask1, 0xffffffff)

            # imask2
            self.assertequal(self.emu.readmemory(addr2, 4), b'\x00\x00\x00\x00')
            self.assertequal(self.emu.readmemvalue(addr2, 4), 0x00000000)
            self.assertequal(self.emu.can[idx].registers.imask2, 0x00000000)

            self.emu.writememory(addr2, b'\xff\xff\xff\xff')
            self.assertequal(self.emu.readmemory(addr2, 4), b'\xff\xff\xff\xff')
            self.assertequal(self.emu.readmemvalue(addr2, 4), 0xffffffff)
            self.assertequal(self.emu.can[idx].registers.imask2, 0xffffffff)

    def test_flexcan_iflag_defaults(self):
        for idx in range(4):
            _, baseaddr = flexcan_devices[idx]
            addr1 = baseaddr + flexcan_iflag1_offset
            addr2 = baseaddr + flexcan_iflag2_offset

            # iflag1
            self.assertequal(self.emu.readmemory(addr1, 4), b'\x00\x00\x00\x00')
            self.assertequal(self.emu.readmemvalue(addr1, 4), 0x00000000)
            self.assertequal(self.emu.can[idx].registers.iflag1, 0x00000000)

            # ensure the flag1 register are w1c and can't be set by writing
            self.emu.writememory(addr1, b'\xff\xff\xff\xff')
            self.assertequal(self.emu.readmemory(addr1, 4), b'\x00\x00\x00\x00')
            self.assertequal(self.emu.readmemvalue(addr1, 4), 0x00000000)
            self.assertequal(self.emu.can[idx].registers.iflag1, 0x00000000)

            self.emu.can[idx].registers.vsoverridevalue('iflag1', 0xffffffff)

            self.assertequal(self.emu.readmemory(addr1, 4), b'\xff\xff\xff\xff')
            self.assertequal(self.emu.readmemvalue(addr1, 4), 0xffffffff)
            self.assertequal(self.emu.can[idx].registers.iflag1, 0xffffffff)

            # clear some flags
            self.emu.writememory(addr1, b'\xa5\xa5\xa5\xa5')
            self.assertequal(self.emu.readmemory(addr1, 4), b'\x5a\x5a\x5a\x5a')
            self.assertequal(self.emu.readmemvalue(addr1, 4), 0x5a5a5a5a)
            self.assertequal(self.emu.can[idx].registers.iflag1, 0x5a5a5a5a)

            # iflag2
            self.assertequal(self.emu.readmemory(addr2, 4), b'\x00\x00\x00\x00')
            self.assertequal(self.emu.readmemvalue(addr2, 4), 0x00000000)
            self.assertequal(self.emu.can[idx].registers.iflag2, 0x00000000)

            # ensure the flag2 register are w1c and can't be set by writing
            self.emu.writememory(addr2, b'\xff\xff\xff\xff')
            self.assertequal(self.emu.readmemory(addr2, 4), b'\x00\x00\x00\x00')
            self.assertequal(self.emu.readmemvalue(addr2, 4), 0x00000000)
            self.assertequal(self.emu.can[idx].registers.iflag2, 0x00000000)

            self.emu.can[idx].registers.vsoverridevalue('iflag2', 0xffffffff)

            self.assertequal(self.emu.readmemory(addr2, 4), b'\xff\xff\xff\xff')
            self.assertequal(self.emu.readmemvalue(addr2, 4), 0xffffffff)
            self.assertequal(self.emu.can[idx].registers.iflag2, 0xffffffff)

            # clear some flags
            self.emu.writememory(addr2, b'\x5a\x5a\x5a\x5a')
            self.assertequal(self.emu.readmemory(addr2, 4), b'\xa5\xa5\xa5\xa5')
            self.assertequal(self.emu.readmemvalue(addr2, 4), 0xa5a5a5a5)
            self.assertequal(self.emu.can[idx].registers.iflag2, 0xa5a5a5a5)

    def test_flexcan_modes(self):
        for idx in range(4):
            devname, baseaddr = flexcan_devices[idx]
            self.assertequal(self.emu.can[idx].devname, devname)

            mcr_addr = baseaddr + flexcan_mcr_offset
            ctrl_addr = baseaddr + flexcan_ctrl_offset

            # should start off in disable, but the mcr[mdis] bit isn't set
            self.assertequal(self.emu.can[idx].mode, flexcan.flexcan_mode.disable)
            self.assertequal(self.emu.can[idx].registers.mcr.mdis, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.frz, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.halt, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.not_rdy, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.frz_ack, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.mdisack, 1)
            self.assertequal(self.emu.can[idx].registers.ctrl.lpb, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.lom, 0)

            # writing the same value back to mcr should put the peripheral into
            # freeze, mcr[mdisack] should now be cleared
            mcr_val = self.emu.readmemvalue(mcr_addr, 4)
            self.emu.writememvalue(mcr_addr, mcr_val, 4)

            self.assertequal(self.emu.can[idx].mode, flexcan.flexcan_mode.freeze)
            self.assertequal(self.emu.can[idx].registers.mcr.mdis, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.frz, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.halt, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.not_rdy, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.frz_ack, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.mdisack, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.lpb, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.lom, 0)

            # writing only the frz and halt bits should result in no change
            self.emu.writememvalue(mcr_addr, flexcan_mcr_frz_mask | flexcan_mcr_halt_mask, 4)

            self.assertequal(self.emu.can[idx].mode, flexcan.flexcan_mode.freeze)
            self.assertequal(self.emu.can[idx].registers.mcr.mdis, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.frz, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.halt, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.not_rdy, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.frz_ack, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.mdisack, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.lpb, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.lom, 0)

            # clearing the mcr[halt] bit should move the device to normal mode
            # and clear mcr[not_rdy] and mcr[frz_ack]
            self.emu.writememvalue(mcr_addr, flexcan_mcr_frz_mask, 4)

            self.assertequal(self.emu.can[idx].mode, flexcan.flexcan_mode.normal)
            self.assertequal(self.emu.can[idx].registers.mcr.mdis, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.frz, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.halt, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.not_rdy, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.frz_ack, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.mdisack, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.lpb, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.lom, 0)

            # set mcr[mdis] to move back to disabled, this should also set
            # mcr[not_rdy] and mcr[mdisack]
            #
            # mcr[frz] is also cleared by this change because the frz mask is
            # not written in this step.
            self.emu.writememvalue(mcr_addr, flexcan_mcr_mdis_mask, 4)

            self.assertequal(self.emu.can[idx].mode, flexcan.flexcan_mode.disable)
            self.assertequal(self.emu.can[idx].registers.mcr.mdis, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.frz, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.halt, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.not_rdy, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.frz_ack, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.mdisack, 1)
            self.assertequal(self.emu.can[idx].registers.ctrl.lpb, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.lom, 0)

            # clearing mcr[mdis] moves back to normal
            self.emu.writememvalue(mcr_addr, 0, 4)

            self.assertequal(self.emu.can[idx].mode, flexcan.flexcan_mode.normal)
            self.assertequal(self.emu.can[idx].registers.mcr.mdis, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.frz, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.halt, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.not_rdy, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.frz_ack, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.mdisack, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.lpb, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.lom, 0)

            # setting only mcr[halt] should not change anything since the
            # mcr[frz] bit is not set.
            self.emu.writememvalue(mcr_addr, flexcan_mcr_halt_mask, 4)

            self.assertequal(self.emu.can[idx].mode, flexcan.flexcan_mode.normal)
            self.assertequal(self.emu.can[idx].registers.mcr.mdis, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.frz, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.halt, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.not_rdy, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.frz_ack, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.mdisack, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.lpb, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.lom, 0)

            # setting both halt and frz moves the device back to freeze
            self.emu.writememvalue(mcr_addr, flexcan_mcr_frz_mask | flexcan_mcr_halt_mask, 4)

            self.assertequal(self.emu.can[idx].mode, flexcan.flexcan_mode.freeze)
            self.assertequal(self.emu.can[idx].registers.mcr.mdis, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.frz, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.halt, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.not_rdy, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.frz_ack, 1)
            self.assertequal(self.emu.can[idx].registers.mcr.mdisack, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.lpb, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.lom, 0)

            # test out loopback and listen-only modes but first move to freeze.
            # this step isn't currently necessary but it is the more "correct"
            # way to change modes.

            # setting ctrl[lpb] should enable loopback mode once the device is
            # back to normal mode.
            self.emu.writememvalue(ctrl_addr, flexcan_ctrl_lpb_mask, 4)
            self.emu.writememvalue(mcr_addr, 0, 4)

            self.assertequal(self.emu.can[idx].mode, flexcan.flexcan_mode.loop_back)
            self.assertequal(self.emu.can[idx].registers.mcr.mdis, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.frz, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.halt, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.not_rdy, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.frz_ack, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.mdisack, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.lpb, 1)
            self.assertequal(self.emu.can[idx].registers.ctrl.lom, 0)

            # back to freeze
            self.emu.writememvalue(mcr_addr, flexcan_mcr_frz_mask | flexcan_mcr_halt_mask, 4)
            self.assertequal(self.emu.can[idx].mode, flexcan.flexcan_mode.freeze)

            # setting lom and lpb should listen-only mode once the device is
            # back to normal mode.
            self.emu.writememvalue(ctrl_addr, flexcan_ctrl_lpb_mask | flexcan_ctrl_lom_mask, 4)
            self.emu.writememvalue(mcr_addr, 0, 4)

            self.assertequal(self.emu.can[idx].mode, flexcan.flexcan_mode.listen_only)
            self.assertequal(self.emu.can[idx].registers.mcr.mdis, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.frz, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.halt, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.not_rdy, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.frz_ack, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.mdisack, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.lpb, 1)
            self.assertequal(self.emu.can[idx].registers.ctrl.lom, 1)

            # back to freeze
            self.emu.writememvalue(mcr_addr, flexcan_mcr_frz_mask | flexcan_mcr_halt_mask, 4)
            self.assertequal(self.emu.can[idx].mode, flexcan.flexcan_mode.freeze)

            # setting lom will also set the device to listen-only mode
            self.emu.writememvalue(ctrl_addr, flexcan_ctrl_lom_mask, 4)
            self.emu.writememvalue(mcr_addr, 0, 4)

            self.assertequal(self.emu.can[idx].mode, flexcan.flexcan_mode.listen_only)
            self.assertequal(self.emu.can[idx].registers.mcr.mdis, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.frz, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.halt, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.not_rdy, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.frz_ack, 0)
            self.assertequal(self.emu.can[idx].registers.mcr.mdisack, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.lpb, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.lom, 1)

    def test_flexcan_speed(self):
        for idx in range(4):
            devname, baseaddr = flexcan_devices[idx]
            self.assertequal(self.emu.can[idx].devname, devname)
            ctrl_addr = baseaddr + flexcan_ctrl_offset

            # with the default clock source of extal, and presdiv the sclk is
            # 40 mhz, and then the default bitrate is 10 mbit/sec
            self.assertequal(self.emu.can[idx].speed, 10000000)
            self.assertequal(self.emu.can[idx].registers.ctrl.presdiv, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.pseg1, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.pseg2, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.clk_src, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.propseg, 0)

            # with clock source of the bus/internal pll, and presdiv the sclk is
            # 30 mhz, and then the default bitrate is 7.5 mbit/sec
            self.emu.writememvalue(ctrl_addr, flexcan_ctrl_clk_src_mask, 4)
            self.assertequal(self.emu.can[idx].speed, 7500000)
            self.assertequal(self.emu.can[idx].registers.ctrl.presdiv, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.pseg1, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.pseg2, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.clk_src, 1)
            self.assertequal(self.emu.can[idx].registers.ctrl.propseg, 0)

        # configure fmpll to an appropriately reasonable example valid baud rate
        self.set_sysclk_240mhz()

        for idx in range(4):
            # force the can device to update the clock speed
            self.emu.can[idx].updatespeed()

            _, baseaddr = flexcan_devices[idx]
            ctrl_addr = baseaddr + flexcan_ctrl_offset

            # with clock source of the bus/internal pll, and presdiv the sclk is
            # 120 mhz, and then the default bitrate is 30 mbit/sec
            self.assertequal(self.emu.can[idx].speed, 30000000)
            self.assertequal(self.emu.can[idx].registers.ctrl.presdiv, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.pseg1, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.pseg2, 0)
            self.assertequal(self.emu.can[idx].registers.ctrl.clk_src, 1)
            self.assertequal(self.emu.can[idx].registers.ctrl.propseg, 0)

            # a baudrate of 250000 can be achieved in a few ways, but one way
            # is:
            #   sclk = 120000000 / (29+1)
            #   tq = sclk / (1 + (4+1) + (7+1) + (1+1))
            val = (29 << flexcan_ctrl_presdiv_shift) | \
                    (7 << flexcan_ctrl_pseg1_shift) | \
                    (1 << flexcan_ctrl_pseg2_shift) | \
                    (flexcan_ctrl_clk_src_mask) | \
                    (4 << flexcan_ctrl_propseg_shift)
            self.emu.writememvalue(ctrl_addr, val, 4)

            # - ctrl[clk_src] set, the bus/internal pll
            # - ctrl[presdiv] is 29
            # - ctrl[pseg1] is 7
            # - ctrl[pseg2] is 1
            # - ctrl[propseg] is 4
            # sclk is 4 mhz, and the bitrate (tq) is 250000 kbit/sec
            self.assertequal(self.emu.can[idx].speed, 250000)
            self.assertequal(self.emu.can[idx].registers.ctrl.presdiv, 29)
            self.assertequal(self.emu.can[idx].registers.ctrl.pseg1, 7)
            self.assertequal(self.emu.can[idx].registers.ctrl.pseg2, 1)
            self.assertequal(self.emu.can[idx].registers.ctrl.clk_src, 1)
            self.assertequal(self.emu.can[idx].registers.ctrl.propseg, 4)

    def test_flexcan_timer(self):
        # because this test attempts to test the accuracy of emulated timers
        # force the system time scaling factor to be 0.01 (100 real milliseconds
        # to 1 emulated millisecond).
        self.emu._systime_scaling = 0.1

        # set standard bus speeds
        self.set_baudrates()

        # at 1mbps run for 0.05 msec can a should have a value of approximately
        # 50000. since the scaling time for this test is set to 0.1 set each
        # bus to normal and then wait 0.5 seconds before collecting the end
        # timer values.
        for idx in range(4):
            devname, baseaddr = flexcan_devices[idx]
            mcr_addr = baseaddr + flexcan_mcr_offset
            timer_addr = baseaddr + flexcan_timer_offset

            # expected ticks:
            expected_val = self.emu.can[idx].speed * 0.5 * self.emu._systime_scaling

            # margin of error is approximately 0.001 (so speed * 0.001 * 0.1)
            # because this is dependant on the execution speed of the machine in
            # question increase to 0.005
            margin = self.emu.can[idx].speed * 0.005 * self.emu._systime_scaling

            self.emu.writememvalue(mcr_addr, 0, 4)

            time.sleep(0.5)
            val = self.emu.readmemvalue(timer_addr, 4)

            self.assertalmostequal(val, expected_val, delta=margin, msg=devname)

            self.assertequal(self.emu.can[idx].mode, flexcan.flexcan_mode.normal, devname)
            self.emu.writememvalue(mcr_addr, flexcan_mcr_mdis_mask, 4)
            self.assertequal(self.emu.can[idx].mode, flexcan.flexcan_mode.disable, devname)
            self.assertequal(self.emu.readmemvalue(timer_addr, 4), 0, devname)

    def test_flexcan_tx(self):
        # because this test attempts to test the accuracy of emulated timers
        # force the system time scaling factor to be 0.01 (100 real milliseconds
        # to 1 emulated millisecond).
        self.emu._systime_scaling = 0.1

        # set standard bus speeds
        self.set_baudrates()

        # only enable some of the mailbox interrupts: 0-7, 24-31, 32-47
        enabled_intrs = list(range(0, 8)) + list(range(24, 32)) + list(range(32, 48))

        # send a message from each bus and ensure the timestamp is correctly
        # updated, wait 0.10 seconds before sending and then check that the time
        # stamp is correct.
        for dev in range(4):
            devname, baseaddr = flexcan_devices[dev]
            mcr_addr = baseaddr + flexcan_mcr_offset
            timer_addr = baseaddr + flexcan_timer_offset

            # generate one message for each mailbox
            msgs = [generate_msg() for i in range(flexcan_num_mbs)]

            # only enable some of the mailbox interrupts: 0-7, 24-31, 32-47
            imask1_val = 0xff0000ff
            imask2_val = 0x0000ffff
            self.emu.writememvalue(baseaddr + flexcan_imask1_offset, imask1_val, 4)
            self.emu.writememvalue(baseaddr + flexcan_imask2_offset, imask2_val, 4)

            # change mode to normal, the timer now starts moving, but disable
            # self-reception of messages to make this test simpler
            self.emu.writememvalue(mcr_addr, flexcan_mcr_srx_dis_mask, 4)
            start_time = time.time()

            # place messages into each mailbox and mark the mailbox as inactive
            for mb in range(flexcan_num_mbs):
                # generate a random priority (0 to 7) to ensure that the
                # priority field is correctly removed during transmission
                prio = random.randrange(0, 8)
                data = msgs[mb].encode(code=flexcan.flexcan_code_tx_inactive, prio=prio)
                write_mb_data(self.emu, dev, mb, data)

                # ensure that the written data matches what should have been
                # written
                testmsg = '%s[%d]' % (devname, mb)
                start = baseaddr + flexcan_mb_offset + (mb * flexcan_mbx_size)
                self.assertequal(self.emu.readmemory(start, flexcan_mbx_size), data, msg=testmsg)

            # ensure that no messages have been transmitted and there are no
            # pending interrupts
            self.assertequal(self.emu.can[dev].gettransmittedobjs(), [], devname)
            self.assertequal(self._getpendingexceptions(), [], msg=devname)

            # wait some short time to let the timer run for a bit
            time.sleep(0.5)

            # for each can device only transmit from some of them:
            #   can a: tx in all mailboxes
            #   can b: tx in every other mailbox
            #   can c: tx in every third mailbox
            #   can d: tx in every fourth mailbox
            tx_mbs = list(range(0, flexcan_num_mbs, dev+1))

            # temporarily disable the garbage collector
            gc.disable()

            # randomize the tx mailbox order now
            random.shuffle(tx_mbs)
            tx_times = {}
            for mb in tx_mbs:
                # save the timestamp that the message was sent
                addr = baseaddr + flexcan_mb_offset + (mb * flexcan_mbx_size)
                self.emu.writememvalue(addr, flexcan.flexcan_code_tx_active, 1)
                tx_times[mb] = time.time()

            # it can be re-enabled now
            gc.enable()

            # now read all queued transmit messages
            txd_msgs = self.emu.can[dev].gettransmittedobjs()
            self.assertequal(len(txd_msgs), len(tx_mbs), msg=devname)

            # ensure the correct iflags are set
            iflag1_val = self.emu.readmemvalue(baseaddr + flexcan_iflag1_offset, 4)
            iflag2_val = self.emu.readmemvalue(baseaddr + flexcan_iflag2_offset, 4)

            if dev == 0:
                # for can a every mailbox should have sent a message
                self.assertequal(iflag1_val, 0xffffffff, msg=devname)
                self.assertequal(iflag2_val, 0xffffffff, msg=devname)
            elif dev == 1:
                # for can b every other mailbox should have sent a message
                self.assertequal(iflag1_val, 0x55555555, msg=devname)
                self.assertequal(iflag2_val, 0x55555555, msg=devname)
            elif dev == 2:
                # for can c every third mailbox should have sent a message
                self.assertequal(iflag1_val, 0x49249249, msg=devname)
                self.assertequal(iflag2_val, 0x92492492, msg=devname)
            elif dev == 3:
                # for can d every fourth mailbox should have sent a message
                self.assertequal(iflag1_val, 0x11111111, msg=devname)
                self.assertequal(iflag2_val, 0x11111111, msg=devname)

            # calculate how many interrupts there should be and correlate the
            # interrupts to the transmit and interrupt enabled mailboxes
            tx_int_mbs = []
            for mb in range(flexcan_num_mbs):
                testmsg = '%s[%d]' % (devname, mb)
                if mb < 32:
                    mb_mask = 1 << mb
                    flag = iflag1_val
                    mask = imask1_val
                else:
                    mb_mask = 1 << (mb-32)
                    flag = iflag2_val
                    mask = imask2_val

                if flag & mb_mask:
                    self.assertin(mb, tx_mbs, msg=testmsg)
                    if mask & mb_mask:
                        tx_int_mbs.append(mb)
                else:
                    self.assertnotin(mb, tx_mbs, msg=testmsg)

            # it is expected that the calculated timestamp will be slightly
            # larger than the actual timestamp because it is saved right
            # after the memory write occurs that causes the transmit
            margin = self.emu.can[dev].speed * 0.0100 * self.emu._systime_scaling

            # confirm that the order of the generated interrupts matches both
            # the order of the transmitted messages and the interrupt source for
            # the tx mailbox
            excs = self._getpendingexceptions()
            self.assertequal(len(excs), len(tx_int_mbs), msg=devname)
            exc_iter = iter(excs)
            txd_msgs_iter = iter(txd_msgs)

            # iterate through the mailboxes based on the order messages were
            # transmitted
            for mb in tx_mbs:
                testmsg = '%s[%d]' % (devname, mb)

                # confirm that the message contents are correct
                txd_msg = next(txd_msgs_iter)
                self.assertequal(txd_msg, msgs[mb], msg=testmsg)

                # confirm that the timestamp is accurate
                tx_delay = tx_times[mb] - start_time
                expected_ticks = int(self.emu.can[dev].speed * tx_delay * self.emu._systime_scaling) & 0xffff

                ts_offset = (mb * flexcan_mbx_size) + 2
                timestamp = struct.unpack_from('>h', self.emu.can[dev].registers.mb.value, ts_offset)[0]

                self.assertalmostequal(timestamp, expected_ticks, delta=margin, msg=testmsg)

                # lastly, a mailbox should only have a corresponding interrupt
                # if the interrupt mask is set
                if mb in tx_int_mbs:
                    self.assertequal(next(exc_iter), get_int(dev, mb), msg=testmsg)

            # now ensure that all mailboxes that were not in the list are still
            # inactive
            for mb in range(flexcan_num_mbs):
                if mb not in tx_mbs:
                    testmsg = '%s[%d]' % (devname, mb)

                    # ensure that inactive mailboxes have the same data and
                    # still have a code of tx_inactive, and the timestamp is
                    # still 0
                    code_offset = mb * flexcan_mbx_size
                    code = self.emu.can[dev].registers.mb[code_offset]
                    self.assertequal(code, flexcan.flexcan_code_tx_inactive, msg=testmsg)
                    code_addr = baseaddr + flexcan_mb_offset + code_offset
                    self.assertequal(self.emu.readmemvalue(code_addr, 1),
                            flexcan.flexcan_code_tx_inactive, msg=testmsg)

                    ts_offset = (mb * flexcan_mbx_size) + 2
                    timestamp = struct.unpack_from('>h', self.emu.can[dev].registers.mb.value, ts_offset)[0]
                    self.assertequal(timestamp, 0, msg=testmsg)
                    ts_addr = baseaddr + flexcan_mb_offset + ts_offset
                    self.assertequal(self.emu.readmemvalue(ts_addr, 2), 0, msg=testmsg)

    def test_flexcan_rx(self):
        # because this test attempts to test the accuracy of emulated timers
        # force the system time scaling factor to be 0.01 (100 real milliseconds
        # to 1 emulated millisecond).
        self.emu._systime_scaling = 0.1

        # set standard bus speeds
        self.set_baudrates()

        # only enable some of the mailbox interrupts: 0-7, 24-31, 32-47
        enabled_intrs = list(range(0, 8)) + list(range(24, 32)) + list(range(32, 48))

        # send a message from each bus and ensure the timestamp is correctly
        # updated, wait 0.10 seconds before sending and then check that the time
        # stamp is correct.

        for dev in range(4):
            devname, baseaddr = flexcan_devices[dev]
            mcr_addr = baseaddr + flexcan_mcr_offset
            timer_addr = baseaddr + flexcan_timer_offset

            # for each can device only enable some mailboxes to receive:
            #   can a: rx in all mailboxes
            #   can b: rx in every other mailbox
            #   can c: rx in every third mailbox
            #   can d: rx in every fourth mailbox
            # set those mailboxes to rx_empty now
            rx_mbs = list(range(0, flexcan_num_mbs, dev+1))
            for mb in rx_mbs:
                addr = baseaddr + flexcan_mb_offset + (mb * flexcan_mbx_size)
                self.emu.writememvalue(addr, flexcan.flexcan_code_rx_empty, 1)

            # only enable some of the mailbox interrupts: 0-7, 24-31, 32-47
            self.emu.writememvalue(baseaddr + flexcan_imask1_offset, 0xff0000ff, 4)
            self.emu.writememvalue(baseaddr + flexcan_imask2_offset, 0x0000ffff, 4)

            # generate one message for each mailbox that can receive, because a
            # message with id 0 would match a mailbox with the entire mask set
            # and the filter value of 0, make the minimum id 1
            msgs = [generate_msg(rtr=0, min_id=1) for i in range(len(rx_mbs))]

            # change mode to normal
            self.emu.writememvalue(mcr_addr, 0, 4)

            # call the processreceiveddata function to mimic what the emulator
            # calls when a message is received during normal execution.  because
            # the default filters are all 1's and no id masks were defined in
            # any of the valid receive mailboxes, these messages should all just
            # be discarded.
            for mb, msg in zip(rx_mbs, msgs):
                addr = baseaddr + flexcan_mb_offset + (mb * flexcan_mbx_size)
                self.emu.can[dev].processreceiveddata(msg)

            # loop through the mailboxes and ensure they are all still empty.
            inactive_mb = b'\x00' * flexcan_mbx_size
            empty_mb = b'\x04' + b'\x00' * (flexcan_mbx_size - 1)
            for mb in range(flexcan_num_mbs):
                testmsg = '%s[%d]' % (devname, mb)
                addr = baseaddr + flexcan_mb_offset + (mb * flexcan_mbx_size)
                # ensure that nothing has been received in this mailbox, but the
                # code is still correct
                if mb in rx_mbs:
                    self.assertequal(self.emu.readmemory(addr, flexcan_mbx_size), empty_mb, msg=testmsg)
                else:
                    self.assertequal(self.emu.readmemory(addr, flexcan_mbx_size), inactive_mb, msg=testmsg)

            # ensure there are no pending interrupts
            self.assertequal(self._getpendingexceptions(), [], msg=devname)

            # now clear out the rxg, rx14, and rx15 masks, these must be changed
            # in freeze mode
            self.emu.writememvalue(mcr_addr, flexcan_mcr_frz_mask | flexcan_mcr_halt_mask, 4)
            self.emu.writememvalue(baseaddr + flexcan_rxgmask_offset, 0, 4)
            self.emu.writememvalue(baseaddr + flexcan_rx14mask_offset, 0, 4)
            self.emu.writememvalue(baseaddr + flexcan_rx15mask_offset, 0, 4)

            # now move back to normal mode
            self.emu.writememvalue(mcr_addr, 0, 4)
            start_time = time.time()

            last_mb = none
            last_timestamp = none

            # it is expected that the calculated timestamp will be slightly
            # larger than the actual timestamp because it is saved right
            # after the memory write occurs that causes the transmit
            margin = self.emu.can[dev].speed * 0.0050 * self.emu._systime_scaling

            # temporarily disable the garbage collector
            gc.disable()

            # call the processreceiveddata function to mimic what the emulator
            # calls when a message is received during normal execution.  because
            # no filtering or masking is set up the messages should be placed
            # into the first empty mailbox
            for mb, msg in zip(rx_mbs, msgs):
                testmsg = '%s[%d]' % (devname, mb)
                addr = baseaddr + flexcan_mb_offset + (mb * flexcan_mbx_size)

                self.emu.can[dev].processreceiveddata(msg)

                # confirm that the timestamp is accurate. the timer has probably
                # wrapped by now so ensure it is limited to 16 bits
                rx_delay = time.time() - start_time
                expected_ticks = int(self.emu.can[dev].speed * rx_delay * self.emu._systime_scaling) & 0xffff

                ts_offset = (mb * flexcan_mbx_size) + 2
                timestamp = struct.unpack_from('>h', self.emu.can[dev].registers.mb.value, ts_offset)[0]
                self.assertalmostequal(timestamp, expected_ticks, delta=margin, msg=testmsg)

                last_mb = mb
                last_timestamp = timestamp

                # now that the timestamp has been confirmed to be within the
                # expected range, ensure that the message in the mailbox matches
                # what is expected for the received message
                rx_msg_data = msg.encode(code=flexcan.flexcan_code_rx_full, timestamp=timestamp)
                self.assertequal(self.emu.readmemory(addr, flexcan_mbx_size), rx_msg_data, msg=testmsg)

                # ensure that there is a pending interrupt for this mailbox
                if mb in enabled_intrs:
                    self.assertequal(self._getpendingexceptions(), [get_int(dev, mb)], msg=testmsg)
                else:
                    self.assertequal(self._getpendingexceptions(), [], msg=testmsg)

            # it can be re-enabled now
            gc.enable()

            # there should be no more interrupts pending
            self.assertequal(self._getpendingexceptions(), [], msg=testmsg)

            # ensure the correct iflags are set
            iflag1_val = self.emu.readmemvalue(baseaddr + flexcan_iflag1_offset, 4)
            iflag2_val = self.emu.readmemvalue(baseaddr + flexcan_iflag2_offset, 4)
            if dev == 0:
                # for can a every mailbox should have a message
                self.assertequal(iflag1_val, 0xffffffff, msg=devname)
                self.assertequal(iflag2_val, 0xffffffff, msg=devname)
            elif dev == 1:
                # for can b every other mailbox should have a message
                self.assertequal(iflag1_val, 0x55555555, msg=devname)
                self.assertequal(iflag2_val, 0x55555555, msg=devname)
            elif dev == 2:
                # for can c every third mailbox should have a message
                self.assertequal(iflag1_val, 0x49249249, msg=devname)
                self.assertequal(iflag2_val, 0x92492492, msg=devname)
            elif dev == 3:
                # for can d every fourth mailbox should have a message
                self.assertequal(iflag1_val, 0x11111111, msg=devname)
                self.assertequal(iflag2_val, 0x11111111, msg=devname)

            # now ensure that all mailboxes that were not in the list are still
            # inactive and empty
            for mb in range(flexcan_num_mbs):
                if mb not in rx_mbs:
                    addr = baseaddr + flexcan_mb_offset + (mb * flexcan_mbx_size)

                    # ensure that nothing has been received in this mailbox
                    self.assertequal(self.emu.readmemory(addr, flexcan_mbx_size), inactive_mb, msg=testmsg)

            # generate one more message and send it, this should cause the code
            # of the last mailbox configured for receive to be set to overrun
            # but should not generate any new interrupts
            overflow_msg = generate_msg(rtr=0)

            # ensure that this doesn't match the last sent message (which should
            # be in the last mailbox)
            #
            self.assertnotequal(overflow_msg, msgs[-1], devname)
            self.emu.can[dev].processreceiveddata(overflow_msg)

            # ensure that the message in the last receive mailbox still matches
            # the last message received
            testmsg = '%s[%d]' % (devname, last_mb)
            overflow_msg_data = msgs[-1].encode(code=flexcan.flexcan_code_rx_overrun, timestamp=last_timestamp)
            addr = baseaddr + flexcan_mb_offset + (last_mb * flexcan_mbx_size)
            self.assertequal(self.emu.readmemory(addr, flexcan_mbx_size), overflow_msg_data, msg=testmsg)

            # and ensure that there are no new interrupts
            self.assertequal(self._getpendingexceptions(), [], msg=testmsg)

    def test_flexcan_rx_fifo(self):
        # because this test attempts to test the accuracy of emulated timers
        # force the system time scaling factor to be 0.01 (100 real milliseconds
        # to 1 emulated millisecond).
        self.emu._systime_scaling = 0.1

        # set standard bus speeds
        self.set_baudrates()

        # only enable some of the mailbox interrupts: 0-7, 24-31, 32-47
        enabled_intrs = list(range(0, 8)) + list(range(24, 32)) + list(range(32, 48))

        for dev in range(4):
            devname, baseaddr = flexcan_devices[dev]
            mcr_addr = baseaddr + flexcan_mcr_offset

            # configure the following things:
            # - enable all interrupts
            self.emu.writememvalue(baseaddr + flexcan_imask1_offset, 0xffffffff, 4)
            self.emu.writememvalue(baseaddr + flexcan_imask2_offset, 0xffffffff, 4)

            # - clear all filter masks
            self.emu.writememvalue(baseaddr + flexcan_rxgmask_offset, 0, 4)
            self.emu.writememvalue(baseaddr + flexcan_rx14mask_offset, 0, 4)
            self.emu.writememvalue(baseaddr + flexcan_rx15mask_offset, 0, 4)

            # - set all non-rxfifo mailboxes to inactive
            for mb in range(6, flexcan_num_mbs):
                addr = baseaddr + flexcan_mb_offset + (mb * flexcan_mbx_size)
                self.emu.writememvalue(addr, flexcan.flexcan_code_rx_inactive, 1)

            # - change mode to normal and enable rx fifo
            self.emu.writememvalue(mcr_addr, flexcan_mcr_fen_mask, 4)
            self.assertequal(self.emu.can[dev].mode, flexcan.flexcan_mode.normal, devname)
            self.assertequal(self.emu.can[dev].registers.mcr.fen, 1, devname)
            start_time = time.time()

            # generate 6 messages to send
            msgs = [generate_msg() for i in range(6)]

            # it is expected that the calculated timestamp will be slightly
            # larger than the actual timestamp because it is saved right
            # after the memory write occurs that causes the transmit
            margin = self.emu.can[dev].speed * 0.0050 * self.emu._systime_scaling

            # temporarily disable the garbage collector
            gc.disable()

            # the rxfifo can hold 6 messages, each received message should
            # generate a rxfifo msg available interrupt (mb5), when the last
            # message is queued an rxfifo warning interrupt (mb6) should be
            # generated
            rx_times = []
            for i in range(len(msgs)):
                testmsg = '%s rxfifo[%d]' % (devname, i)
                self.emu.can[dev].processreceiveddata(msgs[i])
                rx_times.append(time.time())
                time.sleep(0.1)

                # there should be one rxfifo msg available interrupt (mb5) when
                # the first message is sent, then an rxfifo warning interrupt
                # (mb6) after the 6th message is sent.
                if i == 0:
                    self.assertequal(self._getpendingexceptions(), [get_int(dev, 5)], msg=testmsg)
                elif i == 5:
                    self.assertequal(self._getpendingexceptions(), [get_int(dev, 6)], msg=testmsg)

            # only mb5 and mb6 interrupt flags should be set
            iflag1_val = self.emu.readmemvalue(baseaddr + flexcan_iflag1_offset, 4)
            iflag2_val = self.emu.readmemvalue(baseaddr + flexcan_iflag2_offset, 4)
            self.assertequal(iflag1_val, 0x00000060, msg=devname)
            self.assertequal(iflag2_val, 0x00000000, msg=devname)

            # send one more message and ensure the rxfifo overflow interrupt
            # (mb7) happens
            lost_msg = generate_msg()
            self.emu.can[dev].processreceiveddata(lost_msg)

            self.assertequal(self._getpendingexceptions(), [get_int(dev, 7)], msg=testmsg)
            iflag1_val = self.emu.readmemvalue(baseaddr + flexcan_iflag1_offset, 4)
            self.assertequal(iflag1_val, 0x000000e0, msg=devname)

            # now read a message from the rxfifo (mb0).
            # randomize how this data is read from the mailbox registers, it
            # can be read in 1, 2 or 4 byte chunks.
            first_msg = read_mb_data(self.emu, dev, 0)
            rx_msgs = [first_msg]

            # reading the fifo without clearing the interrupt flag should not
            # change the available data, read again and confirm the data matches
            self.assertequal(read_mb_data(self.emu, dev, 0), first_msg, msg=devname)

            # clear the overflow and warning interrupt flags and ensure that the
            # message in mb0 doesn't change
            self.emu.writememvalue(baseaddr + flexcan_iflag1_offset, 0x000000c0, 4)
            iflag1_val = self.emu.readmemvalue(baseaddr + flexcan_iflag1_offset, 4)
            self.assertequal(iflag1_val, 0x00000020, msg=devname)
            self.assertequal(self._getpendingexceptions(), [], msg=devname)

            self.assertequal(read_mb_data(self.emu, dev, 0), first_msg, msg=devname)

            # clear the mb5 interrupt flag and ensure that a new rxfifo msg
            # available interrupt (mb5) happens and that a new message is
            # available in mb0
            self.emu.writememvalue(baseaddr + flexcan_iflag1_offset, 0x00000020, 4)
            self.assertequal(self._getpendingexceptions(), [get_int(dev, 5)], msg=devname)

            self.assertnotequal(read_mb_data(self.emu, dev, 0), first_msg, msg=devname)

            # the mb5 interrupt flag should be set again
            iflag1_val = self.emu.readmemvalue(baseaddr + flexcan_iflag1_offset, 4)
            self.assertequal(iflag1_val, 0x00000020, msg=devname)

            # send another message and ensure the rxfifo warning is set again
            msgs.append(generate_msg())
            self.emu.can[dev].processreceiveddata(msgs[-1])
            rx_times.append(time.time())

            self.assertequal(self._getpendingexceptions(), [get_int(dev, 6)], msg=testmsg)
            iflag1_val = self.emu.readmemvalue(baseaddr + flexcan_iflag1_offset, 4)
            self.assertequal(iflag1_val, 0x00000060, msg=devname)

            # read the remaining 5 messages from the rxfifo
            while iflag1_val:
                # save the message in mb0
                msg = read_mb_data(self.emu, dev, 0)
                rx_msgs.append(msg)

                # clear the interrupt flags, this should trigger a new interrupt
                # if we have not read all of the messages from the fifo
                self.emu.writememvalue(baseaddr + flexcan_iflag1_offset, iflag1_val, 4)
                iflag1_val = self.emu.readmemvalue(baseaddr + flexcan_iflag1_offset, 4)

                if len(rx_msgs) != len(msgs):
                    self.assertequal(iflag1_val, 0x00000020, msg=devname)
                    self.assertequal(self._getpendingexceptions(), [get_int(dev, 5)], msg=devname)
                else:
                    self.assertequal(iflag1_val, 0x00000000, msg=devname)

            # sanity check, the number of received messages should now match the
            # number of sent messages and the number of receive times recorded.
            self.assertequal(len(rx_msgs), len(msgs), msg=devname)
            self.assertequal(len(rx_msgs), len(rx_times), msg=devname)

            # it can be re-enabled now
            gc.enable()

            # go through the received messages and timestamps and ensure that
            # messages were received correctly.
            for i in range(len(msgs)):
                testmsg = '%s rxfifo[%d]' % (devname, i)
                rx_delay = rx_times[i] - start_time
                expected_ticks = int(self.emu.can[dev].speed * rx_delay * self.emu._systime_scaling) & 0xffff

                timestamp = struct.unpack_from('>h', rx_msgs[i], 2)[0]
                self.assertalmostequal(timestamp, expected_ticks, delta=margin, msg=testmsg)

                # now that the timestamp has been confirmed to be within the
                # expected range, ensure that the received message in the
                # matches what was sent
                msg_data = msgs[i].encode(code=0, timestamp=timestamp)
                self.assertequal(rx_msgs[i], msg_data, msg=testmsg)

    @unittest.skip('todo')
    def test_flexcan_rx_filters(self):
        pass

    @unittest.skip('todo')
    def test_flexcan_tx_loopback(self):
        pass

    @unittest.skip('todo')
    def test_flexcan_rtr(self):
        pass

    @unittest.skip('todo')
    def test_flexcan_rtr_fifo(self):
        pass


class MPC5674_FlexCAN_RealIO(MPC5674_Test):
    args = MPC5674_Test.args + [
        '-O', 'project.MPC5674.FlexCAN_A.port=10001',
        '-O', 'project.MPC5674.FlexCAN_B.port=10002',
        '-O', 'project.MPC5674.FlexCAN_C.port=10003',
        '-O', 'project.MPC5674.FlexCAN_D.port=10004',
    ]

    def set_sysclk_240mhz(self):
        # Default PLL clock based on the PCB params selected for these tests is
        # 60 MHz
        self.assertEqual(self.emu.vw.config.project.MPC5674.FMPLL.extal, 40000000)
        self.assertEqual(self.emu.fmpll.f_pll(), 60000000.0)

        # The max clock for the real hardware is 764 MHz:
        #  (40 MHz * (50+16)) / ((4+1) * (1+1))
        #
        # But the more efficient clock speed used in actual hardware is 240 MHz
        # which allows a bus speed of 120 MHz.
        #  (40 MHz * (80+16)) / ((7+1) * (1+1))

        # ESYNCR1[EMFD] = 80
        # ESYNCR1[EPREDIV] = 7
        self.emu.writeMemValue(0xC3F80008, 0xF0070050, 4)
        # ESYNCR2[ERFD] = 1
        self.emu.writeMemValue(0xC3F8000C, 0x00000001, 4)
        self.assertEqual(self.emu.fmpll.f_pll(), 240000000.0)

        # Now set the SIU peripheral configuration to allow the CPU frequency to
        # be double the peripheral speed (otherwise the maximum bus/peripheral
        # speed is 132 MHz

        # SYSDIV[IPCLKDIV] = 0
        # SYSDIV[BYPASS] = 1
        self.emu.writeMemValue(0xC3F909A0, 0x00000010, 4)
        self.assertEqual(self.emu.siu.f_periph(), 120000000.0)

    def set_baudrates(self):
        # Configure FMPLL to an appropriately reasonable example valid baud rate
        self.set_sysclk_240mhz()

        # Set each peripheral to different sclk rates so we can test that the
        # emulated timer runs at an appropriately simulated rate.
        ctrl_addrs = [a + FLEXCAN_CTRL_OFFSET for _, a in FLEXCAN_DEVICES]

        # FlexCAN_A: 1 Mbps
        #   - sclk = 120000000 / (14+1)
        #   - tq = sclk / (1 + (1+1) + (2+1) + (1+1))
        val = (14 << FLEXCAN_CTRL_PRESDIV_SHIFT) | \
                (2 << FLEXCAN_CTRL_PSEG1_SHIFT) | \
                (1 << FLEXCAN_CTRL_PSEG2_SHIFT) | \
                (FLEXCAN_CTRL_CLK_SRC_MASK) | \
                (1 << FLEXCAN_CTRL_PROPSEG_SHIFT)
        self.emu.writeMemValue(ctrl_addrs[0], val, 4)
        self.assertEqual(self.emu.can[0].speed, 1000000)

        # FlexCAN_B: 500 kbps
        #   - sclk = 120000000 / (14+1)
        #   - tq = sclk / (1 + (4+1) + (7+1) + (1+1))
        val = (14 << FLEXCAN_CTRL_PRESDIV_SHIFT) | \
                (7 << FLEXCAN_CTRL_PSEG1_SHIFT) | \
                (1 << FLEXCAN_CTRL_PSEG2_SHIFT) | \
                (FLEXCAN_CTRL_CLK_SRC_MASK) | \
                (4 << FLEXCAN_CTRL_PROPSEG_SHIFT)
        self.emu.writeMemValue(ctrl_addrs[1], val, 4)
        self.assertEqual(self.emu.can[1].speed, 500000)

        #   FlexCAN_C: 250 kbps
        #   - sclk = 120000000 / (29+1)
        #   - tq = sclk / (1 + (4+1) + (7+1) + (1+1))
        val = (29 << FLEXCAN_CTRL_PRESDIV_SHIFT) | \
                (7 << FLEXCAN_CTRL_PSEG1_SHIFT) | \
                (1 << FLEXCAN_CTRL_PSEG2_SHIFT) | \
                (FLEXCAN_CTRL_CLK_SRC_MASK) | \
                (4 << FLEXCAN_CTRL_PROPSEG_SHIFT)
        self.emu.writeMemValue(ctrl_addrs[2], val, 4)
        self.assertEqual(self.emu.can[2].speed, 250000)

        # FlexCAN_D: 125 kbps
        #   - sclk = 120000000 / (59+1)
        #   - tq = sclk / (1 + (4+1) + (7+1) + (1+1))
        val = (59 << FLEXCAN_CTRL_PRESDIV_SHIFT) | \
                (7 << FLEXCAN_CTRL_PSEG1_SHIFT) | \
                (1 << FLEXCAN_CTRL_PSEG2_SHIFT) | \
                (FLEXCAN_CTRL_CLK_SRC_MASK) | \
                (4 << FLEXCAN_CTRL_PROPSEG_SHIFT)
        self.emu.writeMemValue(ctrl_addrs[3], val, 4)
        self.assertEqual(self.emu.can[3].speed, 125000)

    def test_flexcan_io(self):
        # Set standard bus speeds
        self.set_baudrates()

        # Set INTC MCR[HVEN] to allow hardware vectoring to happen
        self.emu.intc.registers.mcr.hven = 1

        # Fill in a bunch of NOPs (0x60000000: ori r0,r0,0) starting at the
        # current PC (0x00000000)
        pc = self.emu.getProgramCounter()
        instrs = b'\x60\x00\x00\x00' * 0x100
        self.emu.flash.data[pc:pc+len(instrs)] = instrs

        # Fill all of the possible target addresses for HW vectored CAN
        # interrupt handlers with one NOP and one RFI (0x4c000064) instruction
        srcs = []
        for dev in range(4):
            srcs += [get_int_src(dev, mb) for mb in range(FLEXCAN_NUM_MBs)]
        srcs = list(set(srcs))
        for src in srcs:
            # The target address calculation is
            #   IPVR (0) | source << 4
            addr = src << 4
            # Change flash directly because otherwise we have to do a whole
            # thing to emulate proper flash erase/write procedures
            self.emu.flash.data[addr:addr+8] = b'\x60\x00\x00\x00\x4c\x00\x00\x64'

        for dev in range(4):
            devname, baseaddr = FLEXCAN_DEVICES[dev]
            mcr_addr = baseaddr + FLEXCAN_MCR_OFFSET

            # Create test IO class that can send and receive messages to the CAN
            # peripheral
            host = self.emu.can[dev]._config['host']
            port = self.emu.can[dev]._config['port']
            client = ExternalIOClient(host, port)
            client.open()

            # Generate one test Tx and Rx message
            tx_msg = generate_msg(rtr=0)
            rx_msg = generate_msg(rtr=0)

            # Determine the expected MB0 and MB1 interrupt vectors
            mb0_int = get_int(dev, 0)
            mb1_int = get_int(dev, 1)

            # When the exception handlers are executed by the stepi() function
            # the PC will be at the second instruction in the ISR
            mb0_handler_addr = (get_int_src(dev, 0) << 4) + 4
            mb1_handler_addr = (get_int_src(dev, 1) << 4) + 4

            # Elevate the priority of the MB0 and MB1 interrupts so we can
            # confirm that the INTC peripheral CPR (current priority) is working
            # properly. Set MB0 interrupt priority to be higher than MB1 to
            # guarantee the order they are processed in
            self.emu.writeMemValue(INTC_PSRn_ADDR + get_int_src(dev, 0), 2, 1)
            self.emu.writeMemValue(INTC_PSRn_ADDR + get_int_src(dev, 1), 1, 1)

            # Configure the following things:
            # - Enable all interrupts
            self.emu.writeMemValue(baseaddr + FLEXCAN_IMASK1_OFFSET, 0xFFFFFFFF, 4)
            self.emu.writeMemValue(baseaddr + FLEXCAN_IMASK2_OFFSET, 0xFFFFFFFF, 4)

            # - Clear all filter masks
            self.emu.writeMemValue(baseaddr + FLEXCAN_RXGMASK_OFFSET, 0, 4)
            self.emu.writeMemValue(baseaddr + FLEXCAN_RX14MASK_OFFSET, 0, 4)
            self.emu.writeMemValue(baseaddr + FLEXCAN_RX15MASK_OFFSET, 0, 4)

            # Fill MB0
            tx_data = tx_msg.encode(code=flexcan.FLEXCAN_CODE_TX_INACTIVE)
            write_mb_data(self.emu, dev, 0, tx_data)

            # Change MB1 to be ready to receive messages
            mb1_addr = baseaddr + FLEXCAN_MB_OFFSET + (1 * FLEXCAN_MBx_SIZE)
            self.emu.writeMemValue(mb1_addr, flexcan.FLEXCAN_CODE_RX_EMPTY, 1)

            # Set CAN to NORMAL
            self.emu.writeMemValue(mcr_addr, 0, 4)

            # Should be no interrupts right now
            iflag1_val = self.emu.readMemValue(baseaddr + FLEXCAN_IFLAG1_OFFSET, 4)
            self.assertEqual(iflag1_val, 0x00000000, devname)

            # single step 1 instruction, ensure no interrupts happen
            self.emu.stepi()
            cur_pc = pc + 4
            self.assertEqual(self.emu.getProgramCounter(), cur_pc, devname)
            self.assertEqual(len(self.emu.mcu_intc.pending), 0, devname)
            self.assertEqual(self.emu.intc._cur_exc, None, devname)

            # Confirm that INTC CPR is 0
            self.assertEqual(self.emu.readMemValue(INTC_CPR_ADDR, 4), 0, devname)

            #### Tx CAN message to external client ####
            logger.info('Tx CAN TEST')

            # Transmit MB0
            mb0_addr = baseaddr + FLEXCAN_MB_OFFSET
            self.emu.writeMemValue(mb0_addr, flexcan.FLEXCAN_CODE_TX_ACTIVE, 1)

            # single step and ensure we enter the MB0 interrupt handler, just
            # after the first instruction in the handler
            self.emu.stepi()
            self.assertEqual(self.emu.getProgramCounter(), mb0_handler_addr, devname)
            self.assertEqual(len(self.emu.mcu_intc.pending), 1, devname)
            self.assertEqual(self.emu.intc._cur_exc, mb0_int, devname)

            # Because we are using hardware vectoring the INTC CPR should
            # automatically have escalated to the priority of the CANx MB0
            # interrupt
            self.assertEqual(self.emu.readMemValue(INTC_CPR_ADDR, 4), 2, devname)

            # Both the MB0 and MB1 interrupts should have happened because the
            # self-reception of messages is not disabled (MCR[SRX_DIS] = 0)
            iflag1_val = self.emu.readMemValue(baseaddr + FLEXCAN_IFLAG1_OFFSET, 4)
            self.assertEqual(iflag1_val, 0x00000003, devname)
            self.emu.writeMemValue(baseaddr + FLEXCAN_IFLAG1_OFFSET, 0x00000001, 4)
            iflag1_val = self.emu.readMemValue(baseaddr + FLEXCAN_IFLAG1_OFFSET, 4)
            self.assertEqual(iflag1_val, 0x00000002, devname)

            # To mimic the way an ISR should work write to EOIR now
            self.emu.writeMemValue(INTC_EOIR_ADDR, 0x00000000, 4)

            # Writing to INTC EOIR should have returned CPR to 0
            self.assertEqual(self.emu.readMemValue(INTC_CPR_ADDR, 4), 0, devname)

            # Step one more time and the RFI instruction should return execution
            # to the previous PC, but the loopback Rx message ISR should now be
            # pending
            self.emu.stepi()
            self.assertEqual(self.emu.getProgramCounter(), cur_pc, devname)
            # The loopback Rx interrupt should be pending now
            self.assertEqual(len(self.emu.mcu_intc.pending), 1, devname)
            # But it is not yet being processed
            self.assertEqual(self.emu.intc._cur_exc, None, devname)

            # single step and ensure we enter the MB1 interrupt handler, just
            # after the first instruction in the handler
            self.emu.stepi()
            self.assertEqual(self.emu.getProgramCounter(), mb1_handler_addr, devname)
            # Now that the external interrupt is being processed there is no
            # longer 1 pending PPC Exception
            self.assertEqual(len(self.emu.mcu_intc.pending), 0, devname)
            self.assertEqual(self.emu.intc._cur_exc, mb1_int, devname)

            # Confirm INTC CPR is now the MB1 priority
            self.assertEqual(self.emu.readMemValue(INTC_CPR_ADDR, 4), 1, devname)

            # Clear the interrupt flag
            iflag1_val = self.emu.readMemValue(baseaddr + FLEXCAN_IFLAG1_OFFSET, 4)
            self.assertEqual(iflag1_val, 0x00000002, devname)
            self.emu.writeMemValue(baseaddr + FLEXCAN_IFLAG1_OFFSET, 0x00000002, 4)
            iflag1_val = self.emu.readMemValue(baseaddr + FLEXCAN_IFLAG1_OFFSET, 4)
            self.assertEqual(iflag1_val, 0x00000000, devname)

            # Verify the received message data (this should match the message
            # that was transmitted from MB0
            mb1_idx = 1 * FLEXCAN_MBx_SIZE
            rcvd_msg = flexcan.CanMsg.from_mb(self.emu.can[dev].registers.mb.value, offset=mb1_idx)
            self.assertEqual(rcvd_msg, tx_msg, devname)

            # To mimic the way an ISR should work write to EOIR now
            self.emu.writeMemValue(INTC_EOIR_ADDR, 0x00000000, 4)

            # Writing to INTC EOIR should have returned CPR to 0
            self.assertEqual(self.emu.readMemValue(INTC_CPR_ADDR, 4), 0, devname)

            # Step one more time and the RFI instruction should return execution
            # to the previous PC
            self.emu.stepi()
            self.assertEqual(self.emu.getProgramCounter(), cur_pc, devname)
            self.assertEqual(len(self.emu.mcu_intc.pending), 0, devname)
            self.assertEqual(self.emu.intc._cur_exc, None, devname)

            # Ensure that this message was correctly received by the client
            self.assertEqual(client.recv(), tx_msg, devname)

            #### Rx CAN message from external client ####
            logger.info('Rx CAN TEST')

            # Return MB1 to EMPTY
            mb1_addr = baseaddr + FLEXCAN_MB_OFFSET + (1 * FLEXCAN_MBx_SIZE)
            self.emu.writeMemValue(mb1_addr, flexcan.FLEXCAN_CODE_RX_EMPTY, 1)

            # Send a message from the client
            client.send(rx_msg)

            # single step and ensure we enter the MB1 interrupt handler, just
            # after the first instruction in the handler
            self.emu.stepi()

            # It is very possible that the message sent from the client won't
            # have been received by the IO thread and queued before the emulator
            # stepi() function has passed that part of the code, so the PC is
            # most likely cur_pc+4 (8) and not in the MB1 ISR yet.
            #
            # It will likely take a few NOP instructions before the received
            # message is fully queued
            pc = self.emu.getProgramCounter()
            while pc != mb1_handler_addr:
                cur_pc = pc

                # NOP processing is too fast so force a small delay here to let
                # network happen
                time.sleep(0.001)

                # The message has not yet been processed by the CAN peripheral
                # which means that the exception count is still 0
                # TODO: this may be 0 or 1 depending on if the exception is
                # queued yet
                #self.assertEqual(len(self.emu.mcu_intc.pending), 0, devname)
                self.assertEqual(self.emu.intc._cur_exc, None, devname)

                # one more instruction
                self.emu.stepi()
                pc = self.emu.getProgramCounter()

            self.assertEqual(self.emu.getProgramCounter(), mb1_handler_addr, devname)
            # Now that the external interrupt is being processed there is no
            # longer 1 pending PPC Exception
            self.assertEqual(len(self.emu.mcu_intc.pending), 0, devname)
            self.assertEqual(self.emu.intc._cur_exc, mb1_int, devname)

            # Confirm INTC CPR is now the MB1 priority
            self.assertEqual(self.emu.readMemValue(INTC_CPR_ADDR, 4), 1, devname)

            # Clear the interrupt flag
            iflag1_val = self.emu.readMemValue(baseaddr + FLEXCAN_IFLAG1_OFFSET, 4)
            self.assertEqual(iflag1_val, 0x00000002, devname)
            self.emu.writeMemValue(baseaddr + FLEXCAN_IFLAG1_OFFSET, 0x00000002, 4)
            iflag1_val = self.emu.readMemValue(baseaddr + FLEXCAN_IFLAG1_OFFSET, 4)
            self.assertEqual(iflag1_val, 0x00000000, devname)

            # Verify the received message data (this should match the message
            # that was transmitted from the client
            mb1_idx = 1 * FLEXCAN_MBx_SIZE
            rcvd_msg = flexcan.CanMsg.from_mb(self.emu.can[dev].registers.mb.value, offset=mb1_idx)
            self.assertEqual(rcvd_msg, rx_msg, devname)

            # To mimic the way an ISR should work write to EOIR now
            self.emu.writeMemValue(INTC_EOIR_ADDR, 0x00000000, 4)

            # Writing to INTC EOIR should have returned CPR to 0
            self.assertEqual(self.emu.readMemValue(INTC_CPR_ADDR, 4), 0, devname)

            # Step one more time and the RFI instruction should return execution
            # to the previous PC
            self.emu.stepi()
            self.assertEqual(self.emu.getProgramCounter(), cur_pc, devname)
            self.assertEqual(len(self.emu.mcu_intc.pending), 0, devname)
            self.assertEqual(self.emu.intc._cur_exc, None, devname)

            client.close()

            # Save the current PC for the next loop
            pc = self.emu.getProgramCounter()
