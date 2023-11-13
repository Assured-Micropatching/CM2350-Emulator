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

    intro = '''
Welcome to the AMP TA3 CM2350 emulator

The following python objects have been created automatically 
    ecui   - The ECU user interface. It provides some GDB-like utilities to
             for debugging and stepping through the execution of the emulator.
    emumon - The emulator monitor used by the ECU user interface object. It
             collects information about execution including the path of
             execution and the current execution context.
    emu    - The emulator itself. The state of the emulator can be queried or
             manipulated directly.

Some of the most common ways to use these objects are:
    ecui:
        # Runs a gdb tui-like interface for stepping through program execution
        ecui.run()

        # Runs until execution is interrupted with CTRL-C (or an unhandled 
        # exception occurs)
        ecui.run(silent=True, pause=False, haltonerror=True)

        # Effectively creates a breakpoint and runs until the target address is 
        # hit.
        ecui.run(silent=True, pause=False, haltonerror=True, finish=0x423b0)

        # Prints additional information any time memory within the target range 
        # is read or written.
        # NOTE: this must be the physical address and not a virtual address
        ecui.watch(<startddr>, <stopaddr>)

    emumon:
        emumon.calls        # All called functions and the context the call is
                            # from
        emumon.funccalls    # The number of times functions have been called
        emumon.curfunc      # The current state of execution including the
                            # non-interrupt and interrupt context
        emumon.curfuncdata  # The address of each instruction and which
                            # function it belongs to
        emumon.path         # The function call path that was followed to
                            # reach the current state of execution
        emumon.ophist       # The number of times each type of instruction has
                            # been executed

    emu:
        emu.getRegisterByName('r1')
        emu.getRegisterByName('pc')
        emu.setRegisterByName('pc', 0x23ed0)
        op = emu.parseOpcode(0x23ed0)
'''

    import envi.interactive as ei
    ei.dbg_interact(locals(), globals(), intro)


if __name__ == '__main__':
    main()
