"""Which scanner objects the active Sim can use right now.

Mirrors how the native pie decides what to list (interactions/choices.py,
checked against the 1.128.90 bytecode because the decompile prints add_aop
with its test inverted): a passing aop is listed, a failing aop with a
tooltip is listed greyed, and a failing aop without one, a suppressed aop,
or an affordance that is not user-directed is not listed at all. Per object:

  usable   at least one listed row passes
  locked   every listed row is greyed (requirements the pie explains)
  empty    the pie would list nothing for this Sim
  pending  not checked yet for this Sim; shown, never hidden

Simulation thread only. A check is a generator that pauses after every
native test, so pump ticks share a small time budget even inside one
object. Nothing here builds a ChoiceMenu or touches the client's choices.
A verdict that keeps coming back the same is checked less often, and an
object whose checks are slow waits longer still, up to MAX_RECHECK_SECONDS.
"""
import sys
import time

import sims4.commands

import tyjokr_a11y_pump as pump
import tyjokr_a11y_settings as settings
import tyjokr_a11y_speech as speech

PENDING = 'pending'
USABLE = 'usable'
LOCKED = 'locked'
EMPTY = 'empty'

RECHECK_SECONDS = 10.0     # first recheck; doubles while the verdict holds
MAX_RECHECK_SECONDS = 60.0
SLOW_STEP_MS = 16.0        # one native step at least this long is a hitch
BUDGET_SECONDS = 0.004     # per pump tick; at least one step always runs
MAX_STEPS = 400            # rows one object may cost before it stays listed
_REARM_SECONDS = 0.5       # the pump drops its oldest entry when full
_LOG_SECONDS = 30.0        # unchanged run summaries are logged this often
_VERDICT_LIMIT = 2000      # verdicts kept for objects out of the scan, oldest dropped

_sim_id = None
_token = 0                 # only the most recently posted tick does work
# obj_id -> (state, checked_at, why, failed, streak, due, cost_ms)
_verdicts = {}
_queue = []
_in_scan = set()           # ids in the latest begin(); counts cover these only
_current = None            # the _Check in progress, resumable across ticks
_revision = 0
_scheduled_at = None       # when the pending tick was posted, None if idle
_errors_logged = set()
_last_tick_ms = 0.0
_run = {}
_last_log = {'at': None, 'counts': None}


class _Check(object):
    __slots__ = ('obj_id', 'label', 'gen', 'steps', 'cost_ms', 'phase', 'at')

    def __init__(self, obj_id, label):
        self.obj_id = obj_id
        self.label = label
        self.gen = None
        self.steps = 0
        self.cost_ms = 0.0
        self.phase = 'setup'
        self.at = ''


def _clear_run():
    _run.update(checked=0, max_tick_ms=0.0, max_step_ms=0.0, slow_steps=0, slowest='')


_clear_run()


def _shown(state):
    # What the scanner does with a verdict. Only a change here needs a rebuild.
    if state == EMPTY:
        return 'hidden'
    return 'tagged' if state == LOCKED else 'plain'


def _bump():
    global _revision
    _revision += 1


def _interval(streak, cost_ms):
    seconds = RECHECK_SECONDS * (2 ** min(max(streak, 1) - 1, 6))
    if cost_ms >= SLOW_STEP_MS:
        seconds *= 2
    return min(seconds, MAX_RECHECK_SECONDS)


def _drop_current():
    global _current
    if _current is not None and _current.gen is not None:
        try:
            _current.gen.close()
        except Exception:
            pass
    _current = None


def _cancel_work():
    global _token, _scheduled_at
    del _queue[:]
    _drop_current()
    _token += 1
    _scheduled_at = None


def _forget_all():
    # A new Sim or zone: its first run summary is always logged.
    _verdicts.clear()
    _in_scan.clear()
    _cancel_work()
    _clear_run()
    _last_log['counts'] = None
    _bump()


def revision():
    return _revision


def _wanted():
    return bool(settings.get('keyboard', True)) and bool(settings.get('scanner', True))


