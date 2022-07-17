
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
import logging
import threading
logger = logging.getLogger(__name__)

import envi
import envi.bits as e_bits
import envi.memory as e_mem
from envi.archs.ppc.regs import REG_MCSR, REG_MSR, REG_TSR, REG_TCR, REG_DEC, \
        REG_DECAR, REG_HID0, REG_HID1, REG_TBU, REG_TB, REG_TBU_WO, REG_TBL_WO
from .ppc_vstructs import BitFieldSPR, v_const, v_w1c, v_bits

from . import emutimers, mmio, ppc_mmu, e200_intc, e200_gdb
from .const import *

# PPC/MCU Exceptions
from . import intc_exc, ppc_xbar


__all__ = [
    'PPC_e200z7',
]


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


class PpcEmulationTime(emutimers.EmulationTime):
    '''
    PowerPC specific emulator time and timer handling.
    '''
    # attributes used by the PpcEmulationTime class, but we can't define
    # __slots__ here because this is used as a parent class for multiple
    # inheritance.
    slots = list(set(emutimers.EmulationTime.slots + ['_tb_offset']))

    def __init__(self, systime_scaling=1.0):
        super().__init__(systime_scaling)

        # The time base can be written to which is supposed to reset the point
        # that the system time is counting from.  We don't want to change the
        # EmulationTime._sysoffset offset because that may impact the tracking
        # of any timers currently running.  Instead use a timebase offset value
        # so values read from TBU/TBL will have the correct values but the
        # systicks() will be unmodified.
        self._tb_offset = 0

        # Register the TBU/TBL callbacks, these are read-only so no write
        # callback is attached.
        self.addSprReadHandler(REG_TB, self.tblRead)
        self.addSprReadHandler(REG_TBU, self.tbuRead)
        self.addSprWriteHandler(REG_TB, self._invalid_tb_write)
        self.addSprWriteHandler(REG_TBU, self._invalid_tb_write)

        # TODO: The TBU/TBL hypervisor access registers are write-only, but this
        # is not yet implemented

        # The TBU_WO/TBL_WO SPRs are used to hold the desired timebase offset
        # value in them.  They are write-only so these callback functions ensure
        # the reads are correctly emulated.
        self.addSprReadHandler(REG_TBL_WO, self._invalid_tb_read)
        self.addSprReadHandler(REG_TBU_WO, self._invalid_tb_read)
        self.addSprWriteHandler(REG_TBL_WO, self.tblWrite)
        self.addSprWriteHandler(REG_TBU_WO, self.tbuWrite)

    def _invalid_tb_write(self, emu, op):
        pass

    def _invalid_tb_read(self, emu, op):
        return 0

    def tblRead(self, emu, op):
        '''
        Read callback handler to associate the value of the TBL SPR with the
        EmulationTime.
        '''
        # In 64-bit mode reading the TBL returns the entire 64-bit TB value, in
        # 32-bit mode its just the lower 32-bits, but this masking is done
        # already in the PpcRegOper class (and will be set in the i_mfspr()
        # handler that calls this)
        return self.systicks()

    def tbuRead(self, emu, op):
        '''
        Read callback handler to associate the value of the TBU SPR with the
        EmulationTime.
        '''
        # Get the top 32-bits of the "ticks" value.  This should be only 32-bits
        # wide regardless of if this is a 64-bit or 32-bit machine.
        return (self.systicks() >> 32) & 0xFFFFFFFF

    def tblWrite(self, emu, op):
        '''
        Update the tb_offset so TBL values returned from this point on
        reflect the new offset.
        '''
        # Ensure that the offset value is only 32-bits wide regardless of the
        # platform size.
        tbl_offset = self.getOperValue(op, 1) & 0xFFFFFFFF

        # Based on the new TBL offset and the current value of TBU_WO, calculate
        # the new desired timebase offset
        tbu_offset = emu.getRegister(REG_TBU_WO)
        offset = (tbu_offset << 32) | tbl_offset
        self._tb_offset = super().systicks() - offset

        # Return the offset so that TBL_WO has the correct offset to use to
        # calculate the desired timebase offset.
        return tbl_offset

    def tbuWrite(self, emu, op):
        '''
        Update the tb_offset so TBU values returned from this point on
        reflect the new offset.
        '''
        # Ensure that the offset value is only 32-bits wide regardless of the
        # platform size.
        tbu_offset = self.getOperValue(op, 1) & 0xFFFFFFFF

        # Based on the new TBU offset and the current value of TBL_WO, calculate
        # the new desired timebase offset
        tbl_offset = emu.getRegister(REG_TBL_WO)
        offset = (tbu_offset << 32) | tbl_offset
        self._tb_offset = super().systicks() - offset

        # Return the offset so that TBU_WO has the correct offset to use to
        # calculate the desired timebase offset.
        return tbu_offset

    def systicks(self):
        '''
        Because PowerPC allows writes to the "Write-Only" TBL/TBU registers,
        adjust the returned systicks value by the current offset.
        '''
        return super().systicks() - self._tb_offset


