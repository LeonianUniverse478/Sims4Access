"""What the game will actually let us touch, and when.

Written for one question: how much of the simulation exists before a lot is
loaded? The mod is imported at game boot and its keyboard runs on the main
menu, but that proves only that Python is alive - not that services, tuning
managers or the CAS natives are usable there. Guessing either way has cost us
rounds before, so this asks the running game and writes the answer to the log.

Everything here is READ-ONLY. It creates nothing, loads nothing and changes no
game state; it is safe to run on the main menu, in CAS, or on a lot.
"""
import a11yscan_log as logfile

# Resource types worth knowing about for Create-a-Sim work. CAS_MENU and
# CAS_MENU_ITEM are exported to the client binary and appear to have no server
# manager, which is exactly the sort of thing to confirm rather than assume.
TUNING_TYPES = (
    'TRAIT', 'ASPIRATION_TRACK', 'CAS_STORIES_QUESTION', 'CAS_STORIES_ANSWER',
    'CAS_STORIES_TRAIT_CHOOSER', 'CAS_PREFERENCE_ITEM', 'CAS_PREFERENCE_CATEGORY',
    'CASPART', 'CAS_MENU', 'CAS_MENU_ITEM', 'OBJECT', 'REGION', 'ZONE_MODIFIER',
)

CAS_NATIVES = (
    'get_catalog_casparts_by_bodytype', 'set_caspart', 'remove_caspart',
    'randomize_caspart', 'randomize_caspart_list', 'get_caspart_bodytype',
    'get_caspart_gender_compatible', 'caspart_has_tag', 'change_bodytype_level',
    'randomize_skintone_from_tags', 'randomize_part_color',
    'generate_random_siminfo', 'generate_household', 'apply_siminfo_override',
)

# Command name fragments that might bear on starting a game without the mouse.
COMMAND_HINTS = ('cas', 'household', 'zone', 'travel', 'save', 'load', 'world',
                 'lot', 'sim')


def _try(label, call):
    try:
        return '{}: {!r}'.format(label, call())
    except Exception as ex:
        return '{}: FAILED {!r}'.format(label, ex)


def _zone_lines():
    lines = ['== zone ==']
    lines.append(_try('current_zone', lambda: __import__('services').current_zone()))
    lines.append(_try('current_zone_id',
                      lambda: __import__('services').current_zone_id()))

    def running():
        import services
        zone = services.current_zone()
        return None if zone is None else zone.is_zone_running

    lines.append(_try('is_zone_running', running))
    lines.append(_try('client_manager',
                      lambda: __import__('services').client_manager()))
    lines.append(_try('first_client',
                      lambda: __import__('services').client_manager().get_first_client()))
    lines.append(_try('active_household',
                      lambda: __import__('services').active_household()))
    lines.append(_try('household_manager',
                      lambda: __import__('services').household_manager()))
    lines.append(_try('sim_info_manager',
                      lambda: __import__('services').sim_info_manager()))
    lines.append(_try('persistence_service',
                      lambda: __import__('services').get_persistence_service()))
    return lines


def _tuning_lines():
    """Tuning is loaded at boot, so these may well work with no lot at all.

    If they do, every list Create-a-Sim needs - traits, aspirations, the CAS
    Stories questionnaire - can be built on the main menu.
    """
    lines = ['== tuning managers ==']
    for name in TUNING_TYPES:
        def count(name=name):
            import services
            import sims4.resources
            type_id = getattr(sims4.resources.Types, name, None)
            if type_id is None:
                return 'no such Types.{}'.format(name)
            manager = services.get_instance_manager(type_id)
            if manager is None:
                return 'no manager'
            return '{} instances'.format(len(manager.types))
        lines.append(_try(name, count))
    return lines


def _cas_lines():
    """The CAS natives, which turn out to cover appearance after all."""
    lines = ['== cas natives ==']
    try:
        import cas.cas as cas_native
    except Exception as ex:
        lines.append('import cas.cas FAILED {!r}'.format(ex))
        return lines
    for name in CAS_NATIVES:
        found = getattr(cas_native, name, None)
        lines.append('{}: {}'.format(
            name, 'present' if found is not None else 'MISSING'))
    # BodyType is referenced all over cas.cas but its home is not obvious from
    # the bytecode, so look for it rather than assume an import path.
    # cas_tuning imports BodyType from sims.outfits.outfit_enums.
    for path, attr in (('sims.outfits.outfit_enums', 'BodyType'),
                       ('cas.cas_enums', 'BodyType'),
                       ('cas.cas_enums', 'SimRegion')):
        try:
            module = __import__(path, fromlist=[attr])
            value = getattr(module, attr, None)
            if value is not None:
                members = [n for n in dir(value) if n.isupper()]
                lines.append('BodyType found in {} ({} members: {})'.format(
                    path, len(members), ', '.join(members[:18])))
                break
        except Exception:
            continue
    else:
        lines.append('BodyType: not found on any tried path')
    return lines


def _cas_stories_lines():
    """The questionnaire, read straight from tuning."""
    lines = ['== cas stories ==']
    try:
        import services
        import sims4.resources
        manager = services.get_instance_manager(
            sims4.resources.Types.CAS_STORIES_QUESTION)
        questions = list(manager.types.values())
        lines.append('{} questions'.format(len(questions)))
        import a11yscan_dialogs as dialogs
        for question in questions[:3]:
            text = None
            for attr in ('question_text', 'text', 'display_text'):
                try:
                    text = dialogs.loc_text(getattr(question, attr, None))
                except Exception:
                    text = None
                if text:
                    break
            answers = getattr(question, 'possible_answers', None)
            lines.append('  Q {!r} -> {} answers, fields: {}'.format(
                text, len(list(answers or ())),
                ', '.join(n for n in dir(question) if not n.startswith('_'))[:200]))
    except Exception as ex:
        lines.append('FAILED {!r}'.format(ex))
    return lines


