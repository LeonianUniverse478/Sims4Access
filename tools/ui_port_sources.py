"""Export targeted classes from current movies serially for manual port review.

Diffs are evidence, not automatic approval or feature verification.
"""
import difflib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'flash'))
from gate_pcode import extra_classes, TOOLTIP, CELL, own_only
from flash_config import java, ffdec


def main():
    work = Path(sys.argv[1]).resolve()
    out = ROOT / 'build/ui-port/current-sources'
    out.mkdir(parents=True, exist_ok=True)
    inventory = json.loads((work / 'current-inputs.json').read_text())
    extras, untouched = extra_classes(), own_only()
    # Needs first, then the shared manager used for occult panels and menus.
    priority = ['SimInfoMotivePanel', 'SimInfoTray', 'ClassLibraryGamedata',
                'PickersPurchase', 'Pickers', 'Dialog', 'UIContainer']
    names = priority + sorted(set(r['movie'] for r in inventory['movies']) - set(priority))
    report = []
    for name in names:
        targets = list(extras.get(name, []))
        if name not in untouched:
            for cls in (TOOLTIP, CELL):
                if name in inventory['class_owners'].get(cls, []):
                    targets.append(cls)
        dest = out / name
        dest.mkdir(exist_ok=True)
        command = [java(), '-jar', ffdec(), '-selectclass', ','.join(targets),
                   '-export', 'script', str(dest), str(work / 'gfx' / ('ea_' + name + '.swf'))]
        with (dest / 'export.log').open('w', encoding='utf-8') as log:
            subprocess.run(command, stdout=log, stderr=log, check=True, timeout=180)
        rows = []
        for cls in targets:
            exported = dest / 'scripts' / Path(*cls.split('.')).with_suffix('.as')
            if not exported.is_file():
                raise SystemExit('Missing export: ' + name + ' / ' + cls)
            canonical = ROOT / 'flash' / ('TooltipManager_patched.as' if cls == TOOLTIP
                                          else 'extra-classes/' + cls.split('.')[-1] + '.as')
            old = exported.read_text(encoding='utf-8-sig').splitlines(True)
            new = canonical.read_text(encoding='utf-8-sig').splitlines(True)
            delta = ''.join(difflib.unified_diff(old, new, fromfile='current-EA/' + cls,
                                               tofile='canonical/' + cls))
            (dest / (cls.split('.')[-1] + '.diff')).write_text(delta, encoding='utf-8')
            rows.append({'class': cls, 'diff_lines': len(delta.splitlines()), 'reviewed': False})
        report.append({'movie': name, 'classes': rows})
        (out / 'review-index.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print('EXPORTED %s: %d targeted classes (manual review pending)' % (name, len(targets)), flush=True)


if __name__ == '__main__':
    main()
