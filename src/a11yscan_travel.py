"""Travelling without the map screen.

The old route ran the Sim's own Travel interaction, which opens a Sim picker
and then a map-view picker. Both are readable, but the map screen is a client
panel that does not close itself afterwards - so travelling left you stuck on
a screen the mod cannot dismiss.

There is a direct route. server_commands.sim_commands.push_travel_affordance
pushes objects.terrain.TravelSuperInteraction straight at a destination:

    context = InteractionContext(sim, SOURCE_PIE_MENU, Priority.High,
                                 client=client, pick=None)
    sim.push_super_affordance(super_affordance=TravelSuperInteraction,
                              target=sim, context=context,
                              to_zone_id=<zone id>, world_id=<world id>,
                              lot_name=<name>, friend_account=None)

Two details matter. The argument the command calls `lot_id` is passed as
`to_zone_id` - it is a ZONE id, which is what a11yscan_lots already enumerates.
And `target` must be None: `pick=None` alone is NOT enough (that was tried and
still hit "Cannot Travel from terrain outside of the street"). The test only
works out a position when target or pick is set, and with a Sim as target it
uses the Sim's own position - on the lot, so not in the street. Both None means
no position, so the street check never runs.

No map screen is opened at any point.
"""
import io
import os

import a11yscan_log as logfile

_places = []
_index = 0
_active = False
_last_travel = [0.0]
# Travel is not idempotent, and a second push while one is in flight is how
# the household switcher wedged the client on a loading screen.
COOLDOWN = 20.0


# Places learned from the game itself rather than from our own survey of the
# save: zone id -> (name, world). Kept beside the log so a destination only has
# to be seen once, ever.
_discovered = {}
_discovered_loaded = False
PLACES_FILE = 'a11yscan_places.txt'


def _places_path():
    try:
        return os.path.join(os.path.dirname(logfile.path()), PLACES_FILE)
    except Exception:
        return None


def _load_discovered():
    """Read the learned destinations once per session."""
    global _discovered_loaded
    if _discovered_loaded:
        return
    _discovered_loaded = True
    path = _places_path()
    if not path or not os.path.isfile(path):
        return
    try:
        with io.open(path, encoding='utf-8') as handle:
            for line in handle:
                parts = line.rstrip('\n').split('\t')
                if len(parts) < 2:
                    continue
                try:
                    zone_id = int(parts[0])
                except ValueError:
                    continue
                _discovered[zone_id] = (parts[1],
                                        parts[2] if len(parts) > 2 else '')
        logfile.write('travel: {} destinations remembered from earlier '
                      'sessions'.format(len(_discovered)))
    except Exception as ex:
        logfile.write('travel: could not read {} ({!r})'.format(path, ex))


def _save_discovered():
    path = _places_path()
    if not path:
        return
    try:
        with io.open(path, 'w', encoding='utf-8', newline='\n') as handle:
            for zone_id in sorted(_discovered):
                name, world = _discovered[zone_id]
                handle.write(u'{}\t{}\t{}\n'.format(zone_id, name, world))
    except Exception as ex:
        logfile.write('travel: could not write {} ({!r})'.format(path, ex))


def remember_destinations(pairs, source='the map'):
    """Learn places the game offered that our own survey may not know.

    Called with whatever a map picker had on it. Each row there is somewhere
    the game says this Sim can travel, which is the only authority that keeps
    working when a mod adds somewhere new.
    """
    _load_discovered()
    added = []
    for zone_id, name in pairs or ():
        try:
            zone_id = int(zone_id)
        except (TypeError, ValueError):
            continue
        if not zone_id or zone_id in _discovered:
            continue
        _discovered[zone_id] = (str(name or 'lot {}'.format(zone_id)), '')
        added.append(_discovered[zone_id][0])
    if added:
        logfile.ok('travel: learned {} new destinations from {}: {}'.format(
            len(added), source, ', '.join(added[:6])))
        _save_discovered()
    return len(added)


