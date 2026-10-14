"""The Build cursor (Ctrl+Alt+B in Build mode): a lot-aligned tile cursor on
plain keys. Covers the lot frame, fit search, wall reading, the cursor's
readout, rotation, exact placement, the "does not fit, here is where it
fits" offer, key routing and ownership, and the fallback to the plain grid.
Game calls are faked; the live engine is exercised in game.
"""
import math
import sys
import types
import unittest
from unittest.mock import Mock, patch

import test_scanner_v5 as env
import test_keyboard_v7 as keyboard_env     # noqa: F401  (same stubs as the Build tests)
import tyjokr_a11y_grid as grid
import tyjokr_a11y_scanner as scanner
import tyjokr_a11y_tiles as tiles

settings = env.settings
keys = env.keys


def corners(width, depth, angle=0.0, origin=(10.0, 20.0)):
    """Lot corners for a lot rotated by angle (radians)."""
    east = (math.cos(angle), -math.sin(angle))
    north = (math.sin(angle), math.cos(angle))
    point = lambda u, v: types.SimpleNamespace(x=origin[0] + u * east[0] + v * north[0],
                                               z=origin[1] + u * east[1] + v * north[1])
    return [point(0, 0), point(width, 0), point(width, depth), point(0, depth)]


class FrameTests(unittest.TestCase):
    def test_axes_size_and_round_trip_on_a_rotated_lot(self):
        for angle in (0.0, 0.7, math.pi / 2):
            f = tiles.Frame(corners(20, 30, angle))
            self.assertEqual((f.width, f.depth), (20, 30))
            for i, j in ((0, 0), (5, 7), (19, 29)):
                x, z = f.world(i, j)
                self.assertEqual(f.tile_of(x, z), (i, j))
            self.assertTrue(f.inside(19, 29))
            self.assertFalse(f.inside(20, 0))
            self.assertEqual(f.clamp(-3, 99), (0, 29))

    def test_facings_round_trip(self):
        f = tiles.Frame(corners(10, 10, 0.3))
        for facing in range(4):
            self.assertEqual(f.facing_of(f.yaw(facing)), facing)
        self.assertNotAlmostEqual(f.yaw(0), f.yaw(1))

    def test_relative_directions(self):
        with patch.object(tiles.lang, '_locale_lang', 'en'):
            self.assertEqual(tiles.relative(0, 0), 'here')
            self.assertEqual(tiles.relative(1, 2), '2 north, 1 east')
            self.assertEqual(tiles.relative(-3, -1), '1 south, 3 west')

    def test_a_degenerate_lot_has_no_frame(self):
        with self.assertRaises(ValueError):
            tiles.Frame(corners(0, 10))


class FitTests(unittest.TestCase):
    def setUp(self):
        self.f = tiles.Frame(corners(10, 10))
        position = patch.object(tiles, 'position', side_effect=lambda f, i, j, level, du=0.5, dv=0.5: (i, j, du, dv))
        position.start()
        self.addCleanup(position.stop)

    def test_the_centre_is_tried_first_then_edges(self):
        tried = []

        def fake(obj, def_id, point, angle, level, ignore=()):
            tried.append(point[2:])
            return (point[2:] == (0.5, 1.0)), 'a wall is in the way'
        with patch.object(tiles, 'test_fit', side_effect=fake):
            point, why = tiles.fit_at(self.f, 7, 2, 2, 0, 0)
        self.assertEqual(point, (2, 2, 0.5, 1.0))
        self.assertEqual(tried[:2], [(0.5, 0.5), (0.5, 1.0)])

    def test_no_answer_is_not_a_refusal(self):
        with patch.object(tiles, 'test_fit', return_value=(None, None)):
            self.assertEqual(tiles.fit_at(self.f, 7, 2, 2, 0, 0), (None, None))
        with patch.object(tiles, 'test_fit', return_value=(False, 'something is in the way')):
            self.assertEqual(tiles.fit_at(self.f, 7, 2, 2, 0, 0), (None, 'something is in the way'))

    def test_nearest_fit_prefers_closer_tiles_and_the_current_facing(self):
        # Nearest tile first; among tiles equally near, the current facing.
        good = {((5, 3), 1), ((4, 5), 0), ((6, 5), 1), ((7, 5), 0)}

        def fake(f, def_id, i, j, level, facing, obj=None):
            return ((i, j, facing), None) if ((i, j), facing) in good else (None, 'x')
        with patch.object(tiles, 'fit_at', side_effect=fake):
            self.assertEqual(tiles.nearest_fit(self.f, 7, 5, 5, 0, 0)[:2], (4, 5))
            self.assertEqual(tiles.nearest_fit(self.f, 7, 5, 5, 0, 1)[:2], (6, 5))
        with patch.object(tiles, 'fit_at', return_value=(None, 'x')):
            self.assertIsNone(tiles.nearest_fit(self.f, 7, 5, 5, 0, 0))

    def test_test_fit_reads_tuples_and_booleans(self):
        build_buy = types.SimpleNamespace(test_location_for_object=Mock(return_value=(False, ['Intersects wall'])))
        math_mod = types.SimpleNamespace(Location=lambda t, s: ('loc', t, s), Transform=lambda p, q: (p, q),
                                         angle_to_yaw_quaternion=lambda a: ('q', a))
        with patch.dict(sys.modules, {'build_buy': build_buy, 'sims4.math': math_mod}), \
                patch.object(tiles, 'surface', return_value='surface'), \
                patch.object(tiles.lang, '_locale_lang', 'en'):
            import sims4
            with patch.object(sims4, 'math', math_mod, create=True):
                self.assertEqual(tiles.test_fit(None, 7, 'p', 0.0, 0), (False, 'a wall is in the way'))
                build_buy.test_location_for_object.return_value = True
                self.assertEqual(tiles.test_fit(None, 7, 'p', 0.0, 0), (True, None))
                build_buy.test_location_for_object.side_effect = RuntimeError('native')
                self.assertEqual(tiles.test_fit(None, 7, 'p', 0.0, 0), (None, None))


