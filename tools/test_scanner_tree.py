"""Tree navigation scenarios with game, keyboard and speech mocked offline."""
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.parse import quote
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
        self.objects = {}
        services = SimpleNamespace(object_manager=lambda: self.objects)
        crafting = SimpleNamespace(CraftingTuning=SimpleNamespace(SERVINGS_STATISTIC='servings'))
        styles = SimpleNamespace(HOVER_TIP_DISABLED=0, HOVER_TIP_DEFAULT=1,
                                 HOVER_TIP_CONSUMABLE_CRAFTABLE=2, HOVER_TIP_GARDENING=3,
                                 HOVER_TIP_COLLECTION=4, HOVER_TIP_CUSTOM_OBJECT=5,
                                 HOVER_TIP_ICON_TITLE_DESCRIPTION=6, HOVER_TIP_OBJECT_RELATIONSHIP=7,
                                 HOVER_TIP_HEIRLOOM_OBJECT=8)
        modules = {'services': services, 'crafting.crafting_tunable': crafting,
                   'objects.hovertip': SimpleNamespace(HovertipStyle=styles)}
        for setting in (patch.dict(sys.modules, modules), patch.object(scanner.lang, '_locale_lang', 'en'),
                        patch.object(scanner.pump, 'post', side_effect=lambda fn, *args: fn(*args) or True)):
            setting.start()
            self.addCleanup(setting.stop)

    def object(self, ident, style, fields=(), crafted=False, servings=None, valid=True):
        obj = SimpleNamespace(id=ident, valid_for_distribution=valid, hover_tip=style,
                              crafting_component=crafted, _ui_metadata_stack=None)
        tracker = SimpleNamespace(has_statistic=lambda stat: stat == 'servings' and servings is not None,
                                  get_value=lambda stat: servings)
        obj.get_tracker = lambda stat: tracker

        built = False

        def build_tooltip():
            nonlocal built
            if built:
                return False  # EA also returns False for an already materialised tooltip.
            built = True
            if obj._ui_metadata_stack is None:
                obj._ui_metadata_stack = [(0, 'hover_tip', style, False)]
            for handle, (name, value) in enumerate(fields, 1):
                obj._ui_metadata_stack.append((handle, name, value, False))
            return True

        obj.on_hovertip_requested = Mock(side_effect=build_tooltip)
        self.objects[ident] = obj
        return obj

    def row(self, obj, label='Item'):
        entry = scanner.Entry(obj.id, False, label, 0, 4, 0, 0, 'misc', 'MISC')
        return scanner._entry_parts(entry, 0, 1)

    def test_single_portion_and_drink_have_quality_without_a_servings_statistic(self):
        for label, tier in (('Single plate', 1), ('Drink', 3)):
            with self.subTest(label=label):
                obj = self.object(101, 2, [('quality', tier)], crafted=True)
                parts = self.row(obj, label)
                obj.on_hovertip_requested.assert_called()
                self.assertIn(('objectquality', obj.id), parts)
                self.assertNotIn('servings:', ''.join(p for p in parts if isinstance(p, str)))

    def test_crafted_platter_keeps_servings_with_or_without_quality(self):
        for tier, count in ((0, 0), (2, 6)):
            with self.subTest(tier=tier):
                obj = self.object(102, 2, [('quality', tier)], crafted=True, servings=count)
                parts = self.row(obj)
                self.assertIn(', servings: {}'.format(count), parts)
                self.assertEqual(('objectquality', obj.id) in parts, bool(tier))

    def test_servings_read_failure_does_not_discard_quality(self):
        obj = self.object(105, 2, [('quality', 2)], crafted=True, servings=6)
        obj.get_tracker = Mock(side_effect=ValueError('servings unavailable'))
        parts = self.row(obj)
        self.assertIn(('objectquality', obj.id), parts)
        self.assertNotIn('servings:', ''.join(p for p in parts if isinstance(p, str)))

    def test_servings_and_quality_keep_upstream_cleanliness(self):
        obj = self.object(106, 2, [('quality', 2)], crafted=True, servings=4)
        dirty = SimpleNamespace(state=SimpleNamespace(guid64=15129), guid64=15131)
        obj.state_component = SimpleNamespace(values=lambda: iter((dirty,)))
        parts = self.row(obj, 'Platter')
        self.assertIn(', servings: 4', parts)
        self.assertIn(('objectquality', obj.id), parts)
        self.assertIn(', dirty, ', ''.join(part for part in parts if isinstance(part, str)))

    def test_non_crafted_fish_retains_its_tokenised_freshness(self):
        freshness = SimpleNamespace(hash=0x054DDA26, tokens=[object()])
        obj = self.object(103, 4, [('quality_description', freshness)])
        # The style may already be present before the first hover builds the fields.
        obj._ui_metadata_stack = [(0, 'hover_tip', 4, False)]
        self.assertIn(('objectquality', obj.id), self.row(obj))
        self.assertIn(('objectquality', obj.id), self.row(obj))

    def test_objects_without_displayed_quality_need_no_client_request(self):
        rarity = SimpleNamespace(hash=0x0499D574, tokens=[object()])
        for style, fields, valid in ((1, [], True), (4, [('rarity_text', rarity)], True),
                                     (1, [('quality', 3), ('quality', 0)], True),
                                     (3, [('quality', 2)], True),
                                     (0, [('quality', 2)], True), (6, [('quality', 1)], True),
                                     (2, [('quality', 1)], False)):
            with self.subTest(style=style, fields=fields, valid=valid):
                obj = self.object(104, style, fields, valid=valid)
                with patch.object(scanner, '_send_ui') as send, patch.object(scanner.speech, 'speak') as speak:
                    scanner._speak_parts(self.row(obj, 'Item'))
                    send.assert_not_called()
                    speak.assert_called_once()
                if not valid:
                    obj.on_hovertip_requested.assert_not_called()

    def test_quality_response_is_per_announcement_and_keeps_the_games_words(self):
        ident = 18446744073709551611  # Would lose precision if represented as a double.
        parts = ['Plate', ('objectquality', ident), ', here']
        with patch.object(scanner, '_send_ui') as send, patch.object(scanner.threading, 'Timer'), \
                patch.object(scanner.speech, 'speak') as speak:
            scanner._speak_parts(parts)
            first = send.call_args[0][0].split('|')
            self.assertEqual(first[:2], ['A11y', 'objectquality'])
            self.assertEqual(first[3], str(ident))
            scanner._speak_parts(parts)
            seq = send.call_args[0][0].split('|')[2]
            self.assertNotEqual(seq, first[2])
            scanner.a11y_objectquality_enc('{}|{}|Old'.format(first[2], ident))
            scanner.a11y_objectquality_enc('{}|{}|Other'.format(seq, ident - 1))
            speak.assert_not_called()
            text = 'Jakość: Wspaniała!'
            formatted = 'Jakość: <span class="threestar">Wspaniała!</span>'
            scanner.a11y_objectquality_enc('{}|{}|{}'.format(seq, ident, quote(formatted, safe='')))
            speak.assert_called_once_with('Plate, ' + text + ', here', source='widget')
            scanner.a11y_objectquality_enc('{}|{}|Duplicate'.format(seq, ident))
            self.assertEqual(speak.call_count, 1)

    def test_quality_timeout_reads_the_rest_and_ignores_late_replies(self):
        parts = ['Platter, servings: 3', ('objectquality', 33), ', here']
        with patch.object(scanner, '_send_ui') as send, patch.object(scanner.threading, 'Timer') as timer, \
                patch.object(scanner.speech, 'speak') as speak:
            scanner._speak_parts(parts)
            seq = send.call_args[0][0].split('|')[2]
            _, expire, args = timer.call_args[0]
            expire(*args)
            speak.assert_called_once_with('Platter, servings: 3, here', source='widget')
            scanner.a11y_objectquality_enc('{}|33|Too%20late'.format(seq))
            self.assertEqual(speak.call_count, 1)

    def test_name_and_quality_are_spoken_once_in_either_reply_order(self):
        parts = [('catalog', 7), ('objectquality', 35), ', here']
        for quality_first in (True, False):
            with self.subTest(quality_first=quality_first), \
                    patch.dict(scanner._loc_cache, {}, clear=True), \
                    patch.dict(scanner._loc_waiting, {}, clear=True), \
                    patch.object(scanner, '_send_ui') as send, patch.object(scanner.threading, 'Timer'), \
                    patch.object(scanner.speech, 'speak') as speak:
                scanner._speak_parts(parts)
                messages = [args[0] for args, _ in send.call_args_list]
                self.assertIn('A11y|loc|7|7', messages)
                request = next(msg for msg in messages if msg.startswith('A11y|objectquality|'))
                seq = request.split('|')[2]
                replies = [(scanner.a11y_loc_enc, '7|Drink'),
                           (scanner.a11y_objectquality_enc, '{}|35|Quality%3A%20Normal'.format(seq))]
                if quality_first:
                    replies.reverse()
                (first, first_args), (second, second_args) = replies
                first(first_args)
                speak.assert_not_called()
                second(second_args)
                speak.assert_called_once_with('Drink, Quality: Normal, here', source='widget')

    def test_lost_name_reply_is_requested_again_after_timeout(self):
        parts = ['Object ', ('loc', 71)]
        with patch.dict(scanner._loc_waiting, {}, clear=True), patch.dict(scanner._loc_cache, {}, clear=True), \
                patch.object(scanner, '_send_ui') as send, patch.object(scanner.threading, 'Timer') as timer, \
                patch.object(scanner.speech, 'speak') as speak:
            scanner._speak_parts(parts)
            send.assert_called_once_with('A11y|loc|71|71')
            _, expire, args = timer.call_args[0]
            expire(*args)
            speak.assert_called_once_with('Object', source='widget')
            send.reset_mock()
            scanner._speak_parts(parts)
            send.assert_called_once_with('A11y|loc|71|71')
            scanner.a11y_loc_enc('71|Bowl')
            speak.assert_called_with('Object Bowl', source='widget')
            self.assertEqual(speak.call_count, 2)

    def test_opening_a_menu_silences_an_unfinished_object_row(self):
        parts = [('catalog', 71), ('objectquality', 35)]
        for quality_already_received in (False, True):
            with self.subTest(quality_already_received=quality_already_received), \
                    patch.dict(scanner._loc_waiting, {}, clear=True), patch.dict(scanner._loc_cache, {}, clear=True), \
                    patch.object(scanner, '_menu_open', False), patch.object(scanner.availability, 'pause'), \
                    patch.object(scanner, '_send_ui') as send, patch.object(scanner.threading, 'Timer') as timer, \
                    patch.object(scanner.speech, 'speak') as speak:
                scanner._speak_parts(parts)
                request = next(call[0][0] for call in send.call_args_list
                               if call[0][0].startswith('A11y|objectquality|'))
                reply = '{}|35|Quality%3A%20Normal'.format(request.split('|')[2])
                if quality_already_received:
                    scanner.a11y_objectquality_enc(reply)
                scanner.note_menu_open()
                # A delayed reply can arrive after the player has already closed the menu.
                scanner.a11y_menuclosed()
                if not quality_already_received:
                    scanner.a11y_objectquality_enc(reply)
                scanner.a11y_loc_enc('71|Drink')
                _, expire, args = timer.call_args[0]
                expire(*args)
                speak.assert_not_called()


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
