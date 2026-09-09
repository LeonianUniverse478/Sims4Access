"""Cheats as a keyboard menu, instead of remembering command names.

Everything here is something you could type in the cheat console. The point is
not new capability - it is not having to remember `stats.set_skill_level
Major_Charisma 10`, or spell a skill name correctly with a screen reader.

Two kinds of line:
  * ACTIONS, which just run (fill needs, max skills, add money).
  * VALUES, where left and right change a number and Enter applies it. Skills
    work this way, so you can hear the current level before changing it.

Anything that changes the game reads the result back afterwards where it can:
after this session, a call that returns without complaint is not evidence.
"""
import a11yscan_log as logfile

MONEY_STEPS = (1000, 10000, 100000)

_entries = []
_index = 0
_active = False
_skill_levels = {}


def active():
    return _active


def _sim():
    import a11yscan_world as world
    return world.active_sim()


def _sim_info():
    sim = _sim()
    return getattr(sim, 'sim_info', None) if sim is not None else sim


# ---------------------------------------------------------------------- money

def _add_money(amount):
    import a11yscan_build as build
    try:
        import services
        household = services.active_household()
    except Exception as ex:
        logfile.fail('cheats: no household ({!r})'.format(ex))
        return 'Could not find your household.'
    before = build.funds_available()
    reason = build.funds_reason()
    for label, call in (('add(amount, reason)',
                         lambda: household.funds.add(amount, reason)),
                        ('add(amount, reason, None)',
                         lambda: household.funds.add(amount, reason, None))):
        try:
            call()
        except TypeError:
            continue
        except Exception as ex:
            logfile.write('cheats: money {} failed ({!r})'.format(label, ex))
            continue
        after = build.funds_available()
        if before is None or after is None or after > before:
            logfile.ok('cheats: added {} ({} -> {})'.format(
                amount, before, after))
            return '{:,} simoleons added. You now have {:,}.'.format(
                amount, int(after or 0))
    logfile.fail('cheats: could not add {}'.format(amount))
    return 'Could not add money.'


# ---------------------------------------------------------------------- needs

def _fill_needs():
    sim = _sim()
    if sim is None:
        return 'No active Sim.'
    try:
        from server_commands.statistic_commands import (
            set_commodities_to_best_values)
    except Exception as ex:
        logfile.fail('cheats: needs command unavailable ({!r})'.format(ex))
        return 'Could not fill needs.'
    connection = None
    try:
        import services
        client = services.client_manager().get_first_client()
        connection = getattr(client, 'id', None)
    except Exception:
        connection = None
    # None, not the Sim. This command takes an optional-target parameter and
    # resolves the active Sim itself; handed a real Sim it calls
    # opt_sim._get_target(), which a Sim does not have - so every shape failed
    # and filling one Sim's needs has never once worked. Same mistake that
    # broke Clear all moodlets and Make friends with everyone.
    for label, call in (
            ('(None, visible_only, connection)',
             lambda: set_commodities_to_best_values(None, True, connection)),
            ('(None, connection)',
             lambda: set_commodities_to_best_values(None, connection)),
            ('(None)', lambda: set_commodities_to_best_values(None))):
        try:
            call()
            logfile.ok('cheats: needs filled via {}'.format(label))
            return 'Needs filled.'
        except TypeError:
            continue
        except Exception as ex:
            logfile.write('cheats: needs {} failed ({!r})'.format(label, ex))
    return 'Could not fill needs.'


# --------------------------------------------------------------------- skills

def _skill_types():
    """Every skill the game has, with a readable name."""
    out = []
    try:
        import services
        import sims4.resources
        import a11yscan_dialogs as dialogs
        import a11yscan_world as world
        manager = services.get_instance_manager(sims4.resources.Types.STATISTIC)
    except Exception as ex:
        logfile.fail('cheats: no statistic manager ({!r})'.format(ex))
        return out
    try:
        from statistics.skill import Skill
    except Exception as ex:
        logfile.fail('cheats: no Skill class ({!r})'.format(ex))
        return out
    total = 0
    for stat in manager.types.values():
        total += 1
        # issubclass, not stat.is_skill(): calling that on the CLASS found
        # nothing at all - every statistic was skipped and the skill sliders
        # never appeared. Subclass testing is what worked for relationship
        # tracks, which live in this same manager.
        try:
            if not issubclass(stat, Skill):
                continue
        except Exception:
            continue
        # Hidden skills exist for gameplay bookkeeping and are not worth
        # offering; the ones people mean have a real name.
        name = None
        for attr in ('stat_name', 'display_name', 'skill_name'):
            try:
                name = dialogs.loc_text(getattr(stat, attr, None))
            except Exception:
                name = None
            if name:
                break
        if not name:
            raw = getattr(stat, '__name__', None)
            if not raw or 'hidden' in raw.lower():
                continue
            name = world.prettify(raw)
        out.append((name, stat))
    sim_info = _sim_info()
    fitting = [pair for pair in out if _skill_fits(pair[1], sim_info)]
    # A safety valve. Reading `ages` wrong once emptied a whole menu, so if the
    # filter wants to throw away most of the list, distrust the filter instead
    # of the game and keep everything.
    if out and len(fitting) < len(out) // 2:
        logfile.write('cheats: age filter wanted to drop {} of {} skills, '
                      'ignoring it'.format(len(out) - len(fitting), len(out)))
    else:
        if len(fitting) != len(out):
            logfile.write('cheats: {} skills are the wrong age for this '
                          'Sim'.format(len(out) - len(fitting)))
        out = fitting
    out.sort(key=lambda pair: pair[0].lower())
    logfile.write('cheats: {} skills listed out of {} statistics'.format(
        len(out), total))
    return out


def _skill_fits(stat_type, sim_info):
    """Whether this Sim is the right age to have this skill at all.

    Communication and the other toddler skills, and Social for children, do not
    exist on an adult: add_statistic quietly refuses, the slider reads back
    zero and the mod reported a failure that was really just the wrong age.
    """
    if sim_info is None:
        return True
    try:
        ages = getattr(stat_type, 'ages', None)
        if not ages:
            return True
        return sim_info.age in ages
    except Exception:
        return True


def _skill_max(stat_type):
    """How high this skill actually goes.

    Not every skill stops at 10 - toddler skills top out at 5, and a few packs
    differ - so a slider hardcoded to 10 would offer levels that do not exist.
    """
    for attr in ('max_level', 'max_level_value'):
        try:
            value = getattr(stat_type, attr, None)
            if value:
                return int(value)
        except Exception:
            continue
    try:
        return int(stat_type.convert_to_user_value(stat_type.max_value))
    except Exception:
        return 10


def _skill_level(stat_type, sim):
    try:
        stat = sim.commodity_tracker.get_statistic(stat_type)
        if stat is None:
            return 0
        return int(stat.get_user_value())
    except Exception:
        return 0


def _set_skill(stat_type, level, name):
    sim = _sim()
    if sim is None:
        return 'No active Sim.'
    try:
        raw = stat_type.convert_from_user_value(level)
    except Exception as ex:
        logfile.write('cheats: could not convert level ({!r})'.format(ex))
        raw = level
    tracker = getattr(sim, 'commodity_tracker', None)
    if tracker is None:
        return 'Could not reach that skill.'
    try:
        tracker.add_statistic(stat_type)
    except Exception:
        pass
    if tracker.get_statistic(stat_type) is None:
        logfile.write('cheats: {} would not attach to this Sim'.format(name))
        return '{} is not a skill this Sim can have at their age.'.format(name)
    for label, call in (
            ('tracker.set_value', lambda: tracker.set_value(stat_type, raw)),
            ('stat.set_value',
             lambda: tracker.get_statistic(stat_type).set_value(raw))):
        try:
            call()
        except Exception as ex:
            logfile.write('cheats: skill {} failed ({!r})'.format(label, ex))
            continue
        now = _skill_level(stat_type, sim)
        if now == level:
            logfile.ok('cheats: {} set to {} via {}'.format(name, level, label))
            return '{} is now level {}.'.format(name, level)
        logfile.write('cheats: {} read back as {} after asking for {}'.format(
            name, now, level))
    return 'Could not set {}.'.format(name)


