import enum

from ..ppc_vstructs import *
from ..ppc_peripherals import *

#import envi.memory as e_mem

import logging
logger = logging.getLogger(__name__)

__all__ = [
    'eTPU2',
]

"""
class ETPU2Device(enum.Enum):
    Registers       = enum.auto()
    ParamRAM        = enum.auto()
    ParamRAMMirror  = enum.auto()
    CodeRAM         = enum.auto()


ETPU2_DEVICE_MMIO_SIZE = {
    ETPU2Device.Registers:      0x00004000,
    ETPU2Device.ParamRAM:       0x00001800,
    ETPU2Device.ParamRAMMirror: 0x00001800,
    ETPU2Device.CodeRAM:        0x00006000,
}
"""


class eTPU2(MMIOPeripheral):
    def __init__(self, emu, mmio_addr):
        # TODO: implement eTPU2 registers and connections to the rest of the
        # MPC5674F.  For now the read/write functions are implemented with
        # placeholder functions that return 0's and discard writes.
        #
        # The eTPU peripheral has a few separate MMIO regions:
        #
        #           Function          |       Memory Range
        #   --------------------------+------------------------
        #   eTPU Registers            | 0xC3FC_0000—0xC3FC_3FFF
        #   (Reserved)                | 0xC3FC_4000—0xC3FC_7FFF
        #   eTPU Parameter RAM        | 0xC3FC_8000—0xC3FC_97FF
        #   eTPU Parameter RAM Mirror | 0xC3FC_C000—0xC3FC_D7FF
        #   eTPU Code RAM             | 0xC3FD_0000—0xC3FD_5FFF
        #   (Reserved)                | 0xC3FD_6000—0xC3FE_FFFF
        #
        # Instead of having seperate MMIO regions, use one giant memory region.
        super().__init__(emu, 'eTPU', mmio_addr, 0x30000)

        # TODO: figure out the param/code ram regions should work, valid access
        # range can be indicated with SCMSIZE somehow?
        #self.param_ram = bytearray(ETPU2_DEVICE_MMIO_SIZE[ETPU2Device.ParamRAM])
        #self.code_ram  = bytearray(ETPU2_DEVICE_MMIO_SIZE[ETPU2Device.CodeRAM])

    def _getPeriphReg(self, offset, size):
        # return placeholder data
        return b'\x00' * size

    def _setPeriphReg(self, offset, data):
        # Do nothing
        pass

    """
    def _param_ram_read(self, va, offset, size):
        value = self.param_ram[offset:offset+size]
        logger.debug("0x%x:  eTPU2 ParamRAM read  [%x:%r] (%r)",
                     self.emu._cur_instr[2], va, size, value)
        return value

    def _param_ram_write(self, va, offset, bytez):
        logger.debug("0x%x:  eTPU2 ParamRAM write [%x] = %r",
                     self.emu._cur_instr[2], va, bytez)
        self.param_ram[offset:offset+len(bytez)] = bytez

    def _param_ram_mirror_read(self, va, offset, size):
        value = self.param_ram[offset:offset+size]
        logger.debug("0x%x:  eTPU2 ParamRAMMirror read  [%x:%r] (%r)",
                     self.emu._cur_instr[2], va, size, value)
        return value

    def _param_ram_bytes(self, va, offset, bytez):
        return self.param_ram

    def _param_ram_mirror_write(self, va, offset, bytez):
        logger.debug("0x%x:  eTPU2 ParamRAMMirror write [%x] = %r",
                     self.emu._cur_instr[2], va, bytez)
        self.param_ram[offset:offset+len(bytez)] = bytez

    def _code_ram_read(self, va, offset, size):
        value = self.code_ram[offset:offset+size]
        logger.debug("0x%x:  eTPU2 CodeRAM read  [%x:%r] (%r)",
                    self.emu._cur_instr[2], va, size, value)
        return value

    def _code_ram_write(self, va, offset, bytez):
        logger.debug("0x%x:  eTPU2 CodeRAM write [%x] = %r",
                     self.emu._cur_instr[2], va, bytez)
        self.code_ram[offset:offset+len(bytez)] = bytez

    def _code_ram_bytes(self, va, offset, bytez):
        return self.code_ram

    def setAddr(self, emu, device, mmio_addr):
        if device == ETPU2Device.ParamRAM:
            args = {
                'va': mmio_addr,
                'msize': ETPU2_DEVICE_MMIO_SIZE[device],
                'fname': device.name,
                'mmio_read': self._param_ram_read,
                'mmio_write': self._param_ram_write,
                'mmio_bytes': self._param_ram_bytes,
                'mmio_perm': e_mem.MM_READ_WRITE,
            }
        elif device == ETPU2Device.ParamRAMMirror:
            args = {
                'va': mmio_addr,
                'msize': ETPU2_DEVICE_MMIO_SIZE[device],
                'fname': device.name,
                'mmio_read': self._param_ram_mirror_read,
                'mmio_write': self._param_ram_mirror_write,
                'mmio_bytes': self._param_ram_bytes,
                'mmio_perm': e_mem.MM_READ_WRITE,
            }
        elif device == ETPU2Device.CodeRAM:
            args = {
                'va': mmio_addr,
                'msize': ETPU2_DEVICE_MMIO_SIZE[device],
                'fname': device.name,
                'mmio_read': self._code_ram_read,
                'mmio_write': self._code_ram_write,
                'mmio_bytes': self._code_ram_bytes,
                'mmio_perm': e_mem.MM_RWX,
            }
        else:
            raise Exception('Invalid device type set MMIO address of core %s registers with setAddr()' % self.__class__.__name__)

        emu.addMMIO(**args)
    """
