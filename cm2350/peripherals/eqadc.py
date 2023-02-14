import enum
from collections import namedtuple

import envi.bits as e_bits
import envi.const as e_const

from ..ppc_vstructs import *
from ..ppc_peripherals import *
from ..intc_exc import INTC_EVENT

import logging
logger = logging.getLogger(__name__)

__all__  = [
    'eQADC',
]


EQADC_MCR_OFFSET     = 0x0000
EQADC_ETDFR_OFFSET   = 0x000C
EQADC_CFPR_OFFSET    = 0x0010
EQADC_RFPR_OFFSET    = 0x0030
EQADC_CFCR_OFFSET    = 0x0050
EQADC_IDCR_OFFSET    = 0x0060
EQADC_FISR_OFFSET    = 0x0070
EQADC_CFTCR_OFFSET   = 0x0090
EQADC_CFSSR_OFFSET   = 0x00A0
EQADC_CFSR_OFFSET    = 0x00AC
EQADC_REDLCCR_OFFSET = 0x00D0
EQADC_CF0Rw_OFFSET   = 0x0100
EQADC_CF0ERw_OFFSET  = 0x0110
EQADC_CF1Rw_OFFSET   = 0x0140
EQADC_CF2Rw_OFFSET   = 0x0180
EQADC_CF3Rw_OFFSET   = 0x01C0
EQADC_CF4Rw_OFFSET   = 0x0200
EQADC_CF5Rw_OFFSET   = 0x0240
EQADC_RF0Rw_OFFSET   = 0x0300
EQADC_RF1Rw_OFFSET   = 0x0340
EQADC_RF2Rw_OFFSET   = 0x0380
EQADC_RF3Rw_OFFSET   = 0x03C0
EQADC_RF4Rw_OFFSET   = 0x0400
EQADC_RF5Rw_OFFSET   = 0x0440

EQADC_NUM_CBUFFERS   = 6
EQADC_NUM_ADCS       = 2

# There are 4 CFxRw (w = 0-3) registers for every CBuffer
EQADC_NUM_FxREGS    = 4

EQADC_CFPR_RANGE    = range(EQADC_CFPR_OFFSET, EQADC_CFPR_OFFSET+(EQADC_NUM_CBUFFERS*4), 4)
EQADC_RFPR_RANGE    = range(EQADC_RFPR_OFFSET, EQADC_RFPR_OFFSET+(EQADC_NUM_CBUFFERS*4), 4)

EQADC_CFIFO0_LEN    = 8
EQADC_CFIFO_LEN     = 4
EQADC_RFIFO_LEN     = 4

EQADC_CMD_SIZE      = 4
EQADC_RESULT_SIZE   = 4

EQADC_CFxRw_RANGE   = \
    list(range(EQADC_CF0Rw_OFFSET, EQADC_CF0Rw_OFFSET+(EQADC_CFIFO0_LEN*4), 4)) + \
    list(range(EQADC_CF1Rw_OFFSET, EQADC_CF1Rw_OFFSET+(EQADC_CFIFO_LEN*4), 4)) + \
    list(range(EQADC_CF2Rw_OFFSET, EQADC_CF2Rw_OFFSET+(EQADC_CFIFO_LEN*4), 4)) + \
    list(range(EQADC_CF3Rw_OFFSET, EQADC_CF3Rw_OFFSET+(EQADC_CFIFO_LEN*4), 4)) + \
    list(range(EQADC_CF4Rw_OFFSET, EQADC_CF4Rw_OFFSET+(EQADC_CFIFO_LEN*4), 4)) + \
    list(range(EQADC_CF5Rw_OFFSET, EQADC_CF5Rw_OFFSET+(EQADC_CFIFO_LEN*4), 4))

EQADC_RFxRw_RANGE   = \
    list(range(EQADC_RF0Rw_OFFSET, EQADC_RF0Rw_OFFSET+(EQADC_RFIFO_LEN*4), 4)) + \
    list(range(EQADC_RF1Rw_OFFSET, EQADC_RF1Rw_OFFSET+(EQADC_RFIFO_LEN*4), 4)) + \
    list(range(EQADC_RF2Rw_OFFSET, EQADC_RF2Rw_OFFSET+(EQADC_RFIFO_LEN*4), 4)) + \
    list(range(EQADC_RF3Rw_OFFSET, EQADC_RF3Rw_OFFSET+(EQADC_RFIFO_LEN*4), 4)) + \
    list(range(EQADC_RF4Rw_OFFSET, EQADC_RF4Rw_OFFSET+(EQADC_RFIFO_LEN*4), 4)) + \
    list(range(EQADC_RF5Rw_OFFSET, EQADC_RF5Rw_OFFSET+(EQADC_RFIFO_LEN*4), 4))

# Constants used in calculating which CBuffer and FIFO entry a CFIFO or RFIFO
# read/write is for
EQADC_xFIFO_BYTES   = 4
EQADC_xFIFO_SIZE    = 0x40

EQADC_CFIFOx_OFFSETS  = [
    EQADC_CF0Rw_OFFSET,
    EQADC_CF1Rw_OFFSET,
    EQADC_CF2Rw_OFFSET,
    EQADC_CF3Rw_OFFSET,
    EQADC_CF4Rw_OFFSET,
    EQADC_CF5Rw_OFFSET,
]

EQADC_RFIFOx_OFFSETS  = [
    EQADC_RF0Rw_OFFSET,
    EQADC_RF1Rw_OFFSET,
    EQADC_RF2Rw_OFFSET,
    EQADC_RF3Rw_OFFSET,
    EQADC_RF4Rw_OFFSET,
    EQADC_RF5Rw_OFFSET,
]

# Some of the analog channels have fixed meanings
# VRH is assumed to be 5V and VRL is assumed to be 0V
EQADC_NUM_ANALOG_CHAN = 256
EQADC_ANALOG_CHAN_VRH = 40
EQADC_ANALOG_CHAN_VRL = 41
EQADC_ANALOG_CHAN_50  = 42
EQADC_ANALOG_CHAN_75  = 43
EQADC_ANALOG_CHAN_25  = 44

