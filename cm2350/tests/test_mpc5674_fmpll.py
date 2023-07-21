from .helpers import MPC5674_Test


FMPLL_SYNSR        = 0xC3F80004
FMPLL_ESYNCR1      = 0xC3F80008
FMPLL_ESYNCR2      = 0xC3F8000C
FMPLL_SYNFMCR      = 0xC3F80020

# FMPLL peripheral register non-zero values
#
# The default value of SYNSR is all 0's.  Only the LOLF and LOCF flags
# can be written to and they are write-1-to-clear.
#
# However:
#   - The SYNSR[LOCKS] and SYNSR[LOCK] bits should be set during
#   initialization to simulate the FMPLL device locking on to the
#   external oscillator clock.
#
#   - The SYNSR[MODE] is the read-only reflection of ESYNCR1[CLKCFG2]
#   - The SYNSR[PLLSEL] is the read-only reflection of ESYNCR1[CLKCFG1]
#   - The SYNSR[PLLREF] is the read-only reflection of ESYNCR1[CLKCFG0]
#
# The initial value of ESYNCR1[CLKCFG] (and 1 bit of ESYNCR1[EPREDIV]) reflects
# the external PLLCFG pins and this emulation assumes that PLLCFG is set to
# 0b110 which means the initial value of ESYNCR1[CLKCFG] should be 0b111
FMPLL_SYNSR_DEFAULT         = 0x000000F8
FMPLL_ESYNCR1_DEFAULT       = 0xF0030020
FMPLL_ESYNCR2_DEFAULT       = 0x00000007
FMPLL_SYNSR_DEFAULT_BYTES   = b'\x00\x00\x00\xF8'
FMPLL_ESYNCR1_DEFAULT_BYTES = b'\xF0\x03\x00\x20'
FMPLL_ESYNCR2_DEFAULT_BYTES = b'\x00\x00\x00\x07'

FMPLL_ESYNCR1_EPREDIV_MASK  = 0x000F0000
FMPLL_ESYNCR1_EPREDIV_SHIFT = 16
FMPLL_ESYNCR1_EMFD_MASK     = 0x000000FF
FMPLL_ESYNCR1_EMFD_SHIFT    = 0
FMPLL_ESYNCR2_ERFD_MASK     = 0x0000003F
FMPLL_ESYNCR2_ERFD_SHIFT    = 0


