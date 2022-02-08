from ..ppc_vstructs import *
from ..ppc_peripherals import *

__all__  = [
    'SIM',
]

class SIM_CONST(PeriphRegister):
	def __init__(self, value):
		super().__init__()
		self.simConst = v_const(32, value)

class SIM_REGISTERS(PeripheralRegisterSet):
    def __init__(self, emu=None):
        super().__init__(emu)

        self.tempCalConst1 = (0x00, SIM_CONST(0x9F03171C))
        self.tempCalConst2 = (0x04, SIM_CONST(0xCFBCFFFF))
        self.uniqueDevID1  = (0x10, SIM_CONST(0x01FFFFFF))
        self.uniqueDevID2  = (0x14, SIM_CONST(0xFF444534))
        self.uniqueDevID3  = (0x18, SIM_CONST(0x33383837))
        self.uniqueDevID4  = (0x1C, SIM_CONST(0x11011014))

class SIM(MMIOPeripheral):
    '''
    This is the System Information Module.
    '''
    def __init__(self, emu, mmio_addr):
        # need to hook a MMIO mmiodev at 0xFFFEC000 of size 0x4000
        super().__init__(emu, 'SIM', mmio_addr, 0x4000, regsetcls=SIM_REGISTERS)
