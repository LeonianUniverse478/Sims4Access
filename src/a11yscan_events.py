"""Planning a social event without the event planner screen.

The planner the game shows is client-side, but everything behind it is a
server command, so the whole flow can be rebuilt as a list:

  which event        SITUATION tuning whose creation_ui_option is AVAILABLE,
                     which is the same test should_display_situation uses
  which activities   situation.get_preferred_activities(sim_id)
  who is invited     the host's relationships, plus whoever is on the lot
  where              here, or any lot in the save
  start it           situation_commands.create_situation_with_guest_list

That last call takes the guest list as loose arguments in threes -
job, sim, purpose, job, sim, purpose - after the fixed parameters, and refuses
the lot outright if the count is not a multiple of three.

The host is always the Sim you are playing: the command reads
client.active_sim itself and does not offer a way to say otherwise.
"""
import a11yscan_log as logfile

# The purpose an invited guest is given. INVITED = 1, straight from
# SituationInvitationPurpose.
PURPOSE_INVITED = 'INVITED'
MAX_GUESTS = 60

_active = False
_index = 0
_entries = []

_event = None
_event_name = ''
_zone_id = None
_zone_name = 'here'
_guests = []
_activities = []


def active():
    return _active


# ------------------------------------------------------------- the choices

def available_events():
    """Every event the game would offer in its own planner.

    should_display_situation gates on creation_ui_option being AVAILABLE, so
    that is the test here too rather than a guess at which situations are
    "really" events.
    """
    out = []
    try:
        import services
        import sims4.resources
        from situations.situation_types import SituationCreationUIOption
        manager = services.get_instance_manager(
            sims4.resources.Types.SITUATION)
    except Exception as ex:
        logfile.fail('events: no situation tuning ({!r})'.format(ex))
        return out
    import a11yscan_dialogs as dialogs
    for situation in manager.types.values():
        try:
            option = getattr(situation, 'creation_ui_option', None)
            if option != SituationCreationUIOption.AVAILABLE:
                continue
        except Exception:
            continue
        name = None
        try:
            name = dialogs.loc_text(getattr(situation, 'display_name', None))
        except Exception:
            name = None
        if not name:
            import a11yscan_world as world
            name = world.prettify(getattr(situation, '__name__', '') or '')
        if not name or name == 'object':
            continue
        out.append((name, situation))
    out.sort(key=lambda pair: pair[0].lower())
    logfile.write('events: {} events can be planned'.format(len(out)))
    return out


def event_summary(situation, name):
    """Name, cost, goal and description - what the planner puts on its card.

    get_situation_data builds that card from situation_description,
    situation_main_objective, situation_location_description, _cost and
    max_participants, so those are read here rather than guessed at. Knowing
    the goal before committing is the whole point: an event you cannot see is
    an event you cannot judge.
    """
    import a11yscan_dialogs as dialogs
    parts = [name]
    try:
        cost = int(getattr(situation, '_cost', 0) or 0)
        if cost:
            parts.append('costs {:,} simoleons'.format(cost))
    except Exception:
        pass
    try:
        limit = int(getattr(situation, 'max_participants', 0) or 0)
        if limit:
            parts.append('up to {} Sims'.format(limit))
    except Exception:
        pass
    for attr, prefix in (('situation_main_objective', 'goal'),
                         ('situation_description', None),
                         ('situation_location_description', 'held at')):
        try:
            text = dialogs.loc_text(getattr(situation, attr, None))
        except Exception:
            text = None
        if not text:
            continue
        text = text.strip().rstrip('.')
        parts.append('{}: {}'.format(prefix, text) if prefix else text)
    return '. '.join(parts)


def _host():
    import a11yscan_world as world
    return world.active_sim()


