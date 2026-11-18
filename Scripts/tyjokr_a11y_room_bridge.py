"""Bridge TS4 Access Plus room names into the standard Build grid."""
import time
import tyjokr_a11y_speech as speech

_cache_at = 0.0
_cache = {}
_cache_zone = None

def _log(message):
    try: speech.log_line("room bridge: " + message)
    except Exception: pass

def _room_map(refresh=False):
    global _cache_at, _cache, _cache_zone
    import services
    zone = services.current_zone_id()
    if zone != _cache_zone:
        _cache, _cache_at, _cache_zone = {}, 0.0, zone
    now = time.monotonic()
    if refresh or now - _cache_at > 2.0:
        try:
            import tyjokr_a11y_plus_rooms as plus_rooms
            _cache = {(int(room.rid), int(room.level)): room.name for room in plus_rooms.scan_rooms()}
            _cache_at = now
        except Exception as ex: _log("lookup failed: {!r}".format(ex))
    return _cache

def inferred_name(room_id, level):
    """Passive fallback to Plus room names; custom native labels take priority."""
    try:
        return _room_map().get((int(room_id), int(level)))
    except (TypeError, ValueError):
        return None
