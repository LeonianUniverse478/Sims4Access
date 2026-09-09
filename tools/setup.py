"""First-time setup for a11yscan, without needing to see the game.

Two things have to be true before a script mod runs at all, and both of them
live behind the Game Options screen - which is a client screen with nothing
behind it to read. That is a bootstrapping problem the mod cannot solve from
inside the game: it is not running yet.

They are plain lines in Options.ini, so this sets them from outside:

    scriptmodsenabled = 1     script mods run
    modsdisabled = 0          mods are not switched off wholesale

It also checks that the files that need to be in the Mods folder are there,
under the right names, and says what is missing.

Run it with the game CLOSED. The Sims 4 rewrites Options.ini when it exits, so
anything changed while it is running is thrown away.

    python setup.py            check and report, change nothing
    python setup.py --fix      make the changes
    python setup.py --fix --quiet-startup
                               also stop the "mods loaded" popup appearing at
                               every launch, which is one more unreadable
                               dialog between you and the game

Ordinary Python 3 - this does not run inside the game.
"""
import io
import os
import shutil
import sys

# Both of the places The Sims 4 keeps its user folder. OneDrive's Documents
# redirection moves it without telling anyone, and a setup tool that only
# knows one of them fails for exactly the people who need it.
CANDIDATE_ROOTS = (
    os.path.join('~', 'Documents', 'Electronic Arts', 'The Sims 4'),
    os.path.join('~', 'OneDrive', 'Documents', 'Electronic Arts',
                 'The Sims 4'),
)

REQUIRED_SETTINGS = (
    ('scriptmodsenabled', '1', 'script mods are allowed to run'),
    ('modsdisabled', '0', 'mods are not switched off wholesale'),
)
QUIET_STARTUP = ('showmodliststartup', '0',
                 'the "mods loaded" popup stays out of the way')

MOD_FILES = (
    ('a11yscan_Companion.ts4script', 'the mod itself'),
    ('a11yscan_names.bin', 'the string table, so things have names'),
    ('a11yscan_objects.bin', 'the object table'),
    ('prism.dll', 'speech, through whichever screen reader you run'),
)


def find_root():
    """The Sims 4 user folder, or None."""
    for candidate in CANDIDATE_ROOTS:
        path = os.path.expanduser(candidate)
        if os.path.isdir(path):
            return path
    return None


def read_settings(path):
    """Every `key = value` line, lowercased keys, in file order."""
    values = {}
    if not os.path.isfile(path):
        return values
    with io.open(path, encoding='utf-8', errors='replace') as handle:
        for line in handle:
            if '=' not in line:
                continue
            key, _sep, value = line.partition('=')
            values[key.strip().lower()] = value.strip()
    return values


def apply_settings(path, wanted):
    """Rewrite only the lines that need it, leaving the rest untouched."""
    with io.open(path, encoding='utf-8', errors='replace') as handle:
        lines = handle.readlines()
    remaining = dict(wanted)
    out = []
    for line in lines:
        key = line.partition('=')[0].strip().lower() if '=' in line else None
        if key in remaining:
            out.append(u'{} = {}\n'.format(key, remaining.pop(key)))
        else:
            out.append(line)
    # A setting the file never had still has to end up in it.
    for key, value in remaining.items():
        out.append(u'{} = {}\n'.format(key, value))
    backup = path + '.a11ybackup'
    if not os.path.exists(backup):
        shutil.copy2(path, backup)
        print('  kept a copy of your old settings as '
              '{}'.format(os.path.basename(backup)))
    with io.open(path, 'w', encoding='utf-8', newline='\n') as handle:
        handle.writelines(out)


def main(argv):
    fix = '--fix' in argv
    quiet = '--quiet-startup' in argv

    root = find_root()
    if root is None:
        print('Could not find your Sims 4 folder. It is normally at')
        for candidate in CANDIDATE_ROOTS:
            print('  {}'.format(os.path.expanduser(candidate)))
        return 1
    print('Sims 4 folder: {}'.format(root))

    options = os.path.join(root, 'Options.ini')
    if not os.path.isfile(options):
        print('No Options.ini yet - run the game once, quit, and try again.')
        return 1

    current = read_settings(options)
    wanted = {}
    checks = list(REQUIRED_SETTINGS)
    if quiet:
        checks.append(QUIET_STARTUP)
    print('')
    print('Settings:')
    for key, value, why in checks:
        have = current.get(key)
        if have == value:
            print('  OK    {} is {} - {}'.format(key, value, why))
        else:
            print('  WRONG {} is {}, should be {} - {}'.format(
                key, 'missing' if have is None else have, value, why))
            wanted[key] = value

    mods = os.path.join(root, 'Mods')
    print('')
    print('Mods folder: {}'.format(mods))
    missing = []
    for name, why in MOD_FILES:
        if os.path.isfile(os.path.join(mods, name)):
            print('  OK    {} - {}'.format(name, why))
        else:
            print('  MISSING {} - {}'.format(name, why))
            missing.append(name)

    print('')
    if wanted and fix:
        apply_settings(options, wanted)
        print('Settings fixed. Start the game.')
    elif wanted:
        print('Run this again with --fix to change those settings.')
        print('Close the game first: it rewrites Options.ini when it exits.')
    else:
        print('Settings are already right.')

    if missing:
        print('')
        print('Still to do: copy these into the Mods folder above:')
        for name in missing:
            print('  {}'.format(name))

    print('')
    print('Once the game is open:')
    print('  Ctrl+Alt+W  says where you are and what to press next.')
    print('  Ctrl+Alt+O  on the main menu, chooses which save Continue opens.')
    print('  Ctrl+Alt+O  on the world screen, chooses which family to play,')
    print('              and loads their lot for you.')
    print('  Ctrl+Alt+H  reads every key.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
