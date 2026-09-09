"""Enumerating and running interactions on a focused object.

The game's own pie menu (interactions/choices.py ChoiceMenu) builds its list by
generating AffordanceObjectPairs and then running aop.test(context) on each,
discarding anything whose tests fail or that is not user-directed. We do the
same thing here, which is what stops nonsense like "sit" appearing on a mirror.

Falling back to the raw tuning list is a last resort: that list is every
affordance the object could EVER offer, untested, so it over-reports badly. We
record which path produced the list so a11y2.why can show it.
"""
import a11yscan_log as logfile
import a11yscan_speech as speech
import a11yscan_world as world

SOURCE_TESTED = 'tested (matches pie menu)'
SOURCE_STATIC = 'UNTESTED tuning list (over-reports)'
SOURCE_NONE = 'none'

_last_source = SOURCE_NONE
_last_rejects = []


class Choice(object):
    __slots__ = ('label', 'aop', 'affordance', 'context', 'target_hint',
                 'choice_id')

    def __init__(self, label, aop, affordance, context=None, target_hint=None,
                 choice_id=None):
        self.label = label
        self.aop = aop
        self.affordance = affordance
        # Running an interaction with a different context than the one that
        # generated it is why relationship actions were all failing.
        self.context = context
        # Which Sim this is about. Relationship-panel interactions need this
        # even when that Sim is standing right here, so it must not be
        # inferred from whatever object the menu happened to be opened on.
        self.target_hint = target_hint
        # Set when this came from the game's own pie menu, and must be run
        # back through the game rather than re-executed by us.
        self.choice_id = choice_id


def _sim_id_of(thing):
    for attr in ('sim_id', 'id'):
        try:
            value = getattr(thing, attr, None)
            if value:
                return value
        except Exception:
            continue
    return None


def _context(sim, target=None, source=None):
    """Build a context the way the game does: with the client, and with the
    target Sim identified when there is one. Omitting either makes
    relationship-panel interactions fail their tests and refuse to run."""
    from interactions.context import InteractionContext
    from interactions.priority import Priority
    if source is None:
        source = InteractionContext.SOURCE_PIE_MENU
    kwargs = {}
    try:
        import services
        client = services.client_manager().get_first_client()
        if client is not None:
            kwargs['client'] = client
    except Exception:
        pass
    if target is not None:
        target_id = _sim_id_of(target)
        if target_id:
            kwargs['target_sim_id'] = target_id
    # No insert_strategy or must_run_next here. They went in alongside the
    # autonomy hold, chasing the same symptom, and the game's own pie menu
    # does not set them either - so this is back to what the game does.
    for attempt in (dict(kwargs), {'client': kwargs.get('client')}, {}):
        attempt = dict((k, v) for k, v in attempt.items() if v is not None)
        try:
            return InteractionContext(sim, source, Priority.High, **attempt)
        except TypeError:
            continue
    return InteractionContext(sim, source, Priority.High)


# Autonomy is switched off for one Sim while they carry out something you
# asked for, and switched back on the moment they are free. Cancelling her
# choices once is not enough: she re-picks a second later and walks away from
# the shower mid-route, which reads as the command being ignored.
_hold = {'sim_id': None, 'previous': None, 'until': 0.0, 'idle_checks': 0}
# Long enough for a walk across a lot and a shower; short enough that a stuck
# interaction cannot leave her a statue.
HOLD_SECONDS = 120.0


def _autonomy_bits(sim):
    import services
    from autonomy.settings import AutonomyState
    component = getattr(sim, 'autonomy_component', None)
    if component is None:
        raise RuntimeError('no autonomy component')
    return (services.autonomy_service().global_autonomy_settings,
            component.get_autonomy_settings_group(), component, AutonomyState)


def hold_autonomy(sim):
    """Stop this Sim choosing for herself until your instruction is done."""
    import time
    sim_id = getattr(sim, 'id', None)
    if not sim_id:
        return
    if _hold['sim_id'] == sim_id:
        _hold['until'] = time.monotonic() + HOLD_SECONDS
        _hold['idle_checks'] = 0
        return
    try:
        settings, group, component, AutonomyState = _autonomy_bits(sim)
        previous = component.get_autonomy_state_setting()
        settings.set_setting(AutonomyState.DISABLED, group)
    except Exception as ex:
        logfile.write('actions: could not hold autonomy ({!r})'.format(ex))
        return
    # An autonomy request already in flight would still land otherwise.
    try:
        component.cancel_actively_running_full_autonomy_request()
    except Exception:
        pass
    _hold.update({'sim_id': sim_id, 'previous': previous,
                  'until': time.monotonic() + HOLD_SECONDS, 'idle_checks': 0})
    logfile.write('actions: autonomy held for {} (was {!r})'.format(
        sim_id, previous))


