from envi.archs.ppc.regs import *
from envi.archs.ppc.const import *
import vtrace.platforms.gdbstub as vtp_gdb

from .intc_const import *
from .intc_src import INTC_SRC, INTC_EVENT

import logging
logger = logging.getLogger(__name__)


__all__ = [
    # Allow INTC_SRC and INTC_EVENT to be imported from this module
    'INTC_SRC',
    'INTC_EVENT',

    # And all of the INTCException-derived exception types
    'StandardPrioException',
    'CriticalPrioException',
    'DebugPrioException',
    'GuestPrioException',
    'MachineCheckPrioException',
    'ResetException',
    'CriticalInputException',
    'MachineCheckException',
    'DataStorageException',
    'InstructionStorageException',
    'ExternalException',
    'AlignmentException',
    'ProgramException',
    'FloatUnavailableException',
    'SystemCallException',
    'APUnavailableException',
    'DecrementerException',
    'FixedIntervalTimerException',
    'WatchdogTimerException',
    'DataTlbException',
    'InstructionTlbException',
    'DebugException',
    'SpeEfpuUnavailableException',
    'EfpuDataException',
    'EfpuRoundException',
    'PerformanceException',
    'DoorbellException',
    'DoorbellCritException',
    'GuestDoorbellException',
    'GuestDoorbellCritException',
    'HypercallException',
    'HyperPrivException',
    'LRATException',
    'MceNMI',
    'MceInstructionFetchBusError',
    'MceDataReadBusError',
    'MceWriteBusError',
    'GdbClientDetachEvent',
]


### the root of all Interrupt-Controller Exceptions
class INTCException(Exception):
    __ivor__ = None         # which handler does this exception use?
    __msrflag__ = None      # what MSR flag determines whether to cause an exception?
    __priority__ = None     # what's the base priority (recognizing that this can be superceded)
    __msrbits__ = None      # what bits get set in MSR on setup?
    __msrmask__ = None      # what bits are updated?  Don't affect anything outside this mask
    __maskable__ = True     # Indicating if an exception type is non-maskable by default or not

    def __init__(self, msg=None, prio=None, maskable=None, cleanup=None, **kwargs):
        '''
        Initialize the Exception.
        '''
        self.msg = msg
        if prio is None:
            prio = self.__priority__
        self.prio = prio

        if maskable is None:
            maskable = self.__maskable__
        self.maskable = maskable

        # optional cleanup function
        self._cleanup_func = cleanup

        # store any add-ins we might want to include.  These may be helpful when setting flags/etc.
        self.kwargs = kwargs

    def shouldHandle(self, emu):
        '''
        This is the check for whether an exception should be handled or ignored.
        Default is to check self.__msrflag__ in the MSR register.
        Override this function for special cases.

        Nonmaskable interrupts will always return True
        '''
        if not self.maskable:
            return True

        # check the MSR register for the bits set in self.__msrflag__
        if self.__msrflag__ is None:
            return True

        msr = emu.getRegister(REG_MSR)
        if msr & self.__msrflag__:
            return True

        logger.debug('Handling %r not enabled: 0x%08x & 0x%08x', self, self.__msrflag__, msr)
        return False

    def setupContext(self, emu):
        '''
        This is executed *when the exception is being handled*.
        Default implementation checks self.kwargs for 'ESR' and, if existing
        will bitwise-OR the ESR register with that value.
        Same for DEAR, MCSR, and MCAR.
        '''
        # Update/clear the MSR value (if enabled)
        msr_orval = self.kwargs.get('MSRBITS', self.__msrbits__)
        msr_ormask = self.kwargs.get('MSRMASK', self.__msrmask__)
        if msr_orval is not None and msr_ormask is not None:
            msr = emu.getRegister(REG_MSR)
            msr &= (msr_ormask ^ 0xffffffff)
            msr |= msr_orval
            emu.setRegister(REG_MSR, msr)

        # check if we hand in a MCAR value (address) and set REG_MCAR
        mcar_orval = self.kwargs.get('MCAR', None)
        if mcar_orval is not None:
            mcar_ormask = self.kwargs.get('MCARMASK', 0)
            mcar = emu.getRegister(REG_MCAR)
            mcar &= (mcar_ormask ^ 0xffffffff)
            mcar |= mcar_orval
            emu.setRegister(REG_MCAR, mcar)

    def setCleanup(self, cleanup=None):
        self._cleanup_func = cleanup

    def doCleanup(self):
        # If there are any cleanup functions registered, call them
        if self._cleanup_func is not None:
            self._cleanup_func()

    def __eq__(self, other):
        return (self.__class__ == other.__class__) and \
                (vars(self) == vars(other))

    def __repr__(self):
        return "%r(%r)" % (self.__class__,
                ', '.join('%s=%s' % (k, hex(v) if isinstance(v, int) else repr(v)) for k, v in vars(self).items()))

