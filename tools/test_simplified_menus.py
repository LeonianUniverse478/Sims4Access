"""Simplified menus switch, Python side: one option, on by default.

The options file, the settings menu row and the readout carry it; the client
hears A11y|simplifiedmenus|on/off at zone load, mark and reload, on a
settings change, when the pump starts and with every keyboard lease. Before a
save loads the listening port says it: 45993 keyboard with simplified menus,
45995 keyboard without them, 45994 speech only. The port follows a settings
change while no UI is connected, so the main menu reached from a loaded game
reads the current choice; a UI copy still connected from before the game
loaded is closed so it reconnects to the new port. Run with
py -3.7 tools/test_simplified_menus.py.
"""
import importlib.util
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import patch

import test_scanner_v5 as env
import tyjokr_a11y_narrator as narrator

settings = env.settings
keys = env.keys
menu = env.menu
lang = env.lang

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('startup_simplified_subject',
                                              ROOT / 'Scripts/tyjokr_a11y_startup.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class Base(unittest.TestCase):
    def setUp(self):
        self.saved = dict(settings._stored)
        self.addCleanup(self.restore)
        env.queue.clear()
        env.messages.clear()

    def restore(self):
        settings._stored.clear()
        settings._stored.update(self.saved)


class SettingTests(Base):
    def test_default_is_on_and_the_file_says_so(self):
        settings._stored.pop('simplified_menus', None)
        self.assertIs(settings.DEFAULTS['simplified_menus'], True)
        self.assertTrue(settings.get('simplified_menus'))
        text = settings.render_default()
        features = text.split('[features]')[1].split('[speech]')[0]
        self.assertIn('simplified menus = on', features)
        self.assertNotIn(chr(0x2014), text)
        self.assertNotIn(chr(0x2013), text)

    def test_hand_edit_reload_and_old_files(self):
        old_path = settings.PATH
        with tempfile.TemporaryDirectory() as folder:
            settings.PATH = os.path.join(folder, 'test.cfg')
            try:
                with open(settings.PATH, 'w', encoding='utf-8') as handle:
                    handle.write('[features]\nkeyboard = on\n')        # written before the option existed
                settings.reload()
                self.assertEqual(settings.load_errors, [])
                self.assertTrue(settings.get('simplified_menus'))
                settings.set('simplified_menus', False)
                with open(settings.PATH, encoding='utf-8') as handle:
                    self.assertIn('simplified menus = off', handle.read())
                settings.reload()
                self.assertIs(settings.get('simplified_menus'), False)  # explicit off survives
                with open(settings.PATH, 'w', encoding='utf-8') as handle:
                    handle.write('[features]\nsimplified menus = sometimes\n')
                settings.reload()
                self.assertTrue(settings.get('simplified_menus'))      # default kept
                self.assertTrue(any('simplified_menus' in err for err in settings.load_errors))
            finally:
                settings.PATH = old_path
                del settings.load_errors[:]

    def test_menu_row_follows_keyboard_and_tells_the_client(self):
        keys_index = [row.key for row in menu.ROWS].index('keyboard')
        row = menu.ROWS[keys_index + 1]
        self.assertEqual((row.key, row.kind), ('simplified_menus', 'bool'))
        self.assertIn(row, menu._SETTING_ROWS)
        self.assertEqual(lang.t(row.term), 'Simplified menus')
        with patch.object(lang, '_locale_lang', 'pl'):
            self.assertEqual(lang.t(row.term), 'Uproszczone menu')
        with patch.object(settings, '_save', return_value=True):
            menu._apply(row, False)
            self.assertIs(settings.get('simplified_menus'), False)
            self.assertEqual(menu._value_text(row), lang.t('off'))
            menu._apply(row, True)
            self.assertIs(settings.get('simplified_menus'), True)
        self.assertEqual(env.messages, ['A11y|simplifiedmenus|off', 'A11y|simplifiedmenus|on'])

    def test_readout_lists_the_switch(self):
        for value, word in ((True, 'on'), (False, 'off')):
            settings._stored['simplified_menus'] = value
            lines = []
            with patch.object(env.commands, 'CheatOutput', lambda connection: lines.append):
                narrator.a11y_settings()
            self.assertTrue(any(line.endswith(': simplified menus ' + word) for line in lines), lines)


class NoticeTests(Base):
    def test_zone_load_mark_and_reload_push_it_with_the_keyboard_switch(self):
        settings._stored['keyboard'] = True
        settings._stored['simplified_menus'] = False
        narrator._push_autofocus()
        self.assertEqual(env.messages, ['A11yKeyboardOn', 'A11y|simplifiedmenus|off'])

    def test_keyboard_heartbeat_carries_it(self):
        settings._stored['simplified_menus'] = True
        keys._announce_ui_settings()
        self.assertIn('A11y|simplifiedmenus|on', env.messages)
        env.messages.clear()
        settings._stored['simplified_menus'] = False
        keys._announce_ui_settings()
        self.assertIn('A11y|simplifiedmenus|off', env.messages)

    def test_pump_start_sends_it(self):
        source = (ROOT / 'Scripts/tyjokr_a11y_pump.py').read_text(encoding='utf-8')
        start = source[source.index("speech.log_line('pump: started')"):]
        start = start[:start.index('return True')]
        self.assertIn('narrator.push_simplified_menus()', start)

    def test_a_failed_notice_is_logged_not_raised(self):
        broken = types.SimpleNamespace(Distributor=types.SimpleNamespace(
            instance=lambda: (_ for _ in ()).throw(RuntimeError('no distributor'))))
        with patch.dict(sys.modules, {'distributor.system': broken}), \
                patch.object(env.distributor, 'system', broken), \
                patch.object(env.speech, 'log_line') as logged:
            self.assertFalse(narrator.push_simplified_menus())
        self.assertIn('simplified menus notice failed', logged.call_args[0][0])


class ScannerHoldTests(Base):
    """Live 2026-09-26: between two of our own windows (world then place,
    phone then category) the scanner announced itself. A short hold keeps it
    quiet; with no next window it still announces once the hold ends."""

    def setUp(self):
        super().setUp()
        import tyjokr_a11y_scanner as scanner
        self.clock = [100.0]
        self.patches = [patch.object(keys.time, 'monotonic', lambda: self.clock[0]),
                        patch.object(keys, '_scanner_effective', return_value=True),
                        patch.object(keys, 'fence_opening_input'),
                        patch.object(scanner, 'resume_mode')]
        for item in self.patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in reversed(self.patches)])
        self.resumed = scanner.resume_mode
        self.state = (keys._scanner_owner, keys._scanner_suspended, keys._scanner_pending_announce,
                      keys._modal_active, keys._editing_active, keys._scanner_hold_until)
        self.addCleanup(self.restore_keys)
        keys._scanner_owner, keys._scanner_suspended, keys._scanner_pending_announce = False, True, False
        keys._modal_active = keys._editing_active = False
        keys._scanner_hold_until = 0.0

    def restore_keys(self):
        (keys._scanner_owner, keys._scanner_suspended, keys._scanner_pending_announce,
         keys._modal_active, keys._editing_active, keys._scanner_hold_until) = self.state

    def test_without_a_hold_the_scanner_resumes_at_once(self):
        keys.a11y_scannerowner('1')
        self.resumed.assert_called_once_with()

    def test_a_hold_waits_then_announces_if_no_window_follows(self):
        keys.hold_scanner_resume()
        keys.a11y_scannerowner('1')
        self.resumed.assert_not_called()
        env.drain()
        self.resumed.assert_not_called()                  # still inside the hold
        self.clock[0] += 1.5
        env.drain()
        self.resumed.assert_called_once_with()

    def test_the_next_window_retires_the_delayed_announcement(self):
        keys.hold_scanner_resume()
        keys.a11y_scannerowner('1')
        keys.a11y_scannerowner('0')                       # our next window took the keys
        self.clock[0] += 1.5
        env.drain()
        self.resumed.assert_not_called()


