import envi.bits as e_bits
import envi.archs.ppc.regs as eapr

from .helpers import MPC5674_Test


# MFSPR/MTSPR constants
MFSPR_VAL       = 0x7C0002A6
MTSPR_VAL       = 0x7C0003A6
INSTR_REG_SHIFT = 21
INSTR_SPR_SHIFT = 11

# Because of how we are measuring elapsed time in the tests this should be 
# extremely accurate
TIMING_ACCURACY = 0.002


class MPC5674_SPRHOOKS_Test(MPC5674_Test):
    accurate_timing = True

    def tb_read(self, tbl=eapr.REG_TB, tbu=eapr.REG_TBU, reg=eapr.REG_R3):
        # Get the actual PPC SPR numbers
        ppctbl = self.get_spr_num(tbl)
        ppctbu = self.get_spr_num(tbu)

        # The SPR has the lower 5 bits at:
        #   0x001F0000
        # and the upper 5 bits at
        #   0x0000F100
        encoded_tbl = ((ppctbl & 0x1F) << 5) | ((ppctbl >> 5) & 0x1F)
        encoded_tbu = ((ppctbu & 0x1F) << 5) | ((ppctbu >> 5) & 0x1F)

        mftbl_val = MFSPR_VAL | (reg << INSTR_REG_SHIFT) | (encoded_tbl << INSTR_SPR_SHIFT)
        mftbl_bytes = e_bits.buildbytes(mftbl_val, 4, self.emu.getEndian())
        mftbl_op = self.emu.archParseOpcode(mftbl_bytes)

        mftbu_val = MFSPR_VAL | (reg << INSTR_REG_SHIFT) | (encoded_tbu << INSTR_SPR_SHIFT)
        mftbu_bytes = e_bits.buildbytes(mftbu_val, 4, self.emu.getEndian())
        mftbu_op = self.emu.archParseOpcode(mftbu_bytes)

        self.emu.executeOpcode(mftbl_op)
        tbl_val = self.emu.getRegister(reg)

        self.emu.executeOpcode(mftbu_op)
        tbu_val = self.emu.getRegister(reg)

        return (tbl_val, tbu_val)

    def tb_write(self, value, tbl=eapr.REG_TBL_WO, tbu=eapr.REG_TBU_WO, reg=eapr.REG_R3):
        # Get the actual PPC SPR numbers
        ppctbl = self.get_spr_num(tbl)
        ppctbu = self.get_spr_num(tbu)

        # The SPR has the lower 5 bits at:
        #   0x001F0000
        # and the upper 5 bits at
        #   0x0000F100
        encoded_tbl = ((ppctbl & 0x1F) << 5) | ((ppctbl >> 5) & 0x1F)
        encoded_tbu = ((ppctbu & 0x1F) << 5) | ((ppctbu >> 5) & 0x1F)

        mttbl_val = MTSPR_VAL | (reg << INSTR_REG_SHIFT) | (encoded_tbl << INSTR_SPR_SHIFT)
        mttbl_bytes = e_bits.buildbytes(mttbl_val, 4, self.emu.getEndian())
        mttbl_op = self.emu.archParseOpcode(mttbl_bytes)

        mttbu_val = MTSPR_VAL | (reg << INSTR_REG_SHIFT) | (encoded_tbu << INSTR_SPR_SHIFT)
        mttbu_bytes = e_bits.buildbytes(mttbu_val, 4, self.emu.getEndian())
        mttbu_op = self.emu.archParseOpcode(mttbu_bytes)

        # Write the upper 32-bits to TBU first
        self.emu.setRegister(reg, (value >> 32) & 0xFFFFFFFF)
        self.emu.executeOpcode(mttbu_op)

        # Write the lower 32-bits to TBL
        self.emu.setRegister(reg, value & 0xFFFFFFFF)
        self.emu.executeOpcode(mttbl_op)

    def test_spr_tb_read(self):
        # Ensure TBL and TBR are 0 by default
        self.assertEqual(self.tb_read(), (0, 0))

        # Start the PPC core timebase
        self.emu.enableTimebase()

        # Sleep for 0.1 second of emulated time
        self.emu.sleep(0.1)

        # Stop all emulator time (also pauses the PPC timebase)
        self.emu.halt_time()

        tbl, tbu = self.tb_read()

        expected_tbl = int(0.1 * self.emu.getSystemFreq())
        margin = TIMING_ACCURACY * expected_tbl

        self.assert_timer_within_range(tbl, expected_tbl, margin)

        # Not enough time has passed for TBU to have a non-zero value.
        self.assertEqual(tbu, 0)

        # The getTimebase function should return the same value
        self.assertEqual(self.emu.getTimebase(), (tbu << 32) | tbl)

        # Writing to the TBL/TBU SPRs should have no effect
        # TODO: this may need to produce an error eventually.
        self.tb_write(0, tbl=eapr.REG_TB, tbu=eapr.REG_TBU)

        # Values read should be unchanged
        self.assertEqual(self.tb_read(), (tbl, tbu))

    def test_spr_tb_write(self):
        # Ensure TBL and TBR are 0 by default
        self.assertEqual(self.tb_read(), (0, 0))

        # Start the PPC core timebase
        self.emu.enableTimebase()

        # Sleep for 0.1 second of emulated time
        self.emu.sleep(0.1)

        # Stop all emulator time (also pauses the PPC timebase)
        self.emu.halt_time()

        tbl, tbu = self.tb_read()

        # Determine the expected upper range based on the elapsed emulated time.
        expected_tbl = int(0.1 * self.emu.getSystemFreq())
        margin = TIMING_ACCURACY * expected_tbl

        self.assert_timer_within_range(tbl, expected_tbl, margin)

        # Not enough time has passed for TBU to have a non-zero value.
        self.assertEqual(tbu, 0)

        # Read from the Write-Only TB SPRs, they should still be 0
        self.assertEqual(self.tb_read(tbl=eapr.REG_TBL_WO, tbu=eapr.REG_TBU_WO), (0, 0))

        # Change the TB offset
        self.tb_write(0)

        # Ensure that TBL/TBU now return 0
        self.assertEqual(self.tb_read(), (0, 0))
        self.assertEqual(self.emu.getTimebase(), 0)

        # Start the timebase again sleep another 0.1 emulated seconds
        self.emu.resume_time()
        self.emu.sleep(0.1)
        self.emu.halt_time()

        tbl2, tbu2 = self.tb_read()

        # Accuracy margin should be the same as before
        expected_tbl = int(0.1 * self.emu.getSystemFreq())
        self.assert_timer_within_range(tbl2, expected_tbl, margin)

        # Not enough time has passed for TBU to have a non-zero value.
        self.assertEqual(tbu2, 0)

        # the systicks() function should return the same value
        self.assertEqual(self.emu.getTimebase(), (tbu2 << 32) | tbl2)

    def test_spr_tbl_overflow(self):
        self.assertEqual(self.tb_read(), (0, 0))

        # Stop all emulator time (also pauses the PPC timebase), but also start 
        # the PPC timebase
        self.emu.halt_time()
        self.emu.enableTimebase()

        # Set the time base lower value so it'll overflow
        tb_offset = 0xFFFFF000
        self.tb_write(tb_offset)

        # The TBL/TBU values should match the offset just written
        self.assertEqual(self.tb_read(), (tb_offset, 0))
        self.assertEqual(self.emu.getTimebase(), tb_offset)

        # Resume and run for about 0.1 seconds
        self.emu.resume_time()
        self.emu.sleep(0.1)
        self.emu.halt_time()

        tbl, tbu = self.tb_read()

        # Get the amount of emulated time that has elapsed
        expected_tb = int(0.1 * self.emu.getSystemFreq()) + tb_offset
        tb = (tbu << 32) | tbl

        # TBU should now be 1
        self.assertEqual(tbu, 1)
        self.assertEqual(tb, 0x100000000 + tbl)

        margin = TIMING_ACCURACY * expected_tb
        expected_tbl = expected_tb & 0xFFFFFFFF
        self.assert_timer_within_range(tbl, expected_tbl, margin)

        self.assertEqual(self.emu.getTimebase(), 0x100000000 + tbl)
        self.assertEqual(self.emu.getTimebase(), tb)
        self.assert_timer_within_range(self.emu.getTimebase(), expected_tb, margin)

    def test_spr_tbu_overflow(self):
        self.assertEqual(self.tb_read(), (0, 0))

        # Stop all emulator time (also pauses the PPC timebase), but also start 
        # the PPC timebase
        self.emu.halt_time()
        self.emu.enableTimebase()

        # Set the time base upper and lower values so TBL will overflow
        tb_offset = 0xFFFFFFFFFFFFF000
        self.tb_write(tb_offset)

        # The TBL/TBU values should match the offset just written
        self.assertEqual(self.tb_read(), (tb_offset & 0xFFFFFFFF, (tb_offset >> 32) & 0xFFFFFFFF))
        self.assertEqual(self.emu.getTimebase(), tb_offset)

        # Get the start emulated time
        now = self.emu.systime()

        # Resume and run for about 0.1 seconds
        self.emu.resume_time()
        self.emu.sleep(0.1)
        self.emu.halt_time()

        tbl, tbu = self.tb_read()

        expected_tb = int(0.1 * self.emu.getSystemFreq()) + tb_offset
        tb = (tbu << 32) | tbl

        # TBU should have overflowed back to 0
        self.assertEqual(tbu, 0)
        self.assertEqual(tb, tbl)

        margin = TIMING_ACCURACY * expected_tb
        expected_tbl = expected_tb & 0xFFFFFFFF
        self.assert_timer_within_range(tbl, expected_tbl, margin)

        self.assertEqual(self.emu.getTimebase(), 0x10000000000000000 + tbl)
        self.assertEqual(self.emu.getTimebase(), 0x10000000000000000 + tb)
        self.assert_timer_within_range(self.emu.getTimebase(), expected_tb, margin)
