import enum
import struct
from operator import rshift, lshift

import envi.bits as e_bits

from ..ppc_vstructs import *
from ..ppc_peripherals import *
from ..intc_exc import INTC_EVENT

import logging
logger = logging.getLogger(__name__)

__all__  = [
    'FlexCAN',
]


FLEXCAN_MAX_MB = 64

FLEXCAN_RxFIFO_MAX_LEN  = 6
FLEXCAN_RxFIFO_WARN_LEN = 5

# Constants used for setting RxFIFO interrupts:
# - Msg Available (MB5)
# - Warning       (MB6)
# - Overflow      (MB7)
FLEXCAN_RxFIFO_MSG_AVAIL_MASK = 1 << 5
FLEXCAN_RxFIFO_WARNING_MASK   = 1 << 6
FLEXCAN_RxFIFO_OVERFLOW_MASK  = 1 << 7


class FLEXCAN_MODE(enum.IntEnum):
    """
    For tracking the mode of the CAN peripheral
    """
    DISABLE     = 0
    FREEZE      = 1
    NORMAL      = 2
    LISTEN_ONLY = 3
    LOOP_BACK   = 4

FLEXCAN_STOPPED = (FLEXCAN_MODE.DISABLE, FLEXCAN_MODE.FREEZE)
FLEXCAN_RUNNING = (FLEXCAN_MODE.NORMAL, FLEXCAN_MODE.LISTEN_ONLY, FLEXCAN_MODE.LOOP_BACK)

# address offsets, needed for the special read/write checks that need to be made
# based on the mode of the peripheral
FLEXCAN_MCR_OFFSET              = 0x0000
FLEXCAN_CTRL_OFFSET             = 0x0004
FLEXCAN_TIMER_OFFSET            = 0x0008
FLEXCAN_RXGMASK_OFFSET          = 0x0010
FLEXCAN_RX14MASK_OFFSET         = 0x0014
FLEXCAN_RX15MASK_OFFSET         = 0x0018
FLEXCAN_ECR_OFFSET              = 0x001C
FLEXCAN_ESR_OFFSET              = 0x0020

# The IMASK2 and IFLAG2 registers are treated as reserved if <= 32 mailboxes are
# configured
FLEXCAN_IMASK2_OFFSET           = 0x0024
FLEXCAN_IMASK1_OFFSET           = 0x0028
FLEXCAN_IFLAG2_OFFSET           = 0x002C
FLEXCAN_IFLAG1_OFFSET           = 0x0030

# When MCR[MAXMB] > 32 (0x1F+1)
# - All MB offsets are valid
#
# When MCR[MAXMB] > 16 (0x0F+1) but <= 32 (0x1F+1)
# - MB offsets larger than FLEXCAN_MB32_OFFSET are reserved
#
# When MCR[MAXMB] <= 16 (0x0F+1)
# - MB offsets larger than FLEXCAN_MB16_OFFSET are reserved
FLEXCAN_MB0_OFFSET              = 0x0080
FLEXCAN_MB16_OFFSET             = 0x0180
FLEXCAN_MB32_OFFSET             = 0x0280
FLEXCAN_MB_END_OFFSET           = 0x0480

# In Rx FIFO mode the registers from 0x00E0 to 0x0100 (MB 6-7) are used for the
# Rx FIFO masks, MB 1-5 are reserved, all received messages that match against
# the RxFIFO masks can be read from MB0 sequentially, and MB8+ behave as normal.
FLEXCAN_MB1_OFFSET              = 0x0090
FLEXCAN_MB6_OFFSET              = 0x00E0
FLEXCAN_MB8_OFFSET              = 0x0100

# Because the mailbox registers are managed as just an array of 32-bit values
# here are some constants and masks

# Each mailbox is made up of 4 32-bit values
FLEXCAN_MBx_SIZE                = 4 * 4

# A range to iterate over all of mailboxes
FLEXCAN_MB_IDX_RANGE            = range(0*FLEXCAN_MBx_SIZE, FLEXCAN_MAX_MB*FLEXCAN_MBx_SIZE, FLEXCAN_MBx_SIZE)
FLEXCAN_MB_RANGE                = range(FLEXCAN_MAX_MB)

# Each mask register is made up of 1 32-bit value
FLEXCAN_RXIMRx_SIZE             = 4

# Rx-specific codes
FLEXCAN_CODE_RX_INACTIVE        = 0x00
FLEXCAN_CODE_RX_BUSY            = 0x01
FLEXCAN_CODE_RX_FULL            = 0x02
FLEXCAN_CODE_RX_OVERRUN         = 0x03
FLEXCAN_CODE_RX_EMPTY           = 0x04

# Tx codes
FLEXCAN_CODE_TX_INACTIVE        = 0x08
FLEXCAN_CODE_TX_ABORT           = 0x09
FLEXCAN_CODE_TX_ACTIVE          = 0x0C
FLEXCAN_CODE_TX_RTR             = 0x0A

# In theory this a mailbox code is changed from 0b1010 to 0b1110 while the CAN
# peripheral is responding to a RTR, if the code is manually set to 0b1110 then
# what is normally a remote response frame will instead be sent immediately.
FLEXCAN_CODE_TX_RTR_SENDING     = 0x0E

# When checking normal messages being received messages marked with these 3
# codes are checked to see if a message can be received, if the last valid
# mailbox that matches is FULL (or OVERRUN) then an overrun interrupt is
# generated instead of the message being received.
RX_CHECK_FILTER = (FLEXCAN_CODE_RX_EMPTY, FLEXCAN_CODE_RX_FULL, FLEXCAN_CODE_RX_OVERRUN)

# For RTR message reception the normal code to see would be FLEXCAN_CODE_TX_RTR,
# but the other options are FLEXCAN_CODE_TX_RTR_SENDING (manually sending an RTR
# data frame).
RTR_CHECK_FILTER = (FLEXCAN_CODE_TX_RTR, FLEXCAN_CODE_TX_RTR_SENDING)

# IDAM filter coding options
FLEXCAN_FILTER_MODE_ONE_FULL    = 0b00
FLEXCAN_FILTER_MODE_TWO_14BIT   = 0b01
FLEXCAN_FILTER_MODE_FOUR_8BIT   = 0b10
FLEXCAN_FILTER_MODE_REJECT_ALL  = 0b11

# The RxFIFO masks and shifts get weird, the masks and shifts for the REM, EXT,
# and ID fields are a list for each IDAM mode because there may be multiple
# filters built into a single register value.
FLEXCAN_RxFIFO_FILTER_REM_MASKS = (
    (0x80000000,),
    (0x80000000, 0x00008000),
    (),
    (),
)
FLEXCAN_RxFIFO_FILTER_REM_SHIFTS = (
    (0x80000000,),
    (0x80000000, 0x00008000),
    (),
    (),
)

FLEXCAN_RxFIFO_FILTER_EXT_MASKS = (
    (0x40000000,),
    (0x40000000, 0x00004000),
    (),
    (),
)
FLEXCAN_RxFIFO_FILTER_EXT_SHIFTS = (
    (0x40000000,),
    (0x40000000, 0x00004000),
    (),
    (),
)

# Standard shifts and masks for dealing with the ID
FLEXCAN_ID_MASK         = 0x1FFFFFFF
FLEXCAN_STD_ID_SHIFT    = 18
FLEXCAN_STD_ID_MASK     = 0x1FFC0000

# For the ID shifts and masks there are two different sets of values, one to
# make the filter an 11-bit (standard) ID, the second to make it a 29-bit
# (extended) ID
FLEXCAN_RxFIFO_FILTER_ID_MASKS = (
    # (11-bit, 29-bit) tuples for each filter style
    ((0x3FF80000, 0x3FFFFFFE),),
    ((0x3FF80000, 0x3FFF0000), (0x00003FF8, 0x00003FFF)),
    ((0xFF000000, 0xFF000000), (0x00FF0000, 0x00FF0000), (0x0000FF00, 0x000FF000), (0x000000FF, 0x000000FF)),
    (),
)

