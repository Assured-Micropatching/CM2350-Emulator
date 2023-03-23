import threading

import envi.bits as e_bits

from ..ppc_vstructs import *
from ..ppc_peripherals import *
from ..intc_exc import MceDataReadBusError, MceWriteBusError, ResetException, INTC_EVENT

import logging
logger = logging.getLogger(__name__)

__all__  = [
    'SWT',
]


# SWT Peripheral Register offsets
SWT_MCR_OFFSET = 0x0000
SWT_IR_OFFSET  = 0x0004
SWT_TO_OFFSET  = 0x0008
SWT_WN_OFFSET  = 0x000C
SWT_SR_OFFSET  = 0x0010
SWT_CO_OFFSET  = 0x0014
SWT_SK_OFFSET  = 0x0018


# Some register reads and writes must be protected to ensure they are threadsafe
# - MCR
# - IR
SWT_THREAD_PROT_OFFSETS = (
    SWT_MCR_OFFSET,
    SWT_IR_OFFSET,
)


# Some registers can be locked against writes
SWT_LOCKABLE_OFFSETS = (
    SWT_MCR_OFFSET,
    SWT_TO_OFFSET,
    SWT_WN_OFFSET,
    SWT_SK_OFFSET,
)


# The MCR[ITR] field has been renamed as MCR[TIF] to allow the MCR register to
# be used as the isrflags register in the MMIOPeripheral class initialization.
class SWT_MCR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.map = v_bits(8, 0xFF)
        self._pad = v_const(14)
        self.key = v_bits(1)
        self.ria = v_bits(1, 1)
        self.wnd = v_bits(1)
        self.tif = v_bits(1)
        self.hlk = v_bits(1)
        self.slk = v_bits(1)
        self.csl = v_bits(1, 1)
        self.stp = v_bits(1)
        self.frz = v_bits(1, 1)
        self.wen = v_bits(1, 1)


