"""Lots and worlds, without the lot-selection screen.

The New Game flow ends at a lot picker that cannot be reached without sight,
but nothing in it is client-only. PersistenceService knows every zone in the
save, which world and region each belongs to, and - through
get_household_id_from_zone_id - which ones are empty. Household.move_into_zone
does the placing. So choosing where to live is an ordinary keyboard list.

This module is READ-ONLY. It lists and describes; moving a household in is a
separate step that changes the save, and belongs with the code that owns that
risk.

Nothing here assumes the shape of the lot and zone protobufs. They are game
data structures whose field names are not in the Python scripts, so the first
listing logs what a proto actually carries and the name lookup tries several
fields rather than guessing one.
"""
import a11yscan_log as logfile

# Field names a zone or lot proto might use for its display name, best first.
NAME_FIELDS = ('name', 'lot_name', 'zone_name', 'lot_description_name',
               'house_description_name', 'venue_name')
SIZE_FIELDS = ('lot_size', 'size', 'lot_template_size', 'width', 'depth')

_structure_logged = False


def _persistence():
    import services
    return services.get_persistence_service()


def _first_field(proto, fields):
    for field in fields:
        try:
            value = getattr(proto, field, None)
        except Exception:
            continue
        if value:
            return value
    return None


def _log_structure(zone_proto, lot_proto):
    """Record the proto shape once, so field names stop being guesswork."""
    global _structure_logged
    if _structure_logged:
        return
    _structure_logged = True
    for label, proto in (('zone', zone_proto), ('lot', lot_proto)):
        if proto is None:
            logfile.write('lots: no {} proto to inspect'.format(label))
            continue
        try:
            # Only the lower-case fields; the SHOUTY protobuf metadata
            # crowded the real names out of the previous dump.
            fields = [n for n in dir(proto)
                      if not n.startswith('_') and n.islower()]
            logfile.write('lots: {} proto fields: {}'.format(
                label, ', '.join(fields)))
        except Exception as ex:
            logfile.write('lots: could not inspect {} proto ({!r})'.format(label, ex))


def _neighborhood_name(persistence, zone_proto, cache):
    """The world's name, via the neighbourhood the zone belongs to."""
    try:
        neighborhood_id = getattr(zone_proto, 'neighborhood_id', None)
    except Exception:
        return None
    if not neighborhood_id:
        return None
    if neighborhood_id in cache:
        return cache[neighborhood_id]
    name = None
    try:
        proto = persistence.get_neighborhood_proto_buff(neighborhood_id)
        name = _first_field(proto, ('name', 'neighborhood_name'))
        if name is None and proto is not None and not cache:
            logfile.write('lots: neighbourhood proto fields: {}'.format(
                ', '.join(n for n in dir(proto)
                          if not n.startswith('_') and n.islower())))
    except Exception as ex:
        if not cache:
            logfile.write('lots: neighbourhood lookup failed ({!r})'.format(ex))
    cache[neighborhood_id] = name
    return name


def _world_names():
    """Region display names, so lots can be grouped by world rather than by id."""
    names = {}
    try:
        import services
        import sims4.resources
        import a11yscan_dialogs as dialogs
        manager = services.get_instance_manager(sims4.resources.Types.REGION)
        regions = list(manager.types.values())
        if regions:
            logfile.write('lots: region fields: {}'.format(
                ', '.join(n for n in dir(regions[0]) if not n.startswith('_'))[:400]))
        for region in regions:
            label = None
            for attr in ('name', 'display_name', 'region_name'):
                try:
                    label = dialogs.loc_text(getattr(region, attr, None))
                except Exception:
                    label = None
                if label:
                    break
            if not label:
                label = getattr(region, '__name__', None)
            if not label:
                continue
            for attr in ('guid64', 'guid', 'region_id', 'world_id'):
                try:
                    key = getattr(region, attr, None)
                except Exception:
                    continue
                if key is not None:
                    names[key] = label
            # A region can span several worlds, so index those too.
            try:
                for world in (getattr(region, 'world_ids', None) or ()):
                    names[world] = label
            except Exception:
                pass
    except Exception as ex:
        logfile.write('lots: region names unavailable ({!r})'.format(ex))
    return names


