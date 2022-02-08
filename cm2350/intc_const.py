INTC_STATE_NORMAL = 0
INTC_STATE_NONCRIT = 1
INTC_STATE_GUEST = 2
INTC_STATE_CRIT = 3
INTC_STATE_DEBUG = 4
INTC_STATE_MACHINECHECK = 5

EXC_RESET               = -1
EXC_CRITICAL_INPUT      = 0
EXC_MACHINE_CHECK       = 1
EXC_MACHINE_CHECK_NMI   = 1
EXC_DATA_STORAGE        = 2
EXC_INSTR_STORAGE       = 3
EXC_EXTERNAL_INPUT      = 4
EXC_ALIGNMENT           = 5
EXC_PROGRAM             = 6
EXC_FLOAT_UNAVAILABLE   = 7
EXC_SYSTEM_CALL         = 8
EXC_AP_UNAVAILABLE      = 9
EXC_DECREMENTER         = 10
EXC_FIXED_TIMER_INTERVAL= 11
EXC_WATCHDOG_TIMER      = 12
EXC_DATA_TLB_ERROR      = 13
EXC_INSTR_TLB_ERROR     = 14
EXC_DEBUG               = 15
# 16-31 are reserved
EXC_SPE_EFPU_UNAVAILABLE= 32
EXC_EFPU_DATA           = 33
EXC_EFPU_ROUND          = 34
EXC_PERFORMANCE         = 35

# Following IVOR registers not supported on the current target

# E.PC (embedded program control)
EXC_DOORBELL            = 36
EXC_DOORBELL_CRITICAL   = 37

# E.HV (embedded hypervisor)
EXC_GUEST_DOORBELL      = 38
EXC_GUEST_DOORBELL_CRITICAL = 39
EXC_HYPERCALL           = 40
EXC_HYPERPRIV           = 41

# E.HV.LRAT (embedded hypervisor logical to real address translation)
EXC_LRAT_ERROR          = 42

# MPC5674F INTC
MCR_HVEN = 0
MCR_VTES = 5

MCR_HVEN_MASK   = 1 << MCR_HVEN
MCR_VTES_MASK   = 1 << MCR_VTES

MMD_MCR = 0
MMD_CPR = 2
MMD_IACKR = 4
