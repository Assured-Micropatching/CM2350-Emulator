import enum

from ..intc_exc import AlignmentException, MceWriteBusError, MceDataReadBusError
from ..intc_src import INTC_EVENT
from ..ppc_vstructs import *
from ..ppc_peripherals import PPC_MAX_READ_SIZE, MMIOPeripheral
from ..ppc_xbar import *


import envi.bits as e_bits

import logging
logger = logging.getLogger(__name__)

__all__  = [
    'eDMA',
]


EDMA_MCR_OFFSET     = 0x0000
EDMA_ESR_OFFSET     = 0x0004
EDMA_ERQRH_OFFSET   = 0x0008
EDMA_ERQRL_OFFSET   = 0x000C
EDMA_EEIRH_OFFSET   = 0x0010
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
        self.eeirh  = (EDMA_EEIRH_OFFSET,  v_bits(32))
        self.eeirl  = (EDMA_EEIRL_OFFSET,  v_bits(32))
        self.irqrh  = (EDMA_IRQRH_OFFSET,  v_bits(32))
        self.irqrl  = (EDMA_IRQRL_OFFSET,  v_bits(32))
        self.erh    = (EDMA_ERH_OFFSET,    v_w1c(32))
        self.erl    = (EDMA_ERL_OFFSET,    v_w1c(32))
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
        self.erl    = (EDMA_ERL_OFFSET,    v_w1c(32))
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

# masks combined with PPC bit positions
BIT_POSITIONS_AND_MASKS = tuple((i, 2 ** i) for i in range(32))


def gen_set_bits(value):
    '''
    Returns channel/bit numbers that are set assuming 32-bit wide registers and
    PPC bit numbering.
    '''
    for bit, mask in BIT_POSITIONS_AND_MASKS:
        if value & mask:
            yield bit


