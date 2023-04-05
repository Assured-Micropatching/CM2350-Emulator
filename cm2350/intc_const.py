import enum
import envi.archs.ppc.regs as eapr

# Useful as a constant but we don't want it to be detected as a valid interrupt
# level.
INTC_LEVEL_NONE = 100

# TODO: It appears the processor specific priority list (for the e200z7) differs
# from the EREF standard, looks like we may need to construct this list
# dynamically
class INTC_LEVEL(enum.IntEnum):
    # List these in decending priority to make it easier to get the correct
    # sorted priority
    RESET                = 0
    MACHINE_CHECK        = 1
    GUEST                = 2   # unused
    DEBUG                = 3
    CRITICAL_INPUT       = 4
    WATCHDOG_TIMER       = 5
    EXTERNAL_INPUT       = 6
    FIXED_INTERVAL_TIMER = 7
    DECREMENTER          = 8
    PERFORMANCE          = 9
    DEBUG_INSTR_COMPARE  = 10
    INSTR_TLB_ERROR      = 11
    INSTR_STORAGE        = 12
    PROGRAM              = 13
    PROGRAM_PRIV         = 14
    APU_UNAVAILABLE      = 15
    PROGRAM_UNIMPL       = 16
    DEBUG_BRANCH         = 17
    SYSTEM_CALL          = 18  # Also TRAP, and ROUNDING
    ALIGNMENT            = 19
    DEBUG_WITH_DTLB_DSI  = 20
    DATA_TLB_ERROR       = 21
    DATA_STORAGE         = 22
    ALIGNMENT_ACCESS     = 23
    DEBUG_INT            = 24
    DEBUG_DATA_COMPARE   = 25
    DEBUG_INSTR_COMPLETE = 26

    # Unused by e200z7, some of these overlap with the e200z7 priorities so fake
    # values are given.
    FPU_UNAVAILABLE      = 27  # 12
    LRAT_ERROR           = 28  # 20

    PROCESSOR_DOORBELL   = 32
    GUEST_DOORBELL       = 33

EXC_RESET                = None
EXC_CRITICAL_INPUT       = eapr.REG_IVOR0
EXC_MACHINE_CHECK        = eapr.REG_IVOR1
EXC_MACHINE_CHECK_NMI    = eapr.REG_IVOR1
EXC_DATA_STORAGE         = eapr.REG_IVOR2
EXC_INSTR_STORAGE        = eapr.REG_IVOR3
EXC_EXTERNAL_INPUT       = eapr.REG_IVOR4
EXC_ALIGNMENT            = eapr.REG_IVOR5
EXC_PROGRAM              = eapr.REG_IVOR6
EXC_FLOAT_UNAVAILABLE    = eapr.REG_IVOR7
EXC_SYSTEM_CALL          = eapr.REG_IVOR8
EXC_APU_UNAVAILABLE      = eapr.REG_IVOR9
EXC_DECREMENTER          = eapr.REG_IVOR10
EXC_FIXED_INTERVAL_TIMER = eapr.REG_IVOR11
EXC_WATCHDOG_TIMER       = eapr.REG_IVOR12
EXC_DATA_TLB_ERROR       = eapr.REG_IVOR13
EXC_INSTR_TLB_ERROR      = eapr.REG_IVOR14
EXC_DEBUG                = eapr.REG_IVOR15
# 16-31 are reserved
EXC_SPE_EFPU_UNAVAILABLE = eapr.REG_IVOR32
EXC_EFPU_DATA            = eapr.REG_IVOR33
EXC_EFPU_ROUND           = eapr.REG_IVOR34
EXC_PERFORMANCE          = eapr.REG_IVOR35

# Following IVOR registers not supported on the current target

# E.PC (embedded program control)
EXC_DOORBELL            = eapr.REG_IVOR36
EXC_DOORBELL_CRITICAL   = eapr.REG_IVOR37

# E.HV (embedded hypervisor)
EXC_GUEST_DOORBELL      = eapr.REG_IVOR38
EXC_GUEST_DOORBELL_CRITICAL = eapr.REG_IVOR39
EXC_HYPERCALL           = eapr.REG_IVOR40
EXC_HYPERPRIV           = eapr.REG_IVOR41

# E.HV.LRAT (embedded hypervisor logical to real address translation)
EXC_LRAT_ERROR          = eapr.REG_IVOR42

# MPC5674F INTC
MCR_HVEN = 0
MCR_VTES = 5

MCR_HVEN_MASK   = 1 << MCR_HVEN
MCR_VTES_MASK   = 1 << MCR_VTES

MMD_MCR = 0
MMD_CPR = 2
MMD_IACKR = 4


class ResetSource(enum.Enum):
    POWER_ON            = enum.auto()
    EXTERNAL            = enum.auto()
    SOFTWARE_SYSTEM     = enum.auto()
    LOSS_OF_CLOCK       = enum.auto()
    LOSS_OF_LOCK        = enum.auto()
    CORE_WATCHDOG       = enum.auto()  # MCU watchdog
    DEBUG               = enum.auto()
    WATCHDOG            = enum.auto()  # SWT peripheral
    SOFTWARE_EXTERNAL   = enum.auto()