def survey():
    """Every zone in the save: (label, zone_id, world_id, occupied)."""
    entries = []
    try:
        persistence = _persistence()
    except Exception as ex:
        logfile.fail('lots: no persistence service ({!r})'.format(ex))
        return entries
    if persistence is None:
        logfile.fail('lots: persistence service is None')
        return entries

    try:
        zone_ids = list(persistence.get_zone_ids())
    except Exception as ex:
        logfile.fail('lots: get_zone_ids failed ({!r})'.format(ex))
        return entries

    regions = _world_names()
    neighborhoods = {}
    logfile.write('lots: {} zones, {} named regions'.format(
        len(zone_ids), len(regions)))

    for zone_id in zone_ids:
        zone_proto = None
        lot_proto = None
        try:
            zone_proto = persistence.get_zone_proto_buff(zone_id)
        except Exception:
            zone_proto = None
        lot_id = None
        try:
            lot_id = persistence.get_lot_id_from_zone_id(zone_id)
            if lot_id:
                lot_proto = persistence.get_lot_proto_buff(lot_id)
        except Exception:
            lot_proto = None
        _log_structure(zone_proto, lot_proto)

        household_id = None
        try:
            household_id = persistence.get_household_id_from_zone_id(zone_id)
        except Exception:
            household_id = None

        world_id = None
        try:
            world_id = persistence.get_world_id_from_zone(zone_id)
        except Exception:
            world_id = None
        region_id = None
        try:
            if world_id is not None:
                region_id = persistence.get_region_id_from_world_id(world_id)
        except Exception:
            region_id = None

        name = _first_field(zone_proto, NAME_FIELDS) or \
            _first_field(lot_proto, NAME_FIELDS)
        if not name:
            name = 'lot {}'.format(zone_id)
        # The zone proto knows its own neighbourhood. That beats matching
        # region tuning by id, which returned object component names.
        proto_world = _neighborhood_name(persistence, zone_proto, neighborhoods)
        world = proto_world or regions.get(region_id) or regions.get(world_id) or (
            'world {}'.format(world_id) if world_id is not None else 'unknown world')
        rooms = None
        beds = baths = None
        try:
            beds = int(getattr(zone_proto, 'bedroom_count', 0) or 0)
            baths = int(getattr(zone_proto, 'bathroom_count', 0) or 0)
            if beds or baths:
                rooms = '{} bed, {} bath'.format(beds, baths)
        except Exception:
            beds = baths = None
            rooms = None
        entries.append({
            'name': str(name),
            'zone_id': zone_id,
            'world': world,
            'occupied': bool(household_id),
            'size': rooms or _first_field(lot_proto, SIZE_FIELDS),
            'beds': beds,
            'baths': baths,
            'description': _first_field(zone_proto, ('description',)),
        })
    entries.sort(key=lambda e: (e['world'].lower(), e['name'].lower()))
    return entries


def empty_lots():
    return [entry for entry in survey() if not entry['occupied']]


def describe(entry):
    parts = [entry['name'], 'in {}'.format(entry['world'])]
    if entry['size']:
        parts.append(str(entry['size']))
    parts.append('occupied' if entry['occupied'] else 'empty')
    return ', '.join(parts)


def move_in(household, zone_id):
    """Give a household a home lot. Changes the save; logs every step."""
    if household is None:
        return False, 'No household to move.'
    name = getattr(household, 'name', None) or 'the household'
    try:
        household.move_into_zone(zone_id)
    except Exception as ex:
        logfile.fail('lots: move_into_zone({}) raised {!r}'.format(zone_id, ex))
        return False, 'Could not move in there.'
    logfile.ok('lots: {} moved into zone {}'.format(name, zone_id))
    # Confirm against the save rather than trusting the call to have worked.
    try:
        persistence = _persistence()
        owner = persistence.get_household_id_from_zone_id(zone_id)
        if owner and owner == getattr(household, 'id', None):
            logfile.ok('lots: zone {} now owned by the new household'.format(zone_id))
        else:
            logfile.write('lots: zone {} owner reads {!r} after the move'.format(
                zone_id, owner))
    except Exception as ex:
        logfile.write('lots: could not verify ownership ({!r})'.format(ex))
    return True, 'Moved in.'


