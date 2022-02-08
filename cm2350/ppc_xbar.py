import enum


__all__  = [
    'XBAR_MASTER',
    'XBAR_PORT',
    'XBAR_SLAVE',
]


class XBAR_MASTER(enum.IntEnum):
    CORE0       = 0
    RESERVED    = 3
    EDMA_A      = 4
    EDMA_B      = 5
    FLEXRAY     = 6
    NEXUS3      = 8


class XBAR_PORT(enum.IntEnum):
    CORE0_INSTR = 0  # CPU Instructions
    CORE0_DATA  = 1  # CORE0 Data or NEXUS3 access
    EDMA_A      = 4
    EDMA_B      = 5
    FLEXRAY     = 6
    RESERVED    = 7


class XBAR_SLAVE(enum.IntEnum):
    FLASH       = 0
    EBI         = 1
    RAM         = 2
    PBRIDGE_A   = 6
    PBRIDGE_B   = 7
