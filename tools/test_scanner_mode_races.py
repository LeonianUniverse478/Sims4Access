"""Independent regressions for delayed owner reports and queued navigation."""
import unittest
from unittest.mock import patch
import test_scanner_mode as fixture
import tyjokr_a11y_hub as hub

keys = fixture.keys
env = fixture.env


class OwnerRaceTests(fixture.ScannerModeBase):
    def test_quick_cancel_is_one_press_in_live_scanner_ownership(self):
        self.turn_on_and_confirm()
        keys.a11y_scannerlive('1')
        with patch.object(hub, 'cancel_from_scanner') as cancel:
            run = fixture.keyboard_env.KeyboardTests.run_samples
            run(self, [{0x51: 0x8001}] + [{0x51: 0x8000}] * 80 + [{}])
            cancel.assert_called_once_with(False)
            cancel.reset_mock()
            run(self, [{0x10: 1, 0x51: 1}, {}])
            cancel.assert_called_once_with(True)
            cancel.reset_mock()
            for modifiers in ({0x11: 1}, {0x12: 1}, {0x11: 1, 0x12: 1}):
                run(self, [{0x51: 1, **modifiers}, {}])
            cancel.assert_not_called()
            for ctrl, alt in ((True, False), (False, True), (True, True)):
                self.assertIsNone(keys._plain_message(0x51, ctrl, alt))

    def test_quick_cancel_does_not_cross_an_owner_or_build_transition(self):
        self.turn_on_and_confirm()
        keys.a11y_scannerlive('1')
        with patch.object(hub, 'cancel_from_scanner') as cancel:
            keys._send(keys._plain_message(0x51))
            keys.a11y_scannerowner('0')
            self.assertIsNone(keys._plain_message(0x51))
            keys.a11y_scannerowner('1')
            env.drain()
            keys._send(keys._plain_message(0x51, shift=True))
            self.zone.is_in_build_buy = True
            env.drain()
            cancel.assert_not_called()
            for state in ('10', '01', '11'):
                keys.a11y_modalstate(state)
                self.assertIsNone(keys._plain_message(0x51))

    def test_quick_cancel_works_in_first_person_while_the_scanner_owns_input(self):
        self.turn_on_and_confirm()
        keys.a11y_scannerlive('1')
        keys.a11y_scannerlive('0')  # First-person view turns off camera follow.
        self.scanner.set_camera_live.assert_called_with(False)
        with patch.object(hub, 'cancel_from_scanner') as cancel:
            run = fixture.keyboard_env.KeyboardTests.run_samples
            run(self, [{0x51: 0x8001}, {}])
            cancel.assert_called_once_with(False)
            cancel.reset_mock()
            run(self, [{0x10: 0x8000, 0x51: 0x8001}, {}])
            cancel.assert_called_once_with(True)

    def test_queued_arrow_does_not_cross_owner_loss_and_return(self):
        self.turn_on_and_confirm()
        keys._send('A11yScanner:next')
        keys.a11y_scannerowner('0')
        keys.a11y_scannerowner('1')
        env.drain()
        self.scanner.on_key.assert_not_called()

    def test_zone_confirmation_announces_even_without_intermediate_zero(self):
        self.turn_on_and_confirm()
        keys.scanner_zone_started()
        keys.a11y_scannerowner('1')
        self.scanner.enter_mode.assert_called_once_with()

    def test_live_heartbeat_rearms_camera_after_scanner_zone_reset(self):
        self.turn_on_and_confirm()
        keys.a11y_scannerlive('1')
        self.scanner.set_camera_live.reset_mock()
        # The scanner's zone hook independently clears the old camera binding.
        keys.a11y_scannerlive('1')
        self.scanner.set_camera_live.assert_called_once_with(True)

    def test_toggle_off_on_without_zero_report_announces_new_session(self):
        self.turn_on_and_confirm()
        keys.set_scanner_mode(False)
        keys.set_scanner_mode(True)
        keys.a11y_scannerowner('1')
        self.scanner.enter_mode.assert_called_once_with()

    def test_owner_report_before_modal_close_still_resumes_on_heartbeat(self):
        self.turn_on_and_confirm()
        keys.a11y_modalstate('10')
        keys.a11y_scannerowner('0')
        keys.a11y_scannerowner('1')
        self.scanner.resume_mode.assert_not_called()
        keys.a11y_modalstate('00')
        keys.a11y_scannerowner('1')
        self.scanner.resume_mode.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
