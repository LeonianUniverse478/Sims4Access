"""Run work on the simulation thread from threads we created.

The game's Python is single-threaded by contract: Sims, objects, the
interaction system and the distributor all belong to the simulation thread.
The keyboard poller and the speech timers are threads of our own, so any
key press that wants to touch the game has to cross over first. This module
is that crossing: post() queues a callable, and a repeating wall-clock alarm
that the game itself fires on the simulation thread drains the queue.

Facts this relies on (checked against the 1.127.41 decompile):

- alarms.add_alarm_real_time schedules on time_service().wall_clock_timeline,
  which advances from the server clock, so it keeps firing while the game is
  paused.
- That timeline is torn down with the zone and takes the alarm with it, so
  the alarm is re-armed on every zone load through the same
  on_loading_screen_animation_finished hook the narrator uses. start() is
  idempotent.
- AlarmHandle keeps its owner by WEAK reference; the owner has to stay alive
  on our side or the alarm dies silently.

Nothing queued is ever run on the calling thread. When no pump is running
(no lot loaded, or the alarm went quiet), post() refuses and returns False
so the caller can tell the player, instead of touching the game from the
wrong thread. That is the deliberate difference from the mod this was
adapted from, which fell back to running game code on the key thread.
"""
import threading
import time

import tyjokr_a11y_speech as speech

_INTERVAL_SECONDS = 0.02   # the game ticks at about 60 Hz; finer buys nothing
_STALE_SECONDS = 2.0       # silence longer than this means the alarm is gone
_MAX_QUEUED = 32           # a held key must never build a backlog

_lock = threading.Lock()
_queue = []
_handle = None
_owner = None
_last_drain = 0.0


class _Owner(object):
    """Something for the alarm to own: it refuses None and holds it weakly."""


def alive():
    """True while the simulation thread has drained us recently."""
    return _handle is not None and (time.monotonic() - _last_drain) < _STALE_SECONDS


def post(fn, *args):
    """Queue fn(*args) for the simulation thread.

    Returns False, and runs nothing, when the pump is not alive."""
    if not alive():
        return False
    with _lock:
        if len(_queue) >= _MAX_QUEUED:
            del _queue[0]
        _queue.append((fn, args))
    return True


def _drain(_alarm_handle=None):
    global _last_drain
    _last_drain = time.monotonic()
    with _lock:
        if not _queue:
            return
        batch = _queue[:]
        del _queue[:]
    for fn, args in batch:
        try:
            fn(*args)
        except Exception as ex:
            speech.log_line('pump: {} failed: {!r}'.format(
                getattr(fn, '__name__', fn), ex))


def start():
    """Arm the alarm on the current zone's wall clock (replacing any old one)."""
    global _handle, _owner, _last_drain
    stop()
    try:
        import alarms
        import clock
        _owner = _Owner()
        _handle = alarms.add_alarm_real_time(
            _owner, clock.interval_in_real_seconds(_INTERVAL_SECONDS), _drain,
            repeating=True)
        _last_drain = time.monotonic()
        speech.log_line('pump: started')
        try:
            import tyjokr_a11y_travel as travel
            travel.announce_setting()
            travel.start_lease()
        except Exception as ex:
            speech.log_line('pump: travel readiness start failed: {!r}'.format(ex))
        try:
            import tyjokr_a11y_build as build
            build.announce_controls()
        except Exception as ex:
            speech.log_line('pump: build controls notice failed: {!r}'.format(ex))
        try:
            import tyjokr_a11y_narrator as narrator
            narrator.push_simplified_menus()
        except Exception as ex:
            speech.log_line('pump: simplified menus notice failed: {!r}'.format(ex))
        try:
            import tyjokr_a11y_keys as keys
            keys.scanner_zone_started()
        except Exception as ex:
            speech.log_line('pump: scanner mode notice failed: {!r}'.format(ex))
        return True
    except Exception as ex:
        _handle = None
        speech.log_line('pump: start failed: {!r}'.format(ex))
        return False


def stop():
    global _handle
    if _handle is None:
        return
    try:
        import alarms
        alarms.cancel_alarm(_handle)
    except Exception:
        pass
    _handle = None
    with _lock:
        del _queue[:]
    try:
        import tyjokr_a11y_travel as travel
        travel.stop_lease()
    except Exception:
        pass


def status():
    if _handle is None:
        return 'not started'
    return 'alive' if alive() else 'stale'


def _install_zone_hook():
    import zone
    original = zone.Zone.on_loading_screen_animation_finished

    def a11y_pump_on_loading_screen_animation_finished(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        try:
            start()
        except Exception as ex:
            speech.log_line('pump: zone start failed: {!r}'.format(ex))
        return result

    zone.Zone.on_loading_screen_animation_finished = (
        a11y_pump_on_loading_screen_animation_finished)


try:
    _install_zone_hook()
except Exception as _zone_ex:
    speech.log_line('pump: zone hook install failed: {!r}'.format(_zone_ex))