# Note that these shift values are intended to shift the filter to a position
# where it can be easily compared against the incoming message ID before it is
# placed into the FlexCAN registers in the required format.  Because some of the
# values are left shift, and others are right shift the only good way to do this
# is to have two entries for each value: (operation, amount)
FLEXCAN_RxFIFO_FILTER_ID_SHIFTS = (
    # (11-bit, 29-bit) tuples for each filter style
    (((rshift, 19), (rshift, 1)),),
    (((rshift, 19), (rshift, 1)), ((rshift, 3), (lshift, 15))),
    (((rshift, 21), (rshift, 3)), ((rshift, 13), (lshift, 5)), ((rshift, 5), (lshift, 13)), ((lshift, 3), (lshift, 21))),
    (),
)

# When MCR[MBFEN] == 1 and MCR[MAXMB] > 32 (0x1F+1)
# - All RXIMR offsets are valid
#
# When MCR[MBFEN] == 1 and MCR[MAXMB] > 16 (0x0F+1) but <= 32 (0x1F+1)
# - RXIMR offsets larger than FLEXCAN_RXIMR32_OFFSET are reserved
#
# When MCR[MBFEN] == 1 and MCR[MAXMB] <= 16 (0x0F+1)
# - RXIMR offsets larger than FLEXCAN_RXIMR16_OFFSET are reserved
#
# When MCR[MBFEN] == 0
# - All RXIMR offsets are reserved
FLEXCAN_RXIMR0_OFFSET    = 0x0880
FLEXCAN_RXIMR16_OFFSET   = 0x08C0
FLEXCAN_RXIMR32_OFFSET   = 0x0900
FLEXCAN_RXIMR_END_OFFSET = 0x0980


# Mapping of interrupt types based on the supported CAN peripherals.
# At the moment the general bus interrupt events are not emulated:
#
#           ISR EVENT         |    ISR source
#   --------------------------+-------------------
#    INTC_EVENT.CANx_ESR_BOFF | INTC_SRC.CANx_BUS
#    INTC_EVENT.CANx_ESR_TWRN | INTC_SRC.CANx_BUS
#    INTC_EVENT.CANx_ESR_RWRN | INTC_SRC.CANx_BUS
#    INTC_EVENT.CANx_ESR_ERR  | INTC_SRC.CANx_ERR
#
FLEXCAN_INT_EVENTS = {
    'FlexCAN_A': {
        'msg': (
            INTC_EVENT.CANA_MB0,     INTC_EVENT.CANA_MB1,     INTC_EVENT.CANA_MB2,     INTC_EVENT.CANA_MB3,
            INTC_EVENT.CANA_MB4,     INTC_EVENT.CANA_MB5,     INTC_EVENT.CANA_MB6,     INTC_EVENT.CANA_MB7,
            INTC_EVENT.CANA_MB8,     INTC_EVENT.CANA_MB9,     INTC_EVENT.CANA_MB10,    INTC_EVENT.CANA_MB11,
            INTC_EVENT.CANA_MB12,    INTC_EVENT.CANA_MB13,    INTC_EVENT.CANA_MB14,    INTC_EVENT.CANA_MB15,
            INTC_EVENT.CANA_MB16,    INTC_EVENT.CANA_MB17,    INTC_EVENT.CANA_MB18,    INTC_EVENT.CANA_MB19,
            INTC_EVENT.CANA_MB20,    INTC_EVENT.CANA_MB21,    INTC_EVENT.CANA_MB22,    INTC_EVENT.CANA_MB23,
            INTC_EVENT.CANA_MB24,    INTC_EVENT.CANA_MB25,    INTC_EVENT.CANA_MB26,    INTC_EVENT.CANA_MB27,
            INTC_EVENT.CANA_MB28,    INTC_EVENT.CANA_MB29,    INTC_EVENT.CANA_MB30,    INTC_EVENT.CANA_MB31,
            INTC_EVENT.CANA_MB32,    INTC_EVENT.CANA_MB33,    INTC_EVENT.CANA_MB34,    INTC_EVENT.CANA_MB35,
            INTC_EVENT.CANA_MB36,    INTC_EVENT.CANA_MB37,    INTC_EVENT.CANA_MB38,    INTC_EVENT.CANA_MB39,
            INTC_EVENT.CANA_MB40,    INTC_EVENT.CANA_MB41,    INTC_EVENT.CANA_MB42,    INTC_EVENT.CANA_MB43,
            INTC_EVENT.CANA_MB44,    INTC_EVENT.CANA_MB45,    INTC_EVENT.CANA_MB46,    INTC_EVENT.CANA_MB47,
            INTC_EVENT.CANA_MB48,    INTC_EVENT.CANA_MB49,    INTC_EVENT.CANA_MB50,    INTC_EVENT.CANA_MB51,
            INTC_EVENT.CANA_MB52,    INTC_EVENT.CANA_MB53,    INTC_EVENT.CANA_MB54,    INTC_EVENT.CANA_MB55,
            INTC_EVENT.CANA_MB56,    INTC_EVENT.CANA_MB57,    INTC_EVENT.CANA_MB58,    INTC_EVENT.CANA_MB59,
            INTC_EVENT.CANA_MB60,    INTC_EVENT.CANA_MB61,    INTC_EVENT.CANA_MB62,    INTC_EVENT.CANA_MB63,
        ),
    },
    'FlexCAN_B': {
        'msg': (
            INTC_EVENT.CANB_MB0,     INTC_EVENT.CANB_MB1,     INTC_EVENT.CANB_MB2,     INTC_EVENT.CANB_MB3,
            INTC_EVENT.CANB_MB4,     INTC_EVENT.CANB_MB5,     INTC_EVENT.CANB_MB6,     INTC_EVENT.CANB_MB7,
            INTC_EVENT.CANB_MB8,     INTC_EVENT.CANB_MB9,     INTC_EVENT.CANB_MB10,    INTC_EVENT.CANB_MB11,
            INTC_EVENT.CANB_MB12,    INTC_EVENT.CANB_MB13,    INTC_EVENT.CANB_MB14,    INTC_EVENT.CANB_MB15,
            INTC_EVENT.CANB_MB16,    INTC_EVENT.CANB_MB17,    INTC_EVENT.CANB_MB18,    INTC_EVENT.CANB_MB19,
            INTC_EVENT.CANB_MB20,    INTC_EVENT.CANB_MB21,    INTC_EVENT.CANB_MB22,    INTC_EVENT.CANB_MB23,
            INTC_EVENT.CANB_MB24,    INTC_EVENT.CANB_MB25,    INTC_EVENT.CANB_MB26,    INTC_EVENT.CANB_MB27,
            INTC_EVENT.CANB_MB28,    INTC_EVENT.CANB_MB29,    INTC_EVENT.CANB_MB30,    INTC_EVENT.CANB_MB31,
            INTC_EVENT.CANB_MB32,    INTC_EVENT.CANB_MB33,    INTC_EVENT.CANB_MB34,    INTC_EVENT.CANB_MB35,
            INTC_EVENT.CANB_MB36,    INTC_EVENT.CANB_MB37,    INTC_EVENT.CANB_MB38,    INTC_EVENT.CANB_MB39,
            INTC_EVENT.CANB_MB40,    INTC_EVENT.CANB_MB41,    INTC_EVENT.CANB_MB42,    INTC_EVENT.CANB_MB43,
            INTC_EVENT.CANB_MB44,    INTC_EVENT.CANB_MB45,    INTC_EVENT.CANB_MB46,    INTC_EVENT.CANB_MB47,
            INTC_EVENT.CANB_MB48,    INTC_EVENT.CANB_MB49,    INTC_EVENT.CANB_MB50,    INTC_EVENT.CANB_MB51,
            INTC_EVENT.CANB_MB52,    INTC_EVENT.CANB_MB53,    INTC_EVENT.CANB_MB54,    INTC_EVENT.CANB_MB55,
            INTC_EVENT.CANB_MB56,    INTC_EVENT.CANB_MB57,    INTC_EVENT.CANB_MB58,    INTC_EVENT.CANB_MB59,
            INTC_EVENT.CANB_MB60,    INTC_EVENT.CANB_MB61,    INTC_EVENT.CANB_MB62,    INTC_EVENT.CANB_MB63,
        ),
    },
    'FlexCAN_C': {
        'msg': (
            INTC_EVENT.CANC_MB0,     INTC_EVENT.CANC_MB1,     INTC_EVENT.CANC_MB2,     INTC_EVENT.CANC_MB3,
            INTC_EVENT.CANC_MB4,     INTC_EVENT.CANC_MB5,     INTC_EVENT.CANC_MB6,     INTC_EVENT.CANC_MB7,
            INTC_EVENT.CANC_MB8,     INTC_EVENT.CANC_MB9,     INTC_EVENT.CANC_MB10,    INTC_EVENT.CANC_MB11,
            INTC_EVENT.CANC_MB12,    INTC_EVENT.CANC_MB13,    INTC_EVENT.CANC_MB14,    INTC_EVENT.CANC_MB15,
            INTC_EVENT.CANC_MB16,    INTC_EVENT.CANC_MB17,    INTC_EVENT.CANC_MB18,    INTC_EVENT.CANC_MB19,
            INTC_EVENT.CANC_MB20,    INTC_EVENT.CANC_MB21,    INTC_EVENT.CANC_MB22,    INTC_EVENT.CANC_MB23,
            INTC_EVENT.CANC_MB24,    INTC_EVENT.CANC_MB25,    INTC_EVENT.CANC_MB26,    INTC_EVENT.CANC_MB27,
            INTC_EVENT.CANC_MB28,    INTC_EVENT.CANC_MB29,    INTC_EVENT.CANC_MB30,    INTC_EVENT.CANC_MB31,
            INTC_EVENT.CANC_MB32,    INTC_EVENT.CANC_MB33,    INTC_EVENT.CANC_MB34,    INTC_EVENT.CANC_MB35,
            INTC_EVENT.CANC_MB36,    INTC_EVENT.CANC_MB37,    INTC_EVENT.CANC_MB38,    INTC_EVENT.CANC_MB39,
            INTC_EVENT.CANC_MB40,    INTC_EVENT.CANC_MB41,    INTC_EVENT.CANC_MB42,    INTC_EVENT.CANC_MB43,
            INTC_EVENT.CANC_MB44,    INTC_EVENT.CANC_MB45,    INTC_EVENT.CANC_MB46,    INTC_EVENT.CANC_MB47,
            INTC_EVENT.CANC_MB48,    INTC_EVENT.CANC_MB49,    INTC_EVENT.CANC_MB50,    INTC_EVENT.CANC_MB51,
            INTC_EVENT.CANC_MB52,    INTC_EVENT.CANC_MB53,    INTC_EVENT.CANC_MB54,    INTC_EVENT.CANC_MB55,
            INTC_EVENT.CANC_MB56,    INTC_EVENT.CANC_MB57,    INTC_EVENT.CANC_MB58,    INTC_EVENT.CANC_MB59,
            INTC_EVENT.CANC_MB60,    INTC_EVENT.CANC_MB61,    INTC_EVENT.CANC_MB62,    INTC_EVENT.CANC_MB63,
        ),
    },
    'FlexCAN_D': {
        'msg': (
            INTC_EVENT.CAND_MB0,     INTC_EVENT.CAND_MB1,     INTC_EVENT.CAND_MB2,     INTC_EVENT.CAND_MB3,
            INTC_EVENT.CAND_MB4,     INTC_EVENT.CAND_MB5,     INTC_EVENT.CAND_MB6,     INTC_EVENT.CAND_MB7,
            INTC_EVENT.CAND_MB8,     INTC_EVENT.CAND_MB9,     INTC_EVENT.CAND_MB10,    INTC_EVENT.CAND_MB11,
            INTC_EVENT.CAND_MB12,    INTC_EVENT.CAND_MB13,    INTC_EVENT.CAND_MB14,    INTC_EVENT.CAND_MB15,
            INTC_EVENT.CAND_MB16,    INTC_EVENT.CAND_MB17,    INTC_EVENT.CAND_MB18,    INTC_EVENT.CAND_MB19,
            INTC_EVENT.CAND_MB20,    INTC_EVENT.CAND_MB21,    INTC_EVENT.CAND_MB22,    INTC_EVENT.CAND_MB23,
            INTC_EVENT.CAND_MB24,    INTC_EVENT.CAND_MB25,    INTC_EVENT.CAND_MB26,    INTC_EVENT.CAND_MB27,
            INTC_EVENT.CAND_MB28,    INTC_EVENT.CAND_MB29,    INTC_EVENT.CAND_MB30,    INTC_EVENT.CAND_MB31,
            INTC_EVENT.CAND_MB32,    INTC_EVENT.CAND_MB33,    INTC_EVENT.CAND_MB34,    INTC_EVENT.CAND_MB35,
            INTC_EVENT.CAND_MB36,    INTC_EVENT.CAND_MB37,    INTC_EVENT.CAND_MB38,    INTC_EVENT.CAND_MB39,
            INTC_EVENT.CAND_MB40,    INTC_EVENT.CAND_MB41,    INTC_EVENT.CAND_MB42,    INTC_EVENT.CAND_MB43,
            INTC_EVENT.CAND_MB44,    INTC_EVENT.CAND_MB45,    INTC_EVENT.CAND_MB46,    INTC_EVENT.CAND_MB47,
            INTC_EVENT.CAND_MB48,    INTC_EVENT.CAND_MB49,    INTC_EVENT.CAND_MB50,    INTC_EVENT.CAND_MB51,
            INTC_EVENT.CAND_MB52,    INTC_EVENT.CAND_MB53,    INTC_EVENT.CAND_MB54,    INTC_EVENT.CAND_MB55,
            INTC_EVENT.CAND_MB56,    INTC_EVENT.CAND_MB57,    INTC_EVENT.CAND_MB58,    INTC_EVENT.CAND_MB59,
            INTC_EVENT.CAND_MB60,    INTC_EVENT.CAND_MB61,    INTC_EVENT.CAND_MB62,    INTC_EVENT.CAND_MB63,
        ),
    },
}