def _max_skills():
    sim = _sim()
    if sim is None:
        return 'No active Sim.'
    done = 0
    for name, stat in _skill_types():
        top = _skill_max(stat)
        if 'level {}'.format(top) in _set_skill(stat, top, name):
            done += 1
    load()
    return 'Maxed {} skills.'.format(done)


# --------------------------------------------------------------------- career

def _career_change(promote=True):
    import a11yscan_careers as careers
    sim_info = _sim_info()
    if sim_info is None:
        return 'No Sim is selected.'
    try:
        held = list(sim_info.career_tracker.careers.values())
    except Exception:
        held = []
    if not held:
        return 'You do not have a job.'
    career = held[0]
    name = careers._career_name(type(career), sim_info) or 'your job'
    before = getattr(career, 'user_level', None)
    for label, call in (
            ('career.promote' if promote else 'career.demote',
             lambda: career.promote() if promote else career.demote()),
            ('tracker level',
             lambda: sim_info.career_tracker.promote_career(type(career))
             if promote else
             sim_info.career_tracker.demote_career(type(career)))):
        try:
            call()
        except Exception as ex:
            logfile.write('cheats: {} failed ({!r})'.format(label, ex))
            continue
        after = getattr(career, 'user_level', None)
        if before is None or after is None or after != before:
            logfile.ok('cheats: {} {} ({} -> {})'.format(
                name, 'promoted' if promote else 'demoted', before, after))
            return '{} is now level {}.'.format(name, after)
    return 'Could not change your job level.'


def _connection():
    try:
        import services
        client = services.client_manager().get_first_client()
        return getattr(client, 'id', None)
    except Exception:
        return None


def _run_command(module_name, func_name, *args):
    """Call a cheat command, trying it with and without a connection."""
    try:
        module = __import__('server_commands.' + module_name,
                            fromlist=[func_name])
        func = getattr(module, func_name)
    except Exception as ex:
        logfile.fail('cheats: {}.{} unavailable ({!r})'.format(
            module_name, func_name, ex))
        return False
    connection = _connection()
    for label, call in (('with connection', lambda: func(*(args + (connection,)))),
                        ('without', lambda: func(*args))):
        try:
            func_result = call()
            logfile.ok('cheats: {} ran {}'.format(func_name, label))
            return True if func_result is None else bool(func_result)
        except TypeError:
            continue
        except Exception as ex:
            # Keep going rather than give up here. The first shape can fail on
            # its arguments as easily as on the work, and the second shape has
            # rescued commands before.
            logfile.write('cheats: {} {} failed ({!r})'.format(
                func_name, label, ex))
            continue
    return False


def _age_up():
    before = getattr(_sim_info(), 'age', None)
    if not _run_command('aging_commands', 'advance_to_next_age', None):
        return 'Could not age them up.'
    after = getattr(_sim_info(), 'age', None)
    return ('Aged up.' if after != before
            else 'Asked to age up, but nothing changed.')


def _age_down():
    before = getattr(_sim_info(), 'age', None)
    if not _run_command('aging_commands', 'reverse_to_previous_age', None):
        return 'Could not age them down.'
    after = getattr(_sim_info(), 'age', None)
    return ('Aged down.' if after != before
            else 'Asked to age down, but nothing changed.')


def _fill_household_needs():
    if _run_command('statistic_commands',
                    'set_commodities_to_best_values_household', True):
        return 'Everyone in the household is topped up.'
    return 'Could not fill the household needs.'


def _clear_moodlets():
    if _run_command('sim_commands', 'remove_all_buffs', None):
        return 'Moodlets cleared.'
    return 'Could not clear the moodlets.'


def _death_toggle(enabled):
    if _run_command('death_commands', 'death_toggle', enabled):
        return 'Death is {}.'.format('on' if enabled else 'off')
    return 'Could not change that.'


def _befriend_everyone():
    # Passing the Sim itself raised "'object_sim' object has no attribute
    # '_get_target'" - the command wants an optional-target parameter, and
    # None means "the active Sim".
    if _run_command('relationship_commands', 'make_all_sims_friends', None):
        return 'Everyone here is now a friend.'
    return 'Could not do that.'


def _introduce_everyone():
    if _run_command('relationship_commands', 'introduce_all_sims'):
        return 'Introduced to everyone.'
    return 'Could not do that.'


# -------------------------------------------------------------- relationships

# Relationship scores run -100 to 100; 10 is a sensible step to hear.
REL_STEP = 10
REL_MIN = -100
REL_MAX = 100


def _rel_tracks():
    """The friendship and romance tracks, as tuning classes.

    Relationship tracks are statistics, not their own resource type, so they
    are found by class. The two people actually mean are the main friendship
    and romance ones; anything else a pack adds is offered after them.
    """
    tracks = []
    try:
        import services
        import sims4.resources
        from relationships.relationship_track import RelationshipTrack
        manager = services.get_instance_manager(sims4.resources.Types.STATISTIC)
    except Exception as ex:
        logfile.fail('cheats: no relationship tracks ({!r})'.format(ex))
        return tracks
    for stat in manager.types.values():
        try:
            if not issubclass(stat, RelationshipTrack):
                continue
        except Exception:
            continue
        raw = getattr(stat, '__name__', '') or ''
        lowered = raw.lower()
        if 'friendship_main' in lowered:
            tracks.append(('friendship', stat, 0))
        elif 'romance_main' in lowered:
            tracks.append(('romance', stat, 1))
    tracks.sort(key=lambda item: item[2])
    logfile.write('cheats: {} relationship tracks'.format(len(tracks)))
    return [(name, stat) for name, stat, _order in tracks]


def _known_sims(sim_info):
    """Sims this one has a relationship with, named."""
    out = []
    try:
        tracker = sim_info.relationship_tracker
    except Exception:
        return out
    for getter in (lambda: tracker.get_target_sim_infos(),
                   lambda: tracker.target_sim_infos()):
        try:
            others = list(getter())
        except Exception:
            continue
        for other in others:
            name = '{} {}'.format(
                getattr(other, 'first_name', '') or '',
                getattr(other, 'last_name', '') or '').strip()
            if name:
                out.append((name, other))
        break
    out.sort(key=lambda pair: pair[0].lower())
    return out


def _rel_score(sim_info, other, track):
    try:
        return int(sim_info.relationship_tracker.get_relationship_score(
            other.sim_id if hasattr(other, 'sim_id') else other.id, track))
    except Exception:
        return 0


def _set_rel(other, track, value, label):
    sim_info = _sim_info()
    if sim_info is None:
        return 'No Sim is selected.'
    target_id = getattr(other, 'sim_id', None) or getattr(other, 'id', None)
    if not target_id:
        return 'Could not identify that Sim.'
    try:
        sim_info.relationship_tracker.set_relationship_score(
            target_id, value, track)
    except Exception as ex:
        logfile.fail('cheats: relationship set failed ({!r})'.format(ex))
        return 'Could not change that relationship.'
    now = _rel_score(sim_info, other, track)
    logfile.ok('cheats: {} set to {} (reads {})'.format(label, value, now))
    if abs(now - value) > 1:
        return '{} asked for {}, but it reads {}.'.format(label, value, now)
    return '{} is now {}.'.format(label, now)


