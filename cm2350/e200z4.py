import logging
logger = logging.getLogger(__name__)

import envi
import envi.memory as e_mem
from envi.archs.ppc.regs import rctx64, REG_TSR, REG_TCR, REG_HID0, REG_HID1, REG_TBU, REG_TB, REG_TBU_WO, REG_TBL_WO
from .ppc_vstructs import BitFieldSPR, v_const

from . import emutimers, ppc_mmio, ppc_mmu, e200_intc
from .ppc_vstructs import BitFieldSPR
from .const import *

# PPC/MCU Exceptions
from . import intc_exc


__all__ = [
    'e200z420n3',
]


# e200z4-specific SPRs

class HID0(BitFieldSPR):
    def __init__(self, emu):
        BitFieldSPR.__init__(self, REG_HID0, emu)
        self.emcp = v_bits(1)
        self._pad0 = v_const(13)
        self.icr = v_bits(1)
        self.nhr = v_bits(1)
        self._pad1 = v_const(3)
        self.dclree = v_bits(1)
        self.dclrce = v_bits(1)
        self.ciclerde = v_bits(1)
        self.mcclrde = v_bits(1)
        self._pad2 = v_const(8)
        self.nopti = v_bits(1)

class HID1(BitFieldSPR):
    def __init__(self, emu):
        BitFieldSPR.__init__(self, REG_HID1, emu)
        self.pad0 = v_bits(22)
        self.hp_nor = v_bits(1)
        self.hp_nmi = v_bits(1)
        self.ats = v_bits(1)
        self.pad1 = v_bits(7)

class TSR(BitFieldSPR):
    '''
    Timer Status Register

    Note: the VBitField stored here is *not* the real register value
    '''
    def __init__(self, emu):
        VBitField.__init__(self)
        self.enw = v_bits(1)
        self.wis = v_bits(1)
        self.wrs = v_bits(2)
        self.dis = v_bits(1)
        self.fis = v_bits(1)
        self.pad0 = v_bits(26)

class TCR(BitFieldSPR):
    '''
    Timer Control Register

    Note: the VBitField stored here is *not* the real register value
    '''
    def __init__(self, emu):
        VBitField.__init__(self)
        self.wp = v_bits(2)
        self.wrc = v_bits(2)
        self.wie = v_bits(1)
        self.die = v_bits(1)
        self.fp = v_bits(2)
        self.fie = v_bits(1)
        self.are = v_bits(1)
        self._pad0 = v_bits(1)
        self.wpext = v_bits(4)
        self.fpext = v_bits(4)
        self._pad1 = v_bits(13)


class PpcEmulationTime(emutimers.EmulationTime):
    '''
    PowerPC specific emulator time and timer handling.
    '''
    def __init__(self, systime_scaling=1.0):
        super().__init__(systime_scaling)

        # The time base can be written to which is supposed to reset the point
        # that the system time is counting from.  We don't want to change the
        # EmulationTime._sysoffset offset because that may impact the tracking
        # of any timers currently running.  Instead use a timebase offset value
        # so values read from TBU/TBL will have the correct values but the
        # systicks() will be unmodified.
        self._tb_offset = 0

        # Register the TBU/TBL callbacks, these are read-only so no write
        # callback is attached.
        self.addSprReadHandler(REG_TB, self.tblRead)
        self.addSprReadHandler(REG_TBU, self.tbuRead)

        # The TBU/TBL hypervisor access registers are write-only, but this is
        # not yet implemented
        self.addSprWriteHandler(REG_TBL_WO, self.tblWrite)
        self.addSprWriteHandler(REG_TBU_WO, self.tbuWrite)

        # The TBU_WO/TBL_WO SPRs are used to hold the desired timebase offset
        # value in them.  They are write-only so these callback functions ensure
        # the reads are correctly emulated.
        self.addSprReadHandler(REG_TBL_WO, self._invalid_tb_read)
        self.addSprReadHandler(REG_TBU_WO, self._invalid_tb_read)

    def _invalid_tb_read(self, emu, op):
        return 0

    def tblRead(self, emu, op):
        '''
        Read callback handler to associate the value of the TBL SPR with the
        EmulationTime.
        '''
        # In 64-bit mode reading the TBL returns the entire 64-bit TB value, in
        # 32-bit mode its just the lower 32-bits, but this masking is done
        # already in the PpcRegOper class (and will be set in the i_mfspr()
        # handler that calls this)
        return self.systicks()

    def tbuRead(self, emu, op):
        '''
        Read callback handler to associate the value of the TBU SPR with the
        EmulationTime.
        '''
        # Get the top 32-bits of the "ticks" value.  This should be only 32-bits
        # wide regardless of if this is a 64-bit or 32-bit machine.
        return (self.systicks() >> 32) & 0xFFFFFFFF

    def tblWrite(self, emu, op):
        '''
        Update the tb_offset so TBL values returned from this point on
        reflect the new offset.
        '''
        # Ensure that the offset value is only 32-bits wide regardless of the
        # platform size.
        tbl_offset = self.getOperValue(op, 1) & 0xFFFFFFFF

        # Based on the new TBL offset and the current value of TBU_WO, calculate
        # the new desired timebase offset
        tbu_offset = emu.getRegister(REG_TBU_WO)
        offset = (tbu_offset << 32) | tbl_offset
        self._tb_offset = super().systicks() - offset

        # Return the offset so that TBL_WO has the correct offset to use to
        # calculate the desired timebase offset.
        return tbl_offset

    def tbuWrite(self, emu, op):
        '''
        Update the tb_offset so TBU values returned from this point on
        reflect the new offset.
        '''
        # Ensure that the offset value is only 32-bits wide regardless of the
        # platform size.
        tbu_offset = self.getOperValue(op, 1) & 0xFFFFFFFF

        # Based on the new TBU offset and the current value of TBL_WO, calculate
        # the new desired timebase offset
        tbl_offset = emu.getRegister(REG_TBL_WO)
        offset = (tbu_offset << 32) | tbl_offset
        self._tb_offset = super().systicks() - offset

        # Return the offset so that TBU_WO has the correct offset to use to
        # calculate the desired timebase offset.
        return tbu_offset

    def systicks(self):
        '''
        Because PowerPC allows writes to the "Write-Only" TBL/TBU registers,
        adjust the returned systicks value by the current offset.
        '''
        return super().systicks() - self._tb_offset