def _ui_busy():
    # A dialog, the console or a scanner menu owns input. A native step
    # cannot be preempted, so the worker steps aside until the next scan.
    # Looked up, not imported: keys and scanner import this module.
    keys = sys.modules.get('tyjokr_a11y_keys')
    if keys is not None and (getattr(keys, '_modal_active', False) or getattr(keys, '_editing_active', False)):
        return True
    scanner = sys.modules.get('tyjokr_a11y_scanner')
    return bool(scanner is not None and getattr(scanner, '_menu_open', False))


def begin(sim, objects):
    """Queue this scan's candidates that are due; keep every known verdict.
    Never raises: anything unchecked simply stays pending, and listed."""
    try:
        return _begin(sim, objects)
    except Exception as ex:
        speech.log_line('availability: begin failed {!r}'.format(ex))
        return _revision


def _begin(sim, objects):
    global _sim_id
    sim_id = getattr(sim, 'id', None)
    if sim_id != _sim_id:
        _forget_all()
        _sim_id = sim_id
    if sim_id is None:
        return _revision
    now = time.monotonic()
    fresh = []
    due = []
    keep = set()
    busy = _current.obj_id if _current is not None else None
    for obj in objects:
        obj_id = getattr(obj, 'id', None)
        if obj_id is None or obj_id in keep:
            continue
        keep.add(obj_id)
        if obj_id == busy:
            continue
        verdict = _verdicts.get(obj_id)
        if verdict is None:
            fresh.append(obj_id)
        elif now >= verdict[5]:
            due.append((verdict[5], obj_id))
    # Objects that left the scan keep their verdicts, so walking back in
    # range shows the last known state at once; only the oldest go.
    spare = [(verdict[1], obj_id) for obj_id, verdict in _verdicts.items() if obj_id not in keep]
    if len(spare) > _VERDICT_LIMIT:
        spare.sort()
        for _, obj_id in spare[:len(spare) - _VERDICT_LIMIT]:
            del _verdicts[obj_id]
    if busy is not None and busy not in keep:
        _drop_current()
    due.sort()
    _in_scan.clear()
    _in_scan.update(keep)
    _queue[:] = fresh + [obj_id for _, obj_id in due]
    _ensure_ticking(now)
    return _revision


def state(obj_or_id):
    try:
        obj_id = obj_or_id if isinstance(obj_or_id, int) else obj_or_id.id
        if _queue or _current is not None:
            _ensure_ticking(time.monotonic())
        verdict = _verdicts.get(obj_id)
        return PENDING if verdict is None else verdict[0]
    except Exception:
        return PENDING


def invalidate(obj_ids=None):
    if obj_ids is None:
        _verdicts.clear()
        _drop_current()
    else:
        for obj_id in obj_ids:
            _verdicts.pop(obj_id, None)
            if _current is not None and _current.obj_id == obj_id:
                _drop_current()
    _bump()


def recheck(obj_ids=None):
    """Check again at the next begin(), keeping the last-known verdicts
    meanwhile, so an explicit rescan does not make hidden objects flicker."""
    for obj_id, verdict in list(_verdicts.items()):
        if obj_ids is None or obj_id in obj_ids:
            _verdicts[obj_id] = verdict[:5] + (0.0,) + verdict[6:]


def pause():
    """Stop checking (the scanner went idle) but keep everything known, so
    the next scan shows the last filtered list at once and only rechecks
    what has come due."""
    _cancel_work()


def on_active_sim_changed(old_sim=None, new_sim=None):
    # Signature matches client.register_active_sim_changed.
    global _sim_id
    _forget_all()
    _sim_id = None


def reset():
    global _sim_id
    _forget_all()
    _sim_id = None
    _errors_logged.clear()


def _ensure_ticking(now):
    # A re-post supersedes the earlier tick, so a delayed tick and its
    # replacement can never both work in the same pump drain.
    global _scheduled_at, _token
    if not _queue and _current is None:
        return
    if _scheduled_at is not None and now - _scheduled_at < _REARM_SECONDS:
        return
    _token += 1
    if pump.post(_tick, _token):
        _scheduled_at = now


