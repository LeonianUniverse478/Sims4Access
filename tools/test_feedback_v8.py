"""Behavior checks for owner release and opening narration (no game hooks)."""
import unittest
from unittest.mock import patch
from urllib.parse import quote
import test_scanner_v5 as env
import tyjokr_a11y_narrator as narrator
import tyjokr_a11y_scanner as scanner
import test_keyboard_v7 as keyboard_env


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        env.settings._stored.clear()
        env.keys._enabled = True
        env.keys._editing_active = False
        env.keys._modal_active = False
        env.keys._hook_handle = None
        env.keys._hook_edges.clear()
        env.keys._hook_state.clear()
        env.queue.clear()
        env.messages.clear()

    def test_closed_owner_returns_camera_escape_and_scanner(self):
        env.keys.a11y_modalstate('10')
        self.assertEqual(env.keys._plain_message(27), 'A11yEscape')
        env.keys.a11y_modalstate('00')
        for vk in (27, 37, 38, 39, 40):
            self.assertIsNone(env.keys._plain_message(vk))
        with patch.object(scanner, 'on_key') as action:
            env.keys._chord('next')
            env.drain()
            action.assert_called_once_with('next', on_simulation_thread=True)

    def test_closed_owner_opens_real_hub_via_simulation_pump(self):
        with patch.object(env.keys.tyjokr_a11y_hub, 'open_hub') as opened:
            env.keys.a11y_modalstate('00')
            env.keys._chord('help')
            opened.assert_not_called()
            env.drain()
            opened.assert_called_once_with()

    def test_opening_body_and_first_choice_are_one_utterance(self):
        payload = 'dialog\x0210|0|New Family Dynamic\x0120|0|Do these Sims get along?\x020|0|Yes'
        with patch.object(env.speech, 'speak') as speak:
            self.assertTrue(narrator.a11y_scope_enc(quote(payload)))
            speak.assert_called_once()
            line = speak.call_args[0][0]
            self.assertLess(line.index('New Family Dynamic'), line.index('Do these Sims'))
            self.assertLess(line.index('Do these Sims'), line.index('Yes'))
            self.assertEqual(speak.call_args[1]['source'], 'widget')

    def test_panel_title_preserves_polish_and_precedes_content(self):
        payload = '\x020|0|Umiejętności\x0210|0|Łucja\x0120|0|Poziom 7'
        with patch.object(env.speech, 'speak') as speak:
            narrator.a11y_scope_enc(quote(payload))
            line = speak.call_args[0][0]
            self.assertTrue(line.startswith('Umiejętności'))
            self.assertIn('Łucja', line)
            self.assertNotIn('Dialog', line)

    def test_invalid_scope_payload_is_silent(self):
        with patch.object(env.speech, 'speak') as speak:
            self.assertFalse(narrator.a11y_scope_enc('truncated'))
            speak.assert_not_called()

    def test_arrow_release_while_ctrl_alt_held_releases_native_guard(self):
        env.keys.a11y_modalstate('10')
        samples = [{40: 0x8000}, {40: 0x8000, 17: 0x8000, 18: 0x8000},
                   {17: 0x8000, 18: 0x8000}, {}]
        messages = keyboard_env.KeyboardTests.run_samples(self, samples)
        # Adding modifiers to an existing hold is no second key press.
        # Its eventual release must still free the native guard.
        self.assertEqual(messages, ['A11yArrowDown', 'A11y|keyup|40'])

    def test_hook_keyup_beats_stale_polled_key_state(self):
        env.keys.a11y_modalstate('10')
        env.keys._hook_handle = 1
        env.keys._hook_last_event = 10.0
        env.keys._hook_state[40] = False
        samples = [{40: 0x8000}, {40: 0x8000, 17: 0x8000, 18: 0x8000}, {}]
        messages = keyboard_env.KeyboardTests.run_samples(self, samples)
        self.assertEqual(messages, ['A11yArrowDown', 'A11y|keyup|40'])

    def test_expired_hook_still_allows_polled_scanner_input(self):
        env.keys.a11y_modalstate('10')
        env.keys._hook_handle = 1
        env.keys._hook_last_event = 0.0
        env.keys._hook_state[40] = False
        samples = [{40: 0x8000, 17: 0x8000, 18: 0x8000},
                   {17: 0x8000, 18: 0x8000}, {}]
        messages = keyboard_env.KeyboardTests.run_samples(self, samples)
        self.assertEqual(messages, ['A11yNavNext', 'A11y|keyup|40'])


if __name__ == '__main__':
    unittest.main()
