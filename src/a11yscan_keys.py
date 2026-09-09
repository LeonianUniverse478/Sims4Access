"""Keyboard polling.

The game gives Python no key events, so like tyjokr's mod we poll Win32
GetAsyncKeyState from a daemon thread and gate on the game window being in the
foreground. Note that polling reads key state, it does not swallow it, so every
binding is behind Control+Alt to keep the bare arrows free for the camera.

ctypes is not shipped by the game; it comes from tyjokr's archive being on
sys.path. If that mod is not installed, keyboard support turns itself off.
"""
import threading
import time

import a11yscan_pump as pump
import a11yscan_reload as reloader
import a11yscan_speech as speech

VK_BACK = 0x08
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_RETURN = 0x0D
VK_F5 = 0x74
VK_HOME = 0x24
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28

CTRL_ALT = 'ctrl_alt'
CTRL_SHIFT = 'ctrl_shift'
BARE = 'bare'

# (vk, modifier) -> (intent, repeats_when_held)
BINDINGS = {
    (VK_LEFT, CTRL_ALT): ('prev_category', True),
    (VK_RIGHT, CTRL_ALT): ('next_category', True),
    (VK_UP, CTRL_ALT): ('prev_item', True),
    (VK_DOWN, CTRL_ALT): ('next_item', True),
    (VK_RETURN, CTRL_ALT): ('activate', False),
    (VK_BACK, CTRL_ALT): ('back', False),
    (0x52, CTRL_ALT): ('repeat', False),
    (0x53, CTRL_ALT): ('rescan', False),
    (0x57, CTRL_ALT): ('where', False),
    (0x48, CTRL_ALT): ('help', False),
    (0x46, CTRL_ALT): ('focus_self', False),
    # Needs is Ctrl+SHIFT+N, not Ctrl+Alt+N: the latter is the Windows
    # shortcut that starts NVDA, so the mod would have been fighting the
    # screen reader for it. Same letter, so the mnemonic survives.
    (0x4E, CTRL_SHIFT): ('needs', False),
    # D for delete: sell whatever the scanner is focused on. Two presses,
    # because it cannot be undone.
    (0x44, CTRL_SHIFT): ('sell_focused', False),
    # O for objectives: the aspiration and the goals still outstanding.
    # Ctrl+Alt+A is already the current action, and Ctrl+Shift+A answers the
    # phone, so the obvious letter was taken twice over.
    (0x4F, CTRL_SHIFT): ('aspiration', False),
    (0x41, CTRL_ALT): ('doing', False),
    (0x44, CTRL_ALT): ('focus_dialog', False),
    (0x50, CTRL_ALT): ('focus_phone', False),
    (0x49, CTRL_ALT): ('focus_inventory', False),
    (0x43, CTRL_ALT): ('focus_contacts', False),
    (0x54, CTRL_ALT): ('narrate', False),
    (0x47, CTRL_ALT): ('wants', False),
    (0x58, CTRL_ALT): ('dismiss_dialog', False),
    (0x45, CTRL_ALT): ('emotion', False),
    (VK_HOME, CTRL_ALT): ('go_home', False),
    (VK_F5, CTRL_ALT): ('reload', False),
    # The map-picker route, which actually travels. Pushing
    # TravelSuperInteraction directly does not: it is appended and immediately
    # reset ("Interaction finished during append", FinishingType.RESET). The
    # map view is now closed for us once the destination is chosen.
    (VK_HOME, CTRL_SHIFT): ('travel_menu', False),
    # T for travel: the direct route, which never opens the map. Kept beside
    # the map-picker route rather than replacing it - if this one refuses,
    # the old way still works, and being unable to travel at all is worse
    # than a screen that will not close.
    (0x54, CTRL_SHIFT): ('travel_open', False),
    # H for house: moving home is the one lot job with no dialog behind it,
    # so the mod offers the list itself.
    (0x48, CTRL_SHIFT): ('move_house', False),
    # P for plan: the event planner is a client screen with no dialog behind
    # it, so the mod builds the whole flow itself.
    (0x50, CTRL_SHIFT): ('events_open', False),
    # Answering a call is time-critical, so it gets its own chord rather than
    # making you navigate to the dialog first. Deliberately NOT Ctrl+Shift+
    # Enter: that is the game's own centre-the-lot shortcut, and doubling up
    # made every camera recentre announce "Nothing waiting".
    (0x41, CTRL_SHIFT): ('answer_call', False),
    # Ctrl+Shift+Enter matches the game's own centre-the-lot shortcut on
    # purpose. Both fire and both centre the lot, so they agree; ours also
    # stops the follow camera, which would otherwise drag the view back to the
    # Sim on the very next tick and make centring look broken.
    (VK_RETURN, CTRL_SHIFT): ('center_lot', False),
    (VK_BACK, CTRL_SHIFT): ('decline_call', False),
    (0x42, CTRL_ALT): ('grid_toggle', False),
    (0x4B, CTRL_ALT): ('catalog_open', False),
    (0x5A, CTRL_ALT): ('build_undo', False),
    # M for 'make a Sim': the keyboard Create-a-Sim, which replaces the CAS
    # screen rather than trying to read it.
    (0x4D, CTRL_ALT): ('cas_open', False),
    # Q for query: what the game will let us touch from here.
    (0x51, CTRL_ALT): ('probe', False),
    # L for look: change how the selected Sim looks.
    (0x4C, CTRL_ALT): ('look_open', False),
    # O for open: choose a save on the main menu, a household in game.
    (0x4F, CTRL_ALT): ('pick_open', False),
    # J for job: the career screen is client-side, so we build our own.
    (0x4A, CTRL_ALT): ('jobs_open', False),
    # V for cheats: skills, money, needs, promotions, in one menu.
    (0x56, CTRL_ALT): ('cheats_open', False),
    # Saving is the difference between a new Sim existing and not.
    (0x53, CTRL_SHIFT): ('save_now', False),
    (0x4D, CTRL_SHIFT): ('funds', False),
    (0x46, CTRL_SHIFT): ('follow_toggle', False),
    (0x47, CTRL_SHIFT): ('settings_open', False),
    (0x4C, CTRL_SHIFT): ('look_random', False),
    (0x52, CTRL_SHIFT): ('relations_open', False),
    # Number keys pick a household Sim directly, matching the numbering
    # a11y2.who reads out. Cycling would mean counting presses.
    (0x31, CTRL_ALT): ('play_1', False),
    (0x32, CTRL_ALT): ('play_2', False),
    (0x33, CTRL_ALT): ('play_3', False),
    (0x34, CTRL_ALT): ('play_4', False),
    (0x35, CTRL_ALT): ('play_5', False),
    (0x36, CTRL_ALT): ('play_6', False),
    (0x37, CTRL_ALT): ('play_7', False),
    (0x38, CTRL_ALT): ('play_8', False),
    # Bare arrows, and only while the grid is on: no chords to
    # remember while mapping a room.
    (VK_UP, BARE): ('grid_north', True),
    (VK_DOWN, BARE): ('grid_south', True),
    (VK_RIGHT, BARE): ('grid_east', True),
    (VK_LEFT, BARE): ('grid_west', True),
    (VK_RETURN, BARE): ('grid_describe', False),
    (VK_BACK, BARE): ('grid_toggle', False),
    (0x21, BARE): ('grid_up', False),
    (0x22, BARE): ('grid_down', False),
}

