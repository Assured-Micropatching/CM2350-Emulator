import os
import random

import envi.bits as e_bits
from ..peripherals import flash as flashperiph

from .helpers import MPC5674_Test

import logging
logger = logging.getLogger(__name__)


FLASH_A_MCR_ADDR     = 0xC3F88000
FLASH_A_LMLR_ADDR    = 0xC3F88004
FLASH_A_HLR_ADDR     = 0xC3F88008
FLASH_A_SLMLR_ADDR   = 0xC3F8800C
FLASH_A_LMSR_ADDR    = 0xC3F88010
FLASH_A_HSR_ADDR     = 0xC3F88014
FLASH_A_AR_ADDR      = 0xC3F88018
FLASH_A_BIUCR_ADDR   = 0xC3F8801C
FLASH_A_BIUAPR_ADDR  = 0xC3F88020
FLASH_A_BIUCR2_ADDR  = 0xC3F88024
FLASH_A_UT0_ADDR     = 0xC3F8803C
FLASH_A_UT1_ADDR     = 0xC3F88040
FLASH_A_UT2_ADDR     = 0xC3F88040

FLASH_B_MCR_ADDR     = 0xC3F8C000
FLASH_B_LMLR_ADDR    = 0xC3F8C004
FLASH_B_HLR_ADDR     = 0xC3F8C008
FLASH_B_SLMLR_ADDR   = 0xC3F8C00C
FLASH_B_LMSR_ADDR    = 0xC3F8C010
FLASH_B_HSR_ADDR     = 0xC3F8C014
FLASH_B_AR_ADDR      = 0xC3F8C018
FLASH_B_UT0_ADDR     = 0xC3F8C03C
FLASH_B_UT1_ADDR     = 0xC3F8C040
FLASH_B_UT2_ADDR     = 0xC3F8C040

# Flash A/B specific values

FLASH_A_MCR_VALUE    = 0x05400600
FLASH_A_BIUCR_VALUE  = 0x0000FF00
FLASH_A_BIUAPR_VALUE = 0xFFFFFFFF
FLASH_A_BIUCR2_VALUE = 0xFFFFFFFF

FLASH_B_MCR_VALUE    = 0x05010600

# Config register values that are the same for flash A and B
FLASH_x_LMLR_VALUE   = 0x001303FF
FLASH_x_HLR_VALUE    = 0x000003FF
FLASH_x_SLMLR_VALUE  = 0x001303FF
FLASH_x_LMSR_VALUE   = 0x00000000
FLASH_x_HSR_VALUE    = 0x00000000
FLASH_x_AR_VALUE     = 0x00000000
FLASH_x_UT0_VALUE    = 0x00000081
FLASH_x_UT1_VALUE    = 0x00000000
FLASH_x_UT2_VALUE    = 0x00000000

# Flash addresses and sizes
FLASH_MAIN_ADDR      = 0x00000000
FLASH_MAIN_SIZE      = 0x00400000
FLASH_A_SHADOW_ADDR  = 0x00FFC000
FLASH_A_SHADOW_SIZE  = 0x00004000
FLASH_B_SHADOW_ADDR  = 0x00EFC000
FLASH_B_SHADOW_SIZE  = 0x00004000

# The default contents of shadow flash A are all erased (0xFF) bytes except for
# some default password stuff at:
#   - 0x3DD8: 8 byte serial passcode (0xFEEDFACECAFEBEEF)
#   - 0x3DE0: 2 bytes censorship control (0x55AA)
#   - 0x3DE2: 2 bytes serial boot control (0x55AA)

FLASH_DEFAULTS_OFFSET               = 0x3DD8
FLASH_DEFAULTS_ADDR                 = FLASH_A_SHADOW_ADDR + FLASH_DEFAULTS_OFFSET
FLASH_DEFAULTS                      = b'\xFE\xED\xFA\xCE\xCA\xFE\xBE\xEF\x55\xAA\x55\xAA'

# Some of the flash array configurations values are read from shadow flash on
# reset

FLASH_A_LMLR_DEFAULT_OFFSET         = 0x3DE8
FLASH_A_LMLR_DEFAULT_ADDR           = FLASH_A_SHADOW_ADDR + FLASH_A_LMLR_DEFAULT_OFFSET
FLASH_A_HLR_DEFAULT_OFFSET          = 0x3DF0
FLASH_A_HLR_DEFAULT_ADDR            = FLASH_A_SHADOW_ADDR + FLASH_A_HLR_DEFAULT_OFFSET
FLASH_A_SLMLR_DEFAULT_OFFSET        = 0x3DF8
FLASH_A_SLMLR_DEFAULT_ADDR          = FLASH_A_SHADOW_ADDR + FLASH_A_SLMLR_DEFAULT_OFFSET
FLASH_A_BIUCR2_DEFAULT_OFFSET       = 0x3E00
FLASH_A_BIUCR2_DEFAULT_ADDR         = FLASH_A_SHADOW_ADDR + FLASH_A_BIUCR2_DEFAULT_OFFSET

FLASH_B_LMLR_DEFAULT_OFFSET         = 0x1DE8
FLASH_B_LMLR_DEFAULT_ADDR           = FLASH_B_SHADOW_ADDR + FLASH_B_LMLR_DEFAULT_OFFSET
FLASH_B_HLR_DEFAULT_OFFSET          = 0x1DF0
FLASH_B_HLR_DEFAULT_ADDR            = FLASH_B_SHADOW_ADDR + FLASH_B_HLR_DEFAULT_OFFSET
FLASH_B_SLMLR_DEFAULT_OFFSET        = 0x1DF8
FLASH_B_SLMLR_DEFAULT_ADDR          = FLASH_B_SHADOW_ADDR + FLASH_B_SLMLR_DEFAULT_OFFSET

# Specific flash block addresses and sizes for reprogramming or erasing
# When programming or erasing an address within a block the entire block (any
# non-programmed/written addresses) will be set back to the default erased
# (0xFF) state.
FLASH_BLOCKS = (
    # (start, end, lmsr_mask, hsr_mask, (mcr_addr,))
    (0x00000000, 0x00004000, 0x00000001, 0x00000000, (FLASH_A_MCR_ADDR,)),                   # A.L0
    (0x00004000, 0x00008000, 0x00000002, 0x00000000, (FLASH_A_MCR_ADDR,)),                   # A.L1
    (0x00008000, 0x0000C000, 0x00000004, 0x00000000, (FLASH_A_MCR_ADDR,)),                   # A.L2
    (0x0000C000, 0x00010000, 0x00000008, 0x00000000, (FLASH_A_MCR_ADDR,)),                   # A.L3
    (0x00010000, 0x00014000, 0x00000010, 0x00000000, (FLASH_A_MCR_ADDR,)),                   # A.L4
    (0x00014000, 0x00018000, 0x00000020, 0x00000000, (FLASH_A_MCR_ADDR,)),                   # A.L5
    (0x00018000, 0x0001C000, 0x00000040, 0x00000000, (FLASH_A_MCR_ADDR,)),                   # A.L6
    (0x0001C000, 0x00020000, 0x00000080, 0x00000000, (FLASH_A_MCR_ADDR,)),                   # A.L7
    (0x00020000, 0x00030000, 0x00000100, 0x00000000, (FLASH_A_MCR_ADDR,)),                   # A.L8
    (0x00030000, 0x00040000, 0x00000200, 0x00000000, (FLASH_A_MCR_ADDR,)),                   # A.L9
    (0x00040000, 0x00060000, 0x00010000, 0x00000000, (FLASH_A_MCR_ADDR,)),                   # A.M0
    (0x00060000, 0x00080000, 0x00020000, 0x00000000, (FLASH_A_MCR_ADDR,)),                   # A.M1
    (0x00080000, 0x000C0000, 0x00000001, 0x00000000, (FLASH_B_MCR_ADDR,)),                   # B.L0
    (0x000C0000, 0x00100000, 0x00010000, 0x00000000, (FLASH_B_MCR_ADDR,)),                   # B.M0
    (0x00100000, 0x00180000, 0x00000000, 0x00000001, (FLASH_A_MCR_ADDR, FLASH_B_MCR_ADDR)),  # A.H0, B.H0
    (0x00180000, 0x00200000, 0x00000000, 0x00000002, (FLASH_A_MCR_ADDR, FLASH_B_MCR_ADDR)),  # A.H1, B.H1
    (0x00200000, 0x00280000, 0x00000000, 0x00000004, (FLASH_A_MCR_ADDR, FLASH_B_MCR_ADDR)),  # A.H2, B.H2
    (0x00280000, 0x00300000, 0x00000000, 0x00000008, (FLASH_A_MCR_ADDR, FLASH_B_MCR_ADDR)),  # A.H3, B.H3
    (0x00300000, 0x00380000, 0x00000000, 0x00000010, (FLASH_A_MCR_ADDR, FLASH_B_MCR_ADDR)),  # A.H4, B.H4
    (0x00380000, 0x00400000, 0x00000000, 0x00000020, (FLASH_A_MCR_ADDR, FLASH_B_MCR_ADDR)),  # A.H5, B.H5
)

