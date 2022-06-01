'''
Core:   e200z7
SIMD:   YES
VLE:    YES
Cache:  32kb (16kb I/16kb D)

NMI:    NMI and Critical Interrupt

MMU:    64 entry
MPU:    YES
XBAR:   5x5

NEXUS: 3+

External Bus: YES

3 x SERIAL ports:
    eSCI_A
    eSCI_B
    eSCI_C

4 x FlexCAN Interfaces:
    CAN_A
    CAN_B
    CAN_C
    CAN_D

4 x SPI Interfaces:
    DSPI_A
    DSPI_B
    DSPI_C
    DSPI_D

1 x FlexRAY

System Timers:
    4 x PIT channels
    4 x SWT     (AutoSAR-compliant)
    1 Watchdog

eMIOS   - 32 channels
eTPU    - 64 channels
    eTPU_A
    eTPU_B
    Code Memory - 24kb
    Data Memory -  6kb

Interrupt Controller - 448

ADC - 64 channels
    eQADC_A
    eQADC_B
    TempSensor
    VariableGainAmp
    DecimationFilter    - 8 on eQADC_B
    SensorDiags

PLL - FM
VRC

Low Power Modes:
    Stop Mode
    Slow Mode



Chapter 12
Core (e200z7) Overview

The MPC5674F is a dual-issue, 32-bit Power Book E compliant design with 64-bit general purpose
registers (GPRs). Power Book E floating-point instructions are not supported in hardware, but are trapped
and may be emulated by software.

An Embedded Floating-point APU is provided to support real-time single-precision embedded numerics
operations using the general-purpose registers.

A second generation Signal Processing Extension APU is provided to support real-time SIMD fixed point
and single-precision, embedded numerics operations using the general-purpose registers. All arithmetic
instructions that execute in the core operate on data in the general purpose registers (GPRs). The GPRs are
64-bits in order to support vector instructions defined by the SPE2 APU. These instructions operate on
8-bit, 16-bit or 32-bit data types, and deliver vector and scalar results.

In addition to the base Power Book E instruction set support, the MPC5674F core also implements the
VLE (variable-length encoding) technology, providing improved code density. The VLE technology is
further documented in "Power VLE Definition, Version 1.03", a separate document.

The MPC5674F processor integrates a pair of integer execution units, a branch control unit, instruction
fetch unit and load/store unit, and a multi-ported register file capable of sustaining six read and three write
operations per clock. Most integer instructions execute in a single clock cycle. Branch target prefetching
is performed by the branch unit to allow single-cycle branches in many cases.

The MPC5674F contains a 16KB Instruction Cache, a 16KB Data Cache, as well as a Memory
Management Unit. A Nexus Class 3+ module is also integrated.


mpc5674 is reponsible for defining:
    * Signal description
    * resets
    * power management controller
    * FMPLL
    * system integration unit
    * system information module
    * BAM - boot assist module
    * INTC - interrupts and interrupt controller
    * SRAM - static ram
    * FLASH memory array and control
    * AMBA (XBAR) - crossbar switch
    * PBRIDGE - peripheral bridge
    * MPU - memory protection unit
    * ECSM - error correction status module
    * SWT - software watchdog timer
    * STM - system timer module
    * PIT_RTI - Periodic Interrupt Timer
    * eDMA - enhanced Direct Memory Access controller
    * FLEXRAY - FlexRay comms controller
    * eMIOS200 - enhanced Modular I/O subsystem
    * FlexCAN module
    * DSPI - Deserial Serial Peripheral Interface
    * eSCI - enhanced Serial Comms Interface
    * EQADC - Enhanced Queued Analog to Digical Converter
    * Decimation Filter
    * eTPU2 - enhanced Time Processing Unit
    * EBI - External Bus Interface
    * NDI - Nexus Development Interface
    * JTAGC - IEEE 1149.1 Test Access Port Controller
    * Device Performance Optimization
    * Temperature Sensor
'''
import sys
import time
import shutil
import os.path
import argparse
import threading
import traceback

