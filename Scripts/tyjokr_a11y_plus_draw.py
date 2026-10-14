# TS4 Access Plus - drawing cursor: build walls, rooms, roofs and fences the way sighted players do,
# by pointing at a start corner and an end corner on the lot grid. The player moves a cursor with
# Alt+arrows and hears where it is; Alt+S marks the start, Alt+D draws with the chosen tool.
# The drawing itself is the game's own tool driven by a real mouse drag (see tyjokr_a11y_plus_build).
import threading, time
import tyjokr_a11y_plus_core as core
import tyjokr_a11y_plus_build as build

TOOLS = {
    "wall": "Wall",
    "room": "Room",
    "roof": "Roof",
    "fence": "Fence",
}

_state = {"on": False, "e": 0, "n": 0, "level": 0, "start": None, "tool": "wall",
          "style": None,         # (product type, tags, name) for roofs and fences
          "grid": None, "names": {}}


def is_on():
    return _state["on"] and build.in_build_mode()

# ---------------------------------------------------------------- what is where


def _refresh_map():
    """Room of every 1 m tile on the cursor's floor: grid[n][e] = room id, 0 for outside."""
    import tyjokr_a11y_plus_rooms as rooms
    f = build.frame()
    real = {}
    for r in rooms.scan_rooms():
        if r.level == _state["level"]:
            real[r.rid] = r.name
    grid = []
    for n in range(f.depth):
        row = []
        for e in range(f.width):
            (x, z) = f.world(e + 0.5, n + 0.5)
            rid = rooms.room_id_at(x, z, _state["level"])
            row.append(rid if rid in real else 0)
        grid.append(row)
    _state["grid"] = grid
    _state["names"] = real


def _tile(e, n):
    g = _state["grid"]
    if g is None or n < 0 or e < 0 or n >= len(g) or e >= len(g[0]):
        return 0
    return g[n][e]


def _wall_dirs(e, n):
    """Which ways a wall runs from grid corner (e, n), judged by rooms on either side."""
    dirs = []
    if _tile(e, n - 1) != _tile(e, n):
        dirs.append("east")             # the line from (e, n) to (e+1, n) lies between tile rows n-1 and n
    if _tile(e - 1, n - 1) != _tile(e - 1, n):
        dirs.append("west")
    if _tile(e - 1, n - 1) != _tile(e, n - 1):
        dirs.append("north")
    if _tile(e - 1, n) != _tile(e, n):
        dirs.append("south")
    return dirs


def _area_text(e, n):
    ids = []
    for t in (_tile(e - 1, n - 1), _tile(e, n - 1), _tile(e - 1, n), _tile(e, n)):
        if t not in ids:
            ids.append(t)
    names = [_state["names"].get(t, "outside") if t else "outside" for t in ids]
    if len(names) == 1:
        return "inside the " + names[0] if names[0] != "outside" else "outside"
    return "between " + ", ".join(names[:-1]) + " and " + names[-1]


def _from_start(e, n):
    s = _state["start"]
    if s is None:
        return ""
    de, dn = e - s[0], n - s[1]
    if de == 0 and dn == 0:
        return "At the start point."
    parts = []
    if de:
        parts.append("{} {}".format(abs(de), "east" if de > 0 else "west"))
    if dn:
        parts.append("{} {}".format(abs(dn), "south" if dn > 0 else "north"))
    return "From the start: " + " and ".join(parts) + "."


def _where(full=False):
    e, n = _state["e"], _state["n"]
    area = _area_text(e, n)
    text = "{} from west, {} from north. {}.".format(e, n, area[:1].upper() + area[1:])
    dirs = _wall_dirs(e, n)
    if dirs:
        text += " On a wall going " + ", ".join(dirs) + "." if full else " On a wall."
    s = _from_start(e, n)
    if s:
        text += " " + s
    if full:
        style = _state["style"] if _state["tool"] in ("roof", "fence") else None
        text += " Tool: {}{}.".format(TOOLS[_state["tool"]], ", " + style[2] if style else "")
    return text

# ---------------------------------------------------------------- turning the cursor on and off


