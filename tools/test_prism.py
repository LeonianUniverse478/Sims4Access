"""Prism reader routing, failures, UTF-8 and braille-only safety."""
import sys
import threading
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
from tyjokr_a11y_prism import _NativeReader as Reader
import tyjokr_a11y_prism as prism


class DLL:
    def __init__(self):
        self.calls = []
        self.result = 0
        self.available = True
    def prism_registry_create(self, ctx, ident): return ident
    def prism_backend_initialize(self, backend): return 0 if self.available else 16
    def prism_backend_free(self, backend): self.calls.append(('free', backend))
    def prism_backend_get_features(self, backend): return 16
    def prism_backend_speak(self, backend, text, interrupt):
        self.calls.append(('speak', text, interrupt)); return self.result
    def prism_backend_braille(self, backend, text):
        self.calls.append(('braille', text)); return self.result
    def prism_backend_stop(self, backend): self.calls.append(('stop',)); return self.result


class Tests(unittest.TestCase):
    def setUp(self):
        self.r = Reader.__new__(Reader)
        self.r.dll = DLL()
        self.r.lock = threading.RLock()
        self.r.log = lambda x: None
        self.r.context = 1
        self.r.backend = None
        self.r.name = None
        self.r.next_probe = 0
        self.r.ids = [(2, 'NVDA'), (3, 'JAWS')]
    def test_utf8_and_interrupt(self):
        self.assertTrue(self.r.output('Élias', 'É', 'off', True))
        self.assertEqual(self.r.dll.calls, [('speak', 'Élias'.encode('utf-8'), True)])
    def test_queue(self):
        self.r.output('description', 'label', 'off', False)
        self.assertEqual(self.r.dll.calls[0], ('speak', b'description', False))
    def test_concise_braille(self):
        self.r.output('label. description', 'label', 'concise', True)
        self.assertEqual(self.r.dll.calls[-1], ('braille', b'label'))
    def test_full_braille(self):
        self.r.output('label. description', 'label', 'full', True)
        self.assertEqual(self.r.dll.calls[-1], ('braille', b'label. description'))
    def test_only_silent_on_failure(self):
        self.r.select(); self.r.dll.result = 6
        self.assertTrue(self.r.output('full', 'short', 'only', True))
        self.assertEqual(self.r.dll.calls, [('braille', b'short')])
    def test_unavailable_falls_back(self):
        self.r.dll.available = False
        self.assertFalse(self.r.output('full', 'short', 'off', True))
    def test_late_reader(self):
        self.r.dll.available = False
        self.assertFalse(self.r.select())
        self.r.dll.available = True
        self.assertTrue(self.r.select(force=True))
        self.assertEqual(self.r.name, 'NVDA')
    def test_failure_releases_reader(self):
        self.r.select(); self.r.dll.result = 6
        self.assertFalse(self.r.output('text', 'text', 'off', True))
        self.assertIsNone(self.r.backend)
        self.assertEqual(self.r.dll.calls[-1], ('free', 2))
    def test_stop(self):
        self.assertFalse(self.r.stop()); self.r.select()
        self.assertTrue(self.r.stop())

    def test_worker_keeps_native_calls_on_owner_thread(self):
        calls = []
        class Native:
            def __init__(self, *args): calls.append(threading.get_ident()); self.name='NVDA'
            def output(self, *args): calls.append(threading.get_ident()); return True
            def stop(self): calls.append(threading.get_ident()); return True
        with patch.object(prism, '_NativeReader', Native):
            worker = prism.Reader('ignored', lambda x: None)
            caller = threading.Thread(target=lambda: worker.output('a','a','off',True))
            caller.start(); caller.join()
            self.assertTrue(worker.stop())
            self.assertEqual(len(set(calls)), 1)
            self.assertNotEqual(calls[0], threading.get_ident())


if __name__ == '__main__': unittest.main()
