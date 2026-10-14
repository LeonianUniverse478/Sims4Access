"""Apply the existing fidelity checks to all six UI Cheats base movies.

Run AFTER the main Flash chain (never alongside another Flash pipeline):
    py -3.7 flash/gate_compat_pcode.py flash/work-compat
Uses separate, fresh pcode exports so a previous build cannot pass the gate.
"""
import os
from pathlib import Path
import re
import sys
import tempfile

import gate_pcode as gate


def main():
    work = Path(sys.argv[1]).resolve()
    base = Path(__file__).resolve().parent / 'uicheats-base'
    source = (base.parent / 'build_uicheats_compat.ps1').read_text(encoding='utf-8')
    block = re.search(r'\$movies\s*=\s*\[ordered\]\s*@\{(.*?)\n\}', source, re.S).group(1)
    targets = {}
    for line in block.splitlines():
        match = re.match(r"\s*'([^']+)'\s*=\s*(.+)$", line)
        if match:
            targets[match[1]] = {cls for cls in re.findall(r'"([\w.]+\.[\w]+)"', match[2])
                                 if not cls.endswith('.as')}
    assert len(targets) == 6, 'expected six compat movies'
    failed = []
    compared = 0
    # FFDec's configuration stays in the same writable folder as chain.ps1.
    os.environ['APPDATA'] = str(base.parent.parent / 'build' / 'ffdec-appdata')
    # Keep exports for review. This unique directory is never reused.
    compare_only = len(sys.argv) > 2
    if compare_only:
        # Rerun comparisons after a checker fix, without stale or partial
        # exports: inputs must predate this run and every export must exist.
        assert sys.argv[2] == '--compare-exports' and len(sys.argv) == 4
        exports = Path(sys.argv[3]).resolve()
        assert exports.parent == work and exports.name.startswith('compat-pcode-')
        for name in targets:
            for prefix in ('base_', 'new_'):
                assert (exports / (prefix + name) / 'scripts').is_dir()
            assert (base / ('uic_' + name + '.swf')).stat().st_mtime <= exports.stat().st_ctime
            assert (work / 'gfx' / ('compat_' + name + '.swf')).stat().st_mtime <= exports.stat().st_ctime
    else:
        exports = Path(tempfile.mkdtemp(prefix='compat-pcode-', dir=str(work)))
    print('Exports: {}'.format(exports), flush=True)
    if not compare_only:
        pairs = []
        for name in sorted(targets):
            pairs.append((str(base / ('uic_' + name + '.swf')), str(exports / ('base_' + name))))
            pairs.append((str(work / 'gfx' / ('compat_' + name + '.swf')), str(exports / ('new_' + name))))
        gate.export_many(pairs, str(exports))
    for name, targeted in sorted(targets.items()):
        old = base / ('uic_' + name + '.swf')
        new = work / 'gfx' / ('compat_' + name + '.swf')
        raw = old.read_bytes()
        if b'TooltipManager' in raw:
            targeted.add(gate.TOOLTIP)
        if b'CatalogImageCellView' in raw:
            targeted.add(gate.CELL)
        before, after = exports / ('base_' + name), exports / ('new_' + name)
        if not compare_only:
            gate.export(str(old), str(before))
            gate.export(str(new), str(after))
        a, b = gate.scripts(str(before)), gate.scripts(str(after))
        if not a or not b or set(a) != set(b):
            failed.append(name + ': missing/changed class set')
        for cls in targeted:
            if cls not in a or cls not in b:
                failed.append(name + ': missing target ' + cls)
                continue
            ops_a, ops_b = gate.opcodes(a[cls]), gate.opcodes(b[cls])
            compared += 1
            for op in gate.INT_OPS:
                if ops_b.get(op, 0) > ops_a.get(op, 0):
                    failed.append('{}: {} gained {}'.format(name, cls, op))
        for cls in sorted(set(a) & set(b) - targeted):
            if gate.opcodes(a[cls]) != gate.opcodes(b[cls]):
                failed.append(name + ': untargeted class changed: ' + cls)
        print('{}: {} classes, {} targets'.format(name, len(a), len(targeted)), flush=True)
    if failed:
        raise SystemExit('\n'.join(failed) + '\ncompat fidelity gate FAILED')
    print('compat fidelity gate PASSED ({} targeted comparisons)'.format(compared))


if __name__ == '__main__':
    main()
