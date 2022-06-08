from ..ppc_vstructs import *
from ..ppc_peripherals import *
from ..ppc_xbar import *

__all__  = [
    'eDMA',
]


EDMA_MCR_OFFSET     = 0x0000
EDMA_ESR_OFFSET     = 0x0004
EDMA_ERQRH_OFFSET   = 0x0008
EDMA_ERQRL_OFFSET   = 0x000C
EDMA_EEIRLH_OFFSET  = 0x0010
EDMA_EEIRL_OFFSET   = 0x0014
EDMA_SERQR_OFFSET   = 0x0018
EDMA_CERQR_OFFSET   = 0x0019
EDMA_SEEIR_OFFSET   = 0x001A
EDMA_CEEIR_OFFSET   = 0x001B
EDMA_CIRQR_OFFSET   = 0x001C
EDMA_CER_OFFSET     = 0x001D
EDMA_SSBR_OFFSET    = 0x001E
EDMA_CDSBR_OFFSET   = 0x001F
EDMA_IRQRH_OFFSET   = 0x0020
EDMA_IRQRL_OFFSET   = 0x0024
EDMA_ERH_OFFSET     = 0x0028
EDMA_ERL_OFFSET     = 0x002C
EDMA_HRSH_OFFSET    = 0x0030
EDMA_HRSL_OFFSET    = 0x0034
EDMA_GWRH_OFFSET    = 0x0038
EDMA_GWRL_OFFSET    = 0x003C
EDMA_CPRx_OFFSET    = 0x0100
EDMA_TCDx_OFFSET    = 0x1000

EDMA_A_NUM_CHAN     = 64
EDMA_B_NUM_CHAN     = 32

# The TCD structure is 256 bits (32 bytes)
EDMA_TCDx_SIZE      = 32

EDMA_TCD_STATUS_OFF = EDMA_TCDx_SIZE - 1


class EDMA_XFER_SIZE(enum.IntEnum):
    S8Bit    = 0b000,
    S16Bit   = 0b001,
    S32Bit   = 0b010,
    S64Bit   = 0b011,
    # reserved 0b100
    S256Bit  = 0b101
    # reserved 0b110
    # reserved 0b111


class EDMA_A_MCR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_bits(14)
        self.cxfr = v_bits(1)
        self.ecx = v_bits(1)
        self.grp3pri = v_bits(2, 0b11)
        self.grp2pri = v_bits(2, 0b10)
        self.grp1pri = v_bits(2, 0b01)
        self.grp0pri = v_bits(2, 0b00)
        self.emlm = v_bits(1)
        self.clm = v_bits(1)
        self.halt = v_bits(1)
        self.hoe = v_bits(1)
        self.erga = v_bits(1)
        self.erca = v_bits(1)
        self.edbg = v_bits(1)
        self._pad1 = v_bits(1)

class EDMA_B_MCR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_bits(14)
        self.cxfr = v_bits(1)
        self.ecx = v_bits(1)
        self._pad1 = v_bits(5)
        self.grp1pri = v_bits(1, 0b1)
        self._pad2 = v_bits(1)
        self.grp0pri = v_bits(1, 0b0)
        self.emlm = v_bits(1)
        self.clm = v_bits(1)
        self.halt = v_bits(1)
        self.hoe = v_bits(1)
        self.erga = v_bits(1)
        self.erca = v_bits(1)
        self.edbg = v_bits(1)
        self._pad3 = v_bits(1)

class EDMA_x_ESR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.vld = v_const(1)
        self._pad0 = v_bits(14)
        self.ecx = v_const(1)
        self.gpe = v_const(1)
        self.cpe = v_const(1)
        self.errchn = v_const(6)
        self.sae = v_const(1)
        self.soe = v_const(1)
        self.dae = v_const(1)
        self.doe = v_const(1)
        self.nce = v_const(1)
        self.sge = v_const(1)
        self.sbe = v_const(1)
        self.dbe = v_const(1)


