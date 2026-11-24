"""Extract six current UI Cheats inputs into an isolated development folder."""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/vendor'))
from dbpf_extract import read_index, read_resource_bytes


def main():
    package, output = Path(sys.argv[1]), Path(sys.argv[2])
    text = (ROOT / 'flash/build_compat_package.py').read_text()
    block = re.sub(r'#.*', '', re.search(r'MOVIES\s*=\s*\{(.*?)\n\}', text, re.S).group(1))
    wanted = {instance: name for name, instance in ast.literal_eval('{' + block + '}').items()}
    output.mkdir(parents=True, exist_ok=True)
    records = []
    with package.open('rb') as stream:
        for entry in list(read_index(stream)):
            if entry['type'] != 0x62ECC59A or entry['instance'] not in wanted:
                continue
            raw = read_resource_bytes(stream, entry)
            name = wanted[entry['instance']]
            target = output / ('uic_' + name + '.swf')
            if target.exists() and target.read_bytes() != raw:
                raise SystemExit('Refusing to overwrite different input: ' + str(target))
            target.write_bytes(raw)
            records.append({'movie': name, 'sha256': hashlib.sha256(raw).hexdigest()})
    if len(records) != len(wanted):
        raise SystemExit('Incomplete compatibility extraction')
    (output / 'inputs.json').write_text(json.dumps({'package_sha256': hashlib.sha256(package.read_bytes()).hexdigest(),
                                                  'movies': records}, indent=2) + '\n')
    print('Extracted %d current compatibility inputs.' % len(records))


if __name__ == '__main__':
    main()
