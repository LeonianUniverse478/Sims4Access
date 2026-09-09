"""Speech output.

Everything goes through Prism (github.com/ethindp/prism), a screen-reader
bridge: it speaks through whatever reader the player already runs, at their own
voice and rate, and the same code path covers Windows, macOS and Linux. The mod
ships a prebuilt prism.dll; other platforms need the matching library beside it.

Order of preference:
  1. prism.dll / libprism.dylib / libprism.so   - the bridge, all platforms
  2. Tolk.dll                                   - older Windows-only bridge
  3. tyjokr_a11y_speech.speak                   - filters by source
  4. console print                              - never silently lose text

Every attempt is recorded so a11y2.diag can show exactly what happened.
"""
import os

import a11yscan_log as logfile

# Files known to live in the Mods folder, used to find it by walking up from
# this module. This used to be the NVDA client; that file is gone, so the
# marker is now the mod's own data table, which always ships.
MODS_MARKERS = ('a11yscan_names.bin', 'prism.dll', 'Tolk.dll')

_backend = None
_attempts = []

_tolk = None
_tyjokr = None
_last_text = ''


def log(message):
    try:
        print('[a11yscan] {}'.format(message))
    except Exception:
        pass
    try:
        logfile.write(message)
    except Exception:
        pass


def _note(name, result):
    _attempts.append('{}: {}'.format(name, result))


def _mods_dir():
    """Walk up from this module's archive to the Mods folder holding the DLLs."""
    try:
        path = __file__
        for _ in range(6):
            parent = os.path.dirname(path)
            if not parent or parent == path:
                break
            path = parent
            for marker in MODS_MARKERS:
                if os.path.isfile(os.path.join(path, marker)):
                    return path
    except Exception as ex:
        _note('mods folder', 'walk failed {!r}'.format(ex))
    return None


# Prism ships no prebuilt binaries, so these are the names a player would end
# up with after building it themselves, per platform.
PRISM_NAMES = {
    'win32': ('prism.dll', 'libprism.dll'),
    'darwin': ('libprism.dylib', 'prism.dylib'),
}
PRISM_DEFAULT = ('libprism.so', 'prism.so')

PRISM_OK = 0
# prism_registry_acquire_best already initialises the backend it hands back,
# so prism_backend_initialize answers "already initialized" on a perfectly
# good one. Treating that as a failure would reject the working case.
PRISM_ALREADY_INITIALIZED = 15

_prism = None
_prism_ctx = None
_prism_backend = None


def platform_name():
    import sys
    return getattr(sys, 'platform', 'unknown')


def _load_native(path):
    """Load a shared library the way this platform expects.

    Prism's C API uses the default calling convention and UTF-8 strings, so
    CDLL is right on every platform. WinDLL is stdcall and does not exist off
    Windows at all - using it was what made this module Windows-only.
    """
    import ctypes
    if platform_name() == 'win32' and hasattr(ctypes, 'WinDLL'):
        # NVDA's client and Tolk are stdcall, so they still want WinDLL.
        return ctypes.CDLL(path)
    return ctypes.CDLL(path)


def _prism_library(mods):
    names = PRISM_NAMES.get(platform_name(), PRISM_DEFAULT)
    for name in names:
        candidate = os.path.join(mods, name)
        if os.path.isfile(candidate):
            return candidate
    return None


def _prism_config_type():
    import ctypes

    class PrismConfig(ctypes.Structure):
        # Straight from include/prism.h. Layout matters: prism_config_init
        # returns this by value and prism_init takes a pointer to it.
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

    return PrismConfig


def _prism_error(lib, code):
    try:
        text = lib.prism_error_string(code)
        return text.decode('utf-8', 'replace') if text else str(code)
    except Exception:
        return str(code)


def _try_prism(mods):
    """Speak through whatever screen reader is actually running."""
    global _prism, _prism_ctx, _prism_backend
    if not mods:
        _note('prism', 'no Mods folder to look in')
        return False
    lib_path = _prism_library(mods)
    if lib_path is None:
        _note('prism', 'library not present')
        return False
    try:
        import ctypes
        lib = _load_native(lib_path)
        PrismConfig = _prism_config_type()

        lib.prism_config_init.restype = PrismConfig
        lib.prism_config_init.argtypes = []
        lib.prism_init.restype = ctypes.c_void_p
        lib.prism_init.argtypes = [ctypes.POINTER(PrismConfig)]
        lib.prism_registry_acquire_best.restype = ctypes.c_void_p
        lib.prism_registry_acquire_best.argtypes = [ctypes.c_void_p]
        lib.prism_backend_initialize.restype = ctypes.c_int
        lib.prism_backend_initialize.argtypes = [ctypes.c_void_p]
        lib.prism_backend_speak.restype = ctypes.c_int
        lib.prism_backend_speak.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
                                            ctypes.c_bool]
        lib.prism_backend_stop.restype = ctypes.c_int
        lib.prism_backend_stop.argtypes = [ctypes.c_void_p]
        lib.prism_backend_name.restype = ctypes.c_char_p
        lib.prism_backend_name.argtypes = [ctypes.c_void_p]
        lib.prism_error_string.restype = ctypes.c_char_p
        lib.prism_error_string.argtypes = [ctypes.c_int]
    except Exception as ex:
        _note('prism', 'could not bind {} ({!r})'.format(
            os.path.basename(lib_path), ex))
        return False

    try:
        cfg = lib.prism_config_init()
        ctx = lib.prism_init(ctypes.byref(cfg))
        if not ctx:
            _note('prism', 'prism_init returned nothing')
            return False
        # "Best" is the reader that is actually running. Asking for it rather
        # than naming one is the whole point of a bridge.
        backend = lib.prism_registry_acquire_best(ctx)
        if not backend:
            lib.prism_shutdown(ctypes.c_void_p(ctx))
            _note('prism', 'no screen reader available to speak through')
            return False
        code = lib.prism_backend_initialize(backend)
        if code not in (PRISM_OK, PRISM_ALREADY_INITIALIZED):
            _note('prism', 'backend would not start ({})'.format(
                _prism_error(lib, code)))
            return False
        try:
            name = lib.prism_backend_name(backend)
            reader = name.decode('utf-8', 'replace') if name else 'unknown'
        except Exception:
            reader = 'unknown'
        _prism = lib
        _prism_ctx = ctx
        _prism_backend = backend
        _note('prism', 'OK, speaking through {}'.format(reader))
        logfile.write('prism: {} via {}'.format(
            reader, os.path.basename(lib_path)))
        return True
    except Exception as ex:
        _note('prism', 'setup failed ({!r})'.format(ex))
        return False


