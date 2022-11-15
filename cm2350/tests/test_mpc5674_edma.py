import os
import random
import struct
import unittest

from cm2350 import intc_exc
import envi.bits as e_bits

from .helpers import MPC5674_Test

import logging
logger = logging.getLogger(__name__)

EDMA_DEVICES = (
    ('eDMA_A', 0XFFF44000),
    ('eDMA_B', 0XFFF54000),
)

EDMA_MCR_OFFSET     = 0x0000
EDMA_ESR_OFFSET     = 0x0004
EDMA_ERQRH_OFFSET   = 0x0008
EDMA_ERQRL_OFFSET   = 0x000C
EDMA_EEIRH_OFFSET   = 0x0010
EDMA_EEIRL_OFFSET   = 0x0014
EDMA_SERQR_OFFSET   = 0x0018
EDMA_CERQR_OFFSET   = 0x0019
EDMA_SEEIR_OFFSET   = 0x001A
EDMA_CEEIR_OFFSET   = 0x001B
EDMA_CIRQR_OFFSET   = 0x001C
EDMA_CER_OFFSET     = 0x001D
EDMA_SSBR_OFFSET    = 0x001E
EDMA_CDSBR_OFFSET   = 0x001F
EDMA_IRQRH_OFFSET   = 0x0020
EDMA_IRQRL_OFFSET   = 0x0024
EDMA_ERH_OFFSET     = 0x0028
EDMA_ERL_OFFSET     = 0x002C
EDMA_HRSH_OFFSET    = 0x0030
EDMA_HRSL_OFFSET    = 0x0034
EDMA_GWRH_OFFSET    = 0x0038
EDMA_GWRL_OFFSET    = 0x003C
EDMA_CPRx_OFFSET    = 0x0100
EDMA_TCDx_OFFSET    = 0x1000

EDMA_MCR_DEFAULT    = (0x0000E400, 0x00000400)
EDMA_MCR_HALT_FLAG  = 0x00000020

EDMA_ESR_VLD_MASK     = 0x80000000
EDMA_ESR_ERRCHN_MASK  = 0x00003F00
EDMA_ESR_ERRCHN_SHIFT = 8
EDMA_ESR_SAE_MASK     = 0x00000080
EDMA_ESR_SOE_MASK     = 0x00000040
EDMA_ESR_DAE_MASK     = 0x00000020
EDMA_ESR_DOE_MASK     = 0x00000010
EDMA_ESR_NCE_MASK     = 0x00000008
EDMA_ESR_SGE_MASK     = 0x00000004
EDMA_ESR_SBE_MASK     = 0x00000002
EDMA_ESR_DBE_MASK     = 0x00000001


SIZE_MAP = {
    1:   0,
    2:   1,
    4:   2,
    8:   3,
    16:  4,  # Invalid
    32:  5,
    64:  6,  # Invalid
    128: 7,  # Invalid
}


def get_xfer_vals(emu, saddr=None, ssize=None, daddr=None, dsize=None, nbytes=None, biter=None):
    # Number of bytes to be transferred, but by default only choose the valid
    # S/DSIZE values
    if ssize is None:
        ssize = random.choice([1, 2, 4, 8, 32])
    if dsize is None:
        dsize = random.choice([1, 2, 4, 8, 32])

    if nbytes is None:
        # Make the number of bytes to transfer between 2 and 10 times the
        # maximum size to transfer
        if dsize > ssize:
            nbytes = dsize * random.randint(2, 10)
        else:
            nbytes = ssize * random.randint(2, 10)

    if biter is None:
        # A reasonable amount of major loops
        biter = random.randrange(1, 5)

    # The source and destination address needs to be nbytes * (biter + 1) bytes
    # away from the end of the memory range
    mem_end_offset = nbytes * (biter + 1)

    if saddr is None:
        start, stop = random.choice(emu.ram_mmaps)
        saddr = random.randrange(start, stop - mem_end_offset)

        # Adjust saddr to be valid given ssize
        saddr -= (saddr % ssize)

    if daddr is None:
        mstart, mstop = random.choice(emu.ram_mmaps)
        if saddr in range(mstart, mstop):
            # Split the possible destination addresses by mem_end_offset*10
            # around the saddr
            buffer = mem_end_offset * 10
            if saddr > mstop - buffer:
                start = mstart
                stop = saddr - buffer
            elif saddr < mstart + buffer:
                start = saddr + buffer
                stop = mstop
            else:
                start, stop = random.choice([
                    (mstart, saddr - buffer),
                    (saddr + buffer, mstop),
                ])
        else:
            start = mstart
            stop = mstop

        try:
            daddr = random.randrange(start, stop - mem_end_offset)
        except ValueError as e:
            print('ERROR generating valid range %#x - %#x (%#x - %#x, saddr: %#x, offset: %#x, buffer: %#x)' %
                  (start, stop, mstart, mstop, mem_end_offset, saddr, buffer))
            raise e

        # Adjust daddr to be valid given dsize
        daddr -= (daddr % dsize)

    return saddr, ssize, daddr, dsize, nbytes, biter


class TCD:
    def __init__(self, emu, saddr=None, smod=0, ssize=None, dmod=0, dsize=None,
                 soff=None, nbytes=None, slast=None, daddr=None, citer=None, doff=None,
                 dlast_sga=None, biter=None, bwc=0, major_linkch=0, done=0, active=0,
                 major_e_link=0, e_sg=0, d_req=0, int_half=0, int_maj=0,
                 start=1):

        if saddr is None or ssize is None or daddr is None or dsize is None or \
                nbytes is None or biter is None:
            self.saddr, self.ssize, self.daddr, self.dsize, self.nbytes, self.biter = \
                    get_xfer_vals(emu, saddr, ssize, daddr, dsize, nbytes, biter)
        else:
            self.saddr  = saddr
            self.ssize  = ssize
            self.daddr  = daddr
            self.dsize  = dsize
            self.nbytes = nbytes
            self.biter  = biter

        if soff is None:
            # Automatically define soff as nbytes
            soff = self.nbytes
        self.soff = soff

        if slast is None:
            # Set slast to return saddr to it's original value
            slast = -self.size()
        self.slast = slast

        if doff is None:
            # Automatically define doff as nbytes
            doff = self.nbytes
        self.doff = doff

        if dlast_sga is None:
            # Set dlast to return saddr to it's original value
            dlast_sga = -self.size()
        self.dlast_sga = dlast_sga

        self._set_values()

        if citer is None:
            citer = self.biter

        self.smod           = smod
        self.dmod           = dmod
        self.citer          = citer
        self.bwc            = bwc
        self.major_linkch   = major_linkch
        self.done           = done
        self.active         = active
        self.major_e_link   = major_e_link
        self.e_sg           = e_sg
        self.d_req          = d_req
        self.int_half       = int_half
        self.int_maj        = int_maj
        self.start          = start

    def size(self):
        return self.nbytes * self.biter

    def _set_values(self):
        # Calculate the correct values for the SSIZE and DSIZE fields
        self._ssize = SIZE_MAP[self.ssize]
        self._dsize = SIZE_MAP[self.dsize]

    def to_bytes(self):
        self._set_values()

        ssize = (self.smod << 3)                 | self._ssize
        dsize = (self.dmod << 3)                 | self._dsize
        link  = ((self.bwc & 0x3) << 6)          | self.major_linkch
        flags = \
                ((self.bwc & 0x3) << 6)          | self.major_linkch | \
                ((self.done & 0x1) << 7)         | ((self.active & 0x1) << 6) | \
                ((self.major_e_link & 0x1) << 5) | ((self.e_sg & 0x1) << 4) | \
                ((self.d_req & 0x1) << 3)        | ((self.int_half & 0x1) << 2) | \
                ((self.int_maj & 0x1) << 1)      | (self.start & 0x1)

        # soff, slast, doff, and dlast_sga are signed fields
        soff  = self.soff & 0xFFFF
        slast = self.slast & 0xFFFFFFFF
        doff  = self.doff & 0xFFFF
        dlast = self.dlast_sga & 0xFFFFFFFF

        return struct.pack('>IBBHIIIHHIHBB', self.saddr, ssize, dsize, soff,
                           self.nbytes, slast, self.daddr, self.citer, doff,
                           dlast, self.biter, link, flags)

    def write(self, emu, addr):
        # Write in 4-byte chunks to mimic the normal maximum size a program can
        # write with one instruction.
        data = self.to_bytes()
        emu.writeMemory(addr, data[:4])
        emu.writeMemory(addr + 4, data[4:8])
        emu.writeMemory(addr + 8, data[8:12])
        emu.writeMemory(addr + 12, data[12:16])
        emu.writeMemory(addr + 16, data[16:20])
        emu.writeMemory(addr + 20, data[20:24])
        emu.writeMemory(addr + 24, data[24:28])
        emu.writeMemory(addr + 28, data[28:])