import logging
logger = logging.getLogger(__name__)

import envi
import vstruct
import envi.bits as e_bits
import envi.memory as e_mem
import envi.archs.ppc.regs as ppc_regs
import envi.archs.ppc.const as ppc_const
import vivisect.const as viv_const
import vivisect.impemu.monitor as viv_imp_monitor

from . import project
from . import e200z7
from .intc_exc import AlignmentException, MceWriteBusError, MceDataReadBusError

# Peripherals
from .peripherals.bam import BAM
from .peripherals.flash import FLASH, FlashDevice, getFlashOffsets
from .peripherals.swt import SWT
from .peripherals.siu import SIU
from .peripherals.fmpll import FMPLL
from .peripherals.flexcan import FlexCAN
from .peripherals.intc import INTC
from .peripherals.dspi import DSPI
from .peripherals.sim import SIM
from .peripherals.eqadc import EQADC
from .peripherals.decfilt import DECFILT
from .peripherals.ebi import EBI
from .peripherals.ecsm import ECSM
from .peripherals.xbar import XBAR
from .peripherals.pbridge import PBRIDGE


__all__ = [
    'MPC5674_Emulator',
    'MPC5674_monitor',
]


###  DEBUGGING ONLY:  Emulation Monitor
from envi.archs.ppc.regs import REG_LR, REG_XER, REG_CR, REG_CTR
class MPC5674_monitor(viv_imp_monitor.AnalysisMonitor):
    def __init__(self, vw, fva=0):
        viv_imp_monitor.AnalysisMonitor.__init__(self, vw, fva)
        self.vas = []
        self.ops = []
        self.ophist = {}
        self.calls = []
        self.funccalls = {}
        self.spraccess = []
        self.curfunc = 0
        self.curfuncdata = {}
        self.path = [0]
        self.level = 0

    def prehook(self, emu, op, starteip):
        #print("prehook: 0x%x: %r" % (starteip, op))
        if any(emu.getOperAddr(op, i) == 0x40010214 for i in range(len(op.opers))):
            repropers = ', '.join('[0x%x] 0x%x' % (emu.getOperAddr(op, i), emu.getOperValue(op, i)) if op.opers[i].isDeref() \
                    else hex(emu.getOperValue(op, i)) for i in range(len(op.opers)))
            print("===============0x40010214 accessed!!!===== 0x%x:  %r (%r)" % (op.va, op, repropers))
            #raw_input("===============0x40010214 accessed!!!===== 0x%x:  %r (%r)" % (op.va, op, repropers))

    '''
        if op.iflags & envi.IF_CALL:
            print("cAll!")
            self.calls.append((op, emu.getProgramCounter()))

        if op.mnem in (ppc_const.INS_MTSPR, ppc_const.INS_MFSPR):
            self.spraccess.append(op)
    '''
    def posthook(self, emu, op, endeip):
        #print("posthook: 0x%x: %r" % (starteip, op))
        # store all opcodes

        #self.ops.append(op)

        # store opcode in the correct function container
        cfdata = self.curfuncdata.get(self.curfunc)
        if cfdata is None:
            cfdata = {'ops': []}
            self.curfuncdata[self.curfunc] = cfdata

        if op.va not in cfdata['ops']:
            cfdata['ops'].append(op.va)

        # track instruction counts
        ophist = self.ophist.get(op.mnem, 0)
        ophist += 1
        self.ophist[op.mnem] = ophist

        if op.iflags & envi.IF_CALL:
            self.calls.append((self.curfunc, op.va, endeip))

            count = self.funccalls.get(endeip, 0) + 1
            self.funccalls[endeip] = count

            self.curfunc = endeip
            self.path.append(endeip)
            self.level += 1
            gap = '  ' * self.level + str(self.level)
            print(gap + " ====>> CALL  0x%x -> 0x%x (0x%x, 0x%x, 0x%x, 0x%x, 0x%x)" % (
                op.va, endeip,
                emu.getRegister(ppc_regs.REG_R3),
                emu.getRegister(ppc_regs.REG_R4),
                emu.getRegister(ppc_regs.REG_R5),
                emu.getRegister(ppc_regs.REG_R6),
                emu.getRegister(ppc_regs.REG_R7)))

        elif op.iflags & envi.IF_RET:
            gap = '  ' * self.level + str(self.level)
            print(gap + " <<==== RET  0x%x <- 0x%x (0x%x)" % (endeip, op.va, emu.getRegister(ppc_regs.REG_R3)))
            self.level -= 1
            self.path.pop()
            self.curfunc = self.path[-1]

        if op.opcode in (ppc_const.INS_MTSPR, ppc_const.INS_MFSPR):
            isCommon = False
            for oper in op.opers:
                if oper.isReg() and oper.reg in (REG_LR, REG_XER, REG_CR, REG_CTR):
                    isCommon = True
            if not isCommon:
                logger.warning('SPR access: 0x%x: %r   (0x%x, 0x%x)', op.va, op, \
                        emu.getOperValue(op, 0), \
                        emu.getOperValue(op, 1))
                self.spraccess.append((op, emu.getOperValue(op, 0), emu.getOperValue(op, 1)))

    def apicall(self, emu, op, pc, api, argv):
        print("call!")
        self.calls.append((op, pc, api, argv))

