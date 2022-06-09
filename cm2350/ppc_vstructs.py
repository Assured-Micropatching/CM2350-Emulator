import bisect
import struct
import operator
import vstruct.bitfield
import vstruct.primitives
import envi.bits as e_bits

from .intc_exc import AlignmentException, MceWriteBusError, MceDataReadBusError

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
    'ReadOnlyRegister',
    'WriteOnlyRegister',
    'PeripheralRegisterSet',
    'BitFieldSPR',
]


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
        super().__init__(width)

        # To mimic the __len__ behavior of the v_number class translate the
        # _vs_bitwidth into the number of bytes wide this object is.  This
        # allows v_bits objects to be used directly in VArrays.  The length will
        # round up to the nearest byte so will not produced correct packed
        # VArray behavior if the size is not a multiple of 8, but that should be
        # ok because this shouldn't be necessary very often.
        self._vs_length = (self._vs_bitwidth + 7) // 8

        # An endianness setting doesn't really matter much for most bitfields,
        # but if this is a multi-byte bitfield it could matter
        self.vsSetEndian(bigend)

        # Set the initial value
        self._vs_value = value

    def vsParse(self, data, offset=0):
        self.vsSetValue(struct.unpack_from(self._vs_fmt, data, offset)[0])
        return offset + self._vs_length

    def vsEmit(self):
        return struct.pack(self._vs_fmt, self._vs_value)

    def vsOverrideValue(self, value):
        self._vs_value = value

    def vsSetEndian(self, bigend):
        """
        Change the saved endianness of this object and the parse/emit format
        """
        self._vs_bigend = bigend
        self._vs_fmt = vstruct.primitives.num_fmts.get((bigend, self._vs_length))


class v_sbits(vstruct.bitfield.v_bits):
    """
    signed v_bits, adds signed number processing to v_bits class.

    This has to inherit from the v_bits class instead of v_snumber because the
    VBitField class specifically looks for v_bits when calculating field sizes.
    """
    def __init__(self, width, value=0, bigend=None):
        super().__init__(width)

        # Values used by _get_svalue()
        self._signed_mask = 2**(self._vs_bitwidth-1)
        self._mask = e_bits.b_masks[self._vs_bitwidth]

        # To mimic the __len__ behavior of the v_number class translate the
        # _vs_bitwidth into the number of bytes wide this object is.  This
        # allows v_bits objects to be used directly in VArrays.  The length will
        # round up to the nearest byte so will not produced correct packed
        # VArray behavior if the size is not a multiple of 8, but that should be
        # ok because this shouldn't be necessary very often.
        self._vs_length = (self._vs_bitwidth + 7) // 8

        # An endianness setting doesn't really matter much for most bitfields,
        # but if this is a multi-byte bitfield it could matter
        self.vsSetEndian(bigend)

        # Set the initial value
        self._vs_value = value

    def _get_svalue(self, value):
        """
        Helper function to return a properly converted signed integer based on
        this field's bitwidth.
        """
        if value & self._signed_mask:
            return -((~value + 1) & self._mask)
        else:
            return value & self._mask

    def vsSetValue(self, value):
        """
        The v_bits class relies on the higher-level VBitField to set the
        correctly sized values, do additional signed conversion now.
        """
        self._vs_value = self._get_svalue(value)

    def vsParse(self, data, offset=0):
        self.vsSetValue(struct.unpack_from(self._vs_fmt, data, offset)[0])
        return offset + self._vs_length

    def vsOverrideValue(self, value):
        self._vs_value = self._get_svalue(value)

    def vsSetEndian(self, bigend):
        """
        Change the saved endianness of this object and the parse/emit format
        """
        self._vs_bigend = bigend
        self._vs_fmt = vstruct.primitives.signed_fmts.get((bigend, self._vs_length))


class v_const(v_bits):
    """
    A variation of the v_bits class. The vsSetValue function will not
    change the _vs_value of this field which makes this class useful for
    defining bitfields in registers that should not be modifiable by standard
    user write operations. Instead the owning peripheral should either directly
    modify _vs_value, or if this field is part of a PeriphRegister object the
    PeriphRegister.vsOverrideValue function can be used.
    """
    def vsSetValue(self, value):
        """
        This is a constant field so the value cannot be modified after creation
        (except by using the vsOverrideValue function).

        Parameters:
            value (int): ignored
        """
        pass

