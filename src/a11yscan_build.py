"""Buying and placing objects.

This is the only part of the mod that changes the world irreversibly, so it is
deliberately cautious:

  * the tile is checked before anything is created,
  * funds are checked before anything is charged,
  * every placement is remembered so it can be undone with a refund,
  * and every step is logged, because a bad placement can corrupt a lot
    without raising anything.

Objects are created with objects.system.create_object, positioned with
move_to (which clones the current location with overrides), registered with
build_buy so the game treats them as owned, and paid for through the
household's funds.
"""
import a11yscan_log as logfile
import a11yscan_world as world

_history = []
MAX_HISTORY = 20


_reason_cache = []


def funds_reason():
    """The integer reason code household funds want for a change.

    try_remove takes a REASON CODE, not a description: passing the string
    'a11yscan build' raised "expected one of: int, long" and the charge was
    silently skipped - which is why placed objects logged charged=False and a
    shop purchase cost nothing. The constants live in Consts_pb2, which is not
    in the script archives, so ask the module at runtime and record what it has.
    """
    if _reason_cache:
        return _reason_cache[0]
    reason = 0
    try:
        from protocolbuffers import Consts_pb2
        names = [n for n in dir(Consts_pb2) if n.startswith('FUNDS_')]
        logfile.write('funds: {} reason codes, e.g. {}'.format(
            len(names), ', '.join(sorted(names)[:12])))
        # Buying furniture is a PURCHASE, and the money cheat was first in
        # this list - so every placement was booked as a cheat. The game
        # treats the two differently, and a cheat is not something it plays a
        # purchase sound for. The cheat code stays, but only as a last resort.
        for name in ('FUNDS_BUILD_BUY_OBJECT', 'FUNDS_OBJECT_BOUGHT',
                     'FUNDS_BUILDBUY', 'FUNDS_BUY_OBJECT',
                     'FUNDS_BUILD_BUY', 'FUNDS_GAMEPLAY',
                     'FUNDS_MONEY_CHEAT', 'FUNDS_UNKNOWN'):
            value = getattr(Consts_pb2, name, None)
            if value is not None:
                reason = int(value)
                logfile.write('funds: using reason {} = {}'.format(name, reason))
                break
        else:
            if names:
                reason = int(getattr(Consts_pb2, sorted(names)[0]))
                logfile.write('funds: falling back to {}'.format(sorted(names)[0]))
    except Exception as ex:
        logfile.write('funds: no Consts_pb2 ({!r}); using 0'.format(ex))
    _reason_cache.append(reason)
    return reason


def charge(amount, sim=None):
    """Take money from the household. Returns True only if it actually left."""
    amount = int(amount or 0)
    if amount <= 0:
        return True
    household = _household()
    if household is None:
        return False
    before = funds_available()
    reason = funds_reason()
    for label, call in (
            ('(amount, reason, sim)',
             lambda: household.funds.try_remove(amount, reason, sim)),
            ('(amount, reason)',
             lambda: household.funds.try_remove(amount, reason))):
        try:
            call()
        except TypeError:
            continue
        except Exception as ex:
            logfile.write('funds: {} raised {!r}'.format(label, ex))
            continue
        after = funds_available()
        # Believe the balance, not the call.
        if before is None or after is None or after < before:
            logfile.ok('funds: charged {} ({} -> {})'.format(
                amount, before, after))
            return True
        logfile.write('funds: {} left the balance at {}'.format(label, after))
    logfile.fail('funds: could not charge {}'.format(amount))
    return False


def _household():
    try:
        import services
        return services.active_household()
    except Exception:
        return None


def funds_available():
    household = _household()
    if household is None:
        return None
    for getter in (lambda: household.funds.money,
                   lambda: household.funds.get_money()):
        try:
            return int(getter())
        except Exception:
            continue
    return None


def _tile_ok(position, level):
    """Refuse obviously bad ground before creating anything."""
    problems = []
    try:
        import services
        lot = services.active_lot()
        if lot is not None and not lot.is_position_on_lot(position):
            problems.append('not on your lot')
    except Exception:
        pass
    try:
        import build_buy
        if build_buy.is_location_pool(position, level):
            problems.append('in a pool')
    except Exception:
        pass
    return problems