# Object to hold the parsed TCD configuration values
class TCDConfig:
    def __init__(self, channel, tcd, emlm):
        self.channel = channel
        self.tcd = tcd

        try:
            self.ssize = EDMA_XFER_SIZE_ALIGNMENT[EDMA_XFER_SIZE(tcd.ssize)]
        except:
            self.ssize = None

        try:
            self.dsize = EDMA_XFER_SIZE_ALIGNMENT[EDMA_XFER_SIZE(tcd.dsize)]
        except:
            self.dsize = None

        # If smod or dmod are set get the masks now.  These masks are the masks
        # of the address value that should be unmodified by the s/dmod
        # calculations
        if tcd.smod:
            self.smod_mask = e_bits.b_masks[tcd.smod]
        else:
            self.smod_mask = 0

        if tcd.dmod:
            self.dmod_mask = e_bits.b_masks[tcd.dmod]
        else:
            self.dmod_mask = 0

        self._get_nbytes(emlm)
        self._get_citer()

    def __str__(self):
        return 'TCD%s' % self.channel

    def _get_nbytes(self, emlm):
        if emlm == 1:
            if self.tcd.nbytes & EDMA_TCD_SMLOE_MASK or \
                    self.tcd.nbytes & EDMA_TCD_DMLOE_MASK:
                # MLOFF is a signed field
                if self.tcd.nbytes & EDMA_TCD_MLOFF_SIGN:
                    self.mloff = -((~(self.tcd.nbytes & EDMA_TCD_DMLOE_MASK) >> EDMA_TCD_MLOFF_SHIFT) + 1)
                else:
                    self.mloff = (self.tcd.nbytes & EDMA_TCD_DMLOE_MASK) >> EDMA_TCD_MLOFF_SHIFT

                self.nbytes = self.tcd.nbytes & EDMA_TCD_MLOFF_NBYTES_MASK
            else:
                self.mloff = None
                self.nbytes = self.tcd.nbytes & EDMA_TCD_NBYTES_MASK

        elif self.tcd.nbytes != 0:
            self.mloff = None
            self.nbytes = self.tcd.nbytes

        else:
            # If minor loop mapping is not enabled and nbytes has a value of 0
            # then the minor loop count is 4GB (0x1_0000_0000).  I can't imagine
            # how this would be applicable to any real usage of this peripheral,
            # but here we go
            self.mloff = None
            self.nbytes = 0x1_0000_0000

    def _get_citer(self):
        if self.tcd.citer & EDMA_TCD_E_LINK_MASK:
            self.linkch = (self.tcd.citer & EDMA_TCD_LINKCH_MASK) >> EDMA_TCD_LINKCH_SHIFT
            self._citer = self.tcd.citer & EDMA_TCD_LINKCH_xITER_MASK
        else:
            self.linkch = None
            self._citer = self.tcd.citer & EDMA_TCD_xITER_MASK

    @property
    def citer(self):
        return self._citer

    @citer.setter
    def citer(self, value):
        self._citer = value
        if self.tcd.citer & EDMA_TCD_E_LINK_MASK:
            self.tcd.citer = (self.tcd.citer & ~EDMA_TCD_LINKCH_xITER_MASK) | value
        else:
            self.tcd.citer = value


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
                (list(range(0, 16)),  'grp0pri'),
                (list(range(16, 32)), 'grp1pri'),
                (list(range(32, 48)), 'grp2pri'),
                (list(range(48, 64)), 'grp3pri'),
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
                (list(range(0, 16)),  'grp0pri'),
                (list(range(16, 32)), 'grp1pri'),
            )

        self._convenience_handlers = {
            EDMA_ERQRH_OFFSET: self.handleWriteERQRH,
            EDMA_ERQRL_OFFSET: self.handleWriteERQRL,
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
        self._active = None
        self._pending = None

        # Callbacks for registers
        self.registers.vsAddParseCallback('mcr', self.mcrUpdate)
        self.registers.cpr.vsAddParseCallback('by_idx', self.cprUpdate)
        self.registers.tcd.vsAddParseCallback('by_idx', self.tcdUpdate)

    def reset(self, emu):
        super().reset(emu)

        # Clear any ongoing DMA transfers
        self._active = None
        self._pending = {}

        # Reset the fixed and round robin priority lists to their defaults
        self._update_chan_priorities()

    def _update_chan_priorities(self):
        self._fixed_group_pri = self._get_group_fixed_priorities()
        self._fixed_channel_pri = [self._get_channel_fixed_priorities(r) for r, _ in self.groups]
        # Default order is highest to lowest, which by default should be the
        # fixed priority order
        self._rr_group_pri = list(self._fixed_group_pri)
        self._rr_channel_pri = [list(c) for c in self._fixed_channel_pri]

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
                sorted(((self.registers.cpr[c].chpri, c) for c in channels), reverse=True)]

    def addPending(self, config):
        self._pending[config.channel] = config

        # Because there are pending DMA transfers, ensure that the
        # "processActiveTransfers" function is queued for extra processing
        self.emu.addExtraProcessing(self.processActiveTransfers)

    def getPending(self):
        """
        Return the next channel that has a pending transfer (if any)
        """
        # TODO: add transfers to the pending list in priority order so we don't
        # have to do these calculations each time, with the current
        # implementation it adds about 1.3 seconds to each bootloader
        # application verification/SPI transmit loop (as measured with the
        # logging timestamps)

        if self.registers.mcr.erga == 0:
            groups = self._fixed_group_pri
        else:
            groups = self._rr_group_pri

        if self.registers.mcr.erca == 0:
            channels = self._fixed_channel_pri
        else:
            channels = self._rr_channel_pri

        group = None
        channel = None
        for group in groups:
            try:
                channel = next(c for c in channels[group] if c in self._pending)
                break
            except StopIteration:
                # Try the next group
                pass

        if group is not None and channel is not None:
            # If RR group priority is enabled, move the found group to the end.
            if self.registers.mcr.erga == 1:
                self._rr_group_pri.remove(group)
                self._rr_group_pri.append(group)

            # If RR group priority is enabled, move the found channel to the
            # end.
            if self.registers.mcr.erca == 1:
                self._rr_channel_pri[group].remove(channel)
                self._rr_channel_pri[group].append(channel)

            # return the config
            return self._pending[channel]
        else:
            return None

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
        if offset in self._convenience_handlers and not \
                offset in (EDMA_ERQRH_OFFSET, EDMA_ERQRL_OFFSET):
            # The convenience registers should always read 0 and are all 1 byte
            # wide.
            return b'\x00' * size
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
            handler(e_bits.parsebytes(data, 0, len(data), bigend=self.emu.getEndian()))
        else:
            super()._setPeriphReg(offset, data)

    def _mmio_read(self, va, offset, size):
        """
        Standard MMIOPeripheral._mmio_read() function with the log comments
        removed to reduce clutter when running in interactive mode and the
        firmware is idling.
        """
        if size > PPC_MAX_READ_SIZE:
            # Assume that this is not a value being changed by emulated
            # instructions
            # TODO: this seems inefficient, but should be good enough for now
            return self._slow_mmio_read(va, offset, size)

        try:
            return self._getPeriphReg(offset, size)

        except (MceDataReadBusError, AlignmentException) as exc:
            # Add in the correct machine state information to this exception
            exc.kwargs.update({
                'va': va,
                'pc': self.emu.getProgramCounter(),
            })
            raise exc

    def handleWriteERQRH(self, value):
        new_bits = value & ~self.registers.erqrh
        self.registers.erqrh = value

        # Attempt to start any new transfers
        for channel in gen_set_bits(new_bits):
            channel += EDMA_B_NUM_CHAN
            if self.registers.hrsh & EDMA_INT_MASKS[channel]:
                self.startTransfer(channel)

    def handleWriteERQRL(self, value):
        new_bits = value & ~self.registers.erqrl
        self.registers.erqrl = value

        # Attempt to start any new transfers
        for channel in gen_set_bits(new_bits):
            if self.registers.hrsl & EDMA_INT_MASKS[channel]:
                self.startTransfer(channel)

    def setERQR(self, channel):
        # If bit 0 is set, ignore the write
        if channel & 0x80:
            return

        # If bit 1 is set, set all ERQR flags
        if channel & 0x40:
            if self.num_channels == EDMA_A_NUM_CHAN:
                self.registers.erqrh = 0xFFFFFFFF
            self.registers.erqrl = 0xFFFFFFFF

            if self.num_channels == EDMA_A_NUM_CHAN:
                for channel in gen_set_bits(self.registers.hrsh):
                    self.startTransfer(channel + EDMA_B_NUM_CHAN)
            for channel in gen_set_bits(self.registers.hrsl):
                self.startTransfer(channel)

        else:
            # Otherwise only set the specified ERQR flag
            if channel >= EDMA_B_NUM_CHAN:
                self.registers.erqrh |= EDMA_INT_MASKS[channel]
                if self.registers.hrsh & EDMA_INT_MASKS[channel]:
                    self.startTransfer(channel)

            else:
                self.registers.erqrl |= EDMA_INT_MASKS[channel]
                if self.registers.hrsl & EDMA_INT_MASKS[channel]:
                    self.startTransfer(channel)

    def clearERQR(self, channel):
        # If bit 0 is set, ignore the write
        if channel & 0x80:
            return

        # If bit 1 is set, clear all ERQR flags
        if channel & 0x40:
            if self.num_channels == EDMA_A_NUM_CHAN:
                self.registers.erqrh = 0x00000000
            self.registers.erqrl = 0x00000000
        else:
            # Otherwise only clear the specified ERQR flag
            if channel >= EDMA_B_NUM_CHAN:
                self.registers.erqrh &= ~EDMA_INT_MASKS[channel]
            else:
                self.registers.erqrl &= ~EDMA_INT_MASKS[channel]

    def setEEIR(self, channel):
        # If bit 0 is set, ignore the write
        if channel & 0x80:
            return

        # If bit 1 is set, set all EEIR flags
        if channel & 0x40:
            if self.num_channels == EDMA_A_NUM_CHAN:
                self.registers.eeirh = 0xFFFFFFFF
            self.registers.eeirl = 0xFFFFFFFF
        else:
            # Otherwise only set the specified EEIR flag
            if channel >= EDMA_B_NUM_CHAN:
                self.registers.eeirh |= EDMA_INT_MASKS[channel]
            else:
                self.registers.eeirl |= EDMA_INT_MASKS[channel]

    def clearEEIR(self, channel):
        # If bit 0 is set, ignore the write
        if channel & 0x80:
            return

        # If bit 1 is set, clear all EEIR flags
        if channel & 0x40:
            if self.num_channels == EDMA_A_NUM_CHAN:
                self.registers.eeirh = 0x00000000
            self.registers.eeirl = 0x00000000
        else:
            # Otherwise only clear the specified EEIR flag
            if channel >= EDMA_B_NUM_CHAN:
                self.registers.eeirh &= ~EDMA_INT_MASKS[channel]
            else:
                self.registers.eeirl &= ~EDMA_INT_MASKS[channel]

    def clearIRQR(self, channel):
        # If bit 0 is set, ignore the write
        if channel & 0x80:
            return

        # If bit 1 is set, clear all IRQR flags
        if channel & 0x40:
            if self.num_channels == EDMA_A_NUM_CHAN:
                self.registers.irqrh = 0x00000000
            self.registers.irqrl = 0x00000000
        else:
            # Otherwise only clear the specified IRQR flag
            if channel >= EDMA_B_NUM_CHAN:
                self.registers.irqrh &= ~EDMA_INT_MASKS[channel]
            else:
                self.registers.irqrl &= ~EDMA_INT_MASKS[channel]

    def clearER(self, channel):
        # If bit 0 is set, ignore the write
        if channel & 0x80:
            return

        # If bit 1 is set, clear all ER flags
        if channel & 0x40:
            if self.num_channels == EDMA_A_NUM_CHAN:
                self.registers.vsOverrideValue('erh', 0x00000000)
            self.registers.vsOverrideValue('erl', 0x00000000)
        else:
            # Otherwise only clear the specified ER flag
            if channel >= EDMA_B_NUM_CHAN:
                value = self.registers.erh & ~EDMA_INT_MASKS[channel]
                self.registers.vsOverrideValue('erh', value)
            else:
                value = self.registers.erl & ~EDMA_INT_MASKS[channel]
                self.registers.vsOverrideValue('erl', value)

    def setStart(self, channel):
        # If bit 0 is set, ignore the write
        if channel & 0x80:
            return

        # If bit 1 is set, set the START flag in all TCDs
        if channel & 0x40:
            for chan in range(self.num_channels):
                self.registers.tcd[chan].start = 1
                if self.registers.tcd[chan].active == 0 and \
                        channel not in self._pending:
                    logger.debug('[%s] Starting DMA channel %d from SW trigger', self.devname, chan)
                    self.startTransfer(chan)
        else:
            # Otherwise only set the specified START flag
            self.registers.tcd[channel].start = 1
            if self.registers.tcd[channel].active == 0 and \
                    channel not in self._pending:
                logger.debug('[%s] Starting DMA channel %d from SW trigger', self.devname, channel)
                self.startTransfer(channel)

    def clearDone(self, channel):
        # If bit 0 is set, ignore the write
        if channel & 0x80:
            return

        # If bit 1 is set, clear the DONE flag in all TCDs
        if channel & 0x40:
            for chan in range(self.num_channels):
                self.registers.tcd[chan].done = 0
        else:
            # Otherwise only clear the specified DONE flag
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
        self._update_chan_priorities()
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
            for channel in list(self._pending):
                del self._pending[channel]

                # Make the channel look as if the minor loop had completed
                self.registers.tcd[channel].start = 0
                self.registers.tcd[channel].active = 0
                self.registers.tcd[channel].done = 0

            # Clear the CXFR bit
            self.registers.mcr.cxfr = 0

        if self.registers.mcr.ecx == 1:
            self._active = None
            for channel in list(self._pending):
                del self._pending[channel]

                # cancel the transfer and set the error status
                self.registers.tcd[channel].start = 0
                self.setError(channel, 'ecx')

            # Clear the CXFR bit
            self.registers.mcr.ecx = 0

        # If DMA is not halted, ensure there are no transfers to start
        if self.registers.mcr.halt == 0:
            any_pending = False
            for channel in range(self.num_channels):
                if self.registers.tcd[channel].start == 1 and \
                        self.registers.tcd[channel].active == 0 and \
                        channel not in self._pending:
                    logger.debug('[%s] Starting DMA channel %d after MCR[HALT] cleared', self.devname, channel)
                    self.startTransfer(channel)
                elif channel in self._pending:
                    any_pending = True

            # If there are any pending transfers to process, ensure that the
            # processActiveTransfers extra processing function is enabled.
            if any_pending:
                self.emu.addExtraProcessing(self.processActiveTransfers)

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
        tcd_offset = foffset % EDMA_TCDx_SIZE
        if EDMA_TCD_STATUS_OFF in range(tcd_offset, tcd_offset + size):
            channel = idx

            # If the DONE bit is set the E_SG and MAJOR.E_LINK bits must be 0
            if self.registers.tcd[channel].done == 1:
                self.registers.tcd[channel].major_e_link = 0
                self.registers.tcd[channel].e_sg = 0

            # if START is set but not ACTIVE, we need to process this transfer,
            # if DMA is enabled
            if self.registers.tcd[channel].start == 1 and \
                    self.registers.tcd[channel].active == 0 and \
                    channel not in self._pending:
                if self.registers.mcr.halt == 1:
                    logger.debug('[%s] ignoring SW initiated transfer for channel %d: DMA halted',
                                 self.devname, channel)
                else:
                    logger.debug('[%s] Starting DMA channel %d from SW trigger', self.devname, channel)
                    self.startTransfer(channel)

    def dmaRequest(self, channel):
        """
        Hardware initiated DMA request for a specific channel
        """
        self.setHRS(channel)

        # Only initiate a request if hardware service requests are enabled
        if channel >= EDMA_B_NUM_CHAN:
            if self.registers.erqrh & EDMA_INT_MASKS[channel]:
                self.startTransfer(channel)
        else:
            if self.registers.erqrl & EDMA_INT_MASKS[channel]:
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

        # config.ssize will be set to None if the TCD has an invalid value
        # in SSIZE field
        if config.ssize is None:
            logger.debug('[%s] channel %d SAE validation error (ssize: %s)',
                         self.devname, channel, config.ssize)
            self.setError(channel, 'sae')
            return None

        # If the ssize was valid, do the remaining ssize related checks

        # Source Address Error checks (esr.sae):
        #   - tcd.saddr is inconsistent with tcd.ssize
        #   - tcd.saddr is inconsistent with tcd.soff (not sure how to check
        #   this?)
        if config.tcd.saddr % config.ssize != 0:
            logger.debug('[%s] channel %d SAE validation error (saddr: %#x, ssize: %d)',
                         self.devname, channel, config.tcd.saddr, config.ssize)
            self.setError(channel, 'sae')
            return None

        # Source Offset Error checks (esr.soe):
        #   - tcd.soff is inconsistent with tcd.ssize
        if config.tcd.soff % config.ssize != 0:
            logger.debug('[%s] channel %d SOE validation error (soff: %d, ssize: %d)',
                         self.devname, channel, config.tcd.soff, config.ssize)
            self.setError(channel, 'soe')
            return None

        # config.dsize will be set to None if the TCD has an invalid value
        # in DSIZE field
        if config.dsize is None:
            logger.debug('[%s] channel %d DAE validation error (dsize: %s)',
                         self.devname, channel, config.dsize)
            self.setError(channel, 'dae')
            return None

        # If the dsize was valid, do the remaining ssize related checks

        # Destination Address Error checks (esr.dae):
        #   - tcd.daddr is inconsistent with tcd.dsize
        #   - tcd.daddr is inconsistent with tcd.doff (not surehow to check
        #   this?)
        if config.tcd.daddr % config.dsize != 0:
            logger.debug('[%s] channel %d DAE validation error (daddr: %#x, dsize: %d)',
                         self.devname, channel, config.tcd.daddr, config.dsize)
            self.setError(channel, 'dae')
            return None

        # Destination Offset Error checks (esr.doe):
        #   - tcd.doff is inconsistent with tcd.dsize
        if config.tcd.doff % config.dsize != 0:
            logger.debug('[%s] channel %d DOE validation error (doff: %d, dsize: %d)',
                         self.devname, channel, config.tcd.doff, config.dsize)
            self.setError(channel, 'doe')
            return None

        # NBYTES/CITER Configuration Error checks (esr.nce):
        #   - tcd.nbytes is not a multiple of tcd.ssize and tcd.dsize
        if config.nbytes % config.ssize or config.nbytes % config.dsize:
            logger.debug('[%s] channel %d NCE validation error (nbytes: %d, ssize: %d, dsize: %d)',
                         self.devname, channel, config.nbytes, config.ssize, config.dsize)
            self.setError(channel, 'nce')
            return None

        #   - tcd.citer == 0 (!= tcd.biter)
        #   - tcd.citer_e_link != tcd.biter_e_link
        if config.citer == 0 or config.tcd.citer != config.tcd.biter:
            logger.debug('[%s] channel %d NCE validation error (biter: %#x, citer: %#x|%d)',
                         self.devname, channel, config.tcd.biter, config.tcd.citer, config.citer)
            self.setError(channel, 'nce')
            return None

        # Scatter-Gather Configuration Error checks (esr.sge):
        #   - ensure tcd.dlast_sga is on a 32 byte boundary
        if config.tcd.e_sg:
            if config.tcd.dlast_sga % EDMA_XFER_SIZE_ALIGNMENT[EDMA_XFER_SIZE.S32Bit] != 0:
                logger.debug('[%s] channel %d SGE validation error (e_sg: %d, dlast_sga: %#x)',
                             self.devname, channel, config.tcd.e_sg, config.tcd.dlast_sga)
                self.setError(channel, 'sge')
                return None

        num_minor_loops = config.nbytes // max(config.ssize, config.dsize)
        logger.debug('[%s] validated channel %d config (%d x %d loops)',
                     self.devname, channel, config.citer, num_minor_loops)

        return config

    def setError(self, channel, flag):
        self.registers.esr.vsOverrideValue('vld', 1)
        self.registers.esr.vsOverrideValue('errchn', channel)
        self.registers.esr.vsOverrideValue(flag, 1)

        if self.registers.mcr.hoe == 1:
            self.registers.mcr.halt = 1

        logger.debug('[%s] channel %d error: %s', self.devname, channel, flag)

        self.event('error', channel, EDMA_INT_MASKS[channel])

    def startTransfer(self, channel):
        # Ensure that the channel does not have a transfer pending already
        if channel in self._pending:
            return

        # Now set the start flag
        self.registers.tcd[channel].start = 1

        # And start the transfer, if DMA is enabled
        if self.registers.mcr.halt == 1:
            logger.debug('[%s] ignoring peripheral initiated transfer for channel %d: DMA halted',
                         self.devname, channel)
            return

        config = self.verifyChannelConfig(channel)
        if config is None:
            logger.debug('[%s] aborting transfer for channel %d: config error',
                    self.devname, channel)
        else:
            logger.debug('[%s] queuing transfer for channel %d',
                    self.devname, channel)

            # Now set the start flag (may be necessary if this was hardware 
            # initiated)
            self.registers.tcd[channel].start = 1

            # Save the current active configuration
            self.addPending(config)

    def processActiveTransfers(self):
        # If this DMA channel is halted (stalled), do nothing, the transfers
        # will be resumed when this DMA channel is no longer halted.
        if self.registers.mcr.halt == 1:
            return

        # Get the next transfer to process
        config = self._active
        if config is None:
            # Search for the next highest priority pending channel
            config = self.getPending()

        # If no pending transfer was found, there is nothing to do
        if config is None:
            return

        self._process_major_loop(config)

        # If there are more major loops to process for the current channel, next
        # cycle it will need to go through arbitration again in case round-robin
        # scheduling is enabled, and if the current transfer is finished this
        # will help check if there are any more pending transfers.
        self.emu.addExtraProcessing(self.processActiveTransfers)

    def _process_major_loop(self, config):
        # Indicate that this channel is active
        config.tcd.start = 0
        config.tcd.done = 0
        config.tcd.active = 1

        logger.debug('[%s] channel %d, major loop %d/%d, xfer %d bytes from 0x%08x[%d] to 0x%08x[%d]',
                     self.devname, config.channel, config.citer,
                     config.tcd.biter, config.nbytes, config.tcd.saddr,
                     config.ssize, config.tcd.daddr, config.dsize)

        data = bytearray()
        try:
            # Strictly speaking we could just read a big chunk of data but I
            # suppose we will emulate the minor loops
            for offset in range(0, config.nbytes, config.ssize):
                # Before reading from this address verify that there is a valid
                # TLB entry, we aren't doing this implicitly through readMemory
                # so the TLB miss exception isn't generated because that doesn't
                # seem to be the correct way to handle this.
                if not self.emu.isValidPointer(config.tcd.saddr+offset):
                    logger.debug('%s[%d:%d] TLB miss for source %#x',
                                 self.devname, config.channel, config.citer,
                                 config.tcd.saddr + offset)
                    raise MceDataReadBusError()

                data += self.emu.readMemory(config.tcd.saddr+offset, config.ssize)
        except MceDataReadBusError:
            self.setError(config.channel, 'sbe')

            # Remove this channel from the pending channels before halting
            # TODO: not 100% sure this is the way read errors should be handled?
            config.tcd.active = 0
            del self._pending[config.channel]

            return None

        try:
            for offset in range(0, len(data), config.dsize):
                # Before writing to this address verify that there is a valid
                # TLB entry, we aren't doing this implicitly through writeMemory
                # so the TLB miss exception isn't generated because that doesn't
                # seem to be the correct way to handle this.
                if not self.emu.isValidPointer(config.tcd.daddr+offset):
                    logger.debug('%s[%d:%d] TLB miss for destination %#x',
                                 self.devname, config.channel, config.citer,
                                 config.tcd.daddr + offset)
                    raise MceWriteBusError()

                self.emu.writeMemory(config.tcd.daddr+offset, data[offset:offset+config.dsize])
        except MceWriteBusError:
            self.setError(config.channel, 'dbe')

            # Remove this channel from the pending channels before halting
            # TODO: not 100% sure this is the way write errors should be
            # handled?
            config.tcd.active = 0
            del self._pending[config.channel]

            return None

        logger.debug("%s[%d:%d] [%x:%r] -> %r -> [%x:%r]", self.devname,
                        config.channel, config.citer, config.tcd.saddr,
                        config.ssize, data, config.tcd.daddr,
                        config.dsize)

        # Now that one major loop is complete, decrement citer, and process any
        # linked channels
        config.citer -= 1

        # Deactivate this channel
        config.tcd.active = 0

        # Adjust the source and destination addresses, this is done at the end 
        # of each minor loop regardless of if this is the last minor loop or 
        # not.
        #
        #TODO mloff
        saddr = config.tcd.saddr + config.tcd.soff
        if config.tcd.smod:
            config.tcd.saddr = (config.tcd.saddr & ~config.smod_mask) | \
                    (saddr & config.smod_mask)
        else:
            config.tcd.saddr = saddr

        daddr = config.tcd.daddr + config.tcd.doff
        if config.tcd.dmod:
            config.tcd.daddr = (config.tcd.daddr & ~config.dmod_mask) | \
                    (daddr & config.dmod_mask)
        else:
            config.tcd.daddr = daddr

        if config.citer != 0:
            # Check if an interrupt needs to be signaled for half-way
            # completing the transfer
            if config.tcd.int_half and \
                    config.tcd.citer == config.tcd.biter // 2:
                self.event('xfer', config.channel, EDMA_INT_MASKS[config.channel])

            if config.linkch is not None:
                # if CLM is set then a minor link loop to the same channel does
                # not have to go through priority arbitration again
                if self.registers.mcr.clm == 1 and config.linkch == config.channel:
                    logger.debug('[%s] re-activating current transfer for current channel %d',
                                 self.devname, config.channel)

                    # Immediately set the current active channel as the next
                    # channel to process
                    self._active = config
                else:
                    logger.debug('[%s] starting minor loop linked transfer %d for current channel %d',
                                 self.devname, config.linkch, config.channel)
                    self.startTransfer(config.linkch)

        else:
            logger.debug('[%s] channel %d transfer complete', self.devname,
                         config.channel)

            # Adjust the source and destination addresses
            saddr = config.tcd.saddr + config.tcd.slast
            if config.tcd.smod:
                config.tcd.saddr = (config.tcd.saddr & ~config.smod_mask) | \
                        (saddr & config.smod_mask)
            else:
                config.tcd.saddr = saddr

            daddr = config.tcd.daddr + config.tcd.dlast_sga
            if config.tcd.dmod:
                config.tcd.daddr = (config.tcd.daddr & ~config.dmod_mask) | \
                        (daddr & config.dmod_mask)
            else:
                config.tcd.daddr = daddr

            config.citer = config.tcd.biter

            # Set the done flag
            config.tcd.done = 1

            # Remove this TCD from pending
            del self._pending[config.channel]

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
                logger.debug('[%s] starting major loop linked transfer %d for current channel %d',
                             self.devname, config.tcd.major_linkch, channel)
                self.startTransfer(config.tcd.major_linkch)

            # Check if scatter-gather is configured for this channel, if so
            # overwrite the current channel and re-start it
            if config.tcd.e_sg == 1:
                tcd = self.emu.readMemory(config.tcd.dlast_sga, EDMA_TCDx_SIZE)
                addr = self.baseaddr + EDMA_TCDx_OFFSET + channel * EDMA_TCDx_SIZE
                self.emu.writeMemory(addr, tcd)

                logger.debug('[%s] queuing SG transfer in channel %d using TCD from 0x%08x',
                             self.devname, channel, config.tcd.dlast_sga)
                self.startTransfer(config.channel)
