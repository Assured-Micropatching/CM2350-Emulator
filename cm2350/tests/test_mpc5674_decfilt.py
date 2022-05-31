from .helpers import MPC5674_Test


DECFILT_DEVICES = (
    ('DECFILT_A', 0XFFF88000),
    ('DECFILT_B', 0XFFF88800),
    ('DECFILT_C', 0XFFF89000),
    ('DECFILT_D', 0XFFF89800),
    ('DECFILT_E', 0XFFF8A000),
    ('DECFILT_F', 0XFFF8A800),
    ('DECFILT_G', 0XFFF8B000),
    ('DECFILT_H', 0XFFF8B800),
)

DECFILT_MCR_OFFSET       = 0x0000
DECFILT_MSR_OFFSET       = 0x0004
DECFILT_MXCR_OFFSET      = 0x0008
DECFILT_MXSR_OFFSET      = 0x000C
DECFILT_IB_OFFSET        = 0x0010
DECFILT_OB_OFFSET        = 0x0014
DECFILT_COEF_RANGE       = range(0x0020, 0x0044, 4)
DECFILT_TAP_RANGE        = range(0x0078, 0x0098, 4)
DECFILT_EDID_OFFSET      = 0x00D0
DECFILT_FINTVAL_OFFSET   = 0x00E0
DECFILT_FINTCNT_OFFSET   = 0x00E4
DECFILT_CINTVAL_OFFSET   = 0x00E8
DECFILT_CINTCNT_OFFSET   = 0x00EC

# The number of COEF and TAP registers
DECFILT_NUM_COEF       = 9
DECFILT_NUM_TAP        = 8

# The MCR register is the only one with a non-0 default value
DECFILT_MCR_DEFAULT       = 0x00008000
DECFILT_MCR_DEFAULT_BYTES = b'\x00\x00\x80\x00'


