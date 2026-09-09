"""Cheat commands, diagnostics and startup wiring.

Every scanner action is reachable from the console as well as the keyboard, so
the mod stays testable even if keyboard polling or ctypes is unavailable.
"""
import sims4.commands

import a11yscan_actions as actions
import a11yscan_audio as audio
import a11yscan_careers as careers
import a11yscan_cas as cas
import a11yscan_dialogs as dialogs
import a11yscan_keys as keys
import a11yscan_log as logfile
import a11yscan_lots as lots
import a11yscan_names as names
import a11yscan_objects as objectnames
import a11yscan_narrate as narrate
import a11yscan_probe as probe
import a11yscan_pump as pump
import a11yscan_reload as reloader
import a11yscan_speech as speech
import a11yscan_state as state
import a11yscan_world as world

VERSION = '0.1'


def _out(connection):
    return sims4.commands.CheatOutput(connection)


def _report_path():
    """Write reports next to the game's own logs, where they can be read
    without having to copy anything out of the cheat console."""
    import os
    mods = speech._mods_dir()
    if not mods:
        return None
    # Prefer the Sims 4 folder; fall back to Mods if that is not writable.
    for folder in (os.path.dirname(mods), mods):
        try:
            path = os.path.join(folder, 'a11yscan_report.txt')
            with open(path, 'a'):
                pass
            return path
        except Exception:
            continue
    return None


def _safe(label, func):
    """Never let one broken probe abort the whole report."""
    try:
        value = func()
        return '{}: {}'.format(label, value)
    except Exception as ex:
        return '{}: FAILED {!r}'.format(label, ex)



def _situation_status():
    """What the lot is running, in the startup report.

    A pair of Sims who chat endlessly and never see to themselves are usually
    being driven by a situation - a date or a hangout scores social
    interactions, so they keep choosing each other over the bathroom. Having
    this in every report means not having to ask for it after the fact.
    """
    import a11yscan_cheats as cheats
    manager, running = cheats._situations()
    if manager is None:
        return 'unavailable'
    if not running:
        return 'nothing running'
    counts = {}
    for situation in running:
        name = type(situation).__name__
        counts[name] = counts.get(name, 0) + 1
    ordered = sorted(counts.items(), key=lambda pair: -pair[1])
    return '{} running: {}'.format(
        len(running), ', '.join('{} x{}'.format(n, c) for n, c in ordered[:8]))


def _mod_string_status():
    """What the runtime string reader has picked up, if anything."""
    import a11yscan_strings as strings
    return strings.status()

def _gather():
    lines = ['a11yscan report, version {}'.format(VERSION)]

    lines.append('')
    lines.append('== speech / independence ==')
    lines.append(_safe('backend', speech.backend))
    for entry in speech.probe():
        lines.append('  {}'.format(entry))
    try:
        ok, borrowed = speech.standalone()
        lines.append('standalone: {}'.format('YES' if ok else 'NO'))
        for item in borrowed:
            lines.append('  borrowed: {}'.format(item))
    except Exception as ex:
        lines.append('standalone check failed {!r}'.format(ex))

    lines.append('')
    lines.append('== environment ==')
    have, missing = [], []
    for name in ('os', 'math', 'time', 'threading', 'ctypes', 're', 'queue',
                 'collections', 'weakref', 'json', 'random', 'subprocess',
                 'struct', 'itertools', 'functools', 'zipfile'):
        try:
            __import__(name)
            have.append(name)
        except Exception:
            missing.append(name)
    lines.append('available: {}'.format(', '.join(have)))
    lines.append('missing:   {}'.format(', '.join(missing) or 'none'))
    lines.append(_safe('name table', names.status))
    lines.append(_safe('object name table', objectnames.status))
    lines.append(_safe('mod strings', _mod_string_status))
    lines.append(_safe('situations', _situation_status))
    lines.append(_safe('keyboard', keys.status))
    lines.append(_safe('pump', pump.status))
    lines.append(_safe('narration', narrate.status))

    lines.append('')
    lines.append('== dialogs ==')
    lines.append('hooks: {}'.format(', '.join(dialogs.hooked()) or 'NONE'))
    try:
        live = dialogs.service_dialogs()
        lines.append('service reports {} live: {}'.format(
            len(live), [type(d).__name__ for d in live[:6]]))
    except Exception as ex:
        lines.append('service query failed {!r}'.format(ex))
    lines.append('captured snapshots: {}'.format(dialogs.snapshot_count()))
    lines.append('last captured dialog:')
    for entry in dialogs.last_snapshot():
        lines.append('  {}'.format(entry))
    lines.append('last route: {!r}'.format(dialogs.last_route()))
    lines.append('last error: {!r}'.format(dialogs.last_error()))

    sim = world.active_sim()
    lines.append('')
    lines.append('== sim ==')
    if sim is None:
        lines.append('NO ACTIVE SIM')
        return lines
    lines.append('active: {}'.format(world.sim_name(sim)))
    lines.append(_safe('current action', lambda: world.current_action(sim)))
    lines.append(_safe('emotion', lambda: world.emotion(sim)))
    for entry in world.emotion_debug()[:6]:
        lines.append('  emotion debug: {}'.format(entry))
    lines.append(_safe('wants', lambda: world.wants(sim)))
    for entry in world.wants_debug()[:10]:
        lines.append('  want debug: {}'.format(entry))

    lines.append('')
    lines.append('== self interactions ==')
    try:
        own = actions.choices_for(sim)
        lines.append('{} offered on the Sim itself:'.format(len(own)))
        for choice in own:
            lines.append('  {}'.format(choice.label))
    except Exception as ex:
        lines.append('self interactions failed {!r}'.format(ex))

    lines.append('')
    lines.append('== relationships ==')
    try:
        contacts = world.contact_entries(sim)
        lines.append('contacts: {}'.format(len(contacts)))
        for entry in world.contacts_debug()[:8]:
            lines.append('  {}'.format(entry))
        if contacts:
            target = contacts[0]
            lines.append('probing: {}'.format(target.name))
            lines.append('relation method present: {}'.format(
                hasattr(sim, 'potential_relation_panel_interactions')))
            choices = actions.relation_panel_choices(target.obj)
            lines.append('relation panel resolved: {} ({})'.format(
                len(choices), actions.last_source()))
            for choice in choices[:12]:
                lines.append('  + {}'.format(choice.label))
            for entry in actions.relation_debug():
                lines.append('  {}'.format(entry))
            for label, reason in actions.last_rejects()[:10]:
                lines.append('  - {}: {}'.format(label, str(reason)[:90]))
    except Exception as ex:
        lines.append('relationship probe failed {!r}'.format(ex))

    lines.append('')
    lines.append('== scan ==')
    try:
        world.reset_name_stats()
        buckets = world.scan()
        for category in world.ordered_categories(buckets):
            lines.append('  {}: {}'.format(category, len(buckets[category])))
        lines.append('name stats: {}'.format(world.name_stats()))
    except Exception as ex:
        lines.append('scan failed {!r}'.format(ex))
    return lines