def active():
    return _active


def places():
    """The destinations from the last load, for reporting and testing."""
    return list(_places)


def load():
    """Everywhere you could go, newest survey each time."""
    global _places, _index
    import a11yscan_lots as lots
    _places = []
    _index = 0
    try:
        import services
        persistence = services.get_persistence_service()
        here = services.current_zone_id()
    except Exception as ex:
        logfile.fail('travel: no persistence service ({!r})'.format(ex))
        return 0
    for entry in lots.survey():
        zone_id = entry.get('zone_id')
        if not zone_id or zone_id == here:
            continue          # no point offering the lot you are stood on
        world_id = None
        try:
            world_id = persistence.get_world_id_from_zone(zone_id)
        except Exception:
            world_id = None
        _places.append({
            'name': entry['name'],
            'world': entry['world'],
            'zone_id': zone_id,
            'world_id': world_id,
            'occupied': entry.get('occupied'),
        })
    # Anything the game has offered on a map screen and the survey above did
    # not produce. Normally none: the survey is a superset. It stops being one
    # the day a mod adds somewhere the save does not describe the usual way.
    _load_discovered()
    known = set(place['zone_id'] for place in _places)
    for zone_id, (name, world) in sorted(_discovered.items()):
        if zone_id in known or zone_id == here:
            continue
        # The world id is only needed by the game's own travel command, and
        # a learned zone still has one - ask for it rather than travelling
        # with a hole in the arguments.
        learned_world_id = None
        try:
            learned_world_id = persistence.get_world_id_from_zone(zone_id)
        except Exception:
            learned_world_id = None
        _places.append({
            'name': name,
            'world': world or 'learned from the map',
            'zone_id': zone_id,
            'world_id': learned_world_id,
            'occupied': None,
        })
        logfile.write('travel: offering {} (zone {}), which the survey did '
                      'not list'.format(name, zone_id))
    _load_companions()
    logfile.write('travel: {} destinations'.format(len(_places)))
    return len(_places)


def open_menu():
    global _active
    count = load()
    if not count:
        return 'Could not find anywhere to go. The log has the reason.'
    _active = True
    return ('Travel. Up and down to browse. The first entries are who comes '
            'with you - enter to bring them or leave them. Then the places: '
            'enter to go. Backspace to stop. {}'.format(describe()))


def close_menu():
    global _active
    _active = False
    return 'Travel closed.'


def describe():
    if not _entry_count():
        return 'Nowhere to go.'
    return _describe_entry(_index % _entry_count())


def next_place(step=1):
    global _index
    if not _entry_count():
        return 'Nowhere to go.'
    _index = (_index + step) % _entry_count()
    return describe()


def _reason_of(result):
    """Whatever the game will tell us about why a push did not take."""
    parts = []
    for attr in ('reason', 'result', 'test_result', 'enqueue_result'):
        try:
            value = getattr(result, attr, None)
        except Exception:
            continue
        if value is not None:
            parts.append('{}={}'.format(attr, str(value)[:120]))
    return ', '.join(parts) or repr(result)[:160]


def _context(sim):
    """The context the game builds for travel: pie menu source, high priority."""
    import services
    from interactions.context import InteractionContext
    from interactions.priority import Priority
    client = services.client_manager().get_first_client()
    return InteractionContext(sim, InteractionContext.SOURCE_PIE_MENU,
                              Priority.High, client=client, pick=None)


