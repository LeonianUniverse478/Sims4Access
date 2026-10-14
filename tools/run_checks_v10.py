"""Run each regression suite in isolation and record its exact source inputs.

The game-module stubs intentionally differ between suites. Separate processes
avoid discovery order accidentally replacing another suite's test environment.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_paths():
    return sorted(list((ROOT / 'tools').glob('test_*.py')) +
                  list((ROOT / 'tools').glob('test_*.js')))


def input_hashes():
    paths = list((ROOT / 'Scripts').rglob('*.py'))
    paths += list((ROOT / 'tools').glob('*.py')) + list((ROOT / 'tools').glob('*.js'))
    paths += list((ROOT / 'tools').glob('*.ps1')) + list((ROOT / 'helper').glob('*'))
    paths += list((ROOT / 'flash/extra-classes').glob('*.as'))
    paths += list((ROOT / 'tools').glob('*v10*.as'))
    paths += [ROOT / 'flash/TooltipManager_patched.as', Path(__file__).resolve()]
    return {path.relative_to(ROOT).as_posix(): sha(path) for path in sorted(set(paths))}


def check_count(output):
    found = (re.search(r'Ran (\d+) tests?', output) or
             re.search(r'ALL (\d+) CHECKS PASSED', output) or
             re.search(r'^(\d+) [^\r\n]*checks passed', output, re.M | re.I))
    return int(found.group(1)) if found else 0


def main():
    assert sys.version_info[:2] == (3, 7), 'run the game regression suites with Python 3.7'
    build = ROOT / 'build'
    build.mkdir(exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    inputs = input_hashes()
    node = shutil.which('node')
    results = []
    for path in test_paths():
        command = [sys.executable, str(path)] if path.suffix == '.py' else [node, str(path)]
        try:
            if command[0] is None:
                raise RuntimeError('Node.js is required for the Flash source fixtures')
            result = subprocess.run(command, cwd=str(ROOT), stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, timeout=120)
            output = result.stdout.decode('utf-8', errors='replace')
            returncode = result.returncode
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
            output, returncode = str(exc) + '\n', -1
        log = build / ('v10-' + path.stem + '.log')
        log.write_text(output, encoding='utf-8')
        count = check_count(output)
        passed = returncode == 0 and count > 0
        results.append({'suite': path.relative_to(ROOT).as_posix(),
                        'kind': 'python' if path.suffix == '.py' else 'as_source_fixture',
                        'returncode': returncode, 'checks': count, 'passed': passed,
                        'log': log.relative_to(ROOT).as_posix(), 'log_sha256': sha(log)})
        print('{}: {} ({} checks)'.format(path.name, 'PASS' if passed else 'FAIL', count), flush=True)
        if not passed:
            print(output[-5000:], flush=True)
    stable = inputs == input_hashes()
    passed = bool(results) and stable and all(item['passed'] for item in results)
    report = {'started_utc': started, 'finished_utc': datetime.now(timezone.utc).isoformat(),
              'passed': passed, 'input_stable': stable, 'inputs': inputs, 'results': results}
    (build / 'v10-checks.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('{} checks across {} isolated suites (includes repeated imported checks).'.format(
        sum(item['checks'] for item in results), len(results)))
    if not stable:
        print('Source changed during the run; repeat after freezing the candidate.')
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
