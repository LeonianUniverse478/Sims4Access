"""Lot-aligned tiles for the Build cursor: where things are, walls and doors,
and whether the chosen catalog object fits at a tile and facing.

Every game call is checked against the 1.128.90 decompile:

  * the lot frame comes from lot.corners (lot.size_x and size_z agree);
  * an object covers a tile when obj.footprint_polygon.contains(point) (as
    HasFootprintComponent and routing.connectivity use it), or when its
    origin is on the tile (objects without a footprint);
  * walls come from routing.ray_test_verbose(start, end, context,
    return_object_id=True) between neighbouring tile centres, as
    ScriptObject.check_line_of_sight reads it: RAYCAST_HIT_TYPE_IMPASSABLE
    with no blocking object is a wall or fence; the context is the active
    Sim's raycast_context(), so walls block as they do for a Sim;
  * fit is build_buy.test_location_for_object(obj, definition id, location,
    objects to ignore), as RuntimeSlot.is_valid_for_placement and Puddle
    use it, at a sims4.math.Location on the world routing surface;
  * rooms are build_buy.get_block_id, which EA's Python never calls, so it
    is optional: anything it does not answer is simply not reported.

Simulation thread only. Unknown answers stay unknown; nothing is invented.
"""
import math

import tyjokr_a11y_lang as lang
import tyjokr_a11y_speech as speech

# Facing and direction index: north is the lot's +j axis, east its +i axis.
DIRECTIONS = (('north', 'północ'), ('east', 'wschód'), ('south', 'południe'), ('west', 'zachód'))
STEPS = ((0, 1), (1, 0), (0, -1), (-1, 0))
# Origins tried inside a tile: centre first, then edges (two-tile objects
# such as beds sit on a tile edge), then corners.
OFFSETS = ((0.5, 0.5), (0.5, 1.0), (1.0, 0.5), (0.5, 0.0), (0.0, 0.5),
           (1.0, 1.0), (1.0, 0.0), (0.0, 0.0), (0.0, 1.0))
NEAREST_RADIUS = 5
NEARBY_RADIUS = 3

_frame = None
_frame_zone = None
_logged_errors = set()


def text(en, pl):
    return pl if lang._detect_lang() == 'pl' else en


def direction_name(index):
    return text(*DIRECTIONS[index % 4])


class Frame(object):
    """The lot's grid: origin corner, unit axes and size in whole tiles."""

    def __init__(self, corners):
        points = [(float(c.x), float(c.z)) for c in corners]
        if len(points) < 3:
            raise ValueError('A lot needs corners')
        origin = points[0]
        others = sorted(points[1:], key=lambda p: (p[0] - origin[0]) ** 2 + (p[1] - origin[1]) ** 2)
        a, b = others[0], others[1]
        self.origin = origin
        self.width, self.east = self._axis(origin, a)
        self.depth, self.north = self._axis(origin, b)
        if self.width < 1 or self.depth < 1:
            raise ValueError('Lot too small')

    @staticmethod
    def _axis(origin, point):
        dx, dz = point[0] - origin[0], point[1] - origin[1]
        length = math.hypot(dx, dz)
        if not math.isfinite(length) or length < 0.5:
            raise ValueError('Degenerate lot corner')
        return int(round(length)), (dx / length, dz / length)

    def world(self, i, j, du=0.5, dv=0.5):
        """(x, z) of a point in tile (i, j); du, dv run 0..1 across it."""
        u, v = i + du, j + dv
        return (self.origin[0] + u * self.east[0] + v * self.north[0],
                self.origin[1] + u * self.east[1] + v * self.north[1])

    def tile_of(self, x, z):
        dx, dz = float(x) - self.origin[0], float(z) - self.origin[1]
        u = dx * self.east[0] + dz * self.east[1]
        v = dx * self.north[0] + dz * self.north[1]
        return int(math.floor(u)), int(math.floor(v))

    def inside(self, i, j):
        return 0 <= i < self.width and 0 <= j < self.depth

    def clamp(self, i, j):
        return min(max(i, 0), self.width - 1), min(max(j, 0), self.depth - 1)

    def yaw(self, facing):
        """Yaw angle (sims4.math convention, atan2(x, z)) of a facing index."""
        vx, vz = ((self.north, self.east, (-self.north[0], -self.north[1]),
                   (-self.east[0], -self.east[1]))[facing % 4])
        return math.atan2(vx, vz)

    def facing_of(self, angle):
        best, best_gap = 0, None
        for index in range(4):
            gap = abs(math.atan2(math.sin(angle - self.yaw(index)), math.cos(angle - self.yaw(index))))
            if best_gap is None or gap < best_gap:
                best, best_gap = index, gap
        return best


