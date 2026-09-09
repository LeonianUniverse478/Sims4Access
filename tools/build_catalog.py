"""Build a definition-id -> catalog name map for the buy catalog.

Object Definitions carry no display name at runtime - their __slots__ hold only
the tuning name, price, tags and geometry. The catalog name lives in the OBJD
resource as a string-table key.

The OBJD layout is not a clean property table, so the name key is read from the
header positions that empirically hold it (offset 8, then 12), validated by
whether the value actually resolves to a string. Anything that does not resolve
is left out and the mod falls back to the tuning name for those.

Layout of the output file:
    magic   8 bytes  b'A11YOBJ1'
    count   u32
    records count * 12 bytes: definition_id u32, offset u32, length u32
    blob    UTF-8 text
"""
import glob
import os
import struct
import sys

import dbpf

MAGIC = b'A11YOBJ1'
TYPE_OBJD = 0x319E4F1D
NAME_OFFSETS = (8, 12, 16)


def load_strings():
    import pickle
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'merged.pkl'), 'rb') as handle:
        return pickle.load(handle)


def plausible(text):
    if not text:
        return False
    if len(text) > 60 or '{' in text or '<' in text:
        return False
    # Descriptions are sentences; catalog names are not.
    if text.endswith('.') and ' ' in text.strip('.'):
        return False
    return True


def collect(roots, strings):
    names = {}
    packages = []
    for root in roots:
        if root and os.path.isdir(root):
            packages.extend(glob.glob(os.path.join(root, '**', '*.package'),
                                      recursive=True))
    scanned = 0
    for path in sorted(packages):
        try:
            entries = [e for e in dbpf.read_index(path) if e.type == TYPE_OBJD]
        except Exception:
            continue
        for entry in entries:
            try:
                data = dbpf.read_resource(path, entry)
            except Exception:
                continue
            scanned += 1
            definition_id = entry.instance & 0xFFFFFFFF
            for offset in NAME_OFFSETS:
                if offset + 4 > len(data):
                    break
                key = struct.unpack_from('<I', data, offset)[0]
                text = strings.get(key)
                if plausible(text):
                    names[definition_id] = text
                    break
    return names, scanned, len(packages)


def write_table(mapping, out_path):
    items = sorted(mapping.items())
    blob = bytearray()
    records = bytearray()
    for definition_id, text in items:
        encoded = text.encode('utf-8')
        records += struct.pack('<III', definition_id, len(blob), len(encoded))
        blob += encoded
    with open(out_path, 'wb') as handle:
        handle.write(MAGIC)
        handle.write(struct.pack('<I', len(items)))
        handle.write(records)
        handle.write(blob)
    return len(items), len(blob)


def main():
    game = r'C:\Program Files (x86)\Steam\steamapps\common\The Sims 4'
    mods = os.path.expanduser(
        r'~\OneDrive\Documents\Electronic Arts\The Sims 4\Mods')
    out = sys.argv[1] if len(sys.argv) > 1 else 'a11yscan_objects.bin'

    strings = load_strings()
    names, scanned, package_count = collect([game, mods], strings)
    print('scanned %d packages, %d object definitions' % (package_count, scanned))
    print('named %d of them (%.0f%%)' % (
        len(names), 100.0 * len(names) / max(scanned, 1)))
    count, blob_size = write_table(names, out)
    print('wrote %s: %d entries, %.1f MB' % (
        out, count, os.path.getsize(out) / 1e6))
    import itertools
    print('samples:')
    for definition_id, text in itertools.islice(sorted(names.items()), 5):
        print('   %d -> %r' % (definition_id, text))


if __name__ == '__main__':
    main()
