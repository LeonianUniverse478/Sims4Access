"""Festivals (2026-11-25): the Accessibility menu's Festivals row lists the
scheduled and running festivals; one opens Travel, when, where and each
advertised activity; Travel does what the flyer's Travel button does
(drama.travel_to_event_zone: travel_to_destination), with the flyer's
reasons when it cannot. The drama scheduler and nodes are stand-ins here."""
import sys
import types
import unittest
from unittest.mock import patch

import test_scanner_v5 as env
import tyjokr_a11y_hub as hub
import tyjokr_a11y_festivals as festivals

lang = env.lang
FESTIVAL, OTHER = 'FESTIVAL', 'OTHER'


class Time(object):
    def __init__(self, hours):
        self.hours = hours

    def __sub__(self, other):
        return types.SimpleNamespace(in_hours=lambda: self.hours - other.hours)

    def absolute_ticks(self):
        return int(self.hours * 1000)


class Node(object):
    def __init__(self, guid, name, start, end, pre=False, on_street=False, lot=7,
                 activities=(('Eat curry', 'Try every stall.'),)):
        self.guid64 = guid
        self.drama_node_type = FESTIVAL
        self.festival_dynamic_sign_info = types.SimpleNamespace(
            festival_name=name, festival_time='Sat 10 to 22', travel_to_festival_text=None,
            activity_info=[types.SimpleNamespace(activity_name=a, activity_description=d) for a, d in activities])
        self._start, self._end, self._pre, self._street, self._lot = start, end, pre, on_street, lot

    def get_calendar_start_time(self):
        return Time(self._start)

    def get_calendar_end_time(self):
        return Time(self._end)

    def is_during_pre_festival(self):
        return self._pre

    def is_on_festival_street(self):
        return self._street

    def get_destination_lot_id(self):
        return None if self._street else self._lot

    def get_travel_interaction(self):
        return 'go_to_festival'

    def get_travel_lot_id(self):
        return self._lot


class Scheduler(object):
    def __init__(self, scheduled, running):
        self.scheduled, self.running = scheduled, running

    def all_nodes_gen(self):
        return iter(self.scheduled + self.running)

    def active_nodes_gen(self):
        return iter(self.running)