class MPC5674_FMPLL_Test(MPC5674_Test):
    # Default to 40MHz external clock
    EXTAL = 40000000
    PLLCFG = 0b101

    # Expect the default ESYNCR1 values
    ESYNCR1_VALUE = FMPLL_ESYNCR1_DEFAULT
    ESYNCR1_BYTES = FMPLL_ESYNCR1_DEFAULT_BYTES

    # PLL is calculated with:
    #   f_pll = (f_extal*(EMFD+16)) / ((EPREDIV+1)*(ERFD+1))
    #
    # The default values are:
    #   f_extal          = 40000000
    #   ESYNCR1[EPREDIV] = 3
    #   ESYNCR1[EMFD]    = 32
    #   ESYNCR2[ERFD]    = 7
    #
    # So the default output clock should be:
    #   f_pll = (40000000*(32+16)) / ((3+1)*(7+1))
    #   f_pll = (40000000*48) / 32
    #   f_pll = 60000000
    PLL = 60000000.0

    # Need some PLL values based on the clock changes made in
    # test_fmpll_change_freq()
    #
    # Change slowly from the default values to:
    #   f_extal          = 40000000
    #   ESYNCR1[EPREDIV] = 7
    #   ESYNCR1[EMFD]    = 16
    #   ESYNCR2[ERFD]    = 5
    #
    # The output PLL at each step is:
    #   f_pll = (40000000*(EMFD+16)) / ((EPREDIV+1)*(ERFD+1))
    #   f_pll = (40000000*(16+16)) / ((5+1)*(7+1))
    #   f_pll = (40000000*32) / 58
    #   f_pll = 30000000
    FREQ_TEST_VALUES = [
        30000000.0,         # ESYNCR1[EPREDIV] = 7
        20000000.0,         # ESYNCR1[EMFD] = 16
        26666666.66666666,  # ESYNCR2[ERFD] = 5
    ]

    # Add specific EXTAL and PLLCFG startup arguments
    args = MPC5674_Test.args + [
        '-O', 'project.MPC5674.FMPLL.extal=%d' % EXTAL,
        '-O', 'project.MPC5674.SIU.pllcfg=%d' % PLLCFG,
    ]

    def test_fmpll_synsr_defaults(self):
        self.assertEqual(self.emu.readMemory(FMPLL_SYNSR, 4), FMPLL_SYNSR_DEFAULT_BYTES)
        self.assertEqual(self.emu.readMemValue(FMPLL_SYNSR, 4), FMPLL_SYNSR_DEFAULT)
        self.assertEqual(self.emu.fmpll.registers.synsr.lolf, 0)
        self.assertEqual(self.emu.fmpll.registers.synsr.loc, 0)
        self.assertEqual(self.emu.fmpll.registers.synsr.mode, 1)
        self.assertEqual(self.emu.fmpll.registers.synsr.pllsel, 1)
        self.assertEqual(self.emu.fmpll.registers.synsr.pllref, 1)
        self.assertEqual(self.emu.fmpll.registers.synsr.locks, 1)
        self.assertEqual(self.emu.fmpll.registers.synsr.lock, 1)
        self.assertEqual(self.emu.fmpll.registers.synsr.locf, 0)

    def test_fmpll_esyncr1_defaults(self):
        # The default value of ESYNCR1 changes based on the external oscillator
        # and PLLCFG
        self.assertEqual(self.emu.readMemory(FMPLL_ESYNCR1, 4), self.ESYNCR1_BYTES)
        self.assertEqual(self.emu.readMemValue(FMPLL_ESYNCR1, 4), self.ESYNCR1_VALUE)
        self.assertEqual(self.emu.fmpll.registers.esyncr1.clkcfg, 7)

        eprediv = (self.ESYNCR1_VALUE & FMPLL_ESYNCR1_EPREDIV_MASK) >> FMPLL_ESYNCR1_EPREDIV_SHIFT
        self.assertEqual(self.emu.fmpll.registers.esyncr1.eprediv, eprediv)

        self.assertEqual(self.emu.fmpll.registers.esyncr1.emfd, 32)

    def test_fmpll_esyncr2_defaults(self):
        self.assertEqual(self.emu.readMemory(FMPLL_ESYNCR2, 4), FMPLL_ESYNCR2_DEFAULT_BYTES)
        self.assertEqual(self.emu.readMemValue(FMPLL_ESYNCR2, 4), FMPLL_ESYNCR2_DEFAULT)
        self.assertEqual(self.emu.fmpll.registers.esyncr2.locen, 0)
        self.assertEqual(self.emu.fmpll.registers.esyncr2.lolre, 0)
        self.assertEqual(self.emu.fmpll.registers.esyncr2.locre, 0)
        self.assertEqual(self.emu.fmpll.registers.esyncr2.lolirq, 0)
        self.assertEqual(self.emu.fmpll.registers.esyncr2.locirq, 0)
        self.assertEqual(self.emu.fmpll.registers.esyncr2.erate, 0)
        self.assertEqual(self.emu.fmpll.registers.esyncr2.clkcfg_dis, 0)
        self.assertEqual(self.emu.fmpll.registers.esyncr2.edepth, 0)
        self.assertEqual(self.emu.fmpll.registers.esyncr2.erfd, 7)

    def test_fmpll_synfmcr_defaults(self):
        self.assertEqual(self.emu.readMemory(FMPLL_SYNFMCR, 4), b'\x00\x00\x00\x00')
        self.assertEqual(self.emu.readMemValue(FMPLL_SYNFMCR, 4), 0)
        self.assertEqual(self.emu.fmpll.registers.synfmcr.fmdac_en, 0)
        self.assertEqual(self.emu.fmpll.registers.synfmcr.fmdac_ctl, 0)

    def test_fmpll_change_clkcfg(self):
        # The SYNSR[MODE], SYNSR[PLLSEL], and SYNSR[PLLREF] bits are based off
        # of the ESYNCR1[CLKCFG] values.
        #
        # The most meaningful CLKCFG values are (from AN11960.pdf):
        #   0b111 - Clock Mode Normal w/ Crystal Ref PLL On
        #   0b011 - Clock Mode Bypass w/ Crystal Ref and PLL On
        #   0b001 - Clock Mode Bypass w/ Crystal Ref PLL Off
        #
        # There also is:
        #   0b000 - Clock Mode Bypass w/ Clock Ref PLL Off
        #
        # The default value is 0b111 so test 0b011 and 0b001

        # ESYNCR1[CLKCFG] = 0b011
        esyncr1_val = self.ESYNCR1_VALUE & 0xBFFFFFFF
        self.emu.writeMemValue(FMPLL_ESYNCR1, esyncr1_val, 4)

        # Confirm value was written
        self.assertEqual(self.emu.readMemValue(FMPLL_ESYNCR1, 4), esyncr1_val)

        # Confirm that mode and pllsel are off, and the PLL lock is not set
        self.assertEqual(self.emu.fmpll.registers.synsr.mode, 0)
        self.assertEqual(self.emu.fmpll.registers.synsr.pllsel, 0)
        self.assertEqual(self.emu.fmpll.registers.synsr.pllref, 0)
        self.assertEqual(self.emu.fmpll.registers.synsr.locks, 0)
        self.assertEqual(self.emu.fmpll.registers.synsr.lock, 0)

        # PLL should now be the same as the external oscillator frequency
        self.assertEqual(self.emu.fmpll.f_pll(), float(self.EXTAL))

        # ESYNCR1[CLKCFG] = 0b001
        esyncr1_val = self.ESYNCR1_VALUE & 0x9FFFFFFF
        self.emu.writeMemValue(FMPLL_ESYNCR1, esyncr1_val, 4)

        # Confirm value was written
        self.assertEqual(self.emu.readMemValue(FMPLL_ESYNCR1, 4), esyncr1_val)

        # Confirm that PLL is now off and not locked, and clock mode is bypass
        self.assertEqual(self.emu.fmpll.registers.synsr.mode, 0)
        self.assertEqual(self.emu.fmpll.registers.synsr.pllsel, 0)
        self.assertEqual(self.emu.fmpll.registers.synsr.pllref, 0)
        self.assertEqual(self.emu.fmpll.registers.synsr.locks, 0)
        self.assertEqual(self.emu.fmpll.registers.synsr.lock, 0)

        # PLL should still be the same as the external oscillator frequency
        self.assertEqual(self.emu.fmpll.f_pll(), float(self.EXTAL))

        # ESYNCR1[CLKCFG] = 0b000
        esyncr1_val = FMPLL_ESYNCR1_DEFAULT & 0x8FFFFFFF
        self.emu.writeMemValue(FMPLL_ESYNCR1, esyncr1_val, 4)

        # Confirm value was written
        self.assertEqual(self.emu.readMemValue(FMPLL_ESYNCR1, 4), esyncr1_val)

        # Confirm that mode, pllsel, and pllref are all off
        self.assertEqual(self.emu.fmpll.registers.synsr.mode, 0)
        self.assertEqual(self.emu.fmpll.registers.synsr.pllsel, 0)
        self.assertEqual(self.emu.fmpll.registers.synsr.pllref, 0)
        self.assertEqual(self.emu.fmpll.registers.synsr.locks, 0)
        self.assertEqual(self.emu.fmpll.registers.synsr.lock, 0)

        # PLL should still be the same as the external oscillator frequency
        self.assertEqual(self.emu.fmpll.f_pll(), float(self.EXTAL))

    def test_fmpll_default_freq(self):
        self.assertEqual(self.emu.vw.config.project.MPC5674.FMPLL.extal, self.EXTAL)
        self.assertEqual(self.emu.fmpll.f_pll(), self.PLL)

    def test_fmpll_change_freq(self):
        # PLL is calculated with:
        #   f_pll = (f_extal*(EMFD+16)) / ((EPREDIV+1)*(ERFD+1))
        #
        # The default values are:
        #   f_extal          = 40000000
        #   ESYNCR1[EPREDIV] = 3
        #   ESYNCR1[EMFD]    = 32
        #   ESYNCR2[ERFD]    = 7
        #
        # So the default output clock should be:
        #   f_pll = (40000000*(32+16)) / ((3+1)*(7+1))
        #   f_pll = (40000000*48) / 32
        #   f_pll = 60000000
        self.assertEqual(self.emu.vw.config.project.MPC5674.FMPLL.extal, self.EXTAL)
        self.assertEqual(self.emu.fmpll.f_pll(), self.PLL)

        # Change slowly from the default values to:
        #   f_extal          = 40000000
        #   ESYNCR1[EPREDIV] = 7
        #   ESYNCR1[EMFD]    = 16
        #   ESYNCR2[ERFD]    = 5
        #
        # The output PLL at each step is:
        #   ESYNCR1[EPREDIV] = 7
        #       f_pll = (40000000*(32+16)) / ((7+1)*(7+1))
        #       f_pll = (40000000*48) / 64
        #       f_pll = 30000000

        esyncr1_val = (self.ESYNCR1_VALUE & ~FMPLL_ESYNCR1_EPREDIV_MASK) | (7 << FMPLL_ESYNCR1_EPREDIV_SHIFT)
        self.emu.writeMemValue(FMPLL_ESYNCR1, esyncr1_val, 4)

        # Confirm value was written
        self.assertEqual(self.emu.readMemValue(FMPLL_ESYNCR1, 4), esyncr1_val)

        # Check ESYNCR1 and ESYNCR2
        self.assertEqual(self.emu.fmpll.registers.esyncr1.clkcfg, 7)
        self.assertEqual(self.emu.fmpll.registers.esyncr1.eprediv, 7)
        self.assertEqual(self.emu.fmpll.registers.esyncr1.emfd, 32)
        self.assertEqual(self.emu.fmpll.registers.esyncr2.erfd, 7)

        # Confirm the SYNSR PLL settings haven't changed
        self.assertEqual(self.emu.fmpll.registers.synsr.mode, 1)
        self.assertEqual(self.emu.fmpll.registers.synsr.pllsel, 1)
        self.assertEqual(self.emu.fmpll.registers.synsr.pllref, 1)
        self.assertEqual(self.emu.fmpll.registers.synsr.locks, 1)
        self.assertEqual(self.emu.fmpll.registers.synsr.lock, 1)

        # PLL should now be 30MHz
        self.assertEqual(self.emu.fmpll.f_pll(), self.FREQ_TEST_VALUES[0])

        #   ESYNCR1[EMFD]    = 16
        #       f_pll = (40000000*(16+16)) / ((7+1)*(7+1))
        #       f_pll = (40000000*32) / 64
        #       f_pll = 20000000

        esyncr1_val = (esyncr1_val & ~FMPLL_ESYNCR1_EMFD_MASK) | (16 << FMPLL_ESYNCR1_EMFD_SHIFT)
        self.emu.writeMemValue(FMPLL_ESYNCR1, esyncr1_val, 4)

        # Confirm value was written
        self.assertEqual(self.emu.readMemValue(FMPLL_ESYNCR1, 4), esyncr1_val)

        # Check ESYNCR1 and ESYNCR2
        self.assertEqual(self.emu.fmpll.registers.esyncr1.clkcfg, 7)
        self.assertEqual(self.emu.fmpll.registers.esyncr1.eprediv, 7)
        self.assertEqual(self.emu.fmpll.registers.esyncr1.emfd, 16)
        self.assertEqual(self.emu.fmpll.registers.esyncr2.erfd, 7)

        # Confirm the SYNSR PLL settings haven't changed
        self.assertEqual(self.emu.fmpll.registers.synsr.mode, 1)
        self.assertEqual(self.emu.fmpll.registers.synsr.pllsel, 1)
        self.assertEqual(self.emu.fmpll.registers.synsr.pllref, 1)
        self.assertEqual(self.emu.fmpll.registers.synsr.locks, 1)
        self.assertEqual(self.emu.fmpll.registers.synsr.lock, 1)

        # PLL should now be 20MHz
        self.assertEqual(self.emu.fmpll.f_pll(), self.FREQ_TEST_VALUES[1])

        #   ESYNCR2[ERFD]    = 5
        #       f_pll = (40000000*(16+16)) / ((7+1)*(5+1))
        #       f_pll = (40000000*32) / 48
        #       f_pll = 26666666

        esyncr2_val = (FMPLL_ESYNCR2_DEFAULT & ~FMPLL_ESYNCR2_ERFD_MASK) | (5 << FMPLL_ESYNCR2_ERFD_SHIFT)
        self.emu.writeMemValue(FMPLL_ESYNCR2, esyncr2_val, 4)

        # Confirm value was written
        self.assertEqual(self.emu.readMemValue(FMPLL_ESYNCR2, 4), esyncr2_val)

        # Check ESYNCR1 and ESYNCR2
        self.assertEqual(self.emu.fmpll.registers.esyncr1.clkcfg, 7)
        self.assertEqual(self.emu.fmpll.registers.esyncr1.eprediv, 7)
        self.assertEqual(self.emu.fmpll.registers.esyncr1.emfd, 16)
        self.assertEqual(self.emu.fmpll.registers.esyncr2.erfd, 5)

        # Confirm the SYNSR PLL settings haven't changed
        self.assertEqual(self.emu.fmpll.registers.synsr.mode, 1)
        self.assertEqual(self.emu.fmpll.registers.synsr.pllsel, 1)
        self.assertEqual(self.emu.fmpll.registers.synsr.pllref, 1)
        self.assertEqual(self.emu.fmpll.registers.synsr.locks, 1)
        self.assertEqual(self.emu.fmpll.registers.synsr.lock, 1)

        # PLL should now be ~26.66MHz
        self.assertAlmostEqual(self.emu.fmpll.f_pll(), self.FREQ_TEST_VALUES[2])

    def test_fmpll_pll_off(self):
        # Change the ESYNCR1[CLKCFG] settings to disable the PLL (0b000)

        esyncr1_val = FMPLL_ESYNCR1_DEFAULT & 0x8FFFFFFF
        self.emu.writeMemValue(FMPLL_ESYNCR1, esyncr1_val, 4)

        # Confirm value was written
        self.assertEqual(self.emu.readMemValue(FMPLL_ESYNCR1, 4), esyncr1_val)

        # Confirm the SYNSR PLL settings indicate that the PLL Mode is no longer
        # active and there is no PLL lock
        self.assertEqual(self.emu.fmpll.registers.synsr.mode, 0)
        self.assertEqual(self.emu.fmpll.registers.synsr.pllsel, 0)
        self.assertEqual(self.emu.fmpll.registers.synsr.pllref, 0)
        self.assertEqual(self.emu.fmpll.registers.synsr.locks, 0)
        self.assertEqual(self.emu.fmpll.registers.synsr.lock, 0)

        # PLL should now be the same as the external oscillator/clock frequency
        self.assertEqual(self.emu.fmpll.f_pll(), float(self.EXTAL))

    def test_fmpll_clkcfg_disable(self):
        self.assertEqual(self.emu.fmpll.registers.esyncr1.clkcfg, 7)

        # The default EPREDIV value changes based on PLLCFG
        eprediv = (self.ESYNCR1_VALUE & FMPLL_ESYNCR1_EPREDIV_MASK) >> FMPLL_ESYNCR1_EPREDIV_SHIFT
        self.assertEqual(self.emu.fmpll.registers.esyncr1.eprediv, eprediv)
        self.assertEqual(self.emu.fmpll.registers.esyncr1.emfd, 32)
        self.assertEqual(self.emu.fmpll.registers.esyncr2.clkcfg_dis, 0)

        # Set ESYNCR2[CLKCFG_DIS] so ESYNCR1[CLKCFG] cannot be modified
        esyncr2_val = FMPLL_ESYNCR2_DEFAULT | 0x00008000
        self.emu.writeMemValue(FMPLL_ESYNCR2, esyncr2_val, 4)

        # Confirm value was written
        self.assertEqual(self.emu.readMemValue(FMPLL_ESYNCR2, 4), esyncr2_val)
        self.assertEqual(self.emu.fmpll.registers.esyncr2.clkcfg_dis, 1)

        # Attempt to modify every field in ESYNCR1
        self.emu.writeMemValue(FMPLL_ESYNCR1, 0, 4)

        # Ensure that EPREDIV and EMFD changed, but not CLKCFG
        self.assertEqual(self.emu.readMemValue(FMPLL_ESYNCR1, 4), 0xF0000000)
        self.assertEqual(self.emu.fmpll.registers.esyncr1.clkcfg, 7)
        self.assertEqual(self.emu.fmpll.registers.esyncr1.eprediv, 0)
        self.assertEqual(self.emu.fmpll.registers.esyncr1.emfd, 0)


