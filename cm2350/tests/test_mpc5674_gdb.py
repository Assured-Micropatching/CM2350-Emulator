import os
import time
import fcntl
import signal
import unittest
import threading
import subprocess

from .helpers import MPC5674_Test, initLogging

import envi.common as e_cmn
import envi.archs.ppc.regs as eapr

from cm2350.mpc5674 import MPC5674_Emulator
from cm2350.intc_exc import GdbServerHaltEvent

from ..ppc_mmu import PpcTlbPageSize

import logging
logger = logging.getLogger(__name__)


class MPC5674_BAM_GDB_Test(MPC5674_Test):
    args = MPC5674_Test.args + ['-g']
    maxDiff = 10000

    def ctrl_c(self):
        self.gdb.send_signal(signal.SIGINT)

    def write(self, data, end='\r\n'):
        if end and not data.endswith('\r\n'):
            data += '\r\n'
        self.gdb.stdin.write(data.encode())
        self.gdb.stdin.flush()

    def _read(self, fd, until=None, timeout=None):
        start = time.time()

        self._buffer = ''
        while True:
            val = self.gdb.stdout.read(1024)
            if val is None:
                if until is None and \
                        (timeout is None or time.time() - start >= timeout):
                    break
                time.sleep(0.1)
            else:
                self._buffer += val.decode()

                if until is not None and until in self._buffer:
                    break

        out = None
        if until is not None:
            idx = self._buffer.find(until)
            if idx != -1:
                out = self._buffer[:idx+len(until)]
                self._buffer = self._buffer[idx+len(until):]

        if out is None:
            out = self._buffer
            self._buffer = ''

        logger.log(e_cmn.MIRE, 'read(%s, until=%r, timeout=%r) elapsed time %f = %s',
                   until, timeout, time.time()-start, out)

        return out

    def read(self, until=None, timeout=None, ignore_errors=False):
        out = self._read(self.gdb.stdout, until, timeout)

        # Read any stderr output that has happened and log it
        err = self.gdb.stderr.read()
        if err and not ignore_errors:
            err = err.rstrip().decode()
            self.fail(err)

        return out

    def run_emu(self):
        try:
            self.emu.run()
        except GdbServerHaltEvent:
            pass

    def setUp(self):
        super().setUp()

        # Give the emulator time to start
        time.sleep(2)

        # TODO: we need to build that disassembler into vivisect...

        # Fill in a bunch of NOPs starting at the current PC (0x00000000). But 
        # put a few different types of branches so we can test that the gdb 
        # client is able to properly step through and control different 
        # instructions.
        #
        #   0x00000000:  60000000  ori r0,r0,0
        #   ...
        #   0x0000004c:  60000000  ori r0,r0,0
        #   0x00000050:  3c604000  lis r3,0x4000
        #   0x00000054:  2c030000  cmpi r3,0
        #   0x00000058:  41810008  bgt 0x00000060
        #   0x0000005c:  3be00001  li r31,1
        #   0x00000060:  60000000  ori r0,r0,0
        #   ...
        #   0x000000ac:  60000000  ori r0,r0,0
        #   0x000000b0:  39000000  li r8,0
        #   0x000000b4:  7d0903a6  mtctr r8
        #   0x000000b8:  4e800420  bctr
        #   0x000000bc:  60000000  ori r0,r0,0
        #   ...
        #   0x000000f8:  60000000  ori r0,r0,0
        #   0x000000fc:  48000006  ba 0x00000004
        #
        pc = self.emu.getProgramCounter()
        instrs = b''.join(([b'\x60\x00\x00\x00'] * 20) + \
                [b'\x3c\x60\x40\x00',
                 b'\x2c\x03\x00\x00',
                 b'\x41\x81\x00\x08',
                 b'\x3b\xe0\x00\x01'] + \
                ([b'\x60\x00\x00\x00'] * 20) + \
                [b'\x39\x00\x00\x00',
                 b'\x7d\x09\x03\xa6',
                 b'\x4e\x80\x04\x20'] + \
                ([b'\x60\x00\x00\x00'] * 16) + \
                [b'\x48\x00\x00\x06'])
        self.assertEqual(len(instrs), 0x100)

        self.emu.flash.data[pc:pc+len(instrs)] = instrs

        # Run the emulator
        self.thread = threading.Thread(target=self.run_emu, daemon=True)
        self.thread.start()

        # spawn GDB
        gdb_args = [
            'gdb-multiarch',
            '-nx',
            '-ex', 'set pagination off',
            '-ex', 'target remote localhost:47001',
            '-ex', 'set endian big',
        ]
        self.gdb = subprocess.Popen(gdb_args,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    stdin=subprocess.PIPE)

        self._buffer = ''

        # Make stdout and stderr nonblocking
        flags = fcntl.fcntl(self.gdb.stdout, fcntl.F_GETFL)
        fcntl.fcntl(self.gdb.stdout, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        flags = fcntl.fcntl(self.gdb.stderr, fcntl.F_GETFL)
        fcntl.fcntl(self.gdb.stderr, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        # Wait until the (gdb) prompt is printed
        self.read(until='(gdb) ', timeout=1, ignore_errors=True)

    def tearDown(self):
        # Queue the halt signal to stop the emulator thread, as soon as the 
        # debugger disconnects the emulator will start executing.
        self.emu.queueException(GdbServerHaltEvent())

        self.write('detach')
        self.write('quit')
        self.gdb.stdin.close()
        self.gdb.stdout.close()
        self.gdb.stderr.close()

        ret = self.gdb.wait(1)
        self.assertNotEqual(ret, None)

        super().tearDown()

    def test_gdb_info_reg(self):
        self.write('info reg')
        out = self.read(timeout=1)

        # The MSR in the following test is set to the following value by the 
        # helper.MPC5674_Test class initialization:
        #   0x29200: MSR_EE_MASK | MSR_CE_MASK | MSR_ME_MASK | MSR_DE_MASK

        # TODO: this feels janky, how to improve?
        expected = '''r0             0x0                 0
r1             0x0                 0
r2             0x0                 0
r3             0x0                 0
r4             0x0                 0
r5             0x0                 0
r6             0x0                 0
r7             0x0                 0
r8             0x0                 0
r9             0x0                 0
r10            0x0                 0
r11            0x0                 0
r12            0x0                 0
r13            0x0                 0
r14            0x0                 0
r15            0x0                 0
r16            0x0                 0
r17            0x0                 0
r18            0x0                 0
r19            0x0                 0
r20            0x0                 0
r21            0x0                 0
r22            0x0                 0
r23            0x0                 0
r24            0x0                 0
r25            0x0                 0
r26            0x0                 0
r27            0x0                 0
r28            0x0                 0
r29            0x0                 0
r30            0x0                 0
r31            0x0                 0
pc             0x0                 0x0
msr            0x29200             168448
cr             0x0                 0
lr             0x0                 0
ctr            0x0                 0
xer            0x0                 0
acc            0x0                 0
spefscr        0x0                 0
DEC            0x0                 0
SRR0           0x0                 0
SRR1           0x0                 0
PID            0x0                 0
DECAR          0x0                 0
LPER           0x0                 0
LPERU          0x0                 0
CSRR0          0x0                 0
CSRR1          0x0                 0
DEAR           0x0                 0
ESR            0x0                 0
IVPR           0x0                 0
TBL            0x0                 0
TBU            0x0                 0
PIR            0x0                 0
PVR            0x0                 0
DBSR           0x0                 0
DBSRWR         0x0                 0
EPCR           0x0                 0
DBCR0          0x0                 0
DBCR1          0x0                 0
DBCR2          0x0                 0
MSRP           0x0                 0
IAC1           0x0                 0
IAC2           0x0                 0
IAC3           0x0                 0
IAC4           0x0                 0
DAC1           0x0                 0
DAC2           0x0                 0
DVC1           0x0                 0
DVC2           0x0                 0
TSR            0x0                 0
LPIDR          0x0                 0
TCR            0x0                 0
IVOR0          0x0                 0
IVOR1          0x0                 0
IVOR2          0x0                 0
IVOR3          0x0                 0
IVOR4          0x0                 0
IVOR5          0x0                 0
IVOR6          0x0                 0
IVOR7          0x0                 0
IVOR8          0x0                 0
IVOR9          0x0                 0
IVOR10         0x0                 0
IVOR11         0x0                 0
IVOR12         0x0                 0
IVOR13         0x0                 0
IVOR14         0x0                 0
IVOR15         0x0                 0
IVOR38         0x0                 0
IVOR39         0x0                 0
IVOR40         0x0                 0
IVOR41         0x0                 0
IVOR42         0x0                 0
TENSR          0x0                 0
TENS           0x0                 0
TENC           0x0                 0
TIR            0x0                 0
L1CFG0         0x0                 0
L1CFG1         0x0                 0
NPIDR5         0x0                 0
L2CFG0         0x0                 0
IVOR32         0x0                 0
IVOR33         0x0                 0
IVOR34         0x0                 0
IVOR35         0x0                 0
IVOR36         0x0                 0
IVOR37         0x0                 0
DBCR3          0x0                 0
DBCNT          0x0                 0
DBCR4          0x0                 0
DBCR5          0x0                 0
MCARU          0x0                 0
MCSRR0         0x0                 0
MCSRR1         0x0                 0
MCSR           0x0                 0
MCAR           0x0                 0
DSRR0          0x0                 0
DSRR1          0x0                 0
DDAM           0x0                 0
L1CSR2         0x0                 0
L1CSR3         0x0                 0
MAS0           0x0                 0
MAS1           0x0                 0
MAS2           0x0                 0
MAS3           0x0                 0
MAS4           0x0                 0
MAS6           0x0                 0
PID1           0x0                 0
PID2           0x0                 0
EDBRAC0        0x0                 0
TLB0CFG        0x0                 0
TLB1CFG        0x200be020          537649184
TLB2CFG        0x0                 0
TLB3CFG        0x0                 0
DBRR0          0x0                 0
EPR            0x0                 0
L2ERRINTEN     0x0                 0
L2ERRATTR      0x0                 0
L2ERRADDR      0x0                 0
L2ERREADDR     0x0                 0
L2ERRCTL       0x0                 0
L2ERRDIS       0x0                 0
L1FINV1        0x0                 0
DEVENT         0x0                 0
NSPD           0x0                 0
NSPC           0x0                 0
L2ERRINJHI     0x0                 0
L2ERRINJLO     0x0                 0
L2ERRINJCTL    0x0                 0
L2CAPTDATAHI   0x0                 0
L2CAPTDATALO   0x0                 0
L2CAPTECC      0x0                 0
L2ERRDET       0x0                 0
HID0           0x0                 0
HID1           0x0                 0
L1CSR0         0x0                 0
L1CSR1         0x0                 0
MMUCSR0        0x0                 0
BUCSR          0x0                 0
MMUCFG         0x4009c4            4196804
L1FINV0        0x0                 0
L2CSR0         0x0                 0
L2CSR1         0x0                 0
PWRMGTCR0      0x0                 0
SCCSRBAR       0x0                 0
SVR            0x0                 0
(gdb) '''

        self.assertEqual(out, expected)

    def test_gdb_set_reg(self):
        # (gdb) set $r2 = 0x12345678
        # (gdb) p/x $r2
        # $1 = 0x12345678
        # (gdb) set $r2 = 0x123456789ABCDEF
        # (gdb) p/x $r2
        # $2 = 0x89abcdef
        self.write('set $r2 = 0x12345678')
        self.read(until='(gdb) ', timeout=1)

        self.write('p/x $r2')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$1 = 0x12345678
(gdb) ''')

        self.assertEqual(self.emu.getRegister(eapr.REG_R2), 0x12345678)

        self.write('set $r2 = 0x123456789abcdef')
        self.read(until='(gdb) ', timeout=1)

        self.write('p/x $r2')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$2 = 0x89abcdef
(gdb) ''')

        self.assertEqual(self.emu.getRegister(eapr.REG_R2), 0x89abcdef)

    def test_gdb_set_mem(self):
        # (gdb) set {int} 0x40000000 = 0x12345678
        # (gdb) p/x *0x40000000
        # $1 = 0x12345678
        # (gdb) set {int} 0x40000000 = 0x12345678abcdef
        # (gdb) p/x *0x40000000
        # $2 = 0x78abcdef
        self.write('set {int} 0x40000004 = 0x12345678')
        self.read(until='(gdb) ', timeout=1)

        self.write('x/4wx 0x40000000')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''0x40000000:\t0x00000000\t0x12345678\t0x00000000\t0x00000000
(gdb) ''')

        expected = bytes.fromhex('00000000 12345678 00000000 00000000')
        self.assertEqual(self.emu.readMemory(0x40000000, 16), expected)

        self.write('set {int} 0x40000008 = 0xfedcba987654321')
        self.read(until='(gdb) ', timeout=1)

        self.write('x/4wx 0x40000000')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''0x40000000:\t0x00000000\t0x12345678\t0x87654321\t0x00000000
(gdb) ''')

        expected = bytes.fromhex('00000000 12345678 87654321 00000000')
        self.assertEqual(self.emu.readMemory(0x40000000, 16), expected)

        self.write('set {char} 0x40000002 = 0xff')
        self.read(until='(gdb) ', timeout=1)

        self.write('x/4wx 0x40000000')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''0x40000000:\t0x0000ff00\t0x12345678\t0x87654321\t0x00000000