@sims4.commands.Command('a11y2.reload', command_type=sims4.commands.CommandType.Live)
def a11y2_reload(_connection=None):
    """Reload the mod in place, without restarting the game."""
    output = _out(_connection)
    result = reloader.reload_all()
    output(result)
    return True


@sims4.commands.Command('a11y2.report', command_type=sims4.commands.CommandType.Live)
def a11y2_report(_connection=None):
    """Write every diagnostic to a file, since the console cannot be copied."""
    output = _out(_connection)
    lines = _gather()
    path = _report_path()
    if path is None:
        output('could not locate the Mods folder')
        speech.speak('Report failed, no folder found.')
        return True
    try:
        with open(path, 'w') as handle:
            handle.write(chr(10).join(lines))
        output('written: {}'.format(path))
        speech.speak('Report saved to the Sims 4 folder.')
    except Exception as ex:
        output('write failed {!r}'.format(ex))
        speech.speak('Report could not be written.')
    return True


@sims4.commands.Command('a11y2.diag', command_type=sims4.commands.CommandType.Live)
def a11y2_diag(_connection=None):
    output = _out(_connection)
    output('Sims 4 Access {} diagnostics'.format(VERSION))
    output('  speech backend: {}'.format(speech.backend()))
    for line in speech.probe():
        output('    {}'.format(line))
    output('  name table: {}'.format(names.status()))
    output('  dialog hooks: {}'.format(', '.join(dialogs.hooked()) or 'NONE'))
    output('  notification sounds: {}'.format(audio.status()))
    for line in audio.recent(6):
        output('    {}'.format(line))
    output('  keyboard: {}'.format(keys.status()))
    output('  action narration: {}'.format(narrate.status()))
    output('  intent pump: {}'.format(pump.status()))

    sim = world.active_sim()
    output('  active Sim: {}'.format(world.sim_name(sim) if sim else 'NONE'))
    if sim is None:
        output('  (load into a lot first, then run this again)')
        return True

    buckets = world.scan()
    total = sum(len(v) for v in buckets.values())
    output('  scanned: {} things in {} categories'.format(
        total, len(world.ordered_categories(buckets))))
    for category in world.ordered_categories(buckets):
        output('    {}: {}'.format(category, len(buckets[category])))

    for category in world.ordered_categories(buckets):
        entries = buckets[category]
        if not entries:
            continue
        probe = entries[0]
        choices = actions.choices_for(probe.obj, sim)
        output('  sample: {} -> {} interactions'.format(
            probe.describe(), len(choices)))
        for choice in choices[:6]:
            output('      {}'.format(choice.label))
        break
    return True


@sims4.commands.Command('a11y2.scan', command_type=sims4.commands.CommandType.Live)
def a11y2_scan(_connection=None):
    output = _out(_connection)
    if state.rescan(announce=True):
        for category in world.ordered_categories(state._buckets):
            output('{}: {}'.format(category, len(state._buckets[category])))
    else:
        output('nothing found')
    return True