def _candidate_guests():
    """People you could invite: everyone you know, plus anyone stood here."""
    found = {}
    host = _host()
    host_id = getattr(host, 'id', None)
    info = getattr(host, 'sim_info', None) or host

    try:
        tracker = info.relationship_tracker
        for other in tracker.target_sim_infos():
            sim_id = getattr(other, 'sim_id', None) or getattr(other, 'id', None)
            if sim_id and sim_id != host_id:
                found[sim_id] = _name_of(other)
    except Exception as ex:
        logfile.write('events: no relationships to invite ({!r})'.format(ex))

    try:
        import services
        manager = services.sim_info_manager()
        for attr in ('instanced_sims_gen',):
            getter = getattr(manager, attr, None)
            if getter is None:
                continue
            for sim in getter():
                sim_id = getattr(sim, 'id', None)
                if sim_id and sim_id != host_id and sim_id not in found:
                    found[sim_id] = _name_of(
                        getattr(sim, 'sim_info', None) or sim)
    except Exception:
        pass

    out = [{'id': sim_id, 'name': name, 'invited': False}
           for sim_id, name in found.items() if name]
    out.sort(key=lambda entry: entry['name'].lower())
    logfile.write('events: {} Sims could be invited'.format(len(out)))
    return out[:MAX_GUESTS]


def _name_of(info):
    return '{} {}'.format(getattr(info, 'first_name', '') or '',
                          getattr(info, 'last_name', '') or '').strip()


def _activity_id(activity):
    """The id the planner sends for an activity."""
    selection = getattr(activity, 'activity_selection', activity)
    for attr in ('guid64', 'activity_id', 'id'):
        found = getattr(selection, attr, None) or getattr(activity, attr, None)
        if found:
            return found
    return None


def _activity_name(activity):
    import a11yscan_dialogs as dialogs
    selection = getattr(activity, 'activity_selection', activity)
    for attr in ('preferred_activity_name', 'display_name', 'name'):
        try:
            name = dialogs.loc_text(getattr(selection, attr, None))
        except Exception:
            name = None
        if name:
            return name
    return 'an activity'


def _listed(holder, attr):
    try:
        return list(getattr(holder, attr, None) or ())
    except Exception:
        return []


def _event_activities(situation):
    """The activities this event offers, with the sensible ones already on.

    The planner marks some activities required and recommends others, and
    there is no reason to make anyone tick those by hand. Required ones are
    switched on and cannot sensibly be left off; recommended ones - what
    get_preferred_activities returns - start on and can be switched off.
    """
    out = []
    host = _host()
    host_id = getattr(host, 'id', None)
    if situation is None or not host_id:
        return out

    selection = getattr(situation, 'activity_selection', None)
    required = _listed(selection, 'required_activities') if selection else []
    available = _listed(selection, 'available_activities') if selection else []

    recommended = []
    for call in (lambda: situation.get_preferred_activities(host_id),
                 lambda: situation.get_preferred_activities()):
        try:
            recommended = list(call())
            break
        except Exception:
            continue

    required_ids = set(filter(None, (_activity_id(a) for a in required)))
    recommended_ids = set(filter(None, (_activity_id(a) for a in recommended)))

    seen = set()
    for activity in list(required) + list(recommended) + list(available):
        activity_id = _activity_id(activity)
        if activity_id is None or activity_id in seen:
            continue
        seen.add(activity_id)
        is_required = activity_id in required_ids
        out.append({
            'id': activity_id,
            'name': _activity_name(activity),
            'required': is_required,
            'recommended': activity_id in recommended_ids,
            # On by default when the game asked for it or suggested it.
            'chosen': is_required or activity_id in recommended_ids,
        })
    logfile.write('events: {} activities - {} required, {} recommended, all '
                  'of those pre-selected'.format(
                      len(out), len(required_ids), len(recommended_ids)))
    return out


# ------------------------------------------------------------------- menu

def _rebuild():
    """One flat list. What is in it depends on whether an event is chosen."""
    global _entries
    _entries = []
    if _event is None:
        for name, situation in available_events():
            _entries.append({'label': event_summary(situation, name),
                             'kind': 'event', 'payload': situation,
                             'name': name})
        return
    _entries.append({'label': 'Event: {}. Enter to choose a different '
                              'one'.format(_event_name),
                     'kind': 'change', 'payload': None})
    _entries.append({'label': 'Where: {}. Enter to hold it here'.format(
        _zone_name), 'kind': 'here', 'payload': None})
    for guest in _guests:
        _entries.append({
            'label': 'Invite {}: {}'.format(
                guest['name'], 'yes' if guest['invited'] else 'no'),
            'kind': 'guest', 'payload': guest})
    for activity in _activities:
        note = ''
        if activity.get('required'):
            note = ', required'
        elif activity.get('recommended'):
            note = ', recommended'
        _entries.append({
            'label': 'Activity {}: {}{}'.format(
                activity['name'], 'yes' if activity['chosen'] else 'no', note),
            'kind': 'activity', 'payload': activity})
    for entry in _lot_entries():
        _entries.append(entry)
    _entries.append({'label': 'Start the event', 'kind': 'start',
                     'payload': None})