# Objects the posture graph cannot cope with. Straight from the game's own
# exception log:
#
#   [rez] Posture graph threw an exception ... _middle_path_gen
#   Cannot pick up an object: object_GardeningFruit_Trash:... from an invalid
#   surface: object_GardeningPlant_Bush_trash:...
#
# A Sim decides to tidy up, routing throws, she abandons it and picks again -
# which is why a lot can end up filthy with nobody cleaning and needs going
# unmet. No mod is involved; it is base game code failing on these objects.
JAMMING_TUNINGS = ('gardeningfruit_trash', 'gardeningplant_bush_trash')


def _jamming_objects():
    """Objects on the lot that routing cannot handle."""
    found = []
    try:
        import services
        manager = services.object_manager()
        objects = list(manager.get_all())
    except Exception as ex:
        logfile.fail('cheats: could not list objects ({!r})'.format(ex))
        return found
    for obj in objects:
        name = ''
        for getter in (lambda o=obj: o.definition.name,
                       lambda o=obj: type(o).__name__):
            try:
                name = str(getter() or '')
            except Exception:
                name = ''
            if name:
                break
        lowered = name.lower()
        if any(hint in lowered for hint in JAMMING_TUNINGS):
            found.append((name, obj))
    logfile.write('cheats: {} objects match the jamming trash tunings'.format(
        len(found)))
    return found


def _clear_jamming_trash():
    """Delete the trash plants and their fruit, so tidying can work again."""
    found = _jamming_objects()
    if not found:
        return ('No jamming trash found on this lot. If Sims still will not '
                'tidy, the log has what the game is complaining about.')
    gone = 0
    for name, obj in found:
        for label, call in (
                ('schedule_destroy_asap',
                 lambda o=obj: o.schedule_destroy_asap(
                     source=o, cause='a11yscan clearing jammed trash')),
                ('destroy', lambda o=obj: o.destroy(
                    source=o, cause='a11yscan clearing jammed trash'))):
            try:
                call()
                gone += 1
                break
            except Exception as ex:
                logfile.write('cheats: {} on {!r} failed ({!r})'.format(
                    label, name, ex))
    # No counting here. schedule_destroy_asap defers to the end of the tick,
    # so a count taken now cannot possibly have changed - which is exactly
    # what happened the first time: 23 asked for, 23 still there, reported as
    # a failure when the work had not had a chance to happen yet.
    logfile.write('cheats: asked {} of {} jamming objects to go'.format(
        gone, len(found)))
    _schedule_trash_check(len(found))
    return ('Clearing {} piece{} of trash that routing cannot handle. I will '
            'tell you what actually went.'.format(
                len(found), '' if len(found) == 1 else 's'))


# Destruction is deferred, so the result is checked on a later tick.
_trash_check = [0.0, 0]
TRASH_CHECK_SECONDS = 8.0


def _schedule_trash_check(asked):
    import time
    _trash_check[0] = time.monotonic() + TRASH_CHECK_SECONDS
    _trash_check[1] = asked


def _tick_trash():
    if not _trash_check[0]:
        return
    import time
    if time.monotonic() < _trash_check[0]:
        return
    _trash_check[0] = 0.0
    asked = _trash_check[1]
    left = _jamming_objects()
    import a11yscan_speech as speech
    logfile.write('cheats: {} jamming objects left of {}'.format(
        len(left), asked))
    if not left:
        speech.speak('All {} pieces of jammed trash are gone. Your Sims '
                     'should tidy up now.'.format(asked))
        return
    if len(left) < asked:
        speech.speak('{} of {} cleared, {} would not go.'.format(
            asked - len(left), asked, len(left)))
        return
    # Nothing moved: try the blunter call on what is left.
    stubborn = 0
    for name, obj in left:
        try:
            obj.destroy(source=obj, cause='a11yscan clearing jammed trash')
            stubborn += 1
        except Exception as ex:
            logfile.write('cheats: destroy on {!r} failed ({!r})'.format(
                name, ex))
    if stubborn:
        logfile.write('cheats: destroyed {} outright on the second '
                      'attempt'.format(stubborn))
        speech.speak('That needed a second attempt on {} pieces.'.format(
            stubborn))
    else:
        speech.speak('The trash will not go. The log has the reason.')


def _visitors():
    """Sims on the lot who are not in your household.

    Household membership is by id rather than by asking each Sim whether it is
    "playable": a Sim from another household you have played is still a
    visitor, and should still be shown the door.
    """
    out = []
    try:
        import services
        household = services.active_household()
        household_id = getattr(household, 'id', None)
        manager = services.sim_info_manager()
        if not household_id:
            logfile.fail('cheats: no active household, refusing to guess who '
                         'is a visitor')
            return out
    except Exception as ex:
        logfile.fail('cheats: cannot list visitors ({!r})'.format(ex))
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
    for sim in sims:
        info = getattr(sim, 'sim_info', None) or sim
        try:
            if getattr(info, 'household_id', None) == household_id:
                continue
        except Exception:
            continue
        out.append((sim, info))
    return out


LEAVE_HINTS = ('leave', 'walkby', 'walk_by')


def _situations():
    try:
        import services
        manager = services.get_zone_situation_manager()
        return manager, list(manager.running_situations())
    except Exception as ex:
        logfile.fail('cheats: cannot list situations ({!r})'.format(ex))
        return None, []


# Walkbys and ambient street population come and go on their own and are not
# worth offering: ending one just spawns another. What matters is anything
# else, because a situation that outstays its welcome can quietly drive - or
# suppress - what Sims choose to do.
AMBIENT_HINTS = ('walkby', 'walk_by', 'openstreets', 'ambient')


def _endable_situations():
    _manager, running = _situations()
    out = []
    for situation in running:
        name = type(situation).__name__
        if any(hint in name.lower() for hint in AMBIENT_HINTS):
            continue
        situation_id = getattr(situation, 'id', None)
        if situation_id is None:
            continue
        out.append((name, situation_id))
    out.sort(key=lambda pair: pair[0].lower())
    return out


def _end_event(situation_id, name):
    import a11yscan_events as events
    return events.end_event(situation_id, name)


def _end_situation(name, situation_id):
    """Stop one running situation, and check it actually stopped."""
    manager, _running = _situations()
    if manager is None:
        return 'Could not reach the situations.'
    try:
        manager.destroy_situation_by_id(situation_id)
    except Exception as ex:
        logfile.fail('cheats: could not end {!r} ({!r})'.format(name, ex))
        return 'Could not end that one. The log has the reason.'
    still = any(sid == situation_id for _n, sid in _endable_situations())
    logfile.ok('cheats: ended {!r} (id {}), still running: {}'.format(
        name, situation_id, still))
    if still:
        return '{} is still running.'.format(name)
    import a11yscan_world as world
    return '{} has ended.'.format(world.prettify(name))


def _talking_partners(sim):
    """Everyone in the same conversation, so both halves can be stopped.

    Cancelling one Sim's chat ends nothing: the other person is still in the
    social group and starts it again within a second. That is why breaking off
    her side looked like it did nothing at all.
    """
    partners = []
    group = None
    for getter in (lambda: sim.social_group,
                   lambda: next(iter(sim.get_groups_for_sim_gen()), None)):
        try:
            group = getter()
        except Exception:
            continue
        if group is not None:
            break
    if group is not None:
        try:
            for other in group:
                if other is not sim:
                    partners.append(other)
        except Exception as ex:
            logfile.write('cheats: could not read the group ({!r})'.format(ex))
    if partners:
        return partners
    # No readable group: fall back to whoever is stood here, since a
    # conversation needs somebody within talking distance.
    try:
        import services
        manager = services.sim_info_manager()
        for other in manager.instanced_sims_on_active_lot_gen():
            if other is not sim:
                partners.append(other)
    except Exception:
        pass
    return partners


