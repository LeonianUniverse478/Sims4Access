"""DBPF resource extractor and search tool.

Reads The Sims 4 .package files (DBPF v2.1) directly, no S4S needed.

Modes:
  find    Search packages for a specific instance hash. Reports all hits.
  list    List resources of a given type with sizes, sorted small to large.
          Useful for picking short voice lines for testing.
  extract Pull one resource by (type, instance) out of a package into a file.

DBPF v2.1 reference: https://simswiki.info/wiki.php?title=DBPF
TS4 SNR resources contain EALayer3-encoded audio with a header that
vgmstream-cli understands.
"""
import argparse
import struct
import sys
import zlib
from pathlib import Path


def read_index(f):
    """Yield (type, group, instance, offset, file_size, compression) per entry."""
    f.seek(0)
    header = f.read(96)
    if header[:4] != b'DBPF':
        raise ValueError('not a DBPF file')

    index_count = struct.unpack_from('<I', header, 36)[0]
    index_offset_low = struct.unpack_from('<I', header, 64)[0]
    index_offset_high = struct.unpack_from('<I', header, 68)[0]
    index_offset = index_offset_low | (index_offset_high << 32)

    f.seek(index_offset)
    flags = struct.unpack('<I', f.read(4))[0]
    const_type_val = struct.unpack('<I', f.read(4))[0] if flags & 1 else None
    const_group_val = struct.unpack('<I', f.read(4))[0] if flags & 2 else None
    const_inst_hi_val = struct.unpack('<I', f.read(4))[0] if flags & 4 else None

    for _ in range(index_count):
        type_id = const_type_val if (flags & 1) else struct.unpack('<I', f.read(4))[0]
        group_id = const_group_val if (flags & 2) else struct.unpack('<I', f.read(4))[0]
        inst_hi = const_inst_hi_val if (flags & 4) else struct.unpack('<I', f.read(4))[0]
        inst_lo = struct.unpack('<I', f.read(4))[0]
        instance = (inst_hi << 32) | inst_lo

        offset = struct.unpack('<I', f.read(4))[0]
        file_size_packed = struct.unpack('<I', f.read(4))[0]
        mem_size = struct.unpack('<I', f.read(4))[0]
        struct.unpack('<I', f.read(4))[0]  # compression(2) + commit(2)

        file_size = file_size_packed & 0x7FFFFFFF

        yield {
            'type': type_id,
            'group': group_id,
            'instance': instance,
            'offset': offset,
            'file_size': file_size,
            'mem_size': mem_size,
        }


def read_resource_bytes(f, entry):
    f.seek(entry['offset'])
    data = f.read(entry['file_size'])

    # Sims 4 sometimes compresses with QFS/Refpack — for SNR audio it's usually uncompressed.
    # If we see a zlib header, try decompress; otherwise return as-is.
    if entry['mem_size'] != entry['file_size']:
        try:
            return zlib.decompress(data)
        except zlib.error:
            pass
    return data


def cmd_find(args):
    target = int(args.instance, 16)
    target_type = int(args.type, 16) if args.type else None
    packages = sorted(Path(args.dir).glob('*.package'))
    found = 0
    for pkg in packages:
        try:
            with open(pkg, 'rb') as f:
                for entry in read_index(f):
                    if entry['instance'] == target and (target_type is None or entry['type'] == target_type):
                        found += 1
                        print(f'{pkg.name}: type 0x{entry["type"]:08X}  group 0x{entry["group"]:08X}  '
                              f'instance 0x{entry["instance"]:016X}  size {entry["file_size"]:,} bytes')
        except Exception as e:
            print(f'{pkg.name}: ERROR {e}', file=sys.stderr)
    if not found:
        print(f'not found: instance 0x{target:016X}', file=sys.stderr)
        return 1
    return 0


