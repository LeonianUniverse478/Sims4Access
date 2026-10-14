"""Scanner mode (persisted setting): plain keys browse the scanner tree while
Flash reports the scanner owns input; the Live signal drives the camera
follow. Actual key loop and command handlers, mocked Windows and client.
Run with py -3.7 tools/test_scanner_mode.py.
"""
import types
import unittest
from unittest.mock import Mock, patch

import test_scanner_v5 as env
import test_keyboard_v7 as keyboard_env

keys = env.keys
settings = env.settings


class ScannerModeBase(unittest.TestCase):
    def setUp(self):
        self.saved = dict(settings._stored)
        self.addCleanup(self.restore)
        settings._stored['scanner'] = True
        settings._stored['keyboard'] = True     # the shared env stores False to keep threads off
        settings._stored['scanner_mode'] = False
        keys._enabled = True
        keys._modal_active = keys._editing_active = False
        keys._scanner_owner = keys._scanner_live = False
        keys._scanner_suspended = keys._scanner_pending_announce = False
        keys._input_epoch = 0
        keys._opening_keys.clear()
        keys._route_logged.clear()
        env.queue.clear()
        env.messages.clear()
        self.scanner = types.SimpleNamespace(enter_mode=Mock(), resume_mode=Mock(), on_key=Mock(),
                                             set_camera_live=Mock(), update_camera_follow=Mock(),
                                             a11y_menuclosed=Mock())
        self.zone = types.SimpleNamespace(is_in_build_buy=False)
        self.grid = types.SimpleNamespace(active=Mock(return_value=False), leave=Mock())
        modules = patch.dict(env.sys.modules, {
            'tyjokr_a11y_scanner': self.scanner, 'tyjokr_a11y_grid': self.grid,
            'services': types.SimpleNamespace(current_zone=lambda: self.zone)})
        modules.start()
        self.addCleanup(modules.stop)
        for name, value in (('_save', True),):
            p = patch.object(settings, name, return_value=value)
            p.start()
            self.addCleanup(p.stop)
        self.speak = patch.object(env.speech, 'speak')
        self.spoken = self.speak.start()
        self.addCleanup(self.speak.stop)

    def restore(self):
        settings._stored.clear()
        settings._stored.update(self.saved)

    def said(self):
        return [call[0][0] for call in self.spoken.call_args_list]

    def turn_on_and_confirm(self):
        self.assertTrue(keys.set_scanner_mode(True))
        keys.a11y_scannerowner('1')
        self.scanner.enter_mode.reset_mock()
        env.messages.clear()


class ToggleTests(ScannerModeBase):
    def test_on_persists_and_waits_for_the_client_before_speaking(self):
        self.assertTrue(keys.set_scanner_mode(True))
        self.assertTrue(settings.get('scanner_mode'))
        self.assertIn('A11y|scannermode|on', env.messages)
        self.scanner.enter_mode.assert_not_called()            # nothing spoken before Flash confirms
        keys.a11y_scannerowner('1')
        self.scanner.enter_mode.assert_called_once_with()
        keys.a11y_scannerowner('1')                             # a heartbeat re-post changes nothing
        self.scanner.enter_mode.assert_called_once_with()
        self.scanner.resume_mode.assert_not_called()

    def test_on_outside_live_says_when_it_starts(self):
        self.zone.is_in_build_buy = True
        self.assertTrue(keys.set_scanner_mode(True))
        self.assertIn('Scanner mode on. It starts in Live mode.', self.said())

    def test_off_releases_everything_and_says_so(self):
        self.turn_on_and_confirm()
        keys.a11y_scannerlive('1')
        self.assertTrue(keys.set_scanner_mode(False))
        self.assertFalse(settings.get('scanner_mode'))
        self.assertIn('A11y|scannermode|off', env.messages)
        self.assertIn('Scanner mode off.', self.said())
        self.scanner.set_camera_live.assert_called_with(False)   # released at once
        self.assertFalse(keys._scanner_routing())

    def test_needs_keyboard_and_scanner_settings(self):
        settings._stored['scanner'] = False
        self.assertFalse(keys.set_scanner_mode(True))
        self.assertFalse(settings.get('scanner_mode'))
        settings._stored['scanner'] = True
        settings._stored['scanner_mode'] = True
        keys._enabled = False
        keys._announce_scanner_mode()
        self.assertEqual(env.messages[-1], 'A11y|scannermode|off')   # capture removed

    def test_ctrl_alt_space_toggles_through_the_pump(self):
        keys._chord('scannermode')
        env.drain()
        self.assertTrue(settings.get('scanner_mode'))
        keys._chord('scannermode')
        env.drain()
        self.assertFalse(settings.get('scanner_mode'))

    def test_console_command(self):
        self.assertTrue(keys.a11y_scannermode('on'))
        self.assertTrue(settings.get('scanner_mode'))
        self.assertFalse(keys.a11y_scannermode('sideways'))
        self.assertTrue(keys.a11y_scannermode('toggle'))
        self.assertFalse(settings.get('scanner_mode'))

    def test_grid_and_scanner_mode_are_exclusive(self):
        self.grid.active.return_value = True
        keys.set_scanner_mode(True)
        self.grid.leave.assert_called_once_with()

    def test_heartbeat_follows_the_effective_setting_and_the_camera(self):
        settings._stored['scanner_mode'] = True
        keys._scanner_live = True
        keys._announce_ui_settings()
        self.assertIn('A11y|scannermode|on', env.messages)
        self.scanner.update_camera_follow.assert_called_once_with()


