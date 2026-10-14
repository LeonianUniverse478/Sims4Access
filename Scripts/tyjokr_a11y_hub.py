"""Common accessibility actions in one native, keyboard-navigable picker.

All callbacks run on the simulation thread. Rows retain real Sim ids and are
revalidated on selection; closing a window never selects a default action.
"""
import sims4.commands
import tyjokr_a11y_lang as lang
import tyjokr_a11y_menu as menu
import tyjokr_a11y_pump as pump
import tyjokr_a11y_speech as speech
import tyjokr_a11y_contacts as contacts

_dialog_id = None

# Native UI messages verified in SimInfoTrayMain. They retain EA's enabled
# checks and panel setup. The hub is closed before one of these is sent.
PANELS = (
    ('needs', 'A11yNeeds'),
    ('mood and moodlets', 'A11yMood'),
    ('wants and fears', 'A11yWants'),
    ('aspirations', 'OpenSimInfoAspirationPanel'),
    ('skills', 'OpenSimInfoSkillPanel'),
    ('career', 'OpenSimInfoCareerPanel'),
    ('inventory', 'OpenSimInfoInventoryPanel'),
    ('relationships', 'OpenSimInfoRelationshipPanel'),
    ('simology', 'OpenSimInfoSummaryPanel'),
    ('social groups', 'OpenSimInfoClubPanel'),
    ('owned businesses', 'OpenHouseholdInfoVenuePanel'),
    ('calendar', 'ShowCalendar'),
)


def _say(term):
    speech.speak(lang.t(term), explicit=True)


def _name(info):
    return ' '.join(p for p in (getattr(info, 'first_name', ''),
                                getattr(info, 'last_name', '')) if p)


def _client():
    import services
    return services.client_manager().get_first_client()


def _ui(message):
    import distributor.ops
    import distributor.system
    distributor.system.Distributor.instance().add_op_with_no_owner(
        distributor.ops.SendUIMessage(message))


def _window(title, description, rows, localized_title=None):
    """Rows are (localized name, localized description, callback)."""
    global _dialog_id
    import services
    from ui.ui_dialog_picker import ObjectPickerRow
    menu._cancel_dialog(_dialog_id)
    _dialog_id = None
    dialog = menu._picker(lang.t(title), lang.t(description), localized_title=localized_title)
    if dialog is None:
        _say('load a household first')
        return False
    # Text-only item rows drew a broken-image placeholder in every row
    # (reported 2026-09-15). Object rows with the active Sim's own thumbnail
    # ask the client for a real icon, like the scanner window does.
    icon_info = None
    try:
        from distributor.shared_messages import IconInfoData
        sim = services.get_active_sim()
        if sim is not None:
            icon_info = IconInfoData(obj_instance=sim)
    except Exception:
        icon_info = None
    callbacks = {}
    for index, (name, detail, callback) in enumerate(rows):
        callbacks[index] = callback
        dialog.add_row(ObjectPickerRow(option_id=index, name=name,
                                         row_description=detail, row_tooltip=None,
                                         icon=None, icon_info=icon_info, tag=index,
                                         is_selected=False))

    def selected(reply):
        global _dialog_id
        if reply.dialog_id != _dialog_id:
            return
        _dialog_id = None
        if not reply.accepted:
            return
        tags = list(reply.get_result_tags())
        if len(tags) != 1 or tags[0] not in callbacks:
            return
        # Defer until EA finishes dismissing this dialog. Never fall back to
        # executing on an arbitrary caller thread if the pump has stopped.
        if not pump.post(callbacks[tags[0]]):
            _say('action unavailable')

    dialog.add_listener(selected)
    _dialog_id = dialog.dialog_id
    # The console Enter that opened this menu belongs to the console.
    # Retire queued activations before the new picker can receive them.
    import tyjokr_a11y_keys as keys
    keys.fence_opening_input()
    dialog.show_dialog()
    return True


def select_sim(sim_id):
    import services
    client = _client()
    info = services.sim_info_manager().get(sim_id)
    if client is None or info is None or info not in client.selectable_sims:
        _say('sim unavailable')
        return False
    if client.active_sim_info is not info and not client.set_active_sim_by_id(sim_id):
        _say('sim unavailable')
        return False
    speech.speak(_name(info), explicit=True)
    return True


