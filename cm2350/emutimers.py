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
    def __init__(self, emutime, name, callback, freq=None, ticks=None, duration=None):
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
            ticks       (optional) The number of clock ticks that should
                        elapse before the timer expires.
            duration    (optional) Instead of freq/ticks a time based duration
                        can be used to set the timer ticks based on an emulated
                        amount of elapsed time.

        If the freq and ticks parameters are not provided during timer
        creation then they should be provided when the start() function is
        called.
        '''
        self._emutime = emutime
        self.name = name
        self._callback = callback

        # Frequency and ticks can either be set when the timer is created if
        # those are fixed, or later when the timer is started.
        self.freq = freq
        self._timerfreq_to_sysfreq = None
        self._ticks = ticks
        self._duration = duration

        # When a timer is not running the target is None
        self.target = None

        # Used to track paused timers, only used by the pause and resume
        # functions
        self._remaining = None

    def start(self, freq=None, ticks=None, duration=None):
        '''
        Start a timer running right now.

        Uses the emutime object's systicks() function call to determine what the
        current system time is.

        Arguments:
            freq        (optional) The clock frequency that the timer uses to
                        determine the duration of the timer.
            ticks       (optional) The number of clock ticks that should
                        elapse before the timer expires.
            duration    (optional) Instead of freq/ticks a time based duration
                        can be used to set the timer ticks based on an emulated
                        amount of elapsed time.

        If the freq and ticks parameters were provided when the timer object
        was created through the EmulationTime.registerTimer() function then
        those parameters are not required when start() is called.
        '''
        sysfreq = self._emutime.getSystemFreq()

        # If the freq or ticks params are supplied, override whatever the
        # default values may be
        if freq is not None:
            self.freq = freq
        elif self.freq is None:
            # If no frequency was provided when the timer was created or in this
            # start function, use the current timebase frequency
            self.freq = sysfreq

        if ticks is not None:
            self._ticks = ticks

        # If duration is provided use that to calculate how many ticks this 
        # timer should be
        if duration is not None:
            self._duration = duration
        if self._duration is not None:
            self._ticks = sysfreq * self._duration

        # Ensure that the remaining time is not set
        self._remaining = None

        # frequency and ticks must be set for a timer to be started
        if not self.freq or not self._ticks:
            # If either frequency or ticks is 0 then ensure that the timer is
            # not running
            self.target = None

            err = 'Cannot start %s timer: %s @ %s Hz' % (self.name, self._ticks, self.freq)
            raise Exception(err)

        # Determine how many system ticks occur for every tick of this timer
        self._timerfreq_to_sysfreq = self.freq / sysfreq
        systicks = int(self._ticks / self._timerfreq_to_sysfreq)
        now = self._emutime.systicks()
        self.target = now + systicks
        logger.debug('[%d] %s timer started: %d @ %d Hz == %d @ %d',
                     now, self.name, self._ticks, self.freq, systicks, sysfreq)

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
            # If the timer has not been started return 0
            return 0.0

        remaining_systicks = self.target - self._emutime.systicks()
        if remaining_systicks <= 0:
            return 0.0

        return remaining_systicks / self._emutime.getSystemFreq()

    def ticks(self):
        '''
        Return the number of timer ticks (not system ticks) remaining before
        this timer should expire.
        '''
        if self.target is None:
            # If the timer has not been started return 0
            return 0

        remaining_systicks = self.target - self._emutime.systicks()
        if remaining_systicks <= 0:
            return 0

        return int(remaining_systicks * self._timerfreq_to_sysfreq)

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

        self._running = False

    def __del__(self):
        # Stop all the timers, probably not necessary
        for t in self._timers:
            t.stop()

    def tick(self):
        self._ticks += 1

        # Determine if any timers should expire
        #expired_timer = self.getExpiredTimer()
        #if expired_timer is not None:
        #    self._handle_expired(expired_timer)

    def systimeReset(self):
        '''
        Clear the system ticks and stop all the timers.
        '''
        self._ticks = 0
        self._systemFreq = None

        # Stop all registered timers
        for timer in self._timers:
            timer.stop()

        self.timerUpdated()

    def setSystemFreq(self, freq):
        self._systemFreq = float(freq)

    def getSystemFreq(self):
        if self._systemFreq is None:
            return 0.0
        else:
            return self._systemFreq

    def registerTimer(self, name, callback, freq=None, ticks=None, duration=None):
        '''
        Used by emulated peripherals and other components to create a timer
        that will be tracked and can be configured, started or stopped by
        those components.
        '''
        new_timer = EmuTimer(self, name, callback, freq=freq, ticks=ticks,
                             duration=duration)
        logger.debug('Registering timer %s', name)
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
        self.timerUpdated()

    def systime(self, offset=None):
        '''
        Return the amount of time the emulator has been running (not halted).
        Optionally adjust the system time by the specified offset (useful for
        testing).
        '''
        return self.systicks(offset) * self.getSystemFreq()

    def systicks(self, offset=None):
        '''
        Return the number of ticks 
        Optionally adjust the system time by the specified offset (useful for
        testing).
        '''
        if offset:
            self._ticks += offset * self.getSystemFreq()

        return self._ticks

    def sleep(self, delay):
        # Move time forward the specified number of seconds
        self._ticks += delay * self.getSystemFreq()

    def resume_time(self):
        self._running = True

    def halt_time(self):
        self._running = False

    def systimeRunning(self):
        return self._running


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

    def resume_time(self):
        '''
        Resume tracking the amount of time passing for the emulator, but only
        if system time has already been started.
        '''
        if self._breakstart is not None:
            halted_time = time.time() - self._breakstart
            self._sysoffset += halted_time
            self._breakstart = None
            self.timerUpdated()
        else:
            logger.warning('resume_time called when time is already running!', exc_info=1)

    def halt_time(self):
        '''
        Pause tracking the amount of time passing for the emulator.

        This also stops timers from expiring.
        '''
        if self._breakstart is None:
            self._breakstart = time.time()
            self.timerUpdated()
        else:
            logger.warning('halt_time called when time is already paused!', exc_info=1)

    def systimeRunning(self):
        '''
        Returns an indication of if the primary system time is running or
        paused. Useful for testing and debugging.
        '''
        return self._sysoffset and not self._breakstart

    def systimeReset(self):
        '''
        Reset the system time and set breakstart to indicate the system is paused.
        '''
        self._sysoffset = time.time()
        self._breakstart = self._sysoffset
        EmuTimeCore.systimeReset(self)

    def getSystemScaling(self):
        '''
        Returns the configured scaling factor for the emulation clock.
        '''
        return self._systime_scaling

    def systime(self, offset=None):
        '''
        Return the amount of time the emulator has been running (not halted).
        Optionally adjust the system time by the specified offset (useful for
        testing).

        This scales the result based on the systime_scaling parameter provided
        during initialization.
        '''
        if offset:
            # This should change the current system time by the specified 
            # amount, so if the offset is positive, then the sysoffset should be 
            # decreased to increase the amount of the it appears the system has 
            # been running. If the offset is negative, then the sysoffset should 
            # be increased to decrease the amount of time the system has been 
            # running.
            #
            # So we invert the offset here. Also multiply the offset by the 
            # desired system time scaling factor.
            self._sysoffset -= offset / self._systime_scaling

        now = time.time()

        # Make sure to take into account the breakstart offset if the system
        # is halted
        if self._breakstart:
            elapsed_time = (now - self._sysoffset) - (now - self._breakstart)
        else:
            elapsed_time = now - self._sysoffset

        return elapsed_time * self._systime_scaling

    def systicks(self, offset=None):
        '''
        Uses the configured system clock frequency to determine how many clock
        ticks have elapsed while the system has been running. Optionally adjust
        the system ticks by the specified offset (useful for testing).
        '''
        # Return the system time in the number of cycles have happened
        systime = self.systime(offset)
        sysfreq = self.getSystemFreq()
        if systime and sysfreq:
            return int(systime * sysfreq)
        else:
            return 0

    def sleep(self, delay):
        # Move time forward/wait the specified number of seconds
        #self._sysoffset -= delay / self._systime_scaling
        time.sleep(delay / self._systime_scaling)

    def timerUpdated(self):
        '''
        A utility that allows timers to notify the core emulation thread that
        they have been updated.
        '''
        self._timers.sort()
        with self._timer_update:
            self._timer_update.notify()

    def getNextEvent(self):
        '''
        Return the amount of time to wait before the next event should occur
        '''
        if self.systimeRunning() and self._timers and self._timers[0].running():
            return self._timers[0].time()
        else:
            return None

    def getExpiredTimer(self):
        '''
        Checks if the next timer scheduled to expire has expired or not.  If it
        has expired the EmuTimer object is returned.
        '''
        if self.systimeRunning() and self._timers and self._timers[0].expired():
            return self._timers[0]
        else:
            return None

    def _tb_run(self):
        '''
        Timer management thread.
        '''
        with self._timer_update:
            while not self._stop.is_set():
                # Get the next scheduled timer/event to wait for
                next_event = self.getNextEvent()

                # Wait until the next scheduled event, or until a timer update
                # occurs.
                self._timer_update.wait(next_event)

                # If the next scheduled timer has expired, handle that
                # expiration
                expired_timer = self.getExpiredTimer()
                if expired_timer:
                    self._handle_expired(expired_timer)