@sims4.commands.Command('a11y2.list', command_type=sims4.commands.CommandType.Live)
def a11y2_list(category=None, _connection=None):
    output = _out(_connection)
    buckets = world.scan()
    if not buckets:
        output('nothing found')
        return True
    category_names = world.ordered_categories(buckets)
    chosen = category if category in buckets else category_names[0]
    output('{}:'.format(chosen))
    for index, entry in enumerate(buckets[chosen][:25], 1):
        output('  {}. {}'.format(index, entry.describe()))
    output('categories: {}'.format(', '.join(category_names)))
    return True


@sims4.commands.Command('a11y2.do', command_type=sims4.commands.CommandType.Live)
def a11y2_do(intent='where', _connection=None):
    """Fire one scanner intent by name, for testing without the keyboard."""
    output = _out(_connection)
    state.dispatch(intent)
    output('intent {} -> {}'.format(intent, speech.last()))
    return True


@sims4.commands.Command('a11y2.names', command_type=sims4.commands.CommandType.Live)
def a11y2_names(_connection=None):
    """Report how many objects on this lot resolved to real catalog names."""
    output = _out(_connection)
    output('name table: {}'.format(names.status()))
    world.reset_name_stats()
    buckets = world.scan()
    stats = world.name_stats()
    total = sum(stats.values())
    if not total:
        output('nothing scanned (load into a lot first)')
        return True
    output('resolved {} objects:'.format(total))
    output('  real catalog name: {} ({:.0f}%)'.format(
        stats['catalog'], 100.0 * stats['catalog'] / total))
    output('  build/buy tag:     {}'.format(stats['tag']))
    output('  tuning fallback:   {}'.format(stats['tuning']))
    shown = 0
    for category in world.ordered_categories(buckets):
        for entry in buckets[category][:3]:
            output('    {}: {}'.format(category, entry.name))
            shown += 1
            if shown >= 12:
                return True
    return True


@sims4.commands.Command('a11y2.standalone', command_type=sims4.commands.CommandType.Live)
def a11y2_standalone(_connection=None):
    """Can this mod run with every other accessibility mod uninstalled?"""
    output = _out(_connection)
    ok, borrowed = speech.standalone()
    output('STANDALONE: {}'.format('YES' if ok else 'NO'))
    output('  speech backend: {}'.format(speech.backend()))
    for line in speech.probe():
        output('    {}'.format(line))
    if borrowed:
        output('  still depending on another mod for:')
        for item in borrowed:
            output('    - {}'.format(item))
    try:
        import ctypes
        output('  ctypes from: {}'.format(getattr(ctypes, '__file__', 'unknown')))
    except Exception as ex:
        output('  ctypes UNAVAILABLE: {!r}'.format(ex))
    output('  keyboard: {}'.format(keys.status()))
    output('  name table: {}'.format(names.status()))
    return True


@sims4.commands.Command('a11y2.lastdialog', command_type=sims4.commands.CommandType.Live)
def a11y2_lastdialog(_connection=None):
    """Raw structure of the most recent pop-up, captured when it appeared."""
    output = _out(_connection)
    output('hooks: {}'.format(', '.join(dialogs.hooked()) or 'NONE'))
    output('captured so far: {}'.format(dialogs.snapshot_count()))
    live = dialogs.service_dialogs()
    output('dialog service reports {} live: {}'.format(
        len(live), [type(d).__name__ for d in live[:5]]))
    for line in dialogs.last_snapshot():
        output('  {}'.format(line))
    return True


@sims4.commands.Command('a11y2.rel', command_type=sims4.commands.CommandType.Live)
def a11y2_rel(_connection=None):
    """Why the relationship-panel menu is or is not resolving."""
    output = _out(_connection)
    sim = world.active_sim()
    if sim is None:
        output('no active Sim')
        return True
    method = getattr(sim, 'potential_relation_panel_interactions', None)
    output('method present: {}'.format(method is not None))
    entries = world.contact_entries(sim)
    output('contacts: {}'.format(len(entries)))
    if not entries:
        return True
    target = entries[0]
    output('probing: {}'.format(target.name))
    choices = actions.relation_panel_choices(target.obj)
    output('resolved {} ({})'.format(len(choices), actions.last_source()))
    for choice in choices[:12]:
        output('  + {}'.format(choice.label))
    for line in actions.relation_debug():
        output('  {}'.format(line))
    for label, reason in actions.last_rejects()[:6]:
        output('  - {}: {}'.format(label, reason[:60]))
    return True


