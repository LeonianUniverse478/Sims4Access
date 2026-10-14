"""Speech output backends for the Screen Reader mod (Windows).

Backend priority, mirroring Tolk's own precedence:
  1. Tolk.dll if present -- routes to NVDA, JAWS, Window-Eyes, ZoomText,
     SuperNova, System Access. Requires a compiled Tolk.dll, which the Tolk
     repository does not ship (it is source only).
  2. NVDA controller client (nvdaControllerClient64.dll in the Mods folder).
  3. System Access (SAAPI64.dll in the Mods folder).
  4. Windows SAPI via a persistent hidden PowerShell child process -- always
     available, no setup, used for sighted testing.
  5. Log-only (no audio) if none are usable.

2 and 3 are the client DLLs Tolk itself loads, so shipping them gives most of
Tolk's coverage without needing to compile anything. macOS is not supported
yet: the input layer and these backends are Windows-only.

Every utterance is also appended to tyjokr_ScreenReader.log in the Mods
folder so behavior can be verified after a play session.
"""
import os
import threading
import time

try:
    import subprocess
except ImportError:
    subprocess = None


def _mods_folder():
    # __file__ lives inside the ts4script zip: <Mods>/tyjokr_ScreenReader.ts4script/...
    # The TS4 user folder name is localized, so never hardcode it; derive from
    # our own load path.
    path = os.path.normpath(__file__)
    lower = path.lower()
    marker = '.ts4script'
    if marker in lower:
        zip_path = path[:lower.index(marker) + len(marker)]
        return os.path.dirname(zip_path)
    return os.path.dirname(path)


MODS_FOLDER = _mods_folder()
LOG_PATH = os.path.join(MODS_FOLDER, 'tyjokr_ScreenReader.log')


def _mods_root():
    """The game's Mods folder itself. The speech pack is a SEPARATE download
    (CurseForge forbids DLL files), so users may extract it anywhere under
    Mods, not just into our folder. Walk up from our own load path to the
    directory literally named Mods; unlike the user folder name, "Mods" is
    not localized."""
    path = MODS_FOLDER
    for _ in range(8):
        if os.path.basename(path).lower() == 'mods':
            return path
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    return MODS_FOLDER


def _find_dlls(names):
    """Locate the screen-reader DLLs: name -> full path.

    Near locations first (the shipped layout: our speech subfolder, our
    folder root, any first-level subfolder, since users rename and reorganize
    freely). Anything still missing triggers ONE depth-capped walk of the
    whole Mods tree, so the pack works no matter where the user dropped it.
    The walk runs once at import and stops as soon as everything is found.
    Misses resolve to the shipped location so a11y.status can say where a
    file belongs."""
    found = {}
    # tyjokr_ScreenReader_SpeechPack is the shipped pack folder, named
    # after the download itself, and self-identifying if extracted loose at
    # the Mods root. The two earlier layouts (tyjokr_ScreenReader_speech,
    # plain speech/) stay accepted so old installs keep working.
    near = [os.path.join(MODS_FOLDER, 'tyjokr_ScreenReader_SpeechPack'),
            os.path.join(MODS_FOLDER, 'tyjokr_ScreenReader_speech'),
            os.path.join(MODS_FOLDER, 'speech'), MODS_FOLDER]
    try:
        near += [os.path.join(MODS_FOLDER, entry)
                 for entry in sorted(os.listdir(MODS_FOLDER))
                 if os.path.isdir(os.path.join(MODS_FOLDER, entry))]
    except OSError:
        pass
    for name in names:
        for base in near:
            candidate = os.path.join(base, name)
            if os.path.isfile(candidate):
                found[name] = candidate
                break
    wanted = {name.lower(): name for name in names if name not in found}
    if wanted:
        root = _mods_root()
        root_depth = os.path.normpath(root).count(os.sep)
        try:
            for folder, subdirs, files in os.walk(root):
                # Mods trees with heavy CC run to tens of thousands of
                # files; cap the depth and bail out on the last hit.
                if os.path.normpath(folder).count(os.sep) - root_depth >= 5:
                    subdirs[:] = []
                subdirs.sort()
                for filename in files:
                    name = wanted.pop(filename.lower(), None)
                    if name is not None:
                        found[name] = os.path.join(folder, filename)
                if not wanted:
                    break
        except OSError:
            pass
    for name in names:
        found.setdefault(name, os.path.join(
            MODS_FOLDER, 'tyjokr_ScreenReader_SpeechPack', name))
    return found