def _register_everything():
    """Re-register everything on the lot, for furniture placed before the fix."""
    import a11yscan_build as build
    return build.register_everything()


def _stop_talking():
    """Break a Sim AND whoever she is talking to out of the conversation.

    The diagnostic found a chat running as a REACTION at High priority, in a
    social group with no anchor and no leader. Nothing displaces that: not
    autonomy, which is Low, and not a player command, which is also High.
    """
    sim = _sim()
    if sim is None:
        return 'No Sim is selected.'
    import a11yscan_actions as actions

    # Shut the GROUP down first. Cancelling interactions on both Sims still
    # leaves the social group standing, and a standing group is what they
    # rejoin a second later - which is what "both want to leave but cannot"
    # actually is. SocialGroup.shutdown ends it for everybody at once.
    closed = _shutdown_groups(sim)

    stopped = list(actions.cancel_autonomous(sim))
    others = 0
    for other in _talking_partners(sim):
        got = actions.cancel_autonomous(other)
        if got:
            others += 1
            stopped.extend('{}: {}'.format(_name_of(other), g) for g in got)
    logfile.ok('cheats: closed {} group(s), broke off {}'.format(
        closed, stopped))
    if not closed and not stopped:
        return 'Nothing was holding them. The log has what they are running.'
    parts = []
    if closed:
        parts.append('Ended {} conversation{}'.format(
            closed, '' if closed == 1 else 's'))
    if stopped:
        parts.append('stopped {} interaction{}'.format(
            len(stopped), '' if len(stopped) == 1 else 's'))
    return '{}. They should both be free now.'.format(', '.join(parts))


def _shutdown_groups(sim):
    """End the social groups this Sim is in.

    SocialGroup.shutdown(finishing_type) is the game's own way out, and it
    ends the conversation for every Sim in it - which is the difference
    between freeing one person and actually stopping the chat.
    """
    finish = None
    for module_name in ('interactions', 'interactions.base.interaction'):
        try:
            module = __import__(module_name, fromlist=['FinishingType'])
            finish = getattr(module, 'FinishingType').USER_CANCEL
            break
        except Exception:
            continue
    groups = []
    for getter in (lambda: list(sim.get_groups_for_sim_gen()),
                   lambda: [sim.social_group]):
        try:
            found = [g for g in getter() if g is not None]
        except Exception:
            continue
        if found:
            groups = found
            break
    closed = 0
    for group in groups:
        try:
            if getattr(group, 'has_been_shutdown', False):
                continue
        except Exception:
            pass
        for label, call in (
                ('shutdown(finishing_type)',
                 lambda g=group: g.shutdown(finish)),
                ('shutdown()', lambda g=group: g.shutdown())):
            try:
                call()
                closed += 1
                logfile.write('cheats: ended {!r} via {}'.format(
                    type(group).__name__, label))
                break
            except Exception as ex:
                logfile.write('cheats: {} on {!r} failed ({!r})'.format(
                    label, type(group).__name__, ex))
    return closed


def _loc(value):
    import a11yscan_dialogs as dialogs
    try:
        return dialogs.loc_text(value)
    except Exception:
        return None


def _aspiration_name(holder, fallback='an aspiration'):
    """The readable name. display_text is the field, not display_name.

    AspirationTrack tunes display_text and description_text; guessing at
    display_name got the prettified class name instead, which is how the
    Knowledge track came out as "track knowledge".
    """
    import a11yscan_world as world
    for attr in ('display_text', 'display_name', 'aspiration_name', 'name'):
        text = _loc(getattr(holder, attr, None))
        if text:
            return text
    raw = getattr(holder, '__name__', '') or ''
    pretty = world.prettify(raw)
    return pretty if pretty and pretty != 'object' else fallback


def _objective_text(objective):
    """What a goal asks for. Objectives tune no display string of their own,
    so the tuning name is tidied up when nothing better exists."""
    import a11yscan_world as world
    for attr in ('display_text', 'objective_description', 'description'):
        text = _loc(getattr(objective, attr, None))
        if text:
            return text
    raw = getattr(objective, '__name__', '') or 'a goal'
    # Strip the prefix every objective carries; it is noise in every line.
    pretty = world.prettify(raw)
    for lead in ('aspiration ', 'objective '):
        if pretty.startswith(lead):
            pretty = pretty[len(lead):]
    return pretty or 'a goal'


def _objectives_of(aspiration):
    out = []
    for attr in ('objective_tuning', 'additional_objectives', 'objectives'):
        try:
            found = list(getattr(aspiration, attr, None) or ())
        except Exception:
            found = []
        for objective in found:
            # additional_objectives wraps its objective in a tuple entry.
            out.append(getattr(objective, 'objective', objective))
    return out


def _milestones_of(track):
    """The milestones of a track, in order, unwrapped.

    get_aspirations() returns cls.aspirations.items() sorted - so (key,
    aspiration) PAIRS, not aspirations. Treating each pair as a milestone is
    why every one read as "a milestone" with no goals: a tuple has neither a
    name nor objectives.
    """
    found = []
    for getter in (lambda: list(track.get_aspirations()),
                   lambda: list(track.aspirations.items()),
                   lambda: list(track.aspirations)):
        try:
            found = getter()
        except Exception:
            continue
        if found:
            break
    out = []
    for entry in found:
        if isinstance(entry, tuple) and len(entry) == 2:
            out.append(entry[1])
        else:
            out.append(entry)
    return out


def aspiration_report():
    """The aspiration, the milestone in progress, and the goals still open."""
    sim = _sim()
    info = getattr(sim, 'sim_info', None) or sim
    if info is None:
        return 'No Sim is selected.'
    tracker = getattr(info, 'aspiration_tracker', None)
    track = None
    try:
        track = tracker.active_track
    except Exception:
        track = None
    if track is None:
        return 'This Sim has no aspiration.'

    done_ids = set()
    try:
        for objective in tracker.completed_objectives:
            done_ids.add(getattr(objective, 'guid64', objective))
    except Exception as ex:
        logfile.write('aspiration: no completed list ({!r})'.format(ex))

    track_name = _aspiration_name(track, 'an aspiration')
    description = None
    for attr in ('description_text', 'description', 'aspiration_description'):
        description = _loc(getattr(track, attr, None))
        if description:
            break
    milestones = _milestones_of(track)
    logfile.write('=' * 60)
    logfile.write('aspiration: {!r} with {} milestones'.format(
        track_name, len(milestones)))

    current = None
    current_left = []
    current_done = []
    finished = 0
    for milestone in milestones:
        objectives = _objectives_of(milestone)
        left = [o for o in objectives
                if getattr(o, 'guid64', o) not in done_ids]
        got = [o for o in objectives if getattr(o, 'guid64', o) in done_ids]
        name = _aspiration_name(milestone, 'a milestone')
        logfile.write('aspiration:   {} - {} of {} done'.format(
            name, len(got), len(objectives)))
        for objective in objectives:
            mark = 'done' if getattr(objective, 'guid64',
                                     objective) in done_ids else 'to do'
            logfile.write('aspiration:     {} - {}'.format(
                mark, _objective_text(objective)))
        if not left and objectives:
            finished += 1
        elif current is None:
            current = name
            current_left = left
            current_done = got
    logfile.write('=' * 60)

    spoken = ['Aspiration: {}'.format(track_name)]
    if description:
        spoken.append(description.strip().rstrip('.'))
    if milestones:
        spoken.append('{} of {} milestones done'.format(
            finished, len(milestones)))
    if current is None:
        spoken.append('the whole aspiration is complete')
    else:
        spoken.append('now on {}, {} of {} goals done'.format(
            current, len(current_done),
            len(current_done) + len(current_left)))
        if current_left:
            spoken.append('still to do: {}'.format(
                '. '.join(_objective_text(o) for o in current_left[:3])))
            if len(current_left) > 3:
                spoken.append('and {} more, all in the log'.format(
                    len(current_left) - 3))
    try:
        for stat in info.commodity_tracker:
            if 'satisfaction' in type(stat).__name__.lower():
                spoken.append('{:,} satisfaction points'.format(
                    int(stat.get_value())))
                break
    except Exception:
        pass
    return '. '.join(spoken) + '.'


