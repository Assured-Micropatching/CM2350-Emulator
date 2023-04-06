class EmuClocks:
    '''
    Provides a standardized way for peripherals to register core processor
    clocks that can be used by other peripherals.
    '''

    def __init__(self):
        self._system_clocks = {}

    def registerClock(self, clock, func):
        self._system_clocks[clock] = func

    def getClock(self, clock):
        return self._system_clocks[clock]()
