"""Build for TS4_Access.

Builds ONE ts4script from Scripts/ (features are toggled by the settings
file, not by deleting parts). Compiles to Python 3.7 .pyc, so it must run
under TS4's runtime:

    py -3.7 compile.py             # dev build -> deployed to the Mods subfolder
    py -3.7 compile.py --release   # distribution build -> dist/ zip, Mods untouched

A release build flips the utterance log's build default off (stored settings
still win, and a11y.log re-enables it in the field) and assembles the
complete install layout (ts4script + UI package + speech DLLs and licences)
into dist/, zipped for distribution.

Deploy also removes the retired per-feature ts4scripts (2026-08-01 split,
superseded by the settings file) from the Mods subfolder: stale copies would
shadow the merged modules, since only the first-loaded copy of a module name
runs.
"""
import marshal
import os
import shutil
import struct
import sys
import time
import zipfile
from importlib.util import MAGIC_NUMBER

ROOT = os.path.dirname(os.path.realpath(__file__))
SRC = os.path.join(ROOT, 'Scripts')
FINAL_NAME = 'TS4_Access'
# Retired outputs from the per-feature split; remove wherever they linger.
RETIRED = [FINAL_NAME + suffix + '.ts4script'
           for suffix in ('_SimActions', '_Keyboard', '_ObjectNames')]
# Everything ships inside one subfolder. Script mods load from Mods root or
# ONE level deep, so this is as nested as the ts4script may go.
MODS_FOLDER = os.path.expanduser(
    os.path.join('~', 'Documents', 'Electronic Arts', 'The Sims 4', 'Mods',
                 FINAL_NAME))

# Release transform: the log master switch lives in the speech module.
LOG_SWITCH_FILE = 'tyjokr_a11y_speech.py'
LOG_ON = 'log_enabled = True'
LOG_OFF = 'log_enabled = False'

# Shipped alongside the script in a release zip.
UI_PACKAGE = os.path.join(ROOT, FINAL_NAME + '_UI.package')
SPEECH_DIR = os.path.join(ROOT, 'prism')
SPEECH_FILES = {'prism.dll': 'prism.dll', 'LICENSE': 'LICENSE',
                'NOTICE': 'NOTICE', 'SOURCE.txt': 'SOURCE.txt'}
for _folder, _dirs, _files in os.walk(os.path.join(SPEECH_DIR, 'LICENSES')):
    for _file in _files:
        _rel = os.path.relpath(os.path.join(_folder, _file), SPEECH_DIR)
        SPEECH_FILES[_rel] = _rel.replace(os.sep, '/')


def _code_to_pyc(code):
    blob = bytearray(MAGIC_NUMBER)
    blob += struct.pack('<I', 0)   # PEP 552: timestamp-based
    blob += struct.pack('<I', 0)   # mtime
    blob += struct.pack('<I', 0)   # source size
    blob += marshal.dumps(code)
    return bytes(blob)


def build(out_dir, release=False):
    ts4script = os.path.join(out_dir, FINAL_NAME + '.ts4script')
    count = 0
    with zipfile.ZipFile(ts4script, 'w', zipfile.ZIP_STORED) as zf:
        for folder, _subs, files in os.walk(SRC):
            if '__pycache__' in folder.replace(os.sep, '/').split('/'):
                continue
            for filename in sorted(files):
                if not filename.endswith('.py'):
                    continue
                full = os.path.join(folder, filename)
                rel = os.path.relpath(full, SRC).replace(os.sep, '/')
                with open(full, 'r', encoding='utf-8') as handle:
                    source = handle.read()
                if release and filename == LOG_SWITCH_FILE:
                    if LOG_ON not in source:
                        sys.exit('ERROR: log switch "{}" not found in {}; '
                                 'release transform would be a no-op'.format(
                                     LOG_ON, filename))
                    source = source.replace(LOG_ON, LOG_OFF)
                code = compile(source, rel, 'exec', optimize=2)
                zf.writestr(rel[:-3] + '.pyc', _code_to_pyc(code))
                count += 1
    if count == 0:
        os.remove(ts4script)
        sys.exit('ERROR: no modules found in Scripts/')
    return ts4script, count


def _remove_retired(folder):
    for name in RETIRED:
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            os.remove(path)
            print('Removed retired script: {}'.format(path))


