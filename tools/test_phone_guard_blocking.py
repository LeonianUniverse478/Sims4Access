"""Control Alt P opens a waiting call behind the call alert and HUD panels
and stays refused behind dialogs, pickers, pie menus and text entry.

Flash reports the owner ('DD' modal state) and, since the phone-guard fix,
a blocking bit: atomically as a third context-suffix digit, and alone on
a11y.blocking (posted after context and modalstate, and again after a sender
reset). These checks drive the real apply_modal_state, a11y_blocking, _chord
and _open_waiting_checked bodies through the shared fixture pump.
"""
import types
import unittest
from unittest.mock import patch

import test_scanner_v5 as env
import tyjokr_a11y_narrator as narrator

keys = env.keys
REFUSAL = keys._PHONE_BLOCKED


class PhoneGuardTests(unittest.TestCase):
    def setUp(self):
        env.settings._stored.clear()
        env.queue.clear()
        env.messages.clear()
        keys._enabled = True
        keys._modal_active = False
        keys._editing_active = False
        keys._blocking_explicit = None
        self.spoken = []
        speech = patch.object(env.speech, 'speak',
                              side_effect=lambda text, *args, **kwargs: self.spoken.append(text))
        speech.start()
        self.addCleanup(speech.stop)
        self.opened = []
        phone = types.SimpleNamespace(open_waiting=lambda *args: self.opened.append(args) or True)
        modules = patch.dict(env.sys.modules, {'tyjokr_a11y_phone': phone})
        modules.start()
        self.addCleanup(modules.stop)

    def press(self):
        keys._chord('phone')
        env.drain()

    def test_world_press_opens_as_before(self):
        self.press()
        self.assertEqual(self.opened, [(True,)])
        self.assertEqual(self.spoken, [])

    def test_old_ui_without_the_bit_keeps_refusing_any_owner(self):
        keys.apply_modal_state('10', 'modalstate')
        self.assertTrue(keys.blocking_active())
        self.press()
        self.assertEqual(self.opened, [])
        self.assertEqual(self.spoken, [REFUSAL])

    def test_the_call_alert_reported_non_blocking_opens_the_phone(self):
        keys.apply_modal_state('100', 'context')     # the alert: owner on, blocking off
        keys.apply_modal_state('10', 'modalstate')    # the direct report follows
        keys.a11y_blocking('0')
        self.press()
        self.assertEqual(self.opened, [(True,)])
        self.assertEqual(self.spoken, [])

    def test_a_dialog_reported_blocking_still_refuses(self):
        keys.apply_modal_state('101', 'context')
        keys.apply_modal_state('10', 'modalstate')
        keys.a11y_blocking('1')
        self.press()
        self.assertEqual(self.opened, [])
        self.assertEqual(self.spoken, [REFUSAL])

    def test_the_bit_alone_permits_after_a_lost_context_post(self):
        keys.apply_modal_state('10', 'modalstate')    # context post lost: unknown blocks
        self.assertTrue(keys.blocking_active())
        keys.a11y_blocking('0')
        self.assertFalse(keys.blocking_active())
        self.press()
        self.assertEqual(self.opened, [(True,)])

    def test_alert_to_dialog_with_the_same_owner_state_turns_blocking_on(self):
        keys.apply_modal_state('100', 'context')
        keys.a11y_blocking('0')
        keys.apply_modal_state('101', 'context')      # still '10', a different owner
        self.assertTrue(keys.blocking_active())
        keys.apply_modal_state('10', 'modalstate')    # a duplicate report changes nothing
        self.assertTrue(keys.blocking_active())
        self.press()
        self.assertEqual(self.opened, [])

    def test_duplicate_owner_reports_keep_an_explicit_permissive_bit(self):
        keys.apply_modal_state('100', 'context')
        keys.a11y_blocking('0')
        for _ in range(3):
            keys.apply_modal_state('10', 'modalstate')
            keys.a11y_modalstate(10)
            keys.a11y_blocking(0)
        self.assertFalse(keys.blocking_active())

    def test_a_new_owner_report_without_its_bit_fails_closed(self):
        keys.apply_modal_state('100', 'context')
        keys.a11y_blocking('0')
        keys.apply_modal_state('00', 'modalstate')    # the owner closed
        self.assertIsNone(keys._blocking_explicit)
        self.assertFalse(keys.blocking_active())      # nothing open, nothing blocks
        keys.apply_modal_state('10', 'modalstate')    # a new owner, its bit not yet known
        self.assertTrue(keys.blocking_active())
        self.press()
        self.assertEqual(self.opened, [])
        self.assertEqual(self.spoken, [REFUSAL])

    def test_three_digit_direct_payloads_are_rejected(self):
        # The native path drops leading zeros: '010' would arrive as '10'.
        for payload in ('100', '101', 100, 101, '010', '001'):
            self.assertFalse(keys.apply_modal_state(payload, 'modalstate'), payload)
            self.assertFalse(keys.a11y_modalstate(payload), payload)
        self.assertFalse(keys._modal_active)
        self.assertIsNone(keys._blocking_explicit)

    def test_context_command_applies_owner_and_bit_as_one_report(self):
        narrator.a11y_context_enc('widgets.SimInfoTray%3A%3APhoneAlert%2Finstance5%3A100')
        self.assertTrue(keys._modal_active)
        self.assertFalse(keys.blocking_active())
        narrator.a11y_context_enc('olympus.dialog%3A%3ADialog%2Finstance9%3A101')
        self.assertTrue(keys.blocking_active())
        narrator.a11y_context_enc('world%3A00')           # two digits still apply
        self.assertFalse(keys._modal_active)
        self.assertFalse(keys.blocking_active())
        narrator.a11y_context_enc('world%3A1xz')          # garbage suffix ignored
        narrator.a11y_context_enc('world%3A1000')
        self.assertFalse(keys._modal_active)

    def test_bit_payloads_are_validated(self):
        self.assertTrue(keys.a11y_blocking(1))
        self.assertTrue(keys._blocking_explicit)
        self.assertTrue(keys.a11y_blocking(0))
        self.assertFalse(keys._blocking_explicit)
        for bad in ('2', '', None, True, '10'):
            self.assertFalse(keys.a11y_blocking(bad), bad)
        self.assertFalse(keys._blocking_explicit)

    def test_pump_recheck_refuses_when_a_dialog_opens_before_the_turn(self):
        keys.apply_modal_state('100', 'context')
        keys.a11y_blocking('0')
        keys._chord('phone')                          # queued while the alert owns the HUD
        self.assertEqual(len(env.queue), 1)
        keys.apply_modal_state('101', 'context')      # a dialog opened before the pump turn
        env.drain()
        self.assertEqual(self.opened, [])
        self.assertEqual(self.spoken, [REFUSAL])

    def test_pump_recheck_refuses_when_typing_starts_before_the_turn(self):
        keys._chord('phone')
        keys.apply_modal_state('01', 'modalstate')
        env.drain()
        self.assertEqual(self.opened, [])
        self.assertEqual(self.spoken, [REFUSAL])

    def test_typing_inside_a_non_blocking_panel_never_switches_the_recipient(self):
        keys.apply_modal_state('110', 'context')
        self.press()
        self.assertEqual(self.opened, [])
        self.assertEqual(self.spoken, [REFUSAL])

    def test_the_shortcut_and_the_recheck_share_one_refusal_text(self):
        keys.apply_modal_state('101', 'context')
        self.press()
        keys.apply_modal_state('100', 'context')
        keys._chord('phone')
        keys.a11y_blocking('1')
        env.drain()
        self.assertEqual(self.spoken, [REFUSAL, REFUSAL])
        self.assertNotIn(chr(0x2014), REFUSAL)
        self.assertNotIn(chr(0x2013), REFUSAL)


if __name__ == '__main__':
    unittest.main(verbosity=2)
