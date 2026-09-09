"""Changing what a lot IS: bar, gym, library, park, home again.

Manage Worlds does this with a dropdown nobody can read. The simulation does it
with two calls, and server_commands.venue_commands.set_venue shows both:

    venue_game_service = services.venue_game_service()
    if venue_game_service is None:
        services.venue_service().on_change_venue_type_at_runtime(venue_tuning)
    else:
        venue_game_service.change_venue_type(services.current_zone_id(),
                                             venue_tuning)

It changes the lot you are standing on, which is the only one the running zone
knows about - so travel there first, then change it.

Every venue type is an instance in the VENUE manager, and each one can say
whether this lot has what it needs:

    ok, why = venue_tuning.lot_has_required_venue_objects(services.active_lot())

That answer is worth having before the change rather than after. A gym with no
exercise equipment is a gym nobody visits, and the game will not tell you so
out loud.
"""
import a11yscan_log as logfile

# Types whose names say they are not somewhere a player converts a lot into.
# Kept as a name test rather than a tuning flag: the flags that mark these vary
# by pack, the names do not.
_SKIP_WORDS = ('hidden', 'debug', 'placeholder', 'test')


def _manager():
    import services
    import sims4.resources
    return services.get_instance_manager(sims4.resources.Types.VENUE)


def _display_name(tuning):
    """What the game calls this venue, falling back to its tuning name."""
    import a11yscan_dialogs as dialogs
    import a11yscan_world as world
    for attr in ('display_name', 'venue_name', 'display_text', 'name'):
        try:
            text = dialogs.loc_text(getattr(tuning, attr, None))
        except Exception:
            text = None
        if text:
            return text
    raw = getattr(tuning, '__name__', None) or 'venue'
    # venue_bar_lounge -> "bar lounge"
    for prefix in ('venue_', 'Venue_'):
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
            break
    return world.prettify(raw)


def choices():
    """[(name, tuning)] for every venue type this install has, sorted."""
    out = []
    try:
        manager = _manager()
    except Exception as ex:
        logfile.fail('venue: no venue manager ({!r})'.format(ex))
        return out
    if manager is None:
        return out
    seen = set()
    for tuning in manager.types.values():
        try:
            raw = str(getattr(tuning, '__name__', '') or '').lower()
            if any(word in raw for word in _SKIP_WORDS):
                continue
            name = _display_name(tuning)
            key = name.lower()
            # Packs ship several tunings that read the same; a second "Bar"
            # in the list is a choice the player cannot tell from the first.
            if not name or key in seen:
                continue
            seen.add(key)
            out.append((name, tuning))
        except Exception:
            continue
    out.sort(key=lambda pair: pair[0].lower())
    logfile.write('venue: {} types offered'.format(len(out)))
    return out


def current():
    """The venue type of the lot we are on, as words."""
    try:
        import services
        service = services.venue_service()
        if service is None:
            return None
        tuning = (getattr(service, 'active_venue', None)
                  or getattr(service, 'source_venue', None))
        if tuning is None:
            return None
        return _display_name(tuning)
    except Exception as ex:
        logfile.write('venue: could not read the current type ({!r})'.format(ex))
        return None


def suits_this_lot(tuning):
    """(ok, why) - does this lot have the objects that venue type needs?"""
    try:
        import services
        lot = services.active_lot()
        if lot is None:
            return True, None
        result = tuning.lot_has_required_venue_objects(lot)
    except Exception as ex:
        logfile.write('venue: requirement test raised {!r}'.format(ex))
        return True, None
    try:
        ok, message = result
    except (TypeError, ValueError):
        ok, message = bool(result), None
    if ok:
        return True, None
    import a11yscan_dialogs as dialogs
    try:
        text = dialogs.loc_text(message) or None
    except Exception:
        text = None
    return False, text


def set_to(name, tuning):
    """Make this lot that kind of place. Verified by reading it back."""
    before = current()
    try:
        import services
        game_service = services.venue_game_service()
        if game_service is None:
            services.venue_service().on_change_venue_type_at_runtime(tuning)
            how = 'on_change_venue_type_at_runtime'
        else:
            game_service.change_venue_type(services.current_zone_id(), tuning)
            how = 'change_venue_type'
    except Exception as ex:
        logfile.fail('venue: could not change to {} ({!r})'.format(name, ex))
        return 'Could not change this lot. The log has the reason.'
    # The call returns nothing useful, so ask the service what the lot is now.
    after = current()
    logfile.ok('venue: {} -> {} via {}, reads back as {!r}'.format(
        before, name, how, after))
    if after and after.lower() != name.lower():
        return ('Asked for {}, but this lot still reads as {}. The log has '
                'what happened.'.format(name, after))
    ok, why = suits_this_lot(tuning)
    spoken = 'This lot is now {}.'.format(name)
    if not ok:
        spoken += ' It is missing what that needs{}.'.format(
            ': {}'.format(why) if why else '')
    return spoken


def report():
    """Lines for the console: what this lot is, and what it could be."""
    lines = ['this lot is: {}'.format(current() or 'unknown')]
    for name, tuning in choices():
        ok, why = suits_this_lot(tuning)
        lines.append('  {}{}'.format(
            name, '' if ok else ' (missing objects{})'.format(
                ': {}'.format(why) if why else '')))
    return lines
