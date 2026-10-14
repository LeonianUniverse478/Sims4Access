"""Startup-only speech transport (V11): Flash writes, Python only listens.

Before a save loads there is no simulation for PostServerCommand to reach, so
the shared TooltipManager writes its narration lines to a loopback listener
owned by this module. Nothing is ever written back: the V10 request/response
protocol (challenge, config, navigation, ping) coincided with five native
crashes at boot, at the main menu and in CAS, and the only common factor was
inbound socket data being delivered into the Flash VM. Navigation keys before
a save loads are handled natively in Flash; this side just speaks.

Keyboard mode is signalled by the listening port: 45993 keyboard on, 45994
speech only. Loopback connections must belong to this game process. Only the
fixed narration/state channels are accepted; there is no command execution.
"""
from collections import deque
import functools
import os
import socket
import threading
import time

PORT_KEYBOARD = 45993
PORT_SPEECH = 45994
MAX_FRAME = 32768
MAX_QUEUE = 48
HELLO = 'HELLO|A11Y_STARTUP_V2'
CHANNELS = frozenset(('a11y.speak_enc', 'a11y.widget_enc', 'a11y.focus_enc',
    'a11y.widgetname_enc', 'a11y.dialog_enc', 'a11y.scope_enc', 'a11y.event_enc',
    'a11y.context_enc', 'a11y.inspect_enc', 'a11y.modalstate', 'a11y.inputfence',
    'a11y.stop', 'a11y.mark'))
_lock = threading.Lock()
_incoming = deque()
_thread = None
_stop = threading.Event()
_connected = False
_startup = True
_generation = 0
_next_tick = 0.0
_port = None
_flash_startup = False


def log(message):
    try:
        import tyjokr_a11y_speech as speech
        speech.log_line('startup: ' + message)
    except Exception:
        pass


def enabled():
    try:
        import tyjokr_a11y_settings as settings
        return bool(settings.get('startup', True))
    except Exception:
        return True


def listen_port():
    """The port tells Flash whether keyboard navigation is enabled."""
    try:
        import tyjokr_a11y_settings as settings
        keyboard = bool(settings.get('keyboard', True))
    except Exception:
        keyboard = True
    return PORT_KEYBOARD if keyboard else PORT_SPEECH


class FrameReader:
    def __init__(self):
        self.buffer = b''

    def feed(self, data):
        self.buffer += data
        lines = []
        while b'\n' in self.buffer:
            raw, self.buffer = self.buffer.split(b'\n', 1)
            if len(raw) > MAX_FRAME:
                raise ValueError('frame too long')
            line = raw.decode('utf-8')
            if '\x00' in line or '\r' in line:
                raise ValueError('invalid framing')
            lines.append(line)
        if len(self.buffer) > MAX_FRAME:
            raise ValueError('unfinished frame too long')
        return lines


def parse_hello(line):
    parts = line.split('|')
    if len(parts) < 2 or '|'.join(parts[:2]) != HELLO:
        return None
    return parts[2] if len(parts) > 2 else ''


def parse_post(line):
    parts = line.split('|', 2)
    if len(parts) != 3 or parts[0] != 'POST' or parts[1] not in CHANNELS:
        return None
    channel, payload = parts[1:]
    if channel == 'a11y.modalstate' and payload not in ('00', '01', '10', '11'):
        return None
    if channel == 'a11y.inputfence' and payload:
        return None
    return channel, payload


def same_process_peer(peer_port, listener_port=None):
    """Use the documented Windows TCP owner table, never game memory."""
    if listener_port is None:
        listener_port = _port or PORT_KEYBOARD
    try:
        import ctypes
        class Row(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulong) for name in
                        ('state', 'local_address', 'local_port',
                         'remote_address', 'remote_port', 'pid')]
        api = ctypes.WinDLL('iphlpapi').GetExtendedTcpTable
        api.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong),
                        ctypes.c_int, ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        api.restype = ctypes.c_ulong
        size = ctypes.c_ulong(0)
        result = api(None, ctypes.byref(size), False, 2, 5, 0)
        if result != 122 or size.value < 4 or size.value > 16 * 1024 * 1024:
            return False
        data = ctypes.create_string_buffer(size.value)
        if api(data, ctypes.byref(size), False, 2, 5, 0) != 0:
            return False
        count = ctypes.c_ulong.from_buffer(data).value
        if 4 + count * ctypes.sizeof(Row) > size.value:
            return False
        for index in range(count):
            row = Row.from_buffer(data, 4 + index * ctypes.sizeof(Row))
            if (row.pid == os.getpid()
                    and row.local_address == 0x0100007F
                    and row.remote_address == 0x0100007F
                    and socket.ntohs(row.local_port & 0xffff) == peer_port
                    and socket.ntohs(row.remote_port & 0xffff) == listener_port):
                return True
    except Exception:
        pass
    return False


def _is_mode_mark(channel, payload):
    return (channel == 'a11y.mark' and isinstance(payload, str)
            and payload.startswith('startup-v11-')
            and payload.endswith(('-active', '-idle', '-native')))


def note_mark(payload):
    """Flash reports its own mode: '...-active' while it owns the keys before
    a save loads, '...-idle' / '...-native' when the loaded-zone path is used.
    Flash is the source of truth so the poller can never double-drive."""
    global _flash_startup
    if not _is_mode_mark('a11y.mark', payload):
        return
    with _lock:
        _flash_startup = payload.endswith('-active')


