"""Buy and place the Build catalog's selected object at the lot grid cursor.

Ported from glaroc's a11yscan build 3 placement engine (a11yscan_build.py,
2026-09-07), with every EA call checked against the 1.128.90 decompile:

  * the object comes from EA's own catalog: the client reports the product it
    selected (a11y.buildproduct), and only that definition is ever created;
  * placement.find_good_location picks the spot with the object's footprint
    and the build/buy tests, within SEARCH_RADIUS of the cursor; when that
    finds nothing the placement is refused (glaroc's untested retry is gone);
  * nothing is created until the client confirms it put down EA's held
    product (A11y|buildhand|drop|id, answered by a11y.buildhand id|ok);
  * objects that belong on a surface go into a free slot the game validates
    for that object (RuntimeSlot.is_valid_for_placement(obj=...));
  * build_buy.add_object_to_buildbuy_system takes the object id;
  * money moves through household funds with FUNDS_OBJECT_BUY and
    FUNDS_OBJECT_SELL, checked against the balance; a failed payment
    removes the object again, so nothing is ever free;
  * every placement can be undone with a refund, and selling takes two
    presses.

Simulation thread only (the key poller reaches it through the pump).
"""
import math
import time

import sims4.commands
import tyjokr_a11y_lang as lang
import tyjokr_a11y_speech as speech

SEARCH_RADIUS = 2.5          # metres: "place here" means near here
SLOT_SEARCH = 1.2            # metres around the cursor to look for surfaces
REPEAT_GUARD_SECONDS = 4.0   # a second Enter on the same tile must be meant
SELL_CONFIRM_SECONDS = 6.0
ACK_SECONDS = 1.5            # the client must put down EA's held product first
MAX_HISTORY = 20

# build_buy.PlacementFlags (build_buy.py): what an object needs under it.
FLAG_WALL = 1 | 2            # CENTER_ON_WALL | EDGE_AGAINST_WALL = REQUIRES_WALL
FLAG_CEILING = 8
FLAG_FENCE = 128
FLAG_SLOT = 1024
FLAG_TERRAIN = 65536
FLAG_WATER = 2097152

# Surfaces ranked as in glaroc's build: a computer on a desk works, the same
# computer on a decorative island slot has no usable posture.
SURFACE_RANK = ((('desk',), 0), (('table',), 1), (('counter', 'island'), 3),
                (('shelf', 'bookcase', 'dresser', 'endtable', 'nightstand'), 4),
                (('lamp', 'light'), 9))

_product = None              # {'id', 'name', 'zone'} from the native catalog
_history = []                # [(obj_id, charged, name, household id, zone id)]
_last = {'obj_id': None, 'position': None, 'household': None, 'zone': None}
_repeat = [(), 0.0]          # (aimed and landed tile keys, time) of the last placement
_sell = [None, 0.0]          # (obj_id, time) awaiting confirmation
_pending = {'serial': 0, 'at': 0.0, 'args': None, 'zone': None, 'product': None}
_owed = {}                   # household id -> refunds that failed and are still due


def _text(en, pl):
    return pl if lang._detect_lang() == 'pl' else en


def _say(parts):
    import tyjokr_a11y_scanner as scanner
    scanner._speak_parts(parts)


def _say_text(en, pl):
    speech.speak(_text(en, pl), explicit=True)


def _zone_id():
    try:
        import services
        return services.current_zone_id()
    except Exception:
        return None


def in_build_mode():
    try:
        import services
        zone = services.current_zone()
        return zone is not None and bool(zone.is_in_build_buy)
    except Exception:
        return False


# ---------------------------------------------------------------- the product

def set_product(instance_text, name):
    """The native catalog selected (or dropped) a product."""
    global _product
    text = str(instance_text or '').strip()
    if not text.isdigit() or int(text) == 0:
        _product = None
        _pending['args'] = None
        return True
    def_id = int(text)
    try:
        import services
        definition = services.definition_manager().get(def_id, get_fallback_definition_id=False)
    except Exception as ex:
        speech.log_line('place: definition lookup failed for {}: {!r}'.format(def_id, ex))
        definition = None
    if definition is None or getattr(definition, 'id', None) != def_id:
        speech.log_line('place: catalog product {} is not an object definition'.format(def_id))
        _product = None
        return False
    _product = {'id': def_id, 'name': str(name or '').strip()[:200], 'zone': _zone_id()}
    _pending['args'] = None
    speech.log_line('place: product {} {!r}'.format(def_id, _product['name']))
    return True


def product():
    """The remembered product, if it still belongs to this zone."""
    global _product
    if _product is not None and _product['zone'] != _zone_id():
        _product = None
    return _product


