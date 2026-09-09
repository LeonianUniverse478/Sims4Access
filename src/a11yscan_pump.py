"""Bridge from the keyboard thread to the simulation thread.

The key poller runs on its own thread, but touching Sims, objects or the
interaction queue from there risks corrupting game state. So the poller only
drops an intent string into a queue, and a repeating real-time alarm drains
that queue on the simulation thread where it is safe to act.

If the alarm cannot be created we degrade to running intents directly on the
poller thread. That is not ideal, and a11y2.diag will say so.
"""
import threading
import time

import a11yscan_log as logfile
import a11yscan_narrate as narrate
import a11yscan_reload as reloader
import a11yscan_speech as speech
import a11yscan_state as state

# The game ticks at roughly 60Hz, so this is about as fine as a real-time
# alarm gets. At the old 0.1s every key press waited up to a tenth of a
# second before anything was even read, which is what made the mod feel
# sluggish - the speech was always immediate, the intent behind it was not.
_INTERVAL_SECONDS = 0.02

# Narration is a poll, not a response to a key, and does not need to run
# every tick now that the ticks are five times more frequent.
_NARRATE_SECONDS = 0.25
_last_narrate = 0.0

# A lock plus a list rather than queue.Queue. Not because queue is missing -
# a11y2.env settles what is actually importable - but because this needs so
# little that the dependency is not worth carrying.
_lock = threading.Lock()
_pending = []
_alarm_handle = None
_owner = None
_direct_mode = False
_generation = None
_last_drain = 0.0
# What the simulation thread is doing right now, if anything. An intent that
# never clears is a hang, and its name says which menu caused it.
_busy_intent = None
_busy_since = 0.0
_reload_requested = False
# When to pick up a newly installed build, if one has appeared.
_reload_soon = [0.0]

# The alarm fires every 0.1s, so silence far past that means it is dead.
_STALE_SECONDS = 5.0


class _Owner(object):
    """Alarms keep a reference to an owner; this is a stable one we control."""
    pass


def _zone_running():
    try:
        import services
        zone = services.current_zone()
        return zone is not None and zone.is_zone_running
    except Exception:
        return False


def _pump_is_stale():
    """Has the simulation stopped draining us?

    Leaving a lot for the main menu tears the zone down, but the alarm handle
    we created at zone load is still non-None, so post() went on queueing
    intents into a list nothing would ever drain again - the mod looked dead
    on the main menu after quitting a game, while the keyboard thread was
    still happily polling. Treat a long silence as the alarm being gone.
    """
    if _alarm_handle is None:
        return True
    return (time.monotonic() - _last_drain) > _STALE_SECONDS


def _go_direct():
    """Fall back to running intents on the key thread.

    Clearing the handle matters as much as the flag: start() returns early
    when a handle is set, so leaving it in place would stop the pump ever
    re-arming when the next lot loads.
    """
    global _direct_mode, _alarm_handle
    if _direct_mode and _alarm_handle is None:
        return
    _direct_mode = True
    _alarm_handle = None
    speech.log('pump went quiet; running intents on the key thread')


# Intents whose whole job is to speak something we already hold. They read no
# game state and change none, so making them wait for the simulation thread
# only adds delay.
INSTANT_INTENTS = frozenset(('repeat', 'help'))



def health():
    """What state the pump is in, for the keyboard thread's watchdog."""
    now = time.monotonic()
    busy_for = (now - _busy_since) if _busy_since else 0.0
    return {
        'armed': _alarm_handle is not None,
        'direct': _direct_mode,
        'silent_for': now - _last_drain if _last_drain else 0.0,
        'busy_intent': _busy_intent,
        'busy_for': busy_for,
        'zone': _zone_running(),
    }

def post(intent):
    """Called from the keyboard thread. Never touches game state."""
    if intent in INSTANT_INTENTS:
        try:
            state.dispatch(intent)
            return
        except Exception as ex:
            speech.log('instant intent {} failed ({!r})'.format(intent, ex))
    if _direct_mode or _pump_is_stale():
        # Before falling back, try to re-arm: a busy simulation thread can look
        # exactly like a dead alarm, and running game work on the key thread
        # stalls polling, which loses the presses that follow.
        if _zone_running() and start():
            try:
                with _lock:
                    _pending.append(intent)
                return
            except Exception:
                pass
        _go_direct()
        state.dispatch(intent)
        return
    try:
        with _lock:
            _pending.append(intent)
    except Exception as ex:
        speech.log('could not queue intent {} ({!r})'.format(intent, ex))


def begin_without_zone():
    """Run intents inline until a lot is loaded.

    The keyboard starts at game boot, but the real-time alarm needs a zone, and
    add_alarm_real_time will happily hand back a handle that never fires when
    there is no simulation behind it - which would silently queue every key
    press until a lot loaded. So before a zone exists we dispatch on the key
    thread instead. There is no simulation running to corrupt, and start()
    takes over with the alarm the moment a lot finishes loading.
    """
    global _direct_mode
    if _alarm_handle is None:
        _direct_mode = True
        speech.log('no zone yet; running intents on the key thread')


