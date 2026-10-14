"""Native follow mode integration, with no real game or camera operations."""
import sys
import types
import unittest
from unittest.mock import Mock, patch
import test_scanner_v5 as env
import tyjokr_a11y_camera as follow


class CameraTests(unittest.TestCase):
    def setUp(self):
        follow._live = False
        follow._client = follow._followed = follow._hooked_camera = None
        follow._was_following = follow._repair_pending = False
        follow._baseline_known = False
        follow._last_request = 0.0
        self.sim = types.SimpleNamespace(id=1)
        self.client = types.SimpleNamespace(register_active_sim_changed=Mock(),
                                           unregister_active_sim_changed=Mock())
        self.camera = types.SimpleNamespace(_follow_mode=False, _sim_id=None,
            focus_on_sim=Mock(), cancel_focus=Mock())
        def report(sim_id=None, follow_mode=None, **kwargs):
            self.camera._sim_id = sim_id
            self.camera._follow_mode = follow_mode
            return 'original-result'
        self.camera.update = report
        self.services = types.SimpleNamespace(
            get_active_sim=lambda: self.sim,
            client_manager=lambda: types.SimpleNamespace(get_first_client=lambda: self.client))
        p = patch.dict(sys.modules, {'camera': self.camera, 'services': self.services})
        p.start()
        self.addCleanup(p.stop)
        p = patch.dict(env.settings._stored, {'keyboard': True, 'scanner': True, 'scanner_mode': True})
        p.start()
        self.addCleanup(p.stop)

    def test_activation_uses_native_follow_with_client(self):
        follow.set_live(True)
        self.camera.focus_on_sim.assert_called_once_with(sim=self.sim, follow=True, client=self.client)
        self.client.register_active_sim_changed.assert_called_once_with(follow._active_sim_changed)

    def test_unchanged_heartbeat_does_not_snap_camera(self):
        follow.set_live(True)
        for _ in range(20):
            follow.update()
        self.assertEqual(self.camera.focus_on_sim.call_count, 1)
        self.assertEqual(self.client.register_active_sim_changed.call_count, 1)

    def test_sim_selection_retargets_immediately(self):
        follow.set_live(True)
        old = self.sim
        self.sim = types.SimpleNamespace(id=2)
        follow._active_sim_changed(old, self.sim)
        self.assertEqual(self.camera.focus_on_sim.call_args[1]['sim'].id, 2)
        self.assertEqual(self.camera.focus_on_sim.call_count, 2)

    def test_build_or_cas_suspends_without_camera_operation(self):
        follow.set_live(True)
        follow.set_live(False)
        self.camera.focus_on_sim.reset_mock()
        follow._active_sim_changed(None, types.SimpleNamespace(id=2))
        follow.update()
        self.camera.focus_on_sim.assert_not_called()
        self.camera.cancel_focus.assert_not_called()
        self.client.unregister_active_sim_changed.assert_called_once()

    def test_returns_to_native_follow_on_live_reentry(self):
        follow.set_live(True)
        follow.set_live(False)
        follow.set_live(True)
        self.assertEqual(self.camera.focus_on_sim.call_count, 2)

    def test_build_roundtrip_does_not_mistake_our_follow_for_user_follow(self):
        follow.set_live(True)
        self.camera.update(sim_id=1, follow_mode=True)
        follow.set_live(False)
        follow.set_live(True)
        env.settings._stored['scanner_mode'] = False
        follow.update()
        self.camera.cancel_focus.assert_called_once_with(object=self.sim)

    def test_settings_off_releases_our_follow_and_unregisters(self):
        follow.set_live(True)
        env.settings._stored['scanner_mode'] = False
        follow.update()
        self.camera.cancel_focus.assert_called_once_with(object=self.sim)
        self.client.unregister_active_sim_changed.assert_called_once()
        follow.update()
        self.assertEqual(self.camera.cancel_focus.call_count, 1)

    def test_existing_native_follow_is_not_cancelled_on_disable(self):
        self.camera._follow_mode = True
        follow.set_live(True)
        env.settings._stored['scanner_mode'] = False
        follow.update()
        self.camera.cancel_focus.assert_not_called()

    def test_setting_disable_live_report_releases_before_clearing_live(self):
        follow.set_live(True)
        env.settings._stored['scanner_mode'] = False
        follow.set_live(False)
        self.camera.cancel_focus.assert_called_once_with(object=self.sim)

    def test_no_sim_or_client_is_safe(self):
        self.sim = None
        follow.set_live(True)
        self.camera.focus_on_sim.assert_not_called()
        follow.reset()
        self.client = None
        follow.set_live(True)
        self.camera.focus_on_sim.assert_not_called()

    def test_native_report_restores_lost_follow_and_preserves_original(self):
        with patch.object(follow.time, 'monotonic', return_value=1):
            follow.set_live(True)
        with patch.object(follow.time, 'monotonic', return_value=2):
            result = self.camera.update(sim_id=7, follow_mode=False)
        self.assertEqual(result, 'original-result')
        self.assertEqual(self.camera.focus_on_sim.call_count, 2)

    def test_successful_native_report_does_not_resend(self):
        follow.set_live(True)
        self.camera.update(sim_id=1, follow_mode=True)
        follow.update()
        self.assertEqual(self.camera.focus_on_sim.call_count, 1)

    def test_rate_limited_lost_follow_is_retried_by_heartbeat(self):
        with patch.object(follow.time, 'monotonic', return_value=1):
            follow.set_live(True)
            self.camera.update(sim_id=1, follow_mode=False)
        self.assertEqual(self.camera.focus_on_sim.call_count, 1)
        with patch.object(follow.time, 'monotonic', return_value=2):
            follow.update()
        self.assertEqual(self.camera.focus_on_sim.call_count, 2)

    def test_zone_reset_drops_old_references_without_camera_operation(self):
        follow.set_live(True)
        follow.reset()
        self.assertIsNone(follow._client)
        self.assertIsNone(follow._followed)
        self.camera.cancel_focus.assert_not_called()


if __name__ == '__main__':
    unittest.main()
