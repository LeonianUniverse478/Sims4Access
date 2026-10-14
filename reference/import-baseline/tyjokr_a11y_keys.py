"""Contextual keyboard navigation.

Tab/Shift+Tab moves between controls; arrows move within the open surface.
Enter/Space activates once; Escape backs out. EA InputAction guards consume
these physical keys while our UI owns focus. Python polling supplies presses,
repeats and releases. The transient Windows hook remains scanner-chord-only.
Ordinary typing never waits on a permanent Python keyboard hook.
"""
import threading
import time
from collections import deque

import sims4.commands

import tyjokr_a11y_lang as lang
import tyjokr_a11y_settings as settings
import tyjokr_a11y_speech as speech
import tyjokr_a11y_phone  # install the incoming-call observer at startup
import tyjokr_a11y_hub  # register the common-actions commands

try:
    # NOTE: the bundled ctypes package ships only the core modules, so
    # ctypes.wintypes is NOT available here; use plain c_ulong for DWORDs.
    import ctypes
except Exception as _import_ex:
    ctypes = None
    _ctypes_error = repr(_import_ex)

VK_SHIFT = 0x10
VK_MENU = 0x12  # Alt
VK_CONTROL = 0x11
VK_LMENU = 0xA4   # left Alt
VK_RMENU = 0xA5   # right Alt; AltGr on many non-US layouts

# Tab direction is resolved from Shift at press time, with one latch per key.
BINDINGS = {
    'A11yTabNext': ('next control (Shift reverses)', [(0x09, False)]),
    'A11yActivate': ('activate or confirm choice', [(0x0D, False)]),
    'A11yToggle': ('toggle or select', [(0x20, False)]),
    'A11yReturnRow': ('return to last picker row', [(0x08, False)]),
    'A11yEscape': ('back or close', [(0x1B, False)]),
    'A11yArrowUp': ('previous row', [(0x26, False)]),
    'A11yArrowDown': ('next row', [(0x28, False)]),
    'A11yArrowLeft': ('left or decrease', [(0x25, False)]),
    'A11yArrowRight': ('right or increase', [(0x27, False)]),
}
NUMPAD_BINDINGS = {0x64: 'A11yArrowUp', 0x66: 'A11yArrowDown',
                   0x65: 'A11yActivate', 0x68: 'A11yRepeat',
                   0x6E: 'A11yDismiss'}

# Scanner chords (Ctrl+Alt; the layout started as glaroc's a11yscan and now
# drives the scanner tree: Up/Down siblings, Right enters, Left goes back):
# vk -> (scanner intent, repeats while held). Polled keys cannot be
# swallowed, so a chord layer keeps bare keys free for the game, and nothing
# here collides with the numpad set above. Two known collisions outside the
# game: Ctrl+Alt+arrows is Intel's screen-rotation hotkey on some laptops
# (turn it off in the Intel graphics settings), and AltGr sends Ctrl+Alt on
# many non-US layouts, so a right-Alt chord on such a layout is treated as
# typing and ignored (see _altgr_pressed).
CHORDS = {
    0x26: ('prev', True),      # Up: previous thing
    0x28: ('next', True),      # Down: next thing
    0x25: ('prevcat', True),   # Left: previous main category
    0x27: ('nextcat', True),   # Right: next main category
    0x21: ('prevsub', True),   # Page Up: previous subcategory
    0x22: ('nextsub', True),   # Page Down: next subcategory
    0x0D: ('open', False),     # Enter: open the menu / activate
    0x20: ('scannermode', False),  # Space: scanner mode on or off
    0x08: ('back', False),     # Backspace: close the menu
    0x53: ('rescan', False),   # S
    0x57: ('where', False),    # W: where am I
    0x52: ('repeat', False),   # R
    0x48: ('help', False),     # H
    0x50: ('phone', False),    # P: waiting household call/text
    0x45: ('mood', False),     # E: emotion and moodlets
    0x47: ('wants', False),    # G: wants/fears
    0x42: ('buildtoggle', False),  # B: native Build cursor
    0x54: ('gridtoggle', False),   # T: read-only lot grid
    0xDB: ('rotateleft', False),   # [ : native Build rotation
    0xDD: ('rotateright', False),  # ]
    0x5A: ('undo', False),         # Z: native Build undo
    0x59: ('redo', False),         # Y: native Build redo
    0x46: ('buildgrid', False),    # F: aim at sampled grid point, never place
    # glaroc's Ctrl+Alt+1..8: switch to household Sim N (selectable order).
    0x31: ('sim1', False), 0x32: ('sim2', False), 0x33: ('sim3', False), 0x34: ('sim4', False),
    0x35: ('sim5', False), 0x36: ('sim6', False), 0x37: ('sim7', False), 0x38: ('sim8', False),
}
CHORD_NAMES = {0x26: 'Up', 0x28: 'Down', 0x25: 'Left', 0x27: 'Right', 0x20: 'Space',
               0x21: 'PageUp', 0x22: 'PageDown',
               0x0D: 'Enter', 0x08: 'Backspace', 0x53: 'S', 0x57: 'W',
               0x52: 'R', 0x48: 'H', 0x50: 'P', 0x45: 'E', 0x47: 'G',
               0x42: 'B', 0x54: 'T', 0xDB: '[', 0xDD: ']', 0x5A: 'Z', 0x59: 'Y',
               0x46: 'F', 0x31: '1', 0x32: '2', 0x33: '3', 0x34: '4',
               0x35: '5', 0x36: '6', 0x37: '7', 0x38: '8'}

# Key names for the a11y.keys listing (single source in settings).
_KEY_NAMES = settings.KEY_NAMES

_POLL_SECONDS = 0.01

# Holding a navigation key auto-repeats it (OS-style: initial delay, then a
# steady rate). Only movement actions repeat; activate/clear/speech keys fire
# once per press. Flash preserves input order while a list realizes a row.
_REPEATABLE = {'A11yNavNext', 'A11yNavPrev', 'A11yArrowUp', 'A11yArrowDown',
               'A11yArrowLeft', 'A11yArrowRight', 'A11yScanner:prev', 'A11yScanner:next'}

