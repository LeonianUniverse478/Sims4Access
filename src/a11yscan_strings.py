"""Names for content the shipped string table has never heard of.

a11yscan_names.bin is a snapshot taken when the mod was packaged. Install a
content mod afterwards and its objects have real names in the game and no name
here, so they read out as "object" - in build mode, in every shop, and in the
scanner. Rebuilding that table by hand after every new mod is not something
anyone should have to remember to do.

The game already holds every string, mods included. sims4.resources.list hands
over the resource keys and sims4.resources.load hands over the bytes, already
decompressed by the game's own loader - so no zlib, no package parsing, and no
knowledge of where anything is installed.

Reading every English string table costs a few seconds, which is far too long
to spend in one go on the simulation thread. So it is done a few resources at
a time on the pump's slow tick, and the result is written next to the log and
reused until the set of string tables actually changes - which is precisely
when a mod has been added or removed.

Deliberately uses only builtins, the same rule a11yscan_names.py follows: the
game ships C extensions but not the pure-Python stdlib.
"""
import os
import time

import a11yscan_log as logfile
import a11yscan_names as names

# STBL. Not in sims4.resources.Types, so the raw resource type id it is.
TYPE_STBL = 0x220557DA
# The top byte of a string table's instance id is its language; 0 is English.
ENGLISH = 0

CACHE_NAME = 'a11yscan_modstrings.bin'
MAGIC = b'A11YMOD1'

# How long the sweep may spend on one tick. The tick runs four times a second,
# so this is a few per cent of one core - unnoticeable, and it still gets
# through a few hundred resources inside a minute.
BUDGET_SECONDS = 0.03
# Sampling a resource is how we tell "already in the shipped table" from "new".
# Four keys is plenty: the shipped table either has a resource or it does not.
SAMPLE_KEYS = 4
# A safety valve. If the shipped table ever fails to load, every string table
# in the game reads as new and this would swallow a few hundred thousand
# strings into memory. Content mods add hundreds, not tens of thousands.
MAX_EXTRA = 40000

_extra = {}
_pending = None
_ready = False
_started = False
_fingerprint = None
_stats = {'resources': 0, 'new_resources': 0, 'strings': 0, 'seconds': 0.0}
_source = 'not started'


def status():
    if not _started:
        return 'mod strings: not started'
    if not _ready:
        remaining = len(_pending) if _pending else 0
        return 'mod strings: reading, {} tables left'.format(remaining)
    return 'mod strings: {} names from {} of {} tables ({}), {:.1f}s'.format(
        len(_extra), _stats['new_resources'], _stats['resources'],
        _source, _stats['seconds'])


def lookup(key):
    """A name the shipped table does not have, or None."""
    if not _extra:
        return None
    try:
        return _extra.get(int(key) & 0xFFFFFFFF)
    except Exception:
        return None


# ----------------------------------------------------------------- the game

def _english_string_tables():
    """Every English string table the game has loaded, mods included."""
    try:
        import sims4.resources
    except Exception as ex:
        logfile.fail('strings: no resource module ({!r})'.format(ex))
        return None
    keys = None
    for label, call in (
            ('list(type=)',
             lambda: sims4.resources.list(type=TYPE_STBL)),
            ('get_all_resources_of_type',
             lambda: sims4.resources.get_all_resources_of_type(TYPE_STBL))):
        try:
            keys = list(call())
        except Exception as ex:
            logfile.write('strings: {} failed ({!r})'.format(label, ex))
            continue
        if keys:
            logfile.write('strings: {} tables via {}'.format(len(keys), label))
            break
    if not keys:
        return None
    english = []
    for key in keys:
        try:
            if (int(getattr(key, 'instance', 0)) >> 56) == ENGLISH:
                english.append(key)
        except Exception:
            continue
    return english