def move_targets():
    """Lots the active household could move into.

    Moving house is not a map picker - the twenty tuned map pickers in this
    game are travel, dating, invites and lot ownership, and none of them is
    this - so there is no dialog to read and none to suppress. It is the
    client's own Manage Worlds screen, which the mod cannot reach at all.
    What it CAN do is the move itself, which is what this list is for.

    Empty lots first: moving onto an occupied one evicts whoever lives there,
    and that should take some scrolling to reach rather than one stray Enter.
    """
    here = None
    try:
        import services
        here = services.current_zone_id()
    except Exception:
        here = None
    free, taken = [], []
    for entry in survey():
        if not entry.get('zone_id') or entry['zone_id'] == here:
            continue
        (taken if entry.get('occupied') else free).append(entry)
    free.sort(key=lambda e: (e['world'].lower(), e['name'].lower()))
    taken.sort(key=lambda e: (e['world'].lower(), e['name'].lower()))
    logfile.write('lots: {} empty and {} occupied lots to move to'.format(
        len(free), len(taken)))
    return free + taken


def describe_move_target(entry):
    parts = [entry['name'], 'in {}'.format(entry['world'])]
    parts.append(_rooms_phrase(entry))
    parts.append('occupied, moving here evicts them' if entry.get('occupied')
                 else 'empty lot')
    return ', '.join(parts)


def _rooms_phrase(entry):
    """How big the house is, in the words the game itself counts in.

    bedroom_count and bathroom_count sit on the zone proto, so this is the
    game's own answer rather than anything counted by hand. Zero of both means
    bare land, which is worth saying outright - it reads very differently from
    a house whose counts simply never got recorded.
    """
    beds = entry.get('beds')
    baths = entry.get('baths')
    if beds is None and baths is None:
        size = entry.get('size')
        return size if size else 'size unknown'
    if not beds and not baths:
        return 'no rooms built yet'
    return '{} bedroom{}, {} bathroom{}'.format(
        beds or 0, '' if beds == 1 else 's',
        baths or 0, '' if baths == 1 else 's')


def _household_name(household):
    name = getattr(household, 'name', None)
    return str(name) if name else 'another household'


def claim_lot(zone_id=None, household=None):
    """Make a lot actually belong to a household, and check that it did.

    move_into_zone sets home_zone_id and is SUPPOSED to hand ownership over -
    its body calls set_household_lot_ownership - but ownership lives in the
    ZONE's proto rather than on the household, and it does not always reach it.
    A household can therefore live somewhere the game does not think is theirs,
    which looks like a normal house right up until build mode refuses to open.

    Two things make this fiddly, and both were found the hard way:

      * set_household_lot_ownership takes zone_id as a KEYWORD argument.
        Passing it positionally raises TypeError, which the first version of
        this did - the call never ran at all.
      * A lot can already be owned by somebody else, and setting our ownership
        does not evict them. The old owner is cleared first, by name, and said
        out loud, because quietly taking someone's house is not something to do
        without mentioning it.
    """
    import services
    if household is None:
        household = services.active_household()
    if household is None:
        return False, 'Could not find your household.'
    if zone_id is None:
        try:
            zone_id = services.current_zone_id()
        except Exception as ex:
            logfile.fail('lots: no current zone ({!r})'.format(ex))
            return False, 'No lot is loaded.'

    def owner_of():
        try:
            return services.get_persistence_service(
                ).get_household_id_from_zone_id(zone_id)
        except Exception as ex:
            logfile.write('lots: could not read the owner ({!r})'.format(ex))
            return None

    mine_id = getattr(household, 'id', None)
    evicted = None
    before = owner_of()
    if before and before != mine_id:
        try:
            other = services.household_manager().get(before)
        except Exception:
            other = None
        if other is not None:
            evicted = _household_name(other)
            try:
                other.clear_household_lot_ownership()
                logfile.write('lots: cleared {!r} off zone {}'.format(
                    evicted, zone_id))
            except Exception as ex:
                logfile.write('lots: could not clear the old owner ({!r})'.format(ex))

    tried = []
    for label, call in (
            ('set_household_lot_ownership(zone_id=)',
             lambda: household.set_household_lot_ownership(zone_id=zone_id)),
            ('move_into_zone', lambda: household.move_into_zone(zone_id))):
        try:
            call()
            tried.append(label)
        except Exception as ex:
            logfile.write('lots: {} raised {!r}'.format(label, ex))
        if owner_of() == mine_id:
            break

    # The venue owner is a separate field from the household deed, used for
    # businesses, and a residential lot should not carry one. A stale one left
    # by a previous owner makes the client treat the lot as somebody else's
    # business, which blocks build mode on that lot alone.
    try:
        import build_buy
        venue_owner = build_buy.get_current_venue_owner_id()
        if venue_owner and venue_owner != mine_id:
            try:
                build_buy.clear_venue_owner(zone_id, venue_owner)
                logfile.write('lots: cleared venue owner {!r} off zone '
                              '{}'.format(venue_owner, zone_id))
            except Exception as ex:
                logfile.write('lots: clear_venue_owner failed ({!r})'.format(ex))
            try:
                build_buy.set_venue_owner_id(zone_id, mine_id)
                logfile.write('lots: venue owner set to us')
            except Exception as ex:
                logfile.write('lots: set_venue_owner_id failed ({!r})'.format(ex))
    except Exception as ex:
        logfile.write('lots: venue owner check failed ({!r})'.format(ex))

    # Verify by effect: the save is what build mode asks, not the call.
    owner = owner_of()
    mine = bool(owner and owner == mine_id)
    logfile.write('lots: claim zone {} via {} -> owner {!r}, mine={}'.format(
        zone_id, ', '.join(tried) or 'nothing', owner, mine))
    if mine:
        spoken = 'This lot belongs to your household now. Build mode should open.'
        if evicted:
            spoken = '{} owned this lot; it is yours now. {}'.format(
                evicted, spoken)
        return True, spoken
    return False, ('The game still does not list this lot as yours. The log '
                   'has what was tried.')


