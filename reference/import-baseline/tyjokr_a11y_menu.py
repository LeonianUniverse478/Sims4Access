"""Visual settings window, opened with a11y.menu [window|open|close].

Pick a row to cycle its value and persist/apply it immediately. Numeric
values wrap at their maximum so every supported value remains reachable.
Scanner chords always belong to the scanner. The old a11y.scanview command
is retained as a diagnostic; captions are the narration display.
First-install automatic opening is deferred by the user (2026-09-15).
"""
import sims4.commands

import tyjokr_a11y_lang as lang
import tyjokr_a11y_pump as pump
import tyjokr_a11y_settings as settings
import tyjokr_a11y_speech as speech



class Row(object):
    __slots__ = ('key', 'kind', 'term', 'choices', 'lo', 'hi', 'step', 'help')

    def __init__(self, key, kind, term, choices=(), lo=0, hi=0, step=1, help=''):
        self.key = key
        self.kind = kind          # bool | choice | number | voice | action
        self.term = term          # tyjokr_a11y_lang term for the label
        self.choices = choices
        self.lo = lo
        self.hi = hi
        self.step = step
        self.help = help          # settings-window description (visual only)


ROWS = [
    Row('speech_mode', 'choice', 'speech mode', choices=('hover', 'manual', 'beeps', 'off'),
        help='hover speaks what the pointer touches; manual reads only on the read key; beeps; off'),
    Row('braille_mode', 'choice', 'braille mode', choices=('concise', 'full', 'only', 'off'),
        help='concise: speak everything, braille the label; full; only: braille only; off'),
    Row('keyboard', 'bool', 'keyboard navigation',
        help='Tab, arrows, Enter, Space and Escape; opening a panel pulls focus inside'),
    Row('numpad_navigation', 'bool', 'numpad navigation',
        help='optional numpad 4/6 navigation, 5 activate, 8 repeat, decimal back'),
    Row('scanner', 'bool', 'scanner',
        help='Ctrl+Alt scanner: browse the Sims and objects on the lot'),
    Row('object_names', 'bool', 'object names',
        help='name tooltips on plain objects'),
    Row('sim_actions', 'bool', 'sim actions',
        help='announce what the active Sim starts doing'),
    Row('tooltip_delay', 'number', 'tooltip delay', lo=0.0, hi=10.0, step=0.5,
        help='seconds before a long description is read; 0 reads it at once'),
    Row('captions', 'bool', 'captions',
        help='show narration as an on-screen caption'),
    Row('startup', 'bool', 'startup speech',
        help='speech and keyboard at the main menu and Create a Sim before a save loads; applies at the next launch'),
    Row('travel_list', 'bool', 'travel list',
        help='with keyboard navigation on, choose travel destinations from a world and place list; the map stays one row away'),
    Row('scanner_mode', 'bool', 'scanner mode',
        help='plain arrows browse the scanner and never move the camera; Control Alt Space toggles'),
    Row('build_controls', 'bool', 'build controls',
        help='experimental: keyboard Build cursor, Build actions window and read-only lot grid'),
    Row('logging', 'bool', 'logging',
        help='diagnostic log next to the ts4script'),
    Row('sapi_rate', 'number', 'voice rate', lo=-10, hi=10, step=1,
        help='Windows voice only (no screen reader running): -10 to 10'),
    Row('sapi_volume', 'number', 'voice volume', lo=0, hi=100, step=5,
        help='Windows voice only: 0 to 100'),
    Row('sapi_voice', 'voice', 'voice name',
        help='Windows voice only: one of the installed voices'),
    Row('reload', 'action', 'reload settings file', help='re-read tyjokr_ScreenReader.cfg after a hand edit'),
    Row('close', 'action', 'close menu', help='close this window'),
]
_SETTING_ROWS = [row for row in ROWS if row.kind != 'action']

_index = 0
_visual_id = None          # settings window dialog id
_scan_visual_id = None     # scanner window dialog id
_voices = None             # cached installed-voice list
_picker_factory = None
_text_picker_factory = None


def is_open():
    return _visual_id is not None


