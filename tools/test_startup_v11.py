"""V11 startup transport: outbound-only framing, port signalling, ownership,
real TCP session without a single byte written back, tick routing."""
import importlib.util
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('startup_v11_subject', ROOT / 'Scripts/tyjokr_a11y_startup.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class Settings:
    def __init__(self, **values):
        self.values = values

    def get(self, key, default=None):
        return self.values.get(key, default)


class StartupV11Tests(unittest.TestCase):
    def setUp(self):
        with bridge._lock:
            bridge._incoming.clear()
            bridge._connected = False
            bridge._startup = True
            bridge._generation = 0
            bridge._next_tick = 0.0
            bridge._port = bridge.PORT_KEYBOARD
            bridge._flash_startup = False
        bridge._stop.clear()

    def test_fragmented_unicode_and_combined_frames(self):
        reader = bridge.FrameReader()
        encoded = 'POST|a11y.widget_enc|Żółć\nPOST|a11y.stop|1\n'.encode('utf-8')
        result = []
        for value in encoded:
            result.extend(reader.feed(bytes((value,))))
        self.assertEqual(result, ['POST|a11y.widget_enc|Żółć', 'POST|a11y.stop|1'])

    def test_limits_and_invalid_framing(self):
        for data in (b'x' * (bridge.MAX_FRAME + 1), b'x\x00\n', b'x\r\n', b'\xff\n'):
            with self.assertRaises((ValueError, UnicodeDecodeError)):
                bridge.FrameReader().feed(data)

    def test_hello_and_channels(self):
        self.assertEqual(bridge.parse_hello('HELLO|A11Y_STARTUP_V2|45993'), '45993')
        self.assertEqual(bridge.parse_hello('HELLO|A11Y_STARTUP_V2'), '')
        for line in ('HELLO|A11Y_STARTUP_V1', 'HELLO', 'POST|a11y.mark|x', ''):
            self.assertIsNone(bridge.parse_hello(line))
        self.assertEqual(bridge.parse_post('POST|a11y.focus_enc|A%20B'), ('a11y.focus_enc', 'A%20B'))
        for line in ('POST|sims.modify_funds|1000', 'EXEC|a11y.widget_enc|hello', 'NAV|A11yActivate',
                     'POST|a11y.modalstate|10|extra', 'POST|a11y.inputfence|payload', 'PING'):
            self.assertIsNone(bridge.parse_post(line))

    def test_listen_port_signals_keyboard_mode(self):
        with patch.dict(sys.modules, {'tyjokr_a11y_settings': Settings(keyboard=True)}):
            self.assertEqual(bridge.listen_port(), bridge.PORT_KEYBOARD)
        with patch.dict(sys.modules, {'tyjokr_a11y_settings': Settings(keyboard=False)}):
            self.assertEqual(bridge.listen_port(), bridge.PORT_SPEECH)
        with patch.dict(sys.modules, {'tyjokr_a11y_settings': Settings(startup=False)}):
            self.assertFalse(bridge.enabled())
        with patch.dict(sys.modules, {'tyjokr_a11y_settings': Settings()}):
            self.assertTrue(bridge.enabled())

    def test_poller_messages_are_swallowed_only_while_flash_reports_startup_mode(self):
        self.assertFalse(bridge.send_navigation('A11yTabNext'))
        bridge._connected = True
        self.assertFalse(bridge.send_navigation('A11yTabNext'))
        bridge.note_mark('startup-v11-ClassLibraryGamedata-port45993-active')
        self.assertTrue(bridge.send_navigation('A11yTabNext'))
        self.assertTrue(bridge.send_navigation('A11y|lease'))
        self.assertFalse(bridge.send_navigation('A11yInspect'))
        self.assertFalse(bridge.send_navigation(None))
        bridge.note_mark('keyboard-native-guards-11')
        self.assertTrue(bridge.send_navigation('A11yTabNext'))
        bridge.note_mark('startup-v11-native')
        self.assertFalse(bridge.send_navigation('A11yTabNext'))
        bridge.note_mark('startup-v11-active')
        self.assertTrue(bridge.send_navigation('A11yTabNext'))
        bridge.note_mark('startup-v11-ClassLibraryGamedata-port45994-idle')
        self.assertFalse(bridge.send_navigation('A11yTabNext'))

    def test_same_process_tcp_is_accepted(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            with socket.create_connection(listener.getsockname()) as client:
                conn, address = listener.accept()
                try:
                    self.assertTrue(bridge.same_process_peer(address[1], listener.getsockname()[1]))
                    self.assertFalse(bridge.same_process_peer(address[1], listener.getsockname()[1] + 1))
                finally:
                    conn.close()

    def test_different_process_tcp_is_rejected(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            listener.settimeout(5)
            program = 'import socket,sys; s=socket.create_connection(("127.0.0.1",int(sys.argv[1]))); s.recv(1)'
            child = subprocess.Popen([sys.executable, '-c', program, str(listener.getsockname()[1])],
                                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            try:
                conn, address = listener.accept()
                try:
                    self.assertFalse(bridge.same_process_peer(address[1], listener.getsockname()[1]))
                finally:
                    conn.close()
            finally:
                child.wait(timeout=5)

    def _session(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            client = socket.create_connection(listener.getsockname())
            conn, _ = listener.accept()
        errors = []
        def worker():
            try:
                bridge._connection(conn)
            except Exception as ex:
                errors.append(ex)
            finally:
                conn.close()
        thread = threading.Thread(target=worker)
        thread.start()
        return client, thread, errors

    def test_real_session_never_writes_back_and_queues_posts(self):
        client, thread, errors = self._session()
        try:
            client.sendall(b'HELLO|A11Y_STARTUP_V2|45993\nPOST|a11y.widget_enc|New%20Game\nPOST|a11y.modalstate|10\n')
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and len(bridge._incoming) < 2:
                time.sleep(0.02)
            with bridge._lock:
                queued = [(channel, payload) for _generation, channel, payload in bridge._incoming]
                self.assertTrue(bridge._connected)
            self.assertEqual(queued, [('a11y.widget_enc', 'New%20Game'), ('a11y.modalstate', '10')])
            client.settimeout(0.5)
            with self.assertRaises(socket.timeout):
                client.recv(16)
            client.sendall(b'NAV|A11yActivate\n')
            thread.join(3)
            self.assertFalse(thread.is_alive())
            self.assertFalse(bridge._connected)
            self.assertFalse(bridge._flash_startup)
            self.assertFalse(bridge._incoming)
            self.assertEqual(errors, [])
        finally:
            client.close()
            thread.join(3)

    def test_wrong_greeting_ends_session(self):
        client, thread, errors = self._session()
        try:
            client.sendall(b'HELLO|A11Y_STARTUP_V1\nPOST|a11y.widget_enc|x\n')
            thread.join(3)
            self.assertFalse(thread.is_alive())
            self.assertFalse(bridge._connected)
            self.assertFalse(bridge._incoming)
            self.assertEqual(errors, [])
        finally:
            client.close()

    def test_transition_keeps_mode_marks_but_discards_departing_narration(self):
        for loaded, mark in ((True, 'startup-v11-native'),
                             (False, 'startup-v11-active')):
            with self.subTest(loaded=loaded):
                services = types.SimpleNamespace(
                    current_zone=lambda: object() if loaded else None,
                    client_manager=lambda: types.SimpleNamespace(get_first_client=lambda: object()))
                bridge._startup = loaded  # force the opposite client state
                bridge._flash_startup = loaded
                bridge._connected = True
                bridge._generation = 7
                bridge._next_tick = 0.0
                bridge._incoming.extend([
                    (7, 'a11y.widget_enc', 'departing screen'),
                    (7, 'a11y.mark', mark),
                    (6, 'a11y.mark', 'startup-v11-active' if loaded else 'startup-v11-native'),
                ])
                narrator = types.SimpleNamespace()
                with patch.dict(sys.modules, {'services': services, 'tyjokr_a11y_narrator': narrator}), \
                        patch.object(bridge, 'log'):
                    bridge.tick()
                self.assertEqual(bridge.send_navigation('A11yTabNext'), not loaded)
                self.assertFalse(bridge._incoming)

    def test_full_speech_queue_cannot_drop_transport_mode(self):
        client, thread, errors = self._session()
        try:
            flood = ('HELLO|A11Y_STARTUP_V2|45993\n' +
                     'POST|a11y.widget_enc|hover\n' * bridge.MAX_QUEUE +
                     'POST|a11y.mark|startup-v11-native\n')
            client.sendall(flood.encode('utf-8'))
            deadline = time.monotonic() + 2
            found = False
            while time.monotonic() < deadline:
                with bridge._lock:
                    found = any(payload == 'startup-v11-native'
                                for _, _, payload in bridge._incoming)
                    size = len(bridge._incoming)
                if found:
                    break
                time.sleep(0.01)
            self.assertTrue(found, 'native handoff was dropped behind speech')
            self.assertLessEqual(size, bridge.MAX_QUEUE)
            self.assertEqual(errors, [])
        finally:
            client.close()
            thread.join(3)

    def test_unrelated_startup_diagnostic_does_not_change_key_owner(self):
        bridge._connected = True
        bridge.note_mark('startup-v11-active')
        bridge.note_mark('startup-v11-diagnostic')
        self.assertTrue(bridge.send_navigation('A11yTabNext'))

    def test_tick_dispatches_current_generation_in_every_state(self):
        client = [None]
        services = types.SimpleNamespace(
            current_zone=lambda: object() if client[0] is not None else None,
            client_manager=lambda: types.SimpleNamespace(get_first_client=lambda: client[0]))
        with patch.dict(sys.modules, {'services': services}), \
                patch.object(bridge, '_dispatch', Mock()) as dispatch, patch.object(bridge, 'log', Mock()):
            bridge._generation = 7
            bridge._incoming.extend([(6, 'a11y.widget_enc', 'stale'), (7, 'a11y.widget_enc', 'current')])
            bridge.tick()
            dispatch.assert_called_once_with('a11y.widget_enc', 'current')
            self.assertFalse(bridge._incoming)
            bridge._next_tick = 0.0
            bridge._incoming.append((7, 'a11y.widget_enc', 'old menu'))
            client[0] = object()
            bridge.tick()
            # Narration queued across the state switch is stale and dropped.
            self.assertEqual(dispatch.call_count, 1)
            self.assertFalse(bridge._startup)
            self.assertFalse(bridge._incoming)
            # With a loaded client nothing else is discarded: Flash only posts
            # here when it decided against the native path, so it is real.
            bridge._next_tick = 0.0
            bridge._incoming.append((7, 'a11y.widget_enc', 'in zone'))
            bridge.tick()
            self.assertEqual(dispatch.call_count, 2)
            self.assertFalse(bridge._incoming)
            bridge._next_tick = 0.0
            client[0] = None
            bridge.tick()
            self.assertTrue(bridge._startup)


if __name__ == '__main__':
    unittest.main()
