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
    import tyjokr_a11y_place as place
    building = place.in_build_mode()
    if keys._scanner_effective() and not building:
        _say('Turn scanner mode off to use the lot grid.',
             'Wyłącz tryb skanera, aby użyć siatki parceli.')
        return False
    import services
    try:
        sim = services.get_active_sim()
        lot = services.active_lot()
        if sim is None or lot is None:
            raise ValueError('No active Sim or lot')
        position, _level, start_note = _start_point(sim, lot)
        _x, _z = float(position.x), float(position.z)
        if not math.isfinite(_x) or not math.isfinite(_z):
            raise ValueError('Invalid start position')
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
    note = (_text(*start_note) + ' ') if start_note is not None else ''
    if building and _start_build(note):
        return describe()
    if building:
        announce_placement(note)
    else:
        _say(note + 'Read-only lot grid on. Arrows sample one metre. Objects are listed by their origin, not their full footprint.',
             note + 'Siatka parceli włączona, tylko do odczytu. Strzałki przesuwają o metr. Lista podaje punkty początkowe obiektów, nie ich pełne obrysy.')
    return describe()


def announce_placement(note=''):
    import tyjokr_a11y_place as place
    import tyjokr_a11y_scanner as scanner
    item = place.product()
    parts = [note, _text('Build placement on. Control Alt arrows move one metre, Page Up and Page Down change floor, '
                   'Control Alt Enter places the object chosen in the Build catalog, brackets rotate it, '
                   'Z undoes, X sells what is here. ',
                   'Umieszczanie włączone. Control Alt i strzałki przesuwają o metr, Page Up i Page Down zmieniają piętro, '
                   'Control Alt Enter umieszcza obiekt wybrany w katalogu, nawiasy go obracają, '
                   'Z cofa, X sprzedaje to, co tu stoi. ')]
    if item is not None and item['name']:
        parts += [_text('Selected: ', 'Wybrano: '), item['name'], '. ']
    else:
        parts.append(_text('Choose an object in the Build catalog, close the catalog, then come back here. ',
                           'Wybierz obiekt w katalogu, zamknij katalog i wróć tutaj. '))
    scanner._speak_parts(parts)
    return True


def placement_toggle():
    """Ctrl+Alt+B: the lot grid as the Build placement cursor."""
    import tyjokr_a11y_place as place
    if not place.in_build_mode():
        _say('Enter Build mode first. In Live mode, Control Alt T reads the lot grid.',
             'Najpierw włącz tryb budowania. W trybie życia Control Alt T odczytuje siatkę parceli.')
        return False
    return toggle()


def _cancel_placement():
    try:
        import tyjokr_a11y_place as place
        place.cancel_pending()
    except Exception:
        pass


def _start_point(sim, lot):
    """(position, level, note): the active Sim's spot when it is on this lot;
    otherwise the lot centre or the game's default lot point (by the front
    door), whichever is on the lot, so the cursor never starts on a sidewalk
    it cannot leave."""
    position = sim.position
    if lot.is_position_on_lot(position):
        return position, int(sim.level), None
    for getter, note in ((lambda: lot.center,
                          ('Your Sim is off the lot, so the grid starts at the centre of the lot.',
                           'Twój Sim jest poza parcelą, więc siatka zaczyna się na środku parceli.')),
                         (lambda: lot.get_default_position(),
                          ('Your Sim is off the lot, so the grid starts near the front of the lot.',
                           'Twój Sim jest poza parcelą, więc siatka zaczyna się przy froncie parceli.'))):
        try:
            candidate = getter()
            if candidate is not None and lot.is_position_on_lot(candidate):
                return candidate, 0, note
        except Exception:
            continue
    raise ValueError('No point on the lot to start from')


def leave():
    global _active
    _active = False
    _stop_build()
    _cancel_placement()
    _say('Lot grid off.', 'Siatka parceli wyłączona.')
    return True


def retire():
    """Build controls switched off: stop the grid without a word (the
    settings row already says what changed)."""
    global _active
    _active = False
    _stop_build()
    _cancel_placement()
    return True


