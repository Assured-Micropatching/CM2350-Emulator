### memory mapped io
import envi
import envi.memory as e_mem

PERM_MMIO = 0x80000000
MMIO_READ_HANDLER = 0
MMIO_WRITE_HANDLER = 1
MMIO_BYTES_REF = 2
MMIO_LAST_REF = MMIO_BYTES_REF


class ComplexMemoryMap(e_mem.MemoryObject):
    def addMemoryMap(self, va, perms, fname, bytez, align=None):
        '''
        Add a memory map to this object...
        Changes the data (bytez) to be a bytearray first to allow for in-place
        modification of the memory map contents.
        '''
        if align:
            curlen = len(bytez)
            newlen = e_bits.align(curlen, align)
            delta = newlen - curlen
            bytez += b'\x00' * delta

        msize = len(bytez)
        mmap = (va, msize, perms, fname)
        hlpr = [va, va+msize, mmap, bytearray(bytez)]
        self._map_defs.append(hlpr)
        return msize

    def addMMIO(self, va, msize, fname, mmio_read, mmio_write, mmio_bytes=None, mmio_perm=e_mem.MM_READ_WRITE):
        '''
        Add a MMIO map to this object...
        '''
        mmap = (va, msize, PERM_MMIO | mmio_perm, fname)
        hlpr = [va, va+msize, mmap, (mmio_read, mmio_write, mmio_bytes)]
        self._map_defs.append(hlpr)

    def readMemory(self, va, size):
        for mva, mmaxva, mmap, mbytes in self._map_defs:
            if va >= mva and va + size <= mmaxva:
                mva, msize, mperms, mfname = mmap
                offset = va - mva

                # Confirm that this segment can be read
                if not (mperms & e_mem.MM_READ or self._supervisor):
                    raise envi.SegmentationViolation(va)

                if mperms & PERM_MMIO:
                    # handle MMIO first
                    return mbytes[MMIO_READ_HANDLER](va, offset, size)
                else:
                    return mbytes[offset:offset+size]

        raise envi.SegmentationViolation(va)

    def writeMemory(self, va, bytez):
        for mapdef in self._map_defs:
            mva, mmaxva, mmap, mbytes = mapdef
            if va >= mva and va < mmaxva:
                mva, msize, mperms, mfname = mmap
                offset = va - mva

                # Confirm that this segment can be read
                if not (mperms & e_mem.MM_WRITE or self._supervisor):
                    raise envi.SegmentationViolation(va)

                if mperms & PERM_MMIO:
                    # handle MMIO first
                    mbytes[MMIO_WRITE_HANDLER](va, offset, bytez)
                else:
                    # Standard byte-backed memory segments are assumed to allow
                    # 1-byte aligned memory access, so don't need checked
                    mbytes[offset:offset+len(bytez)] = bytez
                return

        raise envi.SegmentationViolation(va)

    def getByteDef(self, va):
        '''
        Return bytes representing the entire memory block.  Used mostly for
        parsing instructions out of a block of memory.
        '''
        for mapdef in self._map_defs:
            mva, mmaxva, mmap, mbytes = mapdef
            if va >= mva and va < mmaxva:
                mva, msize, mperms, mfname = mmap
                offset = va - mva

                if mperms & PERM_MMIO:
                    # handle MMIO first
                    get_bytes_func = mbytes[MMIO_BYTES_REF]
                    if get_bytes_func  is not None:
                        return (offset, get_bytes_func())
                    else:
                        # not all MMIO regions may provide a "getBytesDef"
                        # support function, in that case just return an empty
                        # byte string, the access is not invalid, but this is
                        # most likely a device that will not behave correctly if
                        # accessed like normal bytes-memory
                        return (offset, b'')

                # otherwise, retrieve the byte definition for this memory
                # segment as normal
                offset = va - mva
                return (offset, mbytes)

        raise envi.SegmentationViolation(va)


class MMIO_DEVICE:
    '''
    MMIO devices have a control mechanism snapped into a ComplexMemoryMap object
    and functions are called on access (read/write) instead of updating a
    memory map.

    This class should be subclassed.  Training-Wheels versions of _mmio_read()
    and _mmio_write() are provided.
    '''
    def __init__(self, emu, devname, mapaddr, mapsize, **kwargs):
        self.emu = emu
        emu.addMMIO(mapaddr, mapsize, devname, self._mmio_read, self._mmio_write, **kwargs)

    def _mmio_write(self, va, offset, bytez):
        print("%r: [%x] = %r" % (self.__class__, va, bytez))

    def _mmio_read(self, va, offset, size):
        print("%r: read [%x:%r]" % (self.__class__, va, size))
        return "@" * size

    def _mmio_bytes(self):
        return b''

    def __getstate__(self):
        return 'FAKESTATE'

    def __setstate__(self, state):
        print("restoring: %r" % state)


