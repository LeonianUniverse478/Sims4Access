"""Behavior and work bounds for scanner caching, freshness and idling."""
import sys
import types
import unittest
from unittest.mock import patch, Mock
from test_feedback_v9 import ScannerRefreshTests
import tyjokr_a11y_scanner as scanner


class ScannerPerformanceTests(unittest.TestCase):
    def setUp(self):
        ScannerRefreshTests.setUp(self)
        self.clock = patch.object(scanner.time, 'monotonic', return_value=100)
        self.now = self.clock.start()
        self.addCleanup(self.clock.stop)
        scanner._last_activity = 100

    def test_distant_objects_do_not_resolve_metadata_or_affordances(self):
        services, objects, entry = ScannerRefreshTests.fixture(self)
        with patch.dict(sys.modules, {'services': services}), \
                patch.object(scanner, '_entry_for', entry), \
                patch.object(scanner.availability, 'begin') as candidates, \
                patch.object(scanner.availability, 'state', return_value='usable') as affordances, \
                patch.object(scanner, '_tag_names', return_value={'BuyCatSS_Desk'}) as tags, \
                patch.object(scanner, '_buy_flags', return_value=0) as flags:
            scanner._scan()
            affordances.assert_called_once_with(objects[0])
            self.assertEqual(candidates.call_args[0][1], [objects[0]])
            tags.assert_called_once_with(objects[0])
            flags.assert_called_once_with(objects[0])

    def test_shared_definition_cached_but_mutable_object_state_is_fresh(self):
        services, objects, unused = ScannerRefreshTests.fixture(self)
        sim = services.get_active_sim()
        sim.sim_info = types.SimpleNamespace(first_name='Active', last_name='Sim')
        services.sim_info_manager = lambda: types.SimpleNamespace(instanced_sims_gen=lambda: iter([sim]))
        for obj in objects:
            obj.has_custom_name = lambda: True
            obj.custom_name = 'Desk'
        objects[1].definition = objects[0].definition
        objects[1].position.x = 9
        with patch.dict(sys.modules, {'services': services}), \
                patch.object(scanner.availability, 'state', return_value='usable') as affordances, \
                patch.object(scanner, '_tag_names', return_value={'BuyCatSS_Desk'}) as tags, \
                patch.object(scanner, '_buy_flags', return_value=0) as flags:
            scanner._scan()
            scanner._group_index = scanner._groups.index('SURFACE')
            scanner._item_index = 1  # object 3, farther away
            objects[0].custom_name = 'Renamed desk'
            objects[0].position.x = 2
            scanner._scan(preserve=True)
            self.assertEqual(scanner._current().obj_id, 3)
            self.assertEqual(scanner._current().name, 'Renamed desk')
            self.assertEqual(scanner._current().distance, 2)
            self.assertEqual(tags.call_count, 1)
            self.assertEqual(flags.call_count, 1)
            self.assertEqual(affordances.call_count, 4)
            objects[0].is_in_inventory = lambda: True
            objects[1].is_hidden = lambda: True
            scanner._scan(preserve=True)
            self.assertNotIn('SURFACE', scanner._groups)

    def test_definition_cache_expires_and_is_bounded(self):
        obj = types.SimpleNamespace(definition=object())
        with patch.object(scanner, '_tag_names', return_value={'BuyCatSS_Desk'}) as tags, \
                patch.object(scanner, '_buy_flags', return_value=0):
            scanner._classification(obj, 100)
            scanner._classification(obj, 102)
            self.assertEqual(tags.call_count, 1)
            scanner._classification(obj, 131)
            self.assertEqual(tags.call_count, 2)
            with patch.object(scanner, '_CLASS_CACHE_LIMIT', 3):
                for unused in range(10):
                    scanner._classification(types.SimpleNamespace(definition=object()), 131)
                    self.assertLessEqual(len(scanner._class_cache), 3)

    def test_idle_alarm_does_no_world_work_next_action_refreshes(self):
        scanner._last_scan = 100
        with patch.object(scanner, '_scan', return_value=True) as scan:
            self.now.return_value = 131
            scanner._refresh_tick()
            self.assertFalse(scanner._refresh_requested)
            scan.assert_not_called()
            scanner.ensure_scan()
            self.assertTrue(scanner._refresh_requested)
            scan.assert_called_once_with(preserve=True)

    def test_alarm_does_not_duplicate_a_recent_user_scan(self):
        scanner._last_scan = 99
        with patch.object(scanner, '_scan') as scan:
            scanner._refresh_tick()
            scan.assert_not_called()
            self.now.return_value = 102
            scanner._refresh_tick()
            scan.assert_called_once_with(preserve=True)

    def test_switching_active_sim_invalidates_even_recent_results(self):
        scanner._groups = ['SIMS']
        scanner._last_scan = 100
        scanner._last_origin = (1, 0.0, 0.0)
        services = types.SimpleNamespace(get_active_sim=lambda: types.SimpleNamespace(
            id=2, level=0, position=types.SimpleNamespace(x=0, z=0)))
        with patch.dict(sys.modules, {'services': services}), patch.object(scanner, '_scan') as scan:
            scanner._ensure_scan()
            scan.assert_called_once_with(preserve=True)

    def test_walking_does_not_force_a_scan_on_every_keypress(self):
        scanner._groups = ['SIMS']
        scanner._last_scan = 100
        scanner._last_origin = (1, 0.0, 0.0)
        scanner._origin_level = 0
        services = types.SimpleNamespace(get_active_sim=lambda: types.SimpleNamespace(
            id=1, level=0, position=types.SimpleNamespace(x=2, z=3)))
        with patch.dict(sys.modules, {'services': services}), patch.object(scanner, '_scan') as scan:
            self.assertTrue(scanner._ensure_scan())
            scan.assert_not_called()

    def test_manual_rescan_discards_classification_cache(self):
        scanner._class_cache[123] = 'old'
        with patch.object(scanner, '_scan', return_value=False), patch.object(scanner.speech, 'speak'):
            scanner._do_rescan()
        self.assertFalse(scanner._class_cache)


if __name__ == '__main__':
    unittest.main()