import envi.archs.ppc.emu as eape
import vivisect.impemu.platarch.ppc as vimp_ppc_emu
#class PPC_e200z7(mmio.ComplexMemoryMap, eape.Ppc32EmbeddedEmulator, PpcEmulationTime):
class PPC_e200z7(mmio.ComplexMemoryMap, vimp_ppc_emu.PpcWorkspaceEmulator, eape.Ppc32EmbeddedEmulator, PpcEmulationTime):
    #__slots__ = tuple(set(list(eape.Ppc32EmbeddedEmulator.__slots__) +
    #    vimp_ppc_emu.PpcWorkspaceEmulator.slots + mmio.ComplexMemoryMap.slots + PpcEmulationTime.slots +
    #    ['modules', 'mmu', 'mcu_intc', 'opcache', '_cur_instr', '_read_callbacks', '_write_callbacks']))

    def __init__(self, vw):
        # module registry
        self.modules = {}

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
        #
        # TODO: CLI enabled logread/logwrite functionality?
        #vimp_ppc_emu.PpcWorkspaceEmulator.__init__(self, vw, nostack=True, funconly=False, logread=True, logwrite=True)
        vimp_ppc_emu.PpcWorkspaceEmulator.__init__(self, vw, nostack=True, funconly=False)

        #PpcEmulationTime.__init__(self, 0.1)
        PpcEmulationTime.__init__(self)

        # MCU timers
        self.mcu_wdt = None
        self.mcu_fit = None
        self.mcu_dec = None

        # The TCR register controls the MCU watchdog, Decrementer and
        # Fixed-Interval Timers.
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

        # Create the MMU peripheral and then redirect the TLB instruction
        # handlers to the MMU
        self.mmu = ppc_mmu.PpcMMU(self)

        # Create the PowerPC INTC peripheral to handle internal (PowerPC
        # standard) exceptions/interrupts
        self.mcu_intc = e200_intc.e200INTC(emu=self, ivors=True)

        # Create GDBSTUB Server
        self.gdbstub = e200_gdb.e200GDB(self)
        self._pause_queue = queue.Queue()
        self._pausers = queue.Queue()

        # generic Breakpoint data
        self._bpdata = {}
        self._bps_in_place = False

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
        self._cur_instr = None

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
            self.watchdog.start()

        elif not self.tsr.wis:
            # If TSR[ENW] is set but not TSR[WIS], set WIS and start the
            # watchdog timer again
            self.tsr.vsOverrideValue('wis', 1)
            self.watchdog.start()

            # Trigger the watchdog exception
            self.emu.queueException(intc_exc.WatchdogTimerException())

        elif self.tcr.wrc:
            # Any value in TCR[WRC] when TSR[ENW] and TSR[WIS] are set causes a
            # reset to happen
            self.emu.queueException(intc_exc.ResetException())

    def _mcuFITHandler(self):
        # Indicate that a fixed-interval timer event has occured
        self.tsr.vsOverrideValue('fis', 1)

        # Trigger the fixed-interval timer exception
        self.emu.queueException(intc_exc.FixedIntervalTimerException())

    def _mcuDECHandler(self):
        # Indicate that a decrementer event has occured
        self.tsr.vsOverrideValue('dis', 1)

        # If automatic reload is enabled (TCR[ARE]), load DEC from DECAR
        if self.tcr.are:
            self.setRegister(REG_DEC, self.getRegister(REG_DECAR))

        # Trigger the decrementer exception
        self.emu.queueException(intc_exc.DecrementerException())


    def _startMCUWDT(self):
        # The watchdog period is determined by the TCR[WP] and TCR[WPEXT] values
        # concatenated together. These identify which bit of the TB to trigger a
        # watchdog event on.  0 being the MSB, 63 being the LSB.
        wdt_bit = self.tcr.wp << 4 | self.tcr.wpext

        # Determine the actual bit number and then the bit mask is the period
        self.mcu_wdt.start(period=e_bits.b_mask[63 - wdt_bit])

    def _startMCUFIT(self):
        # The fixed-interval period is determined by the TCR[WP] and TCR[WPEXT]
        # values concatenated together. These identify which bit of the TB to
        # trigger a fixed-interval event on.  0 being the MSB, 63 being the LSB.
        fit_bit = self.tcr.fp << 4 | self.tcr.fpext

        # Determine the actual bit number and then the bit mask is the period
        self.mcu_fit.start(period=e_bits.b_mask[63 - fit_bit])

    def _startMCUDEC(self):
        self.mcu_dec.start(period=self.getRegister(REG_DEC))

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
            self.mcu_dec.start(period=value)

        return value

    def _hid0TBUpdate(self, hid0):
        if self.hid0.tben:
            self.enableTimebase()

            # When the timebase is enabled also check if the WDT, FIT or DEC
            # timers should be started
            if self.tcr.wie:
                self._startMCUWDT()
            if self.tcr.fie:
                self._startMCUFIT()
            if self.tcr.die:
                self._startMCUWDT()

        else:
            self.disableTimebase()

            # If any of the timebase-run MCU timers are running, stop them now
            if self.tcr.wie:
                self.mcu_wdt.stop()
            if self.tcr.fie:
                self.mcu_fit.stop()
            if self.tcr.die:
                self.mcu_dec.stop()

    def init_core(self):
        '''
        Setup the Peripherals supported on this chip
        '''
        # Create the MCU timers
        self.mcu_wdt = self.registerTimer('MCU_WDT', self._mcuWDTHandler)
        self.mcu_fit = self.registerTimer('MCU_FIT', self._mcuFITHandler)
        self.mcu_dec = self.registerTimer('MCU_DEC', self._mcuDECHandler)

        # Create a queue to use for any extra processing that must occur before
        # instructions are processed. This should be more efficient than having
        # required checks each cycle.
        self.extra_processing = queue.Queue()

        # Create the queue that external IO threads can use to queue up message
        # for processing
        # WHY DOES NOTHING SIMPLE EVER WORK RIGHT IN PYTHON ANYMORE?
        self.external_io = queue.Queue()

        # initialize the various modules on this chip.
        for key, module in self.modules.items():
            logger.debug("init_core: Initializing %r...", key)
            module.init(self)

            # Accept possible connections from IO threads
            #self.processIO()

    def reset_core(self):
        '''
        Reset all registered peripherals that have a reset function.
        Peripherals that should be returned to some pre-determined state when
        the processor resets should implement this function.
        '''
        # TODO: move MCU timers into the official PowerPC "timebase" class
        self.disableTimebase()

        # Stop all MCU timers
        self.mcu_wdt.stop()
        self.mcu_fit.stop()
        self.mcu_dec.stop()

        # First reset the system emulation time, then reset all modules
        self.systimeReset()
        for key, module in self.modules.items():
            if hasattr(module, 'reset'):
                logger.debug("reset_core: Resetting %r...", key)
                module.reset(self)

    def halt_exec(self):
        '''
        Pause execution on a processor

        #TODO: Make different API calls for each type of break exception:
        * SigTRAP_Exception
        * SigSTOP_Exception
        * SigTSTP_Exception
        '''
        self.queueException(intc_exc.BreakException())

    def _do_halt(self, signal):
        '''
        Internal Pause mechanism (to keep the details in-house).
        This should only be called by something *in the execution thread*.
        Currently, this is only called by BreakException during exception-
        handling, causing a halt (pause) to emulation, until resumed.

        We'll simply grab a Queue entry until something is fed to the queue.
        By design, this will halt the processor from executing.  To resume
        execution, The 

        This will only work for single-core emulators.  On Multi-core emu's 
        the remaining cores will continue to execute without some other
        mechanism.
        '''
        try:
            # store that we're waiting
            self._pausers.put(threading.currentThread())
            # pause the clock

            # this part hangs until something is put in the queue to be received
            self._pause_queue.get()

        finally:
            # clear out that we are waiting
            self._pausers.get_nowait()

            # resume the clock
            self.resume_time()

    def resume_exec(self):
        '''
        Resume the emulator, which has been "paused"
        Sends a message to the _pause_queue in order to free the paused thread
        '''
        if self._pausers.empty():
            logger.warning("resume while not paused!")
            raise intc_exc.ResumeException("Resume while not Paused!")   # is this bad?

        self._pause_queue.put("YAY! BE FREE!")

    def addBreakpoint(self, va):
        '''
        Handles the details of breakpoint tracking and modified bytes.
        '''
        # if va is already a breakpoint, don't do it!!
        if va in self._bpdata:
            return -1   # raise exception

        brkbytes = self.arch.archGetBreakInstr()

        # check for overlapping breakpoints
        for tva in range(va, va+len(brkbytes)-1):
            if tva in self._bpdata:
                return -2   # raise exception

        for tva in range(va - len(brkbytes)+1, va):
            if tva in self._bpdata:
                return -3   # raise exception

        # store existing bytes
        self._bpdata[va] = self.readMemory(va, len(brkbyes))

    def _putDownBreakpoints(self):
        '''
        At each emulator stop, we want to replace the original bytes.  On 
        resume, we put the Break instruction bytes back in.
        '''
        brkbytes = self.arch.archGetBreakInstr()

        for va in self._bpdata:
            # stamp in a Break instruction
            self.writeMemory(va, brkbytes)

        self._bps_in_place = True

    def _pullUpBreakpoints(self):
        '''
        At each emulator stop, we want to replace the original bytes.  On 
        resume, we put the Break instruction bytes back in.
        '''
        brkbytes = self.arch.archGetBreakInstr()

        for va, origbytes in list(self._bpdata.items()):
            # restore the original bytes
            self.writeMemory(va, origbytes)
        
        self._bps_in_place = False

    def delBreakpoint(self, va):
        '''
        Remove breakpoint.
        '''
        if va not in self._bpdata:
            return -1

        origbytes = self._bpdata.pop(va)
        if self._bps_in_place:
            self.writeMemory(va, origbytes)


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

    def readMemory(self, va, size):
        '''
        Data Read
        '''
        ea = self.mmu.translateDataAddr(va)
        data = mmio.ComplexMemoryMap.readMemory(self, ea, size)
        self._checkReadCallbacks(ppc_xbar.XBAR_MASTER.CORE0, ea, data=data)
        return data

    def writeMemory(self, va, bytez):
        '''
        Data Write
        '''
        ea = self.mmu.translateDataAddr(va)
        mmio.ComplexMemoryMap.writeMemory(self, ea, bytez)
        self._checkWriteCallbacks(ppc_xbar.XBAR_MASTER.CORE0, ea, bytez)

        # If the physical address being written to has cached instructions ,
        # those instructions should be cleared.
        #
        # TODO: Not sure of a more efficient way to handle this.  In theory
        # memory writes should happen less often than executing instructions so
        # it seems to make more sense to handle clearing cached instructions
        # during write rather than checking during execute if they are still
        # valid.
        ppc_addr_to_clear = [a for a in range(ea, ea + len(bytez), 4) if a in self.opcache[0]]
        for addr in ppc_addr_to_clear:
            del self.opcache[0][addr]

        vle_addr_to_clear = [a for a in range(ea, ea + len(bytez), 2) if a in self.opcache[1]]
        for addr in vle_addr_to_clear:
            del self.opcache[1][addr]

    def getByteDef(self, va):
        ea = self.mmu.translateDataAddr(va)
        return mmio.ComplexMemoryMap.getByteDef(self, ea)

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

        try:
            # Only do one extra processing function call per tick.  If this
            # function needs to be run in future cycles it should requeue
            # itself.
            extra_processing_func = self.extra_processing.get_nowait()
            extra_processing_func()
        except queue.Empty:
            pass

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

        except (envi.UnsupportedInstruction, envi.InvalidInstruction) as exc:
            logger.exception('Unsupported Instruction 0x%x', pc)

            # Translate the standard envi exception into the PPC-specific
            # exception
            tb = sys.exc_info()[2]
            self.queueException(intc_exc.ProgramException().with_traceback(tb))

        except intc_exc.ResetException:
            # Special case, don't queue a reset exception, just do a reset
            self.reset()

        except intc_exc.INTCException as exc:
            # If any PowerPC-specific exception occurs, queue it to be handled
            # on the next call
            self.queueException(exc)

    def run(self):
        """
        Faster tight loop of what the stepi() function does.
        Make sure this stays in sync with stepi()!
        """
        while True:
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

            except (envi.UnsupportedInstruction, envi.InvalidInstruction) as exc:
                # Translate standard envi exceptions into the PPC-specific
                # exceptions
                tb = sys.exc_info()[2]
                self.queueException(intc_exc.ProgramException().with_traceback(tb))

            except intc_exc.ResetException:
                # Special case, don't queue a reset exception, just do a reset
                self.reset()

            except intc_exc.INTCException as exc:
                # If any PowerPC-specific exception occurs, queue it to be handled
                # on the next call
                logger.warning("INTCExc: %r", exc)
                self.queueException(exc)

    def queueException(self, exception):
        '''
        redirect exceptions to the MCU exception handler
        '''
        self.mcu_intc.queueException(exception)

    def dmaRequest(self, request):
        logger.debug('DMA request for %s (%s)', request.name, request.value)
        devname, channel = request.value
        self.modules[devname].dmaRequest(channel)

    def parseOpcode(self, va, arch=envi.ARCH_PPC_E32, skipcache=False):
        '''
        Combination of the WorkspaceEmulator and the standard envi.memory
        parseOpcode functions that handles translating instruction addresses
        into the correct physical address based on the TLB.
        '''
        ea, vle = self.mmu.translateInstrAddr(va)
        if skipcache:
            op = None
        else:
            # The same sequence of bytes can decode to different PPC or VLE
            # instructions so a different instruction cache must be used for
            # each mode
            op = self.opcache[vle].get(ea, None)

        # Just assume the read was 4 bytes, passing the size means the data will
        # only be read if there is a callback registered.
        self._checkReadCallbacks(ppc_xbar.XBAR_MASTER.CORE0, ea, size=4, instr=True)

        if op is None:
            off, b = mmio.ComplexMemoryMap.getByteDef(self, ea)
            if vle:
                op = self._arch_vle_dis.disasm(b, off, ea)
            else:
                op = self._arch_dis.disasm(b, off, ea)
            self.opcache[vle][ea] = op

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
