"""Where the Flash build scripts find their tools, inputs and outputs.

Every location comes from an environment variable first; otherwise the first
default that exists on this machine is used. A missing tool stops the build
with a message naming the variable to set. No path here names a user folder.

  TS4_JAVA           full path of java.exe (JDK 11 or newer; 21.0.11 tested)
  TS4_FFDEC          full path of ffdec.jar (FFDec 26.2.1 tested)
  TS4_INSTALL        The Sims 4 install folder, the one holding Data\\Client
  TS4_FFDEC_HELPERS  folder holding ReplaceScriptsBatch.class and
                     ExportPcodeBatch.class (default: <project>\\build)

The DBPF reader is the project's own copy in tools\\vendor\\dbpf_extract.py.
flash_config.ps1 mirrors the tool lookups for the PowerShell scripts; keep
the two default lists identical.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(ROOT, 'build')
VENDOR = os.path.join(ROOT, 'tools', 'vendor')

JAVA_DEFAULTS = (r'C:\Tools\jdk21\jdk-21.0.11+10\bin\java.exe',)
FFDEC_DEFAULTS = (r'C:\Tools\ffdec\ffdec.jar',)
INSTALL_DEFAULTS = (
    r'C:\Program Files\EA Games\The Sims 4',
    r'C:\Program Files (x86)\Origin Games\The Sims 4',
    r'C:\Program Files (x86)\Steam\steamapps\common\The Sims 4',
    r'C:\Program Files\Steam\steamapps\common\The Sims 4',
)
# The EA app (and the older Origin installer) record the install folder here.
_INSTALL_KEYS = (r'SOFTWARE\Maxis\The Sims 4', r'SOFTWARE\WOW6432Node\Maxis\The Sims 4')


def _stop(message):
    sys.exit('flash_config: ' + message)


def _file(env, defaults, what):
    value = os.environ.get(env, '').strip().strip('"')
    if value:
        if not os.path.isfile(value):
            _stop('{} is set to "{}", which is not a file. It must be the full path of {}.'.format(env, value, what))
        return value
    for candidate in defaults:
        if os.path.isfile(candidate):
            return candidate
    _stop('{} not found. Set {} to its full path.'.format(what, env))


def java():
    return _file('TS4_JAVA', JAVA_DEFAULTS, 'java.exe (JDK 11 or newer)')


def ffdec():
    return _file('TS4_FFDEC', FFDEC_DEFAULTS, 'ffdec.jar (FFDec 26.2.1)')


def _registry_installs():
    try:
        import winreg
    except ImportError:
        return []
    found = []
    for key_path in _INSTALL_KEYS:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                value, _kind = winreg.QueryValueEx(key, 'Install Dir')
        except OSError:
            continue
        if value:
            found.append(value.rstrip('\\/'))
    return found


def install():
    """The game folder; its Data\\Client\\UI.package holds EA's original movies."""
    value = os.environ.get('TS4_INSTALL', '').strip().strip('"')
    if value:
        if not os.path.isfile(os.path.join(value, 'Data', 'Client', 'UI.package')):
            _stop('TS4_INSTALL is set to "{}", which has no Data\\Client\\UI.package.'.format(value))
        return value
    for candidate in _registry_installs() + list(INSTALL_DEFAULTS):
        if os.path.isfile(os.path.join(candidate, 'Data', 'Client', 'UI.package')):
            return candidate
    _stop('The Sims 4 install folder was not found. Set TS4_INSTALL to the folder that holds Data\\Client.')


def ui_package():
    return os.path.join(install(), 'Data', 'Client', 'UI.package')


def helpers():
    """Folder expected to hold the compiled FFDec batch helpers."""
    value = os.environ.get('TS4_FFDEC_HELPERS', '').strip().strip('"')
    return value or BUILD


def dbpf():
    """The vendored DBPF reader module (read_index, read_resource_bytes)."""
    if not os.path.isfile(os.path.join(VENDOR, 'dbpf_extract.py')):
        _stop('missing {}; the Flash build reads packages with it.'.format(
            os.path.join(VENDOR, 'dbpf_extract.py')))
    if VENDOR not in sys.path:
        sys.path.insert(0, VENDOR)
    import dbpf_extract
    return dbpf_extract


def output(argument, default_name):
    """An explicit output path, else <project>\\build\\<default_name>.

    Builds never write into a Mods folder: the game may hold the file open,
    and a half-written package there is what a player would load. Build here,
    then copy with the game closed."""
    path = os.path.abspath(argument if argument else os.path.join(BUILD, default_name))
    parts = [part.lower() for part in os.path.normpath(path).split(os.sep)]
    if 'mods' in parts[:-1]:
        _stop('refusing to write {} inside a Mods folder; build to a local folder and copy it with the game closed.'.format(path))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path
