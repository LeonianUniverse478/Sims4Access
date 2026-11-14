"""Transfer the selected scanner object after two matching requests."""
import time

import tyjokr_a11y_keys as keys
import tyjokr_a11y_lang as lang
import tyjokr_a11y_speech as speech

_pending = None
_generation = 0


def cancel():
    global _pending, _generation
    _pending = None
    _generation += 1


def enqueue(destination):
    import tyjokr_a11y_pump as pump
    if not pump.post(_transfer, destination, keys._input_epoch, _generation):
        cancel()
        speech.log_line('scanner inventory transfer: simulation pump inactive')
        speech.speak(lang.t('store unavailable'))


def _household_refusal(obj, household, zone):
    import build_buy
    import tyjokr_a11y_place as place
    if household.home_zone_id != zone:
        return 'store home only'
    if place.sell_refusal(obj) or obj.get_household_owner_id() != household.id:
        return 'store protected'
    flags = build_buy.get_object_placement_flags(obj.definition.id)
    if (build_buy.PlacementFlags.NON_INVENTORYABLE in flags or obj.stack_count() != 1
            or getattr(obj, 'consumable_component', None) is not None):
        return 'store protected'
    if not build_buy.is_household_inventory_available(household.id):
        return 'store unavailable'


def _sim_refusal(obj, sim):
    from sims.ghost import Ghost
    drag = getattr(obj, 'live_drag_component', None)
    if not (drag and drag.can_live_drag) and not obj.has_tag(Ghost.URNSTONE_TAG):
        return 'store protected'
    if not obj.inventoryitem_component or sim.inventory_component is None or not sim.inventory_component.can_add(obj):
        return 'store unavailable'


def _transfer(destination, epoch, generation):
    global _pending
    import build_buy
    import services
    import tyjokr_a11y_scanner as scanner
    if generation != _generation or epoch != keys._input_epoch:
        return
    if not (keys._scanner_live and keys._scanner_routing() and keys._in_live()) or keys.blocking_active():
        cancel()
        return
    try:
        entry = scanner._current() if scanner._tree_level == 'items' and not scanner._menu_open else None
        obj = services.object_manager().get(entry.obj_id) if entry and not entry.is_sim else None
        household = services.active_household()
        sim = services.get_active_sim()
        zone = services.current_zone_id()
        if obj is None or household is None or sim is None:
            cancel()
            scanner._speak_parts([lang.t('store select object')])
            return
        item = getattr(obj, 'inventoryitem_component', None)
        family = destination == 'household'
        if (getattr(obj, 'is_part', False) or obj.self_or_part_in_use or getattr(obj, 'interaction_refs', None)
                or getattr(item, 'always_destroy_on_inventory_transfer', False)):
            refusal = 'store protected'
        else:
            refusal = _household_refusal(obj, household, zone) if family else _sim_refusal(obj, sim)
        if refusal:
            cancel()
            scanner._speak_parts([lang.t(refusal)])
            return
        object_id = obj.id
        name = scanner._name_part(entry)
        if not name:
            cancel()
            scanner._speak_parts([lang.t('store select object')])
            return
        token = (epoch, zone, sim.id, household.id, destination, object_id)
        now = time.monotonic()
        if _pending is None or _pending[0] != token or now > _pending[1]:
            _pending = (token, now + 15.0)
            if family:
                prompt = lang.t('store confirm household')
            else:
                who = ' '.join(p for p in (sim.sim_info.first_name, sim.sim_info.last_name) if p)
                prompt = lang.t('store confirm sim').format(who)
            scanner._speak_parts([name, '. ', prompt])
            return
        _pending = None
        if family:
            moved = (build_buy.move_object_to_household_inventory(obj, failure_flags=0)
                     and build_buy.object_exists_in_household_inventory(object_id, household.id))
        else:
            inventory = sim.inventory_component
            moved = inventory.player_try_add_object(obj) and obj in inventory
        scanner._speak_parts([name, '. ', lang.t('store moved' if moved else 'store unverified')])
        if moved:
            scanner._scan(preserve=True)
    except Exception as error:
        cancel()
        speech.log_line('scanner inventory transfer: {!r}'.format(error))
        scanner._speak_parts([lang.t('store unverified')])