_DLLS = _find_dlls(('nvdaControllerClient64.dll', 'SAAPI64.dll', 'Tolk.dll'))
NVDA_DLL_PATH = _DLLS['nvdaControllerClient64.dll']
SA_DLL_PATH = _DLLS['SAAPI64.dll']
TOLK_DLL_PATH = _DLLS['Tolk.dll']

_tolk = None
_nvda = None
_sa = None
# Tolk loaded but no screen reader running: our own SAPI child speaks (it
# honors the a11y.voice settings; Tolk's internal SAPI fallback does not).
# No background polling: detection happens at startup and when a11y.reload
# calls retry_screen_reader().
_tolk_standby = False

# How braille output is handled when a braille display is present:
#   concise  speech gets the full text, braille gets the leading label
#   full     both get the full text
#   only     braille only, speech suppressed (deafblind users who do not
#            want audio at all)
#   off      speech only, no braille
braille_mode = 'concise'
_sapi_proc = None
_backend_name = 'uninitialized'
_last_text = None
_last_time = 0.0


# The cfg value rules logging (default off). This line remains as the
# compile.py --release transform target and as the last-ditch fallback if
# the settings module itself fails to import.
log_enabled = True

# NVDA-style speech modes: hover speaks everything as you point, manual
# captures silently for the read-current key, beeps replaces speech with a
# short tone, off is silent. All four persist via the settings file.
_VALID_MODES = ('hover', 'manual', 'beeps', 'off')
speech_mode = 'hover'

try:
    import tyjokr_a11y_settings as _settings
    log_enabled = bool(_settings.get('logging'))
    _stored_braille = str(_settings.get('braille_mode', braille_mode))
    if _stored_braille in ('concise', 'full', 'only', 'off'):
        braille_mode = _stored_braille
    _stored_mode = str(_settings.get('speech_mode', 'hover'))
    if _stored_mode in _VALID_MODES:
        speech_mode = _stored_mode
except Exception:
    pass


def log_line(message):
    if not log_enabled:
        return
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as handle:
            handle.write('[{}] {}\n'.format(time.strftime('%H:%M:%S'), message))
    except Exception:
        pass


def _try_init_tolk():
    """Tolk routes to whichever screen reader is running: NVDA, JAWS,
    Window-Eyes, ZoomText, SuperNova, System Access."""
    global _tolk, _tolk_standby
    if not os.path.isfile(TOLK_DLL_PATH):
        return False
    try:
        import ctypes
        dll = ctypes.WinDLL(TOLK_DLL_PATH)
        dll.Tolk_Load()
        dll.Tolk_Output.argtypes = [ctypes.c_wchar_p, ctypes.c_bool]
        dll.Tolk_Output.restype = ctypes.c_bool
        dll.Tolk_DetectScreenReader.restype = ctypes.c_wchar_p
        dll.Tolk_HasSpeech.restype = ctypes.c_bool
        dll.Tolk_HasBraille.restype = ctypes.c_bool
        dll.Tolk_Braille.argtypes = [ctypes.c_wchar_p]
        dll.Tolk_Braille.restype = ctypes.c_bool
        dll.Tolk_Speak.argtypes = [ctypes.c_wchar_p, ctypes.c_bool]
        dll.Tolk_Speak.restype = ctypes.c_bool
        reader = dll.Tolk_DetectScreenReader()
        if (not reader or reader == 'SAPI') and not dll.Tolk_HasBraille():
            # No real screen reader: Tolk would speak through ITS OWN SAPI
            # voice, which ignores the a11y.voice rate/volume/name settings.
            # Stand Tolk by and let our own SAPI child speak instead; the
            # standby poll in _speak_now hands back to Tolk if a screen
            # reader starts mid-session.
            _tolk = dll
            _tolk_standby = True
            log_line('Tolk loaded, no screen reader running; standing by '
                     '(own SAPI fallback speaks)')
            return False
        # Safety net if the reader crashes mid-session.
        dll.Tolk_TrySAPI(True)
        _tolk = dll
        log_line('Tolk loaded; screen reader: {}; speech: {}; braille: {}'.format(
            reader,
            'yes' if dll.Tolk_HasSpeech() else 'no',
            'yes' if dll.Tolk_HasBraille() else 'no'))
        return True
    except Exception as ex:
        log_line('Tolk backend init failed: {!r}'.format(ex))
        return False