def _label(obj):
    try:
        return str(getattr(obj.definition, 'name', '') or type(obj).__name__)[:40]
    except Exception:
        return '?'


def _tick(token=None):
    global _scheduled_at, _last_tick_ms, _current
    if token != _token:
        return
    _scheduled_at = None
    if not _queue and _current is None:
        return
    if not _wanted():
        reset()
        return
    if _ui_busy():
        pause()
        return
    try:
        import services
        sim = services.get_active_sim()
        client = services.client_manager().get_first_client()
        manager = services.object_manager()
    except Exception as ex:
        speech.log_line('availability: services unavailable {!r}'.format(ex))
        _cancel_work()
        return
    if sim is None or client is None or sim.id != _sim_id:
        # Verdicts belong to the Sim they were made for; the next scan's
        # begin() starts over for whoever is active now.
        _forget_all()
        return
    started = time.perf_counter()
    deadline = started + BUDGET_SECONDS
    worked = False
    while _queue or _current is not None:
        # Every pass counts against the budget, a vanished object included.
        if worked and time.perf_counter() >= deadline:
            break
        worked = True
        if _current is None:
            obj_id = _queue.pop(0)
            try:
                obj = manager.get(obj_id)
            except Exception as ex:
                _store(obj_id, USABLE, repr(ex)[:80], True, 0.0)
                continue
            if obj is None:
                _verdicts.pop(obj_id, None)
                continue
            _current = _Check(obj_id, _label(obj))
            _current.gen = _evaluation(sim, client, obj, _current)
        check = _current
        step_started = time.perf_counter()
        outcome = _step(check)
        step_ms = (time.perf_counter() - step_started) * 1000.0
        check.cost_ms = max(check.cost_ms, step_ms)
        if step_ms >= SLOW_STEP_MS:
            _run['slow_steps'] += 1
        if step_ms > _run['max_step_ms']:
            _run['max_step_ms'] = step_ms
            _run['slowest'] = '{} {} {} {}'.format(check.obj_id, check.label, check.phase, check.at).strip()
        if outcome is not None:
            _current = None
            _store(check.obj_id, outcome[0], outcome[1], outcome[2], check.cost_ms)
            _run['checked'] += 1
    _last_tick_ms = (time.perf_counter() - started) * 1000.0
    _run['max_tick_ms'] = max(_run['max_tick_ms'], _last_tick_ms)
    if _queue or _current is not None:
        _ensure_ticking(time.monotonic())
    elif _run['checked']:
        _log_run()


def _log_run():
    # Once per finished run at most, and an unchanged picture only every
    # _LOG_SECONDS; the numbers keep adding up in between.
    now = time.monotonic()
    counts = _counts_text()
    if (counts == _last_log['counts'] and _last_log['at'] is not None
            and now - _last_log['at'] < _LOG_SECONDS):
        return
    speech.log_line('availability: checked {} for sim {} ({}), slowest tick {:.1f} ms, '
                    'slowest step {:.1f} ms, {} steps over {:.0f} ms{}'.format(
                        _run['checked'], _sim_id, counts, _run['max_tick_ms'], _run['max_step_ms'],
                        _run['slow_steps'], SLOW_STEP_MS,
                        ', slowest at {}'.format(_run['slowest']) if _run['slowest'] else ''))
    _last_log['at'] = now
    _last_log['counts'] = counts
    _clear_run()


class _LoggerProxy(object):
    """Stands in for objects.script_object.logger while a step runs.

    ScriptObject.potential_interactions catches its own exceptions and
    reports them with logger.exception, then simply stops yielding, which
    would read as an object with nothing to offer. The proxy records the
    report so the object stays listed, and keeps a background check from
    raising an error report the player never caused (a mouse click on the
    same object still reports it as before)."""

    def __init__(self, real, watch):
        self._real = real
        self._watch = watch

    def exception(self, message='', *args, **kwargs):
        self._watch.message = str(message)[:80]

    def __getattr__(self, name):
        return getattr(self._real, name)