################################# END EmuMon

DEFAULT_FLASH_FILENAME = 'cm2350.flash'


class MPC5674_Emulator(e200z7.PPC_e200z7, project.VivProject):
    # MPC5674-specific project configuration values
    defconfig = {
        'project': {
            'MPC5674': {
                'SIU': {
                    'pllcfg': 0b101,
                    'bootcfg': 0b00,
                    'wkpcfg': 0b1,
                },
                'FMPLL': {
                    'extal': 40000000,
                },
                'FLASH': {
                    'fwFilename': None,
                    'baseaddr': 0,
                    'shadowAFilename': None,
                    'shadowAOffset': 0,
                    'shadowBFilename': None,
                    'shadowBOffset': 0,
                    'backup': 'backup.flash',
                },
                'SRAM': {
                    # SRAM size depends on the specific MPC5674 part in use
                    'size': 0,
                    'addr': 0x40000000,
                },
                'FlexCAN_A': {
                    'host': None,
                    'port': None,
                },
                'FlexCAN_B': {
                    'host': None,
                    'port': None,
                },
                'FlexCAN_C': {
                    'host': None,
                    'port': None,
                },
                'FlexCAN_D': {
                    'host': None,
                    'port': None,
                },
                'DSPI_A': {
                    'host': None,
                    'port': None,
                },
                'DSPI_B': {
                    'host': None,
                    'port': None,
                },
                'DSPI_C': {
                    'host': None,
                    'port': None,
                },
                'DSPI_D': {
                    'host': None,
                    'port': None,
                },
                'eQADC_A': {
                    'host': None,
                    'port': None,
                },
                'eQADC_B': {
                    'host': None,
                    'port': None,
                },
            }
        }
    }

    docconfig = {
        'project': {
            'MPC5674': {
                'SIU': {
                    'pllcfg': 'Default state of the MPC5674F PLLCFG (GPIO 208 & 209) pins',
                    'bootcfg': 'Default state of the MPC5674F BOOTCFG (GPIO 211 & 212) pins',
                    'wkpcfg': 'Default state of the MPC5674F WKPCFG (GPIO 213) pin',
                },
                'FMPLL': {
                    'extal': 'External oscillator frequency',
                },
                'FLASH': {
                    'fwFilename': 'File that contains the initial contents of internal flash',
                    'baseaddr': 'Memory offset to load the contents of fwFilename into',
                    'shadowAFilename': 'File that contains the initial contents of shadow flash A',
                    'shadowAOffset': 'Memory offset to load the contents of shadowAFilename into',
                    'shadowBFilename': 'File that contains the initial contents of shadow flash B',
                    'shadowBOffset': 'Memory offset to load the contents of shadowBFilename into',
                    'backup': 'File used to save the contents of flash',
                },
                'SRAM': {
                    'size': 'Amount of SRAM available (differs depending on specific MPC5674 version)',
                    'addr': 'Physical address of SRAM',
                },
                'FlexCAN_A': {
                    'host': 'Host IP address for FlexCAN_A IO server',
                    'port': 'Host TCP port for FlexCAN_A IO server',
                },
                'FlexCAN_B': {
                    'host': 'Host IP address for FlexCAN_B IO server',
                    'port': 'Host TCP port for FlexCAN_B IO server',
                },
                'FlexCAN_C': {
                    'host': 'Host IP address for FlexCAN_C IO server',
                    'port': 'Host TCP port for FlexCAN_C IO server'
                },
                'FlexCAN_D': {
                    'host': 'Host IP address for DSPI_D IO server',
                    'port': 'Host TCP port for DSPI_D IO server',
                },
                'DSPI_A': {
                    'host': 'Host IP address for DSPI_A IO server',
                    'port': 'Host TCP port for DSPI_A IO server',
                },
                'DSPI_B': {
                    'host': 'Host IP address for DSPI_B IO server',
                    'port': 'Host TCP port for DSPI_B IO server',
                },
                'DSPI_C': {
                    'host': 'Host IP address for DSPI_C IO server',
                    'port': 'Host TCP port for DSPI_C IO server'
                },
                'DSPI_D': {
                    'host': 'Host IP address for DSPI_D IO server',
                    'port': 'Host TCP port for DSPI_D IO server',
                },
                'eQADC_A': {
                    'host': 'Host IP address for DSPI_D IO server',
                    'port': 'Host TCP port for DSPI_D IO server',
                },
                'eQADC_B': {
                    'host': 'Host IP address for DSPI_D IO server',
                    'port': 'Host TCP port for DSPI_D IO server',
                },
            }
        }
    }

    # static mapping of "flash" vs "ram" memory regions for this device
    flash_mmaps = ((0x00000000, 0x00400000),)
    ram_mmaps   = ((0x40000000, 0x40040000),)

    def __init__(self, defconfig=None, docconfig=None, args=None):
        # Before initializing the VivProject, add any MPC5674-specific options
        exename = os.path.basename(sys.modules['__main__'].__file__)
        parser = argparse.ArgumentParser(prog=exename)
        parser.add_argument('-I', '--init-flash', action='store_true',
                            help='Copy binary flash image to configuration directory (-c)')
        parser.add_argument('flash_image', nargs='?',
                            help='Binary flash image to load in the emulator')

        # Open up the workspace and read the project configuration
        project.VivProject.__init__(self)
        vw, args = self.open_project_config(defconfig, docconfig, args, parser)

        del parser

        # the self.vw attribute will get created when the e200z7 class calls the
        # workspace emulator initializer.
        e200z7.PPC_e200z7.__init__(self, vw)

        # Now that the standard options have been parsed process anything
        # leftover
        self._process_args(args)

        # The backup file is assumed to be located in the "project directory"
        self.flash = FLASH(self)

        # eTPU2 has a complex memory map like flash
        #self.tpu = ETPU2(self)

        ########################################

        self.flash.setAddr(self, FlashDevice.FLASH_MAIN,     0x00000000)
        self.flash.setAddr(self, FlashDevice.FLASH_B_SHADOW, 0x00EFC000)
        self.flash.setAddr(self, FlashDevice.FLASH_A_SHADOW, 0x00FFC000)

        # SRAM 0x40000000 - 0x40040000 will be initialized by the reset()
        # function

        self.pbridge = (
            PBRIDGE('PBRIDGE_A', self, 0xC3F00000),
            PBRIDGE('PBRIDGE_B', self, 0xFFF00000),
        )

        ########################################
        # PBRIDGE_A
        ########################################

        self.fmpll = FMPLL(self, 0xC3F80000)
        self.ebi = EBI(self, 0xC3F84000)

        # Now the FLASH configuration regions
        self.flash.setAddr(self, FlashDevice.FLASH_A_CONFIG, 0xC3F88000)
        self.flash.setAddr(self, FlashDevice.FLASH_B_CONFIG, 0xC3F8C000)

        self.siu = SIU(self, 0xC3F90000)
        #self.mios = EMIOS(self, 0xC3FA0000)
        #self.pmc = PMC(self, 0xC3FBC000)
        #self.tpu.setAddr(self, ETPU2Device.Registers, 0xC3FC0000)
        #self.tpu.setAddr(self, ETPU2Device.ParamRAM,0xC3FC8000)
        #self.tpu.setAddr(self, ETPU2Device.ParamRAMMirror, 0xC3FCC000)
        #self.tpu.setAddr(self, ETPU2Device.CodeRAM, 0xC3FD0000)
        #self.pit = PIT_RTI(self, 0xC3FF0000)

        ########################################
        # PBRIDGE_B
        ########################################

        self.xbar = XBAR(self, 0xFFF04000)
        # self.mpu = MPU(self, 0xFFF10000)
        self.swt = SWT(self, 0xFFF38000)
        # self.stm = STM(self, 0xFFF3C000)
        self.ecsm = ECSM(self, 0xFFF40000)
        #self.dma = (
        #        EDMA('eDMA_A', self, 0xFFF44000),
        #        EDMA('eDMA_B', self, 0xFFF54000),
        #)
        self.intc = INTC(self, 0xFFF48000)
        self.eqadc = (
            EQADC('eQADC_A', self, 0xFFF80000),
            EQADC('eQADC_B', self, 0xFFF84000),
        )
        self.decfilt = (
            DECFILT('DECFILT_A', self, 0xFFF88000),
            DECFILT('DECFILT_B', self, 0xFFF88800),
            DECFILT('DECFILT_C', self, 0xFFF89000),
            DECFILT('DECFILT_D', self, 0xFFF89800),
            DECFILT('DECFILT_E', self, 0xFFF8A000),
            DECFILT('DECFILT_F', self, 0xFFF8A800),
            DECFILT('DECFILT_G', self, 0xFFF8B000),
            DECFILT('DECFILT_H', self, 0xFFF8B800),
        )
        self.dspi = (
            DSPI('DSPI_A', self, 0xFFF90000),
            DSPI('DSPI_B', self, 0xFFF94000),
            DSPI('DSPI_C', self, 0xFFF98000),
            DSPI('DSPI_D', self, 0xFFF9C000),
        )
        #self.sci = (
        #    ESCI('eSCI_A', self, 0xFFFB0000),
        #    ESCI('eSCI_B', self, 0xFFFB4000),
        #    ESCI('eSCI_C', self, 0xFFFB8000),
        #)
        self.can = (
            FlexCAN('FlexCAN_A', self, 0xFFFC0000),
            FlexCAN('FlexCAN_B', self, 0xFFFC4000),
            FlexCAN('FlexCAN_C', self, 0xFFFC8000),
            FlexCAN('FlexCAN_D', self, 0xFFFCC000),
        )
        #self.flexray = FLEXRAY(self, 0xFFFE0000)
        self.sim = SIM(self, 0xFFFEC000)
        self.bam = BAM(self, 0xFFFFC000)

        ########################################

        # Firmware must be loaded before the peripherals are initialized or BAM
        # won't find a valid address, so if the FLASH peripheral was not able to
        # restore flash contents from the backup load the initial firmware now
        self.loadInitialFirmware()

        # Complete initialization of the e200z7 core
        self.init_core()

        return

        # TODO: Initialize stack memory base address, taints, etc.

        if hasattr(self, 'vw') and self.vw is not None:
            # This attaches the same MMIO class functions and objects to the
            # vivisect workspace (I think this should work?)
            self.vw._map_defs = self._map_defs
            for mva, mmaxva, _, _ in self._map_defs:
                msize = mmaxva - mva
                self.vw.locmap.initMapLookup(mva, msize)
                self.vw.blockmap.initMapLookup(mva, msize)

            import types
            emuself = self

            # Replace the standard vivisect functions with emulator-specific
            # ones
            def _parseOpcode(self, va, arch=envi.ARCH_PPC_E32, skipcache=False):
                return emuself.parseOpcode(va, skipcache=skipcache)
            self.vw.parseOpcode = types.MethodType(_parseOpcode, self.vw)

            def _getEmulator(self, **kwargs):
                return emuself
            self.vw.getEmulator = types.MethodType(_getEmulator, self.vw)

            # To use the MPC5674_Emulator class as a workspace emulator for
            # analysis we need to set up the expected stack analysis attributes
            # used by the WorkspaceEmulator class assume that the stack is near
            # the end of SRAM from 0x40030000 to 0x40040000
            self.stack_map_mask = 0xFFFF0000
            self.stack_map_base = 0x40030000
            self.stack_map_top  = 0x40040000
            self.stack_pointer  = 0x4003FFFC

            def _getFileByVa(self, va):
                segtup = self.getSegment(va)
                if segtup is None:
                    return 'CM2350'
                return segtup[viv_const.SEG_FNAME]
            self.vw.getFileByVa = types.MethodType(_getFileByVa, self.vw)

            # Redirect the normal Vivisect Workspace's MemoryObject functions to
            # this class instance's functions, except translate the PPC
            # exceptions into exceptions that vivisect understands better
            def _writeMemory(self, va, bytez):
                try:
                    return emuself.writeMemory(va, bytez)
                except (MceWriteBusError, MceDataReadBusError, AlignmentException) as exc:
                    raise envi.SegmentationViolation('Bad Memory Access: 0x%x', va) from exc
            self.vw.writeMemory = types.MethodType(_writeMemory, self.vw)

            def _readMemory(self, va, size):
                try:
                    return emuself.readMemory(va, size)
                except (MceWriteBusError, MceDataReadBusError, AlignmentException) as exc:
                    raise envi.SegmentationViolation('Bad Memory Access: 0x%x', va) from exc
            self.vw.readMemory = types.MethodType(_readMemory, self.vw)

            def _getByteDef(self, va):
                try:
                    return emuself.getByteDef(va)
                except (MceWriteBusError, MceDataReadBusError, AlignmentException) as exc:
                    raise envi.SegmentationViolation('Bad Memory Access: 0x%x', va) from exc
            self.vw.getByteDef = types.MethodType(_getByteDef, self.vw)

    def _process_args(self, args):
        """
        Indicate that the supplied file can be used as an initial flash image if
        - The file is large enough to contain the main and shadow flash A & B
        OR
        - The file is large enough to contain the only main flash

        If the file is a valid initial flash image:
        1. Copy the file to the project config flash filename
        2. Update the workspace configuration to indicate if main flash and
           shadow flash data, or only main flash will be loaded from the file
        """
        # Track if this is a new configuration directory or not (needed by
        # init_flash)
        if args.config_dir != False and not os.path.isdir(self.vw.vivhome):
            new_config = True
            # Save the initial config
            logger.critical('Creating new config directory %s', self.vw.vivhome)
            self.vw.config.saveConfigFile()
        else:
            new_config = False

        # Use the EnviConfig.cfginfo attribute directly so we can overwrite the
        # running configuration values for a specific run of the emulator. Such
        # as a overwriting a valid 'fwFilename' path temporarily when the
        # "--init-flash" argument is provided but no "flash_image" is provided
        # (indicating an empty firmware should be initialized).
        cfg = self.vw.config.project.MPC5674.FLASH.cfginfo
        orig_flash_file = cfg['fwFilename']
        cfg_flash_file = self.get_project_path(DEFAULT_FLASH_FILENAME)

        mode = self.vw.getTransMeta("ProjectMode")
        updated_config = getFlashOffsets(args.flash_image)

        if args.config_dir != False and args.init_flash:
            # Update the configuration in the workspace with the values
            for key, value in updated_config.items():
                cfg[key] = value

            if cfg['fwFilename'] is not None:
                if not new_config and orig_flash_file == cfg_flash_file and os.path.exists(cfg_flash_file):
                    # If the flash image is valid, and this is NOT a new
                    # configuration print a message indicating that the existing
                    # flash image is being overwritten
                    logger.critical('Overwriting flash image in existing config directory %s with %s', self.vw.vivhome, args.flash_image)
                else:
                    logger.warning('Copying flash image (%s) into config (%s)', args.flash_image, cfg_flash_file)

                # If this Copy the specified file to the correct location
                shutil.copyfile(cfg['fwFilename'], cfg_flash_file)

                # Update the configuration with the name of the saved flash
                # image file
                cfg['fwFilename'] = self.get_project_path(DEFAULT_FLASH_FILENAME)

                if updated_config['shadowAFilename'] is not None:
                    cfg['shadowAFilename'] = self.get_project_path(DEFAULT_FLASH_FILENAME)

                if updated_config['shadowBFilename'] is not None:
                    cfg['shadowBFilename'] = self.get_project_path(DEFAULT_FLASH_FILENAME)
            else:
                # If there is no initial flash image, but there used to be (and
                # this is an existing config) show a warning and delete the
                # previous flash file
                if not new_config and os.path.exists(cfg_flash_file):
                    logger.critical('No flash file provided: deleting existing flash image from config directory %s', self.vw.vivhome)
                    os.unlink(self.get_project_path(DEFAULT_FLASH_FILENAME))

            # If init_flash was specified save the config file now
            logger.critical('Saving configuration file %s', self.vw.config.filename)
            self.vw.config.saveConfigFile()

        else:
            # Since this is just a temporary run copy any valid flash
            # filename (and offset) config values from the updated config to
            # the running configuration.
            if updated_config['fwFilename'] is not None:
                cfg['fwFilename'] = updated_config['fwFilename']
                cfg['baseaddr'] = updated_config['baseaddr']
            if updated_config['shadowAFilename'] is not None:
                cfg['shadowAFilename'] = updated_config['shadowAFilename']
                cfg['shadowAOffset'] = updated_config['shadowAOffset']
            if updated_config['shadowBFilename'] is not None:
                cfg['shadowBFilename'] = updated_config['shadowBFilename']
                cfg['shadowBOffset'] = updated_config['shadowBOffset']

        # If no firmware file is identified print an error now
        if not cfg['fwFilename'] and mode != 'test':
            logger.critical('No flash file provided, unable to load flash image')

    def reset_ram(self):
        # Clear or initialize SRAM and external RAM
        size = self.vw.config.project.MPC5674.SRAM.size
        addr = self.vw.config.project.MPC5674.SRAM.addr
        if size and addr:
            for i in range(len(self._map_defs)):
                mva, mmaxva, mmap, _ = self._map_defs[i]
                if mva == addr:
                    logger.debug("reset: clearing 0x%x bytes SRAM at BASE: 0x%x", size, addr)
                    # Each map entry is a tuple so we must replace the entire
                    # entry
                    self._map_defs[i] = (mva, mmaxva, mmap, b'\0' * size)
                    break
            else:
               # The initial SRAM memory block must be created
                logger.debug("reset: Initializing 0x%x bytes SRAM at BASE: 0x%x", size, addr)
                self.addMemoryMap(addr, e_mem.MM_RWX, 'SRAM', b'\0' * size)

    def reset(self):
        # Clear RAM
        self.reset_ram()

        # Reset the e200z7 core
        self.reset_core()

    def loadInitialFirmware(self):
        '''
        load firmware into the emulator
        '''
        # Get the FLASH configuration info as a dict
        cfg = self.vw.config.project.MPC5674.FLASH

        # Assume that the filenames are files in the project directory

        if cfg['fwFilename']:
            # First check if the file can be found without adding the project
            # path. Otherwise assume it is intended to be a filename path
            # relative to the project path.
            if os.path.exists(cfg['fwFilename']):
                path = cfg['fwFilename']
            else:
                path = self.get_project_path(cfg['fwFilename'])
            if os.path.exists(path):
                logger.info("Loading Firmware Blob from %r @ 0x%x", path, cfg['baseaddr'])
                self.flash.load(FlashDevice.FLASH_MAIN, path, cfg['baseaddr'])
            else:
                logger.critical("Starting emulator without valid firmware, please update config: %s" % self.vw.vivhome)

        if cfg['shadowAFilename']:
            # First check if the file can be found without adding the project
            # path. Otherwise assume it is intended to be a filename path
            # relative to the project path.
            if os.path.exists(cfg['shadowAFilename']):
                path = cfg['shadowAFilename']
            else:
                path = self.get_project_path(cfg['shadowAFilename'])
            if os.path.exists(path):
                logger.info("Loading Shadow A Blob from %r @ 0x%x", path, cfg['shadowAOffset'])
                self.flash.load(FlashDevice.FLASH_A_SHADOW, path, cfg['shadowAOffset'])

        if cfg['shadowBFilename']:
            # First check if the file can be found without adding the project
            # path. Otherwise assume it is intended to be a filename path
            # relative to the project path.
            if os.path.exists(cfg['shadowBFilename']):
                path = cfg['shadowBFilename']
            else:
                path = self.get_project_path(cfg['shadowBFilename'])
            if os.path.exists(path):
                logger.info("Loading Shadow B Blob from %r @ 0x%x", path, cfg['shadowBOffset'])
                self.flash.load(FlashDevice.FLASH_B_SHADOW, path, cfg['shadowBOffset'])

        # Indicate that initial loading of flash memory from files is complete
        backup_file = self.vw.config.project.MPC5674.FLASH.backup
        if backup_file:
            self.flash.load_complete(self.get_project_path(backup_file))
        else:
            self.flash.load_complete()

    def init_core(self):
        self.reset_ram()
        e200z7.PPC_e200z7.init_core(self)


