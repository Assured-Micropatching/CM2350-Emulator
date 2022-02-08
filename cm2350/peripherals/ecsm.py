import enum

import envi.bits as e_bits
import envi.archs.ppc.const as eapc
import envi.archs.ppc.regs as eapr

from ..ppc_vstructs import *
from ..ppc_peripherals import *
from ..intc_exc import ExternalException, INTC_SRC
from ..ppc_mmu import PpcTlbFlags

import logging
logger = logging.getLogger(__name__)

__all__  = [
    'ECSM',
]

ECSM_PCT_OFFSET   = 0x0000
ECSM_REV_OFFSET   = 0x0002
ECSM_IMC_OFFSET   = 0x0008
ECSM_MRSR_OFFSET  = 0x000F
ECSM_ECR_OFFSET   = 0x0043
ECSM_ESR_OFFSET   = 0x0047
ECSM_EEGR_OFFSET  = 0x004A
ECSM_FEAR_OFFSET  = 0x0050
ECSM_FEMR_OFFSET  = 0x0056
ECSM_FEAT_OFFSET  = 0x0057
ECSM_FEDRH_OFFSET = 0x0058
ECSM_FEDRL_OFFSET = 0x005C
ECSM_REAR_OFFSET  = 0x0060
ECSM_RESR_OFFSET  = 0x0065
ECSM_REMR_OFFSET  = 0x0066
ECSM_REAT_OFFSET  = 0x0067
ECSM_REDRH_OFFSET = 0x0068
ECSM_REDRL_OFFSET = 0x006C


class ECSM_4BIT_CONST(PeriphRegister):
    def __init__(self, value=0):
        super().__init__()
        self._pad = v_const(4)
        self.value = v_const(4, value)


class ECSM_8BIT_CONST(PeriphRegister):
    def __init__(self, value=0):
        super().__init__()
        self.value = v_const(8, value)


class ECSM_16BIT_CONST(PeriphRegister):
    def __init__(self, value=0):
        super().__init__()
        self.value = v_const(16, value)


class ECSM_32BIT_CONST(PeriphRegister):
    def __init__(self, value=0):
        super().__init__()
        self.value = v_const(32, value)


class ECSM_MRSR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.por = v_const(1)
        self.dir = v_const(1)
        self.swtr = v_const(1)
        self._pad0 = v_const(5)


class ECSM_ECR(PeriphRegister):
    def __init__(self):
        super().__init__()

        # The documentation has all of the event status bits in the ECR have an
        # 'e' prefix, the fields here don't have them so to make setting and
        # checking if an interrupt should happen.

        self._pad0 = v_const(2)
        self.r1br = v_bits(1)
        self.f1br = v_bits(1)
        self._pad1 = v_const(2)
        self.rncr = v_bits(1)
        self.fncr = v_bits(1)


class ECSM_ESR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(2)
        self.r1br = v_w1c(1)
        self.f1br = v_w1c(1)
        self._pad1 = v_const(2)
        self.rncr = v_w1c(1)
        self.fncr = v_w1c(1)


class ECSM_EEGR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(2)
        self.frc1bi = v_bits(1)
        self.fr11bi = v_bits(1)
        self._pad1 = v_const(2)
        self.frcnci = v_bits(1)
        self.fr1nci = v_bits(1)
        self._pad2 = v_const(1)
        self.errbit = v_bits(7)


