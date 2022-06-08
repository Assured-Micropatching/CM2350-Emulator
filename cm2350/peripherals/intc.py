import queue
import logging
import threading

from envi.archs.ppc import regs as ppcregs

from ..ppc_vstructs import *
from ..ppc_peripherals import *
from ..intc_exc import ExternalException, INTC_SRC

logger = logging.getLogger(__name__)

__all__  = [
    'INTC',
]


INTC_MAX_SW_INTERRUPTS  = 8
INTC_MAX_INTERRUPTS     = 480
INTC_MIN_PRIO           = 0
INTC_MAX_PRIO           = 15

# A mapping of the software triggered interrupts supported by INTC to the
# correct INTC source vector values
INTC_SSCIR_SRC = (
    INTC_SRC.INTC_SW_0,
    INTC_SRC.INTC_SW_1,
    INTC_SRC.INTC_SW_2,
    INTC_SRC.INTC_SW_3,
    INTC_SRC.INTC_SW_4,
    INTC_SRC.INTC_SW_5,
    INTC_SRC.INTC_SW_6,
    INTC_SRC.INTC_SW_7,
)

# multiply the interrupt source number by this constant to get the hardware
# vector offset
INTC_HWVEC_OFFSET_SIZE  = 0x10

# peripheral register offsets
INTC_MCR_OFFSET         = 0x0000
INTC_CPR_OFFSET         = 0x0008
INTC_IACKR_OFFSET       = 0x0010
INTC_EOIR_OFFSET        = 0x0018
INTC_SSCIR_OFFSET       = 0x0020
INTC_PSR_OFFSET         = 0x0040
INTC_PSR_RANGE          = range(INTC_PSR_OFFSET, INTC_PSR_OFFSET+INTC_MAX_INTERRUPTS)

# Masks and shifts necessary to build the IACKR value
# If MCR[VTES] == 1 then VTBA | INTVEC is shifted left by 1 bit
INTC_IACKR_VTBA_MASK    = (0xFFFFF800, 0xFFFFF000)
INTC_IACKR_VTBA_SHIFT   = (11, 12)
INTC_IACKR_INTVEC_MASK  = (0x000007FC, 0x00000FF8)
INTC_IACKR_INTVEC_SHIFT = (2, 3)


class INTC_MCR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(26)
        self.vtes = v_bits(1)
        self._pad1 = v_const(4)
        self.hven = v_bits(1)

class INTC_CPR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(28)
        self.pri = v_bits(4, 0xF)