def start():
    if not build.in_build_mode():
        core.speak("Go to Build mode first. Press F2, on a laptop Fn+F2.")
        return
    build._hook_product()
    _refresh_map()
    f = build.frame()
    if not _state["on"]:
        # Start at the north west corner of the house, or the middle of the lot when it is empty.
        g = _state["grid"]
        cells = [(e, n) for n in range(f.depth) for e in range(f.width) if g[n][e]]
        if cells:
            _state["e"] = min(c[0] for c in cells)
            _state["n"] = min(c[1] for c in cells)
        else:
            _state["e"], _state["n"] = f.width // 2, f.depth // 2
        _state["start"] = None
    _state["on"] = True
    core.speak("Drawing cursor on. Alt plus arrows move it 1 meter, add Shift for 5 meters. "
               "Alt+S marks the start point, Alt+D draws from the start to the cursor, Alt+X says where you are, "
               "Alt+Z takes back the last thing drawn. Alt+B to choose the tool or turn the cursor off. "
               + _where(full=True))


def stop():
    _state["on"] = False
    core.speak("Drawing cursor off.")


def choose_tool():
    rows = [
        ("Wall", "Draws a straight wall from the start point to the cursor.", "wall"),
        ("Room", "Draws four walls: the start point and the cursor are opposite corners.", "room"),
        ("Roof", "You choose a roof style. The start point and the cursor are opposite corners of the roof.", "roof"),
        # Fences: the game refused a dragged fence ("Must be applied to a room", October 2026). Not offered yet.
    ]

    def picked(tool):
        if tool in ("wall", "room"):
            _state["tool"], _state["style"] = tool, None
            core.speak("Tool: {}. ".format(TOOLS[tool]) + _hint())
            return
        _pick_style(tool)
    core.choose("Drawing tool", "Now: {}.".format(TOOLS[_state["tool"]]), rows, picked, tag="build")



def _hint():
    if _state["start"] is None:
        return "Move to the first corner and press Alt+S."
    return "Move to the end and press Alt+D."


def _pick_style(tool):
    (ptype, tags) = (4, "") if tool == "roof" else (10, "")

    def work():
        items = build.fetch_catalog(ptype, tags, "none")
        if not items:
            core.post(core.speak, "I could not get the list of {}s.".format(tool))
            return
        rows = []
        for (name, price, colors) in items:
            desc = "{:,} simoleons{}".format(price, " a meter" if tool == "fence" else "") if price else None
            rows.append((name, desc, name))

        def chosen(name):
            _state["tool"] = tool
            _state["style"] = (ptype, tags, name)
            core.speak("Tool: {}, {}. ".format(TOOLS[tool], name) + _hint())
        core.post(core.choose, "Choose a " + tool, "{} to choose from.".format(len(rows)), rows, chosen, "build")
    threading.Thread(target=work, name="a11yplus_style", daemon=True).start()

# ---------------------------------------------------------------- keys (only while the cursor is on)


def _move(de, dn, shift=False):
    if not is_on():
        return
    step = 5 if shift else 1
    f = build.frame()
    e = max(0, min(f.width, _state["e"] + de * step))
    n = max(0, min(f.depth, _state["n"] + dn * step))
    edge = (e, n) == (_state["e"], _state["n"]) or e in (0, f.width) or n in (0, f.depth)
    _state["e"], _state["n"] = e, n
    core.speak(_where() + (" Edge of the lot." if edge else ""))


@core.hotkey(0x25, "drawing cursor west")
def _west(shift=False):
    _move(-1, 0, shift)


@core.hotkey(0x27, "drawing cursor east")
def _east(shift=False):
    _move(1, 0, shift)


@core.hotkey(0x26, "drawing cursor north")
def _north(shift=False):
    _move(0, -1, shift)


@core.hotkey(0x28, "drawing cursor south")
def _south(shift=False):
    _move(0, 1, shift)


for _fn in (_west, _east, _north, _south):
    _fn._wants_shift = True


@core.hotkey(ord("X"), "drawing cursor: where am I")
def _say_where():
    if is_on():
        core.speak(_where(full=True))