# the EQADC conversions are 12, 10 or 8 bits:
EQADC_RESULT_MAX = {
    0: 0xFFF,
    1: 0x7FF,
    2: 0x3FF,
}

# EQADC MODES
# The upper bit is the single/continuous scan flag
# The lower 3 bits indicate the trigger mode
class EQADC_MODE(enum.IntEnum):
    DISABLE                 = 0b0000
    SINGLE_SW_TRIGGER       = 0b0001
    SINGLE_LOW_LEVEL        = 0b0010
    SINGLE_HIGH_LEVEL       = 0b0011
    SINGLE_FALLING_EDGE     = 0b0100
    SINGLE_RISING_EDGE      = 0b0101
    SINGLE_ANY_EDGE         = 0b0110
    CONTINUOUS_SW_TRIGGER   = 0b1001
    CONTINUOUS_LOW_LEVEL    = 0b1010
    CONTINUOUS_HIGH_LEVEL   = 0b1011
    CONTINUOUS_FALLING_EDGE = 0b1100
    CONTINUOUS_RISING_EDGE  = 0b1101
    CONTINUOUS_ANY_EDGE     = 0b1110

EQADC_SINGLE_SCAN_TRIGGER_MODES = (
    EQADC_MODE.SINGLE_LOW_LEVEL,
    EQADC_MODE.SINGLE_HIGH_LEVEL,
    EQADC_MODE.SINGLE_FALLING_EDGE,
    EQADC_MODE.SINGLE_RISING_EDGE,
    EQADC_MODE.SINGLE_ANY_EDGE,
)

EQADC_CONTINUOUS_SCAN_TRIGGER_MODES = (
    EQADC_MODE.CONTINUOUS_SW_TRIGGER,
    EQADC_MODE.CONTINUOUS_LOW_LEVEL,
    EQADC_MODE.CONTINUOUS_HIGH_LEVEL,
    EQADC_MODE.CONTINUOUS_FALLING_EDGE,
    EQADC_MODE.CONTINUOUS_RISING_EDGE,
    EQADC_MODE.CONTINUOUS_ANY_EDGE,
)

# Based on the configured mode of each channel there is a 2-bit CFIFO status
# field in the CFSR register
class EQADC_CFS_MODE(enum.IntEnum):
    IDLE                    = 0b00
    #RESERVED               = 0b01
    WAITING_FOR_TRIGGER     = 0b10
    TRIGGERED               = 0b11

# CFS mode fields
EQADC_CFS_FIELDS = ('cfs0', 'cfs1', 'cfs2', 'cfs3', 'cfs4', 'cfs5')

# Idle vs waiting for triggered modes
EQADC_CFS_IDLE_MODES = (EQADC_MODE.DISABLE, EQADC_MODE.SINGLE_SW_TRIGGER,
        EQADC_MODE.SINGLE_LOW_LEVEL, EQADC_MODE.SINGLE_HIGH_LEVEL,
        EQADC_MODE.SINGLE_FALLING_EDGE, EQADC_MODE.SINGLE_RISING_EDGE,
        EQADC_MODE.SINGLE_ANY_EDGE)

EQADC_CFS_WAIT_FOR_TRIGGER_MODES = (EQADC_MODE.CONTINUOUS_SW_TRIGGER,
        EQADC_MODE.CONTINUOUS_LOW_LEVEL, EQADC_MODE.CONTINUOUS_HIGH_LEVEL,
        EQADC_MODE.CONTINUOUS_FALLING_EDGE, EQADC_MODE.CONTINUOUS_RISING_EDGE,
        EQADC_MODE.CONTINUOUS_ANY_EDGE)