def has_braille():
    if _tolk is None:
        return False
    try:
        return bool(_tolk.Tolk_HasBraille())
    except Exception:
        return False


def _braille_text(text):
    """Condense for a braille display, which typically shows ~40 cells.

    The leading segment is the label ("Fishing. 4" / "Dismiss"), which is what
    a braille reader wants; the trailing prose is what speech is good at.
    """
    if braille_mode == 'full':
        return text
    head = text.split('. ', 1)[0].strip()
    if not head:
        head = text
    if len(head) > 120:
        head = head[:120]
    return head


def _try_init_sa():
    """System Access / System Access To Go, via the SAAPI client DLL."""
    global _sa
    if not os.path.isfile(SA_DLL_PATH):
        return False
    try:
        import ctypes
        dll = ctypes.WinDLL(SA_DLL_PATH)
        dll.SA_SayW.argtypes = [ctypes.c_wchar_p]
        if not dll.SA_IsRunning():
            return False
        _sa = dll
        return True
    except Exception as ex:
        log_line('System Access backend init failed: {!r}'.format(ex))
        return False


def _try_init_nvda():
    global _nvda
    if not os.path.isfile(NVDA_DLL_PATH):
        return False
    try:
        import ctypes
        dll = ctypes.WinDLL(NVDA_DLL_PATH)
        if dll.nvdaController_testIfRunning() != 0:
            log_line('NVDA DLL present but NVDA is not running; will retry per utterance')
        _nvda = dll
        return True
    except Exception as ex:
        log_line('NVDA backend init failed: {!r}'.format(ex))
        return False


def _sapi_script():
    """SAPI child script, honoring the sapi_* options. Only affects the
    fallback voice; screen-reader users control voice/rate/volume in their
    own screen reader settings."""
    try:
        import tyjokr_a11y_settings as _s
        rate = max(-10, min(10, int(_s.get('sapi_rate'))))
        volume = max(0, min(100, int(_s.get('sapi_volume'))))
        voice = str(_s.get('sapi_voice') or '')
    except Exception:
        rate, volume, voice = 1, 70, 'zira'
    script = (
        "Add-Type -AssemblyName System.Speech; "
        "$sp = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$sp.Rate = {}; $sp.Volume = {}; ".format(rate, volume))
    if voice:
        # Case-insensitive partial match, so "david"/"zira"/"hazel" work
        # without the full "Microsoft ... Desktop" name.
        script += (
            "$want = '{}'.ToLower(); "
            "foreach($iv in $sp.GetInstalledVoices()) {{ "
            "if($iv.VoiceInfo.Name.ToLower().Contains($want)) {{ "
            "try {{ $sp.SelectVoice($iv.VoiceInfo.Name) }} catch {{}}; break }} }}; "
        ).format(voice.replace("'", "''"))
    script += (
        "while ($true) { "
        "$l = [Console]::In.ReadLine(); "
        "if ($null -eq $l) { break }; "
        "if ($l.Length -lt 1) { continue }; "
        "if ($l[0] -ne 'Q') { $sp.SpeakAsyncCancelAll() }; "
        "if ($l.Length -lt 2) { continue }; "
        "$t = [System.Uri]::UnescapeDataString($l.Substring(1)); "
        "[void]$sp.SpeakAsync($t) }")
    return script