class EDMA_8BIT_REG(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.nop = v_bits(1)
        self.value = v_bits(7)


class EDMA_32BIT_REG(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.value = v_bits(32)


class EDMA_x_CPRx(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.ecp = v_bits(1)
        self.dpa = v_bits(1)
        self.grppri = v_const(2)
        self.chpri = v_bits(4)


# The TCD structure has quite a few fields that can be interpreted in different
# ways, the structure here just defines the standard field and the extraction of
# specific bit fields is done at processing time.
class EDMA_x_TCDx(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.saddr = v_bits(32)         # Source address
        self.smod = v_bits(5)           # Source address modulo
        self.ssize = v_bits(3)          # Source data transfer size
        self.dmod = v_bits(5)           # Destination address modulo
        self.dsize = v_bits(3)          # Destination data transfer size
        self.soff = v_bits(16)          # Source address signed offset,
                                        #   Sign-extended offset applied to the
                                        #   current source address to form the
                                        #   next-state value as each source read
                                        #   is completed.
        self.nbytes = v_bits(32)        # Inner "minor" byte transfer count
        self.slast = v_bits(32)         # Last source address adjustment
        self.daddr = v_bits(32)         # Destination address
        self.citer = v_bits(16)         # Current major iteration count
        self.doff = v_bits(16)          # Destination address signed offset
        self.dlast_sga = v_bits(32)     # last destination address adjustment or
                                        #   address for next TCD
                                        #   (scatter-gather)
        self.biter = v_bits(16)         # Starting major iteration count
        self.bwc = v_bits(2)            # Bandwidth control
        self.major_linkch = v_bits(6)   # Link channel number if MAJOR.E_LINK is
                                        #   0 no linking, otherwise after
                                        #   current major loop is done, set
                                        #   TCD.START bit in the specified
                                        #   MAJOR.LINKCH
        self.done = v_bits(1)           # Channel done
        self.active = v_bits(1)         # Channel active
        self.major_e_link = v_bits(1)   # Enable channel-to-channel linking
        self.e_sg = v_bits(1)           # Enable scatter-gather processing
        self.d_req = v_bits(1)          # Disable hardware request, if set the
                                        #   corresponding ERQH or ERQL bit is
                                        #   cleared when major loop is complete
        self.int_half = v_bits(1)       # Enable interrupt when major counter is
                                        # half complete
        self.int_maj = v_bits(1)        # Enable an interrupt when major
                                        # iteration count completes
        self.start = v_bits(1)          # Channel start


class EDMA_A_REGISTERS(PeripheralRegisterSet):
    def __init__(self):
        super().__init__()

        self.mcr    = (EDMA_MCR_OFFSET,    EDMA_A_MCR())
        self.esr    = (EDMA_ESR_OFFSET,    EDMA_32BIT_REG())
        self.erqrh  = (EDMA_ERQRH_OFFSET,  EDMA_32BIT_REG())
        self.erqrl  = (EDMA_ERQRL_OFFSET,  EDMA_32BIT_REG())
        self.eeirh  = (EDMA_EEIRLH_OFFSET, EDMA_32BIT_REG())
        self.eeirl  = (EDMA_EEIRL_OFFSET,  EDMA_32BIT_REG())
        self.irqrh  = (EDMA_IRQRH_OFFSET,  EDMA_32BIT_REG())
        self.irqrl  = (EDMA_IRQRL_OFFSET,  EDMA_32BIT_REG())
        self.erh    = (EDMA_ERH_OFFSET,    EDMA_32BIT_REG())
        self.erl    = (EDMA_ERL_OFFSET,    EDMA_32BIT_REG())
        self.hrsh   = (EDMA_HRSH_OFFSET,   EDMA_32BIT_REG())
        self.hrsl   = (EDMA_HRSL_OFFSET,   EDMA_32BIT_REG())
        self.gwrh   = (EDMA_GWRH_OFFSET,   EDMA_32BIT_REG())
        self.gwrl   = (EDMA_GWRL_OFFSET,   EDMA_32BIT_REG())
        self.cpr    = (EDMA_CPRx_OFFSET,   VArray([EDMA_x_CPRx() for i in range(EDMA_A_NUM_CHAN)]))
        self.tcd    = (EDMA_TCDx_OFFSET,   VArray([EDMA_x_TCDx() for i in range(EDMA_A_NUM_CHAN)]))

    def reset(self, emu):
        """
        Reset handler for eDMA A registers.

        The CPR field needs to have the group priority values set to the default
        MCR group priority values.
        """
        super().reset(emu)

        for i in range(0, 16):
            self.cpr[i].vsOverrideValue('grppri', self.mcr.grp0pri)
        for i in range(16, 32):
            self.cpr[i].vsOverrideValue('grppri', self.mcr.grp1pri)
        for i in range(32, 48):
            self.cpr[i].vsOverrideValue('grppri', self.mcr.grp2pri)
        for i in range(48, 64):
            self.cpr[i].vsOverrideValue('grppri', self.mcr.grp3pri)


class EDMA_B_REGISTERS(PeripheralRegisterSet):
    def __init__(self):
        super().__init__()

        self.mcr    = (EDMA_MCR_OFFSET,    EDMA_B_MCR())
        self.esr    = (EDMA_ESR_OFFSET,    EDMA_32BIT_REG())
        self.erqrl  = (EDMA_ERQRL_OFFSET,  EDMA_32BIT_REG())
        self.eeirl  = (EDMA_EEIRL_OFFSET,  EDMA_32BIT_REG())
        self.irqrl  = (EDMA_IRQRL_OFFSET,  EDMA_32BIT_REG())
        self.erl    = (EDMA_ERL_OFFSET,    EDMA_32BIT_REG())
        self.hrsl   = (EDMA_HRSL_OFFSET,   EDMA_32BIT_REG())
        self.gwrl   = (EDMA_GWRL_OFFSET,   EDMA_32BIT_REG())
        self.cpr    = (EDMA_CPRx_OFFSET,   VArray([EDMA_x_CPRx() for i in range(EDMA_B_NUM_CHAN)]))
        self.tcd    = (EDMA_TCDx_OFFSET,   VArray([EDMA_x_TCDx() for i in range(EDMA_B_NUM_CHAN)]))

    def reset(self, emu):
        """
        Reset handler for eDMA B registers.

        The CPR field needs to have the group priority values set to the default
        MCR group priority values.
        """
        super().reset(emu)

        for i in range(0, 16):
            self.cpr[i].vsOverrideValue('grppri', self.mcr.grp0pri)
        for i in range(16, 32):
            self.cpr[i].vsOverrideValue('grppri', self.mcr.grp1pri)


EDMA_INT_EVENTS = {
    'eDMA_A': {
        'xfer': (
            INTC_EVENT.EDMA_A_IRQ0,     INTC_EVENT.EDMA_A_IRQ1,     INTC_EVENT.EDMA_A_IRQ2,     INTC_EVENT.EDMA_A_IRQ3,
            INTC_EVENT.EDMA_A_IRQ4,     INTC_EVENT.EDMA_A_IRQ5,     INTC_EVENT.EDMA_A_IRQ6,     INTC_EVENT.EDMA_A_IRQ7,
            INTC_EVENT.EDMA_A_IRQ8,     INTC_EVENT.EDMA_A_IRQ9,     INTC_EVENT.EDMA_A_IRQ10,    INTC_EVENT.EDMA_A_IRQ11,
            INTC_EVENT.EDMA_A_IRQ12,    INTC_EVENT.EDMA_A_IRQ13,    INTC_EVENT.EDMA_A_IRQ14,    INTC_EVENT.EDMA_A_IRQ15,
            INTC_EVENT.EDMA_A_IRQ16,    INTC_EVENT.EDMA_A_IRQ17,    INTC_EVENT.EDMA_A_IRQ18,    INTC_EVENT.EDMA_A_IRQ19,
            INTC_EVENT.EDMA_A_IRQ20,    INTC_EVENT.EDMA_A_IRQ21,    INTC_EVENT.EDMA_A_IRQ22,    INTC_EVENT.EDMA_A_IRQ23,
            INTC_EVENT.EDMA_A_IRQ24,    INTC_EVENT.EDMA_A_IRQ25,    INTC_EVENT.EDMA_A_IRQ26,    INTC_EVENT.EDMA_A_IRQ27,
            INTC_EVENT.EDMA_A_IRQ28,    INTC_EVENT.EDMA_A_IRQ29,    INTC_EVENT.EDMA_A_IRQ30,    INTC_EVENT.EDMA_A_IRQ31,
            INTC_EVENT.EDMA_A_IRQ32,    INTC_EVENT.EDMA_A_IRQ33,    INTC_EVENT.EDMA_A_IRQ34,    INTC_EVENT.EDMA_A_IRQ35,
            INTC_EVENT.EDMA_A_IRQ36,    INTC_EVENT.EDMA_A_IRQ37,    INTC_EVENT.EDMA_A_IRQ38,    INTC_EVENT.EDMA_A_IRQ39,
            INTC_EVENT.EDMA_A_IRQ40,    INTC_EVENT.EDMA_A_IRQ41,    INTC_EVENT.EDMA_A_IRQ42,    INTC_EVENT.EDMA_A_IRQ43,
            INTC_EVENT.EDMA_A_IRQ44,    INTC_EVENT.EDMA_A_IRQ45,    INTC_EVENT.EDMA_A_IRQ46,    INTC_EVENT.EDMA_A_IRQ47,
            INTC_EVENT.EDMA_A_IRQ48,    INTC_EVENT.EDMA_A_IRQ49,    INTC_EVENT.EDMA_A_IRQ50,    INTC_EVENT.EDMA_A_IRQ51,
            INTC_EVENT.EDMA_A_IRQ52,    INTC_EVENT.EDMA_A_IRQ53,    INTC_EVENT.EDMA_A_IRQ54,    INTC_EVENT.EDMA_A_IRQ55,
            INTC_EVENT.EDMA_A_IRQ56,    INTC_EVENT.EDMA_A_IRQ57,    INTC_EVENT.EDMA_A_IRQ58,    INTC_EVENT.EDMA_A_IRQ59,
            INTC_EVENT.EDMA_A_IRQ60,    INTC_EVENT.EDMA_A_IRQ61,    INTC_EVENT.EDMA_A_IRQ62,    INTC_EVENT.EDMA_A_IRQ63,
        ),
        'error': (
            INTC_EVENT.EDMA_A_ERR0,     INTC_EVENT.EDMA_A_ERR1,     INTC_EVENT.EDMA_A_ERR2,     INTC_EVENT.EDMA_A_ERR3,
            INTC_EVENT.EDMA_A_ERR4,     INTC_EVENT.EDMA_A_ERR5,     INTC_EVENT.EDMA_A_ERR6,     INTC_EVENT.EDMA_A_ERR7,
            INTC_EVENT.EDMA_A_ERR8,     INTC_EVENT.EDMA_A_ERR9,     INTC_EVENT.EDMA_A_ERR10,    INTC_EVENT.EDMA_A_ERR11,
            INTC_EVENT.EDMA_A_ERR12,    INTC_EVENT.EDMA_A_ERR13,    INTC_EVENT.EDMA_A_ERR14,    INTC_EVENT.EDMA_A_ERR15,
            INTC_EVENT.EDMA_A_ERR16,    INTC_EVENT.EDMA_A_ERR17,    INTC_EVENT.EDMA_A_ERR18,    INTC_EVENT.EDMA_A_ERR19,
            INTC_EVENT.EDMA_A_ERR20,    INTC_EVENT.EDMA_A_ERR21,    INTC_EVENT.EDMA_A_ERR22,    INTC_EVENT.EDMA_A_ERR23,
            INTC_EVENT.EDMA_A_ERR24,    INTC_EVENT.EDMA_A_ERR25,    INTC_EVENT.EDMA_A_ERR26,    INTC_EVENT.EDMA_A_ERR27,
            INTC_EVENT.EDMA_A_ERR28,    INTC_EVENT.EDMA_A_ERR29,    INTC_EVENT.EDMA_A_ERR30,    INTC_EVENT.EDMA_A_ERR31,
            INTC_EVENT.EDMA_A_ERR32,    INTC_EVENT.EDMA_A_ERR33,    INTC_EVENT.EDMA_A_ERR34,    INTC_EVENT.EDMA_A_ERR35,
            INTC_EVENT.EDMA_A_ERR36,    INTC_EVENT.EDMA_A_ERR37,    INTC_EVENT.EDMA_A_ERR38,    INTC_EVENT.EDMA_A_ERR39,
            INTC_EVENT.EDMA_A_ERR40,    INTC_EVENT.EDMA_A_ERR41,    INTC_EVENT.EDMA_A_ERR42,    INTC_EVENT.EDMA_A_ERR43,
            INTC_EVENT.EDMA_A_ERR44,    INTC_EVENT.EDMA_A_ERR45,    INTC_EVENT.EDMA_A_ERR46,    INTC_EVENT.EDMA_A_ERR47,
            INTC_EVENT.EDMA_A_ERR48,    INTC_EVENT.EDMA_A_ERR49,    INTC_EVENT.EDMA_A_ERR50,    INTC_EVENT.EDMA_A_ERR51,
            INTC_EVENT.EDMA_A_ERR52,    INTC_EVENT.EDMA_A_ERR53,    INTC_EVENT.EDMA_A_ERR54,    INTC_EVENT.EDMA_A_ERR55,
            INTC_EVENT.EDMA_A_ERR56,    INTC_EVENT.EDMA_A_ERR57,    INTC_EVENT.EDMA_A_ERR58,    INTC_EVENT.EDMA_A_ERR59,
            INTC_EVENT.EDMA_A_ERR60,    INTC_EVENT.EDMA_A_ERR61,    INTC_EVENT.EDMA_A_ERR62,    INTC_EVENT.EDMA_A_ERR63,
        ),
    },
    'eDMA_B': {
        'xfer': (
            INTC_EVENT.EDMA_B_IRQ0,     INTC_EVENT.EDMA_B_IRQ1,     INTC_EVENT.EDMA_B_IRQ2,     INTC_EVENT.EDMA_B_IRQ3,
            INTC_EVENT.EDMA_B_IRQ4,     INTC_EVENT.EDMA_B_IRQ5,     INTC_EVENT.EDMA_B_IRQ6,     INTC_EVENT.EDMA_B_IRQ7,
            INTC_EVENT.EDMA_B_IRQ8,     INTC_EVENT.EDMA_B_IRQ9,     INTC_EVENT.EDMA_B_IRQ10,    INTC_EVENT.EDMA_B_IRQ11,
            INTC_EVENT.EDMA_B_IRQ12,    INTC_EVENT.EDMA_B_IRQ13,    INTC_EVENT.EDMA_B_IRQ14,    INTC_EVENT.EDMA_B_IRQ15,
            INTC_EVENT.EDMA_B_IRQ16,    INTC_EVENT.EDMA_B_IRQ17,    INTC_EVENT.EDMA_B_IRQ18,    INTC_EVENT.EDMA_B_IRQ19,
            INTC_EVENT.EDMA_B_IRQ20,    INTC_EVENT.EDMA_B_IRQ21,    INTC_EVENT.EDMA_B_IRQ22,    INTC_EVENT.EDMA_B_IRQ23,
            INTC_EVENT.EDMA_B_IRQ24,    INTC_EVENT.EDMA_B_IRQ25,    INTC_EVENT.EDMA_B_IRQ26,    INTC_EVENT.EDMA_B_IRQ27,
            INTC_EVENT.EDMA_B_IRQ28,    INTC_EVENT.EDMA_B_IRQ29,    INTC_EVENT.EDMA_B_IRQ30,    INTC_EVENT.EDMA_B_IRQ31,
        ),
        'error': (
            INTC_EVENT.EDMA_B_ERR0,     INTC_EVENT.EDMA_B_ERR1,     INTC_EVENT.EDMA_B_ERR2,     INTC_EVENT.EDMA_B_ERR3,
            INTC_EVENT.EDMA_B_ERR4,     INTC_EVENT.EDMA_B_ERR5,     INTC_EVENT.EDMA_B_ERR6,     INTC_EVENT.EDMA_B_ERR7,
            INTC_EVENT.EDMA_B_ERR8,     INTC_EVENT.EDMA_B_ERR9,     INTC_EVENT.EDMA_B_ERR10,    INTC_EVENT.EDMA_B_ERR11,
            INTC_EVENT.EDMA_B_ERR12,    INTC_EVENT.EDMA_B_ERR13,    INTC_EVENT.EDMA_B_ERR14,    INTC_EVENT.EDMA_B_ERR15,
            INTC_EVENT.EDMA_B_ERR16,    INTC_EVENT.EDMA_B_ERR17,    INTC_EVENT.EDMA_B_ERR18,    INTC_EVENT.EDMA_B_ERR19,
            INTC_EVENT.EDMA_B_ERR20,    INTC_EVENT.EDMA_B_ERR21,    INTC_EVENT.EDMA_B_ERR22,    INTC_EVENT.EDMA_B_ERR23,
            INTC_EVENT.EDMA_B_ERR24,    INTC_EVENT.EDMA_B_ERR25,    INTC_EVENT.EDMA_B_ERR26,    INTC_EVENT.EDMA_B_ERR27,
            INTC_EVENT.EDMA_B_ERR28,    INTC_EVENT.EDMA_B_ERR29,    INTC_EVENT.EDMA_B_ERR30,    INTC_EVENT.EDMA_B_ERR31,
        ),
    },
}

EDMA_INT_STATUS_REGS = {
    'eDMA_A': {
        'xfer':  ('irqrl', 'irqrh'),
        'error': ('erl',   'erh'),
    },
    'eDMA_B': {
        'xfer':  ('irqrl',),
        'error': ('erl',),
    },
}

EDMA_INT_FLAG_REGS = {
    'eDMA_A': {
        'xfer':  ('erqrl', 'erqrh'),
        'error': ('eeirl', 'eeirh'),
    },
    'eDMA_B': {
        'xfer':  ('erqrl',),
        'error': ('eeirl',),
    },
}

# Channel event masks
EDMA_INT_MASKS = tuple(2 ** i for i in range(32)) + tuple(2 ** i for i in range(32))


class eDMA(MMIOPeripheral):
    '''
    This is the Enhanced Direct Memory Access Controller module.
    '''
    def __init__(self, devname, emu, mmio_addr):
        if devname == 'eDMA_A':
            super().__init__(emu, devname, mmio_addr, 0x4000,
                    regsetcls=EDMA_A_REGISTERS,
                    isrstatus=EDMA_INT_STATUS_REGS,
                    isrflags=EDMA_INT_FLAG_REGS,
                    isrevents=EDMA_INT_EVENTS)

            # Number of channels managed by this peripheral
            self.num_channels = EDMA_A_NUM_CHAN

            # Group to channel and MCR priority field mappings
            self.groups = (
                (range(0, 16),  'grp0pri'),
                (range(16, 32), 'grp1pri'),
                (range(32, 48), 'grp2pri'),
                (range(48, 64), 'grp3pri'),
            )

            # channel to bit position masks

        else:
            super().__init__(emu, devname, mmio_addr, 0x4000,
                    regsetcls=EDMA_B_REGISTERS,
                    isrstatus=EDMA_INT_STATUS_REGS,
                    isrflags=EDMA_INT_FLAG_REGS,
                    isrevents=EDMA_INT_EVENTS)

            # Number of channels managed by this peripheral
            self.num_channels = EDMA_B_NUM_CHAN

            # Group to channel and MCR priority field mappings
            self.groups = (
                (range(0, 16),  'grp0pri'),
                (range(16, 32), 'grp1pri'),
            )

            # channel to bit position masks
            EDMA_INT_MASKS = tuple(2 ** i for i in range(32))

        self._convenience_handlers = {
            EDMA_SERQR_OFFSET: self.setERQR,
            EDMA_CERQR_OFFSET: self.clearERQR,
            EDMA_SEEIR_OFFSET: self.setEEIR,
            EDMA_CEEIR_OFFSET: self.clearEEIR,
            EDMA_CIRQR_OFFSET: self.clearIRQR,
            EDMA_CER_OFFSET:   self.clearER,
            EDMA_SSBR_OFFSET:  self.setStart,
            EDMA_CDSBR_OFFSET: self.clearDone,
        }

        # Callbacks for registers
        self.registers.vsAddParseCallback('mcr', self.mcrUpdate)
        self.registers.vsAddParseCallback('by_idx_cpr', self.cprUpdate)
        self.registers.vsAddParseCallback('by_idx_tcd', self.tcdUpdate)

    def _getPeriphReg(self, offset, size):
        """
        Customization of the standard ExternalIOPeripheral _getPeriphReg()
        function to support custom handling for the convenience set/clear
        registers:
            - SERQR: set ERQR
            - CERQR: clear ERQR
            - SEEIR: set EEIR
            - CEEIR: clear EEIR
            - CIRQR: clear IRQR
            - CER:   clear ER
            - SSBR:  set tcd[chan].start
            - CDSBR: clear tcd[chan].done
        """
        if offset in EDMA_WRITE_ONLY_CONVENIENCE_REG_OFFSETS:
            # The convenience registers should always read 0 and are all 1 byte
            # wide.
            return b'\x00'
        else:
            return super()._getPeriphReg(offset, size)

    def _setPeriphReg(self, offset, data):
        """
        Customization of the standard ExternalIOPeripheral _setPeriphReg()
        function to support custom handling for the convenience set/clear
        registers:
            - SERQR: set ERQR
            - CERQR: clear ERQR
            - SEEIR: set EEIR
            - CEEIR: clear EEIR
            - CIRQR: clear IRQR
            - CER:   clear ER
            - SSBR:  set tcd[chan].start
            - CDSBR: clear tcd[chan].done
        """
        handler = self._convenience_handlers.get(offset)
        if handler is not None:
            chan = e_bits.parsebytes(data, 0, 1, bigend=self.emu.getEndian()))
            if chan < self.num_channels:
                handler(chan)
        else:
            super()._setPeriphReg(offset, data)

    def setERQR(self, channel):
        if channel >= EDMA_B_NUM_CHAN:
            self.registers.erqrh.value |= EDMA_INT_MASKS[channel]
        else:
            self.registers.erqrl.value |= EDMA_INT_MASKS[channel]

    def clearERQR(self, channel):
        if channel >= EDMA_B_NUM_CHAN:
            self.registers.erqrh.value &= ~EDMA_INT_MASKS[channel]
        else:
            self.registers.erqrl.value &= ~EDMA_INT_MASKS[channel]

    def setEEIR(self, channel):
        if channel >= EDMA_B_NUM_CHAN:
            self.registers.eeirh.value |= EDMA_INT_MASKS[channel]
        else:
            self.registers.eeirl.value |= EDMA_INT_MASKS[channel]

    def clearEEIR(self, channel):
        if channel >= EDMA_B_NUM_CHAN:
            self.registers.eeirh.value &= ~EDMA_INT_MASKS[channel]
        else:
            self.registers.eeirl.value &= ~EDMA_INT_MASKS[channel]

    def clearIRQR(self, channel):
        if channel >= EDMA_B_NUM_CHAN:
            self.registers.irqrh.value &= ~EDMA_INT_MASKS[channel]
        else:
            self.registers.irqrl.value &= ~EDMA_INT_MASKS[channel]

    def clearER(self, channel):
        if channel >= EDMA_B_NUM_CHAN:
            self.registers.erh.value &= ~EDMA_INT_MASKS[channel]
        else:
            self.registers.erl.value &= ~EDMA_INT_MASKS[channel]

    def setStart(self, channel):
        self.registers.tcd[channel].start = 1

    def clearDone(self, channel):
        self.registers.tcd[channel].done = 0

    def mcrUpdate(self, thing):
        """
        Check for any global configuration errors:
            - group priority configuration
        """
        group_priorities = set(self.registers.mcr.vsGetField(f) for _, f in self.groups)
        if len(set(group_priorities)) != len(self.groups):
            self.registers.esr.gpe = 1
        else:
            for channel_range, mcr_field in self.groups:
                for i in channel_range:
                    pri = self.registers.mcr.vsGetField(mcr_field)
                    self.registers.cpr[i].vsOverrideValue('grppri', pri)

    def cprUpdate(self, thing, idx, size):
        """
        Check for any global configuration errors:
            - channel priority configuration
        """
        all_chan_priorities = [cpr.chpri for cpr in self.registers.cpr]
        grouped_chan_priorities = [all_chan_priorities[i:i+16] \
                for i in range(0, len(self.registers.cpr), 16)]
        for grp, chan_priorities for enumerate(grouped_chan_priorities):
            if len(set(chan_priorities)) != len(chan_priorities):
                self.registers.esr.cpe = 1

    def tcdUpdate(self, thing, idx, size):
        """
        Processes all write updates to the TCD memory region. When the START
        field of the status is updated initiate a data transfer.
        """
        # If this is the last byte of a TCD, check the start flag.
        field_offset = idx % EDMA_TCDx_SIZE
        if EDMA_TCD_STATUS_OFF in range(field_offset, field_offset+size):
            status = self.registers.tcd[idx]

            # if START is set but not ACTIVE, we need to process this transfer
            if status & 0x01 and not status & 0x40:
                channel = idx >> EDMA_TCDx_SIZE
                self.transfer(channel)

    def dmaRequest(self, channel):
        """
        Hardware initiated DMA request for a specific channel
        """
        # Only initiate a request if hardware service requests are enabled
        if self.isChannelEnabled(channel):
            # TODO: For now we are processing the entire DMA request at once, so
            # there is no need to update transient status flags like the HRSH/L
            # reigsters.
            #self.setHRS(channel)

            self.setStart(channel)
            self.transfer(channel)

    def isChannelEnabled(self, channel):
        if channel >= EDMA_B_NUM_CHAN:
            return bool(self.registers.erqrh.value | EDMA_INT_MASKS[channel]
        else:
            return bool(self.registers.erqrl.value | EDMA_INT_MASKS[channel]

    def transfer(self, channel):
        """
        Performs the DMA transfer

        DMA Transfer Process:
            assert tcd.biter == tcd.citer
            tcd.done = 0
            tcd.start = 0
            tcd.active = 1

            while tcd.citer > 0
                if tcd.citer_e_link != 0
                    do multiple channel's minor loops in parallel (?)

                Copy tcd.nbytes from tcd.saddr to tcd.daddr, reading the data
                   with tcd.ssize and writing it with tcd.dsize (this may be
                   necessary due to alignment constraints)
                tcd.citer -= 1

                if tcd.citer != 0
                    tcd.saddr += tcd.soff
                    tcd.daddr += tcd.doff

                    if tcd.citer == tcd.biter // 2
                        event(channel, INT_HALF)

            tcd.saddr += tcd.slast
            tcd.daddr += tcd.dlast_vga
            tcd.citer = tcd.biter

            tcd.done = 1
            tcd.active = 0

            event(channel, INT_MAJ)

            if tcd.major_linkch
                dmaRequest(tcd.major_linkch)
        """
        logger.debug('[%s] starting DMA transfer for channel %d', self.devname, channel)
        tcd = self.registers.tcd[channel]

        # TODO: Scatter-Gather support not yet implemented
        if tcd.e_sg:
            raise Exception('[%s] ERROR: SG set for channel %d' % (self.devname, channel))

        # TODO: Parallel minor loop support not yet implemented
        if tcd.citer_e_link:

        # Various channel-specific configuration checks
        config_error = False

        # Source Address Error checks (esr.sae):
        #   - tcd.saddr is inconsistent with tcd.ssize
        try:
            ssize = EDMA_XFER_SIZE(tcd.ssize)
        except ValueError:
            self.registers.esr.sae = 1
            config_error = True

        # Source Offset Error checks (esr.soe):
        #   - tcd.saddr is inconsistent with tcd.soff

        # Destination Address Error checks (esr.dae):
        #   - tcd.daddr is inconsistent with tcd.dsize

        # Destination Offset Error checks (esr.doe):
        #   - tcd.daddr is inconsistent with tcd.doff

        # NBYTES/CITER Configuration Error checks (esr.nce):
        #   - tcd.nbytes is not a multiple of tcd.ssize and tcd.dsize
        #   - tcd.citer == 0 (!= tcd.biter)
        #   - tcd.citer_e_link != tcd.biter_e_link

        # TODO: Scatter-Gather Configuration Error checks (esr.sge):
        #   - ensure tcd.dlast_sga is a 0-module-32 address (?)

        if config_error:
            tcd.start = 0
            self.registers.esr.errchn = channel
            self.event('error', channel, EDMA_INT_MASKS[channel])
            return


        tcd.done = 0
        tcd.start = 0
        tcd.active = 1

        while tcd.citer > 0
            if tcd.citer_e_link != 0
                do multiple channels minor loops in parallel (?)

            Copy tcd.nbytes from tcd.saddr to tcd.daddr, reading the data
               with tcd.ssize and writing it with tcd.dsize (this may be
               necessary due to alignment constraints)
            tcd.citer -= 1

            if tcd.citer != 0
                tcd.saddr += tcd.soff
                tcd.daddr += tcd.doff

                if tcd.citer == tcd.biter // 2
                    event(channel, INT_HALF)

        tcd.saddr += tcd.slast
        tcd.daddr += tcd.dlast_vga
        tcd.citer = tcd.biter

        tcd.done = 1
        tcd.active = 0

        event(channel, INT_MAJ)

        if tcd.major_linkch
            dmaRequest(tcd.major_linkch)


