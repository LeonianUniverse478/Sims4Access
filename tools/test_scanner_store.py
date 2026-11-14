"""Exercise the confirmation and both destinations without touching a game save."""
import unittest
from types import SimpleNamespace as Stub
from unittest.mock import Mock, patch
import sys
import test_scanner_v5
import tyjokr_a11y_store as store


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.obj = Stub(id=11, is_part=False, self_or_part_in_use=False, inventoryitem_component=Stub(),
                        has_tag=lambda tag: tag == 'urn', stack_count=lambda: 1,
                        definition=Stub(id=8), get_household_owner_id=lambda: 9)
        class Inventory(list):
            def player_try_add_object(self, obj):
                self.append(obj)
                return True
            def can_add(self, obj):
                return True
        self.sim = Stub(id=5, sim_info=Stub(first_name='One', last_name=''), inventory_component=Inventory())
        self.family = Stub(id=9, home_zone_id=10)
        self.build = Mock()
        self.build.get_object_placement_flags.return_value = set()
        self.build.PlacementFlags.NON_INVENTORYABLE = 'blocked'
        self.scanner = Mock(_tree_level='items', _menu_open=False)
        self.scanner._current.return_value = Stub(obj_id=11, is_sim=False)
        self.scanner._name_part.return_value = 'Vase'
        services = Stub(active_household=lambda: self.family, get_active_sim=lambda: self.sim,
                        current_zone_id=lambda: 10, object_manager=lambda: Stub(get=lambda oid: self.obj))
        for fixture in (patch.dict(sys.modules, {'services': services, 'build_buy': self.build,
                'tyjokr_a11y_scanner': self.scanner,
                'sims.ghost': Stub(Ghost=Stub(URNSTONE_TAG='urn')),
                'tyjokr_a11y_place': Stub(sell_refusal=lambda obj: None)}),
                patch.object(store, 'keys', Stub(_input_epoch=2, _scanner_live=True, _scanner_routing=lambda: True,
                    _in_live=lambda: True, blocking_active=lambda: False))):
            fixture.start()
            self.addCleanup(fixture.stop)
        store.cancel()

    def press(self, destination):
        store._transfer(destination, 2, store._generation)

    def test_inactive_pump_cancels_confirmation_and_explains_failure(self):
        self.press('sim')
        with patch.object(sys.modules['tyjokr_a11y_pump'], 'post', return_value=False), \
                patch.object(store.speech, 'speak') as say, patch.object(store.speech, 'log_line'):
            store.enqueue('sim')
            say.assert_called_once_with(store.lang.t('store unavailable'))
        self.press('sim')
        self.assertEqual(self.sim.inventory_component, [])

    def test_storage_shortcuts_only_belong_to_the_live_scanner(self):
        keyboard = test_scanner_v5.keys
        with patch.multiple(keyboard, _enabled=True, _scanner_live=True, _scanner_owner=True,
                            _editing_active=False, _modal_active=False, _blocking_explicit=False), \
                patch.object(keyboard, '_scanner_effective', return_value=True):
            self.assertEqual(keyboard._plain_message(8, ctrl=True), 'A11yStoreSim')
            self.assertEqual(keyboard._plain_message(8, shift=True), 'A11yStoreHousehold')
            self.assertEqual(keyboard._plain_message(8), 'A11yScanner:back')
            self.assertIsNone(keyboard._plain_message(8, ctrl=True, alt=True))
            for state in ('_editing_active', '_modal_active', '_blocking_explicit'):
                with patch.object(keyboard, state, True):
                    self.assertNotIn(keyboard._plain_message(8, shift=True), ('A11yStoreSim', 'A11yStoreHousehold'))
                    self.assertIsNone(keyboard._plain_message(8, ctrl=True))

    def test_household_verifies_native_result(self):
        self.press('household')
        self.build.move_object_to_household_inventory.assert_not_called()
        self.press('household')
        self.build.move_object_to_household_inventory.assert_called_once_with(self.obj, failure_flags=0)
        self.build.object_exists_in_household_inventory.assert_called_once_with(11, 9)

    def test_urn_on_another_lot_and_changed_destination(self):
        self.family.home_zone_id = 97
        self.press('sim')
        self.press('household')
        self.press('sim')
        self.assertEqual(self.sim.inventory_component, [])
        self.press('sim')
        self.assertEqual(self.sim.inventory_component, [self.obj])
        self.build.move_object_to_household_inventory.assert_not_called()

    def test_stale_request_and_newly_occupied_object(self):
        self.press('household')
        old = store._generation
        store.cancel()
        store._transfer('household', 2, old)
        self.press('household')
        self.obj.self_or_part_in_use = True
        self.press('household')
        self.build.move_object_to_household_inventory.assert_not_called()


if __name__ == '__main__':
    unittest.main()