def _try_init_sapi():
    global _sapi_proc
    if subprocess is None:
        return False
    try:
        CREATE_NO_WINDOW = 0x08000000
        _sapi_proc = subprocess.Popen(
            ['powershell', '-NoProfile', '-NonInteractive', '-Command', _sapi_script()],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW)
        return True
    except Exception as ex:
        log_line('SAPI backend init failed: {!r}'.format(ex))
        return False


def restart_sapi():
    """Apply changed sapi_* options: kill the child; the next utterance
    respawns it with fresh settings."""
    global _sapi_proc
    if _sapi_proc is not None:
        try:
            _sapi_proc.kill()
        except Exception:
            pass
        _sapi_proc = None


def list_voices():
    """Installed SAPI voice names (one-shot query, ~a second)."""
    if subprocess is None:
        return []
    try:
        out = subprocess.run(
            ['powershell', '-NoProfile', '-NonInteractive', '-Command',
             "Add-Type -AssemblyName System.Speech; "
             "(New-Object System.Speech.Synthesis.SpeechSynthesizer)"
             ".GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }"],
            capture_output=True, text=True, timeout=10,
            creationflags=0x08000000)
        return [line.strip() for line in out.stdout.splitlines() if line.strip()]
    except Exception as ex:
        log_line('voice list failed: {!r}'.format(ex))
        return []


def speech_pack_installed():
    """The speech pack (Tolk + NVDA + System Access client DLLs) ships as a
    separate download: CurseForge does not allow DLL files inside mods."""
    return any(os.path.isfile(path)
               for path in (TOLK_DLL_PATH, NVDA_DLL_PATH, SA_DLL_PATH))


def init():
    global _backend_name
    if _backend_name != 'uninitialized':
        return _backend_name
    # Same precedence Tolk uses: a running screen reader wins over plain TTS.
    if _try_init_tolk():
        _backend_name = 'tolk'
    elif _try_init_nvda():
        _backend_name = 'nvda'
    elif _try_init_sa():
        _backend_name = 'systemaccess'
    elif _try_init_sapi():
        _backend_name = 'sapi'
    else:
        _backend_name = 'log-only'
    log_line('speech backend: {}'.format(_backend_name))
    if not speech_pack_installed():
        log_line('speech pack not installed (no Tolk/NVDA/SA client DLLs); '
                 'expected e.g. {}'.format(TOLK_DLL_PATH))
    return _backend_name


def backend_name():
    return _backend_name


_MIN_GAP = 0.15
_last_accept_time = 0.0
_pending = {}
_pending_timer = None
_speech_lock = threading.Lock()
_FLUSH_ORDER = ('widget', 'tooltip', 'event')


_QUEUE_AFTER_WIDGET_WINDOW = 2.5
_last_source = None

_captured_text = None
_captured_time = 0.0
_last_beep = 0.0


def _segs(text):
    return [seg.strip() for seg in text.split('. ') if seg.strip()]


def _adds_nothing(new, old):
    """True when every segment of `new` already appears in `old`: new is a
    label-only repeat of a richer line about the same control (e.g. "Hunger"
    right after "Hunger. 80%": the motive bar posts its composed line and a
    generic hover announce of the same row can follow with just the title).
    Speaking or parking the bare label would only lose the richer text."""
    if not new or not old or new == old:
        return False
    old_segs = set(_segs(old))
    new_segs = _segs(new)
    return bool(new_segs) and all(seg in old_segs for seg in new_segs)


def _beep():
    """Short activity tone for beeps mode. Beep() blocks for its duration,
    so play it off-thread, throttled against hover bursts."""
    global _last_beep
    now = time.monotonic()
    if now - _last_beep < 0.12:
        return
    _last_beep = now

    def _play():
        try:
            import ctypes
            ctypes.windll.kernel32.Beep(1150, 45)
        except Exception:
            pass
    threading.Thread(target=_play, daemon=True).start()


