"""Experimental native basement drawing, isolated from ordinary room workers."""
import configparser
import math
import threading
import time

_build = None
_core = None
_helpers = None
_selection = None
_failure = threading.local()
SETTING = 'experimental_basement'
TOOL = 'Basement Tool'


def _log(kind, **data):
    import json
    import tyjokr_a11y_speech as speech
    speech.log_line('basement adapter: ' + json.dumps(dict(kind=kind, **data), sort_keys=True, default=str))


def _enabled():
    import tyjokr_a11y_settings as settings
    return bool(settings.get(SETTING, True))


def _context():
    import services
    state = _helpers._state()
    state['household'] = int(services.active_household_id())
    return state


def _same_context(state):
    import services
    return (_enabled() and _helpers._same_world(state)
            and int(services.active_household_id()) == state['household'])


def _rooms():
    result = _build._room_ids()
    if result is None: raise RuntimeError('The game did not supply its room geometry')
    return {(tuple(box), int(level)) for box, level in result}


def _overlap(a, b):
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def _bounds(want, frame):
    if len(want) != 4 or any(isinstance(v, bool) or not isinstance(v, (int,float))
            or not math.isfinite(v) or int(v) != v for v in want):
        raise ValueError('Basement corners must be four whole-metre coordinates')
    box = tuple(int(v) for v in want)
    if not (1 <= box[0] < box[2] <= frame.width-1 and 1 <= box[1] < box[3] <= frame.depth-1):
        raise ValueError('The basement must fit at least one metre inside the lot')
    return box


def reply(encoded=''):
    # Leave all existing catalog, placement and scanner reply behavior intact.
    result = _original_reply(encoded)
    job = _selection
    if job is not None:
        try:
            from urllib.parse import unquote
            parts = unquote(str(encoded or '')).split('|')
            if (len(parts) == 3 and parts[0] == 'selected'
                    and parts[1] == str(job['index']) and unquote(parts[2]) == job['name']
                    and _build._cat['serial'] == job['serial']):
                job['done'].set()
        except Exception:
            _core.log_exc('basement tool reply')
    return result


def _tool(name, state):
    global _selection
    if not _build.on_main(_same_context, state): return False
    # The native bridge replaces its catalog array. An old index must never
    # reselect an unrelated tool if this query or selection is interrupted.
    _build.on_main(_build._cat.pop, 'chosen', None)
    items = _build.fetch_catalog(16, '', 'tool') or []
    names = [item[0] for item in items]
    _log('catalog', wanted=name, tools=names)
    if name not in names or not _build.on_main(_same_context, state): return False
    index = names.index(name)
    job = {'index':index, 'name':name, 'serial':_build._cat['serial'], 'done':threading.Event()}
    _selection = job
    silent = _build._cat.get('silent_select', False)
    try:
        _build._cat['silent_select'] = True
        _build.select_item(index, name)
        acknowledged = job['done'].wait(2.0)
        _log('tool-selection', name=name, acknowledged=acknowledged)
        return acknowledged and bool(_build.on_main(_same_context, state))
    finally:
        _selection = None
        _build._cat['silent_select'] = silent


def _check_result(before, after, wanted):
    target = (wanted, -1)
    # A bounding box alone cannot count a ground-floor room as a basement.
    return target in after-before and before.issubset(after) and after-before == {target}


def _rectangle(wanted):
    import tyjokr_a11y_plus_rooms as rooms
    frame = _build.frame()
    matches = [r for r in rooms.scan_rooms() if int(r.level) == -1 and _build._room_box(r) == wanted]
    if len(matches) != 1: return False
    actual = {(int(math.floor(frame.local(x,z)[0])), int(math.floor(frame.local(x,z)[1]))) for x,z in matches[0].tiles}
    expected = {(x,z) for x in range(wanted[0],wanted[2]) for z in range(wanted[1],wanted[3])}
    return actual == expected


