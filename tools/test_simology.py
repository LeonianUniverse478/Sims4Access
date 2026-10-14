"""The accessibility menu's Milestones (EP13) and Character values (GP05)
rows. Milestones mirror EA's panel: only milestones the tracker's
is_milestone_visible accepts, plus archived ones, grouped by
DEVELOPMENTAL_MILESTONE_CATEGORIES and ordered by ui_sort_order. Character
values are the LifeSkillStatistic entries in the commodity tracker, with the
value on its tuned scale and the trait its range gives at age up.
"""
import enum
import sys
import types
import unittest
from unittest.mock import patch

import test_scanner_v5 as env
import tyjokr_a11y_hub as hub
import tyjokr_a11y_simology as simology

lang = env.lang


class States(enum.Enum):
    LOCKED = 0
    ACTIVE = 1
    UNLOCKED = 2


class Age(enum.IntEnum):
    BABY = 1
    TODDLER = 2
    CHILD = 4
    TEEN = 8
    YOUNGADULT = 16
    ADULT = 32
    ELDER = 64
    INFANT = 128


class LifeSkillStatistic(object):
    pass


class Milestone(types.SimpleNamespace):
    __hash__ = object.__hash__
    __eq__ = object.__eq__


def milestone(name, category, order, hint=None, done_text=None, repeatable=False):
    primary = types.SimpleNamespace(hint_text=hint) if hint else None
    return Milestone(name=name, category=category, ui_sort_order=order,
                                 is_primary_milestone=primary, unlocked_text_no_context=done_text,
                                 repeatable=repeatable)


def data(state, age=None, previous=()):
    return types.SimpleNamespace(state=state, age_completed=age,
                                 previous_goals=dict((i, None) for i in previous))


class Tracker(object):
    def __init__(self, active, archived, hidden=()):
        self._active_milestones_data = active
        self._archived_milestones_data = archived
        self.hidden = hidden

    def is_milestone_visible(self, item, resolver):
        return item not in self.hidden


def value_type(name, low, high, ranges, description):
    stat_type = type(name, (LifeSkillStatistic,), {})
    stat_type.display_name = name
    stat_type.display_description = description
    stat_type.min_value_tuning = low
    stat_type.max_value_tuning = high
    stat_type.trait_on_age_up_list = ranges
    return stat_type


def value_range(low, high, trait=None, age=None):
    info = None
    if trait is not None:
        info = types.SimpleNamespace(life_skill_trait=types.SimpleNamespace(display_name=lambda sim: trait),
                                     age_to_apply_trait=age)
    return types.SimpleNamespace(life_skill_range=types.SimpleNamespace(lower_bound=low, upper_bound=high),
                                 age_up_info=info)


