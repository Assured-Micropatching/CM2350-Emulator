#!/usr/bin/env python3
import os
import sys
import traceback

# Vivisect packages
import vivisect
import envi.common as e_common

# for development purposes.  likely to be removed from final
from cm2350 import ui
#####

# Emulator-specific packages
import cm2350
import cm2350.mpc5674 as cm_mpc


def main():
    ECU = cm2350.CM2350()

    ###### INITIAL ROUGH-IN #######
    emu = ECU.emu
    vw = emu.vw
    emumon = cm_mpc.MPC5674_monitor(emu)
    emu.setEmulationMonitor(emumon)

    ecui = ui.TestEmulator(emu, verbose=False)

    #try:
    #    aemu.runStep(ECU.emu)
    #except:
    #    traceback.print_exc()

    # Suppress the ipython.embed() warning about running in a virtualenv
    import warnings
    warnings.filterwarnings('ignore', module='IPython')

    import envi.interactive as ei
    ei.dbg_interact(locals(), globals())
    ################################

if __name__ == '__main__':
    main()

'''
TODO:
    Emulator
    Board
    MPC5674
        devices:
            SIU and GPIO stuff
            FLASH Controller
            INTC
            FLEXCAN
            TimeBase and TIU and FMPLL
            BAM


    Debugger
    e200z7


eMIOS200:
TimeBase - SPR_TB, SPR_TBU, SPR_TBL... when and how are these updated?
    emulator loop can update them, but they're separate registers according to envi...
'''

'''
MMIO
SPRs
Timing Subsystems
- CPU Timer/TCR
- eTPU
Interrupts and Interrupt Handlers

Serial Connection - Generator-based push-model
    with DMA support.

VLE - normalization and unittests.
    * mnems list
    * add to OPCODE Constants (uniquely)
    * wire into the Emulator
    * Use Operands in meaningful for emulation (PC-based operands should *not* be Immediates)
'''



# junk code:  (requires emumon tracking data)
def getNodesAndEdges(ops):
  last = None
  nodes = []
  nops = []
  edges = []
  for op in ops:
    if last is None:
        nodes.append(op.va)
        nops.append(op)
        print("N:", hex(op.va))
    else:
        if op.va not in nodes:
            nodes.append(op.va)
            nops.append(op)
            print("N:", hex(op.va))
        edge = (last.va, op.va)
        if edge not in edges:
            edges.append(edge)
            print("E: (0x%x, 0x%x)" % (edge))
    last = op
  return nodes, edges, nops

def getJS(ops):
    nodes, edges, nops = getNodesAndEdges(ops)
    ntext = '\n'.join(['    { id: 0x%x, label: "0x%x: %r" },' % (nodes[x], nodes[x], nops[x]) for x in range(len(nodes))])
    etext = '\n'.join(['    { from: 0x%x, to: 0x%x },' % (frva, tova) for frva, tova in edges])
    return template % (ntext, etext)

def printJS(ops):
    print(getJS(ops))

# printJS(emumon.ops)



'''
GPIO Pins 89, 90, 91, 92 all have some special modes the ECU enters:
    If they're all 1 together, we end up in a bad state (branching into reserved address space 0x40080000-ville
    if 89 is set: Run into DSPI config (writing 0x33988 to 0xfff90000)
'''