KEY_NAMES = {
    VK_LEFT: 'left arrow', VK_RIGHT: 'right arrow', VK_UP: 'up arrow',
    VK_DOWN: 'down arrow', VK_RETURN: 'enter', VK_BACK: 'backspace',
    0x52: 'R', 0x53: 'S', 0x57: 'W', 0x48: 'H', 0x46: 'F', 0x4E: 'N',
    0x41: 'A', 0x44: 'D', 0x50: 'P', 0x49: 'I', 0x43: 'C', 0x54: 'T',
    0x47: 'G', 0x58: 'X', 0x45: 'E', VK_HOME: 'home', VK_F5: 'F5',
    0x42: 'B', 0x21: 'page up', 0x22: 'page down', 0x4B: 'K', 0x5A: 'Z',
    0x4D: 'M',
    0x51: 'Q',
    0x4C: 'L',
    0x4F: 'O',
    0x4A: 'J',
    0x56: 'V',
    0x31: '1',
    0x32: '2',
    0x33: '3',
    0x34: '4',
    0x35: '5',
    0x36: '6',
    0x37: '7',
    0x38: '8',
}

MOD_NAMES = {CTRL_ALT: 'Ctrl+Alt', CTRL_SHIFT: 'Ctrl+Shift', BARE: 'grid'}

