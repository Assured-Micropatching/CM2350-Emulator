import random
import unittest

import envi.bits as e_bits
import envi.archs.ppc.spr as eaps
import envi.archs.ppc.regs as eapr
import envi.archs.ppc.const as eapc

# import a few specific constants from the ppc_mmu module that are not exported
# automatically with *
from ..ppc_mmu import PpcTlbPageSize, PpcTlbPerm, PpcTlbFlags, PpcTLBEntry, \
                      MAS0_TBSEL_SHIFT, MAS0_ESEL_SHIFT, MAS4_TLBSELD_SHIFT, \
                      MAS4_TSIZED_SHIFT, MAS4_FLAGSD_SHIFT

from .helpers import MPC5674_Test


# From "8.5.2 BAM Program Operation" page 296 of MPC5674FRM.pdf
default_tlb_entries = (
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_1MB,   'epn': 0xFFF00000, 'flags': PpcTlbFlags.IG,  'rpn': 0xFFF00000, 'user': 0, 'perm': PpcTlbPerm.SU_RWX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_16MB,  'epn': 0x00000000, 'flags': 0,               'rpn': 0x00000000, 'user': 0, 'perm': PpcTlbPerm.SU_RWX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_16MB,  'epn': 0x20000000, 'flags': 0,               'rpn': 0x20000000, 'user': 0, 'perm': PpcTlbPerm.SU_RWX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_256KB, 'epn': 0x40000000, 'flags': PpcTlbFlags.I,   'rpn': 0x40000000, 'user': 0, 'perm': PpcTlbPerm.SU_RWX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_1MB,   'epn': 0xC3F00000, 'flags': PpcTlbFlags.IG,  'rpn': 0xC3F00000, 'user': 0, 'perm': PpcTlbPerm.SU_RWX},
)

default_mas_values = (
    (0x10000000, 0xc0000500, 0xFFF0000A, 0xFFF0003f),
    (0x10010000, 0xc0000700, 0x00000000, 0x0000003f),
    (0x10020000, 0xc0000700, 0x20000000, 0x2000003f),
    (0x10030000, 0xc0000400, 0x40000008, 0x4000003f),
    (0x10040000, 0xc0000500, 0xC3F0000A, 0xC3F0003f),
)

test_tlb_entries = (
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_1MB,   'epn': 0xFFF00000, 'flags': PpcTlbFlags.WIG, 'rpn': 0xFFF00000, 'user': 0, 'perm': PpcTlbPerm.SU_RWX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_64KB,  'epn': 0x00000000, 'flags': PpcTlbFlags.WIG, 'rpn': 0x00000000, 'user': 0, 'perm': PpcTlbPerm.SU_RW},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_64KB,  'epn': 0x00010000, 'flags': PpcTlbFlags.WIG, 'rpn': 0x00010000, 'user': 0, 'perm': PpcTlbPerm.SU_RW},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_256KB, 'epn': 0x40000000, 'flags': PpcTlbFlags.WIG, 'rpn': 0x40000000, 'user': 0, 'perm': PpcTlbPerm.SU_RWX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_1MB,   'epn': 0xC3F00000, 'flags': PpcTlbFlags.WIG, 'rpn': 0xC3F00000, 'user': 0, 'perm': PpcTlbPerm.SU_RWX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_64KB,  'epn': 0x60000000, 'flags': PpcTlbFlags.WIG, 'rpn': 0x40000000, 'user': 0, 'perm': PpcTlbPerm.SU_RWX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_64KB,  'epn': 0x60010000, 'flags': PpcTlbFlags.WIG, 'rpn': 0x40010000, 'user': 0, 'perm': PpcTlbPerm.SU_RWX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_64KB,  'epn': 0x60020000, 'flags': PpcTlbFlags.WIG, 'rpn': 0x40020000, 'user': 0, 'perm': PpcTlbPerm.SU_RWX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_64KB,  'epn': 0x60030000, 'flags': PpcTlbFlags.WIG, 'rpn': 0x40030000, 'user': 0, 'perm': PpcTlbPerm.SU_RWX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_256KB, 'epn': 0x60040000, 'flags': PpcTlbFlags.WIG, 'rpn': 0x30000000, 'user': 0, 'perm': PpcTlbPerm.SU_RW},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_256KB, 'epn': 0x60080000, 'flags': PpcTlbFlags.WIG, 'rpn': 0x30040000, 'user': 0, 'perm': PpcTlbPerm.SU_RW},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_16KB,  'epn': 0x00FFC000, 'flags': PpcTlbFlags.G,   'rpn': 0x00FFC000, 'user': 0, 'perm': PpcTlbPerm.SU_R},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_256KB, 'epn': 0x00040000, 'flags': PpcTlbFlags.WG,  'rpn': 0x00040000, 'user': 0, 'perm': PpcTlbPerm.SU_RX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_256KB, 'epn': 0x00080000, 'flags': PpcTlbFlags.G,   'rpn': 0x00080000, 'user': 0, 'perm': PpcTlbPerm.SU_RX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_256KB, 'epn': 0x000C0000, 'flags': PpcTlbFlags.G,   'rpn': 0x000C0000, 'user': 0, 'perm': PpcTlbPerm.SU_RX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_256KB, 'epn': 0x00100000, 'flags': PpcTlbFlags.G,   'rpn': 0x00100000, 'user': 0, 'perm': PpcTlbPerm.SU_RX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_256KB, 'epn': 0x00140000, 'flags': PpcTlbFlags.G,   'rpn': 0x00140000, 'user': 0, 'perm': PpcTlbPerm.SU_RX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_256KB, 'epn': 0x00180000, 'flags': PpcTlbFlags.G,   'rpn': 0x00180000, 'user': 0, 'perm': PpcTlbPerm.SU_RX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_256KB, 'epn': 0x001C0000, 'flags': PpcTlbFlags.G,   'rpn': 0x001C0000, 'user': 0, 'perm': PpcTlbPerm.SU_RX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_256KB, 'epn': 0x00200000, 'flags': PpcTlbFlags.G,   'rpn': 0x00200000, 'user': 0, 'perm': PpcTlbPerm.SU_RX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_256KB, 'epn': 0x00240000, 'flags': PpcTlbFlags.G,   'rpn': 0x00240000, 'user': 0, 'perm': PpcTlbPerm.SU_RX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_256KB, 'epn': 0x00280000, 'flags': PpcTlbFlags.G,   'rpn': 0x00280000, 'user': 0, 'perm': PpcTlbPerm.SU_RX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_256KB, 'epn': 0x002C0000, 'flags': PpcTlbFlags.G,   'rpn': 0x002C0000, 'user': 0, 'perm': PpcTlbPerm.SU_RX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_256KB, 'epn': 0x00300000, 'flags': PpcTlbFlags.G,   'rpn': 0x00300000, 'user': 0, 'perm': PpcTlbPerm.SU_RX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_256KB, 'epn': 0x00340000, 'flags': PpcTlbFlags.G,   'rpn': 0x00340000, 'user': 0, 'perm': PpcTlbPerm.SU_RX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_256KB, 'epn': 0x00380000, 'flags': PpcTlbFlags.G,   'rpn': 0x00380000, 'user': 0, 'perm': PpcTlbPerm.SU_RX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_256KB, 'epn': 0x003C0000, 'flags': PpcTlbFlags.G,   'rpn': 0x003C0000, 'user': 0, 'perm': PpcTlbPerm.SU_RX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_64KB,  'epn': 0x00020000, 'flags': PpcTlbFlags.IG,  'rpn': 0x00020000, 'user': 0, 'perm': PpcTlbPerm.SU_R},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_64KB,  'epn': 0x00030000, 'flags': PpcTlbFlags.IG,  'rpn': 0x00030000, 'user': 0, 'perm': PpcTlbPerm.SU_R},
    {'valid': 0, 'iprot': 0, 'tid': 0, 'ts': 0, 'tsiz': 0,                         'epn': 0,          'flags': 0,               'rpn': 0,          'user': 0, 'perm': 0},
    {'valid': 0, 'iprot': 0, 'tid': 0, 'ts': 0, 'tsiz': 0,                         'epn': 0,          'flags': 0,               'rpn': 0,          'user': 0, 'perm': 0},
    {'valid': 0, 'iprot': 0, 'tid': 0, 'ts': 0, 'tsiz': 0,                         'epn': 0,          'flags': 0,               'rpn': 0,          'user': 0, 'perm': 0},
)

