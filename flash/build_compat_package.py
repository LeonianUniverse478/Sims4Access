"""Assemble the UI Cheats compatibility package from the compat_*.swf movies
built by build_uicheats_compat.ps1.

Only the 6 movies both mods override (grew from 4 at UIC v1.59.1). The package must load AFTER both the
main mod's package and UI_Cheats_Extension.package to win those movies,
because the last copy of a resource loaded wins.

DEPLOYMENT (changed 2026-08-06 per user): users put this in their own
priority/late-loading folder. Do NOT reintroduce the old
Mods\\tyjokr_ScreenReader\\compat\\ scheme. The package contents do not
depend on where it lands; all that matters is that it loads last.

Usage: python build_compat_package.py <WorkDir> [<output.package>]
Without an output path the package goes to
<project>\\build\\tyjokr_ScreenReader_Compatibility_UICheats.package. EA's
UI.package (index conventions) is found through flash_config (TS4_INSTALL).
"""
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flash_config  # noqa: E402

_dbpf = flash_config.dbpf()
read_index, read_resource_bytes = _dbpf.read_index, _dbpf.read_resource_bytes
EA_UI = flash_config.ui_package()
if len(sys.argv) < 2:
    sys.exit('usage: python build_compat_package.py <WorkDir>')
GFX_DIR = sys.argv[1]
if os.path.isdir(os.path.join(GFX_DIR, 'gfx')):
    GFX_DIR = os.path.join(GFX_DIR, 'gfx')
# Optional 2nd arg: the output package. The default stays inside this
# project's build folder; flash_config refuses any path inside a Mods folder.
OUT = flash_config.output(sys.argv[2] if len(sys.argv) > 2 else None,
                         'tyjokr_ScreenReader_Compatibility_UICheats.package')

GFX_TYPE = 0x62ECC59A
MOVIES = {
    'TimeControls':        0xC4B030271AE45C30,
    'ClassLibraryOlympus': 0x3FFE72432A703655,
    'SimInfoTray':         0x5FFB8AE26BC11E96,
    'SimInfoMotivePanel':  0x093958A845E285BA,
    # New UIC v1.59.1 collisions:
    'SimHub':              0xCC47BCC1ABF46007,
    'PickersPurchase':     0x3EEF420EE17FE553,
}

with open(EA_UI, 'rb') as f:
    header = f.read(96)
    idx_minor = struct.unpack_from('<I', header, 60)[0]
    ea_conv = {}
    wanted = set(MOVIES.values())
    for e in list(read_index(f)):
        if e['type'] == GFX_TYPE and e['instance'] in wanted:
            pass
    # re-read raw index entries for conventions (comp/committed flags)
    count = struct.unpack_from('<I', header, 36)[0]
    off = struct.unpack_from('<I', header, 64)[0] | (struct.unpack_from('<I', header, 68)[0] << 32)
    f.seek(off)
    flags = struct.unpack('<I', f.read(4))[0]
    assert flags == 0
    for _ in range(count):
        t, g, ihi, ilo, _o, fsz, _m, comp, committed = struct.unpack('<IIIIIIIHH', f.read(32))
        inst = (ihi << 32) | ilo
        if t == GFX_TYPE and inst in wanted:
            ea_conv[inst] = (g, fsz & 0x80000000, comp, committed)
    missing = wanted - set(ea_conv)
    assert not missing, 'missing EA entries: {}'.format([hex(m) for m in missing])

payloads = []
for name, inst in MOVIES.items():
    with open(os.path.join(GFX_DIR, 'compat_{}.swf'.format(name)), 'rb') as f:
        raw = f.read()
    assert raw[:3] == b'GFX', name
    g, highbit, comp, committed = ea_conv[inst]
    payloads.append((name, inst, g, highbit, comp, committed, zlib.compress(raw, 9), len(raw)))
    print('{:24s} raw {:>9,} -> zlib {:>9,}'.format(name, len(raw), len(payloads[-1][6])))

header = bytearray(96)
header[0:4] = b'DBPF'
struct.pack_into('<I', header, 4, 2)
struct.pack_into('<I', header, 8, 1)
struct.pack_into('<I', header, 36, len(payloads))
struct.pack_into('<I', header, 44, 4 + 32 * len(payloads))
struct.pack_into('<I', header, 60, idx_minor)

blob = b''
entries = []
for name, inst, g, highbit, comp, committed, compressed, rawlen in payloads:
    entries.append((inst, g, 96 + len(blob), len(compressed) | highbit, rawlen, comp, committed))
    blob += compressed
index_offset = 96 + len(blob)
struct.pack_into('<I', header, 64, index_offset & 0xFFFFFFFF)
struct.pack_into('<I', header, 68, index_offset >> 32)
index = struct.pack('<I', 0)
for inst, g, off, fsz, msz, comp, committed in entries:
    index += struct.pack('<IIIIIIIHH', GFX_TYPE, g, inst >> 32, inst & 0xFFFFFFFF,
                         off, fsz, msz, comp, committed)
with open(OUT, 'wb') as f:
    f.write(header)
    f.write(blob)
    f.write(index)
print('wrote {} ({:,} bytes, {} resources)'.format(
    OUT, 96 + len(blob) + len(index), len(payloads)))

with open(OUT, 'rb') as f:
    got = {e['instance']: read_resource_bytes(f, e) for e in list(read_index(f))}
assert len(got) == len(MOVIES)
for name, inst in MOVIES.items():
    with open(os.path.join(GFX_DIR, 'compat_{}.swf'.format(name)), 'rb') as f:
        assert got[inst] == f.read(), name
print('round-trip verification OK')