def move_house(entry):
    """Move the household you are playing onto this lot."""
    try:
        import services
        household = services.active_household()
    except Exception as ex:
        logfile.fail('lots: no active household ({!r})'.format(ex))
        return 'Could not find your household.'
    if household is None:
        return 'Could not find your household.'
    ok, message = move_in(household, entry['zone_id'])
    if not ok:
        return message
    # Ownership is the half that silently does not happen. Without it you live
    # there and cannot build there, which is not a state anyone would guess at.
    owned, owner_message = claim_lot(entry['zone_id'], household)
    if not owned:
        logfile.write('lots: moved in but the lot is not owned: {}'.format(
            owner_message))
    # Owning the lot is only half of moving: you are still standing in the old
    # house until you travel. Doing both here means one keypress moves you.
    try:
        import a11yscan_travel as travel
        spoken = travel.travel_to_zone(entry['zone_id'], entry['name'])
    except Exception as ex:
        logfile.fail('lots: moved in but could not travel ({!r})'.format(ex))
        return ('{} is now your home, but the trip there failed. '
                'Try Control Shift T.'.format(entry['name']))
    logfile.ok('lots: moved to {!r} and started travelling'.format(
        entry['name']))
    return '{} is now your home. {}'.format(entry['name'], spoken)


def _household_of(sim):
    try:
        import services
        info = getattr(sim, 'sim_info', None) or sim
        return services.household_manager().get(info.household_id)
    except Exception:
        return None


def _funds_of(household):
    for getter in (lambda: household.funds.money,
                   lambda: household._funds.money):
        try:
            return int(getter())
        except Exception:
            continue
    return None


def _zone_name(zone_id):
    for entry in survey():
        if entry.get('zone_id') == zone_id:
            return entry['name']
    return 'their lot'


def move_in_candidates():
    """Sims here you could move in with, offered two ways each.

    Your household is always the one that survives, whichever home you keep.
    Merging the other way would hand your Sims to a household you do not
    control, and getting that wrong would cost someone their save.
    """
    out = []
    try:
        import services
        mine = services.active_household()
        my_id = getattr(mine, 'id', None)
        manager = services.sim_info_manager()
    except Exception as ex:
        logfile.write('lots: no household for move-in ({!r})'.format(ex))
        return out
    if not my_id:
        return out
    sims = []
    for attr in ('instanced_sims_on_active_lot_gen', 'instanced_sims_gen'):
        try:
            getter = getattr(manager, attr, None)
            if getter is not None:
                sims = list(getter())
                break
        except Exception:
            continue
    seen = set()
    for sim in sims:
        info = getattr(sim, 'sim_info', None) or sim
        household_id = getattr(info, 'household_id', None)
        if not household_id or household_id == my_id or household_id in seen:
            continue
        household = _household_of(sim)
        if household is None:
            continue
        seen.add(household_id)
        name = '{} {}'.format(getattr(info, 'first_name', '') or '',
                              getattr(info, 'last_name', '') or '').strip()
        home_zone = getattr(household, 'home_zone_id', None)
        try:
            size = len(list(household.sim_info_gen()))
        except Exception:
            size = None
        base = {'kind': 'merge', 'name': name or 'a Sim',
                'household_id': household_id, 'home_zone': home_zone,
                'size': size, 'funds': _funds_of(household),
                'household_name': getattr(household, 'name', None)}
        here = dict(base)
        here['move_home'] = False
        out.append(here)
        if home_zone:
            there = dict(base)
            there['move_home'] = True
            there['home_name'] = _zone_name(home_zone)
            out.append(there)
    logfile.write('lots: {} move-in options from {} other households'.format(
        len(out), len(seen)))
    return out