# MAS1, 2, 3 values that correspond to the TLB entry values in test_tlb_entries
# Each entry is (MAS0, MAS1, MAS2, MAS3)
# MAS0 may not be used by every test
test_mas_values = (
    (0x10000000, 0xc0000500, 0xfff0001a, 0xfff0003f),
    (0x10010000, 0xc0000300, 0x0000001a, 0x0000000f),
    (0x10020000, 0xc0000300, 0x0001001a, 0x0001000f),
    (0x10030000, 0xc0000400, 0x4000001a, 0x4000003f),
    (0x10040000, 0xc0000500, 0xc3f0001a, 0xc3f0003f),
    (0x10050000, 0xc0000300, 0x6000001a, 0x4000003f),
    (0x10060000, 0xc0000300, 0x6001001a, 0x4001003f),
    (0x10070000, 0xc0000300, 0x6002001a, 0x4002003f),
    (0x10080000, 0xc0000300, 0x6003001a, 0x4003003f),
    (0x10090000, 0xc0000400, 0x6004001a, 0x3000000f),
    (0x100a0000, 0xc0000400, 0x6008001a, 0x3004000f),
    (0x100b0000, 0xc0000200, 0x00ffc002, 0x00ffc003),
    (0x100c0000, 0xc0000400, 0x00040012, 0x00040033),
    (0x100d0000, 0xc0000400, 0x00080002, 0x00080033),
    (0x100e0000, 0xc0000400, 0x000c0002, 0x000c0033),
    (0x100f0000, 0xc0000400, 0x00100002, 0x00100033),
    (0x10100000, 0xc0000400, 0x00140002, 0x00140033),
    (0x10110000, 0xc0000400, 0x00180002, 0x00180033),
    (0x10120000, 0xc0000400, 0x001C0002, 0x001C0033),
    (0x10130000, 0xc0000400, 0x00200002, 0x00200033),
    (0x10140000, 0xc0000400, 0x00240002, 0x00240033),
    (0x10150000, 0xc0000400, 0x00280002, 0x00280033),
    (0x10160000, 0xc0000400, 0x002C0002, 0x002C0033),
    (0x10170000, 0xc0000400, 0x00300002, 0x00300033),
    (0x10180000, 0xc0000400, 0x00340002, 0x00340033),
    (0x10190000, 0xc0000400, 0x00380002, 0x00380033),
    (0x101a0000, 0xc0000400, 0x003C0002, 0x003C0033),
    (0x101b0000, 0xc0000300, 0x0002000a, 0x00020003),
    (0x101c0000, 0xc0000300, 0x0003000a, 0x00030003),
    (0x101d0000,          0,          0,          0),
    (0x101e0000,          0,          0,          0),
    (0x101f0000,          0,          0,          0),
)

# Have iprot first so when enumerated the values generated will be unprotected
tlb_entry_attrs = ('iprot', 'valid', 'tid', 'ts', 'tsiz', 'epn', 'flags', 'rpn', 'user', 'perm')

# MFSPR/MTSPR constants
MFSPR_VAL         = 0x7C0002A6
MTSPR_VAL         = 0x7C0003A6
INSTR_REG_SHIFT   = 21
INSTR_SPR_SHIFT   = 11

# TLB instruction constants
TLBRE_VAL         = 0x7C000764
TLBWE_VAL         = 0x7C0007A4
TLBSX_VAL         = 0x7C000724
TLBIVAX_VAL       = 0x7C000624
TLBSYNC_VAL       = 0x7C00046C
FORMX_OPER2_SHIFT = 11


