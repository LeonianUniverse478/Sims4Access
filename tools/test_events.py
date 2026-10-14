"""Ctrl+Alt+V and the accessibility menu's Events row: the user-facing
situations the game shows, and for one of them: send all guests home and end
it, end it, or send all guests home. Ending uses EA's order
(pre_destroy_situation_by_id, then destroy_situation_by_id); guests leave
through SituationManager.make_sim_leave; the household is never sent away.
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


def sim(name, household):
    return types.SimpleNamespace(name=name, sim_info=types.SimpleNamespace(household_id=household, is_selectable=False))


class Manager(object):
    def __init__(self, situations):
        self.situations = {s.id: s for s in situations}
        self.calls = []

    def get_user_facing_situations_gen(self):
        return iter(list(self.situations.values()))

    def get(self, situation_id):
        return self.situations.get(situation_id)

    def make_sim_leave(self, who):
        self.calls.append(('leave', who.name))

    def pre_destroy_situation_by_id(self, situation_id):
        self.calls.append(('pre_destroy', situation_id))

    def destroy_situation_by_id(self, situation_id):
        self.calls.append(('destroy', situation_id))
        self.situations.pop(situation_id, None)


def party(situation_id=11, minutes=90):
    members = [sim('Host', 1), sim('Guest A', 2), sim('Guest B', 3)]
    return types.SimpleNamespace(id=situation_id, is_user_facing=True, display_name='House Party',
                                 all_sims_in_situation_gen=lambda: iter(members),
                                 _get_remaining_time_in_minutes=lambda: minutes)


class EventTests(unittest.TestCase):
    def setUp(self):
        env.queue.clear()
        keys._enabled = True
        keys._modal_active = keys._editing_active = False
        self.spoken, self.windows = [], []
        self.manager = Manager([party()])
        services = types.SimpleNamespace(get_zone_situation_manager=lambda: self.manager,
                                         active_household=lambda: types.SimpleNamespace(id=1))
        for item in (patch.dict(sys.modules, {'services': services}),
                     patch.object(env.speech, 'speak', side_effect=lambda text, *a, **k: self.spoken.append(text)),
                     patch.object(hub.menu, '_raw', side_effect=lambda text: text),
                     patch.object(hub, '_window', side_effect=lambda title, text, rows, localized_title=None:
                                  self.windows.append((title, rows, localized_title)) or True),
                     patch.object(lang, '_locale_lang', 'en')):
            item.start()
            self.addCleanup(item.stop)

    def rows(self):
        return dict((row[0], row[2]) for row in self.windows[-1][1]), [row[1] for row in self.windows[-1][1]]

    def test_the_chord_and_the_menu_row(self):
        self.assertEqual(keys.CHORDS[0x56], ('events', False))
        self.assertIn('events', shortcuts.chord_label('events'))
        with patch.object(hub, 'events_window', return_value=True) as opened:
            keys._chord('events')
            env.drain()
            self.assertEqual(opened.call_count, 1)
            keys.apply_modal_state('101', 'context')
            keys._chord('events')
            env.drain()
            self.assertEqual(opened.call_count, 1)
            self.assertEqual(self.spoken[-1], lang.t('close the dialog first'))
        self.windows.clear()
        with patch.object(hub, 'events_window', return_value=True):
            hub.open_hub()
        self.assertIn(lang.t('events'), [row[0] for row in self.windows[-1][1]])

    def test_events_are_listed_with_guests_and_time_left(self):
        self.assertTrue(hub.events_window())
        callbacks, details = self.rows()
        self.assertEqual(list(callbacks), ['House Party'])
        self.assertEqual(details, ['Guests: 2. 90 minutes left'])

    def test_no_events(self):
        self.manager.situations.clear()
        self.assertFalse(hub.events_window())
        self.assertEqual(self.spoken, [lang.t('no events')])

    def test_send_everyone_home_and_end(self):
        hub.events_window()
        self.rows()[0]['House Party']()
        callbacks, _ = self.rows()
        self.assertEqual(self.windows[-1][2], 'House Party')
        callbacks['Send all guests home and end the event']()
        self.assertEqual(self.manager.calls, [('leave', 'Guest A'), ('leave', 'Guest B'),
                                              ('pre_destroy', 11), ('destroy', 11)])
        self.assertEqual(self.spoken[-1], 'Guests sent home: 2. The event has ended.')

    def test_end_only_and_send_home_only(self):
        hub.event_actions(11)
        self.rows()[0]['Send all guests home']()
        self.assertEqual(self.manager.calls, [('leave', 'Guest A'), ('leave', 'Guest B')])
        self.assertEqual(self.spoken[-1], 'Guests sent home: 2.')
        self.manager.calls.clear()
        hub.event_actions(11)
        self.rows()[0]['End the event']()
        self.assertEqual(self.manager.calls, [('pre_destroy', 11), ('destroy', 11)])
        self.assertEqual(self.spoken[-1], 'The event has ended.')

    def test_an_event_that_ended_meanwhile(self):
        hub.event_actions(11)
        choose = self.rows()[0]['End the event']
        self.manager.situations.clear()
        self.assertFalse(choose())
        self.assertEqual(self.spoken[-1], lang.t('event already over'))
        self.assertEqual(self.manager.calls, [])

    def test_a_failed_end_is_reported(self):
        def broken(situation_id):
            raise RuntimeError('native')
        self.manager.destroy_situation_by_id = broken
        with patch.object(env.speech, 'log_line', lambda *a, **k: None):
            hub.end_event(11, send_home=False, end=True)
        self.assertEqual(self.spoken[-1], lang.t('event not ended'))

    def test_terms_exist_in_english_and_polish(self):
        for term in ('events', 'events instructions', 'event actions instructions', 'event guests',
                     'event minutes left', 'no events', 'event already over', 'send guests home and end event',
                     'end event', 'send guests home', 'guests sent home', 'event ended', 'event not ended'):
            entry = lang._TRANSLATIONS[term]
            self.assertEqual(set(entry), {'en', 'pl'}, term)
            self.assertEqual(entry['en'].count('{}'), entry['pl'].count('{}'), term)


if __name__ == '__main__':
    unittest.main()
