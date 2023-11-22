
'''
e200z7 is responsible for defining:
    * register model
    * instruction model
    * APU_EFPU2
    * APU_SPE2
    * basic Interrupts and Exceptions
    * performance monitoring APU
    * power management
    * MMU
    * l1 cache
    * debug support
    * external core complex interfaces
    * internal core interfaces
'''
import sys
import queue
import threading

import logging
logger = logging.getLogger(__name__)

# Standard Vivisect/Envi packages
import envi
import envi.bits as e_bits
import envi.memory as e_mem

# PPC registers
from envi.archs.ppc.regs import REG_MCSR, REG_MSR, REG_TSR, REG_TCR, REG_DEC, \
        REG_DECAR, REG_HID0, REG_HID1, REG_TBU, REG_TB, REG_TBU_WO, REG_TBL_WO
from .ppc_vstructs import BitFieldSPR, v_const, v_w1c, v_bits

# PPC Specific packages
from . import emutimers, clocks, ppc_time, mmio, ppc_mmu, ppc_xbar, e200_intc, \
        intc_exc, e200_gdb


__all__ = [
    'PPC_e200z7',
]


# TODO: Define PIR, PVR, and SVR register contents


class HID0(BitFieldSPR):
    def __init__(self, emu):
        super().__init__(REG_HID0, emu)
        self.emcp = v_bits(1)
        self._pad0 = v_const(7)
        self.doze = v_bits(1)
        self.nap = v_bits(1)
        self.sleep = v_bits(1)
        self._pad1 = v_const(3)
        self.icr = v_bits(1)
        self.nhr = v_bits(1)
        self._pad2 = v_const(1)
        self.tben = v_bits(1)
        self.sel_tbclk = v_bits(1)
        self.dclree = v_bits(1)
        self.dclrce = v_bits(1)
        self.ciclerde = v_bits(1)
        self.mcclrde = v_bits(1)
        self.dapuen = v_bits(1)
        self._pad3 = v_const(7)
        self.nopti = v_bits(1)


class HID1(BitFieldSPR):
    def __init__(self, emu):
        super().__init__(REG_HID1, emu)
        self._pad0 = v_bits(16)
        self.sysctl = v_bits(8)
        self.ats = v_bits(1)
        self._pad1 = v_bits(7)


class TSR(BitFieldSPR):
    def __init__(self, emu):
        super().__init__(REG_TSR, emu)
        self.enw = v_w1c(1)
        self.wis = v_w1c(1)
        self.wrs = v_w1c(2)
        self.dis = v_w1c(1)
        self.fis = v_w1c(1)
        self._pad0 = v_const(26)


class TCR(BitFieldSPR):
    def __init__(self, emu):
        super().__init__(REG_TCR, emu)
        self.wp = v_bits(2)
        self.wrc = v_bits(2)
        self.wie = v_bits(1)
        self.die = v_bits(1)
        self.fp = v_bits(2)
        self.fie = v_bits(1)
        self.are = v_bits(1)
        self.rsvd = v_bits(1)
        self.wpext = v_bits(4)
        self.fpext = v_bits(4)
        self._pad0 = v_bits(13)


class MCSR(BitFieldSPR):
    def __init__(self, emu):
        super().__init__(REG_MCSR, emu)
        self.flags = v_w1c(32)


import envi.archs.ppc.emu as eape
import vivisect.impemu.emulator as vimp_emu
#import vivisect.impemu.platarch.ppc as vimp_ppc_emu