_POLL_SECONDS = 0.015
_REPEAT_DELAY = 0.45
_REPEAT_INTERVAL = 0.12

# Every distinct key we bind, so each poll can read and clear them all.
_ALL_VKS = sorted({vk for (vk, _mod) in BINDINGS})

_thread = None
_running = False
_enabled = True
_error = None
_user32 = None
_kernel32 = None


# Windows virtual key -> macOS virtual key. The two are unrelated numbering
# schemes, so every key the mod binds needs an entry here to work on a Mac.
MAC_KEYS = {
    0x41: 0,   0x42: 11,  0x43: 8,   0x44: 2,   0x45: 14,  0x46: 3,
    0x47: 5,   0x48: 4,   0x49: 34,  0x4A: 38,  0x4B: 40,  0x4C: 37,
    0x4D: 46,  0x4E: 45,  0x4F: 31,  0x50: 35,  0x51: 12,  0x52: 15,
    0x53: 1,   0x54: 17,  0x55: 32,  0x56: 9,   0x57: 13,  0x58: 7,
    0x59: 16,  0x5A: 6,
    0x31: 18,  0x32: 19,  0x33: 20,  0x34: 21,
    0x35: 23,  0x36: 22,  0x37: 26,  0x38: 28,
    0x0D: 36,  0x08: 51,  0x20: 49,  0x24: 115,
    0x21: 116, 0x22: 121, 0x74: 96,
    0x25: 123, 0x27: 124, 0x28: 125, 0x26: 126,
    0x11: 59,  0x12: 58,  0x10: 56,          # control, option, shift
}

# kCGEventSourceStateHIDSystemState - the physical keyboard, which is what
# GetAsyncKeyState reports too.
_HID_STATE = 1
_quartz = None
# Last poll's key state, for reconstructing presses where there is no latch.
_was_down = {}


def is_windows():
    import sys
    return getattr(sys, 'platform', '') == 'win32'


def _load_mac():
    """CoreGraphics, for key state. Needs Accessibility permission."""
    global _quartz, _error
    if _quartz is not None:
        return True
    try:
        import ctypes
        _quartz = ctypes.CDLL(
            '/System/Library/Frameworks/ApplicationServices.framework'
            '/ApplicationServices')
        _quartz.CGEventSourceKeyState.argtypes = [ctypes.c_int,
                                                  ctypes.c_uint16]
        _quartz.CGEventSourceKeyState.restype = ctypes.c_bool
        speech.log('keyboard: using CoreGraphics. The game needs Accessibility '
                   'permission in System Settings, Privacy and Security, or no '
                   'key will register.')
        missing = [hex(vk) for vk in _bound_keys() if vk not in MAC_KEYS]
        if missing:
            speech.log('keyboard: {} bound keys have no Mac code: {}'.format(
                len(missing), ', '.join(missing)))
        return True
    except Exception as ex:
        _error = repr(ex)
        speech.log('keyboard: CoreGraphics unavailable ({!r})'.format(ex))
        return False


def _bound_keys():
    seen = set()
    for vk, _mod in BINDINGS:
        seen.add(vk)
    return sorted(seen)


def _down_mac(vk):
    code = MAC_KEYS.get(vk)
    if code is None or _quartz is None:
        return False
    try:
        return bool(_quartz.CGEventSourceKeyState(_HID_STATE, code))
    except Exception:
        return False