class SWT_TO(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.wto = v_bits(32, 0x0005fcd0)


class SWT_IR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad = v_const(31)
        self.tif = v_w1c(1)


class SWT_WN(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.wst = v_bits(32)


class SWT_SR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad = v_const(16)
        self.wsc = v_bits(16)


class SWT_SK(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad = v_const(16)
        self.sk = v_bits(16)


class SWT_REGISTERS(PeripheralRegisterSet):
    def __init__(self):
        super().__init__()

        self.mcr       = (SWT_MCR_OFFSET, SWT_MCR())
        self.ir        = (SWT_IR_OFFSET, SWT_IR())
        self.to        = (SWT_TO_OFFSET, SWT_TO())
        self.wn        = (SWT_WN_OFFSET, SWT_WN())
        self.sr        = (SWT_SR_OFFSET, SWT_SR())
        self.sk        = (SWT_SK_OFFSET, SWT_SK())


# Only one possible type of interrupt event for the SWT peripheral
SWT_INT_EVENTS = {
    'tif': INTC_EVENT.SWT,
}


class SWT(MMIOPeripheral):
    '''
    This is the SWT (Software Watchdog) Controller.
    '''
    def __init__(self, emu, mmio_addr):
        # need to hook a MMIO mmiodev at 0xfff38000 of size 0x4000
        super().__init__(emu, 'SWT', mmio_addr, 0x4000,
                regsetcls=SWT_REGISTERS,
                isrstatus='ir', isrflags='mcr', isrevents=SWT_INT_EVENTS)

        self.registers.vsAddParseCallback('sr', self.processServiceKey)
        self.registers.vsAddParseCallback('mcr', self.updateWatchdog)
        self.registers.vsAddParseCallback('sk', self.setServiceKey)

        # Make a lock to protect any resources accessed by the watchdog callback
        # handler and the main emulator:
        #   - MCR[ITR]
        #   - IR[TIF]
        #   - _timeout_count (only used in callback handler)
        self._wdogHandlerLock = threading.RLock()

        # watchdog timer
        self.watchdog = None

        # Attributes used to track the service keys, unlocking and watchdog
        # timeouts
        self._key = None
        self._slk_idx = None
        self._sk_idx = None
        self._timeout_count = None
        self._slk_keys = None
        self._sks = None

    def _getPeriphReg(self, offset, size):
        """
        Customized method to allow reading the current watchdog tick count
        from a function instead of trying to fit it into a VStruct/Register
        style which would add a lot of unnecessary overhead.
        """
        if offset == SWT_CO_OFFSET:
            # If the offset is for the CO register, return the watchdog timer
            # tick count instead of reading a register
            return e_bits.buildbytes(self.watchdog.ticks(), 4, bigend=self.emu.getEndian())

        elif offset == SWT_SR_OFFSET:
            # Reads from the service register should always return 0
            return b'\x00\x00\x00\x00'

        else:
            # Use the normal method
            try:
                # If this read is for an offset that needs to be protected
                # against accesses from the watchdog timer, lock the mutex
                # before calling the normal _getPeriphReg() function.
                if offset in SWT_THREAD_PROT_OFFSETS:
                    with self._wdogHandlerLock:
                        return super()._getPeriphReg(offset, size)
                else:
                    return super()._getPeriphReg(offset, size)

            except MceDataReadBusError as exc:
                with self._wdogHandlerLock:
                    # if a BUS ERROR happens and MCR[RIA] is set it should generate
                    # a reset if the watchdog is enabled
                    if self.registers.mcr.ria and self.registers.mcr.wen:
                        raise ResetException()
                    else:
                        raise exc

    def _setPeriphReg(self, offset, bytez):
        """
        Customized method to set SWT peripheral register because this class
        has some registers shouldn't be able to be written when SWT is "locked"
        """
        if self.locked():
            # If the offset matches one of the registers that are locked against
            # writes raise a RESET exception if MCR[RIA] is set, otherwise raise
            # the normal BUS ERROR that is raised by
            # ppc_vstructs.ReadOnlyRegister()
            if offset in SWT_LOCKABLE_OFFSETS:
                if self.registers.mcr.ria and self.registers.mcr.wen:
                    raise ResetException()
                else:
                    raise MceWriteBusError()

        # If not locked, or not one of the locked registers, use the normal set
        # _setPeriphReg function, if a write error occurs, change to a RESET if
        # MCR[RIA] and MCR[WEN] are set.
        try:
            # If this read is for an offset that needs to be protected against
            # accesses from the watchdog timer, lock the mutex before calling
            # the normal _getPeriphReg() function.
            if offset in SWT_THREAD_PROT_OFFSETS:
                with self._wdogHandlerLock:
                    super()._setPeriphReg(offset, bytez)
            else:
                super()._setPeriphReg(offset, bytez)

        except MceWriteBusError as exc:
            with self._wdogHandlerLock:
                # if a BUS ERROR happens and MCR[RIA] is set it should generate
                # a reset if the watchdog is enabled
                if self.registers.mcr.ria and self.registers.mcr.wen:
                    raise ResetException()
                else:
                    raise exc

    def init(self, emu):
        """
        SWT initialization
        """
        # Create the watchdog timer before initializing the SWT peripheral and
        # registers
        self.watchdog = emu.registerTimer('WDT', self.handleTimeout)

        # Now finish initialization
        super().init(emu)

    def reset(self, emu):
        """
        Return the SWT peripheral to a reset state
        """
        # Reset the peripheral registers
        super().reset(emu)

        # Return the keys and timeout count back to their defaults
        self._key = 0
        self._slk_idx = 0
        self._sk_idx = 0
        self._timeout_count = 0

        # Values to track unlocking the softlock bit
        self._slk_keys = (0xC520, 0xD928)

        # Default service keys
        self._sks = (0xA602, 0xB480)

        # The default peripheral register values are set when they are created,
        # call updateWatchdog() manually to ensure that the watchdog is running
        # if the default value of MCR[WEN] is 1 (which it is)
        self.updateWatchdog()

    def locked(self):
        # MCR is accessed by the callback handler so protect these checks
        with self._wdogHandlerLock:
            return self.registers.mcr.hlk or self.registers.mcr.slk

    def handleTimeout(self):
        # This watchdog callback handler may execute from the timer thread's
        # context, so wrap any shared SIU data access in a mutex
        with self._wdogHandlerLock:
            # the MCR[ITR] field has been renamed MCR[TIF] to make the standard
            # MMIOPeripheral._eventRequest() function work as expected.
            if self.registers.mcr.tif and not self._timeout_count:
                self._timeout_count = 1

                # The watchdog timer should be restarted
                self.restartWatchdog()

                # Indicate a SWT interrupt is requested
                self.event('tif', 1)
            else:
                self.emu.queueException(ResetException())

                # Update the ECSM event reason
                self.emu.ecsm.swtReset()

    def restartWatchdog(self):
        # Reset the watchdog service key sequence back to the beginning
        self._sk_idx = 0

        # Generate the next set of service keys
        self.updateServiceKeys()

        with self._wdogHandlerLock:
            csl = self.registers.mcr.csl

        if csl:
            freq = self.emu.fmpll.extal
        else:
            freq = self.emu.siu.f_periph()

        # The SWT duration should be the value of TO (or 0x100 if TO is smaller)
        ticks = max(self.registers.to.wto, 0x100)
        self.watchdog.start(freq=freq, ticks=ticks)

    def stopWatchdog(self):
        self.watchdog.stop()

    def updateServiceKeys(self):
        with self._wdogHandlerLock:
            key = self.registers.mcr.key

        if key:
            # "generate" new keys from the current SK value
            key0 = self._key
            key1 = ((17 * key0) + 3) & 0xFFFF
            key2 = ((17 * key1) + 3) & 0xFFFF
            self._sks = (key1, key2)
        else:
            # Reset the key back to 0
            self._key = 0
            self._sks = (0xA602, 0xB480)

    def updateWatchdog(self, thing=None):
        with self._wdogHandlerLock:
            wen = self.registers.mcr.wen
        # Now disable or enable the watchdog
        if wen:
            self.restartWatchdog()
        else:
            self.stopWatchdog()

    def isValidUnlockKey(self, key):
        if key == self._slk_keys[self._slk_idx]:
            self._slk_idx += 1
            if self._slk_idx == 2:
                self._slk_idx = 0
                with self._wdogHandlerLock:
                    self.registers.mcr.slk = 0

            # The key is a valid soft unlock value
            return True
        else:
            return False

    def isValidServiceKey(self, key):
        if key == self._sks[self._sk_idx]:
            self._sk_idx += 1

            # keep track of the key that was just written, if MCR[KEY] is set
            # this will ensure the correct values are generated for the next set
            # of service keys
            self._key = key

            if self._sk_idx == 2:
                self.restartWatchdog()

            # The key was accepted
            return True
        else:
            return False

    def processServiceKey(self, thing):
        key = self.registers.sr._vs_values['wsc']._vs_value

        # Check for the soft unlock keys, the reference manual states that the
        # unlock sequence can be written at any time, so don't generate bus
        # when valid unlock keys are written even if if HLK is set or WEN is
        # clear.
        if self.isValidUnlockKey(key):
            return

        with self._wdogHandlerLock:
            # If watchdog is not running there is nothing else to do
            if not self.registers.mcr.wen:
                return

            # When the watchdog is running and the window mode is set, writes
            # outside of the allowed window should generate invalid access errors
            if self.registers.mcr.wnd and self.registers.wn.wst <= self.watchdog.ticks():
                # If the MCR[RIA] bit is set invalid memory accesses to the SWT
                # peripheral should generate a system reset
                if self.registers.mcr.ria:
                    raise ResetException()
                else:
                    raise MceWriteBusError()

        # Check if this is a valid service key
        self.isValidServiceKey(key)

    def setServiceKey(self, thing):
        with self._wdogHandlerLock:
            # The service key can only be set when the watchdog is disabled
            if not self.registers.mcr.wen and self.registers.mcr.key:
                self._key = self.registers.sk.sk