@core.hotkey(ord("S"), "drawing cursor: mark start")
def _mark_start():
    if not is_on():
        return
    _state["start"] = (_state["e"], _state["n"])
    core.speak("Start point at {} from west, {} from north. Move to the end and press Alt+D.".format(*_state["start"]))


@core.hotkey(ord("Z"), "drawing cursor: undo")
def _undo():
    if is_on():
        build.undo()
        core.speak("Undone.")
        core.post(_refresh_map)


@core.hotkey(ord("D"), "drawing cursor: draw")
def _draw():
    if not is_on():
        return
    s = _state["start"]
    if s is None:
        core.speak("First mark a start point with Alt+S.")
        return
    e, n = _state["e"], _state["n"]
    tool = _state["tool"]
    if (e, n) == tuple(s):
        core.speak("The cursor is on the start point. Move it to the end first.")
        return
    if tool in ("wall", "fence") and e != s[0] and n != s[1]:
        core.speak("A {} goes straight. Move the cursor straight east, west, north or south of the start.".format(tool))
        return
    if tool in ("room", "roof") and (e == s[0] or n == s[1]):
        core.speak("A {} needs two opposite corners. Move the cursor so it is both across and down from the start.".format(tool))
        return
    if tool in ("roof", "fence") and not _state["style"]:
        _pick_style(tool)
        return
    if build._busy[0]:
        core.speak("Still working on the last build step.")
        return
    build._busy[0] = True
    core.speak("Drawing. Please wait, and let go of Alt.")
    threading.Thread(target=_draw_worker, args=(tool, tuple(s), (e, n)), name="tyjokr_a11y_plus_draw", daemon=True).start()


def _wait_keys_up():
    """Holding Alt during a drag makes the game place things off the grid; wait until it is let go."""
    import ctypes
    read = ctypes.windll.user32.GetAsyncKeyState
    end = time.monotonic() + 4.0
    while time.monotonic() < end and (read(0x12) & 0x8000 or read(0x10) & 0x8000):
        time.sleep(0.05)
    time.sleep(0.3)


def _say(text):
    core.post(core.speak, text)


def _select_style(ptype, tags, name):
    items = build.fetch_catalog(ptype, tags, "none")
    names = [it[0] for it in items]
    if name not in names:
        return False
    build._cat["silent_select"] = True
    try:
        build.select_item(names.index(name), name)
    finally:
        build._cat["silent_select"] = False
    return True


