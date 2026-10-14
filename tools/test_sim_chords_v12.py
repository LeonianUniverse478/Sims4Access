"""Ctrl+Alt+1..8 household Sim switch: routing and refusal rules, game stubbed.

Run with py -3.7 tools/test_sim_chords_v12.py.
"""
import sys
import types
import unittest
from unittest.mock import Mock, patch

import test_scanner_v5 as env

keys = env.keys


def _client(names):
    sims = [types.SimpleNamespace(sim_id=100 + i, first_name=n, last_name='Darden') for i, n in enumerate(names)]
    client = types.SimpleNamespace(selectable_sims=sims, active_sim_info=sims[0])
    return client, sims


class SimChordTests(unittest.TestCase):
    def setUp(self):
        env.settings._stored.clear()
        env.queue.clear()
        keys._enabled = True
        keys._modal_active = False
        keys._editing_active = False
        keys._input_epoch = 0
        self.client, self.sims = _client(['Ashton', 'Bea', 'Cal'])
        services = types.ModuleType('services')
        services.client_manager = lambda: types.SimpleNamespace(get_first_client=lambda: self.client)
        self.hub = types.ModuleType('tyjokr_a11y_hub')
        self.hub.select_sim = Mock(return_value=True)
        self.modules = patch.dict(sys.modules, {'services': services, 'tyjokr_a11y_hub': self.hub})
        self.modules.start()
        self.speak = patch.object(env.speech, 'speak')
        self.spoken = self.speak.start()

    def tearDown(self):
        self.speak.stop()
        self.modules.stop()

    def test_every_digit_chord_is_bound_and_named(self):
        for digit in range(1, 9):
            vk = 0x30 + digit
            self.assertEqual(keys.CHORDS[vk], ('sim%d' % digit, False))
            self.assertEqual(keys.CHORD_NAMES[vk], str(digit))

    def test_digit_chord_switches_on_the_simulation_thread(self):
        keys._chord('sim2')
        self.hub.select_sim.assert_not_called()      # key thread never touches the game
        env.drain()
        self.hub.select_sim.assert_called_once_with(101)

    def test_out_of_range_digit_speaks_unavailable(self):
        keys._chord('sim7')
        env.drain()
        self.hub.select_sim.assert_not_called()
        self.assertEqual(self.spoken.call_args[0][0], env.lang.t('sim unavailable'))

    def test_refused_while_typing(self):
        keys._editing_active = True
        keys._chord('sim1')
        self.assertEqual(env.queue, [])
        self.spoken.assert_not_called()

    def test_refused_behind_a_dialog_or_panel_with_speech(self):
        keys._modal_active = True
        keys._chord('sim1')
        self.assertEqual(env.queue, [])
        self.assertIn('Close the current panel or dialog', self.spoken.call_args[0][0])

    def test_switch_queued_before_a_new_surface_is_discarded(self):
        keys._chord('sim3')
        keys.fence_opening_input()                  # a dialog opened before the pump ran
        env.drain()
        self.hub.select_sim.assert_not_called()

    def test_modal_taken_after_queueing_blocks_the_switch(self):
        keys._chord('sim2')                          # queued from the world
        keys._modal_active = True                    # a dialog opened, same epoch
        env.drain()
        self.hub.select_sim.assert_not_called()

    def test_pump_refusal_speaks_no_lot_loaded(self):
        with patch.object(env.pump, 'post', return_value=False):
            keys._chord('sim1')
        self.hub.select_sim.assert_not_called()
        self.assertEqual(self.spoken.call_args[0][0], env.lang.t('no lot loaded'))

    def test_lookup_exception_speaks_unavailable(self):
        broken = types.ModuleType('services')
        broken.client_manager = Mock(side_effect=RuntimeError('no zone'))
        with patch.dict(sys.modules, {'services': broken}):
            keys._chord('sim1')
            env.drain()
        self.hub.select_sim.assert_not_called()
        self.assertEqual(self.spoken.call_args[0][0], env.lang.t('sim unavailable'))

    def test_no_client_speaks_unavailable(self):
        self.client = None
        keys._chord('sim1')
        env.drain()
        self.hub.select_sim.assert_not_called()
        self.assertEqual(self.spoken.call_args[0][0], env.lang.t('sim unavailable'))


if __name__ == '__main__':
    unittest.main()
