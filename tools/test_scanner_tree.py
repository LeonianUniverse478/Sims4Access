"""Tree navigation scenarios with game, keyboard and speech mocked offline."""
import unittest
import sys
from enum import Enum
from types import SimpleNamespace
from unittest.mock import Mock
from unittest.mock import patch
import test_feedback_v9 as fixture
import tyjokr_a11y_scanner as scanner


class ServingTests(unittest.TestCase):
    def test_only_catalog_names_use_the_standalone_form(self):
        forms = '{Y.Plates}{P.Plates}{S.Plate}'
        with patch.dict(scanner._loc_cache, {7: forms}), patch.object(scanner.speech, 'speak') as speak:
            scanner._speak_parts([('catalog', 7), ' / ', ('loc', 7)])
            speak.assert_called_once_with('Plate / ' + forms, source='widget')
        for value in ('{S.Plate}', '{S.A}{Y.B}', '{S.A}{S.B}{Y.C}{P.D}'):
            self.assertEqual(scanner._catalog_name(value), value)

    def setUp(self):
        fields = Enum('TooltipFieldsComplete', ('quality', 'quality_description'))
        self.fields = fields
        game = {
            'objects.components': SimpleNamespace(types=SimpleNamespace(TOOLTIP_COMPONENT='tooltip')),
            'objects.hovertip': SimpleNamespace(TooltipFieldsComplete=fields),
            'crafting.crafting_tunable': SimpleNamespace(CraftingTuning=SimpleNamespace(SERVINGS_STATISTIC='servings'))
        }
        modules = patch.dict(sys.modules, game)
        modules.start()
        self.addCleanup(modules.stop)
        language = patch.object(scanner.lang, '_locale_lang', 'en')
        language.start()
        self.addCleanup(language.stop)

    def test_tooltip_quality_preserves_servings_before_or_after_hover(self):
        supplied = {'quality': SimpleNamespace(field_data=2)}
        resolved = {}
        tooltip = SimpleNamespace(get_tooltip_field=resolved.get, _external_field_to_data=supplied)
        obj = Mock(crafting_component=True)
        obj.get_component.return_value = tooltip
        tracker = obj.get_tracker.return_value
        tracker.get_value.return_value = 0
        def check(key=None):
            expected = [', servings: 0'] + ([('quality', key)] if key else [])
            self.assertEqual(scanner._serving_details(obj), expected)
        check(0xD65A6280)
        for tier, key in [(1, 0x2B79C896), (2, 0xD65A6280), (3, 0xE7486BCE), (0, None), (4, None)]:
            resolved[self.fields.quality] = tier
            check(key)
        spoiled = SimpleNamespace(hash=0xAED7F945, tokens=[])
        supplied['quality_description'] = SimpleNamespace(field_data=spoiled)
        check(spoiled.hash)
        resolved[self.fields.quality_description] = SimpleNamespace(hash=12, tokens=[])
        check(12)
        resolved[self.fields.quality_description].tokens = [object()]
        check()
        obj.get_component.return_value = None
        check()
        tracker.has_statistic.return_value = False
        self.assertEqual(scanner._serving_details(obj), [])
        self.assertEqual(scanner._serving_details(None), [])

    def test_quality_localization_and_timeout(self):
        parts = ['Food, servings: 3', ('quality', 0xD65A6280), ', here']
        with patch.dict(scanner._loc_cache, {}, clear=True), \
                patch.dict(scanner._loc_waiting, {}, clear=True), \
                patch.object(scanner, '_send_ui') as send, \
                patch.object(scanner.threading, 'Timer'), patch.object(scanner.speech, 'speak') as speak:
            scanner._speak_parts(parts)
            self.assertEqual({args[0] for args, _ in send.call_args_list},
                             {'A11y|loc|{0}|{0}'.format(key) for key in (0x01E8983B, 0xD65A6280)})
            scanner.a11y_loc_enc('32020539|Quality%3A')
            speak.assert_not_called()
            scanner.a11y_loc_enc('3596247680|%3Cspan%20class%3D%22twostar%22%3ENormal%3C%2Fspan%3E')
            speak.assert_called_once_with('Food, servings: 3, Quality: Normal, here', source='widget')
            scanner._loc_cache.clear()
            scanner._speak_parts(parts)
            scanner._finish(scanner._loc_waiting[0xD65A6280][0])
            speak.assert_called_with('Food, servings: 3, here', source='widget')


