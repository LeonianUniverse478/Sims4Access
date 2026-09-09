"""The one thing the simulation can say to the Gallery.

There is exactly one Gallery-shaped call in the whole game: the op that asks
the client to open its move-in-from-the-Gallery flow for a particular lot.
MoveInFromGallerySuperInteraction is a terrain interaction whose entire body
builds and sends it:

    op = distributor.ops.MoveHouseholdIntoLotFromGallery(
        household_id=household_id, num_household_sims=len(household),
        plex_zone_ids=zone_ids, zone_id=solo_zone_id)
    Distributor.instance().add_op(sim, op)

Sending it ourselves skips the part that made it unreachable. The interaction
gets its zone from `context.pick.get_zone_id_from_pick_location()` - a click on
the ground, which a keyboard cannot produce - but the op only wants a zone id,
and we already have every zone id in the save.

What the client does when it arrives is the open question, and the reason this
exists. If it draws a panel, we are no better off than with the map screen. If
any part of it arrives as a dialog, the mod's hooks will log it and there is
something to work with. Either way the log answers it, which beats guessing.
"""
import a11yscan_log as logfile


def _distributor():
    from distributor.system import Distributor
    return Distributor.instance()


def _zone_ids_for(zone_id):
    """The zone, plus its apartment siblings if it is one.

    An apartment building is several zones sharing a lot, and the interaction
    passes the whole group so the client can offer the right unit.
    """
    import services
    try:
        plex = services.get_plex_service()
        if plex is not None and plex.is_zone_an_apartment(zone_id):
            group = list(plex.get_plex_zones_in_group(zone_id))
            if zone_id in group:
                group.remove(zone_id)
            return group
    except Exception as ex:
        logfile.write('gallery: plex check failed ({!r})'.format(ex))
    return []


def move_in_from_gallery(zone_id=None):
    """Ask the client to open the Gallery for a lot. Reports what it can."""
    import services
    if zone_id is None:
        try:
            zone_id = services.current_zone_id()
        except Exception as ex:
            logfile.fail('gallery: no current zone ({!r})'.format(ex))
            return 'Could not tell which lot you are on.'
    try:
        zone_id = int(zone_id)
    except (TypeError, ValueError):
        return 'That is not a lot.'

    persistence = services.get_persistence_service()
    try:
        if persistence.is_save_locked():
            return 'The game is saving. Try again in a moment.'
    except Exception:
        pass

    household_id = None
    household = None
    try:
        household_id = persistence.get_household_id_from_zone_id(zone_id)
        household = services.household_manager().get(household_id)
    except Exception as ex:
        logfile.write('gallery: no household on zone {} ({!r})'.format(
            zone_id, ex))
    count = len(household) if household is not None else 0

    sim = None
    try:
        sim = services.get_active_sim()
    except Exception:
        sim = None
    if sim is None:
        return 'No active Sim to send this from.'

    try:
        import distributor.ops as ops
        op = ops.MoveHouseholdIntoLotFromGallery(
            household_id=household_id,
            num_household_sims=count,
            plex_zone_ids=_zone_ids_for(zone_id),
            zone_id=zone_id)
        _distributor().add_op(sim, op)
    except Exception as ex:
        logfile.fail('gallery: could not send the move-in op ({!r})'.format(ex))
        return 'The game would not open the Gallery. The log has the reason.'

    logfile.ok('gallery: asked the client to open the Gallery for zone {} '
               '(household {}, {} Sims)'.format(zone_id, household_id, count))
    # Deliberately vague about what happens next: nobody has seen it yet, and
    # promising a screen that may not be readable would be worse than saying so.
    return ('Asked the game to open the Gallery for this lot. If a panel '
            'appears that will not read, press Control Alt X, then send me '
            'the log - it records anything the game puts up.')
