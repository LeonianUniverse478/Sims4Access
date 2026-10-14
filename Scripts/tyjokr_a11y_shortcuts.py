"""Spoken help generated from the keyboard module's live binding tables.

Imported lazily by the hub/scanner: importing help must not start key threads.
Key combinations live in keys.py; this module supplies their spoken meanings.
"""
import tyjokr_a11y_lang as lang
import tyjokr_a11y_settings as settings
import tyjokr_a11y_speech as speech

CHORD_LABELS = {
    'prev': 'previous item at this scanner level; move up in the grid or Build cursor',
    'next': 'next item at this scanner level; move down in the grid or Build cursor',
    'prevcat': 'back to the parent scanner group; move left in the grid or Build cursor',
    'nextcat': 'open the selected scanner group; move right in the grid or Build cursor',
    'prevsub': 'previous scanner subcategory; grid floor up',
    'nextsub': 'next scanner subcategory; grid floor down',
    'open': 'open a scanner group or the interactions of an object; describe a grid point; select or place with the Build cursor',
    'back': 'back or close; leave the grid; cancel the Build tool',
    'rescan': 'rescan objects; describe the grid point',
    'where': 'read location or cursor position',
    'repeat': 'read again or stop; read the grid or Build cursor position',
    'help': 'open the accessibility menu',
    'phone': 'open a waiting call or text; with Simplified menus and nothing waiting, the phone list',
    'clock': 'read the day and time, with Paused while the game is paused',
    'mood': 'read mood and moodlets',
    'wants': 'read wants and fears',
    'logging': 'turn diagnostic logging on or off (TS4_Access.log next to the mod)',
    'events': 'running events: end one, or send all its guests home',
    'milestones': "the active Sim's milestones by category (Growing Together)",
    'values': "the active Sim's character values (Parenthood)",
    'queue': 'open the action queue: hear what the active Sim is doing and waiting to do, and cancel actions',
    'buildtoggle': 'toggle the Build cursor',
    'buildplace': 'Build placement on the lot grid: Control Alt Enter places the object chosen in the Build catalog',
    'gridtoggle': 'toggle the read-only lot grid',
    'rotateleft': 'rotate the last placed object left, or rotate with the Build cursor',
    'rotateright': 'rotate the last placed object right, or rotate with the Build cursor',
    'undo': 'undo the last placement, or undo in Build mode',
    'redo': 'redo in Build mode',
    'sell': 'sell the object on the grid point (press twice)',
    'buildgrid': 'aim the Build cursor at the grid point without placing',
    'scannermode': 'scanner mode on or off (saved): plain arrows browse the scanner and never move the camera; Right opens a group, Left or Backspace goes back, Enter acts, Space repeats',
}
# Chords that do nothing while Build controls are off.
BUILD_INTENTS = frozenset(('buildplace', 'sell', 'gridtoggle', 'rotateleft', 'rotateright',
                           'undo', 'redo', 'buildgrid'))
EXTRA_LABELS = {'A11yRepeat': 'read again or stop', 'A11yDismiss': 'back or close'}
KEY_LABELS = {0x08: 'Backspace', 0x09: 'Tab', 0x0D: 'Enter', 0x1B: 'Escape',
              0x20: 'Space', 0x21: 'Page Up', 0x22: 'Page Down',
              0xDB: 'left bracket', 0xDD: 'right bracket', 0x6E: 'Numpad decimal'}


def key_name(vk, keyboard):
    if vk in KEY_LABELS:
        return lang.t(KEY_LABELS[vk])
    if 0x60 <= vk <= 0x69:
        return '{} {}'.format(lang.t('Numpad'), vk - 0x60)
    name = keyboard.CHORD_NAMES.get(vk)
    if name is None:
        name = next((label for label, code in settings.KEY_NAMES.items() if code == vk), None)
    if name is None:
        name = chr(vk) if 0x30 <= vk <= 0x5A else 'key {}'.format(vk)
    return lang.t(name)


def chord_label(intent):
    if intent.startswith('sim') and intent[3:].isdigit():
        return lang.t('shortcut household sim').format(int(intent[3:]))
    # New intents are still enumerated, even before their prose is added.
    label = lang.t(CHORD_LABELS.get(intent, intent))
    if intent in BUILD_INTENTS and not settings.get('build_controls'):
        label += ' ({})'.format(lang.t('off in settings'))
    return label


def sections(keyboard=None, numpad=None):
    """Return complete sections; never cache a user's optional key settings."""
    if keyboard is None:
        import tyjokr_a11y_keys as keyboard
    if numpad is None:
        numpad = settings.get('numpad_navigation', False)
    ordinary = []
    for _message, (label, combos) in keyboard.BINDINGS.items():
        for vk, alt in combos:
            combo = ('{} + '.format(lang.t('Alt')) if alt else '') + key_name(vk, keyboard)
            ordinary.append('{}: {}'.format(combo, lang.t(label)))
    # These modifier variants are implemented by _plain_message, not BINDINGS.
    ordinary.append(lang.t('shortcut shift tab'))
    if settings.get('simplified_menus', True):
        ordinary.append(lang.t('shortcut simplified'))
    ordinary.append(lang.t('shortcut needs'))
    chords = ['{} + {} + {}: {}'.format(lang.t('Control'), lang.t('Alt'),
              key_name(vk, keyboard), chord_label(intent))
              for vk, (intent, _repeat) in keyboard.CHORDS.items()]
    result = [(lang.t('shortcut controls'), ordinary),
              (lang.t('shortcut chords'), chords)]
    if numpad:
        rows = []
        for vk, message in keyboard.NUMPAD_BINDINGS.items():
            label = (keyboard.BINDINGS[message][0] if message in keyboard.BINDINGS
                     else EXTRA_LABELS.get(message, message))
            rows.append('{}: {}'.format(key_name(vk, keyboard), lang.t(label)))
        result.append((lang.t('shortcut numpad'), rows))
    return result


def readout():
    parts = [lang.t('keyboard shortcuts'), lang.t('shortcut context')]
    for heading, rows in sections():
        parts.append(heading)
        parts.extend(rows)
    return '. '.join(part.rstrip('. ') for part in parts) + '.'


def speak():
    # One explicit utterance: separate calls would interrupt each other.
    speech.speak(readout(), explicit=True)
    return True