class WallTests(unittest.TestCase):
    def test_walls_doors_and_edges(self):
        f = tiles.Frame(corners(3, 3))
        hits = {}
        routing = types.SimpleNamespace(
            Location=lambda p, q, s: p, RAYCAST_HIT_TYPE_IMPASSABLE=2,
            ray_test_verbose=lambda a, b, ctx, return_object_id=True: hits.get((a, b), (0, 0)))
        math_mod = types.SimpleNamespace(Quaternion=types.SimpleNamespace(IDENTITY=lambda: 'id'))
        with patch.dict(sys.modules, {'routing': routing, 'sims4.math': math_mod}), \
                patch.object(tiles, 'position', side_effect=lambda f, i, j, level, du=0.5, dv=0.5: (i, j)), \
                patch.object(tiles, 'surface', return_value='s'), \
                patch.object(tiles, '_raycast_context', return_value='ctx'):
            import sims4
            with patch.object(sims4, 'math', math_mod, create=True):
                hits[((1, 1), (1, 2))] = (2, 0)       # north: a wall
                hits[((1, 1), (2, 1))] = (2, 55)      # east: blocked by an object, not a wall
                self.assertEqual(tiles.walls(f, 1, 1, 0), {0: 'wall', 1: 'open', 2: 'open', 3: 'open'})
                self.assertEqual(tiles.walls(f, 0, 0, 0)[2], 'edge')