# Scanner mode: bare keys browse the scanner tree while Flash reports that
# the scanner owns input; its native guards consume them, so the arrows never
# pan the camera. No system hook. Escape is deliberately not a scanner key:
# it stays the game's Options menu.
SCANNER_KEYS = {0x26: 'A11yScanner:prev', 0x28: 'A11yScanner:next',
                0x27: 'A11yScanner:nextcat', 0x25: 'A11yScanner:prevcat',
                0x0D: 'A11yScanner:open', 0x08: 'A11yScanner:back',
                0x20: 'A11yScanner:repeat'}
_scanner_owner = False       # Flash: the scanner currently owns bare keys
_scanner_live = False        # Flash: Live mode with the setting on (camera follow)
_scanner_suspended = False   # a menu, dialog or other mode took input meanwhile
_scanner_pending_announce = False   # speak "Scanner" on Flash's first confirmation
_chord_repeating = False     # the poller is sending an auto-repeat of a chord
_REPEAT_DELAY = 0.45
_REPEAT_INTERVAL = 0.065

_thread = None
_running = False
_enabled = bool(settings.get('keyboard', True))
_modal_active = False
_editing_active = False
_input_epoch = 0
_opening_keys = set()
_ACTIVATION_KEYS = frozenset((0x0D, 0x20))


def fence_opening_input():
    """Retire activation input already in flight when a new surface opens.

    Snapshot only keys already down/tapped; a fresh first press stays usable.
    Windows' low bit is consumed here deliberately, before polling can
    mistake the console's completed Enter tap for a new picker activation.
    """
    global _input_epoch
    _input_epoch += 1
    if ctypes is None or not _enabled:
        return
    try:
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        if not _game_is_foreground(user32, kernel32):
            return
        for vk in _ACTIVATION_KEYS:
            if user32.GetAsyncKeyState(vk) & 0x8001:
                _opening_keys.add(vk)
    except Exception as ex:
        speech.log_line('keys: opening input snapshot unavailable: {!r}'.format(ex))


@sims4.commands.Command('a11y.inputfence', command_type=sims4.commands.CommandType.Live)
def a11y_inputfence(payload: str = '', _connection=None):
    # Flash supplies an empty positional payload; the native command wrapper
    # also supplies _connection by keyword. Keep them separate. The startup
    # socket dispatcher calls this without either argument.
    fence_opening_input()
    return True


_route_logged = {}


def _log_route(reason, intent):
    """One line per reason per second: why a chord went where it went."""
    now = time.monotonic()
    if now - _route_logged.get(reason, 0.0) >= 1.0:
        _route_logged[reason] = now
        speech.log_line('keys: chord {} {}'.format(intent, reason))


@sims4.commands.Command('a11y.modalstate', command_type=sims4.commands.CommandType.Live)
def a11y_modalstate(state: str = '00', _connection=None):
    return apply_modal_state(state, 'modalstate')


def apply_modal_state(state, source):
    """Flash's owner report. It arrives twice per change (a11y.modalstate and
    the a11y.context_enc suffix, from the same A11yModalFrame pass), so one
    lost post cannot leave keys routing chords to a closed owner. Applying
    the same state again changes nothing."""
    global _modal_active, _editing_active, _input_epoch
    if isinstance(state, int) and not isinstance(state, bool) and state in (0, 1, 10, 11):
        # sims4.commands converts only str arguments; a payload a caller
        # already turned into a number arrives as one.
        state = '{:02d}'.format(state)
    if isinstance(state, str) and state in ('0', '1'):
        # Live evidence 2026-09-25: the native command path drops the
        # leading zero, so Flash's '00' and '01' arrive as '0' and '1'.
        state = '0' + state
    if state not in ('00', '01', '10', '11'):
        speech.log_line('keys: modal state rejected {} {} ({})'.format(
            type(state).__name__, repr(state)[:24], source))
        return False
    before = ('1' if _modal_active else '0') + ('1' if _editing_active else '0')
    if before != state:
        speech.log_line('keys: modal {}->{} ({})'.format(before, state, source))
    if _modal_active and state[0] == '0':
        _input_epoch += 1       # the owner closed: queued modal navigation is stale
    if (state[0] == '1' and not _modal_active) or (_editing_active and state[1] == '0'):
        # New modal owner, or a text field just closed (console Enter):
        # retire keys already down or tapped before this surface change.
        fence_opening_input()
    _modal_active = state[0] == '1'
    _editing_active = state[1] == '1'
    if not _modal_active:
        # A missed pie-menu Hide message must not route future world chords
        # to the whole HUD. Flash ownership is the authoritative context.
        import tyjokr_a11y_scanner as scanner
        scanner.a11y_menuclosed()
    return True


def _deliver(message_name):
    """Only the simulation-thread pump may call the game distributor."""
    import distributor.ops
    import distributor.system
    op = distributor.ops.SendUIMessage(message_name)
    distributor.system.Distributor.instance().add_op_with_no_owner(op)


def _announce_ui_settings():
    """Simulation thread, with every keyboard lease: a UI copy created since
    the last change (Build and Live swap TooltipManager copies) starts with
    each switch off until it hears it."""
    try:
        import tyjokr_a11y_build as build
        build.announce_controls()
    except Exception as ex:
        speech.log_line('keys: build controls notice failed: {!r}'.format(ex))
    try:
        import tyjokr_a11y_travel as travel
        travel.announce_setting()
    except Exception as ex:
        speech.log_line('keys: travel list notice failed: {!r}'.format(ex))
    _announce_scanner_mode()
    if _scanner_live:
        _scanner_call('update_camera_follow')


def _announce_scanner_mode():
    """Simulation thread: A11y|scannermode|on or off to every UI copy."""
    try:
        _deliver('A11y|scannermode|' + ('on' if _scanner_effective() else 'off'))
    except Exception as ex:
        speech.log_line('keys: scanner mode notice failed: {!r}'.format(ex))