class HelpTests(Base):
    def test_spoken_help_explains_simplified_menus_and_first_person(self):
        import tyjokr_a11y_shortcuts as shortcuts
        settings._stored['simplified_menus'] = True
        text = shortcuts.readout()
        self.assertIn(lang.t('shortcut simplified'), text)
        self.assertIn('first-person', lang.t('shortcut shift tab'))
        self.assertIn(lang.t('shortcut shift tab'), text)
        settings._stored['simplified_menus'] = False
        self.assertNotIn(lang.t('shortcut simplified'), shortcuts.readout())
        for term in ('shortcut simplified', 'shortcut shift tab'):
            for language in ('en', 'pl'):
                self.assertNotIn(chr(0x2014), lang._TRANSLATIONS[term][language])
                self.assertNotIn(chr(0x2013), lang._TRANSLATIONS[term][language])


class OwnPhraseTests(Base):
    """Flash composes two English lines itself: the option position and the
    first-person camera state. The player's language wins."""

    def test_position_and_first_person_follow_the_language(self):
        sep = narrator.FIELD_SEP
        line = '10|5|Load Game' + sep + '999999|999999|3 of 10'
        self.assertEqual(narrator._process(line), 'Load Game. 3 of 10')
        self.assertEqual(narrator._process('0|0|First-person camera on.'), 'First-person camera on.')
        with patch.object(lang, '_locale_lang', 'pl'):
            self.assertEqual(narrator._process(line), 'Load Game. 3 z 10')
            self.assertEqual(narrator._process('0|0|First-person camera off.'),
                             'Kamera z perspektywy pierwszej osoby wyłączona.')
            self.assertEqual(narrator._process('0|0|3 of 10 goals'), '3 of 10 goals')  # game text untouched
            self.assertEqual(narrator._process('0|0|Sims' + sep + '999999|999999|2 selected'), 'Sims. Wybrano: 2')
        self.assertEqual(narrator._process('0|0|Sims' + sep + '999999|999999|2 selected'), 'Sims. 2 selected')


