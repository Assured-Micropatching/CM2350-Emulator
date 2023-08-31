# the core of the CM2350 simulator

import enum

import vivisect.cli as v_cli
import envi.archs.ppc.emu as eape

from .mpc5674 import MPC5674_Emulator
from . import project
from . import ppc_peripherals
from .peripherals.dspi import PlaceholderSPIDevice

import logging
logger = logging.getLogger(__name__)


__all__ = [
    'CM2350',
]


DEFAULT_PROJECT_NAME = 'AMP'


class ASIC_SPI_CMD(enum.IntEnum):
    READ        = 0b00
    WRITE_LOWER = 0b01
    WRITE_UPPER = 0b10
    WRITE_SEQ   = 0b11


class ASIC(ppc_peripherals.BusPeripheral):
    def __init__(self, emu, bus, cs):
        ppc_peripherals.BusPeripheral.__init__(self, emu, 'ASIC', bus, cs)

        # The watchdog timer has a resolution of 1 tick == 512 microseconds
        # which equals a frequency of 1953.125 Hz
        self.watchdog = emu.registerTimer(name='asic_watchdog',
                                          callback=self.asicWatchdogHandler, 
                                          freq=1_000_000 / 512)

        self.addr = None

        self.registers = {
            # register 0 is the fault register
            0x00: 0x303F,

            # register 2 is the watchdog timer
            0x02: 0x00FF,
            0x03: 0x0000,
        }

        # Start the watchdog now
        self.watchdog.start(ticks=self.registers[0x02])

    def asicWatchdogHandler(self):
        # mark the watchdog reset bit
        self.registers[0x02] |= 0x0100

        print('**************\nEXTERNAL WATCHDOG RESET\n**************')
        logger.info('EXTERNAL WATCHDOG RESET')
        self.emu.queueException(intc_exc.ResetException(intc_exc.ResetSource.EXTERNAL))

    def read(self, addr):
        return self.registers.get(addr, 0x00)

    def write(self, cmd, addr, value):
        # special case, the external watchdog is reset by writing an alternating 
        # pattern of 0x0055/0x00AA. 
        if addr == 0x03:
            if self.registers[addr] == 0x55 and value == 0xAA:
                # reset the watchdog, the ticks are in register 2
                self.watchdog.start(ticks=self.registers[0x02])

        if cmd == ASIC_SPI_CMD.WRITE_LOWER:
            cur_val = self.registers.get(addr, 0)
            self.registers[addr] = (value << 8) | (cur_val & 0x00FF)

            logger.info('%s -> %s: WRITE     RS%-3d XX%02x -> %04x',
                        self.bus.devname, self.name, addr, value,
                        self.registers[addr])

        elif cmd == ASIC_SPI_CMD.WRITE_UPPER:
            cur_val = self.registers.get(addr, 0)
            self.registers[addr] = (cur_val & 0xFF00) | value

            logger.info('%s -> %s: WRITE     RS%-3d XX%02x -> %04x',
                        self.bus.devname, self.name, addr, value,
                        self.registers[addr])

        elif cmd == ASIC_SPI_CMD.WRITE_SEQ:
            logger.info('%s -> %s: WRITE SEQ RS%-3d %04x', 
                        self.bus.devname, self.name, addr, value)
            self.registers[addr] = value

        else:
            raise Exception('invalid cmd %s to write %d %x' % (cmd, addr, value))

    def receive(self, data):
        # If sequential write mode, the two
        if self.addr is not None:
            self.write(ASIC_SPI_CMD.WRITE_SEQ, self.addr, data)
            self.addr = None
            return 0x0000

        # first two bits indicate read/write upper/lower byte
        # next six bits are the address
        # lower 8 bits are the value
        cmd = ASIC_SPI_CMD(data >> 14)
        addr = (data & 0x3F00) >> 8

        if cmd == ASIC_SPI_CMD.READ:
            value = self.read(addr)
            logger.info('%s -> %s: READ      RS%-3d %04x',
                        self.bus.devname, self.name, addr, value)
            return value

        elif cmd in (ASIC_SPI_CMD.WRITE_LOWER, ASIC_SPI_CMD.WRITE_UPPER):
            self.write(cmd, addr, data & 0x00FF)
            return 0x0000

        elif cmd == ASIC_SPI_CMD.WRITE_SEQ:
            # no data to write yet, just save the address
            self.addr = addr
            return 0x0000


