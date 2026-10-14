"""Persistent options for the Screen Reader mod.

Stored as a hand-editable, commented INI file (tyjokr_ScreenReader.cfg)
next to the ts4script, MCCC-style. Values are friendly words (on/off, key
names) rather than raw numbers. The in-game a11y.* commands write through
immediately; a11y.reload applies a hand-edit while the game runs; deleting
the file resets everything. The file is fully regenerated on every write,
so user-added comments are not preserved.

This module deliberately imports nothing from the rest of the mod so any
module can import it without cycles. Load problems are collected in
`load_errors` for the narrator to surface instead of raising: a broken
settings file must never take down the mod.

Adding an option: default in DEFAULTS, a line + mapping in _TEMPLATE and
_FILE_MAP, read it at the apply site (get()), persist from its command
(set()), and a line in a11y.settings' readout.
"""
import configparser
import os

DEFAULTS = {
    'sim_actions': False,     # announce what the active Sim starts doing
    'object_names': True,     # name tooltips on gameplay objects
    'numpad_navigation': False,  # optional alternate keyboard layout
    'keyboard': True,         # keyboard focus navigation
    'scanner': True,          # Ctrl+Alt world scanner (Sims and objects on the lot)
    'captions': False,        # on-screen copy of accepted narration
    'startup': True,          # speech (and keyboard) at the main menu and CAS before a save loads
    'travel_list': True,      # keyboard mode answers travel requests from a world/place list instead of the map
    'build_controls': False,  # experimental Build cursor, Build actions window and lot grid
    'scanner_mode': False,    # plain arrows browse the scanner; arrows never move the camera
    'braille_mode': 'concise',  # concise | full | only | off
    'logging': False,         # mod-debugging log
    'speech_mode': 'hover',   # hover | manual | beeps | off
    'auto_focus': False,      # focus ring seizes new pie menus/dialogs
    'tooltip_delay': 1.5,     # seconds to hold back a data row's description
                              # (needs/skills/mood read name+value at once);
                              # 0 = read descriptions immediately
    'sapi_rate': 1,           # SAPI fallback voice only: -10..10
    'sapi_volume': 70,        # SAPI fallback voice only: 0..100
    'sapi_voice': 'zira',     # fallback voice, case-insensitive partial name
}

# Friendly key names for the cfg file and a11y.keybind (single source; the
# keyboard module imports this).
KEY_NAMES = {
    'numpad0': 0x60, 'numpad1': 0x61, 'numpad2': 0x62, 'numpad3': 0x63,
    'numpad4': 0x64, 'numpad5': 0x65, 'numpad6': 0x66, 'numpad7': 0x67,
    'numpad8': 0x68, 'numpad9': 0x69, 'numpadplus': 0x6B, 'numpadminus': 0x6D,
    'numpadstar': 0x6A, 'numpadslash': 0x6F, 'numpaddot': 0x6E,
    'left': 0x25, 'up': 0x26, 'right': 0x27, 'down': 0x28,
    'insert': 0x2D, 'delete': 0x2E, 'backslash': 0xDC, 'backtick': 0xC0,
    'semicolon': 0xBA, 'quote': 0xDE, 'comma': 0xBC, 'period': 0xBE,
    'slash': 0xBF, 'minus': 0xBD, 'equals': 0xBB,
    'tab': 0x09, 'enter': 0x0D, 'escape': 0x1B, 'space': 0x20,
}
# file (section, option) -> internal key, for plain values
_FILE_MAP = {
    ('features', 'sim actions'): 'sim_actions',
    ('features', 'object names'): 'object_names',
    ('features', 'keyboard'): 'keyboard',
    ('features', 'numpad navigation'): 'numpad_navigation',
    ('features', 'scanner'): 'scanner',
    ('features', 'captions'): 'captions',
    ('features', 'startup speech'): 'startup',
    ('features', 'travel list'): 'travel_list',
    ('features', 'build controls'): 'build_controls',
    ('features', 'scanner mode'): 'scanner_mode',
    ('speech', 'mode'): 'speech_mode',
    ('speech', 'braille'): 'braille_mode',
    ('speech', 'logging'): 'logging',
    ('speech', 'tooltip delay'): 'tooltip_delay',
    ('voice', 'rate'): 'sapi_rate',
    ('voice', 'volume'): 'sapi_volume',
    ('voice', 'name'): 'sapi_voice',
    ('behavior', 'auto focus'): 'auto_focus',   # legacy: still read, no longer written
}
_BOOL_KEYS = ('numpad_navigation', 'sim_actions', 'object_names', 'keyboard', 'scanner',
              'captions', 'startup', 'travel_list', 'build_controls',
              'scanner_mode', 'logging', 'auto_focus')

