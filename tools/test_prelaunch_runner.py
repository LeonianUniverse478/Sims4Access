"""No PowerShell or game actions: test setup-helper launcher outcomes."""
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('helper_runner', str(Path(__file__).with_name('test_prelaunch_helper.py')))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

class LauncherTests(unittest.TestCase):
    def invoke(self, effects):
        with patch.object(runner.shutil, 'which', return_value='powershell'), patch.object(runner.subprocess, 'run', side_effect=effects) as call:
            result = runner.main()
            return result, call

    def test_missing_shell_skips(self):
        with patch.object(runner.shutil, 'which', return_value=None):
            self.assertEqual(runner.main(), 77)

    def test_startup_timeout_skips_without_running_suite(self):
        result, call = self.invoke([subprocess.TimeoutExpired('probe', 5)])
        self.assertEqual(result, 77)
        self.assertEqual(call.call_count, 1)
        self.assertEqual(call.call_args[1]['timeout'], 5)

    def test_bad_probe_skips(self):
        result, call = self.invoke([subprocess.CompletedProcess([], 1, b'bad startup')])
        self.assertEqual(result, 77)
        self.assertEqual(call.call_count, 1)

    def test_native_suite_failure_is_not_skipped(self):
        result, call = self.invoke([subprocess.CompletedProcess([], 0, b'TS4_HELPER_READY'), subprocess.CompletedProcess([], 1, b'FAIL')])
        self.assertEqual(result, 1)
        self.assertEqual(call.call_count, 2)

    def test_native_suite_timeout_is_not_skipped(self):
        result, call = self.invoke([subprocess.CompletedProcess([], 0, b'TS4_HELPER_READY'), subprocess.TimeoutExpired('suite', 90)])
        self.assertEqual(result, 1)

    def test_success(self):
        result, call = self.invoke([subprocess.CompletedProcess([], 0, b'TS4_HELPER_READY'), subprocess.CompletedProcess([], 0, b'ALL 50 CHECKS PASSED')])
        self.assertEqual(result, 0)

if __name__ == '__main__':
    unittest.main()