def cmd_list(args):
    target_type = int(args.type, 16)
    limit = args.limit
    min_size = args.min_size
    max_size = args.max_size

    candidates = []
    pkg_path = Path(args.package)
    with open(pkg_path, 'rb') as f:
        for entry in read_index(f):
            if entry['type'] != target_type:
                continue
            if min_size is not None and entry['file_size'] < min_size:
                continue
            if max_size is not None and entry['file_size'] > max_size:
                continue
            candidates.append(entry)

    candidates.sort(key=lambda e: e['file_size'])
    print(f'Found {len(candidates):,} resources of type 0x{target_type:08X} in {pkg_path.name}')
    print(f'{"size":>10}  {"type":>10}  {"group":>10}  {"instance":>18}')
    print('-' * 60)
    for entry in candidates[:limit]:
        print(f'{entry["file_size"]:>10,}  0x{entry["type"]:08X}  0x{entry["group"]:08X}  0x{entry["instance"]:016X}')
    return 0


def cmd_extract(args):
    target_type = int(args.type, 16)
    target_instance = int(args.instance, 16)
    pkg_path = Path(args.package)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(pkg_path, 'rb') as f:
        for entry in read_index(f):
            if entry['type'] == target_type and entry['instance'] == target_instance:
                data = read_resource_bytes(f, entry)
                with open(out_path, 'wb') as out:
                    out.write(data)
                print(f'extracted {len(data):,} bytes -> {out_path}')
                print(f'  type 0x{entry["type"]:08X}  group 0x{entry["group"]:08X}  '
                      f'instance 0x{entry["instance"]:016X}')
                return 0
    print(f'not found in {pkg_path.name}: type 0x{target_type:08X} instance 0x{target_instance:016X}',
          file=sys.stderr)
    return 1


def cmd_dump_all(args):
    """Extract every resource of a given type from a package into a folder.
    Filenames follow S4S convention: TYPE!GROUP!INSTANCE.bin
    """
    target_type = int(args.type, 16)
    pkg_path = Path(args.package)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    with open(pkg_path, 'rb') as f:
        entries = [e for e in read_index(f) if e['type'] == target_type]
        for entry in entries:
            data = read_resource_bytes(f, entry)
            fname = f'{entry["type"]:08X}!{entry["group"]:08X}!{entry["instance"]:016X}.bin'
            with open(out_dir / fname, 'wb') as out:
                out.write(data)
            count += 1
            if count % 1000 == 0:
                print(f'  {count}/{len(entries)} extracted...')
    print(f'extracted {count} resources of type 0x{target_type:08X} into {out_dir}')
    return 0


def main():
    p = argparse.ArgumentParser(description='DBPF resource search and extract tool.')
    sub = p.add_subparsers(dest='cmd', required=True)

    pf = sub.add_parser('find', help='Search packages for a specific instance hash.')
    pf.add_argument('dir', help='Directory of .package files to search')
    pf.add_argument('instance', help='Instance hash (hex, 16 chars)')
    pf.add_argument('--type', help='Optional type filter (hex, 8 chars)')
    pf.set_defaults(fn=cmd_find)

    pl = sub.add_parser('list', help='List resources of a given type with sizes.')
    pl.add_argument('package', help='Package file to inspect')
    pl.add_argument('--type', required=True, help='Type ID (hex, e.g. 01A527DB for SNR)')
    pl.add_argument('--limit', type=int, default=50, help='Max rows to print')
    pl.add_argument('--min-size', type=int, default=None)
    pl.add_argument('--max-size', type=int, default=None)
    pl.set_defaults(fn=cmd_list)

    pe = sub.add_parser('extract', help='Extract one resource to a file.')
    pe.add_argument('package', help='Source .package file')
    pe.add_argument('--type', required=True, help='Type ID (hex)')
    pe.add_argument('--instance', required=True, help='Instance ID (hex)')
    pe.add_argument('--out', required=True, help='Output filename')
    pe.set_defaults(fn=cmd_extract)

    pd = sub.add_parser('dump-all', help='Dump every resource of a type into a folder.')
    pd.add_argument('package', help='Source .package file')
    pd.add_argument('--type', required=True, help='Type ID (hex)')
    pd.add_argument('--out-dir', required=True, help='Output folder')
    pd.set_defaults(fn=cmd_dump_all)

    args = p.parse_args()
    sys.exit(args.fn(args))


if __name__ == '__main__':
    main()
