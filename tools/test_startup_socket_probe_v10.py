"""Real loopback protocol tests; these do not establish Scaleform support."""
import socket
import threading
import unittest
import tyjokr_startup_socket_probe_v10 as probe


class ProtocolTests(unittest.TestCase):
    def run_exchange(self, frames, reply):
        accepted = []
        logs = []
        errors = []
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)

        def worker():
            conn, _ = listener.accept()
            try:
                accepted.append(probe.exchange(conn, logs.append))
            except Exception as ex:
                errors.append(ex)
            finally:
                conn.close()
                listener.close()

        thread = threading.Thread(target=worker)
        thread.start()
        with socket.create_connection(listener.getsockname(), timeout=3) as client:
            for frame in frames:
                client.sendall(frame)
            reply(client)
        thread.join(4)
        self.assertFalse(thread.is_alive())
        return accepted, logs, errors

    def test_fragmented_bidirectional_roundtrip(self):
        def reply(client):
            challenge = probe.receive_frame(client, b'\n')
            self.assertTrue(challenge.startswith(b'CHALLENGE|'))
            self.assertEqual(len(challenge), 43)
            answer = b'CONFIRM|' + challenge.split(b'|')[1]
            for byte in answer:
                client.sendall(bytes((byte,)))
            self.assertEqual(probe.receive_frame(client, b'\n'), b'COMPLETE\n')
        accepted, logs, errors = self.run_exchange([b'A11Y_', b'SOCKET_', b'V10\n'], reply)
        self.assertEqual(accepted, [True])
        self.assertFalse(errors)
        self.assertTrue(any('ROUNDTRIP VERIFIED' in line for line in logs))

    def test_wrong_challenge_never_counts_as_success(self):
        def reply(client):
            probe.receive_frame(client, b'\n')
            client.sendall(b'CONFIRM|' + b'0' * 32 + b'\n')
        accepted, logs, errors = self.run_exchange([probe.HELLO], reply)
        self.assertEqual(accepted, [False])
        self.assertFalse(errors)
        self.assertFalse(any('ROUNDTRIP VERIFIED' in line for line in logs))

    def test_policy_serves_only_fixed_socket_policy(self):
        def reply(client):
            self.assertEqual(probe.receive_frame(client, b'\x00'), probe.POLICY)
        accepted, _logs, errors = self.run_exchange([probe.POLICY_REQUEST], reply)
        self.assertEqual(accepted, [False])
        self.assertFalse(errors)

    def test_arbitrary_commands_are_rejected(self):
        accepted, logs, errors = self.run_exchange([b'a11y.speak arbitrary\n'], lambda c: c.recv(1))
        self.assertEqual(accepted, [False])
        self.assertFalse(errors)
        self.assertTrue(any('Rejected' in line for line in logs))

    def test_oversize_input_fails_bounded(self):
        accepted, _logs, errors = self.run_exchange([b'x' * 257], lambda c: c.recv(1))
        self.assertFalse(accepted)
        self.assertTrue(any(isinstance(ex, ValueError) for ex in errors))

    def test_listener_expires_without_connections(self):
        logs = []
        probe.serve(logs.append, lifetime=0, port=0)
        self.assertIn('Socket diagnostic listener stopped.', logs)


if __name__ == '__main__':
    unittest.main(verbosity=2)