def _load():
    global _user32, _kernel32, _error
    if not is_windows():
        return _load_mac()
    if _user32 is not None:
        return True
    try:
        import ctypes
        _user32 = ctypes.WinDLL('user32', use_last_error=True)
        _kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        return True
    except Exception as ex:
        _error = repr(ex)
        speech.log('ctypes unavailable ({!r}); keyboard off'.format(ex))
        return False


def _game_has_focus():
    if not is_windows():
        # No cheap CoreGraphics equivalent of "is my process frontmost". The
        # cost of assuming focus is that chords still fire while alt-tabbed;
        # the cost of assuming the opposite would be a mod that never
        # responds at all.
        return True
    try:
        import ctypes
        hwnd = _user32.GetForegroundWindow()
        if not hwnd:
            return False
        pid = ctypes.c_ulong(0)
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value == _kernel32.GetCurrentProcessId()
    except Exception:
        return False


def _down(vk):
    if not is_windows():
        return _down_mac(vk)
    return bool(_user32.GetAsyncKeyState(vk) & 0x8000)


def _read_all():
    """One GetAsyncKeyState per bound key, per poll.

    The high bit says a key is down RIGHT NOW; the low bit latches "pressed
    since you last asked". Reading only the high bit misses any tap that starts
    and ends between two polls - and this thread shares the GIL with the
    simulation, so when the game is busy the gap between polls is far longer
    than the sleep suggests. That is why keys needed pressing twice.

    Every bound key is read every poll, even ones under a different modifier,
    because the latch is cleared by reading: leaving a key unread lets a stale
    press sit there and fire later under the wrong chord.
    """
    state = {}
    if not is_windows():
        # CoreGraphics answers "down now" and has no latch, so a tap entirely
        # between two polls is lost. The rising edge is reconstructed here
        # instead: down now and not down last time counts as a press. Not as
        # good as the hardware latch, but it is the same information the
        # latch was standing in for.
        for vk in _ALL_VKS:
            down = _down_mac(vk)
            state[vk] = (down, down and not _was_down.get(vk, False))
            _was_down[vk] = down
        return state
    for vk in _ALL_VKS:
        try:
            value = _user32.GetAsyncKeyState(vk)
        except Exception:
            value = 0
        state[vk] = (bool(value & 0x8000), bool(value & 0x0001))
    return state


def _grid_on():
    try:
        import a11yscan_state as state
        return state.grid_active()
    except Exception:
        return False


def _type_now(intent):
    """Handle a typed key on this thread instead of queueing it.

    The pump exists to keep game state off the key thread, and every other
    intent needs it. Typing does not: it appends to a string in a11yscan_cas
    and speaks a letter through the NVDA client, neither of which touches the
    simulation. Going through the queue meant each character waited for the
    next alarm tick - up to a tenth of a second, and longer whenever the sim
    thread was busy - which is what made typing feel laggy.
    """
    try:
        import a11yscan_state as state
        state.type_key(intent)
    except Exception as ex:
        speech.log('typing failed ({!r})'.format(ex))


# When to synthesise an Escape, as a monotonic deadline. Zero means never.
_escape_at = [0.0]


def request_escape(delay=1.5):
    """Ask for an Escape keystroke shortly from now.

    The map view is a client panel. Answering its dialog satisfies the server
    and the client keeps the map on screen regardless - responses were sent and
    ignored. Nothing server-side reaches it, so the only way to put it away is
    to press the key a player would press.

    Delayed, because the travel has to commit first: sending Escape the instant
    the destination is chosen risks cancelling the very thing we just started.
    """
    _escape_at[0] = time.monotonic() + delay
    speech.log('escape requested in {:.1f}s'.format(delay))


def _tick_escape():
    """Send the pending Escape once its moment arrives."""
    if not _escape_at[0] or time.monotonic() < _escape_at[0]:
        return
    _escape_at[0] = 0.0
    if not _load() or not _game_has_focus():
        speech.log('escape skipped: game not focused')
        return
    if _send_escape():
        speech.log('escape sent to close the client panel')
    else:
        speech.log('escape could not be sent')


