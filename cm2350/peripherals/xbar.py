from ..ppc_vstructs import *
from ..ppc_peripherals import *
from ..ppc_xbar import *

__all__  = [
    'XBAR',
]


XBAR_MPR0_OFFSET   = 0x0000
XBAR_SGPCR0_OFFSET = 0x0010
XBAR_MPR1_OFFSET   = 0x0100
XBAR_SGPCR1_OFFSET = 0x0110
XBAR_MPR2_OFFSET   = 0x0200
XBAR_SGPCR2_OFFSET = 0x0210
XBAR_MPR6_OFFSET   = 0x0600
XBAR_SGPCR6_OFFSET = 0x0610
XBAR_MPR7_OFFSET   = 0x0700
XBAR_SGPCR7_OFFSET = 0x0710


class XBAR_MPRn(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0  = v_const(5, 0b01010)
        self.mstr6  = v_defaultbits(3, 0b100)
        self._pad1  = v_const(1)
        self.mstr5  = v_defaultbits(3, 0b011)
        self._pad2  = v_const(1)
        self.mstr4  = v_defaultbits(3, 0b010)
        self._pad3  = v_const(9)
        self.mstr1  = v_defaultbits(3, 0b001)
        self._pad4  = v_const(1)
        self.mstr0  = v_defaultbits(3, 0b000)

class XBAR_SGPCRn(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.ro    = v_bits(1)
        self._pad0 = v_const(21)
        self.arb   = v_bits(2)
        self._pad1 = v_const(2)
        self.pctl  = v_bits(2)
        self._pad2 = v_const(1)
        self.park  = v_bits(3)


class XBAR_REGISTERS(PeripheralRegisterSet):
    def __init__(self, emu=None):
        super().__init__(emu)

        self.mpr0   = (XBAR_MPR0_OFFSET,   XBAR_MPRn())
        self.sgpcr0 = (XBAR_SGPCR0_OFFSET, XBAR_SGPCRn())
        self.mpr1   = (XBAR_MPR1_OFFSET,   XBAR_MPRn())
        self.sgpcr1 = (XBAR_SGPCR1_OFFSET, XBAR_SGPCRn())
        self.mpr2   = (XBAR_MPR2_OFFSET,   XBAR_MPRn())
        self.sgpcr2 = (XBAR_SGPCR2_OFFSET, XBAR_SGPCRn())
        self.mpr6   = (XBAR_MPR6_OFFSET,   XBAR_MPRn())
        self.sgpcr6 = (XBAR_SGPCR6_OFFSET, XBAR_SGPCRn())
        self.mpr7   = (XBAR_MPR7_OFFSET,   XBAR_MPRn())
        self.sgpcr7 = (XBAR_SGPCR7_OFFSET, XBAR_SGPCRn())


class XBAR(MMIOPeripheral):
    '''
    This is the AMBA Crossover Switch module
    '''
    def __init__(self, emu, mmio_addr):
        super().__init__(emu, 'XBAR', mmio_addr, 0x4000, regsetcls=XBAR_REGISTERS)
