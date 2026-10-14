"""Modal chord navigation belongs to the owner it was sampled under.

A queued Ctrl+Alt Next/Previous must not reach Flash after its dialog or pie
closed (it would walk the HUD behind it: scanner incident 2026-09-25), and
must still arrive while that owner stays open. World chords reach the
scanner on the same pump turn (no second crossing).
Run with py -3.7 tools/test_keyboard_modal_owner.py.
"""
import types
import unittest
from unittest.mock import patch

import test_scanner_v5 as env

keys = env.keys


class ModalOwnerTests(unittest.TestCase):
    def setUp(self):
        self.saved = dict(env.settings._stored)
        self.addCleanup(lambda: (env.settings._stored.clear(), env.settings._stored.update(self.saved)))
        keys._enabled = True
        keys._editing_active = False
        keys._modal_active = False
        keys._input_epoch = 0
        env.queue.clear()
        env.messages.clear()
        self.fence = patch.object(keys, 'fence_opening_input',
                                  side_effect=lambda: setattr(keys, '_input_epoch', keys._input_epoch + 1))
        self.fence.start()
        self.addCleanup(self.fence.stop)
        keys.a11y_modalstate('10')           # a dialog is open

    def test_navigation_reaches_an_owner_that_stays_open(self):
        keys._chord('next')
        keys._chord('prev')
        env.drain()
        self.assertEqual(env.messages, ['A11yNavNext', 'A11yNavPrev'])

    def test_navigation_queued_before_the_owner_closed_is_dropped(self):
        keys._chord('next')
        keys._chord('open')
        keys.a11y_modalstate('00')           # the dialog closed before the pump turn
        env.drain()
        self.assertEqual(env.messages, [])

    def test_only_a_close_advances_the_epoch(self):
        epoch = keys._input_epoch
        keys.a11y_modalstate('10')           # still the same owner state
        self.assertEqual(keys._input_epoch, epoch)
        # (Leaving a text field also fences, by the existing editing-ended
        # rule; that path is covered in test_keyboard_v10.)
        keys.a11y_modalstate('00')
        self.assertEqual(keys._input_epoch, epoch + 1)
        keys.a11y_modalstate('00')
        self.assertEqual(keys._input_epoch, epoch + 1)

    def test_navigation_after_a_new_owner_opens_arrives(self):
        keys.a11y_modalstate('00')
        keys.a11y_modalstate('10')           # a new dialog (opening fence)
        keys._chord('next')
        env.drain()
        self.assertEqual(env.messages, ['A11yNavNext'])

    def test_repeat_stays_a_speech_action(self):
        with patch.object(env.speech, 'repeat_last') as repeat:
            keys._chord('repeat')
        repeat.assert_called_once_with()
        self.assertEqual(env.queue, [])

    def test_world_chord_reaches_the_scanner_on_the_same_pump_turn(self):
        keys.a11y_modalstate('00')
        scanner = types.SimpleNamespace(on_key=unittest.mock.Mock(), a11y_menuclosed=lambda: True)
        with patch.dict(env.sys.modules, {'tyjokr_a11y_scanner': scanner}):
            keys._world_chord('next', keys._input_epoch)
        scanner.on_key.assert_called_once_with('next', on_simulation_thread=True)


if __name__ == '__main__':
    unittest.main()
