"""Keyboard travel list: World, place and unit windows instead of the map.

Python map picker travel requests (the Sim menu, phone and street Travel
chains, Invite To and the other tuned map pickers) end in EA's
UiMapViewPicker dialog. The rows (one per eligible zone) are computed by EA
before the dialog is shown; the native map only answers it with a zone id.
With keyboard navigation on, that request is answered from three native
picker windows instead, and the original dialog is completed through EA's
own dialog service, so companions, eligibility, situation creation, loading
and cancellation stay native. The M key opens the map through the client's
own GoToNeighborhoodTravel path with no Python dialog; it is not handled
here and keeps its native behaviour (a11y.travel offers the tuned Travel
chain for a keyboard entry instead).

Worlds follow the client's own visibility rule: the pack region list in
UiTuning marks each region player facing or not, and the native map draws
only player-facing regions, so the list drops the others (career and hidden
lots that EA's row filter still offers). World names come from the same
list, localized.

Ordinary travel and vacation requests are handled. A vacation adds a Stay
window (1 to 7 days with the cost, as EA's rental panel computes it) and
rents the lot through EA's travel group manager before the dialog is
answered, exactly as the native panel does. Purchase and change-venue
requests, and anything unexpected, fall through to the native map. A row on
the world and place windows opens the native map for the same request, and
lots where the map would ask which small business to visit are handed to
the map as well.

Lifecycle rules: one pending request at a time; every deferred step carries
the request it belongs to and refuses any other; EA's dialog is never left
open without a window (it is cancelled natively instead); picked results are
cleared before any cancel, because EA's picker listener acts on results
without checking the response.
"""
import sims4.commands

import tyjokr_a11y_lang as lang
import tyjokr_a11y_menu as menu
import tyjokr_a11y_pump as pump
import tyjokr_a11y_settings as settings
import tyjokr_a11y_speech as speech

_original_distribute = None
_pending = None
_window_id = None
_last_rows = []

WORLD, PLACE, UNIT = 'world', 'place', 'unit'
_MAP_ROW = 'map'
_BACK_ROW = 'back'
_RESIDENTIAL_BUSINESS_MIN = 1
_VENUE_BUSINESS_MIN = 2
_TRAVEL_AFFORDANCE = 423375   # self_SimPicker_TravelWith (Sim menu Travel)
_STAY_ROW = 'stay'
_MAX_STAY_DAYS = 7            # GERentalPanelTunables.MAX_RENTAL_DAYS
TRAVEL, VACATION = 'travel', 'vacation'


class _Pending(object):
    __slots__ = ('dialog', 'msg_type', 'dialog_msg', 'kwargs', 'places',
                 'worlds', 'fallback_used', 'mode', 'party', 'rented',
                 'generation', 'prices')

    def __init__(self, dialog, msg_type, dialog_msg, kwargs, mode=TRAVEL):
        self.dialog = dialog
        self.msg_type = msg_type
        self.dialog_msg = dialog_msg
        self.kwargs = kwargs
        self.places = []
        self.worlds = []
        self.fallback_used = False
        self.mode = mode
        self.party = []       # sim infos travelling: the actor plus companions
        self.rented = False   # a vacation was created: no native fallback after this
        self.generation = 0   # price bridge token: replies for other requests are ignored
        self.prices = {}      # zone id -> per-day price the client reported for THIS request


class _Place(object):
    __slots__ = ('zone_id', 'name', 'world_key', 'world_name', 'world_label',
                 'venue', 'household', 'household_id', 'master', 'units',
                 'residential', 'visible', 'region', 'residents', 'rental', 'price')

    def __init__(self, zone_id, name):
        self.zone_id = zone_id
        self.name = name
        self.world_key = 0
        self.world_name = ''
        self.world_label = None
        self.venue = None
        self.household = None
        self.household_id = 0
        self.master = zone_id
        self.units = ()
        self.residential = None
        self.visible = None
        self.region = ''
        self.residents = ()
        self.rental = None
        self.price = None

    def copy(self):
        other = _Place(self.zone_id, self.name)
        for slot in ('world_key', 'world_name', 'world_label', 'venue', 'household',
                     'household_id', 'master', 'residential', 'visible', 'region', 'residents',
                     'rental', 'price'):
            setattr(other, slot, getattr(self, slot))
        return other

    def label(self):
        """Occupied homes read family first; venues and empty lots lot first."""
        if self.residential is True and self.household:
            return '{}, {}'.format(self.household, self.name)
        return self.name


def _say(term):
    speech.speak(lang.t(term), explicit=True)


def enabled():
    return bool(settings.get('keyboard', True)) and bool(settings.get('travel_list', True))


def _request_mode(dialog):
    try:
        modes = type(dialog).MapViewMode
        mode = dialog.map_view_mode.mode
        if mode == modes.TRAVEL:
            return TRAVEL
        if mode == modes.VACATION:
            return VACATION
    except Exception:
        pass
    return None


def _rental(zone_id):
    """True for a rentable vacation lot, False for another venue, None unknown."""
    venue = _venue(zone_id)
    if venue is None:
        return None
    try:
        return bool(venue.is_rental)
    except Exception:
        return None


def _lot_values(zone_id):
    """Candidate furnished lot values for a zone that may not be loaded, as
    (source, value) pairs. EA's own code reads an unloaded lot through the
    zone manager's uninstantiated zone data (the home lot while away); the
    build-buy call is only valid for a loaded lot and returns a sentinel
    otherwise, so it comes second and only counts when positive."""
    found = []
    try:
        import services
        zone = services.get_zone(zone_id, allow_uninstantiated_zones=True)
        lot = getattr(zone, 'lot', None)
        if lot is not None:
            found.append(('zone', lot.furnished_lot_value))
    except Exception as ex:
        found.append(('zone', 'error {!r}'.format(ex)))
    try:
        import build_buy
        found.append(('build_buy', build_buy.get_lot_value(zone_id, True)[0]))
    except Exception as ex:
        found.append(('build_buy', 'error {!r}'.format(ex)))
    return found