class StandardPrioException(INTCException):
    # MSR[CE, ME, DE, RI] are not cleared
    __msrbits__ = 0x00000000
    __msrmask__ = 0x0406E034

    def setupContext(self, emu):
        # Set SRR0 (current instruction) and SRR1 (Current MSR)
        emu.setRegister(REG_SRR0, emu.getProgramCounter())
        emu.setRegister(REG_SRR1, emu.getRegister(REG_MSR))
        super().setupContext(emu)

class CriticalPrioException(INTCException):
    __msrflag__ = MSR_CE_MASK

    # MSR[ME, DE, RI] are not cleared
    __msrbits__ = 0x00000000
    __msrmask__ = 0x0606E034

    def setupContext(self, emu):
        # Set CSRR0 (next instruction) and CSRR1 (Current MSR)
        emu.setRegister(REG_CSRR0, emu.getProgramCounter())
        emu.setRegister(REG_CSRR1, emu.getRegister(REG_MSR))

        # Call the INTCException setupContext() function instead of
        # StandardPrioException because we have already set the SRR0 and SRR1
        # values here
        INTCException.setupContext(self, emu)

        # The __msrmask__ leaves MSR[DE] not cleared, but it should be cleared
        # if the Debug APU is disabled (HID0[DAPUEN] == 0) or if it is enabled
        # (HID0[DAPUEN] == 1) and HID0[CICLRDE] == 1
        if emu.hid0.dapuen == 0 or \
                (emu.hid0.dapuen == 1 and emu.hid0.ciclerde == 1):
            msr = emu.getRegister(REG_MSR)
            msr &= (MSR_DE_MASK ^ 0xffffffff)
            emu.setRegister(REG_MSR, msr)

class DebugPrioException(INTCException):
    __priority__ = INTC_LEVEL.DEBUG

class GuestPrioException(INTCException):
    __priority__ = INTC_LEVEL.GUEST

class MachineCheckPrioException(INTCException):
    __priority__ = INTC_LEVEL.MACHINE_CHECK

class ResetException(INTCException):
    __priority__ = INTC_LEVEL.MACHINE_CHECK
    __ivor__ = EXC_RESET
    __maskable__ = False

### Base Exceptions (related to IVORs)
class CriticalInputException(CriticalPrioException):
    __priority__ = INTC_LEVEL.CRITICAL_INPUT
    __ivor__ = EXC_CRITICAL_INPUT