(gdb) ''')

        expected = bytes.fromhex('0000ff00 12345678 87654321 00000000')
        self.assertEqual(self.emu.readMemory(0x40000000, 16), expected)

        self.write('set {char} 0x40000005 = 0xff')
        self.read(until='(gdb) ', timeout=1)

        self.write('x/4wx 0x40000000')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''0x40000000:\t0x0000ff00\t0x12ff5678\t0x87654321\t0x00000000
(gdb) ''')

        expected = bytes.fromhex('0000ff00 12ff5678 87654321 00000000')
        self.assertEqual(self.emu.readMemory(0x40000000, 16), expected)

    def test_gdb_stepi(self):
        # (gdb) p/x $pc
        # $1 = 0x00000000
        # (gdb) x/i $pc
        # 0x00000000:  nop
        # (gdb) stepi
        # (gdb) p/x $pc
        # $2 = 0x00000004
        # (gdb) set $pc = 0x50
        # (gdb) p/x $pc
        # $3 = 0x00000050
        # (gdb) x/i $pc
        # 0x00000050:  lis r3,0x4000
        # (gdb) stepi
        # (gdb) p/x $pc
        # $4 = 0x00000054
        # (gdb) p/x $r3
        # $5 = 0x40000000
        self.write('p/x $pc')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$1 = 0x0
