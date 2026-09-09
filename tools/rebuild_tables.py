"""Rebuild both lookup tables, including everything in the Mods folder.

Two tables ship with the mod:

  a11yscan_names.bin    string-table hash -> English text
  a11yscan_objects.bin  object definition id -> catalog name

Both are built from the game's packages AND the user's Mods folder, because a
mod's objects carry their own OBJD resources and their own STBL strings. Custom
content is invisible to the mod otherwise - a shop selling mod items reads out
prices with no names.

Nothing is filtered by length or content. An earlier version of build_names.py
dropped any string over 80 characters or containing '{' or '<', which throws
away every dialog template - and templates with {0.Money} placeholders are
exactly what the notification code resolves against this table.

Run with ordinary Python 3; only the mod's own code needs the 3.7 interpreter.
"""
import glob
import os
import pickle
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dbpf

NAMES_MAGIC = b'A11YNAM1'
OBJECTS_MAGIC = b'A11YOBJ1'
TYPE_OBJD = 0x319E4F1D
NAME_OFFSETS = (8, 12, 16)

GAME = r'C:\Program Files (x86)\Steam\steamapps\common\The Sims 4'
MODS = os.path.expanduser(
    r'~\OneDrive\Documents\Electronic Arts\The Sims 4\Mods')


def packages(roots):
    found = []
    for root in roots:
        if root and os.path.isdir(root):
            found.extend(glob.glob(os.path.join(root, '**', '*.package'),
                                   recursive=True))
    return sorted(found)


def collect_strings(paths):
    """Every English string in every package, unfiltered."""
    merged = {}
    from_mods = 0
    for path in paths:
        before = len(merged)
        try:
            for entry in dbpf.read_index(path):
                if entry.type == dbpf.TYPE_STBL and entry.locale == 0:
                    merged.update(dbpf.parse_stbl(dbpf.read_resource(path, entry)))
        except Exception:
            continue
        if MODS.lower() in path.lower():
            from_mods += len(merged) - before
    return merged, from_mods


def collect_objects(paths, strings):
    """definition id -> catalog name, read out of OBJD resources."""
    names = {}
    scanned = 0
    from_mods = 0
    for path in paths:
        try:
            entries = [e for e in dbpf.read_index(path) if e.type == TYPE_OBJD]
        except Exception:
            continue
        is_mod = MODS.lower() in path.lower()
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
                # A catalog name is short and has no markup or placeholders;
                # the description sits nearby and would otherwise win.
                if text and 0 < len(text) <= 60 and '{' not in text \
                        and '<' not in text and not (
                            text.endswith('.') and ' ' in text.strip('.')):
                    if definition_id not in names:
                        names[definition_id] = text
                        if is_mod:
                            from_mods += 1
                    break
    return names, scanned, from_mods


def write_table(magic, mapping, out_path):
    items = sorted((key, text) for key, text in mapping.items() if text)
    blob = bytearray()
    records = bytearray()
    for key, text in items:
        encoded = text.encode('utf-8')
        records += struct.pack('<III', key, len(blob), len(encoded))
        blob += encoded
    with open(out_path, 'wb') as handle:
        handle.write(magic)
        handle.write(struct.pack('<I', len(items)))
        handle.write(records)
        handle.write(blob)
    return len(items)


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    paths = packages([GAME, MODS])
    mod_paths = [p for p in paths if MODS.lower() in p.lower()]
    print('%d packages (%d from Mods)' % (len(paths), len(mod_paths)))

    strings, mod_strings = collect_strings(paths)
    print('strings: %d total, ~%d from mods' % (len(strings), mod_strings))
    count = write_table(NAMES_MAGIC, strings,
                        os.path.join(out_dir, 'a11yscan_names.bin'))
    print('  wrote a11yscan_names.bin: %d entries' % count)

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'merged.pkl'), 'wb') as handle:
        pickle.dump(strings, handle)

    names, scanned, mod_named = collect_objects(paths, strings)
    print('objects: %d definitions scanned, %d named (%d from mods)'
          % (scanned, len(names), mod_named))
    count = write_table(OBJECTS_MAGIC, names,
                        os.path.join(out_dir, 'a11yscan_objects.bin'))
    print('  wrote a11yscan_objects.bin: %d entries' % count)


if __name__ == '__main__':
    main()