class CursorTests(unittest.TestCase):
    def setUp(self):
        self.saved = dict(settings._stored)
        self.addCleanup(lambda: (settings._stored.clear(), settings._stored.update(self.saved)))
        settings._stored['build_controls'] = True
        grid._active = True
        grid._build = True
        grid._tile, grid._facing, grid._offer, grid._level = (4, 4), 0, None, 0
        grid._last_room[0] = grid._last_room[1] = None
        keys._modal_active = keys._editing_active = False
        self.frame = tiles.Frame(corners(10, 10))
        self.place = Mock()
        self.place.in_build_mode.return_value = True
        self.place.product.return_value = {'id': 7, 'name': 'Cheap Bed', 'zone': 1}
        self.place.requirement.return_value = None
        self.place._NEEDS = {'wall': ('It hangs on a wall.', 'pl')}
        self.spoken, self.sent = [], []
        self.fits = {}
        patches = [
            patch.dict('sys.modules', {'tyjokr_a11y_place': self.place}),
            patch.object(grid, 'active', return_value=True),
            patch.object(grid, '_surface', return_value='surface'),
            patch.object(grid, '_flash', side_effect=self.sent.append),
            patch.object(grid, '_say', side_effect=lambda en, pl: self.spoken.append(en)),
            patch.object(scanner, '_speak_parts', side_effect=lambda parts: self.spoken.append(
                ''.join(p if isinstance(p, str) else '<name>' for p in parts))),
            patch.object(tiles, 'frame', return_value=self.frame),
            patch.object(tiles, 'objects_on', return_value=[]),
            patch.object(tiles, 'walls', return_value={0: 'wall', 1: 'open', 2: 'open', 3: 'open'}),
            patch.object(tiles, 'doors', return_value={}),
            patch.object(tiles, 'ground', return_value={'floor': True, 'outside': False}),
            patch.object(tiles, 'room', return_value=1),
            patch.object(tiles, 'fit_at', side_effect=lambda f, d, i, j, level, facing, obj=None:
                         self.fits.get((i, j, facing), (None, 'a wall is in the way'))),
            patch.object(tiles, 'nearest_fit', return_value=(6, 4, 'spot', 1)),
            patch.object(tiles.lang, '_locale_lang', 'en'),
            patch.object(grid.lang, '_locale_lang', 'en'),
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def test_each_step_reads_the_tile(self):
        self.fits[(4, 5, 0)] = ('p', None)
        self.assertTrue(grid.move(0, 1))
        self.assertEqual(grid._tile, (4, 5))
        self.assertEqual(self.spoken[-1], 'Empty floor. Wall north. Fits here, facing north. ')
        self.fits.clear()
        grid.move(1, 0)
        self.assertIn('Does not fit here facing north: a wall is in the way.', self.spoken[-1])

    def test_lot_edge_stops_the_cursor(self):
        grid._tile = (9, 4)
        self.assertFalse(grid.move(1, 0))
        self.assertEqual((grid._tile, self.spoken[-1]), ((9, 4), 'Lot edge.'))

    def test_room_and_outside_changes_are_announced(self):
        grid.describe()
        with patch.object(tiles, 'room', return_value=2):
            grid.describe()
        self.assertTrue(self.spoken[-1].startswith('Another room. '))
        with patch.object(tiles, 'ground', return_value={'floor': False, 'outside': True}):
            grid.describe()
        self.assertTrue(self.spoken[-1].startswith('Outside. Empty ground.'))

    def test_r_turns_the_facing_and_reports_the_fit(self):
        self.fits[(4, 4, 1)] = ('p', None)
        grid.on_key('turn')
        self.assertEqual((grid._facing, self.spoken[-1]), (1, 'Facing east. Fits here. '))
        grid.on_key('turnback')
        grid.on_key('turnback')
        self.assertEqual(grid._facing, 3)
        self.assertEqual(self.spoken[-1], 'Facing west. Does not fit here: a wall is in the way. ')

    def test_enter_places_exactly_when_it_fits(self):
        self.fits[(4, 4, 0)] = ('exact point', None)
        grid.on_key('place')
        self.place.place.assert_called_once_with('exact point', 0, 'surface', angle=self.frame.yaw(0), exact=True)

    def test_enter_offers_the_nearest_fit_and_a_second_enter_takes_it(self):
        grid.on_key('place')
        self.place.place.assert_not_called()
        self.assertIn('Cheap Bed does not fit here: a wall is in the way. It fits 2 east, facing east.', self.spoken[-1])
        self.assertIn('Press Enter again', self.spoken[-1])
        grid.on_key('place')
        self.place.place.assert_called_once_with('spot', 0, 'surface', angle=self.frame.yaw(1), exact=True)

    def test_moving_or_turning_cancels_the_offer(self):
        grid.on_key('place')
        grid.move(0, -1)
        grid.move(0, 1)
        grid.on_key('place')
        self.assertEqual(self.place.place.call_count, 0)     # asked again, not taken
        grid.on_key('turn')
        self.assertIsNone(grid._offer)

    def test_nothing_fits_nearby(self):
        with patch.object(tiles, 'nearest_fit', return_value=None):
            self.assertFalse(grid.on_key('place'))
        self.assertIn('No tile within 5 fits it either', self.spoken[-1])

    def test_surface_objects_use_the_slot_search_and_unsupported_needs_refuse(self):
        self.place.requirement.return_value = 'slot'
        with patch.object(grid, 'cursor', return_value=('centre', 0, 1)):
            grid.on_key('place')
        self.place.place.assert_called_once_with('centre', 0, 'surface')
        self.place.requirement.return_value = 'wall'
        grid.on_key('place')
        self.place._say_text.assert_called_once_with('It hangs on a wall.', 'pl')

    def test_no_product_says_how_to_choose_one(self):
        self.place.product.return_value = None
        self.assertFalse(grid.on_key('place'))
        self.assertIn('Choose an object in the Build catalog first', self.spoken[-1])

    def test_detail_keys(self):
        grid.on_key('info3')
        self.assertEqual(self.spoken[-1], 'North: wall. East: open. South: open. West: open. ')
        grid.on_key('info6')
        self.assertTrue(self.spoken[-1].startswith('Column 5 of 10, row 5 of 10, floor 0.'))
        grid.on_key('info5')
        self.assertIn('Cheap Bed. Facing north.', self.spoken[-1])

    def test_objects_are_named_with_what_is_on_them(self):
        table = types.SimpleNamespace(id=3)
        with patch.object(tiles, 'objects_on', return_value=[table]), \
                patch.object(tiles, 'children_on', return_value=['plate']), \
                patch.object(tiles, 'free_spots', return_value=2), \
                patch.object(grid, '_name', side_effect=lambda obj: 'Table' if obj is table else 'Plate'):
            grid.describe()
        self.assertTrue(self.spoken[-1].startswith('Table with Plate on it, free spots: 2. '))

    def test_leaving_hands_the_keys_back(self):
        grid.on_key('back')
        self.assertEqual(self.sent, ['A11yBuildGridOff'])
        self.assertFalse(grid._build)


class StartTests(unittest.TestCase):
    def test_build_mode_start_and_fallback(self):
        grid._build = False
        sent, spoken = [], []
        place = Mock()
        place.product.return_value = None
        lot = types.SimpleNamespace(get_default_position=lambda: types.SimpleNamespace(x=15.0, z=20.1))
        services = types.SimpleNamespace(active_lot=lambda: lot)
        with patch.dict('sys.modules', {'tyjokr_a11y_place': place, 'services': services}), \
                patch.object(grid, '_flash', side_effect=sent.append), \
                patch.object(scanner, '_speak_parts', side_effect=lambda parts: spoken.append(''.join(parts))), \
                patch.object(grid.lang, '_locale_lang', 'en'), patch.object(tiles.lang, '_locale_lang', 'en'):
            grid._x, grid._z = 13.2, 25.7
            with patch.object(tiles, 'frame', return_value=tiles.Frame(corners(10, 10))):
                self.assertTrue(grid._start_build(''))
            self.assertEqual((grid._tile, sent), ((3, 5), ['A11yBuildGridOn']))
            self.assertIn('Arrow keys move one tile', spoken[-1])
            self.assertIn('The street is to the south', spoken[-1])
            grid._build = False
            with patch.object(tiles, 'frame', return_value=None):
                self.assertFalse(grid._start_build(''))
            self.assertFalse(grid._build)


class RoutingTests(unittest.TestCase):
    def setUp(self):
        keys._modal_active = keys._editing_active = False
        keys._build_grid_owner = False
        keys._enabled = True
        self.addCleanup(lambda: setattr(keys, '_build_grid_owner', False))

    def test_plain_keys_route_only_while_the_cursor_owns_them(self):
        self.assertIsNone(keys._plain_message(0x52))
        epoch = keys._input_epoch
        self.assertTrue(keys.a11y_buildgridowner('1'))
        self.assertEqual(keys._input_epoch, epoch + 1)
        for vk, intent in ((0x26, 'up'), (0x25, 'left'), (0x0D, 'place'), (0x52, 'turn'), (0x1B, 'back'),
                           (0x31, 'info1'), (0x36, 'info6'), (0x21, 'floorup'), (0x24, 'last'), (0x2E, 'sell')):
            self.assertEqual(keys._plain_message(vk), 'A11yBuildGrid:' + intent)
        self.assertEqual(keys._plain_message(0x52, shift=True), 'A11yBuildGrid:turnback')
        self.assertNotEqual(keys._plain_message(0x26, shift=True), 'A11yBuildGrid:up')
        self.assertIsNone(keys._plain_message(0x26, ctrl=True, alt=True))
        keys._modal_active = True
        self.assertNotEqual(keys._plain_message(0x52), 'A11yBuildGrid:turn')
        keys._modal_active, keys._editing_active = False, True
        self.assertIsNone(keys._plain_message(0x52))
        self.assertFalse(keys.a11y_buildgridowner('2'))
        self.assertIn('A11yBuildGrid:up', keys._REPEATABLE)

    def test_the_pump_rechecks_ownership(self):
        keys.a11y_buildgridowner('1')
        with patch.object(grid, 'build_cursor', return_value=True), patch.object(grid, 'on_key') as on_key:
            keys._build_grid_key('up', keys._input_epoch)
            on_key.assert_called_once_with('up')
            keys._build_grid_key('up', keys._input_epoch - 1)
            keys.a11y_buildgridowner('0')
            keys._build_grid_key('up', keys._input_epoch)
            self.assertEqual(on_key.call_count, 1)
        keys.a11y_buildgridowner('1')
        with patch.object(grid, 'build_cursor', return_value=False), patch.object(grid, 'on_key') as on_key:
            keys._build_grid_key('up', keys._input_epoch)
            on_key.assert_not_called()


if __name__ == '__main__':
    unittest.main()
