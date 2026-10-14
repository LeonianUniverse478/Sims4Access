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
PB = types.SimpleNamespace(Sims_pb2=types.SimpleNamespace(IQ_QUEUED=QUEUED, IQ_RUNNING=RUNNING))


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
        window = patch.object(hub, '_window', side_effect=lambda title, text, rows: self.windows.append((title, rows)) or True)
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

    def test_the_accessibility_menu_offers_the_queue(self):
        self.windows.clear()
        with patch.object(hub, 'action_queue', return_value=True) as opened:
            hub.open_hub()
            labels = [row[0] for row in self.windows[0][1]]
            self.assertIn(lang.t('action queue'), labels)
            self.assertNotIn(lang.t('current action'), labels)
            self.windows[0][1][labels.index(lang.t('action queue'))][2]()
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