class RoutingTests(ScannerModeBase):
    def keys_after(self, frames):
        keyboard_env.KeyboardTests.run_samples(self, frames)
        return [call[0][0] for call in self.scanner.on_key.call_args_list]

    def test_plain_keys_browse_the_scanner_while_it_owns_input(self):
        self.turn_on_and_confirm()
        for vk, intent in ((0x28, 'next'), (0x26, 'prev'), (0x27, 'nextcat'), (0x25, 'prevcat'),
                           (0x0D, 'open'), (0x08, 'back'), (0x20, 'repeat')):
            self.scanner.on_key.reset_mock()
            self.assertEqual(self.keys_after([{vk: 1}, {}]), [intent], hex(vk))
        for call in self.scanner.on_key.call_args_list:
            self.assertEqual(call[1], {'on_simulation_thread': True})

    def test_escape_is_never_a_scanner_key(self):
        self.turn_on_and_confirm()
        self.assertIsNone(keys._plain_message(0x1B))
        self.assertEqual(self.keys_after([{0x1B: 1}, {}]), [])

    def test_down_repeats_right_does_not(self):
        self.turn_on_and_confirm()
        held = self.keys_after([{0x28: 0x8001}] + [{0x28: 0x8000}] * 80 + [{}])
        self.assertGreater(held.count('next'), 3)
        self.scanner.on_key.reset_mock()
        held = self.keys_after([{0x27: 0x8001}] + [{0x27: 0x8000}] * 80 + [{}])
        self.assertEqual(held, ['nextcat'])

    def test_a_dialog_owner_gets_the_keys(self):
        self.turn_on_and_confirm()
        keys.a11y_modalstate('10')
        self.assertEqual(keys._plain_message(0x28), 'A11yArrowDown')
        self.assertEqual(self.keys_after([{0x28: 1}, {}]), [])

    def test_a_text_field_gets_the_keys(self):
        self.turn_on_and_confirm()
        keys._editing_active = True
        self.assertIsNone(keys._plain_message(0x28))

    def test_no_routing_without_the_client_confirmation(self):
        keys.set_scanner_mode(True)                             # owner not yet reported
        self.assertIsNone(keys._plain_message(0x28))

    def test_a_key_queued_before_the_owner_left_is_dropped(self):
        self.turn_on_and_confirm()
        keys._send('A11yScanner:next')
        keys.a11y_scannerowner('0')                             # a pie opened first
        env.drain()
        self.scanner.on_key.assert_not_called()


