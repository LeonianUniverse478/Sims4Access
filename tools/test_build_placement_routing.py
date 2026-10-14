"""Routing for Build placement on the lot grid: Ctrl+Alt+B, grid Enter,
rotate/undo/redo/sell, scanner mode in Build, pending cancellation and the
Build-exit reset. Run with py -3.7 tools/test_build_placement_routing.py.
"""
import types
import unittest
from unittest.mock import Mock, patch

import test_scanner_v5 as env
import test_keyboard_v7 as keyboard_env     # noqa: F401  (same stubs as the Build tests)
import tyjokr_a11y_build as build
import tyjokr_a11y_grid as grid
import tyjokr_a11y_place as place
import tyjokr_a11y_shortcuts as shortcuts

settings = env.settings
keys = env.keys


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.saved = dict(settings._stored)
        self.addCleanup(lambda: (settings._stored.clear(), settings._stored.update(self.saved)))
        settings._stored['build_controls'] = True
        env.queue.clear()
        grid._active = False
        keys._modal_active = keys._editing_active = False
        self.place = Mock()
        self.place.in_build_mode.return_value = True
        self.spoken = []
        for item in (patch.object(env.speech, 'speak', lambda text, **kw: self.spoken.append(text)),
                     patch.dict('sys.modules', {'tyjokr_a11y_place': self.place})):
            item.start()
            self.addCleanup(item.stop)

    def test_chords(self):
        self.assertEqual(keys.CHORDS[0x42], ('buildplace', False))
        self.assertEqual(keys.CHORDS[0x58], ('sell', False))
        self.assertEqual(keys.CHORD_NAMES[0x58], 'X')
        self.assertNotIn('buildtoggle', {intent for intent, _ in keys.CHORDS.values()})
        for intent in ('buildplace', 'sell'):
            self.assertNotEqual(shortcuts.CHORD_LABELS.get(intent, intent), intent)
            self.assertIn(intent, shortcuts.BUILD_INTENTS)

    def test_ctrl_alt_b_toggles_the_placement_grid(self):
        with patch.object(grid, 'placement_toggle') as toggle:
            keys._world_chord('buildplace', keys._input_epoch)
            toggle.assert_called_once_with()
        keys._modal_active = True           # the catalog scope must not block the toggle
        with patch.object(grid, 'placement_toggle') as toggle:
            keys._world_chord('buildplace', keys._input_epoch)
            toggle.assert_called_once_with()

    def test_placement_toggle_needs_build_mode(self):
        self.place.in_build_mode.return_value = False
        with patch.object(grid, 'toggle') as toggle:
            self.assertFalse(grid.placement_toggle())
            toggle.assert_not_called()
        self.assertIn('Enter Build mode first', self.spoken[-1])
        self.place.in_build_mode.return_value = True
        with patch.object(grid, 'toggle', return_value=True) as toggle:
            self.assertTrue(grid.placement_toggle())
            toggle.assert_called_once_with()

    def test_scanner_mode_blocks_the_grid_only_in_live_mode(self):
        with patch.object(keys, '_scanner_effective', return_value=True):
            self.place.in_build_mode.return_value = False
            self.assertFalse(grid.enter())
            self.assertIn('Turn scanner mode off', self.spoken[-1])
            self.place.in_build_mode.return_value = True
            services = types.ModuleType('services')
            services.get_active_sim = lambda: types.SimpleNamespace(
                position=types.SimpleNamespace(x=1.0, z=2.0), level=0)
            services.active_lot = lambda: types.SimpleNamespace(is_position_on_lot=lambda position: True)
            services.current_zone_id = lambda: 5
            with patch.dict('sys.modules', {'services': services}),                     patch.object(grid, '_controls_enabled', return_value=True),                     patch.object(build, 'active', return_value=False),                     patch.object(build, 'aiming', return_value=False),                     patch.object(grid, 'describe', return_value=True),                     patch.object(grid, 'announce_placement', return_value=True) as announce:
                self.assertTrue(grid.enter())
                announce.assert_called_once_with('')     # no start note: the Sim is on the lot

    def active_grid(self):
        grid._active = True
        return patch.object(grid, 'active', return_value=True)

    def test_grid_keys_in_build_mode(self):
        with self.active_grid(), \
                patch.object(grid, 'cursor', return_value=('pos', 1, 5)), \
                patch.object(grid, '_surface', return_value='surface'):
            grid.on_key('open')
            self.place.place.assert_called_once_with('pos', 1, 'surface')
            grid.on_key('rotateleft')
            self.place.rotate.assert_called_with(-1)
            grid.on_key('rotateright')
            self.place.rotate.assert_called_with(1)
            grid.on_key('undo')
            self.place.undo.assert_called_once_with()
            self.assertFalse(grid.on_key('redo'))
            self.assertIn('Nothing to redo', self.spoken[-1])

    def test_grid_enter_describes_outside_build_mode(self):
        self.place.in_build_mode.return_value = False
        with self.active_grid(), patch.object(grid, 'describe', return_value=True) as describe:
            grid.on_key('open')
            describe.assert_called_once_with()
            self.place.place.assert_not_called()

    def test_enter_on_an_unusable_point_places_nothing(self):
        with self.active_grid(), patch.object(grid, 'cursor', return_value=None):
            self.assertFalse(grid.on_key('open'))
            self.place.place.assert_not_called()
            self.assertIn('cannot take an object', self.spoken[-1])

    def test_sell_picks_the_first_object_that_is_not_a_sim(self):
        sim = types.SimpleNamespace(is_sim=True)
        chair = types.SimpleNamespace(is_sim=False)
        with self.active_grid(), patch.object(grid, '_objects_at_origin', return_value=[sim, chair]):
            grid.on_key('sell')
            self.place.sell.assert_called_once_with(chair)
        self.place.sell.reset_mock()
        with self.active_grid(), patch.object(grid, '_objects_at_origin', return_value=[sim]):
            grid.on_key('sell')
            self.place.sell.assert_called_once_with(None)

    def test_sell_picks_the_topmost_object(self):
        # Live 2026-09-26: desk first in object order, computer on top of it.
        desk = types.SimpleNamespace(is_sim=False, parent=None)
        computer = types.SimpleNamespace(is_sim=False, parent=desk)
        with self.active_grid(), patch.object(grid, '_objects_at_origin', return_value=[desk, computer]):
            grid.on_key('sell')
            self.place.sell.assert_called_once_with(computer)

    def test_leaving_the_grid_cancels_a_pending_placement(self):
        grid.leave()
        self.place.cancel_pending.assert_called_once_with()
        grid.retire()
        self.assertEqual(self.place.cancel_pending.call_count, 2)

    def test_sell_and_transaction_chords_never_reach_the_scanner(self):
        with patch.object(grid, 'active', return_value=False), \
                patch.object(build, 'active', return_value=False), \
                patch.object(build, 'aiming', return_value=False), \
                patch('tyjokr_a11y_scanner.on_key') as scanner_key:
            keys._world_chord('sell', keys._input_epoch)
            scanner_key.assert_not_called()

    def test_focus_position_moves_the_cursor_and_floor(self):
        grid._x, grid._z, grid._level = 0.0, 0.0, 0
        with patch.object(grid, 'active', return_value=False):
            self.assertFalse(grid.focus_position(types.SimpleNamespace(x=3.0, z=4.0), 1))
        with patch.object(grid, 'active', return_value=True):
            self.assertTrue(grid.focus_position(types.SimpleNamespace(x=3.5, z=-2.0), 1))
            self.assertEqual((grid._x, grid._z, grid._level), (3.5, -2.0, 1))
            self.assertFalse(grid.focus_position(types.SimpleNamespace(x=float('nan'), z=0.0), 0))
            self.assertEqual((grid._x, grid._z, grid._level), (3.5, -2.0, 1))

    def test_start_point_is_always_on_the_lot(self):
        class Lot(object):
            center = types.SimpleNamespace(x=10.0, z=10.0, name='centre')
            def __init__(self, on_lot):
                self.on_lot = on_lot
            def is_position_on_lot(self, position):
                return getattr(position, 'name', '') in self.on_lot
            def get_default_position(self):
                return types.SimpleNamespace(x=5.0, z=2.0, name='front')
        sim = types.SimpleNamespace(position=types.SimpleNamespace(x=0.0, z=-3.0, name='lawn'), level=1)
        position, level, note = grid._start_point(sim, Lot({'lawn', 'centre', 'front'}))
        self.assertEqual((position.name, level, note), ('lawn', 1, None))
        sim.position = types.SimpleNamespace(x=0.0, z=-9.0, name='sidewalk')
        position, level, note = grid._start_point(sim, Lot({'centre', 'front'}))
        self.assertEqual((position.name, level), ('centre', 0))
        self.assertIn('off the lot', note[0])
        position, level, note = grid._start_point(sim, Lot({'front'}))
        self.assertEqual(position.name, 'front')
        with self.assertRaises(ValueError):
            grid._start_point(sim, Lot(set()))

    def test_build_exit_forgets_the_product(self):
        build.on_build_buy_exit()
        self.place.forget.assert_called_once_with()

    def test_build_entry_retires_a_live_grid(self):
        # Live 2026-09-26: the read-only grid carried into Build unannounced
        # and the first Ctrl+Alt+B said "Lot grid off".
        with patch.object(grid, 'active', return_value=True), patch.object(grid, 'retire') as retire:
            self.assertTrue(build.on_build_buy_enter())
            retire.assert_called_once_with()
        with patch.object(grid, 'active', return_value=False), patch.object(grid, 'retire') as retire:
            self.assertTrue(build.on_build_buy_enter())
            retire.assert_not_called()
        self.assertEqual(self.spoken, [])           # silent, like the exit

    def test_build_entry_survives_a_grid_failure(self):
        with patch.object(grid, 'active', side_effect=RuntimeError('zone gone')):
            self.assertTrue(build.on_build_buy_enter())

    def test_build_exit_turns_the_placement_grid_off(self):
        with patch.object(grid, 'active', return_value=True), patch.object(grid, 'retire') as retire:
            build.on_build_buy_exit()
            retire.assert_called_once_with()
        with patch.object(grid, 'active', return_value=False), patch.object(grid, 'retire') as retire:
            build.on_build_buy_exit()
            retire.assert_not_called()


if __name__ == '__main__':
    unittest.main()
