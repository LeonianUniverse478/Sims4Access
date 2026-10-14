# TS4 Access Plus - rooms: Alt+R lists the rooms of the house with their contents,
# Alt+W says which room the active Sim is in. Rooms are named from what is inside them.
import math
import tyjokr_a11y_plus_core as core

COMPASS = ("north", "north east", "east", "south east", "south", "south west", "west", "north west")
# (room name, tags that make a room that kind, weight)
KINDS = (
    ("Bathroom", ("BuyCatPA_Toilet", "BuyCatPA_Shower", "BuyCatPA_Tub", "Func_Bathtub"), 5),
    ("Kitchen", ("BuyCatPA_Refrigerator", "BuyCatPA_Stove", "Func_Fridge", "Func_Refrigerator", "Func_Oven"), 5),
    ("Nursery", ("Func_Crib",), 6),
    ("Bedroom", ("BuyCatSS_Bed",), 4),
    ("Dining room", ("BuyCatSS_DiningTable",), 2),
    ("Living room", ("BuyCatSS_Sofa", "BuyCatSS_LoveSeat", "BuyCatEE_TV", "Func_TV", "Func_Television"), 2),
    ("Study", ("BuyCatSS_Desk", "BuyCatEE_Computer", "BuyCatSS_Bookshelf"), 1),
)


def floor_name(level):
    if level == 0:
        return "ground floor"
    if level < 0:
        return "basement" if level == -1 else "basement level {}".format(-level)
    return {1: "first floor up", 2: "second floor up", 3: "third floor up"}.get(level, "floor {}".format(level))


