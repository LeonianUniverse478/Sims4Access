"""Received UI ownership must also restore scanner routing after menu close."""
import sys
import types
import unittest
from unittest.mock import patch
from urllib.parse import quote
import test_feedback_v8 as fixture
import test_scanner_v5 as env
import tyjokr_a11y_narrator as narrator
import tyjokr_a11y_scanner as scanner

keys = env.keys


class ContextHandoffTests(unittest.TestCase):
    def setUp(self):
        keys._enabled = True
        keys._modal_active = True
        keys._editing_active = False
        keys._input_epoch = 0
        scanner._menu_open = True
        env.queue.clear()
        env.messages.clear()
        self.addCleanup(env.queue.clear)
        fence = patch.object(keys, 'fence_opening_input', side_effect=lambda:
                             setattr(keys, '_input_epoch', keys._input_epoch + 1))
        fence.start()
        self.addCleanup(fence.stop)

    def context(self, text):
        narrator.a11y_context_enc(quote(text))

    def test_world_context_recovers_when_separate_close_message_is_missing(self):
        self.context('world:00')
        self.assertFalse(keys._modal_active)
        self.assertFalse(scanner._menu_open)
        self.assertGreater(keys._input_epoch, 0)

    def test_repeated_world_context_clears_stale_menu_marker(self):
        keys._modal_active = False
        self.context('world:00')
        self.assertFalse(scanner._menu_open)

    def test_open_widget_context_retains_ui_ownership(self):
        keys._modal_active = False
        self.context('widgets.Gameplay.PieMenu::PieMenuMain/instance383:10')
        self.assertTrue(keys._modal_active)
        self.assertFalse(keys._editing_active)

    def test_editing_state_is_preserved(self):
        self.context('world:01')
        self.assertFalse(keys._modal_active)
        self.assertTrue(keys._editing_active)

    def test_invalid_context_does_not_release_owner(self):
        # 'world:000' is a valid owner+blocking report since the phone guard
        # fix; four digits or a letter in the suffix are still garbage.
        for text in ('world', 'world:garbage', 'world:0000', 'world:00x', ''):
            self.context(text)
            self.assertTrue(keys._modal_active)

    def test_next_scanner_key_dispatches_after_received_world_context(self):
        build = types.SimpleNamespace(active=lambda: False, aiming=lambda: False)
        grid = types.SimpleNamespace(active=lambda: False)
        with patch.dict(sys.modules, {'tyjokr_a11y_build': build,
                                      'tyjokr_a11y_grid': grid}), \
                patch.object(keys.settings, 'get', return_value=True), \
                patch.object(scanner, '_dispatch') as dispatch:
            self.context('world:00')
            keys._chord('next')
            env.drain()
            dispatch.assert_called_once_with('next')
            self.assertNotIn('A11yNavNext', env.messages)


if __name__ == '__main__':
    unittest.main()
