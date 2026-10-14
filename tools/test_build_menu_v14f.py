"""Build actions window: rows, closure-before-dispatch, explicit menu requests.

Opening the window is a modal, so the client retires the native cursor; a
'menu:' row asks it to resume at the remembered position for that one action
(client contract: A11y|build|menu:<action>|<serial>). On, off, undo, redo and
the grid aim stay ordinary requests. Run with py -3.7 tools/test_build_menu_v14f.py.
"""
import types
import unittest
from unittest.mock import Mock, patch
import test_scanner_v5 as env
import tyjokr_a11y_hub as hub
import tyjokr_a11y_build as build

lang = env.lang
MENU = [a[5:] for _, a in hub.BUILD_ACTIONS if a.startswith('menu:')]
PLAIN = [a for _, a in hub.BUILD_ACTIONS if not a.startswith('menu:')]


class BuildMenuTests(unittest.TestCase):
    def setUp(self):
        env.settings._stored['build_controls'] = True
        self.addCleanup(env.settings._stored.pop, 'build_controls', None)
        hub._dialog_id = None
        env.queue.clear()
        env.messages.clear()
        build._active = False
        build._pending.clear()
        build._serial = build._last_serial = 0
        build._zone_id = None
        build._aim_pending = 0
        self.zone = types.SimpleNamespace(id=7, is_in_build_buy=True)
        self.services = types.SimpleNamespace(current_zone=lambda: self.zone,
                                              get_active_sim=lambda: None,
                                              client_manager=lambda: types.SimpleNamespace(get_first_client=lambda: None))
        self.dialog = Mock(dialog_id=15, accepted=True)
        picker_module = types.SimpleNamespace(BasePickerRow=lambda **kw: kw, ObjectPickerRow=lambda **kw: types.SimpleNamespace(**kw))
        localization = types.ModuleType('sims4.localization')
        localization.LocalizationHelperTuning = types.SimpleNamespace(get_raw_text=lambda text: text)
        env.sims4.localization = localization
        self.patches = [patch.dict(env.sys.modules, {'services': self.services, 'ui.ui_dialog_picker': picker_module,
                                                     'sims4.localization': localization}),
                        patch.object(env.speech, 'speak'),
                        patch.object(hub.menu, '_picker', return_value=self.dialog),
                        patch.object(hub.menu, '_cancel_dialog')]
        for item in self.patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in reversed(self.patches)])

    def rows(self):
        return [call[0][0] for call in self.dialog.add_row.call_args_list]

    def choose(self, action):
        index = [a for _, a in hub.BUILD_ACTIONS].index(action)
        reply = types.SimpleNamespace(dialog_id=15, accepted=True, get_result_tags=lambda: [index])
        self.dialog.add_listener.call_args[0][0](reply)

    def test_window_lists_every_cursor_action_in_order(self):
        self.assertTrue(hub.build_actions())
        self.assertEqual([r.name for r in self.rows()], [lang.t(label) for label, _ in hub.BUILD_ACTIONS])
        self.assertEqual([a for _, a in hub.BUILD_ACTIONS],
                         ['on', 'off', 'menu:left', 'menu:right', 'menu:up', 'menu:down',
                          'menu:fine', 'menu:coarse', 'menu:center', 'grid',
                          'menu:click', 'menu:cancel', 'menu:rotateleft', 'menu:rotateright',
                          'undo', 'redo', 'menu:status'])
        self.assertEqual(set(MENU), set(build.MENU_ACTIONS))     # every resumable action has a row
        self.assertTrue(set(PLAIN) <= build.ACTIONS)

    def test_menu_row_sends_the_explicit_menu_request_after_the_window_closes(self):
        hub.build_actions()
        self.choose('menu:click')
        self.assertEqual(env.messages, [])          # deferred until EA finished the dialog
        env.drain()
        self.assertEqual(env.messages, ['A11y|buildcontrols|on', 'A11y|build|menu:click|1'])   # cursor was retired by the modal; no active() gate
        self.assertFalse(build.active())
        self.assertTrue(build.state('1|1|click|220|180|16'))       # the client resumed and performed it
        self.assertTrue(build.active())

    def test_on_off_undo_redo_rows_are_ordinary_requests(self):
        for action, expected in (('on', 'A11y|build|on|1'), ('off', 'A11y|build|off|2'),
                                 ('undo', 'A11y|build|undo|3'), ('redo', 'A11y|build|redo|4')):
            hub.build_actions()
            self.choose(action)
            env.drain()
            self.assertEqual(env.messages[-1], expected)

    def test_grid_row_uses_the_aim_request(self):
        hub.build_actions()
        with patch.object(build, 'aim_grid', Mock(return_value=True)) as aim:
            self.choose('grid')
            env.drain()
        aim.assert_called_once_with()
        self.assertEqual(env.messages, [])

    def test_outside_build_mode_the_window_does_not_open(self):
        self.zone.is_in_build_buy = False
        self.assertFalse(hub.build_actions())
        self.dialog.add_row.assert_not_called()
        self.assertEqual(env.speech.speak.call_args[0][0], 'Enter Build mode first.')

    def test_cancelled_window_runs_nothing(self):
        hub.build_actions()
        reply = types.SimpleNamespace(dialog_id=15, accepted=False, get_result_tags=lambda: [0])
        self.dialog.add_listener.call_args[0][0](reply)
        env.drain()
        self.assertEqual(env.messages, [])

    def test_hub_offers_the_window_and_terms_exist(self):
        # 2026-09-26: the Build actions window left the accessibility menu
        # (object placement replaced the pixel cursor there); it stays on
        # a11y.buildmenu for testing.
        hub.open_hub()
        self.assertNotIn(lang.t('build actions'), [r.name for r in self.rows()])
        for label, _ in hub.BUILD_ACTIONS:
            self.assertNotEqual(lang.t(label), label, label)
        self.assertNotEqual(lang.t('build actions instructions'), 'build actions instructions')


