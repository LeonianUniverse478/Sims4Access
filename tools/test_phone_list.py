"""Simplified menus phone list and the shared native answer helper.

The phone list is EA's own phone menu (the phone's disable tests, ChoiceMenu
with its tests, pie menu modifiers and tutorial visibility, names, reasons
and categories) in two windows: categories, then actions. An action runs as
the phone runs it (a fresh context, test_and_execute); Travel goes through
the Go alone window. Control Alt P opens it only when nothing is waiting
and Simplified menus are on. The helper answers a picker only through EA's
dialog service and never turns on automatic answering.
Run with py -3.7 tools/test_phone_list.py. Source bodies only.
"""
import sys
import types
import unittest
from unittest.mock import patch

import test_travel_v14 as fixture

env = fixture.env
lang = fixture.lang
travel = fixture.travel
import tyjokr_a11y_phone as phone      # noqa: E402
import tyjokr_a11y_native as native    # noqa: E402
import tyjokr_a11y_hub as hub          # noqa: E402


class Category(object):
    def __init__(self, name, parent=None, priority=0):
        self.name, self._parent, self._display_priority = name, parent, priority

    def _display_name(self, *tokens):
        return self.name


class Affordance(object):
    def __init__(self, name, guid64, description=None):
        self.name, self.guid64, self.description = name, guid64, description

    def get_name(self, target, context, **kwargs):
        return self.name

    def create_localized_string(self, factory, context=None, target=None, **kwargs):
        return 'reason: ' + factory()

    def get_display_tooltip(self, context=None, target=None, **kwargs):
        return self.description


class Aop(object):
    def __init__(self, affordance, outcome=True):
        self.affordance, self.target, self.interaction_parameters = affordance, None, {}
        self.outcome = outcome
        self.runs = []

    def test_and_execute(self, context):
        self.runs.append(context)
        return self.outcome


class Result(object):
    def __init__(self, ok, tooltip=None):
        self.ok, self.tooltip = ok, tooltip

    def __bool__(self):
        return self.ok


class Item(object):
    def __init__(self, aop, context, result, category_key):
        self.aop, self.context, self.result, self.category_key = aop, context, result, category_key


MENU = []           # (aop, result, category_key) the fake ChoiceMenu offers


class ChoiceMenu(object):
    def __init__(self, sim):
        self.items = []

    def add_potential_aops(self, target, context, potential_aops, scoring):
        assert list(potential_aops) == ['phone aops']
        for index, (aop, result, key) in enumerate(MENU):
            self.items.append((index, Item(aop, context, result, key)))

    def __iter__(self):
        return iter(self.items)


class Queue(object):
    full = False

    def can_queue_visible_interaction(self):
        return not self.full


class PhoneSim(object):
    def __init__(self):
        self.sim_id = 700
        self.zone_id = 1000
        self.sim_info = 'info'
        self.queue = Queue()
        self.hidden, self.forbidden, self.suppressed = set(), {}, {}

    def potential_phone_interactions(self, context):
        return ['phone aops']

    def test_pie_menu_modifiers(self, affordance):
        return affordance.guid64 not in self.hidden, self.suppressed.get(affordance.guid64)

    def apply_forbid_by_object_tags_pie_menu_modifiers(self, aop):
        return self.forbidden.get(aop.affordance.guid64)


class Client(object):
    def create_interaction_context(self, sim, **kwargs):
        return types.SimpleNamespace(sim=sim, fresh=True)


CAREER = Category('Career', priority=2)
SOCIAL = Category('Social', priority=1)
INVITE = Category('Invite', parent=SOCIAL)
CATEGORIES = {1: CAREER, 2: SOCIAL, 3: INVITE}
PHONE_DISABLED = []
notifications = []


class _Notification(object):
    def __init__(self, owner, text=None, **kwargs):
        self.text = text

    def show_dialog(self, **kwargs):
        notifications.append(self.text())


choices_module = types.ModuleType('interactions.choices')
choices_module.ChoiceMenu = ChoiceMenu
phone_tuning = types.ModuleType('sims.phone_tuning')
phone_tuning.PhoneTuning = types.SimpleNamespace(DISABLE_PHONE_TESTS=PHONE_DISABLED)
resolver_module = types.ModuleType('event_testing.resolver')
resolver_module.SingleSimResolver = lambda info: (lambda test: test())
notification_module = types.ModuleType('ui.ui_dialog_notification')
notification_module.UiDialogNotification = types.SimpleNamespace(
    TunableFactory=lambda: types.SimpleNamespace(default=_Notification))


