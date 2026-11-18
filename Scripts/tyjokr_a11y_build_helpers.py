"""Narrow integration fixes for the existing house/structure helpers."""
import contextlib
import math
import time
import threading

_floor_lock = threading.Lock()
_floor_job = None
_floor_sequence = -1
_floor_quarantined = False
_planner = None
_house_context = threading.local()
_installed = False

_build = None
_coordinates = None


def _log(kind, **data):
    import tyjokr_a11y_speech as speech
    import json
    speech.log_line('build helpers: ' + json.dumps(dict(kind=kind, **data), sort_keys=True, default=str))


def _state():
    import services
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_keys as keys
    if not _build.in_build_mode() or keys.blocking_active() or keys._editing_active:
        raise RuntimeError('Close the game dialog before changing floors')
    lot = services.active_lot()
    if lot is None: raise RuntimeError('No active lot')
    floor = None  # Camera position is not a native floor number.
    return {'zone': int(services.current_zone_id()), 'floor': floor,
            'center': (float(lot.center.x), float(lot.center.z)),
            'grid': bool(grid.build_cursor()), 'owner': bool(keys._build_grid_owner)}


def _same_world(state):
    import services
    import tyjokr_a11y_keys as keys
    return (_build.in_build_mode() and int(services.current_zone_id()) == state['zone']
            and not keys.blocking_active() and not keys._editing_active)


def _grid_message(message):
    import tyjokr_a11y_grid as grid
    grid._flash(message)


def _grid_released():
    import tyjokr_a11y_keys as keys
    return not keys._build_grid_owner


def _restore_grid(state):
    import services
    import tyjokr_a11y_grid as grid
    if (state['grid'] and _build.in_build_mode() and
            int(services.current_zone_id()) == state['zone'] and grid.build_cursor()):
        grid._flash('A11yBuildGridOn')
        return True
    return False


@contextlib.contextmanager
def _floor_input(state):
    u = _coordinates._api()
    sent_off = False
    try:
        with _coordinates.physical_context(u):
            geometry = _coordinates.window(u)
            if state['grid'] or state['owner']:
                # Only release native key ownership. Preserve the Python grid's
                # tile, height, room focus, orientation and enabled setting.
                sent_off = True
                _build.on_main(_grid_message, 'A11yBuildGridOff')
                # A fresh native request is an ordered UI round trip after Off.
                # It does not move any cursor or click. Never inject a floor key
                # before the native guard and script owner have both released.
                _coordinates._measure(state['center'][0], state['center'][1], state['floor'])
                deadline = time.monotonic() + 2.0
                while not _build.on_main(_grid_released):
                    if time.monotonic() >= deadline: raise RuntimeError('Grid ownership did not release')
                    time.sleep(.02)
                _log('floor-ownership-released', zone=state['zone'])
            yield u, geometry
    finally:
        if sent_off:
            restored = _build.on_main(_restore_grid, state)
            _log('floor-ownership-restored', zone=state['zone'], restored=bool(restored))


def _receive_floor(zone, sequence, status, current, minimum, maximum):
    """Simulation-thread reply from the single native ControlPanel definer."""
    global _floor_sequence
    job = _floor_job
    if job is None or job['done'].is_set() or str(zone) != str(job['zone']): return
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence <= _floor_sequence: return
    _floor_sequence = sequence
    if status != 'ok':
        job['error'] = 'Native floor query: ' + str(status)
    elif (any(isinstance(v, bool) or not isinstance(v, int) for v in (current, minimum, maximum))
          or not -64 <= minimum <= current <= maximum <= 64):
        job['error'] = 'Invalid native floor bounds'
    else:
        job['result'] = {'floor': current, 'minimum': minimum, 'maximum': maximum}
    job['done'].set()


def _native_floor(state, timeout=3.0):
    """One outstanding read-only query; quarantine after timeout, never reuse late replies."""
    global _floor_job, _floor_quarantined
    if _floor_quarantined: raise RuntimeError('Native floor channel timed out; restart the game before retrying')
    if not _floor_lock.acquire(False): raise RuntimeError('Another native floor query is active')
    try:
        job = {'zone': state['zone'], 'done': threading.Event()}
        _floor_job = job
        def send():
            if not _same_world(state): raise RuntimeError('Build context changed before the native query')
            _build._send_ui('A11yNativeFloorQuery')
            return True
        if _build.on_main(send) is not True:
            _floor_quarantined = True
            raise RuntimeError('Native floor query could not be dispatched')
        if not job['done'].wait(timeout):
            _floor_quarantined = True
            raise RuntimeError('Native floor UI did not answer; install the matching UI package')
        if 'error' in job: raise RuntimeError(job['error'])
        if not _build.on_main(_same_world, state): raise RuntimeError('Build context changed during the native query')
        return job['result']
    finally:
        _floor_job = None
        _floor_lock.release()


