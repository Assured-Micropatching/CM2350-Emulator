import os
import time
import random
import struct
import unittest

from .. import intc_exc, mmio
from ..peripherals import flexcan
from ..ppc_peripherals import ExternalIOClient

from .helpers import MPC5674_Test, initLogging

import logging
logger = logging.getLogger(__name__)
#initLogging(logger)


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
    accurate_timing = True

    def set_sysclk_240mhz(self):
        # Default PLL clock based on the PCB params selected for these tests is
        # 60 MHz
        self.assertEqual(self.emu.config.project.MPC5674.FMPLL.extal, 40000000)
        self.assertEqual(self.emu.getClock('pll'), 60000000.0)

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
        self.assertEqual(self.emu.getClock('pll'), 240000000.0)

        # Now set the SIU peripheral configuration to allow the CPU frequency to
        # be double the peripheral speed (otherwise the maximum bus/peripheral
        # speed is 132 MHz

        # SYSDIV[IPCLKDIV] = 0
        # SYSDIV[BYPASS] = 1
        self.emu.writeMemValue(0xC3F909A0, 0x00000010, 4)
        self.assertEqual(self.emu.getClock('periph'), 120000000.0)

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

    def test_flexcan_mcr_defaults(self):
        for idx in range(4):
            devname, baseaddr = FLEXCAN_DEVICES[idx]
            self.assertEqual(self.emu.can[idx].devname, devname)

            addr = baseaddr + FLEXCAN_MCR_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), FLEXCAN_MCR_DEFAULT_BYTES)
            self.assertEqual(self.emu.readMemValue(addr, 4), FLEXCAN_MCR_DEFAULT)
            self.assertEqual(self.emu.can[idx].registers.mcr.mdis, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.frz, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.fen, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.halt, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.not_rdy, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.soft_rst, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.frz_ack, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.supv, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.wrn_en, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.mdisack, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.doze, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.srx_dis, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.mbfen, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.lprio_en, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.aen, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.idam, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.maxmb, 0x0F)

    def test_flexcan_ctrl_defaults(self):
        for idx in range(4):
            _, baseaddr = FLEXCAN_DEVICES[idx]
            addr = baseaddr + FLEXCAN_CTRL_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')
            self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000)
            self.assertEqual(self.emu.can[idx].registers.ctrl.presdiv, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.rjw, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.pseg1, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.pseg2, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.boff_msk, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.err_msk, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.clk_src, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lpb, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.twrn_msk, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.rwrn_msk, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.smp, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.boff_rec, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.tsyn, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lbuf, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lom, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.propseg, 0)

    def test_flexcan_timer_defaults(self):
        test_addrs = [a + FLEXCAN_TIMER_OFFSET for _, a in FLEXCAN_DEVICES]
        for addr in test_addrs:
            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')
            self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000)

        # Start the timer for each peripheral, ensure that the timer value has
        # changed and that none of the other CAN device timers moved

        # CAN A
        self.emu.can[0]._timer.start()
        self.emu.sleep(0.1)
        self.assertNotEqual(self.emu.readMemory(test_addrs[0], 4), b'\x00\x00\x00\x00')
        self.assertNotEqual(self.emu.readMemValue(test_addrs[0], 4), 0x00000000)

        self.assertEqual(self.emu.readMemory(test_addrs[1], 4), b'\x00\x00\x00\x00')
        self.assertEqual(self.emu.readMemValue(test_addrs[1], 4), 0x00000000)
        self.assertEqual(self.emu.readMemory(test_addrs[2], 4), b'\x00\x00\x00\x00')
        self.assertEqual(self.emu.readMemValue(test_addrs[2], 4), 0x00000000)
        self.assertEqual(self.emu.readMemory(test_addrs[3], 4), b'\x00\x00\x00\x00')
        self.assertEqual(self.emu.readMemValue(test_addrs[3], 4), 0x00000000)

        self.emu.can[0]._timer.stop()
        self.assertEqual(self.emu.readMemory(test_addrs[0], 4), b'\x00\x00\x00\x00')
        self.assertEqual(self.emu.readMemValue(test_addrs[0], 4), 0x00000000)

        # CAN B
        self.emu.can[1]._timer.start()
        self.emu.sleep(0.1)
        self.assertNotEqual(self.emu.readMemory(test_addrs[1], 4), b'\x00\x00\x00\x00')
        self.assertNotEqual(self.emu.readMemValue(test_addrs[1], 4), 0x00000000)

        self.assertEqual(self.emu.readMemory(test_addrs[0], 4), b'\x00\x00\x00\x00')
        self.assertEqual(self.emu.readMemValue(test_addrs[0], 4), 0x00000000)
        self.assertEqual(self.emu.readMemory(test_addrs[2], 4), b'\x00\x00\x00\x00')
        self.assertEqual(self.emu.readMemValue(test_addrs[2], 4), 0x00000000)
        self.assertEqual(self.emu.readMemory(test_addrs[3], 4), b'\x00\x00\x00\x00')
        self.assertEqual(self.emu.readMemValue(test_addrs[3], 4), 0x00000000)

        self.emu.can[1]._timer.stop()
        self.assertEqual(self.emu.readMemory(test_addrs[1], 4), b'\x00\x00\x00\x00')
        self.assertEqual(self.emu.readMemValue(test_addrs[1], 4), 0x00000000)

        # CAN C
        self.emu.can[2]._timer.start()
        self.emu.sleep(0.1)
        self.assertNotEqual(self.emu.readMemory(test_addrs[2], 4), b'\x00\x00\x00\x00')
        self.assertNotEqual(self.emu.readMemValue(test_addrs[2], 4), 0x00000000)

        self.assertEqual(self.emu.readMemory(test_addrs[0], 4), b'\x00\x00\x00\x00')
        self.assertEqual(self.emu.readMemValue(test_addrs[0], 4), 0x00000000)
        self.assertEqual(self.emu.readMemory(test_addrs[1], 4), b'\x00\x00\x00\x00')
        self.assertEqual(self.emu.readMemValue(test_addrs[1], 4), 0x00000000)
        self.assertEqual(self.emu.readMemory(test_addrs[3], 4), b'\x00\x00\x00\x00')
        self.assertEqual(self.emu.readMemValue(test_addrs[3], 4), 0x00000000)

        self.emu.can[2]._timer.stop()
        self.assertEqual(self.emu.readMemory(test_addrs[2], 4), b'\x00\x00\x00\x00')
        self.assertEqual(self.emu.readMemValue(test_addrs[2], 4), 0x00000000)

        # CAN D
        self.emu.can[3]._timer.start()
        self.emu.sleep(0.1)
        self.assertNotEqual(self.emu.readMemory(test_addrs[3], 4), b'\x00\x00\x00\x00')
        self.assertNotEqual(self.emu.readMemValue(test_addrs[3], 4), 0x00000000)

        self.assertEqual(self.emu.readMemory(test_addrs[0], 4), b'\x00\x00\x00\x00')
        self.assertEqual(self.emu.readMemValue(test_addrs[0], 4), 0x00000000)
        self.assertEqual(self.emu.readMemory(test_addrs[1], 4), b'\x00\x00\x00\x00')
        self.assertEqual(self.emu.readMemValue(test_addrs[1], 4), 0x00000000)
        self.assertEqual(self.emu.readMemory(test_addrs[2], 4), b'\x00\x00\x00\x00')
        self.assertEqual(self.emu.readMemValue(test_addrs[2], 4), 0x00000000)

        self.emu.can[3]._timer.stop()
        self.assertEqual(self.emu.readMemory(test_addrs[3], 4), b'\x00\x00\x00\x00')
        self.assertEqual(self.emu.readMemValue(test_addrs[3], 4), 0x00000000)

    def test_flexcan_rxgmask_defaults(self):
        for idx in range(4):
            _, baseaddr = FLEXCAN_DEVICES[idx]
            addr = baseaddr + FLEXCAN_RXGMASK_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), b'\xff\xff\xff\xff')
            self.assertEqual(self.emu.readMemValue(addr, 4), 0xffffffff)
            self.assertEqual(self.emu.can[idx].registers.rxgmask, 0xffffffff)

    def test_flexcan_rx14mask_defaults(self):
        for idx in range(4):
            _, baseaddr = FLEXCAN_DEVICES[idx]
            addr = baseaddr + FLEXCAN_RX14MASK_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), b'\xff\xff\xff\xff')
            self.assertEqual(self.emu.readMemValue(addr, 4), 0xffffffff)
            self.assertEqual(self.emu.can[idx].registers.rx14mask, 0xffffffff)

    def test_flexcan_rx15mask_defaults(self):
        for idx in range(4):
            _, baseaddr = FLEXCAN_DEVICES[idx]
            addr = baseaddr + FLEXCAN_RX15MASK_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), b'\xff\xff\xff\xff')
            self.assertEqual(self.emu.readMemValue(addr, 4), 0xffffffff)
            self.assertEqual(self.emu.can[idx].registers.rx15mask, 0xffffffff)

    def test_flexcan_ecr_defaults(self):
        for idx in range(4):
            _, baseaddr = FLEXCAN_DEVICES[idx]
            addr = baseaddr + FLEXCAN_ECR_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')
            self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000)
            self.assertEqual(self.emu.can[idx].registers.ecr.tx_err, 0)
            self.assertEqual(self.emu.can[idx].registers.ecr.rx_err, 0)

    def test_flexcan_esr_defaults(self):
        for idx in range(4):
            _, baseaddr = FLEXCAN_DEVICES[idx]
            addr = baseaddr + FLEXCAN_ESR_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')
            self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000)
            self.assertEqual(self.emu.can[idx].registers.esr.twrn_int, 0)
            self.assertEqual(self.emu.can[idx].registers.esr.rwrn_int, 0)
            self.assertEqual(self.emu.can[idx].registers.esr.bit1_err, 0)
            self.assertEqual(self.emu.can[idx].registers.esr.bit0_err, 0)
            self.assertEqual(self.emu.can[idx].registers.esr.ack_err, 0)
            self.assertEqual(self.emu.can[idx].registers.esr.crc_err, 0)
            self.assertEqual(self.emu.can[idx].registers.esr.frm_err, 0)
            self.assertEqual(self.emu.can[idx].registers.esr.stf_err, 0)
            self.assertEqual(self.emu.can[idx].registers.esr.tx_wrn, 0)
            self.assertEqual(self.emu.can[idx].registers.esr.rx_wrn, 0)
            self.assertEqual(self.emu.can[idx].registers.esr.idle, 0)
            self.assertEqual(self.emu.can[idx].registers.esr.txrx, 0)
            self.assertEqual(self.emu.can[idx].registers.esr.flt_conf, 0)
            self.assertEqual(self.emu.can[idx].registers.esr.boff_int, 0)
            self.assertEqual(self.emu.can[idx].registers.esr.err_int, 0)

    def test_flexcan_imask_defaults(self):
        for idx in range(4):
            _, baseaddr = FLEXCAN_DEVICES[idx]
            addr1 = baseaddr + FLEXCAN_IMASK1_OFFSET
            addr2 = baseaddr + FLEXCAN_IMASK2_OFFSET

            # IMASK1
            self.assertEqual(self.emu.readMemory(addr1, 4), b'\x00\x00\x00\x00')
            self.assertEqual(self.emu.readMemValue(addr1, 4), 0x00000000)
            self.assertEqual(self.emu.can[idx].registers.imask1, 0x00000000)

            self.emu.writeMemory(addr1, b'\xff\xff\xff\xff')
            self.assertEqual(self.emu.readMemory(addr1, 4), b'\xff\xff\xff\xff')
            self.assertEqual(self.emu.readMemValue(addr1, 4), 0xffffffff)
            self.assertEqual(self.emu.can[idx].registers.imask1, 0xffffffff)

            # IMASK2
            self.assertEqual(self.emu.readMemory(addr2, 4), b'\x00\x00\x00\x00')
            self.assertEqual(self.emu.readMemValue(addr2, 4), 0x00000000)
            self.assertEqual(self.emu.can[idx].registers.imask2, 0x00000000)

            self.emu.writeMemory(addr2, b'\xff\xff\xff\xff')
            self.assertEqual(self.emu.readMemory(addr2, 4), b'\xff\xff\xff\xff')
            self.assertEqual(self.emu.readMemValue(addr2, 4), 0xffffffff)
            self.assertEqual(self.emu.can[idx].registers.imask2, 0xffffffff)

    def test_flexcan_iflag_defaults(self):
        for idx in range(4):
            _, baseaddr = FLEXCAN_DEVICES[idx]
            addr1 = baseaddr + FLEXCAN_IFLAG1_OFFSET
            addr2 = baseaddr + FLEXCAN_IFLAG2_OFFSET

            # IFLAG1
            self.assertEqual(self.emu.readMemory(addr1, 4), b'\x00\x00\x00\x00')
            self.assertEqual(self.emu.readMemValue(addr1, 4), 0x00000000)
            self.assertEqual(self.emu.can[idx].registers.iflag1, 0x00000000)

            # Ensure the flag1 register are w1c and can't be set by writing
            self.emu.writeMemory(addr1, b'\xff\xff\xff\xff')
            self.assertEqual(self.emu.readMemory(addr1, 4), b'\x00\x00\x00\x00')
            self.assertEqual(self.emu.readMemValue(addr1, 4), 0x00000000)
            self.assertEqual(self.emu.can[idx].registers.iflag1, 0x00000000)

            self.emu.can[idx].registers.vsOverrideValue('iflag1', 0xffffffff)

            self.assertEqual(self.emu.readMemory(addr1, 4), b'\xff\xff\xff\xff')
            self.assertEqual(self.emu.readMemValue(addr1, 4), 0xffffffff)
            self.assertEqual(self.emu.can[idx].registers.iflag1, 0xffffffff)

            # Clear some flags
            self.emu.writeMemory(addr1, b'\xa5\xa5\xa5\xa5')
            self.assertEqual(self.emu.readMemory(addr1, 4), b'\x5a\x5a\x5a\x5a')
            self.assertEqual(self.emu.readMemValue(addr1, 4), 0x5a5a5a5a)
            self.assertEqual(self.emu.can[idx].registers.iflag1, 0x5a5a5a5a)

            # IFLAG2
            self.assertEqual(self.emu.readMemory(addr2, 4), b'\x00\x00\x00\x00')
            self.assertEqual(self.emu.readMemValue(addr2, 4), 0x00000000)
            self.assertEqual(self.emu.can[idx].registers.iflag2, 0x00000000)

            # Ensure the flag2 register are w1c and can't be set by writing
            self.emu.writeMemory(addr2, b'\xff\xff\xff\xff')
            self.assertEqual(self.emu.readMemory(addr2, 4), b'\x00\x00\x00\x00')
            self.assertEqual(self.emu.readMemValue(addr2, 4), 0x00000000)
            self.assertEqual(self.emu.can[idx].registers.iflag2, 0x00000000)

            self.emu.can[idx].registers.vsOverrideValue('iflag2', 0xffffffff)

            self.assertEqual(self.emu.readMemory(addr2, 4), b'\xff\xff\xff\xff')
            self.assertEqual(self.emu.readMemValue(addr2, 4), 0xffffffff)
            self.assertEqual(self.emu.can[idx].registers.iflag2, 0xffffffff)

            # Clear some flags
            self.emu.writeMemory(addr2, b'\x5a\x5a\x5a\x5a')
            self.assertEqual(self.emu.readMemory(addr2, 4), b'\xa5\xa5\xa5\xa5')
            self.assertEqual(self.emu.readMemValue(addr2, 4), 0xa5a5a5a5)
            self.assertEqual(self.emu.can[idx].registers.iflag2, 0xa5a5a5a5)

    def test_flexcan_modes(self):
        for idx in range(4):
            devname, baseaddr = FLEXCAN_DEVICES[idx]
            self.assertEqual(self.emu.can[idx].devname, devname)

            mcr_addr = baseaddr + FLEXCAN_MCR_OFFSET
            ctrl_addr = baseaddr + FLEXCAN_CTRL_OFFSET

            # Should start off in DISABLE, but the MCR[MDIS] bit isn't set
            self.assertEqual(self.emu.can[idx].mode, flexcan.FLEXCAN_MODE.DISABLE)
            self.assertEqual(self.emu.can[idx].registers.mcr.mdis, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.frz, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.halt, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.not_rdy, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.frz_ack, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.mdisack, 1)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lpb, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lom, 0)

            # Writing the same value back to MCR should put the peripheral into
            # FREEZE, MCR[MDISACK] should now be cleared
            mcr_val = self.emu.readMemValue(mcr_addr, 4)
            self.emu.writeMemValue(mcr_addr, mcr_val, 4)

            self.assertEqual(self.emu.can[idx].mode, flexcan.FLEXCAN_MODE.FREEZE)
            self.assertEqual(self.emu.can[idx].registers.mcr.mdis, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.frz, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.halt, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.not_rdy, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.frz_ack, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.mdisack, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lpb, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lom, 0)

            # Writing only the FRZ and HALT bits should result in no change
            self.emu.writeMemValue(mcr_addr, FLEXCAN_MCR_FRZ_MASK | FLEXCAN_MCR_HALT_MASK, 4)

            self.assertEqual(self.emu.can[idx].mode, flexcan.FLEXCAN_MODE.FREEZE)
            self.assertEqual(self.emu.can[idx].registers.mcr.mdis, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.frz, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.halt, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.not_rdy, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.frz_ack, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.mdisack, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lpb, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lom, 0)

            # Clearing the MCR[HALT] bit should move the device to NORMAL mode
            # and clear MCR[NOT_RDY] and MCR[FRZ_ACK]
            self.emu.writeMemValue(mcr_addr, FLEXCAN_MCR_FRZ_MASK, 4)

            self.assertEqual(self.emu.can[idx].mode, flexcan.FLEXCAN_MODE.NORMAL)
            self.assertEqual(self.emu.can[idx].registers.mcr.mdis, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.frz, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.halt, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.not_rdy, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.frz_ack, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.mdisack, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lpb, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lom, 0)

            # Set MCR[MDIS] to move back to disabled, this should also set
            # MCR[NOT_RDY] and MCR[MDISACK]
            #
            # MCR[FRZ] is also cleared by this change because the FRZ mask is
            # not written in this step.
            self.emu.writeMemValue(mcr_addr, FLEXCAN_MCR_MDIS_MASK, 4)

            self.assertEqual(self.emu.can[idx].mode, flexcan.FLEXCAN_MODE.DISABLE)
            self.assertEqual(self.emu.can[idx].registers.mcr.mdis, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.frz, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.halt, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.not_rdy, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.frz_ack, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.mdisack, 1)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lpb, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lom, 0)

            # Clearing MCR[MDIS] moves back to NORMAL
            self.emu.writeMemValue(mcr_addr, 0, 4)

            self.assertEqual(self.emu.can[idx].mode, flexcan.FLEXCAN_MODE.NORMAL)
            self.assertEqual(self.emu.can[idx].registers.mcr.mdis, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.frz, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.halt, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.not_rdy, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.frz_ack, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.mdisack, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lpb, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lom, 0)

            # Setting only MCR[HALT] should not change anything since the
            # MCR[FRZ] bit is not set.
            self.emu.writeMemValue(mcr_addr, FLEXCAN_MCR_HALT_MASK, 4)

            self.assertEqual(self.emu.can[idx].mode, flexcan.FLEXCAN_MODE.NORMAL)
            self.assertEqual(self.emu.can[idx].registers.mcr.mdis, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.frz, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.halt, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.not_rdy, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.frz_ack, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.mdisack, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lpb, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lom, 0)

            # Setting both HALT and FRZ moves the device back to FREEZE
            self.emu.writeMemValue(mcr_addr, FLEXCAN_MCR_FRZ_MASK | FLEXCAN_MCR_HALT_MASK, 4)

            self.assertEqual(self.emu.can[idx].mode, flexcan.FLEXCAN_MODE.FREEZE)
            self.assertEqual(self.emu.can[idx].registers.mcr.mdis, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.frz, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.halt, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.not_rdy, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.frz_ack, 1)
            self.assertEqual(self.emu.can[idx].registers.mcr.mdisack, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lpb, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lom, 0)

            # Test out loopback and listen-only modes but first move to FREEZE.
            # this step isn't currently necessary but it is the more "correct"
            # way to change modes.

            # Setting CTRL[LPB] should enable loopback mode once the device is
            # back to NORMAL mode.
            self.emu.writeMemValue(ctrl_addr, FLEXCAN_CTRL_LPB_MASK, 4)
            self.emu.writeMemValue(mcr_addr, 0, 4)

            self.assertEqual(self.emu.can[idx].mode, flexcan.FLEXCAN_MODE.LOOP_BACK)
            self.assertEqual(self.emu.can[idx].registers.mcr.mdis, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.frz, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.halt, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.not_rdy, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.frz_ack, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.mdisack, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lpb, 1)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lom, 0)

            # Back to FREEZE
            self.emu.writeMemValue(mcr_addr, FLEXCAN_MCR_FRZ_MASK | FLEXCAN_MCR_HALT_MASK, 4)
            self.assertEqual(self.emu.can[idx].mode, flexcan.FLEXCAN_MODE.FREEZE)

            # Setting LOM and LPB should listen-only mode once the device is
            # back to NORMAL mode.
            self.emu.writeMemValue(ctrl_addr, FLEXCAN_CTRL_LPB_MASK | FLEXCAN_CTRL_LOM_MASK, 4)
            self.emu.writeMemValue(mcr_addr, 0, 4)

            self.assertEqual(self.emu.can[idx].mode, flexcan.FLEXCAN_MODE.LISTEN_ONLY)
            self.assertEqual(self.emu.can[idx].registers.mcr.mdis, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.frz, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.halt, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.not_rdy, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.frz_ack, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.mdisack, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lpb, 1)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lom, 1)

            # Back to FREEZE
            self.emu.writeMemValue(mcr_addr, FLEXCAN_MCR_FRZ_MASK | FLEXCAN_MCR_HALT_MASK, 4)
            self.assertEqual(self.emu.can[idx].mode, flexcan.FLEXCAN_MODE.FREEZE)

            # Setting LOM will also set the device to listen-only mode
            self.emu.writeMemValue(ctrl_addr, FLEXCAN_CTRL_LOM_MASK, 4)
            self.emu.writeMemValue(mcr_addr, 0, 4)

            self.assertEqual(self.emu.can[idx].mode, flexcan.FLEXCAN_MODE.LISTEN_ONLY)
            self.assertEqual(self.emu.can[idx].registers.mcr.mdis, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.frz, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.halt, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.not_rdy, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.frz_ack, 0)
            self.assertEqual(self.emu.can[idx].registers.mcr.mdisack, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lpb, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.lom, 1)

    def test_flexcan_speed(self):
        for idx in range(4):
            devname, baseaddr = FLEXCAN_DEVICES[idx]
            self.assertEqual(self.emu.can[idx].devname, devname)
            ctrl_addr = baseaddr + FLEXCAN_CTRL_OFFSET

            # With the default clock source of EXTAL, and PRESDIV the SCLK is
            # 40 MHz, and then the default bitrate is 10 Mbit/sec
            self.assertEqual(self.emu.can[idx].speed, 10000000)
            self.assertEqual(self.emu.can[idx].registers.ctrl.presdiv, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.pseg1, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.pseg2, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.clk_src, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.propseg, 0)

            # With clock source of the bus/internal PLL, and PRESDIV the SCLK is
            # 30 MHz, and then the default bitrate is 7.5 Mbit/sec
            self.emu.writeMemValue(ctrl_addr, FLEXCAN_CTRL_CLK_SRC_MASK, 4)
            self.assertEqual(self.emu.can[idx].speed, 7500000)
            self.assertEqual(self.emu.can[idx].registers.ctrl.presdiv, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.pseg1, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.pseg2, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.clk_src, 1)
            self.assertEqual(self.emu.can[idx].registers.ctrl.propseg, 0)

        # Configure FMPLL to an appropriately reasonable example valid baud rate
        self.set_sysclk_240mhz()

        for idx in range(4):
            # Force the CAN device to update the clock speed
            self.emu.can[idx].updateSpeed()

            _, baseaddr = FLEXCAN_DEVICES[idx]
            ctrl_addr = baseaddr + FLEXCAN_CTRL_OFFSET

            # With clock source of the bus/internal PLL, and PRESDIV the SCLK is
            # 120 MHz, and then the default bitrate is 30 Mbit/sec
            self.assertEqual(self.emu.can[idx].speed, 30000000)
            self.assertEqual(self.emu.can[idx].registers.ctrl.presdiv, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.pseg1, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.pseg2, 0)
            self.assertEqual(self.emu.can[idx].registers.ctrl.clk_src, 1)
            self.assertEqual(self.emu.can[idx].registers.ctrl.propseg, 0)

            # A baudrate of 250000 can be achieved in a few ways, but one way
            # is:
            #   sclk = 120000000 / (29+1)
            #   tq = sclk / (1 + (4+1) + (7+1) + (1+1))
            val = (29 << FLEXCAN_CTRL_PRESDIV_SHIFT) | \
                    (7 << FLEXCAN_CTRL_PSEG1_SHIFT) | \
                    (1 << FLEXCAN_CTRL_PSEG2_SHIFT) | \
                    (FLEXCAN_CTRL_CLK_SRC_MASK) | \
                    (4 << FLEXCAN_CTRL_PROPSEG_SHIFT)
            self.emu.writeMemValue(ctrl_addr, val, 4)

            # - CTRL[CLK_SRC] set, the bus/internal PLL
            # - CTRL[PRESDIV] is 29
            # - CTRL[PSEG1] is 7
            # - CTRL[PSEG2] is 1
            # - CTRL[PROPSEG] is 4
            # SCLK is 4 MHz, and the bitrate (tq) is 250000 Kbit/sec
            self.assertEqual(self.emu.can[idx].speed, 250000)
            self.assertEqual(self.emu.can[idx].registers.ctrl.presdiv, 29)
            self.assertEqual(self.emu.can[idx].registers.ctrl.pseg1, 7)
            self.assertEqual(self.emu.can[idx].registers.ctrl.pseg2, 1)
            self.assertEqual(self.emu.can[idx].registers.ctrl.clk_src, 1)
            self.assertEqual(self.emu.can[idx].registers.ctrl.propseg, 4)

    def test_flexcan_timer(self):
        # Set standard bus speeds
        self.set_baudrates()

        # at 1Mbps run for 0.05 msec CAN A should have a value of approximately
        # 50000. Since the scaling time for this test is set to 0.1 set each
        # bus to NORMAL and then wait 0.5 seconds before collecting the end
        # timer values.
        for idx in range(4):
            devname, baseaddr = FLEXCAN_DEVICES[idx]
            mcr_addr = baseaddr + FLEXCAN_MCR_OFFSET
            timer_addr = baseaddr + FLEXCAN_TIMER_OFFSET

            # Expected ticks (limit to 16 bits):
            expected_val = int(self.emu.can[idx].speed * 0.5) & 0xFFFF

            # Margin of error is approximately 0.005 (so speed * 0.005)
            margin = self.emu.can[idx].speed * 0.005

            self.emu.writeMemValue(mcr_addr, 0, 4)

            self.emu.sleep(0.5)
            val = self.emu.readMemValue(timer_addr, 4)

            self.assert_timer_within_range(val, expected_val, margin, maxval=0xFFFF, msg=devname)

            self.assertEqual(self.emu.can[idx].mode, flexcan.FLEXCAN_MODE.NORMAL, devname)
            self.emu.writeMemValue(mcr_addr, FLEXCAN_MCR_MDIS_MASK, 4)
            self.assertEqual(self.emu.can[idx].mode, flexcan.FLEXCAN_MODE.DISABLE, devname)
            self.assertEqual(self.emu.readMemValue(timer_addr, 4), 0, devname)

    def test_flexcan_tx(self):
        # Set standard bus speeds
        self.set_baudrates()

        # Only enable some of the mailbox interrupts: 0-7, 24-31, 32-47
        enabled_intrs = list(range(0, 8)) + list(range(24, 32)) + list(range(32, 48))

        # Send a message from each bus and ensure the timestamp is correctly
        # updated, wait 0.10 seconds before sending and then check that the time
        # stamp is correct.
        for dev in range(4):
            devname, baseaddr = FLEXCAN_DEVICES[dev]
            mcr_addr = baseaddr + FLEXCAN_MCR_OFFSET
            timer_addr = baseaddr + FLEXCAN_TIMER_OFFSET

            # Generate one message for each mailbox
            msgs = [generate_msg() for i in range(FLEXCAN_NUM_MBs)]

            # Only enable some of the mailbox interrupts: 0-7, 24-31, 32-47
            int_enabled_mbs = list(range(0, 8)) + list(range(24, 48))
            imask1_val = 0xFF0000FF
            imask2_val = 0x0000FFFF
            self.emu.writeMemValue(baseaddr + FLEXCAN_IMASK1_OFFSET, imask1_val, 4)
            self.emu.writeMemValue(baseaddr + FLEXCAN_IMASK2_OFFSET, imask2_val, 4)

            # Change mode to NORMAL, the timer now starts moving, but disable
            # self-reception of messages to make this test simpler
            self.emu.writeMemValue(mcr_addr, FLEXCAN_MCR_SRX_DIS_MASK, 4)
            start_time = self.emu.systime()

            # Place messages into each mailbox and mark the mailbox as inactive
            for mb in range(FLEXCAN_NUM_MBs):
                # Generate a random priority (0 to 7) to ensure that the
                # priority field is correctly removed during transmission
                prio = random.randrange(0, 8)
                data = msgs[mb].encode(code=flexcan.FLEXCAN_CODE_TX_INACTIVE, prio=prio)
                write_mb_data(self.emu, dev, mb, data)

                # Ensure that the written data matches what should have been
                # written
                testmsg = '%s[%d]' % (devname, mb)
                start = baseaddr + FLEXCAN_MB_OFFSET + (mb * FLEXCAN_MBx_SIZE)
                self.assertEqual(self.emu.readMemory(start, FLEXCAN_MBx_SIZE), data, msg=testmsg)

            # Ensure that no messages have been transmitted and there are no
            # pending interrupts
            self.assertEqual(self.emu.can[dev].getTransmittedObjs(), [], devname)
            self.assertEqual(self._getPendingExceptions(), [], msg=devname)

            # Wait some short time to let the timer run for a bit
            self.emu.sleep(0.5)

            # For each CAN device only transmit from some of them:
            #   CAN A: tx in all mailboxes
            #   CAN B: tx in every other mailbox
            #   CAN C: tx in every third mailbox
            #   CAN D: tx in every fourth mailbox
            tx_mbs = list(range(0, FLEXCAN_NUM_MBs, dev+1))

            # Randomize the tx mailbox order now
            random.shuffle(tx_mbs)

            # Duplicate exception events are not triggered even if the mailbox 
            # is different, the software will use one exception handler to check 
            # and service all mailboxes that are covered by a particular 
            # interrupt source.
            tx_int_srcs = []
            for mb in tx_mbs:
                # Only add interrupt sources if the interrupts are enabled for 
                # this mailbox
                if mb in int_enabled_mbs:
                    exc = get_int(dev, mb)
                    # Don't build duplicate interrupt sources into the list
                    if exc not in tx_int_srcs:
                        tx_int_srcs.append(exc)

            tx_times = {}

            # Zero out the timer register.
            self.emu.writeMemValue(timer_addr, 0, 4)

            # Send the messages
            for mb in tx_mbs:
                # Save the timestamp that the message was sent
                addr = baseaddr + FLEXCAN_MB_OFFSET + (mb * FLEXCAN_MBx_SIZE)
                self.emu.writeMemValue(addr, flexcan.FLEXCAN_CODE_TX_ACTIVE, 1)
                tx_times[mb] = self.emu.systime()

            # Now read all queued transmit messages
            txd_msgs = self.emu.can[dev].getTransmittedObjs()
            self.assertEqual(len(txd_msgs), len(tx_mbs), msg=devname)

            # Ensure the correct IFLAGs are set
            iflag1_val = self.emu.readMemValue(baseaddr + FLEXCAN_IFLAG1_OFFSET, 4)
            iflag2_val = self.emu.readMemValue(baseaddr + FLEXCAN_IFLAG2_OFFSET, 4)

            if dev == 0:
                # For CAN A every mailbox should have sent a message
                self.assertEqual(iflag1_val, 0xFFFFFFFF, msg=devname)
                self.assertEqual(iflag2_val, 0xFFFFFFFF, msg=devname)
            elif dev == 1:
                # For CAN B every other mailbox should have sent a message
                self.assertEqual(iflag1_val, 0x55555555, msg=devname)
                self.assertEqual(iflag2_val, 0x55555555, msg=devname)
            elif dev == 2:
                # For CAN C every third mailbox should have sent a message
                self.assertEqual(iflag1_val, 0x49249249, msg=devname)
                self.assertEqual(iflag2_val, 0x92492492, msg=devname)
            elif dev == 3:
                # For CAN D every fourth mailbox should have sent a message
                self.assertEqual(iflag1_val, 0x11111111, msg=devname)
                self.assertEqual(iflag2_val, 0x11111111, msg=devname)

            # calculate how many interrupts there should be and correlate the
            # interrupts to the transmit AND interrupt enabled mailboxes
            tx_int_mbs = []
            for mb in range(FLEXCAN_NUM_MBs):
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
                    self.assertIn(mb, tx_mbs, msg=testmsg)
                    if mask & mb_mask:
                        tx_int_mbs.append(mb)
                else:
                    self.assertNotIn(mb, tx_mbs, msg=testmsg)

            # Unfortunately the IO thread has a pretty wide variation on when 
            # things are received and processed so the margin has to be larger 
            # for this test.
            margin = self.emu.can[dev].speed * 0.0300

            time.sleep(1)

            # Confirm that the order of the generated interrupts matches both
            # the order of the transmitted messages and the interrupt source for
            # the Tx mailbox
            excs = self._getPendingExceptions()

            self.assertEqual(len(excs), len(tx_int_srcs), msg=devname)
            self.assertEqual(excs, tx_int_srcs, msg=devname)

            txd_msgs_iter = iter(txd_msgs)

            # Iterate through the mailboxes based on the order messages were
            # transmitted
            for i, mb in enumerate(tx_mbs):
                testmsg = '%s[%d] (%d of %d)' % (devname, mb, i, len(tx_mbs))

                # Confirm that the message contents are correct
                txd_msg = next(txd_msgs_iter)
                self.assertEqual(txd_msg, msgs[mb], msg=testmsg)

                # Confirm that the timestamp is accurate
                tx_delay = tx_times[mb] - start_time
                expected_ticks = int(self.emu.can[dev].speed * tx_delay) & 0xFFFF

                ts_offset = (mb * FLEXCAN_MBx_SIZE) + 2
                timestamp = struct.unpack_from('>H', self.emu.can[dev].registers.mb.value, ts_offset)[0]

                self.assert_timer_within_range(timestamp, expected_ticks, margin, maxval=0xFFFF, msg=testmsg)

            # Now ensure that all mailboxes that were not in the list are still
            # inactive
            for mb in range(FLEXCAN_NUM_MBs):
                if mb not in tx_mbs:
                    testmsg = '%s[%d]' % (devname, mb)

                    # Ensure that inactive mailboxes have the same data and
                    # still have a CODE of TX_INACTIVE, and the TIMESTAMP is
                    # still 0
                    code_offset = mb * FLEXCAN_MBx_SIZE
                    code = self.emu.can[dev].registers.mb[code_offset]
                    self.assertEqual(code, flexcan.FLEXCAN_CODE_TX_INACTIVE, msg=testmsg)
                    code_addr = baseaddr + FLEXCAN_MB_OFFSET + code_offset
                    self.assertEqual(self.emu.readMemValue(code_addr, 1),
                            flexcan.FLEXCAN_CODE_TX_INACTIVE, msg=testmsg)

                    ts_offset = (mb * FLEXCAN_MBx_SIZE) + 2
                    timestamp = struct.unpack_from('>H', self.emu.can[dev].registers.mb.value, ts_offset)[0]
                    self.assertEqual(timestamp, 0, msg=testmsg)
                    ts_addr = baseaddr + FLEXCAN_MB_OFFSET + ts_offset
                    self.assertEqual(self.emu.readMemValue(ts_addr, 2), 0, msg=testmsg)

    def test_flexcan_rx(self):
        # Set standard bus speeds
        self.set_baudrates()

        # Only enable some of the mailbox interrupts: 0-7, 24-31, 32-47
        enabled_intrs = list(range(0, 8)) + list(range(24, 32)) + list(range(32, 48))

        # Send a message from each bus and ensure the timestamp is correctly
        # updated, wait 0.10 seconds before sending and then check that the time
        # stamp is correct.

        for dev in range(4):
            devname, baseaddr = FLEXCAN_DEVICES[dev]
            mcr_addr = baseaddr + FLEXCAN_MCR_OFFSET
            timer_addr = baseaddr + FLEXCAN_TIMER_OFFSET

            logger.info('Starting RX test for %s', devname)

            # For each CAN device only enable some mailboxes to receive:
            #   CAN A: rx in all mailboxes
            #   CAN B: rx in every other mailbox
            #   CAN C: rx in every third mailbox
            #   CAN D: rx in every fourth mailbox
            # Set those mailboxes to RX_EMPTY now
            rx_mbs = list(range(0, FLEXCAN_NUM_MBs, dev+1))
            for mb in rx_mbs:
                addr = baseaddr + FLEXCAN_MB_OFFSET + (mb * FLEXCAN_MBx_SIZE)
                self.emu.writeMemValue(addr, flexcan.FLEXCAN_CODE_RX_EMPTY, 1)

            # Only enable some of the mailbox interrupts: 0-7, 24-31, 32-47
            self.emu.writeMemValue(baseaddr + FLEXCAN_IMASK1_OFFSET, 0xFF0000FF, 4)
            self.emu.writeMemValue(baseaddr + FLEXCAN_IMASK2_OFFSET, 0x0000FFFF, 4)

            # Generate one message for each mailbox that can receive, because a
            # message with ID 0 would match a mailbox with the entire mask set
            # and the filter value of 0, make the minimum ID 1
            msgs = [generate_msg(rtr=0, min_id=1) for i in range(len(rx_mbs))]

            # Change mode to NORMAL
            self.emu.writeMemValue(mcr_addr, 0, 4)

            # Call the processReceivedData function to mimic what the emulator
            # calls when a message is received during normal execution.  Because
            # the default filters are all 1's and no ID masks were defined in
            # any of the valid receive mailboxes, these messages should all just
            # be discarded.
            for mb, msg in zip(rx_mbs, msgs):
                self.emu.can[dev].processReceivedData(msg)

            # Loop through the mailboxes and ensure they are all still empty.
            inactive_mb = b'\x00' * FLEXCAN_MBx_SIZE
            empty_mb = b'\x04' + b'\x00' * (FLEXCAN_MBx_SIZE - 1)
            for mb in range(FLEXCAN_NUM_MBs):
                testmsg = '%s[%d]' % (devname, mb)
                addr = baseaddr + FLEXCAN_MB_OFFSET + (mb * FLEXCAN_MBx_SIZE)
                # Ensure that nothing has been received in this mailbox, but the
                # CODE is still correct
                if mb in rx_mbs:
                    self.assertEqual(self.emu.readMemory(addr, FLEXCAN_MBx_SIZE), empty_mb, msg=testmsg)
                else:
                    self.assertEqual(self.emu.readMemory(addr, FLEXCAN_MBx_SIZE), inactive_mb, msg=testmsg)

            # Ensure there are no pending interrupts
            self.assertEqual(self._getPendingExceptions(), [], msg=devname)

            # Now clear out the RXG, RX14, and RX15 masks, these must be changed
            # in FREEZE mode
            self.emu.writeMemValue(mcr_addr, FLEXCAN_MCR_FRZ_MASK | FLEXCAN_MCR_HALT_MASK, 4)
            self.emu.writeMemValue(baseaddr + FLEXCAN_RXGMASK_OFFSET, 0, 4)
            self.emu.writeMemValue(baseaddr + FLEXCAN_RX14MASK_OFFSET, 0, 4)
            self.emu.writeMemValue(baseaddr + FLEXCAN_RX15MASK_OFFSET, 0, 4)

            # Now move back to normal mode
            self.emu.writeMemValue(mcr_addr, 0, 4)
            start_time = self.emu.systime()

            last_mb = None
            last_timestamp = None

            # It is expected that the calculated timestamp will be slightly
            # larger than the actual timestamp because it is saved right
            # after the memory write occurs that causes the transmit
            margin = self.emu.can[dev].speed * 0.0050

            # Zero out the timer register.
            self.emu.writeMemValue(timer_addr, 0, 4)

            # Call the processReceivedData function to mimic what the emulator
            # calls when a message is received during normal execution.  Because
            # no filtering or masking is set up the messages should be placed
            # into the first empty mailbox
            for i, (mb, msg) in enumerate(zip(rx_mbs, msgs)):
                testmsg = '%s[%d]' % (devname, mb)
                addr = baseaddr + FLEXCAN_MB_OFFSET + (mb * FLEXCAN_MBx_SIZE)

                self.emu.can[dev].processReceivedData(msg)

                # Confirm that the timestamp is accurate. The timer has probably
                # wrapped by now so ensure it is limited to 16 bits
                rx_delay = self.emu.systime() - start_time
                expected_ticks = int(self.emu.can[dev].speed * rx_delay) & 0xFFFF

                ts_offset = (mb * FLEXCAN_MBx_SIZE) + 2
                timestamp = struct.unpack_from('>H', self.emu.can[dev].registers.mb.value, ts_offset)[0]
                logger.info('msg %d: timestamp = 0x%04x, expected = 0x%04x', i, timestamp, expected_ticks)
                self.assert_timer_within_range(timestamp, expected_ticks, margin, maxval=0xFFFF, msg=testmsg)

                last_mb = mb
                last_timestamp = timestamp

                # Now that the timestamp has been confirmed to be within the
                # expected range, ensure that the message in the mailbox matches
                # what is expected for the received message
                rx_msg_data = msg.encode(code=flexcan.FLEXCAN_CODE_RX_FULL, timestamp=timestamp)
                self.assertEqual(self.emu.readMemory(addr, FLEXCAN_MBx_SIZE), rx_msg_data, msg=testmsg)

                # Ensure that there is a pending interrupt for this mailbox
                if mb in enabled_intrs:
                    self.assertEqual(self._getPendingExceptions(), [get_int(dev, mb)], msg=testmsg)
                else:
                    self.assertEqual(self._getPendingExceptions(), [], msg=testmsg)

            # There should be no more interrupts pending
            self.assertEqual(self._getPendingExceptions(), [], msg=testmsg)

            # Ensure the correct IFLAGs are set
            iflag1_val = self.emu.readMemValue(baseaddr + FLEXCAN_IFLAG1_OFFSET, 4)
            iflag2_val = self.emu.readMemValue(baseaddr + FLEXCAN_IFLAG2_OFFSET, 4)
            if dev == 0:
                # For CAN A every mailbox should have a message
                self.assertEqual(iflag1_val, 0xFFFFFFFF, msg=devname)
                self.assertEqual(iflag2_val, 0xFFFFFFFF, msg=devname)
            elif dev == 1:
                # For CAN B every other mailbox should have a message
                self.assertEqual(iflag1_val, 0x55555555, msg=devname)
                self.assertEqual(iflag2_val, 0x55555555, msg=devname)
            elif dev == 2:
                # For CAN C every third mailbox should have a message
                self.assertEqual(iflag1_val, 0x49249249, msg=devname)
                self.assertEqual(iflag2_val, 0x92492492, msg=devname)
            elif dev == 3:
                # For CAN D every fourth mailbox should have a message
                self.assertEqual(iflag1_val, 0x11111111, msg=devname)
                self.assertEqual(iflag2_val, 0x11111111, msg=devname)

            # Now ensure that all mailboxes that were not in the list are still
            # inactive and empty
            for mb in range(FLEXCAN_NUM_MBs):
                if mb not in rx_mbs:
                    addr = baseaddr + FLEXCAN_MB_OFFSET + (mb * FLEXCAN_MBx_SIZE)

                    # Ensure that nothing has been received in this mailbox
                    self.assertEqual(self.emu.readMemory(addr, FLEXCAN_MBx_SIZE), inactive_mb, msg=testmsg)

            # Generate one more message and send it, this should cause the CODE
            # of the last mailbox configured for receive to be set to OVERRUN
            # but should not generate any new interrupts
            overflow_msg = generate_msg(rtr=0)

            # Ensure that this doesn't match the last sent message (which should
            # be in the last mailbox)
            #
            self.assertNotEqual(overflow_msg, msgs[-1], devname)
            self.emu.can[dev].processReceivedData(overflow_msg)

            # Ensure that the message in the last receive mailbox still matches
            # the last message received
            testmsg = '%s[%d]' % (devname, last_mb)
            overflow_msg_data = msgs[-1].encode(code=flexcan.FLEXCAN_CODE_RX_OVERRUN, timestamp=last_timestamp)
            addr = baseaddr + FLEXCAN_MB_OFFSET + (last_mb * FLEXCAN_MBx_SIZE)
            self.assertEqual(self.emu.readMemory(addr, FLEXCAN_MBx_SIZE), overflow_msg_data, msg=testmsg)

            # And ensure that there are no new interrupts
            self.assertEqual(self._getPendingExceptions(), [], msg=testmsg)

        self.emu.sleep(2)

        # Quick sanity check see that all exceptions have been properly handled
        self.assertEqual(self._getPendingExceptions(), [], msg=testmsg)

    def test_flexcan_rx_fifo(self):
        # Set standard bus speeds
        self.set_baudrates()

        # Only enable some of the mailbox interrupts: 0-7, 24-31, 32-47
        enabled_intrs = list(range(0, 8)) + list(range(24, 32)) + list(range(32, 48))

        for dev in range(4):
            devname, baseaddr = FLEXCAN_DEVICES[dev]
            mcr_addr = baseaddr + FLEXCAN_MCR_OFFSET

            # Configure the following things:
            # - Enable all interrupts
            self.emu.writeMemValue(baseaddr + FLEXCAN_IMASK1_OFFSET, 0xFFFFFFFF, 4)
            self.emu.writeMemValue(baseaddr + FLEXCAN_IMASK2_OFFSET, 0xFFFFFFFF, 4)

            # - Clear all filter masks
            self.emu.writeMemValue(baseaddr + FLEXCAN_RXGMASK_OFFSET, 0, 4)
            self.emu.writeMemValue(baseaddr + FLEXCAN_RX14MASK_OFFSET, 0, 4)
            self.emu.writeMemValue(baseaddr + FLEXCAN_RX15MASK_OFFSET, 0, 4)

            # - Set all non-RxFIFO mailboxes to INACTIVE
            for mb in range(6, FLEXCAN_NUM_MBs):
                addr = baseaddr + FLEXCAN_MB_OFFSET + (mb * FLEXCAN_MBx_SIZE)
                self.emu.writeMemValue(addr, flexcan.FLEXCAN_CODE_RX_INACTIVE, 1)

            # - Change mode to NORMAL and enable Rx FIFO
            self.emu.writeMemValue(mcr_addr, FLEXCAN_MCR_FEN_MASK, 4)
            self.assertEqual(self.emu.can[dev].mode, flexcan.FLEXCAN_MODE.NORMAL, devname)
            self.assertEqual(self.emu.can[dev].registers.mcr.fen, 1, devname)
            start_time = self.emu.systime()

            # Generate 6 messages to send
            msgs = [generate_msg() for i in range(6)]

            # It is expected that the calculated timestamp will be slightly
            # larger than the actual timestamp because it is saved right
            # after the memory write occurs that causes the transmit
            margin = self.emu.can[dev].speed * 0.0050

            # The RxFIFO can hold 6 messages, each received message should
            # generate a RxFIFO Msg Available interrupt (MB5), when the last
            # message is queued an RxFIFO Warning interrupt (MB6) should be
            # generated
            rx_times = []
            for i in range(len(msgs)):
                testmsg = '%s RxFIFO[%d]' % (devname, i)
                self.emu.can[dev].processReceivedData(msgs[i])
                rx_times.append(self.emu.systime())
                self.emu.sleep(0.1)

                # There should be one RxFIFO Msg Available interrupt (MB5) when
                # the first message is sent, then an RxFIFO Warning interrupt
                # (MB6) after the 6th message is sent.
                if i == 0:
                    self.assertEqual(self._getPendingExceptions(), [get_int(dev, 5)], msg=testmsg)
                elif i == 5:
                    self.assertEqual(self._getPendingExceptions(), [get_int(dev, 6)], msg=testmsg)

            # Only MB5 and MB6 interrupt flags should be set
            iflag1_val = self.emu.readMemValue(baseaddr + FLEXCAN_IFLAG1_OFFSET, 4)
            iflag2_val = self.emu.readMemValue(baseaddr + FLEXCAN_IFLAG2_OFFSET, 4)
            self.assertEqual(iflag1_val, 0x00000060, msg=devname)
            self.assertEqual(iflag2_val, 0x00000000, msg=devname)

            # Send one more message and ensure the RxFIFO Overflow interrupt
            # (MB7) happens
            lost_msg = generate_msg()
            self.emu.can[dev].processReceivedData(lost_msg)

            self.assertEqual(self._getPendingExceptions(), [get_int(dev, 7)], msg=testmsg)
            iflag1_val = self.emu.readMemValue(baseaddr + FLEXCAN_IFLAG1_OFFSET, 4)
            self.assertEqual(iflag1_val, 0x000000E0, msg=devname)

            # Now read a message from the RxFIFO (MB0).
            # Randomize how this data is read from the mailbox registers, it
            # can be read in 1, 2 or 4 byte chunks.
            first_msg = read_mb_data(self.emu, dev, 0)
            rx_msgs = [first_msg]

            # Reading the FIFO without clearing the interrupt flag should not
            # change the available data, read again and confirm the data matches
            self.assertEqual(read_mb_data(self.emu, dev, 0), first_msg, msg=devname)

            # Clear the overflow and warning interrupt flags and ensure that the
            # message in MB0 doesn't change
            self.emu.writeMemValue(baseaddr + FLEXCAN_IFLAG1_OFFSET, 0x000000C0, 4)
            iflag1_val = self.emu.readMemValue(baseaddr + FLEXCAN_IFLAG1_OFFSET, 4)
            self.assertEqual(iflag1_val, 0x00000020, msg=devname)
            self.assertEqual(self._getPendingExceptions(), [], msg=devname)

            self.assertEqual(read_mb_data(self.emu, dev, 0), first_msg, msg=devname)

            # Clear the MB5 interrupt flag and ensure that a new RxFIFO Msg
            # Available interrupt (MB5) happens and that a new message is
            # available in MB0
            self.emu.writeMemValue(baseaddr + FLEXCAN_IFLAG1_OFFSET, 0x00000020, 4)
            self.assertEqual(self._getPendingExceptions(), [get_int(dev, 5)], msg=devname)

            self.assertNotEqual(read_mb_data(self.emu, dev, 0), first_msg, msg=devname)

            # the MB5 interrupt flag should be set again
            iflag1_val = self.emu.readMemValue(baseaddr + FLEXCAN_IFLAG1_OFFSET, 4)
            self.assertEqual(iflag1_val, 0x00000020, msg=devname)

            # Send another message and ensure the RxFIFO Warning is set again
            msgs.append(generate_msg())
            self.emu.can[dev].processReceivedData(msgs[-1])
            rx_times.append(self.emu.systime())

            self.assertEqual(self._getPendingExceptions(), [get_int(dev, 6)], msg=testmsg)
            iflag1_val = self.emu.readMemValue(baseaddr + FLEXCAN_IFLAG1_OFFSET, 4)
            self.assertEqual(iflag1_val, 0x00000060, msg=devname)

            # Read the remaining 5 messages from the RxFIFO
            while iflag1_val:
                # Save the message in MB0
                msg = read_mb_data(self.emu, dev, 0)
                rx_msgs.append(msg)

                # Clear the interrupt flags, this should trigger a new interrupt
                # if we have not read all of the messages from the FIFO
                self.emu.writeMemValue(baseaddr + FLEXCAN_IFLAG1_OFFSET, iflag1_val, 4)
                iflag1_val = self.emu.readMemValue(baseaddr + FLEXCAN_IFLAG1_OFFSET, 4)

                if len(rx_msgs) != len(msgs):
                    self.assertEqual(iflag1_val, 0x00000020, msg=devname)
                    self.assertEqual(self._getPendingExceptions(), [get_int(dev, 5)], msg=devname)
                else:
                    self.assertEqual(iflag1_val, 0x00000000, msg=devname)

            # Sanity check, the number of received messages should now match the
            # number of sent messages and the number of receive times recorded.
            self.assertEqual(len(rx_msgs), len(msgs), msg=devname)
            self.assertEqual(len(rx_msgs), len(rx_times), msg=devname)

            # Go through the received messages and timestamps and ensure that
            # messages were received correctly.
            for i in range(len(msgs)):
                testmsg = '%s RxFIFO[%d]' % (devname, i)
                rx_delay = rx_times[i] - start_time
                expected_ticks = int(self.emu.can[dev].speed * rx_delay) & 0xFFFF

                timestamp = struct.unpack_from('>H', rx_msgs[i], 2)[0]
                self.assert_timer_within_range(timestamp, expected_ticks, margin, maxval=0xFFFF, msg=testmsg)

                # Now that the timestamp has been confirmed to be within the
                # expected range, ensure that the received message in the
                # matches what was sent
                msg_data = msgs[i].encode(code=0, timestamp=timestamp)
                self.assertEqual(rx_msgs[i], msg_data, msg=testmsg)

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
    accurate_timing = True

    args = [
        '-c',
        '-O', 'project.MPC5674.FlexCAN_A.port=10001',
        '-O', 'project.MPC5674.FlexCAN_B.port=10002',
        '-O', 'project.MPC5674.FlexCAN_C.port=10003',
        '-O', 'project.MPC5674.FlexCAN_D.port=10004',
    ]

    def set_sysclk_240mhz(self):
        # Default PLL clock based on the PCB params selected for these tests is
        # 60 MHz
        self.assertEqual(self.emu.config.project.MPC5674.FMPLL.extal, 40000000)
        self.assertEqual(self.emu.getClock('pll'), 60000000.0)

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
        self.assertEqual(self.emu.getClock('pll'), 240000000.0)

        # Now set the SIU peripheral configuration to allow the CPU frequency to
        # be double the peripheral speed (otherwise the maximum bus/peripheral
        # speed is 132 MHz

        # SYSDIV[IPCLKDIV] = 0
        # SYSDIV[BYPASS] = 1
        self.emu.writeMemValue(0xC3F909A0, 0x00000010, 4)
        self.assertEqual(self.emu.getClock('periph'), 120000000.0)

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
        with mmio.supervisorMode(self.emu):
            self.emu.writeMemory(pc, instrs)

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
            with mmio.supervisorMode(self.emu):
                self.emu.writeMemory(addr, b'\x60\x00\x00\x00\x4c\x00\x00\x64')

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