class MachineCheckException(MachineCheckPrioException):
    __priority__ = INTC_LEVEL.MACHINE_CHECK
    __ivor__ = EXC_MACHINE_CHECK
    __mcsrbits__ = None     # what bits get set in MCSR on setup?
    __mcsrmask__ = None     # what bits are updated?  Don't affect anything outside this mask

    # "error report" and NMI Machine Check interrupts are always enabled
    # regardless of MSR[ME]. All Machine Check exceptions described in this file
    # fall into that category
    #__msrflag__ = MSR_ME_MASK

    # MSR[DE] is not cleared
    __msrbits__ = 0x00000000
    __msrmask__ = 0x0606F036

    def setupContext(self, emu):
        # Set MCSRR0 (current instruction) and MCSRR1 (Current MSR)
        emu.setRegister(REG_MCSRR0, emu.getProgramCounter())
        emu.setRegister(REG_MCSRR1, emu.getRegister(REG_MSR))

        # Machine Check exceptions also need to set the MCSR register
        mcsr_orval = self.kwargs.get('MCSRBITS', self.__mcsrbits__)
        mcsr_ormask = self.kwargs.get('MCSRMASK', self.__mcsrmask__)
        if mcsr_orval is not None and mcsr_ormask is not None:
            mcsr = emu.mcsr.flags
            mcsr &= (mcsr_ormask ^ 0xffffffff)
            mcsr |= mcsr_orval
            emu.mcsr.vsOverrideValue('flags', mcsr)

        super().setupContext(emu)

        # The __msrmask__ leaves MSR[DE] not cleared, but it should be cleared
        # if the Debug APU is disabled (HID0[DAPUEN] == 0) or if it is enabled
        # (HID0[DAPUEN] == 1) and HID0[MCCLRDE] == 1
        if emu.hid0.dapuen == 0 or \
                (emu.hid0.dapuen == 1 and emu.hid0.mcclrde== 1):
            msr = emu.getRegister(REG_MSR)
            msr &= (MSR_DE_MASK ^ 0xffffffff)
            emu.setRegister(REG_MSR, msr)

class DataStorageException(MachineCheckPrioException):
    __priority__ = INTC_LEVEL.DATA_STORAGE
    __ivor__ = EXC_DATA_STORAGE

    # MSR[CE, ME, DE, RI] are not cleared
    __msrbits__ = 0x00000000
    __msrmask__ = 0x0604E034

    # TODO: There are 3 different types of DSI exceptions, each one has
    # different ESR bits

    def setupContext(self, emu):
        # Set the correct ESR bits for the current instruction
        esr_val = 0

        msr = emu.getRegister(REG_MSR)

        op, pc, _, vle = emu._cur_instr

        # Access error: ESR[ST, SPE, VLEMI] bits set (if appropriate)
        # Byte Ordering error: ESR[ST, SPE, VLEMI, BO] bits set (if appropriate)
        # Cache Locking error: ESR[DLK/ILK, VLEMI, ST] bits set (if appropriate)

        # TODO: update with cleaner way to check for a "load" ppc instruction
        if op.mnem[:2] == 'st':
            if op.iflags & IF_MEM_EA:
                esr_val = ESR_ST_MASK
        elif op.mnem[:2] in ('ef', 'ev'):
            esr_val = ESR_SPE_MASK
            if op.iflags & IF_MEM_EA and op.mnem[:4] in ('efst', 'evst'):
                esr_val |= ESR_ST_MASK
        elif msr & MSR_UCLE_MASK == 0:
            if op.mnem in ('dcbtls', 'dcbtstls', 'dcblc'):
                esr_val = ESR_DLK_MASK
            elif op.mnem in ('icbtls', 'icblc'):
                esr_val = ESR_ILK_MASK

        # TODO: byte-ordering mismatch condition not checked for
        if vle:
            esr_val = ESR_VLEMI_MASK
            if pc & 1:
                esr_val |= ESR_MIF_MASK
        else:
            if pc & 3:
                esr_val = ESR_MIF_MASK

        emu.setRegister(REG_ESR, esr_val)

        # Set SRR0 (current instruction) and SRR1 (Current MSR)
        emu.setRegister(REG_SRR0, emu.getProgramCounter())
        emu.setRegister(REG_SRR1, emu.getRegister(REG_MSR))

        super().setupContext(emu)

        # The __msrmask__ leaves MSR[DE] not cleared, but it should be cleared
        # if the Debug APU is disabled (HID0[DAPUEN] == 0) or if it is enabled
        # (HID0[DAPUEN] == 1) and HID0[MCCLRDE] == 1
        if emu.hid0.dapuen == 0 or \
                (emu.hid0.dapuen == 1 and emu.hid0.mcclrde== 1):
            msr = emu.getRegister(REG_MSR)
            msr &= (MSR_DE_MASK ^ 0xffffffff)
            emu.setRegister(REG_MSR, msr)

