"""Screen-reader output through Prism, with configurable Windows speech fallback."""
import os
import threading
import time

try:
    import subprocess
except ImportError:
    subprocess = None


def _mods_folder():
    # __file__ lives inside the ts4script zip: <Mods>/TS4_Access.ts4script/...
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
LOG_PATH = os.path.join(MODS_FOLDER, 'TS4_Access.log')


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


def _prism_path():
    pack = 'TS4_Access_SpeechPack'
    candidates = [os.path.join(MODS_FOLDER, pack, 'prism.dll'),
                  os.path.join(MODS_FOLDER, 'prism.dll'),
                  os.path.join(_mods_root(), pack, 'prism.dll')]
    return next((p for p in candidates if os.path.isfile(p)), candidates[0])


PRISM_DLL_PATH = _prism_path()
_init_lock = threading.RLock()
_prism = None
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


def _try_init_prism():
    global _prism
    if not os.path.isfile(PRISM_DLL_PATH):
        return False
    try:
        from tyjokr_a11y_prism import Reader
        _prism = Reader(PRISM_DLL_PATH, log_line)
        log_line('Prism loaded from {}'.format(PRISM_DLL_PATH))
        return True
    except Exception as ex:
        log_line('Prism initialization failed: {!r}'.format(ex))
        return False


def has_braille():
    return bool(_prism is not None and _prism.has_braille())


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
        rate, volume, voice = 3, 70, 'zira'
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
    return os.path.isfile(PRISM_DLL_PATH)


def init():
    with _init_lock:
        return _init_locked()


def _init_locked():
    global _backend_name
    if _backend_name != 'uninitialized':
        return _backend_name
    if _try_init_prism():
        _backend_name = 'prism'
    elif _try_init_sapi():
        _backend_name = 'sapi'
    else:
        _backend_name = 'log-only'
    log_line('speech backend: {}'.format(_backend_name))
    if not speech_pack_installed():
        log_line('Prism speech pack missing; expected {}'.format(PRISM_DLL_PATH))
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
    if _prism is not None:
        try:
            _prism.stop()
        except Exception as ex:
            log_line('Prism stop failed: {!r}'.format(ex))
    # Always cancel any fallback that may still be speaking after a switch.
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
    with _init_lock:
        return _retry_screen_reader_locked()


def _retry_screen_reader_locked():
    global _backend_name
    if _prism is None and not _try_init_prism():
        return False
    _backend_name = 'prism'
    found = _prism.select(force=True)
    if found:
        restart_sapi()
    return found


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
    if _backend_name == 'prism' and _prism is not None:
        try:
            if _prism.output(text, _braille_text(text), braille_mode, interrupt):
                restart_sapi()
                return
        except Exception as ex:
            log_line('Prism output failed: {!r}'.format(ex))
    if braille_mode == 'only':
        return
    if _backend_name in ('prism', 'sapi') and _sapi_proc is None:
        # No available screen reader; use the configured Windows voice.
        _try_init_sapi()
    if _sapi_proc is not None:
        try:
            from urllib.parse import quote
            line = ('I' if interrupt else 'Q') + quote(text) + '\n'
            _sapi_proc.stdin.write(line.encode('ascii'))
            _sapi_proc.stdin.flush()
        except Exception as ex:
            log_line('SAPI speak failed: {!r}'.format(ex))
