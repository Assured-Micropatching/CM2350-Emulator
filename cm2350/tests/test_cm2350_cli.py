import os
import copy
import glob
import json
import random
import shutil
import struct
import hashlib
import os.path
import unittest

import vivisect
import envi.archs.ppc.regs as eapr
import envi.archs.ppc.const as eapc

from .. import CM2350

import logging
logger = logging.getLogger(__name__)


USERDIR         = os.path.expanduser('~')

# There are two possible binary sizes that are considered valid, for just the
# primary flash the file size should be 0x40_0000, for a binary that has both
# flash and shadow flash the file size should be 0x40_8000.
SIZE_FLASH = 0x40_0000
SIZE_FULL  = 0x40_8000

# Project name to use so a user's .AMP doesn't get overwritten during these
# tests
PROJECT_NAME    = 'CM2350_TEST_TMP'

# Unfortunately because of how the CLI arguments and options are parsed a
# workspace must be initialized first before the project.name can be modified
# through normal option parsing.  So instead directly modify the project.name in
# the CM2350 defconfig class attribute
CM2350.defconfig['project']['name'] = PROJECT_NAME

# Directory and file paths used in these tests
DEFAULT_CONFIG       = os.path.join(USERDIR, '.' + PROJECT_NAME)
EXISTING_CONFIG      = os.path.join(USERDIR, '.CM2350_TEST_EXISTING_CONFIG')
NEW_CONFIG           = os.path.join(USERDIR, '.CM2350_TEST_NEW_CONFIG')

FLASH_FILENAME       = 'cm2350.flash'
BACKUP_FILENAME      = 'backup.flash'
CONFIG_FILENAME      = 'viv.json'

EXISTING_CONFIG_BIN  = os.path.join(EXISTING_CONFIG, FLASH_FILENAME)
NEW_BINARY_FULL      = 'CM2350_TEST_all.bin'
NEW_BINARY           = 'CM2350_TEST_flash.bin'
INVALID_BINARY_SMALL = 'CM2350_TEST_invalid_small.bin'
INVALID_BINARY_LARGE = 'CM2350_TEST_invalid_large.bin'

# To make it easier to look up which binary will be used for different
# configuration directories
DEFAULT_BINS = {
    EXISTING_CONFIG: EXISTING_CONFIG_BIN,
}

# A summary of the directories and files created and used during these tests.
TEST_DIRS = (
    DEFAULT_CONFIG,
    EXISTING_CONFIG,
    NEW_CONFIG,
)

# Standalone files that won't be cleaned up when the TEST_DIRS are removed
TEST_FILES = (
    EXISTING_CONFIG_BIN,
    NEW_BINARY_FULL,
    NEW_BINARY,
    INVALID_BINARY_SMALL,
    INVALID_BINARY_LARGE,
)

# For the binaries that are going to be created use these sizes and RCHW
# addresses.
#   - The full sized binaries will have hash values attached to this dictionary
#   during module setup.
#   - The test binaries that do not cover shadow flash will have a partial hash
#   object that can be copied and the remainder of the hash calculated as needed
#   depending on the tests.
#   - Invalid binaries will have a None has value.
RCHW_VALUE = 0x005A_FFFF
TEST_BIN_VALUES = {
    None: {
        'size': 0,
        'rchw_addr': None,
        'entry_addr': 0x0000_0000,
        'rchw': None,
        'pc': 0x0000_0000,
        'hash': None,
    },
    EXISTING_CONFIG_BIN: {
        'size': SIZE_FULL,
        'rchw_addr': 0x0002_0000,
        'entry_addr': 0x0002_1234,
        'rchw': 0x0002_0000,
        'pc': 0x0002_1234,
        'hash': hashlib.md5(),
    },
    NEW_BINARY_FULL: {
        'size': SIZE_FULL,
        'rchw_addr': 0x0001_C000,
        'entry_addr': 0x0003_0000,
        'rchw': 0x0001_C000,
        'pc': 0x0003_0000,
        'hash': hashlib.md5(),
    },
    NEW_BINARY: {
        'size': SIZE_FLASH,
        'rchw_addr': 0x0001_0000,
        'entry_addr': 0x0001_FFF0,
        'rchw': 0x0001_0000,
        'pc': 0x0001_FFF0,
        'hash': hashlib.md5(),
    },
    INVALID_BINARY_SMALL: {
        'size': random.randrange(0x0000_4000, SIZE_FLASH),
        'rchw_addr': 0x0000_0000,
        'entry_addr': 0x0000_0200,
        'rchw': None,
        'pc': 0x0000_0000,
        'hash': None,
    },
    INVALID_BINARY_LARGE: {
        'size': SIZE_FULL + 0x8000,
        'rchw_addr': 0x0003_0000,
        'entry_addr': 0x0000_0200,
        'rchw': None,
        'pc': 0x0000_0000,
        'hash': None,
    },

    # Lastly, create some files in the current directory with the same name as
    # the default flash image file to ensure that the correct file is being read
    # make it valid so if it is used it can easily be identified
    FLASH_FILENAME: {
        'size': SIZE_FULL,
        'rchw_addr': 0x0000_4000,
        'entry_addr': 0x0000_0004,
        'rchw': 0x0000_4000,
        'pc': 0x0000_0004,
        'hash': hashlib.md5(),
    }
}