def forget():
    global _product
    _product = None
    _repeat[0] = ()
    _sell[0] = None
    _pending['args'] = None


def _product_name():
    item = product()
    if item and item['name']:
        return item['name']
    return _text('the object', 'obiekt')


# ------------------------------------------------------------------- the funds

def _household():
    try:
        import services
        return services.active_household()
    except Exception:
        return None


def _household_id():
    household = _household()
    return getattr(household, 'id', None) if household is not None else None


def funds():
    household = _household()
    try:
        return int(household.funds.money)
    except Exception:
        return None


def _reason(name):
    try:
        from protocolbuffers import Consts_pb2
        value = getattr(Consts_pb2, name, None)
        return None if value is None else int(value)
    except Exception as ex:
        speech.log_line('place: no funds reason {} ({!r})'.format(name, ex))
        return None


def _charge(amount):
    """Take exactly amount. True only when the balance fell by exactly that.
    A partial change (an exception half way) is given back; a change we
    cannot see is treated as not charged only when the balance is unknown
    and the call raised."""
    amount = int(amount or 0)
    if amount <= 0:
        return True
    household = _household()
    reason = _reason('FUNDS_OBJECT_BUY')
    if household is None or reason is None:
        return False
    before = funds()
    error = None
    try:
        taken = bool(household.funds.try_remove(amount, reason, None))
    except Exception as ex:
        taken, error = False, ex
    after = funds()
    if before is not None and after is not None:
        taken_now = before - after
        if taken_now == amount:
            ok = True
        else:
            ok = False
            if 0 < taken_now:
                speech.log_line('place: partial charge {} of {}; giving it back'.format(taken_now, amount))
                _refund(taken_now)
    else:
        ok = taken and error is None
    speech.log_line('place: charge {} -> {} ({} to {}, error {!r})'.format(amount, ok, before, after, error))
    return ok


def _refund(amount):
    """Give amount back. Whatever could not be paid is kept as a debt of
    this household that its next build action pays first (settle_owed)."""
    amount = int(amount or 0)
    if amount <= 0:
        return True
    household = _household()
    reason = _reason('FUNDS_OBJECT_SELL')
    paid = 0
    error = None
    before = funds()
    if household is not None and reason is not None:
        try:
            household.funds.add(amount, reason, None, count_as_earnings=False)
        except Exception as ex:
            error = ex
        after = funds()
        if before is not None and after is not None:
            paid = max(0, min(amount, after - before))
        elif error is None:
            paid = amount
    else:
        after = before
    owner = _household_id()
    if paid < amount and owner is not None:
        _owed[owner] = _owed.get(owner, 0) + amount - paid
    speech.log_line('place: refund {} paid {} ({} to {}, error {!r}, owed {})'.format(
        amount, paid, before, after, error, _owed.get(owner, 0)))
    return paid == amount


def settle_owed():
    """Pay this household any refund that failed earlier. Returns the
    amount paid now. Another household's debt is never touched."""
    owner = _household_id()
    owed = _owed.pop(owner, 0) if owner is not None else 0
    if owed <= 0:
        return 0
    if _refund(owed):
        speech.log_line('place: settled {} owed to household {}'.format(owed, owner))
        return owed
    return 0


def owed():
    return _owed.get(_household_id(), 0)


# ------------------------------------------------------------ what it needs

def requirement(def_id):
    """'slot', 'wall', 'ceiling', 'fence', 'terrain', 'water', None (the floor
    will do) or 'unknown' when the game would not say."""
    try:
        import build_buy
        flags = int(build_buy.get_object_placement_flags(def_id))
    except Exception as ex:
        speech.log_line('place: no placement flags for {} ({!r})'.format(def_id, ex))
        return 'unknown'
    for mask, need in ((FLAG_SLOT, 'slot'), (FLAG_WALL, 'wall'), (FLAG_CEILING, 'ceiling'),
                       (FLAG_FENCE, 'fence'), (FLAG_WATER, 'water'), (FLAG_TERRAIN, 'terrain')):
        if flags & mask:
            return need
    return None


_NEEDS = {
    'wall': ('It hangs on a wall. Wall placement is not available from the grid yet.',
             'To wisi na ścianie. Umieszczanie na ścianie nie jest jeszcze dostępne z siatki.'),
    'ceiling': ('It hangs from a ceiling. Ceiling placement is not available from the grid yet.',
                'To wisi pod sufitem. Umieszczanie pod sufitem nie jest jeszcze dostępne z siatki.'),
    'fence': ('It attaches to a fence. Fence placement is not available from the grid yet.',
              'To mocuje się do płotu. Umieszczanie na płocie nie jest jeszcze dostępne z siatki.'),
    'water': ('It needs a water surface.', 'To wymaga powierzchni wody.'),
    'terrain': ('It needs bare ground.', 'To wymaga gołej ziemi.'),
    'unknown': ('The game did not say where this object can go, so nothing was bought.',
                'Gra nie podała, gdzie można postawić ten obiekt, więc nic nie kupiono.'),
}


