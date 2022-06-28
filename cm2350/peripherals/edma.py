import enum

from ..intc_src import INTC_EVENT
from ..ppc_vstructs import *
from ..ppc_peripherals import *
from ..ppc_xbar import *

import envi.bits as e_bits

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

# Channel priority shifts
EDMA_CPR_GRPPRI_SHIFT       = 4

# The TCD structure is 256 bits (32 bytes)
EDMA_TCDx_SIZE      = 32

# TCD field masks and shifts
EDMA_TCD_STATUS_OFF     = EDMA_TCDx_SIZE - 1

EDMA_TCD_SMLOE_MASK         = 0x80000000
EDMA_TCD_SMLOE_SHIFT        = 31
EDMA_TCD_DMLOE_MASK         = 0x40000000
EDMA_TCD_DMLOE_SHIFT        = 30
EDMA_TCD_MLOFF_SIGN         = 0x20000000
EDMA_TCD_MLOFF_MASK         = 0x1FFFFC00  # signed field
EDMA_TCD_MLOFF_SHIFT        = 10
EDMA_TCD_MLOFF_NBYTES_MASK  = 0x000003FF
EDMA_TCD_NBYTES_MASK        = 0x3FFFFFFF

EDMA_TCD_E_LINK_MASK        = 0x8000
EDMA_TCD_E_LINK_SHIFT       = 15
EDMA_TCD_LINKCH_MASK        = 0x7E00
EDMA_TCD_LINKCH_SHIFT       = 9
EDMA_TCD_LINKCH_xITER_MASK  = 0x01FF
EDMA_TCD_xITER_MASK         = 0x7FFF


class EDMA_XFER_SIZE(enum.IntEnum):
    S8Bit    = 0b000,
    S16Bit   = 0b001,
    S32Bit   = 0b010,
    S64Bit   = 0b011,
    # reserved 0b100
    S256Bit  = 0b101
    # reserved 0b110
    # reserved 0b111


# Mapping of SSIZE to alignments
EDMA_XFER_SIZE_ALIGNMENT = {
    EDMA_XFER_SIZE.S8Bit:   1,
    EDMA_XFER_SIZE.S16Bit:  2,
    EDMA_XFER_SIZE.S32Bit:  4,
    EDMA_XFER_SIZE.S64Bit:  8,
    EDMA_XFER_SIZE.S256Bit: 32,
}


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
        self._pad0 = v_const(14)
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


class EDMA_x_CPRx(PeriphRegister):
    def __init__(self, chpri):
        super().__init__()
        self.ecp = v_bits(1)
        self.dpa = v_bits(1)
        self.grppri = v_const(2)
        self.chpri = v_bits(4, chpri)


