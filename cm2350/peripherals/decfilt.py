from ..ppc_vstructs import *
from ..ppc_peripherals import *
from ..intc_exc import ResetException

import logging
logger = logging.getLogger(__name__)

__all__  = [
    'DECFILT',
]


DECFILT_MCR_OFFSET     = 0x0000
DECFILT_MSR_OFFSET     = 0x0004
DECFILT_MXCR_OFFSET    = 0x0008
DECFILT_MXSR_OFFSET    = 0x000C
DECFILT_IB_OFFSET      = 0x0010
DECFILT_OB_OFFSET      = 0x0014
DECFILT_COEF_OFFSET    = 0x0020
DECFILT_TAP_OFFSET     = 0x0078
DECFILT_EDID_OFFSET    = 0x00D0
DECFILT_FINTVAL_OFFSET = 0x00E0
DECFILT_FINTCNT_OFFSET = 0x00E4
DECFILT_CINTVAL_OFFSET = 0x00E8
DECFILT_CINTCNT_OFFSET = 0x00EC

# Coefficient sign/mask constants
DECFILT_COEF_SIGN      = 0x00800000
DECFILT_COEF_SIGN_MASK = 0xFF000000

# There are 9 filter coefficient values and 8 filter TAP values
DECFILT_NUM_COEF       = 9
DECFILT_NUM_TAP        = 8


class DECFILT_x_MCR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.mdis = v_bits(1)
        self.fren = v_bits(1)
        self._pad0 = v_const(1)
        self.frz = v_bits(1)
        self.sres = v_bits(1)
        self.cascd = v_bits(2)
        self.iden = v_bits(1)
        self.oden = v_bits(1)
        self.erren = v_bits(1)
        self._pad1 = v_const(1)
        self.ftype = v_bits(2)
        self._pad2 = v_const(1)
        self.scal = v_bits(2)
        self.idis = v_defaultbits(1, 1)
        self.sat = v_bits(1)
        self.io_sel = v_bits(2)
        self.dec_rate = v_bits(4)
        self.sdie = v_bits(1)
        self.dsel = v_bits(1)
        self.ibie = v_bits(1)
        self.obie = v_bits(1)
        self.edme = v_bits(1)
        self.tore = v_bits(1)
        self.tmode = v_bits(2)


class DECFILT_x_MSR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.bsy = v_const(1)
        self._pad0 = v_const(1)
        self.dec_counter = v_const(4)
        self.idfc = v_bits(1)
        self.odfc = v_bits(1)
        self._pad1 = v_const(1)
        self.ibic = v_bits(1)
        self.obic = v_bits(1)
        self._pad2 = v_const(1)
        self.divrc = v_bits(1)
        self.ovfc = v_bits(1)
        self.ovrc = v_bits(1)
        self.ivrc = v_bits(1)
        self._pad3 = v_const(6)
        self.idf = v_const(1)
        self.odf = v_const(1)
        self._pad4 = v_const(1)
        self.ibif = v_const(1)
        self.obif = v_const(1)
        self._pad5 = v_const(1)
        self.divr = v_const(1)
        self.ovf = v_const(1)
        self.ovr = v_const(1)
        self.ivr = v_const(1)

    # For now the clear/flag behavior is handled by pcb_* functions in this
    # class definition because there is no higher-level attached DECFILT
    # functionality to clearing these bits

    def pcb_idfc(self, thing):
        if self.idfc:
            self.idfc = 0
            self.vsOverrideValue('idf', 0)

    def pcb_odfc(self, thing):
        if self.odfc:
            self.odfc = 0
            self.vsOverrideValue('odf', 0)

    def pcb_ibic(self, thing):
        if self.ibic:
            self.ibic = 0
            self.vsOverrideValue('ibif', 0)

    def pcb_obic(self, thing):
        if self.obic:
            self.obic = 0
            self.vsOverrideValue('obif', 0)

    def pcb_divrc(self, thing):
        if self.divrc:
            self.divrc = 0
            self.vsOverrideValue('divr', 0)

    def pcb_ovfc(self, thing):
        if self.ovfc:
            self.ovfc = 0
            self.vsOverrideValue('ovf', 0)

    def pcb_ovrc(self, thing):
        if self.ovrc:
            self.ovrc = 0
            self.vsOverrideValue('ovr', 0)

    def pcb_ivrc(self, thing):
        if self.ivrc:
            self.ivrc = 0
            self.vsOverrideValue('ivr', 0)

class DECFILT_x_MXCR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.sdmae = v_bits(1)
        self.ssig = v_bits(1)
        self.ssat = v_bits(1)
        self.scsat = v_bits(1)
        self._pad0 = v_const(10)
        self.srq = v_bits(1)
        self.szro = v_bits(1)
        self.sisel = v_bits(1)
        self._pad1 = v_const(1)
        self.szrosel = v_bits(2)
        self._pad2 = v_const(2)
        self.shltsel = v_bits(2)
        self._pad3 = v_const(1)
        self.srqsel = v_bits(3)
        self._pad4 = v_const(2)
        self.sensel = v_bits(2)