# Escape's scan code. The Sims 4 reads the keyboard through raw input, which
# looks at SCAN codes and ignores the virtual key - so a synthetic press with
# scan code 0, which is what keybd_event was being handed, was invisible to
# the game. That is why the map screen never closed.
SCAN_ESCAPE = 0x01
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
INPUT_KEYBOARD = 1


def _input_types():
    import ctypes

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [('wVk', ctypes.c_ushort),
                    ('wScan', ctypes.c_ushort),
                    ('dwFlags', ctypes.c_ulong),
                    ('time', ctypes.c_ulong),
                    ('dwExtraInfo', ctypes.c_void_p)]

    class INPUTUNION(ctypes.Union):
        # The union has to be as big as its LARGEST member, which is
        # MOUSEINPUT at 32 bytes on 64-bit - not KEYBDINPUT at 24. Sizing it
        # to the keyboard struct made INPUT 32 bytes instead of 40, and
        # SendInput rejects the whole call when cbSize does not match what it
        # expects. That is why it inserted 0 of 2 and the scan code never got
        # a chance to matter.
        _fields_ = [('ki', KEYBDINPUT), ('padding', ctypes.c_byte * 32)]

    class INPUT(ctypes.Structure):
        _fields_ = [('type', ctypes.c_ulong), ('u', INPUTUNION)]

    return ctypes, INPUT, KEYBDINPUT


# Scan codes for the keys we may need to synthesize. The game reads scan
# codes, not virtual keys, which is why a keybd_event with scan code 0 was
# invisible to it.
SCAN_F2 = 0x3C


def send_scan(scan, label='key'):
    """Press and release a key by scan code, the way the hardware would.

    Kept honest about the precedent: a synthesized Escape was tried for the map
    screen and the game ignored it. Mode switches may go through a different
    path than panel dismissal, so this is worth one try - but if it does
    nothing, that is the expected result rather than a bug to chase.
    """
    try:
        ctypes, INPUT, KEYBDINPUT = _input_types()
    except Exception as ex:
        speech.log('{}: no ctypes structures ({!r})'.format(label, ex))
        return False
    try:
        events = (INPUT * 2)()
        for index, extra_flag in enumerate((0, KEYEVENTF_KEYUP)):
            events[index].type = INPUT_KEYBOARD
            events[index].u.ki = KEYBDINPUT(
                0, scan, KEYEVENTF_SCANCODE | extra_flag, 0, None)
        size = ctypes.sizeof(INPUT)
        sent = _user32.SendInput(2, ctypes.byref(events), size)
        speech.log('{}: SendInput inserted {} of 2 events (cbSize {})'.format(
            label, sent, size))
        if sent:
            return True
        try:
            speech.log('{}: Windows refused it, error {}'.format(
                label, ctypes.get_last_error()))
        except Exception:
            pass
        return False
    except Exception as ex:
        speech.log('{}: SendInput raised {!r}'.format(label, ex))
        return False


def press_f2():
    """Ask Windows to press F2 for us, for when the real key never arrives."""
    return send_scan(SCAN_F2, 'F2')


