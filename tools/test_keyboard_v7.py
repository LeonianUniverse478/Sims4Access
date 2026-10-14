"""Behavior regressions for contextual input and household call routing."""
import ctypes
import types
import unittest
from unittest.mock import patch, Mock
import test_scanner_v5 as env
import tyjokr_a11y_phone as phone

keys = env.keys


class KeyboardTests(unittest.TestCase):
    def setUp(self):
        env.settings._stored.clear()
        keys._enabled = True
        keys._modal_active = False
        keys._editing_active = False
        keys._hook_handle = None
        keys._hook_edges.clear()
        keys._hook_state.clear()
        env.queue.clear()
        env.messages.clear()

    def test_context_and_editing_ownership(self):
        self.assertIsNone(keys._plain_message(0x26))
        self.assertIsNone(keys._plain_message(0x0D))
        self.assertEqual(keys._plain_message(9), 'A11yTabNext')
        keys.a11y_modalstate('10')
        self.assertEqual(keys._plain_message(0x26), 'A11yArrowUp')
        self.assertEqual(keys._plain_message(0x20), 'A11yToggle')
        keys.a11y_modalstate('11')
        for vk in (0x26, 0x28, 0x25, 0x27, 0x0D, 0x20, 0x08):
            self.assertIsNone(keys._plain_message(vk))
        self.assertEqual(keys._plain_message(9, shift=True), 'A11yTabPrev')
        self.assertEqual(keys._plain_message(27), 'A11yEscape')
        keys._enabled = False
        self.assertIsNone(keys._plain_message(9))
        self.assertIsNone(keys._plain_message(27))

    def test_world_shift_tab_is_the_games_first_person_switch(self):
        # 2026-09-26: HUD backward navigation took the game's own first-person
        # camera key. With no menu open Shift+Tab is left to the game; every
        # menu keeps backward Tab.
        self.assertEqual(keys._plain_message(9), 'A11yTabNext')
        self.assertIsNone(keys._plain_message(9, shift=True))
        keys.a11y_modalstate('10')
        self.assertEqual(keys._plain_message(9, shift=True), 'A11yTabPrev')
        keys.a11y_modalstate('11')
        self.assertEqual(keys._plain_message(9, shift=True), 'A11yTabPrev')
        keys.a11y_modalstate('01')
        self.assertIsNone(keys._plain_message(9, shift=True))  # world text field: typing owns Tab
        keys.a11y_modalstate('00')
        self.assertIsNone(keys._plain_message(9, shift=True))
        self.assertIsNone(keys._plain_message(9, ctrl=True, alt=True, shift=True))

    def test_fast_shift_tab_released_before_the_poll_stays_shifted(self):
        # Live 2026-09-26: Shift was already up when the pass read Tab's press
        # bit, so the first-person Shift+Tab also sent TabNext and opened the
        # HUD. Shift's own press bit, or Shift held at the last pass, counts.
        SHIFT = 0x10

        def run(samples):
            env.messages.clear()
            return self.run_samples(samples)
        self.assertEqual(run([{SHIFT: 1, 9: 1}, {}]), ['A11y|keyup|9'])
        self.assertEqual(run([{SHIFT: 0x8000}, {9: 1}, {}]), ['A11y|keyup|9'])
        self.assertEqual(run([{9: 1}, {}]), ['A11yTabNext', 'A11y|keyup|9'])
        keys.a11y_modalstate('10')
        self.assertEqual(run([{SHIFT: 1, 9: 1}, {}]), ['A11yTabPrev', 'A11y|keyup|9'])
        self.assertEqual(run([{9: 1}, {}]), ['A11yTabNext', 'A11y|keyup|9'])
        # A held key reads Shift as it is now.
        self.assertEqual(run([{SHIFT: 1, 9: 0x8000}, {}]), ['A11yTabNext', 'A11y|keyup|9'])

    def test_optional_numpad_and_retired_bindings(self):
        keys.a11y_modalstate('10')
        for vk in (0xBD, 0xDC, 0xBB, 0xBF, 0x2D, 0x69, 0x66):
            self.assertIsNone(keys._plain_message(vk))
        env.settings._stored['numpad_navigation'] = True
        self.assertEqual(keys._plain_message(0x66), keys._plain_message(0x28))
        self.assertIsNone(keys._plain_message(0x66, ctrl=True, alt=True))

    def test_needs_avoids_nvda_control_alt_n(self):
        self.assertNotIn(0x4E, keys.CHORDS)
        self.assertIsNone(keys._plain_message(0x4E, ctrl=True, alt=True))
        self.assertEqual(keys._plain_message(0x4E, ctrl=True, shift=True), 'A11yNeeds')
        keys._editing_active = True
        self.assertIsNone(keys._plain_message(0x4E, ctrl=True, shift=True))

    def run_samples(self, samples):
        clock = [0, 10.0]
        def sample(vk):
            return samples[clock[0]].get(vk, 0)
        def sleep(seconds):
            clock[0] += 1
            clock[1] += seconds
            if clock[0] >= len(samples):
                keys._running = False
        user32 = types.SimpleNamespace(GetAsyncKeyState=sample)
        keys._running = True
        with patch.object(ctypes, 'WinDLL', return_value=user32), \
                patch.object(keys, '_game_is_foreground', return_value=True), \
                patch.object(keys, '_altgr_pressed', return_value=False), \
                patch.object(keys, 'time', types.SimpleNamespace(monotonic=lambda: clock[1], sleep=sleep)):
            keys._loop()
        env.drain()
        # The lease and the settings heartbeat are periodic, not key output.
        return [m for m in env.messages if m != 'A11y|lease'
                and not m.startswith(('A11y|buildcontrols|', 'A11y|travellist|', 'A11y|scannermode|',
                                            'A11y|simplifiedmenus|'))]

    def test_hold_enter_activates_once_and_releases_native_guard(self):
        keys.a11y_modalstate('10')
        result = self.run_samples([{13: 0x8000}] * 120 + [{}])
        self.assertEqual(result, ['A11yActivate', 'A11y|keyup|13'])

    def test_complete_short_enter_tap_survives_between_polls(self):
        keys.a11y_modalstate('10')
        self.assertEqual(self.run_samples([{13: 1}, {}]),
                         ['A11yActivate', 'A11y|keyup|13'])

    def test_scanner_tap_with_held_modifiers_survives_hook_startup(self):
        with patch.object(keys, '_chord') as chord:
            result = self.run_samples([{0x11: 0x8000, 0x12: 0x8000, 13: 1},
                                       {0x11: 0x8000, 0x12: 0x8000}, {}])
        chord.assert_called_once_with('open')
        self.assertEqual(result, ['A11y|keyup|13'])

    def test_live_hook_release_overrides_stale_windows_tap(self):
        keys._hook_handle = 1
        keys._hook_last_event = 10.0
        keys._hook_state[13] = False
        with patch.object(keys, '_chord') as chord:
            self.run_samples([{0x11: 0x8000, 0x12: 0x8000, 13: 0x8001}, {}])
        chord.assert_not_called()

    def test_scanner_tap_cannot_reuse_released_modifiers(self):
        with patch.object(keys, '_chord') as chord:
            self.run_samples([{0x11: 0x8000, 0x12: 0x8000}, {0x48: 1}, {}])
        chord.assert_not_called()

    def test_world_escape_does_not_enqueue_a_modal_dismiss(self):
        self.assertEqual(self.run_samples([{27: 1}, {}]), ['A11y|keyup|27'])

    def test_modal_escape_asks_flash_to_validate_the_native_claim_once(self):
        keys.a11y_modalstate('10')
        self.assertEqual(self.run_samples([{27: 0x8000}] * 120 + [{}]),
                         ['A11yEscape', 'A11y|keyup|27'])

    def test_scanner_and_numpad_back_do_not_need_a_physical_escape_claim(self):
        keys.a11y_modalstate('10')
        env.settings._stored['numpad_navigation'] = True
        self.assertEqual(keys._plain_message(0x6E), 'A11yDismiss')
        keys._chord('back')
        env.drain()
        self.assertEqual(env.messages, ['A11yDismiss'])

    def test_shift_tab_reverses_once_even_if_shift_changes_while_held(self):
        keys.a11y_modalstate('11')
        self.assertEqual(self.run_samples([{9: 0x8000, 0x10: 0x8000}, {9: 0x8000}, {}]),
                         ['A11yTabPrev', 'A11y|keyup|9'])

    def test_disabled_scanner_does_not_disable_other_chords(self):
        env.settings._stored['scanner'] = False
        scanner = types.SimpleNamespace(on_key=Mock())
        with patch.dict(env.sys.modules, {'tyjokr_a11y_scanner': scanner}):
            keys._chord('next')
            keys._chord('mood')
        scanner.on_key.assert_not_called()
        env.drain()
        self.assertEqual(env.messages, ['A11yMood'])
        with patch.object(env.speech, 'repeat_last') as repeat:
            keys._chord('repeat')
            env.drain()
            repeat.assert_called_once_with()


