import os
import enum
import hashlib
import os.path

import envi
import envi.bits as e_bits
import envi.memory as e_mem

from .. import mmio, e200z7
from ..ppc_vstructs import *
from ..intc_exc import MceDataReadBusError, MceWriteBusError

import logging
logger = logging.getLogger(__name__)


__all__ = [
    'FlashShadowParam',
    'FlashDevice',
    'FLASH',
    'getFlashOffsets',
]

SERIAL_PASSCODE_UPPER_ADDR          = 0x0FFFDD8
FLASH_SERIAL_PASSCODE_LOWER_ADDR    = 0x0FFFDDC
FLASH_CENSORSHIP_CONTROL_ADDR       = 0x0FFFDE0
FLASH_SERIAL_BOOT_CONTROL_ADDR      = 0x0FFFDE2

# Shadow Flash B Configuration value offsets
FLASH_B_LMLR_DEFAULT_OFFSET         = 0x1DE8
FLASH_B_HLR_DEFAULT_OFFSET          = 0x1DF0
FLASH_B_SLMLR_DEFAULT_OFFSET        = 0x1DF8

# Shadow Flash A Configuration value offsets
FLASH_SERIAL_PASSCODE_OFFSET        = 0x3DD8
FLASH_SERIAL_PASSCODE_OFFSET_LOWER  = 0x3DDC
FLASH_CENSORSHIP_CONTROL_OFFSET     = 0x3DE0
FLASH_SERIAL_BOOT_CONTROL_OFFSET    = 0x3DE2
FLASH_A_LMLR_DEFAULT_OFFSET         = 0x3DE8
FLASH_A_HLR_DEFAULT_OFFSET          = 0x3DF0
FLASH_A_SLMLR_DEFAULT_OFFSET        = 0x3DF8
FLASH_A_BIUCR2_DEFAULT_OFFSET       = 0x3E00


# Configuration values stored in shadow flash that SIU needs to access.
# These values are offsets into the shadow flash A region and the size of the
# value being retrieved.
class FlashShadowParam(enum.Enum):
    SERIAL_PASSCODE                 = (FLASH_SERIAL_PASSCODE_OFFSET, 8)
    SERIAL_PASSCODE_UPPER           = (FLASH_SERIAL_PASSCODE_OFFSET, 4)
    SERIAL_PASSCODE_LOWER           = (FLASH_SERIAL_PASSCODE_OFFSET_LOWER, 4)
    CENSORSHIP_CONTROL              = (FLASH_CENSORSHIP_CONTROL_OFFSET, 2)
    SERIAL_BOOT_CONTROL             = (FLASH_SERIAL_BOOT_CONTROL_OFFSET, 2)

    # the Censorship Control and Serial Boot Control values are often referred
    # to together in the documentation as the "Censorship Control Word"
    CENSORSHIP_CONTROL_WORD         = (FLASH_CENSORSHIP_CONTROL_OFFSET, 4)


# Common mask and shift values for flash config shadow/low/mid/high lock and
# selection bits
FLASH_LOCK_SHADOW_MASK              = 0x00100000
FLASH_LOCK_SHADOW_SHIFT             = 20
FLASH_LOCK_LOW_MASK                 = 0x000003FF
FLASH_LOCK_LOW_SHIFT                = 0
FLASH_LOCK_MID_MASK                 = 0x00030000
FLASH_LOCK_MID_SHIFT                = 16
FLASH_LOCK_HIGH_MASK                = 0x0000003F
FLASH_LOCK_HIGH_SHIFT               = 0

class FlashBlockType(enum.IntEnum):
    SHADOW = 0
    LOW = 1
    MID = 2
    HIGH = 3

class FlashBlock(enum.Enum):
    # block_type, block_num, block_mask
    #
    # Unlike the rest of PPC the block bits are ordered from high:low. So L0
    # would be the least significant bit of the LMSR[LSEL] field.
    S0 = (FlashBlockType.SHADOW, 0, None)
    L0 = (FlashBlockType.LOW,    0, 0x001)
    L1 = (FlashBlockType.LOW,    1, 0x002)
    L2 = (FlashBlockType.LOW,    2, 0x004)
    L3 = (FlashBlockType.LOW,    3, 0x008)
    L4 = (FlashBlockType.LOW,    4, 0x010)
    L5 = (FlashBlockType.LOW,    5, 0x020)
    L6 = (FlashBlockType.LOW,    6, 0x040)
    L7 = (FlashBlockType.LOW,    7, 0x080)
    L8 = (FlashBlockType.LOW,    8, 0x100)
    L9 = (FlashBlockType.LOW,    9, 0x200)
    M0 = (FlashBlockType.MID,    0, 0x001)
    M1 = (FlashBlockType.MID,    1, 0x002)
    H0 = (FlashBlockType.HIGH,   0, 0x001)
    H1 = (FlashBlockType.HIGH,   1, 0x002)
    H2 = (FlashBlockType.HIGH,   2, 0x004)
    H3 = (FlashBlockType.HIGH,   3, 0x008)
    H4 = (FlashBlockType.HIGH,   4, 0x010)
    H5 = (FlashBlockType.HIGH,   5, 0x020)

class FlashDevice(enum.IntEnum):
    FLASH_MAIN = 0
    FLASH_A_SHADOW = 1
    FLASH_B_SHADOW = 2
    FLASH_A_CONFIG = 3
    FLASH_B_CONFIG = 4

FLASH_DEVICE_MMIO_SIZE = {
    FlashDevice.FLASH_MAIN:     0x00400000,
    FlashDevice.FLASH_A_SHADOW: 0x00004000,
    FlashDevice.FLASH_B_SHADOW: 0x00004000,
    FlashDevice.FLASH_A_CONFIG: 0x00004000,
    FlashDevice.FLASH_B_CONFIG: 0x00004000,
}


# Utility
def getFlashOffsets(filename):
    """
    Determine if a supplied file is the right size to contain either just main
    flash or all of flash.

    Returns a dictionary of configuration values FLASH configuration values
    based on if the file specified contains enough data to have the shadow
    flash regions or not.
        fwFilename
        baseaddr
        shadowAFilename
        shadowAOffset
        shadowBFilename
        shadowBOffset

    If the supplied file doesn't exist or isn't the proper size None will be
    returned.
    """
    # Return an empty config indicating that a flash image is not going to be
    # loaded from any file.
    empty_config = {
        'fwFilename': None,
        'baseaddr': 0,
        'shadowAFilename': None,
        'shadowAOffset': 0,
        'shadowBFilename': None,
        'shadowBOffset': 0,
    }
    if not filename:
        return empty_config
    elif not os.path.exists(filename):
        logger.critical('%s does not exist, unable to load flash image', filename)
        return empty_config

    flash_size = FLASH_DEVICE_MMIO_SIZE[FlashDevice.FLASH_MAIN]
    flash_and_shadow_size = flash_size + \
            FLASH_DEVICE_MMIO_SIZE[FlashDevice.FLASH_A_SHADOW] + \
            FLASH_DEVICE_MMIO_SIZE[FlashDevice.FLASH_B_SHADOW]

    info = os.stat(filename)

    if info.st_size == flash_size:
        config = {
            'fwFilename': filename,
            'baseaddr': 0,
            'shadowAFilename': None,
            'shadowAOffset': 0,
            'shadowBFilename': None,
            'shadowBOffset': 0,
        }
        return config

    elif info.st_size == flash_and_shadow_size:
        # Shadow flash B comes first in the file
        shadow_b_offset = FLASH_DEVICE_MMIO_SIZE[FlashDevice.FLASH_MAIN]
        shadow_a_offset = shadow_b_offset + \
                FLASH_DEVICE_MMIO_SIZE[FlashDevice.FLASH_B_SHADOW]
        config = {
            'fwFilename': filename,
            'baseaddr': 0,
            'shadowAFilename': filename,
            'shadowAOffset': shadow_a_offset,
            'shadowBFilename': filename,
            'shadowBOffset': shadow_b_offset,
        }
        return config

    else:
        logger.critical('%s size (0x%x) does not match known valid flash image (0x%x or 0x%x), unable to load flash image', filename, info.st_size, flash_size, flash_and_shadow_size)
        return empty_config


