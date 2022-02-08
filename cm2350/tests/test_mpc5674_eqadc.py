import os
import queue
import random
import struct
import unittest

from cm2350 import CM2350, intc_exc
from cm2350.peripherals import eqadc

import envi.archs.ppc.regs as eapr
import envi.archs.ppc.const as eapc


EQADC_DEVICES = (
    ('eQADC_A', 0xFFF80000),
    ('eQADC_B', 0xFFF84000),
)

EQADC_MCR                 = (0x0000, 4)
EQADC_ETDFR               = (0x000C, 4)
EQADC_CFPR                = (range(0x0010, 0x0028, 4), 4)
EQADC_RFPR                = (range(0x0030, 0x0048, 4), 4)
EQADC_CFCR                = (range(0x0050, 0x005C, 2), 2)
EQADC_IDCR                = (range(0x0060, 0x006C, 2), 2)
EQADC_FISR                = (range(0x0070, 0x0088, 4), 4)
EQADC_CFTCR               = (range(0x0090, 0x009C, 2), 2)
EQADC_CFSSR               = (range(0x00A0, 0x00A8, 4), 4)
EQADC_CFSR                = (0x00AC, 4)
EQADC_REDLCCR             = (0x00D0, 4)

# The Command and Result FIFO buffer addresses are weird, the FIFOs are 4
# registers deep for each of the 6 channels. Each channel's FIFO registers are
# consecutive, but separated by n offset of 0x40 for each channel. These
# constants just define the initial register offset, tests will use the
# EQADC_NUM_CFIFO_SIZE and EQADC_NUM_RFIFO_SIZE constants to increment the base
# register.
EQADC_CFxRw               = (range(0x0100, 0x0250, 0x40), 4)
EQADC_RFxRw               = (range(0x0300, 0x0450, 0x40), 4)

# Number of ADC channels and command/result FIFOs.  CFIFO0 can be 4 or 8 entries
# deep.
EQADC_NUM_CHANNELS        = 6
EQADC_NUM_CFIFO0_SIZE     = 8
EQADC_NUM_CFIFO_SIZE      = 4
EQADC_NUM_RFIFO_SIZE      = 4

# Test masks and shifts
EQADC_IDCR_NCF_MASK       = 0x8000
EQADC_IDCR_TORF_MASK      = 0x4000
EQADC_IDCR_PF_MASK        = 0x2000
EQADC_IDCR_EOQF_MASK      = 0x1000
EQADC_IDCR_CFUF_MASK      = 0x0800
EQADC_IDCR_CFFF_MASK      = 0x0200
EQADC_IDCR_CFFS_MASK      = 0x0100
EQADC_IDCR_RFOF_MASK      = 0x0008
EQADC_IDCR_RFDF_MASK      = 0x0002
EQADC_IDCR_RFDS_MASK      = 0x0001

EQADC_FISR_NCF_MASK       = 0x80000000
EQADC_FISR_TORF_MASK      = 0x40000000
EQADC_FISR_PF_MASK        = 0x20000000
EQADC_FISR_EOQF_MASK      = 0x10000000
EQADC_FISR_CFUF_MASK      = 0x08000000
EQADC_FISR_SSS_MASK       = 0x04000000
EQADC_FISR_CFFF_MASK      = 0x02000000
EQADC_FISR_RFOF_MASK      = 0x00080000
EQADC_FISR_RFDF_MASK      = 0x00020000
EQADC_FISR_CFCTR_MASK     = 0x0000F000
EQADC_FISR_TNXTPTR_MASK   = 0x00000F00
EQADC_FISR_RFCTR_MASK     = 0x000000F0
EQADC_FISR_POPNXTPTR_MASK = 0x0000000F

EQADC_CFTCR_MASK          = 0x07FF

# defaults
EQADC_FISR_DEFAULT       = 0x02000000
EQADC_FISR_DEFAULT_BYTES = b'\x02\x00\x00\x00'