# The TCD structure has quite a few fields that can be interpreted in different
# ways, the structure here just defines the standard field and the extraction of
# specific bit fields is done at processing time.
class EDMA_x_TCDx(PeriphRegSubFieldMixin, PeriphRegister):
    def __init__(self):
        super().__init__()
        self.saddr = v_bits(32)         # Source address
        self.smod = v_bits(5)           # Source address modulo
        self.ssize = v_bits(3)          # Source data transfer size
        self.dmod = v_bits(5)           # Destination address modulo
        self.dsize = v_bits(3)          # Destination data transfer size
        self.soff = v_sbits(16)         # Source address signed offset,
                                        #   Sign-extended offset applied to the
                                        #   current source address to form the
                                        #   next-state value as each source read
                                        #   is completed.
        self.nbytes = v_bits(32)        # Inner "minor" byte transfer count
        self.slast = v_sbits(32)        # Last source address adjustment
        self.daddr = v_bits(32)         # Destination address
        self.citer = v_bits(16)         # Current major iteration count
        self.doff = v_sbits(16)         # Destination address signed offset
        self.dlast_sga = v_sbits(32)    # last destination address adjustment or
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
        self.esr    = (EDMA_ESR_OFFSET,    EDMA_x_ESR())
        self.erqrh  = (EDMA_ERQRH_OFFSET,  v_bits(32))
        self.erqrl  = (EDMA_ERQRL_OFFSET,  v_bits(32))
        self.eeirh  = (EDMA_EEIRLH_OFFSET, v_bits(32))
        self.eeirl  = (EDMA_EEIRL_OFFSET,  v_bits(32))
        self.irqrh  = (EDMA_IRQRH_OFFSET,  v_bits(32))
        self.irqrl  = (EDMA_IRQRL_OFFSET,  v_bits(32))
        self.erh    = (EDMA_ERH_OFFSET,    v_bits(32))
        self.erl    = (EDMA_ERL_OFFSET,    v_bits(32))
        self.hrsh   = (EDMA_HRSH_OFFSET,   v_bits(32))
        self.hrsl   = (EDMA_HRSL_OFFSET,   v_bits(32))
        self.gwrh   = (EDMA_GWRH_OFFSET,   v_bits(32))
        self.gwrl   = (EDMA_GWRL_OFFSET,   v_bits(32))
        self.cpr    = (EDMA_CPRx_OFFSET,   VTuple([EDMA_x_CPRx(i) for i in range(EDMA_A_NUM_CHAN)]))
        self.tcd    = (EDMA_TCDx_OFFSET,   VTuple([EDMA_x_TCDx() for i in range(EDMA_A_NUM_CHAN)]))

    def reset(self, emu):
        """
        Reset handler for eDMA A registers.

        All v_bits fields need to be reset manually because they don't support
        init/reset functionality.

        The CPR field needs to have the group priority values set to the default
        MCR group priority values.
        """
        super().reset(emu)

        self.erqrh  = 0
        self.erqrl  = 0
        self.eeirh  = 0
        self.eeirl  = 0
        self.irqrh  = 0
        self.irqrl  = 0
        self.erh    = 0
        self.erl    = 0
        self.hrsh   = 0
        self.hrsl   = 0
        self.gwrh   = 0
        self.gwrl   = 0

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
        self.esr    = (EDMA_ESR_OFFSET,    EDMA_x_ESR())
        self.erqrl  = (EDMA_ERQRL_OFFSET,  v_bits(32))
        self.eeirl  = (EDMA_EEIRL_OFFSET,  v_bits(32))
        self.irqrl  = (EDMA_IRQRL_OFFSET,  v_bits(32))
        self.erl    = (EDMA_ERL_OFFSET,    v_bits(32))
        self.hrsl   = (EDMA_HRSL_OFFSET,   v_bits(32))
        self.gwrl   = (EDMA_GWRL_OFFSET,   v_bits(32))
        self.cpr    = (EDMA_CPRx_OFFSET,   VTuple([EDMA_x_CPRx(i) for i in range(EDMA_B_NUM_CHAN)]))
        self.tcd    = (EDMA_TCDx_OFFSET,   VTuple([EDMA_x_TCDx() for i in range(EDMA_B_NUM_CHAN)]))

    def reset(self, emu):
        """
        Reset handler for eDMA B registers.

        All v_bits fields need to be reset manually because they don't support
        init/reset functionality.

        The CPR field needs to have the group priority values set to the default
        MCR group priority values.
        """
        super().reset(emu)

        self.erqrl  = 0
        self.eeirl  = 0
        self.irqrl  = 0
        self.erl    = 0
        self.hrsl   = 0
        self.gwrl   = 0

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