class SimologyTests(unittest.TestCase):
    def setUp(self):
        env.queue.clear()
        self.spoken, self.windows = [], []
        walk = milestone('First Steps', 1, 2, hint='Help them practice walking.', done_text='Took the first steps.')
        talk = milestone('First Words', 1, 1, done_text='Said a first word.')
        potty = milestone('Potty Trained', 1, 3, hint='Practice with the potty.')
        secret = milestone('Secret', 1, 4, hint='Hidden')
        crush = milestone('First Crush', 2, 1, done_text='Had a crush.', repeatable=True)
        old = milestone('Rolled Over', 3, 1, done_text='Rolled over.')
        self.tracker = Tracker({walk: data(States.UNLOCKED, Age.TODDLER),
                                talk: data(States.UNLOCKED, Age.INFANT),
                                potty: data(States.ACTIVE),
                                secret: data(States.LOCKED),
                                crush: data(States.UNLOCKED, Age.TEEN, previous=(7, 8))},
                               {old: data(States.UNLOCKED, Age.INFANT)}, hidden=(secret,))
        manners = value_type('Manners', -100, 100,
                             [value_range(-100, -50, 'Rude', Age.YOUNGADULT), value_range(-49, 49),
                              value_range(50, 100, 'Considerate', Age.YOUNGADULT)], 'How polite they are.')
        empathy = value_type('Empathy', -100, 100, [value_range(-100, 100)], 'How they feel for others.')
        stats = [manners(), empathy(), types.SimpleNamespace(get_value=lambda: 3)]
        stats[0].get_value = lambda: 62.4
        stats[1].get_value = lambda: -10
        self.info = types.SimpleNamespace(sim_id=5, first_name='Ana', last_name='Lee',
                                          developmental_milestone_tracker=self.tracker,
                                          commodity_tracker=stats)
        info = self.info
        client = types.SimpleNamespace(active_sim_info=info)
        services = types.SimpleNamespace(client_manager=lambda: types.SimpleNamespace(get_first_client=lambda: client),
                                         sim_info_manager=lambda: types.SimpleNamespace(get=lambda i: info if i == 5 else None))
        categories = {1: types.SimpleNamespace(name='Motor and Speech'), 2: types.SimpleNamespace(name='Love'),
                      3: types.SimpleNamespace(name='Infant')}
        milestone_module = types.SimpleNamespace(
            DevelopmentalMilestone=types.SimpleNamespace(DEVELOPMENTAL_MILESTONE_CATEGORIES=categories))
        modules = {
            'services': services,
            'event_testing': types.ModuleType('event_testing'),
            'event_testing.resolver': types.SimpleNamespace(SingleSimResolver=lambda who: who),
            'developmental_milestones': types.ModuleType('developmental_milestones'),
            'developmental_milestones.developmental_milestone': milestone_module,
            'developmental_milestones.developmental_milestone_enums':
                types.SimpleNamespace(DevelopmentalMilestoneStates=States),
            'sims.sim_info_types': types.SimpleNamespace(Age=Age),
            'statistics': types.ModuleType('statistics'),
            'statistics.life_skill_statistic': types.SimpleNamespace(LifeSkillStatistic=LifeSkillStatistic),
            'sims4.localization': types.SimpleNamespace(LocalizationHelperTuning=types.SimpleNamespace(
                get_new_line_separated_strings=lambda *parts: ' | '.join(parts))),
        }
        for item in (patch.dict(sys.modules, modules),
                     patch.object(env.speech, 'speak', side_effect=lambda text, *a, **k: self.spoken.append(text)),
                     patch.object(simology.menu, '_raw', side_effect=lambda text: text),
                     patch.object(hub.menu, '_raw', side_effect=lambda text: text),
                     patch.object(hub, '_window', side_effect=lambda title, text, rows, localized_title=None:
                                  self.windows.append((title, text, rows, localized_title)) or True),
                     patch.object(lang, '_locale_lang', 'en')):
            item.start()
            self.addCleanup(item.stop)

    def rows(self):
        return [(row[0], row[1]) for row in self.windows[-1][2]]

    def test_menu_rows_follow_installed_packs(self):
        for ep13, gp05 in ((True, True), (False, False)):
            self.windows.clear()
            with patch.object(simology, 'milestones_available', return_value=ep13), \
                    patch.object(simology, 'values_available', return_value=gp05):
                hub.open_hub()
            labels = [row[0] for row in self.windows[-1][2]]
            self.assertEqual(lang.t('milestones') in labels, ep13)
            self.assertEqual(lang.t('character values') in labels, gp05)
        self.assertEqual(labels.index(lang.t('businesses')) + 1, labels.index(lang.t('self interactions')))

    def test_categories_count_what_the_panel_shows(self):
        self.assertTrue(simology.milestones_window())
        self.assertIn('Ana Lee', self.windows[-1][1])
        self.assertEqual(self.rows(), [('Motor and Speech', '2 of 3 reached'), ('Love', '1 of 1 reached'),
                                       ('Infant', '1 of 1 reached')])

    def test_a_category_lists_milestones_in_ui_order(self):
        simology.milestones_window()
        self.windows[-1][2][0][2]()
        self.assertEqual(self.windows[-1][3], 'Motor and Speech')
        self.assertEqual(self.rows(), [
            ('First Words', 'Reached as an infant. | Said a first word.'),
            ('First Steps', 'Reached as a toddler. | Took the first steps.'),
            ('Potty Trained', 'Not reached yet, in progress. | Practice with the potty.')])

    def test_repeatable_and_archived_milestones(self):
        simology.milestone_category(5, 2)
        self.assertEqual(self.rows(), [('First Crush', 'Reached 3 times. | Had a crush.')])
        simology.milestone_category(5, 3)
        self.assertEqual(self.rows(), [('Rolled Over', 'Reached as an infant. | Rolled over.')])

    def test_no_tracker_or_nothing_visible(self):
        self.info.developmental_milestone_tracker = None
        self.assertFalse(simology.milestones_window())
        self.assertEqual(self.spoken[-1], 'No milestones to show for Ana Lee.')
        self.assertEqual(self.windows, [])

    def test_character_values(self):
        self.assertTrue(simology.values_window())
        self.assertIn('Ana Lee', self.windows[-1][1])
        self.assertEqual(self.rows(), [
            ('Manners', '62 on a scale from -100 to 100. | At this level, as a young adult the Sim gets: | '
                        'Considerate | How polite they are.'),
            ('Empathy', '-10 on a scale from -100 to 100. | How they feel for others.')])

    def test_no_character_values(self):
        self.info.commodity_tracker = []
        self.assertFalse(simology.values_window())
        self.assertEqual(self.spoken[-1], 'Ana Lee has no character values.')

    def test_chords(self):
        keys = env.keys
        self.assertEqual(keys.CHORDS[0x4D], ('milestones', False))
        self.assertEqual(keys.CHORDS[0x4B], ('values', False))
        import tyjokr_a11y_shortcuts as shortcuts
        self.assertIn('milestones', shortcuts.chord_label('milestones'))
        self.assertIn('character values', shortcuts.chord_label('values'))
        keys._enabled = True
        keys._modal_active = keys._editing_active = False
        missing = []
        for intent, available, opener in (('milestones', 'milestones_available', 'milestones_window'),
                                          ('values', 'values_available', 'values_window')):
            with patch.object(simology, available, return_value=True),                     patch.object(simology, opener, return_value=True) as opened:
                keys._chord(intent)
                env.drain()
                self.assertEqual(opened.call_count, 1)
                keys.apply_modal_state('101', 'context')
                keys._chord(intent)
                env.drain()
                self.assertEqual(opened.call_count, 1)
                self.assertEqual(self.spoken[-1], lang.t('close the dialog first'))
                keys.apply_modal_state('000', 'context')
            with patch.object(simology, available, return_value=False),                     patch.object(simology, opener) as opened:
                keys._chord(intent)
                env.drain()
                opened.assert_not_called()
                missing.append(self.spoken[-1])
        self.assertEqual(missing, [lang.t('needs growing together'), lang.t('needs parenthood')])

    def test_rows_only_read(self):
        simology.values_window()
        count = len(self.windows)
        self.windows[-1][2][0][2]()
        self.assertEqual(len(self.windows), count + 1)
        self.assertEqual(self.windows[-1][0], 'character values')


if __name__ == '__main__':
    unittest.main()
