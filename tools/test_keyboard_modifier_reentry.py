"""A modifier change cannot turn an already-held key into a new shortcut.

Exercise the real poll loop with stale Windows H state, as can remain after
a swallowed key release, and preserve deliberate H/Space/P shortcut presses.
"""
import unittest
from unittest.mock import patch

import test_keyboard_stale_release as stale

keys = stale.keys
H, SPACE, P, DOWN, CTRL, ALT = 0x48, 0x20, 0x50, 0x28, 0x11, 0x12
MODS = {CTRL: 0x8000, ALT: 0x8000}


class ModifierReentryTests(unittest.TestCase):
    setUp = stale.StaleReleaseTests.setUp
    run_loop = stale.StaleReleaseTests.run_loop

    def chords(self, frames):
        calls = []
        with patch.object(keys, '_chord', side_effect=calls.append):
            self.run_loop(frames)
        return calls

    def test_modifiers_alone_do_nothing(self):
        self.assertEqual(self.chords([{}, MODS, MODS, {}]), [])

    def test_scanner_mode_defaults_off_but_preserves_explicit_choice(self):
        stale.env.settings._stored.pop('scanner_mode', None)
        self.assertIs(stale.env.settings.get('scanner_mode'), False)
        stale.env.settings._stored['scanner_mode'] = True
        self.assertIs(stale.env.settings.get('scanner_mode'), True)

    def test_ctrl_alt_alone_does_not_promote_old_h(self):
        frames = [{H: 0x8000}] * 3 + [{CTRL: 0x8000, ALT: 0x8000, H: 0x8000}] * 3
        self.assertEqual(self.chords(frames), [])

    def test_ctrl_alt_space_with_old_h_only_toggles_scanner(self):
        self.assertEqual(self.chords([{H: 0x8000},
            {CTRL: 0x8000, ALT: 0x8000, H: 0x8000, SPACE: 0x8001}, {}]),
            ['scannermode'])

    def test_phone_with_old_h_does_not_open_hub(self):
        self.assertEqual(self.chords([{H: 0x8000},
            {CTRL: 0x8000, ALT: 0x8000, H: 0x8000, P: 0x8001}, {}]), ['phone'])

    def test_repressing_modifiers_does_not_reopen_hub(self):
        self.assertEqual(self.chords([
            {CTRL: 0x8000, ALT: 0x8000, H: 0x8001},
            {H: 0x8000}, {CTRL: 0x8000, ALT: 0x8000, H: 0x8000}, {}]), ['help'])

    def test_released_then_fresh_h_still_works(self):
        self.assertEqual(self.chords([{H: 0x8000}, MODS,
            {CTRL: 0x8000, ALT: 0x8000, H: 0x8001}, {}]), ['help'])

    def test_fresh_h_press_bit_recovers_from_old_held_state(self):
        self.assertEqual(self.chords([{H: 0x8000},
            {CTRL: 0x8000, ALT: 0x8000, H: 0x8001}, {}]), ['help'])

    def test_fresh_hook_press_recovers_from_old_held_state(self):
        def fresh_hook(vk, poll):
            if vk == H and poll == 1:
                keys._hook_handle = 1
                keys._hook_last_event = 10.01
                keys._hook_state[H] = False
                keys._hook_edges.extend(((H, True, 10.01), (H, False, 10.01)))
        calls = []
        with patch.object(keys, '_chord', side_effect=calls.append):
            self.run_loop([{H: 0x8000},
                {CTRL: 0x8000, ALT: 0x8000, H: 0x8000}, {}], on_read=fresh_hook)
        self.assertEqual(calls, ['help'])

    def test_modifier_reentry_does_not_restart_arrow_repeats(self):
        frames = [{CTRL: 0x8000, ALT: 0x8000, DOWN: 0x8001}]
        frames += [{DOWN: 0x8000}] * 3
        frames += [{CTRL: 0x8000, ALT: 0x8000, DOWN: 0x8000}] * 70
        self.assertEqual(self.chords(frames), ['next'])

    def test_focus_return_does_not_replay_held_shortcuts(self):
        for vk, intent in ((H, 'help'), (SPACE, 'scannermode'), (P, 'phone'),
                           (0x42, 'buildplace'), (DOWN, 'next')):
            def lose_focus(key, poll):
                if key == vk and poll == 0:
                    answers = iter([False])
                    keys._game_is_foreground.side_effect = lambda *a: next(answers, True)
            frames = [{CTRL: 0x8000, ALT: 0x8000, vk: 0x8001}, {}]
            frames += [{CTRL: 0x8000, ALT: 0x8000, vk: 0x8000}] * 70
            frames += [MODS, {CTRL: 0x8000, ALT: 0x8000, vk: 0x8001}, {}]
            calls = []
            with patch.object(keys, '_chord', side_effect=calls.append):
                self.run_loop(frames, on_read=lose_focus)
            self.assertEqual(calls, [intent, intent], hex(vk))

    def test_background_tap_is_not_replayed_on_return(self):
        def lose_focus(vk, poll):
            if vk == H and poll == 0:
                answers = iter([False])
                keys._game_is_foreground.side_effect = lambda *a: next(answers, True)
        calls = []
        with patch.object(keys, '_chord', side_effect=calls.append):
            self.run_loop([{}, {}, {CTRL: 0x8000, ALT: 0x8000, H: 1}, {}], on_read=lose_focus)
        self.assertEqual(calls, [])

    def test_enter_held_across_focus_return_does_not_activate_twice(self):
        def lose_focus(vk, poll):
            if vk == H and poll == 0:
                answers = iter([False])
                keys._game_is_foreground.side_effect = lambda *a: next(answers, True)
        messages = self.run_loop([{13: 0x8001}, {}, {13: 0x8000},
                                  {13: 0x8000}, {}, {13: 0x8001}, {}], on_read=lose_focus)
        self.assertEqual(messages.count('A11yActivate'), 2)

    def test_hook_repeat_of_a_focus_blocked_key_does_not_open_hub(self):
        def focus_and_hook(vk, poll):
            if vk == H and poll == 0:
                answers = iter([False])
                keys._game_is_foreground.side_effect = lambda *a: next(answers, True)
            if vk == H and poll == 3:
                keys._hook_handle = 1
                keys._hook_last_event = 10.1
                keys._hook_state[H] = True
                keys._hook_edges.append((H, True, 10.1))
        calls = []
        with patch.object(keys, '_chord', side_effect=calls.append):
            self.run_loop([{}, {}, {CTRL: 0x8000, ALT: 0x8000, H: 0x8000},
                {CTRL: 0x8000, ALT: 0x8000, H: 0x8000}], on_read=focus_and_hook)
        self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
