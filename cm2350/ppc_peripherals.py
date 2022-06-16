import time
import weakref
import threading
import socket
import errno
import struct
import pickle
import select
import atexit
import inspect

import envi.bits as e_bits

from . import mmio
from .ppc_vstructs import *
from .intc_src import INTC_EVENT_MAP
from .intc_exc import AlignmentException, MceWriteBusError, MceDataReadBusError, ExternalException

import logging
logger = logging.getLogger(__name__)


__all__ = [
    'Peripheral',
    'MMIOPeripheral',
    'ExternalIOPeripheral',
    'TimerRegister',
]


# TODO: not sure this is the best way to handle allowing vivisect workspace/user
# to do things that are technically illegal for the PPC instructions to do.
# Seems like this method would lead to a lot of extra and unnecessary overhead.
# A better way might be to add new PPC-specific read/write functions that should
# be used by the emulator when emulating code?

# When emulating PPC code, the largest possible read is 8 bytes, so if reads or
# writes are larger than the desired size silently suppress the PPC-specific
# errors
PPC_MAX_READ_SIZE = 8

# When reading from memory locations that should produce an error fill bytes
# with this value
PPC_INVALID_READ_VAL = b'\x00'


class Peripheral:
    """
    Most basic emulator peripheral class, it automatically registers itself
    with the emulator as a "module" using the device name as the module name.
    """
    #__slots__ = ('devname', 'emu', '_config')

    def __init__(self, emu, devname):
        """
        Standard "module" peripheral constructor, save the device name and
        register with the emulator as a module.
        """
        self.devname = devname
        emu.modules[devname] = self

        # Don't save an emulator instance yet because it may not be ready for
        # this module to interface with it
        self.emu = None

        self._config = None

        # If there is a configuration entry for this peripheral name, save it
        # for easy access
        for project in emu.vw.config.project.getSubConfigNames():
            project_subcfg = emu.vw.config.project.getSubConfig(project)
            if self._config is None:
                devcfg = project_subcfg.getSubConfig(devname, add=False)
                if devcfg is not None:
                    self._config = weakref.proxy(devcfg)
                    break
            else:
                raise Exception('ERROR: duplicate project config entries for peripheral %s:\n%s' %
                        (devname, emu.vw.config.project.reprConfigPaths()))

    def init(self, emu):
        """
        Standard "module" peripheral init function. This is called only once
        during emulator initialization when the emulator's init_core() function
        is called. Any emulator-dependant initialization should be done in this
        function and not in the constructor.

        By default this function calls it's own reset() function at the end of
        this init() function. This should make it easy for a peripheral to
        ensure that during initial start up and during each subsequent reset
        the registers and any internal attribute are set to the correct state.
        """
        logger.debug('init: %s module', self.devname)

        # Now save the emulator, it should be ready to be used where needed
        self.emu = weakref.proxy(emu)

        # Perform the standard peripheral reset actions
        self.reset(emu)

    def reset(self, emu):
        """
        Standard "module" peripheral reset function. This is called every time
        the emulator's reset_core() function is called, and also by default by
        this class's own init() function. This means that each peripheral only
        needs to implement one function to initialize all values to the correct
        default state.

        This function is required to be implemented by all peripherals.
        """
        raise NotImplementedError()


