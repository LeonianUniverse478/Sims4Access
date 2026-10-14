"""Behavior checks for v6 input and speech, with native/game APIs stubbed."""
import ctypes
import io
import types
import unittest
from unittest.mock import patch, Mock

import test_scanner_v5 as env

keys, speech = env.keys, env.speech


class NavigationTests(unittest.TestCase):
    def setUp(self):
        keys._enabled = True
        keys._modal_active = False
        keys._editing_active = False
        keys._hook_edges.clear()
        keys._hook_state.clear()
        keys._hook_handle = None
        env.queue.clear()
        env.messages.clear()
        speech._last_text = None
        speech._last_time = 0
        speech._last_source = None
        speech.braille_mode = 'off'
        speech._prism = None
        speech._sapi_proc = None
        speech._backend_name = 'test'

    def poll_once(self, down=(), foreground=True):
        user32 = types.SimpleNamespace(GetAsyncKeyState=lambda vk: 0x8000 if vk in down else 0)
        kernel32 = object()
        fake_time = types.SimpleNamespace(monotonic=lambda: 10.0,
                                         sleep=lambda seconds: setattr(keys, '_running', False))
        keys._running = True
        with patch.object(ctypes, 'WinDLL', side_effect=lambda name, **kw: user32 if name == 'user32' else kernel32), \
                patch.object(keys, '_game_is_foreground', return_value=foreground), \
                patch.object(keys, '_altgr_pressed', return_value=False), \
                patch.object(keys, 'time', fake_time):
            keys._loop()

    def test_navigation_is_delivered_only_by_simulation_pump(self):
        keys._send('A11yNavNext')
        self.assertEqual(env.messages, [])
        env.drain()
        self.assertEqual(env.messages, ['A11yNavNext'])
        with patch.object(env.pump, 'post', return_value=False):
            keys._send('A11yActivate')
        self.assertEqual(env.messages, ['A11yNavNext'])

    def test_modal_owns_chords_and_world_routing_returns_on_close(self):
        scanner = types.SimpleNamespace(on_key=Mock(), a11y_menuclosed=Mock())
        with patch.dict(env.sys.modules, {'tyjokr_a11y_scanner': scanner}):
            keys.a11y_modalstate('10')
            for intent in ('next', 'prev', 'open', 'back', 'rescan', 'nextsub'):
                keys._chord(intent)
            with patch.object(speech, 'repeat_last') as repeat:
                keys._chord('repeat')
                repeat.assert_called_once_with()
            scanner.on_key.assert_not_called()
            env.drain()
            self.assertEqual(env.messages, ['A11yNavNext', 'A11yNavPrev', 'A11yActivate', 'A11yDismiss'])
            self.assertFalse(keys.a11y_modalstate('bad'))
            self.assertTrue(keys._modal_active)
            keys.a11y_modalstate('00')
            keys._chord('next')
            env.drain()
            scanner.on_key.assert_called_once_with('next', on_simulation_thread=True)

    def test_complete_chord_taps_between_samples_preserve_order(self):
        keys._hook_edges.extend([(0x28, True, 9.8), (0x28, False, 9.81),
                                 (0x26, True, 9.82), (0x26, False, 9.83),
                                 (0x28, True, 9.84), (0x28, False, 9.85)])
        with patch.object(keys, '_chord') as chord:
            self.poll_once()
        self.assertEqual([call[0][0] for call in chord.call_args_list], ['next', 'prev', 'next'])

    def test_hook_down_and_poll_down_do_not_duplicate_a_press(self):
        keys._hook_edges.append((0x28, True, 9.9))
        with patch.object(keys, '_chord') as chord:
            self.poll_once((keys.VK_CONTROL, keys.VK_MENU, 0x28))
        chord.assert_called_once_with('next')

    def test_focus_loss_discards_pending_native_input(self):
        keys._hook_edges.append((0x0D, True, 9.9))
        with patch.object(keys, '_chord') as chord:
            self.poll_once(foreground=False)
        chord.assert_not_called()
        self.assertEqual(list(keys._hook_edges), [])

    def test_text_entry_does_not_activate_or_navigate_on_punctuation(self):
        keys.a11y_modalstate('11')
        env.settings._stored['numpad_navigation'] = True
        with patch.object(keys, '_send') as send:
            self.poll_once((0x0D, 0xBD, 0xBF, 0x26, 0x66))
        self.assertEqual([call[0][0] for call in send.call_args_list
                          if call[0][0] != 'A11y|lease'], ['A11yArrowDown'])

    def test_prism_receives_polish_text(self):
        speech._backend_name = 'prism'
        speech._prism = types.SimpleNamespace(output=Mock(return_value=True))
        with patch.object(speech, '_try_init_sapi') as sapi:
            speech._speak_now('Zażółć gęślą jaźń', source='widget')
        speech._prism.output.assert_called_once_with('Zażółć gęślą jaźń', 'Zażółć gęślą jaźń', 'off', True)
        sapi.assert_not_called()

    def test_prism_failure_falls_back_to_windows_speech(self):
        speech._backend_name = 'prism'
        speech._prism = types.SimpleNamespace(output=Mock(return_value=False))
        pipe = io.BytesIO()
        def initialize():
            speech._sapi_proc = types.SimpleNamespace(stdin=pipe)
        with patch.object(speech, '_try_init_sapi', side_effect=initialize) as sapi:
            speech._speak_now('Dialog działa', source='widget')
        sapi.assert_called_once_with()
        self.assertIn(b'Dialog%20dzia%C5%82a', pipe.getvalue())

    def test_braille_only_never_falls_back_to_audio(self):
        speech._backend_name = 'prism'
        speech.braille_mode = 'only'
        speech._prism = types.SimpleNamespace(output=Mock(return_value=False))
        with patch.object(speech, 'has_braille', return_value=True), \
                patch.object(speech, '_try_init_sapi') as sapi:
            speech._speak_now('Dialog', source='widget')
        sapi.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