import envi.archs.ppc.emu as eape
import vivisect.impemu.emulator as vimp_emulator
class e200z420n3(ppc_mmio.PpcMemoryMap, vimp_emulator.WorkspaceEmulator, eape.PpcVleEmulator, PpcEmulationTime):
    def __init__(self, vw):
        # module registry
        self.modules = {}

        # initialize base class and CPU/Modules
        ppc_mmio.PpcMemoryMap.__init__(self)

        # Initialize the core "helper" emulator
        # WorkspaceEmulator to start, as it provides inspection hooks and
        # tracing which is helpful for debugging.
        eape.PpcVleEmulator.__init__(self, endian=envi.ENDIAN_MSB)
        #vimp_ppc_emu.Ppc32EmbeddedWorkspaceEmulator.__init__(self, vw, nostack=True, funconly=False)

        PpcEmulationTime.__init__(self, 0.1)

        #  TODO: FIGURE OUT HOW TO NORMALIZE THE Envi Registers' value with the TSR/TCR...
        #       or not... this may give a double-buffering effect which could be useful
        self.tcr = TCR(self)
        self.tsr = TSR(self)
        # TODO: Need to hook a callback into HID0[TBEN] to start/stop the
        # internal timebase counting
        self.hid0 = HID0(self)
        self.hid1 = HID1(self)

        # Create the MMU peripheral and then redirect the TLB instruction
        # handlers to the MMU
        self.mmu = ppc_mmu.PpcMMU(self)

        # Create the PowerPC INTC peripheral to handle internal (PowerPC
        # standard) exceptions/interrupts
        self.mcu_intc = e200_intc.e200INTC(emu=self, ivors=True)

        # initialize SRAM
        self.init_ram()

        # initialize the core "helper" emulator.  WorkspaceEmulator to start, as it provides inspection hooks and tracing which is helpful for debugging.
        #vimp_emulator.HLEmulator.__init__(self, vw, initStack=False)
        vimp_emulator.WorkspaceEmulator.__init__(self, vw, nostack=True, funconly=False)

        # init_core must be called later in order to enable the whole chain

    def init_core(self):
        '''
        Setup the Peripherals supported on this chip
        '''
        # setup Interrupt Subsystem


        # initialize the various modules on this chip.
        for key, module in self.modules.items():
            logger.debug("init_core: Initializing %r...", key)
            module.init(self)

    def reset_core(self):
        '''
        Reset all registered peripherals that have a reset function.
        Peripherals that should be returned to some pre-determined state when
        the processor resets should implement this function.
        '''
        for key, module in self.modules.items():
            if hasattr(module, 'reset'):
                logger.debug("reset_core: Resetting %r...", key)
                module.reset()

    # Redirect TLB instruction emulation functions to the MMU peripheral
    def i_tlbre(self, op):
        self.mmu.i_tlbre(op)

    def i_tlbwe(self, op):
        self.mmu.i_tlbwe(op)

    def i_tlbsx(self, op):
        self.mmu.i_tlbsx(op)

    def i_tlbivax(self, op):
        self.mmu.i_tlbivax(op)

    def i_tlbsync(self, op):
        self.mmu.i_tlbsync(op)

    def readMemory(self, va, size):
        '''
        Data Read
        '''
        ea = self.mmu.translateDataAddr(va)
        return ppc_mmio.PpcMemoryMap.readMemory(self, ea, size)

    def writeMemory(self, va, bytez):
        '''
        Data Write
        '''
        ea = self.mmu.translateDataAddr(va)
        ppc_mmio.PpcMemoryMap.writeMemory(self, ea, bytez)

    def getHandler(self, exception):
        '''
        Utility function to return PC to code that should handle the exception.
        This redirects to the MCU INTC module.
        '''
        return self.mcu_intc.getHandler(exception)

    def stepi(self):
        try:
            # See if there are any exceptions that need to start being handled
            self.mcu_intc.checkException()

            # do normal opcode parsing and execution
            pc = self.getProgramCounter()
            op = self.parseOpcode(pc)
            self.executeOpcode(op)

        except intc_exc.ResetException:
            # Special case, don't queue a reset exception, just do a reset
            self.reset()

        except intc_exc.INTCException as exc:
            # If any PowerPC-specific exception occurs, queue it to be handled
            # on the next call
            self.queueException(exc)

    def queueException(self, exception):
        '''
        Allow non-immediate exceptions to be queued for processing later
        '''
        self.mcu_intc.queueException(exception)

    def parseOpcode(self, va, arch=envi.ARCH_PPC_E32):
        '''
        Combination of the WorkspaceEmulator and the standard envi.memory
        parseOpcode functions that handles translating instruction addresses
        into the correct physical address based on the TLB.
        '''
        ea, vle = self.mmu.translateInstrAddr(va)

        off, b = self.getByteDef(ea)
        if vle:
            op = self._arch_vle_dis.disasm(b, off, ea)
        else:
            op = self._arch_dis.disasm(b, off, ea)
        return op