class MMIOPeripheral(Peripheral, mmio.MMIO_DEVICE):
    """
    A peripheral class that implements read/write functions to connect this
    object as an MMIO device to an emulator.
    """
    #__slots__ = tuple(set(list(Peripheral.__slots__) +
    #    mmio.MMIO_DEVICE.slots + ['baseaddr', 'registers']))

    def __init__(self, emu, devname, mapaddr, mapsize, regsetcls=None,
            isrstatus=None, isrflags=None, isrevents=None, **kwargs):
        """
        Constructor for MMIOPeripheral class.

        Parameters:
            emu:      Emulator to register this peripheral with
            devname:  Name of this device, used as a unique string when
                      registering the peripheral object as an emulator "module"
            mapaddr:  Memory map base address to use in the emu.addMMIO()
                      function call
            mapsize:  Memory map size to use in the emu.addMMIO() function call
            **kwargs: Any extra keyword arguments are passed to the
                      emu.addMMIO() to allow a peripheral object to specify
                      custom permissions or an mmio_bytes function.
        """
        super().__init__(emu, devname)

        # Keep track of the base address for this peripheral
        self.baseaddr = mapaddr

        # Don't do the normal MMIO_DEVICE __init__ because it assigns emu, since
        # this is a module we should wait to store the emu instance
        emu.addMMIO(mapaddr, mapsize, devname, self._mmio_read, self._mmio_write, **kwargs)

        # To be customized by subclasses, if ppc_vstructs.PeripheralRegisterSet
        # is used the read/write functions in this base class can be used
        # unmodified.
        if regsetcls is not None:
            # If the register set accepts a bigend parameter supply it from the
            # emulator
            if 'bigend' in inspect.signature(regsetcls).parameters:
                self.registers = regsetcls(bigend=emu.getEndian())
            else:
                self.registers = regsetcls()
        else:
            self.registers = None

        # Initialize the ISR status, flag and source information
        self._initISRInfo(isrstatus, isrflags, isrevents)

        # Lastly find any possible DMA request events for this peripheral
        self._initDMASources()

    def _is_isr_no_channels(self, isrstatus, isrflags, isrevents):
        if isrstatus in self.registers._vs_fields and \
                isrflags in self.registers._vs_fields:
            status_reg = self.registers.vsGetField(isrstatus)
            flags_reg = self.registers.vsGetField(isrflags)
        else:
            status_reg = None
            flags_reg = None

        is_no_channels_config = isinstance(status_reg, PeriphRegister) and \
                isinstance(flags_reg, PeriphRegister) and \
                isinstance(isrevents, dict)

        if is_no_channels_config:
            # If this does look like a "no channels" config sanity check the
            # event data against the available fields in the target registers
            if not all(f in status_reg._vs_fields and f in flags_reg._vs_fields for f in isrevents):
                src_fields_str = ', '.join(isrevents)
                status_fields_str = ', '.join(status_reg._vs_fields)
                flag_fields_str = ', '.join(flags_reg._vs_fields)
                raise Exception('ISR status and flag registers missing sources: %s (status: %s, flag: %s)' % \
                        (src_fields_str, status_fields_str, flag_fields_str))

        return is_no_channels_config

    def _is_isr_with_channels(self, isrstatus, isrflags, isrevents):
        if isrstatus in self.registers._vs_fields and \
                isrflags in self.registers._vs_fields:
            status_reg = self.registers.vsGetField(isrstatus)
            flags_reg = self.registers.vsGetField(isrflags)
        else:
            status_reg = None
            flags_reg = None

        is_with_channels_config = isinstance(status_reg, VArray) and \
                isinstance(status_reg[0], PeriphRegister) and \
                isinstance(flags_reg, VArray) and \
                isinstance(flags_reg[0], PeriphRegister) and \
                isinstance(isrevents, (list, tuple))

        if is_with_channels_config:
            if len(status_reg._vs_fields) != len(flags_reg._vs_fields):
                raise Exception('ISR status and flag size mismatch: (%s) %s != (%s) %s' %
                        (isrstatus, len(status_reg._vs_fields),
                            isrflags, len(flags_reg._vs_fields)))

            # If this does look like a "no channels" config sanity check the
            # event data against the available fields in the target registers
            if not all(f in status_reg[0]._vs_fields and f in flags_reg[0]._vs_fields for f in isrevents[0]):
                src_fields_str = ', '.join(isrevents[0])
                status_fields_str = ', '.join(status_reg[0]._vs_fields)
                flag_fields_str = ', '.join(flags_reg[0]._vs_fields)
                raise Exception('ISR status and flag registers missing sources: %s:\n\tstatus: %s\n\tflag: %s' % \
                        (src_fields_str, status_fields_str, flag_fields_str))

        return is_with_channels_config

    def _is_isr_only_channels(self, isrstatus, isrflags, isrevents):
        # If interrupt status and events is not indicated through a single field
        # in a register then it will be a dictionary of "events" (because the
        # register names will vary) and lists of status and flag registers.

        is_only_channels_config = isinstance(isrstatus, dict) and \
                isinstance(isrflags, dict) and \
                isinstance(isrevents, dict)

        if is_only_channels_config:
            if isrstatus.keys() != isrflags.keys() or  \
                    isrstatus.keys() != isrevents.keys():
                raise Exception('ISR status and flag events mismatch: %s != %s != %s' %
                        (', '.join(isrstatus), ', '.join(isrflags), ', '.join(isrevents)))

            for name in isrstatus:
                status_regs = [self.registers.vsGetField(n) for n in isrstatus[name]]
                if not all(isinstance(r, (v_w1c, v_bits)) for r in status_regs):
                    types_str = ', '.join(str(type(r)) for r in status_regs)
                    raise Exception('Invalid register status regs types for event %s: %s' % (name, types_str))

                flag_regs = [self.registers.vsGetField(n) for n in isrflags[name]]
                if not all(isinstance(r, (v_w1c, v_bits)) for r in flag_regs):
                    types_str = ', '.join(str(type(r)) for r in flag_regs)
                    raise Exception('Invalid register flag regs types for event %s: %s' % (name, types_str))

                status_len = sum(r._vs_bitwidth for r in status_regs)
                flag_len = sum(r._vs_bitwidth for r in status_regs)
                if status_len != flag_len or status_len != len(isrevents[name]):
                    raise Exception('ISR channels mismatch for event %s' % name)

        return is_only_channels_config

    def _populate_isr_channels(self, reg_info):
        channels = {}
        for name in reg_info:
            reg_list = [(n, self.registers.vsGetField(n)._vs_bitwidth) for n in reg_info[name]]
            # Save the register name that each channel should reference
            channels[name] = tuple(sum(([name] * bits for name, bits in reg_list), []))
        return channels

    def _initISRInfo(self, isrstatus=None, isrflags=None, isrevents=None):
        """
        Initialize the peripheral ISR status, flag and source information
        """
        if isrstatus is not None and isrflags is not None and isrevents is not None:
            # There may be different registers for each instance of this type of
            # peripheral.
            if isinstance(isrstatus, dict) and self.devname in isrstatus:
                isrstatus = isrstatus[self.devname]

            if isinstance(isrflags, dict) and self.devname in isrflags:
                isrflags = isrflags[self.devname]

            if isinstance(isrevents, dict) and self.devname in isrevents:
                self.isrevents = isrevents[self.devname]
            else:
                self.isrevents = isrevents

            # Identify the type of ISR configs
            if self._is_isr_only_channels(isrstatus, isrflags, self.isrevents):
                self.isrstatus = self._populate_isr_channels(isrstatus)
                self.isrflags = self._populate_isr_channels(isrflags)

                self.event = self._eventRequestWithOnlyChannel

            elif self._is_isr_with_channels(isrstatus, isrflags, self.isrevents):
                self.isrstatus = self.registers.vsGetField(isrstatus)
                self.isrflags = self.registers.vsGetField(isrflags)

                self.event = self._eventRequestWithChannel

            elif self._is_isr_no_channels(isrstatus, isrflags, self.isrevents):
                self.isrstatus = self.registers.vsGetField(isrstatus)
                self.isrflags = self.registers.vsGetField(isrflags)

                self.event = self._eventRequest

            else:
                raise Exception('Inconsistent ISR information provided:\n\t%s\n\t%s\n\t%s' %
                        (isrstatus, isrflags, self.isrevents))

        elif isrstatus is None and isrflags is None and isrevents is None:
            self.isrstatus = None
            self.isrflags = None
            self.isrevents = None

            self.event = self._eventDoNothing

        else:
            raise Exception('Inconsistent ISR information provided for peripheral %s' % self.devname)

    def _initDMASources(self):
        """
        Identify any ISR events that have associated DMA request events
        automatically from the ISR flag registers.
        """

        # Default to an empty DMA events
        self.dmaevents = {}

        # if the event function is set to _eventDoNothing() then interrupts are
        # not supported for this peripheral therefore DMA requests are not
        # supported.  If the event function is set
        # to_eventRequestWithOnlyChannel() then DMA requests are not supported
        # in that special configuration.
        if self.event == self._eventDoNothing or \
                self.event == self._eventRequestWithOnlyChannel:
            return

        # loop through the possible interrupt events and find any field names
        # in the ISR flag register that a corresponding "_dirs" suffix and if
        # there is a corresponding DIRS field save the DIRS field name.  The IRQ
        # events are the same indicating both interrupt events and DMA requests.
        if isinstance(self.isrevents, (list, tuple)):
            src_fields = self.isrevents[0].keys()
            flag_reg = self.isrflags[0]
        else:
            src_fields = self.isrevents.keys()
            flag_reg = self.isrflags

        for field in src_fields:
            dirs_field = field + '_dirs'
            if dirs_field in flag_reg:
                self.dmaevents[field] = dirs_field
            else:
                # Indicate that there is no corresponding DMA event for this
                # interrupt source
                self.dmaevents[field] = None

    def init(self, emu):
        """
        Initialize the peripheral registers
        """
        if self.registers is not None and hasattr(self.registers, 'init'):
            self.registers.init(emu)

        super().init(emu)

    def reset(self, emu):
        """
        Reset the peripheral registers here rather than having them be
        registered directly as an emu module. This provides more control
        over when the registers are returned to their initial state.
        """
        if isVstructType(self.registers) and hasattr(self.registers, 'reset'):
            # Because the register set has not been registered as an emu module
            # we need to provide the emu now in case there is some emulator
            # state information required to properly return the register set to
            # it's initial reset state.
            self.registers.reset(emu)

        elif isinstance(self.registers, (list, tuple)):
            # If instead of a PeripheralRegisterSet (or other VStruct) the
            # registers are a list, go through the list and reset any list item
            # that is a VStruct.
            for item in self.registers:
                if isVstructType(item) and hasattr(item, 'reset'):
                    item.reset(emu)

    def _getPeriphReg(self, offset, size):
        """
        Utility function to get a peripheral register value at a particular
        offset.

        This standard implementation of this function assumes that the
        self.registers class attribute is a VStruct-like PeripheralRegisterSet
        that can have part of of the registers read from or written to.
        """
        try:
            data = self.registers.vsEmitFromOffset(offset, size)

            if not data:
                raise MceDataReadBusError(data=b'')
            elif len(data) != size:
                raise AlignmentException(data=data)

        except VStructAlignmentError as exc:
            if 'data' not in exc.kwargs:
                exc.kwargs['data'] = b''
            raise AlignmentException(**exc.kwargs) from exc

        except (VStructDataError, VStructWriteOnlyError) as exc:
            if 'data' not in exc.kwargs:
                exc.kwargs['data'] = b''
            raise MceDataReadBusError(**exc.kwargs) from exc

        return data

    def _setPeriphReg(self, offset, data):
        """
        Utility function to set a peripheral register value at a particular
        offset.

        This standard implementation of this function assumes that the
        self.registers class attribute is a VStruct-like PeripheralRegisterSet
        that can have part of of the registers read from or written to.
        """
        try:
            new_offset = self.registers.vsParseAtOffset(offset, data)

            data_remaining = (offset + len(data)) - new_offset
            if data_remaining == len(data):
                raise MceWriteBusError(written=0)
            elif data_remaining:
                raise AlignmentException(written=0)

        except VStructAlignmentError as exc:
            if 'written' not in exc.kwargs:
                exc.kwargs['written'] = 0
            raise AlignmentException(**exc.kwargs) from exc

        except (VStructDataError, VStructReadOnlyError) as exc:
            if 'written' not in exc.kwargs:
                exc.kwargs['written'] = 0
            raise MceWriteBusError(**exc.kwargs) from exc

    def _slow_mmio_read(self, va, offset, size):
        """
        A slower version of _mmio_read that automatically suppresses PPC read errors
        """
        data = bytearra()

        # Try to read the entire memory range
        end = offset + size
        idx = offset
        while idx < end:
            read_size = end - idx
            try:
                value = self._getPeriphReg(idx, read_size)
            except (MceDataReadBusError, AlignmentException) as exc:
                # See if any data was able to be read
                if 'data' in exc.kwargs and exc.kwargs['data']:
                    value = exc.kwargs['data']
                else:
                    value = PPC_INVALID_READ_VAL

            idx += len(value)
            data += value

        return data

    def _mmio_read(self, va, offset, size):
        """
        Standard MMIO peripheral read function.
        """
        if size > PPC_MAX_READ_SIZE:
            # Assume that this is not a value being changed by emulated
            # instructions
            # TODO: this seems inefficient, but should be good enough for now
            return self._slow_mmio_read(va, offset, size)

        try:
            value = self._getPeriphReg(offset, size)
            logger.debug("0x%x:  %s: read [%x:%r] (%s)", self.emu.getProgramCounter(), self.devname, va, size, value.hex())
            return value

        except NotImplementedError:
            # Make the errors generated by the PlaceholderRegister more useful
            raise NotImplementedError('0x%x:  %s: BAD READ [%x:%d]' % (self.emu.getProgramCounter(), self.devname, va, size))

        except (MceDataReadBusError, AlignmentException) as exc:
            # Add in the correct machine state information to this exception
            exc.kwargs.update({
                'va': va,
                'pc': self.emu.getProgramCounter(),
            })
            raise exc

    def _slow_mmio_write(self, va, offset, data):
        """
        A slower version of _mmio_write that automatically suppresses PPC write errors
        """
        idx = 0
        while idx < len(data):
            try:
                self._setPeriphReg(offset+idx, data[idx:])

                # If this completed successfully all data was written
                break
            except (MceWriteBusError, AlignmentException) as exc:
                # See if any data was written
                if 'written' in exc.kwargs and exc.kwargs['written'] > 0:
                    idx += exc.kwargs['written']
                else:
                    # Just move to the next byte and try again
                    idx += 1

    def _mmio_write(self, va, offset, data):
        """
        Standard MMIO peripheral write function.
        """
        if len(data) > PPC_MAX_READ_SIZE:
            # Assume that this is not a value being changed by emulated
            # instructions
            # TODO: this seems inefficient, but should be good enough for now
            return self._slow_mmio_write(va, offset, data)

        logger.debug("0x%x:  %s: write [%x] = %s", self.emu.getProgramCounter(), self.devname, va, data.hex())
        try:
            self._setPeriphReg(offset, data)

        except NotImplementedError:
            # Make the errors generated by the PlaceholderRegister more useful
            raise NotImplementedError('0x%x:  %s: BAD WRITE [%x:%r]' % (self.emu.getProgramCounter(), self.devname, va, data))

        except (MceWriteBusError, AlignmentException) as exc:
            # Add in the correct machine state information to this exception
            exc.kwargs.update({
                'va': va,
                'data': data,
                'pc': self.emu.getProgramCounter(),
            })
            raise exc

    def _eventDoNothing(self, *args, **kwargs):
        logger.error('[%s] call to unconfigured event function', self.devname)

    def _eventRequest(self, field, value):
        """
        Takes a register field name,  and a value to set in the ISR status and
        mask fields.

        This function cannot be used to clear an interrupt event, that can only
        be done manually with the vsOverrideValue() function or by writing a 1
        to the correct status field.

        If the interrupt has not been set previously, and the ISR mask is
        enabled, then an ExternalException interrupt will be registered. If
        there is a dma event associated with the supplied field then a DMA event
        will also be initiated.
        """
        field_value = self.isrstatus.vsGetField(field)
        if value and field_value == 0:
            # Set the ISR status flag
            self.isrstatus.vsOverrideValue(field, int(value))

            intc_src, dma_req = INTC_EVENT_MAP.get(self.isrevents[field], (None, None))
            dma_field = self.dmaevents[field]

            flag_value = self.isrflags.vsGetField(field)
            if flag_value == 1:
                if dma_req is not None and dma_field is not None and \
                        self.isrflags.vsGetField(dma_field) == 1:
                    logger.debug('[%s] sending DMA request %s for %s', self.devname, dma_req, field)
                    self.emu.dmaRequest(dma_req)

                elif intc_src is not None:
                    logger.debug('[%s] queuing exception %s for %s', self.devname, intc_src, field)
                    self.emu.queueException(ExternalException(intc_src))

                else:
                    logger.warning('[%s] Ignoring %s event because no valid ISR source or DMA request configured',
                                   self.devname, field)

    def _eventRequestWithChannel(self, channel, field, value):
        """
        Takes a register field name, channel, and a value to set in the ISR
        status and mask fields.

        This function cannot be used to clear an interrupt event, that can only
        be done manually with the vsOverrideValue() function or by writing a 1
        to the correct status field.

        If the interrupt has not been set previously, and the ISR mask is
        enabled, then an ExternalException interrupt will be registered. If
        there is a dma event associated with the supplied field then a DMA event
        will also be initiated.
        """
        field_value = self.isrstatus[channel].vsGetField(field)
        if value and field_value == 0:
            # Set the ISR status flag
            self.isrstatus[channel].vsOverrideValue(field, int(value))

            intc_src, dma_req = INTC_EVENT_MAP.get(self.isrevents[channel][field], (None, None))
            dma_field = self.dmaevents[field]

            flag_value = self.isrflags[channel].vsGetField(field)
            if flag_value == 1:
                if dma_req is not None and dma_field is not None and \
                        self.isrflags[channel].vsGetField(dma_field) == 1:
                    logger.debug('[%s] sending DMA request %s for [%d]%s', self.devname, dma_req, channel, field)
                    self.emu.dmaRequest(dma_req)

                elif intc_src is not None:
                    logger.debug('[%s] queuing exception %s for [%d]%s', self.devname, intc_src, channel, field)
                    self.emu.queueException(ExternalException(intc_src))

                else:
                    logger.warning('[%s] Ignoring channel %d %s event because no valid ISR source or DMA request configured',
                                   self.devname, channel, field)

    def _eventRequestWithOnlyChannel(self, event, channel, value):
        """
        Takes a channel, and a value to set in one of the ISR status and mask
        registers.  Because this variation of the event() function is used only
        when there are multiple register Value should be a mask of one or more
        bits to be set.

        This function cannot be used to clear an interrupt event, that can only
        be done manually with the vsOverrideValue() function or by writing a 1
        to the correct status field.

        If the interrupt has not been set previously, and the ISR mask is
        enabled, then an ExternalException interrupt will be registered. If
        there is a dma event associated with the supplied field then a DMA event
        will also be initiated.
        """
        # Check if the specified value is set in the target register or not
        reg = self.registers.vsGetField(self.isrstatus[event][channel])
        status = reg.vsGetValue()
        new_bits = value & ~status
        if new_bits:
            # Set the ISR status flag
            reg.vsOverrideValue(new_bits | status)

            flag_reg = self.registers.vsGetField(self.isrflags[event][channel])
            flags = flag_reg.vsGetValue()
            if new_bits & flags:
                intc_src, _ = INTC_EVENT_MAP.get(self.isrevents[event][channel], (None, None))

                if intc_src is not None:
                    # channel-only event configurations don't have corresponding
                    # DMA request flags
                    logger.debug('[%s] queuing exception %s for event %s[%d]', self.devname, intc_src, event, channel)
                    self.emu.queueException(ExternalException(intc_src))
                else:
                    logger.warning('[%s] Ignoring channel %d event because no valid ISR source configured',
                                   self.devname, channel)


