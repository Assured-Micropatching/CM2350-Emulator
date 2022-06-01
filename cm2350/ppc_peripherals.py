import time
import weakref
import threading
import socket
import errno
import struct
import pickle
import select
import atexit

import envi.bits as e_bits

from . import mmio
from .ppc_vstructs import *
from .intc_exc import AlignmentException, MceWriteBusError, \
        MceDataReadBusError, ExternalException

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
            else:
                print(emu.vw.config.project.reprConfigPaths())
                raise Exception('ERROR: duplicate project config entries for peripheral %s' % devname)

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
    def __init__(self, emu, devname, mapaddr, mapsize, regsetcls=None,
            isrstatus=None, isrflags=None, isrsources=None, **kwargs):
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

        # Don't do the normal MMIO_DEVICE __init__ because it assigns emu, since
        # this is a module we should wait to store the emu instance
        emu.addMMIO(mapaddr, mapsize, devname, self._mmio_read, self._mmio_write, **kwargs)

        # To be customized by subclasses, if ppc_vstructs.PeripheralRegisterSet
        # is used the read/write functions in this base class can be used
        # unmodified.
        if regsetcls is not None:
            self.registers = regsetcls()
        else:
            self.registers = None

        # Initialize the ISR status, flag and source information
        self._initISRInfo(isrstatus, isrflags, isrsources)

        # Now initialize the event set/clear functions that are appropriate for
        # the ISR status, flag, and sources provided.
        self._initISRFunctions()

        # Lastly find any possible DMA request sources for this peripheral
        self._initDMASources()

    def _initISRInfo(self, isrstatus=None, isrflags=None, isrsources=None):
        """
        Initialize the peripheral ISR status, flag and source information
        """
        if isrstatus is not None and isrflags is not None and isrsources is not None:
            if isinstance(isrstatus, (tuple, list)) and \
                    isinstance(isrflags, (tuple, list)):
                # This will be a channel-only ISR config, create the ISR status
                # and flag lists
                self.isrstatus = []
                for name in isrstatus:
                    reg = self.registers.vsGetField(name)
                    self.isrstatus.extend([reg] * (len(reg) * 8))

                self.isrflags = []
                for name in isrflags:
                    reg = self.registers.vsGetField(name)
                    self.isrflags.extend([reg] * (len(reg) * 8))

            else:
                # ISR status and flag registers used by the standard event()
                # function
                self.isrstatus = self.registers.vsGetField(isrstatus)
                self.isrflags = self.registers.vsGetField(isrflags)

            # Keep track of the interrupt sources for this peripheral. There may
            # be different sources for each instance of this type of peripheral
            # so get the instance-specific ISR sources for this peripheral.
            if isinstance(isrsources, dict) and self.devname in isrsources:
                self.isrsources = isrsources[self.devname]
            else:
              self.isrsources = isrsources

        elif isrstatus is None and isrflags is None and isrsources is None:
            self.isrstatus = None
            self.isrflags = None
            self.isrsources = None

        else:
            raise Exception('Inconsistent ISR information provided for peripheral %s' % self.devname)

    def _initISRFunctions(self):
        """
        Assign the correct event set/clear functions that correspond to the
        possible ISR sources for this peripheral
        """
        if self.isrstatus is None:
            # Set a placeholder event function
            self.event = self._eventDoNothing
            return

        # Determine if the ISR sources and register types require a channel
        if isinstance(self.isrstatus, PeriphRegister) and \
                isinstance(self.isrflags, PeriphRegister) and \
                isinstance(self.isrsources, dict):

            # Standard case, only field names expected
            self.event = self._eventRequest

            src_fields = self.isrsources.keys()
            status_reg = self.isrstatus
            flag_reg = self.isrflags

        elif isinstance(self.isrstatus, VArray) and \
                isinstance(self.isrflags, VArray) and \
                isinstance(self.isrsources, (tuple, list)):

            # Channel case, both channel number and field names expected
            self.event = self._eventRequestWithChannel

            # Ensure that the sources for each channel are a dictionary and have
            # the same keys.
            if any(not isinstance(src, dict) for src in self.isrsources):
                src_types_str = ', '.join(str(type(src)) for src in self.isrsources)
                raise Exception('Inconsistent ISR channel source types: %s' % src_types_str)

            src_fields = self.isrsources[0].keys()
            status_reg = self.isrstatus[0]
            flag_reg = self.isrflags[0]

            if not all(src.keys() == src_fields and len(src) == len(src_fields) for src in self.isrsources[1:]):
                src_fields_str = ', '.join(src_fields)
                raise Exception('Inconsistent ISR channel sources != %s' % src_fields_str)

        elif isinstance(self.isrstatus, list) and \
                isinstance(self.isrflags, list) and \
                isinstance(self.isrsources, (tuple, list)):

            # Channel-only case, only a channel number expected but status and
            # flag values are split across one or more multi-bit wide w1c
            # registers
            self.event = self._eventRequestWithOnlyChannel

            if len(self.isrsources) != len(self.isrstatus) or \
                    len(self.isrsources) != len(self.isrflags):
                raise Exception('ISR status (%d), flags (%d), and sources (%d) mismatch' %
                        (len(self.isrstatus), len(self.isrflags), len(self.isrsources)))

            # The final check doesn't apply tho this ISR configuration
            return

        else:
            raise Exception('Inconsistent channel requirements for ISR status (%s), flags (%s) and sources (%s)' %
                    (isinstance(self.isrstatus, VArray),
                        isinstance(self.isrflags, VArray),
                        isinstance(self.isrsources, (tuple, list))))

        # Ensure that all ISR sources are in the status and flag registers
        if not all(f in status_reg._vs_fields and f in flag_reg._vs_fields for f in src_fields):
            src_fields_str = ', '.join(src_fields)
            status_fields_str = ', '.join(status_reg._vs_fields)
            flag_fields_str = ', '.join(flag_reg._vs_fields)
            raise Exception('ISR status and flag registers missing sources: %s (status: %s, flag: %s)' % \
                    (src_fields_str, status_fields_str, flag_fields_str))

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

        # loop through the possible interrupt sources and find any field names
        # in the ISR flag register that a corresponding "_dirs" suffix and if
        # there is a corresponding DIRS field save the DIRS field name.  The IRQ
        # sources are the same indicating both interrupt sources and DMA event
        # requests.
        if isinstance(self.isrsources, (list, tuple)):
            src_fields = self.isrsources[0].keys()
            flag_reg = self.isrflags[0]
        else:
            src_fields = self.isrsources.keys()
            flag_reg = self.isrflags

        for field in src_fields:
            dirs_field = field + '_dirs'
            if dirs_field in flag_reg:
                self.dmaevents[field] = dirs_field
            else:
                # Indicate that there is no corresponding DMA event for this
                # interrupt source
                self.dmaevents[field] = None

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
            self.registers.reset(self.emu)

        elif isinstance(self.registers, (list, tuple)):
            # If instead of a PeripheralRegisterSet (or other VStruct) the
            # registers are a list, go through the list and reset any list item
            # that is a VStruct.
            for item in self.registers:
                if isVstructType(self.registers) and hasattr(self.registers, 'reset'):
                    item.reset(self.emu)

    def _getPeriphReg(self, offset, size):
        """
        Utility function to get a peripheral register value at a particular
        offset.

        This standard implementation of this function assumes that the
        self.registers class attribute is a VStruct-like PeripheralRegisterSet
        that can have part of of the registers read from or written to.
        """
        return self.registers.vsEmitFromOffset(offset, size)

    def _setPeriphReg(self, offset, bytez):
        """
        Utility function to set a peripheral register value at a particular
        offset.

        This standard implementation of this function assumes that the
        self.registers class attribute is a VStruct-like PeripheralRegisterSet
        that can have part of of the registers read from or written to.
        """
        self.registers.vsParseAtOffset(offset, bytez)

    def _slow_mmio_read(self, va, offset, size):
        """
        A slower version of _mmio_read that automatically suppresses PPC read errors
        """
        data = b''

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
            logger.debug("0x%x:  %s: read [%x:%r] (%s)", self.emu.getProgramCounter(), self.__class__.__name__, va, size, value.hex())
            return value

        except NotImplementedError:
            # Make the errors generated by the PlaceholderRegister more useful
            raise NotImplementedError('0x%x:  %s: BAD READ [%x:%d]' % (self.emu.getProgramCounter(), self.__class__.__name__, va, size))

        except (MceDataReadBusError, AlignmentException) as exc:
            # Add in the correct machine state information to this exception
            exc.kwargs.update({
                'va': va,
                'pc': self.emu.getProgramCounter(),
            })
            raise exc

    def _slow_mmio_write(self, va, offset, bytez):
        """
        A slower version of _mmio_write that automatically suppresses PPC write errors
        """
        idx = 0
        while idx < len(bytez):
            try:
                self._setPeriphReg(offset+idx, bytez[idx:])

                # If this completed successfully all data was written
                break
            except (MceWriteBusError, AlignmentException) as exc:
                # See if any data was written
                if 'written' in exc.kwargs and exc.kwargs['written'] > 0:
                    idx += exc.kwargs['written']
                else:
                    # Just move to the next byte and try again
                    idx += 1

    def _mmio_write(self, va, offset, bytez):
        """
        Standard MMIO peripheral write function.
        """
        if len(bytez) > PPC_MAX_READ_SIZE:
            # Assume that this is not a value being changed by emulated
            # instructions
            # TODO: this seems inefficient, but should be good enough for now
            return self._slow_mmio_write(va, offset, bytez)

        logger.debug("0x%x:  %s: write [%x] = %s", self.emu.getProgramCounter(), self.__class__.__name__, va, bytez.hex())
        try:
            self._setPeriphReg(offset, bytez)

        except NotImplementedError:
            # Make the errors generated by the PlaceholderRegister more useful
            raise NotImplementedError('0x%x:  %s: BAD WRITE [%x:%r]' % (self.emu.getProgramCounter(), self.__class__.__name__, va, bytez))

        except (MceWriteBusError, AlignmentException) as exc:
            # Add in the correct machine state information to this exception
            exc.kwargs.update({
                'va': va,
                'data': bytez,
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
        if value and self.isrstatus.vsGetField(field) == 0:
            # Set the ISR status flag
            self.isrstatus.vsOverrideValue(field, int(value))

            if self.isrflags.vsGetField(field) == 1:
                if self.isrsources[field] is not None:
                    # If this field can initiate a DMA event, determine if an
                    # interrupt request or dma request should be initiated.
                    if self.dmaevents[field] is None or \
                            self.isrflags.vsGetField(self.dmaevents[field]) == 0:
                        # if the DIRS field in the flag register is 0 that indicates
                        # an interrupt should be initiated
                        self.emu.queueException(ExternalException(self.isrsources[field]))
                    else:
                        self.emu.dmaRequest(self.isrsources[field])
                else:
                    logger.warning('[%s] Ignoring %s event because no valid ISR source configured',
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
        if value and self.isrstatus[channel].vsGetField(field) == 0:
            # Set the ISR status flag
            self.isrstatus[channel].vsOverrideValue(field, int(value))

            if self.isrflags[channel].vsGetField(field) == 1:
                if self.isrsources[field] is not None:
                    # If this field can initiate a DMA event, determine if an
                    # interrupt request or dma request should be initiated.
                    if self.dmaevents[field] is None or \
                            self.isrflags[channel].vsGetField(self.dmaevents[field]) == 0:
                        # if the DIRS field in the flag register is 0 that indicates
                        # an interrupt should be initiated
                        self.emu.queueException(ExternalException(self.isrsources[channel][field]))
                    else:
                        self.emu.dmaRequest(self.isrsources[channel][field])
                else:
                    logger.warning('[%s] Ignoring channel %d %s event because no valid ISR source configured',
                                   self.devname, channel, field)

    def _eventRequestWithOnlyChannel(self, channel, value):
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
        name, status = next((n, v) for n, v in self.isrstatus[channel])
        new_status = value & ~status
        if new_status != 0:
            # Set the ISR status flag
            self.isrstatus[channel].vsOverrideValue(name, value | status)

            flags = next(val for _, val in self.isrflags[channel])
            if new_status & flags:
                if self.isrsources[channel] is not None:
                    # channel-only event configurations don't have corresponding
                    # DMA request flags
                    self.emu.queueException(ExternalException(self.isrsources[channel]))
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
    def __init__(self, emu, devname, mmio_addr, mmio_size, **kwargs):
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
        super().__init__(emu, devname, mmio_addr, mmio_size, **kwargs)

        # Get the server configuration from the peripheral config
        host = self._config['host']
        port = self._config['port']

        # Check if the IO thread should be created or not
        if emu.vw.getTransMeta('ProjectMode') != 'test' and port is not None:
            # If the host IP address is empty default to localhost
            if host is None:
                host = 'localhost'

            self._server_args = (host, port)
        else:
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
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()

        # Now close the server socket
        if self._server is not None:
            self._server.shutdown(socket.SHUT_RDWR)
            self._server.close()

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
