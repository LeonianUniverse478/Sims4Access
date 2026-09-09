"""Catalog names for object definitions.

A Definition carries no display name at runtime, so the name is looked up in a
table built offline from OBJD resources. Same flat binary shape as the string
table: binary-searched in place, builtins only.
"""
import os

MAGIC = b'A11YOBJ1'
FILENAME = 'a11yscan_objects.bin'
_HEADER = 12
_RECORD = 12

_data = None
_count = 0
_blob_start = 0
_status = 'not loaded'


def _u32(data, pos):
    return int.from_bytes(data[pos:pos + 4], 'little')


def _candidate_paths():
    paths = []
    try:
        here = os.path.dirname(__file__)
        paths.append(os.path.join(here, FILENAME))
        archive = here
        for _ in range(4):
            parent = os.path.dirname(archive)
            if not parent or parent == archive:
                break
            archive = parent
            paths.append(os.path.join(archive, FILENAME))
    except Exception:
        pass
    return paths


def _load():
    global _data, _count, _blob_start, _status
    if _data is not None or _status.startswith('failed'):
        return _data is not None
    raw = None
    try:
        loader = globals().get('__loader__')
        if loader is not None and hasattr(loader, 'get_data'):
            raw = loader.get_data(os.path.join(os.path.dirname(__file__), FILENAME))
    except Exception:
        raw = None
    if raw is None:
        for path in _candidate_paths():
            try:
                if os.path.isfile(path):
                    with open(path, 'rb') as handle:
                        raw = handle.read()
                    break
            except Exception:
                continue
    if not raw:
        _status = 'failed: table not found'
        return False
    if raw[:8] != MAGIC:
        _status = 'failed: bad magic {!r}'.format(raw[:8])
        return False
    _data = raw
    _count = _u32(raw, 8)
    _blob_start = _HEADER + _count * _RECORD
    _status = 'loaded {} object names ({:.1f} MB)'.format(_count, len(raw) / 1e6)
    return True


def status():
    _load()
    return _status


def lookup(definition_id):
    """Catalog name for a definition id, or None."""
    if not definition_id or not _load():
        return None
    key = int(definition_id) & 0xFFFFFFFF
    low = 0
    high = _count - 1
    while low <= high:
        mid = (low + high) // 2
        pos = _HEADER + mid * _RECORD
        found = _u32(_data, pos)
        if found == key:
            offset = _blob_start + _u32(_data, pos + 4)
            length = _u32(_data, pos + 8)
            try:
                return _data[offset:offset + length].decode('utf-8')
            except Exception:
                return None
        if found < key:
            low = mid + 1
        else:
            high = mid - 1
    return None
