# the core of the CM2350 simulator
import os
import sys
import time

path = os.path.dirname(os.path.abspath(__file__))
internalpath = os.sep.join([os.path.abspath('.'), 'cm2350', 'internal'])
if internalpath not in sys.path:
    sys.path.insert(0, internalpath)

import vivisect.cli as v_cli
import envi.archs.ppc.emu as eape

from .mpc5674 import MPC5674_Emulator
from . import project


__all__ = [
    'CM2350',
]


DEFAULT_PROJECT_NAME = 'AMP'


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

        # Standard vivisect emulator settings that need to be different for the
        # target platform. Usually the project-specific values will be used but
        # if the vivisect loader-specific options are used we want them to be
        # correct.
        'viv': {
            'parsers': {
                'blob': {
                    'arch': 'ppc32-embedded',
                    'bigend': True,
                    'baseaddr': 0,
                },
                'ihex': {
                    'arch': 'ppc32-embedded',
                    'bigend': True,
                    'offset': 0,
                },
                'srec': {
                    'arch': 'ppc32-embedded',
                    'bigend': True,
                    'offset': 0,
                }
            }
        }
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
        self.connectGPDI(89, self.emu.vw.config.project.CM2350.p89)
        self.connectGPDI(90, self.emu.vw.config.project.CM2350.p90)
        self.connectGPDI(91, self.emu.vw.config.project.CM2350.p91)
        self.connectGPDI(92, self.emu.vw.config.project.CM2350.p92)

    def __del__(self):
        self.shutdown()

    def shutdown(self):
        # Clean up the ECU and Vivisect Workspace cleanly
        if hasattr(self, 'emu') and self.emu:
            self.emu.shutdown()

    def connectGPDI(self, pinid, val=True):
        self.emu.siu.connectGPIO(pinid, val)

    def start(self, blocking=False):
        '''
        start emulating the board/processor
        '''
        # start peripherals
        # start emulator
        self.emu.run(blocking)