def _inspect_one(obj):
    """Log everything about one object, and return (name, can, refused)."""
    import a11yscan_actions as actions
    import a11yscan_world as world
    name = world.object_name(obj)
    logfile.write('inspect: --- {} ---'.format(name))
    for label, getter in (
            ('tuning', lambda: obj.definition.name),
            ('position', lambda: obj.position),
            ('level', lambda: obj.level),
            ('parent', lambda: world.object_name(obj.parent)
                if obj.parent is not None else None),
            ('parent slot', lambda: obj.parent_slot),
            ('in use', lambda: obj.in_use),
            ('on active lot', lambda: obj.is_on_active_lot()),
            ('persistence group', lambda: obj.persistence_group)):
        try:
            logfile.write('inspect:   {} = {!r}'.format(label, getter()))
        except Exception as ex:
            logfile.write('inspect:   {} unreadable ({!r})'.format(label, ex))
    try:
        choices = actions.choices_for(obj)
    except Exception as ex:
        logfile.write('inspect:   could not list interactions ({!r})'.format(ex))
        choices = []
    for choice in choices[:12]:
        logfile.write('inspect:   can do - {}'.format(choice.label))
    rejects = []
    try:
        rejects = actions.last_rejects()
    except Exception:
        rejects = []
    for label, reason in rejects[:15]:
        logfile.write('inspect:   refused - {}: {}'.format(label, reason))
    return (name, len(choices), len(rejects))


def _inspect_object():
    """Everything about what you are pointed at, and why it refuses.

    EVERY object on the tile, not the first. A computer sits on a desk or a
    counter, so the first thing on its tile is the furniture underneath - and
    inspecting only that reports on the counter while saying nothing about the
    computer you actually asked about.
    """
    import a11yscan_grid as grid
    import a11yscan_state as state

    targets = []
    try:
        if grid.active():
            targets = [obj for _name, obj in grid.objects_here()]
    except Exception:
        targets = []
    if not targets:
        entry = state.current_entry()
        obj = getattr(entry, 'obj', None) if entry is not None else None
        if obj is not None:
            targets = [obj]
    if not targets:
        return 'Point at something first, with the grid or the scanner.'

    logfile.write('=' * 60)
    logfile.write('inspect: {} object(s) on this tile'.format(len(targets)))
    summary = []
    for obj in targets:
        try:
            summary.append(_inspect_one(obj))
        except Exception as ex:
            logfile.write('inspect: failed on one object ({!r})'.format(ex))
    logfile.write('=' * 60)
    if not summary:
        return 'Could not inspect anything here.'
    spoken = ['{} things here'.format(len(summary))]
    for name, can, refused in summary[:4]:
        spoken.append('{}: {} can do, {} refused'.format(name, can, refused))
    spoken.append('full detail in the log')
    return '. '.join(spoken) + '.'


def _why_stuck():
    """Everything that decides what a Sim does next, written to the log.

    Autonomy being on, the needs being low and the Sim doing neither is a
    contradiction, and guessing which half is lying has cost a whole evening.
    This asks the game directly: what is she running, what is queued, what
    does autonomy think it is allowed to do, how low are the motives really,
    and is a social group holding her.
    """
    sim = _sim()
    if sim is None:
        return 'No Sim is selected.'
    name = _name_of(sim)
    logfile.write('=' * 60)
    logfile.write('why stuck: {}'.format(name))

    # Autonomy, per Sim and globally - they are different settings and either
    # can stop her.
    try:
        import services
        from autonomy.settings import AutonomyState
        component = sim.autonomy_component
        state = component.get_autonomy_state_setting()
        logfile.write('why stuck: her autonomy reads {!r}'.format(state))
        service = services.autonomy_service()
        logfile.write('why stuck: autonomy service enabled={!r}'.format(
            getattr(service, 'enable_automation', 'unknown')))
        for attr in ('_global_autonomy_settings', 'global_autonomy_settings'):
            group = getattr(service, attr, None)
            if group is not None:
                logfile.write('why stuck: global setting object {!r}'.format(
                    group))
                break
    except Exception as ex:
        logfile.write('why stuck: autonomy unreadable ({!r})'.format(ex))

    # What she is actually doing, and who asked for it.
    for label, holder in (('running', getattr(sim, 'si_state', None)),
                          ('queued', getattr(sim, 'queue', None))):
        try:
            for interaction in list(holder):
                context = getattr(interaction, 'context', None)
                logfile.write('why stuck: {} {} (source={!r}, priority={!r})'
                              .format(label, type(interaction).__name__,
                                      getattr(context, 'source', None),
                                      getattr(context, 'priority', None)))
        except Exception as ex:
            logfile.write('why stuck: {} unreadable ({!r})'.format(label, ex))

    # The motives themselves. "She is exhausted" should be visible here as a
    # number, not inferred from a moodlet.
    low = []
    try:
        tracker = sim.commodity_tracker
        for stat in list(tracker):
            try:
                if not getattr(stat, 'is_motive', False):
                    continue
                value = int(stat.get_value())
                label = type(stat).__name__
                logfile.write('why stuck: motive {} = {}'.format(label, value))
                if value < -50:
                    low.append('{} {}'.format(label, value))
            except Exception:
                continue
    except Exception as ex:
        logfile.write('why stuck: motives unreadable ({!r})'.format(ex))

    # A social group she cannot leave would explain both halves at once.
    try:
        group = getattr(sim, 'social_group', None) or getattr(
            sim, 'get_main_group', lambda: None)()
        logfile.write('why stuck: social group {!r}'.format(group))
        for attr in ('_group_leader', 'anchor', 'is_active_social_group'):
            logfile.write('why stuck:   group {} = {!r}'.format(
                attr, getattr(group, attr, None)))
    except Exception as ex:
        logfile.write('why stuck: social group unreadable ({!r})'.format(ex))

    try:
        groups = list(getattr(sim, 'get_groups_for_sim_gen', lambda: [])())
        logfile.write('why stuck: {} social groups'.format(len(groups)))
    except Exception:
        pass
    logfile.write('=' * 60)
    if low:
        return ('Written to the log. Her lowest needs are {}.'.format(
            ', '.join(low[:3])))
    return 'Written to the log.'


def _situation_report():
    """What the lot is actually running.

    A Sim who picks a new action every second is usually not being autonomous -
    something is pushing work at them. This says what.
    """
    manager, running = _situations()
    if manager is None:
        return 'Could not reach the situations.'
    if not running:
        return 'Nothing is running on this lot.'
    counts = {}
    for situation in running:
        name = type(situation).__name__
        counts[name] = counts.get(name, 0) + 1
    ordered = sorted(counts.items(), key=lambda pair: -pair[1])
    logfile.write('cheats: {} situations running: {}'.format(
        len(running), ', '.join('{} x{}'.format(n, c) for n, c in ordered)))
    top = ', '.join('{}, {}'.format(world_words(n), c) for n, c in ordered[:5])
    return '{} situations running. {}.'.format(len(running), top)


