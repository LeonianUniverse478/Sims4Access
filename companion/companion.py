"""Shared parts of the a11yscan companion: speech, screen reading, clicking.

The companion exists for the screens the mod cannot reach - the ones drawn by
the game client, which has no accessibility tree and no simulation behind it.
It is a separate desktop program because it needs the screen and the mouse, and
the mod's Python has neither.

It deliberately does NOT try to be a screen reader. NVDA already does generic
OCR-and-click, and does it well. What NVDA cannot do is a whole known sequence:
"start my game" as one action, verified at each step. That is what this is for.

Three pieces, none of which need anything installed:

  speech   prism.dll, the same library the mod speaks through, so it comes out
           in the player's own voice at their own rate
  screen   Windows' own OCR engine, driven by ocr.ps1
  click    SendInput, after saying out loud what is about to be clicked

Nothing here clicks without announcing what it found and where. An OCR tool
that clicks silently will eventually click the wrong thing, and the player will
have no way to know why.
"""
import ctypes
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OCR_SCRIPT = os.path.join(HERE, 'ocr.ps1')
GAME_WINDOW = 'The Sims 4'

CANDIDATE_ROOTS = (
    os.path.join('~', 'Documents', 'Electronic Arts', 'The Sims 4'),
    os.path.join('~', 'OneDrive', 'Documents', 'Electronic Arts',
                 'The Sims 4'),
)


# --------------------------------------------------------------------- speech

PRISM_OK = 0
PRISM_ALREADY_INITIALIZED = 15

_prism = None
_backend = None

# Whether the last read came from the game's own window or from the whole
# screen. Falling back silently would let the companion click something on the
# desktop while the player believes it is looking at the game.
last_source = 'nothing read yet'


class PrismConfig(ctypes.Structure):
    # Straight from include/prism.h; prism_config_init returns this by value.
    _fields_ = [
        ('version', ctypes.c_uint8),
        ('registry', ctypes.c_void_p),
        ('availability_callback', ctypes.c_void_p),
        ('availability_userdata', ctypes.c_void_p),
        ('availability_poll_interval_ms', ctypes.c_uint32),
        ('availability_debounce_samples', ctypes.c_uint32),
        ('availability_backoff_max_ms', ctypes.c_uint32),
        ('availability_auto_power_manage', ctypes.c_bool),
    ]


def sims_root():
    for candidate in CANDIDATE_ROOTS:
        path = os.path.expanduser(candidate)
        if os.path.isdir(path):
            return path
    return None


def _prism_path():
    root = sims_root()
    if root:
        candidate = os.path.join(root, 'Mods', 'prism.dll')
        if os.path.isfile(candidate):
            return candidate
    local = os.path.join(HERE, 'prism.dll')
    return local if os.path.isfile(local) else None


def start_speech():
    """Speak through whatever screen reader is running. False if none is."""
    global _prism, _backend
    if _prism is not None:
        return True
    path = _prism_path()
    if path is None:
        return False
    try:
        # Prism's C API is cdecl with UTF-8 char*, so CDLL, never WinDLL.
        lib = ctypes.CDLL(path)
        lib.prism_config_init.restype = PrismConfig
        lib.prism_init.restype = ctypes.c_void_p
        lib.prism_init.argtypes = [ctypes.POINTER(PrismConfig)]
        lib.prism_registry_acquire_best.restype = ctypes.c_void_p
        lib.prism_registry_acquire_best.argtypes = [ctypes.c_void_p]
        lib.prism_backend_initialize.restype = ctypes.c_int
        lib.prism_backend_initialize.argtypes = [ctypes.c_void_p]
        lib.prism_backend_speak.restype = ctypes.c_int
        lib.prism_backend_speak.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
                                            ctypes.c_bool]
        cfg = lib.prism_config_init()
        ctx = lib.prism_init(ctypes.byref(cfg))
        if not ctx:
            return False
        backend = lib.prism_registry_acquire_best(ctx)
        if not backend:
            return False
        code = lib.prism_backend_initialize(backend)
        # acquire_best already initialises, so "already initialized" is a
        # working backend rather than a failure.
        if code not in (PRISM_OK, PRISM_ALREADY_INITIALIZED):
            return False
        _prism, _backend = lib, backend
        return True
    except Exception:
        return False


