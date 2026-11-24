"""Read-only Windows/build coordinate diagnostics; never inject input or set DPI."""
import ctypes
import json
import math
import os
import threading
import time
import sims4.commands
import tyjokr_a11y_speech as speech

class POINT(ctypes.Structure):
    _fields_ = [('x', ctypes.c_int32), ('y', ctypes.c_int32)]

class RECT(ctypes.Structure):
    _fields_ = [(n, ctypes.c_int32) for n in ('left', 'top', 'right', 'bottom')]

_timer = None
_window_start = 0.0
_count = 0
_lock = threading.Lock()


def _api():
    # Private function objects: do not overwrite prototypes cached by the
    # existing mouse worker. HWND/context return values must be pointer-wide.
    u = ctypes.WinDLL('user32', use_last_error=True)
    ptr, integer = ctypes.c_void_p, ctypes.c_int32
    signatures = {
        'GetForegroundWindow': (ptr, []),
        'GetWindowThreadProcessId': (ctypes.c_uint32, [ptr, ctypes.POINTER(ctypes.c_uint32)]),
        'GetClientRect': (integer, [ptr, ctypes.POINTER(RECT)]),
        'GetWindowRect': (integer, [ptr, ctypes.POINTER(RECT)]),
        'ClientToScreen': (integer, [ptr, ctypes.POINTER(POINT)]),
        'ScreenToClient': (integer, [ptr, ctypes.POINTER(POINT)]),
        'GetCursorPos': (integer, [ctypes.POINTER(POINT)]),
        'GetPhysicalCursorPos': (integer, [ctypes.POINTER(POINT)]),
        'LogicalToPhysicalPointForPerMonitorDPI': (integer, [ptr, ctypes.POINTER(POINT)]),
        'GetDpiForWindow': (ctypes.c_uint32, [ptr]),
        'GetThreadDpiAwarenessContext': (ptr, []),
        'GetWindowDpiAwarenessContext': (ptr, [ptr]),
        'GetAwarenessFromDpiAwarenessContext': (integer, [ptr]),
        'GetSystemMetrics': (integer, [integer]),
        'MonitorFromWindow': (ptr, [ptr, ctypes.c_uint32]),
        'GetWindowLongPtrW': (ctypes.c_ssize_t, [ptr, integer]),
        'IsZoomed': (integer, [ptr]),
        'IsIconic': (integer, [ptr]),
    }
    for name, (result, args) in signatures.items():
        fn = getattr(u, name, None)
        if fn is not None:
            fn.restype, fn.argtypes = result, args
    return u


def _monitor_scale(u, hwnd):
    monitor = u.MonitorFromWindow(hwnd, 2)
    if not monitor: raise RuntimeError('monitor unavailable')
    lib = ctypes.WinDLL('shcore', use_last_error=True)
    fn = lib.GetScaleFactorForMonitor
    fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int32)]
    fn.restype = ctypes.c_int32
    scale = ctypes.c_int32()
    if fn(monitor, ctypes.byref(scale)) != 0: raise RuntimeError('scale unavailable')
    return int(scale.value)


