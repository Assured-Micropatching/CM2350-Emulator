from ..ppc_xbar import XBAR_SLAVE

from .helpers import MPC5674_Test


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


class MPC5674_XBAR_Test(MPC5674_Test):

    ##################################################
    # Tests
    ##################################################

    def test_xbar(self):
        for mpr_addr, sgpcr_addr in zip(XBAR_MPRn_ADDRS, XBAR_SGPCRn_ADDRS):
            self.assertEqual(self.emu.readMemValue(mpr_addr,4), XBAR_MPCRn_DEFAULT_VALUE)
            self.assertEqual(self.emu.readMemory(mpr_addr,4), XBAR_MPCRn_DEFAULT)
            self.assertEqual(self.emu.readMemValue(sgpcr_addr,4), XBAR_SGPCRn_DEFAULT_VALUE)
            self.assertEqual(self.emu.readMemory(sgpcr_addr,4), XBAR_SGPCRn_DEFAULT)
