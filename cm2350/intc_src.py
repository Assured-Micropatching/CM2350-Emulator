import enum


__all__ = [
    'INTC_SRC',
    'INTC_EVENT',
    'DMA_REQUEST',
    'INTC_EVENT_MAP',
]


class INTC_SRC(enum.IntEnum):
    """
    Valid peripheral interrupt sources (external interrupts) for the MPC5674
    """
    INTC_SW_0               = 0     # INTC_SSCIR0[CLR0]
    INTC_SW_1               = 1     # INTC_SSCIR1[CLR1]
    INTC_SW_2               = 2     # INTC_SSCIR2[CLR2]
    INTC_SW_3               = 3     # INTC_SSCIR3[CLR3]
    INTC_SW_4               = 4     # INTC_SSCIR4[CLR4]
    INTC_SW_5               = 5     # INTC_SSCIR5[CLR5]
    INTC_SW_6               = 6     # INTC_SSCIR6[CLR6]
    INTC_SW_7               = 7     # INTC_SSCIR7[CLR7]
    SWT                     = 8     # ECSM_SWTIR[SWTIC] ECSM software wdt?
                                    #    probably a documentation error.
    ECSM                    = 9     # ECSM_ESR[RNCE], ECSM_ESR[FNCE]
    EDMA_A_ERR              = 10    # EDMA_ERL[ERR31:ERR0]
    EDMA_A_IRQ0             = 11    # EDMA_IRQRL[INT0]
    EDMA_A_IRQ1             = 12    # EDMA_IRQRL[INT1]
    EDMA_A_IRQ2             = 13    # EDMA_IRQRL[INT2]
    EDMA_A_IRQ3             = 14    # EDMA_IRQRL[INT3]
    EDMA_A_IRQ4             = 15    # EDMA_IRQRL[INT4]
    EDMA_A_IRQ5             = 16    # EDMA_IRQRL[INT5]
    EDMA_A_IRQ6             = 17    # EDMA_IRQRL[INT6]
    EDMA_A_IRQ7             = 18    # EDMA_IRQRL[INT7]
    EDMA_A_IRQ8             = 19    # EDMA_IRQRL[INT8]
    EDMA_A_IRQ9             = 20    # EDMA_IRQRL[INT9]
    EDMA_A_IRQ10            = 21    # EDMA_IRQRL[INT10]
    EDMA_A_IRQ11            = 22    # EDMA_IRQRL[INT11]
    EDMA_A_IRQ12            = 23    # EDMA_IRQRL[INT12]
    EDMA_A_IRQ13            = 24    # EDMA_IRQRL[INT13]
    EDMA_A_IRQ14            = 25    # EDMA_IRQRL[INT14]
    EDMA_A_IRQ15            = 26    # EDMA_IRQRL[INT15]
    EDMA_A_IRQ16            = 27    # EDMA_IRQRL[INT16]
    EDMA_A_IRQ17            = 28    # EDMA_IRQRL[INT17]
    EDMA_A_IRQ18            = 29    # EDMA_IRQRL[INT18]
    EDMA_A_IRQ19            = 30    # EDMA_IRQRL[INT19]
    EDMA_A_IRQ20            = 31    # EDMA_IRQRL[INT20]
    EDMA_A_IRQ21            = 32    # EDMA_IRQRL[INT21]
    EDMA_A_IRQ22            = 33    # EDMA_IRQRL[INT22]
    EDMA_A_IRQ23            = 34    # EDMA_IRQRL[INT23]
    EDMA_A_IRQ24            = 35    # EDMA_IRQRL[INT24]
    EDMA_A_IRQ25            = 36    # EDMA_IRQRL[INT25]
    EDMA_A_IRQ26            = 37    # EDMA_IRQRL[INT26]
    EDMA_A_IRQ27            = 38    # EDMA_IRQRL[INT27]
    EDMA_A_IRQ28            = 39    # EDMA_IRQRL[INT28]
    EDMA_A_IRQ29            = 40    # EDMA_IRQRL[INT29]
    EDMA_A_IRQ30            = 41    # EDMA_IRQRL[INT30]
    EDMA_A_IRQ31            = 42    # EDMA_IRQRL[INT31]
    FMPLL_LOC               = 43    # FMPLL_SYNSR[LOCF]
    FMPLL_LOL               = 44    # FMPLL_SYNSR[LOLF]
    SIU_OSR                 = 45    # SIU_OSR[OVF15:OVF0]
    SIU_EISR0               = 46    # SIU_EISR[EIF0]
    SIU_EISR1               = 47    # SIU_EISR[EIF1]
    SIU_EISR2               = 48    # SIU_EISR[EIF2]
    SIU_EISR3               = 49    # SIU_EISR[EIF3]
    SIU_EISR4_15            = 50    # SIU_EISR[EIF15:EIF4]
    EMIOS_GFR0              = 51    # EMIOS_GFR[F0]
    EMIOS_GFR1              = 52    # EMIOS_GFR[F1]
    EMIOS_GFR2              = 53    # EMIOS_GFR[F2]
    EMIOS_GFR3              = 54    # EMIOS_GFR[F3]
    EMIOS_GFR4              = 55    # EMIOS_GFR[F4]
    EMIOS_GFR5              = 56    # EMIOS_GFR[F5]
    EMIOS_GFR6              = 57    # EMIOS_GFR[F6]
    EMIOS_GFR7              = 58    # EMIOS_GFR[F7]
    EMIOS_GFR8              = 59    # EMIOS_GFR[F8]
    EMIOS_GFR9              = 60    # EMIOS_GFR[F9]
    EMIOS_GFR10             = 61    # EMIOS_GFR[F10]
    EMIOS_GFR11             = 62    # EMIOS_GFR[F11]
    EMIOS_GFR12             = 63    # EMIOS_GFR[F12]
    EMIOS_GFR13             = 64    # EMIOS_GFR[F13]
    EMIOS_GFR14             = 65    # EMIOS_GFR[F14]
    EMIOS_GFR15             = 66    # EMIOS_GFR[F15]
    ETPU_MCR                = 67    # ETPU_MCR[MGEA, MGEB, MGEB, ILFA, ILFB, SCMMISF]
    ETPU_CISR_A0            = 68    # ETPU_CISR_A[CIS0]
    ETPU_CISR_A1            = 69    # ETPU_CISR_A[CIS1]
    ETPU_CISR_A2            = 70    # ETPU_CISR_A[CIS2]
    ETPU_CISR_A3            = 71    # ETPU_CISR_A[CIS3]
    ETPU_CISR_A4            = 72    # ETPU_CISR_A[CIS4]
    ETPU_CISR_A5            = 73    # ETPU_CISR_A[CIS5]
    ETPU_CISR_A6            = 74    # ETPU_CISR_A[CIS6]
    ETPU_CISR_A7            = 75    # ETPU_CISR_A[CIS7]
    ETPU_CISR_A8            = 76    # ETPU_CISR_A[CIS8]
    ETPU_CISR_A9            = 77    # ETPU_CISR_A[CIS9]
    ETPU_CISR_A10           = 78    # ETPU_CISR_A[CIS10]
    ETPU_CISR_A11           = 79    # ETPU_CISR_A[CIS11]
    ETPU_CISR_A12           = 80    # ETPU_CISR_A[CIS12]
    ETPU_CISR_A13           = 81    # ETPU_CISR_A[CIS13]
    ETPU_CISR_A14           = 82    # ETPU_CISR_A[CIS14]
    ETPU_CISR_A15           = 83    # ETPU_CISR_A[CIS15]
    ETPU_CISR_A16           = 84    # ETPU_CISR_A[CIS16]
    ETPU_CISR_A17           = 85    # ETPU_CISR_A[CIS17]
    ETPU_CISR_A18           = 86    # ETPU_CISR_A[CIS18]
    ETPU_CISR_A19           = 87    # ETPU_CISR_A[CIS19]
    ETPU_CISR_A20           = 88    # ETPU_CISR_A[CIS20]
    ETPU_CISR_A21           = 89    # ETPU_CISR_A[CIS21]
    ETPU_CISR_A22           = 90    # ETPU_CISR_A[CIS22]
    ETPU_CISR_A23           = 91    # ETPU_CISR_A[CIS23]
    ETPU_CISR_A24           = 92    # ETPU_CISR_A[CIS24]
    ETPU_CISR_A25           = 93    # ETPU_CISR_A[CIS25]
    ETPU_CISR_A26           = 94    # ETPU_CISR_A[CIS26]
    ETPU_CISR_A27           = 95    # ETPU_CISR_A[CIS27]
    ETPU_CISR_A28           = 96    # ETPU_CISR_A[CIS28]
    ETPU_CISR_A29           = 97    # ETPU_CISR_A[CIS29]
    ETPU_CISR_A30           = 98    # ETPU_CISR_A[CIS30]
    ETPU_CISR_A31           = 99    # ETPU_CISR_A[CIS31]
    EQADC_A_OVERRUN         = 100   # EQADC_FISRx[TORF, RFOF, CFUF]
    EQADC_A_FISR0_NCF       = 101   # EQADC_FISR0[NCF]
    EQADC_A_FISR0_PF        = 102   # EQADC_FISR0[PF]
    EQADC_A_FISR0_EOQF      = 103   # EQADC_FISR0[EOQF]
    EQADC_A_FISR0_CFFF      = 104   # EQADC_FISR0[CFFF]
    EQADC_A_FISR0_RFDF      = 105   # EQADC_FISR0[RFDF]
    EQADC_A_FISR1_NCF       = 106   # EQADC_FISR1[NCF]
    EQADC_A_FISR1_PF        = 107   # EQADC_FISR1[PF]
    EQADC_A_FISR1_EOQF      = 108   # EQADC_FISR1[EOQF]
    EQADC_A_FISR1_CFFF      = 109   # EQADC_FISR1[CFFF]
    EQADC_A_FISR1_RFDF      = 110   # EQADC_FISR1[RFDF]
    EQADC_A_FISR2_NCF       = 111   # EQADC_FISR2[NCF]
    EQADC_A_FISR2_PF        = 112   # EQADC_FISR2[PF]
    EQADC_A_FISR2_EOQF      = 113   # EQADC_FISR2[EOQF]
    EQADC_A_FISR2_CFFF      = 114   # EQADC_FISR2[CFFF]
    EQADC_A_FISR2_RFDF      = 115   # EQADC_FISR2[RFDF]
    EQADC_A_FISR3_NCF       = 116   # EQADC_FISR3[NCF]
    EQADC_A_FISR3_PF        = 117   # EQADC_FISR3[PF]
    EQADC_A_FISR3_EOQF      = 118   # EQADC_FISR3[EOQF]
    EQADC_A_FISR3_CFFF      = 119   # EQADC_FISR3[CFFF]
    EQADC_A_FISR3_RFDF      = 120   # EQADC_FISR3[RFDF]
    EQADC_A_FISR4_NCF       = 121   # EQADC_FISR4[NCF]
    EQADC_A_FISR4_PF        = 122   # EQADC_FISR4[PF]
    EQADC_A_FISR4_EOQF      = 123   # EQADC_FISR4[EOQF]
    EQADC_A_FISR4_CFFF      = 124   # EQADC_FISR4[CFFF]
    EQADC_A_FISR4_RFDF      = 125   # EQADC_FISR4[RFDF]
    EQADC_A_FISR5_NCF       = 126   # EQADC_FISR5[NCF]
    EQADC_A_FISR5_PF        = 127   # EQADC_FISR5[PF]
    EQADC_A_FISR5_EOQF      = 128   # EQADC_FISR5[EOQF]
    EQADC_A_FISR5_CFFF      = 129   # EQADC_FISR5[CFFF]
    EQADC_A_FISR5_RFDF      = 130   # EQADC_FISR5[RFDF]
    DSPI_B_OVERRUN          = 131   # DSPI_BSR[TFUF, RFOF]
    DSPI_B_TX_EOQ           = 132   # DSPI_BSR[EOQF]
    DSPI_B_TX_FILL          = 133   # DSPI_BSR[TFFF]
    DSPI_B_TX_CMPLT         = 134   # DSPI_BSR[TCF]
    DSPI_B_RX_DRAIN         = 135   # DSPI_BSR[RFDF]
    DSPI_C_OVERRUN          = 136   # DSPI_CSR[TFUF, RFOF]
    DSPI_C_TX_EOQ           = 137   # DSPI_CSR[EOQF]
    DSPI_C_TX_FILL          = 138   # DSPI_CSR[TFFF]
    DSPI_C_TX_CMPLT         = 139   # DSPI_CSR[TCF]
    DSPI_C_RX_DRAIN         = 140   # DSPI_CSR[RFDF]
    DSPI_D_OVERRUN          = 141   # DSPI_DSR[TFUF, RFOF]
    DSPI_D_TX_EOQ           = 142   # DSPI_DSR[EOQF]
    DSPI_D_TX_FILL          = 143   # DSPI_DSR[TFFF]
    DSPI_D_TX_CMPLT         = 144   # DSPI_DSR[TCF]
    DSPI_D_RX_DRAIN         = 145   # DSPI_DSR[RFDF]
    ESCIA                   = 146   # ESCIA_IFSR1[*], ESCIA_IFSR2[*]
    ESCIB                   = 149   # ESCIB_IFSR1[*], ESCIB_IFSR2[*]
    CANA_BUS                = 152   # CANA_ESR[BOFF_INT, TWRN_INT, RWRN_INT]
    CANA_ERR                = 153   # CANA_ESR[ERR_INT]
    CANA_MB0                = 155   # CANA_IFRL[BUF0]
    CANA_MB1                = 156   # CANA_IFRL[BUF1]
    CANA_MB2                = 157   # CANA_IFRL[BUF2]
    CANA_MB3                = 158   # CANA_IFRL[BUF3]
    CANA_MB4                = 159   # CANA_IFRL[BUF4]
    CANA_MB5                = 160   # CANA_IFRL[BUF5]
    CANA_MB6                = 161   # CANA_IFRL[BUF6]
    CANA_MB7                = 162   # CANA_IFRL[BUF7]
    CANA_MB8                = 163   # CANA_IFRL[BUF8]
    CANA_MB9                = 164   # CANA_IFRL[BUF9]
    CANA_MB10               = 165   # CANA_IFRL[BUF10]
    CANA_MB11               = 166   # CANA_IFRL[BUF11]
    CANA_MB12               = 167   # CANA_IFRL[BUF12]
    CANA_MB13               = 168   # CANA_IFRL[BUF13]
    CANA_MB14               = 169   # CANA_IFRL[BUF14]
    CANA_MB15               = 170   # CANA_IFRL[BUF15]
    CANA_MB16_31            = 171   # CANA_IFRL[BUF31:BUF16]
    CANA_MB32_63            = 172   # CANA_IFRH[BUF63:BUF32]
    CANC_BUS                = 173   # CANC_ESR[BOFF_INT, TWRN_INT, RWRN_INT]
    CANC_ERR                = 174   # CANC_ESR[ERR_INT]
    CANC_MB0                = 176   # CANC_IFRL[BUF0]
    CANC_MB1                = 177   # CANC_IFRL[BUF1]
    CANC_MB2                = 178   # CANC_IFRL[BUF2]
    CANC_MB3                = 179   # CANC_IFRL[BUF3]
    CANC_MB4                = 180   # CANC_IFRL[BUF4]
    CANC_MB5                = 181   # CANC_IFRL[BUF5]
    CANC_MB6                = 182   # CANC_IFRL[BUF6]
    CANC_MB7                = 183   # CANC_IFRL[BUF7]
    CANC_MB8                = 184   # CANC_IFRL[BUF8]
    CANC_MB9                = 185   # CANC_IFRL[BUF9]
    CANC_MB10               = 186   # CANC_IFRL[BUF10]
    CANC_MB11               = 187   # CANC_IFRL[BUF11]
    CANC_MB12               = 188   # CANC_IFRL[BUF12]
    CANC_MB13               = 189   # CANC_IFRL[BUF13]
    CANC_MB14               = 190   # CANC_IFRL[BUF14]
    CANC_MB15               = 191   # CANC_IFRL[BUF15]
    CANC_MB16_31            = 192   # CANC_IFRL[BUF31:BUF16]
    CANC_MB32_63            = 193   # CANC_IFRH[BUF63:BUF32]
    DEC_A_FILL              = 197   # DEC_A (fill)
    DEC_A_DRAIN             = 198   # DEC_A (drain)
    DEC_A_ERROR             = 199   # DEC_A (error)
    STM0                    = 200   # STM[0]
    STM1_3                  = 201   # STM[1:3]
    EMIOS_GFR16             = 202   # EMIOS_GFR[F16]
    EMIOS_GFR17             = 203   # EMIOS_GFR[F17]
    EMIOS_GFR18             = 204   # EMIOS_GFR[F18]
    EMIOS_GFR19             = 205   # EMIOS_GFR[F19]
    EMIOS_GFR20             = 206   # EMIOS_GFR[F20]
    EMIOS_GFR21             = 207   # EMIOS_GFR[F21]
    EMIOS_GFR22             = 208   # EMIOS_GFR[F22]
    EMIOS_GFR23             = 209   # EMIOS_GFR[F23]
    EDMA_A_ERR32_63         = 210   # EDMA_ERL[ERR63:ERR32]
    EDMA_A_IRQ32            = 211   # EDMA_IRQRH[INT32]
    EDMA_A_IRQ33            = 212   # EDMA_IRQRH[INT33]
    EDMA_A_IRQ34            = 213   # EDMA_IRQRH[INT34]
    EDMA_A_IRQ35            = 214   # EDMA_IRQRH[INT35]
    EDMA_A_IRQ36            = 215   # EDMA_IRQRH[INT36]
    EDMA_A_IRQ37            = 216   # EDMA_IRQRH[INT37]
    EDMA_A_IRQ38            = 217   # EDMA_IRQRH[INT38]
    EDMA_A_IRQ39            = 218   # EDMA_IRQRH[INT39]
    EDMA_A_IRQ40            = 219   # EDMA_IRQRH[INT40]
    EDMA_A_IRQ41            = 220   # EDMA_IRQRH[INT41]
    EDMA_A_IRQ42            = 221   # EDMA_IRQRH[INT42]
    EDMA_A_IRQ43            = 222   # EDMA_IRQRH[INT43]
    EDMA_A_IRQ44            = 223   # EDMA_IRQRH[INT44]
    EDMA_A_IRQ45            = 224   # EDMA_IRQRH[INT45]
    EDMA_A_IRQ46            = 225   # EDMA_IRQRH[INT46]
    EDMA_A_IRQ47            = 226   # EDMA_IRQRH[INT47]
    EDMA_A_IRQ48            = 227   # EDMA_IRQRH[INT48]
    EDMA_A_IRQ49            = 228   # EDMA_IRQRH[INT49]
    EDMA_A_IRQ50            = 229   # EDMA_IRQRH[INT50]
    EDMA_A_IRQ51            = 230   # EDMA_IRQRH[INT51]
    EDMA_A_IRQ52            = 231   # EDMA_IRQRH[INT52]
    EDMA_A_IRQ53            = 232   # EDMA_IRQRH[INT53]
    EDMA_A_IRQ54            = 233   # EDMA_IRQRH[INT54]
    EDMA_A_IRQ55            = 234   # EDMA_IRQRH[INT55]
    EDMA_A_IRQ56            = 235   # EDMA_IRQRH[INT56]
    EDMA_A_IRQ57            = 236   # EDMA_IRQRH[INT57]
    EDMA_A_IRQ58            = 237   # EDMA_IRQRH[INT58]
    EDMA_A_IRQ59            = 238   # EDMA_IRQRH[INT59]
    EDMA_A_IRQ60            = 239   # EDMA_IRQRH[INT60]
    EDMA_A_IRQ61            = 240   # EDMA_IRQRH[INT61]
    EDMA_A_IRQ62            = 241   # EDMA_IRQRH[INT62]
    EDMA_A_IRQ63            = 242   # EDMA_IRQRH[INT63]
    ETPU_CISR_B0            = 243   # ETPU_CISR_B[CIS0]
    ETPU_CISR_B1            = 244   # ETPU_CISR_B[CIS1]
    ETPU_CISR_B2            = 245   # ETPU_CISR_B[CIS2]
    ETPU_CISR_B3            = 246   # ETPU_CISR_B[CIS3]
    ETPU_CISR_B4            = 247   # ETPU_CISR_B[CIS4]
    ETPU_CISR_B5            = 248   # ETPU_CISR_B[CIS5]
    ETPU_CISR_B6            = 249   # ETPU_CISR_B[CIS6]
    ETPU_CISR_B7            = 250   # ETPU_CISR_B[CIS7]
    ETPU_CISR_B8            = 251   # ETPU_CISR_B[CIS8]
    ETPU_CISR_B9            = 252   # ETPU_CISR_B[CIS9]
    ETPU_CISR_B10           = 253   # ETPU_CISR_B[CIS10]
    ETPU_CISR_B11           = 254   # ETPU_CISR_B[CIS11]
    ETPU_CISR_B12           = 255   # ETPU_CISR_B[CIS12]
    ETPU_CISR_B13           = 256   # ETPU_CISR_B[CIS13]
    ETPU_CISR_B14           = 257   # ETPU_CISR_B[CIS14]
    ETPU_CISR_B15           = 258   # ETPU_CISR_B[CIS15]
    ETPU_CISR_B16           = 259   # ETPU_CISR_B[CIS16]
    ETPU_CISR_B17           = 260   # ETPU_CISR_B[CIS17]
    ETPU_CISR_B18           = 261   # ETPU_CISR_B[CIS18]
    ETPU_CISR_B19           = 262   # ETPU_CISR_B[CIS19]
    ETPU_CISR_B20           = 263   # ETPU_CISR_B[CIS20]
    ETPU_CISR_B21           = 264   # ETPU_CISR_B[CIS21]
    ETPU_CISR_B22           = 265   # ETPU_CISR_B[CIS22]
    ETPU_CISR_B23           = 266   # ETPU_CISR_B[CIS23]
    ETPU_CISR_B24           = 267   # ETPU_CISR_B[CIS24]
    ETPU_CISR_B25           = 268   # ETPU_CISR_B[CIS25]
    ETPU_CISR_B26           = 269   # ETPU_CISR_B[CIS26]
    ETPU_CISR_B27           = 270   # ETPU_CISR_B[CIS27]
    ETPU_CISR_B28           = 271   # ETPU_CISR_B[CIS28]
    ETPU_CISR_B29           = 272   # ETPU_CISR_B[CIS29]
    ETPU_CISR_B30           = 273   # ETPU_CISR_B[CIS30]
    ETPU_CISR_B31           = 274   # ETPU_CISR_B[CIS31]
    DSPI_A_OVERRUN          = 275   # DSPI_ASR[TFUF, RFOF]
    DSPI_A_TX_EOQ           = 276   # DSPI_ASR[EOQF]
    DSPI_A_TX_FILL          = 277   # DSPI_ASR[TFFF]
    DSPI_A_TX_CMPLT         = 278   # DSPI_ASR[TCF]
    DSPI_A_RX_DRAIN         = 279   # DSPI_ASR[RFDF]
    CANB_BUS                = 280   # CANB_ESR[BOFF_INT, TWRN_INT, RWRN_INT]
    CANB_ERR                = 281   # CANB_ESR[ERR_INT]
    CANB_MB0                = 283   # CANB_IFRL[BUF0]
    CANB_MB1                = 284   # CANB_IFRL[BUF1]
    CANB_MB2                = 285   # CANB_IFRL[BUF2]
    CANB_MB3                = 286   # CANB_IFRL[BUF3]
    CANB_MB4                = 287   # CANB_IFRL[BUF4]
    CANB_MB5                = 288   # CANB_IFRL[BUF5]
    CANB_MB6                = 289   # CANB_IFRL[BUF6]
    CANB_MB7                = 290   # CANB_IFRL[BUF7]
    CANB_MB8                = 291   # CANB_IFRL[BUF8]
    CANB_MB9                = 292   # CANB_IFRL[BUF9]
    CANB_MB10               = 293   # CANB_IFRL[BUF10]
    CANB_MB11               = 294   # CANB_IFRL[BUF11]
    CANB_MB12               = 295   # CANB_IFRL[BUF12]
    CANB_MB13               = 296   # CANB_IFRL[BUF13]
    CANB_MB14               = 297   # CANB_IFRL[BUF14]
    CANB_MB15               = 298   # CANB_IFRL[BUF15]
    CANB_MB16_31            = 299   # CANB_IFRL[BUF31:BUF16]
    CANB_MB32_63            = 300   # CANB_IFRH[BUF63:BUF32]
    PIT0                    = 301   # PIT[0]
    PIT1                    = 302   # PIT[1]
    PIT2                    = 303   # PIT[2]
    PIT3                    = 304   # PIT[3]
    RTI                     = 305   # RTI
    PMC                     = 306   # PMC
    ECC                     = 307   # ECC Correction
    CAND_BUS                = 308   # CAND_ESR[BOFF_INT, TWRN_INT, RWRN_INT]
    CAND_ERR                = 309   # CAND_ESR[ERR_INT]
    CAND_MB0                = 311   # CAND_IFRL[BUF0]
    CAND_MB1                = 312   # CAND_IFRL[BUF1]
    CAND_MB2                = 313   # CAND_IFRL[BUF2]
    CAND_MB3                = 314   # CAND_IFRL[BUF3]
    CAND_MB4                = 315   # CAND_IFRL[BUF4]
    CAND_MB5                = 316   # CAND_IFRL[BUF5]
    CAND_MB6                = 317   # CAND_IFRL[BUF6]
    CAND_MB7                = 318   # CAND_IFRL[BUF7]
    CAND_MB8                = 319   # CAND_IFRL[BUF8]
    CAND_MB9                = 320   # CAND_IFRL[BUF9]
    CAND_MB10               = 321   # CAND_IFRL[BUF10]
    CAND_MB11               = 322   # CAND_IFRL[BUF11]
    CAND_MB12               = 323   # CAND_IFRL[BUF12]
    CAND_MB13               = 324   # CAND_IFRL[BUF13]
    CAND_MB14               = 325   # CAND_IFRL[BUF14]
    CAND_MB15               = 326   # CAND_IFRL[BUF15]
    CAND_MB16_31            = 327   # CAND_IFRL[BUF31:BUF16]
    CAND_MB32_63            = 328   # CAND_IFRH[BUF63:BUF32]
    FLEXRAY_MIF             = 350   # GIFER[MIF]
    FLEXRAY_PROTO           = 351   # GIFER[PRIF]
    FLEXRAY_ERR             = 352   # GIFER[CHIF]
    FLEXRAY_WKUP            = 353   # GIFER[WUP_IF]
    FLEXRAY_B_WTRMRK        = 354   # GIFER[FBNE_F]
    FLEXRAY_A_WTRMRK        = 355   # GIFER[FANE_F]
    FLEXRAY_RX              = 356   # GIFER[RBIF]
    FLEXRAY_TX              = 357   # GIFER[TBIF]
    DEC_B_FILL              = 366   # DEC_B (fill)
    DEC_B_DRAIN             = 367   # DEC_B (drain)
    DEC_B_ERROR             = 368   # DEC_B (error)
    EQADC_B_OVERRUN         = 394   # EQADC_FISRx[TORF, RFOF, CFUF]
    EQADC_B_FISR0_NCF       = 395   # EQADC_FISR0[NCF]
    EQADC_B_FISR0_PF        = 396   # EQADC_FISR0[PF]
    EQADC_B_FISR0_EOQF      = 397   # EQADC_FISR0[EOQF]
    EQADC_B_FISR0_CFFF      = 398   # EQADC_FISR0[CFFF]
    EQADC_B_FISR0_RFDF      = 399   # EQADC_FISR0[RFDF]
    EQADC_B_FISR1_NCF       = 400   # EQADC_FISR1[NCF]
    EQADC_B_FISR1_PF        = 401   # EQADC_FISR1[PF]
    EQADC_B_FISR1_EOQF      = 402   # EQADC_FISR1[EOQF]
    EQADC_B_FISR1_CFFF      = 403   # EQADC_FISR1[CFFF]
    EQADC_B_FISR1_RFDF      = 404   # EQADC_FISR1[RFDF]
    EQADC_B_FISR2_NCF       = 405   # EQADC_FISR2[NCF]
    EQADC_B_FISR2_PF        = 406   # EQADC_FISR2[PF]
    EQADC_B_FISR2_EOQF      = 407   # EQADC_FISR2[EOQF]
    EQADC_B_FISR2_CFFF      = 408   # EQADC_FISR2[CFFF]
    EQADC_B_FISR2_RFDF      = 409   # EQADC_FISR2[RFDF]
    EQADC_B_FISR3_NCF       = 410   # EQADC_FISR3[NCF]
    EQADC_B_FISR3_PF        = 411   # EQADC_FISR3[PF]
    EQADC_B_FISR3_EOQF      = 412   # EQADC_FISR3[EOQF]
    EQADC_B_FISR3_CFFF      = 413   # EQADC_FISR3[CFFF]
    EQADC_B_FISR3_RFDF      = 414   # EQADC_FISR3[RFDF]
    EQADC_B_FISR4_NCF       = 415   # EQADC_FISR4[NCF]
    EQADC_B_FISR4_PF        = 416   # EQADC_FISR4[PF]
    EQADC_B_FISR4_EOQF      = 417   # EQADC_FISR4[EOQF]
    EQADC_B_FISR4_CFFF      = 418   # EQADC_FISR4[CFFF]
    EQADC_B_FISR4_RFDF      = 419   # EQADC_FISR4[RFDF]
    EQADC_B_FISR5_NCF       = 420   # EQADC_FISR5[NCF]
    EQADC_B_FISR5_PF        = 421   # EQADC_FISR5[PF]
    EQADC_B_FISR5_EOQF      = 422   # EQADC_FISR5[EOQF]
    EQADC_B_FISR5_CFFF      = 423   # EQADC_FISR5[CFFF]
    EQADC_B_FISR5_RFDF      = 424   # EQADC_FISR5[RFDF]
    EDMA_B_ERR              = 425   # EDMA_ERL[ERR31:ERR0]
    EDMA_B_IRQ0             = 426   # EDMA_IRQRL[INT0]
    EDMA_B_IRQ1             = 427   # EDMA_IRQRL[INT1]
    EDMA_B_IRQ2             = 428   # EDMA_IRQRL[INT2]
    EDMA_B_IRQ3             = 429   # EDMA_IRQRL[INT3]
    EDMA_B_IRQ4             = 430   # EDMA_IRQRL[INT4]
    EDMA_B_IRQ5             = 431   # EDMA_IRQRL[INT5]
    EDMA_B_IRQ6             = 432   # EDMA_IRQRL[INT6]
    EDMA_B_IRQ7             = 433   # EDMA_IRQRL[INT7]
    EDMA_B_IRQ8             = 434   # EDMA_IRQRL[INT8]
    EDMA_B_IRQ9             = 435   # EDMA_IRQRL[INT9]
    EDMA_B_IRQ10            = 436   # EDMA_IRQRL[INT10]
    EDMA_B_IRQ11            = 437   # EDMA_IRQRL[INT11]
    EDMA_B_IRQ12            = 438   # EDMA_IRQRL[INT12]
    EDMA_B_IRQ13            = 439   # EDMA_IRQRL[INT13]
    EDMA_B_IRQ14            = 440   # EDMA_IRQRL[INT14]
    EDMA_B_IRQ15            = 441   # EDMA_IRQRL[INT15]
    EDMA_B_IRQ16            = 442   # EDMA_IRQRL[INT16]
    EDMA_B_IRQ17            = 443   # EDMA_IRQRL[INT17]
    EDMA_B_IRQ18            = 444   # EDMA_IRQRL[INT18]
    EDMA_B_IRQ19            = 445   # EDMA_IRQRL[INT19]
    EDMA_B_IRQ20            = 446   # EDMA_IRQRL[INT20]
    EDMA_B_IRQ21            = 447   # EDMA_IRQRL[INT21]
    EDMA_B_IRQ22            = 448   # EDMA_IRQRL[INT22]
    EDMA_B_IRQ23            = 449   # EDMA_IRQRL[INT23]
    EDMA_B_IRQ24            = 450   # EDMA_IRQRL[INT24]
    EDMA_B_IRQ25            = 451   # EDMA_IRQRL[INT25]
    EDMA_B_IRQ26            = 452   # EDMA_IRQRL[INT26]
    EDMA_B_IRQ27            = 453   # EDMA_IRQRL[INT27]
    EDMA_B_IRQ28            = 454   # EDMA_IRQRL[INT28]
    EDMA_B_IRQ29            = 455   # EDMA_IRQRL[INT29]
    EDMA_B_IRQ30            = 456   # EDMA_IRQRL[INT30]
    EDMA_B_IRQ31            = 457   # EDMA_IRQRL[INT31]
    EMIOS_GFR24             = 459   # EMIOS_GFR[F24]
    EMIOS_GFR25             = 460   # EMIOS_GFR[F25]
    EMIOS_GFR26             = 461   # EMIOS_GFR[F26]
    EMIOS_GFR27             = 462   # EMIOS_GFR[F27]
    EMIOS_GFR28             = 463   # EMIOS_GFR[F28]
    EMIOS_GFR29             = 464   # EMIOS_GFR[F29]
    EMIOS_GFR30             = 465   # EMIOS_GFR[F30]
    EMIOS_GFR31             = 466   # EMIOS_GFR[F31]
    DEC_C_FILL              = 467   # DEC_C (fill)
    DEC_C_DRAIN             = 468   # DEC_C (drain)
    DEC_C_ERROR             = 469   # DEC_C (error)
    DEC_D_FILL              = 470   # DEC_D (fill)
    DEC_D_DRAIN             = 471   # DEC_D (drain)
    DEC_D_ERROR             = 472   # DEC_D (error)
    ESCIC                   = 473   # ESCIC_IFSR1[*], ESCIC_IFSR2[*]
    DEC_E                   = 476   # DEC_E
    DEC_F                   = 477   # DEC_F
    DEC_G                   = 478   # DEC_G
    DEC_H                   = 479   # DEC_H