def _resource_bytes(key):
    """The raw resource, however the loader hands it back."""
    try:
        import sims4.resources
        blob = sims4.resources.load(key)
    except Exception:
        return None
    if blob is None:
        return None
    if isinstance(blob, (bytes, bytearray)):
        return bytes(blob)
    for getter in (lambda: blob.read(), lambda: bytes(blob)):
        try:
            data = getter()
            if data:
                return bytes(data)
        except Exception:
            continue
    return None


def _parse_stbl(data):
    """STBL version 5 to {key: text}. Anything else reads as empty.

    Header is 'STBL', a 16-bit version, a compression byte, then a 64-bit
    entry count; entries start at 21 and run key, flags, length, utf-8 bytes.
    """
    if not data or len(data) < 21 or data[:4] != b'STBL':
        return {}
    if int.from_bytes(data[4:6], 'little') != 5:
        return {}
    count = int.from_bytes(data[7:15], 'little')
    out = {}
    pos = 21
    size = len(data)
    for _ in range(count):
        if pos + 7 > size:
            break
        key = int.from_bytes(data[pos:pos + 4], 'little')
        length = int.from_bytes(data[pos + 5:pos + 7], 'little')
        pos += 7
        raw = data[pos:pos + length]
        pos += length
        if raw:
            try:
                out[key] = raw.decode('utf-8')
            except Exception:
                try:
                    out[key] = raw.decode('utf-8', 'replace')
                except Exception:
                    continue
    return out


def _is_new(table):
    """Does the shipped table already cover this string table?

    Sampling rather than checking every key: a string table was either present
    when the mod was packaged or it was not, and one binary search per string
    over a few hundred thousand of them is the kind of cost that turns a
    background sweep into a stutter.
    """
    checked = 0
    for key in table:
        if names.lookup_shipped(key) is None:
            return True
        checked += 1
        if checked >= SAMPLE_KEYS:
            return False
    return checked == 0


# -------------------------------------------------------------- the cache

def _cache_path():
    for folder in (_log_folder(), _mod_folder()):
        if folder:
            return os.path.join(folder, CACHE_NAME)
    return None


def _log_folder():
    try:
        path = logfile.path()
        return os.path.dirname(path) if path else None
    except Exception:
        return None


def _mod_folder():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except Exception:
        return None


def _read_cache(fingerprint):
    path = _cache_path()
    if not path or not os.path.isfile(path):
        return False
    try:
        with open(path, 'rb') as handle:
            data = handle.read()
    except Exception as ex:
        logfile.write('strings: cache unreadable ({!r})'.format(ex))
        return False
    try:
        if data[:len(MAGIC)] != MAGIC:
            return False
        pos = len(MAGIC)
        mark_len = int.from_bytes(data[pos:pos + 4], 'little')
        pos += 4
        mark = data[pos:pos + mark_len].decode('utf-8')
        pos += mark_len
        if mark != fingerprint:
            logfile.write('strings: cache is for different content, rebuilding')
            return False
        count = int.from_bytes(data[pos:pos + 4], 'little')
        pos += 4
        blob_start = pos + count * 12
        found = {}
        for index in range(count):
            entry = pos + index * 12
            key = int.from_bytes(data[entry:entry + 4], 'little')
            offset = int.from_bytes(data[entry + 4:entry + 8], 'little')
            length = int.from_bytes(data[entry + 8:entry + 12], 'little')
            found[key] = data[blob_start + offset:
                              blob_start + offset + length].decode('utf-8')
    except Exception as ex:
        logfile.write('strings: cache malformed ({!r})'.format(ex))
        return False
    _extra.update(found)
    return True