def household():
    client = _client()
    if client is None:
        _say('load a household first')
        return False
    rows = []
    for info in client.selectable_sims:
        sim_id = info.sim_id
        detail = 'active sim' if info is client.active_sim_info else 'select this sim'
        rows.append((menu._raw(_name(info)), menu._raw(lang.t(detail)),
                     lambda ident=sim_id: select_sim(ident)))
    if not rows:
        _say('load a household first')
        return False
    return _window('household sims', 'choose a sim', rows)


def funds_text(household=None):
    """'Household funds: 12,345 simoleons' for the active household."""
    if household is None:
        import services
        household = services.active_household()
    if household is None:
        return ''
    return '{}: {:,} {}'.format(lang.t('household funds'),
                                household.funds.money, lang.t('simoleons'))


def funds():
    import services
    household = services.active_household()
    if household is None:
        _say('load a household first')
        return False
    speech.speak(funds_text(household), explicit=True)
    return True


def read_clock():
    """The client's clock text, the same request as Control Alt C. The hub
    picker has already closed when a row callback runs."""
    import tyjokr_a11y_keys as keys
    return keys.request_clock()


def scanner_help():
    # Retain the callback name for callers of older hub versions.
    import tyjokr_a11y_shortcuts as shortcuts
    return shortcuts.speak()


def self_interactions():
    import services
    import tyjokr_a11y_scanner as scanner
    sim = services.get_active_sim()
    if sim is None or not scanner.enabled() or not scanner._scan():
        _say('action unavailable')
        return False
    if not scanner.select_item(scanner.SIMS, sim.id):
        _say('action unavailable')
        return False
    scanner._do_open()
    return True


def _queue_entries(sim):
    """The icons of EA's interaction queue, from the same UIManager records
    the client draws: running (super, group and posture) first, then queued
    in order. Each is (info, interaction or None, state)."""
    from protocolbuffers import Sims_pb2
    infos = [info for info in sim.ui_manager.get_interactions_gen() if not info.canceled]
    running = [info for info in infos if info.ui_state != Sims_pb2.IQ_QUEUED]
    queued = [info for info in infos if info.ui_state == Sims_pb2.IQ_QUEUED]
    entries = []
    for state, group in (('running', running), ('queued', queued)):
        for info in group:
            entries.append((info, _queue_interaction(sim, info.interaction_id), state))
    return entries


def _queue_interaction(sim, interaction_id):
    # interactions.cancel_si looks an id up the same two ways.
    interaction = sim.find_interaction_by_id(interaction_id)
    return interaction if interaction is not None else sim.find_continuation_by_id(interaction_id)


def _queue_detail(info, interaction, state, position, total):
    parts = []
    if info.is_visual_type_posture():
        parts.append(lang.t('queue posture'))
    elif state == 'running':
        parts.append(lang.t('queue running'))
    else:
        parts.append(lang.t('queue waiting').format(position, total))
    if interaction is not None and interaction.is_autonomous:
        parts.append(lang.t('queue autonomous'))
    elif interaction is not None and interaction.is_user_directed:
        parts.append(lang.t('queue chosen by you'))
    parts.append(lang.t('queue enter cancels') if info.user_cancelable else lang.t('queue cannot cancel'))
    return '. '.join(parts)


def action_queue():
    """Control Alt Q and the accessibility menu row: the active Sim's action
    queue as a native picker. Enter on a row cancels that action the way
    clicking its queue icon does."""
    import services
    sim = services.get_active_sim()
    if sim is None:
        _say('load a household first')
        return False
    try:
        entries = _queue_entries(sim)
    except Exception as ex:
        speech.log_line('hub: queue read failed: {!r}'.format(ex))
        _say('action unavailable')
        return False
    sim_id = sim.id
    rows = []
    cancelable = [info.interaction_id for info, _i, _s in entries if info.user_cancelable]
    if len(cancelable) > 1:
        rows.append((menu._raw(lang.t('cancel all actions')), None,
                     lambda ids=tuple(cancelable): cancel_actions(sim_id, ids)))
    queued_total = sum(1 for _info, _i, state in entries if state == 'queued')
    position = 0
    for info, interaction, state in entries:
        if state == 'queued':
            position += 1
        name = info.display_name
        if name is None and interaction is not None:
            name = interaction.get_name()
        if name is None:
            continue
        detail = menu._raw(_queue_detail(info, interaction, state, position, queued_total))
        rows.append((name, detail, lambda value=info.interaction_id: cancel_actions(sim_id, (value,))))
    if not rows:
        rows.append((menu._raw(lang.t('queue empty')), None, open_hub))
    return _window('action queue', 'action queue instructions', rows)


