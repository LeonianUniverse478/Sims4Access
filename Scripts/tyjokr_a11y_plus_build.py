# TS4 Access Plus - build helper (Alt+B, in Build mode).
# Walls and rooms are drawn by the game's own tools with a real mouse drag between two points.
# TS4 Access projects world points to screen points (its "buildaim" message); we then move the
# real mouse there. The tool (Room Tool, Wall Tool, a door, a paint) is chosen by the player in the
# Build catalog with TS4 Access's keyboard navigation; we only do the pointing.
import math, threading, time, re
import tyjokr_a11y_plus_core as core

# ---------------------------------------------------------------- lot frame
# Positions are given in whole meters from the lot's west edge (x) and north edge (y).


class Frame(object):
    def __init__(self, lot):
        xs = [c.x for c in lot.corners]
        zs = [c.z for c in lot.corners]
        self.x0, self.x1 = min(xs), max(xs)
        self.z0, self.z1 = min(zs), max(zs)
        self.width = int(round(self.x1 - self.x0))      # west to east
        self.depth = int(round(self.z1 - self.z0))      # north to south

    def world(self, e, n):
        """meters from west edge, meters from north edge -> world x, z"""
        return (self.x0 + e, self.z1 - n)

    def local(self, x, z):
        return (x - self.x0, self.z1 - z)


def frame():
    import services
    return Frame(services.active_lot())


def in_build_mode():
    try:
        import services
        return bool(services.current_zone().is_in_build_buy)
    except Exception:
        return False

# ---------------------------------------------------------------- tile map


def tile_map(level=0):
    """grid[n][e] for each 1 m tile: 'room' id (int > 0), 'free', or 'object'."""
    import services, build_buy, terrain, sims4.math
    import tyjokr_a11y_plus_rooms as rooms
    f = frame()
    grid = [[None] * f.width for _ in range(f.depth)]
    for n in range(f.depth):
        for e in range(f.width):
            (x, z) = f.world(e + 0.5, n + 0.5)
            rid = rooms.room_id_at(x, z, level)
            pos = sims4.math.Vector3(x, terrain.get_terrain_height(x, z), z)
            try:
                outside = build_buy.is_location_outside(pos, level)
            except Exception:
                outside = rid == 0
            grid[n][e] = "free" if outside else (rid or "inside")
    for obj in services.object_manager().values():
        try:
            if obj.is_sim or int(obj.level) != level:
                continue
            if not any(t.startswith("BuyCat") for t in rooms.tag_names(obj)):
                continue
            (e, n) = f.local(obj.position.x, obj.position.z)
            (e, n) = (int(e), int(n))
            if 0 <= n < f.depth and 0 <= e < f.width and grid[n][e] == "free":
                grid[n][e] = "object"
        except Exception:
            continue
    return f, grid