def _go_home_affordance(sim):
    """The Sim's own Go Home interaction, and the parameters it carries.

    Go Home works. It is a travel interaction that already knows where it is
    going, pushed the way the game pushes it - which is the one travel route
    in this game that has never failed here. If the destination can be
    overridden, the same mechanism travels anywhere without a map.
    """
    import a11yscan_actions as actions
    try:
        choices = actions.choices_for(sim)
    except Exception as ex:
        logfile.fail('travel: could not list self interactions ({!r})'.format(ex))
        return None, {}
    for choice in choices:
        if 'go home' not in choice.label.lower():
            continue
        params = {}
        try:
            params = dict(getattr(choice.aop, 'interaction_parameters', None) or {})
        except Exception:
            params = {}
        logfile.write('travel: go-home affordance {} carries {}'.format(
            getattr(choice.affordance, '__name__', '?'),
            {k: str(v)[:60] for k, v in params.items()}))
        return choice.affordance, params
    logfile.write('travel: no go-home interaction offered right now')
    return None, {}


def _is_picker(affordance):
    """Does running this put a picker on screen instead of travelling?

    Every step of the travel chain is a picker until the last one: Travel...
    asks who is coming, its continuation asks where to. Pushing a picker is
    how the map screen ended up opening from the "no map" command.
    """
    for attr in ('picker_rows_gen', 'picker_dialog', '_create_dialog'):
        if getattr(affordance, attr, None) is not None:
            return True
    name = (getattr(affordance, '__name__', '') or '').lower()
    if 'picker' in name:
        return True
    # Travel_DummyInteractions_Phone_TravelWith has no picker rows and no
    # continuations, and pushing it opened the map anyway: it shows the travel
    # dialog directly, the same way TravelSuperInteraction does.
    return 'dummyinteractions' in name or 'travelwith' in name


def _continuations_of(affordance):
    out = []
    for attr in ('actor_continuation', 'target_continuation'):
        for entry in getattr(affordance, attr, None) or ():
            nested = getattr(entry, 'affordance', None)
            if nested is not None:
                out.append(nested)
    return out


# Who is coming. The Sim picker step used to ask this and then open the map,
# so the two questions are asked in one list here instead.
_companions = []


def _load_companions():
    """Household Sims standing on this lot, and whether they are coming.

    Only Sims on the lot: the game says so itself when a picked continuation
    gets someone who is not here - "You must pick on lot sims for a tuned
    'picked continuation' to function."
    """
    global _companions
    keep = dict((entry['id'], entry['coming']) for entry in _companions)
    _companions = []
    try:
        import services
        import a11yscan_world as world
        household = services.active_household()
        household_id = getattr(household, 'id', None)
        active = world.active_sim()
        active_id = getattr(active, 'id', None)
        manager = services.sim_info_manager()
    except Exception as ex:
        logfile.write('travel: no companions available ({!r})'.format(ex))
        return
    sims = []
    for attr in ('instanced_sims_on_active_lot_gen', 'instanced_sims_gen'):
        try:
            getter = getattr(manager, attr, None)
            if getter is not None:
                sims = list(getter())
                break
        except Exception:
            continue
    # Everyone here, not only your own household. The person you came to the
    # bar with is the whole reason to bring anyone, and they are exactly who
    # a household-only list leaves behind - the game's own Travel With picker
    # offers anybody present.
    for sim in sims:
        info = getattr(sim, 'sim_info', None) or sim
        sim_id = getattr(sim, 'id', None)
        if not sim_id or sim_id == active_id:
            continue
        name = '{} {}'.format(getattr(info, 'first_name', '') or '',
                              getattr(info, 'last_name', '') or '').strip()
        mine = getattr(info, 'household_id', None) == household_id
        _companions.append({'id': sim_id, 'name': name or 'a Sim',
                            'mine': mine,
                            'coming': keep.get(sim_id, False)})
    # Your own household first, then everyone else, each alphabetically.
    _companions.sort(key=lambda entry: (not entry['mine'],
                                        entry['name'].lower()))
    logfile.write('travel: {} Sims here to bring ({} of them yours)'.format(
        len(_companions), sum(1 for c in _companions if c['mine'])))


def _entry_count():
    return len(_companions) + len(_places)