def _draw_worker(tool, a, b):
    import tyjokr_a11y_plus_house as house
    try:
        _wait_keys_up()
        f = build.frame()
        level = _state["level"]
        if tool == "roof":
            if not _select_style(*_state["style"]):
                _say("I could not choose the {} in the catalog.".format(_state["style"][2]))
                return
            box = (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
            res = roof_worker(box, level)
            core.log("draw: roof {} result {}".format(box, res))
            _say(_roof_result(res, box))
        elif tool == "room":
            if not house._pick_tool("Room Tool"):
                _say("I could not choose the Room Tool.")
                return
            want = (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
            box = build.room_worker(want)
            if box in (None, "nomoney"):
                _say("The room was not built. Something may be in the way, or there is not enough money.")
            elif box == "noscreen":
                pass
            elif box == "open":
                _say("The walls were built, but they did not make a closed room.")
            else:
                _say("Built a {} by {} meter room.".format(box[2] - box[0], box[3] - box[1]))
        else:
            if tool == "wall":
                if not house._pick_tool("Wall Tool"):
                    u = build._user32()             # the game's own key for the Wall Tool
                    u.keybd_event(0x42, 0x30, 0, 0)
                    u.keybd_event(0x42, 0x30, 2, 0)
                    time.sleep(0.8)
            elif not _select_style(*_state["style"]):
                _say("I could not choose the {} in the catalog.".format(_state["style"][2]))
                return
            money = build.on_main(build.funds) or 0
            started = time.monotonic()
            ok = build.point_and_act([f.world(*a), f.world(*b)], level, lambda s: build.drag(s[0], s[1]),
                                     "{} {}->{}".format(tool, a, b), overview=True)
            time.sleep(0.8)
            spent = money - (build.on_main(build.funds) or 0)
            core.log("draw: {} {}->{} ok={} spent={}".format(tool, a, b, ok, spent))
            what = {"wall": "wall", "fence": "fence", "roof": "roof"}[tool]
            if ok and spent > 0:
                _say("Built the {}. It cost {:,} simoleons.".format(what, spent))
            elif ok:
                reason = build._last_error["text"] if build._last_error["at"] > started else ""
                _say("The {} was not built. {}".format(what, ("The game says: " + reason) if reason else
                                                       "Something may be in the way, or there is not enough money."))
        build.on_main(_refresh_map)
        _state["start"] = (_state["e"], _state["n"])   # the next piece starts where this one ended
    except Exception:
        core.log_exc("draw job")
        _say("Sorry, drawing failed.")
    finally:
        build._busy[0] = False

# ---------------------------------------------------------------- roof over the whole house


def roof_whole_house():
    """Choose a roof style, then put one roof over every ground floor room (their outer corners)."""
    if not build.in_build_mode():
        core.speak("Go to Build mode first. Press F2, on a laptop Fn+F2.")
        return
    import tyjokr_a11y_plus_rooms as rooms
    all_rooms = [r for r in rooms.scan_rooms() if r.level >= 0]
    if not all_rooms:
        core.speak("There are no rooms to put a roof on yet.")
        return
    # The roof goes on the top floor.
    level = max(r.level for r in all_rooms)
    boxes = [build._room_box(r) for r in all_rooms if r.level == level]
    box = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))

    def work():
        items = build.fetch_catalog(4, "", "none")
        if not items:
            _say("I could not get the list of roofs.")
            return
        rows = [(name, None, name) for (name, price, colors) in items]

        def chosen(name):
            if build._busy[0]:
                core.speak("Still working on the last build step.")
                return
            build._busy[0] = True
            _state["style"] = (4, "", name)
            core.speak("Putting a {} over the house, {} by {} meters. Please wait.".format(
                name, box[2] - box[0], box[3] - box[1]))
            saved = _state["tool"]
            _state["tool"] = "roof"

            def go():
                try:
                    _draw_roof_box(box, level)
                finally:
                    _state["tool"] = saved
            threading.Thread(target=go, name="a11yplus_roof", daemon=True).start()
        core.post(core.choose, "Roof style", "Choose the roof for the whole house.", rows, chosen, "build")
    threading.Thread(target=work, name="a11yplus_roofs", daemon=True).start()


def _draw_roof_box(box, level=0):
    try:
        _wait_keys_up()
        if not _select_style(*_state["style"]):
            _say("I could not choose that roof in the catalog.")
            return
        res = roof_worker(box, level)
        core.log("roof: box {} result {}".format(box, res))
        _say(_roof_result(res, box))
    except Exception:
        core.log_exc("roof job")
        _say("Sorry, the roof failed.")
    finally:
        build._busy[0] = False


# ---------------------------------------------------------------- roofs
# The game's Roof tool does not draw by dragging (a drag pans the camera). A click puts down a
# 3 by 3 meter roof centred on the clicked tile, sitting on the walls, and selects it. Its arrow
# handles then stretch each side: they sit about 1.3 m outside the middle of each edge, 3.5 m above the
# floor (measured October 2026). The handles are small, so before each drag we look at the screen
# for the white (or light blue) arrow near where it should be and grab it there.

HANDLE_OUT = 1.3
HANDLE_UP = 3.5
WALL_TOP = 3.0


