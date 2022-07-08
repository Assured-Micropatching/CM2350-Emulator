from ..ppc_vstructs import *
from ..ppc_peripherals import *

import logging
logger = logging.getLogger(__name__)

__all__ = [
    'eMIOS200',
]


class eMIOS200(MMIOPeripheral):
    def __init__(self, emu, mmio_addr):
        super().__init__(emu, 'eMIOS', mmio_addr, 0x4000)

    def _getPeriphReg(self, offset, size):
        # return placeholder data
        return b'\x00' * size

    def _setPeriphReg(self, offset, data):
        # Do nothing
        pass
