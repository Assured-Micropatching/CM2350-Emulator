import time
import threading

import logging
logger = logging.getLogger(__name__)


# Timer objects should not normally be created manually so don't export the
# Timer class by default.
__all__ = [
    'EmuTimer',
    'EmuTimeCore',
    'ScaledEmuTimeCore',
]


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
        self._sysfreq_to_freq = None
        self.period = period

        # When a timer is not running the target is None
        self.target = None

        # Used to track paused timers, only used by the pause and resume
        # functions
        self._remaining = None

    def start(self, freq=None, period=None):
        '''
        Start a timer running right now.

        Uses the emutime object's systicks() function call to determine what the
        current system time is.

        Arguments:
            freq        (optional) The clock frequency that the timer uses to
                        determine the duration of the timer.
            period      (optional) The number of clock ticks that should
                        elapse before the timer expires.

        If the freq and period parameters were provided when the timer object
        was created through the EmulationTime.registerTimer() function then
        those parameters are not required when start() is called.
        '''
        # If the freq or period params are supplied, override whatever the
        # default values may be
        if freq is not None:
            self.freq = freq
        elif self.freq is None:
            # If no frequency was provided when the timer was created or in this
            # start function, use the current timebase frequency
            self.freq = self._emutime.getSystemFreq()

        if period is not None:
            self.period = period

        now = self._emutime.systicks()

        # Ensure that the remaining time is not set
        self._remaining = None

        # frequency and period must be set for a timer to be started
        if self.freq and self.period:
            # Determine how much time it should take to reach the timeout period
            # at the specified frequency
            duration = self.period / self.freq
            self.target = now + duration
            logger.debug('[%s] %s timer started: %s @ %s Hz == %s',
                    now, self.name, self.period, self.freq, duration)
        else:
            # If either frequency or period is 0 then ensure that the timer is
            # not running
            self.target = None

            err = 'Cannot start %s timer: %s @ %s Hz' % (self.name, self.period, self.freq)
            raise Exception(err)

        # Determine how many system ticks occur for every tick of this timer
        self._sysfreq_to_freq = self._emutime.getSystemFreq() / self.freq
        duration = int(self.period * self._sysfreq_to_freq)
        self.target = now + duration
        logger.debug('[%d] %s timer started: %d @ %d Hz == %d', now, self.name, self.period, self.freq, duration)

        # notify the emutime obj that a timer has been updated
        self._emutime.timerUpdated()

    def callback(self):
        '''
        Execute the registered callback function.

        This marks the timer as no longer running and executes the registered
        callback function if one has been registered.
        '''
        self.target = None
        if self._callback:
            self._callback()

    def stop(self):
        '''
        Stop a timer.
        '''
        now = self._emutime.systicks()
        logger.debug('[%d] %s timer stopped', now, self.name)

        self.target = None
        self._remaining = None

        # Because this is the function intended to be used outside of the
        # EmulationTime object, notify the emutime obj that a timer has been
        # updated
        self._emutime.timerUpdated()

    def pause(self):
        '''
        Temporarily pause a timer.
        '''
        now = self._emutime.systicks()
        self._remaining = self.target - now
        logger.debug('[%d] %s timer paused (%d remaining)', now, self.name, self._remaining)
        self.target = None

        # Because this is the function intended to be used outside of the
        # EmulationTime object, notify the emutime obj that a timer has been
        # updated
        self._emutime.timerUpdated()

    def resume(self):
        '''
        Resume a paused timer.
        '''
        now = self._emutime.systicks()
        logger.debug('[%d] %s timer resumed (%d remaining)', now, self.name, self._remaining)

        self.target = now + self._remaining
        self._remaining = None

        # Because this is the function intended to be used outside of the
        # EmulationTime object, notify the emutime obj that a timer has been
        # updated
        self._emutime.timerUpdated()

    def time(self):
        '''
        Return the amount of seconds remaining before this timer should expire
        '''
        if self.target is None:
            return None

        return self.freq / self.ticks()

    def ticks(self):
        '''
        Return the number of timer ticks (not system ticks) remaining before
        this timer should expire.
        '''
        if self.target is None:
            return None

        systicks_remaining = self.target - self._emutime.systicks()
        return int(systicks_remaining / self._sysfreq_to_freq)

    def running(self):
        '''
        Returns an indication of if a timer has been started or not.
        '''
        return self.target is not None

    def expired(self):
        '''
        Returns a bool indicating if the timer is running and has expired.
        '''
        return self.running() and self._emutime.systicks() >= self.target

    def __lt__(self, other):
        '''
        comparison function so a list of timers can easily be sorted. Timers
        that aren't running get moved to the end of the list.
        '''
        if not self.running():
            return False
        elif not other.running():
            return True

        return self.target < other.target

    def __eq__(self, other):
        '''
        comparison function so a list of timers can easily be sorted
        '''
        return self.target == other.target