def _send_escape():
    """Press and release Escape the way the hardware would.

    SendInput with KEYEVENTF_SCANCODE, because the scan code is the part the
    game actually reads. keybd_event is kept as a second attempt, but with a
    real scan code this time rather than zero.

    SendInput returns how many events it managed to insert, so a zero here is
    a genuine failure rather than a guess - worth logging, since silence was
    exactly the problem before.
    """
    try:
        ctypes, INPUT, KEYBDINPUT = _input_types()
    except Exception as ex:
        speech.log('escape: no ctypes structures ({!r})'.format(ex))
        return False

    try:
        events = (INPUT * 2)()
        for index, extra_flag in enumerate((0, KEYEVENTF_KEYUP)):
            events[index].type = INPUT_KEYBOARD
            events[index].u.ki = KEYBDINPUT(
                0, SCAN_ESCAPE, KEYEVENTF_SCANCODE | extra_flag, 0, None)
        size = ctypes.sizeof(INPUT)
        sent = _user32.SendInput(2, ctypes.byref(events), size)
        if sent:
            speech.log('escape: SendInput inserted {} of 2 events '
                       '(cbSize {})'.format(sent, size))
            return True
        # Zero means Windows refused it. The reason is worth having: 5 is
        # access denied, 87 is a malformed call.
        try:
            reason = ctypes.get_last_error()
        except Exception:
            reason = '?'
        speech.log('escape: SendInput refused everything, cbSize {} '
                   'error {}'.format(size, reason))
    except Exception as ex:
        speech.log('escape: SendInput failed ({!r})'.format(ex))

    try:
        # Same idea through the older call, and this time the scan code is
        # filled in - it was the zero that made this invisible.
        _user32.keybd_event(VK_ESCAPE, SCAN_ESCAPE, 0, 0)
        _user32.keybd_event(VK_ESCAPE, SCAN_ESCAPE, KEYEVENTF_KEYUP, 0)
        speech.log('escape: sent via keybd_event with a real scan code')
        return True
    except Exception as ex:
        speech.log('escape: keybd_event failed ({!r})'.format(ex))
    return False


def _typing_on():
    try:
        import a11yscan_state as state
        return state.typing_active()
    except Exception:
        return False


# Letters, digits, space, and the three keys that finish or undo.
_TYPING_KEYS = ([(vk, chr(vk)) for vk in range(0x41, 0x5B)]
                + [(vk, chr(vk)) for vk in range(0x30, 0x3A)]
                + [(VK_SPACE, 'SPACE')])


def _poll_typing(held, now):
    """Collect typed characters while a name is being entered.

    Polling cannot swallow keys, so the game still sees them - but nothing here
    is held with Control or Alt, and bare letters only nudge the camera, which
    Control Shift Enter recentres. That is a smaller price than not being able
    to type your own Sim's name.
    """
    if _down(VK_CONTROL) or _down(VK_MENU):
        return
    shifted = _down(VK_SHIFT)
    for vk, char in _TYPING_KEYS:
        key = ('type', vk)
        if not _down(vk):
            held.pop(key, None)
            continue
        if key in held:
            continue
        held[key] = now
        if char == 'SPACE':
            _type_now('type_char_SPACE')
        elif char.isalpha():
            _type_now('type_char_' + (char if shifted else char.lower()))
        else:
            _type_now('type_char_' + char)
    for vk, intent in ((VK_BACK, 'type_back'), (VK_RETURN, 'type_done'),
                       (VK_ESCAPE, 'type_cancel')):
        key = ('type', vk)
        if not _down(vk):
            held.pop(key, None)
            continue
        if key in held:
            continue
        held[key] = now
        _type_now(intent)


def _active_modifier():
    """Exactly one chord at a time: Ctrl+Alt and Ctrl+Shift must not overlap."""
    if not _down(VK_CONTROL):
        # Unmodified keys drive the grid, and only while the grid is on.
        return BARE if _grid_on() else None
    alt = _down(VK_MENU)
    shift = _down(VK_SHIFT)
    if alt and not shift:
        return CTRL_ALT
    if shift and not alt:
        return CTRL_SHIFT
    return None


def alive():
    """Is the polling thread actually running?"""
    if not _running:
        return False
    try:
        return _thread is not None and _thread.is_alive()
    except Exception:
        return bool(_running)


# How long the simulation-side pump may be silent before we treat it as dead.
# Loading screens tear the alarm down for real, so this has to be longer than
# one, and it is only ever checked when a key has actually been pressed.
_WATCHDOG_SECONDS = 8.0
# A reload is not free, and a reload loop would be worse than a dead mod.
_WATCHDOG_COOLDOWN = 90.0
_last_rescue = [0.0]


