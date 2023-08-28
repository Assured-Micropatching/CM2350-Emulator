import enum

import envi.bits as e_bits

from ..ppc_vstructs import *
from ..ppc_peripherals import *
from ..intc_exc import INTC_EVENT

import logging
import envi.common as e_cmn
logger = logging.getLogger(__name__)


__all__  = [
    'DSPI',
    'SPI_CS',
    'SPIBus',
]



DSPI_MCR_OFFSET     = 0x0000
DSPI_TCR_OFFSET     = 0x0008
DSPI_CTAR_OFFSET    = 0x000C
DSPI_SR_OFFSET      = 0x002C
DSPI_RSER_OFFSET    = 0x0030
DSPI_PUSHR_OFFSET   = 0x0034
DSPI_POPR_OFFSET    = 0x0038
DSPI_TXFR_OFFSET    = 0x003C
DSPI_RXFR_OFFSET    = 0x007C
DSPI_DSICR_OFFSET   = 0x00BC
DSPI_SDR_OFFSET     = 0x00C0
DSPI_ASDR_OFFSET    = 0x00C4
DSPI_COMPR_OFFSET   = 0x00C8
DSPI_DDR_OFFSET     = 0x00CC
DSPI_DSICR1_OFFSET  = 0x00D0

# DSPI MCR constants
DSPI_PERIPHERAL     = 0
DSPI_CONTROLLER     = 1
DSPI_DCONF_SPI      = 0b00
DSPI_DCONF_DSI      = 0b01
DSPI_DCONF_CSI      = 0b10

# The supported number of "transfer attributes" supported
DSPI_CTAS_MAX       = 8

# The number of FIFO entries for both Rx and Tx
DSPI_MSG_SIZE       = 4
DSPI_FIFO_SIZE      = 4
DSPI_TX_FIFO_LEN    = DSPI_FIFO_SIZE * DSPI_MSG_SIZE

# The Rx FIFO is 1 larger than the Tx FIFO because there is an extra "shift
# register" that holds the most recent data.
DSPI_RX_FIFO_SIZE   = 5
DSPI_RX_FIFO_LEN    = DSPI_RX_FIFO_SIZE * DSPI_MSG_SIZE

DSPI_PUSHR_RANGE    = range(DSPI_PUSHR_OFFSET, DSPI_PUSHR_OFFSET+DSPI_MSG_SIZE)
DSPI_POPR_RANGE     = range(DSPI_POPR_OFFSET, DSPI_POPR_OFFSET+DSPI_MSG_SIZE)
DSPI_TXFR_RANGE     = range(DSPI_TXFR_OFFSET, DSPI_TXFR_OFFSET+(DSPI_FIFO_SIZE*DSPI_MSG_SIZE))
DSPI_RXFR_RANGE     = range(DSPI_RXFR_OFFSET, DSPI_RXFR_OFFSET+(DSPI_FIFO_SIZE*DSPI_MSG_SIZE))

# Some DSPI constants
DSPI_MAX_TCNT        = 0xFFFF

# Some constants for extracting control/transmit information from the Tx data
# registers.
PUSHR_CONT_MASK      = 0x80000000
PUSHR_CTAS_MASK      = 0x70000000
PUSHR_EOQ_MASK       = 0x08000000
PUSHR_CTCNT_MASK     = 0x04000000
PUSHR_PCS_MASK       = 0x003F0000
PUSHR_DATA_MASK      = 0x0000FFFF

PUSHR_CONT_SHIFT     = 31
PUSHR_CTAS_SHIFT     = 28
PUSHR_EOQ_SHIFT      = 27
PUSHR_CTCNT_SHIFT    = 26
PUSHR_PCS_SHIFT      = 16
PUSHR_DATA_SHIFT     = 0