def _positive(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float('inf'), float('-inf')) or number <= 0:
        return None
    return number


_price_generation = 0   # grows per vacation request; a reply must carry the current value
_MAX_DAILY_PRICE = 2 ** 31 - 1   # the client reports an unsigned int; anything larger is not a price


def _request_client_price(pending, zone_id):
    """Ask the client for the lot's rental price (the map's own numbers:
    GetNeighborhoodLotData and GetLotRentalPriceCalculator). The answer
    arrives on a11y.lotprice_enc with this request's generation and is kept
    on the request only, never across vacations."""
    return _ui('A11y|lotprice|{}|{}'.format(int(zone_id), pending.generation))


def _daily_price(zone_id, pending=None):
    """EA's rental panel price. The client's answer for this request is used
    when it has arrived; otherwise the furnished lot value times the tuned
    modifiers, truncated. None when no positive value is available, so the
    row stays unpriced and picking it hands the request to the native map."""
    if pending is not None:
        cached = _positive(pending.prices.get(int(zone_id)))
        if cached is not None:
            return int(cached)
    try:
        from world.rentable_lot_tuning import RentableZoneTuning
        modifiers = RentableZoneTuning.PRICE_MODIFIERS
    except Exception:
        return None
    for source, value in _lot_values(zone_id):
        number = _positive(value)
        if number is None:
            continue
        price = _positive(number * modifiers.multiply + modifiers.add)
        if price is not None:
            return int(price)
    return None


def _party(dialog):
    """Sim infos the request travels with: the actor plus companions."""
    sims = [getattr(dialog, 'owner', None)] + list(getattr(dialog, 'traveling_sims', None) or ())
    infos = []
    for sim in sims:
        info = getattr(sim, 'sim_info', None) if sim is not None else None
        if info is None or info in infos:
            continue
        infos.append(info)
    return infos


def _funds():
    try:
        import services
        return int(services.active_household().funds.money)
    except Exception:
        return None


def _zone_loaded():
    try:
        import services
        return services.current_zone() is not None
    except Exception:
        return False


def _service():
    import services
    return services.ui_dialog_service()


def _dialog_active(dialog):
    """True while EA still holds this exact dialog as active."""
    try:
        service = _service()
        lookup = getattr(service, 'get_dialog', None)
        if lookup is not None:
            return lookup(dialog.dialog_id) is dialog
        return service._active_dialogs.get(dialog.dialog_id) is dialog
    except Exception:
        return False


# ------------------------------------------------------------ zone facts

def _venue(zone_id):
    try:
        import build_buy
        import services
        import sims4.resources
        venue_id = build_buy.get_current_venue(zone_id)
        return services.get_instance_manager(sims4.resources.Types.VENUE).get(venue_id)
    except Exception:
        return None


def _residential(zone_id):
    """True, False, or None when the venue cannot be read."""
    venue = _venue(zone_id)
    if venue is None:
        return None
    try:
        return bool(venue.is_residential)
    except Exception:
        return None


_is_residential = _residential


def _residents(household_id):
    """Full names of the Sims living in a household, in household order."""
    try:
        import services
        household = services.household_manager().get(household_id)
        if household is None:
            return ()
        names = []
        for info in household:
            full = ' '.join(str(part) for part in (getattr(info, 'first_name', ''), getattr(info, 'last_name', '')) if part)
            if full:
                names.append(full)
        return tuple(names)
    except Exception:
        return ()


def _region_table():
    """Region tuning instance -> (player facing, localized name), from the
    same pack region list the client's world selector uses."""
    table = {}
    try:
        from ui.ui_tuning import UiTuning
        from world.region import Region
        for pack_data in UiTuning.PACK_SPECIFIC_DATA.values():
            for region_data in getattr(pack_data, 'region_list', ()) or ():
                instance = Region.REGION_DESCRIPTION_TUNING_MAP.get(region_data.region_resource)
                if instance is not None:
                    table[instance] = (bool(getattr(region_data, 'is_player_facing', True)),
                                       getattr(region_data, 'region_name', None))
    except Exception as ex:
        speech.log_line('travel: region table unavailable ({!r})'.format(ex))
    return table


def _region_of(zone_id):
    try:
        from world import region
        return region.get_region_instance_from_zone_id(zone_id)
    except Exception:
        return None


def _collect(dialog, vacation=False, pending=None):
    """One entry per row of EA's dialog, grouped by world; rows in regions the
    client never draws are dropped."""
    import services
    persistence = services.get_persistence_service()
    try:
        plex = services.get_plex_service()
    except Exception:
        plex = None
    regions = _region_table()
    if not regions:
        raise ValueError('region visibility data unavailable')
    places = []
    names = {}
    hidden = 0
    skipped = 0
    for row in dialog.picker_rows:
        zone_id = getattr(row, 'zone_id', None) or getattr(row, 'option_id', None)
        if not zone_id:
            continue
        place = _Place(int(zone_id), str(getattr(row, 'name', '') or ''))
        data = getattr(row, 'tag', None)
        neighborhood_id = getattr(data, 'neighborhood_id', 0) or 0
        world_id = getattr(row, 'world_id', 0) or getattr(data, 'world_id', 0) or 0
        place.world_key = neighborhood_id or world_id
        region = _region_of(place.zone_id)
        place.region = getattr(region, '__name__', '') if region is not None else ''
        info = regions.get(region) if region is not None else None
        if info is None:
            # No visibility data for this region: the native map decides.
            raise ValueError('region without list data: {}'.format(place.region or place.world_key))
        place.visible = info[0]
        place.world_label = info[1]
        if place.visible is False:
            hidden += 1
            continue
        if place.world_key not in names:
            label = ''
            try:
                proto = persistence.get_neighborhood_proto_buff(neighborhood_id) if neighborhood_id else None
                label = str(getattr(proto, 'name', '') or '')
            except Exception:
                label = ''
            names[place.world_key] = label or lang.t('other worlds')
        place.world_name = names[place.world_key]
        place.venue = getattr(row, 'venue_type_name', None)
        place.household = getattr(row, 'household_name', None) or None
        place.household_id = getattr(data, 'household_id', 0) or 0
        place.residential = _residential(place.zone_id)
        if place.residential is True and place.household_id:
            place.residents = _residents(place.household_id)
        if vacation:
            place.rental = _rental(place.zone_id)
            if place.rental is not True:
                # Sims on vacation may only stay on lots designated as
                # vacation rentals (the native map refuses the others).
                skipped += 1
                continue
            place.price = _daily_price(place.zone_id, pending)
            if place.price is None:
                _request_client_price(pending, place.zone_id)
        if plex is not None:
            try:
                place.master = int(plex.get_master_zone_id(place.zone_id))
            except Exception:
                place.master = place.zone_id
        places.append(place)
    if skipped:
        speech.log_line('travel: {} non-rental rows left to the native rules'.format(skipped))
    if hidden:
        speech.log_line('travel: {} rows in non player-facing regions dropped'.format(hidden))
    return places


