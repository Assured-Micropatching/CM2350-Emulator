import time

import envi.bits as e_bits
import envi.archs.ppc.spr as eaps
import envi.archs.ppc.regs as eapr

from .. import emutimers

from .helpers import MPC5674_Test


# MFSPR/MTSPR constants
MFSPR_VAL       = 0x7C0002A6
MTSPR_VAL       = 0x7C0003A6
INSTR_REG_SHIFT = 21
INSTR_SPR_SHIFT = 11

TIMING_ACCURACY = 0.010


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

        freq = self.emu.getSystemFreq()

        # Sleep for 1 emulated second (1.0 * system scaling) and ensure that
        # approximately the correct amount of time has elapsed (allowing for the
        # inaccuracy of python sleep durations)
        self.emu.resume_time()
        time.sleep(1.0)
        self.emu.halt_time()

        tbl, tbu = self.tb_read()

        # Determine the expected upper range based on sleeping for 1 second and
        # the current scaling factor.  The expected margin of accuracy is about
        # 0.005 seconds
        expected_tbl = int(1.0 * freq * self.emu._systime_scaling)
        margin = TIMING_ACCURACY * freq * self.emu._systime_scaling

        self.assertAlmostEqual(tbl, expected_tbl, delta=margin)

        # Not enough time has passed for TBU to have a non-zero value.
        self.assertEqual(tbu, 0)

        # The systicks function should return the same value
        self.assertEqual(self.emu.systicks(), (tbu << 32) | tbl)

        # Writing to the TBL/TBU SPRs should have no effect
        # TODO: this may need to produce an error eventually.
        self.tb_write(0, tbl=eapr.REG_TB, tbu=eapr.REG_TBU)

        # Values read should be unchanged
        self.assertEqual(self.tb_read(), (tbl, tbu))

    def test_spr_tb_write(self):
        # Ensure TBL and TBR are 0 by default
        self.assertEqual(self.tb_read(), (0, 0))

        freq = self.emu.getSystemFreq()

        # Sleep for 1 second and ensure that approximately the correct amount of
        # time has elapsed (allowing for the inaccuracy of python sleep
        # durations)
        self.emu.resume_time()
        time.sleep(1.0)
        self.emu.halt_time()

        tbl, tbu = self.tb_read()

        # Determine the expected upper range based on sleeping for 1 second and
        # the current scaling factor.  The expected margin of accuracy is about
        # 0.005 seconds
        expected_tbl = int(1.0 * freq * self.emu._systime_scaling)
        margin = TIMING_ACCURACY * freq * self.emu._systime_scaling

        self.assertAlmostEqual(tbl, expected_tbl, delta=margin)

        # Not enough time has passed for TBU to have a non-zero value.
        self.assertEqual(tbu, 0)

        # Read from the Write-Only TB SPRs, they should still be 0
        # TODO: this may need to produce an error eventually.
        self.assertEqual(self.tb_read(tbl=eapr.REG_TBL_WO, tbu=eapr.REG_TBU_WO), (0, 0))

        # Change the TB offset
        self.tb_write(0)

        # Ensure that TBL/TBU now return 0
        self.assertEqual(self.tb_read(), (0, 0))
        self.assertEqual(self.emu.systicks(), 0)

        # The tb offset should match the timebase/systicks values we just read
        self.assertEqual(self.emu._tb_offset, (tbu << 32) | tbl)

        # Sleep 1 more second
        self.emu.resume_time()
        time.sleep(1.0)
        self.emu.halt_time()

        tbl2, tbu2 = self.tb_read()

        # Accuracy margin should be the same as before
        expected_tbl = int(1.0 * freq * self.emu._systime_scaling)
        self.assertAlmostEqual(tbl2, expected_tbl, delta=margin)

        # Not enough time has passed for TBU to have a non-zero value.
        self.assertEqual(tbu2, 0)

        # the systicks() function should return the same value
        self.assertEqual(self.emu.systicks(), (tbu2 << 32) | tbl2)

        # Call the non-PPC systicks() function, it should return the sum of both
        # timebase reads
        expected_ticks = ((tbu + tbu2) << 32) | (tbl + tbl2)
        self.assertEqual(emutimers.EmulationTime.systicks(self.emu), expected_ticks)

    def test_spr_tbl_overflow(self):
        self.assertEqual(self.tb_read(), (0, 0))
        self.assertEqual(self.emu.systicks(), 0)

        # Change the current TB offset to be < 50 msec worth of ticks from
        # 0xFFFFFFFF, sleep 0.1 second and confirm that TBU has a value of 1 and
        # the TBL has a value of approximately 50 msec ticks.
        freq = self.emu.getSystemFreq()
        tb_offset = 0xFFFF_FFFF - int(0.05 * freq * self.emu._systime_scaling)
        self.tb_write(tb_offset)

        # The TBL/TBU values should match the offset just written
        self.assertEqual(self.tb_read(), (tb_offset, 0))
        self.assertEqual(self.emu.systicks(), tb_offset)

        # Sleep 0.1 second
        self.emu.resume_time()
        time.sleep(0.1)
        self.emu.halt_time()

        tbl, tbu = self.tb_read()

        # Determine the expected upper range based on sleeping for 1 second and
        # the current scaling factor.  The expected margin of accuracy is about
        # 0.005 seconds
        expected_tbl = int(0.05 * freq * self.emu._systime_scaling)
        margin = TIMING_ACCURACY * freq * self.emu._systime_scaling

        self.assertAlmostEqual(tbl, expected_tbl, delta=margin)

        # TBU should finally be 1
        self.assertEqual(tbu, 1)

        self.assertEqual(self.emu.systicks(), 0x100000000 + tbl)
        self.assertEqual(self.emu.systicks(), (tbu << 32) | tbl)

    def test_spr_tbu_overflow(self):
        self.assertEqual(self.tb_read(), (0, 0))
        self.assertEqual(self.emu.systicks(), 0)

        # Change the current TB offset to be < 50 msec worth of ticks from
        # 0xFFFFFFFFFFFFFFFF, sleep 0.1 second and confirm that TBU has reset
        # back to a value of 1 and the TBL has a value of approximately 50 msec ticks.
        freq = self.emu.getSystemFreq()
        tb_offset = 0xFFFF_FFFF_FFFF_FFFF - int(0.05 * freq * self.emu._systime_scaling)
        self.tb_write(tb_offset)

        # Because the system time is still at 0 when we wrote a new offset, the
        # current emu._tb_offset should be -tb_offset
        self.assertEqual(self.emu._tb_offset, - tb_offset)

        # The TBL/TBU values should match the offset just written
        self.assertEqual(self.tb_read(), ((tb_offset & 0xFFFF_FFFF), 0xFFFF_FFFF))
        self.assertEqual(self.emu.systicks(), tb_offset)

        # Sleep 0.1 second (scaled based on the systime scaling)
        self.emu.resume_time()
        time.sleep(0.1)
        self.emu.halt_time()

        tbl, tbu = self.tb_read()

        # Determine the expected upper range based on sleeping for 1 second and
        # the current scaling factor.  The expected margin of accuracy is about
        # 0.005 seconds
        expected_tbl = int(0.05 * freq * self.emu._systime_scaling)
        margin = TIMING_ACCURACY * freq * self.emu._systime_scaling

        self.assertAlmostEqual(tbl, expected_tbl, delta=margin)

        # TBU should have overflowed back to 0
        self.assertEqual(tbu, 0)

        tb = (tbu << 32) | tbl
        self.assertEqual(tb, tbl)
        self.assertEqual(self.emu.systicks(), 0x10000000000000000 + tbl)
        self.assertEqual(self.emu.systicks(), 0x10000000000000000 + tb)