def cancel_actions(sim_id, interaction_ids):
    """Cancel on the simulation thread after the picker closes. Everything is
    looked up again: the Sim or the action may have changed meanwhile."""
    import services
    sim = services.get_active_sim()
    if sim is None or sim.id != sim_id:
        _say('sim unavailable')
        return False
    canceled = refused = 0
    for interaction_id in interaction_ids:
        interaction = _queue_interaction(sim, interaction_id)
        if interaction is None:
            continue
        if interaction.user_cancelable and interaction.cancel_user(
                cancel_reason_msg='TS4 Access action queue'):
            canceled += 1
        else:
            refused += 1
    if canceled:
        _say('action canceled')
    elif refused:
        _say('queue cannot cancel')
    else:
        _say('action already finished')
    return canceled > 0


# Enter on an item of the active Sim's inventory (TooltipManager
# A11yInventoryMenu posts a11y.invitem_enc) opens this item menu instead of
# EA's pie menu. Item actions asks Flash to replay the original click.
# Selling follows EA's own paths (game 1.128.90): the inventory panel's
# sell request (inventory.sim_inventory_sell_multiple, items with id and
# count) for one or all, and the native sell picker for an amount.
_sell_factory = None


def _currency():
    """GameplayStateData.CurrentRegionCurrencyBucksType on the server side:
    the region's bucks type; INVALID (0) means simoleons."""
    import services
    region = services.current_region()
    return int(getattr(region, 'region_currency_bucks_type', 0) or 0) if region is not None else 0


def _price_text(amount, currency):
    if currency == 0:
        unit = lang.t('simoleons')
    else:
        try:
            from bucks.bucks_enums import BucksType
            name = BucksType(currency).name.lower()
        except Exception:
            name = ''
        unit = lang.t('galactic credits') if 'galactic' in name else ''
    return '{:,} {}'.format(amount, unit).strip()


def _inventory_item(obj_id):
    """(active Sim, object) when the object is in that Sim's own inventory."""
    import services
    sim = services.get_active_sim()
    obj = services.inventory_manager().get(obj_id)
    inventory = sim.inventory_component if sim is not None else None
    if inventory is None or obj is None or obj not in inventory:
        return sim, None
    return sim, obj


def _sellable(obj):
    # The panel's two gates: sim_inventory_sell_multiple skips
    # non_deletable_by_user, and the item info carries
    # is_sell_disabled_from_component (InventoryStorage).
    if getattr(obj, 'non_deletable_by_user', False):
        return False
    check = getattr(obj, 'is_sell_disabled_from_component', None)
    return not (check is not None and check())


def _sell_price(sim, obj, count):
    # sim_inventory_sell_multiple: current_value * count * sell modifier, rounded.
    return int(round(obj.current_value * count * sim.sim_info.get_item_sell_price_modifier(obj)))


def inventory_item_menu(obj_id):
    sim, obj = _inventory_item(obj_id)
    if obj is None:
        # Not the active Sim's own inventory: EA's menu as usual.
        _ui('A11yInvItemActions')
        return False
    from sims4.localization import LocalizationHelperTuning
    sim_id = sim.id
    rows = [(menu._raw(lang.t('item actions')), None, lambda: _ui('A11yInvItemActions'))]
    if _sellable(obj):
        count = obj.stack_count()
        currency = _currency()
        one = _price_text(_sell_price(sim, obj, 1), currency)
        if count <= 1:
            rows.append((menu._raw(lang.t('sell for').format(one)), None,
                         lambda: sell_inventory_item(sim_id, obj_id, 1)))
        else:
            every = _price_text(_sell_price(sim, obj, count), currency)
            rows.append((menu._raw(lang.t('sell one for').format(one)), None,
                         lambda: sell_inventory_item(sim_id, obj_id, 1)))
            rows.append((menu._raw(lang.t('sell all for').format(count, every)), None,
                         lambda: confirm_sell_all(sim_id, obj_id)))
            rows.append((menu._raw(lang.t('choose how many to sell')), None,
                         lambda: sell_window(sim_id, obj_id)))
    else:
        rows.append((menu._raw(lang.t('cannot be sold')), None, lambda: _say('cannot be sold')))
    return _window('inventory item', 'inventory item instructions', rows,
                   localized_title=LocalizationHelperTuning.get_object_name(obj))