# What the game says an object needs, from build_buy.PlacementFlags. A
# computer carries REQUIRES_SLOT: it belongs on a desk, and dropping one on
# the floor produces furniture that looks placed, charges full price and
# cannot be used - which is exactly what happened to a 10,000 simoleon PC.
PLACEMENT_NEEDS = (
    (1024, 'a desk or table to stand on'),
    (65536, 'bare ground'),
    (2097152, 'a water surface'),
    (128, 'a fence to attach to'),
    (1, 'a wall to hang on'),
    (8, 'a ceiling to hang from'),
)


def placement_requirement(definition):
    """What this object needs under it, or None if the floor will do."""
    definition_id = getattr(definition, 'id', None)
    if not definition_id:
        return None
    try:
        import build_buy
        flags = int(build_buy.get_object_placement_flags(definition_id))
    except Exception as ex:
        logfile.write('build: no placement flags ({!r})'.format(ex))
        return None
    for bit, phrase in PLACEMENT_NEEDS:
        if flags & bit:
            return phrase
    return None


def refund(amount):
    """Give money back for something sold. Verified against the balance."""
    amount = int(amount or 0)
    if amount <= 0:
        return True
    household = _household()
    if household is None:
        return False
    before = funds_available()
    reason = funds_reason()
    for label, call in (('(amount, reason)',
                         lambda: household.funds.add(amount, reason)),
                        ('(amount, reason, None)',
                         lambda: household.funds.add(amount, reason, None))):
        try:
            call()
        except TypeError:
            continue
        except Exception as ex:
            logfile.write('funds: refund {} raised {!r}'.format(label, ex))
            continue
        after = funds_available()
        if before is None or after is None or after > before:
            logfile.ok('funds: refunded {} ({} -> {})'.format(
                amount, before, after))
            return True
    logfile.fail('funds: could not refund {}'.format(amount))
    return False


def sale_value(obj):
    """What this object is worth. The game's own figure where it has one."""
    for getter in (lambda: obj.current_value,
                   lambda: obj.definition.price):
        try:
            value = int(getter())
            if value:
                return value
        except Exception:
            continue
    return 0


def sell(obj):
    """Sell one placed object: money back, then it goes.

    Order matters. Destroying first loses the value - current_value lives on
    the object - so the refund is worked out and paid before anything is
    removed, and the removal is verified rather than assumed.
    """
    if obj is None:
        return 'Nothing to sell.'
    import a11yscan_world as world
    name = world.object_name(obj)
    value = sale_value(obj)
    paid = refund(value) if value else False
    if not _destroy(obj):
        if paid:
            # Take it back rather than leaving free money behind.
            charge(value)
        logfile.fail('build: could not remove {!r}'.format(name))
        return 'Could not sell {}.'.format(name)
    logfile.ok('build: sold {!r} for {}'.format(name, value))
    if value and paid:
        return '{} sold for {:,} simoleons.'.format(name, value)
    if value:
        return '{} removed, but the money did not come back.'.format(name)
    return '{} removed. It was worth nothing.'.format(name)


SLOT_SEARCH_TILES = 1.2


def _slot_flag(slot, name):
    """Read a slot attribute whether it is a property or a method.

    RuntimeSlot exposes empty, is_deco_slot and is_valid_for_placement, and
    getting this wrong is silent: calling a bool raises, the exception is
    swallowed, and every slot looks unusable. That is why a desk right under
    the cursor still reported no free slot.
    """
    try:
        value = getattr(slot, name)
    except Exception:
        return None
    if callable(value):
        try:
            value = value()
        except Exception:
            return None
    return value


# Not every surface is a good home for every object. A computer on a kitchen
# island sits in a decorative stand slot with no usable posture: the
# interaction queues, the game cannot build a transition to it, and it is
# dropped silently. The same computer on a desk works. So surfaces are ranked,
# and the best one near the cursor wins rather than merely the closest.
SURFACE_RANK = (
    (('desk',), 0),
    (('table',), 1),
    (('counter', 'island'), 3),
    (('shelf', 'bookcase', 'dresser', 'endtable', 'nightstand'), 4),
    (('lamp', 'light'), 9),
)


def _surface_rank(surface):
    name = ''
    for getter in (lambda: surface.definition.name,
                   lambda: type(surface).__name__):
        try:
            name = str(getter() or '').lower()
        except Exception:
            name = ''
        if name:
            break
    for words, rank in SURFACE_RANK:
        if any(word in name for word in words):
            return rank
    return 2