class DSPI_MODE(enum.IntEnum):
    """
    For tracking the mode of the DSPI peripheral
    """
    DISABLE    = enum.auto()
    SPI_CNTRLR = enum.auto()
    SPI_PERIPH = enum.auto()
    DSI_CNTRLR = enum.auto()
    DSI_PERIPH = enum.auto()
    CSI_CNTRLR = enum.auto()
    CSI_PERIPH = enum.auto()


# Summary of running and not-running modes
DSPI_MODE_CNTRLR = (DSPI_MODE.SPI_CNTRLR, DSPI_MODE.DSI_CNTRLR, DSPI_MODE.CSI_CNTRLR)
DSPI_MODE_PERIPH = (DSPI_MODE.SPI_PERIPH, DSPI_MODE.DSI_PERIPH, DSPI_MODE.CSI_PERIPH)
DSPI_MODE_RUNNING = DSPI_MODE_CNTRLR + DSPI_MODE_PERIPH

DSPI_MODE_DSI_UNSUPPORTED = (DSPI_MODE.DSI_CNTRLR, DSPI_MODE.DSI_PERIPH)
DSPI_MODE_CSI_UNSUPPORTED = (DSPI_MODE.CSI_CNTRLR, DSPI_MODE.CSI_PERIPH)


# Mapping of interrupt types based on the supporting DSPI peripherals and the
# corresponding SR flag field names
DSPI_INT_EVENTS = {
    'DSPI_A': {
        'eoqf': INTC_EVENT.DSPI_A_TX_EOQ,
        'tfff': INTC_EVENT.DSPI_A_TX_FILL,
        'tcf':  INTC_EVENT.DSPI_A_TX_CMPLT,
        'tfuf': INTC_EVENT.DSPI_A_TFUF,
        'rfdf': INTC_EVENT.DSPI_A_RX_DRAIN,
        'rfof': INTC_EVENT.DSPI_A_RFOF,
    },
    'DSPI_B': {
        'eoqf': INTC_EVENT.DSPI_B_TX_EOQ,
        'tfff': INTC_EVENT.DSPI_B_TX_FILL,
        'tcf':  INTC_EVENT.DSPI_B_TX_CMPLT,
        'tfuf': INTC_EVENT.DSPI_B_TFUF,
        'rfdf': INTC_EVENT.DSPI_B_RX_DRAIN,
        'rfof': INTC_EVENT.DSPI_B_RFOF,
    },
    'DSPI_C': {
        'eoqf': INTC_EVENT.DSPI_C_TX_EOQ,
        'tfff': INTC_EVENT.DSPI_C_TX_FILL,
        'tcf':  INTC_EVENT.DSPI_C_TX_CMPLT,
        'tfuf': INTC_EVENT.DSPI_C_TFUF,
        'rfdf': INTC_EVENT.DSPI_C_RX_DRAIN,
        'rfof': INTC_EVENT.DSPI_C_RFOF,
    },
    'DSPI_D': {
        'eoqf': INTC_EVENT.DSPI_D_TX_EOQ,
        'tfff': INTC_EVENT.DSPI_D_TX_FILL,
        'tcf':  INTC_EVENT.DSPI_D_TX_CMPLT,
        'tfuf': INTC_EVENT.DSPI_D_TFUF,
        'rfdf': INTC_EVENT.DSPI_D_RX_DRAIN,
        'rfof': INTC_EVENT.DSPI_D_RFOF,
    },
}


class DSPI_x_MCR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.mstr = v_bits(1)
        self.cont_scke = v_bits(1)
        self.dconf = v_bits(2)
        self.frz = v_bits(1)
        self.mtfe = v_bits(1)
        self.pcsse = v_bits(1)
        self.rooe = v_bits(1)
        self._pad0 = v_const(2)
        self.pcsis = v_bits(6)
        self.doze = v_bits(1)
        self.mdis = v_bits(1)
        self.dis_txf = v_bits(1)
        self.dis_rxf = v_bits(1)
        self.clr_txf = v_bits(1)
        self.clr_rxf = v_bits(1)
        self.smpl_pt = v_bits(2)
        self._pad1 = v_const(7)
        self.halt = v_bits(1, 1)


