import os
import struct
import itertools

import envi.bits as e_bits

from cm2350 import intc_exc, mmio

from .helpers import MPC5674_Test


# The SIU memory range is confusing, there are sub ranges with different valid
# memory access sizes, and within those regions some "invalid" addresses which
# are read-only (so they should produce bus errors on write), or may be
# "invalid" meaning that there is no functionality backed by that register (so
# they have a default value of 0, cannot be modified, but presumably don't
# produce an error when written to).
#
# NOTE: The default memory alignment is assumed to be 4
SIU_RANGE = range(0xC3F90000, 0xC3F94000, 4)

GPIO_RANGE = range(512)

# SIU registers, regions, and minimum access sizes.  From
# Table 6-5. SIU Memory Map (from MPC5674FRM.pdf page 204)
SIU_MIDR        = (0xC3F90004, 4)
SIU_RSR         = (0xC3F9000C, 4)
SIU_SRCR        = (0xC3F90010, 4)
SIU_EISR        = (0xC3F90014, 4)
SIU_DIRER       = (0xC3F90018, 4)
SIU_DIRSR       = (0xC3F9001C, 4)
SIU_OSR         = (0xC3F90020, 4)
SIU_ORER        = (0xC3F90024, 4)
SIU_IREER       = (0xC3F90028, 4)
SIU_IFEER       = (0xC3F9002C, 4)
SIU_IDFR        = (0xC3F90030, 4)
SIU_IFIR        = (0xC3F90034, 4)
SIU_PCR         = (range(0xC3F90040, 0xC3F90440, 2), 2)
SIU_GPDO        = (range(0xC3F90600, 0xC3F90800, 1), 1)
SIU_GPDI_LEGACY = (range(0xC3F90800, 0xC3F90900, 1), 1)
SIU_EIISR       = (0xC3F90904, 4)
SIU_DISR        = (0xC3F90908, 4)
SIU_ISEL4       = (0xC3F90910, 4)
SIU_ISEL5       = (0xC3F90914, 4)
SIU_ISEL6       = (0xC3F90918, 4)
SIU_ISEL7       = (0xC3F9091C, 4)
SIU_ISEL8       = (0xC3F90920, 4)
SIU_ISEL9       = (0xC3F90924, 4)
SIU_DECFIL      = (range(0xC3F90928, 0xC3F90930, 4), 4)
SIU_CCR         = (0xC3F90980, 4)
SIU_ECCR        = (0xC3F90984, 4)
SIU_CBRH        = (0xC3F90990, 4)
SIU_CBRL        = (0xC3F90994, 4)
SIU_SYSDIV      = (0xC3F909A0, 4)
SIU_HLT         = (0xC3F909A4, 4)
SIU_HLTACK      = (0xC3F909A8, 4)
SIU_PGPDO       = (range(0xC3F90C00, 0xC3F90C40, 4), 4)
SIU_PGPDI       = (range(0xC3F90C40, 0xC3F90C80, 4), 4)
SIU_MPGPDO      = (range(0xC3F90C80, 0xC3F90D00, 4), 4)

# TODO: The following peripheral-specific registers are not yet implemented
#   - QADC
#   - DSPI
#   - eTPU
#   - eMIOS
#SIU_DSPI        = (range(0xC3F90D00, 0xC3F90D20, 4), 4)
#SIU_ETPUBA      = (0xC3F90D40, 4)
#SIU_EMIOSA      = (0xC3F90D44, 4)
#SIU_DSPIAHLA    = (0xC3F90D48, 4)
#SIU_ETPUAB      = (0xC3F90D50, 4)
#SIU_EMIOSB      = (0xC3F90D54, 4)
#SIU_DSPIAHLB    = (0xC3F90D58, 4)
#SIU_ETPUAC      = (0xC3F90D60, 4)
#SIU_EMIOSC      = (0xC3F90D64, 4)
#SIU_DSPIAHLC    = (0xC3F90D68, 4)
#SIU_ETPUBC      = (0xC3F90D6C, 4)
#SIU_ETPUBD      = (0xC3F90D70, 4)
#SIU_EMIOSD      = (0xC3F90D74, 4)
#SIU_DSPIAHLD    = (0xC3F90D78, 4)
SIU_PERIPH      = (range(0xC3F90D00, 0xC3F90E00, 4), 4)

# NOTE: Table 6-5 indicates the expanded legacy GDPI range goes from 0x0E00 to
# 0x0FDC. It seems like the range _should_ be from 0x0E00 to 0x1000?
SIU_GPDI        = (range(0xC3F90E00, 0xC3F91000, 1), 1)

VALID_SIU_ADDRs = (
    (SIU_MIDR[0], SIU_RSR[0], SIU_SRCR[0], SIU_EISR[0], SIU_DIRER[0], SIU_DIRSR[0], SIU_OSR[0], SIU_ORER[0], SIU_IREER[0], SIU_IFEER[0], SIU_IDFR[0], SIU_IFIR[0]),
    SIU_PCR[0],
    SIU_GPDO[0],
    SIU_GPDI_LEGACY[0],
    (SIU_EIISR[0], SIU_DISR[0]),
    (SIU_ISEL4[0], SIU_ISEL5[0], SIU_ISEL6[0], SIU_ISEL7[0], SIU_ISEL8[0], SIU_ISEL9[0]),
    SIU_DECFIL[0],
    (SIU_CCR[0], SIU_ECCR[0], SIU_CBRH[0], SIU_CBRL[0], SIU_SYSDIV[0], SIU_HLT[0], SIU_HLTACK[0]),
    SIU_PGPDO[0],
    SIU_PGPDI[0],
    SIU_MPGPDO[0],
    SIU_PERIPH[0],
    SIU_GPDI[0],
)
VALID_SIU_ADDR_LIST = list(itertools.chain.from_iterable(VALID_SIU_ADDRs))

# Addresses that are within the SIU memory range that will produce bus errors
# when read from or written to.
INVALID_SIU_ADDR_LIST = [x for x in SIU_RANGE if x not in VALID_SIU_ADDR_LIST]

# SIU addresses that are valid and represent functionality that is not emulated,
# so reads/writes should be valid but there is no associated functionality to
# test.  The following registers have specific tests and are not included in
# this list:
#   MIDR
#   RSR
#   SRCR
#   EISR
#
# The peripheral-specific configuration registers are also not included in this
# because they are not yet implemented
VALID_SIU_GENERIC_ADDRs = (
    (SIU_DIRER[0], SIU_DIRSR[0], SIU_OSR[0], SIU_ORER[0], SIU_IREER[0], SIU_IFEER[0], SIU_IDFR[0], SIU_IFIR[0]),
    (SIU_EIISR[0], SIU_DISR[0]),
    (SIU_ISEL4[0], SIU_ISEL5[0], SIU_ISEL6[0], SIU_ISEL7[0], SIU_ISEL8[0], SIU_ISEL9[0]),
    SIU_DECFIL[0],
    (SIU_CCR[0], SIU_CBRH[0], SIU_CBRL[0], SIU_HLT[0], SIU_HLTACK[0]),
)
VALID_SIU_GENERIC_ADDR_LIST = list(itertools.chain.from_iterable(VALID_SIU_GENERIC_ADDRs))

# Some of the registers which don't have any special functionality to test do
# have bits which are always expected to be a specific value, so here are some
# mask/value pairs for SIU registers
SIU_REG_CONST_BITS = {
    SIU_DIRER[0]: (0x7F7F0000, 0x00000000),
    SIU_DIRSR[0]: (0xFFFFFFF0, 0x00000000),
    SIU_OSR[0]:   (0xFFFF0000, 0x00000000),
    SIU_ORER[0]:  (0xFFFF0000, 0x00000000),
    SIU_IREER[0]: (0x7FFF0000, 0x00000000),
    SIU_IFEER[0]: (0x7FFF0000, 0x00000000),
    SIU_IDFR[0]:  (0xFFFFFFF0, 0x00000000),
    SIU_IFIR[0]:  (0x7FFF0000, 0x00000000),
    SIU_ISEL4[0]: (0x80808080, 0x00000000),
    SIU_ISEL5[0]: (0x8080FFFF, 0x00000000),
    SIU_ISEL6[0]: (0x80808080, 0x00000000),
    SIU_ISEL7[0]: (0x8080FFFF, 0x00000000),
    SIU_ISEL8[0]: (0xFFEEEEEE, 0x00000000),
    SIU_ISEL9[0]: (0xFFFFFFE0, 0x00000000),
    SIU_CCR[0]:   (0xFFFFFFFE, 0x00000000),
}

# The legacy (single pin) access method has gaps in the memory map for pins that
# cannot be used as GPIO signals
#
# Table 6-66. GPIO Pin Data Input Registers Memory Map
# (from MPC5674FRM.pdf page 282)
#
#        Offset     | GPIO Pin(s)
#   ----------------+------------
#   0x0E00 - 0x0E4A |
#   0x0E4B - 0x0E6E | 75 - 110
#   0x0E6F - 0x0E70 |
#   0x0E71 - 0x0ECC | 113 - 204
#   0x0ECD - 0x0ECF |
#   0x0ED0 - 0x0ED1 | 208 - 209
#   0x0ED2          |
#   0x0ED3          | 211
#   0x0ED4          |
#   0x0ED5          | 213
#   0x0ED6 - 0x0EE6 |
#   0x0EE7 - 0x0EFD | 231 - 253
#   0x0EFE - 0x0EFF |
#   0x0F00 - 0x0F33 | 256 - 307
#   0x0F34 - 0x0FAF |
#   0x0FB0 - 0x0FB5 | 432 - 437
#   0x0FB6 - 0x0FB7 |
#   0x0FB8 - 0x0FD8 | 440 - 472
#   0x0FD9 - 0x0FFF |
#
# NOTE: This table seems incorrect, for example pin 212 appears to be a valid
# GPIO pin in Table 6-22. SIU_PCRn Settings (MPC5674FRM.pdf page 225):
#
#   PCRn | Offset |   GPIO  |  Primary |  A2  | A3 | A4 | ...
#   -----+--------+---------+----------+------+----+----+-----
#    ...
#    212 | 0x01E8 | GPIO212 | BOOTCFG1 | IRQ3 | -- | -- | ...
#    ...
#
# This is the best approximation of which GPIO pins are valid by using the
# values from Table 6-22. where a "GPIO" function is listed for a PCR location.
# The following GPIO pins appear to be valid that are not listed in Table 6-66.
# GPIO Pin Data Input Registers Memory Map: 212, and 220 - 223
#
VALID_GPIO_PINS = (
    range(75, 110+1),
    range(113, 204+1),
    range(208, 209+1),
    range(211, 213+1),
    range(220, 223+1),
    range(231, 253+1),
    range(256, 307+1),
    range(432, 437+1),
    range(440, 472+1),
)