def _group(places, master):
    """Every offered zone of one building, the master included when EA
    offered it (a master can be a real unit, not only a shell)."""
    return [p for p in places if p.master == master]


def _buildings(places):
    """Fresh top-level entries for one world: plain lots, and one entry per
    multi-unit building carrying copies of its unit rows. Never alters the
    collected places, so repeated visits group identically."""
    top = []
    by_master = {}
    for place in places:
        if place.master == place.zone_id:
            entry = place.copy()
            entry.units = []
            by_master[place.zone_id] = entry
            top.append(entry)
    for place in places:
        if place.master != place.zone_id:
            building = by_master.get(place.master)
            if building is None:
                building = _Place(place.master, _zone_name(place.master) or place.world_name)
                building.world_key = place.world_key
                building.world_name = place.world_name
                building.units = []
                by_master[place.master] = building
                top.append(building)
            if not building.units:
                master = by_master[place.master]
                if any(p.zone_id == master.zone_id for p in places):
                    building.units.append(master.copy())   # a plain row, not the building entry itself
            building.units.append(place)
    return top


def _zone_name(zone_id):
    try:
        import services
        proto = services.get_persistence_service().get_zone_proto_buff(zone_id)
        return str(getattr(proto, 'name', '') or '')
    except Exception:
        return ''


def _units_of(pending, master):
    """Unit rows to offer for a building: all offered members including an
    offered master; an offered master alone is a plain lot (empty list)."""
    group = _group(pending.places, master)
    if len(group) < 2:
        return []
    return group


def _find(pending, zone_id):
    for place in pending.places:
        if place.zone_id == zone_id:
            return place
    return None


# --------------------------------------------------- small business gate

def _allowed_zones(manager):
    zones = getattr(manager, 'allowed_zone_ids', None)
    if zones is None:
        getter = getattr(manager, 'get_allowed_zone_ids', None)
        zones = getter() if getter is not None else ()
    elif callable(zones):
        zones = zones()
    return tuple(zones or ())


def _household_trackers(business, owner):
    lookup = getattr(business, 'get_business_trackers_for_household', None)
    found = lookup(owner) if lookup is not None else None
    if found is None:
        found = [t for t in business.business_trackers_gen()
                 if getattr(t, 'owner_household_id', None) == owner]
    elif isinstance(found, dict):
        found = list(found.values())
    return list(found)


def _needs_native_map(place):
    """The native map asks which of another household's small businesses to
    visit when enough of them are assigned to the lot (one on a residential
    lot, two on a venue); the list cannot ask, so such lots are handed to the
    map. When the check itself fails for a lot another household owns, the
    native route is kept rather than skipping the business choice."""
    import services
    owner = int(place.household_id or 0)
    if not owner:
        return False
    try:
        if owner == services.active_household_id():
            return False
        count = 0
        for tracker in _household_trackers(services.business_service(), owner):
            managers = list(getattr(tracker, 'business_managers', {}).values())
            managers += list(getattr(tracker, 'zoneless_business_managers', {}).values())
            for manager in managers:
                if place.zone_id in _allowed_zones(manager):
                    count += 1
        if count == 0:
            return False
        residential = place.residential
        if residential is None:
            residential = _residential(place.zone_id)
        minimum = _VENUE_BUSINESS_MIN if residential is False else _RESIDENTIAL_BUSINESS_MIN
        return count >= minimum
    except Exception as ex:
        speech.log_line('travel: small business check failed for zone {} ({!r}); native map kept'.format(place.zone_id, ex))
        return True


# ---------------------------------------------------------------- windows

def _icon():
    try:
        import services
        from distributor.shared_messages import IconInfoData
        sim = services.get_active_sim()
        if sim is not None:
            return IconInfoData(obj_instance=sim)
    except Exception:
        pass
    return None


def _detail(place):
    parts = []
    if place.units:
        parts.append(menu._raw(lang.t('units count').format(len(place.units))))
    if place.venue is not None:
        parts.append(place.venue)
    if place.household and place.label() == place.name:
        parts.append(menu._raw(str(place.household)))
    if place.residents:
        parts.append(menu._raw(lang.t('residents').format(', '.join(place.residents))))
    if place.price is not None:
        parts.append(menu._raw(lang.t('price per day').format(place.price)))
    return menu._join(*parts) if parts else None


