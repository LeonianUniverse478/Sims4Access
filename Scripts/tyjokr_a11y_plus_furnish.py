# TS4 Access Plus - furnish a room with the basics (in the build helper, Alt+B).
# The player says what kind of room it is; we buy the cheapest good item of each kind it needs
# (picked by name from the Buy catalog) and let TS4 Access place each one, starting in the middle
# of the room and then along the walls, away from doors.
import math, threading, time
import tyjokr_a11y_plus_core as core
import tyjokr_a11y_plus_build as build

# key -> (label, catalog tags, names to prefer in order, words that rule an item out)
ITEMS = {
    "double bed": ("Double bed", "BUYCAT_SS_BED", ("Killer Queen Double Bed", "Soothing Sleeper Double Bed"), ("single", "bunk", "crib", "toddler")),
    "single bed": ("Single bed", "BUYCAT_SS_BED", ("Teen Dreams Single", "Burst of Pride Single Bed"), ("double", "bunk", "crib", "toddler")),
    "toddler bed": ("Toddler bed", "BUYCAT_SS_BED", ("BlandCo Contemporary Toddler Bed", "Classic Toddler Bed"), ("crib", "bassinet")),
    "toilet": ("Toilet", "BUYCAT_PA_TOILET", ("The Ambassador", "Modern Relief"), ("potty",)),
    "shower": ("Shower", "BUYCAT_PA_SHOWER", ("Post Modern Shower Stall",), ("tub",)),
    "bath sink": ("Sink", "BUYCAT_PA_SINK", ("Brut Pedestal Sink", "RAW Pedestal Sink"), ("kitchen", "counter")),
    "fridge": ("Refrigerator", "BUYCAT_PA_REFRIGERATOR", ("Crisponix Budget Dee-Lux", "Crisponix Adequate"), ("mini",)),
    "stove": ("Stove", "BUYCAT_PA_STOVE", ("The YumCooker",), ("griddle",)),
    "counter": ("Counter", "BUYCAT_SS_COUNTER", ("BlandCo Contemporary Counter",), ("island",)),
    "trash": ("Trash can", "BUYCAT_PA_DISPOSABLE,BUYCAT_PA_DISPOSAL_INDOOR", ("Garbelle Wastebasket",), ("children", "baby", "outdoor")),
    "sofa": ("Sofa", "BUYCAT_SS_SOFA", ("Mega Sofa", "Squarely There Modern Sofa"), ()),
    "tv": ("Television", "BUYCAT_EE_TV", ("Been There, Watched That TV", "Trusty Companion TV"), ("stand", "children")),
    # Ceiling lights cannot be placed from the keyboard yet (TS4 Access), so a floor lamp.
    "light": ("Floor lamp", "BUYCAT_LD_FLOORLAMP", (), ("kid",)),
}
SETS = (
    ("Bedroom for a couple", ["double bed", "light"]),
    ("Bedroom for one grown-up or teen", ["single bed", "light"]),
    ("Child's bedroom", ["single bed", "light"]),
    ("Toddler's bedroom", ["toddler bed", "light"]),
    ("Bathroom", ["toilet", "shower", "bath sink", "light"]),
    ("Kitchen", ["fridge", "stove", "counter", "counter", "trash", "light"]),
    ("Living room", ["sofa", "tv", "light"]),
    ("Hallway or other room", ["light"]),
)
# What each set costs with the preferred items (October 2026 prices), to show before buying.
PRICES = {"double bed": 725, "single bed": 330, "toddler bed": 150, "toilet": 250, "shower": 375, "bath sink": 145,
          "fridge": 375, "stove": 400, "counter": 150, "trash": 50, "sofa": 235, "tv": 500, "light": 60}


def _guess_set(room_name):
    n = room_name.lower()
    for (word, i) in (("bedroom", 0), ("bathroom", 4), ("kitchen", 5), ("living", 6), ("hall", 7)):
        if word in n:
            return i
    return None


def furnish_room():
    if not build.in_build_mode():
        core.speak("Go to Build mode first. Press F2, on a laptop Fn+F2.")
        return
    import tyjokr_a11y_plus_rooms as rooms
    all_rooms = rooms.scan_rooms()
    if not all_rooms:
        core.speak("There are no rooms yet.")
        return
    rows = [(r.name, "{}, {} things in it now.".format(r.size_text(), len(r.objects)), r) for r in all_rooms]

    def got_room(room):
        guess = _guess_set(room.name)
        srows = []
        for (i, (label, keys)) in enumerate(SETS):
            things = ", ".join(ITEMS[k][0].lower() for k in keys)
            cost = sum(PRICES.get(k, 0) for k in keys)
            srows.append((label, "Buys: {}. About {:,} simoleons.".format(things, cost), i))
        if guess is not None:
            srows.insert(0, srows.pop(guess))

        def got_set(i):
            _furnish(room, SETS[i])
        core.choose("Furnish the {}".format(room.name),
                    "What kind of room is it? You have {:,} simoleons.".format(build.funds() or 0),
                    srows, got_set, tag="build")
    core.choose("Furnish a room", "Choose the room.", rows, got_room, tag="build")


def _choose_item(key):
    """Worker: select the catalog item for `key`. Returns (name, price) or None."""
    (label, tags, prefer, exclude) = ITEMS[key]
    items = build.fetch_catalog(2, tags, "object")
    if not items:
        return None
    names = [it[0] for it in items]
    index = None
    for want in prefer:
        if want in names:
            index = names.index(want)
            break
    if index is None:
        ok = [(it[1], i) for (i, it) in enumerate(items) if not any(w in it[0].lower() for w in exclude)]
        if not ok:
            return None
        index = min(ok)[1]
    build._cat["silent_select"] = True
    try:
        build.select_item(index, names[index])
    finally:
        build._cat["silent_select"] = False
    return (names[index], items[index][1])