def world_words(raw):
    import a11yscan_world as world
    return world.prettify(raw)


def _clear_leave_situations():
    """Throw away the leave-now situations.

    One of these is created for every Sim asked to leave. If that Sim is then
    removed from the lot - or simply never manages to walk out - the situation
    stays behind trying to run, and a pile of them is exactly the endless
    churn that follows using the leave cheats.

    Only leave and walkby situations are touched. Destroying anything else
    would take a venue's own roles with it.
    """
    manager, running = _situations()
    if manager is None:
        return 'Could not reach the situations.'
    doomed = []
    for situation in running:
        name = type(situation).__name__.lower()
        if any(hint in name for hint in LEAVE_HINTS):
            doomed.append(situation)
    if not doomed:
        return 'No leaving or walkby situations to clear.'
    gone = 0
    for situation in doomed:
        situation_id = getattr(situation, 'id', None)
        if situation_id is None:
            continue
        try:
            manager.destroy_situation_by_id(situation_id)
            gone += 1
        except Exception as ex:
            logfile.write('cheats: could not destroy {!r} ({!r})'.format(
                type(situation).__name__, ex))
    after = len(_situations()[1])
    logfile.ok('cheats: destroyed {} of {} leave situations, {} still '
               'running'.format(gone, len(doomed), after))
    if not gone:
        return 'Could not clear them. The log has the reason.'
    return 'Cleared {} leaving situation{}. {} other things still running.'.format(
        gone, '' if gone == 1 else 's', after)


def _queue_depth(sim):
    for getter in (lambda: len(sim.queue),
                   lambda: len(list(sim.queue))):
        try:
            return int(getter())
        except Exception:
            continue
    return None


def _running_count(sim):
    try:
        return len(list(sim.si_state))
    except Exception:
        return 0


def _autonomy_is_on(sim):
    """True when the Sim will simply refill the queue by themselves."""
    try:
        from autonomy.settings import AutonomyState
        state = sim.autonomy_component.get_autonomy_state_setting()
        return int(state) != int(AutonomyState.DISABLED)
    except Exception:
        return False


def _clear_queue():
    """Throw away everything queued up, and stop what is running.

    cancel_all() empties the queue, but an interaction already RUNNING is not
    in the queue any more - it lives in si_state - so clearing without also
    cancelling those leaves the Sim still doing the thing you wanted stopped.
    """
    sim = _sim()
    if sim is None:
        return 'No Sim is selected.'
    before = _queue_depth(sim)
    running_before = _running_count(sim)

    finish = None
    for module_name in ('interactions', 'interactions.utils.interaction_elements',
                        'interactions.base.interaction'):
        try:
            module = __import__(module_name, fromlist=['FinishingType'])
            finish = getattr(module, 'FinishingType').USER_CANCEL
            break
        except Exception:
            continue
    if finish is None:
        logfile.write('cheats: no FinishingType, cancels will be skipped')

    queue = getattr(sim, 'queue', None)
    if queue is not None:
        try:
            queue.cancel_all()
        except Exception as ex:
            logfile.write('cheats: queue.cancel_all failed ({!r})'.format(ex))

    stopped = 0
    try:
        for interaction in list(sim.si_state):
            if finish is None:
                break
            try:
                interaction.cancel(finish, 'a11yscan cleared the queue')
                stopped += 1
            except Exception as ex:
                logfile.write('cheats: could not cancel {!r} ({!r})'.format(
                    type(interaction).__name__, ex))
    except Exception as ex:
        logfile.write('cheats: could not read running interactions '
                      '({!r})'.format(ex))

    after = _queue_depth(sim)
    logfile.ok('cheats: queue {} -> {}, stopped {} of {} running'.format(
        before, after, stopped, running_before))

    parts = []
    if before is None or after is None:
        parts.append('Queue cleared.')
    elif after >= before and before:
        # Say what actually happened, not what was asked for.
        parts.append('Asked to clear {} but {} are still queued.'.format(
            before, after))
    else:
        parts.append('Cleared {} queued action{}.'.format(
            before or 0, '' if before == 1 else 's'))
    if stopped:
        parts.append('Stopped {} in progress.'.format(stopped))
    if _autonomy_is_on(sim):
        # Otherwise this reads as a broken cheat: it worked, and autonomy put
        # the work straight back.
        parts.append('Autonomy is still on, so they will start something new. '
                     'Turn it off in this menu to stop that.')
    return ' '.join(parts)


def _my_autonomy(state_name, spoken):
    """Set autonomy for the Sim you are playing, and nobody else.

    Autonomy is stored per settings group, and every Sim has their own:

        service.global_autonomy_settings.set_setting(value, group)

    where group comes from that Sim's autonomy component. The settings menu
    changes the global group, which turns the whole world off; this changes
    one Sim, which is what stops your own Sim breaking off what he is doing to
    greet whoever walked in.
    """
    sim = _sim()
    if sim is None:
        return 'No Sim is selected.'
    try:
        import services
        from autonomy.settings import AutonomyState
        component = getattr(sim, 'autonomy_component', None)
        group = component.get_autonomy_settings_group()
        settings = services.autonomy_service().global_autonomy_settings
    except Exception as ex:
        logfile.fail('cheats: no per-Sim autonomy ({!r})'.format(ex))
        return 'Could not reach that setting.'
    value = getattr(AutonomyState, state_name, None)
    if value is None:
        return 'Could not reach that setting.'
    try:
        settings.set_setting(value, group)
    except Exception as ex:
        logfile.fail('cheats: autonomy set failed ({!r})'.format(ex))
        return 'Could not change it.'
    # Read it back off the Sim rather than trusting the write.
    try:
        now = component.get_autonomy_state_setting()
    except Exception:
        now = None
    logfile.ok('cheats: {} autonomy -> {} (reads {!r})'.format(
        _name_of(sim), state_name, now))
    if now is not None and int(now) != int(value):
        return 'Asked for {}, but it still reads something else.'.format(spoken)
    return '{} is now {}.'.format(_name_of(sim), spoken)


def _reset_sim(sim, why='a11yscan unstick'):
    """Put one Sim back to a known state, clearing whatever it is stuck on."""
    try:
        from objects.object_enums import ResetReason
        reason = ResetReason.RESET_EXPECTED
    except Exception:
        reason = None
    for label, call in (
            ('reset(reason, source, cause)',
             lambda: sim.reset(reason, sim, why)),
            ('reset(reason)', lambda: sim.reset(reason)),
            ('reset()', lambda: sim.reset())):
        try:
            call()
            return True
        except Exception as ex:
            logfile.write('cheats: {} on {!r} failed ({!r})'.format(
                label, _name_of(sim), ex))
    return False


def _household_sims():
    """The Sims of your household who are actually standing on the lot."""
    out = []
    try:
        import services
        household = services.active_household()
        household_id = getattr(household, 'id', None)
        manager = services.sim_info_manager()
    except Exception:
        return out
    if not household_id:
        return out
    for attr in ('instanced_sims_on_active_lot_gen', 'instanced_sims_gen'):
        try:
            getter = getattr(manager, attr, None)
            if getter is None:
                continue
            for sim in getter():
                info = getattr(sim, 'sim_info', None) or sim
                if getattr(info, 'household_id', None) == household_id:
                    out.append(sim)
            break
        except Exception:
            continue
    return out