# A list of flash addresses that are managed by flash array A
FLASH_A_ADDRS = (
    range(0x00000000, 0x00004000, 4),   # A.L0
    range(0x00004000, 0x00008000, 4),   # A.L1
    range(0x00008000, 0x0000C000, 4),   # A.L2
    range(0x0000C000, 0x00010000, 4),   # A.L3
    range(0x00010000, 0x00014000, 4),   # A.L4
    range(0x00014000, 0x00018000, 4),   # A.L5
    range(0x00018000, 0x0001C000, 4),   # A.L6
    range(0x0001C000, 0x00020000, 4),   # A.L7
    range(0x00020000, 0x00030000, 4),   # A.L8
    range(0x00030000, 0x00040000, 4),   # A.L9
    range(0x00040000, 0x00060000, 4),   # A.M0
    range(0x00060000, 0x00080000, 4),   # A.M1

    # The "high" blocks are interleaved A/B every 16 bytes
    range(0x00100000, 0x00280000, 32),  # A.H0, B.H0
    range(0x00100004, 0x00280000, 32),  # A.H0, B.H0
    range(0x00100008, 0x00280000, 32),  # A.H0, B.H0
    range(0x0010000C, 0x00280000, 32),  # A.H0, B.H0

    range(0x00180000, 0x002C0000, 32),  # A.H1, B.H1
    range(0x00180004, 0x002C0000, 32),  # A.H1, B.H1
    range(0x00180008, 0x002C0000, 32),  # A.H1, B.H1
    range(0x0018000C, 0x002C0000, 32),  # A.H1, B.H1

    range(0x002C0000, 0x00300000, 32),  # A.H2, B.H2
    range(0x002C0004, 0x00300000, 32),  # A.H2, B.H2
    range(0x002C0008, 0x00300000, 32),  # A.H2, B.H2
    range(0x002C000C, 0x00300000, 32),  # A.H2, B.H2

    range(0x00200000, 0x00380000, 32),  # A.H3, B.H3
    range(0x00200004, 0x00380000, 32),  # A.H3, B.H3
    range(0x00200008, 0x00380000, 32),  # A.H3, B.H3
    range(0x0020000C, 0x00380000, 32),  # A.H3, B.H3

    range(0x00380000, 0x003C0000, 32),  # A.H4, B.H4
    range(0x00380004, 0x003C0000, 32),  # A.H4, B.H4
    range(0x00380008, 0x003C0000, 32),  # A.H4, B.H4
    range(0x0038000C, 0x003C0000, 32),  # A.H4, B.H4

    range(0x003C0000, 0x00400000, 32),  # A.H5, B.H5
    range(0x003C0004, 0x00400000, 32),  # A.H5, B.H5
    range(0x003C0008, 0x00400000, 32),  # A.H5, B.H5
    range(0x003C000C, 0x00400000, 32),  # A.H5, B.H5
)

# A list of flash addresses that are managed by flash array B
FLASH_B_ADDRS = (
    range(0x00080000, 0x000C0000, 4),  # B.L0
    range(0x000C0000, 0x00100000, 4),  # B.M0

    range(0x00100010, 0x00280000, 32),  # A.H0, B.H0
    range(0x00100014, 0x00280000, 32),  # A.H0, B.H0
    range(0x00100018, 0x00280000, 32),  # A.H0, B.H0
    range(0x0010001C, 0x00280000, 32),  # A.H0, B.H0

    range(0x00180010, 0x002C0000, 32),  # A.H1, B.H1
    range(0x00180014, 0x002C0000, 32),  # A.H1, B.H1
    range(0x00180018, 0x002C0000, 32),  # A.H1, B.H1
    range(0x0018001C, 0x002C0000, 32),  # A.H1, B.H1

    range(0x002C0010, 0x00300000, 32),  # A.H2, B.H2
    range(0x002C0014, 0x00300000, 32),  # A.H2, B.H2
    range(0x002C0018, 0x00300000, 32),  # A.H2, B.H2
    range(0x002C001C, 0x00300000, 32),  # A.H2, B.H2

    range(0x00200010, 0x00380000, 32),  # A.H3, B.H3
    range(0x00200014, 0x00380000, 32),  # A.H3, B.H3
    range(0x00200018, 0x00380000, 32),  # A.H3, B.H3
    range(0x0020001C, 0x00380000, 32),  # A.H3, B.H3

    range(0x00380010, 0x003C0000, 32),  # A.H4, B.H4
    range(0x00380014, 0x003C0000, 32),  # A.H4, B.H4
    range(0x00380018, 0x003C0000, 32),  # A.H4, B.H4
    range(0x0038001C, 0x003C0000, 32),  # A.H4, B.H4

    range(0x003C0010, 0x00400000, 32),  # A.H5, B.H5
    range(0x003C0014, 0x00400000, 32),  # A.H5, B.H5
    range(0x003C0018, 0x00400000, 32),  # A.H5, B.H5
    range(0x003C001C, 0x00400000, 32),  # A.H5, B.H5
)

def find_interlock_addr(addr, mcr_addr):
    """
    Return an address managed by the same flash array that is _not_ in the
    block to be modified or erased
    """
    if mcr_addr == FLASH_A_MCR_ADDR:
        blocks = [r for r in FLASH_A_ADDRS if addr not in r]
    else:
        blocks = [r for r in FLASH_B_ADDRS if addr not in r]

    # Pick a block
    block = random.choice(blocks)

    # Now pick an address
    return random.choice(block)