# Utilities used by the ExternalIOPeripheral class, these are separate to make
# it easier to re-use them in the test ExternalIOClient test class below.

def _recvData(sock):
    """
    utility to receive (4-byte) length-prefixed data from a socket
    """
    data = sock.recv(4)
    if len(data) < 4:
        # If no data is received, assume this is an error and exit
        logger.info('Incomplete data received %d bytes: %r', len(data), data)
        raise OSError()
    size = struct.unpack('>I', data)[0]

    data = b''
    while len(data) != size:
        # since TCP is a stream the message contents may be segmented, keep
        # receiving until all of the msg is received.
        chunk = sock.recv(size-len(data))
        if not chunk:
            # If no data is received, assume this is an error and exit
            logger.error('No data received: %r', chunk)
            raise OSError()
        data += chunk

    return data

def _sendData(sock, data):
    """
    Utility to transmit data by prefixing the (4-byte) length
    """
    size = struct.pack('>I', len(data))

    # The sock param is allowed to be a list to send to multiple sockets
    # without having to repack/build data each time
    if isinstance(sock, (list, tuple)):
        for s in sock:
            s.sendall(size + data)
    else:
        sock.sendall(size + data)

def _recvObj(sock):
    """
    Utility to recreate an object from received data. The default method
    used here is to unpickle the data.
    """
    # TODO: Don't use pickle for packing/unpacking message data
    data = _recvData(sock)
    obj = pickle.loads(data)
    return obj

