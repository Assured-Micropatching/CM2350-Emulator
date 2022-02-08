import envi.memory as e_mem

from ..ppc_vstructs import *
from ..ppc_peripherals import *

import logging
logger = logging.getLogger(__name__)


__all__  = [
    'EBI',
]


EBI_MCR_OFFSET     = 0x0000
EBI_TESR_OFFSET    = 0x0008
EBI_BMCR_OFFSET    = 0x000C
EBI_CAL_BR0_OFFSET = 0x0040
EBI_CAL_OR0_OFFSET = 0x0044
EBI_CAL_BR1_OFFSET = 0x0048
EBI_CAL_OR1_OFFSET = 0x004C
EBI_CAL_BR2_OFFSET = 0x0050
EBI_CAL_OR2_OFFSET = 0x0054
EBI_CAL_BR3_OFFSET = 0x0058
EBI_CAL_OR3_OFFSET = 0x005C

NUM_EXTERNAL_BANKS = 4

EBI_BR_FIXED_SHIFT = 29
EBI_BR_BA_SHIFT    = 15
EBI_OR_FIXED_SHIFT = 29
EBI_OR_AM_SHIFT    = 15

EBI_VALID_ADDR_MASK = 0x3FFFFFFF

class EBI_MCR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(16)
        self.acge = v_bits(1)
        self._pad1 = v_const(8, 0x10)
        self.mdis = v_bits(1)
        self._pad2 = v_const(3)
        self.d16_31 = v_bits(1)
        self.ad_mux = v_bits(1)
        self.dbm = v_bits(1)


class EBI_TESR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(30)
        self.teaf = v_const(1)
        self.bmtf = v_const(1)


class EBI_BMCR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(16)
        self.bmt = v_defaultbits(8, 0xFF)
        self.bme = v_defaultbits(1, 1)
        self._pad1 = v_const(7)