class FestivalTests(unittest.TestCase):
    def setUp(self):
        self.spoken, self.windows, self.pushed = [], [], []
        self.spice = Node(1, 'Spice Festival', start=10, end=20)
        self.geek = Node(2, 'GeekCon', start=60, end=70)
        self.other = Node(3, 'Not a festival', start=5, end=6)
        self.other.drama_node_type = OTHER
        self.scheduler = Scheduler([self.geek, self.other], [self.spice])
        self.vacation = False
        self.push_ok = True
        sim = types.SimpleNamespace(push_super_affordance=lambda i, t, c: self.pushed.append((i, c.pick.lot_id)) or self.push_ok)
        info = types.SimpleNamespace(is_in_travel_group=lambda: self.vacation,
                                     get_sim_instance=lambda allow_hidden_flags=None: sim)
        persistence = types.SimpleNamespace(resolve_lot_id_into_zone_id=lambda lot, ignore_neighborhood_id=True: lot * 10,
                                            get_zone_proto_buff=lambda zone: types.SimpleNamespace(name='Spice Market'))
        services = types.SimpleNamespace(drama_scheduler_service=lambda: self.scheduler,
                                         time_service=lambda: types.SimpleNamespace(sim_now=Time(12)),
                                         active_sim_info=lambda: info,
                                         get_persistence_service=lambda: persistence)

        class Context(object):
            SOURCE_SCRIPT_WITH_USER_INTENT = 'user'

            def __init__(self, sim, source, priority, insert_strategy=None, pick=None):
                self.pick = pick
        game = {
            'services': services,
            'drama_scheduler': types.ModuleType('drama_scheduler'),
            'drama_scheduler.drama_node_types': types.SimpleNamespace(DramaNodeType=types.SimpleNamespace(FESTIVAL=FESTIVAL)),
            'objects': types.SimpleNamespace(ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED=0),
            'server': types.ModuleType('server'),
            'server.pick_info': types.SimpleNamespace(PickInfo=lambda **k: types.SimpleNamespace(**k),
                                                      PickType=types.SimpleNamespace(PICK_TERRAIN=1)),
            'interactions': types.ModuleType('interactions'),
            'interactions.context': types.SimpleNamespace(InteractionContext=Context,
                                                          QueueInsertStrategy=types.SimpleNamespace(NEXT=1)),
            'interactions.priority': types.SimpleNamespace(Priority=types.SimpleNamespace(High=2)),
        }
        for item in (patch.dict(sys.modules, game),
                     patch.object(env.speech, 'speak', side_effect=lambda text, *a, **k: self.spoken.append(text)),
                     patch.object(festivals, '_raw', side_effect=lambda text: text),
                     patch.object(festivals, '_lines', side_effect=lambda *p: ' | '.join(x for x in p if x)),
                     patch.object(hub, '_window', side_effect=lambda title, text, rows, localized_title=None, selected_index=None:
                                  self.windows.append((title, rows, localized_title, selected_index)) or True),
                     patch.object(lang, '_locale_lang', 'en')):
            item.start()
            self.addCleanup(item.stop)

    def test_lists_festivals_running_first(self):
        self.assertTrue(festivals.open_festivals())
        title, rows, _, _ = self.windows[-1]
        self.assertEqual(title, 'festivals')
        self.assertEqual([r[0] for r in rows], ['Spice Festival', 'GeekCon'], 'running first; other drama nodes left out')
        background = Node(4, None, start=11, end=12)
        background.festival_dynamic_sign_info = None
        self.scheduler.running.append(background)
        festivals.open_festivals()
        self.assertEqual([r[0] for r in self.windows[-1][1]], ['Spice Festival', 'GeekCon'],
                         'festival nodes without a flyer (Life & Death background ones) are left out')
        self.assertEqual(rows[0][1], 'On now, ends in about 8 hours. | Sat 10 to 22')
        self.assertEqual(rows[1][1], 'Starts in about 2 days. | Sat 10 to 22')

    def test_no_festivals(self):
        self.scheduler.scheduled, self.scheduler.running = [], []
        self.assertFalse(festivals.open_festivals())
        self.assertEqual(self.spoken, ['No festivals are coming up.'])

    def test_one_festival_reads_like_the_flyer(self):
        festivals.open_festival(1)
        title, rows, name, _ = self.windows[-1]
        self.assertEqual(name, 'Spice Festival')
        self.assertEqual([r[0] for r in rows], ['Travel to the festival', 'When', 'Where', 'Eat curry', 'Back to festivals'])
        self.assertEqual(rows[0][1], 'Your Sim travels there now.')
        self.assertEqual(rows[2][1], 'Spice Market')
        self.assertEqual(rows[3][1], 'Try every stall.')
        rows[3][2]()
        self.assertEqual(self.windows[-1][3], 3, 'Enter on a description row keeps the place')

    def test_travel_pushes_the_festival_travel_on_the_active_sim(self):
        self.assertTrue(festivals.travel(1))
        self.assertEqual(self.pushed, [('go_to_festival', 7)])
        self.assertEqual(self.spoken, ['Travelling to the festival.'])

    def test_travel_gives_the_flyers_reasons(self):
        self.assertFalse(festivals.travel(2))
        self.spice._pre = True
        self.assertFalse(festivals.travel(1))
        self.spice._pre, self.spice._street = False, True
        self.assertFalse(festivals.travel(1))
        self.spice._street, self.vacation = False, True
        self.assertFalse(festivals.travel(1))
        self.assertEqual(self.spoken, ["The festival hasn't started yet.", "The festival hasn't started yet.",
                                       "You're already at the festival.",
                                       "You can't travel to a festival while on vacation."])
        self.assertEqual(self.pushed, [])

    def test_refused_and_ended(self):
        self.push_ok = False
        self.assertFalse(festivals.travel(1))
        self.assertFalse(festivals.travel(99))
        self.assertEqual(self.spoken, ["The game wouldn't send your Sim to the festival.",
                                       'That festival is no longer on the calendar.'])

    def test_the_chord(self):
        keys = env.keys
        self.assertEqual(keys.CHORDS[0x41], ('festivals', False))
        self.assertEqual(keys.CHORD_NAMES[0x41], 'A')
        import tyjokr_a11y_shortcuts as shortcuts
        self.assertIn('festivals', shortcuts.chord_label('festivals'))
        keys._enabled = True
        keys._modal_active = keys._editing_active = False
        env.queue.clear()
        with patch.object(festivals, 'open_festivals', return_value=True) as opened:
            keys._chord('festivals')
            env.drain()
            self.assertEqual(opened.call_count, 1)
            keys._modal_active = True
            keys._chord('festivals')
            env.drain()
            self.assertEqual(opened.call_count, 1, 'not over an open dialog')
        keys._modal_active = False

    def test_in_the_places_group(self):
        with open(hub.__file__, encoding='utf-8') as fh:
            source = fh.read()
        self.assertIn("('festivals', festivals.open_festivals)", source)
        for key in ('festivals', 'festival not started', 'festival travelling', 'back to festivals'):
            self.assertIn('pl', lang._TRANSLATIONS[key], key)

    def test_read_flyer_opens_the_festival_menu(self):
        flyers = []

        class FestivalDramaNode(object):
            guid64 = 1

            @classmethod
            def show_festival_info(cls):
                flyers.append(cls.guid64)
        module = types.SimpleNamespace(FestivalDramaNode=FestivalDramaNode)
        with patch.dict(sys.modules, {'drama_scheduler.festival_drama_node': module}):
            festivals._install()
            festivals._install()
        FestivalDramaNode.show_festival_info()
        self.assertEqual(flyers, [], 'a calendar festival opens the menu, not the flyer')
        self.assertEqual(self.windows[-1][2], 'Spice Festival')
        FestivalDramaNode.guid64 = 42
        FestivalDramaNode.show_festival_info()
        self.assertEqual(flyers, [42], 'a festival that is not on the calendar keeps the game flyer')
        self.assertEqual(self.spoken, [])


if __name__ == '__main__':
    unittest.main()
