import sys
import time
import signal
import logging
import threading

import envi
import envi.archs.ppc.regs as eapr
import vtrace.platforms.gdbstub as vtp_gdb

from . import mmio
from . import intc_exc
from .gdbdefs import e200z759n3

logger = logging.getLogger(__name__)


__all__ = [
    'e200GDB',
]


# TODO: handle reset


# the DNH instruction opcodes for BookE and VLE modes, the instructions are 
# organized first by a flag indicating if the instruction should be VLE, and 
# secondly by size
PPC_DNH_INSTR_BYTES = {
    0: {
        4: b'\x4c\x00\x01\x8c',
    },
    1: {
        2: b'\x00\x0F',
        4: b'\x7c\x00\x00\xc2',
    },
}


class e200GDB(vtp_gdb.GdbBaseEmuServer):
    '''
    Emulated hardware debugger/gdb-stub for the e200 core.
    '''
    def __init__(self, emu):
        # TODO: figure out GPR 32/64 bit stuff, same for PC/LR/CTR, and all SPRs
        # such as specifying TBL vs TB.
        #reggrps = [
        #    ('general',     'org.gnu.gdb.power.core'),
        #    ('spe',         'org.gnu.gdb.power.spe'),
        #    ('spr',         'org.gnu.gdb.power.spr'),
        #]
        #vtp_gdb.GdbBaseEmuServer.__init__(self, emu, reggrps=reggrps)
        vtp_gdb.GdbBaseEmuServer.__init__(self, emu, haltregs=['pc', 'r1'])

        emu.modules['GDBSTUB'] = self

        # To track breakpoints, for the purposes of emulation both hardware and 
        # software breakpoints are treated the same
        self._bpdata = {}
        self._bps_in_place = False

        # There is no real filename for the firmware image
        self.supported_features[b'qXfer:exec-file:read'] = None
        self.xfer_read_handlers[b'exec-file'] = None

        # We don't support the vfile handlers for this debug connection
        self.vfile_handlers = {}

    def getTargetXml(self, reggrps=None, haltregs=None):
        # Hardcoded register format and XML
        self._gdb_reg_fmt = e200z759n3.reg_fmt
        self._gdb_target_xml = e200z759n3.target_xml

        # Define the default register packet size as just the general PPC 
        # registers
        self._reg_pkt_size = e200z759n3.reg_pkt_size

        # Generate the information required based on the parsed register format.
        self._genRegPktFmt()
        self._updateEnviGdbIdxMap()

        # To mimic what the GdbBaseEmuServer.getTargetXml() function does, go 
        # find the gdb register indexes for the halt
        for reg_name, (_, reg_idx) in self._gdb_reg_fmt.items():
            envi_idx = self._gdb_to_envi_map[reg_idx][vtp_gdb.GDB_TO_ENVI_IDX]
            if envi_idx in haltregs or reg_name in haltregs:
                self._haltregs.append(reg_idx)

    def initProcessInfo(self):
        self.pid = 1
        self.tid = 1
        self.processes = [1]

        # We don't use these for the e200 GDB stub
        self.process_filenames = {}
        self.vfile_pid = None

    def waitForClient(self):
        # Queue up a debug interrupt
        self.emu.halt_exec()

    def isClientConnected(self):
        return self.connstate == vtp_gdb.STATE_CONN_CONNECTED

    def init(self, emu):
        logger.info("e200GDB Initialized.")

        if self.runthread is None:
            logger.info("starting GDBServer runthread")
            self.runthread = threading.Thread(target=self.runServer, daemon=True)
            self.runthread.start()
        else:
            logger.critical("WTFO!  self.runthread is not None?")

    def handleInterrupts(self, interrupt):
        # TODO: emulate the PPC debug control registers that can disable/enable 
        # some things?

        # If there is a debugger connected halt execution, otherwise queue the 
        # debug exception so it can be processed by the normal PPC exception 
        # handler.
        logger.info('Execution halted at %x', self.emu._cur_instr[1])
        self.emu._do_halt()

        # TODO: different signal reasons based on the interrupt type?
        self._halt_reason = signal.SIGTRAP

        self._pullUpBreakpoints()

        self.emu._do_wait_resume()

    def _postClientAttach(self, addr):
        vtp_gdb.GdbBaseEmuServer._postClientAttach(self, addr)

        # TODO: Install callbacks for signals that should cause execution to 
        # halt.

        logger.info("Client attached: %r", repr(addr))

    def _serverBreak(self, sig=signal.SIGTRAP):
        self.emu.halt_exec()

    def _serverCont(self, sig=0):
        # If the program counter is at a breakpoint execute the current 
        # (original) instruction before restoring the breakpoints
        if self.emu.getProgramCounter() in self._bpdata:
            # The breakpoints should not be installed because we are halted
            assert not self._bps_in_place

            # Should have no problem doing stepi in the server thread because 
            # the primary thread should be halted.
            self._serverStepi()

        # Restore the breakpoints and resume execution
        self._putDownBreakpoints()

        # Continue execution
        self.emu.resume_exec()

    def _installBreakpoint(self, addr):
        ea, vle, _, _, breakbytes, breakop = self._bpdata[addr]

        with self.emu.getAdminRights():
            self.emu.writeOpcode(addr, breakbytes)

        self.emu.updateOpcache(ea, vle, breakop)

    def _uninstallBreakpoint(self, addr):
        ea, vle, origbytes, origop, _, _ = self._bpdata[addr]

        with self.emu.getAdminRights():
            self.emu.writeOpcode(addr, origbytes)

        self.emu.updateOpcache(ea, vle, origop)

    def _putDownBreakpoints(self):
        '''
        At each emulator stop, we want to replace the original bytes.  On 
        resume, we put the Break instruction bytes back in.
        '''
        if not self._bps_in_place:
            logger.debug('Installing breakpoints: %r', self._bpdata)
            for va in self._bpdata:
                self._installBreakpoint(va)
            self._bps_in_place = True

    def _pullUpBreakpoints(self):
        '''
        At each emulator stop, we want to replace the original bytes.  On 
        resume, we put the Break instruction bytes back in.
        '''
        if self._bps_in_place:
            logger.debug('Removing breakpoints: %r', self._bpdata)
            for va in self._bpdata:
                self._uninstallBreakpoint(va)
            self._bps_in_place = False

    def _serverSetSWBreak(self, addr):
        return self._serverSetHWBreak(addr)

    def _serverSetHWBreak(self, addr):
        if addr in self._bpdata:
            raise Exception('Cannot add breakpoint that already exists @ 0x%x' % addr)

        logger.debug('Adding new breakpoint: 0x%x', addr)
        origbytes = self._bpdata.get(addr)
        if origbytes:
            # Error, this breakpoint is already set
            return b'E02'

        try:
            # Find the opcode being replaced
            op = self.emu.parseOpcode(addr, skipcallbacks=True)

        except intc_exc.MceDataReadBusError:
            return b'E%02d' % signal.SIGSEGV

        except intc_exc.DataTlbException:
            return b'E%02d' % signal.SIGBUS

        # Get the break instruction info
        ea, vle, origop, origbytes = self.emu.getInstrInfo(addr, skipcache=True)

        # Create a new break instruction for the target address
        breakbytes = PPC_DNH_INSTR_BYTES[vle][origop.size]

        # Generate the breakpoint instruction object for the target address
        if vle:
            breakop = self.emu._arch_vle_dis.disasm(breakbytes, 0, addr)
        else:
            breakop = self.emu._arch_dis.disasm(breakbytes, 0, addr)

        # Save the physical address, vle flag, original bytes, original 
        # instruction, breakpoint bytes, and breakpoint instruction we just 
        # created.
        self._bpdata[addr] = (ea, vle, origbytes, origop, breakbytes, breakop)

        # If breakpoints are currently installed, add the new one.
        if self._bps_in_place:
            self._installBreakpoint(addr)

        return b'OK'

    def _serverRemoveSWBreak(self, addr):
        return self._serverRemoveHWBreak(addr)

    def _serverRemoveHWBreak(self, addr):
        if addr not in self._bpdata:
            raise Exception('Cannot remove breakpoint that doesn\'t exist @ 0x%x' % addr)

        # Only need to write the original data back to memory if the breakpoint 
        # is currently in memory.
        logger.debug('Removing breakpoint: 0x%x', addr)
        if self._bps_in_place:
            self._uninstallBreakpoint(addr)
        del self._bpdata[addr]

        return b'OK'

    def _serverDetach(self):
        vtp_gdb.GdbBaseEmuServer._serverDetach(self)

        # Clear all breakpoints and resume execution
        self._pullUpBreakpoints()
        self._bpdata = {}
        self._bps_in_place = False

        # Signal to the emulator that the gdb client has detached
        self.emu.debug_client_detached()

    def _serverQSymbol(self, cmd_data):
        # we have no symbol information
        return b'OK'

    def getMemoryMapXml(self):
        self._gdb_memory_map_xml = b'''<?xml version="1.0" ?>
<!DOCTYPE memory-map
  PUBLIC '+//IDN gnu.org//DTD GDB Memory Map V1.0//EN'
  'http://sourceware.org/gdb/gdb-memory-map.dtd'>
<memory-map>
  <memory length="0xafc000" start="0x400000" type="ram"/>
  <memory length="0xfc000" start="0xf00000" type="ram"/>
  <memory length="0xff000000" start="0x1000000" type="ram"/>
  <memory length="0x400000" start="0x0" type="flash">
    <property name="blocksize">0x800</property>
  </memory>
  <memory length="0x4000" start="0xefc000" type="flash">
    <property name="blocksize">0x800</property>
  </memory>
  <memory length="0x4000" start="0xffc000" type="flash">
    <property name="blocksize">0x800</property>
  </memory>
</memory-map>
'''

    def _serverReadMem(self, addr, size):
        """
        Normally a GDB server should return an error if an invalid memory
        address is read, but the GDB client when it connects to a remote target
        has no knowledge of the target endianness and it immediately attempts
        to read the memory address referenced by the PC and SP registers. But
        if the gdb client's endianness setting hasn't been set to big endian
        before connecting, GDB will attempt to read an invalid memory address.

        So this function has to return a fake value for all memory addressing
        related errors
        """
        try:
            return vtp_gdb.GdbBaseEmuServer._serverReadMem(self, addr, size)

        except (intc_exc.MceDataReadBusError, intc_exc.DataTlbException):
            # Return garbage filler values
            return b'\x00' * size

    def _serverWriteMem(self, addr, val):
        """
        Support writing to server memory but translate the PPC data access
        exceptions into standard error types.
        """
        try:
            return vtp_gdb.GdbBaseEmuServer._serverWriteMem(self, addr, val)

        except intc_exc.MceWriteBusError:
            return b'E%02d' % signal.SIGSEGV

        except intc_exc.DataTlbException:
            return b'E%02d' % signal.SIGBUS

    def _serverWriteRegVal(self, reg_idx, reg_val):
        try:
            envi_idx = self._gdb_to_envi_map[reg_idx][vtp_gdb.GDB_TO_ENVI_IDX]
        except IndexError:
            logger.warning("Attempted Bad Register Write: %d", reg_idx)
            return 0

        try:
            self.emu.writeRegValue(envi_idx, reg_val)
        except IndexError:
            logger.warning("Attempted Bad Register Write: %d -> %d", reg_idx, envi_idx)
            return 0


        return b'OK'

    def _serverReadRegVal(self, reg_idx):
        try:
            _, size, envi_idx, mask = self._gdb_to_envi_map[reg_idx]
        except IndexError:
            logger.warning("Attempted Bad Register Read: %d", reg_idx)
            return 0, None

        try:
            # Sometimes the register format may specify a bit width that is 
            # smaller than the internal register size, ensure the value 
            # returned is the correct size
            return (self.emu.readRegValue(envi_idx) & mask), size
        except IndexError:
            logger.warning("Attempted Bad Register Read: %d -> %d", reg_idx, envi_idx)
            return 0, None