def _draw(want, overview):
    state = _build.on_main(_context)
    if not state: raise RuntimeError('The simulation thread did not answer')
    frame = _build.on_main(_build.frame)
    if frame is None: raise RuntimeError('The lot geometry is unavailable')
    wanted = _bounds(want, frame)
    before = _build.on_main(_rooms)
    if before is None: raise RuntimeError('Room inspection timed out')
    if any(level == -1 and _overlap(box,wanted) for box,level in before):
        _log('occupied', wanted=wanted)
        return 'occupied'
    if not _build.set_floor(0): return 'nofloor'
    selected = False
    attempted = False
    result = 'nocatalog'
    restore_ok = True
    try:
        attempted = True
        selected = _tool(TOOL, state)
        if not selected:
            _core.post(_core.speak, 'The native Basement Tool was not confirmed. Nothing was drawn. Its catalog entries were logged.')
            return 'nocatalog'
        points = [frame.world(wanted[0],wanted[1]), frame.world(wanted[2],wanted[3])]
        started = time.monotonic()
        funds_before = _build.on_main(_build.funds)
        def action(screen):
            if not _build.on_main(_same_context,state): raise RuntimeError('Build context changed before the basement drag')
            if not _tool(TOOL,state): raise RuntimeError('The Basement Tool could not be confirmed after camera preparation')
            info = _helpers._native_floor(state)
            if info['floor'] != 0: raise RuntimeError('The game is no longer showing the ground floor')
            _log('drag', wanted=wanted, input_floor=0, expected_floor=-1, native_floor=info)
            _build.drag(screen[0],screen[1])
        performed = _build.point_and_act(points,0,action,'experimental basement {}'.format(wanted),overview=overview)
        if not performed: return 'noscreen'
        _log('after-drag', native_floor=_helpers._native_floor(state), funds_before=funds_before, funds_after=_build.on_main(_build.funds))
        after = before
        for attempt in range(20):
            if not _build.on_main(_same_context,state): raise RuntimeError('Build context changed while checking the basement')
            after = _build.on_main(_rooms)
            if after is None: raise RuntimeError('Basement verification timed out')
            if after != before: break
            time.sleep(.25)
        okay = _check_result(before,after,wanted) and bool(_build.on_main(_rectangle,wanted))
        error = _build._last_error
        reason = error.get('text','') if error.get('at',0) >= started else ''
        _log('verification', wanted=wanted, expected_floor=-1, new=sorted(after-before),
             removed=sorted(before-after), success=okay, game_reason=reason)
        result = wanted if okay else 'unverified'
        if not okay:
            _core.post(_core.speak, 'Basement construction stopped: the game did not confirm the requested room on floor minus one.'
                       + (' Game message: '+reason if reason else '') + ' Inspect the result before using Undo or trying again.')
    finally:
        # Never leave Basement Tool selected for the next above-ground room.
        if attempted:
            if _build.on_main(_same_context,state): restore_ok = _tool('Room Tool',state)
            else: restore_ok = False
            _log('restore-room-tool', success=restore_ok)
    if not restore_ok:
        _core.post(_core.speak,'The basement step stopped because the ordinary Room Tool could not be restored.')
        return 'nocatalog'
    return result


def failure_reason():
    return getattr(_failure,'reason','')


def room_worker(want, overview=False, tries=4, level=0):
    _failure.reason = ''
    if level != -1:
        return _original_room(want,overview=overview,tries=tries,level=level)
    if not _enabled():
        _core.post(_core.speak,'Experimental basement creation is off in accessibility settings.')
        result = 'disabled'
    else:
        try:
            result = _draw(want,overview)
        except Exception as exc:
            _log('stopped', wanted=want, error=str(exc))
            _core.post(_core.speak,'Basement construction stopped. '+str(exc))
            result = 'unverified'
    if result != tuple(want):
        _failure.reason = {'disabled':'experimental basement creation is turned off',
                          'occupied':'the requested footprint overlaps an existing basement room',
                          'nofloor':'the game could not reach the ground floor for the basement tool',
                          'nocatalog':'the required native tool selection was not confirmed',
                          'noscreen':'the corners could not be framed clear of the interface'}.get(result,'the requested room on floor minus one could not be verified')
    return result