def frame():
    """The active lot's frame, cached per zone; None when the lot will not say."""
    global _frame, _frame_zone
    try:
        import services
        zone = services.current_zone_id()
        if _frame is not None and zone == _frame_zone:
            return _frame
        lot = services.active_lot()
        _frame, _frame_zone = Frame(list(lot.corners)), zone
        return _frame
    except Exception as ex:
        speech.log_line('tiles: no lot frame ({!r})'.format(ex))
        _frame = None
        return None


def forget():
    global _frame
    _frame = None


def relative(di, dj):
    """'2 north, 1 east', or 'here'."""
    parts = []
    for amount, positive, negative in ((dj, 0, 2), (di, 1, 3)):
        if amount:
            parts.append('{} {}'.format(abs(amount), direction_name(positive if amount > 0 else negative)))
    return ', '.join(parts) if parts else text('here', 'tutaj')


# ------------------------------------------------------------- game queries

def surface(level):
    import routing
    import services
    return routing.SurfaceIdentifier(services.current_zone_id(), int(level),
                                     routing.SurfaceType.SURFACETYPE_WORLD)


def position(f, i, j, level, du=0.5, dv=0.5):
    import terrain
    from sims4.math import Vector3
    x, z = f.world(i, j, du, dv)
    y = terrain.get_terrain_height(x, z, routing_surface=surface(level))
    if y is None or not math.isfinite(float(y)):
        raise ValueError('Tile height unavailable')
    return Vector3(x, float(y), z)


def _lot_objects(level):
    import services
    lot = services.active_lot()
    for obj in list(services.object_manager().values()):
        try:
            if obj.is_in_inventory() or int(obj.level) != int(level):
                continue
            if obj.is_hidden() or not lot.is_position_on_lot(obj.position):
                continue
        except Exception:
            continue
        yield obj


def _covers(obj, f, i, j, point):
    try:
        footprint = obj.footprint_polygon
        if footprint is not None and footprint.contains(point):
            return True
    except Exception:
        pass
    try:
        return f.tile_of(obj.position.x, obj.position.z) == (i, j)
    except Exception:
        return False


def objects_on(f, i, j, level):
    """Top-level objects covering the tile (Sims included), largest last so a
    rug does not hide the bed on it; slotted objects are reached through
    children_on()."""
    point = position(f, i, j, level)
    found = []
    for obj in _lot_objects(level):
        try:
            if getattr(obj, 'parent', None) is not None:
                continue
            if _covers(obj, f, i, j, point):
                found.append(obj)
        except Exception:
            continue
    return found


def children_on(obj):
    result = []
    try:
        for child in getattr(obj, 'children', ()) or ():
            if not getattr(child, 'is_sim', False):
                result.append(child)
    except Exception:
        pass
    return result


def free_spots(obj):
    """Empty, non-decoration slots: where a computer or plate could go."""
    count = 0
    try:
        for slot in obj.get_runtime_slots_gen():
            try:
                if slot.empty and not slot.is_deco_slot():
                    count += 1
            except Exception:
                continue
    except Exception:
        return 0
    return count


def is_door(obj):
    try:
        return any(cls.__name__ == 'Door' for cls in type(obj).__mro__)
    except Exception:
        return False


def _raycast_context():
    try:
        import services
        sim = services.get_active_sim()
        return sim.raycast_context() if sim is not None else None
    except Exception as ex:
        speech.log_line('tiles: no raycast context ({!r})'.format(ex))
        return None


def walls(f, i, j, level):
    """{direction: 'wall' | 'edge' | 'open'}; directions the ray test could
    not answer are left out."""
    result = {}
    context = _raycast_context()
    try:
        import routing
        import sims4.math
        start = routing.Location(position(f, i, j, level), sims4.math.Quaternion.IDENTITY(), surface(level))
    except Exception as ex:
        speech.log_line('tiles: wall probe unavailable ({!r})'.format(ex))
        return result
    for index, (di, dj) in enumerate(STEPS):
        ni, nj = i + di, j + dj
        if not f.inside(ni, nj):
            result[index] = 'edge'
            continue
        if context is None:
            continue
        try:
            end = routing.Location(position(f, ni, nj, level), sims4.math.Quaternion.IDENTITY(), surface(level))
            hit, blocker = routing.ray_test_verbose(start, end, context, return_object_id=True)
            if hit == routing.RAYCAST_HIT_TYPE_IMPASSABLE and not blocker:
                result[index] = 'wall'
            else:
                result[index] = 'open'
        except Exception as ex:
            speech.log_line('tiles: ray test failed ({!r})'.format(ex))
    return result


def doors(f, i, j, level):
    """{direction: door object} for doors on this tile's edges."""
    result = {}
    for obj in _lot_objects(level):
        if not is_door(obj):
            continue
        try:
            x, z = float(obj.position.x), float(obj.position.z)
        except Exception:
            continue
        for index, (di, dj) in enumerate(STEPS):
            ex, ez = f.world(i, j, 0.5 + di * 0.5, 0.5 + dj * 0.5)
            if (x - ex) ** 2 + (z - ez) ** 2 <= 0.36:
                result[index] = obj
    return result