def _lot_entries():
    out = []
    try:
        import a11yscan_lots as lots
        for lot in lots.survey():
            if not lot.get('zone_id'):
                continue
            out.append({'label': 'Hold it at {}, in {}'.format(
                lot['name'], lot['world']), 'kind': 'venue', 'payload': lot})
    except Exception as ex:
        logfile.write('events: no lots to offer ({!r})'.format(ex))
    return out


MEDALS = ('no medal yet', 'bronze', 'silver', 'gold')

_goal_shape_logged = False


# Announcing progress on its own, so an event can be played rather than
# interrogated. Only CHANGES are spoken.
_watch_on = True
_watch_state = {}
_WATCH_SECONDS = 6.0
_last_watch = [0.0]


def watch_enabled():
    return _watch_on


def set_watch(enabled):
    """Turn the automatic announcements on or off."""
    global _watch_on
    _watch_on = bool(enabled)
    _watch_state.clear()
    return ('Event progress will be read out as it happens.' if _watch_on
            else 'Event progress will stay quiet until you ask.')


def _watch_key(situation):
    try:
        return int(getattr(situation, 'id', 0) or id(situation))
    except Exception:
        return id(situation)


def watch_tick():
    """Say what changed since the last look. Called from the slow tick."""
    if not _watch_on:
        return
    import time
    now = time.monotonic()
    if now - _last_watch[0] < _WATCH_SECONDS:
        return
    _last_watch[0] = now

    import a11yscan_speech as speech
    events = running_events()
    live = set()
    for situation in events:
        key = _watch_key(situation)
        live.add(key)
        try:
            goals = dict(_goal_pairs(situation))
            medal = _medal_level(situation)
        except Exception as ex:
            logfile.write('events: watch read failed ({!r})'.format(ex))
            continue
        before = _watch_state.get(key)
        _watch_state[key] = {'goals': goals, 'medal': medal}
        if before is None:
            # First sighting. Say the event is being watched rather than
            # reading every goal at someone who just started one.
            continue
        said = []
        for text, status in goals.items():
            was = before['goals'].get(text)
            if was == status:
                continue
            if status == 'done':
                said.append('{}, done'.format(text))
            elif was is not None:
                said.append('{}, {}'.format(text, status))
        if medal > before['medal']:
            said.append('{} medal reached'.format(MEDALS[medal]))
        if said:
            speech.speak('. '.join(said) + '.')

    for key in [k for k in _watch_state if k not in live]:
        del _watch_state[key]
        import a11yscan_speech as speech
        speech.speak('The event has ended.')


def _goal_pairs(situation):
    """[(goal text, status)] where status is 'done' or 'n of m' or 'not yet'."""
    pairs = []
    for line in _goal_lines(situation):
        text, _sep, status = line.rpartition(': ')
        pairs.append((text or line, status))
    return pairs


def _medal_level(situation):
    try:
        score = int(getattr(situation, 'score', 0) or 0)
    except Exception:
        return 0
    reached = 0
    for level in range(1, 4):
        try:
            threshold = situation.get_level_min_threshold(level)
        except Exception:
            continue
        if threshold is not None and score >= int(threshold):
            reached = level
    return reached


def event_name(situation):
    """What to call it out loud: the game's own name, not the class."""
    import a11yscan_dialogs as dialogs
    import a11yscan_world as world
    try:
        text = dialogs.loc_text(getattr(situation, 'display_name', None))
    except Exception:
        text = None
    return text or world.prettify(type(situation).__name__)


def endable():
    """[(name, situation_id)] for the events you could end right now."""
    out = []
    for situation in running_events():
        situation_id = getattr(situation, 'id', None)
        if situation_id is None:
            continue
        out.append((event_name(situation), situation_id))
    return out