def _command_lines():
    """Which console commands exist here.

    If something can start a new game or load a lot, it is registered as a
    command, and commands are callable from Python as well as the console.
    """
    lines = ['== commands ==']
    try:
        import sims4.commands
        names = []
        try:
            for info in sims4.commands.get_command_info_gen():
                name = getattr(info, 'name', None) or str(info)
                names.append(name)
        except Exception as ex:
            lines.append('get_command_info_gen failed ({!r})'.format(ex))
            registry = getattr(sims4.commands, '_commands', None)
            try:
                names = [str(n) for n in registry.keys()]
            except Exception:
                names = []
        names = sorted(set(names))
        lines.append('{} commands registered'.format(len(names)))
        for hint in COMMAND_HINTS:
            matches = [n for n in names if hint in n.lower()]
            if matches:
                lines.append('  {!r}: {}'.format(hint, ', '.join(matches[:24])))
    except Exception as ex:
        lines.append('FAILED {!r}'.format(ex))
    return lines


def _services_sweep():
    """Every service getter the game has, and which ones answer here.

    Guessing which services exist in an unknown state has been the slow way to
    do this. Clicking New Game puts the game somewhere neither the main menu
    nor a loaded lot, so sweep the lot: call every zero-argument getter on the
    services module and record what comes back. Restricted to get_* / *_service
    / *_manager names, which are accessors, so nothing here starts anything.
    """
    lines = ['== services sweep ==']
    try:
        import services
    except Exception as ex:
        lines.append('import services FAILED {!r}'.format(ex))
        return lines
    alive = []
    empty = []
    for name in sorted(dir(services)):
        if name.startswith('_'):
            continue
        if not (name.startswith('get_') or name.endswith('_service')
                or name.endswith('_manager')):
            continue
        call = getattr(services, name, None)
        if not callable(call):
            continue
        try:
            value = call()
        except TypeError:
            continue          # needs arguments; not a plain accessor
        except Exception:
            continue
        if value is None:
            empty.append(name)
        else:
            alive.append('{}={}'.format(name, type(value).__name__))
    lines.append('ALIVE ({}): {}'.format(len(alive), ', '.join(alive)))
    lines.append('None  ({}): {}'.format(len(empty), ', '.join(empty)))
    return lines


def _population_lines():
    """Is there a Sim being edited right now?"""
    lines = ['== population ==']

    def sims():
        import services
        manager = services.sim_info_manager()
        return 'none' if manager is None else '{} sim_infos'.format(len(list(manager.values())))

    def households():
        import services
        manager = services.household_manager()
        return 'none' if manager is None else '{} households'.format(len(list(manager.values())))

    def active():
        import services
        client = services.client_manager().get_first_client()
        return getattr(client, 'active_sim_info', None)

    lines.append(_try('sim_infos', sims))
    lines.append(_try('households', households))
    lines.append(_try('client active_sim_info', active))
    return lines


def _open_dialog_lines():
    """What pop-ups the game has open right now, from three angles.

    Pressed while a screen is up, this separates "the mod cannot see the
    dialog" from "there is no server-side dialog to see" - which is the
    difference between a bug and a client-only panel like CAS.
    """
    lines = ['== dialogs open right now ==']
    try:
        import services
        service = services.ui_dialog_service()
        lines.append('ui_dialog_service: {!r}'.format(service))
        active = getattr(service, '_active_dialogs', None)
        lines.append('_active_dialogs: {!r}'.format(
            list(active.keys()) if hasattr(active, 'keys') else active))
        if hasattr(active, 'values'):
            for dialog in list(active.values()):
                lines.append('  {}: {!r}'.format(
                    type(dialog).__name__,
                    getattr(dialog, 'dialog_id', None)))
    except Exception as ex:
        lines.append('service lookup FAILED {!r}'.format(ex))
    try:
        import a11yscan_dialogs as dialogs
        lines.append('mod sees: {!r}'.format(dialogs.current()))
        lines.append('mod hooked: {} classes'.format(len(dialogs.hooked())))
    except Exception as ex:
        lines.append('mod view FAILED {!r}'.format(ex))
    # What the Sim is doing explains a picker that has not opened yet.
    try:
        import a11yscan_world as world
        sim = world.active_sim()
        queue = getattr(sim, 'queue', None)
        lines.append('running: {!r}'.format(getattr(queue, 'running', None)))
        lines.append('queued: {!r}'.format(
            [getattr(i, 'affordance', i) for i in queue][:6] if queue else None))
    except Exception as ex:
        lines.append('queue FAILED {!r}'.format(ex))
    return lines


def gather():
    lines = ['probe: what is reachable right now']
    for section in (_open_dialog_lines, _zone_lines, _services_sweep,
                    _population_lines, _tuning_lines, _cas_lines,
                    _cas_stories_lines, _command_lines):
        try:
            lines.extend(section())
        except Exception as ex:
            lines.append('section {} raised {!r}'.format(section.__name__, ex))
    return lines


def run():
    """Write the whole picture to the log and say how it went out loud."""
    lines = gather()
    logfile.write('=' * 60)
    for line in lines:
        logfile.write(line, 'probe')
    logfile.write('=' * 60)
    zone = 'no lot'
    for line in lines:
        if line.startswith('is_zone_running') and 'True' in line:
            zone = 'on a lot'
    return 'Probe written to the log, {} lines, {}.'.format(len(lines), zone)
