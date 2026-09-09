"""Build the shipped name table for the scanner mod.

Scans every .package in the game install and (optionally) the user's Mods
folder, pulls the English STBL resources, and writes a flat binary table the
mod can binary-search at runtime without importing anything.

Layout:
    magic   8 bytes  b'A11YNAM1'
    count   u32
    records count * 12 bytes: hash u32, offset u32, length u32, sorted by hash
    blob    UTF-8 text
"""
import glob
import os
import struct
import sys

import dbpf

MAGIC = b'A11YNAM1'
MAX_LEN = 80


def keep(text):
    """Keep everything non-empty.

    An 80-character cap used to exclude 46,000 strings - including most
    notification bodies, which is exactly the text that needs reading aloud.
    Markup and token placeholders are handled when the string is read.
    """
    return bool(text)


def collect(roots):
    merged = {}
    packages = []
    for root in roots:
        if root and os.path.isdir(root):
            packages.extend(glob.glob(os.path.join(root, '**', '*.package'),
                                      recursive=True))
    for path in sorted(packages):
        try:
            for entry in dbpf.read_index(path):
                if entry.type == dbpf.TYPE_STBL and entry.locale == 0:
                    merged.update(dbpf.parse_stbl(dbpf.read_resource(path, entry)))
        except Exception:
            continue
    return merged, len(packages)


def write_table(mapping, out_path):
    items = sorted((h, t) for h, t in mapping.items() if keep(t))
    blob = bytearray()
    records = bytearray()
    for key, text in items:
        encoded = text.encode('utf-8')
        records += struct.pack('<III', key, len(blob), len(encoded))
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
    out = sys.argv[1] if len(sys.argv) > 1 else 'a11yscan_names.bin'

    merged, package_count = collect([game, mods])
    print('scanned %d packages, %d English strings' % (package_count, len(merged)))
    count, blob_size = write_table(merged, out)
    print('wrote %s: %d entries, %.1f MB text, %.1f MB file'
          % (out, count, blob_size / 1e6, os.path.getsize(out) / 1e6))

    # Spot-check that real catalog names actually survived the filter.
    probes = ('Grill', 'Dolce', 'Chair', 'Fridge', 'Toilet', 'Easel')
    lowered = [t for t in merged.values() if keep(t)]
    for probe in probes:
        matches = [t for t in lowered if probe.lower() in t.lower()][:2]
        print('  %-8s -> %s' % (probe, matches or 'NONE'))


if __name__ == '__main__':
    main()
