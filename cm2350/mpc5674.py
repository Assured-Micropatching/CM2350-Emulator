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
    * eQADC - Enhanced Queued Analog to Digical Converter
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
import envi.memory as e_mem
import envi.archs.ppc.regs as ppc_regs
import envi.archs.ppc.const as ppc_const
import vivisect.const as viv_const
import vivisect.impemu.monitor as viv_imp_monitor

from . import project, e200z7, intc_exc, mmio

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
from .peripherals.eqadc import eQADC
from .peripherals.decfilt import DECFILT
from .peripherals.ebi import EBI
from .peripherals.ecsm import ECSM
from .peripherals.xbar import XBAR
from .peripherals.pbridge import PBRIDGE
from .peripherals.edma import eDMA
from .peripherals.etpu2 import eTPU2
from .peripherals.emios200 import eMIOS200
from .peripherals.esci import eSCI
from .peripherals.pit import PIT


__all__ = [
    'MPC5674_Emulator',
    'MPC5674_monitor',
]


###  DEBUGGING ONLY:  Emulation Monitor
COMMON_SPRs = (ppc_regs.REG_LR, ppc_regs.REG_XER, ppc_regs.REG_CR, ppc_regs.REG_CTR)
class MPC5674_monitor(viv_imp_monitor.AnalysisMonitor):
    def __init__(self, vw, fva=0):
        viv_imp_monitor.AnalysisMonitor.__init__(self, vw, fva)
        #self.vas = []
        #self.ops = []
        self.ophist = {}
        self.calls = []
        self.funccalls = {}
        self.curfuncdata = {}
        #self.spraccess = []

        self.int_context = None

        # All dependant on the current interrupt context
        self.curfunc = {None: 0}
        self.path = {None: [0]}
        self.level = {None: 0}

    def posthook(self, emu, op, endeip):
        #print("posthook: 0x%x: %r" % (starteip, op))
        # store all opcodes

        #self.ops.append(op)

        # track instruction counts
        self.ophist[op.mnem] = self.ophist.get(op.mnem, 0) + 1

        # Check if we've entered or exited an interrupt context self.int_context
        if emu.mcu_intc.stack:
            cur_context = emu.mcu_intc.stack[0].prio
        else:
            cur_context = None

        # Watch for resets
        if op.va == emu.bam.rchw.entry_point:
            self.curfunc = {None: 0}
            self.path = {None: [0]}
            self.level = {None: 0}

            print("%s%d ###### RESET  0x%x" % (
                '  '*self.level[self.int_context], self.level[self.int_context], op.va))

        if cur_context != self.int_context:
            if cur_context not in self.curfunc:
                # if the current context isn't in the current function set yet,
                # then this is a new interrupt context.  In this case the
                # instruction passed into this hook is incorrect.  Get the
                # actual instruction executed from the emulator
                interrupted_op = op
                op = emu._cur_instr[0]

                # Start new context-based entries for this interrupt handler
                self.curfunc[cur_context] = op.va
                self.path[cur_context] = [op.va]
                self.level[cur_context] = 1

            # If an RFI was just executed, remove the old interrupt context
            if op.iflags & ppc_const.IF_RFI:
                print("%s%d ****** 0x%x RFI    <- 0x%x" % (
                    '  '*self.level[self.int_context], self.level[self.int_context], endeip, op.va))

                # Clean up the interrupt context path
                del self.curfunc[self.int_context]
                del self.path[self.int_context]
                del self.level[self.int_context]

            # If we are not in the "normal" context and an RFI was not just
            # executed, the first instruction of an interrupt handler was
            # executed.
            if cur_context is not None and not op.iflags & ppc_const.IF_RFI:
                # The first instruction of the interrupt handler is the address
                # of the instruction that was just executed
                count = self.funccalls.get(op.va, 0) + 1
                self.funccalls[op.va] = count

                if isinstance(emu.mcu_intc.stack[0], intc_exc.MachineCheckException):
                    xrr0 = emu.getRegister(ppc_regs.REG_MCSRR0)
                    xrr1 = emu.getRegister(ppc_regs.REG_MCSRR1)
                    xrr0_name = 'MCSRR0'
                    xrr1_name = 'MCSRR1'
                elif isinstance(emu.mcu_intc.stack[0], (intc_exc.StandardPrioException, intc_exc.MachineCheckPrioException)):
                    # standard and non-MCE machine check priority level
                    # exceptions use SRR0/SRR1
                    xrr0 = emu.getRegister(ppc_regs.REG_SRR0)
                    xrr1 = emu.getRegister(ppc_regs.REG_SRR1)
                    xrr0_name = 'SRR0'
                    xrr1_name = 'SRR1'
                elif isinstance(emu.mcu_intc.stack[0], intc_exc.CriticalPrioException):
                    xrr0 = emu.getRegister(ppc_regs.REG_CSRR0)
                    xrr1 = emu.getRegister(ppc_regs.REG_CSRR1)
                    xrr0_name = 'CSRR0'
                    xrr1_name = 'CSRR1'
                else:
                    raise Exception('Unknown exception context %s' % repr(cur_context))

                print("%s%d ****** 0x%x  INT  0x%x -> 0x%x (MSR: 0x%x  MCAR: 0x%x  ESR: 0x%x  %s: 0x%x  %s: 0x%x" % (
                    '  '*self.level[cur_context], self.level[cur_context],
                    xrr0, op.va, endeip, emu.getRegister(ppc_regs.REG_MSR),
                    emu.getRegister(ppc_regs.REG_MCAR), emu.getRegister(ppc_regs.REG_ESR),
                    xrr0_name, xrr0, xrr1_name, xrr1))

            self.int_context = cur_context

        # store opcode in the correct function container
        cfdata = self.curfuncdata.get(self.curfunc[self.int_context])
        if cfdata is None:
            cfdata = {'ops': []}
            self.curfuncdata[self.curfunc[self.int_context]] = cfdata

        if op.va not in cfdata['ops']:
            cfdata['ops'].append(op.va)

        if op.iflags & envi.IF_CALL:
            self.calls.append((self.curfunc[self.int_context], op.va, endeip))

            count = self.funccalls.get(endeip, 0) + 1
            self.funccalls[endeip] = count

            self.curfunc[self.int_context] = endeip
            self.path[self.int_context].append(endeip)
            self.level[self.int_context] += 1
            print("%s%d ====>> CALL 0x%x -> 0x%x (0x%x, 0x%x, 0x%x, 0x%x, 0x%x)" % (
                '  '*self.level[self.int_context], self.level[self.int_context],
                op.va, endeip,
                emu.getRegister(ppc_regs.REG_R3),
                emu.getRegister(ppc_regs.REG_R4),
                emu.getRegister(ppc_regs.REG_R5),
                emu.getRegister(ppc_regs.REG_R6),
                emu.getRegister(ppc_regs.REG_R7)))

        # If this is a conditional return, only print this information if
        # the condition was met and the branch taken. The first branch
        # option returned by getBranches() is the fall-through, so if PC !=
        # first target
        elif (op.iflags & envi.IF_RET and not op.iflags & ppc_const.IF_RFI) and \
                ((not op.iflags & envi.IF_COND) or \
                (op.iflags & envi.IF_COND and op.getBranches()[0][0] != endeip)):

            print("%s%d <<==== RET  0x%x <- 0x%x (0x%x)" % (
                '  '*self.level[self.int_context], self.level[self.int_context],
                endeip, op.va,
                emu.getRegister(ppc_regs.REG_R3)))

            self.level[self.int_context] -= 1
            self.path[self.int_context].pop()
            self.curfunc[self.int_context] = self.path[self.int_context][-1]

    def apicall(self, emu, op, pc, api, argv):
        print("call!")
        self.calls.append((op, pc, api, argv))