class RequestMenuTests(unittest.TestCase):
    def setUp(self):
        env.settings._stored['build_controls'] = True
        self.addCleanup(env.settings._stored.pop, 'build_controls', None)
        env.messages.clear()
        build._active = False
        build._pending.clear()
        build._serial = build._last_serial = 0
        build._zone_id = None
        build._aim_pending = 0
        build._last_feedback = 'old hover text'
        self.zone = types.SimpleNamespace(id=12, is_in_build_buy=True)
        self.patches = [patch.object(build, '_zone', side_effect=lambda: self.zone),
                        patch.object(build.speech, 'speak')]
        for item in self.patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in reversed(self.patches)])

    def test_only_the_allowlist_and_only_in_build_mode(self):
        for action in ('on', 'off', 'toggle', 'undo', 'redo', 'grid', 'bulldoze', '', 'menu:left'):
            self.assertFalse(build.request_menu(action), action)
        self.assertEqual(env.messages, [])
        self.zone = None
        self.assertFalse(build.request_menu('left'))
        self.assertEqual(env.messages, [])
        self.assertEqual(build.speech.speak.call_args[0][0], 'Enter Build mode first.')

    def test_menu_request_bypasses_the_active_gate_but_keeps_serial_and_zone_tracking(self):
        self.assertFalse(build.request('left'))              # ordinary path still needs the acknowledgement
        self.assertTrue(build.request_menu('left'))
        self.assertEqual(env.messages, ['A11y|buildcontrols|on', 'A11y|build|menu:left|1'])
        self.assertEqual(build._pending, {1: 12})
        self.assertEqual(build._last_feedback, '')           # a move clears stale hover text like the chord does
        self.assertFalse(build.state('1|1|move|20|90|16') is False)
        self.assertTrue(build.active())
        self.assertIn('Screen x 20, y 90', build.speech.speak.call_args[0][0])

    def test_a_blocked_or_unavailable_reply_leaves_the_cursor_off(self):
        build.request_menu('status')
        self.assertTrue(build.state('1|0|blocked|20|90|16'))
        self.assertFalse(build.active())
        self.assertEqual(build.speech.speak.call_args[0][0], 'Close the open dialog or text field first.')
        build.request_menu('click')
        self.assertTrue(build.state('2|0|unavailable|20|90|16'))
        self.assertFalse(build.active())

    def test_menu_reply_for_another_zone_is_refused(self):
        build.request_menu('right')
        self.zone = types.SimpleNamespace(id=13, is_in_build_buy=True)
        self.assertFalse(build.state('1|1|move|20|90|16'))
        self.assertFalse(build.active())