class INTC_EVENT(enum.Enum):
    """
    Peripheral interrupt events. Multiple events may map to a single INTC_SRC,
    but individual DMA channels.
    """

    # SW triggered interrupts
    INTC_SW_0               = enum.auto()  # INTC_SSCIR0[CLR0]
    INTC_SW_1               = enum.auto()  # INTC_SSCIR1[CLR1]
    INTC_SW_2               = enum.auto()  # INTC_SSCIR2[CLR2]
    INTC_SW_3               = enum.auto()  # INTC_SSCIR3[CLR3]
    INTC_SW_4               = enum.auto()  # INTC_SSCIR4[CLR4]
    INTC_SW_5               = enum.auto()  # INTC_SSCIR5[CLR5]
    INTC_SW_6               = enum.auto()  # INTC_SSCIR6[CLR6]
    INTC_SW_7               = enum.auto()  # INTC_SSCIR7[CLR7]

    # SWT
    SWT                     = enum.auto()  # ECSM_SWTIR[SWTIC] ECSM sw wdt?
                                           #    probably a documentation error.

    # ECSM
    ECSM_ESR_R1BE           = enum.auto()  # ECSM_ESR[R1BE]
    ECSM_ESR_F1BE           = enum.auto()  # ECSM_ESR[F1BE]
    ECSM_ESR_RNCE           = enum.auto()  # ECSM_ESR[RNCE]
    ECSM_ESR_FNCE           = enum.auto()  # ECSM_ESR[FNCE]

    # eDMA A
    EDMA_A_ERR0             = enum.auto()  # EDMA_A_ERL[0]
    EDMA_A_ERR1             = enum.auto()  # EDMA_A_ERL[1]
    EDMA_A_ERR2             = enum.auto()  # EDMA_A_ERL[2]
    EDMA_A_ERR3             = enum.auto()  # EDMA_A_ERL[3]
    EDMA_A_ERR4             = enum.auto()  # EDMA_A_ERL[4]
    EDMA_A_ERR5             = enum.auto()  # EDMA_A_ERL[5]
    EDMA_A_ERR6             = enum.auto()  # EDMA_A_ERL[6]
    EDMA_A_ERR7             = enum.auto()  # EDMA_A_ERL[7]
    EDMA_A_ERR8             = enum.auto()  # EDMA_A_ERL[8]
    EDMA_A_ERR9             = enum.auto()  # EDMA_A_ERL[9]
    EDMA_A_ERR10            = enum.auto()  # EDMA_A_ERL[10]
    EDMA_A_ERR11            = enum.auto()  # EDMA_A_ERL[11]
    EDMA_A_ERR12            = enum.auto()  # EDMA_A_ERL[12]
    EDMA_A_ERR13            = enum.auto()  # EDMA_A_ERL[13]
    EDMA_A_ERR14            = enum.auto()  # EDMA_A_ERL[14]
    EDMA_A_ERR15            = enum.auto()  # EDMA_A_ERL[15]
    EDMA_A_ERR16            = enum.auto()  # EDMA_A_ERL[16]
    EDMA_A_ERR17            = enum.auto()  # EDMA_A_ERL[17]
    EDMA_A_ERR18            = enum.auto()  # EDMA_A_ERL[18]
    EDMA_A_ERR19            = enum.auto()  # EDMA_A_ERL[19]
    EDMA_A_ERR20            = enum.auto()  # EDMA_A_ERL[20]
    EDMA_A_ERR21            = enum.auto()  # EDMA_A_ERL[21]
    EDMA_A_ERR22            = enum.auto()  # EDMA_A_ERL[22]
    EDMA_A_ERR23            = enum.auto()  # EDMA_A_ERL[23]
    EDMA_A_ERR24            = enum.auto()  # EDMA_A_ERL[24]
    EDMA_A_ERR25            = enum.auto()  # EDMA_A_ERL[25]
    EDMA_A_ERR26            = enum.auto()  # EDMA_A_ERL[26]
    EDMA_A_ERR27            = enum.auto()  # EDMA_A_ERL[27]
    EDMA_A_ERR28            = enum.auto()  # EDMA_A_ERL[28]
    EDMA_A_ERR29            = enum.auto()  # EDMA_A_ERL[29]
    EDMA_A_ERR30            = enum.auto()  # EDMA_A_ERL[30]
    EDMA_A_ERR31            = enum.auto()  # EDMA_A_ERL[31]
    EDMA_A_ERR32            = enum.auto()  # EDMA_A_ERL[32]
    EDMA_A_ERR33            = enum.auto()  # EDMA_A_ERL[33]
    EDMA_A_ERR34            = enum.auto()  # EDMA_A_ERL[34]
    EDMA_A_ERR35            = enum.auto()  # EDMA_A_ERL[35]
    EDMA_A_ERR36            = enum.auto()  # EDMA_A_ERL[36]
    EDMA_A_ERR37            = enum.auto()  # EDMA_A_ERL[37]
    EDMA_A_ERR38            = enum.auto()  # EDMA_A_ERL[38]
    EDMA_A_ERR39            = enum.auto()  # EDMA_A_ERL[39]
    EDMA_A_ERR40            = enum.auto()  # EDMA_A_ERL[40]
    EDMA_A_ERR41            = enum.auto()  # EDMA_A_ERL[41]
    EDMA_A_ERR42            = enum.auto()  # EDMA_A_ERL[42]
    EDMA_A_ERR43            = enum.auto()  # EDMA_A_ERL[43]
    EDMA_A_ERR44            = enum.auto()  # EDMA_A_ERL[44]
    EDMA_A_ERR45            = enum.auto()  # EDMA_A_ERL[45]
    EDMA_A_ERR46            = enum.auto()  # EDMA_A_ERL[46]
    EDMA_A_ERR47            = enum.auto()  # EDMA_A_ERL[47]
    EDMA_A_ERR48            = enum.auto()  # EDMA_A_ERL[48]
    EDMA_A_ERR49            = enum.auto()  # EDMA_A_ERL[49]
    EDMA_A_ERR50            = enum.auto()  # EDMA_A_ERL[50]
    EDMA_A_ERR51            = enum.auto()  # EDMA_A_ERL[51]
    EDMA_A_ERR52            = enum.auto()  # EDMA_A_ERL[52]
    EDMA_A_ERR53            = enum.auto()  # EDMA_A_ERL[53]
    EDMA_A_ERR54            = enum.auto()  # EDMA_A_ERL[54]
    EDMA_A_ERR55            = enum.auto()  # EDMA_A_ERL[55]
    EDMA_A_ERR56            = enum.auto()  # EDMA_A_ERL[56]
    EDMA_A_ERR57            = enum.auto()  # EDMA_A_ERL[57]
    EDMA_A_ERR58            = enum.auto()  # EDMA_A_ERL[58]
    EDMA_A_ERR59            = enum.auto()  # EDMA_A_ERL[59]
    EDMA_A_ERR60            = enum.auto()  # EDMA_A_ERL[60]
    EDMA_A_ERR61            = enum.auto()  # EDMA_A_ERL[61]
    EDMA_A_ERR62            = enum.auto()  # EDMA_A_ERL[62]
    EDMA_A_ERR63            = enum.auto()  # EDMA_A_ERL[63]
    EDMA_A_IRQ0             = enum.auto()  # EDMA_A_IRQRL[INT0]
    EDMA_A_IRQ1             = enum.auto()  # EDMA_A_IRQRL[INT1]
    EDMA_A_IRQ2             = enum.auto()  # EDMA_A_IRQRL[INT2]
    EDMA_A_IRQ3             = enum.auto()  # EDMA_A_IRQRL[INT3]
    EDMA_A_IRQ4             = enum.auto()  # EDMA_A_IRQRL[INT4]
    EDMA_A_IRQ5             = enum.auto()  # EDMA_A_IRQRL[INT5]
    EDMA_A_IRQ6             = enum.auto()  # EDMA_A_IRQRL[INT6]
    EDMA_A_IRQ7             = enum.auto()  # EDMA_A_IRQRL[INT7]
    EDMA_A_IRQ8             = enum.auto()  # EDMA_A_IRQRL[INT8]
    EDMA_A_IRQ9             = enum.auto()  # EDMA_A_IRQRL[INT9]
    EDMA_A_IRQ10            = enum.auto()  # EDMA_A_IRQRL[INT10]
    EDMA_A_IRQ11            = enum.auto()  # EDMA_A_IRQRL[INT11]
    EDMA_A_IRQ12            = enum.auto()  # EDMA_A_IRQRL[INT12]
    EDMA_A_IRQ13            = enum.auto()  # EDMA_A_IRQRL[INT13]
    EDMA_A_IRQ14            = enum.auto()  # EDMA_A_IRQRL[INT14]
    EDMA_A_IRQ15            = enum.auto()  # EDMA_A_IRQRL[INT15]
    EDMA_A_IRQ16            = enum.auto()  # EDMA_A_IRQRL[INT16]
    EDMA_A_IRQ17            = enum.auto()  # EDMA_A_IRQRL[INT17]
    EDMA_A_IRQ18            = enum.auto()  # EDMA_A_IRQRL[INT18]
    EDMA_A_IRQ19            = enum.auto()  # EDMA_A_IRQRL[INT19]
    EDMA_A_IRQ20            = enum.auto()  # EDMA_A_IRQRL[INT20]
    EDMA_A_IRQ21            = enum.auto()  # EDMA_A_IRQRL[INT21]
    EDMA_A_IRQ22            = enum.auto()  # EDMA_A_IRQRL[INT22]
    EDMA_A_IRQ23            = enum.auto()  # EDMA_A_IRQRL[INT23]
    EDMA_A_IRQ24            = enum.auto()  # EDMA_A_IRQRL[INT24]
    EDMA_A_IRQ25            = enum.auto()  # EDMA_A_IRQRL[INT25]
    EDMA_A_IRQ26            = enum.auto()  # EDMA_A_IRQRL[INT26]
    EDMA_A_IRQ27            = enum.auto()  # EDMA_A_IRQRL[INT27]
    EDMA_A_IRQ28            = enum.auto()  # EDMA_A_IRQRL[INT28]
    EDMA_A_IRQ29            = enum.auto()  # EDMA_A_IRQRL[INT29]
    EDMA_A_IRQ30            = enum.auto()  # EDMA_A_IRQRL[INT30]
    EDMA_A_IRQ31            = enum.auto()  # EDMA_A_IRQRL[INT31]
    EDMA_A_IRQ32            = enum.auto()  # EDMA_A_IRQRL[INT32]
    EDMA_A_IRQ33            = enum.auto()  # EDMA_A_IRQRL[INT33]
    EDMA_A_IRQ34            = enum.auto()  # EDMA_A_IRQRL[INT34]
    EDMA_A_IRQ35            = enum.auto()  # EDMA_A_IRQRL[INT35]
    EDMA_A_IRQ36            = enum.auto()  # EDMA_A_IRQRL[INT36]
    EDMA_A_IRQ37            = enum.auto()  # EDMA_A_IRQRL[INT37]
    EDMA_A_IRQ38            = enum.auto()  # EDMA_A_IRQRL[INT38]
    EDMA_A_IRQ39            = enum.auto()  # EDMA_A_IRQRL[INT39]
    EDMA_A_IRQ40            = enum.auto()  # EDMA_A_IRQRL[INT40]
    EDMA_A_IRQ41            = enum.auto()  # EDMA_A_IRQRL[INT41]
    EDMA_A_IRQ42            = enum.auto()  # EDMA_A_IRQRL[INT42]
    EDMA_A_IRQ43            = enum.auto()  # EDMA_A_IRQRL[INT43]
    EDMA_A_IRQ44            = enum.auto()  # EDMA_A_IRQRL[INT44]
    EDMA_A_IRQ45            = enum.auto()  # EDMA_A_IRQRL[INT45]
    EDMA_A_IRQ46            = enum.auto()  # EDMA_A_IRQRL[INT46]
    EDMA_A_IRQ47            = enum.auto()  # EDMA_A_IRQRL[INT47]
    EDMA_A_IRQ48            = enum.auto()  # EDMA_A_IRQRL[INT48]
    EDMA_A_IRQ49            = enum.auto()  # EDMA_A_IRQRL[INT49]
    EDMA_A_IRQ50            = enum.auto()  # EDMA_A_IRQRL[INT50]
    EDMA_A_IRQ51            = enum.auto()  # EDMA_A_IRQRL[INT51]
    EDMA_A_IRQ52            = enum.auto()  # EDMA_A_IRQRL[INT52]
    EDMA_A_IRQ53            = enum.auto()  # EDMA_A_IRQRL[INT53]
    EDMA_A_IRQ54            = enum.auto()  # EDMA_A_IRQRL[INT54]
    EDMA_A_IRQ55            = enum.auto()  # EDMA_A_IRQRL[INT55]
    EDMA_A_IRQ56            = enum.auto()  # EDMA_A_IRQRL[INT56]
    EDMA_A_IRQ57            = enum.auto()  # EDMA_A_IRQRL[INT57]
    EDMA_A_IRQ58            = enum.auto()  # EDMA_A_IRQRL[INT58]
    EDMA_A_IRQ59            = enum.auto()  # EDMA_A_IRQRL[INT59]
    EDMA_A_IRQ60            = enum.auto()  # EDMA_A_IRQRL[INT60]
    EDMA_A_IRQ61            = enum.auto()  # EDMA_A_IRQRL[INT61]
    EDMA_A_IRQ62            = enum.auto()  # EDMA_A_IRQRL[INT62]
    EDMA_A_IRQ63            = enum.auto()  # EDMA_A_IRQRL[INT63]

    # eDMA B
    EDMA_B_ERR0             = enum.auto()  # EDMA_B_ERL[0]
    EDMA_B_ERR1             = enum.auto()  # EDMA_B_ERL[1]
    EDMA_B_ERR2             = enum.auto()  # EDMA_B_ERL[2]
    EDMA_B_ERR3             = enum.auto()  # EDMA_B_ERL[3]
    EDMA_B_ERR4             = enum.auto()  # EDMA_B_ERL[4]
    EDMA_B_ERR5             = enum.auto()  # EDMA_B_ERL[5]
    EDMA_B_ERR6             = enum.auto()  # EDMA_B_ERL[6]
    EDMA_B_ERR7             = enum.auto()  # EDMA_B_ERL[7]
    EDMA_B_ERR8             = enum.auto()  # EDMA_B_ERL[8]
    EDMA_B_ERR9             = enum.auto()  # EDMA_B_ERL[9]
    EDMA_B_ERR10            = enum.auto()  # EDMA_B_ERL[10]
    EDMA_B_ERR11            = enum.auto()  # EDMA_B_ERL[11]
    EDMA_B_ERR12            = enum.auto()  # EDMA_B_ERL[12]
    EDMA_B_ERR13            = enum.auto()  # EDMA_B_ERL[13]
    EDMA_B_ERR14            = enum.auto()  # EDMA_B_ERL[14]
    EDMA_B_ERR15            = enum.auto()  # EDMA_B_ERL[15]
    EDMA_B_ERR16            = enum.auto()  # EDMA_B_ERL[16]
    EDMA_B_ERR17            = enum.auto()  # EDMA_B_ERL[17]
    EDMA_B_ERR18            = enum.auto()  # EDMA_B_ERL[18]
    EDMA_B_ERR19            = enum.auto()  # EDMA_B_ERL[19]
    EDMA_B_ERR20            = enum.auto()  # EDMA_B_ERL[20]
    EDMA_B_ERR21            = enum.auto()  # EDMA_B_ERL[21]
    EDMA_B_ERR22            = enum.auto()  # EDMA_B_ERL[22]
    EDMA_B_ERR23            = enum.auto()  # EDMA_B_ERL[23]
    EDMA_B_ERR24            = enum.auto()  # EDMA_B_ERL[24]
    EDMA_B_ERR25            = enum.auto()  # EDMA_B_ERL[25]
    EDMA_B_ERR26            = enum.auto()  # EDMA_B_ERL[26]
    EDMA_B_ERR27            = enum.auto()  # EDMA_B_ERL[27]
    EDMA_B_ERR28            = enum.auto()  # EDMA_B_ERL[28]
    EDMA_B_ERR29            = enum.auto()  # EDMA_B_ERL[29]
    EDMA_B_ERR30            = enum.auto()  # EDMA_B_ERL[30]
    EDMA_B_ERR31            = enum.auto()  # EDMA_B_ERL[31]
    EDMA_B_IRQ00            = enum.auto()  # EDMA_B_IRQRL[INT00]
    EDMA_B_IRQ01            = enum.auto()  # EDMA_B_IRQRL[INT01]
    EDMA_B_IRQ02            = enum.auto()  # EDMA_B_IRQRL[INT02]
    EDMA_B_IRQ03            = enum.auto()  # EDMA_B_IRQRL[INT03]
    EDMA_B_IRQ04            = enum.auto()  # EDMA_B_IRQRL[INT04]
    EDMA_B_IRQ05            = enum.auto()  # EDMA_B_IRQRL[INT05]
    EDMA_B_IRQ06            = enum.auto()  # EDMA_B_IRQRL[INT06]
    EDMA_B_IRQ07            = enum.auto()  # EDMA_B_IRQRL[INT07]
    EDMA_B_IRQ08            = enum.auto()  # EDMA_B_IRQRL[INT08]
    EDMA_B_IRQ09            = enum.auto()  # EDMA_B_IRQRL[INT09]
    EDMA_B_IRQ10            = enum.auto()  # EDMA_B_IRQRL[INT10]
    EDMA_B_IRQ11            = enum.auto()  # EDMA_B_IRQRL[INT11]
    EDMA_B_IRQ12            = enum.auto()  # EDMA_B_IRQRL[INT12]
    EDMA_B_IRQ13            = enum.auto()  # EDMA_B_IRQRL[INT13]
    EDMA_B_IRQ14            = enum.auto()  # EDMA_B_IRQRL[INT14]
    EDMA_B_IRQ15            = enum.auto()  # EDMA_B_IRQRL[INT15]
    EDMA_B_IRQ16            = enum.auto()  # EDMA_B_IRQRL[INT16]
    EDMA_B_IRQ17            = enum.auto()  # EDMA_B_IRQRL[INT17]
    EDMA_B_IRQ18            = enum.auto()  # EDMA_B_IRQRL[INT18]
    EDMA_B_IRQ19            = enum.auto()  # EDMA_B_IRQRL[INT19]
    EDMA_B_IRQ20            = enum.auto()  # EDMA_B_IRQRL[INT20]
    EDMA_B_IRQ21            = enum.auto()  # EDMA_B_IRQRL[INT21]
    EDMA_B_IRQ22            = enum.auto()  # EDMA_B_IRQRL[INT22]
    EDMA_B_IRQ23            = enum.auto()  # EDMA_B_IRQRL[INT23]
    EDMA_B_IRQ24            = enum.auto()  # EDMA_B_IRQRL[INT24]
    EDMA_B_IRQ25            = enum.auto()  # EDMA_B_IRQRL[INT25]
    EDMA_B_IRQ26            = enum.auto()  # EDMA_B_IRQRL[INT26]
    EDMA_B_IRQ27            = enum.auto()  # EDMA_B_IRQRL[INT27]
    EDMA_B_IRQ28            = enum.auto()  # EDMA_B_IRQRL[INT28]
    EDMA_B_IRQ29            = enum.auto()  # EDMA_B_IRQRL[INT29]
    EDMA_B_IRQ30            = enum.auto()  # EDMA_B_IRQRL[INT30]
    EDMA_B_IRQ31            = enum.auto()  # EDMA_B_IRQRL[INT31]

    # FMPLL
    FMPLL_LOC               = enum.auto()  # FMPLL_SYNSR[LOCF]
    FMPLL_LOL               = enum.auto()  # FMPLL_SYNSR[LOLF]

    # SIU
    SIU_OVF0                = enum.auto()  # SIU_OSR[OVF0]
    SIU_OVF1                = enum.auto()  # SIU_OSR[OVF1]
    SIU_OVF2                = enum.auto()  # SIU_OSR[OVF2]
    SIU_OVF3                = enum.auto()  # SIU_OSR[OVF3]
    SIU_OVF4                = enum.auto()  # SIU_OSR[OVF4]
    SIU_OVF5                = enum.auto()  # SIU_OSR[OVF5]
    SIU_OVF6                = enum.auto()  # SIU_OSR[OVF6]
    SIU_OVF7                = enum.auto()  # SIU_OSR[OVF7]
    SIU_OVF8                = enum.auto()  # SIU_OSR[OVF8]
    SIU_OVF9                = enum.auto()  # SIU_OSR[OVF9]
    SIU_OVF10               = enum.auto()  # SIU_OSR[OVF10]
    SIU_OVF11               = enum.auto()  # SIU_OSR[OVF11]
    SIU_OVF12               = enum.auto()  # SIU_OSR[OVF12]
    SIU_OVF13               = enum.auto()  # SIU_OSR[OVF13]
    SIU_OVF14               = enum.auto()  # SIU_OSR[OVF14]
    SIU_OVF15               = enum.auto()  # SIU_OSR[OVF15]
    SIU_EISR0               = enum.auto()  # SIU_EISR[EIF0]
    SIU_EISR1               = enum.auto()  # SIU_EISR[EIF1]
    SIU_EISR2               = enum.auto()  # SIU_EISR[EIF2]
    SIU_EISR3               = enum.auto()  # SIU_EISR[EIF3]
    SIU_EISR4               = enum.auto()  # SIU_EISR[EIF4]
    SIU_EISR5               = enum.auto()  # SIU_EISR[EIF5]
    SIU_EISR6               = enum.auto()  # SIU_EISR[EIF6]
    SIU_EISR7               = enum.auto()  # SIU_EISR[EIF7]
    SIU_EISR8               = enum.auto()  # SIU_EISR[EIF8]
    SIU_EISR9               = enum.auto()  # SIU_EISR[EIF9]
    SIU_EISR10              = enum.auto()  # SIU_EISR[EIF10]
    SIU_EISR11              = enum.auto()  # SIU_EISR[EIF11]
    SIU_EISR12              = enum.auto()  # SIU_EISR[EIF12]
    SIU_EISR13              = enum.auto()  # SIU_EISR[EIF13]
    SIU_EISR14              = enum.auto()  # SIU_EISR[EIF14]
    SIU_EISR15              = enum.auto()  # SIU_EISR[EIF15]

    # eMIOS
    EMIOS_GFR0              = enum.auto()  # EMIOS_GFR[F0]
    EMIOS_GFR1              = enum.auto()  # EMIOS_GFR[F1]
    EMIOS_GFR2              = enum.auto()  # EMIOS_GFR[F2]
    EMIOS_GFR3              = enum.auto()  # EMIOS_GFR[F3]
    EMIOS_GFR4              = enum.auto()  # EMIOS_GFR[F4]
    EMIOS_GFR5              = enum.auto()  # EMIOS_GFR[F5]
    EMIOS_GFR6              = enum.auto()  # EMIOS_GFR[F6]
    EMIOS_GFR7              = enum.auto()  # EMIOS_GFR[F7]
    EMIOS_GFR8              = enum.auto()  # EMIOS_GFR[F8]
    EMIOS_GFR9              = enum.auto()  # EMIOS_GFR[F9]
    EMIOS_GFR10             = enum.auto()  # EMIOS_GFR[F10]
    EMIOS_GFR11             = enum.auto()  # EMIOS_GFR[F11]
    EMIOS_GFR12             = enum.auto()  # EMIOS_GFR[F12]
    EMIOS_GFR13             = enum.auto()  # EMIOS_GFR[F13]
    EMIOS_GFR14             = enum.auto()  # EMIOS_GFR[F14]
    EMIOS_GFR15             = enum.auto()  # EMIOS_GFR[F15]
    EMIOS_GFR16             = enum.auto()  # EMIOS_GFR[F16]
    EMIOS_GFR17             = enum.auto()  # EMIOS_GFR[F17]
    EMIOS_GFR18             = enum.auto()  # EMIOS_GFR[F18]
    EMIOS_GFR19             = enum.auto()  # EMIOS_GFR[F19]
    EMIOS_GFR20             = enum.auto()  # EMIOS_GFR[F20]
    EMIOS_GFR21             = enum.auto()  # EMIOS_GFR[F21]
    EMIOS_GFR22             = enum.auto()  # EMIOS_GFR[F22]
    EMIOS_GFR23             = enum.auto()  # EMIOS_GFR[F23]
    EMIOS_GFR24             = enum.auto()  # EMIOS_GFR[F24]
    EMIOS_GFR25             = enum.auto()  # EMIOS_GFR[F25]
    EMIOS_GFR26             = enum.auto()  # EMIOS_GFR[F26]
    EMIOS_GFR27             = enum.auto()  # EMIOS_GFR[F27]
    EMIOS_GFR28             = enum.auto()  # EMIOS_GFR[F28]
    EMIOS_GFR29             = enum.auto()  # EMIOS_GFR[F29]
    EMIOS_GFR30             = enum.auto()  # EMIOS_GFR[F30]
    EMIOS_GFR31             = enum.auto()  # EMIOS_GFR[F31]

    # eTPU
    ETPU_MCR_MGEA           = enum.auto()  # ETPU_MCR[MGEA]
    ETPU_MCR_MGEB           = enum.auto()  # ETPU_MCR[MGEB]
    ETPU_MCR_ILFA           = enum.auto()  # ETPU_MCR[ILFA]
    ETPU_MCR_ILFB           = enum.auto()  # ETPU_MCR[ILFB]
    ETPU_MCR_SCMMISF        = enum.auto()  # ETPU_MCR[SCMMISF]

    # eTPU A
    ETPU_CISR_A0            = enum.auto()  # ETPU_CISR_A[CIS0]
    ETPU_CISR_A1            = enum.auto()  # ETPU_CISR_A[CIS1]
    ETPU_CISR_A2            = enum.auto()  # ETPU_CISR_A[CIS2]
    ETPU_CISR_A3            = enum.auto()  # ETPU_CISR_A[CIS3]
    ETPU_CISR_A4            = enum.auto()  # ETPU_CISR_A[CIS4]
    ETPU_CISR_A5            = enum.auto()  # ETPU_CISR_A[CIS5]
    ETPU_CISR_A6            = enum.auto()  # ETPU_CISR_A[CIS6]
    ETPU_CISR_A7            = enum.auto()  # ETPU_CISR_A[CIS7]
    ETPU_CISR_A8            = enum.auto()  # ETPU_CISR_A[CIS8]
    ETPU_CISR_A9            = enum.auto()  # ETPU_CISR_A[CIS9]
    ETPU_CISR_A10           = enum.auto()  # ETPU_CISR_A[CIS10]
    ETPU_CISR_A11           = enum.auto()  # ETPU_CISR_A[CIS11]
    ETPU_CISR_A12           = enum.auto()  # ETPU_CISR_A[CIS12]
    ETPU_CISR_A13           = enum.auto()  # ETPU_CISR_A[CIS13]
    ETPU_CISR_A14           = enum.auto()  # ETPU_CISR_A[CIS14]
    ETPU_CISR_A15           = enum.auto()  # ETPU_CISR_A[CIS15]
    ETPU_CISR_A16           = enum.auto()  # ETPU_CISR_A[CIS16]
    ETPU_CISR_A17           = enum.auto()  # ETPU_CISR_A[CIS17]
    ETPU_CISR_A18           = enum.auto()  # ETPU_CISR_A[CIS18]
    ETPU_CISR_A19           = enum.auto()  # ETPU_CISR_A[CIS19]
    ETPU_CISR_A20           = enum.auto()  # ETPU_CISR_A[CIS20]
    ETPU_CISR_A21           = enum.auto()  # ETPU_CISR_A[CIS21]
    ETPU_CISR_A22           = enum.auto()  # ETPU_CISR_A[CIS22]
    ETPU_CISR_A23           = enum.auto()  # ETPU_CISR_A[CIS23]
    ETPU_CISR_A24           = enum.auto()  # ETPU_CISR_A[CIS24]
    ETPU_CISR_A25           = enum.auto()  # ETPU_CISR_A[CIS25]
    ETPU_CISR_A26           = enum.auto()  # ETPU_CISR_A[CIS26]
    ETPU_CISR_A27           = enum.auto()  # ETPU_CISR_A[CIS27]
    ETPU_CISR_A28           = enum.auto()  # ETPU_CISR_A[CIS28]
    ETPU_CISR_A29           = enum.auto()  # ETPU_CISR_A[CIS29]
    ETPU_CISR_A30           = enum.auto()  # ETPU_CISR_A[CIS30]
    ETPU_CISR_A31           = enum.auto()  # ETPU_CISR_A[CIS31]
    ETPU_CDTRSR_A0          = enum.auto()  # ETPU_CDTRSR_A[DTROS0]
    ETPU_CDTRSR_A1          = enum.auto()  # ETPU_CDTRSR_A[DTROS1]
    ETPU_CDTRSR_A2          = enum.auto()  # ETPU_CDTRSR_A[DTROS2]
    ETPU_CDTRSR_A3          = enum.auto()  # ETPU_CDTRSR_A[DTROS3]
    ETPU_CDTRSR_A4          = enum.auto()  # ETPU_CDTRSR_A[DTROS4]
    ETPU_CDTRSR_A5          = enum.auto()  # ETPU_CDTRSR_A[DTROS5]
    ETPU_CDTRSR_A6          = enum.auto()  # ETPU_CDTRSR_A[DTROS6]
    ETPU_CDTRSR_A7          = enum.auto()  # ETPU_CDTRSR_A[DTROS7]
    ETPU_CDTRSR_A8          = enum.auto()  # ETPU_CDTRSR_A[DTROS8]
    ETPU_CDTRSR_A9          = enum.auto()  # ETPU_CDTRSR_A[DTROS9]
    ETPU_CDTRSR_A10         = enum.auto()  # ETPU_CDTRSR_A[DTROS10]
    ETPU_CDTRSR_A11         = enum.auto()  # ETPU_CDTRSR_A[DTROS11]
    ETPU_CDTRSR_A12         = enum.auto()  # ETPU_CDTRSR_A[DTROS12]
    ETPU_CDTRSR_A13         = enum.auto()  # ETPU_CDTRSR_A[DTROS13]
    ETPU_CDTRSR_A14         = enum.auto()  # ETPU_CDTRSR_A[DTROS14]
    ETPU_CDTRSR_A15         = enum.auto()  # ETPU_CDTRSR_A[DTROS15]
    ETPU_CDTRSR_A16         = enum.auto()  # ETPU_CDTRSR_A[DTROS16]
    ETPU_CDTRSR_A17         = enum.auto()  # ETPU_CDTRSR_A[DTROS17]
    ETPU_CDTRSR_A18         = enum.auto()  # ETPU_CDTRSR_A[DTROS18]
    ETPU_CDTRSR_A19         = enum.auto()  # ETPU_CDTRSR_A[DTROS19]
    ETPU_CDTRSR_A20         = enum.auto()  # ETPU_CDTRSR_A[DTROS20]
    ETPU_CDTRSR_A21         = enum.auto()  # ETPU_CDTRSR_A[DTROS21]
    ETPU_CDTRSR_A22         = enum.auto()  # ETPU_CDTRSR_A[DTROS22]
    ETPU_CDTRSR_A23         = enum.auto()  # ETPU_CDTRSR_A[DTROS23]
    ETPU_CDTRSR_A24         = enum.auto()  # ETPU_CDTRSR_A[DTROS24]
    ETPU_CDTRSR_A25         = enum.auto()  # ETPU_CDTRSR_A[DTROS25]
    ETPU_CDTRSR_A26         = enum.auto()  # ETPU_CDTRSR_A[DTROS26]
    ETPU_CDTRSR_A27         = enum.auto()  # ETPU_CDTRSR_A[DTROS27]
    ETPU_CDTRSR_A28         = enum.auto()  # ETPU_CDTRSR_A[DTROS28]
    ETPU_CDTRSR_A29         = enum.auto()  # ETPU_CDTRSR_A[DTROS29]
    ETPU_CDTRSR_A30         = enum.auto()  # ETPU_CDTRSR_A[DTROS30]
    ETPU_CDTRSR_A31         = enum.auto()  # ETPU_CDTRSR_A[DTROS31]

    # eTPU B
    ETPU_CISR_B0            = enum.auto()  # ETPU_CISR_B[CIS0]
    ETPU_CISR_B1            = enum.auto()  # ETPU_CISR_B[CIS1]
    ETPU_CISR_B2            = enum.auto()  # ETPU_CISR_B[CIS2]
    ETPU_CISR_B3            = enum.auto()  # ETPU_CISR_B[CIS3]
    ETPU_CISR_B4            = enum.auto()  # ETPU_CISR_B[CIS4]
    ETPU_CISR_B5            = enum.auto()  # ETPU_CISR_B[CIS5]
    ETPU_CISR_B6            = enum.auto()  # ETPU_CISR_B[CIS6]
    ETPU_CISR_B7            = enum.auto()  # ETPU_CISR_B[CIS7]
    ETPU_CISR_B8            = enum.auto()  # ETPU_CISR_B[CIS8]
    ETPU_CISR_B9            = enum.auto()  # ETPU_CISR_B[CIS9]
    ETPU_CISR_B10           = enum.auto()  # ETPU_CISR_B[CIS10]
    ETPU_CISR_B11           = enum.auto()  # ETPU_CISR_B[CIS11]
    ETPU_CISR_B12           = enum.auto()  # ETPU_CISR_B[CIS12]
    ETPU_CISR_B13           = enum.auto()  # ETPU_CISR_B[CIS13]
    ETPU_CISR_B14           = enum.auto()  # ETPU_CISR_B[CIS14]
    ETPU_CISR_B15           = enum.auto()  # ETPU_CISR_B[CIS15]
    ETPU_CISR_B16           = enum.auto()  # ETPU_CISR_B[CIS16]
    ETPU_CISR_B17           = enum.auto()  # ETPU_CISR_B[CIS17]
    ETPU_CISR_B18           = enum.auto()  # ETPU_CISR_B[CIS18]
    ETPU_CISR_B19           = enum.auto()  # ETPU_CISR_B[CIS19]
    ETPU_CISR_B20           = enum.auto()  # ETPU_CISR_B[CIS20]
    ETPU_CISR_B21           = enum.auto()  # ETPU_CISR_B[CIS21]
    ETPU_CISR_B22           = enum.auto()  # ETPU_CISR_B[CIS22]
    ETPU_CISR_B23           = enum.auto()  # ETPU_CISR_B[CIS23]
    ETPU_CISR_B24           = enum.auto()  # ETPU_CISR_B[CIS24]
    ETPU_CISR_B25           = enum.auto()  # ETPU_CISR_B[CIS25]
    ETPU_CISR_B26           = enum.auto()  # ETPU_CISR_B[CIS26]
    ETPU_CISR_B27           = enum.auto()  # ETPU_CISR_B[CIS27]
    ETPU_CISR_B28           = enum.auto()  # ETPU_CISR_B[CIS28]
    ETPU_CISR_B29           = enum.auto()  # ETPU_CISR_B[CIS29]
    ETPU_CISR_B30           = enum.auto()  # ETPU_CISR_B[CIS30]
    ETPU_CISR_B31           = enum.auto()  # ETPU_CISR_B[CIS31]
    ETPU_CDTRSR_B0          = enum.auto()  # ETPU_CDTRSR_B[DTROS0]
    ETPU_CDTRSR_B1          = enum.auto()  # ETPU_CDTRSR_B[DTROS1]
    ETPU_CDTRSR_B2          = enum.auto()  # ETPU_CDTRSR_B[DTROS2]
    ETPU_CDTRSR_B3          = enum.auto()  # ETPU_CDTRSR_B[DTROS3]
    ETPU_CDTRSR_B4          = enum.auto()  # ETPU_CDTRSR_B[DTROS4]
    ETPU_CDTRSR_B5          = enum.auto()  # ETPU_CDTRSR_B[DTROS5]
    ETPU_CDTRSR_B6          = enum.auto()  # ETPU_CDTRSR_B[DTROS6]
    ETPU_CDTRSR_B7          = enum.auto()  # ETPU_CDTRSR_B[DTROS7]
    ETPU_CDTRSR_B8          = enum.auto()  # ETPU_CDTRSR_B[DTROS8]
    ETPU_CDTRSR_B9          = enum.auto()  # ETPU_CDTRSR_B[DTROS9]
    ETPU_CDTRSR_B10         = enum.auto()  # ETPU_CDTRSR_B[DTROS10]
    ETPU_CDTRSR_B11         = enum.auto()  # ETPU_CDTRSR_B[DTROS11]
    ETPU_CDTRSR_B12         = enum.auto()  # ETPU_CDTRSR_B[DTROS12]
    ETPU_CDTRSR_B13         = enum.auto()  # ETPU_CDTRSR_B[DTROS13]
    ETPU_CDTRSR_B14         = enum.auto()  # ETPU_CDTRSR_B[DTROS14]
    ETPU_CDTRSR_B15         = enum.auto()  # ETPU_CDTRSR_B[DTROS15]
    ETPU_CDTRSR_B16         = enum.auto()  # ETPU_CDTRSR_B[DTROS16]
    ETPU_CDTRSR_B17         = enum.auto()  # ETPU_CDTRSR_B[DTROS17]
    ETPU_CDTRSR_B18         = enum.auto()  # ETPU_CDTRSR_B[DTROS18]
    ETPU_CDTRSR_B19         = enum.auto()  # ETPU_CDTRSR_B[DTROS19]
    ETPU_CDTRSR_B20         = enum.auto()  # ETPU_CDTRSR_B[DTROS20]
    ETPU_CDTRSR_B21         = enum.auto()  # ETPU_CDTRSR_B[DTROS21]
    ETPU_CDTRSR_B22         = enum.auto()  # ETPU_CDTRSR_B[DTROS22]
    ETPU_CDTRSR_B23         = enum.auto()  # ETPU_CDTRSR_B[DTROS23]
    ETPU_CDTRSR_B24         = enum.auto()  # ETPU_CDTRSR_B[DTROS24]
    ETPU_CDTRSR_B25         = enum.auto()  # ETPU_CDTRSR_B[DTROS25]
    ETPU_CDTRSR_B26         = enum.auto()  # ETPU_CDTRSR_B[DTROS26]
    ETPU_CDTRSR_B27         = enum.auto()  # ETPU_CDTRSR_B[DTROS27]
    ETPU_CDTRSR_B28         = enum.auto()  # ETPU_CDTRSR_B[DTROS28]
    ETPU_CDTRSR_B29         = enum.auto()  # ETPU_CDTRSR_B[DTROS29]
    ETPU_CDTRSR_B30         = enum.auto()  # ETPU_CDTRSR_B[DTROS30]
    ETPU_CDTRSR_B31         = enum.auto()  # ETPU_CDTRSR_B[DTROS31]

    # eQADC A
    EQADC_A_TORF            = enum.auto()  # EQADC_A_FISRx[TORF]
    EQADC_A_RFOF            = enum.auto()  # EQADC_A_FISRx[RFOF]
    EQADC_A_CFUF            = enum.auto()  # EQADC_A_FISRx[CFUF]
    EQADC_A_FISR0_NCF       = enum.auto()  # EQADC_A_FISR0[NCF]
    EQADC_A_FISR0_PF        = enum.auto()  # EQADC_A_FISR0[PF]
    EQADC_A_FISR0_EOQF      = enum.auto()  # EQADC_A_FISR0[EOQF]
    EQADC_A_FISR0_CFFF      = enum.auto()  # EQADC_A_FISR0[CFFF]
    EQADC_A_FISR0_RFDF      = enum.auto()  # EQADC_A_FISR0[RFDF]
    EQADC_A_FISR1_NCF       = enum.auto()  # EQADC_A_FISR1[NCF]
    EQADC_A_FISR1_PF        = enum.auto()  # EQADC_A_FISR1[PF]
    EQADC_A_FISR1_EOQF      = enum.auto()  # EQADC_A_FISR1[EOQF]
    EQADC_A_FISR1_CFFF      = enum.auto()  # EQADC_A_FISR1[CFFF]
    EQADC_A_FISR1_RFDF      = enum.auto()  # EQADC_A_FISR1[RFDF]
    EQADC_A_FISR2_NCF       = enum.auto()  # EQADC_A_FISR2[NCF]
    EQADC_A_FISR2_PF        = enum.auto()  # EQADC_A_FISR2[PF]
    EQADC_A_FISR2_EOQF      = enum.auto()  # EQADC_A_FISR2[EOQF]
    EQADC_A_FISR2_CFFF      = enum.auto()  # EQADC_A_FISR2[CFFF]
    EQADC_A_FISR2_RFDF      = enum.auto()  # EQADC_A_FISR2[RFDF]
    EQADC_A_FISR3_NCF       = enum.auto()  # EQADC_A_FISR3[NCF]
    EQADC_A_FISR3_PF        = enum.auto()  # EQADC_A_FISR3[PF]
    EQADC_A_FISR3_EOQF      = enum.auto()  # EQADC_A_FISR3[EOQF]
    EQADC_A_FISR3_CFFF      = enum.auto()  # EQADC_A_FISR3[CFFF]
    EQADC_A_FISR3_RFDF      = enum.auto()  # EQADC_A_FISR3[RFDF]
    EQADC_A_FISR4_NCF       = enum.auto()  # EQADC_A_FISR4[NCF]
    EQADC_A_FISR4_PF        = enum.auto()  # EQADC_A_FISR4[PF]
    EQADC_A_FISR4_EOQF      = enum.auto()  # EQADC_A_FISR4[EOQF]
    EQADC_A_FISR4_CFFF      = enum.auto()  # EQADC_A_FISR4[CFFF]
    EQADC_A_FISR4_RFDF      = enum.auto()  # EQADC_A_FISR4[RFDF]
    EQADC_A_FISR5_NCF       = enum.auto()  # EQADC_A_FISR5[NCF]
    EQADC_A_FISR5_PF        = enum.auto()  # EQADC_A_FISR5[PF]
    EQADC_A_FISR5_EOQF      = enum.auto()  # EQADC_A_FISR5[EOQF]
    EQADC_A_FISR5_CFFF      = enum.auto()  # EQADC_A_FISR5[CFFF]
    EQADC_A_FISR5_RFDF      = enum.auto()  # EQADC_A_FISR5[RFDF]

    # eQADC B
    EQADC_B_TORF            = enum.auto()  # EQADC_B_FISRx[TORF]
    EQADC_B_RFOF            = enum.auto()  # EQADC_B_FISRx[RFOF]
    EQADC_B_CFUF            = enum.auto()  # EQADC_B_FISRx[CFUF]
    EQADC_B_FISR0_NCF       = enum.auto()  # EQADC_B_FISR0[NCF]
    EQADC_B_FISR0_PF        = enum.auto()  # EQADC_B_FISR0[PF]
    EQADC_B_FISR0_EOQF      = enum.auto()  # EQADC_B_FISR0[EOQF]
    EQADC_B_FISR0_CFFF      = enum.auto()  # EQADC_B_FISR0[CFFF]
    EQADC_B_FISR0_RFDF      = enum.auto()  # EQADC_B_FISR0[RFDF]
    EQADC_B_FISR1_NCF       = enum.auto()  # EQADC_B_FISR1[NCF]
    EQADC_B_FISR1_PF        = enum.auto()  # EQADC_B_FISR1[PF]
    EQADC_B_FISR1_EOQF      = enum.auto()  # EQADC_B_FISR1[EOQF]
    EQADC_B_FISR1_CFFF      = enum.auto()  # EQADC_B_FISR1[CFFF]
    EQADC_B_FISR1_RFDF      = enum.auto()  # EQADC_B_FISR1[RFDF]
    EQADC_B_FISR2_NCF       = enum.auto()  # EQADC_B_FISR2[NCF]
    EQADC_B_FISR2_PF        = enum.auto()  # EQADC_B_FISR2[PF]
    EQADC_B_FISR2_EOQF      = enum.auto()  # EQADC_B_FISR2[EOQF]
    EQADC_B_FISR2_CFFF      = enum.auto()  # EQADC_B_FISR2[CFFF]
    EQADC_B_FISR2_RFDF      = enum.auto()  # EQADC_B_FISR2[RFDF]
    EQADC_B_FISR3_NCF       = enum.auto()  # EQADC_B_FISR3[NCF]
    EQADC_B_FISR3_PF        = enum.auto()  # EQADC_B_FISR3[PF]
    EQADC_B_FISR3_EOQF      = enum.auto()  # EQADC_B_FISR3[EOQF]
    EQADC_B_FISR3_CFFF      = enum.auto()  # EQADC_B_FISR3[CFFF]
    EQADC_B_FISR3_RFDF      = enum.auto()  # EQADC_B_FISR3[RFDF]
    EQADC_B_FISR4_NCF       = enum.auto()  # EQADC_B_FISR4[NCF]
    EQADC_B_FISR4_PF        = enum.auto()  # EQADC_B_FISR4[PF]
    EQADC_B_FISR4_EOQF      = enum.auto()  # EQADC_B_FISR4[EOQF]
    EQADC_B_FISR4_CFFF      = enum.auto()  # EQADC_B_FISR4[CFFF]
    EQADC_B_FISR4_RFDF      = enum.auto()  # EQADC_B_FISR4[RFDF]
    EQADC_B_FISR5_NCF       = enum.auto()  # EQADC_B_FISR5[NCF]
    EQADC_B_FISR5_PF        = enum.auto()  # EQADC_B_FISR5[PF]
    EQADC_B_FISR5_EOQF      = enum.auto()  # EQADC_B_FISR5[EOQF]
    EQADC_B_FISR5_CFFF      = enum.auto()  # EQADC_B_FISR5[CFFF]
    EQADC_B_FISR5_RFDF      = enum.auto()  # EQADC_B_FISR5[RFDF]

    # DSPI A
    DSPI_A_TFUF             = enum.auto()  # DSPI_ASR[TFUF]
    DSPI_A_RFOF             = enum.auto()  # DSPI_ASR[RFOF]
    DSPI_A_TX_EOQ           = enum.auto()  # DSPI_ASR[EOQF]
    DSPI_A_TX_FILL          = enum.auto()  # DSPI_ASR[TFFF]
    DSPI_A_TX_CMPLT         = enum.auto()  # DSPI_ASR[TCF]
    DSPI_A_RX_DRAIN         = enum.auto()  # DSPI_ASR[RFDF]

    # DSPI B
    DSPI_B_TFUF             = enum.auto()  # DSPI_BSR[TFUF]
    DSPI_B_RFOF             = enum.auto()  # DSPI_BSR[RFOF]
    DSPI_B_TX_EOQ           = enum.auto()  # DSPI_BSR[EOQF]
    DSPI_B_TX_FILL          = enum.auto()  # DSPI_BSR[TFFF]
    DSPI_B_TX_CMPLT         = enum.auto()  # DSPI_BSR[TCF]
    DSPI_B_RX_DRAIN         = enum.auto()  # DSPI_BSR[RFDF]

    # DSPI C
    DSPI_C_TFUF             = enum.auto()  # DSPI_CSR[TFUF]
    DSPI_C_RFOF             = enum.auto()  # DSPI_CSR[RFOF]
    DSPI_C_TX_EOQ           = enum.auto()  # DSPI_CSR[EOQF]
    DSPI_C_TX_FILL          = enum.auto()  # DSPI_CSR[TFFF]
    DSPI_C_TX_CMPLT         = enum.auto()  # DSPI_CSR[TCF]
    DSPI_C_RX_DRAIN         = enum.auto()  # DSPI_CSR[RFDF]

    # DSPI D
    DSPI_D_TFUF             = enum.auto()  # DSPI_DSR[TFUF]
    DSPI_D_RFOF             = enum.auto()  # DSPI_DSR[RFOF]
    DSPI_D_TX_EOQ           = enum.auto()  # DSPI_DSR[EOQF]
    DSPI_D_TX_FILL          = enum.auto()  # DSPI_DSR[TFFF]
    DSPI_D_TX_CMPLT         = enum.auto()  # DSPI_DSR[TCF]
    DSPI_D_RX_DRAIN         = enum.auto()  # DSPI_DSR[RFDF]

    # eSCI A
    ESCIA_IFSR1_TDRE        = enum.auto()  # ESCIA_IFSR1[TDRE]
    ESCIA_IFSR1_TC          = enum.auto()  # ESCIA_IFSR1[TC]
    ESCIA_IFSR1_RDRF        = enum.auto()  # ESCIA_IFSR1[RDRF]
    ESCIA_IFSR1_IDLE        = enum.auto()  # ESCIA_IFSR1[IDLE]
    ESCIA_IFSR1_OR          = enum.auto()  # ESCIA_IFSR1[OR]
    ESCIA_IFSR1_NF          = enum.auto()  # ESCIA_IFSR1[NF]
    ESCIA_IFSR1_FE          = enum.auto()  # ESCIA_IFSR1[FE]
    ESCIA_IFSR1_PF          = enum.auto()  # ESCIA_IFSR1[PF]
    ESCIA_IFSR1_BERR        = enum.auto()  # ESCIA_IFSR1[BERR]
    ESCIA_IFSR2_RXRDY       = enum.auto()  # ESCIA_IFSR2[RXRDY]
    ESCIA_IFSR2_TXRDY       = enum.auto()  # ESCIA_IFSR2[TXRDY]
    ESCIA_IFSR2_LWAKE       = enum.auto()  # ESCIA_IFSR2[LWAKE]
    ESCIA_IFSR2_STO         = enum.auto()  # ESCIA_IFSR2[STO]
    ESCIA_IFSR2_PBERR       = enum.auto()  # ESCIA_IFSR2[PBERR]
    ESCIA_IFSR2_CERR        = enum.auto()  # ESCIA_IFSR2[CERR]
    ESCIA_IFSR2_CKERR       = enum.auto()  # ESCIA_IFSR2[CKERR]
    ESCIA_IFSR2_FRC         = enum.auto()  # ESCIA_IFSR2[FRC]
    ESCIA_IFSR2_OVFL        = enum.auto()  # ESCIA_IFSR2[OVFL]
    ESCIA_IFSR2_UREQ        = enum.auto()  # ESCIA_IFSR2[UREQ]

    # eSCI B
    ESCIB_IFSR1_TDRE        = enum.auto()  # ESCIB_IFSR1[TDRE]
    ESCIB_IFSR1_TC          = enum.auto()  # ESCIB_IFSR1[TC]
    ESCIB_IFSR1_RDRF        = enum.auto()  # ESCIB_IFSR1[RDRF]
    ESCIB_IFSR1_IDLE        = enum.auto()  # ESCIB_IFSR1[IDLE]
    ESCIB_IFSR1_OR          = enum.auto()  # ESCIB_IFSR1[OR]
    ESCIB_IFSR1_NF          = enum.auto()  # ESCIB_IFSR1[NF]
    ESCIB_IFSR1_FE          = enum.auto()  # ESCIB_IFSR1[FE]
    ESCIB_IFSR1_PF          = enum.auto()  # ESCIB_IFSR1[PF]
    ESCIB_IFSR1_BERR        = enum.auto()  # ESCIB_IFSR1[BERR]
    ESCIB_IFSR2_RXRDY       = enum.auto()  # ESCIB_IFSR2[RXRDY]
    ESCIB_IFSR2_TXRDY       = enum.auto()  # ESCIB_IFSR2[TXRDY]
    ESCIB_IFSR2_LWAKE       = enum.auto()  # ESCIB_IFSR2[LWAKE]
    ESCIB_IFSR2_STO         = enum.auto()  # ESCIB_IFSR2[STO]
    ESCIB_IFSR2_PBERR       = enum.auto()  # ESCIB_IFSR2[PBERR]
    ESCIB_IFSR2_CERR        = enum.auto()  # ESCIB_IFSR2[CERR]
    ESCIB_IFSR2_CKERR       = enum.auto()  # ESCIB_IFSR2[CKERR]
    ESCIB_IFSR2_FRC         = enum.auto()  # ESCIB_IFSR2[FRC]
    ESCIB_IFSR2_OVFL        = enum.auto()  # ESCIB_IFSR2[OVFL]
    ESCIB_IFSR2_UREQ        = enum.auto()  # ESCIB_IFSR2[UREQ]

    # eSCI C
    ESCIC_IFSR1_TDRE        = enum.auto()  # ESCIC_IFSR1[TDRE]
    ESCIC_IFSR1_TC          = enum.auto()  # ESCIC_IFSR1[TC]
    ESCIC_IFSR1_RDRF        = enum.auto()  # ESCIC_IFSR1[RDRF]
    ESCIC_IFSR1_IDLE        = enum.auto()  # ESCIC_IFSR1[IDLE]
    ESCIC_IFSR1_OR          = enum.auto()  # ESCIC_IFSR1[OR]
    ESCIC_IFSR1_NF          = enum.auto()  # ESCIC_IFSR1[NF]
    ESCIC_IFSR1_FE          = enum.auto()  # ESCIC_IFSR1[FE]
    ESCIC_IFSR1_PF          = enum.auto()  # ESCIC_IFSR1[PF]
    ESCIC_IFSR1_BERR        = enum.auto()  # ESCIC_IFSR1[BERR]
    ESCIC_IFSR2_RXRDY       = enum.auto()  # ESCIC_IFSR2[RXRDY]
    ESCIC_IFSR2_TXRDY       = enum.auto()  # ESCIC_IFSR2[TXRDY]
    ESCIC_IFSR2_LWAKE       = enum.auto()  # ESCIC_IFSR2[LWAKE]
    ESCIC_IFSR2_STO         = enum.auto()  # ESCIC_IFSR2[STO]
    ESCIC_IFSR2_PBERR       = enum.auto()  # ESCIC_IFSR2[PBERR]
    ESCIC_IFSR2_CERR        = enum.auto()  # ESCIC_IFSR2[CERR]
    ESCIC_IFSR2_CKERR       = enum.auto()  # ESCIC_IFSR2[CKERR]
    ESCIC_IFSR2_FRC         = enum.auto()  # ESCIC_IFSR2[FRC]
    ESCIC_IFSR2_OVFL        = enum.auto()  # ESCIC_IFSR2[OVFL]
    ESCIC_IFSR2_UREQ        = enum.auto()  # ESCIC_IFSR2[UREQ]

    # FlexCAN A
    CANA_ESR_BOFF           = enum.auto()  # CANA_ESR[BOFF_INT]
    CANA_ESR_TWRN           = enum.auto()  # CANA_ESR[TWRN_INT]
    CANA_ESR_RWRN           = enum.auto()  # CANA_ESR[RWRN_INT]
    CANA_ESR_ERR            = enum.auto()  # CANA_ESR[ERR_INT]
    CANA_MB0                = enum.auto()  # CANA_IFRL[BUF0]
    CANA_MB1                = enum.auto()  # CANA_IFRL[BUF1]
    CANA_MB2                = enum.auto()  # CANA_IFRL[BUF2]
    CANA_MB3                = enum.auto()  # CANA_IFRL[BUF3]
    CANA_MB4                = enum.auto()  # CANA_IFRL[BUF4]
    CANA_MB5                = enum.auto()  # CANA_IFRL[BUF5]
    CANA_MB6                = enum.auto()  # CANA_IFRL[BUF6]
    CANA_MB7                = enum.auto()  # CANA_IFRL[BUF7]
    CANA_MB8                = enum.auto()  # CANA_IFRL[BUF8]
    CANA_MB9                = enum.auto()  # CANA_IFRL[BUF9]
    CANA_MB10               = enum.auto()  # CANA_IFRL[BUF10]
    CANA_MB11               = enum.auto()  # CANA_IFRL[BUF11]
    CANA_MB12               = enum.auto()  # CANA_IFRL[BUF12]
    CANA_MB13               = enum.auto()  # CANA_IFRL[BUF13]
    CANA_MB14               = enum.auto()  # CANA_IFRL[BUF14]
    CANA_MB15               = enum.auto()  # CANA_IFRL[BUF15]
    CANA_MB16               = enum.auto()  # CANA_IFRL[BUF16]
    CANA_MB17               = enum.auto()  # CANA_IFRL[BUF17]
    CANA_MB18               = enum.auto()  # CANA_IFRL[BUF18]
    CANA_MB19               = enum.auto()  # CANA_IFRL[BUF19]
    CANA_MB20               = enum.auto()  # CANA_IFRL[BUF20]
    CANA_MB21               = enum.auto()  # CANA_IFRL[BUF21]
    CANA_MB22               = enum.auto()  # CANA_IFRL[BUF22]
    CANA_MB23               = enum.auto()  # CANA_IFRL[BUF23]
    CANA_MB24               = enum.auto()  # CANA_IFRL[BUF24]
    CANA_MB25               = enum.auto()  # CANA_IFRL[BUF25]
    CANA_MB26               = enum.auto()  # CANA_IFRL[BUF26]
    CANA_MB27               = enum.auto()  # CANA_IFRL[BUF27]
    CANA_MB28               = enum.auto()  # CANA_IFRL[BUF28]
    CANA_MB29               = enum.auto()  # CANA_IFRL[BUF29]
    CANA_MB30               = enum.auto()  # CANA_IFRL[BUF30]
    CANA_MB31               = enum.auto()  # CANA_IFRL[BUF31]
    CANA_MB32               = enum.auto()  # CANA_IFRL[BUF32]
    CANA_MB33               = enum.auto()  # CANA_IFRL[BUF33]
    CANA_MB34               = enum.auto()  # CANA_IFRL[BUF34]
    CANA_MB35               = enum.auto()  # CANA_IFRL[BUF35]
    CANA_MB36               = enum.auto()  # CANA_IFRL[BUF36]
    CANA_MB37               = enum.auto()  # CANA_IFRL[BUF37]
    CANA_MB38               = enum.auto()  # CANA_IFRL[BUF38]
    CANA_MB39               = enum.auto()  # CANA_IFRL[BUF39]
    CANA_MB40               = enum.auto()  # CANA_IFRL[BUF40]
    CANA_MB41               = enum.auto()  # CANA_IFRL[BUF41]
    CANA_MB42               = enum.auto()  # CANA_IFRL[BUF42]
    CANA_MB43               = enum.auto()  # CANA_IFRL[BUF43]
    CANA_MB44               = enum.auto()  # CANA_IFRL[BUF44]
    CANA_MB45               = enum.auto()  # CANA_IFRL[BUF45]
    CANA_MB46               = enum.auto()  # CANA_IFRL[BUF46]
    CANA_MB47               = enum.auto()  # CANA_IFRL[BUF47]
    CANA_MB48               = enum.auto()  # CANA_IFRL[BUF48]
    CANA_MB49               = enum.auto()  # CANA_IFRL[BUF49]
    CANA_MB50               = enum.auto()  # CANA_IFRL[BUF50]
    CANA_MB51               = enum.auto()  # CANA_IFRL[BUF51]
    CANA_MB52               = enum.auto()  # CANA_IFRL[BUF52]
    CANA_MB53               = enum.auto()  # CANA_IFRL[BUF53]
    CANA_MB54               = enum.auto()  # CANA_IFRL[BUF54]
    CANA_MB55               = enum.auto()  # CANA_IFRL[BUF55]
    CANA_MB56               = enum.auto()  # CANA_IFRL[BUF56]
    CANA_MB57               = enum.auto()  # CANA_IFRL[BUF57]
    CANA_MB58               = enum.auto()  # CANA_IFRL[BUF58]
    CANA_MB59               = enum.auto()  # CANA_IFRL[BUF59]
    CANA_MB60               = enum.auto()  # CANA_IFRL[BUF60]
    CANA_MB61               = enum.auto()  # CANA_IFRL[BUF61]
    CANA_MB62               = enum.auto()  # CANA_IFRL[BUF62]
    CANA_MB63               = enum.auto()  # CANA_IFRL[BUF63]

    # FlexCAN B
    CANB_ESR_BOFF           = enum.auto()  # CANB_ESR[BOFF_INT]
    CANB_ESR_TWRN           = enum.auto()  # CANB_ESR[TWRN_INT]
    CANB_ESR_RWRN           = enum.auto()  # CANB_ESR[RWRN_INT]
    CANB_ESR_ERR            = enum.auto()  # CANB_ESR[ERR_INT]
    CANB_MB0                = enum.auto()  # CANB_IFRL[BUF0]
    CANB_MB1                = enum.auto()  # CANB_IFRL[BUF1]
    CANB_MB2                = enum.auto()  # CANB_IFRL[BUF2]
    CANB_MB3                = enum.auto()  # CANB_IFRL[BUF3]
    CANB_MB4                = enum.auto()  # CANB_IFRL[BUF4]
    CANB_MB5                = enum.auto()  # CANB_IFRL[BUF5]
    CANB_MB6                = enum.auto()  # CANB_IFRL[BUF6]
    CANB_MB7                = enum.auto()  # CANB_IFRL[BUF7]
    CANB_MB8                = enum.auto()  # CANB_IFRL[BUF8]
    CANB_MB9                = enum.auto()  # CANB_IFRL[BUF9]
    CANB_MB10               = enum.auto()  # CANB_IFRL[BUF10]
    CANB_MB11               = enum.auto()  # CANB_IFRL[BUF11]
    CANB_MB12               = enum.auto()  # CANB_IFRL[BUF12]
    CANB_MB13               = enum.auto()  # CANB_IFRL[BUF13]
    CANB_MB14               = enum.auto()  # CANB_IFRL[BUF14]
    CANB_MB15               = enum.auto()  # CANB_IFRL[BUF15]
    CANB_MB16               = enum.auto()  # CANB_IFRL[BUF16]
    CANB_MB17               = enum.auto()  # CANB_IFRL[BUF17]
    CANB_MB18               = enum.auto()  # CANB_IFRL[BUF18]
    CANB_MB19               = enum.auto()  # CANB_IFRL[BUF19]
    CANB_MB20               = enum.auto()  # CANB_IFRL[BUF20]
    CANB_MB21               = enum.auto()  # CANB_IFRL[BUF21]
    CANB_MB22               = enum.auto()  # CANB_IFRL[BUF22]
    CANB_MB23               = enum.auto()  # CANB_IFRL[BUF23]
    CANB_MB24               = enum.auto()  # CANB_IFRL[BUF24]
    CANB_MB25               = enum.auto()  # CANB_IFRL[BUF25]
    CANB_MB26               = enum.auto()  # CANB_IFRL[BUF26]
    CANB_MB27               = enum.auto()  # CANB_IFRL[BUF27]
    CANB_MB28               = enum.auto()  # CANB_IFRL[BUF28]
    CANB_MB29               = enum.auto()  # CANB_IFRL[BUF29]
    CANB_MB30               = enum.auto()  # CANB_IFRL[BUF30]
    CANB_MB31               = enum.auto()  # CANB_IFRL[BUF31]
    CANB_MB32               = enum.auto()  # CANB_IFRL[BUF32]
    CANB_MB33               = enum.auto()  # CANB_IFRL[BUF33]
    CANB_MB34               = enum.auto()  # CANB_IFRL[BUF34]
    CANB_MB35               = enum.auto()  # CANB_IFRL[BUF35]
    CANB_MB36               = enum.auto()  # CANB_IFRL[BUF36]
    CANB_MB37               = enum.auto()  # CANB_IFRL[BUF37]
    CANB_MB38               = enum.auto()  # CANB_IFRL[BUF38]
    CANB_MB39               = enum.auto()  # CANB_IFRL[BUF39]
    CANB_MB40               = enum.auto()  # CANB_IFRL[BUF40]
    CANB_MB41               = enum.auto()  # CANB_IFRL[BUF41]
    CANB_MB42               = enum.auto()  # CANB_IFRL[BUF42]
    CANB_MB43               = enum.auto()  # CANB_IFRL[BUF43]
    CANB_MB44               = enum.auto()  # CANB_IFRL[BUF44]
    CANB_MB45               = enum.auto()  # CANB_IFRL[BUF45]
    CANB_MB46               = enum.auto()  # CANB_IFRL[BUF46]
    CANB_MB47               = enum.auto()  # CANB_IFRL[BUF47]
    CANB_MB48               = enum.auto()  # CANB_IFRL[BUF48]
    CANB_MB49               = enum.auto()  # CANB_IFRL[BUF49]
    CANB_MB50               = enum.auto()  # CANB_IFRL[BUF50]
    CANB_MB51               = enum.auto()  # CANB_IFRL[BUF51]
    CANB_MB52               = enum.auto()  # CANB_IFRL[BUF52]
    CANB_MB53               = enum.auto()  # CANB_IFRL[BUF53]
    CANB_MB54               = enum.auto()  # CANB_IFRL[BUF54]
    CANB_MB55               = enum.auto()  # CANB_IFRL[BUF55]
    CANB_MB56               = enum.auto()  # CANB_IFRL[BUF56]
    CANB_MB57               = enum.auto()  # CANB_IFRL[BUF57]
    CANB_MB58               = enum.auto()  # CANB_IFRL[BUF58]
    CANB_MB59               = enum.auto()  # CANB_IFRL[BUF59]
    CANB_MB60               = enum.auto()  # CANB_IFRL[BUF60]
    CANB_MB61               = enum.auto()  # CANB_IFRL[BUF61]
    CANB_MB62               = enum.auto()  # CANB_IFRL[BUF62]
    CANB_MB63               = enum.auto()  # CANB_IFRL[BUF63]

    # FlexCAN C
    CANC_ESR_BOFF           = enum.auto()  # CANC_ESR[BOFF_INT]
    CANC_ESR_TWRN           = enum.auto()  # CANC_ESR[TWRN_INT]
    CANC_ESR_RWRN           = enum.auto()  # CANC_ESR[RWRN_INT]
    CANC_ESR_ERR            = enum.auto()  # CANC_ESR[ERR_INT]
    CANC_MB0                = enum.auto()  # CANC_IFRL[BUF0]
    CANC_MB1                = enum.auto()  # CANC_IFRL[BUF1]
    CANC_MB2                = enum.auto()  # CANC_IFRL[BUF2]
    CANC_MB3                = enum.auto()  # CANC_IFRL[BUF3]
    CANC_MB4                = enum.auto()  # CANC_IFRL[BUF4]
    CANC_MB5                = enum.auto()  # CANC_IFRL[BUF5]
    CANC_MB6                = enum.auto()  # CANC_IFRL[BUF6]
    CANC_MB7                = enum.auto()  # CANC_IFRL[BUF7]
    CANC_MB8                = enum.auto()  # CANC_IFRL[BUF8]
    CANC_MB9                = enum.auto()  # CANC_IFRL[BUF9]
    CANC_MB10               = enum.auto()  # CANC_IFRL[BUF10]
    CANC_MB11               = enum.auto()  # CANC_IFRL[BUF11]
    CANC_MB12               = enum.auto()  # CANC_IFRL[BUF12]
    CANC_MB13               = enum.auto()  # CANC_IFRL[BUF13]
    CANC_MB14               = enum.auto()  # CANC_IFRL[BUF14]
    CANC_MB15               = enum.auto()  # CANC_IFRL[BUF15]
    CANC_MB16               = enum.auto()  # CANC_IFRL[BUF16]
    CANC_MB17               = enum.auto()  # CANC_IFRL[BUF17]
    CANC_MB18               = enum.auto()  # CANC_IFRL[BUF18]
    CANC_MB19               = enum.auto()  # CANC_IFRL[BUF19]
    CANC_MB20               = enum.auto()  # CANC_IFRL[BUF20]
    CANC_MB21               = enum.auto()  # CANC_IFRL[BUF21]
    CANC_MB22               = enum.auto()  # CANC_IFRL[BUF22]
    CANC_MB23               = enum.auto()  # CANC_IFRL[BUF23]
    CANC_MB24               = enum.auto()  # CANC_IFRL[BUF24]
    CANC_MB25               = enum.auto()  # CANC_IFRL[BUF25]
    CANC_MB26               = enum.auto()  # CANC_IFRL[BUF26]
    CANC_MB27               = enum.auto()  # CANC_IFRL[BUF27]
    CANC_MB28               = enum.auto()  # CANC_IFRL[BUF28]
    CANC_MB29               = enum.auto()  # CANC_IFRL[BUF29]
    CANC_MB30               = enum.auto()  # CANC_IFRL[BUF30]
    CANC_MB31               = enum.auto()  # CANC_IFRL[BUF31]
    CANC_MB32               = enum.auto()  # CANC_IFRL[BUF32]
    CANC_MB33               = enum.auto()  # CANC_IFRL[BUF33]
    CANC_MB34               = enum.auto()  # CANC_IFRL[BUF34]
    CANC_MB35               = enum.auto()  # CANC_IFRL[BUF35]
    CANC_MB36               = enum.auto()  # CANC_IFRL[BUF36]
    CANC_MB37               = enum.auto()  # CANC_IFRL[BUF37]
    CANC_MB38               = enum.auto()  # CANC_IFRL[BUF38]
    CANC_MB39               = enum.auto()  # CANC_IFRL[BUF39]
    CANC_MB40               = enum.auto()  # CANC_IFRL[BUF40]
    CANC_MB41               = enum.auto()  # CANC_IFRL[BUF41]
    CANC_MB42               = enum.auto()  # CANC_IFRL[BUF42]
    CANC_MB43               = enum.auto()  # CANC_IFRL[BUF43]
    CANC_MB44               = enum.auto()  # CANC_IFRL[BUF44]
    CANC_MB45               = enum.auto()  # CANC_IFRL[BUF45]
    CANC_MB46               = enum.auto()  # CANC_IFRL[BUF46]
    CANC_MB47               = enum.auto()  # CANC_IFRL[BUF47]
    CANC_MB48               = enum.auto()  # CANC_IFRL[BUF48]
    CANC_MB49               = enum.auto()  # CANC_IFRL[BUF49]
    CANC_MB50               = enum.auto()  # CANC_IFRL[BUF50]
    CANC_MB51               = enum.auto()  # CANC_IFRL[BUF51]
    CANC_MB52               = enum.auto()  # CANC_IFRL[BUF52]
    CANC_MB53               = enum.auto()  # CANC_IFRL[BUF53]
    CANC_MB54               = enum.auto()  # CANC_IFRL[BUF54]
    CANC_MB55               = enum.auto()  # CANC_IFRL[BUF55]
    CANC_MB56               = enum.auto()  # CANC_IFRL[BUF56]
    CANC_MB57               = enum.auto()  # CANC_IFRL[BUF57]
    CANC_MB58               = enum.auto()  # CANC_IFRL[BUF58]
    CANC_MB59               = enum.auto()  # CANC_IFRL[BUF59]
    CANC_MB60               = enum.auto()  # CANC_IFRL[BUF60]
    CANC_MB61               = enum.auto()  # CANC_IFRL[BUF61]
    CANC_MB62               = enum.auto()  # CANC_IFRL[BUF62]
    CANC_MB63               = enum.auto()  # CANC_IFRL[BUF63]

    # FlexCAN D
    CAND_ESR_BOFF           = enum.auto()  # CAND_ESR[BOFF_INT]
    CAND_ESR_TWRN           = enum.auto()  # CAND_ESR[TWRN_INT]
    CAND_ESR_RWRN           = enum.auto()  # CAND_ESR[RWRN_INT]
    CAND_ESR_ERR            = enum.auto()  # CAND_ESR[ERR_INT]
    CAND_MB0                = enum.auto()  # CAND_IFRL[BUF0]
    CAND_MB1                = enum.auto()  # CAND_IFRL[BUF1]
    CAND_MB2                = enum.auto()  # CAND_IFRL[BUF2]
    CAND_MB3                = enum.auto()  # CAND_IFRL[BUF3]
    CAND_MB4                = enum.auto()  # CAND_IFRL[BUF4]
    CAND_MB5                = enum.auto()  # CAND_IFRL[BUF5]
    CAND_MB6                = enum.auto()  # CAND_IFRL[BUF6]
    CAND_MB7                = enum.auto()  # CAND_IFRL[BUF7]
    CAND_MB8                = enum.auto()  # CAND_IFRL[BUF8]
    CAND_MB9                = enum.auto()  # CAND_IFRL[BUF9]
    CAND_MB10               = enum.auto()  # CAND_IFRL[BUF10]
    CAND_MB11               = enum.auto()  # CAND_IFRL[BUF11]
    CAND_MB12               = enum.auto()  # CAND_IFRL[BUF12]
    CAND_MB13               = enum.auto()  # CAND_IFRL[BUF13]
    CAND_MB14               = enum.auto()  # CAND_IFRL[BUF14]
    CAND_MB15               = enum.auto()  # CAND_IFRL[BUF15]
    CAND_MB16               = enum.auto()  # CAND_IFRL[BUF16]
    CAND_MB17               = enum.auto()  # CAND_IFRL[BUF17]
    CAND_MB18               = enum.auto()  # CAND_IFRL[BUF18]
    CAND_MB19               = enum.auto()  # CAND_IFRL[BUF19]
    CAND_MB20               = enum.auto()  # CAND_IFRL[BUF20]
    CAND_MB21               = enum.auto()  # CAND_IFRL[BUF21]
    CAND_MB22               = enum.auto()  # CAND_IFRL[BUF22]
    CAND_MB23               = enum.auto()  # CAND_IFRL[BUF23]
    CAND_MB24               = enum.auto()  # CAND_IFRL[BUF24]
    CAND_MB25               = enum.auto()  # CAND_IFRL[BUF25]
    CAND_MB26               = enum.auto()  # CAND_IFRL[BUF26]
    CAND_MB27               = enum.auto()  # CAND_IFRL[BUF27]
    CAND_MB28               = enum.auto()  # CAND_IFRL[BUF28]
    CAND_MB29               = enum.auto()  # CAND_IFRL[BUF29]
    CAND_MB30               = enum.auto()  # CAND_IFRL[BUF30]
    CAND_MB31               = enum.auto()  # CAND_IFRL[BUF31]
    CAND_MB32               = enum.auto()  # CAND_IFRL[BUF32]
    CAND_MB33               = enum.auto()  # CAND_IFRL[BUF33]
    CAND_MB34               = enum.auto()  # CAND_IFRL[BUF34]
    CAND_MB35               = enum.auto()  # CAND_IFRL[BUF35]
    CAND_MB36               = enum.auto()  # CAND_IFRL[BUF36]
    CAND_MB37               = enum.auto()  # CAND_IFRL[BUF37]
    CAND_MB38               = enum.auto()  # CAND_IFRL[BUF38]
    CAND_MB39               = enum.auto()  # CAND_IFRL[BUF39]
    CAND_MB40               = enum.auto()  # CAND_IFRL[BUF40]
    CAND_MB41               = enum.auto()  # CAND_IFRL[BUF41]
    CAND_MB42               = enum.auto()  # CAND_IFRL[BUF42]
    CAND_MB43               = enum.auto()  # CAND_IFRL[BUF43]
    CAND_MB44               = enum.auto()  # CAND_IFRL[BUF44]
    CAND_MB45               = enum.auto()  # CAND_IFRL[BUF45]
    CAND_MB46               = enum.auto()  # CAND_IFRL[BUF46]
    CAND_MB47               = enum.auto()  # CAND_IFRL[BUF47]
    CAND_MB48               = enum.auto()  # CAND_IFRL[BUF48]
    CAND_MB49               = enum.auto()  # CAND_IFRL[BUF49]
    CAND_MB50               = enum.auto()  # CAND_IFRL[BUF50]
    CAND_MB51               = enum.auto()  # CAND_IFRL[BUF51]
    CAND_MB52               = enum.auto()  # CAND_IFRL[BUF52]
    CAND_MB53               = enum.auto()  # CAND_IFRL[BUF53]
    CAND_MB54               = enum.auto()  # CAND_IFRL[BUF54]
    CAND_MB55               = enum.auto()  # CAND_IFRL[BUF55]
    CAND_MB56               = enum.auto()  # CAND_IFRL[BUF56]
    CAND_MB57               = enum.auto()  # CAND_IFRL[BUF57]
    CAND_MB58               = enum.auto()  # CAND_IFRL[BUF58]
    CAND_MB59               = enum.auto()  # CAND_IFRL[BUF59]
    CAND_MB60               = enum.auto()  # CAND_IFRL[BUF60]
    CAND_MB61               = enum.auto()  # CAND_IFRL[BUF61]
    CAND_MB62               = enum.auto()  # CAND_IFRL[BUF62]
    CAND_MB63               = enum.auto()  # CAND_IFRL[BUF63]

    # Decimation Filter A
    DECA_MSR_IDF            = enum.auto()  # DECA_MSR[IDF]
    DECA_MSR_ODF            = enum.auto()  # DECA_MSR[ODF]
    DECA_MSR_IBIF           = enum.auto()  # DECA_MSR[IBIF]
    DECA_MSR_OBIF           = enum.auto()  # DECA_MSR[OBIF]
    DECA_MSR_DIVR           = enum.auto()  # DECA_MSR[DIVR]
    DECA_MSR_OVR            = enum.auto()  # DECA_MSR[OVR]
    DECA_MSR_IVR            = enum.auto()  # DECA_MSR[IVR]

    # Decimation Filter B
    DECB_MSR_IDF            = enum.auto()  # DECB_MSR[IDF]
    DECB_MSR_ODF            = enum.auto()  # DECB_MSR[ODF]
    DECB_MSR_IBIF           = enum.auto()  # DECB_MSR[IBIF]
    DECB_MSR_OBIF           = enum.auto()  # DECB_MSR[OBIF]
    DECB_MSR_DIVR           = enum.auto()  # DECB_MSR[DIVR]
    DECB_MSR_OVR            = enum.auto()  # DECB_MSR[OVR]
    DECB_MSR_IVR            = enum.auto()  # DECB_MSR[IVR]

    # Decimation Filter C
    DECC_MSR_IDF            = enum.auto()  # DECC_MSR[IDF]
    DECC_MSR_ODF            = enum.auto()  # DECC_MSR[ODF]
    DECC_MSR_IBIF           = enum.auto()  # DECC_MSR[IBIF]
    DECC_MSR_OBIF           = enum.auto()  # DECC_MSR[OBIF]
    DECC_MSR_DIVR           = enum.auto()  # DECC_MSR[DIVR]
    DECC_MSR_OVR            = enum.auto()  # DECC_MSR[OVR]
    DECC_MSR_IVR            = enum.auto()  # DECC_MSR[IVR]

    # Decimation Filter D
    DECD_MSR_IDF            = enum.auto()  # DECD_MSR[IDF]
    DECD_MSR_ODF            = enum.auto()  # DECD_MSR[ODF]
    DECD_MSR_IBIF           = enum.auto()  # DECD_MSR[IBIF]
    DECD_MSR_OBIF           = enum.auto()  # DECD_MSR[OBIF]
    DECD_MSR_DIVR           = enum.auto()  # DECD_MSR[DIVR]
    DECD_MSR_OVR            = enum.auto()  # DECD_MSR[OVR]
    DECD_MSR_IVR            = enum.auto()  # DECD_MSR[IVR]

    # Decimation Filter E
    DECE_MSR_IDF            = enum.auto()  # DECE_MSR[IDF]
    DECE_MSR_ODF            = enum.auto()  # DECE_MSR[ODF]
    DECE_MSR_IBIF           = enum.auto()  # DECE_MSR[IBIF]
    DECE_MSR_OBIF           = enum.auto()  # DECE_MSR[OBIF]
    DECE_MSR_DIVR           = enum.auto()  # DECE_MSR[DIVR]
    DECE_MSR_OVR            = enum.auto()  # DECE_MSR[OVR]
    DECE_MSR_IVR            = enum.auto()  # DECE_MSR[IVR]

    # Decimation Filter F
    DECF_MSR_IDF            = enum.auto()  # DECF_MSR[IDF]
    DECF_MSR_ODF            = enum.auto()  # DECF_MSR[ODF]
    DECF_MSR_IBIF           = enum.auto()  # DECF_MSR[IBIF]
    DECF_MSR_OBIF           = enum.auto()  # DECF_MSR[OBIF]
    DECF_MSR_DIVR           = enum.auto()  # DECF_MSR[DIVR]
    DECF_MSR_OVR            = enum.auto()  # DECF_MSR[OVR]
    DECF_MSR_IVR            = enum.auto()  # DECF_MSR[IVR]

    # Decimation Filter G
    DECG_MSR_IDF            = enum.auto()  # DECG_MSR[IDF]
    DECG_MSR_ODF            = enum.auto()  # DECG_MSR[ODF]
    DECG_MSR_IBIF           = enum.auto()  # DECG_MSR[IBIF]
    DECG_MSR_OBIF           = enum.auto()  # DECG_MSR[OBIF]
    DECG_MSR_DIVR           = enum.auto()  # DECG_MSR[DIVR]
    DECG_MSR_OVR            = enum.auto()  # DECG_MSR[OVR]
    DECG_MSR_IVR            = enum.auto()  # DECG_MSR[IVR]

    # Decimation Filter H
    DECH_MSR_IDF            = enum.auto()  # DECH_MSR[IDF]
    DECH_MSR_ODF            = enum.auto()  # DECH_MSR[ODF]
    DECH_MSR_IBIF           = enum.auto()  # DECH_MSR[IBIF]
    DECH_MSR_OBIF           = enum.auto()  # DECH_MSR[OBIF]
    DECH_MSR_DIVR           = enum.auto()  # DECH_MSR[DIVR]
    DECH_MSR_OVR            = enum.auto()  # DECH_MSR[OVR]
    DECH_MSR_IVR            = enum.auto()  # DECH_MSR[IVR]

    # STM
    STM0                    = enum.auto()  # STM[0]
    STM1                    = enum.auto()  # STM[1]
    STM2                    = enum.auto()  # STM[2]
    STM3                    = enum.auto()  # STM[3]

    # PIT
    PIT_CH0                 = enum.auto()  # PIT CH[0]
    PIT_CH1                 = enum.auto()  # PIT CH[1]
    PIT_CH2                 = enum.auto()  # PIT CH[2]
    PIT_CH3                 = enum.auto()  # PIT CH[3]
    PIT_RTI                 = enum.auto()  # PIT RTI

    # PMC
    PMC                     = enum.auto()  # PMC

    # SRAM ECC (?)
    ECC                     = enum.auto()  # ECC Correction

    # FlexRAY
    FLEXRAY_MIF             = enum.auto()  # GIFER[MIF]
    FLEXRAY_PROTO           = enum.auto()  # GIFER[PRIF]
    FLEXRAY_ERR             = enum.auto()  # GIFER[CHIF]
    FLEXRAY_WKUP            = enum.auto()  # GIFER[WUP_IF]
    FLEXRAY_B_WTRMRK        = enum.auto()  # GIFER[FBNE_F]
    FLEXRAY_A_WTRMRK        = enum.auto()  # GIFER[FANE_F]
    FLEXRAY_RX              = enum.auto()  # GIFER[RBIF]
    FLEXRAY_TX              = enum.auto()  # GIFER[TBIF]


