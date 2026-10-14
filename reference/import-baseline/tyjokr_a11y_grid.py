"""Read-only one-metre sampling cursor on the current lot.

Inspired by glaroc's a11yscan grid, with EA 1.127's actual routing signature.
Object origins are not footprints; a navmesh point is not placement approval.
This never moves the native mouse, Sim, objects, camera, or household funds.
"""
import math

import sims4.commands
import tyjokr_a11y_lang as lang
import tyjokr_a11y_speech as speech

_active = False
_zone_id = None
_x = _z = 0.0
_level = 0
_origin = (0.0, 0.0)


def _text(en, pl):
    return pl if lang._detect_lang() == 'pl' else en


def _say(en, pl):
    speech.speak(_text(en, pl), explicit=True)


def _controls_enabled():
    import tyjokr_a11y_build as build
    return build.controls_enabled()


def active():
    global _active
    try:
        import services
        if services.current_zone_id() != _zone_id or services.active_lot() is None:
            _active = False
        elif not _controls_enabled():
            _active = False
    except Exception:
        _active = False
    return _active


def _sample_key(x, z):
    return int(math.floor(x + 0.5)), int(math.floor(z + 0.5))


def _surface():
    import routing
    return routing.SurfaceIdentifier(_zone_id, _level,
                                     routing.SurfaceType.SURFACETYPE_WORLD)


def _position(x=None, z=None):
    import terrain
    from sims4.math import Vector3
    x = _x if x is None else x
    z = _z if z is None else z
    y = terrain.get_terrain_height(x, z, routing_surface=_surface())
    if y is None or not math.isfinite(float(y)):
        raise ValueError('Grid height unavailable')
    return Vector3(x, float(y), z)


def enter():
    global _active, _zone_id, _x, _z, _level, _origin
    if not _controls_enabled():
        import tyjokr_a11y_build as build
        return build.refuse_disabled()
    import tyjokr_a11y_keys as keys
    if keys._scanner_effective():
        _say('Turn scanner mode off to use the lot grid.',
             'Wyłącz tryb skanera, aby użyć siatki parceli.')
        return False
    import services
    try:
        sim = services.get_active_sim()
        lot = services.active_lot()
        if sim is None or lot is None:
            raise ValueError('No active Sim or lot')
        position = sim.position
        _x, _z = float(position.x), float(position.z)
        if not math.isfinite(_x) or not math.isfinite(_z):
            raise ValueError('Invalid Sim position')
        _level = int(sim.level)
        _zone_id = services.current_zone_id()
        _origin = (_x, _z)
        import tyjokr_a11y_build as build
        if build.active() or build.aiming():
            build.request('off')
        _active = True
    except Exception:
        _active = False
        _say('Load a household with an active Sim first.',
             'Najpierw wczytaj rodzinę z aktywnym Simem.')
        return False
    _say('Read-only lot grid on. Arrows sample one metre. Objects are listed by their origin, not their full footprint.',
         'Siatka parceli włączona, tylko do odczytu. Strzałki przesuwają o metr. Lista podaje punkty początkowe obiektów, nie ich pełne obrysy.')
    return describe()


def leave():
    global _active
    _active = False
    _say('Lot grid off.', 'Siatka parceli wyłączona.')
    return True


def retire():
    """Build controls switched off: stop the grid without a word (the
    settings row already says what changed)."""
    global _active
    _active = False
    return True


def toggle():
    return leave() if active() else enter()


def cursor():
    """Validated read-only snapshot for explicitly aiming the native cursor."""
    if not active():
        return None
    import services
    import build_buy
    try:
        if not int(build_buy.get_lowest_level_allowed()) <= _level <= int(build_buy.get_highest_level_allowed()):
            return None
        position = _position()
        if not services.active_lot().is_position_on_lot(position):
            return None
        return position, _level, _zone_id
    except Exception:
        return None


def move(dx, dz):
    global _x, _z
    if not active():
        return False
    if (dx, dz) not in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        return False
    import services
    try:
        position = _position(_x + dx, _z + dz)
        if not services.active_lot().is_position_on_lot(position):
            _say('Lot boundary.', 'Granica parceli.')
            return False
    except Exception:
        _say('Tile information unavailable.', 'Informacje o polu niedostępne.')
        return False
    _x, _z = _x + dx, _z + dz
    return describe()


def change_level(delta):
    global _level
    if not active() or delta not in (-1, 1):
        return False
    import build_buy
    try:
        minimum = int(build_buy.get_lowest_level_allowed())
        maximum = int(build_buy.get_highest_level_allowed())
        if not minimum <= _level + delta <= maximum:
            _say('Floor limit.', 'Granica pięter.')
            return False
    except Exception:
        _say('Floor information unavailable.', 'Informacje o piętrach niedostępne.')
        return False
    _level += delta
    return describe()


