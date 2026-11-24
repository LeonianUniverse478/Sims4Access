"""V reuses the native event reader, with explicit selection and lot checks."""
import ast
import pathlib
import sys
import types
import unittest
from unittest.mock import Mock, patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Scripts'))
import tyjokr_a11y_event_goals as goals


class ShortcutTests(unittest.TestCase):
    def setUp(self):
        self.zone = 9007199254740993
        self.event = types.SimpleNamespace(id=18446744073709551000,
                                           display_name='Native event')
        self.hub = types.SimpleNamespace(
            _events=Mock(return_value=[self.event]), _say=Mock(),
            _window=Mock(return_value=True), _event_detail=lambda event: 'Details',
            menu=types.SimpleNamespace(_raw=lambda text: text),
            _event=Mock(return_value=(None, None)), _ui=Mock())
        self.keys = types.SimpleNamespace(_enabled=True, _editing_active=False,
                                          blocking_active=Mock(return_value=False))
        self.speech = types.SimpleNamespace(speak=Mock(), log_line=Mock())
        modules = {
            'services': types.SimpleNamespace(current_zone_id=lambda: self.zone),
            'tyjokr_a11y_hub': self.hub,
            'tyjokr_a11y_keys': self.keys,
            'tyjokr_a11y_speech': self.speech,
            'tyjokr_a11y_lang': types.SimpleNamespace(t=lambda text: text),
            'tyjokr_a11y_pump': types.SimpleNamespace(post=Mock()),
        }
        replacements = patch.dict(sys.modules, modules)
        replacements.start()
        self.addCleanup(replacements.stop)

    def test_single_event_uses_existing_reader_with_exact_id(self):
        with patch.object(goals, 'open_goals', return_value=True) as opened:
            self.assertTrue(goals.open_current(str(self.zone)))
        opened.assert_called_once_with(self.event.id)
        self.hub._window.assert_not_called()

    def test_multiple_events_do_not_guess_and_rows_keep_their_own_ids(self):
        other = types.SimpleNamespace(id=18446744073709551001, display_name='Other')
        self.hub._events.return_value = [self.event, other]
        with patch.object(goals, 'open_goals', return_value=True) as opened:
            self.assertTrue(goals.open_current(str(self.zone)))
            opened.assert_not_called()
            title, instructions, rows = self.hub._window.call_args[0]
            self.assertEqual(title, 'current event goals')
            self.assertEqual(instructions, 'event goals selection instructions')
            self.assertEqual([row[:2] for row in rows],
                             [('Native event', 'Details'), ('Other', 'Details')])
            rows[1][2]()
            opened.assert_called_once_with(other.id)
            rows[0][2]()
            self.assertEqual(opened.call_args[0], (self.event.id,))

    def test_no_named_events_has_spoken_feedback_and_no_picker(self):
        for events in ([], [types.SimpleNamespace(id=1, display_name=None)]):
            self.hub._events.return_value = events
            self.assertFalse(goals.open_current(str(self.zone)))
        self.assertEqual(self.hub._say.call_count, 2)
        self.hub._say.assert_called_with('no events')
        self.hub._window.assert_not_called()

    def test_travel_before_command_drops_the_request(self):
        self.assertFalse(goals.open_current(str(self.zone - 1)))
        self.hub._events.assert_not_called()
        self.speech.speak.assert_not_called()

    def test_travel_after_picker_does_not_open_an_event_on_another_lot(self):
        self.hub._events.return_value = [self.event, self.event]
        goals.open_current(str(self.zone))
        callback = self.hub._window.call_args[0][2][0][2]
        self.zone += 1
        with patch.object(goals, 'open_goals') as opened:
            self.assertFalse(callback())
        opened.assert_not_called()

    def test_editing_or_blocking_owner_opened_after_key_guard(self):
        self.keys._editing_active = True
        self.assertFalse(goals.open_current(str(self.zone)))
        self.keys._editing_active = False
        self.keys.blocking_active.return_value = True
        self.assertFalse(goals.open_current(str(self.zone)))
        self.hub._events.assert_not_called()

    def test_keyboard_navigation_disabled_after_key_guard_drops_request(self):
        self.keys._enabled = False
        self.assertFalse(goals.open_current(str(self.zone)))
        self.hub._events.assert_not_called()

    def test_hud_owner_is_not_treated_as_a_blocking_dialog(self):
        self.keys._modal_active = True
        with patch.object(goals, 'open_goals', return_value=True) as opened:
            self.assertTrue(goals.open_current(str(self.zone)))
        opened.assert_called_once_with(self.event.id)

    def test_ended_event_is_revalidated_by_existing_reader(self):
        self.assertFalse(goals.open_current(str(self.zone)))
        self.hub._event.assert_called_once_with(self.event.id)
        self.hub._ui.assert_not_called()

    def test_query_exception_reports_existing_unavailable_message(self):
        self.hub._events.side_effect = RuntimeError('No manager')
        self.assertFalse(goals.open_current(str(self.zone)))
        self.speech.speak.assert_called_once_with('event goals unavailable', explicit=True)
        self.hub._window.assert_not_called()

    def test_command_preserves_large_zone_as_a_prefixed_string(self):
        tree = ast.parse((ROOT / 'Scripts/tyjokr_a11y_hub.py').read_text(encoding='utf-8'))
        command = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                       and node.name == 'a11y_eventgoals_shortcut')
        command.decorator_list = []
        namespace = {}
        exec(compile(ast.Module(body=[command]), 'event_goals_shortcut', 'exec'), namespace)
        with patch.object(goals, 'open_current', return_value=True) as opened:
            self.assertTrue(namespace[command.name]('zone:' + str(self.zone)))
            opened.assert_called_once_with(str(self.zone))
            self.assertFalse(namespace[command.name](str(self.zone)))
            self.assertEqual(opened.call_count, 1)


if __name__ == '__main__':
    unittest.main()
