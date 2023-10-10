import unittest

from .. import mmio
from ..ppc_mmu import PpcTlbPageSize, PpcTlbFlags, PpcTlbPerm

from .helpers import MPC5674_Test


BAM_RCHW_ADDRS = [
    0x00000000,
    0x00004000,
    0x00010000,
    0x0001C000,
    0x00020000,
    0x00030000,
]

DEFAULT_BOOKE_TLB = (
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_1MB,   'epn': 0xFFF00000, 'flags': PpcTlbFlags.IG,  'rpn': 0xFFF00000, 'user': 0, 'perm': PpcTlbPerm.SU_RWX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_16MB,  'epn': 0x00000000, 'flags': 0,               'rpn': 0x00000000, 'user': 0, 'perm': PpcTlbPerm.SU_RWX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_16MB,  'epn': 0x20000000, 'flags': 0,               'rpn': 0x20000000, 'user': 0, 'perm': PpcTlbPerm.SU_RWX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_256KB, 'epn': 0x40000000, 'flags': PpcTlbFlags.I,   'rpn': 0x40000000, 'user': 0, 'perm': PpcTlbPerm.SU_RWX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_1MB,   'epn': 0xC3F00000, 'flags': PpcTlbFlags.IG,  'rpn': 0xC3F00000, 'user': 0, 'perm': PpcTlbPerm.SU_RWX},
)

DEFAULT_VLE_TLB = (
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_1MB,   'epn': 0xFFF00000, 'flags': PpcTlbFlags.IG,  'rpn': 0xFFF00000, 'user': 0, 'perm': PpcTlbPerm.SU_RWX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_16MB,  'epn': 0x00000000, 'flags': PpcTlbFlags.VLE, 'rpn': 0x00000000, 'user': 0, 'perm': PpcTlbPerm.SU_RWX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_16MB,  'epn': 0x20000000, 'flags': PpcTlbFlags.VLE, 'rpn': 0x20000000, 'user': 0, 'perm': PpcTlbPerm.SU_RWX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_256KB, 'epn': 0x40000000, 'flags': PpcTlbFlags.I | PpcTlbFlags.VLE, 'rpn': 0x40000000, 'user': 0, 'perm': PpcTlbPerm.SU_RWX},
    {'valid': 1, 'iprot': 1, 'tid': 0, 'ts': 0, 'tsiz': PpcTlbPageSize.SIZE_1MB,   'epn': 0xC3F00000, 'flags': PpcTlbFlags.IG,  'rpn': 0xC3F00000, 'user': 0, 'perm': PpcTlbPerm.SU_RWX},
)

