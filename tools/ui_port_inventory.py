"""Record current EA inputs and real owners of patched classes; no deployment."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'flash'))
from extract_ea_movies import movies
from gate_pcode import extra_classes, TOOLTIP, CELL
from audit_ui_classes import definitions, read_index, read_resource_bytes
from flash_config import ui_package


def main():
    work = Path(sys.argv[1]).resolve()
    package = Path(ui_package())
    targets = {TOOLTIP, CELL}
    for classes in extra_classes().values():
        targets.update(classes)
    owners = {name: [] for name in sorted(targets)}
    records = []
    wanted = {instance: name for name, instance in movies().items()}
    names = {}
    for line in (ROOT / 'reference/ui-movie-names.tsv').read_text().splitlines():
        parts = line.split('\t')
        if len(parts) == 2:
            names[int(parts[0], 16)] = parts[1]
    with package.open('rb') as stream:
        for entry in list(read_index(stream)):
            if entry['type'] != 0x62ECC59A:
                continue
            raw = read_resource_bytes(stream, entry)
            classes = definitions(raw)
            name = names.get(entry['instance'], '%016X' % entry['instance'])
            for target in targets.intersection(classes):
                owners[target].append(name)
            if entry['instance'] in wanted:
                name = wanted[entry['instance']]
                extracted = work / 'gfx' / ('ea_' + name + '.swf')
                if not extracted.is_file() or extracted.read_bytes() != raw:
                    raise SystemExit('Current extraction mismatch: ' + name)
                records.append({'movie': name, 'instance': '%016X' % entry['instance'],
                                'sha256': hashlib.sha256(raw).hexdigest(),
                                'class_count': len(classes)})
    if len(records) != len(wanted):
        raise SystemExit('Incomplete movie inventory')
    result = {'package_sha256': hashlib.sha256(package.read_bytes()).hexdigest(),
              'movies': sorted(records, key=lambda row: row['movie']),
              'class_owners': owners}
    output = work / 'current-inputs.json'
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('Verified %d current extracted movies; ownership scanned across the full UI package.' % len(records))
    print(output)


if __name__ == '__main__':
    main()
