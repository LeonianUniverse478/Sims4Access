r"""Re-extract the EA original movies that rebuild_all.ps1 patches.

Run this FIRST after every EA patch: UI.package is replaced wholesale, so a
rebuild against a stale work dir would ship last patch's UI as an override.

    python extract_ea_movies.py <WorkDir>

Writes <WorkDir>\gfx\ea_<Name>.swf for every entry in build_ui_package.py's
MOVIES dict (that dict stays the single source of truth for what ships).
The game's UI.package is found through flash_config (TS4_INSTALL, else the
install folder the EA app records, else the usual install folders).
"""
import ast
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flash_config  # noqa: E402

GFX_TYPE = 0x62ECC59A


def movies():
    """Parse MOVIES out of build_ui_package.py without importing it (that
    module builds a package as a side effect of import)."""
    src = open(os.path.join(HERE, 'build_ui_package.py'), encoding='utf-8').read()
    body = re.sub(r'#.*', '', re.search(r'MOVIES\s*=\s*\{(.*?)\n\}', src, re.S).group(1))
    return ast.literal_eval('{' + body + '}')


def main():
    if len(sys.argv) < 2:
        sys.exit('usage: python extract_ea_movies.py <WorkDir>')
    gfx = os.path.join(sys.argv[1], 'gfx')
    os.makedirs(gfx, exist_ok=True)

    wanted = movies()
    by_instance = {inst: name for name, inst in wanted.items()}
    assert len(by_instance) == len(wanted), 'duplicate instance id in MOVIES'

    dbpf = flash_config.dbpf()
    read_index, read_resource_bytes = dbpf.read_index, dbpf.read_resource_bytes
    ea_ui = flash_config.ui_package()
    print('reading ' + ea_ui)
    found = {}
    with open(ea_ui, 'rb') as f:
        # read_index is lazy and read_resource_bytes seeks, so the index
        # MUST be materialised first or the walk dies after the first hit.
        for entry in list(read_index(f)):
            if entry['type'] != GFX_TYPE or entry['instance'] not in by_instance:
                continue
            name = by_instance[entry['instance']]
            raw = read_resource_bytes(f, entry)
            if raw[:3] != b'GFX':
                sys.exit('%s: not a GFX movie (magic %r)' % (name, raw[:3]))
            out = os.path.join(gfx, 'ea_%s.swf' % name)
            with open(out, 'wb') as g:
                g.write(raw)
            found[name] = len(raw)
            print('  %-28s %10s bytes' % (name, format(len(raw), ',')))

    missing = set(wanted) - set(found)
    if missing:
        sys.exit('MISSING from UI.package: %s' % sorted(missing))
    print('\nextracted %d/%d movies to %s' % (len(found), len(wanted), gfx))


if __name__ == '__main__':
    main()