FLEXCAN_INT_STATUS_REGS = {
    'msg': ('iflag1', 'iflag2'),
}

FLEXCAN_INT_FLAG_REGS = {
    'msg': ('imask1', 'imask2'),
}

# Simple MB to IFLAG1/2 bitmask lookup. Mailboxes 0-31 are in IFLAG1, 32-63 are
# in IFLAG2. Unlike most of the PowerPC documentation the MSB is the higher bit
# value rather than the lower (in IFLAG1 MB0 is the LSB and MB31 is the MSB).
FLEXCAN_IFLAG1_MASK = tuple([1 << mb for mb in range(0, 32)] + [None for i in range(32, 64)])
FLEXCAN_IFLAG2_MASK = tuple([None for i in range(32, 64)] + [1 << (mb-32) for mb in range(32, 64)])


class FLEXCAN_x_MCR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.mdis = v_bits(1)
        self.frz = v_bits(1, 1)
        self.fen = v_bits(1)
        self.halt = v_bits(1, 1)
        self.not_rdy = v_const(1, 1)
        self._pad0 = v_const(1)
        self.soft_rst = v_bits(1)
        self.frz_ack = v_const(1, 1)
        self.supv = v_bits(1, 1)
        self._pad1 = v_const(1)
        self.wrn_en = v_bits(1)
        self.mdisack = v_const(1, 1)
        self._pad2 = v_const(1)
        self.doze = v_bits(1)
        self.srx_dis = v_bits(1)
        self.mbfen = v_bits(1)
        self._pad3 = v_const(2)
        self.lprio_en = v_bits(1)
        self.aen = v_bits(1)
        self._pad4 = v_const(2)
        self.idam = v_bits(2)
        self._pad5 = v_const(2)
        self.maxmb = v_bits(6, 0b001111)