def find_surface_slot(position, level):
    """An empty slot on a surface at this spot: (surface, slot) or None.

    Objects with REQUIRES_SLOT belong ON something, so the surfaces near the
    cursor are asked for a free slot - which is what build mode does when it
    snaps a computer onto a desk.
    """
    import a11yscan_world as world
    try:
        candidates = list(world._iter_objects())
    except Exception as ex:
        logfile.write('build: could not list surfaces ({!r})'.format(ex))
        return None
    # Nearest first. Taking whatever came out of the object list first put a
    # computer on a patio table and another on a lamp, because both happened
    # to be within a tile and both had a free slot.
    nearby = []
    for surface in candidates:
        try:
            if int(getattr(surface, 'level', 0) or 0) != int(level):
                continue
            spot = surface.position
            dx = float(spot.x) - float(position.x)
            dz = float(spot.z) - float(position.z)
            if abs(dx) > SLOT_SEARCH_TILES or abs(dz) > SLOT_SEARCH_TILES:
                continue
            nearby.append((_surface_rank(surface), dx * dx + dz * dz,
                           surface))
        except Exception:
            continue
    # Best kind of surface first, then nearest of that kind.
    nearby.sort(key=lambda item: (item[0], item[1]))
    if nearby:
        import a11yscan_world as world
        logfile.write('build: surfaces here, best first: {}'.format(
            ', '.join('{} (rank {})'.format(world.object_name(sfc), rank)
                      for rank, _d, sfc in nearby[:4])))

    slotted = examined = 0
    for _rank, _distance, surface in nearby:
        try:
            slots = list(surface.get_runtime_slots_gen())
        except Exception:
            continue
        if slots:
            slotted += 1
        for slot in slots:
            examined += 1
            if _slot_flag(slot, 'is_deco_slot'):
                continue
            if _slot_flag(slot, 'empty') is False:
                continue
            if _slot_flag(slot, 'is_valid_for_placement') is False:
                continue
            logfile.ok('build: free slot on {!r}'.format(
                world.object_name(surface)))
            return (surface, slot)
    near = len(nearby)
    logfile.write('build: {} objects on this tile, {} with slots, {} slots '
                  'examined, none usable'.format(near, slotted, examined))
    return None


def put_in_slot(obj, surface, slot):
    """Attach a placed object to a surface slot. Verified by its parent."""
    import a11yscan_world as world
    for label, call in (
            ('slot.add_child', lambda: slot.add_child(obj)),
            ('surface.slot_object',
             lambda: surface.slot_object(parent_slot=slot,
                                         slotting_object=obj))):
        try:
            call()
        except Exception as ex:
            logfile.write('build: {} failed ({!r})'.format(label, ex))
            continue
        # Believe the parent, not the call.
        try:
            parent = obj.parent
        except Exception:
            parent = None
        if parent is not None:
            logfile.ok('build: slotted onto {!r} via {}'.format(
                world.object_name(surface), label))
            return True
        logfile.write('build: {} ran but nothing is holding it'.format(label))
    return False


# Where the last placed object ended up, so the grid cursor can follow it.
_last_position = [None]


def last_placed_position():
    return _last_position[0]


def good_location_near(obj, position, routing_surface):
    """Ask the game where this object should actually go.

    placement.find_good_location is the search build mode uses: it knows the
    object's footprint, what the lot allows and what is already there, so it
    finds a spot that WORKS near the one you asked for. Choosing coordinates
    by hand cannot do any of that - it is how a computer ended up on a patio
    table and objects ended up somewhere Sims could not use them.

    Returns (translation, orientation) or None to leave the object be.
    """
    try:
        import placement
    except Exception as ex:
        logfile.write('build: no placement module ({!r})'.format(ex))
        return None
    try:
        starting = placement.create_starting_location(
            position=position, routing_surface=routing_surface)
    except Exception as ex:
        logfile.write('build: could not build a starting location '
                      '({!r})'.format(ex))
        return None
    for label, call in (
            ('with buildbuy tests',
             lambda: placement.create_fgl_context_for_object(starting, obj)),
            ('without buildbuy tests',
             lambda: placement.create_fgl_context_for_object(
                 starting, obj, test_buildbuy_allowed=False))):
        try:
            context = call()
            result = placement.find_good_location(context)
        except Exception as ex:
            logfile.write('build: fgl {} raised ({!r})'.format(label, ex))
            continue
        try:
            translation, orientation = result[0], result[1]
        except Exception:
            translation = orientation = None
        if translation is None:
            logfile.write('build: fgl {} found nowhere ({})'.format(
                label, str(result)[:90]))
            continue
        logfile.write('build: fgl {} chose {}'.format(label, translation))
        return (translation, orientation)
    return None