def _open_window(pending, title, text, rows, on_pick):
    """rows: (localized name, localized description or None, tag). A window
    that cannot open cancels the request rather than leaving EA's dialog
    open with nothing on screen."""
    global _window_id
    if _pending is not pending:
        return False
    try:
        from ui.ui_dialog_picker import ObjectPickerRow
        menu._cancel_dialog(_window_id)
        _window_id = None
        dialog = menu._picker(lang.t(title), lang.t(text))
        if dialog is None:
            raise ValueError('no active Sim')
        icon_info = _icon()
        for index, (name, detail, tag) in enumerate(rows):
            dialog.add_row(ObjectPickerRow(option_id=index, name=name, row_description=detail,
                                           row_tooltip=None, icon=None, icon_info=icon_info,
                                           tag=tag, is_selected=False))
        dialog.add_listener(lambda reply, handler=on_pick, owner=pending: handler(owner, reply))
        try:
            import tyjokr_a11y_keys as keys
            keys.fence_opening_input()
        except Exception:
            pass
        dialog.show_dialog()
        _window_id = dialog.dialog_id
        return True
    except Exception as ex:
        speech.log_line('travel: window failed ({!r}); request cancelled'.format(ex))
        _cancel(pending)
        return False


def _reply(pending, dialog):
    """Common picker-reply gate: this request, our current window, one
    answer only, settings still on."""
    global _window_id
    if _pending is not pending or dialog.dialog_id != _window_id:
        return None
    _window_id = None
    if not dialog.accepted or not enabled():
        _cancel(pending)
        return None
    try:
        tags = list(dialog.get_result_tags())
    except Exception as ex:
        speech.log_line('travel: pick result failed: {!r}'.format(ex))
        tags = []
    if len(tags) != 1:
        _cancel(pending)
        return None
    return tags[0]


def _later(pending, fn, *args):
    """Continue on the simulation pump after EA has finished handling the
    reply. A dead pump cancels the request instead of running inline."""
    def step(owner=pending):
        if _pending is not owner:
            return
        if enabled():
            fn(owner, *args)
        else:
            _cancel(owner)        # switched off between the reply and this step
    if not pump.post(step):
        speech.log_line('travel: pump unavailable; request cancelled')
        _cancel(pending)


def _show_worlds(pending):
    rows = []
    for key, name, count, label in pending.worlds:
        rows.append((label if label is not None else menu._raw(name),
                     menu._raw(lang.t('places count').format(count)), (WORLD, key)))
    rows.append((menu._raw(lang.t('open the map instead')), None, (_MAP_ROW, 0)))
    return _open_window(pending, 'travel destinations', 'choose a world', rows, _on_world)


def _on_world(pending, dialog):
    tag = _reply(pending, dialog)
    if tag is None:
        return
    kind, key = tag
    if kind == _MAP_ROW:
        _later(pending, _fallback)
    else:
        _later(pending, _show_places, key)


def _show_places(pending, world_key):
    places = [p for p in pending.places if p.world_key == world_key]
    if not places:
        return _show_worlds(pending)
    if pending.mode == VACATION:
        for place in places:
            place.price = _daily_price(place.zone_id, pending)
    rows = [(menu._raw(lang.t('back to worlds')), None, (_BACK_ROW, 0))]
    for entry in sorted(_buildings(places), key=lambda p: p.label().lower()):
        rows.append((menu._raw(entry.label()), _detail(entry), (PLACE, entry.zone_id)))
    rows.append((menu._raw(lang.t('open the map instead')), None, (_MAP_ROW, 0)))
    return _open_window(pending, 'travel destinations', 'choose a place', rows, _on_place)


def _on_place(pending, dialog):
    tag = _reply(pending, dialog)
    if tag is None:
        return
    kind, key = tag
    if kind == _BACK_ROW:
        _later(pending, _show_worlds)
    elif kind == _MAP_ROW:
        _later(pending, _fallback)
    elif _units_of(pending, key):
        _later(pending, _show_units, key)
    else:
        _choose(pending, _find(pending, key))


def _show_units(pending, master):
    units = _units_of(pending, master)
    if not units:
        return _show_worlds(pending)
    rows = [(menu._raw(lang.t('back to places')), None, (_BACK_ROW, units[0].world_key))]
    for place in sorted(units, key=lambda p: p.label().lower()):
        rows.append((menu._raw(place.label()), _detail(place), (UNIT, place.zone_id)))
    return _open_window(pending, 'travel destinations', 'choose a unit', rows, _on_unit)


def _on_unit(pending, dialog):
    tag = _reply(pending, dialog)
    if tag is None:
        return
    kind, key = tag
    if kind == _BACK_ROW:
        _later(pending, _show_places, key)
    else:
        _choose(pending, _find(pending, key))


def _choose(pending, place):
    if place is None:
        _cancel(pending)
        return
    if pending.mode == VACATION:
        if place.price is None:
            place.price = _daily_price(place.zone_id, pending)   # the client answer may have arrived
        if place.rental is True and place.price is not None:
            _later(pending, _show_stay, place.zone_id)
        else:
            # No usable price: the native panel decides, before anything is created.
            speech.log_line('travel: zone {} has no rental price; native map'.format(place.zone_id))
            _later(pending, _fallback)
        return
    if _needs_native_map(place):
        speech.log_line('travel: zone {} needs the native business selector'.format(place.zone_id))
        _say('map required here')
        _later(pending, _fallback)
        return
    _later(pending, _commit, place.zone_id)


def _show_stay(pending, zone_id):
    place = _find(pending, zone_id)
    if place is not None:
        place.price = _daily_price(zone_id, pending)   # the client may have answered since
    if place is None or place.price is None:
        return _fallback(pending)
    funds = _funds()
    rows = [(menu._raw(lang.t('back to places')), None, (_BACK_ROW, place.world_key))]
    for days in range(1, _MAX_STAY_DAYS + 1):
        cost = int(place.price * days)
        label = lang.t('stay one day').format(cost) if days == 1 else lang.t('stay days').format(days, cost)
        detail = menu._raw(lang.t('cannot afford')) if funds is not None and cost > funds else None
        rows.append((menu._raw(label), detail, (_STAY_ROW, (zone_id, days, cost))))
    return _open_window(pending, 'travel destinations', 'choose a stay', rows, _on_stay)