class MPC5674_Flash_BAM(MPC5674_Test):
    _start_timebase_paused = True

    def test_bam_flash_empty(self):
        # Confirm that by default no valid target was found
        self.assertEqual(self.emu.bam.rchw_addr, None)
        self.assertEqual(self.emu.bam.rchw.entry_point, 0)
        self.assertEqual(self.emu.getProgramCounter(), 0)

        # The BAM analyze function has already been run but run it explicitly
        # now and ensure it returns a failure
        self.assertEqual(self.emu.bam.analyze(), False)

    def test_bam_find_rchw(self):
        with mmio.supervisorMode(self.emu):
            self.emu.writeMemory(0, b'\x00\x5a\x00\x00\xaa\xaa\xaa\xaa')

        # reset to cause standard BAM processing
        self.emu.reset()

        self.assertEqual(self.emu.bam.rchw_addr, 0x00000000)
        self.assertEqual(self.emu.bam.rchw.entry_point, 0xAAAAAAAA)
        self.assertEqual(self.emu.getProgramCounter(), 0xAAAAAAAA)

        # Modify the value @ 0x00000000 and ensure it is no longer found
        with mmio.supervisorMode(self.emu):
            self.emu.writeMemory(0, b'\xff')

        # Modify the value after offset 0x10004 so the entry_point value changes
        with mmio.supervisorMode(self.emu):
            self.emu.writeMemory(0x4000, b'\x00\x5a\x00\x00\x20\x00\x00\x00')

        self.emu.reset()

        self.assertEqual(self.emu.bam.rchw_addr, 0x00004000)
        self.assertEqual(self.emu.bam.rchw.entry_point, 0x20000000)
        self.assertEqual(self.emu.getProgramCounter(), 0x20000000)

        # Modify the value @ 0x00004000 and ensure it is no longer found
        with mmio.supervisorMode(self.emu):
            self.emu.writeMemory(0x4000, b'\xff')

        # Modify the value after offset 0x10004 so the entry_point value changes
        with mmio.supervisorMode(self.emu):
            self.emu.writeMemory(0x10000, b'\x00\x5a\x00\x00\x40\x00\x00\x00')

        self.emu.reset()

        self.assertEqual(self.emu.bam.rchw_addr, 0x00010000)
        self.assertEqual(self.emu.bam.rchw.entry_point, 0x40000000)
        self.assertEqual(self.emu.getProgramCounter(), 0x40000000)

        # Modify the value @ 0x00010000 and ensure it is no longer found
        with mmio.supervisorMode(self.emu):
            self.emu.writeMemory(0x10000, b'\xff')

        # Modify the value after offset 0x1C004 so the entry_point value changes
        with mmio.supervisorMode(self.emu):
            self.emu.writeMemory(0x1c000, b'\x00\x5a\x00\x00\x00\x12\x34\x56')

        self.emu.reset()

        self.assertEqual(self.emu.bam.rchw_addr, 0x0001C000)
        self.assertEqual(self.emu.bam.rchw.entry_point, 0x00123456)
        self.assertEqual(self.emu.getProgramCounter(), 0x00123456)

        # Modify the value @ 0x0001C000 and ensure it is no longer found
        with mmio.supervisorMode(self.emu):
            self.emu.writeMemory(0x1c000, b'\xff')

        # Modify the value after offset 0x20004 so the entry_point value changes
        with mmio.supervisorMode(self.emu):
            self.emu.writeMemory(0x20000, b'\x00\x5a\x00\x00\x00\x00\x00\x00')

        self.emu.reset()

        self.assertEqual(self.emu.bam.rchw_addr, 0x00020000)
        self.assertEqual(self.emu.bam.rchw.entry_point, 0x00000000)
        self.assertEqual(self.emu.getProgramCounter(), 0x00000000)

        # Modify the value @ 0x00020000 and ensure it is no longer found
        with mmio.supervisorMode(self.emu):
            self.emu.writeMemory(0x20000, b'\xff')

        # Modify the value after offset 0x30004 so the entry_point value changes
        with mmio.supervisorMode(self.emu):
            self.emu.writeMemory(0x30000, b'\x00\x5a\x00\x00\x00\x00\x00\x10')

        self.emu.reset()

        self.assertEqual(self.emu.bam.rchw_addr, 0x00030000)
        self.assertEqual(self.emu.bam.rchw.entry_point, 0x00000010)
        self.assertEqual(self.emu.getProgramCounter(), 0x00000010)

        # Modify the value @ 0x00030000 and ensure no valid RCHW entries are
        # found
        with mmio.supervisorMode(self.emu):
            self.emu.writeMemory(0x30000, b'\xff')

        self.emu.reset()

        self.assertEqual(self.emu.bam.rchw_addr, None)
        self.assertEqual(self.emu.bam.rchw.entry_point, 0)
        self.assertEqual(self.emu.getProgramCounter(), 0)

    def test_bam_rchw_booke(self):
        with mmio.supervisorMode(self.emu):
            self.emu.writeMemory(0x4000, b'\x00\x5A\x00\x00\x40\x00\x00\x00')

        # reset to cause standard BAM processing
        self.emu.reset()

        self.assertEqual(self.emu.bam.rchw_addr, 0x00004000)
        self.assertEqual(self.emu.bam.rchw.entry_point, 0x40000000)
        self.assertEqual(self.emu.getProgramCounter(), 0x40000000)

        self.assertEqual(self.emu.bam.rchw.rsvd, 0)
        self.assertEqual(self.emu.bam.rchw.swt, 0)
        self.assertEqual(self.emu.bam.rchw.wte, 0)
        self.assertEqual(self.emu.bam.rchw.ps0, 0)
        self.assertEqual(self.emu.bam.rchw.vle, 0)

        # Ensure that the MPC4674F SWT is not running
        self.assertEqual(self.emu.swt.watchdog.running(), False)

        # Ensure that the e200z7 MCU Watchdog is not running
        self.assertEqual(self.emu.mcu_wdt.running(), False)

        # TLB checking code borrowed from MMU/TLB tests
        for esel in range(len(DEFAULT_BOOKE_TLB)):
            for attr, val in DEFAULT_BOOKE_TLB[esel].items():
                msg = 'tlb[%d].%s == 0x%x' % (esel, attr, val)
                self.assertEqual(getattr(self.emu.mmu._tlb[esel], attr), val, msg)

    def test_bam_rchw_vle(self):
        with mmio.supervisorMode(self.emu):
            self.emu.writeMemory(0x4000, b'\x01\x5A\x00\x00\x40\x00\x00\x00')

        # reset to cause standard BAM processing
        self.emu.reset()

        # System time should be disabled again after reset, re-enable it
        self.assertFalse(self.emu.timebaseRunning())
        self.emu.enableTimebase()
        self.assertTrue(self.emu.timebaseRunning())

        self.assertEqual(self.emu.bam.rchw_addr, 0x00004000)
        self.assertEqual(self.emu.bam.rchw.entry_point, 0x40000000)
        self.assertEqual(self.emu.getProgramCounter(), 0x40000000)

        self.assertEqual(self.emu.bam.rchw.rsvd, 0)
        self.assertEqual(self.emu.bam.rchw.swt, 0)
        self.assertEqual(self.emu.bam.rchw.wte, 0)
        self.assertEqual(self.emu.bam.rchw.ps0, 0)
        self.assertEqual(self.emu.bam.rchw.vle, 1)

        # Ensure that the MPC4674F SWT is not running
        self.assertEqual(self.emu.swt.watchdog.running(), False)

        # Ensure that the e200z7 MCU Watchdog is not running
        self.assertEqual(self.emu.mcu_wdt.running(), False)

        # TLB checking code borrowed from MMU/TLB tests
        for esel in range(len(DEFAULT_VLE_TLB)):
            for attr, val in DEFAULT_VLE_TLB[esel].items():
                msg = 'tlb[%d].%s == 0x%x' % (esel, attr, val)
                self.assertEqual(getattr(self.emu.mmu._tlb[esel], attr), val, msg)

    def test_bam_rchw_swt(self):
        with mmio.supervisorMode(self.emu):
            self.emu.writeMemory(0x4000, b'\x08\x5A\x00\x00\x40\x00\x00\x00')

        # reset to cause standard BAM processing
        self.emu.reset()

        # System time should be disabled again after reset, re-enable it
        self.assertFalse(self.emu.timebaseRunning())
        self.emu.enableTimebase()
        self.assertTrue(self.emu.timebaseRunning())

        self.assertEqual(self.emu.bam.rchw_addr, 0x00004000)
        self.assertEqual(self.emu.bam.rchw.entry_point, 0x40000000)
        self.assertEqual(self.emu.getProgramCounter(), 0x40000000)

        self.assertEqual(self.emu.bam.rchw.rsvd, 0)
        self.assertEqual(self.emu.bam.rchw.swt, 1)
        self.assertEqual(self.emu.bam.rchw.wte, 0)
        self.assertEqual(self.emu.bam.rchw.ps0, 0)
        self.assertEqual(self.emu.bam.rchw.vle, 0)

        # Ensure that the SWT watchdog is running
        self.assertEqual(self.emu.swt.watchdog.running(), True)

        # Ensure that the e200z7 MCU Watchdog is running
        self.assertEqual(self.emu.mcu_wdt.running(), False)

    @unittest.skip('fix implementation of MCU WDT so it runs correctly')
    def test_bam_rchw_mcu_wdt(self):
        with mmio.supervisorMode(self.emu):
            self.emu.writeMemory(0x4000, b'\x04\x5A\x00\x00\x40\x00\x00\x00')

        # reset to cause standard BAM processing
        self.emu.reset()

        # System time should be disabled again after reset, re-enable it
        self.assertFalse(self.emu.timebaseRunning())
        self.emu.enableTimebase()
        self.assertTrue(self.emu.timebaseRunning())

        self.assertEqual(self.emu.bam.rchw_addr, 0x00004000)
        self.assertEqual(self.emu.bam.rchw.entry_point, 0x40000000)
        self.assertEqual(self.emu.getProgramCounter(), 0x40000000)

        self.assertEqual(self.emu.bam.rchw.rsvd, 0)
        self.assertEqual(self.emu.bam.rchw.swt, 0)
        self.assertEqual(self.emu.bam.rchw.wte, 1)
        self.assertEqual(self.emu.bam.rchw.ps0, 0)
        self.assertEqual(self.emu.bam.rchw.vle, 0)

        # Ensure that the SWT watchdog is not running
        self.assertEqual(self.emu.swt.watchdog.running(), False)

        # Ensure that the e200z7 MCU Watchdog is running
        self.assertEqual(self.emu.mcu_wdt.running(), True)

    @unittest.skip('fix implementation of MCU WDT so it runs correctly')
    def test_bam_rchw_swt_and_mcu_wdt(self):
        with mmio.supervisorMode(self.emu):
            self.emu.writeMemory(0x4000, b'\x0C\x5A\x00\x00\x40\x00\x00\x00')

        # reset to cause standard BAM processing
        self.emu.reset()

        # System time should be disabled again after reset, re-enable it
        self.assertFalse(self.emu.timebaseRunning())
        self.emu.enableTimebase()
        self.assertTrue(self.emu.timebaseRunning())

        self.assertEqual(self.emu.bam.rchw_addr, 0x00004000)
        self.assertEqual(self.emu.bam.rchw.entry_point, 0x40000000)
        self.assertEqual(self.emu.getProgramCounter(), 0x40000000)

        self.assertEqual(self.emu.bam.rchw.rsvd, 0)
        self.assertEqual(self.emu.bam.rchw.swt, 1)
        self.assertEqual(self.emu.bam.rchw.wte, 1)
        self.assertEqual(self.emu.bam.rchw.ps0, 0)
        self.assertEqual(self.emu.bam.rchw.vle, 0)

        # Ensure that the SWT watchdog is running
        self.assertEqual(self.emu.swt.watchdog.running(), True)

        # Ensure that the e200z7 MCU Watchdog is running
        self.assertEqual(self.emu.mcu_wdt.running(), True)