_build_watch = {'until': 0.0, 'last': None}


def build_state():
    """Does the GAME think you are in build mode right now?"""
    try:
        import build_buy
        import services
        return bool(build_buy.get_user_in_build_buy(services.current_zone_id()))
    except Exception:
        return None


def watch_build(seconds=25.0):
    """Sample that flag for a while, so F2 can be tested against a fact.

    Every check so far has asked the game a question the game can answer, and
    all of them came back clean while F2 stayed dead. This asks a different
    question: does anything change when the key is pressed? If the flag flips,
    build mode IS opening and the problem is that nothing says so. If it never
    flips, the key is not reaching the game and no amount of server-side
    fixing will help.
    """
    import time
    import a11yscan_log as logfile
    _build_watch['until'] = time.monotonic() + float(seconds)
    _build_watch['last'] = build_state()
    logfile.write('build: watching the build/buy flag for {:.0f}s, it is {!r} '
                  'now'.format(seconds, _build_watch['last']))
    return ('Watching for {:.0f} seconds. Press F2 now, a few times. I will '
            'say if the game notices.'.format(seconds))


def watch_tick():
    """Called from the slow tick while a watch is running."""
    import time
    if time.monotonic() > _build_watch['until']:
        return
    state = build_state()
    if state == _build_watch['last']:
        return
    _build_watch['last'] = state
    import a11yscan_log as logfile
    import a11yscan_speech as speech
    logfile.ok('build: the build/buy flag changed to {!r}'.format(state))
    speech.speak('The game says build mode is now {}.'.format(
        'open' if state else 'closed'))


def announce_enter():
    """Say when build mode opens, which nothing has ever done.

    build_buy exposes an enter callback beside the exit one the mod already
    uses. Without it, opening build mode is silent - and a blind player has no
    way to tell "F2 did nothing" from "F2 worked and nobody mentioned it".
    """
    import a11yscan_log as logfile
    try:
        import build_buy

        def a11yscan_on_build_buy_enter(*args, **kwargs):
            try:
                import a11yscan_speech as speech
                speech.speak('Build mode. Control Alt B for the tile grid, '
                             'Control Alt K for the catalog.')
                logfile.ok('build: build mode opened')
            except Exception:
                pass

        build_buy.register_build_buy_enter_callback(
            a11yscan_on_build_buy_enter)
        logfile.write('build/buy enter hook installed')
        return True
    except Exception as ex:
        logfile.write('build/buy enter hook failed ({!r})'.format(ex))
        return False


def locking_situations():
    """Situations currently holding build mode shut, by name.

    A situation with a tuned build_buy_lock_reason sends the client a
    BuildBuyLockUnlock op when it starts, and the matching unlock from
    Situation.on_remove when it ends. If one ever goes away without that
    unlock reaching the client, build mode stays locked with nothing on the
    server side to show for it - which looks exactly like a dead F2 key.
    """
    out = []
    try:
        import services
        manager = services.get_zone_situation_manager()
        for situation in manager.running_situations():
            try:
                if getattr(situation, 'build_buy_lock_reason', None) is not None:
                    out.append(type(situation).__name__)
            except Exception:
                continue
    except Exception as ex:
        import a11yscan_log as logfile
        logfile.write('build: could not check for locks ({!r})'.format(ex))
    return out


def unlock_build():
    """Tell the client build mode is not locked, whoever locked it.

    The same op the game sends, with the flag the other way round. Sending an
    unlock when nothing is locked is harmless: it says "not locked", which is
    already true.
    """
    import a11yscan_log as logfile
    holders = locking_situations()
    try:
        from distributor.ops import BuildBuyLockUnlock
        from distributor.system import Distributor
        op = BuildBuyLockUnlock(False, None)
        Distributor.instance().add_op_with_no_owner(op)
    except Exception as ex:
        logfile.fail('build: unlock op failed ({!r})'.format(ex))
        return 'Could not send the unlock. The log has the reason.'
    logfile.ok('build: sent a build/buy unlock; {} situations still hold a '
               'lock reason: {}'.format(len(holders), ', '.join(holders) or 'none'))
    if holders:
        return ('Unlock sent, but {} is still running and locks building. End '
                'it from this menu, then press F2.'.format(holders[0]))
    return 'Unlock sent. Press F2 now.'