# Expected hash value for empty (default) flash contents
DEFAULT_FLASH_HASH = bytes.fromhex('a318f882cb81e45ae7f94e859070aaf8')

# The values expected in the default Shadow flash B and A regions, used to
# calculate expected hash values
DEFAULT_SHADOW_FLASH_B = b'\xFF' * 0x4000
DEFAULT_SHADOW_FLASH_A = \
        b'\xFF' * 0x3DD8 + \
        b'\xFE\xED\xFA\xCE\xCA\xFE\xBE\xEF\x55\xAA\x55\xAA' + \
        b'\xFF' * 0x021C


def dict_merge(a, b):
    result = copy.deepcopy(a)

    for key, value in b.items():
        if isinstance(value, dict):
            result[key] = dict_merge(result.get(key, {}), value)
        else:
            result[key] = copy.deepcopy(b[key])

    return result


# Default project configuration using the DEFAULT_CONFIG path, so it has an
# empty firmware configuration.
CM2350_DEFAULT_CONFIG = {
    'viv': {
        'parsers': {
            'blob': {
                'arch': 'ppc32-embedded',
                'bigend': True,
                'baseaddr': 0,
            },
            'ihex': {
                'arch': 'ppc32-embedded',
                'bigend': True,
                'offset': 0,
            },
            'srec': {
                'arch': 'ppc32-embedded',
                'bigend': True,
                'offset': 0,
            }
        }
    },

    'project': {
        'name': PROJECT_NAME,
        'platform': 'CM2350',
        'arch': 'ppc32-embedded',
        'bigend': True,
        'format': 'blob',
        'CM2350': { 'p89': 1, 'p90': 0, 'p91': 1, 'p92': 0},
        'MPC5674': {
            'SIU': {'pllcfg': 5, 'bootcfg': 0, 'wkpcfg': 1},
            'FMPLL': {'extal': 40000000},
            'FLASH': {
                'fwFilename': None,
                'baseaddr': 0,
                'shadowAFilename': None,
                'shadowAOffset': 0,
                'shadowBFilename': None,
                'shadowBOffset': 0,
                'backup': 'backup.flash'
            },
            'SRAM': {'addr': 1073741824, 'size': 262144, 'standby_size': 32768},
            'FlexCAN_A': {'host': None, 'port': None},
            'FlexCAN_B': {'host': None, 'port': None},
            'FlexCAN_C': {'host': None, 'port': None},
            'FlexCAN_D': {'host': None, 'port': None},
            'DSPI_A': {'host': None, 'port': None},
            'DSPI_B': {'host': None, 'port': None},
            'DSPI_C': {'host': None, 'port': None},
            'DSPI_D': {'host': None, 'port': None},
            'eQADC_A': {'host': None, 'port': None},
            'eQADC_B': {'host': None, 'port': None},
        }
    },
}

# Merge the CM2350 default config with the vivisect default config
DEFAULT_PROJECT_CONFIG = dict_merge(vivisect.defconfig, CM2350_DEFAULT_CONFIG)