def say(text, interrupt=False):
    """Speak it and print it. The console line is the fallback, always."""
    print(text)
    sys.stdout.flush()
    if _prism is None or _backend is None:
        return
    try:
        _prism.prism_backend_speak(_backend, text.encode('utf-8'),
                                   bool(interrupt))
    except Exception:
        pass


# --------------------------------------------------------------------- screen

def read_screen(window_title=GAME_WINDOW, save_png=None):
    """Every word on the game's window, with where to click it.

    Returns (words, error). Falls back to the whole screen when the window
    cannot be found, because a player whose game is on a second monitor should
    get a worse answer rather than no answer.
    """
    args = ['powershell.exe', '-ExecutionPolicy', 'Bypass', '-NoProfile',
            '-File', OCR_SCRIPT]
    if window_title:
        args += ['-WindowTitle', window_title]
    if save_png:
        args += ['-SavePng', save_png]
    try:
        raw = subprocess.check_output(args, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as ex:
        text = (ex.output or b'').decode('utf-8', 'replace')
        if 'window not found' in text and window_title:
            return read_screen(window_title=None, save_png=save_png)
        return [], text.strip()[:200] or 'the screen could not be read'
    except Exception as ex:
        return [], repr(ex)
    try:
        # strict=False because OCR happily reports control characters it found
        # in a texture, and one of those should not lose the whole screen.
        data = json.loads(raw.decode('utf-8', 'replace'), strict=False)
    except Exception as ex:
        return [], 'unreadable OCR output ({!r})'.format(ex)
    if isinstance(data, dict) and data.get('error'):
        return [], data['error']
    words = data.get('words') or []
    # One word on screen comes back as a dict rather than a list of one.
    if isinstance(words, dict):
        words = [words]
    global last_source
    last_source = ('the game window' if window_title
                   else 'the whole screen, not the game window')
    return words, None


def _norm(text):
    return ''.join(c for c in text.lower() if c.isalnum())


def _distance(a, b):
    """Edit distance, for OCR that reads Documents as Docurnents."""
    if a == b:
        return 0
    if not a or not b:
        return max(len(a), len(b))
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1,
                               previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def find_text(words, wanted, tolerance=None):
    """Where `wanted` is on screen, allowing for OCR noise.

    Matches a word or a whole line, so "New Game" is found even though OCR
    reports "New" and "Game" separately. Returns the best (x, y, text) or None.
    """
    target = _norm(wanted)
    if tolerance is None:
        # Roughly one wrong character per five, which covers rn/m and l/I
        # without letting "Continue" match "Options".
        tolerance = max(1, len(target) // 5)
    best = None
    for word in words:
        for field in ('text', 'line'):
            value = word.get(field)
            if not value:
                continue
            score = _distance(_norm(value), target)
            if score <= tolerance and (best is None or score < best[0]):
                best = (score, int(word['x']), int(word['y']), value)
    if best is None:
        return None
    return best[1], best[2], best[3]


# ---------------------------------------------------------------------- click

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [('dx', ctypes.c_long), ('dy', ctypes.c_long),
                ('mouseData', ctypes.c_ulong), ('dwFlags', ctypes.c_ulong),
                ('time', ctypes.c_ulong),
                ('dwExtraInfo', ctypes.POINTER(ctypes.c_ulong))]


class INPUT(ctypes.Structure):
    _fields_ = [('type', ctypes.c_ulong), ('mi', MOUSEINPUT)]


def click(x, y):
    """Move the pointer there and click. True if Windows accepted both events."""
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.SetCursorPos(int(x), int(y))
    down = INPUT(type=0, mi=MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, None))
    up = INPUT(type=0, mi=MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, None))
    sent = user32.SendInput(2, ctypes.byref((INPUT * 2)(down, up)),
                            ctypes.sizeof(INPUT))
    return sent == 2


def focus_game(window_title=GAME_WINDOW):
    """Bring the game forward, so the click lands on it and not on us."""
    try:
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        handle = user32.FindWindowW(None, window_title)
        if not handle:
            return False
        user32.SetForegroundWindow(handle)
        return True
    except Exception:
        return False