def send_navigation(message_name):
    """Called from the key poller. True means the message is consumed here.

    While Flash reports startup mode it handles the navigation keys natively
    through its input-action guards, so the poller's message is deliberately
    dropped rather than posted to a pump that has no zone. Otherwise the
    native distributor path is used and this returns False.
    """
    if not isinstance(message_name, str):
        return False
    # Explicit read-only diagnostic commands have no native key equivalent.
    # Let the simulation pump deliver these on travel maps with a loaded zone.
    if message_name == 'A11yInspect':
        return False
    with _lock:
        return _connected and _flash_startup


def _dispatch(channel, payload):
    import tyjokr_a11y_narrator as narrator
    if channel == 'a11y.modalstate':
        import tyjokr_a11y_keys as keys
        keys.a11y_modalstate(payload)
    elif channel == 'a11y.inputfence':
        import tyjokr_a11y_keys as keys
        keys.a11y_inputfence()
    elif channel == 'a11y.mark':
        note_mark(payload)
        log('shared UI ready: ' + payload[:100])
    else:
        handlers = {
            'a11y.speak_enc': narrator.a11y_speak_enc,
            'a11y.widget_enc': narrator.a11y_widget_enc,
            'a11y.focus_enc': narrator.a11y_focus_enc,
            'a11y.widgetname_enc': narrator.a11y_widgetname_enc,
            'a11y.dialog_enc': narrator.a11y_dialog_enc,
            'a11y.scope_enc': narrator.a11y_scope_enc,
            'a11y.event_enc': narrator.a11y_event_enc,
            'a11y.context_enc': narrator.a11y_context_enc,
            'a11y.inspect_enc': narrator.a11y_inspect_enc,
            'a11y.stop': narrator.a11y_stop,
        }
        handler = handlers.get(channel)
        if handler is not None:
            handler(payload)


def tick():
    """Called only by the game's core.on_tick, which also runs pre-zone."""
    global _startup, _next_tick
    if time.monotonic() < _next_tick:
        return
    _next_tick = time.monotonic() + 0.02
    import services
    zone = services.current_zone()
    manager = services.client_manager() if zone is not None else None
    client = manager.get_first_client() if manager is not None else None
    startup = client is None
    with _lock:
        changed = startup != _startup
        if changed:
            log('transport switched to ' + ('startup Socket' if startup else 'native loaded client'))
        _startup = startup
        generation = _generation
        batch = list(_incoming)
        _incoming.clear()
    for message_generation, channel, payload in batch:
        # Socket posts are narration Flash chose not to send natively; they
        # are dispatched in every game state so a wrong mode guess on the
        # Flash side degrades to key ownership, never to silence.
        if message_generation != generation:
            continue
        # Drop the departing screen's speech, but keep transport ownership.
        # Losing the one native-mode mark leaves the poller suppressed after
        # Flash has already stopped handling startup keys (and vice versa).
        if changed and not _is_mode_mark(channel, payload):
            continue
        try:
            _dispatch(channel, payload)
        except Exception as ex:
            log('handler failed: {} {!r}'.format(channel, ex))


def _connection(conn):
    """Serve one UI connection. Never sends a byte."""
    global _connected, _generation, _flash_startup
    reader = FrameReader()
    greeted = False
    conn.settimeout(0.5)
    try:
        while not _stop.is_set():
            try:
                data = conn.recv(4096)
            except socket.timeout:
                continue
            if data == b'':
                return
            for line in reader.feed(data):
                if not greeted:
                    if parse_hello(line) is None:
                        return
                    with _lock:
                        _generation += 1
                        _incoming.clear()
                        _connected = True
                    greeted = True
                    log('UI Socket connected (outbound only, port {})'.format(_port))
                    continue
                post = parse_post(line)
                if post is None:
                    return
                with _lock:
                    if len(_incoming) >= MAX_QUEUE and (
                            post[0] in ('a11y.inputfence', 'a11y.modalstate')
                            or _is_mode_mark(*post)):
                        _incoming.popleft()
                    if len(_incoming) < MAX_QUEUE:
                        _incoming.append((_generation,) + post)
    finally:
        with _lock:
            _connected = False
            _flash_startup = False
            _generation += 1
            _incoming.clear()
        if greeted:
            log('UI Socket disconnected')


def _serve():
    global _port
    listener = None
    try:
        if not enabled():
            log('startup speech disabled in settings; not listening')
            return
        _port = listen_port()
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Exclusive Windows binding prevents a second process from joining
        # the same local endpoint. No external interface is ever bound.
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        listener.bind(('127.0.0.1', _port))
        listener.listen(2)
        listener.settimeout(0.5)
        log('same-process-only loopback listener ready on port {}'.format(_port))
        while not _stop.is_set():
            try:
                conn, address = listener.accept()
            except socket.timeout:
                continue
            try:
                if address[0] == '127.0.0.1' and same_process_peer(address[1], _port):
                    _connection(conn)
            except Exception as ex:
                log('Socket session ended: {!r}'.format(ex))
            finally:
                conn.close()
    except Exception as ex:
        log('Socket unavailable: {!r}'.format(ex))
    finally:
        if listener is not None:
            listener.close()


def stop():
    _stop.set()


def install():
    global _thread
    if _thread is not None:
        return
    import sims4.core_services as core
    original = core.on_tick

    @functools.wraps(original)
    def on_tick(*args, **kwargs):
        result = original(*args, **kwargs)
        try:
            tick()
        except Exception as ex:
            log('core tick failed: {!r}'.format(ex))
        return result

    core.on_tick = on_tick
    _thread = threading.Thread(target=_serve, name='a11y_startup', daemon=True)
    _thread.start()


try:
    import sims4.core_services
except ImportError:
    pass
else:
    install()