def _start_room(wanted):
    if _build._busy[0]:
        _core.speak('Still working on the last build step.'); return
    if not _enabled():
        _core.speak('Turn on experimental basement creation in accessibility settings first.'); return
    _build._busy[0] = True
    _core.speak('Building the basement room. Please do not press keys until it finishes.')
    def work():
        try:
            result = room_worker(wanted,overview=True,level=-1)
            if result == wanted:
                shown = _build.set_floor(-1)
                _core.post(_core.speak,'The basement room was verified on floor minus one. '
                           + ('The game now shows the basement.' if shown else 'The room exists, but the game could not switch to its floor.'))
            else:
                _core.post(_core.speak,'The basement room was not completed: {}. No further rooms were attempted.'.format(result))
        finally:
            _build._busy[0] = False
    try: threading.Thread(target=work,name='a11y_basement_room',daemon=True).start()
    except Exception:
        _build._busy[0] = False
        raise


def _ask_room():
    def size(text):
        values = _build._numbers(text)
        if len(values) != 2 or any(v < 1 or v > 30 for v in values):
            _core.speak('Type a width and depth between 1 and 30 metres.'); return
        width,depth = values
        def position(text):
            coords = _build._numbers(text)
            if len(coords) != 2:
                _core.speak('Type meters from west and north, for example 2 3.'); return
            wanted = (coords[0],coords[1],coords[0]+width,coords[1]+depth)
            try: _bounds(wanted,_build.frame())
            except ValueError as exc: _core.speak(str(exc)); return
            rows=[('Build this basement room','Uses the native tool and spends household funds only if the game accepts it.',True),('Cancel',None,False)]
            _core.choose('Confirm experimental basement','{} by {} metres, {} from west and {} from north. Floor minus one. Existing basement rooms must not overlap this footprint.'.format(width,depth,*coords),rows,
                         lambda yes:_start_room(wanted) if yes else None,tag='build')
        _core.ask_text('Basement position','Type meters from the west edge, then the north edge of the lot. For example 2 3.','',position)
    _core.ask_text('Basement size','Type width west to east and depth north to south in metres, for example 4 5.','',size)


def _inspect():
    if _build._busy[0]: _core.speak('Still working on the last build step.'); return
    _build._busy[0] = True
    def work():
        try:
            state = _build.on_main(_context)
            info = _helpers._native_floor(state)
            geometry = _build.on_main(_rooms)
            if geometry is None: raise RuntimeError('Room inspection timed out')
            basements = sorted(box for box,level in geometry if level == -1)
            _log('inspect', basement_rooms=basements, native_floor=info)
            _core.post(_core.speak,'Logged current floor bounds and {} basement rooms. Nothing was built or selected.'.format(len(basements)))
        except Exception as exc:
            _log('inspect-failed',error=str(exc)); _core.post(_core.speak,'Basement inspection failed. '+str(exc))
        finally: _build._busy[0] = False
    try: threading.Thread(target=work,name='a11y_basement_inspect',daemon=True).start()
    except Exception:
        _build._busy[0] = False; raise


def open_assistant():
    if not _build.in_build_mode(): _core.speak('Enter Build mode first.'); return
    rows=[('Build a rectangular basement room','Choose size and position; verifies floor minus one before reporting success.',_ask_room),
          ('Inspect basement floors and rooms','Read-only native-floor and room diagnostics; builds and selects nothing.',_inspect)]
    _core.choose('Basement assistant (experimental)','Stacked houses with a basement use the same adapter automatically. Creation can be turned off in accessibility settings.',rows,lambda fn:fn(),tag='build')


def install():
    """Startup: the engine and helper modules this adapter uses. Idempotent."""
    global _build, _core, _helpers
    if _build is not None:
        return
    import tyjokr_a11y_plus_build as build
    import tyjokr_a11y_plus_core as core
    import tyjokr_a11y_build_helpers as helpers
    _build, _core, _helpers = build, core, helpers
    _log('installed', experimental=True, enabled=_enabled())


def _original_room(want, overview=False, tries=4, level=0):
    import tyjokr_a11y_plus_build as build
    return build._room_worker_base(want, overview=overview, tries=tries, level=level)


def _original_reply(encoded=''):
    import tyjokr_a11y_plus_build as build
    return build._flash_reply_base(encoded)
