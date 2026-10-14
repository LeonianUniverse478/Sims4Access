"""Runs tools/test_prelaunch_helper.ps1 so the pre-launch helper's offline
checks are part of run_checks_v10 (which only collects .py and .js suites).
Run with py -3.7 tools/test_prelaunch_helper.py.
"""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'tools' / 'test_prelaunch_helper.ps1'


def main():
    shell = shutil.which('powershell') or shutil.which('pwsh')
    if shell is None:
        print('no PowerShell on this machine')
        return 1
    result = subprocess.run([shell, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                             '-File', str(SCRIPT)], cwd=str(ROOT), stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=110)
    sys.stdout.write(result.stdout.decode('utf-8', 'replace'))
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