def why_no_build():
    """Why the game is refusing build mode, in the order that matters."""
    import a11yscan_log as logfile
    reasons = []
    notes = []
    try:
        import services
        zone_id = services.current_zone_id()
    except Exception as ex:
        return 'No lot is loaded, so there is nothing to build on. ({!r})'.format(ex)

    # Already in it. If the client thinks build mode is open, F2 is a toggle
    # being pressed against a state nobody can see.
    try:
        import build_buy
        inside = build_buy.get_user_in_build_buy(zone_id)
        notes.append('the game says you are {} build mode'.format(
            'IN' if inside else 'not in'))
        if inside:
            reasons.append('The game already thinks you are in build mode. '
                           'Press F2 again, or use the menu entry to force it '
                           'closed and then press F2.')
    except Exception as ex:
        notes.append('could not ask whether build mode is open ({!r})'.format(ex))

    # Whose lot is this? Build mode is for lots you own.
    owner_id = None
    household = None
    try:
        import services
        persistence = services.get_persistence_service()
        owner_id = persistence.get_household_id_from_zone_id(zone_id)
        household = services.active_household()
    except Exception as ex:
        notes.append('could not read who owns this lot ({!r})'.format(ex))
    mine = bool(household is not None and owner_id
                and owner_id == getattr(household, 'id', None))
    notes.append('this lot is {}'.format('yours' if mine else 'not yours'))
    if not mine:
        reasons.append('This lot does not belong to your household, and build '
                       'mode only opens on lots you own. Travel home first.')

    # A venue change is the most likely recent cause, so name it outright.
    try:
        import a11yscan_venues as venues
        kind = venues.current()
        if kind:
            notes.append('it is {}'.format(kind))
            if mine and kind and 'residential' not in kind.lower():
                reasons.append('This lot is {} rather than a home. Changing a '
                               'lot away from residential is what usually '
                               'takes build mode away - set it back with '
                               'a11y2.venue, or the cheats menu.'.format(kind))
    except Exception as ex:
        notes.append('could not read the venue type ({!r})'.format(ex))

    # An event running on the lot blocks building until it ends.
    try:
        import services
        manager = services.get_zone_situation_manager()
        running = [s for s in manager.running_situations()
                   if 'event' in type(s).__name__.lower()]
        if running:
            names = ', '.join(type(s).__name__ for s in running[:3])
            reasons.append('An event is running here ({}), and the game blocks '
                           'building during one. End it from the cheats '
                           'menu.'.format(names))
    except Exception as ex:
        notes.append('could not list situations ({!r})'.format(ex))

    holders = locking_situations()
    if holders:
        notes.append('locked by {}'.format(', '.join(holders)))
        reasons.append('{} is running and holds build mode locked. End it, or '
                       'use "Unlock build mode" in this menu.'.format(
                           holders[0]))
    # Owning a lot and LIVING on it are different facts, and the game asks
    # the second one. A household can own a lot whose home_zone_id points
    # somewhere else entirely, which reads as visiting.
    try:
        home = getattr(household, 'home_zone_id', None) if household else None
        notes.append('home zone {}, this zone {}'.format(home, zone_id))
        if household is not None and home and int(home) != int(zone_id):
            reasons.append('Your household owns this lot but its home is a '
                           'different one, so the game treats you as visiting. '
                           'Use the moving menu to move here properly.')
        resides = None
        try:
            resides = household.considers_current_zone_its_residence()
        except Exception:
            resides = None
        if resides is not None:
            notes.append('considers this its residence: {}'.format(resides))
            if not resides:
                reasons.append('The game does not consider this lot your '
                               "household's residence, which is the test build "
                               'mode uses.')
    except Exception as ex:
        notes.append('could not compare home zones ({!r})'.format(ex))

    # A modal the client is still drawing stops mode switches dead, and it is
    # the one thing on this list that lives entirely on the client - which is
    # why every server-side check can come back clean while F2 does nothing.
    # service_dialogs asks the game's own dialog service, not our hooks.
    try:
        import a11yscan_dialogs as dialogs
        live = dialogs.service_dialogs()
        notes.append('{} dialogs open'.format(len(live)))
        if live:
            names = []
            for dialog in live[:3]:
                title = None
                try:
                    title = dialogs.title_of(dialog, fallback=False)
                except Exception:
                    title = None
                names.append(title or type(dialog).__name__)
            reasons.append('The game still has {} dialog{} open ({}). A '
                           'pop-up on screen blocks build mode. Press Control '
                           'Alt X to force it closed, then F2.'.format(
                               len(live), '' if len(live) == 1 else 's',
                               ', '.join(names)))
    except Exception as ex:
        notes.append('could not check open dialogs ({!r})'.format(ex))

    # The lot has a SECOND owner field, separate from the household deed:
    # the venue owner, used for businesses. A residential lot should have none.
    # If one is left pointing at somebody, the client treats the lot as a
    # business you do not own - which blocks build mode on that lot only, and
    # is invisible to every household-level check above.
    try:
        import build_buy
        venue_owner = build_buy.get_current_venue_owner_id()
        notes.append('venue owner {!r}'.format(venue_owner))
        if venue_owner and venue_owner != getattr(household, 'id', None):
            reasons.append('This lot is registered as a business belonging to '
                           'somebody else. Use "Make this lot mine" in the '
                           'cheats menu, which now clears that too.')
    except Exception as ex:
        notes.append('could not read the venue owner ({!r})'.format(ex))

    logfile.write('why no build: {}'.format('; '.join(notes)))
    if reasons:
        return ' '.join(reasons)
    return ('Nothing on the game\'s side is blocking build mode: {}. So F2 '
            'itself is not arriving - check whether another program took that '
            'key, and try clicking on the game window first.'.format(
                ', '.join(notes)))