class TreeTests(unittest.TestCase):
    def setUp(self):
        def entry(ident, group, sub):
            return scanner.Entry(ident, group == 'SIMS', str(ident), 0,
                                 4, 0, 0, sub, group)
        scanner._groups = ['SIMS', 'PLUMBING']
        scanner._by_group = {
            'SIMS': [entry(1, 'SIMS', 'SIMS')],
            'PLUMBING': [entry(2, 'PLUMBING', 'showers'),
                         entry(3, 'PLUMBING', 'showers'),
                         entry(4, 'PLUMBING', 'toilets')]}
        scanner._group_index = scanner._item_index = 0
        scanner._tree_level = 'groups'
        scanner._tree_groups.clear()
        scanner._tree_items.clear()
        scanner._menu_open = False
        for name, kwargs in [('_ensure_scan', {'return_value': True}),
                             ('_speak_parts', {}), ('_do_open', {}),
                             ('_label_hash', {'side_effect': lambda key: key})]:
            p = patch.object(scanner, name, **kwargs)
            setattr(self, name, p.start())
            self.addCleanup(p.stop)

    def key(self, *intents):
        for intent in intents:
            scanner._dispatch(intent)

    def shower(self):
        self.key('next', 'nextcat', 'nextcat')

    def test_categories_do_not_activate_objects(self):
        self.key('next', 'open')
        self.assertEqual(scanner._tree_level, 'subcategories')
        self.assertEqual(scanner._current().category, 'showers')
        self._do_open.assert_not_called()

    def test_complete_shower_interaction_path(self):
        self.shower()
        self.assertEqual(scanner._tree_level, 'items')
        self.key('next', 'open')
        self.assertEqual(scanner._current().obj_id, 3)
        self._do_open.assert_called_once_with()

    def test_right_on_leaf_does_not_activate(self):
        self.shower()
        self.key('nextcat')
        self._do_open.assert_not_called()

    def test_item_arrows_stay_within_subcategory(self):
        self.shower()
        self.key('next', 'next')
        self.assertEqual(scanner._current().obj_id, 2)
        self.key('prev')
        self.assertEqual(scanner._current().obj_id, 3)

    def test_left_and_backspace_are_parent_navigation(self):
        self.shower()
        self.key('prevcat')
        self.assertEqual(scanner._tree_level, 'subcategories')
        self.key('back')
        self.assertEqual(scanner._tree_level, 'groups')
        self.assertEqual(scanner._group_key(), 'PLUMBING')
        self.key('back')
        self.assertEqual(scanner._group_key(), 'PLUMBING')

    def test_remembers_item_in_each_subcategory(self):
        self.shower()
        self.key('next', 'back', 'next', 'open')
        self.assertEqual(scanner._current().obj_id, 4)
        self.key('back', 'prev', 'open')
        self.assertEqual(scanner._current().obj_id, 3)

    def test_remembers_subcategory_and_item_on_category_return(self):
        self.shower()
        self.key('back', 'next', 'open', 'back', 'back', 'prev')
        self.assertEqual(scanner._group_key(), 'SIMS')
        self.key('next', 'open', 'open')
        self.assertEqual(scanner._current().obj_id, 4)

    def test_sims_skip_redundant_subcategory(self):
        self.key('open')
        self.assertEqual(scanner._tree_level, 'items')
        self.key('back')
        self.assertEqual(scanner._tree_level, 'groups')

    def test_refresh_reorder_preserves_identity(self):
        self.shower()
        self.key('next')
        scanner._by_group['PLUMBING'].reverse()
        scanner._tree_restore()
        self.assertEqual(scanner._current().obj_id, 3)

    def test_deleted_item_falls_back_inside_same_subcategory(self):
        self.shower()
        self.key('next')
        scanner._by_group['PLUMBING'] = [scanner._by_group['PLUMBING'][2],
                                         scanner._by_group['PLUMBING'][0]]
        scanner._tree_restore()
        self.assertEqual(scanner._current().obj_id, 2)

    def test_disappearing_subcategory_has_valid_fallback(self):
        self.shower()
        scanner._tree_remember()
        scanner._by_group['PLUMBING'] = [scanner._by_group['PLUMBING'][2]]
        scanner._tree_restore()
        self.key('next', 'back', 'open')
        self.assertEqual(scanner._current().obj_id, 4)

    def test_menu_close_and_resume_preserve_tree_position(self):
        self.shower()
        self.key('next')
        scanner.note_menu_open()
        scanner.a11y_menuclosed()
        scanner.resume_mode()
        self.assertEqual(scanner._tree_level, 'items')
        self.assertEqual(scanner._current().obj_id, 3)

    def test_empty_tree_navigation_is_safe(self):
        scanner._groups = []
        scanner._by_group = {}
        self.key('next', 'prev', 'open', 'nextcat', 'back')
        self._do_open.assert_not_called()

    def test_item_announcement_counts_only_siblings(self):
        self.shower()
        self.key('next')
        self.assertIn('2 of 2', ''.join(p for p in scanner._tree_parts()
                                       if isinstance(p, str)))

    def test_explicit_rescan_preserves_tree_selection(self):
        self.shower()
        with patch.object(scanner, '_scan', return_value=True) as scan:
            scanner._do_rescan()
        scan.assert_called_once_with(preserve=True)
        self.assertEqual(scanner._tree_level, 'items')


if __name__ == '__main__':
    unittest.main()
