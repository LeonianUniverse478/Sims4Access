"""Independent regressions for delayed owner reports and queued navigation."""
import unittest
import test_scanner_mode as fixture

keys = fixture.keys
env = fixture.env


class OwnerRaceTests(fixture.ScannerModeBase):
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