# chain all of the valid GPIO pin numbers
VALID_GPIO_LIST = list(itertools.chain.from_iterable(VALID_GPIO_PINS))
INVALID_GPIO_LIST = [x for x in GPIO_RANGE if x not in VALID_GPIO_LIST]

# mask and shift values to generate PCR test values
PCR_PA_shift = 10
PCR_PA_bits = 3
PCR_OBE_shift = 9
PCR_OBE_bits = 1
PCR_IBE_shift = 8
PCR_IBE_bits = 1
PCR_DSC_shift = 6
PCR_DSC_bits = 2
PCR_ODE_shift = 5
PCR_ODE_bits = 1
PCR_HYS_shift = 4
PCR_HYS_bits = 1
PCR_SRC_shift = 2
PCR_SRC_bits = 2
PCR_WPE_shift = 1
PCR_WPE_bits = 1
PCR_WPS_shift = 0
PCR_WPS_bits = 1

PCR_FIELDS = {
    'pa':  (PCR_PA_shift,  PCR_PA_bits),
    'obe': (PCR_OBE_shift, PCR_OBE_bits),
    'ibe': (PCR_IBE_shift, PCR_IBE_bits),
    'dsc': (PCR_DSC_shift, PCR_DSC_bits),
    'ode': (PCR_ODE_shift, PCR_ODE_bits),
    'hys': (PCR_HYS_shift, PCR_HYS_bits),
    'src': (PCR_SRC_shift, PCR_SRC_bits),
    'wpe': (PCR_WPE_shift, PCR_WPE_bits),
    'wps': (PCR_WPS_shift, PCR_WPS_bits),
}
PCR_PAD_BITS_MASK = 0xE000


