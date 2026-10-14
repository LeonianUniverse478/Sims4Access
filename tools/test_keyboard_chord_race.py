"""Fast chords: the swallow hook installs only once Ctrl+Alt are held, so a
chord key pressed a moment after Alt can reach Windows before the hook
exists. The hook then consumes that key's release and drains its press bit.
If the poller had not read the press yet, the whole chord vanished (live
2026-09-26 22:10:01: Ctrl+Alt+B with B 30 ms after Alt installed and removed
the hook and did nothing; with a 400 ms lead it worked every time).
Actual hook callback and polling loop, mocked Windows.
Run with py -3.7 tools/test_keyboard_chord_race.py.
"""
import ctypes
import types
import unittest
from unittest.mock import patch

import test_keyboard_stale_release as stale

keys = stale.keys
B, DOWN, CTRL, ALT = 0x42, 0x28, 0x11, 0x12
HELD = {CTRL: 0x8000, ALT: 0x8000}


def held(vk, state):
    """One poll frame: Ctrl+Alt held and vk in state."""
    frame = dict(HELD)
    frame[vk] = state
    return frame


class OsKeys(object):
    """Windows' async key state. A read returns the high (held) bit and the
    low (pressed since the last read) bit, then clears the low bit. A key-up
    the hook consumes never reaches it, so the high bit stays set."""

    def __init__(self, *held):
        self.state = {vk: [True, False] for vk in held}

    def press(self, vk):
        self.state[vk] = [True, True]

    def read(self, vk):
        high, low = self.state.get(vk, [False, False])
        if vk in self.state:
            self.state[vk][1] = False
        return (0x8000 if high else 0) | (1 if low else 0)


