"""DaRainbowGirlXX's Build cursor and scanner contribution, merged into the
kit's own modules on 2026-11-12 (first integrated 2026-10-16 as runtime
patches). Scanner ranges live in the scanner, moving furniture in the grid,
walls, room labels, surfaces and layers in their own modules that the grid
calls directly. Her keys are ordinary chords and Build cursor keys: no
polling threads, no monkeypatching."""
import pathlib
import types
import unittest
from unittest.mock import patch

import test_scanner_v5 as env  # noqa: F401  (installs the game stand-ins)
import tyjokr_a11y_scanner as scanner
import tyjokr_a11y_grid as grid
import tyjokr_a11y_keys as keys
import tyjokr_a11y_menu as menu
import tyjokr_a11y_place as place
import tyjokr_a11y_settings as settings
import tyjokr_a11y_shortcuts as shortcuts
import tyjokr_a11y_tiles as tiles
import tyjokr_a11y_wall as wall
import tyjokr_a11y_rooms as rooms
import tyjokr_a11y_surfaces as surfaces
import tyjokr_a11y_layers as layers

SCRIPTS = env.ROOT / 'Scripts'


class MergedTests(unittest.TestCase):
    def test_no_runtime_patching_left(self):
        self.assertFalse((SCRIPTS / 'tyjokr_a11y_contrib.py').exists())
        self.assertFalse((SCRIPTS / 'tyjokr_a11y_contrib_settings.py').exists())
        for name in ('wall', 'rooms', 'surfaces', 'layers', 'scanner', 'grid'):
            text = (SCRIPTS / ('tyjokr_a11y_%s.py' % name)).read_text(encoding='utf-8')
            self.assertNotIn('GetAsyncKeyState', text, name + ' polls keys itself')
            self.assertNotIn('_original_', text, name + ' wraps another module')
            self.assertNotIn('def install(', text, name)

    def test_keymap(self):
        expected = {0x55: 'layerup', 0x44: 'layerdown', 0x4A: 'roomlabel',
                    0xBC: 'scopeprev', 0xBE: 'scopenext', 0x49: 'catalogfind'}
        for vk, intent in expected.items():
            self.assertEqual(keys.CHORDS[vk], (intent, False))
            self.assertIn(vk, keys.CHORD_NAMES)
            self.assertIn(intent, shortcuts.CHORD_LABELS)
        self.assertEqual(keys.BUILD_GRID_KEYS[0x4D], 'moveobject')
        self.assertEqual(keys.CHORDS[0x4D], ('milestones', False), 'Ctrl+Alt+M stays milestones')
        self.assertNotIn(0x4E, keys.CHORDS, "Ctrl+Alt+N is NVDA's")
        self.assertEqual(keys.CHORDS[0x48], ('help', False), 'Ctrl+Alt+H stays the menu')
        self.assertEqual(len(set(keys.CHORDS)), len(keys.CHORDS))
        flash = (env.ROOT / 'flash' / 'TooltipManager_patched.as').read_text(encoding='utf-8')
        self.assertIn('54,77,82].indexOf(key)', flash, 'the Build cursor swallows M natively')

    def test_layer_keys_need_the_build_cursor(self):
        said = []
        keys._input_epoch = 7
        with patch.object(keys, '_editing_active', False), patch.object(keys, '_modal_active', False), \
                patch.object(grid, 'build_cursor', return_value=False), \
                patch.object(grid, 'on_key') as on_key, \
                patch.object(keys.speech, 'speak', side_effect=lambda text, **kw: said.append(text)):
            keys._world_chord('layerup', 7)
        on_key.assert_not_called()
        self.assertIn('Build cursor', said[-1])
        with patch.object(keys, '_editing_active', False), patch.object(keys, '_modal_active', False), \
                patch.object(grid, 'build_cursor', return_value=True), \
                patch.object(grid, 'on_key') as on_key:
            keys._world_chord('roomlabel', 7)
        on_key.assert_called_once_with('roomlabel')

    def test_scope_chords_reach_the_scanner(self):
        keys._input_epoch = 8
        with patch.object(keys, '_editing_active', False), patch.object(keys, '_modal_active', False), \
                patch.object(scanner, 'cycle_range') as cycle:
            keys._world_chord('scopenext', 8)
            keys._world_chord('scopeprev', 8)
        self.assertEqual([c[0] for c in cycle.call_args_list], [(1,), (-1,)])

    def test_settings_and_legacy_section(self):
        for key in ('scanner_range', 'surface_layer_focus', 'experimental_bare_ground',
                    'experimental_water', 'experimental_ceiling', 'experimental_fence', 'chair_alignment_hints'):
            self.assertIn(key, settings.DEFAULTS)
        text = settings._render({})
        self.assertIn('[build cursor]', text)
        self.assertIn('scanner range = 40 meters', text)
        self.assertEqual(settings._FILE_MAP[('contribution', 'scanner scope')], 'scanner_range')
        stored = dict(settings._stored)
        try:
            self.assertEqual(settings._FILE_MAP[('contribution', 'chair alignment hints')], 'chair_alignment_hints')
            settings._apply_value('chair_alignment_hints', 'off')
            self.assertIs(settings._stored['chair_alignment_hints'], False)
            self.assertIn('chair alignment hints = off', settings._render(settings._stored))
            settings._apply_value('scanner_range', 'Whole  Lot')
            self.assertEqual(settings._stored['scanner_range'], 'whole lot')
        finally:
            settings._stored.clear()
            settings._stored.update(stored)
        rows = [row.key for row in menu.ROWS]
        self.assertLess(rows.index('scanner_range'), rows.index('reload'))
        self.assertIn('experimental_fence', [row.key for row in menu._SETTING_ROWS])

    def test_scanner_ranges_keep_sims(self):
        entry = lambda d, sim: types.SimpleNamespace(distance=d, is_sim=sim, level_delta=0, obj_id=1)
        with patch.object(settings, 'get', side_effect=lambda k, d=None: '6 meters' if k == 'scanner_range' else d):
            self.assertTrue(scanner._in_range(entry(5, False), None))
            self.assertFalse(scanner._in_range(entry(7, False), None))
            self.assertTrue(scanner._in_range(entry(90, True), None), 'Sims stay listed, as in the scanner')
            self.assertEqual(scanner._range_limit(), 6.0)
        with patch.object(settings, 'get', side_effect=lambda k, d=None: 'whole lot' if k == 'scanner_range' else d):
            self.assertGreater(scanner._range_limit(), 1000)

    def _walls(self, room, label=None):
        frame = types.SimpleNamespace()
        with patch.object(tiles, 'walls', return_value={0: 'wall', 1: 'open', 2: 'open', 3: 'edge'}), \
                patch.object(tiles, 'doors', return_value={}), \
                patch.object(tiles, 'room', side_effect=room), \
                patch.object(tiles, 'ground', return_value={'outside': False}), \
                patch.object(tiles, 'frame', return_value=frame), \
                patch.object(grid, '_tile', (4, 4)), patch.object(grid, '_level', 0), \
                patch.object(rooms, 'label_for', side_effect=lambda r, level: label(r) if label else None), \
                patch.object(place, 'product', return_value=None):
            return grid._wall_parts(frame), grid._wall_parts(frame, all_sides=True)

    def test_a_wall_between_rooms_is_a_wall(self):
        brief, full = self._walls(lambda f, i, j, level: (i, j))
        self.assertEqual(brief, ['Wall north. '], 'no room talk while nothing is labelled')
        self.assertEqual(full[0], 'North: wall. ')
        self.assertEqual(full[3], 'West: lot edge. ')
        self.assertEqual(len(full), 4, 'number 3 adds no room context')

    def test_labelled_rooms_are_named_across_walls_only(self):
        brief, _full = self._walls(lambda f, i, j, level: (i, j),
                                   label=lambda r: 'kitchen' if r == (4, 5) else None)
        self.assertEqual(brief, ['Wall north. ', 'Current room: unlabelled room. ', 'Across north: kitchen. '],
                         'open sides are not walls, so no room is named across them')

    def test_an_edge_inside_one_space_may_be_a_fence(self):
        brief, full = self._walls(lambda f, i, j, level: 7)
        self.assertEqual(brief, ['Wall or fence north. '])
        self.assertEqual(full[0], 'North: wall, or possibly a fence. ')

    def test_labelled_rooms_are_named_on_entry(self):
        frame = types.SimpleNamespace()
        with patch.object(tiles, 'ground', return_value={'outside': False}), \
                patch.object(tiles, 'room', return_value=5), \
                patch.object(grid, '_last_room', [4, False]), \
                patch.object(rooms, 'label_for', return_value='kitchen'):
            parts, _facts = grid._room_parts(frame)
        self.assertEqual(parts, ['Entering kitchen. '])

    def test_build_place_routes_by_requirement(self):
        item = {'id': 9, 'name': 'Art'}
        with patch.object(place, 'product', return_value=item), \
                patch.object(place, 'requirement', return_value='wall'), \
                patch.object(layers, 'wall_refusal', return_value=False), \
                patch.object(wall, 'place', return_value=True) as hang:
            self.assertTrue(grid._build_place())
        hang.assert_called_once_with(item)
        with patch.object(place, 'product', return_value=item), \
                patch.object(place, 'requirement', return_value='wall'), \
                patch.object(layers, 'wall_refusal', return_value=True), \
                patch.object(wall, 'place') as hang:
            self.assertFalse(grid._build_place())
        hang.assert_not_called()
        with patch.object(place, 'product', return_value=item), \
                patch.object(place, 'requirement', return_value='water'), \
                patch.object(settings, 'get', side_effect=lambda k, d=None: d), \
                patch.object(surfaces, 'place', return_value=True) as wet:
            self.assertTrue(grid._build_place())
        wet.assert_called_once_with(item, 'water')

    def test_experimental_needs_pass_checks_only_when_exact(self):
        said = []
        with patch.object(place, 'product', return_value={'id': 3, 'name': 'Lily'}), \
                patch.object(place, 'in_build_mode', return_value=True), \
                patch.object(place, 'requirement', return_value='water'), \
                patch.object(place, '_say_text', side_effect=lambda en, pl: said.append(en)):
            self.assertIsNone(place._checks(None, 0, (0, 0, 0), guard=False))
        self.assertEqual(said[-1], 'It needs a water surface.')

    def test_wall_objects_are_hung_by_the_game_tool(self):
        """Leo, 2026-10-16: let the game's own Build tool hang wall objects
        (exact placement failed MustBeAgainstWall at every computed spot)."""
        import tyjokr_a11y_plus_build as plus

        class V(object):
            def __init__(self, x, y, z):
                self.x, self.y, self.z = x, y, z
        jobs, said, clicks, sent, timers = [], [], [], [], []
        frame = types.SimpleNamespace()
        item = {'id': 190131, 'name': 'Wall Full Of Stars'}
        common = [patch.object(tiles, 'position', return_value=V(4.5, 0.0, 4.5)),
                  patch.object(wall, 'column_here', return_value=False),
                  patch.object(tiles, 'direction_name', return_value='north'),
                  patch.object(grid, '_tile', (4, 4)), patch.object(grid, '_level', 0),
                  patch.object(place, '_say_text', side_effect=lambda en, pl: said.append(en)),
                  patch.object(plus, 'run_job', side_effect=lambda pts, level, act, desc, **kw: jobs.append((pts, level, act, kw))),
                  patch.object(plus, 'cost_check', return_value=lambda: said.append('result spoken')),
                  patch.object(plus, 'funds', side_effect=[100, 100, 100, 95]),
                  patch.object(wall, '_spot_key', return_value=('zone', 0, (4, 4), 0, 'middle')),
                  patch.object(plus, '_reselect'), patch.object(plus, 'click', side_effect=clicks.append),
                  patch.object(plus.core, 'post', side_effect=lambda fn, *a: fn(*a)),
                  patch.object(plus, '_send_ui', side_effect=lambda m: sent.append(m)),
                  patch.object(wall.time, 'sleep'),
                  patch.object(wall.threading, 'Timer', side_effect=lambda d, fn: timers.append(fn) or types.SimpleNamespace(start=lambda: None, daemon=True))]
        for p in common:
            p.start()
            self.addCleanup(p.stop)
        with patch.dict(plus._cat, {'chosen': None}):
            self.assertFalse(wall.hang_with_game_tool(frame, 0, item, V(4.5, 0.0, 5.0), 1.5))
        self.assertIn('Choose it with Control Alt O first', said[-1])
        self.assertEqual(jobs, [])
        with patch.dict(plus._cat, {'chosen': 3}):
            self.assertTrue(wall.hang_with_game_tool(frame, 0, item, V(4.5, 0.0, 5.0), 1.5))
        (pts, level, act, kw) = jobs[-1]
        self.assertEqual([tuple(round(c, 2) for c in pt) for pt in pts], [(4.5, 4.95)], 'just inside the room')
        self.assertEqual((kw['height'], tuple(round(c, 2) for c in kw['view']), kw['focus_height']), (1.5, (0.0, -1.0), 1.5),
                         'the camera looks at the wall at the chosen height (2026-11-12 screenshots)')
        wall._history.clear()
        with patch.dict(plus._last_error, {'text': 'Must be placed on a wall.', 'at': 1e12}):
            kw['verify']()
        self.assertEqual(wall._history[('zone', 0, (4, 4), 0, 'middle')], (False, 'Must be placed on a wall.'))
        self.assertEqual(said[-1], 'result spoken')
        with patch.dict(plus._product, {'name': 'Some Lamp'}):
            act([(100, 200)])
        self.assertEqual(clicks, [], 'no click while the game holds something else')
        with patch.dict(plus._product, {'name': 'Wall Full Of Stars'}):
            act([(100, 200)])
        self.assertEqual(clicks, [(100, 200)])
        self.assertEqual(sent.count('A11y|plus|wallsup'), 1)
        self.assertEqual(sent.count('A11y|plus|wallsrestore'), 2)
        timers[-1]()
        self.assertEqual(sent[-1], 'A11y|plus|wallsrestore', 'and by the fallback timer')

    def _report(self, on_wall=(), ends=([], []), past=None, column=False):
        with patch.object(wall, 'selected_wall', return_value=(types.SimpleNamespace(), 0)),                 patch.object(wall, 'column_here', return_value=column),                 patch.object(wall, '_on_this_wall', return_value=list(on_wall)),                 patch.object(wall, '_wall_continues', return_value=ends),                 patch.object(wall, '_spot_key', return_value='k'),                 patch.dict(wall._history, {'k': past} if past else {}, clear=True):
            return wall.hang_report()

    def test_hang_report_before_enter(self):
        """Leo, 2026-11-12: say whether it will hang while moving."""
        self.assertEqual(self._report(), ('yes', []))
        self.assertEqual(self._report(column=True)[0], 'no')
        verdict, reasons = self._report(on_wall=[('Octopane', 'window')])
        self.assertEqual((verdict, reasons), ('no', ['Octopane is in this stretch of wall']))
        verdict, reasons = self._report(ends=(['east'], ['west']))
        self.assertEqual((verdict, reasons), ('maybe', ['a door is just west', 'the wall ends to the east']))
        verdict, reasons = self._report(past=(False, 'Must be placed on a wall.'))
        self.assertEqual((verdict, reasons), ('no', ['the game refused this spot before: Must be placed on a wall']))
        verdict, reasons = self._report(ends=(['east'], []), past=(True, ''))
        self.assertEqual(verdict, 'yes', 'a spot that worked before beats a guess')
        with patch.object(wall, 'hang_report', return_value=('maybe', ['the wall ends to the east'])),                 patch.object(wall, '_hinted', [True]),                 patch.object(wall, 'selected_height', return_value=('middle', 1.5)):
            self.assertEqual(wall.fit_parts(), ['Might not fit: the wall ends to the east. ', 'Height middle, 1.5 metres. '])

    def test_a_column_tile_is_refused_with_advice(self):
        import tyjokr_a11y_plus_build as plus
        said = []
        with patch.object(tiles, 'objects_on', return_value=[types.SimpleNamespace(is_sim=False)]), \
                patch.object(scanner, '_tag_names', return_value={'Build_Column'}), \
                patch.object(grid, '_tile', (4, 4)), patch.object(grid, '_level', 0), \
                patch.object(place, '_say_text', side_effect=lambda en, pl: said.append(en)), \
                patch.dict(plus._cat, {'chosen': 3}), patch.object(plus, 'run_job') as job:
            self.assertFalse(wall.hang_with_game_tool(types.SimpleNamespace(), 0, {'id': 1, 'name': 'Art'}, None, 1.5))
        job.assert_not_called()
        self.assertIn('A column stands here', said[-1])

    def test_layers_and_wall_height(self):
        with patch.object(layers, '_mode', 3), patch.object(layers, '_wall_index', 2), \
                patch.object(grid, 'build_cursor', return_value=True), \
                patch.object(layers, 'enabled', return_value=True), \
                patch.object(place, '_say_text'):
            for _ in range(5):
                layers.change_layer(1)
            self.assertEqual(layers._mode, 7, 'ceiling is the top')
            self.assertEqual(wall.selected_height(), ('near the top', 3.0))
            for _ in range(9):
                layers.change_layer(-1)
            self.assertEqual(layers._mode, 0, 'ground is the bottom')
            self.assertEqual(wall.selected_height(), ('very low', 0.5), 'the last wall height is kept')

    def test_sell_and_move_use_a_focused_layer_object(self):
        focused = types.SimpleNamespace(id=5)
        with patch.object(layers, 'focused_target', return_value=focused), \
                patch.object(place, 'sell', side_effect=lambda obj: obj) as sell:
            self.assertIs(grid._sell_here(), focused)
        sell.assert_called_once_with(focused)

    def test_escape_cancels_a_move_before_leaving(self):
        with patch.object(grid, '_build', True), patch.dict(grid._move, {'obj_id': 4, 'name': 'Sofa'}), \
                patch.object(grid, '_say') as say, patch.object(grid, 'leave') as leave:
            self.assertTrue(grid.on_key('back'))
            self.assertIsNone(grid._move['obj_id'])
        leave.assert_not_called()
        say.assert_called_once_with('Move cancelled.', 'Anulowano przesuwanie.')


if __name__ == '__main__':
    unittest.main()
