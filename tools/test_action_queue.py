"""Control Alt Q and the accessibility menu's Action queue row list the
active Sim's interaction queue from the UIManager records EA's queue icons
are drawn from: running actions (and posture) first, then waiting ones in
order, each labelled with who chose it and whether it can be canceled.
Enter cancels an action the way interactions.cancel_si does, after looking
the Sim and action up again on the simulation thread.
"""
import sys
import types
import unittest
from unittest.mock import patch

import test_scanner_v5 as env
import tyjokr_a11y_hub as hub
import tyjokr_a11y_shortcuts as shortcuts

keys = env.keys
lang = env.lang
RUNNING, QUEUED = 1, 0
PB = types.SimpleNamespace(Sims_pb2=types.SimpleNamespace(
    IQ_QUEUED=QUEUED, IQ_RUNNING=RUNNING, Interaction=types.SimpleNamespace(POSTURE=3)))


class Interaction:
    def __init__(self, source='pie', cancelable=True, accepts=True):
        self.is_autonomous = source == 'autonomy'
        self.is_user_directed = source == 'pie'
        self.user_cancelable = cancelable
        self.accepts = accepts
        self.cancels = []

    def get_name(self):
        return 'fallback name'

    def cancel_user(self, cancel_reason_msg=None):
        self.cancels.append(cancel_reason_msg)
        return self.accepts


def info(interaction_id, name, state, cancelable=True, posture=False, canceled=False):
    return types.SimpleNamespace(interaction_id=interaction_id, display_name=name, ui_state=state,
                                 user_cancelable=cancelable, canceled=canceled,
                                 is_visual_type_posture=lambda: posture)


def native_action(ident, name, cancelable=True, posture=False, visible=True, finishing=False):
    action = Interaction(cancelable=cancelable)
    action.id = ident
    action.is_finishing = finishing
    action.visible_as_interaction = visible
    action.get_name = lambda: name
    action.get_interaction_queue_visual_type = lambda: (3 if posture else 1, None)
    return action


class NativeQueue(list):
    def __init__(self, running, waiting):
        super().__init__(waiting)
        self.running = running


class Sim:
    def __init__(self, infos, interactions, continuations=None, sim_id=7):
        self.id = sim_id
        self.ui_manager = types.SimpleNamespace(get_interactions_gen=lambda: iter(infos))
        self._interactions = interactions
        self._continuations = continuations or {}

    def find_interaction_by_id(self, interaction_id):
        return self._interactions.get(interaction_id)

    def find_continuation_by_id(self, interaction_id):
        return self._continuations.get(interaction_id)