def end_event(situation_id=None, name=None):
    """Stop an event early. The score you have already earned still counts.

    destroy_situation_by_id is what the game's own destroy_situation command
    calls, so the event ends the way it would if its timer ran out rather than
    being torn out from under the guests.
    """
    import services
    if situation_id is None:
        current = endable()
        if not current:
            return 'No event is running.'
        name, situation_id = current[0]
    try:
        manager = services.get_zone_situation_manager()
        manager.destroy_situation_by_id(situation_id)
    except Exception as ex:
        logfile.fail('events: could not end {} ({!r})'.format(name, ex))
        return 'Could not end the event. The log has the reason.'
    # Verify by effect: ask whether it is still listed rather than trusting it.
    still = any(sid == situation_id for _n, sid in endable())
    logfile.write('events: ended {!r} (id {}), still running: {}'.format(
        name, situation_id, still))
    if still:
        return '{} is still running.'.format(name or 'The event')
    return '{} has ended.'.format(name or 'The event')


def running_events():
    """The events the game itself would show, and nothing else.

    should_track_score was the wrong test - 20 of the 22 situations on an
    ordinary lot answer True to it, so every visitor and background job read as
    a running event. The game's own question is is_user_facing, and the manager
    exposes exactly that filter:

        SituationManager.get_user_facing_situations_gen():
            for situation in self.values():
                if situation.is_user_facing:
                    yield situation

    That is the list the event panel is drawn from, so it is the list to report.
    """
    out = []
    try:
        import services
        manager = services.get_zone_situation_manager()
    except Exception as ex:
        logfile.write('events: could not reach the situations ({!r})'.format(ex))
        return out
    for getter in (lambda: list(manager.get_user_facing_situations_gen()),
                   lambda: [s for s in manager.running_situations()
                            if getattr(s, 'is_user_facing', False)]):
        try:
            out = getter()
        except Exception as ex:
            logfile.write('events: user-facing lookup failed ({!r})'.format(ex))
            continue
        break
    if out:
        logfile.write('events: {} user-facing: {}'.format(
            len(out), ', '.join(type(s).__name__ for s in out[:4])))
    return out


def _value_of(holder, *names):
    """Read a field whether the game made it a property or a method."""
    for name in names:
        value = getattr(holder, name, None)
        if value is None:
            continue
        if callable(value):
            try:
                value = value()
            except Exception:
                continue
        if value is not None:
            return value
    return None


def _goal_lines(situation):
    """Each goal, how far along it is, and whether it is done.

    get_goal_info returns pairs of (goal, None) - the second element is NOT a
    completion flag, which is what made every goal read "not yet" for ever.
    Completion lives on the goal: is_completed, and completed_iterations out of
    max_iterations for the counted ones. The count is the useful part: "2 of 5
    conversations" is progress you can hear, where "not yet" is indis-
    tinguishable from a goal that is not working.
    """
    import a11yscan_dialogs as dialogs
    import a11yscan_world as world
    global _goal_shape_logged
    lines = []
    info = None
    for label, getter in (
            ('situation.get_situation_goal_info',
             lambda: situation.get_situation_goal_info()),
            ('tracker.get_goal_info',
             lambda: situation._get_goal_tracker().get_goal_info())):
        try:
            info = getter()
        except Exception as ex:
            logfile.write('events: {} failed ({!r})'.format(label, ex))
            info = None
        if info:
            break
    info = list(info or ())
    # Some trackers take a goal OUT of the live list once it is finished and
    # hand it back from a second one. Missing that list means a completed goal
    # silently disappears from the readout instead of being announced.
    finished = []
    for getter in (lambda: situation.get_completed_situation_goal_info(),
                   lambda: situation._get_goal_tracker().get_completed_goal_info()):
        try:
            finished = list(getter() or ())
        except Exception:
            finished = []
        if finished:
            break
    for item in finished:
        goal = item[0] if isinstance(item, (tuple, list)) and item else item
        if goal is not None and goal not in [
                (i[0] if isinstance(i, (tuple, list)) and i else i)
                for i in info]:
            info.append((goal, True))
    if not info:
        return lines

    for item in info:
        goal = item[0] if isinstance(item, (tuple, list)) and item else item
        if goal is None:
            continue
        if not _goal_shape_logged:
            _goal_shape_logged = True
            try:
                logfile.write('events: goal fields {}'.format(
                    ', '.join(a for a in dir(goal) if not a.startswith('_'))[:400]))
            except Exception:
                pass
        text = None
        raw = _value_of(goal, 'get_display_name', 'display_name')
        if raw is not None:
            try:
                text = dialogs.loc_text(raw)
            except Exception:
                text = None
        if not text:
            text = world.prettify(getattr(type(goal), '__name__', 'a goal'))

        done = bool(_value_of(goal, 'is_completed') or
                    _value_of(goal, 'completed_time'))
        if isinstance(item, (tuple, list)) and len(item) > 1 and item[1] is True:
            done = True
        # What finishing this one is worth. SituationGoal.score is the tuned
        # value the medal thresholds are counted in, so this turns "how do I
        # earn points" into a list you can sort by yourself.
        worth = None
        try:
            value = _value_of(goal, 'score')
            if value is not None and int(value):
                worth = int(value)
        except Exception:
            worth = None
        so_far = _value_of(goal, 'completed_iterations')
        needed = _value_of(goal, 'max_iterations')
        if done:
            lines.append('{}: done'.format(text))
        elif so_far is not None and needed and int(needed) > 1:
            lines.append('{}: {} of {}{}'.format(
                text, int(so_far), int(needed),
                ', worth {}'.format(worth) if worth else ''))
        else:
            lines.append('{}: not yet{}'.format(
                text, ', worth {}'.format(worth) if worth else ''))
    return lines


