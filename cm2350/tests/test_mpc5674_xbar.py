import unittest
import os
import queue

import envi.archs.ppc.const as eapc
import envi.archs.ppc.regs as eapr

from cm2350 import intc_exc

from .. import CM2350
from ..ppc_xbar import XBAR_SLAVE


# The XBAR peripheral has MPR and SGPCR registers for each slave device on the
# processor bus.  These are captured in the cm2350.ppc_xbar.XBAR_PORTS type:
#   FLASH       = 0
#   EBI         = 1
#   RAM         = 2
#   PBRIDGE_A   = 6
#   PBRIDGE_B   = 7
#
# There is a set of MPR/SGPCR registers for each XBAR slave.
XBAR_BASE_ADDR            = 0xFFF04000
XBAR_MPRn_OFFSET          = 0x0000
XBAR_SGPCRn_OFFSET        = 0x0010
XBAR_MPRn_ADDRS           = [XBAR_BASE_ADDR + (n*0x100) + XBAR_MPRn_OFFSET   for n in XBAR_SLAVE]
XBAR_SGPCRn_ADDRS         = [XBAR_BASE_ADDR + (n*0x100) + XBAR_SGPCRn_OFFSET for n in XBAR_SLAVE]

XBAR_MPCRn_DEFAULT_VALUE  = 0x54320010
XBAR_MPCRn_DEFAULT        = b'\x54\x32\x00\x10'
XBAR_SGPCRn_DEFAULT_VALUE = 0x00000000
XBAR_SGPCRn_DEFAULT       = b'\x00\x00\x00\x00'


class MPC5674_XBAR_Test(unittest.TestCase):
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

    def test_xbar(self):
        for mpr_addr, sgpcr_addr in zip(XBAR_MPRn_ADDRS, XBAR_SGPCRn_ADDRS):
            self.assertEqual(self.emu.readMemValue(mpr_addr,4), XBAR_MPCRn_DEFAULT_VALUE)
            self.assertEqual(self.emu.readMemory(mpr_addr,4), XBAR_MPCRn_DEFAULT)
            self.assertEqual(self.emu.readMemValue(sgpcr_addr,4), XBAR_SGPCRn_DEFAULT_VALUE)
            self.assertEqual(self.emu.readMemory(sgpcr_addr,4), XBAR_SGPCRn_DEFAULT)
