"""Simplified menus travel front, Python side.

M first offers Go alone or Choose who comes. Choose who comes is today's path
(EA's Travel, its companion picker, then the world and place list). Go alone
pushes the same EA Travel and answers only its own companion picker with
nobody, through EA's dialog service, when the picker allows an empty choice;
anything else is shown natively. A refused Travel says so and shows EA's own
reason. Run with py -3.7 tools/test_travel_front.py. Source bodies only.
"""
import sys
import types
import unittest
from unittest.mock import patch

import test_travel_v14 as fixture

travel = fixture.travel
env = fixture.env
lang = fixture.lang
sim = fixture.sim
service = fixture.service
OK = fixture.OK


class FakeTravel(object):
    """The pushed Travel interaction; EA's picker listener is its method."""

    def __init__(self):
        self.picks = []
        self.is_finishing = False
        self.has_been_canceled = False
        self.guid64 = travel._TRAVEL_AFFORDANCE
        self.sim = types.SimpleNamespace(sim_id=700)

    def on_picker_selected(self, dialog):
        self.picks.append(list(dialog.picked_results))


class Pushed(object):
    def __init__(self, interaction):
        self.interaction = interaction

    def __bool__(self):
        return True


class Refused(object):
    def __init__(self, tooltip=None):
        self.test_result = types.SimpleNamespace(tooltip=tooltip)

    def __bool__(self):
        return False


notifications = []


class _Notification(object):
    def __init__(self, owner, text=None, **kwargs):
        self.owner, self.text = owner, text

    def show_dialog(self, **kwargs):
        notifications.append(self.text())


notification_module = types.ModuleType('ui.ui_dialog_notification')
notification_module.UiDialogNotification = types.SimpleNamespace(
    TunableFactory=lambda: types.SimpleNamespace(default=_Notification))