class MPC5674_SIU_Test(MPC5674_Test):

    ##################################################
    # Useful utilities for tests
    ##################################################

    def validate_invalid_addr_noexc(self, addr, size):
        '''
        "Invalid" has multiple meanings for the SIU, this function tests that
        writes to addresses representing "invalid" GPIO pins are always 0 and
        do not produce errors when written to.
        '''
        # The value read from an "invalid" address should be 0 but should not
        # produce a PPC exception.
        self.assertEqual(self.emu.readMemValue(addr, size), 0)

        # Write a value of all 1's and confirm that it still reads 0
        self.emu.writeMemory(addr, b'\x00' * size)
        self.assertEqual(self.emu.readMemValue(addr, size), 0)

        # Confirm no read or write exceptions occured
        msg = 'Invalid read from 0x%x (size %d) confirming no exceptions' % (addr, size)
        self.assertEqual(self._getPendingExceptions(), [], msg)

    def get_pcr_defaults(self):
        # PCR defaults
        #   Table 6-22. SIU_PCRn Settings (MPC5674FRM.pdf page 225)
        #
        # NOTE: Not all GPIO pins are registers are considered as valid (see
        # VALID_GPIO_PINS above), and there are valid PCR registers for pins
        # that are not considered valid GPIO pins.
        pcr_defaults = {}

        wkpcfg_default = self.emu.config.project.MPC5674.SIU.wkpcfg

        # I can't think of a better way to handle this
        for pin in range(75, 83):
            pcr_defaults[pin] = {'pa': None, 'obe': 0,    'ibe': 0,    'dsc': 3,    'ode': None, 'hys': None, 'src': None, 'wpe': None, 'wps': None}
        for pin in range(83, 111):
            pcr_defaults[pin] = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': 1}
        pcr_defaults[113]     = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': 1}
        for pin in range(114, 146):
            pcr_defaults[pin] = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': wkpcfg_default}
        pcr_defaults[146]     = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': 1}
        for pin in range(147, 205):
            pcr_defaults[pin] = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': wkpcfg_default}
        for pin in range(208, 210):
            pcr_defaults[pin] = {'pa': 1,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 1,    'src': 0,    'wpe': 1,    'wps': 1}
        for pin in range(211, 213):
            pcr_defaults[pin] = {'pa': 1,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 1,    'src': 0,    'wpe': 1,    'wps': 0}
        pcr_defaults[213]     = {'pa': 1,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': None, 'hys': 1,    'src': 0,    'wpe': 1,    'wps': 1}
        pcr_defaults[214]     = {'pa': None, 'obe': 1,    'ibe': None, 'dsc': 3,    'ode': None, 'hys': None, 'src': None, 'wpe': None, 'wps': None}
        pcr_defaults[219]     = {'pa': None, 'obe': None, 'ibe': None, 'dsc': 3,    'ode': None, 'hys': None, 'src': None, 'wpe': None, 'wps': None}
        pcr_defaults[220]     = {'pa': None, 'obe': 0,    'ibe': 0,    'dsc': 3,    'ode': 0,    'hys': 0,    'src': 0,    'wpe': 0,    'wps': None}
        for pin in range(221, 224):
            pcr_defaults[pin] = {'pa': None, 'obe': 0,    'ibe': 0,    'dsc': 3,    'ode': 0,    'hys': 0,    'src': 0,    'wpe': 0,    'wps': 0}
        for pin in range(224, 229):
            pcr_defaults[pin] = {'pa': None, 'obe': None, 'ibe': None, 'dsc': 3,    'ode': None, 'hys': None, 'src': None, 'wpe': None, 'wps': None}
        pcr_defaults[229]     = {'pa': None, 'obe': 1,    'ibe': None, 'dsc': 3,    'ode': None, 'hys': None, 'src': None, 'wpe': None, 'wps': None}
        pcr_defaults[230]     = {'pa': None, 'obe': 1,    'ibe': None, 'dsc': None, 'ode': None, 'hys': None, 'src': 0,    'wpe': None, 'wps': None}
        for pin in range(231, 235):
            pcr_defaults[pin] = {'pa': None, 'obe': 0,    'ibe': 0,    'dsc': 3,    'ode': 0,    'hys': 0,    'src': None, 'wpe': 0,    'wps': 0}
        for pin in range(235, 248):
            pcr_defaults[pin] = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': 1}
        for pin in range(248, 254):
            pcr_defaults[pin] = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': 1}
        for pin in range(256, 299):
            pcr_defaults[pin] = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': 1}
        pcr_defaults[299] = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': 0}
        for pin in range(300, 308):
            pcr_defaults[pin] = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': 1}
        for pin in range(432, 438):
            pcr_defaults[pin] = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': wkpcfg_default}
        pcr_defaults[440] = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': 1}
        for pin in range(441, 472):
            pcr_defaults[pin] = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': wkpcfg_default}

        # Add default "None" fields for PCR addresses that aren't valid.
        for pin in GPIO_RANGE:
            if pin not in pcr_defaults:
                pcr_defaults[pin] = dict((key, None) for key in PCR_FIELDS)

        return pcr_defaults

    def get_pcr_default_value(self, cfg):
        val = 0
        for key in cfg:
            shift, bits = PCR_FIELDS[key]
            val |= cfg[key] << shift if cfg[key] is not None else 0
        return val

    def gen_pcr_test_values(self, cfg):
        '''
        Generate a list of PCR values to test.

        Each entry in the list is a tuple of 3 values:
            - write value
            - read value
            - a dict of attribute names and their expected values
        '''
        # The test values could get large so generate the following write/read
        # values pairs:
        # all 0's
        write_val = 0
        read_val = 0
        field_vals = {'pa': 0, 'obe': 0, 'ibe': 0, 'dsc': 0, 'ode': 0, 'hys': 0, 'src': 0, 'wpe': 0, 'wps': 0}
        test_vals = [(write_val, read_val, dict(field_vals))]

        # all fields 1's (read result: all values 1 except for disabled fields)
        write_val = 0
        read_val = 0
        field_vals = {}
        for key in cfg:
            shift, bits = PCR_FIELDS[key]
            write_val |= 1 << shift
            if cfg[key] is None:
                field_vals[key] = 0
            else:
                read_val |= 1 << shift
                field_vals[key] = 1
        test_vals.append((write_val, read_val, dict(field_vals)))

        # all reserved bits 1 and all other's 0 (read result is all 0's)
        write_val = PCR_PAD_BITS_MASK
        read_val = 0
        field_vals = {'pa': 0, 'obe': 0, 'ibe': 0, 'dsc': 0, 'ode': 0, 'hys': 0, 'src': 0, 'wpe': 0, 'wps': 0}
        for key in cfg:
            shift, bits = PCR_FIELDS[key]
            if cfg[key] is None:
                val = e_bits.b_masks[bits]
                write_val |= val << shift
        test_vals.append((write_val, read_val, dict(field_vals)))

        # all bits set to 1 (read result is only valid fields set to 1's)
        write_val = 0xFFFF
        read_val = 0
        field_vals = {}
        for key in cfg:
            shift, bits = PCR_FIELDS[key]
            if cfg[key] is None:
                field_vals[key] = 0
            else:
                val = e_bits.b_masks[bits]
                read_val |= val << shift
                field_vals[key] = val
        test_vals.append((write_val, read_val, dict(field_vals)))

        return test_vals

    def get_gpio_test_info(self):
        '''
        Iterate over the entire SIU memory range and for each valid register
        returns the (address, size) pairs of how to access this pin, the
        default state and PCR config for the GPIO.
        '''
        pcr_cfg = self.get_pcr_defaults()

        tests = []
        for pin in VALID_GPIO_LIST:
            offset = pin // 32
            mask = 1 << (31 - (pin % 32))
            shift = 31 - (pin % 32)

            # The "default" state for all GPIO inputs should be 0 because none
            # of the GPIO pins have the input buffer enabled.  However, once the
            # input buffer is enabled the default pull up/down state should
            # drive the default state.
            default = 1 if pcr_cfg[pin]['wpe'] and pcr_cfg[pin]['wps'] else 0

            info = {
                'pin': pin,
                'default': default,
                'cfg': pcr_cfg[pin],

                # Standard offset/mask/shift values
                'offset': offset,
                'mask': mask,
                'shift': shift,

                # Flags indicating if this GPIO can be used to read/write
                # external pin values
                'input': pcr_cfg[pin]['pa'] is not None and pcr_cfg[pin]['ibe'] is not None,
                'output': pcr_cfg[pin]['pa'] is not None and pcr_cfg[pin]['obe'] is not None,

                # Addresses that can be used to test read/write
                'read': [],
                'write': [],
            }

            # TODO: Ideally I'd like to manually confirm which GPIO pins are
            # valid for input and output and just return that, but given the
            # list of GPIO pins and how complex this all is I am doing it
            # pragmatically based on the PCR config values for now.

            # Each GPIO may not be able to be used to actually read or change
            # the status of a simulated external pin, but reads and attempted
            # writes should complete successfully.

            # 0xC3F90800: GPDI (legacy) limited to the first 256 pins
            if pin < 256:
                info['read'].append({
                    'addr': SIU_GPDI_LEGACY[0].start + pin,
                    'align': 1,
                    'mask': 0x01,
                    'shift': 0,
                })

            # 0xC3F90C40: PGPDI
            info['read'].append({
                'addr': SIU_PGPDI[0].start + (offset * 4),
                'align': 4,
                'mask': mask,
                'shift': shift,
            })

            # 0xC3F90E00: GPDI (legacy) expanded to allow full access to all
            #             512 pin access
            info['read'].append({
                'addr': SIU_GPDI[0].start + pin,
                'align': 1,
                'mask': 0x01,
                'shift': 0,
            })

            # 0xC3F90600: GPDO (legacy, limited to the first 256 pins)
            info['write'].append({
                'addr': SIU_GPDO[0].start + pin,
                'align': 1,
                'mask': 0x01,
                'shift': 0,
            })

            # 0xC3F90C00: PGPDO
            info['write'].append({
                'addr': SIU_PGPDO[0].start + (offset * 4),
                'align': 4,
                'mask': mask,
                'shift': shift,
            })

            tests.append(info)
        return tests

    def set_one_gpio(self, cur_val, gpio_val, mask, **kwargs):
        # Helper to set/clear 1 bit in a value
        if gpio_val:
            return cur_val | mask
        else:
            return cur_val & ~mask

    def get_one_gpio(self, cur_val, mask, shift, **kwargs):
        # Extract 1 GPIO bit from the input value and return it
        return (cur_val & mask) >> shift

    def write_one_gpio(self, gpio_val, addr, align, mask, **kwargs):
        cur_val = self.emu.readMemValue(addr, align)
        write_val = self.set_one_gpio(cur_val, gpio_val, mask)
        self.emu.writeMemValue(addr, write_val, align)

    def read_one_gpio(self, addr, align, mask, shift, **kwargs):
        cur_val = self.emu.readMemValue(addr, align)
        return self.get_one_gpio(cur_val, mask, shift)

    def set_sysclk_264mhz(self):
        # Default PLL clock based on the PCB params selected for these tests is
        # 60 MHz
        self.assertEqual(self.emu.config.project.MPC5674.FMPLL.extal, 40000000)
        self.assertEqual(self.emu.getClock('pll'), 60000000.0)

        # The max clock for the real hardware is 264 MHz:
        #  (40 MHz * (50+16)) / ((4+1) * (1+1))

        # ESYNCR1[EMFD] = 50
        # ESYNCR1[EPREDIV] = 4
        self.emu.writeMemValue(0xC3F80008, 0xF0040032, 4)
        # ESYNCR2[ERFD] = 1
        self.emu.writeMemValue(0xC3F8000C, 0x00000001, 4)
        self.assertEqual(self.emu.getClock('pll'), 264000000.0)

    def change_pgpdo_state(self, state):
        """
        Change all GPIO pins to the specified value (0 or 1). Returns the
        expected state of the PGPDO values
        """
        num_pgpdo_regs = len(list(self.emu.siu.registers.pgpdo))
        if state:
            expected_pgpdo_vals = [0xFFFFFFFF for i in range(num_pgpdo_regs)]
        else:
            expected_pgpdo_vals = [0x00000000 for i in range(num_pgpdo_regs)]

        # Loop through the output pins now, and for pins that can be configured
        # as output (PCR[PA] = 0 and PCR[OBE] = 1), change the expected value of
        # external pin to the specified state
        expected_pin_vals = self.emu.siu.pin_value[:]
        pcr_cfg = self.get_pcr_defaults()
        for pin in VALID_GPIO_LIST:
            if pcr_cfg[pin]['pa'] is not None and pcr_cfg[pin]['obe'] is not None:
                offset = pin // 32
                mask = 1 << (31 - (pin % 32))
                if state:
                    expected_pin_vals[offset] |= mask
                else:
                    expected_pin_vals[offset] &= ~mask

        # Now set the PGPDO registers through the normal writeMemValue api to
        # ensure the callbacks happen to update the external pin states
        for val, addr in zip(expected_pgpdo_vals, SIU_PGPDO[0]):
            self.emu.writeMemValue(addr, val, SIU_PGPDO[1])

        return (expected_pgpdo_vals, expected_pin_vals)

    ##################################################
    # Tests
    ##################################################

    # Tests for configuration registers with special functionality

    def test_siu_midr(self):
        addr, size = SIU_MIDR
        self.assertEqual(self.emu.readMemValue(addr, size), 0x5674E000)
        self.validate_invalid_write(addr, size)

    def test_siu_rsr(self):
        # Verify RSR[SERF] default. The RSR register has WKPCFG and BOOTCFG
        # read-only values
        # For this configuration WKPCFG is 1 and BOOTCFG is 0 so the default RSR
        # value is:
        #   0xx00008000
        addr, size = SIU_RSR
        default_val = 0x80008000

        # By default the PORS flag should be set
        self.assertEqual(self.emu.readMemValue(addr, size), default_val)
        self.assertEqual(self.emu.siu.registers.rsr.pors, 1)
        self.assertEqual(self.emu.siu.registers.rsr.ers, 0)
        self.assertEqual(self.emu.siu.registers.rsr.llrs, 0)
        self.assertEqual(self.emu.siu.registers.rsr.lcrs, 0)
        self.assertEqual(self.emu.siu.registers.rsr.wdrs, 0)
        self.assertEqual(self.emu.siu.registers.rsr.swtrs, 0)
        self.assertEqual(self.emu.siu.registers.rsr.ssrs, 0)
        self.assertEqual(self.emu.siu.registers.rsr.serf, 0)
        self.assertEqual(self.emu.siu.registers.rsr.wkpcfg, 1)
        self.assertEqual(self.emu.siu.registers.rsr.abr, 0)
        self.assertEqual(self.emu.siu.registers.rsr.bootcfg, 0)
        self.assertEqual(self.emu.siu.registers.rsr.rgf, 0)

        # The SERF and RGF fields are w1c, all other fields are const:
        # Writing 1 to every 0 bit in RSR should result in no change.
        self.emu.writeMemValue(addr, ~default_val, size)
        self.assertEqual(self.emu.readMemValue(addr, size), default_val)

        # Trigger some resets and ensure the correct reset source is set (also 
        # the weak pullup flag is set)
        source_tests = [
            (intc_exc.ResetSource.POWER_ON,          'pors',  0x80008000),
            (intc_exc.ResetSource.EXTERNAL,          'ers',   0x40008000),
            (intc_exc.ResetSource.LOSS_OF_LOCK,      'llrs',  0x20008000),
            (intc_exc.ResetSource.LOSS_OF_CLOCK,     'lcrs',  0x10008000),
            (intc_exc.ResetSource.CORE_WATCHDOG,     'wdrs',  0x08008000),
            (intc_exc.ResetSource.DEBUG,             'wdrs',  0x08008000),
            (intc_exc.ResetSource.WATCHDOG,          'swtrs', 0x02008000),
            (intc_exc.ResetSource.SOFTWARE_SYSTEM,   'ssrs',  0x00028000),
            (intc_exc.ResetSource.SOFTWARE_EXTERNAL, 'serf',  0x00018000),
        ]

        for source, test_field, test_value in source_tests:
            # Queue a reset exception with the desired reset reason and step to 
            # reset the emulator
            self.emu.queueException(intc_exc.ResetException(source))
            self.emu.stepi()

            # Verify that the reset reason is now set correctly
            self.assertEqual(self.emu.readMemValue(addr, size), test_value, msg=test_field)

            for field, value in self.emu.siu.registers.rsr.vsGetFields():
                msg = '%s (%s)' % (field, test_field)
                if field in (test_field, 'wkpcfg'):
                    self.assertEqual(value, 1, msg=msg)
                else:
                    self.assertEqual(value, 0, msg=msg)

            # Writing 0 to all fields should not change anything
            self.emu.writeMemValue(addr, 0, size)

            for field, value in self.emu.siu.registers.rsr.vsGetFields():
                msg = '%s (%s)' % (field, test_field)
                if field in (test_field, 'wkpcfg'):
                    self.assertEqual(value, 1, msg=msg)
                else:
                    self.assertEqual(value, 0, msg=msg)

            # Writing the value read should not change anything unless the bit 
            # being changed is SERF
            self.emu.writeMemValue(addr, test_value, size)

            for field, value in self.emu.siu.registers.rsr.vsGetFields():
                msg = '%s (%s)' % (field, test_field)
                if field in (test_field, 'wkpcfg') and field != 'serf':
                    self.assertEqual(value, 1, msg=msg)
                else:
                    self.assertEqual(value, 0, msg=msg)

    def test_siu_srcr(self):
        # Fill in a bunch of NOPs (0x60000000: ori r0,r0,0) starting at the
        # current PC (0x00000000)
        pc = self.emu.getProgramCounter()
        self.assertEqual(pc, 0)
        instrs = b'\x60\x00\x00\x00' * 0x100
        with mmio.supervisorMode(self.emu):
            self.emu.writeMemory(pc, instrs)

        rsr_addr, size = SIU_RSR

        # Verify RSR[SERF] is 0 WKPCFG = 1, BOOTCFG = 0, and PORS is 1 (because 
        # this is the initial power on)
        rsr_val = 0x80008000
        self.assertEqual(self.emu.readMemValue(rsr_addr, size), rsr_val)
        self.assertEqual(self.emu.siu.registers.rsr.serf, 0)

        # Verify SRCR is 0 by default
        srcr_addr, _ = SIU_SRCR
        self.assertEqual(self.emu.readMemValue(srcr_addr, size), 0)
        self.assertEqual(self.emu.siu.registers.srcr.ser, 0)
        self.assertEqual(self.emu.siu.registers.srcr.ssr, 0)

        # Writing a 1 to SRCR[SSR] causes a software system reset and sets the 
        # RSR[SSRS] flag.
        self.emu.writeMemValue(srcr_addr, 0x80000000, size)

        # Ensure that the exception has been queued
        self.assertEqual(self.checkPendingExceptions(), \
                [intc_exc.ResetException(intc_exc.ResetSource.SOFTWARE_SYSTEM)])

        # Before the reset:
        #   RSR[SSRS] is 0
        #   RSR[SERF] is 0
        self.assertEqual(self.emu.readMemValue(rsr_addr, size), rsr_val)
        self.assertEqual(self.emu.siu.registers.rsr.serf, 0)
        self.assertEqual(self.emu.siu.registers.rsr.ssrs, 0)

        #   SRCR[SER] is 0
        #   SRCR[SSR] is 1
        self.assertEqual(self.emu.readMemValue(srcr_addr, size), 0x80000000)
        self.assertEqual(self.emu.siu.registers.srcr.ser, 0)
        self.assertEqual(self.emu.siu.registers.srcr.ssr, 1)

        # Step to trigger the reset
        self.emu.stepi()

        # PC should be back at 0
        self.assertEqual(self.emu.getProgramCounter(), 0)

        # After the reset:
        #   RSR[SSRS] is 1
        #   RSR[SERF] is 0
        rsr_val = 0x00028000
        self.assertEqual(self.emu.readMemValue(rsr_addr, size), rsr_val)
        self.assertEqual(self.emu.siu.registers.rsr.serf, 0)
        self.assertEqual(self.emu.siu.registers.rsr.ssrs, 1)

        #   SRCR[SER] is 0
        #   SRCR[SSR] is 0
        self.assertEqual(self.emu.readMemValue(srcr_addr, size), 0)
        self.assertEqual(self.emu.siu.registers.srcr.ser, 0)
        self.assertEqual(self.emu.siu.registers.srcr.ssr, 0)

        # Writing a 1 to SRCR[SSR] causes a software external reset and sets the 
        # RSR[SERF] flag.
        self.emu.writeMemValue(srcr_addr, 0x40000000, size)

        # Ensure that the exception has been queued
        self.assertEqual(self.checkPendingExceptions(), \
                [intc_exc.ResetException(intc_exc.ResetSource.SOFTWARE_EXTERNAL)])

        # Before the reset:
        #   RSR[SSRS] is still 1
        #   RSR[SERF] is 0
        self.assertEqual(self.emu.readMemValue(rsr_addr, size), rsr_val)
        self.assertEqual(self.emu.siu.registers.rsr.ssrs, 1)
        self.assertEqual(self.emu.siu.registers.rsr.serf, 0)

        #   SRCR[SER] is 1
        #   SRCR[SSR] is 0
        self.assertEqual(self.emu.readMemValue(srcr_addr, size), 0x40000000)
        self.assertEqual(self.emu.siu.registers.srcr.ser, 1)
        self.assertEqual(self.emu.siu.registers.srcr.ssr, 0)

        # Step to trigger the reset
        self.emu.stepi()

        # PC should be back at 0
        self.assertEqual(self.emu.getProgramCounter(), 0)

        # After the reset:
        #   RSR[SSRS] is 0
        #   RSR[SERF] is 1
        rsr_val = 0x00018000
        self.assertEqual(self.emu.readMemValue(rsr_addr, size), rsr_val)
        self.assertEqual(self.emu.siu.registers.rsr.ssrs, 0)
        self.assertEqual(self.emu.siu.registers.rsr.serf, 1)

        #   SRCR[SER] is 0
        #   SRCR[SSR] is 0
        self.assertEqual(self.emu.readMemValue(srcr_addr, size), 0)
        self.assertEqual(self.emu.siu.registers.srcr.ser, 0)
        self.assertEqual(self.emu.siu.registers.srcr.ssr, 0)

        # All other values should have no affect
        self.emu.writeMemValue(srcr_addr, 0x3FFFFFFF, size)
        self.assertEqual(self.emu.readMemValue(srcr_addr, size), 0)

        # Step and verify no reset occured
        self.emu.stepi()

        # PC should have moved to 4
        self.assertEqual(self.emu.getProgramCounter(), 4)

        # Verify RSR and SCRC haven't changed
        self.assertEqual(self.emu.readMemValue(rsr_addr, size), rsr_val)
        self.assertEqual(self.emu.readMemValue(srcr_addr, size), 0)

    def test_siu_ccr(self):
        # writing FEEDFACECAFEBEEF to CBRH/CBRL
        ccr_addr, size = SIU_CCR
        cbrh_addr, _ = SIU_CBRH
        cbrl_addr, _ = SIU_CBRL
        self.assertEqual(self.emu.readMemValue(ccr_addr, size), 0)
        self.assertEqual(self.emu.siu.registers.ccr.match, 0)
        self.assertEqual(self.emu.readMemValue(cbrh_addr, size), 0)
        self.assertEqual(self.emu.readMemValue(cbrl_addr, size), 0)

        # Write 0xFEEDFACE to CBRH and confirm nothing changed
        self.emu.writeMemValue(cbrh_addr, 0xFEEDFACE, size)
        self.assertEqual(self.emu.readMemValue(cbrh_addr, size), 0xFEEDFACE)

        self.assertEqual(self.emu.readMemValue(ccr_addr, size), 0)
        self.assertEqual(self.emu.siu.registers.ccr.match, 0)

        # Write 0 to CBRH and 0xCAFEBEEF to CBRL and confirm nothing changed
        self.emu.writeMemValue(cbrh_addr, 0, size)
        self.emu.writeMemValue(cbrl_addr, 0xCAFEBEEF, size)
        self.assertEqual(self.emu.readMemValue(cbrh_addr, size), 0)
        self.assertEqual(self.emu.readMemValue(cbrl_addr, size), 0xCAFEBEEF)

        self.assertEqual(self.emu.readMemValue(ccr_addr, size), 0)
        self.assertEqual(self.emu.siu.registers.ccr.match, 0)

        # Write 0xFEEDFACE to CBRH 0xCAFEBEEF to CBRL and that the CCR[MATCH]
        # bit is now set
        self.emu.writeMemValue(cbrh_addr, 0xFEEDFACE, size)
        self.emu.writeMemValue(cbrl_addr, 0xCAFEBEEF, size)
        self.assertEqual(self.emu.readMemValue(cbrh_addr, size), 0xFEEDFACE)
        self.assertEqual(self.emu.readMemValue(cbrl_addr, size), 0xCAFEBEEF)

        self.assertEqual(self.emu.readMemValue(ccr_addr, size), 0x00020000)
        self.assertEqual(self.emu.siu.registers.ccr.match, 1)

    # PCR tests

    def test_siu_pcr_defaults(self):
        pcr_cfg = self.get_pcr_defaults()
        pcr_range, pcr_size = SIU_PCR
        # The PCR configuration is annoying and weird, test it separately from
        # the majority of the vstruct backed regions
        start_addr = pcr_range.start
        for test_addr in pcr_range:
            pin = (test_addr - start_addr) // pcr_size

            try:
                test_val = self.get_pcr_default_value(pcr_cfg[pin])

                # First verify the PCR register has the expected default value
                msg = '(0x%x) PCR[%d] default 0x%x' % (test_addr, pin, test_val)
                self.assertEqual(self.emu.readMemValue(test_addr, pcr_size), test_val, msg)

                # Get the list of read/write values to test
                for test_values in self.gen_pcr_test_values(pcr_cfg[pin]):
                    write_val, read_val, field_vals = test_values
                    msg = '(0x%x) PCR[%d] = 0x%x (result = 0x%x)' % (test_addr, pin, write_val, read_val)

                    self.emu.writeMemValue(test_addr, write_val, pcr_size)
                    self.assertEqual(self.emu.readMemValue(test_addr, pcr_size), read_val, msg)

                    fields = dict((k, v) for k, v in self.emu.siu.registers.pcr[pin].vsGetFields() if not k.startswith('_'))
                    self.assertEqual(fields, field_vals, msg)

            except KeyError:
                # This is not a valid PCR/GPIO pin, verify that both reads and
                # writes fail.
                self.validate_invalid_addr_noexc(test_addr, pcr_size)

            # Ensure that there are no unprocessed exceptions
            msg = 'PCR(%d) checking if all exceptions handled' % pin
            self.assertEqual(self._getPendingExceptions(), [], msg)

    def test_siu_pcr_4byte_access(self):
        # Pins 212, 213, and 214 have different default values and are
        # sequential.
        pcr_range, size = SIU_PCR
        base = pcr_range.start

        pcr_cfg = self.get_pcr_defaults()

        pcr212_addr = base + (212 * size)
        pcr212_val = self.get_pcr_default_value(pcr_cfg[212])

        pcr213_addr = base + (213 * size)
        pcr213_val = self.get_pcr_default_value(pcr_cfg[213])

        pcr214_addr = base + (214 * size)
        pcr214_val = self.get_pcr_default_value(pcr_cfg[214])

        pcr215_addr = base + (215 * size)
        pcr215_val = self.get_pcr_default_value(pcr_cfg[215])

        # Confirm that the 4 PCR register defaults are as expected:
        self.assertEqual(self.emu.readMemValue(pcr212_addr, size), pcr212_val)
        self.assertEqual(self.emu.readMemValue(pcr213_addr, size), pcr213_val)
        self.assertEqual(self.emu.readMemValue(pcr214_addr, size), pcr214_val)
        self.assertEqual(self.emu.readMemValue(pcr215_addr, size), pcr215_val)

        # And that PCR 215 is 0 (because it is not a "valid" GPIO)
        self.assertEqual(pcr215_val, 0)

        # All memory reads of the PCR region that multiples of 2 bytes and are
        # 2-byte aligned should be successful.

        # Read PCRs 212 and 213 together
        self.assertEqual(self.emu.readMemValue(pcr212_addr, 4), (pcr212_val << 16) | pcr213_val)

        self.assertEqual(self.emu.readMemValue(pcr213_addr, 4), (pcr213_val << 16) | pcr214_val)

        # Read PCR 213 with odd size, this should generate an ALIGNMENT
        # exception (reading 5 bytes from a 2-byte aligned offset)
        # Expected data that will have been read before generating the error
        align_err_data = struct.pack('>HHH', pcr213_val, pcr214_val, 0)
        self.validate_unaligned_read(pcr213_addr, 5, data=align_err_data)

        # Read PCRs 213 and 214 together
        # Read PCRs 214 and 215 together
        self.assertEqual(self.emu.readMemValue(pcr214_addr, 4), (pcr214_val << 16) | pcr215_val)

    def test_siu_unaligned_read(self):
        pcr_range, size = SIU_PCR
        base = pcr_range.start

        # Unaligned reads now have data attached that is useful for debugging
        # (and doesn't hurt anything having it attached), gather the expected
        # read results for
        pcr_cfg = self.get_pcr_defaults()
        pcr212_val = self.get_pcr_default_value(pcr_cfg[212])
        pcr213_val = self.get_pcr_default_value(pcr_cfg[213])
        pcr214_val = self.get_pcr_default_value(pcr_cfg[214])
        pcr215_val = self.get_pcr_default_value(pcr_cfg[215])
        pcr216_val = self.get_pcr_default_value(pcr_cfg[216])
        pcr217_val = self.get_pcr_default_value(pcr_cfg[217])

        # Don't read sizes larger than 8, reads larger than a valid PowerPC
        # access use a more permissive memory read method
        test_vals = (
            (base + (212 * size),     1, struct.pack('>H', pcr212_val)),
            (base + (212 * size),     3, struct.pack('>HH', pcr212_val, pcr213_val)),
            (base + (213 * size) + 1, 2, b''),
            (base + (214 * size),     7, struct.pack('>HHHH', pcr214_val, pcr215_val, pcr216_val, pcr217_val)),
            (base + (215 * size),     5, struct.pack('>HHH', pcr215_val, pcr216_val, pcr217_val)),
        )

        for addr, size, read_data in test_vals:
            self.validate_unaligned_read(addr, size, data=read_data)

    def test_siu_unaligned_write(self):
        pcr_range, size = SIU_PCR
        base = pcr_range.start

        # Don't write sizes larger than 8, writes larger than a valid PowerPC
        # access use a more permissive memory write method.  AlignmentExceptions
        # that happen during write have attached information indicating how much
        # data was written.
        test_vals = (
            (base + (212 * size),     1, 0),
            (base + (212 * size),     3, 2),
            (base + (213 * size) + 1, 2, 0),
            (base + (214 * size),     7, 6),
            (base + (215 * size),     5, 4),
        )
        for addr, size, written in test_vals:
            self.validate_unaligned_write(addr, size=size, written=written)

    # GPIO tests

    def test_siu_gpdi(self):
        pcr_range, pcr_size = SIU_PCR
        ibe_bit   = 0x0100
        pa_mask   = 0x1C00
        pull_mask = 0x0003
        pcr_cfg = self.get_pcr_defaults()

        # Confirm the default pin state for all valid GPIO signals
        for info in self.get_gpio_test_info():
            pin = info['pin']

            for test in info['read']:
                msg = '[0x%08x] GPDI(%d) default == %d' % (test['addr'], pin, 0)
                read_val = self.read_one_gpio(**test)
                # The initial read for all GPIO inputs should be 0 because none
                # of the GPIO pins have their input buffer enabled by default
                self.assertEqual(read_val, 0, msg)

                # Attempting to write to the read locations should produce an
                # error
                msg = 'GPDI(%d) write' % pin
                self.validate_invalid_write(test['addr'], test['align'], msg=msg)

            # If this GPIO is able to act as an input change the pin_value
            # to be the opposite of the default value and verify that the
            # value being read is still the default and not the pin_value
            # (because the input buffer should not be enabled for any GPIO
            # pin by default).
            if info['input']:
                # input buffer currently disabled
                self.assertEqual(self.emu.siu.registers.pcr[pin].ibe, 0, msg)

                # If a pin is an output, has an externally connected value, or
                # has the weak pull up/down enabled then the pin value will be
                # overridden whenever the GPIO states are refreshed (when PCR,
                # PGPDO, or connect changes occur).
                #
                # Clear this GPIO's default connection (if it exists)
                self.emu.siu.disconnectGPIO(pin)

                # Enable the input buffer and ensure that this pin's mode is set
                # to GPIO
                pcr_addr = pcr_range.start + (pin * pcr_size)
                pcr_val = self.emu.readMemValue(pcr_addr, pcr_size)
                enable_input_val = (pcr_val & ~pa_mask) | ibe_bit
                self.emu.writeMemValue(pcr_addr, enable_input_val, pcr_size)

                self.assertEqual(self.emu.readMemValue(pcr_addr, pcr_size), enable_input_val)
                self.assertEqual(self.emu.siu.registers.pcr[pin].pa, 0)
                self.assertEqual(self.emu.siu.registers.pcr[pin].ibe, 1)

                # Ensure that the default input value has the expected value
                msg = '[0x%08x] GPDI(%d) default == %d' % (test['addr'], pin, info['default'])
                for test in info['read']:
                    msg = '[0x%08x] GPDI(%d) == %d' % (test['addr'], pin, info['default'])
                    read_val = self.read_one_gpio(**test)
                    self.assertEqual(read_val, info['default'], msg)

                # Now ensure any pull up/downs are disabled
                pcr_val = self.emu.readMemValue(pcr_addr, pcr_size)
                disable_pull_val = enable_input_val & ~pull_mask
                self.emu.writeMemValue(pcr_addr, disable_pull_val, pcr_size)

                self.assertEqual(self.emu.readMemValue(pcr_addr, pcr_size), disable_pull_val)
                self.assertEqual(self.emu.siu.registers.pcr[pin].wpe, 0)
                self.assertEqual(self.emu.siu.registers.pcr[pin].wps, 0)

                # Disabling the external connection and the pull up/down should
                # have left the external pin value at 0
                for test in info['read']:
                    msg = '[0x%08x] GPDI(%d) == %d' % (test['addr'], pin, info['default'])
                    read_val = self.read_one_gpio(**test)
                    self.assertEqual(read_val, 0, msg)
                msg = 'getGPIO(%d)' % pin
                self.assertEqual(self.emu.siu.getGPIO(pin), False, msg)

                # Since the external value is now 0, force the external pin
                # value to be 1
                cur_pin_val = self.emu.siu.pin_value[info['offset']]
                new_val = self.set_one_gpio(cur_pin_val, 1, **info)
                self.emu.siu.pin_value[info['offset']] = new_val

                # Confirm that the getGPIO API returns the changed pin value
                msg = 'getGPIO(%d)' % pin
                self.assertEqual(self.emu.siu.getGPIO(pin), True, msg)

                # Because we just changed the pin value directly and not through
                # normal MMIO peripheral write methods the input value has not
                # been refreshed from the external pin value yet.
                #
                # If we call the refreshPinValue SIU utility function to force
                # this refresh to happen the external pin value is re-calculated
                # based on possible inputs so we should read a value of 0 again.
                self.emu.siu.refreshPinValue(pin)

                for test in info['read']:
                    msg = '[0x%08x] GPDI(%d) == %d' % (test['addr'], pin, info['default'])
                    read_val = self.read_one_gpio(**test)
                    self.assertEqual(read_val, 0, msg)
                msg = 'getGPIO(%d)' % pin
                self.assertEqual(self.emu.siu.getGPIO(pin), False, msg)

                # To force the external pin value to become 1 instead of 0,
                # force the default_value to 1 (normally the "default" is
                # calculated based on the pull up/down configuration, but not
                # all pins are pull up/down capable so for testing purposes it's
                # easier just to force it.
                self.emu.siu._default_value[info['offset']] = info['mask']

                # Confirm that external pin value has not changed yet
                read_val = self.emu.siu.pin_value[info['offset']]
                msg = 'GPIO(%d) pin_value[%d] & 0x%x' % (pin, info['offset'], info['mask'])
                self.assertEqual(self.get_one_gpio(read_val, **info), 0, msg)
                msg = 'getGPIO(%d)' % pin
                self.assertEqual(self.emu.siu.getGPIO(pin), False, msg)

                # force the pin values to refresh again
                self.emu.siu.refreshPinValue(pin)

                # If this is a GPIO capable pin, verify that the read value has
                # changed, otherwise it should still be the 0 value that was
                # calculated when the PCR configuration changed above.
                if pcr_cfg[pin]['pa'] is not None and pcr_cfg[pin]['ibe'] is not None:
                    expected_read_val = 1
                else:
                    expected_read_val = 0

                for test in info['read']:
                    msg = '[0x%08x] GPIO(%d) == %d' % (test['addr'], pin, expected_read_val)
                    read_val = self.read_one_gpio(**test)
                    self.assertEqual(read_val, expected_read_val, msg)

    def test_siu_gpdo(self):
        # Confirm the default GPIO values:
        #   - If OBE is set then the pin_value should match the pgpdo value and
        #     the connected value is ignored
        #   - If OBE is cleared and IBE is set then:
        #       - If connected the pin_value should match the connected value
        #       - If not connected the pin_value is set based on the pullup/down
        #         configuration
        num_pgpdo_regs = len(list(self.emu.siu.registers.pgpdo))

        # For all GPIO pins (if possible) enable GPIO mode, and set output mode.
        # Where possible also disable the default pull ups.
        pcr_range, pcr_size = SIU_PCR
        pcr_cfg = self.get_pcr_defaults()
        ibe_bit   = 0x0100
        obe_bit   = 0x0200
        pa_mask   = 0x1C00
        pull_mask = 0x0003
        for pin in VALID_GPIO_LIST:
            # Disable any external connections (if possible)
            self.emu.siu.disconnectGPIO(pin)

            # Enable the output buffer and ensure that this pin's mode is set to
            # GPIO, and disable any pull ups
            pcr_addr = pcr_range.start + (pin * pcr_size)
            pcr_val = self.emu.readMemValue(pcr_addr, pcr_size)

            # Take the current PCR value and clear WPS & WPE
            pcr_val = pcr_val & ~(pa_mask|pull_mask)

            if pcr_cfg[pin]['pa'] is not None and pcr_cfg[pin]['obe'] is not None:
                pcr_val |= obe_bit | ibe_bit

            # Write the changed PCR value
            self.emu.writeMemValue(pcr_addr, pcr_val, pcr_size)

            self.assertEqual(self.emu.readMemValue(pcr_addr, pcr_size), pcr_val)
            self.assertEqual(self.emu.siu.registers.pcr[pin].wpe, 0)
            self.assertEqual(self.emu.siu.registers.pcr[pin].wps, 0)

            if pcr_cfg[pin]['pa'] is not None and pcr_cfg[pin]['obe'] is not None:
                self.assertEqual(self.emu.siu.registers.pcr[pin].pa, 0)
                self.assertEqual(self.emu.siu.registers.pcr[pin].obe, 1)
                self.assertEqual(self.emu.siu.registers.pcr[pin].ibe, 1)

        # Test writes, even if the GPIO is not a valid output signal this
        # should not produce an error even though it may not result in an
        # output value (which isn't being tested here)
        for info in self.get_gpio_test_info():
            pin = info['pin']
            for test in info['write']:
                # For each GPIO, and each write method:
                # 1. Default all pins to 0
                expected_pgpdo_vals, expected_pin_vals = self.change_pgpdo_state(0)
                pgpdo_vals = [self.emu.siu.registers.pgpdo[i].data for i in range(num_pgpdo_regs)]

                msg = 'testing GPDO(%d)' % pin
                self.assertEqual(pgpdo_vals, expected_pgpdo_vals, msg)
                self.assertEqual(self.emu.siu.pin_value, expected_pin_vals, msg)

                # 2. write a 1 to the pin
                self.write_one_gpio(1, **test)

                # 3. read from all write locations and confirm 1 is read
                for readback_test in info['write']:
                    read_val = self.read_one_gpio(**readback_test)
                    msg = '[0x%08x] GPDO(%d) == 1' % (readback_test['addr'], pin)
                    self.assertEqual(read_val, 1, msg)

                # If this pin is output capable then the value we read should be
                # 1, but if not read 0
                if pcr_cfg[pin]['pa'] is not None and pcr_cfg[pin]['obe'] is not None:
                    test_val = 1
                else:
                    test_val = 0

                # 4. read from all read locations and confirm 1 is read
                for read_test in info['read']:
                    read_val = self.read_one_gpio(**read_test)
                    msg = '[0x%08x] GPDO(%d) == %d' % (read_test['addr'], pin, test_val)
                    self.assertEqual(read_val, test_val, msg)

                # 5. Confirm the PGPDO and external pin values now have the
                # expected pin value set
                expected_pgpdo_vals[info['offset']] |= info['mask']
                msg = 'testing GPDO(%d)' % pin
                pgpdo_vals = [self.emu.siu.registers.pgpdo[i].data for i in range(num_pgpdo_regs)]
                self.assertEqual(pgpdo_vals, expected_pgpdo_vals, msg)

                # The external pin value should only have changed if this GPIO
                # pin is a valid output
                if pcr_cfg[pin]['pa'] is not None and pcr_cfg[pin]['obe'] is not None:
                    expected_pin_vals[info['offset']] |= info['mask']
                self.assertEqual(self.emu.siu.pin_value, expected_pin_vals, msg)

                # Now do the reverse test:
                # 6. Default all pins to 1
                expected_pgpdo_vals, expected_pin_vals = self.change_pgpdo_state(1)
                pgpdo_vals = [self.emu.siu.registers.pgpdo[i].data for i in range(num_pgpdo_regs)]
                self.assertEqual(pgpdo_vals, expected_pgpdo_vals, msg)
                self.assertEqual(self.emu.siu.pin_value, expected_pin_vals, msg)

                # 7. write a 0 to the pin
                self.write_one_gpio(0, **test)

                # 8. read from all write locations and confirm 0 is read
                for readback_test in info['write']:
                    read_val = self.read_one_gpio(**readback_test)
                    msg = '[0x%08x] GPDO(%d) == 0' % (readback_test['addr'], pin)
                    self.assertEqual(read_val, 0, msg)

                # If this pin is not input capable then the value read will
                # always be 0. If it is input and output capable then the value
                # read should be 0, but if not it should read the default pin
                # value of 1.
                if pcr_cfg[pin]['ibe'] is not None:
                    if pcr_cfg[pin]['obe'] is not None:
                        test_val = 0
                    else:
                        test_val = 1
                else:
                    test_val = 0

                # 9. read from all read locations and confirm 1 is read
                for read_test in info['read']:
                    read_val = self.read_one_gpio(**read_test)
                    msg = '[0x%08x] GPDO(%d) == %d' % (read_test['addr'], pin, test_val)
                    self.assertEqual(read_val, test_val, msg)

                # 10. Confirm the PGPDO and external pin values now have the
                # expected pin value set
                expected_pgpdo_vals[info['offset']] &= ~info['mask']
                msg = 'testing GPDO(%d)' % pin
                pgpdo_vals = [self.emu.siu.registers.pgpdo[i].data for i in range(num_pgpdo_regs)]
                self.assertEqual(pgpdo_vals, expected_pgpdo_vals, msg)

                # The external pin value should only have changed if this GPIO
                # pin is a valid output
                if pcr_cfg[pin]['pa'] is not None and pcr_cfg[pin]['obe'] is not None:
                    expected_pin_vals[info['offset']] &= ~info['mask']
                self.assertEqual(self.emu.siu.pin_value, expected_pin_vals, msg)

    def test_siu_mpgpdo_invalid_read(self):
        # Reading from the MPGPDO registers should result in an error
        mpgpdo_range, mpgpdo_size = SIU_MPGPDO
        for addr in mpgpdo_range:
            self.validate_invalid_read(addr, mpgpdo_size)

    def test_siu_mpgpdo(self):
        # Essentially the same test as the PGPDO test above, but instead of
        # using the write_one_gpio() utility to ensure only 1 GPIO is written,
        # the value of each MPGPDO location will be fully set (or cleared) and
        # only the mask will change which GPIO should be modified.

        mpgpdo_range, mpgpdo_size = SIU_MPGPDO
        num_pgpdo_regs = len(list(self.emu.siu.registers.pgpdo))

        # For all GPIO pins (if possible) enable GPIO mode, and set output mode.
        # Where possible also disable the default pull ups.
        pcr_range, pcr_size = SIU_PCR
        pcr_cfg = self.get_pcr_defaults()
        ibe_bit   = 0x0100
        obe_bit   = 0x0200
        pa_mask   = 0x1C00
        pull_mask = 0x0003

        for pin in VALID_GPIO_LIST:
            # Disable any external connections (if possible)
            self.emu.siu.disconnectGPIO(pin)

            # Enable the output buffer and ensure that this pin's mode is set to
            # GPIO, and disable any pull ups
            pcr_addr = pcr_range.start + (pin * pcr_size)
            pcr_val = self.emu.readMemValue(pcr_addr, pcr_size)

            # Take the current PCR value and clear WPS & WPE
            pcr_val = pcr_val & ~(pa_mask|pull_mask)

            if pcr_cfg[pin]['pa'] is not None and pcr_cfg[pin]['obe'] is not None:
                pcr_val |= obe_bit | ibe_bit

            # Write the changed PCR value
            self.emu.writeMemValue(pcr_addr, pcr_val, pcr_size)

            self.assertEqual(self.emu.readMemValue(pcr_addr, pcr_size), pcr_val)
            self.assertEqual(self.emu.siu.registers.pcr[pin].wpe, 0)
            self.assertEqual(self.emu.siu.registers.pcr[pin].wps, 0)
            self.assertEqual(self.emu.siu.registers.pcr[pin].pa, 0)

            if pcr_cfg[pin]['pa'] is not None and pcr_cfg[pin]['obe'] is not None:
                self.assertEqual(self.emu.siu.registers.pcr[pin].obe, 1)
                self.assertEqual(self.emu.siu.registers.pcr[pin].ibe, 1)

        for info in self.get_gpio_test_info():
            pin = info['pin']

            mpgpdo_offset = (pin // 16) * 4
            mpgpdo_addr = mpgpdo_range.start + mpgpdo_offset

            # For each GPIO
            # 1. Default all pins to 0
            expected_pgpdo_vals, expected_pin_vals = self.change_pgpdo_state(0)
            pgpdo_vals = [self.emu.siu.registers.pgpdo[i].data for i in range(num_pgpdo_regs)]

            msg = 'testing GPDO(%d)' % pin
            self.assertEqual(pgpdo_vals, expected_pgpdo_vals, msg)
            self.assertEqual(self.emu.siu.pin_value, expected_pin_vals, msg)

            # 2. Set the mask to only select the current GPIO, but set the value
            # portion of the MPGPDO write to be 0xFFFF
            test_mask = 1 << (15 - (pin % 16) + 16)
            write_value = test_mask | 0xFFFF
            self.emu.writeMemValue(mpgpdo_addr, write_value, mpgpdo_size)

            # 3. read from all write locations and confirm 1 is read
            for readback_test in info['write']:
                read_val = self.read_one_gpio(**readback_test)
                msg = '[0x%08x] GPDO(%d) == %d' % (readback_test['addr'], pin, 1)
                self.assertEqual(read_val, 1, msg)

            # If this pin is output capable then the value we read should be 1,
            # but if not read 0
            if pcr_cfg[pin]['pa'] is not None and pcr_cfg[pin]['obe'] is not None:
                test_val = 1
            else:
                test_val = 0

            # 4. read from all read locations and confirm 1 is read
            for read_test in info['read']:
                read_val = self.read_one_gpio(**read_test)
                msg = '[0x%08x] GPDO(%d) == %d' % (read_test['addr'], pin, test_val)
                self.assertEqual(read_val, test_val, msg)

            # 5. Confirm the PGPDO and external pin values now have the expected
            # pin value set
            expected_pgpdo_vals[info['offset']] |= info['mask']
            msg = 'testing GPDO(%d)' % pin
            pgpdo_vals = [self.emu.siu.registers.pgpdo[i].data for i in range(num_pgpdo_regs)]
            self.assertEqual(pgpdo_vals, expected_pgpdo_vals, msg)

            # The external pin value should only have changed if this GPIO
            # pin is a valid output
            if pcr_cfg[pin]['pa'] is not None and pcr_cfg[pin]['obe'] is not None:
                expected_pin_vals[info['offset']] |= info['mask']
            self.assertEqual(self.emu.siu.pin_value, expected_pin_vals, msg)

            # Now do the reverse test:
            # 6. Default all pins to 1
            expected_pgpdo_vals, expected_pin_vals = self.change_pgpdo_state(1)
            pgpdo_vals = [self.emu.siu.registers.pgpdo[i].data for i in range(num_pgpdo_regs)]
            self.assertEqual(pgpdo_vals, expected_pgpdo_vals, msg)
            self.assertEqual(self.emu.siu.pin_value, expected_pin_vals, msg)

            # 7. Set the mask to only select the current GPIO, but set the value
            # portion of the MPGPDO write to be 0x0000
            write_value = test_mask | 0x0000
            self.emu.writeMemValue(mpgpdo_addr, write_value, mpgpdo_size)

            # 8. read from all write locations and confirm 0 is read
            for readback_test in info['write']:
                read_val = self.read_one_gpio(**readback_test)
                msg = '[0x%08x] GPDO(%d) == 0' % (readback_test['addr'], pin)
                self.assertEqual(read_val, 0, msg)

            # If this pin is not input capable then the value read will always
            # be 0. If it is input and output capable then the value read should
            # be 0, but if not it should read the default pin value of 1.
            if pcr_cfg[pin]['ibe'] is not None:
                if pcr_cfg[pin]['obe'] is not None:
                    test_val = 0
                else:
                    test_val = 1
            else:
                test_val = 0

            # 9. read from all read locations and confirm 1 is read
            for read_test in info['read']:
                read_val = self.read_one_gpio(**read_test)
                msg = '[0x%08x] GPDO(%d) == %d' % (read_test['addr'], pin, test_val)
                self.assertEqual(read_val, test_val, msg)

            # 10. Confirm the PGPDO and external pin values now have the
            # expected pin value set
            expected_pgpdo_vals[info['offset']] &= ~info['mask']
            msg = 'testing GPDO(%d)' % pin
            pgpdo_vals = [self.emu.siu.registers.pgpdo[i].data for i in range(num_pgpdo_regs)]
            self.assertEqual(pgpdo_vals, expected_pgpdo_vals, msg)

            # The external pin value should only have changed if this GPIO
            # pin is a valid output
            if pcr_cfg[pin]['pa'] is not None and pcr_cfg[pin]['obe'] is not None:
                expected_pin_vals[info['offset']] &= ~info['mask']
            self.assertEqual(self.emu.siu.pin_value, expected_pin_vals, msg)

    def test_siu_connected_defaults(self):
        # Confirm the default connected GPIO values
        connected_gpio = {
            # PLLCFG
            #   GPIO208/PLLCFG0: 1
            #   GPIO209/PLLCFG1: 0
            #           PLLCFG2: 1
            208: True,
            209: False,
            210: True,

            # BOOTCFG
            #   GPIO211/BOOTCFG0: 0
            #   GPIO212/BOOTCFG1: 0
            211: False,
            212: False,

            # WKPCFG
            #   GPIO213/WKPCFG: 1
            213: True,
        }

        # Confirm the default connected configuration
        for info in self.get_gpio_test_info():
            pin = info['pin']
            connected_val = connected_gpio.get(pin)
            msg = 'GPIO connected = %s' % connected_val
            self.assertEqual(self.emu.siu._connected[pin], connected_val, msg)

    # Frequency tests

    def test_siu_clocks(self):
        # The f_sys SIU clock is based on the FMPLL output and is divided down
        # based on:
        #   SYSDIV[BYPASS]    (default 0b1)
        #   SYSDIV[SYSCLKDIV] (default 0b00)
        addr, size = SIU_SYSDIV
        self.assertEqual(self.emu.readMemValue(addr, size), 0x00000010)
        self.assertEqual(self.emu.siu.registers.sysdiv.ipclkdiv, 0)
        self.assertEqual(self.emu.siu.registers.sysdiv.bypass, 1)
        self.assertEqual(self.emu.siu.registers.sysdiv.sysclkdiv, 0)

        # Default system clock is 60 MHz
        self.assertEqual(self.emu.siu.f_sys(), 60000000.0)
        self.assertEqual(self.emu.getClock('sys'), 60000000.0)

        # The CPU, Peripheral, and eTPU clocks are derived from the system clock
        # and divided based on the value of SYSDIV[IPCLKDIV]:
        #
        #  IPCLKDIV |   CPU  | Periph |  eTPU
        #  ---------+--------+--------+--------
        #      0b00 |  sys/1 |  sys/2 |  sys/2
        #      0b00 |  sys/1 |  sys/2 |  sys/1
        #      0b10 |     --  Reserved --
        #      0b11 |  sys/1 |  sys/2 |  sys/2
        tests = (
            (0x00000010, 0, 0, 60000000.0, 60000000.0, 30000000.0, 30000000.0),
            (0x00000110, 0, 1, 60000000.0, 60000000.0, 30000000.0, 60000000.0),
            (0x00000310, 0, 3, 60000000.0, 30000000.0, 30000000.0, 30000000.0),
        )
        for sysdiv_val, sysckldiv_val, ipclkdiv_val, sys_freq, cpu_freq, periph_freq, etpu_freq in tests:
            self.emu.writeMemValue(addr, sysdiv_val, size)
            self.assertEqual(self.emu.siu.registers.sysdiv.ipclkdiv, ipclkdiv_val, msg=hex(sysdiv_val))
            self.assertEqual(self.emu.siu.registers.sysdiv.bypass, 1, msg=hex(sysdiv_val))
            self.assertEqual(self.emu.siu.registers.sysdiv.sysclkdiv, sysckldiv_val, msg=hex(sysdiv_val))

            self.assertEqual(self.emu.siu.f_sys(), sys_freq, msg=hex(sysdiv_val))
            self.assertEqual(self.emu.siu.f_cpu(), cpu_freq, msg=hex(sysdiv_val))
            self.assertEqual(self.emu.siu.f_periph(), periph_freq, msg=hex(sysdiv_val))
            self.assertEqual(self.emu.siu.f_etpu(), etpu_freq, msg=hex(sysdiv_val))

            self.assertEqual(self.emu.getClock('sys'), sys_freq, msg=hex(sysdiv_val))
            self.assertEqual(self.emu.getClock('cpu'), cpu_freq, msg=hex(sysdiv_val))
            self.assertEqual(self.emu.getClock('periph'), periph_freq, msg=hex(sysdiv_val))
            self.assertEqual(self.emu.getClock('etpu'), etpu_freq, msg=hex(sysdiv_val))

        # When bypass is disabled the system clock is the FMPLL clock divided
        # down based on SYSDIV[SYSCLKDIV]:
        #   0b00 = divide by 2
        #   0b01 = divide by 4
        #   0b10 = divide by 8
        #   0b11 = divide by 16
        tests = (
            # SYCLKDIV = 0b00
            (0x00000000, 0, 0, 30000000.0, 30000000.0, 15000000.0, 15000000.0),
            (0x00000100, 0, 1, 30000000.0, 30000000.0, 15000000.0, 30000000.0),
            (0x00000300, 0, 3, 30000000.0, 15000000.0, 15000000.0, 15000000.0),

            # SYCLKDIV = 0b01
            (0x00000004, 1, 0, 15000000.0, 15000000.0,  7500000.0,  7500000.0),
            (0x00000104, 1, 1, 15000000.0, 15000000.0,  7500000.0, 15000000.0),
            (0x00000304, 1, 3, 15000000.0,  7500000.0,  7500000.0,  7500000.0),

            # SYCLKDIV = 0b10
            (0x00000008, 2, 0,  7500000.0,  7500000.0,  3750000.0,  3750000.0),
            (0x00000108, 2, 1,  7500000.0,  7500000.0,  3750000.0,  7500000.0),
            (0x00000308, 2, 3,  7500000.0,  3750000.0,  3750000.0,  3750000.0),

            # SYCLKDIV = 0b11
            (0x0000000C, 3, 0,  3750000.0,  3750000.0,  1875000.0,  1875000.0),
            (0x0000010C, 3, 1,  3750000.0,  3750000.0,  1875000.0,  3750000.0),
            (0x0000030C, 3, 3,  3750000.0,  1875000.0,  1875000.0,  1875000.0),
        )
        for sysdiv_val, sysckldiv_val, ipclkdiv_val, sys_freq, cpu_freq, periph_freq, etpu_freq in tests:
            self.emu.writeMemValue(addr, sysdiv_val, size)
            self.assertEqual(self.emu.siu.registers.sysdiv.ipclkdiv, ipclkdiv_val)
            self.assertEqual(self.emu.siu.registers.sysdiv.bypass, 0)
            self.assertEqual(self.emu.siu.registers.sysdiv.sysclkdiv, sysckldiv_val)

            self.assertEqual(self.emu.siu.f_sys(), sys_freq)
            self.assertEqual(self.emu.siu.f_cpu(), cpu_freq)
            self.assertEqual(self.emu.siu.f_periph(), periph_freq)
            self.assertEqual(self.emu.siu.f_etpu(), etpu_freq)

            self.assertEqual(self.emu.getClock('sys'), sys_freq)
            self.assertEqual(self.emu.getClock('cpu'), cpu_freq)
            self.assertEqual(self.emu.getClock('periph'), periph_freq)
            self.assertEqual(self.emu.getClock('etpu'), etpu_freq)

        self.set_sysclk_264mhz()

        # 264 MHz system clock with bypass enabled
        # TODO: an eTPU clock > 200 MHz is invalid. At the moment a warning is
        # printed, this may eventually throw an error.
        tests = (
            # SYCLKDIV = 0b00
            (0x00000010, 0, 0, 264000000.0, 264000000.0, 132000000.0, 132000000.0),
            (0x00000110, 0, 1, 264000000.0, 264000000.0, 132000000.0, 264000000.0),
            (0x00000310, 0, 3, 264000000.0, 132000000.0, 132000000.0, 132000000.0),
        )
        for sysdiv_val, sysckldiv_val, ipclkdiv_val, sys_freq, cpu_freq, periph_freq, etpu_freq in tests:
            self.emu.writeMemValue(addr, sysdiv_val, size)
            self.assertEqual(self.emu.siu.registers.sysdiv.ipclkdiv, ipclkdiv_val)
            self.assertEqual(self.emu.siu.registers.sysdiv.bypass, 1)
            self.assertEqual(self.emu.siu.registers.sysdiv.sysclkdiv, sysckldiv_val)

            self.assertEqual(self.emu.siu.f_sys(), sys_freq)
            self.assertEqual(self.emu.siu.f_cpu(), cpu_freq)
            self.assertEqual(self.emu.siu.f_periph(), periph_freq)
            self.assertEqual(self.emu.siu.f_etpu(), etpu_freq)

            self.assertEqual(self.emu.getClock('sys'), sys_freq)
            self.assertEqual(self.emu.getClock('cpu'), cpu_freq)
            self.assertEqual(self.emu.getClock('periph'), periph_freq)
            self.assertEqual(self.emu.getClock('etpu'), etpu_freq)

        # 264 MHz system clock with bypass disabled
        tests = (
            # SYCLKDIV = 0b00
            (0x00000000, 0, 0, 132000000.0, 132000000.0,  66000000.0,  66000000.0),
            (0x00000100, 0, 1, 132000000.0, 132000000.0,  66000000.0, 132000000.0),
            (0x00000300, 0, 3, 132000000.0,  66000000.0,  66000000.0,  66000000.0),

            # SYCLKDIV = 0b01
            (0x00000004, 1, 0,  66000000.0,  66000000.0,  33000000.0,  33000000.0),
            (0x00000104, 1, 1,  66000000.0,  66000000.0,  33000000.0,  66000000.0),
            (0x00000304, 1, 3,  66000000.0,  33000000.0,  33000000.0,  33000000.0),

            # SYCLKDIV = 0b10
            (0x00000008, 2, 0,  33000000.0,  33000000.0,  16500000.0,  16500000.0),
            (0x00000108, 2, 1,  33000000.0,  33000000.0,  16500000.0,  33000000.0),
            (0x00000308, 2, 3,  33000000.0,  16500000.0,  16500000.0,  16500000.0),

            # SYCLKDIV = 0b11
            (0x0000000C, 3, 0,  16500000.0,  16500000.0,   8250000.0,   8250000.0),
            (0x0000010C, 3, 1,  16500000.0,  16500000.0,   8250000.0,  16500000.0),
            (0x0000030C, 3, 3,  16500000.0,   8250000.0,   8250000.0,   8250000.0),
        )
        for sysdiv_val, sysckldiv_val, ipclkdiv_val, sys_freq, cpu_freq, periph_freq, etpu_freq in tests:
            self.emu.writeMemValue(addr, sysdiv_val, size)
            self.assertEqual(self.emu.siu.registers.sysdiv.ipclkdiv, ipclkdiv_val)
            self.assertEqual(self.emu.siu.registers.sysdiv.bypass, 0)
            self.assertEqual(self.emu.siu.registers.sysdiv.sysclkdiv, sysckldiv_val)

            self.assertEqual(self.emu.siu.f_sys(), sys_freq)
            self.assertEqual(self.emu.siu.f_cpu(), cpu_freq)
            self.assertEqual(self.emu.siu.f_periph(), periph_freq)
            self.assertEqual(self.emu.siu.f_etpu(), etpu_freq)

            self.assertEqual(self.emu.getClock('sys'), sys_freq)
            self.assertEqual(self.emu.getClock('cpu'), cpu_freq)
            self.assertEqual(self.emu.getClock('periph'), periph_freq)
            self.assertEqual(self.emu.getClock('etpu'), etpu_freq)

    def test_siu_output_clk(self):
        # The ENGCLK can be driven from the external clock/crystal or from the
        # peripheral clock depending on:
        #   ECCR[ECSS]   (default 0b0, use periph clock)
        #   ECCR[ENGDIV] (default 0b00010000)
        #
        # CLKOUT is always based on the peripheral clock and is divided down by
        # the value of (ECCR[EBDF] * 2)
        addr, size = SIU_ECCR
        self.assertEqual(self.emu.readMemValue(addr, size), 0x00001001)
        self.assertEqual(self.emu.siu.registers.eccr.engdiv, 0x10)
        self.assertEqual(self.emu.siu.registers.eccr.ecss, 0)
        self.assertEqual(self.emu.siu.registers.eccr.ebts, 0)
        self.assertEqual(self.emu.siu.registers.eccr.ebdf, 1)

        # The default system clock is 60 MHz, and the peripheral clock is 30 MHz
        self.assertEqual(self.emu.siu.f_sys(), 60000000.0)
        self.assertEqual(self.emu.siu.f_periph(), 30000000.0)
        self.assertEqual(self.emu.getClock('sys'), 60000000.0)
        self.assertEqual(self.emu.getClock('periph'), 30000000.0)

        # Based on the default ECCS values ENGCLK will be 937.5 kHz and CLKOUT
        # will be 15 MHz
        self.assertEqual(self.emu.siu.f_engclk(), 937500.0)
        self.assertEqual(self.emu.siu.f_clkout(), 15000000.0)
        self.assertEqual(self.emu.getClock('engclk'), 937500.0)
        self.assertEqual(self.emu.getClock('clkout'), 15000000.0)

        # Set ECCR[ECSS] and confirm that the ENGCLK is the same as the external
        # clock (40 MHz)
        self.emu.writeMemValue(addr, 0x00001081, size)
        self.assertEqual(self.emu.siu.registers.eccr.engdiv, 0x10)
        self.assertEqual(self.emu.siu.registers.eccr.ecss, 1)
        self.assertEqual(self.emu.siu.registers.eccr.ebts, 0)
        self.assertEqual(self.emu.siu.registers.eccr.ebdf, 1)
        self.assertEqual(self.emu.siu.f_engclk(), 40000000.0)
        self.assertEqual(self.emu.getClock('engclk'), 40000000.0)

        # Test a few ECCR[ENGDIV] values
        tests = (
            (0x00000001,   0, 30000000.0),
            (0x00000401,   4,  3750000.0),
            (0x00004001,  64,   234375.0),
            (0x0000FA01, 250,    60000.0),
        )
        for eccr_val, engdiv_val, engclk_freq in tests:
            self.emu.writeMemValue(addr, eccr_val, size)
            self.assertEqual(self.emu.siu.registers.eccr.engdiv, engdiv_val)
            self.assertEqual(self.emu.siu.registers.eccr.ecss, 0)
            self.assertEqual(self.emu.siu.registers.eccr.ebdf, 1)

            self.assertEqual(self.emu.siu.f_engclk(), engclk_freq)
            self.assertEqual(self.emu.siu.f_clkout(), 15000000.0)

            self.assertEqual(self.emu.getClock('engclk'), engclk_freq)
            self.assertEqual(self.emu.getClock('clkout'), 15000000.0)

        # Test the possible ECCR[EBDF] values
        tests = (
            (0x00001000, 0, 30000000.0),
            (0x00001001, 1, 15000000.0),
            (0x00001002, 2, 10000000.0),
            (0x00001003, 3,  7500000.0),
        )
        for eccr_val, ebdf_val, clkout_freq in tests:
            self.emu.writeMemValue(addr, eccr_val, size)
            self.assertEqual(self.emu.siu.registers.eccr.engdiv, 0x10)
            self.assertEqual(self.emu.siu.registers.eccr.ecss, 0)
            self.assertEqual(self.emu.siu.registers.eccr.ebdf, ebdf_val)

            self.assertEqual(self.emu.siu.f_engclk(), 937500.0)
            self.assertEqual(self.emu.siu.f_clkout(), clkout_freq)

            self.assertEqual(self.emu.getClock('engclk'), 937500.0)
            self.assertEqual(self.emu.getClock('clkout'), clkout_freq)

    # Tests for SIU addresses with no emulated functionality

    def test_siu_valid_addrs(self):
        # Confirm that all registers not related to GPIO/PCR functionality
        # All generic registers in SIU are 4-byte aligned
        size = 4
        for addr in VALID_SIU_GENERIC_ADDR_LIST:
            # Confirm default values are 0
            msg = '0x%08x = 0x%08x ?' % (addr, 0)
            self.assertEqual(self.emu.readMemValue(addr, size), 0)

            # should be able to write any value and read it back
            write_val, _ = self.get_random_val(size)

            # Some of the registers being tested have bits that are const so
            # they won't change.  Determine the value that should be read back.
            if addr in SIU_REG_CONST_BITS:
                mask, const = SIU_REG_CONST_BITS[addr]
                read_val = (const & mask) | (write_val & ~mask)
            else:
                read_val = write_val

            self.emu.writeMemValue(addr, write_val, size)
            msg = '[0x%08x] write 0x%08x, read 0x%08x' % (addr, write_val, read_val)
            self.assertEqual(self.emu.readMemValue(addr, size), read_val, msg)

    def test_siu_invalid_addrs(self):
        # Confirm that addresses assigned to SIU that are marked as reserved
        # generate the correct errors for read/write
        size = 4
        for addr in INVALID_SIU_ADDR_LIST:
            self.validate_invalid_addr(addr, size)

    def test_siu_unimplemented_addrs(self):
        # Confirm that the unimplemented register range raises
        # NotImplementedErrors
        addr_range, size = SIU_PERIPH
        for addr in addr_range:
            self.validate_unimplemented_addrs(addr, size)

    def test_siu_external_gpio(self):
        # Ensure that the default GPIO values can be read by all valid input
        # pins

        # For all GPIO pins (if possible) enable GPIO mode, and set input mode.
        # Where possible also disable the default pull ups.
        pcr_range, pcr_size = SIU_PCR
        pcr_cfg = self.get_pcr_defaults()
        ibe_bit   = 0x0100
        pa_mask   = 0x1C00
        pull_mask = 0x0003
        for pin in VALID_GPIO_LIST:
            # Disable any external connections (if possible)
            self.emu.siu.disconnectGPIO(pin)

            # Enable the output buffer and ensure that this pin's mode is set to
            # GPIO, and disable any pull ups
            pcr_addr = pcr_range.start + (pin * pcr_size)
            pcr_val = self.emu.readMemValue(pcr_addr, pcr_size)

            # Take the current PCR value and clear WPS & WPE
            pcr_val = pcr_val & ~(pa_mask|pull_mask)

            if pcr_cfg[pin]['pa'] is not None and pcr_cfg[pin]['ibe'] is not None:
                pcr_val |= ibe_bit

            # Write the changed PCR value
            self.emu.writeMemValue(pcr_addr, pcr_val, pcr_size)

            self.assertEqual(self.emu.readMemValue(pcr_addr, pcr_size), pcr_val)
            self.assertEqual(self.emu.siu.registers.pcr[pin].wpe, 0)
            self.assertEqual(self.emu.siu.registers.pcr[pin].wps, 0)
            self.assertEqual(self.emu.siu.registers.pcr[pin].pa, 0)

            if pcr_cfg[pin]['pa'] is not None and pcr_cfg[pin]['ibe'] is not None:
                self.assertEqual(self.emu.siu.registers.pcr[pin].ibe, 1)
            else:
                self.assertEqual(self.emu.siu.registers.pcr[pin].ibe, 0)

        # Disconnect all GPIO pins
        for pin in GPIO_RANGE:
            self.emu.siu.disconnectGPIO(pin)

        addr_range, size = SIU_PGPDI

        # Now test each external GPIO input
        for info in self.get_gpio_test_info():
            pin = info['pin']

            # Ensure that all GPIO inputs read 0
            num_pgpdi_regs = len(list(self.emu.siu.registers.pgpdi))
            expected_pgpdi_vals = [0x00000000 for i in range(num_pgpdi_regs)]

            msg = 'testing GPDI(%d)' % pin
            pgpdi_vals = [self.emu.siu.registers.pgpdi[i].data for i in range(num_pgpdi_regs)]
            self.assertEqual(pgpdi_vals, expected_pgpdi_vals, msg)

            pgpdi_vals = [self.emu.readMemValue(a, size) for a in addr_range]
            self.assertEqual(pgpdi_vals, expected_pgpdi_vals, msg)

            # Current value should read 0
            for read_test in info['read']:
                read_val = self.read_one_gpio(**read_test)
                msg = '[0x%08x] GPDI(%d) == %d' % (read_test['addr'], pin, read_val)
                self.assertEqual(read_val, 0, msg)

            # Now set the external GPIO value
            self.emu.siu.connectGPIO(pin, 1)

            # If the pin value should change only if this GPIO can act as an
            # input
            if info['input']:
                test_val = 1
                expected_pgpdi_vals[info['offset']] |= info['mask']
            else:
                test_val = 0

            msg = 'testing GPDI(%d)' % pin
            pgpdi_vals = [self.emu.siu.registers.pgpdi[i].data for i in range(num_pgpdi_regs)]
            self.assertEqual(pgpdi_vals, expected_pgpdi_vals, msg)

            pgpdi_vals = [self.emu.readMemValue(a, size) for a in addr_range]
            self.assertEqual(pgpdi_vals, expected_pgpdi_vals, msg)

            for read_test in info['read']:
                read_val = self.read_one_gpio(**read_test)
                msg = '[0x%08x] GPDI(%d) == %d' % (read_test['addr'], pin, read_val)
                self.assertEqual(read_val, test_val, msg)

            # If it was changed, disconnect the GPIO
            if info['input']:
                self.emu.siu.disconnectGPIO(pin)
