import bisect
import struct
import operator
import itertools

import vstruct.bitfield
import vstruct.primitives
import envi.bits as e_bits

# Import some values from vstruct that we want to re-export
from vstruct import VStruct, isVstructType
from vstruct.bitfield import VBitField


import logging
logger = logging.getLogger(__name__)


__all__ = [
    # standard VStruct types
    'VStruct',
    'isVstructType',
    'VBitField',

    # New Exception types
    'VStructAlignmentError',
    'VStructDataError',
    'VStructReadOnlyError',
    'VStructWriteOnlyError',
    'VStructUnimplementedError',

    # New VStruct types
    'v_bits',
    'v_sbits',
    'v_const',
    'v_sconst',
    'v_w1c',
    'v_bytearray',
    'VArray',
    'VTuple',
    'PlaceholderRegister',
    'PeriphRegister',
    'PeriphRegSubFieldMixin',
    'ReadOnlyRegister',
    'WriteOnlyRegister',
    'PeripheralRegisterSet',
    'BitFieldSPR',
]


class VStructAlignmentError(ValueError):
    def __init__(self, message=None, **kwargs):
        super().__init__(message)
        self.kwargs = kwargs


class VStructDataError(TypeError):
    def __init__(self, message=None, **kwargs):
        super().__init__(message)
        self.kwargs = kwargs


class VStructReadOnlyError(TypeError):
    def __init__(self, message=None, **kwargs):
        super().__init__(message)
        self.kwargs = kwargs


class VStructWriteOnlyError(TypeError):
    def __init__(self, message=None, **kwargs):
        super().__init__(message)
        self.kwargs = kwargs


class VStructUnimplementedError(NotImplementedError):
    def __init__(self, message=None, **kwargs):
        super().__init__(message)
        self.kwargs = kwargs


VSTRUCT_ADD_DATA_ERROR_TYPES = (
    VStructAlignmentError,
    VStructDataError,
    VStructReadOnlyError,
    VStructWriteOnlyError,
    VStructUnimplementedError,
)


def bytes_to_int(fmt, data, offset, size):
    """
    efficient in-place parsing of data from the offset to the specified size
    """
    if fmt is not None and size < 8:
        return struct.unpack_from(fmt, data, offset)[0]
    else:
        # We have to do this the slow way
        return sum(c << (s*8) for c, s in \
                zip(itertools.islice(data, offset, offset+size), \
                reversed(range(size))))


def int_to_bytes(fmt, value, size):
    """
    efficient transforming of an integer to bytes
    """
    if fmt is not None and size < 8:
        return struct.pack(fmt, value)
    else:
        # We have to do this the slow way
        return bytes((value >> (s*8)) & 0xFF for s in reversed(range(size)))