class ActionQueueTests(unittest.TestCase):
    def setUp(self):
        env.settings._stored.clear()
        env.queue.clear()
        env.messages.clear()
        keys._enabled = True
        keys._modal_active = False
        keys._editing_active = False
        self.spoken = []
        for target, name, value in (
                (env.speech, 'speak', lambda text, *a, **k: self.spoken.append(text)),
                (hub.menu, '_raw', lambda text: text),
                (lang, '_locale_lang', 'en')):
            patcher = patch.object(target, name, value) if name == '_locale_lang' else \
                patch.object(target, name, side_effect=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.windows = []
        hub._dialog_id = None
        self.selections = []
        def record_window(title, text, rows, **options):
            self.windows.append((title, rows))
            self.selections.append(options.get('selected_index'))
            return True
        window = patch.object(hub, '_window', side_effect=record_window)
        window.start()
        self.addCleanup(window.stop)
        self.sim = None
        self.services = types.SimpleNamespace(get_active_sim=lambda: self.sim)
        modules = patch.dict(sys.modules, {'services': self.services, 'protocolbuffers': PB,
                                           'protocolbuffers.Sims_pb2': PB.Sims_pb2})
        modules.start()
        self.addCleanup(modules.stop)

    def rows(self):
        self.assertEqual(len(self.windows), 1)
        self.assertEqual(self.windows[0][0], 'action queue')
        return self.windows[0][1]

    def test_quick_cancel_current_prefers_primary_and_all_includes_waiting(self):
        actions = {i: Interaction(cancelable=i != 4) for i in range(1, 6)}
        self.sim = Sim([info(1, 'Sit', RUNNING, posture=True), info(2, 'Talk', RUNNING),
                        info(3, 'TV', RUNNING), info(4, 'Fixed', QUEUED, cancelable=False),
                        info(5, 'Eat', QUEUED)], actions)
        self.sim.queue = types.SimpleNamespace(running=types.SimpleNamespace(id=3))
        self.assertTrue(hub.cancel_from_scanner(False))
        self.assertEqual([n for n, a in actions.items() if a.cancels], [3])
        self.sim.queue.running = types.SimpleNamespace(id=1)
        self.assertTrue(hub.cancel_from_scanner(False))
        self.assertTrue(actions[2].cancels)
        self.assertTrue(hub.cancel_from_scanner(True))
        self.assertEqual([len(a.cancels) for a in actions.values()], [1, 2, 2, 0, 1])

    def test_no_icons_falls_back_to_live_actions_once_and_ignores_posture(self):
        class Queue(list):
            pass
        actions = {i: Interaction() for i in range(1, 6)}
        for i, action in actions.items():
            action.id = i
            action.visible_as_interaction = True
            action.is_finishing = i == 4
            action.get_interaction_queue_visual_type = lambda n=i: ('posture' if n == 1 else 'simple', None)
        icons = []
        self.sim = Sim(icons, actions)
        self.sim.queue = Queue([actions[2], actions[3], actions[4]])
        self.sim.queue.running = actions[1]
        self.sim.si_state = types.SimpleNamespace(sis_actor_gen=lambda: iter((actions[1], actions[2])))
        with patch.object(PB.Sims_pb2, 'Interaction', types.SimpleNamespace(POSTURE='posture'), create=True):
            self.assertTrue(hub.cancel_from_scanner(False))
            self.assertEqual([len(a.cancels) for a in actions.values()], [0, 1, 0, 0, 0])
            # An already-canceled icon must not hide other activities or
            # resurrect the corresponding action before the Sim drops it.
            icons.append(info(5, 'Old', QUEUED, canceled=True))
            self.sim.queue.append(actions[5])
            self.assertTrue(hub.cancel_from_scanner(True))
            self.assertEqual([len(a.cancels) for a in actions.values()], [1, 2, 1, 0, 0])

    def test_quick_cancel_reports_waiting_only_and_no_sim(self):
        self.sim = Sim([info(1, 'Wait', QUEUED)], {1: Interaction()})
        self.assertFalse(hub.cancel_from_scanner(False))
        self.assertEqual(self.spoken[-1], lang.t('no current action'))
        self.sim = None
        self.assertFalse(hub.cancel_from_scanner(True))
        self.assertEqual(self.spoken[-1], lang.t('load a household first'))

    def test_q_is_the_queue_chord_and_is_described(self):
        self.assertEqual(keys.CHORDS[0x51], ('queue', False))
        self.assertEqual(keys.CHORD_NAMES[0x51], 'Q')
        self.assertIn('action queue', shortcuts.chord_label('queue'))
        rows = shortcuts.sections(numpad=False)[1][1]
        self.assertTrue(any(row.startswith('Control + Alt + Q:') for row in rows), rows)

    def test_the_chord_opens_the_queue_on_the_pump_and_respects_owners(self):
        with patch.object(hub, 'action_queue', return_value=True) as opened:
            keys._chord('queue')
            env.drain()
            self.assertEqual(opened.call_count, 1)
            keys.apply_modal_state('101', 'context')      # a dialog owns input
            keys._chord('queue')
            env.drain()
            self.assertEqual(opened.call_count, 1)
            self.assertEqual(self.spoken, [lang.t('close the dialog first')])
            keys.apply_modal_state('01', 'modalstate')    # typing
            keys._chord('queue')
            env.drain()
            self.assertEqual(opened.call_count, 1)
            # A dialog opening after the press, before the pump turn.
            keys.apply_modal_state('00', 'modalstate')
            keys._chord('queue')
            keys.apply_modal_state('101', 'context')
            env.drain()
            self.assertEqual(opened.call_count, 1)

    def test_rows_follow_the_queue_icons(self):
        user, auto, wait1, wait2 = Interaction('pie'), Interaction('autonomy'), Interaction('autonomy'), Interaction('pie')
        sit = Interaction('script', cancelable=False)
        self.sim = Sim([info(3, 'Eat', QUEUED), info(4, 'Nap', QUEUED),
                        info(1, 'Chat', RUNNING), info(2, 'Sit', RUNNING, cancelable=False, posture=True),
                        info(5, 'Gone', QUEUED, canceled=True), info(6, 'Watch TV', RUNNING)],
                       {1: user, 2: sit, 3: wait1, 4: wait2, 6: auto})
        self.assertTrue(hub.action_queue())
        rows = self.rows()
        self.assertEqual([row[0] for row in rows], ['Cancel all actions', 'Chat', 'Sit', 'Watch TV', 'Eat', 'Nap'])
        details = dict((row[0], row[1]) for row in rows)
        self.assertEqual(details['Chat'], 'Doing now. Chosen by you. Enter cancels')
        self.assertEqual(details['Sit'], 'Current posture. This action cannot be canceled.')
        self.assertEqual(details['Watch TV'], 'Doing now. Chosen by the Sim. Enter cancels')
        self.assertEqual(details['Eat'], 'Waiting, 1 of 2. Chosen by the Sim. Enter cancels')
        self.assertEqual(details['Nap'], 'Waiting, 2 of 2. Chosen by you. Enter cancels')

    def test_enter_cancels_after_looking_everything_up_again(self):
        chat, nap = Interaction('pie'), Interaction('autonomy')
        self.sim = Sim([info(1, 'Chat', RUNNING), info(4, 'Nap', QUEUED)], {1: chat}, {4: nap})
        hub.action_queue()
        rows = dict((row[0], row[2]) for row in self.rows())
        self.assertTrue(rows['Nap']())                  # a continuation is found like cancel_si finds it
        self.assertEqual(nap.cancels, ['TS4 Access action queue'])
        self.assertEqual(self.spoken, [lang.t('action canceled')])
        self.spoken.clear()
        self.sim._interactions.pop(1)                   # finished while the menu was open
        self.assertFalse(rows['Chat']())
        self.assertEqual(self.spoken, [lang.t('action already finished')])
        self.spoken.clear()
        self.sim = Sim([], {1: chat}, sim_id=8)        # the player switched Sims
        self.assertFalse(rows['Chat']())
        self.assertEqual(chat.cancels, [])
        self.assertEqual(self.spoken, [lang.t('sim unavailable')])

    def test_missing_icons_show_native_actions_and_still_refresh_after_cancel(self):
        watch = native_action(1, 'Watch TV')
        sit = native_action(2, 'Sit', cancelable=False, posture=True)
        eat = native_action(3, 'Eat')
        self.sim = Sim([], {1: watch, 2: sit, 3: eat})
        self.sim.queue = NativeQueue(watch, (watch, eat))
        self.sim.si_state = types.SimpleNamespace(sis_actor_gen=lambda: iter((watch, sit)))
        self.assertTrue(hub.action_queue())
        rows = self.rows()
        self.assertEqual([row[0] for row in rows], ['Cancel all actions', 'Watch TV', 'Sit', 'Eat'])
        self.assertEqual(rows[1][1], 'Doing now. Chosen by you. Enter cancels')
        self.assertEqual(rows[2][1], 'Current posture. Chosen by you. This action cannot be canceled.')
        self.assertEqual(rows[3][1], 'Waiting, 1 of 1. Chosen by you. Enter cancels')
        self.assertTrue(rows[1][2]())
        self.assertEqual(watch.cancels, ['TS4 Access action queue'])
        self.assertEqual([row[0] for row in self.windows[-1][1]], ['Sit', 'Eat'])
        self.assertEqual(self.selections[-1], 0)

    def test_native_fallback_excludes_canceled_finishing_and_hidden_actions(self):
        actions = [native_action(1, 'Already canceled'), native_action(2, 'Finishing', finishing=True),
                   native_action(3, 'Hidden', visible=False, cancelable=False),
                   native_action(4, 'Cancelable', visible=False),
                   native_action(5, 'Visible', cancelable=False)]
        self.sim = Sim([info(1, 'Canceled icon', RUNNING, canceled=True)],
                       {action.id: action for action in actions})
        self.sim.queue = NativeQueue(actions[0], actions)
        self.sim.si_state = types.SimpleNamespace(sis_actor_gen=lambda: iter((None,) + tuple(actions)))
        self.assertTrue(hub.action_queue())
        self.assertEqual([row[0] for row in self.rows()], ['Cancelable', 'Visible'])
        self.assertEqual([entry[0].interaction_id for entry in hub._queue_entries(self.sim)], [4, 5])

    def test_existing_icons_remain_authoritative_over_native_fallback(self):
        watch = native_action(1, 'Native title')
        self.sim = Sim([info(1, 'Icon title', QUEUED)], {1: watch})
        self.sim.queue = NativeQueue(watch, (native_action(2, 'Not in icons'),))
        def unused_running_actions():
            raise AssertionError('Native fallback must not run while icons exist')
        self.sim.si_state = types.SimpleNamespace(sis_actor_gen=unused_running_actions)
        self.assertTrue(hub.action_queue())
        self.assertEqual([row[0] for row in self.rows()], ['Icon title'])
        self.assertEqual(self.rows()[0][1], 'Waiting, 1 of 1. Chosen by you. Enter cancels')

    def test_cancel_all_and_refusals(self):
        a, b, c = Interaction('pie'), Interaction('autonomy', accepts=False), Interaction('pie', cancelable=False)
        self.sim = Sim([info(1, 'A', RUNNING), info(2, 'B', QUEUED), info(3, 'C', QUEUED, cancelable=False)],
                       {1: a, 2: b, 3: c})
        hub.action_queue()
        cancel_all = self.rows()[0]
        self.assertEqual(cancel_all[0], 'Cancel all actions')
        self.assertTrue(cancel_all[2]())
        self.assertEqual((len(a.cancels), len(b.cancels), len(c.cancels)), (1, 1, 0))
        self.assertEqual(self.spoken, [lang.t('action canceled')])
        self.spoken.clear()
        self.assertFalse(hub.cancel_actions(7, (3,)))
        self.assertEqual(self.spoken, [lang.t('queue cannot cancel')])

    def test_empty_queue_and_no_sim(self):
        self.sim = Sim([], {})
        hub.action_queue()
        self.assertEqual([row[0] for row in self.rows()], [lang.t('queue empty')])
        self.sim = None
        self.assertFalse(hub.action_queue())
        self.assertEqual(self.spoken, [lang.t('load a household first')])

    def test_repeated_enter_refreshes_the_list_and_eventually_shows_empty(self):
        actions = [Interaction() for _ in range(3)]
        self.sim = Sim([info(i, name, QUEUED) for i, name in enumerate('ABC')], dict(enumerate(actions)))
        hub.action_queue()
        self.windows[-1][1][2][2]()  # B. The UI manager still lists its stale icon.
        rows = self.windows[-1][1]
        self.assertEqual([r[0] for r in rows], ['A', 'C', 'Cancel all actions'])
        self.assertEqual(self.selections[-1], 1)
        rows[-1][2]()
        self.assertEqual([r[0] for r in self.windows[-1][1]], [lang.t('queue empty')])
        self.windows[-1][1][0][2]()
        self.assertEqual(self.windows[-1][0], 'action queue')
        self.assertEqual([len(action.cancels) for action in actions], [1, 1, 1])

    def test_refused_action_stays_and_other_dialog_is_not_replaced(self):
        action = Interaction(accepts=False)
        self.sim = Sim([info(1, 'Nap', RUNNING)], {1: action})
        hub.action_queue()
        self.assertFalse(self.rows()[0][2]())
        self.assertEqual([r[0] for r in self.windows[-1][1]], ['Nap'])
        hub._dialog_id = 17
        self.windows[-1][1][0][2]()
        self.assertEqual(len(self.windows), 2)
        self.assertEqual(len(action.cancels), 1)

    def test_the_accessibility_menu_offers_the_queue(self):
        self.windows.clear()
        with patch.object(hub, 'action_queue', return_value=True) as opened:
            hub.open_hub()
            next(row[2] for row in self.windows[0][1] if row[0] == lang.t('now'))()
            labels = [row[0] for row in self.windows[-1][1]]
            self.assertIn(lang.t('action queue'), labels)
            self.assertNotIn(lang.t('current action'), labels)
            self.windows[-1][1][labels.index(lang.t('action queue'))][2]()
        self.assertEqual(opened.call_count, 1)

    def test_terms_exist_in_english_and_polish(self):
        for term in ('action queue', 'action queue instructions', 'queue running', 'queue posture',
                     'queue waiting', 'queue autonomous', 'queue chosen by you', 'queue enter cancels',
                     'queue cannot cancel', 'cancel all actions', 'queue empty', 'action canceled',
                     'action already finished', 'close the dialog first'):
            entry = lang._TRANSLATIONS[term]
            self.assertEqual(set(entry), {'en', 'pl'}, term)
        self.assertEqual(lang._TRANSLATIONS['queue waiting']['pl'].count('{}'), 2)


if __name__ == '__main__':
    unittest.main()
