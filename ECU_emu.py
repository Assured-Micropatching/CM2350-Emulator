#!/usr/bin/env python3

# for development purposes.  likely to be removed from final
from cm2350 import ui

# Emulator-specific packages
import cm2350
import cm2350.mpc5674 as cm_mpc


def main():
    ECU = cm2350.CM2350()

    emu = ECU.emu
    vw = emu.vw
    emumon = cm_mpc.MPC5674_monitor(emu)
    emu.setEmulationMonitor(emumon)

    ecui = ui.TestEmulator(emu, verbose=False)

    # Suppress the ipython.embed() warning about running in a virtualenv
    import warnings
    warnings.filterwarnings('ignore', module='IPython')

    import envi.interactive as ei
    ei.dbg_interact(locals(), globals())


if __name__ == '__main__':
    main()
