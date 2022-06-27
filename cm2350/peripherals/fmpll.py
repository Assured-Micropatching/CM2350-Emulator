from ..ppc_vstructs import *
from ..ppc_peripherals import *
from ..intc_exc import MceDataReadBusError, MceWriteBusError

import logging
logger = logging.getLogger(__name__)

__all__  = [
    'FMPLL',
]


class FMPLL_SYNSR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(22)
        self.lolf = v_w1c(1)
        self.loc = v_const(1)
        self.mode = v_const(1)
        self.pllsel = v_const(1)
        self.pllref = v_const(1)
        self.locks = v_const(1)
        self.lock = v_const(1)
        self.locf = v_w1c(1)
        self.u = v_const(2)

class FMPLL_ESYNCR1(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(1, 1)
        self.clkcfg = v_bits(3)
        self._pad1 = v_const(8)
        self.eprediv = v_bits(4)
        self._pad2 = v_const(8)
        self.emfd = v_bits(8, 0x20)

class FMPLL_ESYNCR2(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(8)
        self.locen = v_bits(1)
        self.lolre = v_bits(1)
        self.locre = v_bits(1)
        self.lolirq = v_bits(1)
        self.locirq = v_bits(1)
        self._pad1 = v_const(1)
        self.erate = v_bits(2)
        self.clkcfg_dis = v_bits(1)
        self._pad2 = v_const(4)
        self.edepth = v_bits(3)
        self._pad3 = v_const(2)
        self.erfd = v_bits(6, 0x07)

class FMPLL_SYNFMCR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(1)
        self.fmdac_en = v_bits(1)
        self._pad1 = v_const(9)
        self.fmdac_ctl = v_bits(5)
        self._pad2 = v_const(16)


class FMPLL_REGISTERS(PeripheralRegisterSet):
    def __init__(self):
        super().__init__()

        self.synsr   = (0x0004, FMPLL_SYNSR())
        self.esyncr1 = (0x0008, FMPLL_ESYNCR1())
        self.esyncr2 = (0x000C, FMPLL_ESYNCR2())
        self.synfmcr = (0x0020, FMPLL_SYNFMCR())


class FMPLL(MMIOPeripheral):
    '''
    This is the FMPLL Controller.
    '''
    def __init__(self, emu, mmio_addr):
        # need to hook a MMIO mmiodev at 0xc3f80000 of size 0x4000
        super().__init__(emu, 'FMPLL', mmio_addr, 0x4000, regsetcls=FMPLL_REGISTERS)

        # Create attribute to hold configured external oscillator value
        self.extal = self._config.extal

        # Place to save ESYNCR1[CLKCFG] to restore later if that field is
        # updated when it shouldn't be
        self._saved_clkcfg = None

        # Output PLL value
        self.pll = None

        # Attach callbacks to the ESYNCR1 and ESYNCR2 registers
        self.registers.vsAddParseCallback('esyncr1', self.esyncr1Update)
        self.registers.vsAddParseCallback('esyncr2', self.esyncr2Update)

    def reset(self, emu):
        """
        Return the FMPLL peripheral to a reset state
        """
        # Reset the peripheral registers
        super().reset(emu)

        # Table 5-13. Clock Mode Selection (MPC5674FRM.pdf page 196)
        #
        #         PLLCFG     |       Clock Mode       |      CLKCFG
        #    [0] | [1] | [2] |                        | [2] | [1] | [0]
        #   -----+-----+-----+------------------------+-----+-----+-----
        #     0  |  0  |  X  | PLL Off Mode           |  0  |  X  |  X
        #     0  |  1  |  X  | Normal Mode w/ extal   |  1  |  1  |  0
        #     1  |  0  |  X  | Normal Mode w/ crystal |  1  |  1  |  1
        #     1  |  1  |  X  | Reserved               |  1  |  0  |  0
        #
        # NOTE: CLKCFG bit numbers seem reversed from normal PPC style (i.e.
        #       normal). NXP application node "MPC564xA/MPC563xMFMPLL
        #       Initialization" (AN11960.pdf) has examples that appear to
        #       confirm this:
        #
        #   FMPLL.ESYNCR1.B.CLKCFG = 0x01; /* Clock Mode :Bypass w/ Crystal Ref PLL Off */
        #   FMPLL.ESYNCR1.B.CLKCFG = 0x03; /* Clock Mode :Bypass w/ Crystal Ref and PLL On */
        #   FMPLL.ESYNCR1.B.CLKCFG = 0x07; /* Clock Mode :Normal w/ Crystal Ref PLL On */
        #
        # For now assume that the PLLCFG is set to Normal Mode w/ Crystal (0b10)
        # Based on that:
        #   - ESYNCR1[CLKCFG]  = 0b111
        #   - ESYNCR1[EPREDIV] = 0b0011
        #
        # PLLCFG[2] sets the range of the external crystal oscillator:
        #   EXTAL from 8 MHz to 20 MHZ, PLLCFG[2] = 0
        #   EXTAL @ 40 MHZ, PLLCFG[2] = 1

        # If extal == 40MHz then PLLCFG[2] should be 1, if it is from 8MHz to
        # 20MHz then PLLCFG[2] should be 0
        if ((self.emu.siu.pllcfg & 1) == 1 and self.extal != 40000000) or \
                ((self.emu.siu.pllcfg & 1) == 0 and \
                (self.extal < 8000000 or self.extal > 40000000)):
            logger.warning('INVALID PLLCFG (%s) for external clock %f MHz', bin(self.emu.siu.pllcfg), self.extal / 1000000)

        # Set the default ESYNCR1[CLKCFG] reset value
        if self.emu.siu.pllcfg & 0b110 == 0b000:
            self.registers.esyncr1.clkcfg = 0b000
        elif self.emu.siu.pllcfg & 0b110 == 0b010:
            self.registers.esyncr1.clkcfg = 0b110
        elif self.emu.siu.pllcfg & 0b110 == 0b100:
            self.registers.esyncr1.clkcfg = 0b111
        elif self.emu.siu.pllcfg & 0b110 == 0b110:
            self.registers.esyncr1.clkcfg = 0b100

        # Save the current ESYNCR1[CLKCFG] value
        self._saved_clkcfg = self.registers.esyncr1.clkcfg

        # The default ESYNCR1[EPREDIV] value is based on PLLCFG[2]:
        #   ESYNCR1[EPREDIV] = 0b0001 if PLLCFG[2] is 0
        #   ESYNCR1[EPREDIV] = 0b0011 if PLLCFG[2] is 1
        if self.emu.siu.pllcfg & 0b001 == 0b000:
            self.registers.esyncr1.eprediv = 0b0001
        else:
            self.registers.esyncr1.eprediv = 0b0011

        # Normally the configClock() method is called by the esyncr1Update(), or
        # esyncr2Update() write handlers, but since we set the reset values
        # directly, manually call the clockConfig() function now.
        self.configClock()

    def configClock(self):
        # TODO: changing EPREDIV or EMFD causes the PLL lock to be lost. Also
        # the reference manual indicates not to change these values in FM mode
        # but does not indicate why.
        # The recommended procedure is:
        #   1. disable FM
        #   2. reconfigure PLL settings
        #   3. wait until PLL locks with the new settings
        #   4. re-enable FM
        #
        # Additionally if ESYNCR2[LOLRE] is set when clock settings change it
        # should cause a reset.

        # TODO: In theory this is probably where we should generate LOL and LOC
        # interrupts if those interrupt sources are enabled? Maybe?

        # As noted above the CLKCFG bit numbering appears reversed from the
        # normal PPC documentation
        #   SYNSR[MODE] == ESYNCR1[CLKCFG2]
        #   SYNSR[PLLREF] == ESYNCR1[CLKCFG1]
        #   SYNSR[PLLSEL] == ESYNCR1[CLKCFG0]

        print('synsr  ', self.registers.synsr.vsEmit().hex())
        print('esyncr1', self.registers.esyncr1.vsEmit().hex())
        print('esyncr2', self.registers.esyncr2.vsEmit().hex())

        clkcfg = self.registers.esyncr1.clkcfg
        mode = (clkcfg >> 2) & 0b001
        self.registers.synsr.vsOverrideValue('mode',  mode)

        # PLLREF should only be set if the mode is 1
        pllref = (clkcfg >> 1) & mode
        self.registers.synsr.vsOverrideValue('pllref', pllref)

        # PLLSEL should only be set if the mode is 1
        pllsel = clkcfg & mode
        self.registers.synsr.vsOverrideValue('pllsel', pllsel)

        # The PLL lock flags should reflect if normal PLL mode is enabled or
        # not. If PLL normal mode is selected indicate that lock has been
        # achieved.
        self.registers.synsr.vsOverrideValue('locks', pllsel)
        self.registers.synsr.vsOverrideValue('lock', pllsel)

        print(clkcfg, mode, pllref, pllsel)

        # Table 5-10. Clock-Out vs. Clock-In Relationships
        # (MPC5674FRM.pdf page 196)
        #
        #   Clock Mode | Frequency Equation
        #   -----------+-------------------
        #   PLL Off    | f_pll = f_extal
        #   Normal PLL | f_pll = (f_extal*(EMFD+16)) / ((EPREDIV+1)*(ERFD+1))
        if self.registers.synsr.pllsel:
            freq = (self.extal * (self.registers.esyncr1.emfd+16)) / \
                ((self.registers.esyncr1.eprediv+1) * (self.registers.esyncr2.erfd+1))

            # freq is a float already because of the division in the above
            # calculation
            self.pll = freq
        else:
            # Ensure that the system PLL is a floating point value
            self.pll = float(self.extal)

        logger.debug('FMPLL: Setting PLL to %f MHz', self.pll / 1000000)

    def esyncr1Update(self, thing):
        print('esyncr1 written', self.registers.esyncr1.vsEmit().hex())
        print(self.registers.esyncr1.tree())
        # Only allow clkcfg to change if ESYNCR2[CLKCFG_DIS] is 0, if
        # ESYNCR2[CLKCFG_DIS] is 1 restore the previously saved ESYNCR1[CLKCFG]
        if self.registers.esyncr2.clkcfg_dis == 1:
            self.registers.esyncr1.clkcfg = self._saved_clkcfg
        else:
            # Save the current ESYNCR1[CLKCFG] in case we need to it later
            self._saved_clkcfg = self.registers.esyncr1.clkcfg

        # TODO: Trigger loss of clock interrupts if enabled and the clock values
        # are changed

        # Re-run the clock configuration
        self.configClock()

    def esyncr2Update(self, thing):
        print('esyncr2 written', self.registers.esyncr1.vsEmit().hex())
        # TODO: Trigger loss of clock interrupts if enabled and the clock values
        # are changed

        # Re-run the clock configuration
        self.configClock()

    def f_pll(self):
        """
        Utility function that allows other peripherals to get the FMPLL clock
        """
        return self.pll

    def f_extal(self):
        """
        Utility function that allows other peripherals to get external
        oscillator clock frequency
        """
        return float(self.extal)
