import random

from .helpers import MPC5674_Test


EBI_MCR_ADDR            = 0xC3F84000
EBI_TESR_ADDR           = 0xC3F84008
EBI_BMCR_ADDR           = 0xC3F8400C
EBI_CAL_BR0_ADDR        = 0xC3F84040
EBI_CAL_OR0_ADDR        = 0xC3F84044
EBI_CAL_BR1_ADDR        = 0xC3F84048
EBI_CAL_OR1_ADDR        = 0xC3F8404C
EBI_CAL_BR2_ADDR        = 0xC3F84050
EBI_CAL_OR2_ADDR        = 0xC3F84054
EBI_CAL_BR3_ADDR        = 0xC3F84058
EBI_CAL_OR3_ADDR        = 0xC3F8405C

EBI_MCR_VALUE           = 0x00000800
EBI_MCR_BYTES           = b'\x00\x00\x08\x00'
EBI_TESR_VALUE          = 0x00000000
EBI_TESR_BYTES          = b'\x00\x00\x00\x00'
EBI_BMCR_VALUE          = 0x0000FF80
EBI_BMCR_BYTES          = b'\x00\x00\xFF\x80'
EBI_CAL_BRn_VALUE       = 0x20000002
EBI_CAL_BRn_BYTES       = b'\x20\x00\x00\x02'
EBI_CAL_ORn_VALUE       = 0xE0000000
EBI_CAL_ORn_BYTES       = b'\xE0\x00\x00\x00'

# When writing values to EBI BRn/ORn the LSB of the BRn register indicates
# if the bank configuration is valid
EBI_BRn_VALID_MASK  = 0x00000001

EBI_CONFIG_ADDRS = (
    (EBI_CAL_BR0_ADDR, EBI_CAL_OR0_ADDR),
    (EBI_CAL_BR1_ADDR, EBI_CAL_OR1_ADDR),
    (EBI_CAL_BR2_ADDR, EBI_CAL_OR2_ADDR),
    (EBI_CAL_BR3_ADDR, EBI_CAL_OR3_ADDR),
)

# Test BRn/ORn values and the resulting start/end memory range values they
# create.  Each entry has the 4 BRn/ORn config values in it, they may be None to
# indicate that a bank should be left as "invalid"
EBI_DEFAULT_ADDR = 0x20000000
EBI_DEFAULT_SIZE = 0x20000000

# To make things easier we just always ensure the mask completely covers the
# address
EBI_CONFIG_TESTS = (
    # Defaults (minimum possible values)
    (
        (EBI_DEFAULT_ADDR, 0xE0000000, EBI_DEFAULT_ADDR, EBI_DEFAULT_SIZE),
        None,
        None,
        None,
    ),
    # Maximum possible values
    (
        None,
        (0x3FFF8000, 0xFFFF8000, 0x3FFF8000, 0x00008000),
        None,
        None,
    ),
    # Largest possible BRn value
    (
        None,
        None,
        (0x3FFF8000, 0xE0000000, 0x3FFF8000, 0x00008000),
        None,
    ),
    # Largest possible ORn value
    (
        None,
        None,
        None,
        (0x20000000, 0xFFFF8000, 0x20000000, 0x00008000),
    ),
    # Test values
    (
        None,
        None,
        None,
        (0x30000000, 0xFFE00000, 0x30000000, 0x00200000),
    ),
    (
        (0x20400000, 0xFF800000, 0x20400000, 0x00400000),
        (0x20C00000, 0xFFC00000, 0x20C00000, 0x00400000),
        (0x30420000, 0xFFFE0000, 0x30420000, 0x00020000),
        (0x30520000, 0xFFFF0000, 0x30520000, 0x00010000),
    ),
    (
        (0x20000000, 0xF8000000, 0x20000000, 0x08000000),
        (0x28000000, 0xF8000000, 0x28000000, 0x08000000),
        (0x30000000, 0xF8000000, 0x30000000, 0x08000000),
        (0x38000000, 0xF8000000, 0x38000000, 0x08000000),
    ),
)