class InstructionStorageException(MachineCheckPrioException):
    __priority__ = INTC_LEVEL.INSTR_STORAGE
    __ivor__ = EXC_INSTR_STORAGE

    # MSR[CE, ME, DE, RI] are not cleared
    __msrbits__ = 0x00000000
    __msrmask__ = 0x0604E034

    def setupContext(self, emu):
        # Set the correct ESR bits for the current instruction
        esr_val = 0

        _, pc, _, vle = emu._cur_instr

        # ESR[BO, MIF, VLEMI] bits set (if appropriate)
        # TODO: byte-ordering mismatch condition not checked for
        if vle:
            esr_val = ESR_VLEMI_MASK
            if pc & 1:
                esr_val |= ESR_MIF_MASK
        else:
            if pc & 3:
                esr_val = ESR_MIF_MASK

        emu.setRegister(REG_ESR, esr_val)

        # Set SRR0 (current instruction) and SRR1 (Current MSR)
        emu.setRegister(REG_SRR0, emu.getProgramCounter())
        emu.setRegister(REG_SRR1, emu.getRegister(REG_MSR))

        super().setupContext(emu)

        # The __msrmask__ leaves MSR[DE] not cleared, but it should be cleared
        # if the Debug APU is disabled (HID0[DAPUEN] == 0) or if it is enabled
        # (HID0[DAPUEN] == 1) and HID0[MCCLRDE] == 1
        if emu.hid0.dapuen == 0 or \
                (emu.hid0.dapuen == 1 and emu.hid0.mcclrde== 1):
            msr = emu.getRegister(REG_MSR)
            msr &= (MSR_DE_MASK ^ 0xffffffff)
            emu.setRegister(REG_MSR, msr)

class ExternalException(StandardPrioException):
    __priority__ = INTC_LEVEL.EXTERNAL_INPUT
    __ivor__ = EXC_EXTERNAL_INPUT
    __msrflag__ = MSR_EE_MASK

    def __init__(self, source, *args, **kwargs):
        # External Exceptions (peripheral interrupts) need additional source
        # information to be routed to the correct handler
        self.source = source
        super().__init__(*args, **kwargs)

    def shouldHandle(self, emu):
        if super().shouldHandle(emu):
            # If this ExternalException can be handled, check if the current
            # priority level allows handling it now or not
            return emu.intc.shouldHandle(self)
        else:
            return False

class AlignmentException(StandardPrioException):
    __priority__ = INTC_LEVEL.ALIGNMENT
    __ivor__ = EXC_ALIGNMENT

    def setupContext(self, emu):
        # Set the correct ESR bits for the current instruction
        esr_val = 0

        op, _, _, vle = emu._cur_instr

        # TODO: update with cleaner way to check for a "load" ppc instruction
        if op.mnem[:2] == 'st':
            if op.iflags & IF_MEM_EA:
                esr_val = ESR_ST_MASK
        elif op.mnem[:2] in ('ef', 'ev'):
            esr_val = ESR_SPE_MASK
            if op.iflags & IF_MEM_EA and op.mnem[:4] in ('efst', 'evst'):
                esr_val |= ESR_ST_MASK

        if vle:
            esr_val |= ESR_VLEMI_MASK

        emu.setRegister(REG_ESR, esr_val)

        # If an address is provided update DEAR
        va = self.kwargs.get('va', None)
        if va is not None:
            emu.setRegister(REG_DEAR, va)

        super().setupContext(emu)

class ProgramException(StandardPrioException):
    __priority__ = INTC_LEVEL.PROGRAM
    __ivor__ = EXC_PROGRAM

    def setupContext(self, emu):
        # Set the correct ESR bits for the current instruction
        esr_val = 0

        _, _, _, vle = emu._cur_instr

        # TODO: Currently this is only supporting the "Illegal Instruction"
        # case, the following conditions need to be handled in the future:
        # - privileged instruction exception
        # - trap exception
        # - unimplemented operation exception
        esr_val = ESR_PIL_MASK

        if vle:
            esr_val |= ESR_VLEMI_MASK

        emu.setRegister(REG_ESR, esr_val)

        super().setupContext(emu)

class FloatUnavailableException(StandardPrioException):
    __priority__ = INTC_LEVEL.FPU_UNAVAILABLE
    __ivor__ = EXC_FLOAT_UNAVAILABLE