# ------------------------------------------------------------------- surfaces

def _surface_rank(obj):
    try:
        name = str(obj.definition.name or '').lower()
    except Exception:
        name = type(obj).__name__.lower()
    for words, rank in SURFACE_RANK:
        if any(word in name for word in words):
            return rank
    return 2


def _free_slot(obj, position, level):
    """(surface, slot) near the cursor that the game accepts for this object."""
    import services
    nearby = []
    lot = services.active_lot()
    household = _household_id()
    for surface in list(services.object_manager().values()):
        try:
            if surface is obj or getattr(surface, 'is_sim', False) or surface.is_in_inventory():
                continue
            if surface.is_hidden() or not lot.is_position_on_lot(surface.position):
                continue
            owner = surface.get_household_owner_id()
            if owner and owner != household:
                continue
            if int(surface.level) != int(level):
                continue
            dx = float(surface.position.x) - float(position.x)
            dz = float(surface.position.z) - float(position.z)
            if abs(dx) > SLOT_SEARCH or abs(dz) > SLOT_SEARCH:
                continue
            nearby.append((_surface_rank(surface), dx * dx + dz * dz, surface))
        except Exception:
            continue
    nearby.sort(key=lambda item: (item[0], item[1]))
    for _rank, _distance, surface in nearby:
        try:
            slots = list(surface.get_runtime_slots_gen())
        except Exception:
            continue
        for slot in slots:
            try:
                if slot.is_deco_slot() or not slot.empty:
                    continue
                if not slot.is_valid_for_placement(obj=obj):
                    continue
            except Exception:
                continue
            return surface, slot
    return None


def _put_in_slot(obj, surface, slot):
    for label, call in (('add_child', lambda: slot.add_child(obj)),
                        ('slot_object', lambda: surface.slot_object(parent_slot=slot, slotting_object=obj))):
        try:
            call()
        except Exception as ex:
            speech.log_line('place: {} failed ({!r})'.format(label, ex))
            continue
        if getattr(obj, 'parent', None) is not None:
            return True
    return False


# ------------------------------------------------------------------ the spot

def _good_location(obj, position, orientation, routing_surface, ignore=()):
    """(translation, orientation) found by the game near position, or None."""
    try:
        import placement
        start = placement.create_starting_location(position=position, orientation=orientation,
                                                   routing_surface=routing_surface)
        context = placement.create_fgl_context_for_object(
            start, obj, test_buildbuy_allowed=True, max_distance=SEARCH_RADIUS,
            ignored_object_ids=list(ignore) or None)
        result = placement.find_good_location(context)
    except Exception as ex:
        speech.log_line('place: fgl raised {!r}'.format(ex))
        return None
    if result and result[0] is not None:
        speech.log_line('place: fgl chose {}'.format(result[0]))
        return result[0], result[1]
    speech.log_line('place: fgl found nothing: {}'.format(
        result[2] if result and len(result) > 2 else result))
    return None


def _yaw(angle):
    import sims4.math
    return sims4.math.angle_to_yaw_quaternion(angle)


def _destroy(obj):
    try:
        obj.destroy(source=obj, cause='TS4 Access placement undo')
        return True
    except Exception as ex:
        speech.log_line('place: destroy failed ({!r})'.format(ex))
        return False


def _register(obj):
    try:
        import build_buy
        build_buy.add_object_to_buildbuy_system(obj.id)
        return True
    except Exception as ex:
        speech.log_line('place: add_object_to_buildbuy_system failed ({!r})'.format(ex))
        return False


def _drop_native_hand(serial):
    """Ask the client to put down whatever EA's own placement tool holds, so
    the same product is never bought twice (here, and by a later native
    click). The object is created only after the client answers."""
    try:
        import distributor.ops
        import distributor.system
        distributor.system.Distributor.instance().add_op_with_no_owner(
            distributor.ops.SendUIMessage('A11y|buildhand|drop|{}'.format(serial)))
        return True
    except Exception as ex:
        speech.log_line('place: could not ask the client to drop its tool ({!r})'.format(ex))
        return False


def _where(obj, cursor_position, level):
    import tyjokr_a11y_scanner as scanner
    try:
        entry = scanner._entry_for(obj, cursor_position, level, False, '', '')
        return scanner._place_part(entry)
    except Exception:
        return ''


