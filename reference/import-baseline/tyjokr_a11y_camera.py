"""Use EA's native follow-Sim camera while scanner mode owns Live gameplay.

No camera coordinates, input simulation or polling thread. Flash reports Live
camera eligibility independently of scanner/menu focus. The client callback
retargets on Sim selection; native camera reports repair a lost follow target.
"""
import time
import tyjokr_a11y_settings as settings
import tyjokr_a11y_speech as speech

_live = False
_client = None
_followed = None
_last_request = 0.0
_was_following = False
_baseline_known = False
_hooked_camera = None
_repair_pending = False


def _configured():
    return (settings.get('keyboard', True) and
            settings.get('scanner', True) and settings.get('scanner_mode', False))


def _enabled():
    return _live and _configured()


def _release():
    global _followed, _client, _was_following, _baseline_known, _repair_pending
    # Restore manual camera behavior only while still in the Live camera.
    # Never send a camera operation into Build/CAS during their transition.
    if _live and _followed is not None and not _was_following:
        try:
            import camera
            camera.cancel_focus(object=_followed)
        except Exception as ex:
            speech.log_line('scanner camera: release failed {!r}'.format(ex))
    if _client is not None:
        try:
            _client.unregister_active_sim_changed(_active_sim_changed)
        except Exception as ex:
            speech.log_line('scanner camera: unregister failed {!r}'.format(ex))
    _followed = None
    _client = None
    if not _configured():
        _was_following = False
        _baseline_known = False
    _repair_pending = False


def set_live(live):
    """Simulation thread, from the independent Flash Live-camera report."""
    global _live
    if _live and not live and not _enabled():
        # Setting disabled while still in Live: release our follow before
        # clearing eligibility. A Build/CAS transition keeps settings enabled
        # and therefore never takes this path.
        _release()
    _live = bool(live)
    update()


def _active_sim_changed(old_sim, new_sim):
    if _enabled():
        _follow(new_sim)


def _follow(sim, repair=False):
    global _followed, _last_request, _repair_pending
    if not _enabled() or sim is None:
        return
    now = time.monotonic()
    if sim is _followed and not repair:
        return
    # A client can send multiple stale reports before processing our operation.
    if repair and sim is _followed and now - _last_request < 0.25:
        _repair_pending = True
        return
    try:
        import camera
        camera.focus_on_sim(sim=sim, follow=True, client=_client)
        _followed = sim
        _last_request = now
        _repair_pending = False
        speech.log_line('scanner camera: native follow sim {}'.format(sim.id))
    except Exception as ex:
        speech.log_line('scanner camera: follow failed {!r}'.format(ex))


def _install_report_hook(camera):
    global _hooked_camera
    if _hooked_camera is camera:
        return
    original = camera.update

    def update_report(*args, **kwargs):
        global _repair_pending
        result = original(*args, **kwargs)
        if _enabled():
            try:
                import services
                sim = services.get_active_sim()
                if sim is not None and (not camera._follow_mode or camera._sim_id != sim.id):
                    _follow(sim, repair=True)
                else:
                    _repair_pending = False
            except Exception as ex:
                speech.log_line('scanner camera: report repair failed {!r}'.format(ex))
        return result

    camera.update = update_report
    _hooked_camera = camera


def update():
    """Simulation heartbeat: bind the native callback, repair missed Sim changes.

    An unchanged active Sim sends no operation, so walking is followed natively
    without repeatedly snapping the camera to new coordinates.
    """
    global _client, _was_following, _baseline_known
    if not _enabled():
        _release()
        return
    try:
        import camera
        import services
        client = services.client_manager().get_first_client()
        if client is None:
            return
        if client is not _client:
            _release()
            # Keep the pre-scanner state through Build/CAS suspension. A
            # native report after returning may describe our own follow.
            if not _baseline_known:
                _was_following = bool(getattr(camera, '_follow_mode', False))
                _baseline_known = True
            _client = client
            client.register_active_sim_changed(_active_sim_changed)
        _install_report_hook(camera)
        _follow(services.get_active_sim(), repair=_repair_pending)
    except Exception as ex:
        speech.log_line('scanner camera: update failed {!r}'.format(ex))


def reset():
    """Zone changed: forget old Sim/client references without moving the camera."""
    global _live, _baseline_known, _was_following
    _live = False
    _release()
    _baseline_known = False
    _was_following = False
