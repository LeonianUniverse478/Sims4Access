"""Scanner membership and cursor behavior with active-Sim availability."""
import sys
import types
import unittest
from unittest.mock import patch
from test_feedback_v9 import ScannerRefreshTests
import tyjokr_a11y_scanner as scanner

class AvailabilityIntegrationTests(unittest.TestCase):
    def setUp(self):
        ScannerRefreshTests.setUp(self)
        scanner.availability.reset()
        scanner._availability_revision = scanner.availability.revision()
        self.services, self.objects, self.entry = ScannerRefreshTests.fixture(self)
        self.objects[1].position.x = self.objects[1].distance = 12
        self.verdicts = {3: 'usable', 4: 'usable'}
        self.contexts = [
            patch.dict(sys.modules, {'services': self.services}),
            patch.object(scanner, '_entry_for', self.entry),
            patch.object(scanner, '_tag_names', lambda obj: {obj.tag}),
            patch.object(scanner, '_buy_flags', return_value=0),
            patch.object(scanner.availability, 'begin'),
            patch.object(scanner.availability, 'state', side_effect=lambda obj: self.verdicts[obj.id])]
        for context in self.contexts:
            context.start()
            self.addCleanup(context.stop)
        scanner._tree_level = 'groups'
        scanner._tree_groups.clear()
        scanner._tree_items.clear()

    def test_only_confirmed_empty_objects_disappear(self):
        for verdict in ('usable', 'locked', 'pending', 'empty'):
            self.verdicts[3] = verdict
            scanner._scan()
            ids = [e.obj_id for e in scanner._by_group.get('SURFACE', [])]
            self.assertEqual(3 in ids, verdict != 'empty', verdict)
            self.assertEqual([e.obj_id for e in scanner._by_group['SIMS']], [1, 2])

    def test_forwarded_target_is_not_rejected_by_static_census(self):
        with patch.object(scanner, '_has_interactions', return_value=False):
            scanner._scan()
        self.assertEqual([e.obj_id for e in scanner._by_group['SURFACE']], [3, 4])

    def test_locked_item_has_spoken_status_but_keeps_native_open(self):
        self.verdicts[3] = 'locked'
        scanner._scan()
        scanner._group_index = scanner._groups.index('SURFACE')
        scanner._item_index = 0
        scanner._tree_level = 'items'
        parts = scanner._entry_parts(scanner._current(), 0, 2)
        self.assertIn('unavailable', ''.join(str(p) for p in parts))
        with patch.object(scanner, '_do_open') as opened:
            scanner._tree_enter(activate=True)
        opened.assert_called_once_with()

    def test_filtering_sibling_preserves_selected_object(self):
        scanner._scan()
        scanner._group_index = scanner._groups.index('SURFACE')
        scanner._item_index = 1
        scanner._tree_level = 'items'
        self.verdicts[3] = 'empty'
        scanner._scan(preserve=True)
        self.assertEqual(scanner._current().obj_id, 4)

    def test_new_verdict_refreshes_before_next_key(self):
        scanner._scan()
        scanner._last_scan = scanner.time.monotonic()
        with patch.object(scanner.availability, 'revision',
                          return_value=scanner._availability_revision + 1), \
                patch.object(scanner, '_scan', return_value=True) as scan:
            scanner._ensure_scan()
        scan.assert_called_once_with(preserve=True)

    def test_sim_switch_discards_verdicts_before_queued_refresh(self):
        with patch.object(scanner.availability, 'reset') as reset, \
                patch.object(scanner.pump, 'post') as post:
            scanner._active_sim_changed(object(), object())
        reset.assert_called_once_with()
        self.assertEqual(scanner._last_scan, 0)
        post.assert_called_once_with(scanner._scan, True)

    def test_explicit_rescan_rechecks_without_clearing_visible_results(self):
        with patch.object(scanner.availability, 'recheck') as recheck, \
                patch.object(scanner, '_scan', return_value=False), \
                patch.object(scanner.speech, 'speak'):
            scanner._do_rescan()
        recheck.assert_called_once_with()

    def test_idle_pauses_work_without_discarding_results(self):
        scanner._refresh_requested = True
        scanner._menu_open = False
        scanner._last_activity = scanner.time.monotonic() - 31
        with patch.object(scanner, 'enabled', return_value=True), \
                patch.object(scanner.settings, 'get', return_value=True), \
                patch.dict(sys.modules, {'tyjokr_a11y_keys': types.SimpleNamespace(_modal_active=False, _editing_active=False)}), \
                patch.object(scanner.availability, 'pause') as pause, \
                patch.object(scanner.availability, 'reset') as reset:
            scanner._refresh_tick()
        pause.assert_called_once_with()
        reset.assert_not_called()
        self.assertFalse(scanner._refresh_requested)

    def test_dialog_navigation_pauses_background_checks(self):
        scanner._refresh_requested = True
        scanner._menu_open = False
        with patch.object(scanner, 'enabled', return_value=True), \
                patch.object(scanner.settings, 'get', return_value=True), \
                patch.dict(sys.modules, {'tyjokr_a11y_keys': types.SimpleNamespace(_modal_active=True, _editing_active=False)}), \
                patch.object(scanner.availability, 'pause') as pause, \
                patch.object(scanner, '_scan') as scan:
            scanner._refresh_tick()
        pause.assert_called_once_with()
        scan.assert_not_called()

    def test_pie_open_pauses_pending_checks(self):
        with patch.object(scanner.availability, 'pause') as pause:
            scanner.note_menu_open()
        pause.assert_called_once_with()

if __name__ == '__main__':
    unittest.main()
