# TS4 Access Plus - "Build my house" and door tools (in the build helper, Alt+B).
# Build my house: the player picks the rooms; we lay them out (front row: living room and kitchen,
# a hallway behind them, bedrooms and bathrooms at the back), build each room with the Room Tool,
# put a front door into the living room and a door from every room to the room it opens onto,
# and name the rooms. Door tools: a door between two rooms (or to the yard), and removing a door
# or window. Everything uses the build helper's pointing (tyjokr_a11y_plus_build).
import math, threading, time
import tyjokr_a11y_plus_core as core
import tyjokr_a11y_plus_build as build

WALL_PRICE = 60         # Room Tool, per meter of wall (measured)
FRONT_DEPTH, HALL_DEPTH, BACK_DEPTH = 5, 2, 4
SETBACK = 2             # meters of front yard between the street side of the lot and the house

# kind -> (row, width, name)
KINDS = {
    "living": ("front", 6, "Living room"),
    "kitchen": ("front", 4, "Kitchen"),
    "dining": ("front", 4, "Dining room"),
    "bedroom": ("back", 4, "Bedroom"),
    "bathroom": ("back", 3, "Bathroom"),
    "study": ("back", 3, "Study"),
}
PRESETS = (
    ("Living room, kitchen, bathroom and 1 bedroom", ["living", "kitchen", "bathroom", "bedroom"]),
    ("Living room, kitchen, bathroom and 2 bedrooms", ["living", "kitchen", "bathroom", "bedroom", "bedroom"]),
    ("Living room, kitchen, bathroom and 3 bedrooms", ["living", "kitchen", "bathroom", "bedroom", "bedroom", "bedroom"]),
    ("Living room, kitchen, 2 bathrooms and 3 bedrooms",
     ["living", "kitchen", "bathroom", "bathroom", "bedroom", "bedroom", "bedroom"]),
)
# Two-floor houses for smaller lots: (label, variant). See make_two_floor_plan.
TWO_FLOOR_PRESETS = (
    ("Two floors, 3 bedrooms. Downstairs: living room, kitchen, dining room and bathroom. "
     "Upstairs: 3 bedrooms and a bathroom", "3bed"),
    ("Two floors, 4 bedrooms. Downstairs: living room, kitchen, a bedroom and bathroom. "
     "Upstairs: 3 bedrooms and a bathroom", "4bed"),
    ("Two floors, 2 bedrooms. Downstairs: living room, kitchen, dining room and bathroom. "
     "Upstairs: 2 bedrooms, a study and a bathroom", "2bed"),
)
TWO_W = 10              # a two-floor house is 10 meters along the street and 11 deep
STAIRS = ("Unremarkable Staircase", "Stairs", "Sturdy Stairs")
STAIR_LEN = 3           # tiles of steps, for normal wall height (measured October 2026)
STAIR_PRICE = 600
INTERIOR_DOORS = ("Simple Single-Panel Door", "HBD Interior Door", "Simple Two-Panel Door")
FRONT_DOORS = ("Wooden Four-Panel Door", "HBD Front Door", "Simple Single-Panel Door")

# ---------------------------------------------------------------- which side is the street


def street_side():
    """The lot edge nearest the place where Sims arrive: 'north', 'south', 'west' or 'east'."""
    import services
    f = build.frame()
    point = None
    try:
        sp = services.current_zone().active_lot_arrival_spawn_point
        c = sp.get_approximate_center()
        point = f.local(c.x, c.z)
    except Exception:
        core.log_exc("arrival spawn point")
    if point is None:
        return "north"
    (e, n) = point
    dist = {"north": abs(n), "south": abs(f.depth - n), "west": abs(e), "east": abs(f.width - e)}
    return min(dist, key=dist.get)

# ---------------------------------------------------------------- layout
# Planned in house coordinates: u along the street (left to right seen from the street),
# v away from the street (0 = the front wall). Then mapped to meters from the west and north edges.


class Plan(object):
    def __init__(self):
        self.rooms = []     # dicts: name, kind, uv=(u0, v0, u1, v1), box=(e0, n0, e1, n1)
        self.doors = []     # dicts: what, a=(u, v) tile inside, b=(u, v) tile on the other side, front
        self.width = 0
        self.depth = 0
        self.side = "north"
        self.problem = None
        self.floors = 1
        self.stairs = None   # dict: top=(u, v) highest step tile, climb=(du, dv); mapped: top_lot, climb_lot


def _names_for(kinds):
    counts = {}
    for k in kinds:
        counts[k] = counts.get(k, 0) + 1
    seen = {}
    out = []
    for k in kinds:
        base = KINDS[k][2]
        if counts[k] > 1:
            seen[k] = seen.get(k, 0) + 1
            out.append("{} {}".format(base, seen[k]))
        else:
            out.append(base)
    return out


