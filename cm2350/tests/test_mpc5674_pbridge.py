from .helpers import MPC5674_Test


PBRIDGE_DEVICES = (
    ('PBRIDGE_A', 0XC3F00000),
    ('PBRIDGE_B', 0XFFF00000),
)


PBRIDGE_x_MPCR_OFFSET         = 0x0000

# PBRIDGE_A has only 1 PACR register, PBRIDGE_B has 3
PBRIDGE_x_PACRn_RANGE = (
    range(0x0020, 0x0024, 4),
    range(0x0020, 0x002C, 4),
)

# Both PBRIDGE controllers have the same number of OPACR registers
PBRIDGE_x_OPACRn_RANGE = (
    range(0x0040, 0x0050, 4),
    range(0x0040, 0x0050, 4),
)

PBRIDGE_x_MPCR_DEFAULT_VALUE  = 0x77777777
PBRIDGE_x_MPCR_DEFAULT        = b'\x77\x77\x77\x77'
PBRIDGE_x_PACR_DEFAULT_VALUE  = 0x44444444
PBRIDGE_x_PACR_DEFAULT        = b'\x44\x44\x44\x44'
PBRIDGE_x_OPACR_DEFAULT_VALUE = 0x44444444
PBRIDGE_x_OPACR_DEFAULT       = b'\x44\x44\x44\x44'


class MPC5674_PBRIDGE_Test(MPC5674_Test):

    ##################################################
    # Tests
    ##################################################

    def test_pbridge(self):
        for idx, (devname, baseaddr) in enumerate(PBRIDGE_DEVICES):
            self.assertEqual(self.emu.pbridge[idx].devname, devname)

            addr = baseaddr + PBRIDGE_x_MPCR_OFFSET
            self.assertEqual(self.emu.readMemValue(addr,4), PBRIDGE_x_MPCR_DEFAULT_VALUE, msg=devname)
            self.assertEqual(self.emu.readMemory(addr,4), PBRIDGE_x_MPCR_DEFAULT, msg=devname)

            for pacr_offset in PBRIDGE_x_PACRn_RANGE[idx]:
                msg = '%s PACR%d' % (devname, idx)
                addr = baseaddr + pacr_offset
                self.assertEqual(self.emu.readMemValue(addr,4), PBRIDGE_x_PACR_DEFAULT_VALUE, msg=msg)
                self.assertEqual(self.emu.readMemory(addr,4), PBRIDGE_x_PACR_DEFAULT, msg=msg)

            for opacr_offset in PBRIDGE_x_OPACRn_RANGE[idx]:
                msg = '%s OPACR%d' % (devname, idx)
                addr = baseaddr + opacr_offset
                self.assertEqual(self.emu.readMemValue(addr,4), PBRIDGE_x_OPACR_DEFAULT_VALUE, msg=msg)
                self.assertEqual(self.emu.readMemory(addr,4), PBRIDGE_x_OPACR_DEFAULT, msg=msg)