@sims4.commands.Command('a11y2.probe', command_type=sims4.commands.CommandType.Live)
def a11y2_probe(_connection=None):
    """Dump the real shapes we have been guessing at: command signatures,
    whim structure, and the live dialog."""
    output = _out(_connection)
    output('--- ui command signatures ---')
    for line in dialogs.signature_report():
        output('  {}'.format(line))
    output('--- wants ---')
    sim = world.active_sim()
    if sim is None:
        output('  no active Sim')
    else:
        output('  resolved: {!r}'.format(world.wants(sim)))
        for line in world.wants_debug()[:14]:
            output('  {}'.format(line))
    output('--- relationships ---')
    if sim is not None:
        entries = world.contact_entries(sim)
        output('  {} contacts'.format(len(entries)))
        for entry in entries[:5]:
            output('    {}'.format(entry.describe()))
        for line in world.contacts_debug()[:8]:
            output('    debug: {}'.format(line))
        if entries:
            first = entries[0]
            output('  menu sources for {}:'.format(first.name))
            output('    relation panel: {}'.format(
                len(actions.relation_panel_choices(first.obj))))
            output('    phone: {}'.format(len(actions.phone_choices())))
    output('--- live dialog ---')
    dialog = dialogs.current()
    if dialog is None:
        output('  none open')
    else:
        for line in dialogs.inspect(dialog):
            output('  {}'.format(line))
        output('  body: {!r}'.format(dialogs.body_of(dialog)))
        output('  service says open: {!r}'.format(
            dialogs.is_open(getattr(dialog, 'dialog_id', None))))
    output('  last route: {!r}'.format(dialogs.last_route()))
    output('  last error: {!r}'.format(dialogs.last_error()))
    return True


@sims4.commands.Command('a11y2.wants', command_type=sims4.commands.CommandType.Live)
def a11y2_wants(_connection=None):
    """Read the active Sim's current wants."""
    output = _out(_connection)
    sim = world.active_sim()
    if sim is None:
        output('no active Sim')
        return True
    items = world.wants(sim)
    output('{}: {} wants'.format(world.sim_name(sim), len(items)))
    for item in items:
        output('  - {}'.format(item))
    if not items:
        output('  (none found - run a11y2.probe for the raw structure)')
    for line in world.wants_debug()[:10]:
        output('  debug: {}'.format(line))
    return True


@sims4.commands.Command('a11y2.narrate', command_type=sims4.commands.CommandType.Live)
def a11y2_narrate(mode=None, _connection=None):
    """Turn running-action announcements on or off."""
    output = _out(_connection)
    if mode is not None:
        narrate.set_enabled(str(mode).lower() in ('on', 'true', '1', 'yes'))
    output('action narration: {}'.format(narrate.status()))
    output('last announced: {!r}'.format(narrate.last_label()))
    return True


@sims4.commands.Command('a11y2.env', command_type=sims4.commands.CommandType.Live)
def a11y2_env(_connection=None):
    """Probe which stdlib modules this game build actually provides."""
    output = _out(_connection)
    wanted = ('os', 'sys', 'math', 'time', 'threading', 'ctypes', 're', 'queue',
              'collections', 'weakref', 'json', 'random', 'subprocess', 'struct',
              'itertools', 'functools', 'zipfile', 'io', 'codecs')
    have = []
    missing = []
    for name in wanted:
        try:
            __import__(name)
            have.append(name)
        except Exception:
            missing.append(name)
    output('available: {}'.format(', '.join(have)))
    output('MISSING:   {}'.format(', '.join(missing) or 'none'))
    return True


@sims4.commands.Command('a11y2.dialog', command_type=sims4.commands.CommandType.Live)
def a11y2_dialog(_connection=None):
    """Dump the live pop-up so we can learn its real structure."""
    output = _out(_connection)
    output('hook: {}'.format('installed' if dialogs.installed() else 'NOT installed'))
    dialog = dialogs.current()
    if dialog is None:
        output('no active dialog - open a recipe picker or wait for a call, then rerun')
        return True
    for line in dialogs.inspect(dialog):
        output('  {}'.format(line))
    output('  options:')
    for index, (label, kind, _payload) in enumerate(dialogs.options(dialog)[:20], 1):
        output('    {}. [{}] {}'.format(index, kind, label))
    if dialogs.last_route():
        output('  last successful route: {}'.format(dialogs.last_route()))
    if dialogs.last_error():
        output('  last error: {}'.format(dialogs.last_error()))
    return True


@sims4.commands.Command('a11y2.why', command_type=sims4.commands.CommandType.Live)
def a11y2_why(_connection=None):
    """Show what the focused object offers, and what was filtered out and why."""
    output = _out(_connection)
    entry = state.current_entry()
    if entry is None:
        output('nothing focused - use a11y2.do focus_self or browse first')
        return True
    choices = actions.choices_for(entry.obj)
    output('{} ({})'.format(entry.name, entry.category))
    output('  source: {}'.format(actions.last_source()))
    output('  offered: {}'.format(len(choices)))
    for choice in choices[:20]:
        output('    + {}'.format(choice.label))
    rejects = actions.last_rejects()
    output('  filtered out: {}'.format(len(rejects)))
    for label, reason in rejects[:20]:
        output('    - {}: {}'.format(label, reason[:70]))
    return True