def _objects_at_origin():
    """Fresh lookup: no stale references after moves, sales or zone changes."""
    import services
    objects = []
    for obj in services.object_manager().values():
        try:
            if obj.is_in_inventory() or int(obj.level) != _level:
                continue
            pos = obj.position
            # Cells are relative to the starting Sim so fractional starts
            # don't put the cursor and object in different arbitrary grids.
            if _sample_key(pos.x - _origin[0], pos.z - _origin[1]) != _sample_key(_x - _origin[0], _z - _origin[1]):
                continue
            objects.append(obj)
        except Exception:
            continue
    return objects


def facts():
    """Independent queries preserve unknown values rather than inventing facts."""
    import build_buy
    import routing
    result = {}
    try:
        position = _position()
    except Exception:
        return result
    for label, method in (('floor', 'has_floor_at_location'),
                          ('pool', 'is_location_pool'),
                          ('ground', 'is_location_natural_ground'),
                          ('outside', 'is_location_outside')):
        try:
            value = getattr(build_buy, method)(position, _level)
            if value is not None:
                result[label] = bool(value)
        except Exception:
            pass
    try:
        # Verified in EA objects/pools/pond.py; this takes surface, position.
        value = routing.test_point_placement_in_navmesh(_surface(), position)
        if value is not None:
            result['navmesh'] = bool(value)
    except Exception:
        pass
    return result


def describe():
    if not active():
        return False
    import tyjokr_a11y_scanner as scanner
    parts = [_text('Grid x {}, z {}, floor {}. ', 'Siatka x {}, z {}, piętro {}. ').format(
        int(round(_x - _origin[0])), int(round(_z - _origin[1])), _level)]
    values = facts()
    labels = {
        'floor': (('floor', 'podłoga'), ('no floor', 'brak podłogi')),
        'pool': (('pool', 'basen'), None),
        'ground': (('natural ground', 'naturalny grunt'), None),
        'outside': (('outside', 'na zewnątrz'), ('inside', 'wewnątrz')),
        'navmesh': (('walking surface present', 'powierzchnia do chodzenia'),
                    ('no walking surface at this point', 'brak powierzchni do chodzenia w tym punkcie')),
    }
    for key, pair in labels.items():
        if key in values:
            label = pair[0 if values[key] else 1]
            if label:
                parts.append(_text(*label) + '. ')
    if not values:
        parts.append(_text('Tile information unavailable. ', 'Informacje o polu niedostępne. '))
    try:
        objects = _objects_at_origin()
        if objects:
            parts.append(_text('Object origins here: ', 'Punkty początkowe obiektów tutaj: '))
            for index, obj in enumerate(objects[:5]):
                if index:
                    parts.append(', ')
                entry = scanner._entry_for(obj, obj.position, _level,
                                            bool(getattr(obj, 'is_sim', False)), '', '')
                parts.append(scanner._name_part(entry))
            if len(objects) > 5:
                parts.append(_text(' and {} more', ' i {} więcej').format(len(objects) - 5))
        else:
            parts.append(_text('No object origins in this sample.',
                               'Brak punktów początkowych obiektów w tym polu.'))
    except Exception:
        parts.append(_text('Object information unavailable.', 'Informacje o obiektach niedostępne.'))
    scanner._speak_parts(parts)
    return True


def on_key(intent):
    actions = {'left': lambda: move(-1, 0), 'right': lambda: move(1, 0),
               'up': lambda: move(0, 1), 'down': lambda: move(0, -1),
               'prevcat': lambda: move(-1, 0), 'nextcat': lambda: move(1, 0),
               'prev': lambda: move(0, 1), 'next': lambda: move(0, -1),
               'prevsub': lambda: change_level(1), 'nextsub': lambda: change_level(-1),
               'floorup': lambda: change_level(1), 'floordown': lambda: change_level(-1),
               'open': describe, 'repeat': describe, 'where': describe,
               'status': describe, 'rescan': describe, 'back': leave,
               'off': leave, 'on': enter, 'toggle': toggle}
    callback = actions.get(intent)
    return callback() if callback is not None else False


@sims4.commands.Command('a11y.grid', command_type=sims4.commands.CommandType.Live)
def command(action: str = 'toggle', _connection=None):
    action = action.lower()
    if action not in ('off', 'back') and not _controls_enabled():
        import tyjokr_a11y_build as build
        return build.refuse_disabled()
    return on_key(action)