class PpcTLBEntry_Test(unittest.TestCase):
    def test_config(self):
        entry = PpcTLBEntry(0)
        # All params should default to 0
        for attr in tlb_entry_attrs:
            msg = '%s = 0' % attr
            self.assertEqual(getattr(entry, attr), 0, msg)

        # Change all of the params to something different
        for val, attr in enumerate(tlb_entry_attrs):
            setattr(entry, attr, val)

        # Ensure that the config function defaults unspecified params to 0
        entry.config()
        for attr in tlb_entry_attrs:
            msg = '%s = 0' % attr
            self.assertEqual(getattr(entry, attr), 0, msg)

        # Change the values
        args = dict((a, v) for v, a in enumerate(tlb_entry_attrs))
        entry.config(**args)

        # Verify they were changed correctly
        for val, attr in enumerate(tlb_entry_attrs):
            msg = '%s = %d' % (attr, val)
            self.assertEqual(getattr(entry, attr), val, msg)

    def test_read(self):
        entry = PpcTLBEntry(0)

        self.assertEqual(len(test_tlb_entries), len(test_mas_values))

        # Set the TLB entry values to the values in each test_tlb_entries test
        # and confirm that when read() is called the MAS1, MAS2, and MAS3
        # registers match test_mas_values
        for esel, (test, results) in enumerate(zip(test_tlb_entries, test_mas_values)):
            entry.config(**test)
            self.assertEqual(entry.read(), results[1:], str(esel))

    def test_write(self):
        entry = PpcTLBEntry(0)

        # Write MAS1, MAS2, and MAS3 test values in test_mas_values to the TLB
        # entry and confirm that the values extracted match the values in
        # test_tlb_entries.
        for esel, (test, results) in enumerate(zip(test_mas_values, test_tlb_entries)):
            entry.write(*test[1:])
            for attr, val in results.items():
                msg = 'tlb[%d].%s == 0x%x' % (esel, attr, val)
                self.assertEqual(getattr(entry, attr), val, msg)

    def test_iprot(self):
        # Use test_tlb_entries[4] as the basis for this test, but change iport
        test = dict(test_tlb_entries[4])
        test['iprot'] = 0
        entry = PpcTLBEntry(0, **test)
        self.assertEqual(entry.valid, 1)
        self.assertEqual(entry.iprot, 0)

        # Change the MAS1 value of the results to clear the IPROT flag (bit 1)
        _, mas1, mas2, mas3 = test_mas_values[4]
        mas1 &= 0xBFFFFFFF
        self.assertEqual(entry.read(), (mas1, mas2, mas3))

        # When the entry is invalidated confirm the valid bit is no longer set
        entry.invalidate()
        self.assertEqual(entry.valid, 0)
        self.assertEqual(entry.iprot, 0)

        mas1 &= 0x3FFFFFFF
        self.assertEqual(entry.read(), (mas1, mas2, mas3))

        # Set valid & iprot
        entry.valid = 1
        entry.iprot = 1
        self.assertEqual(entry.read(), test_mas_values[4][1:])

        # Confirm invalidating the entry does not clear the valid bit
        entry.invalidate()
        self.assertEqual(entry.valid, 1)
        self.assertEqual(entry.iprot, 1)
        self.assertEqual(entry.read(), test_mas_values[4][1:])

        # But confirm that we can reconfigure the entry through the normal
        # write() method
        entry.write(mas1, mas2, mas3)
        self.assertEqual(entry.valid, 0)
        self.assertEqual(entry.iprot, 0)


