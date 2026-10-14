"""Contributor setup: recreate the pinned inputs the public source leaves out.

The public source does not include EA's own interface movies or UI Cheats
Extension's movies, since neither may be redistributed. Every contributor makes
them from their own installs instead:

    Dev.ps1 setup                                   EA's movies, from TS4_INSTALL
    Dev.ps1 setup --uicheats <UI_Cheats_Extension.package>   and UI Cheats' movies

The results go where the kit expects them (flash/work-1.128.90/gfx and
flash/uicheats-base), and every pinned input in reference/toolchain.json is
then checked by hash, as Dev.ps1 doctor does. Nothing here changes a hash or a
build gate: inputs from another game or UI Cheats version are reported, not
accepted.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'flash/work-1.128.90'
UIC = ROOT / 'flash/uicheats-base'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(lock):
    """Pinned inputs by group: (missing, different)."""
    missing, different = [], []
    for name, expected in sorted(lock['immutable_inputs'].items()):
        p = ROOT / name
        if not p.is_file():
            missing.append(name)
        elif sha(p) != expected:
            different.append(name)
    return missing, different


def setup(env, uicheats=None):
    lock = json.loads((ROOT / 'reference/toolchain.json').read_text(encoding='utf-8'))
    game = Path(env.get('TS4_INSTALL', ''))
    ui = game / 'Data/Client/UI.package'
    if str(game) in ('', '.') or not ui.is_file():
        raise RuntimeError('Set TS4_INSTALL in dev.local.json to your Steam or EA game install folder first.')
    if sha(ui) != lock['game_ui_sha256']:
        raise RuntimeError('Your game is not version ' + lock['game_version'] + ', which this source is built against. '
                           'Its interface movies would differ, so they were not extracted. See docs/development/GFX-SAFETY.md '
                           'on rebasing, or ask in the repository before working against another version.')
    print('Extracting EA interface movies from your game...', flush=True)
    subprocess.run([sys.executable, str(ROOT / 'flash/extract_ea_movies.py'), str(WORK)], env=env, check=True)
    if uicheats:
        package = Path(uicheats)
        if not package.is_file():
            raise RuntimeError('UI Cheats package not found: ' + str(package))
        print('Extracting UI Cheats Extension movies...', flush=True)
        with tempfile.TemporaryDirectory() as out:
            subprocess.run([sys.executable, str(ROOT / 'flash/extract_uicheats_bases.py'),
                            '--package', str(package), '--out', out], env=env, check=True)
            UIC.mkdir(parents=True, exist_ok=True)
            # SOURCE.txt in the kit is pinned; only the movies are copied.
            for movie in Path(out).glob('uic_*.swf'):
                shutil.copyfile(str(movie), str(UIC / movie.name))
    missing, different = check(lock)
    uic_missing = [n for n in missing if n.startswith('flash/uicheats-base/')]
    other = [n for n in missing + different if n not in uic_missing]
    for name in different:
        print('DIFFERENT: ' + name, flush=True)
    for name in missing:
        print('MISSING: ' + name, flush=True)
    if uic_missing and not other:
        print('Almost ready. The UI Cheats Extension bases are missing: run Dev.ps1 setup --uicheats '
              '<path to UI_Cheats_Extension.package>, version 1.59.1.', flush=True)
        return False
    if other:
        if any(n.startswith('flash/uicheats-base/') for n in different):
            print('Your UI Cheats Extension is not version 1.59.1, which this source is built against.', flush=True)
        print('Some pinned inputs are missing or different; see above.', flush=True)
        return False
    print('Setup complete: every pinned input matches. Next: Dev.ps1 doctor --full, then Dev.ps1 build.', flush=True)
    return True