# Mapping of interrupt types based on the supporting EQADC peripherals and the
# corresponding IDCRx FISRx field names. Most of the interrupt types have
# different sources depending on which CBuffer the interrupt comes from, but the
# TORF (Trigger Overrun), RFOF (Result FIFO Overflow), and CFUF (Command FIFO
# Underflow) for all CBuffers share the same interrupt source.
EQADC_INT_EVENTS = {
    'eQADC_A': (
        {
            'ncf':  INTC_EVENT.EQADC_A_FISR0_NCF,
            'torf': INTC_EVENT.EQADC_A_TORF,
            'pf':   INTC_EVENT.EQADC_A_FISR0_PF,
            'eoqf': INTC_EVENT.EQADC_A_FISR0_EOQF,
            'cfuf': INTC_EVENT.EQADC_A_CFUF,
            'cfff': INTC_EVENT.EQADC_A_FISR0_CFFF,
            'rfof': INTC_EVENT.EQADC_A_RFOF,
            'rfdf': INTC_EVENT.EQADC_A_FISR0_RFDF,
        },
        {
            'ncf':  INTC_EVENT.EQADC_A_FISR1_NCF,
            'torf': INTC_EVENT.EQADC_A_TORF,
            'pf':   INTC_EVENT.EQADC_A_FISR1_PF,
            'eoqf': INTC_EVENT.EQADC_A_FISR1_EOQF,
            'cfuf': INTC_EVENT.EQADC_A_CFUF,
            'cfff': INTC_EVENT.EQADC_A_FISR1_CFFF,
            'rfof': INTC_EVENT.EQADC_A_RFOF,
            'rfdf': INTC_EVENT.EQADC_A_FISR1_RFDF,
        },
        {
            'ncf':  INTC_EVENT.EQADC_A_FISR2_NCF,
            'torf': INTC_EVENT.EQADC_A_TORF,
            'pf':   INTC_EVENT.EQADC_A_FISR2_PF,
            'eoqf': INTC_EVENT.EQADC_A_FISR2_EOQF,
            'cfuf': INTC_EVENT.EQADC_A_CFUF,
            'cfff': INTC_EVENT.EQADC_A_FISR2_CFFF,
            'rfof': INTC_EVENT.EQADC_A_RFOF,
            'rfdf': INTC_EVENT.EQADC_A_FISR2_RFDF,
        },
        {
            'ncf':  INTC_EVENT.EQADC_A_FISR3_NCF,
            'torf': INTC_EVENT.EQADC_A_TORF,
            'pf':   INTC_EVENT.EQADC_A_FISR3_PF,
            'eoqf': INTC_EVENT.EQADC_A_FISR3_EOQF,
            'cfuf': INTC_EVENT.EQADC_A_CFUF,
            'cfff': INTC_EVENT.EQADC_A_FISR3_CFFF,
            'rfof': INTC_EVENT.EQADC_A_RFOF,
            'rfdf': INTC_EVENT.EQADC_A_FISR3_RFDF,
        },
        {
            'ncf':  INTC_EVENT.EQADC_A_FISR4_NCF,
            'torf': INTC_EVENT.EQADC_A_TORF,
            'pf':   INTC_EVENT.EQADC_A_FISR4_PF,
            'eoqf': INTC_EVENT.EQADC_A_FISR4_EOQF,
            'cfuf': INTC_EVENT.EQADC_A_CFUF,
            'cfff': INTC_EVENT.EQADC_A_FISR4_CFFF,
            'rfof': INTC_EVENT.EQADC_A_RFOF,
            'rfdf': INTC_EVENT.EQADC_A_FISR4_RFDF,
        },
        {
            'ncf':  INTC_EVENT.EQADC_A_FISR5_NCF,
            'torf': INTC_EVENT.EQADC_A_TORF,
            'pf':   INTC_EVENT.EQADC_A_FISR5_PF,
            'eoqf': INTC_EVENT.EQADC_A_FISR5_EOQF,
            'cfuf': INTC_EVENT.EQADC_A_CFUF,
            'cfff': INTC_EVENT.EQADC_A_FISR5_CFFF,
            'rfof': INTC_EVENT.EQADC_A_RFOF,
            'rfdf': INTC_EVENT.EQADC_A_FISR5_RFDF,
        },
    ),
    'eQADC_B': (
        {
            'ncf':  INTC_EVENT.EQADC_B_FISR0_NCF,
            'torf': INTC_EVENT.EQADC_B_TORF,
            'pf':   INTC_EVENT.EQADC_B_FISR0_PF,
            'eoqf': INTC_EVENT.EQADC_B_FISR0_EOQF,
            'cfuf': INTC_EVENT.EQADC_B_CFUF,
            'cfff': INTC_EVENT.EQADC_B_FISR0_CFFF,
            'rfof': INTC_EVENT.EQADC_B_RFOF,
            'rfdf': INTC_EVENT.EQADC_B_FISR0_RFDF,
        },
        {
            'ncf':  INTC_EVENT.EQADC_B_FISR1_NCF,
            'torf': INTC_EVENT.EQADC_B_TORF,
            'pf':   INTC_EVENT.EQADC_B_FISR1_PF,
            'eoqf': INTC_EVENT.EQADC_B_FISR1_EOQF,
            'cfuf': INTC_EVENT.EQADC_B_CFUF,
            'cfff': INTC_EVENT.EQADC_B_FISR1_CFFF,
            'rfof': INTC_EVENT.EQADC_B_RFOF,
            'rfdf': INTC_EVENT.EQADC_B_FISR1_RFDF,
        },
        {
            'ncf':  INTC_EVENT.EQADC_B_FISR2_NCF,
            'torf': INTC_EVENT.EQADC_B_TORF,
            'pf':   INTC_EVENT.EQADC_B_FISR2_PF,
            'eoqf': INTC_EVENT.EQADC_B_FISR2_EOQF,
            'cfuf': INTC_EVENT.EQADC_B_CFUF,
            'cfff': INTC_EVENT.EQADC_B_FISR2_CFFF,
            'rfof': INTC_EVENT.EQADC_B_RFOF,
            'rfdf': INTC_EVENT.EQADC_B_FISR2_RFDF,
        },
        {
            'ncf':  INTC_EVENT.EQADC_B_FISR3_NCF,
            'torf': INTC_EVENT.EQADC_B_TORF,
            'pf':   INTC_EVENT.EQADC_B_FISR3_PF,
            'eoqf': INTC_EVENT.EQADC_B_FISR3_EOQF,
            'cfuf': INTC_EVENT.EQADC_B_CFUF,
            'cfff': INTC_EVENT.EQADC_B_FISR3_CFFF,
            'rfof': INTC_EVENT.EQADC_B_RFOF,
            'rfdf': INTC_EVENT.EQADC_B_FISR3_RFDF,
        },
        {
            'ncf':  INTC_EVENT.EQADC_B_FISR4_NCF,
            'torf': INTC_EVENT.EQADC_B_TORF,
            'pf':   INTC_EVENT.EQADC_B_FISR4_PF,
            'eoqf': INTC_EVENT.EQADC_B_FISR4_EOQF,
            'cfuf': INTC_EVENT.EQADC_B_CFUF,
            'cfff': INTC_EVENT.EQADC_B_FISR4_CFFF,
            'rfof': INTC_EVENT.EQADC_B_RFOF,
            'rfdf': INTC_EVENT.EQADC_B_FISR4_RFDF,
        },
        {
            'ncf':  INTC_EVENT.EQADC_B_FISR5_NCF,
            'torf': INTC_EVENT.EQADC_B_TORF,
            'pf':   INTC_EVENT.EQADC_B_FISR5_PF,
            'eoqf': INTC_EVENT.EQADC_B_FISR5_EOQF,
            'cfuf': INTC_EVENT.EQADC_B_CFUF,
            'cfff': INTC_EVENT.EQADC_B_FISR5_CFFF,
            'rfof': INTC_EVENT.EQADC_B_RFOF,
            'rfdf': INTC_EVENT.EQADC_B_FISR5_RFDF,
        },
    ),
}