class FLEXCAN_x_CTRL(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.presdiv = v_bits(8)
        self.rjw = v_bits(2)
        self.pseg1 = v_bits(3)
        self.pseg2 = v_bits(3)
        self.boff_msk = v_bits(1)
        self.err_msk = v_bits(1)
        self.clk_src = v_bits(1)
        self.lpb = v_bits(1)
        self.twrn_msk = v_bits(1)
        self.rwrn_msk = v_bits(1)
        self._pad0 = v_bits(2)
        self.smp = v_bits(1)
        self.boff_rec = v_bits(1)
        self.tsyn = v_bits(1)
        self.lbuf = v_bits(1)
        self.lom = v_bits(1)
        self.propseg = v_bits(3)

class FLEXCAN_x_ECR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(16)
        self.rx_err = v_bits(8)
        self.tx_err = v_bits(8)

class FLEXCAN_x_ESR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(14)
        self.twrn_int = v_w1c(1)
        self.rwrn_int = v_w1c(1)
        self.bit1_err = v_const(1)
        self.bit0_err = v_const(1)
        self.ack_err = v_const(1)
        self.crc_err = v_const(1)
        self.frm_err = v_const(1)
        self.stf_err = v_const(1)
        self.tx_wrn = v_const(1)
        self.rx_wrn = v_const(1)
        self.idle = v_const(1)
        self.txrx = v_const(1)
        self.flt_conf = v_const(1)
        self.pad1 = v_const(1)
        self.boff_int = v_w1c(1)
        self.err_int = v_w1c(1)
        self.pad2 = v_const(1)


class CanMsg:
    """
    Object used to make it easier to send/recv CAN messages to external IO
    clients, and also to write/read message data to/from FlexCAN mailboxes.
    """
    # struct pack/unpack format for going to/from the CAN peripheral message
    # buffer structure. The first byte is the CODE which is not captured in the
    # message that is transmitted.
    _fmt = '>BBHI8s'

    def __init__(self, rtr, ide, arbid, length, data):
        """
        Constructor for the CanMsg class, sets the initial rtr, ide, arbid,
        length and data attributes for the message object.
        """
        self.rtr = rtr
        self.ide = ide
        self.arbid = arbid
        self.length = length
        self.data = data
        self.timestamp = None

    @classmethod
    def from_mb(cls, mb_data, offset=0):
        """
        Creates a CanMsg object based on the mailbox data structure
        """
        # The code and timestamp fields are not used by the CanMsg class
        _, length_val, _, id_val, data = struct.unpack_from(cls._fmt, mb_data, offset=offset)

        # Now extract the RTR, IDE and isolated length values
        ide = (length_val & 0x20) >> 5
        rtr = (length_val & 0x10) >> 4
        length = length_val & 0x0F

        # If this is an extended mode message then the arbid is just the value
        # in the register (without the priority bits), if it is a standard mode
        # message then right shift the ID 18 bits because the 11-bit ID is in
        # the most significant bits of the ID portion of the register.
        if ide:
            arbid = id_val & FLEXCAN_ID_MASK
        else:
            arbid = (id_val & FLEXCAN_ID_MASK) >> FLEXCAN_STD_ID_SHIFT

        return cls(rtr=rtr, ide=ide, arbid=arbid, length=length, data=data[:length])

    def _encode_len_ts_id(self, prio, timestamp):
        """
        Pack the length and ID values as appropriate for encoding into bytes
        with self._fmt
        """
        # pack the flags into the length value, if IDE is set also set SRR
        length_val = (self.rtr << 4) | self.length
        if self.ide:
            length_val |= 0x60

        if timestamp is not None:
            ts_val = timestamp
        elif self.timestamp is not None:
            ts_val = self.timestamp
        else:
            ts_val = 0

        # Now format the ID as expected, the priority should be the top 3 bits
        if self.ide:
            id_val = (prio << 29) | self.arbid
        else:
            id_val = (prio << 29) | (self.arbid << FLEXCAN_STD_ID_SHIFT)

        return (length_val, ts_val, id_val)

    def into_mb(self, mb_data, offset, code=FLEXCAN_CODE_RX_INACTIVE, timestamp=None, prio=0):
        """
        Returns the mailbox data structure for this CanMsg object
        """
        length_val, ts_val, id_val = self._encode_len_ts_id(prio=prio, timestamp=timestamp)
        struct.pack_into(self._fmt, mb_data, offset, code, length_val, ts_val, id_val, self.data)

    def __repr__(self):
        return '%s(rtr=%d, ide=%d, id=%08x, length=%d, data=%r)' % \
                (self.__class__.__name__, self.rtr, self.ide, self.arbid, self.length, self.data)

    def encode(self, code=FLEXCAN_CODE_RX_INACTIVE, timestamp=None, prio=0):
        """
        Return bytes that represent the data to be written into the CAN
        peripheral registers.
        """
        length_val, ts_val, id_val = self._encode_len_ts_id(prio=prio, timestamp=timestamp)
        return struct.pack(self._fmt, code, length_val, ts_val, id_val, self.data)

    def __eq__(self, other):
        """
        To make it easier to compare msgs during testing
        """
        return self.rtr == other.rtr and \
                self.ide == other.ide and \
                self.arbid == other.arbid and \
                self.length == other.length and \
                self.data == other.data


class FLEXCAN_REGISTERS(PeripheralRegisterSet):
    """
    Register set for FlexCAN peripherals.  All registers are handled by this
    object except for the TIMER register which requires custom processing.
    """
    def __init__(self):
        super().__init__()

        self.mcr        = (FLEXCAN_MCR_OFFSET,      FLEXCAN_x_MCR())
        self.ctrl       = (FLEXCAN_CTRL_OFFSET,     FLEXCAN_x_CTRL())
        self.rxgmask    = (FLEXCAN_RXGMASK_OFFSET,  v_bits(32, 0xFFFFFFFF))
        self.rx14mask   = (FLEXCAN_RX14MASK_OFFSET, v_bits(32, 0xFFFFFFFF))
        self.rx15mask   = (FLEXCAN_RX15MASK_OFFSET, v_bits(32, 0xFFFFFFFF))
        self.ecr        = (FLEXCAN_ECR_OFFSET,      FLEXCAN_x_ECR())
        self.esr        = (FLEXCAN_ESR_OFFSET,      FLEXCAN_x_ESR())
        self.imask2     = (FLEXCAN_IMASK2_OFFSET,   v_bits(32))
        self.imask1     = (FLEXCAN_IMASK1_OFFSET,   v_bits(32))
        self.iflag2     = (FLEXCAN_IFLAG2_OFFSET,   v_w1c(32))
        self.iflag1     = (FLEXCAN_IFLAG1_OFFSET,   v_w1c(32))

        # The mailbox structure _could_ be defined with a bunch of bitfields,
        # and structures, but it makes re-using these mailbox registers for the
        # RxFIFO and normal MB modes easier if we just keep this to a simple
        # array. Each mailbox consists of 4 32-bit values.

        # To ensure that the alignment checks work properly the mailboxes must
        # be 8-bit aligned.
        self.mb         = (FLEXCAN_MB0_OFFSET,      v_bytearray(size=FLEXCAN_MAX_MB * FLEXCAN_MBx_SIZE))
        self.rximr      = (FLEXCAN_RXIMR0_OFFSET,   v_bytearray(size=FLEXCAN_MAX_MB * FLEXCAN_RXIMRx_SIZE))

    def reset(self, emu):
        """
        Reset handler for FlexCAN registers.  The mb and rximr fields need to
        manually be reset because they are not PeriphRegister objects and don't
        have init/reset functions.
        """
        super().reset(emu)

        self.mb.vsSetValue(b'\x00' * (FLEXCAN_MAX_MB * FLEXCAN_MBx_SIZE))
        self.rximr.vsSetValue(b'\x00' * (FLEXCAN_MAX_MB * FLEXCAN_RXIMRx_SIZE))


class FlexCAN(ExternalIOPeripheral):
    """
    Class to emulate the FlexCAN peripheral.  It emulates most of the FlexCAN
    behavior except for the following features:
    - Bus Off/On errors, transitions and states are not emulated.  Once the CAN
      bus is enabled through the MCR register the bus is considered up and
      never experiences any errors.
    - The MMIO range is not dynamically adjusted based on MCR[MAXMB]

    Supports sending and receiving pickled CanMsg objects over a TCP connection.
    The host and port to use are read from the "project.MPC5674.FlexCAN_?"
    configuration tree. The default configuration values are specified in the
    cm2350.MPC4674F.defconfig dict.

    The following code is an example of how to receive messages from the
    FlexCAN_A peripheral of the CM2350 emulator with the default host and port
    values:

        from cm2350.ppc_peripherals import ExternalIOClient
        client = ExternalIOClient(None, 10001)
        client.open()
        while True:
            data = client.recv()
            if data is None:
                break
            print(data)

    """
    def __init__(self, devname, emu, mmio_addr):
        """
        FlexCAN constructor.  Each processor has multiple FlexCAN peripherals
        so the devname parameter must be unique.
        """
        super().__init__(emu, devname, mmio_addr, 0x4000,
                regsetcls=FLEXCAN_REGISTERS,
                isrstatus=FLEXCAN_INT_STATUS_REGS,
                isrflags=FLEXCAN_INT_FLAG_REGS,
                isrevents=FLEXCAN_INT_EVENTS)
        # timer register
        self._timer = TimerRegister(16)

        self.mode = None
        self.speed = None

        # Queue used to hold messages to be placed in the Rx FIFO. This is sized
        # so if there is only 1 message it is placed in MB0, and it can hold 7
        # more messages.
        self._rx_fifo = []

        # values used to efficiently generate a list of filters and masks to
        # check incoming message IDs against. The filter dictionary has an entry
        # for each mailbox that consists of a tuple of (mask, filter).  If the
        # RxFIFO is enabled a key of None will be used and will have a list of
        # filters.  RTR frames have a different filter cache.
        self._rx_fifo_filters = {0: {0: [], 1: []}, 1: {0: [], 1: []}}
        self._rx_filters = {0: {}, 1: {}}
        self._rtr_filters = {0: {}, 1: {}}

        # TODO: should we simulate Rx/Tx errors and handle bus off transitions?

        # TODO: not sure it's worth the effort to implement this
        # invalid/reserved memory range behavior
        #self._valid_offsets = None

        # Update the state of the peripheral based on MCR writes
        self.registers.vsAddParseCallback('mcr', self.mcrUpdate)
        self.registers.vsAddParseCallback('ctrl', self.ctrlUpdate)
        self.registers.vsAddParseCallback('iflag1', self.iflag1Update)

        # Handle writes to the mailbox registers
        self.registers.mb.vsAddParseCallback('by_idx', self.mbUpdate)

    def _getPeriphReg(self, offset, size):
        """
        Customization of the standard ExternalIOPeripheral _getPeriphReg()
        function to allow custom handling of the TIMER register which is
        emulated using a TimerRegister object.

        The real FlexCAN peripheral changes how much of it's standard MMIO
        range is valid based on the value of the MCR[MAXMB] field, but this
        emulation doesn't go that far.
        """
        if offset == FLEXCAN_TIMER_OFFSET:
            return e_bits.buildbytes(self._timer.get(), 4, bigend=self.emu.getEndian())
        else:
            return super()._getPeriphReg(offset, size)

    def _setPeriphReg(self, offset, data):
        """
        Customization of the standard ExternalIOPeripheral _setPeriphReg()
        function to allow custom handling of the TIMER register which is
        emulated using a TimerRegister object.
        """
        if offset == FLEXCAN_TIMER_OFFSET:
            self._timer.set(e_bits.parsebytes(data, 0, 4, bigend=self.emu.getEndian()))
        else:
            super()._setPeriphReg(offset, data)

    def _resetFilters(self):
        """
        Utility to reset all receive filters back to their defaults (empty)
        """
        self._rx_fifo_filters[0][0] = []
        self._rx_fifo_filters[0][1] = []
        self._rx_fifo_filters[1][0] = []
        self._rx_fifo_filters[1][1] = []
        self._rx_filters[0] = {}
        self._rx_filters[1] = {}
        self._rtr_filters[0] = {}
        self._rtr_filters[1] = {}

    def softReset(self):
        """
        The FlexCAN peripheral implements a soft reset feature which clears
        most of the peripheral's state but does not change the enable/disable
        state in the MCR register, or the bus configuration in the CTRL
        register.
        """
        # Save the current MCR[MDIS] value
        mdis = self.registers.mcr.mdis

        # Reset registers that are not related to CAN bus configuration
        self.registers.mcr.reset(self.emu)
        self.registers.ecr.reset(self.emu)
        self.registers.esr.reset(self.emu)
        self.registers.imask1.reset(self.emu)
        self.registers.imask2.reset(self.emu)
        self.registers.iflag1.reset(self.emu)
        self.registers.iflag2.reset(self.emu)

        # also clear out any msgs in the Rx FIFO
        self._rx_fifo = []

        # And the filters
        self._resetFilters()

        # Restore the previous MCR[MDIS] value
        self.registers.mcr.mdis = mdis

        # Force the mode and speed to be updated
        self.updateMode()
        self.updateSpeed()

    def reset(self, emu):
        """
        Handle standard core reset and initialization
        """
        # clear the Rx FIFO
        self._rx_fifo = []

        # And the filters
        self._resetFilters()

        super().reset(emu)

        # After reset the default mode is DISABLE, even though the MCR[MDIS] bit
        # is 0 (the MCR[MDISACK] bit is 1)
        self.mode = FLEXCAN_MODE.DISABLE

        # Update the default speed
        self.updateSpeed()

    def getMBCode(self, mb):
        """
        Helper function to make it easier to get the code for a particular
        mailbox since it is done frequently.
        """
        idx = mb * FLEXCAN_MBx_SIZE
        return self.registers.mb[idx] & 0x0F

    def setMBCode(self, mb, code):
        """
        Helper function to make it easier to change the code for a particular
        mailbox since it is done frequently.
        """
        # TODO: Not sure if the Rx FIFO MB0 should be treated as having a code
        # or not
        #if self.registers.mcr.fen and mb == 0:
        #    return
        idx = mb * FLEXCAN_MBx_SIZE
        self.registers.mb[idx] = code

    def rxFifoRecv(self, msg):
        """
        Handle placing a received message into the RxFIFO
        """
        # Save the time that this message was received
        msg.timestamp = self._timer.get()

        if len(self._rx_fifo) == 0:
            # If the FIFO is empty, place the message directly into MB0 and
            # place a None placeholder item in the RxFIFO so the length of the
            # RxFIFO represents the number of messages that have been received
            # and not read.
            self.normalRx(0, msg)
            self._rx_fifo.append(None)
            return True

        elif len(self._rx_fifo) < FLEXCAN_RxFIFO_MAX_LEN:
            self._rx_fifo.append(msg)

            # According to "23.4.7 Rx FIFO" (MPC5674FRM.pdf page 853):
            #   "A warning interrupt is also generated when 5 frames are
            #   accumulated in the FIFO."
            #
            # However, from what I can determine it looks like the warning
            # interrupt should only be issued when the 6th message is received
            # It seems like this particular section is referring to the
            # messages not already stored in MB0 as being "in the fifo"? Or
            # perhaps it means if there were 5 messages in the RxFIFO before a
            # new message was queued?
            if len(self._rx_fifo) == FLEXCAN_RxFIFO_MAX_LEN:
                self.event('msg', 6, FLEXCAN_RxFIFO_WARNING_MASK)
            return True

        else:
            return False

    def processReceivedData(self, obj):
        """
        Take incoming CAN messages and place them into the correct CAN
        mailboxes according to the current mailbox configuration.
        """
        if self.registers.mcr.not_rdy:
            # the peripheral is not in a state that it can receive messages
            logger.debug('%s (%s): not ready to receive %r', self.devname, self.mode, obj)
            return

        last_match = None
        if self.registers.mcr.fen:
            # Check this message against the available RxFIFO filters
            for mask, filt in self._rx_fifo_filters[obj.rtr][obj.ide]:
                if (obj.arbid & mask) == filt:
                    if self.rxFifoRecv(obj):
                        return

                    # If the RxFIFO was full then search through the reset of
                    # the available mailboxes to see if one of the non-FIFO
                    # mailboxes match.
                    last_match = 0
                    break

        if obj.rtr:
            for mb, (mask, filt) in self._rtr_filters[obj.ide].items():
                if (obj.arbid & mask) == filt:
                    # Automatically transmit the remote frame
                    self.normalTx(mb)
                    return

        for mb, (mask, filt) in self._rx_filters[obj.ide].items():
            if (obj.arbid & mask) == filt:
                # Ensure this mailbox is empty
                code = self.getMBCode(mb)
                if code == FLEXCAN_CODE_RX_EMPTY:
                    # place the message into the mailbox
                    self.normalRx(mb, obj)
                    return
                else:
                    # Keep track of the last mailbox that matched but wasn't
                    # empty so we can mark it as overrun if no other matches
                    # are found.
                    last_match = mb

        # If we have reached here it means that no available mailboxes were
        # found. If any matching Rx mailboxes were
        if last_match is not None:
            if last_match == 0 and self.registers.mcr.fen:
                # If the RxFIFO is enabled and the last match was "MB0" then
                # signal an RxFIFO Overflow interrupt (MB7)
                self.event('msg', 7, FLEXCAN_RxFIFO_OVERFLOW_MASK)
            else:
                # mark the last matched mailbox as overrun
                self.setMBCode(last_match, FLEXCAN_CODE_RX_OVERRUN)

            logger.debug('%s (%s): overrun of mb %d, discarding msg %r', self.devname, self.mode, last_match, obj)
        else:
            logger.debug('%s (%s): discarding received msg %r', self.devname, self.mode, obj)

    def mcrUpdate(self, thing):
        """
        Process updates to the MCR register. Updates the current peripheral mode
        based on the new MCR value and current CTRL value.  If the peripheral is
        moving from disabled to enabled the mailbox filters are configured.
        """
        old_mode = self.mode
        self.updateMode()

        # If MCR[WRN_EN] is 0, ensure the TWRN and RWRN interrupt flags in the
        # CTRL register are also 0
        if self.registers.mcr.wrn_en == 0:
            self.registers.mcr.twrn_int = 0
            self.registers.mcr.rwrn_int = 0

        # If the peripheral used to be disabled, and is now NORMAL or LOOP_BACK,
        # check if any of the mailboxes need to be transmitted
        if self.mode in (FLEXCAN_MODE.NORMAL, FLEXCAN_MODE.LOOP_BACK) and old_mode in FLEXCAN_STOPPED:
            for mb in FLEXCAN_MB_RANGE:
                if self.getMBCode(mb) in (FLEXCAN_CODE_TX_ACTIVE, FLEXCAN_CODE_TX_RTR_SENDING):
                    idx = mb * FLEXCAN_MBx_SIZE
                    self.mbUpdate(thing=None, idx=mb_idx, size=1)

    def ctrlUpdate(self, thing):
        """
        Process updates to the CTRL register and updates the peripheral mode and
        configured bus speed. CTRL only enables the "Listen Only", "Loopback",
        or "Normal" modes so there is no need to handle updating the mailbox
        filters.
        """
        self.updateMode()
        self.updateSpeed()

    def iflag1Update(self, thing):
        """
        Process updates to the IFLAG1 register.  The IFLAG1 register is a v_w1c
        field so the only processing that needs to happen here is if RxFIFO mode
        is enabled, the Message Available interrupt is cleared (MB5), and there
        are messages current in the RxFIFO, then the next message is dequeued
        and placed in MB0.
        """
        # If MCR[NOT_RDY] == 0 then we should be doing normal message
        # processing, otherwise there is nothing to do now
        if self.registers.mcr.not_rdy:
            return

        # If Rx FIFO mode is enabled, the MB0 interrupt flag is cleared, and
        # there is a message available in the rx fifo, populate MB0
        if self.registers.mcr.fen and self._rx_fifo and \
                (self.registers.iflag1 & FLEXCAN_RxFIFO_MSG_AVAIL_MASK) == 0:
            if len(self._rx_fifo) == 1:
                # Discard the first RxFIFO element, it is a 'None' placeholder
                # representing the current message that is in the RxFIFO mailbox
                # (mailbox 0) already. Clearing the interrupt flag indicates
                # that the software is finished with the message
                self._rx_fifo.pop(0)

            elif len(self._rx_fifo) > 1:
                # Leave the placeholder None in index 0 of the RxFIFO and move
                # the next unread message into the RxFIFO mailbox (mailbox 0)
                msg = self._rx_fifo.pop(1)
                self.normalRx(0, msg)

    def mbUpdate(self, thing, idx, size, **kwargs):
        """
        Processes all write updates to the MB memory region. When the CODE
        offset is updated, the following actions will be performed depending on
        the new CODE value:
            TX_ACTIVE, RTR_SENDING : transmit message
            RX_EMPTY               : Update RX filters for the current MB
            TX_RTR                 : Update RTR filters for the current MB
            other                  : Remove MB from all filters
        """
        # If this was the mailbox offset that contains the code (byte 0 of 16),
        # check the code to identify what needs to be done
        if idx % FLEXCAN_MBx_SIZE == 0:
            # TODO: change // to >>
            mb = idx // FLEXCAN_MBx_SIZE
            code = self.getMBCode(mb)

            if code in (FLEXCAN_CODE_TX_ACTIVE, FLEXCAN_CODE_TX_RTR_SENDING):
                # The Rx and RTR filters and CODE after the msg is transmitted
                # will be updated in normalTx()
                self.normalTx(mb)

            elif code == FLEXCAN_CODE_RX_EMPTY:
                self.filterAddRxMB(mb)

            elif code == FLEXCAN_CODE_TX_RTR:
                self.filterAddRtrMB(mb)

            else:
                # This mailbox shouldn't be used for Rx or RTR filtering, so
                # check if it needs to be removed from the current set of
                # filters
                self.filterRemoveMB(mb)

    def normalRx(self, mb, msg):
        """
        Take a message object and do the following:
        - populate the specified mailbox with the received message
        - update the MBx CODE value
        - update the IFLAGx register that corresponds to the received msg
        - if the corresponding IMASKx bit is set queue an interrupt
        """
        idx = mb * FLEXCAN_MBx_SIZE

        # Check for Timer Sync
        if self.registers.ctrl.tsyn:
            if (self.registers.mcr.fen and mb == 8) or \
                    (self.registers.mcr.fen == 0 and mb == 0):
                self._timer.set(0)

        # Set the interrupt flag for this mailbox
        if mb == 0 and self.registers.mcr.fen:
            # Use the timestamp for when the message was received by the RxFIFO
            msg.into_mb(self.registers.mb.value, offset=idx, code=0, timestamp=msg.timestamp)
            self.event('msg', 5, FLEXCAN_RxFIFO_MSG_AVAIL_MASK)

        elif mb < 32:
            # Set the code to indicate that a message has been received (this
            # isn't done for the RxFIFO received messages)
            msg.into_mb(self.registers.mb.value, offset=idx, code=FLEXCAN_CODE_RX_FULL, timestamp=self._timer.get())
            self.event('msg', mb, FLEXCAN_IFLAG1_MASK[mb])

        else:
            # Set the code to indicate that a message has been received (this
            # isn't done for the RxFIFO received messages)
            msg.into_mb(self.registers.mb.value, offset=idx, code=FLEXCAN_CODE_RX_FULL, timestamp=self._timer.get())

            self.event('msg', mb, FLEXCAN_IFLAG2_MASK[mb])

    def normalTx(self, mb):
        """
        For the specified mailbox do the following if the peripherals mode is
        enabled (MCR[NOT_RDY] == 0):
        - Read a message out of the mailbox
        - if CODE == TX_ACTIVE and msg.rtr is NOT set:
            - set CODE = TX_INACTIVE
            - ensure this MB is not in any filter
        - if CODE == TX_ACTIVE and msg.rtr is set:
            - set CODE = RX_EMPTY
            - add this MB to the RX filter list so the RTR data can be received
              in the same mailbox
        - if CODE == TX_RTR_SENDING:
            - set CODE = TX_RTR
            - add this MB to the RTR filter list any future RTR requests seen on
              the bus that match this msg's ID will cause this message to
              automatically be sent.
        - if mode is NORMAL:
            - Update the IFLAGx register for this mailbox
            - if the corresponding IMASKx bit is set queue an interrupt
        - if mode is NORMAL or LOOPBACK and the self-reception disable flag is
          NOT set:
            - immediately receive the msg being transmitted
              by calling the processReceivedData() function.
        """
        if self.registers.mcr.not_rdy:
            # the peripheral is not in a state that it can transmit messages
            logger.debug('%s (%s): not ready to transmit %r', self.devname, self.mode, obj)
            return

        # create the object used for transmission
        idx = mb * FLEXCAN_MBx_SIZE
        msg = CanMsg.from_mb(self.registers.mb.value, offset=idx)
        code = self.getMBCode(mb)

        if code == FLEXCAN_CODE_TX_ACTIVE:
            # If the code for this mailbox is FLEXCAN_CODE_TX_ACTIVE return the
            # mailbox to FLEXCAN_CODE_TX_INACTIVE unless RTR is set in which
            # case this mailbox code needs to be changed to
            # FLEXCAN_CODE_RX_EMPTY to be ready to receive the remote frame
            if msg.rtr:
                self.setMBCode(mb, FLEXCAN_CODE_RX_EMPTY)

                # Manually add this mailbox to the Rx filter list since it will
                # not be in there now because the code was
                # FLEXCAN_CODE_TX_ACTIVE
                self.filterAddRxMB(mb)
            else:
                self.setMBCode(mb, FLEXCAN_CODE_TX_INACTIVE)

                # Ensure that this mailbox is not in any of the Rx or RTR
                # filters
                self.filterRemoveMB(mb)

        elif code == FLEXCAN_CODE_TX_RTR_SENDING:
            # Normally this is used in the real hardware when the peripheral is
            # responding to a remote frame request, but if the CPU sets it the
            # message should be sent as a normal message immediately and then
            # returned to FLEXCAN_CODE_TX_RTR.
            self.setMBCode(mb, FLEXCAN_CODE_TX_RTR)

            # Ensure this mailbox is in the RTR filter list
            self.filterAddRtrMB(mb)

        else:
            # This shouldn't happen?
            raise Exception('bad CODE 0x%x for MB %d(0x%x)' % (code, mb, idx))

        # Only transmit the message if in NORMAL mode
        if self.mode == FLEXCAN_MODE.NORMAL:
            # Write the value of the TIMER register into the timer field of the
            # mailbox. The timer field starts at offset 2 and is 2 bytes long.
            struct.pack_into('>H', self.registers.mb.value, idx+2, self._timer.get())
            self.transmit(msg)

            # Set the interrupt flag for this mailbox
            if mb < 32:
                mask_val = FLEXCAN_IFLAG1_MASK[mb]
            else:
                mask_val = FLEXCAN_IFLAG2_MASK[mb]

            self.event('msg', mb, mask_val)

        # If mode is NORMAL or LOOP-BACK, and the MCR[SRX_DIS] bit == 0
        # (self-reception of messages enabled), feed this message
        # directly into the receive queue
        if self.mode in (FLEXCAN_MODE.NORMAL, FLEXCAN_MODE.LOOP_BACK) and \
                self.registers.mcr.srx_dis == 0:
            # Bypass the primary emulator IO input and just process the message
            # now
            self.processReceivedData(msg)

    def getMaskForMB(self, mb):
        """
        Return the correct mask to use to compare an incoming msg ID to mailbox
        filter ID values. The FlexCAN peripheral has different filter modes
        depending on the value of the MCR[MBFEN] bit.  If set this enables
        individual filter mode, if not set then that enables legacy filter mode.

        In legacy filter mode the RXGMASK register is used for all mailboxes
        except for MB14 and MB15 which use the RX14MASK and RX15MASK registers.
        Unless the RxFIFO is enabled (MCR[FEN] == 1), then RX14MASK and RX15MASK
        are used as the mask for the filter values in entry 6 and 7 of the
        RxFIFO filter table.

        In individual filter mode the RXIMRx register values are used as the
        mask value for receive message filtering, and if the RxFIFO is enabled
        (MCR[FEN] == 1) then the RxFIFO filter table entries use the
        RXIMR0-RXIMR7 mask values.
        """
        # Return the correct filter based on the MCR[MBFEN] mode for the
        # specified mailbox
        if self.registers.mcr.mbfen:
            idx = mb * FLEXCAN_RXIMRx_SIZE
            return e_bits.parsebytes(self.registers.rximr, idx, FLEXCAN_RXIMRx_SIZE, bigend=self.emu.getEndian())
        # Use the legacy filter registers, Now it gets weird.
        if self.registers.mcr.fen == 0:
            # if MCR[FEN] is not set then all mailboxes use the global
            # filter (RXGMASK), except for MB14 (RX14MASK) and MB15
            # (RX15MASK).
            if mb == 14:
                return self.registers.rx14mask
            elif mb == 15:
                return self.registers.rx15mask
            else:
                return self.registers.rxgmask
        else:
            # If MCR[FEN] is set then the RxFIFO is active and the RX14MASK
            # applies to both MB14 and the 6th filter ID in the RxFIFO
            # filter ID list. RX15MASK applies to MB15 and the 7th ID in the
            # RxFIFO filter list.
            if mb in (6, 14):
                return self.registers.rx14mask
            elif mb in (7, 15):
                return self.registers.rx15mask
            else:
                return self.registers.rxgmask

    def filterAddRtrMB(self, mb):
        """
        Add a mailbox to the RTR filter list. The RTR filters are used to
        quickly identify the first mailbox that is configured to be able to
        reply to RTR requests. Mailbox matching is done using the mask and
        filter values configured for the corresponding mailboxes.
        """
        # If this is in the RTR list it shouldn't be in the Rx list
        if mb in self._rx_filters[0]:
            self._rx_filters[0].pop(mb)
            self._rx_filters[1].pop(mb)

        idx = mb * FLEXCAN_MBx_SIZE

        # Create different filters and masks for standard (11-bit) and extended
        # (29-bit) message IDs
        mask_val = self.getMaskForMB(mb)
        ext_mask = mask_val & FLEXCAN_ID_MASK

        # the message ID starts at offset 4 and is 4 bytes long
        ext_filt = self.registers.mb.parsebytes(idx+4, 4, bigend=self.emu.getEndian())
        ext_filt &= FLEXCAN_ID_MASK & ext_mask
        self._rtr_filters[1][mb] = ext_mask, ext_filt

        # If there are filter mask bits set in the lower 18 bits then this mask
        # is ext 29-bit specific and a std 11-bit filter should not be created
        if ext_filt & FLEXCAN_STD_ID_MASK == 0:
            # shift the extended mask and filter by 18 bits to get the correct
            # standard ID filters
            std_mask = ext_mask >> FLEXCAN_STD_ID_SHIFT
            std_filt = ext_filt >> FLEXCAN_STD_ID_SHIFT
            self._rtr_filters[0][mb] = std_mask, std_filt

    def filterAddRxMB(self, mb):
        """
        Add a mailbox to the Rx filter list. The Rx filters are used to quickly
        identify the first mailbox that is configured to be able to receive
        non-RTR CAN messages. Mailbox matching is done using the mask and filter
        values configured for the corresponding mailboxes in the filter list.
        """
        # If this is in the RTR list it shouldn't be in the Rx list
        if mb in self._rtr_filters[0]:
            self._rtr_filters[0].pop(mb)
            self._rtr_filters[1].pop(mb)

        # Convert mailbox ID to offset into a mailbox data offset
        idx = mb * FLEXCAN_MBx_SIZE

        # Create different filters and masks for standard (11-bit) and extended
        # (29-bit) message IDs
        mask_val = self.getMaskForMB(mb)
        ext_mask = mask_val & FLEXCAN_ID_MASK

        # the message ID starts at offset 4 and is 4 bytes long
        #   CODE | LEN | TIMESTAMP
        #   PRI | 11-bit | 29-bit
        #   DATA0    ...     DATA3
        #   DATA4    ...     DATA7
        ext_filt = self.registers.mb.parsebytes(idx+4, 4, bigend=self.emu.getEndian())
        # Don't forget to mask out the bits that we care about
        ext_filt &= FLEXCAN_ID_MASK & ext_mask
        self._rx_filters[1][mb] = ext_mask, ext_filt

        # If there are filter mask bits set in the lower 18 bits then this mask
        # is ext 29-bit specific and a std 11-bit filter should not be created
        if ext_filt & FLEXCAN_STD_ID_MASK == 0:
            # shift the extended mask and filter by 18 bits to get the correct
            # standard ID filters
            std_mask = ext_mask >> FLEXCAN_STD_ID_SHIFT
            std_filt = ext_filt >> FLEXCAN_STD_ID_SHIFT
            self._rx_filters[0][mb] = std_mask, std_filt

    def filterRemoveMB(self, mb):
        """
        Utility function that removes a mailbox from all Rx and RTR filters.
        """
        if mb in self._rx_filters[0]:
            self._rx_filters[0].pop(mb)
        if mb in self._rx_filters[1]:
            self._rx_filters[1].pop(mb)
        if mb in self._rtr_filters[0]:
            self._rtr_filters[0].pop(mb)
        if mb in self._rtr_filters[1]:
            self._rtr_filters[1].pop(mb)

    def filterUpdate(self):
        """
        Utility function that will go through each mailbox and re-create the
        Rx and RTR filters with the currently configured mask and filter ID
        values.  If RxFIFO mode is enabled (MCR[FEN] == 1) then the peripheral
        offsets that normally correspond to MB6 and MB7 will be used as a set of
        filter values that correspond to messages that can be received in the
        RxFIFO.
        """
        # The filters will be re-generated in this function, reset them to empty
        # first
        self._resetFilters()

        if self.registers.mcr.fen:
            # RxFIFO is enabled, use the values in MB6-MB7 as the filter list,
            # but the filter list has 4 different modes.  Also unlike the normal
            # mailbox filters some of the RxFIFO filter modes have the RTR and
            # IDE bits embedded in the filter ID

            # TODO: not sure if the mask does not include the RTR and IDE bits
            # if applies to all incoming messages, not just ones that match the
            # specified RTR and IDE values.  My current assumption is that the
            # filter option with 4 8-bit values apply to all incoming messages,
            # not just "STD or non-RTR" messages

            mode = self.registers.mcr.idam

            # Collect all of the masks and shifts to turn the RxFIFO filter
            # values into something that can be compared against incoming
            # messages
            rxfifo_mask_shift_list = list(zip(
                    FLEXCAN_RxFIFO_FILTER_REM_MASKS[mode],
                    FLEXCAN_RxFIFO_FILTER_REM_SHIFTS[mode],
                    FLEXCAN_RxFIFO_FILTER_EXT_MASKS[mode],
                    FLEXCAN_RxFIFO_FILTER_EXT_SHIFTS[mode],
                    FLEXCAN_RxFIFO_FILTER_ID_MASKS[mode],
                    FLEXCAN_RxFIFO_FILTER_ID_SHIFTS[mode]))

            # There are 8 filters stored in the MB memory in MB6 and MB7
            filters = struct.unpack_from('>8I', self.registers.mb.value, offset=6*FLEXCAN_MBx_SIZE)
            for mb in range(8):
                filt_val = filters[mb]
                mask_val = self.getMaskForMB(mb)

                for rem_mask, rem_shift, ext_mask, ext_shift, id_mask, id_shift_vals in rxfifo_mask_shift_list:
                    # If the filter mask doesn't overlap with any of the remote
                    # frame mask bit(s) then this filter value applies to both
                    # data and remote frames
                    if rem_mask is not None and rem_mask & mask_val != 0:
                        rtr = (filt_val & rem_mask) >> rem_shift
                    else:
                        rtr = None

                    # If the filter mask doesn't overlap with any of the
                    # extended ID mask bit(s) then this filter value applies to
                    # both standard and extended frames
                    if rem_mask is not None and ext_mask & mask_val != 0:
                        ide = (filt_val & ext_mask) >> ext_shift
                    else:
                        ide = None

                    if ide is None or ide == 0:
                        # 11-bit (std)
                        id_shift_oper, id_shift = id_shift_vals[0]
                        mask = id_shift_oper(mask_val & id_mask[0], id_shift)
                        filt = id_shift_oper(filt_val & id_mask[0], id_shift)

                        if rtr is None or rtr == 0:
                            self._rx_fifo_filters[0][0].append((mask, filt))
                        if rtr is None or rtr == 1:
                            self._rx_fifo_filters[1][0].append((mask, filt))

                    if ide is None or ide == 1:
                        # 29-bit (ext)
                        id_shift_oper, id_shift = id_shift_vals[1]
                        mask = id_shift_oper(mask_val & id_mask[1], id_shift)
                        filt = id_shift_oper(filt_val & id_mask[1], id_shift)

                        if rtr is None or rtr == 0:
                            self._rx_fifo_filters[0][1].append((mask, filt))
                        if rtr is None or rtr == 1:
                            self._rx_fifo_filters[1][1].append((mask, filt))

            # Now add normal message filters starting with MB8
            start_mb = 8
        else:
            # RxFIFO is not enabled, do normal Rx message filtering starting at
            # MB0
            start_mb = 0

        # Calculate the normal filters
        mb_idx_range = range(start_mb*FLEXCAN_MBx_SIZE, FLEXCAN_MAX_MB*FLEXCAN_MBx_SIZE, FLEXCAN_MBx_SIZE)
        mask_idx_range = range(0, FLEXCAN_MAX_MB)
        for mb_idx, mask_idx in zip(mb_idx_range, mask_idx_range):
            # the mask index is the same as the mailbox ID
            code = self.getMBCode(mask_idx)
            if code in RX_CHECK_FILTER:
                self.filterAddRxMB(mask_idx)
            elif code == FLEXCAN_CODE_TX_RTR:
                self.filterAddRtrMB(mask_idx)

    def updateMode(self):
        """
        Update the CAN peripheral mode and set the appropriate MCR status bits
        to indicate the current mode.
        """
        # First check if the soft reset bit is set
        if self.registers.mcr.soft_rst:
            self.softReset()
            self.registers.mcr.soft_rst = 0

        # The MCR[NOT_RDY, MDISACK] bits should be set when in either the
        # DISABLE or FREEZE modes
        if self.registers.mcr.mdis:
            mode = FLEXCAN_MODE.DISABLE
            self.registers.mcr.vsOverrideValue('mdisack', 1)
            self.registers.mcr.vsOverrideValue('not_rdy', 1)
            self.registers.mcr.vsOverrideValue('frz_ack', 0)

            # Stop the timer
            self._timer.stop()

        elif self.registers.mcr.halt and self.registers.mcr.frz:
            mode = FLEXCAN_MODE.FREEZE
            self.registers.mcr.vsOverrideValue('mdisack', 0)
            self.registers.mcr.vsOverrideValue('not_rdy', 1)
            self.registers.mcr.vsOverrideValue('frz_ack', 1)

            # Stop the timer
            self._timer.stop()

        else:
            self.registers.mcr.vsOverrideValue('mdisack', 0)
            self.registers.mcr.vsOverrideValue('not_rdy', 0)
            self.registers.mcr.vsOverrideValue('frz_ack', 0)

            # If not in the DISABLE or FREEZE state then use the values in the
            # CTRL register to determine the current mode.
            if self.registers.ctrl.lom:
                mode = FLEXCAN_MODE.LISTEN_ONLY
            elif self.registers.ctrl.lpb:
                mode = FLEXCAN_MODE.LOOP_BACK
            else:
                mode = FLEXCAN_MODE.NORMAL

            # If the old mode was not running, but the new mode is, Generate a
            # set of filters and masks that are easier to test received messages
            # against than doing the calculations each time a message is
            # received
            if self.mode in FLEXCAN_STOPPED:
                self.filterUpdate()

                # The timer (prescaler) should be running
                self._timer.start()

        if self.mode != mode:
            self.mode = mode
            logger.debug('%s: changing to mode %s', self.devname, self.mode.name)

    def updateSpeed(self):
        """
        Update the can bus speed based on the CTRL register and the currently
        selected clock source
        """
        # If disabled or frozen, don't bother doing this calculation
        if self.mode in (FLEXCAN_MODE.DISABLE, FLEXCAN_MODE.FREEZE):
            self.speed = None

        # CAN bus clocks are typically calculated by breaking a clock into a
        # "time quantum", and the specifying the number of "time quantums"
        # (which I will label as "tq" because "time quantum" sounds stupid) that
        # make up the following portions of a single CAN bit:
        # - SYNC: 1 tq
        # - PROPSEG (propagation time): 0 to 7 tq + 1
        # - SEGMENT1: 0 to 7 tq + 1 tq
        # - SEGMENT2: 1 to 7 tq + 1 tq
        #
        # PROPSEG + SEGMENT1 must be between 4 and 16 tq
        # SEGMENT2 must be between 2 and 8 tq
        #
        # The value of the bit is then sampled once (or 3 times) between
        # segments 1 and 2.  If three samples is enabled the third sample
        # happens at the break between segment 1 and 2.
        #
        # There is also a correlation between the number of mailboxes that are
        # selected and the configured tq per bit, but we don't have to worry
        # about that.

        ctrl = self.registers.ctrl

        # source clock = CPI source clock / (PRESDIV + 1)
        if ctrl.clk_src:
            sclk = self.emu.siu.f_periph() / (ctrl.presdiv + 1)
        else:
            sclk = self.emu.fmpll.f_extal() / (ctrl.presdiv + 1)

        # SYNC (1) + PROPSEG (0-7 + 1) + SEG1 (0-7 + 1) + SEG2 (0-7 + 1)
        tq_per_bit = ctrl.propseg + ctrl.pseg1 + ctrl.pseg2 + 4

        self.speed = sclk / tq_per_bit

        # Set the timer register to run at the bus bit clock
        self._timer.setFreq(self.emu, self.speed)