def _grab_screen(x0, y0, w, h):
    """Screen pixels of a rectangle as bytes, 4 per pixel (blue, green, red, unused)."""
    import ctypes
    u, g = ctypes.windll.user32, ctypes.windll.gdi32

    class BMI(ctypes.Structure):
        _fields_ = [("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32), ("biHeight", ctypes.c_int32),
                    ("biPlanes", ctypes.c_uint16), ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
                    ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_int32), ("biYPelsPerMeter", ctypes.c_int32),
                    ("biClrUsed", ctypes.c_uint32), ("biClrImportant", ctypes.c_uint32), ("pad", ctypes.c_uint32 * 4)]
    u.GetDC.restype = ctypes.c_void_p
    u.GetDC.argtypes = [ctypes.c_void_p]
    u.ReleaseDC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    g.CreateCompatibleDC.restype = ctypes.c_void_p
    g.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
    g.DeleteDC.argtypes = [ctypes.c_void_p]
    g.CreateCompatibleBitmap.restype = ctypes.c_void_p
    g.CreateCompatibleBitmap.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
    g.SelectObject.restype = ctypes.c_void_p
    g.SelectObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    g.DeleteObject.argtypes = [ctypes.c_void_p]
    g.BitBlt.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                         ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_uint32]
    g.GetDIBits.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p,
                            ctypes.c_void_p, ctypes.c_uint]
    src = u.GetDC(None)
    mem = g.CreateCompatibleDC(src)
    bmp = g.CreateCompatibleBitmap(src, w, h)
    old = g.SelectObject(mem, bmp)
    g.BitBlt(mem, 0, 0, w, h, src, x0, y0, 0x00CC0020)
    bmi = BMI()
    bmi.biSize = 40
    bmi.biWidth, bmi.biHeight, bmi.biPlanes, bmi.biBitCount = w, -h, 1, 32
    buf = ctypes.create_string_buffer(w * h * 4)
    g.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bmi), 0)
    g.SelectObject(mem, old)
    g.DeleteObject(bmp)
    g.DeleteDC(mem)
    u.ReleaseDC(None, src)
    return buf.raw


def _find_handle(sx, sy, radius=40):
    """Screen point of the white handle nearest to (sx, sy), or None."""
    x0, y0 = int(sx - radius), int(sy - radius)
    w = h = 2 * radius
    data = _grab_screen(x0, y0, w, h)
    white = []
    for y in range(h):
        row = y * w * 4
        for x in range(w):
            i = row + x * 4
            if data[i] > 215 and data[i + 1] > 200:          # white or light blue (blue, green)
                white.append((x, y))
    if len(white) < 6:
        return None
    near = min(white, key=lambda p: (p[0] - radius) ** 2 + (p[1] - radius) ** 2)
    blob = [p for p in white if (p[0] - near[0]) ** 2 + (p[1] - near[1]) ** 2 <= 81]
    if len(blob) < 6:
        return None
    return (x0 + sum(p[0] for p in blob) / len(blob), y0 + sum(p[1] for p in blob) / len(blob))


def _drag_screen(a, b):
    (ax, ay), (bx, by) = a, b
    build.move_to(ax, ay)
    time.sleep(0.4)
    build._mouse(build.LEFT_DOWN)
    time.sleep(0.3)
    for i in range(1, 26):
        build.move_to(ax + (bx - ax) * i / 25, ay + (by - ay) * i / 25)
        time.sleep(0.03)
    time.sleep(0.4)
    build._mouse(build.LEFT_UP)
    time.sleep(0.6)


def _handle_point(side, r):
    mid_e, mid_n = (r[0] + r[2]) / 2.0, (r[1] + r[3]) / 2.0
    return {"south": (mid_e, r[3] + HANDLE_OUT), "east": (r[2] + HANDLE_OUT, mid_n),
            "west": (r[0] - HANDLE_OUT, mid_n), "north": (mid_e, r[1] - HANDLE_OUT)}[side]