class SystemCallException(StandardPrioException):
    __priority__ = INTC_LEVEL.SYSTEM_CALL
    __ivor__ = EXC_SYSTEM_CALL

    def setupContext(self, emu):
        # Set the correct ESR bits for the current instruction
        esr_val = 0

        # TODO: seems like there should be a way to just cache this info in
        # exceuteOpcode()
        pc = emu.getProgramCounter()
        _, vle = self.mmu.translateInstrAddr(pc)

        if vle:
            esr_val |= ESR_VLEMI_MASK

        emu.setRegister(REG_ESR, esr_val)

        super().setupContext(emu)

class APUnavailableException(MachineCheckPrioException):
    __priority__ = INTC_LEVEL.FPU_UNAVAILABLE
    __ivor__ = EXC_APU_UNAVAILABLE

    # MSR[CE, ME, DE, RI] are not cleared
    __msrbits__ = 0x00000000
    __msrmask__ = 0x0604E034

    def setupContext(self, emu):
        # Set SRR0 (current instruction) and SRR1 (Current MSR)
        emu.setRegister(REG_SRR0, emu.getProgramCounter())
        emu.setRegister(REG_SRR1, emu.getRegister(REG_MSR))

        super().setupContext(emu)

        # The __msrmask__ leaves MSR[DE] not cleared, but it should be cleared
        # if the Debug APU is disabled (HID0[DAPUEN] == 0) or if it is enabled
        # (HID0[DAPUEN] == 1) and HID0[MCCLRDE] == 1
        if emu.hid0.dapuen == 0 or \
                (emu.hid0.dapuen == 1 and emu.hid0.mcclrde== 1):
            msr = emu.getRegister(REG_MSR)
            msr &= (MSR_DE_MASK ^ 0xffffffff)
            emu.setRegister(REG_MSR, msr)

class DecrementerException(StandardPrioException):
    __priority__ = INTC_LEVEL.DECREMENTER
    __ivor__ = EXC_DECREMENTER

    def setupContext(self, emu):
        # Set SRR0 (next instruction) and SRR1 (Current MSR)
        emu.setRegister(REG_SRR0, emu.getProgramCounter())
        emu.setRegister(REG_SRR1, emu.getRegister(REG_MSR))

        # Call the INTCException setupContext() function instead of
        # StandardPrioException because we have already set the SRR0 and SRR1
        # values here
        INTCException.setupContext(self, emu)

class FixedIntervalTimerException(StandardPrioException):
    __priority__ = INTC_LEVEL.FIXED_INTERVAL_TIMER
    __ivor__ = EXC_FIXED_INTERVAL_TIMER

    def setupContext(self, emu):
        # Set SRR0 (next instruction) and SRR1 (Current MSR)
        emu.setRegister(REG_SRR0, emu.getProgramCounter())
        emu.setRegister(REG_SRR1, emu.getRegister(REG_MSR))

        # Call the INTCException setupContext() function instead of
        # StandardPrioException because we have already set the SRR0 and SRR1
        # values here
        INTCException.setupContext(self, emu)

class WatchdogTimerException(CriticalPrioException):
    __priority__ = INTC_LEVEL.WATCHDOG_TIMER
    __ivor__ = EXC_WATCHDOG_TIMER

class DataTlbException(StandardPrioException):
    __priority__ = INTC_LEVEL.DATA_TLB_ERROR
    __ivor__ = EXC_DATA_TLB_ERROR

    def setupContext(self, emu):
        # Set the correct ESR bits for the current instruction
        esr_val = 0

        op, pc, _, vle = emu._cur_instr

        # TODO: update with cleaner way to check for a "load" ppc instruction
        if op.mnem[:2] == 'st':
            if op.iflags & IF_MEM_EA:
                esr_val = ESR_ST_MASK
        elif op.mnem[:2] in ('ef', 'ev'):
            esr_val = ESR_SPE_MASK
            if op.iflags & IF_MEM_EA and op.mnem[:4] in ('efst', 'evst'):
                esr_val |= ESR_ST_MASK

        if vle:
            esr_val |= ESR_VLEMI_MASK

        emu.setRegister(REG_ESR, esr_val)

        # If an address is provided update DEAR
        va = self.kwargs.get('va', None)
        if va is not None:
            emu.setRegister(REG_DEAR, va)

        super().setupContext(emu)

