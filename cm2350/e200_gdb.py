import sys
import time
import signal
import logging
import threading

import envi
import envi.archs.ppc.regs as eapr
import vtrace.platforms.gdbstub as vtp_gdb

from . import intc_exc

logger = logging.getLogger(__name__)


__all__ = [
    'e200GDB',
]


# TODO: handle reset
# TODO: handle monitor commands (monitor reset)


STATE_DISCONNECTED = 0
STATE_CONNECTED = 1
STATE_RUNNING = 2
STATE_PAUSED = 3


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


class e200GDB(vtp_gdb.GdbServerStub):
    '''
    Emulated hardware debugger/gdb-stub for the e200 core.
    '''
    def __init__(self, emu, port=47001):
        self.emu = emu
        regfmt = self.generateRegFmt()
        vtp_gdb.GdbServerStub.__init__(self, 'ppc32-embedded', 4, bigend=True, reg=regfmt, port=port, find_port=True)

        # don't ask me why, but GDB doesn't like the way we encode repeated values.  so for now, leave it off.
        self._doEncoding = False

        emu.modules['GDBSTUB'] = self

        # To track breakpoints, for the purposes of emulation both hardware and 
        # software breakpoints are treated the same
        self._bpdata = {}
        self._bps_in_place = False

        self.connstate = vtp_gdb.STATE_CONN_DISCONNECTED
        self.runthread = None

        self._halt_reason = 0

        self.xfer_read_handlers = {
            b'features': {
                b'target.xml': self.XferFeaturesReadTargetXml,
            },
        }

    def setPort(self, port):
        self._gdb_port = port

    def waitForClient(self):
        while self.connstate != vtp_gdb.STATE_CONN_CONNECTED:
            time.sleep(0.1)

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
        if self.isClientConnected():
            self.emu._do_halt()
            self._pullUpBreakpoints()
        else:
            self.emu.queueException(interrupt)

    def generateRegFmt(self, emu=None):
        if emu is None:
            emu = self.emu

        arch = envi.getArchModule(self.emu._arch_name)
        regs_core = arch.archGetRegisterGroups().get('gdb_power_core')
        regfmt = [(name, bitsize, idx) for idx, (name, bitsize) in enumerate(emu._rctx_regdef) if name in regs_core]
        return regfmt

    def _postClientAttach(self, addr):
        # TODO: Install callbacks for signals that should cause execution to 
        # halt.

        logger.info("Client attached: %r", repr(addr))
        logger.info("Halting processor")
        self._halt_reason = signal.SIGTRAP
        self.emu.halt_exec()

    # gdb_reg_fmt population from archGetRegCtx() (or emu-equiv)
    # wire up and handle server requests
    # specifically: qXfer handling

    def _serverBreak(self):
        self._halt_reason = signal.SIGTRAP
        self.emu.halt_exec()
        return self._halt_reason

    def _serverCont(self):
        # If the program counter is at a breakpoint execute the current 
        # (original) instruction before restoring the breakpoints
        if self.emu.getProgramCounter() in self._bpdata:
            self._serverStepi()

        # Restore the breakpoints and resume execution
        self._putDownBreakpoints()

        # Continue execution
        self._halt_reason = 0
        self.emu.resume_exec()

        # TODO also check _serverBREAK and _handleBREAK

        return self._halt_reason

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
            logger.debug('Installing breakpoints: ' + ','.join(hex(a) for a in self._bpdata))
            for va in self._bpdata:
                self._installBreakpoint(va)
            self._bps_in_place = True

    def _pullUpBreakpoints(self):
        '''
        At each emulator stop, we want to replace the original bytes.  On 
        resume, we put the Break instruction bytes back in.
        '''
        if self._bps_in_place:
            logger.debug('Removing breakpoints: ' + ','.join(hex(a) for a in self._bpdata))
            for va in self._bpdata:
                self._uninstallBreakpoint(va)
            self._bps_in_place = False

    def _serverSetSWBreak(self, addr):
        return self._serverSetHWBreak(addr)

    def _serverSetHWBreak(self, addr):
        if addr in self._bpdata:
            raise Exception('Cannot add breakpoint that already exists @ 0x%x' % addr)

        logger.debug('Adding new breakpoint: 0x%x' % addr)
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
        logger.debug('Removing breakpoint: 0x%x' % addr)
        if self._bps_in_place:
            self._uninstallBreakpoint(addr)
        del self._bpdata[addr]

        return b'OK'

    def _serverGetHaltSignal(self):
        # Return the halt reason and the current values of the PC and SP (r1) 
        # registers in big-endian format
        #return (self._halt_reason, {
        #    eapr.REG_R1: self.emu.getRegister(eapr.REG_R1),
        #    eapr.REG_PC: self.emu.getProgramCounter(),
        #})
        return self._halt_reason

    def _serverReadMem(self, addr, size):
        # The particular error msg doesn't matter, but for testing purposes use 
        # the signal numbers to indicate the type of failure:
        #   - MMU error         = SIGBUS
        #   - unable to read    = SIGSEGV
        try:
            with self.emu.getAdminRights():
                return self.emu.readMemory(addr, size, skipcallbacks=True)

        except intc_exc.MceDataReadBusError:
            return b'E%02d' % signal.SIGSEGV

        except intc_exc.DataTlbException:
            return b'E%02d' % signal.SIGBUS

    def _serverWriteMem(self, addr, val):
        # The particular error msg doesn't matter, but for testing purposes use 
        # the signal numbers to indicate the type of failure:
        #   - MMU error         = SIGBUS
        #   - unable to write   = SIGSEGV

        try:
            with self.emu.getAdminRights():
                self.emu.writeMemory(addr, val, skipcallbacks=True)
            return b'OK'

        except intc_exc.MceDataWriteBusError:
            return b'E%02d' % signal.SIGSEGV

        except intc_exc.DataTlbException:
            return b'E%02d' % signal.SIGBUS

    def _serverWriteRegValByName(self, reg_name, reg_val):
        self.emu.setRegisterByName(reg_name, reg_val)

    def _serverReadRegValByName(self, reg_name):
        return self.emu.getRegisterByName(reg_name)

    def _serverWriteRegVal(self, ridx, reg_val):
        self.emu.setRegister(ridx, reg_val)

    def _serverReadRegVal(self, ridx):
        return self.emu.getRegister(ridx)

    def _serverStepi(self):
        self.emu.stepi()

        # Return the trap signal
        self._halt_reason = signal.SIGTRAP
        return self._halt_reason

    def _serverDetach(self):
        self.connstate = vtp_gdb.STATE_CONN_DISCONNECTED

        # Clear all breakpoints and resume execution
        self._pullUpBreakpoints()
        self._bpdata = {}
        self._bps_in_place = False

        self._halt_reason = 0
        self.emu.resume_exec()

    def _serverH(self, cmd_data):
        return self.curThread

    def _serverQSupported(self, cmd_data):
        return b"PacketSize=1000;qXfer:memory-map:read+;qXfer:features:read+"
        #return b"PacketSize=1000;qXfer:features:read+;qXfer:memorymap:read+"

    def _serverQXfer(self, cmd_data):
        res = b''
        fields = cmd_data.split(b":")
        logger.warning("qXfer fields:  %r", fields)
        if fields[2] == b'read':
            section = self.xfer_read_handlers.get(fields[1])
            if not section:
                logger.warning("qXfer no section:  %r", fields[1])
                return b'E00'

            hdlr = section.get(fields[3])
            if not hdlr:
                logger.warning("qXfer no handler:  %r", fields[3])
                return b'E00'

            res = hdlr(fields)

            offstr, szstr = fields[-1].split(b',')
            off = int(offstr, 16)
            sz = int(szstr, 16)

            logger.debug("_serverQXfer(%r) => %r", cmd_data, res[off:off+sz])
            if (off+sz) >= len(res):
                return b'l' + res[off:off+sz]
            return b'm' + res[off:off+sz]

    def _serverQC(self, cmd_data):
        '''
        return Current Thread ID
        '''
        return b'QC0'

    def _serverQL(self, cmd_data):
        '''
        return Current Thread ID
        '''
        return b'qM011000000010'

    def _serverQTStatus(self, cmd_data):
        '''
        return Current Thread Status
        '''
        return b'T0'

    def _serverQfThreadInfo(self, cmd_data):
        '''
        return Current Thread Status
        just tell them we're done...
        '''
        return b'l'

    def _serverQAttached(self):
        '''
        return whether we're attached?
        '''
        return b'1'

    def _serverQCRC(self, cmd_data):
        return b''

    def XferFeaturesReadTargetXml(self, fields):
        return getTargetXml(self.emu, self.emu._arch_name)

    def _serverQSetting(self, cmd_data):
        # TODO: finish
        #print("FIXME: serverQSetting(%r)" % cmd_data)
        if b':' in cmd_data:
            key, value = cmd_data.split(b':', 1)
            self._settings[key] = value
        else:
            self._settings[cmd_data] = True
        return b'OK'

    def _serverGetThread(self, cmd_data=None):
        # The thread syntax is p<process ID>:<thread ID>
        return b'p1:1'

    def _serverSetThread(self, cmd_data):
        # We really don't change threads for this target, just return OK
        return b'OK'

    def _serverGetCore(self, cmd_data=None):
        return b'1'

