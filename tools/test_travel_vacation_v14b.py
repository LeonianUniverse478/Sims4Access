"""Vacation requests through the travel list: rental before the answer, never after.

Run with py -3.7 tools/test_travel_vacation_v14b.py. Source bodies only.
"""
import types
import unittest
from unittest.mock import patch

import test_travel_v14 as fixture

travel = fixture.travel
env = fixture.env
shown, service, services = fixture.shown, fixture.service, fixture.services
OK, CANCEL = fixture.OK, fixture.CANCEL
lang = fixture.lang
BACK_P = lang.t('back to places')
MAP = lang.t('open the map instead')

VACATION = fixture.UiMapViewPicker.MapViewMode.VACATION
RENTAL = {40: True, 41: True, 42: False}          # 42 = a community lot in the destination world
LOT_VALUE = {40: 200000, 41: 50000, 42: 30000}
ZONE_VALUE = dict(LOT_VALUE)          # the uninstantiated-zone source


def get_zone(zone_id, allow_uninstantiated_zones=False):
    if zone_id in ZONE_VALUE:
        return types.SimpleNamespace(lot=types.SimpleNamespace(furnished_lot_value=ZONE_VALUE[zone_id]))
    return None
fixture.ZONE_REGION.update({40: 'wc', 41: 'wc', 42: 'wc'})
PRICE_MODIFIERS = types.SimpleNamespace(multiply=0.005, add=0.0)   # tuning stub: 200000 -> 1000 a day


class Household(object):
    def __init__(self, grouped=False):
        self.grouped = grouped

    def any_member_in_travel_group(self):
        return self.grouped


class Info(object):
    def __init__(self, sim_id, grouped=False, household_grouped=False):
        self.sim_id = sim_id
        self._grouped = grouped
        self.household = Household(household_grouped)

    def is_in_travel_group(self):
        return self._grouped


class Sim(object):
    def __init__(self, sim_id, grouped=False, household_grouped=False):
        self.sim_info = Info(sim_id, grouped, household_grouped)


class FakeGroup(object):
    _next = 30

    def __init__(self, zone_id, members):
        FakeGroup._next += 1
        self.id = FakeGroup._next
        self.zone_id = zone_id
        self.members = members

    def __contains__(self, info):
        return info in self.members


class FakeTravelGroupManager(object):
    def __init__(self):
        self.calls = []
        self.result = True
        self.groups = []
        self.destroyed = []
        self.refuse_destroy = False

    def create_travel_group_and_rent_zone(self, **kwargs):
        self.calls.append(kwargs)
        if self.result:
            self.groups.append(FakeGroup(kwargs['zone_id'], list(kwargs['sim_infos'])))
        return self.result

    def get_travel_group_by_sim_info(self, info):
        for group in self.groups:
            if info in group.members:
                return group
        return None

    def get_travel_group_by_zone_id(self, zone_id):
        for group in self.groups:
            if group.zone_id == zone_id:
                return group
        return None

    def destroy_travel_group_and_release_zone(self, group, last_sim_info=None, return_objects=False):
        if self.refuse_destroy:
            return False
        self.groups.remove(group)
        self.destroyed.append(group)
        return True


class FakeFunds(object):
    def __init__(self, money):
        self.money = money
        self.added = []

    def add(self, amount, reason, sim=None, tags=None, count_as_earnings=True):
        self.money += amount
        self.added.append((amount, reason, count_as_earnings))


consts = types.ModuleType('protocolbuffers.Consts_pb2')
consts.FUNDS_MONEY_VACATION = 'vacation'
protocolbuffers = types.ModuleType('protocolbuffers')
protocolbuffers.Consts_pb2 = consts


manager = FakeTravelGroupManager()
household = types.SimpleNamespace(funds=FakeFunds(5000))
rentable = types.ModuleType('world.rentable_lot_tuning')
rentable.RentableZoneTuning = types.SimpleNamespace(PRICE_MODIFIERS=PRICE_MODIFIERS)
clock = types.ModuleType('clock')
clock.interval_in_sim_days = lambda days: days * 1440
street = types.ModuleType('world.street')
street.get_vacation_zone_id = lambda zone_id: zone_id


def vacation_rows():
    return [fixture.Row(40, 'Granite Falls Lodge', 10, venue='RENTAL'),
            fixture.Row(41, 'Cabin', 10, venue='RENTAL'),
            fixture.Row(42, 'Ranger Station', 10, venue='PARK')]