class MPC5674_DECFILT_Test(MPC5674_Test):

    ##################################################
    # Simple Register Tests
    ##################################################

    def test_decfilt_mcr(self):
        for dev in range(len(DECFILT_DEVICES)):
            devname, baseaddr = DECFILT_DEVICES[dev]
            self.assertEqual(self.emu.decfilt[dev].devname, devname)

            addr = baseaddr + DECFILT_MCR_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), DECFILT_MCR_DEFAULT_BYTES, msg=devname)
            self.assertEqual(self.emu.readMemValue(addr, 4), DECFILT_MCR_DEFAULT, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mcr.mdis, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mcr.fren, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mcr.frz, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mcr.sres, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mcr.cascd, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mcr.iden, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mcr.oden, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mcr.erren, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mcr.ftype, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mcr.scal, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mcr.idis, 1, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mcr.sat, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mcr.io_sel, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mcr.dec_rate, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mcr.sdie, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mcr.dsel, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mcr.ibie, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mcr.obie, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mcr.edme, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mcr.tore, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mcr.tmode, 0, msg=devname)

    def test_decfilt_msr(self):
        for dev in range(len(DECFILT_DEVICES)):
            devname, baseaddr = DECFILT_DEVICES[dev]
            self.assertEqual(self.emu.decfilt[dev].devname, devname)

            addr = baseaddr + DECFILT_MSR_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00', msg=devname)
            self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.msr.bsy, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.msr.dec_counter, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.msr.idfc, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.msr.odfc, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.msr.ibic, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.msr.obic, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.msr.divrc, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.msr.ovfc, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.msr.ovrc, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.msr.ivrc, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.msr.idf, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.msr.odf, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.msr.ibif, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.msr.obif, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.msr.divr, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.msr.ovf, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.msr.ovr, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.msr.ivr, 0, msg=devname)

    def test_decfilt_mxcr(self):
        for dev in range(len(DECFILT_DEVICES)):
            devname, baseaddr = DECFILT_DEVICES[dev]
            self.assertEqual(self.emu.decfilt[dev].devname, devname)

            addr = baseaddr + DECFILT_MXCR_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00', msg=devname)
            self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mxcr.sdmae, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mxcr.ssig, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mxcr.ssat, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mxcr.scsat, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mxcr.srq, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mxcr.szro, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mxcr.sisel, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mxcr.szrosel, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mxcr.shltsel, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mxcr.srqsel, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mxcr.sensel, 0, msg=devname)

    def test_decfilt_mxsr(self):
        for dev in range(len(DECFILT_DEVICES)):
            devname, baseaddr = DECFILT_DEVICES[dev]
            self.assertEqual(self.emu.decfilt[dev].devname, devname)

            addr = baseaddr + DECFILT_MXSR_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00', msg=devname)
            self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mxsr.sdfc, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mxsr.ssec, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mxsr.scec, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mxsr.ssovfc, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mxsr.scovfc, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mxsr.svrc, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mxsr.sdf, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mxsr.sse, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mxsr.sce, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mxsr.ssovf, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mxsr.scovf, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.mxsr.svr, 0, msg=devname)

    def test_decfilt_ib(self):
        for dev in range(len(DECFILT_DEVICES)):
            devname, baseaddr = DECFILT_DEVICES[dev]
            self.assertEqual(self.emu.decfilt[dev].devname, devname)

            addr = baseaddr + DECFILT_IB_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00', msg=devname)
            self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.ib.intag, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.ib.prefill, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.ib.flush, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.ib.inpbuf, 0, msg=devname)

    def test_decfilt_ob(self):
        for dev in range(len(DECFILT_DEVICES)):
            devname, baseaddr = DECFILT_DEVICES[dev]
            self.assertEqual(self.emu.decfilt[dev].devname, devname)

            addr = baseaddr + DECFILT_OB_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00', msg=devname)
            self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.ob.outtag, 0, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.ob.outbuf, 0, msg=devname)

    def test_decfilt_coef(self):
        self.assertEqual(len(list(DECFILT_COEF_RANGE)), DECFILT_NUM_COEF)

        for dev in range(len(DECFILT_DEVICES)):
            devname, baseaddr = DECFILT_DEVICES[dev]
            self.assertEqual(self.emu.decfilt[dev].devname, devname)

            for idx, offset in zip(range(DECFILT_NUM_COEF), DECFILT_COEF_RANGE):
                addr = baseaddr + offset

                self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00', msg=devname)
                self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000, msg=devname)
                self.assertEqual(self.emu.decfilt[dev].registers.coef[idx].value, 0, msg=devname)

    def test_decfilt_tap(self):
        self.assertEqual(len(list(DECFILT_TAP_RANGE)), DECFILT_NUM_TAP)

        for dev in range(len(DECFILT_DEVICES)):
            devname, baseaddr = DECFILT_DEVICES[dev]
            self.assertEqual(self.emu.decfilt[dev].devname, devname)

            for idx, offset in zip(range(DECFILT_NUM_TAP), DECFILT_TAP_RANGE):
                addr = baseaddr + offset

                self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00', msg=devname)
                self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000)
                self.assertEqual(self.emu.decfilt[dev].registers.tap[idx].value, 0, msg=devname)

    def test_decfilt_edid(self):
        for dev in range(len(DECFILT_DEVICES)):
            devname, baseaddr = DECFILT_DEVICES[dev]
            self.assertEqual(self.emu.decfilt[dev].devname, devname)

            addr = baseaddr + DECFILT_EDID_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00', msg=devname)
            self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.edid.samp_data, 0, msg=devname)

    def test_decfilt_fintval(self):
        for dev in range(len(DECFILT_DEVICES)):
            devname, baseaddr = DECFILT_DEVICES[dev]
            self.assertEqual(self.emu.decfilt[dev].devname, devname)

            addr = baseaddr + DECFILT_FINTVAL_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00')
            self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.fintval.value, 0, msg=devname)

    def test_decfilt_fintcnt(self):
        for dev in range(len(DECFILT_DEVICES)):
            devname, baseaddr = DECFILT_DEVICES[dev]
            self.assertEqual(self.emu.decfilt[dev].devname, devname)

            addr = baseaddr + DECFILT_FINTCNT_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00', msg=devname)
            self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.fintcnt.count, 0, msg=devname)

    def test_decfilt_cintval(self):
        for dev in range(len(DECFILT_DEVICES)):
            devname, baseaddr = DECFILT_DEVICES[dev]
            self.assertEqual(self.emu.decfilt[dev].devname, devname)

            addr = baseaddr + DECFILT_CINTVAL_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00', msg=devname)
            self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.cintval.value, 0, msg=devname)

    def test_decfilt_cintcnt(self):
        for dev in range(len(DECFILT_DEVICES)):
            devname, baseaddr = DECFILT_DEVICES[dev]
            self.assertEqual(self.emu.decfilt[dev].devname, devname)

            addr = baseaddr + DECFILT_CINTCNT_OFFSET

            self.assertEqual(self.emu.readMemory(addr, 4), b'\x00\x00\x00\x00', msg=devname)
            self.assertEqual(self.emu.readMemValue(addr, 4), 0x00000000, msg=devname)
            self.assertEqual(self.emu.decfilt[dev].registers.cintcnt.count, 0, msg=devname)