class DMA_REQUEST(enum.Enum):
    # eDMA A
    EQADC_A_FISR0_CFFF      = ('eDMA_A', 0)
    EQADC_A_FISR0_RFDF      = ('eDMA_A', 1)
    EQADC_A_FISR1_CFFF      = ('eDMA_A', 2)
    EQADC_A_FISR1_RFDF      = ('eDMA_A', 3)
    EQADC_A_FISR2_CFFF      = ('eDMA_A', 4)
    EQADC_A_FISR2_RFDF      = ('eDMA_A', 5)
    EQADC_A_FISR3_CFFF      = ('eDMA_A', 6)
    EQADC_A_FISR3_RFDF      = ('eDMA_A', 7)
    EQADC_A_FISR4_CFFF      = ('eDMA_A', 8)
    EQADC_A_FISR4_RFDF      = ('eDMA_A', 9)
    EQADC_A_FISR5_CFFF      = ('eDMA_A', 10)
    EQADC_A_FISR5_RFDF      = ('eDMA_A', 11)
    DSPIB_SR_TFFF           = ('eDMA_A', 12)
    DSPIB_SR_RFDF           = ('eDMA_A', 13)
    DSPIC_SR_TFFF           = ('eDMA_A', 14)
    DSPIC_SR_RFDF           = ('eDMA_A', 15)
    DSPID_SR_TFFF           = ('eDMA_A', 16)
    DSPID_SR_RFDF           = ('eDMA_A', 17)
    ESCIA_COMBTX            = ('eDMA_A', 18)
    ESCIA_COMBRX            = ('eDMA_A', 19)
    EMIOS_GFR_F0            = ('eDMA_A', 20)
    EMIOS_GFR_F1            = ('eDMA_A', 21)
    EMIOS_GFR_F2            = ('eDMA_A', 22)
    EMIOS_GFR_F3            = ('eDMA_A', 23)
    EMIOS_GFR_F4            = ('eDMA_A', 24)
    EMIOS_GFR_F8            = ('eDMA_A', 25)
    EMIOS_GFR_F9            = ('eDMA_A', 26)
    ETPU_CDTRSR_A_DTRS0     = ('eDMA_A', 27)
    ETPU_CDTRSR_A_DTRS1     = ('eDMA_A', 28)
    ETPU_CDTRSR_A_DTRS2     = ('eDMA_A', 29)
    ETPU_CDTRSR_A_DTRS14    = ('eDMA_A', 30)
    ETPU_CDTRSR_A_DTRS15    = ('eDMA_A', 31)
    DSPIA_SR_TFFF           = ('eDMA_A', 32)
    DSPIA_SR_RFDF           = ('eDMA_A', 33)
    ESCIB_COMBTX            = ('eDMA_A', 34)
    ESCIB_COMBRX            = ('eDMA_A', 35)
    EMIOS_GFR_F6            = ('eDMA_A', 36)
    EMIOS_GFR_F7            = ('eDMA_A', 37)
    EMIOS_GFR_F10           = ('eDMA_A', 38)
    EMIOS_GFR_F11           = ('eDMA_A', 39)
    EMIOS_GFR_F16           = ('eDMA_A', 40)
    EMIOS_GFR_F17           = ('eDMA_A', 41)
    EMIOS_GFR_F18           = ('eDMA_A', 42)
    EMIOS_GFR_F19           = ('eDMA_A', 43)
    ETPU_CDTRSR_A_DTRS12    = ('eDMA_A', 44)
    ETPU_CDTRSR_A_DTRS13    = ('eDMA_A', 45)
    ETPU_CDTRSR_A_DTRS28    = ('eDMA_A', 46)
    ETPU_CDTRSR_A_DTRS29    = ('eDMA_A', 47)
    SIU_EISR_EIF0           = ('eDMA_A', 48)
    SIU_EISR_EIF1           = ('eDMA_A', 49)
    SIU_EISR_EIF2           = ('eDMA_A', 50)
    SIU_EISR_EIF3           = ('eDMA_A', 51)
    ETPU_CDTRSR_B_DTRS0     = ('eDMA_A', 52)
    ETPU_CDTRSR_B_DTRS1     = ('eDMA_A', 53)
    ETPU_CDTRSR_B_DTRS2     = ('eDMA_A', 54)
    ETPU_CDTRSR_B_DTRS3     = ('eDMA_A', 55)
    ETPU_CDTRSR_B_DTRS12    = ('eDMA_A', 56)
    ETPU_CDTRSR_B_DTRS13    = ('eDMA_A', 57)
    ETPU_CDTRSR_B_DTRS14    = ('eDMA_A', 58)
    ETPU_CDTRSR_B_DTRS15    = ('eDMA_A', 59)
    ETPU_CDTRSR_B_DTRS28    = ('eDMA_A', 60)
    ETPU_CDTRSR_B_DTRS29    = ('eDMA_A', 61)
    ETPU_CDTRSR_B_DTRS30    = ('eDMA_A', 62)
    ETPU_CDTRSR_B_DTRS31    = ('eDMA_A', 63)

    # eDMA B
    EQADC_B_FISR0_CFFF      = ('eDMA_B', 0)
    EQADC_B_FISR0_RFDF      = ('eDMA_B', 1)
    EQADC_B_FISR1_CFFF      = ('eDMA_B', 2)
    EQADC_B_FISR1_RFDF      = ('eDMA_B', 3)
    EQADC_B_FISR2_CFFF      = ('eDMA_B', 4)
    EQADC_B_FISR2_RFDF      = ('eDMA_B', 5)
    EQADC_B_FISR3_CFFF      = ('eDMA_B', 6)
    EQADC_B_FISR3_RFDF      = ('eDMA_B', 7)
    EQADC_B_FISR4_CFFF      = ('eDMA_B', 8)
    EQADC_B_FISR4_RFDF      = ('eDMA_B', 9)
    EQADC_B_FISR5_CFFF      = ('eDMA_B', 10)
    EQADC_B_FISR5_RFDF      = ('eDMA_B', 11)
    DECFILTERA_IB           = ('eDMA_B', 12)
    DECFILTERA_OB           = ('eDMA_B', 13)
    DECFILTERB_IB           = ('eDMA_B', 14)
    DECFILTERB_OB           = ('eDMA_B', 15)
    DECFILTERC_IB           = ('eDMA_B', 16)
    DECFILTERC_OB           = ('eDMA_B', 17)
    DECFILTERD_IB           = ('eDMA_B', 18)
    DECFILTERD_OB           = ('eDMA_B', 19)
    DECFILTERE_IB           = ('eDMA_B', 20)
    DECFILTERE_OB           = ('eDMA_B', 21)
    DECFILTERF_IB           = ('eDMA_B', 22)
    DECFILTERF_OB           = ('eDMA_B', 23)
    DECFILTERG_IB           = ('eDMA_B', 24)
    DECFILTERG_OB           = ('eDMA_B', 25)
    DECFILTERH_IB           = ('eDMA_B', 26)
    DECFILTERH_OB           = ('eDMA_B', 27)