def set_mode(mode):
    global speech_mode
    if mode not in _VALID_MODES:
        return False
    speech_mode = mode
    try:
        import tyjokr_a11y_settings as _s
        _s.set('speech_mode', mode)
    except Exception:
        pass
    log_line('speech mode -> {}'.format(mode))
    _speak_now({'hover': 'Speech on.', 'manual': 'Speech manual.',
                'beeps': 'Speech beeps.', 'off': 'Speech off.'}[mode],
               source='widget')
    return True


def cycle_mode():
    set_mode(_VALID_MODES[(_VALID_MODES.index(speech_mode) + 1) % len(_VALID_MODES)])


# Text the user has already HEARD: either spoken automatically (hover mode)
# or read out by the read-current key. Drives that key's read/stop toggle.
_last_repeated = None
_deferred_timer = None


def _cancel_deferred():
    global _deferred_timer
    timer = _deferred_timer
    _deferred_timer = None
    if timer is not None:
        try:
            timer.cancel()
        except Exception:
            pass


def speak_progressive(head, body, source='tooltip', delay=1.2, head_spoken=False):
    """Say the short head now and hold the long body back, so a pointer that
    is only passing through (the time/weather panel sits under the speed
    buttons) never dumps a wall of text. Anything else being said cancels the
    body; the read-current key still reads head and body together.

    head_spoken=True means the head was already announced as its own
    utterance (the time panel's widget line), so this call only sets the
    combined capture and schedules the body."""
    global _deferred_timer, _captured_text, _captured_time, _last_repeated
    if not head_spoken:
        speak(head, source=source)
    full = head if not body else head + '. ' + body
    _captured_text = full
    _captured_time = time.monotonic()
    if not body or speech_mode != 'hover':
        return          # other modes never auto-speak, so nothing to defer
    # The head is playing right now and the body is on its way, so the user
    # is hearing this capture: the read key must STOP. speak() armed the key
    # with the head alone, which broke the stop-equality and made the key
    # re-read the whole text, heard as "restarts the narration" (numpad-8
    # bug, fixed 2026-08-02).
    _last_repeated = full
    _cancel_deferred()
    timer = threading.Timer(delay, _flush_deferred, args=(body, source))
    timer.daemon = True
    _deferred_timer = timer
    timer.start()


def _flush_deferred(body, source):
    global _deferred_timer, _last_repeated
    _deferred_timer = None
    if speech_mode != 'hover':
        return
    _last_repeated = _captured_text     # heard in full: 8 now stops
    _speak_now(body, source)


# No backend exposes an is-speaking query, so track roughly how long the
# audio should last. Queued utterances (a tooltip parked behind a row label)
# start only once the previous one ends, so measuring from send time would
# call playback finished while it is still talking.
_SPEAK_RATE_CPS = 15.0
_busy_until = 0.0


def _note_utterance(text, interrupt):
    global _busy_until
    now = time.monotonic()
    start = now if interrupt else max(now, _busy_until)
    _busy_until = start + max(1.0, min(25.0, 0.6 + len(text) / _SPEAK_RATE_CPS))


def _probably_still_speaking():
    if _last_text is None:
        return False
    return time.monotonic() < _busy_until


def repeat_last():
    """The read-current key: stops speech that is still playing, otherwise
    reads what is under the pointer. The already-heard check alone made a
    press in SILENCE do a soundless "stop", so the key felt dead until a
    second press (tester report, fixed 2026-08-03)."""
    global _last_repeated
    _cancel_deferred()
    if speech_mode == 'off':
        return
    if not _captured_text:
        return
    if _last_repeated == _captured_text and _probably_still_speaking():
        stop()
        _last_repeated = None
        return
    _last_repeated = _captured_text
    init()
    _speak_now(_captured_text, source='widget')