class ChordRaceTests(unittest.TestCase):
    setUp = stale.StaleReleaseTests.setUp
    run_loop = stale.StaleReleaseTests.run_loop

    def hook(self, os_keys, vk, wparam):
        """Deliver one key event to the real hook callback (hook installed)."""
        user32 = types.SimpleNamespace(GetAsyncKeyState=os_keys.read, CallNextHookEx=lambda *a: 0)
        with patch.object(keys, '_game_is_foreground', return_value=True), \
                patch.object(keys, '_altgr_pressed', return_value=False), \
                patch.object(keys, '_swallow_enabled', return_value=True), \
                patch.object(keys, 'time', types.SimpleNamespace(monotonic=lambda: 10.0)):
            callback = keys._hook_callback_factory(user32, types.SimpleNamespace())
            code = ctypes.c_ulong(vk)
            return callback(0, wparam, ctypes.addressof(code))

    def tracing(self):
        """The trace runs only while the diagnostic log is on."""
        item = patch.object(keys.speech, 'log_enabled', True)
        item.start()
        self.addCleanup(item.stop)

    def install_hook(self):
        keys._hook_state.clear()          # as _hook_loop's install() does
        keys._hook_handle = 1

    def chords_from(self, frames, on_read=None):
        keys._modal_active = False
        keys._hook_last_event = 10.0
        chords = []
        with patch.object(keys, '_chord', side_effect=chords.append):
            self.run_loop(frames, on_read=on_read)
        return chords

    def test_press_that_beat_the_hook_install_fires_once(self):
        # The live failure: B goes down while Ctrl+Alt are held but before
        # the hook exists, the hook installs, then consumes B's release
        # before the poller reads B. The press bit is drained, B's stale
        # high bit is masked, and the hook never saw B go down.
        os_keys = OsKeys(CTRL, ALT)
        os_keys.press(B)
        self.install_hook()
        self.assertEqual(self.hook(os_keys, B, keys.WM_KEYUP), 1)     # consumed
        self.assertEqual(os_keys.read(B), 0x8000)                      # stale, drained
        frames = [held(B, 0x8000)] * 3 + [{B: 0x8000}] * 60
        self.assertEqual(self.chords_from(frames), ['buildplace'])
        self.assertIn(B, keys._swallowed_up)                           # stale bit still masked

    def test_press_the_poller_already_read_is_not_repeated(self):
        # The poller reads B = 0x8001 and fires, then the hook installs and
        # consumes B's release. The press bit is already spent: one chord.
        os_keys = OsKeys(CTRL, ALT)
        os_keys.press(B)

        def hook_after_first_read(vk, poll):
            if vk == B and poll == 0:
                os_keys.read(B)           # the poller's own read spends the press bit
                self.install_hook()
                self.hook(os_keys, B, keys.WM_KEYUP)
        frames = [held(B, 0x8001)] + [held(B, 0x8000)] * 3 + [{B: 0x8000}] * 60
        self.assertEqual(self.chords_from(frames, on_read=hook_after_first_read), ['buildplace'])

    def test_press_the_hook_saw_fires_once(self):
        # Normal case (a human-speed lead): the hook sees both edges and
        # Windows never sees B at all.
        os_keys = OsKeys(CTRL, ALT)
        self.install_hook()
        self.assertEqual(self.hook(os_keys, B, keys.WM_KEYDOWN), 1)
        self.assertEqual(self.hook(os_keys, B, keys.WM_KEYUP), 1)
        frames = [HELD] * 3 + [{}] * 20
        self.assertEqual(self.chords_from(frames), ['buildplace'])

    def test_unread_press_is_a_tap_never_a_hold(self):
        # A press nobody read, released inside the chord, counts once. With
        # Ctrl+Alt still held for 1.2 s (longer than the hook stays trusted)
        # the stale high bit must not become a held, repeating scanner key.
        os_keys = OsKeys(CTRL, ALT)
        os_keys.press(DOWN)
        self.install_hook()
        self.assertEqual(self.hook(os_keys, DOWN, keys.WM_KEYUP), 1)
        frames = [held(DOWN, 0x8000)] * 120 + [{DOWN: 0x8000}] * 10
        self.assertEqual(self.chords_from(frames), ['next'])

    def test_press_both_the_hook_and_windows_saw_fires_once(self):
        # A slow callback (GIL) can time out: Windows keeps the key-down
        # and the late callback still reports it. The poller reads the press
        # bit and pops the hook's edge in the same poll: one chord, not two.
        os_keys = OsKeys(CTRL, ALT)
        os_keys.press(B)
        self.install_hook()

        def late_callback(vk, poll):
            if vk == B and poll == 0:
                self.hook(os_keys, B, keys.WM_KEYDOWN)
            if vk == B and poll == 2:
                self.hook(os_keys, B, keys.WM_KEYUP)
        frames = [held(B, 0x8001)] + [held(B, 0x8000)] * 3 + [{B: 0x8000}] * 30
        self.assertEqual(self.chords_from(frames, on_read=late_callback), ['buildplace'])

    def test_every_fire_is_logged_with_its_source(self):
        # The route line is throttled to one per second; the fire line is
        # not, so a double or a lost press shows in the log.
        lines = []
        with patch.object(keys.speech, 'log_line', side_effect=lines.append):
            os_keys = OsKeys(CTRL, ALT)
            self.install_hook()
            self.hook(os_keys, B, keys.WM_KEYDOWN)
            self.hook(os_keys, B, keys.WM_KEYUP)
            self.chords_from([HELD] * 3 + [{}] * 5)
            keys._hook_handle = None
            keys._hook_state.clear()
            self.chords_from([held(B, 0x8001)] + [HELD] * 3 + [{}] * 5)
        fired = [line for line in lines if ' fired ' in line]
        self.assertEqual(fired, ['keys: chord buildplace fired (edge)', 'keys: chord buildplace fired (held)'])

    def test_focus_loss_with_a_held_chord_key_is_logged(self):
        # Diagnostic only: losing focus for one poll while a chord key is
        # held is logged, so a later double toggle can be traced to it.
        lines = []
        os_keys = OsKeys(CTRL, ALT)
        self.install_hook()
        self.hook(os_keys, B, keys.WM_KEYDOWN)            # B held, seen by the hook

        def flicker(vk, poll):
            if vk == B and poll == 3:
                answers = iter([False])
                keys._game_is_foreground.side_effect = lambda *a: next(answers, True)
        with patch.object(keys.speech, 'log_line', side_effect=lines.append):
            self.chords_from([HELD] * 12, on_read=flicker)
        self.assertIn('keys: focus left the game with chord key B held', lines)
        self.assertEqual(sum(1 for line in lines if 'focus left' in line), 1)

    def test_hook_events_are_traced_without_repeats(self):
        self.tracing()
        lines = []
        os_keys = OsKeys(CTRL, ALT)
        self.install_hook()
        self.hook(os_keys, B, keys.WM_KEYDOWN)
        self.hook(os_keys, B, keys.WM_KEYDOWN)            # auto-repeat: not traced
        self.hook(os_keys, B, keys.WM_KEYUP)
        with patch.object(keys.speech, 'log_line', side_effect=lines.append):
            self.chords_from([HELD] * 2 + [{}] * 3)
        traced = [line for line in lines if 'trace hook' in line]
        self.assertEqual(traced, ['keys: trace hook B down (down seen 0) gate 1 late -1 ms',
                                  'keys: trace hook B up (down seen 1) gate 1 late -1 ms'])

    def test_a_press_read_with_modifiers_up_near_a_chord_is_traced(self):
        self.tracing()
        # Diagnostic only; the press still does not count (see
        # test_keyboard_v7: a tap cannot reuse released modifiers).
        lines = []
        with patch.object(keys.speech, 'log_line', side_effect=lines.append):
            chords = self.chords_from([HELD, {B: 1}, {}])
        self.assertEqual(chords, [])
        self.assertIn('keys: trace B press read with Ctrl+Alt up (held after the read: 0)', lines)
        # Modifiers read up, then held right after the key sample.
        lines.clear()
        frames = [{}] * 60 + [{B: 1}, {}]

        def alt_after_b(vk, poll):
            if vk == B and poll == 60:
                frames[60] = {B: 1, CTRL: 0x8000, ALT: 0x8000}
        with patch.object(keys.speech, 'log_line', side_effect=lines.append):
            chords = self.chords_from(frames, on_read=alt_after_b)
        self.assertEqual(chords, [])
        self.assertIn('keys: trace B press read with Ctrl+Alt up (held after the read: 1)', lines)

    def test_no_trace_work_while_the_log_is_off(self):
        # Codex 03:55: the diagnostic must cost nothing in release, where the
        # log is off: no deque entries, no second modifier read.
        os_keys = OsKeys(CTRL, ALT)
        self.install_hook()
        with patch.object(keys.speech, 'log_enabled', False):
            self.hook(os_keys, B, keys.WM_KEYDOWN)
            self.hook(os_keys, B, keys.WM_KEYUP)
            self.assertEqual(len(keys._hook_trace), 0)
            reads = []

            def count(vk, poll):
                if vk == CTRL:
                    reads.append(poll)
            self.chords_from([HELD] * 3 + [{}] * 2, on_read=count)
        self.assertEqual(len(reads), len(set(reads)))       # one Ctrl read per poll

    def test_ordinary_typing_is_not_traced(self):
        lines = []
        with patch.object(keys.speech, 'log_line', side_effect=lines.append):
            self.chords_from([HELD] + [{}] * 60 + [{B: 1}, {}])     # 0.6 s later
        self.assertFalse([line for line in lines if 'press read' in line])

    def test_plain_keys_just_after_release_stay_plain(self):
        # Codex 03:45: B, X and Enter pressed right after Ctrl+Alt are
        # released must never become chords (a stray Enter would place and
        # charge). One poll after release, then two polls after release.
        for key in (B, 0x58, 0x0D):
            for gap in (0, 1):
                chords = self.chords_from([HELD] + [{}] * gap + [{key: 1}, {}])
                self.assertEqual(chords, [], (hex(key), gap))

    def test_typing_in_a_text_field_is_never_traced(self):
        lines = []
        keys._editing_active = True
        self.addCleanup(setattr, keys, '_editing_active', False)
        with patch.object(keys.speech, 'log_line', side_effect=lines.append):
            self.chords_from([HELD, {B: 1}, {}])
        self.assertFalse([line for line in lines if 'press read' in line])

    def test_key_reader_keeps_the_gil_only_for_a_real_user32(self):
        # Live 2026-09-26 trace: 2 of 10 fast chords lost to a sample that
        # read Ctrl+Alt up, then spent B's press after Alt went down.
        reader = keys._key_reader(ctypes.WinDLL('user32'))
        self.assertTrue(reader._flags_ & keys.ctypes._FUNCFLAG_PYTHONAPI)   # PyDLL: GIL kept
        self.assertIs(reader.restype, ctypes.c_short)
        self.assertEqual(reader.argtypes, [ctypes.c_int])
        mock_read = lambda vk: 0
        self.assertIs(keys._key_reader(types.SimpleNamespace(GetAsyncKeyState=mock_read)), mock_read)

    def test_sample_reads_modifiers_then_keys_with_nothing_between(self):
        order = []
        real_snapshot = keys._swallowed_snapshot

        def snapshot():
            order.append('snapshot')
            return real_snapshot()
        with patch.object(keys, '_swallowed_snapshot', side_effect=snapshot):
            self.chords_from([HELD, {}], on_read=lambda vk, poll: order.append((poll, vk)))
        first = [entry for entry in order if entry == 'snapshot' or entry[0] == 0]
        self.assertEqual(first[:4], ['snapshot', (0, ALT), (0, CTRL), (0, 0x10)])
        # The burst is every polled key once (it grew past 40 with the Build
        # cursor keys, 2026-09-30); read up to the next sample's snapshot.
        burst = first[4:]
        if 'snapshot' in burst:
            burst = burst[:burst.index('snapshot')]
        polled = [entry[1] for entry in burst]
        self.assertGreaterEqual(len(polled), len(keys.CHORDS))
        self.assertEqual(len(polled), len(set(polled)))      # each key read once
        self.assertNotIn(ALT, polled)          # no modifier re-read inside the key burst
        self.assertTrue(set(keys.CHORDS) <= set(polled))     # every chord key in the same burst

    def test_two_fast_chords_in_a_row_both_fire(self):
        # The live sequence: the first fast chord leaves B's high bit stale
        # (its release was consumed); the second fast chord must still fire.
        os_keys = OsKeys(CTRL, ALT)
        os_keys.press(B)
        self.install_hook()
        self.hook(os_keys, B, keys.WM_KEYUP)
        first = self.chords_from([held(B, 0x8000)] * 3 + [{B: 0x8000}] * 30)
        keys._hook_handle = None                      # Ctrl+Alt released: hook removed
        keys._hook_state.clear()
        os_keys.press(B)                              # second chord, again before the install
        self.install_hook()
        self.hook(os_keys, B, keys.WM_KEYUP)
        second = self.chords_from([held(B, 0x8000)] * 3 + [{B: 0x8000}] * 30)
        self.assertEqual((first, second), (['buildplace'], ['buildplace']))


if __name__ == '__main__':
    unittest.main()
