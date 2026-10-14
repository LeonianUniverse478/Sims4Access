"""Keyboard travel list: dialog lifecycle against stubbed EA services.

Run with py -3.7 tools/test_travel_v14.py. Source bodies only; nothing here
is in-game evidence. The dialog service stub models EA's picker listener,
which pushes the continuation from the picked results without checking the
response, so a cancel carrying picks would travel.
"""
import sys
import types
import unittest
from unittest.mock import patch

import test_scanner_v5 as env

# ---------------------------------------------------------------- EA stubs

class ButtonType(object):
    DIALOG_RESPONSE_OK = 10001
    DIALOG_RESPONSE_CANCEL = 10002


ui_dialog = types.ModuleType('ui.ui_dialog')
ui_dialog.ButtonType = ButtonType


class ObjectPickerRow(object):
    def __init__(self, option_id=None, name=None, row_description=None, row_tooltip=None,
                 icon=None, icon_info=None, tag=None, is_selected=False, is_enable=True):
        self.option_id, self.name, self.row_description, self.tag = option_id, name, row_description, tag
        self.row_tooltip, self.is_enable = row_tooltip, is_enable


class BasePickerRow(ObjectPickerRow):
    pass


shown = []


class FakeWindow(object):
    """Our native picker window (what menu._picker returns)."""
    _next = 500

    def __init__(self, title, text):
        FakeWindow._next += 1
        self.dialog_id = FakeWindow._next
        self.title, self.text = title, text
        self.rows, self.listeners = [], []
        self.accepted = False
        self._picked = []

    def add_row(self, row):
        self.rows.append(row)

    def add_listener(self, fn):
        self.listeners.append(fn)

    def show_dialog(self):
        shown.append(self)

    def get_result_tags(self):
        return list(self._picked)

    def names(self):
        return [r.name for r in self.rows]

    def answer(self, index):
        self.accepted = True
        self._picked = [self.rows[index].tag]
        for fn in list(self.listeners):
            fn(self)

    def close(self):
        self.accepted = False
        self._picked = []
        for fn in list(self.listeners):
            fn(self)


class _Factory(object):
    def default(self, owner, title=None, text=None, **kwargs):
        return FakeWindow(title(), text())


class UiObjectPicker(object):
    UiObjectPickerObjectPickerType = types.SimpleNamespace(OBJECT=4)
    TunableFactory = staticmethod(lambda: _Factory())


class UiItemPicker(UiObjectPicker):
    pass


native_calls = []
pushed = []          # continuations EA's listener would push: (dialog_id, zone_ids)


class UiMapViewPicker(object):
    MapViewMode = types.SimpleNamespace(TRAVEL=0, VACATION=1, PURCHASE=2, CHANGE_VENUE=3)
    _next = 900

    def __init__(self, rows, mode=0):
        UiMapViewPicker._next += 1
        self.dialog_id = UiMapViewPicker._next
        self.picker_rows = rows
        self.picked_results = []
        self.map_view_mode = types.SimpleNamespace(mode=mode)

    def distribute_dialog(self, msg_type, dialog_msg, **kwargs):
        native_calls.append((self.dialog_id, msg_type, dialog_msg))

    def on_picker_selected(self):
        # MapViewPickerInteraction._on_picker_selected: results, not accepted.
        if self.picked_results:
            pushed.append((self.dialog_id, list(self.picked_results)))


sim_picker_native = []   # companion pickers the client was sent


class UiSimPicker(object):
    """EA's companion picker: rows are Sims, EA preselects household members,
    and its listener is the pushed interaction's own _on_picker_selected."""
    _next = 1500

    def __init__(self, interaction=None, minimum=0, rows=(7, 8)):
        UiSimPicker._next += 1
        self.dialog_id = UiSimPicker._next
        self.min_selectable = minimum
        self.picker_rows = [types.SimpleNamespace(option_id=row) for row in rows]
        self.picked_results = [rows[0]]
        self._listeners = [interaction.on_picker_selected] if interaction is not None else []

    def distribute_dialog(self, msg_type, dialog_msg, **kwargs):
        sim_picker_native.append(self.dialog_id)

    def on_picker_selected(self):
        for listener in list(self._listeners):
            listener(self)