# ------------------------------------------------------------------ values

def _keys():
    import tyjokr_a11y_keys as keys
    return keys


def _value(row):
    key = row.key
    try:
        if key == 'speech_mode':
            return speech.speech_mode
        if key == 'braille_mode':
            return speech.braille_mode
        if key == 'keyboard':
            return bool(_keys()._enabled)
        if key == 'object_names':
            import tyjokr_a11y_objectnames as objectnames
            return bool(objectnames._enabled)
        if key == 'logging':
            return bool(speech.log_enabled)
    except Exception:
        pass
    value = settings.get(key)
    if row.kind == 'bool':
        return bool(value)
    if row.kind == 'voice':
        return str(value or 'default')
    return value


def _value_text(row):
    value = _value(row)
    if row.kind == 'bool':
        return lang.t('on') if value else lang.t('off')
    if row.key == 'tooltip_delay':
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = 0.0
        if number <= 0:
            return lang.t('off')
        return '{:g} {}'.format(number, lang.t('seconds'))
    return str(value)


def _label(row):
    return lang.t(row.term)


def _apply(row, value):
    """Set one option live and persist it (the same paths the a11y.*
    commands use). Simulation thread."""
    key = row.key
    if key == 'speech_mode':
        speech.speech_mode = value
        settings.set(key, value)
        speech.log_line('speech mode -> {} (menu)'.format(value))
    elif key == 'braille_mode':
        speech.braille_mode = value
        settings.set(key, value)
    elif key == 'keyboard':
        keys = _keys()
        keys._enabled = bool(value)
        keys._send('A11yKeyboardOn' if value else 'A11yKeyboardOff')
        settings.set(key, bool(value))
        if value:
            keys.start()
    elif key == 'auto_focus':
        settings.set(key, bool(value))
        import tyjokr_a11y_narrator as narrator
        narrator._push_autofocus()
    elif key == 'captions':
        settings.set(key, bool(value))
        if not value:
            speech.clear_caption()
    elif key == 'startup':
        settings.set(key, bool(value))
    elif key == 'travel_list':
        settings.set(key, bool(value))
        try:
            import tyjokr_a11y_travel as travel
            travel.apply_setting()
        except Exception as ex:
            speech.log_line('menu: travel setting notice failed: {!r}'.format(ex))
    elif key == 'scanner_mode':
        try:
            _keys().set_scanner_mode(bool(value))
        except Exception as ex:
            speech.log_line('menu: scanner mode failed: {!r}'.format(ex))
    elif key == 'build_controls':
        settings.set(key, bool(value))
        try:
            import tyjokr_a11y_build as build
            build.apply_setting()
        except Exception as ex:
            speech.log_line('menu: build controls notice failed: {!r}'.format(ex))
    elif key == 'scanner':
        settings.set(key, bool(value))
        if value:
            _keys().start_swallow()
    elif key == 'object_names':
        settings.set(key, bool(value))
        import tyjokr_a11y_objectnames as objectnames
        objectnames.enable(bool(value))
    elif key == 'logging':
        if value:
            speech.log_enabled = True
            settings.set(key, True)
            speech.log_line('logging enabled via the settings menu')
        else:
            speech.log_line('logging disabled via the settings menu')
            speech.log_enabled = False
            settings.set(key, False)
    elif key in ('sapi_rate', 'sapi_volume'):
        settings.set(key, int(value))
        speech.restart_sapi()
    elif key == 'sapi_voice':
        settings.set(key, str(value))
        speech.restart_sapi()
    elif key == 'tooltip_delay':
        settings.set(key, float(value))
    else:
        settings.set(key, bool(value) if row.kind == 'bool' else value)


def _voice_list():
    global _voices
    if _voices is None:
        try:
            _voices = list(speech.list_voices())
        except Exception:
            _voices = []
        if not _voices:
            _voices = ['david', 'zira', 'hazel']
    return _voices