class _SwallowWatch(object):
    def __init__(self):
        self.message = None
        self._module = None
        self._real = None

    def __enter__(self):
        try:
            import objects.script_object as module
            self._real = module.logger
            self._module = module
            module.logger = _LoggerProxy(self._real, self)
        except Exception:
            self._module = None
        return self

    def __exit__(self, *exc_info):
        if self._module is not None:
            self._module.logger = self._real
        return False


def _step(check):
    """Advance one check by one native test; its outcome when finished."""
    check.steps += 1
    watch = _SwallowWatch()
    outcome = None
    try:
        with watch:
            next(check.gen)
    except StopIteration as done:
        outcome = done.value
    except Exception as ex:
        outcome = (USABLE, repr(ex)[:80], True)
    if watch.message is not None:
        outcome = (USABLE, 'swallowed: ' + watch.message, True)
    elif outcome is None and check.steps >= MAX_STEPS:
        outcome = (USABLE, 'over {} rows'.format(MAX_STEPS), True)
    if outcome is not None:
        try:
            check.gen.close()
        except Exception:
            pass
    return outcome


def _store(obj_id, verdict, why, failed, cost_ms):
    old = _verdicts.get(obj_id)
    streak = 1
    if old is not None and old[0] == verdict and bool(old[3]) == bool(failed):
        # The same outcome again, an error included: an object that always
        # fails (listed, fail-open) need not be retried every few seconds.
        streak = old[4] + 1
    now = time.monotonic()
    _verdicts[obj_id] = (verdict, now, why, failed, streak, now + _interval(streak, cost_ms), cost_ms)
    if failed and (_sim_id, obj_id) not in _errors_logged:
        _errors_logged.add((_sim_id, obj_id))
        speech.log_line('availability: check failed for {}, kept listed: {}'.format(obj_id, why))
    if _shown(verdict) != _shown(PENDING if old is None else old[0]):
        _bump()


def _name(affordance):
    return getattr(affordance, '__name__', None) or str(affordance)