ui_dialog_picker = types.ModuleType('ui.ui_dialog_picker')
ui_dialog_picker.UiSimPicker = UiSimPicker
ui_dialog_picker.ObjectPickerRow = ObjectPickerRow
ui_dialog_picker.BasePickerRow = BasePickerRow
ui_dialog_picker.UiObjectPicker = UiObjectPicker
ui_dialog_picker.UiItemPicker = UiItemPicker
ui_dialog_picker.UiMapViewPicker = UiMapViewPicker

# Pack region list (ui.ui_tuning) and region tuning instances (world.region).
REGION_WC, REGION_TOM, REGION_CAREER = object(), object(), object()
REGION_NAMES = {REGION_WC: 'region_Residential_WillowCreek', REGION_TOM: 'region_Residential_EP16World',
                REGION_CAREER: 'region_Career_PoliceStation'}
for _instance, _name in REGION_NAMES.items():
    pass
region_data = [types.SimpleNamespace(region_resource='wc', is_player_facing=True, region_name='Willow Creek'),
               types.SimpleNamespace(region_resource='tom', is_player_facing=True, region_name='Tomarang'),
               types.SimpleNamespace(region_resource='career', is_player_facing=False, region_name='EP01 career')]
ui_tuning = types.ModuleType('ui.ui_tuning')
ui_tuning.UiTuning = types.SimpleNamespace(PACK_SPECIFIC_DATA={1: types.SimpleNamespace(region_list=region_data)})
world_region = types.ModuleType('world.region')


class _RegionInstance(object):
    def __init__(self, name):
        self.__name__ = name


REGIONS = {key: _RegionInstance(name) for key, name in
           (('wc', 'region_Residential_WillowCreek'), ('tom', 'region_Residential_EP16World'),
            ('career', 'region_Career_PoliceStation'), ('odd', 'region_Something_Unlisted'))}
world_region.Region = types.SimpleNamespace(REGION_DESCRIPTION_TUNING_MAP={k: v for k, v in REGIONS.items() if k != 'odd'})
ZONE_REGION = {1: 'wc', 2: 'wc', 3: 'tom', 31: 'tom', 32: 'tom', 4: 'tom', 5: 'career', 6: 'odd'}
world_region.get_region_instance_from_zone_id = lambda zone_id: REGIONS.get(ZONE_REGION.get(zone_id))
world_pkg = types.ModuleType('world')
world_pkg.region = world_region
ui = types.ModuleType('ui')
ui.ui_dialog, ui.ui_dialog_picker, ui.ui_tuning = ui_dialog, ui_dialog_picker, ui_tuning


class FakeDialogService(object):
    def __init__(self):
        self._active_dialogs = {}
        self.picks, self.responses = [], []
        self.refuse_ok = False

    def get_dialog(self, dialog_id):
        return self._active_dialogs.get(dialog_id)

    def dialog_pick_result(self, dialog_id, picked_results=[], **kwargs):
        dialog = self._active_dialogs.get(dialog_id)
        if dialog is None:
            return False
        option_ids = [row.option_id for row in dialog.picker_rows]
        if any(result not in option_ids for result in picked_results):
            return False
        dialog.picked_results = list(picked_results)
        self.picks.append((dialog_id, list(picked_results)))
        return True

    def dialog_respond(self, dialog_id, response, client=None):
        dialog = self._active_dialogs.get(dialog_id)
        if dialog is None:
            return False
        if self.refuse_ok and response == ButtonType.DIALOG_RESPONSE_OK:
            return False
        self.responses.append((dialog_id, response))
        dialog.on_picker_selected()
        del self._active_dialogs[dialog_id]
        return True


class Row(object):
    def __init__(self, zone_id, name, neighborhood_id, world_id=1, venue=None, household=None, household_id=0):
        self.option_id = self.zone_id = zone_id
        self.name = name
        self.world_id = world_id
        self.venue_type_name = venue
        self.household_name = household
        self.tag = types.SimpleNamespace(zone_id=zone_id, neighborhood_id=neighborhood_id,
                                         world_id=world_id, household_id=household_id)


NEIGHBORHOODS = {10: 'Willow Creek', 20: 'Tomarang', 30: 'EP01_World'}
ZONE_NAMES = {1: 'Umbrage Manor', 2: 'Daisy Hovel', 3: '09 Taka Soi 15', 31: 'Unit 1', 32: 'Unit 2',
              4: 'Blue Velvet', 5: 'Police Station', 6: 'Odd Lot'}
MASTERS = {31: 3, 32: 3}
RESIDENTIAL = {1: True, 2: True, 3: True, 31: True, 32: True, 4: False, 5: False, 6: True}