def speak(text, interrupt=True, source='tooltip', explicit=False):
    """Speak text through the active backend, newest-wins under flood.

    Bursts of announcements (hover transitions, busy async UI) are thinned to
    one per _MIN_GAP seconds, but the LATEST utterance in a burst is the one
    that survives: it is parked and flushed a moment later, replacing anything
    older still waiting. The last thing hovered is always what gets spoken.

    Interrupt policy: widget labels always interrupt (newest hover wins); a
    tooltip that follows a recent widget label QUEUES behind it instead of
    cutting it off, so "Fishing. 4" finishes before the skill description.
    """
    global _pending_timer, _last_accept_time, _captured_text, _last_repeated
    global _captured_time
    if not text:
        return
    init()
    _cancel_deferred()   # a new utterance drops any held-back tooltip body
    now = time.monotonic()
    if not explicit:
        # Command confirmations are not "what the pointer is on", so they
        # never become the capture the read-current key repeats. A bare
        # label re-announcing a fresh richer capture of the same control
        # keeps the richer line for the read key.
        keep_richer = (_captured_text is not None
                       and now - _captured_time < _QUEUE_AFTER_WIDGET_WINDOW
                       and _adds_nothing(text, _captured_text))
        if not keep_richer:
            if text != _captured_text:
                _last_repeated = None   # new capture re-arms the read key
            _captured_text = text
        _captured_time = now
    # Speech modes: automatic narration is suppressed in manual (captured
    # for the read-current key), replaced by a tone in beeps, silenced in
    # off. Explicit speech (command feedback, read-current) always talks.
    # Deafblind exception: in braille-only mode the braille stream keeps
    # flowing regardless of speech mode.
    if (not explicit and speech_mode != 'hover'
            and not (braille_mode == 'only' and has_braille())):
        log_line('CAPTURE[{}/{}]: {}'.format(speech_mode, source[0], text))
        if speech_mode == 'beeps':
            _beep()
        return
    if explicit:
        # The user asked for this utterance directly: skip burst-thinning,
        # and drop anything parked so a stale hover can't talk over it.
        with _speech_lock:
            _pending.clear()
            _last_accept_time = time.monotonic()
        _speak_now(text, source)
        return
    # About to be spoken automatically, so the user is hearing it: the
    # read-current key becomes a stop key until something new is captured.
    with _speech_lock:
        gap = now - _last_accept_time
        if gap < _MIN_GAP:
            # Park newest per channel: a description can never evict its own
            # (or the next) label; a new label evicts a stale description.
            if source == 'widget':
                _pending.pop('tooltip', None)
                parked = _pending.get('widget')
                if parked is not None and _adds_nothing(text, parked):
                    # A bare label must not evict the richer parked line for
                    # the same control ("Fishing" evicting "Fishing. 4"
                    # under newest-wins ate the level read, 2026-08-02).
                    text = parked
            _pending[source] = text
            _last_repeated = text
            if _pending_timer is None or not _pending_timer.is_alive():
                _pending_timer = threading.Timer(_MIN_GAP - gap, _flush_pending)
                _pending_timer.daemon = True
                _pending_timer.start()
            return
        _last_accept_time = now
        if source == 'widget':
            _pending.pop('tooltip', None)
    _last_repeated = text
    _speak_now(text, source)


def _flush_pending():
    global _last_accept_time
    with _speech_lock:
        items = [(src, _pending.pop(src)) for src in _FLUSH_ORDER if src in _pending]
        _pending.clear()
        _last_accept_time = time.monotonic()
    for src, text in items:
        _speak_now(text, src)