class EBI_CAL_BRx(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.fixed = v_const(3, 0b001)
        self.ba = v_bits(14)
        self._pad0 = v_const(3)
        self.ps = v_bits(1)
        self._pad1 = v_const(3)
        self.ad_mux = v_bits(1)
        self.bl = v_bits(1)
        self.webs = v_bits(1)
        self.tbdip = v_bits(1)
        self._pad2 = v_const(1)
        self.seta = v_bits(1)
        self.bi = v_defaultbits(1, 1)
        self.vi = v_bits(1)


class EBI_CAL_ORx(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.fixed = v_const(3, 0b111)
        self.am = v_bits(14)
        self._pad0 = v_const(7)
        self.scy = v_bits(4)
        self._pad1 = v_const(1)
        self.bscy = v_bits(2)
        self._pad2 = v_const(1)


class EBI_REGISTERS(PeripheralRegisterSet):
    def __init__(self, emu=None):
        super().__init__(emu)

        self.mcr  = (EBI_MCR_OFFSET,     EBI_MCR())
        self.tesr = (EBI_TESR_OFFSET,    EBI_TESR())
        self.bmcr = (EBI_BMCR_OFFSET,    EBI_BMCR())
        self.br0  = (EBI_CAL_BR0_OFFSET, EBI_CAL_BRx())
        self.or0  = (EBI_CAL_OR0_OFFSET, EBI_CAL_ORx())
        self.br1  = (EBI_CAL_BR1_OFFSET, EBI_CAL_BRx())
        self.or1  = (EBI_CAL_OR1_OFFSET, EBI_CAL_ORx())
        self.br2  = (EBI_CAL_BR2_OFFSET, EBI_CAL_BRx())
        self.or2  = (EBI_CAL_OR2_OFFSET, EBI_CAL_ORx())
        self.br3  = (EBI_CAL_BR3_OFFSET, EBI_CAL_BRx())
        self.or3  = (EBI_CAL_OR3_OFFSET, EBI_CAL_ORx())


class ExternalRAMBank:
    def __init__(self, addr=0, size=0, valid=False):
        self.addr = addr
        self.size = size
        self.valid = valid

    def changed(self, addr, size, valid):
        return self.addr != addr or self.size != size or self.valid != valid

    def update(self, addr, size, valid):
        self.addr = addr
        self.size = size
        self.valid = valid


class EBI(MMIOPeripheral):
    '''
    This is the External Bus Interface module.  This just provides a access to
    a valid set of registers.  The configuration of the registers in this
    peripheral don't impact the available external memory.  That requires the addi
    '''
    def __init__(self, emu, mmio_addr):
        # need to hook a MMIO mmiodev at 0xFFFEC000 of size 0x4000
        super().__init__(emu, 'EBI', mmio_addr, 0x4000, regsetcls=EBI_REGISTERS)

        self.bank_registers = (
            (self.registers.br0, self.registers.or0),
            (self.registers.br1, self.registers.or1),
            (self.registers.br2, self.registers.or2),
            (self.registers.br3, self.registers.or3),
        )

        self.bank_config = tuple(ExternalRAMBank() for i in range(NUM_EXTERNAL_BANKS))

        # A valid external memory region is created when the BRx[VI] flag is set
        # and the corresponding ORx[AM] field is defined.  It appears that these
        # registers can be set in either order which is a little annoying
        # because the ORx[AM] field has a default value of 0xE000.  This means
        # that we need to
        self.registers.vsAddParseCallback('br0', self.br0Update)
        self.registers.vsAddParseCallback('or0', self.or0Update)
        self.registers.vsAddParseCallback('br1', self.br1Update)
        self.registers.vsAddParseCallback('or1', self.or1Update)
        self.registers.vsAddParseCallback('br2', self.br2Update)
        self.registers.vsAddParseCallback('or2', self.or2Update)
        self.registers.vsAddParseCallback('br3', self.br3Update)
        self.registers.vsAddParseCallback('or3', self.or3Update)

    def reset(self, emu):
        super().reset(emu)

        # Update the bank configurations
        for bank in range(NUM_EXTERNAL_BANKS):
            self.updateBank(bank)

    def br0Update(self, thing):
        self.updateBank(0)

    def or0Update(self, thing):
        self.updateBank(0)

    def br1Update(self, thing):
        self.updateBank(1)

    def or1Update(self, thing):
        self.updateBank(1)

    def br2Update(self, thing):
        self.updateBank(2)

    def or2Update(self, thing):
        self.updateBank(2)

    def br3Update(self, thing):
        self.updateBank(3)

    def or3Update(self, thing):
        self.updateBank(3)

    def updateBank(self, bank):
        addr = (self.bank_registers[bank][0].fixed << EBI_BR_FIXED_SHIFT) | \
                (self.bank_registers[bank][0].ba << EBI_BR_BA_SHIFT)
        valid = bool(self.bank_registers[bank][0].vi)

        # Also OR in the address itself
        mask = (self.bank_registers[bank][1].fixed << EBI_OR_FIXED_SHIFT) | \
                (self.bank_registers[bank][1].am << EBI_OR_AM_SHIFT) | addr

        # Convert the mask to a size
        size = (~mask & EBI_VALID_ADDR_MASK) + 1

        logger.debug('%s[%d] addr=0x%x, mask=0x%x, size=0x%x valid=%s',
                self.devname, bank, addr, mask, size, valid)

        changed = self.bank_config[bank].changed(addr, size, valid)
        if changed:
            logger.debug('%s[%d] changed (old: addr=0x%x, size=0x%x valid=%s)',
                    self.devname, bank,
                    self.bank_config[bank].addr, self.bank_config[bank].size,
                    self.bank_config[bank].valid)
            # If the old config was valid, delete the map
            if self.bank_config[bank].valid:
                old_start = self.bank_config[bank].addr
                old_end = old_start + self.bank_config[bank].size
                logger.debug('%s[%d] removing old memory map 0x%x - 0x%x', self.devname, bank, old_start, old_end)
                self.emu.delMemoryMap(addr)

        self.bank_config[bank].update(addr, size, valid)

        # If the new config is valid (and it was changed), and the size is > 0
        # add a new entry
        if valid and changed and size > 0:
            # The initial external RAM memory block must be created
            logger.debug('%s[%d] adding external RAM 0x%x - 0x%x', self.devname, bank, addr, addr+size)
            self.emu.addMemoryMap(addr, e_mem.MM_RWX, '%s[%d]' % (self.devname, bank), b'\x00' * size)
