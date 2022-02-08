import struct
import unittest
import random
import os
import queue
import time
import itertools

import envi.archs.ppc.const as eapc
import envi.archs.ppc.regs as eapr

import envi.bits as e_bits
from cm2350 import intc_exc

from .. import CM2350

class MPC5674_SIM(unittest.TestCase):
    def setUp(self):
            import os
            if os.environ.get('LOG_LEVEL', 'INFO') == 'DEBUG':
                args = ['-m', 'test', '-c', '-vvv']
            else:
                args = ['-m', 'test', '-c']

            self.ECU = CM2350(args)
            self.emu = self.ECU.emu

            # Set the INTC[CPR] to 0 to allow all peripheral (external) exception
            # priorities to happen
            self.emu.intc.registers.cpr.pri = 0
            msr_val = self.emu.getRegister(eapr.REG_MSR)

            # Enable all possible Exceptions so if anything happens it will be
            # detected by the _getPendingExceptions utility
            msr_val |= eapc.MSR_EE_MASK | eapc.MSR_CE_MASK | eapc.MSR_ME_MASK | eapc.MSR_DE_MASK
            self.emu.setRegister(eapr.REG_MSR, msr_val)

            # Enable the timebase (normally done by writing a value to HID0)
            self.emu.enableTimebase()

    def _getPendingExceptions(self):
        pending_excs = []
        for intq in self.emu.mcu_intc.intqs[1:]:
            try:
                while True:
                    pending_excs.append(intq.get_nowait())
            except queue.Empty:
                pass
        return pending_excs

    #This is for the proc in the cm2350
    def test_SIM(self):
        self.assertEqual(self.emu.readMemValue(0xfffec000,4), 0x9F03171C)
        self.assertEqual(self.emu.readMemValue(0xfffec004,4), 0xCFBCFFFF)
        self.assertEqual(self.emu.readMemValue(0xfffec010,4), 0x01FFFFFF)
        self.assertEqual(self.emu.readMemValue(0xfffec014,4), 0xFF444534)
        self.assertEqual(self.emu.readMemValue(0xfffec018,4), 0x33383837)
        self.assertEqual(self.emu.readMemValue(0xfffec01c,4), 0x11011014)

    def test_undefined_offsets(self):
        # Verify a few memory addresses which are not defined in the SIM
        # peripheral properly generate errors when they are read from

        self.validate_invalid_read(0xFFFEC008, 4)
        self.validate_invalid_read(0xFFFEC00C, 4)
        self.validate_invalid_read(0xFFFEC020, 4)
        self.validate_invalid_read(0xFFFEC024, 4)

    def test_attempt_write(self):
        self.emu.writeMemValue(0xfffec000, 0x12345678, 4)
        self.emu.writeMemValue(0xfffec004, 0x12345678, 4)
        self.emu.writeMemValue(0xfffec010, 0x12345678, 4)
        self.emu.writeMemValue(0xfffec014, 0x12345678, 4)
        self.emu.writeMemValue(0xfffec018, 0x12345678, 4)
        self.emu.writeMemValue(0xfffec01c, 0x12345678, 4)

        self.assertEqual(self.emu.readMemValue(0xfffec000,4), 0x9F03171C)
        self.assertEqual(self.emu.readMemValue(0xfffec004,4), 0xCFBCFFFF)
        self.assertEqual(self.emu.readMemValue(0xfffec010,4), 0x01FFFFFF)
        self.assertEqual(self.emu.readMemValue(0xfffec014,4), 0xFF444534)
        self.assertEqual(self.emu.readMemValue(0xfffec018,4), 0x33383837)
        self.assertEqual(self.emu.readMemValue(0xfffec01c,4), 0x11011014)

    def tearDown(self):
        # Ensure that there are no unprocessed exceptions
        pending_excs = self._getPendingExceptions()
        for exc in pending_excs:
            print('Unhanded PPC Exception %s' % exc)
        self.assertEqual(pending_excs, [])

    ##################################################
    # Useful utilities for tests
    ##################################################

    def validate_invalid_read(self, addr, size):
        '''
        For testing addresses that raise a bus error on read
        '''
        pc = self.get_random_pc()
        self.emu.setProgramCounter(pc)

        msg = 'invalid read from 0x%x' % (addr)
        with self.assertRaises(intc_exc.MceDataReadBusError, msg=msg) as cm:
            self.emu.readMemValue(addr, size)

        args = {
            'va': addr,
            'pc': pc,
            'data': b'',
        }
        self.assertEqual(cm.exception.kwargs, args)

    def validate_invalid_write(self, addr, size, msg=None):
        '''
        For testing addresses that raise a bus error on write (like read-only
        memory locations)
        '''
        value, value_bytes = self.get_random_val(size)

        pc = self.get_random_pc()
        self.emu.setProgramCounter(pc)

        if msg is None:
            msg = 'invalid write of 0x%x to 0x%x' % (value, addr)
        else:
            msg = 'invalid write of 0x%x to 0x%x (%s)' % (value, addr, msg)

        with self.assertRaises(intc_exc.MceWriteBusError, msg=msg) as cm:
            self.emu.writeMemValue(addr, value, size)

        args = {
            'va': addr,
            'pc': pc,
            'data': value_bytes,
            'written': 0,
        }
        self.assertEqual(cm.exception.kwargs, args)

    def set_random_pc(self):
        pc = self.get_random_pc()
        self.emu.setProgramCounter(pc)
        return pc

    def get_random_pc(self):
        start, end, perms, filename = self.emu.getMemoryMap(0)
        return random.randrange(start, end, 4)