def _change(row, direction):
    """Step the value. Returns True when something changed."""
    if row.kind == 'bool':
        _apply(row, not _value(row))
        return True
    if row.kind == 'choice':
        current = _value(row)
        choices = list(row.choices)
        index = choices.index(current) if current in choices else 0
        _apply(row, choices[(index + direction) % len(choices)])
        return True
    if row.kind == 'number':
        try:
            current = float(_value(row))
        except (TypeError, ValueError):
            current = 0.0
        value = current + direction * row.step
        if value > row.hi:
            value = row.lo
        elif value < row.lo:
            value = row.hi
        if row.key == 'tooltip_delay':
            value = round(value, 1)
        else:
            value = int(round(value))
        if value == current:
            return False
        _apply(row, value)
        return True
    if row.kind == 'voice':
        names = _voice_list()
        current = str(_value(row)).lower()
        index = -1
        for position, name in enumerate(names):
            if current and (current in name.lower() or name.lower() in current):
                index = position
                break
        _apply(row, names[(index + direction) % len(names)])
        return True
    return False


# ------------------------------------------------------------------ speaking

def _say(text):
    speech.speak(text, explicit=True)


def _open_menu():
    """Simulation thread: show only the visual settings window."""
    global _index
    _index = 0
    return _show_settings_window()


def _close():
    global _visual_id
    _cancel_dialog(_visual_id)
    _visual_id = None
    speech.log_line('menu: closed')


def _toggle():
    if is_open():
        _close()
    else:
        _open_menu()


def _enter(row):
    if row.kind == 'action':
        return _run_action(row)
    return _change(row, 1)


def _run_action(row):
    key = row.key
    if key == 'reload':
        settings.reload()
        for setting_row in _SETTING_ROWS:
            try:
                _apply(setting_row, settings.get(setting_row.key))
            except Exception as ex:
                speech.log_line('menu: reload apply {} failed: {!r}'.format(setting_row.key, ex))
        try:
            speech.retry_screen_reader()
        except Exception:
            pass
        warnings = list(settings.load_errors)
        text = lang.t('settings reloaded') + '.'
        if warnings:
            text += ' {} {}. {}'.format(len(warnings), 'warnings', ' '.join(warnings))
        speech.log_line(text)
        return True
    if key == 'close':
        _close()
        return False
    return False


# ------------------------------------------------------------------ dialogs

def _raw(text):
    from sims4.localization import LocalizationHelperTuning
    return LocalizationHelperTuning.get_raw_text(str(text))


def _ls_hash(key):
    """A LocalizedString for a string-table key the client will render."""
    try:
        from sims4.localization import _create_localized_string
        return _create_localized_string(int(key))
    except Exception:
        from protocolbuffers.Localization_pb2 import LocalizedString
        result = LocalizedString()
        result.hash = int(key)
        return result


def _join(*strings):
    """Comma-join LocalizedStrings; falls back to the first one."""
    strings = [s for s in strings if s is not None]
    if not strings:
        return None
    if len(strings) == 1:
        return strings[0]
    try:
        from sims4.localization import LocalizationHelperTuning
        return LocalizationHelperTuning.get_comma_separated_list(*strings)
    except Exception as ex:
        speech.log_line('menu: comma list failed: {!r}'.format(ex))
        return strings[0]


def _cancel_dialog(dialog_id):
    if not dialog_id:
        return
    try:
        import services
        services.ui_dialog_service().dialog_cancel(dialog_id)
    except Exception as ex:
        speech.log_line('menu: cancel dialog {} failed: {!r}'.format(dialog_id, ex))


def _picker(title, text, text_only=False):
    global _picker_factory, _text_picker_factory
    import services
    from ui.ui_dialog_picker import UiObjectPicker, UiItemPicker
    owner = services.get_active_sim()
    if owner is None:
        return None
    if text_only:
        # Item pickers carry BasePickerRow data. An ObjectPickerRow with no
        # definition still asks the client for a thumbnail of definition 0.
        if _text_picker_factory is None:
            _text_picker_factory = UiItemPicker.TunableFactory()
        return _text_picker_factory.default(
            owner,
            title=lambda *args, **kwargs: _raw(title),
            text=lambda *args, **kwargs: _raw(text),
            min_selectable=1, max_selectable=1)
    if _picker_factory is None:
        _picker_factory = UiObjectPicker.TunableFactory()
    return _picker_factory.default(
        owner,
        title=lambda *args, **kwargs: _raw(title),
        text=lambda *args, **kwargs: _raw(text),
        picker_type=UiObjectPicker.UiObjectPickerObjectPickerType.OBJECT,
        min_selectable=1, max_selectable=1)


