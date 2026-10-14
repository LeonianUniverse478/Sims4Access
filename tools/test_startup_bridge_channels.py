"""The zoneless startup bridge (main menu socket path) carries the phone
blocking bit and the clock reply like the loaded-zone command path does:
Flash's startup allow list posts them, so parse_post must accept them and
_dispatch must hand them to the same handlers. Otherwise Control Alt C is
silent at the main menu and the bit is dropped (fails closed, but blind).
"""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('startup_channels_subject', ROOT / 'Scripts/tyjokr_a11y_startup.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class StartupChannelTests(unittest.TestCase):
    def test_both_channels_are_known(self):
        self.assertIn('a11y.blocking', bridge.CHANNELS)
        self.assertIn('a11y.clock_enc', bridge.CHANNELS)

    def test_blocking_payloads_are_validated_like_the_owner_state(self):
        self.assertEqual(bridge.parse_post('POST|a11y.blocking|0'), ('a11y.blocking', '0'))
        self.assertEqual(bridge.parse_post('POST|a11y.blocking|1'), ('a11y.blocking', '1'))
        for line in ('POST|a11y.blocking|2', 'POST|a11y.blocking|', 'POST|a11y.blocking|10',
                     'POST|a11y.blocking|1|extra'):
            self.assertIsNone(bridge.parse_post(line), line)

    def test_clock_replies_pass_through_encoded(self):
        self.assertEqual(bridge.parse_post('POST|a11y.clock_enc|clock%3A'), ('a11y.clock_enc', 'clock%3A'))
        self.assertEqual(bridge.parse_post('POST|a11y.clock_enc|clock%3ASun%208%3A05%20AM'),
                         ('a11y.clock_enc', 'clock%3ASun%208%3A05%20AM'))

    def test_dispatch_reaches_the_same_handlers_as_the_command_path(self):
        keys = types.SimpleNamespace(a11y_blocking=Mock(), a11y_modalstate=Mock(), a11y_inputfence=Mock())
        # The dispatch table names every narrator handler; a Mock module answers them all.
        narrator = Mock()
        with patch.dict(sys.modules, {'tyjokr_a11y_keys': keys, 'tyjokr_a11y_narrator': narrator}):
            bridge._dispatch('a11y.blocking', '1')
            bridge._dispatch('a11y.blocking', '0')
            bridge._dispatch('a11y.clock_enc', 'clock%3A')
        self.assertEqual([c[0] for c in keys.a11y_blocking.call_args_list], [('1',), ('0',)])   # 3.7: no call.args
        narrator.a11y_clock_enc.assert_called_once_with('clock%3A')
        keys.a11y_modalstate.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