class INTC_SSCIRn(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(6)
        self.set = v_bits(1)
        self.clr = v_w1c(1)

class INTC_REGISTERS(PeripheralRegisterSet):
    def __init__(self):
        super().__init__()
        self.mcr        = (INTC_MCR_OFFSET, INTC_MCR())
        self.cpr        = (INTC_CPR_OFFSET, INTC_CPR())

        # The IACKR and EOIR registers can't be emulated with VStructs and is
        # implemented directly in the FlexCAN _getPeriphReg and _setPeriphReg
        # functions below.
        self.sscir      = (INTC_SSCIR_OFFSET, VArray([INTC_SSCIRn() for x in range(INTC_MAX_SW_INTERRUPTS)]))
        self.psr        = (INTC_PSR_OFFSET, v_bytearray(size=INTC_MAX_INTERRUPTS))

    def reset(self, emu):
        super().reset(emu)

        # Manually reset any registers that are VStruct primitive types instead
        # of PeriphRegister objects
        self.psr[:] = b'\x00' * INTC_MAX_INTERRUPTS


class INTC(MMIOPeripheral):
    def __init__(self, emu, mmio_addr):
        # need to hook a MMIO mmiodev at 0xfff38000 of size 0x4000
        super().__init__(emu, 'INTC', mmio_addr, 0x4000, regsetcls=INTC_REGISTERS)

        # Allow other peripherals to add callback functions based on when a
        # specific ExternalInterrupt source is handled
        self._callbacks = {}

        # The MCU INTC peripheral
        self.mcuintc = None

        # Last written IACKR value, in SWVEC mode this hold both the VTBA and
        # IACKR values.  The value saved in this attribute will be normalized
        # when written so that if the MCR[VTES] value changes it will be
        # returned correctly based on
        self.vtba = None
        self._iackr = None

        # The interrupt being currently handled
        self._cur_exc = None

        self._saved_prio = None
        self._delayed_excs = None

        # A mutex to protect some registers if accessed in timer threads
        self._lock = threading.RLock()

        # Install a callback handler for the SSCIR register so when values are
        # written the correct actions can be taken.
        self.registers.vsAddParseCallback('by_idx_sscir', self.sscirUpdate)

        # A callback for the CPR register, so when the priority changes any
        # delayed interrupts that have been saved will be re-queued.
        self.registers.vsAddParseCallback('cpr', self.cprUpdate)

    def init(self, emu):
        # Connect to the MCU interrupt controller
        self.mcuintc = emu.modules.get('MCU_INTC')
        self.mcuintc.registerExtINTC(self)

        # Now register the external exception callback handler
        self.mcuintc.addCallback(ExternalException, self.externalExcCallback)

        super().init(emu)

    def reset(self, emu):
        # Reset the IACKR/current interrupt values
        self.vtba = 0
        self._iackr = 0
        self._cur_exc = None

        # Clear out the interrupt priority LIFO and delayed peripheral interrupt
        # queue
        self._saved_prio = []
        self._delayed_excs = []

    def _getPeriphReg(self, offset, size):
        # It's easier to just lock all peripheral access for this peripheral
        with self._lock:
            # The IACKR and EOIR registers need custom handling
            if offset == INTC_IACKR_OFFSET:
                if self.registers.mcr.hven == 0:
                    # In SWVEC mode, trigger the "interrupt acknowledge signal" now
                    self._signalIACK()
                return e_bits.buildbytes(self._iackr, 4, bigend=self.emu.getEndian())

            elif offset == INTC_EOIR_OFFSET:
                # Reading EOIR has no side effects and always returns all 0's
                return b'\x00\x00\x00\x00'

            else:
                return super()._getPeriphReg(offset, size)

    def _setPeriphReg(self, offset, bytez):
        # It's easier to just lock all peripheral access for this peripheral
        with self._lock:
            # The IACKR and EOIR registers need custom handling
            if offset == INTC_IACKR_OFFSET:
                # Save the IACKR[VTBA] value
                vtba = e_bits.parsebytes(bytez, 0, 4, bigend=self.emu.getEndian()) & INTC_IACKR_VTBA_MASK[vtes]
                self.vtba = vtba >> INTC_IACKR_VTBA_SHIFT[vtes]

                # Update the saved IACKR value with the new VTBA value
                intvec = self._iackr & ~INTC_IACKR_VTBA_MASK[vtes]
                self._iackr = vtba | intvec

            elif offset == INTC_EOIR_OFFSET:
                # The value written to EOIR doesn't matter, but signal the end of
                # the interrupt
                with self._lock:
                    self._signalEOIR()

            else:
                super()._setPeriphReg(offset, bytez)

    def sscirUpdate(self, thing, idx, size):
        if self.registers.sscir[idx].set:
            # If the SSCIRn[SET] bit is set, queue an exception and clear the
            # SET bit (it should always read 0)
            self.registers.sscir[idx].set = 0
            self.registers.sscir[idx].vsOverrideValue('clr', 1)
            self.emu.queueException(ExternalException(INTC_SSCIR_SRC[idx]))

    def cprUpdate(self, thing):
        # Any manual change to the CPR value should cause the potential delayed
        # exceptions to be re-evaluated
        self._checkDelayedExcs()

    def _rfi(self):
        # check for any delayed exceptions now
        with self._lock:
            self._checkDelayedExcs()

        # And clear the current exception
        self._cur_exc = None

    def _checkDelayedExcs(self):
        # If there are any delayed interrupts that are now a higher priority
        # than the current level, queue them
        #
        # iterate backwards over the list so we can pop any exceptions from the
        # list that need to be re-queued
        saved_excs = self._delayed_excs

        # Clear the current set of delayed exceptions because anything that
        # can't be handled right now may get re-queued
        self._delayed_excs = []
        for exc in saved_excs:
            if self.shouldHandle(exc):
                self.emu.queueException(exc)

    def _signalEOIR(self):
        try:
            self.registers.cpr.pri = self._saved_prio.pop()
        except IndexError:
            # Set CPR to the default priority (it should already be this)
            self.registers.cpr.pri = INTC_MIN_PRIO

        # Any delayed external interrupts may be able to be processed now
        self._checkDelayedExcs()

    def _signalIACK(self):
        """
        A utility function that handles the "interrupt acknowledge signal" that
        is triggered in different ways depending on MCR[HVEN].

        In HWVEC mode the "interrupt acknowledge signal" happens when the
        handler address is determined and executed, in SWVEC mode it happens
        when the IACKR register is read.
        """
        self._saved_prio.append(self.registers.cpr.pri)
        self.registers.cpr.pri = self._getExcPrio(self._cur_exc)

    def getHandler(self, exception):
        '''
        Based on the configuration of the INTC and the exception priority,
        return the correct Next Instruction Address.
        '''
        # Save the current exception being handled
        self._cur_exc = exception

        # the MCR[VTES] value is needed to set the correct IACKR value
        vtes = self.registers.mcr.vtes

        ipvr = self.emu.getRegister(ppcregs.REG_IVPR) & 0xFFFF0000
        intsrc = int(exception.source)

        # Use the current exception's source to calculate INTVEC
        vtba = (self.vtba << INTC_IACKR_VTBA_SHIFT[vtes]) & INTC_IACKR_VTBA_MASK[vtes]
        intvec = (intsrc * INTC_HWVEC_OFFSET_SIZE) << INTC_IACKR_INTVEC_SHIFT[vtes]
        self._iackr = vtba | intvec

        if self.registers.mcr.hven:
            # In HWVEC mode, trigger the "interrupt acknowledge signal" now
            self._signalIACK()

            # Return IPVR + the calculated hardware int vector offset (not the
            # same things as the IACKR value) for some reason?
            #   IPVR | source << 4
            return ipvr | (intsrc << 4)

        else:
            # Return the standard IPVR + IVOR4 offset
            return ipvr | (self.emu.getRegister(exception.__ivor__) & 0x0000FFFC)

    def _getExcPrio(self, exception):
        return self.registers.psr[exception.source] & INTC_MAX_PRIO

    def shouldHandle(self, exception):
        # This function can be called from timer threads, so wrap the PSR and
        # CPR accesses in a lock
        with self._lock:
            exc_pri = self._getExcPrio(exception)
            ret = exc_pri >= self.registers.cpr.pri
            if not ret:
                logger.debug('INT priority %d too low (CPR: %d)', exc_pri, self.registers.cpr.pri)
                # delayed this exception until later
                self._delayed_excs.append(exception)

        return ret

    def addCallback(self, src, callback):
        if src not in self._callbacks:
            self._callbacks[src] = [callback]
        else:
            self._callbacks[src].append(callback)

    def externalExcCallback(self, exception):
        # Callback handler for external exceptions to see if there are any
        # peripheral interrupt-specific callback handlers installed
        for callback in self._callbacks.get(exception.source, []):
            callback(exception)