def _write_cache(fingerprint):
    path = _cache_path()
    if not path:
        return
    try:
        mark = fingerprint.encode('utf-8')
        records = bytearray()
        blob = bytearray()
        for key, text in sorted(_extra.items()):
            encoded = text.encode('utf-8')
            records += (key & 0xFFFFFFFF).to_bytes(4, 'little')
            records += len(blob).to_bytes(4, 'little')
            records += len(encoded).to_bytes(4, 'little')
            blob += encoded
        with open(path, 'wb') as handle:
            handle.write(MAGIC)
            handle.write(len(mark).to_bytes(4, 'little'))
            handle.write(mark)
            handle.write(len(_extra).to_bytes(4, 'little'))
            handle.write(bytes(records))
            handle.write(bytes(blob))
        logfile.ok('strings: cached {} names to {}'.format(
            len(_extra), os.path.basename(path)))
    except Exception as ex:
        logfile.write('strings: could not write the cache ({!r})'.format(ex))


# --------------------------------------------------------------- the sweep

def _fingerprint_of(keys):
    """Changes exactly when the set of string tables does.

    Which is to say: when a content mod is installed or removed. Counting and
    summing is enough - this only has to differ, not be a real digest.
    """
    total = 0
    for key in keys:
        try:
            total = (total + int(getattr(key, 'instance', 0))) & ((1 << 61) - 1)
        except Exception:
            continue
    return '{}:{}'.format(len(keys), total)


def start():
    """Work out whether there is anything to read. Cheap; safe to call twice."""
    global _started, _pending, _ready, _fingerprint, _source
    if _started:
        return
    _started = True
    keys = _english_string_tables()
    if not keys:
        _ready = True
        _source = 'no string tables'
        logfile.write('strings: nothing to read')
        return
    if not names.count():
        _ready = True
        _source = 'shipped table missing'
        logfile.fail('strings: the shipped name table did not load, so every '
                     'string would look new. Not sweeping.')
        return
    _fingerprint = _fingerprint_of(keys)
    _stats['resources'] = len(keys)
    if _read_cache(_fingerprint):
        _ready = True
        _source = 'cache'
        logfile.ok('strings: {} names from the cache, content unchanged'.format(
            len(_extra)))
        return
    _pending = keys
    _source = 'scan'
    logfile.write('strings: reading {} string tables in the background'.format(
        len(keys)))


def tick(budget=BUDGET_SECONDS):
    """Read a few string tables. Called from the pump's slow tick."""
    global _ready, _pending
    if _ready:
        return
    if not _started:
        start()
        return
    if not _pending:
        _finish()
        return
    started = time.monotonic()
    while _pending and (time.monotonic() - started) < budget:
        key = _pending.pop()
        table = _parse_stbl(_resource_bytes(key))
        if not table:
            continue
        if _is_new(table):
            _stats['new_resources'] += 1
            _extra.update(table)
            if len(_extra) > MAX_EXTRA:
                logfile.fail('strings: {} names is far more than a content mod '
                             'adds - the shipped table is probably not loading. '
                             'Stopping.'.format(len(_extra)))
                _pending = []
                break
    _stats['seconds'] += time.monotonic() - started
    if not _pending:
        _finish()


def _finish():
    global _ready
    _ready = True
    _stats['strings'] = len(_extra)
    logfile.ok('strings: {} names from {} new tables of {}, took {:.1f}s'.format(
        len(_extra), _stats['new_resources'], _stats['resources'],
        _stats['seconds']))
    if _fingerprint:
        _write_cache(_fingerprint)


def finish_now(limit_seconds=20.0):
    """Read whatever is left in one go.

    Used when something is about to need every name at once - opening the buy
    catalog - rather than making the first browse of a new mod's furniture read
    out "object" until the trickle catches up.
    """
    if not _started:
        start()
    if _ready:
        return False
    logfile.write('strings: finishing {} tables now'.format(
        len(_pending) if _pending else 0))
    started = time.monotonic()
    while _pending and (time.monotonic() - started) < limit_seconds:
        tick(budget=0.5)
    if _pending:
        logfile.write('strings: still {} tables to go after {:.0f}s'.format(
            len(_pending), limit_seconds))
    return True
