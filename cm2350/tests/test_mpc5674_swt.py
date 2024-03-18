import random

import envi.bits as e_bits

from cm2350 import intc_exc

from .helpers import MPC5674_Test

import logging
logger = logging.getLogger(__name__)


SWT_MCR     = 0xfff38000
SWT_IR      = 0xfff38004
SWT_TO      = 0xfff38008
SWT_WN      = 0xfff3800C
SWT_SR      = 0xfff38010
SWT_CO      = 0xfff38014
SWT_SK      = 0xfff38018

SWT_MCR_IDX = 0
SWT_IR_IDX  = 1
SWT_TO_IDX  = 2
SWT_WN_IDX  = 3
SWT_SR_IDX  = 4
SWT_CO_IDX  = 5
SWT_SK_IDX  = 6

# SWT peripheral register non-zero values
SWT_MCR_DEFAULT       = 0xff00010a  # Default when BAM forces SWT to be disabled
SWT_MCR_ENABLE_WDOG   = 0xff00010b
SWT_TO_DEFAULT        = 0x0005fcd0
SWT_MCR_DEFAULT_BYTES = b'\xff\x00\x01\x0a'
SWT_TO_DEFAULT_BYTES  = b'\x00\x05\xfc\xd0'

# SIU and ECSM constants for checking reset sources
SIU_RSR         = (0xC3F9000C, 4)
SIU_RSR_PORS    = 0x80008000
SIU_RSR_SWTRS   = 0x02008000

ECSM_MRSR       = (0xFFF4000F, 1)
ECSM_MRSR_POR   = 0x80
ECSM_MRSR_SWTR  = 0x20