def _sendObj(sock, obj):
    """
    Utility to serialize an object into the data form necessary for
    transmitting over the network. The default method used here is
    to pickle the object.
    """
    # TODO: Don't use pickle for packing/unpacking message data
    data = pickle.dumps(obj)
    _sendData(sock, data)


class ExternalIOPeripheral(MMIOPeripheral):
    """
    A peripheral class that supports external IO connections.
    """
    #__slots__ = tuple(set(list(MMIOPeripheral.__slots__) +
    #    ['_server_args' '_server',
    #    '_clients', '_io_thread_sock', '_io_thread_tx_sock',
    #    '_io_thread_rx_sock', '_io_thread']))

    # Sometimes python gets stupid about not calling thread destructors when
    # ipython exits, so just to be keep track of any ExternalIOPeripheral
    # objects allocated and ensure they are cleaned up
    _tasks = None
    _task_lock = threading.RLock()

    @classmethod
    def _kill_tasks(cls):
        """
        Used to try and ensure all threads shut down cleanly, the goal is to
        ensure that all client connections can be cleanly shutdown and are not
        left hanging.
        """
        # Classes could be being deallocated now, so play nice with the lock
        with cls._task_lock:
            while cls._tasks:
                task = cls._tasks.pop()
                del task

    # TODO: Eventually I'd like to either have one single socket for _all_
    # client data to come through and be directed to the correct thread
    # OR
    # Figure out how to mix peripheral configs with the primary VivProject
    # object so the peripheral port/type/style/whatever is defined in the
    # config, and the correct configuration values and defaults could be defined
    # in the peripheral class itself.
    #
    def __init__(self, emu, devname, mapaddr, mapsize, regsetcls=None,
                 isrstatus=None, isrflags=None, isrevents=None, **kwargs):
        """
        Constructor for ExternalIOPeripheral class.

        Parameters:
            emu:      Emulator to register this peripheral with
            devname:  Name of this device, used as a unique string when
                      registering the peripheral object as an emulator "module"
            mapaddr:  Memory map base address to use in the emu.addMMIO()
                      function call
            mapsize:  Memory map size to use in the emu.addMMIO() function call
            **kwargs: Any extra keyword arguments are passed to the
                      emu.addMMIO() to allow a peripheral object to specify
                      custom permissions or an mmio_bytes function.
        """
        super().__init__(emu, devname, mapaddr, mapsize, regsetcls=regsetcls,
                         isrstatus=isrstatus, isrflags=isrflags,
                         isrevents=isrevents, **kwargs)

        # Get the server configuration from the peripheral config (if a config
        # was found)
        if self._config is not None:
            # Check if the IO thread should be created or not
            if emu.vw.getTransMeta('ProjectMode') == 'test':
                self._server_args = None
                logger.debug('Test mode enabled, not creating IO thread for IO module %s',
                        self.devname)
            elif self._config['port'] is None:
                self._server_args = None
                logger.debug('No port configured, not creating IO thread for IO module %s',
                        self.devname)
            else:
                # If the host IP address is empty default to localhost
                if self._config['host'] is None:
                    host = 'localhost'
                    self._server_args = (host, port)
                else:
                    self._server_args = (self._config['host'], self._config['port'])

                logger.debug('Using %s:%s for IO module %s',
                        self._server_args[0], self._server_args[1], self.devname)
        else:
            logger.warning('Could not locate configuration for IO module %s', self.devname)
            self._server_args = None

        self._server = None
        self._clients = []

        # Used for communication between the main and IO threads
        self._io_thread_sock = None
        self._io_thread_tx_sock = None
        self._io_thread_rx_sock = None

        # Don't create the IO thread yet
        self._io_thread = None

        # Keep track of allocated ExternalIOPeripheral objects
        with ExternalIOPeripheral._task_lock:
            if ExternalIOPeripheral._tasks is None:
                ExternalIOPeripheral._tasks = []
                atexit.register(ExternalIOPeripheral._kill_tasks)

            ExternalIOPeripheral._tasks.append(self)

    def __del__(self):
        self.stop()

        # Close the client connections
        for sock in self._clients:
            try:
                sock.shutdown(socket.SHUT_RDWR)
                sock.close()
            except OSError:
                pass

        # Now close the server socket
        if self._server is not None:
            try:
                self._server.shutdown(socket.SHUT_RDWR)
                self._server.close()
            except OSError:
                pass

        # Remove this object from the list of tasks that need cleaned up
        with ExternalIOPeripheral._task_lock:
            try:
                ExternalIOPeripheral._tasks.remove(self)
            except ValueError:
                # Probably means not fully initialized, ignore the error
                pass

    def stop(self):
        """
        Stop the IO thread from running, but don't close the client sockets
        """
        if self._io_thread is not None:
            # Close the sockets used for communication between the main thread
            # and the IO thread, that should signal the IO thread to exit
            if self._io_thread_tx_sock is not None:
                self._io_thread_tx_sock.shutdown(socket.SHUT_RDWR)
                self._io_thread_tx_sock.close()

            self._io_thread.join(1)

            # Now close the thread end of the socket
            self._io_thread_rx_sock.shutdown(socket.SHUT_RDWR)
            self._io_thread_rx_sock.close()

            # If the thread has not exited, something has gone wrong
            if self._io_thread.is_alive():
                logger.error('Failed to stop %s IO thread', self.devname)
            else:
                self._io_thread = None

        # These should all be closed, but just to avoid weird errors during
        # shutdown ensure they are closed now
        if self._io_thread_sock is not None:
            try:
                self._io_thread_sock.close()
            except OSError:
                pass
            self._io_thread_sock = None

        if self._io_thread_tx_sock is not None:
            try:
                self._io_thread_tx_sock.close()
            except OSError:
                pass
            self._io_thread_tx_sock = None

        if self._io_thread_rx_sock is not None:
            try:
                self._io_thread_rx_sock.close()
            except OSError:
                pass
            self._io_thread_rx_sock = None

    def init(self, emu):
        """
        Handle all one-time initialization that needs to be done
        """
        # If analysis-only mode is enabled don't create sockets and attempt to
        # do network things
        if self._server_args is not None:
            # Create the server socket to listen for client connections, this
            # should persist across emulator resets
            # TODO: support IPv6 (AF_INET6)?
            self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server.bind(self._server_args)
            self._server.listen(0)

        super().init(emu)

    def reset(self, emu):
        """
        Handle reset (and initial power up) of the peripheral
        """
        # Ensure that the thread is not currently running, and that the
        # main-to-IO thread socket pair has been cleaned up
        self.stop()

        # (re-)create the socket pair that will be used for the peripheral
        # functions run in the main thread to send output data to the IO
        # thread It'd be a lot more convenient to just use a queue for this
        # but if we did that we couldn't use select() in the IO thread to
        # listen for all incoming messages
        self._io_thread_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._io_thread_sock.bind(('', 0))
        self._io_thread_sock.listen(1)
        io_addr = self._io_thread_sock.getsockname()

        self._io_thread_tx_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._io_thread_tx_sock.connect(io_addr)
        self._io_thread_rx_sock, _ = self._io_thread_sock.accept()

        # Create the server thread for this peripheral if the server args are
        # defined.
        if self._server_args is not None:
            # Now (re-)create the IO thread
            args = {
                'name': '%s-IO' % self.devname,
                'target': self._io_handler,

                # For some bizzare reason ipython just absolutely will hang up
                # when exiting unless these are marked as daemon threads. There
                # is some sort of check happening in check in
                # /usr/lib/python3.9/threading.py that is run before the atexit
                # handler and is halting cleanup. This is some sort of weird
                # behavior with ipython + SimpleQueue + Threads. However we have
                # no need to add "task tracking" to this design so we don't want
                # to add in the extra complexity of using full Queues.
                #
                # So to work around this we just set the daemon flag, even
                # though I don't like it.
                'daemon': True,
            }
            self._io_thread = threading.Thread(**args)
            self._io_thread.start()

    def transmit(self, obj):
        """
        To be used by peripheral when queuing message for transmit. This
        function should be customized to handle any peripheral register
        modifications necessary when transmit happens.
        """
        logger.debug('%s: TRANSMIT %r', self.devname, obj)
        _sendObj(self._io_thread_tx_sock, obj)

    def getTransmittedObjs(self):
        """
        Utility that is useful during testing to manually read transmitted
        objects/messages from the inter-thread socket. This is needed during
        testing when the separate IO thread is not running.
        """
        # To get around the weird and various python/OS/socket issues to get
        # reliable non-blocking sockets, just use select() with a timeout of 0
        # to check for available data
        objs = []
        while True:
            pending_inputs, _, _ = select.select([self._io_thread_rx_sock], [], [], 0.0)
            if self._io_thread_rx_sock in pending_inputs:
                objs.append(_recvObj(self._io_thread_rx_sock))
            else:
                break
        return objs

    def receive(self, obj):
        """
        Used by the io_thread to queue a received message for later processing.
        Can also be used by a peripheral to force receive values (such as if
        the peripheral should receive messages it transmits).
        """
        logger.debug('%s: RECEIVE %r', self.devname, obj)
        self.emu.putIO(self.devname, obj)

    def processReceivedData(self, obj):
        """
        To be used in the executeOpcode() function to do the peripheral
        specific things to take the received data and store it in the
        correct peripheral registers.
        """
        # 1. Take information from the receive object and update the peripheral
        #    registers or settings appropriately
        # 2. Set any necessary "msg received" flags
        # 3. If "msg received" interrupt is enabled:
        #       raise PeripheralSpecificInterrupt()
        raise NotImplementedError()

    def _io_handler(self):
        """
        Standard IO thread that runs select() on the current list of sockets
        and handles inputs:

        * If input is pending on the server socket, then a new client
          connection is accepted the list of client sockets is updated.
        * If input is pending on the socket created to receive outgoing data
          from the peripheral (sent with the transmit() function), then that
          data is received and broadcast to to all clients.
        * If a client connection has disconnected (OSError is received when
          attempting to read from the socket) disconnects then that socket is
          removed from the client socket list.
        * If data is received from the client connection it is placed in the
          emulator's main IO queue using the receive() function.
        """
        # Create the default list of sockets to watch for messages
        inputs = [self._io_thread_rx_sock, self._server] + self._clients
        outputs = []
        excs = []

        while True:
            # select should work on windows as long as we are waiting on
            # sockets
            pending_inputs, _, _ = select.select(inputs, outputs, excs)

            for sock in pending_inputs:
                if sock == self._io_thread_rx_sock:
                    try:
                        data = _recvData(self._io_thread_rx_sock)
                        # Send to all available client sockets
                        _sendData(self._clients, data)
                    except OSError as e:
                        # If an OSError happens while receiving from the
                        # internal main-to-IO thread socket it means this thread
                        # should exit
                        logger.info('Lost connection to main thread, exiting', exc_info=1)
                        return

                elif sock == self._server:
                    # Currently not using the address returned by accept
                    client_sock, _ = self._server.accept()
                    self._clients.append(client_sock)
                    inputs.append(client_sock)

                else:
                    try:
                        # receive data from client and send to the main thread
                        obj = _recvObj(sock)
                        self.receive(obj)
                    except OSError:
                        # If an OSError occurs while receiving from a client
                        # thread, the client has disconnected, remove the socket
                        # from the list of inputs to receive data from
                        logger.info('client sock %r disconnected', sock, exc_info=1)
                        self._clients.remove(sock)
                        inputs.remove(sock)


