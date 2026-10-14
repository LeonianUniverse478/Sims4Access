"""Stage a TS4 Access release from REVIEWED artifacts. Never uploads.

    py -3.7 tools/stage_release.py --final build/<final-chain-dir> --frozen build/<final-chain-dir>/script-manifest.json [--readme README.txt]
    py -3.7 tools/stage_release.py --verify-installed dist/<stamp>/TS4_Access_<stamp>.zip

--final    directory holding the reviewed TS4_Access_UI.package and
           TS4_Access_Compatibility_UICheats.package (final chain outputs).
--frozen   script-manifest.json written by tools/build_script_archive.py for the
           reviewed archive: live Scripts/ must still hash to it, or staging aborts.
--readme   the release README to ship (default README.txt). Refused while it still
           carries the pre-startup-support claims, so a stale README cannot ship.
--verify-installed  rule 4 of Utilities/RELEASE-SCRIPT-BUILD.md: the archive in
           Mods/TS4_Access must be byte-identical to the one in the zip.

What ships (2026-09-24 review with Codex):
- main zip: TS4_Access/ {ts4script, UI package, README.txt,
  CONTROLS.txt, CHEATS.txt}. NO cfg
  (the mod regenerates defaults; shipping one would overwrite a player's
  settings on extract-over).
- compat zip, SEPARATE: the UI Cheats compatibility package + its install note,
  so it is never auto-loaded by players who do not run UI Cheats.
Parity: the release archive is compared attribute by attribute (recursively)
against a fresh compile of the frozen sources with the one log transform,
basename co_filename and optimize=2, after strip_pyc_paths ran on it.
Output goes to a fresh dist/<stamp>/ that must not exist yet; nothing is
deleted anywhere.
"""
import argparse, hashlib, importlib.util, json, marshal, os, shutil, sys, time, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UTIL = ROOT / 'tools' / 'vendor' / 'strip_pyc_paths.py'
MODS = Path(os.path.expanduser('~')) / 'Documents' / 'Electronic Arts' / 'The Sims 4' / 'Mods' / 'TS4_Access'
NAME = 'TS4_Access'
DOWNLOAD_NAME = 'TS4_Access'
UI = NAME + '_UI.package'
COMPAT = NAME + '_Compatibility_UICheats.package'
ARCHIVE = NAME + '.ts4script'
REVIEWED_UI = 'tyjokr_ScreenReader_UI.package'
REVIEWED_COMPAT = 'tyjokr_ScreenReader_Compatibility_UICheats.package'
FORBIDDEN = ('C:\\', 'C:/', 'Users\\', 'Users/', 'piecreate', 'Claude', 'Codex', 'TODO', 'FIXME', 'XXX')
STALE_README = ('TEST-V9', 'remains unsupported', 'under investigation', 'does not solve it')
COMPAT_NOTE = """UI Cheats Extension compatibility package for TS4 Access
=============================================================

Only install this if you use UI Cheats Extension. Put
TS4_Access_Compatibility_UICheats.package in a folder that loads
after your other mods, for example Mods\\_priority, so it wins over the
movies UI Cheats replaces. Rebuilt for every TS4 Access release; always
update it together with the main mod. Everyone else: leave it out.
"""


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def forbidden(text):
    return any(f in text for f in FORBIDDEN) or 'tyjok' in text.replace('tyjokr_', '')


def code_identical(a, b):
    """Exact code-object equality, recursive, marshal-independent."""
    if type(a) != type(b):
        return False
    if not hasattr(a, 'co_code'):
        return a == b and type(a) == type(b)
    attrs = ('co_argcount', 'co_kwonlyargcount', 'co_nlocals', 'co_stacksize', 'co_flags', 'co_code',
             'co_names', 'co_varnames', 'co_freevars', 'co_cellvars', 'co_name', 'co_filename',
             'co_firstlineno', 'co_lnotab')
    for attr in attrs:
        if getattr(a, attr) != getattr(b, attr):
            return False
    if len(a.co_consts) != len(b.co_consts):
        return False
    return all(code_identical(x, y) for x, y in zip(a.co_consts, b.co_consts))


def walk(code):
    yield code
    for k in code.co_consts:
        if hasattr(k, 'co_code'):
            for sub in walk(k):
                yield sub


