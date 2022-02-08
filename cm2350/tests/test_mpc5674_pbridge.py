import unittest
import os
import queue

import envi.archs.ppc.const as eapc
import envi.archs.ppc.regs as eapr

from cm2350 import intc_exc

from .. import CM2350


PBRIDGE_DEVICES = (
    ('PBRIDGE_A', 0XC3F00000),
    ('PBRIDGE_B', 0XFFF00000),
)


PBRIDGE_x_MPCR_OFFSET         = 0x0000

# PBRIDGE_A has only 1 PACR register, PBRIDGE_B has 3
PBRIDGE_x_PACRn_RANGE = (
    range(0x0020, 0x0024, 4),
    range(0x0020, 0x002C, 4),
)

# Both PBRIDGE controllers have the same number of OPACR registers
PBRIDGE_x_OPACRn_RANGE = (
    range(0x0040, 0x0050, 4),
    range(0x0040, 0x0050, 4),
)

PBRIDGE_x_MPCR_DEFAULT_VALUE  = 0x77777777
PBRIDGE_x_MPCR_DEFAULT        = b'\x77\x77\x77\x77'
PBRIDGE_x_PACR_DEFAULT_VALUE  = 0x44444444
PBRIDGE_x_PACR_DEFAULT        = b'\x44\x44\x44\x44'
PBRIDGE_x_OPACR_DEFAULT_VALUE = 0x44444444
PBRIDGE_x_OPACR_DEFAULT       = b'\x44\x44\x44\x44'


class MPC5674_PBRIDGE_Test(unittest.TestCase):
    def setUp(self):
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
    # Tests
    ##################################################

    def test_pbridge(self):
        for idx, (devname, baseaddr) in enumerate(PBRIDGE_DEVICES):
            self.assertEqual(self.emu.pbridge[idx].devname, devname)

            addr = baseaddr + PBRIDGE_x_MPCR_OFFSET
            self.assertEqual(self.emu.readMemValue(addr,4), PBRIDGE_x_MPCR_DEFAULT_VALUE, msg=devname)
            self.assertEqual(self.emu.readMemory(addr,4), PBRIDGE_x_MPCR_DEFAULT, msg=devname)

            for pacr_offset in PBRIDGE_x_PACRn_RANGE[idx]:
                msg = '%s PACR%d' % (devname, idx)
                addr = baseaddr + pacr_offset
                self.assertEqual(self.emu.readMemValue(addr,4), PBRIDGE_x_PACR_DEFAULT_VALUE, msg=msg)
                self.assertEqual(self.emu.readMemory(addr,4), PBRIDGE_x_PACR_DEFAULT, msg=msg)

            for opacr_offset in PBRIDGE_x_OPACRn_RANGE[idx]:
                msg = '%s OPACR%d' % (devname, idx)
                addr = baseaddr + opacr_offset
                self.assertEqual(self.emu.readMemValue(addr,4), PBRIDGE_x_OPACR_DEFAULT_VALUE, msg=msg)
                self.assertEqual(self.emu.readMemory(addr,4), PBRIDGE_x_OPACR_DEFAULT, msg=msg)