@sims4.commands.Command('a11y2.say', command_type=sims4.commands.CommandType.Live)
def a11y2_say(*text, _connection=None):
    """Speak a phrase, to test the speech path on its own."""
    output = _out(_connection)
    phrase = ' '.join(str(t) for t in text) or 'Scanner speech test.'
    speech.speak(phrase)
    output('backend {} <- {!r}'.format(speech.backend(), phrase))
    for line in speech.probe():
        output('  {}'.format(line))
    return True


@sims4.commands.Command('a11y2.keys', command_type=sims4.commands.CommandType.Live)
def a11y2_keys(mode=None, _connection=None):
    output = _out(_connection)
    if mode is not None:
        wanted = str(mode).lower() in ('on', 'true', '1', 'yes')
        keys.set_enabled(wanted)
        if wanted and keys.status() == 'stopped':
            keys.start()
    output('keyboard: {}'.format(keys.status()))
    for line in keys.describe_bindings():
        output(line)
    return True


@sims4.commands.Command('a11y2.start', command_type=sims4.commands.CommandType.Live)
def a11y2_start(_connection=None):
    output = _out(_connection)
    pump.start()
    keys.start()
    dialogs.install(state.on_dialog_shown)
    output('pump: {}'.format(pump.status()))
    output('dialog hook: {}'.format('installed' if dialogs.installed() else 'failed'))
    output('keyboard: {}'.format(keys.status()))
    return True


def _install_build_mode_hook():
    """Leaving build mode must drop the catalog and grid, or the arrows stay
    captured in live mode and only a reload frees them."""
    try:
        import build_buy

        def a11yscan_on_build_buy_exit(*args, **kwargs):
            try:
                state.leave_build_modes(announce=True)
            except Exception as ex:
                logfile.write('build exit hook failed ({!r})'.format(ex))

        build_buy.register_build_buy_exit_callback(a11yscan_on_build_buy_exit)
        import a11yscan_build as build
        build.announce_enter()
        logfile.write('build/buy exit hook installed')
        return True
    except Exception as ex:
        logfile.write('build/buy exit hook failed ({!r})'.format(ex))
        return False


def start_everything():
    """Single entry point used by both zone load and reload."""
    pump.start()
    keys.start()
    dialogs.install(state.on_dialog_shown)
    audio.install()
    _install_build_mode_hook()
    _log_startup()


def _log_startup():
    """Write the full diagnostic to the log on every load, so nothing depends
    on the player remembering to run a command."""
    try:
        logfile.session('Sims 4 Access {} loaded, log at {}'.format(
            VERSION, logfile.path()))
        for line in _gather():
            logfile.write(line, 'startup')
    except Exception as ex:
        try:
            logfile.fail('startup diagnostic failed {!r}'.format(ex))
        except Exception:
            pass


def _install_zone_hook():
    """Start the sim-thread pump once a lot has finished loading."""
    try:
        import zone
        original = zone.Zone.on_loading_screen_animation_finished

        def a11yscan_on_loading_screen_animation_finished(self, *args, **kwargs):
            result = original(self, *args, **kwargs)
            try:
                start_everything()
                speech.speak('Sims 4 Access ready, {} speech.'.format(speech.backend()))
            except Exception as ex:
                speech.log('startup after zone load failed ({!r})'.format(ex))
            return result

        zone.Zone.on_loading_screen_animation_finished = \
            a11yscan_on_loading_screen_animation_finished
        return True
    except Exception as ex:
        speech.log('zone hook failed ({!r}); use a11y2.start'.format(ex))
        return False


def start_early():
    """Bring the keyboard up at game boot, before any lot is loaded.

    start_everything only runs when a lot finishes loading, which meant every
    key was dead on the main menu and on the world and household screens - the
    exact place you are standing when you need to create a Sim. Polling
    GetAsyncKeyState needs no zone, so the keyboard can start now; the pump
    runs intents inline until a lot loads and the alarm takes over.
    """
    try:
        pump.begin_without_zone()
        keys.start()
        reloader.note_load()
        logfile.session('Sims 4 Access {} loaded at boot, keyboard {}'.format(
            VERSION, keys.status()))
        # Without this there is no way to tell from the main menu whether the
        # mod is running at all, which reads as "it does not start here".
        try:
            # "No lot loaded yet" told a new player nothing about what to do
            # about it, and the screens they are looking at cannot be read.
            import a11yscan_start as start
            speech.speak('Sims 4 Access ready. {}'.format(start.next_step()))
        except Exception:
            try:
                speech.speak('Sims 4 Access ready. No lot loaded yet. Press '
                             'Control Alt W to hear what to do next.')
            except Exception:
                pass
    except Exception as ex:
        speech.log('early start failed ({!r})'.format(ex))


_install_zone_hook()
start_early()
speech.log('Sims 4 Access {} loaded'.format(VERSION))


