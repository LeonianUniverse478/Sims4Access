"""Mod menu census (logging only).

Script mods build their menus from EA's dialog classes (pickers, text
inputs, OK/Cancel dialogs, notifications); none of the mods surveyed on
2026-10-04 ships its own Flash. To learn which of those windows TS4 Access
reads and which stay silent, every dialog a mod shows is written to
TS4_Access.log while diagnostic logging is on (Ctrl+Alt+L), with the prefix
"modui:":

    modui: MC Command Center (mc_cmd_center.mc_ui) UiItemPicker
           title "MC Command Center" rows 12: "MC Settings" | "MC Cheats" | ...

The calling mod is the first stack frame outside EA's code
(T:\\InGame\\...) and outside TS4 Access. Text is the raw text a mod passes
(LocalizationHelperTuning.get_raw_text); string-table text is logged as its
key. The log's existing "UI owner:" and "SPEAK" lines show what the client
opened and what was read, so the two together show which windows need work.
Nothing is spoken and nothing changes the game.
"""
import sys

import tyjokr_a11y_speech as speech

_installed = False
EA_PREFIXES = ('T:\\InGame', 'T:/InGame', '<')
MAX_ROWS = 8


def _log(text):
    if speech.log_enabled:
        speech.log_line('modui: ' + text)


def _source():
    """(label, module) of the first mod frame that led to this dialog."""
    frame = sys._getframe(2)
    while frame is not None:
        module = frame.f_globals.get('__name__', '') or ''
        filename = frame.f_code.co_filename or ''
        if not filename.startswith(EA_PREFIXES) and not module.startswith('tyjokr_a11y') \
                and module not in ('sims4.commands', __name__):
            return module, filename
        frame = frame.f_back
    return None, None


def ls_text(value, depth=0):
    """Readable text of a LocalizedString proto: its raw-text tokens, or its key."""
    if value is None or depth > 3:
        return ''
    if isinstance(value, str):
        return value
    parts = []
    for token in getattr(value, 'tokens', ()) or ():
        raw = getattr(token, 'raw_text', '')
        if raw:
            parts.append(str(raw))
        nested = getattr(token, 'text_string', None)
        if nested is not None and getattr(nested, 'hash', 0):
            inner = ls_text(nested, depth + 1)
            if inner:
                parts.append(inner)
    if parts:
        return ' '.join(parts)
    key = getattr(value, 'hash', 0)
    return 'key 0x{:08X}'.format(key) if key else ''


def _rows(dialog):
    rows = list(getattr(dialog, 'picker_rows', None) or ())
    names = []
    for row in rows[:MAX_ROWS]:
        name = getattr(row, 'name', None)
        names.append(ls_text(name) or '?')
    return len(rows), names


def describe(dialog, msg):
    parts = [type(dialog).__name__]
    for field in ('title', 'text'):
        try:
            text = ls_text(getattr(msg, field, None)) if msg is not None and msg.HasField(field) else ''
        except Exception:
            text = ''
        if text:
            parts.append('{} "{}"'.format(field, text[:120]))
    count, names = _rows(dialog)
    if count:
        parts.append('rows {}: {}'.format(count, ' | '.join('"{}"'.format(n[:60]) for n in names)))
    inputs = getattr(dialog, 'text_inputs', None)
    if inputs:
        try:
            parts.append('text inputs {}'.format(sorted(inputs)))
        except Exception:
            pass
    picker_type = getattr(dialog, 'picker_type', None)
    if picker_type is not None:
        parts.append('picker_type {}'.format(getattr(picker_type, 'name', picker_type)))
    return ' '.join(parts)


def install():
    global _installed
    if _installed:
        return True
    _installed = True
    from ui.ui_dialog import UiDialog
    original = UiDialog.build_msg

    def build_msg(self, *args, **kwargs):
        msg = original(self, *args, **kwargs)
        if speech.log_enabled:
            try:
                module, filename = _source()
                if module is not None:
                    _log('{} ({}) {}'.format(module, filename, describe(self, msg)))
            except Exception as ex:
                _log('census failed: {!r}'.format(ex))
        return msg
    build_msg.__name__ = original.__name__
    UiDialog.build_msg = build_msg
    return True


try:
    install()
except Exception as _install_ex:
    speech.log_line('modui: install failed: {!r}'.format(_install_ex))