class EmuTimeCore:
    '''
    The base system time class that defines the functionality of any
    EmulationTime child class.
    '''
    def __init__(self, **kwargs):
        # List of active timers in the system
        self._timers = []

        self._ticks = 0

        # Track the number of ticks that have elapsed
        self.freq = None

    def __del__(self):
        # Stop all the timers, probably not necessary
        for t in self._timers:
            t.stop()

    def tick(self):
        self._ticks += 1

        # Determine if any timers should expire
        expired_timer = self.getExpiredTimer()
        if expired_timer is not None:
            self._handle_expired(expired_timer)

    def resume(self):
        '''
        placeholder for the scaled time based timer emulation core
        '''
        pass

    def halt(self):
        '''
        placeholder for the scaled time based timer emulation core
        '''
        pass

    def systimeReset(self):
        '''
        Reset the timebase back to 0 and clear the system frequency.
        Also stop all timers (but don't delete them, there's no need to force
        modules to re-create their timers).
        '''
        self._ticks = 0
        self._systemFreq = None
        self.timerUpdated()

    def setSystemFreq(self, freq):
        self._systemFreq = float(freq)

    def getSystemFreq(self):
        if self._systemFreq is None:
            return 0.0
        else:
            return self._systemFreq

    def systime(self):
        '''
        Return the amount of time "real" time the emulator has been running
        based on the number of ticks that have occured and the current system
        frequency.
        '''
        return self.systicks() * self._systemFreq

    def systicks(self):
        return self._ticks

    def registerTimer(self, name, callback, freq=None, period=None):
        '''
        Used by emulated peripherals and other components to create a timer
        that will be tracked and can be configured, started or stopped by
        those components.
        '''
        new_timer = EmuTimer(self, name, callback, freq=freq, period=period)
        self._timers.append(new_timer)
        return new_timer

    def timerUpdated(self):
        '''
        Update the timer list for which timer/event should expire first.
        '''
        self._timers.sort()

    def _handle_expired(self, expired_timer):
        '''
        Call the timer's callback handler
        '''
        logger.debug('[%d] %s expired', self.systicks(), expired_timer.name)
        expired_timer.callback()

        # After the timer callback has been run, this timer should be placed at
        # the end of the queue
        self._emutime.timerUpdated()


class ScaledEmuTimeCore(EmuTimeCore):
    '''
    An object that correlates an emulator's run time to the platform's system
    time, and to allow the creation and management of multiple timers with
    callbacks, and allows the emulator time to be halted and resumed.
    '''
    def __init__(self, systime_scaling=1.0, **kwargs):
        '''
        Creates a separate thread to track which timer has the least amount of
        time before it expires and to calls the timer's callback function when
        a timer expires. The EmuTimeCore object is created with time halted.

        Arguments:
            systime_scaling     (optional) Default is 1.0 which means that the
                                system time as reported by time.time() is not
                                adjusted. If time should move slower for the
                                emulated system a lower value should be used.
        '''
        EmuTimeCore.__init__(self)

        self._systime_scaling = systime_scaling

        self._sysoffset = time.time()
        self._breakstart = self._sysoffset

        # Because the timers will be maanged by a separate thread
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

    def __del__(self):
        self.haltEmuTimeThread()

    def shutdown(self):
        '''
        Stops the timer management thread and cleanly exits the system.  This
        is done to ensure that when an EmuTimeCore object is deleted that the
        callback handlers do not continue to run which can cause weird behavior,
        especially during testing.
        '''
        # Stop and deallocate all the timers
        if hasattr(self, '_tb_thread') and self._tb_thread:
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

    def systimeRunning(self):
        '''
        Returns an indication of if the primary system time is running or
        paused. Useful for testing and debugging.
        '''
        return self._breakstart is None

    def tick(self):
        '''
        keep track of ticks but don't check for expiration here
        '''
        self._ticks += 1

    def resume_time(self):
        '''
        Resume tracking the amount of time passing for the emulator, but only
        if system time has already been started.
        '''
        halted_time = time.time() - self._breakstart
        self._sysoffset += halted_time
        self._breakstart = None
        self.timerUpdated()

    def halt_time(self):
        '''
        Pause tracking the amount of time passing for the emulator.

        This also stops timers from expiring.
        '''
        self._breakstart = time.time()
        self.timerUpdated()

    def systimeReset(self):
        EmuTimeCore.systimeReset(self)
        self._sysoffset = time.time()
        self._breakstart = _sysoffset
        self.timerUpdated()

    def getSystemScaling(self):
        '''
        Returns the configured scaling factor for the emulation clock.
        '''
        return self._systime_scaling

    def systime(self):
        '''
        Return the amount of time the emulator has been running (not halted).

        This scales the result based on the systime_scaling parameter provided
        during initialization.
        '''
        now = time.time()

        # Make sure to take into account the breakstart offset if the system
        # is halted
        if not self.systimeRunning():
            elapsed_time = (now - self._sysoffset) - (now - self._breakstart)
        else:
            elapsed_time = now - self._sysoffset
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
        with self._timer_lock:
            # Do any standard update stuff behind the lock
            EmuTimeCore.timerUpdated(self)

        with self._timer_update:
            self._timer_update.notify()

    def getNextEvent(self):
        '''
        Return the amount of time to wait before the next event should occur
        '''
        if not self.systimeRunning():
            return None

        if self._timers and self._timers[0].expired():
            return self._timers[0].time()

        return None

    def getExpiredTimer(self):
        '''
        Checks if the next timer scheduled to expire has expired or not.  If it
        has expired the EmuTimer object is returned.
        '''
        if not self.systimeRunning():
            return None

        if self._timers and self._timers[0].expired():
            return self._timers[0]

        return None

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
                expired_timer = self.getExpiredTimer()
                if expired_timer:
                    self._handle_expired(expired_timer)

                # Get the next scheduled timer/event to wait for
                next_event = self.getNextEvent()