def _scanner_effective():
    """The scanner mode setting counts only while keyboard mode and the
    scanner are on."""
    return (bool(settings.get('scanner_mode', False)) and _enabled
            and bool(settings.get('keyboard', True)) and bool(settings.get('scanner', True)))


def _scanner_routing():
    return _scanner_effective() and _scanner_owner and not _modal_active and not _editing_active


def _in_live():
    try:
        import services
        zone = services.current_zone()
        return zone is not None and not zone.is_in_build_buy
    except Exception:
        return False


def set_scanner_mode(on):
    """Simulation thread: persist the scanner mode setting and apply it
    (Ctrl+Alt+Space, the settings menu and a11y.scannermode all come here)."""
    if on and (not _enabled or not settings.get('scanner', True)):
        speech.speak(lang.t('scanner mode needs scanner'), explicit=True)
        return False
    was = bool(settings.get('scanner_mode', False))
    settings.set('scanner_mode', bool(on))
    apply_scanner_setting(announce_change=(was != bool(on)))
    return True


def apply_scanner_setting(announce_change=False):
    """The setting (or keyboard/scanner) changed: tell every UI copy and set
    up the announcement. On: "Scanner. <location>" when Flash first confirms
    it owns the keys (Live), or a spoken note outside Live. Off: release."""
    global _scanner_suspended, _scanner_pending_announce, _scanner_live, _input_epoch
    _announce_scanner_mode()
    _input_epoch += 1               # nothing queued under the old setting may act
    if not _scanner_effective():
        _scanner_suspended = False
        _scanner_pending_announce = False
        if _scanner_live:
            _scanner_live = False
            _scanner_call('set_camera_live', False)   # release at once, before Flash reports
        if announce_change:
            speech.log_line('keys: scanner mode off')
            speech.speak(lang.t('scanner mode off'), explicit=True)
        return
    try:
        import tyjokr_a11y_grid as grid
        if grid.active():
            grid.leave()         # one cursor at a time: the grid also uses arrows
    except Exception as ex:
        speech.log_line('keys: grid leave failed: {!r}'.format(ex))
    fence_opening_input()        # the toggle's Space must not also act
    _scanner_suspended = False
    # "Scanner" is spoken when Flash confirms it owns the keys, never before.
    _scanner_pending_announce = True
    speech.log_line('keys: scanner mode on (waiting for the client)')
    if announce_change and not _in_live():
        speech.speak(lang.t('scanner mode starts in live'), explicit=True)


def scanner_zone_started():
    """Zone load (pump start): say where the scanner is once Live input is
    confirmed again."""
    global _scanner_pending_announce
    if _scanner_effective():
        _scanner_pending_announce = True
    _announce_scanner_mode()


def _toggle_scanner_mode(epoch):
    if epoch != _input_epoch:
        _log_route('dropped: input epoch changed before the pump turn', 'scannermode')
        return
    set_scanner_mode(not settings.get('scanner_mode', False))


def _scanner_key(intent, epoch):
    """Simulation thread: one bare key in scanner mode, re-checked here."""
    if epoch != _input_epoch:
        _log_route('dropped: input epoch changed before the pump turn', 'scanner ' + intent)
        return
    if not _scanner_routing():
        _log_route('dropped: the scanner no longer owns input', 'scanner ' + intent)
        return
    import tyjokr_a11y_scanner as scanner
    _log_route('handled by scanner mode', 'scanner ' + intent)
    scanner.on_key(intent, on_simulation_thread=True)


@sims4.commands.Command('a11y.scannerowner', command_type=sims4.commands.CommandType.Live)
def a11y_scannerowner(state: str = '0', _connection=None):
    """Flash: whether the scanner owns bare keys now. Posted on change and
    again with every mode heartbeat; only a change does anything here."""
    global _scanner_owner, _scanner_suspended, _scanner_pending_announce
    if isinstance(state, int) and not isinstance(state, bool) and state in (0, 1):
        state = str(state)
    if state not in ('0', '1'):
        speech.log_line('keys: scanner owner rejected {} {}'.format(type(state).__name__, repr(state)[:24]))
        return False
    global _input_epoch
    owner = state == '1'
    changed = owner != _scanner_owner
    if changed:
        speech.log_line('keys: scanner owner {}->{}'.format(int(_scanner_owner), int(owner)))
        _scanner_owner = owner
        # A scanner key queued under the old owner must not act under the
        # next one (a menu can open and close before the pump turn).
        _input_epoch += 1
    if not _scanner_effective():
        return True
    if not owner:
        if changed:
            _scanner_suspended = not _scanner_pending_announce
        return True
    if not changed and not _scanner_pending_announce and not _scanner_suspended:
        return True                 # a heartbeat re-post: nothing to do
    if _modal_active or _editing_active:
        return True                 # announced when the scanner really has the keys
    import tyjokr_a11y_scanner as scanner
    if _scanner_pending_announce:
        _scanner_pending_announce = False
        _scanner_suspended = False
        scanner.enter_mode()
        return True
    if _scanner_suspended and not _modal_active and not _editing_active:
        # Back from a menu, dialog, panel or Build: a still-held Enter must
        # not act again, then say where the scanner is.
        _scanner_suspended = False
        fence_opening_input()
        scanner.resume_mode()
    return True


def _scanner_call(name, *args):
    """Call a scanner hook if this build of the scanner has it."""
    try:
        import tyjokr_a11y_scanner as scanner
        fn = getattr(scanner, name, None)
        if fn is not None:
            return fn(*args)
    except Exception as ex:
        speech.log_line('keys: scanner.{} failed: {!r}'.format(name, ex))
    return None


