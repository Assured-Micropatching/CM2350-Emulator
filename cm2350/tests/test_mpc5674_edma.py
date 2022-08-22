
import envi.bits as e_bits

from .helpers import MPC5674_Test


FLEXCAN_DEVICES = (
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


class MPC5674_eDMA_Test(MPC5674_Test):

    # Simple register tests

    def test_edma_mcr_defaults(self):
        for i in range(len(FLEXCAN_DEVICES)):
            devname, baseaddr = FLEXCAN_DEVICES[i]
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
        for i in range(len(FLEXCAN_DEVICES)):
            devname, baseaddr = FLEXCAN_DEVICES[i]
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
        for i in range(len(FLEXCAN_DEVICES)):
            devname, baseaddr = FLEXCAN_DEVICES[i]
            self.assertEqual(self.emu.dma[i].devname, devname)

            if devname == 'eDMA_A':
                addr = baseaddr + EDMA_ERQRH_OFFSET
                self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000)
                self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')

            addr = baseaddr + EDMA_ERQRL_OFFSET
            self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000)
            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')

    def test_edma_eeir_defaults(self):
        for i in range(len(FLEXCAN_DEVICES)):
            devname, baseaddr = FLEXCAN_DEVICES[i]
            self.assertEqual(self.emu.dma[i].devname, devname)

            if devname == 'eDMA_A':
                addr = baseaddr + EDMA_EEIRH_OFFSET
                self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000)
                self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')

            addr = baseaddr + EDMA_EEIRL_OFFSET
            self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000)
            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')

    def test_edma_irqr_defaults(self):
        for i in range(len(FLEXCAN_DEVICES)):
            devname, baseaddr = FLEXCAN_DEVICES[i]
            self.assertEqual(self.emu.dma[i].devname, devname)

            if devname == 'eDMA_A':
                addr = baseaddr + EDMA_IRQRH_OFFSET
                self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000)
                self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')

            addr = baseaddr + EDMA_IRQRL_OFFSET
            self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000)
            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')

    def test_edma_er_defaults(self):
        for i in range(len(FLEXCAN_DEVICES)):
            devname, baseaddr = FLEXCAN_DEVICES[i]
            self.assertEqual(self.emu.dma[i].devname, devname)

            if devname == 'eDMA_A':
                addr = baseaddr + EDMA_ERH_OFFSET
                self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000)
                self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')

            addr = baseaddr + EDMA_ERL_OFFSET
            self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000)
            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')

    def test_edma_hrs_defaults(self):
        for i in range(len(FLEXCAN_DEVICES)):
            devname, baseaddr = FLEXCAN_DEVICES[i]
            self.assertEqual(self.emu.dma[i].devname, devname)

            if devname == 'eDMA_A':
                addr = baseaddr + EDMA_HRSH_OFFSET
                self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000)
                self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')

            addr = baseaddr + EDMA_HRSL_OFFSET
            self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000)
            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')

    def test_edma_gwr_defaults(self):
        for i in range(len(FLEXCAN_DEVICES)):
            devname, baseaddr = FLEXCAN_DEVICES[i]
            self.assertEqual(self.emu.dma[i].devname, devname)

            if devname == 'eDMA_A':
                addr = baseaddr + EDMA_GWRH_OFFSET
                self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000)
                self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')

            addr = baseaddr + EDMA_GWRL_OFFSET
            self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000)
            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')

    def test_edma_cpr_defaults(self):
        for i in range(len(FLEXCAN_DEVICES)):
            devname, baseaddr = FLEXCAN_DEVICES[i]
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
        for i in range(len(FLEXCAN_DEVICES)):
            devname, baseaddr = FLEXCAN_DEVICES[i]
            self.assertEqual(self.emu.dma[i].devname, devname)

            if devname == 'eDMA_A':
                self.assertEqual(self.emu.dma[i].num_channels, 64)
            else:
                self.assertEqual(self.emu.dma[i].num_channels, 32)

            addr = baseaddr + EDMA_TCDx_OFFSET
            # Each TCD is a 256 bit (8 byte) field
            bytevalue = b'\x00' * 8
            for chan in range(self.emu.dma[i].num_channels):
                testmsg = '%s[%d]' % (devname, chan)
                self.assertEqual(self.emu.readMemValue(addr + (8*chan), 8), 0, msg=testmsg)
                self.assertEqual(self.emu.readMemory(addr + (8*chan), 8), bytevalue, msg=testmsg)
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
