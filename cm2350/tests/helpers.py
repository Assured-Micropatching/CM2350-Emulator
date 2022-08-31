import gc
import os
import queue
import random
import unittest

import envi.bits as e_bits
import envi.common as e_common
import envi.archs.ppc.spr as eaps
import envi.archs.ppc.regs as eapr
import envi.archs.ppc.const as eapc

from .. import CM2350, intc_exc, ppc_vstructs

import logging
logger = logging.getLogger(__name__)


__all__ = [
    'MPC5674_Test',
]


class MPC5674_Test(unittest.TestCase):
    args = ['-m', 'test', '-c']

    # When set to False automatically sets the following options:
    #   - _start_timebase_paused = False
    #   - _systime_scaling = 1
    #   - _disable_gc = False
    #
    # When set to True automatically sets the following options:
    #   - _start_timebase_paused = True
    #   - _systime_scaling = 0.1
    #   - _disable_gc = True
    #
    # If any of the specific performance settings are not None, the specific
    # performance setting will be used instead of the default.
    accurate_timing = False
    _systime_scaling = None
    _start_timebase_paused = None
    _disable_gc = None

    def setUp(self):
        if os.environ.get('LOG_LEVEL', 'INFO') == 'DEBUG':
            e_common.initLogging(logger, logging.DEBUG)
            #self.args.append('-vvv')

        if self._systime_scaling is None:
            self._systime_scaling = 0.1 if self.accurate_timing else 1.0
        if self._start_timebase_paused is None:
            self._start_timebase_paused = True if self.accurate_timing else False
        if self._disable_gc is None:
            self._disable_gc = True if self.accurate_timing else False

        logger.debug('Creating CM2350 with args: %s' % ', '.join(self.args))
        self.ECU = CM2350(self.args)
        self.emu = self.ECU.emu

        # Set the emulator systime scaling
        self.emu._systime_scaling = self._systime_scaling

        # Check if the garbage collector should be disabled for these tests
        if self._disable_gc:
            gc.disable()

        # Set the INTC[CPR] to 0 to allow all peripheral (external) exception
        # priorities to happen
        self.emu.intc.registers.cpr.pri = 0
        msr_val = self.emu.getRegister(eapr.REG_MSR)

        # Enable all possible Exceptions so if anything happens it will be
        # detected by the _getPendingExceptions utility
        msr_val |= eapc.MSR_EE_MASK | eapc.MSR_CE_MASK | eapc.MSR_ME_MASK | eapc.MSR_DE_MASK
        self.emu.setRegister(eapr.REG_MSR, msr_val)

        # Enable the timebase (normally done by writing a value to HID0)
        self.emu.enableTimebase(start_paused=self._start_timebase_paused)

    def _getPendingExceptions(self):
        # Remove all the exceptions in the pending list
        pending = self.emu.mcu_intc.pending
        self.emu.mcu_intc.pending = []
        return pending

    def tearDown(self):
        # Ensure that there are no unprocessed exceptions
        pending_excs = self._getPendingExceptions()
        for exc in pending_excs:
            print('Unhanded PPC Exception %s' % exc)
        self.assertEqual(pending_excs, [])

        # Clean up the resources
        self.ECU.shutdown()
        del self.emu
        del self.ECU

        # Re-enable the garbage collector if it was disabled and force memory
        # cleanup now
        if self._disable_gc:
            gc.enable()
            gc.collect()

    ##################################################
    # Helper utility functions
    ##################################################

    def get_random_pc(self):
        start, end, perms, filename = self.emu.getMemoryMap(0)
        return random.randrange(start, end, 4)

    def set_random_pc(self):
        test_pc = self.get_random_pc()
        self.emu.setProgramCounter(test_pc)
        return test_pc

    def get_random_val(self, size):
        val_bytes = os.urandom(size)
        val = e_bits.parsebytes(val_bytes, 0, size, bigend=self.emu.getEndian())
        return (val, val_bytes)

    def get_random_flash_addr_and_data(self):
        start, end = self.emu.flash_mmaps[0]
        addr = random.randrange(start, end, 4)

        # Determine write size and generate some data
        size = random.choice((1, 2, 4))
        value, _ = self.get_random_val(size)

        return (addr, value, size)

    def get_random_ram_addr_and_data(self):
        start, end = self.emu.ram_mmaps[0]
        addr = random.randrange(start, end, 4)

        # Determine write size and generate some data
        size = random.choice((1, 2, 4))
        value, _ = self.get_random_val(size)

        return (addr, value, size)

    def validate_invalid_read(self, addr, size, data=None, msg=None):
        '''
        For testing addresses that raise a bus error on read
        '''
        pc = self.set_random_pc()

        if data is None:
            data = b''

        if msg is None:
            msg = 'invalid read from 0x%x' % (addr)
        else:
            msg = 'invalid read from 0x%x (%s)' % (addr, msg)

        with self.assertRaises(intc_exc.MceDataReadBusError, msg=msg) as cm:
            self.emu.readMemValue(addr, size)

        self.assertEqual(cm.exception.kwargs['va'], addr, msg=msg)
        self.assertEqual(cm.exception.kwargs['pc'], pc, msg=msg)
        self.assertEqual(cm.exception.kwargs['data'], data, msg=msg)

    def validate_unaligned_read(self, addr, size, data=None, msg=None):
        '''
        For testing addresses that raise an alignment error on read
        '''
        pc = self.set_random_pc()

        if data is None:
            data = b''

        if msg is None:
            msg = 'unaligned read from 0x%x' % (addr)
        else:
            msg = 'unaligned read from 0x%x (%s)' % (addr, msg)

        with self.assertRaises(intc_exc.AlignmentException, msg=msg) as cm:
            self.emu.readMemValue(addr, size)

        self.assertEqual(cm.exception.kwargs['va'], addr, msg=msg)
        self.assertEqual(cm.exception.kwargs['pc'], pc, msg=msg)
        self.assertEqual(cm.exception.kwargs['data'], data, msg=msg)

    def validate_invalid_write(self, addr, size, written=0, msg=None):
        '''
        For testing addresses that raise a bus error on write (like read-only
        memory locations)
        '''
        pc = self.set_random_pc()

        value, value_bytes = self.get_random_val(size)
        print(hex(value), value_bytes.hex(), self.emu.getEndian())

        if msg is None:
            msg = 'unaligned write of 0x%s to 0x%x' % (value_bytes.hex(), addr)
        else:
            msg = 'unaligned write of 0x%s to 0x%x (%s)' % (value_bytes.hex(), addr, msg)

        with self.assertRaises(intc_exc.MceWriteBusError, msg=msg) as cm:
            self.emu.writeMemValue(addr, value, size)

        import traceback
        traceback.print_exception(cm.exception)

        self.assertEqual(cm.exception.kwargs['va'], addr, msg=msg)
        self.assertEqual(cm.exception.kwargs['pc'], pc, msg=msg)
        self.assertEqual(cm.exception.kwargs['data'], value_bytes[:written], msg=msg)

    def validate_unaligned_write(self, addr, size=0, data=None, written=0, msg=None):
        '''
        For testing addresses that raise an unaligned on write.
        '''
        pc = self.set_random_pc()

        assert size or data

        if data is None:
            data = os.urandom(size)

        if msg is None:
            msg = 'invalid write of 0x%s to 0x%x' % (data.hex(), addr)
        else:
            msg = 'invalid write of 0x%s to 0x%x (%s)' % (data.hex(), addr, msg)

        with self.assertRaises(intc_exc.AlignmentException, msg=msg) as cm:
            self.emu.writeMemory(addr, data)

        self.assertEqual(cm.exception.kwargs['va'], addr, msg=msg)
        self.assertEqual(cm.exception.kwargs['pc'], pc, msg=msg)
        self.assertEqual(cm.exception.kwargs['data'], data[:written], msg=msg)

    def validate_invalid_addr(self, addr, size, msg=None):
        '''
        "Invalid" has multiple meanings for the SIU, this function tests that
        addresses within the SIU range produce bus errors for both reads and
        writes
        '''
        self.validate_invalid_read(addr, size, msg=msg)
        self.validate_invalid_write(addr, size, msg=msg)

    def validate_unimplemented_addrs(self, addr, size):
        '''
        Confirm that the unimplemented register range raises
        VStructUnimplementedError
        '''
        pc = self.set_random_pc()

        msg = 'Read unimplemented memory @ 0x%08x' % addr
        with self.assertRaises(ppc_vstructs.VStructUnimplementedError, msg=msg) as cm:
            self.emu.readMemValue(addr, size)

        self.assertEqual(cm.exception.kwargs['pc'], pc)
        self.assertEqual(cm.exception.kwargs['va'], addr)
        self.assertEqual(cm.exception.kwargs['data'], b'')
        self.assertEqual(cm.exception.kwargs['size'], size)

        val, val_bytes = self.get_random_val(size)
        msg = 'Write unimplemented memory @ 0x%08x' % addr
        with self.assertRaises(ppc_vstructs.VStructUnimplementedError, msg=msg) as cm:
            self.emu.writeMemValue(addr, val, size)

        self.assertEqual(cm.exception.kwargs['pc'], pc)
        self.assertEqual(cm.exception.kwargs['va'], addr)
        self.assertEqual(cm.exception.kwargs['data'], b'')
        self.assertEqual(cm.exception.kwargs['size'], size)

    def get_spr_num(self, reg):
        regname = self.emu.getRegisterName(reg)
        return next(num for num, (name, _, _) in eaps.sprs.items() if name == regname)