def _entry_at(index):
    """('companion', entry) or ('place', entry) for one line of the list."""
    if index < len(_companions):
        return 'companion', _companions[index]
    return 'place', _places[index - len(_companions)]


def _describe_entry(index):
    kind, entry = _entry_at(index)
    if kind == 'companion':
        return '{}{}, coming: {}. {} of {}.'.format(
            entry['name'], '' if entry.get('mine') else ' (not your household)',
            'yes' if entry['coming'] else 'no', index + 1, _entry_count())
    parts = [entry['name'], 'in {}'.format(entry['world'])]
    if entry.get('occupied'):
        parts.append('someone lives here')
    coming = [c['name'] for c in _companions if c['coming']]
    if coming:
        parts.append('with {}'.format(', '.join(coming)))
    parts.append('{} of {}'.format(index + 1, _entry_count()))
    return ', '.join(parts)


def toggle_or_go():
    """Enter: flip a companion, or travel to a destination."""
    if not _entry_count():
        return 'Nowhere to go.'
    kind, entry = _entry_at(_index % _entry_count())
    if kind == 'companion':
        entry['coming'] = not entry['coming']
        return '{} is {} coming.'.format(
            entry['name'], 'now' if entry['coming'] else 'not')
    return go()


def _companion_ids():
    return [entry['id'] for entry in _companions if entry['coming']]


def _map_picker_continuations():
    """What the MAP picker runs after you confirm - read from tuning.

    The chain from the Sim's own menu stops at the interaction that opens the
    map, and it has no continuations of its own, so following it further finds
    nothing. But every tuned map picker is loaded whether or not one is on
    screen, and each carries the continuation it would push on confirm:

        self.push_tunable_continuation(self.actor_continuation,
                                       picked_zone_ids=picked)

    Reading those out of the interaction manager gets the last link of the
    chain without opening the screen we are trying to avoid.
    """
    out = []
    try:
        import services
        import sims4.resources
        from interactions.base.picker_interaction import MapViewPickerInteraction
        manager = services.get_instance_manager(
            sims4.resources.Types.INTERACTION)
    except Exception as ex:
        logfile.fail('travel: no map picker tuning ({!r})'.format(ex))
        return out
    pickers = 0
    for affordance in manager.types.values():
        try:
            if not issubclass(affordance, MapViewPickerInteraction):
                continue
        except Exception:
            continue
        pickers += 1
        picker_name = getattr(affordance, '__name__', '?')
        for nested in _continuations_of(affordance):
            name = getattr(nested, '__name__', '?')
            logfile.write('travel: map picker {} runs {} on confirm'.format(
                picker_name, name))
            if _is_picker(nested):
                continue
            out.append((_travel_rank(picker_name, name), name, nested))
    # Order matters more than it looks. All of these travel, because they all
    # create a situation at the chosen lot - but "ask on date" also starts a
    # date, and "invite to" brings people along. Going somewhere on your own
    # should not quietly do either, so the plainest travel wins.
    out.sort(key=lambda item: item[0])
    logfile.write('travel: {} tuned map pickers, {} travel continuations, '
                  'best is {}'.format(pickers, len(out),
                                      out[0][1] if out else 'none'))
    return [(name, affordance) for _rank, name, affordance in out]


def _travel_rank(picker_name, continuation_name):
    """Lower is better. Plain solo travel first, side effects last."""
    picker = picker_name.lower()
    nested = continuation_name.lower()
    if ':' in picker_name:
        return 90        # another mod's picker; ours to borrow only as a last resort
    if 'travel' in picker and 'solo' in picker:
        return 0
    if 'travel' in picker:
        return 10
    if 'date' in nested or 'date' in picker:
        return 70        # starts a date as well as travelling
    if 'invite' in nested or 'invite' in picker:
        return 60        # brings other Sims with you
    return 40