class MPC5674_MMU_Test(MPC5674_Test):

    ##################################################
    # UTILITIES
    ##################################################

    def get_spr_num(self, reg):
        regname = self.emu.getRegisterName(reg)
        return next(num for num, (name, _, _) in eaps.sprs.items() if name == regname)

    def mfspr(self, spr, reg=eapr.REG_R3):
        # Get the actual PPC SPR number
        ppcspr = self.get_spr_num(spr)

        # The SPR has the lower 5 bits at:
        #   0x001F0000
        # and the upper 5 bits at
        #   0x0000F100
        encoded_spr = ((ppcspr & 0x1F) << 5) | ((ppcspr >> 5) & 0x1F)

        mfspr_val = MFSPR_VAL | (reg << INSTR_REG_SHIFT) | (encoded_spr << INSTR_SPR_SHIFT)
        mfspr_bytes = e_bits.buildbytes(mfspr_val, 4, self.emu.getEndian())
        mfspr_op = self.emu.archParseOpcode(mfspr_bytes)

        self.emu.executeOpcode(mfspr_op)
        spr_val = self.emu.getRegister(reg)
        return spr_val

    def mtspr(self, spr, val, reg=eapr.REG_R3):
        # Get the actual PPC SPR number
        ppcspr = self.get_spr_num(spr)

        # The SPR has the lower 5 bits at:
        #   0x001F0000
        # and the upper 5 bits at
        #   0x0000F100
        encoded_spr = ((ppcspr & 0x1F) << 5) | ((ppcspr >> 5) & 0x1F)

        mtspr_val = MTSPR_VAL | (reg << INSTR_REG_SHIFT) | (encoded_spr << INSTR_SPR_SHIFT)
        mtspr_bytes = e_bits.buildbytes(mtspr_val, 4, self.emu.getEndian())
        mtspr_op = self.emu.archParseOpcode(mtspr_bytes)

        self.emu.setRegister(reg, val)
        self.emu.executeOpcode(mtspr_op)

    def tlbre(self):
        # 7C000764  tlbre
        tlbre_bytes = e_bits.buildbytes(TLBRE_VAL, 4, self.emu.getEndian())
        tlbre_op = self.emu.archParseOpcode(tlbre_bytes)
        self.emu.executeOpcode(tlbre_op)

    def tlbwe(self):
        # 7C0007A4  tlbwe
        tlbwe_bytes = e_bits.buildbytes(TLBWE_VAL, 4, self.emu.getEndian())
        tlbwe_op = self.emu.archParseOpcode(tlbwe_bytes)
        self.emu.executeOpcode(tlbwe_op)

    def tlbsx(self, val):
        # 7C001F24  tlbsx 0,r3
        self.emu.setRegister(eapr.REG_R3, val)
        tlbsx_val = TLBSX_VAL | (eapr.REG_R3 << FORMX_OPER2_SHIFT)
        tlbsx_bytes = e_bits.buildbytes(tlbsx_val, 4, self.emu.getEndian())
        tlbsx_op = self.emu.archParseOpcode(tlbsx_bytes)
        self.emu.executeOpcode(tlbsx_op)

    def tlbivax(self, val):
        # 7C001E24  tlbivax 0,r3
        self.emu.setRegister(eapr.REG_R3, val)
        tlbivax_val = TLBIVAX_VAL | (eapr.REG_R3 << FORMX_OPER2_SHIFT)
        tlbivax_bytes = e_bits.buildbytes(tlbivax_val, 4, self.emu.getEndian())
        tlbivax_op = self.emu.archParseOpcode(tlbivax_bytes)
        self.emu.executeOpcode(tlbivax_op)

    def tlbsync(self):
        # 7C00046C  tlbsync
        tlbsync_bytes = e_bits.buildbytes(TLBSYNC_VAL, 4, self.emu.getEndian())
        tlbsync_op = self.emu.archParseOpcode(tlbsync_bytes)
        self.emu.executeOpcode(tlbsync_op)

    ##################################################
    # TESTS
    ##################################################

    def test_mmu_config(self):
        '''
        Verify the tlbConfig() function uses the correct default values
        '''
        tlb_config_defaults = {
            'valid': 1,
            'iprot': 1,
            'tid': 0,
            'ts': 0,
            'tsiz': 0,
            'epn': 0,
            'flags': 0,
            'rpn': 0,
            'user': 0,
            'perm': PpcTlbPerm.SU_RWX
        }
        # MAS registers resulting from the default config
        results = (
            0xC0000000,
            0x00000000,
            0x0000003F,
        )
        self.emu.mmu.tlbConfig(0)
        self.assertEqual(self.emu.mmu._tlb[0].read(), results)

    def test_mmucfg(self):
        val = self.mfspr(spr=eapr.REG_MMUCFG)
        self.assertEqual(val, 0x004009C4)

        # MMUCFG is read-only
        self.mtspr(spr=eapr.REG_MMUCFG, val=0xFFFFFFFF)
        val = self.mfspr(spr=eapr.REG_MMUCFG)
        self.assertEqual(val, 0x004009C4)

    def test_tlb0cfg(self):
        self.assertEqual(self.mfspr(spr=eapr.REG_TLB0CFG), 0x00000000)

        # TLB0CFG is read-only
        self.mtspr(spr=eapr.REG_TLB0CFG, val=0xFFFFFFFF)
        self.assertEqual(self.mfspr(spr=eapr.REG_TLB0CFG), 0x00000000)

    def test_tlb1cfg(self):
        self.assertEqual(self.mfspr(spr=eapr.REG_TLB1CFG), 0x200BE020)

        # TLB1CFG is read-only
        self.mtspr(spr=eapr.REG_TLB1CFG, val=0xFFFFFFFF)
        self.assertEqual(self.mfspr(spr=eapr.REG_TLB1CFG), 0x200BE020)

    def test_l1csr0(self):
        self.assertEqual(self.mfspr(spr=eapr.REG_L1CSR0), 0x00000000)

        # Ensure that the DCINV flag is always 0
        self.mtspr(spr=eapr.REG_L1CSR0, val=0xFFFFFFFF)
        self.assertEqual(self.mfspr(spr=eapr.REG_L1CSR0), 0xFFFFFFFD)

    def test_l1csr1(self):
        self.assertEqual(self.mfspr(spr=eapr.REG_L1CSR1), 0x00000000)

        # Ensure that the DCINV flag is always 0
        self.mtspr(spr=eapr.REG_L1CSR1, val=0xFFFFFFFF)
        self.assertEqual(self.mfspr(spr=eapr.REG_L1CSR1), 0xFFFFFFFD)

    def test_mmu_defaults(self):
        '''
        Ensure that the TLB entries are configured as expected to allow access
        to the standard MPC5674F peripherals.
        '''
        for esel in range(len(default_tlb_entries)):
            for attr, val in default_tlb_entries[esel].items():
                msg = 'tlb[%d].%s == 0x%x' % (esel, attr, val)
                self.assertEqual(getattr(self.emu.mmu._tlb[esel], attr), val, msg)

    def test_tlbre(self):
        '''
        Use the tlbre instruction to read the default TLB configs and ensure
        they match the expected values
        '''
        for esel in range(len(default_tlb_entries)):
            mas0 = (1 << MAS0_TBSEL_SHIFT) | (esel << MAS0_ESEL_SHIFT)
            self.emu.setRegister(eapr.REG_MAS0, mas0)
            self.tlbre()

            _, mas1, mas2, mas3 = default_mas_values[esel]
            self.assertEqual(self.emu.getRegister(eapr.REG_MAS1), mas1, str(esel))
            self.assertEqual(self.emu.getRegister(eapr.REG_MAS2), mas2, str(esel))
            self.assertEqual(self.emu.getRegister(eapr.REG_MAS3), mas3, str(esel))

    def test_tlbwe(self):
        '''
        Write the test MAS values to the MAS1-MAS3 registers, execute tlbwe
        and ensure that the TLB entries have been changed correctly.
        '''
        # First set all TLB entry attributes to 1. This isn't really a
        # meaningful value for all of the attributes but it will ensure that
        # changes are meaningful.
        for esel in range(len(default_tlb_entries)):
            for attr in tlb_entry_attrs:
                setattr(self.emu.mmu._tlb[esel], attr, 0)

        # Write all of the entires
        for esel in range(len(test_tlb_entries)):
            mas0, mas1, mas2, mas3 = test_mas_values[esel]
            self.emu.setRegister(eapr.REG_MAS0, mas0)
            self.emu.setRegister(eapr.REG_MAS1, mas1)
            self.emu.setRegister(eapr.REG_MAS2, mas2)
            self.emu.setRegister(eapr.REG_MAS3, mas3)
            self.tlbwe()

        # Verify the TLB entires are correct
        for esel in range(len(test_tlb_entries)):
            for attr, val in test_tlb_entries[esel].items():
                msg = 'tlb[%d].%s == 0x%x' % (esel, attr, val)
                self.assertEqual(getattr(self.emu.mmu._tlb[esel], attr), val, msg)

    def test_mmucsr0(self):
        # Mark all of the TLB entries as valid, but only the odd entries will
        # be protected
        for esel in range(len(self.emu.mmu._tlb)):
            self.emu.mmu._tlb[esel].valid = 1
            self.emu.mmu._tlb[esel].iprot = esel % 2

        # MMUCSR0 is clear by default
        self.assertEqual(self.mfspr(spr=eapr.REG_MMUCSR0), 0x00000000)

        # Writing 1's to bits except for 30 does nothing
        self.mtspr(spr=eapr.REG_MMUCSR0, val=0xFFFFFFFD)

        for esel in range(len(self.emu.mmu._tlb)):
            msg = '[%d] = %d, %d' % (esel, 1, esel % 2)
            self.assertEqual(self.emu.mmu._tlb[esel].valid, 1, msg)
            self.assertEqual(self.emu.mmu._tlb[esel].iprot, esel % 2, msg)

        # Writing 1 to bit 30 invalidates all non-protected TLB entries
        self.mtspr(spr=eapr.REG_MMUCSR0, val=0x00000002)

        for esel in range(len(self.emu.mmu._tlb)):
            msg = '[%d] = %d, %d' % (esel, esel % 2, esel % 2)
            self.assertEqual(self.emu.mmu._tlb[esel].valid, esel % 2, msg)
            self.assertEqual(self.emu.mmu._tlb[esel].iprot, esel % 2, msg)

        # The read value should still be 0
        self.assertEqual(self.mfspr(spr=eapr.REG_MMUCSR0), 0x00000000)

    def test_tlbivax_specific(self):
        def randts():
            return random.getrandbits(1)

        def randtid():
            return random.getrandbits(7)

        # This test will find all TLB entries that match 0x12345678 (of varying
        # page sizes) and invalidate them if they are not protected

        # Set the first 7 TLB entries to match with different TS & PID values,
        # with valid and iprot set
        self.emu.mmu.tlbConfig(0,  epn=0x12340000, tsiz=PpcTlbPageSize.SIZE_64KB,  ts=randts(), tid=randtid())
        self.emu.mmu.tlbConfig(1,  epn=0x12345200, tsiz=PpcTlbPageSize.SIZE_4KB,   ts=randts(), tid=randtid())
        self.emu.mmu.tlbConfig(2,  epn=0x12340000, tsiz=PpcTlbPageSize.SIZE_1MB,   ts=randts(), tid=randtid())
        self.emu.mmu.tlbConfig(3,  epn=0x12345000, tsiz=PpcTlbPageSize.SIZE_16KB,  ts=randts(), tid=randtid())
        self.emu.mmu.tlbConfig(4,  epn=0x12240000, tsiz=PpcTlbPageSize.SIZE_2MB,   ts=randts(), tid=randtid())
        self.emu.mmu.tlbConfig(5,  epn=0x10000000, tsiz=PpcTlbPageSize.SIZE_128MB, ts=randts(), tid=randtid())

        # Because the search EPN and entry EPN should be masked before being
        # compared.  so it doesn't matter what the EPN is for a 4GB entry.
        self.emu.mmu.tlbConfig(6,  epn=0x00000000, tsiz=PpcTlbPageSize.SIZE_4GB,   ts=randts(), tid=randtid())

        # Set 4 more TLB entires to similar but non-matching addresses
        self.emu.mmu.tlbConfig(7,  epn=0x12200000, tsiz=PpcTlbPageSize.SIZE_1MB,   ts=randts(), tid=randtid(), iprot=0)
        self.emu.mmu.tlbConfig(8,  epn=0x12347000, tsiz=PpcTlbPageSize.SIZE_4KB,   ts=randts(), tid=randtid(), iprot=0)
        self.emu.mmu.tlbConfig(9,  epn=0x02340000, tsiz=PpcTlbPageSize.SIZE_256MB, ts=randts(), tid=randtid(), iprot=0)
        self.emu.mmu.tlbConfig(10, epn=0x10000000, tsiz=PpcTlbPageSize.SIZE_64KB,  ts=randts(), tid=randtid(), iprot=0)

        # clear iprot for the rest of the TLB entries
        for esel in range(11, 32):
            self.emu.mmu.tlbConfig(esel, iprot=0)

        # bits 0:21 = 0x12345678
        # bit    28 = 1
        self.tlbivax(0x12345408)

        # Ensure that none of the entries were invalidated
        for esel in range(0, 7):
            msg = '[%d] = %d, %d' % (esel, 1, 1)
            self.assertEqual(self.emu.mmu._tlb[esel].valid, 1, msg)
            self.assertEqual(self.emu.mmu._tlb[esel].iprot, 1, msg)
        for esel in range(7, 32):
            msg = '[%d] = %d, %d' % (esel, 1, 0)
            self.assertEqual(self.emu.mmu._tlb[esel].valid, 1, msg)
            self.assertEqual(self.emu.mmu._tlb[esel].iprot, 0, msg)

        # remove iprot for the first 6 TLB entries and ensure tlbivax
        # invalidates them
        for esel in range(0, 7):
            self.emu.mmu._tlb[esel].iprot = 0

        # bits 0:21 = 0x12345678
        # bit    28 = 1
        self.tlbivax(0x12345408)

        for esel in range(0, 7):
            msg = '[%d] = %d, %d' % (esel, 0, 0)
            self.assertEqual(self.emu.mmu._tlb[esel].valid, 0, msg)
            self.assertEqual(self.emu.mmu._tlb[esel].iprot, 0, msg)
        for esel in range(7, 32):
            msg = '[%d] = %d, %d' % (esel, 1, 0)
            self.assertEqual(self.emu.mmu._tlb[esel].valid, 1, msg)
            self.assertEqual(self.emu.mmu._tlb[esel].iprot, 0, msg)

    def test_tlbivax_all(self):
        # Mark all of the TLB entries as valid, but only the odd entries will
        # be protected
        for esel in range(len(self.emu.mmu._tlb)):
            self.emu.mmu._tlb[esel].valid = 1
            self.emu.mmu._tlb[esel].iprot = esel % 2

        # Setting bit 29 of the operand to the tlbivax instruction invalidates
        # all non-protected TLB entries.
        # Bit 28 should be set to 1 for future compatibility (but is ignored)
        self.tlbivax(0x000000C)

        for esel in range(len(self.emu.mmu._tlb)):
            msg = '[%d] = %d, %d' % (esel, esel % 2, esel % 2)
            self.assertEqual(self.emu.mmu._tlb[esel].valid, esel % 2, msg)
            self.assertEqual(self.emu.mmu._tlb[esel].iprot, esel % 2, msg)

    def test_tlbsync(self):
        '''
        No functionality to test for tlbsync, just confirm it does not produce
        an error.
        '''
        # Fill the GPRs with random values
        gpr_vals = {}
        for gpr in range(0, 32):
            val = random.getrandbits(32)
            gpr_vals[gpr] = val
            self.emu.setRegister(gpr, val)

        # Fill all MAS registers with random values
        mas_vals = {}
        for mas in (eapr.REG_MAS0, eapr.REG_MAS1, eapr.REG_MAS2, eapr.REG_MAS3, eapr.REG_MAS4, eapr.REG_MAS6):
            val = random.getrandbits(32)
            mas_vals[mas] = val
            self.emu.setRegister(mas, val)

        # And set every TLB entry to valid, unprotected, and other values
        for esel in range(len(self.emu.mmu._tlb)):
            for val, attr in enumerate(tlb_entry_attrs):
                setattr(self.emu.mmu._tlb[esel], attr, val)

        self.tlbsync()

        # Confirm nothing changed
        for gpr, val in gpr_vals.items():
            msg = 'r%d = %d' % (gpr, val)
            self.assertEqual(self.emu.getRegister(gpr), val, msg)

        for mas, val in mas_vals.items():
            msg = '%s = %d' % (self.emu.getRegisterName(mas), val)
            self.assertEqual(self.emu.getRegister(mas), val, msg)

        for esel in range(len(self.emu.mmu._tlb)):
            for val, attr in enumerate(tlb_entry_attrs):
                self.assertEqual(getattr(self.emu.mmu._tlb[esel], attr), val)

    def test_tlbsx(self):
        # Clear all TLB entires
        for esel in range(32):
            self.emu.mmu._tlb[esel].config()

        # Test TLB entries:
        #   - 0, 4 should be TS=0, PID=0
        #   - 1, 5 should be TS=0, PID=1
        #   - 2, 6 should be TS=1, PID=2
        #   - 3, 7 should be TS=1, PID=1
        #   - the first 4 for EPN 0x70000000
        #   - the second 4 for EPN 0x80000000
        entries = (
            # Global (PID 0) TLB entries for TS0 and TS1
            {'esel': 27, 'valid': 1, 'ts': 0, 'tid': 0, 'tsiz': PpcTlbPageSize.SIZE_64KB, 'epn': 0x60000000, 'rpn': 0xA0000000},
            {'esel': 28, 'valid': 1, 'ts': 0, 'tid': 0, 'tsiz': PpcTlbPageSize.SIZE_64KB, 'epn': 0x60010000, 'rpn': 0xA0010000},
            {'esel': 29, 'valid': 1, 'ts': 1, 'tid': 0, 'tsiz': PpcTlbPageSize.SIZE_64KB, 'epn': 0x60000000, 'rpn': 0xB0000000},
            {'esel': 30, 'valid': 1, 'ts': 1, 'tid': 0, 'tsiz': PpcTlbPageSize.SIZE_64KB, 'epn': 0x60010000, 'rpn': 0xB0010000},

            # Process-specific TLB entries
            {'esel': 0,  'valid': 1, 'ts': 0, 'tid': 1, 'tsiz': PpcTlbPageSize.SIZE_64KB, 'epn': 0x70000000, 'rpn': 0x40000000},
            {'esel': 1,  'valid': 1, 'ts': 0, 'tid': 2, 'tsiz': PpcTlbPageSize.SIZE_64KB, 'epn': 0x70000000, 'rpn': 0x40010000},
            {'esel': 5,  'valid': 1, 'ts': 1, 'tid': 3, 'tsiz': PpcTlbPageSize.SIZE_64KB, 'epn': 0x70000000, 'rpn': 0x40020000},
            {'esel': 10, 'valid': 1, 'ts': 1, 'tid': 2, 'tsiz': PpcTlbPageSize.SIZE_64KB, 'epn': 0x70000000, 'rpn': 0x40030000},
            {'esel': 7,  'valid': 1, 'ts': 0, 'tid': 1, 'tsiz': PpcTlbPageSize.SIZE_64KB, 'epn': 0x80000000, 'rpn': 0x40040000},
            {'esel': 2,  'valid': 1, 'ts': 0, 'tid': 2, 'tsiz': PpcTlbPageSize.SIZE_64KB, 'epn': 0x80000000, 'rpn': 0x40050000},
            {'esel': 4,  'valid': 1, 'ts': 1, 'tid': 3, 'tsiz': PpcTlbPageSize.SIZE_64KB, 'epn': 0x80000000, 'rpn': 0x40060000},
            {'esel': 31, 'valid': 1, 'ts': 1, 'tid': 2, 'tsiz': PpcTlbPageSize.SIZE_64KB, 'epn': 0x80000000, 'rpn': 0x40070000},

            # A few invalid entries with different RPNs but with duplicate
            # TS/TID/EPN values
            {'esel': 3,  'valid': 0, 'ts': 1, 'tid': 2, 'tsiz': PpcTlbPageSize.SIZE_64KB, 'epn': 0x80000000, 'rpn': 0x50060000},
            {'esel': 6,  'valid': 0, 'ts': 0, 'tid': 0, 'tsiz': PpcTlbPageSize.SIZE_64KB, 'epn': 0x80000000, 'rpn': 0x50040000},
            {'esel': 9,  'valid': 0, 'ts': 1, 'tid': 1, 'tsiz': PpcTlbPageSize.SIZE_64KB, 'epn': 0x70000000, 'rpn': 0x50030000},
            {'esel': 20, 'valid': 0, 'ts': 1, 'tid': 1, 'tsiz': PpcTlbPageSize.SIZE_64KB, 'epn': 0x80000000, 'rpn': 0x50070000},

            # Some different EPNs but the TLB entries are not valid
            {'esel': 11, 'valid': 0, 'ts': 0, 'tid': 1, 'tsiz': PpcTlbPageSize.SIZE_64KB, 'epn': 0x90000000, 'rpn': 0x60000000},
            {'esel': 12, 'valid': 0, 'ts': 1, 'tid': 1, 'tsiz': PpcTlbPageSize.SIZE_64KB, 'epn': 0xa0000000, 'rpn': 0x60000000},
            {'esel': 13, 'valid': 0, 'ts': 0, 'tid': 2, 'tsiz': PpcTlbPageSize.SIZE_64KB, 'epn': 0x90000000, 'rpn': 0x60000000},
            {'esel': 14, 'valid': 0, 'ts': 1, 'tid': 2, 'tsiz': PpcTlbPageSize.SIZE_64KB, 'epn': 0xa0000000, 'rpn': 0x60000000},
            {'esel': 15, 'valid': 0, 'ts': 0, 'tid': 3, 'tsiz': PpcTlbPageSize.SIZE_64KB, 'epn': 0x90000000, 'rpn': 0x60000000},
            {'esel': 16, 'valid': 0, 'ts': 1, 'tid': 3, 'tsiz': PpcTlbPageSize.SIZE_64KB, 'epn': 0xa0000000, 'rpn': 0x60000000},
        )

        # Configure the test TLB entries
        for entry in entries:
            self.emu.mmu.tlbConfig(**entry)

        # When tlbsx does not find a valid entry some of the MASx register
        # fields are filled in from the defaults values in MAS4.
        # (In the test setup below MAS0[NV] will be set to 15)
        mas4 = (1 << MAS4_TLBSELD_SHIFT) | \
                (PpcTlbPageSize.SIZE_2KB << MAS4_TSIZED_SHIFT) | \
                ((PpcTlbFlags.VLE | PpcTlbFlags.WG) << MAS4_FLAGSD_SHIFT)
        self.emu.setRegister(eapr.REG_MAS4, mas4)

        tests = (
            #      MAS6  | search addr |      MAS0 |      MAS1 |      MAS2 |      MAS3

            # First 8 tests should find the 8 process-specific entries
            ((0x00010000, 0x70003E3E), (0x10000000, 0xc0010300, 0x70000000, 0x4000003f)),
            ((0x00020000, 0x70003E3E), (0x10010000, 0xc0020300, 0x70000000, 0x4001003f)),
            ((0x00030001, 0x70003E3E), (0x10050000, 0xc0031300, 0x70000000, 0x4002003f)),
            ((0x00020001, 0x70003E3E), (0x100a0000, 0xc0021300, 0x70000000, 0x4003003f)),
            ((0x00010000, 0x80003E3E), (0x10070000, 0xc0010300, 0x80000000, 0x4004003f)),
            ((0x00020000, 0x80003E3E), (0x10020000, 0xc0020300, 0x80000000, 0x4005003f)),
            ((0x00030001, 0x80003E3E), (0x10040000, 0xc0031300, 0x80000000, 0x4006003f)),
            ((0x00020001, 0x80003E3E), (0x101f0000, 0xc0021300, 0x80000000, 0x4007003f)),

            # The search PID doesn't matter for global TLB entries (but TS does)
            ((0x00000000, 0x60003E3E), (0x101B0000, 0xc0000300, 0x60000000, 0xA000003f)),
            ((0x00000001, 0x60003E3E), (0x101D0000, 0xc0001300, 0x60000000, 0xB000003f)),
            ((0x00000000, 0x60013E3E), (0x101C0000, 0xc0000300, 0x60010000, 0xA001003f)),
            ((0x00000001, 0x60013E3E), (0x101E0000, 0xc0001300, 0x60010000, 0xB001003f)),
            ((0x00010000, 0x60003E3E), (0x101B0000, 0xc0000300, 0x60000000, 0xA000003f)),
            ((0x00020001, 0x60003E3E), (0x101D0000, 0xc0001300, 0x60000000, 0xB000003f)),
            ((0x00030000, 0x60013E3E), (0x101C0000, 0xc0000300, 0x60010000, 0xA001003f)),
            ((0x00040001, 0x60013E3E), (0x101E0000, 0xc0001300, 0x60010000, 0xB001003f)),

            # TS=0/PID=3 should have no valid result
            ((0x00030000, 0x70003E3E), (0x100E000E, 0x00030080, 0x70003C32, 0x00000000)),
            ((0x00030000, 0x80003E3E), (0x100E000E, 0x00030080, 0x80003C32, 0x00000000)),

            # Search valid TS/PID combinations but for EPNs that are not valid
            ((0x00010000, 0x90003E3E), (0x100E000E, 0x00010080, 0x90003C32, 0x00000000)),
            ((0x00010001, 0xa0003E3E), (0x100E000E, 0x00011080, 0xa0003C32, 0x00000000)),
            ((0x00020000, 0x90003E3E), (0x100E000E, 0x00020080, 0x90003C32, 0x00000000)),
            ((0x00020001, 0xa0003E3E), (0x100E000E, 0x00021080, 0xa0003C32, 0x00000000)),
            ((0x00030000, 0x90003E3E), (0x100E000E, 0x00030080, 0x90003C32, 0x00000000)),
            ((0x00030001, 0xa0003E3E), (0x100E000E, 0x00031080, 0xa0003C32, 0x00000000)),

            # PID 10 has no non-global entries
            ((0x000a0000, 0x00003E3E), (0x100E000E, 0x000a0080, 0x00003C32, 0x00000000)),
            ((0x000a0001, 0x00013E3E), (0x100E000E, 0x000a1080, 0x00013C32, 0x00000000)),
            ((0x000a0000, 0x70003E3E), (0x100E000E, 0x000a0080, 0x70003C32, 0x00000000)),
            ((0x000a0001, 0x70013E3E), (0x100E000E, 0x000a1080, 0x70013C32, 0x00000000)),
            ((0x000a0000, 0x80003E3E), (0x100E000E, 0x000a0080, 0x80003C32, 0x00000000)),
            ((0x000a0001, 0x80013E3E), (0x100E000E, 0x000a1080, 0x80013C32, 0x00000000)),
            ((0x000a0000, 0x90003E3E), (0x100E000E, 0x000a0080, 0x90003C32, 0x00000000)),
            ((0x000a0001, 0x90013E3E), (0x100E000E, 0x000a1080, 0x90013C32, 0x00000000)),
            ((0x000a0000, 0xa0003E3E), (0x100E000E, 0x000a0080, 0xa0003C32, 0x00000000)),
            ((0x000a0001, 0xa0013E3E), (0x100E000E, 0x000a1080, 0xa0013C32, 0x00000000)),
        )

        for idx, (inputs, outputs) in enumerate(tests):
            # Before running the test fill the MAS registers where the search
            # results are placed with meaningless data, but set the MAS0[NV]
            # field so ESEL will be set as expected during a TLB miss
            self.emu.setRegister(eapr.REG_MAS0, 0xFFFFFFEE)  # MAS0[NV] = 15
            self.emu.setRegister(eapr.REG_MAS1, 0xFFFFFFFF)
            self.emu.setRegister(eapr.REG_MAS2, 0xFFFFFFFF)
            self.emu.setRegister(eapr.REG_MAS3, 0xFFFFFFFF)

            mas6, addr = inputs
            self.emu.setRegister(eapr.REG_MAS6, mas6)
            self.tlbsx(addr)

            mas0, mas1, mas2, mas3 = outputs
            msg = '[%d] find 0x%08x|0x%08x = 0x%08x|0x%08x|0x%08x|0x%08x' % (idx, mas6, addr, mas0, mas1, mas2, mas3)
            self.assertEqual(self.emu.getRegister(eapr.REG_MAS0), mas0, msg)
            self.assertEqual(self.emu.getRegister(eapr.REG_MAS1), mas1, msg)
            self.assertEqual(self.emu.getRegister(eapr.REG_MAS2), mas2, msg)
            self.assertEqual(self.emu.getRegister(eapr.REG_MAS3), mas3, msg)

    def test_valid_instr_addr(self):
        # Before clearing the default TLB entries, write the test data to SRAM

        # (immediates < 1024 are printed in decimal)
        # PPC instruction @ 0x40012340:     li r6,532
        # VLE instruction @ 0x40012340:     e_lha r6,532
        # VLE instruction @ 0x40012342:     se_mtar r12,r1
        self.emu.writeMemValue(0x40012340, 0x38C00214, 4)

        # PPC instruction @ 0x40022340:     addi r3,r3,0x4e8
        # VLE instruction @ 0x40022340:     e_lha r3,0x4e8(r3)
        # VLE instruction @ 0x40022342:     se_add r24,r30
        self.emu.writeMemValue(0x40032340, 0x386304E8, 4)

        # Clear all TLB entires
        for esel in range(32):
            self.emu.mmu._tlb[esel].config()

        self.emu.mmu.tlbConfig(0, epn=0x10000000, rpn=0x40000000, tsiz=PpcTlbPageSize.SIZE_128KB, ts=0)
        self.emu.mmu.tlbConfig(1, epn=0x10080000, rpn=0x40000000, tsiz=PpcTlbPageSize.SIZE_128KB, ts=0,
            flags=PpcTlbFlags.VLE)
        self.emu.mmu.tlbConfig(2, epn=0x10000000, rpn=0x40020000, tsiz=PpcTlbPageSize.SIZE_128KB, ts=1)
        self.emu.mmu.tlbConfig(3, epn=0x10080000, rpn=0x40020000, tsiz=PpcTlbPageSize.SIZE_128KB, ts=1,
            flags=PpcTlbFlags.VLE)

        msr = self.emu.getRegister(eapr.REG_MSR)

        # Test MSR[IS] to 0 for both MSR[DS] = 0 and MSR[DS] = 1
        msr_vals = (
            msr & ~(eapc.MSR_IS_MASK | eapc.MSR_DS_MASK ),
            (msr & ~eapc.MSR_IS_MASK) | eapc.MSR_DS_MASK,
        )
        for test_msr in msr_vals:
            msg = 'MSR = 0x%08x' % test_msr
            self.emu.setRegister(eapr.REG_MSR, test_msr)

            op = self.emu.parseOpcode(0x10012340)
            self.assertEqual(str(op), 'li r6,0x214', msg)

            # When going through the address with VLE enabled different instructions
            # should be found
            op = self.emu.parseOpcode(0x10092340)
            self.assertEqual(str(op), 'e_lha r6,0x214', msg)
            op = self.emu.parseOpcode(0x10092342)
            self.assertEqual(str(op), 'se_mtar r12,r1', msg)

        # Test MSR[IS] to 1 for both MSR[DS] = 0 and MSR[DS] = 1
        msr_vals = (
            (msr | eapc.MSR_IS_MASK) & ~eapc.MSR_DS_MASK,
            msr | eapc.MSR_IS_MASK | eapc.MSR_DS_MASK,
        )
        for test_msr in msr_vals:
            msg = 'MSR = 0x%08x' % test_msr
            self.emu.setRegister(eapr.REG_MSR, test_msr)

            op = self.emu.parseOpcode(0x10012340)
            self.assertEqual(str(op), 'addi r3,r3,0x4e8', msg)

            # When going through the address with VLE enabled different instructions
            # should be found
            op = self.emu.parseOpcode(0x10092340)
            self.assertEqual(str(op), 'e_lha r3,0x4e8(r3)', msg)
            op = self.emu.parseOpcode(0x10092342)
            self.assertEqual(str(op), 'se_add r24,r30', msg)

    def test_valid_data_addr(self):
        # Before clearing the default TLB entries, write the test data to SRAM
        self.emu.writeMemValue(0x40012340, 0xF00DCAFE, 4)
        self.emu.writeMemValue(0x40023400, 0xFEEDF00D, 4)

        # Clear all TLB entires
        for esel in range(32):
            self.emu.mmu._tlb[esel].config()

        self.emu.mmu.tlbConfig(0, epn=0x10000000, rpn=0x40010000, tsiz=PpcTlbPageSize.SIZE_128KB, ts=0)
        self.emu.mmu.tlbConfig(1, epn=0x10000000, rpn=0x40020000, tsiz=PpcTlbPageSize.SIZE_128KB, ts=1)

        # Set MSR[IS] to 0
        msr = self.emu.getRegister(eapr.REG_MSR)
        msr &= eapc.MSR_IS_MASK
        self.emu.setRegister(eapr.REG_MSR, msr)

        self.assertEqual(self.emu.readMemValue(0x10012340, 4), 0xF00DCAFE)

        # Set MSR[IS] to 1
        msr = self.emu.getRegister(eapr.REG_MSR)
        msr |= eapc.MSR_IS_MASK
        self.emu.setRegister(eapr.REG_MSR, msr)

        self.assertEqual(self.emu.readMemValue(0x10012340, 4), 0xF00DCAFE)

    @unittest.skip('Create this test when MMU/TLB peripheral is integrated into PPC Exceptions')
    def test_invalid_instr_addr(self):
        pass

    @unittest.skip('Create this test when MMU/TLB peripheral is integrated into PPC Exceptions')
    def test_invalid_data_addr(self):
        pass

    @unittest.skip('Create this test when MMU/TLB peripheral is integrated into PPC Exceptions')
    def test_tlb_miss(self):
        pass
