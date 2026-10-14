r"""Extract UI Cheats Extension's movies that the compatibility build uses as bases.

Needed only when UI Cheats Extension updates: its package overrides some of
the same UI movies as ours, and the compatibility package is our classes
compiled on top of UI Cheats' copies (build_uicheats_compat.ps1).

    python extract_uicheats_bases.py --package <UI_Cheats_Extension.package> --out <folder>

Writes <folder>\uic_<Name>.swf for every movie in build_compat_package.py's
MOVIES dict, plus SOURCE.txt recording the package it came from, and reports
how each movie compares with the current baseline in flash\uicheats-base.
The baseline itself is only replaced with --replace-baseline and --out
pointing at flash\uicheats-base; review the comparison first. After replacing
it, rebuild the compat movies and run gate_compat_pcode.py.
"""
import argparse
import ast
import datetime
import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flash_config  # noqa: E402

GFX_TYPE = 0x62ECC59A
BASELINE = os.path.join(HERE, 'uicheats-base')


def compat_movies():
    """MOVIES from build_compat_package.py, parsed without importing it (that
    module builds a package as a side effect of import)."""
    src = open(os.path.join(HERE, 'build_compat_package.py'), encoding='utf-8').read()
    body = re.sub(r'#.*', '', re.search(r'MOVIES\s*=\s*\{(.*?)\n\}', src, re.S).group(1))
    return ast.literal_eval('{' + body + '}')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description='Extract UI Cheats Extension base movies.')
    parser.add_argument('--package', required=True, help='UI_Cheats_Extension.package to read')
    parser.add_argument('--out', required=True, help='folder for uic_<Name>.swf and SOURCE.txt')
    parser.add_argument('--replace-baseline', action='store_true',
                        help='allow --out to be flash\\uicheats-base (replaces the kit baseline)')
    args = parser.parse_args()

    package = os.path.abspath(args.package)
    out = os.path.abspath(args.out)
    if not os.path.isfile(package):
        sys.exit('no such package: ' + package)
    if os.path.normcase(out) == os.path.normcase(os.path.abspath(BASELINE)) and not args.replace_baseline:
        sys.exit('--out is the kit baseline folder; add --replace-baseline to overwrite it.')
    if os.path.normcase(out) == os.path.normcase(os.path.dirname(package)):
        sys.exit('--out must not be the folder holding the package.')

    dbpf = flash_config.dbpf()
    wanted = compat_movies()
    by_instance = {inst: name for name, inst in wanted.items()}
    found = {}
    with open(package, 'rb') as f:
        # The index must be materialised before seeking to resources.
        for entry in list(dbpf.read_index(f)):
            if entry['type'] != GFX_TYPE or entry['instance'] not in by_instance:
                continue
            name = by_instance[entry['instance']]
            raw = dbpf.read_resource_bytes(f, entry)
            if raw[:3] != b'GFX':
                sys.exit('{}: not a GFX movie (magic {!r})'.format(name, raw[:3]))
            if name in found:
                sys.exit('{}: the package holds this movie twice'.format(name))
            found[name] = raw

    missing = sorted(set(wanted) - set(found))
    if missing:
        sys.exit('UI Cheats no longer overrides: {}. The compat build and its movie list '
                 'must change before rebasing; nothing was written.'.format(', '.join(missing)))

    os.makedirs(out, exist_ok=True)
    lines = []
    for name in sorted(found):
        raw = found[name]
        target = os.path.join(out, 'uic_{}.swf'.format(name))
        with open(target, 'wb') as g:
            g.write(raw)
        current = os.path.join(BASELINE, 'uic_{}.swf'.format(name))
        if not os.path.isfile(current):
            state = 'new (no baseline copy)'
        elif open(current, 'rb').read() == raw:
            state = 'same as baseline'
        else:
            state = 'differs from baseline'
        print('  {:24s} {:>10,} bytes  {}'.format(name, len(raw), state))
        lines.append('uic_{}.swf {} {}'.format(name, len(raw), sha(raw)))

    package_bytes = open(package, 'rb').read()
    source = [
        'Bases extracted from {} ({:,} bytes, sha256 {})'.format(
            os.path.basename(package), len(package_bytes), sha(package_bytes)),
        'on {} by extract_uicheats_bases.py. Record the UI Cheats Extension version here:'.format(
            datetime.date.today().isoformat()),
        'version: ',
        '',
    ] + lines
    with open(os.path.join(out, 'SOURCE.txt'), 'w', encoding='utf-8', newline='\r\n') as g:
        g.write('\n'.join(source) + '\n')
    print('\nwrote {} movies and SOURCE.txt to {}'.format(len(found), out))


if __name__ == '__main__':
    main()
