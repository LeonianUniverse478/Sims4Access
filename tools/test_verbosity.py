"""Verbosity (settings window, cfg [speech] verbosity): full, the default,
says what a thing is before its name (Category, Subcategory, Dialog, Menu
open); brief says only the names. Counts, positions and the Scanner mode
announcement are the same in both.
"""
import unittest
from unittest.mock import patch

import test_feedback_v9 as fixture
import tyjokr_a11y_lang as lang
import tyjokr_a11y_menu as menu
import tyjokr_a11y_narrator as narrator
import tyjokr_a11y_scanner as scanner
import tyjokr_a11y_settings as settings
import tyjokr_a11y_speech as speech


def text(parts):
    return ''.join(part if isinstance(part, str) else '<{}>'.format(part[1]) for part in parts)


class VerbosityTests(unittest.TestCase):
    def setUp(self):
        def entry(ident, group, sub):
            return scanner.Entry(ident, group == 'SIMS', str(ident), 0, 4, 0, 0, sub, group)
        scanner._groups = ['SIMS', 'PLUMBING']
        scanner._by_group = {'SIMS': [entry(1, 'SIMS', 'SIMS')],
                             'PLUMBING': [entry(2, 'PLUMBING', 'showers'), entry(3, 'PLUMBING', 'toilets')]}
        scanner._group_index = 1
        scanner._item_index = 0
        scanner._tree_level = 'groups'
        scanner._tree_groups.clear()
        scanner._tree_items.clear()
        self.spoken = []
        stored = patch.dict(settings._stored, {}, clear=True)
        stored.start()
        self.addCleanup(stored.stop)
        for target, name, kwargs in (
                (scanner, '_label_hash', {'side_effect': lambda key: key}),
                (speech, 'speak', {'side_effect': lambda line, *a, **k: self.spoken.append(line)}),
                (settings, '_save', {'return_value': True}),
                (lang, '_locale_lang', {'new': 'en'})):
            p = patch.object(target, name, **kwargs)
            p.start()
            self.addCleanup(p.stop)

    def brief(self):
        settings._stored['verbosity'] = 'brief'

    def test_full_is_the_default_and_names_the_kind(self):
        self.assertEqual(settings.DEFAULTS['verbosity'], 'full')
        self.assertFalse(settings.brief())
        self.assertEqual(text(scanner._tree_parts()), 'Category. <PLUMBING>, 2 items. 2 of 2.')
        scanner._tree_level = 'subcategories'
        self.assertEqual(text(scanner._tree_parts()), 'Subcategory. <showers>, 1 items. 1 of 2.')

    def test_brief_says_only_the_names(self):
        self.brief()
        self.assertEqual(text(scanner._tree_parts()), '<PLUMBING>, 2 items. 2 of 2.')
        scanner._tree_level = 'subcategories'
        self.assertEqual(text(scanner._tree_parts()), '<showers>, 1 items. 1 of 2.')
        scanner._tree_level = 'items'
        full_item = text(scanner._tree_parts())
        del settings._stored['verbosity']
        self.assertEqual(text(scanner._tree_parts()), full_item)    # items never had a kind

    def test_dialogs_and_menus(self):
        narrator.a11y_dialog_enc('Save%20your%20game%3F')
        narrator.a11y_menuopen('5')
        self.brief()
        narrator.a11y_dialog_enc('Save%20your%20game%3F')
        narrator.a11y_menuopen('5')
        self.assertEqual(self.spoken, ['Dialog. Save your game?', 'Menu open. 5 options.',
                                       'Save your game?', '5 options.'])

    def test_scope_openings(self):
        narrator.a11y_scope_enc('dialog%02Pick%20one%02Yes')
        self.brief()
        narrator.a11y_scope_enc('dialog%02Pick%20one%02Yes')
        self.assertEqual(self.spoken, ['Dialog. Pick one. Yes', 'Pick one. Yes'])

    def test_cfg_round_trip_and_bad_values(self):
        self.assertIn('verbosity = full', settings.render_default())
        rendered = settings._render({'verbosity': 'brief'})
        self.assertIn('verbosity = brief', rendered)
        self.assertEqual(settings._FILE_MAP[('speech', 'verbosity')], 'verbosity')

    def test_settings_window_row_cycles_and_reads(self):
        row = next(r for r in menu.ROWS if r.key == 'verbosity')
        self.assertEqual((row.kind, row.choices), ('choice', ('full', 'brief')))
        self.assertEqual(menu._value_text(row), 'Full')
        self.assertTrue(menu._change(row, 1))
        self.assertEqual(settings._stored['verbosity'], 'brief')
        self.assertEqual(menu._value_text(row), 'Brief')
        self.assertTrue(settings.brief())
        menu._change(row, 1)
        self.assertEqual(menu._value_text(row), 'Full')

    def test_terms_exist_in_english_and_polish(self):
        for term in ('verbosity', 'verbosity full', 'verbosity brief'):
            self.assertEqual(set(lang._TRANSLATIONS[term]), {'en', 'pl'}, term)


class VerbosityCfgParseTests(unittest.TestCase):
    def test_parse_accepts_known_levels_only(self):
        parse = next(getattr(settings, name) for name in dir(settings)
                     if callable(getattr(settings, name)) and getattr(settings, name).__doc__
                     and "Parse one cfg value" in getattr(settings, name).__doc__)
        with patch.dict(settings._stored, {}, clear=True):
            del settings.load_errors[:]
            parse('verbosity', 'Brief')
            self.assertEqual(settings._stored['verbosity'], 'brief')
            parse('verbosity', 'chatty')
            self.assertEqual(settings._stored['verbosity'], 'brief')
            self.assertTrue(any('verbosity' in error for error in settings.load_errors))
            del settings.load_errors[:]


if __name__ == '__main__':
    unittest.main()