def build_release():
    """Two zips: the mod itself (CurseForge rejects DLL files, so it ships
    with NO speech folder) and a speech pack with the screen reader client
    DLLs + licences, hosted separately (Sim File Share). Both extract into
    Mods the same way and merge into one folder. Without the pack the mod
    still talks through the Windows SAPI voice; a real screen reader and
    braille need the pack."""
    if not os.path.isfile(UI_PACKAGE):
        sys.exit('ERROR: missing {} — build the UI package first'.format(UI_PACKAGE))
    dist = os.path.join(ROOT, 'dist')
    stage = os.path.join(dist, FINAL_NAME)
    if os.path.isdir(stage):
        shutil.rmtree(stage)
    os.makedirs(stage)
    ts4script, count = build(stage, release=True)
    print('Built {:2d} module(s) -> {} (log default off)'.format(
        count, os.path.basename(ts4script)))
    shutil.copyfile(UI_PACKAGE, os.path.join(stage, os.path.basename(UI_PACKAGE)))
    # Ship a pristine default settings file (the mod regenerates it if the
    # user deletes it; extracting an update over the folder resets options).
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'tyjokr_a11y_settings_build', os.path.join(SRC, 'tyjokr_a11y_settings.py'))
    settings_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(settings_mod)
    with open(os.path.join(stage, 'TS4_Access.cfg'), 'w',
              encoding='utf-8') as handle:
        handle.write(settings_mod.render_default())
    print('Wrote default TS4_Access.cfg into the zip')
    readme = os.path.join(ROOT, 'README.txt')
    if os.path.isfile(readme):
        shutil.copyfile(readme, os.path.join(stage, 'README.txt'))
        print('Wrote README.txt into the zip')
    stamp = time.strftime('%Y-%m-%d')
    zip_path = os.path.join(dist, '{}_{}.zip'.format(FINAL_NAME, stamp))
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for folder, _subs, files in os.walk(stage):
            for filename in sorted(files):
                full = os.path.join(folder, filename)
                arc = os.path.relpath(full, dist).replace(os.sep, '/')
                zf.write(full, arc)
    # Guard the whole point of the split: the CurseForge zip must be DLL-free.
    with zipfile.ZipFile(zip_path) as zf:
        dlls = [n for n in zf.namelist() if n.lower().endswith('.dll')]
        if dlls:
            sys.exit('ERROR: DLLs leaked into the main zip: {}'.format(dlls))
    print('Release zip (no DLLs, for CurseForge): {} ({:,} bytes)'.format(
        zip_path, os.path.getsize(zip_path)))
    # Speech pack: same folder layout so it extracts into Mods identically.
    pack_readme = os.path.join(ROOT, 'README-SpeechPack.txt')
    if not os.path.isfile(pack_readme):
        sys.exit('ERROR: missing README-SpeechPack.txt')
    pack_path = os.path.join(dist, '{}_SpeechPack_{}.zip'.format(FINAL_NAME, stamp))
    with zipfile.ZipFile(pack_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # The pack README lives INSIDE the pack folder so the whole pack is
        # one self-contained, relocatable folder. It ships as plain
        # README.txt (user's naming); the SOURCE file keeps the distinct
        # name README-SpeechPack.txt because the main README.txt sits in
        # the same source directory.
        zf.write(pack_readme,
                 '{0}/{0}_SpeechPack/README.txt'.format(FINAL_NAME))
        for src_name, ship_name in sorted(SPEECH_FILES.items()):
            src_path = os.path.join(SPEECH_DIR, src_name)
            if not os.path.isfile(src_path):
                sys.exit('ERROR: missing speech file {}'.format(src_path))
            # Folder is self-identifying so a loose extract at the Mods root
            # stays recognizable; the mod finds the DLLs anywhere under Mods.
            zf.write(src_path, '{0}/{0}_SpeechPack/{1}'.format(FINAL_NAME, ship_name))
    print('Speech pack zip (for Sim File Share):  {} ({:,} bytes)'.format(
        pack_path, os.path.getsize(pack_path)))
    print('Local Mods install NOT touched (still the dev build).')


if __name__ == '__main__':
    if os.path.isfile(os.path.join(ROOT, '.handoff', 'baseline.json')):
        sys.exit('Source kit: use Dev.ps1 build or Dev.ps1 build --scripts-only. '
                 'The legacy direct compiler deploys files or creates an obsolete release layout.')
    if sys.version_info[:2] != (3, 7):
        sys.exit('ERROR: build must run under Python 3.7 (TS4 runtime). '
                 'Use `py -3.7 compile.py`. Detected {}.'.format(
                     '.'.join(map(str, sys.version_info[:3]))))
    if '--release' in sys.argv[1:]:
        build_release()
        sys.exit(0)
    os.makedirs(MODS_FOLDER, exist_ok=True)
    ts4script, count = build(ROOT)
    dest = os.path.join(MODS_FOLDER, os.path.basename(ts4script))
    shutil.copyfile(ts4script, dest)
    _remove_retired(MODS_FOLDER)
    _remove_retired(ROOT)
    print('Built {:2d} module(s) -> {}'.format(count, os.path.basename(ts4script)))
    print('Deployed: {}'.format(dest))