_TEMPLATE = """# Screen Reader options. Edit in any text editor, then type a11y.reload in
# the cheat console (or restart the game). Delete this file to reset.

[features]
# Keyboard navigation of menus, dialogs and panels (on/off)
keyboard = {keyboard}
# Enable the world scanner: Sims and objects on the lot (required for Scanner mode) (on/off)
scanner = {scanner}
# Scanner mode, Live mode only: plain arrows browse the scanner instead of moving
# the camera, and the camera follows the active Sim. Ctrl+Alt+Space switches it (on/off)
scanner mode = {scanner_mode}
# With the keyboard, choose travel destinations from a list, not the map (on/off)
travel list = {travel_list}
# Read the names of objects under the mouse (on/off)
object names = {object_names}
# Say what the active Sim starts doing (on/off)
sim actions = {sim_actions}
# Show narration as on-screen captions (on/off)
captions = {captions}
# Speech and keyboard at the main menu and in Create a Sim (on/off)
startup speech = {startup}
# Numpad 4 and 6 move, 5 activates, 8 repeats, decimal goes back (on/off)
numpad navigation = {numpad_navigation}
# Experimental Build cursor, Build actions window and lot grid (on/off)
build controls = {build_controls}

[speech]
# hover, manual, beeps or off
mode = {speech_mode}
# concise, full, only or off
braille = {braille_mode}
# Seconds before a long description is read (0 reads it at once)
tooltip delay = {tooltip_delay}
# Diagnostic log next to the mod (on/off)
logging = {logging}

[voice]
# Windows voice, used only when no screen reader is running.
# rate -10 to 10
rate = {sapi_rate}
# volume 0 to 100
volume = {sapi_volume}
# david, zira or hazel
name = {sapi_voice}
"""


def _mods_folder():
    # __file__ lives inside the ts4script zip: <Mods>/.../<name>.ts4script/...
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
PATH = os.path.join(MODS_FOLDER, 'tyjokr_ScreenReader.cfg')
# Only auto-create the file when actually running from inside the game's
# ts4script zip; importing this module from plain source (the build script)
# must stay side-effect free.
_IN_GAME = '.ts4script' in os.path.normpath(__file__).lower()

_stored = {}
load_errors = []
# True when no settings file existed at launch (first install, or reset).
# Retained for future onboarding; the automatic settings popup is deferred.
first_run = False

_TRUE_WORDS = ('on', 'true', 'yes', '1')
_FALSE_WORDS = ('off', 'false', 'no', '0')


def _parse_bool(raw, option):
    low = raw.strip().lower()
    if low in _TRUE_WORDS:
        return True
    if low in _FALSE_WORDS:
        return False
    load_errors.append('"{}" is not on/off for {}; keeping default'.format(raw, option))
    return None


def _apply_value(key, raw):
    """Parse one cfg value into _stored; empty means 'leave unset'."""
    raw = raw.strip()
    if '\n' in raw or '\r' in raw:
        # An accidentally indented line below this option was glued onto its
        # value by INI continuation rules; recover the first line and say so.
        first = raw.splitlines()[0].strip()
        load_errors.append(
            '{} had an extra indented line glued to it; using "{}"'.format(key, first))
        raw = first
    if not raw:
        return
    if key in _BOOL_KEYS:
        value = _parse_bool(raw, key)
        if value is not None:
            _stored[key] = value
        return
    if key == 'speech_mode':
        mode = raw.lower().replace('-', '_').replace(' ', '_')
        # legacy names from earlier builds
        if mode == 'talk':
            mode = 'hover'
        elif mode in ('ondemand', 'on_demand'):
            mode = 'manual'
        if mode in ('hover', 'manual', 'beeps', 'off'):
            _stored[key] = mode
        else:
            load_errors.append('unknown speech mode "{}"; keeping default'.format(raw))
        return
    if key == 'braille_mode':
        mode = raw.lower()
        if mode in ('concise', 'full', 'only', 'off'):
            _stored[key] = mode
        else:
            load_errors.append('unknown braille mode "{}"; keeping default'.format(raw))
        return
    if key == 'tooltip_delay':
        try:
            value = float(raw)
        except ValueError:
            load_errors.append(
                'tooltip delay must be a number of seconds, not "{}"'.format(raw))
            return
        _stored[key] = max(0.0, min(10.0, value))
        return
    if key in ('sapi_rate', 'sapi_volume'):
        try:
            value = int(raw)
        except ValueError:
            load_errors.append('{} must be a number, not "{}"'.format(key, raw))
            return
        if key == 'sapi_rate':
            _stored[key] = max(-10, min(10, value))
        else:
            _stored[key] = max(0, min(100, value))
        return
    _stored[key] = raw   # sapi_voice: free text