def release_autonomy(reason='finished'):
    """Give her free will back."""
    sim_id = _hold['sim_id']
    if not sim_id:
        return
    previous = _hold['previous']
    _hold.update({'sim_id': None, 'previous': None, 'until': 0.0,
                  'idle_checks': 0})
    try:
        import services
        sim = services.object_manager().get(sim_id)
    except Exception:
        sim = None
    if sim is None:
        logfile.write('actions: autonomy hold ended, Sim {} is gone'.format(
            sim_id))
        return
    try:
        settings, group, component, AutonomyState = _autonomy_bits(sim)
        # Back to whatever it was. If that is unreadable, FULL - leaving a Sim
        # permanently unable to act on her own would be far worse than a
        # setting that is briefly wrong.
        target = previous
        if target is None:
            target = AutonomyState.FULL
        settings.set_setting(target, group)
        logfile.ok('actions: autonomy restored to {!r} ({}), still running '
                   '{}'.format(target, reason, _told_to_do(sim)))
    except Exception as ex:
        logfile.write('actions: could not restore autonomy ({!r})'.format(ex))


_warned_off = [False]


def autonomy_tick():
    """Called from the pump. Ends any leftover hold, and says so if a Sim was
    left unable to act by one."""
    import time
    if not _hold['sim_id']:
        _warn_if_switched_off()
        return
    if time.monotonic() >= _hold['until']:
        release_autonomy('time limit reached')
        return
    try:
        import services
        sim = services.object_manager().get(_hold['sim_id'])
        yours = _told_to_do(sim)
    except Exception:
        release_autonomy('could not read the queue')
        return
    # Counting interactions was wrong: a Sim always has one idle behaviour
    # running, so "queue plus running is at most one" called a Sim in the
    # shower idle and gave her free will back mid-wash. What matters is
    # whether anything YOU asked for is still going.
    if yours:
        _hold['idle_checks'] = 0
        return
    # Two quiet checks rather than one: there is a moment between finishing a
    # walk and starting the thing it was a walk to.
    _hold['idle_checks'] += 1
    if _hold['idle_checks'] >= 2:
        release_autonomy('your instruction is finished')


def _warn_if_switched_off():
    """Say once per load if the Sim you are playing cannot act on her own.

    The autonomy hold stored the previous setting in memory, and a reload
    throws that away - so a hold that was in flight when a new build landed
    would leave a Sim switched off with nothing left running to switch her
    back. Saying so is better than silently overriding a setting you might
    have chosen yourself in the cheats menu.
    """
    if _warned_off[0]:
        return
    _warned_off[0] = True
    try:
        import a11yscan_world as world
        from autonomy.settings import AutonomyState
        sim = world.active_sim()
        state = sim.autonomy_component.get_autonomy_state_setting()
        if int(state) != int(AutonomyState.DISABLED):
            return
    except Exception:
        return
    logfile.write('actions: this Sim has autonomy switched off')
    try:
        import a11yscan_speech as speech
        speech.speak('This Sim cannot act on their own. If that was not on '
                     'purpose, turn it back on in the cheats menu.')
    except Exception:
        pass


def _told_to_do(sim):
    """Interactions this Sim is doing because you said so, running or queued."""
    from interactions.context import InteractionContext
    found = []
    for holder in (getattr(sim, 'si_state', None), getattr(sim, 'queue', None)):
        if holder is None:
            continue
        try:
            entries = list(holder)
        except Exception:
            continue
        for interaction in entries:
            try:
                source = getattr(getattr(interaction, 'context', None),
                                 'source', None)
                if source is not None and source != InteractionContext.SOURCE_AUTONOMY:
                    found.append(type(interaction).__name__)
            except Exception:
                continue
    return found


# What blocks a told-to interaction. AUTONOMY is the obvious one; REACTION is
# the one that actually mattered:
#
#   running sim_Chat (source=InteractionSource.REACTION, priority=Priority.High)
#
# A reaction chat runs at HIGH priority, the same as a player command, and
# equal priority does not displace - so neither autonomy changes nor anything
# the player asked for could move a Sim out of it. That single line explained
# an evening of Sims who would not shower, eat or sleep.
BLOCKING_SOURCES = ('AUTONOMY', 'REACTION', 'SOCIAL_ADJUSTMENT')


# After a command, watch what becomes of it. An interaction that is accepted
# and then never happens looks identical to one that was refused, and the
# difference - queued then cancelled, versus never queued - decides where to
# look next.
_watch = {'sim_id': None, 'label': '', 'until': 0.0, 'ticks': 0}
WATCH_SECONDS = 12.0


def watch_command(sim, label):
    import time
    _watch.update({'sim_id': getattr(sim, 'id', None), 'label': label,
                   'until': time.monotonic() + WATCH_SECONDS, 'ticks': 0})