def _name_parts(obj):
    import tyjokr_a11y_scanner as scanner
    try:
        entry = scanner._entry_for(obj, obj.position, int(obj.level), False, '', '')
        return scanner._name_part(entry)
    except Exception:
        return _text('the object', 'obiekt')


def tile_key(position, level):
    return (int(math.floor(float(position.x))), int(math.floor(float(position.z))), int(level))


# -------------------------------------------------------------------- actions

def _checks(position, level, key, guard):
    """Everything that can refuse before an object exists. Speaks the refusal;
    returns (item, price, need) or None."""
    item = product()
    if item is None:
        _say_text('Choose an object in the Build catalog first.',
                  'Najpierw wybierz obiekt w katalogu trybu budowania.')
        return None
    if not in_build_mode():
        _say_text('Enter Build mode first.', 'Najpierw włącz tryb budowania.')
        return None
    if guard and key in _repeat[0] and time.monotonic() - _repeat[1] < REPEAT_GUARD_SECONDS:
        _repeat[1] = 0.0
        _say([_text('Already placed here. Press Enter again to place another ',
                    'Już umieszczono tutaj. Naciśnij Enter ponownie, aby umieścić kolejny: '),
              item['name'] or _product_name(), '.'])
        return None
    need = requirement(item['id'])
    if need in _NEEDS:
        _say_text(*_NEEDS[need])
        return None
    try:
        import services
        definition = services.definition_manager().get(item['id'], get_fallback_definition_id=False)
        price = int(getattr(definition, 'price', 0) or 0)
    except Exception:
        definition, price = None, 0
    if definition is None:
        forget()
        _say_text('That catalog object is no longer available.', 'Ten obiekt z katalogu nie jest już dostępny.')
        return None
    money = funds()
    if money is not None and price > money:
        _say_text('Not enough money. It costs {} and you have {}.'.format(price, money),
                  'Za mało pieniędzy. Kosztuje {}, a masz {}.'.format(price, money))
        return None
    try:
        import build_buy
        import services
        if not services.active_lot().is_position_on_lot(position):
            _say_text('That point is not on this lot.', 'Ten punkt nie należy do tej parceli.')
            return None
        if build_buy.is_location_pool(position, level):
            _say_text('That point is in a pool.', 'Ten punkt jest w basenie.')
            return None
    except Exception as ex:
        speech.log_line('place: tile check failed ({!r})'.format(ex))
        _say_text('This point could not be checked, so nothing was bought.',
                  'Nie udało się sprawdzić tego punktu, więc nic nie kupiono.')
        return None
    return item, price, need


def place(position, level, routing_surface, angle=0.0, exact=False):
    """Ctrl+Alt+Enter on the grid: ask the client to put down EA's held
    product; the object is bought and placed when it answers (a11y.buildhand).
    exact (the Build cursor): put it at position and angle as they are,
    after the game's own placement test, instead of searching nearby.
    True when the request went out."""
    key = tile_key(position, level)
    now = time.monotonic()
    if _pending['args'] is not None and now - _pending['at'] < ACK_SECONDS:
        _say_text('Still placing the last one.', 'Trwa umieszczanie poprzedniego obiektu.')
        return False
    settle_owed()
    if _checks(position, level, key, guard=True) is None:
        return False
    _pending['serial'] += 1
    serial = _pending['serial']
    _pending.update(at=now, args=(position, level, routing_surface, angle, key, exact),
                    zone=_zone_id(), product=(product() or {}).get('id'))
    if not _drop_native_hand(serial):
        _pending['args'] = None
        _say_text('The Build tool is not answering. Nothing was bought.',
                  'Narzędzie budowania nie odpowiada. Nic nie kupiono.')
        return False
    try:
        import threading
        import tyjokr_a11y_pump as pump
        timer = threading.Timer(ACK_SECONDS, lambda: pump.post(_ack_timeout, serial))
        timer.daemon = True
        timer.start()
    except Exception as ex:
        speech.log_line('place: no acknowledgement timer ({!r})'.format(ex))
    return True


def _ack_timeout(serial):
    if serial == _pending['serial'] and _pending['args'] is not None:
        _pending['args'] = None
        speech.log_line('place: no buildhand acknowledgement for {}'.format(serial))
        _say_text('The Build tool did not answer. Nothing was bought.',
                  'Narzędzie budowania nie odpowiedziało. Nic nie kupiono.')


def cancel_pending():
    """A mode, product or grid change: an unanswered placement is dropped."""
    _pending['args'] = None


