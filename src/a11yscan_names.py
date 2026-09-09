"""Lookup of real catalog names from the shipped string table.

The table is a flat binary blob built offline by tools/build_names.py from the
game's STBL resources. We binary-search it in place rather than building a dict,
so nothing is parsed until a name is actually asked for and memory stays flat.

Deliberately uses only builtins: the game's Python has C extensions but no
pure-Python stdlib, so struct and friends are not safe to import here.
"""
import os

MAGIC = b'A11YNAM1'
FILENAME = 'a11yscan_names.bin'
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
        # Loose copy beside the .ts4script in the Mods folder.
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
    # Inside the .ts4script first, via the zip importer.
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
    _status = 'loaded {} names ({:.1f} MB)'.format(_count, len(raw) / 1e6)
    return True


def status():
    _load()
    return _status


def count():
    _load()
    return _count


def lookup(key):
    """The catalog string for an STBL key hash, or None.

    Falls through to the runtime reader for anything this table predates - a
    content mod installed after the mod was packaged has real names in the
    game and none in here.
    """
    text = lookup_shipped(key)
    if text is not None:
        return text
    try:
        import a11yscan_strings as strings
        return strings.lookup(key)
    except Exception:
        return None


def lookup_shipped(key):
    """Only what shipped in the table. The runtime reader needs this to tell
    a string table it has already covered from one it has never seen."""
    if not key or not _load():
        return None
    key = int(key) & 0xFFFFFFFF
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
