import enum

from ..ppc_vstructs import *
from ..ppc_peripherals import *
from ..ppc_xbar import *

__all__  = [
    'PBRIDGE',
]


PBRIDGE_MPCR_OFFSET   = 0x0000
PBRIDGE_PACR0_OFFSET  = 0x0020
PBRIDGE_PACR1_OFFSET  = 0x0024
PBRIDGE_PACR2_OFFSET  = 0x0028
PBRIDGE_OPACR0_OFFSET = 0x0040
PBRIDGE_OPACR1_OFFSET = 0x0044
PBRIDGE_OPACR2_OFFSET = 0x0048
PBRIDGE_OPACR3_OFFSET = 0x004C


class PBRIDGE_x_MPCR(PeriphRegister):
    def __init__(self):
        super().__init__()

        # Each 4-bit field indicates:
        #   mbw: master buffer writes
        #   mtr: master trusted for reads
        #   mtw: master trusted for writes
        #   mpl: master privilege level (0 = force user, 1 = not forced)

        self.mb0    = v_bits(4, 0b0111)
        self.mb1    = v_bits(4, 0b0111)

        # masters 2 and 3 are fixed
        self.mb2    = v_const(4, 0b0111)
        self.mb3    = v_const(4, 0b0111)

        self.mb4    = v_bits(4, 0b0111)
        self.mb5    = v_bits(4, 0b0111)
        self.mb6    = v_bits(4, 0b0111)

        # master 7 is fixed
        self.mb7    = v_const(4, 0b0111)


class PBRIDGE_x_PACRn(PeriphRegister):
    def __init__(self):
        super().__init__()

        # Each 4-bit field indicates
        #   bw: peripheral writes are allowed to be buffered
        #   sp: peripheral requires supervisor level for access (1 = required)
        #   wp: peripheral allows write (1 = write protected)
        #   tp: peripheral allows writes from untrusted masters (1 = not
        #       allowed)

        self.p0    = v_bits(4, 0b0100)
        self.p1    = v_bits(4, 0b0100)
        self.p2    = v_bits(4, 0b0100)
        self.p3    = v_bits(4, 0b0100)
        self.p4    = v_bits(4, 0b0100)
        self.p5    = v_bits(4, 0b0100)
        self.p6    = v_bits(4, 0b0100)
        self.p7    = v_bits(4, 0b0100)


class PBRIDGE_A_REGISTERS(PeripheralRegisterSet):
    def __init__(self):
        super().__init__()
        self.mpcr   = (PBRIDGE_MPCR_OFFSET,   PBRIDGE_x_MPCR())
        self.pacr0  = (PBRIDGE_PACR0_OFFSET,  PBRIDGE_x_PACRn())
        self.pacr1  = None
        self.pacr2  = None
        self.opacr0 = (PBRIDGE_OPACR0_OFFSET, PBRIDGE_x_PACRn())
        self.opacr1 = (PBRIDGE_OPACR1_OFFSET, PBRIDGE_x_PACRn())
        self.opacr2 = (PBRIDGE_OPACR2_OFFSET, PBRIDGE_x_PACRn())
        self.opacr3 = (PBRIDGE_OPACR3_OFFSET, PBRIDGE_x_PACRn())


class PBRIDGE_B_REGISTERS(PeripheralRegisterSet):
    def __init__(self):
        super().__init__()
        self.mpcr   = (PBRIDGE_MPCR_OFFSET,   PBRIDGE_x_MPCR())
        self.pacr0  = (PBRIDGE_PACR0_OFFSET,  PBRIDGE_x_PACRn())
        self.pacr1  = (PBRIDGE_PACR1_OFFSET,  PBRIDGE_x_PACRn())
        self.pacr2  = (PBRIDGE_PACR2_OFFSET,  PBRIDGE_x_PACRn())
        self.opacr0 = (PBRIDGE_OPACR0_OFFSET, PBRIDGE_x_PACRn())
        self.opacr1 = (PBRIDGE_OPACR1_OFFSET, PBRIDGE_x_PACRn())
        self.opacr2 = (PBRIDGE_OPACR2_OFFSET, PBRIDGE_x_PACRn())
        self.opacr3 = (PBRIDGE_OPACR3_OFFSET, PBRIDGE_x_PACRn())