class DSPI_x_TCR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.spi_tcnt = v_bits(16)
        self._pad0 = v_const(16)


class DSPI_x_CTAR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.dbr = v_bits(1)
        self.fmsz = v_bits(4, 0xF)
        self.cpol = v_bits(1)
        self.cpha = v_bits(1)
        self.lsbfe = v_bits(1)
        self.pcssck = v_bits(2)
        self.pasc = v_bits(2)
        self.pdt = v_bits(2)
        self.pbr = v_bits(2)
        self.cssck = v_bits(4)
        self.asc = v_bits(4)
        self.dt = v_bits(4)
        self.br = v_bits(4)


class DSPI_x_SR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.tcf = v_w1c(1)
        self.txrxs = v_const(1)
        self._pad0 = v_const(1)
        self.eoqf = v_w1c(1)
        self.tfuf = v_w1c(1)
        self._pad1 = v_const(1)
        self.tfff = v_w1c(1, 1)
        self._pad2 = v_const(5)
        self.rfof = v_w1c(1)
        self._pad3 = v_const(1)
        self.rfdf = v_w1c(1)
        self._pad4 = v_const(1)
        self.txctr = v_const(4)
        self.txnxtptr = v_const(4)
        self.rxctr = v_const(4)
        self.popnxtptr = v_const(4)


# The RSER register bit fields have the same name as the SR register with a
# "_RE" suffix, but to make interrupt mask checking easier use the same exact
# field names as DSPI_x_SR (at least for bits that have an exact match between
# the registers)
class DSPI_x_RSER(PeriphRegister):
    def __init__(self):
        super().__init__()

        self.tcf = v_bits(1)
        self._pad0 = v_const(2)
        self.eoqf = v_bits(1)
        self.tfuf = v_bits(1)
        self._pad1 = v_const(1)
        self.tfff = v_bits(1)
        self.tfff_dirs = v_bits(1)
        self._pad2 = v_const(4)
        self.rfof = v_bits(1)
        self._pad3 = v_const(1)
        self.rfdf = v_bits(1)
        self.rfdf_dirs = v_bits(1)
        self._pad4 = v_const(16)