def _drain(_handle=None):
    global _last_drain
    _last_drain = time.monotonic()
    # A pump from a previous load must not keep running against stale modules.
    if _generation is not None and not reloader.is_current(_generation):
        try:
            stop()
        except Exception:
            pass
        return
    # Narration rides the same tick, but at its own slower rate: it is a poll
    # of the Sim's current action, not a response to anything, and running it
    # 50 times a second would spend real work to say nothing new.
    global _last_narrate
    now = time.monotonic()
    if now - _last_narrate >= _NARRATE_SECONDS:
        _last_narrate = now
        try:
            narrate.tick()
        except Exception as ex:
            speech.log('narrate failed ({!r})'.format(ex))
        # Riding the same slow tick: re-aiming the camera at the Sim being
        # followed, so positional audio stays centred as they move about.
        try:
            state.follow_tick()
        except Exception as ex:
            speech.log('follow failed ({!r})'.format(ex))
        # The autonomy hold is gone, but a hold left over from a previous
        # build must still be released - otherwise a Sim stays unable to act
        # and nothing is left running that would ever switch her back on.
        try:
            import a11yscan_actions as actions
            actions.autonomy_tick()
            actions.watch_tick()
        except Exception as ex:
            speech.log('autonomy tick failed ({!r})'.format(ex))
        # Asking visitors to leave only shows its result seconds later, so
        # the follow-up check rides this tick.
        try:
            import a11yscan_cheats as cheats
            cheats.tick()
        except Exception as ex:
            speech.log('cheats tick failed ({!r})'.format(ex))
        # An event you have to interrogate is an event you are not playing.
        try:
            import a11yscan_events as events
            events.watch_tick()
        except Exception as ex:
            speech.log('event watch failed ({!r})'.format(ex))
        try:
            import a11yscan_build as build
            build.watch_tick()
        except Exception as ex:
            speech.log('build watch failed ({!r})'.format(ex))
        # The keyboard thread is the only way into this mod. If it has
        # died there is nothing left to press a key with, so put it back.
        try:
            import a11yscan_keys as keys
            if not keys.alive():
                speech.log('watchdog: keyboard thread was gone, restarting it')
                keys.start()
        except Exception as ex:
            speech.log('watchdog: could not check the keyboard thread '
                       '({!r})'.format(ex))
        # Read the game's own string tables a few at a time, so objects
        # from a newly installed content mod get their real names without
        # anyone having to rebuild anything by hand.
        try:
            import a11yscan_strings as strings
            strings.tick()
        except Exception as ex:
            speech.log('string sweep failed ({!r})'.format(ex))
        # Catch dialog classes whose modules were imported after startup.
        try:
            import a11yscan_dialogs as dialogs
            dialogs.refresh_hooks()
        except Exception as ex:
            speech.log('dialog hook sweep failed ({!r})'.format(ex))
        # Load a newer build rather than asking for it. The warning worked -
        # it fired a minute before the last test - but a spoken notice in the
        # middle of everything else being read out is easy to miss, and a fix
        # that was never loaded looks exactly like a fix that does not work.
        # That has now cost four rounds of testing.
        try:
            if reloader.newer_build_waiting():
                speech.speak('A newer build of the scanner is installed. '
                             'Loading it now.')
                logfile.write('build: newer archive found, reloading on its own')
                _reload_soon[0] = time.monotonic() + 2.0
        except Exception:
            pass
        # Done a moment later, on a later tick: reloading from inside the
        # drain would tear down the alarm that is running this very call.
        try:
            if _reload_soon[0] and time.monotonic() >= _reload_soon[0]:
                _reload_soon[0] = 0.0
                speech.speak(reloader.reload_all())
        except Exception as ex:
            speech.log('automatic reload failed ({!r})'.format(ex))
    try:
        with _lock:
            batch = _pending[:]
            del _pending[:]
    except Exception as ex:
        speech.log('could not read intent queue ({!r})'.format(ex))
        return
    global _busy_intent, _busy_since
    for intent in batch:
        _busy_intent = intent
        _busy_since = time.monotonic()
        try:
            state.dispatch(intent)
        except Exception as ex:
            speech.log('dispatch failed ({!r})'.format(ex))
        finally:
            _busy_intent = None
            _busy_since = 0.0


def start():
    """Install the real-time alarm. Safe to call more than once."""
    global _alarm_handle, _owner, _direct_mode, _generation, _last_drain
    if _alarm_handle is not None:
        return True
    _generation = reloader.generation()
    _last_drain = time.monotonic()
    try:
        import alarms
        import clock
        _owner = _Owner()
        _alarm_handle = alarms.add_alarm_real_time(
            _owner,
            clock.interval_in_real_seconds(_INTERVAL_SECONDS),
            _drain,
            repeating=True)
        _direct_mode = False
        return True
    except Exception as ex:
        speech.log('real-time alarm unavailable ({!r}); running intents inline'.format(ex))
        _alarm_handle = None
        _direct_mode = True
        return False


def stop():
    global _alarm_handle
    if _alarm_handle is None:
        return
    try:
        import alarms
        alarms.cancel_alarm(_alarm_handle)
    except Exception as ex:
        speech.log('could not cancel alarm ({!r})'.format(ex))
    _alarm_handle = None


def status():
    if _alarm_handle is not None:
        return 'real-time alarm every {:g}s'.format(_INTERVAL_SECONDS)
    if _direct_mode:
        return 'INLINE on key thread (alarm unavailable)'
    return 'not started'