(gdb) ''')
        self.write('x/i $pc')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''=> 0x0:\tnop
(gdb) ''')
        self.assertEqual(self.emu.getRegister(eapr.REG_PC), 0x00000000)

        self.write('stepi')
        self.read(until='(gdb) ', timeout=1)
        self.write('p/x $pc')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$2 = 0x4
(gdb) ''')
        self.assertEqual(self.emu.getRegister(eapr.REG_PC), 0x00000004)

        self.write('set $pc = 0x50')
        self.read(until='(gdb) ', timeout=1)
        self.write('p/x $pc')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$3 = 0x50
(gdb) ''')
        self.write('x/i $pc')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''=> 0x50:\tlis     r3,16384
(gdb) ''')
        self.assertEqual(self.emu.getRegister(eapr.REG_PC), 0x00000050)
        self.assertEqual(self.emu.getRegister(eapr.REG_R3), 0x00000000)

        self.write('stepi')
        self.read(until='(gdb) ', timeout=1)
        self.write('p/x $pc')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$4 = 0x54
(gdb) ''')
        self.assertEqual(self.emu.getRegister(eapr.REG_PC), 0x00000054)

        self.write('p/x $r3')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$5 = 0x40000000
(gdb) ''')
        self.assertEqual(self.emu.getRegister(eapr.REG_R3), 0x40000000)

        # TODO branch test with changed compare reg value

    def test_gdb_breakpoint(self):
        self.write('p/x $pc')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$1 = 0x0
(gdb) ''')
        self.assertEqual(self.emu.getRegister(eapr.REG_PC), 0x00000000)

        self.write('break *0xb8')
        self.read(until='(gdb) ', timeout=1)
        self.write('continue')

        # should reach that quickly
        self.read(until='(gdb) ', timeout=0.1)

        self.write('p/x $pc')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$2 = 0xb8
