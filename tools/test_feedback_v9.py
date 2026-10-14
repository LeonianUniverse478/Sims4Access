"""V9 scanner refresh/category and stale owner regressions; no game/audio."""
import sys
import types
import unittest
from unittest.mock import patch
import test_scanner_v5 as env
import tyjokr_a11y_scanner as scanner
from test_feedback_v8 import FeedbackTests


class ScannerRefreshTests(unittest.TestCase):
    def setUp(self):
        scanner._by_group = {}
        scanner._groups = []
        scanner._item_index = scanner._group_index = 0
        scanner._last_scan = 0
        scanner._menu_open = False
        scanner._refresh_requested = True
        scanner._last_activity = scanner.time.monotonic()
        scanner._class_cache.clear()
        scanner.availability.reset()
        scanner._availability_revision = scanner.availability.revision()
        env.settings._stored.clear()

    def test_live_mode_zero_flags_use_function_tags(self):
        cases = {'BuyCatSS_Desk': 'SURFACE', 'BuyCatSS_Bed': 'COMFORT',
                 'BuyCatSS_Dresser': 'STORAGE', 'BuyCatEE_Computer': 'ELECTRONICS',
                 'BuyCatEE_CreativeActivity': 'ENTERTAINMENT', 'BuyCatEE_KidToy': 'KIDS',
                 'BuyCatPA_Toilet': 'PLUMBING', 'BuyCatPA_Refrigerator': 'APPLIANCES',
                 'BuyCatLD_FloorLamp': 'LIGHTING', 'BuyCatLD_Rug': 'DECOR',
                 'BuyCatEE_PetToys': 'PETS', 'BuyCatEE_Transportation': 'VEHICLE',
                 'Build_Door': 'BUILD', 'unrecognized': 'MISC'}
        for tag, group in cases.items():
            with self.subTest(tag=tag):
                self.assertEqual(scanner._group_of(0, tag), group)

    def test_native_nonzero_category_takes_precedence(self):
        self.assertEqual(scanner._group_of(scanner.buycat.GROUP_FLAG['PETS'], 'BuyCatSS_Bed'), 'PETS')

    def fixture(self):
        def obj(ident, distance, tag='BuyCatSS_Desk'):
            return types.SimpleNamespace(id=ident, distance=distance, tag=tag,
                position=types.SimpleNamespace(x=distance, y=0, z=0), level=0,
                definition=types.SimpleNamespace(name='test'), is_hidden=lambda: False)
        sim = obj(1, 0)
        visitor = obj(2, 20)
        objects = [obj(3, 10), obj(4, 41)]
        services = types.SimpleNamespace(get_active_sim=lambda: sim,
            sim_info_manager=lambda: types.SimpleNamespace(instanced_sims_gen=lambda: iter([sim, visitor])),
            object_manager=lambda: types.SimpleNamespace(get_valid_objects_gen=lambda: iter(objects)))
        def entry(obj, origin, level, is_sim, category, group):
            return scanner.Entry(obj.id, is_sim, 'test', None, obj.distance, 0, 0, category, group)
        return services, objects, entry

    def test_refresh_adds_removes_and_preserves_selection_silently(self):
        services, objects, entry = self.fixture()
        with patch.dict(sys.modules, {'services': services}), \
                patch.object(scanner, '_entry_for', entry), \
                patch.object(scanner, '_has_interactions', return_value=True), \
                patch.object(scanner, '_tag_names', lambda obj: {obj.tag}), \
                patch.object(scanner, '_buy_flags', return_value=0), \
                patch.object(scanner, '_speak_parts') as speak:
            self.assertTrue(scanner._scan())
            self.assertEqual([x.obj_id for x in scanner._by_group['SIMS']], [1, 2])
            self.assertEqual([x.obj_id for x in scanner._by_group['SURFACE']], [3])
            scanner._group_index = scanner._groups.index('SURFACE')
            # A previously out-of-range object moves in closer; sorting changes.
            objects[1].distance = 2
            objects[1].position.x = 2
            scanner._last_scan -= 3
            scanner._refresh_tick()
            self.assertEqual([x.obj_id for x in scanner._by_group['SURFACE']], [4, 3])
            self.assertEqual(scanner._current().obj_id, 3)
            objects.pop(0)
            scanner._last_scan -= 3
            scanner._refresh_tick()
            self.assertEqual(scanner._current().obj_id, 4)
            speak.assert_not_called()

    def test_menu_freezes_refresh_until_closed(self):
        with patch.object(scanner, '_scan') as scan:
            scanner._menu_open = True
            scanner._refresh_tick()
            scan.assert_not_called()
            scanner._menu_open = False
            scanner._refresh_tick()
            scan.assert_called_once_with(preserve=True)

    def test_stale_results_refresh_on_next_action(self):
        scanner._groups = ['SIMS']
        scanner._last_scan = 10
        with patch.object(scanner.time, 'monotonic', return_value=11), patch.object(scanner, '_scan') as scan:
            self.assertTrue(scanner._ensure_scan())
            scan.assert_not_called()
        with patch.object(scanner.time, 'monotonic', return_value=13), patch.object(scanner, '_scan', return_value=True) as scan:
            self.assertTrue(scanner._ensure_scan())
            scan.assert_called_once_with(preserve=True)

    def test_world_owner_clears_missed_pie_close_before_scanner_route(self):
        scanner._menu_open = True
        env.keys.a11y_modalstate('00')
        self.assertFalse(scanner._menu_open)
        env.queue.clear()
        with patch.object(scanner.pump, 'post') as post, patch.object(env.keys, '_send') as ui:
            scanner.on_key('next')
            post.assert_called_once_with(scanner._dispatch, 'next')
            ui.assert_not_called()

    def test_new_zone_rearms_refresh_when_old_alarm_is_already_dead(self):
        from unittest.mock import Mock
        alarm = types.SimpleNamespace(cancel_alarm=Mock(side_effect=RuntimeError('old timeline gone')),
                                      add_alarm_real_time=Mock(return_value='new handle'))
        clock = types.SimpleNamespace(interval_in_real_seconds=lambda value: value)
        scanner._refresh_handle = 'old handle'
        with patch.dict(sys.modules, {'alarms': alarm, 'clock': clock}):
            scanner._start_refresh()
        self.assertEqual(scanner._refresh_handle, 'new handle')
        args, kwargs = alarm.add_alarm_real_time.call_args
        self.assertIs(args[0], scanner._refresh_owner)
        self.assertEqual(args[1], 2.0)
        self.assertIs(args[2], scanner._refresh_tick)
        self.assertEqual(kwargs, {'repeating': True})


if __name__ == '__main__':
    unittest.main()
