import queue
import logging
import traceback
import operator

from envi.archs.ppc import regs as ppcregs

from .intc_const import *
from . import intc_exc

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

        self.stack = []     # track current and preempted exceptions
        self._external_intc = None

        # attributes for handling interrupts
        self.pending = []
        self.hasInterrupt = False

    def registerExtINTC(self, extintc):
        '''
        Register interrupt controller for External Interrupts
        '''
        if self._external_intc is not None:
            raise Exception("Registering External Interrupt Controller when one exists")

        self._external_intc = extintc

    def init(self, emu):
        logger.debug('init: e200INTC module (Interrupt Controller)')

        self.reset(emu)

    def reset(self, emu):
        '''
        Clear out any pending exceptions and restore the machine to it's initial state
        '''
        # Clear out the pending and active interrupts
        self.stack = []
        self.pending = []

        # use instance variable to keep the run loop tight.  this must be only
        # used in one thread.
        self.hasInterrupt = False

        # Default priority level
        self.curlvl = INTC_LEVEL_NONE

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
        self.pending.append(exception)

        # So sort the list to ensure the higher priorities are at the beginning
        self.pending.sort(key=operator.attrgetter('prio'))

        # If the first interrupt in the list is one that can be handled at the
        # current priority level, indicate there is a pending interrupt
        self.hasInterrupt = self.curlvl > self.pending[0].prio

    def checkException(self):
        if self.hasInterrupt:
            # do most costly Interrupt Handling stuff here
            self.handleException()

    def handleException(self):
        '''
        Look for exceptions that should preempt the current state
        '''
        # This is only called if the first pending exception has a higher
        # priority than the current level, so get the first exception and start
        # processing it.l

        # pull the next exception from the prioritized queue.
        newexc = self.pending.pop(0)

        # store the new exception on the stack (pushing the new one in front of
        # the previous)
        self.stack.append(newexc)

        # set ESR/MSR??
        newexc.setupContext(self.emu)

        # set PC from IVOR
        newpc = self.getHandler(newexc)

        # Check if there are any peripheral-specific callbacks for this
        # exception type
        for callback in self._callbacks.get(type(newexc), []):
            callback(newexc)

        logger.debug('PC: 0x%08x (%r)  LVL: %d -> %d  NEWPC: 0x%08x',
                self.emu.getProgramCounter(), newexc, self.curlvl, newexc.prio, newpc)
        self.emu.setProgramCounter(newpc)

        # change self.curlvl
        self.curlvl = newexc.prio

        # Indicate if there are any other pending interrupts that can be
        # processed at the current level
        self.hasInterrupt = self.pending and self.curlvl > self.pending[0].prio

    def addCallback(self, exception, callback):
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
        oldexc = self.stack.pop()

        # If there are still interrupts on the stack then we are returning into
        # another interrupt
        if self.stack:
            curexc = self.stack[-1]
            self.curlvl = curexc.prio
        else:
            self.curlvl = INTC_LEVEL_NONE

        # Now execute any exception cleanup functions that may be attached to
        # this exception
        oldexc.doCleanup()

        # Check if there are any pending exceptions that can be processed
        self.hasInterrupt = self.pending and self.curlvl > self.pending[0].prio

    def isExceptionActive(self, exctype):
        return any(isinstance(e, exctype) for e in self.stack) or \
                any(isinstance(e, exctype) for e in self.pending)

    def findPendingException(self, exctype):
        # Finds and returns all active and pending exceptions of the specified
        # type
        for exc in self.stack:
            if isinstance(exc, exctype):
                yield exc

        for exc in self.pending:
            if isinstance(exc, exctype):
                yield exc
