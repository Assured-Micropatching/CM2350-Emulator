from .helpers import MPC5674_Test


class MPC5674_SIM(MPC5674_Test):
    def test_SIM(self):
        self.assertEqual(self.emu.readMemValue(0xfffec000,4), 0x9F03171C)
        self.assertEqual(self.emu.readMemValue(0xfffec004,4), 0xCFBCFFFF)
        self.assertEqual(self.emu.readMemValue(0xfffec010,4), 0x01FFFFFF)
        self.assertEqual(self.emu.readMemValue(0xfffec014,4), 0xFF444534)
        self.assertEqual(self.emu.readMemValue(0xfffec018,4), 0x33383837)
        self.assertEqual(self.emu.readMemValue(0xfffec01c,4), 0x11011014)

    def test_undefined_offsets(self):
        # Verify a few memory addresses which are not defined in the SIM
        # peripheral properly generate errors when they are read from

        self.validate_invalid_read(0xFFFEC008, 4)
        self.validate_invalid_read(0xFFFEC00C, 4)
        self.validate_invalid_read(0xFFFEC020, 4)
        self.validate_invalid_read(0xFFFEC024, 4)

    def test_attempt_write(self):
        self.emu.writeMemValue(0xfffec000, 0x12345678, 4)
        self.emu.writeMemValue(0xfffec004, 0x12345678, 4)
        self.emu.writeMemValue(0xfffec010, 0x12345678, 4)
        self.emu.writeMemValue(0xfffec014, 0x12345678, 4)
        self.emu.writeMemValue(0xfffec018, 0x12345678, 4)
        self.emu.writeMemValue(0xfffec01c, 0x12345678, 4)

        self.assertEqual(self.emu.readMemValue(0xfffec000,4), 0x9F03171C)
        self.assertEqual(self.emu.readMemValue(0xfffec004,4), 0xCFBCFFFF)
        self.assertEqual(self.emu.readMemValue(0xfffec010,4), 0x01FFFFFF)
        self.assertEqual(self.emu.readMemValue(0xfffec014,4), 0xFF444534)
        self.assertEqual(self.emu.readMemValue(0xfffec018,4), 0x33383837)
        self.assertEqual(self.emu.readMemValue(0xfffec01c,4), 0x11011014)