class DSPI_x_DSICR(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.mtoe = v_bits(1)
        self._pad0 = v_const(1)
        self.mtocnt = v_bits(6)
        self._pad1 = v_const(3)
        self.tsbc = v_bits(1)
        self.txss = v_bits(1)
        self.tpol = v_bits(1)
        self.trre = v_bits(1)
        self.cid = v_bits(1)
        self.dcont = v_bits(1)
        self.dsictas = v_bits(3)
        self._pad2 = v_const(6)
        self.dpcs = v_bits(6)


class DSPI_x_CONST(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.data = v_const(32)


class DSPI_x_DATA(PeriphRegister):
    def __init__(self):
        super().__init__()
        self.data = v_bits(32)


class DSPI_x_DSICR1(PeriphRegister):
    def __init__(self):
        super().__init__()
        self._pad0 = v_const(3)
        self.tsbcnt = v_bits(5)
        self._pad1 = v_const(6)
        self.dse = v_bits(2)
        self._pad2 = v_const(8)
        self.dpcs1 = v_bits(8)


class DSPI_REGISTERS(PeripheralRegisterSet):
    """
    Register set for DSPI peripherals.
    """
    def __init__(self):
        super().__init__()

        # Basic SPI operation
        self.mcr    = (DSPI_MCR_OFFSET,    DSPI_x_MCR())
        self.tcr    = (DSPI_TCR_OFFSET,    DSPI_x_TCR())
        self.ctar   = (DSPI_CTAR_OFFSET,   VTuple([DSPI_x_CTAR() for x in range(DSPI_CTAS_MAX)]))
        self.sr     = (DSPI_SR_OFFSET,     DSPI_x_SR())
        self.rser   = (DSPI_RSER_OFFSET,   DSPI_x_RSER())

        # The PUSHR/POPR/TXFR/RXFR registers are implemented manually in the
        # DSPI peripheral because the operation of these fields is more complex
        # than is easy to handle with VStruct objects

        # "Deserial" SPI (parallel/multi-channel SPI operation)
        self.dsicr  = (DSPI_DSICR_OFFSET,  DSPI_x_DSICR())
        self.sdr    = (DSPI_SDR_OFFSET,    DSPI_x_CONST())
        self.asdr   = (DSPI_ASDR_OFFSET,   DSPI_x_DATA())
        self.compr  = (DSPI_COMPR_OFFSET,  DSPI_x_CONST())
        self.ddr    = (DSPI_DDR_OFFSET,    DSPI_x_CONST())
        self.dsicr1 = (DSPI_DSICR1_OFFSET, DSPI_x_DSICR1())


class SPI_CS(enum.IntEnum):
    CS0 = 0b000001
    CS1 = 0b000010
    CS2 = 0b000100
    CS3 = 0b001000
    CS4 = 0b010000
    CS5 = 0b100000


class SPIBus(ExternalIOPeripheral):
    """
    The SPI device doesn't require an external IO thread. Instead bus devices
    are registered and the transmit function identifies the registered device
    to call that can perform custom handling of the read/write request.
    """
    def __init__(self, emu, devname, mapaddr, mapsize, regsetcls=None,
                 isrstatus=None, isrflags=None, isrevents=None, **kwargs):
        ExternalIOPeripheral.__init__(self, emu=emu, devname=devname,
                                      mapaddr=mapaddr, mapsize=mapsize,
                                      regsetcls=regsetcls, isrstatus=isrstatus,
                                      isrflags=isrflags, isrevents=isrevents,
                                      **kwargs)

        # Ensure the server arguments are clear so the io thread is not started
        self._server_args = None

        # Add a dictionary to lookup SPI bus peripheral devices
        self.devices = {}

    def registerBusPeripheral(self, device, cs):
        self.devices[SPI_CS(cs)] = device

    def transmit(self, cs, value):
        device = self.devices.get(cs)
        if device is not None:
            logger.log(e_cmn.EMULOG, '%s -> %s: 0x%x', self.devname, device.name, value)
            result = device.receive(value)
            if result is not None:
                logger.log(e_cmn.EMULOG, '%s <- %s: 0x%x', self.devname, device.name, result)
                device.transmit(result)
        else:
            logger.info('%s TRANSMIT: 0x%x', self.devname, value)


class DSPI(SPIBus):
    """
    Class to emulate the DSPI peripheral.

    NOTE: at the moment this emulation does not connect external interrupt
          sources and GPIO state change notifications. That will be necessary to
          completely emulate the behavior of a typical SPI bus where the chip
          select signal is used to allow data to be sent or transmitted from
          specific peripherals.

    NOTE: The NXP DSPI peripheral supports DSI and CSI modes that allow complex
          configurations where multiple DSPI peripherals are chained together,
          this emulation does not support emulating those more complex modes.

    <tx/rx example tbd>
    """
    def __init__(self, devname, emu, mmio_addr):
        """
        DSPI constructor.  Each processor has multiple DSPI peripherals so the
        devname parameter must be unique.
        """
        super().__init__(emu, devname, mmio_addr, 0x4000,
                regsetcls=DSPI_REGISTERS,
                isrstatus='sr', isrflags='rser', isrevents=DSPI_INT_EVENTS)

        self.mode = None
        self._tx_fifo = None
        self._rx_fifo = None

        # We need a value other than SR[RXCTR] to keep track of the real Rx FIFO
        # size
        self._rx_fifo_size = 0

        # TODO: read from a fixed-log or buffer, for now we make this match
        # what the real CM2350 reads from the DSPI buses
        if self.devname == 'DSPI_D':
            self._popr_empty_data = b'\x00\x00\x87\xad'
        else:
            self._popr_empty_data = b'\x00\x00\xff\xff'
        logger.debug('[%s] setting 0x%s as data to return when receive queue is empty',
                     self.devname, self._popr_empty_data)

        # Update the state of the peripheral based on MCR writes
        self.registers.vsAddParseCallback('mcr', self.mcrUpdate)

        # If TFFF is cleared in SR and the Tx queue is not full yet the TFFF 
        # event should be set again
        self.registers.vsAddParseCallback('sr', self.srUpdate)

    def reset(self, emu):
        """
        Handle standard core reset and initialization, after the normal reset
        actions re-calculate the current mode.
        """
        super().reset(emu)

        # Set the Tx and Rx FIFOs to default sizes and values the FIFO region
        # has 4 elements
        self._tx_fifo = bytearray(DSPI_TX_FIFO_LEN)
        self._rx_fifo = bytearray(DSPI_RX_FIFO_LEN)
        self._rx_fifo_size = 0

        self.updateMode()

    def _getPeriphReg(self, offset, size):
        """
        Customization of the standard ExternalIOPeripheral _getPeriphReg()
        function to allow custom handling of the PUSHR, POPR, TXFR, and RXFR
        registers which are implemented with bytearray's outside of the standard
        PeripheralRegisterSet object.
        """

        # POPR can be read with 1, 2, or 4 byte reads, PUSHR can be written with
        # those size accesses, so presumably all of the FIFO related registers
        # are ok to be read with any byte size access
        if offset in DSPI_PUSHR_RANGE:
            # Read the last item pushed, which is at offset 0
            idx = offset - DSPI_PUSHR_OFFSET
            return bytes(self._tx_fifo[idx:idx+size])

        elif offset in DSPI_POPR_RANGE:
            # Any size read in the POPR register address range causes a new
            # element to be shifted into POPR from the Rx FIFO, but reads of 2
            # bytes or 1 byte should read from the lower part of the data.
            return self.popRx()[-size:]

        elif offset in DSPI_TXFR_RANGE:
            idx = offset - DSPI_TXFR_OFFSET
            return bytes(self._tx_fifo[idx:idx+size])

        elif offset in DSPI_RXFR_RANGE:
            idx = offset - DSPI_RXFR_OFFSET
            return bytes(self._rx_fifo[idx:idx+size])

        else:
            return super()._getPeriphReg(offset, size)

    def _setPeriphReg(self, offset, bytez):
        """
        Customization of the standard ExternalIOPeripheral _setPeriphReg()
        function to allow custom handling of the PUSHR, POPR, TXFR, and RXFR
        registers which are implemented with bytearray's outside of the standard
        PeripheralRegisterSet object.
        """
        if offset in DSPI_PUSHR_RANGE:
            # 1, 2, or 4 byte writes cause a new value to get pushed onto the Tx
            # FIFO, so if the data being written isn't a 4-byte value pad it out
            # correctly
            idx = offset - DSPI_PUSHR_OFFSET
            size = idx + len(bytez)

            # the data to be pushed onto the Tx FIFO should not exceed 4 bytes
            if size > DSPI_MSG_SIZE:
                raise AlignmentException()

            data = (b'\x00' * idx) + bytez + (b'\x00' * (DSPI_MSG_SIZE-size))
            self.pushTx(data)

        else:
            super()._setPeriphReg(offset, bytez)

    def processReceivedData(self, obj):
        """
        Process incoming data for the DSPI peripheral.

        If in peripheral mode, use the configuration in CTAR0 to send a reply.
        If in controller mode, add the incoming data to the Rx FIFO.
        """
        # If the peripheral is disabled, just discard this data
        if self.mode == DSPI_MODE.DISABLE or self.registers.sr.txrxs == 0:
            logger.debug('[%s] %s: discarding msg %r', self.devname, self.mode, obj)
        else:
            # Add the received data to the Rx FIFO (convert to bytes first)
            value = e_bits.buildbytes(obj, DSPI_MSG_SIZE, bigend=self.emu.getEndian())
            self.pushRx(value)

    def normalTx(self, data):
        """
        Accept a transmit buffer, decode into the relevant PUSHR register
        fields, look up the corresponding CATRx register and the relevant
        configuration values from that register, and return the data necessary
        to transmit this data.

        Returns an indication of if this Tx buffer is configured as the last
        data in the Tx queue.
        """
        pushr_value = e_bits.parsebytes(data, 0, DSPI_MSG_SIZE, bigend=self.emu.getEndian())
        cont = (pushr_value & PUSHR_CONT_MASK) >> PUSHR_CONT_SHIFT
        ctas = (pushr_value & PUSHR_CTAS_MASK) >> PUSHR_CTAS_SHIFT
        eoq = (pushr_value & PUSHR_EOQ_MASK) >> PUSHR_EOQ_SHIFT
        ctcnt = (pushr_value & PUSHR_CTCNT_MASK) >> PUSHR_CTCNT_SHIFT
        pcs = (pushr_value & PUSHR_PCS_MASK) >> PUSHR_PCS_SHIFT

        ctar = self.registers.ctar[ctas]

        # The frame size is the CTARx[FMSZ] field + 1
        bits = ctar.fmsz + 1
        value = pushr_value & e_bits.b_masks[bits]

        # If the PUSHR[CTCNT] flag is set, change the count to 0 before we
        # transmit
        if ctcnt == 1:
            cur_count = 0
        else:
            cur_count = self.registers.tcr.spi_tcnt

        # Send the value to be transmitted along with chip select signal to 
        # enable (allows selection of the right destination bus device)
        self.transmit(pcs, value)

        # The message was transmitted so increment the TCR[SPI_TCNT]
        self.registers.tcr.spi_tcnt = (cur_count + 1) & DSPI_MAX_TCNT

        # Mark the transmit as complete with SR[TCF]
        self.event('tcf', 1)

        # set the SR[EOQF] based on the flag in PUSHR
        self.event('eoqf', eoq)

        if eoq:
            # If the EOQ flag is set then the SR[TXRXS] flag should be cleared
            # and the MCR[HALT] bit should be set
            self.registers.sr.vsOverrideValue('txrxs', 0)
            self.registers.mcr.halt = 1

        return eoq

    def pushTx(self, data):
        """
        Takes data written to the DSPI PUSH TX FIFO register (PUSHR) and
        transmit the message

        NOTE: To be 100% accurate we may need to set/get GPIO pin states to
              emulate the clock, chip select, and data pins.  For now I am not
              doing that level of emulation.
        """
        if self.registers.sr.txrxs == 1:
            # If Tx/Rx is enabled, just send it
            # TODO: strictly speaking in peripheral mode the chip select must be
            # enabled to allow data to be transmitted, but we aren't emulating
            # that yet.
            self.normalTx(data)

            # The TFFF event should always be set here because more data can be 
            # sent.
            self.event('tfff', 1)

        else:
            # Otherwise we need to add this message to the Tx queue
            if self.registers.mcr.dis_txf == 0:
                max_fifo_size = DSPI_FIFO_SIZE
            else:
                max_fifo_size = 1

            # Add to the Tx FIFO (if it isn't full or disabled)
            fifo_size = self.registers.sr.txctr
            if fifo_size < max_fifo_size:
                self._tx_fifo[DSPI_MSG_SIZE:] = self._tx_fifo[:-DSPI_MSG_SIZE]
                self._tx_fifo[:DSPI_MSG_SIZE] = data

                # Increment the SR[TXCTR] and SR[TXNXTPTR] fields
                fifo_size += 1
                self.registers.sr.vsOverrideValue('txctr', fifo_size)

                # The Tx pointer should point to the oldest item in the Tx FIFO
                # (if any), so it should be fifo_size - 1
                self.registers.sr.vsOverrideValue('txnxtptr', max(fifo_size-1, 0))
                self.event('tfff', fifo_size != max_fifo_size)

    def isTxFifoFull(self):
        if self.registers.mcr.dis_txf == 0:
            return self.registers.sr.txctr >= DSPI_FIFO_SIZE
        else:
            return self.registers.sr.txctr >= 1

    def popRx(self):
        """
        Return 4 bytes of data from the Rx FIFO, and remove 1 item from the Rx
        FIFO. If there are no more elements in the Rx FIFO then all 0's will be
        returned.
        """
        fifo_size = self._rx_fifo_size
        if fifo_size > 0:
            # The oldest message is always at index 0
            data = self._rx_fifo[:DSPI_MSG_SIZE]

            # Now shift all of the items in the Rx FIFO left by 1 message
            self._rx_fifo[:-DSPI_MSG_SIZE] = self._rx_fifo[DSPI_MSG_SIZE:]

            # Decrement the SR[RXCTR] field (SR[RXNXTPTR]
            fifo_size -= 1
            self._rx_fifo_size = fifo_size
            self.registers.sr.vsOverrideValue('rxctr', fifo_size)
            self.event('rfdf', fifo_size != 0)

            return data

        else:
            # return the default value
            return b'\x00\x00\x00\x00'
            #return self._popr_empty_data

    def popTx(self):
        """
        Return 4 bytes of data from the Tx FIFO, and remove 1 item from the Tx
        FIFO. If there are no more elements in the Rx FIFO then return None to
        indicate that an underflow has occured.
        """
        fifo_size = self.registers.sr.txctr
        if fifo_size > 0:
            idx = self.registers.sr.txnxtptr * DSPI_MSG_SIZE
            data = self._tx_fifo[idx:idx+DSPI_MSG_SIZE]

            # Decrement the SR[RXCTR] and SR[RXNXTPTR] fields
            fifo_size -= 1
            self.registers.sr.vsOverrideValue('txctr', fifo_size)

            # The Tx pointer should point to the oldest item in the Tx FIFO (if
            # any), so it should be fifo_size - 1
            self.registers.sr.vsOverrideValue('txnxtptr', max(fifo_size-1, 0))

            # Now that data has been removed from the Tx FIFO indicate that it
            # can be filled with more data.
            self.event('tfff', 1)

            return data

        else:
            return None

    def pushRx(self, data):
        """
        Adds incoming data to the Rx FIFO
        """
        if self.registers.mcr.dis_rxf == 0:
            max_fifo_size = DSPI_RX_FIFO_SIZE
        else:
            max_fifo_size = 2

        # Add to the Rx FIFO (if it isn't full or disabled)
        fifo_size = self._rx_fifo_size
        if fifo_size < max_fifo_size:
            # As long as the fifo_size is <= the Rx FIFO max (5) append the data
            # to the Rx FIFO.
            idx = fifo_size * DSPI_MSG_SIZE
            self._rx_fifo[idx:idx+DSPI_MSG_SIZE] = data

            # now increment the fifo size
            fifo_size += 1
            self._rx_fifo_size = fifo_size

            # update the SR[RXCTR] counter, make sure to cap the Rx FIFO size at
            # max FIFO size - 1 (so it doesn't include the hidden shift
            # register)
            if fifo_size < max_fifo_size:
                self.registers.sr.vsOverrideValue('rxctr', fifo_size)

            # A message was added so indicate there is data to be removed from
            # the Rx FIFO
            self.event('rfdf', 1)

        else:
            # The Rx FIFO has overflowed
            self.event('rfof', 1)

            # If the MCR[ROOE] bit is set then overwrite the last value in the
            # Rx FIFO (the "shift register") instead of discarding it.
            if self.registers.mcr.rooe == 1:
                idx = (fifo_size-1) * DSPI_MSG_SIZE
                self._rx_fifo[idx:idx+DSPI_MSG_SIZE] = data
                logger.debug('[%s] %s: Rx overflow, overwriting last msg with %r', self.devname, self.mode, data)
            else:
                logger.debug('[%s] %s: Rx overflow, discarding msg %r', self.devname, self.mode, data)

    def mcrUpdate(self, thing):
        """
        Process updates to the MCR register.
        """
        if self.registers.mcr.clr_txf == 1:
            # Clear the SR[TXCTR] count and set the SR[TFFF] flag
            self.registers.sr.vsOverrideValue('txctr', 0)
            self.registers.sr.vsOverrideValue('txnxtptr', 0)
            self.registers.mcr.clr_txf = 0

            # The Tx FIFO can be filled again
            self.event('tfff', 1)

        if self.registers.mcr.clr_rxf == 1:
            # Clear the SR[RXCTR] count and the SR[RFDF] flag
            self.registers.sr.vsOverrideValue('rxctr', 0)
            self.registers.sr.vsOverrideValue('popnxtptr', 0)
            self.registers.mcr.clr_rxf = 0

        self.updateMode()

    def srUpdate(self, thing):
        # If the TFFF flag was cleared and there is still space in the transmit 
        # queue, re-set TFFF.
        if self.registers.sr.tfff == 0 and not self.isTxFifoFull():
            self.event('tfff', 1)

    def updateMode(self):
        """
        Update the DSPI peripheral mode and set the appropriate MCR status bits
        to indicate the current mode.
        """
        if self.registers.mcr.mdis == 1:
            mode = DSPI_MODE.DISABLE

        elif self.registers.mcr.dconf == DSPI_DCONF_SPI:
            if self.registers.mcr.mstr:
                mode = DSPI_MODE.SPI_CNTRLR
            else:
                mode = DSPI_MODE.SPI_PERIPH

        elif self.registers.mcr.dconf == DSPI_DCONF_DSI:
            if self.registers.mcr.mstr:
                mode = DSPI_MODE.DSI_CNTRLR
            else:
                mode = DSPI_MODE.DSI_PERIPH

        elif self.registers.mcr.dconf == DSPI_DCONF_CSI:
            if self.registers.mcr.mstr:
                mode = DSPI_MODE.CSI_CNTRLR
            else:
                mode = DSPI_MODE.CSI_PERIPH

        else:
            # other options are reserved, default to disabled
            mode = DSPI_MODE.DISABLE

        if self.mode != mode:
            self.mode = mode
            logger.debug('[%s] changing to mode %s', self.devname, self.mode.name)

        # Some DSPI modes are not yet supported
        if self.mode in DSPI_MODE_DSI_UNSUPPORTED:
            raise NotImplementedError('DSPI DSI mode not yet supported')
        elif self.mode in DSPI_MODE_CSI_UNSUPPORTED:
            raise NotImplementedError('DSPI CSI mode not yet supported')

        # Update the SR[TXRXS] flag based on the mode (it must be running) and
        # the HALT flag (TXRXS is one SR field that does not have to be set or
        # cleared through the event() utility function)
        old_txrxs = self.registers.sr.txrxs
        if self.mode == DSPI_MODE.DISABLE or self.registers.mcr.halt == 1:
            self.registers.sr.vsOverrideValue('txrxs', 0)
            if old_txrxs == 1:
                logger.debug('[%s] disabling Tx/Rx', self.devname)
        else:
            self.registers.sr.vsOverrideValue('txrxs', 1)

            # If the TXRXS mode was just changed from 0 to 1, and there is data
            # in the Tx FIFO, and this peripheral is in controller mode,
            # transmit it now.
            if old_txrxs == 0:
                logger.debug('[%s] enabling Tx/Rx (%d msgs in Tx FIFO)',
                        self.devname, self.registers.sr.txctr)
                if self.registers.sr.txctr > 0:
                    # Pull data from the Tx FIFO until we run out of data or the
                    # EOQ frame is found.
                    eoq = 0
                    while not eoq:
                        # Pull the next object from the Tx FIFO
                        data = self.popTx()
                        if data is None:
                            break
                        eoq = self.normalTx(data)