def _travel_continuations(sim, depth=4):
    """The interaction at the END of the travel chain - the one that travels.

    TravelSuperInteraction only shows the map. The map picker only pushes a
    continuation. So the destination lands, as picked_zone_ids, on whatever
    sits at the bottom of the chain:

        Travel...  (pick who comes)  -> continuation
          map picker (pick where)    -> continuation
            the interaction that travels

    Walking one link found the map picker and opened the map, which is the
    thing we are trying not to do. So the chain is followed to the end, and
    anything that would draw a picker is offered last.
    """
    import a11yscan_actions as actions
    try:
        choices = actions.choices_for(sim)
    except Exception as ex:
        logfile.fail('travel: could not list self interactions ({!r})'.format(ex))
        return []
    roots = []
    for choice in choices:
        if 'travel' in (choice.label or '').lower():
            roots.append((choice.label, choice.affordance))
    if not roots:
        logfile.write('travel: no travel interaction to follow')
        return []

    plain, pickers = [], []
    seen = set()
    frontier = [(label, affordance, 0) for label, affordance in roots]
    while frontier:
        label, affordance, level = frontier.pop(0)
        name = getattr(affordance, '__name__', '?')
        if name in seen or level > depth:
            continue
        seen.add(name)
        picker = _is_picker(affordance)
        logfile.write('travel: chain depth {} {} ({})'.format(
            level, name, 'picker' if picker else 'not a picker'))
        if level:
            (pickers if picker else plain).append((name, affordance))
        for nested in _continuations_of(affordance):
            frontier.append((label, nested, level + 1))
    # Deepest first: the end of the chain is the one that travels.
    plain.reverse()
    logfile.write('travel: {} non-picker continuations, {} pickers'.format(
        len(plain), len(pickers)))
    return plain + pickers


def _search_for_street(terrain, steps=14, per_ring=16):
    """Walk outward from the Sim until a position is in the street.

    Nothing in the game hands out "a point on the road", and every spawn point
    belongs to the lot, so the only way to get one is to ask about candidate
    spots until the game says yes. A ring of directions at growing distance
    finds the kerb of any normal lot within a few dozen metres.
    """
    import math
    import a11yscan_world as world
    sim = world.active_sim()
    if sim is None:
        return None
    try:
        from sims4.math import Vector3
        origin = sim.position
    except Exception as ex:
        logfile.write('travel: no position to search from ({!r})'.format(ex))
        return None
    tested = 0
    for step in range(1, steps + 1):
        radius = step * 8.0
        for index in range(per_ring):
            angle = (2.0 * math.pi * index) / per_ring
            spot = Vector3(origin.x + radius * math.cos(angle),
                           origin.y,
                           origin.z + radius * math.sin(angle))
            tested += 1
            try:
                if terrain.is_position_in_street(spot):
                    logfile.ok('travel: found street at {} after {} '
                               'tries'.format(spot, tested))
                    return spot
            except Exception:
                continue
    logfile.write('travel: no street within {:.0f} metres after {} '
                  'tries'.format(steps * 8.0, tested))
    return None