class ResumeTests(ScannerModeBase):
    def test_resume_after_a_menu_with_the_opening_fence(self):
        self.turn_on_and_confirm()
        keys.a11y_scannerowner('0')                             # a pie took input
        epoch = keys._input_epoch
        keys.a11y_scannerowner('1')
        self.scanner.resume_mode.assert_called_once_with()
        self.assertGreater(keys._input_epoch, epoch)          # a held Enter cannot reopen it

    def test_zone_load_announces_again_on_confirmation(self):
        self.turn_on_and_confirm()
        keys.a11y_scannerowner('0')
        keys.scanner_zone_started()
        keys.a11y_scannerowner('1')
        self.scanner.enter_mode.assert_called_once_with()
        self.scanner.resume_mode.assert_not_called()

    def test_owner_and_live_reports_are_validated(self):
        self.assertFalse(keys.a11y_scannerowner('2'))
        self.assertFalse(keys.a11y_scannerlive(None))
        self.assertTrue(keys.a11y_scannerowner(1))              # a number payload is normalized
        self.assertTrue(keys._scanner_owner)

    def test_every_live_report_reaches_the_camera(self):
        # The camera module dedupes; a zone reset there resumes on the next
        # report even though this flag did not change.
        settings._stored['scanner_mode'] = True
        keys.a11y_scannerlive('1')
        keys.a11y_scannerlive('1')
        keys.a11y_scannerlive('0')
        self.assertEqual([c[0][0] for c in self.scanner.set_camera_live.call_args_list], [True, True, False])

    def test_a_key_queued_across_a_menu_round_trip_is_dropped(self):
        self.turn_on_and_confirm()
        keys._send('A11yScanner:open')
        keys.a11y_scannerowner('0')                             # the pie opened
        keys.a11y_scannerowner('1')                             # and closed, all before the pump turn
        env.drain()
        self.scanner.on_key.assert_not_called()

    def test_disable_and_reenable_retire_queued_keys(self):
        self.turn_on_and_confirm()
        keys._send('A11yScanner:next')
        keys.set_scanner_mode(False)
        keys.set_scanner_mode(True)
        keys.a11y_scannerowner('1')
        env.drain()
        self.scanner.on_key.assert_not_called()

    def test_pending_announcement_on_a_repeated_owner_report(self):
        self.turn_on_and_confirm()
        keys.apply_scanner_setting()                            # reload with the mode already on
        keys.a11y_scannerowner('1')                             # the owner never changed
        self.scanner.enter_mode.assert_called_once_with()
        keys.a11y_scannerowner('1')
        self.scanner.enter_mode.assert_called_once_with()

    def test_saved_keyboard_setting_counts(self):
        settings._stored['scanner_mode'] = True
        settings._stored['keyboard'] = False
        self.assertFalse(keys._scanner_effective())

    def test_live_signal_never_enables_the_camera_while_the_setting_is_off(self):
        keys.a11y_scannerlive('1')
        self.assertEqual([c[0][0] for c in self.scanner.set_camera_live.call_args_list], [False])


class ChordRepeatTests(ScannerModeBase):
    def test_repeated_chord_left_right_never_walk_tree_levels(self):
        build = types.SimpleNamespace(active=Mock(return_value=False), aiming=Mock(return_value=False),
                                      controls_enabled=Mock(return_value=False), _zone=Mock(return_value=None))
        with patch.dict(env.sys.modules, {'tyjokr_a11y_build': build}):
            keys._world_chord('nextcat', keys._input_epoch, True)
            keys._world_chord('next', keys._input_epoch, True)
            keys._world_chord('nextcat', keys._input_epoch)
        self.assertEqual([c[0][0] for c in self.scanner.on_key.call_args_list], ['next', 'nextcat'])


class GridRefusalTests(unittest.TestCase):
    """The real grid: scanner mode governs the arrows and the camera, so the
    lot grid refuses to start and never switches the saved mode off."""

    def setUp(self):
        self.saved = dict(settings._stored)
        self.addCleanup(lambda: (settings._stored.clear(), settings._stored.update(self.saved)))
        settings._stored.update({'scanner': True, 'keyboard': True, 'scanner_mode': True,
                                 'build_controls': True})
        keys._enabled = True
        import tyjokr_a11y_grid as grid
        self.grid = grid
        grid._active = False
        self.speak = patch.object(env.speech, 'speak')
        self.spoken = self.speak.start()
        self.addCleanup(self.speak.stop)

    def test_grid_refuses_and_the_saved_mode_stays(self):
        with patch.object(settings, '_save', return_value=True) as saved:
            self.assertFalse(self.grid.enter())
        saved.assert_not_called()
        self.assertTrue(settings.get('scanner_mode'))
        self.assertFalse(self.grid._active)
        self.assertIn('Turn scanner mode off to use the lot grid.',
                      [c[0][0] for c in self.spoken.call_args_list])


if __name__ == '__main__':
    unittest.main()