class ADC_REGS(enum.IntEnum):
    CMD     = 0x00
    CR      = 0x01
    TSCR    = 0x02
    TBCR    = 0x03
    GR      = 0x04
    OR      = 0x05
    ALTCMD1 = 0x08
    ALTCMD2 = 0x09
    ALTCMD3 = 0x0A
    ALTCMD4 = 0x0B
    ALTCMD5 = 0x0C
    ALTCMD6 = 0x0D
    ALTCMD7 = 0x0E
    ALTCMD8 = 0x0F
    ACR1    = 0x30
    AGR1    = 0x31
    AOR1    = 0x32
    ACR2    = 0x34
    AGR2    = 0x35
    AOR2    = 0x36
    ACR3    = 0x38
    ACR4    = 0x3C
    ACR5    = 0x40
    ACR6    = 0x44
    ACR7    = 0x48
    ACR8    = 0x4C
    PUDCR0  = 0x70
    PUDCR1  = 0x71
    PUDCR2  = 0x72
    PUDCR3  = 0x73
    PUDCR4  = 0x74
    PUDCR5  = 0x75
    PUDCR6  = 0x76
    PUDCR7  = 0x77

ADC_REGS_ALTCNV_RANGE = range(ADC_REGS.ALTCMD1, ADC_REGS.ALTCMD8+1)

# Convert command to configuration register offset mapping
ADC_CR_MAP = {
    ADC_REGS.CMD:     ADC_REGS.CR,
    ADC_REGS.ALTCMD1: ADC_REGS.ACR1,
    ADC_REGS.ALTCMD2: ADC_REGS.ACR2,
    ADC_REGS.ALTCMD3: ADC_REGS.ACR3,
    ADC_REGS.ALTCMD4: ADC_REGS.ACR4,
    ADC_REGS.ALTCMD5: ADC_REGS.ACR5,
    ADC_REGS.ALTCMD6: ADC_REGS.ACR6,
    ADC_REGS.ALTCMD7: ADC_REGS.ACR7,
    ADC_REGS.ALTCMD8: ADC_REGS.ACR8,
}


class ADC:
    def __init__(self, eqadc, devname):
        # We don't want to register this module directly, it'll be reset and
        # initialized by the EQADC class
        self.devname = devname
        self.eqadc = eqadc

        self.registers = {}
        for reg in ADC_REGS:
            self.registers[reg.value] = v_bits(16)

    def reset(self, emu):
        for reg in ADC_REGS:
            self._get(reg).vsSetValue(0)

    def _get(self, offset):
        reg = ADC_REGS(offset)
        return self.registers[reg.value]

    def __getitem__(self, offset):
        return self._get(offset).vsGetValue()

    def __setitem__(self, offset, value):
        self._get(offset).vsSetValue(value)

    def read(self, offset):
        return self._get(offset).vsEmit()

    def write(self, offset, data):
        return self._get(offset).vsParse(data)

    def config(self, cmd_offset=ADC_REGS.CMD):
        config_reg = ADC_CR_MAP[cmd_offset]
        config = self._get(config_reg)
        return config

    def convert(self, adc_chan, cmd_offset=ADC_REGS.CMD):
        config = self.config(cmd_offset)

        # If the result is inhibited just return None
        if not config & 0x8000:
            return None

        vrh = self.eqadc.channels[EQADC_ANALOG_CHAN_VRH]
        vrl = self.eqadc.channels[EQADC_ANALOG_CHAN_VRL]
        value = self.eqadc.channels[adc_chan]

        if cmd_offset in ADC_REGS_ALTCNV_RANGE:
            ressel = (config & 0x00C0) >> 6
            vrh_max = EQADC_RESULT_MAX[ressel]

            # TODO: the GAIN and OFFSET values are currently ignored for ACR1
            # and ACR2 configs, and the PRE_GAIN value is not yet used from the
            # ACRx config registers

        else:
            # The standard conversion command does a simple 1x, 12-bit
            # conversion
            vrh_max = EQADC_RESULT_MAX[0]

        # limit the min and max of the incoming value based on VRH and VRL
        if value > vrh:
            value = vrh
        elif value < vrl:
            value = vrl

        result = int(((value - vrl) / (vrh - vrl)) * vrh_max)

        if cmd_offset in ADC_REGS_ALTCNV_RANGE:
            # See if the result should be sign extended to 14-bits or not
            if config & 0x0200 and result & e_bits.bsign_bits[12]:
                result |= 0x3000

        logger.debug('%s: converting %d: %f (max/min: %f/%f) = 0x%x (max: 0x%x)', self.devname, adc_chan, value, vrh, vrl, result, vrh_max)

        # Convert to bytes and return the result
        return e_bits.buildbytes(result, 2, bigend=self.eqadc.emu.getEndian())


# If lowest "configuration" field is 0 then this ADC Conversion Command uses the
# standard ADC Configuration Register.  Otherwise an alternate configuration is
# use.
ADC_CMD_CONVERT = namedtuple('ADC_CMD_CONVERT',
        ['eoq', 'pause', 'rep', 'bn', 'cal', 'tag', 'lst', 'tsr', 'fmt', 'chan', 'offset'])
ADC_CMD_WRITE = namedtuple('ADC_CMD_WRITE',
        ['eoq', 'pause', 'rep', 'bn', 'value', 'offset'])
ADC_CMD_READ = namedtuple('ADC_CMD_READ',
        ['eoq', 'pause', 'rep', 'bn', 'tag', 'offset'])