(gdb) ''')
        self.assertEqual(self.emu.getRegister(eapr.REG_PC), 0x000000b8)

        # the CTR register should point to address 0
        self.write('p/x $ctr')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$3 = 0x0
(gdb) ''')
        self.assertEqual(self.emu.getRegister(eapr.REG_CTR), 0x00000000)

        # Ensure we go to 0
        self.write('stepi')
        self.read(until='(gdb) ', timeout=1)
        self.write('p/x $pc')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$4 = 0x0
(gdb) ''')
        self.assertEqual(self.emu.getRegister(eapr.REG_PC), 0x00000000)

        # continue again
        self.write('continue')
        self.read(until='(gdb) ', timeout=0.1)

        self.write('p/x $pc')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$5 = 0xb8
(gdb) ''')
        self.assertEqual(self.emu.getRegister(eapr.REG_PC), 0x000000b8)

        # Modify the CTR register
        self.write('set $ctr = 0xbc')
        self.read(until='(gdb) ', timeout=1)

        self.write('p/x $ctr')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$6 = 0xbc
(gdb) ''')

        self.assertEqual(self.emu.getRegister(eapr.REG_CTR), 0x000000bc)

        # Ensure we go to 0xbc
        self.write('stepi')
        self.read(until='(gdb) ', timeout=1)
        self.write('p/x $pc')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$7 = 0xbc
(gdb) ''')
        self.assertEqual(self.emu.getRegister(eapr.REG_PC), 0x000000bc)

        # continue again
        self.write('continue')
        self.read(until='(gdb) ', timeout=0.1)

        self.write('p/x $pc')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$8 = 0xb8