def _show_settings_window():
    """Simulation thread. Replaces any earlier settings window."""
    global _visual_id
    _cancel_dialog(_visual_id)
    _visual_id = None
    try:
        from ui.ui_dialog_picker import BasePickerRow
        dialog = _picker(
            lang.t('settings menu'),
            'Pick a row to change it. Numbers cycle back to their minimum after the maximum. '
            'Open this window with a11y.menu window.', text_only=True)
        if dialog is None:
            speech.log_line('menu: no active Sim, settings window skipped')
            return False
        for position, row in enumerate(ROWS):
            if row.kind == 'action':
                name = _label(row)
            else:
                name = '{}: {}'.format(_label(row), _value_text(row))
            dialog.add_row(BasePickerRow(
                option_id=position, name=_raw(name), row_description=_raw(row.help),
                row_tooltip=None, icon=None, tag=position,
                is_selected=(position == _index % len(ROWS))))
        dialog.add_listener(_on_settings_pick)
        _keys().fence_opening_input()
        dialog.show_dialog()
        _visual_id = dialog.dialog_id
        return True
    except Exception as ex:
        speech.log_line('menu: settings window failed: {!r}'.format(ex))
        return False


def _on_settings_pick(dialog):
    """Picker reply (simulation thread)."""
    global _visual_id, _index
    if dialog.dialog_id != _visual_id:
        return          # a window we already replaced
    _visual_id = None
    if not dialog.accepted:
        return
    try:
        tags = list(dialog.get_result_tags())
    except Exception as ex:
        speech.log_line('menu: pick result failed: {!r}'.format(ex))
        return
    if not tags:
        return
    position = int(tags[0]) % len(ROWS)
    row = ROWS[position]
    _index = position
    if row.key == 'close':
        _close()
        return
    _enter(row)
    _show_settings_window()


def _show_scanner_window():
    """Simulation thread. What the scanner sees, one row per thing."""
    global _scan_visual_id
    _cancel_dialog(_scan_visual_id)
    _scan_visual_id = None
    try:
        import services
        import tyjokr_a11y_scanner as scanner
        from ui.ui_dialog_picker import ObjectPickerRow
        if not scanner.ensure_scan():
            _say(lang.t('nothing nearby'))
            return False
        groups, current_group, current_entry = scanner.snapshot()
        total = sum(len(entries) for _key, entries in groups)
        dialog = _picker(
            'Scanner',
            '{} things in {} categories around the active Sim. Pick a row to move the scanner there.'.format(
                total, len(groups)))
        if dialog is None:
            return False
        manager = services.object_manager()
        option = 0
        for group_key, entries in groups:
            subs = scanner.subs_in(entries)
            dialog.add_row(ObjectPickerRow(
                option_id=option, name=_ls_hash(scanner.label_hash(group_key)),
                row_description=_raw('{} items, {} subcategories{}'.format(
                    len(entries), len(subs), '  (current)' if group_key == current_group else '')),
                row_tooltip=None, icon=None, tag=('group', group_key)))
            option += 1
            for position, entry in enumerate(entries):
                name, icon_info = _entry_name(entry, manager)
                where = '{}. {} of {}'.format(scanner.place_text(entry), position + 1, len(entries))
                if entry is current_entry:
                    where = '>> ' + where
                if len(subs) > 1:
                    description = _join(_ls_hash(scanner.label_hash(entry.category)), _raw(where))
                else:
                    description = _raw(where)
                dialog.add_row(ObjectPickerRow(
                    option_id=option, name=name, row_description=description,
                    row_tooltip=None, icon=None, icon_info=icon_info,
                    tag=('item', group_key, entry.obj_id),
                    is_selected=(entry is current_entry)))
                option += 1
        dialog.add_listener(_on_scanner_pick)
        dialog.show_dialog()
        _scan_visual_id = dialog.dialog_id
        speech.log_line('menu: scanner window with {} rows'.format(option))
        return True
    except Exception as ex:
        speech.log_line('menu: scanner window failed: {!r}'.format(ex))
        return False