def set_floor(level):
    """Use BBGetLevelInfo, never camera height, to verify native floor keys."""
    try:
        if isinstance(level, bool) or not isinstance(level, (int, float)) or not math.isfinite(level) or int(level) != level:
            return False
        level = int(level)
    except (ValueError, OverflowError):
        return False
    try:
        state = _build.on_main(_state)
        if state is None: raise RuntimeError('Simulation thread did not answer')
        info = _native_floor(state)
        state['floor'] = info['floor']
        _log('floor-query', wanted=level, **info)
        if not info['minimum'] <= level <= info['maximum']:
            _log('floor-out-of-range', wanted=level, **info)
            return False
        if state['floor'] == level: return True
        with _floor_input(state) as (u, geometry):
            for _ in range(abs(level - state['floor'])):
                if _coordinates.window(u) != geometry or not _build.on_main(_same_world, state):
                    raise RuntimeError('Game focus, window or Build context changed')
                if not _build.on_main(_grid_released): raise RuntimeError('The grid reclaimed the floor keys')
                if any(u.GetAsyncKeyState(key) & 0x8000 for key in (16,17,18,91,92)):
                    raise RuntimeError('Release modifier keys before changing floors')
                current = _native_floor(state)['floor']
                if current == level: return True
                step = 1 if current < level else -1
                key, scan = (33, 0x49) if step > 0 else (34, 0x51)
                if (not _build.on_main(_same_world, state) or _coordinates.window(u) != geometry
                        or u.GetAsyncKeyState(key) & 0x8000):
                    raise RuntimeError('Input context changed before the floor key')
                pressed = False
                try:
                    u.keybd_event(key, scan, 1, 0); pressed = True
                    time.sleep(.05)
                finally:
                    if pressed: u.keybd_event(key, scan, 3, 0)
                actual = current
                # Wait for one key acknowledgement; never stack unacknowledged keys.
                for poll in range(30):
                    time.sleep(.1)
                    if _coordinates.window(u) != geometry or not _build.on_main(_same_world, state):
                        raise RuntimeError('Build context changed while waiting for the floor')
                    actual = _native_floor(state)['floor']
                    if actual != current: break
                _log('floor-step', wanted=level, before=current, actual=actual, source='BBGetLevelInfo')
                if actual != current + step: return False
                if actual == level: return True
            return False
    except Exception as exc:
        _log('floor-refused', wanted=level, error=str(exc))
        return False


def _house_build(plan):
    """Scope stacked stairs to the running plan, even after a failed room."""
    planner = _planner
    if planner is None: return _original_house_build(plan)
    _house_context.transitions = tuple(getattr(plan, '_a11y_transitions', ()))
    planner._pending_stairs = []
    try:
        return _original_house_build(plan)
    finally:
        planner._pending_stairs = []
        _house_context.transitions = ()


def _stairs_for_plan(top, climb):
    planner = _planner
    transitions = getattr(_house_context, 'transitions', ())
    if planner is None or not transitions: return _original_house_stairs(top, climb)
    for stair_top, stair_climb, lower, upper in transitions:
        result = planner._place_stair_at(stair_top, stair_climb, lower)
        _log('stair-transition', lower=lower, upper=upper, result=result)
        if result is not True: return result
    return True


def install():
    """Startup: the a11y.floor_native reply command. Idempotent."""
    global _build, _coordinates, _planner, _installed
    if _installed:
        return
    _installed = True
    import tyjokr_a11y_plus_build as build
    import tyjokr_a11y_build_coordinates as coordinates
    import sims4.commands
    def receive(zone: str='', sequence: int=0, status: str='', current: int=0, minimum: int=0, maximum: int=0, _connection=None):
        _receive_floor(zone, sequence, status, current, minimum, maximum)
    sims4.commands.Command('a11y.floor_native', command_type=sims4.commands.CommandType.Live)(receive)
    try:
        import tyjokr_a11y_house_planner as planner
    except ImportError:
        planner = None
    _planner = planner
    _build, _coordinates = build, coordinates
    _log('installed')


def _original_house_build(plan):
    import tyjokr_a11y_detached as detached
    return detached._build_followup(plan)


def _original_house_stairs(top, climb):
    import tyjokr_a11y_plus_house as house
    return house._place_stairs_worker_base(top, climb)