(gdb) ''')
        self.assertEqual(self.emu.getRegister(eapr.REG_PC), 0x000000b8)

        # current instruction should be a bctr
        self.write('x/i $pc')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''=> 0xb8:\tbctr
(gdb) ''')

    @unittest.skip("vFlashErase and vFlashWrite not implemented")
    def test_gdb_modify_flash(self):
        # Should be able to change it to a nop through the GDB interface
        # TODO: change to a load command:
        self.write('set {int} $pc = 0x60000000')
        self.read(until='(gdb) ', timeout=1)

        self.write('x/wx $pc')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''0xb8:\t0x60000000
(gdb) ''')

        self.write('x/i $pc')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''=> 0xb8:\tnop
(gdb) ''')

        self.assertEqual(self.emu.readMemory(0xb8, 4), bytes.fromhex('60000000'))

        # Ensure that the CTR register is currently 0 and we go to 0xbc
        self.write('p/x $ctr')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$9 = 0x0
(gdb) ''')
        self.assertEqual(self.emu.getRegister(eapr.REG_CTR), 0x00000000)

        self.write('stepi')
        self.read(until='(gdb) ', timeout=1)
        self.write('p/x $pc')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$10 = 0x0
(gdb) ''')
        self.assertEqual(self.emu.getRegister(eapr.REG_PC), 0x00000000)

    def test_gdb_continue_interrupt(self):
        self.write('p/x $pc')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$1 = 0x0
(gdb) ''')
        self.assertEqual(self.emu.getRegister(eapr.REG_PC), 0x00000000)

        self.write('continue')
        time.sleep(1)
        self.ctrl_c()
        self.read(until='(gdb) ', timeout=1)

        pc = self.emu.getRegister(eapr.REG_PC)

        self.write('p/x $pc')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$2 = 0x%x
(gdb) ''' % pc)

        # The instructions should continuously loop between PC's 0x4 and 0xFC
        self.assertIn(pc, range(0x00000004, 0x00000100))
        self.assertEqual(self.emu.getRegister(eapr.REG_PC), pc)

    def test_gdb_set_bitfield_spr(self):
        # Testing the registers defined as "BitFieldSPR" objects to ensure that 
        # GDB can write and read them and the correct values will be reflected 
        # on both the emulator and GDB client interface, and any side effects 
        # can be properly observed

        # Write to the TCR[WIE] bit to enable the MCU watchdog
        self.assertEqual(self.emu.tcr.wie, 0)
        self.assertEqual(self.emu.hid0.tben, 0)
        self.assertEqual(self.emu.mcu_wdt.running(), False)

        self.write('set $TCR = 0x08000000')
        self.read(until='(gdb) ', timeout=1)

        self.write('p/x $TCR')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$1 = 0x8000000