class InstructionTlbException(StandardPrioException):
    __priority__ = INTC_LEVEL.INSTR_TLB_ERROR
    __ivor__ = EXC_INSTR_TLB_ERROR

    def setupContext(self, emu):
        # Always set the ESR[MIF] bit since that is the only reason this
        # exception happens
        esr_val = ESR_MIF_MASK
        emu.setRegister(REG_ESR, esr_val)

        super().setupContext(emu)

class DebugException(DebugPrioException):
    __priority__ = INTC_LEVEL.DEBUG
    __ivor__ = EXC_DEBUG

    # MSR[CE, EE, ME, RI] are not cleared
    __msrbits__ = 0x00000000
    __msrmask__ = 0x06046034

    def setupContext(self, emu):
        # If the Debug APU is not enabled the debug exception uses the CSRR0/1 
        # registers and the exception handler is returned from with RFI

        # Set CSRR0 (next instruction) and CSRR1 (Current MSR)
        #emu.setRegister(REG_CSRR0, emu._cur_instr[2])
        emu.setRegister(REG_CSRR0, emu.getProgramCounter())
        emu.setRegister(REG_CSRR1, emu.getRegister(REG_MSR))

        # Call the INTCException setupContext() function instead of
        # StandardPrioException because we have already set the SRR0 and SRR1
        # values here
        INTCException.setupContext(self, emu)

        # The __msrmask__ leaves MSR[DE] not cleared, but it should be cleared
        # if the Debug APU is disabled (HID0[DAPUEN] == 0) or if it is enabled
        # (HID0[DAPUEN] == 1) and HID0[CICLRDE] == 1
        if emu.hid0.dapuen == 0 or \
                (emu.hid0.dapuen == 1 and emu.hid0.ciclerde == 1):
            msr = emu.getRegister(REG_MSR)
            msr &= (MSR_DE_MASK ^ 0xffffffff)
            emu.setRegister(REG_MSR, msr)

        super().setupContext(emu)

        # TODO: Check the HID0 register to determine if MSR[CE, EE] should be 
        # cleared or not


class SpeEfpuUnavailableException(StandardPrioException):
    __priority__ = INTC_LEVEL.FPU_UNAVAILABLE
    __ivor__ = EXC_SPE_EFPU_UNAVAILABLE

    def setupContext(self, emu):
        # Set the correct ESR bits for the current instruction, ESR[SPE] is
        # always set
        esr_val = ESR_SPE_MASK

        # TODO: seems like there should be a way to just cache this info in
        # exceuteOpcode()
        pc = emu.getProgramCounter()
        _, vle = self.mmu.translateInstrAddr(pc)
        if vle:
            esr_val |= ESR_VLEMI_MASK

        emu.setRegister(REG_ESR, esr_val)

        super().setupContext(emu)

class EfpuDataException(StandardPrioException):
    __priority__ = INTC_LEVEL.FPU_UNAVAILABLE
    __ivor__ = EXC_EFPU_DATA

    def setupContext(self, emu):
        # Set the correct ESR bits for the current instruction, ESR[SPE] is
        # always set
        esr_val = ESR_SPE_MASK

        # TODO: seems like there should be a way to just cache this info in
        # exceuteOpcode()
        pc = emu.getProgramCounter()
        _, vle = self.mmu.translateInstrAddr(pc)
        if vle:
            esr_val |= ESR_VLEMI_MASK

        emu.setRegister(REG_ESR, esr_val)

        super().setupContext(emu)