@sims4.commands.Command('a11y.scannerlive', command_type=sims4.commands.CommandType.Live)
def a11y_scannerlive(state: str = '0', _connection=None):
    """Flash: Live mode with scanner mode on, whatever owns the keys (menus
    and text fields keep it on; Build, CAS and the main menu turn it off).
    Drives the camera follow; only a change does anything."""
    global _scanner_live
    if isinstance(state, int) and not isinstance(state, bool) and state in (0, 1):
        state = str(state)
    if state not in ('0', '1'):
        speech.log_line('keys: scanner live rejected {} {}'.format(type(state).__name__, repr(state)[:24]))
        return False
    live = state == '1' and _scanner_effective()
    if live != _scanner_live:
        speech.log_line('keys: scanner live {}->{}'.format(int(_scanner_live), int(live)))
    _scanner_live = live
    # Every report goes through: a zone reset on the camera side must be
    # able to resume from the next report even when this flag did not move.
    _scanner_call('set_camera_live', live)
    return True


@sims4.commands.Command('a11y.scannermode', command_type=sims4.commands.CommandType.Live)
def a11y_scannermode(action: str = 'toggle', _connection=None):
    """a11y.scannermode [on|off|toggle]"""
    action = str(action).lower()
    if action not in ('on', 'off', 'toggle'):
        return False
    current = bool(settings.get('scanner_mode', False))
    return set_scanner_mode(not current if action == 'toggle' else action == 'on')


def _send_owned(message_name):
    """Modal chord navigation: delivered only while the owner it was sampled
    under is still current. A closed dialog or pie (or a new one) advances
    the epoch, so a queued Next/Previous can no longer walk the HUD behind it.
    Scope: owner changes Flash reports (close, or a new owner through its
    opening fence). A swap between two owners with no fence in between is
    left to the client's own no-owner guard."""
    if message_name == 'A11yRepeat':
        return _send(message_name)
    epoch = _input_epoch
    try:
        try:
            import tyjokr_a11y_startup as startup
            if startup.send_navigation(message_name):
                return
        except ImportError:
            pass
        import tyjokr_a11y_pump as pump
        if not pump.post(_deliver_activation, message_name, epoch):
            speech.log_line('keys: navigation unavailable (simulation pump inactive)')
    except Exception as ex:
        speech.log_line('keys: send {} failed: {!r}'.format(message_name, ex))


def _deliver_activation(message_name, epoch):
    # A queued press belongs to the surface that owned it when sampled.
    if epoch == _input_epoch:
        _deliver(message_name)


def _send(message_name):
    # Speech-control actions are handled in Python; only focus navigation
    # goes to the Flash layer.
    if message_name == 'A11yRepeat':
        try:
            speech.repeat_last()
        except Exception as ex:
            speech.log_line('keys: repeat failed: {!r}'.format(ex))
        return
    if message_name.startswith('A11yScanner:'):
        try:
            import tyjokr_a11y_pump as pump
            if not pump.post(_scanner_key, message_name[len('A11yScanner:'):], _input_epoch):
                speech.log_line('keys: navigation unavailable (simulation pump inactive)')
        except Exception as ex:
            speech.log_line('keys: send {} failed: {!r}'.format(message_name, ex))
        return
    if message_name == 'A11ySpeechMode':
        try:
            speech.cycle_mode()
        except Exception as ex:
            speech.log_line('keys: speech mode cycle failed: {!r}'.format(ex))
        return
    try:
        try:
            import tyjokr_a11y_startup as startup
            if startup.send_navigation(message_name):
                return
        except ImportError:
            # Older/unavailable startup bridges retain the loaded-zone path.
            pass
        import tyjokr_a11y_pump as pump
        posted = (pump.post(_deliver_activation, message_name, _input_epoch)
                  if message_name in ('A11yActivate', 'A11yToggle')
                  else pump.post(_deliver, message_name))
        if not posted:
            if message_name != 'A11y|lease':
                speech.log_line('keys: navigation unavailable (simulation pump inactive)')
    except Exception as ex:
        speech.log_line('keys: send {} failed: {!r}'.format(message_name, ex))


_altgr_layouts = {}


def _layout_has_altgr(user32, hkl):
    """True when this keyboard layout types characters with Ctrl+Alt (AltGr)."""
    if hkl in _altgr_layouts:
        return _altgr_layouts[hkl]
    found = False
    try:
        user32.VkKeyScanExW.restype = ctypes.c_short
        user32.VkKeyScanExW.argtypes = [ctypes.c_wchar, ctypes.c_void_p]
        for code in range(0x20, 0x100):
            result = user32.VkKeyScanExW(chr(code), hkl)
            if result != -1 and ((result >> 8) & 0x06) == 0x06:
                found = True
                break
    except Exception:
        found = False
    _altgr_layouts[hkl] = found
    return found


def _altgr_pressed(user32):
    """Right Alt alone on an AltGr layout: the player is typing, not chording."""
    try:
        if not (user32.GetAsyncKeyState(VK_RMENU) & 0x8000):
            return False
        if user32.GetAsyncKeyState(VK_LMENU) & 0x8000:
            return False
        hwnd = user32.GetForegroundWindow()
        thread_id = user32.GetWindowThreadProcessId(hwnd, None)
        user32.GetKeyboardLayout.restype = ctypes.c_void_p
        hkl = user32.GetKeyboardLayout(thread_id)
        return _layout_has_altgr(user32, hkl)
    except Exception:
        return False


# --------------------------------------------------- chord key swallowing
# Polling cannot stop the game from seeing a key, so Ctrl+Alt+Down still
# panned the camera on every scanner step (first in-game test, 2026-09-06).
# A WH_KEYBOARD_LL hook can refuse a key before it reaches the message
# queue. It lives on its own thread with its own message loop (a low-level
# hook is only called while its owning thread pumps messages), blocks ONLY
# chord keys while Ctrl+Alt is held and the game is in front, and is
# removed when polling stops or the feature is off. A blocked key never
# reaches the system key state, so the hook reports chord keys to the
# poller itself (_hook_state). Windows silently drops a hook whose callback
# is too slow (the callback needs the GIL, which a busy simulation thread
# can hold); the poller notices a chord key the hook never reported and the
# hook thread reinstalls it.
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
_SWALLOW_VKS = frozenset(CHORDS)
_hook_thread = None
_hook_running = False
_hook_handle = None
_hook_proc = None          # keep the ctypes callback alive or the hook dies
_hook_state = {}           # vk -> down, as the hook last saw it
# Key-ups the hook consumed never reach Windows, so the key's async high bit
# stays set after the physical release. Kept across hook removal until
# Windows shows a real release or a new press (see _mask_swallowed_releases).
# vk -> generation of its latest consumed key-up; the hook thread records,
# the poller retires, both under _swallow_lock.
_swallowed_up = {}
_swallow_lock = threading.Lock()
_swallow_generation = 0