def _checked_item(sim_id, obj_id):
    """Look everything up again on the simulation thread after a menu."""
    sim, obj = _inventory_item(obj_id)
    if sim is None or sim.id != sim_id:
        _say('sim unavailable')
        return None, None
    if obj is None:
        _say('item no longer in inventory')
        return None, None
    if not _sellable(obj):
        _say('cannot be sold')
        return None, None
    return sim, obj


def confirm_sell_all(sim_id, obj_id):
    sim, obj = _checked_item(sim_id, obj_id)
    if obj is None:
        return False
    from sims4.localization import LocalizationHelperTuning
    count = obj.stack_count()
    every = _price_text(_sell_price(sim, obj, count), _currency())
    return _window('inventory item', 'sell all instructions', [
        (menu._raw(lang.t('yes sell all').format(count, every)), None,
         lambda: sell_inventory_item(sim_id, obj_id, count)),
        (menu._raw(lang.t('no keep them')), None, lambda: _say('nothing sold'))],
        localized_title=LocalizationHelperTuning.get_object_name(obj))


def sell_inventory_item(sim_id, obj_id, count):
    """EA's inventory panel sell request for count items of one object."""
    import services
    sim, obj = _checked_item(sim_id, obj_id)
    if obj is None:
        return False
    count = min(int(count), obj.stack_count())
    if count < 1:
        _say('item no longer in inventory')
        return False
    currency = _currency()
    amount = _sell_price(sim, obj, count)
    household = services.active_household()
    before = household.funds.money if household is not None and currency == 0 else None
    from google.protobuf import text_format
    from protocolbuffers import UI_pb2
    from server_commands import inventory_commands
    request = UI_pb2.InventorySellRequest()
    request.sim_id = sim.id
    request.currency_type = currency
    item = request.items.add()
    item.id = obj.id
    item.count = count
    client = services.client_manager().get_first_client()
    inventory_commands.sim_inventory_sell_multiple(text_format.MessageToString(request),
                                                   _connection=client.id if client is not None else None)
    if before is not None and household.funds.money <= before:
        _say('sale failed')
        return False
    speech.speak(lang.t('sold for').format(_price_text(amount, currency)), explicit=True)
    return True


def sell_window(sim_id, obj_id):
    """EA's native sell picker (quantity, price and total) for one item.
    Set up as SellPickerInteraction._setup_dialog does; the client's Sell
    runs inventory.sell_picker_response_by_ids, which pays and stores the
    amounts on the dialog; this listener then removes what was sold, as
    SellPickerInteraction._remove_sold_objects_from_inventory does."""
    global _sell_factory
    import services
    import tyjokr_a11y_keys as keys
    sim, obj = _checked_item(sim_id, obj_id)
    if obj is None:
        return False
    from sims4.localization import LocalizationHelperTuning
    from ui.ui_dialog_picker import UiSellPicker, PurchasePickerRow
    if _sell_factory is None:
        _sell_factory = UiSellPicker.TunableFactory()
    name = LocalizationHelperTuning.get_object_name(obj)
    dialog = _sell_factory.default(sim, title=lambda *args, **kwargs: name,
                                   text=lambda *args, **kwargs: menu._raw(lang.t('sell window instructions')))
    dialog.inventory_object_id = sim.id
    dialog.use_dialog_pick_response = False
    dialog.add_row(PurchasePickerRow(def_id=obj.definition.id, is_enable=True,
                                     num_available=obj.stack_count(),
                                     tags=obj.definition.build_buy_tags,
                                     custom_price=_sell_price(sim, obj, 1), objects={obj}))
    currency = _currency()

    def sold(reply):
        if not reply.accepted:
            return
        triples = reply.ids_and_amounts_and_price
        source = reply.source_inventory
        if not triples or source is None:
            speech.log_line('hub: sell window reply without amounts')
            return
        manager = services.inventory_manager()
        removed = paid = 0
        for item_id, amount, price in zip(triples[::3], triples[1::3], triples[2::3]):
            item = manager.get(item_id)
            if item is None:
                continue
            count = min(amount, item.stack_count())
            if count > 0 and source.try_destroy_object(item, count):
                removed += count
                paid += price * count
        if removed:
            speech.speak(lang.t('sold for').format(_price_text(paid, currency)), explicit=True)

    dialog.add_listener(sold)
    keys.fence_opening_input()
    dialog.show_dialog()
    return True