def acknowledged(serial, ok):
    """The client answered drop request serial. Place only when it put the
    product down (ok) and nothing changed meanwhile: same zone, still Build
    mode, same product."""
    if serial != _pending['serial'] or _pending['args'] is None:
        return False
    args, _pending['args'] = _pending['args'], None
    if time.monotonic() - _pending['at'] > ACK_SECONDS:
        # A backlogged pump may run this before the timer's own turn.
        speech.log_line('place: acknowledgement {} arrived too late'.format(serial))
        _say_text('The Build tool did not answer. Nothing was bought.',
                  'Narzędzie budowania nie odpowiedziało. Nic nie kupiono.')
        return False
    if not ok:
        _say_text('Press Escape to put down the current Build tool, then try again. Nothing was bought.',
                  'Naciśnij Escape, aby odłożyć bieżące narzędzie budowania, i spróbuj ponownie. Nic nie kupiono.')
        return False
    item = product()
    if (_pending.get('zone') != _zone_id() or not in_build_mode()
            or item is None or item['id'] != _pending.get('product')):
        speech.log_line('place: acknowledgement {} arrived after a change; dropped'.format(serial))
        return False
    return _execute(*args)


def _execute(position, level, routing_surface, angle, key, exact=False):
    checked = _checks(position, level, key, guard=False)
    if checked is None:
        return False
    item, price, need = checked
    try:
        from objects.system import create_object
        obj = create_object(item['id'])
    except Exception as ex:
        speech.log_line('place: create_object raised {!r}'.format(ex))
        obj = None
    if obj is None:
        _say_text('The game could not create that object.', 'Gra nie mogła utworzyć tego obiektu.')
        return False
    try:
        return _finish(obj, item, price, need, position, level, routing_surface, angle, key, exact)
    except Exception as ex:
        speech.log_line('place: placement raised {!r}; removing the object'.format(ex))
        _destroy(obj)
        _say_text('The game could not place that object, so nothing was bought.',
                  'Gra nie mogła umieścić tego obiektu, więc nic nie kupiono.')
        return False


def _finish(obj, item, price, need, position, level, routing_surface, angle, key, exact=False):
    """Put a freshly created obj in place, then own, register and pay for
    it. Any refusal removes it; an exception is handled by the caller."""
    surface = None
    if need == 'slot':
        found = _free_slot(obj, position, level)
        if found is None or not _put_in_slot(obj, found[0], found[1]):
            _destroy(obj)
            _say_text('It needs a free spot on a desk or table. Move the cursor onto one.',
                      'To wymaga wolnego miejsca na biurku lub stole. Przesuń kursor na taki mebel.')
            return False
        surface = found[0]
    elif exact:
        import tyjokr_a11y_tiles as tiles
        ok, why = tiles.test_fit(obj, item['id'], position, angle, level)
        if ok is False:
            _destroy(obj)
            _say_text('It no longer fits there ({}), so nothing was bought.'.format(why),
                      'Już się tam nie mieści ({}), więc nic nie kupiono.'.format(why))
            return False
        try:
            obj.move_to(translation=position, orientation=_yaw(angle), routing_surface=routing_surface)
        except Exception as ex:
            speech.log_line('place: exact move_to raised {!r}'.format(ex))
            _destroy(obj)
            _say_text('The game could not position that object.', 'Gra nie mogła ustawić tego obiektu.')
            return False
    else:
        spot = _good_location(obj, position, _yaw(angle), routing_surface)
        if spot is None:
            _destroy(obj)
            _say_text('No room for it here. Try another point.',
                      'Brak tu miejsca. Wybierz inny punkt.')
            return False
        try:
            obj.move_to(translation=spot[0], orientation=spot[1], routing_surface=routing_surface)
        except Exception as ex:
            speech.log_line('place: move_to raised {!r}'.format(ex))
            _destroy(obj)
            _say_text('The game could not position that object.', 'Gra nie mogła ustawić tego obiektu.')
            return False
    owner = _household_id()
    if owner is None:
        _destroy(obj)
        _say_text('No active household to own it, so nothing was bought.',
                  'Brak aktywnej rodziny, która mogłaby go posiadać, więc nic nie kupiono.')
        return False
    obj.set_household_owner_id(owner)
    if not _register(obj):
        _destroy(obj)
        _say_text('The lot would not accept it, so nothing was bought.',
                  'Parcela go nie przyjęła, więc nic nie kupiono.')
        return False
    if price and not _charge(price):
        _destroy(obj)
        _say_text('Payment failed, so nothing was bought.', 'Płatność nie powiodła się, więc nic nie kupiono.')
        return False
    # Paid: from here on the object is the household's. Nothing below may
    # raise to the caller, whose clean-up would remove a paid object.
    _after_payment(obj, item, price, owner, surface, position, level, key, exact)
    return True