class DECFILT_x_MXSR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(7)
        self.sdfc = v_bits(1)
        self._pad1 = v_const(2)
        self.ssec = v_bits(1)
        self.scec = v_bits(1)
        self._pad2 = v_const(1)
        self.ssovfc = v_bits(1)
        self.scovfc = v_bits(1)
        self.svrc = v_bits(1)
        self._pad3 = v_const(7)
        self.sdf = v_const(1)
        self._pad4 = v_const(2)
        self.sse = v_const(1)
        self.sce = v_const(1)
        self._pad5 = v_const(1)
        self.ssovf = v_const(1)
        self.scovf = v_const(1)
        self.svr = v_const(1)

    def pcb_sdfc(self, thing):
        if self.sdfc:
            self.sdfc = 0
            self.vsOverrideValue('sdf', 0)

    def pcb_ssec(self, thing):
        if self.ssec:
            self.ssec = 0
            self.vsOverrideValue('sse', 0)

    def pcb_scec(self, thing):
        if self.scec:
            self.scec = 0
            self.vsOverrideValue('sce', 0)

    def pcb_ssovfc(self, thing):
        if self.ssovfc:
            self.ssovfc = 0
            self.vsOverrideValue('ssovf', 0)

    def pcb_scovfc(self, thing):
        if self.scovfc:
            self.scovfc = 0
            self.vsOverrideValue('scovf', 0)

    def pcb_svrc(self, thing):
        if self.svrc:
            self.svrc = 0
            self.vsOverrideValue('svr', 0)

class DECFILT_x_IB(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(4)
        self.intag = v_bits(4)
        self._pad1 = v_const(6)
        self.prefill = v_bits(1)
        self.flush = v_bits(1)
        self.inpbuf = v_bits(16)

class DECFILT_x_OB(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(12)
        self.outtag = v_const(4)
        self.outbuf = v_const(16)

class DECFILT_x_EDID(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(16)
        self.samp_data = v_const(16)

class DECFILT_x_VALUE(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.value = v_const(32)

class DECFILT_x_COUNT(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.count = v_const(32)

class DECFILT_REGISTERS(PeripheralRegisterSet):
    def __init__(self, emu=None):
        super().__init__(emu)

        self.mcr     = (DECFILT_MCR_OFFSET,     DECFILT_x_MCR())
        self.msr     = (DECFILT_MSR_OFFSET,     DECFILT_x_MSR())
        self.mxcr    = (DECFILT_MXCR_OFFSET,    DECFILT_x_MXCR())
        self.mxsr    = (DECFILT_MXSR_OFFSET,    DECFILT_x_MXSR())
        self.ib      = (DECFILT_IB_OFFSET,      DECFILT_x_IB())
        self.ob      = (DECFILT_OB_OFFSET,      DECFILT_x_OB())
        self.coef    = (DECFILT_COEF_OFFSET,    VArray([DECFILT_x_VALUE() for i in range(DECFILT_NUM_COEF)]))
        self.tap     = (DECFILT_TAP_OFFSET,     VArray([DECFILT_x_VALUE() for i in range(DECFILT_NUM_TAP)]))
        self.edid    = (DECFILT_EDID_OFFSET,    DECFILT_x_EDID())
        self.fintval = (DECFILT_FINTVAL_OFFSET, DECFILT_x_VALUE())
        self.fintcnt = (DECFILT_FINTCNT_OFFSET, DECFILT_x_COUNT())
        self.cintval = (DECFILT_CINTVAL_OFFSET, DECFILT_x_VALUE())
        self.cintcnt = (DECFILT_CINTCNT_OFFSET, DECFILT_x_COUNT())


class DECFILT(MMIOPeripheral):
    def __init__(self, devname, emu, mmio_addr):
        super().__init__(emu, devname, mmio_addr, 0x800, regsetcls=DECFILT_REGISTERS)

        self.registers.vsAddParseCallback('mcr', self.mcrUpdate)
        self.registers.vsAddParseCallback('mxcr', self.mxcrUpdate)
        self.registers.vsAddParseCallback('ib', self.ibUpdate)
        self.registers.vsAddParseCallback('by_idx_coef', self.coefUpdate)

    def softReset(self):
        """
        Clear the TAP and MSR registers
        """
        self.registers.msr.reset()
        for _, vobj in self.registers.tap.vsGetFields():
            vobj.reset()

    def mcrUpdate(self, thing):
        if self.registers.msr.sres:
            self.registers.msr.sres = 0
            self.softReset()

    def mxcrUpdate(self, thing):
        if self.registers.msr.srq:
            self.registers.msr.srq = 0
            self.integratorOutputRequest()

        if self.registers.msr.szro:
            self.registers.msr.szro = 0
            self.integratorZero()

    def ibUpdate(self, thing):
        self.newInput()

    def coefUpdate(self, thing, idx, size):
        # Take the 24-bit 2's compliment value and sign extend it
        coef = self.registers.coef[idx].value
        if coef & DECFILT_COEF_SIGN:
            self.registers.coef[idx].value = coef | DECFILT_COEF_SIGN_MASK
        else:
            self.registers.coef[idx].value = coef & ~DECFILT_COEF_SIGN_MASK

    def integratorOutputRequest(self):
        raise NotImplementedError()

    def integratorZero(self):
        raise NotImplementedError()

    def newInput(self):
        raise NotImplementedError()