class FLASH_MCR(PeriphRegister):
    def __init__(self, las, mas, bigend=True):
        PeriphRegister.__init__(self, bigend=bigend)
        self._pad0 = v_const(5)
        self.size = v_const(3, 0b101)
        self._pad1 = v_const(1)
        self.las = v_const(3, las)
        self._pad2 = v_const(3)
        self.mas = v_const(1, mas)
        self.eer = v_w1c(1)
        self.rwe = v_w1c(1)
        self.sbc = v_w1c(1)
        self._pad3 = v_const(1)
        self.peas = v_const(1, 0)
        self.done = v_const(1, 1)
        self.peg = v_const(1, 1)
        self._pad4 = v_const(4)
        self.pgm = v_bits(1)
        self.psus = v_bits(1)
        self.ers = v_bits(1)
        self.esus = v_bits(1)
        self.ehv = v_bits(1)

class FLASH_LMLR(PeriphRegister):
    def __init__(self, bigend=True):
        PeriphRegister.__init__(self, bigend=bigend)
        self.lme = v_const(1)
        self._pad0 = v_const(10)
        self.slock = v_bits(1)
        self._pad1 = v_const(2)
        self.mlock = v_bits(2)
        self._pad2 = v_const(6)
        self.llock = v_bits(10)

class FLASH_HLR(PeriphRegister):
    def __init__(self, bigend=True):
        PeriphRegister.__init__(self, bigend=bigend)
        self.hbe = v_const(1)
        self._pad0 = v_const(21)
        self.hlock = v_bits(10)

class FLASH_SLMLR(PeriphRegister):
    def __init__(self, bigend=True):
        PeriphRegister.__init__(self, bigend=bigend)
        self.sle = v_const(1)
        self._pad0 = v_const(10)
        self.sslock = v_bits(1)
        self._pad1 = v_const(2)
        self.smlock = v_bits(2)
        self._pad2 = v_const(6)
        self.sllock = v_bits(10)

class FLASH_LMSR(PeriphRegister):
    def __init__(self, bigend=True):
        PeriphRegister.__init__(self, bigend=bigend)
        self._pad0 = v_const(14)
        self.msel = v_bits(2)
        self._pad1 = v_const(6)
        self.lsel = v_bits(10)

class FLASH_HSR(PeriphRegister):
    def __init__(self, bigend=True):
        PeriphRegister.__init__(self, bigend=bigend)
        self._pad0 = v_const(26)
        self.hsel = v_bits(6)

class FLASH_AR(PeriphRegister):
    def __init__(self, bigend=True):
        PeriphRegister.__init__(self, bigend=bigend)
        self.sad = v_const(1)
        self._pad0 = v_const(13)
        self.addr = v_bits(15)
        self._pad1 = v_const(3)

class FLASH_BIUCR(PeriphRegister):
    def __init__(self, bigend=True):
        PeriphRegister.__init__(self, bigend=bigend)
        self._pad0 = v_const(7)
        self.m8pfe = v_bits(1)
        self._pad1 = v_const(1)
        self.m6pfe = v_bits(1)
        self.m5pfe = v_bits(1)
        self.m4pfe = v_bits(1)
        self._pad2 = v_const(3)
        self.m0pfe = v_bits(1)
        self.apc = v_bits(3, 0b111)
        self.wwsc = v_bits(2, 0b11)
        self.rwsc = v_bits(3, 0b111)
        self._pad3 = v_const(1)
        self.dpfen = v_bits(1)
        self._pad4 = v_const(1)
        self.ifpfen = v_bits(1)
        self._pad5 = v_const(1)
        self.pflim = v_bits(2)
        self.bfen = v_bits(1)

class FLASH_BIUAPR(PeriphRegister):
    def __init__(self, bigend=True):
        PeriphRegister.__init__(self, bigend=bigend)
        # The pad fields in this register aren't v_const because the
        # documentation seems to indicate that the values read may be 1 if
        # shadow flash has been erased
        #
        # The default values for the pad bits are set to 1 here because that is
        # what is shown in the documentation.  Even though this is the only
        # register in the flash controller that seems to be this way.  So I
        # suspect this is probably a documentation bug.
        self._pad0 = v_bits(14, 0x3FFF)
        self.m8ap = v_bits(2, 0b11)
        self._pad1 = v_bits(2, 0b11)
        self.m6ap = v_bits(2, 0b11)
        self.m5ap = v_bits(2, 0b11)
        self.m4ap = v_bits(2, 0b11)
        self._pad2 = v_bits(6, 0x3F)
        self.m0ap = v_bits(2, 0b11)

class FLASH_BIUCR2(PeriphRegister):
    def __init__(self, bigend=True):
        # The pad fields in this register aren't v_const because the
        # documentation seems to indicate that the values read may be 1 if
        # shadow flash has been erased
        PeriphRegister.__init__(self, bigend=bigend)
        self.lbcfg = v_bits(2)
        self._pad0 = v_bits(30)

class FLASH_UT0(PeriphRegister):
    def __init__(self, bigend=True):
        PeriphRegister.__init__(self, bigend=bigend)
        self.ute = v_bits(1)
        self.scbe = v_bits(1)
        self._pad0 = v_const(6)
        self.dsi = v_bits(8)
        self._pad1 = v_const(8)
        self.ea = v_bits(1, 1)
        self._pad2 = v_const(1)
        self.mre = v_bits(1)
        self.mrv = v_bits(1)
        self.eie = v_bits(1)
        self.ais = v_bits(1)
        self.aie = v_bits(1)
        self.aid = v_const(1, 1)

class FLASH_UT1(PeriphRegister):
    def __init__(self, bigend=True):
        PeriphRegister.__init__(self, bigend=bigend)
        self.dai = v_bits(32)

class FLASH_UT2(PeriphRegister):
    def __init__(self, bigend=True):
        PeriphRegister.__init__(self, bigend=bigend)
        self.dai = v_bits(32)


# Register array index constants
FLASH_MCR_REG_IDX   = 0x0000 // 4
FLASH_LMLR_REG_IDX  = 0x0004 // 4
FLASH_HLR_REG_IDX   = 0x0008 // 4
FLASH_SLMLR_REG_IDX = 0x000C // 4
LMSR_REG_IDX        = 0x0010 // 4
HSR_REG_IDX         = 0x0014 // 4
AR_REG_IDX          = 0x0018 // 4
BIUCR_REG_IDX       = 0x001C // 4
BIUAPR_REG_IDX      = 0x0020 // 4
BIUCR2_REG_IDX      = 0x0024 // 4
UT0_REG_IDX         = 0x003C // 4
UT1_REG_IDX         = 0x0040 // 4
UT2_REG_IDX         = 0x0044 // 4


