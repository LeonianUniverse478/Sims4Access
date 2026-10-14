"""Build controls switch: one setting gates the Build cursor, the Build
actions window and the read-only lot grid; on by default.

Off refuses every activation with one spoken reason, retires what this
session started (silently), never announces a late client activation, and
still lets a release through. The client hears A11y|buildcontrols|on/off
at zone load, on every settings change, just before each activation and
with every keyboard lease. Run with py -3.7 tools/test_build_controls.py.
"""
import os
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

import test_scanner_v5 as env
import test_keyboard_v7 as keyboard_env
import tyjokr_a11y_build as build
import tyjokr_a11y_grid as grid
import tyjokr_a11y_hub as hub
import tyjokr_a11y_narrator as narrator
import tyjokr_a11y_shortcuts as shortcuts

settings = env.settings
keys = env.keys
menu = env.menu
lang = env.lang
OFF_NOTICE = 'Build controls are off. Turn them on in the settings menu.'


def switch(on):
    settings._stored['build_controls'] = on


class Base(unittest.TestCase):
    def setUp(self):
        self.saved = dict(settings._stored)
        self.addCleanup(self.restore)
        switch(False)
        env.queue.clear()
        env.messages.clear()
        build._active = False
        build._pending.clear()
        build._serial = build._last_serial = build._release_serial = 0
        build._zone_id = None
        build._aim_pending = 0
        build._last_feedback = ''
        grid._active = False
        self.zone = types.SimpleNamespace(id=12, is_in_build_buy=True)
        self.patches = [patch.object(build, '_zone', side_effect=lambda: self.zone),
                        patch.object(env.speech, 'speak')]
        for item in self.patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in reversed(self.patches)])

    def restore(self):
        settings._stored.clear()
        settings._stored.update(self.saved)

    def spoken(self):
        return [call[0][0] for call in env.speech.speak.call_args_list]


class SettingTests(Base):
    def test_default_is_on_and_the_file_says_so(self):
        settings._stored.pop('build_controls')
        self.assertTrue(settings.DEFAULTS['build_controls'])
        self.assertTrue(settings.get('build_controls'))
        self.assertTrue(build.controls_enabled())
        text = settings.render_default()
        features = text.split('[features]')[1].split('[speech]')[0]
        self.assertIn('build controls = on', features)
        self.assertNotIn(chr(0x2014), text)   # no em dash in shipped copy
        self.assertNotIn(chr(0x2013), text)   # no en dash either

    def test_hand_edit_and_reload_round_trip(self):
        old_path = settings.PATH
        with tempfile.TemporaryDirectory() as folder:
            settings.PATH = os.path.join(folder, 'test.cfg')
            try:
                with open(settings.PATH, 'w', encoding='utf-8') as handle:
                    handle.write(settings.render_default())
                settings.reload()
                self.assertTrue(settings.get('build_controls'))
                settings.set('build_controls', False)
                with open(settings.PATH, encoding='utf-8') as handle:
                    self.assertIn('build controls = off', handle.read())
                settings.reload()
                self.assertFalse(settings.get('build_controls'))  # explicit off survives
                with open(settings.PATH, 'w', encoding='utf-8') as handle:
                    handle.write('[features]\nbuild controls = maybe\n')
                settings.reload()
                self.assertTrue(settings.get('build_controls'))        # default kept
                self.assertTrue(any('build_controls' in err for err in settings.load_errors))
            finally:
                settings.PATH = old_path
                del settings.load_errors[:]

    def test_menu_row_toggles_and_retires(self):
        row = next(r for r in menu.ROWS if r.key == 'build_controls')
        self.assertEqual(row.kind, 'bool')
        self.assertEqual(lang.t(row.term), 'Build controls')
        with patch.object(settings, '_save', return_value=True), \
                patch.object(build, 'apply_setting') as applied:
            menu._apply(row, True)
            self.assertTrue(settings.get('build_controls'))
            menu._apply(row, False)
            self.assertFalse(settings.get('build_controls'))
        self.assertEqual(applied.call_count, 2)

    def test_readout_lists_the_switch(self):
        lines = []
        with patch.object(env.commands, 'CheatOutput', lambda connection: lines.append):
            narrator.a11y_settings()
        self.assertTrue(any('Build controls off' in line for line in lines), lines)
        switch(True)
        lines[:] = []
        with patch.object(env.commands, 'CheatOutput', lambda connection: lines.append):
            narrator.a11y_settings()
        self.assertTrue(any('Build controls on' in line for line in lines), lines)

    def test_reload_applies_build_and_travel_switches(self):
        import tyjokr_a11y_travel as travel
        with patch.object(settings, 'reload'), patch.object(env.speech, 'restart_sapi'), \
                patch.object(env.speech, 'retry_screen_reader', return_value=False), \
                patch.object(env.speech, 'clear_caption'), \
                patch.object(narrator, '_push_autofocus'), \
                patch.object(build, 'apply_setting') as build_applied, \
                patch.object(travel, 'apply_setting') as travel_applied:
            self.assertTrue(narrator.a11y_reload())
        build_applied.assert_called_once_with()
        travel_applied.assert_called_once_with()


