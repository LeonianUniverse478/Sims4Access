"""Opening-key isolation and Build/grid routing, with native/game APIs stubbed."""
import ctypes
import types
import unittest
from unittest.mock import Mock, patch

import test_scanner_v5 as env
import test_keyboard_v7 as keyboard_env

keys = env.keys


class OpeningInputTests(unittest.TestCase):
    def setUp(self):
        env.settings._stored.clear()
        keys._enabled = True
        keys._modal_active = True
        keys._editing_active = False
        keys._opening_keys.clear()
        keys._input_epoch = 0
        keys._hook_handle = None
        keys._hook_edges.clear()
        keys._hook_state.clear()
        env.queue.clear()
        env.messages.clear()

    def tearDown(self):
        keys._opening_keys.clear()

    def fence(self, sampled):
        user32 = types.SimpleNamespace(GetAsyncKeyState=lambda vk: sampled.get(vk, 0))
        with patch.object(ctypes, 'WinDLL', return_value=user32), \
                patch.object(keys, '_game_is_foreground', return_value=True):
            keys.fence_opening_input()

    def test_native_inputfence_accepts_flash_payload_and_command_connection(self):
        with patch.object(keys, 'fence_opening_input') as fence:
            self.assertTrue(keys.a11y_inputfence('', _connection=123))
        fence.assert_called_once_with()

    def test_socket_inputfence_keeps_its_no_argument_path(self):
        with patch.object(keys, 'fence_opening_input') as fence:
            self.assertTrue(keys.a11y_inputfence())
        fence.assert_called_once_with()

    def test_complete_console_enter_tap_cannot_activate_first_picker_row(self):
        self.fence({13: 1})
        result = keyboard_env.KeyboardTests.run_samples(self, [{13: 1}, {}, {13: 1}, {}])
        self.assertEqual(result, ['A11y|keyup|13', 'A11yActivate', 'A11y|keyup|13'])

    def test_held_opener_waits_for_release_before_any_new_activation(self):
        self.fence({13: 0x8001})
        result = keyboard_env.KeyboardTests.run_samples(self, [{13: 0x8000}] * 120 + [{}, {13: 1}, {}])
        self.assertEqual(result, ['A11y|keyup|13', 'A11yActivate', 'A11y|keyup|13'])

    def test_new_press_after_clean_opening_is_not_suppressed(self):
        self.fence({})
        result = keyboard_env.KeyboardTests.run_samples(self, [{13: 1}, {}])
        self.assertEqual(result, ['A11yActivate', 'A11y|keyup|13'])

    def test_space_has_same_opening_protection(self):
        self.fence({32: 1})
        result = keyboard_env.KeyboardTests.run_samples(self, [{32: 1}, {}, {32: 1}, {}])
        self.assertEqual(result, ['A11y|keyup|32', 'A11yToggle', 'A11y|keyup|32'])

    def test_queued_activation_does_not_cross_a_new_scope(self):
        keys._send('A11yActivate')
        self.fence({})
        env.drain()
        self.assertEqual(env.messages, [])

    def test_queued_navigation_is_not_discarded_as_an_activation(self):
        keys._send('A11yArrowDown')
        self.fence({})
        env.drain()
        self.assertEqual(env.messages, ['A11yArrowDown'])

    def test_hook_and_poll_do_not_replay_quarantined_opening_enter(self):
        self.fence({13: 0x8000})
        keys._hook_edges.extend([(13, True, 9.9), (13, False, 9.95)])
        with patch.object(keys, '_chord') as chord:
            keyboard_env.KeyboardTests.run_samples(self, [{17: 0x8000, 18: 0x8000, 13: 1}, {}])
        chord.assert_not_called()

    def test_released_modifier_low_bits_are_not_evidence_of_a_real_chord(self):
        # This documents the unresolved complete-chord sampling limit. The
        # same samples can come from separate Ctrl, Alt and H taps or AltGr.
        with patch.object(keys, '_chord') as chord:
            keyboard_env.KeyboardTests.run_samples(self, [{17: 1, 18: 1, 72: 1}, {}])
        chord.assert_not_called()

    def editing_samples(self, frames, close_during_sample=False):
        # Model Windows consuming bit 0, including input-fence reads. Change
        # editing on the simulation thread between polls or inside a key read.
        position, clock = [0], [10.0]
        values = dict(frames[0][1])
        keys._editing_active = frames[0][0]
        fired = [False]
        def sample(vk):
            raw = values.get(vk, 0)
            values[vk] = raw & 0x8000
            if close_during_sample and vk == 13 and raw and not fired[0]:
                fired[0] = True
                keys.a11y_modalstate('10')
            return raw
        def sleep(seconds):
            # A simulation tick may deliver this poll's action before the next
            # poll notices editing ended; do not hide that race by draining last.
            env.drain()
            position[0] += 1
            clock[0] += seconds
            if position[0] == len(frames):
                keys._running = False
                return
            editing, sampled = frames[position[0]]
            values.clear()
            values.update(sampled)
            keys.a11y_modalstate('11' if editing else '10')
        user32 = types.SimpleNamespace(GetAsyncKeyState=sample)
        keys._running = True
        with patch.object(ctypes, 'WinDLL', return_value=user32), \
                patch.object(keys, '_game_is_foreground', return_value=True), \
                patch.object(keys, '_altgr_pressed', return_value=False), \
                patch.object(keys, 'time', types.SimpleNamespace(monotonic=lambda: clock[0], sleep=sleep)):
            keys._loop()
        env.drain()
        return [message for message in env.messages if message in ('A11yActivate', 'A11yToggle')]

    def test_editing_close_discards_submit_tap_but_accepts_fresh_enter(self):
        self.assertEqual(self.editing_samples([(True, {}), (False, {13: 1}),
                                              (False, {}), (False, {13: 1}), (False, {})]),
                         ['A11yActivate'])

    def test_editing_close_holds_submit_until_release(self):
        self.assertEqual(self.editing_samples([(True, {}), (False, {13: 0x8001}),
                                              (False, {13: 0x8000}), (False, {}),
                                              (False, {13: 1}), (False, {})]), ['A11yActivate'])

    def test_editing_close_during_sample_cannot_replay_submit(self):
        self.assertEqual(self.editing_samples([(True, {13: 1}), (False, {})],
                                              close_during_sample=True), [])