class Settings:
    def __init__(self, **values):
        self.values = values

    def get(self, key, default=None):
        return self.values.get(key, default)


class FakeListener:
    def __init__(self, port):
        self.port = port
        self.closed = False

    def close(self):
        self.closed = True


class PortTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings()
        self.modules = patch.dict(sys.modules, {'tyjokr_a11y_settings': self.settings})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.bound = []
        self.refuse = set()
        self.binder = patch.object(bridge, '_bind', side_effect=self.bind)
        self.binder.start()
        self.addCleanup(self.binder.stop)
        saved = (bridge._port, bridge._wanted, bridge._seen)
        self.addCleanup(self.restore, saved)

    def restore(self, saved):
        bridge._port, bridge._wanted, bridge._seen = saved

    def bind(self, port):
        if port in self.refuse:
            raise OSError('port {} in use'.format(port))
        self.bound.append(port)
        return FakeListener(port)

    def prefer(self, **values):
        self.settings.values = values

    def serving(self, port):
        bridge._port = bridge._wanted = bridge._seen = port
        return FakeListener(port)

    def idle(self, listener, times=1):
        """What _serve does on each accept timeout."""
        for _ in range(times):
            if bridge._preference_moved():
                listener = bridge._move_listener(listener)
        return listener

    def test_port_says_keyboard_and_simplified_menus(self):
        cases = [({}, bridge.PORT_KEYBOARD),
                 ({'keyboard': True, 'simplified_menus': True}, 45993),
                 ({'keyboard': True, 'simplified_menus': False}, 45995),
                 ({'keyboard': False, 'simplified_menus': True}, 45994),
                 ({'keyboard': False, 'simplified_menus': False}, 45994)]
        for values, port in cases:
            self.prefer(**values)
            self.assertEqual(bridge.listen_port(), port, values)
        self.assertEqual(bridge.PORT_KEYBOARD_FULL_MENUS, 45995)
        self.assertEqual(len({bridge.PORT_KEYBOARD, bridge.PORT_SPEECH,
                              bridge.PORT_KEYBOARD_FULL_MENUS}), 3)

    def test_a_change_moves_the_port_after_two_matching_readings(self):
        old = listener = self.serving(45993)
        self.prefer(simplified_menus=False)
        listener = self.idle(listener)
        self.assertEqual((listener.port, bridge._wanted, self.bound), (45993, 45993, []))
        listener = self.idle(listener)
        self.assertEqual((listener.port, bridge._wanted, bridge._port), (45995, 45995, 45995))
        self.assertTrue(old.closed)
        listener = self.idle(listener, 3)
        self.assertEqual(self.bound, [45995])                 # settled: no further binds

    def test_a_single_odd_reading_never_moves_it(self):
        listener = self.serving(45995)
        self.prefer(simplified_menus=True)                    # a11y.reload's empty store reads defaults
        listener = self.idle(listener)
        self.prefer(simplified_menus=False)
        listener = self.idle(listener, 3)
        self.assertEqual((listener.port, bridge._port, self.bound), (45995, 45995, []))

    def test_not_serving_never_moves(self):
        bridge._wanted = bridge._seen = None
        self.prefer(simplified_menus=False)
        for _ in range(3):
            self.assertFalse(bridge._preference_moved())

    def test_a_failed_move_keeps_the_listener_and_waits_for_the_next_change(self):
        listener = self.serving(45993)
        self.refuse.add(45994)
        self.prefer(keyboard=False)
        with patch.object(bridge, 'log') as logged:
            listener = self.idle(listener, 5)
        self.assertEqual((listener.port, listener.closed, bridge._port), (45993, False, 45993))
        self.assertEqual(sum('listener stays on port 45993' in c[0][0] for c in logged.call_args_list), 1)
        self.refuse.clear()
        self.prefer(keyboard=True, simplified_menus=False)
        listener = self.idle(listener, 2)
        self.assertEqual((listener.port, bridge._port), (45995, 45995))

    def test_full_menus_port_taken_falls_back_to_the_keyboard_port(self):
        self.refuse.add(45995)
        with patch.object(bridge, 'log') as logged:
            port, listener = bridge._open_listener(45995)
        self.assertEqual((port, listener.port), (45993, 45993))
        self.assertIn('simplified menus stay on', logged.call_args[0][0])

    def test_speech_only_never_falls_back_to_a_keyboard_port(self):
        self.refuse.add(45994)
        with self.assertRaises(OSError):
            bridge._open_listener(45994)
        self.assertEqual(self.bound, [])

    def test_the_fallback_is_not_retried_and_never_closes_a_session(self):
        self.refuse.add(45995)
        self.prefer(simplified_menus=False)
        with patch.object(bridge, 'log'):
            bridge._wanted = bridge._seen = 45995
            bridge._port, listener = bridge._open_listener(45995)
            for _ in range(4):
                self.assertFalse(bridge._preference_moved())  # a connected UI stays connected
            listener = self.idle(listener, 4)
        self.assertEqual(self.bound, [45993])
        self.prefer(simplified_menus=True)                    # now wanted and served agree
        listener = self.idle(listener, 3)
        self.assertEqual((self.bound, bridge._port), ([45993], 45993))


