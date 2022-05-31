import time
import threading

import logging
logger = logging.getLogger(__name__)


# Timer objects should not normally be created manually so don't export the
# Timer class by default.
__all__ = ['EmulationTime']


class EmuTimer:
    '''
    An object to enable tracking the amount of time left until a specific
    action is supposed to happen.

    EmuTimer objects are created from the EmulationTime.registerTimer() function.
    '''
    def __init__(self, emutime, name, callback, freq=None, period=None):
        '''
        Saves timer configuration information and leaves the timer disabled.

        Arguments:
            emutime     The EmulationTime object, this is necessary so the
                        timer object can determine what the system time is
                        and how much emulation time needs to elapse before
                        the timer should expire.
            name        The name of the timer. Useful for debugging.
            callback    The function to call when the timer expires.
            freq        (optional) The clock frequency that the timer uses to
                        determine the duration of the timer.
            period      (optional) The number of clock ticks that should
                        elapse before the timer expires.

        If the freq and period parameters are not provided during timer
        creation then they should be provided when the start() function is
        called.
        '''
        self._emutime = emutime
        self.name = name
        self._callback = callback

        # Frequency and period can either be set when the timer is created if
        # those are fixed, or later when the timer is started.
        self.freq = freq
        self.period = period

        # When a timer is not running the target is None
        self.target = None

    def start(self, freq=None, period=None):
        '''
        Start a timer running right now.

        Uses the emutime object's systime() function call to determine what the current time is.

        Arguments:
            freq        (optional) The clock frequency that the timer uses to
                        determine the duration of the timer.
            period      (optional) The number of clock ticks that should
                        elapse before the timer expires.

        If the freq and period parameters were provided when the timer object
        was created through the EmulationTime.registerTimer() function then
        those parameters are not required when start() is called.
        '''
        now = self._emutime.systime()

        # If the freq or period params are supplied, override whatever the
        # default values may be
        if freq is not None:
            self.freq = freq

        if period is not None:
            self.period = period

        # frequency and period must be set for a timer to be started
        if self.freq and self.period:
            # Determine how much time it should take to reach the timeout period
            # at the specified frequency
            duration = self.period / self.freq
            self.target = now + duration
            logger.debug('[%s] %s timer started: %s @ %s Hz == %s', now, self.name, self.period, self.freq, duration)
        else:
            # If either frequency or period is 0 then ensure that the timer is
            # not running
            self.target = None

            err = 'Cannot start %s timer: %s @ %s Hz' % (self.name, self.period, self.freq)
            raise Exception(err)

        # notify the emutime obj that a timer has been updated
        self._emutime.timerUpdated()

    def callback(self):
        '''
        Execute the registered callback function.

        This marks the timer as no longer running and executes the regsitered
        callback function if one has been registered.
        '''
        self.target = None
        if self._callback:
            self._callback()

    def stop(self):
        '''
        Stop a timer.

        This method is meant to be called by code that registered the original timer.
        '''
        now = self._emutime.systime()
        logger.debug('[%s] %s timer stopped', now, self.name)

        self.target = None

        # Because this is the function intended to be used outside of the
        # EmulationTime object, notify the emutime obj that a timer has been
        # updated
        self._emutime.timerUpdated()

    def running(self):
        '''
        Returns an indication of if a timer has been started or not.
        '''
        return self.target is not None

    def time(self):
        '''
        Return the amount of time remaining before this timer should expire as
        a floating point value.
        '''
        if self.target is None:
            return 0.0
        else:
            return self.target - self._emutime.systime()

    def ticks(self):
        '''
        Return the number of ticks remaining before this timer should expire.

        The value returned is the number of clock ticks at the frequency
        configured for this timer that remain. This is calculated based on the
        current system time returned by EmulationTime.systime().
        '''
        return int(self.time() * self.freq)

    def expired(self):
        '''
        Returns a bool indicating if the timer is running and has expired.
        '''
        return self.running() and self._emutime.systime() >= self.target

    def __lt__(self, other):
        '''
        comparison function so a list of timers can easily be sorted
        '''
        return self.running() and self.target < other.target

    def __eq__(self, other):
        '''
        comparison function so a list of timers can easily be sorted
        '''
        return self.target == other.target