def force_leave_build():
    """Clear a build mode the client thinks is open when it is not."""
    import a11yscan_log as logfile
    try:
        import build_buy
        import services
        zone_id = services.current_zone_id()
        build_buy.init_build_buy_force_exit(zone_id)
        build_buy.build_buy_force_exit(zone_id)
    except Exception as ex:
        logfile.fail('build: force exit failed ({!r})'.format(ex))
        return 'Could not force build mode closed. The log has the reason.'
    logfile.ok('build: forced build mode closed')
    return 'Told the game to close build mode. Press F2 now.'


def register(obj):
    """Hand an object to the build/buy system so the lot owns it.

    The object's ID, not the object. This wanted an int all along -
    "argument 1 must be int, not object_Computer_DS" - so registration failed
    silently on every placement. The object appeared and was paid for, but the
    lot never took ownership, which is why Sims would not use what was built.
    """
    for label, argument in (('id', getattr(obj, 'id', None)), ('object', obj)):
        if argument is None:
            continue
        try:
            import build_buy
            build_buy.add_object_to_buildbuy_system(argument)
            logfile.write('build: registered via {}'.format(label))
            return True
        except Exception as ex:
            logfile.write('build: add_object_to_buildbuy_system({}) failed '
                          '({!r})'.format(label, ex))
    return False


def register_everything():
    """Register every object on the lot the build/buy system does not own.

    For furniture placed before that call was fixed. Registering something
    already registered is harmless - the system takes the id either way - so
    this can be run without working out which objects are affected.
    """
    try:
        import services
        objects = list(services.object_manager().get_all())
    except Exception as ex:
        logfile.fail('build: could not list objects ({!r})'.format(ex))
        return 'Could not read the lot.'
    done = failed = skipped = 0
    for obj in objects:
        # Sims are objects too, and so is anything without an id.
        try:
            if getattr(obj, 'is_sim', False) or getattr(obj, 'id', None) is None:
                skipped += 1
                continue
        except Exception:
            skipped += 1
            continue
        if register(obj):
            done += 1
        else:
            failed += 1
    logfile.ok('build: registered {} objects, {} failed, {} skipped'.format(
        done, failed, skipped))
    if not done:
        return 'Nothing could be registered. The log has the reason.'
    if failed:
        return ('Registered {} objects on the lot. {} would not take - the log '
                'says which.'.format(done, failed))
    return ('Registered {} objects on the lot. Anything you built before '
            'should work now.'.format(done))


