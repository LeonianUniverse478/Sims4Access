"""Scanner dispatch keeps one simulation crossing and preserves ownership."""
import unittest
import sys
import types
from unittest.mock import patch
import test_feedback_v9 as fixture
import tyjokr_a11y_scanner as scanner


class ScannerDispatchTests(unittest.TestCase):
    def setUp(self):
        self.enabled = patch.object(scanner, 'enabled', return_value=True)
        self.enabled.start()
        self.addCleanup(self.enabled.stop)
        self.menu = patch.object(scanner, '_menu_open', False)
        self.menu.start()
        self.addCleanup(self.menu.stop)

    def test_poll_thread_still_queues_game_work(self):
        with patch.object(scanner.pump, 'post', return_value=True) as post, \
                patch.object(scanner, '_dispatch') as dispatch:
            scanner.on_key('next')
            post.assert_called_once_with(dispatch, 'next')
            dispatch.assert_not_called()

    def test_simulation_callback_does_not_wait_for_second_alarm(self):
        with patch.object(scanner.pump, 'post') as post, \
                patch.object(scanner, '_dispatch') as dispatch:
            scanner.on_key('next', on_simulation_thread=True)
            dispatch.assert_called_once_with('next')
            post.assert_not_called()

    def test_disabled_scanner_never_dispatches_inline(self):
        with patch.object(scanner, 'enabled', return_value=False), \
                patch.object(scanner, '_dispatch') as dispatch:
            scanner.on_key('next', on_simulation_thread=True)
            dispatch.assert_not_called()

    def test_open_pie_keeps_ui_routing(self):
        import tyjokr_a11y_keys as keys
        with patch.object(scanner, '_menu_open', True), \
                patch.object(keys, '_send') as send, \
                patch.object(scanner, '_dispatch') as dispatch:
            scanner.on_key('next', on_simulation_thread=True)
            send.assert_called_once_with(scanner.MENU_KEYS['next'])
            dispatch.assert_not_called()

    def test_world_key_reaches_scanner_in_one_drain(self):
        import test_scanner_v5 as env
        keys = env.keys
        env.queue.clear()
        self.addCleanup(env.queue.clear)
        build = types.SimpleNamespace(active=lambda: False, aiming=lambda: False)
        grid = types.SimpleNamespace(active=lambda: False)
        with patch.dict(sys.modules, {'tyjokr_a11y_build': build,
                                      'tyjokr_a11y_grid': grid}), \
                patch.object(keys, '_modal_active', False), \
                patch.object(keys, '_editing_active', False), \
                patch.object(keys.settings, 'get', return_value=True), \
                patch.object(scanner, '_dispatch') as dispatch:
            keys._chord('next')
            dispatch.assert_not_called()
            self.assertEqual(len(env.queue), 1)
            env.drain()
            dispatch.assert_called_once_with('next')
            self.assertEqual(env.queue, [])


if __name__ == '__main__':
    unittest.main()