(gdb) ''')

        self.assertEqual(self.emu.tcr.wie, 1)
        self.assertEqual(self.emu.hid0.tben, 0)
        self.assertEqual(self.emu.mcu_wdt.running(), False)

        # then to HID0[TBEN] to enable the MCU timebase.
        self.write('set $HID0 = 0x08000000')
        self.read(until='(gdb) ', timeout=1)

        self.write('p/x $HID0 = 0x00004000')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$2 = 0x4000
(gdb) ''')

        # Ensure that the MCU watchdog has been started
        self.assertEqual(self.emu.tcr.wie, 1)
        self.assertEqual(self.emu.hid0.tben, 1)
        self.assertEqual(self.emu.mcu_wdt.running(), True)

    def test_gdb_set_invalidate_mmu(self):
        # Testing registers with defined SPR write hooks (but that aren't 
        # defined as bitfield SPR objects) to ensure that the proper write or 
        # read hooks are called

        # Add an unprotected TLB entry, then write to MMUCSR0[TLB1_FI] (bit 30) 
        # to invalidate all unprotected MMU entries.
        self.emu.mmu.tlbConfig(8, epn=0x12345000, rpn=0x40000000,
                               tsiz=PpcTlbPageSize.SIZE_4KB, ts=0, tid=0, iprot=0)
        self.assertEqual(self.emu.mmu._tlb[8].valid, 1)

        # Search for the 
        pc = self.emu.getProgramCounter()
        # 7C001F24  tlbsx 0,r3
        self.emu.flash.data[pc:pc+4] = bytes.fromhex('7C001F24')

        self.write('x/i $pc')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''=> 0x0:\ttlbsx   0,r3
(gdb) ''')

        # Write the value to search for to R3 and then execute the instruction
        self.write('set $r3 = 0x12345678')
        self.read(until='(gdb) ', timeout=1)
        self.assertEqual(self.emu.readRegValue(eapr.REG_R3), 0x12345678)

        self.write('stepi')
        self.read(until='(gdb) ', timeout=1)

        # MAS0-MAS3 should now have TLB entry 8 in it
        #   MAS0:   0x10080000 (entry 8)
        #   MAS1:   0x80000100 (valid, iprot=0, 4KB)
        #   MAS1:   0x12345000 (virt addr, no special bits set)
        #   MAS1:   0x4000003f (phys addr, full RWX)

        self.write('p/x $MAS0')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$1 = 0x10080000
(gdb) ''')
        self.assertEqual(self.emu.readRegValue(eapr.REG_MAS0), 0x10080000)
        self.write('p/x $MAS1')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$2 = 0x80000100
(gdb) ''')
        self.assertEqual(self.emu.readRegValue(eapr.REG_MAS1), 0x80000100)
        self.write('p/x $MAS2')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$3 = 0x12345000
(gdb) ''')
        self.assertEqual(self.emu.readRegValue(eapr.REG_MAS2), 0x12345000)
        self.write('p/x $MAS3')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$4 = 0x4000003f
(gdb) ''')
        self.assertEqual(self.emu.readRegValue(eapr.REG_MAS3), 0x4000003f)

        # Put a value in RAM and it should be able to be read the new virtual 
        # address
        self.emu.writeMemory(0x40000678, bytes.fromhex('11112222333344445555666677778888'))
        self.write('x/4wx 0x12345678')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''0x12345678:\t0x11112222\t0x33334444\t0x55556666\t0x77778888
(gdb) ''')

        # Now write to MMUCSR0[TLB1_FI]
        self.write('set $MMUCSR0 = 2')
        self.read(until='(gdb) ', timeout=1)

        self.write('p/x $MMUCSR0')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$5 = 0x0
(gdb) ''')

        self.assertEqual(self.emu.mmu._tlb[8].valid, 0)

        # Reading an invalid memory address through GDB will result in a bunch 
        # of 0's. This mimics how the P&E Micro GDB server works.
        self.write('x/4wx 0x12345678')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''0x12345678:\t0x00000000\t0x00000000\t0x00000000\t0x00000000
(gdb) ''')

    def test_gdb_set_invalidate_cache(self):
        # Write to L1CSR0[ICINV] and L1CSR1[ICINV] and ensure that bit 30 is not 
        # set in either register
        self.assertEqual(self.emu.readRegValue(eapr.REG_L1CSR0), 0)

        self.write('set $L1CSR0 = 0xffffffff')
        self.read(until='(gdb) ', timeout=1)

        self.write('p/x $L1CSR0')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$1 = 0xfffffffd
(gdb) ''')

        self.assertEqual(self.emu.readRegValue(eapr.REG_L1CSR0), 0xfffffffd)

        self.assertEqual(self.emu.readRegValue(eapr.REG_L1CSR1), 0)

        self.write('set $L1CSR1 = 0xffffffff')
        self.read(until='(gdb) ', timeout=1)

        self.write('p/x $L1CSR1')
        out = self.read(timeout=0.1)
        self.assertEqual(out, '''$2 = 0xfffffffd
(gdb) ''')

        self.assertEqual(self.emu.readRegValue(eapr.REG_L1CSR1), 0xfffffffd)
