"""Keyboard requests for EA's native Build cursor and transaction history.

Only the client performs placement. No object creation, funds adjustment,
footprint override, custom undo stack or synthetic success announcement.
The cursor uses screen coordinates, independently of the read-only lot grid.
"""
import time
import math
from urllib.parse import unquote

import sims4.commands
import tyjokr_a11y_lang as lang
import tyjokr_a11y_speech as speech

_active = False
_zone_id = None
_last_reply = 0.0
_serial = 0
_last_serial = 0
_pending = {}
_last_feedback = ''
_feedback_time = 0.0
_aim_pending = 0
_aim_until = 0.0
_release_serial = 0   # the 'off' sent when Build mode ended; its reply is silent
_log_window = 0.0     # client diagnostics burst window start
_log_count = 0
_LOG_BURST = 40       # lines per 5 s window; the rest are dropped with one notice
_installed = False

ACTIONS = frozenset(('on', 'off', 'toggle', 'left', 'right', 'up', 'down',
                     'click', 'cancel', 'rotateleft', 'rotateright', 'undo',
                     'redo', 'status', 'fine', 'coarse', 'center', 'grid'))
ALIASES = {'prev': 'up', 'next': 'down', 'prevcat': 'left',
           'nextcat': 'right', 'open': 'click', 'back': 'cancel',
           'repeat': 'status', 'where': 'status'}
# Actions an accessibility menu row may request. Opening that menu retires
# the native cursor (a modal is open), so the client re-enables it at its
# remembered position for this one explicit choice, under its own guards.
MENU_ACTIONS = frozenset(('left', 'right', 'up', 'down', 'click', 'cancel',
                          'rotateleft', 'rotateright', 'status', 'fine',
                          'coarse', 'center'))


def _text(en, pl):
    return pl if lang._detect_lang() == 'pl' else en


def _say(en, pl):
    speech.speak(_text(en, pl), explicit=True)


def controls_enabled():
    """The Build controls switch: the cursor, the Build actions window and
    the read-only lot grid. Off by default while the cursor is experimental;
    turning it off never blocks the release of a cursor already sent."""
    try:
        import tyjokr_a11y_settings as settings
        return bool(settings.get('build_controls', False))
    except Exception:
        return False


def refuse_disabled():
    _say('Build controls are off. Turn them on in the settings menu.',
         'Sterowanie budowaniem jest wyłączone. Włącz je w menu ustawień.')
    return False


def announce_controls():
    """Simulation thread: tell every live UI copy the current switch. New
    TooltipManager copies start with it off, so the keyboard heartbeat and
    each activation request send it again."""
    try:
        import distributor.ops
        import distributor.system
        distributor.system.Distributor.instance().add_op_with_no_owner(
            distributor.ops.SendUIMessage(
                'A11y|buildcontrols|' + ('on' if controls_enabled() else 'off')))
        return True
    except Exception as ex:
        speech.log_line('build: controls notice failed ({!r})'.format(ex))
        return False


def apply_setting():
    """The switch changed (settings menu or a11y.reload). Off retires the
    grid and any cursor or aim this session asked for, silently, before the
    client hears the new value."""
    global _active, _aim_pending, _zone_id, _release_serial
    if not controls_enabled():
        try:
            import tyjokr_a11y_grid as grid
            grid.retire()
        except Exception as ex:
            speech.log_line('build: grid retire failed ({!r})'.format(ex))
        if _active or _aim_pending or _pending or _zone_id is not None:
            _pending.clear()
            sent = request('off')
            _release_serial = _serial if sent else 0
        _active, _aim_pending, _zone_id = False, 0, None
    return announce_controls()


def _zone():
    try:
        import services
        zone = services.current_zone()
        return zone if zone is not None and zone.is_in_build_buy else None
    except Exception:
        return None


def active():
    """A client acknowledgement is required before rerouting scanner keys."""
    global _active
    zone = _zone()
    if zone is None or zone.id != _zone_id or not controls_enabled():
        _active = False
    return _active


