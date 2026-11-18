"""Optional Windows setup-helper checks; exit 77 when PowerShell cannot start.

This helper enables mods before launching the game. It is not mod runtime code.
Only the startup probe may skip; failures after startup remain test failures.
"""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'tools' / 'test_prelaunch_helper.ps1'
SKIP = 77


def main():
    shell = shutil.which('powershell') or shutil.which('pwsh')
    if shell is None:
        print('SKIP: optional setup helper requires PowerShell')
        return SKIP
    flags = [shell, '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass']
    try:
        probe = subprocess.run(flags + ['-Command', '[Console]::WriteLine("TS4_HELPER_READY")'],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=5)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print('SKIP: PowerShell startup unavailable: ' + str(exc))
        return SKIP
    if probe.returncode != 0 or b'TS4_HELPER_READY' not in probe.stdout:
        print('SKIP: PowerShell startup probe failed: ' + probe.stdout.decode('utf-8', 'replace'))
        return SKIP
    try:
        result = subprocess.run(flags + ['-File', str(SCRIPT)], cwd=str(ROOT),
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print('FAIL: setup helper tests failed after PowerShell startup: ' + str(exc))
        return 1
    sys.stdout.write(result.stdout.decode('utf-8', 'replace'))
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