def get_int_src(dev, channel, event):
    """
    Calculate the correct external interrupt source for a EQADC device and event
    values are from
    "Table 9-8. Interrupt Request Sources" (MPC5674FRM.pdf page 325-341)
      EQADC_FISRx[TORF/RFOF/CFUF] = 100
      EQADC_FISRx[TORF/RFOF/CFUF] = 394

    Parameters:
        dev   (int): indicating EQADC A (0) to B (1)
        event (str): the event to return the interrupt source for

    Return:
        interrupt source value (int)
    """
    if event in ('torf', 'rorf', 'cfuf'):
        # torf, rorf, and cfuf all use the base event ID
        base = (100, 394)[dev]
        return base
    else:
        # The other events are based on which channel the event is for
        base = (101, 395)[dev] + (channel * 5)
        offset = {'ncf': 0, 'pf': 1, 'eoqf': 2, 'cfff': 3, 'rfdf': 4}[event]
        return base + offset


def get_int(dev, event):
    """
    Returns an ExternalException object that corresponds to a queued exception
    associated with a specific EQADC device and event.

    Parameters:
        dev   (int): indicating EQADC A (0) to B (1)
        event (str): the event to return the interrupt source for

    Return:
        interrupt source value (int)
    """
    return intc_exc.ExternalException(intc_exc.INTC_SRC(get_int_src(dev, event)))