def _rescue_if_dead():
    """Called when a key is pressed. Puts the mod back if the pump has died.

    Returns True when a reload was started, so the press that triggered it is
    not also dispatched into a mod that is being torn down.
    """
    try:
        health = pump.health()
    except Exception:
        return False
    if health.get('silent_for', 0.0) < _WATCHDOG_SECONDS:
        return False
    if not health.get('zone'):
        return False          # a loading screen, not a death
    if health.get('busy_intent'):
        # Not dead - stuck inside something. Say so rather than reloading out
        # from under work that may still finish.
        speech.speak('Still working on {}, {:.0f} seconds so far.'.format(
            health['busy_intent'].replace('_', ' '), health.get('busy_for', 0)))
        return False
    now = time.monotonic()
    if now - _last_rescue[0] < _WATCHDOG_COOLDOWN:
        return False
    # One more chance to simply re-arm; a busy simulation thread looks exactly
    # like a dead one, and re-arming is far cheaper than a reload.
    try:
        if pump.start() and pump.health().get('silent_for', 99) < _WATCHDOG_SECONDS:
            return False
    except Exception:
        pass
    _last_rescue[0] = now
    speech.log('watchdog: pump silent for {:.0f}s, reloading the mod'.format(
        health.get('silent_for', 0)))
    speech.speak('The scanner stopped responding. Reloading it now.')
    try:
        result = reloader.reload_all()
    except Exception as ex:
        speech.log('watchdog: reload raised ({!r})'.format(ex))
        speech.speak('Automatic reload failed. Press Control Alt F5.')
        return True
    speech.speak(result)
    return True


def _loop():
    global _running
    generation = reloader.generation()
    held = {}
    speech.log('keyboard polling started')
    while _running:
        try:
            time.sleep(_POLL_SECONDS)
            if not reloader.is_current(generation):
                speech.log('keyboard thread retiring, superseded by a reload')
                return
            if not _enabled or not _game_has_focus():
                held.clear()
                continue
            _tick_escape()
            if _typing_on():
                _poll_typing(held, time.monotonic())
                continue
            # Read and clear every latch first, so nothing goes stale.
            state = _read_all()
            modifier = _active_modifier()
            if modifier is None:
                held.clear()
                continue
            now = time.monotonic()
            for (vk, mod), (intent, repeatable) in BINDINGS.items():
                down, tapped = state.get(vk, (False, False))
                if mod != modifier:
                    held.pop((vk, mod), None)
                    continue
                if not down and not tapped:
                    held.pop((vk, mod), None)
                    continue
                info = held.get((vk, mod))
                if info is None:
                    held[(vk, mod)] = [now, now]
                    if _rescue_if_dead():
                        held.clear()
                        break
                    pump.post(intent)
                    # A tap already over by the time we looked leaves nothing
                    # held, so clear it now and be ready for the next press
                    # rather than waiting for a release we already missed.
                    if not down:
                        held.pop((vk, mod), None)
                elif repeatable and down:
                    pressed_at, last_fire = info
                    if now - pressed_at >= _REPEAT_DELAY and now - last_fire >= _REPEAT_INTERVAL:
                        info[1] = now
                        pump.post(intent)
        except Exception as ex:
            speech.log('poll error ({!r})'.format(ex))
            time.sleep(0.25)
    speech.log('keyboard polling stopped')


def start():
    global _thread, _running
    if _running:
        return True
    if not _load():
        return False
    _running = True
    _thread = threading.Thread(target=_loop, name='a11yscan_keys')
    _thread.daemon = True
    _thread.start()
    return True


def stop():
    global _running
    _running = False


def set_enabled(value):
    global _enabled
    _enabled = bool(value)


def status():
    if _error is not None:
        return 'unavailable ({})'.format(_error)
    if not _running:
        return 'stopped'
    return 'on' if _enabled else 'paused'


def describe_bindings():
    lines = []
    for (vk, mod), (intent, _) in sorted(BINDINGS.items(), key=lambda kv: kv[1][0]):
        lines.append('  {}+{}: {}'.format(
            MOD_NAMES.get(mod, mod), KEY_NAMES.get(vk, hex(vk)), intent))
    return lines