def bearing(dx, dz):
    angle = math.degrees(math.atan2(dx, dz)) % 360.0
    return COMPASS[int((angle + 22.5) % 360.0 // 45) % 8]


def tag_names(obj):
    names = set()
    try:
        from tag import Tag
        for t in obj.definition.get_tags() or ():
            try:
                names.add(str(Tag(t).name))
            except Exception:
                pass
    except Exception:
        pass
    return names


def room_id_at(x, z, level, y=None):
    import build_buy, services, terrain, sims4.math
    if y is None:
        try:
            y = terrain.get_terrain_height(x, z)
        except Exception:
            y = 0.0
    pos = sims4.math.Vector3(float(x), float(y), float(z))
    try:
        rid = build_buy.get_room_id(services.current_zone_id(), pos, int(level))
    except Exception:
        core.log_exc("get_room_id")
        return 0
    return int(rid or 0)


def _obj_room(obj):
    try:
        return room_id_at(obj.position.x, obj.position.z, int(obj.level), obj.position.y)
    except Exception:
        return 0


class Room(object):
    def __init__(self, rid, level):
        self.rid = rid
        self.level = level
        self.tiles = []
        self.objects = []
        self.sims = []
        self.name = "Room"

    @property
    def center(self):
        xs = [t[0] for t in self.tiles] or [0]
        zs = [t[1] for t in self.tiles] or [0]
        return (sum(xs) / len(xs), sum(zs) / len(zs))

    def size_text(self):
        n = len(self.tiles)
        if not n:
            return ""
        xs = [t[0] for t in self.tiles]
        zs = [t[1] for t in self.tiles]
        w = int(round(max(xs) - min(xs))) + 1
        d = int(round(max(zs) - min(zs))) + 1
        if w * d == n:
            return "{} by {} meters".format(w, d)
        return "about {} square meters".format(n)


def scan_rooms():
    """Return list of Room, indoor rooms only, on every floor of the active lot."""
    import services
    lot = services.active_lot()
    if lot is None:
        return []
    corners = list(lot.corners)
    c0, c1, c3 = corners[0], corners[1], corners[3]
    ux, uz = c1.x - c0.x, c1.z - c0.z
    vx, vz = c3.x - c0.x, c3.z - c0.z
    nu = max(1, int(round(math.hypot(ux, uz))))
    nv = max(1, int(round(math.hypot(vx, vz))))
    try:
        levels = range(int(lot.min_level), int(lot.max_level) + 1)
    except Exception:
        levels = range(0, 3)
    rooms = {}
    for level in levels:
        for i in range(nu):
            for j in range(nv):
                fu, fv = (i + 0.5) / nu, (j + 0.5) / nv
                x = c0.x + ux * fu + vx * fv
                z = c0.z + uz * fu + vz * fv
                rid = room_id_at(x, z, level)
                if rid:
                    room = rooms.get((rid, level))
                    if room is None:
                        room = rooms[(rid, level)] = Room(rid, level)
                    room.tiles.append((x, z))
    # The biggest "room" on the ground floor that touches the lot edge is the yard, not a room.
    for key in list(rooms):
        room = rooms[key]
        if len(room.tiles) > 0.5 * nu * nv:
            del rooms[key]
    by_id = {}
    for room in rooms.values():
        by_id.setdefault(room.rid, room)
    for obj in services.object_manager().values():
        try:
            if obj.is_sim or not getattr(obj, "is_on_active_lot", lambda: True)():
                continue
            if getattr(obj, "is_in_inventory", lambda: False)():
                continue
            if not any(n.startswith("BuyCat") for n in tag_names(obj)):
                continue        # helpers and hidden game objects, not furniture
            rid = _obj_room(obj)
            room = rooms.get((rid, int(obj.level)))
            if room is not None:
                room.objects.append(obj)
        except Exception:
            continue
    for info in core.household_sims():
        sim = info.get_sim_instance()
        rid = _obj_room(sim)
        room = rooms.get((rid, int(sim.level)))
        if room is not None:
            room.sims.append(sim)
    _name_rooms(list(rooms.values()))
    out = sorted(rooms.values(), key=lambda r: (r.level, r.name, -len(r.tiles)))
    core.log("rooms: lot {}x{}, {} rooms: {}".format(nu, nv, len(out),
             ", ".join("{}({} tiles, {} objs, level {})".format(r.name, len(r.tiles), len(r.objects), r.level) for r in out)))
    return out


# ---------------------------------------------------------------- names given by the player
# Saved per lot in Mods\TS4_Access_Plus_rooms.txt: zone, level, room box (world tile centers), name.
import os
NAMES_PATH = os.path.join(core.MODS_FOLDER, "TS4_Access_Plus_rooms.txt")
_names = {}     # (zone, level, x0, z0, x1, z1) -> name
_names_loaded = [False]


def _box_key(room):
    import services
    xs = [t[0] for t in room.tiles] or [0]
    zs = [t[1] for t in room.tiles] or [0]
    return (int(services.current_zone_id()), int(room.level),
            int(round(min(xs))), int(round(min(zs))), int(round(max(xs))), int(round(max(zs))))


def _load_names():
    if _names_loaded[0]:
        return
    _names_loaded[0] = True
    try:
        if os.path.isfile(NAMES_PATH):
            with open(NAMES_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) == 7:
                        _names[tuple(int(v) for v in parts[:6])] = parts[6]
    except Exception:
        core.log_exc("load room names")


def _save_names():
    if not core.IN_GAME:
        return
    try:
        with open(NAMES_PATH, "w", encoding="utf-8") as f:
            for (key, name) in _names.items():
                f.write("\t".join(str(v) for v in key) + "\t" + name + "\n")
    except Exception:
        core.log_exc("save room names")


def set_room_name(room, name):
    _load_names()
    key = _box_key(room)
    if name:
        _names[key] = name
    else:
        _names.pop(key, None)
    _save_names()
    room.name = name or room.name


def given_name(room):
    _load_names()
    try:
        return _names.get(_box_key(room))
    except Exception:
        return None


def _name_rooms(rooms):
    given = [(room, given_name(room)) for room in rooms]
    rooms = [room for (room, name) in given if not name]
    for (room, name) in given:
        if name:
            room.name = name
    counts = {}
    for room in rooms:
        score = {}
        for obj in room.objects:
            names = tag_names(obj)
            for (kind, tags, weight) in KINDS:
                if names.intersection(tags):
                    score[kind] = score.get(kind, 0) + weight
        if score:
            room.name = max(score.items(), key=lambda kv: kv[1])[0]
        elif not room.objects:
            room.name = "Empty room"
        else:
            room.name = "Room"
        counts[room.name] = counts.get(room.name, 0) + 1
    numbered = {}
    for room in sorted(rooms, key=lambda r: (r.level, -len(r.tiles))):
        if counts[room.name] > 1:
            numbered[room.name] = numbered.get(room.name, 0) + 1
            room.name = "{} {}".format(room.name, numbered[room.name])


def _where_text(room, sim):
    (cx, cz) = room.center
    dx, dz = cx - sim.position.x, cz - sim.position.z
    dist = int(round(math.hypot(dx, dz)))
    text = floor_name(room.level)
    if sim in room.sims or dist < 1:
        return "you are here, " + text
    return "{} meters {}, {}".format(dist, bearing(dx, dz), text)


@core.hotkey(ord("R"), "rooms")
def open_rooms():
    sim = core.active_sim()
    if sim is None:
        core.speak("No active Sim.")
        return
    rooms = scan_rooms()
    if not rooms:
        core.speak("No rooms found on this lot.")
        return
    rows = []
    for room in rooms:
        who = ", ".join(s.sim_info.first_name for s in room.sims)
        desc = "{}. {}. {} objects{}.".format(room.size_text(), _where_text(room, sim), len(room.objects),
                                              (". " + who + " here") if who else "")
        rows.append((room.name, desc, room))
    core.choose("Rooms", "{} rooms in this house. Choose a room to hear what is in it.".format(len(rooms)),
                rows, _open_room, tag="rooms")


def _open_room(room):
    sim = core.active_sim()
    if sim is None:
        return
    rows = []
    entries = []
    for s in room.sims:
        entries.append((s, s.sim_info.first_name))
    for obj in room.objects:
        entries.append((obj, None))
    for (obj, label) in entries:
        dx, dz = obj.position.x - sim.position.x, obj.position.z - sim.position.z
        dist = int(round(math.hypot(dx, dz)))
        desc = "here" if dist < 1 else "{} meters {}".format(dist, bearing(dx, dz))
        if label is None:
            try:
                label = obj.catalog_name
                from protocolbuffers.Localization_pb2 import LocalizedString
                if not isinstance(label, LocalizedString):
                    from sims4.localization import _create_localized_string
                    label = _create_localized_string(int(getattr(label, "hash", label)))
            except Exception:
                label = "Object"
        rows.append((label, desc + ". Choose to see its actions.", obj, False, obj))
    if not rows:
        core.speak("{} is empty.".format(room.name))
        return
    core.choose(room.name, "{}, {}. {} things. Choose one to open its actions.".format(
        room.name, room.size_text(), len(rows)), rows, core.open_interactions, tag="rooms")


@core.hotkey(ord("W"), "where am I")
def where_am_i():
    import build_buy
    sim = core.active_sim()
    if sim is None:
        core.speak("No active Sim.")
        return
    rid = _obj_room(sim)
    name = None
    if rid:
        for room in scan_rooms():
            if room.rid == rid:
                name = room.name
                break
    try:
        outside = build_buy.is_location_outside(sim.position, int(sim.level))
    except Exception:
        outside = None
    where = name or ("outside" if outside else "inside")
    core.speak("{} is in the {}, {}.".format(sim.sim_info.first_name, where, floor_name(int(sim.level)))
               if name else "{} is {}, {}.".format(sim.sim_info.first_name, where, floor_name(int(sim.level))))
