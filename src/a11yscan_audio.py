"""Why a notification made no sound.

Notification stings are not played by the client when the card appears. They
are played by the simulation, inside UiDialog.show_dialog, before the dialog is
ever sent:

    if self.audio_sting is not None:
        sting_owner = None
        if self.audio_sting_owner is not None:
            sting_owner = self._resolver.get_participant(self.audio_sting_owner)
            if sting_owner is not None and isinstance(sting_owner, SimInfo):
                sting_owner = sting_owner.get_sim_instance(
                    allow_hidden_flags=ALL_HIDDEN_REASONS)
        play_tunable_audio(self.audio_sting, owner=sting_owner)

The detail that matters is the last line. play_tunable_audio falls back to the
active Sim only when owner is DEFAULT - its own sentinel. An owner of None is
not DEFAULT, so it is passed straight through to PlaySound, which has no object
to attach the sound to and plays nothing. A Sim who is not instanced, or a
participant the resolver cannot fill in, therefore produces a notification you
can read and cannot hear.

So this module does two things:

  * Records every sting the game asks for - the resource key, who it was to
    play on, and whether that owner was real. If a sound goes missing, the log
    says whether the game even asked for it, which separates a tuning problem
    from a mod problem from an audio-device problem.
  * Substitutes the active Sim when the owner came through as None, which is
    what DEFAULT would have done, so the sound is heard.

play_tunable_audio is imported by value into a dozen modules
(`from audio.primitive import play_tunable_audio`), so patching audio.primitive
alone would miss every one of them. The patch walks sys.modules instead and
replaces the name wherever it is bound to the original function, which also
covers modules another mod imported.
"""
import a11yscan_log as logfile

MAX_RECORDS = 40

# Distinguishes "the caller left owner out" from "the caller passed None".
_OMITTED = object()

_installed = False
_original = None
_patched = []
_records = []
_missing_owner = 0
_error = None


def installed():
    return _installed


def status():
    if not _installed:
        return 'not installed{}'.format(
            ' ({})'.format(_error) if _error else '')
    return '{} modules watched, {} stings seen, {} played on nothing'.format(
        len(_patched), len(_records), _missing_owner)


def recent(limit=12):
    """The last stings the game asked for, newest last."""
    return list(_records[-limit:])


def _active_sim():
    try:
        import services
        client = services.client_manager().get_first_client()
        return getattr(client, 'active_sim', None) if client else None
    except Exception:
        return None


def _describe(owner):
    if owner is None:
        return 'nothing'
    for attr in ('first_name', 'full_name'):
        try:
            name = getattr(owner, attr, None)
            if name:
                return str(name)
        except Exception:
            continue
    try:
        return '{} {}'.format(type(owner).__name__, getattr(owner, 'id', ''))
    except Exception:
        return 'something'


def _sting_name(tunable):
    """The sting's resource key, or the closest thing to it."""
    for attr in ('audio', 'sound', 'key', 'resource_key'):
        try:
            value = getattr(tunable, attr, None)
            if value is not None:
                return str(value)
        except Exception:
            continue
    try:
        return type(tunable).__name__
    except Exception:
        return 'sting'


def _record(entry):
    _records.append(entry)
    if len(_records) > MAX_RECORDS:
        del _records[:len(_records) - MAX_RECORDS]


def _wrapper(tunable_play_audio, owner=_OMITTED):
    """Log the sting, and give it something to play on if it has nothing.

    A caller that leaves owner out must still get the game's own default, so
    the sentinel here is not None - None is a real value with a real meaning,
    and telling the two apart is the whole point.
    """
    global _missing_owner
    import time
    from singletons import DEFAULT
    if owner is _OMITTED:
        owner = DEFAULT
    substituted = False
    try:
        if owner is None:
            # None is not DEFAULT, so the game would hand PlaySound nothing to
            # attach to and the player would hear silence. DEFAULT's own answer
            # is the active Sim, so use it.
            replacement = _active_sim()
            if replacement is not None:
                owner = replacement
                substituted = True
                _missing_owner += 1
    except Exception as ex:
        logfile.write('audio: could not find a Sim to play on ({!r})'.format(ex))
    try:
        _record('{} sting {} on {}{}'.format(
            time.strftime('%H:%M:%S'), _sting_name(tunable_play_audio),
            _describe(owner), ', substituted' if substituted else ''))
        if substituted:
            logfile.write('audio: sting {} had no owner, playing it on {} '
                          'instead'.format(_sting_name(tunable_play_audio),
                                           _describe(owner)))
    except Exception:
        pass
    return _original(tunable_play_audio, owner=owner)


def install():
    """Watch every binding of play_tunable_audio there is."""
    global _installed, _original, _error
    if _installed:
        return True
    del _patched[:]
    try:
        import sys
        import audio.primitive as primitive
        original = getattr(primitive, 'play_tunable_audio', None)
        if original is None:
            _error = 'audio.primitive has no play_tunable_audio'
            logfile.write('audio: ' + _error)
            return False
        if getattr(original, '_a11yscan_wrapper', False):
            # A reload. The modules point at the PREVIOUS module's wrapper,
            # which carries the game's own function; take that back and patch
            # them onto this one, or every sting would be recorded into a
            # module nothing reads any more.
            original = getattr(original, '_a11yscan_original', None)
            if original is None:
                _error = 'a previous wrapper lost the original function'
                logfile.write('audio: ' + _error)
                return False
        _original = original
        _wrapper._a11yscan_wrapper = True
        _wrapper._a11yscan_original = original
        for name, module in list(sys.modules.items()):
            if module is None:
                continue
            try:
                bound = getattr(module, 'play_tunable_audio', None)
                # Either the game's own function, or a wrapper this mod left
                # behind on a previous load - both get pointed at this one.
                if bound is original or getattr(bound, '_a11yscan_wrapper',
                                                False):
                    setattr(module, 'play_tunable_audio', _wrapper)
                    _patched.append(name)
            except Exception:
                continue
        _installed = bool(_patched)
        logfile.write('audio: watching stings in {} modules ({})'.format(
            len(_patched), ', '.join(_patched[:6])))
        return _installed
    except Exception as ex:
        _error = repr(ex)
        logfile.write('audio: could not watch stings ({!r})'.format(ex))
        return False
