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

from .. import CM2350, intc_exc

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
        pending_excs = []
        for intq in self.emu.mcu_intc.intqs[1:]:
            try:
                while True:
                    pending_excs.append(intq.get_nowait())
            except queue.Empty:
                pass
        return pending_excs

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
        val = random.getrandbits(size * 8)
        val_bytes = e_bits.buildbytes(val, size, self.emu.getEndian())
        return (val, val_bytes)

    def get_random_ram_addr_and_data(self):
        start, end = self.emu.ram_mmaps[0]
        addr = random.randrange(start, end, 4)

        # Determine write size and generate some data
        size = random.choice((1, 2, 4))
        value = random.getrandbits(size * 8)

        return (addr, value, size)

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

    def validate_invalid_addr(self, addr, size):
        '''
        "Invalid" has multiple meanings for the SIU, this function tests that
        addresses within the SIU range produce bus errors for both reads and
        writes
        '''
        self.validate_invalid_read(addr, size)
        self.validate_invalid_write(addr, size)

    def get_spr_num(self, reg):
        regname = self.emu.getRegisterName(reg)
        return next(num for num, (name, _, _) in eaps.sprs.items() if name == regname)