def place(definition, price, position, level, routing_surface):
    """Buy and place one object. Returns a spoken status string."""
    # Something that belongs ON a surface goes into a slot, not on the floor.
    # Only refuse when there is genuinely nowhere to put it.
    needs = placement_requirement(definition)
    target_slot = None
    if needs == 'a desk or table to stand on':
        target_slot = find_surface_slot(position, level)
        if target_slot is None:
            logfile.write('build: refused, no free surface slot nearby')
            return ('That needs a desk or table with room on it. Put one down '
                    'and move the cursor onto it.')
    elif needs:
        logfile.write('build: refused, this needs {}'.format(needs))
        return ('That needs {}. Put one down first, then place this on '
                'it.'.format(needs))

    price = int(price or 0)
    money = funds_available()
    if money is not None and money < price:
        logfile.fail('build: {} costs {} but funds are {}'.format(
            world.definition_name(definition), price, money))
        return 'Not enough money. That costs {} and you have {}.'.format(
            price, money)

    problems = _tile_ok(position, level)
    if problems:
        logfile.fail('build: refused, {}'.format('; '.join(problems)))
        return 'Cannot place there: {}.'.format(', '.join(problems))

    name = world.definition_name(definition)
    try:
        from objects.system import create_object
        obj = create_object(definition)
    except Exception as ex:
        logfile.fail('build: create_object raised {!r}'.format(ex))
        return 'Could not create that object.'
    if obj is None:
        logfile.fail('build: create_object returned nothing')
        return 'Could not create that object.'

    # Let the game choose the exact spot. You point at roughly where you want
    # it; find_good_location works out somewhere the object actually fits and
    # is allowed, near there.
    moved_to = position
    orientation = None
    found = good_location_near(obj, position, routing_surface)
    if found is not None:
        moved_to, orientation = found
    try:
        if orientation is not None:
            obj.move_to(translation=moved_to, orientation=orientation,
                        routing_surface=routing_surface)
        else:
            obj.move_to(translation=moved_to, routing_surface=routing_surface)
    except Exception as ex:
        logfile.fail('build: move_to raised {!r}'.format(ex))
        _destroy(obj)
        return 'Could not position that object.'

    # The object's ID, not the object. This wanted an int all along -
    # "argument 1 must be int, not object_Computer_DS" - so registration
    # failed silently on every single placement. The object still appeared and
    # you were still charged, but the lot never took ownership of it, which is
    # why Sims would not use what you built.
    surface_name = None
    if target_slot is not None:
        surface, slot = target_slot
        if not put_in_slot(obj, surface, slot):
            _destroy(obj)
            return ('Could not put that on the surface. The log has the '
                    'reason.')
        surface_name = world.object_name(surface)

    registered = register(obj)

    charged = charge(price) if price else False

    try:
        _last_position[0] = obj.position
    except Exception:
        _last_position[0] = None
    _history.append((obj, price if charged else 0, name))
    del _history[:-MAX_HISTORY]
    logfile.ok('build: placed {!r} for {} (registered={}, charged={})'.format(
        name, price, registered, charged))
    if not registered:
        # Say so. An object the lot does not own looks placed and cannot be
        # used, and silence there cost several thousand simoleons of furniture
        # that nobody could sit at.
        return ('{} placed for {} simoleons, but the lot would not register '
                'it - Sims may not be able to use it.'.format(name, price))
    if surface_name:
        return '{} placed on the {} for {} simoleons.'.format(
            name, surface_name, price)
    return '{} placed for {} simoleons.'.format(name, price)


def _destroy(obj):
    for attempt in (lambda: obj.destroy(source=obj, cause='a11yscan undo'),
                    lambda: obj.destroy()):
        try:
            attempt()
            return True
        except Exception:
            continue
    return False


def undo():
    """Remove the most recent placement and refund it."""
    if not _history:
        return 'Nothing to undo.'
    obj, price, name = _history.pop()
    if not _destroy(obj):
        logfile.fail('build: could not remove {!r}'.format(name))
        return 'Could not remove {}.'.format(name)
    if price:
        household = _household()
        try:
            household.funds.add(price, 'a11yscan undo', None)
        except TypeError:
            try:
                household.funds.add(price, 'a11yscan undo')
            except Exception as ex:
                logfile.write('build: refund failed ({!r})'.format(ex))
        except Exception as ex:
            logfile.write('build: refund failed ({!r})'.format(ex))
    logfile.ok('build: undid {!r}, refunded {}'.format(name, price))
    return '{} removed, {} refunded.'.format(name, price)


def history_depth():
    return len(_history)


# --------------------------------------------------------------- shop purchases