def free_spots(grid, w, d, limit=6):
    """Top-left corners (e, n) where a w x d rectangle is completely free, preferring spots
    that touch the house (so the new room joins it) and are near the middle."""
    rows, cols = len(grid), len(grid[0]) if grid else 0
    spots = []
    for n in range(1, rows - d):            # rooms must stay 1 m inside the lot edge
        for e in range(1, cols - w):
            if all(grid[n + j][e + i] == "free" for j in range(d) for i in range(w)):
                touch = 0
                for j in range(-1, d + 1):
                    for i in range(-1, w + 1):
                        if 0 <= n + j < rows and 0 <= e + i < cols and (i in (-1, w) or j in (-1, d)):
                            if grid[n + j][e + i] not in ("free", "object"):
                                touch += 1
                spots.append((-touch, abs(e + w / 2 - cols / 2) + abs(n + d / 2 - rows / 2), e, n))
    spots.sort()
    out = []
    for (_touch, _dist, e, n) in spots:
        if all(abs(e - e2) >= max(2, w // 2) or abs(n - n2) >= max(2, d // 2) for (e2, n2) in out):
            out.append((e, n))
        if len(out) >= limit:
            break
    return out


def _touch_text(grid, e, n, w, d):
    sides = []
    rows, cols = len(grid), len(grid[0])
    def solid(r, c):
        return 0 <= r < rows and 0 <= c < cols and grid[r][c] not in ("free", "object")
    if any(solid(n - 1, e + i) for i in range(w)):
        sides.append("north")
    if any(solid(n + d, e + i) for i in range(w)):
        sides.append("south")
    if any(solid(n + j, e - 1) for j in range(d)):
        sides.append("west")
    if any(solid(n + j, e + w) for j in range(d)):
        sides.append("east")
    if not sides:
        return "stands on its own"
    return "joins the house on its {} side".format(" and ".join(sides))

# ---------------------------------------------------------------- projection (via TS4 Access)

_waiting = {}       # serial -> [event, result]
_hooked = [False]
_SCREEN_RE = re.compile(r"Screen x (-?\d+), y (-?\d+)")


def _hook_replies():
    if _hooked[0]:
        return
    import tyjokr_a11y_build as b
    original = b._say

    def a11yplus_say(en, pl=None):
        try:
            if _waiting:
                m = _SCREEN_RE.search(en or "")
                serial = max(_waiting)
                (ev, res) = _waiting[serial]
                if m and "aimed" in en:
                    res[:] = [int(m.group(1)), int(m.group(2))]
                    ev.set()
                    return
                if "not visible" in (en or "") or "unavailable" in (en or "") or "Close the open" in (en or ""):
                    res[:] = ["fail", en]
                    ev.set()
                    return
                if "Build cursor off" in (en or "") or "Select or place" in (en or ""):
                    return
        except Exception:
            core.log_exc("aim reply")
        return original(en, pl) if pl is not None else original(en)

    b._say = a11yplus_say
    _hooked[0] = True


def _send_ui(msg):
    import distributor.ops, distributor.system
    distributor.system.Distributor.instance().add_op_with_no_owner(distributor.ops.SendUIMessage(msg))


def _new_serial():
    import tyjokr_a11y_build as b, services
    b._serial += 1
    b._pending[b._serial] = services.current_zone_id()
    b._zone_id = services.current_zone_id()
    return b._serial


def floor_height(x, z, level):
    """Height of the floor at a point (includes the house foundation), or ground height outside."""
    import routing, services, terrain
    try:
        surface = routing.SurfaceIdentifier(services.current_zone_id(), int(level), routing.SurfaceType.SURFACETYPE_WORLD)
        return terrain.get_terrain_height(x, z, routing_surface=surface)
    except Exception:
        return terrain.get_terrain_height(x, z) + 3.0 * level


def project(x, z, level, timeout=2.5, height=0.0):
    """Runs in a worker thread. Returns (stage_x, stage_y) or None."""
    import services
    ev = threading.Event()
    res = []
    holder = {}

    def start():
        serial = _new_serial()
        holder["serial"] = serial
        _waiting[serial] = (ev, res)
        y = floor_height(x, z, level) + height
        _send_ui("A11y|buildaim|{}|{:.6f}|{:.6f}|{:.6f}|{}|{}".format(serial, x, y, z, level, services.current_zone_id()))
    core.post(start)
    ok = ev.wait(timeout)
    _waiting.pop(holder.get("serial"), None)
    if not ok or not res or res[0] == "fail":
        core.log("project ({:.1f},{:.1f}) failed: {}".format(x, z, res))
        return None
    return (res[0], res[1])


def cursor_off():
    def go():
        _send_ui("A11y|build|off|{}".format(_new_serial()))
    core.post(go)
    time.sleep(0.4)

# ---------------------------------------------------------------- real mouse


def _user32():
    import ctypes
    return ctypes.windll.user32


# Measured: TS4 Access's projected point sits about 21 interface pixels below where the game's own
# pointer hits the ground (October 2026, 1920x1080 at 125%).
OFFSET = [0.0, 0.0]


def _to_screen(sx, sy):
    """TS4 Access reports interface (stage) coordinates. The interface is scaled by the Windows
    display scale (125% on this laptop), while the mouse uses real pixels."""
    import ctypes

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
    u = _user32()
    hwnd = u.GetForegroundWindow()
    try:
        scale = u.GetDpiForWindow(hwnd) / 96.0 or 1.0
    except Exception:
        scale = 1.0
    pt = POINT(int(round((sx + OFFSET[0]) * scale)), int(round((sy + OFFSET[1]) * scale)))
    u.ClientToScreen(hwnd, ctypes.byref(pt))
    return (pt.x, pt.y)


def _mouse(flags, data=0):
    _user32().mouse_event(flags, 0, 0, data, 0)


LEFT_DOWN, LEFT_UP, WHEEL = 0x0002, 0x0004, 0x0800


def move_to(x, y):
    """Real mouse movement (absolute SendInput), which games see as raw mouse input,
    unlike SetCursorPos. x, y in screen pixels."""
    u = _user32()
    u.SetCursorPos(int(x), int(y))
    w, h = u.GetSystemMetrics(0), u.GetSystemMetrics(1)
    nx = int(round(x * 65535.0 / max(1, w - 1)))
    ny = int(round(y * 65535.0 / max(1, h - 1)))
    u.mouse_event(0x8001, nx, ny, 0, 0)


def drag(a, b, shift=False):
    u = _user32()
    (ax, ay), (bx, by) = _to_screen(*a), _to_screen(*b)
    if shift:
        u.keybd_event(0x10, 0x2A, 0, 0)
    move_to(ax, ay)
    time.sleep(0.3)
    _mouse(LEFT_DOWN)
    time.sleep(0.3)
    steps = 25
    for i in range(1, steps + 1):
        move_to(ax + (bx - ax) * i / steps, ay + (by - ay) * i / steps)
        time.sleep(0.03)
    move_to(bx, by)
    time.sleep(0.4)
    _mouse(LEFT_UP)
    if shift:
        u.keybd_event(0x10, 0x2A, 2, 0)
    time.sleep(0.3)


def click(a, shift=False):
    u = _user32()
    (ax, ay) = _to_screen(*a)
    if shift:
        u.keybd_event(0x10, 0x2A, 0, 0)
        time.sleep(0.05)
    move_to(ax, ay)
    time.sleep(0.3)
    _mouse(LEFT_DOWN)
    time.sleep(0.1)
    _mouse(LEFT_UP)
    if shift:
        time.sleep(0.05)
        u.keybd_event(0x10, 0x2A, 2, 0)
    time.sleep(0.3)


def tap_scan(scan, extended=False):
    """Press and release a key by its scan code with SendInput, the way a keyboard does
    (the game ignores some keys sent with keybd_event)."""
    import ctypes

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort), ("dwFlags", ctypes.c_ulong),
                    ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.c_size_t)]

    class _U(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("pad", ctypes.c_byte * 32)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [("type", ctypes.c_ulong), ("u", _U)]
    for up in (False, True):
        flags = 0x0008 | (0x0001 if extended else 0) | (0x0002 if up else 0)
        inp = INPUT(type=1)
        inp.ki = KEYBDINPUT(0, scan, flags, 0, 0)
        _user32().SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        time.sleep(0.08)


def park_mouse():
    """Move the mouse to the middle of the view (screen edges scroll the camera) so hover effects do not confuse."""
    u = _user32()
    w = u.GetSystemMetrics(0)
    u.SetCursorPos(w // 2, u.GetSystemMetrics(1) // 3)

# ---------------------------------------------------------------- doing a pointing job


_busy = [False]


VIEW_FROM = {"north": (0.0, -1.0), "south": (0.0, 1.0), "east": (-1.0, 0.0), "west": (1.0, 0.0)}


def _focus_camera(x, z, level, view=None):
    """Center the camera on a point. view=(dx, dz): put the camera on that side of the point,
    looking at it, so a wall there is seen from the front and is not cut away."""
    import camera, terrain, sims4.math
    y = terrain.get_terrain_height(x, z) + 3.0 * level
    target = sims4.math.Vector3(x, y, z)
    if view is None:
        camera.focus_on_position(target)
        return
    (dx, dz) = view
    eye = sims4.math.Vector3(x + dx * 7.0, y + 6.0, z + dz * 7.0)
    camera.focus_on_object_from_position(obj_position=target, camera_position=eye)

def _zoom_out(notches=2):
    u = _user32()
    w, h = u.GetSystemMetrics(0), u.GetSystemMetrics(1)
    u.SetCursorPos(w // 2, h // 2)
    for _ in range(notches):
        _mouse(WHEEL, -120)
        time.sleep(0.15)


def overview_camera(points_world, level=0):
    """Look down from high above the street side (north) at a group of points, so a whole house fits
    on screen. Aimed at the near (north) edge: points close to the camera drop off the bottom otherwise."""
    import camera, terrain, sims4.math
    cx = sum(p[0] for p in points_world) / len(points_world)
    zmax = max(p[1] for p in points_world)
    span = max(max(p[0] for p in points_world) - min(p[0] for p in points_world),
               zmax - min(p[1] for p in points_world))
    tz = zmax - 1.0
    y = terrain.get_terrain_height(cx, tz) + 3.0 * level
    up = 14.0 + span * 1.1
    camera.focus_on_object_from_position(obj_position=sims4.math.Vector3(cx, y, tz),
                                         camera_position=sims4.math.Vector3(cx, y + up, tz + up * 0.3))


def point_and_act(points_world, level, action, describe, height=0.0, view=None, overview=False):
    """Worker thread only. Center the camera, project the points, do the mouse action.
    Returns True when the action was performed."""
    _hook_replies()
    cx = sum(p[0] for p in points_world) / len(points_world)
    cz = sum(p[1] for p in points_world) / len(points_world)
    if overview:
        core.post(overview_camera, points_world, level)
    else:
        core.post(_focus_camera, cx, cz, level, view)
    time.sleep(1.8)
    screen = None
    for attempt in range(4):
        pts = []
        for (x, z) in points_world:
            p = project(x, z, level, height=height)
            if p is None:
                break
            pts.append(p)
        if len(pts) == len(points_world) and all(_clear_of_panels(pt) for pt in pts):
            screen = pts
            break
        core.log("build: projection attempt {} failed or under a panel ({}), zooming out".format(attempt + 1, pts))
        cursor_off()
        if overview:
            core.post(overview_camera, points_world + [(cx, cz + 3.0 * (attempt + 1))], level)
        else:
            _zoom_out(3)
            core.post(_focus_camera, cx, cz, level, view)
        time.sleep(1.5)
    cursor_off()
    if screen is None:
        core.post(core.speak, "I could not get that spot on screen. Try a smaller size.")
        return False
    core.log("build: {} at screen {}".format(describe, screen))
    action(screen)
    park_mouse()
    time.sleep(1.0)
    return True


def _stage_size():
    """Width and height of the game window in interface (stage) units."""
    import ctypes

    class RECT(ctypes.Structure):
        _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]
    u = _user32()
    hwnd = u.GetForegroundWindow()
    rc = RECT()
    u.GetClientRect(hwnd, ctypes.byref(rc))
    try:
        scale = u.GetDpiForWindow(hwnd) / 96.0 or 1.0
    except Exception:
        scale = 1.0
    return ((rc.r - rc.l) / scale, (rc.b - rc.t) / scale)


def _clear_of_panels(pt):
    """False when a screen point is where a click would hit the interface instead of the lot: the
    toolbar at the top, the catalog and the Cancel bar at the bottom (their top is about 73 percent
    down the screen), or the edges, which scroll the camera."""
    try:
        (w, h) = _stage_size()
    except Exception:
        return True
    if w < 100 or h < 100:
        return True
    (x, y) = pt
    return 0.02 * w <= x <= 0.98 * w and 0.08 * h <= y <= 0.70 * h


def on_main(fn, *args):
    """Worker thread only: run fn on the game thread and wait for its result."""
    ev = threading.Event()
    box = []

    def go():
        try:
            box.append(fn(*args))
        except Exception:
            core.log_exc("on_main")
            box.append(None)
        ev.set()
    core.post(go)
    ev.wait(10)
    return box[0] if box else None


def current_floor():
    """The floor the game is showing and building on (0 = ground floor). The game keeps the camera
    target about 1 meter above the floor it shows, and tells us where the target is."""
    import camera, terrain
    t = camera._target_position
    if t is None:
        return None
    return int(round((t.y - terrain.get_terrain_height(t.x, t.z) - 1.0) / 3.0))


def set_floor(level):
    """Worker thread only. Go up or down floors with Page Up / Page Down (the game's floor keys)
    until the game shows `level`. Returns True when it does."""
    u = _user32()
    for _ in range(3):
        now = on_main(current_floor)
        if now is None:
            # The game has not told us where the camera is yet: start from the ground floor.
            core.log("floor: unknown, assuming ground floor")
            now = 0
        if now == level:
            return True
        key = (0x21, 0x49) if level > now else (0x22, 0x51)     # Page Up / Page Down
        for _i in range(abs(level - now)):
            u.keybd_event(key[0], key[1], 1, 0)
            time.sleep(0.05)
            u.keybd_event(key[0], key[1], 3, 0)
            time.sleep(1.2)
        time.sleep(1.0)
    ok = on_main(current_floor) == level
    core.log("floor: wanted {} now {}".format(level, on_main(current_floor)))
    return ok


def undo():
    _send_ui("A11y|build|undo|{}".format(_new_serial()))


def run_job(points_world, level, action, describe, verify=None, height=0.0, view=None):
    """Do one pointing job in a background thread so the game keeps drawing frames."""
    if _busy[0]:
        core.speak("Still working on the last build step.")
        return
    _busy[0] = True

    def work():
        try:
            if point_and_act(points_world, level, action, describe, height, view) and verify is not None:
                core.post(verify)
        except Exception:
            core.log_exc("build job")
            core.post(core.speak, "Sorry, the build step failed.")
        finally:
            _busy[0] = False

    threading.Thread(target=work, name="tyjokr_a11y_plus_build", daemon=True).start()

# ---------------------------------------------------------------- selected tool / product

_product = {"id": None, "name": ""}


def _hook_product():
    try:
        import tyjokr_a11y_place as place
    except Exception:
        return
    if getattr(place, "_a11yplus_hooked", False):
        return
    original = place.set_product

    def a11yplus_set_product(instance_text, name):
        try:
            text = str(instance_text or "").strip()
            _product["id"] = int(text) if text.isdigit() and int(text) else None
            _product["name"] = str(name or "").strip()
            core.log("build: selected product {} {!r}".format(_product["id"], _product["name"]))
        except Exception:
            pass
        return original(instance_text, name)

    place.set_product = a11yplus_set_product
    place._a11yplus_hooked = True


def tool_name():
    return _product["name"] or ""


def _tool_is(*words):
    name = tool_name().lower()
    return any(w in name for w in words)

# ---------------------------------------------------------------- user features


def describe_lot():
    import tyjokr_a11y_plus_rooms as rooms
    f, grid = tile_map()
    free = sum(1 for row in grid for c in row if c == "free")
    parts = ["The lot is {} meters from west to east, and {} meters from north to south.".format(f.width, f.depth)]
    rlist = [r for r in rooms.scan_rooms() if r.level == 0]
    if rlist:
        parts.append("Ground floor rooms, as meters from the west edge and from the north edge:")
        for r in rlist:
            es = [f.local(t[0], t[1])[0] for t in r.tiles]
            ns = [f.local(t[0], t[1])[1] for t in r.tiles]
            parts.append("{}: {} to {} from west, {} to {} from north.".format(
                r.name, int(min(es)), int(max(es)) + 1, int(min(ns)), int(max(ns)) + 1))
    sim = core.active_sim()
    if sim is not None:
        (e, n) = f.local(sim.position.x, sim.position.z)
        parts.append("{} is at {} from west, {} from north.".format(sim.sim_info.first_name, int(e), int(n)))
    parts.append("{} square meters are free for building.".format(free))
    core.speak(" ".join(parts))


def _numbers(text):
    return [int(v) for v in re.findall(r"\d+", text or "")]


def build_room():
    if not in_build_mode():
        core.speak("Go to Build mode first with F2.")
        return
    if not _tool_is("room tool"):
        core.speak("First choose the Room Tool in the Build catalog. Tab to the catalog, open Walls and Empty Rooms, "
                   "choose Room Tool with Enter, press Escape, then Alt+B again.")
        return

    def got_size(text):
        nums = _numbers(text)
        if len(nums) < 2 or not (1 <= nums[0] <= 30 and 1 <= nums[1] <= 30):
            core.speak("Please type two numbers, for example 4 5.")
            return
        (w, d) = nums[0], nums[1]
        f, grid = tile_map()
        spots = free_spots(grid, w, d)
        rows = []
        for (e, n) in spots:
            rows.append(("{} from west, {} from north".format(e, n),
                         "This room {}.".format(_touch_text(grid, e, n, w, d)), (e, n)))
        rows.append(("Type a position", "Type the meters from the west edge and from the north edge.", "type"))
        if not spots:
            core.speak("No free space fits {} by {} meters. You can still type a position.".format(w, d))

        def place_at(value):
            if value == "type":
                core.ask_text("Room position", "Type meters from the west edge, then meters from the north edge, for example 2 3.", "",
                              lambda t: _do_room(w, d, *(_numbers(t) + [None, None])[:2]))
            else:
                _do_room(w, d, value[0], value[1])

        core.choose("Where to build", "Free places for a {} by {} meter room. The position is the north west corner.".format(w, d),
                    rows, place_at, tag="build")

    core.ask_text("Room size", "Type the width from west to east, then the depth from north to south, in meters. For example 4 5.",
                  "", got_size)


def _new_room_box(before):
    """Box (e0, n0, e1, n1) of rooms that did not exist before, or None. Rooms are compared by their
    box, because the game may renumber a room when a new one is built next to it."""
    import tyjokr_a11y_plus_rooms as rooms
    new = [_room_box(r) for r in rooms.scan_rooms() if (_room_box(r), r.level) not in before]
    if not new:
        return None
    return (min(b[0] for b in new), min(b[1] for b in new), max(b[2] for b in new), max(b[3] for b in new))


def _room_ids():
    import tyjokr_a11y_plus_rooms as rooms
    return {(_room_box(r), r.level) for r in rooms.scan_rooms()}


def _do_room(w, d, e, n):
    if e is None or n is None:
        core.speak("I need two numbers.")
        return
    f = frame()
    if e < 1 or n < 1 or e + w > f.width - 1 or n + d > f.depth - 1:
        core.speak("That does not fit. Rooms must stay at least 1 meter inside the lot edge. The lot is {} by {} meters.".format(
            f.width, f.depth))
        return
    if _busy[0]:
        core.speak("Still working on the last build step.")
        return
    _busy[0] = True
    want = (e, n, e + w, n + d)
    core.speak("Building a {} by {} meter room. Please wait.".format(w, d))

    def work():
        try:
            box = room_worker(want)
            if box in (None, "nomoney", "open", "noscreen"):
                if box in ("nomoney", None):
                    core.post(core.speak, "The room was not built. Something may be in the way, or there is not enough money.")
                elif box == "open":
                    core.post(core.speak, "The walls were built, but they did not make a closed room.")
                return
            (bw, bd) = (box[2] - box[0], box[3] - box[1])
            if (bw, bd) == (w, d) and box[:2] == want[:2]:
                core.post(core.speak, "Built a {} by {} meter room at {} from west, {} from north.".format(w, d, e, n))
            else:
                core.post(core.speak, "Built a room, but it came out {} by {} meters, at {} from west, {} from north. "
                                      "You can undo it from the TS4 Access build actions.".format(bw, bd, box[0], box[1]))
        except Exception:
            core.log_exc("room job")
            core.post(core.speak, "Sorry, building the room failed.")
        finally:
            _busy[0] = False

    threading.Thread(target=work, name="a11yplus_room", daemon=True).start()

def room_worker(want, overview=False, tries=4, level=0):
    """Worker thread only. Draw a room with the Room Tool (already chosen) from corner (want[0], want[1])
    to (want[2], want[3]), in meters from the west and north edges. The room tool snaps to the nearest
    grid corner; where a side meets an existing wall the game sometimes stops a meter short, so check
    the result and redraw with a correction. Returns the built box, or "nomoney", "open", "noscreen"."""
    f = frame()
    fix = [0.0, 0.0, 0.0, 0.0]
    box = None
    if not set_floor(level):
        return "nofloor"
    for attempt in range(tries):
        before = on_main(_room_ids) or set()
        money = on_main(funds)
        a = f.world(want[0] - fix[0], want[1] - fix[1])
        b = f.world(want[2] - fix[2], want[3] - fix[3])
        if not point_and_act([a, b], level, lambda s: drag(s[0], s[1]), "room {} try {}".format(want, attempt + 1),
                             overview=overview):
            return "noscreen"
        # 0.7.1: slower computers take longer to report a new room (upstairs especially).
        for _wait in range(10):
            time.sleep(0.5)
            box = on_main(_new_room_box, before)
            if box is not None:
                break
        core.log("build: wanted {} got {} (fix {})".format(want, box, fix))
        if box is None:
            spent = (money or 0) - (on_main(funds) or 0)
            if spent <= 0:
                return "nomoney"
            if attempt == tries - 1:
                return "open"
            # 0.7.1: walls were built but did not close a room: take them back and draw again.
            core.log("build: walls did not close, undo and try again")
            on_main(undo)
            time.sleep(2.0)
            if not set_floor(level):
                return "nofloor"
            continue
        err = [box[i] - want[i] for i in range(4)]
        if err == [0, 0, 0, 0]:
            break
        if attempt == tries - 1 or any(abs(v) > 2 for v in err):
            break
        on_main(undo)
        time.sleep(1.5)
        # Half a meter at a time: the pointer lands between grid corners.
        fix = [fix[i] + 0.5 * err[i] for i in range(4)]
    return box


def build_wall():
    if not in_build_mode():
        core.speak("Go to Build mode first with F2.")
        return
    # The Wall Tool has its own game key, B; press it for the player.
    u = _user32()
    u.keybd_event(0x42, 0x30, 0, 0)
    u.keybd_event(0x42, 0x30, 2, 0)
    _product.update(id=None, name="Wall Tool")

    def got(text):
        nums = _numbers(text)
        if len(nums) < 3:
            core.speak("Please type three numbers: from west, from north, and length.")
            return
        (e, n, length) = nums[:3]
        rows = [("East", None, (1, 0)), ("South", None, (0, 1)), ("West", None, (-1, 0)), ("North", None, (0, -1))]

        def go(direction):
            f = frame()
            (de, dn) = direction
            e2, n2 = e + de * length, n + dn * length
            if not (0 <= e <= f.width and 0 <= n <= f.depth and 0 <= e2 <= f.width and 0 <= n2 <= f.depth):
                core.speak("That wall would leave the lot.")
                return
            core.speak("Drawing a {} meter wall. Please wait.".format(length))
            run_job([f.world(e, n), f.world(e2, n2)], 0, lambda s: drag(s[0], s[1]), "wall",
                    cost_check("Built the wall", "The wall was not built. Something may be in the way."))
        core.choose("Wall direction", "Which way does the wall go from the start point?", rows, go, tag="build")

    core.ask_text("Wall", "Type the start point as meters from the west edge and from the north edge, then the length. For example 2 3 5.",
                  "", got)


def funds():
    try:
        import services
        return int(services.active_household().funds.money)
    except Exception:
        return None


def cost_check(done_text, fail_text):
    """A verify callback: compares household money before and after the job."""
    before = funds()
    started = time.monotonic()

    def verify():
        after = funds()
        if before is None or after is None:
            core.speak(done_text + ".")
        elif after < before:
            core.speak("{}. It cost {:,} simoleons.".format(done_text, before - after))
        elif after > before:
            core.speak("{}. You got {:,} simoleons back for what it replaced.".format(done_text, after - before))
        else:
            reason = _last_error["text"] if _last_error["at"] > started else ""
            core.speak("Not done. The game says: {}".format(reason) if reason else fail_text)
    return verify


def _room_rows():
    import tyjokr_a11y_plus_rooms as rooms
    rows = []
    for r in rooms.scan_rooms():
        rows.append((r.name, "{}, {}".format(r.size_text(), rooms.floor_name(r.level)), r))
    return rows


def _room_box(room):
    f = frame()
    es = [f.local(t[0], t[1])[0] for t in room.tiles]
    ns = [f.local(t[0], t[1])[1] for t in room.tiles]
    return (math.floor(min(es)), math.floor(min(ns)), math.floor(max(es)) + 1, math.floor(max(ns)) + 1)


def wall_point(room, side, where=0.5):
    """World (x, z) on the middle of a room wall, a little inside the room so the click hits it."""
    f = frame()
    (e0, n0, e1, n1) = _room_box(room)
    inset = 0.0
    if side == "north":
        return f.world(e0 + (e1 - e0) * where, n0 + inset)
    if side == "south":
        return f.world(e0 + (e1 - e0) * where, n1 - inset)
    if side == "west":
        return f.world(e0 + inset, n0 + (n1 - n0) * where)
    return f.world(e1 - inset, n0 + (n1 - n0) * where)


def _room_tiles(room):
    f = frame()
    return {(int(math.floor(f.local(t[0], t[1])[0])), int(math.floor(f.local(t[0], t[1])[1]))) for t in room.tiles}


# side -> (tile step to the outside neighbor, how to read "left to right" when facing that wall from inside)
_SIDES = {
    "north": ((0, -1), lambda e, n: e),
    "south": ((0, 1), lambda e, n: -e),
    "west": ((-1, 0), lambda e, n: -n),
    "east": ((1, 0), lambda e, n: n),
}


def room_walls(room):
    """List of walls: dict(side, cells=[(e, n), ...] left to right). Each cell is the 1 m wall piece
    on that side of the room tile (e, n)."""
    tiles = _room_tiles(room)
    walls = []
    for (side, ((de, dn), order)) in _SIDES.items():
        cells = sorted([t for t in tiles if (t[0] + de, t[1] + dn) not in tiles], key=lambda t: order(*t))
        if cells:
            walls.append({"side": side, "cells": cells})
    return walls


def wall_cell_point(side, cell):
    """World (x, z) at the middle of the wall piece on `side` of tile `cell`."""
    f = frame()
    (e, n) = cell
    if side == "north":
        return f.world(e + 0.5, n)
    if side == "south":
        return f.world(e + 0.5, n + 1)
    if side == "west":
        return f.world(e, n + 0.5)
    return f.world(e + 1, n + 0.5)


def _wall_things():
    """Doors and windows on the lot: list of (e, n, kind)."""
    import services
    import tyjokr_a11y_plus_rooms as rooms
    f = frame()
    out = []
    for obj in services.object_manager().values():
        try:
            names = rooms.tag_names(obj)
            kind = "door" if ("Build_Door" in names or "Build_Arch" in names) else ("window" if "Build_Window" in names else None)
            if kind:
                (e, n) = f.local(obj.position.x, obj.position.z)
                out.append((e, n, kind))
        except Exception:
            continue
    return out


def _cell_status(side, cell, things):
    (x, z) = wall_cell_point(side, cell)
    (e, n) = frame().local(x, z)
    for (te, tn, kind) in things:
        if abs(te - e) < 0.75 and abs(tn - n) < 0.75:
            return kind
    return None


def _reselect():
    """Choose the catalog item again right before using it (the game sometimes drops it)."""
    index = _cat.get("chosen")
    if index is not None:
        on_main(_send_ui, "A11y|plus|select|{}".format(index))
        time.sleep(0.7)


def place_on_wall():
    if not in_build_mode():
        core.speak("Go to Build mode first with F2.")
        return
    if not tool_name():
        core.speak("First choose a door or window with Alt+B, Catalog.")
        return
    rows = _room_rows()
    if not rows:
        core.speak("There are no rooms yet.")
        return

    def got_room(room):
        walls = room_walls(room)
        things = _wall_things()
        wrows = []
        for w in walls:
            used = [_cell_status(w["side"], c, things) for c in w["cells"]]
            note = ", ".join("{} {}{}".format(used.count(k), k, "" if used.count(k) == 1 else "s") for k in ("door", "window") if k in used)
            wrows.append(("{} wall, {} meters".format(w["side"].capitalize(), len(w["cells"])),
                          ("Has " + note + ".") if note else "No doors or windows yet.", w))

        def got_wall(w):
            srows = []
            for (i, cell) in enumerate(w["cells"]):
                st = _cell_status(w["side"], cell, things)
                srows.append(("Meter {} from the left".format(i + 1),
                              "A {} is here already.".format(st) if st else "Free.", cell))

            def got_cell(cell):
                (x, z) = wall_cell_point(w["side"], cell)
                core.speak("Placing {} on the {} wall of the {}. Please wait.".format(tool_name(), w["side"], room.name))

                def act(s):
                    _reselect()
                    click(s[0])
                run_job([(x, z)], room.level, act, "wall item", height=0.15, view=VIEW_FROM[w["side"]],
                        verify=cost_check("Placed {}".format(tool_name()),
                                          "It was not placed. There may be a door, window or furniture in the way, or the wall is too short."))
            core.choose("Where on the {} wall".format(w["side"]),
                        "Meters are counted from the left as you face the wall from inside the room.", srows, got_cell, tag="build")
        core.choose("Which wall", "Walls of the {}.".format(room.name), wrows, got_wall, tag="build")
    core.choose("Place {}".format(tool_name()), "Choose the room.", rows, got_room, tag="build")

def paint_room(part):
    if not in_build_mode():
        core.speak("Go to Build mode first with F2.")
        return
    if not tool_name():
        core.speak("First choose a wall pattern or a floor pattern in the Build catalog, press Escape, then Alt+B again.")
        return
    rows = _room_rows()

    def got_room(room):
        if part == "walls":
            target = wall_point(room, "north")
        else:
            target = room.center
        core.speak("Painting the {} of the {}. Please wait.".format(part, room.name))
        run_job([target], room.level, lambda s: click(s[0], shift=True), "paint " + part,
                cost_check("Painted the {} of the {}".format(part, room.name), "Nothing was painted."),
                height=0.15 if part == "walls" else 0.0, view=VIEW_FROM["north"] if part == "walls" else None)
    core.choose("Paint {}".format(part), "Choose the room. The whole room gets the chosen pattern.", rows, got_room, tag="build")


# ---------------------------------------------------------------- catalog search assistant
# Moves TS4 Access's keyboard focus to the Build catalog's search field, types the words, and
# moves to the first result. Typing into the game directly is risky: if the search field is not
# being edited, letters are Build mode shortcuts (B wall tool, K sledgehammer...).


class _Quiet(object):
    """While navigating, record what TS4 Access would say instead of speaking it."""
    def __init__(self):
        self.said = []

    def __enter__(self):
        import tyjokr_a11y_speech as s
        self._s = s
        self._orig = s.speak

        def record(text, *args, **kwargs):
            self.said.append(str(text or ""))
        s.speak = record
        return self

    def __exit__(self, *exc):
        self._s.speak = self._orig
        return False

    def last(self):
        return self.said[-1] if self.said else ""


def _nav_until(quiet, words, message="A11yTabNext", steps=160, delay=0.15):
    import tyjokr_a11y_keys as keys
    for _ in range(steps):
        core.post(keys._send, message)
        time.sleep(delay)
        text = quiet.last().lower()
        if any(w in text for w in words):
            return quiet.last()
    return None


def _type_text(text):
    u = _user32()
    for ch in text.upper():
        if "A" <= ch <= "Z" or "0" <= ch <= "9":
            vk = ord(ch)
        elif ch == " ":
            vk = 0x20
        else:
            continue
        u.keybd_event(vk, 0, 0, 0)
        time.sleep(0.03)
        u.keybd_event(vk, 0, 2, 0)
        time.sleep(0.06)


def catalog_search():
    if not in_build_mode():
        core.speak("Go to Build mode first with F2.")
        return

    def got(query):
        query = "".join(ch for ch in query if ch.isalnum() or ch == " ").strip()
        if not query:
            core.speak("Nothing to search for.")
            return
        if _busy[0]:
            core.speak("Still working on the last build step.")
            return
        _busy[0] = True
        core.speak("Searching the catalog for {}. Please wait.".format(query))

        def work():
            import tyjokr_a11y_keys as keys
            try:
                time.sleep(1.5)
                with _Quiet() as q:
                    # The search field sits just before the catalog items, so walking backwards
                    # from inside a long item list reaches it soonest.
                    found = _nav_until(q, ["text field"], message="A11yTabPrev", steps=400, delay=0.12)
                    if not found:
                        core.log("search nav heard: {!r}".format(q.said[-40:]))
                        core.post(core.speak, "I could not find the catalog search field.")
                        return
                    core.post(keys._send, "A11yActivate")
                    time.sleep(0.6)
                    _type_text(query)
                    time.sleep(0.2)
                    u = _user32()
                    u.keybd_event(0x0D, 0, 0, 0)
                    u.keybd_event(0x0D, 0, 2, 0)
                    time.sleep(1.5)
                    first = _nav_until(q, ["simoleons"], steps=12, delay=0.3)
                if first:
                    core.post(core.speak, "Results for {}. First: {}. Tab moves to the next result, Shift+Tab back. "
                                          "Enter chooses one, then press Escape and use Alt+B.".format(query, first))
                else:
                    core.post(core.speak, "Nothing found for {}.".format(query))
            except Exception:
                core.log_exc("catalog search")
                core.post(core.speak, "The search failed.")
            finally:
                _busy[0] = False

        threading.Thread(target=work, name="a11yplus_search", daemon=True).start()

    core.ask_text("Search the catalog", "Type what to look for, for example door, window, brick wall, wood floor.", "", got)

# ---------------------------------------------------------------- accessible catalog
# Uses the TS4 Access Plus bridge added to TS4 Access's interface file: "A11y|plus|catalog|type|tags|serial"
# lists a catalog category, "A11y|plus|select|index" picks an item exactly as clicking it would.

# (menu name, product type, comma separated catalog tag names, what to do next)
BUILD_CATALOG = (
    ("Doors", 2, "BUILDTAG_DOOR", "wall"),
    ("Windows", 2, "BUILDTAG_WINDOW", "wall"),
    ("Wall patterns, paint and wallpaper", 7, "", "paintwalls"),
    ("Floor patterns", 5, "", "paintfloor"),
    ("Stairs", 14, "", "none"),
    ("Fences", 10, "", "none"),
    ("Gates", 2, "BUILDTAG_GATE", "wall"),
    ("Columns", 2, "BUILDTAG_COLUMN", "none"),
    ("Roofs", 4, "", "none"),
    ("Rooms and wall tools", 16, "BUILDTAG_BLOCK_WALLTOOL,BUILDTAG_BLOCK_WITH_WALLS", "tool"),
    ("Plants, bushes and trees", 2, "BUILDTAG_SHRUB,BUILDTAG_FLOWER,BUILDTAG_TREE", "object"),
)
STYLED_ROOMS = (
    ("Bathrooms", "BUYCAT_MAG_BATHROOM"), ("Bedrooms", "BUYCAT_MAG_BEDROOM"), ("Kitchens", "BUYCAT_MAG_KITCHEN"),
    ("Living rooms", "BUYCAT_MAG_LIVINGROOM"), ("Dining rooms", "BUYCAT_MAG_DINNINGROOM"), ("Studies", "BUYCAT_MAG_STUDY"),
    ("Kids rooms", "BUYCAT_MAG_KIDS"), ("Outdoor areas", "BUYCAT_MAG_OUTDOOR"),
)
BUY_CATALOG = (
    ("Beds", "BUYCAT_SS_BED"), ("Sofas and loveseats", "BUYCAT_SS_SOFA,BUYCAT_SS_LOVESEAT"),
    ("Living chairs", "BUYCAT_SS_LIVINGCHAIR"), ("Dining tables", "BUYCAT_SS_DININGTABLE"),
    ("Dining chairs", "BUYCAT_SS_DININGCHAIR"), ("Desks", "BUYCAT_SS_DESK"), ("Desk chairs", "BUYCAT_SS_DESKCHAIR"),
    ("Coffee and end tables", "BUYCAT_SS_COFFEETABLE,BUYCAT_SS_ENDTABLE"), ("Counters", "BUYCAT_SS_COUNTER"),
    ("Dressers", "BUYCAT_SS_DRESSER"), ("Bookshelves", "BUYCAT_SS_BOOKSHELF"),
    ("Refrigerators", "BUYCAT_PA_REFRIGERATOR"), ("Stoves and ovens", "BUYCAT_PA_STOVE"),
    ("Small appliances", "BUYCAT_PA_SMALLAPPLIANCE,BUYCAT_PA_MICROWAVE,BUYCAT_PA_COFFEE_MAKER"),
    ("Sinks", "BUYCAT_PA_SINK"), ("Toilets", "BUYCAT_PA_TOILET"), ("Showers", "BUYCAT_PA_SHOWER"), ("Bathtubs", "BUYCAT_PA_TUB"),
    ("Trash cans", "BUYCAT_PA_DISPOSABLE,BUYCAT_PA_DISPOSAL_INDOOR"),
    ("Televisions", "BUYCAT_EE_TV"), ("Computers", "BUYCAT_EE_COMPUTER"), ("Music and audio", "BUYCAT_EE_AUDIO"),
    ("Creative activities, easels and instruments", "BUYCAT_EE_CREATIVEACTIVITY"),
    ("Knowledge activities, chess and telescopes", "BUYCAT_EE_KNOWLEDGEACTIVITY"),
    ("Exercise and active", "BUYCAT_EE_ACTIVEACTIVITY"), ("Kids and toddlers", "BUYCAT_EE_KIDFURNITURE,BUYCAT_EE_KIDTOY,BUYCAT_EE_TODDLERS"),
    ("Ceiling lights", "BUYCAT_LD_CEILINGLIGHT"), ("Table and floor lamps", "BUYCAT_LD_TABLELAMP,BUYCAT_LD_FLOORLAMP"),
    ("Wall lights", "BUYCAT_LD_WALLLIGHT"), ("Outdoor lights", "BUYCAT_LD_OUTDOORLIGHT"),
    ("Mirrors", "BUYCAT_LD_MIRROR"), ("Rugs", "BUYCAT_LD_RUG"), ("Plants for indoors", "BUYCAT_LD_PLANT"),
    ("Wall decorations and paintings", "BUYCAT_LD_WALLDECORATION"), ("Other decorations", "BUYCAT_LD_MISCDECORATION,BUYCAT_LD_SCULPTURE"),
    ("Outdoor seating and tables", "BUYCAT_SS_OUTDOORSEATING,BUYCAT_SS_OUTDOORTABLES,BUYCAT_SS_OUTDOORCHAIR"),
    ("Grills and outdoor cooking", "BUYCAT_PA_OUTDOORCOOKING"),
)

_cat = {"serial": 0, "items": [], "total": 0, "name": "", "next": "", "event": None}
_bridge = {"pong": 0.0}
_last_error = {"text": "", "at": 0.0}


def _flash_reply(encoded=""):
    from urllib.parse import unquote
    text = unquote(str(encoded or ""))
    parts = text.split("|")
    kind = parts[0]
    if kind == "pong":
        _bridge["pong"] = time.monotonic()
        core.log("bridge: pong")
    elif kind == "cat" and len(parts) >= 5 and parts[1] == str(_cat["serial"]):
        _cat["total"] = int(parts[3])
        for item in parts[4].split("^"):
            bits = item.split("~")
            if len(bits) >= 2:
                _cat["items"].append((unquote(bits[0]), int(float(bits[1] or 0)), int(bits[2] or 1) if len(bits) > 2 else 1))
    elif kind == "catend" and len(parts) >= 2 and parts[1] == str(_cat["serial"]):
        if _cat.get("quiet") is not None:
            _cat["quiet"].set()
        else:
            core.post(_show_catalog)
    elif kind == "selected":
        name = unquote(parts[2]) if len(parts) > 2 else "item"
        _product["name"] = name
        if not _cat.get("silent_select") and not _busy[0]:     # quiet while a build job picks things itself
            core.speak("Chosen: {}. {}".format(name, _NEXT_HINT.get(_cat["next"], "")))
    elif kind == "builderror":
        reason = unquote(parts[1]) if len(parts) > 1 else ""
        _last_error.update(text=reason, at=time.monotonic())
        core.log("game build error: " + reason)
    elif kind == "error":
        core.log("bridge error: " + text)
        core.speak("The catalog said: " + "|".join(parts[1:]))
    return True


_NEXT_HINT = {
    "wall": "Now use Alt+B, Put the chosen door or window on a wall.",
    "paintwalls": "Now use Alt+B, Paint the walls of a room.",
    "paintfloor": "Now use Alt+B, Paint the floor of a room.",
    "object": "Now use Alt+B, Put the chosen object in a room.",
    "tool": "Now use Alt+B to build with it.",
    "room": "Now use Alt+B, Place the chosen furnished room.",
    "none": "Placing this needs the build cursor. See the TS4 Access build controls.",
}


def bridge_ok():
    return time.monotonic() - _bridge["pong"] < 600


def _register_flash_command():
    import sims4.commands

    @sims4.commands.Command("a11yplus.flash", command_type=sims4.commands.CommandType.Live)
    def a11yplus_flash(encoded: str = "", _connection=None):
        try:
            return _flash_reply(encoded)
        except Exception:
            core.log_exc("flash reply")
            return False


try:
    _register_flash_command()
except Exception:
    core.log_exc("register a11yplus.flash")


def ping_bridge():
    _send_ui("A11y|plus|ping")


def request_catalog(name, product_type, tags, nxt):
    if not in_build_mode():
        core.speak("Go to Build mode first with F2.")
        return
    _cat["serial"] += 1
    _cat.update(items=[], total=0, name=name, next=nxt, quiet=None)
    core.speak("Opening {}.".format(name))
    _send_ui("A11y|plus|catalog|{}|{}|{}".format(product_type, tags, _cat["serial"]))

    def timeout(serial=_cat["serial"]):
        if _cat["serial"] == serial and not _cat["items"] and not bridge_ok():
            core.speak("The catalog did not answer. The TS4 Access Plus part of the TS4 Access interface file may be missing.")
    threading.Timer(4.0, lambda: core.post(timeout)).start()


def fetch_catalog(product_type, tags, nxt, timeout=6.0):
    """Worker thread only: list a catalog category without showing it. Returns [(name, price, colors)]."""
    ev = threading.Event()

    def start():
        _cat["serial"] += 1
        _cat.update(items=[], total=0, name="", next=nxt, quiet=ev)
        _send_ui("A11y|plus|catalog|{}|{}|{}".format(product_type, tags, _cat["serial"]))
    core.post(start)
    ev.wait(timeout)
    _cat["quiet"] = None
    return list(_cat["items"])


def select_item(index, name):
    """Worker thread only: choose catalog item `index` of the last fetched list, as clicking it would."""
    _cat["chosen"] = index
    _product["name"] = name
    on_main(_send_ui, "A11y|plus|select|{}".format(index))
    time.sleep(0.8)


def _show_catalog():
    items = _cat["items"]
    if not items:
        core.speak("{} is empty.".format(_cat["name"]))
        return
    rows = []
    for (i, (name, price, variations)) in enumerate(items):
        desc = "{:,} simoleons".format(price)
        if variations > 1:
            desc += ", {} colors".format(variations)
        rows.append((name, desc, i))
    core.choose(_cat["name"], "{} items. Enter chooses one.".format(len(items)), rows,
                _choose_item, tag="catalog")


def _choose_item(i):
    _cat["chosen"] = i
    _send_ui("A11y|plus|select|{}".format(i))


def open_catalog():
    rows = [(name, None, ("build", name, t, tags, nxt)) for (name, t, tags, nxt) in BUILD_CATALOG]
    rows.insert(0, ("Furnished rooms", "Ready-made rooms with walls, floor, door and furniture: bathrooms, bedrooms, kitchens and more.", ("styled",)))
    rows.append(("Furniture and other objects", "Beds, fridges, toilets, lights and more, by kind.", ("buy",)))

    def picked(value):
        if value[0] == "styled":
            srows = [(name, None, (name, tags)) for (name, tags) in STYLED_ROOMS]
            core.choose("Furnished rooms", "Choose a kind of room.", srows,
                        lambda v: request_catalog("Furnished " + v[0].lower(), 23, v[1], "room"), tag="catalog")
        elif value[0] == "buy":
            brows = [(name, None, (name, tags)) for (name, tags) in BUY_CATALOG]
            core.choose("Furniture and objects", "Choose a kind of object.", brows,
                        lambda v: request_catalog(v[0], 2, v[1], "object"), tag="catalog")
        else:
            request_catalog(value[1], value[2], value[3], value[4])
    core.choose("Catalog", "What do you want to buy or build with?", rows, picked, tag="catalog")


def place_object_in_room():
    if not in_build_mode():
        core.speak("Go to Build mode first with F2.")
        return
    rows = _room_rows()
    if not rows:
        core.speak("There are no rooms yet.")
        return

    def got(room):
        try:
            import routing, services, terrain, sims4.math
            import tyjokr_a11y_place as place
            (x, z) = room.center
            surface = routing.SurfaceIdentifier(services.current_zone_id(), room.level, routing.SurfaceType.SURFACETYPE_WORLD)
            pos = sims4.math.Vector3(x, terrain.get_terrain_height(x, z, routing_surface=surface), z)
            if not place.product():
                core.speak("First choose an object in the catalog with Alt+B, Catalog.")
                return
            place.place(pos, room.level, surface)
        except Exception:
            core.log_exc("place in room")
            core.speak("Could not place it.")
    core.choose("Put it in which room", "TS4 Access finds a free spot near the middle of the room and buys it.", rows, got, tag="build")


def place_styled_room():
    if not in_build_mode():
        core.speak("Go to Build mode first with F2.")
        return
    if _cat.get("next") != "room" or _cat.get("chosen") is None:
        core.speak("First choose a furnished room with Alt+B, Catalog, Furnished rooms.")
        return
    f, grid = tile_map()
    spots = free_spots(grid, 4, 4) or free_spots(grid, 3, 3)
    rows = [("Around {} from west, {} from north".format(e + 2, n + 2), "Free space. " + _touch_text(grid, e, n, 4, 4).capitalize() + ".",
             (e + 2, n + 2)) for (e, n) in spots]
    rows.append(("Type a position", "Type the meters from the west edge and from the north edge for the middle of the room.", "type"))

    def go(center):
        (ce, cn) = center
        name = tool_name()
        before = _room_ids()
        money = cost_check("Placed " + name, "The room was not placed. It may not fit there.")

        def verify_and_describe():
            box = _new_room_box(before)
            if box is None:
                money()
                return
            g = tile_map()[1]
            (w, d) = (box[2] - box[0], box[3] - box[1])
            core.speak("Placed {}. It is {} by {} meters, from {} to {} west, {} to {} north. It {}. "
                       "Use Alt+R to hear what is inside.".format(name, w, d, box[0], box[2], box[1], box[3], _touch_text(g, box[0], box[1], w, d)))

        x, z = f.world(ce, cn)
        core.speak("Placing {}. Please wait.".format(name))

        def act(s):
            _reselect()
            click(s[0])
        run_job([(x, z)], 0, act, "styled room", verify_and_describe)

    def picked(value):
        if value == "type":
            core.ask_text("Room position", "Type meters from the west edge, then from the north edge, for example 3 6.", "",
                          lambda t: go(tuple((_numbers(t) + [0, 0])[:2])))
        else:
            go(value)
    core.choose("Where to put {}".format(tool_name()), "The room is placed with its middle at the spot you choose.", rows, picked, tag="build")

def _undo_spoken():
    undo()
    core.speak("Undone.")


@core.hotkey(ord("B"), "build helper")
def open_menu():
    _hook_product()
    if not in_build_mode():
        core.speak("The build helper works in Build mode. Press F2 first, on a laptop Fn+F2.")
        return
    tool = tool_name() or "nothing"
    import tyjokr_a11y_plus_house as house, tyjokr_a11y_plus_furnish as furnish, tyjokr_a11y_plus_decor as decor, tyjokr_a11y_plus_draw as draw
    rows = []
    if draw.is_on():
        rows += [
            ("Choose the drawing tool", "Wall, room or roof.", draw.choose_tool),
            ("Turn the drawing cursor off", None, draw.stop),
        ]
    else:
        rows.append(("Draw with a cursor, like sighted players",
                     "Move a cursor around the lot with Alt+arrows and draw walls, rooms and roofs from corner to corner.",
                     draw.start))
    rows += [
        ("Put a roof on my house", "Choose a roof style. One roof goes over all the ground floor rooms.", draw.roof_whole_house),
        ("Build my house", "Choose the rooms you want. The whole house is built with doors between the rooms.", house.build_my_house),
        ("Door between two rooms", "Choose two rooms, or a room and the yard. The door goes in the middle of the wall between them.",
         house.door_between_rooms),
        ("Remove a door or window", "Lists every door and window and where it is.", house.remove_door_or_window),
        ("Furnish a room with the basics", "Say what kind of room it is: the bed, toilet, fridge and so on are bought and placed.",
         furnish.furnish_room),
        ("Decorate a room", "Choose a room, walls or floor, then a paint, wallpaper or floor from a list. The whole room is done at once.",
         decor.decorate_room),
        ("Sell things in a room", "Lists everything in a room with what it sells for. Check the ones to sell.", decor.sell_in_room),
        ("Name a room", "Give a room a name, like Kitchen or Shay's bedroom.", house.name_a_room),
        ("Catalog", "Doors, windows, wall and floor patterns, furniture and more, as lists with prices.", open_catalog),
        ("Place the chosen furnished room", "After choosing one in Catalog, Furnished rooms. You choose a free spot.", place_styled_room),
        ("Put the chosen object in a room", "After choosing furniture in the Catalog. TS4 Access finds a free spot.", place_object_in_room),
        ("Describe the lot", "Lot size, rooms and free space, in meters from the west and north edges.", describe_lot),
        ("Build a room", "Needs the Room Tool chosen in the catalog. You give the size and choose a place.", build_room),
        ("Draw a wall", "Picks the Wall Tool for you. You give a start point, a direction and a length.", build_wall),
        ("Put the chosen door or window on a wall", "Choose a door or window in the catalog first.", place_on_wall),
        ("Paint the walls of a room", "Choose a wall pattern in the catalog first.", lambda: paint_room("walls")),
        ("Paint the floor of a room", "Choose a floor pattern in the catalog first.", lambda: paint_room("floor")),
        ("Undo the last build step", "Takes back the last thing built, with a refund.", _undo_spoken),
    ]
    core.choose("Build helper", "Chosen in the catalog now: {}.".format(tool), rows, lambda fn: fn(), tag="build")


@core.on_zone_started
def _start():
    _hook_product()
