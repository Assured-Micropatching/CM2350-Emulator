from ..ppc_vstructs import *
from ..ppc_peripherals import *
from .. import ppc_mmu, intc_exc

import logging
logger = logging.getLogger(__name__)


# When searching for the RCHW, ignore the flags.  The upper nibble of reserved
# bits should have a value of 0.
BAM_RCHW_MASK  = 0xF0FF
BAM_RCHW_VALUE = 0x005A

# The RCHW signature is just 2 bytes (counting the flags) but including 16 bits
# of padding and the entry point it is 8 bytes.
BAM_RCHW_SIG_SIZE = 2
BAM_RCHW_SIZE     = 8


class RCHW(VBitField):
    def __init__(self):
        VBitField.__init__(self)
        self.rsvd = v_bits(4)
        self.swt = v_bits(1)
        self.wte = v_bits(1)
        self.ps0 = v_bits(1)
        self.vle = v_bits(1)
        self.bootid = v_bits(8)
        self._pad0 = v_bits(16)
        self.entry_point = v_bits(32)


class BAM(MMIOPeripheral):
    '''
    Simple Boot-Assist-Module.
    Searches for a RCHW in several locations of memory to determine the correct
    boot location and context.
    One-Time-Use
    '''
    def __init__(self, emu, mmio_addr):
        super().__init__(emu, 'BAM', mmio_addr, 0x4000)

        # Values that are populated after the boot target has been found
        self.rchw = RCHW()
        self.rchw_addr = None

    def _getPeriphReg(self, offset, size):
        '''
        BAM represents a boot ROM on the device, we don't emulate the "real"
        contents of BAM, instead just return fake data for all reads.
        '''
        return b'\x00' * size

    def _setPeriphReg(self, offset, bytez):
        '''
        None of BAM is writable
        '''
        raise intc_exc.MceWriteBusError(written=offset)

    def analyze(self):
        '''
        Adapted from the vivisect.analysis.ppc.bootstrap module because the
        vivisect workspace doesn't call ComplexMemoryMap read and write
        methods.
        '''
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
        #
        # TODO: Theoretically this should support both external and internal
        # boot targets.
        if self.emu.siu.bootcfg == 0b00:
            # BOOTCFG == 0b00 means internal boot
            for offset in (0x0000, 0x4000, 0x10000, 0x1C000, 0x20000, 0x30000):
                # BAM needs to set the initial MMU/TLB config so until that
                # happens the normal MMIO APIs will be unable to successfully
                # use that API, instead directly read from the flash peripheral
                # and look for an RCHW structure
                value = self.emu.flash.readMemValue(offset, BAM_RCHW_SIG_SIZE)
                logger.info("analyzing: 0x%x : 0x%x", offset, value)

                if value & BAM_RCHW_MASK == BAM_RCHW_VALUE:
                    # Found the boot location, save the RCHW information
                    self.rchw_addr = offset
                    self.rchw.vsParse(self.emu.flash.readMemory(offset, BAM_RCHW_SIZE))
                    return True
        else:
            raise NotImplementedError('BOOTCFG 0b%s not yet supported' % bin(self.emu.siu.bootcfg))

        mode = self.emu.vw.getTransMeta("ProjectMode")
        if mode != 'test':
            logger.critical('No valid RCHW identified')

        # No valid entry was found, Set the RCHW value back to all 0's
        self.rchw.vsParse(b'\x00' * BAM_RCHW_SIZE)
        self.rchw_addr = None
        return False

    def reset(self, emu):
        '''
        Reset the emulator by placing the PC at the function identified by the
        RCHW.
        '''
        # TODO: Clear TLB and initialize the default entries
        #
        #   MAS0 10000000
        #   MAS1 c0000500
        #   MAS2 fff0000a
        #   MAS3 fff0003f
        #
        #   MAS0 10010000
        #   MAS1 c0000700
        #   MAS2 00000000
        #   MAS3 0000003f
        #
        #   MAS0 10020000
        #   MAS1 c0000700
        #   MAS2 20000000
        #   MAS3 0000003f
        #
        #   MAS0 10030000
        #   MAS1 c0000400
        #   MAS2 40000008
        #   MAS3 4000003f
        #
        #   MAS0 10040000
        #   MAS1 c0000500
        #   MAS2 c3f0000a
        #   MAS3 c3f0003f

        # Because flash can be modified between resets we need to re-evaluate
        # flash for the first valid RCHW.
        if self.analyze():
            logger.info("booting from first discovered boot entry: baseaddr: 0x%x  codeva: 0x%x", self.rchw_addr, self.rchw.entry_point)
            logger.debug(self.rchw.tree())

        # The default entry point if no BAM entry is found ix 0x00000000, which
        # is what the "invalid" RHCW will now indicate.
        self.emu.setProgramCounter(self.rchw.entry_point)

        # After BAM completes and before execution starts at the entry point
        # specified by the RCHW, BAM configures the TLB to allow access to all
        # MPC5674F peripherals. We duplicate the result of that here. Values
        # used here are from
        #   "8.5.2 BAM Program Operation" page 296 of MPC5674FRM.pdf
        #
        # When the BAM VLE flag is set then entries 1-3 also get the VLE flag

        # Peripheral Bridge B (1MB)
        self.emu.mmu.tlbConfig(0, epn=0xFFF00000, rpn=0xFFF00000,
                tsiz=ppc_mmu.PpcTlbPageSize.SIZE_1MB,
                flags=ppc_mmu.PpcTlbFlags.IG)
        # Peripheral Bridge A (1MB)
        self.emu.mmu.tlbConfig(4, epn=0xC3F00000, rpn=0xC3F00000,
                tsiz=ppc_mmu.PpcTlbPageSize.SIZE_1MB,
                flags=ppc_mmu.PpcTlbFlags.IG)

        if self.rchw.vle == 0:
            # Flash (16MB) (covers flash and shadow flash)
            self.emu.mmu.tlbConfig(1, epn=0x00000000, rpn=0x00000000,
                    tsiz=ppc_mmu.PpcTlbPageSize.SIZE_16MB,
                    flags=0)
            # EBI (16MB) (external memory and development memory)
            self.emu.mmu.tlbConfig(2, epn=0x20000000, rpn=0x20000000,
                    tsiz=ppc_mmu.PpcTlbPageSize.SIZE_16MB,
                    flags=0)
            # SRAM (256KB)
            self.emu.mmu.tlbConfig(3, epn=0x40000000, rpn=0x40000000,
                    tsiz=ppc_mmu.PpcTlbPageSize.SIZE_256KB,
                    flags=ppc_mmu.PpcTlbFlags.I)
        else:
            # Flash (16MB) (covers flash and shadow flash)
            self.emu.mmu.tlbConfig(1, epn=0x00000000, rpn=0x00000000,
                    tsiz=ppc_mmu.PpcTlbPageSize.SIZE_16MB,
                    flags=ppc_mmu.PpcTlbFlags.VLE)
            # EBI (16MB) (external memory and development memory)
            self.emu.mmu.tlbConfig(2, epn=0x20000000, rpn=0x20000000,
                    tsiz=ppc_mmu.PpcTlbPageSize.SIZE_16MB,
                    flags=ppc_mmu.PpcTlbFlags.VLE)
            # SRAM (256KB)
            self.emu.mmu.tlbConfig(3, epn=0x40000000, rpn=0x40000000,
                    tsiz=ppc_mmu.PpcTlbPageSize.SIZE_256KB,
                    flags=ppc_mmu.PpcTlbFlags.I | ppc_mmu.PpcTlbFlags.VLE)

        # TODO: Enable or disable the e200z7 MCU Watchdog

        # By default (according to the documentation) the SWT watchdog is
        # enabled, but if RCHW[SWT] flag is 0, disable the SWT.  But just to
        # ensure that the initial value is correct explicitly enable or
        # disable the SWT based on the RCHW flag.
        old_wen = self.emu.swt.registers.mcr.wen
        if self.rchw.swt:
            logger.info("BAM: Enabling SWT")
            self.emu.swt.registers.mcr.wen = 1
        else:
            logger.info("BAM: Disabling SWT")
            self.emu.swt.registers.mcr.wen = 0

        if self.emu.swt.registers.mcr.wen != old_wen:
            # The SWT "updateWatchdog" function must be called manually when
            # directly changing SWT_MCR[WEN]
            self.emu.swt.updateWatchdog()