class CM2350:
    defconfig = {
        # AMP/CM2350 project-specific default configuration values
        'project': {
            'name': DEFAULT_PROJECT_NAME,
            'platform': 'CM2350',
            'arch': 'ppc32-embedded',
            'bigend': True,
            'format': 'blob',
            'CM2350': {
                'p89': 1,
                'p90': 0,
                'p91': 1,
                'p92': 0,
            },
            'MPC5674': {
                'FMPLL': {
                    'extal': 40000000,
                },
                'SRAM': {
                    # MPC5674F RAM size and address:
                    'size': 256 * 1024,
                },
            }
        },
    }

    docconfig = {
        'project': {
            'CM2350': {
                'p89': 'GPIO 89 boot selection initial value',
                'p90': 'GPIO 90 boot selection initial value',
                'p91': 'GPIO 91 boot selection initial value',
                'p92': 'GPIO 92 boot selection initial value',
            }
        }
    }

    def __init__(self, args=None):
        # Create the MPC5674 emulator with the default configuration values
        self.emu = MPC5674_Emulator(defconfig=self.defconfig, docconfig=self.docconfig, args=args)

        # start off with the external pins
        self.emu.gpio(89, self.emu.vw.config.project.CM2350.p89)
        self.emu.gpio(90, self.emu.vw.config.project.CM2350.p90)
        self.emu.gpio(91, self.emu.vw.config.project.CM2350.p91)
        self.emu.gpio(92, self.emu.vw.config.project.CM2350.p92)

        # Register the ASIC as a SPI peripheral and fill the rest of the SPI 
        # buses and chip select optikons with placeholder devices, not all of 
        # these may be used but this ensures that any attempt to read data from 
        # a SPI device will always return a value.
        self.spi_devices = [
            # SPI A
            ASIC(self.emu, 'DSPI_A', 0),
            PlaceholderSPIDevice(self.emu, 'DeviceA1', 'DSPI_A', 1, 0x4141),
            PlaceholderSPIDevice(self.emu, 'DeviceA2', 'DSPI_A', 2, 0x4141),
            PlaceholderSPIDevice(self.emu, 'DeviceA3', 'DSPI_A', 3, 0x4141),
            PlaceholderSPIDevice(self.emu, 'DeviceA4', 'DSPI_A', 4, 0x4141),
            PlaceholderSPIDevice(self.emu, 'DeviceA5', 'DSPI_A', 5, 0x4141),

            # SPI B
            PlaceholderSPIDevice(self.emu, 'DeviceB0', 'DSPI_B', 0, 0x4141),
            PlaceholderSPIDevice(self.emu, 'DeviceB1', 'DSPI_B', 1, 0x4141),
            PlaceholderSPIDevice(self.emu, 'DeviceB2', 'DSPI_B', 2, 0x4141),
            PlaceholderSPIDevice(self.emu, 'DeviceB3', 'DSPI_B', 3, 0x4141),
            PlaceholderSPIDevice(self.emu, 'DeviceB4', 'DSPI_B', 4, 0x4141),
            PlaceholderSPIDevice(self.emu, 'DeviceB5', 'DSPI_B', 5, 0x4141),

            # SPI C
            PlaceholderSPIDevice(self.emu, 'DeviceC0', 'DSPI_C', 0, 0x4141),
            PlaceholderSPIDevice(self.emu, 'DeviceC1', 'DSPI_C', 1, 0x4141),
            PlaceholderSPIDevice(self.emu, 'DeviceC2', 'DSPI_C', 2, 0x4141),
            PlaceholderSPIDevice(self.emu, 'DeviceC3', 'DSPI_C', 3, 0x4141),
            PlaceholderSPIDevice(self.emu, 'DeviceC4', 'DSPI_C', 4, 0x4141),
            PlaceholderSPIDevice(self.emu, 'DeviceC5', 'DSPI_C', 5, 0x4141),

            # SPI D
            PlaceholderSPIDevice(self.emu, 'DeviceD0', 'DSPI_D', 0, 0x4141),
            PlaceholderSPIDevice(self.emu, 'DeviceD1', 'DSPI_D', 1, 0x4141),
            PlaceholderSPIDevice(self.emu, 'DeviceD2', 'DSPI_D', 2, 0x4141),
            PlaceholderSPIDevice(self.emu, 'DeviceD3', 'DSPI_D', 3, 0x4141),
            PlaceholderSPIDevice(self.emu, 'DeviceD4', 'DSPI_D', 4, 0x4141),
            PlaceholderSPIDevice(self.emu, 'DeviceD5', 'DSPI_D', 5, 0x4141),
        ]

    def __del__(self):
        self.shutdown()

    def shutdown(self):
        # Clean up the ECU and Vivisect Workspace cleanly
        if hasattr(self, 'emu') and self.emu:
            self.emu.shutdown()

    def start(self):
        '''
        start emulating the board/processor
        '''
        self.emu.run()
