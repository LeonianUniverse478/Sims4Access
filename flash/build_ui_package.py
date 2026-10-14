"""Build a multi-resource DBPF v2.1 override package: every movie patched by
rebuild_all.ps1 (25 as of 2026-09-26). Mirrors EA index entry conventions.

Keep MOVIES here in sync with rebuild_all.ps1's $movies: this dict decides
what ships, that one decides what gets patched.

Usage: python build_ui_package.py <WorkDir> [<output.package>]
where <WorkDir> is the same directory passed to rebuild_all.ps1 -WorkDir
(patched_*.swf are read from <WorkDir>\\gfx). Without an output path the
package goes to <project>\\build\\tyjokr_ScreenReader_UI.package. EA's
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
    sys.exit('usage: python build_ui_package.py <WorkDir>  '
             '(the rebuild_all.ps1 -WorkDir; patched_*.swf in <WorkDir>\\gfx)')
GFX_DIR = sys.argv[1]
if os.path.isdir(os.path.join(GFX_DIR, 'gfx')):
    GFX_DIR = os.path.join(GFX_DIR, 'gfx')
# Optional 2nd arg: the output package. The default stays inside this
# project's build folder; flash_config refuses any path inside a Mods folder.
OUT = flash_config.output(sys.argv[2] if len(sys.argv) > 2 else None,
                         'tyjokr_ScreenReader_UI.package')

GFX_TYPE = 0x62ECC59A

# Every movie rebuild_all.ps1 patches; instance = FNV-1 64 of lowercase name.
MOVIES = {
    'TimeControls':              0xC4B030271AE45C30,
    'ClassLibraryScaleform':     0x940FE9A5E7A10370,
    'ClassLibraryOlympus':       0x3FFE72432A703655,
    'ClassLibraryGamedata':      0x12272E1AC0C1F8E2,
    'ClassLibraryWidgetsShared': 0xB8CE021C763422F8,
    'UIContainer':               0x931C3320F314D6B8,
    'BaseLibrary':               0xEE5AC747CDBDA847,
    'ComponentLibrary':          0xA8BC70A1B382004F,
    'GUIComponentLibrary':       0x0CE54D7C2E5B859C,
    'HUDLibrary':                0x96C9A9D28A7456CD,
    'GameEntryLibrary':          0xA6C497E9547E5A92,
    'GameEntryLauncher':         0x6D20AB71641B1539,
    'GameEntryDock':             0x0C27353D9707DDAC,
    'SimInfoTray':               0x5FFB8AE26BC11E96,
    'SimHub':                    0xCC47BCC1ABF46007,
    # NOTE: CASCustomizer (0xDF09D526F4C77B95) is deliberately NOT shipped.
    # Any ffdec-rebuilt copy hard-crashes the client on CAS load; see
    # TODO-NEXT-SESSION.md and the disabled entry in rebuild_all.ps1.
    'SimInfoMotivePanel':        0x093958A845E285BA,
    'InteractionQueue':          0x2D204AB5977F2E80,
    'ObjectBoundElements':       0x499F6A94F677B6C7,
    'Notifications':             0x47928BF88A95BD53,
    'Dialog':                    0x379A262E4BFB7F29,
    'PieMenu':                   0xF335C695884B7E64,
    'Pickers':                   0xF68004C9F7BCB296,
    # Purchase picker cart narration (quantity/totals announcements).
    'PickersPurchase':           0x3EEF420EE17FE553,
    # Dedicated age-up/trait-reassignment hooks only.
    'AgeUpPanel': 0xEB4EA2715398D221,
    # GameTray: ControlPanel M key route to the keyboard travel list (single
    # definition of ControlPanel in UI.package, scanned 2026-09-25).
    'GameTray': 0xBEB822E79797F7EF,
}

# EA conventions per instance (group, comp, committed) + header idx minor
with open(EA_UI, 'rb') as f:
    header = f.read(96)
    idx_minor = struct.unpack_from('<I', header, 60)[0]
    count = struct.unpack_from('<I', header, 36)[0]
    off = struct.unpack_from('<I', header, 64)[0] | (struct.unpack_from('<I', header, 68)[0] << 32)
    f.seek(off)
    flags = struct.unpack('<I', f.read(4))[0]
    assert flags == 0
    ea_conv = {}
    wanted = set(MOVIES.values())
    for _ in range(count):
        t, g, ihi, ilo, _o, fsz, _m, comp, committed = struct.unpack('<IIIIIIIHH', f.read(32))
        inst = (ihi << 32) | ilo
        if t == GFX_TYPE and inst in wanted:
            ea_conv[inst] = (g, fsz & 0x80000000, comp, committed)
    missing = wanted - set(ea_conv)
    assert not missing, f'missing EA entries: {[hex(m) for m in missing]}'

payloads = []   # (instance, group, highbit, comp, committed, compressed, rawlen)
for name, inst in MOVIES.items():
    with open(os.path.join(GFX_DIR, f'patched_{name}.swf'), 'rb') as f:
        raw = f.read()
    assert raw[:3] == b'GFX', name
    g, highbit, comp, committed = ea_conv[inst]
    payloads.append((name, inst, g, highbit, comp, committed, zlib.compress(raw, 9), len(raw)))
    print(f'{name:28s} raw {len(raw):>9,} -> zlib {len(payloads[-1][6]):>9,}')

header = bytearray(96)
header[0:4] = b'DBPF'
struct.pack_into('<I', header, 4, 2)
struct.pack_into('<I', header, 8, 1)
struct.pack_into('<I', header, 36, len(payloads))
index_size = 4 + 32 * len(payloads)
struct.pack_into('<I', header, 44, index_size)
struct.pack_into('<I', header, 60, idx_minor)

data_offset = 96
entries = []
blob = b''
for name, inst, g, highbit, comp, committed, compressed, rawlen in payloads:
    entries.append((inst, g, data_offset + len(blob), len(compressed) | highbit, rawlen, comp, committed))
    blob += compressed

index_offset = data_offset + len(blob)
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
print(f'wrote {OUT} ({96 + len(blob) + len(index):,} bytes, {len(payloads)} resources)')

# verify round-trip
with open(OUT, 'rb') as f:
    got = {e['instance']: read_resource_bytes(f, e) for e in list(read_index(f))}
assert len(got) == len(MOVIES)
for name, inst in MOVIES.items():
    with open(os.path.join(GFX_DIR, f'patched_{name}.swf'), 'rb') as f:
        raw = f.read()
    assert got[inst] == raw, name
print('round-trip verification OK: all resources match, GFX magic intact')