def _record_swallowed_up(vk):
    global _swallow_generation
    with _swallow_lock:
        _swallow_generation += 1
        _swallowed_up[vk] = _swallow_generation


def _clear_swallowed_up(vk):
    with _swallow_lock:
        _swallowed_up.pop(vk, None)


def _swallowed_snapshot():
    with _swallow_lock:
        return dict(_swallowed_up)
_hook_edges = deque()      # preserve complete chord taps between poll samples
_hook_last_event = 0.0
_hook_missed = 0.0         # poller saw a chord key the hook did not report
_hook_installs = 0


def _swallow_enabled():
    # Always on with keyboard mode (no longer a player option); the hook
    # still needs Ctrl+Alt held, the game in front and no AltGr typing.
    return _enabled


def _hook_callback_factory(user32, kernel32):
    LRESULT = ctypes.c_ssize_t
    proto = ctypes.CFUNCTYPE(LRESULT, ctypes.c_int, ctypes.c_size_t, ctypes.c_ssize_t)
    user32.CallNextHookEx.restype = LRESULT
    user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t, ctypes.c_ssize_t]

    def callback(code, wparam, lparam):
        global _hook_last_event
        try:
            _hook_last_event = time.monotonic()
            if code == 0 and wparam in (WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP):
                # KBDLLHOOKSTRUCT starts with vkCode (DWORD)
                vk = ctypes.cast(lparam, ctypes.POINTER(ctypes.c_ulong))[0]
                if vk in _SWALLOW_VKS:
                    is_down = wparam in (WM_KEYDOWN, WM_SYSKEYDOWN)
                    previous = _hook_state.get(vk, False)
                    _hook_state[vk] = is_down
                    if is_down:
                        _clear_swallowed_up(vk)
                    if not is_down and previous:
                        _hook_edges.append((vk, False, _hook_last_event))
                    ctrl = user32.GetAsyncKeyState(VK_CONTROL) & 0x8000 != 0
                    alt = user32.GetAsyncKeyState(VK_MENU) & 0x8000 != 0
                    shift = user32.GetAsyncKeyState(VK_SHIFT) & 0x8000 != 0
                    if (ctrl and alt and not shift and _swallow_enabled()
                            and _game_is_foreground(user32, kernel32)
                            and not _altgr_pressed(user32)):
                        if is_down and not previous:
                            _hook_edges.append((vk, is_down, _hook_last_event))
                        elif not is_down:
                            user32.GetAsyncKeyState(vk)   # drain the old press bit
                            _record_swallowed_up(vk)
                        return 1
        except Exception:
            pass
        return user32.CallNextHookEx(None, code, wparam, lparam)

    return proto(callback)


def _hook_loop():
    """Own the hook and pump messages for it. Runs on its own thread."""
    global _hook_handle, _hook_proc, _hook_installs
    try:
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        user32.SetWindowsHookExW.restype = ctypes.c_void_p
        user32.SetWindowsHookExW.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
        user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
        kernel32.GetModuleHandleW.restype = ctypes.c_void_p
        kernel32.GetModuleHandleW.argtypes = [ctypes.c_void_p]
        _hook_proc = _hook_callback_factory(user32, kernel32)
        module = kernel32.GetModuleHandleW(None)

        class MSG(ctypes.Structure):
            _fields_ = [('hwnd', ctypes.c_void_p), ('message', ctypes.c_uint),
                        ('wParam', ctypes.c_size_t), ('lParam', ctypes.c_ssize_t),
                        ('time', ctypes.c_ulong), ('pt_x', ctypes.c_long), ('pt_y', ctypes.c_long)]
        msg = MSG()

        def install():
            global _hook_handle, _hook_installs, _hook_last_event, _hook_missed
            _hook_state.clear()
            _hook_last_event = time.monotonic()
            _hook_missed = 0.0
            handle = user32.SetWindowsHookExW(WH_KEYBOARD_LL, ctypes.cast(_hook_proc, ctypes.c_void_p), module, 0)
            _hook_handle = handle
            _hook_installs += 1
            speech.log_line('keys: swallow hook {} (install #{})'.format(
                'installed' if handle else 'FAILED err={}'.format(ctypes.get_last_error()), _hook_installs))
            return bool(handle)

        def remove(reason):
            global _hook_handle
            if _hook_handle:
                try:
                    user32.UnhookWindowsHookEx(_hook_handle)
                except Exception:
                    pass
                _hook_handle = None
                _hook_state.clear()
                speech.log_line('keys: swallow hook removed ({})'.format(reason))

        # The hook is system-wide and its callback needs the GIL, so while it
        # is installed every keystroke in every program waits on the game.
        # Even ordinary typing INSIDE the game must bypass this Python hook.
        # Check modifiers on every pass; keep the hook only for scanner chords.
        last_check = time.monotonic()
        while _hook_running:
            # Pump whatever is queued (the hook callback is delivered here), then rest.
            while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            time.sleep(0.005)
            now = time.monotonic()
            wanted = (_swallow_enabled()
                      and bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
                      and bool(user32.GetAsyncKeyState(VK_MENU) & 0x8000)
                      and not (user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)
                      and _game_is_foreground(user32, kernel32)
                      and not _altgr_pressed(user32))
            if wanted and not _hook_handle:
                install()
            elif _hook_handle and not wanted:
                remove('scanner chord released or inactive')
            if now - last_check > 1.0:
                last_check = now
                if _hook_handle and _hook_missed > _hook_last_event + 0.5:
                    remove('dropped by Windows, reinstalling')
                    install()
        remove('polling stopped')
    except Exception as ex:
        speech.log_line('keys: swallow hook thread failed: {!r}'.format(ex))
    finally:
        # A failed message loop must not leave a hook blocking all input.
        if _hook_handle:
            try:
                user32.UnhookWindowsHookEx(_hook_handle)
            except Exception:
                pass
        _hook_handle = None
        _hook_state.clear()


