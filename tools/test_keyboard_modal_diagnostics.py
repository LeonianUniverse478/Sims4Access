"""Owner state arrives twice (a11y.modalstate and the context suffix) and
every routing decision that can silence a chord leaves one log line.

Scanner incident 2026-09-25 (v14l): after a pie closed, Ctrl+Alt chords
went nowhere and the log could not say why. Run with
py -3.7 tools/test_keyboard_modal_diagnostics.py.
"""
import types
import unittest
from unittest.mock import patch

import test_scanner_v5 as env
import tyjokr_a11y_narrator as narrator

keys = env.keys


class ModalDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.saved = dict(env.settings._stored)
        self.addCleanup(lambda: (env.settings._stored.clear(), env.settings._stored.update(self.saved)))
        keys._enabled = True
        keys._modal_active = keys._editing_active = False
        keys._input_epoch = 0
        keys._route_logged.clear()
        env.queue.clear()
        env.messages.clear()
        fence = patch.object(keys, 'fence_opening_input',
                             side_effect=lambda: setattr(keys, '_input_epoch', keys._input_epoch + 1))
        fence.start()
        self.addCleanup(fence.stop)
        self.log = patch.object(env.speech, 'log_line')
        self.lines = self.log.start()
        self.addCleanup(self.log.stop)

    def logged(self):
        return [call[0][0] for call in self.lines.call_args_list]

    def test_both_reports_of_one_change_apply_it_once(self):
        keys.a11y_modalstate('10')
        epoch = keys._input_epoch
        narrator.a11y_context_enc('widgets.Gameplay.PieMenu%3A%3APieMenuMain/instance383%3A10')
        self.assertEqual(keys._input_epoch, epoch)                   # no second fence
        keys.a11y_modalstate('00')
        narrator.a11y_context_enc('world%3A00')
        self.assertEqual(keys._input_epoch, epoch + 1)               # one close advance, not two
        self.assertEqual([l for l in self.logged() if l.startswith('keys: modal ')],
                         ['keys: modal 00->10 (modalstate)', 'keys: modal 10->00 (modalstate)'])

    def test_context_alone_clears_a_stranded_owner(self):
        keys.a11y_modalstate('10')
        import tyjokr_a11y_scanner as scanner
        scanner.note_menu_open()
        narrator.a11y_context_enc('world%3A00')                      # the modalstate post was lost
        self.assertFalse(keys._modal_active)
        self.assertFalse(scanner._menu_open)
        self.assertIn('keys: modal 10->00 (context)', self.logged())

    def test_rejected_payloads_are_logged_with_their_type(self):
        self.assertFalse(keys.a11y_modalstate('2'))
        self.assertFalse(keys.apply_modal_state(None, 'context'))
        self.assertIn("keys: modal state rejected str '2' (modalstate)", self.logged())
        self.assertIn('keys: modal state rejected NoneType None (context)', self.logged())
        self.assertFalse(keys._modal_active)

    def test_native_path_dropping_the_leading_zero_is_repaired(self):
        # In game, a11y.modalstate '00' arrived as '0' (log 2026-09-25 15:47).
        keys.a11y_modalstate('10')
        self.assertTrue(keys.a11y_modalstate('0'))
        self.assertFalse(keys._modal_active)
        self.assertTrue(keys.a11y_modalstate('1'))               # '01': editing, no modal owner
        self.assertFalse(keys._modal_active)
        self.assertTrue(keys._editing_active)
        self.assertFalse(any('rejected' in line for line in self.logged()))

    def test_a_number_payload_is_normalized(self):
        self.assertTrue(keys.apply_modal_state(10, 'modalstate'))
        self.assertTrue(keys._modal_active)
        self.assertTrue(keys.apply_modal_state(0, 'modalstate'))
        self.assertFalse(keys._modal_active)
        self.assertFalse(keys.apply_modal_state(True, 'modalstate'))   # bool is not a state

    def test_context_without_a_state_suffix_changes_nothing(self):
        keys.a11y_modalstate('10')
        narrator.a11y_context_enc('world')
        narrator.a11y_context_enc('world%3A2x')
        self.assertTrue(keys._modal_active)

    def test_modal_routing_is_logged_once_per_second(self):
        keys.a11y_modalstate('10')
        for _ in range(5):
            keys._chord('next')
        routed = [l for l in self.logged() if l == 'keys: chord next routed to the modal owner']
        self.assertEqual(len(routed), 1)

    def test_world_chord_handoff_is_logged_both_ways(self):
        keys._chord('next')
        self.assertIn('keys: chord next queued for world handling', self.logged())
        with patch.object(env.pump, 'post', return_value=False):
            keys._chord('prev')
        self.assertIn('keys: chord prev lost: simulation pump inactive', self.logged())

    def test_scanner_logs_flag_transitions_and_routes(self):
        import tyjokr_a11y_scanner as scanner
        scanner._route_logged.clear()
        scanner.a11y_menuclosed()
        self.lines.reset_mock()
        scanner.note_menu_open()
        scanner.note_menu_open()                    # no second line for the same state
        with patch.object(env.keys, '_send'):
            scanner.on_key('next', on_simulation_thread=True)
        scanner.a11y_menuclosed()
        scanner.a11y_menuclosed()
        with patch.object(scanner, '_dispatch'), patch.object(scanner, 'enabled', return_value=True):
            scanner.on_key('next', on_simulation_thread=True)
        self.assertEqual(self.logged(), ['scanner: menu flag set', 'scanner: chord next sent to the open menu',
                                         'scanner: menu flag cleared', 'scanner: chord next dispatched to the scanner'])

    def test_world_chord_drops_say_why(self):
        keys._world_chord('next', keys._input_epoch + 7)
        keys._editing_active = True
        keys._world_chord('next', keys._input_epoch)
        keys._editing_active = False
        keys._modal_active = True
        keys._world_chord('next', keys._input_epoch)
        lines = self.logged()
        self.assertIn('keys: chord next dropped: input epoch changed before the pump turn', lines)
        self.assertIn('keys: chord next dropped: a text field has focus', lines)
        self.assertIn('keys: chord next dropped: a modal owner opened before the pump turn', lines)


if __name__ == '__main__':
    unittest.main()