def windows_snapshot(u=None):
    u = _api() if u is None else u
    hwnd = u.GetForegroundWindow()
    owner = ctypes.c_uint32()
    if not hwnd or not u.GetWindowThreadProcessId(hwnd, ctypes.byref(owner)) or owner.value != os.getpid():
        return {'refused': 'foreground window is not owned by this game process'}
    result = {'hwnd': int(hwnd), 'thread': threading.current_thread().name,
              'game_ui_stage_size': None, 'errors': {}}
    def field(name, fn):
        try: result[name] = fn()
        except Exception as exc: result['errors'][name] = type(exc).__name__
    def rect(fn):
        r = RECT()
        if not fn(hwnd, ctypes.byref(r)): raise RuntimeError('rectangle query failed')
        return [r.left, r.top, r.right, r.bottom]
    def point(fn, initial=(0, 0), window=True):
        p = POINT(*initial)
        args = (hwnd, ctypes.byref(p)) if window else (ctypes.byref(p),)
        if not fn(*args): raise RuntimeError('point query failed')
        return [p.x, p.y]
    field('client_rect_reported', lambda: rect(u.GetClientRect))
    field('window_rect_reported', lambda: rect(u.GetWindowRect))
    field('client_origin_reported', lambda: point(u.ClientToScreen))
    field('cursor_reported', lambda: point(u.GetCursorPos, window=False))
    field('cursor_physical', lambda: point(u.GetPhysicalCursorPos, window=False))
    field('window_dpi', lambda: int(u.GetDpiForWindow(hwnd)))
    field('monitor_scale_percent', lambda: _monitor_scale(u, hwnd))
    field('window_style_hex', lambda: hex(u.GetWindowLongPtrW(hwnd, -16) & 0xffffffff))
    field('maximized', lambda: bool(u.IsZoomed(hwnd)))
    field('minimized', lambda: bool(u.IsIconic(hwnd)))
    field('thread_awareness', lambda: int(u.GetAwarenessFromDpiAwarenessContext(u.GetThreadDpiAwarenessContext())))
    field('window_awareness', lambda: int(u.GetAwarenessFromDpiAwarenessContext(u.GetWindowDpiAwarenessContext(hwnd))))
    field('primary_size_reported', lambda: [u.GetSystemMetrics(0), u.GetSystemMetrics(1)])
    field('virtual_desktop_reported', lambda: [u.GetSystemMetrics(i) for i in (76, 77, 78, 79)])
    r = result.get('client_rect_reported')
    if r:
        w, h = r[2] - r[0], r[3] - r[1]
        result['client_size_reported'] = [w, h]
        samples = []
        for initial in ((0, 0), (w // 2, h // 2), (max(0,w-1), max(0,h-1))):
            sample = {'client': list(initial)}
            try:
                screen = point(u.ClientToScreen, initial)
                sample.update(screen_reported=screen, client_roundtrip=point(u.ScreenToClient, screen))
                sample['screen_physical_for_window'] = point(u.LogicalToPhysicalPointForPerMonitorDPI, screen)
            except Exception as exc: sample['error'] = type(exc).__name__
            samples.append(sample)
        result['samples'] = samples
    if u.GetForegroundWindow() != hwnd:
        return {'refused': 'foreground changed during capture'}
    return result


def saved_options():
    # Read only display fields, with a size cap; never include unrelated
    # preferences, paths or personal data from Options.ini in the log.
    result = {}
    try:
        folder = os.path.dirname(speech.LOG_PATH)
        for _ in range(3):
            if os.path.basename(folder).lower() == 'mods':
                root = os.path.dirname(folder)
                break
            folder = os.path.dirname(folder)
        else:
            raise ValueError('Mods root unavailable')
        with open(os.path.join(root, 'Options.ini'), 'r', encoding='utf-8-sig') as f:
            text = f.read(65536)
        keys = {'resolutionwidth','resolutionheight','resolutionrefresh','fullscreen','windowedfullscreen','uiscale','sceneresolution'}
        for line in text.splitlines():
            key, sep, value = line.partition('=')
            if sep and key.strip().lower() in keys:
                result[key.strip().lower()] = int(value.strip())
    except Exception as exc: result['error'] = type(exc).__name__
    return result


def record(kind, data=None, build=None):
    global _window_start, _count
    if not speech.log_enabled: return False
    with _lock:
        now = time.monotonic()
        if now - _window_start >= 60: _window_start, _count = now, 0
        if _count >= 30: return False
        _count += 1
    try:
        row = windows_snapshot()
        row.update(kind=kind, data=data, saved_options=saved_options())
        if build is not None and 'refused' not in row:
            try: row['adapter_size_reported'] = list(build._stage_size())
            except Exception as exc: row['errors']['adapter_size_reported'] = type(exc).__name__
        speech.log_line('display inspect: ' + json.dumps(row, sort_keys=True, default=str))
        return 'refused' not in row
    except Exception as exc:
        speech.log_line('display inspect: capture failed ' + type(exc).__name__)
        return False


_active = False


def observe(kind, data):
    """The build engine reports each projection; logged once a11y.inspect_display ran."""
    if not _active:
        return
    try:
        try:
            import tyjokr_a11y_plus_build as build
        except Exception:
            build = None
        record(kind, data, build)
    except Exception:
        pass  # Optional logging must never break a build.


def install(build=None):
    global _active
    _active = True


@sims4.commands.Command('a11y.inspect_display', command_type=sims4.commands.CommandType.Live)
def inspect_display(delay: float = 5, _connection=None):
    global _timer
    output = sims4.commands.CheatOutput(_connection)
    if not math.isfinite(delay): return False
    if not speech.log_enabled:
        output('Run a11y.log on first.'); return False
    try:
        import tyjokr_a11y_plus_build as build
        install(build)
    except Exception as exc:
        speech.log_line('display inspect: adapter unavailable ' + type(exc).__name__)
        output('Display diagnostic unavailable; see TS4 Access log.')
        return False
    if _timer is not None: _timer.cancel()
    delay = max(0, min(30, delay))
    def capture():
        try:
            record('manual', build=build)
        except Exception as exc:
            speech.log_line('display inspect: manual capture failed ' + type(exc).__name__)
    # No game APIs on this timer: only Win32/filesystem reads. Actual builder
    # worker DPI/coordinates are captured by the passive wrappers separately.
    _timer = threading.Timer(delay, capture)
    _timer.daemon = True
    _timer.name = 'a11y_display_probe'
    _timer.start()
    output('Read-only display snapshot in {} seconds. Close the console and keep the game focused; see TS4 Access log.'.format(delay))
    return True
