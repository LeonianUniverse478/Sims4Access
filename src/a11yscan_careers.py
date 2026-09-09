"""Choosing a job, without the career screen.

The "Find a Job" screen is client-side. Proven rather than assumed: with the
screen visibly up and the game paused, `ui_dialog_service._active_dialogs` is
EMPTY - the service is alive and reachable, there is simply no server-side
dialog. Same wall as CAS and the pause menu, so the same answer: rebuild it
from the data the screen is drawn from.

Careers are ordinary tuning. The instance manager lists them, each carries a
localised name through its starting track, and joining one is a plain call on
the Sim's career tracker.
"""
import a11yscan_dialogs as dialogs
import a11yscan_log as logfile

_careers = []
_index = 0
_active = False


def active():
    return _active


def _sim_info():
    try:
        import services
        client = services.client_manager().get_first_client()
        if client is not None:
            info = getattr(client, 'active_sim_info', None)
            if info is not None:
                return info
        sim = services.get_active_sim()
        return getattr(sim, 'sim_info', None) if sim is not None else None
    except Exception:
        return None


def _career_name(career, sim_info):
    """The name the game would show for this career."""
    # career_name lives on the starting track and is a string factory that
    # takes the Sim, so it can say "Barista" or a gendered variant.
    for getter in (
            lambda: career.start_track.career_name(sim_info),
            lambda: career.start_track.get_career_name(sim_info),
            lambda: career.career_name(sim_info),
            lambda: career.display_name(sim_info)):
        try:
            text = dialogs.loc_text(getter())
        except Exception:
            continue
        if text:
            return text
    for attr in ('career_name', 'display_name'):
        try:
            text = dialogs.loc_text(getattr(career, attr, None))
        except Exception:
            text = None
        if text:
            return text
    raw = getattr(career, '__name__', None)
    if raw:
        import a11yscan_world as world
        return world.prettify(raw)
    return None


def _current_career_names(sim_info):
    held = set()
    try:
        tracker = sim_info.career_tracker
        for career in tracker.careers.values():
            name = _career_name(type(career), sim_info)
            if name:
                held.add(name)
    except Exception:
        pass
    return held


def _held_careers(sim_info):
    try:
        return list(sim_info.career_tracker.careers.values())
    except Exception:
        return []


def _describe_job(career, sim_info):
    """Level, performance and time off for a job the Sim holds."""
    parts = [_career_name(type(career), sim_info) or 'your job']
    try:
        level = getattr(career, 'user_level', None)
        if level is None:
            level = getattr(career, 'level', None)
        if level is not None:
            parts.append('level {}'.format(int(level)))
    except Exception:
        pass
    try:
        performance = getattr(career, 'work_performance', None)
        if performance is not None:
            parts.append('performance {}'.format(int(performance)))
    except Exception:
        pass
    try:
        pto = getattr(career, 'pto', None)
        if pto:
            parts.append('{} days off saved'.format(int(pto)))
    except Exception:
        pass
    try:
        if career.is_work_time():
            parts.append('work is on now')
    except Exception:
        pass
    return ', '.join(parts)


def _go_to_work(career, sim_info):
    for label, call in (('go_to_work_early', lambda: career.go_to_work_early()),
                        ('set_at_work_when_attending',
                         lambda: career.set_at_work_when_attending())):
        try:
            call()
            logfile.ok('careers: {} ran'.format(label))
            return 'Heading to work.'
        except Exception as ex:
            logfile.write('careers: {} failed ({!r})'.format(label, ex))
    return 'Could not go to work now.'


def _day_off(career, sim_info):
    for label, call in (('request_day_off(None)',
                         lambda: career.request_day_off(None)),
                        ('request_day_off()',
                         lambda: career.request_day_off())):
        try:
            call()
            logfile.ok('careers: day off requested via {}'.format(label))
            return 'Day off requested.'
        except TypeError:
            continue
        except Exception as ex:
            logfile.write('careers: {} failed ({!r})'.format(label, ex))
    return 'Could not take a day off.'


def _quit(career, sim_info):
    name = _career_name(type(career), sim_info) or 'that job'
    tracker = sim_info.career_tracker
    for label, call in (
            ('remove_career(uid)',
             lambda: tracker.remove_career(career.guid64)),
            ('remove_career(career_uid)',
             lambda: tracker.remove_career(career.career_uid))):
        try:
            call()
            logfile.ok('careers: quit {!r} via {}'.format(name, label))
            load()
            return 'You quit {}.'.format(name)
        except Exception as ex:
            logfile.write('careers: {} failed ({!r})'.format(label, ex))
    return 'Could not quit {}.'.format(name)


