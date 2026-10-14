"""State/lifecycle regressions for native Build requests and read-only grid.

Mocks model EA 1.127 signatures; these do not certify native client behavior.
"""
import types
import unittest
from unittest.mock import Mock, patch

import test_scanner_v5 as env
import tyjokr_a11y_build as build
import tyjokr_a11y_grid as grid
import tyjokr_a11y_scanner as scanner


class BuildTests(unittest.TestCase):
    def setUp(self):
        env.settings._stored['build_controls'] = True
        self.addCleanup(env.settings._stored.pop, 'build_controls', None)
        build._active = False
        build._pending.clear()
        build._serial = build._last_serial = 0
        build._zone_id = None
        build._last_feedback = ''
        build._aim_pending = 0
        env.messages.clear()
        self.zone = types.SimpleNamespace(id=12, is_in_build_buy=True)
        self.patches = [patch.object(build, '_zone', side_effect=lambda: self.zone),
                        patch.object(build.speech, 'speak')]
        for item in self.patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in reversed(self.patches)])

    def test_requires_client_ack_before_routing_cursor_keys(self):
        self.assertTrue(build.request('on'))
        self.assertFalse(build.active())
        self.assertFalse(build.request('click'))
        self.assertEqual(env.messages, ['A11y|buildcontrols|on', 'A11y|build|on|1'])
        self.assertTrue(build.state('1|1|on|220|180|16'))
        self.assertTrue(build.active())
        self.assertTrue(build.on_key('open'))
        self.assertEqual(env.messages[-1], 'A11y|build|click|2')
        self.assertTrue(build.state('2|1|click|220|180|16'))
        self.assertIn('Select or place', build.speech.speak.call_args[0][0])

    def test_invalid_and_unsolicited_activation_are_rejected(self):
        build.request('on')
        for reply in ('', '999|1|on|20|90|16', '0|1|on|20|90|16',
                      '1|7|on|20|90|16', '1|1|on|-1|90|16',
                      '1|1|on|20|90|999', '1|1|on|nan|90|16'):
            self.assertFalse(build.state(reply), reply)
            self.assertFalse(build.active())
        self.assertTrue(build.state('1|1|on|20|90|16'))

    def test_late_reply_cannot_reactivate_after_off(self):
        build.request('on')
        build.request('off')
        build.state('2|0|off|20|90|16')
        self.assertFalse(build.state('1|1|on|20|90|16'))
        self.assertFalse(build.active())

    def test_off_retires_keys_immediately_before_client_reply(self):
        build.request('on')
        build.state('1|1|on|20|90|16')
        self.assertTrue(build.active())
        build.request('on')
        build.request('off')
        self.assertFalse(build.active())
        self.assertFalse(build.state('2|1|on|20|90|16'))

    def test_native_localized_error_and_name_roundtrip_without_claiming_success(self):
        from urllib.parse import quote
        build.request('on')
        build.state('1|1|on|20|90|16')
        error = 'Nie można umieścić tutaj: ściana | 25%'
        self.assertTrue(build.info('error|' + quote(error)))
        self.assertEqual(build.speech.speak.call_args[0][0], error)
        build.request('status')
        build.state('2|1|status|20|90|16')
        self.assertIn(error, build.speech.speak.call_args[0][0])
        build.request('left')
        self.assertEqual(build._last_feedback, '')
        self.assertFalse(build.info('placed|Success'))
        self.zone = None
        self.assertFalse(build.info('name|Stale object'))

    def test_zone_change_and_automatic_retirement_discard_inflight_actions(self):
        build.request('on')
        self.zone = types.SimpleNamespace(id=13, is_in_build_buy=True)
        self.assertFalse(build.state('1|1|on|20|90|16'))
        build.request('on')
        self.assertTrue(build.state('0|0|off|20|90|16'))
        self.assertFalse(build.state('2|1|on|20|90|16'))
        self.assertFalse(build.active())

    def test_outside_build_requests_never_reach_client(self):
        self.zone = None
        for action in ('on', 'click', 'undo', 'redo', 'rotateleft'):
            self.assertFalse(build.request(action))
        self.assertEqual(env.messages, [])
        self.assertFalse(build.request('sell_everything'))

    def test_undo_uses_client_history_even_when_cursor_is_off(self):
        self.assertTrue(build.request('undo'))
        self.assertTrue(build.request('redo'))
        self.assertEqual(env.messages, ['A11y|build|undo|1', 'A11y|build|redo|2'])

    def test_projection_sends_validated_world_point_without_clicking_or_capturing_early(self):
        point = types.SimpleNamespace(x=2.25, y=3.5, z=7.25)
        with patch.object(grid, 'cursor', return_value=(point, 1, 12)), patch.object(grid, 'leave') as leave:
            self.assertTrue(build.aim_grid())
        leave.assert_called_once_with()
        self.assertEqual(env.messages, ['A11y|buildcontrols|on', 'A11y|buildaim|1|2.250000|3.500000|7.250000|1|12'])
        self.assertFalse(build.active())
        self.assertTrue(build.aiming())
        self.assertFalse(build.on_key('open'))
        self.assertTrue(build.state('1|1|aim|610|270|16'))
        self.assertTrue(build.active())
        self.assertFalse(build.aiming())
        self.assertEqual(len(env.messages), 2)       # switch + aim; the early 'open' sent nothing

    def test_failed_projection_preconditions_preserve_grid(self):
        with patch.object(grid, 'cursor', return_value=None), patch.object(grid, 'leave') as leave:
            self.assertFalse(build.aim_grid())
        leave.assert_not_called()
        self.assertEqual(env.messages, [])

    def test_projection_timeout_rejects_late_activation(self):
        point = types.SimpleNamespace(x=2, y=3, z=7)
        with patch.object(grid, 'cursor', return_value=(point, 1, 12)), patch.object(grid, 'leave'):
            self.assertTrue(build.aim_grid())
        with patch.object(build.time, 'monotonic', return_value=build._aim_until + 1):
            self.assertFalse(build.aiming())
        self.assertFalse(build.state('1|1|aim|610|270|16'))

    def test_build_mode_validation_precedes_retiring_grid(self):
        self.zone = None
        with patch.object(grid, 'active', return_value=True), patch.object(grid, 'leave') as leave:
            self.assertFalse(build.request('on'))
            leave.assert_not_called()
            self.zone = types.SimpleNamespace(id=12, is_in_build_buy=True)
            self.assertTrue(build.request('on'))
            leave.assert_called_once_with()