def toggle():
    return leave() if active() else enter()


def focus_position(position, level):
    """Move the cursor to position on level (after a placement landed
    somewhere near the aimed point). Coordinates stay relative to the start."""
    global _x, _z, _level
    if not active():
        return False
    x, z = float(position.x), float(position.z)
    if not (math.isfinite(x) and math.isfinite(z)):
        return False
    _x, _z, _level = x, z, int(level)
    if _build:
        global _tile
        import tyjokr_a11y_tiles as tiles
        f = tiles.frame()
        if f is not None:
            _tile = f.clamp(*f.tile_of(x, z))
            _x, _z = f.world(*_tile)
    return True


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
    if _build:
        return _build_move(dx, dz)
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
    global _offer
    _offer = None
    return describe()


def _place_here():
    import tyjokr_a11y_place as place
    target = cursor()
    if target is None:
        _say('This grid point cannot take an object. Move the cursor.',
             'W tym punkcie siatki nie można umieścić obiektu. Przesuń kursor.')
        return False
    position, level, _ident = target
    return place.place(position, level, _surface())


def _enter_key():
    import tyjokr_a11y_place as place
    if _build and place.in_build_mode():
        return _build_place()
    return _place_here() if place.in_build_mode() else describe()


def _sell_here():
    import tyjokr_a11y_place as place
    try:
        objects = [obj for obj in _objects_at_origin() if not getattr(obj, 'is_sim', False)]
        # Topmost first, as the game's own Build cursor picks: a computer
        # on a desk before the desk (live 2026-09-26).
        objects.sort(key=_parent_depth, reverse=True)
    except Exception:
        objects = []
    return place.sell(objects[0] if objects else None)


def _parent_depth(obj):
    depth, parent = 0, getattr(obj, 'parent', None)
    while parent is not None and depth < 8:
        depth, parent = depth + 1, getattr(parent, 'parent', None)
    return depth


def _no_redo():
    _say('Nothing to redo.', 'Nie ma czego ponowić.')
    return False


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
    if _build:
        return describe_build()
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
               'open': _enter_key, 'repeat': describe, 'where': describe,
               'status': describe, 'rescan': describe, 'back': leave,
               'off': leave, 'on': enter, 'toggle': toggle}
    import tyjokr_a11y_place as place
    actions.update({'rotateleft': lambda: place.rotate(-1), 'rotateright': lambda: place.rotate(1),
                    'undo': place.undo, 'redo': _no_redo, 'sell': _sell_here,
                    'place': _place_here})
    if _build:
        actions.update({'place': _enter_key, 'turn': lambda: _turn(1), 'turnback': lambda: _turn(-1),
                        'last': _jump_to_last})
        for topic in range(1, 7):
            actions['info{}'.format(topic)] = (lambda value=topic: _detail(value))
    callback = actions.get(intent)
    return callback() if callback is not None else False


# --------------------------------------------------------- the Build cursor
#
# Ctrl+Alt+B in Build mode: the grid becomes a lot-aligned tile cursor that
# owns plain keys (TooltipManager A11yBuildGridOwner reports it; keys.py
# routes A11yBuildGrid:<intent>). Arrows step one tile and read it: what
# stands there (by footprint), walls, doors and room changes, and whether
# the chosen catalog object fits there at the current facing. R turns the
# facing, Enter places exactly on the tile, or says why not and offers the
# nearest tile where it fits (a second Enter places it there). Number keys
# read one topic each. Falls back to the plain grid when the lot has no
# frame, so nothing is placed on a guessed grid.

_build = False
_tile = (0, 0)
_facing = 0
_offer = None
_last_room = [None, None]      # (room id, outside) of the last tile read
OFFER_SECONDS = 20.0


def _flash(message):
    try:
        import distributor.ops
        import distributor.system
        distributor.system.Distributor.instance().add_op_with_no_owner(
            distributor.ops.SendUIMessage(message))
    except Exception as ex:
        speech.log_line('grid: {} not sent ({!r})'.format(message, ex))