class ECSM_ATTRS(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.write = v_const(1)
        self.size = v_const(3)
        self.protection = v_const(4)


class ECSM_REGISTERS(PeripheralRegisterSet):
    def __init__(self, emu=None):
        super().__init__(emu)

        self.pct   = (ECSM_PCT_OFFSET,   ECSM_16BIT_CONST(0xE760))
        self.rev   = (ECSM_REV_OFFSET,   ECSM_16BIT_CONST(0x0000))
        self.imc   = (ECSM_IMC_OFFSET,   ECSM_32BIT_CONST(0xC803E400))
        self.mrsr  = (ECSM_MRSR_OFFSET,  ECSM_MRSR())
        self.ecr   = (ECSM_ECR_OFFSET,   ECSM_ECR())
        self.esr   = (ECSM_ESR_OFFSET,   ECSM_ESR())
        self.eegr  = (ECSM_EEGR_OFFSET,  ECSM_EEGR())
        self.fear  = (ECSM_FEAR_OFFSET,  ECSM_32BIT_CONST())
        self.femr  = (ECSM_FEMR_OFFSET,  ECSM_4BIT_CONST())
        self.feat  = (ECSM_FEAT_OFFSET,  ECSM_ATTRS())
        self.fedrh = (ECSM_FEDRH_OFFSET, ECSM_32BIT_CONST())
        self.fedrl = (ECSM_FEDRL_OFFSET, ECSM_32BIT_CONST())
        self.rear  = (ECSM_REAR_OFFSET,  ECSM_32BIT_CONST())
        self.resr  = (ECSM_RESR_OFFSET,  ECSM_8BIT_CONST())
        self.remr  = (ECSM_REMR_OFFSET,  ECSM_4BIT_CONST())
        self.reat  = (ECSM_REAT_OFFSET,  ECSM_ATTRS())
        self.redrh = (ECSM_REDRH_OFFSET, ECSM_32BIT_CONST())
        self.redrl = (ECSM_REDRL_OFFSET, ECSM_32BIT_CONST())


# ECC Error types, the value of the error type is the value that should be saved
# in the RESR register when the error type happens.  These values are taken from
# the "Table 16-13. RAM Syndrome Mapping for Single-Bit Correctable Errors"
# table in MPC5674FRM.pdf (page 498-499).
class ECSM_ERROR_TYPE(enum.IntEnum):
    NO_ERROR = 0x00
    ECC_0    = 0x01
    ECC_1    = 0x02
    ECC_2    = 0x04
    ECC_3    = 0x08
    ECC_4    = 0x10
    ECC_5    = 0x20
    ECC_6    = 0x40
    ECC_7    = 0x80
    DATA_0   = 0xCE
    DATA_1   = 0xCB
    DATA_2   = 0xD3
    DATA_3   = 0xD5
    DATA_4   = 0xD6
    DATA_5   = 0xD9
    DATA_6   = 0xDA
    DATA_7   = 0xDC
    DATA_8   = 0x23
    DATA_9   = 0x25
    DATA_10  = 0x26
    DATA_11  = 0x29
    DATA_12  = 0x2A
    DATA_13  = 0x2C
    DATA_14  = 0x31
    DATA_15  = 0x34
    DATA_16  = 0x0E
    DATA_17  = 0x0B
    DATA_18  = 0x13
    DATA_19  = 0x15
    DATA_20  = 0x16
    DATA_21  = 0x19
    DATA_22  = 0x1A
    DATA_23  = 0x1C
    DATA_24  = 0xE3
    DATA_25  = 0xE5
    DATA_26  = 0xE6
    DATA_27  = 0xE9
    DATA_28  = 0xEA
    DATA_29  = 0xEC
    DATA_30  = 0xF1
    DATA_31  = 0xF4
    DATA_32  = 0x4F
    DATA_33  = 0x4A
    DATA_34  = 0x52
    DATA_35  = 0x54
    DATA_36  = 0x57
    DATA_37  = 0x58
    DATA_38  = 0x5B
    DATA_39  = 0x5D
    DATA_40  = 0xA2
    DATA_41  = 0xA4
    DATA_42  = 0xA7
    DATA_43  = 0xA8
    DATA_44  = 0xAB
    DATA_45  = 0xAD
    DATA_46  = 0xB0
    DATA_47  = 0xB5
    DATA_48  = 0x8F
    DATA_49  = 0x8A
    DATA_50  = 0x92
    DATA_51  = 0x94
    DATA_52  = 0x97
    DATA_53  = 0x98
    DATA_54  = 0x9B
    DATA_55  = 0x9D
    DATA_56  = 0x62
    DATA_57  = 0x64
    DATA_58  = 0x67
    DATA_59  = 0x68
    DATA_60  = 0x6B
    DATA_61  = 0x6D
    DATA_62  = 0x70
    DATA_63  = 0x75


# A mapping of possible values in the EEGR[ERRBIT] field and the resulting
# ECSM_ERROR_TYPE value that will be written to the RESR register when the error
# occurs.
ECSM_EERBIT_VALUES = {
    0:  ECSM_ERROR_TYPE.DATA_0,
    1:  ECSM_ERROR_TYPE.DATA_1,
    2:  ECSM_ERROR_TYPE.DATA_2,
    3:  ECSM_ERROR_TYPE.DATA_3,
    4:  ECSM_ERROR_TYPE.DATA_4,
    5:  ECSM_ERROR_TYPE.DATA_5,
    6:  ECSM_ERROR_TYPE.DATA_6,
    7:  ECSM_ERROR_TYPE.DATA_7,
    8:  ECSM_ERROR_TYPE.DATA_8,
    9:  ECSM_ERROR_TYPE.DATA_9,
    10: ECSM_ERROR_TYPE.DATA_10,
    11: ECSM_ERROR_TYPE.DATA_11,
    12: ECSM_ERROR_TYPE.DATA_12,
    13: ECSM_ERROR_TYPE.DATA_13,
    14: ECSM_ERROR_TYPE.DATA_14,
    15: ECSM_ERROR_TYPE.DATA_15,
    16: ECSM_ERROR_TYPE.DATA_16,
    17: ECSM_ERROR_TYPE.DATA_17,
    18: ECSM_ERROR_TYPE.DATA_18,
    19: ECSM_ERROR_TYPE.DATA_19,
    20: ECSM_ERROR_TYPE.DATA_20,
    21: ECSM_ERROR_TYPE.DATA_21,
    22: ECSM_ERROR_TYPE.DATA_22,
    23: ECSM_ERROR_TYPE.DATA_23,
    24: ECSM_ERROR_TYPE.DATA_24,
    25: ECSM_ERROR_TYPE.DATA_25,
    26: ECSM_ERROR_TYPE.DATA_26,
    27: ECSM_ERROR_TYPE.DATA_27,
    28: ECSM_ERROR_TYPE.DATA_28,
    29: ECSM_ERROR_TYPE.DATA_29,
    30: ECSM_ERROR_TYPE.DATA_30,
    31: ECSM_ERROR_TYPE.DATA_31,
    32: ECSM_ERROR_TYPE.DATA_32,
    33: ECSM_ERROR_TYPE.DATA_33,
    34: ECSM_ERROR_TYPE.DATA_34,
    35: ECSM_ERROR_TYPE.DATA_35,
    36: ECSM_ERROR_TYPE.DATA_36,
    37: ECSM_ERROR_TYPE.DATA_37,
    38: ECSM_ERROR_TYPE.DATA_38,
    39: ECSM_ERROR_TYPE.DATA_39,
    40: ECSM_ERROR_TYPE.DATA_40,
    41: ECSM_ERROR_TYPE.DATA_41,
    42: ECSM_ERROR_TYPE.DATA_42,
    43: ECSM_ERROR_TYPE.DATA_43,
    44: ECSM_ERROR_TYPE.DATA_44,
    45: ECSM_ERROR_TYPE.DATA_45,
    46: ECSM_ERROR_TYPE.DATA_46,
    47: ECSM_ERROR_TYPE.DATA_47,
    48: ECSM_ERROR_TYPE.DATA_48,
    49: ECSM_ERROR_TYPE.DATA_49,
    50: ECSM_ERROR_TYPE.DATA_50,
    51: ECSM_ERROR_TYPE.DATA_51,
    52: ECSM_ERROR_TYPE.DATA_52,
    53: ECSM_ERROR_TYPE.DATA_53,
    54: ECSM_ERROR_TYPE.DATA_54,
    55: ECSM_ERROR_TYPE.DATA_55,
    56: ECSM_ERROR_TYPE.DATA_56,
    57: ECSM_ERROR_TYPE.DATA_57,
    58: ECSM_ERROR_TYPE.DATA_58,
    59: ECSM_ERROR_TYPE.DATA_59,
    60: ECSM_ERROR_TYPE.DATA_60,
    61: ECSM_ERROR_TYPE.DATA_61,
    62: ECSM_ERROR_TYPE.DATA_62,
    63: ECSM_ERROR_TYPE.DATA_63,
    64: ECSM_ERROR_TYPE.ECC_0,
    65: ECSM_ERROR_TYPE.ECC_1,
    66: ECSM_ERROR_TYPE.ECC_2,
    67: ECSM_ERROR_TYPE.ECC_3,
    68: ECSM_ERROR_TYPE.ECC_4,
    69: ECSM_ERROR_TYPE.ECC_5,
    70: ECSM_ERROR_TYPE.ECC_6,
    71: ECSM_ERROR_TYPE.ECC_7,
}


# According to "Table 9-8. Interrupt Request Sources" in MPC5674FRM.pdf the
# 1-bit errors do not trigger interrupts even if set?  The non-correctable
# errors use the same interrupt source
ECSM_INT_SRCS = {
    'r1br': None,
    'f1br': None,
    'rncr': INTC_SRC.ECSM,
    'fncr': INTC_SRC.ECSM,
}

# FEAT/REAT[SIZE] values, based on size of write/read data that caused the error
ECSM_ATTR_SIZE_VALUES = {
    1: 0b000,
    2: 0b001,
    4: 0b010,
    8: 0b011,
}

# FEAT/REAT[PROTECTION] values, based on the MMU cache flags for the affected
# memory region
ECSM_ATTR_PROT_CACHEABLE_MASK  = 0b1000
ECSM_ATTR_PROT_BUFFERED_MASK   = 0b0100
ECSM_ATTR_PROT_SUP_MODE_MASK   = 0b0010
ECSM_ATTR_PROT_DATA_FETCH_MASK = 0b0001


class ECSM(MMIOPeripheral):
    '''
    This is the Error Correction Status Module, on the real system it handles
    flash and RAM ECC.  This simulation just presents the registers and does not
    perform ECC simulation at this time.
    '''
    def __init__(self, emu, mmio_addr):
        super().__init__(emu, 'ECSM', mmio_addr, 0x4000, regsetcls=ECSM_REGISTERS)

        # Callback for the EEGR register that can force RAM ECC write errors
        self.registers.vsAddParseCallback('eegr', self.eegrUpdate)

        self._swt_reset = False

        # Flags to keep track of what types of read/write errors have been
        # enabled.  These are named after the corresponding flags in the EEGR
        # register.  None indicates the bit in EEGR is not set, 1 indicates it
        # has been set and 0 indicates a single-event error has been set and
        # cleared because it occurred.
        self._frc1bi = None
        self._fr11bi = None
        self._frcnci = None
        self._fr1nci = None

    def init(self, emu):
        # Do the normal MMIOPeripheral things, except for calling reset()
        logger.debug('init: %s module', self.devname)
        self.emu = emu

        # Normally a module's init function calls it's reset function.  In this
        # case init is different so we can set the MRSR[POR] bit accurately
        self.registers.reset(self.emu)

        # MRSR[POR] should be 1 after initial power on
        self.registers.mrsr.vsOverrideValue('por', 1)

    def reset(self, emu):
        super().reset(emu)

        # If the SWT reset flag is set, set MRSR[SWTR], otherwise set MRSR[DIR]
        if self._swt_reset:
            # Clear the flag for next reset
            self._swt_reset = False
            self.registers.mrsr.vsOverrideValue('swtr', 1)
        else:
            self.registers.mrsr.vsOverrideValue('dir', 1)

    def swtReset(self):
        # Indicates that a reset is because of a software watchdog timeout
        self._swt_reset = True

    def event(self, name, value):
        """
        Takes in a name for an event, updates the status register (ESR) field of
        the matching name, and if the value is "1" queues a corresponding
        interrupt if there is a valid interrupt source configured.

        Setting an event value of 0 has no effect, and setting an event value of
        1 when the ESR field is already 1 has no effect.
        """
        if value and self.registers.esr.vsGetField(name) == 0:
            self.registers.esr.vsOverrideValue(name, int(value))

            if self.registers.ecr.vsGetField(name) == 1:
                intsrc = ECSM_INT_SRCS[name]
                if intsrc:
                    self.emu.queueException(ExternalException(intsrc))
                else:
                    logger.warning('Ignoring %s event because no valid INT_SRC configured', name)

    def _getAddrAttrs(self, addr, instr):
        flags = 0
        if instr:
            tlb_entry = self.emu.mmu.getInstrEntry(addr)
        else:
            tlb_entry = self.emu.mmu.getDataEntry(addr)

        # This address is in a cache able region if the I (Cache Inhibited flag)
        # is not set
        if not tlb_entry.flags & PpcTlbFlags.I:
            flags |= ECSM_ATTR_PROT_CACHEABLE_MASK

        # TODO: An access is buffered depending on the source bus master and the
        # target bus slave, and the XBAR and PBRIDGE configurations, for now for
        # emulation purposes we will consider this to be not buffered.
        #if not tlb_entry.flags & PpcTlbFlags.W:
        #    flags |= ECSM_ATTR_PROT_BUFFERED_MASK

        if not self.emu.getRegister(eapr.REG_MSR) & eapc.MSR_PR_MASK:
            # MSR[PR] = 0 means supervisor mode
            flags |= ECSM_ATTR_PROT_SUP_MODE_MASK

        if not instr:
            flags |= ECSM_ATTR_PROT_DATA_FETCH_MASK

        return flags

    def writeEventCallback(self, src, addr, data, instr=False):
        """
        Supports forced RAM write ECC errors as configured by in EEGR.  Those
        are the only types of forced ECC errors that the ECSM supports.

        The emulated ECSM peripheral does not do actual ECC checking so no flash
        write errors need to be checked for.
        """
        if self._frc1bi:
            # Continuous RAM 1-bit write errors, set the event and keep the
            # write callback installed
            report = self.registers.ecr.r1br
            event = 'r1br'

        elif self._fr11bi:
            # We can't clear the EEGR[FR11BI] flag so clear the internal flag to
            # indicate that the event has happened.
            report = self.registers.ecr.r1br
            event = 'r1br'
            self._fr11bi = 0

        elif self._frcnci:
            # Continuous RAM non-correctable write errors: set the event and
            # keep the write callback installed
            report = self.registers.ecr.rncr
            event = 'rncr'

        elif self._fr1nci:
            # We can't clear the EEGR[FR1NCI] flag so clear the internal flag to
            # indicate that the event has happened.
            report = self.registers.ecr.rncr
            event = 'rncr'
            self._fr1nci = 0

        else:
            report = 0
            event = None

        if report:
            # All RAM ECC events cause the REAR, REDR, RESR, REMR, and REAT
            # registers to be updated.
            self.registers.rear.vsOverrideValue('value', addr)

            write_value = e_bits.parsebytes(data, 0, len(data), bigend=self.emu.getEndian())
            self.registers.redrh.vsOverrideValue('value', write_value >> 32)
            self.registers.redrl.vsOverrideValue('value', write_value)

            error_type = ECSM_EERBIT_VALUES[self.registers.eegr.errbit]

            # All forced RAM error tests will come from bus master of CORE0
            self.registers.resr.vsOverrideValue('value', error_type.value)

            self.registers.remr.vsOverrideValue('value', src.value)

            self.registers.reat.vsOverrideValue('write', 1)
            self.registers.reat.vsOverrideValue('size', ECSM_ATTR_SIZE_VALUES[len(data)])
            self.registers.reat.vsOverrideValue('protection', self._getAddrAttrs(addr, instr))

        # Now signal the exception (if there is one for this event).  This is
        # done even if the event isn't reported because the ESR bit should be
        # set regardless
        if event is not None:
            self.event(event, 1)

        # If none of the forced error events are set, clear the write error
        # callback
        if not self._frc1bi and not self._fr11bi and \
                not self._frcnci and not self._fr1nci:
            for start, end in self.emu.ram_mmaps:
                logger.debug('Removing write callback to force RAM write error (0x%x - 0x%x)', start, end)
                self.emu.removeWriteCallback(start)

    def eegrUpdate(self, thing):
        # All of the forced error flags must be set to 0 before they can be
        # re-enabled
        if self.registers.eegr.frc1bi:
            if self._frc1bi is None:
                self._frc1bi = 1
        else:
            self._frc1bi = None

        if self.registers.eegr.fr11bi and self._fr11bi is None:
            self._fr11bi = 1
        else:
            self._fr11bi = None

        if self.registers.eegr.frcnci and self._frcnci is None:
            self._frcnci = 1
        else:
            self._frcnci = None

        if self.registers.eegr.fr1nci and self._fr1nci is None:
            self._fr1nci = 1
        else:
            self._fr1nci = None

        # If any of the forced error flags are set ensure that the forced error
        # callback is installed
        if self._frc1bi or self._fr11bi or self._frcnci or self._fr1nci:
            for start, end, in self.emu.ram_mmaps:
                logger.debug('Installing write callback to force RAM write error (0x%x - 0x%x)', start, end)
                self.emu.installWriteCallback(start, end, self.writeEventCallback)
        else:
            for start, end in self.emu.ram_mmaps:
                logger.debug('Removing write callback to force RAM write error (0x%x - 0x%x)', start, end)
                self.emu.removeWriteCallback(start)
