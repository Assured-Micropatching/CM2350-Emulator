from ..ppc_vstructs import *
from ..ppc_peripherals import *
from ..intc_exc import ResetException

import logging
logger = logging.getLogger(__name__)

__all__  = [
    'SIU',
]


NUM_GPDIO_PINS = 512


class SIU_MIDR(ReadOnlyRegister):
    def __init__(self):
        super().__init__()
        # TODO: These values are Core/Part-specific, get from config?
        self.partnum = v_const(16, 0x5674)
        self.pkg = v_const(4, 0b1110)
        self._pad0 = v_const(4)
        self.masknum_major =  v_const(4)
        self.masknum_minor = v_const(4)


class SIU_RSR(PeriphRegister):
    # TODO: SYSTEM_RESET reasons should eventually be linked to the e200z7
    # setException API.
    #
    # TODO: there are various fields in this register that appear to be
    # read-only (like the PORS field) but may need to be able to be changed to
    # reflect system reset information. For now set these bits as
    # const/read-only
    def __init__(self, wkpcfg, bootcfg):
        super().__init__()
        self.pors = v_const(1)
        self.ers = v_const(1)
        self.llrs = v_const(1)
        self.lcrs = v_const(1)
        self.wdrs = v_const(1)
        self._pad0 = v_const(1)
        self.swtrs = v_const(1)
        self._pad1 = v_const(7)
        self.ssrs = v_const(1)
        self.serf = v_w1c(1)
        self.wkpcfg = v_const(1, wkpcfg)
        self._pad2 = v_const(11)
        self.abr = v_const(1)
        self.bootcfg = v_const(2, bootcfg)
        self.rgf = v_w1c(1)


class SIU_SRCR(PeriphRegister):  # System Reset Control Register...
    # TODO: might need to hook this one with some special logic
    def __init__(self):
        super().__init__()
        self.ssr = v_bits(1)
        self.ser = v_bits(1)
        self._pad0 = v_const(30)


class SIU_EISR(PeriphRegister):  # External Interrupt Status Register
    # TODO: bit 0 should be linked to the NMI exception handling
    def __init__(self):
        super().__init__()
        self.nmi = v_w1c(1)
        self._pad0 = v_const(15)
        self.eif = v_w1c(16)


class SIU_DIRER(PeriphRegister):     # DMA/Interrupt Request Enable Register
    # TODO: bit 0 & 8 should be linked to the NMI exception handling
    def __init__(self):
        super().__init__()
        self.nmi_sel8 = v_bits(1)
        self._pad0 = v_const(7)
        self.nmi_sel0 = v_bits(1)
        self._pad1 = v_const(7)
        self.eire = v_bits(16)


class SIU_DIRSR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(28)
        self.dirs = v_bits(4)


class SIU_OSR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(16)
        self.ovf = v_bits(16)


