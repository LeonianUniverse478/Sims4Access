"""M key handshake, Python side: session epoch, heartbeat, request lifetime, cancel.

Run with py -3.7 tools/test_travel_m_v14c.py. Source bodies only.
"""
import unittest
from unittest.mock import patch

import test_travel_v14 as fixture

travel = fixture.travel
env = fixture.env
lang = fixture.lang
sim = fixture.sim


class MHandshakeTests(unittest.TestCase):
    def setUp(self):
        self.base = fixture.TravelListTests()
        self.base.setUp()
        env.messages[:] = []
        travel._epoch = 0
        travel._lease_sent = 0.0
        travel._lease_running = False
        del travel._requests[:]
        self.clock = [1000.0]
        self.time = patch('time.monotonic', lambda: self.clock[0])
        self.time.start()

    def tearDown(self):
        self.time.stop()
        self.base.tearDown()

    def messages(self):
        return list(env.messages)

    def last(self):
        return env.messages[-1]

    def test_heartbeat_republishes_the_same_epoch_and_is_throttled(self):
        self.assertTrue(travel.start_lease())
        self.assertEqual(self.messages(), ['A11y|travelready|1'])
        self.assertEqual(len(env.queue), 1)     # re-armed on the pump
        env.drain()                              # same instant: no new message
        self.assertEqual(self.messages(), ['A11y|travelready|1'])
        self.clock[0] += 2.5
        env.drain()
        self.assertEqual(self.messages(), ['A11y|travelready|1', 'A11y|travelready|1'])
        self.assertEqual(travel._epoch, 1)

    def test_epoch_grows_across_stop_and_start_and_never_resets(self):
        travel.start_lease()
        travel.stop_lease()
        self.assertEqual(self.last(), 'A11y|travelready|0')
        self.assertEqual(travel._epoch, 1)
        travel.start_lease()
        self.assertEqual(self.last(), 'A11y|travelready|2')

    def test_dead_pump_stops_the_heartbeat(self):
        travel.start_lease()
        with patch.object(travel.pump, 'post', return_value=False):
            self.clock[0] += 3
            env.drain()
        self.assertFalse(travel._lease_running)
        self.assertEqual(env.queue, [])

    def test_setting_off_publishes_lease_zero_and_setting_state(self):
        env.settings._stored['travel_list'] = False
        travel.start_lease()
        self.assertEqual(self.last(), 'A11y|travelready|0')
        self.assertTrue(travel.announce_setting())
        self.assertEqual(self.last(), 'A11y|travellist|off')

    def test_ok_path_pushes_and_replies_ok(self):
        travel.start_lease()
        env.queue.clear()
        self.assertTrue(travel.a11y_travel('1', '7'))
        self.assertEqual(sim.pushes, [])         # deferred to the pump
        env.drain()
        self.assertEqual(len(sim.pushes), 1)
        self.assertEqual(self.last(), 'A11y|travelresult|1|7|ok')
        self.assertEqual(travel._entry((1, 7))[1], 'ok')

    def test_old_epoch_is_refused_at_ingress_without_a_push(self):
        travel.start_lease()
        env.queue.clear()
        self.assertFalse(travel.a11y_travel('99', '8'))
        self.assertEqual(self.last(), 'A11y|travelresult|99|8|refused|stale')
        self.assertEqual(env.queue, [])
        self.assertEqual(sim.pushes, [])

    def test_request_crossing_a_heartbeat_is_still_valid(self):
        travel.start_lease()
        env.queue.clear()
        travel.a11y_travel('1', '9')
        self.clock[0] += 2.5                     # a heartbeat would fire now; same epoch
        env.drain()
        self.assertEqual(len(sim.pushes), 1)
        self.assertIn('A11y|travelresult|1|9|ok', self.messages())

    def test_epoch_change_before_the_push_refuses_it(self):
        travel.start_lease()
        env.queue.clear()
        travel.a11y_travel('1', '10')
        travel.start_lease()                     # zone reload / pump restart
        self.assertIn('A11y|travelresult|1|10|refused|stale', self.messages())   # settled at the epoch change
        env.queue.clear()
        travel.open_travel(10, 1)
        self.assertEqual(sim.pushes, [])

    def test_stalled_pump_request_expires_at_the_deadline(self):
        travel.start_lease()
        env.queue.clear()
        travel.a11y_travel('1', '11')
        self.clock[0] += 3.5                     # Flash has re-enabled M meanwhile
        env.drain()
        self.assertEqual(sim.pushes, [])
        self.assertEqual(self.last(), 'A11y|travelresult|1|11|refused|stale')

    def test_cancel_at_ingress_is_acknowledged_at_once_and_beats_a_queued_push(self):
        travel.start_lease()
        env.queue.clear()
        travel.a11y_travel('1', '12')
        before = len(env.messages)
        self.assertTrue(travel.a11y_travel_cancel('12'))
        self.assertEqual(self.last(), 'A11y|travelresult|1|12|refused|cancelled')   # ack before any drain
        env.drain()
        self.assertEqual(sim.pushes, [])
        self.assertEqual(len(env.messages), before + 1)      # the drain stays silent
        self.assertTrue(travel.a11y_travel_cancel('12'))    # duplicate cancel: acknowledged again
        self.assertEqual(len(env.messages), before + 2)

    def test_duplicate_and_replayed_requests_are_refused(self):
        travel.start_lease()
        env.queue.clear()
        travel.a11y_travel('1', '13')
        before = len(env.messages)
        self.assertFalse(travel.a11y_travel('1', '13'))
        self.assertEqual(len(env.messages), before)          # a pending duplicate stays silent
        env.drain()
        self.assertEqual(len(sim.pushes), 1)
        self.assertEqual(self.last(), 'A11y|travelresult|1|13|ok')   # only the original outcome answers
        self.assertFalse(travel.a11y_travel('1', '13'))     # done: answered again, never re-queued
        self.assertEqual(self.last(), 'A11y|travelresult|1|13|ok')
        self.assertEqual(len(env.queue), 0)

    def test_request_history_is_bounded(self):
        travel.start_lease()
        for n in range(1, 100):
            travel.a11y_travel('1', str(n))
        self.assertLessEqual(len(travel._requests), travel._REQUEST_HISTORY)

    def test_affordance_refusal_and_away_sim_are_reported_and_spoken(self):
        travel.start_lease()
        env.queue.clear()
        sim.result = False
        travel.a11y_travel('1', '14')
        env.drain()
        self.assertEqual(self.last(), 'A11y|travelresult|1|14|refused|refused')
        self.assertEqual(self.base.spoken.call_args[0][0], lang.t('action unavailable'))
        sim.result = True
        sim.zone_id = 2000
        travel.a11y_travel('1', '15')
        env.drain()
        self.assertEqual(self.last(), 'A11y|travelresult|1|15|refused|away')
        self.assertEqual(self.base.spoken.call_args[0][0], lang.t('sim unavailable'))
        self.assertEqual(len(sim.pushes), 1)     # only the refused attempt

    def test_dead_pump_or_setting_off_refuse_at_dispatch(self):
        travel.start_lease()
        with patch.object(travel.pump, 'post', return_value=False):
            self.assertFalse(travel.a11y_travel('1', '16'))
        self.assertEqual(self.last(), 'A11y|travelresult|1|16|refused|no_pump')
        env.settings._stored['travel_list'] = False
        self.assertFalse(travel.a11y_travel('1', '17'))
        self.assertEqual(self.last(), 'A11y|travelresult|1|17|refused|refused')

    def test_stop_invalidates_pending_requests(self):
        travel.start_lease()
        env.queue.clear()
        travel.a11y_travel('1', '18')
        travel.stop_lease()
        env.drain()
        self.assertEqual(sim.pushes, [])
        self.assertIn('A11y|travelresult|1|18|refused|stale', self.messages())

    def test_zero_publication_invalidates_queued_work(self):
        travel.start_lease()                     # the heartbeat stays queued ahead of the request
        travel.a11y_travel('1', '20')
        env.settings._stored['travel_list'] = False
        self.clock[0] += 2.5
        env.drain()                              # heartbeat publishes 0, then the queued push runs
        self.assertIn('A11y|travelready|0', self.messages())
        self.assertEqual(sim.pushes, [])
        env.settings._stored['travel_list'] = True
        env.drain()
        self.assertEqual(sim.pushes, [])         # nothing survives the zero publication

    def test_cancel_before_the_request_leaves_a_tombstone(self):
        travel.start_lease()
        env.queue.clear()
        self.assertTrue(travel.a11y_travel_cancel('21'))
        self.assertEqual(self.last(), 'A11y|travelresult|1|21|refused|cancelled')
        self.assertFalse(travel.a11y_travel('1', '21'))   # the late request is refused
        self.assertEqual(self.last(), 'A11y|travelresult|1|21|refused|cancelled')
        self.assertEqual(env.queue, [])

    def test_duplicate_cancel_and_cancel_after_completion_answer_again(self):
        travel.start_lease()
        env.queue.clear()
        travel.a11y_travel('1', '22')
        env.drain()
        self.assertEqual(self.last(), 'A11y|travelresult|1|22|ok')
        self.assertTrue(travel.a11y_travel_cancel('22'))           # lost reply recovery
        self.assertEqual(self.last(), 'A11y|travelresult|1|22|ok')
        travel.a11y_travel('1', '23')
        travel.a11y_travel_cancel('23')
        before = len(env.messages)
        self.assertTrue(travel.a11y_travel_cancel('23'))
        self.assertEqual(self.last(), 'A11y|travelresult|1|23|refused|cancelled')
        self.assertEqual(len(env.messages), before + 1)
        env.drain()
        self.assertEqual(len(sim.pushes), 1)

    def test_replayed_request_after_a_refusal_answers_with_the_same_refusal(self):
        travel.start_lease()
        env.queue.clear()
        sim.result = False
        travel.a11y_travel('1', '24')
        env.drain()
        self.assertEqual(self.last(), 'A11y|travelresult|1|24|refused|refused')
        self.assertFalse(travel.a11y_travel('1', '24'))
        self.assertEqual(self.last(), 'A11y|travelresult|1|24|refused|refused')
        self.assertEqual(len(sim.pushes), 1)

    def test_menu_toggle_announces_the_setting_and_starts_an_epoch(self):
        row = next(r for r in fixture.menu.ROWS if r.key == 'travel_list')
        saving = patch.object(env.settings, '_save', return_value=True)
        saving.start()
        self.addCleanup(saving.stop)
        fixture.menu._apply(row, False)
        self.assertFalse(env.settings.get('travel_list'))
        self.assertIn('A11y|travellist|off', self.messages())
        self.assertIn('A11y|travelready|0', self.messages())
        fixture.menu._apply(row, True)
        self.assertEqual(self.messages()[-2:], ['A11y|travellist|on', 'A11y|travelready|2'])


if __name__ == '__main__':
    unittest.main(verbosity=1)