class Base(unittest.TestCase):
    def setUp(self):
        self.base = fixture.TravelListTests()
        self.base.setUp()
        env.settings._stored['simplified_menus'] = True
        env.messages[:] = []
        notifications[:] = []
        del MENU[:]
        del PHONE_DISABLED[:]
        phone._list = None
        phone._list_id = None
        phone._waiting[:] = []
        travel._front_id = None
        travel._alone = None
        self.sim = PhoneSim()
        self.client = Client()
        tutorial = types.SimpleNamespace(is_affordance_visible=lambda affordance: affordance.guid64 != 99)
        manager = types.SimpleNamespace(get=lambda key: CATEGORIES.get(key))
        self.patches = [
            patch.dict(sys.modules, {'interactions.choices': choices_module, 'sims.phone_tuning': phone_tuning,
                                     'event_testing.resolver': resolver_module,
                                     'ui.ui_dialog_notification': notification_module}),
            patch.object(fixture.services, 'get_active_sim', lambda: self.sim),
            patch.object(fixture.services, 'client_manager',
                         lambda: types.SimpleNamespace(get_first_client=lambda: self.client)),
            patch.object(fixture.services, 'get_tutorial_service', lambda: tutorial, create=True),
            patch.object(fixture.services, 'get_instance_manager',
                         lambda kind: manager if kind == 'piecat' else fixture._instance_manager(kind)),
            patch.object(fixture.resources.Types, 'PIE_MENU_CATEGORY', 'piecat', create=True),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.base.tearDown()

    def spoken(self):
        return [call[0][0] for call in self.base.spoken.call_args_list]

    def offer(self, name, guid64, key=None, ok=True, tooltip=None, outcome=True, description=None):
        aop = Aop(Affordance(name, guid64, description), outcome)
        MENU.append((aop, Result(ok, tooltip), key))
        return aop

    def window(self):
        return fixture.shown[-1]

    def settle(self, limit=10):
        """Drain the pump until nothing is queued (an action waits one
        extra turn for our window to close on the client)."""
        for _ in range(limit):
            if not env.queue:
                return
            env.drain()


class PhoneListTests(Base):
    def test_categories_in_phone_priority_then_uncategorized_actions(self):
        self.offer('Find a Job', 10, key=1)
        self.offer('Quit Job', 11, key=1)
        self.offer('Throw a Party', 12, key=3)                  # Social > Invite
        self.offer('Check Weather', 13)
        self.assertTrue(phone.open_list())
        window = self.window()
        self.assertEqual(window.title, lang.t('phone'))
        self.assertEqual(window.text, lang.t('phone list instructions'))
        self.assertEqual(window.names(), ['Social', 'Career', 'Check Weather'])
        self.assertEqual([row.row_description for row in window.rows[:2]],
                         [lang.t('phone group count one').format(1), lang.t('phone group count').format(2)])

    def test_one_action_is_singular(self):
        self.offer('Find a Job', 10, key=1)
        self.offer('Throw a Party', 12, key=3)
        self.offer('Invite Over', 14, key=2)
        phone.open_list()
        descriptions = [row.row_description for row in self.window().rows]
        self.assertEqual(descriptions, [lang.t('phone group count').format(2),
                                        lang.t('phone group count one').format(1)])
        self.assertEqual(lang.t('phone group count one').format(1), '1 action')

    def test_opening_a_category_holds_the_scanner(self):
        import tyjokr_a11y_keys as keys
        self.offer('Find a Job', 10, key=1)
        phone.open_list()
        with patch.object(keys, 'hold_scanner_resume') as held:
            self.window().answer(0)
            held.assert_called_once_with()
            env.drain()
            self.window().answer(1)                             # an action: no window follows
            held.assert_called_once_with()

    def test_a_category_lists_its_actions_after_a_way_back(self):
        self.offer('Throw a Party', 12, key=3)
        self.offer('Invite Over', 14, key=2, description='Ask someone over')
        phone.open_list()
        self.window().answer(0)
        env.drain()
        group = self.window()
        self.assertEqual(group.title, 'Social')                  # the game's own category name
        self.assertEqual(group.names(), [lang.t('back to phone'), 'Throw a Party', 'Invite Over'])
        self.assertEqual([row.row_description for row in group.rows[1:]], ['Invite', 'Ask someone over'])
        group.answer(0)
        env.drain()
        self.assertEqual(self.window().names(), ['Social'])

    def test_unavailable_actions_show_the_reason_and_never_run(self):
        aop = self.offer('Call to Chat', 15, ok=False, tooltip=lambda: 'asleep')
        self.sim.forbidden[16] = lambda: 'forbidden here'
        forbidden = self.offer('Order Pizza', 16)
        phone.open_list()
        rows = self.window().rows
        self.assertEqual([row.is_enable for row in rows], [False, False])
        self.assertEqual(rows[0].row_tooltip(), 'reason: asleep')
        self.assertEqual(rows[1].row_tooltip(), 'reason: forbidden here')
        self.window().answer(0)
        env.drain()
        self.assertEqual(aop.runs, [])
        self.assertEqual(forbidden.runs, [])
        self.assertEqual(self.spoken()[-1], lang.t('action unavailable'))

    def test_a_modifier_suppression_tooltip_alone_does_not_grey_an_action(self):
        # 1.128.90 bytecode of create_pie_menu_message (lines 881-884): the
        # modifier decides visibility only; its tooltip is replaced by the
        # forbid-by-object-tags one, so the phone shows this action enabled.
        aop = self.offer('Call to Chat', 40)
        self.sim.suppressed[40] = lambda *tokens: 'suppressed'
        phone.open_list()
        row = self.window().rows[0]
        self.assertTrue(row.is_enable)
        self.assertIsNone(row.row_tooltip)
        self.window().answer(0)
        self.settle()
        self.assertEqual(len(aop.runs), 1)
        self.assertEqual(notifications, [])

    def test_hidden_entries_stay_hidden(self):
        self.sim.hidden.add(20)
        self.offer('Secret', 20)
        self.offer('Tutorial Only', 99)
        self.offer('Visible', 21)
        phone.open_list()
        self.assertEqual(self.window().names(), ['Visible'])

    def test_an_action_runs_as_the_phone_runs_it(self):
        aop = self.offer('Find a Job', 10, key=1)
        phone.open_list()
        self.window().answer(0)
        env.drain()
        self.window().answer(1)
        self.assertEqual(aop.runs, [])                           # never inside the reply
        self.settle()
        self.assertEqual(len(aop.runs), 1)
        self.assertTrue(aop.runs[0].fresh)
        self.assertIsNone(phone._list)

    def test_a_refused_action_says_so_and_shows_the_reason(self):
        refused = Result(False)
        refused.test_result = types.SimpleNamespace(tooltip=lambda *tokens: 'not now')
        aop = self.offer('Plan Social Event', 30, outcome=refused)
        phone.open_list()
        self.window().answer(0)
        self.settle()
        self.assertEqual(len(aop.runs), 1)
        self.assertEqual(self.spoken()[-1], lang.t('action unavailable'))
        self.assertEqual(notifications, ['not now'])

    def test_an_action_waits_for_our_window_to_close(self):
        # Live 2026-09-26: Purchase Gifts ran while our phone window was still
        # the client's modal and left a dim, empty screen.
        import tyjokr_a11y_keys as keys
        aop = self.offer('Purchase Gifts', 186369)
        clock = [100.0]
        with patch.object(keys, '_modal_active', True), patch('time.monotonic', lambda: clock[0]):
            phone.open_list()
            self.window().answer(0)
            env.drain()
            env.drain()
            self.assertEqual(aop.runs, [])                        # our window still owns the keys
            keys._modal_active = False                            # the client closed it
            self.settle()
        self.assertEqual(len(aop.runs), 1)

    def test_a_window_that_stays_open_refuses_the_action(self):
        import tyjokr_a11y_keys as keys
        aop = self.offer('Purchase Gifts', 186369)
        clock = [100.0]
        with patch.object(keys, '_modal_active', True), patch('time.monotonic', lambda: clock[0]):
            phone.open_list()
            self.window().answer(0)
            env.drain()
            clock[0] += phone._CLOSE_WAIT + 0.1
            self.settle()
        self.assertEqual(aop.runs, [])
        self.assertEqual(self.spoken()[-1], lang.t('action unavailable'))

    def test_a_sim_change_during_the_wait_refuses(self):
        import tyjokr_a11y_keys as keys
        aop = self.offer('Purchase Gifts', 186369)
        with patch.object(keys, '_modal_active', True):
            phone.open_list()
            self.window().answer(0)
            env.drain()
            self.sim.sim_id = 701
            keys._modal_active = False
            self.settle()
        self.assertEqual(aop.runs, [])
        self.assertEqual(self.spoken()[-1], lang.t('sim unavailable'))

    def test_travel_goes_through_the_go_alone_window(self):
        aop = self.offer('Travel', travel._TRAVEL_AFFORDANCE)
        phone.open_list()
        self.window().answer(0)
        env.drain()
        self.assertEqual(aop.runs, [])
        self.assertEqual(self.window().names(), [lang.t('travel alone'), lang.t('travel with others')])

    def test_the_phones_own_refusals_come_first(self):
        self.offer('Find a Job', 10)
        PHONE_DISABLED.append(types.SimpleNamespace(test=lambda: True, tooltip=lambda *tokens: 'no signal'))
        self.assertFalse(phone.open_list())
        self.assertEqual(self.spoken()[-1], lang.t('phone unavailable'))
        self.assertEqual(notifications, ['no signal'])
        self.assertEqual(fixture.shown, [])
        del PHONE_DISABLED[:]
        self.sim.queue.full = True
        self.assertFalse(phone.open_list())
        self.assertEqual(self.spoken()[-1], lang.t('action queue full'))
        self.sim.queue.full = False
        del MENU[:]
        self.assertFalse(phone.open_list())
        self.assertEqual(self.spoken()[-1], lang.t('phone empty'))

    def test_a_changed_sim_or_a_stale_window_does_nothing(self):
        aop = self.offer('Find a Job', 10)
        phone.open_list()
        first = self.window()
        self.sim.sim_id = 701
        first.answer(0)
        env.drain()
        self.assertEqual(aop.runs, [])
        self.assertEqual(self.spoken()[-1], lang.t('sim unavailable'))
        self.sim.sim_id = 700
        phone.open_list()
        first.answer(0)                                           # an old window's late reply
        env.drain()
        self.assertEqual(aop.runs, [])

    def test_a_category_opens_only_with_the_setting_on_and_the_same_sim(self):
        self.offer('Find a Job', 10, key=1)
        phone.open_list()
        env.settings._stored['simplified_menus'] = False
        before = len(fixture.shown)
        self.window().answer(0)
        env.drain()
        self.assertEqual(len(fixture.shown), before)             # no category window
        self.assertEqual(self.spoken()[-1], lang.t('action unavailable'))
        self.assertIsNone(phone._list)
        env.settings._stored['simplified_menus'] = True
        phone.open_list()
        self.sim.sim_id = 701
        before = len(fixture.shown)
        self.window().answer(0)
        env.drain()
        self.assertEqual(len(fixture.shown), before)
        self.assertEqual(self.spoken()[-1], lang.t('sim unavailable'))

    def test_the_phone_checks_run_again_before_an_action(self):
        aop = self.offer('Find a Job', 10)
        phone.open_list()
        PHONE_DISABLED.append(types.SimpleNamespace(test=lambda: True, tooltip=lambda *tokens: 'asleep now'))
        self.window().answer(0)
        env.drain()
        self.assertEqual(aop.runs, [])
        self.assertEqual(self.spoken()[-1], lang.t('phone unavailable'))
        self.assertEqual(notifications, ['asleep now'])
        del PHONE_DISABLED[:]
        phone.open_list()
        self.sim.forbidden[10] = lambda *tokens: 'not allowed here'
        self.window().answer(0)
        env.drain()
        self.assertEqual(aop.runs, [])
        self.assertEqual(self.spoken()[-1], lang.t('action unavailable'))
        self.assertEqual(notifications[-1], 'not allowed here')
        del self.sim.forbidden[10]
        phone.open_list()
        self.sim.hidden.add(10)
        self.window().answer(0)
        env.drain()
        self.assertEqual(aop.runs, [])
        self.sim.hidden.clear()
        phone.open_list()
        self.sim.queue.full = True
        self.window().answer(0)
        env.drain()
        self.assertEqual(aop.runs, [])
        self.assertEqual(self.spoken()[-1], lang.t('action queue full'))

    def test_control_alt_p_keeps_calls_first_and_follows_the_setting(self):
        with patch.object(phone, 'open_list', return_value=True) as listed:
            self.assertTrue(phone.open_waiting(True))
            listed.assert_called_once_with()
            listed.reset_mock()
            self.assertFalse(phone.open_waiting())                # the hub row: calls only
            listed.assert_not_called()
            env.settings._stored['simplified_menus'] = False
            self.assertFalse(phone.open_waiting(True))
            listed.assert_not_called()
        self.assertEqual(self.spoken()[-1], 'No waiting call or text.')

    def test_the_chord_asks_for_the_list_fallback(self):
        import tyjokr_a11y_keys as keys
        with patch.object(keys, '_modal_active', False), patch.object(keys, '_editing_active', False), \
                patch.object(fixture.env.pump, 'post', return_value=True) as posted:
            keys._chord('phone')
        posted.assert_called_once_with(keys._open_waiting_checked)

    def test_the_hub_offers_the_phone_only_with_simplified_menus(self):
        names = []
        with patch.object(hub, '_window', side_effect=lambda title, text, rows: names.append([r[0] for r in rows])), \
                patch.object(hub.menu, '_raw', side_effect=lambda text: text):
            hub.open_hub()
            env.settings._stored['simplified_menus'] = False
            hub.open_hub()
        self.assertIn(lang.t('phone'), names[0])
        self.assertNotIn(lang.t('phone'), names[1])

    def test_terms_are_translated_without_dashes(self):
        for term in ('phone list instructions', 'phone group instructions', 'phone group count',
                     'back to phone', 'phone unavailable', 'phone empty', 'action queue full'):
            for language in ('en', 'pl'):
                text = lang._TRANSLATIONS[term][language]
                self.assertNotIn(chr(0x2014), text)
                self.assertNotIn(chr(0x2013), text)


class Dialog(object):
    def __init__(self, dialog_id=77, minimum=0, maximum=None, rows=(1, 2)):
        self.dialog_id, self.min_selectable = dialog_id, minimum
        if maximum is not None:
            self.max_selectable = maximum
        self.picker_rows = [types.SimpleNamespace(option_id=row) for row in rows]
        self.picked_results = [1]
        self.answered = []

    def on_picker_selected(self):
        self.answered.append(list(self.picked_results))


class StrictService(fixture.FakeDialogService):
    """Only the dialog service calls EA's own answer path uses."""

    def __getattr__(self, name):
        raise AssertionError('unexpected service use: ' + name)


class NativeHelperTests(Base):
    def setUp(self):
        super().setUp()
        self.service = StrictService()
        self.patches.append(patch.object(fixture.services, 'ui_dialog_service', lambda: self.service))
        self.patches[-1].start()

    def register(self, dialog):
        self.service._active_dialogs[dialog.dialog_id] = dialog
        return dialog

    def test_answers_through_pick_then_ok(self):
        dialog = self.register(Dialog())
        self.assertTrue(native.answer_picker(dialog, []))
        self.assertEqual(self.service.picks, [(77, [])])
        self.assertEqual(self.service.responses, [(77, fixture.OK)])
        self.assertEqual(dialog.answered, [[]])

    def test_refuses_a_gone_dialog_a_short_pick_and_a_foreign_row(self):
        self.assertFalse(native.answer_picker(Dialog(), []))              # never registered
        dialog = self.register(Dialog(minimum=1))
        self.assertFalse(native.answer_picker(dialog, []))
        self.assertFalse(native.answer_picker(dialog, [9]))               # EA's membership check
        self.assertEqual(self.service.responses, [])
        self.assertEqual(dialog.picked_results, [1])                      # left exactly as it was

    def test_a_policy_maximum_is_left_to_ea(self):
        dialog = self.register(Dialog(maximum=types.SimpleNamespace(get_max_selectable=lambda *a: 1)))
        self.assertTrue(native.answer_picker(dialog, [1, 2]))
        dialog = self.register(Dialog(dialog_id=78, maximum=1))
        self.assertFalse(native.answer_picker(dialog, [1, 2]))

    def test_refused_ok_reports_false(self):
        dialog = self.register(Dialog())
        self.service.refuse_ok = True
        self.assertFalse(native.answer_picker(dialog, [1]))


if __name__ == '__main__':
    unittest.main()