def room(f, i, j, level):
    """An opaque room id, or None when the game will not say."""
    try:
        import build_buy
        import services
        point = position(f, i, j, level)
        value = build_buy.get_block_id(services.current_zone_id(), point, int(level))
        return int(value) if value is not None else None
    except Exception:
        return None


def ground(f, i, j, level):
    """Floor facts the game answers: floor, outside, pool."""
    result = {}
    try:
        import build_buy
        point = position(f, i, j, level)
    except Exception:
        return result
    for label, method in (('floor', 'has_floor_at_location'), ('outside', 'is_location_outside'),
                          ('pool', 'is_location_pool')):
        try:
            value = getattr(build_buy, method)(point, int(level))
            if value is not None:
                result[label] = bool(value)
        except Exception:
            pass
    return result


# ------------------------------------------------------------------- fitting

def test_fit(obj, def_id, point, angle, level, ignore=()):
    """(ok, reason): build_buy.test_location_for_object at an exact point."""
    try:
        import build_buy
        import sims4.math
        location = sims4.math.Location(sims4.math.Transform(point, sims4.math.angle_to_yaw_quaternion(angle)),
                                       surface(level))
        result = build_buy.test_location_for_object(obj, def_id, location, list(ignore))
    except Exception as ex:
        speech.log_line('tiles: placement test raised {!r}'.format(ex))
        return None, None
    if isinstance(result, tuple):
        ok = bool(result[0])
        errors = result[1] if len(result) > 1 else None
    else:
        ok, errors = bool(result), None
    if not ok and errors:
        key = str(errors)[:160]
        if key not in _logged_errors:
            _logged_errors.add(key)
            speech.log_line('tiles: placement refused: {}'.format(key))
    return ok, (reason(errors) if not ok else None)


def reason(errors):
    """A player-facing reason from EA's placement errors, when one is clear."""
    words = str(errors or '').lower()
    for needles, en, pl in ((('wall',), 'a wall is in the way', 'przeszkadza ściana'),
                            (('intersect', 'overlap', 'object', 'footprint'), 'something is in the way',
                             'coś przeszkadza'),
                            (('floor',), 'it needs a floor', 'wymaga podłogi'),
                            (('slope', 'terrain'), 'the ground is not flat enough', 'teren nie jest dość płaski'),
                            (('pool', 'water'), 'water is in the way', 'przeszkadza woda'),
                            (('lot', 'bound'), 'it would leave the lot', 'wyszedłby poza parcelę')):
        if any(needle in words for needle in needles):
            return text(en, pl)
    return text('the game will not allow it here', 'gra nie pozwala na to tutaj')


def fit_at(f, def_id, i, j, level, facing, obj=None):
    """(point, None) for the first origin in the tile that fits, or
    (None, reason), or (None, None) when the game could not be asked."""
    first_reason = None
    asked = False
    angle = f.yaw(facing)
    for du, dv in OFFSETS:
        try:
            point = position(f, i, j, level, du, dv)
        except Exception:
            continue
        ok, why = test_fit(obj, def_id, point, angle, level)
        if ok is None:
            continue
        asked = True
        if ok:
            return point, None
        if first_reason is None:
            first_reason = why
    return None, (first_reason if asked else None)


def nearest_fit(f, def_id, i, j, level, facing, radius=NEAREST_RADIUS):
    """(ni, nj, point, facing) of the closest tile where it fits, trying the
    current facing before the others; None when nothing fits nearby."""
    facings = [facing] + [index for index in range(4) if index != facing]
    for ring in range(1, radius + 1):
        tiles = []
        for di in range(-ring, ring + 1):
            for dj in range(-ring, ring + 1):
                if max(abs(di), abs(dj)) != ring:
                    continue
                ni, nj = i + di, j + dj
                if f.inside(ni, nj):
                    tiles.append((di * di + dj * dj, ni, nj))
        tiles.sort()
        for option in facings:
            for _distance, ni, nj in tiles:
                point, _why = fit_at(f, def_id, ni, nj, level, option)
                if point is not None:
                    return ni, nj, point, option
    return None


def covered_tiles(f, obj, level):
    """Tiles whose centre the object's footprint covers (up to a 7 by 7 area)."""
    try:
        ci, cj = f.tile_of(obj.position.x, obj.position.z)
        footprint = obj.footprint_polygon
    except Exception:
        return []
    tiles = []
    for di in range(-3, 4):
        for dj in range(-3, 4):
            try:
                if footprint is not None and footprint.contains(position(f, ci + di, cj + dj, level)):
                    tiles.append((ci + di, cj + dj))
            except Exception:
                continue
    return tiles or [(ci, cj)]