class MPC5674_Flash_Test(MPC5674_Test):

    ############################################
    # Confirm default control register states
    ############################################

    def test_flash_mcr(self):
        self.assertEqual(self.emu.readMemValue(FLASH_A_MCR_ADDR, 4), FLASH_A_MCR_VALUE)
        self.assertEqual(self.emu.flash.A.mcr.size, 0b101)
        self.assertEqual(self.emu.flash.A.mcr.las, 0b100)
        self.assertEqual(self.emu.flash.A.mcr.mas, 0)
        self.assertEqual(self.emu.flash.A.mcr.eer, 0)
        self.assertEqual(self.emu.flash.A.mcr.rwe, 0)
        self.assertEqual(self.emu.flash.A.mcr.sbc, 0)
        self.assertEqual(self.emu.flash.A.mcr.peas, 0)
        self.assertEqual(self.emu.flash.A.mcr.done, 1)
        self.assertEqual(self.emu.flash.A.mcr.peg, 1)
        self.assertEqual(self.emu.flash.A.mcr.pgm, 0)
        self.assertEqual(self.emu.flash.A.mcr.psus, 0)
        self.assertEqual(self.emu.flash.A.mcr.ers, 0)
        self.assertEqual(self.emu.flash.A.mcr.esus, 0)
        self.assertEqual(self.emu.flash.A.mcr.ehv, 0)

        self.assertEqual(self.emu.readMemValue(FLASH_B_MCR_ADDR, 4), FLASH_B_MCR_VALUE)
        self.assertEqual(self.emu.flash.B.mcr.size, 0b101)
        self.assertEqual(self.emu.flash.B.mcr.las, 0b000)
        self.assertEqual(self.emu.flash.B.mcr.mas, 1)
        self.assertEqual(self.emu.flash.B.mcr.eer, 0)
        self.assertEqual(self.emu.flash.B.mcr.rwe, 0)
        self.assertEqual(self.emu.flash.B.mcr.sbc, 0)
        self.assertEqual(self.emu.flash.B.mcr.peas, 0)
        self.assertEqual(self.emu.flash.B.mcr.done, 1)
        self.assertEqual(self.emu.flash.B.mcr.peg, 1)
        self.assertEqual(self.emu.flash.B.mcr.pgm, 0)
        self.assertEqual(self.emu.flash.B.mcr.psus, 0)
        self.assertEqual(self.emu.flash.B.mcr.ers, 0)
        self.assertEqual(self.emu.flash.B.mcr.esus, 0)
        self.assertEqual(self.emu.flash.B.mcr.ehv, 0)

    def test_flash_lmlr(self):
        self.assertEqual(self.emu.readMemValue(FLASH_A_LMLR_ADDR, 4), FLASH_x_LMLR_VALUE)
        self.assertEqual(self.emu.flash.A.lmlr.lme, 0)
        self.assertEqual(self.emu.flash.A.lmlr.slock, 1)
        self.assertEqual(self.emu.flash.A.lmlr.mlock, 3)
        self.assertEqual(self.emu.flash.A.lmlr.llock, 0x3FF)

        self.assertEqual(self.emu.readMemValue(FLASH_B_LMLR_ADDR, 4), FLASH_x_LMLR_VALUE)
        self.assertEqual(self.emu.flash.B.lmlr.lme, 0)
        self.assertEqual(self.emu.flash.B.lmlr.slock, 1)
        self.assertEqual(self.emu.flash.B.lmlr.mlock, 3)
        self.assertEqual(self.emu.flash.B.lmlr.llock, 0x3FF)

    def test_flash_hlr(self):
        self.assertEqual(self.emu.readMemValue(FLASH_A_HLR_ADDR, 4), FLASH_x_HLR_VALUE)
        self.assertEqual(self.emu.flash.A.hlr.hbe, 0)
        self.assertEqual(self.emu.flash.A.hlr.hlock, 0x3FF)

        self.assertEqual(self.emu.readMemValue(FLASH_B_HLR_ADDR, 4), FLASH_x_HLR_VALUE)
        self.assertEqual(self.emu.flash.B.hlr.hbe, 0)
        self.assertEqual(self.emu.flash.B.hlr.hlock, 0x3FF)

    def test_flash_slmlr(self):
        self.assertEqual(self.emu.readMemValue(FLASH_A_SLMLR_ADDR, 4), FLASH_x_SLMLR_VALUE)
        self.assertEqual(self.emu.flash.A.slmlr.sle, 0)
        self.assertEqual(self.emu.flash.A.slmlr.sslock, 1)
        self.assertEqual(self.emu.flash.A.slmlr.smlock, 3)
        self.assertEqual(self.emu.flash.A.slmlr.sllock, 0x3FF)

        self.assertEqual(self.emu.readMemValue(FLASH_B_SLMLR_ADDR, 4), FLASH_x_SLMLR_VALUE)
        self.assertEqual(self.emu.flash.B.slmlr.sle, 0)
        self.assertEqual(self.emu.flash.B.slmlr.sslock, 1)
        self.assertEqual(self.emu.flash.B.slmlr.smlock, 3)
        self.assertEqual(self.emu.flash.B.slmlr.sllock, 0x3FF)

    def test_flash_lmsr(self):
        self.assertEqual(self.emu.readMemValue(FLASH_A_LMSR_ADDR, 4), FLASH_x_LMSR_VALUE)
        self.assertEqual(self.emu.flash.A.lmsr.msel, 0)
        self.assertEqual(self.emu.flash.A.lmsr.lsel, 0)

        self.assertEqual(self.emu.readMemValue(FLASH_B_LMSR_ADDR, 4), FLASH_x_LMSR_VALUE)
        self.assertEqual(self.emu.flash.B.lmsr.msel, 0)
        self.assertEqual(self.emu.flash.B.lmsr.lsel, 0)

    def test_flash_hsr(self):
        self.assertEqual(self.emu.readMemValue(FLASH_A_HSR_ADDR, 4), FLASH_x_HSR_VALUE)
        self.assertEqual(self.emu.flash.A.hsr.hsel, 0)

        self.assertEqual(self.emu.readMemValue(FLASH_B_HSR_ADDR, 4), FLASH_x_HSR_VALUE)
        self.assertEqual(self.emu.flash.B.hsr.hsel, 0)

    def test_flash_ar(self):
        self.assertEqual(self.emu.readMemValue(FLASH_A_AR_ADDR, 4), FLASH_x_AR_VALUE)
        self.assertEqual(self.emu.flash.A.ar.sad, 0)
        self.assertEqual(self.emu.flash.A.ar.addr, 0)

        self.assertEqual(self.emu.readMemValue(FLASH_B_AR_ADDR, 4), FLASH_x_AR_VALUE)
        self.assertEqual(self.emu.flash.B.ar.sad, 0)
        self.assertEqual(self.emu.flash.B.ar.addr, 0)

    def test_flash_biucr(self):
        self.assertEqual(self.emu.readMemValue(FLASH_A_BIUCR_ADDR, 4), FLASH_A_BIUCR_VALUE)
        self.assertEqual(self.emu.flash.A.biucr.m8pfe, 0)
        self.assertEqual(self.emu.flash.A.biucr.m6pfe, 0)
        self.assertEqual(self.emu.flash.A.biucr.m5pfe, 0)
        self.assertEqual(self.emu.flash.A.biucr.m4pfe, 0)
        self.assertEqual(self.emu.flash.A.biucr.m0pfe, 0)
        self.assertEqual(self.emu.flash.A.biucr.apc, 0b111)
        self.assertEqual(self.emu.flash.A.biucr.wwsc, 0b11)
        self.assertEqual(self.emu.flash.A.biucr.rwsc, 0b111)
        self.assertEqual(self.emu.flash.A.biucr.dpfen, 0)
        self.assertEqual(self.emu.flash.A.biucr.ifpfen, 0)
        self.assertEqual(self.emu.flash.A.biucr.pflim, 0)
        self.assertEqual(self.emu.flash.A.biucr.bfen, 0)

    def test_flash_biuapr(self):
        self.assertEqual(self.emu.readMemValue(FLASH_A_BIUAPR_ADDR, 4), FLASH_A_BIUAPR_VALUE)
        self.assertEqual(self.emu.flash.A.biuapr.m8ap, 0b11)
        self.assertEqual(self.emu.flash.A.biuapr.m6ap, 0b11)
        self.assertEqual(self.emu.flash.A.biuapr.m5ap, 0b11)
        self.assertEqual(self.emu.flash.A.biuapr.m4ap, 0b11)
        self.assertEqual(self.emu.flash.A.biuapr.m0ap, 0b11)

    def test_flash_biucr2(self):
        self.assertEqual(self.emu.readMemValue(FLASH_A_BIUCR2_ADDR, 4), FLASH_A_BIUCR2_VALUE)
        self.assertEqual(self.emu.flash.A.biucr2.lbcfg, 0b11)

    def test_flash_ut0(self):
        self.assertEqual(self.emu.readMemValue(FLASH_A_UT0_ADDR, 4), FLASH_x_UT0_VALUE)
        self.assertEqual(self.emu.flash.A.ut0.ute, 0)
        self.assertEqual(self.emu.flash.A.ut0.scbe, 0)
        self.assertEqual(self.emu.flash.A.ut0.dsi, 0)
        self.assertEqual(self.emu.flash.A.ut0.ea, 1)
        self.assertEqual(self.emu.flash.A.ut0.mre, 0)
        self.assertEqual(self.emu.flash.A.ut0.mrv, 0)
        self.assertEqual(self.emu.flash.A.ut0.eie, 0)
        self.assertEqual(self.emu.flash.A.ut0.ais, 0)
        self.assertEqual(self.emu.flash.A.ut0.aie, 0)
        self.assertEqual(self.emu.flash.A.ut0.aid, 1)

        self.assertEqual(self.emu.readMemValue(FLASH_B_UT0_ADDR, 4), FLASH_x_UT0_VALUE)
        self.assertEqual(self.emu.flash.B.ut0.ute, 0)
        self.assertEqual(self.emu.flash.B.ut0.scbe, 0)
        self.assertEqual(self.emu.flash.B.ut0.dsi, 0)
        self.assertEqual(self.emu.flash.B.ut0.ea, 1)
        self.assertEqual(self.emu.flash.B.ut0.mre, 0)
        self.assertEqual(self.emu.flash.B.ut0.mrv, 0)
        self.assertEqual(self.emu.flash.B.ut0.eie, 0)
        self.assertEqual(self.emu.flash.B.ut0.ais, 0)
        self.assertEqual(self.emu.flash.B.ut0.aie, 0)
        self.assertEqual(self.emu.flash.B.ut0.aid, 1)

    def test_flash_ut1(self):
        self.assertEqual(self.emu.readMemValue(FLASH_A_UT1_ADDR, 4), FLASH_x_UT1_VALUE)
        self.assertEqual(self.emu.flash.A.ut1.dai, 0)

        self.assertEqual(self.emu.readMemValue(FLASH_B_UT1_ADDR, 4), FLASH_x_UT1_VALUE)
        self.assertEqual(self.emu.flash.B.ut1.dai, 0)

    def test_flash_ut2(self):
        self.assertEqual(self.emu.readMemValue(FLASH_A_UT2_ADDR, 4), FLASH_x_UT2_VALUE)
        self.assertEqual(self.emu.flash.A.ut2.dai, 0)

        self.assertEqual(self.emu.readMemValue(FLASH_B_UT2_ADDR, 4), FLASH_x_UT2_VALUE)
        self.assertEqual(self.emu.flash.B.ut2.dai, 0)

    ############################################
    # Verify load default firmware contents
    ############################################

    def test_flash_default_firmware(self):
        # By default the firmware should be all FF's
        expected_data = bytearray(b'\xFF' * FLASH_MAIN_SIZE)
        self.assertEqual(self.emu.flash.data, expected_data)
        self.assertEqual(self.emu.readMemory(FLASH_MAIN_ADDR, FLASH_MAIN_SIZE), expected_data)

        # Verify that the Shadow flash B
        expected_data = bytearray(b'\xFF' * FLASH_B_SHADOW_SIZE)
        self.assertEqual(self.emu.flash.B.shadow, expected_data)
        self.assertEqual(self.emu.readMemory(FLASH_B_SHADOW_ADDR, FLASH_B_SHADOW_SIZE), expected_data)

        # Shadow flash A has the same size as B, but we need to add the special
        # default configuration values to the expected data
        start = FLASH_DEFAULTS_OFFSET
        end = start + len(FLASH_DEFAULTS)
        expected_data[start:end] = FLASH_DEFAULTS

        self.assertEqual(self.emu.flash.A.shadow, expected_data)
        self.assertEqual(self.emu.readMemory(FLASH_A_SHADOW_ADDR, FLASH_A_SHADOW_SIZE), expected_data)

    ############################################
    # Verify load main firmware blob
    ############################################

    def test_flash_load_firmware(self):
        # By default the firmware should be all FF's
        expected_data = bytearray(b'\xFF' * FLASH_MAIN_SIZE)
        self.assertEqual(self.emu.flash.data, expected_data)
        self.assertEqual(self.emu.readMemory(FLASH_MAIN_ADDR, FLASH_MAIN_SIZE), expected_data)

        # Generate some random data
        rand_data = bytearray(os.urandom(4096))

        # Load this data at offset 0x123456
        start = 0x123456
        end = start + len(rand_data)
        self.emu.flash.load(flashperiph.FlashDevice.FLASH_MAIN, rand_data, start)

        # Update the expected data
        expected_data[start:end] = rand_data

        self.assertEqual(self.emu.readMemory(FLASH_MAIN_ADDR + 0x123456, len(rand_data)), rand_data)
        self.assertEqual(self.emu.flash.data, expected_data)
        self.assertEqual(self.emu.readMemory(FLASH_MAIN_ADDR, FLASH_MAIN_SIZE), expected_data)

        # Verify that the Shadow flash contents A and B have not been modified
        expected_data = bytearray(b'\xFF' * FLASH_B_SHADOW_SIZE)
        self.assertEqual(self.emu.flash.B.shadow, expected_data)
        self.assertEqual(self.emu.readMemory(FLASH_B_SHADOW_ADDR, FLASH_B_SHADOW_SIZE), expected_data)

        # Shadow flash A has the same size as B, but we need to add the special
        # default configuration values to the expected data
        start = FLASH_DEFAULTS_OFFSET
        end = start + len(FLASH_DEFAULTS)
        expected_data[start:end] = FLASH_DEFAULTS

        self.assertEqual(self.emu.flash.A.shadow, expected_data)
        self.assertEqual(self.emu.readMemory(FLASH_A_SHADOW_ADDR, FLASH_A_SHADOW_SIZE), expected_data)

    ############################################
    # Verify load shadow flash A
    ############################################

    def test_flash_load_shadow_A(self):
        # By default the Shadow A flash should be all FF's except for the
        # default configuration values
        expected_data = bytearray(b'\xFF' * FLASH_A_SHADOW_SIZE)
        start = FLASH_DEFAULTS_OFFSET
        end = start + len(FLASH_DEFAULTS)
        expected_data[start:end] = FLASH_DEFAULTS

        self.assertEqual(self.emu.flash.A.shadow, expected_data)
        self.assertEqual(self.emu.readMemory(FLASH_A_SHADOW_ADDR, FLASH_A_SHADOW_SIZE), expected_data)

        # Explicitly verify the default values
        self.assertEqual(self.emu.readMemory(FLASH_DEFAULTS_ADDR, len(FLASH_DEFAULTS)), FLASH_DEFAULTS)

        # Generate some random data
        rand_data = bytearray(os.urandom(4096))

        # Load this data at an offset so that it stops 0x80 before the end of
        # the shadow flash
        start = FLASH_A_SHADOW_SIZE - len(rand_data) - 0x80
        end = start + len(rand_data)
        self.emu.flash.load(flashperiph.FlashDevice.FLASH_A_SHADOW, rand_data, start)

        # Update the expected data
        expected_data[start:end] = rand_data

        self.assertEqual(self.emu.readMemory(FLASH_A_SHADOW_ADDR + start, len(rand_data)), rand_data)
        self.assertEqual(self.emu.flash.A.shadow, expected_data)
        self.assertEqual(self.emu.readMemory(FLASH_A_SHADOW_ADDR, FLASH_A_SHADOW_SIZE), expected_data)

        # Explicitly verify the default values are no longer the defaults
        self.assertNotEqual(self.emu.readMemory(FLASH_DEFAULTS_ADDR, len(FLASH_DEFAULTS)), FLASH_DEFAULTS)

        # Verify that Shadow flash B has not been modified
        expected_data = bytearray(b'\xFF' * FLASH_B_SHADOW_SIZE)
        self.assertEqual(self.emu.flash.B.shadow, expected_data)
        self.assertEqual(self.emu.readMemory(FLASH_B_SHADOW_ADDR, FLASH_B_SHADOW_SIZE), expected_data)

        # Verify primary flash has not been modified
        expected_data = bytearray(b'\xFF' * FLASH_MAIN_SIZE)
        self.assertEqual(self.emu.flash.data, expected_data)
        self.assertEqual(self.emu.readMemory(FLASH_MAIN_ADDR, FLASH_MAIN_SIZE), expected_data)

    ############################################
    # Verify load shadow flash B
    ############################################

    def test_flash_load_shadow_B(self):
        # By default the Shadow B flash should be all FF's
        expected_data = bytearray(b'\xFF' * FLASH_B_SHADOW_SIZE)
        self.assertEqual(self.emu.flash.B.shadow, expected_data)
        self.assertEqual(self.emu.readMemory(FLASH_B_SHADOW_ADDR, FLASH_B_SHADOW_SIZE), expected_data)

        # Generate some random data
        rand_data = bytearray(os.urandom(4096))

        # Load this data at a random address
        start = random.randint(0, FLASH_B_SHADOW_SIZE - len(rand_data))
        end = start + len(rand_data)
        self.emu.flash.load(flashperiph.FlashDevice.FLASH_B_SHADOW, rand_data, start)

        # Update the expected data
        expected_data[start:end] = rand_data

        self.assertEqual(self.emu.readMemory(FLASH_B_SHADOW_ADDR + start, len(rand_data)), rand_data)
        self.assertEqual(self.emu.flash.B.shadow, expected_data)
        self.assertEqual(self.emu.readMemory(FLASH_B_SHADOW_ADDR, FLASH_B_SHADOW_SIZE), expected_data)

        # Verify that Shadow flash A has not been modified
        expected_data = bytearray(b'\xFF' * FLASH_A_SHADOW_SIZE)
        start = FLASH_DEFAULTS_OFFSET
        end = start + len(FLASH_DEFAULTS)
        expected_data[start:end] = FLASH_DEFAULTS

        self.assertEqual(self.emu.flash.A.shadow, expected_data)
        self.assertEqual(self.emu.readMemory(FLASH_A_SHADOW_ADDR, FLASH_A_SHADOW_SIZE), expected_data)

        # Verify primary flash has not been modified
        expected_data = bytearray(b'\xFF' * FLASH_MAIN_SIZE)
        self.assertEqual(self.emu.flash.data, expected_data)
        self.assertEqual(self.emu.readMemory(FLASH_MAIN_ADDR, FLASH_MAIN_SIZE), expected_data)

    ############################################
    # Confirm Flash controller A gets initial values from shadow flash
    ############################################

    def test_flash_shadow_default_values(self):
        # For each register to test we need the following values:
        #   (flashdev, default_offset, default_addr, reg_addr, reg_default)
        tests = (
            (self.emu.flash.A, FLASH_A_LMLR_DEFAULT_OFFSET,   FLASH_A_LMLR_DEFAULT_ADDR,   FLASH_A_LMLR_ADDR,   FLASH_x_LMLR_VALUE),
            (self.emu.flash.A, FLASH_A_HLR_DEFAULT_OFFSET,    FLASH_A_HLR_DEFAULT_ADDR,    FLASH_A_HLR_ADDR,    FLASH_x_HLR_VALUE),
            (self.emu.flash.A, FLASH_A_SLMLR_DEFAULT_OFFSET,  FLASH_A_SLMLR_DEFAULT_ADDR,  FLASH_A_SLMLR_ADDR,  FLASH_x_SLMLR_VALUE),
            (self.emu.flash.A, FLASH_A_BIUCR2_DEFAULT_OFFSET, FLASH_A_BIUCR2_DEFAULT_ADDR, FLASH_A_BIUCR2_ADDR, FLASH_A_BIUCR2_VALUE),
            (self.emu.flash.B, FLASH_B_LMLR_DEFAULT_OFFSET,   FLASH_B_LMLR_DEFAULT_ADDR,   FLASH_B_LMLR_ADDR,   FLASH_x_LMLR_VALUE),
            (self.emu.flash.B, FLASH_B_HLR_DEFAULT_OFFSET,    FLASH_B_HLR_DEFAULT_ADDR,    FLASH_B_HLR_ADDR,    FLASH_x_HLR_VALUE),
            (self.emu.flash.B, FLASH_B_SLMLR_DEFAULT_OFFSET,  FLASH_B_SLMLR_DEFAULT_ADDR,  FLASH_B_SLMLR_ADDR,  FLASH_x_SLMLR_VALUE),
        )

        # Generate some test values
        test_values = [os.urandom(4) for i in range(len(tests))]

        # Modify all the locations in shadow flash to test
        for i in range(len(tests)):
            flashdev, default_offset, default_addr, reg_addr, reg_default = tests[i]

            # Verify the expected default shadow flash value
            self.assertEqual(self.emu.readMemValue(default_addr, 4), 0xFFFFFFFF)

            # Verify that the register has the execpted default value
            self.assertEqual(self.emu.readMemValue(reg_addr, 4), reg_default)

            test_data = test_values[i]
            test_default = int.from_bytes(test_data, 'big')

            # Directly modify the shadow flash value
            flashdev.shadow[default_offset:default_offset+4] = test_data

            # Verify that value read from shadow flash has changed
            self.assertEqual(self.emu.readMemValue(default_addr, 4), test_default)

            # Verify that the config register value has not changed yet
            self.assertEqual(self.emu.readMemValue(reg_addr, 4), reg_default)

        self.emu.reset()

        # Now verify all the config registers changed
        for i in range(len(tests)):
            _, _, default_addr, reg_addr, reg_default = tests[i]
            test_data = test_values[i]
            test_default = int.from_bytes(test_data, 'big')

            # Verify shadow flash still has the test value
            self.assertEqual(self.emu.readMemValue(default_addr, 4), test_default)

            # Since the default value has cleared all non-modifiable values mask
            # the randomly generated test value against the default register
            # value to determine what value the config register should have
            # after reset.
            test_val = reg_default & test_default

            # Verify that the config register value has changed
            self.assertEqual(self.emu.readMemValue(reg_addr, 4), test_val)

    ############################################
    # Confirm erase block sequence works for main flash and shadow flash
    ############################################

    def test_flash_erase_shadow_A(self):
        # Enable writes to shadow block A
        self.emu.writeMemValue(FLASH_A_LMLR_ADDR, 0xA1A11111, 4)
        self.emu.writeMemValue(FLASH_A_SLMLR_ADDR, 0xC3C33333, 4)

        # Leave low and mid blocks locked, but unlock the shadow block
        self.emu.writeMemValue(FLASH_A_LMLR_ADDR, 0x000303FF, 4)
        self.emu.writeMemValue(FLASH_A_SLMLR_ADDR, 0x000303FF, 4)

        # Change Shadow A, B and main flash to be all 0x00's
        expected_shadow_data = bytearray(b'\x00' * FLASH_A_SHADOW_SIZE)
        self.emu.flash.A.shadow[:] = expected_shadow_data
        self.emu.flash.B.shadow[:] = expected_shadow_data

        expected_main_data = bytearray(b'\x00' * FLASH_MAIN_SIZE)
        self.emu.flash.data[:] = expected_main_data

        # The Set the MCR[ERS] bit
        val = self.emu.readMemValue(FLASH_A_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_A_MCR_ADDR, val|0x4, 4)

        # Shadow block does not have to be selected, it is selected
        # automatically during the interlock write

        # S0 start and end
        start = FLASH_A_SHADOW_ADDR
        end = FLASH_A_SHADOW_ADDR + FLASH_A_SHADOW_SIZE

        # Write any value to any address in shadow flash A
        interlock_addr = random.randint(start, end)
        interlock_val = random.randint(0x00000001, 0xFFFFFFFE)

        # Interlock write
        self.emu.writeMemValue(interlock_addr, interlock_val, 4)

        # Now set the MCR[EHV] bit to initiate the erase
        val = self.emu.readMemValue(FLASH_A_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_A_MCR_ADDR, val|0x1, 4)

        # Confirm shadow flash A is erased
        expected_data = bytearray(b'\xFF' * FLASH_A_SHADOW_SIZE)
        self.assertEqual(self.emu.flash.A.shadow, expected_data)
        self.assertEqual(self.emu.readMemory(FLASH_A_SHADOW_ADDR, FLASH_A_SHADOW_SIZE), expected_data)

        # Confirm shadow flash B and main flash have not been modified
        self.assertEqual(self.emu.flash.B.shadow, expected_shadow_data)
        self.assertEqual(self.emu.readMemory(FLASH_B_SHADOW_ADDR, FLASH_B_SHADOW_SIZE), expected_shadow_data)

        self.assertEqual(self.emu.flash.data, expected_main_data)
        self.assertEqual(self.emu.readMemory(FLASH_MAIN_ADDR, FLASH_MAIN_SIZE), expected_main_data)

    def test_flash_erase_shadow_B(self):
        # Enable writes to shadow block B
        self.emu.writeMemValue(FLASH_B_LMLR_ADDR, 0xA1A11111, 4)
        self.emu.writeMemValue(FLASH_B_SLMLR_ADDR, 0xC3C33333, 4)

        # Leave low and mid blocks locked, but unlock the shadow block
        self.emu.writeMemValue(FLASH_B_LMLR_ADDR, 0x000303FF, 4)
        self.emu.writeMemValue(FLASH_B_SLMLR_ADDR, 0x000303FF, 4)

        # Change Shadow A, B and main flash to be all 0x00's
        expected_shadow_data = bytearray(b'\x00' * FLASH_B_SHADOW_SIZE)
        self.emu.flash.A.shadow[:] = expected_shadow_data
        self.emu.flash.B.shadow[:] = expected_shadow_data

        expected_main_data = bytearray(b'\x00' * FLASH_MAIN_SIZE)
        self.emu.flash.data[:] = expected_main_data

        # The Set the MCR[ERS] bit
        val = self.emu.readMemValue(FLASH_B_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_B_MCR_ADDR, val|0x4, 4)

        # Shadow block does not have to be selected, it is selected
        # automatically during the interlock write

        # S0 start and end
        start = FLASH_B_SHADOW_ADDR
        end = FLASH_B_SHADOW_ADDR + FLASH_B_SHADOW_SIZE

        # Write any value to any address in shadow flash A
        interlock_addr = random.randint(start, end)
        interlock_val = random.randint(0x00000001, 0xFFFFFFFE)

        # Interlock write
        self.emu.writeMemValue(interlock_addr, interlock_val, 4)

        # Now set the MCR[EHV] bit to initiate the erase
        val = self.emu.readMemValue(FLASH_B_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_B_MCR_ADDR, val|0x1, 4)

        # Confirm shadow flash B is erased
        expected_data = bytearray(b'\xFF' * FLASH_B_SHADOW_SIZE)
        self.assertEqual(self.emu.flash.B.shadow, expected_data)
        self.assertEqual(self.emu.readMemory(FLASH_B_SHADOW_ADDR, FLASH_B_SHADOW_SIZE), expected_data)

        # Confirm shadow flash A and main flash have not been modified
        self.assertEqual(self.emu.flash.A.shadow, expected_shadow_data)
        self.assertEqual(self.emu.readMemory(FLASH_A_SHADOW_ADDR, FLASH_A_SHADOW_SIZE), expected_shadow_data)

        self.assertEqual(self.emu.flash.data, expected_main_data)
        self.assertEqual(self.emu.readMemory(FLASH_MAIN_ADDR, FLASH_MAIN_SIZE), expected_main_data)

    def test_flash_erase_H0_interleaved(self):
        # Unlock all high blocks
        self.emu.writeMemValue(FLASH_A_HLR_ADDR, 0xB2B22222, 4)
        self.emu.writeMemValue(FLASH_B_HLR_ADDR, 0xB2B22222, 4)
        self.emu.writeMemValue(FLASH_A_HLR_ADDR, 0x00000000, 4)
        self.emu.writeMemValue(FLASH_B_HLR_ADDR, 0x00000000, 4)

        # explicitly test that the high blocks are interleaved correctly by
        # erasing block H0 only in flash array A

        # Change primary flash to be all 0x00's
        expected_data = bytearray(b'\x00' * FLASH_MAIN_SIZE)
        self.emu.flash.data[:] = expected_data

        # The Set the MCR[ERS] bit
        val = self.emu.readMemValue(FLASH_A_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_A_MCR_ADDR, val|0x4, 4)

        # Select the H0 block
        val = self.emu.readMemValue(FLASH_A_HSR_ADDR, 4)
        self.emu.writeMemValue(FLASH_A_HSR_ADDR, val|0x1, 4)

        # H0 start and end
        start = 0x00100000
        end = 0x00180000

        # Write any value to any address managed by the same flash array as the
        # block that is intended to be erased and it will confirm the erase
        # operation (without this write nothing will be erased).
        interlock_addr = find_interlock_addr(start, FLASH_A_MCR_ADDR)
        interlock_val = random.randint(0x00000001, 0xFFFFFFFE)

        # Interlock write
        logger.debug('writing interlock [0x%08x] = 0x%08x', interlock_addr, interlock_val)
        self.emu.writeMemValue(interlock_addr, interlock_val, 4)

        # Now set the MCR[EHV] (bit 29) to initiate the erase
        val = self.emu.readMemValue(FLASH_A_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_A_MCR_ADDR, val|0x1, 4)

        # Now loop through the H0 address range and ensure that erased/unerased
        # sections are interleaved every 16 bytes.
        erased_chunk = bytearray(b'\xFF' * 16)
        unerased_chunk = bytearray(b'\x00' * 16)
        for addr in range(start, end, 32):
            # The first 16 bytes of each 32 byte chunk being compared should be
            # erased.
            self.assertEqual(self.emu.readMemory(addr, 16), erased_chunk, msg=hex(addr))
            self.assertEqual(self.emu.flash.data[addr:addr+16], erased_chunk, msg=hex(addr))

            # Second 16 bytes should not be erased since they belong to array B
            self.assertEqual(self.emu.readMemory(addr+16, 16), unerased_chunk, msg=hex(addr+16))
            self.assertEqual(self.emu.flash.data[addr+16:addr+32], unerased_chunk, msg=hex(addr+16))

    def test_flash_erase_locked(self):
        # Change Shadow A, B and main flash to be all 0x00's
        expected_shadow_data = bytearray(b'\x00' * FLASH_A_SHADOW_SIZE)
        self.emu.flash.A.shadow[:] = expected_shadow_data
        self.emu.flash.B.shadow[:] = expected_shadow_data

        expected_data = bytearray(b'\x00' * FLASH_MAIN_SIZE)
        self.emu.flash.data[:] = expected_data

        ###################################
        # Select all blocks in primary flash for erase
        ###################################

        val = self.emu.readMemValue(FLASH_A_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_A_MCR_ADDR, val|0x4, 4)

        val = self.emu.readMemValue(FLASH_B_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_B_MCR_ADDR, val|0x4, 4)

        # Can just set all bits to 1 to select all blocks
        self.emu.writeMemValue(FLASH_A_LMSR_ADDR, 0xFFFFFFFF, 4)
        self.emu.writeMemValue(FLASH_A_HSR_ADDR, 0xFFFFFFFF, 4)
        self.emu.writeMemValue(FLASH_B_LMSR_ADDR, 0xFFFFFFFF, 4)
        self.emu.writeMemValue(FLASH_B_HSR_ADDR, 0xFFFFFFFF, 4)

        # interlock writes to both the A and B arrays
        self.emu.writeMemValue(0x00000000, 0xAAAAAAAA, 4)  # A.L0
        self.emu.writeMemValue(0x00080000, 0xAAAAAAAA, 4)  # B.L0

        # Initiate the erase by writing MCR[EHV] bit 31
        val = self.emu.readMemValue(FLASH_A_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_A_MCR_ADDR, val|0x1, 4)

        val = self.emu.readMemValue(FLASH_B_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_B_MCR_ADDR, val|0x1, 4)

        # Confirm nothing was erased
        self.assertEqual(self.emu.flash.data, expected_data)
        self.assertEqual(self.emu.readMemory(FLASH_MAIN_ADDR, FLASH_MAIN_SIZE), expected_data)

        ###################################
        # Now try the same for shadow flash
        ###################################

        val = self.emu.readMemValue(FLASH_A_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_A_MCR_ADDR, val|0x4, 4)

        val = self.emu.readMemValue(FLASH_B_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_B_MCR_ADDR, val|0x4, 4)

        # interlock writes to A and B shadow flash (interlock writes also select
        # shadow blocks)
        self.emu.writeMemValue(FLASH_A_SHADOW_ADDR, 0xAAAAAAAA, 4)  # A.S0
        self.emu.writeMemValue(FLASH_B_SHADOW_ADDR, 0xAAAAAAAA, 4)  # B.S0

        # Initiate the erase by writing MCR[EHV] bit 31
        val = self.emu.readMemValue(FLASH_A_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_A_MCR_ADDR, val|0x1, 4)

        val = self.emu.readMemValue(FLASH_B_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_B_MCR_ADDR, val|0x1, 4)

        # Confirm nothing was erased
        self.assertEqual(self.emu.flash.A.shadow, expected_shadow_data)
        self.assertEqual(self.emu.readMemory(FLASH_A_SHADOW_ADDR, FLASH_A_SHADOW_SIZE), expected_shadow_data)
        self.assertEqual(self.emu.flash.B.shadow, expected_shadow_data)
        self.assertEqual(self.emu.readMemory(FLASH_B_SHADOW_ADDR, FLASH_B_SHADOW_SIZE), expected_shadow_data)

    def test_flash_erase_unlocked(self):
        # Change Shadow A, B and main flash to be all 0x00's
        self.emu.flash.A.shadow[:] = b'\x00' * FLASH_A_SHADOW_SIZE
        self.emu.flash.B.shadow[:] = b'\x00' * FLASH_A_SHADOW_SIZE
        self.emu.flash.data[:] = b'\x00' * FLASH_MAIN_SIZE

        # Confirm writes are disabled by default to the block lock registers
        self.assertEqual(self.emu.readMemValue(FLASH_A_LMLR_ADDR, 4) & 0x80000000, 0x00000000)
        self.assertEqual(self.emu.readMemValue(FLASH_A_HLR_ADDR, 4) & 0x80000000, 0x00000000)
        self.assertEqual(self.emu.readMemValue(FLASH_A_SLMLR_ADDR, 4) & 0x80000000, 0x00000000)

        self.assertEqual(self.emu.readMemValue(FLASH_B_LMLR_ADDR, 4) & 0x80000000, 0x00000000)
        self.assertEqual(self.emu.readMemValue(FLASH_B_HLR_ADDR, 4) & 0x80000000, 0x00000000)
        self.assertEqual(self.emu.readMemValue(FLASH_B_SLMLR_ADDR, 4) & 0x80000000, 0x00000000)

        # Enable writes to the block lock registers
        self.emu.writeMemValue(FLASH_A_LMLR_ADDR, 0xA1A11111, 4)
        self.emu.writeMemValue(FLASH_A_HLR_ADDR, 0xB2B22222, 4)
        self.emu.writeMemValue(FLASH_A_SLMLR_ADDR, 0xC3C33333, 4)

        self.emu.writeMemValue(FLASH_B_LMLR_ADDR, 0xA1A11111, 4)
        self.emu.writeMemValue(FLASH_B_HLR_ADDR, 0xB2B22222, 4)
        self.emu.writeMemValue(FLASH_B_SLMLR_ADDR, 0xC3C33333, 4)

        # Ensure that writes are now enabled
        self.assertEqual(self.emu.readMemValue(FLASH_A_LMLR_ADDR, 4) & 0x80000000, 0x80000000)
        self.assertEqual(self.emu.readMemValue(FLASH_A_HLR_ADDR, 4) & 0x80000000, 0x80000000)
        self.assertEqual(self.emu.readMemValue(FLASH_A_SLMLR_ADDR, 4) & 0x80000000, 0x80000000)

        self.assertEqual(self.emu.readMemValue(FLASH_B_LMLR_ADDR, 4) & 0x80000000, 0x80000000)
        self.assertEqual(self.emu.readMemValue(FLASH_B_HLR_ADDR, 4) & 0x80000000, 0x80000000)
        self.assertEqual(self.emu.readMemValue(FLASH_B_SLMLR_ADDR, 4) & 0x80000000, 0x80000000)

        # Unlock all blocks
        self.emu.writeMemValue(FLASH_A_LMLR_ADDR, 0x00000000, 4)
        self.emu.writeMemValue(FLASH_A_HLR_ADDR, 0x00000000, 4)
        self.emu.writeMemValue(FLASH_A_SLMLR_ADDR, 0x00000000, 4)

        self.emu.writeMemValue(FLASH_B_LMLR_ADDR, 0x00000000, 4)
        self.emu.writeMemValue(FLASH_B_HLR_ADDR, 0x00000000, 4)
        self.emu.writeMemValue(FLASH_B_SLMLR_ADDR, 0x00000000, 4)

        # Ensure all blocks are now unlocked
        self.assertEqual(self.emu.readMemValue(FLASH_A_LMLR_ADDR, 4), 0x80000000)
        self.assertEqual(self.emu.readMemValue(FLASH_A_HLR_ADDR, 4), 0x80000000)
        self.assertEqual(self.emu.readMemValue(FLASH_A_SLMLR_ADDR, 4), 0x80000000)

        self.assertEqual(self.emu.readMemValue(FLASH_B_LMLR_ADDR, 4), 0x80000000)
        self.assertEqual(self.emu.readMemValue(FLASH_B_HLR_ADDR, 4), 0x80000000)
        self.assertEqual(self.emu.readMemValue(FLASH_B_SLMLR_ADDR, 4), 0x80000000)

        ###################################
        # Select all blocks in primary flash for erase
        ###################################

        val = self.emu.readMemValue(FLASH_A_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_A_MCR_ADDR, val|0x4, 4)

        val = self.emu.readMemValue(FLASH_B_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_B_MCR_ADDR, val|0x4, 4)

        # Can just set all bits to 1 to select all blocks
        self.emu.writeMemValue(FLASH_A_LMSR_ADDR, 0xFFFFFFFF, 4)
        self.emu.writeMemValue(FLASH_A_HSR_ADDR, 0xFFFFFFFF, 4)
        self.emu.writeMemValue(FLASH_B_LMSR_ADDR, 0xFFFFFFFF, 4)
        self.emu.writeMemValue(FLASH_B_HSR_ADDR, 0xFFFFFFFF, 4)

        # interlock writes to both the A and B arrays
        self.emu.writeMemValue(0x00000000, 0xAAAAAAAA, 4)  # A.L0
        self.emu.writeMemValue(0x00080000, 0xAAAAAAAA, 4)  # B.L0

        # Initiate the erase by writing MCR[EHV] bit 31
        val = self.emu.readMemValue(FLASH_A_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_A_MCR_ADDR, val|0x1, 4)

        val = self.emu.readMemValue(FLASH_B_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_B_MCR_ADDR, val|0x1, 4)

        # Confirm main flash was erased
        expected_data = bytearray(b'\xFF' * FLASH_MAIN_SIZE)
        self.assertEqual(self.emu.flash.data, expected_data)
        self.assertEqual(self.emu.readMemory(FLASH_MAIN_ADDR, FLASH_MAIN_SIZE), expected_data)

        ###################################
        # Now try the same for shadow flash
        ###################################

        val = self.emu.readMemValue(FLASH_A_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_A_MCR_ADDR, val|0x4, 4)

        val = self.emu.readMemValue(FLASH_B_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_B_MCR_ADDR, val|0x4, 4)

        # interlock writes to A and B shadow flash (interlock writes also select
        # shadow blocks)
        self.emu.writeMemValue(FLASH_A_SHADOW_ADDR, 0xAAAAAAAA, 4)  # A.S0
        self.emu.writeMemValue(FLASH_B_SHADOW_ADDR, 0xAAAAAAAA, 4)  # B.S0

        # Initiate the erase by writing MCR[EHV] bit 31
        val = self.emu.readMemValue(FLASH_A_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_A_MCR_ADDR, val|0x1, 4)

        val = self.emu.readMemValue(FLASH_B_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_B_MCR_ADDR, val|0x1, 4)

        # Confirm both shadow flashes have been erased
        expected_shadow_data = bytearray(b'\xFF' * FLASH_A_SHADOW_SIZE)
        self.assertEqual(self.emu.flash.A.shadow, expected_shadow_data)
        self.assertEqual(self.emu.readMemory(FLASH_A_SHADOW_ADDR, FLASH_A_SHADOW_SIZE), expected_shadow_data)
        self.assertEqual(self.emu.flash.B.shadow, expected_shadow_data)
        self.assertEqual(self.emu.readMemory(FLASH_B_SHADOW_ADDR, FLASH_B_SHADOW_SIZE), expected_shadow_data)

        # Confirm that writes to the block lock registers are still enabled
        self.assertEqual(self.emu.readMemValue(FLASH_A_LMLR_ADDR, 4) & 0x80000000, 0x80000000)
        self.assertEqual(self.emu.readMemValue(FLASH_A_HLR_ADDR, 4) & 0x80000000, 0x80000000)
        self.assertEqual(self.emu.readMemValue(FLASH_A_SLMLR_ADDR, 4) & 0x80000000, 0x80000000)

        # Reset and ensure that the writes to the lock registers are disabled
        self.emu.reset()

        self.assertEqual(self.emu.readMemValue(FLASH_A_LMLR_ADDR, 4) & 0x80000000, 0x00000000)
        self.assertEqual(self.emu.readMemValue(FLASH_A_HLR_ADDR, 4) & 0x80000000, 0x00000000)
        self.assertEqual(self.emu.readMemValue(FLASH_A_SLMLR_ADDR, 4) & 0x80000000, 0x00000000)

    def test_flash_erase_main(self):
        # Unlock all blocks
        self.emu.writeMemValue(FLASH_A_LMLR_ADDR, 0xA1A11111, 4)
        self.emu.writeMemValue(FLASH_A_HLR_ADDR, 0xB2B22222, 4)
        self.emu.writeMemValue(FLASH_A_SLMLR_ADDR, 0xC3C33333, 4)

        self.emu.writeMemValue(FLASH_A_LMLR_ADDR, 0x00000000, 4)
        self.emu.writeMemValue(FLASH_A_HLR_ADDR, 0x00000000, 4)
        self.emu.writeMemValue(FLASH_A_SLMLR_ADDR, 0x00000000, 4)

        self.emu.writeMemValue(FLASH_B_LMLR_ADDR, 0xA1A11111, 4)
        self.emu.writeMemValue(FLASH_B_HLR_ADDR, 0xB2B22222, 4)
        self.emu.writeMemValue(FLASH_B_SLMLR_ADDR, 0xC3C33333, 4)

        self.emu.writeMemValue(FLASH_B_LMLR_ADDR, 0x00000000, 4)
        self.emu.writeMemValue(FLASH_B_HLR_ADDR, 0x00000000, 4)
        self.emu.writeMemValue(FLASH_B_SLMLR_ADDR, 0x00000000, 4)

        # Change Shadow A, B and main flash to be all 0x00's
        expected_shadow_data = bytearray(b'\x00' * FLASH_A_SHADOW_SIZE)
        self.emu.flash.A.shadow[:] = expected_shadow_data
        self.emu.flash.B.shadow[:] = expected_shadow_data

        expected_data = bytearray(b'\x00' * FLASH_MAIN_SIZE)
        self.emu.flash.data[:] = expected_data

        for start, end, lmsr_mask, hsr_mask, mcr_addrs in FLASH_BLOCKS:
            # The Set the MCR[ERS] bit(s)
            for addr in mcr_addrs:
                # MCR[ERS] is bit 29
                val = self.emu.readMemValue(addr, 4)
                self.emu.writeMemValue(addr, val|0x4, 4)

            # Verify:
            #   - MCR[PEAS] (bit 20) bit(s) are 0
            #   - MCR[DONE] (bit 21) bit(s) are 1 (EHV has not transitioned)
            #   - MCR[PEG]  (bit 22) bit(s) are 1 (DONE has not transitioned)
            for addr in mcr_addrs:
                self.assertEqual(self.emu.readMemValue(addr, 4) & 0x00000E00, 0x00000600)

            # Select the desired block with the LMSR/HSR registers
            for addr in mcr_addrs:
                if lmsr_mask:
                    if addr == FLASH_A_MCR_ADDR:
                        addr = FLASH_A_LMSR_ADDR
                    else:
                        addr = FLASH_B_LMSR_ADDR

                    self.emu.writeMemValue(addr, lmsr_mask, 4)

                    # Verify the value was written (i.e. that we didn't write an
                    # invalid mask value)
                    self.assertEqual(self.emu.readMemValue(addr, 4), lmsr_mask)

                if hsr_mask:
                    if addr == FLASH_A_MCR_ADDR:
                        addr = FLASH_A_HSR_ADDR
                    else:
                        addr = FLASH_B_HSR_ADDR

                    self.emu.writeMemValue(addr, hsr_mask, 4)

                    # Verify the value was written (i.e. that we didn't write an
                    # invalid mask value)
                    self.assertEqual(self.emu.readMemValue(addr, 4), hsr_mask)

            # The end values are exclusive so use randrange
            rand_addr = random.randrange(start, end)

            # Write any value to any address managed by the same flash array as
            # the block that is intended to be erased and it will confirm the
            # erase operation (without this write nothing will be erased).
            for addr in mcr_addrs:
                interlock_addr = find_interlock_addr(rand_addr, addr)
                cur_val = self.emu.readMemValue(interlock_addr, 4)

                # The value written doesn't matter, but specify values between
                # 0x00000001 and 0xFFFFFFFE to ensure that it won't match the
                # initial or erased states.
                interlock_val = random.randint(0x00000001, 0xFFFFFFFE)
                logger.debug('writing interlock [0x%08x] = 0x%08x', interlock_addr, interlock_val)
                self.emu.writeMemValue(interlock_addr, interlock_val, 4)

                # Ensure that the value at the interlock address was not changed
                self.assertEqual(self.emu.readMemValue(interlock_addr, 4), cur_val)

            # Now set the MCR[EHV] bit(s) to initiate the erase
            for addr in mcr_addrs:
                # MCR[EHV] is bit 31
                val = self.emu.readMemValue(addr, 4)
                self.emu.writeMemValue(addr, val|0x1, 4)

            # Change the erased block in the expected data
            expected_data[start:end] = b'\xFF' * (end - start)

            # Verify the expected block has been erased
            logger.debug('Checking if block 0x%08x-0x%08x was erased', start, end)

            # First check only the block we care about (easier validation if
            # this fails)
            self.assertEqual(self.emu.flash.data[start:end], expected_data[start:end])

            # Confirm the entire state of flash looks like expected
            self.assertEqual(self.emu.flash.data, expected_data)
            self.assertEqual(self.emu.readMemory(FLASH_MAIN_ADDR, FLASH_MAIN_SIZE), expected_data)

        # All of flash should now be erased
        expected_data = bytearray(b'\xFF' * FLASH_MAIN_SIZE)
        self.assertEqual(self.emu.flash.data, expected_data)
        self.assertEqual(self.emu.readMemory(FLASH_MAIN_ADDR, FLASH_MAIN_SIZE), expected_data)

        # Shadow flash A and B should not be erased
        self.assertEqual(self.emu.flash.A.shadow, expected_shadow_data)
        self.assertEqual(self.emu.flash.B.shadow, expected_shadow_data)
        self.assertEqual(self.emu.readMemory(FLASH_A_SHADOW_ADDR, FLASH_A_SHADOW_SIZE), expected_shadow_data)
        self.assertEqual(self.emu.readMemory(FLASH_B_SHADOW_ADDR, FLASH_B_SHADOW_SIZE), expected_shadow_data)

    ############################################
    # Confirm program block sequence works for main flash and shadow flash
    ############################################

    def test_flash_program_main(self):
        # Unlock all blocks (but not shadow blocks)
        self.emu.writeMemValue(FLASH_A_LMLR_ADDR, 0xA1A11111, 4)
        self.emu.writeMemValue(FLASH_A_HLR_ADDR, 0xB2B22222, 4)
        self.emu.writeMemValue(FLASH_A_SLMLR_ADDR, 0xC3C33333, 4)

        self.emu.writeMemValue(FLASH_A_LMLR_ADDR, 0x00100000, 4)
        self.emu.writeMemValue(FLASH_A_HLR_ADDR, 0x00000000, 4)
        self.emu.writeMemValue(FLASH_A_SLMLR_ADDR, 0x00100000, 4)

        self.emu.writeMemValue(FLASH_B_LMLR_ADDR, 0xA1A11111, 4)
        self.emu.writeMemValue(FLASH_B_HLR_ADDR, 0xB2B22222, 4)
        self.emu.writeMemValue(FLASH_B_SLMLR_ADDR, 0xC3C33333, 4)

        self.emu.writeMemValue(FLASH_B_LMLR_ADDR, 0x00100000, 4)
        self.emu.writeMemValue(FLASH_B_HLR_ADDR, 0x00000000, 4)
        self.emu.writeMemValue(FLASH_B_SLMLR_ADDR, 0x00100000, 4)

        # Ensure Shadow A, B and main flash all start out "erased" (0xFF's)
        expected_shadow_data = bytearray(b'\xFF' * FLASH_A_SHADOW_SIZE)
        self.emu.flash.A.shadow[:] = expected_shadow_data
        self.emu.flash.B.shadow[:] = expected_shadow_data

        expected_data = bytearray(b'\xFF' * FLASH_MAIN_SIZE)
        self.emu.flash.data[:] = expected_data

        for start, end, _, _, mcr_addrs in FLASH_BLOCKS:
            # The Set the MCR[PGM] bit(s)
            for addr in mcr_addrs:
                # MCR[PGM] is bit 27
                val = self.emu.readMemValue(addr, 4)
                self.emu.writeMemValue(addr, val|0x10, 4)

            # Verify:
            #   - MCR[PEAS] (bit 20) bit(s) are 0
            #   - MCR[DONE] (bit 21) bit(s) are 1 (EHV has not transitioned)
            #   - MCR[PEG]  (bit 22) bit(s) are 1 (DONE has not transitioned)
            for addr in mcr_addrs:
                self.assertEqual(self.emu.readMemValue(addr, 4) & 0x00000E00, 0x00000600)

            # Generate some random data to write
            rand_data = os.urandom(end-start)

            # Write the data in 4-byte chunks to emulate how code would normally
            # be writing data
            for offset in range(0, len(rand_data), 4):
                chunk = rand_data[offset:offset+4]
                self.emu.writeMemory(start + offset, chunk)

            # Now set the MCR[EHV] bit(s) to initiate the programming
            for addr in mcr_addrs:
                # MCR[EHV] is bit 31
                val = self.emu.readMemValue(addr, 4)
                self.emu.writeMemValue(addr, val|0x1, 4)

            # Change the erased block in the expected data
            expected_data[start:end] = rand_data

            # Verify the expected block has been erased
            logger.debug('Checking if block 0x%08x-0x%08x was programmed', start, end)

            # First check only the block we care about (easier validation if
            # this fails)
            self.assertEqual(self.emu.flash.data[start:end], expected_data[start:end])

            # Confirm the entire state of flash looks as expected
            self.assertEqual(self.emu.flash.data, expected_data)
            self.assertEqual(self.emu.readMemory(FLASH_MAIN_ADDR, FLASH_MAIN_SIZE), expected_data)

        # This was just tested, but final check that flash was completely
        # programmed
        self.assertEqual(self.emu.flash.data, expected_data)
        self.assertEqual(self.emu.readMemory(FLASH_MAIN_ADDR, FLASH_MAIN_SIZE), expected_data)

        # Shadow flash A and B should not be erased
        self.assertEqual(self.emu.flash.A.shadow, expected_shadow_data)
        self.assertEqual(self.emu.flash.B.shadow, expected_shadow_data)
        self.assertEqual(self.emu.readMemory(FLASH_A_SHADOW_ADDR, FLASH_A_SHADOW_SIZE), expected_shadow_data)
        self.assertEqual(self.emu.readMemory(FLASH_B_SHADOW_ADDR, FLASH_B_SHADOW_SIZE), expected_shadow_data)

    def test_flash_program_shadow_A(self):
        # Unlock the A shadow block
        self.emu.writeMemValue(FLASH_A_LMLR_ADDR, 0xA1A11111, 4)
        self.emu.writeMemValue(FLASH_A_SLMLR_ADDR, 0xC3C33333, 4)

        self.emu.writeMemValue(FLASH_A_LMLR_ADDR, 0x000303FF, 4)
        self.emu.writeMemValue(FLASH_A_SLMLR_ADDR, 0x000303FF, 4)

        # Ensure Shadow A, B and main flash all start out "erased" (0xFF's)
        erased_shadow_data = bytearray(b'\xFF' * FLASH_A_SHADOW_SIZE)
        self.emu.flash.A.shadow[:] = erased_shadow_data
        self.emu.flash.B.shadow[:] = erased_shadow_data

        erased_main_data = bytearray(b'\xFF' * FLASH_MAIN_SIZE)
        self.emu.flash.data[:] = erased_main_data

        # The Set the MCR[PGM] bit
        val = self.emu.readMemValue(FLASH_A_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_A_MCR_ADDR, val|0x10, 4)

        # S0 start and end
        start = FLASH_A_SHADOW_ADDR
        end = FLASH_A_SHADOW_ADDR + FLASH_A_SHADOW_SIZE

        # Generate some random data to write
        rand_data = bytearray(os.urandom(end-start))

        # Write the data in 4-byte chunks to emulate how code would normally be
        # writing data
        for offset in range(0, len(rand_data), 4):
            chunk = rand_data[offset:offset+4]
            self.emu.writeMemory(start + offset, chunk)

        # Now set the MCR[EHV] bit to initiate the erase
        val = self.emu.readMemValue(FLASH_A_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_A_MCR_ADDR, val|0x1, 4)

        # Confirm shadow flash A is programmed
        self.assertEqual(self.emu.flash.A.shadow, rand_data)
        self.assertEqual(self.emu.readMemory(FLASH_A_SHADOW_ADDR, FLASH_A_SHADOW_SIZE), rand_data)

        # Primary flash should still be erased
        self.assertEqual(self.emu.flash.data, erased_main_data)
        self.assertEqual(self.emu.readMemory(FLASH_MAIN_ADDR, FLASH_MAIN_SIZE), erased_main_data)

        # Shadow flash B should still be erased
        self.assertEqual(self.emu.flash.B.shadow, erased_shadow_data)
        self.assertEqual(self.emu.readMemory(FLASH_B_SHADOW_ADDR, FLASH_B_SHADOW_SIZE), erased_shadow_data)

    def test_flash_program_shadow_B(self):
        # Unlock the B shadow block
        self.emu.writeMemValue(FLASH_B_LMLR_ADDR, 0xA1A11111, 4)
        self.emu.writeMemValue(FLASH_B_SLMLR_ADDR, 0xC3C33333, 4)

        self.emu.writeMemValue(FLASH_B_LMLR_ADDR, 0x000303FF, 4)
        self.emu.writeMemValue(FLASH_B_SLMLR_ADDR, 0x000303FF, 4)

        # Ensure Shadow A, B and main flash all start out "erased" (0xFF's)
        erased_shadow_data = bytearray(b'\xFF' * FLASH_B_SHADOW_SIZE)
        self.emu.flash.A.shadow[:] = erased_shadow_data
        self.emu.flash.B.shadow[:] = erased_shadow_data

        erased_main_data = bytearray(b'\xFF' * FLASH_MAIN_SIZE)
        self.emu.flash.data[:] = erased_main_data

        # The Set the MCR[PGM] bit
        val = self.emu.readMemValue(FLASH_B_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_B_MCR_ADDR, val|0x10, 4)

        # S0 start and end
        start = FLASH_B_SHADOW_ADDR
        end = FLASH_B_SHADOW_ADDR + FLASH_B_SHADOW_SIZE

        # Generate some random data to write
        rand_data = bytearray(os.urandom(end-start))

        # Write the data in 4-byte chunks to emulate how code would normally be
        # writing data
        for offset in range(0, len(rand_data), 4):
            chunk = rand_data[offset:offset+4]
            self.emu.writeMemory(start + offset, chunk)

        # Now set the MCR[EHV] bit to initiate the erase
        val = self.emu.readMemValue(FLASH_B_MCR_ADDR, 4)
        self.emu.writeMemValue(FLASH_B_MCR_ADDR, val|0x1, 4)

        # Confirm shadow flash B is programmed
        self.assertEqual(self.emu.flash.B.shadow, rand_data)
        self.assertEqual(self.emu.readMemory(FLASH_B_SHADOW_ADDR, FLASH_B_SHADOW_SIZE), rand_data)

        # Primary flash should still be erased
        self.assertEqual(self.emu.flash.data, erased_main_data)
        self.assertEqual(self.emu.readMemory(FLASH_MAIN_ADDR, FLASH_MAIN_SIZE), erased_main_data)

        # Shadow flash A should still be erased
        self.assertEqual(self.emu.flash.A.shadow, erased_shadow_data)
        self.assertEqual(self.emu.readMemory(FLASH_A_SHADOW_ADDR, FLASH_A_SHADOW_SIZE), erased_shadow_data)

    ############################################
    # Verify function that can be used to retrieve parameters from flash from
    # other peripherals
    ############################################

    def test_flash_read_shadow_param(self):
        default_params = {
            flashperiph.FlashShadowParam.SERIAL_PASSCODE:           (0,  8, 0xFEEDFACECAFEBEEF),
            flashperiph.FlashShadowParam.SERIAL_PASSCODE_UPPER:     (0,  4, 0xFEEDFACE),
            flashperiph.FlashShadowParam.SERIAL_PASSCODE_LOWER:     (4,  4, 0xCAFEBEEF),
            flashperiph.FlashShadowParam.CENSORSHIP_CONTROL:        (8,  2, 0x55AA),
            flashperiph.FlashShadowParam.SERIAL_BOOT_CONTROL:       (10, 2, 0x55AA),
            flashperiph.FlashShadowParam.CENSORSHIP_CONTROL_WORD:   (8,  4, 0x55AA55AA),
        }

        # Default shadow parameters
        for param, (offset, size, value) in default_params.items():
            logger.debug('checking %s default (0x%08x to 0x%08x)', param.name, FLASH_DEFAULTS_ADDR, FLASH_DEFAULTS_ADDR+size)

            # Some test data sanity checking
            value_bytes = FLASH_DEFAULTS[offset:offset+size]
            self.assertEqual(e_bits.parsebytes(value_bytes, 0, size, bigend=True), value)

            # Test the internal peripheral API
            self.assertEqual(self.emu.flash.readShadowValue(param), value)

            # Read the data directly from flash
            start = FLASH_DEFAULTS_ADDR + offset
            end = start + size
            self.assertEqual(self.emu.readMemValue(start, size), value)
            self.assertEqual(self.emu.readMemory(start, size), bytearray(value_bytes))

            start = FLASH_DEFAULTS_OFFSET + offset
            end = start + size
            self.assertEqual(self.emu.flash.A.shadow[start:end], bytearray(value_bytes))

        # Randomize shadow flash A
        rand_data = os.urandom(FLASH_A_SHADOW_SIZE)
        self.emu.flash.A.shadow[:] = rand_data

        # Check that the data we read is logical
        for param, (offset, size, default_value) in default_params.items():
            logger.debug('checking %s (0x%08x to 0x%08x)', param.name, FLASH_DEFAULTS_ADDR, FLASH_DEFAULTS_ADDR+size)

            # Get the values we should expect
            rand_offset = FLASH_DEFAULTS_OFFSET + offset
            value_bytes = rand_data[rand_offset:rand_offset+size]
            value = e_bits.parsebytes(value_bytes, 0, size, bigend=True)
            self.assertNotEqual(value, default_value)

            # Test the internal peripheral API
            self.assertEqual(self.emu.flash.readShadowValue(param), value)

            # Read the data directly from flash (a bit redundant, but a good
            # sanity check)
            start =  FLASH_DEFAULTS_ADDR + offset
            end = start + size
            self.assertEqual(self.emu.readMemValue(start, size), value)
            self.assertEqual(self.emu.readMemory(start, size), bytearray(value_bytes))

            start = FLASH_DEFAULTS_OFFSET + offset
            end = start + size
            self.assertEqual(self.emu.flash.A.shadow[start:end], bytearray(value_bytes))