################################# END EmuMon


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
                    'size': 0x00040000,
                    'addr': 0x40000000,
                    # Indicates how much of the ram is preserved during resets
                    'standby_size': 0x8000,
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
                    'standby_size': 'Size of SRAM that is preserved across device resets',
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
                    'host': 'Host IP address for FlexCAN_D IO server',
                    'port': 'Host TCP port for FlexCAN_D IO server',
                },
                'eQADC_A': {
                    'host': 'Host IP address for eQADC_D IO server',
                    'port': 'Host TCP port for eQADC_D IO server',
                },
                'eQADC_B': {
                    'host': 'Host IP address for eQADC_B IO server',
                    'port': 'Host TCP port for eQADC_B IO server',
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
        parser.add_argument('-g', '--gdb-port', nargs='?', const=47001, type=int,
                            help='indicates that execution should\'nt start until a gdb client has connected, default is port 47001')
        group = parser.add_mutually_exclusive_group()
        group.add_argument('-N', '--no-backup',
                           help='run without a flash backup file, flash writes will be lost')
        group.add_argument('-I', '--init-flash',
                           help='Copy binary flash image to configuration directory (-c)')
        group.add_argument('-R', '--reset-backup', action='store_true',
                           help='Reset backup file, undoing any cached changes to the state of flash.')

        # Open up the workspace and read the project configuration
        project.VivProject.__init__(self, defconfig=defconfig, docconfig=docconfig, args=args, parser=parser)
        del parser

        # the self.vw attribute will get created when the e200z7 class calls the
        # workspace emulator initializer.
        e200z7.PPC_e200z7.__init__(self, self.vw)

        # Now that the standard options have been parsed process anything
        # leftover
        self._process_args()

        # The backup file is assumed to be located in the "project directory"
        self.flash = FLASH(self)

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
        self.mios = eMIOS200(self, 0xC3FA0000)
        #self.pmc = PMC(self, 0xC3FBC000)
        self.tpu = eTPU2(self, 0xC3FC0000)
        self.pit = PIT(self, 0xC3FF0000)

        ########################################
        # PBRIDGE_B
        ########################################

        self.xbar = XBAR(self, 0xFFF04000)
        # self.mpu = MPU(self, 0xFFF10000)
        self.swt = SWT(self, 0xFFF38000)
        # self.stm = STM(self, 0xFFF3C000)
        self.ecsm = ECSM(self, 0xFFF40000)
        self.dma = (
                eDMA('eDMA_A', self, 0xFFF44000),
                eDMA('eDMA_B', self, 0xFFF54000),
        )
        self.intc = INTC(self, 0xFFF48000)
        self.eqadc = (
            eQADC('eQADC_A', self, 0xFFF80000),
            eQADC('eQADC_B', self, 0xFFF84000),
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
        self.sci = (
            eSCI('eSCI_A', self, 0xFFFB0000),
            eSCI('eSCI_B', self, 0xFFFB4000),
            eSCI('eSCI_C', self, 0xFFFB8000),
        )
        self.can = (
            FlexCAN('FlexCAN_A', self, 0xFFFC0000),
            FlexCAN('FlexCAN_B', self, 0xFFFC4000),
            FlexCAN('FlexCAN_C', self, 0xFFFC8000),
            FlexCAN('FlexCAN_D', self, 0xFFFCC000),
        )
        #self.flexray = FLEXRAY(self, 0xFFFE0000)
        self.sim = SIM(self, 0xFFFEC000)

        # The BAM object is configurable, supply the valid boot addresses for 
        # the MPC5674F.
        #
        # Possible locations of the RCHW value from
        #   "Table 3-4. RCHW Location" (MPC5674FRM.pdf page 147)
        #
        #   Boot Mode |   Address
        #   ----------+-------------
        #    External | 0x0000_0000
        #   ----------+-------------
        #    Internal | 0x0000_0000
        #             | 0x0000_4000
        #             | 0x0001_0000
        #             | 0x0001_C000
        #             | 0x0002_0000
        #             | 0x0003_0000
        self.bam = BAM(self, 0xFFFFC000,
                       (0x0000, 0x4000, 0x10000, 0x1C000, 0x20000, 0x30000))

        ########################################

        # Firmware must be loaded before the peripherals are initialized or BAM
        # won't find a valid address, so if the FLASH peripheral was not able to
        # restore flash contents from the backup load the initial firmware now
        self.loadInitialFirmware()

        # Complete initialization of the e200z7 core
        self.init()

    def overrideEntryPoint(self):
        # If one valid entrypoint defined, move the PC there now and set the 
        # stack pointer (r1) to the end of RAM - 16 bytes (standard PowerPC 
        # stack frame is 16 bytes)
        #   RAM = 0x40000000 - 0x40040000
        #   SP  = 0x4003fff0
        entrypoints = self.vw.getEntryPoints()
        self.custom_entrypoint = None
        if len(entrypoints) == 1:
            # Set the program counter to the entry point, and then prepare the 
            # processor to run as if the bootloader has been run.
            self.custom_entrypoint = entrypoints[0]
            logger.info('Overriding entry point 0x%x with 0x%x',
                        self.getProgramCounter(), self.custom_entrypoint)
            self.setProgramCounter(self.custom_entrypoint)

            # Update the stack pointer
            sram_end = self.vw.config.project.MPC5674.SRAM.addr + \
                    self.vw.config.project.MPC5674.SRAM.size

            # Get the calling convention stack alignment
            align = max(c.align for _, c in self.getCallingConventions())
            self.setRegister(ppc_regs.REG_R1, sram_end - align)

    def _process_args(self):
        """
        Indicate that the supplied file can be used as an initial flash image if
        - The file is large enough to contain the main and shadow flash A & B
        OR
        - The file is large enough to contain the only main flash

        There are four different possible modes to run the emulator:
        1. No arguments:   run with existing configuration/initialized firmware
        2. --no-backup:    Use the specified file without copying to the project
                           directory or creating a backup file.
        3. --init-flash:   copies the specified file to the project directory and
                           creates an initial backup file.
        4. --reset-backup: re-initializes the backup file using the original
                           firmware file specified in the configuration.
        """

        # First set the proper port to use for the GDB server if one was 
        # specified.
        if self.args.gdb_port:
            self.gdbstub.setPort(self.args.gdb_port)
            self._wait_for_gdb_client = True
        else:
            self._wait_for_gdb_client = False

        # Track if this is a new configuration directory or not (needed by
        # init_flash)
        if self.vw.vivhome and not os.path.isdir(self.vw.vivhome):
            new_config = True
            # Save the initial config
            logger.critical('Creating new config directory %s', self.vw.vivhome)
            self.vw.config.saveConfigFile()
        else:
            new_config = False

        # Use the EnviConfig.cfginfo attribute directly so we can overwrite the
        # running configuration values for a specific run of the emulator if the 
        # "no backup" 
        flash_cfg = self.vw.config.project.MPC5674.FLASH.cfginfo

        mode = self.vw.getTransMeta("ProjectMode")

        # Get any custom file name and offsets to use for this run of the 
        # emulator based on the init_flash and no_backup flags.
        if self.args.init_flash:
            updated_config = getFlashOffsets(self.args.init_flash)
        elif self.args.no_backup:
            updated_config = getFlashOffsets(self.args.no_backup)
        else:
            # Will return an empty config
            updated_config = getFlashOffsets(None)

        # Initialize the configuration flash file using the specified firmware 
        # file.
        if self.args.init_flash:
            # If the filename specified in the command line arguments was not 
            # valid, raise an exception
            if updated_config['fwFilename'] is None:
                raise ValueError('ERROR: --init-flash option requires valid initial firmware image')

            # Figure out what configuration firmware filename is from the 
            # existing config or from the new file.
            flash_cfg['fwFilename'] = os.path.basename(updated_config['fwFilename'])
            cfg_flash_file = self.get_project_path(flash_cfg['fwFilename'])

            logger.critical('Initializing flash image in config directory %s with %s', 
                            cfg_flash_file, self.args.init_flash)

            # If the source and destination files are not the same, copy the 
            # specified file to the destination flash file.
            if self.args.init_flash != cfg_flash_file:
                shutil.copyfile(self.args.init_flash, cfg_flash_file)

            # If the init flash file was large enough to contain the shadow 
            # flash regions, also specify those as being in the flash file
            if updated_config['shadowAFilename'] is not None:
                flash_cfg['shadowAFilename'] = os.path.basename(updated_config['shadowAFilename'])
                flash_cfg['shadowAOffset'] = updated_config['shadowAOffset']

            if updated_config['shadowBFilename'] is not None:
                flash_cfg['shadowBFilename'] = os.path.basename(updated_config['shadowBFilename'])
                flash_cfg['shadowBOffset'] = updated_config['shadowBOffset']

            # If init_flash was specified save the config file now
            logger.critical('Saving configuration file %s', self.vw.config.filename)
            self.vw.config.saveConfigFile()

        elif self.args.no_backup:
            # Since this is just a temporary run copy any valid flash
            # filename (and offset) config values from the updated config to
            # the running configuration.
            if updated_config['fwFilename'] is not None:
                flash_cfg['fwFilename'] = updated_config['fwFilename']
                flash_cfg['baseaddr'] = updated_config['baseaddr']
            if updated_config['shadowAFilename'] is not None:
                flash_cfg['shadowAFilename'] = updated_config['shadowAFilename']
                flash_cfg['shadowAOffset'] = updated_config['shadowAOffset']
            if updated_config['shadowBFilename'] is not None:
                flash_cfg['shadowBFilename'] = updated_config['shadowBFilename']
                flash_cfg['shadowBOffset'] = updated_config['shadowBOffset']

            # Set to an empty string instead of None because otherwise 
            # retreiving this field through project.MPC5674.FLASH.backup throws 
            # an error
            flash_cfg['backup'] = ''

        # If no firmware file is identified print an error now as long as we 
        # aren't in test mode.
        if not flash_cfg['fwFilename'] and mode != 'test':
            logger.critical('No flash file provided, unable to load flash image')

    def loadInitialFirmware(self):
        '''
        load firmware into the emulator
        '''
        # Get the FLASH configuration info as a dict
        flash_cfg = self.vw.config.project.MPC5674.FLASH

        if flash_cfg['fwFilename']:
            # First check if the file can be found without adding the project
            # path. Otherwise assume it is intended to be a filename path
            # relative to the project path.
            if os.path.exists(flash_cfg['fwFilename']):
                path = flash_cfg['fwFilename']
            else:
                path = self.get_project_path(flash_cfg['fwFilename'])
            if os.path.exists(path):
                logger.info("Loading Firmware Blob from %r @ 0x%x", path, flash_cfg['baseaddr'])
                self.flash.load(FlashDevice.FLASH_MAIN, path, flash_cfg['baseaddr'])
            else:
                logger.critical("Starting emulator without valid firmware, please update config: %s", self.vw.vivhome)

        if flash_cfg['shadowAFilename']:
            # First check if the file can be found without adding the project
            # path. Otherwise assume it is intended to be a filename path
            # relative to the project path.
            if os.path.exists(flash_cfg['shadowAFilename']):
                path = flash_cfg['shadowAFilename']
            else:
                path = self.get_project_path(flash_cfg['shadowAFilename'])
            if os.path.exists(path):
                logger.info("Loading Shadow A Blob from %r @ 0x%x", path, flash_cfg['shadowAOffset'])
                self.flash.load(FlashDevice.FLASH_A_SHADOW, path, flash_cfg['shadowAOffset'])

        if flash_cfg['shadowBFilename']:
            # First check if the file can be found without adding the project
            # path. Otherwise assume it is intended to be a filename path
            # relative to the project path.
            if os.path.exists(flash_cfg['shadowBFilename']):
                path = flash_cfg['shadowBFilename']
            else:
                path = self.get_project_path(flash_cfg['shadowBFilename'])
            if os.path.exists(path):
                logger.info("Loading Shadow B Blob from %r @ 0x%x", path, flash_cfg['shadowBOffset'])
                self.flash.load(FlashDevice.FLASH_B_SHADOW, path, flash_cfg['shadowBOffset'])

        # Check if there are any memory maps loaded through the standard 
        # vivisect loading methods that we can copy into the emulator memory 
        # space.
        #
        # Use the MMIO methods and not the e200z7 core methods, we can't use the 
        # normal read/write functions yet because the MMU and other peripherals 
        # have not yet been initialized
        self.custom_overlay = False
        for mva, msize, mperms, mname in self.vw.getMemoryMaps():
            self.custom_overlay = True
            offset, mbytes = self.vw.getByteDef(mva)
            chunk = mbytes[offset:offset+msize]
            if self.getMemoryMap(mva):
                filename = self.vw.getFileByVa(mva)
                logger.info('Updating %08x - %08x memory map from loaded file %s', mva, msize, filename)

                # Enable supervisor mode so the actual contents of flash are 
                # modified if this is a flash memory segment.
                with mmio.supervisorMode(self):
                    mmio.ComplexMemoryMap.writeMemory(self, mva, chunk)

            else:
                logger.info('Adding %08x - %08x memory map from loaded file %s', mva, msize, filename)
                mmio.ComplexMemoryMap.addMemoryMap(self, mva, mperms, mname, chunk)

        # Now that the initial state of flash has been loaded, if the command 
        # line arguments indicates to reset the backup, delete the backup file
        if self.args.reset_backup:
            self.flash.delete_backup(self.get_project_path(flash_cfg['backup']))

        # Indicate that initial loading of flash memory from files is complete
        self.flash.load_complete(self.get_project_path(flash_cfg['backup']))

    def gpio(self, pinid, val=None):
        if val is not None:
            self.siu.connectGPIO(pinid, val)
        return self.siu.getGPIO(pinid)

    def externalResetHandler(self):
        print('**************\nEXTERNAL RESET\n**************')
        logger.info('EXTERNAL RESET')
        self.queueException(intc_exc.ResetException(intc_exc.ResetSource.EXTERNAL))

    def init(self):
        logger.info('INIT')

        # Create the initial RAM data (it isn't all cleared out during reset)
        size = self.vw.config.project.MPC5674.SRAM.size
        addr = self.vw.config.project.MPC5674.SRAM.addr

        # The initial SRAM memory block must be created
        logger.debug("init: Initializing SRAM 0x%08x - 0x%08x",
                addr, addr + size)
        self.addMemoryMap(addr, e_mem.MM_RWX, 'SRAM', b'\x00' * size)

        # Init the core
        super().init()

        # After BAM has initialized, if a valid entrypoint override exists, 
        # modify the initial state of the emulator.
        self.overrideEntryPoint()

        # If the --gdb-port flag was provided then we should wait for a GDB 
        # client to connect before completing initialization
        if self._wait_for_gdb_client:
            print('Waiting for GDB client to connect on port %d' % self.gdbstub._gdb_port)
            self.gdbstub.waitForClient()

    def reset(self):
        logger.info("RESET")

        # Clear or initialize SRAM and external RAM
        size = self.vw.config.project.MPC5674.SRAM.size
        addr = self.vw.config.project.MPC5674.SRAM.addr
        standby_size = self.vw.config.project.MPC5674.SRAM.standby_size

        start = addr + standby_size
        end = addr + size
        logger.debug("reset: clearing SRAM 0x%08x - 0x%08x",
                addr + standby_size, addr + size)
        self.writeMemory(start, b'\x00' * (end - start))

        # Reset the core
        super().reset()

        # After the emulator has been reset, BAM will have restored the initial 
        # entry point, but if a valid custom entry point has been defined, 
        # override the state of the emulator to start at the application.
        self.overrideEntryPoint()

    def run(self):
        try:
            logger.info('Starting execution @ 0x%x', self._cur_instr[1])
            e200z7.PPC_e200z7.run(self)
        except KeyboardInterrupt:
            print()
            logger.info('Execution stopped @ 0x%x', self._cur_instr[1])


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