def describe_merge(entry):
    parts = ['Move in with {}'.format(entry['name'])]
    if entry.get('move_home'):
        parts.append('everyone moves to {}'.format(
            entry.get('home_name') or 'their lot'))
    else:
        parts.append('they move in here')
    if entry.get('size'):
        parts.append('{} Sim{} joining'.format(
            entry['size'], '' if entry['size'] == 1 else 's'))
    if entry.get('funds') is not None:
        parts.append('bringing {:,} simoleons'.format(entry['funds']))
    if entry.get('household_name'):
        parts.append('the {} household'.format(entry['household_name']))
    return ', '.join(parts)


def move_in_together(entry):
    """Merge their household into yours, and move house if that was the choice."""
    try:
        import services
        mine = services.active_household()
    except Exception as ex:
        logfile.fail('lots: no household to merge into ({!r})'.format(ex))
        return 'Could not find your household.'
    if mine is None:
        return 'Could not find your household.'
    before = _funds_of(mine)
    try:
        before_size = len(list(mine.sim_info_gen()))
    except Exception:
        before_size = None

    merged = False
    for label, call in (
            ('keywords',
             lambda: mine.merge(entry['household_id'], should_spawn=True,
                                selectable=True,
                                reason='a11yscan move in together')),
            ('positional',
             lambda: mine.merge(entry['household_id'], True, True,
                                'a11yscan move in together'))):
        try:
            call()
            merged = True
            break
        except TypeError as ex:
            logfile.write('lots: merge {} signature wrong ({!r})'.format(
                label, ex))
        except Exception as ex:
            logfile.fail('lots: merge {} failed ({!r})'.format(label, ex))
            break
    if not merged:
        return 'Could not move in together. The log has the reason.'

    # Read the household back rather than trusting the merge. The Sim count
    # and the money are the two things that prove it actually happened.
    after = _funds_of(mine)
    try:
        after_size = len(list(mine.sim_info_gen()))
    except Exception:
        after_size = None
    logfile.ok('lots: merged {} - household {} to {} Sims, funds {} to {}'
               .format(entry['name'], before_size, after_size, before, after))
    if not (after_size or 0) > (before_size or 0):
        return ('Asked {} to move in, but your household did not '
                'change.'.format(entry['name']))
    spoken = '{} joined your household'.format(entry['name'])
    if before is not None and after is not None and after != before:
        spoken += ', bringing {:,} simoleons'.format(after - before)
    spoken += '.'

    if not entry.get('move_home'):
        return spoken + ' They live here now.'

    ok, message = move_in(mine, entry['home_zone'])
    if not ok:
        return '{} But the move to their lot failed: {}'.format(spoken, message)
    try:
        import a11yscan_travel as travel
        return '{} {}'.format(spoken, travel.travel_to_zone(
            entry['home_zone'], entry.get('home_name') or 'your new home'))
    except Exception as ex:
        logfile.fail('lots: merged and moved but could not travel '
                     '({!r})'.format(ex))
        return (spoken + ' Their lot is now your home; travel there with '
                'Control Shift T.')


def report():
    """Write the whole survey to the log and summarise it out loud."""
    entries = survey()
    if not entries:
        return 'No lots found. The log has the reason.'
    free = [e for e in entries if not e['occupied']]
    logfile.write('=' * 60)
    for entry in entries:
        logfile.write('lot: {}'.format(describe(entry)), 'lots')
    logfile.write('=' * 60)
    worlds = sorted(set(e['world'] for e in entries))
    return '{} lots across {} worlds, {} empty. Written to the log.'.format(
        len(entries), len(worlds), len(free))