class MPC5674_WDT_Test(MPC5674_Test):
    accurate_timing = True

    def test_swt_mcr_defaults(self):
        self.assertEqual(self.emu.readMemory(SWT_MCR, 4), SWT_MCR_DEFAULT_BYTES)
        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), SWT_MCR_DEFAULT)
        self.assertEqual(self.emu.swt.registers.mcr.map, 0xFF)
        self.assertEqual(self.emu.swt.registers.mcr.key, 0)
        self.assertEqual(self.emu.swt.registers.mcr.ria, 1)
        self.assertEqual(self.emu.swt.registers.mcr.wnd, 0)
        self.assertEqual(self.emu.swt.registers.mcr.tif, 0)  # ITR
        self.assertEqual(self.emu.swt.registers.mcr.hlk, 0)
        self.assertEqual(self.emu.swt.registers.mcr.slk, 0)
        self.assertEqual(self.emu.swt.registers.mcr.csl, 1)
        self.assertEqual(self.emu.swt.registers.mcr.stp, 0)
        self.assertEqual(self.emu.swt.registers.mcr.frz, 1)

        # The reset default of MCR[WEN] is 1 but BAM may set it to false if the
        # RCHW does not have the SWT configuration bit set. Because this test is
        # run with no firmware SWT will never be set so BAM will change MCR[WEN]
        # to 0.
        self.assertEqual(self.emu.swt.registers.mcr.wen, 0)

    def test_swt_disable(self):
        # Default enabled and running
        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), SWT_MCR_DEFAULT)

        # SWT disabled by BAM by default
        self.assertEqual(self.emu.swt.registers.mcr.wen, 0)
        self.assertEqual(self.emu.swt.watchdog.running(), False)

        # Re-enable the watchdog
        self.emu.writeMemValue(SWT_MCR, SWT_MCR_ENABLE_WDOG, 4)
        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), SWT_MCR_ENABLE_WDOG)
        self.assertEqual(self.emu.swt.registers.mcr.wen, 1)
        self.assertEqual(self.emu.swt.watchdog.running(), True)

        # But because the SLK or HLK are not set it can be disabled by changing
        # MCR[WEN]
        clear_wen_val = SWT_MCR_ENABLE_WDOG & 0xFFFFFFFE
        self.emu.writeMemValue(SWT_MCR, clear_wen_val, 4)
        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), clear_wen_val)

        self.assertEqual(self.emu.swt.registers.mcr.wen, 0)
        self.assertEqual(self.emu.swt.watchdog.running(), False)

        # Ensure the rest of the MCR fields were not modified (defaults used
        # from the test_swt_mcr_defaults() test)
        #
        # Some registers have side effects when writing values, changing WEN
        # from 1 to 0 should have no side effects other than stopping the
        # watchdog timer.
        self.assertEqual(self.emu.swt.registers.mcr.map, 0xFF)
        self.assertEqual(self.emu.swt.registers.mcr.key, 0)
        self.assertEqual(self.emu.swt.registers.mcr.ria, 1)
        self.assertEqual(self.emu.swt.registers.mcr.wnd, 0)
        self.assertEqual(self.emu.swt.registers.mcr.tif, 0)  # ITR
        self.assertEqual(self.emu.swt.registers.mcr.hlk, 0)
        self.assertEqual(self.emu.swt.registers.mcr.slk, 0)
        self.assertEqual(self.emu.swt.registers.mcr.csl, 1)
        self.assertEqual(self.emu.swt.registers.mcr.stp, 0)
        self.assertEqual(self.emu.swt.registers.mcr.frz, 1)

    def test_swt_reenable(self):
        # SWT disabled by BAM by default
        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), SWT_MCR_DEFAULT)
        self.assertEqual(self.emu.readMemory(SWT_MCR, 4), SWT_MCR_DEFAULT_BYTES)
        self.assertEqual(self.emu.swt.registers.mcr.wen, 0)
        self.assertEqual(self.emu.swt.watchdog.running(), False)

        # Enable
        self.emu.writeMemValue(SWT_MCR, SWT_MCR_ENABLE_WDOG, 4)
        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), SWT_MCR_ENABLE_WDOG)
        self.assertEqual(self.emu.readMemory(SWT_MCR, 4), b'\xff\x00\x01\x0b')
        self.assertEqual(self.emu.swt.registers.mcr.wen, 1)
        self.assertEqual(self.emu.swt.watchdog.running(), True)

        # Disable
        clear_wen_val = SWT_MCR_ENABLE_WDOG & 0xFFFFFFFE
        self.assertEqual(clear_wen_val, SWT_MCR_DEFAULT)
        self.emu.writeMemValue(SWT_MCR, clear_wen_val, 4)
        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), SWT_MCR_DEFAULT)
        self.assertEqual(self.emu.readMemory(SWT_MCR, 4), SWT_MCR_DEFAULT_BYTES)
        self.assertEqual(self.emu.swt.registers.mcr.wen, 0)
        self.assertEqual(self.emu.swt.watchdog.running(), False)

        # Re-Enable
        self.emu.writeMemValue(SWT_MCR, SWT_MCR_ENABLE_WDOG, 4)
        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), SWT_MCR_ENABLE_WDOG)
        self.assertEqual(self.emu.readMemory(SWT_MCR, 4), b'\xff\x00\x01\x0b')
        self.assertEqual(self.emu.swt.registers.mcr.wen, 1)
        self.assertEqual(self.emu.swt.watchdog.running(), True)

    def test_swt_ir_defaults(self):
        self.assertEqual(self.emu.readMemory(SWT_IR, 4), b'\x00\x00\x00\x00')
        self.assertEqual(self.emu.readMemValue(SWT_IR, 4), 0)
        self.assertEqual(self.emu.swt.registers.ir.tif, 0)

    def test_swt_ir_write_one_to_clear(self):
        # IR[TIF] should be 0 by default
        self.assertEqual(self.emu.swt.registers.ir.tif, 0)

        # Manually set the SWT IR[TIF] flag
        self.emu.swt.registers.ir.vsOverrideValue('tif', 1)
        self.assertEqual(self.emu.readMemValue(SWT_IR, 4), 1)
        self.assertEqual(self.emu.swt.registers.ir.tif, 1)

        # Attempt to clear by writing 0, ensure it doesn't work
        self.emu.writeMemValue(SWT_IR, 0, 4)
        self.assertEqual(self.emu.readMemValue(SWT_IR, 4), 1)
        self.assertEqual(self.emu.swt.registers.ir.tif, 1)

        # Now write 1
        self.emu.writeMemValue(SWT_IR, 1, 4)
        self.assertEqual(self.emu.readMemValue(SWT_IR, 4), 0)
        self.assertEqual(self.emu.swt.registers.ir.tif, 0)

    def test_swt_to_defaults(self):
        self.assertEqual(self.emu.readMemory(SWT_TO, 4), SWT_TO_DEFAULT_BYTES)
        self.assertEqual(self.emu.readMemValue(SWT_TO, 4), SWT_TO_DEFAULT)
        self.assertEqual(self.emu.swt.registers.to.wto, SWT_TO_DEFAULT)

        # The SWT is enabled and running by default, ensure that the timeout
        # period matches the default TO value
        self.assertEqual(self.emu.swt.watchdog._ticks, SWT_TO_DEFAULT)

    def test_swt_wn_defaults(self):
        self.assertEqual(self.emu.readMemory(SWT_WN, 4), b'\x00\x00\x00\x00')
        self.assertEqual(self.emu.readMemValue(SWT_WN, 4), 0)
        self.assertEqual(self.emu.swt.registers.wn.wst, 0)

    def test_swt_sr_defaults(self):
        # SR should always return 0
        self.assertEqual(self.emu.readMemory(SWT_SR, 4), b'\x00\x00\x00\x00')
        self.assertEqual(self.emu.readMemValue(SWT_SR, 4), 0)

        # Valid writes to the SR register aren't simple so are tested in the
        # lock/unlock and watchdog service tests. Valid values to write are
        # either the unlock sequence (0xC520, 0xD928), the "standard" service
        # keys (0xA602, 0xB480), or pseudo-random generated keys if SWT MCR[KEY]
        # is set.

        # The SLK and SK indexes should be 0
        self.assertEqual(self.emu.swt._slk_idx, 0)
        self.assertEqual(self.emu.swt._sk_idx, 0)

        # Write an invalid value to the SWT SR register, invalid SR values
        # should be ignored
        self.emu.writeMemory(SWT_SR, b'\xA5\xA5\xA5\xA5')

        # SLK and SK indexes should be unchanged
        self.assertEqual(self.emu.swt._slk_idx, 0)
        self.assertEqual(self.emu.swt._sk_idx, 0)

    def test_swt_co_defaults(self):
        # Watchdog should be disabled by default because the SWT flag in the BAM 
        # RCHW entry isn't set.
        self.assertEqual(self.emu.swt.watchdog.running(), False)

        # Pause the emulator system time so no emulated time elapses
        self.emu.halt_time()

        # Enable the watchdog
        self.emu.writeMemValue(SWT_MCR, SWT_MCR_ENABLE_WDOG, 4)
        self.assertEqual(self.emu.swt.watchdog.running(), True)

        # The SWT CO register should reflect the amount of time left before the
        # watchdog timer expires. Because the system starts paused it should
        # have the same value as the TO initialization value
        self.assertEqual(self.emu.readMemory(SWT_CO, 4), SWT_TO_DEFAULT_BYTES)
        self.assertEqual(self.emu.readMemValue(SWT_CO, 4), SWT_TO_DEFAULT)

        # Stop the watchdog timer
        clear_wen_val = SWT_MCR_ENABLE_WDOG & 0xFFFFFFFE
        self.emu.writeMemValue(SWT_MCR, clear_wen_val, 4)
        self.assertEqual(self.emu.swt.watchdog.running(), False)

        # When the watchdog is not running CO should be 0
        self.assertEqual(self.emu.readMemory(SWT_CO, 4), b'\x00\x00\x00\x00')
        self.assertEqual(self.emu.readMemValue(SWT_CO, 4), 0)

    def test_swt_invalid_access_error_ria_set_wen_set(self):
        start = 0xfff3801C  # SWT_SK + 4
        stop = 0xfff3C000 - 4

        # writing or reading invalid memory addresses should result in
        # a SYSTEM_RESET if SWT MCR[RIA] is set and MCR[WEN] is set, or a Bus
        # Error (MCE) if RIA is not set.

        # SWT MCR[RIA] should be enabled by default
        self.assertEqual(self.emu.swt.registers.mcr.ria, 1)

        # But the watchdog is not enabled by default (disabled by BAM)
        self.assertEqual(self.emu.swt.registers.mcr.wen, 0)

        # Enable the watchdog now to ensure test that invalid accesses generate
        # resets
        self.emu.writeMemValue(SWT_MCR, SWT_MCR_ENABLE_WDOG, 4)
        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), SWT_MCR_ENABLE_WDOG)
        self.assertEqual(self.emu.swt.registers.mcr.wen, 1)
        self.assertEqual(self.emu.swt.watchdog.running(), True)

        # Test min invalid, max invalid and a few in between
        test_addrs = [start, stop] + [random.randrange(start, stop, 4) for i in range(3)]

        # Values to write for each test
        test_vals = [random.getrandbits(32) for i in range(len(test_addrs))]

        for test_addr, test_val in zip(test_addrs, test_vals):
            # Pretend these reads and writes are happening from a random
            # instruction
            test_pc = self.get_random_pc()
            self.emu.setProgramCounter(test_pc)

            # Read the test address
            # This should generate a ResetException
            msg = 'invalid read from 0x%x' % test_addr
            with self.assertRaises(intc_exc.ResetException, msg=msg) as cm:
                self.emu.readMemory(test_addr, 4)
            self.assertEqual(cm.exception.source, intc_exc.ResetSource.WATCHDOG)
            self.assertEqual(cm.exception.kwargs, {}, msg=msg)

            # Write the test value to the test address
            msg = 'invalid write of 0x%x to 0x%x' % (test_val, test_addr)
            with self.assertRaises(intc_exc.ResetException, msg=msg) as cm:
                self.emu.writeMemValue(test_addr, test_val, 4)
            self.assertEqual(cm.exception.source, intc_exc.ResetSource.WATCHDOG)
            self.assertEqual(cm.exception.kwargs, {}, msg=msg)

    def test_swt_invalid_access_error_ria_clear_wen_set(self):
        # Enable the watchdog
        mcr_val = SWT_MCR_ENABLE_WDOG
        self.emu.writeMemValue(SWT_MCR, mcr_val, 4)
        self.assertEqual(self.emu.swt.registers.mcr.wen, 1)
        self.assertEqual(self.emu.swt.watchdog.running(), True)

        start = 0xfff3801C  # SWT_SK + 4
        stop  = 0xfff3C000 - 4

        # writing or reading invalid memory addresses should result in
        # a ResetException if SWT MCR[RIA] is set, or a Bus Error (MCE) if RIA is
        # not set.

        # SWT MCR[RIA] should be enabled by default
        self.assertEqual(self.emu.swt.registers.mcr.ria, 1)

        # But for this test we want RIA to not be set
        clear_ria_val = mcr_val & 0xFFFFFEFF
        self.emu.writeMemValue(SWT_MCR, clear_ria_val, 4)
        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), clear_ria_val)
        self.assertEqual(self.emu.swt.registers.mcr.ria, 0)

        # Test min invalid, max invalid and a few in between
        test_addrs = [start, stop] + [random.randrange(start, stop, 4) for i in range(3)]

        for test_addr in test_addrs:
            self.validate_invalid_addr(test_addr, 4)

    def test_swt_ro_reg_writes_sysreset(self):

        mrsr_addr, mrsr_size = ECSM_MRSR
        rsr_addr, rsr_size = SIU_RSR

        # Writes to read-only registers should generate Bus Errors or resets
        # depending on RIA
        unlocked_ro_regs = [SWT_CO]
        locked_ro_regs = [SWT_MCR, SWT_TO, SWT_WN, SWT_CO, SWT_SK]

        # SWT MCR[RIA] is set by default
        self.assertEqual(self.emu.swt.registers.mcr.ria, 1)

        # But the watchdog is not enabled by default (disabled by BAM)
        self.assertEqual(self.emu.swt.registers.mcr.wen, 0)

        # Enable the watchdog now to ensure test that invalid accesses generate
        # resets
        self.emu.writeMemValue(SWT_MCR, SWT_MCR_ENABLE_WDOG, 4)
        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), SWT_MCR_ENABLE_WDOG)
        self.assertEqual(self.emu.swt.registers.mcr.wen, 1)
        self.assertEqual(self.emu.swt.watchdog.running(), True)

        # SWT is unlocked by default
        self.assertEqual(self.emu.swt.registers.mcr.slk, 0)
        self.assertEqual(self.emu.swt.registers.mcr.hlk, 0)
        self.assertEqual(self.emu.swt.locked(), False)

        # Writes to any of the "unlocked" addresses should cause a reset now
        test_vals = [random.getrandbits(32) for i in
                     range(len(unlocked_ro_regs))]
        for test_addr, test_val in zip(unlocked_ro_regs, test_vals):
            # Pretend these reads and writes are happening from a random
            # instruction
            test_pc = self.get_random_pc()
            self.emu.setProgramCounter(test_pc)

            # Should be no pending exceptions by default
            self.assertEqual(self.checkPendingExceptions(), [])

            msg = 'invalid write of 0x%x to 0x%x' % (test_val, test_addr)
            with self.assertRaises(intc_exc.ResetException, msg=msg) as cm:
                self.emu.writeMemValue(test_addr, test_val, 4)
            self.assertEqual(cm.exception.source, intc_exc.ResetSource.WATCHDOG)
            self.assertEqual(cm.exception.kwargs, {}, msg=msg)

            self.emu.queueException(cm.exception)
            self.emu.stepi()

            # queue the exception as it would be if this had happened while 
            # processing an instruction, step and then check that the watchdog 
            # is marked as the source of the reset
            self.assertEqual(self.emu.readMemValue(*SIU_RSR), SIU_RSR_SWTRS)
            self.assertEqual(self.emu.readMemValue(*ECSM_MRSR), ECSM_MRSR_SWTR)

        # Lock the SWT and try again
        lock_swt_val = SWT_MCR_ENABLE_WDOG | 0x00000010
        self.emu.writeMemValue(SWT_MCR, lock_swt_val, 4)
        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), lock_swt_val)
        self.assertEqual(self.emu.swt.registers.mcr.hlk, 0)
        self.assertEqual(self.emu.swt.registers.mcr.slk, 1)
        self.assertEqual(self.emu.swt.locked(), True)

        test_vals = [random.getrandbits(32) for i in
                     range(len(unlocked_ro_regs))]
        for test_addr, test_val in zip(unlocked_ro_regs, test_vals):
            # Pretend these reads and writes are happening from a random
            # instruction
            test_pc = self.get_random_pc()
            self.emu.setProgramCounter(test_pc)

            # Should be no pending exceptions by default
            self.assertEqual(self.checkPendingExceptions(), [])

            msg = 'invalid write of 0x%x to 0x%x' % (test_val, test_addr)
            with self.assertRaises(intc_exc.ResetException, msg=msg) as cm:
                self.emu.writeMemValue(test_addr, test_val, 4)
            self.assertEqual(cm.exception.source, intc_exc.ResetSource.WATCHDOG)
            self.assertEqual(cm.exception.kwargs, {}, msg=msg)

            self.emu.queueException(cm.exception)
            self.emu.stepi()

            # queue the exception as it would be if this had happened while 
            # processing an instruction, step and then check that the watchdog 
            # is marked as the source of the reset
            self.assertEqual(self.emu.readMemValue(*SIU_RSR), SIU_RSR_SWTRS)
            self.assertEqual(self.emu.readMemValue(*ECSM_MRSR), ECSM_MRSR_SWTR)

    def test_swt_ro_reg_writes_buserror(self):
        # Writes to read-only registers should generate Bus Errors or resets
        # depending on RIA
        unlocked_ro_regs = [SWT_CO]
        locked_ro_regs = [SWT_MCR, SWT_TO, SWT_WN, SWT_CO, SWT_SK]

        # SWT MCR[RIA] is set by default
        self.assertEqual(self.emu.swt.registers.mcr.ria, 1)

        # Clear RIA so we get Bus Errors instead of System Resets
        clear_ria_val = SWT_MCR_ENABLE_WDOG & 0xFFFFFEFF
        self.emu.writeMemValue(SWT_MCR, clear_ria_val, 4)
        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), clear_ria_val)
        self.assertEqual(self.emu.swt.registers.mcr.ria, 0)

        # SWT is unlocked by default
        self.assertEqual(self.emu.swt.registers.mcr.slk, 0)
        self.assertEqual(self.emu.swt.registers.mcr.hlk, 0)
        self.assertEqual(self.emu.swt.locked(), False)

        for test_addr in unlocked_ro_regs:
            self.validate_invalid_write(test_addr, 4)

        # Lock the SWT and try again
        lock_swt_val = clear_ria_val | 0x00000010
        self.emu.writeMemValue(SWT_MCR, lock_swt_val, 4)
        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), lock_swt_val)
        self.assertEqual(self.emu.swt.registers.mcr.hlk, 0)
        self.assertEqual(self.emu.swt.registers.mcr.slk, 1)
        self.assertEqual(self.emu.swt.locked(), True)

        for test_addr in unlocked_ro_regs:
            self.validate_invalid_write(test_addr, 4)

    def test_swt_softlock(self):
        # Enable the watchdog
        self.emu.writeMemValue(SWT_MCR, SWT_MCR_ENABLE_WDOG, 4)

        # SWT is unlocked by default
        self.assertEqual(self.emu.swt.registers.mcr.slk, 0)
        self.assertEqual(self.emu.swt.registers.mcr.hlk, 0)
        self.assertEqual(self.emu.swt.locked(), False)

        # Set the SLK flag
        lock_swt_val = SWT_MCR_ENABLE_WDOG | 0x00000010
        self.emu.writeMemValue(SWT_MCR, lock_swt_val, 4)
        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), lock_swt_val)
        self.assertEqual(self.emu.swt.registers.mcr.hlk, 0)
        self.assertEqual(self.emu.swt.registers.mcr.slk, 1)
        self.assertEqual(self.emu.swt.locked(), True)

        # Before a reset the ECSM MRSR[SWTR] should be 0 and MRSR[POR] should be
        # set since this was the first boot.
        self.assertEqual(self.emu.readMemValue(*SIU_RSR), SIU_RSR_PORS)
        self.assertEqual(self.emu.readMemValue(*ECSM_MRSR), ECSM_MRSR_POR)

        # Attempt to unlock by writing to MCR and ensure this fails
        with self.assertRaises(intc_exc.ResetException) as cm:
            self.emu.writeMemValue(SWT_MCR, SWT_MCR_ENABLE_WDOG, 4)
        self.assertEqual(cm.exception.source, intc_exc.ResetSource.WATCHDOG)
        self.assertEqual(cm.exception.kwargs, {})

        # MCR values should be unchanged
        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), lock_swt_val)
        self.assertEqual(self.emu.swt.registers.mcr.hlk, 0)
        self.assertEqual(self.emu.swt.registers.mcr.slk, 1)
        self.assertEqual(self.emu.swt.locked(), True)

        # Cause a reset with the captured exception
        self.emu.queueException(cm.exception)
        self.emu.stepi()

        # queue the exception as it would be if this had happened while 
        # processing an instruction, step and then check that the watchdog is 
        # marked as the source of the reset
        self.assertEqual(self.emu.readMemValue(*SIU_RSR), SIU_RSR_SWTRS)
        self.assertEqual(self.emu.readMemValue(*ECSM_MRSR), ECSM_MRSR_SWTR)

        # Since we reset, set the SLK flag again
        lock_swt_val = SWT_MCR_ENABLE_WDOG | 0x00000010
        self.emu.writeMemValue(SWT_MCR, lock_swt_val, 4)
        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), lock_swt_val)
        self.assertEqual(self.emu.swt.registers.mcr.hlk, 0)
        self.assertEqual(self.emu.swt.registers.mcr.slk, 1)
        self.assertEqual(self.emu.swt.locked(), True)

        # Write some values that are not the first unlock key (0xC520) and
        # ensure that the SLK sequence does not progress
        # Use the second SLK value and some other random values.
        invalid_slk_vals = [0, 0xFFFF, 0xB480, 0xD928] + [random.getrandbits(32) for i in range(10)]

        # If one of the random values happens to match the first unlock key
        # (0xC520) or the first service key (0xA602) drop them from the list of
        # tests values
        invalid_slk_vals = [v for v in invalid_slk_vals if v not in (0xA602, 0xC520)]

        # The SLK and SK indexes should be 0
        self.assertEqual(self.emu.swt._slk_idx, 0)
        self.assertEqual(self.emu.swt._sk_idx, 0)

        for test_val in invalid_slk_vals:
            # Write an invalid value to the SWT SR register, invalid SR values
            # should be ignored
            self.emu.writeMemValue(SWT_SR, test_val, 4)

            # SLK and SK indexes should be unchanged
            self.assertEqual(self.emu.swt._slk_idx, 0)
            self.assertEqual(self.emu.swt._sk_idx, 0)

        # Write the correct first watchdog SK
        self.emu.writeMemValue(SWT_SR, 0xA602, 4)

        # SLK is unchanged but SK should now be 1
        self.assertEqual(self.emu.swt._slk_idx, 0)
        self.assertEqual(self.emu.swt._sk_idx, 1)

        # Write the first SLK unlock value
        self.emu.writeMemValue(SWT_SR, 0xC520, 4)

        # SLK and SK should now be 1
        self.assertEqual(self.emu.swt._slk_idx, 1)
        self.assertEqual(self.emu.swt._sk_idx, 1)

        # Attempt to unlock by writing to MCR and ensure this fails
        with self.assertRaises(intc_exc.ResetException) as cm:
            self.emu.writeMemValue(SWT_MCR, SWT_MCR_ENABLE_WDOG, 4)
        self.assertEqual(cm.exception.source, intc_exc.ResetSource.WATCHDOG)
        self.assertEqual(cm.exception.kwargs, {})

        # MCR values should be unchanged
        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), lock_swt_val)
        self.assertEqual(self.emu.swt.registers.mcr.hlk, 0)
        self.assertEqual(self.emu.swt.registers.mcr.slk, 1)
        self.assertEqual(self.emu.swt.locked(), True)

        # Cause a reset with the captured exception
        self.emu.queueException(cm.exception)
        self.emu.stepi()

        # Pause the emulated system time and reset it back to 0
        self.emu.halt_time()
        self.emu.systime(-self.emu.systime())

        # check that the watchdog is marked as the source of the reset
        self.assertEqual(self.emu.readMemValue(*SIU_RSR), SIU_RSR_SWTRS)
        self.assertEqual(self.emu.readMemValue(*ECSM_MRSR), ECSM_MRSR_SWTR)

        # Since we reset, set the SLK flag again
        lock_swt_val = SWT_MCR_ENABLE_WDOG | 0x00000010
        self.emu.writeMemValue(SWT_MCR, lock_swt_val, 4)
        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), lock_swt_val)
        self.assertEqual(self.emu.swt.registers.mcr.hlk, 0)
        self.assertEqual(self.emu.swt.registers.mcr.slk, 1)
        self.assertEqual(self.emu.swt.locked(), True)

        # And write write the unlock sequence
        self.emu.writeMemValue(SWT_SR, 0xA602, 4)
        self.emu.writeMemValue(SWT_SR, 0xC520, 4)

        # Write some values that are not the second unlock key (0xD928) and
        # ensure that the SLK sequence does not progress
        # Use the first SLK value, first SK value, and some other random values.
        invalid_slk_vals = [0, 0xFFFF, 0xA602, 0xC520] + [random.getrandbits(32) for i in range(10)]

        # If one of the random values happens to match the second unlock key
        # (0xD928) or the second service key (0xB480) drop them from the list of
        # tests values
        invalid_slk_vals = [v for v in invalid_slk_vals if v not in (0xB480, 0xD928)]

        for test_val in invalid_slk_vals:
            # Write an invalid value to the SWT SR register, invalid SR values
            # should be ignored
            self.emu.writeMemValue(SWT_SR, test_val, 4)

            # SLK and SK indexes should be unchanged
            self.assertEqual(self.emu.swt._slk_idx, 1)
            self.assertEqual(self.emu.swt._sk_idx, 1)

        # The watchdog hasn't run yet so there should be the full period left
        wdt_time = SWT_TO_DEFAULT / self.emu.swt.watchdog.freq
        self.assertEqual(self.emu.swt.watchdog.time(), wdt_time)
        self.assertEqual(self.emu.swt.watchdog.ticks(), SWT_TO_DEFAULT)

        # Force the system time forward 0.005 emulated seconds so we can tell 
        # when the watchdog is restarted (do this by moving starting sysoffset 
        # back 0.005 seconds).  Any more than this and it will cause the 
        # watchdog to expire.
        updated_systime = self.emu.systime(0.005)
        self.assertAlmostEqual(updated_systime, 0.005, places=6)
        new_time = wdt_time - 0.005

        # Because of the floating point numbers involved with the addition of
        # the system time (time.time()) the time remaining calculation is only
        # accurate to within 6 places
        self.assertAlmostEqual(self.emu.swt.watchdog.time(), new_time, places=6)

        new_ticks = int(new_time * self.emu.swt.watchdog.freq)

        tick_delta = 0.000001 * self.emu.swt.watchdog.freq
        self.assertAlmostEqual(self.emu.swt.watchdog.ticks(), new_ticks, delta=tick_delta)

        # Write the correct second watchdog SK
        self.emu.writeMemValue(SWT_SR, 0xB480, 4)

        # SLK is unchanged but SK should now be reset back to 0
        self.assertEqual(self.emu.swt._slk_idx, 1)
        self.assertEqual(self.emu.swt._sk_idx, 0)

        # The watchdog should still be running but the duration should be back
        # to the full period
        self.assertEqual(self.emu.swt.watchdog.running(), True)
        self.assertEqual(self.emu.swt.watchdog.ticks(), SWT_TO_DEFAULT)
        self.assertAlmostEqual(self.emu.swt.watchdog.time(), wdt_time)

        # SWT is still locked
        self.assertEqual(self.emu.swt.registers.mcr.hlk, 0)
        self.assertEqual(self.emu.swt.registers.mcr.slk, 1)
        self.assertEqual(self.emu.swt.locked(), True)

        # Now write the correct second unlock key
        self.emu.writeMemValue(SWT_SR, 0xD928, 4)

        # SLK and SK should be back at 0
        self.assertEqual(self.emu.swt._slk_idx, 0)
        self.assertEqual(self.emu.swt._sk_idx, 0)
        self.assertEqual(self.emu.swt.registers.mcr.hlk, 0)
        self.assertEqual(self.emu.swt.registers.mcr.slk, 0)
        self.assertEqual(self.emu.swt.locked(), False)
        self.assertEqual(self.emu.swt.registers.mcr.wen, 1)
        self.assertEqual(self.emu.swt.watchdog.running(), True)

        # We should now be able to disable the watchdog
        clear_wen_val = SWT_MCR_ENABLE_WDOG & 0xFFFFFFFE
        self.emu.writeMemValue(SWT_MCR, clear_wen_val, 4)
        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), clear_wen_val)
        self.assertEqual(self.emu.swt.registers.mcr.wen, 0)
        self.assertEqual(self.emu.swt.watchdog.running(), False)

    def test_swt_hardlock(self):
        # Enable the watchdog
        self.emu.writeMemValue(SWT_MCR, SWT_MCR_ENABLE_WDOG, 4)

        # SWT is unlocked by default
        self.assertEqual(self.emu.swt.registers.mcr.slk, 0)
        self.assertEqual(self.emu.swt.registers.mcr.hlk, 0)
        self.assertEqual(self.emu.swt.locked(), False)

        # Set the HLK flag
        lock_swt_val = SWT_MCR_ENABLE_WDOG | 0x00000020
        self.emu.writeMemValue(SWT_MCR, lock_swt_val, 4)
        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), lock_swt_val)
        self.assertEqual(self.emu.swt.registers.mcr.hlk, 1)
        self.assertEqual(self.emu.swt.registers.mcr.slk, 0)
        self.assertEqual(self.emu.swt.locked(), True)

        # Before a reset the ECSM MRSR[SWTR] should be 0 and MRSR[POR] should be
        # set since this was the first boot.
        self.assertEqual(self.emu.readMemValue(*SIU_RSR), SIU_RSR_PORS)
        self.assertEqual(self.emu.readMemValue(*ECSM_MRSR), ECSM_MRSR_POR)

        # Attempt to unlock by writing to MCR and ensure this fails
        # This should generate a ResetException
        with self.assertRaises(intc_exc.ResetException) as cm:
            self.emu.writeMemValue(SWT_MCR, SWT_MCR_ENABLE_WDOG, 4)
        self.assertEqual(cm.exception.source, intc_exc.ResetSource.WATCHDOG)
        self.assertEqual(cm.exception.kwargs, {})

        # Write the soft unlock sequence and ensure that the HLK flag is
        # unchanged
        self.emu.writeMemValue(SWT_SR, 0xC520, 4)
        self.emu.writeMemValue(SWT_SR, 0xD928, 4)

        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), lock_swt_val)
        self.assertEqual(self.emu.swt.registers.mcr.hlk, 1)
        self.assertEqual(self.emu.swt.registers.mcr.slk, 0)
        self.assertEqual(self.emu.swt.locked(), True)

        # We haven't processed the reset exception yet so the watchdog should 
        # still be running
        self.assertEqual(self.emu.swt.registers.mcr.wen, 1)
        self.assertEqual(self.emu.swt.watchdog.running(), True)

        # Attempt to unlock again by writing to MCR and ensure this fails
        # This should generate a ResetException
        with self.assertRaises(intc_exc.ResetException) as cm:
            self.emu.writeMemValue(SWT_MCR, SWT_MCR_ENABLE_WDOG, 4)
        self.assertEqual(cm.exception.source, intc_exc.ResetSource.WATCHDOG)
        self.assertEqual(cm.exception.kwargs, {})

        # Cause a reset with the captured exception
        self.emu.queueException(cm.exception)
        self.emu.stepi()

        # queue the exception as it would be if this had happened while 
        # processing an instruction, step and then check that the watchdog is 
        # marked as the source of the reset
        self.assertEqual(self.emu.readMemValue(*SIU_RSR), SIU_RSR_SWTRS)
        self.assertEqual(self.emu.readMemValue(*ECSM_MRSR), ECSM_MRSR_SWTR)

    def test_swt_xtal_freq(self):
        # Pause the emulated system time and reset it back to 0
        self.emu.halt_time()
        self.emu.systime(-self.emu.systime())

        default_extal = self.emu.config.project.MPC5674.FMPLL.extal

        # Enable the watchdog
        self.emu.writeMemValue(SWT_MCR, SWT_MCR_ENABLE_WDOG, 4)

        # By default the watchdog frequency should be the external oscillator
        self.assertEqual(self.emu.swt.watchdog.freq, default_extal)
        wdt_time = SWT_TO_DEFAULT / default_extal
        self.assertEqual(self.emu.swt.watchdog.time(), wdt_time)
        self.assertEqual(self.emu.swt.watchdog.ticks(), SWT_TO_DEFAULT )

        self.assertEqual(self.emu.swt.registers.mcr.csl, 1)
        self.assertEqual(self.emu.swt.registers.mcr.wen, 1)
        self.assertEqual(self.emu.swt.watchdog.running(), True)

        # Disable the watchdog
        mcr_val = SWT_MCR_ENABLE_WDOG & 0xFFFFFFFE
        self.emu.writeMemValue(SWT_MCR, mcr_val, 4)
        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), mcr_val)
        self.assertEqual(self.emu.swt.registers.mcr.csl, 1)
        self.assertEqual(self.emu.swt.registers.mcr.wen, 0)
        self.assertEqual(self.emu.swt.watchdog.running(), False)

        # Change MCR[CSL] to use the peripheral clock instead of the external
        # oscillator, and re-enable the watchdog
        mcr_val = SWT_MCR_ENABLE_WDOG & 0xFFFFFFF7
        self.emu.writeMemValue(SWT_MCR, mcr_val, 4)
        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), mcr_val)
        self.assertEqual(self.emu.swt.registers.mcr.csl, 0)
        self.assertEqual(self.emu.swt.registers.mcr.wen, 1)
        self.assertEqual(self.emu.swt.watchdog.running(), True)

        # The watchdog clock should now be using the platform/peripheral clock
        self.assertEqual(self.emu.swt.watchdog.freq, self.emu.getClock('periph'))
        wdt_time = SWT_TO_DEFAULT / self.emu.getClock('periph')
        self.assertEqual(self.emu.swt.watchdog.time(), wdt_time)
        self.assertEqual(self.emu.swt.watchdog.ticks(), SWT_TO_DEFAULT)

    def test_swt_expire_reset(self):
        # Enable the watchdog
        self.emu.writeMemValue(SWT_MCR, SWT_MCR_ENABLE_WDOG, 4)

        # Default value of MCR[ITR] (TIF) is 0 so the first watchdog expiration
        # will
        # generate a ResetException
        self.assertEqual(self.emu.swt.registers.mcr.tif, 0)
        self.assertEqual(self.emu.swt.registers.mcr.wen, 1)
        self.assertEqual(self.emu.swt.watchdog.running(), True)

        default_extal = self.emu.config.project.MPC5674.FMPLL.extal
        wdt_time = SWT_TO_DEFAULT / default_extal

        start = self.emu.systime()

        # The default timeout time is 0.00981 seconds, divide the timeout time
        # by 0.01 to get the real amount of time to sleep for half of the
        # watchdog time to elapse for the emulator.
        sleep_time = wdt_time * 0.5
        self.emu.resume_time()
        self.emu.sleep(sleep_time)
        self.emu.halt_time()

        # Get current system time
        now = self.emu.systime()

        # It's unlikely the python timing will be accurate enough so that the
        # system time is now the sleep_time. but it should be less than the
        # watchdog time
        self.assertGreaterEqual(now - start, wdt_time * 0.5)
        self.assertLessEqual(now - start, wdt_time)

        # The watchdog should not have expired yet
        self.assertEqual(self.emu.swt.watchdog.running(), True)

        self.assertEqual(self.checkPendingExceptions(), [])

        # Before the SWT watchdog generates a reset the ECSM MRSR[SWTR] should
        # be 0 and MRSR[POR] should be set since this was the first boot.
        self.assertEqual(self.emu.ecsm.registers.mrsr.por, 1)
        self.assertEqual(self.emu.ecsm.registers.mrsr.dir, 0)
        self.assertEqual(self.emu.ecsm.registers.mrsr.swtr, 0)

        # Run for a full WDT time
        sleep_time = wdt_time
        self.emu.resume_time()
        self.emu.sleep(sleep_time)
        self.emu.halt_time()

        # Get current system time
        now = self.emu.systime()

        # The watchdog timer should have expired by now
        self.assertGreater(now - start, wdt_time)

        self.assertEqual(self.emu.swt.watchdog.running(), False)
        reset_exc = intc_exc.ResetException(intc_exc.ResetSource.WATCHDOG)
        self.assertEqual(self.checkPendingExceptions(), [reset_exc])

        # Process the reset exception
        self.emu.stepi()

        # queue the exception as it would be if this had happened while 
        # processing an instruction, step and then check that the watchdog is 
        # marked as the source of the reset
        self.assertEqual(self.emu.readMemValue(*SIU_RSR), SIU_RSR_SWTRS)
        self.assertEqual(self.emu.readMemValue(*ECSM_MRSR), ECSM_MRSR_SWTR)

    def test_swt_expire_interrupt(self):
        # Enable the watchdog
        self.emu.writeMemValue(SWT_MCR, SWT_MCR_ENABLE_WDOG, 4)

        # Change MCR[ITR] so that the first watchdog expiration generates an
        # interrupt, and the second one generates a reset
        mcr_val = SWT_MCR_ENABLE_WDOG | 0x00000040
        self.emu.writeMemValue(SWT_MCR, mcr_val, 4)
        self.assertEqual(self.emu.readMemValue(SWT_MCR, 4), mcr_val)

        self.assertEqual(self.emu.swt.registers.mcr.tif, 1)
        self.assertEqual(self.emu.swt.registers.mcr.wen, 1)
        self.assertEqual(self.emu.swt.watchdog.running(), True)

        default_extal = self.emu.config.project.MPC5674.FMPLL.extal
        wdt_time = SWT_TO_DEFAULT / default_extal

        # Get the start emulated time
        start = self.emu.systime()

        logger.debug('0. [%f] (WDT timeout = %f)', start, wdt_time)

        # resume the system time, wait half of the WDT time and then halt the
        # system again to stop time from counting
        sleep_time = wdt_time * 0.5
        self.emu.resume_time()
        self.emu.sleep(sleep_time)
        self.emu.halt_time()

        # It's unlikely the python timing will be accurate enough so that the
        # system time is now the sleep_time. but it should be less than the
        # watchdog time
        now = self.emu.systime()
        logger.debug('1. [%f] WDT time remaining = %f', now, self.emu.swt.watchdog.time())
        self.assertGreaterEqual(now - start, wdt_time * 0.5)
        self.assertLess(now - start, wdt_time)

        # The watchdog should not have expired yet
        self.assertEqual(self.emu.swt.watchdog.running(), True)
        self.assertEqual(self.checkPendingExceptions(), [])

        # Run for a full WDT time
        sleep_time = wdt_time
        self.emu.resume_time()
        self.emu.sleep(sleep_time)
        self.emu.halt_time()

        # The watchdog timer should have expired by now, but only once
        now = self.emu.systime()
        logger.debug('2. [%f] WDT time remaining = %f', now, self.emu.swt.watchdog.time())
        self.assertGreater(now - start, wdt_time * 1.5)
        self.assertLess(now - start, wdt_time * 2)

        self.assertEqual(self.emu.swt.watchdog.running(), True)
        self.assertEqual(self._getPendingExceptions(),
                [intc_exc.ExternalException(intc_exc.INTC_SRC.SWT)])

        # Before a reset the ECSM MRSR[SWTR] should be 0 and MRSR[POR] should be
        # set since this was the first boot.
        self.assertEqual(self.emu.readMemValue(*SIU_RSR), SIU_RSR_PORS)
        self.assertEqual(self.emu.readMemValue(*ECSM_MRSR), ECSM_MRSR_POR)

        # Wait for another half WDT time for the watchdog to expire again.  The
        # second expiration should generate a ResetException
        sleep_time = wdt_time * 0.5
        self.emu.resume_time()
        self.emu.sleep(sleep_time)
        self.emu.halt_time()

        # Watchdog should have expired twice now
        now = self.emu.systime()
        logger.debug('3. [%f] WDT time remaining = %f', now, self.emu.swt.watchdog.time())
        self.assertGreater(now - start, wdt_time * 2.0)
        self.assertLess(now - start, wdt_time * 2.5)
        self.assertEqual(self.emu.swt.watchdog.running(), False)

        # a reset exception should be queued
        reset_exc = intc_exc.ResetException(intc_exc.ResetSource.WATCHDOG)
        self.assertEqual(self.checkPendingExceptions(), [reset_exc])

        # Process the reset exception
        self.emu.stepi()

        # queue the exception as it would be if this had happened while 
        # processing an instruction, step and then check that the watchdog is 
        # marked as the source of the reset
        self.assertEqual(self.emu.readMemValue(*SIU_RSR), SIU_RSR_SWTRS)
        self.assertEqual(self.emu.readMemValue(*ECSM_MRSR), ECSM_MRSR_SWTR)
