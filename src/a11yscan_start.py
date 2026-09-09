"""Getting into the game, from the screens that come before a lot.

Three states exist before you are standing on a lot, and they need different
answers:

  1. The main menu. No zone, no save loaded, nothing in the persistence
     service. All the mod can do is choose which save Continue opens, which is
     a11yscan_saves.
  2. A save is loaded but you are on the world or lot screen - no zone is
     running, yet the persistence service is full of the save's data. This is
     where a new player gets stranded, because it looks identical to the main
     menu from the keyboard and it is not.
  3. A lot is running. Everything works.

State 2 is what this module is for. The persistence service answers with no
zone at all - all_household_protos() lists every family in the save - and the
game's own household switcher shows how to act on that answer without a lot:

    SwitchActiveHouseholdControlPickerInteraction._do_switch_operation:
        op = SwitchActiveHouseholdControl(sim_id=sim_id, zone_id=zone_id,
                                          household_id=household_id,
                                          household_name=household_name)
        Distributor.instance().add_op_with_no_owner(op)

Every value there comes from save protos rather than live objects
(get_sim_proto_buff(sim_id).zone_id is where that Sim lives), which is why it
works in a state where there are no live objects yet.

The proto field names are not documented anywhere, so each is read through a
list of candidates and what actually answered is written to the log. A wrong
guess here reads as "no households found", which is the least helpful thing the
mod could say to someone stuck on the screen this exists for.
"""
import a11yscan_log as logfile

_logged_shape = False


def _persistence():
    import services
    return services.get_persistence_service()


def _field(proto, names, default=None):
    for name in names:
        try:
            value = getattr(proto, name, None)
        except Exception:
            continue
        if value not in (None, '', 0):
            return value
    return default


def zone_running():
    try:
        import services
        zone = services.current_zone()
        return zone is not None and zone.is_zone_running
    except Exception:
        return False


def has_client():
    """A client exists from the moment a save starts loading, never before.

    This is what separates the main menu from the world and lot screens. The
    persistence service alone is not enough: quitting to the menu can leave a
    save's data in memory, and offering to switch family there would be the
    wrong question asked confidently.
    """
    try:
        import services
        manager = services.client_manager()
        return manager is not None and manager.get_first_client() is not None
    except Exception:
        return False


def save_is_loaded():
    """True when a save is open, whether or not a lot is running."""
    if not has_client():
        return False
    try:
        persistence = _persistence()
        if persistence is None:
            return False
        for _proto in persistence.all_household_protos():
            return True
    except Exception:
        return False
    return False


def households_in_save():
    """Every family in the loaded save, read from protos, no zone needed."""
    global _logged_shape
    out = []
    try:
        persistence = _persistence()
        protos = list(persistence.all_household_protos())
    except Exception as ex:
        logfile.write('start: no household protos ({!r})'.format(ex))
        return out
    for proto in protos:
        try:
            if not _logged_shape:
                _logged_shape = True
                fields = [f for f in dir(proto) if not f.startswith('_')][:30]
                logfile.write('start: household proto fields {}'.format(
                    ', '.join(fields)))
            household_id = _field(proto, ('household_id', 'id'))
            name = _field(proto, ('name', 'household_name'), 'a household')
            sims = _field(proto, ('sims', 'sim_ids', 'sim_list'), ()) or ()
            sim_ids = []
            for entry in sims:
                sim_id = entry if isinstance(entry, int) else _field(
                    entry, ('sim_id', 'id'))
                if sim_id:
                    sim_ids.append(sim_id)
            if not household_id or not sim_ids:
                continue
            zone_id = None
            for sim_id in sim_ids:
                try:
                    sim_proto = persistence.get_sim_proto_buff(sim_id)
                    zone_id = _field(sim_proto, ('zone_id',))
                except Exception:
                    zone_id = None
                if zone_id:
                    break
            out.append({'name': str(name), 'household_id': household_id,
                        'sim_id': sim_ids[0], 'zone_id': zone_id,
                        'size': len(sim_ids)})
        except Exception as ex:
            logfile.write('start: skipped a household ({!r})'.format(ex))
            continue
    out.sort(key=lambda e: (e['zone_id'] is None, e['name'].lower()))
    logfile.write('start: {} households in the save, {} with a home'.format(
        len(out), sum(1 for e in out if e['zone_id'])))
    return out


def describe(entry):
    where = 'no home lot' if not entry['zone_id'] else 'at home'
    return '{}, {} {}, {}'.format(
        entry['name'], entry['size'],
        'Sim' if entry['size'] == 1 else 'Sims', where)


def play(entry):
    """Load onto this family's lot and take control of them."""
    if not entry.get('zone_id'):
        return ('{} has no home lot, so there is nowhere to load. Choose a '
                'family that lives somewhere.'.format(entry['name']))
    try:
        from distributor.ops import SwitchActiveHouseholdControl
        from distributor.system import Distributor
        op = SwitchActiveHouseholdControl(
            sim_id=entry['sim_id'], zone_id=entry['zone_id'],
            household_id=entry['household_id'],
            household_name=entry['name'])
        Distributor.instance().add_op_with_no_owner(op)
    except Exception as ex:
        logfile.fail('start: could not switch to {!r} ({!r})'.format(
            entry['name'], ex))
        return 'The game would not load that family. The log has the reason.'
    logfile.ok('start: asked to play {!r} (household {}, zone {})'.format(
        entry['name'], entry['household_id'], entry['zone_id']))
    return ('Loading {}. Wait for the lot, then the scanner will say it is '
            'ready.'.format(entry['name']))


def next_step():
    """What to press, from wherever you are. Works before any lot exists."""
    if zone_running():
        return ('A lot is loaded. Control Alt S scans it, Control Alt F finds '
                'your Sim, Control Alt H lists every key.')
    if save_is_loaded():
        families = households_in_save()
        playable = [e for e in families if e['zone_id']]
        if playable:
            return ('A save is loaded but you are not on a lot yet. Press '
                    'Control Alt O to choose which of the {} families to '
                    'play - that loads their lot for you, so you never need '
                    'the world or lot screens.'.format(len(playable)))
        return ('A save is loaded but no family in it has a home lot. Press '
                'Control Alt M to build a Sim, which ends by choosing a lot '
                'to move into.')
    return ('No save is loaded, so this is the main menu. Press Control Alt O '
            'to choose which save to open, then press Continue on the screen '
            'to start it.')