def _unstick_me():
    """Reset the Sim you are playing.

    A Sim whose interaction partner disappeared - which is exactly what
    removing visitors does - can be left retrying something that can never
    finish. That is the endless situation noise. A reset drops the queue and
    puts them back on their feet; nothing about the Sim is lost.
    """
    sim = _sim()
    if sim is None:
        return 'No Sim is selected.'
    if _reset_sim(sim):
        logfile.ok('cheats: reset {!r}'.format(_name_of(sim)))
        return '{} has been reset and should move again.'.format(_name_of(sim))
    return 'Could not reset them. The log has the reason.'


def _unstick_household():
    """Reset everyone in your household who is on the lot."""
    sims = _household_sims()
    if not sims:
        return 'Nobody from your household is here.'
    done = 0
    for sim in sims:
        if _reset_sim(sim):
            done += 1
    logfile.ok('cheats: reset {} of {} household Sims'.format(done, len(sims)))
    if not done:
        return 'Could not reset them. The log has the reason.'
    return 'Reset {} of your Sims.'.format(done)


def _release_from_situations(manager, sim):
    """Let go of whatever is keeping this Sim on the lot.

    make_sim_leave_now_must_run returns immediately if the Sim is already in a
    leave-now situation, so asking a second time does nothing at all - which is
    why repeat calls kept reporting success while eleven Sims stood there. They
    were not refusing; other situations still held them.

    Sims are removed from those situations one at a time rather than the
    situations being destroyed: a situation can hold several Sims, and tearing
    down a venue's own roles would break the lot for everyone else on it.
    """
    freed = 0
    situations = None
    for who in (sim, getattr(sim, 'sim_info', None)):
        if who is None:
            continue
        try:
            situations = list(manager.get_situations_sim_is_in(who))
        except Exception:
            continue
        if situations:
            sim = who
            break
    if not situations:
        return freed
    leave_type = getattr(manager, 'DEFAULT_LEAVE_NOW_MUST_RUN_SITUATION', None)
    for situation in situations:
        if leave_type is not None and type(situation) is leave_type:
            continue
        situation_id = getattr(situation, 'id', None)
        if situation_id is None:
            continue
        try:
            manager.remove_sim_from_situation(sim, situation_id)
            freed += 1
        except Exception as ex:
            logfile.write('cheats: could not free {!r} from {!r} ({!r})'.format(
                _name_of(sim), type(situation).__name__, ex))
    return freed


def _send_visitors_home():
    """Ask every visiting Sim to leave, after letting go of what holds them."""
    try:
        import services
        manager = services.get_zone_situation_manager()
    except Exception as ex:
        logfile.fail('cheats: no situation manager ({!r})'.format(ex))
        return 'Could not reach the visitors.'
    if manager is None:
        return 'Could not reach the visitors.'
    visitors = _visitors()
    if not visitors:
        return 'Nobody here but your household.'
    sent = 0
    freed = 0
    for sim, info in visitors:
        freed += _release_from_situations(manager, sim)
        for who in (sim, info):
            try:
                manager.make_sim_leave_now_must_run(who)
                sent += 1
                break
            except Exception as ex:
                logfile.write('cheats: {!r} would not leave ({!r})'.format(
                    _name_of(info), ex))
    logfile.ok('cheats: asked {} of {} visitors to leave, freed them from {} '
               'situations'.format(sent, len(visitors), freed))
    if not sent:
        return 'None of them would leave. The log has the reason.'
    # They walk out rather than vanishing, so this cannot be checked now. Come
    # back in a few seconds and say what actually happened.
    _schedule_leave_check(len(visitors))
    return ('Asked {} visitor{} to leave. I will tell you if they '
            'actually go.'.format(sent, '' if sent == 1 else 's'))


def _remove_visitors_now():
    """Take every visiting Sim off the lot immediately.

    Nobody is deleted: a Sim object is the instance standing on the lot, and
    its SimInfo - the person, their relationships, their memories - is
    untouched. They simply stop being here, and the game respawns them
    elsewhere as it normally would.
    """
    visitors = _visitors()
    if not visitors:
        return 'Nobody here but your household.'
    gone = 0
    for sim, info in visitors:
        for label, call in (
                ('schedule_destroy_asap',
                 lambda s=sim: s.schedule_destroy_asap(
                     source=s, cause='a11yscan sent them away')),
                ('destroy', lambda s=sim: s.destroy(
                    source=s, cause='a11yscan sent them away'))):
            try:
                call()
                gone += 1
                break
            except Exception as ex:
                logfile.write('cheats: {} on {!r} failed ({!r})'.format(
                    label, _name_of(info), ex))
    logfile.ok('cheats: removed {} of {} visitors from the lot'.format(
        gone, len(visitors)))
    # Your own Sims may have been mid-conversation with someone who has just
    # stopped existing, and will retry that for ever. Reset them so they let
    # go - this is the noise that followed the first version of this cheat.
    if gone:
        for sim in _household_sims():
            _reset_sim(sim, 'a11yscan cleared visitors')
    if not gone:
        return 'Could not remove them. The log has the reason.'
    _schedule_leave_check(len(visitors))
    return 'Removing {} visitor{}.'.format(gone, '' if gone == 1 else 's')


# The result of asking people to leave only shows up seconds later, so it is
# checked afterwards rather than guessed at.
_leave_check = [0.0, 0]
LEAVE_CHECK_SECONDS = 15.0


def _schedule_leave_check(asked):
    import time
    _leave_check[0] = time.monotonic() + LEAVE_CHECK_SECONDS
    _leave_check[1] = asked


def tick():
    """Called from the pump's slow tick. Reports what actually happened."""
    try:
        _tick_trash()
    except Exception as ex:
        logfile.write('cheats: trash check failed ({!r})'.format(ex))
    if not _leave_check[0]:
        return
    import time
    if time.monotonic() < _leave_check[0]:
        return
    _leave_check[0] = 0.0
    asked = _leave_check[1]
    remaining = len(_visitors())
    logfile.write('cheats: {} visitors still here, {} were asked to go'.format(
        remaining, asked))
    import a11yscan_speech as speech
    if remaining == 0:
        speech.speak('Everyone who is not family has gone.')
    elif remaining < asked:
        speech.speak('{} of {} have gone. {} still here.'.format(
            asked - remaining, asked, remaining))
    else:
        speech.speak('{} are still here. Something is holding them; try '
                     'removing them instead.'.format(remaining))


def _name_of(who):
    info = getattr(who, 'sim_info', None) or who
    return '{} {}'.format(getattr(info, 'first_name', '') or '',
                          getattr(info, 'last_name', '') or '').strip()


# ----------------------------------------------------------------- the menu

def _gallery_here():
    import a11yscan_gallery as gallery
    return gallery.move_in_from_gallery()


def _claim_lot():
    import a11yscan_lots as lots
    _ok, message = lots.claim_lot()
    return message


def _why_no_build():
    import a11yscan_build as build
    return build.why_no_build()


def _unlock_build():
    import a11yscan_build as build
    return build.unlock_build()


def _force_leave_build():
    import a11yscan_build as build
    return build.force_leave_build()


def _venue_choices():
    try:
        import a11yscan_venues as venues
        return venues.choices()
    except Exception as ex:
        logfile.write('cheats: no venue list ({!r})'.format(ex))
        return []


def _venue_here():
    import a11yscan_venues as venues
    name = venues.current()
    if not name:
        return 'Could not tell what kind of lot this is.'
    return 'This lot is {}.'.format(name)