def _join(career_type, sim_info):
    name = _career_name(career_type, sim_info) or 'that job'
    tracker = sim_info.career_tracker
    before = {type(c) for c in _held_careers(sim_info)}
    for label, call in (
            ('add_career(career(sim_info))',
             lambda: tracker.add_career(career_type(sim_info))),
            ('add_career(career(sim_info), show_join_msg=False)',
             lambda: tracker.add_career(career_type(sim_info),
                                        show_join_msg=False)),
            ('add_career(career)', lambda: tracker.add_career(career_type))):
        try:
            call()
        except TypeError as ex:
            logfile.write('careers: {} wrong signature ({!r})'.format(label, ex))
            continue
        except Exception as ex:
            logfile.write('careers: {} raised {!r}'.format(label, ex))
            continue
        # Believe the tracker, not the call.
        if {type(c) for c in _held_careers(sim_info)} != before:
            logfile.ok('careers: joined {!r} via {}'.format(name, label))
            load()
            return 'You are now a {}.'.format(name)
        logfile.write('careers: {} changed nothing'.format(label))
    logfile.fail('careers: could not join {!r}'.format(name))
    return 'Could not take that job. The log has the reason.'


def _can_take(career, sim_info):
    """Whether the game would offer this job to this Sim.

    Career.is_valid_career is what the game's own screen filters on - without
    it the list includes teen-only and pack careers the Sim cannot hold, and
    taking one just fails.
    """
    for getter in (lambda: career.is_valid_career(sim_info, from_join=True),
                   lambda: career.is_valid_career(sim_info),
                   lambda: career.is_career_available(sim_info)):
        try:
            return bool(getter())
        except TypeError:
            continue
        except Exception:
            continue
    return True


def load():
    """Build the whole job menu: what you have, then what you can take."""
    global _careers, _index
    _careers = []
    _index = 0
    sim_info = _sim_info()
    if sim_info is None:
        return 0

    held = _held_careers(sim_info)
    for career in held:
        _careers.append({
            'label': _describe_job(career, sim_info),
            'action': None})
        _careers.append({
            'label': 'Go to work now',
            'action': lambda c=career: _go_to_work(c, sim_info)})
        _careers.append({
            'label': 'Take a day off',
            'action': lambda c=career: _day_off(c, sim_info)})
        _careers.append({
            'label': 'Quit {}'.format(
                _career_name(type(career), sim_info) or 'this job'),
            'action': lambda c=career: _quit(c, sim_info)})

    try:
        import services
        import sims4.resources
        manager = services.get_instance_manager(sims4.resources.Types.CAREER)
    except Exception as ex:
        logfile.fail('careers: no career manager ({!r})'.format(ex))
        return len(_careers)

    holding = {type(c) for c in held}
    offered = 0
    skipped = 0
    seen = set()
    for career in manager.types.values():
        if career in holding:
            continue
        if not _can_take(career, sim_info):
            skipped += 1
            continue
        name = _career_name(career, sim_info)
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        offered += 1
        _careers.append({
            'label': 'Take the job: {}'.format(name),
            'action': lambda c=career: _join(c, sim_info)})
    logfile.write('careers: {} held, {} jobs offered, {} not available'.format(
        len(held), offered, skipped))
    return len(_careers)


def open_picker():
    global _active
    count = load()
    if not count:
        return 'Could not read the jobs. The log has the reason.'
    _active = True
    return ('Jobs. Up and down to browse, enter to choose, backspace to '
            'stop. {}'.format(describe()))


def close_picker():
    global _active
    _active = False
    return 'Job menu closed.'


def describe():
    if not _careers:
        return 'Nothing here.'
    entry = _careers[_index % len(_careers)]
    return '{}. {} of {}.'.format(
        entry['label'], _index % len(_careers) + 1, len(_careers))


def next_career(step=1):
    global _index
    if not _careers:
        return 'Nothing here.'
    _index = (_index + step) % len(_careers)
    return describe()


def take_current():
    """Run whatever the highlighted line does."""
    if not _careers:
        return 'Nothing here.'
    entry = _careers[_index % len(_careers)]
    action = entry.get('action')
    if action is None:
        # The summary line: repeating it is the sensible thing to do.
        return entry['label']
    try:
        result = action()
    except Exception as ex:
        logfile.fail('careers: action failed ({!r})'.format(ex))
        return 'That did not work.'
    return '{} {}'.format(result, describe())


def quit_current_job():
    sim_info = _sim_info()
    if sim_info is None:
        return 'No Sim is selected.'
    held = _held_careers(sim_info)
    if not held:
        return 'You do not have a job.'
    return _quit(held[0], sim_info)