def _after_payment(obj, item, price, owner, surface, position, level, key, exact=False):
    try:
        _history.append((obj.id, price, item['name'], owner, _zone_id()))
        del _history[:-MAX_HISTORY]
        _last.update(obj_id=obj.id, household=owner, zone=_zone_id(), position=None)
        _repeat[0], _repeat[1] = (key,), time.monotonic()
    except Exception as ex:
        _quiet_log('place: placed, but recording it failed ({!r})'.format(ex))
    _quiet_log('place: placed {} {!r} for {}'.format(getattr(obj, 'id', '?'), item.get('name'), price))
    try:
        if exact and surface is None:
            _announce_exact(obj, item, price, level, key)
        else:
            _announce_placed(obj, item, price, surface, position, level, key)
    except Exception as ex:
        _quiet_log('place: placed, but the announcement failed ({!r})'.format(ex))
        try:
            _say_text('Placed.', 'Umieszczono.')
        except Exception:
            pass


def _quiet_log(line):
    try:
        speech.log_line(line)
    except Exception:
        pass


def _announce_placed(obj, item, price, surface, position, level, key):
    try:
        _last['position'] = obj.position
        landed = tile_key(obj.position, int(getattr(obj, 'level', level)))
        _repeat[0] = (key, landed)
    except Exception as ex:
        speech.log_line('place: landed position unavailable ({!r})'.format(ex))
    parts = [item['name'] or _product_name()]
    if surface is not None:
        parts += [_text(' placed on ', ' umieszczono na: '), _name_parts(surface)]
    else:
        where = _where(obj, position, level)
        if not where or where == lang.t('here'):
            parts.append(_text(' placed at the cursor', ' umieszczono przy kursorze'))
        else:
            parts += [_text(' placed', ' umieszczono'), ', ', where, _text(' from the cursor', ' od kursora')]
    parts.append(_text(', {} simoleons.'.format(price), ', {} simoleonów.'.format(price)))
    if _follow(obj, level):
        parts.append(_text(' The cursor moved to it.', ' Kursor przesunięto do niego.'))
    _say(parts)


def _announce_exact(obj, item, price, level, key):
    """The Build cursor placed it exactly: facing and the tiles it covers,
    counted from its own tile; the cursor moves to it."""
    import tyjokr_a11y_tiles as tiles
    try:
        _last['position'] = obj.position
        _repeat[0] = (key, tile_key(obj.position, int(getattr(obj, 'level', level))))
    except Exception as ex:
        speech.log_line('place: landed position unavailable ({!r})'.format(ex))
    parts = [item['name'] or _product_name(), _text(' placed', ' umieszczono')]
    f = tiles.frame()
    if f is not None:
        try:
            import sims4.math
            facing = f.facing_of(sims4.math.yaw_quaternion_to_angle(obj.orientation))
            parts.append(_text(', facing {}'.format(tiles.direction_name(facing)),
                               ', skierowany na {}'.format(tiles.direction_name(facing))))
        except Exception:
            pass
        covered = tiles.covered_tiles(f, obj, level)
        if len(covered) > 1:
            base = f.tile_of(obj.position.x, obj.position.z)
            others = [tiles.relative(ci - base[0], cj - base[1]) for ci, cj in covered if (ci, cj) != base][:5]
            parts.append(_text(', covering {} tiles: this one and {}'.format(len(covered), '; '.join(others)),
                               ', zajmuje pól: {}: to i {}'.format(len(covered), '; '.join(others))))
    parts.append(_text(', {} simoleons.'.format(price), ', {} simoleonów.'.format(price)))
    if _follow(obj, level):
        parts.append(_text(' The cursor is on it.', ' Kursor jest na nim.'))
    _say(parts)


def _follow(obj, level):
    """Put the grid cursor on the placed object, on its floor."""
    try:
        import tyjokr_a11y_grid as grid
        return bool(grid.focus_position(obj.position, int(getattr(obj, 'level', level))))
    except Exception as ex:
        speech.log_line('place: cursor did not follow ({!r})'.format(ex))
        return False


def last_position():
    return _last['position']


def _last_object():
    obj_id = _last['obj_id']
    if obj_id is None or _last['household'] != _household_id() or _last['zone'] != _zone_id():
        return None
    try:
        import services
        return services.object_manager().get(obj_id)
    except Exception:
        return None


def _build_only():
    """Changing the lot's objects is a Build mode action, as in the game."""
    if in_build_mode():
        return True
    _say_text('Enter Build mode first.', 'Najpierw włącz tryb budowania.')
    return False