def _mask_swallowed_releases(sampled, before=None):
    """Report a key as up while Windows still lacks a key-up the hook
    consumed and no new press has arrived.

    Without this, the stale high bit reads as a held key once Ctrl+Alt are
    released or the hook goes quiet, and navigation repeats until that key
    is pressed again (scanner incident 2026-09-25). Only consumed key-ups
    count: a hook Windows dropped leaves _hook_state stale, and then the
    polled state is the one to trust.

    before is the record snapshot taken just ahead of sampling. A record
    made after it belongs to a key-up that happened after (or during) the
    read, so the sample cannot retire it: a press it read still counts, and
    otherwise the consumed key-up already proves the key is up."""
    for vk, generation in _swallowed_snapshot().items():
        state = sampled.get(vk)
        if state is None:
            continue
        pressed = bool(state & 1)
        if before is not None and before.get(vk) != generation:
            if not pressed:
                sampled[vk] = 0
            continue
        if not state & 0x8000 or pressed:
            with _swallow_lock:          # retire only the record this sample saw
                if _swallowed_up.get(vk) == generation:
                    del _swallowed_up[vk]
        else:
            sampled[vk] = 0
    return sampled


def start_swallow():
    global _hook_thread, _hook_running
    if ctypes is None or not _swallow_enabled():
        return False
    if _hook_thread is not None and _hook_thread.is_alive():
        return True
    _hook_running = True
    _hook_thread = threading.Thread(target=_hook_loop, name='a11y_keys_hook', daemon=True)
    _hook_thread.start()
    return True


def stop_swallow():
    global _hook_running
    _hook_running = False


def swallow_status():
    if not _swallow_enabled():
        return 'off'
    if _hook_thread is None or not _hook_thread.is_alive():
        return 'not running'
    return 'installed' if _hook_handle else 'armed (hold Ctrl+Alt in the game)'


def _chord(intent):
    """An active modal owns navigation before the world scanner."""
    try:
        if intent == 'scannermode':
            if not _editing_active:
                import tyjokr_a11y_pump as pump
                pump.post(_toggle_scanner_mode, _input_epoch)
            return
        if intent == 'repeat' and (_modal_active or _editing_active):
            _send('A11yRepeat')
            return
        if _editing_active and not _modal_active:
            return
        if intent == 'phone':
            if _modal_active:
                speech.speak('Close the current panel or dialog before opening a waiting call.', explicit=True)
                return
            import tyjokr_a11y_phone as phone
            import tyjokr_a11y_pump as pump
            pump.post(phone.open_waiting)
            return
        if intent.startswith('sim') and intent[3:].isdigit():
            # Direct household switch (glaroc's Ctrl+Alt+digit). Never while
            # typing, and never behind a dialog, picker or focused panel: a
            # switch would pull the context out from under it (Codex review).
            if _editing_active:
                return
            if _modal_active:
                speech.speak('Close the current panel or dialog before switching Sims.', explicit=True)
                return
            import tyjokr_a11y_pump as pump
            if not pump.post(_switch_household_sim, int(intent[3:]), _input_epoch):
                speech.speak(lang.t('no lot loaded'), explicit=True)
            return
        if intent in ('mood', 'wants', 'needs'):
            if not _modal_active:
                _send({'mood': 'A11yMood', 'wants': 'A11yWants', 'needs': 'A11yNeeds'}[intent])
            return
        if intent in ('buildtoggle', 'buildgrid') and not _editing_active:
            # Catalog keyboard browsing also owns a scope. Let the native
            # Build handler distinguish it from an actual modal dialog.
            import tyjokr_a11y_pump as pump
            pump.post(_world_chord, intent, _input_epoch)
            return
        if _modal_active:
            message = {'prev': 'A11yNavPrev', 'next': 'A11yNavNext',
                       'prevcat': 'A11yArrowLeft', 'nextcat': 'A11yArrowRight',
                       'open': 'A11yActivate', 'back': 'A11yDismiss',
                       'repeat': 'A11yRepeat'}.get(intent)
            if message is not None:
                _log_route('routed to the modal owner', intent)
                _send_owned(message)
            # Scanner rescan/category actions must not reach the world
            # behind a dialog. Help remains available without changing it.
            elif intent == 'help':
                speech.speak('Dialog. Up and down move between controls. '
                             'Enter activates. Backspace goes back when allowed. '
                             'R reads the current control. Tab moves between controls. Escape closes. '
                             'Hold Control and Alt for scanner navigation keys.',
                             explicit=True)
            return
        import tyjokr_a11y_pump as pump
        args = (intent, _input_epoch, True) if _chord_repeating else (intent, _input_epoch)
        if pump.post(_world_chord, *args):
            _log_route('queued for world handling', intent)
        else:
            _log_route('lost: simulation pump inactive', intent)
    except Exception as ex:
        speech.log_line('keys: chord {} failed: {!r}'.format(intent, ex))


def _switch_household_sim(index, epoch):
    """Simulation thread. index is 1-based in the client's selectable order.
    Ownership is re-checked here: a dialog or panel may have taken focus
    between the key press and this pump slot (Codex review)."""
    if epoch != _input_epoch or _editing_active or _modal_active:
        return False
    import tyjokr_a11y_hub as hub
    try:
        import services
        manager = services.client_manager()
        client = manager.get_first_client() if manager is not None else None
        sims = list(client.selectable_sims) if client is not None else []
    except Exception as ex:
        speech.log_line('keys: household lookup failed: {!r}'.format(ex))
        sims = []
    if not 1 <= index <= len(sims):
        speech.speak(lang.t('sim unavailable'), explicit=True)
        return False
    return hub.select_sim(sims[index - 1].sim_id)