# --------------------------------------------------------------- households

def households():
    """Every household in the save, with the one being played marked."""
    try:
        import services
        manager = services.household_manager()
        active = services.active_household()
    except Exception as ex:
        logfile.fail('households: unavailable ({!r})'.format(ex))
        return []
    if manager is None:
        return []
    entries = []
    for household in manager.values():
        try:
            sims = list(household.sim_info_gen())
        except Exception:
            sims = []
        if not sims:
            continue          # empty households are not playable
        # Every household in the world lives in this manager, townies and
        # service NPCs included. Listing them flat meant one keypress could
        # drop you into a family you had never seen. Yours come first, and the
        # rest stay reachable but are announced as not yours.
        mine = False
        try:
            mine = bool(household.is_player_household
                        or household.is_played_household)
        except Exception:
            mine = False
        if household is active:
            mine = True
        home_zone = getattr(household, 'home_zone_id', None)
        if not home_zone:
            continue          # nowhere to travel to; zone 0 hangs the client
        entries.append({
            'household': household,
            'name': getattr(household, 'name', None) or 'household',
            'sims': [str(getattr(s, 'first_name', '') or '') for s in sims],
            'playing': household is active,
            'mine': mine,
            'zone_id': getattr(household, 'home_zone_id', None),
        })
    entries.sort(key=lambda e: (not e['playing'], not e['mine'],
                                e['name'].lower()))
    logfile.write('households: {} total, {} yours'.format(
        len(entries), sum(1 for e in entries if e['mine'])))
    return entries


def describe_household(entry):
    who = ', '.join(name for name in entry['sims'] if name)
    parts = [entry['name']]
    if who:
        parts.append(who)
    else:
        parts.append('{} sims'.format(len(entry['sims'])))
    if entry['playing']:
        parts.append('playing now')
    elif not entry.get('mine'):
        parts.append('not one of yours')
    return ', '.join(parts)


def claim(entry):
    """Mark a household as one of yours, so it sorts with the rest of them."""
    try:
        entry['household'].set_played_household(True)
        entry['mine'] = True
        logfile.ok('households: {!r} marked as yours'.format(entry['name']))
        return '{} is now one of your households.'.format(entry['name'])
    except Exception as ex:
        logfile.fail('households: could not claim {!r} ({!r})'.format(
            entry['name'], ex))
        return 'Could not mark that household as yours.'


_last_switch = [0.0]
# One travel op at a time. Six of them went out inside a single second when a
# held Enter re-fired, two aimed at households with no lot, and the client sat
# on a travel screen that never resolved. Travel is not idempotent.
SWITCH_COOLDOWN = 20.0


def switch_household(entry):
    """Go and play another household, loading their lot.

    Uses the route the game uses itself (household_commands
    _activate_sims_family -> send_travel_live_to_nhd_to_live_op). It is still a
    client travel op, and a different one of those once left the game with no
    active Sim, so this says to save first rather than assuming.
    """
    if entry['playing']:
        return 'You are already playing {}.'.format(entry['name'])
    import time
    since = time.monotonic() - _last_switch[0]
    if since < SWITCH_COOLDOWN:
        logfile.write('households: refused a second switch {:.1f}s after the '
                      'last one'.format(since))
        return ('Already travelling. Wait for the lot to load before '
                'switching again.')
    if not entry.get('zone_id'):
        logfile.fail('households: {!r} has no home lot'.format(entry['name']))
        return '{} has no home lot to travel to.'.format(entry['name'])
    household = entry['household']
    sim_infos = []
    try:
        sim_infos = list(household.sim_info_gen())
    except Exception:
        pass
    if not sim_infos:
        return '{} has nobody to play.'.format(entry['name'])
    logfile.write('households: switching to {!r} (zone {})'.format(
        entry['name'], entry['zone_id']))
    try:
        sim_infos[0].send_travel_live_to_nhd_to_live_op(
            getattr(household, 'id', None), entry['zone_id'])
    except Exception as ex:
        logfile.fail('households: switch failed ({!r})'.format(ex))
        return 'Could not switch to that household. The log has the reason.'
    _last_switch[0] = time.monotonic()
    logfile.ok('households: travel op sent for {!r}'.format(entry['name']))
    return ('Loading {}. If anything looks wrong afterwards, load your save '
            'again rather than saving over it.'.format(entry['name']))