def aiming():
    global _aim_pending
    zone = _zone()
    if _aim_pending and (zone is None or zone.id != _zone_id or time.monotonic() > _aim_until
                         or not controls_enabled()):
        _pending.pop(_aim_pending, None)
        _aim_pending = 0
    return bool(_aim_pending)


def on_key(intent):
    if aiming():
        return request('off') if intent in ('back', 'cancel', 'off') else False
    return request(ALIASES.get(intent, intent))


def toggle():
    return request('off' if active() else 'on')


def aim_grid():
    """Aim via native world-to-screen binding; never select/place automatically."""
    global _serial, _zone_id, _active, _last_serial, _last_feedback, _aim_pending, _aim_until
    if not controls_enabled():
        return refuse_disabled()
    import tyjokr_a11y_grid as grid
    zone = _zone()
    target = grid.cursor()
    if zone is None or target is None or target[2] != zone.id:
        _say('Choose a point on the lot grid in Build mode first.',
             'Najpierw wybierz punkt na siatce parceli w trybie budowania.')
        return False
    position, level, ident = target
    values = (float(position.x), float(position.y), float(position.z))
    if not all(math.isfinite(value) for value in values):
        return False
    import distributor.ops
    import distributor.system
    _serial += 1
    _zone_id, _active, _last_serial = ident, False, _serial
    _last_feedback = ''
    _pending.clear()
    _pending[_serial] = ident
    _aim_pending = _serial
    _aim_until = time.monotonic() + 2.5
    # This leaves the sampled point intact but stops grid key capture.
    grid.leave()
    announce_controls()
    distributor.system.Distributor.instance().add_op_with_no_owner(
        distributor.ops.SendUIMessage('A11y|buildaim|{}|{:.6f}|{:.6f}|{:.6f}|{}|{}'.format(
            _serial, values[0], values[1], values[2], level, ident)))
    return True


def request(action):
    """Simulation thread only; accepted means sent, never placed successfully."""
    global _serial, _zone_id, _active, _last_serial, _last_feedback, _aim_pending
    if action not in ACTIONS:
        return False
    if action != 'off' and not controls_enabled():
        return refuse_disabled()
    if action == 'toggle':
        return toggle()
    if action == 'grid':
        return aim_grid()
    zone = _zone()
    if zone is None and action != 'off':
        _active = False
        _say('Enter Build mode first.', 'Najpierw włącz tryb budowania.')
        return False
    if action not in ('on', 'off', 'undo', 'redo') and not active():
        _say('Build cursor is off.', 'Kursor budowania jest wyłączony.')
        return False
    if action == 'on':
        import tyjokr_a11y_grid as grid
        if grid.active():
            grid.leave()
    if action in ('on', 'off', 'left', 'right', 'up', 'down', 'center', 'click', 'cancel'):
        _last_feedback = ''
    import distributor.ops
    import distributor.system
    _serial += 1
    if action == 'off':
        _active = False
        _last_serial = _serial
        _aim_pending = 0
    if len(_pending) > 128:
        _pending.clear()
    _zone_id = zone.id if zone is not None else None
    _pending[_serial] = _zone_id
    if action == 'on':
        announce_controls()
    distributor.system.Distributor.instance().add_op_with_no_owner(
        distributor.ops.SendUIMessage('A11y|build|{}|{}'.format(action, _serial)))
    return True