def get_config(config, flash_cfg=None):
    """
    Just a simple utility to get a default config dictionary but helps to
    ensure it is a copy so the original default doesn't get modified.

    If the flash_cfg parameter is supplied then the FLASH configuration values
    will be overridden by the values in the flash_cfg dict.
    """
    cfg = copy.deepcopy(DEFAULT_PROJECT_CONFIG)
    # If this is the existing config then add the default flash file
    if config == EXISTING_CONFIG:
        cfg['project']['MPC5674']['FLASH']['fwFilename'] = os.path.join(config, FLASH_FILENAME)
        cfg['project']['MPC5674']['FLASH']['shadowAFilename'] = os.path.join(config, FLASH_FILENAME)
        cfg['project']['MPC5674']['FLASH']['shadowAOffset'] = 4210688
        cfg['project']['MPC5674']['FLASH']['shadowBFilename'] = os.path.join(config, FLASH_FILENAME)
        cfg['project']['MPC5674']['FLASH']['shadowBOffset'] = 4194304

    if flash_cfg:
        # Update the config with the supplied FLASH configuration values
        for key, value in flash_cfg.items():
            cfg['project']['MPC5674']['FLASH'][key] = value

    return cfg


def get_bytes(size):
    """
    Returns random bytes object of the size specified.
    """
    if hasattr(random, 'randbytes'):
        return random.randbytes(size)
    else:
        # os.urandom() could be used here but I am a little bit concerned about
        # the amount of data it would use, on some Linux versions urandom()
        # might stall if it thinks it "doesn't have enough randomness"
        return bytes(random.getrandbits(8) for i in range(size))


def get_cm2350_args(*args):
    """
    Utility to return the CLI arguments to use when creating a CM2350() object.
    Return the args to use.  The standard args for the CLI testing are:
        - verboseness based on environment LOG_LEVEL variable
        - MODE == "test"
    Any arguments supplied as parameters are also added to the argument list
    """
    test_args = ['-m', 'test']
    if os.environ.get('LOG_LEVEL', 'INFO') == 'DEBUG':
        test_args.append('-vvv')
    return test_args + list(args)


def get_expected_hash(binary, default_binary=None):
    #print('CALCULATING HASH for %s (default=%s)' % (binary, default_binary))
    invalid = False

    if TEST_BIN_VALUES[binary]['size'] == SIZE_FULL:
        # If the binary's size contains both primary and shadow flash,
        # then use the TEST_BIN_VALUE
        hash_value = TEST_BIN_VALUES[binary]['hash'].digest()
        #print('Using %s hash: %s' % (binary, hash_value.hex()))

    elif TEST_BIN_VALUES[binary]['size'] == SIZE_FLASH:
        # Use the binary's hash as a starting point and then add in the
        # contents of the configuration's default binary (if one exists), or
        # the default shadow flash states if the config does not have a
        # default binary.
        test_hash = TEST_BIN_VALUES[binary]['hash'].copy()
        #print('Using %s ' % binary, end='')
        if default_binary is not None:
            #print('+ %s hash: ' % default_binary, end='')
            with open(default_binary, 'rb') as f:
                f.seek(SIZE_FLASH)
                test_hash.update(f.read())
        else:
            #print('+ DEFAULTS hash: ', end='')
            # Supplement with the default shadow A and B contents
            test_hash.update(DEFAULT_SHADOW_FLASH_B)
            test_hash.update(DEFAULT_SHADOW_FLASH_A)
        hash_value = test_hash.digest()
        #print(hash_value.hex())

    else:
        invalid = True

        # Otherwise this binary should be considered invalid and the default
        # values for flash will be used
        hash_value = DEFAULT_FLASH_HASH
        #print('Using default hash: %s' % (hash_value.hex()))

    return invalid, hash_value