class MPC5674_FMPLL_20MHz_Test(MPC5674_FMPLL_Test):
    # 20MHz external clock
    EXTAL = 20000000
    PLLCFG = 0b100

    # Because the external clock on this test config is only 10MHz, the
    # ESYNCR1[EPREDIV] should be 0b0001 instead of 0b0011
    ESYNCR1_VALUE = 0xF0010020
    ESYNCR1_BYTES = b'\xF0\x01\x00\x20'

    # PLL is calculated with:
    #   f_pll = (f_extal*(EMFD+16)) / ((EPREDIV+1)*(ERFD+1))
    #
    # The default values are:
    #   f_extal          = 20000000
    #   ESYNCR1[EPREDIV] = 1
    #   ESYNCR1[EMFD]    = 32
    #   ESYNCR2[ERFD]    = 7
    #
    # So the default output clock should be:
    #   f_pll = (20000000*(32+16)) / ((1+1)*(7+1))
    #   f_pll = (20000000*48) / 16
    #   f_pll = 60000000
    PLL = 60000000.0

    # Need some PLL values based on the clock changes made in
    # test_fmpll_change_freq()
    #
    # Change slowly from the default values to:
    #   f_extal          = 40000000
    #   ESYNCR1[EPREDIV] = 7
    #   ESYNCR1[EMFD]    = 16
    #   ESYNCR2[ERFD]    = 5
    #
    # The output PLL at each step is:
    #   f_pll = (20000000*(EMFD+16)) / ((EPREDIV+1)*(ERFD+1))
    #   f_pll = (20000000*(16+16)) / ((5+1)*(7+1))
    #   f_pll = (20000000*32) / 48
    #   f_pll = 133333333.33333333
    FREQ_TEST_VALUES = [
        15000000.0,         # ESYNCR1[EPREDIV] = 7
        10000000.0,         # ESYNCR1[EMFD] = 16
        13333333.33333333,  # ESYNCR2[ERFD] = 5
    ]

    # Add specific EXTAL and PLLCFG startup arguments
    args = MPC5674_Test.args + [
        '-O', 'project.MPC5674.FMPLL.extal=%d' % EXTAL,
        '-O', 'project.MPC5674.SIU.pllcfg=%d' % PLLCFG,
    ]


