import queue
import logging
import traceback
from .intc_const import *
from . import intc_exc
from .internal.envi.archs.ppc import regs as ppcregs

logger = logging.getLogger(__name__)


class e200INTC:
    '''
    This is the Interrupt Controller for the e200 core.

    When execution is run from the defined run() or runStep() functions,
    exceptions are queued and handled (when raised from within the emulation
    thread or queued via queueException())
    Exceptions are handled when the appropriate MSR flag is set (EE, CE, DE, ME,
    GS?).

    IVPR and IVORs are used to calculate ISR start.  (does PowerISA support
    specific offsets and e200 doesn't?)

    Once an Interrupt is triggered, another Interrupt will not be triggered
    until <<<<<>>>>> happens.

    Once that occurs, execution can be pre-empted by higher priority interrupts
    '''
    def __init__(self, emu, ivors=True, reset=True):
        '''
        Initializer
        emu is an emulator to hook into.  This must have a "modules" dictionary

        If IVORS are supported, the next instruction address will be retrieved from the IVOR# register
        Otherwise, the offset from the base address in IVPR is used (0x20 for each)
        '''
        self.emu = emu
        self.ivors = ivors
        emu.modules['MCU_INTC'] = self
        self._needreset = reset

        # callback handlers
        self._callbacks = {}
        self._callbacks_ext = {}

        self.stack = []     # track current and preempted exceptions
        self._external_intc = None

        # attributes for handling interrupts
        self.intqs = None
        self.exc_count = 0
        self.hasInterrupt = False
        self.canHandleNextInterrupt = True

    def registerExtINTC(self, extintc):
        '''
        Register interrupt controller for External Interrupts
        '''
        if self._external_intc is not None:
            raise Exception("Registering External Interrupt Controller when one exists")

        self._external_intc = extintc

    def init(self, emu):
        logger.debug('init: e200INTC module (Interrupt Controller)')

        # each type of exception has their own queue.
        #FIXME: how does the MPC5674F's 16 priority
        self.srq = queue.SimpleQueue()    # non-critical
        self.gq = queue.SimpleQueue()     # guest
        self.csq = queue.SimpleQueue()    # critical
        self.mcq = queue.SimpleQueue()    # machine-check
        self.dbgq = queue.SimpleQueue()   # debug

        self.reset(emu)

    def reset(self, emu):
        '''
        Clear out any pending exceptions and restore the machine to it's initial state
        '''
        self.intqs = (
                None,
                self.srq,
                self.gq,
                self.csq,
                self.mcq,
                self.dbgq,
                )

        # fast-check status variables (warning, no thread-safety-checks for speed... be very cautious):
        self.exc_count = 0

        # use instance variable to keep the run loop tight.  this must be only used in one thread.
        self.hasInterrupt = False

        # maintain whether a new interrupt *can* be handled yet...
        self.canHandleNextInterrupt = True

        # Default priority level
        self.curlvl = INTC_STATE_NORMAL

    def queueException(self, exception):
        '''
        Handle the details of queing the exception.
        Interrupt handling will be dealt with in handleException

        exception is expected to be a subclass of one of the PriorityExceptions
        '''
        if not exception.shouldHandle(self.emu):
            # skip queuing this exception, we don't handle it
            logger.warning('not handling exception: %r', exception)
            return

        logger.debug('queuing exception: %r', exception)
        self.intqs[exception.prio].put(exception)
        self.exc_count += 1
        self.hasInterrupt = True

    def checkException(self):
        if self.hasInterrupt and self.canHandleNextInterrupt:
            # do most costly Interrupt Handling stuff here
            self.handleException()

    def handleException(self):
        '''
        Look for exceptions that should preempt the current state
        If there are any:
            Store the state
            Set the ESR/MSR/context
            Set the PC to the correct Interrupt Service Routine
                (two modes, determined by INTC_MCR[HVEN])
        '''
        # check current exception level
        # look for higher exception queues to be populated
        for checklvl in range(4, self.curlvl, -1):
            curq = self.intqs[checklvl]
            if not curq.empty():
                # pull the next exception from the prioritized queue.
                newexc = curq.get_nowait()

                # store the new exception on the stack (pushing the new one in
                # front of the previous)
                self.stack.append(newexc)

                # set ESR/MSR??
                newexc.setupContext(self.emu)

                # set PC from IVOR
                newpc = self.getHandler(newexc)

                # Check if there are any peripheral-specific callbacks for this
                # exception type
                ######################T SHIS IS SOME JACKED UP CRAP....  .source doesn't exist on more exceptions!
                if newexc.__ivor__ == EXC_EXTERNAL_INPUT:
                    for callback in self._callbacks_ext.get(newexc.source, []):
                        callback(newexc)

                else: 
                    if newexc.__ivor__ in self._callbacks:
                        for callback in self._callbacks.get(newexc.__ivor__, []):
                            callback(newexc)

                logger.debug('PC: 0x%08x (%r)', self.emu.getProgramCounter(), newexc)
                logger.debug('NEWPC: %r', newpc)
                self.emu.setProgramCounter(newpc)

                # change self.curlvl
                self.curlvl = newexc.prio

                # if exc_count == 0, reset hasException  (in the future, might make this only set when there's an exception of higher priority than current??)
                self.exc_count -= 1
                if not self.exc_count:
                    self.hasInterrupt = False

                break   # only need to do one

    def addCallback(self, exception, callback):
        if exception not in self._callbacks_ext:
            self._callbacks_ext[exception] = [callback]
        else:
            self._callbacks_ext[exception].append(callback)

    def addCallbackInt(self, exception, callback):
        if exception not in self._callbacks:
            self._callbacks[exception] = [callback]
        else:
            self._callbacks[exception].append(callback)

    def getHandler(self, exception):
        '''
        Based on the configuration of the INTC and the exception priority,
        return the correct Next Instruction Address.
        '''
        if exception.__ivor__ == EXC_EXTERNAL_INPUT and self._external_intc is not None:
            return self._external_intc.getHandler(exception)

        # Otherwise use the IVPR + IVOR to find the correct PC of the handler
        ivpr = self.emu.getRegister(ppcregs.REG_IVPR)
        ivor = self.emu.getRegister(exception.__ivor__)
        return ivpr + ivor

    def _rfi(self):
        '''
        perform the INTC-specific tasks necessary upon interrupt-return
        rfi
        rfci
        rfdi
        rfgi
        rfmci
        se_*

        each of these return-from-interrupt instructions must provide the
        correct PC and MSR (stored in their own SRR* registers)
        '''
        # Get rid of the newest exception, it is finished being processed
        if self.stack:
            oldexc = self.stack.pop()

        # If there are still interrupts on the stack then we are returning
        # into another interrupt
        if self.stack:
            curexc = self.stack[-1]
            self.curlvl = curexc.prio
        else:
            self.curlvl = INTC_STATE_NORMAL
