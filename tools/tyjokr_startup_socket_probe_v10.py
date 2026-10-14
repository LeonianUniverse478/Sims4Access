"""Isolated startup transport capability test; excluded from the shipping mod.

The worker accepts only a fixed handshake, not game commands, speech, paths,
or arbitrary content. It binds loopback only and expires after ten minutes.
The random challenge requires a second Flash-to-Python message to prove a
complete round trip. Core ticks record startup state separately.
"""
import functools
import os
import socket
import threading
import time

PORT = 45992
HELLO = b'A11Y_SOCKET_V10\n'
POLICY_REQUEST = b'<policy-file-request/>\x00'
POLICY = (b'<?xml version="1.0"?><cross-domain-policy>'
          b'<allow-access-from domain="*" to-ports="45992" />'
          b'</cross-domain-policy>\x00')
MAX_INPUT = 256
_next = 0.0
_phases = set()


def receive_frame(conn, delimiter):
    """TCP may split any message; cap input and terminate stalled peers."""
    data = b''
    deadline = time.monotonic() + 2.0
    while delimiter not in data:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise socket.timeout('Incomplete diagnostic frame')
        conn.settimeout(remaining)
        chunk = conn.recv(MAX_INPUT + 1 - len(data))
        if not chunk:
            raise ValueError('Peer closed before frame terminator')
        data += chunk
        if len(data) > MAX_INPUT:
            raise ValueError('Diagnostic frame too long')
    return data


def exchange(conn, log):
    # A socket-policy request is NUL terminated; the diagnostic is newline
    # terminated. Neither parser deserializes objects or evaluates content.
    first = b''
    deadline = time.monotonic() + 2.0
    while b'\n' not in first and b'\x00' not in first:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise socket.timeout('Incomplete first frame')
        conn.settimeout(remaining)
        chunk = conn.recv(MAX_INPUT + 1 - len(first))
        if not chunk:
            raise ValueError('Peer closed before first terminator')
        first += chunk
        if len(first) > MAX_INPUT:
            raise ValueError('First frame too long')
    if first == POLICY_REQUEST:
        conn.sendall(POLICY)
        log('Socket policy requested and returned.')
        return False
    if first != HELLO:
        log('Rejected a non-diagnostic connection.')
        return False
    log('HELLO received from Flash; outgoing startup direction established.')
    challenge = os.urandom(16).hex().encode('ascii')
    conn.sendall(b'CHALLENGE|' + challenge + b'\n')
    confirm = receive_frame(conn, b'\n')
    if confirm != b'CONFIRM|' + challenge + b'\n':
        log('Challenge confirmation did not match.')
        return False
    log('ROUNDTRIP VERIFIED: Flash echoed this connection\'s random challenge.')
    conn.sendall(b'COMPLETE\n')
    return True


def serve(log, lifetime=600.0, ready=None, port=PORT):
    listener = None
    try:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(('127.0.0.1', port))
        listener.listen(2)
        listener.settimeout(0.5)
        if ready is not None:
            ready(listener.getsockname()[1])
        log('Loopback Socket listener ready; expires in {} seconds.'.format(lifetime))
        deadline = time.monotonic() + lifetime
        while time.monotonic() < deadline:
            try:
                conn, _address = listener.accept()
            except socket.timeout:
                continue
            try:
                if exchange(conn, log):
                    # One proof is sufficient; the UI keeps the green result.
                    break
            except Exception as ex:
                log('Diagnostic connection failed: {!r}'.format(ex))
            finally:
                conn.close()
    except Exception as ex:
        log('Socket capability test unavailable: {!r}'.format(ex))
    finally:
        if listener is not None:
            listener.close()
        log('Socket diagnostic listener stopped.')


def install():
    import tyjokr_a11y_speech as speech
    import sims4.core_services as core
    log_path = os.path.join(os.path.dirname(speech.LOG_PATH), 'startup-socket-probe-v10.log')

    def log(message):
        try:
            with open(log_path, 'a', encoding='utf-8') as fh:
                fh.write('{} {}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S'), message))
        except Exception:
            pass

    original = core.on_tick

    @functools.wraps(original)
    def on_tick(*args, **kwargs):
        global _next
        result = original(*args, **kwargs)
        if time.monotonic() >= _next:
            _next = time.monotonic() + 5.0
            try:
                import services
                zone = services.current_zone()
                manager = services.client_manager() if zone is not None else None
                client = manager.get_first_client() if manager is not None else None
                phase = (zone is not None, client is not None)
                if phase not in _phases:
                    _phases.add(phase)
                    log('Core phase: zone={}, client={}.'.format(*phase))
            except Exception as ex:
                log('Core phase unavailable: {!r}'.format(ex))
        return result

    core.on_tick = on_tick
    threading.Thread(target=serve, args=(log,), name='a11y_socket_probe', daemon=True).start()
    log('Isolated V10 Socket diagnostic installed; fixed protocol only.')


try:
    import sims4.core_services
except ImportError:
    pass  # Allows offline protocol verification without pretending to run EA.
else:
    install()
