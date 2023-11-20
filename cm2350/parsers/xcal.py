import io
import enum
import struct

import logging
logger = logging.getLogger(__name__)

import envi.const as e_const
import envi.common as e_common
import vivisect.const as viv_const
import vivisect.parsers as viv_parsers

__all__ = [
    'parse_ihex',

    # The vivisect parser module standard functions
    'parseFile',
    'parseMemory',
]


class CODE(enum.IntEnum):
    DATA = 0
    EOF = 1
    EXT_SEG_ADDR = 2
    START_SEG_ADDR = 3
    EXT_LINEAR_ADDR = 4
    START_LINEAR_ADDR = 5


def checksum(data, init=0):
    """
    Performs a simple 1-byte checksum as used by the ihex file format
    """
    val = init
    for i in range(len(data)):
        val = (val + data[i]) & 0xFF
    return val


def parse_ihex(filename):
    """
    Utility wrapper around the parse function
    """
    with open(filename, 'r') as f:
        blocks, _ = parse(f.read())
        return blocks


def parse(data):
    """
    Parses ihex files and ignores any invalid data
    """
    blocks = {}
    entrypoints = []
    cur_block = None
    cur_offset = None
    offset = 0

    # readlines is really useful for this and ihex files only use ascii 
    # characters so treat the incoming bytes as string data
    with io.StringIO(data) as f:
        lines = f.readlines()

    for line in lines:
        # Check
        if line[0] != ':':
            continue

        # convert the line to bytes (drop the ':' and newline)
        line_data = bytes.fromhex(line.strip(':\r\n'))

        # Validate the checksum
        assert checksum(line_data) == 0

        size, addr, code = struct.unpack_from('>BHB', line_data)

        # 4 bytes of header + 1 byte of checksum
        assert len(line_data) == size + 5

        # Determine if the data should be treated as bytes or an integer
        if code == CODE.DATA:
            if cur_block is not None and \
                    cur_offset + len(cur_block) != offset + addr:
                logger.log(e_common.MIRE, 'saving block 0x%x: 0x%x bytes', cur_offset, len(cur_block))
                blocks[cur_offset] = cur_block
                cur_block = bytearray()
                cur_offset = offset + addr

            elif cur_block is None:
                cur_block = bytearray()
                cur_offset = offset + addr

            cur_block += line_data[4:-1]

        elif code == CODE.EOF:
            logger.log(e_common.MIRE, CODE(code).name)
            break

        elif code == CODE.EXT_SEG_ADDR:
            assert size == 2
            base = struct.unpack_from('>H', line_data, 4)[0]
            offset = base * 16
            logger.log(e_common.MIRE, '%s: 0x%04x -> 0x%08x', CODE(code).name, base, offset)

        elif code == CODE.START_SEG_ADDR:
            cs, ip = struct.unpack_from('>HH', line_data, 4)[0]
            offset = (cs << 4) + ip
            entrypoints.append(offset)
            logger.log(e_common.MIRE, '%s: 0x%04x, 0x%04x -> 0x%08x', CODE(code).name, cs, ip, offset)

        elif code == CODE.EXT_LINEAR_ADDR:
            assert size == 2
            base = struct.unpack_from('>H', line_data, 4)[0]
            offset = base << 16
            logger.log(e_common.MIRE, '%s: 0x%04x -> 0x%08x', CODE(code).name, base, offset)

        elif code == CODE.START_LINEAR_ADDR:
            offset = struct.unpack_from('>I', line_data, 4)[0]
            entrypoints.append(offset)
            logger.log(e_common.MIRE, '%s: 0x%08x', CODE(code).name, offset)

    # Save the last block
    if cur_block is not None:
        logger.log(e_common.MIRE, 'saving block 0x%x: 0x%x bytes', cur_offset, len(cur_block))
        blocks[cur_offset] = cur_block

    return (blocks, entrypoints)


def parseFile(vw, filename, baseaddr=None):
    """
    Designed to be used by vivisect as one of the file parser modules
    """
    logger.info('Loading XCAL file %s', filename)

    with open(filename, 'rb') as f:
        data = f.read()

    # Re-use the settings from the ihex parser, but don't throw an error if 
    # there is no arch set. the project will define an arch.
    arch = vw.config.viv.parsers.ihex.arch
    if arch:
        vw.setMeta('Architecture', arch)
        vw.setMeta('bigend', vw.config.viv.parsers.ihex.bigend)
        vw.setMeta('DefaultCall', viv_const.archcalls.get(arch, 'unknown'))
        vw.setMeta('Platform', 'Unknown')

    vw.setMeta('Format', 'ihex')

    # We need two SHA256 hashes to collect the information that should be 
    # collected by a vivisect file parser. Also an MD5 is attached to the 
    # filename
    fname = vw.addFile(filename, 0, viv_parsers.md5Bytes(data))
    vw.setFileMeta(fname, 'sha256', viv_parsers.sha256Bytes(data))

    # Gather only the valid ihex data
    with io.BytesIO(data) as f:
        lines = f.readlines()
        prefix = ord(b':')
        ihex_data = b''.join(l for l in lines if l[0] == prefix)

    vw.setFileMeta(fname, 'sha256_ihex', viv_parsers.sha256Bytes(ihex_data))

    # ihex and xcal files should all be ascii
    try:
        blocks, entrypoints = parse(ihex_data.decode())
    except UnicodeDecodeError:
        # Not a valid ihex/xcal file
        raise Exception('%s not a valid xcal (ihex) file' % filename)

    for addr, data in blocks.items():
        logger.info('adding memory map from IHEX: 0x%x - 0x%x', addr, addr + len(data))
        vw.addMemoryMap(addr, e_const.MM_RWX, '', data)
        vw.addSegment(addr, len(data), '%.8x' % addr, fname)

    for eva in entrypoints:
        if eva is not None:
            logger.info('adding function from IHEX metadata: 0x%x', eva)
            vw.addEntryPoint(eva)


def parseMemory(vw, memobj, baseaddr):
    raise Exception('xcal loader cannot parse memory!')