def _on_stay(pending, dialog):
    tag = _reply(pending, dialog)
    if tag is None:
        return
    kind, key = tag
    if kind == _BACK_ROW:
        _later(pending, _show_places, key)
    else:
        zone_id, days, quoted = key
        _later(pending, _rent_and_commit, zone_id, days, quoted)


def _grouped(info):
    """EA's manager drops every Sim whose household already has a member in
    a travel group, so the whole party is checked at household level."""
    household = getattr(info, 'household', None)
    check = getattr(household, 'any_member_in_travel_group', None)
    if check is not None and check():
        return True
    return bool(info.is_in_travel_group())


def _created_group(manager, party, zone_id):
    """The travel group the rental just created for this party, verified by
    membership and zone; None when it cannot be identified."""
    try:
        group = manager.get_travel_group_by_sim_info(party[0])
        if group is None:
            return None
        from world.street import get_vacation_zone_id
        expected = (zone_id, get_vacation_zone_id(zone_id))
        if getattr(group, 'zone_id', None) not in expected:
            return None
        for info in party:
            if info not in group:
                return None
        return group
    except Exception:
        return None


def _rollback_rental(manager, group, household, zone_id, cost):
    """Undo a rental whose dialog answer was refused: release the exact
    group created for this request and return the money to the household
    that paid. Anything unverifiable is reported, never guessed."""
    if group is None:
        speech.log_line('travel: rental of zone {} could not be identified for rollback'.format(zone_id))
        return False
    try:
        if not manager.destroy_travel_group_and_release_zone(group):
            speech.log_line('travel: rental of zone {} could not be released'.format(zone_id))
            return False
        if cost:
            from protocolbuffers import Consts_pb2
            household.funds.add(cost, Consts_pb2.FUNDS_MONEY_VACATION, count_as_earnings=False)
        speech.log_line('travel: rental of zone {} rolled back, {} returned'.format(zone_id, cost))
        return True
    except Exception as ex:
        speech.log_line('travel: rental rollback failed for zone {} ({!r})'.format(zone_id, ex))
        return False


def _rent_and_commit(pending, zone_id, days, quoted=None):
    """Validate the answer, rent the lot through EA's travel group manager
    exactly as the native rental panel does, then answer the dialog. Every
    check happens before the rental; a refused answer after the rental is
    rolled back, and there is never a native fallback after a rental."""
    global _pending
    if _pending is not pending or pending.rented:
        return False
    place = _find(pending, zone_id)
    dialog = pending.dialog
    if place is None or not _dialog_active(dialog):
        _say('action unavailable')
        return _cancel(pending)
    # The client's answer for this request may have arrived, changed or been
    # withdrawn since the stay was quoted: read it again before any sum.
    place.price = _daily_price(zone_id, pending)
    if days and place.price is None:
        speech.log_line('travel: zone {} has no usable price at commit; native map'.format(zone_id))
        _say('map required here')
        return _fallback(pending)
    cost = int(place.price * days) if days else 0
    if quoted is not None and cost != quoted:
        # The price moved after the stay was quoted: never charge an amount
        # the player has not heard; show the stay window again instead.
        speech.log_line('travel: quoted {} but current cost {} for zone {}; re-quoting'.format(quoted, cost, zone_id))
        _say('price changed')
        return _show_stay(pending, zone_id)
    party = pending.party
    try:
        import services
        if not party:
            raise ValueError('no travelling Sims')
        for info in party:
            if _grouped(info):
                speech.log_line('travel: household of {} already has a travel group; vacation refused'.format(getattr(info, 'sim_id', info)))
                _say('action unavailable')
                return _cancel(pending)
        funds = _funds()
        if cost and (funds is None or funds < cost):
            speech.log_line('travel: vacation cost {} exceeds funds {}; refused'.format(cost, funds))
            _say('cannot afford')
            return _cancel(pending)
        service = _service()
        if not service.dialog_pick_result(dialog.dialog_id, [zone_id]):
            speech.log_line('travel: zone {} refused by dialog {} before renting; request cancelled'.format(zone_id, dialog.dialog_id))
            _say('action unavailable')
            return _cancel(pending)
        import clock
        now = services.time_service().sim_now
        end = now + clock.interval_in_sim_days(days) if days else None
        manager = services.travel_group_manager()
        payer = services.active_household()
        created = manager.create_travel_group_and_rent_zone(
            sim_infos=list(party), zone_id=zone_id, played=True,
            create_timestamp=now, end_timestamp=end, cost=cost)
    except Exception as ex:
        speech.log_line('travel: vacation setup failed ({!r}); request cancelled'.format(ex))
        _say('action unavailable')
        return _cancel(pending)
    if not created:
        speech.log_line('travel: rental of zone {} refused by the travel group manager'.format(zone_id))
        _say('action unavailable')
        return _cancel(pending)
    pending.rented = True
    group = _created_group(manager, party, zone_id)
    speech.log_line('travel: zone {} rented for {} days at {} (group {})'.format(
        zone_id, days, cost, getattr(group, 'id', 'unverified')))
    _pending = None
    answered = False
    try:
        from ui.ui_dialog import ButtonType
        answered = _dialog_active(dialog) and bool(service.dialog_respond(dialog.dialog_id, ButtonType.DIALOG_RESPONSE_OK))
    except Exception as ex:
        speech.log_line('travel: answering dialog {} failed ({!r})'.format(dialog.dialog_id, ex))
        answered = False
    if answered:
        speech.log_line('travel: dialog {} answered with zone {}'.format(dialog.dialog_id, zone_id))
        return True
    speech.log_line('travel: dialog {} did not accept OK after the rental; rolling back'.format(dialog.dialog_id))
    _rollback_rental(manager, group, payer, zone_id, cost)
    _say('action unavailable')
    _cancel_dialog(dialog)
    return False


# ------------------------------------------------------- dialog outcomes

def _clear_picks(dialog):
    # EA's picker listener pushes continuations from the picked results
    # without checking the response, so a cancel must never carry picks.
    try:
        dialog.picked_results = []
    except Exception:
        pass


