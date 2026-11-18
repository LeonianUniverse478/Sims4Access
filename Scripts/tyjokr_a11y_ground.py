"""Explicit native floor pick; never choose or enqueue a cleaning action."""
import math
import tyjokr_a11y_speech as speech


def open_floor_menu():
    """Simulation thread, after the accessibility picker has closed."""
    import services
    import routing
    import terrain
    import tyjokr_a11y_place as place
    import tyjokr_a11y_scanner as scanner
    from server.pick_info import PickType
    try:
        sim, lot = services.get_active_sim(), services.active_lot()
        if sim is None or lot is None or place.in_build_mode():
            speech.speak('Floor actions require an active Sim in Live Mode.', explicit=True)
            return False
        pos = sim.position
        x, z = float(pos.x), float(pos.z)
        if not all(math.isfinite(v) for v in (x, z)):
            raise ValueError('non-finite floor position')
        if not lot.is_position_on_lot(pos):
            speech.speak('Move the active Sim onto the active lot first.', explicit=True)
            return False
        level, lot_id = int(sim.level), int(lot.lot_id)
        if lot_id < 0:
            raise ValueError('invalid lot ID')
        # The existing Flash bridge carries a uint. Native floor resolution
        # accepts zero as the current-lot sentinel; never truncate a wider ID.
        if lot_id > 0xffffffff:
            lot_id = 0
        surface = routing.SurfaceIdentifier(services.current_zone_id(), level,
                                            routing.SurfaceType.SURFACETYPE_WORLD)
        # Read the actual floor height, including foundations/platforms;
        # the Sim may currently be sitting above it on furniture.
        y = float(terrain.get_terrain_height(x, z, routing_surface=surface))
        if not math.isfinite(y):
            raise ValueError('floor height unavailable')
        # A zero target is a native surface pick, not an object pick. The
        # game creates TerrainPoint on this world's routing surface/level.
        # Reuse the client's request counter and normal pie-menu lifecycle.
        sent = scanner._send_ui('A11y|pick|0|{}|{}||{:.3f}|{:.3f}|{:.3f}|{}'.format(
            int(PickType.PICK_FLOOR), lot_id, x, y, z, level))
        speech.log_line('floor actions: sim={} zone={} lot={} level={} point=({:.3f},{:.3f},{:.3f}) sent={}'.format(
            sim.id, services.current_zone_id(), lot_id, level, x, y, z, sent))
        if not sent:
            speech.speak('The floor menu could not be requested.', explicit=True)
        return bool(sent)
    except Exception as ex:
        speech.log_line('floor actions: request failed {!r}'.format(ex))
        speech.speak('The floor menu is unavailable here.', explicit=True)
        return False