def _medal(situation):
    """Which medal the current score has earned, and what the next one needs."""
    try:
        score = int(getattr(situation, 'score', 0) or 0)
    except Exception:
        score = 0
    reached = 0
    next_at = None
    for level in range(1, 4):
        try:
            threshold = situation.get_level_min_threshold(level)
        except Exception:
            threshold = None
        if threshold is None:
            continue
        if score >= int(threshold):
            reached = level
        elif next_at is None:
            next_at = (level, int(threshold))
    spoken = '{} points, {}'.format(score, MEDALS[reached])
    if next_at is not None:
        spoken += ', {} more for {}'.format(next_at[1] - score,
                                            MEDALS[next_at[0]])
    return spoken


def live_report():
    """What is running, how it is scoring, and which goals are left."""
    import a11yscan_dialogs as dialogs
    import a11yscan_world as world
    events = running_events()
    if not events:
        return None
    parts = []
    for situation in events[:2]:
        try:
            name = dialogs.loc_text(getattr(situation, 'display_name', None))
        except Exception:
            name = None
        name = name or world.prettify(type(situation).__name__)
        lines = [name, _medal(situation)]
        goals = _goal_lines(situation)
        if goals:
            lines.extend(goals)
        else:
            lines.append('no goals are being tracked')
        parts.append('. '.join(lines))
    spoken = '. '.join(parts) + '.'
    logfile.write('events: reporting {!r}'.format(spoken))
    return spoken


def open_menu():
    global _active, _index, _event, _event_name, _zone_id, _zone_name
    global _guests, _activities
    _event = None
    _event_name = ''
    _zone_id = None
    _zone_name = 'here'
    _guests = []
    _activities = []
    _index = 0
    _rebuild()
    if not _entries:
        return 'No events can be planned right now. The log has the reason.'
    _active = True
    return ('Plan an event. {} to choose from. Up and down to browse, enter '
            'to choose, backspace to stop. {}'.format(
                len(_entries), describe()))


def close_menu():
    global _active
    _active = False
    return 'Event planning closed.'


def describe():
    if not _entries:
        return 'Nothing to choose.'
    index = _index % len(_entries)
    return '{}. {} of {}.'.format(
        _entries[index]['label'], index + 1, len(_entries))


def next_entry(step=1):
    global _index
    if not _entries:
        return 'Nothing to choose.'
    _index = (_index + step) % len(_entries)
    return describe()