def _genErasedBytes(size):
    return b'\xFF' * size

def _loadFromBlob(blob, offset, size):
    # If an offset is specified fill the initial part of the flash with
    # erased values
    if offset:
        data = _genErasedBytes(offset)
    else:
        data = bytes()

    # If the filename is larger than the flash for this part only read the
    # amount of data necessary
    readsize = size - offset
    data += blob[:readsize]

    # If the data does not fill the specified size fill the rest with erased
    # values
    if len(data) < size:
        fillsize = size - len(data)
        data += _genErasedBytes(fillsize)

    return data

def _loadFromFile(filename, offset, size):
    with open(filename, 'rb') as f:
        # If the filename is larger than the flash for this part only read
        # the amount of data necessary.
        f.seek(offset)
        data = f.read(size)
        return _loadFromBlob(data, 0, size)


class FlashArray:
    def __init__(self, flashdev, device, bigend=True):
        self.flashdev = flashdev
        self.device = device
        self.shadow = None

        # Block to device/offset/size mapping
        if device == FlashDevice.FLASH_A_CONFIG:
            self.name = 'A'
            self._block_map = {
                FlashBlock.L0: (FlashDevice.FLASH_MAIN,     0x00000000, 0x00004000),  # 16K
                FlashBlock.L1: (FlashDevice.FLASH_MAIN,     0x00004000, 0x00004000),  # 16K
                FlashBlock.L2: (FlashDevice.FLASH_MAIN,     0x00008000, 0x00004000),  # 16K
                FlashBlock.L3: (FlashDevice.FLASH_MAIN,     0x0000C000, 0x00004000),  # 16K
                FlashBlock.L4: (FlashDevice.FLASH_MAIN,     0x00010000, 0x00004000),  # 16K
                FlashBlock.L5: (FlashDevice.FLASH_MAIN,     0x00014000, 0x00004000),  # 16K
                FlashBlock.L6: (FlashDevice.FLASH_MAIN,     0x00018000, 0x00004000),  # 16K
                FlashBlock.L7: (FlashDevice.FLASH_MAIN,     0x0001C000, 0x00004000),  # 16K
                FlashBlock.L8: (FlashDevice.FLASH_MAIN,     0x00020000, 0x00010000),  # 64K
                FlashBlock.L9: (FlashDevice.FLASH_MAIN,     0x00030000, 0x00010000),  # 64K
                FlashBlock.M0: (FlashDevice.FLASH_MAIN,     0x00040000, 0x00020000),  # 128K
                FlashBlock.M1: (FlashDevice.FLASH_MAIN,     0x00060000, 0x00020000),  # 128K
                FlashBlock.S0: (FlashDevice.FLASH_A_SHADOW, 0x00000000, 0x00004000),  # 16K

                # For the high blocks, because they are interleaved the address
                # and sizes are exactly the same for each flash array and they
                # will be interleaved on write.
                FlashBlock.H0: (FlashDevice.FLASH_MAIN,     0x00100000, 0x00040000),  # 256K
                FlashBlock.H1: (FlashDevice.FLASH_MAIN,     0x00180000, 0x00040000),  # 256K
                FlashBlock.H2: (FlashDevice.FLASH_MAIN,     0x00200000, 0x00040000),  # 256K
                FlashBlock.H3: (FlashDevice.FLASH_MAIN,     0x00280000, 0x00040000),  # 256K
                FlashBlock.H4: (FlashDevice.FLASH_MAIN,     0x00300000, 0x00040000),  # 256K
                FlashBlock.H5: (FlashDevice.FLASH_MAIN,     0x00380000, 0x00040000),  # 256K
            }
        else:
            self.name = 'B'
            self._block_map = {
                FlashBlock.L0: (FlashDevice.FLASH_MAIN,     0x00080000, 0x00040000),  # 256K
                FlashBlock.M0: (FlashDevice.FLASH_MAIN,     0x000C0000, 0x00040000),  # 256K
                FlashBlock.S0: (FlashDevice.FLASH_B_SHADOW, 0x00000000, 0x00004000),  # 16K

                # For the high blocks, because they are interleaved the address
                # and sizes are exactly the same for each flash array and they
                # will be interleaved on write.
                FlashBlock.H0: (FlashDevice.FLASH_MAIN,     0x00100000, 0x00040000),  # 256K
                FlashBlock.H1: (FlashDevice.FLASH_MAIN,     0x00180000, 0x00040000),  # 256K
                FlashBlock.H2: (FlashDevice.FLASH_MAIN,     0x00200000, 0x00040000),  # 256K
                FlashBlock.H3: (FlashDevice.FLASH_MAIN,     0x00280000, 0x00040000),  # 256K
                FlashBlock.H4: (FlashDevice.FLASH_MAIN,     0x00300000, 0x00040000),  # 256K
                FlashBlock.H5: (FlashDevice.FLASH_MAIN,     0x00380000, 0x00040000),  # 256K
            }

        # Buffer to store data being written, and information about the data
        # being modified
        self._write_data = None

        if device == FlashDevice.FLASH_A_CONFIG:
            self.mcr = FLASH_MCR(las=0b100, mas=0b0)
        elif device == FlashDevice.FLASH_B_CONFIG:
            self.mcr = FLASH_MCR(las=0b000, mas=0b1)
        else:
            errmsg = 'Invalid %s device: %r' % (self.__class__.__name__, device)
            raise Exception(errmsg)

        self.lmlr = FLASH_LMLR(bigend=bigend)
        self.hlr = FLASH_HLR(bigend=bigend)
        self.slmlr = FLASH_SLMLR(bigend=bigend)
        self.lmsr = FLASH_LMSR(bigend=bigend)
        self.hsr = FLASH_HSR(bigend=bigend)
        self.ar = FLASH_AR(bigend=bigend)
        self.biucr = FLASH_BIUCR(bigend=bigend)
        self.biuapr = FLASH_BIUAPR(bigend=bigend)
        self.biucr2 = FLASH_BIUCR2(bigend=bigend)
        self.ut0 = FLASH_UT0(bigend=bigend)
        self.ut1 = FLASH_UT1(bigend=bigend)
        self.ut2 = FLASH_UT2(bigend=bigend)

        # TODO: At the moment all read/write operations are assumed to be coming
        # from the Z7 core (Bus Master ID 0), need to provide a method for other
        # bus masters (DMA A/B & FlexRay) to do reads/writes

        # TODO: Many of these flash control registers should not be writable
        # while certain operations are in progress, including UTest operations.
        # For now these restrictions are not in place, they may need to be
        # implemented eventually.
        self._read_registers = [
            self.mcr,               # 0x0000
            self.lmlr,              # 0x0004
            self.hlr,               # 0x0008
            self.slmlr,             # 0x000C
            self.lmsr,              # 0x0010
            self.hsr,               # 0x0014
            self.ar,                # 0x0018

            # TODO: Offsets 0x1C to 0248 are theoretically reserved on the B
            # array, but the CM2350 firmware does configure the BIUCR register
            # on the B array.  So possibly it isn't checked for anything or
            # doesn't control anything?
            #
            # Also possible that the NXP docs are wrong.  For now those
            # registers are defined for both the A and B flash array
            # controllers, but the B registers won't be used for anything. (they
            # aren't technically used for anything on the A array either yet)
            self.biucr,             # 0x001C
            self.biuapr,            # 0x0020
            self.biucr2,            # 0x0024

            # Offsets 0x28 to 0x38 are reserved
            None,                   # 0x0028
            None,                   # 0x002C
            None,                   # 0x0030
            None,                   # 0x0034
            None,                   # 0x0038
            self.ut0,               # 0x003C
            self.ut1,               # 0x0040
            self.ut2,               # 0x0044
        ]

        self._write_registers = [
            self.mcr,               # 0x0000
            self._lmlrWrite,        # 0x0004
            self._hlrWrite,         # 0x0008
            self._slmlrWrite,       # 0x000C
            self.lmsr,              # 0x0010
            self.hsr,               # 0x0014
            self._writePlaceholder, # 0x0018

            # Offsets 0x1C to 0248 are reserved on the B device
            # TODO: There is a line in
            # 11.2.1 Module Memory Map (MPC5674FRM.pdf  page 365) that states:
            #   "Flash bus configuration registers are common to both arrays."
            # It is unclear what this means.
            self.biucr,             # 0x001C
            self.biuapr,            # 0x0020
            self.biucr2,            # 0x0024

            # Offsets 0x28 to 0x38 are reserved
            None,                   # 0x0028
            None,                   # 0x002C
            None,                   # 0x0030
            None,                   # 0x0034
            None,                   # 0x0038
            self.ut0,               # 0x003C
            self.ut1,               # 0x0040
            self.ut2,               # 0x0044
        ]

        # TODO: Correctly handle bus master access protection changes (if
        # necessary)

        self.mcr.vsAddParseCallback('ehv', self._handleEHV)

    def load_defaults(self):
        # Return the contents of shadow flash to their default state
        if self.device == FlashDevice.FLASH_A_CONFIG:
            size = FLASH_DEVICE_MMIO_SIZE[FlashDevice.FLASH_A_SHADOW]
        else:
            size = FLASH_DEVICE_MMIO_SIZE[FlashDevice.FLASH_B_SHADOW]

        # We need to initialize shadow flash from scratch.
        self.shadow = bytearray(_genErasedBytes(size))

        # Also if this is is the "A" array there are some defaults that need
        # to be placed into shadow flash.
        if self.device == FlashDevice.FLASH_A_CONFIG:
            #
            # The different flash shadow regions have the following special
            # purpose values.  So if the flash is being initialized from scratch
            # we need to populate specific values at certain locations
            #
            # (from "Table 11-2. Shadow Block Memory Map" MPC5674FRM.pdf page
            # 367)
            #
            #     Address  | Block | Use
            #   -----------+-------+-----------
            #   0x00EFDDE8 |   B   | FLASH_B_LMLR reset value
            #   0x00EFDDF0 |   B   | FLASH_B_HLR reset value
            #   0x00EFDDE8 |   B   | FLASH_B_SLMLR reset value
            #   -----------+-------+-----------
            #   0x00FFFDD8 |   A   | Serial passcode (0xFEED_FACE_CAFE_BEEF)
            #   0x00FFFDE0 |   A   | Censorship control word (0x55AA_55AA)
            #   0x00FFFDE8 |   A   | FLASH_A_LMLR reset value (0x0010_0000)
            #   0x00FFFDF0 |   A   | FLASH_A_HLR reset value (0x0FFF_FFFF)
            #   0x00FFFDF8 |   A   | FLASH_A_SLMLR reset value (0x000F_FFFF)
            #   0x00FFFE00 |   A   | FLASH_BIUCR2 reset value (0xFFFF_FFFF)
            #
            # The documentation also seems to indicate that the BIUCR and BIUAPR
            # registers _should_ get their initial values from shadow flash, but
            # I have not identified any actual documentation that hints at the
            # address that would be used for such values.
            #
            # The default values specified in the table referenced above do not
            # line up with the default values for the following registers:
            #    - FLASH_x_LMLR
            #    - FLASH_x_HLR
            #    - FLASH_x_SLMLR
            #
            # The default values for those registers should be all 1's except
            # for the reserved bits and the register-specific "lock enable"
            # bits. The registers should automatically get those values based on
            # the PeriphRegister classes defined in this module if a value
            # of
            # 0xFFFFFFFF is provided during initialization.  For that reason no
            # additional default value is set here.
            #
            # These additional default values only need to be written to the
            # shadow flash for array A.
            if self.device == FlashDevice.FLASH_A_CONFIG:
                shadow_a_defaults = (
                    (FLASH_SERIAL_PASSCODE_OFFSET,     b'\xFE\xED\xFA\xCE\xCA\xFE\xBE\xEF'),
                    (FLASH_CENSORSHIP_CONTROL_OFFSET,  b'\x55\xAA'),
                    (FLASH_SERIAL_BOOT_CONTROL_OFFSET, b'\x55\xAA'),
                )
                for offset, value in shadow_a_defaults:
                    end = offset + len(value)
                    self.shadow[offset:end] = value

    def reset(self, emu):
        # To more closely manage the order of resetting registers to their
        # default values, and then initializing some of these registers from
        # shadow flash the flash array peripheral registers are reset here
        # instead of using the standard PeripheralRegister reset capability.
        self.lmlr.reset(emu)
        self.hlr.reset(emu)
        self.slmlr.reset(emu)
        self.lmsr.reset(emu)
        self.hsr.reset(emu)
        self.ar.reset(emu)
        self.biucr.reset(emu)
        self.biuapr.reset(emu)
        self.biucr2.reset(emu)
        self.ut0.reset(emu)
        self.ut1.reset(emu)
        self.ut2.reset(emu)

        # The A and B flash arrays have different configuration registers that
        # need to be configured from the shadow flash values on reset.  The
        # default values are set in the __init__ function if shadow flash is
        # generated from scratch.
        if self.device == FlashDevice.FLASH_A_CONFIG:
            offset = FLASH_A_LMLR_DEFAULT_OFFSET
            self.lmlr.vsParse(self.shadow[offset:offset+4])

            offset = FLASH_A_HLR_DEFAULT_OFFSET
            self.hlr.vsParse(self.shadow[offset:offset+4])

            offset = FLASH_A_SLMLR_DEFAULT_OFFSET
            self.slmlr.vsParse(self.shadow[offset:offset+4])

            offset = FLASH_A_BIUCR2_DEFAULT_OFFSET
            self.biucr2.vsParse(self.shadow[offset:offset+4])

        else:
            offset = FLASH_B_LMLR_DEFAULT_OFFSET
            self.lmlr.vsParse(self.shadow[offset:offset+4])

            offset = FLASH_B_HLR_DEFAULT_OFFSET
            self.hlr.vsParse(self.shadow[offset:offset+4])

            offset = FLASH_B_SLMLR_DEFAULT_OFFSET
            self.slmlr.vsParse(self.shadow[offset:offset+4])

    def _writePlaceholder(self, data):
        """
        This is a placeholder for writing to a register that should not
        generate an error but should not change any config register values.
        """
        pass

    def _lmlrWrite(self, data):
        # If the value being written is 0xA1A11111 set the LMLR[LME] bit
        if data == b'\xA1\xA1\x11\x11':
            self.lmlr.vsOverrideValue('lme', 1)
        elif self.lmlr.lme == 1:
            # If the LMLR[LME] bit is set then the lock fields can be modified
            self.lmlr.vsParse(data)

    def _hlrWrite(self, data):
        # If the value being written is 0xB2B22222 set the HLR[HBE] bit
        if data == b'\xB2\xB2\x22\x22':
            self.hlr.vsOverrideValue('hbe', 1)
        elif self.hlr.hbe == 1:
            # If the HLR[HBE] bit is set then the lock field can be modified
            self.hlr.vsParse(data)

    def _slmlrWrite(self, data):
        # If the value being written is 0xC3C33333 set the SLMLR[SLE] bit
        if data == b'\xC3\xC3\x33\x33':
            self.slmlr.vsOverrideValue('sle', 1)
        elif self.slmlr.sle == 1:
            # If the SLMLR[SLE] bit is set then the lock fields can be modified
            self.slmlr.vsParse(data)

    def _mmio_read(self, va, offset, size):

        reg_idx = offset//4
        try:
            vst = self._read_registers[reg_idx]
        except IndexError:
            # offset is out of range
            vst = None

        if isinstance(vst, VBitField):
            val = vst.vsEmit()

        elif isinstance(vst, bytes):
            # Some read registers return constant values
            val = vst

        elif callable(vst):
            val = e_bits.buildbytes(vst(), size, bigend=self.emu.getEndian())

        elif vst is None:
            state = {
                'va': va,
                'pc': self.emu.getProgramCounter(),
            }
            raise MceDataReadBusError(**state)

        else:
            # This shouldn't happen
            raise Exception('Invalid FLASH CONFIG register @ 0x%x: %r' % (va, vst))

        logger.debug("0x%x:  %s[%s] read [%x:%r] (%s)", self.flashdev.emu.getProgramCounter(), self.__class__.__name__, self.name, va, size, val.hex())
        return val

    def _mmio_write(self, va, offset, bytez):
        logger.debug("0x%x:  %s[%s] [%x] = %s", self.flashdev.emu.getProgramCounter(), self.__class__.__name__, self.name, va, bytez.hex())
        try:
            vst = self._write_registers[offset//4]
        except IndexError:
            # offset is out of range
            vst = None

        if isinstance(vst, VBitField):
            vst.vsParse(bytez)

        elif callable(vst):
            vst(bytez)

        elif vst is None:
            state = {
                'va': va,
                'data': bytez,
                'pc': self.emu.getProgramCounter(),
            }
            raise MceWriteBusError(**state)

        else:
            # This shouldn't happen
            raise Exception('Invalid FMPLL periph register @ 0x%x: %r' % (va, vst))

    def _handleEHV(self, thing):
        """
        Handle initiating erase or program operations
        """
        if self.mcr.ehv == 1:
            # Indicate programming is starting
            self.mcr.vsOverrideValue('done', 0)
            self.mcr.vsOverrideValue('peg', 0)

            if self.mcr.pgm:
                self.program()
            elif self.mcr.ers:
                self.erase()

            # Restore the MCR[PEAS,PGM,ERS] bits to their default values
            self.mcr.vsOverrideValue('peas', 0)
            self.mcr.vsOverrideValue('pgm', 0)
            self.mcr.vsOverrideValue('ers', 0)

            # Mark programming as complete
            self.mcr.vsOverrideValue('done', 1)
            self.mcr.vsOverrideValue('peg', 1)

            # Set MCR[EHV] back to 0
            self.mcr.vsOverrideValue('ehv', 0)

    def checkBlockWritable(self, block):
        block_type, _, block_mask = block.value

        if block_type == FlashBlockType.SHADOW:
            locked = bool((self.lmlr.slock | self.slmlr.sslock) & 1)
        elif block_type == FlashBlockType.LOW:
            locked = bool((self.lmlr.llock | self.slmlr.sllock) & block_mask)
        elif block_type == FlashBlockType.MID:
            locked = bool((self.lmlr.mlock | self.slmlr.smlock) & block_mask)
        elif block_type == FlashBlockType.HIGH:
            locked = bool(self.hlr.hlock & block_mask)

        return not locked

    def getSelectedBlocks(self):
        """
        Returns a list of blocks that are selected by the LMSR, HSR registers
        and MCR[PEAS] bit
        """
        selected = []
        for block in FlashBlock:
            # Unlike the rest of PPC the block bits are ordered from high:low.
            # So L0 would be the least significant bit of the LMSR[LSEL] field.
            block_type, _, block_mask = block.value

            # Flash array B does not have the same number of blocks as array A,
            # so only add a block as selected if it is valid for the current
            # array.
            #
            if (self._block_map.get(block) is not None) and \
                    ((block_type == FlashBlockType.LOW and self.lmsr.lsel & block_mask) or \
                    (block_type == FlashBlockType.MID and self.lmsr.msel & block_mask) or \
                    (block_type == FlashBlockType.HIGH and self.hsr.hsel & block_mask) or \
                    (block_type == FlashBlockType.SHADOW and self.mcr.peas)):
                selected.append(block)
        return selected

    def program(self):
        # If write_data is None then this array was never selected with the
        # "write interlock" so no program or erase will be done.
        if self._write_data is not None:
            # If programming: only one block can be written at a time
            block, data = self._write_data
            device, offset, size = self._block_map[block]

            # Ensure that the block has can be modified
            if self.checkBlockWritable(block):
                if block.value[0] == FlashBlockType.HIGH:
                    # high blocks are interleaved every 16 bytes. So and write
                    # the data in 16-byte chunks.
                    #
                    # TODO: It seems like there should be a better way
                    if self.device == FlashDevice.FLASH_B_CONFIG:
                        flash_offset = offset | 0x00000010
                    else:
                        flash_offset = offset

                    for i in range(0, len(data), 16):
                        start = flash_offset + i
                        self.flashdev.data[start:start+16] = data[i:i+16]
                        flash_offset += 16

                    self.flashdev.save(device, offset, size*2)
                else:
                    if device == FlashDevice.FLASH_MAIN:
                        self.flashdev.data[offset:offset+size] = data
                    else:
                        self.shadow[offset:offset+size] = data

                    self.flashdev.save(device, offset, size)

            else:
                # It isn't clear from the documentation what should happen if a
                # block wasn't selected?
                logger.error('[%s]%s flash write failed, block %s locked',
                        self.name, device.name, block.name)

            # Regardless of how well things went clear out the saved write
            # information
            self._write_data = None

    def erase(self):
        # If write_data is None then this array was never selected with the
        # "write interlock" so no program or erase will be done.
        if self._write_data is not None:
            # If erasing: multiple blocks can be erased at the same time
            # (indicated by the LMSR/HSR registers)
            for block in self.getSelectedBlocks():
                device, offset, size = self._block_map[block]

                # Ensure that the block has can be modified
                if self.checkBlockWritable(block):

                    if block.value[0] == FlashBlockType.HIGH:
                        # high blocks are interleaved every 16 bytes. So just
                        # erase every other 16-byte chunk.
                        #
                        # TODO: It seems like there should be a better way
                        erased_chunk = _genErasedBytes(16)

                        if self.device == FlashDevice.FLASH_B_CONFIG:
                            flash_offset = offset | 0x00000010
                        else:
                            flash_offset = offset

                        for i in range(0, size, 16):
                            start = flash_offset + i
                            self.flashdev.data[start:start+16] = erased_chunk
                            flash_offset += 16

                        self.flashdev.save(device, offset, size*2)
                    else:
                        if device == FlashDevice.FLASH_MAIN:
                            self.flashdev.data[offset:offset+size] = _genErasedBytes(size)
                        else:
                            self.shadow[offset:offset+size] = _genErasedBytes(size)

                        self.flashdev.save(device, offset, size)
                else:
                    # It isn't clear from the documentation what should happen if a
                    # block wasn't selected?
                    logger.error('[%s]%s flash erase failed, block %s locked',
                            self.name, device.name, block.name)

            # Regardless of how well things went clear out the saved write
            # information
            self._write_data = None

    def write(self, block, offset, bytez):
        # If this is the first write create the buffer holding the data to
        # be written
        size = self._block_map[block][2]
        if self._write_data is None:
            if self.mcr.pgm:
                # If this block is being programmed, save the initial data that
                # is being written.  If this block is being erased then the
                # write is just used to identify (confirm?) which block is being
                # modified and no data needs to be saved.
                self._write_data = (block, bytearray(_genErasedBytes(size)))

            elif self.mcr.ers:
                # If the shadow block is selected, set the MCR[PEAS] bit
                if block.value[0] == FlashBlockType.SHADOW:
                    self.mcr.vsOverrideValue('peas', 1)
                else:
                    self.mcr.vsOverrideValue('peas', 0)

                # This is an erase operation, don't bother generating erased
                # bytes now, they will be generated when the erase happens
                # for each selected block
                self._write_data = (block, None)

        if self.mcr.pgm:
            # If this block is being programmed, save the initial data that is
            # being written.  If this block is being erased then the write is
            # just used to identify (confirm?) which block is being modified and
            # no data needs to be saved.
            end = offset + size
            self._write_data[1][offset:end] = bytez

        # TODO: Should an exception be produced if write is attempted and not
        # enabled? From reading the documentation I think it should just
        # silently do nothing?


class FLASH(mmio.MMIO_DEVICE):
    """
    This is the FLASH Controller.

    Unlike other peripherals this one is staying an MMIO_DEVICE because of how
    weirdly the different memory regions need to work.
    """
    def __init__(self, emu, filename=None):
        emu.modules['FLASH'] = self

        # Empty flash for the moment
        self.data = None

        # No backup loaded yet either
        self._backup = None

        # Initialize the A and B flash arrays.  These objects handle both the
        # configuration registers and the shadow flash.
        self.A = FlashArray(self, FlashDevice.FLASH_A_CONFIG, bigend=emu.getEndian())
        self.B = FlashArray(self, FlashDevice.FLASH_B_CONFIG, bigend=emu.getEndian())

        # Flash memory for blocks A and B are distributed oddly
        # (from "Table 11-1. Memory Map" MPC5674FRM.pdf page 366):
        #
        #     Address  |  A |  B | Partition | A Sz | B Sz | Width
        #   -----------+----+----+-----------+------+------+------
        #   0x00000000 | L0 |    |     1     |  16K |      |  128
        #   0x00004000 | L1 |    |     1     |  16K |      |  128
        #   0x00008000 | L2 |    |     1     |  16K |      |  128
        #   0x0000C000 | L3 |    |     1     |  16K |      |  128
        #   0x00010000 | L4 |    |     2     |  16K |      |  128
        #   0x00014000 | L5 |    |     2     |  16K |      |  128
        #   0x00018000 | L6 |    |     2     |  16K |      |  128
        #   0x0001C000 | L7 |    |     2     |  16K |      |  128
        #   0x00020000 | L8 |    |     3     |  64K |      |  128
        #   0x00030000 | L9 |    |     3     |  64K |      |  128
        #   0x00040000 | M0 |    |     4     | 128K |      |  128
        #   0x00060000 | M1 |    |     4     | 128K |      |  128
        #   0x00080000 |    | L0 |     5     |      | 256K |  128
        #   0x000C0000 |    | M0 |     5     |      | 256K |  128
        #   0x00100000 | H0 | H0 |     6     | 256K | 256K |  256
        #   0x00180000 | H1 | H1 |     6     | 256K | 256K |  256
        #   0x00200000 | H2 | H2 |     7     | 256K | 256K |  256
        #   0x00280000 | H3 | H3 |     7     | 256K | 256K |  256
        #   0x00300000 | H4 | H4 |     8     | 256K | 256K |  256
        #   0x00380000 | H5 | H5 |     8     | 256K | 256K |  256
        #   0x00EFC000 |    | S0 |    all    |      |  16K |  128
        #   0x00FFC000 | S0 |    |    all    |  16K |      |  128
        #
        # TODO: The partition number is used to determine what flash sectors can
        # be read while an erase or program operation is in progress.  "RWW"
        # operations are not currently modeled, and most likely won't need to
        # be.

        # This block map identifies which flash part (A/B) a block belongs to,
        # whether it is part of the SHADOW/LOW/MID/HIGH block and which block
        # number it is.
        #
        # TODO: I don't like that the most (apparently) efficient way to
        # organize the block mapping is to have a list of block information here
        # and then specific block offset/size lookups in the array objects. It
        # seems like there should be a better way to organize this data.
        self.FLASH_BLOCK_MAP = (
            (0x00000000, 0x00004000, self.A, FlashBlock.L0),
            (0x00004000, 0x00008000, self.A, FlashBlock.L1),
            (0x00008000, 0x0000C000, self.A, FlashBlock.L2),
            (0x0000C000, 0x00010000, self.A, FlashBlock.L3),
            (0x00010000, 0x00014000, self.A, FlashBlock.L4),
            (0x00014000, 0x00018000, self.A, FlashBlock.L5),
            (0x00018000, 0x0001C000, self.A, FlashBlock.L6),
            (0x0001C000, 0x00020000, self.A, FlashBlock.L7),
            (0x00020000, 0x00030000, self.A, FlashBlock.L8),
            (0x00030000, 0x00040000, self.A, FlashBlock.L9),
            (0x00040000, 0x00060000, self.A, FlashBlock.M0),
            (0x00060000, 0x00080000, self.A, FlashBlock.M1),
            (0x00080000, 0x000C0000, self.B, FlashBlock.L0),
            (0x000C0000, 0x00100000, self.B, FlashBlock.M0),

            # Some flash regions are made up of 1 block from both the A and
            # B arrays interleaved every 16 bytes for increased speed. There is
            # no good way to do this but to properly emulate the way the real
            # thing works it is necessary to alternate which array is handling
            # the writes.
            #
            # So this list specifies "None" as the array for these blocks
            # because additional logic is necessary to correctly identify the
            # array and offset.
            (0x00100000, 0x00180000,   None, FlashBlock.H0),
            (0x00180000, 0x00200000,   None, FlashBlock.H1),
            (0x00200000, 0x00280000,   None, FlashBlock.H2),
            (0x00280000, 0x00300000,   None, FlashBlock.H3),
            (0x00300000, 0x00380000,   None, FlashBlock.H4),
            (0x00380000, 0x00400000,   None, FlashBlock.H5),
        )

    def __del__(self):
        # Gracefully close the backup file
        if self._backup:
            self._backup.close()

    def init(self, emu):
        logger.debug('init: FLASH module')
        self.emu = emu

        self.reset(emu)

    def reset(self, emu):
        # Some flash control registers get their initial values from shadow
        # flash
        self.A.reset(emu)
        self.B.reset(emu)

    def readShadowValue(self, param):
        """
        Utility function to make it easier for other peripherals to read
        configuration parameters from shadow flash. Supported parameters are
        defined by the FlashShadowParam type.
        """
        # TODO: Integrate this into the SIU peripheral
        offset, size = param.value
        # All non-flash parameters are located in the A array shadow flash block
        return e_bits.parsebytes(self.A.shadow, offset, size, bigend=self.emu.getEndian())

    def setAddr(self, emu, device, mmio_addr):
        if device == FlashDevice.FLASH_MAIN:
            args = {
                'va': mmio_addr,
                'msize': FLASH_DEVICE_MMIO_SIZE[device],
                'fname': device.name,
                'mmio_read': self._flash_read,
                'mmio_write': self._flash_write,
                'mmio_bytes': self._flash_bytes,
                'mmio_perm': e_mem.MM_RWX,
            }

        elif device == FlashDevice.FLASH_A_SHADOW:
            args = {
                'va': mmio_addr,
                'msize': FLASH_DEVICE_MMIO_SIZE[device],
                'fname': device.name,
                'mmio_read': self._shadow_A_read,
                'mmio_write': self._shadow_A_write,
                'mmio_bytes': self._shadow_A_bytes,
                'mmio_perm': e_mem.MM_RWX,
            }

        elif device == FlashDevice.FLASH_B_SHADOW:
            args = {
                'va': mmio_addr,
                'msize': FLASH_DEVICE_MMIO_SIZE[device],
                'fname': device.name,
                'mmio_read': self._shadow_B_read,
                'mmio_write': self._shadow_B_write,
                'mmio_bytes': self._shadow_B_bytes,
                'mmio_perm': e_mem.MM_RWX,
            }

        elif device == FlashDevice.FLASH_A_CONFIG:
            args = {
                'va': mmio_addr,
                'msize': FLASH_DEVICE_MMIO_SIZE[device],
                'fname': device.name,
                'mmio_read': self.A._mmio_read,
                'mmio_write': self.A._mmio_write,
            }

        elif device == FlashDevice.FLASH_B_CONFIG:
            args = {
                'va': mmio_addr,
                'msize': FLASH_DEVICE_MMIO_SIZE[device],
                'fname': device.name,
                'mmio_read': self.B._mmio_read,
                'mmio_write': self.B._mmio_write,
            }

        emu.addMMIO(**args)

    def load(self, device, filename, offset):
        size = FLASH_DEVICE_MMIO_SIZE[device]

        if isinstance(filename, (bytes, bytearray)):
            # If the filename param is a bytes object assume this is a blob that
            # should be loaded rather than a file that should be opened.
            data = filename

            if device == FlashDevice.FLASH_MAIN:
                self.data = bytearray(_loadFromBlob(data, offset, size))
            elif device == FlashDevice.FLASH_A_SHADOW:
                self.A.shadow = bytearray(_loadFromBlob(data, offset, size))
            elif device == FlashDevice.FLASH_B_SHADOW:
                self.B.shadow = bytearray(_loadFromBlob(data, offset, size))
            else:
                raise Exception('Cannot initialize %s from blob' % device.name)

        elif os.path.exists(filename):
            logger.debug('Loading %s from %s @ 0x%x to 0x%x', device.name, filename, offset, offset + size)
            if device == FlashDevice.FLASH_MAIN:
                self.data = bytearray(_loadFromFile(filename, offset, size))
            elif device == FlashDevice.FLASH_A_SHADOW:
                self.A.shadow = bytearray(_loadFromFile(filename, offset, size))
            elif device == FlashDevice.FLASH_B_SHADOW:
                self.B.shadow = bytearray(_loadFromFile(filename, offset, size))
            else:
                raise Exception('Cannot initialize %s from file' % device.name)

        else:
            raise Exception('Cannot initialize %s from %r' % (device.name, filename))

        self.save(device)

    def get_hash(self):
        flash_hash = hashlib.md5()
        flash_hash.update(self.data)

        # Since the primary flash is defined, add in the shadow flash contents
        # if they have been loaded. Make sure to add shadow flash B contents
        # first.
        if self.B.shadow is not None:
            flash_hash.update(self.B.shadow)
        if self.A.shadow is not None:
            flash_hash.update(self.A.shadow)

        return flash_hash.digest()

    def load_complete(self, backup_filename=None):
        """
        This function indicates to the flash peripheral that all initial
        contents of flash have been loaded.

        The following checks are performed:
            - A hash of the initial state of all flash devices is created if at
              least the main flash has been loaded
            - If a backup filename is defined and there exists a backup file
              that matches the hash calculated in the previous step (if one was
              calculated) then all flash devices are (re)loaded from the backup
            - If any flash device has not been loaded yet then a default state
              is created for that device
        """
        flash_size = FLASH_DEVICE_MMIO_SIZE[FlashDevice.FLASH_MAIN]
        shadow_A_size = FLASH_DEVICE_MMIO_SIZE[FlashDevice.FLASH_A_SHADOW]
        shadow_B_size = FLASH_DEVICE_MMIO_SIZE[FlashDevice.FLASH_B_SHADOW]

        # Start with the assumption that a backup needs to be created
        backup_valid = False

        # The loaded/not loaded state of main flash is used to identify if a
        # backup file should be opened or restored from, but before
        # self.get_hash() returns a valid value the shadow flash must be
        # initalized
        if self.B.shadow is None:
            logger.debug('Generating default %s', FlashDevice.FLASH_B_SHADOW)
            self.B.load_defaults()
        if self.A.shadow is None:
            logger.debug('Generating default %s', FlashDevice.FLASH_A_SHADOW)
            self.A.load_defaults()

        if self.data is not None:
            # If a backup filename was provided see if a backup file exists that
            # matches the hash digest that was created
            if backup_filename is not None:
                filename = backup_filename + '.' + self.get_hash().hex()
                if os.path.exists(filename):
                    logger.debug('Opening flash backup file %s', filename)
                    # use 'r+b' mode with open to avoid truncating the backup
                    # file
                    self._backup = open(filename, 'r+b')

                    # Now attempt to restore the contents of flash from the
                    # backup file we don't use the _loadFrom???() helper
                    # functions here because if the backup file doesn't have the
                    # correct size then the backup file is considered to not
                    # have valid data for that section.
                    #
                    # Shadow flash B is first in the backup file
                    flash_data = self._backup.read(flash_size)
                    logger.debug('Restoring %s from backup file %s @ 0x%x to 0x%x', FlashDevice.FLASH_MAIN, filename, self._backup.tell(), self._backup.tell() + flash_size)
                    shadow_b_data = self._backup.read(shadow_B_size)
                    logger.debug('Restoring %s from backup file %s @ 0x%x to 0x%x', FlashDevice.FLASH_B_SHADOW, filename, self._backup.tell(), self._backup.tell() + shadow_B_size)
                    shadow_a_data = self._backup.read(shadow_A_size)
                    logger.debug('Restoring %s from backup file %s @ 0x%x to 0x%x', FlashDevice.FLASH_A_SHADOW, filename, self._backup.tell(), self._backup.tell() + shadow_A_size)

                    if len(flash_data) == flash_size and \
                            len(shadow_b_data) == shadow_B_size and \
                            len(shadow_a_data) == shadow_A_size:
                        backup_valid = True

                        self.data = bytearray(flash_data)
                        self.B.shadow = bytearray(shadow_b_data)
                        self.A.shadow = bytearray(shadow_a_data)

                        logger.info('flash restored from backup %r', filename)
                else:
                    # Create the backup file
                    self._backup = open(filename, 'w+b')

        else:
            # If the main flash has not been initialized yet, initialize it now
            # to the default (erased) state
            logger.debug('Generating default %s', FlashDevice.FLASH_MAIN)
            self.data = bytearray(_genErasedBytes(flash_size))

        # If the backup has not been detected as valid, save a copy of the state
        # of flash now.
        if backup_valid != True:
            self.save(FlashDevice.FLASH_MAIN)
            self.save(FlashDevice.FLASH_B_SHADOW)
            self.save(FlashDevice.FLASH_A_SHADOW)

    def save(self, device, start=0, size=None):
        if size is None:
            size = FLASH_DEVICE_MMIO_SIZE[device]

        # The shadow flash regions are saved to the same backup file as the main
        # flash, and shadow flash B is saved first mimicking the order they are
        # found on the real device.
        if self._backup is not None:
            logger.debug('Saving %s[0x%08x:0x%08x]', device.name, start, start + size)

            if device == FlashDevice.FLASH_MAIN:
                file_offset = start
                data = self.data

            elif device == FlashDevice.FLASH_B_SHADOW:
                file_offset = FLASH_DEVICE_MMIO_SIZE[FlashDevice.FLASH_MAIN] + start
                data = self.B.shadow

            elif device == FlashDevice.FLASH_A_SHADOW:
                file_offset = FLASH_DEVICE_MMIO_SIZE[FlashDevice.FLASH_MAIN] + \
                        FLASH_DEVICE_MMIO_SIZE[FlashDevice.FLASH_B_SHADOW] + start
                data = self.A.shadow

            else:
                raise Exception('Cannot save backup of %s' % device.name)

            self._backup.seek(file_offset)
            self._backup.write(data[start:start+size])
            self._backup.flush()

    def _getArrayBlockOffset(self, offset):
        """
        Returns the array, block and offset for a particular address.

        According to
        "11.3.3 Read While Write (RWW)" of MPC57674FRM.pdf, page 389

          "For each Flash array, the high address space of each RWW partition is
          physically comprised of two 256K blocks as shown in Figure 11-1.  However,
          because the high address space blocks are interleaved every 16 bytes between
          Flash array A and Flash array B, the practical size of the high address
          space RWW partitions is effectively four 256K blocks."

        To achieve accurate emulation each array expects the offsets to go from 0 to
        (block size // 2).  And the data will be interleaved every 16 bytes when the
        cached block is written back to main flash.  Array A is first (bytes 0-15)
        array B is second (bytes 16-31).

        Because writes in PowerPC must be aligned by the size of the write,
        and there are no instructions to write values larger than 16 bytes
        interleaving values does not have to be handled during write.
        """
        for start, end, array, block in self.FLASH_BLOCK_MAP:
            if offset >= start and offset < end:
                # Get an offset from the start of the block to the desired
                # location
                new_offset = offset - start

                if array is not None:
                    return (array, block, new_offset)
                else:
                    # Figure out the offset for the array to use internally for
                    # this write
                    chunk_idx = new_offset // 32
                    array_offset = (chunk_idx * 16) + (new_offset % 16)

                    # If the array is None it means this is one of the blocks
                    # that is shared between the A and B arrays.
                    # Check if bit 4 is set in the offset to see which array to
                    # write the data to.
                    if new_offset & 0x00000010:
                        return (self.B, block, array_offset)
                    else:
                        return (self.A, block, array_offset)

        raise envi.SegmentationViolation(va)

    ##########################################
    # 0x00000000 - 0x00400000  Main Flash
    ##########################################

    def _flash_read(self, va, offset, size):
        value = self.data[offset:offset+size]
        #logger.debug("0x%x:  FLASH read [%x:%r] (%s)", self.emu.getProgramCounter(), offset, size, value.hex())
        return value

    def _flash_write(self, va, offset, bytez):
        logger.debug("0x%x:  FLASH write [%x] = %s", self.emu.getProgramCounter(), va, bytez.hex())
        # The array corresponding to the block being modified must be identified
        # because the writes are cached by the sub-array until the MCR[EHV] bit
        # is written which causes the cached data to be written to the flash
        # bytearray stored in this class.
        array, block, offset = self._getArrayBlockOffset(va)
        array.write(block, offset, bytez)

    def _flash_bytes(self):
        return self.data

    ##########################################
    # 0x00FFC000 - 0x01000000  Shadow A Flash
    ##########################################

    def _shadow_A_read(self, va, offset, size):
        value = self.A.shadow[offset:offset+size]
        logger.debug("0x%x:  ShadowFlash[A] read [%x:%r] (%s)", self.emu.getProgramCounter(), va, size, value.hex())
        return value

    def _shadow_A_write(self, va, offset, bytez):
        logger.debug("0x%x:  ShadowFlash[A] write [%x] = %s", self.emu.getProgramCounter(), va, bytez.hex())
        self.A.write(FlashBlock.S0, offset, bytez)

    def _shadow_A_bytes(self):
        return self.A.shadow

    ##########################################
    # 0x00EFC000 - 0x00FF0000  Shadow B Flash
    ##########################################

    def _shadow_B_read(self, va, offset, size):
        value = self.B.shadow[offset:offset+size]
        logger.debug("0x%x:  ShadowFlash[B] read [%x:%r] (%s)", self.emu.getProgramCounter(), va, size, value.hex())
        return value

    def _shadow_B_write(self, va, offset, bytez):
        logger.debug("0x%x:  ShadowFlash[B] write [%x] = %s", self.emu.getProgramCounter(), va, bytez.hex())
        self.B.write(FlashBlock.S0, offset, bytez)

    def _shadow_B_bytes(self):
        return self.B.shadow

    ##########################################
    # envi.MemoryObject-like utility functions
    #
    # This allows peripherals direct access to flash when the MMU/TLB is
    # uninitialized (MMU/TLB is technically only used for addresses referenced
    # from assembly)
    ##########################################

    def readMemory(self, addr, size):
        if addr + size <= len(self.data):
            return self.data[addr:addr+size]
        else:
            raise envi.SegmentationViolation(addr)

    def readMemValue(self, addr, size):
        return e_bits.parsebytes(self.readMemory(addr, size), 0, size, False, self.emu.getEndian())

    def writeMemory(self, addr, data):
        if addr + len(data) <= len(self.data):
            self.data[addr:addr+size] = data
        else:
            raise envi.SegmentationViolation(addr)

    def writeMemValue(self, addr, value, size):
        self.writeMemory(addr, e_bits.buildbytes(value, size, self.emu.getEndian()))