def _spots(room):
    """Places to put things: (x, z, angle) in the corners and along the walls, away from doors, each
    turned to face into the room; the middle of the room comes last (beds go there first)."""
    f = build.frame()
    tiles = sorted(build._room_tiles(room))
    (e0, n0, e1, n1) = build._room_box(room)
    door_tiles = set()
    for (te, tn, kind) in build._wall_things():
        if kind == "door":
            for de in (-0.5, 0.5):
                for dn in (-0.5, 0.5):
                    door_tiles.add((int(math.floor(te + de)), int(math.floor(tn + dn))))
    out = []
    for t in tiles:
        if t in door_tiles:
            continue
        faces = []
        if t[1] == n0:
            faces.append((0, 1))        # against the north wall: face south
        if t[1] == n1 - 1:
            faces.append((0, -1))
        if t[0] == e0:
            faces.append((1, 0))
        if t[0] == e1 - 1:
            faces.append((-1, 0))
        if not faces:
            continue
        (de, dn) = faces[0]
        (x, z) = f.world(t[0] + 0.5, t[1] + 0.5)
        # Object forward at angle 0 is north (world +z). World direction of (de, dn) is (de, -dn).
        out.append((len(faces) == 2, x, z, math.atan2(de, -dn)))
    out.sort(key=lambda s: not s[0])          # corners first
    spots = [(x, z, a) for (_c, x, z, a) in out]
    (cx, cz) = f.world((e0 + e1) / 2.0, (n0 + n1) / 2.0)
    return spots, (cx, cz, 0.0)


def _face_into_room(place, room):
    """The game may turn an object while finding room for it. If its front now faces a wall,
    turn it to face into the room."""
    import services, sims4.math
    try:
        obj = services.object_manager().get(place._last.get("obj_id"))
        if obj is None:
            return
        f = build.frame()
        tiles = build._room_tiles(room)
        fw = obj.orientation.transform_vector(sims4.math.Vector3.Z_AXIS())
        (e, n) = f.local(obj.position.x, obj.position.z)
        (fe, fn) = (fw.x, -fw.z)
        front = (int(math.floor(e + fe * 0.9)), int(math.floor(n + fn * 0.9)))
        if front in tiles:
            return
        (e0, n0, e1, n1) = build._room_box(room)
        (de, dn) = ((e0 + e1) / 2.0 - e, (n0 + n1) / 2.0 - n)
        (de, dn) = ((1 if de > 0 else -1), 0) if abs(de) > abs(dn) else (0, (1 if dn > 0 else -1))
        q = sims4.math.angle_to_yaw_quaternion(math.atan2(de, -dn))
        obj.move_to(translation=obj.position, orientation=q, routing_surface=obj.routing_surface)
        core.log("furnish: turned {} to face into the room".format(obj.id))
    except Exception:
        core.log_exc("face into room")


def _say(text):
    core.post(core.speak, text)


def _furnish(room, item_set):
    (label, keys) = item_set
    if build._busy[0]:
        core.speak("Still working on the last build step.")
        return
    build._busy[0] = True
    core.speak("Furnishing the {} as a {}. Please wait.".format(room.name, label.lower()))

    def work():
        import routing, services, terrain, sims4.math
        import tyjokr_a11y_place as place
        bought, missed = [], []
        start = build.on_main(build.funds) or 0
        try:
            (spots, middle) = _spots(room)
            spot_i = 0
            for key in keys:
                chosen = _choose_item(key)
                if chosen is None:
                    missed.append(ITEMS[key][0].lower())
                    continue
                ok = False
                for attempt in range(4):
                    if key.endswith("bed") and attempt == 0:
                        (x, z, angle) = middle
                    else:
                        (x, z, angle) = spots[spot_i % len(spots)] if spots else middle
                        spot_i += 1
                    before = build.on_main(build.funds) or 0

                    def go():
                        surface = routing.SurfaceIdentifier(services.current_zone_id(), room.level, routing.SurfaceType.SURFACETYPE_WORLD)
                        pos = sims4.math.Vector3(x, terrain.get_terrain_height(x, z, routing_surface=surface), z)
                        return place.place(pos, room.level, surface, angle)
                    build.on_main(go)
                    for _ in range(20):
                        time.sleep(0.25)
                        if (build.on_main(build.funds) or 0) < before:
                            ok = True
                            break
                    if ok:
                        break
                    time.sleep(0.5)
                if ok:
                    build.on_main(_face_into_room, place, room)
                (bought if ok else missed).append(ITEMS[key][0].lower())
                core.log("furnish {} {}: {}".format(room.name, key, "ok" if ok else "missed"))
            spent = start - (build.on_main(build.funds) or 0)
            text = "Done furnishing the {}. Bought: {}. It cost {:,} simoleons.".format(
                room.name, ", ".join(bought) if bought else "nothing", spent)
            if missed:
                text += " Could not place: {}. The room may be too full.".format(", ".join(missed))
            _say(text)
        except Exception:
            core.log_exc("furnish")
            _say("Sorry, furnishing failed.")
        finally:
            build._busy[0] = False
    threading.Thread(target=work, name="tyjokr_a11y_plus_furnish", daemon=True).start()