def _commit(pending, zone_id):
    """Answer EA's dialog with the chosen zone; EA does the rest."""
    global _pending
    if _pending is not pending:
        return False
    _pending = None
    dialog = pending.dialog
    if not _dialog_active(dialog):
        speech.log_line('travel: dialog {} no longer active, nothing sent'.format(dialog.dialog_id))
        _say('action unavailable')
        return False
    from ui.ui_dialog import ButtonType
    service = _service()
    if not service.dialog_pick_result(dialog.dialog_id, [zone_id]):
        speech.log_line('travel: zone {} refused by dialog {}; request cancelled'.format(zone_id, dialog.dialog_id))
        _say('action unavailable')
        _cancel_dialog(dialog)
        return False
    if service.dialog_respond(dialog.dialog_id, ButtonType.DIALOG_RESPONSE_OK):
        speech.log_line('travel: dialog {} answered with zone {}'.format(dialog.dialog_id, zone_id))
        return True
    speech.log_line('travel: dialog {} did not accept OK; request cancelled'.format(dialog.dialog_id))
    _say('action unavailable')
    _cancel_dialog(dialog)
    return False


def _cancel_dialog(dialog):
    """Cancel EA's dialog natively if it is still active, with no picks."""
    if not _dialog_active(dialog):
        return False
    _clear_picks(dialog)
    try:
        from ui.ui_dialog import ButtonType
        return bool(_service().dialog_respond(dialog.dialog_id, ButtonType.DIALOG_RESPONSE_CANCEL))
    except Exception as ex:
        speech.log_line('travel: cancelling dialog {} failed ({!r})'.format(dialog.dialog_id, ex))
        return False


def _cancel(pending):
    """The request ends without a destination: cancel EA's dialog natively."""
    global _pending, _window_id
    if _pending is not pending:
        return False
    _pending = None
    if _window_id is not None:
        menu._cancel_dialog(_window_id)
        _window_id = None
    speech.log_line('travel: dialog {} cancelled from the list'.format(pending.dialog.dialog_id))
    result = _cancel_dialog(pending.dialog)
    _say('travel cancelled')
    return result


def _fallback(pending):
    """Hand the same request to the native map, once."""
    global _pending
    if _pending is not pending or pending.fallback_used or pending.rented:
        return False
    _pending = None
    pending.fallback_used = True
    if not _dialog_active(pending.dialog):
        _say('action unavailable')
        return False
    speech.log_line('travel: dialog {} handed to the native map'.format(pending.dialog.dialog_id))
    _original_distribute(pending.dialog, pending.msg_type, pending.dialog_msg, **pending.kwargs)
    return True


def _distribute(dialog, msg_type, dialog_msg, **kwargs):
    global _pending, _last_rows, _price_generation
    mode = _request_mode(dialog)
    if not (enabled() and mode is not None and _zone_loaded()):
        return _original_distribute(dialog, msg_type, dialog_msg, **kwargs)
    if _pending is not None:
        # A second request while one list is open: the older one is
        # cancelled natively so no invisible interaction stays behind.
        speech.log_line('travel: dialog {} superseded by dialog {}'.format(
            _pending.dialog.dialog_id, dialog.dialog_id))
        _cancel(_pending)
    pending = _Pending(dialog, msg_type, dialog_msg, kwargs, mode)
    try:
        if mode == VACATION:
            pending.party = _party(dialog)
            if not pending.party:
                raise ValueError('no travelling Sims')
            import services
            services.travel_group_manager()
            if _funds() is None:
                raise ValueError('household funds unavailable')
        if mode == VACATION:
            _price_generation += 1
            pending.generation = _price_generation
        pending.places = _collect(dialog, vacation=(mode == VACATION), pending=pending)
        _last_rows = list(pending.places)
        counts = {}
        names = {}
        labels = {}
        for place in pending.places:
            counts[place.world_key] = counts.get(place.world_key, 0) + 1
            names[place.world_key] = place.world_name
            labels.setdefault(place.world_key, place.world_label)
        pending.worlds = sorted(((key, names[key], counts[key], labels[key]) for key in counts),
                                key=lambda item: item[1].lower())
        if not pending.worlds:
            raise ValueError('no destinations')
    except Exception as ex:
        speech.log_line('travel: list unavailable ({!r}), native map instead'.format(ex))
        return _original_distribute(dialog, msg_type, dialog_msg, **kwargs)
    _pending = pending
    if _show_worlds(pending):
        speech.log_line('travel: dialog {} listed as {} places in {} worlds'.format(
            dialog.dialog_id, len(pending.places), len(pending.worlds)))
    return None


# --------------------------------------------------------------- commands

def _hidden_flag(zone_id):
    try:
        import services
        proto = services.get_persistence_service().get_zone_proto_buff(zone_id)
        world_desc = services.get_world_description_id(proto.world_id)
        return services.get_hide_from_lot_picker(proto.lot_id, world_desc)
    except Exception as ex:
        return 'error {!r}'.format(ex)


@sims4.commands.Command('a11y.lotprice_enc', command_type=sims4.commands.CommandType.Live)
def a11y_lotprice_enc(payload: str = '', _connection=None):
    """Client bridge reply: <zone id>|<per-day price>|<generation> as the map
    computes it. Only the open vacation request that asked (same
    generation) may use it; anything else is dropped."""
    try:
        parts = str(payload).split('|')
        if len(parts) != 3:
            return False
        zone_id = int(parts[0])
        value = _positive(float(parts[1]))
        generation = int(parts[2])
    except (TypeError, ValueError):
        return False
    if value is not None and not 1 <= int(value) <= _MAX_DAILY_PRICE:
        value = None
    pending = _pending
    if pending is None or pending.mode != VACATION or generation != pending.generation:
        speech.log_line('travel: client price for zone {} ignored (generation {})'.format(zone_id, generation))
        return False
    if value is None:
        pending.prices.pop(zone_id, None)
        speech.log_line('travel: client price for zone {} unusable ({!r})'.format(zone_id, payload))
        return False
    pending.prices[zone_id] = int(value)
    return True