# Events (Ctrl+Alt+V and the accessibility menu row): the user-facing
# situations the game shows (parties, dates, holidays, career events), with
# EA's own ending and leaving paths (game 1.128.90):
#   * SituationManager.get_user_facing_situations_gen() lists them;
#   * ending is what situations.pre_destroy_user_facing_situation and
#     situations.destroy_user_facing_situation do:
#     pre_destroy_situation_by_id(id), then destroy_situation_by_id(id);
#   * sending a guest home is SituationManager.make_sim_leave(sim), the
#     game's normal leave (it falls back to make_sim_leave_now_must_run
#     itself when the leave situation is missing).
# Household Sims are never sent away. Everything is looked up again when a
# row is chosen: the event may have ended meanwhile.

def _situation_manager():
    import services
    return services.get_zone_situation_manager()


def _events():
    manager = _situation_manager()
    return list(manager.get_user_facing_situations_gen()) if manager is not None else []


def _guests(situation):
    """Sims in the event who are not in the active household."""
    import services
    household = services.active_household()
    home = getattr(household, 'id', None)
    guests = []
    for sim in list(situation.all_sims_in_situation_gen()):
        try:
            info = sim.sim_info
            if getattr(info, 'household_id', None) == home or getattr(info, 'is_selectable', False):
                continue
            guests.append(sim)
        except Exception:
            continue
    return guests


def _event_detail(situation):
    parts = [lang.t('event guests').format(len(_guests(situation)))]
    try:
        minutes = int(situation._get_remaining_time_in_minutes())
        if minutes > 0:
            parts.append(lang.t('event minutes left').format(minutes))
    except Exception:
        pass
    return '. '.join(parts)


def events_window():
    """The running events; Enter on one opens what can be done with it."""
    try:
        events = _events()
    except Exception as ex:
        speech.log_line('hub: events unavailable ({!r})'.format(ex))
        _say('action unavailable')
        return False
    if not events:
        _say('no events')
        return False
    rows = []
    for situation in events:
        name = getattr(situation, 'display_name', None)
        if name is None:
            continue
        rows.append((name, menu._raw(_event_detail(situation)),
                     lambda value=situation.id: event_actions(value)))
    if not rows:
        _say('no events')
        return False
    return _window('events', 'events instructions', rows)


def _event(situation_id):
    manager = _situation_manager()
    situation = manager.get(situation_id) if manager is not None else None
    if situation is None or not getattr(situation, 'is_user_facing', False):
        _say('event already over')
        return None, None
    return manager, situation


def event_actions(situation_id):
    manager, situation = _event(situation_id)
    if situation is None:
        return False
    rows = [(menu._raw(lang.t('send guests home and end event')), None,
             lambda: end_event(situation_id, send_home=True, end=True)),
            (menu._raw(lang.t('end event')), None,
             lambda: end_event(situation_id, send_home=False, end=True)),
            (menu._raw(lang.t('send guests home')), None,
             lambda: end_event(situation_id, send_home=True, end=False))]
    return _window('events', 'event actions instructions', rows,
                   localized_title=getattr(situation, 'display_name', None))


def end_event(situation_id, send_home, end):
    manager, situation = _event(situation_id)
    if situation is None:
        return False
    sent = 0
    if send_home:
        for sim in _guests(situation):
            try:
                manager.make_sim_leave(sim)
                sent += 1
            except Exception as ex:
                speech.log_line('hub: could not send a guest home ({!r})'.format(ex))
    ended = False
    if end:
        try:
            manager.pre_destroy_situation_by_id(situation_id)
            manager.destroy_situation_by_id(situation_id)
            ended = True
        except Exception as ex:
            speech.log_line('hub: could not end the event ({!r})'.format(ex))
    parts = []
    if send_home:
        parts.append(lang.t('guests sent home').format(sent))
    if end:
        parts.append(lang.t('event ended') if ended else lang.t('event not ended'))
    speech.speak(' '.join(parts), explicit=True)
    return ended or sent > 0


@sims4.commands.Command('a11y.events', command_type=sims4.commands.CommandType.Live)
def a11y_events(_connection=None):
    return events_window()