class FakePersistence(object):
    def get_neighborhood_proto_buff(self, nid):
        return types.SimpleNamespace(name=NEIGHBORHOODS[nid]) if nid in NEIGHBORHOODS else None

    def get_zone_proto_buff(self, zone_id):
        return types.SimpleNamespace(name=ZONE_NAMES.get(zone_id, ''), world_id=1, lot_id=zone_id * 10)


class FakePlex(object):
    def get_master_zone_id(self, zone_id):
        return MASTERS.get(zone_id, zone_id)


class FakeManager(object):
    def __init__(self, zones):
        self._zones = list(zones)

    def get_allowed_zone_ids(self):
        return self._zones


class FakeTracker(object):
    def __init__(self, owner, managers):
        self.owner_household_id = owner
        self.business_type = 5
        self.business_managers = {}
        self.zoneless_business_managers = dict(enumerate(managers))


class FakeBusinessService(object):
    def __init__(self):
        self.trackers = []

    def business_trackers_gen(self):
        return iter(self.trackers)


class FakeSim(object):
    def __init__(self):
        self.sim_id = 700
        self.zone_id = 1000
        self.pushes = []
        self.result = True

    def push_super_affordance(self, affordance, target, context, **kwargs):
        self.pushes.append((affordance, target, context))
        return self.result


def rows():
    return [Row(1, 'Umbrage Manor', 10, household='Goth', household_id=7),
            Row(2, 'Daisy Hovel', 10, venue='VENUE'),
            Row(31, 'Unit 1', 20, world_id=2), Row(32, 'Unit 2', 20, world_id=2, household='Kim'),
            Row(4, 'Blue Velvet', 20, world_id=2, venue='LOUNGE', household='Bar', household_id=8),
            Row(5, 'Police Station', 30, world_id=3, venue='POLICE')]


localization = types.ModuleType('sims4.localization')
localization.LocalizationHelperTuning = types.SimpleNamespace(
    get_raw_text=lambda text: text,
    get_comma_separated_list=lambda *parts: ', '.join(str(p) for p in parts))
env.sims4.localization = localization
resources = types.ModuleType('sims4.resources')
resources.Types = types.SimpleNamespace(VENUE='venue', INTERACTION='interaction')
env.sims4.resources = resources
build_buy = types.ModuleType('build_buy')
build_buy.get_current_venue = lambda zone_id: zone_id
shared_messages = types.ModuleType('distributor.shared_messages')
shared_messages.IconInfoData = lambda **kwargs: kwargs
interactions_context = types.ModuleType('interactions.context')


class InteractionContext(object):
    SOURCE_PIE_MENU = 'pie'

    def __init__(self, sim, source, priority, client=None, pick=None):
        self.sim, self.source, self.priority, self.client, self.pick = sim, source, priority, client, pick


interactions_context.InteractionContext = InteractionContext
interactions_priority = types.ModuleType('interactions.priority')
interactions_priority.Priority = types.SimpleNamespace(High='high')
interactions_pkg = types.ModuleType('interactions')

TRAVEL_AFFORDANCE = object()
services = types.ModuleType('services')
service = FakeDialogService()
business = FakeBusinessService()
sim = FakeSim()
services.ui_dialog_service = lambda: service
services.get_persistence_service = lambda: FakePersistence()
services.get_plex_service = lambda: FakePlex()
services.current_zone = lambda: object()
services.current_zone_id = lambda: 1000
services.get_active_sim = lambda: sim
services.active_household_id = lambda: 1
services.business_service = lambda: business
services.client_manager = lambda: types.SimpleNamespace(get_first_client=lambda: 'client')
services.get_world_description_id = lambda world_id: 5000 + world_id
services.get_hide_from_lot_picker = lambda lot_id, world_desc: lot_id == 50
HOUSEHOLDS = {7: [types.SimpleNamespace(first_name=n, last_name='Goth') for n in ('Bella', 'Mortimer', 'Cassandra')],
              8: [types.SimpleNamespace(first_name='Barkeep', last_name='')]}
services.household_manager = lambda: types.SimpleNamespace(get=lambda hid: HOUSEHOLDS.get(hid))


def _instance_manager(kind):
    if kind == 'venue':
        return types.SimpleNamespace(get=lambda zone_id: types.SimpleNamespace(is_residential=RESIDENTIAL.get(zone_id, True)))
    return types.SimpleNamespace(get=lambda key: TRAVEL_AFFORDANCE if key == 423375 else None)