@sims4.commands.Command('a11y.lot_value', command_type=sims4.commands.CommandType.Live)
def a11y_lot_value(zone: str = '0', _connection=None):
    """Log every lot value source for a zone and the price the list would use."""
    output = sims4.commands.CheatOutput(_connection)
    try:
        zone_id = int(zone, 0)
    except (TypeError, ValueError):
        output('a11y lot value: usage a11y.lot_value <zone id>')
        return False
    line = 'travel lot value: zone {} sources {} price {}'.format(zone_id, _lot_values(zone_id), _daily_price(zone_id))
    speech.log_line(line)
    output(line)
    return True


@sims4.commands.Command('a11y.travel_probe', command_type=sims4.commands.CommandType.Live)
def a11y_travel_probe(_connection=None):
    """Log every row of the last travel request with its region facts."""
    output = sims4.commands.CheatOutput(_connection)
    if not _last_rows:
        output('a11y travel probe: no travel request listed yet')
        return True
    for place in _last_rows:
        line = 'travel probe: zone {} name {!r} world {!r} region {!r} facing {} hide {} venue {} residential {} household {!r} master {}'.format(
            place.zone_id, place.name, place.world_name, place.region, place.visible,
            _hidden_flag(place.zone_id), place.venue is not None, place.residential,
            place.household, place.master)
        speech.log_line(line)
    output('a11y travel probe: {} rows logged'.format(len(_last_rows)))
    return True


def _ui(message):
    """Encoded UI message on the existing A11y| channel (Flash side: Codex)."""
    try:
        import distributor.ops
        import distributor.system
        distributor.system.Distributor.instance().add_op_with_no_owner(
            distributor.ops.SendUIMessage(message))
        return True
    except Exception as ex:
        speech.log_line('travel: ui message failed ({!r})'.format(ex))
        return False


# Readiness lease for the keyboard M entry. Flash routes M to Python only
# while a recent lease says the pump is alive; the heartbeat runs from inside
# the pump drain, so a dead pump stops refreshing by construction. The lease
# value is a session epoch that only ever grows; Flash judges freshness by
# the age of the last heartbeat, not by the value.
_LEASE_INTERVAL = 2.0
_REQUEST_DEADLINE = 3.0
_REQUEST_HISTORY = 64
_epoch = 0
_lease_sent = 0.0
_lease_running = False
_lease_generation = 0  # bumped by every start and stop; retires queued heartbeats
_requests = []        # [(epoch, request id), state, ingress time], newest last


def announce_setting():
    return _ui('A11y|travellist|' + ('on' if settings.get('travel_list', True) else 'off'))


def apply_setting():
    """Settings changed (menu or a11y.reload): an open list is cancelled
    natively when it was switched off (the same contract as a reply that
    arrives after the switch), every UI copy hears the value at once and
    the M lease starts a new epoch."""
    if not enabled() and _pending is not None:
        _cancel(_pending)
    announce_setting()
    return start_lease()


def _publish_lease():
    if enabled() and _zone_loaded():
        return _ui('A11y|travelready|{}'.format(_epoch))
    # Flash drops its pending request on a zero lease, so nothing queued
    # here may survive to push later.
    _invalidate_requests('stale')
    return _ui('A11y|travelready|0')


def _refresh_lease(generation, force=False):
    """Pump-driven heartbeat: re-posts itself while the pump drains; sends at
    most one readiness message per interval. Exactly one chain is live: a
    callback queued before the latest start or stop ends without re-posting
    and leaves the live chain's state alone."""
    global _lease_sent, _lease_running
    if generation != _lease_generation:
        return False
    import time
    now = time.monotonic()
    if force or now - _lease_sent >= _LEASE_INTERVAL:
        _publish_lease()
        _lease_sent = now
    _lease_running = pump.post(_refresh_lease, generation)
    return _lease_running


def start_lease():
    """A new session epoch (zone load, pump start, setting change). Requests
    from an earlier epoch are refused from here on."""
    global _epoch, _lease_running, _lease_generation
    _epoch += 1
    _lease_generation += 1
    _invalidate_requests('stale')
    _lease_running = False
    return _refresh_lease(_lease_generation, force=True)


def stop_lease():
    """Pump stopped or zone unloading: publish no lease, keep the epoch."""
    global _lease_running, _lease_generation
    _lease_generation += 1
    _lease_running = False
    _invalidate_requests('stale')
    _ui('A11y|travelready|0')


def _entry(key):
    for entry in _requests:
        if entry[0] == key:
            return entry
    return None


def _invalidate_requests(reason):
    """Settle every queued request as refused and tell Flash, so nothing
    queued can push later and no pending request is left unanswered."""
    for entry in _requests:
        if entry[1] == 'pending':
            entry[1] = 'refused:' + reason
            epoch, request = entry[0]
            _ui('A11y|travelresult|{}|{}|refused|{}'.format(epoch, request, reason))


def _remember(key, state, when):
    _requests.append([key, state, when])
    del _requests[:-_REQUEST_HISTORY]


def _result(request, outcome, reason='', epoch=None):
    """Explicit reply Flash waits for; the epoch lets it ignore replies to a
    request from an earlier session. The settled outcome is kept on the
    request entry so a lost reply can be answered again."""
    epoch = _epoch if epoch is None else epoch
    text = 'A11y|travelresult|{}|{}|{}'.format(epoch, request, outcome)
    if reason:
        text += '|' + reason
    entry = _entry((epoch, request))
    if entry is not None and entry[1] == 'pending':
        entry[1] = outcome + (':' + reason if reason else '')
    _ui(text)
    return outcome == 'ok'


