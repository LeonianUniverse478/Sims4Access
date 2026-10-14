"""Tree navigation scenarios with game, keyboard and speech mocked offline."""
import unittest
from unittest.mock import patch
import test_feedback_v9 as fixture
import tyjokr_a11y_scanner as scanner


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