def watch_tick():
    """Called from the pump. Reports what the Sim is doing after a command."""
    import time
    if not _watch['sim_id']:
        return
    if time.monotonic() >= _watch['until']:
        logfile.write('watch: {!r} - stopped watching'.format(_watch['label']))
        _watch['sim_id'] = None
        return
    _watch['ticks'] += 1
    # Every fourth slow tick, so about once a second.
    if _watch['ticks'] % 4:
        return
    try:
        import services
        sim = services.object_manager().get(_watch['sim_id'])
        running = []
        for interaction in sim.si_state:
            context = getattr(interaction, 'context', None)
            running.append('{}({})'.format(
                type(interaction).__name__,
                getattr(getattr(context, 'source', None), 'name', '?')))
        queued = [type(i).__name__ for i in sim.queue]
    except Exception as ex:
        logfile.write('watch: unreadable ({!r})'.format(ex))
        _watch['sim_id'] = None
        return
    logfile.write('watch: {!r} +{}s running {} queued {}'.format(
        _watch['label'], _watch['ticks'] // 4, running[:4], queued[:4]))


def cancel_autonomous(sim):
    """Stop what a Sim did not choose deliberately, so your command can start.

    Anything the player asked for is left alone. Priority and queue position
    decide what runs NEXT, but neither interrupts something already under way.
    """
    stopped = []
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
        logfile.write('actions: no FinishingType, leaving autonomy running')
        return stopped
    try:
        running = list(sim.si_state)
    except Exception as ex:
        logfile.write('actions: could not read running interactions '
                      '({!r})'.format(ex))
        return stopped
    for interaction in running:
        try:
            context = getattr(interaction, 'context', None)
            source = getattr(context, 'source', None)
            source_name = getattr(source, 'name', str(source)) or ''
            if not any(hint in source_name.upper()
                       for hint in BLOCKING_SOURCES):
                continue
            interaction.cancel(finish, 'a11yscan: you asked for something else')
            stopped.append('{} ({})'.format(
                type(interaction).__name__, source_name))
        except Exception as ex:
            logfile.write('actions: could not stop {!r} ({!r})'.format(
                type(interaction).__name__, ex))
    if stopped:
        logfile.write('actions: stopped autonomous {}'.format(stopped))
    return stopped


def _is_user_directed(affordance):
    try:
        if getattr(affordance, 'debug', False) or getattr(affordance, 'cheat', False):
            return False
        return bool(getattr(affordance, 'allow_user_directed', True))
    except Exception:
        return True


def label_for(aop, affordance, context=None, target=None):
    """The interaction's real display name.

    Interaction.get_name is a CLASSMETHOD taking (inst, target, context), so
    calling aop.get_name() with no arguments simply raised and every label fell
    back to tuning text like "social flatter friendly always on".
    """
    import a11yscan_dialogs as dialogs
    if target is None:
        target = getattr(aop, 'target', None)

    # How the game itself does it, read out of create_pie_menu_message:
    #
    #   name = aop_affordance.get_name(aop.target, context,
    #                                  **aop.interaction_parameters)
    #
    # interaction_parameters is the half that was missing. A mod's entries take
    # their tokens from there, which is why they read as "Accepted Sexual Acts
    # ()" and "Choose 's Preferences" - the brackets and the name were empty
    # because nothing filled them.
    try:
        params = dict(getattr(aop, 'interaction_parameters', None) or {})
    except Exception:
        params = {}

    attempts = []
    for method_name in ('get_name', '_get_name'):
        method = getattr(affordance, method_name, None)
        if method is None:
            continue
        if params:
            attempts.append(lambda m=method: m(target, context, **params))
            attempts.append(lambda m=method: m(None, target, context, **params))
        attempts.append(lambda m=method: m(None, target, context))
        attempts.append(lambda m=method: m(None, target, context, False))
        attempts.append(lambda m=method: m(target, context))
    display = getattr(affordance, 'display_name', None)
    if display is not None:
        attempts.append(lambda d=display: d(target))
        attempts.append(lambda d=display: d())
        attempts.append(lambda d=display: d)
    attempts.append(lambda: aop.get_name())
    attempts.append(lambda: aop.name)

    for attempt in attempts:
        try:
            text = dialogs.loc_text(attempt())
        except Exception:
            continue
        if text:
            return text

    for getter in (lambda: affordance.__name__, lambda: type(affordance).__name__):
        try:
            value = getter()
            if value:
                return world.prettify_interaction(value)
        except Exception:
            continue
    return 'interaction'


def last_source():
    return _last_source


def last_rejects():
    """[(label, reason)] for interactions that failed their tests."""
    return list(_last_rejects)


def _harvest(aop_iter, context, seen=None):
    """Keep only interactions whose tests actually pass, like ChoiceMenu does."""
    if seen is None:
        seen = set()
    found = []
    for aop in aop_iter:
        affordance = getattr(aop, 'affordance', None) or aop
        if not _is_user_directed(affordance):
            continue
        label = label_for(aop, affordance, context)
        try:
            result = aop.test(context)
        except Exception as ex:
            # A test that blows up is not a test that passed.
            _last_rejects.append((label, 'test raised {!r}'.format(ex)))
            continue
        if not result:
            reason = getattr(result, 'reason', None) or 'test failed'
            _last_rejects.append((label, str(reason)))
            continue
        if label in seen:
            continue
        seen.add(label)
        found.append(Choice(label, aop, affordance, context))
    return found


def phone_choices(sim=None):
    """What the phone offers, straight from the game's own phone menu source."""
    global _last_source, _last_rejects
    _last_source = SOURCE_NONE
    _last_rejects = []
    sim = sim or world.active_sim()
    if sim is None:
        return []
    try:
        context = _context(sim)
    except Exception as ex:
        speech.log('interaction context failed ({!r})'.format(ex))
        return []
    try:
        found = _harvest(sim.potential_phone_interactions(context), context)
    except Exception as ex:
        speech.log('potential_phone_interactions failed ({!r})'.format(ex))
        return []
    _last_source = SOURCE_TESTED
    found.sort(key=lambda choice: choice.label)
    return found


_relation_debug = []


def _contexts(sim, target=None):
    """Contexts to try, each carrying the client and the target Sim."""
    from interactions.context import InteractionContext
    out = []
    for name in ('SOURCE_PIE_MENU', 'SOURCE_SCRIPT_WITH_USER_INTENT',
                 'SOURCE_SCRIPT'):
        source = getattr(InteractionContext, name, None)
        if source is None:
            continue
        try:
            out.append((name, _context(sim, target=target, source=source)))
        except Exception:
            continue
    return out


def relation_debug():
    return list(_relation_debug)


def sub_choices(choice, target, sim=None):
    """The socials nested under a pie-menu category.

    Friendly, Funny, Romantic and the rest are not top-level interactions: they
    are sub-interactions of a super interaction, which is why listing only
    potential_interactions never showed them.
    """
    sim = sim or world.active_sim()
    if sim is None or choice is None:
        return []
    affordance = choice.affordance
    generator = getattr(affordance, 'potential_pie_menu_sub_interactions_gen', None)
    if generator is None:
        return []
    context = getattr(choice, 'context', None)
    if context is None:
        try:
            context = _context(sim, target=target)
        except Exception:
            return []

    real_target = target
    if real_target is not None and not hasattr(real_target, 'posture_state'):
        for getter in (lambda: real_target.get_sim_instance(),
                       lambda: real_target.get_sim_instance(allow_hidden_flags=-1)):
            try:
                resolved = getter()
                if resolved is not None:
                    real_target = resolved
                    break
            except Exception:
                continue

    for name, call in (('(target, context)',
                        lambda: generator(real_target, context)),
                       ('(context, target)',
                        lambda: generator(context, real_target)),
                       ('(context)', lambda: generator(context))):
        try:
            found = _harvest(call(), context)
        except TypeError:
            continue
        except Exception as ex:
            logfile.write('sub-interactions {} raised {!r}'.format(name, ex))
            continue
        if found:
            for item in found:
                item.target_hint = getattr(choice, 'target_hint', None)
            logfile.write('sub-interactions for {!r}: {} via {}'.format(
                choice.label, len(found), name))
            found.sort(key=lambda item: item.label)
            return found
    logfile.write('no sub-interactions for {!r}'.format(choice.label))
    return []


_PIE_REFERENCE_ID = 91101


def pie_menu_choices(target, sim=None):
    """Ask the game to build its real pie menu for `target`, then read it.

    Social mixers (Flirt, Tell Joke, Compliment) are assembled by the game and
    never appear in potential_interactions. generate_choices takes fourteen
    arguments describing the click - target, pick type, world position, lot,
    level, modifier keys and a reference id - and leaves the resulting
    ChoiceMenu on the client. select_choice runs one, using the SAME reference
    id. Passing only the target id, as an earlier attempt did, left the client
    holding a previous menu.
    """
    import a11yscan_dialogs as dialogs
    sim = sim or world.active_sim()
    if sim is None or target is None:
        return []
    try:
        import services
        from server.pick_info import PickType
        from server_commands import interaction_commands
        client = services.client_manager().get_first_client()
    except Exception as ex:
        logfile.write('pie menu: setup failed {!r}'.format(ex))
        return []
    if client is None:
        return []

    target_id = getattr(target, 'id', None) or _sim_id_of(target)
    if not target_id:
        return []

    is_sim = bool(getattr(target, 'is_sim', False))
    pick_type = PickType.PICK_SIM if is_sim else PickType.PICK_OBJECT
    try:
        position = target.position
        x, y, z = float(position.x), float(position.y), float(position.z)
    except Exception:
        x = y = z = 0.0
    try:
        level = int(getattr(target, 'level', 0) or 0)
    except Exception:
        level = 0
    try:
        lot_id = int(services.active_lot().lot_id)
    except Exception:
        lot_id = 0

    try:
        interaction_commands.generate_choices(
            target_id, pick_type, x, y, z, lot_id, level,
            False, False, False, _PIE_REFERENCE_ID, 0, 0, True,
            _connection=client.id)
    except Exception as ex:
        logfile.write('pie menu: generate_choices raised {!r}'.format(ex))
        return []

    menu = getattr(client, 'choice_menu', None)
    if menu is None:
        logfile.write('pie menu: client has no choice_menu')
        return []

    out = []
    seen = set()
    try:
        entries = list(menu)
    except Exception as ex:
        logfile.write('pie menu: iteration failed {!r}'.format(ex))
        return []
    for entry in entries:
        choice_id = None
        item = entry
        if isinstance(entry, tuple) and len(entry) == 2:
            choice_id, item = entry
        aop = getattr(item, 'aop', None) or item
        affordance = getattr(aop, 'affordance', None) or aop
        if choice_id is None:
            for attr in ('choice_id', 'aop_id', 'unique_id'):
                choice_id = (getattr(item, attr, None)
                             or getattr(aop, attr, None))
                if choice_id is not None:
                    break
        # The menu item the game built already carries its name as a
        # LocalizedString with the tokens filled in. Re-deriving it from the
        # affordance calls get_name with no instance, which is why a mod's
        # entries read as "Accepted Sexual Acts ()" and "Choose 's
        # Preferences" - the instance is what supplies those tokens.
        label = None
        for attr in ('name', 'display_name', 'loc_name'):
            try:
                label = dialogs.loc_text(getattr(item, attr, None))
            except Exception:
                label = None
            if label:
                break
        if not label:
            item_context = (getattr(item, 'context', None)
                            or getattr(aop, 'context', None))
            label = label_for(aop, affordance, item_context, target)
        if label in seen:
            continue
        seen.add(label)
        out.append(Choice(label, aop, affordance, None, None, choice_id))
    logfile.write('pie menu: {} entries for target {} (pick_type={})'.format(
        len(out), target_id, pick_type))
    return out


def merged_choices(target, sim=None):
    """Our own enumeration plus whatever the game's menu adds.

    Merging rather than replacing: the game's menu is the only source of social
    mixers, but our list is known good and must not be lost if the command
    misbehaves again.
    """
    base = choices_for(target, sim)
    base_labels = set(c.label for c in base)
    try:
        extra = [c for c in pie_menu_choices(target, sim)
                 if c.label not in base_labels]
    except Exception as ex:
        logfile.write('pie merge failed {!r}'.format(ex))
        extra = []
    if extra:
        logfile.write('pie menu added {} interactions our list lacked'.format(
            len(extra)))
        for choice in extra[:12]:
            logfile.write('  added: {!r}'.format(choice.label))
    return base + extra



def _dialog_ids():
    """Ids of every dialog the game currently considers live."""
    try:
        import a11yscan_dialogs as dialogs
        found = set()
        for dialog in dialogs.service_dialogs():
            found.add(id(dialog) if getattr(dialog, 'dialog_id', None) is None
                      else dialog.dialog_id)
        return found
    except Exception:
        return set()


def _announce_new_dialog():
    """Read out the pop-up an interaction just opened.

    The dialog hooks normally do this, but a class the hooks never saw arrives
    silently - and a modal nobody announced is indistinguishable from the mod
    having died.
    """
    try:
        import a11yscan_dialogs as dialogs
        import a11yscan_state as state
        dialog = dialogs.current()
        if dialog is not None:
            state.on_dialog_shown(dialog)
    except Exception as ex:
        logfile.write('pie select: could not read the new dialog ({!r})'.format(ex))


def _queue_depth(sim):
    """Rough size of the Sim's interaction queue, for verifying a selection."""
    for getter in (lambda: len(sim.queue),
                   lambda: len(list(sim.queue)),
                   lambda: len(list(sim.si_state.sis))):
        try:
            return int(getter())
        except Exception:
            continue
    return None


def run_pie_choice(choice, target, sim=None):
    """Run something from the game's own menu, through the game.

    The menu is regenerated first: choice ids belong to one generation, and an
    id from a menu built a minute ago is quietly discarded.
    """
    sim = sim or world.active_sim()
    if sim is None or target is None:
        return False
    try:
        import services
        from server_commands import interaction_commands
        client = services.client_manager().get_first_client()
    except Exception as ex:
        logfile.fail('pie select: setup failed {!r}'.format(ex))
        return False
    if client is None:
        return False

    fresh = pie_menu_choices(target, sim)
    match = None
    for candidate in fresh:
        if candidate.label == choice.label:
            match = candidate
            break
    if match is None or match.choice_id is None:
        logfile.fail('pie select: {!r} absent from freshly built menu'.format(
            choice.label))
        return False

    before = _queue_depth(sim)
    # Queue depth is not the only way an interaction succeeds. A picker
    # interaction - which is most of what a content mod adds - queues nothing
    # and opens a dialog instead, so judging it by the queue alone called every
    # one of them a failure and then ignored the dialog it had just opened.
    dialogs_before = _dialog_ids()
    result = None
    try:
        result = interaction_commands.select_choice(
            match.choice_id, _PIE_REFERENCE_ID, _connection=client.id)
    except Exception as ex:
        logfile.fail('pie select: select_choice raised {!r}'.format(ex))
        return False
    after = _queue_depth(sim)
    opened = _dialog_ids() - dialogs_before
    if opened:
        logfile.ok('{} opened a dialog via select_choice id={} ({} new)'.format(
            choice.label, match.choice_id, len(opened)))
        _announce_new_dialog()
        return True

    # The command returns nothing useful, so confirm by effect: a queued
    # interaction means it really ran.
    if before is not None and after is not None and after > before:
        logfile.ok('{} via select_choice id={} (queue {} -> {})'.format(
            choice.label, match.choice_id, before, after))
        return True
    logfile.write('pie select: {!r} id={} returned {!r}, queue {} -> {}'.format(
        choice.label, match.choice_id, result, before, after))
    if result:
        logfile.ok('{} via select_choice (reported by game)'.format(choice.label))
        return True
    logfile.fail('{}: select_choice had no effect (no queue change, no '
                 'dialog)'.format(choice.label))
    return False


def probe_mixers(target, sim=None):
    """Diagnostic only: is the mixer system reachable for socials?"""
    sim = sim or world.active_sim()
    if sim is None:
        return
    for name in ('get_potential_mixer_targets', 'potential_behavior_affordances_gen',
                 'potential_joinable_interactions_gen'):
        method = getattr(sim, name, None)
        if method is None:
            logfile.write('mixer probe: {} absent'.format(name))
            continue
        for shape, call in (('()', lambda m=method: m()),
                            ('(target)', lambda m=method: m(target))):
            try:
                result = list(call())
                logfile.write('mixer probe: {}{} -> {} items'.format(
                    name, shape, len(result)))
                break
            except Exception as ex:
                logfile.write('mixer probe: {}{} raised {!r}'.format(
                    name, shape, ex))


class Category(object):
    """A pie-menu category holding interactions, so the menu can be browsed
    the way the game presents it rather than as one flat list."""

    __slots__ = ('label', 'items')

    def __init__(self, label, items):
        self.label = label
        self.items = items


def category_of(choice):
    """Localized pie-menu category name for an interaction, or None."""
    import a11yscan_dialogs as dialogs
    affordance = choice.affordance
    category = None
    for attr in ('category', 'pie_menu_category'):
        try:
            category = getattr(affordance, attr, None)
            if category is not None:
                break
        except Exception:
            continue
    if category is None:
        return None
    for attr in ('display_name', 'pie_menu_category_name', 'category_name',
                 'name', 'title'):
        try:
            label = dialogs.loc_text(getattr(category, attr, None))
            if label:
                return label
        except Exception:
            continue
    try:
        raw = getattr(category, '__name__', None) or type(category).__name__
        pretty = world.prettify_interaction(raw)
        if pretty and pretty != 'object':
            return pretty
    except Exception:
        pass
    return None


def group_by_category(choices, minimum=8):
    """Split a long interaction list into categories. Returns a list mixing
    Category objects and loose Choices."""
    if len(choices) < minimum:
        return list(choices)
    buckets = {}
    loose = []
    for choice in choices:
        label = category_of(choice)
        if label:
            buckets.setdefault(label, []).append(choice)
        else:
            loose.append(choice)
    if not buckets:
        return list(choices)
    out = []
    for label in sorted(buckets):
        items = sorted(buckets[label], key=lambda c: c.label)
        # A category holding one thing is just noise; show the thing itself.
        if len(items) == 1:
            out.append(items[0])
        else:
            out.append(Category(label, items))
    out.extend(sorted(loose, key=lambda c: c.label))
    logfile.write('grouped {} interactions into {} categories, {} loose'.format(
        len(choices), len(buckets), len(loose)))
    return out


def expand_socials(choices, target, sim=None):
    """Pull nested socials up into the menu so they are actually reachable.

    Which parent owns Friendly/Funny/Romantic is not obvious from its name, so
    rather than make the player hunt for the right entry we probe every one and
    surface whatever they contain as "Parent: Social".
    """
    extra = []
    found_any = 0
    for choice in list(choices):
        try:
            subs = sub_choices(choice, target, sim)
        except Exception as ex:
            logfile.write('sub probe failed for {!r} ({!r})'.format(
                choice.label, ex))
            continue
        if not subs:
            continue
        found_any += len(subs)
        logfile.write('category {!r}: {} socials'.format(
            choice.label, len(subs)))
        for sub in subs:
            sub.label = '{}: {}'.format(choice.label, sub.label)
            extra.append(sub)
    logfile.write('expand_socials added {} from {} parents'.format(
        found_any, len(choices)))
    return extra


def relation_panel_choices(target=None, sim=None):
    """The relationship-panel menu for another Sim: Invite to Lot, Ask on Date.

    A distinct set from both the pie menu and the phone, reached through
    Sim.potential_relation_panel_interactions over _relation_panel_affordances.
    """
    global _last_source, _last_rejects, _relation_debug
    _relation_debug = []
    _last_rejects = []
    _last_source = SOURCE_NONE
    sim = sim or world.active_sim()
    if sim is None:
        return []
    method = getattr(sim, 'potential_relation_panel_interactions', None)
    if method is None:
        _relation_debug.append('method not present on this build')
        return []

    best_raw = []
    best_context = None
    for context_name, context in _contexts(sim, target):
        shapes = []
        if target is not None:
            shapes.append(('(context, target)',
                           lambda c=context: method(c, target)))
            shapes.append(('(target, context)',
                           lambda c=context: method(target, c)))
        shapes.append(('(context)', lambda c=context: method(c)))
        for shape_name, call in shapes:
            try:
                raw = list(call())
            except TypeError:
                _relation_debug.append(
                    '{} {}: wrong signature'.format(context_name, shape_name))
                continue
            except Exception as ex:
                _relation_debug.append(
                    '{} {}: raised {!r}'.format(context_name, shape_name, ex))
                continue
            _relation_debug.append(
                '{} {}: {} raw'.format(context_name, shape_name, len(raw)))
            if not raw:
                continue
            tested = _harvest(iter(raw), context)
            _relation_debug.append('    passed tests: {}'.format(len(tested)))
            if tested:
                _last_source = SOURCE_TESTED
                tested.sort(key=lambda choice: choice.label)
                for choice in tested:
                    choice.target_hint = target
                logfile.ok('relation panel: {} via {} {}'.format(
                    len(tested), context_name, shape_name))
                return tested
            for label, reason in _last_rejects[:8]:
                logfile.write('relation reject {}: {}'.format(
                    label, str(reason)[:100]))
            if not best_raw:
                best_raw = raw
                best_context = context

    if best_raw:
        # The call worked but every test failed - most likely our context is
        # not the one the panel uses. Show them anyway: a listed option you can
        # try beats a menu that silently falls back to the phone.
        out = []
        seen = set()
        for aop in best_raw:
            affordance = getattr(aop, 'affordance', None) or aop
            label = label_for(aop, affordance)
            if label in seen:
                continue
            seen.add(label)
            out.append(Choice(label, aop, affordance, best_context, target))
        out.sort(key=lambda choice: choice.label)
        _last_source = SOURCE_STATIC
        _relation_debug.append('returning {} untested'.format(len(out)))
        for entry in _relation_debug:
            logfile.write('relation: {}'.format(entry))
        return out
    for entry in _relation_debug:
        logfile.write('relation: {}'.format(entry))
    logfile.fail('relation panel produced nothing')
    return []


def choices_for(obj, sim=None):
    """Interactions genuinely available on obj right now."""
    global _last_source, _last_rejects
    _last_source = SOURCE_NONE
    _last_rejects = []

    sim = sim or world.active_sim()
    if sim is None or obj is None:
        return []

    try:
        context = _context(sim)
    except Exception as ex:
        speech.log('interaction context failed ({!r})'.format(ex))
        return []

    found = []
    seen = set()
    generated = False

    try:
        found = _harvest(obj.potential_interactions(context), context, seen)
        generated = True
    except Exception as ex:
        speech.log('potential_interactions failed ({!r})'.format(ex))
        generated = False

    if generated:
        _last_source = SOURCE_TESTED
        found.sort(key=lambda c: c.label)
        return found

    # Last resort only: unfiltered and known to over-report.
    for affordance in world.player_affordances(obj):
        label = world.prettify_interaction(getattr(affordance, '__name__', 'interaction'))
        if label in seen:
            continue
        seen.add(label)
        found.append(Choice(label, None, affordance))
    _last_source = SOURCE_STATIC if found else SOURCE_NONE
    found.sort(key=lambda c: c.label)
    return found


def run(choice, obj, sim=None):
    """Queue the chosen interaction on the active Sim. Returns True on success."""
    sim = sim or world.active_sim()
    if sim is None or choice is None:
        return False
    context = getattr(choice, 'context', None)
    if context is None:
        try:
            context = _context(sim, target=obj)
        except Exception as ex:
            speech.log('interaction context failed ({!r})'.format(ex))
            return False

    hint = getattr(choice, 'target_hint', None)
    if hint is not None:
        obj = hint
    logfile.write('RUN {!r} on {!r} (aop={}, ctx={}, hinted={})'.format(
        choice.label, obj, choice.aop is not None, context is not None,
        hint is not None))
    # NOTHING is cancelled here any more. Cancelling first made the game queue
    # its own "stop and stand up" interaction - sim-stand(BODY_CANCEL_AOP) -
    # at high priority, and that displaced the very command being issued. The
    # watch log showed it plainly: the commanded interaction never reached the
    # queue at all, only a body-cancel stand followed by autonomy picking
    # something else. The game displaces what it needs to on its own.
    #
    # cancel_autonomous is still available for "Stop this conversation", where
    # cancelling IS the whole point and nothing is pushed afterwards.

    # Everything below this point is a retry, and a retry of an interaction
    # that already opened a dialog is what froze the game: the picker was run
    # a second time while its own modal was still up, and the mod's code re-
    # entered itself on the simulation thread. So the presence of a new dialog
    # ends the attempt, on every route, not just the pie menu one.
    dialogs_at_start = _dialog_ids()

    def _stop_for_dialog(where):
        if not (_dialog_ids() - dialogs_at_start):
            return False
        logfile.ok('{}: a dialog opened at {}, not retrying'.format(
            choice.label, where))
        _announce_new_dialog()
        return True

    if getattr(choice, 'choice_id', None) is not None:
        if run_pie_choice(choice, obj, sim):
            return True
        if _stop_for_dialog('the pie menu route'):
            return True
        # Fall through: the game's own route failed, so try ours.

    watch_command(sim, choice.label)
    if choice.aop is not None:
        logfile.write('{}: trying aop.test_and_execute'.format(choice.label))
        try:
            if choice.aop.test_and_execute(context):
                logfile.ok('{} via aop.test_and_execute'.format(choice.label))
                return True
            logfile.write('{}: aop.test_and_execute returned false'.format(
                choice.label))
        except Exception as ex:
            logfile.fail('{}: aop execute raised {!r}'.format(choice.label, ex))
        if _stop_for_dialog('test_and_execute'):
            return True

    # Crafting interactions (cooking, grilling) require crafting_process and
    # phase, which live on the AOP rather than the affordance.
    kwargs = {}
    if choice.aop is not None:
        for attr in ('interaction_parameters', '_interaction_parameters'):
            try:
                found = getattr(choice.aop, attr, None)
                if found:
                    kwargs = dict(found)
                    break
            except Exception:
                continue

    # Relationship-panel interactions are picker interactions: the Sim they
    # act on arrives as picked_item_ids, not as the AOP target. Without it the
    # game refuses with "target_sims list is empty", and passing a SimInfo as
    # the target instead crashes in posture handling.
    # A SimInfo target always crashes in posture handling, so for those never
    # try it at all - go straight to the combination that works.
    # A relationship-panel interaction always needs picked_item_ids, whether
    # or not the Sim is physically present.
    is_sim_info = obj is not None and (
        hint is not None or not hasattr(obj, 'posture_state'))
    candidates = [] if is_sim_info else [('as given', obj, {})]
    if is_sim_info:
        target_id = _sim_id_of(obj)
        picked = {}
        if target_id:
            picked = {'picked_item_ids': frozenset((target_id,))}
        instance = None
        for getter in (lambda: obj.get_sim_instance(),
                       lambda: obj.get_sim_instance(allow_hidden_flags=-1)):
            try:
                instance = getter()
                if instance is not None:
                    break
            except Exception:
                continue
        # Confirmed working order: the acting Sim with the other Sim supplied
        # as a picked item is what the game accepts.
        if picked:
            candidates.append(('acting Sim + picked', sim, picked))
            if instance is not None:
                candidates.append(('their Sim + picked', instance, picked))
            candidates.append(('no target + picked', None, picked))
        if instance is not None:
            candidates.append(('their live Sim', instance, {}))
        candidates.append(('acting Sim', sim, {}))

    for label, target, extra in candidates:
        # Six candidates, each of which may test, execute AND push - so a
        # picker interaction could be run a dozen times over. One dialog is the
        # signal that it already worked; carrying on from here is what wedged
        # the simulation thread.
        if _stop_for_dialog('candidate {!r}'.format(label)):
            return True
        call_kwargs = dict(kwargs)
        call_kwargs.update(extra)
        # Build our own AOP so the game reports WHY it refuses, instead of
        # push_super_affordance silently returning false.
        try:
            from interactions.aop import AffordanceObjectPair
            aop = AffordanceObjectPair(choice.affordance, target,
                                       choice.affordance, None, **call_kwargs)
        except Exception as ex:
            logfile.write('{}: could not build aop target={} ({!r})'.format(
                choice.label, label, ex))
            aop = None

        if aop is not None:
            logfile.write('{}: trying aop.test target={}'.format(
                choice.label, label))
            try:
                result = aop.test(context)
            except Exception as ex:
                logfile.fail('{}: test target={} raised {!r}'.format(
                    choice.label, label, ex))
                result = None
            if result:
                logfile.write('{}: trying aop.execute target={}'.format(
                    choice.label, label))
                try:
                    if aop.execute(context):
                        logfile.ok('{} via aop target={}'.format(
                            choice.label, label))
                        return True
                    logfile.write('{}: aop.execute target={} false'.format(
                        choice.label, label))
                except Exception as ex:
                    logfile.fail('{}: aop.execute target={} raised {!r}'.format(
                        choice.label, label, ex))
            elif result is not None:
                reason = getattr(result, 'reason', None) or result
                logfile.write('{}: refused target={} because {}'.format(
                    choice.label, label, str(reason)[:140]))

        logfile.write('{}: trying push target={}'.format(choice.label, label))
        try:
            if sim.push_super_affordance(choice.affordance, target, context,
                                         **call_kwargs):
                logfile.ok('{} via push target={}'.format(choice.label, label))
                return True
        except TypeError as ex:
            logfile.fail('{}: push target={} missing params {!r}'.format(
                choice.label, label, ex))
        except Exception as ex:
            logfile.fail('{}: push target={} raised {!r}'.format(
                choice.label, label, ex))
    return False