def _load_cfg():
    """Forgiving parse: strict=False tolerates duplicate lines (last wins), a
    ParsingError keeps everything that DID parse and only skips the bad lines
    (reported with line numbers), and section/option names are matched after
    collapsing case and stray spaces."""
    parser = configparser.ConfigParser(
        inline_comment_prefixes=(';', '#'), interpolation=None,
        strict=False, empty_lines_in_values=False)
    try:
        with open(PATH, 'r', encoding='utf-8') as handle:
            try:
                parser.read_file(handle)
            except configparser.ParsingError as ex:
                for lineno, line in getattr(ex, 'errors', []):
                    load_errors.append(
                        'line {} is not "option = value" and was skipped: {}'.format(
                            lineno, line))
    except Exception as ex:
        load_errors.append('settings file unreadable ({!r}); using defaults'.format(ex))
        return
    normalized = {}
    for section in parser.sections():
        sec_key = ' '.join(section.lower().split())
        for option, value in parser.items(section):
            opt_key = ' '.join(option.lower().split())
            normalized[(sec_key, opt_key)] = value
    for (section, option), key in _FILE_MAP.items():
        if (section, option) in normalized:
            _apply_value(key, normalized[(section, option)])


def _load():
    if os.path.isfile(PATH):
        _load_cfg()
        return
    # A default copy ships in the release zip; if the user deleted it (or a
    # dev build never had one), materialize it on launch so there is always
    # a file to edit in the mod folder.
    if _IN_GAME:
        global first_run
        first_run = True
        _save()


def _fmt_seconds(value):
    """Render a seconds value without a trailing .0 (the file is meant to be
    read and hand-edited)."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number == int(number):
        return str(int(number))
    return '{:g}'.format(number)


def _render(stored):
    """Render the cfg content for a given stored-values dict (pure; the
    build script uses render_default() to ship a pristine copy in the zip)."""
    def sget(name):
        return stored[name] if name in stored else DEFAULTS.get(name)
    fields = {
        'sim_actions': 'on' if sget('sim_actions') else 'off',
        'object_names': 'on' if sget('object_names') else 'off',
        'numpad_navigation': 'on' if sget('numpad_navigation') else 'off',
        'keyboard': 'on' if sget('keyboard') else 'off',
        'scanner': 'on' if sget('scanner') else 'off',
        'captions': 'on' if sget('captions') else 'off',
        'startup': 'on' if sget('startup') else 'off',
        'travel_list': 'on' if sget('travel_list') else 'off',
        'build_controls': 'on' if sget('build_controls') else 'off',
        'scanner_mode': 'on' if sget('scanner_mode') else 'off',
        'speech_mode': str(sget('speech_mode')),
        'braille_mode': sget('braille_mode'),
        'logging': 'on' if sget('logging') else 'off',
        'sapi_rate': sget('sapi_rate'),
        'sapi_volume': sget('sapi_volume'),
        'sapi_voice': sget('sapi_voice') or '',
        'tooltip_delay': _fmt_seconds(sget('tooltip_delay')),
    }
    return _TEMPLATE.format(**fields)


def render_default():
    return _render({})


def _save():
    try:
        content = _render(_stored)
        # Temp name ends in .cfg (ModGuard whitelist) rather than .tmp, so
        # the atomic write stays legal even on exotic user paths that happen
        # to contain one of ModGuard's prohibited substrings.
        tmp = PATH[:-len('.cfg')] + '.tmp.cfg'
        with open(tmp, 'w', encoding='utf-8') as handle:
            handle.write(content)
        os.replace(tmp, PATH)
        return True
    except Exception as ex:
        # Log only (per user decision, no audible warning). MCCC's most-
        # reported settings failure is this exact class: OneDrive write-
        # permission errors on the Mods folder.
        try:
            import tyjokr_a11y_speech as speech
            speech.log_line('settings: save failed: {!r}'.format(ex))
        except Exception:
            pass
        return False


def get(name, fallback=None):
    """Stored value if present, else the given fallback (lets a build supply
    its own default, e.g. release logging), else the DEFAULTS entry."""
    if name in _stored:
        return _stored[name]
    if fallback is not None:
        return fallback
    return DEFAULTS.get(name)


def set(name, value):
    _stored[name] = value
    return _save()


def reload():
    """Re-read the cfg (for a11y.reload after a hand-edit)."""
    global _stored
    del load_errors[:]
    _stored = {}
    _load()
    return True


_load()