class EmulationTime:
    '''
    An object that correlates an emulator's run time to the platform's system
    time, and to allow the creation and management of multiple timers with
    callbacks, and allows the emulator time to be halted and resumed.
    '''

    def __init__(self, systime_scaling=1.0):
        '''
        Creates a separate thread to track which timer has the least amount of
        time before it expires and to calls the timer's callback function when
        a timer expires. The EmulationTime object is created with time halted.

        Arguments:
            systime_scaling     (optional) Default is 1.0 which means that the
                                system time as reported by time.time() is not
                                adjusted. If time should move slower for the
                                emulated system a lower value should be used.
        '''
        self._systime_scaling = systime_scaling

        self._timers = []

        # Lock to allow adding and sorting timers from different threads of
        # execution.
        self._timer_lock = threading.Lock()

        self._timer_update = threading.Condition()
        self._stop = threading.Event()

        # Thread to run the timers. This thread should get cleaned up properly
        # when the EmulationTime object is deleted
        #
        # For some bizzare reason ipython just absolutely will hang up
        # when exiting unless these are marked as daemon threads. There
        # is some sort of check happening in check in
        # /usr/lib/python3.9/threading.py that is run before the atexit
        # handler and is halting cleanup. This is some sort of weird
        # behavior with ipython + SimpleQueue + Threads. However we have
        # no need to add "task tracking" to this design so we don't want
        # to add in the extra complexity of using full Queues.
        #
        # So to work around this we just set the daemon flag, even
        # though I don't like it.
        args = {
            'name': 'tb',
            'target': self._tb_run,
            'daemon': True,
        }
        self._tb_thread = threading.Thread(**args)

        self._tb_thread.start()

        # Variables to let us track how long the emulated system has been
        # running
        #self._sysoffset = time.time()
        self._sysoffset = None

        # Set _breakstart to the starting offset because we are starting the
        # system time in halted mode.
        self._breakstart = self._sysoffset

        self.freq = None

    def __del__(self):
        self.haltEmuTimeThread()

    def shutdown(self):
        '''
        Stops the timer management thread and cleanly exits the system.  This
        is done to ensure that when an EmulationTime object is deleted that the
        callback handlers do not continue to run which can cause weird behavior,
        especially during testing.
        '''
        # Stop and deallocate all the timers
        if self._tb_thread:
            self._stop.set()

            # Stop all of the timers
            if self._timers:
                with self._timer_update:
                    for t in self._timers:
                        # This will cause a timer to be "stopped"
                        t.target = None

                    # Signal the timer re-check condition as well which will force the
                    # thread to re-evaluate which timer is next and it will notice it should
                    # halt
                    self._timer_update.notify()
                self._timers = []

            # Wait for the thread to exit
            self._tb_thread.join(1)

            if self._tb_thread.is_alive():
                logger.error('Failed to stop system time thread')
            else:
                self._tb_thread = None

    def enableTimebase(self, start_paused=False):
        '''
        Start a timebase
        '''
        self._sysoffset = time.time()
        if start_paused:
            # Set breakstart to the current system time offset which will cause
            # any reads of the system time to indicate that no time has elapsed
            self._breakstart = self._sysoffset
        else:
            # Set breakstart to 0 so the timebase is running
            self._breakstart = 0
        self.timerUpdated()

    def disableTimebase(self):
        '''
        Stop a timebase
        '''
        self._sysoffset = None
        self._breakstart = None
        self.timerUpdated()

    def resume_time(self):
        '''
        Resume tracking the amount of time passing for the emulator, but only
        if system time has already been started.
        '''
        if self._sysoffset is not None:
            halted_time = time.time() - self._breakstart
            self._sysoffset += halted_time

            # Clear the breakstart so when halted systime() can use breakstart to
            # return the actual running time.
            self._breakstart = 0
            self.timerUpdated()

    def halt_time(self):
        '''
        Pause tracking the amount of time passing for the emulator.

        This also stops timers from expiring.
        '''
        if self._sysoffset is not None:
            self._breakstart = time.time()
            self.timerUpdated()

    def systimeRunning(self):
        '''
        Returns an indication of if the primary system time is runnning or
        paused.  Useful for testing and debugging.
        '''
        return bool(self._sysoffset and not self._breakstart)

    def systimeReset(self):
        '''
        Handle a system reset. This will return the _sysoffset and _breakstart
        values to their default (disabled) state but will not will remove any
        peripheral timers because those should be created only once during
        initialization and then reconfigured to their correct default states
        when the peripheral module's reset() functions are called.
        '''
        self.disableTimebase()

    def setSystemFreq(self, freq):
        '''
        Set the system clock frequency.

        This is not a configuration parameter because it is not expected that
        the system clock speed can be known at object creation time, and also
        because it is expected that the system clock frequency may change as
        peripheral configurations are changed.

        The system clock frequency is only required to determine the number of
        clock ticks that have elapsed while the system has been running.
        '''
        self._systemFreq = freq

    def getSystemFreq(self):
        '''
        Returns the configured system clock frequency.
        '''
        return self._systemFreq

    def systime(self):
        '''
        Return the amount of time the emulator has been running (not halted).

        This scales the result based on the systime_scaling parameter provided
        during initialization.
        '''
        if self._sysoffset is None:
            return 0.0

        now = time.time()
        halted_time = 0

        # Make sure to take into account the breakstart offset if the system
        # is halted
        if self._breakstart:
            halted_time = now - self._breakstart

        elapsed_time = now - self._sysoffset - halted_time

        return elapsed_time * self._systime_scaling

    def systicks(self):
        '''
        Uses the configured system clock frequency to determine how many clock
        ticks have elapsed while the system has been running.
        '''
        # Return the system time in the number of cycles have happened
        return int(self.systime() * self.getSystemFreq())

    def registerTimer(self, name, callback, freq=None, period=None):
        '''
        Used by emulated peripherals and other components to create a timer
        that will be tracked and can be configured, started or stopped by
        those components.
        '''
        new_timer = EmuTimer(self, name, callback, freq=freq, period=period)
        with self._timer_lock:
            self._timers.append(new_timer)
        return new_timer

    def timerUpdated(self):
        '''
        A utility that allows timers to notify the core emulation thread that
        they have been updated.
        '''
        with self._timer_update:
            self._timer_update.notify()

    def getNextEvent(self):
        '''
        Return the amount of time to wait before the next event should occur
        '''
        # If system time is halted just return None
        if self._breakstart:
            return None

        # Ensure that the timer with the earliest expiry is at the front
        with self._timer_lock:
            self._timers.sort()

        try:
            next_timer = self._timers[0]
            if next_timer.running():
                return next_timer.time()
        except IndexError:
            pass

        return None

    def checkTimerExpired(self):
        '''
        Checks if the next timer scheduled to expire has expired or not.  If it
        has expired the EmuTimer object is returned.
        '''
        # If system time is halted timers can't expire
        if self._breakstart:
            return False

        try:
            next_timer = self._timers[0]
            if next_timer.expired():
                return next_timer
        except IndexError:
            pass

        return False

    def _handle_expired(self, expired_timer):
        '''
        Call the timer's callback handler
        '''
        logger.debug('[%s] %s expired', self.systime(), expired_timer.name)
        expired_timer.callback()

    def _tb_run(self):
        '''
        Timer management thread.
        '''
        # When we first start set the next timer event to None which will cause
        # self._timer_update.wait() to block forever until we are notified that
        # there has been an update
        next_event = None

        with self._timer_update:
            while not self._stop.is_set():
                # Wait until the next scheduled event, or until a timer update
                # occurs.
                out = self._timer_update.wait(next_event)

                # If the next scheduled timer has expired, handle that
                # expiration
                expired_timer = self.checkTimerExpired()
                if expired_timer:
                    self._handle_expired(expired_timer)

                # Get the next scheduled timer/event to wait for
                next_event = self.getNextEvent()
