"""Remote portrait routing, visibility and stale selection regressions."""
import types
import unittest
from unittest.mock import Mock, patch
import test_scanner_v5 as env
import tyjokr_a11y_contacts as contacts


class ContactTests(unittest.TestCase):
    def setUp(self):
        self.remote = types.SimpleNamespace(sim_id=82, first_name='Łucja', last_name='Kowalska')
        self.hidden = types.SimpleNamespace(sim_id=83, first_name='Hidden', last_name='Contact')
        self.tracker = types.SimpleNamespace(
            get_target_sim_infos=lambda: [self.hidden, self.remote, self.remote],
            is_hidden=lambda ident: ident == 83)
        self.actor = types.SimpleNamespace(
            sim_info=types.SimpleNamespace(sim_id=42, relationship_tracker=self.tracker),
            position=types.SimpleNamespace(x=10, y=2, z=20), level=1)
        self.services = types.SimpleNamespace(
            get_active_sim=lambda: self.actor,
            active_lot=lambda: types.SimpleNamespace(lot_id=11))
        self.scanner = types.SimpleNamespace(_send_ui=Mock(return_value=True))
        self.patch = patch.dict(env.sys.modules, {
            'services': self.services, 'tyjokr_a11y_scanner': self.scanner,
            'server': types.ModuleType('server'),
            'server.pick_info': types.SimpleNamespace(PickType=types.SimpleNamespace(PICK_PORTRAIT=10))})
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_remote_sim_needs_no_instance_or_world_position(self):
        self.assertTrue(contacts.open_contact(82, 42))
        fields = self.scanner._send_ui.call_args[0][0].split('|')
        self.assertEqual(fields[:5], ['A11y', 'pick', '82', '10', '11'])
        self.assertEqual(fields[5], 'Łucja Kowalska')

    def test_hidden_contacts_and_duplicates_are_excluded(self):
        self.assertEqual(contacts._contacts(self.actor), [('Łucja Kowalska', 82)])

    def test_changed_actor_missing_contact_or_newly_hidden_contact_cannot_activate(self):
        with patch.object(env.speech, 'speak'):
            self.assertFalse(contacts.open_contact(82, 999))
            self.assertFalse(contacts.open_contact(999, 42))
            self.tracker.is_hidden = lambda ident: True
            self.assertFalse(contacts.open_contact(82, 42))
        self.scanner._send_ui.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
