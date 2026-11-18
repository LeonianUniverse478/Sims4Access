"""Speech child ownership: isolated mocks plus real Windows crash cleanup.
No PowerShell, speech output, game actions or user configuration writes.
"""
import ctypes
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import threading
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Scripts'))
sys.modules['tyjokr_a11y_settings'] = types.SimpleNamespace(get=lambda key, default=None: default)
import tyjokr_a11y_speech as speech
speech.log_enabled = False


class FakeProcess:
    def __init__(self):
        self.stdin = Mock()
        self.exited = False
        self.kills = self.waits = 0
    def poll(self):
        return 0 if self.exited else None
    def kill(self):
        self.kills += 1
        self.exited = True
    def wait(self, timeout):
        self.waits += 1
        return 0


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        speech._sapi_proc = speech._sapi_job = None
        self.job = Mock()
        self.proc = FakeProcess()
        self.jobs = patch('tyjokr_a11y_speech_process.SpeechJob', return_value=self.job)
        self.jobs.start()
        self.launch = patch.object(speech.subprocess, 'Popen', return_value=self.proc)
        self.popen = self.launch.start()
    def tearDown(self):
        speech.restart_sapi()
        self.launch.stop()
        self.jobs.stop()
    def test_repeated_init_reuses_owned_child(self):
        self.assertTrue(speech._try_init_sapi())
        self.assertTrue(speech._try_init_sapi())
        self.assertEqual(self.popen.call_count, 1)
        self.job.assign.assert_called_once_with(self.proc)
    def test_restart_closes_job_pipe_and_reaps(self):
        speech._try_init_sapi()
        speech.restart_sapi()
        self.job.close.assert_called_once_with()
        self.assertEqual((self.proc.kills, self.proc.waits), (1, 1))
        self.proc.stdin.close.assert_called_once_with()
        self.assertIsNone(speech._sapi_proc)
        self.assertIsNone(speech._sapi_job)
        speech.restart_sapi()
        self.assertEqual(self.proc.waits, 1)
    def test_assignment_refusal_never_leaves_unowned_child(self):
        self.job.assign.side_effect = OSError('job refused')
        self.assertFalse(speech._try_init_sapi())
        self.assertEqual(self.proc.kills, 1)
        self.assertEqual(self.proc.waits, 1)
        self.assertIsNone(speech._sapi_proc)
        self.job.close.assert_called_once_with()
    def test_launch_failure_releases_job(self):
        self.popen.side_effect = OSError('launch refused')
        self.assertFalse(speech._try_init_sapi())
        self.job.close.assert_called_once_with()
    def test_exited_child_reaped_before_replacement(self):
        speech._try_init_sapi()
        self.proc.exited = True
        new = FakeProcess()
        self.popen.return_value = new
        self.assertTrue(speech._try_init_sapi())
        self.assertEqual(self.proc.waits, 1)
        self.assertEqual(self.proc.kills, 0)
        self.assertIs(speech._sapi_proc, new)
    def test_concurrent_init_starts_only_one_child(self):
        threads = [threading.Thread(target=speech._try_init_sapi) for _ in range(12)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(self.popen.call_count, 1)
    def test_blocked_pipe_does_not_block_restart(self):
        speech._try_init_sapi()
        entered, release = threading.Event(), threading.Event()
        def blocked(data):
            entered.set()
            release.wait(3)
        self.proc.stdin.write.side_effect = blocked
        thread = threading.Thread(target=speech._write_sapi, args=(b'I\n', 'test'))
        thread.start()
        try:
            self.assertTrue(entered.wait(1))
            speech.restart_sapi()
            self.assertIsNone(speech._sapi_proc)
            self.assertEqual(self.proc.kills, 1)
        finally:
            release.set()
            thread.join(4)
        self.assertFalse(thread.is_alive())
    def test_child_pipe_not_inherited(self):
        speech._try_init_sapi()
        self.assertTrue(self.popen.call_args[1]['close_fds'])


@unittest.skipUnless(os.name == 'nt', 'Windows kernel ownership test')
class WindowsOwnershipTests(unittest.TestCase):
    def check_parent(self, abrupt):
        # The harmless child only sleeps: this tests the real kernel job, even
        # when PowerShell startup is unavailable. Kill a parent to bypass atexit.
        code = (
            'import subprocess,sys,time;sys.path.insert(0,sys.argv[1]);'
            'from tyjokr_a11y_speech_process import SpeechJob;'
            'job=SpeechJob();'
            'p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"],close_fds=True);'
            'job.assign(p);print(p.pid,flush=True);'
            + ('time.sleep(60)' if abrupt else 'sys.stdin.readline()'))
        parent = subprocess.Popen([sys.executable, '-u', '-c', code, str(ROOT/'Scripts')],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  creationflags=0x08000000)
        handle = None
        pid = None
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        api.OpenProcess.restype = ctypes.c_void_p
        api.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        api.CloseHandle.argtypes = [ctypes.c_void_p]
        try:
            pid = int(parent.stdout.readline())
            handle = api.OpenProcess(0x100000, False, pid)
            self.assertTrue(handle)
            if abrupt: parent.kill()
            else: parent.stdin.write(b'quit\n'); parent.stdin.flush()
            parent.wait(timeout=5)
            self.assertEqual(api.WaitForSingleObject(handle, 5000), 0,
                             'speech-owned child survived its parent')
        finally:
            if parent.poll() is None: parent.kill()
            parent.communicate(timeout=5)
            if handle: api.CloseHandle(handle)
            # Only this test's own dummy process, if native ownership regressed.
            if pid:
                cleanup = api.OpenProcess(1, False, pid)
                if cleanup:
                    api.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
                    api.TerminateProcess(cleanup, 1)
                    api.CloseHandle(cleanup)
    def test_kernel_ends_child_after_parent_crash(self): self.check_parent(True)
    def test_kernel_ends_child_after_normal_parent_exit(self): self.check_parent(False)


if __name__ == '__main__': unittest.main()