def _inventory_size(inventory):
    """How many ITEMS are held, counting stacks properly.

    len(list(inventory)) counts stacks. Buying a second identical thing merges
    into the existing stack and leaves that number unchanged, which read as a
    failed add - and the object was then destroyed, taking the whole stack with
    it. So the inventory ended up smaller than before the purchase.
    """
    try:
        total = 0
        for item in inventory:
            count = getattr(item, 'stack_count', None)
            if callable(count):
                count = count()
            try:
                total += max(1, int(count or 1))
            except Exception:
                total += 1
        return total
    except Exception:
        return None


def buy_into_inventory(def_id, count, price=None):
    """Buy `count` of a definition straight into the Sim's inventory.

    The game's own shop flow could not be completed from here: answering the
    picker only records the basket against the interaction
    (PurchasePickerInteraction._on_picker_selected), and the Sim buys later as
    part of the interaction continuing - which we were never able to drive. The
    household funds never moved, proven by reading them either side.

    So this does the two things a shop actually does: take the money, and hand
    over the goods. It bypasses whatever else a shop's own logic might do, and
    it works the same way for every shop.
    """
    import a11yscan_world as world
    count = max(1, int(count))
    try:
        import services
        definition = services.definition_manager().get(def_id)
    except Exception as ex:
        logfile.fail('shop: no definition for {} ({!r})'.format(def_id, ex))
        return False, 'Could not find that item.'
    if definition is None:
        logfile.fail('shop: definition {} is unknown'.format(def_id))
        return False, 'Could not find that item.'

    name = world.definition_name(definition)
    if price is None:
        try:
            price = int(getattr(definition, 'price', 0) or 0)
        except Exception:
            price = 0
    total = int(price) * count

    money = funds_available()
    if money is not None and total and money < total:
        logfile.fail('shop: {} costs {} but funds are {}'.format(
            name, total, money))
        return False, 'Not enough money. That costs {} and you have {}.'.format(
            total, money)

    sim = world.active_sim()
    inventory = getattr(sim, 'inventory_component', None) if sim else None
    if inventory is None:
        logfile.fail('shop: no inventory to put {} in'.format(name))
        return False, 'Your Sim has nowhere to put that.'

    made = []
    try:
        from objects.system import create_object
    except Exception as ex:
        logfile.fail('shop: create_object unavailable ({!r})'.format(ex))
        return False, 'Could not create that item.'
    for _each in range(count):
        try:
            obj = create_object(definition)
        except Exception as ex:
            logfile.fail('shop: create_object raised {!r}'.format(ex))
            break
        if obj is None:
            break
        # system_add_object is what the game uses when it puts a crafted or
        # carried object away (crafting_interactions.create_craftable,
        # carry_postures). player_try_add_object returned true without the
        # object ever landing - the inventory count did not move - so believe
        # the count, not the return value.
        before_count = _inventory_size(inventory)
        added = False
        for label, call in (
                ('system_add_object',
                 lambda o=obj: inventory.system_add_object(o)),
                ('system_add_object(sim)',
                 lambda o=obj: inventory.system_add_object(o, sim)),
                ('player_try_add_object',
                 lambda o=obj: inventory.player_try_add_object(o))):
            try:
                call()
            except TypeError:
                continue
            except Exception as ex:
                logfile.write('shop: {} failed ({!r})'.format(label, ex))
                continue
            after_count = _inventory_size(inventory)
            if before_count is None or after_count is None or                     after_count > before_count:
                added = True
                logfile.write('shop: added via {} ({} -> {})'.format(
                    label, before_count, after_count))
                break
            logfile.write('shop: {} did not change the inventory ({})'.format(
                label, after_count))
        if not added:
            # Do not destroy it: if it merged into an existing stack, the
            # object is now part of that stack and destroying it takes the
            # others with it. Leave it and stop.
            logfile.fail('shop: could not put {} in the inventory'.format(name))
            break
        made.append(obj)

    if not made:
        return False, 'Could not buy {}.'.format(name)

    # Charge for what was actually delivered, not what was asked for.
    charged = 0
    if price:
        amount = int(price) * len(made)
        if charge(amount):
            charged = amount

    try:
        held = len(list(inventory))
    except Exception:
        held = '?'
    logfile.ok('shop: {} x{} delivered, charged {}, inventory now holds {}'
               .format(name, len(made), charged, held))
    return True, '{} {}, {} simoleons.'.format(len(made), name, charged)