def _world_chord(intent, epoch, repeat=False):
    """Resolve world modes on the simulation thread, after ownership checks."""
    if epoch != _input_epoch:
        _log_route('dropped: input epoch changed before the pump turn', intent)
        return
    if _editing_active:
        _log_route('dropped: a text field has focus', intent)
        return
    if _modal_active and intent not in ('buildtoggle', 'buildgrid'):
        _log_route('dropped: a modal owner opened before the pump turn', intent)
        return
    import tyjokr_a11y_build as build
    import tyjokr_a11y_grid as grid
    if intent == 'buildgrid':
        build.aim_grid()
        return
    if intent == 'buildtoggle':
        # Module entry points validate their destination before retiring the
        # other mode, so a failed request cannot disable a working cursor.
        build.toggle()
        return
    if intent == 'gridtoggle':
        grid.toggle()
        return
    if intent == 'help':
        tyjokr_a11y_hub.open_hub()
        return
    if build.active() or build.aiming():
        build.on_key(intent)
        return
    if grid.active():
        grid.on_key(intent)
        return
    if intent == 'repeat':
        _send('A11yRepeat')
        return
    # Native transaction commands have no scanner meaning when the cursor
    # is off. They must never become unrelated actions in Live mode.
    if intent in ('rotateleft', 'rotateright', 'undo', 'redo'):
        if not build.controls_enabled() and build._zone() is not None:
            build.refuse_disabled()     # in Build mode, say why nothing happened
        return
    if repeat and intent in ('prevcat', 'nextcat'):
        return                  # holding Left/Right must not walk several tree levels
    if settings.get('scanner', True):
        import tyjokr_a11y_scanner as scanner
        scanner.on_key(intent, on_simulation_thread=True)


def _game_is_foreground(user32, kernel32):
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value == kernel32.GetCurrentProcessId()
    except Exception:
        return False


def _plain_message(vk, ctrl=False, alt=False, shift=False):
    """One policy for native context, editing and optional numpad navigation."""
    if not _enabled:
        return None
    if vk == 0x4E and ctrl and shift and not alt and not _modal_active and not _editing_active:
        return 'A11yNeeds'
    if ctrl or alt:
        return None
    if vk == 0x09 and (not _editing_active or _modal_active):
        return 'A11yTabPrev' if shift else 'A11yTabNext'
    if vk in SCANNER_KEYS and not shift and _scanner_routing():
        return SCANNER_KEYS[vk]
    if not _modal_active:
        return None
    if vk == 0x1B:
        # Flash checks whether its native guard actually owned this press.
        # The world Escape may already have opened Options by this poll.
        return 'A11yEscape'
    if settings.get('numpad_navigation', False) and vk in NUMPAD_BINDINGS:
        return NUMPAD_BINDINGS[vk]
    if _editing_active or shift:
        return None
    for message, (_label, combos) in BINDINGS.items():
        if (vk, False) in combos:
            return message
    return None