# Object to hold the parsed TCD configuration values
class TCDConfig:
    # The attributes for this class are fixed
    __slots__ = ('channel', 'tcd', 'ssize', 'dsize', 'mloff', 'nbytes', 'linkch', '_citer')

    def __init__(self, channel, tcd, emlm):
        self.channel = channel
        self.tcd = tcd

        try:
            self.ssize = EDMA_XFER_SIZE(tcd.ssize)
        except:
            self.ssize = None

        try:
            self.dsize = EDMA_XFER_SIZE(tcd.dsize)
        except:
            self.dsize = None

        self._get_nbytes()
        self._get_citer()

    def _get_nbytes(self, emlm):
        if emlm == 1:
            if tcd.nbytes & EDMA_TCD_SMLOE_MASK or \
                    tcd.nbytes & EDMA_TCD_DMLOE_MASK:
                # MLOFF is a signed field
                if tcd.nbytes & EDMA_TCD_MLOFF_SIGN:
                    self.mloff = -((~(tcd.nbytes & EDMA_TCD_DMLOE_MASK) >> EDMA_TCD_MLOFF_SHIFT) + 1)
                else:
                    self.mloff = (tcd.nbytes & EDMA_TCD_DMLOE_MASK) >> EDMA_TCD_MLOFF_SHIFT

                self.nbytes = tcd.nbytes & EDMA_TCD_MLOFF_NBYTES_MASK
            else:
                self.mloff = None
                self.nbytes = tcd.nbytes & EDMA_TCD_NBYTES_MASK

        elif tcd.nbytes != 0:
            self.mloff = None
            self.nbytes = nbytes

        else:
            # If minor loop mapping is not enabled and nbytes has a value of 0
            # then the minor loop count is 4GB (0x1_0000_0000).  I can't imagine
            # how this would be applicable to any real usage of this peripheral,
            # but here we go
            self.mloff = None
            self.nbytes = 0x1_0000_0000

    def _get_citer(self):
        if tcd._citer & EDMA_TCD_E_LINK_MASK:
            self.linkch = (tcd.citer & EDMA_TCD_LINKCH_MASK) >> EDMA_TCD_LINKCH_SHIFT
            self._citer = tcd.citer & EDMA_TCD_LINKCH_xITER_MASK
        else:
            self.linkch = None
            self._citer = tcd.citer & EDMA_TCD_xITER_MASK

    @property
    def citer(self):
        return self._citer

    @citer.setter
    def citer(self, value):
        self._citer = value
        if self.tcd.citer & EDMA_TCD_E_LINK_MASK:
            self.tcd.citer = (self.tcd.citer & ~EDMA_TCD_LINKCH_xITER_MASK) | value
        else:
            tcd.citer = value


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

        # For fixed-priority scheduling keep track of the group priorities
        self._fixed_group_pri = None
        self._fixed_channel_pri = None

        # For round-robin scheduling keep track of the next group and channel
        self._rr_group_pri = None
        self._rr_channel_pri = None

        # Holds any current ongoing DMA transfer configurations
        self._pending = {}
        self._active = None

        # Callbacks for registers
        self.registers.vsAddParseCallback('mcr', self.mcrUpdate)
        self.registers.vsAddParseCallback('esr', self.esrUpdate)
        self.registers.cpr.vsAddParseCallback('by_idx', self.cprUpdate)
        self.registers.tcd.vsAddParseCallback('by_idx', self.tcdUpdate)

    def reset(self, emu):
        super().reset(emu)

        # Clear any ongoing DMA transfers
        self._pending = {}
        self._active = None

        # Reset the fixed and round robin priority lists to their defaults
        self._fixed_group_pri = self._get_group_fixed_priorities()
        self._fixed_channel_pri = [self._get_channel_fixed_priorities(r) for r, _ in self.groups]
        self._rr_group_pri = list(range(len(self.groups)))
        self._rr_channel_pri = [list(r) for r, _ in self.groups]

    def _get_group_fixed_priorities(self):
        # Return the group numbers (indexes) for this peripheral ordered by
        # which priority values are highest
        return [i for _, i in \
                sorted(((self.registers.mcr.vsGetField(f).vsGetValue(), i) \
                       for i, (_, f) in enumerate(self.groups)), reverse=True)]

    def _get_channel_fixed_priorities(self, channels):
        # Return the channel numbers (indexes) for this peripheral ordered by
        # which priority values are highest
        return [c for _, c in \
                sorted(((cpr.chpri, c) for c, cpr in self.registers.cpr), reverse=True)]

    def _get_next_channel(self):
        """
        Return the next channel that has a pending transfer (if any)
        """

        if self.registers.mcr.egra == 0:
            # fixed group priority
            for group in self._fixed_group_pri:
                try:
                    if self.registers.mcr.egca == 0:
                        # fixed channel priority
                        return next(c for c in self._fixed_channel_pri[group] if c in self._pending)
                    else:
                        # round-robin channel priority
                        return next(c for c in self._rr_channel_pri[group] if c in self._pending)
                except StopIteration:
                    # Try the next group
                    pass

            # If we've reached this point, no pending transfers were found
            return None

        else:
            # round-robin group priority
            processed = []
            channel = None
            while self._rr_group_pri and channel is None:
                group = self._rr_group_pri.pop(0)
                try:
                    if self.registers.mcr.egca == 0:
                        # fixed channel priority
                        channel = next(c for c in self._fixed_channel_pri[group] if c in self._pending)
                    else:
                        # round-robin channel priority
                        channel = next(c for c in self._rr_channel_pri[group] if c in self._pending)
                except StopIteration:
                    # Try the next group
                    pass
                finally:
                    processed.append(group)

            # Add the processed groups to the end of the round-robin priority
            # list
            self._rr_group_pri.extend(processed)

            # return what we found
            return channel

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
        if offset in self._convenience_handlers:
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
            chan = e_bits.parsebytes(data, 0, 1, bigend=self.emu.getEndian())
            if chan < self.num_channels:
                handler(chan)
        else:
            super()._setPeriphReg(offset, data)

    def setERQR(self, channel):
        if channel >= EDMA_B_NUM_CHAN:
            self.registers.erqrh |= EDMA_INT_MASKS[channel]
        else:
            self.registers.erqrl |= EDMA_INT_MASKS[channel]

    def clearERQR(self, channel):
        if channel >= EDMA_B_NUM_CHAN:
            self.registers.erqrh &= ~EDMA_INT_MASKS[channel]
        else:
            self.registers.erqrl &= ~EDMA_INT_MASKS[channel]

    def setEEIR(self, channel):
        if channel >= EDMA_B_NUM_CHAN:
            self.registers.eeirh |= EDMA_INT_MASKS[channel]
        else:
            self.registers.eeirl |= EDMA_INT_MASKS[channel]

    def clearEEIR(self, channel):
        if channel >= EDMA_B_NUM_CHAN:
            self.registers.eeirh &= ~EDMA_INT_MASKS[channel]
        else:
            self.registers.eeirl &= ~EDMA_INT_MASKS[channel]

    def clearIRQR(self, channel):
        if channel >= EDMA_B_NUM_CHAN:
            self.registers.irqrh &= ~EDMA_INT_MASKS[channel]
        else:
            self.registers.irqrl &= ~EDMA_INT_MASKS[channel]

    def clearER(self, channel):
        if channel >= EDMA_B_NUM_CHAN:
            self.registers.erh &= ~EDMA_INT_MASKS[channel]
        else:
            self.registers.erl &= ~EDMA_INT_MASKS[channel]

    def setStart(self, channel):
        self.registers.tcd[channel].start = 1

    def clearDone(self, channel):
        self.registers.tcd[channel].done = 0

    def setHRS(self, channel):
        if channel >= EDMA_B_NUM_CHAN:
            self.registers.hrsh |= EDMA_INT_MASKS[channel]
        else:
            self.registers.hrsl |= EDMA_INT_MASKS[channel]

    def clearHRS(self, channel):
        if channel >= EDMA_B_NUM_CHAN:
            self.registers.hrsh &= ~EDMA_INT_MASKS[channel]
        else:
            self.registers.hrsl &= ~EDMA_INT_MASKS[channel]

    def mcrUpdate(self, thing):
        """
        Check for any global configuration errors:
            - group priority configuration
        """
        group_priorities = set(self.registers.mcr.vsGetField(f).vsGetValue() for _, f in self.groups)
        if len(set(group_priorities)) != len(self.groups):
            self.registers.esr.gpe = 1
        else:
            # Update the grppri fields in each CPR register to reflect the group
            # priority for that particular channel
            for channel_range, mcr_field in self.groups:
                for i in channel_range:
                    pri = self.registers.mcr.vsGetField(mcr_field)
                    self.registers.cpr[i].vsOverrideValue('grppri', pri)

            # Sort the group indexes based on their priorities.
            self._fixed_group_pri = self._get_group_fixed_priorities()

        if self.registers.mcr.cxfr == 1:
            self._active = None
            for channel in self._pending:
                del self._pending[channel]

                # Make the channel look as if the minor loop had completed
                self.registers.tcd[channel].start = 0
                self.registers.tcd[channel].active = 0
                self.registers.tcd[channel].done = 0

            # Clear the CXFR bit
            self.registers.mcr.cxfr = 0

        if self.registers.mcr.ecx == 1:
            self._active = None
            for channel in self._pending:
                del self._pending[channel]

                # cancel the transfer and set the error status
                self.registers.tcd[channel].start = 0
                self.setError(channel, 'ecx')

            # Clear the CXFR bit
            self.registers.mcr.ecx = 0

        if self.registers.mcr.halt == 0:
            for channel in range(self.num_channels):
                if channel not in self._pending and self.registers.tcd[channel].start == 1:
                    self.startTransfer(channel)

    def esrUpdate(self, thing):
        # If no error bits are set ensure the VLD bit is clear
        self.registers.esr.vld = self.ecx == 1 or self.gpe == 1 or \
                self.cpe == 1 or self.sae == 1 or self.soe == 1 or \
                self.dae == 1 or self.doe == 1 or self.nce == 1 or \
                self.sge == 1 or self.sbe == 1 or self.dbe == 1

    def cprUpdate(self, thing, idx, size, **kwargs):
        """
        Check for any global configuration errors:
            - channel priority configuration
        """
        all_chan_priorities = [cpr.chpri for _, cpr in self.registers.cpr]
        grouped_chan_priorities = [all_chan_priorities[i:i+16] \
                for i in range(0, len(self.registers.cpr), 16)]
        for grp, chan_priorities in enumerate(grouped_chan_priorities):
            if len(set(chan_priorities)) != len(chan_priorities):
                self.registers.esr.cpe = 1

        # TODO: not sure how to handle ECP or DPA bits yet
        if self.registers.cpr[idx].ecp:
            raise NotImplementedError('setting CPR[%d].ECP not yet supported'  % idx)
        if self.registers.cpr[idx].dpa:
            raise NotImplementedError('setting CPR[%d].DPA not yet supported'  % idx)

    def tcdUpdate(self, thing, idx, foffset, size):
        """
        Processes all write updates to the TCD memory region. When the START
        field of the status is updated initiate a data transfer.
        """
        # Figure out which part of the TCD was just modified
        channel = idx

        if EDMA_TCD_STATUS_OFF in range(foffset, foffset+size):
            channel = idx >> EDMA_TCDx_SIZE

            # If the DONE bit is set the E_SG and MAJOR.E_LINK bits must be 0
            if self.registers.tcd[channel].done == 1:
                self.registers.tcd[channel].major_e_link = 0
                self.registers.tcd[channel].e_sg = 0

            # if START is set but not ACTIVE, we need to process this transfer
            if self.registers.tcd[channel].start == 1 and \
                    self.registers.tcd[channel].active == 0:
                self.startTransfer(channel)

    def isChannelEnabled(self, channel):
        if channel >= EDMA_B_NUM_CHAN:
            return bool(self.registers.erqrh | EDMA_INT_MASKS[channel])
        else:
            return bool(self.registers.erqrl | EDMA_INT_MASKS[channel])

    def dmaRequest(self, channel):
        """
        Hardware initiated DMA request for a specific channel
        """
        # Only initiate a request if hardware service requests are enabled
        if self.isChannelEnabled(channel):
            self.setHRS(channel)
            self.startTransfer(channel)

    def verifyChannelConfig(self, channel):
        """
        Validate the TCD configuration and return the masked/shifted values that
        are necessary for processing the transfer:
            - tcd reference (for convenience)
            - ssize enum
            - dsize enum
            - mloff
            - nbytes
            - linkch
            - citer
        """
        logger.debug('[%s] Validating DMA channel %d configuration', self.devname, channel)

        config = TCDConfig(channel, self.registers.tcd[channel], self.registers.mcr.emlm)

        if config.ssize is None:
            # config.ssize will be set to None if the TCD has an invalid value
            # in SSIZE field
            self.setError(channel, 'sae')
            return None

        # If the ssize was valid, do the remaining ssize related checks

        # Source Address Error checks (esr.sae):
        #   - tcd.saddr is inconsistent with tcd.ssize
        #   - tcd.saddr is inconsistent with tcd.soff (not sure how to check
        #   this?)
        if config.tcd.saddr % config.ssize != 0:
            self.setError(channel, 'sae')
            return None

        # Source Offset Error checks (esr.soe):
        #   - tcd.soff is inconsistent with tcd.ssize
        if config.tcd.soff % config.ssize != 0:
            self.setError(channel, 'soe')
            return None

        if config.dsize is None:
            # config.dsize will be set to None if the TCD has an invalid value
            # in DSIZE field
            self.setError(channel, 'dae')
            return None

        # If the dsize was valid, do the remaining ssize related checks

        # Destination Address Error checks (esr.dae):
        #   - tcd.daddr is inconsistent with tcd.dsize
        #   - tcd.daddr is inconsistent with tcd.doff (not surehow to check
        #   this?)
        if config.tcd.daddr % config.dsize != 0:
            self.setError(channel, 'dae')
            return None

        # Destination Offset Error checks (esr.doe):
        #   - tcd.doff is inconsistent with tcd.dsize
        if config.tcd.doff % config.dsize != 0:
            self.setError(channel, 'doe')
            return None

        # NBYTES/CITER Configuration Error checks (esr.nce):
        #   - tcd.nbytes is not a multiple of tcd.ssize and tcd.dsize
        if config.nbytes % config.ssize or config.nbytes % config.dsize:
            self.setError(channel, 'nce')
            return None

        #   - tcd.citer == 0 (!= tcd.biter)
        #   - tcd.citer_e_link != tcd.biter_e_link
        if config.citer == 0 or config.tcd.citer != config.tcd.biter:
            self.setError(channel, 'nce')
            return None

        # Scatter-Gather Configuration Error checks (esr.sge):
        #   - ensure tcd.dlast_sga is on a 32 byte boundary
        if config.tcd.e_sg:
            if config.tcd.dlast_sga % EDMA_XFER_SIZE_ALIGNMENT[EDMA_XFER_SIZE.S32Bit] != 0:
                self.setError(channel, 'sge')
                return None

        num_minor_loops = config.nbytes // max(config.ssize, config.dsize)
        logger.debug('[%s] validated channel %d config (%d x %d loops)',
                     self.devname, channel, config.citer, num_minor_loops)

        return config

    def setError(self, channel, flag):
        self.registers.esr.vsSetField(flag, 1)
        self.registers.esr.errchn = channel

        # Set the VLD bit
        self.registers.esr.vld = 1

        if self.registers.mcr.hoe == 1:
            self.registers.mcr.halt = 1

        self.event('error', channel, EDMA_INT_MASKS[channel])

    def startTransfer(self, channel):
        # If DMA is halted, do nothing
        if self.registers.mcr.halt:
            logger.debug('[%s] ignoring transfer for channel %d: DMA halted',
                    self.devname, channel)
        else:
            config = verifyChannelConfig(self, channel)
            if config is None:
                logger.debug('[%s] aborting transfer for channel %d: config error',
                        self.devname, channel)
            else:
                logger.debug('[%s] queuing transfer for channel %d',
                        self.devname, channel)

                # Save the current active configuration
                self._pending[channel] = config

    def processActiveTransfers(self):
        # Get the next transfer to process
        config = self._active
        if config is None:
            # Search for the next highest priority pending channel
            channel = self._get_next_channel()
            config = self._pending.get(channel)

        # If no pending transfer was found, there is nothing to do
        if config is None:
            return

        linkch = self._process_major_loop(config)
        if linkch is not None:
            # if CLM is set then a minor link loop to the same channel does not
            # have to go through priority arbitration again
            if linkch == config.channel and linkch == config.linkch and \
                    config.citer != 0 and self.registers.mcr.clm == 1:
                logger.debug('[%s] re-activating current transfer for current channel %d',
                             self.devname, channel)
                self._active = config
            else:
                logger.debug('[%s] starting linked transfer %d for current channel %d',
                             self.devname, linkch, channel)
                self.startTransfer(linkch)

        if config.citer == 0:
            # This channel is no longer active
            del self._pending[config.channel]

            # Check if scatter-gather is configured for this channel, if so
            # overwrite the current channel and re-start it
            tcd = self.emu.readMemory(config.tcd.dlast_sga, EDMA_TCDx_SIZE)
            addr = self.baseaddr + EDMA_TCDx_OFFSET + channel * EDMA_TCDx_SIZE
            self.emu.writeMemory(addr, tcd)

            self.startTransfer(config.channel)

    def _process_major_loop(self, config):
        # Indicate that this channel is active
        config.tcd.start = 0
        config.tcd.done = 0
        config.tcd.active = 1

        logger.debug('[%s] 0x%08x[%d] -> 0x%08x[%d]', self.devname,
                config.tcd.saddr, config.ssize,
                config.tcd.daddr, config.dsize)

        data = bytearray()
        try:
            while len(data) < config.nbytes:
                data += self.emu.readMemory(config.tcd.saddr, config.ssize)
        except MceDataReadBusError:
            self.setError(config.channel, 'sbe')

            # Remove this channel from the pending channels before halting
            # TODO: not 100% sure this is the way read errors should be handled?
            config.tcd.active = 0
            del self._pending[config.channel]

            return None

        try:
            for i in range(0, len(data), config.dsize):
                self.emu.writeMemory(config.tcd.daddr, data[i:i+config.dsize])
        except MceWriteBusError:
            self.setError(config.channel, 'dbe')

            # Remove this channel from the pending channels before halting
            # TODO: not 100% sure this is the way write errors should be
            # handled?
            config.tcd.active = 0
            del self._pending[config.channel]

            return None

        # Now that one major loop is complete, decrement citer, and process any
        # linked channels
        config.citer -= 1

        # Deactivate this channel
        config.tcd.active = 0

        if config.citer != 0:
            # Adjust the source and destination addresses
            #TODO mloff
            config.tcd.saddr += config.tcd.soff
            config.tcd.daddr += config.tcd.doff

            # Check if an interrupt needs to be signaled for half-way
            # completing the transfer
            if config.tcd.int_half and \
                    config.tcd.citer == config.tcd.biter // 2:
                self.event('xfer', config.channel, EDMA_INT_MASKS[config.channel])

            if config.linkch != 0:
                # Mark the linked channel as started so that it is processed
                # next time.
                self.setStart(config.linkch)
                return config.linkch

        else:
            # Adjust the source and destination addresses
            config.tcd.saddr += tcd.slast
            config.tcd.daddr += tcd.dlast_vga
            config.tcd.citer = tcd.biter

            # Set the done flag
            config.tcd.done = 1

            # If the HRS flag is set for this channel, clear it
            self.clearHRS(config.channel)

            # Check if an interrupt should be signaled when the transfer is
            # complete
            if config.tcd.int_maj == 1:
                self.event('xfer', config.channel, EDMA_INT_MASKS[config.channel])

            # If the d_req flag is set, clear the ERQx flag for this channel
            # TODO: it is unclear if this should be checked before or after a
            # potential INT_MAJ interrupt is signaled.
            if config.tcd.d_req == 1:
                self.clearERQR(config.channel)

            if config.tcd.major_e_link == 1:
                # Mark the linked channel as started so that it is processed
                # next time.
                self.setStart(config.tcd.major_linkch)
                return config.tcd.major_linkch

        # No channel linking to be done
        return None