class SIU_ORER(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(16)
        self.ore = v_bits(16)


class SIU_IREER(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.iree_nmi8 = v_bits(1)
        self._pad0 = v_const(15)
        self.iree = v_bits(16)


class SIU_IFEER(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.ifee_nmi8 = v_bits(1)
        self._pad0 = v_const(15)
        self.ifee = v_bits(16)


class SIU_IDFR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(28)
        self.dfl = v_bits(4)


class SIU_IFIR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.ifi_nmi = v_bits(1)
        self._pad0 = v_const(15)
        self.ifi = v_bits(16)


class SIU_PCRn(PeriphRegister):
    def __init__(self, pa=None, obe=None, ibe=None, dsc=None, ode=None, hys=None, src=None, wpe=None, wps=None):
        super().__init__()

        # not all PCR fields are supported for all pins, if a value of None is
        # supplied define the field as a v_const field with a value of 0.
        # TODO: In some PCR fields the PA field is limited in valid range,
        # doesn't seem necessary to fully emulate this for now.

        self._pad0 = v_const(3)

        if pa is None:
            self.pa = v_const(3)
        else:
            self.pa = v_bits(3, pa)

        if obe is None:
            self.obe = v_const(1)
        else:
            self.obe = v_bits(1, obe)

        if ibe is None:
            self.ibe = v_const(1)
        else:
            self.ibe = v_bits(1, ibe)

        if dsc is None:
            self.dsc = v_const(2)
        else:
            self.dsc = v_bits(2, dsc)

        if ode is None:
            self.ode = v_const(1)
        else:
            self.ode = v_bits(1, ode)

        if hys is None:
            self.hys = v_const(1)
        else:
            self.hys = v_bits(1, hys)

        if src is None:
            self.src = v_const(2)
        else:
            self.src = v_bits(2, src)

        if wpe is None:
            self.wpe = v_const(1)
        else:
            self.wpe = v_bits(1, wpe)

        if wps is None:
            self.wps = v_const(1)
        else:
            self.wps = v_bits(1, wps)


class SIU_GPDOn(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(7)
        self.pdo = v_bits(1)


class SIU_GPDIn(ReadOnlyRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(7)
        self.pdi = v_bits(1)


class SIU_PGPDOn(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.data = v_bits(32)


class SIU_PGPDIn(ReadOnlyRegister):
    def __init__(self):
        super().__init__()
        self.data = v_bits(32)


class SIU_MPGPDOn(WriteOnlyRegister):
    def __init__(self):
        super().__init__()
        self.mask = v_bits(16)
        self.data = v_bits(16)


class SIU_EIISR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.esel15 = v_bits(2)
        self.esel14 = v_bits(2)
        self.esel13 = v_bits(2)
        self.esel12 = v_bits(2)
        self.esel11 = v_bits(2)
        self.esel10 = v_bits(2)
        self.esel9 = v_bits(2)
        self.esel8 = v_bits(2)
        self.esel7 = v_bits(2)
        self.esel6 = v_bits(2)
        self.esel5 = v_bits(2)
        self.esel4 = v_bits(2)
        self.esel3 = v_bits(2)
        self.esel2 = v_bits(2)
        self.esel1 = v_bits(2)
        self.esel0 = v_bits(2)


class SIU_DISR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.sinsela = v_bits(2)
        self.sssela = v_bits(2)
        self.scksela = v_bits(2)
        self.trigsela = v_bits(2)
        self.sinselb = v_bits(2)
        self.ssselb = v_bits(2)
        self.sckselb = v_bits(2)
        self.trigselb = v_bits(2)
        self.sinselc = v_bits(2)
        self.ssselc = v_bits(2)
        self.sckselc = v_bits(2)
        self.trigselc = v_bits(2)
        self.sinseld = v_bits(2)
        self.ssseld = v_bits(2)
        self.sckseld = v_bits(2)
        self.trigseld = v_bits(2)


class SIU_ISEL4(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(1)
        self.cTSEL5_0 = v_bits(7)
        self._pad1 = v_const(1)
        self.cTSEL4_0 = v_bits(7)
        self._pad2 = v_const(1)
        self.cTSEL3_0 = v_bits(7)
        self._pad3 = v_const(1)
        self.cTSEL2_0 = v_bits(7)


class SIU_ISEL5(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(1)
        self.cTSEL1_0 = v_bits(7)
        self._pad1 = v_const(1)
        self.cTSEL0_0 = v_bits(7)
        self._pad2 = v_const(16)


class SIU_ISEL6(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(1)
        self.cTSEL5_1 = v_bits(7)
        self._pad1 = v_const(1)
        self.cTSEL4_1 = v_bits(7)
        self._pad2 = v_const(1)
        self.cTSEL3_1 = v_bits(7)
        self._pad3 = v_const(1)
        self.cTSEL2_1 = v_bits(7)


class SIU_ISEL7(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(1)
        self.cTSEL1_1 = v_bits(7)
        self._pad1 = v_const(1)
        self.cTSEL0_1 = v_bits(7)
        self._pad2 = v_const(16)


class SIU_ISEL8(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(11)
        self.eTPU29 = v_bits(1)
        self._pad1 = v_const(3)
        self.eTPU28 = v_bits(1)
        self._pad2 = v_const(3)
        self.eTPU27 = v_bits(1)
        self._pad3 = v_const(3)
        self.eTPU26 = v_bits(1)
        self._pad4 = v_const(3)
        self.eTPU25 = v_bits(1)
        self._pad5 = v_const(3)
        self.eTPU24 = v_bits(1)


class SIU_ISEL9(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(27)
        self.eTSEL0A = v_bits(5)


class SIU_DECFIL(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.zsele = v_bits(4)
        self.hsele = v_bits(4)
        self.zself = v_bits(4)
        self.hself = v_bits(4)
        self.zselg = v_bits(4)
        self.hselg = v_bits(4)
        self.zselh = v_bits(4)
        self.hselh = v_bits(4)


class SIU_CCR(PeriphRegister):
    def __init__(self, match=0, disnex=0):
        super().__init__()
        self._pad0 = v_const(14)

        # NOTE: the CCR[MATCH] field indicates if password written to CBRH/CBRL
        # matches the password in flash
        self.match = v_const(1, match)

        # NOTE: the CCR[DISNEX] field holds the state of the "Nexus Disable"
        # signal which is determined based on the boot mode and some internal
        # values.  This is described more in the BAM section and specifically
        # in Table 8-3. Boot Modes (MPC5674FRM.pdf page 297).
        self.disnex = v_const(1, disnex)

        self._pad1 = v_const(15)
        self.test = v_bits(1)


class SIU_ECCR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(16)
        self.engdiv = v_bits(8, 0x10)
        self.ecss = v_bits(1)
        self._pad1 = v_const(3)
        self.ebts = v_bits(1)
        self._pad2 = v_const(1)
        self.ebdf = v_bits(2, 0x1)


class SIU_CBRH(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.cmpbh = v_bits(32)


class SIU_CBRL(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.cmpbl = v_bits(32)


class SIU_SYSDIV(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(22)
        self.ipclkdiv = v_bits(2)
        self._pad1 = v_const(3)
        self.bypass = v_bits(1, 1)
        self.sysclkdiv = v_bits(2)
        self._pad2 = v_const(2)


class SIU_HLT(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.hlt = v_bits(32)


class SIU_HLTACK(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.hltack = v_bits(32)


class SIU_REGISTERS(PeripheralRegisterSet):
    def __init__(self, wkpcfg, bootcfg):
        super().__init__()

        #############################################

        # There are 512 PCR registers but not all of them are valid, initialize
        # the PCR configurations with all fields set to None.
        #
        # NOTE: PCRs that are not valid should (probably) not be able to be able
        # to be modifed, but should have default values of 0 and should not
        # result in invalid read or write errors.  At least this is my current
        # best guess as to how PCRn values that don't correspond to a valid GPIO
        # should behave.
        self._pcr_defaults = [None for x in range(NUM_GPDIO_PINS)]

        # Configuration values set here are defined in:
        #   Table 6-22. SIU_PCRn Settings (MPC5674FRM.pdf page 225)
        #
        # Some of the pull-up/down initial values are based on the WKPCFG pin
        for pin in range(75, 83):
            self._pcr_defaults[pin] = {'pa': None, 'obe': 0,    'ibe': 0,    'dsc': 3,    'ode': None, 'hys': None, 'src': None, 'wpe': None, 'wps': None}

        for pin in range(83, 111):
            self._pcr_defaults[pin] = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': 1}
        self._pcr_defaults[113]     = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': 1}
        for pin in range(114, 146):
            self._pcr_defaults[pin] = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': wkpcfg}
        self._pcr_defaults[146]     = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': 1}
        for pin in range(147, 205):
            self._pcr_defaults[pin] = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': wkpcfg}

        # NOTE GPIO(210) is not in "Table 6-22" but is PLLCFG2.  It is not GPIO
        # capable but the default connection does cause the emulated external
        # pin value to be "1"
        for pin in range(208, 210):
            self._pcr_defaults[pin] = {'pa': 1,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 1,    'src': 0,    'wpe': 1,    'wps': 1}

        for pin in range(211, 213):
            self._pcr_defaults[pin] = {'pa': 1,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 1,    'src': 0,    'wpe': 1,    'wps': 0}
        self._pcr_defaults[213]     = {'pa': 1,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': None, 'hys': 1,    'src': 0,    'wpe': 1,    'wps': 1}
        self._pcr_defaults[214]     = {'pa': None, 'obe': 1,    'ibe': None, 'dsc': 3,    'ode': None, 'hys': None, 'src': None, 'wpe': None, 'wps': None}
        self._pcr_defaults[219]     = {'pa': None, 'obe': None, 'ibe': None, 'dsc': 3,    'ode': None, 'hys': None, 'src': None, 'wpe': None, 'wps': None}
        self._pcr_defaults[220]     = {'pa': None, 'obe': 0,    'ibe': 0,    'dsc': 3,    'ode': 0,    'hys': 0,    'src': 0,    'wpe': 0,    'wps': None}
        for pin in range(221, 224):
            self._pcr_defaults[pin] = {'pa': None, 'obe': 0,    'ibe': 0,    'dsc': 3,    'ode': 0,    'hys': 0,    'src': 0,    'wpe': 0,    'wps': 0}
        for pin in range(224, 229):
            self._pcr_defaults[pin] = {'pa': None, 'obe': None, 'ibe': None, 'dsc': 3,    'ode': None, 'hys': None, 'src': None, 'wpe': None, 'wps': None}
        self._pcr_defaults[229]     = {'pa': None, 'obe': 1,    'ibe': None, 'dsc': 3,    'ode': None, 'hys': None, 'src': None, 'wpe': None, 'wps': None}
        self._pcr_defaults[230]     = {'pa': None, 'obe': 1,    'ibe': None, 'dsc': None, 'ode': None, 'hys': None, 'src': 0,    'wpe': None, 'wps': None}
        for pin in range(231, 235):
            self._pcr_defaults[pin] = {'pa': None, 'obe': 0,    'ibe': 0,    'dsc': 3,    'ode': 0,    'hys': 0,    'src': None, 'wpe': 0,    'wps': 0}
        for pin in range(235, 248):
            self._pcr_defaults[pin] = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': 1}

        # NOTE: The WPE and PWS bits for pins 248-253 are marked in the
        # reference manual as being 1 on the second revision of the MPC5674F,
        # 0 on earlier revs.
        for pin in range(248, 254):
            self._pcr_defaults[pin] = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': 1}

        for pin in range(256, 299):
            self._pcr_defaults[pin] = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': 1}
        self._pcr_defaults[299] = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': 0}
        for pin in range(300, 308):
            self._pcr_defaults[pin] = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': 1}
        for pin in range(432, 438):
            self._pcr_defaults[pin] = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': wkpcfg}
        self._pcr_defaults[440] = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': 1}
        for pin in range(441, 472):
            self._pcr_defaults[pin] = {'pa': 0,    'obe': 0,    'ibe': 0,    'dsc': None, 'ode': 0,    'hys': 0,    'src': 0,    'wpe': 1,    'wps': wkpcfg}

        #############################################

        # Registers

        self.midr    = (0x0004, SIU_MIDR())
        self.rsr     = (0x000C, SIU_RSR(wkpcfg, bootcfg))
        self.srcr    = (0x0010, SIU_SRCR())
        self.eisr    = (0x0014, SIU_EISR())
        self.direr   = (0x0018, SIU_DIRER())
        self.dirsr   = (0x001C, SIU_DIRSR())
        self.osr     = (0x0020, SIU_OSR())
        self.orer    = (0x0024, SIU_ORER())
        self.ireer   = (0x0028, SIU_IREER())
        self.ifeer   = (0x002C, SIU_IFEER())
        self.idfr    = (0x0030, SIU_IDFR())
        self.ifir    = (0x0034, SIU_IFIR())


        # PCR (Pin Control Registers)
        # PCR registers must be initialized using the PCR_DEFAULT values because
        # not all PCR fields can be modified for all pins.
        self.pcr     = (0x0040, VArray([SIU_PCRn() if c is None else SIU_PCRn(**c) for c in self._pcr_defaults]))

        # Legacy GPDO
        self.gpdo    = (0x0600, VArray([SIU_GPDOn() for i in range(NUM_GPDIO_PINS)]))

        # Legacy GPDI (only first 256 pins)
        self.gpdi    = (0x0800, VArray([SIU_GPDIn() for i in range(NUM_GPDIO_PINS // 2)]))

        self.eiisr   = (0x0904, SIU_EIISR())
        self.disr    = (0x0908, SIU_DISR())
        self.isel4   = (0x0910, SIU_ISEL4())
        self.isel5   = (0x0914, SIU_ISEL5())
        self.isel6   = (0x0918, SIU_ISEL6())
        self.isel7   = (0x091C, SIU_ISEL7())
        self.isel8   = (0x0920, SIU_ISEL8())
        self.isel9   = (0x0924, SIU_ISEL9())
        self.decfil1 = (0x0928, SIU_DECFIL())
        self.decfil2 = (0x092C, SIU_DECFIL())
        self.ccr     = (0x0980, SIU_CCR())
        self.eccr    = (0x0984, SIU_ECCR())
        self.cbrh    = (0x0990, SIU_CBRH())
        self.cbrl    = (0x0994, SIU_CBRL())
        self.sysdiv  = (0x09A0, SIU_SYSDIV())
        self.hlt     = (0x09A4, SIU_HLT())
        self.hltack  = (0x09A8, SIU_HLTACK())

        # Parallel GPDO
        # 4 bytes for every 32 pins
        self.pgpdo   = (0x0C00, VArray([SIU_PGPDOn() for i in range(NUM_GPDIO_PINS // 32)]))

        # Parallel GPDI
        # 4 bytes for every 32 pins
        self.pgpdi   = (0x0C40, VArray([SIU_PGPDIn() for i in range(NUM_GPDIO_PINS // 32)]))

        # Masked Parallel GPDO
        # 2 bytes of mask and 2 bytes of data for every 16 pins
        self.mpgpdo  = (0x0C80, VArray([SIU_MPGPDOn() for i in range(NUM_GPDIO_PINS // 16)]))

        # 0x0D00-0x0E00 is unimplemented (related to DSPI or eTPU functionality)
        # 0x100 bytes / 32 bits per register = 64 placeholder registers
        self.tbd     = (0x0D00, VArray([PlaceholderRegister(32) for i in range(64)]))

        # Legacy GPDI (full range)
        self.gpdi_full = (0x0E00, VArray([SIU_GPDIn() for i in range(NUM_GPDIO_PINS)]))

    def reset(self, emu):
        # TODO: Will probably need to set some other register values based on
        # the reset reason, like watchdog and such

        # Read the current state of SRCR[SER]
        ser_value = self.srcr.ser

        super().reset(emu)

        # Change the default value of the RSR[SERF] flag to indicate if a reset
        # has happened because the SRCR[SER] bit was set or not
        self.rsr.vsOverrideValue('serf', ser_value)


# Cache the byte offset, bit offset, and pin mask values for each pin.
# This is used for mapping the 1 bit legacy GPIO read/writes onto the
# newer parallel GPIO read/writes that are 32-bits wide.
#
# Also, the bit shift and mask for the parallel GPIO reads/writes are
# ordered with lower "pins" at more significant bit positions. The bit
# shift value and bitmask here reflect this.
_gpio_offsets = tuple((
    p // 32,             # Byte Offset (0 to 15)
    31 - (p % 32),       # Bit Position (in sane numbers, not PPC numbers)
    1 << (31 - (p % 32)) # Bit Mask
) for p in range(NUM_GPDIO_PINS))

# Cache the supported read/write struct formats based on the current
# endian-ness of the emulator and the size of the read/write happening.
_gpio_fmts = (
    # LE
    (None, '<B', '<BB', None, '<BBBB', None, None, None, '<BBBBBBBB'),
    # BE
    (None, '>B', '>BB', None, '>BBBB', None, None, None, '>BBBBBBBB'),
)

_pgpio_fmts = (
    # LE
    (None, None, None, None, '<I', None, None, None, '<II'),
    # BE
    (None, None, None, None, '>I', None, None, None, '>II'),
)


class SIU(MMIOPeripheral):
    '''
    System Integration Unit

    Ties a number of things together:
    * MCU reset configuration
        Controls the external pin boot logic

    * System reset operation
    * Pad Configuration
    * External Interrupts
    * GPIO
    * Internal Peripheral MUXing
    * GPDI/GPDO I/Os of the DSPi modules


    INPUTS:
        Monitors internal and External RESET sources

    OUTPUTS:
        Drives the external nRSTOUT pin

    '''
    def __init__(self, emu, mmio_addr):
        super().__init__(emu, 'SIU', mmio_addr, 0x4000)

        # Create attributes for boot parameter settings (PLLCFG, etc.)
        self.pllcfg = self._config.pllcfg
        self.bootcfg = self._config.bootcfg
        self.wkpcfg = self._config.wkpcfg

        # Create the register set now
        self.registers = SIU_REGISTERS(wkpcfg=self.wkpcfg, bootcfg=self.bootcfg)

        # GPIO 75-82 are available to be used as GPIO pins only when the NDI
        # peripheral is configured to operate in Reduced-Port (or Disabled-Port)
        # mode. In that situation these pins will fall back on GPIO
        # functionality. But their GPIO function isn't configured through the
        # PCR[PA] register as normal, but rather controlled through the MCKO_EN
        # and FPM bits of the Nexus Port Configuration Register (PCR).
        #
        # Because of this situation we need a way to track the mode of valid
        # GPIO pins with a PCR[PA] field cannot be modified.
        self._gpioMode = [None for x in range(NUM_GPDIO_PINS)]

        # Input/Output masks
        self._out_mask = [0x00 for x in range(NUM_GPDIO_PINS // 32)]
        self._in_mask = [0x00 for x in range(NUM_GPDIO_PINS // 32)]

        # To keep track the value of GPDI pins being driven externally
        self._connected = [None for x in range(NUM_GPDIO_PINS)]

        # PGPDO-like packed masks and values for updating external pin values
        self._connected_value = [0 for x in range(NUM_GPDIO_PINS // 32)]
        self._connected_mask = [0 for x in range(NUM_GPDIO_PINS // 32)]

        # Pull up/down default values
        self._default_value = [0 for x in range(NUM_GPDIO_PINS // 32)]

        # Keeps track of the external pin values. Essentially a mirror of the
        # self.registers.pgpdo array, but should reflect the state of the pins
        # as measured from outside of the processor package.
        self.pin_value = [0x00 for x in range(NUM_GPDIO_PINS // 32)]

        # Restore any default GPIO connections
        # PCB connected pins are implicitly connected
        #   GPIO208 = PLLCFG0
        #   GPIO209 = PLLCFG1
        #             PLLCFG2 (pin 210, but is not GPIO capable)
        #   GPIO211 = BOOTCFG0
        #   GPIO212 = BOOTCFG1
        #   GPIO213 = WPKCFG
        #
        self.connectGPIO(208, (self.pllcfg >> 2) & 1)
        self.connectGPIO(209, (self.pllcfg >> 1) & 1)
        self.connectGPIO(210, self.pllcfg & 1)
        self.connectGPIO(211, (self.bootcfg >> 1) & 1)
        self.connectGPIO(212, self.bootcfg & 1)
        self.connectGPIO(213, self.wkpcfg)

        # The SIU peripheral generates the following output clocks based on the
        # FMPLL output:
        #   f_sys       Clock used to generate the peripheral clocks and also
        #               that runs the e200z7 core (referred to as m_clk in the
        #               e200z7 docs)
        #
        #   f_periph    Clock sent to most of the peripherals
        #
        #   f_cpu       Doesn't matter for our emulation maybe? but changes
        #               based on IPCLKDIV settings
        #
        #   f_etpu      Clock used to drive the eTPU "microengines"
        #
        #   f_clkout    D_CLKOUT external clock (also called EBI CAL)
        #
        #   f_engclk    Engineering clock (EGNCLK output signal)
        #
        # The FMPLL output clock is configured and not modified, but because the
        # peripheral clocks are simple dividers an entire PLL locking procedure
        # isn't required when changing the dividers. Because of that these
        # clock outputs are implemented as functions that will calculate the
        # appropriate clock on demand, and not just static properties that are
        # set when the various clock dividers fields are modified.
        #
        # TODO: In theory by the time any of the clock values will be required
        # to drive actual time in the emulation the FMPLL clock will be locked
        # and the SIU dividers will no longer be being changed so any time
        # values read from these functions or timers started using these times
        # should be valid. The alternative is that any timers created will need
        # to get connected to clock/frequency change events. That seems unlikely
        # to be necessary.

        ########

        # When the SRCR[SSR] or SRCR[SER] fields are set to 1 that should
        # trigger a reset.
        self.registers.vsAddParseCallback('srcr', self.srcrUpdate)

        # Have the value written to CBRH/CBRL reflect in the CCR[MATCH] field
        self.registers.vsAddParseCallback('cbrh', self.checkCBRMatch)
        self.registers.vsAddParseCallback('cbrl', self.checkCBRMatch)

        # Attach a callback to the sysdiv timer so that whenever the system
        # clock divider changes the main system time frequency is updated
        self.registers.vsAddParseCallback('sysdiv', self.updateSystemFreq)

        # Attach the callback functions to handle writes that need to cause GPIO
        # value updates
        self.registers.vsAddParseCallback('by_idx_pcr', self.pcrUpdate)
        self.registers.vsAddParseCallback('by_idx_gpdo', self.gpdoUpdate)
        self.registers.vsAddParseCallback('by_idx_pgpdo', self.pgpdoUpdate)
        self.registers.vsAddParseCallback('by_idx_mpgpdo', self.mpgpdoUpdate)

    def reset(self, emu):
        """
        Return the SIU peripheral to a reset state
        """
        # Reset the peripheral registers
        super().reset(emu)

        # Set the system frequency now based on the default register values.
        self.updateSystemFreq()

        # Update all of the external pin values based on the GPIO configurations
        # and any externally connected pins
        for pin in range(NUM_GPDIO_PINS):
            self.updateMasksFromPCR(pin)

        # Refresh any externally connected pins
        for pin in range(len(self._connected)):
            # Just explicitly re-set the current connected value, that will
            # update the value mask
            self.setGPIO(pin, self._connected[pin])

        # Lastly update all of the input and output values based on the current
        # PCR configurations
        for idx in range(NUM_GPDIO_PINS // 32):
            self.refreshBlockValue(idx)

    def checkCBRMatch(self, thing):
        # TODO: Eventually this should be compared against the password values
        # in shadow flash
        if self.registers.cbrh.cmpbh == 0xFEEDFACE and self.registers.cbrl.cmpbl == 0xCAFEBEEF:
            self.registers.ccr.vsOverrideValue('match', 1)
        else:
            self.registers.ccr.vsOverrideValue('match', 0)

    def srcrUpdate(self, thing):
        if self.registers.srcr.ser or self.registers.srcr.ssr:
            raise ResetException()

    def updateSystemFreq(self, thing=None):
        logger.debug('SIU: Setting system clock to %f MHz', self.f_cpu() / 1000000)
        self.emu.setSystemFreq(self.f_cpu())

    def f_sys(self):
        if self.registers.sysdiv.bypass:
            divider = 1
        else:
            divider = (2, 4, 8, 16)[self.registers.sysdiv.sysclkdiv]
        return self.emu.fmpll.f_pll() // divider

    def updateMasksFromPCR(self, pin):
        """
        Update the various masks and cached values that are used to
        efficiently update the external pin values and input values
        when GPIO values change.
        """
        idx, _, pinmask = _gpio_offsets[pin]

        # Update the GPIO state of the pin. If the PCR[PA] field is None then
        # this cannot be set to GPIO mode through the PCR values, instead it
        # must be changed by some other peripheral.
        pcr_cfg = self.registers._pcr_defaults[pin]
        pcr = self.registers.pcr[pin]
        if pcr_cfg and pcr_cfg['pa'] is not None:
            self._gpioMode[pin] = not pcr.pa

        # Update the output and input masks
        if self.isOutputPin(pin):
            self._out_mask[idx] |= pinmask
        else:
            self._out_mask[idx] &= ~pinmask

        if self.isInputPin(pin):
            self._in_mask[idx] |= pinmask
        else:
            self._in_mask[idx] &= ~pinmask

        # Update the cached default values for this pin
        if pcr.wpe and pcr.wps:
            self._default_value[idx] |= pinmask
        else:
            self._default_value[idx] &= ~pinmask

    def pcrUpdate(self, thing, idx, size):
        """
        Update the GPIO(s) that correspond to the PCR that was just set (the
        PCR index == the GPIO pin number)
        """
        self.updateMasksFromPCR(idx)
        self.refreshPinValue(idx)

    def gpdoUpdate(self, thing, idx, size):
        """
        Update the output value for then pin controlled by the specified GPDO register
        """
        pin = idx
        pgpdo_idx, bitoff, pinmask = _gpio_offsets[pin]

        pgpdo_val = self.registers.pgpdo[pgpdo_idx].data
        if self.registers.gpdo[pin].pdo:
            pgpdo_val |= pinmask
        else:
            pgpdo_val &= ~pinmask

        # Update the correct PGPDO register first, then call the pgpdoUpdate()
        # function to force the rest of the actions to take place
        self.registers.pgpdo[pgpdo_idx].data = pgpdo_val
        self.refreshPinValue(pin)

    def pgpdoUpdate(self, thing, idx, size):
        """
        Update the output value for pins controlled by the specified PGPDO register
        """
        # Ensure all of the legacy GPDO values have been updated to match the
        # PGPDO value
        value = self.registers.pgpdo[idx].data
        start_pin = idx * 32
        for pin in range(start_pin, start_pin + 32):
            _, bitoff, _ = _gpio_offsets[pin]
            pin_out_val = (value >> bitoff) & 1
            self.registers.gpdo[pin].pdo = pin_out_val

        self.refreshBlockValue(idx)

    def mpgpdoUpdate(self, thing, idx, size):
        # There are 2 MPGPDO registers for every PGPDO register, 8-byte aligned
        # addresses map to the upper 15 bits of the PGPDO register, the next
        # register maps to the lower 16 bits of the PGPDO register.
        pgpdo_idx = idx // 2
        pgpdo_val = self.registers.pgpdo[pgpdo_idx].data

        # The MPGPDO registers are marked as write-only so get the value by
        # reading the _vs_value from the correct array entry.
        mask = self.registers.mpgpdo[idx]._vs_values['mask']._vs_value
        value = self.registers.mpgpdo[idx]._vs_values['data']._vs_value

        # If the MPGPDO index is even then update the upper 16 bits of the PGPDO
        if idx & 1 == 0:
            mask <<= 16
            value <<= 16

        # Make sure to keep the bits that are not in the write mask
        keep_val = pgpdo_val & ~mask
        write_val = keep_val | (value & mask)
        self.registers.pgpdo[pgpdo_idx].data = write_val

        # Ensure all of the legacy GPDO values have been updated to match the
        # PGPDO value just set. Only 16 GPDO values need updated since one
        # MPGPDO register only sets half of a PGPDO register.
        start_pin = idx * 16
        for pin in range(start_pin, start_pin + 16):
            _, bitoff, _ = _gpio_offsets[pin]
            pin_out_val = (write_val >> bitoff) & 1
            self.registers.gpdo[pin].pdo = pin_out_val

        ## Update the external pins
        self.refreshBlockValue(pgpdo_idx)

    def f_periph(self):
        # Peripheral clock is set based on the SYSDIV[IPCLKDIV] values:
        #
        # From Table 6-45. SIU_SYSDIV Bit Field Descriptions
        # (MPC5674FRM.pdf page 266)
        #
        # 00    CPU frequency is doubled (Max 264Mhz)
        #       Platform, peripheral and eTPU clocks are 1/2 of CPU frequency
        # 01    CPU and eTPU frequency is doubled (Max 200Mhz)
        #       Platform and peripheral clocks are 1/2 of CPU frequency
        # 10    Reserved
        # 11    CPU, eTPU, platform, and peripheral’s clocks all run at same
        #       speed (Max 132Mhz)
        #       Note: Refer to the MPC5674F Data Sheet for the latest frequency
        #       specifications.
        #
        # "doubled" means "not divided by 2" so a doubled clock has the
        # frequency returned by f_sys()
        divider = (2, 2, None, 2)
        freq = self.f_sys() / divider[self.registers.sysdiv.ipclkdiv]

        # Based on table in the f_periph(), 132MHz is the fastest allowed
        # peripheral clock
        if freq > 132000000.0:
            logger.warning('INVALID f_periph: %s', freq)
        return freq

    def f_cpu(self):
        # Same as in f_periph() but to create the CPU clock instead of the
        # peripheral clock
        divider = (1, 1, None, 2)
        freq = self.f_sys() / divider[self.registers.sysdiv.ipclkdiv]

        # Based on table in the f_periph(), 264MHz is the fastest allowed CPU
        # clock
        if freq > 264000000.0:
            logger.warning('INVALID f_cpu: %s', freq)
        return freq

    def f_etpu(self):
        # Same as in f_periph() but to create the eTPU clock instead of the
        # peripheral clock
        divider = (2, 1, None, 2)
        freq = self.f_sys() / divider[self.registers.sysdiv.ipclkdiv]

        # Based on table in the f_periph(), 200MHz is the fastest allowed eTPU
        # clock
        if freq > 200000000.0:
            logger.warning('INVALID f_etpu: %s', freq)
        return freq

    def f_engclk(self):
        # From Table 6-44. SIU_ECCR Bit Field Descriptions:
        # (MPC5674FRM.pdf page 264)
        #
        # ENGDIV:
        # Engineering clock frequency = f_periph / (ENGDIV × 2)
        # The maximum ENGCLK frequency is 66 MHz (132 MHz ÷ 2)
        # Note: Setting ENGDIV to 0 makes the ENGCLK frequency equal to the
        # fperiph.
        #
        # ECCS:
        # 0 The system clock is the source of the ENGCLK
        # 1 The external clock (the EXTAL frequency of the oscillator) is the
        # source of the ENGCLK
        if self.registers.eccr.ecss:
            freq = self.emu.fmpll.f_extal()
        elif self.registers.eccr.engdiv != 0:
            freq = self.f_periph() / (self.registers.eccr.engdiv * 2)
        else:
            freq = self.f_periph()

        if freq > 66000000.0:
            logger.warning('INVALID f_engclk: %s', freq)
        return freq

    def f_clkout(self):
        divider = (1, 2, 3, 4)
        freq = self.f_periph() / divider[self.registers.eccr.ebdf]

        # Note on Figure 5-1. MPC5674F Block Operating Frequency Domain Diagram:
        # (MPC5674FRM.pdf page 176)
        #
        # D_CLKOUT is not available on all packages and cannot be programmed for
        # faster than f_sys/2
        if freq > self.f_sys() // 2:
            logger.warning('INVALID f_clkout: %s', freq)
        return freq

    def isInputPin(self, pin):
        return self._gpioMode[pin] and self.registers.pcr[pin].ibe

    def isOutputPin(self, pin):
        return self._gpioMode[pin] and self.registers.pcr[pin].obe

    def refreshPinValue(self, pin):
        '''
        Ensures that all of the GPIO values match up correctly:
        - If the output buffer is enabled the external pin status is set to the
          PGPDO value (GPIO output will override "connected" values)
        - If output buffer is not enabled, the external pin value is set to
          whatever the current connected value is
        - If output buffer is not enabled, and there is no externally connected
          value the external pin value is the default pull up/down value
        - If the input buffer is enabled the PGPDI and GPDI values are set to
          the externally connected value.

        NOTE: this function operates on a just a single pin so some of the pin
        state management for packed values (such as pgpdo and pin_value) are
        less efficient than they could be possible.
        '''
        idx, bitoff, pinmask = _gpio_offsets[pin]
        pin_out_val = (self.registers.pgpdo[idx].data >> bitoff) & 1

        # The external value for a pin has the following priority levels:
        #   - Output value (if output pin)
        #   - Connected value (if connected)
        #   - default pull up/down value
        if self._out_mask[idx] & pinmask:
            value = pin_out_val
        elif self._connected_mask[idx] & pinmask:
            value = (self._connected_value[idx] >> bitoff) & 1
        else:
            value = (self._default_value[idx] >> bitoff) & 1

        if value:
            self.pin_value[idx] |= pinmask
        else:
            self.pin_value[idx] &= ~pinmask

        if self._in_mask[idx] & pinmask:
            in_value = self.registers.pgpdi[idx].data
            if value:
                in_value |= pinmask
            else:
                in_value &= ~pinmask
            self.registers.pgpdi[idx].vsOverrideValue('data', in_value)

            # Refresh the legacy GPDI registers as well
            if pin < 256:
                self.registers.gpdi[pin].vsOverrideValue('pdi', value)
            self.registers.gpdi_full[pin].vsOverrideValue('pdi', value)

    def refreshBlockValue(self, idx):
        '''
        Does the same thing as refreshPinValue(), but does it efficiently for
        a block of bit-packed GPIO values rather than a single pin.
        '''
        # Now update the external pin values. The external pin value has the
        # following priorities:
        #   - Output value (if output pin)
        #   - Connected value (if connected)
        #   - default pull up/down value

        # Start with the default values and mix in the connected values
        keep_value = self._default_value[idx] & ~self._connected_mask[idx]
        out_value = keep_value | (self._connected_value[idx] & self._connected_mask[idx])

        # Now mix in the output values
        keep_value = out_value & ~self._out_mask[idx]
        out_value = keep_value | (self.registers.pgpdo[idx].data & self._out_mask[idx])

        # Save the result
        self.pin_value[idx] = out_value

        # Update the input values for this pin range
        in_value = self.registers.pgpdi[idx].data
        keep_value = in_value & ~self._in_mask[idx]
        in_value = keep_value | (out_value & self._in_mask[idx])
        self.registers.pgpdi[idx].vsOverrideValue('data', in_value)

        # Now update the legacy GPDI values
        start_pin = idx * 32
        for pin in range(start_pin, start_pin + 32):
            _, bitoff, _ = _gpio_offsets[pin]
            pin_in_val = (in_value >> bitoff) & 1

            if pin < 256:
                self.registers.gpdi[pin].vsOverrideValue('pdi', pin_in_val)
            self.registers.gpdi_full[pin].vsOverrideValue('pdi', pin_in_val)

    def connectGPIO(self, pin, val=1):
        '''
        We track connections to GPD pins, primarily to identify if the
        pull-up/down resistor is used for reading GPDIs.  This tells the SIU
        to use the pin setting, rather than the default value.
        '''
        self.setGPIO(pin, int(val))

    def disconnectGPIO(self, pin):
        '''
        This tells the SIU to use the default pull up/down value, rather than
        an externally connected signal value.
        '''
        self.setGPIO(pin, None)

    def getGPIO(self, pin):
        '''
        Read the external value of a GPIO pin.
        '''
        idx, bitoff, pinmask = _gpio_offsets[pin]
        return bool(self.pin_value[idx] & pinmask)

    def setGPIO(self, pin, val):
        '''
        Write the external value of a GPIO pin.
        '''
        self._connected[pin] = val

        # Update the packed connected value and mask
        idx, _, pinmask = _gpio_offsets[pin]

        if val is not None:
            self._connected_mask[idx] |= pinmask
            if self._connected[pin]:
                self._connected_value[idx] |= pinmask
            else:
                self._connected_value[idx] &= ~pinmask
        else:
            self._connected_mask[idx] &= ~pinmask
            self._connected_value[idx] &= ~pinmask

        self.refreshPinValue(pin)