@sims4.commands.Command('a11y.invitem_enc', command_type=sims4.commands.CommandType.Live)
def a11y_invitem_enc(text: str = '', _connection=None):
    try:
        obj_id = int(text.strip())
    except ValueError:
        return False
    return inventory_item_menu(obj_id)


# Build cursor actions reachable without holding a chord. This window is a
# modal, so opening it retires the native cursor; a 'menu:' row asks the
# client to bring the cursor back where it was and perform that one action
# after the window has closed, under the cursor's own guards. On, off, undo,
# redo and the grid aim are the ordinary requests. Native feedback is what
# the player hears.
BUILD_ACTIONS = (
    ('build cursor on', 'on'), ('build cursor off', 'off'),
    ('move left', 'menu:left'), ('move right', 'menu:right'),
    ('move up', 'menu:up'), ('move down', 'menu:down'),
    ('fine step', 'menu:fine'), ('coarse step', 'menu:coarse'),
    ('center cursor', 'menu:center'), ('aim at grid point', 'grid'),
    ('select or place', 'menu:click'), ('cancel tool', 'menu:cancel'),
    ('rotate left', 'menu:rotateleft'), ('rotate right', 'menu:rotateright'),
    ('undo', 'undo'), ('redo', 'redo'),
    ('cursor status', 'menu:status'),
)


def _build_action(action):
    import tyjokr_a11y_build as build
    if action.startswith('menu:'):
        return build.request_menu(action[5:])
    return build.request(action)


def build_actions():
    import tyjokr_a11y_build as build
    if not build.controls_enabled():
        return build.refuse_disabled()
    if build._zone() is None:
        build._say('Enter Build mode first.', 'Najpierw włącz tryb budowania.')
        return False
    rows = []
    for label, action in BUILD_ACTIONS:
        rows.append((menu._raw(lang.t(label)), None,
                     lambda value=action: _build_action(value)))
    return _window('build actions', 'build actions instructions', rows)


def open_hub():
    import tyjokr_a11y_phone as phone
    import tyjokr_a11y_build as build
    import tyjokr_a11y_grid as grid
    rows = []
    for label, message in PANELS:
        rows.append((menu._raw(lang.t(label)), None,
                     lambda value=message: _ui(value)))
    # Build controls off: no dead rows; the settings menu row turns them on.
    # One row: object placement in Build mode, the read-only grid in Live.
    # The pixel cursor and its actions window stay on a11y.build/a11y.buildmenu.
    import tyjokr_a11y_place as place
    if not build.controls_enabled():
        build_rows = ()
    elif place.in_build_mode():
        build_rows = (('build placement', grid.placement_toggle),)
    else:
        build_rows = (('read-only lot grid', grid.toggle),)
    # Pack Simology readers: only for the packs this game has installed.
    import tyjokr_a11y_simology as simology
    pack_rows = ((('milestones', simology.milestones_window),) if simology.milestones_available() else ()) + \
                ((('character values', simology.values_window),) if simology.values_available() else ())
    import tyjokr_a11y_business as business
    for label, callback in (
            (('action queue', action_queue), ('events', events_window), ('businesses', business.businesses_window)) +
            pack_rows +
            (('self interactions', self_interactions),
             ('household sims', household), ('household funds', funds),
             ('day and time', read_clock),
             ('known contacts', contacts.open_contacts)) + build_rows +
            (('waiting call or text', phone.open_waiting),) +
            ((('phone', phone.open_list),) if phone.simplified() else ()) +
            (('keyboard shortcuts', scanner_help),
             ('settings menu', menu._show_settings_window))):
        rows.append((menu._raw(lang.t(label)), None, callback))
    return _window('accessibility menu', 'accessibility menu instructions', rows)


@sims4.commands.Command('a11y.hub', command_type=sims4.commands.CommandType.Live)
def a11y_hub(_connection=None):
    return open_hub()


@sims4.commands.Command('a11y.buildmenu', command_type=sims4.commands.CommandType.Live)
def a11y_buildmenu(_connection=None):
    return build_actions()


@sims4.commands.Command('a11y.household', command_type=sims4.commands.CommandType.Live)
def a11y_household(_connection=None):
    return household()


@sims4.commands.Command('a11y.funds', command_type=sims4.commands.CommandType.Live)
def a11y_funds(_connection=None):
    return funds()