def parseCommand(data, endian=e_const.ENDIAN_MSB):
    """
    Takes the 32-bit value from the CFIFO, determines what type of ADC command
    this is and parses it.
    """
    cmd = e_bits.parsebytes(data, 0, EQADC_CMD_SIZE, bigend=endian)

    # These values are used by all commands
    eoq = (cmd & 0x80000000) >> 31
    pause = (cmd & 0x40000000) >> 30
    if pause:
        raise NotImplementedError('PAUSE not handled in commands: %s' % data.hex())
    rep = (cmd & 0x20000000) >> 29
    if rep:
        raise NotImplementedError('REP not handled in commands: %s' % data.hex())
    bn = (cmd & 0x02000000) >> 25

    # This field is the CAL flag for conversion commands, and the R/W flag for
    # read/write commands
    cal = (cmd & 0x01000000) >> 24

    # If the lowest byte is 0x0 or 0x8-0xF then this is a conversion command
    # All other commands are read or write commands
    offset = cmd & 0x000000FF
    if offset == 0 or offset in ADC_REGS_ALTCNV_RANGE:
        tag = (cmd & 0x00F00000) >> 20
        lst = (cmd & 0x000C0000) >> 18
        tsr = (cmd & 0x00020000) >> 17
        fmt = (cmd & 0x00010000) >> 16
        chan = (cmd & 0x0000FF00) >> 8
        return ADC_CMD_CONVERT(eoq, pause, rep, bn, cal, tag, lst, tsr, fmt, chan, offset)
    elif cal == 0:
        # when the R/W bit is 0 this is a write command
        value = (cmd & 0x00FFFF00) >> 8
        return ADC_CMD_WRITE(eoq, pause, rep, bn, value, offset)
    else:
        # this is a read command
        tag = (cmd & 0x00F00000) >> 20
        return ADC_CMD_READ(eoq, pause, rep, bn, tag, offset)


class EQADC_MCR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(24)
        self.icea = v_bits(2)
        self._pad1 = v_const(4)
        self.dbg = v_bits(2)

class EQADC_ETDFR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(28)
        self.dfl = v_bits(4)