def setUpModule():
    # There are a few things needed for these tests:
    # 1. An existing config with a "binary"
    if os.path.exists(EXISTING_CONFIG):
        # If the config directory already exists, we don't know what state the
        # contents are in so remove the directory and re-create it
        logger.debug('"existing config" folder %s exists, cleaning it now', EXISTING_CONFIG)
        shutil.rmtree(EXISTING_CONFIG)
    logger.debug('Creating "existing config" folder %s', EXISTING_CONFIG)
    os.mkdir(EXISTING_CONFIG)

    # Create the configuration file for the existing config
    json_filename = os.path.join(EXISTING_CONFIG, CONFIG_FILENAME)
    logger.debug('creating %s for existing config', json_filename)
    with open(json_filename, 'w') as f:
        f.write(json.dumps(get_config(EXISTING_CONFIG)))

    # 2. Various standalone binaries
    for testfile in TEST_FILES:
        with open(testfile, 'w+b') as f:
            logger.debug('creating test file %s', testfile)
            # Write random data
            bin_values = TEST_BIN_VALUES[testfile]
            f.write(get_bytes(bin_values['size']))

            # Now add in the RCHW value
            f.seek(bin_values['rchw_addr'])
            f.write(struct.pack('>II', RCHW_VALUE, bin_values['entry_addr']))

            # If the file's hash entry is not None, calculate the hash of the
            # entire file
            if bin_values['hash'] is not None:
                f.seek(0)
                bin_values['hash'].update(f.read())
                #print('Created %s with initial hash of %s' % (testfile, bin_values['hash'].digest().hex()))


def tearDownModule():
    # Remove any files or directories created during this test including the
    # default project name config directory if one was created and not cleaned
    # up (like if a test failure caused an early abort)
    for testdir in TEST_DIRS:
        if os.path.exists(testdir):
            if os.path.isdir(testdir):
                logger.debug('removing test directory %s', testdir)
                shutil.rmtree(testdir)
            else:
                logger.error('WARNING: test directory %s is not a directory! not removing' % testdir)
        else:
            logger.debug('test directory %s not present, skipping', testdir)

    for testfile in TEST_FILES:
        if os.path.exists(testfile):
            logger.debug('removing test file %s', testfile)
            os.unlink(testfile)
        else:
            logger.debug('test file %s not present, skipping', testfile)


