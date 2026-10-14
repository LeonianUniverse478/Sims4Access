"""Simpler options file: scanner swallow is no longer a player option (its
protection is always on), auto focus is read but no longer written, every
other value survives a save, and old files load without warnings.
Run with py -3.7 tools/test_settings_simplified.py.
"""
import os
import tempfile
import unittest
from unittest.mock import patch

import test_scanner_v5 as env

settings = env.settings
keys = env.keys
menu = env.menu

LEGACY = """# old file with every section the mod ever wrote
[features]
sim actions = on
object names = off
keyboard = on
numpad navigation = on
scanner = on
scanner swallow = off
captions = on
startup speech = off
travel list = off
build controls = on
scanner mode = on

[speech]
mode = manual
braille = full
logging = on
tooltip delay = 2.5

[voice]
rate = -3
volume = 55
name = david

[behavior]
auto focus = on
"""


class SimplifiedSettingsTests(unittest.TestCase):
    def setUp(self):
        self.saved = dict(settings._stored)
        self.old_path = settings.PATH
        self.folder = tempfile.TemporaryDirectory()
        settings.PATH = os.path.join(self.folder.name, 'test.cfg')
        self.addCleanup(self.restore)

    def restore(self):
        settings.PATH = self.old_path
        settings._stored.clear()
        settings._stored.update(self.saved)
        del settings.load_errors[:]
        self.folder.cleanup()

    def load(self, text):
        with open(settings.PATH, 'w', encoding='utf-8') as handle:
            handle.write(text)
        settings.reload()

    def written(self):
        with open(settings.PATH, encoding='utf-8') as handle:
            return handle.read()

    def test_new_file_has_no_swallow_or_auto_focus_and_no_dashes(self):
        text = settings.render_default()
        for gone in ('scanner swallow', 'auto focus', '[behavior]', 'captions'):
            self.assertNotIn(gone, text)
        self.assertNotIn(chr(0x2014), text)
        self.assertNotIn(chr(0x2013), text)
        for line in ('keyboard = on', 'scanner = on', 'scanner mode = off', 'travel list = on',
                     'object names = on', 'sim actions = on', 'startup speech = on',
                     'numpad navigation = off', 'build controls = on', 'mode = hover',
                     'braille = concise', 'tooltip delay = 1.5', 'logging = off',
                     'rate = 3', 'volume = 70', 'name = zira'):
            self.assertIn(line, text)
        self.assertNotIn('scanner_swallow', settings.DEFAULTS)

    def test_old_file_loads_quietly_and_keeps_every_value_on_save(self):
        self.load(LEGACY)
        self.assertEqual(settings.load_errors, [])
        expected = {'sim_actions': True, 'object_names': False, 'keyboard': True,
                    'numpad_navigation': True, 'scanner': True, 'captions': True,
                    'startup': False, 'travel_list': False, 'build_controls': True,
                    'scanner_mode': True, 'speech_mode': 'manual', 'braille_mode': 'full',
                    'logging': True, 'tooltip_delay': 2.5, 'sapi_rate': -3,
                    'sapi_volume': 55, 'sapi_voice': 'david', 'auto_focus': True}
        for key, value in expected.items():
            self.assertEqual(settings.get(key), value, key)
        self.assertNotIn('scanner_swallow', settings._stored)
        settings.set('captions', True)                      # any in-game change rewrites the file
        text = self.written()
        self.assertNotIn('scanner swallow', text)
        self.assertNotIn('auto focus', text)
        settings.reload()
        for key, value in expected.items():
            if key not in ('auto_focus', 'captions'):
                self.assertEqual(settings.get(key), value, key + ' after save')

    def test_protection_stays_on_whatever_an_old_file_said(self):
        self.load(LEGACY)
        settings._stored['scanner_swallow'] = False          # even a stale stored value
        with patch.object(keys, '_enabled', True):
            self.assertTrue(keys._swallow_enabled())
        with patch.object(keys, '_enabled', False):
            self.assertFalse(keys._swallow_enabled())      # keyboard off still means no hook

    def test_menu_and_readout_no_longer_offer_it(self):
        self.assertNotIn('scanner_swallow', [row.key for row in menu.ROWS])
        import tyjokr_a11y_narrator as narrator
        lines = []
        with patch.object(env.commands, 'CheatOutput', lambda connection: lines.append):
            narrator.a11y_settings()
        self.assertFalse(any('swallow' in line for line in lines), lines)

    def test_the_users_installed_file_round_trips(self):
        installed = os.path.join(os.path.expanduser('~'), 'Documents', 'Electronic Arts', 'The Sims 4',
                                 'Mods', 'TS4_Access', 'TS4_Access.cfg')
        if not os.path.isfile(installed):
            self.skipTest('no installed options file on this machine')
        with open(installed, encoding='utf-8') as handle:
            original = handle.read()                      # read only; the real file is never written
        self.load(original)
        self.assertEqual(settings.load_errors, [])
        before = {key: settings.get(key) for key in settings.DEFAULTS if key != 'auto_focus'}
        settings.set('sim_actions', settings.get('sim_actions'))
        settings.reload()
        after = {key: settings.get(key) for key in settings.DEFAULTS if key != 'auto_focus'}
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