def rotate(step):
    """Turn the last placed object a quarter turn (step -1 or 1), where it fits."""
    if not _build_only():
        return False
    obj = _last_object()
    if obj is None:
        _say_text('Place an object first, then rotate it.', 'Najpierw umieść obiekt, a potem go obróć.')
        return False
    if getattr(obj, 'parent', None) is not None:
        _say_text('It sits on a surface and keeps its direction.', 'Stoi na powierzchni i zachowuje swój kierunek.')
        return False
    import sims4.math
    try:
        angle = sims4.math.yaw_quaternion_to_angle(obj.orientation) + step * sims4.math.PI / 2
        spot = _good_location(obj, obj.position, _yaw(angle), obj.routing_surface, ignore=(obj.id,))
        if spot is None:
            _say_text('No room to turn it here.', 'Brak miejsca, aby go tu obrócić.')
            return False
        obj.move_to(translation=spot[0], orientation=spot[1])
        _last['position'] = obj.position
    except Exception as ex:
        speech.log_line('place: rotate failed ({!r})'.format(ex))
        _say_text('Could not rotate it.', 'Nie udało się go obrócić.')
        return False
    _say_text('Rotated a quarter turn {}.'.format('left' if step < 0 else 'right'),
              'Obrócono o ćwierć obrotu w {}.'.format('lewo' if step < 0 else 'prawo'))
    return True


def undo():
    """Remove the most recent placement and give the money back."""
    if not _build_only():
        return False
    import services
    settle_owed()
    owner, zone = _household_id(), _zone_id()
    for index in range(len(_history) - 1, -1, -1):
        obj_id, price, name, household, placed_zone = _history[index]
        if household != owner or placed_zone != zone:
            continue           # another family's or another lot's purchase
        obj = services.object_manager().get(obj_id)
        if obj is None:
            del _history[index]    # sold or removed some other way
            continue
        if _occupied(obj):
            _say_text(*_CANNOT_SELL['occupied'])
            return False
        if not _destroy(obj):
            _say_text('Could not remove it.', 'Nie udało się go usunąć.')
            return False
        del _history[index]
        paid = _refund(price)
        if _last['obj_id'] == obj_id:
            _last['obj_id'] = None
        _repeat[0] = ()
        if price and not paid:
            _say([name, _text(' removed. The refund failed and will be retried with your next Build action.',
                              ' usunięto. Zwrot pieniędzy nie powiódł się i zostanie ponowiony przy następnej akcji.')])
        else:
            _say([name, _text(' removed, {} simoleons refunded.'.format(price),
                              ' usunięto, zwrócono {} simoleonów.'.format(price))])
        return True
    _say_text('Nothing to undo.', 'Nie ma czego cofnąć.')
    return False


def _value(obj):
    """What the game says obj is worth now. Its current value when it has
    one, zero included (a worthless object sells for nothing); the catalog
    price only when the object reports no value at all."""
    for getter in (lambda: obj.current_value, lambda: obj.definition.price):
        try:
            value = getter()
        except Exception:
            continue
        if value is None:
            continue
        try:
            return max(0, int(value))
        except Exception:
            continue
    return 0


_CANNOT_SELL = {
    'sim': ('Sims cannot be sold.', 'Simów nie można sprzedać.'),
    'offlot': ('That is not on this lot.', 'To nie znajduje się na tej parceli.'),
    'hidden': ('That object cannot be sold from here.', 'Tego obiektu nie można stąd sprzedać.'),
    'protected': ('The game does not allow deleting that object.', 'Gra nie pozwala usunąć tego obiektu.'),
    'foreign': ('That belongs to another household.', 'To należy do innej rodziny.'),
    'occupied': ('Something is on it, inside it or using it. Remove that first.',
                 'Coś na nim stoi, jest w nim albo ktoś go używa. Najpierw to usuń.'),
}


def _occupied(obj):
    """True when removing obj would take something else with it for obj's
    price only (live 2026-09-26: X offered a desk with a computer on it):
    any child, hidden ones included (an object in a slot, a Sim using it),
    or anything in its own inventory, which EA purges with its owner
    (InventoryComponent.on_remove; shared inventories survive)."""
    try:
        if getattr(obj, 'children', None):
            return True
        inventory = getattr(obj, 'inventory_component', None)
        if inventory is not None and not inventory.is_shared_inventory:
            for _item in inventory:
                return True
    except Exception as ex:
        speech.log_line('place: occupancy check failed ({!r})'.format(ex))
        return True           # cannot tell: never risk what it holds
    return False