def _entry_name(entry, manager):
    """LocalizedString name (and an icon when the game has one) for a
    scanner entry."""
    from sims4.localization import LocalizationHelperTuning
    icon_info = None
    obj = None
    try:
        obj = manager.get(entry.obj_id)
    except Exception:
        obj = None
    if entry.is_sim:
        if entry.name:
            return _raw(entry.name), None
        if entry.name_hash:
            return _ls_hash(entry.name_hash), None
        return _raw('Sim'), None
    if obj is not None:
        try:
            from distributor.shared_messages import IconInfoData
            icon_info = IconInfoData(obj_instance=obj)
        except Exception:
            icon_info = None
        if entry.name:
            return _raw(entry.name), icon_info
        try:
            return LocalizationHelperTuning.get_object_name(obj), icon_info
        except Exception as ex:
            speech.log_line('menu: object name failed: {!r}'.format(ex))
    if entry.name:
        return _raw(entry.name), icon_info
    if entry.name_hash:
        return _ls_hash(entry.name_hash), icon_info
    return _raw('?'), icon_info


def _on_scanner_pick(dialog):
    global _scan_visual_id
    if dialog.dialog_id != _scan_visual_id:
        return
    _scan_visual_id = None
    if not dialog.accepted:
        return
    try:
        tags = list(dialog.get_result_tags())
    except Exception as ex:
        speech.log_line('menu: scanner pick failed: {!r}'.format(ex))
        return
    if not tags:
        return
    import tyjokr_a11y_scanner as scanner
    tag = tags[0]
    try:
        if tag[0] == 'group':
            scanner.select_group(tag[1])
        elif tag[0] == 'item':
            scanner.select_item(tag[1], tag[2])
    except Exception as ex:
        speech.log_line('menu: scanner select failed: {!r}'.format(ex))


# First-install popup deferred. Forget dialog ids when changing zones.
def _install_zone_hook():
    import zone
    original = zone.Zone.on_loading_screen_animation_finished

    def a11y_menu_on_loading_screen_animation_finished(self, *args, **kwargs):
        global _visual_id, _scan_visual_id
        result = original(self, *args, **kwargs)
        _visual_id = None
        _scan_visual_id = None
        return result

    zone.Zone.on_loading_screen_animation_finished = (
        a11y_menu_on_loading_screen_animation_finished)


# ------------------------------------------------------------------ commands

@sims4.commands.Command('a11y.menu', command_type=sims4.commands.CommandType.Live)
def a11y_menu(action: str = 'toggle', _connection=None):
    """a11y.menu [open|close|toggle|window] - visual settings."""
    output = sims4.commands.CheatOutput(_connection)
    action = action.lower()
    if action == 'open':
        _open_menu()
    elif action == 'close':
        _close()
    elif action == 'window':
        _show_settings_window()
    elif action == 'toggle':
        _toggle()
    else:
        output('Usage: a11y.menu [open|close|toggle|window]')
        return False
    output('a11y: settings window {} (row {} of {}), pump {}'.format(
        'open' if is_open() else 'closed', _index + 1, len(ROWS), pump.status()))
    return True


@sims4.commands.Command('a11y.scanview', command_type=sims4.commands.CommandType.Live)
def a11y_scanview(_connection=None):
    """Show the scanner window: what the scanner sees, with the cursor."""
    output = sims4.commands.CheatOutput(_connection)
    shown = _show_scanner_window()
    output('a11y: scanner window {}'.format('shown' if shown else 'not shown (see log)'))
    return True


try:
    _install_zone_hook()
except Exception as _zone_ex:
    speech.log_line('menu: zone hook install failed: {!r}'.format(_zone_ex))