class GateTests(Base):
    def test_every_activation_is_refused_with_one_reason_and_nothing_sent(self):
        for action in ('on', 'toggle', 'left', 'click', 'undo', 'redo', 'rotateleft', 'status', 'grid', 'center'):
            env.speech.speak.reset_mock()
            self.assertFalse(build.request(action), action)
            self.assertEqual(self.spoken(), [OFF_NOTICE], action)
        for action in sorted(build.MENU_ACTIONS):
            self.assertFalse(build.request_menu(action))
        self.assertFalse(build.aim_grid())
        self.assertFalse(build.toggle())
        self.assertFalse(build.command('on'))
        self.assertEqual(env.messages, [])
        self.assertEqual(build._pending, {})

    def test_release_still_goes_through_while_off(self):
        self.assertTrue(build.request('off'))
        self.assertEqual(env.messages, ['A11y|build|off|1'])

    def test_build_actions_window_and_console_are_refused(self):
        with patch.object(hub, '_window') as window:
            self.assertFalse(hub.build_actions())
            self.assertFalse(hub.a11y_buildmenu())
        window.assert_not_called()
        self.assertEqual(self.spoken(), [OFF_NOTICE, OFF_NOTICE])

    def test_hub_lists_build_rows_only_while_on(self):
        names = []
        with patch.object(hub, '_window', side_effect=lambda title, text, rows: names.append([r[0] for r in rows])), \
                patch.object(hub.menu, '_raw', side_effect=lambda text: text):
            hub.open_hub()
            switch(True)
            hub.open_hub()
        # 2026-09-26: one Build row. Live mode offers the read-only grid; Build
        # mode offers object placement. The pixel cursor and its actions window
        # are console-only (a11y.build, a11y.buildmenu).
        build_rows = {lang.t('build cursor'), lang.t('build actions'), lang.t('read-only lot grid'),
                      lang.t('build placement')}
        self.assertFalse(build_rows & set(names[0]))
        self.assertEqual(build_rows & set(names[1]), {lang.t('read-only lot grid')})
        self.assertEqual(len(names[1]) - len(names[0]), 1)
        self.assertEqual(names[0][-1], lang.t('settings menu'))    # the way back on stays last
        import tyjokr_a11y_place as place
        with patch.object(hub, '_window', side_effect=lambda title, text, rows: names.append([r[0] for r in rows])), \
                patch.object(hub.menu, '_raw', side_effect=lambda text: text), \
                patch.object(place, 'in_build_mode', return_value=True):
            hub.open_hub()
        self.assertEqual(build_rows & set(names[2]), {lang.t('build placement')})
        self.assertNotEqual(lang.t('build placement'), 'build placement')

    def test_native_feedback_is_ignored_while_off(self):
        build._zone_id = 12
        self.assertFalse(build.info('name|Chair'))
        env.speech.speak.assert_not_called()

    def test_active_and_aiming_read_false_while_off(self):
        build._active, build._zone_id, build._aim_pending = True, 12, 3
        build._aim_until = 1e18
        self.assertFalse(build.active())
        self.assertFalse(build.aiming())


class GridGateTests(Base):
    def setUp(self):
        super().setUp()
        # grid.enter checks the start point is on the lot (off-lot Sims start at the lot centre).
        self.services = types.SimpleNamespace(current_zone_id=lambda: 12,
                                              active_lot=lambda: types.SimpleNamespace(is_position_on_lot=lambda p: True),
                                              get_active_sim=lambda: None)
        modules = patch.dict(env.sys.modules, {'services': self.services})
        modules.start()
        self.addCleanup(modules.stop)

    def test_grid_refuses_to_start_and_reads_inactive_while_off(self):
        self.assertFalse(grid.enter())
        self.assertFalse(grid.toggle())
        self.assertEqual(self.spoken(), [OFF_NOTICE, OFF_NOTICE])
        grid._active, grid._zone_id = True, 12
        self.assertFalse(grid.active())
        self.assertFalse(grid.move(1, 0))
        self.assertIsNone(grid.cursor())

    def test_grid_console_refuses_all_but_leaving(self):
        self.assertFalse(grid.command('on'))
        self.assertFalse(grid.command('toggle'))
        self.assertTrue(grid.command('off'))            # leaving is always allowed
        self.assertEqual(self.spoken()[:2], [OFF_NOTICE, OFF_NOTICE])

    def test_grid_enter_works_when_on(self):
        switch(True)
        with patch.object(grid, 'describe', return_value=True):
            self.services.get_active_sim = lambda: types.SimpleNamespace(
                position=types.SimpleNamespace(x=1.0, z=2.0), level=0)
            self.assertTrue(grid.enter())
        self.assertTrue(grid.active())