def build_cursor():
    return _build and active()


def _start_build(note):
    """Called by enter() in Build mode. False keeps the plain grid."""
    global _build, _tile, _facing, _offer, _x, _z
    import tyjokr_a11y_tiles as tiles
    f = tiles.frame()
    if f is None:
        return False
    _tile = f.clamp(*f.tile_of(_x, _z))
    _x, _z = f.world(*_tile)
    _facing, _offer = 0, None
    _last_room[0] = _last_room[1] = None
    _build = True
    _flash('A11yBuildGridOn')
    import tyjokr_a11y_place as place
    import tyjokr_a11y_scanner as scanner
    item = place.product()
    parts = [note, _text('Build placement on. Arrow keys move one tile. R turns the object, Enter places it, '
                         'number keys 1 to 6 read details, Space repeats, Escape leaves. ',
                         'Umieszczanie włączone. Strzałki przesuwają o jedno pole. R obraca obiekt, Enter go umieszcza, '
                         'klawisze od 1 do 6 czytają szczegóły, spacja powtarza, Escape kończy. ')]
    if item is not None and item['name']:
        parts += [_text('Selected: ', 'Wybrano: '), item['name'], '. ']
    else:
        parts.append(_text('Choose an object in the Build catalog; Tab returns to it. ',
                           'Wybierz obiekt w katalogu; Tab do niego wraca. '))
    street = _street_side(f)
    if street is not None:
        parts.append(_text('The street is to the {}. ', 'Ulica jest na {}. ').format(tiles.direction_name(street)))
    scanner._speak_parts(parts)
    return True


def _stop_build():
    global _build, _offer
    if _build:
        _flash('A11yBuildGridOff')
    _build, _offer = False, None


def _street_side(f):
    """Direction of the lot edge nearest the game's default lot point (by the
    street), or None."""
    try:
        import services
        point = services.active_lot().get_default_position()
        i, j = f.tile_of(point.x, point.z)
    except Exception:
        return None
    gaps = ((f.depth - 1 - j, 0), (f.width - 1 - i, 1), (j, 2), (i, 3))
    return min(gaps)[1]


def _build_move(dx, dz):
    global _tile, _x, _z, _offer
    import tyjokr_a11y_tiles as tiles
    f = tiles.frame()
    if f is None:
        return False
    ni, nj = _tile[0] + dx, _tile[1] + dz
    if not f.inside(ni, nj):
        _say('Lot edge.', 'Granica parceli.')
        return False
    _tile, _offer = (ni, nj), None
    _x, _z = f.world(ni, nj)
    return describe()


def _name(obj):
    import tyjokr_a11y_scanner as scanner
    try:
        entry = scanner._entry_for(obj, obj.position, _level, bool(getattr(obj, 'is_sim', False)), '', '')
        return scanner._name_part(entry)
    except Exception:
        return _text('an object', 'obiekt')


def _object_parts(f, objects, spots=True):
    import tyjokr_a11y_tiles as tiles
    parts = []
    for index, obj in enumerate(objects[:4]):
        if index:
            parts.append(', ')
        parts.append(_name(obj))
        children = tiles.children_on(obj)
        if children:
            parts.append(_text(' with ', ' z: '))
            for number, child in enumerate(children[:3]):
                if number:
                    parts.append(_text(' and ', ' i '))
                parts.append(_name(child))
            parts.append(_text(' on it', ' na nim'))
        if spots:
            free = tiles.free_spots(obj)
            if free:
                parts.append(_text(', free spots: {}', ', wolne miejsca: {}').format(free))
    if len(objects) > 4:
        parts.append(_text(' and {} more', ' i {} więcej').format(len(objects) - 4))
    parts.append('. ')
    return parts