reg_xlate = set(['fpscr'])

def translateRegFrom(rname):
    if rname in reg_xlate:
        return rname.upper()

    return rname


def getTargetXml(emu, arch='ppc32-embedded'):
    global target, regdefs
    '''
    Takes in a RegisterContext and an archname.
    Returns an XML file as described in the gdb-remote spec 
    '''
    archmod = envi.getArchModule(emu._arch_name)

    gdbarchname = 'powerpc:vle'
    regdefs = {}
    for regnum, (rname, bitsize) in enumerate(emu.getRegDef()):
        regdefs[rname] = (regnum, bitsize)

    # features defined in https://sourceware.org/gdb/current/onlinedocs/gdb/PowerPC-Features.html
    import xml.etree.ElementTree as ET

    target = ET.Element('target')

    arch = ET.SubElement(target, 'architecture')
    arch.text = gdbarchname

    feat_core = ET.SubElement(target, 'feature', {'name': 'org.gnu.gdb.power.core'})

    reggrps = archmod.archGetRegisterGroups()
    for rname in reggrps.get('gdb_power_core'):
        regnum, bitsize = regdefs[translateRegFrom(rname)]
        #print(rname, regnum, bitsize)
        ET.SubElement(feat_core, 'reg', {'bitsize':str(bitsize), 'name': rname, 'regnum': str(regnum) })

    feat_fpu = ET.SubElement(target, 'feature', {'name': 'org.gnu.gdb.power.fpu'})
    for rname in reggrps.get('gdb_power_fpu'):
        regnum, bitsize = regdefs[translateRegFrom(rname)]
        #print(rname, regnum, bitsize)
        ET.SubElement(feat_fpu, 'reg', {'bitsize':str(bitsize), 'name': rname, 'regnum': str(regnum) })

    feat_spr = ET.SubElement(target, 'feature', {'name': 'org.gnu.gdb.power.e200spr'})
    for rname in reggrps.get('gdb_power_spr'):
        regnum, bitsize = regdefs[translateRegFrom(rname)]
        ET.SubElement(feat_spr, 'reg', {'bitsize':str(bitsize), 'name': rname, 'regnum': str(regnum) })

    #feat_altivec = ET.SubElement(target, 'feature', {'name': 'org.gnu.gdb.power.altivec'})
    #for rname in reggrps.get('gdb_power_altivec'):
    #    regnum, bitsize = regdefs[translateRegFrom(rname)]
    #    ET.SubElement(feat_altivec, 'reg', {'bitsize':str(bitsize), 'name': rname, 'regnum': str(regnum) })

    #feat_spe = ET.SubElement(target, 'feature', {'name': 'org.gnu.gdb.power.spe'})
    #for rname in reggrps.get('gdb_power_spe'):
        #regnum, bitsize = regdefs[translateRegFrom(rname)]
        #ET.SubElement(feat_spe, 'reg', {'bitsize':str(bitsize), 'name': rname, 'regnum': str(regnum) })


    out = [b'<?xml version="1.0"?>',
            b'<!DOCTYPE target SYSTEM "gdb-target.dtd">']
    out.append(ET.tostring(target))

    return b'\n'.join(out)