class RetireTests(Base):
    def turn_on_cursor(self):
        switch(True)
        self.assertTrue(build.request('on'))
        self.assertTrue(build.state('1|1|on|220|180|16'))
        self.assertTrue(build.active())
        env.messages.clear()
        env.speech.speak.reset_mock()

    def test_switching_off_releases_silently_then_tells_the_client(self):
        self.turn_on_cursor()
        grid._active, grid._zone_id = True, 12
        switch(False)
        self.assertTrue(build.apply_setting())
        self.assertEqual(env.messages, ['A11y|build|off|2', 'A11y|buildcontrols|off'])
        self.assertFalse(build._active)
        self.assertEqual(build._aim_pending, 0)
        self.assertIsNone(build._zone_id)
        self.assertFalse(grid._active)
        self.assertTrue(build.state('2|0|off|220|180|16'))   # the release reply is silent
        env.speech.speak.assert_not_called()

    def test_switching_off_with_nothing_started_only_tells_the_client(self):
        self.assertTrue(build.apply_setting())
        self.assertEqual(env.messages, ['A11y|buildcontrols|off'])
        env.speech.speak.assert_not_called()

    def test_switching_on_tells_the_client(self):
        switch(True)
        self.assertTrue(build.apply_setting())
        self.assertEqual(env.messages, ['A11y|buildcontrols|on'])

    def test_late_activation_is_never_announced_and_is_released_once(self):
        switch(True)
        self.assertTrue(build.request('on'))
        env.messages.clear()
        switch(False)                                      # hand edit, no reload yet
        self.assertTrue(build.state('1|1|on|220|180|16'))
        self.assertFalse(build.active())
        env.speech.speak.assert_not_called()               # no "Build cursor on"
        self.assertEqual(env.messages, ['A11y|build|off|2'])
        self.assertTrue(build.state('2|0|off|220|180|16'))
        env.speech.speak.assert_not_called()               # and its release is silent
        self.assertFalse(build.state('1|1|on|220|180|16'))  # a duplicate cannot revive it

    def test_leaving_build_mode_still_releases_while_off(self):
        self.turn_on_cursor()
        switch(False)
        self.zone = None
        self.assertTrue(build.on_build_buy_exit())
        self.assertEqual(env.messages, ['A11y|build|off|2'])

    def test_activations_carry_the_switch_first(self):
        switch(True)
        self.assertTrue(build.request('on'))
        self.assertTrue(build.request_menu('left'))
        self.assertEqual(env.messages, ['A11y|buildcontrols|on', 'A11y|build|on|1',
                                        'A11y|buildcontrols|on', 'A11y|build|menu:left|2'])
        env.messages.clear()
        self.assertTrue(build.state('2|1|move|220|180|16'))
        self.assertTrue(build.request('left'))              # an ordinary move needs no repeat
        self.assertEqual(env.messages, ['A11y|build|left|3'])


class KeyTests(Base):
    def setUp(self):
        super().setUp()
        keys._modal_active = keys._editing_active = False
        keys._input_epoch = 0

    def test_build_chords_explain_themselves_in_build_mode_only(self):
        for intent in ('undo', 'redo', 'rotateleft', 'rotateright', 'buildtoggle', 'buildgrid'):
            env.speech.speak.reset_mock()
            keys._world_chord(intent, 0)
            self.assertEqual(self.spoken(), [OFF_NOTICE], intent)
        self.zone = None                                    # Live mode: transactions stay silent
        env.speech.speak.reset_mock()
        for intent in ('undo', 'redo', 'rotateleft', 'rotateright'):
            keys._world_chord(intent, 0)
        env.speech.speak.assert_not_called()
        self.assertEqual(env.messages, [])

    def test_heartbeat_announces_both_switches_on_the_pump(self):
        settings._stored['travel_list'] = True
        keys._announce_ui_settings()
        self.assertEqual(env.messages, ['A11y|buildcontrols|off', 'A11y|travellist|on',
                                        'A11y|simplifiedmenus|on', 'A11y|scannermode|off'])

    def test_keyboard_loop_posts_the_heartbeat_with_the_lease(self):
        keys._enabled = True
        keys._modal_active = True
        keys._hook_handle = None
        keys._opening_keys.clear()
        keyboard_env.KeyboardTests.run_samples(self, [{}, {}])
        self.assertIn('A11y|lease', env.messages)
        self.assertIn('A11y|buildcontrols|off', env.messages)
        self.assertIn('A11y|travellist|on', env.messages)
        self.assertEqual(env.queue, [])                     # nothing ran off the pump

    def test_shortcut_help_marks_build_chords_while_off(self):
        marked = ' ({})'.format(lang.t('off in settings'))
        for intent in shortcuts.BUILD_INTENTS:
            self.assertTrue(shortcuts.chord_label(intent).endswith(marked), intent)
        self.assertFalse(shortcuts.chord_label('mood').endswith(marked))
        switch(True)
        for intent in shortcuts.BUILD_INTENTS:
            self.assertFalse(shortcuts.chord_label(intent).endswith(marked), intent)
        self.assertEqual(shortcuts.BUILD_INTENTS,
                         {intent for intent, _ in keys.CHORDS.values()} & shortcuts.BUILD_INTENTS)


if __name__ == '__main__':
    unittest.main()