class FrontTests(unittest.TestCase):
    def setUp(self):
        self.base = fixture.TravelListTests()
        self.base.setUp()
        env.settings._stored['simplified_menus'] = True
        env.messages[:] = []
        fixture.sim_picker_native[:] = []
        notifications[:] = []
        travel._front_id = None
        travel._alone = None
        travel._epoch = 0
        travel._lease_running = False
        del travel._requests[:]
        self.clock = [1000.0]
        self.time = patch('time.monotonic', lambda: self.clock[0])
        self.time.start()
        self.modules = patch.dict(sys.modules, {'ui.ui_dialog_notification': notification_module})
        self.modules.start()
        self.travel_si = FakeTravel()
        sim.result = Pushed(self.travel_si)

    def tearDown(self):
        self.modules.stop()
        self.time.stop()
        self.base.tearDown()

    def spoken(self):
        return [call[0][0] for call in self.base.spoken.call_args_list]

    def press_m(self, request='7'):
        travel.start_lease()
        env.queue.clear()
        self.assertTrue(travel.a11y_travel(str(travel._epoch), request))
        env.drain()
        return fixture.shown[-1]

    def companion_picker(self, interaction=None, minimum=0):
        dialog = fixture.UiSimPicker(interaction or self.travel_si, minimum=minimum)
        service._active_dialogs[dialog.dialog_id] = dialog      # EA registers before it distributes
        result = dialog.distribute_dialog('msg', 'proto')
        return dialog, result

    def test_m_offers_alone_or_with_others_and_pushes_nothing_yet(self):
        window = self.press_m()
        self.assertEqual(window.names(), [lang.t('travel alone'), lang.t('travel with others')])
        self.assertEqual(window.title, lang.t('travel'))
        self.assertEqual(sim.pushes, [])
        self.assertIn('A11y|travelresult|1|7|ok', env.messages)   # Flash is answered: our window is up
        self.assertNotEqual(lang.t('travel alone'), 'travel alone')

    def test_choose_who_comes_is_todays_path(self):
        window = self.press_m()
        window.answer(1)
        self.assertEqual(sim.pushes, [])                          # never inside the reply
        env.drain()
        self.assertEqual(len(sim.pushes), 1)
        self.assertEqual(sim.pushes[0][0], fixture.TRAVEL_AFFORDANCE)
        self.assertIsNone(travel._alone)
        dialog, _ = self.companion_picker()
        self.assertEqual(fixture.sim_picker_native, [dialog.dialog_id])   # EA's picker, as always
        self.assertEqual(service.picks, [])

    def test_go_alone_answers_only_our_picker_with_nobody(self):
        window = self.press_m()
        window.answer(0)
        env.drain()
        self.assertEqual(len(sim.pushes), 1)
        dialog, result = self.companion_picker()
        self.assertIsNone(result)
        self.assertEqual(fixture.sim_picker_native, [])          # never drawn
        self.assertEqual(service.picks, [])                       # deferred to the pump
        env.drain()
        self.assertEqual(service.picks, [(dialog.dialog_id, [])])  # EA's preselection cleared
        self.assertEqual(service.responses, [(dialog.dialog_id, OK)])
        self.assertEqual(self.travel_si.picks, [[]])              # EA's own listener ran: nobody
        self.assertNotIn(dialog.dialog_id, service._active_dialogs)
        self.assertIsNone(travel._alone)

    def immediate(self, owner=None):
        """423375 is an ImmediateSuperInteraction: EA shows the companion
        picker inside push_super_affordance, before it returns."""
        shown = []

        def push(affordance, target, context, **kwargs):
            sim.pushes.append((affordance, target, context))
            shown.append(self.companion_picker(interaction=owner or self.travel_si))
            return sim.result
        return shown, patch.object(sim, 'push_super_affordance', side_effect=push)

    def test_go_alone_claims_a_picker_shown_inside_the_push(self):
        # Live 2026-09-26, BFF household: the picker appeared in the same
        # second as "Travel ok" and was shown natively.
        window = self.press_m()
        shown, pusher = self.immediate()
        with pusher:
            window.answer(0)
            env.drain()
        dialog, result = shown[0]
        self.assertIsNone(result)
        self.assertEqual(fixture.sim_picker_native, [])
        env.drain()
        self.assertEqual(service.picks, [(dialog.dialog_id, [])])
        self.assertEqual(service.responses, [(dialog.dialog_id, OK)])
        self.assertEqual(self.travel_si.picks, [[]])
        self.assertIsNone(travel._alone)
        self.assertIsNone(travel._alone_push)
        later, _ = self.companion_picker()                    # nothing left to claim
        self.assertEqual(fixture.sim_picker_native, [later.dialog_id])

    def test_inside_the_push_only_our_sims_travel_is_claimed(self):
        other_sim = FakeTravel()
        other_sim.sim = types.SimpleNamespace(sim_id=701)
        other_kind = FakeTravel()
        other_kind.guid64 = 999
        for index, owner in enumerate((other_sim, other_kind)):
            fixture.sim_picker_native[:] = []
            window = self.press_m(str(30 + index))
            shown, pusher = self.immediate(owner)
            with pusher:
                window.answer(0)
                env.drain()
            dialog, _ = shown[0]
            self.assertEqual(fixture.sim_picker_native, [dialog.dialog_id])
            self.assertIsNone(travel._alone_push)

    def test_choose_who_comes_never_claims_inside_the_push(self):
        window = self.press_m()
        shown, pusher = self.immediate()
        with pusher:
            window.answer(1)
            env.drain()
        dialog, _ = shown[0]
        self.assertEqual(fixture.sim_picker_native, [dialog.dialog_id])
        self.assertEqual(service.picks, [])

    def test_other_sim_pickers_are_untouched_and_keep_the_claim(self):
        window = self.press_m()
        window.answer(0)
        env.drain()
        other, result = self.companion_picker(interaction=FakeTravel())
        self.assertIsNone(result)
        self.assertEqual(fixture.sim_picker_native, [other.dialog_id])
        self.assertIsNotNone(travel._alone)
        ours, _ = self.companion_picker()
        env.drain()
        self.assertEqual(service.responses, [(ours.dialog_id, OK)])

    def test_a_picker_that_needs_someone_is_shown(self):
        window = self.press_m()
        window.answer(0)
        env.drain()
        dialog, _ = self.companion_picker(minimum=1)
        self.assertEqual(fixture.sim_picker_native, [dialog.dialog_id])
        self.assertEqual(service.picks, [])
        self.assertIsNone(travel._alone)                          # used up; never answers a later one

    def test_a_long_pause_still_goes_alone(self):
        # Live 2026-09-26: the game sat paused 40 to 50 s before the phone
        # animation ran. The claim follows the interaction, not a clock.
        window = self.press_m()
        window.answer(0)
        env.drain()
        self.clock[0] += 3600
        dialog, result = self.companion_picker()
        self.assertIsNone(result)
        env.drain()
        self.assertEqual(service.responses, [(dialog.dialog_id, OK)])

    def test_a_finished_or_cancelled_travel_leaves_later_pickers_alone(self):
        for index, flag in enumerate(('is_finishing', 'has_been_canceled')):
            self.travel_si = FakeTravel()
            sim.result = Pushed(self.travel_si)
            fixture.sim_picker_native[:] = []
            window = self.press_m(str(20 + index))
            window.answer(0)
            env.drain()
            setattr(self.travel_si, flag, True)
            dialog, _ = self.companion_picker()
            self.assertEqual(fixture.sim_picker_native, [dialog.dialog_id], flag)
            self.assertIsNone(travel._alone)

    def test_a_new_travel_replaces_go_alone(self):
        window = self.press_m()
        window.answer(0)
        env.drain()
        first = self.travel_si
        self.travel_si = FakeTravel()
        sim.result = Pushed(self.travel_si)
        window = self.press_m('8')
        window.answer(1)                                          # Choose who comes
        env.drain()
        self.assertIsNone(travel._alone)
        dialog, _ = self.companion_picker(interaction=first)
        self.assertEqual(fixture.sim_picker_native, [dialog.dialog_id])

    def test_logs_say_queued_then_answered(self):
        window = self.press_m()
        window.answer(0)
        env.drain()
        with patch.object(env.speech, 'log_line') as logged:
            self.companion_picker()
            env.drain()
        lines = [call[0][0] for call in logged.call_args_list]
        self.assertTrue(any('queued for nobody' in line for line in lines), lines)
        self.assertTrue(any('answered: nobody' in line for line in lines), lines)

    def test_our_window_change_holds_the_scanner(self):
        import tyjokr_a11y_keys as keys
        with patch.object(keys, 'hold_scanner_resume') as held:
            window = self.press_m()
            window.answer(0)
            env.drain()
            held.assert_not_called()                              # Go alone: the Sim walks off first
            dialog = fixture.UiMapViewPicker(fixture.rows())
            dialog.distribute_dialog('msg', 'proto')
            fixture.shown[-1].answer(0)                           # a world: the place window follows
            held.assert_called_once_with()

    def test_if_ea_refuses_nobody_the_picker_is_shown_after_all(self):
        window = self.press_m()
        window.answer(0)
        env.drain()
        service.refuse_ok = True
        dialog, _ = self.companion_picker()
        env.drain()
        self.assertEqual(fixture.sim_picker_native, [dialog.dialog_id])
        self.assertIn(dialog.dialog_id, service._active_dialogs)

    def test_switched_off_before_the_picker_shows_it(self):
        window = self.press_m()
        window.answer(0)
        env.drain()
        env.settings._stored['simplified_menus'] = False
        dialog, _ = self.companion_picker()
        self.assertEqual(fixture.sim_picker_native, [dialog.dialog_id])

    def test_escape_on_the_window_does_nothing(self):
        window = self.press_m()
        window.close()
        env.drain()
        self.assertEqual(sim.pushes, [])
        self.assertIsNone(travel._front_id)

    def test_the_choice_rechecks_the_sim_and_the_setting(self):
        window = self.press_m()
        env.settings._stored['travel_list'] = False
        window.answer(0)
        env.drain()
        self.assertEqual(sim.pushes, [])
        self.assertEqual(self.spoken()[-1], lang.t('action unavailable'))
        env.settings._stored['travel_list'] = True
        window = self.press_m('8')
        sim.zone_id = 999                                         # away from the lot
        window.answer(1)
        env.drain()
        self.assertEqual(sim.pushes, [])
        self.assertEqual(self.spoken()[-1], lang.t('sim unavailable'))

    def test_a_refused_travel_says_so_and_shows_eas_reason(self):
        reasons = []
        sim.result = Refused(tooltip=lambda *tokens: reasons.append(tokens) or 'reason text')
        window = self.press_m()
        window.answer(0)
        env.drain()
        self.assertEqual(self.spoken()[-1], lang.t('action unavailable'))
        self.assertEqual(notifications, ['reason text'])
        self.assertEqual(reasons, [(sim,)])
        self.assertIsNone(travel._alone)
        sim.result = Refused(tooltip=None)
        window = self.press_m('9')
        window.answer(1)
        env.drain()
        self.assertEqual(notifications, ['reason text'])          # no reason, no notification
        self.assertEqual(self.spoken()[-1], lang.t('action unavailable'))

    def test_simplified_off_pushes_at_once(self):
        env.settings._stored['simplified_menus'] = False
        travel.start_lease()
        env.queue.clear()
        travel.a11y_travel('1', '7')
        env.drain()
        self.assertEqual(len(sim.pushes), 1)
        self.assertEqual(fixture.shown, [])

    def test_the_native_map_fallback_is_logged(self):
        env.settings._stored['travel_list'] = False
        dialog = fixture.UiMapViewPicker(fixture.rows())
        with patch.object(env.speech, 'log_line') as logged:
            dialog.distribute_dialog('msg', 'proto')
        self.assertIn('to the native map (list off', logged.call_args[0][0])

    def test_terms_are_translated(self):
        for term in ('travel', 'travel front instructions', 'travel alone', 'travel alone detail',
                     'travel with others', 'travel with others detail', 'selected count'):
            self.assertIn('pl', lang._TRANSLATIONS[term], term)
            for language in ('en', 'pl'):
                text = lang._TRANSLATIONS[term][language]
                self.assertNotIn(chr(0x2014), text)
                self.assertNotIn(chr(0x2013), text)


if __name__ == '__main__':
    unittest.main()
