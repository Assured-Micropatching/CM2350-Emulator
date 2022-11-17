from . import emutimers
from envi.archs.ppc.regs import REG_TBU, REG_TB, REG_TBU_WO, REG_TBL_WO


__all__ = [
    'PpcEmuTime',
]


class PpcEmuTime:
    '''
    PowerPC specific emulator time and timer handling mixin
    '''
    def __init__(self):
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
        self._tb_offset = self.systicks() - offset

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
        self._tb_offset = self.systicks() - offset

        # Return the offset so that TBU_WO has the correct offset to use to
        # calculate the desired timebase offset.
        return tbu_offset

    def systicks(self):
        '''
        Because PowerPC allows writes to the "Write-Only" TBL/TBU registers,
        adjust the returned systicks value by the current offset.
        '''
        return super().systicks() - self._tb_offset