@sims4.commands.Command('a11y2.cas', command_type=sims4.commands.CommandType.Live)
def a11y2_cas(_connection=None):
    """Open the keyboard Sim builder, for when Ctrl+Alt+M is unavailable."""
    output = _out(_connection)
    state.cas_open()
    output(cas.describe() if cas.active() else 'Create a Sim closed.')


@sims4.commands.Command('a11y2.cas.first', command_type=sims4.commands.CommandType.Live)
def a11y2_cas_first(*name, _connection=None):
    """Set an exact first name. The rolled pool can only offer names the game
    ships with, and people want their own."""
    output = _out(_connection)
    output(cas.set_first(' '.join(name)))


@sims4.commands.Command('a11y2.cas.last', command_type=sims4.commands.CommandType.Live)
def a11y2_cas_last(*name, _connection=None):
    output = _out(_connection)
    output(cas.set_last(' '.join(name)))


@sims4.commands.Command('a11y2.cas.make', command_type=sims4.commands.CommandType.Live)
def a11y2_cas_make(_connection=None):
    """Create the Sim described by the current choices."""
    output = _out(_connection)
    output(cas.create())


@sims4.commands.Command('a11y2.rename', command_type=sims4.commands.CommandType.Live)
def a11y2_rename(first='', last='', _connection=None):
    """Rename the selected Sim. Two words: first name then last name."""
    output = _out(_connection)
    if not first:
        output('Usage: a11y2.rename Miranda Newman')
        return
    output(cas.rename_active(first, last))


@sims4.commands.Command('a11y2.who', command_type=sims4.commands.CommandType.Live)
def a11y2_who(_connection=None):
    """List the household, numbered, marking who is selected and who is dead."""
    output = _out(_connection)
    sims = cas.household_sims()
    if not sims:
        output('No household Sims found.')
        return
    for index, (sim_info, is_active) in enumerate(sims, 1):
        line = '{}: {}'.format(index, cas.describe_sim(sim_info, is_active))
        output(line)
        # Console output never reaches the log, which is the whole reason
        # diagnosis moved to the log in the first place.
        logfile.write('who: {} (id={})'.format(line, getattr(sim_info, 'id', '?')))


@sims4.commands.Command('a11y2.rename.n', command_type=sims4.commands.CommandType.Live)
def a11y2_rename_n(index=0, first='', last='', _connection=None):
    """Rename by number from a11y2.who, for Sims that are not selected."""
    output = _out(_connection)
    if not index or not first:
        output('Usage: a11y2.rename.n 2 Miranda Newman')
        return
    output(cas.rename_at(index, first, last))


@sims4.commands.Command('a11y2.play', command_type=sims4.commands.CommandType.Live)
def a11y2_play(index=0, _connection=None):
    """Switch which household Sim you are playing, numbered as in a11y2.who."""
    output = _out(_connection)
    if not index:
        output('Usage: a11y2.play 2   (see a11y2.who for the numbers)')
        return
    output(cas.switch_to(index))


@sims4.commands.Command('a11y2.voice', command_type=sims4.commands.CommandType.Live)
def a11y2_voice(index=0, _connection=None):
    """Change the selected Sim's voice. Without a number, list what is on offer."""
    output = _out(_connection)
    if not index:
        cas.set_voice_active(0)
        choices = cas.voice_choices()
        if len(choices) < 2:
            output('No voices found for that Sim in this world.')
            return
        output('Voices for the selected Sim:')
        for position, (label, actor) in enumerate(choices):
            if position:
                output('  {}: {} ({})'.format(position, label, actor))
        return
    output(cas.set_voice_active(index))


@sims4.commands.Command('a11y2.probe2', command_type=sims4.commands.CommandType.Live)
def a11y2_probe2(_connection=None):
    """Write the reachability probe to the log. Read-only."""
    output = _out(_connection)
    output(probe.run())


@sims4.commands.Command('a11y2.endevent', command_type=sims4.commands.CommandType.Live)
def a11y2_endevent(_connection=None):
    """End the event that is running."""
    output = _out(_connection)
    import a11yscan_events as events
    output(events.end_event())
    return True


@sims4.commands.Command('a11y2.eventwatch', command_type=sims4.commands.CommandType.Live)
def a11y2_eventwatch(state=None, _connection=None):
    """Read event progress automatically: a11y2.eventwatch off, or on."""
    output = _out(_connection)
    import a11yscan_events as events
    if state is None:
        output('event progress is read automatically: {}'.format(
            'on' if events.watch_enabled() else 'off'))
        return True
    wanted = str(state).lower() not in ('off', 'false', '0', 'no')
    output(events.set_watch(wanted))
    return True


@sims4.commands.Command('a11y2.claimlot', command_type=sims4.commands.CommandType.Live)
def a11y2_claimlot(_connection=None):
    """Make the lot you are on belong to your household."""
    output = _out(_connection)
    import a11yscan_lots as lots
    _ok, message = lots.claim_lot()
    output(message)
    return True