class GridTests(unittest.TestCase):
    def setUp(self):
        env.settings._stored['build_controls'] = True
        self.addCleanup(env.settings._stored.pop, 'build_controls', None)
        grid._active = False
        self.zone_id = 12
        self.objects = []
        self.pos = lambda x, y, z: types.SimpleNamespace(x=x, y=y, z=z)
        self.sim = types.SimpleNamespace(position=self.pos(0.25, 5, 0.25), level=1)
        self.lot = types.SimpleNamespace(is_position_on_lot=lambda p: -3 <= p.x <= 3 and -3 <= p.z <= 3)
        self.services = types.SimpleNamespace(
            current_zone_id=lambda: self.zone_id,
            get_active_sim=lambda: self.sim,
            active_lot=lambda: self.lot,
            object_manager=lambda: types.SimpleNamespace(values=lambda: self.objects))
        self.routing = types.SimpleNamespace(
            SurfaceIdentifier=lambda zone, level, kind: (zone, level, kind),
            SurfaceType=types.SimpleNamespace(SURFACETYPE_WORLD=0),
            test_point_placement_in_navmesh=Mock(return_value=True))
        self.terrain = types.SimpleNamespace(get_terrain_height=Mock(side_effect=lambda x, z, routing_surface: 3 * routing_surface[1]))
        self.bb = types.SimpleNamespace(
            has_floor_at_location=Mock(return_value=True),
            is_location_pool=Mock(return_value=False),
            is_location_natural_ground=Mock(return_value=False),
            is_location_outside=Mock(return_value=False),
            get_lowest_level_allowed=lambda: -2,
            get_highest_level_allowed=lambda: 3)
        self.patches = [patch.dict(env.sys.modules, {
            'services': self.services, 'routing': self.routing, 'terrain': self.terrain,
            'build_buy': self.bb, 'sims4.math': types.SimpleNamespace(Vector3=self.pos)}),
            patch.object(grid.speech, 'speak'), patch.object(scanner, '_speak_parts')]
        for item in self.patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in reversed(self.patches)])

    def test_grid_is_read_only_and_queries_current_floor_surface(self):
        self.assertTrue(grid.enter())
        self.assertTrue(grid.move(1, 0))
        self.assertTrue(grid.change_level(1))
        surface, position = self.routing.test_point_placement_in_navmesh.call_args[0]
        self.assertEqual(surface, (12, 2, 0))
        self.assertEqual((position.x, position.y, position.z), (1.25, 6.0, 0.25))
        self.assertEqual((self.sim.position.x, self.sim.position.y), (0.25, 5))

    def test_lot_boundary_and_floor_limits_do_not_move_cursor(self):
        grid.enter()
        grid.move(1, 0)
        grid.move(1, 0)
        self.assertFalse(grid.move(1, 0))
        self.assertEqual(grid._x, 2.25)
        grid.change_level(1)
        grid.change_level(1)
        self.assertFalse(grid.change_level(1))
        self.assertEqual(grid._level, 3)
        self.assertFalse(grid.move(200, 0))

    def test_tile_query_failures_never_become_safe_placement_claims(self):
        grid.enter()
        self.bb.has_floor_at_location.side_effect = RuntimeError('unavailable')
        self.routing.test_point_placement_in_navmesh.return_value = None
        self.assertNotIn('floor', grid.facts())
        self.assertNotIn('navmesh', grid.facts())
        self.assertIn('outside', grid.facts())
        grid.describe()
        spoken = str(scanner._speak_parts.call_args[0][0]).lower()
        self.assertNotIn('safe', spoken)
        self.assertNotIn('clear to build', spoken)

    def test_zone_change_retires_grid(self):
        grid.enter()
        self.zone_id = 99
        self.assertFalse(grid.active())
        self.assertFalse(grid.move(1, 0))

    def test_objects_use_relative_sample_origins_and_refresh_each_time(self):
        grid.enter()
        item = types.SimpleNamespace(position=self.pos(0.65, 3, 0.25), level=1,
                                     is_in_inventory=lambda: False)
        self.objects.append(item)
        self.assertEqual(grid._objects_at_origin(), [item])
        item.position.x = 2
        self.assertEqual(grid._objects_at_origin(), [])
        item.position.x = 0.25
        item.is_in_inventory = lambda: True
        self.assertEqual(grid._objects_at_origin(), [])

    def test_unknown_terrain_height_blocks_movement_without_mutation(self):
        grid.enter()
        self.terrain.get_terrain_height.side_effect = lambda *args, **kwargs: float('nan')
        self.assertFalse(grid.move(1, 0))
        self.assertEqual(grid._x, 0.25)

    def test_grid_validates_before_retiring_build(self):
        self.sim = None
        with patch.object(build, 'active', return_value=True), patch.object(build, 'request') as request:
            self.assertFalse(grid.enter())
            request.assert_not_called()
            self.sim = types.SimpleNamespace(position=self.pos(0.25, 5, 0.25), level=1)
            self.assertTrue(grid.enter())
            request.assert_called_once_with('off')

    def test_grid_projection_snapshot_uses_actual_floor_height_and_rechecks_lot(self):
        grid.enter()
        position, level, zone_id = grid.cursor()
        self.assertEqual((position.x, position.y, position.z, level, zone_id), (0.25, 3, 0.25, 1, 12))
        self.lot.is_position_on_lot = lambda point: False
        self.assertIsNone(grid.cursor())


if __name__ == '__main__':
    unittest.main(verbosity=2)