class CM2350_CLI(unittest.TestCase):
    def do_config_test(self, flash_cfg, config=None, binary=None, init_flash=False):
        """
        Utility to do a configuration test, each test works in essentially the
        same way, with a few different options:

        Parameters:
            flash_cfg: dict (required)
                - the expected FLASH configuration values are difficult to
                  calculate automatically, so they must be supplied here

            config: path (optional)
                - if None, then DEFAULT_CONFIG is used, otherwise
                - if not default then the "-c" CLI param is provided
                - identifies the default path where the config files are

            binary: path (optional)
                - if None then the file in DEFAULT_BINS is used if there is an
                  entry for the supplied config
                - used to calculate expected hash values

            init_flash: bool (optional)
                - if True then config's flash file and config to be updated
                - if False then the config's flash file and configuration should
                  remain unchanged, but the emulator's hash should reflect the
                  contents of the "binary" param
        """
        self.maxDiff = None
        #############################
        # Setup

        # The configuration will only already exist if it is EXISTING_CONFIG
        if config == EXISTING_CONFIG:
            exists = True
        else:
            exists = False

        args = []
        # If the config is not None (and not DEFAULT_CONFIG) add a
        # "--config-dir" argument
        if config is not None and config != DEFAULT_CONFIG:
            args.extend(['--config-dir', config])
        # if the init flash param is provided add "--init-flash"
        if init_flash:
            args.append('--init-flash')

            # If init_flash is set when the config is EXISTING_CONFIG make a
            # backup of the flash file and config that can be restored after the
            # test is done
            if config == EXISTING_CONFIG:
                shutil.copyfile(EXISTING_CONFIG_BIN, EXISTING_CONFIG_BIN + '.bak')
                config_file = os.path.join(EXISTING_CONFIG, CONFIG_FILENAME)
                shutil.copyfile(config_file, config_file + '.bak')

        # Add a binary if provided
        if binary is not None:
            args.append(binary)

        # Default configuration
        if config is None:
            config = DEFAULT_CONFIG
        default_binary = DEFAULT_BINS.get(config)

        # If init_flash is set then there is no default or backup binary to use
        # flash sections from
        if init_flash:
            invalid_bin, hash_value = get_expected_hash(binary)

            # Determine whether or not a cm2350.flash file should exist at the
            # end of the test.  Since this branch is only taken if init_flash is
            # set
            #   - if an initial flash image was supplied and is not invalid
            config_flash_file_exists = not invalid_bin

            # Force invalid_bin to be False so that the empty binary value is
            # used
            invalid_bin = False

        else:
            invalid_bin, hash_value = get_expected_hash(binary, default_binary)
            # If the primary binary is invalid, use the default (if it exists)
            if invalid_bin and default_binary is not None:
                _, hash_value = get_expected_hash(default_binary)

            # Determine whether or not a cm2350.flash file should exist at the
            # end of the test.  Since this branch is only taken if init_flash is
            # false the cm2350.flash file should only exist if config ==
            # EXISTING_CONFIG (the exists flag is set)
            config_flash_file_exists = exists

        # Get a dictionary of the expected standard configuration values for the
        # selected config
        cfg = get_config(config, flash_cfg)

        # A backup.flash file is only created if data is loaded from a flash
        # file.  The filename should be "backup.flash.<hash>.
        if cfg['project']['MPC5674']['FLASH']['fwFilename'] is None:
            backup_file = None
        else:
            backup_file = os.path.join(config, '%s.%s' % (BACKUP_FILENAME, hash_value.hex()))

        #############################
        # Start testing now

        self.assertEqual(os.path.exists(config), exists)
        ecu = CM2350(get_cm2350_args(*args))
        self.assertEqual(ecu.emu.vw.config.getConfigPrimitive(), cfg)
        self.assertEqual(ecu.emu.flash.get_hash().hex(), hash_value.hex())

        if invalid_bin:
            # Use the default binary's RCHW and PC
            self.assertEqual(ecu.emu.bam.rchw_addr, TEST_BIN_VALUES[default_binary]['rchw'])
            self.assertEqual(ecu.emu.getProgramCounter(), TEST_BIN_VALUES[default_binary]['pc'])
        else:
            self.assertEqual(ecu.emu.bam.rchw_addr, TEST_BIN_VALUES[binary]['rchw'])
            self.assertEqual(ecu.emu.getProgramCounter(), TEST_BIN_VALUES[binary]['pc'])
        self.assertTrue(os.path.isdir(config))

        # Confirm that the configuration json file is as expected:
        json_cfg_file = os.path.join(config, CONFIG_FILENAME)
        self.assertTrue(os.path.exists(json_cfg_file))
        with open(json_cfg_file, 'r') as f:
            json_cfg = json.loads(f.read())
            if init_flash:
                self.assertEqual(json_cfg, cfg)
            else:
                self.assertEqual(json_cfg, get_config(config))

        self.assertEqual(os.path.exists(os.path.join(config, FLASH_FILENAME)), config_flash_file_exists)

        # Check for the backup file
        backup_exists = backup_file is not None
        backup_file_glob = glob.glob(os.path.join(config, '%s.*' % BACKUP_FILENAME))
        if not backup_exists:
            self.assertEqual(backup_file_glob, [])
        else:
            # The backup files should always be the size of MAIN flash and both
            # shadow regions
            for bfile in backup_file_glob:
                self.assertEqual(os.stat(bfile).st_size, 0x408000, msg=bfile)
            self.assertEqual(backup_file_glob, [backup_file])

            # Lastly confirm that the hash of the backup file matches the
            # expected hash_value (because the contents of flash should not have
            # changed since it was initialized)
            with open(backup_file, 'rb') as f:
                self.assertEqual(hashlib.md5(f.read()).digest().hex(), hash_value.hex())

        #############################
        # Cleanup

        # to gracefully clean up the ECU resources call halt() before deleting
        # the object
        ecu.shutdown()
        del ecu

        # Test is completed, remove the configuration directory (unless config
        # == EXISTING_CONFIG)
        if not exists:
            shutil.rmtree(config)
        elif backup_exists:
            # If the configuration shouldn't be deleted, cleanup the backup file
            os.unlink(backup_file)

        # If the config was EXISTING_CONFIG and init_flash was specified restore
        # the original test flash and config files
        if init_flash and config == EXISTING_CONFIG:
            shutil.move(EXISTING_CONFIG_BIN + '.bak', EXISTING_CONFIG_BIN)
            config_file = os.path.join(EXISTING_CONFIG, CONFIG_FILENAME)
            shutil.move(config_file + '.bak', config_file)

    ########## DEFAULT CONFIG ##########

    def test_default_config(self):
        flash_cfg = {
            'fwFilename': None,
            'baseaddr': 0,
            'shadowAFilename': None,
            'shadowAOffset': 0,
            'shadowBFilename': None,
            'shadowBOffset': 0,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg)

    def test_default_config_new_bin_full(self):
        flash_cfg = {
            'fwFilename': NEW_BINARY_FULL,
            'baseaddr': 0,
            'shadowAFilename': NEW_BINARY_FULL,
            'shadowAOffset': 0x404000,
            'shadowBFilename': NEW_BINARY_FULL,
            'shadowBOffset': 0x400000,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, binary=NEW_BINARY_FULL)

    def test_default_config_new_bin(self):
        flash_cfg = {
            'fwFilename': NEW_BINARY,
            'baseaddr': 0,
            'shadowAFilename': None,
            'shadowAOffset': 0,
            'shadowBFilename': None,
            'shadowBOffset': 0,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, binary=NEW_BINARY)

    def test_default_config_invalid_bin_small(self):
        flash_cfg = {
            'fwFilename': None,
            'baseaddr': 0,
            'shadowAFilename': None,
            'shadowAOffset': 0,
            'shadowBFilename': None,
            'shadowBOffset': 0,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, binary=INVALID_BINARY_SMALL)

    def test_default_config_invalid_bin_large(self):
        flash_cfg = {
            'fwFilename': None,
            'baseaddr': 0,
            'shadowAFilename': None,
            'shadowAOffset': 0,
            'shadowBFilename': None,
            'shadowBOffset': 0,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, binary=INVALID_BINARY_LARGE)

    def test_default_config_new_bin_full_init(self):
        flash_cfg = {
            'fwFilename': os.path.join(DEFAULT_CONFIG, FLASH_FILENAME),
            'baseaddr': 0,
            'shadowAFilename': os.path.join(DEFAULT_CONFIG, FLASH_FILENAME),
            'shadowAOffset': 0x404000,
            'shadowBFilename': os.path.join(DEFAULT_CONFIG, FLASH_FILENAME),
            'shadowBOffset': 0x400000,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, binary=NEW_BINARY_FULL, init_flash=True)

    def test_default_config_new_bin_init(self):
        flash_cfg = {
            'fwFilename': os.path.join(DEFAULT_CONFIG, FLASH_FILENAME),
            'baseaddr': 0,
            'shadowAFilename': None,
            'shadowAOffset': 0,
            'shadowBFilename': None,
            'shadowBOffset': 0,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, binary=NEW_BINARY, init_flash=True)

    def test_default_config_invalid_bin_small_init(self):
        flash_cfg = {
            'fwFilename': None,
            'baseaddr': 0,
            'shadowAFilename': None,
            'shadowAOffset': 0,
            'shadowBFilename': None,
            'shadowBOffset': 0,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, binary=INVALID_BINARY_SMALL, init_flash=True)

    def test_default_config_invalid_bin_large_init(self):
        flash_cfg = {
            'fwFilename': None,
            'baseaddr': 0,
            'shadowAFilename': None,
            'shadowAOffset': 0,
            'shadowBFilename': None,
            'shadowBOffset': 0,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, binary=INVALID_BINARY_LARGE, init_flash=True)

    def test_default_config_init_no_file (self):
        flash_cfg = {
            'fwFilename': None,
            'baseaddr': 0,
            'shadowAFilename': None,
            'shadowAOffset': 0,
            'shadowBFilename': None,
            'shadowBOffset': 0,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, init_flash=True)

    ########## EXISTING CONFIG ##########
    def test_existing_config(self):
        flash_cfg = {
            'fwFilename': os.path.join(EXISTING_CONFIG, FLASH_FILENAME),
            'baseaddr': 0,
            'shadowAFilename': os.path.join(EXISTING_CONFIG, FLASH_FILENAME),
            'shadowAOffset': 0x404000,
            'shadowBFilename': os.path.join(EXISTING_CONFIG, FLASH_FILENAME),
            'shadowBOffset': 0x400000,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, config=EXISTING_CONFIG)

    def test_existing_config_new_bin_full(self):
        flash_cfg = {
            'fwFilename': NEW_BINARY_FULL,
            'baseaddr': 0,
            'shadowAFilename': NEW_BINARY_FULL,
            'shadowAOffset': 0x404000,
            'shadowBFilename': NEW_BINARY_FULL,
            'shadowBOffset': 0x400000,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, config=EXISTING_CONFIG, binary=NEW_BINARY_FULL)

    def test_existing_config_new_bin(self):
        flash_cfg = {
            'fwFilename': NEW_BINARY,
            'baseaddr': 0,
            'shadowAFilename': os.path.join(EXISTING_CONFIG, FLASH_FILENAME),
            'shadowAOffset': 0x404000,
            'shadowBFilename': os.path.join(EXISTING_CONFIG, FLASH_FILENAME),
            'shadowBOffset': 0x400000,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, config=EXISTING_CONFIG, binary=NEW_BINARY)

    def test_existing_config_invalid_bin_small(self):
        flash_cfg = {
            'fwFilename': os.path.join(EXISTING_CONFIG, FLASH_FILENAME),
            'baseaddr': 0,
            'shadowAFilename': os.path.join(EXISTING_CONFIG, FLASH_FILENAME),
            'shadowAOffset': 0x404000,
            'shadowBFilename': os.path.join(EXISTING_CONFIG, FLASH_FILENAME),
            'shadowBOffset': 0x400000,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, config=EXISTING_CONFIG, binary=INVALID_BINARY_SMALL)

    def test_existing_config_invalid_bin_large(self):
        flash_cfg = {
            'fwFilename': os.path.join(EXISTING_CONFIG, FLASH_FILENAME),
            'baseaddr': 0,
            'shadowAFilename': os.path.join(EXISTING_CONFIG, FLASH_FILENAME),
            'shadowAOffset': 0x404000,
            'shadowBFilename': os.path.join(EXISTING_CONFIG, FLASH_FILENAME),
            'shadowBOffset': 0x400000,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, config=EXISTING_CONFIG, binary=INVALID_BINARY_LARGE)

    def test_existing_config_new_bin_full_init(self):
        flash_cfg = {
            'fwFilename': os.path.join(EXISTING_CONFIG, FLASH_FILENAME),
            'baseaddr': 0,
            'shadowAFilename': os.path.join(EXISTING_CONFIG, FLASH_FILENAME),
            'shadowAOffset': 0x404000,
            'shadowBFilename': os.path.join(EXISTING_CONFIG, FLASH_FILENAME),
            'shadowBOffset': 0x400000,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, config=EXISTING_CONFIG, binary=NEW_BINARY_FULL, init_flash=True)

    def test_existing_config_new_bin_init(self):
        flash_cfg = {
            'fwFilename': os.path.join(EXISTING_CONFIG, FLASH_FILENAME),
            'baseaddr': 0,
            'shadowAFilename': None,
            'shadowAOffset': 0,
            'shadowBFilename': None,
            'shadowBOffset': 0,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, config=EXISTING_CONFIG, binary=NEW_BINARY, init_flash=True)

    def test_existing_config_invalid_bin_small_init(self):
        flash_cfg = {
            'fwFilename': None,
            'baseaddr': 0,
            'shadowAFilename': None,
            'shadowAOffset': 0,
            'shadowBFilename': None,
            'shadowBOffset': 0,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, config=EXISTING_CONFIG, binary=INVALID_BINARY_SMALL, init_flash=True)

    def test_existing_config_invalid_bin_large_init(self):
        flash_cfg = {
            'fwFilename': None,
            'baseaddr': 0,
            'shadowAFilename': None,
            'shadowAOffset': 0,
            'shadowBFilename': None,
            'shadowBOffset': 0,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, config=EXISTING_CONFIG, binary=INVALID_BINARY_LARGE, init_flash=True)

    def test_existing_config_init_no_file(self):
        flash_cfg = {
            'fwFilename': None,
            'baseaddr': 0,
            'shadowAFilename': None,
            'shadowAOffset': 0,
            'shadowBFilename': None,
            'shadowBOffset': 0,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, config=EXISTING_CONFIG, init_flash=True)

    ########## NEW CONFIG ##########

    def test_new_config(self):
        flash_cfg = {
            'fwFilename': None,
            'baseaddr': 0,
            'shadowAFilename': None,
            'shadowAOffset': 0,
            'shadowBFilename': None,
            'shadowBOffset': 0,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, config=NEW_CONFIG)

    def test_new_config_new_bin_full(self):
        flash_cfg = {
            'fwFilename': NEW_BINARY_FULL,
            'baseaddr': 0,
            'shadowAFilename': NEW_BINARY_FULL,
            'shadowAOffset': 0x404000,
            'shadowBFilename': NEW_BINARY_FULL,
            'shadowBOffset': 0x400000,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, config=NEW_CONFIG, binary=NEW_BINARY_FULL)

    def test_new_config_new_bin(self):
        flash_cfg = {
            'fwFilename': NEW_BINARY,
            'baseaddr': 0,
            'shadowAFilename': None,
            'shadowAOffset': 0,
            'shadowBFilename': None,
            'shadowBOffset': 0,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, config=NEW_CONFIG, binary=NEW_BINARY)

    def test_new_config_invalid_bin_small(self):
        flash_cfg = {
            'fwFilename': None,
            'baseaddr': 0,
            'shadowAFilename': None,
            'shadowAOffset': 0,
            'shadowBFilename': None,
            'shadowBOffset': 0,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, config=NEW_CONFIG, binary=INVALID_BINARY_SMALL)

    def test_new_config_invalid_bin_large(self):
        flash_cfg = {
            'fwFilename': None,
            'baseaddr': 0,
            'shadowAFilename': None,
            'shadowAOffset': 0,
            'shadowBFilename': None,
            'shadowBOffset': 0,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, config=NEW_CONFIG, binary=INVALID_BINARY_LARGE)

    def test_new_config_new_bin_full_init(self):
        flash_cfg = {
            'fwFilename': os.path.join(NEW_CONFIG, FLASH_FILENAME),
            'baseaddr': 0,
            'shadowAFilename': os.path.join(NEW_CONFIG, FLASH_FILENAME),
            'shadowAOffset': 0x404000,
            'shadowBFilename': os.path.join(NEW_CONFIG, FLASH_FILENAME),
            'shadowBOffset': 0x400000,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, config=NEW_CONFIG, binary=NEW_BINARY_FULL, init_flash=True)

    def test_new_config_new_bin_init(self):
        flash_cfg = {
            'fwFilename': os.path.join(NEW_CONFIG, FLASH_FILENAME),
            'baseaddr': 0,
            'shadowAFilename': None,
            'shadowAOffset': 0,
            'shadowBFilename': None,
            'shadowBOffset': 0,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, config=NEW_CONFIG, binary=NEW_BINARY, init_flash=True)

    def test_new_config_invalid_bin_small_init(self):
        flash_cfg = {
            'fwFilename': None,
            'baseaddr': 0,
            'shadowAFilename': None,
            'shadowAOffset': 0,
            'shadowBFilename': None,
            'shadowBOffset': 0,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, config=NEW_CONFIG, binary=INVALID_BINARY_SMALL, init_flash=True)

    def test_new_config_invalid_bin_large_init(self):
        flash_cfg = {
            'fwFilename': None,
            'baseaddr': 0,
            'shadowAFilename': None,
            'shadowAOffset': 0,
            'shadowBFilename': None,
            'shadowBOffset': 0,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, config=NEW_CONFIG, binary=INVALID_BINARY_LARGE, init_flash=True)

    def test_new_config_init_no_file(self):
        flash_cfg = {
            'fwFilename': None,
            'baseaddr': 0,
            'shadowAFilename': None,
            'shadowAOffset': 0,
            'shadowBFilename': None,
            'shadowBOffset': 0,
            'backup': 'backup.flash'
        }
        self.do_config_test(flash_cfg, config=NEW_CONFIG, init_flash=True)