def activate():
    global _event, _event_name, _zone_id, _zone_name, _guests, _activities
    global _index
    if not _entries:
        return 'Nothing to choose.'
    entry = _entries[_index % len(_entries)]
    kind = entry['kind']

    if kind == 'event':
        _event = entry['payload']
        # The short name for later lines; the long summary was only for
        # choosing, and repeating it on every rebuild would be unbearable.
        _event_name = entry.get('name') or entry['label']
        _guests = _candidate_guests()
        _activities = _event_activities(_event)
        _index = 0
        _rebuild()
        picked = sum(1 for a in _activities if a['chosen'])
        return ('{} chosen. {} people to invite, {} activities with {} already '
                'selected for you. {}'.format(
                    _event_name, len(_guests), len(_activities), picked,
                    describe()))

    if kind == 'change':
        _event = None
        _index = 0
        _rebuild()
        return 'Choose an event. {}'.format(describe())

    if kind == 'guest':
        entry['payload']['invited'] = not entry['payload']['invited']
        _rebuild()
        return '{} is {} invited.'.format(
            entry['payload']['name'],
            'now' if entry['payload']['invited'] else 'not')

    if kind == 'activity':
        entry['payload']['chosen'] = not entry['payload']['chosen']
        _rebuild()
        return '{} is {} on the list.'.format(
            entry['payload']['name'],
            'now' if entry['payload']['chosen'] else 'not')

    if kind == 'here':
        _zone_id = None
        _zone_name = 'here'
        _rebuild()
        return 'The event will be held here.'

    if kind == 'venue':
        _zone_id = entry['payload']['zone_id']
        _zone_name = entry['payload']['name']
        _rebuild()
        return 'The event will be held at {}.'.format(_zone_name)

    if kind == 'start':
        return start()
    return 'Nothing to do with that.'


# ------------------------------------------------------------------ start

def _job_key(situation):
    """The job invited guests are given.

    create_situation_with_guest_list looks the job up with
    job_manager.get(job_name_or_key), so it wants the resource id rather than
    a readable name.
    """
    job = None
    for getter in (lambda: situation.default_job(),
                   lambda: situation.default_job):
        try:
            job = getter()
        except Exception:
            continue
        if job is not None:
            break
    if job is None:
        try:
            job = next(iter(situation.all_jobs_gen()))
        except Exception:
            job = None
    if job is None:
        return None
    for attr in ('guid64', 'guid', 'id'):
        key = getattr(job, attr, None)
        if key:
            return key
    return None


def start():
    """Create the event. Verified by asking the situation manager afterwards."""
    if _event is None:
        return 'Choose an event first.'
    host = _host()
    if host is None:
        return 'No Sim to host it.'
    try:
        import services
        from server_commands.situation_commands import (
            create_situation_with_guest_list)
        client = services.client_manager().get_first_client()
        connection = getattr(client, 'id', None)
        manager = services.get_zone_situation_manager()
        zone_id = _zone_id or services.current_zone_id()
    except Exception as ex:
        logfile.fail('events: cannot reach the situation commands '
                     '({!r})'.format(ex))
        return 'Could not start the event.'

    before = 0
    try:
        before = len(list(manager.running_situations()))
    except Exception:
        before = 0

    invited = [guest for guest in _guests if guest['invited']]
    job_key = _job_key(_event)
    guest_args = []
    if job_key is not None:
        for guest in invited:
            guest_args.extend([job_key, guest['id'], PURPOSE_INVITED])
    elif invited:
        logfile.write('events: no job to put guests in, starting without them')

    activity_ids = ','.join(str(a['id']) for a in _activities if a['chosen'])
    # The CLASS, not its id. The command's first act is:
    #
    #   guest_list = SituationGuestList(situation_type.force_invite_only,
    #                                   host_sim_id)
    #
    # so an id gets it 'int' object has no attribute 'force_invite_only'. From
    # the console that conversion is done by the command decorator, which does
    # not run when it is called directly from Python.
    situation_id = _event

    logfile.write('events: starting {!r} ({}) at zone {} with {} guests, job '
                  '{!r}, activities {!r}'.format(
                      _event_name, getattr(_event, '__name__', '?'), zone_id,
                      len(invited), job_key, activity_ids))
    try:
        create_situation_with_guest_list(
            situation_id, True, zone_id, 0, 0, activity_ids, 0, 0, False,
            *guest_args, _connection=connection)
    except Exception as ex:
        logfile.fail('events: create_situation_with_guest_list raised '
                     '({!r})'.format(ex))
        return 'Could not start the event. The log has the reason.'

    # Ask the manager rather than trusting the command: it returns nothing
    # useful, and a new running situation is the only proof it worked.
    after = before
    try:
        after = len(list(manager.running_situations()))
    except Exception:
        pass
    logfile.write('events: situations {} before, {} after'.format(
        before, after))
    if after <= before:
        return ('Asked to start {}, but no event appeared. The log has the '
                'detail.'.format(_event_name))
    close_menu()
    where = 'here' if _zone_id is None else _zone_name
    if invited:
        return '{} started {}, with {} invited.'.format(
            _event_name, where, len(invited))
    return '{} started {}.'.format(_event_name, where)