# Mapping of PACR/OPACR registers and peripherals (from "Table 14-6. PACR and
# OPACR Access Control Registers and Peripheral Mapping" in MPC5674FRM.pdf page
# 462):
#
#      REGISTER[FIELD]  | Peripheral
#   ====================+============
#   PBRIDGE_A_PACR0[0]  |  PBRIDGE_A
#   ====================+============
#   PBRIDGE_A_OPACR0[0] |  FMPLL
#   PBRIDGE_A_OPACR0[1] |  EBI
#   PBRIDGE_A_OPACR0[2] |  FLASH_A
#   PBRIDGE_A_OPACR0[3] |  FLASH_B
#   PBRIDGE_A_OPACR0[4] |  SIU
#   --------------------+------------
#   PBRIDGE_A_OPACR1[0] |  eMIOS
#   PBRIDGE_A_OPACR1[7] |  PMC
#   --------------------+------------
#   PBRIDGE_A_OPACR2[0] |  eTPU
#   PBRIDGE_A_OPACR2[2] |  eTPU PRAM
#   PBRIDGE_A_OPACR2[3] |  eTPU PRAM Monitor
#   PBRIDGE_A_OPACR2[2] |  eTPU SCM
#   --------------------+------------
#   PBRIDGE_A_OPACR3[4] |  PIT_RTI
#   ====================+============
#   PBRIDGE_B_PACR0[0]  |  PBRIDGE_B
#   PBRIDGE_B_PACR0[1]  |  XBAR
#   PBRIDGE_B_PACR0[4]  |  MPU
#   --------------------+------------
#   PBRIDGE_B_PACR1[6]  |  SWT
#   PBRIDGE_B_PACR1[7]  |  STM
#   --------------------+------------
#   PBRIDGE_B_PACR2[0]  |  ESCM
#   PBRIDGE_B_PACR2[1]  |  eDMA_A
#   PBRIDGE_B_PACR2[2]  |  INTC
#   PBRIDGE_B_PACR2[5]  |  eDMA_B
#   ====================+============
#   PBRIDGE_A_OPACR0[0] |  eQADC_A
#   PBRIDGE_A_OPACR0[1] |  eQADC_A
#   PBRIDGE_A_OPACR0[2] |  DECFILT_A-D
#   PBRIDGE_A_OPACR0[4] |  DSPI_A
#   PBRIDGE_A_OPACR0[5] |  DSPI_B
#   PBRIDGE_A_OPACR0[6] |  DSPI_C
#   PBRIDGE_A_OPACR0[7] |  DSPI_D
#   --------------------+------------
#   PBRIDGE_A_OPACR1[4] |  eSCI_A
#   PBRIDGE_A_OPACR1[4] |  eSCI_B
#   PBRIDGE_A_OPACR1[4] |  eSCI_C
#   --------------------+------------
#   PBRIDGE_A_OPACR2[0] |  FlexCAN_A
#   PBRIDGE_A_OPACR2[1] |  FlexCAN_B
#   PBRIDGE_A_OPACR2[2] |  FlexCAN_C
#   PBRIDGE_A_OPACR2[3] |  FlexCAN_D
#   --------------------+------------
#   PBRIDGE_A_OPACR3[0] |  FlexRAY
#   PBRIDGE_A_OPACR3[3] |  Temp Sensor
#   PBRIDGE_A_OPACR3[7] |  BAM
#   --------------------+------------
#
# Notably, Decimation Filters E through H are missing from this table


class PBRIDGE(MMIOPeripheral):
    '''
    This is the Peripheral Bridge control register module
    '''
    def __init__(self, devname, emu, mmio_addr):
        if devname == 'PBRIDGE_A':
            super().__init__(emu, devname, mmio_addr, 0x4000, regsetcls=PBRIDGE_A_REGISTERS)
        else:
            super().__init__(emu, devname, mmio_addr, 0x4000, regsetcls=PBRIDGE_B_REGISTERS)