def sell_refusal(obj):
    """Why obj may not be sold here, or None. Uses the game's own flags."""
    try:
        if getattr(obj, 'is_sim', False):
            return 'sim'
        if obj.is_in_inventory() or obj.is_hidden():
            return 'hidden'
        if getattr(obj, 'non_deletable', False) or getattr(obj, 'non_deletable_by_user', False):
            return 'protected'
        if _occupied(obj):
            return 'occupied'
        import services
        if not services.active_lot().is_position_on_lot(obj.position):
            return 'offlot'
        owner = obj.get_household_owner_id()
        if owner and owner != _household_id():
            return 'foreign'
    except Exception as ex:
        speech.log_line('place: sell check failed ({!r})'.format(ex))
        return 'hidden'
    return None


def sell(obj):
    """Sell obj; asks for a second press within SELL_CONFIRM_SECONDS."""
    if not _build_only():
        _sell[0] = None
        return False
    settle_owed()
    if obj is None:
        _say_text('Nothing here to sell.', 'Nie ma tu nic do sprzedania.')
        return False
    refusal = sell_refusal(obj)
    if refusal is not None:
        _sell[0] = None
        _say_text(*_CANNOT_SELL[refusal])
        return False
    now = time.monotonic()
    value = _value(obj)
    name = _name_parts(obj)
    if _sell[0] != obj.id or now - _sell[1] > SELL_CONFIRM_SECONDS:
        _sell[0], _sell[1] = obj.id, now
        _say([_text('Sell ', 'Sprzedać: '), name,
              _text(' for {} simoleons? Press again to confirm.'.format(value),
                    ' za {} simoleonów? Naciśnij ponownie, aby potwierdzić.'.format(value))])
        return False
    _sell[0] = None
    if not _destroy(obj):
        _say_text('Could not sell it.', 'Nie udało się tego sprzedać.')
        return False
    paid = _refund(value)
    if _last['obj_id'] == obj.id:
        _last['obj_id'] = None
    if value and not paid:
        _say([name, _text(' removed. The money did not come back yet and will be retried with your next Build action.',
                          ' usunięto. Pieniądze jeszcze nie wróciły; zwrot zostanie ponowiony przy następnej akcji.')])
    else:
        _say([name, _text(' sold for {} simoleons.'.format(value), ' sprzedano za {} simoleonów.'.format(value))])
    return True


@sims4.commands.Command('a11y.buildproduct', command_type=sims4.commands.CommandType.Live)
def buildproduct(encoded: str = '', _connection=None):
    """Client: the Build catalog selected a product ('<instance>|<name>') or
    dropped it ('0|'). Names arrive percent-encoded."""
    from urllib.parse import unquote
    text = str(encoded)
    if '|' not in text or len(text) > 800:
        return False
    instance, name = text.split('|', 1)
    return set_product(instance, unquote(name))


@sims4.commands.Command('a11y.catalogleft', command_type=sims4.commands.CommandType.Live)
def catalogleft(_state: str = '', _connection=None):
    """Client: Escape released the Build catalog's keys (TooltipManager
    A11yReleaseBuildCatalog). The chosen product is unchanged."""
    item = product()
    try:
        import tyjokr_a11y_grid as grid
        placing = grid.build_cursor()
    except Exception:
        placing = False
    if placing:
        name = item['name'] if item is not None and item['name'] else ''
        _say_text('Back to Build placement. {}'.format(name + ' chosen.' if name else 'No object chosen.'),
                  'Powrót do umieszczania. {}'.format('Wybrano: ' + name + '.' if name else 'Nie wybrano obiektu.'))
        return True
    if item is not None and item['name']:
        _say_text('Left the Build catalog. {} chosen. Control Alt B places it. Tab returns to the catalog.'.format(item['name']),
                  'Opuszczono katalog budowania. Wybrano: {}. Control Alt B umieszcza. Tab wraca do katalogu.'.format(item['name']))
    else:
        _say_text('Left the Build catalog. Tab returns to the catalog.',
                  'Opuszczono katalog budowania. Tab wraca do katalogu.')
    return True


@sims4.commands.Command('a11y.buildhand', command_type=sims4.commands.CommandType.Live)
def buildhand(encoded: str = '', _connection=None):
    """Client: '<serial>|ok' once EA's placement tool holds nothing (it put
    the product down, or held none), '<serial>|denied' when it could not."""
    text = str(encoded)
    if '|' not in text or len(text) > 40:
        return False
    serial, state = text.split('|', 1)
    if not serial.isdigit() or state not in ('ok', 'denied'):
        return False
    return acknowledged(int(serial), state == 'ok')