class WorldModeTests(unittest.TestCase):
    def setUp(self):
        env.queue.clear()
        env.messages.clear()
        env.settings._stored.clear()
        keys._modal_active = keys._editing_active = False
        keys._input_epoch = 0
        self.build = types.SimpleNamespace(active=Mock(return_value=False),
            toggle=Mock(), request=Mock(), on_key=Mock(), aim_grid=Mock(),
            aiming=Mock(return_value=False), controls_enabled=Mock(return_value=True),
            _zone=Mock(return_value=None), refuse_disabled=Mock(return_value=False))
        self.grid = types.SimpleNamespace(active=Mock(return_value=False),
            toggle=Mock(), leave=Mock(), on_key=Mock())
        self.scanner = types.SimpleNamespace(on_key=Mock())
        self.modules = patch.dict(env.sys.modules, {'tyjokr_a11y_build': self.build,
            'tyjokr_a11y_grid': self.grid, 'tyjokr_a11y_scanner': self.scanner})
        self.modules.start()

    def tearDown(self):
        self.modules.stop()

    def test_mode_ownership_is_resolved_on_simulation_thread(self):
        self.build.active.return_value = True
        keys._chord('open')
        self.build.active.assert_not_called()
        self.build.on_key.assert_not_called()
        env.drain()
        self.build.on_key.assert_called_once_with('open')
        self.scanner.on_key.assert_not_called()

    def test_build_toggle_delegates_exclusivity_after_destination_validation(self):
        self.grid.active.return_value = True
        keys._chord('buildtoggle')
        env.drain()
        self.build.toggle.assert_called_once_with()
        self.grid.leave.assert_not_called()

    def test_grid_toggle_delegates_exclusivity_after_destination_validation(self):
        self.build.active.return_value = True
        keys._chord('gridtoggle')
        env.drain()
        self.grid.toggle.assert_called_once_with()
        self.build.request.assert_not_called()

    def test_build_toggle_from_catalog_scope_reaches_native_context_validator(self):
        keys._modal_active = True
        keys._chord('buildtoggle')
        env.drain()
        self.build.toggle.assert_called_once_with()

    def test_modal_and_editing_states_do_not_place_or_move_objects(self):
        self.build.active.return_value = True
        keys._modal_active = True
        keys._chord('next')
        env.drain()
        self.assertEqual(env.messages, ['A11yNavNext'])
        self.build.on_key.assert_not_called()
        keys._editing_active = True
        keys._chord('buildtoggle')
        env.drain()
        self.build.toggle.assert_not_called()

    def test_active_grid_gets_movement_and_floor_commands(self):
        self.grid.active.return_value = True
        for intent in ('prev', 'nextcat', 'prevsub', 'nextsub', 'open', 'back'):
            keys._chord(intent)
        env.drain()
        self.assertEqual([args[0][0] for args in self.grid.on_key.call_args_list],
                         ['prev', 'nextcat', 'prevsub', 'nextsub', 'open', 'back'])
        self.scanner.on_key.assert_not_called()

    def test_build_transactions_have_no_scanner_fallback(self):
        for intent in ('rotateleft', 'rotateright', 'undo', 'redo'):
            keys._chord(intent)
        env.drain()
        self.scanner.on_key.assert_not_called()
        self.build.on_key.assert_not_called()

    def test_new_scope_invalidates_queued_world_click(self):
        self.build.active.return_value = True
        keys._chord('open')
        keys._input_epoch += 1
        env.drain()
        self.build.on_key.assert_not_called()

    def test_scanner_disabled_does_not_disable_build_or_grid(self):
        env.settings._stored['scanner'] = False
        self.build.active.return_value = True
        keys._chord('rotateleft')
        env.drain()
        self.build.on_key.assert_called_once_with('rotateleft')

    def test_all_build_bindings_require_explicit_ctrl_alt_layer(self):
        # 2026-09-26: Ctrl+Alt+B is Build placement on the grid (the native
        # pixel cursor stays on a11y.build and Ctrl+Alt+F); X sells.
        expected = {0x42: 'buildplace', 0x54: 'gridtoggle', 0xDB: 'rotateleft',
                    0xDD: 'rotateright', 0x5A: 'undo', 0x59: 'redo', 0x46: 'buildgrid',
                    0x58: 'sell'}
        for vk, intent in expected.items():
            self.assertEqual(keys.CHORDS[vk], (intent, False))
            self.assertIsNone(keys._plain_message(vk))

    def test_grid_aim_reaches_native_projection_before_grid_movement(self):
        self.grid.active.return_value = True
        keys._modal_active = True  # catalog browsing can own a UI scope
        keys._chord('buildgrid')
        env.drain()
        self.build.aim_grid.assert_called_once_with()
        self.grid.on_key.assert_not_called()
        self.build.on_key.assert_not_called()

    def test_pending_native_projection_does_not_fall_through_to_scanner(self):
        self.build.aiming.return_value = True
        keys._chord('open')
        keys._chord('back')
        env.drain()
        self.assertEqual([args[0][0] for args in self.build.on_key.call_args_list], ['open', 'back'])
        self.scanner.on_key.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