def _street_position():
    """A position the game agrees is in the street, or None.

    TravelSuperInteraction refuses unless the position it derives is in the
    street:

        if position is not None and not is_position_in_street(position):
            return TestResult(False, 'Cannot Travel from terrain outside of
                                      the street!')

    Standing on your own lot never satisfies that, which is why every push
    with the Sim as target was refused. Spawn points sit at the lot's street
    edge - they are where visitors arrive - so one of those is what the real
    flow effectively uses when you click the road.
    """
    try:
        import services
        import terrain
    except Exception as ex:
        logfile.write('travel: no terrain module ({!r})'.format(ex))
        return None, None
    candidates = []
    try:
        zone = services.current_zone()
        point = zone.get_spawn_point()
        if point is not None:
            candidates.append(('zone spawn point', point))
    except Exception as ex:
        logfile.write('travel: no zone spawn point ({!r})'.format(ex))
    try:
        for point in zone.spawn_points_gen():
            candidates.append(('spawn point', point))
    except Exception:
        pass
    for label, point in candidates[:12]:
        position = None
        for getter in (lambda p=point: p.get_approximate_center(),
                       lambda p=point: p.center,
                       lambda p=point: p.position):
            try:
                position = getter()
            except Exception:
                continue
            if position is not None:
                break
        if position is None:
            continue
        try:
            if terrain.is_position_in_street(position):
                logfile.write('travel: {} at {} is in the street'.format(
                    label, position))
                surface = None
                for getter in (lambda p=point: p.routing_surface,
                               lambda p=point: p.get_routing_surface()):
                    try:
                        surface = getter()
                    except Exception:
                        continue
                    if surface is not None:
                        break
                return position, surface
        except Exception as ex:
            logfile.write('travel: street test raised ({!r})'.format(ex))

    # Spawn points are all ON the lot - every one of them tested False - so
    # the street has to be found by looking for it. Step outward from the Sim
    # in a ring of directions until the game agrees a spot is road.
    found = _search_for_street(terrain)
    if found is not None:
        return found, None

    logfile.write('travel: no spawn point was in the street')
    return None, None


def _street_context(sim):
    """A context whose pick sits in the street, so the travel test passes."""
    import services
    from interactions.context import InteractionContext
    from interactions.priority import Priority
    from server.pick_info import PickInfo, PickType
    position, surface = _street_position()
    if position is None:
        return None
    client = services.client_manager().get_first_client()
    try:
        level = int(getattr(sim, 'level', 0) or 0)
    except Exception:
        level = 0
    try:
        lot_id = int(services.active_lot().lot_id)
    except Exception:
        lot_id = 0
    pick = PickInfo(pick_type=PickType.PICK_TERRAIN, target=None,
                    location=position, routing_surface=surface,
                    lot_id=lot_id, level=level)
    return InteractionContext(sim, InteractionContext.SOURCE_PIE_MENU,
                              Priority.High, client=client, pick=pick)


def _travel_affordances(limit=12):
    """Every tuned travel interaction, not just the one on the pie menu.

    Go Home is only offered when you are away from home, so borrowing it off
    the menu fails in the exact place people travel FROM. The tuning is still
    loaded either way, so the classes are collected straight out of the
    interaction manager instead.
    """
    found = []
    try:
        import services
        import sims4.resources
        from objects.terrain import TravelSuperInteraction
        manager = services.get_instance_manager(
            sims4.resources.Types.INTERACTION)
    except Exception as ex:
        logfile.fail('travel: no interaction manager ({!r})'.format(ex))
        return found
    # The base interaction itself, always. The sweep below looks for tuned
    # SUBCLASSES and found none at all, so the one class the game's own travel
    # command uses was never actually pushed - which is the whole reason we
    # have a refusal with no reason attached.
    found.append(('TravelSuperInteraction', TravelSuperInteraction))
    for affordance in manager.types.values():
        try:
            if not issubclass(affordance, TravelSuperInteraction):
                continue
        except Exception:
            continue
        name = getattr(affordance, '__name__', '') or '?'
        lowered = name.lower()
        # Home first: it is the one we know travels. Then anything else that
        # is plainly a travel, and nothing that looks like a special case.
        if 'home' in lowered:
            found.insert(0, (name, affordance))
        elif any(word in lowered for word in ('travel', 'goto', 'visit')):
            found.append((name, affordance))
    logfile.write('travel: {} tuned travel interactions: {}'.format(
        len(found), ', '.join(n for n, _a in found[:10])))
    return found[:limit]


def travel_to_zone(zone_id, name='there'):
    """Travel to a zone by id, for callers holding a lot rather than a menu row."""
    world_id = None
    try:
        import services
        world_id = services.get_persistence_service().get_world_id_from_zone(
            zone_id)
    except Exception as ex:
        logfile.write('travel: no world id for zone {} ({!r})'.format(
            zone_id, ex))
    return travel_to({'name': name, 'world': '', 'zone_id': zone_id,
                      'world_id': world_id, 'occupied': False})


