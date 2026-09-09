"""Continuous logging to a file.

The cheat console cannot be copied from, and requiring a command to produce a
report puts the diagnostics behind the very thing that might be broken. So the
mod logs what it does as it happens: every interaction it runs, every dialog
route it tries, and every failure with the game's own reason.

Deliberately self-contained - it resolves its own path rather than importing
the speech module, so nothing here can create an import cycle, and it fails
silent-but-once rather than ever raising into the game.
"""
import os
import time

FILENAME = 'a11yscan_log.txt'
MAX_BYTES = 1500000

# Files that identify the Mods folder while walking up from this module. The
# NVDA client used to be one of them; speech is Prism now and that file is
# gone, so prism.dll takes its place.
_MARKERS = ('a11yscan_names.bin', 'prism.dll', 'Resource.cfg')

_path = None
_resolved = False
_broken = False


def _writable(candidate):
    try:
        with open(candidate, 'a'):
            pass
        return True
    except Exception:
        return False


def _find_path():
    try:
        path = os.path.dirname(__file__)
        for _ in range(6):
            parent = os.path.dirname(path)
            if not parent or parent == path:
                break
            path = parent
            for marker in _MARKERS:
                if os.path.isfile(os.path.join(path, marker)):
                    # `path` is the Mods folder; the Sims 4 folder above it is
                    # the tidier home, but fall back to Mods if need be.
                    for folder in (os.path.dirname(path), path):
                        candidate = os.path.join(folder, FILENAME)
                        if _writable(candidate):
                            return candidate
    except Exception:
        pass
    return None


def path():
    global _path, _resolved
    if not _resolved:
        _resolved = True
        _path = _find_path()
    return _path


def _trim(target):
    try:
        if os.path.getsize(target) <= MAX_BYTES:
            return
        with open(target, 'r', errors='replace') as handle:
            data = handle.read()
        with open(target, 'w') as handle:
            handle.write(data[-(MAX_BYTES // 2):])
    except Exception:
        pass


def write(message, category='info'):
    """Append one line. Never raises; gives up permanently after a failure."""
    global _broken
    if _broken:
        return
    target = path()
    if not target:
        _broken = True
        return
    _trim(target)
    try:
        with open(target, 'a') as handle:
            handle.write('{} [{}] {}\n'.format(
                time.strftime('%H:%M:%S'), category, message))
    except Exception:
        _broken = True


def ok(message):
    write(message, 'OK')


def fail(message):
    write(message, 'FAIL')


def session(message):
    write('', 'info')
    write('=' * 60, 'info')
    write(message, 'SESSION')