def stop():
    """Cut off current and queued speech immediately."""
    global _last_text, _last_time, _last_source, _pending, _busy_until
    init()
    _cancel_deferred()
    with _speech_lock:
        _pending.clear()
    now = time.monotonic()
    _last_text = None
    _last_time = now
    _last_source = 'widget'
    _busy_until = 0.0
    # Silence whichever backend is ACTUALLY producing audio. Claiming a
    # backend is not the same as that backend speaking: the NVDA client DLL
    # always loads (so NVDA starting mid-session works), but with NVDA not
    # running every utterance falls through to the SAPI child. stop() used
    # to fire nvdaController_cancelSpeech and return unconditionally, so it
    # silenced nothing while SAPI kept talking; the read key looked dead
    # and the next press restarted the text ("needs two presses", fixed
    # 2026-08-03). Mirror _speak_now: only stop here if the call reports
    # success, and always fall through to SAPI otherwise.
    if _backend_name == 'tolk' and _tolk is not None:
        try:
            if _tolk.Tolk_Silence():
                return
        except Exception as ex:
            log_line('Tolk stop failed: {!r}'.format(ex))
    if _backend_name == 'systemaccess' and _sa is not None:
        try:
            if _sa.SA_IsRunning():
                _sa.SA_StopAudio()
                return
        except Exception as ex:
            log_line('System Access stop failed: {!r}'.format(ex))
    if _backend_name == 'nvda' and _nvda is not None:
        try:
            # Returns an error code rather than raising; nonzero means NVDA
            # is not running and something else is speaking.
            if _nvda.nvdaController_cancelSpeech() == 0:
                return
        except Exception as ex:
            log_line('NVDA stop failed: {!r}'.format(ex))
    if _sapi_proc is not None:
        try:
            _sapi_proc.stdin.write(b'I\n')
            _sapi_proc.stdin.flush()
        except Exception as ex:
            log_line('SAPI stop failed: {!r}'.format(ex))


def request_hush(grace=0.8):
    """A textless control was touched (Flash fell back to a derived name or
    an outright stop). Silence stale speech, but never cut down a widget
    line that just started: entering a row often crosses its icon-only
    children, and their empty announce used to kill the row's own label
    mid-word (part of the skills/needs "title, then level" regression,
    2026-08-02)."""
    now = time.monotonic()
    with _speech_lock:
        if _pending.get('widget') is not None:
            return
    if (_last_source == 'widget' and _last_text is not None
            and (now - _last_time) < grace):
        return
    stop()


def retry_screen_reader():
    """Hand speech to Tolk if a screen reader is running now. Called from
    a11y.reload only; there is deliberately no background polling."""
    global _backend_name, _tolk_standby
    if not _tolk_standby or _tolk is None:
        return False
    try:
        reader = _tolk.Tolk_DetectScreenReader()
        if reader and reader != 'SAPI':
            _tolk_standby = False
            _tolk.Tolk_TrySAPI(True)
            _backend_name = 'tolk'
            restart_sapi()
            log_line('screen reader "{}" now running; switched to Tolk'.format(reader))
            return True
    except Exception as ex:
        log_line('screen reader re-check failed: {!r}'.format(ex))
    return False


_CAPTION_MAX_CHARS = 480


def _send_caption(text):
    """Simulation thread only; recheck the toggle for queued utterances."""
    import tyjokr_a11y_settings as settings
    if text and not settings.get('captions', False):
        return
    import distributor.ops
    import distributor.system
    # Same UTF-8 percent encoding as Flash encodeURIComponent. Escape all
    # bytes outside the unreserved ASCII set, including pipes and percent.
    safe = b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~'
    encoded = ''.join(chr(byte) if byte in safe else '%{:02X}'.format(byte)
                      for byte in text.encode('utf-8', errors='replace'))
    op = distributor.ops.SendUIMessage('A11y|cap|' + encoded)
    distributor.system.Distributor.instance().add_op_with_no_owner(op)


def _post_caption(text):
    try:
        import tyjokr_a11y_settings as settings
        if text and not settings.get('captions', False):
            return
        import tyjokr_a11y_pump as pump
        if len(text) > _CAPTION_MAX_CHARS:
            text = text[:_CAPTION_MAX_CHARS - 1] + '\u2026'
        pump.post(_send_caption, text)
    except Exception as ex:
        log_line('caption: post failed: {!r}'.format(ex))


def clear_caption():
    _post_caption('')


