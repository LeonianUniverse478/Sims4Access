"""A keyboard cursor over the lot's tile grid.

The lot is a 1-metre grid, which is the only discrete structure in an otherwise
continuous 3D space - the same reason a tile grid makes Stardew navigable. We
compute it ourselves rather than depending on the client's grid view, so this
works whether or not build mode is showing it.

Read-only. Nothing here places, moves or deletes anything.
"""
import math

import a11yscan_log as logfile
import a11yscan_world as world

_active = False
_x = 0.0
_z = 0.0
_y = 0.0
_level = 0
_origin = (0.0, 0.0)
_objects = {}


def active():
    return _active


def _tile_key(x, z):
    return (int(math.floor(x + 0.5)), int(math.floor(z + 0.5)))


def _build_object_map(level):
    """Tile -> names, so each step can be described without rescanning."""
    tiles = {}
    try:
        for obj in world._iter_objects():
            try:
                if callable(getattr(obj, 'is_in_inventory', None)) and obj.is_in_inventory():
                    continue
                position = obj.position
                obj_level = int(getattr(obj, 'level', 0) or 0)
                if obj_level != level:
                    continue
                key = _tile_key(float(position.x), float(position.z))
                # The object itself alongside its name. Keeping only names
                # meant the grid could say what was on a tile but nothing
                # could act on it - which is why selling from grid mode found
                # nothing to sell.
                tiles.setdefault(key, []).append((world.object_name(obj), obj))
            except Exception:
                continue
    except Exception as ex:
        logfile.write('grid: object map failed ({!r})'.format(ex))
    return tiles


def enter():
    """Put the cursor on the active Sim's tile."""
    global _active, _x, _z, _y, _level, _origin, _objects
    sim = world.active_sim()
    if sim is None:
        return 'No active Sim.'
    try:
        position = sim.position
        _x, _y, _z = float(position.x), float(position.y), float(position.z)
        _level = int(getattr(sim, 'level', 0) or 0)
    except Exception as ex:
        logfile.write('grid: could not read Sim position ({!r})'.format(ex))
        return 'Could not find your Sim.'
    _origin = (_x, _z)
    _objects = _build_object_map(_level)
    _active = True
    logfile.write('grid: entered at {} with {} occupied tiles'.format(
        _tile_key(_x, _z), len(_objects)))
    return 'Grid on. Arrows to move, enter to describe, backspace to leave. {}'.format(
        describe())


def leave():
    global _active
    _active = False
    return 'Grid off.'


def _position():
    import sims4.math
    return sims4.math.Vector3(_x, _y, _z)


# The eight neighbours, in reading order, as (dx, dz).
_NEIGHBOURS = ((-1, 1), (0, 1), (1, 1),
               (-1, 0), (1, 0),
               (-1, -1), (0, -1), (1, -1))
# The four that matter for a corridor: north, south, east, west.
_CARDINALS = {'north': (0, 1), 'south': (0, -1),
              'east': (1, 0), 'west': (-1, 0)}


def _routing_context():
    try:
        sim = world.active_sim()
        return sim.routing_surface, sim.routing_context
    except Exception:
        return None, None


def _walkable(x, z, surface, context):
    """Can a Sim stand here? Asked of the navmesh, not guessed from objects."""
    try:
        import routing
        from sims4.math import Vector3
        spot = Vector3(x, _y, z)
        location = routing.Location(spot, routing_surface=surface)
        return bool(routing.test_point_placement_in_navmesh(context, location))
    except Exception:
        return None


MAX_CLEARANCE = 8


def clearance():
    """How many walkable tiles run in each direction from here.

    The footprint of the thing you are about to place cannot be read reliably
    - test_location_for_object is native with no signature to go on - so
    rather than guess an object's size, this measures the SPACE. "Four tiles
    east, one west" tells you a two-tile sofa fits east and not west, whatever
    the sofa happens to be.
    """
    surface, context = _routing_context()
    if surface is None:
        return {}
    out = {}
    for name, (dx, dz) in _CARDINALS.items():
        run = 0
        for step in range(1, MAX_CLEARANCE + 1):
            if not _walkable(_x + dx * step, _z + dz * step, surface, context):
                break
            run += 1
        out[name] = run
    return out


def clearance_phrase():
    room = clearance()
    if not room:
        return None
    # Only the directions with space; listing four zeroes helps nobody.
    parts = ['{} {}'.format(count, name)
             for name, count in sorted(room.items()) if count]
    if not parts:
        return 'no room around it'
    return 'room: ' + ', '.join(parts)


