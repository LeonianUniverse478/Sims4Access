"""Rewrite an options file in the simplified v14o layout, keeping every
active value. Dry run by default (prints the new file and a diff); --write
applies it, only with the game closed, after a verified backup.

    py -3.7 tools/migrate_cfg_v14o.py [--write] [--cfg PATH] [--backup DIR]

Dropped on purpose: 'scanner swallow' (no longer an option; the protection is
always on) and the legacy '[behavior] auto focus'. Everything else is parsed
with the mod's own settings code and rendered from exactly those values; the
new text is parsed again and must give the same values, or nothing is written.
"""
import argparse
import difflib
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Scripts'))
import tyjokr_a11y_settings as settings   # noqa: E402  (source import never creates a file)

DEFAULT_CFG = (Path(os.path.expanduser('~')) / 'Documents' / 'Electronic Arts' / 'The Sims 4' /
               'Mods' / 'TS4_Access' / 'TS4_Access.cfg')
LEGACY = ('auto_focus', 'captions')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def game_closed():
    result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq TS4_x64.exe'],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    return result.returncode == 0 and 'TS4_x64.exe' not in result.stdout


def parse(path):
    """The mod's own reading of a file: (active values, warnings)."""
    old_path = settings.PATH
    try:
        settings.PATH = str(path)
        settings.reload()
        values = {key: settings.get(key) for key in settings.DEFAULTS if key not in LEGACY}
        return values, list(settings.load_errors)
    finally:
        settings.PATH = old_path
        settings.reload()


def migrate(cfg, write=False, backup=None, closed=game_closed, out=print):
    cfg = Path(cfg)
    if not cfg.is_file():
        out('no options file at {}'.format(cfg))
        return 2
    original = cfg.read_text(encoding='utf-8')
    values, warnings = parse(cfg)
    if warnings:
        out('refused: the current file has warnings; fix them first:')
        for warning in warnings:
            out('  ' + warning)
        return 3
    stored = {key: value for key, value in values.items()}
    new_text = settings._render(stored)
    check = cfg.with_name(cfg.stem + '.migrate-check.cfg')
    try:
        check.write_text(new_text, encoding='utf-8')
        after, after_warnings = parse(check)
    finally:
        if check.exists():
            check.unlink()
    if after_warnings or after != values:
        changed = sorted(key for key in values if values[key] != after.get(key))
        out('refused: the new layout would change {} {}'.format(changed, after_warnings))
        return 4
    diff = list(difflib.unified_diff(original.splitlines(True), new_text.splitlines(True),
                                     str(cfg.name) + ' (current)', str(cfg.name) + ' (simplified)'))
    out(''.join(diff) if diff else 'already in the simplified layout')
    if not write:
        out('dry run: nothing written (add --write with the game closed)')
        return 0
    if not diff:
        return 0
    if not closed():
        out('refused: TS4_x64.exe is running')
        return 5
    backup = Path(backup) if backup else ROOT / 'build' / 'cfg-before-v14o'
    backup.mkdir(parents=True, exist_ok=False)
    saved = backup / cfg.name
    shutil.copy2(str(cfg), str(saved))
    assert sha(saved) == sha(cfg), 'backup mismatch'
    temporary = cfg.with_name(cfg.stem + '.tmp.cfg')
    temporary.write_text(new_text, encoding='utf-8')
    if not closed():
        temporary.unlink()
        out('refused: TS4_x64.exe started; nothing replaced')
        return 5
    os.replace(str(temporary), str(cfg))
    final, final_warnings = parse(cfg)
    if final != values or final_warnings:
        shutil.copy2(str(saved), str(cfg))
        out('restored the backup: the written file did not read back the same')
        return 6
    out('written {} (was {}); backup {}'.format(sha(cfg), sha(saved), saved))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--cfg', default=str(DEFAULT_CFG))
    parser.add_argument('--backup')
    args = parser.parse_args(argv)
    return migrate(args.cfg, write=args.write, backup=args.backup)


if __name__ == '__main__':
    sys.exit(main())