services.get_instance_manager = _instance_manager

patch.dict(sys.modules, {'ui': ui, 'ui.ui_dialog': ui_dialog, 'ui.ui_dialog_picker': ui_dialog_picker,
                         'ui.ui_tuning': ui_tuning, 'world': world_pkg, 'world.region': world_region,
                         'sims4.localization': localization, 'sims4.resources': resources,
                         'build_buy': build_buy, 'services': services,
                         'interactions': interactions_pkg, 'interactions.context': interactions_context,
                         'interactions.priority': interactions_priority,
                         'distributor.shared_messages': shared_messages}).start()

import tyjokr_a11y_travel as travel   # noqa: E402  (installs the wrap on the stub class)
menu = env.menu
lang = env.lang
OK, CANCEL = ButtonType.DIALOG_RESPONSE_OK, ButtonType.DIALOG_RESPONSE_CANCEL
MAP, BACK_W, BACK_P = lang.t('open the map instead'), lang.t('back to worlds'), lang.t('back to places')


def request(mode=0, picker_rows=None):
    """EA shows a map picker: register, then distribute (EA's order)."""
    dialog = UiMapViewPicker(rows() if picker_rows is None else picker_rows, mode=mode)
    service._active_dialogs[dialog.dialog_id] = dialog
    dialog.distribute_dialog('MSG', {'msg': dialog.dialog_id})
    return dialog