def _tolk_output(text, interrupt):
    """Return success so a driver failure cannot silently discard speech."""
    if braille_mode == 'off' or not has_braille():
        return bool(_tolk.Tolk_Output(text, interrupt))
    brief = _braille_text(text)
    if braille_mode == 'only':
        _tolk.Tolk_Braille(brief)
        return True  # Deliberately silent; never force an audio fallback.
    if braille_mode == 'full':
        return bool(_tolk.Tolk_Output(text, interrupt))
    if not _tolk.Tolk_Speak(text, interrupt):
        return bool(_tolk.Tolk_Output(text, interrupt))
    _tolk.Tolk_Braille(brief)
    return True


def _speak_now(text, source='tooltip'):
    global _last_text, _last_time, _last_source, _last_repeated
    now = time.monotonic()
    if text == _last_text and (now - _last_time) < 1.0:
        return
    if (source == 'widget' and _last_source == 'widget' and _last_text
            and (now - _last_time) < _QUEUE_AFTER_WIDGET_WINDOW
            and _adds_nothing(text, _last_text)):
        # A bare label re-announcing the control whose richer line is still
        # playing ("Hunger" cutting off "Hunger. 80%"): information-free,
        # and widget-over-widget interrupts, so speaking it truncated the
        # level read (2026-08-02). Keep the read key armed on what is
        # actually being heard.
        _last_repeated = _last_text
        return
    if source == 'tooltip' and _last_text and (now - _last_time) < 4.0:
        # Cross-utterance dedupe: a tooltip often opens with the exact text
        # just spoken from the hovered control (e.g. a trait name). Strip
        # leading segments that were just heard.
        prev_segs = set(seg.strip() for seg in _last_text.split('. '))
        segs = [seg.strip() for seg in text.split('. ')]
        while segs and segs[0] in prev_segs:
            segs.pop(0)
        if not segs:
            return
        text = '. '.join(segs)
    interrupt = True
    if (source == 'tooltip' and _last_source == 'widget'
            and (now - _last_time) < _QUEUE_AFTER_WIDGET_WINDOW):
        interrupt = False
    if source == 'event':
        # Ambient narration (e.g. "what is my sim doing") never cuts off
        # whatever the player is actively reading.
        interrupt = False
    _last_text = text
    _last_time = now
    _last_source = source
    _note_utterance(text, interrupt)
    # After capture, thinning and dedupe: repeat/deferred speech also comes
    # through here, whereas text merely captured in manual/off never does.
    _post_caption(text)
    log_line('SPEAK[{}{}]: {}'.format(source[0], 'i' if interrupt else 'q', text))
    if _backend_name == 'tolk' and _tolk is not None:
        try:
            if _tolk_output(text, interrupt):
                return
            log_line('Tolk reported output failure; trying NVDA/Windows speech')
        except Exception as ex:
            log_line('Tolk speak failed: {!r}'.format(ex))
        if _nvda is None:
            _try_init_nvda()
    if _backend_name == 'systemaccess' and _sa is not None:
        try:
            if interrupt:
                _sa.SA_StopAudio()
            _sa.SA_SayW(text)
            return
        except Exception as ex:
            log_line('System Access speak failed: {!r}'.format(ex))
    if _backend_name in ('nvda', 'tolk') and _nvda is not None:
        try:
            if interrupt:
                _nvda.nvdaController_cancelSpeech()
            # The controller reports failure via return code, not exception;
            # nonzero means NVDA is not actually running, so fall through to
            # the SAPI child below instead of going silent.
            if _nvda.nvdaController_speakText(text) == 0:
                return
        except Exception as ex:
            log_line('NVDA speak failed: {!r}'.format(ex))
    if _backend_name in ('nvda', 'tolk', 'sapi') and _sapi_proc is None:
        # NVDA path broke at runtime; bring up SAPI as a live fallback.
        _try_init_sapi()
    if _sapi_proc is not None:
        try:
            from urllib.parse import quote
            line = ('I' if interrupt else 'Q') + quote(text) + '\n'
            _sapi_proc.stdin.write(line.encode('ascii'))
            _sapi_proc.stdin.flush()
        except Exception as ex:
            log_line('SAPI speak failed: {!r}'.format(ex))