class v_bits(vstruct.bitfield.v_bits):
    """
    Slight adaptation of the v_bits class that allows setting an initial value
    """
    def __init__(self, width, value=0, bigend=None):
        """
        Constructor for v_bits class

        Parameters:
            width (int): bit width of field
            value (int): default value
        """

        # To mimic the __len__ behavior of the v_number class translate the
        # _vs_bitwidth into the number of bytes wide this object is.  This
        # allows v_bits objects to be used directly in VArrays.  The length will
        # round up to the nearest byte so will not produced correct packed
        # VArray behavior if the size is not a multiple of 8, but that should be
        # ok because this shouldn't be necessary very often.

        # Initialize _vs_size and _vs_mask so they exists
        object.__setattr__(self, '_vs_size', (width + 7) // 8)
        object.__setattr__(self, '_vs_mask', e_bits.b_masks[width])

        super().__init__(width)

        # Set again because the vstruct.bitfield.v_bits initializer sets the
        # wrong values
        self._vs_size = (width + 7) // 8
        self._vs_mask = e_bits.b_masks[width]

        self._vs_startbyte = None
        self._vs_startbit = None
        self._vs_endbyte = None
        self._vs_endbit = None
        self._vs_shift = None

        # An endianness setting doesn't really matter much for most bitfields,
        # but if this is a multi-byte bitfield it could matter
        self.vsSetEndian(bigend)

        # Set the initial value
        self.vsOverrideValue(value)

    def vsSetValue(self, value):
        self._vs_value = value & self._vs_mask

    def vsOverrideValue(self, value):
        self._vs_value = value & self._vs_mask

    def vsSetEndian(self, bigend):
        """
        Change the saved endianness of this object and the parse/emit format
        """
        self._vs_bigend = bigend
        self._vs_fmt = vstruct.primitives.num_fmts.get((self._vs_bigend, self._vs_size))

    # Some helper functions to make it faster and easier to parse and emit data
    # from this field

    def vsSetBitPos(self, bitoff):
        """
        Sets the bit position of this object in a VBitField so that the
        start/end byte and bit offsets, shifts, masks, and formats can be
        calculated once to make using VBitFields faster.
        """
        self._vs_startbyte, self._vs_startbit = divmod(bitoff, 8)
        self._vs_endbyte, self._vs_endbit = divmod(bitoff + self._vs_bitwidth, 8)
        if self._vs_endbit:
            self._vs_shift = 8 - self._vs_endbit
        else:
            self._vs_shift = 0

    def vsSetBitFieldWidth(self, bitwidth):
        """
        Sets the width of the bitfield object that this field lives in so the
        correct shift amount can be calculated correctly.
        """
        # Round bitwidth up to the nearest byte
        bitwidth = ((bitwidth + 7) // 8) * 8

        # Convert the end byte/bit into an end bit offset
        endbitoff = (self._vs_endbyte * 8) + self._vs_endbit
        self._vs_shift = bitwidth - endbitoff

    def vsEmit(self):
        if not self._vs_startbit and not self._vs_endbit:
            return struct.pack(self._vs_fmt, self._vs_value)
        else:
            raise ValueError('Cannot emit field with non-byte aligned bit position: %d:%d - %d:%d' %
                    (self._vs_startbyte, self._vs_startbit, self._vs_endbyte, self._vs_endbit))

    def vsParse(self, data, offset=0):
        if not self._vs_startbit and not self._vs_endbit:
            rawvalue = bytes_to_int(self._vs_fmt, data, offset, self._vs_size)
            self.vsSetValue(rawvalue)
            return offset + self._vs_size
        else:
            raise ValueError('Cannot parse field with non-byte aligned bit position: %d:%d - %d:%d' %
                    (self._vs_startbyte, self._vs_startbit, self._vs_endbyte, self._vs_endbit))


class v_sbits(v_bits):
    """
    signed v_bits, adds signed number processing to v_bits class.

    This has to inherit from the v_bits class instead of v_snumber because the
    VBitField class specifically looks for v_bits when calculating field sizes.
    """
    def __init__(self, width, value=0, bigend=None):
        # Set a sign mask to make it easy to identify negative values
        self._vs_smask = 2**(width-1)

        super().__init__(width, value, bigend)

    def _transform_value(self, value):
        """
        Helper function to return a properly converted signed integer based on
        this field's bitwidth.
        """
        if value & self._vs_smask:
            return -((~value + 1) & self._vs_mask)
        else:
            return value & self._vs_mask

    def vsSetValue(self, value):
        """
        The v_bits class relies on the higher-level VBitField to set the
        correctly sized values, do additional signed conversion now.
        """
        self._vs_value = self._transform_value(value)

    def vsOverrideValue(self, value):
        self._vs_value = self._transform_value(value)

    def vsSetEndian(self, bigend):
        """
        Change the saved endianness of this object and the parse/emit format
        """
        self._vs_bigend = bigend
        self._vs_fmt = vstruct.primitives.signed_fmts.get((bigend, self._vs_size))


class v_const(v_bits):
    """
    A variation of the v_bits class. The vsSetValue function will not
    change the _vs_value of this field which makes this class useful for
    defining bitfields in registers that should not be modifiable by standard
    user write operations. Instead the owning peripheral should either directly
    modify _vs_value, or if this field is part of a PeriphRegister object the
    PeriphRegister.vsOverrideValue function can be used.
    """
    def vsOverrideValue(self, value):
        self._vs_value = value

    def vsSetValue(self, value):
        """
        This is a constant field so the value cannot be modified after creation
        (except by using the vsOverrideValue function).

        Parameters:
            value (int): ignored
        """
        pass

    def vsParse(self, data, offset=0):
        """
        This is a constant field so the value cannot be modified after creation
        (except by using the vsOverrideValue function).

        Parameters:
            data (bytes): ignored
            offset (int): ignored
        """
        return offset

class v_sconst(v_sbits):
    """
    A variation of the v_sbits class. The vsSetValue function will not
    change the _vs_value of this field which makes this class useful for
    defining bitfields in registers that should not be modifiable by standard
    user write operations. Instead the owning peripheral should either directly
    modify _vs_value, or if this field is part of a PeriphRegister object the
    PeriphRegister.vsOverrideValue function can be used.
    """
    def vsOverrideValue(self, value):
        self._vs_value = self._transform_value(value)

    def vsSetValue(self, value):
        """
        This is a constant field so the value cannot be modified after creation
        (except by using the vsOverrideValue function).

        Parameters:
            value (int): ignored
        """
        pass

    def vsParse(self, data, offset=0):
        """
        This is a constant field so the value cannot be modified after creation
        (except by using the vsOverrideValue function).

        Parameters:
            data (bytes): ignored
            offset (int): ignored
        """
        return offset


class v_w1c(v_bits):
    """
    A variation of the v_bits class. Bit values can only be changed from
    1 to 0 by writing a value of 1 for that bit. Normal write operations cannot
    change the bit value from 0 to 1, instead the owning peripheral should
    either directly modify _vs_value, or if this field is part of a
    PeriphRegister object the PeriphRegister.vsOverrideValue function can be
    used.
    """
    def vsSetValue(self, value):
        """
        A field where bits can only be changed from 1 to 0 by writing a 1.

        Parameters:
            value (int): bits in this param that have a value of 1 will be set
                         to 0 in _vs_value attribute.
        """
        if self._vs_value is not None:
            self._vs_value = self._vs_value & ~value


# quick map lookup for big/little endian formats
_fmt_chars = (
    e_bits.le_fmt_chars,
    e_bits.be_fmt_chars,
)


class v_bytearray(vstruct.primitives.v_bytes):
    """
    A bytearray-version of v_bytes, this allows in-place parse/emit like the
    VArray type using __getitem__ and __setitem__ operations.
    """
    def __init__(self, size=0, vbytes=None):
        """
        Constructor for v_bytearray class

        Parameters:
            size (int): size (number of bytes) of this field
            value (bytes): initial value of this field
        """
        if vbytes is None:
            vbytes = b'\x00' * size
        self._vs_pcallbacks = {}
        super().__init__(size=size, vbytes=bytearray(vbytes))
        self._vs_size = len(self._vs_value)

    def vsSetValue(self, value):
        # Raw bytes should be the only values written, so set this the same as
        # vsParse
        self.vsParseAtOffset(0, value, 0)

    def vsGetValue(self):
        """
        To ensure that this primitive not accidentally overwritten return this
        object itself as the "value" and then implement setitem/getitem methods
        to allow accessing the individual array components.
        """
        return self

    @property
    def value(self):
        return self._vs_value

    def __getitem__(self, index):
        """
        Returns an element of the _vs_value bytearray
        """
        return self._vs_value[index]

    def __setitem__(self, index, value):
        """
        Directly modifies an element in the _vs_value bytearray
        """
        self._vs_value[index] = value

    def vsEmitFromOffset(self, offset, size):
        if offset > self._vs_size:
            raise VStructDataError()
        return self._vs_value[offset:offset+size]

    def vsParseAtOffset(self, offset, data, data_offset=0):
        if offset > self._vs_size:
            raise VStructDataError()

        write_len = len(data) - data_offset
        end = offset + write_len
        self._vs_value[offset:end] = data[data_offset:]
        written = min(write_len, self._vs_size - offset)

        self._vsFireCallbacks('by_idx', idx=offset, foffset=0, size=written)

        return offset + written

    def parsebytes(self, offset, size, sign=False, bigend=False):
        """
        Provides envi.bits.parsebytes-like functionality but based on the
        contents of this v_bytearray.
        """
        return e_bits.parsebytes(self._vs_value, offset, size, sign=sign, bigend=bigend)

    def buildbytes(self, offset, value, size, bigend=False):
        """
        Provides envi.bits.buildbytes-like functionality but based on the
        contents of this v_bytearray. Instead of returning the resulting bytes
        they are placed into the contents of this v_bytearray at the specified
        offset.
        """
        struct.pack_into(self._vs_value, offset, _fmt_chars[bigend][size],
                e_bits.unsigned(value, size))

    def vsEmit(self):
        return self._vs_value

    def vsParse(self, data, offset=0):
        return self.vsParseAtOffset(0, data, offset)

    def vsAddParseCallback(self, fieldname, callback):
        """
        Allow attaching a generic parse callback handler for all array indexes
        """
        if fieldname == 'by_idx':
            # We don't have to validate that this is an element
            cblist = self._vs_pcallbacks.get(fieldname)
            if cblist is None:
                cblist = []
                self._vs_pcallbacks[fieldname] = cblist
            cblist.append(callback)
        else:
            super().vsAddParseCallback(fieldname, callback)

    def _vsFireCallbacks(self, fname, *args, **kwargs):
        """
        Slight modification of the standard VStruct._vsFireCallbacks function
        that handles extra args that can be passed to the callback functions
        (such as for by_idx callbacks).
        """
        callback = getattr(self, 'pcb_%s' % fname, None)
        if callback is not None:
            callback(*args, **kwargs)
        for callback in self._vs_pcallbacks.get(fname, []):
            callback(self, *args, **kwargs)


class VArrayFieldsView:
    def __init__(self, varray):
        assert isinstance(varray, VArray)
        self._varray = varray

    def __len__(self):
        return len(self._varray._vs_elems)

    def __iter__(self):
        return iter(range(len(self._varray._vs_elems)))

    def __getitem__(self, idx):
        if isinstance(idx, int) and idx in range(len(self._varray._vs_elems)):
            return idx
        else:
            raise KeyError(idx)

    def get(self, idx, default=None):
        if isinstance(idx, int) and idx in range(len(self._varray._vs_elems)):
            return idx
        else:
            return default


class VArrayValuesView:
    def __init__(self, varray):
        assert isinstance(varray, VArray)
        self._varray = varray

    def __len__(self):
        return len(self._varray._vs_elems)

    def __iter__(self):
        return enumerate(self._varray._vs_elems)

    def __getitem__(self, idx):
        if isinstance(idx, int) and idx in range(len(self._varray._vs_elems)):
            return self._varray._vs_elems[idx]
        else:
            raise KeyError(idx)

    def get(self, idx, default=None):
        if isinstance(idx, int) and idx in range(len(self._varray._vs_elems)):
            return self._varray._vs_elems[idx]
        else:
            return default


class VArray(VStruct):
    """
    Re-imagining of the VStruct VArray class to improve efficiency
    """
    def __init__(self, elems, count=0):
        super().__init__()
        self._vs_pcallbacks = {}

        if isinstance(elems, (list, tuple)):
            self._vsInitElems(elems)
        elif count and isinstance(elems, type) and \
                issubclass(vstruct.primitives.v_base):
            self._vsInitElems(elems() for i in range(count))
        else:
            raise TypeError('Cannot create %s with %s' % (self.__class__.__name__, elems))

        try:
            self._vs_elem_type = type(self._vs_elems[0])
            self._vs_elem_size = len(self._vs_elems[0])

            # Ensure that all elements in this object are the same type
            if not all(type(e) == self._vs_elem_type for e in self._vs_elems):
                raise TypeError('Cannot create %s with elements of different types' %
                        self.__class__.__name__)

        except IndexError:
            self._vs_elem_type = None
            self._vs_elem_size = None

    def _vsInitElems(self, elems):
        self._vs_elems = list(elems)

    def vsAddElement(self, elem):
        if self._vs_elem_type is None:
            self._vs_elem_type = type(elem)
            self._vs_elem_size = len(elem)
        elif type(elem) != self._vs_elem_type:
            raise TypeError('Cannot create %s with elements of different types (%s != %s)' %
                    (self.__class__.__name__, type(elem), self._vs_elem_type))

        self._vs_elems.append(elem)

    def vsAddElements(self, count, eclass):
        if self._vs_elem_type is None:
            self._vs_elem_type = eclass
        elif eclass != self._vs_elem_type:
            raise TypeError('Cannot create %s with elements of different types (%s != %s)' %
                    (self.__class__.__name__, eclass, self._vs_elem_type))

        self._vs_elems.extend([eclass()] * count)

        if self._vs_elem_size is None and count:
            self._vs_elem_size = len(self._vs_elems[0])

    def __getitem__(self, index):
        return self._vs_elems[index]

    def __setitem__(self, index, value):
        self._vs_elems[index].vsSetValue(value)

    # A few more modifications to the standard VStruct functions are necessary
    # to make a list/index based VArray class work

    def __len__(self):
        return len(self._vs_elems) * self._vs_elem_size

    def __iter__(self):
        for idx, value in enumerate(self._vs_elems):
            yield (idx, value)

    @property
    def _vs_fields(self):
        return VArrayFieldsView(self)

    @_vs_fields.setter
    def _vs_fields(self, value):
        # Placeholder setter to allow standard VStruct __init__ work
        pass

    @property
    def _vs_values(self):
        return VArrayValuesView(self)

    @_vs_values.setter
    def _vs_values(self, value):
        # Placeholder setter to allow standard VStruct __init__ work
        pass

    def vsGetField(self, key):
        return self._vs_elems[key]

    def vsSetField(self, key, value):
        self._vs_elems[key] = value

    def vsGetFields(self):
        return self.__iter__()

    def _getFieldAndIndexByOffset(self, offset, names=None):
        """
        Modification of the standard VStruct vsGetFieldByOffset() function to
        allow for a faster search because the array elements have consistent
        sizes.
        """
        if names is None:
            names = []

        # Identify the array index and the field-specific offset
        idx = offset // self._vs_elem_size
        foffset = idx * self._vs_elem_size

        if idx >= len(self._vs_elems):
            # Target offset not found
            raise VStructDataError()

        # The offset falls somewhere in this field
        names.append(str(idx))

        return names, self._vs_elems[idx], idx, offset-foffset

    def vsGetFieldByOffset(self, offset, names=None):
        names, field, _, foffset = self._getFieldAndIndexByOffset(offset, names=names)

        # If foffset is not 0, we need to look into the field
        if foffset:
            return field.vsGetFieldByOffset(foffset, names)
        else:
            return '.'.join(names), field

    # A few functions defined by PeripheralRegisterSet to support parsing
    # into/emitting from arrays of VStructs that have complex subfields.

    def vsEmitFromOffset(self, offset, size):
        data = bytearray()
        try:
            while len(data) < size:
                names, field, idx, foffset = self._getFieldAndIndexByOffset(offset+len(data))

                if hasattr(field, 'vsEmitFromOffset'):
                    data += field.vsEmitFromOffset(foffset, size - len(data))
                elif not foffset:
                    data += field.vsEmit()
                else:
                    if foffset >= len(field):
                        # This offset is beyond the identified field
                        raise VStructDataError()
                    else:
                        # We can't evenly emit a subfield so just stop now
                        raise VStructAlignmentError()

        except VSTRUCT_ADD_DATA_ERROR_TYPES as exc:
            # Ensure that the amount of data read is recorded in the exception
            exc.kwargs['data'] = data
            raise exc

        return data

    def vsParseAtOffset(self, offset, data, data_offset=0):
        written = 0
        try:
            while data_offset < len(data):
                names, field, idx, foffset = self._getFieldAndIndexByOffset(offset)

                if hasattr(field, 'vsParseAtOffset'):
                    ret_offset = field.vsParseAtOffset(foffset, data, data_offset)
                    written_len = ret_offset - foffset
                elif not foffset:
                    ret_offset = field.vsParse(data, offset=data_offset)
                    written_len = ret_offset - data_offset
                else:
                    if foffset >= len(field):
                        # This offset is beyond the identified field
                        raise VStructDataError()
                    else:
                        # We can't parse into a subfield so just stop now, but
                        # track how much data has been parsed
                        raise VStructAlignmentError()

                written += written_len
                offset += written_len
                data_offset = ret_offset

                # If there is a "by_idx" callback, call it now
                self._vsFireCallbacks('by_idx', idx=idx, foffset=foffset, size=written_len)

        except VSTRUCT_ADD_DATA_ERROR_TYPES as exc:
            # Ensure that the amount of data parsed is recorded in the exception
            exc.kwargs['data'] = data[data_offset-written:data_offset]
            raise exc

        return offset

    def vsAddParseCallback(self, fieldname, callback):
        """
        Allow attaching a generic parse callback handler for all array indexes
        """
        if fieldname == 'by_idx':
            # We don't have to validate that this is an element
            cblist = self._vs_pcallbacks.get(fieldname)
            if cblist is None:
                cblist = []
                self._vs_pcallbacks[fieldname] = cblist
            cblist.append(callback)
        else:
            super().vsAddParseCallback(fieldname, callback)

    def _vsFireCallbacks(self, fname, *args, **kwargs):
        """
        Slight modification of the standard VStruct._vsFireCallbacks function
        that handles extra args that can be passed to the callback functions
        (such as for by_idx callbacks).
        """
        callback = getattr(self, 'pcb_%s' % fname, None)
        if callback is not None:
            callback(*args, **kwargs)
        for callback in self._vs_pcallbacks.get(fname, []):
            callback(self, *args, **kwargs)



class VTuple(VArray):
    def _vsInitElems(self, elems):
        self._vs_elems = tuple(elems)


class PlaceholderRegister(v_const):
    """
    A v_const-like value that represents a peripheral register that has not yet
    been implemented and raises a NotImplementedError whenever it is read from
    or written to using the standard VStruct vsEmit or vsParse functions.
    """
    def vsParse(self, data, offset=0):
        raise VStructUnimplementedError('%s not implemented' % self.__class__.__name__)

    def vsEmit(self):
        raise VStructUnimplementedError('%s not implemented' % self.__class__.__name__)


class PeriphRegister(VBitField):
    """
    A VBitField object that enables easy integration into a bare metal emulator.
    """
    def __init__(self, emu=None, name=None, bigend=None):
        """
        Constructor for PeriphRegister class.  If this object is not part of a
        peripheral but a standalone special register then it the emu and name
        fields should be supplied to enable standard emulator module init and
        reset behavior.

        Parameters:
            emu (object) optional:  The emulator this register should be
                                    registered with
            name (string) optional: The name to use when registering this
                                    object as an emulator module.
        """
        super().__init__()
        self._vs_defaults = {}

        # Default the size to 0
        self._vs_bitwidth = 0
        self._vs_size = 0

        # Save the endianness so we can update all added fields, VBitField
        # doesn't support the bigend parameter so we set it manually now.
        if bigend is not None:
            self.vsSetEndian(bigend)
        else:
            self._vs_bigend = None

        if emu is not None:
            if name is None:
                name = self.__class__.__name__
            if name in emu.modules:
                idx = emu.modules.index(name)
                cur_module = emu.modules[idx]
                raise ValueError('Module %s:%r already registered, cannot register %s:%r' % (name, cur_module, name, self))
            emu.modules[name] = self

            if self._vs_bigend is None:
                self.vsSetEndian(emu.getEndian())

    # TODO: implement more efficient lookup of fields in the bitfield for
    #       vsParse, vsEmit?

    def vsSetEndian(self, bigend):
        if bigend is None:
            raise ValueError('Cannot set endianness of %s to %s' % (self.__class__.__name__, bigend))

        self._vs_bigend = bool(bigend)

        # Now go update all fields this class has
        total_bits = 0
        for name, value in self:
            self._vsUpdateValueEndian(value)
            total_bits += value._vs_bitwidth

        # Verify the size is up to date now also
        self._vs_bitwidth = total_bits
        self._vs_size = (total_bits + 7) // 8

        # Now update the emit format
        self._vs_fmt = vstruct.primitives.num_fmts.get((self._vs_bigend, self._vs_size))

    def _vsUpdateValueEndian(self, value):
        if hasattr(value, 'vsSetEndian'):
            value.vsSetEndian(self._vs_bigend)
        elif hasattr(value, '_vs_bigend'):
            value._vs_bigend = self._vs_bigend
        elif isinstance(value, VArray):
            # Do the same for every item in the VArray
            for _, elem in value:
                if hasattr(elem, 'vsSetEndian'):
                    elem.vsSetEndian(self._vs_bigend)
                elif hasattr(elem, '_vs_bigend'):
                    elem._vs_bigend = self._vs_bigend

    def vsAddField(self, name, value):
        """
        Allows adding a field to an existing PeriphRegister object. Tracks the
        initial value of the field which is used when the register is reset.
        """
        # Now update the endianness setting for this field
        if self._vs_bigend is not None:
            self._vsUpdateValueEndian(value)

        # Update this new field's bit position
        value.vsSetBitPos(self._vs_bitwidth)

        # Now add field
        super().vsAddField(name, value)
        if not isinstance(value, PlaceholderRegister):
            self._vs_defaults[name] = value.vsGetValue()

        # Update the size for this register
        self._vs_bitwidth += value._vs_bitwidth
        self._vs_size = (self._vs_bitwidth + 7) // 8

        # Now update the emit format
        self._vs_fmt = vstruct.primitives.num_fmts.get((self._vs_bigend, self._vs_size))

        # Update all fields with the total bit width of this bitfield
        for fname, field in self.vsGetFields():
            field.vsSetBitFieldWidth(self._vs_bitwidth)

    def vsOverrideValue(self, name, value):
        """
        Sometimes it is necessary to change the value of a read-only field
        because of some internal emulation logic.  This function helps do that.
        """
        self._vs_values[name].vsOverrideValue(value)

    def init(self, emu):
        """
        Init function, used when a peripheral register is initialized as an
        emulator module.
        """
        # If the endianness of this register set has not yet been defined, set
        # it now
        if self._vs_bigend is None:
            bigend = emu.getEndian()
            self.vsSetEndian(bigend)

    def reset(self, emu):
        """
        Reset function, used to return a peripheral register to the correct
        initial state.
        """
        # For any items with defaults set them now
        for name, value in self._vs_defaults.items():
            # Set values directly instead of using the vsSetField() function
            # to make it easier to reset w1c fields to their default values.  We
            # could use vsOverrideValue() but the normal v_bits() fields don't
            # have this function.
            self.vsOverrideValue(name, value)

        # If there are any fields that have their own reset function, call it
        # now
        for name, value in self:
            if name not in self._vs_defaults and hasattr(value, 'reset'):
                value.reset(emu)

    # More efficient versions of VBitField vsEmit and vsParse functions that
    # take advantage of expected limitations in valid peripheral register
    # configurations.

    def vsEmit(self):
        # Unfortunately we can't just call field.vsEmit() here because we need
        # to be able to mesh fields with unaligned start and end bits. Instead
        # continually add field values into one accumulated value
        value = 0
        for fname, field in self.vsGetFields():
            value |= (field.vsGetValue() & field._vs_mask) << field._vs_shift

        return int_to_bytes(self._vs_fmt, value, self._vs_size)

    def vsParse(self, data, offset=0):
        # Unfortunately we can't just call field.vsParse() here because we need
        # to be able to mesh fields with unaligned start and end bits, and
        # ensure that the endianness of the entire register is treated
        # correctly.
        #
        # Instead unpack the data for this register now and then extract each
        # field individually.
        if len(data) - offset < self._vs_size:
            raise VStructAlignmentError()

        value = bytes_to_int(self._vs_fmt, data, offset, self._vs_size)
        for fname, field in self.vsGetFields():
            field.vsSetValue(value >> field._vs_shift)
            self._vsFireCallbacks(fname)

        return offset + self._vs_size

    def vsGetPrintInfo(self, offset=0, indent=0, top=True):
        """
        Adapted version of the VBitField.vsGetPrintInfo() function that prints
        the proper subfield offsets rather than just 0.
        """
        ret = []
        if top:
            ret.append((offset, indent, self._vs_name, self))

        indent += 1
        bitoff = 0
        for fname,field in self.vsGetFields():
            # use vsSetBitWidth(0) to disable fields
            if field._vs_bitwidth == 0:
                continue
            bw = field._vs_bitwidth
            if bw > 1:
                bitname = '%s[%d:%d]' % (fname,bitoff,bitoff + bw - 1)
            else:
                bitname = '%s[%d]' % (fname,bitoff)
            off = offset + (bitoff // 8)
            ret.append( (off, indent, bitname, field) )
            bitoff += field._vs_bitwidth

        return ret



class PeriphRegSubFieldMixin:
    """
    mixin for PeriphRegister that allows supporting emitting from or parsing
    into subfields
    """
    def vsEmitFromOffset(self, offset, size):
        """
        Mixed implementation of the normal VBitField.vsEmit() function that
        can handle reading data that isn't evenly aligned by byte-boundaries,
        and the normal VStruct.vsEmit() which doesn't require reading all
        fields in a VStruct object at the same time.
        """

        # TODO: Not as fast as finding the right starting offset like
        #       PeripheralRegisterSet, perhaps we should support a bitoffset
        #       based lookup?

        # Identify how many bits long the result is expected to be, and how much
        # to adjust the field shift values based on the starting offset and
        # target bitwidth
        start_bitwidth = offset * 8
        target_bitwidth = size * 8
        end_bitwidth = start_bitwidth + target_bitwidth
        missing_bits = self._vs_bitwidth - (start_bitwidth + target_bitwidth)

        value = 0
        emit_bitwidth = 0
        cur_bitwidth = 0
        for fname, field in self.vsGetFields():
            # Unfortunately we can't just call field.vsEmit() here because we
            # need to be able to mesh fields with unaligned start and end
            # bits. Instead continually add field values into one accumulated
            # value
            if start_bitwidth > cur_bitwidth and \
                    start_bitwidth < cur_bitwidth + field._vs_bitwidth:
                # If the starting bit is in the middle of a field grab only the
                # relevant bits
                cut_bits = start_bitwidth - cur_bitwidth
                width = field._vs_bitwidth - cut_bits
                mask = e_bits.b_masks[width]

                value |= (field.vsGetValue() & mask) << (field._vs_shift - missing_bits)
                emit_bitwidth += width

            elif end_bitwidth > cur_bitwidth and \
                    end_bitwidth < cur_bitwidth + field._vs_bitwidth:
                # If the ending bit is in the middle of a field grab only the
                # relevant bits
                cut_bits = field._vs_bitwidth - (target_bitwidth - emit_bitwidth)
                width = field._vs_bitwidth - cut_bits
                mask = e_bits.b_masks[width]

                # The field also needs to be right shifted a few extra bits
                # depending on how many are being left out of this field
                value |= (((field.vsGetValue() & field._vs_mask) >> cut_bits) & mask) << (field._vs_shift - missing_bits)
                emit_bitwidth += width

            elif field._vs_startbyte >= offset:
                # Grab the field value as-is but adjust the shift amount for the
                # missing bits
                value |= (field.vsGetValue() & field._vs_mask) << (field._vs_shift - missing_bits)
                emit_bitwidth += field._vs_bitwidth

            cur_bitwidth += field._vs_bitwidth
            if cur_bitwidth >= end_bitwidth:
                break

        if emit_bitwidth:
            emit_size = (emit_bitwidth + 7) // 8
            fmt = vstruct.primitives.num_fmts.get((self._vs_bigend, emit_size))
            return int_to_bytes(fmt, value, emit_size)

        else:
            # If the target offset was not found, then this field doesn't have
            # the requested data
            raise VStructDataError()

    def vsParseAtOffset(self, offset, data, data_offset=0):
        """
        Mixed implementation of the normal VBitField.vsParse() function that
        can handle writing data that isn't evenly aligned by byte-boundaries,
        and the normal VStruct.vsParse() which doesn't require writing all
        fields in a VStruct object at the same time.
        """
        # Figure out how much data can be parsed and get a value out so we can
        # place the numbers into individual fields.
        avail_data = len(data) - data_offset
        avail_space = self._vs_size - offset
        extra_data = max(avail_data - avail_space, 0)
        parse_size = avail_data - extra_data

        fmt = vstruct.primitives.num_fmts.get((self._vs_bigend, parse_size))
        value = bytes_to_int(fmt, data, data_offset, parse_size)

        # TODO: Not as fast as finding the right starting offset like
        #       PeripheralRegisterSet, perhaps we should support a bitoffset
        #       based lookup?

        # Identify how many bits long the result is expected to be, and how much
        # to adjust the field shift values based on the starting offset and
        # target bitwidth
        start_bitwidth = offset * 8
        target_bitwidth = (len(data) - data_offset) * 8
        end_bitwidth = start_bitwidth + target_bitwidth
        missing_bits = self._vs_bitwidth - (start_bitwidth + target_bitwidth)

        parse_bitwidth = 0
        cur_bitwidth = 0
        for fname, field in self.vsGetFields():
            # Adjust the expected shift amount for the bits not in the provided
            # data
            shift = field._vs_shift - missing_bits

            if start_bitwidth > cur_bitwidth and \
                    start_bitwidth < cur_bitwidth + field._vs_bitwidth:
                # If the starting bit is in the middle of a field update only
                # the correct parts of the target field

                cut_bits = start_bitwidth - cur_bitwidth
                width = field._vs_bitwidth - cut_bits
                mask = e_bits.b_masks[width]

                # Mask off the bits that will not be changing
                cur_value = field.vsGetValue() & ~mask

                # grab the relevant bits and shift them into place for the
                # updated field value
                field_value = (value >> shift) & mask

                # Combine the old and new parts
                field.vsSetValue(cur_value | field_value)
                self._vsFireCallbacks(fname)

                parse_bitwidth += width

            elif end_bitwidth > cur_bitwidth and \
                    end_bitwidth < cur_bitwidth + field._vs_bitwidth:
                # If the ending bit is in the middle of a field update only
                # the correct parts of the target field

                cut_bits = cur_bitwidth + field._vs_bitwidth - end_bitwidth
                width = field._vs_bitwidth - cut_bits
                mask = e_bits.b_masks[width] << cut_bits

                # Mask off the bits that will not be changing
                cur_value = field.vsGetValue() & ~mask

                # grab the relevant bits and shift them into place for the
                # updated field value
                field_value = (value >> (shift - cut_bits)) & mask

                # Combine the old and new parts
                field.vsSetValue(field_value | cur_value)
                self._vsFireCallbacks(fname)

                parse_bitwidth += width

            elif field._vs_startbyte >= offset:
                # Collect the fields to be parsed because we need to identify
                # what the correct format conversion is.

                field.vsSetValue(value >> shift)

                parse_bitwidth += field._vs_bitwidth

            cur_bitwidth += field._vs_bitwidth
            if cur_bitwidth >= end_bitwidth:
                break

        return offset + parse_size


class ReadOnlyRegister(PeriphRegister):
    """
    Read-only peripheral register
    """
    def vsSetValue(self, value):
        raise VStructReadOnlyError('Cannot read from %s' % self.__class__.__name__)

    def vsParse(self, data, offset=0):
        raise VStructReadOnlyError('Cannot read from %s' % self.__class__.__name__)


class WriteOnlyRegister(PeriphRegister):
    """
    Read-only peripheral register
    """
    def vsGetValue(self):
        raise VStructWriteOnlyError('Cannot write to %s' % self.__class__.__name__)

    def vsEmit(self):
        raise VStructWriteOnlyError('Cannot write to %s' % self.__class__.__name__)


class PeripheralRegisterSet(VStruct):
    """
    VStruct customized class that can hold multiple "registers" (PeriphRegister)
    and provide some standard peripheral-like behavior like:
    - Supporting system init/reset of all contained fields
    - Supporting parse/emit of only a subset of fields because it tracks field
      offset (this allows a sparse register space to exist)

    Example from the FlexCAN peripheral (with constants changed to numbers for the
    purposes of this example):

        class FLEXCAN_REGISTERS(PeripheralRegisterSet):
            def __init__(self, emu=None):
                super().__init__(emu)
                self.mcr      = (0x0000, FLEXCAN_x_MCR())
                self.ctrl     = (0x0004, FLEXCAN_x_CTRL())
                self.rxgmask  = (0x0010, FLEXCAN_x_MASK(0xFFFFFFFF))
                self.rx14mask = (0x0014, FLEXCAN_x_MASK(0xFFFFFFFF))
                self.rx15mask = (0x0018, FLEXCAN_x_MASK(0xFFFFFFFF))
                self.ecr      = (0x001C, FLEXCAN_x_ECR())
                self.esr      = (0x0020, FLEXCAN_x_ESR())
                self.imask2   = (0x0024, FLEXCAN_x_MASK())
                self.imask1   = (0x0028, FLEXCAN_x_MASK())
                self.iflag2   = (0x002C, FLEXCAN_x_FLAG())
                self.iflag1   = (0x0030, FLEXCAN_x_FLAG())
                self.mb       = (0x0080, v_bytearray(size=0x800))
                self.rximr    = (0x0880, v_bytearray(size=0x400))

    In this example all but the last two elements are PeriphRegisters so they
    can automatically be reset by the reset function in this class, but the
    last two fields will require customizing the reset() function to ensure
    those fields are correctly reset to their default values:

        def reset(self, emu):
            super().reset(emu)
            self.mb[:] = b'\x00' * 0x800
            self.rximr[:] = b'\x00' * 0x400
    """
    def __init__(self, name=None, bigend=None):
        """
        Constructor for PeripheralRegisterSet class.  If this object is not
        part of a peripheral but a standalone special register then it the emu
        and name fields should be supplied to enable standard emulator module
        init and reset behavior.

        The PeripheralRegisterSet class does not support an emu parameter
        because it is intended to be attached to a Peripheral object, instead of
        directly to an emulator.

        Parameters:
            name (string) optional: The name to use when registering this
                                    object as an emulator module.
        """
        super().__init__()

        # Save the endianness so we can update all added fields, VBitField
        # doesn't support the bigend parameter so we set it manually now.
        if bigend is not None:
            self.vsSetEndian(bigend)
        else:
            self._vs_bigend = None

        self._vs_field_offset = {}

        # Regenerated each time a field is added, makes it faster to find the
        # field to emit from or parse into
        self._vs_field_by_offset = {}
        self._vs_sorted_offsets = []

    def _vsUpdateValueEndian(self, value):
        # Check for a VArry first so we can do custom endian setting and avoid 
        # having to modify using the VArrayValuesView
        if isinstance(value, VArray):
            for _, elem in value:
                if hasattr(elem, 'vsSetEndian'):
                    elem.vsSetEndian(self._vs_bigend)
                elif hasattr(elem, '_vs_bigend'):
                    elem._vs_bigend = self._vs_bigend
        elif hasattr(value, 'vsSetEndian'):
            value.vsSetEndian(self._vs_bigend)
        elif hasattr(value, '_vs_bigend'):
            value._vs_bigend = self._vs_bigend

    def vsSetEndian(self, bigend):
        if bigend is None:
            raise ValueError('Cannot set endianness of %s to %s' % (self.__class__.__name__, bigend))

        self._vs_bigend = bool(bigend)

        # Now go update all fields this class has
        for _, value in self:
            self._vsUpdateValueEndian(value)

    def vsOverrideValue(self, name, value):
        """
        Sometimes it is necessary to change the value of a read-only field
        because of some internal emulation logic.  This function helps do that.
        """
        self._vs_values[name].vsOverrideValue(value)

    def __setattr__(self, name, value):
        """
        Change the value of a field that has already been registered, or
        register a new field.  If the value provided is a tuple where the first
        element is an integer value, and the second element is a VStruct then
        the field is registered at that specific offset to enable "sparse"
        register/field behavior.
        """
        x = self._vs_values.get(name, None)
        if x is not None:
            return self.vsSetField(name, value)

        # If it's a vstruct type, create a new field
        if isVstructType(value):
            return self.vsAddField(name, value)

        # If the value is a tuple where the first element is an integer and the
        # second is a vstruct type, use the integer as the desired offset for
        # this field
        if isinstance(value, (list, tuple)) and len(value) == 2 and \
                isinstance(value[0], int) and isVstructType(value[1]):
            return self.vsAddField(name, value[1], offset=value[0])

        # Fail over to standard object attribute behavior
        return object.__setattr__(self, name, value)

    def _rebuildFieldOffsetLookup(self):
        """
        Utility used when fields are added to recalculate which fields are
        located at particular offsets and to build the _vs_field_offset lookup
        table to enable faster lookup specific fields based on offset.
        """
        self._vs_field_by_offset = {}

        end_offset = 0
        prev_fname = None

        # Sort the registered fields by the offset so we can ensure that there
        # are no overlapping fields
        for name, offset in sorted(self._vs_field_offset.items(), key=operator.itemgetter(1)):
            value = self._vs_values[name]

            # Sanity check: make sure that the starting offset does not overlap
            # the previous field
            if offset < end_offset:
                prev_offset = self._vs_field_offset[prev_fname]
                raise ValueError('Field %s@%d overlaps with previous field %s@%d' % (name, offset, prev_fname, prev_offset))

            self._vs_field_by_offset[offset] = (name, value)

            end_offset = offset + len(value)
            prev_fname = name

        self._vs_sorted_offsets = sorted(self._vs_field_by_offset)

    def vsInsertField(self, name, value, befname, offset=None):
        """
        Insert a field before an existing field.  If necessary the following
        fields are moved to accommodate the new field.

        Parameters:
            name (string)        : name of the new field
            value (object)       : initial value of the new field
            befname (string)     : field to insert the new field before
            offset (int) optional: offset to use for the new field
        """
        # First update the endianness setting for this field
        if self._vs_bigend is not None:
            self._vsUpdateValueEndian(value)

        super().vsInsertField(name, value, befname)

        if offset is not None:
            if offset not in self._vs_field_offset.values():
                # If offset is specified allow inserting a field into
                # a currently unmapped area, just add the new offset and there
                # is nothing else to do (as long as the new field fits into the
                # space allowed by the old field)
                if len(self._vs_values[befname]) <= len(value):
                    move_offset = None
                    move_amount = 0
                else:
                    # We have to move all fields some small amount to allow the
                    # new field to fit
                    move_offset = offset + len(self._vs_values[befname])
                    move_amount = len(value) - len(self._vs_values[befname])
            else:
                # Sanity check
                assert self._vs_field_offset[name] == offset
                move_offset = offset
                move_amount = len(value)
        else:
            move_offset = self._vs_field_offset[befname]
            move_amount = len(value)

        # Recalculate the field offsets for all fields that follow "befname"
        if move_offset:
            for fname, foffset in self._vs_field_offset.items():
                if foffset >= move_offset:
                    self._vs_field_offset[fname] += move_amount

        self._rebuildFieldOffsetLookup()

    def vsAddField(self, name, value, offset=None):
        """
        Add a new field. If an explicit offset is specified then the field will
        be placed at that offset and an error will be raised if there is not
        enough space before the next field with an explicit offset.

        If an offset is not specified then the field will automatically be
        assigned an offset that points to the current end of the fields.

        Parameters:
            name (string)        : name of the new field
            value (object)       : initial value of the new field
            offset (int) optional: offset to use for the new field
        """
        # First update the endianness setting for this field
        if self._vs_bigend is not None:
            self._vsUpdateValueEndian(value)

        super().vsAddField(name, value)
        if offset is None:
            # Because the field offsets haven't been updated yet use the len()
            # function to find out the next offset to use
            offset = len(self)

        self._vs_field_offset[name] = offset
        self._rebuildFieldOffsetLookup()

    def __len__(self):
        """
        Returns the effective length of all fields by starting from the largest
        offset and returning the offset + length of that element.
        """
        max_fname, max_foffset = max(self._vs_field_offset.items(), key=lambda x: x[1])
        max_fname_size = len(self._vs_values[max_fname])
        return max_foffset + max_fname_size

    # TODO: could speed things up some with direct callback lookups that instead
    # of assigning callback functions to a name-based dictionary

    def _getFieldByOffset(self, offset, names=None):
        """
        Utility used to retrieve the name, index, and field of a field by
        offset.  Searches first in the _vs_field_by_offset array, if not found
        there will use bisect to quickly find the closest field.
        """
        if names is None:
            names = []

        match = self._vs_field_by_offset.get(offset)
        if match is not None:
            fname, field = match
            names.append(fname)
            return names, field, 0

        oidx = bisect.bisect(self._vs_sorted_offsets, offset)

        # The >= offset will always be one index to the left of the returned
        # value
        if oidx == 0 or oidx > len(self._vs_sorted_offsets):
            # This object does not contain the requested offset
            raise VStructDataError(data=b'')

        foffset = self._vs_sorted_offsets[oidx - 1]
        fname, field = self._vs_field_by_offset[foffset]
        # Confirm that the field offset + field length includes the target
        # offset
        if foffset + len(field) <= offset:
            raise VStructDataError(data=b'')

        names.append(fname)

        off = offset - foffset
        return names, field, off

    def vsGetFieldByOffset(self, offset, names=None):
        names, field, foffset = self._getFieldByOffset(offset, names=names)

        # If foffset is not 0, we need to look into the field
        if foffset:
            return field.vsGetFieldByOffset(foffset, names)
        else:
            return '.'.join(names), field

    def vsEmitFromOffset(self, offset, size):
        """
        Variant of the standard VStruct vsEmit() function but instead starting
        at a specific offset one or more elements are emitted based on the
        desired amount of data to read.
        """
        data = bytearray()
        try:
            while len(data) < size:
                # As long as more data is requested, continue reading it
                names, field, foffset = self._getFieldByOffset(offset+len(data))

                if hasattr(field, 'vsEmitFromOffset'):
                    data += field.vsEmitFromOffset(foffset, size - len(data))
                elif not foffset:
                    data += field.vsEmit()
                else:
                    if foffset >= len(field):
                        # This offset is beyond the identified field
                        raise VStructDataError()
                    else:
                        # We can't evenly emit a subfield so just stop now
                        raise VStructAlignmentError()

        except VSTRUCT_ADD_DATA_ERROR_TYPES as exc:
            # Ensure that the amount of data read is recorded in the exception
            exc.kwargs['data'] = data
            raise exc

        return data

    def vsParseAtOffset(self, offset, data, data_offset=0):
        """
        Variant of the standard VStruct vsParse() function but instead starting
        at a specific offset data is parsed into one or more elements based on
        the amount of data to be written.
        """
        written = 0
        try:
            while data_offset < len(data):
                # As long as there is data to parse into a structure, find the
                # next field and parse data into it
                names, field, foffset = self._getFieldByOffset(offset)

                if hasattr(field, 'vsParseAtOffset'):
                    ret_offset = field.vsParseAtOffset(foffset, data, data_offset)
                    written_len = ret_offset - foffset
                elif not foffset:
                    ret_offset = field.vsParse(data, offset=data_offset)
                    written_len = ret_offset - data_offset
                else:
                    if foffset >= len(field):
                        # This offset is beyond the identified field
                        raise VStructDataError()
                    else:
                        # We can't parse into a subfield so just stop now
                        raise VStructAlignmentError()

                offset += written_len
                data_offset += written_len

                # Update the count of how much data has been written
                written += written_len

                # Finally fire any parse callbacks
                self._vsFireCallbacks(names[0])

        except VSTRUCT_ADD_DATA_ERROR_TYPES as exc:
            # Ensure that the amount of data parsed is recorded in the exception
            exc.kwargs['data'] = data[data_offset-written:data_offset] + exc.kwargs.get('data', b'')
            raise exc

        return offset

    def init(self, emu):
        # If the endianness of this register set has not yet been defined, set
        # it now
        if self._vs_bigend is None:
            bigend = emu.getEndian()
            self.vsSetEndian(bigend)

        for _, value in self:
            if hasattr(value, 'init') and callable(value.init):
                value.init(emu)

    def reset(self, emu):
        for _, value in self:
            if hasattr(value, 'reset') and callable(value.reset):
                value.reset(emu)
            elif isinstance(value, VArray):
                for _, elem in value:
                    if hasattr(elem, 'reset') and callable(elem.reset):
                        elem.reset(emu)

    def vsGetPrintInfo(self, offset=0, indent=0, top=True):
        """
        Adapted version of the VStruct.vsGetPrintInfo() function that prints
        the proper field offsets rather than just their storage offset.
        """
        ret = []
        if top:
            ret.append((offset, indent, self._vs_name, self))
        indent += 1
        for fname in self._vs_fields:
            x = self._vs_values.get(fname)
            off = self._vs_field_offset[fname]
            if isinstance(x, VStruct):
                ret.append((off, indent, fname, x))
                ret.extend(x.vsGetPrintInfo(offset=off, indent=indent, top=False))
            else:
                ret.append((off, indent, fname, x))
        # returns (offset, indent, fieldname, field_instance)
        return ret




class BitFieldSPR(PeriphRegister):
    """
    A PeriphRegister object specifically for attaching SPR read/write handlers
    to an emulator-registered register module.  This allows SPRs to be
    automatically reset when the emulator resets, and also for an emulator to
    register "pcb" callbacks to specific SPR bits such as the PowerPC e200z7
    HID0[TBEN] field.
    """
    def __init__(self, spridx, emu):
        """
        Constructor for BitFieldSPR class.

        Parameters:
            spridx (int): The REG_??? value that represents the SPR
            emu (object): The emulator this SPR module should be registered with
        """
        # Use the SPR name as the module name
        super().__init__(emu, emu.getRegisterName(spridx), bigend=emu.getEndian())
        self._reg = spridx

        # SPRs should be 4 or 8 bytes
        width = emu.getRegisterWidth(spridx)
        self._vs_size = ((width + 31) // 32) * 4

        # determine the pack/unpack format now
        self._fmt = e_bits.getFormat(self._vs_size, emu.getEndian())

    def init(self, emu):
        """
        Emulator initializer function, all registered module init() functions
        are called when the emulator processor core's init() function is called.
        """
        emu.addSprReadHandler(self._reg, self.read)
        emu.addSprWriteHandler(self._reg, self.write)

        super().init(emu)

    def read(self, emu, op):
        """
        Handles SPR read requests, returns the current value of the object
        returned by vsEmit() as an integer.
        """
        # vsEmit() returns bytes, convert to an integer value
        return struct.unpack(self._fmt, self.vsEmit())[0]

    def write(self, emu, op):
        """
        Handles SPR write requests, accepts the operands of the write
        instruction, and parses the new value in the source operand into this
        object with vsParse().

        The current value of the object is then read with vsEmit() and returned
        so that the "simple" SPR register will hold the correct value. The
        vsEmit() value is used instead of the operand value because there may
        be special bitfield processing that causes the new "current" SPR value
        to be different than the value being written by the operand.
        """
        # Convert operand 1 to bytes before it can be parsed
        write_val = emu.getOperValue(op, 1)
        self.vsParse(struct.pack(self._fmt, write_val))

        # vsEmit() returns bytes, convert to an integer value
        return struct.unpack(self._fmt, self.vsEmit())[0]
