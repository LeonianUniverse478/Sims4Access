"""Shortcut help follows live bindings and uses one interrupt-safe utterance."""
import types
import unittest
from unittest.mock import patch

import test_scanner_v5 as env
import tyjokr_a11y_hub as hub
import tyjokr_a11y_scanner as scanner
import tyjokr_a11y_shortcuts as shortcuts


class ShortcutTests(unittest.TestCase):
    def setUp(self):
        self.locale = patch.object(env.lang, '_locale_lang', 'en')
        self.locale.start()
        self.addCleanup(self.locale.stop)

    def test_every_registered_chord_has_a_spoken_meaning(self):
        for vk, (intent, _) in env.keys.CHORDS.items():
            self.assertIn(vk, env.keys.CHORD_NAMES)
            self.assertTrue(intent in shortcuts.CHORD_LABELS or
                            intent in {'sim{}'.format(n) for n in range(1, 9)}, intent)
            self.assertNotEqual(shortcuts.chord_label(intent), intent)
        rows = shortcuts.sections(numpad=False)[1][1]
        self.assertEqual(len(rows), len(env.keys.CHORDS))
        for number in range(1, 9):
            self.assertIn('Control + Alt + {}: control household Sim {}'.format(number, number), rows)

    def test_readout_uses_runtime_tables_not_a_stale_key_list(self):
        fake = types.SimpleNamespace(
            BINDINGS={'new': ('new test action', [(0x51, True)])},
            CHORDS={0x56: ('help', False)}, CHORD_NAMES={0x56: 'V'}, NUMPAD_BINDINGS={})
        sections = shortcuts.sections(fake, numpad=False)
        self.assertIn('Alt + Q: new test action', sections[0][1])
        self.assertEqual(sections[1][1], ['Control + Alt + V: open the accessibility menu'])

    def test_numpad_setting_is_reread_and_every_mapping_is_described(self):
        with patch.dict(env.settings._stored, {'numpad_navigation': False}):
            self.assertEqual(len(shortcuts.sections()), 2)
            env.settings._stored['numpad_navigation'] = True
            sections = shortcuts.sections()
            rows = sections[2][1]
            self.assertEqual(len(rows), len(env.keys.NUMPAD_BINDINGS))
            self.assertIn('Numpad 8: read again or stop', rows)
            self.assertIn('Numpad decimal: back or close', rows)
            self.assertIn('Num Lock', sections[2][0])

    def test_plain_variants_and_context_are_present_without_duplicate_hub_chord(self):
        text = shortcuts.readout()
        self.assertIn('Shift + Tab: previous control', text)
        self.assertIn('Control + Shift + N:', text)
        self.assertEqual(text.count('Control + Alt + H:'), 1)
        self.assertIn('Open panels and dialogs take priority', text)
        self.assertIn('In text fields, ordinary keys edit text', text)
        self.assertIn('left bracket', text)
        self.assertNotIn('0x', text)

    def test_all_plain_bindings_and_alternatives_are_included(self):
        rows = shortcuts.sections(numpad=False)[0][1]
        # Shift + Tab and Control + Shift + N, plus the Simplified menus line
        # while that setting is on (the default).
        extra = 3 if env.settings.get('simplified_menus', True) else 2
        self.assertEqual(len(rows), sum(len(combos) for _, combos in env.keys.BINDINGS.values()) + extra)
        for label, _ in env.keys.BINDINGS.values():
            self.assertTrue(any(label in row for row in rows), label)

    def test_hub_speaks_complete_help_once_even_when_scanner_is_off(self):
        with patch.dict(env.settings._stored, {'scanner': False}), patch.object(env.speech, 'speak') as say:
            self.assertTrue(hub.scanner_help())
            say.assert_called_once_with(shortcuts.readout(), explicit=True)

    def test_legacy_scanner_help_uses_same_full_readout(self):
        with patch.object(scanner, 'enabled', return_value=True), patch.object(env.speech, 'speak') as say:
            scanner.on_key('help')
            say.assert_called_once_with(shortcuts.readout(), explicit=True)

    def test_hub_offers_keyboard_shortcuts_row(self):
        with patch.object(hub, '_window', return_value=True) as window, patch.object(hub.menu, '_raw', side_effect=lambda x: x):
            hub.open_hub()
        rows = window.call_args[0][2]
        self.assertIn(('Keyboard shortcuts', None, hub.scanner_help), rows)
        self.assertFalse(any(name == 'Scanner help' for name, _, _ in rows))

    def test_untranslated_locale_falls_back_to_readable_english(self):
        with patch.object(env.lang, '_locale_lang', 'fr'):
            self.assertEqual(env.lang.t('keyboard shortcuts'), 'Keyboard shortcuts')
            self.assertIn('control household Sim 8', shortcuts.readout())


if __name__ == '__main__':
    unittest.main(verbosity=2)
