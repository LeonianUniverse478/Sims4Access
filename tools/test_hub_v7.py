"""Regression checks for stale dialogs and household selection safety."""
import types
import unittest
from unittest.mock import Mock, patch
import test_scanner_v5 as env
import tyjokr_a11y_hub as hub


class HubTests(unittest.TestCase):
    def setUp(self):
        hub._dialog_id = None
        env.queue.clear()
        self.sim = types.SimpleNamespace(sim_id=42, first_name='Łucja', last_name='Kowalska')
        self.client = types.SimpleNamespace(selectable_sims=[self.sim],
                                           active_sim_info=None,
                                           set_active_sim_by_id=Mock(return_value=True))
        self.services = types.SimpleNamespace(
            client_manager=lambda: types.SimpleNamespace(get_first_client=lambda: self.client),
            sim_info_manager=lambda: types.SimpleNamespace(get=lambda ident: self.sim if ident == 42 else None))
        self.patches = [patch.dict(env.sys.modules, {'services': self.services}),
                        patch.object(env.speech, 'speak')]
        for item in self.patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in reversed(self.patches)])

    def test_selectable_membership_is_rechecked_when_activated(self):
        self.assertTrue(hub.select_sim(42))
        self.client.set_active_sim_by_id.assert_called_once_with(42)
        self.client.set_active_sim_by_id.reset_mock()
        self.client.selectable_sims.clear()
        self.assertFalse(hub.select_sim(42))
        self.assertFalse(hub.select_sim(999))
        self.client.set_active_sim_by_id.assert_not_called()

    def test_already_active_does_not_call_switch_that_would_return_false(self):
        self.client.active_sim_info = self.sim
        self.assertTrue(hub.select_sim(42))
        self.client.set_active_sim_by_id.assert_not_called()

    def test_cancel_stale_and_invalid_reply_never_runs_an_action(self):
        action = Mock()
        dialog = Mock(dialog_id=15, accepted=False)
        dialog.get_result_tags.return_value = [0]
        picker_module = types.SimpleNamespace(BasePickerRow=lambda **kw: kw, ObjectPickerRow=lambda **kw: kw)
        with patch.dict(env.sys.modules, {'ui.ui_dialog_picker': picker_module}), \
                patch.object(hub.menu, '_picker', return_value=dialog), \
                patch.object(hub.menu, '_cancel_dialog'):
            for accepted, ident, tags in ((False, 15, [0]), (True, 99, [0]),
                                          (True, 15, [99]), (True, 15, [0, 1])):
                hub._window('test', 'test', [('label', None, action)])
                reply = types.SimpleNamespace(dialog_id=ident, accepted=accepted,
                                               get_result_tags=lambda: tags)
                dialog.add_listener.call_args[0][0](reply)
                env.drain()
            action.assert_not_called()

    def test_valid_action_is_deferred_until_dialog_response_finishes(self):
        action = Mock()
        dialog = Mock(dialog_id=15, accepted=True)
        dialog.get_result_tags.return_value = [0]
        with patch.dict(env.sys.modules, {'ui.ui_dialog_picker': types.SimpleNamespace(BasePickerRow=lambda **kw: kw, ObjectPickerRow=lambda **kw: kw)}), \
                patch.object(hub.menu, '_picker', return_value=dialog), \
                patch.object(hub.menu, '_cancel_dialog'):
            hub._window('test', 'test', [('label', None, action)])
            callback = dialog.add_listener.call_args[0][0]
            callback(dialog)
            callback(dialog)  # duplicate response
            action.assert_not_called()
            env.drain()
            action.assert_called_once_with()

    def test_phone_shortcut_cannot_replace_an_unfinished_dialog(self):
        env.keys._modal_active = True
        with patch.object(hub, 'open_hub') as opened, \
                patch.dict(env.sys.modules, {'tyjokr_a11y_phone': types.SimpleNamespace(open_waiting=opened)}):
            env.keys._chord('phone')
            env.drain()
            opened.assert_not_called()
        env.keys._modal_active = False


if __name__ == '__main__':
    unittest.main(verbosity=2)