@sims4.commands.Command('a11y2.pressf2', command_type=sims4.commands.CommandType.Live)
def a11y2_pressf2(_connection=None):
    """Have Windows press F2, for when the real key never reaches the game."""
    output = _out(_connection)
    import a11yscan_build as build
    before = build.build_state()
    ok = keys.press_f2()
    output('sent: {}, build mode was {!r} before'.format(ok, before))
    output(build.watch_build(15.0))
    return True


@sims4.commands.Command('a11y2.watchbuild', command_type=sims4.commands.CommandType.Live)
def a11y2_watchbuild(_connection=None):
    """Watch the game's build-mode flag while you press F2."""
    output = _out(_connection)
    import a11yscan_build as build
    output('the game currently says in build mode: {!r}'.format(
        build.build_state()))
    output(build.watch_build())
    return True


@sims4.commands.Command('a11y2.unlockbuild', command_type=sims4.commands.CommandType.Live)
def a11y2_unlockbuild(_connection=None):
    """Clear a build/buy lock a situation left behind."""
    output = _out(_connection)
    import a11yscan_build as build
    output(build.unlock_build())
    return True


@sims4.commands.Command('a11y2.whybuild', command_type=sims4.commands.CommandType.Live)
def a11y2_whybuild(_connection=None):
    """Why build mode will not open on this lot."""
    output = _out(_connection)
    import a11yscan_build as build
    output(build.why_no_build())
    return True


@sims4.commands.Command('a11y2.relationships', command_type=sims4.commands.CommandType.Live)
def a11y2_relationships(_connection=None):
    """Every relationship profile, as the panel would show them."""
    output = _out(_connection)
    import a11yscan_relations as relations
    for line in relations.report():
        output(line)
    return True


@sims4.commands.Command('a11y2.gallery', command_type=sims4.commands.CommandType.Live)
def a11y2_gallery(zone_id=None, _connection=None):
    """Ask the client to open the Gallery for this lot, or a given zone id."""
    output = _out(_connection)
    import a11yscan_gallery as gallery
    output(gallery.move_in_from_gallery(zone_id))
    return True


@sims4.commands.Command('a11y2.venue', command_type=sims4.commands.CommandType.Live)
def a11y2_venue(name=None, _connection=None):
    """Report what this lot is, or change it: a11y2.venue bar"""
    output = _out(_connection)
    import a11yscan_venues as venues
    if not name:
        for line in venues.report():
            output(line)
        return True
    needle = str(name).lower()
    matches = [pair for pair in venues.choices()
               if needle in pair[0].lower()]
    if not matches:
        output('nothing matching {!r}. Run a11y2.venue with no argument for '
               'the list.'.format(name))
        return False
    if len(matches) > 1:
        exact = [pair for pair in matches if pair[0].lower() == needle]
        if not exact:
            output('{} types match {!r}: {}'.format(
                len(matches), name, ', '.join(p[0] for p in matches)))
            return False
        matches = exact
    output(venues.set_to(matches[0][0], matches[0][1]))
    return True


@sims4.commands.Command('a11y2.places', command_type=sims4.commands.CommandType.Live)
def a11y2_places(search=None, _connection=None):
    """Every travel destination, or the ones whose name matches a word.

    Use it to check what a newly installed mod added: run it before and after,
    or search for the place the mod claims to unlock.
    """
    output = _out(_connection)
    import a11yscan_travel as travel
    count = travel.load()
    places = travel.places()
    output('{} destinations'.format(count))
    learned = [p for p in places if p.get('world') == 'learned from the map']
    if learned:
        output('{} of them learned from a map screen rather than the '
               'save'.format(len(learned)))
    if search:
        needle = str(search).lower()
        found = [p for p in places if needle in p['name'].lower()
                 or needle in str(p.get('world', '')).lower()]
        output('{} matching {!r}:'.format(len(found), search))
        for place in found:
            output('  {} in {} (zone {})'.format(place['name'], place['world'],
                                                 place['zone_id']))
        return True
    by_world = {}
    for place in places:
        by_world.setdefault(place['world'], []).append(place['name'])
    for world in sorted(by_world):
        output('  {}: {}'.format(world, len(by_world[world])))
    return True


@sims4.commands.Command('a11y2.lots', command_type=sims4.commands.CommandType.Live)
def a11y2_lots(_connection=None):
    """List every lot in the save, marking which are empty. Read-only."""
    output = _out(_connection)
    output(lots.report())


def _households():
    """Every household in the save, newest last."""
    import services
    manager = services.household_manager()
    return list(manager.values()) if manager is not None else []