class BuildExitReleaseTests(unittest.TestCase):
    """Leaving Build mode forces the native cursor off through whichever UI
    instance is live, silently, and only when this Build session used it."""

    def setUp(self):
        env.settings._stored['build_controls'] = True
        self.addCleanup(env.settings._stored.pop, 'build_controls', None)
        env.messages.clear()
        build._active = False
        build._pending.clear()
        build._serial = build._last_serial = 0
        build._zone_id = None
        build._aim_pending = 0
        build._release_serial = 0
        self.zone = types.SimpleNamespace(id=12, is_in_build_buy=True)
        self.patches = [patch.object(build, '_zone', side_effect=lambda: self.zone),
                        patch.object(build.speech, 'speak'),
                        patch.object(build.speech, 'log_line')]
        for item in self.patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in reversed(self.patches)])

    def test_exit_after_use_sends_off_and_its_reply_is_silent(self):
        build.request('on')
        build.state('1|1|on|20|90|16')
        self.assertTrue(build.active())
        self.zone = None                                       # Build UI torn down, Live mode now
        self.assertTrue(build.on_build_buy_exit())
        self.assertEqual(env.messages[-1], 'A11y|build|off|2')
        self.assertFalse(build.active())
        self.assertIsNone(build._zone_id)
        build.speech.speak.reset_mock()
        self.assertTrue(build.state('2|0|off|20|90|16'))       # the Live instance answers
        build.speech.speak.assert_not_called()
        self.assertFalse(build.state('1|1|on|20|90|16'))       # nothing older can revive it

    def test_exit_without_any_request_sends_nothing(self):
        self.zone = None
        self.assertFalse(build.on_build_buy_exit())
        self.assertEqual(env.messages, [])

    def test_exit_after_an_explicit_off_still_releases_once_then_stays_quiet(self):
        build.request('on')
        build.state('1|1|on|20|90|16')
        build.request('off')
        build.state('2|0|off|20|90|16')
        self.zone = None
        self.assertTrue(build.on_build_buy_exit())              # the client's off is idempotent
        self.assertEqual(env.messages[-1], 'A11y|build|off|3')
        self.assertFalse(build.on_build_buy_exit())             # nothing left to release
        self.assertEqual(len(env.messages), 4)                  # switch, on, off, exit release

    def test_ordinary_off_reply_is_still_spoken(self):
        build.request('on')
        build.state('1|1|on|20|90|16')
        build.request('off')
        build.state('2|0|off|20|90|16')
        self.assertEqual(build.speech.speak.call_args[0][0], 'Build cursor off.')

    def test_install_registers_the_exit_callback_once(self):
        build._installed = False
        registered = []
        stub = types.SimpleNamespace(register_build_buy_exit_callback=registered.append,
                                     register_build_buy_enter_callback=registered.append)
        with patch.dict(env.sys.modules, {'build_buy': stub}):
            self.assertTrue(build.install())
            self.assertTrue(build.install())
        self.assertEqual(registered, [build.on_build_buy_exit, build.on_build_buy_enter])


class BuildLogTests(unittest.TestCase):
    def setUp(self):
        build._log_window, build._log_count = 0.0, 0
        self.patches = [patch.object(build.speech, 'speak'), patch.object(build.speech, 'log_line')]
        for item in self.patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in reversed(self.patches)])

    def test_lines_are_logged_decoded_and_never_spoken(self):
        self.assertTrue(build.buildlog('product%20selected%20class%3DCatalogProduct%20key%3D1'))
        build.speech.log_line.assert_called_once_with('build client: product selected class=CatalogProduct key=1')
        build.speech.speak.assert_not_called()

    def test_empty_or_oversized_lines_are_refused(self):
        self.assertFalse(build.buildlog(''))
        self.assertFalse(build.buildlog('   '))
        self.assertFalse(build.buildlog('x' * 401))
        build.speech.log_line.assert_not_called()

    def test_burst_is_capped_with_one_notice(self):
        for i in range(build._LOG_BURST):
            self.assertTrue(build.buildlog('line {}'.format(i)))
        self.assertFalse(build.buildlog('too many'))
        self.assertFalse(build.buildlog('still too many'))
        self.assertEqual(build.speech.log_line.call_count, build._LOG_BURST + 1)
        self.assertEqual(build.speech.log_line.call_args[0][0], 'build client: further lines dropped for this window')


if __name__ == '__main__':
    unittest.main(verbosity=1)