def request_menu(action):
    """An explicit Build menu choice, sent after that window has closed.
    The client checks Build mode, the keyboard lease and every modal or
    editing guard itself, enables the native cursor where it was (the mouse
    position the first time in this Build session) and performs the one
    action. Nothing resumes on its own; an unknown action is refused here."""
    global _serial, _zone_id, _active, _last_feedback
    if action not in MENU_ACTIONS:
        return False
    if not controls_enabled():
        return refuse_disabled()
    zone = _zone()
    if zone is None:
        _active = False
        _say('Enter Build mode first.', 'Najpierw włącz tryb budowania.')
        return False
    import tyjokr_a11y_grid as grid
    if grid.active():
        grid.leave()
    if action in ('left', 'right', 'up', 'down', 'center', 'click', 'cancel'):
        _last_feedback = ''
    import distributor.ops
    import distributor.system
    _serial += 1
    if len(_pending) > 128:
        _pending.clear()
    _zone_id = zone.id
    _pending[_serial] = _zone_id
    announce_controls()
    distributor.system.Distributor.instance().add_op_with_no_owner(
        distributor.ops.SendUIMessage('A11y|build|menu:{}|{}'.format(action, _serial)))
    return True


def on_build_buy_exit():
    """Build mode ended. The client's Build UI can be torn down before its
    own per-frame guard released the native cursor, which would leave that
    cursor enabled in Live mode, so the release is forced from here as well:
    an ordinary 'off', accepted outside Build, answered by whichever UI
    instance is live. Sent only when this Build session made a request; its
    reply is not spoken."""
    global _release_serial, _zone_id, _active, _aim_pending
    if not (_active or _zone_id is not None):
        return False      # this Build session never asked for the cursor
    try:
        sent = request('off')
    except Exception as ex:
        speech.log_line('build: release on Build exit failed ({!r})'.format(ex))
        sent = False
    _release_serial = _serial if sent else 0
    _active, _aim_pending, _zone_id = False, 0, None
    speech.log_line('build: Build mode ended, cursor release {} (serial {})'.format(
        'sent' if sent else 'not sent', _serial))
    return sent


def install():
    """Register the Build exit release once; EA calls the exit callbacks
    from buildbuy_session_end on the simulation thread."""
    global _installed
    if _installed:
        return True
    import build_buy
    build_buy.register_build_buy_exit_callback(on_build_buy_exit)
    _installed = True
    return True


try:
    install()
except Exception as _install_ex:
    speech.log_line('build: exit release not installed: {!r}'.format(_install_ex))


@sims4.commands.Command('a11y.build', command_type=sims4.commands.CommandType.Live)
def command(action: str = 'toggle', _connection=None):
    return request(action.lower())


@sims4.commands.Command('a11y.buildinfo', command_type=sims4.commands.CommandType.Live)
def info(encoded: str = '', _connection=None):
    """Native localized hovered-object/error text; never infer placement success."""
    global _last_feedback, _feedback_time
    zone = _zone()
    if zone is None or zone.id != _zone_id or not controls_enabled():
        return False
    try:
        kind, payload = encoded.split('|', 1)
    except ValueError:
        return False
    if kind == 'clear':
        _last_feedback = ''
        return True
    if kind not in ('name', 'error'):
        return False
    text = unquote(payload).strip()
    if not text or len(text) > 6000:
        return False
    now = time.monotonic()
    if text == _last_feedback and now - _feedback_time < 1:
        return True
    _last_feedback, _feedback_time = text, now
    speech.speak(text, explicit=True)
    return True


@sims4.commands.Command('a11y.buildlog', command_type=sims4.commands.CommandType.Live)
def buildlog(encoded: str = '', _connection=None):
    """Client lifecycle diagnostics for the Build cursor and the catalog
    product memory: written to the log, never spoken, capped per window."""
    global _log_window, _log_count
    text = unquote(str(encoded)).strip()
    if not text or len(text) > 400:
        return False
    now = time.monotonic()
    if now - _log_window > 5:
        _log_window, _log_count = now, 0
    _log_count += 1
    if _log_count > _LOG_BURST:
        if _log_count == _LOG_BURST + 1:
            speech.log_line('build client: further lines dropped for this window')
        return False
    speech.log_line('build client: ' + text)
    return True