def go():
    """Travel to the destination under the cursor. No map screen.

    Two routes, because the obvious one does not work. The game's own
    travel_to_specific_location pushes objects.terrain.TravelSuperInteraction
    and that push returns false here every time. The Sim's own Go Home
    interaction, by contrast, travels reliably - so the second route borrows
    that affordance and points it somewhere else.
    """
    if not _places:
        return 'Nowhere to go.'
    kind, place = _entry_at(_index % _entry_count())
    if kind != 'place':
        return 'That is a travel companion, not a destination.'
    return travel_to(place)


def travel_to(place):
    """Travel to one place. Separate from the menu so anything can call it.

    Moving house wants to travel to the new home straight afterwards, and it
    has a lot rather than a menu position to work from.
    """
    import time
    since = time.monotonic() - _last_travel[0]
    if since < COOLDOWN:
        logfile.write('travel: refused, {:.1f}s since the last one'.format(since))
        return 'Already travelling. Wait for the lot to load.'

    try:
        import services
        import a11yscan_world as world
        sim = world.active_sim()
        client = services.client_manager().get_first_client()
        connection = getattr(client, 'id', None)
    except Exception as ex:
        logfile.fail('travel: no sim or client ({!r})'.format(ex))
        return 'Could not travel.'
    if sim is None:
        return 'No active Sim.'

    logfile.write('travel: heading for {!r} zone={} world={}'.format(
        place['name'], place['zone_id'], place['world_id']))

    # Route one: the game's own command. Cheap to try and it is the supported
    # path, even though it has refused every time so far.
    try:
        from server_commands.sim_commands import travel_to_specific_location
        result = travel_to_specific_location(
            None, place['zone_id'], place['world_id'], place['name'],
            _connection=connection)
        logfile.write('travel: game command returned {!r}'.format(result))
        if result is not False:
            _last_travel[0] = time.monotonic()
            logfile.ok('travel: {!r} via the game command'.format(place['name']))
            close_menu()
            return 'Travelling to {}.'.format(place['name'])
    except Exception as ex:
        logfile.write('travel: game command raised {!r}'.format(ex))

    # Route two: push a travel interaction ourselves, so the refusal has a
    # reason attached. The game's command throws its reason away.
    # The continuation is what travels, so it goes first. Everything after it
    # is a fallback kept only because it costs nothing to try.
    candidates = []
    zone_param = {'picked_zone_ids': frozenset((place['zone_id'],))}
    coming = _companion_ids()
    if coming:
        zone_param['picked_item_ids'] = frozenset(coming)
        logfile.write('travel: bringing {}'.format(
            ', '.join(c['name'] for c in _companions if c['coming'])))
    # The map picker's own continuation first: that is the last link, the one
    # that travels. The chain from the Sim's menu only reaches the interaction
    # that OPENS the map, which is why pushing it opened the map.
    for name, affordance in _map_picker_continuations():
        candidates.append(('continuation ' + name, affordance, zone_param))
    for name, affordance in _travel_continuations(sim):
        candidates.append(('continuation ' + name, affordance, zone_param))
    home_affordance, home_params = _go_home_affordance(sim)
    if home_affordance is not None:
        candidates.append(('go home, borrowed', home_affordance, home_params))
    for name, affordance in _travel_affordances():
        candidates.append((name, affordance, {}))

    overrides = {'to_zone_id': place['zone_id'],
                 'world_id': place['world_id'],
                 'lot_name': place['name']}
    tried = 0
    for name, affordance, params in candidates:
        call_params = dict(params)
        call_params.update(overrides)
        # The target decides whether the street test runs at all:
        #
        #   position, surface, result = _get_target_position_surface_and_test_
        #       off_lot(target, context)
        #   if position is not None and not is_position_in_street(position):
        #       return TestResult(False, 'Cannot Travel from terrain outside
        #                                 of the street!')
        #
        # With the Sim as target the position is where he stands - on the lot,
        # never in the street - so it always refuses. With no target and no
        # pick there is no position, so the check is skipped. That shape was
        # tried once before and failed differently, but every one of those
        # attempts also passed friend_account=None, which raises inside the
        # interaction. Without it, this combination has never actually run.
        shapes = []
        if name.startswith('continuation '):
            # picked_zone_ids IS the destination for these - adding to_zone_id
            # and the rest would only confuse an interaction that never asked
            # for them.
            shapes.append((name + ', as the game pushes it', sim, params, False))
            shapes.append((name + ', no target', None, params, False))
            for shape, push_target, kwargs, use_street in shapes:
                tried += 1
                try:
                    context = _context(sim)
                    result = sim.push_super_affordance(
                        super_affordance=affordance, target=push_target,
                        context=context, **kwargs)
                except Exception as ex:
                    logfile.write('travel: {} raised {!r}'.format(shape, ex))
                    continue
                logfile.write('travel: {} -> {}'.format(
                    shape, _reason_of(result)))
                if bool(result) or bool(getattr(result, 'result', False)):
                    _last_travel[0] = time.monotonic()
                    logfile.ok('travel: {!r} via {}'.format(place['name'], shape))
                    close_menu()
                    return 'Travelling to {}.'.format(place['name'])
            continue
        # A pick in the street satisfies the test instead of dodging it, and
        # dodging it - no target, no pick - broke inside the interaction
        # instead.
        shapes.append(('street pick, no target', None, call_params, True))
        shapes.append(('street pick, target sim', sim, call_params, True))
        for target_label, target in (('no target', None), ('target sim', sim)):
            shapes.append(('{}, with lot name'.format(target_label),
                           target, call_params, False))
            shapes.append(('{}, zone and world only'.format(target_label),
                           target, {'to_zone_id': place['zone_id'],
                                    'world_id': place['world_id']}, False))
        for shape, push_target, kwargs, use_street in shapes:
            tried += 1
            try:
                context = _street_context(sim) if use_street else _context(sim)
                if context is None:
                    logfile.write('travel: {} skipped, no street position '
                                  'found'.format(shape))
                    continue
                result = sim.push_super_affordance(
                    super_affordance=affordance, target=push_target,
                    context=context, **kwargs)
            except Exception as ex:
                logfile.write('travel: {} ({}) raised {!r}'.format(
                    name, shape, ex))
                continue
            logfile.write('travel: {} ({}) -> {}'.format(
                name, shape, _reason_of(result)))
            # push_super_affordance swallows the test result. Running the test
            # ourselves is the only way to see WHY the game says no.
            try:
                from interactions.aop import AffordanceObjectPair
                probe = AffordanceObjectPair(affordance, push_target,
                                             affordance, None, **kwargs)
                verdict = probe.test(_context(sim))
                logfile.write('travel: {} test says {} ({})'.format(
                    name, bool(verdict),
                    str(getattr(verdict, 'reason', verdict))[:160]))
            except Exception as ex:
                logfile.write('travel: {} test raised {!r}'.format(name, ex))
            # An EnqueueResult is only truthy when the interaction also
            # EXECUTED, and travel takes the queue over - so being enqueued is
            # the success worth having, not the overall truthiness.
            enqueued = bool(result) or bool(getattr(result, 'result', False))
            if enqueued:
                _last_travel[0] = time.monotonic()
                logfile.ok('travel: {!r} via {} ({})'.format(
                    place['name'], name, shape))
                close_menu()
                return 'Travelling to {}.'.format(place['name'])
    logfile.fail('travel: {} attempts, none would travel to {!r}'.format(
        tried, place['name']))
    return 'Could not travel there. The log has the reasons.'