def _set_venue(name, tuning):
    import a11yscan_venues as venues
    return venues.set_to(name, tuning)


def load():
    """Build the menu: actions first, then one line per skill."""
    global _entries, _index
    _entries = []
    _index = 0
    sim = _sim()

    for amount in MONEY_STEPS:
        _entries.append({
            'label': 'Add {:,} simoleons'.format(amount),
            'action': lambda a=amount: _add_money(a)})
    _entries.append({'label': 'Fill all needs', 'action': _fill_needs})
    _entries.append({'label': 'Max every skill', 'action': _max_skills})
    _entries.append({'label': 'Fill the whole household\'s needs',
                     'action': _fill_household_needs})
    _entries.append({'label': 'Promote at work',
                     'action': lambda: _career_change(True)})
    _entries.append({'label': 'Demote at work',
                     'action': lambda: _career_change(False)})
    _entries.append({'label': 'Age up this Sim', 'action': _age_up})
    _entries.append({'label': 'Age down this Sim', 'action': _age_down})
    _entries.append({'label': 'Clear all moodlets', 'action': _clear_moodlets})
    _entries.append({'label': 'Turn death off',
                     'action': lambda: _death_toggle(False)})
    _entries.append({'label': 'Turn death back on',
                     'action': lambda: _death_toggle(True)})
    # Events first, by their real names: the generic situation list below
    # carries two dozen background situations with tuning names, and the party
    # you want to stop is somewhere in the middle of it.
    try:
        import a11yscan_events as _events
        for _ename, _eid in _events.endable():
            _entries.append({
                'label': 'End the event: {}'.format(_ename),
                'action': (lambda i=_eid, n=_ename: _end_event(i, n))})
    except Exception as _ex:
        logfile.write('cheats: no event list ({!r})'.format(_ex))
    for _name, _sid in _endable_situations():
        import a11yscan_world as _w
        _entries.append({
            'label': 'End situation: {}'.format(_w.prettify(_name)),
            'action': (lambda n=_name, i=_sid: _end_situation(n, i))})
    _entries.append({'label': 'Fix furniture Sims will not use',
                     'action': _register_everything})
    _entries.append({'label': 'Clear trash that Sims cannot pick up',
                     'action': _clear_jamming_trash})
    _entries.append({'label': 'Send everyone who is not family home',
                     'action': _send_visitors_home})
    _entries.append({'label': 'Remove everyone who is not family right now',
                     'action': _remove_visitors_now})
    _entries.append({'label': "Clear my Sim's queue", 'action': _clear_queue})
    _entries.append({'label': 'Stop this conversation', 'action': _stop_talking})
    _entries.append({'label': 'Why will this object not work',
                     'action': _inspect_object})
    _entries.append({'label': 'Why will my Sim not do anything',
                     'action': _why_stuck})
    _entries.append({'label': 'Why will build mode not open',
                     'action': _why_no_build})
    _entries.append({'label': 'Make this lot mine, so build mode opens',
                     'action': _claim_lot})
    _entries.append({'label': 'Force build mode closed, then press F2',
                     'action': _force_leave_build})
    _entries.append({'label': 'Unlock build mode, then press F2',
                     'action': _unlock_build})
    _entries.append({'label': 'What is running on this lot',
                     'action': _situation_report})
    _entries.append({'label': 'Clear leftover leaving situations',
                     'action': _clear_leave_situations})
    _entries.append({'label': 'Stop my Sim doing things on their own',
                     'action': lambda: _my_autonomy(
                         'DISABLED', 'only doing what you tell them')})
    _entries.append({'label': 'Let my Sim act on their own again',
                     'action': lambda: _my_autonomy(
                         'FULL', 'free to act on their own')})
    _entries.append({'label': 'Unstick my Sim', 'action': _unstick_me})
    _entries.append({'label': 'Unstick my whole household',
                     'action': _unstick_household})
    _entries.append({'label': 'Make friends with everyone here',
                     'action': _befriend_everyone})
    _entries.append({'label': 'Introduce me to everyone',
                     'action': _introduce_everyone})

    _entries.append({'label': 'What kind of lot is this',
                     'action': _venue_here})
    for _vname, _vtuning in _venue_choices():
        _entries.append({
            'label': 'Change this lot to {}'.format(_vname),
            'action': (lambda n=_vname, t=_vtuning: _set_venue(n, t))})

    sim_info = _sim_info()
    if sim_info is not None:
        tracks = _rel_tracks()
        for person, other in _known_sims(sim_info):
            for track_name, track in tracks:
                label = '{}, {}'.format(person, track_name)
                score = _rel_score(sim_info, other, track)
                _skill_levels[label] = score
                _entries.append({
                    'label': label, 'name': label, 'rel': (other, track),
                    'action': None})

    for name, stat in _skill_types():
        level = _skill_level(stat, sim) if sim is not None else 0
        _skill_levels[name] = level
        _entries.append({
            'label': name, 'skill': stat, 'name': name,
            'max': _skill_max(stat), 'action': None})
    logfile.write('cheats: {} lines'.format(len(_entries)))
    return len(_entries)


def open_menu():
    global _active
    if not load():
        return 'Could not build the cheat menu. The log has the reason.'
    _active = True
    return ('Cheats. Up and down to browse, left and right to set a skill '
            'level, enter to use it, backspace to stop. {}'.format(describe()))


def close_menu():
    global _active
    _active = False
    return 'Cheats closed.'


def describe():
    if not _entries:
        return 'Nothing here.'
    entry = _entries[_index % len(_entries)]
    if entry.get('rel') is not None:
        return '{}, {}, left and right to change. {} of {}.'.format(
            entry['name'], _skill_levels.get(entry['name'], 0),
            _index % len(_entries) + 1, len(_entries))
    if entry.get('skill') is not None:
        return '{}, level {} of {}, left and right to change. {} of {}.'.format(
            entry['name'], _skill_levels.get(entry['name'], 0),
            entry.get('max', 10), _index % len(_entries) + 1, len(_entries))
    return '{}. {} of {}.'.format(
        entry['label'], _index % len(_entries) + 1, len(_entries))


def next_entry(step=1):
    global _index
    if not _entries:
        return 'Nothing here.'
    _index = (_index + step) % len(_entries)
    return describe()


def change(step=1):
    """Left and right set the level on a skill line."""
    if not _entries:
        return 'Nothing here.'
    entry = _entries[_index % len(_entries)]
    if entry.get('rel') is not None:
        name = entry['name']
        value = max(REL_MIN, min(REL_MAX,
                                 _skill_levels.get(name, 0) + step * REL_STEP))
        _skill_levels[name] = value
        return '{}, {}. Enter to set it.'.format(name, value)
    if entry.get('skill') is None:
        # Not a value line; move along instead of doing nothing.
        return next_entry(step)
    name = entry['name']
    top = entry.get('max', 10)
    level = max(0, min(top, _skill_levels.get(name, 0) + step))
    _skill_levels[name] = level
    return '{}, level {} of {}. Enter to set it.'.format(name, level, top)


def activate():
    if not _entries:
        return 'Nothing here.'
    entry = _entries[_index % len(_entries)]
    if entry.get('rel') is not None:
        other, track = entry['rel']
        name = entry['name']
        return _set_rel(other, track, _skill_levels.get(name, 0), name)
    if entry.get('skill') is not None:
        name = entry['name']
        return _set_skill(entry['skill'], _skill_levels.get(name, 0), name)
    action = entry.get('action')
    if action is None:
        return entry['label']
    try:
        return action()
    except Exception as ex:
        logfile.fail('cheats: {!r} failed ({!r})'.format(entry['label'], ex))
        return 'That did not work.'