def _roof_camera(f, box, level=0):
    """Look at the middle of the house from high above its north side, so the whole roof and all four
    handles are on screen, away from the toolbar at the top."""
    import camera, terrain, sims4.math
    # Aimed a little north of the middle: the near (north) handle ends up low on the screen.
    (x, z) = f.world((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0 - 1.5)
    span = max(box[2] - box[0], box[3] - box[1]) + 4
    y = terrain.get_terrain_height(x, z) + WALL_TOP + 3.0 * level
    up = 10.0 + span * 1.25
    camera.focus_on_object_from_position(obj_position=sims4.math.Vector3(x, y, z),
                                         camera_position=sims4.math.Vector3(x, y + up, z + up * 0.55))


def _park():
    """Mouse away from the roof (hovering it shows a tooltip) and from the screen edges (they scroll)."""
    u = build._user32()
    build.move_to(int(u.GetSystemMetrics(0) * 0.9), int(u.GetSystemMetrics(1) * 0.85))


def _screen_of(f, e, n, height, tries=2):
    for _ in range(tries):
        p = build.project(*f.world(e, n), 0, height=height)
        if p:
            return build._to_screen(*p)
    return None


def _screen_toward(f, here, there, height):
    """Screen point of `there`. When it cannot be projected, step from `here` one meter toward it and
    stretch that step to the full distance."""
    p = _screen_of(f, there[0], there[1], height)
    if p:
        return p
    de, dn = there[0] - here[0], there[1] - here[1]
    dist = (de * de + dn * dn) ** 0.5
    if not dist:
        return None
    a = _screen_of(f, here[0], here[1], height)
    b = _screen_of(f, here[0] + de / dist, here[1] + dn / dist, height)
    if not a or not b:
        return None
    return (a[0] + (b[0] - a[0]) * dist, a[1] + (b[1] - a[1]) * dist)


def roof_worker(box, level=0):
    """Worker thread only, roof style already chosen. Put a roof over box (e0, n0, e1, n1), in meters
    from the west and north lot edges, on top of the walls of floor `level`. Returns True or a reason."""
    f = build.frame()
    build._hook_replies()
    # The game puts a roof on the floor it shows, so an upstairs roof is put down from the floor above
    # (from the floor of the rooms themselves the game says roofs can't be placed in enclosed rooms).
    if level > 0 and not build.set_floor(level + 1):
        return "nofloor"
    up = 3.0 * level
    _park()
    build.on_main(_roof_camera, f, box, level)
    time.sleep(2.5)
    cx, cn = (box[0] + box[2]) // 2, (box[1] + box[3]) // 2
    r = [cx - 1, cn - 1, cx + 2, cn + 2]       # where the first 3 by 3 roof lands
    click = _screen_of(f, cx + 0.5, cn + 0.5, WALL_TOP + up)
    build.cursor_off()
    if click is None:
        return "noscreen"
    build.move_to(*click)
    time.sleep(0.4)
    build._mouse(build.LEFT_DOWN)
    time.sleep(0.1)
    build._mouse(build.LEFT_UP)
    time.sleep(1.0)
    _park()
    time.sleep(0.6)
    # The far (south) side first, while the roof is still low and that handle is not hidden behind it.
    for (side, idx, want) in (("south", 3, box[3]), ("east", 2, box[2]), ("west", 0, box[0]), ("north", 1, box[1])):
        if r[idx] == want:
            continue
        goal_r = list(r)
        goal_r[idx] = want
        here, there = _handle_point(side, r), _handle_point(side, goal_r)
        a = _screen_of(f, here[0], here[1], HANDLE_UP + up)
        b = _screen_toward(f, here, there, HANDLE_UP + up)
        build.cursor_off()
        if a is None or b is None:
            return "noscreen"
        found = _find_handle(*a)
        core.log("roof: {} handle expected {} found {}".format(side, a, found))
        if found is None:
            return "nohandle"
        _drag_screen(found, (found[0] + b[0] - a[0], found[1] + b[1] - a[1]))
        _park()
        time.sleep(0.6)
        r = goal_r
    # Check: the east and north handles must now be where the finished roof puts them.
    for side in ("east", "north"):
        e, n = _handle_point(side, r)
        p = _screen_of(f, e, n, HANDLE_UP + up)
        build.cursor_off()
        found = _find_handle(*p, radius=25) if p else None
        core.log("roof: check {} expected {} found {}".format(side, p, found))
        if found is None:
            return "unsure"
    return True


def _roof_result(res, box):
    w, d = box[2] - box[0], box[3] - box[1]
    if res is True:
        return "The roof is on, {} by {} meters.".format(w, d)
    if res == "unsure":
        return "I put the roof down and stretched it, but I could not check its size. Undo it if it sounds wrong."
    if res == "nohandle":
        return "I put a small roof down but could not grab its handles to stretch it. Undo it and try again."
    if res == "nofloor":
        return "I could not switch the game to the right floor. Press Page Up or Page Down and try again."
    return "I could not get that spot on screen."
