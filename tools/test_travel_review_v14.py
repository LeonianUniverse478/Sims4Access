"""Independent lifecycle regressions for the travel prototype; no live claims."""
import unittest
import types
from unittest.mock import patch
import test_travel_v14 as fixture


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.base = fixture.TravelListTests()
        self.base.setUp()

    def tearDown(self):
        self.base.tearDown()

    def test_queued_commit_cannot_answer_replacement_request(self):
        first = fixture.request()
        fixture.shown[-1].answer(1)
        fixture.env.drain()
        fixture.shown[-1].answer(2)
        second = fixture.request()
        fixture.env.drain()
        self.assertNotIn((second.dialog_id, fixture.ButtonType.DIALOG_RESPONSE_OK),
                         fixture.service.responses)
        self.assertIs(fixture.travel._pending.dialog, second)
        self.assertNotIn(first.dialog_id, fixture.service._active_dialogs)

    def test_failed_pick_does_not_leave_invisible_original(self):
        dialog = fixture.request()
        fixture.shown[-1].answer(1)
        fixture.env.drain()
        dialog.picker_rows = dialog.picker_rows[1:]
        fixture.shown[-1].answer(2)
        fixture.env.drain()
        self.assertNotIn(dialog.dialog_id, fixture.service._active_dialogs)
        self.assertNotIn((dialog.dialog_id, fixture.ButtonType.DIALOG_RESPONSE_OK),
                         fixture.service.responses)

    def test_repeated_building_grouping_does_not_accumulate_units(self):
        rows = [fixture.Row(3, 'Taka Soi 15', 20),
                fixture.Row(31, 'Unit 1', 20), fixture.Row(32, 'Unit 2', 20)]
        dialog = fixture.request(picker_rows=rows)
        places = fixture.travel._collect(dialog)
        first = fixture.travel._buildings(places)
        second = fixture.travel._buildings(places)
        self.assertEqual(len(first[0].units), 3)
        self.assertEqual(len(second[0].units), 3)

    def test_offered_master_unit_remains_reachable_in_unit_picker(self):
        rows = [fixture.Row(3, '09 Taka Soi 15', 20),
                fixture.Row(31, '08 Taka Soi 15', 20)]
        dialog = fixture.request(picker_rows=rows)
        pending = fixture.travel._pending
        units = fixture.travel._units_of(pending, 3)
        self.assertEqual({p.zone_id for p in units}, {3, 31},
                         'A native offered destination must not disappear when grouped')

    def test_rejected_pump_does_not_open_next_window_inline(self):
        dialog = fixture.request()
        with patch.object(fixture.travel.pump, 'post', return_value=False):
            fixture.shown[-1].answer(1)
        self.assertEqual(len(fixture.shown), 1)
        self.assertNotIn(dialog.dialog_id, fixture.service._active_dialogs)

    def test_next_window_failure_recovers_the_original_request(self):
        dialog = fixture.request()
        fixture.shown[-1].answer(1)
        with patch.object(fixture.travel.menu, '_picker', return_value=None):
            fixture.env.drain()
        native = [call for call in fixture.native_calls if call[0] == dialog.dialog_id]
        self.assertTrue(native or dialog.dialog_id not in fixture.service._active_dialogs,
                        'Original dialog is active with no visible picker or map')

    def test_queued_map_fallback_cannot_replace_a_new_request(self):
        first = fixture.request()
        fixture.shown[-1].answer(2)
        second = fixture.request()
        fixture.env.drain()
        self.assertEqual(fixture.native_calls, [])
        self.assertIs(fixture.travel._pending.dialog, second)
        self.assertNotIn(first.dialog_id, fixture.service._active_dialogs)

    def test_business_guard_uses_native_allowed_zone_property(self):
        place = fixture.travel._Place(77, 'Home business')
        place.household_id = 42
        manager = types.SimpleNamespace(allowed_zone_ids=[77])
        tracker = types.SimpleNamespace(owner_household_id=42,
                                        business_managers={},
                                        zoneless_business_managers={5: manager})
        business = types.SimpleNamespace(business_trackers_gen=lambda: iter([tracker]),
                    get_business_trackers_for_household=lambda owner: [tracker])
        with patch.object(fixture.services, 'active_household_id', lambda: 1, create=True), \
             patch.object(fixture.services, 'business_service', lambda: business, create=True), \
             patch.object(fixture.travel, '_is_residential', lambda zone: True):
            self.assertTrue(fixture.travel._needs_native_map(place))


if __name__ == '__main__':
    unittest.main()
