"""Minimal DBPF 2.1 reader and STBL parser for The Sims 4.

Runs offline on a normal Python, so it may use zlib/struct freely. Only the
runtime lookup shipped inside the mod has to stay import-light.
"""
import struct
import zlib

TYPE_STBL = 0x220557DA

COMP_NONE = 0x0000
COMP_STREAMABLE = 0xFFFE
COMP_UNCOMPRESSED = 0xFFFF
COMP_ZLIB = 0x5A42


class Entry(object):
    __slots__ = ('type', 'group', 'instance', 'position', 'size',
                 'size_decompressed', 'compression')

    def __init__(self, type_, group, instance, position, size,
                 size_decompressed, compression):
        self.type = type_
        self.group = group
        self.instance = instance
        self.position = position
        self.size = size
        self.size_decompressed = size_decompressed
        self.compression = compression

    @property
    def locale(self):
        """Top byte of the instance id is the language code; 0 is English."""
        return self.instance >> 56


def refpack_decompress(data):
    """EA RefPack / QFS. Rare in TS4 but present in some resources."""
    pos = 0
    signature = struct.unpack_from('>H', data, pos)[0]
    pos += 2
    width = 4 if signature & 0x8000 else 3
    if signature & 0x0100:
        pos += width
    out = bytearray()
    pos += width  # uncompressed size, we grow dynamically instead

    while pos < len(data):
        control = data[pos]
        pos += 1
        if control < 0x80:
            b1 = data[pos]
            pos += 1
            plain = control & 0x03
            out += data[pos:pos + plain]
            pos += plain
            count = ((control & 0x1C) >> 2) + 3
            offset = ((control & 0x60) << 3) + b1 + 1
        elif control < 0xC0:
            b1 = data[pos]
            b2 = data[pos + 1]
            pos += 2
            plain = (b1 >> 6) & 0x03
            out += data[pos:pos + plain]
            pos += plain
            count = (control & 0x3F) + 4
            offset = ((b1 & 0x3F) << 8) + b2 + 1
        elif control < 0xE0:
            b1 = data[pos]
            b2 = data[pos + 1]
            b3 = data[pos + 2]
            pos += 3
            plain = control & 0x03
            out += data[pos:pos + plain]
            pos += plain
            count = ((control & 0x0C) << 6) + b3 + 5
            offset = ((control & 0x10) << 12) + (b1 << 8) + b2 + 1
        elif control < 0xFC:
            plain = ((control & 0x1F) + 1) * 4
            out += data[pos:pos + plain]
            pos += plain
            continue
        else:
            plain = control & 0x03
            out += data[pos:pos + plain]
            pos += plain
            break
        start = len(out) - offset
        if start < 0:
            raise ValueError('refpack back-reference before start')
        for i in range(count):
            out.append(out[start + i])
    return bytes(out)


def read_index(path):
    """Yield Entry objects for every resource in a package."""
    with open(path, 'rb') as handle:
        header = handle.read(96)
        if len(header) < 96 or header[:4] != b'DBPF':
            return []
        count = struct.unpack_from('<I', header, 0x24)[0]
        index_size = struct.unpack_from('<I', header, 0x2C)[0]
        index_pos = struct.unpack_from('<Q', header, 0x40)[0]
        if not count or not index_pos:
            return []
        handle.seek(index_pos)
        blob = handle.read(index_size)

    pos = 0
    flags = struct.unpack_from('<I', blob, pos)[0]
    pos += 4
    const_type = const_group = const_inst_hi = None
    if flags & 0x1:
        const_type = struct.unpack_from('<I', blob, pos)[0]
        pos += 4
    if flags & 0x2:
        const_group = struct.unpack_from('<I', blob, pos)[0]
        pos += 4
    if flags & 0x4:
        const_inst_hi = struct.unpack_from('<I', blob, pos)[0]
        pos += 4

    entries = []
    for _ in range(count):
        if const_type is None:
            type_ = struct.unpack_from('<I', blob, pos)[0]
            pos += 4
        else:
            type_ = const_type
        if const_group is None:
            group = struct.unpack_from('<I', blob, pos)[0]
            pos += 4
        else:
            group = const_group
        if const_inst_hi is None:
            inst_hi = struct.unpack_from('<I', blob, pos)[0]
            pos += 4
        else:
            inst_hi = const_inst_hi
        inst_lo = struct.unpack_from('<I', blob, pos)[0]
        pos += 4
        position = struct.unpack_from('<I', blob, pos)[0]
        pos += 4
        raw_size = struct.unpack_from('<I', blob, pos)[0]
        pos += 4
        size_dec = struct.unpack_from('<I', blob, pos)[0]
        pos += 4
        compression = COMP_NONE
        if raw_size & 0x80000000:
            compression = struct.unpack_from('<H', blob, pos)[0]
            pos += 4  # compression u16 + committed u16
        entries.append(Entry(type_, group, (inst_hi << 32) | inst_lo,
                             position, raw_size & 0x7FFFFFFF,
                             size_dec, compression))
    return entries


def read_resource(path, entry):
    with open(path, 'rb') as handle:
        handle.seek(entry.position)
        raw = handle.read(entry.size)
    # Sizes matching means nothing was compressed, whatever the flag claims.
    if entry.size == entry.size_decompressed:
        return raw
    if entry.compression == COMP_NONE:
        return raw
    if entry.compression == COMP_ZLIB:
        return zlib.decompress(raw)
    # 0xFFFF and 0xFFFE are both EA internal RefPack in TS4, despite 0xFFFF
    # being documented elsewhere as "uncompressed".
    if entry.compression in (COMP_UNCOMPRESSED, COMP_STREAMABLE):
        return refpack_decompress(raw)
    try:
        return zlib.decompress(raw)
    except Exception:
        return refpack_decompress(raw)


def parse_stbl(data):
    """STBL v5 -> {key_hash: text}. Returns {} for other versions."""
    if len(data) < 21 or data[:4] != b'STBL':
        return {}
    version = struct.unpack_from('<H', data, 4)[0]
    if version != 5:
        return {}
    num_entries = struct.unpack_from('<Q', data, 7)[0]
    pos = 21
    out = {}
    for _ in range(num_entries):
        if pos + 7 > len(data):
            break
        key = struct.unpack_from('<I', data, pos)[0]
        length = struct.unpack_from('<H', data, pos + 5)[0]
        pos += 7
        text = data[pos:pos + length]
        pos += length
        if text:
            try:
                out[key] = text.decode('utf-8')
            except UnicodeDecodeError:
                out[key] = text.decode('utf-8', 'replace')
    return out