# MMIO Exceptions
class MmioReadException(Exception):
    def __init__(self, va, size):
        Exception.__init__(self)
        self.va = va
        self.size = size

    def __repr__(self):
        return "(%r) attempting to read %d bytes from reserved MMIO region: 0x%x" %\
                (self.__class__, self.size, self.va)


class MmioWriteException(Exception):
    def __init__(self, va, bytez):
        Exception.__init__(self)
        self.va = va
        self.bytez = bytez

    def __repr__(self):
        return "(%r) attempting to write to reserved MMIO region: 0x%x (%r)" %\
                (self.__class__, self.va, self.bytez)


class TESTMMIO(str):
    def __add__(self, *args, **kwargs):
        res = str.__add__(self, *args, **kwargs)
        print("=__add__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __class__(self, *args, **kwargs):
        res = str.__class__(self, *args, **kwargs)
        print("=__class__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __contains__(self, *args, **kwargs):
        res = str.__contains__(self, *args, **kwargs)
        print("=__contains__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __delattr__(self, *args, **kwargs):
        res = str.__delattr__(self, *args, **kwargs)
        print("=__delattr__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __doc__(self, *args, **kwargs):
        res = str.__doc__(self, *args, **kwargs)
        print("=__doc__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __eq__(self, *args, **kwargs):
        res = str.__eq__(self, *args, **kwargs)
        print("=__eq__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __format__(self, *args, **kwargs):
        res = str.__format__(self, *args, **kwargs)
        print("=__format__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __ge__(self, *args, **kwargs):
        res = str.__ge__(self, *args, **kwargs)
        print("=__ge__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __getattribute__(self, *args, **kwargs):
        res = str.__getattribute__(self, *args, **kwargs)
        print("=__getattribute__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __getitem__(self, *args, **kwargs):
        res = str.__getitem__(self, *args, **kwargs)
        print("=__getitem__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __getnewargs__(self, *args, **kwargs):
        res = str.__getnewargs__(self, *args, **kwargs)
        print("=__getnewargs__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __getslice__(self, *args, **kwargs):
        res = str.__getslice__(self, *args, **kwargs)
        print("=__getslice__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __gt__(self, *args, **kwargs):
        res = str.__gt__(self, *args, **kwargs)
        print("=__gt__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __hash__(self, *args, **kwargs):
        res = str.__hash__(self, *args, **kwargs)
        print("=__hash__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __init__(self, *args, **kwargs):
        res = str.__init__(self, *args, **kwargs)
        print("=__init__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __le__(self, *args, **kwargs):
        res = str.__le__(self, *args, **kwargs)
        print("=__le__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __len__(self, *args, **kwargs):
        res = str.__len__(self, *args, **kwargs)
        print("=__len__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __lt__(self, *args, **kwargs):
        res = str.__lt__(self, *args, **kwargs)
        print("=__lt__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __mod__(self, *args, **kwargs):
        res = str.__mod__(self, *args, **kwargs)
        print("=__mod__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __mul__(self, *args, **kwargs):
        res = str.__mul__(self, *args, **kwargs)
        print("=__mul__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __ne__(self, *args, **kwargs):
        res = str.__ne__(self, *args, **kwargs)
        print("=__ne__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __new__(self, *args, **kwargs):
        res = str.__new__(self, *args, **kwargs)
        print("=__new__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __reduce__(self, *args, **kwargs):
        res = str.__reduce__(self, *args, **kwargs)
        print("=__reduce__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __reduce_ex__(self, *args, **kwargs):
        res = str.__reduce_ex__(self, *args, **kwargs)
        print("=__reduce_ex__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __repr__(self, *args, **kwargs):
        res = str.__repr__(self, *args, **kwargs)
        print("=__repr__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __rmod__(self, *args, **kwargs):
        res = str.__rmod__(self, *args, **kwargs)
        print("=__rmod__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __rmul__(self, *args, **kwargs):
        res = str.__rmul__(self, *args, **kwargs)
        print("=__rmul__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __setattr__(self, *args, **kwargs):
        res = str.__setattr__(self, *args, **kwargs)
        print("=__setattr__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __sizeof__(self, *args, **kwargs):
        res = str.__sizeof__(self, *args, **kwargs)
        print("=__sizeof__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __str__(self, *args, **kwargs):
        res = str.__str__(self, *args, **kwargs)
        print("=__str__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def __subclasshook__(self, *args, **kwargs):
        res = str.__subclasshook__(self, *args, **kwargs)
        print("=__subclasshook__=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def _formatter_field_name_split(self, *args, **kwargs):
        res = str._formatter_field_name_split(self, *args, **kwargs)
        print("=_formatter_field_name_split=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def _formatter_parser(self, *args, **kwargs):
        res = str._formatter_parser(self, *args, **kwargs)
        print("=_formatter_parser=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def capitalize(self, *args, **kwargs):
        res = str.capitalize(self, *args, **kwargs)
        print("=capitalize=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def center(self, *args, **kwargs):
        res = str.center(self, *args, **kwargs)
        print("=center=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def count(self, *args, **kwargs):
        res = str.count(self, *args, **kwargs)
        print("=count=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def decode(self, *args, **kwargs):
        res = str.decode(self, *args, **kwargs)
        print("=decode=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def encode(self, *args, **kwargs):
        res = str.encode(self, *args, **kwargs)
        print("=encode=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def endswith(self, *args, **kwargs):
        res = str.endswith(self, *args, **kwargs)
        print("=endswith=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def expandtabs(self, *args, **kwargs):
        res = str.expandtabs(self, *args, **kwargs)
        print("=expandtabs=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def find(self, *args, **kwargs):
        res = str.find(self, *args, **kwargs)
        print("=find=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def format(self, *args, **kwargs):
        res = str.format(self, *args, **kwargs)
        print("=format=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def index(self, *args, **kwargs):
        res = str.index(self, *args, **kwargs)
        print("=index=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def isalnum(self, *args, **kwargs):
        res = str.isalnum(self, *args, **kwargs)
        print("=isalnum=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def isalpha(self, *args, **kwargs):
        res = str.isalpha(self, *args, **kwargs)
        print("=isalpha=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def isdigit(self, *args, **kwargs):
        res = str.isdigit(self, *args, **kwargs)
        print("=isdigit=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def islower(self, *args, **kwargs):
        res = str.islower(self, *args, **kwargs)
        print("=islower=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def isspace(self, *args, **kwargs):
        res = str.isspace(self, *args, **kwargs)
        print("=isspace=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def istitle(self, *args, **kwargs):
        res = str.istitle(self, *args, **kwargs)
        print("=istitle=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def isupper(self, *args, **kwargs):
        res = str.isupper(self, *args, **kwargs)
        print("=isupper=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def join(self, *args, **kwargs):
        res = str.join(self, *args, **kwargs)
        print("=join=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def ljust(self, *args, **kwargs):
        res = str.ljust(self, *args, **kwargs)
        print("=ljust=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def lower(self, *args, **kwargs):
        res = str.lower(self, *args, **kwargs)
        print("=lower=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def lstrip(self, *args, **kwargs):
        res = str.lstrip(self, *args, **kwargs)
        print("=lstrip=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def partition(self, *args, **kwargs):
        res = str.partition(self, *args, **kwargs)
        print("=partition=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def replace(self, *args, **kwargs):
        res = str.replace(self, *args, **kwargs)
        print("=replace=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def rfind(self, *args, **kwargs):
        res = str.rfind(self, *args, **kwargs)
        print("=rfind=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def rindex(self, *args, **kwargs):
        res = str.rindex(self, *args, **kwargs)
        print("=rindex=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def rjust(self, *args, **kwargs):
        res = str.rjust(self, *args, **kwargs)
        print("=rjust=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def rpartition(self, *args, **kwargs):
        res = str.rpartition(self, *args, **kwargs)
        print("=rpartition=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def rsplit(self, *args, **kwargs):
        res = str.rsplit(self, *args, **kwargs)
        print("=rsplit=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def rstrip(self, *args, **kwargs):
        res = str.rstrip(self, *args, **kwargs)
        print("=rstrip=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def split(self, *args, **kwargs):
        res = str.split(self, *args, **kwargs)
        print("=split=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def splitlines(self, *args, **kwargs):
        res = str.splitlines(self, *args, **kwargs)
        print("=splitlines=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def startswith(self, *args, **kwargs):
        res = str.startswith(self, *args, **kwargs)
        print("=startswith=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def strip(self, *args, **kwargs):
        res = str.strip(self, *args, **kwargs)
        print("=strip=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def swapcase(self, *args, **kwargs):
        res = str.swapcase(self, *args, **kwargs)
        print("=swapcase=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def title(self, *args, **kwargs):
        res = str.title(self, *args, **kwargs)
        print("=title=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def translate(self, *args, **kwargs):
        res = str.translate(self, *args, **kwargs)
        print("=translate=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def upper(self, *args, **kwargs):
        res = str.upper(self, *args, **kwargs)
        print("=upper=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

    def zfill(self, *args, **kwargs):
        res = str.zfill(self, *args, **kwargs)
        print("=zfill=(%r, %r) = %r" % (repr(args), repr(kwargs), res))
        return res

