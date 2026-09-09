"""Typing text anywhere, not just in Create-a-Sim.

The Sim builder grew its own typing support because naming a Sim needed it,
and that left every other text box in the game unreachable: the mod could
answer a text-input dialog, but only by sending back whatever was already in
the field. Renaming a Sim on the age-up screen, or filling in anything else a
mod puts in front of you, was not possible.

This is the same idea with the field made generic. Whoever starts the entry
says what the field is called, what is in it now, and what to do with the
result; nothing here knows or cares whether that is a dialog, a menu, or
something not written yet.

Speaking each character back matters more than it looks. There is no cursor to
watch, so the only way to know a key registered is to hear it.
"""
import a11yscan_log as logfile

MAX_LENGTH = 60

_field = None
_label = ''
_text = ''
_original = ''
_on_accept = None


def active():
    return _field is not None


def field():
    return _field


def typed():
    return _text


def start(field_key, label, initial, on_accept):
    """Begin entry. on_accept(text) is called with the final value."""
    global _field, _label, _text, _original, _on_accept
    _field = field_key
    _label = label or 'field'
    _original = initial or ''
    _text = ''
    _on_accept = on_accept
    logfile.write('typing: editing {!r}, currently {!r}'.format(
        _label, _original))
    return ('Type the {}. It currently says {}. Letters, digits and space, '
            'backspace to rub out, enter when done, escape to leave it '
            'alone.'.format(_label, _original or 'nothing'))


def character(char):
    global _text
    if _field is None:
        return None
    if len(_text) >= MAX_LENGTH:
        return 'That is long enough.'
    _text += char
    return char if char != ' ' else 'space'


def backspace():
    global _text
    if _field is None:
        return None
    if not _text:
        return 'Empty.'
    removed = _text[-1]
    _text = _text[:-1]
    return 'deleted {}, {}'.format(
        'space' if removed == ' ' else removed, _text or 'empty')


def accept():
    """Keep what was typed. Typing nothing leaves the field as it was."""
    global _field, _text, _on_accept
    text = _text.strip()
    label = _label
    callback = _on_accept
    original = _original
    _field = None
    _text = ''
    _on_accept = None
    if not text:
        return 'Nothing typed, {} stays as {}.'.format(
            label, original or 'it was')
    if callback is not None:
        try:
            spoken = callback(text)
        except Exception as ex:
            logfile.fail('typing: {} could not be set ({!r})'.format(label, ex))
            return 'Could not set the {}.'.format(label)
        if spoken:
            return spoken
    logfile.write('typing: {} set to {!r}'.format(label, text))
    return '{} is now {}.'.format(label, text)


def cancel():
    global _field, _text, _on_accept
    label = _label
    _field = None
    _text = ''
    _on_accept = None
    return 'Left the {} alone.'.format(label)