### special register hardware interfacing
# hook particular registers such that they don't store data, but rather interface to a virtual device
# justification: what register(s) needs this?




####### test case speed-tests
class int_test:
    static_var = False
    def __init__(self):
        self.instance_var = False
        self.int_list = []
        self.int_list_lock = threading.Lock()
        self.intq = queue.Queue()

    def do_tests(self, count=10000000):
        for item in dir(self):
            if not item.startswith('test_'):
                continue
            results = getattr(self, item)(count=count)


    def test_static(self, count=10000000):
        st = time.time()
        while count > 0:
            if self.static_var:
                print("woops")
            count -= 1
        et = time.time()
        return et-st

    def test_instance(self, count=10000000):
        st = time.time()
        while count > 0:
            if self.instance_var:
                print("woops")
            count -= 1
        et = time.time()
        return et-st

    def test_listlen(self, count=10000000):
        st = time.time()
        while count > 0:
            if len(self.int_list):
                print("woops")
            count -= 1
        et = time.time()
        return et-st

    def test_lockedlistlen(self, count=10000000):
        st = time.time()
        while count > 0:
            with self.int_list_lock:
                if len(self.int_list):
                    print("woops")
            count -= 1
        et = time.time()
        return et-st

    def test_queue0(self, count=10000000):
        st = time.time()
        while count > 0:
            if not self.intq.empty():
                print("woops")
            count -= 1
        et = time.time()
        return et-st

    def test_queue1(self, count=10000000):
        st = time.time()
        while count > 0:
            try:
                thing = self.intq.get_nowait()
            except queue.Empty:
                pass
            count -= 1
        et = time.time()
        return et-st