def free_ports(count):
    holders = [socket.socket() for _ in range(count)]
    try:
        for holder in holders:
            holder.bind(('127.0.0.1', 0))
        return [holder.getsockname()[1] for holder in holders]
    finally:
        for holder in holders:
            holder.close()


def accepts(port):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=0.5):
            return True
    except OSError:
        return False


class ReturnToMainMenuTests(unittest.TestCase):
    """Real loopback sockets on free ports (never the game's own ports). A UI
    copy can stay connected from the main menu through a loaded game and
    back, so a settings change closes an idle session and moves the listener
    at once; the main menu then reads the current choice."""

    def setUp(self):
        on, speech_only, off = free_ports(3)
        self.ports = patch.multiple(bridge, PORT_KEYBOARD=on, PORT_SPEECH=speech_only,
                                    PORT_KEYBOARD_FULL_MENUS=off)
        self.ports.start()
        self.addCleanup(self.ports.stop)
        self.on, self.off = on, off
        self.settings = Settings(keyboard=True, simplified_menus=True, startup=True)
        self.modules = patch.dict(sys.modules, {'tyjokr_a11y_settings': self.settings})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.logs = []
        self.logger = patch.object(bridge, 'log', side_effect=self.logs.append)
        self.logger.start()
        self.addCleanup(self.logger.stop)
        bridge._stop.clear()
        self.thread = threading.Thread(target=bridge._serve, daemon=True)
        self.thread.start()
        self.addCleanup(self.finish)
        self.wait_for(lambda: bridge._port == on and accepts(on))

    def finish(self):
        bridge._stop.set()
        self.thread.join(timeout=5)
        bridge._stop.clear()
        bridge._wanted = bridge._seen = None

    def wait_for(self, condition, seconds=4.0):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if condition():
                return True
            time.sleep(0.05)
        self.fail('condition not met; log: {}'.format(self.logs))

    def connect(self, port):
        client = socket.create_connection(('127.0.0.1', port))
        client.sendall(b'HELLO|A11Y_STARTUP_V2\n')
        self.wait_for(lambda: bridge._connected)
        return client

    def test_the_main_menu_reads_the_current_choice(self):
        self.settings.values['simplified_menus'] = False
        self.wait_for(lambda: bridge._port == self.off)
        self.assertTrue(accepts(self.off))
        self.assertFalse(accepts(self.on))
        self.assertTrue(any('simplified menus off' in line for line in self.logs), self.logs)
        self.settings.values['simplified_menus'] = True
        self.wait_for(lambda: bridge._port == self.on)
        self.assertTrue(accepts(self.on))

    def test_an_idle_connected_ui_is_closed_and_the_port_moves(self):
        client = self.connect(self.on)
        try:
            client.settimeout(4)
            self.settings.values['simplified_menus'] = False
            self.assertEqual(client.recv(1), b'')               # closed by us, not a byte written
        finally:
            client.close()
        self.wait_for(lambda: bridge._port == self.off)
        self.assertFalse(accepts(self.on))
        self.assertTrue(any('settings now ask for port {}'.format(self.off) in line
                            for line in self.logs), self.logs)
        client = self.connect(self.off)                          # the new copy reads "off"
        client.close()

    def test_a_ui_that_reconnects_at_once_lands_on_the_new_port(self):
        client = self.connect(self.on)
        client.settimeout(4)
        self.settings.values['simplified_menus'] = False
        self.assertEqual(client.recv(1), b'')
        client.close()
        landed = None
        deadline = time.monotonic() + 4
        while landed is None and time.monotonic() < deadline:
            for port in (self.on, self.off):                     # a Flash probe, as fast as it can
                try:
                    probe = socket.create_connection(('127.0.0.1', port), timeout=0.2)
                except OSError:
                    continue
                try:
                    probe.sendall(b'HELLO|A11Y_STARTUP_V2\n')
                    probe.settimeout(1.5)
                    closed = probe.recv(1) == b''
                except socket.timeout:
                    closed = False                               # still connected: it stayed
                except OSError:
                    closed = True
                finally:
                    probe.close()
                if not closed:
                    landed = port
                    break
        self.assertEqual(landed, self.off)
        self.assertEqual(sum('settings now ask for port' in line for line in self.logs), 1)

    def test_a_busy_ui_is_still_checked(self):
        client = self.connect(self.on)
        try:
            self.settings.values['simplified_menus'] = False
            client.settimeout(0.1)
            deadline = time.monotonic() + 4
            closed = False
            while time.monotonic() < deadline and not closed:
                try:
                    client.sendall(b'POST|a11y.mark|busy\n')    # never idle for half a second
                    closed = client.recv(1) == b''
                except socket.timeout:
                    continue
                except OSError:
                    closed = True
            self.assertTrue(closed)
        finally:
            client.close()
        self.wait_for(lambda: bridge._port == self.off)


if __name__ == '__main__':
    unittest.main()