class TravelListTests(unittest.TestCase):
    def setUp(self):
        env.settings._stored.clear()
        env.settings._stored['keyboard'] = True
        # Today's M path; the Simplified menus front is test_travel_front.py.
        env.settings._stored['simplified_menus'] = False
        env.queue.clear()
        shown[:] = []
        native_calls[:] = []
        pushed[:] = []
        service._active_dialogs.clear()
        service.picks[:] = []
        service.responses[:] = []
        service.refuse_ok = False
        business.trackers = []
        sim.pushes = []
        sim.result = True
        sim.zone_id = 1000
        travel._pending = None
        travel._window_id = None
        travel._last_rows = []
        menu._visual_id = None
        self.fence = patch.object(env.keys, 'fence_opening_input', lambda: None)
        self.fence.start()
        self.speak = patch.object(env.speech, 'speak')
        self.spoken = self.speak.start()

    def tearDown(self):
        self.speak.stop()
        self.fence.stop()

    def spoken_last(self):
        return self.spoken.call_args[0][0]

    def test_wrap_installed_and_original_kept(self):
        self.assertEqual(UiMapViewPicker.distribute_dialog.__name__, 'a11y_travel_distribute_dialog')
        self.assertIsNotNone(travel._original_distribute)

    def test_keyboard_off_uses_native_map(self):
        env.settings._stored['keyboard'] = False
        dialog = request()
        self.assertEqual(native_calls, [(dialog.dialog_id, 'MSG', {'msg': dialog.dialog_id})])
        self.assertEqual(shown, [])
        self.assertIsNone(travel._pending)

    def test_travel_list_setting_off_uses_native_map(self):
        env.settings._stored['travel_list'] = False
        request()
        self.assertEqual(len(native_calls), 1)
        self.assertEqual(shown, [])

    def test_other_map_modes_fall_through(self):
        for mode in (1, 2, 3):
            request(mode=mode)
        self.assertEqual(len(native_calls), 3)
        self.assertEqual(shown, [])

    def test_world_window_lists_player_facing_worlds_only(self):
        request()
        self.assertEqual(native_calls, [])
        self.assertEqual(len(shown), 1)
        self.assertEqual(shown[0].names(), ['Tomarang', 'Willow Creek', MAP])   # career world dropped
        self.assertEqual([r.row_description for r in shown[0].rows][:2], ['3 places', '2 places'])
        self.assertEqual({p.zone_id for p in travel._pending.places}, {1, 2, 31, 32, 4})

    def test_world_rows_use_the_localized_region_name(self):
        ui_tuning.UiTuning.PACK_SPECIFIC_DATA[1].region_list[0].region_name = 'Willow Creek (localized)'
        try:
            request()
            self.assertEqual(shown[0].names()[1], 'Willow Creek (localized)')
        finally:
            ui_tuning.UiTuning.PACK_SPECIFIC_DATA[1].region_list[0].region_name = 'Willow Creek'

    def test_region_without_list_data_hands_the_request_to_the_native_map(self):
        request(picker_rows=[Row(1, 'Umbrage Manor', 10), Row(6, 'Odd Lot', 10)])
        self.assertEqual(len(native_calls), 1)
        self.assertEqual(shown, [])
        self.assertIsNone(travel._pending)

    def test_region_table_failure_hands_the_request_to_the_native_map(self):
        with patch.object(travel, '_region_table', lambda: {}):
            request()
        self.assertEqual(len(native_calls), 1)
        self.assertEqual(shown, [])

    def test_occupied_home_lists_its_residents(self):
        request()
        shown[0].answer(1)
        env.drain()
        self.assertEqual(shown[1].rows[2].name, 'Goth, Umbrage Manor')
        self.assertEqual(shown[1].rows[2].row_description, 'Residents: Bella Goth, Mortimer Goth, Cassandra Goth')
        shown[1].answer(0)
        env.drain()
        shown[2].answer(0)                      # Tomarang
        env.drain()
        self.assertEqual(shown[3].rows[2].row_description, 'LOUNGE, Bar')   # public venue: no resident list

    def test_occupied_home_reads_family_first(self):
        dialog = request()
        shown[0].answer(1)                      # Willow Creek
        env.drain()
        self.assertEqual(shown[1].names(), [BACK_W, 'Daisy Hovel', 'Goth, Umbrage Manor', MAP])
        self.assertEqual(shown[1].rows[2].row_description, 'Residents: Bella Goth, Mortimer Goth, Cassandra Goth')
        self.assertEqual(shown[1].rows[1].row_description, 'VENUE')
        shown[1].answer(2)                      # the Goth home, still zone 1
        env.drain()
        self.assertEqual(service.picks, [(dialog.dialog_id, [1])])
        self.assertEqual(service.responses, [(dialog.dialog_id, OK)])
        self.assertEqual(pushed, [(dialog.dialog_id, [1])])
        self.assertIsNone(travel._pending)
        self.assertEqual(native_calls, [])

    def test_public_venue_owned_by_a_household_stays_lot_first(self):
        request()
        shown[0].answer(0)                      # Tomarang
        env.drain()
        self.assertEqual(shown[1].names(), [BACK_W, '09 Taka Soi 15', 'Blue Velvet', MAP])
        self.assertEqual(shown[1].rows[2].row_description, 'LOUNGE, Bar')

    def test_multi_unit_building_opens_unit_window_and_commits_unit_zone(self):
        dialog = request()
        shown[0].answer(0)                      # Tomarang
        env.drain()
        self.assertEqual(shown[1].rows[1].row_description, '2 units')
        shown[1].answer(1)                      # the building (master not offered)
        env.drain()
        self.assertEqual(shown[2].names(), [BACK_P, 'Kim, Unit 2', 'Unit 1'])
        self.assertIsNone(shown[2].rows[1].row_description)
        shown[2].answer(1)                      # Kim's unit, zone 32
        env.drain()
        self.assertEqual(service.picks, [(dialog.dialog_id, [32])])
        self.assertEqual(service.responses, [(dialog.dialog_id, OK)])

    def test_offered_master_unit_is_listed_with_its_household(self):
        master_rows = [Row(3, '09 Taka Soi 15', 20, world_id=2, household='Cahyaputri', household_id=9),
                       Row(31, '08 Taka Soi 15', 20, world_id=2), Row(32, '07 Taka Soi 15', 20, world_id=2, household='Kim')]
        dialog = request(picker_rows=master_rows)
        shown[0].answer(0)
        env.drain()
        self.assertEqual(shown[1].names(), [BACK_W, 'Cahyaputri, 09 Taka Soi 15', MAP])
        self.assertEqual(shown[1].rows[1].row_description, '3 units')
        shown[1].answer(1)
        env.drain()
        self.assertEqual(shown[2].names(), [BACK_P, '08 Taka Soi 15', 'Cahyaputri, 09 Taka Soi 15', 'Kim, 07 Taka Soi 15'])
        shown[2].answer(2)                      # the master unit itself
        env.drain()
        self.assertEqual(service.picks, [(dialog.dialog_id, [3])])
        self.assertEqual(service.responses, [(dialog.dialog_id, OK)])

    def test_offered_master_without_other_units_is_a_plain_lot(self):
        dialog = request(picker_rows=[Row(3, '09 Taka Soi 15', 20, world_id=2, household='Cahyaputri')])
        shown[0].answer(0)
        env.drain()
        self.assertIsNone(shown[1].rows[1].row_description)
        shown[1].answer(1)
        env.drain()
        self.assertEqual(len(shown), 2)         # no unit window
        self.assertEqual(service.picks, [(dialog.dialog_id, [3])])

    def test_back_rows_return_without_touching_the_original(self):
        request()
        shown[0].answer(0)
        env.drain()
        shown[1].answer(1)
        env.drain()
        shown[2].answer(0)                      # back to places
        env.drain()
        self.assertEqual(shown[3].names()[1:3], ['09 Taka Soi 15', 'Blue Velvet'])
        self.assertEqual(shown[3].rows[1].row_description, '2 units')
        shown[3].answer(0)                      # back to worlds
        env.drain()
        self.assertEqual(shown[4].names()[0], 'Tomarang')
        self.assertEqual(service.responses, [])
        self.assertIsNotNone(travel._pending)

    def test_grouping_is_fresh_on_every_visit_and_counts_an_offered_master(self):
        dialog = request()
        places = [p for p in travel._collect(dialog) if p.world_key == 20]
        first = travel._buildings(places)
        second = travel._buildings(places)
        self.assertEqual([len(e.units) for e in first], [0, 2])
        self.assertEqual([len(e.units) for e in second], [0, 2])
        self.assertTrue(all(len(p.units) == 0 for p in places))
        with_master = travel._collect(UiMapViewPicker([Row(3, '09', 20), Row(31, '08', 20), Row(32, '07', 20)]))
        grouped = travel._buildings(with_master)
        self.assertEqual([len(e.units) for e in grouped], [3])
        self.assertEqual([len(e.units) for e in travel._buildings(with_master)], [3])
        self.assertTrue(all(unit is not grouped[0] and not unit.units for unit in grouped[0].units))   # no self-reference
        self.assertEqual({p.zone_id for p in travel._units_of(types.SimpleNamespace(places=with_master), 3)}, {3, 31, 32})

    def test_escape_cancels_the_trip_natively(self):
        dialog = request()
        shown[0].close()
        self.assertEqual(service.responses, [(dialog.dialog_id, CANCEL)])
        self.assertEqual(service.picks, [])
        self.assertEqual(pushed, [])
        self.assertIsNone(travel._pending)
        self.assertEqual(self.spoken_last(), lang.t('travel cancelled'))

    def test_escape_in_place_window_also_cancels(self):
        dialog = request()
        shown[0].answer(1)
        env.drain()
        shown[1].close()
        self.assertEqual(service.responses, [(dialog.dialog_id, CANCEL)])

    def test_failed_pick_cancels_the_original_without_travelling(self):
        dialog = request()
        dialog.picker_rows = dialog.picker_rows[1:]   # zone 1 withdrawn after listing
        shown[0].answer(1)
        env.drain()
        shown[1].answer(2)                      # the Goth home, zone 1
        env.drain()
        self.assertEqual(service.picks, [])
        self.assertEqual(service.responses, [(dialog.dialog_id, CANCEL)])
        self.assertEqual(pushed, [])
        self.assertNotIn(dialog.dialog_id, service._active_dialogs)
        self.assertIsNone(travel._pending)
        self.assertEqual(self.spoken_last(), lang.t('action unavailable'))

    def test_refused_ok_clears_picks_before_cancelling(self):
        dialog = request()
        service.refuse_ok = True
        shown[0].answer(1)
        env.drain()
        shown[1].answer(2)
        env.drain()
        self.assertEqual(service.picks, [(dialog.dialog_id, [1])])
        self.assertEqual(service.responses, [(dialog.dialog_id, CANCEL)])
        self.assertEqual(dialog.picked_results, [])
        self.assertEqual(pushed, [])            # the cancel carried no picks

    def test_stale_original_dialog_is_not_answered(self):
        dialog = request()
        del service._active_dialogs[dialog.dialog_id]  # EA dropped it (interaction cancelled)
        shown[0].answer(1)
        env.drain()
        shown[1].answer(2)
        env.drain()
        self.assertEqual(service.picks, [])
        self.assertEqual(service.responses, [])
        self.assertEqual(self.spoken_last(), lang.t('action unavailable'))

    def test_duplicate_window_reply_is_ignored(self):
        dialog = request()
        shown[0].answer(1)
        env.drain()
        window = shown[1]
        window.answer(2)
        window.answer(2)                        # a second reply from the same window
        env.drain()
        self.assertEqual(service.picks, [(dialog.dialog_id, [1])])
        self.assertEqual(len(service.responses), 1)

    def test_replaced_window_reply_is_ignored(self):
        request()
        first = shown[0]
        first.answer(1)
        env.drain()
        first.answer(1)                         # stale reply from the world window
        env.drain()
        self.assertEqual(len(shown), 2)
        self.assertEqual(service.responses, [])

    def test_queued_reply_of_a_superseded_request_is_dropped(self):
        first = request()
        shown[-1].answer(1)
        env.drain()
        shown[-1].answer(2)                     # commit queued for the first request
        second = request()                      # arrives before the pump drains
        self.assertEqual(service.responses, [(first.dialog_id, CANCEL)])
        env.drain()
        self.assertEqual(service.responses, [(first.dialog_id, CANCEL)])
        self.assertEqual(pushed, [])
        self.assertIs(travel._pending.dialog, second)
        self.assertIn(second.dialog_id, service._active_dialogs)

    def test_dead_pump_cancels_instead_of_running_inline(self):
        dialog = request()
        with patch.object(travel.pump, 'post', return_value=False):
            shown[0].answer(1)
        self.assertEqual(len(shown), 1)
        self.assertEqual(service.responses, [(dialog.dialog_id, CANCEL)])
        self.assertIsNone(travel._pending)

    def test_settings_turned_off_mid_flow_cancel_the_request(self):
        dialog = request()
        env.settings._stored['travel_list'] = False
        shown[0].answer(1)
        env.drain()
        self.assertEqual(service.responses, [(dialog.dialog_id, CANCEL)])
        self.assertEqual(len(shown), 1)

    def test_window_failure_mid_flow_cancels_the_request(self):
        dialog = request()
        with patch.object(menu, '_picker', return_value=None):
            shown[0].answer(1)
            env.drain()
        self.assertEqual(len(shown), 1)
        self.assertEqual(service.responses, [(dialog.dialog_id, CANCEL)])
        self.assertIsNone(travel._pending)

    def test_map_fallback_hands_over_once_and_never_after_terminal(self):
        dialog = request()
        pending = travel._pending
        shown[0].answer(2)                      # open the map instead
        env.drain()
        self.assertEqual(native_calls, [(dialog.dialog_id, 'MSG', {'msg': dialog.dialog_id})])
        self.assertIsNone(travel._pending)
        self.assertFalse(travel._fallback(pending))   # no second hand-over
        self.assertEqual(len(native_calls), 1)
        second = request()
        pending = travel._pending
        shown[-1].answer(1)
        env.drain()
        shown[-1].answer(2)                     # commit
        env.drain()
        self.assertEqual(service.responses[-1], (second.dialog_id, OK))
        self.assertFalse(travel._fallback(pending))
        self.assertEqual(len(native_calls), 1)

    def test_map_fallback_from_place_window(self):
        dialog = request()
        shown[0].answer(1)
        env.drain()
        shown[1].answer(3)
        env.drain()
        self.assertEqual(native_calls[-1][0], dialog.dialog_id)
        self.assertEqual(service.responses, [])

    def test_empty_or_broken_rows_use_native_map(self):
        request(picker_rows=[])
        self.assertEqual(len(native_calls), 1)
        self.assertEqual(shown, [])
        self.assertIsNone(travel._pending)

    def test_only_hidden_rows_use_native_map(self):
        request(picker_rows=[Row(5, 'Police Station', 30, world_id=3)])
        self.assertEqual(len(native_calls), 1)
        self.assertEqual(shown, [])

    def test_newer_request_cancels_an_open_list_natively(self):
        first = request()
        second = request()
        self.assertIs(travel._pending.dialog, second)
        self.assertEqual(service.responses, [(first.dialog_id, CANCEL)])
        shown[0].answer(1)                      # reply from the first list's window
        env.drain()
        self.assertEqual(len(service.responses), 1)
        self.assertEqual(len(shown), 2)

    def test_small_business_lot_of_another_household_goes_to_the_map(self):
        business.trackers = [FakeTracker(7, [FakeManager([1])])]      # one business on residential zone 1
        dialog = request()
        shown[0].answer(1)
        env.drain()
        shown[1].answer(2)                      # the Goth home, owned by household 7
        env.drain()
        self.assertEqual(native_calls[-1][0], dialog.dialog_id)
        self.assertEqual(service.picks, [])
        self.assertEqual(self.spoken.call_args_list[-1][0][0], lang.t('map required here'))

    def test_small_business_manager_shapes_and_failure_keeps_native_route(self):
        places = {p.zone_id: p for p in travel._collect(request())}
        prop = types.SimpleNamespace(allowed_zone_ids=[1])                       # EA property shape
        business.trackers = [FakeTracker(7, [prop])]
        self.assertTrue(travel._needs_native_map(places[1]))
        by_household = types.SimpleNamespace(
            business_trackers_gen=lambda: iter([]),
            get_business_trackers_for_household=lambda owner: {5: FakeTracker(7, [FakeManager([1])])})
        with patch.object(services, 'business_service', lambda: by_household):
            self.assertTrue(travel._needs_native_map(places[1]))
        broken = types.SimpleNamespace(business_trackers_gen=lambda: 1 / 0)
        with patch.object(services, 'business_service', lambda: broken):
            self.assertTrue(travel._needs_native_map(places[1]))      # owned by another household: keep the map
            self.assertFalse(travel._needs_native_map(places[2]))     # unowned: nothing to ask

    def test_small_business_threshold_and_ownership(self):
        one = FakeTracker(8, [FakeManager([4])])
        two = FakeTracker(8, [FakeManager([4]), FakeManager([4, 9])])
        places = {p.zone_id: p for p in travel._collect(request())}
        business.trackers = [one]
        self.assertFalse(travel._needs_native_map(places[4]))     # venue lot needs two
        business.trackers = [two]
        self.assertTrue(travel._needs_native_map(places[4]))
        business.trackers = [FakeTracker(1, [FakeManager([1])])]  # active household's own
        self.assertFalse(travel._needs_native_map(places[1]))
        business.trackers = []
        self.assertFalse(travel._needs_native_map(places[2]))     # unowned lot

    def test_probe_logs_every_listed_row(self):
        request()
        with patch.object(env.speech, 'log_line') as log:
            travel.a11y_travel_probe()
        lines = [c[0][0] for c in log.call_args_list if c[0][0].startswith('travel probe:')]
        self.assertEqual(len(lines), 5)
        self.assertIn("zone 1 name 'Umbrage Manor' world 'Willow Creek' region 'region_Residential_WillowCreek' facing True hide False", lines[0])

    def test_keyboard_entry_pushes_the_tuned_travel_chain(self):
        travel._epoch = 0
        del travel._requests[:]
        travel.start_lease()
        env.queue.clear()
        self.assertTrue(travel.a11y_travel('1', '1'))
        self.assertEqual(sim.pushes, [])        # deferred to the simulation pump
        env.drain()
        self.assertEqual(len(sim.pushes), 1)
        affordance, target, context = sim.pushes[0]
        self.assertIs(affordance, TRAVEL_AFFORDANCE)
        self.assertIs(target, sim)
        self.assertEqual((context.source, context.priority, context.client, context.pick), ('pie', 'high', 'client', None))

    def test_keyboard_entry_refusals_are_spoken(self):
        travel._epoch = 0
        del travel._requests[:]
        travel.start_lease()
        env.queue.clear()
        sim.result = False
        travel.a11y_travel('1', '2')
        env.drain()
        self.assertEqual(self.spoken_last(), lang.t('action unavailable'))
        sim.result = True
        sim.zone_id = 2000                      # active Sim is away
        travel.a11y_travel('1', '3')
        env.drain()
        self.assertEqual(self.spoken_last(), lang.t('sim unavailable'))
        self.assertEqual(len(sim.pushes), 1)
        env.settings._stored['travel_list'] = False
        self.assertFalse(travel.a11y_travel('1', '4'))
        self.assertEqual(env.queue, [])

    def test_setting_in_cfg_menu_and_readout(self):
        self.assertTrue(env.settings.DEFAULTS['travel_list'])
        self.assertIn('travel list = on', env.settings.render_default())
        self.assertIn('travel_list', [r.key for r in menu.ROWS])
        self.assertEqual(env.settings._FILE_MAP[('features', 'travel list')], 'travel_list')
        for term in ('travel list', 'travel destinations', 'choose a world', 'choose a place',
                     'choose a unit', 'places count', 'units count', 'open the map instead',
                     'back to worlds', 'back to places', 'other worlds', 'travel cancelled',
                     'map required here', 'residents'):
            self.assertNotEqual(lang.t(term), term, term)


if __name__ == '__main__':
    unittest.main(verbosity=1)
