"""Swallowed key-ups: the scanner hook consumes chord key-ups, so Windows
keeps the key's async high bit set after the physical release. The poller
must not read that as a held key (scanner incident 2026-09-25: Down kept
repeating after every key was released). Real presses, holds and releases
must behave as before. Actual polling loop and hook callback, mocked Windows.
Run with py -3.7 tools/test_keyboard_stale_release.py.
"""
import ctypes
import types
import unittest
from unittest.mock import patch

import test_scanner_v5 as env

keys = env.keys
DOWN, CTRL, ALT = 0x28, 0x11, 0x12


class StaleReleaseTests(unittest.TestCase):
    def setUp(self):
        self.saved = dict(env.settings._stored)
        self.addCleanup(lambda: (env.settings._stored.clear(), env.settings._stored.update(self.saved)))
        keys._enabled = True
        keys._modal_active = True
        keys._editing_active = False
        keys._opening_keys.clear()
        keys._hook_edges.clear()
        keys._hook_state.clear()
        keys._swallowed_up.clear()
        keys._hook_handle = None
        keys._input_epoch = 0
        self.addCleanup(keys._swallowed_up.clear)
        self.addCleanup(keys._hook_state.clear)
        self.addCleanup(setattr, keys, '_hook_handle', None)

    def run_loop(self, frames, start=10.0, on_read=None):
        """frames: list of {vk: state} per poll; returns the sent messages.
        on_read(vk, poll) runs right after a key is read (a hook event that
        lands between the poller's read and its mask)."""
        clock = {'n': 0, 't': start}
        sent = []

        def sample(vk):
            state = frames[min(clock['n'], len(frames) - 1)].get(vk, 0)
            if on_read is not None:
                on_read(vk, clock['n'])
            return state

        def sleep(seconds):
            clock['n'] += 1
            clock['t'] += seconds
            if clock['n'] >= len(frames):
                keys._running = False

        keys._running = True
        with patch.object(keys.ctypes, 'WinDLL', return_value=types.SimpleNamespace(GetAsyncKeyState=sample)), \
                patch.object(keys, '_game_is_foreground', return_value=True), \
                patch.object(keys, '_altgr_pressed', return_value=False), \
                patch.object(keys, '_send', side_effect=lambda m: sent.append((round(clock['t'] - start, 3), m))), \
                patch.object(keys, 'time', types.SimpleNamespace(monotonic=lambda: clock['t'], sleep=sleep)):
            keys._loop()
        return [m for _, m in sent if m not in ('A11y|lease',)]

    def arrows(self, messages):
        return [m for m in messages if m == 'A11yArrowDown']

    def swallow_up_through_real_callback(self, vk=DOWN):
        """Drive the real hook callback: Ctrl+Alt held, key-up consumed."""
        user32 = types.SimpleNamespace(
            GetAsyncKeyState=lambda k: 0x8000 if k in (CTRL, ALT) else 0,
            CallNextHookEx=lambda *a: 0)
        with patch.object(keys, '_game_is_foreground', return_value=True), \
                patch.object(keys, '_altgr_pressed', return_value=False), \
                patch.object(keys, '_swallow_enabled', return_value=True):
            callback = keys._hook_callback_factory(user32, types.SimpleNamespace())
            code = ctypes.c_ulong(vk)
            consumed = callback(0, keys.WM_KEYUP, ctypes.addressof(code))
        return consumed

    def test_incident_state_emits_no_phantom_repeat(self):
        # The incident: the hook consumed Down's key-up while Ctrl+Alt were
        # held, then every key was released and Windows still reports Down
        # held. Before the fix: 12 actions in 1.2 s (Codex's reproduction).
        self.assertEqual(self.swallow_up_through_real_callback(), 1)
        keys._hook_handle, keys._hook_last_event = 1, 10.0
        messages = self.run_loop([{DOWN: 0x8000}] * 120)
        self.assertEqual(self.arrows(messages), [])

    def test_swallowed_key_up_survives_hook_removal(self):
        self.assertEqual(self.swallow_up_through_real_callback(), 1)   # consumed
        self.assertIn(DOWN, keys._swallowed_up)
        keys._hook_state.clear()                                         # hook removed
        messages = self.run_loop([{DOWN: 0x8000}] * 120)
        self.assertEqual(self.arrows(messages), [])
        self.assertIn(DOWN, keys._swallowed_up)                          # still stale

    def test_new_press_after_stale_release_fires_once_then_holds_normally(self):
        keys._record_swallowed_up(DOWN)
        frames = [{DOWN: 0x8000}] * 20 + [{DOWN: 0x8001}] + [{DOWN: 0x8000}] * 60 + [{}]
        messages = self.run_loop(frames)
        arrows = self.arrows(messages)
        self.assertGreaterEqual(len(arrows), 2)       # the press, then the OS-style repeat of a real hold
        self.assertNotIn(DOWN, keys._swallowed_up)
        self.assertIn('A11y|keyup|40', messages)       # the real release still frees the native guard

    def test_real_release_clears_the_record(self):
        keys._record_swallowed_up(DOWN)
        messages = self.run_loop([{DOWN: 0x8000}] * 5 + [{}] * 5 + [{DOWN: 1}] + [{}] * 3)
        self.assertNotIn(DOWN, keys._swallowed_up)
        self.assertEqual(self.arrows(messages), ['A11yArrowDown'])   # only the later genuine tap

    def test_key_down_seen_by_the_hook_clears_the_record(self):
        keys._record_swallowed_up(DOWN)
        user32 = types.SimpleNamespace(GetAsyncKeyState=lambda k: 0, CallNextHookEx=lambda *a: 0)
        callback = keys._hook_callback_factory(user32, types.SimpleNamespace())
        code = ctypes.c_ulong(DOWN)
        callback(0, keys.WM_KEYDOWN, ctypes.addressof(code))
        self.assertNotIn(DOWN, keys._swallowed_up)

    def test_chord_path_ignores_the_stale_bit_after_the_hook_goes_quiet(self):
        # Ctrl+Alt still held, hook installed but silent for over a second,
        # Down's key-up was consumed earlier: no repeating scanner move.
        keys._modal_active = False
        keys._hook_handle, keys._hook_last_event = 1, 0.0
        keys._record_swallowed_up(DOWN)
        chords = []
        with patch.object(keys, '_chord', side_effect=chords.append):
            self.run_loop([{DOWN: 0x8000, CTRL: 0x8000, ALT: 0x8000}] * 120)
        self.assertEqual(chords, [])

    def test_consumed_up_drains_the_old_press_bit(self):
        # Windows model: a read returns the high bit and the "pressed since
        # the last read" low bit, then clears the low bit. Down is pressed
        # (no chord), Ctrl+Alt follow, Down is released inside the chord
        # before the poller read the press: the hook must drain that bit or
        # the first poll reads 0x8001 as a new press and trusts the stale
        # high bit from then on (Codex review 13:04).
        os_state = {DOWN: [True, True], CTRL: [True, False], ALT: [True, False]}

        def read(vk):
            high, low = os_state.get(vk, [False, False])
            if vk in os_state:
                os_state[vk][1] = False
            return (0x8000 if high else 0) | (1 if low else 0)

        user32 = types.SimpleNamespace(GetAsyncKeyState=read, CallNextHookEx=lambda *a: 0)
        with patch.object(keys, '_game_is_foreground', return_value=True), \
                patch.object(keys, '_altgr_pressed', return_value=False), \
                patch.object(keys, '_swallow_enabled', return_value=True):
            callback = keys._hook_callback_factory(user32, types.SimpleNamespace())
            code = ctypes.c_ulong(DOWN)
            self.assertEqual(callback(0, keys.WM_KEYUP, ctypes.addressof(code)), 1)
        os_state[CTRL] = [False, False]
        os_state[ALT] = [False, False]       # every key released; Down's high bit is stale
        frames = [{DOWN: read(DOWN)} for _ in range(60)]
        self.assertEqual(frames[0][DOWN], 0x8000)
        self.assertEqual(self.arrows(self.run_loop(frames)), [])

    def test_release_recorded_after_a_press_read_keeps_its_record(self):
        # Codex race (13:10:17): the poller reads Down = 0x8001 (a real
        # press), then the hook consumes Down's key-up before the mask runs.
        # The press counts once; the new record must survive, so the stale
        # high bit that follows is never trusted.
        def hook_after_first_read(vk, poll):
            if vk == DOWN and poll == 0:
                keys._record_swallowed_up(DOWN)
        frames = [{DOWN: 0x8001}] + [{DOWN: 0x8000}] * 100
        messages = self.run_loop(frames, on_read=hook_after_first_read)
        self.assertEqual(self.arrows(messages), ['A11yArrowDown'])
        self.assertIn('A11y|keyup|40', messages)
        self.assertIn(DOWN, keys._swallowed_up)

    def test_release_recorded_between_snapshot_and_read_masks_at_once(self):
        # A real hold, then the key-up is consumed while that very poll is
        # reading: the stale high bit of that read must not extend the hold.
        def hook_during_read(vk, poll):
            if vk == DOWN and poll == 30:
                keys._record_swallowed_up(DOWN)
        frames = [{DOWN: 0x8001}] + [{DOWN: 0x8000}] * 100
        messages = self.run_loop(frames, on_read=hook_during_read)
        arrows = self.arrows(messages)
        held_until_release = len(arrows)
        self.assertGreaterEqual(held_until_release, 1)
        release_index = messages.index('A11y|keyup|40')
        self.assertEqual(self.arrows(messages[release_index:]), [])   # nothing after the release

    def test_a_dropped_hook_does_not_mask_real_input(self):
        # Windows can drop a slow hook: _hook_state then goes stale and the
        # polled state must stay authoritative (no consumed key-up recorded).
        keys._hook_handle, keys._hook_last_event = 1, 0.0
        keys._hook_state[DOWN] = False
        messages = self.run_loop([{DOWN: 0x8001}] + [{DOWN: 0x8000}] * 10 + [{}])
        self.assertEqual(self.arrows(messages)[:1], ['A11yArrowDown'])

    def test_ordinary_hold_without_any_hook_history_still_repeats(self):
        messages = self.run_loop([{DOWN: 0x8001}] + [{DOWN: 0x8000}] * 80 + [{}])
        self.assertGreater(len(self.arrows(messages)), 5)


if __name__ == '__main__':
    unittest.main()
