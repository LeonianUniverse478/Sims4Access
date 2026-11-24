"""Every class we patch: which game movies define it, and are they all shipped?

    py -3.7 tools/rebase/definer_check.py

TooltipManager is defined almost everywhere; ClassLibraryGamedata's copy wins
(GFX-SAFETY.md), so for it we only report the count. Every other targeted
class must be defined only by movies we ship."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools' / 'vendor'), str(ROOT / 'flash')]
from audit_ui_classes import definitions
from dbpf_extract import read_index, read_resource_bytes
from flash_config import ui_package
import gate_pcode as g

names = {}
for line in (ROOT / 'reference/ui-movie-names.tsv').read_text(encoding='utf-8').splitlines():
    p = line.split('\t')
    if len(p) == 2:
        try: names[int(p[0], 16)] = p[1]
        except ValueError: pass
shipped = set(g.movie_list())
targets = {c for v in g.extra_classes().values() for c in v} | {g.TOOLTIP, g.CELL}
found = {t: [] for t in targets}
with open(ui_package(), 'rb') as f:
    for e in list(read_index(f)):
        if e['type'] != 0x62ECC59A: continue
        cls = definitions(read_resource_bytes(f, e))
        n = names.get(e['instance'], '%016X' % e['instance'])
        for t in targets & cls: found[t].append(n)
bad = 0
for t in sorted(found):
    outside = sorted(set(found[t]) - shipped)
    if t in (g.TOOLTIP, g.CELL):
        print('%s: %d definers (shared library class; every shipped copy is patched)' % (t, len(found[t])))
        continue
    flag = 'OK' if not outside and found[t] else 'CHECK'
    if flag != 'OK': bad += 1
    print('%-5s %s: %s%s' % (flag, t, ', '.join(sorted(found[t])), ('  NOT SHIPPED: ' + ', '.join(outside)) if outside else ''))
print('\n%d class(es) need a look' % bad)