def _wall_parts(f, all_sides=False):
    import tyjokr_a11y_tiles as tiles
    i, j = _tile
    sides = tiles.walls(f, i, j, _level)
    doors = tiles.doors(f, i, j, _level)
    if all_sides:
        parts = []
        for index in range(4):
            if index in doors:
                state = _text('door', 'drzwi')
            else:
                state = {'wall': _text('wall', 'ściana'), 'edge': _text('lot edge', 'granica parceli'),
                         'open': _text('open', 'wolne')}.get(sides.get(index), _text('unknown', 'nieznane'))
            parts.append('{}: {}. '.format(tiles.direction_name(index).capitalize(), state))
        return parts
    parts = []
    wall_dirs = [tiles.direction_name(index) for index in range(4) if sides.get(index) == 'wall' and index not in doors]
    if wall_dirs:
        parts.append(_text('Wall {}. ', 'Ściana: {}. ').format(_text(' and ', ' i ').join(wall_dirs)))
    door_dirs = [tiles.direction_name(index) for index in sorted(doors)]
    if door_dirs:
        parts.append(_text('Door {}. ', 'Drzwi: {}. ').format(_text(' and ', ' i ').join(door_dirs)))
    return parts


def _room_parts(f):
    import tyjokr_a11y_tiles as tiles
    i, j = _tile
    facts = tiles.ground(f, i, j, _level)
    room = tiles.room(f, i, j, _level)
    outside = facts.get('outside')
    parts = []
    previous_room, previous_outside = _last_room
    if previous_outside is not None and outside is not None and outside != previous_outside:
        parts.append(_text('Outside. ', 'Na zewnątrz. ') if outside else _text('Inside. ', 'Wewnątrz. '))
    elif previous_room is not None and room is not None and room != previous_room and not outside:
        parts.append(_text('Another room. ', 'Inne pomieszczenie. '))
    _last_room[0], _last_room[1] = room, outside
    return parts, facts


def _fit_parts(f, with_facing=True):
    """What the chosen object would do on this tile at the current facing."""
    import tyjokr_a11y_place as place
    import tyjokr_a11y_tiles as tiles
    item = place.product()
    if item is None:
        return []
    need = place.requirement(item['id'])
    i, j = _tile
    if need == 'slot':
        surfaces = [obj for obj in tiles.objects_on(f, i, j, _level) if tiles.free_spots(obj)]
        return [_text('It can go on a surface here. ', 'Może stanąć tu na powierzchni. ') if surfaces
                else _text('It needs a surface with a free spot. ', 'Wymaga powierzchni z wolnym miejscem. ')]
    if need in place._NEEDS:
        return [_text(*place._NEEDS[need]), ' ']
    point, why = tiles.fit_at(f, item['id'], i, j, _level, _facing)
    facing = tiles.direction_name(_facing)
    if not with_facing:
        if point is not None:
            return [_text('Fits here. ', 'Mieści się tutaj. ')]
        if why is None:
            return [_text('Fit unknown here. ', 'Nie wiadomo, czy się tu zmieści. ')]
        return [_text('Does not fit here: {}. ', 'Nie mieści się tutaj: {}. ').format(why)]
    if point is not None:
        return [_text('Fits here, facing {}. ', 'Mieści się tutaj, skierowany na {}. ').format(facing)]
    if why is None:
        return [_text('Fit unknown here. ', 'Nie wiadomo, czy się tu zmieści. ')]
    return [_text('Does not fit here facing {}: {}. ', 'Nie mieści się tutaj, skierowany na {}: {}. ').format(facing, why)]


def describe_build():
    import tyjokr_a11y_scanner as scanner
    import tyjokr_a11y_tiles as tiles
    f = tiles.frame()
    if f is None:
        _say('Tile information unavailable.', 'Informacje o polu niedostępne.')
        return False
    i, j = _tile
    parts, facts = _room_parts(f)
    try:
        objects = tiles.objects_on(f, i, j, _level)
    except Exception:
        objects = []
    if objects:
        parts += _object_parts(f, objects)
    elif facts.get('pool'):
        parts.append(_text('Pool. ', 'Basen. '))
    elif facts.get('floor') is False and facts.get('outside'):
        parts.append(_text('Empty ground. ', 'Pusty teren. '))
    else:
        parts.append(_text('Empty floor. ', 'Pusta podłoga. '))
    parts += _wall_parts(f)
    parts += _fit_parts(f)
    scanner._speak_parts(parts)
    return True