class EQADC_CFCRx(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(3)
        self.cfeee0 = v_bits(1)
        self.strme0 = v_bits(1)
        self.sse = v_bits(1)
        self.cfinv = v_bits(1)
        self._pad1 = v_const(1)
        self.mode = v_bits(4)
        self.amode0 = v_bits(4)

# The FISRx register bit fields have the same almost the same names as the IDCRx
# register with "f" as a suffix instead of "ie". I'm defining the interrupt flag
# fields in both registers to use the "f" suffix to make setting and checking
# for interrupts more consistent.
#
# Fields that select between enabled interrupt requests and DMA requests are
# indicated with the name of the event field with an added "_dirs" suffix.  so
# CFFS becomes CFFF_DIRS.

class EQADC_IDCRx(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.ncf = v_bits(1)
        self.torf = v_bits(1)
        self.pf = v_bits(1)
        self.eoqf = v_bits(1)
        self.cfuf = v_bits(1)
        self._pad0 = v_const(1)
        self.cfff = v_bits(1)
        self.cfff_dirs = v_bits(1)
        self._pad1 = v_const(4)
        self.rfof = v_bits(1)
        self._pad2 = v_const(1)
        self.rfdf = v_bits(1)
        self.rfds = v_bits(1)

class EQADC_FISRx(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.ncf = v_w1c(1)
        self.torf = v_w1c(1)
        self.pf = v_w1c(1)
        self.eoqf = v_w1c(1)
        self.cfuf = v_w1c(1)
        self.sss = v_const(1)
        self.cfff = v_w1c(1, 1)
        self._pad0 = v_const(5)
        self.rfof = v_w1c(1)
        self._pad1 = v_const(1)
        self.rfdf = v_w1c(1)
        self._pad2 = v_const(1)
        self.cfctr = v_const(4)
        self.tnxtptr = v_const(4)
        self.rfctr = v_const(4)
        self.popnxtptr = v_const(4)

class EQADC_CFTCRx(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(5)
        self.tc = v_bits(11)

class EQADC_CFSSRx(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.cfs0 = v_const(2)
        self.cfs1 = v_const(2)
        self.cfs2 = v_const(2)
        self.cfs3 = v_const(2)
        self.cfs4 = v_const(2)
        self.cfs5 = v_const(2)
        self._pad0 = v_const(5)
        self.lcftcb = v_const(4)
        self.tc_lcftcb = v_const(11)

class EQADC_CFSR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.cfs0 = v_const(2)
        self.cfs1 = v_const(2)
        self.cfs2 = v_const(2)
        self.cfs3 = v_const(2)
        self.cfs4 = v_const(2)
        self.cfs5 = v_const(2)
        self._pad0 = v_const(20)

class EQADC_REDLCCR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(16)
        self.redbs2 = v_bits(4)
        self.srv2 = v_bits(4)
        self.redbs1 = v_bits(4)
        self.srv1 = v_bits(4)

class EQADC_REGISTERS(PeripheralRegisterSet):
    def __init__(self):
        super().__init__()

        self.mcr     = (EQADC_MCR_OFFSET, EQADC_MCR())
        self.etdfr   = (EQADC_ETDFR_OFFSET, EQADC_ETDFR())
        self.cfcr    = (EQADC_CFCR_OFFSET, VTuple([EQADC_CFCRx() for i in range(EQADC_NUM_CBUFFERS)]))
        self.idcr    = (EQADC_IDCR_OFFSET, VTuple([EQADC_IDCRx() for i in range(EQADC_NUM_CBUFFERS)]))
        self.fisr    = (EQADC_FISR_OFFSET, VTuple([EQADC_FISRx() for i in range(EQADC_NUM_CBUFFERS)]))
        self.cftcr   = (EQADC_CFTCR_OFFSET, VTuple([EQADC_CFTCRx() for i in range(EQADC_NUM_CBUFFERS)]))
        self.cfssr   = (EQADC_CFSSR_OFFSET, VTuple([EQADC_CFSSRx() for i in range(EQADC_NUM_ADCS)]))
        self.cfsr    = (EQADC_CFSR_OFFSET, EQADC_CFSR())
        self.redlccr = (EQADC_REDLCCR_OFFSET, EQADC_REDLCCR())


class eQADC(ExternalIOPeripheral):
    """
    Class to emulate the EQADC peripheral.

    NOTE: at the moment this emulation does not connect external interrupt
          sources and GPIO state change notifications. That will be necessary to
          completely emulate the behavior of a typical ADC inputs bus to enable
          the different EQADC pins to accept values from multiple different
          sources depending on the SIU and peripheral configuration for those
          pins.

    NOTE: The NXP EQADC inputs can be connected to ETPU outputs, currently ETPU
          functionality is not implemented.

    <tx/rx example tbd>
    """
    def __init__(self, devname, emu, mmio_addr):
        """
        EQADC constructor.  Each processor has multiple EQADC peripherals so the
        devname parameter must be unique.
        """
        super().__init__(emu, devname, mmio_addr, 0x4000,
                regsetcls=EQADC_REGISTERS,
                isrstatus='fisr', isrflags='idcr', isrevents=EQADC_INT_EVENTS)

        # There are so many peripheral register ranges that need custom handling
        # in this function that we need a fast and easy lookup for the different
        # offsets and the functions that handle that range
        self._get_reg_handlers = {}
        self._get_reg_handlers.update((i, self._getCFPR) for i in EQADC_CFPR_RANGE)
        self._get_reg_handlers.update((i, self._getRFPR) for i in EQADC_RFPR_RANGE)
        self._get_reg_handlers.update((i, self._getCFxRw) for i in EQADC_CFxRw_RANGE)
        self._get_reg_handlers.update((i, self._getRFxRw) for i in EQADC_RFxRw_RANGE)

        self._set_reg_handlers = {}
        self._set_reg_handlers.update((i, self._setCFPR) for i in EQADC_CFPR_RANGE)
        self._set_reg_handlers.update((i, self._setIgnored) for i in EQADC_RFPR_RANGE)
        self._set_reg_handlers.update((i, self._setIgnored) for i in EQADC_CFxRw_RANGE)
        self._set_reg_handlers.update((i, self._setIgnored) for i in EQADC_RFxRw_RANGE)

        # modes (one per CBuffer)
        self.mode = None
        # A list of Command FIFOs (one for each channel)
        self.cfifo = None
        # A list of Results FIFOs
        self.rfifo = None
        # Voltage inputs, there are 256 possible input channels
        self.channels = None

        # Each EQADC device has 2 ADC conversion chips that are indirectly
        # accessed and programmed
        self.adc = (ADC(self, 'ADC0'), ADC(self, 'ADC1'))

        self.registers.cfcr.vsAddParseCallback('by_idx', self.cfcrUpdate)

    def reset(self, emu):
        super().reset(emu)
        for adc in self.adc:
            adc.reset(emu)

        # modes (one per CBuffer)
        self.mode = [EQADC_MODE.DISABLE for i in range(EQADC_NUM_CBUFFERS)]

        # Each FIFO is 4 entries long (except CFIFO0 which can be 8 long),
        # implement each FIFO as a bytearray to make it easy to push and pop
        # data as needed.
        self.cfifo = tuple(bytearray(EQADC_CFIFO_LEN) if i != 0 else \
                bytearray(EQADC_CFIFO0_LEN) for i in range(EQADC_NUM_CBUFFERS))
        self.rfifo = tuple(bytearray(EQADC_RFIFO_LEN) for i in range(EQADC_NUM_CBUFFERS))

        # TODO: should the voltage values really be reset?
        self.channels = [0.0 for i in range(EQADC_NUM_ANALOG_CHAN)]

        # Set special analog voltage values
        self.channels[EQADC_ANALOG_CHAN_VRH] = 5.0
        self.channels[EQADC_ANALOG_CHAN_VRL] = 0.0
        self.channels[EQADC_ANALOG_CHAN_50]  = 2.5
        self.channels[EQADC_ANALOG_CHAN_75]  = 3.75
        self.channels[EQADC_ANALOG_CHAN_25]  = 1.25

        # TODO: come up with a more generic way to initialize these
        if self.devname == 'eQADC_A':
            self.channels[2] = 0.2395   # 0x00C4
            self.channels[20] = 4.9963  # 0x3FFC
            self.channels[21] = 4.9963  # 0x3FFC
            self.channels[22] = 4.9963  # 0x3FFC
            self.channels[23] = 0.2295  # 0x00BC, 0x00C0
        elif self.devname == 'eQADC_B':
            self.channels[9] = 0.3720   # 0x0130, 0x0134

    def _getPeriphReg(self, offset, size):
        handler = self._get_reg_handlers.get(offset)
        if handler is not None:
            data = b''
            while len(data) < size:
                data += handler(offset-len(data), size-len(data))
            return data
        else:
            return super()._getPeriphReg(offset, size)

    def _getCFPR(self, offset, size):
        # reading the CFPR offsets should always return 0
        return b'\x00' * size

    def _getRFPR(self, offset, size):
        channel = (offset - EQADC_RFPR_OFFSET) // 4
        return self.popRFIFO(channel)

    def _getCFxRw(self, offset, size):
        # Calculate which channel and which FIFO index is being read
        channel = (offset - EQADC_CF0Rw_OFFSET) // EQADC_xFIFO_SIZE
        start = offset - EQADC_CFIFOx_OFFSETS[channel]
        end = start + size
        return self.cfifo[channel][start:end]

    def _getRFxRw(self, offset, size):
        # Calculate which channel and which FIFO index is being read
        channel = (offset - EQADC_RF0Rw_OFFSET) // EQADC_xFIFO_SIZE
        start = offset - EQADC_RFIFOx_OFFSETS[channel]
        end = start + size
        return self.rfifo[channel][start:end]

    def _setPeriphReg(self, offset, data):
        handler = self._set_reg_handlers.get(offset)
        if handler is not None:
            while data:
                data = handler(offset, data)
        else:
            super()._setPeriphReg(offset, data)

    def _setCFPR(self, offset, data):
        channel = (offset - EQADC_CFPR_OFFSET) // 4

        # Increment the transfer count for this channel
        self.registers.cftcr[channel].tc += 1

        if self.mode[channel] == EQADC_MODE.DISABLE:
            # If this channel is disable, queue the command
            self.pushCFIFO(channel, data[:4])
        else:
            # Otherwise just process it now
            self.processCommand(channel, data)

        # Return the remainder of data that has not yet been handled
        return data[4:]

    def _setIgnored(self, offset, size):
        # Writes to the RFPR, CFxRw, and RFxRw registers are ignored
        # Return an empty bytes value to indicate that all data has been handled
        return b''

    def cfcrUpdate(self, thing, idx, size, **kwargs):
        # If the SSE flag is set update the SSS status indicator in the FISRx
        # register
        if self.registers.cfcr[idx].sse:
            self._update_cfsr(idx, triggered=True)
            self.registers.cfcr[idx].sse = 0

        if self.registers.cfcr[idx].cfinv:
            self.registers.cfcr[idx].cfinv = 0
            # reset the CFIFO status
            self.registers.fisr[idx].vsOverrideValue('cfctr', 0)
            self.registers.fisr[idx].vsOverrideValue('tnxtptr', 0)
            self.registers.fisr[idx].vsOverrideValue('rfctr', 0)
            self.registers.fisr[idx].vsOverrideValue('popnxtptr', 0)

        # If this is channel 0 then check if the STRME0/AMODE0 fields have
        # anything other than 0, if so raise an exception because we don't
        # emulate those modes yet
        if self.registers.cfcr[idx].strme0 != 0 or \
                self.registers.cfcr[idx].amode0 != 0:
            if idx == 0:
                cfcr = self.registers.cfcr[idx]
                pc = self.emu.getProgramCounter()
                errmsg = '0x%x: %s[%d] Streaming mode not supported (CFCR%d = %s)' % \
                        (pc, self.devname, idx, idx, cfcr.vsEmit().hex())
                raise NotImplementedError(errmsg)
            else:
                # fields not supported for channels other than 0, force them
                # back to 0
                self.registers.cfcr[idx].strme0 = 0
                self.registers.cfcr[idx].amode0 = 0

        # Update mode for the channel being updated
        self.updateMode(idx)

    def _update_cfsr(self, channel, triggered=False):
        mode = self.mode[channel]
        field = EQADC_CFS_FIELDS[channel]
        if mode in EQADC_CFS_WAIT_FOR_TRIGGER_MODES:
            self.registers.fisr[channel].vsOverrideValue('sss', 0)
            self.registers.cfsr.vsOverrideValue(field, EQADC_CFS_MODE.WAITING_FOR_TRIGGER)
        elif mode in EQADC_CFS_IDLE_MODES and triggered:
            self.registers.fisr[channel].vsOverrideValue('sss', 1)
            self.registers.cfsr.vsOverrideValue(field, EQADC_CFS_MODE.TRIGGERED)
        else:
            self.registers.fisr[channel].vsOverrideValue('sss', 0)
            self.registers.cfsr.vsOverrideValue(field, EQADC_CFS_MODE.IDLE)

    def updateMode(self, channel):
        mode = EQADC_MODE(self.registers.cfcr[channel].mode)

        # NOTE: Continuous or non-software triggered results should be generated
        # based on a periodic timer to mimic how long it takes hardware to
        # generate an ADC result.

        if self.mode[channel] != mode:
            self.mode[channel] = mode
            logger.debug('%s[%d]: changing to mode %s', self.devname, channel, self.mode[channel].name)

            # TODO: the sss bit should indicate that the event has not yet
            # occured, when the event is eventually triggered then the sss bit
            # will be set.
            self._update_cfsr(channel)

            # If the channel is not disabled and there are commands in the fifo,
            # process them now
            if self.mode[channel] != EQADC_MODE.DISABLE and self.registers.fisr[channel].cfctr > 0:
                # Pull data from the command FIFO until we run out of data or
                # the EOQ frame is found
                eoq = 0
                while not eoq:
                    # Pull the next object from the Tx FIFO
                    data = self.popCFIFO(channel)
                    if data is None:
                        break
                    eoq = self.processCommand(channel, data)

    def pushCFIFO(self, channel, data):
        # if this is channel 1 and CFCR0[CFEEE0] is set then CFIFO0 is 8 entries
        # long, otherwise it is 4 like every other CFIFO
        if channel == 0 and self.registers.cfcr[0].cfeee0:
            max_fifo_size = EQADC_CFIFO0_LEN
        else:
            max_fifo_size = EQADC_CFIFO_LEN

        fifo_size = self.registers.fisr[channel].cfctr
        if fifo_size < max_fifo_size:
            self.cfifo[channel][EQADC_CMD_SIZE:] = self.cfifo[channel][:-EQADC_CMD_SIZE]
            self.cfifo[channel][:EQADC_CMD_SIZE] = data

            # Increment the FISRx[CFCTR] and FISRx[TNXTPTR] fields
            fifo_size += 1
            self.registers.fisr[channel].vsOverrideValue('cfctr', fifo_size)

            # The Tx pointer should point to the oldest item in the Tx FIFO
            # (if any), so it should be fifo_size - 1
            self.registers.fisr[channel].vsOverrideValue('tnxtptr', max(fifo_size-1, 0))
            self.event(channel, 'cfff', fifo_size != max_fifo_size)

    def popCFIFO(self, channel):
        fifo_size = self.registers.fisr[channel].cfctr
        data = None
        if fifo_size > 0:
            idx = self.registers.fisr[channel].tnxtptr * EQADC_CMD_SIZE
            data = self.cfifo[channel][idx:idx+EQADC_CMD_SIZE]

            # Decrement the SR[RXCTR] and SR[RXNXTPTR] fields
            fifo_size -= 1
            self.registers.fisr[channel].vsOverrideValue('cfctr', fifo_size)

            # The CF pointer should point to the oldest item in the CFIFO (if
            # any), so it should be fifo_size - 1
            self.registers.fisr[channel].vsOverrideValue('tnxtptr', max(fifo_size-1, 0))

            # Indicate that the command fifo is no longer full
            self.event(channel, 'cfff', 1)

        return data

    def popRFIFO(self, channel):
        fifo_size = self.registers.fisr[channel].rfctr
        if fifo_size > 0:
            # The oldest message is always at index 0
            data = self.rfifo[channel][:EQADC_RESULT_SIZE]
            self.rfifo[channel][:-EQADC_RESULT_SIZE] = self.rfifo[channel][EQADC_RESULT_SIZE:]

            # If this channel is in a continuous mode, populate the last entry
            # in the queue with a new result, otherwise remove a result from the
            # FIFO
            if self.mode[channel] in EQADC_CONTINUOUS_SCAN_TRIGGER_MODES:
                last_result = self.rfifo[channel][-(EQADC_RESULT_SIZE*2):-EQADC_RESULT_SIZE]
                self.rfifo[channel][-EQADC_RESULT_SIZE:] = last_result

            else:
                # Increment FISRx[RFCTR] (FISRx[POPNXTPTR] is always 0 in our
                # emulation)
                fifo_size -= 1
                self.registers.fisr[channel].vsOverrideValue('rfctr', fifo_size)

            self.event(channel, 'rfdf', fifo_size != 0)

        else:
            # Create a placeholder value to read
            data = b'\x00' * EQADC_RESULT_SIZE
            logger.debug('%s[%d] (%s): No available data, returning %r',
                    self.devname, channel, self.mode[channel], data)

        return data

    def pushRFIFO(self, channel, data):
        # Add to the Rx FIFO (if it isn't full or disabled)
        fifo_size = self.registers.fisr[channel].rfctr
        if fifo_size < EQADC_RFIFO_LEN:
            # As long as the fifo_size is <= the Rx FIFO max (5) append the data
            # to the Rx FIFO.
            idx = fifo_size * EQADC_RESULT_SIZE
            self.rfifo[channel][idx:idx+EQADC_RESULT_SIZE] = data

            # now increment the fifo size
            fifo_size += 1
            self.registers.fisr[channel].vsOverrideValue('rfctr', fifo_size)

            # A message was added so indicate there is data to be removed from
            # the Rx FIFO
            self.event(channel, 'rfdf', 1)

        else:
            # The Rx FIFO has overflowed
            self.event(channel, 'rfof', 1)

            logger.debug('%s[%d] (%s): Rx overflow, discarding msg %r', self.devname, channel, self.mode[channel].name, data)

    def processReceivedData(self, obj):
        """
        Incoming data for the EQADC peripheral, contains the analog input channel and the
        """
        analog_channel, value = obj
        self.channels[analog_channel] = value

    def processCommand(self, channel, data):
        cmd = parseCommand(data, self.emu.getEndian())
        logger.debug('%s: new command %r', self.devname, cmd)

        # Update the CFSSR for the selected ADC
        field = EQADC_CFS_FIELDS[channel]
        value = self.registers.cfsr.vsGetField(field)
        self.registers.cfssr[cmd.bn].vsOverrideValue(field, value)
        self.registers.cfssr[cmd.bn].vsOverrideValue('lcftcb', channel)
        self.registers.cfssr[cmd.bn].vsOverrideValue('tc_lcftcb', self.registers.cftcr[channel].tc)

        if isinstance(cmd, ADC_CMD_CONVERT):
            if cmd.tag < EQADC_NUM_CBUFFERS:
                config = self.adc[cmd.bn].config(cmd.offset)
                result = self.adc[cmd.bn].convert(cmd.chan, cmd.offset)
                if result is not None:
                    # Pad the result out to 32 bits
                    result = b'\x00\x00' + result

                    # If this is an alt config register then the result may be
                    # sent to the DECFILT peripheral
                    if cmd.offset in ADC_REGS_ALTCNV_RANGE and config & 0x3C00 != 0x0000:
                        errmsg = '%s[%d] DECFILT dest not supported for result 0x%s, cmd %r (config: 0x%x)' % \
                                (self.devname, result.hex(), cmd, config)
                        raise NotImplementedError(errmsg)

                    logger.debug('%s: conversion result = %r (cmd=%r, config=0x%x', self.devname, result, cmd, config)
                    self.pushRFIFO(cmd.tag, result)

                    # TODO: technically "continuous" scans don't stop processing
                    # when EOQ happens. For now if the mode is continuous and
                    # the RFIFO is not full, fill it with copies of the last
                    # result.
                    if self.mode[channel] in EQADC_CONTINUOUS_SCAN_TRIGGER_MODES and cmd.eoq:
                        while self.registers.fisr[channel].rfctr < EQADC_RFIFO_LEN:
                            self.pushRFIFO(cmd.tag, result)

                else:
                    logger.debug('%s: conversion %r result inhibited: 0x%x', self.devname, cmd, config)
            else:
                if cmd.tag == 0b1000:
                    tag_type = 'null'
                else:
                    tag_type = 'reserved'
                logger.debug('%s: Ignoring conversion with %s tag (%r)', self.devname, tag_type, cmd)

        elif isinstance(cmd, ADC_CMD_WRITE):
            logger.debug('%s: Write ADC%d[0x%x] = 0x%x', self.devname, cmd.bn, cmd.offset, cmd.value)
            self.adc[cmd.bn][cmd.offset] = cmd.value

        elif isinstance(cmd, ADC_CMD_READ):
            if cmd.tag < EQADC_NUM_CBUFFERS:
                # Pad the result out to 32 bits
                result = b'\x00\x00' + self.adc[cmd.bn].read(cmd.offset)
                logger.debug('%s: Read ADC%d[0x%x] = %r', self.devname, cmd.bn, cmd.offset, result)
                self.pushRFIFO(cmd.tag, result)
            else:
                if cmd.tag == 0b1000:
                    tag_type = 'null'
                else:
                    tag_type = 'reserved'
                logger.debug('%s: Ignoring read with %s tag (%r)', self.devname, tag_type, cmd)

        else:
            raise Exception('Unepxected ADC Command: %r (%r)' % (cmd, data))

        # If the EOQ flag is set clear the transfer count
        if cmd.eoq:
            self.registers.cftcr[channel].tc = 0

        self.event(channel, 'eoqf', cmd.eoq)
        return cmd.eoq