def make_plan(kinds):
    f = build.frame()
    p = Plan()
    p.side = street_side()
    names = _names_for(kinds)
    front = [(k, n) for (k, n) in zip(kinds, names) if KINDS[k][0] == "front"]
    back = [(k, n) for (k, n) in zip(kinds, names) if KINDS[k][0] == "back"]
    if not any(k == "living" for (k, _n) in front):
        front.insert(0, ("living", "Living room"))
    # Living room first (left), then kitchen, then dining room.
    order = {"living": 0, "kitchen": 1, "dining": 2}
    front.sort(key=lambda kn: order[kn[0]])
    # Back row: bathrooms between bedrooms, a study at the end.
    beds = [kn for kn in back if kn[0] == "bedroom"]
    baths = [kn for kn in back if kn[0] == "bathroom"]
    others = [kn for kn in back if kn[0] not in ("bedroom", "bathroom")]
    row = []
    while beds or baths:
        if beds:
            row.append(beds.pop(0))
        if baths:
            row.append(baths.pop(0))
    back = row + others
    fw = [KINDS[k][1] for (k, _n) in front]
    bw = [KINDS[k][1] for (k, _n) in back]
    width = max(sum(fw), sum(bw))
    fw[0] += width - sum(fw)            # the living room takes up any spare width
    if back and sum(bw) < width:
        spare = width - sum(bw)
        i = 0
        while spare > 0:                # bedrooms grow first
            j = i % len(back)
            if back[j][0] == "bedroom" or all(k != "bedroom" for (k, _n) in back):
                bw[j] += 1
                spare -= 1
            i += 1
    depth = FRONT_DEPTH + (HALL_DEPTH + BACK_DEPTH if back else 0)
    along, deep = (f.width, f.depth) if p.side in ("north", "south") else (f.depth, f.width)
    if width > along - 2 or depth > deep - SETBACK - 1:
        p.problem = ("A house of {} by {} meters does not fit on this {} by {} meter lot. Choose fewer rooms, "
                     "or one of the two-floor houses, which need only 10 by 11 meters.").format(width, depth, f.width, f.depth)
        return p
    p.width, p.depth = width, depth
    u = 0
    rooms = []
    for ((k, name), w) in zip(front, fw):
        rooms.append({"kind": k, "name": name, "uv": (u, 0, u + w, FRONT_DEPTH)})
        u += w
    living = rooms[0]
    if back:
        hall = {"kind": "hall", "name": "Hallway", "uv": (0, FRONT_DEPTH, width, FRONT_DEPTH + HALL_DEPTH)}
        rooms.append(hall)
        u = 0
        v0 = FRONT_DEPTH + HALL_DEPTH
        for ((k, name), w) in zip(back, bw):
            rooms.append({"kind": k, "name": name, "uv": (u, v0, u + w, v0 + BACK_DEPTH)})
            u += w
    for r in rooms:
        r["level"] = 0
    p.rooms = rooms
    # Doors.
    (lu0, _, lu1, _) = living["uv"]
    mid = (lu0 + lu1) // 2
    p.doors.append({"what": "Front door into the living room", "a": (mid, 0), "b": (mid, -1), "front": True})
    for i in range(1, len(front)):
        left, right = rooms[i - 1], rooms[i]
        p.doors.append({"what": "Door between the {} and the {}".format(left["name"].lower(), right["name"].lower()),
                        "a": (left["uv"][2] - 1, FRONT_DEPTH // 2), "b": (left["uv"][2], FRONT_DEPTH // 2), "front": False})
    if back:
        p.doors.append({"what": "Door from the living room to the hallway",
                        "a": (mid, FRONT_DEPTH - 1), "b": (mid, FRONT_DEPTH), "front": False})
        for r in rooms:
            if r["kind"] in ("hall",) or KINDS.get(r["kind"], ("front",))[0] != "back":
                continue
            (u0, v0, u1, _v1) = r["uv"]
            m = (u0 + u1) // 2
            p.doors.append({"what": "Door from the hallway to {}".format(r["name"].lower()),
                            "a": (m, v0), "b": (m, v0 - 1), "front": False})
    for d in p.doors:
        d["level"] = 0
    _map_plan(p, f, along)
    return p


def _map_plan(p, f, along):
    """House coordinates to lot meters, for rooms, doors and stairs."""
    u_off = (along - p.width) // 2
    for r in p.rooms:
        (u0, v0, u1, v1) = r["uv"]
        (e0, n0) = _to_lot(p, f, u_off, u0, v0)
        (e1, n1) = _to_lot(p, f, u_off, u1, v1)
        r["box"] = (min(e0, e1), min(n0, n1), max(e0, e1), max(n0, n1))
    for d in p.doors:
        d["tile_a"] = _tile_to_lot(p, f, u_off, d["a"])
        d["tile_b"] = _tile_to_lot(p, f, u_off, d["b"])
    if p.stairs:
        p.stairs["top_lot"] = _tile_to_lot(p, f, u_off, p.stairs["top"])
        p.stairs["climb_lot"] = _dir_to_lot(p, p.stairs["climb"])


def _the(name):
    """'the dining room', but 'bedroom 4' (a numbered room needs no 'the')."""
    return name.lower() if name[-1].isdigit() else "the " + name.lower()


def _dir_to_lot(p, d):
    """A direction (du, dv) in house coordinates to (de, dn) on the lot."""
    (du, dv) = d
    return {"north": (du, dv), "south": (-du, -dv), "west": (dv, -du), "east": (-dv, du)}[p.side]


def make_two_floor_plan(variant):
    """A 10 by 11 meter house with two floors. Both floors: a 5 meter deep front row, a 2 meter hallway
    across the house with the stairs in it, and a 4 meter deep back row."""
    f = build.frame()
    p = Plan()
    p.side = street_side()
    p.floors = 2
    W, F, H = TWO_W, FRONT_DEPTH, FRONT_DEPTH + HALL_DEPTH
    D = H + BACK_DEPTH
    along, deep = (f.width, f.depth) if p.side in ("north", "south") else (f.depth, f.width)
    if W > along - 2 or D > deep - SETBACK - 1:
        p.problem = ("Even a two-floor house, {} by {} meters, does not fit on this {} by {} meter lot. "
                     "Choose a bigger lot.").format(W, D, f.width, f.depth)
        return p
    p.width, p.depth = W, D
    down_back = ("bedroom", "Bedroom 4") if variant == "4bed" else ("dining", "Dining room")
    up_back = ("study", "Study") if variant == "2bed" else ("bedroom", "Bedroom 3")

    def room(kind, name, uv, level):
        return {"kind": kind, "name": name, "uv": uv, "level": level}
    p.rooms = [
        room("living", "Living room", (0, 0, 6, F), 0),
        room("kitchen", "Kitchen", (6, 0, W, F), 0),
        room("hall", "Hallway", (0, F, W, H), 0),
        room(down_back[0], down_back[1], (0, H, 7, D), 0),
        room("bathroom", "Bathroom", (7, H, W, D), 0),
        room("bedroom", "Bedroom 1", (0, 0, 5, F), 1),
        room("bedroom", "Bedroom 2", (5, 0, W, F), 1),
        room("hall", "Upstairs hallway", (0, F, W, H), 1),
        room(up_back[0], up_back[1], (0, H, 7, D), 1),
        room("bathroom", "Upstairs bathroom", (7, H, W, D), 1),
    ]

    def door(what, a, b, level, front=False):
        return {"what": what, "a": a, "b": b, "level": level, "front": front}
    # The stairs sit in the front half of the hallway and go up toward the right (seen from the street):
    # steps on the 3 tiles before the last one; you step on downstairs at the left end and step off
    # upstairs at the right end, by the door of bedroom 2. Doors stay clear of the stairs.
    p.stairs = {"top": (W - 2, F), "climb": (1, 0)}
    p.doors = [
        door("Front door into the living room", (3, 0), (3, -1), 0, True),
        door("Door between the living room and the kitchen", (5, 2), (6, 2), 0),
        door("Door from the living room to the hallway", (3, F - 1), (3, F), 0),
        door("Door from the hallway to the {}".format(_the(down_back[1])), (3, H), (3, H - 1), 0),
        door("Door from the hallway to the bathroom", (8, H), (8, H - 1), 0),
        door("Upstairs, door from the hallway to bedroom 1", (2, F - 1), (2, F), 1),
        door("Upstairs, door from the hallway to bedroom 2", (W - 1, F - 1), (W - 1, F), 1),
        door("Upstairs, door from the hallway to {}".format(_the(up_back[1])), (3, H), (3, H - 1), 1),
        door("Upstairs, door from the hallway to the upstairs bathroom", (8, H), (8, H - 1), 1),
    ]
    _map_plan(p, f, along)
    return p


def _to_lot(p, f, u_off, u, v):
    """House point (u, v) to (meters from west, meters from north)."""
    u += u_off
    v += SETBACK
    if p.side == "north":
        return (u, v)
    if p.side == "south":
        return (f.width - u, f.depth - v)
    if p.side == "west":
        return (v, f.depth - u)
    return (f.width - v, u)


def _tile_to_lot(p, f, u_off, tile):
    (e, n) = _to_lot(p, f, u_off, tile[0] + 0.5, tile[1] + 0.5)
    return (int(math.floor(e)), int(math.floor(n)))


def wall_meters(p):
    total = 0
    for level in set(r.get("level", 0) for r in p.rooms):
        total += _wall_meters([r for r in p.rooms if r.get("level", 0) == level])
    return total


def _wall_meters(room_list):
    edges = set()
    for r in room_list:
        (e0, n0, e1, n1) = r["box"]
        for e in range(e0, e1):
            edges.add(("h", e, n0))
            edges.add(("h", e, n1))
        for n in range(n0, n1):
            edges.add(("v", e0, n))
            edges.add(("v", e1, n))
    return len(edges)


def side_between(tile_a, tile_b):
    de, dn = tile_b[0] - tile_a[0], tile_b[1] - tile_a[1]
    if dn < 0:
        return "north"
    if dn > 0:
        return "south"
    if de < 0:
        return "west"
    return "east"

# ---------------------------------------------------------------- choosing


def build_my_house():
    if not build.in_build_mode():
        core.speak("Go to Build mode first. Press F2, on a laptop Fn+F2.")
        return
    rows = [(label, None, kinds) for (label, kinds) in PRESETS]
    rows += [(label, "Uses less of the lot: 10 by 11 meters, with stairs in the hallway.", ("two", v))
             for (label, v) in TWO_FLOOR_PRESETS]
    rows.append(("Choose the rooms yourself", "Add rooms one at a time. One floor.", "custom"))

    def picked(value):
        if value == "custom":
            _custom([])
        else:
            _show_plan(value)
    core.choose("Build my house",
                "Choose the rooms. The house is built facing the street, with a front door into the living room, "
                "a hallway, and a door from each room. You hear the plan and the price before anything is built.",
                rows, picked, tag="build")


def _custom(kinds):
    names = ", ".join(_names_for(kinds)) if kinds else "no rooms yet"
    rows = []
    if kinds:
        rows.append(("Done, show the plan", "Rooms so far: {}.".format(names), "done"))
    for (k, (row, w, name)) in KINDS.items():
        if k == "living" and "living" in kinds:
            continue
        rows.append(("Add a {}".format(name.lower()), "{} meters wide, at the {}.".format(w, "front" if row == "front" else "back"), k))
    if kinds:
        rows.append(("Remove the last room", None, "undo"))

    def picked(value):
        if value == "done":
            _show_plan(kinds)
        elif value == "undo":
            _custom(kinds[:-1])
        else:
            core.speak("{} added.".format(KINDS[value][2]))
            _custom(kinds + [value])
    core.choose("Your rooms", "Rooms so far: {}. A living room is always included.".format(names), rows, picked, tag="build")


def _plan_text(p):
    if p.floors == 2:
        return _two_floor_text(p)
    parts = ["The house is {} meters along the street and {} meters deep, with {} of front yard.".format(
        p.width, p.depth, "2 meters")]
    front = [r for r in p.rooms if r["uv"][1] == 0]
    order = {"north": "west to east", "south": "east to west", "west": "south to north", "east": "north to south"}[p.side]
    parts.append("The front faces the street, on the {} side. At the front, from {}: ".format(p.side, order) +
                 ", ".join("{}, {} by {}".format(r["name"].lower(), r["uv"][2] - r["uv"][0], r["uv"][3] - r["uv"][1])
                           for r in front) + ".")
    back = [r for r in p.rooms if r["uv"][1] > FRONT_DEPTH]
    if back:
        parts.append("Behind them a hallway across the house. At the back, from {}: ".format(order) +
                     ", ".join("{}, {} by {}".format(r["name"].lower(), r["uv"][2] - r["uv"][0], r["uv"][3] - r["uv"][1])
                               for r in back) + ".")
    parts.append("Doors: " + "; ".join(d["what"].lower() for d in p.doors) + ".")
    return " ".join(parts)


def _two_floor_text(p):
    order = {"north": "west to east", "south": "east to west", "west": "south to north", "east": "north to south"}[p.side]

    def names(level, row):
        rs = [r for r in p.rooms if r["level"] == level and r["kind"] != "hall" and
              ((r["uv"][1] == 0) == (row == "front"))]
        return ", ".join("{}, {} by {}".format(r["name"].lower(), r["uv"][2] - r["uv"][0], r["uv"][3] - r["uv"][1]) for r in rs)
    return ("The house has two floors, {} meters along the street and {} meters deep, with 2 meters of front yard. "
            "The front faces the street, on the {} side. Rooms are listed from {}. "
            "Downstairs at the front: {}. Then a hallway across the house with the stairs in it. Downstairs at the back: {}. "
            "Upstairs at the front: {}. Then the upstairs hallway. Upstairs at the back: {}. "
            "Every room has a door to the hallway, and the front door goes into the living room.").format(
        p.width, p.depth, p.side, order, names(0, "front"), names(0, "back"), names(1, "front"), names(1, "back"))


def _show_plan(kinds):
    try:
        if isinstance(kinds, tuple):
            p = make_two_floor_plan(kinds[1])
        else:
            p = make_plan(list(kinds))
    except Exception:
        core.log_exc("make plan")
        core.speak("Sorry, the plan could not be made.")
        return
    if p.problem:
        core.speak(p.problem)
        return
    walls = wall_meters(p) * WALL_PRICE
    doors = len(p.doors) * 100
    stairs = STAIR_PRICE if p.stairs else 0
    cost = walls + doors + stairs
    money = build.funds() or 0
    text = "{} It costs about {:,} simoleons: {:,} for walls and floors, about {:,} for doors{}. You have {:,}.".format(
        _plan_text(p), cost, walls, doors, ", about {:,} for the stairs".format(stairs) if stairs else "", money)
    rows = [("Build it", "Takes a few minutes. Do not press keys until you hear that it is finished.", "go"),
            ("Hear the plan again", None, "again"),
            ("Cancel", None, None)]
    if cost > money:
        rows[0] = ("Not enough money", "Choose fewer rooms.", None)

    def picked(value):
        if value == "go":
            start_build(p)
        elif value == "again":
            _show_plan(kinds)
    core.choose("Your house plan", text, rows, picked, tag="build")

# ---------------------------------------------------------------- building


def _pick_door(names_wanted):
    """Worker thread: choose a door from the catalog. Returns its name or None."""
    items = build.fetch_catalog(2, "BUILDTAG_DOOR", "wall")
    if not items:
        return None
    names = [it[0] for it in items]
    index = None
    for want in names_wanted:
        if want in names:
            index = names.index(want)
            break
    if index is None:
        plain = [i for (i, it) in enumerate(items)
                 if not any(w in it[0].lower() for w in ("arch", "frame", "double", "wide", "sliding", "window", "commercial"))]
        index = plain[0] if plain else 0
    build._cat["silent_select"] = True
    try:
        build.select_item(index, names[index])
    finally:
        build._cat["silent_select"] = False
    return names[index]


def _pick_tool(name):
    items = build.fetch_catalog(16, "BUILDTAG_BLOCK_WALLTOOL,BUILDTAG_BLOCK_WITH_WALLS", "tool")
    names = [it[0] for it in items]
    if name not in names:
        return False
    build._cat["silent_select"] = True
    try:
        build.select_item(names.index(name), name)
    finally:
        build._cat["silent_select"] = False
    return True


def _stair_ids():
    import services
    import tyjokr_a11y_plus_rooms as rooms
    out = []
    for obj in services.object_manager().values():
        try:
            if "Build_Stair" in rooms.tag_names(obj):
                out.append(obj.id)
        except Exception:
            pass
    return out


def _stair_info(oid):
    """(e, n, climb) of a placed staircase: its position is the middle of the bottom edge of the lowest
    step, and its forward direction points to the side (measured October 2026)."""
    import services
    obj = services.object_manager().get(oid)
    if obj is None:
        return None
    (e, n) = build.frame().local(obj.position.x, obj.position.z)
    fx, fz = obj.forward.x, obj.forward.z
    return (e, n, (int(round(-fz)), int(round(-fx))))


def _pick_stairs():
    """Worker thread: the catalog index and name of plain stairs, or None."""
    items = build.fetch_catalog(14, "", "none")
    if not items:
        return None
    names = [it[0] for it in items]
    for want in STAIRS:
        if want in names:
            return (names.index(want), want)
    plain = [i for (i, n) in enumerate(names) if not any(w in n.lower() for w in ("ladder", "mega", "floating", "spiral"))]
    i = plain[0] if plain else 0
    return (i, names[i])


def place_stairs_worker(top, climb):
    """Worker thread only. Straight stairs on the ground floor going up to the floor above.
    top: lot tile (e, n) of the highest step; climb: direction (de, dn) going up.
    The pointer goes on the highest step. The game keeps the last way stairs were turned, so we
    place, check which way they went, and if wrong take them back, turn them (the . key) and try again.
    Returns True or a reason."""
    pick = _pick_stairs()
    if not pick:
        return "nocatalog"
    if not build.set_floor(0):
        return "nofloor"
    f = build.frame()
    want = (top[0] + 0.5 - (STAIR_LEN - 0.5) * climb[0], top[1] + 0.5 - (STAIR_LEN - 0.5) * climb[1])
    shift = [0.0, 0.0]
    turn = False
    for attempt in range(10):
        before = set(build.on_main(_stair_ids) or [])
        build._cat["silent_select"] = True
        try:
            build.select_item(*pick)
        finally:
            build._cat["silent_select"] = False
        if turn:
            build.tap_scan(0x34)        # the . key turns the stairs a quarter turn
            time.sleep(0.5)
            turn = False
        pt = f.world(top[0] + 0.5 + shift[0], top[1] + 0.5 + shift[1])

        def act(s):
            build.move_to(*build._to_screen(*s[0]))
            time.sleep(0.8)
            build.click(s[0])
        if not build.point_and_act([pt], 0, act, "stairs try {}".format(attempt + 1)):
            return "noscreen"
        time.sleep(0.5)
        new = [oid for oid in (build.on_main(_stair_ids) or []) if oid not in before]
        if not new:
            core.log("stairs: not placed: {}".format(build._last_error["text"]))
            turn = True
            continue
        info = build.on_main(_stair_info, new[0])
        core.log("stairs: placed {} want pos {} climb {}".format(info, want, climb))
        if info is None:
            continue
        (e, n, got) = info
        if got != tuple(climb):
            build.on_main(build.undo)
            time.sleep(1.5)
            turn = True
            continue
        err = (e - want[0], n - want[1])
        if abs(err[0]) < 0.3 and abs(err[1]) < 0.3:
            return True
        build.on_main(build.undo)
        time.sleep(1.5)
        shift = [shift[0] - err[0], shift[1] - err[1]]
    return "failed"


def door_count():
    return sum(1 for t in build._wall_things() if t[2] == "door")


def place_door_worker(tile_a, tile_b, level=0):
    """Worker thread, door already chosen. Click the wall between two neighboring tiles.
    Returns True when a door was added."""
    side = side_between(tile_a, tile_b)
    (x, z) = build.wall_cell_point(side, tile_a)
    if not build.set_floor(level):
        return False
    before = build.on_main(door_count) or 0

    def act(s):
        build._reselect()
        build.click(s[0])
    if not build.point_and_act([(x, z)], level, act, "door {} {}".format(tile_a, side), height=0.15,
                               view=build.VIEW_FROM[side]):
        return False
    time.sleep(0.8)
    return (build.on_main(door_count) or 0) > before


def start_build(p):
    if build._busy[0]:
        core.speak("Still working on the last build step.")
        return
    build._busy[0] = True
    core.speak("Building your house. This takes a few minutes. Please do not press any keys until you hear that it is finished.")

    def work():
        try:
            _build(p)
        except Exception:
            core.log_exc("build house")
            core.post(core.speak, "Sorry, building the house failed. Send the TS4_Access_Plus.log file from the Mods folder for help.")
        finally:
            build._busy[0] = False
    threading.Thread(target=work, name="tyjokr_a11y_plus_house", daemon=True).start()


def _say(text):
    core.post(core.speak, text)


def _build(p):
    import tyjokr_a11y_plus_rooms as rooms
    start_money = build.on_main(build.funds) or 0
    if not _pick_tool("Room Tool"):
        _say("I could not choose the Room Tool in the catalog.")
        return
    built = []
    for r in p.rooms:
        _say("Building the {}.".format(r["name"].lower()))
        box = build.room_worker(r["box"], overview=True, level=r.get("level", 0))
        core.log("house: {} level {} wanted {} got {}".format(r["name"], r.get("level", 0), r["box"], box))
        if box != r["box"]:
            what = {"nomoney": "there is not enough money or something is in the way",
                    "open": "the walls did not close", "noscreen": "I could not get it on screen",
                    "nofloor": "I could not switch the game to the right floor"}.get(
                box, "it came out a different size. Something may already be built there, so start on an empty lot")
            _say("I stopped building at the {}, because {}. {} rooms were built. "
                 "You can take back each step with Undo in the build helper.".format(r["name"].lower(), what, len(built)))
            _name_rooms(p, rooms)
            return
        built.append(r)
    _name_rooms(p, rooms)
    stairs_ok = True
    if p.stairs:
        _say("Putting in the stairs.")
        res = place_stairs_worker(p.stairs["top_lot"], p.stairs["climb_lot"])
        core.log("house: stairs {}".format(res))
        stairs_ok = res is True
    # Doors: the front door first, then the inside doors.
    missed = []
    current = None
    for d in p.doors:
        wanted = FRONT_DOORS if d["front"] else INTERIOR_DOORS
        if current != wanted:
            name = _pick_door(wanted)
            if not name:
                _say("I could not choose a door in the catalog.")
                return
            current = wanted
        _say(d["what"] + ".")
        level = d.get("level", 0)
        ok = place_door_worker(d["tile_a"], d["tile_b"], level)
        if not ok:
            ok = place_door_worker(d["tile_a"], d["tile_b"], level)      # once more, the game sometimes drops the tool
        if not ok:
            missed.append(d["what"].lower())
        core.log("house: {} {}".format(d["what"], "ok" if ok else "MISSED"))
    build.set_floor(0)
    spent = start_money - (build.on_main(build.funds) or 0)
    left = build.on_main(build.funds) or 0
    text = "Your house is finished. It cost {:,} simoleons, and you have {:,} left. ".format(spent, left)
    if p.stairs:
        text += ("The stairs are in the hallway. " if stairs_ok else
                 "But I could not put in the stairs, so nobody can get upstairs yet. Send the TS4_Access_Plus.log file from the Mods folder for help. ")
        text += "The game now shows the ground floor. Page Up and Page Down change floors. "
    if missed:
        text += "These doors could not be placed: {}. Use Door between two rooms in the build helper to try again. ".format(
            "; ".join(missed))
    text += "Alt+R lists the rooms by name. Next, furnish them: Alt+B, Furnish a room with the basics."
    _say(text)


def _name_rooms(p, rooms):
    def go():
        for room in rooms.scan_rooms():
            box = build._room_box(room)
            for r in p.rooms:
                if r["box"] == box and room.level == r.get("level", 0):
                    rooms.set_room_name(room, r["name"])
    build.on_main(go)

# ---------------------------------------------------------------- door tools


def _neighbors(room, all_rooms):
    """Rooms that share a wall with `room`, with the wall tiles: list of (other or None, [(tile_a, tile_b)])."""
    mine = build._room_tiles(room)
    by_tile = {}
    for other in all_rooms:
        if other is room or other.level != room.level:
            continue
        for t in build._room_tiles(other):
            by_tile[t] = other
    found = {}
    outside = []
    for t in mine:
        for (de, dn) in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nb = (t[0] + de, t[1] + dn)
            if nb in mine:
                continue
            other = by_tile.get(nb)
            if other is None:
                outside.append((t, nb))
            else:
                found.setdefault(id(other), (other, []))[1].append((t, nb))
    out = list(found.values())
    return out, outside


def _middle(pairs):
    """The wall piece in the middle of a run of wall pieces."""
    pairs = sorted(pairs, key=lambda ab: (ab[0][0], ab[0][1]))
    return pairs[len(pairs) // 2]


def door_between_rooms():
    if not build.in_build_mode():
        core.speak("Go to Build mode first. Press F2, on a laptop Fn+F2.")
        return
    import tyjokr_a11y_plus_rooms as rooms
    all_rooms = [r for r in rooms.scan_rooms()]
    if not all_rooms:
        core.speak("There are no rooms yet.")
        return
    rows = [(r.name, "{}, {}".format(r.size_text(), rooms.floor_name(r.level)), r) for r in all_rooms]

    def got_room(room):
        nbs, outside = _neighbors(room, all_rooms)
        orows = []
        for (other, pairs) in nbs:
            if len(pairs) < 1:
                continue
            orows.append(("{}".format(other.name), "They share {} meters of wall.".format(len(pairs)), ("room", other, pairs)))
        by_side = {}
        for (a, b) in outside:
            by_side.setdefault(side_between(a, b), []).append((a, b))
        street = street_side()
        for (side, pairs) in sorted(by_side.items()):
            label = "Outside, the {} wall{}".format(side, ", facing the street" if side == street else "")
            orows.append((label, "A door to the yard. {} meters of wall.".format(len(pairs)), ("out", side, pairs)))

        def got_other(value):
            (_kind, other, pairs) = value
            (a, b) = _middle(pairs)
            what = "a door between the {} and the {}".format(room.name, other.name if _kind == "room" else "yard")
            _run_door(a, b, room.level, what)
        core.choose("Door from the {} to".format(room.name), "Choose where the door leads. It goes in the middle of the shared wall.",
                    orows, got_other, tag="build")
    core.choose("Door between two rooms", "Choose the first room.", rows, got_room, tag="build")


def _run_door(a, b, level, what):
    if build._busy[0]:
        core.speak("Still working on the last build step.")
        return
    build._busy[0] = True
    use_chosen = build._cat.get("next") == "wall" and build._cat.get("chosen") is not None and "door" in build.tool_name().lower()
    core.speak("Putting {}. Please wait.".format(what))

    def work():
        try:
            if not use_chosen and not _pick_door(INTERIOR_DOORS):
                _say("I could not choose a door in the catalog.")
                return
            money = build.on_main(build.funds) or 0
            ok = place_door_worker(a, b, level)
            spent = money - (build.on_main(build.funds) or 0)
            if ok:
                _say("Done, {} is in place. It cost {:,} simoleons.".format(what, spent))
            else:
                reason = build._last_error["text"]
                _say("The door was not placed. {}".format("The game says: " + reason if reason else
                                                         "Furniture or another door may be in the way."))
        except Exception:
            core.log_exc("door job")
            _say("Sorry, placing the door failed.")
        finally:
            build._busy[0] = False
    threading.Thread(target=work, name="a11yplus_door", daemon=True).start()


def _thing_rows():
    """Doors and windows with where they are: list of (label, (x, z, level, side, kind))."""
    import services
    import tyjokr_a11y_plus_rooms as rooms
    f = build.frame()
    named = {}
    for r in rooms.scan_rooms():
        for t in build._room_tiles(r):
            named[(t[0], t[1], r.level)] = r.name
    out = []
    for obj in services.object_manager().values():
        try:
            names = rooms.tag_names(obj)
            kind = "Door" if ("Build_Door" in names or "Build_Arch" in names) else ("Window" if "Build_Window" in names else None)
            if not kind:
                continue
            level = int(obj.level)
            (e, n) = f.local(obj.position.x, obj.position.z)
            # A door sits on a wall line: one of e, n is a whole number. The rooms on either side tell where it is.
            if abs(e - round(e)) < abs(n - round(n)):
                a, b = (int(round(e)) - 1, int(math.floor(n))), (int(round(e)), int(math.floor(n)))
            else:
                a, b = (int(math.floor(e)), int(round(n)) - 1), (int(math.floor(e)), int(round(n)))
            ra, rb = named.get((a[0], a[1], level), "outside"), named.get((b[0], b[1], level), "outside")
            if ra == "outside":
                (ra, rb, a, b) = (rb, ra, b, a)
            where = "between the {} and the {}".format(ra, rb) if rb != "outside" else "from the {} to outside, {} wall".format(
                ra, side_between(a, b))
            label = "{} {}".format(kind, where)
            out.append((label, (obj.position.x, obj.position.z, level, side_between(a, b), kind, getattr(obj, "id", 0))))
        except Exception:
            core.log_exc("door row")
    out.sort()
    return out


def remove_door_or_window():
    if not build.in_build_mode():
        core.speak("Go to Build mode first. Press F2, on a laptop Fn+F2.")
        return
    rows = [(label, None, value) for (label, value) in _thing_rows()]
    if not rows:
        core.speak("There are no doors or windows.")
        return

    def got(value):
        (x, z, level, side, kind, oid) = value
        if build._busy[0]:
            core.speak("Still working on the last build step.")
            return
        build._busy[0] = True
        core.speak("Removing the {}. Please wait.".format(kind.lower()))

        def work():
            import services
            try:
                money = build.on_main(build.funds) or 0
                u = build._user32()
                # The game's Sledgehammer is the K key in Build mode.
                u.keybd_event(0x4B, 0x25, 0, 0)
                time.sleep(0.05)
                u.keybd_event(0x4B, 0x25, 2, 0)
                time.sleep(0.5)
                build.point_and_act([(x, z)], level, lambda s: build.click(s[0]), "remove " + kind, height=1.0,
                                    view=build.VIEW_FROM.get(side))
                time.sleep(0.8)
                gone = build.on_main(lambda: services.object_manager().get(oid) is None)
                back = (build.on_main(build.funds) or 0) - money
                # Put the Sledgehammer away again.
                u.keybd_event(0x1B, 0x01, 0, 0)
                time.sleep(0.05)
                u.keybd_event(0x1B, 0x01, 2, 0)
                if gone:
                    _say("Removed the {}. You got {:,} simoleons back.".format(kind.lower(), max(0, back)))
                else:
                    _say("The {} is still there. Send the TS4_Access_Plus.log file from the Mods folder for help.".format(kind.lower()))
            except Exception:
                core.log_exc("remove door")
                _say("Sorry, removing failed.")
            finally:
                build._busy[0] = False
        threading.Thread(target=work, name="a11yplus_remove", daemon=True).start()
    core.choose("Remove a door or window", "Choose which one.", rows, got, tag="build")

# ---------------------------------------------------------------- naming a room


def name_a_room():
    import tyjokr_a11y_plus_rooms as rooms
    all_rooms = rooms.scan_rooms()
    if not all_rooms:
        core.speak("There are no rooms yet.")
        return
    rows = [(r.name, "{}, {}".format(r.size_text(), rooms.floor_name(r.level)), r) for r in all_rooms]

    def got(room):
        def named(text):
            rooms.set_room_name(room, text.strip())
            core.speak("The room is now called {}.".format(text.strip()) if text.strip() else "Name removed.")
        core.ask_text("Room name", "Type a name, for example Kitchen or Shay's bedroom.", room.name, named)
    core.choose("Name a room", "Choose the room to name.", rows, got, tag="build")