class MPC5674_EBI_Test(MPC5674_Test):

    ##################################################
    # Tests
    ##################################################

    def test_ebi_regs(self):
        self.assertEqual(self.emu.readMemValue(EBI_MCR_ADDR, 4), EBI_MCR_VALUE)
        self.assertEqual(self.emu.readMemory(EBI_MCR_ADDR, 4), EBI_MCR_BYTES)
        self.assertEqual(self.emu.readMemValue(EBI_TESR_ADDR, 4), EBI_TESR_VALUE)
        self.assertEqual(self.emu.readMemory(EBI_TESR_ADDR, 4), EBI_TESR_BYTES)
        self.assertEqual(self.emu.readMemValue(EBI_BMCR_ADDR, 4), EBI_BMCR_VALUE)
        self.assertEqual(self.emu.readMemory(EBI_BMCR_ADDR, 4), EBI_BMCR_BYTES)
        self.assertEqual(self.emu.readMemValue(EBI_CAL_BR0_ADDR, 4), EBI_CAL_BRn_VALUE)
        self.assertEqual(self.emu.readMemory(EBI_CAL_BR0_ADDR, 4), EBI_CAL_BRn_BYTES)
        self.assertEqual(self.emu.readMemValue(EBI_CAL_OR0_ADDR, 4), EBI_CAL_ORn_VALUE)
        self.assertEqual(self.emu.readMemory(EBI_CAL_OR0_ADDR, 4), EBI_CAL_ORn_BYTES)
        self.assertEqual(self.emu.readMemValue(EBI_CAL_BR1_ADDR, 4), EBI_CAL_BRn_VALUE)
        self.assertEqual(self.emu.readMemory(EBI_CAL_BR1_ADDR, 4), EBI_CAL_BRn_BYTES)
        self.assertEqual(self.emu.readMemValue(EBI_CAL_OR1_ADDR, 4), EBI_CAL_ORn_VALUE)
        self.assertEqual(self.emu.readMemory(EBI_CAL_OR1_ADDR, 4), EBI_CAL_ORn_BYTES)
        self.assertEqual(self.emu.readMemValue(EBI_CAL_BR2_ADDR, 4), EBI_CAL_BRn_VALUE)
        self.assertEqual(self.emu.readMemory(EBI_CAL_BR2_ADDR, 4), EBI_CAL_BRn_BYTES)
        self.assertEqual(self.emu.readMemValue(EBI_CAL_OR2_ADDR, 4), EBI_CAL_ORn_VALUE)
        self.assertEqual(self.emu.readMemory(EBI_CAL_OR2_ADDR, 4), EBI_CAL_ORn_BYTES)
        self.assertEqual(self.emu.readMemValue(EBI_CAL_BR3_ADDR, 4), EBI_CAL_BRn_VALUE)
        self.assertEqual(self.emu.readMemory(EBI_CAL_BR3_ADDR, 4), EBI_CAL_BRn_BYTES)
        self.assertEqual(self.emu.readMemValue(EBI_CAL_OR3_ADDR, 4), EBI_CAL_ORn_VALUE)
        self.assertEqual(self.emu.readMemory(EBI_CAL_OR3_ADDR, 4), EBI_CAL_ORn_BYTES)

    def test_ebi_mmap_config(self):
        # Make sure that the default EBI cached memory bank values match the
        # defaults
        for bank in range(len(self.emu.ebi.bank_config)):
            msg = 'init bank%d' % bank
            self.assertEqual(self.emu.ebi.bank_config[bank].addr, EBI_DEFAULT_ADDR, msg=msg)
            self.assertEqual(self.emu.ebi.bank_config[bank].size, EBI_DEFAULT_SIZE, msg=msg)
            self.assertFalse(self.emu.ebi.bank_config[bank].valid, msg=msg)

        for test in range(len(EBI_CONFIG_TESTS)):
            # One set of values for the 4 external banks
            for bank in range(len(EBI_CONFIG_TESTS[test])):
                msg = 'before test %d: bank%d' % (test, bank)
                if EBI_CONFIG_TESTS[test][bank] is not None:
                    _, _, start, size = EBI_CONFIG_TESTS[test][bank]
                    end = start + size
                    # Make sure that the specified address doesn't exist now
                    self.assertIsNone(self.emu.getMemoryMap(start), msg=msg)
                    self.assertIsNone(self.emu.getMemoryMap(random.randrange(start, end)), msg=msg)
                    self.assertIsNone(self.emu.getMemoryMap(end-1), msg=msg)

            # Write all of the values, ORn first, then BRn and set the VALID bit
            for test_addrs, test_values in zip(EBI_CONFIG_ADDRS, EBI_CONFIG_TESTS[test]):
                if test_values is not None:
                    br_addr, or_addr = test_addrs
                    br_value, or_value, start, end = test_values

                    self.emu.writeMemValue(or_addr, or_value, 4)
                    self.emu.writeMemValue(br_addr, br_value | EBI_BRn_VALID_MASK, 4)

            # Now make sure that the banks have been configured and the
            # corresponding memory map is found
            for bank in range(len(self.emu.ebi.bank_config)):
                msg = 'after test %d: bank%d' % (test, bank)
                if EBI_CONFIG_TESTS[test][bank] is not None:
                    _, _, start, size = EBI_CONFIG_TESTS[test][bank]
                    end = start + size

                    self.assertEqual(self.emu.ebi.bank_config[bank].addr, start, msg=msg)
                    self.assertEqual(self.emu.ebi.bank_config[bank].size, size, msg=msg)
                    self.assertTrue(self.emu.ebi.bank_config[bank].valid, msg=msg)

                    self.assertIsNotNone(self.emu.getMemoryMap(start), msg=msg)
                    self.assertIsNotNone(self.emu.getMemoryMap(random.randrange(start, end)), msg=msg)
                    self.assertIsNotNone(self.emu.getMemoryMap(end-1), msg=msg)
                else:
                    self.assertFalse(self.emu.ebi.bank_config[bank].valid, msg=msg)

            # Now clear the VALID bit for all banks
            for br_addr, _ in EBI_CONFIG_ADDRS:
                value = self.emu.readMemValue(br_addr, 4)
                self.emu.writeMemValue(br_addr, value & ~EBI_BRn_VALID_MASK, 4)