class MPC5674_EQADC_Test(unittest.TestCase):
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

    def test_eqadc_mcr(self):
        for dev in range(len(EQADC_DEVICES)):
            devname, baseaddr = EQADC_DEVICES[dev]
            self.assertEqual(self.emu.eqadc[dev].devname, devname)

            offset, size = EQADC_MCR
            addr = baseaddr + offset

            self.assertEqual(self.emu.readMemory(addr, size), b'\x00' * size, msg=devname)
            self.assertEqual(self.emu.readMemValue(addr, size), 0, msg=devname)
            self.assertEqual(self.emu.eqadc[dev].registers.mcr.icea, 0, msg=devname)
            self.assertEqual(self.emu.eqadc[dev].registers.mcr.dbg, 0, msg=devname)

    def test_eqadc_etdfr(self):
        for dev in range(len(EQADC_DEVICES)):
            devname, baseaddr = EQADC_DEVICES[dev]
            self.assertEqual(self.emu.eqadc[dev].devname, devname)

            offset, size = EQADC_ETDFR
            addr = baseaddr + offset

            self.assertEqual(self.emu.readMemory(addr, size), b'\x00' * size, msg=devname)
            self.assertEqual(self.emu.readMemValue(addr, size), 0, msg=devname)
            self.assertEqual(self.emu.eqadc[dev].registers.etdfr.dfl, 0, msg=devname)

    def test_eqadc_cfpr(self):
        for dev in range(len(EQADC_DEVICES)):
            devname, baseaddr = EQADC_DEVICES[dev]
            self.assertEqual(self.emu.eqadc[dev].devname, devname)

            addr_range, size = EQADC_CFPR
            for channel, offset in enumerate(addr_range):
                # The read address already incorporates the channel
                addr = baseaddr + offset
                msg = '%s[%d]' % (devname, channel)

                self.assertEqual(self.emu.readMemory(addr, size), b'\x00' * size, msg=msg)
                self.assertEqual(self.emu.readMemValue(addr, size), 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].cfifo[channel][:size], b'\x00' * size, msg=msg)

                rand_data = os.urandom(size)
                self.emu.eqadc[dev].cfifo[channel][:size] = rand_data

                # Reads of the CFPR register should always be 0
                self.assertEqual(self.emu.readMemValue(addr, size), 0, msg=msg)

    def test_eqadc_rfpr(self):
        for dev in range(len(EQADC_DEVICES)):
            devname, baseaddr = EQADC_DEVICES[dev]
            self.assertEqual(self.emu.eqadc[dev].devname, devname)

            addr_range, size = EQADC_RFPR
            for channel, offset in enumerate(addr_range):
                addr = baseaddr + offset
                msg = '%s[%d]' % (devname, channel)

                self.assertEqual(self.emu.readMemory(addr, size), b'\x00' * size, msg=msg)
                self.assertEqual(self.emu.readMemValue(addr, size), 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].rfifo[channel][:size], b'\x00' * size, msg=msg)

                rand_data = os.urandom(size)
                self.emu.eqadc[dev].rfifo[channel][:size] = rand_data

                # The data read from RFPR depends on the current count of
                # pending results.  Reading the RFPR when the result count is 0
                # means 0x00000000 is returned
                self.assertEqual(self.emu.readMemory(addr, size), b'\x00' * size, msg=msg)

                # Set the rfctr to 1 and the random data written to the RFIFO
                # should now be readable
                self.emu.eqadc[dev].registers.fisr[channel].vsOverrideValue('rfctr', 1)
                self.assertEqual(self.emu.readMemory(addr, size), rand_data, msg=msg)

    def test_eqadc_cfcr(self):
        for dev in range(len(EQADC_DEVICES)):
            devname, baseaddr = EQADC_DEVICES[dev]
            self.assertEqual(self.emu.eqadc[dev].devname, devname)

            addr_range, size = EQADC_CFCR
            for channel, offset in enumerate(addr_range):
                addr = baseaddr + offset
                msg = '%s[%d]' % (devname, channel)

                self.assertEqual(self.emu.readMemory(addr, size), b'\x00' * size, msg=msg)
                self.assertEqual(self.emu.readMemValue(addr, size), 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.cfcr[channel].sse, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.cfcr[channel].cfinv, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.cfcr[channel].mode, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.cfcr[channel].amode0, 0, msg=msg)

                # CFEEE0 and STRME0 are technically only valid for channel 0 but
                # exist in all of the register definitions
                self.assertEqual(self.emu.eqadc[dev].registers.cfcr[channel].cfeee0, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.cfcr[channel].strme0, 0, msg=msg)

    def test_eqadc_idcr(self):
        for dev in range(len(EQADC_DEVICES)):
            devname, baseaddr = EQADC_DEVICES[dev]
            self.assertEqual(self.emu.eqadc[dev].devname, devname)

            # Ensure that the flags map correctly
            fields = (
                ('ncf',  1, EQADC_IDCR_NCF_MASK),
                ('torf', 1, EQADC_IDCR_TORF_MASK),
                ('pf',   1, EQADC_IDCR_PF_MASK),
                ('eoqf', 1, EQADC_IDCR_EOQF_MASK),
                ('cfuf', 1, EQADC_IDCR_CFUF_MASK),
                ('cfff', 1, EQADC_IDCR_CFFF_MASK),
                ('rfof', 1, EQADC_IDCR_RFOF_MASK),
                ('rfdf', 1, EQADC_IDCR_RFDF_MASK),

                # These fields are used to enable DMA transfers instead of
                # relying on software interrupt handlers.
                ('cffs', 1, EQADC_IDCR_CFFS_MASK),
                ('rfds', 1, EQADC_IDCR_RFDS_MASK),
            )

            addr_range, size = EQADC_IDCR
            for channel, offset in enumerate(addr_range):
                addr = baseaddr + offset
                msg = '%s[%d]' % (devname, channel)

                self.assertEqual(self.emu.readMemory(addr, size), b'\x00' * size, msg=msg)
                self.assertEqual(self.emu.readMemValue(addr, size), 0, msg=msg)
                # The bit fields that are ISR request bits use the same names as the
                # status register field names.
                self.assertEqual(self.emu.eqadc[dev].registers.idcr[channel].ncf, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.idcr[channel].torf, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.idcr[channel].pf, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.idcr[channel].eoqf, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.idcr[channel].cfuf, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.idcr[channel].cfff, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.idcr[channel].rfof, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.idcr[channel].rfdf, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.idcr[channel].rfds, 0, msg=msg)

                # DMA transfer flags
                self.assertEqual(self.emu.eqadc[dev].registers.idcr[channel].cffs, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.idcr[channel].rfds, 0, msg=msg)

                for field, field_val, idcr_val in fields:
                    msg = '%s[%d|%s]' % (devname, channel, field)
                    self.emu.eqadc[dev].registers.idcr[channel].vsSetField(field, field_val)
                    self.assertEqual(self.emu.readMemValue(addr, size), idcr_val, msg=msg)
                    self.emu.eqadc[dev].registers.idcr[channel].vsSetField(field, 0)
                    self.assertEqual(self.emu.readMemValue(addr, size), 0, msg=msg)

    def test_eqadc_fisr(self):
        for dev in range(len(EQADC_DEVICES)):
            devname, baseaddr = EQADC_DEVICES[dev]
            self.assertEqual(self.emu.eqadc[dev].devname, devname)

            # fields to test
            const_fields = (
                ('sss',         1, EQADC_FISR_SSS_MASK),
                ('cfctr',     0xF, EQADC_FISR_CFCTR_MASK),
                ('tnxtptr',   0xF, EQADC_FISR_TNXTPTR_MASK),
                ('rfctr',     0xF, EQADC_FISR_RFCTR_MASK),
                ('popnxtptr', 0xF, EQADC_FISR_POPNXTPTR_MASK),
            )

            w1c_fields = (
                ('ncf',         1, EQADC_FISR_NCF_MASK),
                ('torf',        1, EQADC_FISR_TORF_MASK),
                ('pf',          1, EQADC_FISR_PF_MASK),
                ('eoqf',        1, EQADC_FISR_EOQF_MASK),
                ('cfuf',        1, EQADC_FISR_CFUF_MASK),
                ('cfff',        1, EQADC_FISR_CFFF_MASK),
                ('rfof',        1, EQADC_FISR_RFOF_MASK),
                ('rfdf',        1, EQADC_FISR_RFDF_MASK),
            )

            addr_range, size = EQADC_FISR
            for channel, offset in enumerate(addr_range):
                addr = baseaddr + offset
                msg = '%s[%d]' % (devname, channel)

                self.assertEqual(self.emu.readMemory(addr, size), EQADC_FISR_DEFAULT_BYTES, msg=msg)
                self.assertEqual(self.emu.readMemValue(addr, size), EQADC_FISR_DEFAULT, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.fisr[channel].ncf, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.fisr[channel].torf, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.fisr[channel].pf, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.fisr[channel].eoqf, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.fisr[channel].cfuf, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.fisr[channel].cfff, 1, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.fisr[channel].rfof, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.fisr[channel].rfdf, 0, msg=msg)

                # the SSSx bit indicates if a single scan trigger is ready
                self.assertEqual(self.emu.eqadc[dev].registers.fisr[channel].sss, 0, msg=msg)

                # IDCR also holds the various count values
                self.assertEqual(self.emu.eqadc[dev].registers.fisr[channel].cfctr, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.fisr[channel].tnxtptr, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.fisr[channel].rfctr, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.fisr[channel].popnxtptr, 0, msg=msg)

                # Ensure that the flags map correctly, first clear CFFF so SR is
                # all 0.
                self.emu.eqadc[dev].registers.fisr[channel].vsOverrideValue('cfff', 0)
                self.assertEqual(self.emu.readMemValue(addr, size), 0, msg=msg)

                # test "constant" fields
                for field, field_val, fisr_val in const_fields:
                    msg = '%s[%d|%s]' % (devname, channel, field)
                    self.emu.eqadc[dev].registers.fisr[channel].vsOverrideValue(field, field_val)
                    self.assertEqual(self.emu.readMemValue(addr, size), fisr_val, msg=msg)
                    self.emu.eqadc[dev].registers.fisr[channel].vsOverrideValue(field, 0)
                    self.assertEqual(self.emu.readMemValue(addr, size), 0, msg=msg)

                # test "w1c" fields
                for field, field_val, fisr_val in w1c_fields:
                    msg = '%s[%d|%s]' % (devname, channel, field)
                    # Set the field
                    self.emu.eqadc[dev].registers.fisr[channel].vsOverrideValue(field, field_val)
                    self.assertEqual(self.emu.readMemValue(addr, size), fisr_val, msg=msg)
                    # Clear it by writing 1
                    self.emu.writeMemValue(addr, fisr_val, size)
                    self.assertEqual(self.emu.readMemValue(addr, size), 0, msg=msg)

    def test_eqadc_cftcr(self):
        for dev in range(len(EQADC_DEVICES)):
            devname, baseaddr = EQADC_DEVICES[dev]
            self.assertEqual(self.emu.eqadc[dev].devname, devname)

            addr_range, size = EQADC_CFTCR
            for channel, offset in enumerate(addr_range):
                addr = baseaddr + offset
                msg = '%s[%d]' % (devname, channel)

                self.assertEqual(self.emu.readMemory(addr, size), b'\x00' * size, msg=msg)
                self.assertEqual(self.emu.readMemValue(addr, size), 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.cftcr[channel].tc, 0, msg=msg)

                # Can write any value to it, but only the lower 11 bits will be
                # kept
                value = random.randrange(EQADC_CFTCR_MASK+1, size**(2*8))
                self.emu.writeMemValue(addr, value, size)
                self.assertEqual(self.emu.eqadc[dev].registers.cftcr[channel].tc, value & EQADC_CFTCR_MASK, msg=msg)

    def test_eqadc_cfssr(self):
        for dev in range(len(EQADC_DEVICES)):
            devname, baseaddr = EQADC_DEVICES[dev]
            self.assertEqual(self.emu.eqadc[dev].devname, devname)

            addr_range, size = EQADC_CFSSR
            for adc, offset in enumerate(addr_range):
                addr = baseaddr + offset
                msg = '%s[%d]' % (devname, adc)

                self.assertEqual(self.emu.readMemory(addr, size), b'\x00' * size, msg=msg)
                self.assertEqual(self.emu.readMemValue(addr, size), 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.cfssr[adc].cfs0, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.cfssr[adc].cfs1, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.cfssr[adc].cfs2, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.cfssr[adc].cfs3, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.cfssr[adc].cfs4, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.cfssr[adc].cfs5, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.cfssr[adc].lcftcb, 0, msg=msg)
                self.assertEqual(self.emu.eqadc[dev].registers.cfssr[adc].tc_lcftcb, 0, msg=msg)

    def test_eqadc_cfsr(self):
        for dev in range(len(EQADC_DEVICES)):
            devname, baseaddr = EQADC_DEVICES[dev]
            self.assertEqual(self.emu.eqadc[dev].devname, devname)

            offset, size = EQADC_CFSR
            addr = baseaddr + offset

            self.assertEqual(self.emu.readMemory(addr, size), b'\x00' * size, msg=devname)
            self.assertEqual(self.emu.readMemValue(addr, size), 0, msg=devname)
            self.assertEqual(self.emu.eqadc[dev].registers.cfsr.cfs0, 0, msg=devname)
            self.assertEqual(self.emu.eqadc[dev].registers.cfsr.cfs1, 0, msg=devname)
            self.assertEqual(self.emu.eqadc[dev].registers.cfsr.cfs2, 0, msg=devname)
            self.assertEqual(self.emu.eqadc[dev].registers.cfsr.cfs3, 0, msg=devname)
            self.assertEqual(self.emu.eqadc[dev].registers.cfsr.cfs4, 0, msg=devname)
            self.assertEqual(self.emu.eqadc[dev].registers.cfsr.cfs5, 0, msg=devname)

    def test_eqadc_redlccr(self):
        for dev in range(len(EQADC_DEVICES)):
            devname, baseaddr = EQADC_DEVICES[dev]
            self.assertEqual(self.emu.eqadc[dev].devname, devname)

            offset, size = EQADC_REDLCCR
            addr = baseaddr + offset

            self.assertEqual(self.emu.readMemory(addr, size), b'\x00' * size, msg=devname)
            self.assertEqual(self.emu.readMemValue(addr, size), 0, msg=devname)
            self.assertEqual(self.emu.eqadc[dev].registers.redlccr.redbs2, 0, msg=devname)
            self.assertEqual(self.emu.eqadc[dev].registers.redlccr.srv2, 0, msg=devname)
            self.assertEqual(self.emu.eqadc[dev].registers.redlccr.redbs1, 0, msg=devname)
            self.assertEqual(self.emu.eqadc[dev].registers.redlccr.srv1, 0, msg=devname)

    ##################################################
    # Functionality tests
    ##################################################

    @unittest.skip('implement test after accepting pre-programmed inputs is implemented')
    def test_eqadc_single_scan_sw_trigger(self):
        pass

    @unittest.skip('implement after periodic result updates are implemented')
    def test_eqadc_single_scan_trigger(self):
        pass

    @unittest.skip('implement after periodic result updates are implemented')
    def test_eqadc_continuous_scan(self):
        pass

    @unittest.skip('implement after single and continuous result tests are written')
    def test_eqadc_events(self):
        pass