class MPC5674_FMPLL_10MHz_Test(MPC5674_FMPLL_Test):
    # 10MHz external clock
    EXTAL = 10000000
    PLLCFG = 0b100

    # Because the external clock on this test config is only 10MHz, the
    # ESYNCR1[EPREDIV] should be 0b0001 instead of 0b0011
    ESYNCR1_VALUE = 0xF0010020
    ESYNCR1_BYTES = b'\xF0\x01\x00\x20'

    # PLL is calculated with:
    #   f_pll = (f_extal*(EMFD+16)) / ((EPREDIV+1)*(ERFD+1))
    #
    # The default values are:
    #   f_extal          = 10000000
    #   ESYNCR1[EPREDIV] = 1
    #   ESYNCR1[EMFD]    = 32
    #   ESYNCR2[ERFD]    = 7
    #
    # So the default output clock should be:
    #   f_pll = (10000000*(32+16)) / ((1+1)*(7+1))
    #   f_pll = (10000000*48) / 16
    #   f_pll = 30000000
    PLL = 30000000.0

    # Need some PLL values based on the clock changes made in
    # test_fmpll_change_freq()
    #
    # Change slowly from the default values to:
    #   f_extal          = 10000000
    #   ESYNCR1[EPREDIV] = 7
    #   ESYNCR1[EMFD]    = 16
    #   ESYNCR2[ERFD]    = 5
    #
    # The output PLL at each step is:
    #   f_pll = (10000000*(EMFD+16)) / ((EPREDIV+1)*(ERFD+1))
    #   f_pll = (10000000*(16+16)) / ((7+1)*(5+1))
    #   f_pll = (10000000*32) / 48
    #   f_pll = 6666666.66666666
    FREQ_TEST_VALUES = [
        7500000.0,          # ESYNCR1[EPREDIV] = 7
        5000000.0,          # ESYNCR1[EMFD] = 16
        6666666.66666666,   # ESYNCR2[ERFD] = 5
    ]

    # Add specific EXTAL and PLLCFG startup arguments
    args = MPC5674_Test.args + [
        '-O', 'project.MPC5674.FMPLL.extal=%d' % EXTAL,
        '-O', 'project.MPC5674.SIU.pllcfg=%d' % PLLCFG,
    ]