def stage(final, frozen, readme):
    assert sys.version_info[:2] == (3, 7), 'run with py -3.7'
    final = Path(final)
    for n in (REVIEWED_UI, REVIEWED_COMPAT):
        assert (final / n).is_file(), 'missing reviewed package: ' + n
    compiler = load_module('sr_compile', ROOT / 'compile.py')
    strip = load_module('strip_pyc_paths', UTIL)
    # 0) live sources must be the frozen, reviewed ones
    manifest_in = json.loads(Path(frozen).read_text(encoding='utf-8'))
    drift = [k for k, h in manifest_in['sources'].items() if sha(ROOT / 'Scripts' / k) != h]
    assert not drift, 'live Scripts/ differ from the frozen manifest: ' + str(drift)
    # All player guides must exist before creating the output directory.
    readme = Path(readme)
    assert readme.is_file(), 'README missing: ' + str(readme)
    guides = [readme, readme.parent / 'CONTROLS.txt', readme.parent / 'CHEATS.txt']
    for guide in guides:
        assert guide.is_file(), 'player guide missing: ' + str(guide)
    text = readme.read_text(encoding='utf-8', errors='replace')
    stale = [m for m in STALE_README if m in text]
    assert not stale, 'README still carries stale claims ' + str(stale) + '; accept README-proposed.txt or pass --readme'
    # fresh output dir, never overwrite
    stamp = time.strftime('%Y-%m-%d_%H%M%S')
    out = ROOT / 'dist' / stamp
    assert not out.exists(), 'output dir exists: ' + str(out)
    main_dir = out / 'main' / NAME
    compat_dir = out / 'compat'
    main_dir.mkdir(parents=True)
    compat_dir.mkdir(parents=True)
    # 1) release archive: log switch flipped by compile.build, then paths stripped
    archive, count = compiler.build(str(main_dir), release=True)
    strip.strip_archive(archive)
    # 2) parity against a fresh compile of the frozen sources with the same transform
    with zipfile.ZipFile(archive) as zf:
        raw = {n: zf.read(n) for n in zf.namelist()}
    for n, data in raw.items():
        assert data[:4] == importlib.util.MAGIC_NUMBER, 'pyc magic mismatch in ' + n
        assert data[4:16] == bytes(12), 'pyc header not timestamp-less zeros in ' + n
    members = {n: marshal.loads(data[16:]) for n, data in raw.items()}
    expected = {}
    for k in manifest_in['sources']:
        src = (ROOT / 'Scripts' / k).read_text(encoding='utf-8')
        if os.path.basename(k) == compiler.LOG_SWITCH_FILE:
            assert compiler.LOG_ON in src, 'log switch not found in ' + k
            src = src.replace(compiler.LOG_ON, compiler.LOG_OFF)
        expected[k[:-3] + '.pyc'] = compile(src, os.path.basename(k), 'exec', optimize=2)
    assert set(expected) == set(members), 'member sets differ: ' + str(set(expected) ^ set(members))
    bad = [n for n in members if not code_identical(members[n], expected[n])]
    assert not bad, 'release archive code differs from the frozen sources: ' + str(bad)
    for n, code in members.items():
        for c in walk(code):
            assert '/' not in c.co_filename and '\\' not in c.co_filename, 'path left in ' + n
            for k in c.co_consts:
                assert not (isinstance(k, str) and forbidden(k)), 'forbidden string in {}: {!r}'.format(n, k[:100])
    # 3) main zip: archive + UI package + player guides (no cfg)
    shutil.copyfile(str(final / REVIEWED_UI), str(main_dir / UI))
    assert sha(main_dir / UI) == sha(final / REVIEWED_UI)
    for guide, name in zip(guides, ('README.txt', 'CONTROLS.txt', 'CHEATS.txt')):
        shutil.copyfile(str(guide), str(main_dir / name))
        assert sha(main_dir / name) == sha(guide)
    main_zip = out / '{}_{}.zip'.format(DOWNLOAD_NAME, stamp[:10])
    with zipfile.ZipFile(str(main_zip), 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(main_dir.rglob('*')):
            if p.is_file():
                zf.write(str(p), NAME + '/' + p.relative_to(main_dir).as_posix())
    # 4) compat zip, separate
    shutil.copyfile(str(final / REVIEWED_COMPAT), str(compat_dir / COMPAT))
    assert sha(compat_dir / COMPAT) == sha(final / REVIEWED_COMPAT)
    (compat_dir / 'README-UICheats-compat.txt').write_text(COMPAT_NOTE, encoding='utf-8')
    compat_zip = out / '{}_Compatibility_UICheats_{}.zip'.format(DOWNLOAD_NAME, stamp[:10])
    with zipfile.ZipFile(str(compat_zip), 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(compat_dir.iterdir()):
            zf.write(str(p), p.name)
    # 5) manifest
    manifest = {
        'stamp': stamp, 'modules': count,
        'main_zip': {'name': main_zip.name, 'sha256': sha(main_zip)},
        'compat_zip': {'name': compat_zip.name, 'sha256': sha(compat_zip)},
        'files': {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in list(main_dir.iterdir()) + list(compat_dir.iterdir())},
        'frozen_manifest': str(frozen), 'final_dir': str(final), 'readme': str(readme),
    }
    (out / 'RELEASE-MANIFEST.json').write_text(json.dumps(manifest, indent=1), encoding='utf-8')
    print(json.dumps(manifest, indent=1))
    print('STAGED in', out, '(no upload). Main zip has no cfg by design; compat zip is separate.')
    return main_zip


def verify_installed(zip_path):
    with zipfile.ZipFile(str(zip_path)) as zf:
        shipped = zf.read(NAME + '/' + ARCHIVE)
    installed = (MODS / ARCHIVE).read_bytes()
    ok = shipped == installed
    print('installed archive byte-identical to the zipped one:', ok)
    return ok


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--final')
    ap.add_argument('--frozen')
    ap.add_argument('--readme', default=str(ROOT / 'README.txt'))
    ap.add_argument('--verify-installed')
    a = ap.parse_args()
    if a.verify_installed:
        sys.exit(0 if verify_installed(a.verify_installed) else 1)
    assert a.final and a.frozen, 'need --final and --frozen'
    stage(a.final, a.frozen, a.readme)