def pathing_advice():
    """Whether building here would get in a Sim's way.

    Placement is the one part of build mode with no substitute for seeing it:
    a chair in the middle of a doorway looks obviously wrong and reads
    identically to a chair against a wall. So the navmesh is asked about this
    tile and the eight around it, and the shape of the answer says what kind
    of spot this is.

    A tile with walkable neighbours on opposite sides and blocked ones either
    side of them is a doorway or a corridor - fill it and Sims have to go
    round, or cannot get through at all.
    """
    surface, context = _routing_context()
    if surface is None:
        return None
    here = _walkable(_x, _z, surface, context)
    if here is None:
        return None
    if not here:
        return 'not walkable anyway, safe to build on'

    open_dirs = []
    for name, (dx, dz) in _CARDINALS.items():
        if _walkable(_x + dx, _z + dz, surface, context):
            open_dirs.append(name)
    walkable_around = 0
    for dx, dz in _NEIGHBOURS:
        if _walkable(_x + dx, _z + dz, surface, context):
            walkable_around += 1

    opposite = (('north' in open_dirs and 'south' in open_dirs)
                or ('east' in open_dirs and 'west' in open_dirs))
    if opposite and len(open_dirs) == 2:
        return ('a walkway between {} - building here will block the way '
                'through'.format(' and '.join(sorted(open_dirs))))
    if walkable_around <= 2:
        return 'a tight corner, good place to build'
    if walkable_around <= 4:
        return 'against a wall, usually fine to build on'
    if opposite:
        return ('open floor but on a through route - Sims can go round, but '
                'it is in the way')
    return 'open floor, clear to build on'


def _tile_facts():
    """What the game says about the tile under the cursor."""
    facts = []
    position = None
    try:
        position = _position()
    except Exception:
        return facts
    try:
        import services
        lot = services.active_lot()
        if lot is not None and not lot.is_position_on_lot(position):
            facts.append('off lot')
    except Exception:
        pass
    try:
        import build_buy
        if build_buy.has_floor_at_location(position, _level):
            facts.append('floor')
        else:
            facts.append('no floor')
        if build_buy.is_location_pool(position, _level):
            facts.append('pool')
        if build_buy.is_location_natural_ground(position, _level):
            facts.append('ground')
        if build_buy.is_location_outside(position, _level):
            facts.append('outside')
        else:
            facts.append('inside')
    except Exception as ex:
        logfile.write('grid: location queries failed ({!r})'.format(ex))
    return facts


def objects_here():
    """(name, object) for everything on the tile under the cursor."""
    return list(_objects.get(_tile_key(_x, _z)) or [])


def describe(full=False):
    """One tile, spoken."""
    key = _tile_key(_x, _z)
    names = [name for name, _obj in (_objects.get(key) or [])]
    parts = []
    if names:
        parts.append(', '.join(names[:3]))
        if len(names) > 3:
            parts.append('and {} more'.format(len(names) - 3))
    facts = _tile_facts()
    if not names:
        parts.append(', '.join(facts) if facts else 'empty')
    elif full:
        parts.extend(facts)
    # The part you cannot get any other way: whether this spot is in a Sim's
    # path. Said on every tile, because it is the whole reason to be here.
    try:
        advice = pathing_advice()
    except Exception as ex:
        logfile.write('grid: pathing advice failed ({!r})'.format(ex))
        advice = None
    if advice:
        parts.append(advice)
    # Only on the detailed reading: the clearance is the number you want when
    # deciding where something fits, not on every step across a room.
    if full:
        try:
            room = clearance_phrase()
        except Exception as ex:
            logfile.write('grid: clearance failed ({!r})'.format(ex))
            room = None
        if room:
            parts.append(room)
    if full:
        east = int(round(_x - _origin[0]))
        north = int(round(_z - _origin[1]))
        where = []
        if east:
            where.append('{} {}'.format(abs(east), 'east' if east > 0 else 'west'))
        if north:
            where.append('{} {}'.format(abs(north), 'north' if north > 0 else 'south'))
        parts.append('at start' if not where else ' and '.join(where) + ' of start')
        parts.append('level {}'.format(_level))
    return '. '.join(p for p in parts if p)


def cursor():
    """(position, level, routing_surface) under the cursor, or None."""
    try:
        position = _position()
    except Exception:
        return None
    surface = None
    try:
        sim = world.active_sim()
        surface = sim.routing_surface
    except Exception:
        surface = None
    return (position, _level, surface)


def focus_position(position, level=None):
    """Put the cursor where an object actually ended up.

    The game chooses the exact spot, which may not be the tile that was
    pointed at - so the cursor follows it. Otherwise you place something, it
    lands a tile over, and the grid still describes where you were.
    """
    global _x, _z, _level
    try:
        _x = float(position.x)
        _z = float(position.z)
        if level is not None:
            _level = int(level)
    except Exception as ex:
        logfile.write('grid: could not move the cursor ({!r})'.format(ex))
        return False
    refresh()
    return True


def refresh():
    global _objects
    _objects = _build_object_map(_level)
    return describe()


def move(dx, dz):
    global _x, _z
    if not _active:
        return 'Grid is off.'
    _x += dx
    _z += dz
    return describe()


def up_level():
    global _level, _objects
    _level += 1
    _objects = _build_object_map(_level)
    return 'Level {}. {}'.format(_level, describe())


def down_level():
    global _level, _objects
    _level -= 1
    _objects = _build_object_map(_level)
    return 'Level {}. {}'.format(_level, describe())