def _resend(entry):
    """Answer again from the settled state of an entry (lost reply, duplicate
    cancel, replayed request); nothing is queued or pushed."""
    epoch, request = entry[0]
    state = entry[1]
    if state == 'pending':
        return
    if state == 'cancelled':
        _ui('A11y|travelresult|{}|{}|refused|cancelled'.format(epoch, request))
        return
    outcome, _, reason = state.partition(':')
    text = 'A11y|travelresult|{}|{}|{}'.format(epoch, request, outcome)
    if reason:
        text += '|' + reason
    _ui(text)


def open_travel(request=0, epoch=0):
    """Keyboard entry: the tuned Sim menu Travel chain for the active Sim
    (companion picker, then this list). EA's own tests gate it: the save
    lock, the career and multi-unit event blacklists, venue rules. Runs on
    the pump; the request must still be current, uncancelled and younger
    than the deadline when it gets here. Every refusal is reported to Flash
    and spoken."""
    import services
    import time
    entry = _entry((epoch, request))
    if entry is None:
        return _result(request, 'refused', 'stale', epoch)
    if entry[1] != 'pending':
        return False                     # settled already (cancelled, stale or answered)
    if epoch != _epoch or time.monotonic() - entry[2] > _REQUEST_DEADLINE:
        speech.log_line('travel: keyboard entry request {} expired (epoch {} vs {})'.format(request, epoch, _epoch))
        return _result(request, 'refused', 'stale', epoch)
    if not enabled() or not _zone_loaded():
        _say('action unavailable')
        return _result(request, 'refused', 'refused', epoch)
    sim = services.get_active_sim()
    if sim is None:
        _say('load a household first')
        return _result(request, 'refused', 'no_sim', epoch)
    try:
        if sim.zone_id != services.current_zone_id():
            _say('sim unavailable')
            return _result(request, 'refused', 'away', epoch)
    except Exception:
        pass
    try:
        import sims4.resources
        from interactions.context import InteractionContext
        from interactions.priority import Priority
        affordance = services.get_instance_manager(sims4.resources.Types.INTERACTION).get(_TRAVEL_AFFORDANCE)
        if affordance is None:
            raise ValueError('travel affordance missing')
        client = services.client_manager().get_first_client()
        context = InteractionContext(sim, InteractionContext.SOURCE_PIE_MENU, Priority.High, client=client, pick=None)
        result = sim.push_super_affordance(affordance, sim, context)
        if not result:
            speech.log_line('travel: keyboard entry refused: {}'.format(result))
            _say('action unavailable')
            return _result(request, 'refused', 'refused', epoch)
        speech.log_line('travel: keyboard entry pushed for sim {} (request {})'.format(sim.sim_id, request))
        return _result(request, 'ok', '', epoch)
    except Exception as ex:
        speech.log_line('travel: keyboard entry failed: {!r}'.format(ex))
        _say('action unavailable')
        return _result(request, 'refused', 'error', epoch)


@sims4.commands.Command('a11y.travel', command_type=sims4.commands.CommandType.Live)
def a11y_travel(lease: str = '0', request: str = '0', _connection=None):
    """Flash posts a11y.travel <epoch> <request> after its native guards.
    Refusals here happen at ingress, before anything is queued."""
    import time
    try:
        epoch = int(lease)
        request_id = int(request)
    except (TypeError, ValueError):
        return _result(0, 'refused', 'error', 0)
    key = (epoch, request_id)
    entry = _entry(key)
    if entry is not None:
        if entry[1] == 'pending':
            return False                 # still queued: only its eventual outcome may answer
        _resend(entry)                   # cancelled tombstone or a lost reply
        return False
    if epoch != _epoch or not _lease_running:
        _remember(key, 'pending', time.monotonic())
        return _result(request_id, 'refused', 'stale', epoch)
    if not enabled() or not _zone_loaded():
        _remember(key, 'pending', time.monotonic())
        return _result(request_id, 'refused', 'refused', epoch)
    _remember(key, 'pending', time.monotonic())
    if not pump.post(open_travel, request_id, epoch):
        _say('action unavailable')
        return _result(request_id, 'refused', 'no_pump', epoch)
    return True


@sims4.commands.Command('a11y.travel_cancel', command_type=sims4.commands.CommandType.Live)
def a11y_travel_cancel(request: str = '0', lease: str = '', _connection=None):
    """Flash invalidates one exact request (another M, Escape, zone change,
    its bounded timeout). Applied at ingress, never queued, so it always
    beats a push still waiting on a stalled pump; the acknowledgement is
    sent at once and Flash keeps the request pending until it arrives."""
    try:
        request_id = int(request)
        epoch = int(lease) if lease else _epoch
    except (TypeError, ValueError):
        return False
    import time
    key = (epoch, request_id)
    entry = _entry(key)
    if entry is None:
        # Cancel arrived before the request: leave a tombstone so the late
        # request is refused, and acknowledge now.
        _remember(key, 'cancelled', time.monotonic())
        _ui('A11y|travelresult|{}|{}|refused|cancelled'.format(epoch, request_id))
        return True
    if entry[1] == 'pending':
        entry[1] = 'cancelled'
        speech.log_line('travel: keyboard entry request {} cancelled'.format(request_id))
        _ui('A11y|travelresult|{}|{}|refused|cancelled'.format(epoch, request_id))
        return True
    _resend(entry)                       # duplicate cancel or a finished request: answer again
    return True


def install():
    global _original_distribute
    if _original_distribute is not None:
        return True
    from ui.ui_dialog_picker import UiMapViewPicker
    _original_distribute = UiMapViewPicker.distribute_dialog

    def a11y_travel_distribute_dialog(self, msg_type, dialog_msg, **kwargs):
        return _distribute(self, msg_type, dialog_msg, **kwargs)

    UiMapViewPicker.distribute_dialog = a11y_travel_distribute_dialog
    return True


try:
    install()
except Exception as _install_ex:
    speech.log_line('travel: install failed: {!r}'.format(_install_ex))