class TimerRegister:
    """
    Utility to allow peripherals that have some sort of timer/time register to
    get a scaled tick count based on the primary emulator system time.

    This is based on the emutimers.EmulationTime class but without a separate
    thread to track individual timers. This uses the primary emulator systime
    scaling factor.
    """

    #__slots__ = ('_systime_scaling', 'freq', '_bitmask', '_timer_offset',
    #        '_running')

    def __init__(self, bits=None):
        """
        Constructor for the TimerRegister class. If the bits parameter is
        specified then all timer values will be masked to ensure they are
        always within the allowed bit size.
        """
        self._systime_scaling = None
        self.freq = 0

        if bits is not None:
            self._bitmask = e_bits.b_masks[bits]
        else:
            self._bitmask = None

        # Variables to let us track how long the emulated system has been
        # running
        self._timer_offset = None
        self._running = False

    def setFreq(self, emu, freq):
        """
        Set the frequency of this timer. Uses the emulator's systime_scaling
        value to ensure that all timers are running with the same relative
        speed.
        """
        self._systime_scaling = emu._systime_scaling
        self.freq = freq

    def stop(self):
        """
        Stops this timer from running.
        """
        self._running = False
        self._timer_offset = None

    def start(self):
        """
        Starts this timer running (if it is not already running)
        """
        if not self._running:
            self._running = True
            self._timer_offset = time.time()

    def _time(self):
        """
        Internal function to return the scaled amount of time since the timer
        started counting scaled according to the emulator system scaling factor.
        """
        return (time.time() - self._timer_offset) * self._systime_scaling

    def _ticks(self):
        """
        Internal function to return the scaled amount of ticks since the timer
        started counting scaled according to the emulator system scaling factor.
        """
        return int(self._time() * self.freq)

    def get(self):
        """
        Return the number of ticks since the timer started counting wrapped to
        the specified bit width (if a bit width is configured)
        """
        if not self._running:
            return 0
        elif self._bitmask is not None:
            return self._ticks() & self._bitmask
        else:
            return self._ticks()

    def set(self, value):
        """
        Set a custom timer offset
        """
        self._timer_offset = time.time() - value


class ExternalIOClient:
    """
    Utility to make connecting to an ExternalIOPeripheral's server port and
    receive data easier
    """
    def __init__(self, host, port):
        """
        Constructor for ExternalIOClient, uses the host and port parameters to
        connect as a TCP client to the server.
        """
        self._sock = None

        if host is None:
            host = 'localhost'
        self._addr = (host, port)

    def __del__(self):
        self.close()

    def open(self):
        """
        Opens the client connection
        """
        if self._sock is None:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.connect(self._addr)

    def close(self):
        """
        Closes the client connection
        """
        if self._sock is not None:
            self._sock.shutdown(socket.SHUT_RDWR)
            self._sock.close()
            self._sock = None

    def send(self, obj):
        """
        Sends an object to the server using the _sendObj() utility
        """
        logger.debug('Sending %r to %r', obj, self._addr)
        _sendObj(self._sock, obj)

    def recv(self):
        """
        Receives an object from the server using the _recvObj() utility
        """
        try:
            obj = _recvObj(self._sock)
            logger.debug('Received %r from %r', obj, self._addr)
            return obj
        except OSError:
            logger.debug('Connection closed %r', self._addr)
            self.close()
