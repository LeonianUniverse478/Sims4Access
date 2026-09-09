"""Choosing which save the game will open, from the main menu.

Loading a save is a client action: at the main menu there is no zone, no client
and no sim_info_manager, and PersistenceService has no load method at all. So a
script mod cannot open a save. What it CAN do is decide which one "Continue"
opens, because that is a file on disk - Slot_ffffffff.save is the slot the game
resumes from, and the numbered slots are the manual saves.

So this is a keyboard save picker: browse your saves, pick one, and the mod puts
it in the resume slot. Then Continue - one button, always in the same place -
opens it. That is one mouse action instead of navigating a save list by sight.

It runs with no lot loaded, which is the whole point, so it uses nothing from
the simulation: only the file system.

The chosen save is never modified. Only the resume slot is written, and the
resume slot is backed up before it is replaced.
"""
import os

import a11yscan_log as logfile

RESUME_SLOT = 'Slot_ffffffff.save'
BACKUP_SUFFIX = '.a11ybackup'

_saves = []
_index = 0
_active = False


def active():
    return _active


def _saves_dir():
    """The Sims 4 saves folder, found the same way the log finds its own file."""
    try:
        import a11yscan_speech as speech
        mods = speech._mods_dir()
        if mods:
            folder = os.path.join(os.path.dirname(mods), 'saves')
            if os.path.isdir(folder):
                return folder
    except Exception as ex:
        logfile.write('saves: could not locate via mods dir ({!r})'.format(ex))
    try:
        home = os.path.expanduser('~')
        for middle in (('OneDrive', 'Documents'), ('Documents',)):
            folder = os.path.join(home, *(middle + ('Electronic Arts',
                                                    'The Sims 4', 'saves')))
            if os.path.isdir(folder):
                return folder
    except Exception:
        pass
    return None


def _describe_time(path):
    try:
        import time
        stamp = os.path.getmtime(path)
        now = time.time()
        when = time.localtime(stamp)
        clock = time.strftime('%I:%M %p', when).lstrip('0')
        days = int((now - stamp) // 86400)
        if days <= 0:
            return 'today at {}'.format(clock)
        if days == 1:
            return 'yesterday at {}'.format(clock)
        if days < 7:
            return '{} days ago, {}'.format(days, clock)
        return time.strftime('%d %B', when).lstrip('0')
    except Exception:
        return 'unknown date'


def load():
    """Every save slot on disk, newest first."""
    global _saves, _index
    _saves = []
    _index = 0
    folder = _saves_dir()
    if not folder:
        logfile.fail('saves: could not find the saves folder')
        return 0
    try:
        names = os.listdir(folder)
    except Exception as ex:
        logfile.fail('saves: could not read {} ({!r})'.format(folder, ex))
        return 0
    for name in names:
        # Only the live slots: the .ver0/.day.ver1 files are the game's own
        # rolling backups and picking one would be a trap, not a feature.
        if not name.startswith('Slot_') or not name.endswith('.save'):
            continue
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        slot = name[len('Slot_'):-len('.save')]
        if slot.lower() == 'ffffffff':
            label = 'the game you were last playing'
        else:
            try:
                label = 'save {}'.format(int(slot, 16))
            except Exception:
                label = 'save {}'.format(slot)
        _saves.append({
            'name': name,
            'path': path,
            'label': label,
            'when': _describe_time(path),
            'is_resume': slot.lower() == 'ffffffff',
        })
    _saves.sort(key=lambda entry: os.path.getmtime(entry['path']), reverse=True)
    logfile.write('saves: {} slots in {}'.format(len(_saves), folder))
    return len(_saves)


def describe():
    if not _saves:
        return 'No saves found.'
    entry = _saves[_index % len(_saves)]
    return '{}, saved {}. {} of {}.'.format(
        entry['label'], entry['when'], _index % len(_saves) + 1, len(_saves))


def open_picker():
    global _active
    count = load()
    if not count:
        return 'No saves found. The log has where I looked.'
    _active = True
    return ('Choose a save. Up and down to browse, enter to pick it, '
            'backspace to stop. {}'.format(describe()))


def close_picker():
    global _active
    _active = False
    return 'Save picker closed.'


def next_save(step=1):
    global _index
    if not _saves:
        return 'No saves found.'
    _index = (_index + step) % len(_saves)
    return describe()


def choose():
    """Make the game resume from the save under the cursor.

    Copies it over the resume slot, after backing that slot up. The save you
    picked is only ever read.
    """
    if not _saves:
        return 'No saves found.'
    entry = _saves[_index % len(_saves)]
    if entry['is_resume']:
        return ('That is already the game Continue will open. Press Continue '
                'on the main menu.')
    folder = os.path.dirname(entry['path'])
    resume = os.path.join(folder, RESUME_SLOT)
    try:
        import shutil
        if os.path.isfile(resume):
            backup = resume + BACKUP_SUFFIX
            shutil.copy2(resume, backup)
            logfile.write('saves: backed up the resume slot to {}'.format(
                os.path.basename(backup)))
        shutil.copy2(entry['path'], resume)
    except Exception as ex:
        logfile.fail('saves: could not set the resume slot ({!r})'.format(ex))
        return 'Could not set that save. The log has the reason.'
    logfile.ok('saves: {} is now what Continue will open'.format(entry['name']))
    close_picker()
    return ('{} is ready. Press Continue on the main menu to play it.'.format(
        entry['label']))


def restore():
    """Put back the resume slot we replaced, if someone changes their mind."""
    folder = _saves_dir()
    if not folder:
        return 'Could not find the saves folder.'
    resume = os.path.join(folder, RESUME_SLOT)
    backup = resume + BACKUP_SUFFIX
    if not os.path.isfile(backup):
        return 'There is no backup to put back.'
    try:
        import shutil
        shutil.copy2(backup, resume)
    except Exception as ex:
        logfile.fail('saves: restore failed ({!r})'.format(ex))
        return 'Could not put it back.'
    logfile.ok('saves: resume slot restored from backup')
    return 'Put back the game you were last playing.'