class PhoneTests(unittest.TestCase):
    def setUp(self):
        phone._waiting.clear()
        env.messages.clear()
        self.first = types.SimpleNamespace(sim_id=11, first_name='Anna', last_name='Kowalska')
        self.second = types.SimpleNamespace(sim_id=22, first_name='Jan', last_name='Kowalski')
        self.client = types.SimpleNamespace(active_sim_info=self.first,
                                           selectable_sims=[self.first, self.second],
                                           set_active_sim_by_id=Mock(return_value=True))
        self.active = {101: object()}
        self.services = types.SimpleNamespace(
            ui_dialog_service=lambda: types.SimpleNamespace(_active_dialogs=self.active),
            client_manager=lambda: types.SimpleNamespace(get_first_client=lambda: self.client),
            sim_info_manager=lambda: types.SimpleNamespace(get=lambda sim_id: {11: self.first, 22: self.second}.get(sim_id)))
        self.module_patch = patch.dict(env.sys.modules, {'services': self.services})
        self.module_patch.start()
        self.speech_patch = patch.object(env.speech, 'speak')
        self.speech_patch.start()

    def tearDown(self):
        self.speech_patch.stop()
        self.module_patch.stop()

    def test_inactive_recipient_is_selected_before_opening_that_phone(self):
        phone._waiting.append((101, 22))
        self.assertTrue(phone.open_waiting())
        self.client.set_active_sim_by_id.assert_called_once_with(22)
        self.assertEqual(env.messages, ['A11y|phone|22'])

    def test_expired_and_non_household_calls_cannot_switch_sims(self):
        phone._waiting.extend([(100, 22), (101, 99)])
        self.assertFalse(phone.open_waiting())
        self.client.set_active_sim_by_id.assert_not_called()
        self.assertEqual(env.messages, [])

    def test_failed_sim_switch_never_opens_the_wrong_phone(self):
        self.client.set_active_sim_by_id.return_value = False
        phone._waiting.append((101, 22))
        self.assertFalse(phone.open_waiting())
        self.assertEqual(env.messages, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