def _detail(topic):
    import tyjokr_a11y_scanner as scanner
    import tyjokr_a11y_tiles as tiles
    import tyjokr_a11y_place as place
    f = tiles.frame()
    if f is None:
        _say('Tile information unavailable.', 'Informacje o polu niedostępne.')
        return False
    i, j = _tile
    parts = []
    if topic == 1:
        objects = tiles.objects_on(f, i, j, _level)
        parts = _object_parts(f, objects) if objects else [_text('Nothing here.', 'Nic tu nie ma.')]
    elif topic == 2:
        facts = tiles.ground(f, i, j, _level)
        parts.append(_text('Floor {}. ', 'Piętro {}. ').format(_level))
        for key, yes, no in (('outside', ('Outside', 'Na zewnątrz'), ('Inside', 'Wewnątrz')),
                             ('floor', ('Floor tiles', 'Podłoga'), ('No floor tiles', 'Brak podłogi')),
                             ('pool', ('Pool', 'Basen'), None)):
            if key in facts:
                label = yes if facts[key] else no
                if label:
                    parts.append(_text(*label) + '. ')
    elif topic == 3:
        parts = _wall_parts(f, all_sides=True)
    elif topic == 4:
        nearby = []
        for di in range(-tiles.NEARBY_RADIUS, tiles.NEARBY_RADIUS + 1):
            for dj in range(-tiles.NEARBY_RADIUS, tiles.NEARBY_RADIUS + 1):
                if (di, dj) == (0, 0) or not f.inside(i + di, j + dj):
                    continue
                try:
                    for obj in tiles.objects_on(f, i + di, j + dj, _level):
                        nearby.append((di * di + dj * dj, di, dj, obj))
                except Exception:
                    continue
        seen, count = set(), 0
        for _distance, di, dj, obj in sorted(nearby, key=lambda item: item[0]):
            if obj.id in seen:
                continue
            seen.add(obj.id)
            parts += [_name(obj), ', ', tiles.relative(di, dj), '. ']
            count += 1
            if count >= 8:
                break
        if not count:
            parts = [_text('Nothing within {} tiles.', 'Nic w promieniu {} pól.').format(tiles.NEARBY_RADIUS)]
    elif topic == 5:
        item = place.product()
        if item is None:
            parts = [_text('No object chosen. Tab returns to the Build catalog.',
                           'Nie wybrano obiektu. Tab wraca do katalogu.')]
        else:
            parts = [item['name'] or _text('The object', 'Obiekt'), '. ',
                     _text('Facing {}. ', 'Skierowany na {}. ').format(tiles.direction_name(_facing))]
            parts += _fit_parts(f)
    elif topic == 6:
        parts.append(_text('Column {} of {}, row {} of {}, floor {}. ', 'Kolumna {} z {}, rząd {} z {}, piętro {}. ').format(
            i + 1, f.width, j + 1, f.depth, _level))
        street = _street_side(f)
        if street is not None:
            parts.append(_text('The street is to the {}. ', 'Ulica jest na {}. ').format(tiles.direction_name(street)))
        try:
            import services
            door = services.active_lot().get_front_door()
            if door is not None:
                di, dj = (a - b for a, b in zip(f.tile_of(door.position.x, door.position.z), _tile))
                parts.append(_text('Front door: {}. ', 'Drzwi frontowe: {}. ').format(tiles.relative(di, dj)))
        except Exception:
            pass
    scanner._speak_parts(parts)
    return True