@sims4.commands.Command('a11y2.households', command_type=sims4.commands.CommandType.Live)
def a11y2_households(_connection=None):
    """List households and their home lots, numbered for a11y2.moveto."""
    output = _out(_connection)
    import services
    persistence = services.get_persistence_service()
    active = services.active_household()
    for index, household in enumerate(_households(), 1):
        try:
            sims = len(list(household.sim_info_gen()))
        except Exception:
            sims = '?'
        where = 'no home lot'
        try:
            zone_id = getattr(household, 'home_zone_id', None)
            if zone_id:
                proto = persistence.get_zone_proto_buff(zone_id)
                where = getattr(proto, 'name', None) or 'zone {}'.format(zone_id)
        except Exception:
            pass
        line = '{}: {} - {} sims, {}{}'.format(
            index, getattr(household, 'name', 'household'), sims, where,
            ' (playing)' if household is active else '')
        output(line)
        logfile.write('households: {}'.format(line))


@sims4.commands.Command('a11y2.moveto', command_type=sims4.commands.CommandType.Live)
def a11y2_moveto(index=0, _connection=None):
    """Switch to playing another household, loading their lot.

    This is the route the game uses itself (household_commands
    _activate_sims_family -> send_travel_live_to_nhd_to_live_op). It is still a
    client travel op, and a bad one of those once left the game with no active
    Sim, so SAVE FIRST - it says so rather than assuming you did.
    """
    output = _out(_connection)
    if not index:
        output('Usage: a11y2.moveto 3   (see a11y2.households). SAVE FIRST.')
        return
    try:
        position = int(index) - 1
    except Exception:
        output('Give a number from a11y2.households.')
        return
    households = _households()
    if position < 0 or position >= len(households):
        output('There are only {} households.'.format(len(households)))
        return
    household = households[position]
    name = getattr(household, 'name', 'that household')
    sim_infos = []
    try:
        sim_infos = list(household.sim_info_gen())
    except Exception:
        pass
    if not sim_infos:
        output('{} has no Sims to play.'.format(name))
        return
    zone_id = getattr(household, 'home_zone_id', None)
    logfile.write('moveto: switching to {!r} (household {}, zone {})'.format(
        name, getattr(household, 'id', '?'), zone_id))
    sim_info = sim_infos[0]
    try:
        sim_info.send_travel_live_to_nhd_to_live_op(
            getattr(household, 'id', None), zone_id)
        logfile.ok('moveto: travel op sent for {!r}'.format(name))
        output('Loading {}. If the game looks wrong afterwards, reload your '
               'save rather than saving over it.'.format(name))
    except Exception as ex:
        logfile.fail('moveto: travel op failed ({!r})'.format(ex))
        output('Could not switch to that household. The log has the reason.')


@sims4.commands.Command('a11y2.save', command_type=sims4.commands.CommandType.Live)
def a11y2_save(_connection=None):
    """Save the game without the menu."""
    output = _out(_connection)
    try:
        from server_commands.persistence_commands import save_game
    except Exception as ex:
        output('Save command unavailable ({!r}).'.format(ex))
        return
    for label, call in (
            ('save_game(True, False, connection)',
             lambda: save_game(True, False, _connection)),
            ('save_game(connection)', lambda: save_game(_connection))):
        try:
            call()
            logfile.ok('save: requested via {}'.format(label))
            output('Saving.')
            return
        except TypeError:
            continue
        except Exception as ex:
            logfile.fail('save: {} raised {!r}'.format(label, ex))
            break
    output('Could not save. The log has the reason.')


@sims4.commands.Command('a11y2.dialogs', command_type=sims4.commands.CommandType.Live)
def a11y2_dialogs(_connection=None):
    """What pop-ups the GAME currently has open, regardless of our hooks."""
    output = _out(_connection)
    live = dialogs.service_dialogs()
    if not live:
        output('The game has no dialog open right now.')
        logfile.write('dialogs: none open')
        return
    for dialog in live:
        line = '{}: {!r} ({} options)'.format(
            type(dialog).__name__, dialogs.title_of(dialog, fallback=False),
            len(dialogs.options(dialog)))
        output(line)
        logfile.write('dialogs open: {}'.format(line))


@sims4.commands.Command('a11y2.queue', command_type=sims4.commands.CommandType.Live)
def a11y2_queue(_connection=None):
    """What your Sim is actually doing and queued to do.

    "Find a Job" only queues an interaction; the picker appears once the Sim
    has walked over and used the phone. If the queue is empty the interaction
    was dropped, which looks identical to a dialog that never opened.
    """
    output = _out(_connection)
    import a11yscan_world as world
    sim = world.active_sim()
    if sim is None:
        output('No active Sim.')
        return
    try:
        running = sim.queue.running
        output('Running: {}'.format(getattr(running, 'affordance', running)))
    except Exception as ex:
        output('Could not read the running interaction ({!r}).'.format(ex))
    try:
        for index, item in enumerate(sim.queue, 1):
            line = '{}: {}'.format(index, getattr(item, 'affordance', item))
            output(line)
            logfile.write('queue: {}'.format(line))
    except Exception as ex:
        output('Could not read the queue ({!r}).'.format(ex))


@sims4.commands.Command('a11y2.quitjob', command_type=sims4.commands.CommandType.Live)
def a11y2_quitjob(_connection=None):
    """Leave your current job."""
    output = _out(_connection)
    output(careers.quit_current_job())