def _prism_speak(text, interrupt):
    if _prism is None or _prism_backend is None:
        return False
    try:
        code = _prism.prism_backend_speak(_prism_backend,
                                          text.encode('utf-8'),
                                          bool(interrupt))
        if code == PRISM_OK:
            return True
        log('prism speak refused ({})'.format(_prism_error(_prism, code)))
    except Exception as ex:
        log('prism speak failed ({!r})'.format(ex))
    return False


def _try_tolk(mods):
    global _tolk
    dll = os.path.join(mods, 'Tolk.dll')
    if not os.path.isfile(dll):
        _note('tolk', 'dll not present')
        return False
    if platform_name() != 'win32':
        _note('tolk', 'Windows only, skipped on {}'.format(platform_name()))
        return False
    try:
        import ctypes
        # Tolk loads sibling client DLLs, which are found via PATH, not via
        # Tolk's own folder, so make sure the Mods folder is searchable first.
        if mods not in os.environ.get('PATH', ''):
            os.environ['PATH'] = mods + os.pathsep + os.environ.get('PATH', '')
        lib = ctypes.WinDLL(dll)
        lib.Tolk_Load()
        lib.Tolk_Output.argtypes = [ctypes.c_wchar_p, ctypes.c_bool]
        lib.Tolk_Output.restype = ctypes.c_bool
        _tolk = lib
        _note('tolk', 'OK')
        return True
    except Exception as ex:
        _note('tolk', 'failed {!r}'.format(ex))
        return False


def _try_tyjokr():
    global _tyjokr
    try:
        import tyjokr_a11y_speech as mod
        if hasattr(mod, 'speak'):
            _tyjokr = mod
            _note('tyjokr', 'available (may filter by mode/source)')
            return True
        _note('tyjokr', 'module present but no speak()')
    except Exception as ex:
        _note('tyjokr', 'not importable {!r}'.format(ex))
    return False


def _init():
    global _backend
    if _backend is not None:
        return
    _backend = 'console'
    mods = _mods_dir()
    _note('mods folder', mods or 'NOT FOUND')
    if mods:
        # NVDA first on Windows: it is what ships with the mod and what most
        # players already run. Prism comes next - it covers macOS and Linux,
        # and other readers on Windows - and is skipped entirely when its
        # library is not present, which is the normal case today.
        if _try_prism(mods):
            _backend = 'prism'
        elif _try_tolk(mods):
            _backend = 'tolk'
    if _backend == 'console' and _try_tyjokr():
        _backend = 'tyjokr'


def backend():
    _init()
    return _backend


def standalone():
    """(is_standalone, [things still borrowed from another mod])."""
    _init()
    borrowed = []
    if _backend == 'tyjokr':
        borrowed.append("speech routed through tyjokr's mod")
    elif _backend == 'tolk':
        # Not something we ship: Tolk means another mod's copy is doing the
        # talking, which is worth saying out loud in the diagnostics.
        borrowed.append("using Tolk.dll from another mod")
    elif _backend == 'console':
        borrowed.append('no speech backend at all')
    try:
        import ctypes
        origin = getattr(ctypes, '__file__', '') or ''
        if 'a11yscan' not in origin.lower() and 'tyjokr' in origin.lower():
            borrowed.append('ctypes loaded from tyjokr archive')
    except Exception:
        borrowed.append('ctypes unavailable')
    return (not borrowed, borrowed)


def probe():
    """Human-readable log of every backend attempt, for diagnostics."""
    _init()
    return list(_attempts)


def speak(text, interrupt=True):
    global _last_text
    if not text:
        return
    text = str(text)
    _last_text = text
    _init()

    if _prism is not None and _prism_speak(text, interrupt):
        return

    if _tolk is not None:
        try:
            import ctypes
            if _tolk.Tolk_Output(ctypes.c_wchar_p(text), bool(interrupt)):
                return
        except Exception as ex:
            log('tolk speak failed ({!r})'.format(ex))

    if _tyjokr is not None:
        for call in (lambda: _tyjokr.speak(text, explicit=True),
                     lambda: _tyjokr.speak(text)):
            try:
                call()
                return
            except Exception:
                continue

    log(text)


def last():
    return _last_text