class v_sconst(v_sbits):
    """
    A variation of the v_sbits class. The vsSetValue function will not
    change the _vs_value of this field which makes this class useful for
    defining bitfields in registers that should not be modifiable by standard
    user write operations. Instead the owning peripheral should either directly
    modify _vs_value, or if this field is part of a PeriphRegister object the
    PeriphRegister.vsOverrideValue function can be used.
    """
    def vsSetValue(self, value):
        """
        This is a constant field so the value cannot be modified after creation
        (except by using the vsOverrideValue function).

        Parameters:
            value (int): ignored
        """
        pass


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


class v_bytearray(vstruct.primitives.v_bytes):
    """
    A bytearray-version of v_bytes, this allows in-place parse/emit
    like the VArray type using __getitem__ and __setitem__ operations.
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
        super().__init__(size=size, vbytes=bytearray(vbytes))

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

        if isinstance(elems, (list, tuple)):
            self._vsInitElems(elems)
        elif count and isinstance(elems, type) and \
                issubclass(vstruct.primitives.v_base):
            self._vsInitElems(elems() for i in range(count))
        else:
            raise TypeError('Cannot create %s with %s' % (self.__class__.__name, elems))

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

    def __setitem__(self, index, valu):
        self._vs_elems[index] = vsSetField("%d" % index, valu)

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

    def vsGetFields(self):
        return self.__iter__()

    def vsGetFieldByOffset(self, offset, names=None, coffset=0):
        """
        Modification of the standard VStruct vsGetFieldByOffset() function to
        allow for a faster search because the array elements have consistent
        sizes.
        """
        oidx = offset // self._vs_elem_size
        foffset = oidx * self._vs_elem_size

        fname = str(oidx)
        field = self._vs_elems[oidx]

        # The offset falls somewhere in this field
        names.append(fname)

        off = offset - foffset
        # If the offset is not at 0 we haven't found the start of the target
        if off > 0:
            return field.vsGetFieldByOffset(off, names=names, coffset=0)

        # If no field was found that matches the offset, then this is an invalid
        # address offset
        if not names:
            raise MceDataReadBusError()

        return '.'.join(names), field


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
        raise NotImplementedError()

    def vsEmit(self):
        raise NotImplementedError()


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

        # Save the endianness so we can update all added fields, VBitField
        # doesn't support the bigend parameter so we set it manually now.
        self._vs_bigend = bigend

        if emu is not None:
            if name is None:
                name = self.__class__.__name__
            if name in emu.modules:
                idx = emu.modules.index(name)
                cur_module = emu.modules[idx]
                raise ValueError('Module %s:%r already registered, cannot register %s:%r' % (name, cur_module, name, self))
            emu.modules[name] = self

    def vsSetEndian(self, bigend):
        if bigend is None:
            raise ValueError('Cannot set endianness of %s to %s' % (self.__class__.__name__, bigend))

        self._vs_bigend = bigend

        # Now go update all fields this class has
        for _, value in self:
            self._vsUpdateValueEndian(value)

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

        # Now add field
        super().vsAddField(name, value)
        if not name.startswith('_') and not isinstance(value, PlaceholderRegister):
            self._vs_defaults[name] = value.vsGetValue()

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
        for name, value in self._vs_values.items():
            if name not in self._vs_defaults and hasattr(value, 'reset'):
                value.reset(emu)


class ReadOnlyRegister(PeriphRegister):
    """
    Read-only peripheral register, raises the correct PPC exception when write
    is attempted.
    """
    def vsSetValue(self, value):
        raise MceWriteBusError()

    def vsParse(self, bytez, offset=0):
        raise MceWriteBusError()


class WriteOnlyRegister(PeriphRegister):
    """
    Read-only peripheral register, raises the correct PPC exception when write
    is attempted.
    """
    def vsGetValue(self):
        raise MceDataReadBusError()

    def vsEmit(self):
        raise MceDataReadBusError()


class PeripheralRegisterSet(VStruct):
    """
    VStruct customized class that can hold multiple "registers" (PeriphRegister)
    and provide some standard peripheral-like behavior like:
    - Supporting system init/reset of all contained fields
    - Supporting parse/emit of only a subset of fields because it tracks field
      offset (this allows a sparse register space to exist)
    - Raising standard PPC MachineCheck/Bus errors when reading or writing to
      "reserved" registers

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

        self._vs_bigend = bigend

        self._vs_field_offset = {}

        # Regenerated each time a field is added, makes it faster to find the
        # field to emit from or parse into
        self._vs_field_by_offset = {}
        self._vs_sorted_offsets = []

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

    def vsSetEndian(self, bigend):
        if bigend is None:
            raise ValueError('Cannot set endianness of %s to %s' % (self.__class__.__name__, bigend))

        self._vs_bigend = bigend

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

            # To make emit/parse more efficient if the new field is an array add
            # an entry for each valid offset
            if isinstance(value, v_bytearray):
                for elem_idx in range(0, len(value)):
                    self._vs_field_by_offset[offset + elem_idx] = (name, elem_idx, value)

            elif isinstance(value, VArray):
                elem_size = len(value[0])
                for elem_off in range(0, len(value), elem_size):
                    elem_idx = elem_off // elem_size
                    self._vs_field_by_offset[offset + elem_off] = (name, elem_idx, value)

            else:
                self._vs_field_by_offset[offset] = (name, None, value)

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

    def _vsFireCallbacks(self, fname, *args, **kwargs):
        """
        Slight modification of the standard VStruct _vsFireCallbacks function
        that handles extra args that can be passed to the callback functions
        (such as for by_idx_<field> callbacks).
        """
        callback = getattr(self, 'pcb_%s' % fname, None)
        if callback is not None:
            callback(*args, **kwargs)
        cblist = self._vs_pcallbacks.get(fname)
        if cblist is not None:
            for callback in cblist:
                callback(self, *args, **kwargs)

    def vsAddParseCallback(self, fieldname, callback):
        """
        Slight modification of the standard VStruct vsAddParseCallback function
        to be aware of the by_idx_<field> callback convention.

        Adding a callback named by_idx_fieldname will cause the associated
        function to be called whenever an element of a VArray of v_bytearray
        object is written to.

        "by_idx" handlers will be called with 3 parameters compared to the
        normal 1 parameter used in parse callback functions:

            by_idx_fieldname_handler(thing, idx, size)

        "thing" parameter is the VStruct object that the field is a member of
        "idx"   is the index in the field that was modified
        "size"  is the amount of data that is written, because multiple fields
                may be written at the same time. If that happens then the "idx"
                parameter will be the offset of the first element that was
                modified.

        Example from the FlexCAN peripheral for the "mb" field:
            class FlexCAN(ExternalIOPeripheral):
                def __init__(self, ...stuff...):
                    self.registers.vsAddParseCallback('by_idx_mb', self.mbUpdate)

                def mbUpdate(self, thing, idx, size):
                    # check which index (offset) was updated
                    # do stuff
                    pass
        """
        # TODO: This could be sped up by directly associating the callbacks
        # with the field offset so a field name lookup isn't necessary.
        if fieldname[:7] == 'by_idx_':
            fname = fieldname[7:]
        else:
            fname = fieldname

        if self._vs_values.get(fname) is None:
            raise Exception('Invalid Field: %s' % fname)

        cblist = self._vs_pcallbacks.get(fieldname)
        if cblist is None:
            cblist = []
            self._vs_pcallbacks[fieldname] = cblist

        cblist.append(callback)

    def _getValueByOffsetLookup(self, addr):
        """
        Utility used to retrieve the value of a field by an offset.  This only
        uses the _vs_field_by_offset offset lookup table to find a valid
        field. This is faster but less complete of a lookup than using
        vsGetFieldByOffset() function.

        For PowerPC register behavior it is assumed that only entire registers
        can be read or written.  For non-emulation related read or write
        actions the vsGetFieldByOffset() function would allow writing or
        reading a sub element of a register field, but it performs a slower
        lookup.
        """
        try:
            return self._vs_field_by_offset[addr]
        except KeyError:
            # Do a slower check to see if this address is valid, but it cannot
            # be completed because it is improperly aligned.
            name, field = self.vsGetFieldByOffset(addr)
            logger.debug('Found %s (%s) at address 0x%x', name, field, addr)

            # A valid field was found, but because we can't index it that means
            # the original read was not properly aligned
            raise AlignmentException()

    def vsEmitFromOffset(self, addr, size):
        """
        Variant of the standard VStruct vsEmit() function but instead starting
        at a specific offset one or more elements are emitted based on the
        desired amount of data to read.
        """
        # Find the field that corresponds to the specified address
        data = b''
        addr_offset = 0
        try:
            while len(data) < size:
                name, idx, value = self._getValueByOffsetLookup(addr + addr_offset)

                # Now that we have valid name and index, read data
                if idx is not None:
                    if isinstance(value, v_bytearray):
                        # If this is a v_byetarray the bytes to emit directly from
                        # the value at the right offset
                        new_data = value._vs_value[idx:idx+size]

                    else:
                        new_data = value[idx].vsEmit()
                else:
                    new_data = value.vsEmit()

                addr_offset += len(new_data)
                data += new_data

        except (AlignmentException, MceDataReadBusError) as exc:
            # Add an indication of how much data was read before the exception
            # happened
            exc.kwargs['data'] = data
            raise exc

        # If we have grabbed more data than the size specified it means the read
        # operation was not properly size-aligned (because PPC)
        if len(data) > size:
            # Indicate how much data has been read
            raise AlignmentException(data=data)
        return data

    def vsParseAtOffset(self, addr, bytez, offset=0):
        """
        Variant of the standard VStruct vsParse() function but instead starting
        at a specific offset data is parsed into one or more elements based on
        the amount of data to be written.
        """
        addr_offset = 0
        try:
            while offset < len(bytez):
                name, idx, value = self._getValueByOffsetLookup(addr + addr_offset)

                if idx is not None:
                    if isinstance(value, v_bytearray):
                        # If this is a v_byetarray the bytes to parse can just
                        # be written directly into the value at the right offset
                        value._vs_value[idx:idx+len(bytez)] = bytez
                        value_len = len(bytez)

                    else:
                        value = value[idx]
                        value.vsParse(bytez, offset=offset)
                        value_len = len(value)

                        # It's possible for specific array elements to have
                        # callbacks, trigger those now if any are set
                        value._vsFireCallbacks(str(idx))

                    # Since this is an VArray (or v_bytearray) see if there is a
                    # 'by_idx_<field>' callback defined and if so call it
                    self._vsFireCallbacks('by_idx_%s' % name, idx=idx, size=value_len)

                else:
                    value.vsParse(bytez, offset=offset)
                    value_len = len(value)

                    # Now fire the callbacks for this specific field
                    self._vsFireCallbacks(name)

                # Determine how much of the supplied data was used by this field
                addr_offset += value_len
                offset += value_len

        except (AlignmentException, MceWriteBusError) as exc:
            # Indicate how much data was written before the exception occured
            exc.kwargs['written'] = addr_offset
            raise exc

        except MceDataReadBusError as exc:
            # translate MceDataReadBusError exceptions into the correct bus
            # write exception

            # Indicate how much data was written before the exception occured
            raise MceWriteBusError(written=addr_offset) from exc

        except ValueError as exc:
            if str(exc) == "invalid literal for int() with base 16: b''":
                # If we get this error it means that there wasn't enough
                # information in the supplied bytes to populate the fields, so
                # this is an alignment error.
                raise AlignmentException(written=addr_offset) from exc
            else:
                # This is something else, re-raise the original exception
                raise exc

        # If the fields attempted to use more data than has was provided
        # we have an alignment error.
        if offset > len(bytez):
            raise AlignmentException(written=addr_offset)

    def vsGetFieldByOffset(self, offset, names=None, coffset=0):
        """
        Modification of the standard VStruct vsGetFieldByOffset() function to
        search faster based on the _vs_field_offset lookup table.
        """
        if names is None:
            names = []

        oidx = bisect.bisect(self._vs_sorted_offsets, offset)

        print(offset, oidx, len(self._vs_sorted_offsets))

        # The >= offset will always be one index to the left of the returned
        # value
        if oidx > 0 and oidx < len(self._vs_sorted_offsets):
            foffset = self._vs_sorted_offsets[oidx-1]
            fname, idx, field = self._vs_field_by_offset[foffset]
            names.append(fname)

            if idx is not None:
                names.append(str(idx))
                field = field[idx]

            if offset < foffset + len(field):
                if foffset == offset:
                    return '.'.join(names), field
                else:
                    # We have not found an exact match yet
                    off = offset - foffset
                    return field.vsGetFieldByOffset(off, names=names, coffset=0)

        # This object does not contain the requested offset
        raise MceDataReadBusError()

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
        self._size = ((width + 31) // 32) * 4

        # determine the pack/unpack format now
        self._fmt = e_bits.getFormat(self._size, emu.getEndian())

    def init(self, emu):
        """
        Emulator initializer function, all registered module init() functions
        are called when the emulator's init_core() function is called.
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
