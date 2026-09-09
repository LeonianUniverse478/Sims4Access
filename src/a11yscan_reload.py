"""Reloading the mod without restarting the game.

Three things outlive a naive module reload and would otherwise pile up:

  * the keyboard polling thread,
  * the repeating real-time alarm that drains intents,
  * the wrappers we installed on the game's own dialog classes.

So a generation number is kept in builtins, where it survives module reloads.
Old threads and alarms notice their generation is stale and retire themselves,
and hook wrappers stash the original method on the class so it can be put back
before wrapping again. Without that, every reload would double every
announcement.

Two import caches must BOTH be cleared. zipimport caches the archive's
directory, and sys.path_importer_cache holds a zipimporter bound to the byte
offsets of the archive as it was. Clearing only the first leaves that importer
reading old offsets out of a new file, which fails as a truncated stream.

Finally, the old modules are kept aside rather than discarded, so a failed
reload can be rolled back instead of leaving the mod dead until a restart.
"""
import sys

import a11yscan_log as logfile

MODULE_PREFIX = 'a11yscan_'
ENTRY_MODULE = 'a11yscan_cmds'
ARCHIVE_MARKER = 'a11yscan'


def _builtins():
    import builtins
    return builtins


def generation():
    """Current generation. Anything older than this should retire."""
    return getattr(_builtins(), '_A11YSCAN_GENERATION', 0)


def set_generation(value):
    _builtins()._A11YSCAN_GENERATION = value
    return value


def bump_generation():
    return set_generation(generation() + 1)


def is_current(captured):
    return captured == generation()


def _clear_import_caches():
    """Both caches, or the importer keeps reading the previous archive."""
    cleared = []
    try:
        import zipimport
        cache = getattr(zipimport, '_zip_directory_cache', None)
        if cache is not None:
            for key in list(cache):
                if ARCHIVE_MARKER in key.lower():
                    del cache[key]
                    cleared.append('zip:' + key)
    except Exception as ex:
        logfile.write('reload: zipimport cache not cleared ({!r})'.format(ex))
    try:
        for key in list(sys.path_importer_cache):
            if ARCHIVE_MARKER in str(key).lower():
                del sys.path_importer_cache[key]
                cleared.append('path:' + str(key))
    except Exception as ex:
        logfile.write('reload: path importer cache not cleared ({!r})'.format(ex))
    try:
        import importlib
        importlib.invalidate_caches()
    except Exception as ex:
        logfile.write('reload: invalidate_caches failed ({!r})'.format(ex))
    logfile.write('reload: cleared {} cache entries'.format(len(cleared)))


def _shutdown_current():
    """Ask the running pieces to stop before their modules are set aside."""
    for name, attr in (('a11yscan_keys', 'stop'), ('a11yscan_pump', 'stop')):
        module = sys.modules.get(name)
        if module is None:
            continue
        try:
            getattr(module, attr)()
        except Exception as ex:
            logfile.write('reload: {}.{} failed ({!r})'.format(name, attr, ex))

    module = sys.modules.get('a11yscan_dialogs')
    if module is not None:
        try:
            module.uninstall()
        except Exception as ex:
            logfile.write('reload: dialog uninstall failed ({!r})'.format(ex))


def _take_modules():
    """Remove our modules from sys.modules but keep them for rollback."""
    saved = {}
    for name in list(sys.modules):
        if name.startswith(MODULE_PREFIX) and name != __name__:
            try:
                saved[name] = sys.modules.pop(name)
            except Exception:
                continue
    return saved


def _rollback(saved, previous_generation):
    """Put the previous build back and restart it."""
    sys.modules.update(saved)
    set_generation(previous_generation)
    entry = saved.get(ENTRY_MODULE)
    try:
        if entry is not None and hasattr(entry, 'start_everything'):
            entry.start_everything()
        logfile.write('reload: rolled back to generation {}'.format(
            previous_generation))
        return True
    except Exception as ex:
        logfile.fail('reload: rollback failed {!r}'.format(ex))
        return False


def reload_all():
    """Reload every module of this mod. Returns a spoken status string."""
    previous_generation = generation()
    new_generation = bump_generation()
    logfile.session('reload requested, generation {}'.format(new_generation))

    _shutdown_current()
    _clear_import_caches()
    saved = _take_modules()
    logfile.write('reload: set aside {} modules'.format(len(saved)))

    try:
        del sys.modules[__name__]
    except Exception:
        pass

    try:
        __import__(ENTRY_MODULE)
    except Exception as ex:
        logfile.fail('reload: re-import failed {!r}'.format(ex))
        sys.modules[__name__] = sys.modules.get(__name__) or None
        if _rollback(saved, previous_generation):
            return 'Reload failed, kept the previous version.'
        return 'Reload failed, restart the game.'

    module = sys.modules.get(ENTRY_MODULE)
    try:
        if module is not None and hasattr(module, 'start_everything'):
            module.start_everything()
    except Exception as ex:
        logfile.fail('reload: restart failed {!r}'.format(ex))
        if _rollback(saved, previous_generation):
            return 'Reload failed, kept the previous version.'
        return 'Reloaded, but could not restart. Restart the game.'

    logfile.ok('reload complete, generation {}'.format(new_generation))
    return 'Mod reloaded, generation {}.'.format(new_generation)


# ---------------------------------------------------------- build freshness

ARCHIVE = 'Sims4Access.ts4script'
_loaded_stamp = None
_announced_stamp = None


def _archive_path():
    try:
        import os
        import a11yscan_speech as speech
        mods = speech._mods_dir()
        if mods:
            return os.path.join(mods, ARCHIVE)
    except Exception:
        pass
    return None


def _archive_stamp():
    try:
        import os
        path = _archive_path()
        if path and os.path.isfile(path):
            return os.path.getmtime(path)
    except Exception:
        pass
    return None


def note_load():
    """Remember which build is actually running."""
    global _loaded_stamp, _announced_stamp
    _loaded_stamp = _archive_stamp()
    _announced_stamp = None
    logfile.write('build: running the archive as of {}'.format(_loaded_stamp))


def newer_build_waiting():
    """True when a newer .ts4script is on disk than the one we loaded.

    Testing a fix that was never loaded wastes a whole round and looks exactly
    like the fix not working, which has now happened twice. The mod knows the
    archive's timestamp, so it can simply say so.
    """
    global _announced_stamp
    if _loaded_stamp is None:
        return False
    stamp = _archive_stamp()
    if stamp is None or stamp <= _loaded_stamp:
        return False
    # Announce each NEW build, not just the first. A one-shot flag meant that
    # after the first warning every later build landed silently - and testing
    # a fix that was never loaded looks exactly like the fix not working.
    if _announced_stamp is not None and stamp <= _announced_stamp:
        return False
    _announced_stamp = stamp
    logfile.write('build: a newer archive is on disk ({} > {})'.format(
        stamp, _loaded_stamp))
    return True