def _turn(step):
    global _facing, _offer
    import tyjokr_a11y_scanner as scanner
    import tyjokr_a11y_tiles as tiles
    f = tiles.frame()
    if f is None:
        return False
    _facing, _offer = (_facing + step) % 4, None
    import tyjokr_a11y_place as place
    if place.product() is None:
        _say('Choose an object in the Build catalog first.', 'Najpierw wybierz obiekt w katalogu.')
        return False
    scanner._speak_parts([_text('Facing {}. ', 'Skierowany na {}. ').format(tiles.direction_name(_facing))]
                         + _fit_parts(f, with_facing=False))
    return True


def _build_place():
    """Enter: place exactly here, or offer the nearest tile where it fits."""
    global _offer
    import time
    import tyjokr_a11y_place as place
    import tyjokr_a11y_tiles as tiles
    item = place.product()
    if item is None:
        _say('Choose an object in the Build catalog first. Tab returns to it.',
             'Najpierw wybierz obiekt w katalogu. Tab do niego wraca.')
        return False
    f = tiles.frame()
    if f is None:
        return False
    i, j = _tile
    now = time.monotonic()
    offer = _offer
    if (offer is not None and offer['from'] == (i, j, _level, _facing) and offer['product'] == item['id']
            and now - offer['at'] < OFFER_SECONDS):
        _offer = None
        return place.place(offer['point'], _level, _surface(), angle=f.yaw(offer['facing']), exact=True)
    _offer = None
    need = place.requirement(item['id'])
    if need == 'slot':
        target = cursor()
        if target is None:
            _say('This tile cannot take an object.', 'To pole nie może przyjąć obiektu.')
            return False
        return place.place(target[0], _level, _surface())
    if need in place._NEEDS:
        place._say_text(*place._NEEDS[need])
        return False
    point, why = tiles.fit_at(f, item['id'], i, j, _level, _facing)
    if point is not None:
        return place.place(point, _level, _surface(), angle=f.yaw(_facing), exact=True)
    if why is None:
        _say('The game could not check this tile, so nothing was bought.',
             'Gra nie mogła sprawdzić tego pola, więc nic nie kupiono.')
        return False
    import tyjokr_a11y_scanner as scanner
    name = item['name'] or _text('It', 'Obiekt')
    found = tiles.nearest_fit(f, item['id'], i, j, _level, _facing)
    if found is None:
        scanner._speak_parts([name, _text(' does not fit here: {}. No tile within {} fits it either. Try another spot or facing.',
                                          ' nie mieści się tutaj: {}. W promieniu {} pól też nie ma miejsca. Spróbuj innego miejsca lub kierunku.'
                                          ).format(why, tiles.NEAREST_RADIUS)])
        return False
    ni, nj, spot, facing = found
    _offer = {'from': (i, j, _level, _facing), 'product': item['id'], 'point': spot,
              'facing': facing, 'tile': (ni, nj), 'at': now}
    scanner._speak_parts([name, _text(' does not fit here: {}. It fits {}, facing {}. Press Enter again to place it there, or move to cancel.',
                                      ' nie mieści się tutaj: {}. Zmieści się: {}, skierowany na {}. Naciśnij Enter ponownie, aby go tam umieścić, albo przesuń kursor.'
                                      ).format(why, tiles.relative(ni - i, nj - j), tiles.direction_name(facing))])
    return False


def _jump_to_last():
    global _tile, _x, _z, _offer
    import tyjokr_a11y_place as place
    import tyjokr_a11y_tiles as tiles
    f = tiles.frame()
    position = place.last_position()
    if f is None or position is None:
        _say('Nothing placed yet.', 'Jeszcze nic nie umieszczono.')
        return False
    ni, nj = f.tile_of(position.x, position.z)
    if not f.inside(ni, nj):
        return False
    _tile, _offer = (ni, nj), None
    _x, _z = f.world(ni, nj)
    return describe()


@sims4.commands.Command('a11y.grid', command_type=sims4.commands.CommandType.Live)
def command(action: str = 'toggle', _connection=None):
    action = action.lower()
    if action not in ('off', 'back') and not _controls_enabled():
        import tyjokr_a11y_build as build
        return build.refuse_disabled()
    return on_key(action)