class MPC5674_eDMA_Test(MPC5674_Test):

    # Simple register tests

    def test_edma_mcr_defaults(self):
        for i in range(len(EDMA_DEVICES)):
            devname, baseaddr = EDMA_DEVICES[i]
            self.assertEqual(self.emu.dma[i].devname, devname)

            addr = baseaddr + EDMA_MCR_OFFSET
            self.assertEqual(self.emu.readMemValue(addr, 4), EDMA_MCR_DEFAULT[i])
            self.assertEqual(self.emu.readMemory(addr, 4),
                             e_bits.buildbytes(EDMA_MCR_DEFAULT[i], 4, bigend=self.emu.getEndian()))
            self.assertEqual(self.emu.dma[i].registers.mcr.cxfr, 0)
            self.assertEqual(self.emu.dma[i].registers.mcr.ecx, 0)
            if devname == 'eDMA_A':
                self.assertEqual(self.emu.dma[i].registers.mcr.grp3pri, 3)
                self.assertEqual(self.emu.dma[i].registers.mcr.grp2pri, 2)
            self.assertEqual(self.emu.dma[i].registers.mcr.grp1pri, 1)
            self.assertEqual(self.emu.dma[i].registers.mcr.grp0pri, 0)
            self.assertEqual(self.emu.dma[i].registers.mcr.emlm, 0)
            self.assertEqual(self.emu.dma[i].registers.mcr.clm, 0)
            self.assertEqual(self.emu.dma[i].registers.mcr.halt, 0)
            self.assertEqual(self.emu.dma[i].registers.mcr.hoe, 0)
            self.assertEqual(self.emu.dma[i].registers.mcr.erga, 0)
            self.assertEqual(self.emu.dma[i].registers.mcr.erca, 0)
            self.assertEqual(self.emu.dma[i].registers.mcr.edbg, 0)

    def test_edma_esr_defaults(self):
        for i in range(len(EDMA_DEVICES)):
            devname, baseaddr = EDMA_DEVICES[i]
            self.assertEqual(self.emu.dma[i].devname, devname)

            addr = baseaddr + EDMA_ESR_OFFSET
            self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000)
            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')
            self.assertEqual(self.emu.dma[i].registers.esr.vld, 0)
            self.assertEqual(self.emu.dma[i].registers.esr.ecx, 0)
            self.assertEqual(self.emu.dma[i].registers.esr.gpe, 0)
            self.assertEqual(self.emu.dma[i].registers.esr.cpe, 0)
            self.assertEqual(self.emu.dma[i].registers.esr.errchn, 0)
            self.assertEqual(self.emu.dma[i].registers.esr.sae, 0)
            self.assertEqual(self.emu.dma[i].registers.esr.soe, 0)
            self.assertEqual(self.emu.dma[i].registers.esr.dae, 0)
            self.assertEqual(self.emu.dma[i].registers.esr.doe, 0)
            self.assertEqual(self.emu.dma[i].registers.esr.nce, 0)
            self.assertEqual(self.emu.dma[i].registers.esr.sge, 0)
            self.assertEqual(self.emu.dma[i].registers.esr.sbe, 0)
            self.assertEqual(self.emu.dma[i].registers.esr.dbe, 0)

    def test_edma_erqr_defaults(self):
        for i in range(len(EDMA_DEVICES)):
            devname, baseaddr = EDMA_DEVICES[i]
            self.assertEqual(self.emu.dma[i].devname, devname)

            high_addr = baseaddr + EDMA_ERQRH_OFFSET
            low_addr = baseaddr + EDMA_ERQRL_OFFSET
            set_addr = baseaddr + EDMA_SERQR_OFFSET
            clear_addr = baseaddr + EDMA_CERQR_OFFSET

            if devname == 'eDMA_A':
                self.assertEqual(self.emu.readMemValue(high_addr, 4), 0x00000000)
                self.assertEqual(self.emu.readMemory(high_addr, 4), b'\x00\x00\x00\x00')

            self.assertEqual(self.emu.readMemValue(low_addr, 4), 0x00000000)
            self.assertEqual(self.emu.readMemory(low_addr, 4), b'\x00\x00\x00\x00')

            # Verify that the "set ERQR" register works as expected
            #   0x80 writes are ignored
            #   0x40 writes cause all ERQR flags to be set
            #        all other writes will only set the specific channel
            self.emu.writeMemValue(set_addr, 0xFF, 1)
            if devname == 'eDMA_A':
                self.assertEqual(self.emu.readMemValue(high_addr, 4), 0x00000000)
            self.assertEqual(self.emu.readMemValue(low_addr, 4), 0x00000000)

            self.emu.writeMemValue(set_addr, 0x40, 1)
            if devname == 'eDMA_A':
                self.assertEqual(self.emu.readMemValue(high_addr, 4), 0xFFFFFFFF)
            self.assertEqual(self.emu.readMemValue(low_addr, 4), 0xFFFFFFFF)

            # Inverse for the "clear ERQR" register
            self.emu.writeMemValue(clear_addr, 0xFF, 1)
            if devname == 'eDMA_A':
                self.assertEqual(self.emu.readMemValue(high_addr, 4), 0xFFFFFFFF)
            self.assertEqual(self.emu.readMemValue(low_addr, 4), 0xFFFFFFFF)

            self.emu.writeMemValue(clear_addr, 0x40, 1)
            if devname == 'eDMA_A':
                self.assertEqual(self.emu.readMemValue(high_addr, 4), 0x00000000)
            self.assertEqual(self.emu.readMemValue(low_addr, 4), 0x00000000)

            # Set each channel individually
            for chan in range(self.emu.dma[i].num_channels):
                if devname == 'eDMA_A':
                    self.emu.dma[i].registers.erqrh = 0x00000000
                self.emu.dma[i].registers.erqrl = 0x00000000

                msg = 'setting ERQR[%d]' % chan
                mask = 1 << (chan % 32)
                self.emu.writeMemValue(set_addr, chan, 1)

                if chan >= 32:
                    self.assertEqual(self.emu.readMemValue(high_addr, 4), mask, msg=msg)
                    self.assertEqual(self.emu.readMemValue(low_addr, 4), 0x00000000, msg=msg)
                else:
                    if devname == 'eDMA_A':
                        self.assertEqual(self.emu.readMemValue(high_addr, 4), 0x00000000, msg=msg)
                    self.assertEqual(self.emu.readMemValue(low_addr, 4), mask, msg=msg)

            # Clear each channel individually
            for chan in range(self.emu.dma[i].num_channels):
                if devname == 'eDMA_A':
                    self.emu.dma[i].registers.erqrh = 0xFFFFFFFF
                self.emu.dma[i].registers.erqrl = 0xFFFFFFFF

                msg = 'clearing ERQR[%d]' % chan
                mask = ~(1 << (chan % 32)) & 0xFFFFFFFF
                self.emu.writeMemValue(clear_addr, chan, 1)

                if chan >= 32:
                    self.assertEqual(self.emu.readMemValue(high_addr, 4), mask, msg=msg)
                    self.assertEqual(self.emu.readMemValue(low_addr, 4), 0xFFFFFFFF, msg=msg)
                else:
                    if devname == 'eDMA_A':
                        self.assertEqual(self.emu.readMemValue(high_addr, 4), 0xFFFFFFFF, msg=msg)
                    self.assertEqual(self.emu.readMemValue(low_addr, 4), mask, msg=msg)

    def test_edma_eeir_defaults(self):
        for i in range(len(EDMA_DEVICES)):
            devname, baseaddr = EDMA_DEVICES[i]
            self.assertEqual(self.emu.dma[i].devname, devname)

            high_addr = baseaddr + EDMA_EEIRH_OFFSET
            low_addr = baseaddr + EDMA_EEIRL_OFFSET
            set_addr = baseaddr + EDMA_SEEIR_OFFSET
            clear_addr = baseaddr + EDMA_CEEIR_OFFSET

            if devname == 'eDMA_A':
                self.assertEqual(self.emu.readMemValue(high_addr, 4), 0x00000000)
                self.assertEqual(self.emu.readMemory(high_addr, 4), b'\x00\x00\x00\x00')

            self.assertEqual(self.emu.readMemValue(low_addr, 4), 0x00000000)
            self.assertEqual(self.emu.readMemory(low_addr, 4), b'\x00\x00\x00\x00')

            # Verify that the "set EEIR" register works as expected
            #   0x80 writes are ignored
            #   0x40 writes cause all EEIR flags to be set
            #        all other writes will only set the specific channel
            self.emu.writeMemValue(set_addr, 0xFF, 1)
            if devname == 'eDMA_A':
                self.assertEqual(self.emu.readMemValue(high_addr, 4), 0x00000000)
            self.assertEqual(self.emu.readMemValue(low_addr, 4), 0x00000000)

            self.emu.writeMemValue(set_addr, 0x40, 1)
            if devname == 'eDMA_A':
                self.assertEqual(self.emu.readMemValue(high_addr, 4), 0xFFFFFFFF)
            self.assertEqual(self.emu.readMemValue(low_addr, 4), 0xFFFFFFFF)

            # Inverse for the "clear EEIR" register
            self.emu.writeMemValue(clear_addr, 0xFF, 1)
            if devname == 'eDMA_A':
                self.assertEqual(self.emu.readMemValue(high_addr, 4), 0xFFFFFFFF)
            self.assertEqual(self.emu.readMemValue(low_addr, 4), 0xFFFFFFFF)

            self.emu.writeMemValue(clear_addr, 0x40, 1)
            if devname == 'eDMA_A':
                self.assertEqual(self.emu.readMemValue(high_addr, 4), 0x00000000)
            self.assertEqual(self.emu.readMemValue(low_addr, 4), 0x00000000)

            # Set each channel individually
            for chan in range(self.emu.dma[i].num_channels):
                if devname == 'eDMA_A':
                    self.emu.dma[i].registers.eeirh = 0x00000000
                self.emu.dma[i].registers.eeirl = 0x00000000

                msg = 'setting EEIR[%d]' % chan

                mask = 1 << (chan % 32)
                self.emu.writeMemValue(set_addr, chan, 1)

                if chan >= 32:
                    self.assertEqual(self.emu.readMemValue(high_addr, 4), mask, msg=msg)
                    self.assertEqual(self.emu.readMemValue(low_addr, 4), 0x00000000, msg=msg)
                else:
                    if devname == 'eDMA_A':
                        self.assertEqual(self.emu.readMemValue(high_addr, 4), 0x00000000, msg=msg)
                    self.assertEqual(self.emu.readMemValue(low_addr, 4), mask, msg=msg)

            # Clear each channel individually
            for chan in range(self.emu.dma[i].num_channels):
                if devname == 'eDMA_A':
                    self.emu.dma[i].registers.eeirh = 0xFFFFFFFF
                self.emu.dma[i].registers.eeirl = 0xFFFFFFFF

                msg = 'clearing EEIR[%d]' % chan

                mask = ~(1 << (chan % 32)) & 0xFFFFFFFF
                self.emu.writeMemValue(clear_addr, chan, 1)

                if chan >= 32:
                    self.assertEqual(self.emu.readMemValue(high_addr, 4), mask, msg=msg)
                    self.assertEqual(self.emu.readMemValue(low_addr, 4), 0xFFFFFFFF, msg=msg)
                else:
                    if devname == 'eDMA_A':
                        self.assertEqual(self.emu.readMemValue(high_addr, 4), 0xFFFFFFFF, msg=msg)
                    self.assertEqual(self.emu.readMemValue(low_addr, 4), mask, msg=msg)

    def test_edma_irqr_defaults(self):
        for i in range(len(EDMA_DEVICES)):
            devname, baseaddr = EDMA_DEVICES[i]
            self.assertEqual(self.emu.dma[i].devname, devname)

            high_addr = baseaddr + EDMA_IRQRH_OFFSET
            low_addr = baseaddr + EDMA_IRQRL_OFFSET
            clear_addr = baseaddr + EDMA_CIRQR_OFFSET

            if devname == 'eDMA_A':
                self.assertEqual(self.emu.readMemValue(high_addr, 4), 0x00000000)
                self.assertEqual(self.emu.readMemory(high_addr, 4), b'\x00\x00\x00\x00')

            self.assertEqual(self.emu.readMemValue(low_addr, 4), 0x00000000)
            self.assertEqual(self.emu.readMemory(low_addr, 4), b'\x00\x00\x00\x00')

            # Verify that the "clear IRQR" register works as expected
            #   0x80 writes are ignored
            #   0x40 writes cause all IRQR flags to be cleared
            #        all other writes will only cleared the specific channel
            if devname == 'eDMA_A':
                self.emu.dma[i].registers.irqrh = 0xFFFFFFFF
            self.emu.dma[i].registers.irqrl = 0xFFFFFFFF

            self.emu.writeMemValue(clear_addr, 0xFF, 1)
            if devname == 'eDMA_A':
                self.assertEqual(self.emu.readMemValue(high_addr, 4), 0xFFFFFFFF)
            self.assertEqual(self.emu.readMemValue(low_addr, 4), 0xFFFFFFFF)

            self.emu.writeMemValue(clear_addr, 0x40, 1)
            if devname == 'eDMA_A':
                self.assertEqual(self.emu.readMemValue(high_addr, 4), 0x00000000)
            self.assertEqual(self.emu.readMemValue(low_addr, 4), 0x00000000)

            # Clear each channel individually
            for chan in range(self.emu.dma[i].num_channels):
                if devname == 'eDMA_A':
                    self.emu.dma[i].registers.irqrh = 0xFFFFFFFF
                self.emu.dma[i].registers.irqrl = 0xFFFFFFFF

                msg = 'clearing IRQR[%d]' % chan

                mask = ~(1 << (chan % 32)) & 0xFFFFFFFF
                self.emu.writeMemValue(clear_addr, chan, 1)

                if chan >= 32:
                    self.assertEqual(self.emu.readMemValue(high_addr, 4), mask, msg=msg)
                    self.assertEqual(self.emu.readMemValue(low_addr, 4), 0xFFFFFFFF, msg=msg)
                else:
                    if devname == 'eDMA_A':
                        self.assertEqual(self.emu.readMemValue(high_addr, 4), 0xFFFFFFFF, msg=msg)
                    self.assertEqual(self.emu.readMemValue(low_addr, 4), mask, msg=msg)

    def test_edma_er_defaults(self):
        for i in range(len(EDMA_DEVICES)):
            devname, baseaddr = EDMA_DEVICES[i]
            self.assertEqual(self.emu.dma[i].devname, devname)

            high_addr = baseaddr + EDMA_ERH_OFFSET
            low_addr = baseaddr + EDMA_ERL_OFFSET
            clear_addr = baseaddr + EDMA_CER_OFFSET

            if devname == 'eDMA_A':
                self.assertEqual(self.emu.readMemValue(high_addr, 4), 0x00000000)
                self.assertEqual(self.emu.readMemory(high_addr, 4), b'\x00\x00\x00\x00')

            self.assertEqual(self.emu.readMemValue(low_addr, 4), 0x00000000)
            self.assertEqual(self.emu.readMemory(low_addr, 4), b'\x00\x00\x00\x00')

            # Verify that the "clear ER" register works as expected
            #   0x80 writes are ignored
            #   0x40 writes cause all ER flags to be cleared
            #        all other writes will only cleared the specific channel
            if devname == 'eDMA_A':
                self.emu.dma[i].registers.vsOverrideValue('erh', 0xFFFFFFFF)
            self.emu.dma[i].registers.vsOverrideValue('erl', 0xFFFFFFFF)

            self.emu.writeMemValue(clear_addr, 0xFF, 1)
            if devname == 'eDMA_A':
                self.assertEqual(self.emu.readMemValue(high_addr, 4), 0xFFFFFFFF)
            self.assertEqual(self.emu.readMemValue(low_addr, 4), 0xFFFFFFFF)

            self.emu.writeMemValue(clear_addr, 0x40, 1)
            if devname == 'eDMA_A':
                self.assertEqual(self.emu.readMemValue(high_addr, 4), 0x00000000)
            self.assertEqual(self.emu.readMemValue(low_addr, 4), 0x00000000)

            # Clear each channel individually
            for chan in range(self.emu.dma[i].num_channels):
                if devname == 'eDMA_A':
                    self.emu.dma[i].registers.vsOverrideValue('erh', 0xFFFFFFFF)
                self.emu.dma[i].registers.vsOverrideValue('erl', 0xFFFFFFFF)

                msg = 'clearing ER[%d]' % chan

                mask = ~(1 << (chan % 32)) & 0xFFFFFFFF
                self.emu.writeMemValue(clear_addr, chan, 1)

                if chan >= 32:
                    self.assertEqual(self.emu.readMemValue(high_addr, 4), mask, msg=msg)
                    self.assertEqual(self.emu.readMemValue(low_addr, 4), 0xFFFFFFFF, msg=msg)
                else:
                    if devname == 'eDMA_A':
                        self.assertEqual(self.emu.readMemValue(high_addr, 4), 0xFFFFFFFF, msg=msg)
                    self.assertEqual(self.emu.readMemValue(low_addr, 4), mask, msg=msg)

    def test_edma_hrs_defaults(self):
        for i in range(len(EDMA_DEVICES)):
            devname, baseaddr = EDMA_DEVICES[i]
            self.assertEqual(self.emu.dma[i].devname, devname)

            if devname == 'eDMA_A':
                addr = baseaddr + EDMA_HRSH_OFFSET
                self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000)
                self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')

            addr = baseaddr + EDMA_HRSL_OFFSET
            self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000)
            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')

    def test_edma_gwr_defaults(self):
        for i in range(len(EDMA_DEVICES)):
            devname, baseaddr = EDMA_DEVICES[i]
            self.assertEqual(self.emu.dma[i].devname, devname)

            if devname == 'eDMA_A':
                addr = baseaddr + EDMA_GWRH_OFFSET
                self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000)
                self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')

            addr = baseaddr + EDMA_GWRL_OFFSET
            self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000)
            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')

    def test_edma_cpr_defaults(self):
        for i in range(len(EDMA_DEVICES)):
            devname, baseaddr = EDMA_DEVICES[i]
            self.assertEqual(self.emu.dma[i].devname, devname)

            if devname == 'eDMA_A':
                self.assertEqual(self.emu.dma[i].num_channels, 64)
            else:
                self.assertEqual(self.emu.dma[i].num_channels, 32)

            addr = baseaddr + EDMA_CPRx_OFFSET
            for chan in range(self.emu.dma[i].num_channels):
                testmsg = '%s[%d]' % (devname, chan)
                grppri = chan // 16
                value = (grppri << 4) | chan
                self.assertEqual(self.emu.readMemValue(addr + chan, 1), value, msg=testmsg)
                self.assertEqual(self.emu.readMemory(addr + chan, 1),
                                 e_bits.buildbytes(value, 1, bigend=self.emu.getEndian()),
                                 msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.cpr[chan].ecp, 0, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.cpr[chan].dpa, 0, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.cpr[chan].grppri, grppri, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.cpr[chan].chpri, chan & 0xF, msg=testmsg)

    def test_edma_tcd_defaults(self):
        for i in range(len(EDMA_DEVICES)):
            devname, baseaddr = EDMA_DEVICES[i]
            self.assertEqual(self.emu.dma[i].devname, devname)

            if devname == 'eDMA_A':
                self.assertEqual(self.emu.dma[i].num_channels, 64)
            else:
                self.assertEqual(self.emu.dma[i].num_channels, 32)

            # Each TCD is a 256 bit (16 byte) field
            bytevalue = b'\x00' * 32
            for chan in range(self.emu.dma[i].num_channels):
                testmsg = '%s[%d]' % (devname, chan)

                tcd_addr = baseaddr + EDMA_TCDx_OFFSET + (32 * chan)

                self.assertEqual(self.emu.readMemory(tcd_addr, 32), bytevalue, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.tcd[chan].saddr, 0, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.tcd[chan].smod, 0, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.tcd[chan].ssize, 0, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.tcd[chan].dmod, 0, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.tcd[chan].dsize, 0, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.tcd[chan].nbytes, 0, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.tcd[chan].slast, 0, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.tcd[chan].daddr, 0, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.tcd[chan].citer, 0, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.tcd[chan].doff, 0, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.tcd[chan].dlast_sga, 0, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.tcd[chan].biter, 0, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.tcd[chan].bwc, 0, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.tcd[chan].major_linkch, 0, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.tcd[chan].done, 0, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.tcd[chan].active, 0, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.tcd[chan].major_e_link, 0, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.tcd[chan].e_sg, 0, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.tcd[chan].d_req, 0, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.tcd[chan].int_half, 0, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.tcd[chan].int_maj, 0, msg=testmsg)
                self.assertEqual(self.emu.dma[i].registers.tcd[chan].start, 0, msg=testmsg)

    # Functionality tests

    def test_edma_tcd_config_errors(self):
        # Possible configuration errors:
        #   - Invalid tcd.ssize
        #   - tcd.saddr is inconsistent with tcd.ssize
        #   - tcd.soff is inconsistent with tcd.ssize
        #   - Invalid tcd.dsize
        #   - tcd.daddr is inconsistent with tcd.dsize
        #   - tcd.doff is inconsistent with tcd.dsize
        #   - tcd.nbytes is not a multiple of tcd.ssize and tcd.dsize
        #   - tcd.citer == 0 (!= tcd.biter)
        #   - tcd.citer_e_link != tcd.biter_e_link
        #   - ensure tcd.dlast_sga is on a 32 byte boundary
        #
        # A list of TCD configurations to test and the ESR value that should
        # result
        tests = (
            # ssize values 16 (4), 64 (6), and 128 (7) are invalid
            ({'ssize': 16},                         'sae', EDMA_ESR_SAE_MASK),
            ({'ssize': 64},                         'sae', EDMA_ESR_SAE_MASK),
            ({'ssize': 128},                        'sae', EDMA_ESR_SAE_MASK),
            ({'saddr': 0x40000001, 'ssize': 2},     'sae', EDMA_ESR_SAE_MASK),
            ({'saddr': 0x40000002, 'ssize': 32},    'sae', EDMA_ESR_SAE_MASK),

            # source offset errors
            ({'soff': 1, 'ssize': 2},               'soe', EDMA_ESR_SOE_MASK),
            ({'soff': 2, 'ssize': 32},              'soe', EDMA_ESR_SOE_MASK),

            # dsize values 16 (4), 64 (6), and 128 (7) are invalid
            ({'dsize': 16},                         'dae', EDMA_ESR_DAE_MASK),
            ({'dsize': 64},                         'dae', EDMA_ESR_DAE_MASK),
            ({'dsize': 128},                        'dae', EDMA_ESR_DAE_MASK),
            ({'daddr': 0x40000001, 'dsize': 2},     'dae', EDMA_ESR_DAE_MASK),
            ({'daddr': 0x40000002, 'dsize': 32},    'dae', EDMA_ESR_DAE_MASK),

            # dest offset errors
            ({'doff': 1, 'dsize': 2},               'doe', EDMA_ESR_DOE_MASK),
            ({'doff': 2, 'dsize': 32},              'doe', EDMA_ESR_DOE_MASK),

            # num bytes errors
            ({'nbytes': 7, 'soff': 8, 'ssize': 2, 'doff': 8, 'dsize': 8}, 'nce', EDMA_ESR_NCE_MASK),
            ({'nbytes': 2, 'soff': 2, 'ssize': 2, 'doff': 4, 'dsize': 4}, 'nce', EDMA_ESR_NCE_MASK),
            ({'nbytes': 6, 'soff': 8, 'ssize': 4, 'doff': 8, 'dsize': 8}, 'nce', EDMA_ESR_NCE_MASK),
            ({'nbytes': 2, 'soff': 4, 'ssize': 4, 'doff': 4, 'dsize': 4}, 'nce', EDMA_ESR_NCE_MASK),
            ({'biter': 0, 'citer': 0},              'nce', EDMA_ESR_NCE_MASK),
            ({'citer': 0},                          'nce', EDMA_ESR_NCE_MASK),
            ({'biter': 3, 'citer': 2},              'nce', EDMA_ESR_NCE_MASK),
            ({'biter': 1, 'citer': 2},              'nce', EDMA_ESR_NCE_MASK),

            # scatter-gather errors
            ({'e_sg': 1, 'dlast_sga': 0x40000002},  'sge', EDMA_ESR_SGE_MASK),
            ({'e_sg': 1, 'dlast_sga': 0x40000005},  'sge', EDMA_ESR_SGE_MASK),

            # TLB src lookup error
            ({'saddr': 0x30000000},                 'sbe', EDMA_ESR_SBE_MASK),

            # TLB dest lookup error
            ({'daddr': 0x30000000},                 'dbe', EDMA_ESR_DBE_MASK),

            # read src error (within valid default MMU entry, outside of valid
            # memory)
            ({'saddr': 0x00500000},                 'sbe', EDMA_ESR_SBE_MASK),

            # write src error (within valid default MMU entry, outside of valid
            # memory)
            ({'daddr': 0x00500000},                 'dbe', EDMA_ESR_DBE_MASK),
        )

        for i in range(len(EDMA_DEVICES)):
            devname, baseaddr = EDMA_DEVICES[i]
            self.assertEqual(self.emu.dma[i].devname, devname)

            esr_addr = baseaddr + EDMA_ESR_OFFSET
            erl_addr = baseaddr + EDMA_ERL_OFFSET
            erh_addr = baseaddr + EDMA_ERH_OFFSET

            for tcd_args, flag, esr_value in tests:
                # Pick a channel to test
                chan = random.randrange(self.emu.dma[i].num_channels)
                tcd_addr = baseaddr + EDMA_TCDx_OFFSET + (32 * chan)

                msg = '[%s] channel %d error %s: %s' % (devname, chan, flag, tcd_args)

                # Clear the contents of ESR
                self.emu.dma[i].registers.esr.reset(self.emu)
                self.assertEqual(self.emu.readMemValue(esr_addr, 4), 0, msg=msg)

                tcd = TCD(self.emu, **tcd_args)
                tcd.write(self.emu, tcd_addr)

                # If this is the 'sbe' or 'dbe' error, we need to process active
                # transfers first before the errors will be triggered.
                if flag in ('sbe', 'dbe'):
                    self.assertTrue(chan in self.emu.dma[i]._pending, msg=msg)
                    config = self.emu.dma[i]._pending[chan]
                    self.assertEqual(self.emu.dma[i].getPending(), config, msg=msg)
                    self.assertEqual(self.emu.extra_processing,
                                     [self.emu.dma[i].processActiveTransfers], msg=msg)

                    # One call to processActiveTransfers() to initiate the
                    # error, another call to clear the extra call to
                    # processActiveTransfers()

                    # By default when an extra processing function is called
                    # it's removed from the list

                    self.emu.extra_processing = []
                    self.emu.dma[i].processActiveTransfers()

                    self.assertTrue(chan not in self.emu.dma[i]._pending, msg=msg)
                    self.assertEqual(self.emu.dma[i].getPending(), None, msg=msg)
                    self.assertEqual(self.emu.extra_processing,
                                     [self.emu.dma[i].processActiveTransfers], msg=msg)

                    self.emu.extra_processing = []
                    self.emu.dma[i].processActiveTransfers()

                self.assertTrue(chan not in self.emu.dma[i]._pending, msg=msg)
                self.assertEqual(self.emu.dma[i].getPending(), None, msg=msg)
                self.assertEqual(self.emu.extra_processing, [], msg=msg)

                value = EDMA_ESR_VLD_MASK | (chan << EDMA_ESR_ERRCHN_SHIFT) | esr_value
                self.assertEqual(self.emu.readMemValue(esr_addr, 4), value, msg=msg)

                # Confirm the error flag was set and then clear it
                if chan >= 32:
                    value = self.emu.readMemValue(erh_addr, 4)
                    self.assertEqual(value, 1 << (chan-32), msg=msg)
                    self.emu.writeMemValue(erh_addr, value, 4)
                    self.assertEqual(self.emu.readMemValue(erh_addr, 4), 0, msg=msg)
                else:
                    value = self.emu.readMemValue(erl_addr, 4)
                    self.assertEqual(value, 1 << chan, msg=msg)
                    self.emu.writeMemValue(erl_addr, value, 4)
                    self.assertEqual(self.emu.readMemValue(erl_addr, 4), 0, msg=msg)

    def test_edma_tcd_simple(self):
        for i in range(len(EDMA_DEVICES)):
            devname, baseaddr = EDMA_DEVICES[i]
            self.assertEqual(self.emu.dma[i].devname, devname)

            if devname == 'eDMA_A':
                self.assertEqual(self.emu.dma[i].num_channels, 64, msg=devname)
            else:
                self.assertEqual(self.emu.dma[i].num_channels, 32, msg=devname)

            mcr_addr = baseaddr + EDMA_MCR_OFFSET
            ssbr_addr = baseaddr + EDMA_SSBR_OFFSET
            cdsbr_addr = baseaddr + EDMA_CDSBR_OFFSET

            # Create some TCDs
            tcd1 = TCD(self.emu, start=1)
            tcd2 = TCD(self.emu, start=0)

            # Fill in the source addresses with some random data, along with a
            # little data surrounding the valid start and end.
            sdata1_size = tcd1.size() + (tcd1.nbytes * 2)
            sdata1 = os.urandom(sdata1_size)
            self.emu.writeMemory(tcd1.saddr - tcd1.nbytes, sdata1)

            sdata1_empty = os.urandom(sdata1_size)
            self.emu.writeMemory(tcd1.daddr - tcd1.nbytes, sdata1_empty)

            sdata1_expected = sdata1_empty[:tcd1.nbytes] + \
                    sdata1[tcd1.nbytes:-tcd1.nbytes] + \
                    sdata1_empty[-tcd1.nbytes:]

            sdata2_size = tcd2.size() + (tcd2.nbytes * 2)
            sdata2 = os.urandom(sdata2_size)
            self.emu.writeMemory(tcd2.saddr - tcd2.nbytes, sdata2)

            sdata2_empty = os.urandom(sdata2_size)
            self.emu.writeMemory(tcd2.daddr - tcd2.nbytes, sdata2_empty)

            sdata2_expected = sdata2_empty[:tcd2.nbytes] + \
                    sdata2[tcd2.nbytes:-tcd2.nbytes] + \
                    sdata2_empty[-tcd2.nbytes:]

            # Pick two channels to use in the same priority group
            chan1, chan2 = random.sample(random.choice(self.emu.dma[i].groups)[0], k=2)
            logger.debug('Selected test channels: %d, %d', chan1, chan2)
            tcd1_addr = baseaddr + EDMA_TCDx_OFFSET + (32 * chan1)
            tcd2_addr = baseaddr + EDMA_TCDx_OFFSET + (32 * chan2)
            cpr1_addr = baseaddr + EDMA_CPRx_OFFSET + chan1
            cpr2_addr = baseaddr + EDMA_CPRx_OFFSET + chan2

            # With the default fixed priority set channel 2 to have higher
            # priority over channel 1
            self.assertEqual(self.emu.readMemValue(cpr1_addr, 1) & 0x0F, chan1 % 16, msg=devname)
            self.assertEqual(self.emu.readMemValue(cpr2_addr, 1) & 0x0F, chan2 % 16, msg=devname)
            self.emu.writeMemValue(cpr1_addr, 0, 1)
            self.emu.writeMemValue(cpr2_addr, 1, 1)

            # Disable DMA (set MCR[HALT])
            self.emu.writeMemValue(mcr_addr, EDMA_MCR_DEFAULT[i] | EDMA_MCR_HALT_FLAG, 4)
            self.assertEqual(self.emu.dma[i].registers.mcr.halt, 1, msg=devname)

            # Write the TCDs and confirm nothing happens.
            tcd1.write(self.emu, tcd1_addr)
            self.assertEqual(self.emu.readMemory(tcd1_addr, 32), tcd1.to_bytes(), msg=devname)
            self.assertTrue(chan1 not in self.emu.dma[i]._pending)
            self.assertEqual(self.emu.dma[i].registers.tcd[chan1].start, 1, msg=devname)
            self.assertEqual(self.emu.dma[i].registers.tcd[chan1].active, 0, msg=devname)

            tcd2.write(self.emu, tcd2_addr)
            self.assertEqual(self.emu.readMemory(tcd2_addr, 32), tcd2.to_bytes(), msg=devname)
            self.assertTrue(chan2 not in self.emu.dma[i]._pending)
            self.assertEqual(self.emu.dma[i].registers.tcd[chan2].start, 0, msg=devname)
            self.assertEqual(self.emu.dma[i].registers.tcd[chan2].active, 0, msg=devname)

            self.assertEqual(self.emu.dma[i].getPending(), None, msg=devname)

            # clear MCR[HALT]
            self.emu.writeMemValue(mcr_addr, EDMA_MCR_DEFAULT[i], 4)
            self.assertEqual(self.emu.dma[i].registers.mcr.halt, 0, msg=devname)

            # TCD1 should have been started when halt was cleared
            self.assertEqual(self.emu.readMemory(tcd1_addr, 32), tcd1.to_bytes(), msg=devname)
            self.assertTrue(chan1 in self.emu.dma[i]._pending)
            config1 = self.emu.dma[i]._pending[chan1]
            self.assertEqual(config1.tcd, self.emu.dma[i].registers.tcd[chan1], msg=devname)
            self.assertEqual(self.emu.dma[i].registers.tcd[chan1].start, 1, msg=devname)
            self.assertEqual(self.emu.dma[i].registers.tcd[chan1].active, 0, msg=devname)

            self.assertEqual(self.emu.readMemory(tcd2_addr, 32), tcd2.to_bytes(), msg=devname)
            self.assertTrue(chan2 not in self.emu.dma[i]._pending)
            self.assertEqual(self.emu.dma[i].registers.tcd[chan2].start, 0, msg=devname)
            self.assertEqual(self.emu.dma[i].registers.tcd[chan2].active, 0, msg=devname)

            self.assertEqual(self.emu.dma[i].getPending(), config1, msg=devname)

            # TODO: set START
            self.assertEqual(self.emu.readMemory(ssbr_addr, 1), b'\x00', msg=devname)
            self.emu.writeMemValue(ssbr_addr, chan2, 1)
            self.assertEqual(self.emu.readMemory(ssbr_addr, 1), b'\x00', msg=devname)

            tcd2.start = 1
            self.assertEqual(self.emu.readMemory(tcd2_addr, 32), tcd2.to_bytes(), msg=devname)
            self.assertTrue(chan2 in self.emu.dma[i]._pending)
            config2 = self.emu.dma[i]._pending[chan2]
            self.assertEqual(config2.tcd, self.emu.dma[i].registers.tcd[chan2], msg=devname)
            self.assertEqual(self.emu.dma[i].registers.tcd[chan2].start, 1, msg=devname)
            self.assertEqual(self.emu.dma[i].registers.tcd[chan2].active, 0, msg=devname)

            # Ensure that channel 2 is now higher in the priority list
            self.assertEqual(self.emu.dma[i].getPending(), config2, msg=devname)

            # Determine how many stepi() calls it should take to complete the
            # transfers
            cycles = tcd1.biter + tcd2.biter

            # Fill in a bunch of NOPs (0x60000000: ori r0,r0,0) starting at the
            # current PC
            pc = self.emu.getProgramCounter()
            instrs = b'\x60\x00\x00\x00' * cycles
            self.emu.flash.data[pc:pc+len(instrs)] = instrs

            # Confirm the two designations have not been written to yet by the
            # DMA transfer
            self.assertEqual(self.emu.readMemory(tcd2.daddr - tcd2.nbytes, sdata2_size),
                             sdata2_empty, msg=devname)
            self.assertEqual(self.emu.readMemory(tcd1.daddr - tcd1.nbytes, sdata1_size),
                             sdata1_empty, msg=devname)

            # There are no active transfers yet
            self.assertEqual(self.emu.dma[i]._active, None)

            # 2 pending transfers
            self.assertEqual(self.emu.dma[i]._pending,
                             {chan1: config1, chan2: config2}, msg=devname)

            self.assertEqual(self.emu.dma[i].registers.tcd[chan2].citer,
                             tcd2.biter, msg=devname)
            logger.debug('[%s] channel (%d) %d major loops', devname, chan2, tcd2.biter)
            for citer in reversed(range(tcd2.biter)):
                msg = '[%s] channel %d / loop %d of %d' % (devname, chan2, citer, tcd2.biter)
                logger.debug(msg)
                self.emu.stepi()

                if citer > 0:
                    # Start and Done should be cleared, Active will be set while
                    # data is actively being transfered, so it should be cleared
                    # by now.
                    self.assertEqual(self.emu.dma[i].registers.tcd[chan2].start, 0, msg=msg)
                    self.assertEqual(self.emu.dma[i].registers.tcd[chan2].active, 0, msg=msg)
                    self.assertEqual(self.emu.dma[i].registers.tcd[chan2].done, 0, msg=msg)
                    self.assertTrue(chan2 in self.emu.dma[i]._pending, msg=msg)
                    self.assertEqual(self.emu.dma[i].getPending(), config2, msg=msg)

                    # TCD2 should not be the active transfer (because that only
                    # happens in a small minor-loop self linked condition)
                    self.assertEqual(self.emu.dma[i]._active, None, msg=msg)

                    # But it should be the first pending transfer
                    self.assertTrue(chan2 in self.emu.dma[i]._pending, msg=msg)
                    self.assertEqual(self.emu.dma[i].getPending(), config2, msg=msg)

                    # Confirm that citer has been decremented
                    self.assertEqual(self.emu.dma[i].registers.tcd[chan2].citer, citer, msg=msg)
                else:
                    self.assertEqual(self.emu.dma[i].registers.tcd[chan2].start, 0, msg=msg)
                    self.assertEqual(self.emu.dma[i].registers.tcd[chan2].active, 0, msg=msg)
                    self.assertEqual(self.emu.dma[i].registers.tcd[chan2].done, 1, msg=msg)
                    self.assertTrue(chan2 not in self.emu.dma[i]._pending, msg=msg)
                    self.assertEqual(self.emu.dma[i].getPending(), config1, msg=msg)

                    # Confirm that citer has been reset to the starting value
                    self.assertEqual(self.emu.dma[i].registers.tcd[chan2].citer, tcd2.biter, msg=msg)

            # TCD2 should be complete
            self.assertEqual(config2.tcd, self.emu.dma[i].registers.tcd[chan2], msg=devname)

            # TCD1 is not active yet
            self.assertEqual(self.emu.dma[i]._active, None, msg=devname)

            # 1 pending transfers
            self.assertEqual(self.emu.dma[i]._pending, {chan1: config1}, msg=devname)

            # Confirm that the correct amount of data has been written to the
            # TCD2 destination
            self.assertEqual(self.emu.readMemory(tcd2.daddr - tcd2.nbytes, sdata2_size), sdata2_expected, msg=devname)
            self.assertEqual(self.emu.readMemory(tcd1.daddr - tcd1.nbytes, sdata1_size), sdata1_empty, msg=devname)

            self.assertEqual(self.emu.dma[i].registers.tcd[chan1].citer, tcd1.biter, msg=devname)
            logger.debug('[%s] channel (%d) %d major loops', devname, chan1, tcd1.biter)
            for citer in reversed(range(tcd1.biter)):
                msg = '[%s] channel %d / loop %d of %d' % (devname, chan1, citer, tcd1.biter)
                logger.debug(msg)
                self.emu.stepi()

                if citer > 0:
                    # Start and Done should be cleared, Active will be set while
                    # data is actively being transfered, so it should be cleared
                    # by now.
                    self.assertEqual(self.emu.dma[i].registers.tcd[chan1].start, 0, msg=msg)
                    self.assertEqual(self.emu.dma[i].registers.tcd[chan1].active, 0, msg=msg)
                    self.assertEqual(self.emu.dma[i].registers.tcd[chan1].done, 0, msg=msg)
                    self.assertTrue(chan1 in self.emu.dma[i]._pending, msg=msg)
                    self.assertEqual(self.emu.dma[i].getPending(), config1, msg=msg)

                    # TCD1 should not be the active transfer (because that only
                    # happens in a small minor-loop self linked condition)
                    self.assertEqual(self.emu.dma[i]._active, None, msg=msg)

                    # But it should be the first pending transfer
                    self.assertTrue(chan1 in self.emu.dma[i]._pending, msg=msg)
                    self.assertEqual(self.emu.dma[i].getPending(), config1, msg=msg)

                    # Confirm that citer has been decremented
                    self.assertEqual(self.emu.dma[i].registers.tcd[chan1].citer, citer, msg=msg)
                else:
                    self.assertEqual(self.emu.dma[i].registers.tcd[chan1].start, 0, msg=msg)
                    self.assertEqual(self.emu.dma[i].registers.tcd[chan1].active, 0, msg=msg)
                    self.assertEqual(self.emu.dma[i].registers.tcd[chan1].done, 1, msg=msg)
                    self.assertTrue(chan1 not in self.emu.dma[i]._pending, msg=msg)
                    self.assertEqual(self.emu.dma[i].getPending(), None, msg=msg)

                    # Confirm that citer has been reset to the starting value
                    self.assertEqual(self.emu.dma[i].registers.tcd[chan1].citer, tcd1.biter, msg=msg)

            self.assertEqual(self.emu.readMemory(tcd2.daddr - tcd2.nbytes, sdata2_size), sdata2_expected, msg=devname)
            self.assertEqual(self.emu.readMemory(tcd1.daddr - tcd1.nbytes, sdata1_size), sdata1_expected, msg=devname)

            # No active transfers anymore
            self.assertEqual(self.emu.dma[i]._active, None, msg=devname)

            # No more pending transfers
            self.assertEqual(self.emu.dma[i]._pending, {}, msg=devname)

            # There should still be the processActiveTransfers function
            # registered for this peripheral, it will clear itself on the next
            # cycle
            self.assertEqual(self.emu.extra_processing, [self.emu.dma[i].processActiveTransfers], msg=devname)
            self.emu.stepi()
            self.assertEqual(self.emu.extra_processing, [], msg=devname)

    @unittest.skip('implement')
    def test_edma_fixed_priority(self):
        pass

    @unittest.skip('implement')
    def test_edma_rr_priority(self):
        pass

    def test_edma_hw_trigger(self):
        # Set the "normal" empty DSPI A receive queue value that isn't an
        # attempt to mimic real hardware
        self.emu.dspi[0]._popr_empty_data = b'\x00\x00\x00\x00'

        dspi_a_mcr_addr     = 0XFFF90000
        dspi_a_sr_addr      = 0XFFF9002C
        dspi_a_rser_addr    = 0XFFF90030
        dspi_a_popr_addr    = 0XFFF90038

        SR_RFDF_MASK        = 0x00020000
        RSER_RFDF_RE_MASK   = 0x00020000
        RSER_RFDF_DIRS_MASK = 0x00010000

        # Enable DSPI A
        self.emu.writeMemValue(dspi_a_mcr_addr, 0, 4)

        # Set the RSER[RFDF_RE] flag to indicate that received messages should
        # result in an interrupt or DMA request
        value = self.emu.readMemValue(dspi_a_rser_addr, 4)
        self.emu.writeMemValue(dspi_a_rser_addr, value | RSER_RFDF_RE_MASK, 4)

        # Set up the DSPI A receive event (eDMA A, channel 33)
        # Configure the TCD to do a circular queue of 4 2-byte entries @
        # 0x40000000
        tcd = TCD(self.emu, start=0, saddr=dspi_a_popr_addr, ssize=2, slast=0,
                  daddr=0x40000000, dsize=2, dmod=3, nbytes=2, biter=1, citer=1,
                  dlast_sga=2)
        tcd_addr = EDMA_DEVICES[0][1] + EDMA_TCDx_OFFSET + (32 * 33)
        tcd.write(self.emu, tcd_addr)

        # Populate known patterns from 0x40000000 - 0x40000010
        self.emu.writeMemory(0x40000000, b'\x11\x11\x22\x22\x33\x33\x44\x44')

        ########################
        # Leave ERQRH[ERQ33] unset and RSER[RFDF_DIRS] clear, send a message to
        # DSPI A
        ########################

        self.emu.dspi[0].processReceivedData(0xAAAA)
        self.assertEqual(self.emu.dma[0]._pending, {})
        self.emu.dma[0].processActiveTransfers()

        # ensure that it was not automatically moved to the destination
        # address as specified in TCD33
        self.assertEqual(self.emu.readMemory(0x40000000, 8),
                         b'\x11\x11\x22\x22\x33\x33\x44\x44')
        self.assertEqual(self.emu.readMemory(dspi_a_popr_addr, 4), b'\x00\x00\xAA\xAA')
        self.assertEqual(self.emu.readMemory(dspi_a_popr_addr, 4), b'\x00\x00\x00\x00')

        # Ensure that the SR[RFDF] flag is set and the right exception has been
        # queued.
        self.assertEqual(self.emu.readMemValue(dspi_a_sr_addr, 4) & SR_RFDF_MASK, SR_RFDF_MASK)
        self.assertEqual(self._getPendingExceptions(),
                         [intc_exc.ExternalException(intc_exc.INTC_SRC.DSPI_A_RX_DRAIN)])
        self.emu.writeMemValue(dspi_a_sr_addr, SR_RFDF_MASK, 4)
        self.assertEqual(self.emu.readMemValue(dspi_a_sr_addr, 4) & SR_RFDF_MASK, 0)

        ########################
        # Set ERQRH[ERQ33] but leave RSER[RFDF_DIRS] cleared and ensure the
        # normal interrupt still happens.
        ########################

        erqrh_addr = EDMA_DEVICES[0][1] + EDMA_ERQRH_OFFSET
        self.emu.writeMemValue(erqrh_addr, 0x00000002, 4)

        self.emu.dspi[0].processReceivedData(0xBBBB)
        self.assertEqual(self.emu.dma[0]._pending, {})
        self.emu.dma[0].processActiveTransfers()

        # ensure that it was not automatically moved to the destination
        # address as specified in TCD33
        self.assertEqual(self.emu.readMemory(0x40000000, 8),
                         b'\x11\x11\x22\x22\x33\x33\x44\x44')
        self.assertEqual(self.emu.readMemory(dspi_a_popr_addr, 4), b'\x00\x00\xBB\xBB')
        self.assertEqual(self.emu.readMemory(dspi_a_popr_addr, 4), b'\x00\x00\x00\x00')

        # Ensure that the SR[RFDF] flag is set and the right exception has been
        # queued.
        self.assertEqual(self.emu.readMemValue(dspi_a_sr_addr, 4) & SR_RFDF_MASK, SR_RFDF_MASK)
        self.assertEqual(self._getPendingExceptions(),
                         [intc_exc.ExternalException(intc_exc.INTC_SRC.DSPI_A_RX_DRAIN)])
        self.emu.writeMemValue(dspi_a_sr_addr, SR_RFDF_MASK, 4)
        self.assertEqual(self.emu.readMemValue(dspi_a_sr_addr, 4) & SR_RFDF_MASK, 0)

        ########################
        # clear ERQRH[ERQ33] and set the RSER[RFDF_DIRS] bit for DSPI A and
        # ensure that the normal interrupt does not happen, but also the DMA
        # transfer does not happen.
        ########################

        value = self.emu.readMemValue(dspi_a_rser_addr, 4)
        self.emu.writeMemValue(dspi_a_rser_addr, value | RSER_RFDF_DIRS_MASK, 4)

        erqrh_addr = EDMA_DEVICES[0][1] + EDMA_ERQRH_OFFSET
        self.emu.writeMemValue(erqrh_addr, 0x00000000, 4)

        self.emu.dspi[0].processReceivedData(0xCCCC)
        self.assertEqual(self.emu.dma[0]._pending, {})
        self.emu.dma[0].processActiveTransfers()

        # ensure that it was not automatically moved to the destination
        # address as specified in TCD33
        self.assertEqual(self.emu.readMemory(0x40000000, 8),
                         b'\x11\x11\x22\x22\x33\x33\x44\x44')
        self.assertEqual(self.emu.readMemory(dspi_a_popr_addr, 4), b'\x00\x00\xCC\xCC')
        self.assertEqual(self.emu.readMemory(dspi_a_popr_addr, 4), b'\x00\x00\x00\x00')

        # Ensure that the SR[RFDF] flag is not set and the no exceptions are
        # queued.
        self.assertEqual(self.emu.readMemValue(dspi_a_sr_addr, 4) & SR_RFDF_MASK, 0)
        self.assertEqual(self._getPendingExceptions(), [])

        ########################
        # set ERQRH[ERQ33] and set the RSER[RFDF_DIRS] bit for DSPI A and ensure
        # that the RFDF interrupt is not set but rather the data is copied
        # correctly to the destination address specified in TCD33 using the
        # circular queue feature.
        ########################

        erqrh_addr = EDMA_DEVICES[0][1] + EDMA_ERQRH_OFFSET
        self.emu.writeMemValue(erqrh_addr, 0x00000002, 4)

        # Test messages and the address we expect them to be placed at
        msgs = (
            (random.randrange(1, 0xFFFF+1), 0x40000000),
            (random.randrange(1, 0xFFFF+1), 0x40000002),
            (random.randrange(1, 0xFFFF+1), 0x40000004),
            (random.randrange(1, 0xFFFF+1), 0x40000006),
            (random.randrange(1, 0xFFFF+1), 0x40000000),
            (random.randrange(1, 0xFFFF+1), 0x40000002),
        )
        expected = bytearray(b'\x11\x11\x22\x22\x33\x33\x44\x44')
        for msg, daddr in msgs:
            # Modify the expected bytes to match what should be read @
            # 0x40000000 after the DMA transfer is complete.
            offset = daddr - 0x40000000
            expected[offset:offset+2] = e_bits.buildbytes(msg, 2, bigend=self.emu.getEndian())

            # Send the message and force the transfer to complete
            self.emu.dspi[0].processReceivedData(msg)
            self.assertTrue(33 in self.emu.dma[0]._pending)
            self.emu.dma[0].processActiveTransfers()
            self.assertEqual(self.emu.dma[0]._pending, {})

            # ensure the message was moved to the destination and the POPR
            # register is empty
            data = self.emu.readMemory(0x40000000, 8)
            logger.debug('send msg 0x%x, dest 0x%08x: %s', msg, daddr, data.hex())
            self.assertEqual(data, expected)
            self.assertEqual(self.emu.readMemory(dspi_a_popr_addr, 4), b'\x00\x00\x00\x00')

            # Ensure that the SR[RFDF] flag is not set and the no exceptions are
            # queued.
            self.assertEqual(self.emu.readMemValue(dspi_a_sr_addr, 4) & SR_RFDF_MASK, 0)
            self.assertEqual(self._getPendingExceptions(), [])

    @unittest.skip('implement')
    def test_edma_channel_linking(self):
        pass

    @unittest.skip('implement')
    def test_edma_scatter_gather(self):
        pass