class PPC_e200z7(mmio.ComplexMemoryMap, vimp_emu.WorkspaceEmulator,
                 eape.Ppc32EmbeddedEmulator, ppc_time.PpcEmuTime,
                 #emutimers.ScaledEmuTimeCore, clocks.EmuClocks):
                 emutimers.EmuTimeCore, clocks.EmuClocks):
    def __init__(self, vw):
        # module registry
        self.modules = {}

        # BitFieldSPR registry
        self.sprs = {}

        # initialize base class and CPU/Modules
        mmio.ComplexMemoryMap.__init__(self)

        # Initialize the core PPC emualtor
        eape.Ppc32EmbeddedEmulator.__init__(self, endian=envi.ENDIAN_MSB)

        # initialize the core "helper" emulator. WorkspaceEmulator to start, as
        # it provides inspection hooks and tracing which is helpful for
        # debugging. PpcWorkspaceEmulator is the base PPC WorkspaceEmulator with
        # the necessary hooks in place to support the core vivisect analysis
        # tools.
        #
        # Instead of using the standard vivisect Ppc32EmbeddedWorkspaceEmulator
        # class the PPC_e200z7 is designed so that the core vivisect workspace
        # emulator can be removed in the future to improve performance (at the
        # cost of analysis/inspection/live debug capabilities).

        vimp_emu.WorkspaceEmulator.__init__(self, vw, nostack=True, funconly=False)

        ppc_time.PpcEmuTime.__init__(self)
        #emutimers.ScaledEmuTimeCore.__init__(self, 0.1)
        emutimers.EmuTimeCore.__init__(self)
        clocks.EmuClocks.__init__(self)

        # MCU timers
        self.mcu_wdt = None
        self.mcu_fit = None
        self.mcu_dec = None

        # The TCR register controls the MCU watchdog, Decrementer and
        # Fixed-Interval Timers.
        # TODO: These timers should be running when the timebase is enabled 
        # regardless of the resulting interrrupt on/off action that is 
        # configured.
        self.tcr = TCR(self)
        self.tcr.vsAddParseCallback('wie', self._tcrWIEUpdate)
        self.tcr.vsAddParseCallback('fie', self._tcrFIEUpdate)
        self.tcr.vsAddParseCallback('die', self._tcrDIEUpdate)

        self.tsr = TSR(self)

        self.addSprReadHandler(REG_DEC, self._readDec)
        self.addSprWriteHandler(REG_DEC, self._writeDec)

        # Attach a callback to HID0[TBEN] that can start/stop timebase
        self.hid0 = HID0(self)
        self.hid0.vsAddParseCallback('tben', self._hid0TBUpdate)

        self.hid1 = HID1(self)

        self.mcsr = MCSR(self)

        # Create the MMU peripheral and then redirect the TLB instruction
        # handlers to the MMU
        self.mmu = ppc_mmu.PpcMMU(self)

        # Create the PowerPC INTC peripheral to handle internal (PowerPC
        # standard) exceptions/interrupts
        self.mcu_intc = e200_intc.e200INTC(emu=self, ivors=True)

        # MSR callback handler. We don't need a full BitFieldSPR object but we 
        # do need to re-evaluate pending interrupts when the MSR changes
        self.addSprWriteHandler(REG_MSR, self.mcu_intc.msrUpdated)

        # Create GDBSTUB Server
        self.gdbstub = e200_gdb.e200GDB(self)
        self._run = threading.Event()

        # By default the debugger _run event flag should be set.
        self._run.set()

        # The same sequence of bytes can decode to different PPC or VLE
        # instructions so the opcache must be split into a full PPC and VLE PPC
        # cache
        self.opcache = ({}, {})

        # Some cache information about the current instruction that makes it
        # faster to parse/create PPC-specific exception information.  This is a
        # tuple consisting of:
        # - the current instruction
        # - PC
        # - "next" PC
        # - if PC is in a VLE context or not
        self._cur_instr = (None, 0, 0, False)

        # Support read and write callbacks
        self._read_callbacks = {}
        self._write_callbacks = {}

    def __del__(self):
        self.shutdown()

    def shutdown(self):
        # Call the emutime shutdown function
        super().shutdown()

        if hasattr(self, 'modules') and self.modules:
            # Go through each peripheral and if any of them have a server thread
            # running, stop it now
            for mname in list(self.modules):
                if hasattr(self.modules[mname], 'stop'):
                    self.modules[mname].stop()
                del self.modules[mname]

    def _mcuWDTHandler(self):
        # From "Figure 8-1. Watchdog State Machine" (EREF_RM.pdf page 886)
        if not self.tsr.enw:
            # If TSR[ENW] and TSR[WIS] are both cleared, set TSR[ENW] and start
            # the watchdog timer again
            self.tsr.vsOverrideValue('enw', 1)
            self.mcu_wdt.start()

        elif not self.tsr.wis:
            # If TSR[ENW] is set but not TSR[WIS], set WIS and start the
            # watchdog timer again
            self.tsr.vsOverrideValue('wis', 1)
            self.mcu_wdt.start()

            # Trigger the watchdog exception
            self.queueException(intc_exc.WatchdogTimerException())

        elif self.tcr.wrc:
            # Any value in TCR[WRC] when TSR[ENW] and TSR[WIS] are set causes a
            # reset to happen
            self.queueException(intc_exc.ResetException(intc_exc.ResetSource.CORE_WATCHDOG))

    def _mcuFITHandler(self):
        # Indicate that a fixed-interval timer event has occured
        self.tsr.vsOverrideValue('fis', 1)

        # Trigger the fixed-interval timer exception
        self.queueException(intc_exc.FixedIntervalTimerException())

    def _mcuDECHandler(self):
        # Indicate that a decrementer event has occured
        self.tsr.vsOverrideValue('dis', 1)

        # Trigger the decrementer exception, unless there already is one pending
        if not self.isExceptionActive(intc_exc.DecrementerException):
            self.queueException(intc_exc.DecrementerException())

        # If automatic reload is enabled (TCR[ARE]), load DEC from DECAR
        if self.tcr.are:
            value = self.getRegister(REG_DECAR)
            logger.debug('Reloading DEC from DECAR: 0x%08x', value)
            self.setRegister(REG_DEC, value)

    def _startMCUWDT(self):
        # The watchdog period is determined by the TCR[WP] and TCR[WPEXT] values
        # concatenated together. These identify which bit of the TB to trigger a
        # watchdog event on.  0 being the MSB, 63 being the LSB.
        wdt_bit = self.tcr.wp << 4 | self.tcr.wpext

        # Determine the actual bit number and then the bit mask is the period
        self.mcu_wdt.start(ticks=e_bits.b_mask[63 - wdt_bit])

    def _startMCUFIT(self):
        # The fixed-interval period is determined by the TCR[WP] and TCR[WPEXT]
        # values concatenated together. These identify which bit of the TB to
        # trigger a fixed-interval event on.  0 being the MSB, 63 being the LSB.
        fit_bit = self.tcr.fp << 4 | self.tcr.fpext

        # Determine the actual bit number and then the bit mask is the period
        self.mcu_fit.start(ticks=e_bits.b_mask[63 - fit_bit])

    def _startMCUDEC(self):
        # If there is a queued or active decrementer exception already, attach a
        # cleanup function to it to start start the timer again.  The real
        # processor would just do this immediately but because of variations in
        # how long it may take to execute the handler we have to do it this way
        # for now.
        exc = self.nextPendingException(intc_exc.DecrementerException)
        if exc is not None:
            # There is an active or pending decremeter exception, attach this
            # function as a cleanup function.
            exc.setCleanup(self._startMCUDEC)
        else:
            # There is no active decrementer exception, so start the timer
            self.mcu_dec.start(ticks=self.getRegister(REG_DEC))

    def _tcrWIEUpdate(self, tcr):
        if self.tcr.wie and self.systimeRunning():
            self._startMCUWDT()
        else:
            self.mcu_wdt.stop()

    def _tcrFIEUpdate(self, tcr):
        if self.tcr.fie and self.systimeRunning():
            self._startMCUFIT()
        else:
            self.mcu_fit.stop()

    def _tcrDIEUpdate(self, tcr):
        if self.tcr.die and self.systimeRunning():
            self._startMCUDEC()
        else:
            self.mcu_dec.stop()

    def _readDec(self, emu, op):
        # If the decremeter is running return how many ticks are remaining.
        if self.mcu_dec.running():
            return self.mcu_dec.ticks()
        else:
            # If we return None then the existing REG_DEC value will be used.
            return None

    def _writeDec(self, emu, op):
        value = self.getOperValue(op, 1)

        # If the decrementer is enabled, restart it.
        if self.tcr.die:
            self.mcu_dec.start(ticks=value)

        return value

    def _hid0TBUpdate(self, hid0):
        if self.hid0.tben:
            self.enableTimebase()
        else:
            self.disableTimebase()

    def init(self):
        '''
        Setup the Peripherals supported on this chip
        '''
        # TODO: move MCU timers into the official PowerPC "timebase" class
        # Create the MCU timers
        self.mcu_wdt = self.registerTimer('MCU_WDT', self._mcuWDTHandler)
        self.mcu_fit = self.registerTimer('MCU_FIT', self._mcuFITHandler)
        self.mcu_dec = self.registerTimer('MCU_DEC', self._mcuDECHandler)

        # Create a queue to use for any extra processing that must occur before
        # instructions are processed. This should be more efficient than having
        # required checks each cycle.
        self.extra_processing = []
        self.extra_processing_lock = threading.RLock()

        # Create the queue that external IO threads can use to queue up message
        # for processing
        self.external_io = queue.Queue()

        # reset the system emulation time, then init all modules
        self.systimeReset()

        # initialize the various modules on this chip.
        for key, module in self.modules.items():
            logger.debug("init: Initializing %r...", key)
            module.init(self)

        # Start the core emulator time now
        self.resume_time()

    def reset(self):
        '''
        Reset all registered peripherals that have a reset function.
        Peripherals that should be returned to some pre-determined state when
        the processor resets should implement this function.
        '''
        self.disableTimebase()

        # Reset the cached "current instruction" data
        self._cur_instr = (None, 0, 0, False)

        # Clear out all pending extra processing
        with self.extra_processing_lock:
            self.extra_processing = []

        # First reset the system emulation time, then reset all modules
        self.systimeReset()
        for key, module in self.modules.items():
            if hasattr(module, 'reset'):
                logger.debug("reset: Resetting %r...", key)
                module.reset(self)

        # Start the core emulator time now
        self.resume_time()

    def halt_exec(self):
        '''
        Pause execution on a processor

        #TODO: Make different API calls for each type of break exception:
        * SigTRAP_Exception
        * SigSTOP_Exception
        * SigTSTP_Exception
        '''
        self.queueException(intc_exc.DebugException())

    def _do_halt(self):
        '''
        Internal Pause mechanism (to keep the details in-house).
        This should only be called by something *in the execution thread*.
        Currently, this is only called by DebugException exception during
        exception- handling, causing a halt (pause) to emulation, until resumed.

        We'll simply grab a Queue entry until something is fed to the queue.
        By design, this will halt the processor from executing.  To resume
        execution, The 

        This will only work for single-core emulators.  On Multi-core emu's 
        the remaining cores will continue to execute without some other
        mechanism.
        '''
        self.halt_time()
        self._run.clear()
        self._run.wait()
        self.resume_time()

    def resume_exec(self):
        '''
        Resume the emulator, which has been "paused"
        '''
        self._run.set()

    def debug_client_detached(self):
        '''
        Handles the condition when a gdb client detaches. For now we will halt
        the emulator when this occurs.
        '''
        self.queueException(intc_exc.GdbClientDetachEvent())
        self.resume_exec()

    ###############################################################################
    # Redirect TLB instruction emulation functions to the MMU peripheral
    ###############################################################################

    def i_tlbre(self, op):
        self.mmu.i_tlbre(op)

    def i_tlbwe(self, op):
        self.mmu.i_tlbwe(op)

    def i_tlbsx(self, op):
        self.mmu.i_tlbsx(op)

    def i_tlbivax(self, op):
        self.mmu.i_tlbivax(op)

    def i_tlbsync(self, op):
        self.mmu.i_tlbsync(op)

    ###############################################################################
    # replace the placeholder rfi with MCU INTC "return from interrupt" function
    ###############################################################################

    def _rfi(self, op):
        self.mcu_intc._rfi()
        self.intc._rfi()

    # TODO: properly enable/disable the rfdi instruction
    #if emu.hid0.dapuen == 0:
    #    # rfi is an invalid instruction if the Debug APU is not enabled
    #    envi.InvalidInstruction(mesg='%r is an invalid instruction when the Debug APU is disabled' % op)

    def i_dnh(self, op):
        raise intc_exc.DebugException()

    def i_dni(self, op):
        raise intc_exc.DebugException()

    def readMemory(self, va, size, skipcallbacks=False):
        '''
        Data Read
        '''
        ea = self.mmu.translateDataAddr(va)

        # Translate Segmentation Violation exceptions into the correct PPC
        # Data Read Exception
        try:
            data = mmio.ComplexMemoryMap.readMemory(self, ea, size)
        except envi.SegmentationViolation:
            raise intc_exc.MceDataReadBusError(pc=self.getProgramCounter(),
                                               data=b'', va=va)

        if not skipcallbacks:
            self._checkReadCallbacks(ppc_xbar.XBAR_MASTER.CORE0, ea, data=data)

        return data

    def writeMemory(self, va, bytez, skipcallbacks=False):
        '''
        Data Write
        '''
        ea = self.mmu.translateDataAddr(va)
        try:
            mmio.ComplexMemoryMap.writeMemory(self, ea, bytez)
        except envi.SegmentationViolation:
            raise intc_exc.MceWriteBusError(pc=self.getProgramCounter(),
                                               data=b'', va=va)

        if not skipcallbacks:
            self._checkWriteCallbacks(ppc_xbar.XBAR_MASTER.CORE0, ea, bytez)

        # If this is an executable section, we may need to clear any instruction 
        # cache
        _, _, perm, _ = mmio.ComplexMemoryMap.getMemoryMap(self, ea)
        if perm & e_mem.MM_READ_WRITE:
            self.clearOpcache(ea, len(bytez))

    def updateOpcache(self, ea, vle, op):
        self.opcache[vle][ea] = op

    def clearOpcache(self, ea, size):
        """
        If the physical address being written to has cached instructions,
        those instructions should be cleared.
        """

        # TODO: Not sure of a more efficient way to handle this.  In theory
        # memory writes should happen less often than executing instructions so
        # it seems to make more sense to handle clearing cached instructions
        # during write rather than checking during execute if they are still
        # valid.

        # NOTE: if you have instructions with overlaps like this (numbers 
        # between |--| indicate execution order):
        #
        #   0 1 2 4 5 6 7 8
        #   |1--------|
        #       |2--|3---|
        #
        # Then instruction 1 will be left in the cache and may cause issues when 
        # clearing the cache for self modifying or intentionally tricky code 
        # because this clearOpcache() function won't be called in between 
        # parsing those instructions.
        #
        # To prevent this situation remove the
        #
        #   else:
        #       break
        #
        # statement in the first loop below.

        # Go backwards the max expected max instruction size and delete any 
        # cached instructions if they overlap the modified memory area.
        for addr in range(ea - 1, ea - 16, -1):
            #if addr in self.opcache:
            #    if addr + self.opcache[addr].size > va:
            #        del self.opcache[addr]
            #    else:
            #        break
            if addr in self.opcache[0] and addr + self.opcache[0][addr].size > ea:
                del self.opcache[0][addr]
            if addr in self.opcache[1] and addr + self.opcache[1][addr].size > ea:
                del self.opcache[1][addr]

        for addr in range(ea - 16, ea + size):
            if addr in self.opcache[0]:
                del self.opcache[0][addr]
            if addr in self.opcache[1]:
                del self.opcache[1][addr]

    def getByteDef(self, va):
        ea = self.mmu.translateDataAddr(va)
        return mmio.ComplexMemoryMap.getByteDef(self, ea)

    def isValidPointer(self, va):
        return self.mmu.getDataEntry(va)[2] is not None

    def readRegValue(self, reg):
        """
        A method to read a register value like getRegister() that automatically
        determines if a register is a BitFieldSPR and therefore reads the
        proper object instead of from the register file.

        Because this is less efficient than getRegister() it should not be used
        unless necessary.
        """
        # TODO: figure out how to integrate BitFieldSPR objects more seemlessly?
        sprobj = self.sprs.get(reg)
        if sprobj is None:
            return self.getRegister(reg)
        else:
            return sprobj.read(self)

    def writeRegValue(self, reg, value):
        """
        A method to read a register value like getRegister() that automatically
        determines if a register is a BitFieldSPR and therefore reads the
        proper object instead of from the register file.

        Because this is less efficient than getRegister() it should not be used
        unless necessary.
        """
        # TODO: figure out how to integrate BitFieldSPR objects more seemlessly?
        sprobj = self.sprs.get(reg)
        if sprobj is None:
            return self.setRegister(reg, value)
        else:
            return sprobj.write(self, value)

    def putIO(self, devname, obj):
        """
        enqueue new IO data to be processed by a peripheral
        """
        self.external_io.put_nowait((devname, obj))

    def processIO(self):
        """
        process new IO data
        """
        try:
            while True:
                devname, obj = self.external_io.get_nowait()
                # TODO: may be a faster way to do this than with string/hash
                # lookups
                #logger.debug('processing %s:%r', devname, obj)
                self.modules[devname].processReceivedData(obj)
        except queue.Empty:
            pass

        # Only do one extra processing function call per tick.  If this
        # function needs to be run in future cycles it should requeue
        # itself.
        with self.extra_processing_lock:
            try:
                self.extra_processing.pop(0)()
            except IndexError:
                pass

    def addExtraProcessing(self, func):
        with self.extra_processing_lock:
            # Don't double-add extra processing functions
            if func not in self.extra_processing:
                self.extra_processing.append(func)

    def stepi(self):
        """
        First see if there are any incoming messages that need to be processed
        into their corresponding peripheral registers
        """
        self.processIO()

        try:
            # See if there are any exceptions that need to start being handled
            self.mcu_intc.checkException()

            # do normal opcode parsing and execution
            pc = self.getProgramCounter()
            op = self.parseOpcode(pc)

            # TODO: check MSR for FP (MSR_FP_MASK) and SPE (MSR_SPE_MASK)
            # support here?
            self.executeOpcode(op)

            # Increment the tick counter
            self.tick()

        except intc_exc.ResetException as exc:
            # Reset the entire CPU
            self.reset()

            # If any peripherals have registered a "setResetSource" function 
            # call it now.
            for key, module in self.modules.items():
                if hasattr(module, 'setResetSource'):
                    logger.debug("system reset: setting reset source %s in %s", exc.source, key)
                    module.setResetSource(exc.source)

        except intc_exc.DebugException as exc:
            # TODO: If the op is DNH
            #       If debug exceptions are enabled and external exception 
            #       handling is set this either generates a debug exception (if 
            #       EDBCR0[DNH_EN] is set) or it generates an illegal 
            #       instruction.

            # TODO: if the op is DNI
            #       If debug exceptions are enabled and internal exception 
            #       handling is set this instruction generates a debug 
            #       exception, otherwise it is a no-op.

            # If the Debug APU is enabled and a debug client is attached and 
            # this was a DNH instruction, pass control to the GDB stub.
            self.gdbstub.handleInterrupts(exc)

        except (envi.UnsupportedInstruction, envi.InvalidInstruction) as exc:
            logger.exception('Unsupported Instruction 0x%x', pc)

            # Translate the standard envi exception into the PPC-specific
            # exception
            tb = sys.exc_info()[2]
            self.queueException(intc_exc.ProgramException().with_traceback(tb))

        except intc_exc.INTCException as exc:
            # If any PowerPC-specific exception occurs, queue it to be handled
            # on the next call
            self.queueException(exc)

    def run(self):
        # TODO: potentially slightly faster without calling a separate function,
        # but keeping them in sync is difficult.
        while True:
            self.stepi()

    def queueException(self, exception):
        self.mcu_intc.queueException(exception)

    def isExceptionActive(self, exctype):
        return self.mcu_intc.isExceptionActive(exctype)

    def nextPendingException(self, exctype):
        try:
            return next(self.mcu_intc.findPendingException(exctype))
        except StopIteration:
            return None

    def dmaRequest(self, request):
        logger.debug('DMA request for %s (%s)', request.name, request.value)
        devname, channel = request.value
        self.modules[devname].dmaRequest(channel)

    def getInstrInfo(self, va, arch=envi.ARCH_PPC_E32, skipcache=False):
        ea, vle = self.mmu.translateInstrAddr(va)

        if skipcache:
            op = None
        else:
            op = self.opcache[vle].get(ea)

        if op is None:
            off, b = mmio.ComplexMemoryMap.getByteDef(self, ea)
            if vle:
                op = self._arch_vle_dis.disasm(b, off, va)
            else:
                op = self._arch_dis.disasm(b, off, va)

        instrbytes = b[off:off + op.size]

        return ea, vle, op, instrbytes

    def writeOpcode(self, va, bytez):
        '''
        In PowerPC instructions can use different MMU entries than data, which
        means that using the normal writeMemory() function to install a
        breakpoint may not work properly. Instead there is a special function to
        support modifying instructions.

        This function clears the cache of any instructions written.
        '''
        ea, vle = self.mmu.translateInstrAddr(va)
        try:
            mmio.ComplexMemoryMap.writeMemory(self, ea, bytez)
        except envi.SegmentationViolation:
            raise intc_exc.MceWriteBusError(pc=self.getProgramCounter(),
                                               data=b'', va=va)

        # If this is an executable section, we may need to clear any instruction 
        # cache
        _, _, perm, _ = mmio.ComplexMemoryMap.getMemoryMap(self, ea)
        if perm & e_mem.MM_READ_WRITE:
            self.clearOpcache(ea, len(bytez))

    def parseOpcode(self, va, arch=envi.ARCH_PPC_E32, skipcache=False, skipcallbacks=False):
        '''
        Combination of the WorkspaceEmulator and the standard envi.memory
        parseOpcode functions that handles translating instruction addresses
        into the correct physical address based on the TLB.
        '''
        ea, vle = self.mmu.translateInstrAddr(va)

        if skipcache:
            op = None
        else:
            op = self.opcache[vle].get(ea)

        if op is None:
            off, b = mmio.ComplexMemoryMap.getByteDef(self, ea)
            if vle:
                op = self._arch_vle_dis.disasm(b, off, va)
            else:
                op = self._arch_dis.disasm(b, off, va)

            self.updateOpcache(ea, vle, op)

        if not skipcallbacks:
            self._checkReadCallbacks(ppc_xbar.XBAR_MASTER.CORE0, ea,
                                     size=op.size, instr=True)

        # TODO: Check for the following condition:
        # - SpeEfpuUnavailableException: EFPU/SPE instruction when MSR[SPE] == 0
        #
        # The e200z7 core does not use or need to check for the following
        # conditions:
        # - FloatUnavailableException
        # - APUnavailableException

        # Cache the decoded instruction and the "next" instruction for exception
        # handling information
        self._cur_instr = (op, va, va+op.size, vle)

        return op

    def _checkReadCallbacks(self, src, addr, data=None, size=0, instr=False):
        '''
        Check if there are any read callbacks defined that can be used to
        implement emulation of ECC forced error behavior.
        '''
        # Call the handlers outside of looping through the callbacks because a
        # callback may uninstall itself when called
        call_list = [(s, e, h) for s, e, h in self._write_callbacks.values() if \
                s <= addr and addr < e]
        for start, end, handler in call_list:
            # If data is None, read the "bad" data now
            if data is None:
                data = mmio.ComplexMemoryMap.readMemory(self, addr, size)
            handler(src, addr, data, instr=instr)

    def _checkWriteCallbacks(self, src, addr, data):
        '''
        Check if there are any write callbacks defined that can be used to
        implement emulation of ECC forced error behavior.
        '''
        # Call the handlers outside of looping through the callbacks because a
        # callback may uninstall itself when called
        call_list = [(s, e, h) for s, e, h in self._write_callbacks.values() if \
                s <= addr and addr < e]
        for start, end, handler in call_list:
            handler(src, addr, data, instr=False)

    def installReadCallback(self, baseaddr, endaddr, callback):
        '''
        Allow installing a new read callback. Only one callback at a time is
        supported.
        '''
        if baseaddr not in self._read_callbacks:
            logger.debug('Adding read callback for 0x%x - 0x%x', baseaddr, endaddr)
            self._read_callbacks[baseaddr] = (baseaddr, endaddr, callback)
        else:
            logger.warning('Read callback for 0x%x already installed', baseaddr)

    def removeReadCallback(self, baseaddr):
        '''
        Allow removing an existing read callback
        '''
        if baseaddr in self._read_callbacks:
            start, end, _ = self._read_callbacks.pop(baseaddr)
            logger.debug('Removing read callback for 0x%x - 0x%x', start, end)

    def installWriteCallback(self, baseaddr, endaddr, callback):
        '''
        Allow installing a new write callback. Only one callback at a time is
        supported.
        '''
        if baseaddr not in self._write_callbacks:
            logger.debug('Adding write callback for 0x%x - 0x%x', baseaddr, endaddr)
            self._write_callbacks[baseaddr] = (baseaddr, endaddr, callback)

    def removeWriteCallback(self, baseaddr):
        '''
        Allow removing an existing write callback
        '''
        if baseaddr in self._write_callbacks:
            start, end, _ = self._write_callbacks.pop(baseaddr)
            logger.debug('Removing write callback for 0x%x - 0x%x', start, end)

    ############################################################################
    # stack-related functions adapted from WorkspaceEmulator to return accurate
    # answers based on the current state of the emulator.
    #
    # TODO: we need to implement these functions accurately to use the emulator
    # values (such as r1 for the stack pointer) or perhaps make a "project"
    # version of the WorkspaceEmulator that has logical defaults
    ############################################################################
    #
    #def initStackMemory(self, stacksize=init_stack_size):
    #    pass
    #
    #def isUninitStack(self, val):
    #    return False
    #
    #def isStackPointer(self, va):
    #    return False
    #
    #def getStackOffset(self, va):
    #    return None