def request(rows=None, companions=(), actor=None):
    dialog = fixture.UiMapViewPicker(vacation_rows() if rows is None else rows, mode=VACATION)
    dialog.owner = actor or Sim(700)
    dialog.traveling_sims = list(companions)
    service._active_dialogs[dialog.dialog_id] = dialog
    dialog.distribute_dialog('MSG', {'msg': dialog.dialog_id})
    return dialog


def get_instance_manager(kind):
    if kind == 'venue':
        return types.SimpleNamespace(get=lambda zone_id: types.SimpleNamespace(
            is_residential=fixture.RESIDENTIAL.get(zone_id, False), is_rental=RENTAL.get(zone_id, False)))
    return fixture._instance_manager(kind)


class VacationTests(unittest.TestCase):
    def setUp(self):
        self.base = fixture.TravelListTests()
        self.base.setUp()
        manager.calls = []
        manager.result = True
        manager.groups = []
        manager.destroyed = []
        manager.refuse_destroy = False
        household.funds = FakeFunds(5000)
        ZONE_VALUE.clear()
        ZONE_VALUE.update(LOT_VALUE)
        self.patches = [
            patch.object(services, 'travel_group_manager', lambda: manager, create=True),
            patch.object(services, 'active_household', lambda: household, create=True),
            patch.object(services, 'time_service', lambda: types.SimpleNamespace(sim_now=100), create=True),
            patch.object(services, 'get_instance_manager', get_instance_manager),
            patch.object(fixture.build_buy, 'get_lot_value', lambda zone_id, furnished: (LOT_VALUE.get(zone_id, 0), 0), create=True),
            patch.object(services, 'get_zone', get_zone, create=True),
            patch.dict('sys.modules', {'world.rentable_lot_tuning': rentable, 'clock': clock,
                                       'protocolbuffers': protocolbuffers, 'protocolbuffers.Consts_pb2': consts,
                                       'world.street': street}),
        ]
        for p in self.patches:
            p.start()
        fixture.world_pkg.rentable_lot_tuning = rentable

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.base.tearDown()

    def spoken_last(self):
        return self.base.spoken.call_args[0][0]

    def spoken_all(self):
        return [c[0][0] for c in self.base.spoken.call_args_list]

    def test_vacation_request_lists_rentals_with_daily_price(self):
        request()
        self.assertEqual(fixture.native_calls, [])
        shown[0].answer(0)                      # Willow Creek (the test worlds)
        env.drain()
        names = shown[1].names()
        self.assertEqual(names, [BACK_P.replace('places', 'worlds'), 'Cabin', 'Granite Falls Lodge', MAP])   # the park is not a rental
        self.assertEqual(shown[1].rows[2].row_description, 'RENTAL, 1000 Simoleons per day')

    def test_stay_window_prices_days_and_marks_unaffordable(self):
        request()
        shown[0].answer(0)
        env.drain()
        shown[1].answer(2)                      # Granite Falls Lodge, 1000 a day, funds 5000
        env.drain()
        rows = shown[2]
        self.assertEqual(rows.names()[0], BACK_P)
        self.assertEqual(rows.names()[1], '1 day, 1000 Simoleons')
        self.assertEqual(rows.names()[7], '7 days, 7000 Simoleons')
        self.assertEqual([r.row_description for r in rows.rows][1:], [None] * 5 + [lang.t('cannot afford')] * 2)
        self.assertEqual(manager.calls, [])

    def test_rental_happens_once_before_the_answer_with_actor_and_companions(self):
        companion = Sim(701)
        dialog = request(companions=[companion, companion])   # duplicate companion collapses
        shown[0].answer(0)
        env.drain()
        shown[1].answer(2)
        env.drain()
        shown[2].answer(3)                      # 3 days
        env.drain()
        self.assertEqual(len(manager.calls), 1)
        call = manager.calls[0]
        self.assertEqual([i.sim_id for i in call['sim_infos']], [700, 701])
        self.assertEqual((call['zone_id'], call['played'], call['create_timestamp'], call['end_timestamp'], call['cost']),
                         (40, True, 100, 100 + 3 * 1440, 3000))
        self.assertEqual(service.picks, [(dialog.dialog_id, [40])])
        self.assertEqual(service.responses, [(dialog.dialog_id, OK)])
        self.assertEqual(fixture.pushed, [(dialog.dialog_id, [40])])
        self.assertIsNone(travel._pending)

    def test_non_rental_destinations_are_never_listed_for_a_vacation(self):
        request()
        self.assertEqual({p.zone_id for p in travel._pending.places}, {40, 41})
        shown[0].answer(0)
        env.drain()
        self.assertNotIn('Ranger Station', shown[1].names())
        self.assertEqual(manager.calls, [])

    def test_a_vacation_with_no_rentals_at_all_uses_the_native_map(self):
        dialog = request(rows=[fixture.Row(42, 'Ranger Station', 10, venue='PARK')])
        self.assertEqual(fixture.native_calls, [(dialog.dialog_id, 'MSG', {'msg': dialog.dialog_id})])
        self.assertEqual(shown, [])
        self.assertIsNone(travel._pending)

    def test_client_price_bridge_is_asked_for_unpriced_rentals_and_used_when_it_answers(self):
        ZONE_VALUE.clear()
        with patch.object(fixture.build_buy, 'get_lot_value', lambda zone_id, furnished: (-1, -1), create=True):
            dialog = request()
            gen = travel._pending.generation
            self.assertIn('A11y|lotprice|40|{}'.format(gen), env.messages)
            self.assertIn('A11y|lotprice|41|{}'.format(gen), env.messages)
            self.assertTrue(travel.a11y_lotprice_enc('40|397|{}'.format(gen)))      # the map's own number arrives
            self.assertFalse(travel.a11y_lotprice_enc('41|-2|{}'.format(gen)))      # sentinel refused
            self.assertFalse(travel.a11y_lotprice_enc('41|500|{}'.format(gen - 1)))  # stale generation ignored
            self.assertFalse(travel.a11y_lotprice_enc('41|500'))                    # no generation ignored
            shown[0].answer(0)
            env.drain()
            self.assertEqual(shown[1].rows[2].row_description, 'RENTAL, 397 Simoleons per day')
            self.assertEqual(shown[1].rows[1].row_description, 'RENTAL')     # Cabin still unpriced
            shown[1].answer(2)                                               # Granite Falls Lodge
            env.drain()
            self.assertEqual(shown[2].names()[1], '1 day, 397 Simoleons')
            shown[2].answer(2)
            env.drain()
            self.assertEqual(manager.calls[0]['cost'], 794)
            self.assertEqual(service.responses, [(dialog.dialog_id, OK)])

    def test_prices_never_survive_into_the_next_vacation_request(self):
        ZONE_VALUE.clear()
        with patch.object(fixture.build_buy, 'get_lot_value', lambda zone_id, furnished: (-1, -1), create=True):
            request()
            first = travel._pending
            travel.a11y_lotprice_enc('40|397|{}'.format(first.generation))
            shown[0].close()                                                 # trip cancelled
            request()
            second = travel._pending
            self.assertGreater(second.generation, first.generation)
            self.assertEqual(second.prices, {})
            self.assertFalse(travel.a11y_lotprice_enc('40|397|{}'.format(first.generation)))   # late reply for the old request
            shown[-1].answer(0)
            env.drain()
            self.assertEqual(shown[-1].rows[2].row_description, 'RENTAL')  # unpriced again until the client answers

    def test_a_changed_price_after_the_quote_re_quotes_instead_of_charging(self):
        dialog = request()
        shown[0].answer(0)
        env.drain()
        shown[1].answer(2)                                                   # Lodge at 1000 a day
        env.drain()
        self.assertEqual(shown[2].names()[2], '2 days, 2000 Simoleons')
        # The client's own answer arrives after the quote, through the real
        # reply path: nothing on the place is touched directly.
        self.assertTrue(travel.a11y_lotprice_enc('40|1500|{}'.format(travel._pending.generation)))
        self.assertEqual(travel._find(travel._pending, 40).price, 1000)     # the shown quote is untouched until commit
        shown[2].answer(2)                                                   # quoted 2 days, 2000
        env.drain()
        self.assertEqual(manager.calls, [])
        self.assertEqual(shown[-1].names()[2], '2 days, 3000 Simoleons')      # stay window again with the new price
        self.assertIn(lang.t('price changed'), self.spoken_all())
        shown[-1].answer(2)
        env.drain()
        self.assertEqual(manager.calls[0]['cost'], 3000)
        self.assertEqual(service.responses, [(dialog.dialog_id, OK)])

    def test_a_price_withdrawn_after_the_quote_goes_to_the_native_map_before_any_rental(self):
        ZONE_VALUE.clear()
        with patch.object(fixture.build_buy, 'get_lot_value', lambda zone_id, furnished: (-1, -1), create=True):
            dialog = request()
            gen = travel._pending.generation
            travel.a11y_lotprice_enc('40|397|{}'.format(gen))
            shown[0].answer(0)
            env.drain()
            shown[1].answer(2)                                               # Lodge, 397 a day
            env.drain()
            self.assertEqual(shown[2].names()[1], '1 day, 397 Simoleons')
            self.assertFalse(travel.a11y_lotprice_enc('40|0|{}'.format(gen)))   # the client withdraws it
            shown[2].answer(1)
            env.drain()
        self.assertEqual(manager.calls, [])
        self.assertEqual(fixture.native_calls[-1][0], dialog.dialog_id)
        self.assertIn(lang.t('map required here'), self.spoken_all())
        self.assertNotIn((dialog.dialog_id, OK), service.responses)

    def test_bridge_reply_needs_exactly_three_fields_and_a_price_in_range(self):
        ZONE_VALUE.clear()
        with patch.object(fixture.build_buy, 'get_lot_value', lambda zone_id, furnished: (-1, -1), create=True):
            request()
            gen = travel._pending.generation
            for payload in ('40|397|{}|extra', '40|397', '40', '', '40|0.5|{}', '40|0|{}', '40|-397|{}',
                            '40|3000000000|{}', '40|nan|{}', '40|inf|{}', 'x|397|{}', '40|397|y'):
                self.assertFalse(travel.a11y_lotprice_enc(payload.format(gen)), payload)
                self.assertEqual(travel._pending.prices, {}, payload)
            self.assertTrue(travel.a11y_lotprice_enc('40|397.9|{}'.format(gen)))
            self.assertEqual(travel._pending.prices, {40: 397})              # truncated like the client's uint
            self.assertTrue(travel.a11y_lotprice_enc('40|2147483647|{}'.format(gen)))
            self.assertEqual(travel._pending.prices[40], 2147483647)

    def test_unpriced_rental_pick_goes_to_the_native_map_before_any_rental(self):
        ZONE_VALUE.clear()
        with patch.object(fixture.build_buy, 'get_lot_value', lambda zone_id, furnished: (-1, -1), create=True):
            dialog = request()
            shown[0].answer(0)
            env.drain()
            shown[1].answer(1)                                               # Cabin, no price
            env.drain()
        self.assertEqual(fixture.native_calls[-1][0], dialog.dialog_id)
        self.assertEqual(manager.calls, [])

    def test_back_and_escape_in_the_stay_window_create_nothing(self):
        dialog = request()
        shown[0].answer(0)
        env.drain()
        shown[1].answer(2)
        env.drain()
        shown[2].answer(0)                      # back to places
        env.drain()
        self.assertEqual(shown[3].names()[1], 'Cabin')
        shown[3].answer(2)
        env.drain()
        shown[4].close()                        # Escape at the stay window
        self.assertEqual(manager.calls, [])
        self.assertEqual(service.responses, [(dialog.dialog_id, CANCEL)])
        self.assertEqual(fixture.pushed, [])

    def test_insufficient_funds_at_commit_refuses_without_creating(self):
        dialog = request()
        shown[0].answer(0)
        env.drain()
        shown[1].answer(2)
        env.drain()
        household.funds.money = 1500             # funds dropped after the window opened
        shown[2].answer(2)                      # 2 days, 2000
        env.drain()
        self.assertEqual(manager.calls, [])
        self.assertEqual(service.responses, [(dialog.dialog_id, CANCEL)])
        self.assertEqual(self.spoken_all()[-2:], [lang.t('cannot afford'), lang.t('travel cancelled')])

    def test_party_member_already_in_a_travel_group_refuses_before_creating(self):
        dialog = request(companions=[Sim(701, grouped=True)])
        shown[0].answer(0)
        env.drain()
        shown[1].answer(2)
        env.drain()
        shown[2].answer(1)
        env.drain()
        self.assertEqual(manager.calls, [])
        self.assertEqual(service.responses, [(dialog.dialog_id, CANCEL)])
        self.assertEqual(self.spoken_all()[-2:], [lang.t('action unavailable'), lang.t('travel cancelled')])

    def test_manager_refusal_cancels_natively_and_never_answers_ok(self):
        manager.result = False
        dialog = request()
        shown[0].answer(0)
        env.drain()
        shown[1].answer(2)
        env.drain()
        shown[2].answer(1)
        env.drain()
        self.assertEqual(len(manager.calls), 1)
        self.assertEqual(service.picks, [(dialog.dialog_id, [40])])   # validated before renting
        self.assertEqual(dialog.picked_results, [])                   # cleared before the cancel
        self.assertEqual(fixture.pushed, [])
        self.assertEqual(service.responses, [(dialog.dialog_id, CANCEL)])
        self.assertEqual(fixture.native_calls, [])

    def test_refused_ok_after_a_rental_rolls_back_and_never_falls_back_to_the_map(self):
        service.refuse_ok = True
        dialog = request(companions=[Sim(701)])
        pending = travel._pending
        shown[0].answer(0)
        env.drain()
        shown[1].answer(2)
        env.drain()
        shown[2].answer(2)                      # 2 days, 2000
        env.drain()
        self.assertEqual(len(manager.calls), 1)
        self.assertEqual(manager.groups, [])                       # group destroyed
        self.assertEqual(len(manager.destroyed), 1)
        self.assertEqual(household.funds.added, [(2000, 'vacation', False)])   # money returned
        self.assertEqual(service.responses, [(dialog.dialog_id, CANCEL)])
        self.assertEqual(dialog.picked_results, [])
        self.assertEqual(fixture.pushed, [])
        self.assertFalse(travel._fallback(pending))
        self.assertEqual(fixture.native_calls, [])

    def test_exception_while_answering_after_a_rental_rolls_back(self):
        dialog = request()
        shown[0].answer(0)
        env.drain()
        shown[1].answer(2)
        env.drain()
        with patch.object(service, 'dialog_respond', side_effect=RuntimeError('boom')):
            shown[2].answer(1)
            env.drain()
        self.assertEqual(len(manager.calls), 1)
        self.assertEqual(manager.groups, [])
        self.assertEqual(household.funds.added, [(1000, 'vacation', False)])
        self.assertIsNone(travel._pending)

    def test_unverifiable_group_is_reported_not_refunded(self):
        service.refuse_ok = True
        dialog = request()
        shown[0].answer(0)
        env.drain()
        shown[1].answer(2)
        env.drain()
        with patch.object(manager, 'get_travel_group_by_sim_info', lambda info: None), \
             patch.object(env.speech, 'log_line') as log:
            shown[2].answer(1)
            env.drain()
        self.assertEqual(len(manager.groups), 1)           # untouched: nothing verified
        self.assertEqual(household.funds.added, [])
        self.assertTrue(any('could not be identified for rollback' in c[0][0] for c in log.call_args_list))
        self.assertEqual(service.responses, [(dialog.dialog_id, CANCEL)])

    def test_refused_destroy_is_reported_not_refunded(self):
        service.refuse_ok = True
        manager.refuse_destroy = True
        request()
        shown[0].answer(0)
        env.drain()
        shown[1].answer(2)
        env.drain()
        with patch.object(env.speech, 'log_line') as log:
            shown[2].answer(1)
            env.drain()
        self.assertEqual(household.funds.added, [])
        self.assertTrue(any('could not be released' in c[0][0] for c in log.call_args_list))

    def test_household_member_elsewhere_on_vacation_refuses_before_creating(self):
        dialog = request(companions=[Sim(701, household_grouped=True)])   # the Sim is free, a relative is away
        shown[0].answer(0)
        env.drain()
        shown[1].answer(2)
        env.drain()
        shown[2].answer(1)
        env.drain()
        self.assertEqual(manager.calls, [])
        self.assertEqual(service.picks, [])
        self.assertEqual(service.responses, [(dialog.dialog_id, CANCEL)])

    def test_pick_is_validated_before_any_rental(self):
        dialog = request()
        shown[0].answer(0)
        env.drain()
        shown[1].answer(2)
        env.drain()
        dialog.picker_rows = dialog.picker_rows[1:]   # the lodge withdrawn after listing
        shown[2].answer(1)
        env.drain()
        self.assertEqual(manager.calls, [])
        self.assertEqual(service.responses, [(dialog.dialog_id, CANCEL)])
        self.assertEqual(household.funds.money, 5000)

    def test_successful_answer_keeps_the_rental(self):
        dialog = request()
        shown[0].answer(0)
        env.drain()
        shown[1].answer(2)
        env.drain()
        shown[2].answer(1)
        env.drain()
        self.assertEqual(len(manager.groups), 1)
        self.assertEqual(manager.destroyed, [])
        self.assertEqual(household.funds.added, [])
        self.assertEqual(service.responses, [(dialog.dialog_id, OK)])

    def test_duplicate_stay_reply_creates_exactly_one_group(self):
        request()
        shown[0].answer(0)
        env.drain()
        shown[1].answer(2)
        env.drain()
        window = shown[2]
        window.answer(1)
        window.answer(1)
        env.drain()
        self.assertEqual(len(manager.calls), 1)
        self.assertEqual(len(service.responses), 1)

    def test_missing_price_or_party_uses_the_native_map_before_anything_is_created(self):
        ZONE_VALUE.clear()
        with patch.object(fixture.build_buy, 'get_lot_value', lambda *a: 1 / 0, create=True):
            dialog = request()
            shown[0].answer(0)
            env.drain()
            self.assertIsNone(shown[1].rows[2].row_description.replace('RENTAL', '') or None)   # no price shown
            shown[1].answer(2)
            env.drain()
        self.assertEqual(fixture.native_calls[-1][0], dialog.dialog_id)
        self.assertEqual(manager.calls, [])
        fixture.native_calls[:] = []
        dialog = fixture.UiMapViewPicker(vacation_rows(), mode=VACATION)
        dialog.owner = None
        dialog.traveling_sims = []
        service._active_dialogs[dialog.dialog_id] = dialog
        dialog.distribute_dialog('MSG', {})
        self.assertEqual(len(fixture.native_calls), 1)
        self.assertIsNone(travel._pending)

    def test_unloaded_lot_sentinel_never_becomes_a_price(self):
        ZONE_VALUE.clear()                       # zone source unavailable
        with patch.object(fixture.build_buy, 'get_lot_value', lambda zone_id, furnished: (-400, -1), create=True):
            self.assertIsNone(travel._daily_price(40))
            dialog = request()
            shown[0].answer(0)
            env.drain()
            self.assertEqual(shown[1].rows[2].row_description, 'RENTAL')   # unpriced, no negative
            shown[1].answer(2)
            env.drain()
        self.assertEqual(fixture.native_calls[-1][0], dialog.dialog_id)  # native panel decides
        self.assertEqual(manager.calls, [])

    def test_zone_source_wins_over_a_build_buy_sentinel(self):
        with patch.object(fixture.build_buy, 'get_lot_value', lambda zone_id, furnished: (-1, -1), create=True):
            self.assertEqual(travel._daily_price(40), 1000)
        ZONE_VALUE[40] = float('nan')
        self.assertEqual(travel._daily_price(40), 1000)       # build_buy positive value used
        ZONE_VALUE[40] = 0
        with patch.object(fixture.build_buy, 'get_lot_value', lambda zone_id, furnished: (float('inf'), 0), create=True):
            self.assertIsNone(travel._daily_price(40))

    def test_lot_value_command_logs_both_sources(self):
        with patch.object(env.speech, 'log_line') as log:
            self.assertTrue(travel.a11y_lot_value('40'))
        line = log.call_args[0][0]
        self.assertIn("('zone', 200000)", line)
        self.assertIn("('build_buy', 200000)", line)
        self.assertTrue(line.endswith('price 1000'))

    def test_map_row_still_available_before_a_rental(self):
        dialog = request()
        shown[0].answer(0)
        env.drain()
        shown[1].answer(3)                      # open the map instead (Back, Cabin, Lodge, Map)
        env.drain()
        self.assertEqual(fixture.native_calls[-1][0], dialog.dialog_id)
        self.assertEqual(manager.calls, [])

    def test_ordinary_travel_rows_carry_no_price(self):
        fixture.request()
        shown[0].answer(1)
        env.drain()
        self.assertNotIn('per day', str(shown[1].rows[1].row_description))
        self.assertIsNone(travel._pending.places[0].rental)

    def test_stay_terms_exist(self):
        for term in ('price per day', 'choose a stay', 'stay one day', 'stay days', 'cannot afford', 'price changed'):
            self.assertNotEqual(lang.t(term), term, term)


if __name__ == '__main__':
    unittest.main(verbosity=1)
