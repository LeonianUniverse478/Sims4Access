"""Ctrl+Alt+L turns diagnostic logging on or off without the cheat console:
the settings window's Logging row, toggled and saved the same way, with the
new state spoken. A text field keeps the key; dialogs do not block it.
"""
import unittest
from unittest.mock import patch

import test_scanner_v5 as env
import tyjokr_a11y_shortcuts as shortcuts

keys = env.keys
lang = env.lang
speech = env.speech
settings = env.settings


class LoggingShortcutTests(unittest.TestCase):
    def setUp(self):
        self.saved = dict(settings._stored)
        self.addCleanup(lambda: (settings._stored.clear(), settings._stored.update(self.saved)))
        self.was = speech.log_enabled
        self.addCleanup(lambda: setattr(speech, 'log_enabled', self.was))
        env.queue.clear()
        keys._enabled = True
        keys._modal_active = keys._editing_active = False
        self.spoken = []
        for item in (patch.object(speech, 'speak', side_effect=lambda text, *a, **k: self.spoken.append(text)),
                     patch.object(speech, 'log_line', lambda *a, **k: None),
                     patch.object(settings, '_save', return_value=True),
                     patch.object(lang, '_locale_lang', 'en')):
            item.start()
            self.addCleanup(item.stop)

    def test_l_is_the_logging_chord_and_is_described(self):
        self.assertEqual(keys.CHORDS[0x4C], ('logging', False))
        self.assertEqual(keys.CHORD_NAMES[0x4C], 'L')
        self.assertIn('logging', shortcuts.chord_label('logging'))
        rows = shortcuts.sections(numpad=False)[1][1]
        self.assertTrue(any(row.startswith('Control + Alt + L:') for row in rows), rows)

    def test_it_toggles_saves_and_speaks(self):
        speech.log_enabled = False
        keys._chord('logging')
        env.drain()
        self.assertTrue(speech.log_enabled)
        self.assertTrue(settings._stored.get('logging'))
        self.assertEqual(self.spoken[-1], '{}: {}'.format(lang.t('logging'), lang.t('on')))
        keys._chord('logging')
        env.drain()
        self.assertFalse(speech.log_enabled)
        self.assertFalse(settings._stored.get('logging'))
        self.assertEqual(self.spoken[-1], '{}: {}'.format(lang.t('logging'), lang.t('off')))

    def test_dialogs_allow_it_and_typing_keeps_the_key(self):
        speech.log_enabled = False
        keys.apply_modal_state('101', 'context')        # a dialog is open
        keys._chord('logging')
        env.drain()
        self.assertTrue(speech.log_enabled)
        keys.apply_modal_state('01', 'modalstate')      # typing in a text field
        keys._chord('logging')
        env.drain()
        self.assertTrue(speech.log_enabled)


if __name__ == '__main__':
    unittest.main()