def _loop():
    global _running, _hook_missed, _chord_repeating
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    was_down, pressed_at, last_fire = {}, {}, {}
    editing_prev = False
    last_lease = 0.0
    plain = {vk for _label, combos in BINDINGS.values() for vk, _alt in combos}
    plain.update(NUMPAD_BINDINGS)
    plain.add(0x4E)
    all_keys = plain | set(CHORDS)
    speech.log_line('keys: contextual polling started')
    while _running:
        try:
            if not _enabled or not _game_is_foreground(user32, kernel32):
                # Release native guards when focus leaves the game. Never
                # replay background keystrokes on return.
                for vk in plain:
                    if was_down.get(('plain', vk), False):
                        _send('A11y|keyup|{}'.format(vk))
                was_down.clear()
                pressed_at.clear()
                last_fire.clear()
                _hook_edges.clear()
                _opening_keys.clear()
                time.sleep(0.05)
                continue
            now = time.monotonic()
            # A text field that just closed (cheat console on Enter) leaves the
            # submitting key's tap latch behind; if this poll lands after Flash
            # clears the editing flag, that tap would activate whatever we focus
            # next (settings row, HUD button). Retire it once, here.
            editing_ended = editing_prev and not _editing_active
            editing_prev = _editing_active
            if editing_ended:
                fence_opening_input()
            if now - last_lease >= 0.5:
                _send('A11y|lease')
                try:
                    import tyjokr_a11y_pump as pump
                    pump.post(_announce_ui_settings)
                except Exception as ex:
                    speech.log_line('keys: settings heartbeat failed: {!r}'.format(ex))
                last_lease = now
            alt = bool(user32.GetAsyncKeyState(VK_MENU) & 0x8000)
            ctrl = bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
            shift = bool(user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)
            chord = ctrl and alt and not shift and not _altgr_pressed(user32)
            # Read each key once: GetAsyncKeyState's low bit records a short
            # tap since the last query and must not be drained by two loops.
            epoch_at_sample = _input_epoch
            swallowed_before = _swallowed_snapshot()
            sampled = _mask_swallowed_releases(
                {vk: user32.GetAsyncKeyState(vk) for vk in all_keys}, swallowed_before)
            hook_alive = _hook_handle is not None and (now - _hook_last_event) < 1.0
            while _hook_edges:
                vk, down, edge_time = _hook_edges.popleft()
                key = ('chord', vk)
                if down and vk not in _opening_keys and not was_down.get(key, False):
                    _chord(CHORDS[vk][0])
                    pressed_at[key] = edge_time
                    last_fire[key] = now
                was_down[key] = down
            for vk, (intent, repeatable) in CHORDS.items():
                key = ('chord', vk)
                raw_down = bool(sampled[vk] & 0x8000)
                raw_tap = bool(sampled[vk] & 1)
                hook_knows_key = hook_alive and vk in _hook_state
                if chord and raw_down and _hook_handle is not None and not hook_knows_key:
                    _hook_missed = now
                # A consumed key-up may not reach GetAsyncKeyState. Its
                # stale high bit must not restart a released scanner chord.
                down = chord and (bool(_hook_state[vk]) if hook_knows_key else raw_down)
                # The transient hook may not be installed yet. Preserve a
                # complete letter/arrow tap while Ctrl+Alt are still held,
                # just as plain navigation preserves taps between polls.
                # A live hook's release wins over stale Windows state.
                pressed = down or (chord and raw_tap and not hook_knows_key)
                if pressed and vk not in _opening_keys and not was_down.get(key, False):
                    _chord(intent)
                    pressed_at[key] = now
                    last_fire[key] = now
                elif down and repeatable and now - pressed_at.get(key, now) >= _REPEAT_DELAY and now - last_fire.get(key, 0) >= _REPEAT_INTERVAL:
                    _chord_repeating = True
                    try:
                        _chord(intent)
                    finally:
                        _chord_repeating = False
                    last_fire[key] = now
                was_down[key] = down
            for vk in plain:
                key = ('plain', vk)
                held = bool(sampled[vk] & 0x8000)
                tapped = bool(sampled[vk] & 1)
                if vk in _ACTIVATION_KEYS and not held and (editing_ended or epoch_at_sample != _input_epoch):
                    # Tap sampled across a surface change (editing ended, or a
                    # fence bumped the epoch since sampling): retire it.
                    was_down[key] = False
                    continue
                down = held or tapped
                message = _plain_message(vk, ctrl, alt, shift)
                if vk in _opening_keys:
                    # Consume the opener's key and its release, then allow
                    # a new physical press. Never synthesize another click.
                    if not held:
                        _opening_keys.discard(vk)
                        _send('A11y|keyup|{}'.format(vk))
                    was_down[key] = held
                    continue
                if chord:
                    # Holding Enter after releasing Ctrl/Alt cannot activate twice.
                    # A key released while modifiers remain held must also
                    # release its native guard. A swallowed hook key-up can
                    # leave GetAsyncKeyState stale, so a live hook wins.
                    chord_held = (bool(_hook_state[vk])
                                  if hook_alive and vk in _hook_state else held)
                    if not chord_held and (was_down.get(key, False) or tapped):
                        _send('A11y|keyup|{}'.format(vk))
                    was_down[key] = chord_held
                    continue
                if down and not was_down.get(key, False):
                    if message:
                        _send(message)
                    pressed_at[key] = now
                    last_fire[key] = now
                elif held and message in _REPEATABLE and now - pressed_at.get(key, now) >= _REPEAT_DELAY and now - last_fire.get(key, 0) >= _REPEAT_INTERVAL:
                    _send(message)
                    last_fire[key] = now
                if not held and (was_down.get(key, False) or tapped):
                    _send('A11y|keyup|{}'.format(vk))
                was_down[key] = held
        except Exception as ex:
            speech.log_line('keys: poll error: {!r}'.format(ex))
            time.sleep(1.0)
        time.sleep(_POLL_SECONDS)
    speech.log_line('keys: polling stopped')


def start():
    global _thread, _running
    if ctypes is None:
        speech.log_line('keys: ctypes unavailable ({}), keyboard navigation off'.format(
            globals().get('_ctypes_error', 'unknown')))
        return False
    if _thread is not None and _thread.is_alive():
        return True
    _running = True
    _thread = threading.Thread(target=_loop, name='a11y_keys', daemon=True)
    _thread.start()
    start_swallow()
    return True


def stop():
    global _running
    _running = False
    stop_swallow()


@sims4.commands.Command('a11y.keys', command_type=sims4.commands.CommandType.Live)
def a11y_keys(mode: str = 'on', _connection=None):
    global _enabled
    output = sims4.commands.CheatOutput(_connection)
    if mode.lower() in ('off', 'false', '0'):
        _enabled = False
        settings.set('keyboard', False)
        _send('A11yKeyboardOff')
        output('a11y: keyboard navigation OFF')
        speech.speak('Keyboard navigation off.', explicit=True)
        return True
    _enabled = True
    settings.set('keyboard', True)
    _send('A11yKeyboardOn')
    started = start()
    output('a11y: keyboard navigation {}'.format('ON' if started else 'UNAVAILABLE'))
    for message, (label, combos) in BINDINGS.items():
        output('   {}: {}'.format(label, ' or '.join(_describe(vk, alt) for (vk, alt) in combos)))
    for vk, (intent, _rep) in CHORDS.items():
        output('   {}: Ctrl+Alt+{}'.format(intent, CHORD_NAMES.get(vk, hex(vk))))
    output('   needs: Ctrl+Shift+N; accessibility menu: Ctrl+Alt+H')
    speech.speak('Keyboard navigation on.', explicit=True)
    return True


def _describe(vk, needs_alt):
    for name, code in _KEY_NAMES.items():
        if code == vk:
            return ('Alt+' if needs_alt else '') + name
    return ('Alt+' if needs_alt else '') + hex(vk)


@sims4.commands.Command('a11y.keyprobe', command_type=sims4.commands.CommandType.Live)
def a11y_keyprobe(mode: str = 'off', _connection=None):
    """Optional, non-consuming native/stage input diagnostics for one minute."""
    value = mode.lower()
    if value not in ('on', 'off'):
        return False
    _send('A11yKeyProbeOn' if value == 'on' else 'A11yKeyProbeOff')
    sims4.commands.CheatOutput(_connection)(
        'a11y: key probe {} requested{}'.format(
            value, ' for 60 seconds (key/modifier metadata only)' if value == 'on' else ''))
    return True


try:
    if _enabled:
        start()
    else:
        speech.log_line('keys: keyboard navigation disabled by settings')
except Exception as _ex:
    speech.log_line('keys: autostart failed: {!r}'.format(_ex))