@sims4.commands.Command('a11y.buildstate', command_type=sims4.commands.CommandType.Live)
def state(encoded: str = '', _connection=None):
    """Client reply: serial|active|result|x|y|step. Coordinates are pixels."""
    global _active, _last_reply, _last_serial, _aim_pending, _release_serial
    try:
        fields = encoded.split('|')
        if len(fields) != 6:
            return False
        serial, flag = int(fields[0]), int(fields[1])
        if flag not in (0, 1) or (serial != 0 and serial not in _pending):
            return False
        if serial == 0 and flag != 0:
            return False
        result = fields[2]
        x, y, step = (int(value) for value in fields[3:])
        if min(x, y) < 0 or step not in (4, 16, 64):
            return False
    except (ValueError, TypeError):
        return False
    zone = _zone()
    if serial:
        expected_zone = _pending.pop(serial)
        if serial < _last_serial or (flag and (zone is None or zone.id != expected_zone)):
            return False
        _last_serial = serial
    else:
        # Automatic retirement wins over any older request still in flight.
        _last_serial = _serial
        _pending.clear()
    if flag and not controls_enabled():
        # The client turned a cursor on for a request sent before the switch
        # went off: never announce it; release it once, silently.
        _active, _aim_pending = False, 0
        _pending.clear()
        if request('off'):
            _release_serial = _serial
        _last_reply = time.monotonic()
        return True
    _active = bool(flag) and zone is not None
    if serial == 0 or serial == _aim_pending:
        _aim_pending = 0
    _last_reply = time.monotonic()
    if serial and serial == _release_serial and not flag:
        return True      # the Build-exit release: nothing to announce in Live mode
    replies = {
        'on': ('Build cursor on. Screen pixels, not lot tiles. ',
               'Kursor budowania włączony. Piksele ekranu, nie pola parceli. '),
        'off': ('Build cursor off.', 'Kursor budowania wyłączony.'),
        'blocked': ('Close the open dialog or text field first.',
                    'Najpierw zamknij otwarte okno lub pole tekstowe.'),
        'unavailable': ('Build cursor unavailable.', 'Kursor budowania niedostępny.'),
        'click': ('Select or place. ', 'Wybierz lub umieść. '),
        'cancel': ('Cancel Build tool.', 'Anuluj narzędzie budowania.'),
        'undo': ('Undo.', 'Cofnij.'),
        'redo': ('Redo.', 'Ponów.'),
        'rotateleft': ('Rotate left requested.', 'Wysłano polecenie obrotu w lewo.'),
        'rotateright': ('Rotate right requested.', 'Wysłano polecenie obrotu w prawo.'),
        'toolblocked': ('Choose the Select tool or an object from the catalog first.',
                        'Najpierw wybierz narzędzie zaznaczania lub obiekt z katalogu.'),
        'nohistory': ('Nothing to undo or redo.',
                      'Brak dostępnego wpisu w historii gry.'),
        'aim': ('Build cursor aimed at the grid point. Press Enter to select or place. ',
                'Kursor budowania ustawiony na rzucie punktu siatki. Naciśnij Enter, aby wybrać lub umieścić obiekt. '),
        'aimfailed': ('The grid point is not visible in the Build viewport. Adjust the camera or floor, then choose the grid point again.',
                      'Punkt siatki nie jest widoczny w oknie budowania. Zmień kamerę lub piętro, a następnie ponownie wybierz punkt.'),
    }
    if result in ('on', 'aim', 'move', 'status', 'fine', 'coarse', 'center', 'click'):
        prefix = _text(*replies[result]) if result in replies else ''
        feedback = ' ' + _last_feedback if _last_feedback and result in ('click', 'status') else ''
        _say(prefix + 'Screen x {}, y {}. Step {} pixels.'.format(x, y, step) + feedback,
             prefix + 'Ekran x {}, y {}. Krok {} pikseli.'.format(x, y, step) + feedback)
    elif result in replies:
        _say(*replies[result])
    return True