# Mapping of interrupt event to interrupt source and DMA request
INTC_EVENT_MAP = {
    # SW triggered interrupts
    INTC_EVENT.INTC_SW_0:           (INTC_SRC.INTC_SW_0,            None),
    INTC_EVENT.INTC_SW_1:           (INTC_SRC.INTC_SW_1,            None),
    INTC_EVENT.INTC_SW_2:           (INTC_SRC.INTC_SW_2,            None),
    INTC_EVENT.INTC_SW_3:           (INTC_SRC.INTC_SW_3,            None),
    INTC_EVENT.INTC_SW_4:           (INTC_SRC.INTC_SW_4,            None),
    INTC_EVENT.INTC_SW_5:           (INTC_SRC.INTC_SW_5,            None),
    INTC_EVENT.INTC_SW_6:           (INTC_SRC.INTC_SW_6,            None),
    INTC_EVENT.INTC_SW_7:           (INTC_SRC.INTC_SW_7,            None),

    # SWT
    INTC_EVENT.SWT:                 (INTC_SRC.SWT,                  None),

    # ECSM
    INTC_EVENT.ECSM_ESR_R1BE:       (None,                          None),
    INTC_EVENT.ECSM_ESR_F1BE:       (None,                          None),
    INTC_EVENT.ECSM_ESR_RNCE:       (INTC_SRC.ECSM,                 None),
    INTC_EVENT.ECSM_ESR_FNCE:       (INTC_SRC.ECSM,                 None),

    # eDMA A
    INTC_EVENT.EDMA_A_ERR0:         (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR1:         (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR2:         (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR3:         (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR4:         (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR5:         (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR6:         (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR7:         (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR8:         (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR9:         (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR10:        (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR11:        (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR12:        (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR13:        (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR14:        (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR15:        (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR16:        (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR17:        (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR18:        (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR19:        (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR20:        (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR21:        (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR22:        (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR23:        (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR24:        (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR25:        (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR26:        (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR27:        (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR28:        (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR29:        (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR30:        (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR31:        (INTC_SRC.EDMA_A_ERR,           None),
    INTC_EVENT.EDMA_A_ERR32:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR33:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR34:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR35:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR36:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR37:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR38:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR39:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR40:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR41:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR42:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR43:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR44:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR45:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR46:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR47:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR48:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR49:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR50:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR51:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR52:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR53:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR54:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR55:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR56:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR57:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR58:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR59:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR60:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR61:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR62:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_ERR63:        (INTC_SRC.EDMA_A_ERR32_63,      None),
    INTC_EVENT.EDMA_A_IRQ0:         (INTC_SRC.EDMA_A_IRQ0,          None),
    INTC_EVENT.EDMA_A_IRQ1:         (INTC_SRC.EDMA_A_IRQ1,          None),
    INTC_EVENT.EDMA_A_IRQ2:         (INTC_SRC.EDMA_A_IRQ2,          None),
    INTC_EVENT.EDMA_A_IRQ3:         (INTC_SRC.EDMA_A_IRQ3,          None),
    INTC_EVENT.EDMA_A_IRQ4:         (INTC_SRC.EDMA_A_IRQ4,          None),
    INTC_EVENT.EDMA_A_IRQ5:         (INTC_SRC.EDMA_A_IRQ5,          None),
    INTC_EVENT.EDMA_A_IRQ6:         (INTC_SRC.EDMA_A_IRQ6,          None),
    INTC_EVENT.EDMA_A_IRQ7:         (INTC_SRC.EDMA_A_IRQ7,          None),
    INTC_EVENT.EDMA_A_IRQ8:         (INTC_SRC.EDMA_A_IRQ8,          None),
    INTC_EVENT.EDMA_A_IRQ9:         (INTC_SRC.EDMA_A_IRQ9,          None),
    INTC_EVENT.EDMA_A_IRQ10:        (INTC_SRC.EDMA_A_IRQ10,         None),
    INTC_EVENT.EDMA_A_IRQ11:        (INTC_SRC.EDMA_A_IRQ11,         None),
    INTC_EVENT.EDMA_A_IRQ12:        (INTC_SRC.EDMA_A_IRQ12,         None),
    INTC_EVENT.EDMA_A_IRQ13:        (INTC_SRC.EDMA_A_IRQ13,         None),
    INTC_EVENT.EDMA_A_IRQ14:        (INTC_SRC.EDMA_A_IRQ14,         None),
    INTC_EVENT.EDMA_A_IRQ15:        (INTC_SRC.EDMA_A_IRQ15,         None),
    INTC_EVENT.EDMA_A_IRQ16:        (INTC_SRC.EDMA_A_IRQ16,         None),
    INTC_EVENT.EDMA_A_IRQ17:        (INTC_SRC.EDMA_A_IRQ17,         None),
    INTC_EVENT.EDMA_A_IRQ18:        (INTC_SRC.EDMA_A_IRQ18,         None),
    INTC_EVENT.EDMA_A_IRQ19:        (INTC_SRC.EDMA_A_IRQ19,         None),
    INTC_EVENT.EDMA_A_IRQ20:        (INTC_SRC.EDMA_A_IRQ20,         None),
    INTC_EVENT.EDMA_A_IRQ21:        (INTC_SRC.EDMA_A_IRQ21,         None),
    INTC_EVENT.EDMA_A_IRQ22:        (INTC_SRC.EDMA_A_IRQ22,         None),
    INTC_EVENT.EDMA_A_IRQ23:        (INTC_SRC.EDMA_A_IRQ23,         None),
    INTC_EVENT.EDMA_A_IRQ24:        (INTC_SRC.EDMA_A_IRQ24,         None),
    INTC_EVENT.EDMA_A_IRQ25:        (INTC_SRC.EDMA_A_IRQ25,         None),
    INTC_EVENT.EDMA_A_IRQ26:        (INTC_SRC.EDMA_A_IRQ26,         None),
    INTC_EVENT.EDMA_A_IRQ27:        (INTC_SRC.EDMA_A_IRQ27,         None),
    INTC_EVENT.EDMA_A_IRQ28:        (INTC_SRC.EDMA_A_IRQ28,         None),
    INTC_EVENT.EDMA_A_IRQ29:        (INTC_SRC.EDMA_A_IRQ29,         None),
    INTC_EVENT.EDMA_A_IRQ30:        (INTC_SRC.EDMA_A_IRQ30,         None),
    INTC_EVENT.EDMA_A_IRQ31:        (INTC_SRC.EDMA_A_IRQ31,         None),
    INTC_EVENT.EDMA_A_IRQ32:        (INTC_SRC.EDMA_A_IRQ32,         None),
    INTC_EVENT.EDMA_A_IRQ33:        (INTC_SRC.EDMA_A_IRQ33,         None),
    INTC_EVENT.EDMA_A_IRQ34:        (INTC_SRC.EDMA_A_IRQ34,         None),
    INTC_EVENT.EDMA_A_IRQ35:        (INTC_SRC.EDMA_A_IRQ35,         None),
    INTC_EVENT.EDMA_A_IRQ36:        (INTC_SRC.EDMA_A_IRQ36,         None),
    INTC_EVENT.EDMA_A_IRQ37:        (INTC_SRC.EDMA_A_IRQ37,         None),
    INTC_EVENT.EDMA_A_IRQ38:        (INTC_SRC.EDMA_A_IRQ38,         None),
    INTC_EVENT.EDMA_A_IRQ39:        (INTC_SRC.EDMA_A_IRQ39,         None),
    INTC_EVENT.EDMA_A_IRQ40:        (INTC_SRC.EDMA_A_IRQ40,         None),
    INTC_EVENT.EDMA_A_IRQ41:        (INTC_SRC.EDMA_A_IRQ41,         None),
    INTC_EVENT.EDMA_A_IRQ42:        (INTC_SRC.EDMA_A_IRQ42,         None),
    INTC_EVENT.EDMA_A_IRQ43:        (INTC_SRC.EDMA_A_IRQ43,         None),
    INTC_EVENT.EDMA_A_IRQ44:        (INTC_SRC.EDMA_A_IRQ44,         None),
    INTC_EVENT.EDMA_A_IRQ45:        (INTC_SRC.EDMA_A_IRQ45,         None),
    INTC_EVENT.EDMA_A_IRQ46:        (INTC_SRC.EDMA_A_IRQ46,         None),
    INTC_EVENT.EDMA_A_IRQ47:        (INTC_SRC.EDMA_A_IRQ47,         None),
    INTC_EVENT.EDMA_A_IRQ48:        (INTC_SRC.EDMA_A_IRQ48,         None),
    INTC_EVENT.EDMA_A_IRQ49:        (INTC_SRC.EDMA_A_IRQ49,         None),
    INTC_EVENT.EDMA_A_IRQ50:        (INTC_SRC.EDMA_A_IRQ50,         None),
    INTC_EVENT.EDMA_A_IRQ51:        (INTC_SRC.EDMA_A_IRQ51,         None),
    INTC_EVENT.EDMA_A_IRQ52:        (INTC_SRC.EDMA_A_IRQ52,         None),
    INTC_EVENT.EDMA_A_IRQ53:        (INTC_SRC.EDMA_A_IRQ53,         None),
    INTC_EVENT.EDMA_A_IRQ54:        (INTC_SRC.EDMA_A_IRQ54,         None),
    INTC_EVENT.EDMA_A_IRQ55:        (INTC_SRC.EDMA_A_IRQ55,         None),
    INTC_EVENT.EDMA_A_IRQ56:        (INTC_SRC.EDMA_A_IRQ56,         None),
    INTC_EVENT.EDMA_A_IRQ57:        (INTC_SRC.EDMA_A_IRQ57,         None),
    INTC_EVENT.EDMA_A_IRQ58:        (INTC_SRC.EDMA_A_IRQ58,         None),
    INTC_EVENT.EDMA_A_IRQ59:        (INTC_SRC.EDMA_A_IRQ59,         None),
    INTC_EVENT.EDMA_A_IRQ60:        (INTC_SRC.EDMA_A_IRQ60,         None),
    INTC_EVENT.EDMA_A_IRQ61:        (INTC_SRC.EDMA_A_IRQ61,         None),
    INTC_EVENT.EDMA_A_IRQ62:        (INTC_SRC.EDMA_A_IRQ62,         None),
    INTC_EVENT.EDMA_A_IRQ63:        (INTC_SRC.EDMA_A_IRQ63,         None),

    # eDMA B
    INTC_EVENT.EDMA_B_ERR0:         (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR1:         (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR2:         (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR3:         (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR4:         (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR5:         (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR6:         (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR7:         (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR8:         (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR9:         (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR10:        (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR11:        (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR12:        (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR13:        (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR14:        (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR15:        (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR16:        (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR17:        (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR18:        (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR19:        (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR20:        (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR21:        (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR22:        (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR23:        (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR24:        (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR25:        (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR26:        (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR27:        (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR28:        (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR29:        (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR30:        (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_ERR31:        (INTC_SRC.EDMA_B_ERR,           None),
    INTC_EVENT.EDMA_B_IRQ00:        (INTC_SRC.EDMA_B_IRQ0,          None),
    INTC_EVENT.EDMA_B_IRQ01:        (INTC_SRC.EDMA_B_IRQ1,          None),
    INTC_EVENT.EDMA_B_IRQ02:        (INTC_SRC.EDMA_B_IRQ2,          None),
    INTC_EVENT.EDMA_B_IRQ03:        (INTC_SRC.EDMA_B_IRQ3,          None),
    INTC_EVENT.EDMA_B_IRQ04:        (INTC_SRC.EDMA_B_IRQ4,          None),
    INTC_EVENT.EDMA_B_IRQ05:        (INTC_SRC.EDMA_B_IRQ5,          None),
    INTC_EVENT.EDMA_B_IRQ06:        (INTC_SRC.EDMA_B_IRQ6,          None),
    INTC_EVENT.EDMA_B_IRQ07:        (INTC_SRC.EDMA_B_IRQ7,          None),
    INTC_EVENT.EDMA_B_IRQ08:        (INTC_SRC.EDMA_B_IRQ8,          None),
    INTC_EVENT.EDMA_B_IRQ09:        (INTC_SRC.EDMA_B_IRQ9,          None),
    INTC_EVENT.EDMA_B_IRQ10:        (INTC_SRC.EDMA_B_IRQ10,         None),
    INTC_EVENT.EDMA_B_IRQ11:        (INTC_SRC.EDMA_B_IRQ11,         None),
    INTC_EVENT.EDMA_B_IRQ12:        (INTC_SRC.EDMA_B_IRQ12,         None),
    INTC_EVENT.EDMA_B_IRQ13:        (INTC_SRC.EDMA_B_IRQ13,         None),
    INTC_EVENT.EDMA_B_IRQ14:        (INTC_SRC.EDMA_B_IRQ14,         None),
    INTC_EVENT.EDMA_B_IRQ15:        (INTC_SRC.EDMA_B_IRQ15,         None),
    INTC_EVENT.EDMA_B_IRQ16:        (INTC_SRC.EDMA_B_IRQ16,         None),
    INTC_EVENT.EDMA_B_IRQ17:        (INTC_SRC.EDMA_B_IRQ17,         None),
    INTC_EVENT.EDMA_B_IRQ18:        (INTC_SRC.EDMA_B_IRQ18,         None),
    INTC_EVENT.EDMA_B_IRQ19:        (INTC_SRC.EDMA_B_IRQ19,         None),
    INTC_EVENT.EDMA_B_IRQ20:        (INTC_SRC.EDMA_B_IRQ20,         None),
    INTC_EVENT.EDMA_B_IRQ21:        (INTC_SRC.EDMA_B_IRQ21,         None),
    INTC_EVENT.EDMA_B_IRQ22:        (INTC_SRC.EDMA_B_IRQ22,         None),
    INTC_EVENT.EDMA_B_IRQ23:        (INTC_SRC.EDMA_B_IRQ23,         None),
    INTC_EVENT.EDMA_B_IRQ24:        (INTC_SRC.EDMA_B_IRQ24,         None),
    INTC_EVENT.EDMA_B_IRQ25:        (INTC_SRC.EDMA_B_IRQ25,         None),
    INTC_EVENT.EDMA_B_IRQ26:        (INTC_SRC.EDMA_B_IRQ26,         None),
    INTC_EVENT.EDMA_B_IRQ27:        (INTC_SRC.EDMA_B_IRQ27,         None),
    INTC_EVENT.EDMA_B_IRQ28:        (INTC_SRC.EDMA_B_IRQ28,         None),
    INTC_EVENT.EDMA_B_IRQ29:        (INTC_SRC.EDMA_B_IRQ29,         None),
    INTC_EVENT.EDMA_B_IRQ30:        (INTC_SRC.EDMA_B_IRQ30,         None),
    INTC_EVENT.EDMA_B_IRQ31:        (INTC_SRC.EDMA_B_IRQ31,         None),

    # FMPLL
    INTC_EVENT.FMPLL_LOC:           (INTC_SRC.FMPLL_LOC,            None),
    INTC_EVENT.FMPLL_LOL:           (INTC_SRC.FMPLL_LOL,            None),

    # SIU
    INTC_EVENT.SIU_OVF0:            (INTC_SRC.SIU_OSR,              None),
    INTC_EVENT.SIU_OVF1:            (INTC_SRC.SIU_OSR,              None),
    INTC_EVENT.SIU_OVF2:            (INTC_SRC.SIU_OSR,              None),
    INTC_EVENT.SIU_OVF3:            (INTC_SRC.SIU_OSR,              None),
    INTC_EVENT.SIU_OVF4:            (INTC_SRC.SIU_OSR,              None),
    INTC_EVENT.SIU_OVF5:            (INTC_SRC.SIU_OSR,              None),
    INTC_EVENT.SIU_OVF6:            (INTC_SRC.SIU_OSR,              None),
    INTC_EVENT.SIU_OVF7:            (INTC_SRC.SIU_OSR,              None),
    INTC_EVENT.SIU_OVF8:            (INTC_SRC.SIU_OSR,              None),
    INTC_EVENT.SIU_OVF9:            (INTC_SRC.SIU_OSR,              None),
    INTC_EVENT.SIU_OVF10:           (INTC_SRC.SIU_OSR,              None),
    INTC_EVENT.SIU_OVF11:           (INTC_SRC.SIU_OSR,              None),
    INTC_EVENT.SIU_OVF12:           (INTC_SRC.SIU_OSR,              None),
    INTC_EVENT.SIU_OVF13:           (INTC_SRC.SIU_OSR,              None),
    INTC_EVENT.SIU_OVF14:           (INTC_SRC.SIU_OSR,              None),
    INTC_EVENT.SIU_OVF15:           (INTC_SRC.SIU_OSR,              None),
    INTC_EVENT.SIU_EISR0:           (INTC_SRC.SIU_EISR0,            DMA_REQUEST.SIU_EISR_EIF0),
    INTC_EVENT.SIU_EISR1:           (INTC_SRC.SIU_EISR1,            DMA_REQUEST.SIU_EISR_EIF1),
    INTC_EVENT.SIU_EISR2:           (INTC_SRC.SIU_EISR2,            DMA_REQUEST.SIU_EISR_EIF2),
    INTC_EVENT.SIU_EISR3:           (INTC_SRC.SIU_EISR3,            DMA_REQUEST.SIU_EISR_EIF3),
    INTC_EVENT.SIU_EISR4:           (INTC_SRC.SIU_EISR4_15,         None),
    INTC_EVENT.SIU_EISR5:           (INTC_SRC.SIU_EISR4_15,         None),
    INTC_EVENT.SIU_EISR6:           (INTC_SRC.SIU_EISR4_15,         None),
    INTC_EVENT.SIU_EISR7:           (INTC_SRC.SIU_EISR4_15,         None),
    INTC_EVENT.SIU_EISR8:           (INTC_SRC.SIU_EISR4_15,         None),
    INTC_EVENT.SIU_EISR9:           (INTC_SRC.SIU_EISR4_15,         None),
    INTC_EVENT.SIU_EISR10:          (INTC_SRC.SIU_EISR4_15,         None),
    INTC_EVENT.SIU_EISR11:          (INTC_SRC.SIU_EISR4_15,         None),
    INTC_EVENT.SIU_EISR12:          (INTC_SRC.SIU_EISR4_15,         None),
    INTC_EVENT.SIU_EISR13:          (INTC_SRC.SIU_EISR4_15,         None),
    INTC_EVENT.SIU_EISR14:          (INTC_SRC.SIU_EISR4_15,         None),
    INTC_EVENT.SIU_EISR15:          (INTC_SRC.SIU_EISR4_15,         None),

    # eMIOS
    INTC_EVENT.EMIOS_GFR0:          (INTC_SRC.EMIOS_GFR0,           DMA_REQUEST.EMIOS_GFR_F0),
    INTC_EVENT.EMIOS_GFR1:          (INTC_SRC.EMIOS_GFR1,           DMA_REQUEST.EMIOS_GFR_F1),
    INTC_EVENT.EMIOS_GFR2:          (INTC_SRC.EMIOS_GFR2,           DMA_REQUEST.EMIOS_GFR_F2),
    INTC_EVENT.EMIOS_GFR3:          (INTC_SRC.EMIOS_GFR3,           DMA_REQUEST.EMIOS_GFR_F3),
    INTC_EVENT.EMIOS_GFR4:          (INTC_SRC.EMIOS_GFR4,           DMA_REQUEST.EMIOS_GFR_F4),
    INTC_EVENT.EMIOS_GFR5:          (INTC_SRC.EMIOS_GFR5,           None),
    INTC_EVENT.EMIOS_GFR6:          (INTC_SRC.EMIOS_GFR6,           DMA_REQUEST.EMIOS_GFR_F6),
    INTC_EVENT.EMIOS_GFR7:          (INTC_SRC.EMIOS_GFR7,           DMA_REQUEST.EMIOS_GFR_F7),
    INTC_EVENT.EMIOS_GFR8:          (INTC_SRC.EMIOS_GFR8,           DMA_REQUEST.EMIOS_GFR_F8),
    INTC_EVENT.EMIOS_GFR9:          (INTC_SRC.EMIOS_GFR9,           DMA_REQUEST.EMIOS_GFR_F9),
    INTC_EVENT.EMIOS_GFR10:         (INTC_SRC.EMIOS_GFR10,          DMA_REQUEST.EMIOS_GFR_F10),
    INTC_EVENT.EMIOS_GFR11:         (INTC_SRC.EMIOS_GFR11,          DMA_REQUEST.EMIOS_GFR_F11),
    INTC_EVENT.EMIOS_GFR12:         (INTC_SRC.EMIOS_GFR12,          None),
    INTC_EVENT.EMIOS_GFR13:         (INTC_SRC.EMIOS_GFR13,          None),
    INTC_EVENT.EMIOS_GFR14:         (INTC_SRC.EMIOS_GFR14,          None),
    INTC_EVENT.EMIOS_GFR15:         (INTC_SRC.EMIOS_GFR15,          None),
    INTC_EVENT.EMIOS_GFR16:         (INTC_SRC.EMIOS_GFR16,          DMA_REQUEST.EMIOS_GFR_F16),
    INTC_EVENT.EMIOS_GFR17:         (INTC_SRC.EMIOS_GFR17,          DMA_REQUEST.EMIOS_GFR_F17),
    INTC_EVENT.EMIOS_GFR18:         (INTC_SRC.EMIOS_GFR18,          DMA_REQUEST.EMIOS_GFR_F18),
    INTC_EVENT.EMIOS_GFR19:         (INTC_SRC.EMIOS_GFR19,          DMA_REQUEST.EMIOS_GFR_F19),
    INTC_EVENT.EMIOS_GFR20:         (INTC_SRC.EMIOS_GFR20,          None),
    INTC_EVENT.EMIOS_GFR21:         (INTC_SRC.EMIOS_GFR21,          None),
    INTC_EVENT.EMIOS_GFR22:         (INTC_SRC.EMIOS_GFR22,          None),
    INTC_EVENT.EMIOS_GFR23:         (INTC_SRC.EMIOS_GFR23,          None),
    INTC_EVENT.EMIOS_GFR24:         (INTC_SRC.EMIOS_GFR24,          None),
    INTC_EVENT.EMIOS_GFR25:         (INTC_SRC.EMIOS_GFR25,          None),
    INTC_EVENT.EMIOS_GFR26:         (INTC_SRC.EMIOS_GFR26,          None),
    INTC_EVENT.EMIOS_GFR27:         (INTC_SRC.EMIOS_GFR27,          None),
    INTC_EVENT.EMIOS_GFR28:         (INTC_SRC.EMIOS_GFR28,          None),
    INTC_EVENT.EMIOS_GFR29:         (INTC_SRC.EMIOS_GFR29,          None),
    INTC_EVENT.EMIOS_GFR30:         (INTC_SRC.EMIOS_GFR30,          None),
    INTC_EVENT.EMIOS_GFR31:         (INTC_SRC.EMIOS_GFR31,          None),

    # eTPU
    INTC_EVENT.ETPU_MCR_MGEA:       (INTC_SRC.ETPU_MCR,             None),
    INTC_EVENT.ETPU_MCR_MGEB:       (INTC_SRC.ETPU_MCR,             None),
    INTC_EVENT.ETPU_MCR_ILFA:       (INTC_SRC.ETPU_MCR,             None),
    INTC_EVENT.ETPU_MCR_ILFB:       (INTC_SRC.ETPU_MCR,             None),
    INTC_EVENT.ETPU_MCR_SCMMISF:    (INTC_SRC.ETPU_MCR,             None),

    # eTPU A
    INTC_EVENT.ETPU_CISR_A0:        (INTC_SRC.ETPU_CISR_A0,         None),
    INTC_EVENT.ETPU_CISR_A1:        (INTC_SRC.ETPU_CISR_A1,         None),
    INTC_EVENT.ETPU_CISR_A2:        (INTC_SRC.ETPU_CISR_A2,         None),
    INTC_EVENT.ETPU_CISR_A3:        (INTC_SRC.ETPU_CISR_A3,         None),
    INTC_EVENT.ETPU_CISR_A4:        (INTC_SRC.ETPU_CISR_A4,         None),
    INTC_EVENT.ETPU_CISR_A5:        (INTC_SRC.ETPU_CISR_A5,         None),
    INTC_EVENT.ETPU_CISR_A6:        (INTC_SRC.ETPU_CISR_A6,         None),
    INTC_EVENT.ETPU_CISR_A7:        (INTC_SRC.ETPU_CISR_A7,         None),
    INTC_EVENT.ETPU_CISR_A8:        (INTC_SRC.ETPU_CISR_A8,         None),
    INTC_EVENT.ETPU_CISR_A9:        (INTC_SRC.ETPU_CISR_A9,         None),
    INTC_EVENT.ETPU_CISR_A10:       (INTC_SRC.ETPU_CISR_A10,        None),
    INTC_EVENT.ETPU_CISR_A11:       (INTC_SRC.ETPU_CISR_A11,        None),
    INTC_EVENT.ETPU_CISR_A12:       (INTC_SRC.ETPU_CISR_A12,        None),
    INTC_EVENT.ETPU_CISR_A13:       (INTC_SRC.ETPU_CISR_A13,        None),
    INTC_EVENT.ETPU_CISR_A14:       (INTC_SRC.ETPU_CISR_A14,        None),
    INTC_EVENT.ETPU_CISR_A15:       (INTC_SRC.ETPU_CISR_A15,        None),
    INTC_EVENT.ETPU_CISR_A16:       (INTC_SRC.ETPU_CISR_A16,        None),
    INTC_EVENT.ETPU_CISR_A17:       (INTC_SRC.ETPU_CISR_A17,        None),
    INTC_EVENT.ETPU_CISR_A18:       (INTC_SRC.ETPU_CISR_A18,        None),
    INTC_EVENT.ETPU_CISR_A19:       (INTC_SRC.ETPU_CISR_A19,        None),
    INTC_EVENT.ETPU_CISR_A20:       (INTC_SRC.ETPU_CISR_A20,        None),
    INTC_EVENT.ETPU_CISR_A21:       (INTC_SRC.ETPU_CISR_A21,        None),
    INTC_EVENT.ETPU_CISR_A22:       (INTC_SRC.ETPU_CISR_A22,        None),
    INTC_EVENT.ETPU_CISR_A23:       (INTC_SRC.ETPU_CISR_A23,        None),
    INTC_EVENT.ETPU_CISR_A24:       (INTC_SRC.ETPU_CISR_A24,        None),
    INTC_EVENT.ETPU_CISR_A25:       (INTC_SRC.ETPU_CISR_A25,        None),
    INTC_EVENT.ETPU_CISR_A26:       (INTC_SRC.ETPU_CISR_A26,        None),
    INTC_EVENT.ETPU_CISR_A27:       (INTC_SRC.ETPU_CISR_A27,        None),
    INTC_EVENT.ETPU_CISR_A28:       (INTC_SRC.ETPU_CISR_A28,        None),
    INTC_EVENT.ETPU_CISR_A29:       (INTC_SRC.ETPU_CISR_A29,        None),
    INTC_EVENT.ETPU_CISR_A30:       (INTC_SRC.ETPU_CISR_A30,        None),
    INTC_EVENT.ETPU_CISR_A31:       (INTC_SRC.ETPU_CISR_A31,        None),
    INTC_EVENT.ETPU_CDTRSR_A0:      (None,                          DMA_REQUEST.ETPU_CDTRSR_A_DTRS0),
    INTC_EVENT.ETPU_CDTRSR_A1:      (None,                          DMA_REQUEST.ETPU_CDTRSR_A_DTRS1),
    INTC_EVENT.ETPU_CDTRSR_A2:      (None,                          DMA_REQUEST.ETPU_CDTRSR_A_DTRS2),
    INTC_EVENT.ETPU_CDTRSR_A3:      (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_A4:      (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_A5:      (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_A6:      (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_A7:      (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_A8:      (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_A9:      (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_A10:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_A11:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_A12:     (None,                          DMA_REQUEST.ETPU_CDTRSR_A_DTRS12),
    INTC_EVENT.ETPU_CDTRSR_A13:     (None,                          DMA_REQUEST.ETPU_CDTRSR_A_DTRS13),
    INTC_EVENT.ETPU_CDTRSR_A14:     (None,                          DMA_REQUEST.ETPU_CDTRSR_A_DTRS14),
    INTC_EVENT.ETPU_CDTRSR_A15:     (None,                          DMA_REQUEST.ETPU_CDTRSR_A_DTRS15),
    INTC_EVENT.ETPU_CDTRSR_A16:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_A17:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_A18:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_A19:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_A20:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_A21:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_A22:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_A23:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_A24:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_A25:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_A26:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_A27:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_A28:     (None,                          DMA_REQUEST.ETPU_CDTRSR_A_DTRS28),
    INTC_EVENT.ETPU_CDTRSR_A29:     (None,                          DMA_REQUEST.ETPU_CDTRSR_A_DTRS29),
    INTC_EVENT.ETPU_CDTRSR_A30:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_A31:     (None,                          None),

    # eTPU B
    INTC_EVENT.ETPU_CISR_B0:        (INTC_SRC.ETPU_CISR_B0,         None),
    INTC_EVENT.ETPU_CISR_B1:        (INTC_SRC.ETPU_CISR_B1,         None),
    INTC_EVENT.ETPU_CISR_B2:        (INTC_SRC.ETPU_CISR_B2,         None),
    INTC_EVENT.ETPU_CISR_B3:        (INTC_SRC.ETPU_CISR_B3,         None),
    INTC_EVENT.ETPU_CISR_B4:        (INTC_SRC.ETPU_CISR_B4,         None),
    INTC_EVENT.ETPU_CISR_B5:        (INTC_SRC.ETPU_CISR_B5,         None),
    INTC_EVENT.ETPU_CISR_B6:        (INTC_SRC.ETPU_CISR_B6,         None),
    INTC_EVENT.ETPU_CISR_B7:        (INTC_SRC.ETPU_CISR_B7,         None),
    INTC_EVENT.ETPU_CISR_B8:        (INTC_SRC.ETPU_CISR_B8,         None),
    INTC_EVENT.ETPU_CISR_B9:        (INTC_SRC.ETPU_CISR_B9,         None),
    INTC_EVENT.ETPU_CISR_B10:       (INTC_SRC.ETPU_CISR_B10,        None),
    INTC_EVENT.ETPU_CISR_B11:       (INTC_SRC.ETPU_CISR_B11,        None),
    INTC_EVENT.ETPU_CISR_B12:       (INTC_SRC.ETPU_CISR_B12,        None),
    INTC_EVENT.ETPU_CISR_B13:       (INTC_SRC.ETPU_CISR_B13,        None),
    INTC_EVENT.ETPU_CISR_B14:       (INTC_SRC.ETPU_CISR_B14,        None),
    INTC_EVENT.ETPU_CISR_B15:       (INTC_SRC.ETPU_CISR_B15,        None),
    INTC_EVENT.ETPU_CISR_B16:       (INTC_SRC.ETPU_CISR_B16,        None),
    INTC_EVENT.ETPU_CISR_B17:       (INTC_SRC.ETPU_CISR_B17,        None),
    INTC_EVENT.ETPU_CISR_B18:       (INTC_SRC.ETPU_CISR_B18,        None),
    INTC_EVENT.ETPU_CISR_B19:       (INTC_SRC.ETPU_CISR_B19,        None),
    INTC_EVENT.ETPU_CISR_B20:       (INTC_SRC.ETPU_CISR_B20,        None),
    INTC_EVENT.ETPU_CISR_B21:       (INTC_SRC.ETPU_CISR_B21,        None),
    INTC_EVENT.ETPU_CISR_B22:       (INTC_SRC.ETPU_CISR_B22,        None),
    INTC_EVENT.ETPU_CISR_B23:       (INTC_SRC.ETPU_CISR_B23,        None),
    INTC_EVENT.ETPU_CISR_B24:       (INTC_SRC.ETPU_CISR_B24,        None),
    INTC_EVENT.ETPU_CISR_B25:       (INTC_SRC.ETPU_CISR_B25,        None),
    INTC_EVENT.ETPU_CISR_B26:       (INTC_SRC.ETPU_CISR_B26,        None),
    INTC_EVENT.ETPU_CISR_B27:       (INTC_SRC.ETPU_CISR_B27,        None),
    INTC_EVENT.ETPU_CISR_B28:       (INTC_SRC.ETPU_CISR_B28,        None),
    INTC_EVENT.ETPU_CISR_B29:       (INTC_SRC.ETPU_CISR_B29,        None),
    INTC_EVENT.ETPU_CISR_B30:       (INTC_SRC.ETPU_CISR_B30,        None),
    INTC_EVENT.ETPU_CISR_B31:       (INTC_SRC.ETPU_CISR_B31,        None),
    INTC_EVENT.ETPU_CDTRSR_B0:      (None,                          DMA_REQUEST.ETPU_CDTRSR_B_DTRS0),
    INTC_EVENT.ETPU_CDTRSR_B1:      (None,                          DMA_REQUEST.ETPU_CDTRSR_B_DTRS1),
    INTC_EVENT.ETPU_CDTRSR_B2:      (None,                          DMA_REQUEST.ETPU_CDTRSR_B_DTRS2),
    INTC_EVENT.ETPU_CDTRSR_B3:      (None,                          DMA_REQUEST.ETPU_CDTRSR_B_DTRS3),
    INTC_EVENT.ETPU_CDTRSR_B4:      (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_B5:      (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_B6:      (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_B7:      (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_B8:      (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_B9:      (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_B10:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_B11:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_B12:     (None,                          DMA_REQUEST.ETPU_CDTRSR_B_DTRS12),
    INTC_EVENT.ETPU_CDTRSR_B13:     (None,                          DMA_REQUEST.ETPU_CDTRSR_B_DTRS13),
    INTC_EVENT.ETPU_CDTRSR_B14:     (None,                          DMA_REQUEST.ETPU_CDTRSR_B_DTRS14),
    INTC_EVENT.ETPU_CDTRSR_B15:     (None,                          DMA_REQUEST.ETPU_CDTRSR_B_DTRS15),
    INTC_EVENT.ETPU_CDTRSR_B16:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_B17:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_B18:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_B19:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_B20:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_B21:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_B22:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_B23:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_B24:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_B25:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_B26:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_B27:     (None,                          None),
    INTC_EVENT.ETPU_CDTRSR_B28:     (None,                          DMA_REQUEST.ETPU_CDTRSR_B_DTRS28),
    INTC_EVENT.ETPU_CDTRSR_B29:     (None,                          DMA_REQUEST.ETPU_CDTRSR_B_DTRS29),
    INTC_EVENT.ETPU_CDTRSR_B30:     (None,                          DMA_REQUEST.ETPU_CDTRSR_B_DTRS30),
    INTC_EVENT.ETPU_CDTRSR_B31:     (None,                          DMA_REQUEST.ETPU_CDTRSR_B_DTRS31),

    # eQADC A
    INTC_EVENT.EQADC_A_TORF:        (INTC_SRC.EQADC_A_OVERRUN,      None),
    INTC_EVENT.EQADC_A_RFOF:        (INTC_SRC.EQADC_A_OVERRUN,      None),
    INTC_EVENT.EQADC_A_CFUF:        (INTC_SRC.EQADC_A_OVERRUN,      None),
    INTC_EVENT.EQADC_A_FISR0_NCF:   (INTC_SRC.EQADC_A_FISR0_NCF,    None),
    INTC_EVENT.EQADC_A_FISR0_PF:    (INTC_SRC.EQADC_A_FISR0_PF,     None),
    INTC_EVENT.EQADC_A_FISR0_EOQF:  (INTC_SRC.EQADC_A_FISR0_EOQF,   None),
    INTC_EVENT.EQADC_A_FISR0_CFFF:  (INTC_SRC.EQADC_A_FISR0_CFFF,   DMA_REQUEST.EQADC_A_FISR0_CFFF),
    INTC_EVENT.EQADC_A_FISR0_RFDF:  (INTC_SRC.EQADC_A_FISR0_RFDF,   DMA_REQUEST.EQADC_A_FISR0_RFDF),
    INTC_EVENT.EQADC_A_FISR1_NCF:   (INTC_SRC.EQADC_A_FISR1_NCF,    None),
    INTC_EVENT.EQADC_A_FISR1_PF:    (INTC_SRC.EQADC_A_FISR1_PF,     None),
    INTC_EVENT.EQADC_A_FISR1_EOQF:  (INTC_SRC.EQADC_A_FISR1_EOQF,   None),
    INTC_EVENT.EQADC_A_FISR1_CFFF:  (INTC_SRC.EQADC_A_FISR1_CFFF,   DMA_REQUEST.EQADC_A_FISR1_CFFF),
    INTC_EVENT.EQADC_A_FISR1_RFDF:  (INTC_SRC.EQADC_A_FISR1_RFDF,   DMA_REQUEST.EQADC_A_FISR1_RFDF),
    INTC_EVENT.EQADC_A_FISR2_NCF:   (INTC_SRC.EQADC_A_FISR2_NCF,    None),
    INTC_EVENT.EQADC_A_FISR2_PF:    (INTC_SRC.EQADC_A_FISR2_PF,     None),
    INTC_EVENT.EQADC_A_FISR2_EOQF:  (INTC_SRC.EQADC_A_FISR2_EOQF,   None),
    INTC_EVENT.EQADC_A_FISR2_CFFF:  (INTC_SRC.EQADC_A_FISR2_CFFF,   DMA_REQUEST.EQADC_A_FISR2_CFFF),
    INTC_EVENT.EQADC_A_FISR2_RFDF:  (INTC_SRC.EQADC_A_FISR2_RFDF,   DMA_REQUEST.EQADC_A_FISR2_RFDF),
    INTC_EVENT.EQADC_A_FISR3_NCF:   (INTC_SRC.EQADC_A_FISR3_NCF,    None),
    INTC_EVENT.EQADC_A_FISR3_PF:    (INTC_SRC.EQADC_A_FISR3_PF,     None),
    INTC_EVENT.EQADC_A_FISR3_EOQF:  (INTC_SRC.EQADC_A_FISR3_EOQF,   None),
    INTC_EVENT.EQADC_A_FISR3_CFFF:  (INTC_SRC.EQADC_A_FISR3_CFFF,   DMA_REQUEST.EQADC_A_FISR3_CFFF),
    INTC_EVENT.EQADC_A_FISR3_RFDF:  (INTC_SRC.EQADC_A_FISR3_RFDF,   DMA_REQUEST.EQADC_A_FISR3_RFDF),
    INTC_EVENT.EQADC_A_FISR4_NCF:   (INTC_SRC.EQADC_A_FISR4_NCF,    None),
    INTC_EVENT.EQADC_A_FISR4_PF:    (INTC_SRC.EQADC_A_FISR4_PF,     None),
    INTC_EVENT.EQADC_A_FISR4_EOQF:  (INTC_SRC.EQADC_A_FISR4_EOQF,   None),
    INTC_EVENT.EQADC_A_FISR4_CFFF:  (INTC_SRC.EQADC_A_FISR4_CFFF,   DMA_REQUEST.EQADC_A_FISR4_CFFF),
    INTC_EVENT.EQADC_A_FISR4_RFDF:  (INTC_SRC.EQADC_A_FISR4_RFDF,   DMA_REQUEST.EQADC_A_FISR4_RFDF),
    INTC_EVENT.EQADC_A_FISR5_NCF:   (INTC_SRC.EQADC_A_FISR5_NCF,    None),
    INTC_EVENT.EQADC_A_FISR5_PF:    (INTC_SRC.EQADC_A_FISR5_PF,     None),
    INTC_EVENT.EQADC_A_FISR5_EOQF:  (INTC_SRC.EQADC_A_FISR5_EOQF,   None),
    INTC_EVENT.EQADC_A_FISR5_CFFF:  (INTC_SRC.EQADC_A_FISR5_CFFF,   DMA_REQUEST.EQADC_A_FISR5_CFFF),
    INTC_EVENT.EQADC_A_FISR5_RFDF:  (INTC_SRC.EQADC_A_FISR5_RFDF,   DMA_REQUEST.EQADC_A_FISR5_RFDF),

    # eQADC B
    INTC_EVENT.EQADC_B_TORF:        (INTC_SRC.EQADC_B_OVERRUN,      None),
    INTC_EVENT.EQADC_B_RFOF:        (INTC_SRC.EQADC_B_OVERRUN,      None),
    INTC_EVENT.EQADC_B_CFUF:        (INTC_SRC.EQADC_B_OVERRUN,      None),
    INTC_EVENT.EQADC_B_FISR0_NCF:   (INTC_SRC.EQADC_B_FISR0_NCF,    None),
    INTC_EVENT.EQADC_B_FISR0_PF:    (INTC_SRC.EQADC_B_FISR0_PF,     None),
    INTC_EVENT.EQADC_B_FISR0_EOQF:  (INTC_SRC.EQADC_B_FISR0_EOQF,   None),
    INTC_EVENT.EQADC_B_FISR0_CFFF:  (INTC_SRC.EQADC_B_FISR0_CFFF,   DMA_REQUEST.EQADC_B_FISR0_CFFF),
    INTC_EVENT.EQADC_B_FISR0_RFDF:  (INTC_SRC.EQADC_B_FISR0_RFDF,   DMA_REQUEST.EQADC_B_FISR0_RFDF),
    INTC_EVENT.EQADC_B_FISR1_NCF:   (INTC_SRC.EQADC_B_FISR1_NCF,    None),
    INTC_EVENT.EQADC_B_FISR1_PF:    (INTC_SRC.EQADC_B_FISR1_PF,     None),
    INTC_EVENT.EQADC_B_FISR1_EOQF:  (INTC_SRC.EQADC_B_FISR1_EOQF,   None),
    INTC_EVENT.EQADC_B_FISR1_CFFF:  (INTC_SRC.EQADC_B_FISR1_CFFF,   DMA_REQUEST.EQADC_B_FISR1_CFFF),
    INTC_EVENT.EQADC_B_FISR1_RFDF:  (INTC_SRC.EQADC_B_FISR1_RFDF,   DMA_REQUEST.EQADC_B_FISR1_RFDF),
    INTC_EVENT.EQADC_B_FISR2_NCF:   (INTC_SRC.EQADC_B_FISR2_NCF,    None),
    INTC_EVENT.EQADC_B_FISR2_PF:    (INTC_SRC.EQADC_B_FISR2_PF,     None),
    INTC_EVENT.EQADC_B_FISR2_EOQF:  (INTC_SRC.EQADC_B_FISR2_EOQF,   None),
    INTC_EVENT.EQADC_B_FISR2_CFFF:  (INTC_SRC.EQADC_B_FISR2_CFFF,   DMA_REQUEST.EQADC_B_FISR2_CFFF),
    INTC_EVENT.EQADC_B_FISR2_RFDF:  (INTC_SRC.EQADC_B_FISR2_RFDF,   DMA_REQUEST.EQADC_B_FISR2_RFDF),
    INTC_EVENT.EQADC_B_FISR3_NCF:   (INTC_SRC.EQADC_B_FISR3_NCF,    None),
    INTC_EVENT.EQADC_B_FISR3_PF:    (INTC_SRC.EQADC_B_FISR3_PF,     None),
    INTC_EVENT.EQADC_B_FISR3_EOQF:  (INTC_SRC.EQADC_B_FISR3_EOQF,   None),
    INTC_EVENT.EQADC_B_FISR3_CFFF:  (INTC_SRC.EQADC_B_FISR3_CFFF,   DMA_REQUEST.EQADC_B_FISR3_CFFF),
    INTC_EVENT.EQADC_B_FISR3_RFDF:  (INTC_SRC.EQADC_B_FISR3_RFDF,   DMA_REQUEST.EQADC_B_FISR3_RFDF),
    INTC_EVENT.EQADC_B_FISR4_NCF:   (INTC_SRC.EQADC_B_FISR4_NCF,    None),
    INTC_EVENT.EQADC_B_FISR4_PF:    (INTC_SRC.EQADC_B_FISR4_PF,     None),
    INTC_EVENT.EQADC_B_FISR4_EOQF:  (INTC_SRC.EQADC_B_FISR4_EOQF,   None),
    INTC_EVENT.EQADC_B_FISR4_CFFF:  (INTC_SRC.EQADC_B_FISR4_CFFF,   DMA_REQUEST.EQADC_B_FISR4_CFFF),
    INTC_EVENT.EQADC_B_FISR4_RFDF:  (INTC_SRC.EQADC_B_FISR4_RFDF,   DMA_REQUEST.EQADC_B_FISR4_RFDF),
    INTC_EVENT.EQADC_B_FISR5_NCF:   (INTC_SRC.EQADC_B_FISR5_NCF,    None),
    INTC_EVENT.EQADC_B_FISR5_PF:    (INTC_SRC.EQADC_B_FISR5_PF,     None),
    INTC_EVENT.EQADC_B_FISR5_EOQF:  (INTC_SRC.EQADC_B_FISR5_EOQF,   None),
    INTC_EVENT.EQADC_B_FISR5_CFFF:  (INTC_SRC.EQADC_B_FISR5_CFFF,   DMA_REQUEST.EQADC_B_FISR5_CFFF),
    INTC_EVENT.EQADC_B_FISR5_RFDF:  (INTC_SRC.EQADC_B_FISR5_RFDF,   DMA_REQUEST.EQADC_B_FISR5_RFDF),

    # DSPI A
    INTC_EVENT.DSPI_A_TFUF:         (INTC_SRC.DSPI_A_OVERRUN,       None),
    INTC_EVENT.DSPI_A_RFOF:         (INTC_SRC.DSPI_A_OVERRUN,       None),
    INTC_EVENT.DSPI_A_TX_EOQ:       (INTC_SRC.DSPI_A_TX_EOQ,        None),
    INTC_EVENT.DSPI_A_TX_FILL:      (INTC_SRC.DSPI_A_TX_FILL,       DMA_REQUEST.DSPIA_SR_TFFF),
    INTC_EVENT.DSPI_A_TX_CMPLT:     (INTC_SRC.DSPI_A_TX_CMPLT,      None),
    INTC_EVENT.DSPI_A_RX_DRAIN:     (INTC_SRC.DSPI_A_RX_DRAIN,      DMA_REQUEST.DSPIA_SR_RFDF),

    # DSPI B
    INTC_EVENT.DSPI_B_TFUF:         (INTC_SRC.DSPI_B_OVERRUN,       None),
    INTC_EVENT.DSPI_B_RFOF:         (INTC_SRC.DSPI_B_OVERRUN,       None),
    INTC_EVENT.DSPI_B_TX_EOQ:       (INTC_SRC.DSPI_B_TX_EOQ,        None),
    INTC_EVENT.DSPI_B_TX_FILL:      (INTC_SRC.DSPI_B_TX_FILL,       DMA_REQUEST.DSPIB_SR_TFFF),
    INTC_EVENT.DSPI_B_TX_CMPLT:     (INTC_SRC.DSPI_B_TX_CMPLT,      None),
    INTC_EVENT.DSPI_B_RX_DRAIN:     (INTC_SRC.DSPI_B_RX_DRAIN,      DMA_REQUEST.DSPIB_SR_RFDF),

    # DSPI C
    INTC_EVENT.DSPI_C_TFUF:         (INTC_SRC.DSPI_C_OVERRUN,       None),
    INTC_EVENT.DSPI_C_RFOF:         (INTC_SRC.DSPI_C_OVERRUN,       None),
    INTC_EVENT.DSPI_C_TX_EOQ:       (INTC_SRC.DSPI_C_TX_EOQ,        None),
    INTC_EVENT.DSPI_C_TX_FILL:      (INTC_SRC.DSPI_C_TX_FILL,       DMA_REQUEST.DSPIC_SR_TFFF),
    INTC_EVENT.DSPI_C_TX_CMPLT:     (INTC_SRC.DSPI_C_TX_CMPLT,      None),
    INTC_EVENT.DSPI_C_RX_DRAIN:     (INTC_SRC.DSPI_C_RX_DRAIN,      DMA_REQUEST.DSPIC_SR_RFDF),

    # DSPI D
    INTC_EVENT.DSPI_D_TFUF:         (INTC_SRC.DSPI_D_OVERRUN,       None),
    INTC_EVENT.DSPI_D_RFOF:         (INTC_SRC.DSPI_D_OVERRUN,       None),
    INTC_EVENT.DSPI_D_TX_EOQ:       (INTC_SRC.DSPI_D_TX_EOQ,        None),
    INTC_EVENT.DSPI_D_TX_FILL:      (INTC_SRC.DSPI_D_TX_FILL,       DMA_REQUEST.DSPID_SR_TFFF),
    INTC_EVENT.DSPI_D_TX_CMPLT:     (INTC_SRC.DSPI_D_TX_CMPLT,      None),
    INTC_EVENT.DSPI_D_RX_DRAIN:     (INTC_SRC.DSPI_D_RX_DRAIN,      DMA_REQUEST.DSPID_SR_RFDF),

    # eSCI A
    INTC_EVENT.ESCIA_IFSR1_TDRE:    (INTC_SRC.ESCIA,                DMA_REQUEST.ESCIA_COMBTX),
    INTC_EVENT.ESCIA_IFSR1_TC:      (INTC_SRC.ESCIA,                DMA_REQUEST.ESCIA_COMBTX),
    INTC_EVENT.ESCIA_IFSR1_RDRF:    (INTC_SRC.ESCIA,                DMA_REQUEST.ESCIA_COMBRX),
    INTC_EVENT.ESCIA_IFSR1_IDLE:    (INTC_SRC.ESCIA,                None),
    INTC_EVENT.ESCIA_IFSR1_OR:      (INTC_SRC.ESCIA,                None),
    INTC_EVENT.ESCIA_IFSR1_NF:      (INTC_SRC.ESCIA,                None),
    INTC_EVENT.ESCIA_IFSR1_FE:      (INTC_SRC.ESCIA,                None),
    INTC_EVENT.ESCIA_IFSR1_PF:      (INTC_SRC.ESCIA,                None),
    INTC_EVENT.ESCIA_IFSR1_BERR:    (INTC_SRC.ESCIA,                None),
    INTC_EVENT.ESCIA_IFSR2_RXRDY:   (INTC_SRC.ESCIA,                DMA_REQUEST.ESCIA_COMBRX),
    INTC_EVENT.ESCIA_IFSR2_TXRDY:   (INTC_SRC.ESCIA,                DMA_REQUEST.ESCIA_COMBTX),
    INTC_EVENT.ESCIA_IFSR2_LWAKE:   (INTC_SRC.ESCIA,                None),
    INTC_EVENT.ESCIA_IFSR2_STO:     (INTC_SRC.ESCIA,                None),
    INTC_EVENT.ESCIA_IFSR2_PBERR:   (INTC_SRC.ESCIA,                None),
    INTC_EVENT.ESCIA_IFSR2_CERR:    (INTC_SRC.ESCIA,                None),
    INTC_EVENT.ESCIA_IFSR2_CKERR:   (INTC_SRC.ESCIA,                None),
    INTC_EVENT.ESCIA_IFSR2_FRC:     (INTC_SRC.ESCIA,                None),
    INTC_EVENT.ESCIA_IFSR2_OVFL:    (INTC_SRC.ESCIA,                None),
    INTC_EVENT.ESCIA_IFSR2_UREQ:    (INTC_SRC.ESCIA,                None),

    # eSCI B
    INTC_EVENT.ESCIB_IFSR1_TDRE:    (INTC_SRC.ESCIB,                DMA_REQUEST.ESCIB_COMBTX),
    INTC_EVENT.ESCIB_IFSR1_TC:      (INTC_SRC.ESCIB,                DMA_REQUEST.ESCIB_COMBTX),
    INTC_EVENT.ESCIB_IFSR1_RDRF:    (INTC_SRC.ESCIB,                DMA_REQUEST.ESCIB_COMBRX),
    INTC_EVENT.ESCIB_IFSR1_IDLE:    (INTC_SRC.ESCIB,                None),
    INTC_EVENT.ESCIB_IFSR1_OR:      (INTC_SRC.ESCIB,                None),
    INTC_EVENT.ESCIB_IFSR1_NF:      (INTC_SRC.ESCIB,                None),
    INTC_EVENT.ESCIB_IFSR1_FE:      (INTC_SRC.ESCIB,                None),
    INTC_EVENT.ESCIB_IFSR1_PF:      (INTC_SRC.ESCIB,                None),
    INTC_EVENT.ESCIB_IFSR1_BERR:    (INTC_SRC.ESCIB,                None),
    INTC_EVENT.ESCIB_IFSR2_RXRDY:   (INTC_SRC.ESCIB,                DMA_REQUEST.ESCIB_COMBRX),
    INTC_EVENT.ESCIB_IFSR2_TXRDY:   (INTC_SRC.ESCIB,                DMA_REQUEST.ESCIB_COMBTX),
    INTC_EVENT.ESCIB_IFSR2_LWAKE:   (INTC_SRC.ESCIB,                None),
    INTC_EVENT.ESCIB_IFSR2_STO:     (INTC_SRC.ESCIB,                None),
    INTC_EVENT.ESCIB_IFSR2_PBERR:   (INTC_SRC.ESCIB,                None),
    INTC_EVENT.ESCIB_IFSR2_CERR:    (INTC_SRC.ESCIB,                None),
    INTC_EVENT.ESCIB_IFSR2_CKERR:   (INTC_SRC.ESCIB,                None),
    INTC_EVENT.ESCIB_IFSR2_FRC:     (INTC_SRC.ESCIB,                None),
    INTC_EVENT.ESCIB_IFSR2_OVFL:    (INTC_SRC.ESCIB,                None),
    INTC_EVENT.ESCIB_IFSR2_UREQ:    (INTC_SRC.ESCIB,                None),

    # eSCI C
    INTC_EVENT.ESCIC_IFSR1_TDRE:    (INTC_SRC.ESCIC,                None),
    INTC_EVENT.ESCIC_IFSR1_TC:      (INTC_SRC.ESCIC,                None),
    INTC_EVENT.ESCIC_IFSR1_RDRF:    (INTC_SRC.ESCIC,                None),
    INTC_EVENT.ESCIC_IFSR1_IDLE:    (INTC_SRC.ESCIC,                None),
    INTC_EVENT.ESCIC_IFSR1_OR:      (INTC_SRC.ESCIC,                None),
    INTC_EVENT.ESCIC_IFSR1_NF:      (INTC_SRC.ESCIC,                None),
    INTC_EVENT.ESCIC_IFSR1_FE:      (INTC_SRC.ESCIC,                None),
    INTC_EVENT.ESCIC_IFSR1_PF:      (INTC_SRC.ESCIC,                None),
    INTC_EVENT.ESCIC_IFSR1_BERR:    (INTC_SRC.ESCIC,                None),
    INTC_EVENT.ESCIC_IFSR2_RXRDY:   (INTC_SRC.ESCIC,                None),
    INTC_EVENT.ESCIC_IFSR2_TXRDY:   (INTC_SRC.ESCIC,                None),
    INTC_EVENT.ESCIC_IFSR2_LWAKE:   (INTC_SRC.ESCIC,                None),
    INTC_EVENT.ESCIC_IFSR2_STO:     (INTC_SRC.ESCIC,                None),
    INTC_EVENT.ESCIC_IFSR2_PBERR:   (INTC_SRC.ESCIC,                None),
    INTC_EVENT.ESCIC_IFSR2_CERR:    (INTC_SRC.ESCIC,                None),
    INTC_EVENT.ESCIC_IFSR2_CKERR:   (INTC_SRC.ESCIC,                None),
    INTC_EVENT.ESCIC_IFSR2_FRC:     (INTC_SRC.ESCIC,                None),
    INTC_EVENT.ESCIC_IFSR2_OVFL:    (INTC_SRC.ESCIC,                None),
    INTC_EVENT.ESCIC_IFSR2_UREQ:    (INTC_SRC.ESCIC,                None),

    # FlexCAN A
    INTC_EVENT.CANA_ESR_BOFF:       (INTC_SRC.CANA_BUS,             None),
    INTC_EVENT.CANA_ESR_TWRN:       (INTC_SRC.CANA_BUS,             None),
    INTC_EVENT.CANA_ESR_RWRN:       (INTC_SRC.CANA_BUS,             None),
    INTC_EVENT.CANA_ESR_ERR:        (INTC_SRC.CANA_ERR,             None),
    INTC_EVENT.CANA_MB0:            (INTC_SRC.CANA_MB0,             None),
    INTC_EVENT.CANA_MB1:            (INTC_SRC.CANA_MB1,             None),
    INTC_EVENT.CANA_MB2:            (INTC_SRC.CANA_MB2,             None),
    INTC_EVENT.CANA_MB3:            (INTC_SRC.CANA_MB3,             None),
    INTC_EVENT.CANA_MB4:            (INTC_SRC.CANA_MB4,             None),
    INTC_EVENT.CANA_MB5:            (INTC_SRC.CANA_MB5,             None),
    INTC_EVENT.CANA_MB6:            (INTC_SRC.CANA_MB6,             None),
    INTC_EVENT.CANA_MB7:            (INTC_SRC.CANA_MB7,             None),
    INTC_EVENT.CANA_MB8:            (INTC_SRC.CANA_MB8,             None),
    INTC_EVENT.CANA_MB9:            (INTC_SRC.CANA_MB9,             None),
    INTC_EVENT.CANA_MB10:           (INTC_SRC.CANA_MB10,            None),
    INTC_EVENT.CANA_MB11:           (INTC_SRC.CANA_MB11,            None),
    INTC_EVENT.CANA_MB12:           (INTC_SRC.CANA_MB12,            None),
    INTC_EVENT.CANA_MB13:           (INTC_SRC.CANA_MB13,            None),
    INTC_EVENT.CANA_MB14:           (INTC_SRC.CANA_MB14,            None),
    INTC_EVENT.CANA_MB15:           (INTC_SRC.CANA_MB15,            None),
    INTC_EVENT.CANA_MB16:           (INTC_SRC.CANA_MB16_31,         None),
    INTC_EVENT.CANA_MB17:           (INTC_SRC.CANA_MB16_31,         None),
    INTC_EVENT.CANA_MB18:           (INTC_SRC.CANA_MB16_31,         None),
    INTC_EVENT.CANA_MB19:           (INTC_SRC.CANA_MB16_31,         None),
    INTC_EVENT.CANA_MB20:           (INTC_SRC.CANA_MB16_31,         None),
    INTC_EVENT.CANA_MB21:           (INTC_SRC.CANA_MB16_31,         None),
    INTC_EVENT.CANA_MB22:           (INTC_SRC.CANA_MB16_31,         None),
    INTC_EVENT.CANA_MB23:           (INTC_SRC.CANA_MB16_31,         None),
    INTC_EVENT.CANA_MB24:           (INTC_SRC.CANA_MB16_31,         None),
    INTC_EVENT.CANA_MB25:           (INTC_SRC.CANA_MB16_31,         None),
    INTC_EVENT.CANA_MB26:           (INTC_SRC.CANA_MB16_31,         None),
    INTC_EVENT.CANA_MB27:           (INTC_SRC.CANA_MB16_31,         None),
    INTC_EVENT.CANA_MB28:           (INTC_SRC.CANA_MB16_31,         None),
    INTC_EVENT.CANA_MB29:           (INTC_SRC.CANA_MB16_31,         None),
    INTC_EVENT.CANA_MB30:           (INTC_SRC.CANA_MB16_31,         None),
    INTC_EVENT.CANA_MB31:           (INTC_SRC.CANA_MB16_31,         None),
    INTC_EVENT.CANA_MB32:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB33:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB34:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB35:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB36:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB37:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB38:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB39:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB40:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB41:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB42:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB43:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB44:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB45:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB46:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB47:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB48:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB49:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB50:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB51:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB52:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB53:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB54:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB55:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB56:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB57:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB58:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB59:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB60:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB61:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB62:           (INTC_SRC.CANA_MB32_63,         None),
    INTC_EVENT.CANA_MB63:           (INTC_SRC.CANA_MB32_63,         None),

    # FlexCAN B
    INTC_EVENT.CANB_ESR_BOFF:       (INTC_SRC.CANB_BUS,             None),
    INTC_EVENT.CANB_ESR_TWRN:       (INTC_SRC.CANB_BUS,             None),
    INTC_EVENT.CANB_ESR_RWRN:       (INTC_SRC.CANB_BUS,             None),
    INTC_EVENT.CANB_ESR_ERR:        (INTC_SRC.CANB_ERR,             None),
    INTC_EVENT.CANB_MB0:            (INTC_SRC.CANB_MB0,             None),
    INTC_EVENT.CANB_MB1:            (INTC_SRC.CANB_MB1,             None),
    INTC_EVENT.CANB_MB2:            (INTC_SRC.CANB_MB2,             None),
    INTC_EVENT.CANB_MB3:            (INTC_SRC.CANB_MB3,             None),
    INTC_EVENT.CANB_MB4:            (INTC_SRC.CANB_MB4,             None),
    INTC_EVENT.CANB_MB5:            (INTC_SRC.CANB_MB5,             None),
    INTC_EVENT.CANB_MB6:            (INTC_SRC.CANB_MB6,             None),
    INTC_EVENT.CANB_MB7:            (INTC_SRC.CANB_MB7,             None),
    INTC_EVENT.CANB_MB8:            (INTC_SRC.CANB_MB8,             None),
    INTC_EVENT.CANB_MB9:            (INTC_SRC.CANB_MB9,             None),
    INTC_EVENT.CANB_MB10:           (INTC_SRC.CANB_MB10,            None),
    INTC_EVENT.CANB_MB11:           (INTC_SRC.CANB_MB11,            None),
    INTC_EVENT.CANB_MB12:           (INTC_SRC.CANB_MB12,            None),
    INTC_EVENT.CANB_MB13:           (INTC_SRC.CANB_MB13,            None),
    INTC_EVENT.CANB_MB14:           (INTC_SRC.CANB_MB14,            None),
    INTC_EVENT.CANB_MB15:           (INTC_SRC.CANB_MB15,            None),
    INTC_EVENT.CANB_MB16:           (INTC_SRC.CANB_MB16_31,         None),
    INTC_EVENT.CANB_MB17:           (INTC_SRC.CANB_MB16_31,         None),
    INTC_EVENT.CANB_MB18:           (INTC_SRC.CANB_MB16_31,         None),
    INTC_EVENT.CANB_MB19:           (INTC_SRC.CANB_MB16_31,         None),
    INTC_EVENT.CANB_MB20:           (INTC_SRC.CANB_MB16_31,         None),
    INTC_EVENT.CANB_MB21:           (INTC_SRC.CANB_MB16_31,         None),
    INTC_EVENT.CANB_MB22:           (INTC_SRC.CANB_MB16_31,         None),
    INTC_EVENT.CANB_MB23:           (INTC_SRC.CANB_MB16_31,         None),
    INTC_EVENT.CANB_MB24:           (INTC_SRC.CANB_MB16_31,         None),
    INTC_EVENT.CANB_MB25:           (INTC_SRC.CANB_MB16_31,         None),
    INTC_EVENT.CANB_MB26:           (INTC_SRC.CANB_MB16_31,         None),
    INTC_EVENT.CANB_MB27:           (INTC_SRC.CANB_MB16_31,         None),
    INTC_EVENT.CANB_MB28:           (INTC_SRC.CANB_MB16_31,         None),
    INTC_EVENT.CANB_MB29:           (INTC_SRC.CANB_MB16_31,         None),
    INTC_EVENT.CANB_MB30:           (INTC_SRC.CANB_MB16_31,         None),
    INTC_EVENT.CANB_MB31:           (INTC_SRC.CANB_MB16_31,         None),
    INTC_EVENT.CANB_MB32:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB33:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB34:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB35:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB36:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB37:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB38:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB39:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB40:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB41:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB42:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB43:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB44:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB45:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB46:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB47:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB48:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB49:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB50:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB51:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB52:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB53:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB54:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB55:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB56:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB57:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB58:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB59:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB60:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB61:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB62:           (INTC_SRC.CANB_MB32_63,         None),
    INTC_EVENT.CANB_MB63:           (INTC_SRC.CANB_MB32_63,         None),

    # FlexCAN C
    INTC_EVENT.CANC_ESR_BOFF:       (INTC_SRC.CANC_BUS,             None),
    INTC_EVENT.CANC_ESR_TWRN:       (INTC_SRC.CANC_BUS,             None),
    INTC_EVENT.CANC_ESR_RWRN:       (INTC_SRC.CANC_BUS,             None),
    INTC_EVENT.CANC_ESR_ERR:        (INTC_SRC.CANC_ERR,             None),
    INTC_EVENT.CANC_MB0:            (INTC_SRC.CANC_MB0,             None),
    INTC_EVENT.CANC_MB1:            (INTC_SRC.CANC_MB1,             None),
    INTC_EVENT.CANC_MB2:            (INTC_SRC.CANC_MB2,             None),
    INTC_EVENT.CANC_MB3:            (INTC_SRC.CANC_MB3,             None),
    INTC_EVENT.CANC_MB4:            (INTC_SRC.CANC_MB4,             None),
    INTC_EVENT.CANC_MB5:            (INTC_SRC.CANC_MB5,             None),
    INTC_EVENT.CANC_MB6:            (INTC_SRC.CANC_MB6,             None),
    INTC_EVENT.CANC_MB7:            (INTC_SRC.CANC_MB7,             None),
    INTC_EVENT.CANC_MB8:            (INTC_SRC.CANC_MB8,             None),
    INTC_EVENT.CANC_MB9:            (INTC_SRC.CANC_MB9,             None),
    INTC_EVENT.CANC_MB10:           (INTC_SRC.CANC_MB10,            None),
    INTC_EVENT.CANC_MB11:           (INTC_SRC.CANC_MB11,            None),
    INTC_EVENT.CANC_MB12:           (INTC_SRC.CANC_MB12,            None),
    INTC_EVENT.CANC_MB13:           (INTC_SRC.CANC_MB13,            None),
    INTC_EVENT.CANC_MB14:           (INTC_SRC.CANC_MB14,            None),
    INTC_EVENT.CANC_MB15:           (INTC_SRC.CANC_MB15,            None),
    INTC_EVENT.CANC_MB16:           (INTC_SRC.CANC_MB16_31,         None),
    INTC_EVENT.CANC_MB17:           (INTC_SRC.CANC_MB16_31,         None),
    INTC_EVENT.CANC_MB18:           (INTC_SRC.CANC_MB16_31,         None),
    INTC_EVENT.CANC_MB19:           (INTC_SRC.CANC_MB16_31,         None),
    INTC_EVENT.CANC_MB20:           (INTC_SRC.CANC_MB16_31,         None),
    INTC_EVENT.CANC_MB21:           (INTC_SRC.CANC_MB16_31,         None),
    INTC_EVENT.CANC_MB22:           (INTC_SRC.CANC_MB16_31,         None),
    INTC_EVENT.CANC_MB23:           (INTC_SRC.CANC_MB16_31,         None),
    INTC_EVENT.CANC_MB24:           (INTC_SRC.CANC_MB16_31,         None),
    INTC_EVENT.CANC_MB25:           (INTC_SRC.CANC_MB16_31,         None),
    INTC_EVENT.CANC_MB26:           (INTC_SRC.CANC_MB16_31,         None),
    INTC_EVENT.CANC_MB27:           (INTC_SRC.CANC_MB16_31,         None),
    INTC_EVENT.CANC_MB28:           (INTC_SRC.CANC_MB16_31,         None),
    INTC_EVENT.CANC_MB29:           (INTC_SRC.CANC_MB16_31,         None),
    INTC_EVENT.CANC_MB30:           (INTC_SRC.CANC_MB16_31,         None),
    INTC_EVENT.CANC_MB31:           (INTC_SRC.CANC_MB16_31,         None),
    INTC_EVENT.CANC_MB32:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB33:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB34:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB35:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB36:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB37:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB38:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB39:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB40:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB41:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB42:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB43:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB44:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB45:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB46:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB47:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB48:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB49:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB50:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB51:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB52:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB53:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB54:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB55:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB56:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB57:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB58:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB59:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB60:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB61:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB62:           (INTC_SRC.CANC_MB32_63,         None),
    INTC_EVENT.CANC_MB63:           (INTC_SRC.CANC_MB32_63,         None),

    # FlexCAN D
    INTC_EVENT.CAND_ESR_BOFF:       (INTC_SRC.CAND_BUS,             None),
    INTC_EVENT.CAND_ESR_TWRN:       (INTC_SRC.CAND_BUS,             None),
    INTC_EVENT.CAND_ESR_RWRN:       (INTC_SRC.CAND_BUS,             None),
    INTC_EVENT.CAND_ESR_ERR:        (INTC_SRC.CAND_ERR,             None),
    INTC_EVENT.CAND_MB0:            (INTC_SRC.CAND_MB0,             None),
    INTC_EVENT.CAND_MB1:            (INTC_SRC.CAND_MB1,             None),
    INTC_EVENT.CAND_MB2:            (INTC_SRC.CAND_MB2,             None),
    INTC_EVENT.CAND_MB3:            (INTC_SRC.CAND_MB3,             None),
    INTC_EVENT.CAND_MB4:            (INTC_SRC.CAND_MB4,             None),
    INTC_EVENT.CAND_MB5:            (INTC_SRC.CAND_MB5,             None),
    INTC_EVENT.CAND_MB6:            (INTC_SRC.CAND_MB6,             None),
    INTC_EVENT.CAND_MB7:            (INTC_SRC.CAND_MB7,             None),
    INTC_EVENT.CAND_MB8:            (INTC_SRC.CAND_MB8,             None),
    INTC_EVENT.CAND_MB9:            (INTC_SRC.CAND_MB9,             None),
    INTC_EVENT.CAND_MB10:           (INTC_SRC.CAND_MB10,            None),
    INTC_EVENT.CAND_MB11:           (INTC_SRC.CAND_MB11,            None),
    INTC_EVENT.CAND_MB12:           (INTC_SRC.CAND_MB12,            None),
    INTC_EVENT.CAND_MB13:           (INTC_SRC.CAND_MB13,            None),
    INTC_EVENT.CAND_MB14:           (INTC_SRC.CAND_MB14,            None),
    INTC_EVENT.CAND_MB15:           (INTC_SRC.CAND_MB15,            None),
    INTC_EVENT.CAND_MB16:           (INTC_SRC.CAND_MB16_31,         None),
    INTC_EVENT.CAND_MB17:           (INTC_SRC.CAND_MB16_31,         None),
    INTC_EVENT.CAND_MB18:           (INTC_SRC.CAND_MB16_31,         None),
    INTC_EVENT.CAND_MB19:           (INTC_SRC.CAND_MB16_31,         None),
    INTC_EVENT.CAND_MB20:           (INTC_SRC.CAND_MB16_31,         None),
    INTC_EVENT.CAND_MB21:           (INTC_SRC.CAND_MB16_31,         None),
    INTC_EVENT.CAND_MB22:           (INTC_SRC.CAND_MB16_31,         None),
    INTC_EVENT.CAND_MB23:           (INTC_SRC.CAND_MB16_31,         None),
    INTC_EVENT.CAND_MB24:           (INTC_SRC.CAND_MB16_31,         None),
    INTC_EVENT.CAND_MB25:           (INTC_SRC.CAND_MB16_31,         None),
    INTC_EVENT.CAND_MB26:           (INTC_SRC.CAND_MB16_31,         None),
    INTC_EVENT.CAND_MB27:           (INTC_SRC.CAND_MB16_31,         None),
    INTC_EVENT.CAND_MB28:           (INTC_SRC.CAND_MB16_31,         None),
    INTC_EVENT.CAND_MB29:           (INTC_SRC.CAND_MB16_31,         None),
    INTC_EVENT.CAND_MB30:           (INTC_SRC.CAND_MB16_31,         None),
    INTC_EVENT.CAND_MB31:           (INTC_SRC.CAND_MB16_31,         None),
    INTC_EVENT.CAND_MB32:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB33:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB34:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB35:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB36:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB37:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB38:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB39:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB40:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB41:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB42:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB43:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB44:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB45:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB46:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB47:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB48:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB49:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB50:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB51:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB52:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB53:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB54:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB55:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB56:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB57:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB58:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB59:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB60:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB61:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB62:           (INTC_SRC.CAND_MB32_63,         None),
    INTC_EVENT.CAND_MB63:           (INTC_SRC.CAND_MB32_63,         None),

    # Decimation Filter A
    INTC_EVENT.DECA_MSR_IDF:        (None,                          None),
    INTC_EVENT.DECA_MSR_ODF:        (None,                          None),
    INTC_EVENT.DECA_MSR_IBIF:       (INTC_SRC.DEC_A_FILL,           DMA_REQUEST.DECFILTERA_IB),
    INTC_EVENT.DECA_MSR_OBIF:       (INTC_SRC.DEC_A_DRAIN,          DMA_REQUEST.DECFILTERA_OB),
    INTC_EVENT.DECA_MSR_DIVR:       (INTC_SRC.DEC_A_ERROR,          None),
    INTC_EVENT.DECA_MSR_OVR:        (INTC_SRC.DEC_A_ERROR,          None),
    INTC_EVENT.DECA_MSR_IVR:        (INTC_SRC.DEC_A_ERROR,          None),

    # Decimation Filter B
    INTC_EVENT.DECB_MSR_IDF:        (None,                          None),
    INTC_EVENT.DECB_MSR_ODF:        (None,                          None),
    INTC_EVENT.DECB_MSR_IBIF:       (INTC_SRC.DEC_A_FILL,           DMA_REQUEST.DECFILTERB_IB),
    INTC_EVENT.DECB_MSR_OBIF:       (INTC_SRC.DEC_A_DRAIN,          DMA_REQUEST.DECFILTERB_OB),
    INTC_EVENT.DECB_MSR_DIVR:       (INTC_SRC.DEC_A_ERROR,          None),
    INTC_EVENT.DECB_MSR_OVR:        (INTC_SRC.DEC_A_ERROR,          None),
    INTC_EVENT.DECB_MSR_IVR:        (INTC_SRC.DEC_A_ERROR,          None),

    # Decimation Filter C
    INTC_EVENT.DECC_MSR_IDF:        (None,                          None),
    INTC_EVENT.DECC_MSR_ODF:        (None,                          None),
    INTC_EVENT.DECC_MSR_IBIF:       (INTC_SRC.DEC_A_FILL,           DMA_REQUEST.DECFILTERC_IB),
    INTC_EVENT.DECC_MSR_OBIF:       (INTC_SRC.DEC_A_DRAIN,          DMA_REQUEST.DECFILTERC_OB),
    INTC_EVENT.DECC_MSR_DIVR:       (INTC_SRC.DEC_A_ERROR,          None),
    INTC_EVENT.DECC_MSR_OVR:        (INTC_SRC.DEC_A_ERROR,          None),
    INTC_EVENT.DECC_MSR_IVR:        (INTC_SRC.DEC_A_ERROR,          None),

    # Decimation Filter D
    INTC_EVENT.DECD_MSR_IDF:        (None,                          None),
    INTC_EVENT.DECD_MSR_ODF:        (None,                          None),
    INTC_EVENT.DECD_MSR_IBIF:       (INTC_SRC.DEC_A_FILL,           DMA_REQUEST.DECFILTERD_IB),
    INTC_EVENT.DECD_MSR_OBIF:       (INTC_SRC.DEC_A_DRAIN,          DMA_REQUEST.DECFILTERD_OB),
    INTC_EVENT.DECD_MSR_DIVR:       (INTC_SRC.DEC_A_ERROR,          None),
    INTC_EVENT.DECD_MSR_OVR:        (INTC_SRC.DEC_A_ERROR,          None),
    INTC_EVENT.DECD_MSR_IVR:        (INTC_SRC.DEC_A_ERROR,          None),

    # Decimation Filter E
    INTC_EVENT.DECE_MSR_IDF:        (None,                          None),
    INTC_EVENT.DECE_MSR_ODF:        (None,                          None),
    INTC_EVENT.DECE_MSR_IBIF:       (INTC_SRC.DEC_E,                DMA_REQUEST.DECFILTERE_IB),
    INTC_EVENT.DECE_MSR_OBIF:       (INTC_SRC.DEC_E,                DMA_REQUEST.DECFILTERE_OB),
    INTC_EVENT.DECE_MSR_DIVR:       (INTC_SRC.DEC_E,                None),
    INTC_EVENT.DECE_MSR_OVR:        (INTC_SRC.DEC_E,                None),
    INTC_EVENT.DECE_MSR_IVR:        (INTC_SRC.DEC_E,                None),

    # Decimation Filter F
    INTC_EVENT.DECF_MSR_IDF:        (None,                          None),
    INTC_EVENT.DECF_MSR_ODF:        (None,                          None),
    INTC_EVENT.DECF_MSR_IBIF:       (INTC_SRC.DEC_F,                DMA_REQUEST.DECFILTERF_IB),
    INTC_EVENT.DECF_MSR_OBIF:       (INTC_SRC.DEC_F,                DMA_REQUEST.DECFILTERF_OB),
    INTC_EVENT.DECF_MSR_DIVR:       (INTC_SRC.DEC_F,                None),
    INTC_EVENT.DECF_MSR_OVR:        (INTC_SRC.DEC_F,                None),
    INTC_EVENT.DECF_MSR_IVR:        (INTC_SRC.DEC_F,                None),

    # Decimation Filter G
    INTC_EVENT.DECG_MSR_IDF:        (None,                          None),
    INTC_EVENT.DECG_MSR_ODF:        (None,                          None),
    INTC_EVENT.DECG_MSR_IBIF:       (INTC_SRC.DEC_G,                DMA_REQUEST.DECFILTERG_IB),
    INTC_EVENT.DECG_MSR_OBIF:       (INTC_SRC.DEC_G,                DMA_REQUEST.DECFILTERG_OB),
    INTC_EVENT.DECG_MSR_DIVR:       (INTC_SRC.DEC_G,                None),
    INTC_EVENT.DECG_MSR_OVR:        (INTC_SRC.DEC_G,                None),
    INTC_EVENT.DECG_MSR_IVR:        (INTC_SRC.DEC_G,                None),

    # Decimation Filter H
    INTC_EVENT.DECH_MSR_IDF:        (None,                          None),
    INTC_EVENT.DECH_MSR_ODF:        (None,                          None),
    INTC_EVENT.DECH_MSR_IBIF:       (INTC_SRC.DEC_H,                DMA_REQUEST.DECFILTERH_IB),
    INTC_EVENT.DECH_MSR_OBIF:       (INTC_SRC.DEC_H,                DMA_REQUEST.DECFILTERH_OB),
    INTC_EVENT.DECH_MSR_DIVR:       (INTC_SRC.DEC_H,                None),
    INTC_EVENT.DECH_MSR_OVR:        (INTC_SRC.DEC_H,                None),
    INTC_EVENT.DECH_MSR_IVR:        (INTC_SRC.DEC_H,                None),

    # STM
    INTC_EVENT.STM0:                (INTC_SRC.STM0,                 None),
    INTC_EVENT.STM1:                (INTC_SRC.STM1_3,               None),
    INTC_EVENT.STM2:                (INTC_SRC.STM1_3,               None),
    INTC_EVENT.STM3:                (INTC_SRC.STM1_3,               None),

    # PIT
    INTC_EVENT.PIT_CH0:             (INTC_SRC.PIT0,                 None),
    INTC_EVENT.PIT_CH1:             (INTC_SRC.PIT1,                 None),
    INTC_EVENT.PIT_CH2:             (INTC_SRC.PIT2,                 None),
    INTC_EVENT.PIT_CH3:             (INTC_SRC.PIT3,                 None),
    INTC_EVENT.PIT_RTI:             (INTC_SRC.RTI,                  None),

    # PMC
    INTC_EVENT.PMC:                 (INTC_SRC.PMC,                  None),

    # SRAM ECC (?)
    INTC_EVENT.ECC:                 (INTC_SRC.ECC,                  None),

    # FlexRAY
    INTC_EVENT.FLEXRAY_MIF:         (INTC_SRC.FLEXRAY_MIF,          None),
    INTC_EVENT.FLEXRAY_PROTO:       (INTC_SRC.FLEXRAY_PROTO,        None),
    INTC_EVENT.FLEXRAY_ERR:         (INTC_SRC.FLEXRAY_ERR,          None),
    INTC_EVENT.FLEXRAY_WKUP:        (INTC_SRC.FLEXRAY_WKUP,         None),
    INTC_EVENT.FLEXRAY_B_WTRMRK:    (INTC_SRC.FLEXRAY_B_WTRMRK,     None),
    INTC_EVENT.FLEXRAY_A_WTRMRK:    (INTC_SRC.FLEXRAY_A_WTRMRK,     None),
    INTC_EVENT.FLEXRAY_RX:          (INTC_SRC.FLEXRAY_RX,           None),
    INTC_EVENT.FLEXRAY_TX:          (INTC_SRC.FLEXRAY_TX,           None),
}
