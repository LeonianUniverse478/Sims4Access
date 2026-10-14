"""Travel list switch: every settings change reaches the client at once,
and an open list honours a switch-off at every step.

Audit (travel.py): the native dialog wrap, the M ingress and its pump step,
every list reply and the M lease all check enabled(). These checks add the
two paths that did not: a11y.reload (no resync, no new lease epoch) and a
continuation queued on the pump before the switch went off.
Run with py -3.7 tools/test_travel_controls.py.
"""
import unittest
from unittest.mock import patch

import test_travel_v14 as fixture

env = fixture.env
travel = fixture.travel
menu = env.menu
CANCEL = fixture.CANCEL


class TravelSwitchTests(unittest.TestCase):
    # Borrow the fixture's setup without inheriting (and re-running) its tests.
    def setUp(self):
        fixture.TravelListTests.setUp(self)
        self.addCleanup(fixture.TravelListTests.tearDown, self)
        env.messages.clear()
        travel._requests[:] = []

    def test_switch_off_resyncs_client_and_starts_a_stale_epoch(self):
        epoch = travel._epoch
        env.settings._stored['travel_list'] = False
        travel.apply_setting()
        self.assertIn('A11y|travellist|off', env.messages)
        self.assertEqual(travel._epoch, epoch + 1)
        self.assertEqual(env.messages[-1], 'A11y|travelready|0')   # Flash stops routing M at once

    def test_switch_on_resyncs_client_with_a_fresh_lease(self):
        env.settings._stored['travel_list'] = True
        travel.apply_setting()
        self.assertIn('A11y|travellist|on', env.messages)
        self.assertEqual(env.messages[-1], 'A11y|travelready|{}'.format(travel._epoch))

    def test_switch_off_cancels_an_open_list_natively(self):
        dialog = fixture.request()
        self.assertIsNotNone(travel._pending)
        env.settings._stored['travel_list'] = False
        travel.apply_setting()
        self.assertEqual(fixture.service.responses, [(dialog.dialog_id, CANCEL)])
        self.assertIsNone(travel._pending)
        self.assertIsNone(travel._window_id)
        shown_before = len(fixture.shown)
        fixture.shown[0].answer(1)          # a late answer to the closed window does nothing
        env.drain()
        self.assertEqual(len(fixture.shown), shown_before)
        self.assertEqual(fixture.service.responses, [(dialog.dialog_id, CANCEL)])

    def test_switch_off_between_reply_and_pump_step_cancels(self):
        dialog = fixture.request()
        fixture.shown[0].answer(1)          # accepted while on: the next window is queued
        self.assertEqual(len(fixture.shown), 1)
        env.settings._stored['travel_list'] = False
        env.drain()
        self.assertEqual(len(fixture.shown), 1)                     # no places window
        self.assertEqual(fixture.service.responses, [(dialog.dialog_id, CANCEL)])
        self.assertIsNone(travel._pending)

    def test_switch_off_before_commit_step_never_answers_with_a_zone(self):
        dialog = fixture.request()
        fixture.shown[0].answer(1)
        env.drain()
        places = fixture.shown[-1]
        index = next(i for i, row in enumerate(places.rows)
                     if row.tag[0] == travel.PLACE and not travel._units_of(travel._pending, row.tag[1]))
        places.answer(index)               # queues the commit on the pump
        env.settings._stored['travel_list'] = False
        env.drain()
        self.assertEqual(fixture.service.picks, [])
        self.assertEqual(fixture.service.responses, [(dialog.dialog_id, CANCEL)])

    def test_menu_row_goes_through_the_same_apply(self):
        row = next(r for r in menu.ROWS if r.key == 'travel_list')
        with patch.object(env.settings, '_save', return_value=True), \
                patch.object(travel, 'apply_setting') as applied:
            menu._apply(row, False)
        applied.assert_called_once_with()
        self.assertFalse(env.settings.get('travel_list'))

    def heartbeats(self):
        return [item for item in env.queue if item[0] is travel._refresh_lease]

    def test_repeated_starts_leave_one_heartbeat_chain(self):
        env.queue.clear()
        for _ in range(3):
            travel.apply_setting()          # menu toggles and reloads
        travel.start_lease()                # plus a pump restart
        self.assertEqual(len(self.heartbeats()), 4)     # queued before the retirements run
        for _ in range(3):
            env.drain()
            self.assertEqual(len(self.heartbeats()), 1)
        self.assertTrue(travel._lease_running)          # a retired callback left the live chain alone

    def test_stop_retires_queued_heartbeats_for_good(self):
        env.queue.clear()
        travel.start_lease()
        travel.apply_setting()
        env.messages.clear()
        travel.stop_lease()
        for _ in range(3):
            env.drain()
        self.assertEqual(self.heartbeats(), [])
        self.assertFalse(travel._lease_running)
        self.assertEqual([m for m in env.messages if m.startswith('A11y|travelready|')],
                         ['A11y|travelready|0'])

    def test_m_ingress_refuses_while_off(self):
        travel._lease_running = True
        env.settings._stored['travel_list'] = False
        self.assertFalse(travel.a11y_travel(str(travel._epoch), '5'))
        self.assertEqual(env.messages[-1], 'A11y|travelresult|{}|5|refused|refused'.format(travel._epoch))
        self.assertEqual(env.queue, [])     # nothing reached the pump


if __name__ == '__main__':
    unittest.main()
