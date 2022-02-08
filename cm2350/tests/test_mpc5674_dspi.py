import os
import queue
import random
import struct
import unittest

from cm2350 import CM2350, intc_exc
from cm2350.peripherals import dspi

import envi.archs.ppc.regs as eapr
import envi.archs.ppc.const as eapc


DSPI_DEVICES = (
    ('DSPI_A', 0XFFF90000),
    ('DSPI_B', 0XFFF94000),
    ('DSPI_C', 0XFFF98000),
    ('DSPI_D', 0XFFF9C000),
)

DSPI_MCR_OFFSET          = 0x0000
DSPI_TCR_OFFSET          = 0x0008
DSPI_CTAR_RANGE          = range(0x000C, 0x002C, 4)
DSPI_SR_OFFSET           = 0x002C
DSPI_RSER_OFFSET         = 0x0030
DSPI_PUSHR_OFFSET        = 0x0034
DSPI_POPR_OFFSET         = 0x0038
DSPI_TXFR_RANGE          = range(0x003C, 0x004C, 4)
DSPI_RXFR_RANGE          = range(0x007C, 0x008C, 4)
DSPI_DSICR_OFFSET        = 0x00BC
DSPI_SDR_OFFSET          = 0x00C0
DSPI_ASDR_OFFSET         = 0x00C4
DSPI_COMPR_OFFSET        = 0x00C8
DSPI_DDR_OFFSET          = 0x00CC
DSPI_DSICR1_OFFSET       = 0x00D0

DSPI_MCR_DEFAULT         = 0x00000001
DSPI_MCR_DEFAULT_BYTES   = b'\x00\x00\x00\x01'
DSPI_CTARx_DEFAULT       = 0x78000000
DSPI_CTARx_DEFAULT_BYTES = b'\x78\x00\x00\x00'
DSPI_SR_DEFAULT          = 0x02000000
DSPI_SR_DEFAULT_BYTES    = b'\x02\x00\x00\x00'

# Masks and shifts used in testing
DSPI_MCR_MSTR_MASK       = 0x80000000
DSPI_MCR_DSI_MASK        = 0x10000000
DSPI_MCR_CSI_MASK        = 0x20000000
DSPI_MCR_ROOE_MASK       = 0x01000000
DSPI_MCR_MDIS_MASK       = 0x00004000
DSPI_MCR_DIS_TXF_MASK    = 0x00002000
DSPI_MCR_DIS_RXF_MASK    = 0x00001000
DSPI_MCR_CLR_TXF_MASK    = 0x00000800
DSPI_MCR_CLR_RXF_MASK    = 0x00000400
DSPI_MCR_HALT_MASK       = 0x00000001

DSPI_MCR_MSTR_SHIFT      = 31

DSPI_TCR_TCNT_SHIFT      = 16

DSPI_CTAR_FMSZ_SHIFT     = 27

DSPI_PUSHR_EOQ_MASK      = 0x08000000
DSPI_PUSHR_CTCNT_MASK    = 0x04000000

DSPI_PUSHR_CTAS_SHIFT    = 28
DSPI_PUSHR_EOQ_SHIFT     = 27
DSPI_PUSHR_CTCNT_SHIFT   = 26

DSPI_SR_TCF_MASK         = 0x80000000
DSPI_SR_TXRXS_MASK       = 0x40000000
DSPI_SR_EOQF_MASK        = 0x10000000
DSPI_SR_TFUF_MASK        = 0x08000000
DSPI_SR_TFFF_MASK        = 0x02000000
DSPI_SR_RFOF_MASK        = 0x00080000
DSPI_SR_RFDF_MASK        = 0x00020000
DSPI_SR_TXCTR_MASK       = 0x0000F000
DSPI_SR_TXNXTPTR_MASK    = 0x00000F00
DSPI_SR_RXCTR_MASK       = 0x000000F0
DSPI_SR_POPNXTPTR_MASK   = 0x0000000F

DSPI_SR_TXCTR_SHIFT      = 12
DSPI_SR_TXNXTPTR_SHIFT   = 8
DSPI_SR_RXCTR_SHIFT      = 4
DSPI_SR_POPNXTPTR_SHIFT  = 0

DSPI_RSER_TCF_MASK         = 0x80000000
DSPI_RSER_EOQF_MASK        = 0x10000000
DSPI_RSER_TFUF_MASK        = 0x08000000
DSPI_RSER_TFFF_MASK        = 0x02000000
DSPI_RSER_TFFF_DIRS_MASK   = 0x01000000
DSPI_RSER_RFOF_MASK        = 0x00080000
DSPI_RSER_RFDF_MASK        = 0x00020000
DSPI_RSER_RFDF_DIRS_MASK   = 0x00010000


def get_int_src(dev, event):
    """
    Calculate the correct external interrupt source for a DSPI device and event
    values are from
    "Table 9-8. Interrupt Request Sources" (MPC5674FRM.pdf page 325-341)
      DSPI_BSR[TFUF/RFOF] = 131
      DSPI_CSR[TFUF/RFOF] = 136
      DSPI_DSR[TFUF/RFOF] = 141
      DSPI_ASR[TFUF/RFOF] = 275

    Parameters:
        dev   (int): indicating DSPI A (0) to D (3)
        event (str): the event to return the interrupt source for

    Return:
        interrupt source value (int)
    """
    base = (275, 131, 136, 141)[dev]
    offset = {'tfuf': 0, 'rfof': 0, 'eoqf': 1, 'tfff': 2, 'tcf': 3, 'rfdf': 4}[event]
    return base + offset


def get_int(dev, event):
    """
    Returns an ExternalException object that corresponds to a queued exception
    associated with a specific DSPI device and event.

    Parameters:
        dev   (int): indicating DSPI A (0) to D (3)
        event (str): the event to return the interrupt source for

    Return:
        interrupt source value (int)
    """
    return intc_exc.ExternalException(intc_exc.INTC_SRC(get_int_src(dev, event)))