class EfpuRoundException(StandardPrioException):
    __priority__ = INTC_LEVEL.SYSTEM_CALL
    __ivor__ = EXC_EFPU_ROUND

    def setupContext(self, emu):
        # Set the correct ESR bits for the current instruction, ESR[SPE] is
        # always set
        esr_val = ESR_SPE_MASK

        # TODO: seems like there should be a way to just cache this info in
        # exceuteOpcode()
        pc = emu.getProgramCounter()
        _, vle = self.mmu.translateInstrAddr(pc)
        if vle:
            esr_val |= ESR_VLEMI_MASK

        emu.setRegister(REG_ESR, esr_val)

        # Set SRR0 (next instruction) and SRR1 (Current MSR)
        emu.setRegister(REG_SRR0, emu.getProgramCounter())
        emu.setRegister(REG_SRR1, emu.getRegister(REG_MSR))

        # Call the INTCException setupContext() function instead of
        # StandardPrioException because we have already set the SRR0 and SRR1
        # values here
        INTCException.setupContext(self, emu)

class PerformanceException(StandardPrioException):
    __priority__ = INTC_LEVEL.PERFORMANCE
    __ivor__ = EXC_PERFORMANCE

    def setupContext(self, emu):
        # Set SRR0 (next instruction) and SRR1 (Current MSR)
        emu.setRegister(REG_SRR0, emu.getProgramCounter())
        emu.setRegister(REG_SRR1, emu.getRegister(REG_MSR))

        # Call the INTCException setupContext() function instead of
        # StandardPrioException because we have already set the SRR0 and SRR1
        # values here
        INTCException.setupContext(self, emu)


###############################################################################
# The following exceptions are standard PowerPC exceptions but not supported by
# cores that don't support the E.PC, E.HV, and E.HV.LRAT categories (the e200z7
# core does not support these)
###############################################################################


class DoorbellException(StandardPrioException):
    __priority__ = INTC_LEVEL.PROCESSOR_DOORBELL
    __ivor__ = EXC_DOORBELL

    def setupContext(self, emu):
        raise NotImplementedError()

class DoorbellCritException(StandardPrioException):
    __priority__ = INTC_LEVEL.PROCESSOR_DOORBELL
    __ivor__ = EXC_DOORBELL_CRITICAL

    def setupContext(self, emu):
        raise NotImplementedError()

class GuestDoorbellException(StandardPrioException):
    __priority__ = INTC_LEVEL.GUEST_DOORBELL
    __ivor__ = EXC_GUEST_DOORBELL

    def setupContext(self, emu):
        raise NotImplementedError()

class GuestDoorbellCritException(StandardPrioException):
    __priority__ = INTC_LEVEL.GUEST_DOORBELL
    __ivor__ = EXC_GUEST_DOORBELL_CRITICAL

    def setupContext(self, emu):
        raise NotImplementedError()

class HypercallException(StandardPrioException):
    __priority__ = INTC_LEVEL.SYSTEM_CALL
    __ivor__ = EXC_HYPERCALL

    def setupContext(self, emu):
        raise NotImplementedError()

class HyperPrivException(StandardPrioException):
    __priority__ = INTC_LEVEL.PROGRAM_PRIV
    __ivor__ = EXC_HYPERPRIV

    def setupContext(self, emu):
        raise NotImplementedError()

class LRATException(StandardPrioException):
    __priority__ = INTC_LEVEL.LRAT_ERROR
    __ivor__ = EXC_LRAT_ERROR

    def setupContext(self, emu):
        raise NotImplementedError()


###############################################################################
# More specific Machine Check Exception types
###############################################################################

class MceNMI(MachineCheckException):
    __maskable__ = False
    # Set the MCSR[NMI] bit
    __mcsrbits__ = 0x00100000
    __mcsrmask__ = 0x00100000

class MceInstructionFetchBusError(MachineCheckException):
    # Set the MCSR[IF] bit
    __mcsrbits__ = 0x00010000
    __mcsrmask__ = 0x00010000

class MceDataReadBusError(MachineCheckException):
    # Set the MCSR[LD] bit
    __mcsrbits__ = 0x00008000
    __mcsrmask__ = 0x00008000

class MceWriteBusError(MachineCheckException):
    # Set the MCSR[ST] bit
    __mcsrbits__ = 0x00004000
    __mcsrmask__ = 0x00004000


###############################################################################
# Debug exception used to signal when GDB clients detach
###############################################################################

class GdbClientDetachEvent(DebugException):
    pass