def _evaluation(sim, client, obj, check):
    """Generator: pauses after each native test, returns (state, why, failed).
    check.phase and check.at name the work the latest step did."""
    import services
    import interactions.choices as choices
    from server.pick_info import PickInfo, PickType
    ChoiceMenu = choices.ChoiceMenu
    show_hidden = bool(getattr(choices, '_show_interaction_failure_reason', False))
    try:
        lot_id = int(services.active_lot().lot_id)
    except Exception:
        lot_id = 0
    try:
        level = int(obj.level)
    except Exception:
        level = 0
    parameters = client.get_interaction_parameters() or {}
    location = obj.position
    surface = obj.routing_surface
    targets = [obj]
    for target in obj.forwarded_pick_targets or ():
        if target is not None and target is not obj:
            targets.append(target)
    yield
    locked_by = None
    parents = []               # (aop, result, context): rows the pie lists only through their mixers
    for target in targets:
        # As _add_potential_object_aops: one pick and context per target, at
        # the picked object's location, surface and level, preferring it.
        check.phase = 'rows'
        pick = PickInfo(pick_type=PickType.PICK_OBJECT, target=target, location=location,
                        routing_surface=surface, lot_id=lot_id, level=level)
        context = client.create_interaction_context(sim, pick=pick)
        context.add_preferred_objects((obj,))
        for aop in target.potential_interactions(context, **parameters):
            affordance = aop.affordance
            check.at = _name(affordance)
            result = ChoiceMenu.is_valid_aop(aop, context, user_pick_target=target)
            if affordance.allow_user_directed is False:
                if show_hidden and locked_by is None:
                    locked_by = affordance
                if result or result.tooltip:
                    parents.append((aop, result, context))
            elif result:
                return USABLE, _name(affordance), False
            elif result.tooltip and locked_by is None:
                locked_by = affordance
            yield
        check.phase = 'rows end'
    # A greyed row's mixers inherit its failure, so they can add greyed
    # rows only; walk the passing parents first, they may add usable ones.
    parents.sort(key=lambda parent: not parent[1])
    for aop, result, context in parents:
        parent_passed = bool(result)
        if not parent_passed and locked_by is not None:
            break
        check.phase = 'mixers'
        check.at = _name(aop.affordance)
        sub_rows = aop.affordance.potential_pie_menu_sub_interactions_gen(
            aop.target, context, None, **aop.interaction_parameters)
        for mixer_aop, mixer_result in sub_rows or ():
            mixer = mixer_aop.affordance
            if mixer.allow_user_directed is False:
                if show_hidden and locked_by is None:
                    locked_by = mixer
            else:
                checked = ChoiceMenu.is_valid_aop(
                    mixer_aop, context,
                    result_override=mixer_result if parent_passed else result, do_test=False)
                if checked:
                    return USABLE, _name(mixer), False
                if getattr(checked, 'tooltip', None) and locked_by is None:
                    locked_by = mixer
            yield
            if not parent_passed and locked_by is not None:
                break
    if locked_by is not None:
        return LOCKED, _name(locked_by), False
    # Rows this first cut does not probe: the pie adds terrain or ocean
    # points for surface providers, and fire rows when a nearby fire would
    # otherwise leave it empty. Keep those objects listed rather than guess.
    check.phase = 'special'
    if (getattr(obj, 'provided_routing_surface', None) is not None
            or getattr(obj, 'provides_terrain_interactions', False)
            or getattr(obj, 'provides_ocean_interactions', False)):
        return USABLE, 'surface provider, not probed', False
    fire_service = services.get_fire_service()
    if fire_service is not None and fire_service.fire_is_active:
        if fire_service.get_fires_in_potential_targets([(target, surface) for target in targets]):
            return USABLE, 'fire nearby, not probed', False
    return EMPTY, '', False


def _counts():
    counts = {USABLE: 0, LOCKED: 0, EMPTY: 0, 'errors': 0}
    for obj_id, verdict in _verdicts.items():
        if obj_id not in _in_scan:
            continue
        counts[verdict[0]] += 1
        if verdict[3]:
            counts['errors'] += 1
    return counts


def _counts_text():
    counts = _counts()
    return 'usable {} locked {} empty {} errors {}'.format(
        counts[USABLE], counts[LOCKED], counts[EMPTY], counts['errors'])


def status():
    return 'availability: sim {} {} queued {} busy {} last tick {:.1f} ms revision {}'.format(
        _sim_id, _counts_text(), len(_queue), _current.obj_id if _current is not None else '-',
        _last_tick_ms, _revision)


@sims4.commands.Command('a11y.availability', command_type=sims4.commands.CommandType.Live)
def a11y_availability(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    output(status())
    try:
        import services
        sim = services.get_active_sim()
        manager = services.object_manager()
        now = time.monotonic()
        rows = []
        for obj_id, verdict in _verdicts.items():
            obj = manager.get(obj_id)
            if obj is None or sim is None:
                continue
            dx = float(obj.position.x) - float(sim.position.x)
            dz = float(obj.position.z) - float(sim.position.z)
            rows.append((dx * dx + dz * dz, obj, verdict))
        rows.sort(key=lambda row: row[0])
        for distance, obj, verdict in rows[:10]:
            output('  {:.1f} m {} {} {} ({:.1f} ms, next in {:.0f} s)'.format(
                distance ** 0.5, _label(obj), verdict[0], verdict[2], verdict[6],
                max(0.0, verdict[5] - now)))
        slow = sorted(_verdicts.items(), key=lambda item: -item[1][6])[:3]
        output('  slowest: ' + ', '.join('{} {:.1f} ms'.format(obj_id, verdict[6]) for obj_id, verdict in slow))
    except Exception as ex:
        output('availability: listing failed {!r}'.format(ex))