class MPC5674_DSPI_Test(unittest.TestCase):
    def get_random_pc(self):
        start, end, perms, filename = self.emu.getMemoryMap(0)
        return random.randrange(start, end, 4)

    def setUp(self):
        # Specify mode "test" and a non-existing directory for the configuration
        # location to use (so the user's configuration is not used)
        if os.environ.get('LOG_LEVEL', 'INFO') == 'DEBUG':
            args = ['-m', 'test', '-c', '-vvv']
        else:
            args = ['-m', 'test', '-c']
        self.ECU = CM2350(args)
        self.emu = self.ECU.emu

        # Set the INTC[CPR] to 0 to allow all peripheral (external) exception
        # priorities to happen
        self.emu.intc.registers.cpr.pri = 0
        msr_val = self.emu.getRegister(eapr.REG_MSR)

        # Enable all possible Exceptions so if anything happens it will be
        # detected by the _getPendingExceptions utility
        msr_val |= eapc.MSR_EE_MASK | eapc.MSR_CE_MASK | eapc.MSR_ME_MASK | eapc.MSR_DE_MASK
        self.emu.setRegister(eapr.REG_MSR, msr_val)

        # Enable the timebase (normally done by writing a value to HID0)
        self.emu.enableTimebase()

    def _getPendingExceptions(self):
        pending_excs = []
        for intq in self.emu.mcu_intc.intqs[1:]:
            try:
                while True:
                    pending_excs.append(intq.get_nowait())
            except queue.Empty:
                pass
        return pending_excs

    def tearDown(self):
        # Ensure that there are no unprocessed exceptions
        pending_excs = self._getPendingExceptions()
        for exc in pending_excs:
            print('Unhanded PPC Exception %s' % exc)
        self.assertEqual(pending_excs, [])

    ##################################################
    # Simple Register Tests
    ##################################################

    def test_dspi_mcr(self):
        for dev in range(len(DSPI_DEVICES)):
            devname, baseaddr = DSPI_DEVICES[dev]
            self.assertEqual(self.emu.dspi[dev].devname, devname)

            addr = baseaddr + DSPI_MCR_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), DSPI_MCR_DEFAULT_BYTES)
            self.assertEqual(self.emu.readMemValue(addr, 4), DSPI_MCR_DEFAULT)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.mstr, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.cont_scke, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.dconf, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.frz, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.mtfe, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.pcsse, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.rooe, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.pcsis, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.doze, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.mdis, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.dis_txf, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.dis_rxf, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.clr_txf, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.clr_rxf, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.smpl_pt, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.halt, 1)

    def test_dspi_tcr(self):
        for dev in range(len(DSPI_DEVICES)):
            devname, baseaddr = DSPI_DEVICES[dev]
            self.assertEqual(self.emu.dspi[dev].devname, devname)

            addr = baseaddr + DSPI_TCR_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')
            self.assertEqual(self.emu.readMemValue(addr, 4), 0)
            self.assertEqual(self.emu.dspi[dev].registers.tcr.spi_tcnt, 0)

            # Should be able to manually modify the transfer count
            tcnt = random.randrange(1, 0xFFFF + 1)
            self.emu.writeMemValue(addr, tcnt << 16, 4)
            self.assertEqual(self.emu.readMemValue(addr, 4), tcnt << 16)
            self.assertEqual(self.emu.dspi[dev].registers.tcr.spi_tcnt, tcnt)

    def test_dspi_ctar(self):
        for dev in range(len(DSPI_DEVICES)):
            devname, baseaddr = DSPI_DEVICES[dev]
            self.assertEqual(self.emu.dspi[dev].devname, devname)

            for ctar_idx, offset in zip(range(8), DSPI_CTAR_RANGE):
                addr = baseaddr + offset

                self.assertEqual(self.emu.readMemory(addr, 4), DSPI_CTARx_DEFAULT_BYTES)
                self.assertEqual(self.emu.readMemValue(addr, 4), DSPI_CTARx_DEFAULT)
                self.assertEqual(self.emu.dspi[dev].registers.ctar[ctar_idx].dbr, 0)
                self.assertEqual(self.emu.dspi[dev].registers.ctar[ctar_idx].fmsz, 0xF)
                self.assertEqual(self.emu.dspi[dev].registers.ctar[ctar_idx].cpol, 0)
                self.assertEqual(self.emu.dspi[dev].registers.ctar[ctar_idx].cpha, 0)
                self.assertEqual(self.emu.dspi[dev].registers.ctar[ctar_idx].lsbfe, 0)
                self.assertEqual(self.emu.dspi[dev].registers.ctar[ctar_idx].pcssck, 0)
                self.assertEqual(self.emu.dspi[dev].registers.ctar[ctar_idx].pdt, 0)
                self.assertEqual(self.emu.dspi[dev].registers.ctar[ctar_idx].pbr, 0)
                self.assertEqual(self.emu.dspi[dev].registers.ctar[ctar_idx].cssck, 0)
                self.assertEqual(self.emu.dspi[dev].registers.ctar[ctar_idx].asc, 0)
                self.assertEqual(self.emu.dspi[dev].registers.ctar[ctar_idx].dt, 0)
                self.assertEqual(self.emu.dspi[dev].registers.ctar[ctar_idx].br, 0)

                # Write an arbitrary value and make sure it was able to be
                # written successfully.
                val = random.getrandbits(32)
                self.emu.writeMemValue(addr, val, 4)
                self.assertEqual(self.emu.readMemValue(addr, 4), val)

    def test_dspi_sr(self):
        for dev in range(len(DSPI_DEVICES)):
            devname, baseaddr = DSPI_DEVICES[dev]
            self.assertEqual(self.emu.dspi[dev].devname, devname)

            addr = baseaddr + DSPI_SR_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), DSPI_SR_DEFAULT_BYTES)
            self.assertEqual(self.emu.readMemValue(addr, 4), DSPI_SR_DEFAULT)
            self.assertEqual(self.emu.dspi[dev].registers.sr.tcf, 0)
            self.assertEqual(self.emu.dspi[dev].registers.sr.txrxs, 0)
            self.assertEqual(self.emu.dspi[dev].registers.sr.eoqf, 0)
            self.assertEqual(self.emu.dspi[dev].registers.sr.tfuf, 0)
            self.assertEqual(self.emu.dspi[dev].registers.sr.tfff, 1)
            self.assertEqual(self.emu.dspi[dev].registers.sr.rfof, 0)
            self.assertEqual(self.emu.dspi[dev].registers.sr.rfdf, 0)
            self.assertEqual(self.emu.dspi[dev].registers.sr.txctr, 0)
            self.assertEqual(self.emu.dspi[dev].registers.sr.txnxtptr, 0)
            self.assertEqual(self.emu.dspi[dev].registers.sr.rxctr, 0)
            self.assertEqual(self.emu.dspi[dev].registers.sr.popnxtptr, 0)

            # Ensure that the flags map correctly, first clear TFFF so SR is
            # all 0.
            self.emu.dspi[dev].registers.sr.vsOverrideValue('tfff', 0)
            self.assertEqual(self.emu.readMemValue(addr, 4), 0)

            # fields to test
            fields = (
                ('tcf',         1, DSPI_SR_TCF_MASK),
                ('txrxs',       1, DSPI_SR_TXRXS_MASK),
                ('eoqf',        1, DSPI_SR_EOQF_MASK),
                ('tfuf',        1, DSPI_SR_TFUF_MASK),
                ('tfff',        1, DSPI_SR_TFFF_MASK),
                ('rfof',        1, DSPI_SR_RFOF_MASK),
                ('rfdf',        1, DSPI_SR_RFDF_MASK),
                ('txctr',     0xF, DSPI_SR_TXCTR_MASK),
                ('txnxtptr',  0xF, DSPI_SR_TXNXTPTR_MASK),
                ('rxctr',     0xF, DSPI_SR_RXCTR_MASK),
                ('popnxtptr', 0xF, DSPI_SR_POPNXTPTR_MASK),
            )

            for field, field_val, sr_val in fields:
                self.emu.dspi[dev].registers.sr.vsOverrideValue(field, field_val)
                self.assertEqual(self.emu.readMemValue(addr, 4), sr_val, msg=field)
                self.emu.dspi[dev].registers.sr.vsOverrideValue(field, 0)
                self.assertEqual(self.emu.readMemValue(addr, 4), 0, msg=field)

    def test_dspi_rser(self):
        for dev in range(len(DSPI_DEVICES)):
            devname, baseaddr = DSPI_DEVICES[dev]
            self.assertEqual(self.emu.dspi[dev].devname, devname)

            addr = baseaddr + DSPI_RSER_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')
            self.assertEqual(self.emu.readMemValue(addr, 4), 0)
            # The bit fields that are ISR request bits use the same names as the
            # status register field names.
            self.assertEqual(self.emu.dspi[dev].registers.rser.tcf, 0)
            self.assertEqual(self.emu.dspi[dev].registers.rser.eoqf, 0)
            self.assertEqual(self.emu.dspi[dev].registers.rser.tfff, 0)
            self.assertEqual(self.emu.dspi[dev].registers.rser.tfff_dirs, 0)
            self.assertEqual(self.emu.dspi[dev].registers.rser.rfof, 0)
            self.assertEqual(self.emu.dspi[dev].registers.rser.rfdf, 0)
            self.assertEqual(self.emu.dspi[dev].registers.rser.rfdf_dirs, 0)

            # Ensure that the flags map correctly
            fields = (
                ('tcf',         1, DSPI_RSER_TCF_MASK),
                ('eoqf',        1, DSPI_RSER_EOQF_MASK),
                ('tfuf',        1, DSPI_RSER_TFUF_MASK),
                ('tfff',        1, DSPI_RSER_TFFF_MASK),
                ('tfff_dirs',   1, DSPI_RSER_TFFF_DIRS_MASK),
                ('rfof',        1, DSPI_RSER_RFOF_MASK),
                ('rfdf',        1, DSPI_RSER_RFDF_MASK),
                ('rfdf_dirs',   1, DSPI_RSER_RFDF_DIRS_MASK),
            )

            for field, field_val, rser_val in fields:
                self.emu.dspi[dev].registers.rser.vsSetField(field, field_val)
                self.assertEqual(self.emu.readMemValue(addr, 4), rser_val, msg=field)
                self.emu.dspi[dev].registers.rser.vsSetField(field, 0)
                self.assertEqual(self.emu.readMemValue(addr, 4), 0, msg=field)

    ##################################################
    # Register tests for DSI and CSI related registers
    ##################################################

    def test_dspi_dsicr(self):
        for dev in range(len(DSPI_DEVICES)):
            devname, baseaddr = DSPI_DEVICES[dev]
            self.assertEqual(self.emu.dspi[dev].devname, devname)

            addr = baseaddr + DSPI_DSICR_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')
            self.assertEqual(self.emu.readMemValue(addr, 4), 0)
            self.assertEqual(self.emu.dspi[dev].registers.dsicr.mtoe, 0)
            self.assertEqual(self.emu.dspi[dev].registers.dsicr.mtocnt, 0)
            self.assertEqual(self.emu.dspi[dev].registers.dsicr.tsbc, 0)
            self.assertEqual(self.emu.dspi[dev].registers.dsicr.txss, 0)
            self.assertEqual(self.emu.dspi[dev].registers.dsicr.tpol, 0)
            self.assertEqual(self.emu.dspi[dev].registers.dsicr.trre, 0)
            self.assertEqual(self.emu.dspi[dev].registers.dsicr.cid, 0)
            self.assertEqual(self.emu.dspi[dev].registers.dsicr.dcont, 0)
            self.assertEqual(self.emu.dspi[dev].registers.dsicr.dsictas, 0)
            self.assertEqual(self.emu.dspi[dev].registers.dsicr.dpcs, 0)

            # Write an arbitrary value and make sure it was able to be
            # written successfully.
            val = 0
            expected = 0
            while expected == 0:
                val = random.randrange(1, 0xFFFFFFFF + 1)
                # Some of the DSICR1 bits are fixed at 0, so ensure that we
                # generate a test value that won't result in all 0's
                expected = val & 0xBF1FF03F
            self.emu.writeMemValue(addr, val, 4)
            self.assertEqual(self.emu.readMemValue(addr, 4), expected)


    def test_dspi_sdr(self):
        for dev in range(len(DSPI_DEVICES)):
            devname, baseaddr = DSPI_DEVICES[dev]
            self.assertEqual(self.emu.dspi[dev].devname, devname)

            addr = baseaddr + DSPI_SDR_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')
            self.assertEqual(self.emu.readMemValue(addr, 4), 0)
            self.assertEqual(self.emu.dspi[dev].registers.sdr.data, 0)

            # writing to SDR should have no affect
            val = random.randrange(1, 0xFFFFFFFF + 1)
            self.emu.writeMemValue(addr, val, 4)
            self.assertEqual(self.emu.readMemValue(addr, 4), 0)

    def test_dspi_asdr(self):
        for dev in range(len(DSPI_DEVICES)):
            devname, baseaddr = DSPI_DEVICES[dev]
            self.assertEqual(self.emu.dspi[dev].devname, devname)

            addr = baseaddr + DSPI_ASDR_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')
            self.assertEqual(self.emu.readMemValue(addr, 4), 0)
            self.assertEqual(self.emu.dspi[dev].registers.asdr.data, 0)

            # Write an arbitrary value and make sure it was able to be
            # written successfully.
            val = random.getrandbits(32)
            self.emu.writeMemValue(addr, val, 4)
            self.assertEqual(self.emu.readMemValue(addr, 4), val)
            self.assertEqual(self.emu.dspi[dev].registers.asdr.data, val)

    def test_dspi_compr(self):
        for dev in range(len(DSPI_DEVICES)):
            devname, baseaddr = DSPI_DEVICES[dev]
            self.assertEqual(self.emu.dspi[dev].devname, devname)

            addr = baseaddr + DSPI_COMPR_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')
            self.assertEqual(self.emu.readMemValue(addr, 4), 0)
            self.assertEqual(self.emu.dspi[dev].registers.compr.data, 0)

            # writing to DDR should have no affect
            val = random.randrange(1, 0xFFFFFFFF + 1)
            self.emu.writeMemValue(addr, val, 4)
            self.assertEqual(self.emu.readMemValue(addr, 4), 0)

    def test_dspi_ddr(self):
        for dev in range(len(DSPI_DEVICES)):
            devname, baseaddr = DSPI_DEVICES[dev]
            self.assertEqual(self.emu.dspi[dev].devname, devname)

            addr = baseaddr + DSPI_DDR_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')
            self.assertEqual(self.emu.readMemValue(addr, 4), 0)
            self.assertEqual(self.emu.dspi[dev].registers.ddr.data, 0)

            # writing to DDR should have no affect
            val = random.randrange(1, 0xFFFFFFFF + 1)
            self.emu.writeMemValue(addr, val, 4)
            self.assertEqual(self.emu.readMemValue(addr, 4), 0)

    def test_dspi_dsicr1(self):
        for dev in range(len(DSPI_DEVICES)):
            devname, baseaddr = DSPI_DEVICES[dev]
            self.assertEqual(self.emu.dspi[dev].devname, devname)

            addr = baseaddr + DSPI_DSICR1_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')
            self.assertEqual(self.emu.readMemValue(addr, 4), 0)
            self.assertEqual(self.emu.dspi[dev].registers.dsicr1.tsbcnt, 0)
            self.assertEqual(self.emu.dspi[dev].registers.dsicr1.dse, 0)
            self.assertEqual(self.emu.dspi[dev].registers.dsicr1.dpcs1, 0)

            # Write an arbitrary value and make sure it was able to be
            # written successfully.
            val = 0
            expected = 0
            while expected == 0:
                val = random.getrandbits(32)
                # Some of the DSICR1 bits are fixed at 0, so ensure that we
                # generate a test value that won't result in all 0's
                expected = val & 0x1F0300FF

            self.emu.writeMemValue(addr, val, 4)
            self.assertEqual(self.emu.readMemValue(addr, 4), expected)

    ##################################################
    # SPI functionality tests
    ##################################################

    def test_dspi_modes(self):
        for dev in range(len(DSPI_DEVICES)):
            devname, baseaddr = DSPI_DEVICES[dev]
            self.assertEqual(self.emu.dspi[dev].devname, devname)

            addr = baseaddr + DSPI_MCR_OFFSET

            # Should start off in peripheral mode, but transmit/receive is off
            self.assertEqual(self.emu.dspi[dev].mode, dspi.DSPI_MODE.SPI_PERIPH)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.mstr, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.frz, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.mdis, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.halt, 1)
            self.assertEqual(self.emu.dspi[dev].registers.sr.txrxs, 0)

            # Disable (set MCR[MDIS])
            val = DSPI_MCR_MDIS_MASK | DSPI_MCR_HALT_MASK
            self.emu.writeMemValue(addr, val, 4)
            self.assertEqual(self.emu.dspi[dev].mode, dspi.DSPI_MODE.DISABLE)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.mstr, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.frz, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.mdis, 1)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.halt, 1)
            self.assertEqual(self.emu.dspi[dev].registers.sr.txrxs, 0)

            # Controller mode TX/Rx off
            val = DSPI_MCR_MSTR_MASK | DSPI_MCR_HALT_MASK
            self.emu.writeMemValue(addr, val, 4)
            self.assertEqual(self.emu.dspi[dev].mode, dspi.DSPI_MODE.SPI_CNTRLR)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.mstr, 1)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.frz, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.mdis, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.halt, 1)
            self.assertEqual(self.emu.dspi[dev].registers.sr.txrxs, 0)

            # Controller mode TX/Rx on
            val = DSPI_MCR_MSTR_MASK
            self.emu.writeMemValue(addr, val, 4)
            self.assertEqual(self.emu.dspi[dev].mode, dspi.DSPI_MODE.SPI_CNTRLR)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.mstr, 1)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.frz, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.mdis, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.halt, 0)
            self.assertEqual(self.emu.dspi[dev].registers.sr.txrxs, 1)

            # Peripheral mode TX/Rx off
            val = DSPI_MCR_HALT_MASK
            self.emu.writeMemValue(addr, val, 4)
            self.assertEqual(self.emu.dspi[dev].mode, dspi.DSPI_MODE.SPI_PERIPH)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.mstr, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.frz, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.mdis, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.halt, 1)
            self.assertEqual(self.emu.dspi[dev].registers.sr.txrxs, 0)

            # Peripheral mode TX/Rx on
            val = 0
            self.emu.writeMemValue(addr, val, 4)
            self.assertEqual(self.emu.dspi[dev].mode, dspi.DSPI_MODE.SPI_PERIPH)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.mstr, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.frz, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.mdis, 0)
            self.assertEqual(self.emu.dspi[dev].registers.mcr.halt, 0)
            self.assertEqual(self.emu.dspi[dev].registers.sr.txrxs, 1)

    ##################################################
    # DSI and CSI functionality tests
    ##################################################

    def test_dspi_unsupported_modes(self):
        # Attempting to change to the DSI or CSI modes should generate
        # NotImplementedError exceptions
        for dev in range(len(DSPI_DEVICES)):
            devname, baseaddr = DSPI_DEVICES[dev]
            self.assertEqual(self.emu.dspi[dev].devname, devname)

            addr = baseaddr + DSPI_MCR_OFFSET

            # DSI Controller
            val = DSPI_MCR_MSTR_MASK | DSPI_MCR_DSI_MASK | DSPI_MCR_HALT_MASK
            with self.assertRaises(NotImplementedError):
                self.emu.writeMemValue(addr, val, 4)
            self.assertEqual(self.emu.dspi[dev].mode, dspi.DSPI_MODE.DSI_CNTRLR)

            # DSI Peripheral
            val = DSPI_MCR_DSI_MASK | DSPI_MCR_HALT_MASK
            with self.assertRaises(NotImplementedError):
                self.emu.writeMemValue(addr, val, 4)
            self.assertEqual(self.emu.dspi[dev].mode, dspi.DSPI_MODE.DSI_PERIPH)

            # CSI Controller
            val = DSPI_MCR_MSTR_MASK | DSPI_MCR_CSI_MASK | DSPI_MCR_HALT_MASK
            with self.assertRaises(NotImplementedError):
                self.emu.writeMemValue(addr, val, 4)
            self.assertEqual(self.emu.dspi[dev].mode, dspi.DSPI_MODE.CSI_CNTRLR)

            # CSI Peripheral
            val = DSPI_MCR_CSI_MASK | DSPI_MCR_HALT_MASK
            with self.assertRaises(NotImplementedError):
                self.emu.writeMemValue(addr, val, 4)
            self.assertEqual(self.emu.dspi[dev].mode, dspi.DSPI_MODE.CSI_PERIPH)

    ##################################################
    # Tx and Rx tests
    ##################################################

    def test_dspi_controller_tx(self):
        # There are 8 CTAR registers and the valid data size is from 4 (value of
        # 3) to 16 (value of 15), use these msg sizes in testing
        msg_sizes = [4, 5, 8, 9, 10, 11, 14, 16]

        # Create the CTAR values, only the FMSZ field matters for the current
        # emulation
        ctar_values = [(s-1) << DSPI_CTAR_FMSZ_SHIFT for s in msg_sizes]

        # Message contents intended to enable verification of which CTAR was
        # used to transmit the message, the least significant nibble indicates
        # which message this is.  The rest of the message has a bit set at the
        # MSB of each message size to ensure that it is easy to distinguish
        # which CTAR was used to transmit the message.
        msgs = [0xA7B8, 0xA7B9, 0xA7BA, 0xA7BB, 0xA7BC, 0xA7BD, 0xA7AB, 0xA7BF]

        # The 4th message is cleared from the transmit queue and will never be
        # sent.
        expected_msgs = [0x8, 0x19, 0xBA, None, 0x3BC, 0x7BD, 0x27AB, 0xA7BF]

        # Create the values to write to the PUSHR register, set the EOQ bit
        # every 3rd message (so the last msg in the Tx FIFO will not set EOQ)
        # and the CTCNT bit on the 8th message.
        pushr_values = []
        for i, msg in zip(range(8), msgs):
            val = i << DSPI_PUSHR_CTAS_SHIFT | msg
            if i % 3 == 2:
                val |= DSPI_PUSHR_EOQ_MASK
            if i == 7:
                val |= DSPI_PUSHR_CTCNT_MASK
            pushr_values.append(val)

        # Value to enable all interrupts
        rser_val = DSPI_RSER_TCF_MASK | DSPI_RSER_EOQF_MASK | \
                DSPI_RSER_TFUF_MASK | DSPI_RSER_TFFF_MASK | \
                DSPI_RSER_RFOF_MASK | DSPI_RSER_RFDF_MASK

        # The transmit behavior should be the same for both controller and
        # peripheral
        device_modes = (
            # MCR[MSTR] | DSPI mode
            (1, dspi.DSPI_MODE.SPI_CNTRLR),
            (0, dspi.DSPI_MODE.SPI_PERIPH),
        )

        for dev in range(len(DSPI_DEVICES)):
            devname, baseaddr = DSPI_DEVICES[dev]
            self.assertEqual(self.emu.dspi[dev].devname, devname)

            mcr_addr = baseaddr + DSPI_MCR_OFFSET
            tcr_addr = baseaddr + DSPI_TCR_OFFSET
            pushr_addr = baseaddr + DSPI_PUSHR_OFFSET
            sr_addr = baseaddr + DSPI_SR_OFFSET
            rser_addr = baseaddr + DSPI_RSER_OFFSET

            # Before the first pass of this test the default state of the
            # SR[TFFF] flag is 1, the second time through this event will be
            # acknowledged so it'll be 0.  Acknowledge the TFFF event now before
            # the loop starts.
            self.assertEqual(self.emu.readMemValue(sr_addr, 4), DSPI_SR_TFFF_MASK, msg=devname)
            self.assertEqual(self.emu.dspi[dev].registers.sr.tfff, 1, msg=devname)
            self.emu.writeMemValue(sr_addr, DSPI_SR_TFFF_MASK, 4)

            for mstr_flag, expected_mode in device_modes:
                testmsg = '%s(%s)' % (devname, expected_mode.name)

                # Ensure there are no pending exceptions right now
                self.assertEqual(self._getPendingExceptions(), [], msg=testmsg)

                # Change to controller mode
                val = (mstr_flag << DSPI_MCR_MSTR_SHIFT) | DSPI_MCR_HALT_MASK
                self.emu.writeMemValue(mcr_addr, val, 4)
                self.assertEqual(self.emu.dspi[dev].mode, expected_mode, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.mcr.halt, 1, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txrxs, 0, msg=testmsg)

                # Configure the CTARx registers with different bit sizes, this will
                # help ensure that a transmitted messages used the correct CTARx
                # configuration register for the data size.
                for val, ctar_offset in zip(ctar_values, DSPI_CTAR_RANGE):
                    ctar_addr = baseaddr + ctar_offset
                    self.emu.writeMemValue(ctar_addr, val, 4)

                # Enable all interrupt sources
                self.emu.writeMemValue(rser_addr, rser_val, 4)

                # Verify the initial state of the peripheral
                self.assertEqual(self.emu.dspi[dev].registers.sr.tfff, 0, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txctr, 0, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txnxtptr, 0, msg=testmsg)

                # Fill the Tx Buffer with 4 messages, verify the correct SR flags
                # after each message is queued: TFFF, TXNXTPTR
                self.emu.writeMemValue(pushr_addr, pushr_values[0], 4)
                self.assertEqual(self.emu.dspi[dev].registers.sr.tfff, 1, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txctr, 1, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txnxtptr, 0, msg=testmsg)

                # After the first message is placed into the Tx FIFO the TFFF
                # event will be re-evaluated and trigger queue exception
                expected_excs = [
                    get_int(dev, 'tfff'),
                ]
                self.assertEqual(self._getPendingExceptions(), expected_excs, msg=testmsg)

                self.emu.writeMemValue(pushr_addr, pushr_values[1], 4)
                self.assertEqual(self.emu.dspi[dev].registers.sr.tfff, 1, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txctr, 2, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txnxtptr, 1, msg=testmsg)

                self.emu.writeMemValue(pushr_addr, pushr_values[2], 4)
                self.assertEqual(self.emu.dspi[dev].registers.sr.tfff, 1, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txctr, 3, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txnxtptr, 2, msg=testmsg)

                # The TFFF flag won't get be zero after adding the next message
                # unless it is cleared first
                self.emu.writeMemValue(sr_addr, DSPI_SR_TFFF_MASK, 4)
                # There will be no TFFF exception queued here because this test
                # started with TFFF being set

                self.emu.writeMemValue(pushr_addr, pushr_values[3], 4)
                self.assertEqual(self.emu.dspi[dev].registers.sr.tfff, 0, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txctr, 4, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txnxtptr, 3, msg=testmsg)

                # Verify that the data in the Tx FIFO matches what is expected based
                # on the msg data written msg 0 should be at the last position of
                # the Tx FIFO
                for i, txf_offset in zip(reversed(range(4)), DSPI_TXFR_RANGE):
                    msg = '%s(%s) TXF[%d]' % (devname, expected_mode.name, i)
                    txf_addr = baseaddr + txf_offset
                    self.assertEqual(self.emu.readMemValue(txf_addr, 4), pushr_values[i], msg=msg)

                # The value in PUSHR should be the last data written
                self.assertEqual(self.emu.readMemValue(pushr_addr, 4), pushr_values[3], msg=testmsg)

                # Attempt to write to PUSHR again, and confirm nothing has changed
                self.emu.writeMemValue(pushr_addr, pushr_values[4], 4)
                self.assertEqual(self.emu.dspi[dev].registers.sr.tfff, 0, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txctr, 4, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txnxtptr, 3, msg=testmsg)
                for i, txf_offset in zip(reversed(range(4)), DSPI_TXFR_RANGE):
                    msg = '%s(%s) TXF[%d]' % (devname, expected_mode.name, i)
                    txf_addr = baseaddr + txf_offset
                    self.assertEqual(self.emu.readMemValue(txf_addr, 4), pushr_values[i], msg=msg)
                self.assertEqual(self.emu.readMemValue(pushr_addr, 4), pushr_values[3], msg=testmsg)

                # No messages have been sent yet (if this is the controller
                # mode, otherwise the TCNT should be the same as the end of the
                # previous test:
                if expected_mode == dspi.DSPI_MODE.SPI_CNTRLR:
                    start_tcnt = 0
                else:
                    start_tcnt = 1
                self.assertEqual(self.emu.dspi[dev].registers.tcr.spi_tcnt, start_tcnt, msg=testmsg)
                expected_tcnt = start_tcnt << DSPI_TCR_TCNT_SHIFT
                self.assertEqual(self.emu.readMemValue(tcr_addr, 4), expected_tcnt, msg=testmsg)

                # Enable Tx/Rx
                self.assertEqual(self.emu.dspi[dev].registers.sr.eoqf, 0, msg=testmsg)
                val = (mstr_flag << DSPI_MCR_MSTR_SHIFT)
                self.emu.writeMemValue(mcr_addr, val, 4)

                # After the write is complete Tx/Rx should be enabled until the EOQ
                # message is hit.  By the time writeMemValue() returns the
                # peripheral should be halted again.
                self.assertEqual(self.emu.dspi[dev].registers.mcr.halt, 1, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txrxs, 0, msg=testmsg)

                # Should be able to write again
                self.assertEqual(self.emu.dspi[dev].registers.sr.tfff, 1, msg=testmsg)

                # There should be TCF, EOQ, and TFFF interrupts queued
                expected = DSPI_SR_TCF_MASK | DSPI_SR_EOQF_MASK | DSPI_SR_TFFF_MASK | \
                        (1 << DSPI_SR_TXCTR_SHIFT)
                self.assertEqual(self.emu.readMemValue(sr_addr, 4), expected, msg=testmsg)
                expected_excs = [
                    get_int(dev, 'tfff'),
                    get_int(dev, 'tcf'),
                    get_int(dev, 'eoqf'),
                ]
                self.assertEqual(self._getPendingExceptions(), expected_excs, msg=testmsg)

                # Clear the TCF, EOQ, and TFFF interrupt flags
                self.emu.writeMemValue(sr_addr, expected, 4)
                expected = 1 << DSPI_SR_TXCTR_SHIFT
                self.assertEqual(self.emu.readMemValue(sr_addr, 4), expected, msg=testmsg)

                # Verify that only three frames were sent and there is still 1 msg
                # in the Tx FIFO
                self.assertEqual(self.emu.dspi[dev].registers.sr.txctr, 1, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txnxtptr, 0, msg=testmsg)

                # Clear the transmit fifo
                val = (mstr_flag << DSPI_MCR_MSTR_SHIFT) | DSPI_MCR_CLR_TXF_MASK | DSPI_MCR_HALT_MASK
                self.emu.writeMemValue(mcr_addr, val, 4)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txctr, 0, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txnxtptr, 0, msg=testmsg)

                # Only 3 (or 4) messages sent so far
                self.assertEqual(self.emu.dspi[dev].registers.tcr.spi_tcnt, start_tcnt + 3, msg=testmsg)
                expected_tcnt = (start_tcnt + 3) << DSPI_TCR_TCNT_SHIFT
                self.assertEqual(self.emu.readMemValue(tcr_addr, 4), expected_tcnt, msg=testmsg)

                # Verify the message values in the transmit queue match the expected
                # value for msgs 0, 1, and 2.
                txd_msgs = self.emu.dspi[dev].getTransmittedObjs()
                self.assertEqual(txd_msgs, expected_msgs[:3], msg=testmsg)

                # Manually change the transmit count to the 0xFFFF so after sending
                # 2 more messages the TCNT will have wrapped around to 1
                self.emu.writeMemValue(tcr_addr, 0xFFFF0000, 4)
                self.assertEqual(self.emu.dspi[dev].registers.tcr.spi_tcnt, 0xFFFF, msg=testmsg)

                # Fill the queue again
                self.emu.writeMemValue(pushr_addr, pushr_values[4], 4)
                self.assertEqual(self.emu.dspi[dev].registers.sr.tfff, 1, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txctr, 1, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txnxtptr, 0, msg=testmsg)

                self.emu.writeMemValue(pushr_addr, pushr_values[5], 4)
                self.assertEqual(self.emu.dspi[dev].registers.sr.tfff, 1, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txctr, 2, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txnxtptr, 1, msg=testmsg)

                self.emu.writeMemValue(pushr_addr, pushr_values[6], 4)
                self.assertEqual(self.emu.dspi[dev].registers.sr.tfff, 1, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txctr, 3, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txnxtptr, 2, msg=testmsg)

                # The TFFF flag won't get be zero after adding the next message
                # unless it is cleared first
                self.emu.writeMemValue(sr_addr, DSPI_SR_TFFF_MASK, 4)
                # Confirm the exception is queued also
                expected_excs = [
                    get_int(dev, 'tfff'),
                ]
                self.assertEqual(self._getPendingExceptions(), expected_excs, msg=testmsg)

                self.emu.writeMemValue(pushr_addr, pushr_values[7], 4)
                self.assertEqual(self.emu.dspi[dev].registers.sr.tfff, 0, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txctr, 4, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txnxtptr, 3, msg=testmsg)

                # Verify that the data in the Tx FIFO matches what is expected based
                # on the msg data written msg 0 should be at the last position of
                # the Tx FIFO
                for i, txf_offset in zip(reversed(range(4, 8)), DSPI_TXFR_RANGE):
                    msg = '%s(%s) TXF[%d]' % (devname, expected_mode.name, i)
                    txf_addr = baseaddr + txf_offset
                    self.assertEqual(self.emu.readMemValue(txf_addr, 4), pushr_values[i], msg=msg)

                # Enable Tx/Rx
                self.assertEqual(self.emu.dspi[dev].registers.sr.eoqf, 0, msg=testmsg)
                val = (mstr_flag << DSPI_MCR_MSTR_SHIFT)
                self.emu.writeMemValue(mcr_addr, val, 4)

                # After the write is complete Tx/Rx should be enabled until the EOQ
                # message is hit.  By the time writeMemValue() returns the
                # peripheral should be halted again.
                self.assertEqual(self.emu.dspi[dev].registers.mcr.halt, 1, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txrxs, 0, msg=testmsg)

                # Should be able to write again
                self.assertEqual(self.emu.dspi[dev].registers.sr.tfff, 1, msg=testmsg)

                # There should be TCF, EOQ, and TFFF interrupts queued
                expected = DSPI_SR_TCF_MASK | DSPI_SR_EOQF_MASK | DSPI_SR_TFFF_MASK | \
                        (2 << DSPI_SR_TXCTR_SHIFT) | (1 << DSPI_SR_TXNXTPTR_SHIFT)
                self.assertEqual(self.emu.readMemValue(sr_addr, 4), expected, msg=testmsg)
                expected_excs = [
                    get_int(dev, 'tfff'),
                    get_int(dev, 'tcf'),
                    get_int(dev, 'eoqf'),
                ]
                self.assertEqual(self._getPendingExceptions(), expected_excs, msg=testmsg)

                # Clear the TCF, EOQ, and TFFF interrupt flags
                self.emu.writeMemValue(sr_addr, expected, 4)
                expected = (2 << DSPI_SR_TXCTR_SHIFT) | (1 << DSPI_SR_TXNXTPTR_SHIFT)
                self.assertEqual(self.emu.readMemValue(sr_addr, 4), expected, msg=testmsg)

                # Verify that three frames were sent and there is 2 frames left in
                # the Tx FIFO
                self.assertEqual(self.emu.dspi[dev].registers.sr.txctr, 2, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txnxtptr, 1, msg=testmsg)

                # The transmit count should have wrapped around to 1
                self.assertEqual(self.emu.dspi[dev].registers.tcr.spi_tcnt, 1, msg=testmsg)
                self.assertEqual(self.emu.readMemValue(tcr_addr, 4), 0x00010000, msg=testmsg)

                # Verify the message values in the transmit queue match the expected
                # value for msgs 4 and 5
                txd_msgs = self.emu.dspi[dev].getTransmittedObjs()
                self.assertEqual(txd_msgs, expected_msgs[4:6], msg=testmsg)

                # Enable Tx/Rx to transmit the last message
                self.assertEqual(self.emu.dspi[dev].registers.sr.eoqf, 0, msg=testmsg)
                val = (mstr_flag << DSPI_MCR_MSTR_SHIFT)
                self.emu.writeMemValue(mcr_addr, val, 4)

                # After the write is complete Tx/Rx will continue until the Tx FIFO
                # is exhausted, because the EOQ flag was not set TXRXS will still be
                # set so HALT will be 0
                self.assertEqual(self.emu.dspi[dev].registers.mcr.halt, 0, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txrxs, 1, msg=testmsg)

                # There should be TCF, and TFFF interrupts queued.  This time the
                # EOQ flag should not be set because the last message did not have
                # the EOQ bit set in the command portion of the messages.
                expected = DSPI_SR_TCF_MASK | DSPI_SR_TXRXS_MASK | DSPI_SR_TFFF_MASK
                self.assertEqual(self.emu.readMemValue(sr_addr, 4), expected, msg=testmsg)
                expected_excs = [
                    get_int(dev, 'tfff'),
                    get_int(dev, 'tcf'),
                ]
                self.assertEqual(self._getPendingExceptions(), expected_excs, msg=testmsg)

                # Clear the interrupt flags
                self.emu.writeMemValue(sr_addr, expected, 4)
                expected = DSPI_SR_TXRXS_MASK
                self.assertEqual(self.emu.readMemValue(sr_addr, 4), expected, msg=testmsg)

                # Verify that there are no more frames remaining in the Tx FIFO
                self.assertEqual(self.emu.dspi[dev].registers.sr.txctr, 0, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txnxtptr, 0, msg=testmsg)

                # The CTCNT bit was set in the last message's command so TCNT was
                # cleared back to 0 before the message is sent, therefore the TCNT
                # will be 1 now.
                self.assertEqual(self.emu.dspi[dev].registers.tcr.spi_tcnt, 1, msg=testmsg)
                self.assertEqual(self.emu.readMemValue(tcr_addr, 4), 0x00010000, msg=testmsg)

                # Verify there is are two remaining messages that has been
                # transmitted, msgs 6 and 7
                txd_msgs = self.emu.dspi[dev].getTransmittedObjs()
                self.assertEqual(txd_msgs, expected_msgs[6:], msg=testmsg)

    def test_dspi_controller_rx(self):
        # The transmit behavior should be the same for both controller and
        # peripheral
        device_modes = (
            # MCR[MSTR] | DSPI mode
            (1, dspi.DSPI_MODE.SPI_CNTRLR),
            (0, dspi.DSPI_MODE.SPI_PERIPH),
        )

        # Value to enable all interrupts
        rser_val = DSPI_RSER_TCF_MASK | DSPI_RSER_EOQF_MASK | \
                DSPI_RSER_TFUF_MASK | DSPI_RSER_TFFF_MASK | \
                DSPI_RSER_RFOF_MASK | DSPI_RSER_RFDF_MASK

        for dev in range(len(DSPI_DEVICES)):
            devname, baseaddr = DSPI_DEVICES[dev]
            self.assertEqual(self.emu.dspi[dev].devname, devname)

            mcr_addr = baseaddr + DSPI_MCR_OFFSET
            tcr_addr = baseaddr + DSPI_TCR_OFFSET
            popr_addr = baseaddr + DSPI_POPR_OFFSET
            sr_addr = baseaddr + DSPI_SR_OFFSET
            rser_addr = baseaddr + DSPI_RSER_OFFSET

            # Before the first pass of this test the default state of the
            # SR[TFFF] flag is 1, after that no messages will be transmitted so
            # clear the TFFF flag now.
            self.assertEqual(self.emu.readMemValue(sr_addr, 4), DSPI_SR_TFFF_MASK, msg=devname)
            self.assertEqual(self.emu.dspi[dev].registers.sr.tfff, 1, msg=devname)
            self.emu.writeMemValue(sr_addr, DSPI_SR_TFFF_MASK, 4)

            # For both controller and peripheral mode
            for mstr_flag, expected_mode in device_modes:
                testmsg = '%s(%s)' % (devname, expected_mode.name)

                # Generate 8 unique message values, data can be between 4 and 16
                # bits (to be consistent with the Tx data), so generate test
                # values with a max of 65535
                msgs = [random.randrange(0x0001, 0xFFFF + 1) for i in range(8)]

                # Change to controller mode
                val = (mstr_flag << DSPI_MCR_MSTR_SHIFT) | DSPI_MCR_HALT_MASK
                self.emu.writeMemValue(mcr_addr, val, 4)
                self.assertEqual(self.emu.dspi[dev].mode, expected_mode, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.mcr.rooe, 0, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.mcr.halt, 1, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txrxs, 0, msg=testmsg)

                # Enable all interrupt sources
                self.emu.writeMemValue(rser_addr, rser_val, 4)

                # No messages in Rx FIFO
                self.assertEqual(self.emu.dspi[dev].registers.sr.rxctr, 0)

                # send Rx data to the peripheral and ensure it is discarded
                self.emu.dspi[dev].processReceivedData(msgs[0])

                # No messages in Rx FIFO
                self.assertEqual(self.emu.dspi[dev].registers.sr.rxctr, 0)

                # Enable Tx/Rx
                val = (mstr_flag << DSPI_MCR_MSTR_SHIFT)
                self.emu.writeMemValue(mcr_addr, val, 4)
                self.assertEqual(self.emu.dspi[dev].mode, expected_mode, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.mcr.rooe, 0, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.mcr.halt, 0, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txrxs, 1, msg=testmsg)

                # No messages in Rx FIFO
                self.assertEqual(self.emu.dspi[dev].registers.sr.rxctr, 0)

                # receive 1 msg, make sure the RFDF event has occurred
                self.emu.dspi[dev].processReceivedData(msgs[1])

                expected = DSPI_SR_TXRXS_MASK | DSPI_SR_RFDF_MASK | \
                        (1 << DSPI_SR_RXCTR_SHIFT)
                self.assertEqual(self.emu.readMemValue(sr_addr, 4), expected, msg=testmsg)
                expected_excs = [
                    get_int(dev, 'rfdf'),
                ]
                self.assertEqual(self._getPendingExceptions(), expected_excs, msg=testmsg)

                # Clear the RFDF interrupt flag
                self.emu.writeMemValue(sr_addr, expected, 4)
                expected = DSPI_SR_TXRXS_MASK | (1 << DSPI_SR_RXCTR_SHIFT)
                self.assertEqual(self.emu.readMemValue(sr_addr, 4), expected, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.rxctr, 1)

                # receive 3 more msgs, make sure the RFOF event has not occurred
                # yet
                self.emu.dspi[dev].processReceivedData(msgs[2])
                self.emu.dspi[dev].processReceivedData(msgs[3])
                self.emu.dspi[dev].processReceivedData(msgs[4])

                expected = DSPI_SR_TXRXS_MASK | DSPI_SR_RFDF_MASK | \
                        (4 << DSPI_SR_RXCTR_SHIFT)
                self.assertEqual(self.emu.readMemValue(sr_addr, 4), expected, msg=testmsg)
                expected_excs = [
                    get_int(dev, 'rfdf'),
                ]
                self.assertEqual(self._getPendingExceptions(), expected_excs, msg=testmsg)

                # Clear the RFDF interrupt flag
                self.emu.writeMemValue(sr_addr, expected, 4)
                expected = DSPI_SR_TXRXS_MASK | (4 << DSPI_SR_RXCTR_SHIFT)
                self.assertEqual(self.emu.readMemValue(sr_addr, 4), expected, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.rxctr, 4)

                # receive 1 more msg, make sure the RFOF event has not occurred,
                # and that the RXCTR maxes out at 4, but the Rx FIFO (including
                # "shift register") has the 5 messages just received.
                self.emu.dspi[dev].processReceivedData(msgs[5])

                expected = DSPI_SR_TXRXS_MASK | DSPI_SR_RFDF_MASK | \
                        (4 << DSPI_SR_RXCTR_SHIFT)
                self.assertEqual(self.emu.readMemValue(sr_addr, 4), expected, msg=testmsg)
                expected_excs = [
                    get_int(dev, 'rfdf'),
                ]
                self.assertEqual(self._getPendingExceptions(), expected_excs, msg=testmsg)

                # Clear the RFDF interrupt flag
                self.emu.writeMemValue(sr_addr, expected, 4)
                expected = DSPI_SR_TXRXS_MASK | (4 << DSPI_SR_RXCTR_SHIFT)
                self.assertEqual(self.emu.readMemValue(sr_addr, 4), expected, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.rxctr, 4)

                # Verify that the data in the Rx FIFO matches what is expected based
                # on the received msg data written
                for i, rxf_offset in zip(range(1, 5), DSPI_RXFR_RANGE):
                    msg = '%s(%s) RXF[%d]' % (devname, expected_mode.name, i)
                    rxf_addr = baseaddr + rxf_offset
                    self.assertEqual(self.emu.readMemValue(rxf_addr, 4), msgs[i], msg=msg)

                # Check the contents of the shift register
                rx_fifo_data = struct.pack('>IIIII',
                        msgs[1], msgs[2], msgs[3], msgs[4], msgs[5])
                self.assertEqual(self.emu.dspi[dev]._rx_fifo, rx_fifo_data, msg=testmsg)

                # receive 1 more msg, nothing changes, shift register is not
                # overwritten, but the RFOF interrupt has been set
                self.emu.dspi[dev].processReceivedData(msgs[6])

                expected = DSPI_SR_TXRXS_MASK | DSPI_SR_RFOF_MASK | \
                        (4 << DSPI_SR_RXCTR_SHIFT)
                self.assertEqual(self.emu.readMemValue(sr_addr, 4), expected, msg=testmsg)
                expected_excs = [
                    get_int(dev, 'rfof'),
                ]
                self.assertEqual(self._getPendingExceptions(), expected_excs, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.rxctr, 4)
                self.assertEqual(self.emu.dspi[dev]._rx_fifo, rx_fifo_data, msg=testmsg)

                # Clear the RFOF interrupt flag
                self.emu.writeMemValue(sr_addr, expected, 4)
                expected = DSPI_SR_TXRXS_MASK | (4 << DSPI_SR_RXCTR_SHIFT)
                self.assertEqual(self.emu.readMemValue(sr_addr, 4), expected, msg=testmsg)

                # set MCR[ROOE] and receive 1 more message, ensure new message
                # was placed on the shift register, and the RFOF interrupt has
                # been signaled again.
                val = (mstr_flag << DSPI_MCR_MSTR_SHIFT) | DSPI_MCR_ROOE_MASK
                self.emu.writeMemValue(mcr_addr, val, 4)
                self.assertEqual(self.emu.dspi[dev].mode, expected_mode, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.mcr.rooe, 1, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.mcr.halt, 0, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.txrxs, 1, msg=testmsg)

                self.emu.dspi[dev].processReceivedData(msgs[7])

                expected = DSPI_SR_TXRXS_MASK | DSPI_SR_RFOF_MASK | \
                        (4 << DSPI_SR_RXCTR_SHIFT)
                self.assertEqual(self.emu.readMemValue(sr_addr, 4), expected, msg=testmsg)
                expected_excs = [
                    get_int(dev, 'rfof'),
                ]
                self.assertEqual(self._getPendingExceptions(), expected_excs, msg=testmsg)
                self.assertEqual(self.emu.readMemValue(sr_addr, 4), expected, msg=testmsg)
                self.assertEqual(self.emu.dspi[dev].registers.sr.rxctr, 4)

                # Clear the RFOF interrupt flag
                self.emu.writeMemValue(sr_addr, expected, 4)
                expected = DSPI_SR_TXRXS_MASK | (4 << DSPI_SR_RXCTR_SHIFT)
                self.assertEqual(self.emu.readMemValue(sr_addr, 4), expected, msg=testmsg)

                # Verify that the data in the Rx FIFO hasn't changed
                for i, rxf_offset in zip(range(1, 5), DSPI_RXFR_RANGE):
                    msg = '%s(%s) RXF[%d]' % (devname, expected_mode.name, i)
                    rxf_addr = baseaddr + rxf_offset
                    self.assertEqual(self.emu.readMemValue(rxf_addr, 4), msgs[i], msg=msg)

                # Check the contents of the shift register
                rx_fifo_data = struct.pack('>IIIII',
                        msgs[1], msgs[2], msgs[3], msgs[4], msgs[7])
                self.assertEqual(self.emu.dspi[dev]._rx_fifo, rx_fifo_data, msg=testmsg)

                # Expected order that messages will be read from the POPR
                # register, and the RXCTR values after they are read
                read_vals = (
                    (msgs[1], 4),
                    (msgs[2], 3),
                    (msgs[3], 2),
                    (msgs[4], 1),
                    (msgs[7], 0)
                )
                # receive all messages
                for msg_val, rxctr_val in read_vals:
                    msg = '%s(%s) POPR = 0x%x, RXCTR = 0x%x' % (devname, expected_mode.name, msg_val, rxctr_val)
                    self.assertEqual(self.emu.readMemValue(popr_addr, 4), msg_val, msg=msg)

                    # Every time a value is read from POPR the RFDF event is
                    # re-evaluated
                    if rxctr_val:
                        expected = DSPI_SR_TXRXS_MASK | DSPI_SR_RFDF_MASK | \
                                (rxctr_val << DSPI_SR_RXCTR_SHIFT)
                        self.assertEqual(self.emu.readMemValue(sr_addr, 4), expected, msg=msg)
                        expected_excs = [
                            get_int(dev, 'rfdf'),
                        ]
                        self.assertEqual(self._getPendingExceptions(), expected_excs, msg=msg)
                        self.emu.writeMemValue(sr_addr, expected, 4)

                    expected = DSPI_SR_TXRXS_MASK | (rxctr_val << DSPI_SR_RXCTR_SHIFT)
                    self.assertEqual(self.emu.readMemValue(sr_addr, 4), expected, msg=msg)
                    self.assertEqual(self.emu.dspi[dev].registers.sr.rxctr, rxctr_val, msg=msg)

    @unittest.skip('Implement test after DSPI DSI mode is supported')
    def test_dspi_peripheral_dsi(self):
        pass

    @unittest.skip('Implement test after DSPI CSI mode is supported')
    def test_dspi_peripheral_csi(self):
        pass
