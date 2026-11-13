"""Drift check of the EA classes we inject, between two work dirs.

    py -3.7 tools/rebase/ea_drift.py flash/work-OLD flash/work-NEW

Exports the NEW work dir's ea_ movies to pcode (batch exporter) if needed,
then compares every targeted class (TooltipManager, CatalogImageCellView and
rebuild_all.ps1's extra classes) after normalising FFDec's numbering, and
lists every other class that changed too, for the record."""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'flash'))
import gate_pcode as g

NORM = [(re.compile(r'\bofs[0-9a-f]+\b'), 'ofsN'),
        (re.compile(r'PrivateNamespace\(null,"\d+"\)'), 'PrivateNamespace(null,"N")'),
        (re.compile(r'\bnewclass \d+'), 'newclass N'),
        (re.compile(r'\bnewfunction \d+'), 'newfunction N'),
        (re.compile(r'(method|function|class|body|script)\s+(\d+)'), r'\1 N'),
        (re.compile(r'"[^"]*"\s*,\s*"\d+"'), 'NS')]

def norm(path):
    out = []
    for line in open(path, encoding='utf-8', errors='replace'):
        for rx, rep in NORM:
            line = rx.sub(rep, line)
        out.append(line.rstrip())
    return out

def main():
    old, new = sys.argv[1], sys.argv[2]
    names = g.movie_list()
    pairs = [(os.path.join(new, 'gfx', 'ea_%s.swf' % n), os.path.join(new, 'pcode', 'ea_' + n)) for n in names]
    os.makedirs(os.path.join(new, 'pcode'), exist_ok=True)
    g.export_many(pairs, new)
    extras = g.extra_classes()
    own = g.own_only()
    changed_targets, changed_other = [], {}
    for n in names:
        a = g.scripts(os.path.join(old, 'pcode', 'ea_' + n))
        b = g.scripts(os.path.join(new, 'pcode', 'ea_' + n))
        raw = open(os.path.join(new, 'gfx', 'ea_%s.swf' % n), 'rb').read()
        targeted = set(extras.get(n, []))
        if n not in own and b'TooltipManager' in raw: targeted.add(g.TOOLTIP)
        if n not in own and b'CatalogImageCellView' in raw: targeted.add(g.CELL)
        for cls in sorted(targeted):
            if cls not in a or cls not in b:
                changed_targets.append((n, cls, 'MISSING old=%s new=%s' % (cls in a, cls in b)))
            elif norm(a[cls]) != norm(b[cls]):
                changed_targets.append((n, cls, 'CHANGED'))
        others = [c for c in set(a) & set(b) if c not in targeted and norm(a[c]) != norm(b[c])]
        added = sorted(set(b) - set(a)); gone = sorted(set(a) - set(b))
        if others or added or gone:
            changed_other[n] = (sorted(others), added, gone)
        print('%-28s targeted=%d classes old=%d new=%d other-changed=%d added=%d gone=%d'
              % (n, len(targeted), len(a), len(b), len(others), len(added), len(gone)))
    print('\nTARGETED CLASS DRIFT:')
    for t in changed_targets: print('  %s / %s: %s' % t)
    if not changed_targets: print('  none')
    print('\nOTHER CHANGES:')
    for n, (o, ad, go) in sorted(changed_other.items()):
        print('  %s: changed %s added %s gone %s' % (n, o[:12], ad[:12], go[:12]))

main()
