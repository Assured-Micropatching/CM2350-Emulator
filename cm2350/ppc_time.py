from . import emutimers
from .ppc_vstructs import PpcSprCallbackWrapper

import envi.bits as e_bits
import envi.archs.ppc.regs as eapr

import logging
logger = logging.getLogger(__name__)


__all__ = [
    'PpcEmuTime',
]


class PpcEmuTime:
    '''
    PowerPC specific emulator time and timer handling mixin

    TODO: lots of docs here about how this is separate from the core emulator
    time class
    '''
    def __init__(self):
        # TODO: The PPC timebase count should not reset during a software reset 
        # or when the timebase is disabled.
        #
        # The time base can be written to which is supposed to reset the point
        # that the system time is counting from.  We don't want to change the
        # EmulationTime._sysoffset offset because that may impact the tracking
        # of any timers currently running.  Instead use a timebase offset value
        # so values read from TBU/TBL will have the correct values but the
        # systicks() will be unmodified.
        self._tb_offset = None

        # Register the TBU/TBL callbacks, both read and write is valid
        self.tb = PpcSprCallbackWrapper(eapr.REG_TB, self,
                                        read_handler=self.tbRead,
                                        write_handler=self.tbWrite)
        self.tbu = PpcSprCallbackWrapper(eapr.REG_TBU, self,
                                         read_handler=self.tbuRead,
                                         write_handler=self.tbuWrite)

        # TODO: The TBU/TBL hypervisor access registers are write-only, but this
        # is not yet implemented

        # The TBU_WO/TBL_WO SPRs are used to hold the desired timebase offset
        # value in them.  They are write-only so these callback functions ensure
        # the reads are correctly emulated.
        self.tbl_wo = PpcSprCallbackWrapper(eapr.REG_TBL_WO, self,
                                            read_handler=self._invalid_tb_read,
                                            write_handler=self.tbWrite)
        self.tbu_wo = PpcSprCallbackWrapper(eapr.REG_TBU_WO, self,
                                            read_handler=self._invalid_tb_read,
                                            write_handler=self.tbuWrite)

    def _invalid_tb_write(self, value):
        pass

    def _invalid_tb_read(self):
        return 0

    def enableTimebase(self):
        '''
        when the timebase is stopped the timebase registers shouldn't increment
        and the timebase-managed timers (decrementer, watchdog, and the
        fixed-interval timer) should be disabled when the timebase is disabled.
        '''
        if self._tb_offset is None:
            self._tb_offset = self.systicks()
        else:
            logger.warning('PPC timebase enabled when already enabled!', exc_info=1)

        # When the timebase is enabled also check if the WDT, FIT or DEC
        # timers should be started
        #
        # TODO: Fix how timers are started, they should be started always when 
        # the timebase is running.
        if self.tcr.wie:
            self._startMCUWDT()
        if self.tcr.fie:
            self._startMCUFIT()
        if self.tcr.die:
            self._startMCUWDT()

    def disableTimebase(self):
        '''
        when the timebase is stopped the timebase registers shouldn't increment
        and the timebase-managed timers (decrementer, watchdog, and the
        fixed-interval timer) should be disabled when the timebase is disabled.
        '''
        if self._tb_offset is not None:
            self._tb_offset = None
        else:
            logger.warning('PPC timebase disabled when already disabled!', exc_info=1)

        # Stop all MCU timers
        self.mcu_wdt.stop()
        self.mcu_fit.stop()
        self.mcu_dec.stop()

    def timebaseRunning(self):
        '''
        Useful for testing to indicate if the timebase is running or not
        '''
        return self._tb_offset is not None

    def tbRead(self):
        '''
        Read callback handler to associate the value of the TBL SPR with the
        EmulationTime.
        '''
        # In 64-bit mode reading the TBL returns the entire 64-bit TB value, in
        # 32-bit mode its just the lower 32-bits, but this masking is done
        # already in the PpcRegOper class (and will be set in the i_mfspr()
        # handler that calls this)
        return self.getTimebase()

    def tbuRead(self):
        '''
        Read callback handler to associate the value of the TBU SPR with the
        EmulationTime.
        '''
        # Get the top 32-bits of the "ticks" value.  This should be only 32-bits
        # wide regardless of if this is a 64-bit or 32-bit machine.
        return (self.getTimebase() >> 32) & 0xFFFFFFFF

    def tbWrite(self, value):
        '''
        Update the tb_offset so TBL values returned from this point on
        reflect the new offset.
        '''
        # On 64 bit platforms this will be the full timebase, on 32 bit 
        # platforms this needs to be combined with the current TBU value to get 
        # the full timebase
        tb = value

        if self.psize == 4:
            # Based on the new TB offset and the current value of TBU, calculate
            # the new desired timebase offset
            tbu = (self.getTimebase() >> 32) & 0xFFFFFFFF
            tb |= (tbu << 32)

        self._tb_offset = self.systicks() - tb

        # Return the offset so that TBL has the correct offset to use to
        # calculate the desired timebase offset.
        return tb & e_bits.b_masks[self.psize]

    def tbuWrite(self, value):
        '''
        Update the tb_offset so TBU values returned from this point on
        reflect the new offset.
        '''
        # Ensure that the offset value is only 32-bits wide regardless of the
        # platform size.
        tbu = value & 0xFFFFFFFF

        # Based on the new TBU offset and the current value of TBL (the lower 32 
        # bits of the current offset), calculate the new desired timebase offset
        tbl = self.getTimebase() & 0xFFFFFFFF
        tb = (tbu << 32) | tbl

        self._tb_offset = self.systicks() - tb

        # Return the offset so that TBU has the correct offset to use to
        # calculate the desired timebase offset.
        return (tb >> 32) & 0xFFFFFFFF

    def getTimebase(self):
        '''
        Because PowerPC allows writes to the "Write-Only" TBL/TBU registers,
        adjust the returned systicks value by the current offset.
        '''
        if self._tb_offset is None:
            return 0
        else:
            return self.systicks() - self._tb_offset
