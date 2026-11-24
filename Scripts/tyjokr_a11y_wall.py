"""Walls on the Build cursor: telling a wall from a fence, and hanging wall
objects. Contributed by DaRainbowGirlXX (2026-10-16), merged into TS4 Access
2026-11-12. The Build cursor (tyjokr_a11y_grid) calls these directly.

The wall height comes from the target layer (tyjokr_a11y_layers): Ctrl+Alt+U
and Ctrl+Alt+D step through ground, six wall heights and ceiling.
"""

import threading
import time

import tyjokr_a11y_settings as settings
import tyjokr_a11y_speech as speech


HEIGHTS = (
    ("very low", 0.5),
    ("low", 1.0),
    ("middle", 1.5),
    ("high", 2.0),
    ("very high", 2.5),
    ("near the top", 3.0),
)

_attempt = [0]     # diagnostics: screenshot slot 1 to 3


def _log(message):
    speech.log_line("wall: " + message)


def _text(en, pl):
    import tyjokr_a11y_grid as grid
    return grid._text(en, pl)


def _blocked(state):
    """A side the ray test found impassable with no object in the way.
    tiles.walls says 'wall'; tyjokr's October 1 build said 'blocked'."""
    return state in ("blocked", "wall")


def selected_height():
    import tyjokr_a11y_layers as layers
    return layers.wall_height()


def _wall_state():
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_tiles as tiles
    frame = tiles.frame()
    if frame is None:
        return None
    i, j = grid._tile
    objects = tiles.snapshot(grid._level)
    sides = tiles.walls(frame, i, j, grid._level)
    doors = tiles.doors(frame, i, j, grid._level, objects=objects)
    return frame, sides, doors


def selected_wall():
    """(frame, side) when the cursor faces a real wall, else None."""
    import tyjokr_a11y_grid as grid
    state = _wall_state()
    if state is None:
        return None
    frame, sides, doors = state
    side = int(grid._facing) % 4
    if side in doors or not _blocked(sides.get(side)) or not separates_rooms(frame, side):
        return None
    return frame, side


def separates_rooms(frame, side):
    """Room topology tells a wall from a fence: a wall has a different room
    on each side."""
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_tiles as tiles
    i, j = grid._tile
    di, dj = tiles.STEPS[side]
    try:
        here = tiles.room(frame, i, j, grid._level)
        there = tiles.room(frame, i + di, j + dj, grid._level)
    except Exception as ex:
        _log("room boundary check failed: {!r}".format(ex))
        return False
    return here is not None and there is not None and here != there


def _wall_anchor(frame, side):
    import sims4.math
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_tiles as tiles
    i, j = grid._tile
    di, dj = tiles.STEPS[side]
    center = tiles.position(frame, i, j, grid._level)
    neighbor = frame.world(i + di, j + dj)
    label, height = selected_height()
    point = sims4.math.Vector3(
        (float(center.x) + float(neighbor[0])) / 2.0,
        float(center.y) + height,
        (float(center.z) + float(neighbor[1])) / 2.0,
    )
    return point, height


def wall_parts(frame, all_sides=False, objects=None):
    """Walls, possible fences, doors and the lot edge around the cursor."""
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_tiles as tiles
    i, j = grid._tile
    sides = tiles.walls(frame, i, j, grid._level)
    doors = tiles.doors(frame, i, j, grid._level, objects=objects)
    if all_sides:
        parts = []
        for index in range(4):
            if index in doors:
                state = _text("door", "drzwi")
            elif _blocked(sides.get(index)) and separates_rooms(frame, index):
                state = _text("wall", "ściana")
            else:
                state = {
                    "blocked": _text("wall, or possibly a fence", "ściana lub prawdopodobnie płot"),
                    "wall": _text("wall, or possibly a fence", "ściana lub prawdopodobnie płot"),
                    "object": _text("an object is in the way", "przeszkadza obiekt"),
                    "edge": _text("lot edge", "granica parceli"),
                    "open": _text("open", "wolne"),
                }.get(sides.get(index), _text("unknown", "nieznane"))
            parts.append("{}: {}. ".format(tiles.direction_name(index).capitalize(), state))
        return parts
    walls, maybe = [], []
    for index in range(4):
        if _blocked(sides.get(index)) and index not in doors:
            (walls if separates_rooms(frame, index) else maybe).append(tiles.direction_name(index))
    door_dirs = [tiles.direction_name(index) for index in sorted(doors)]
    joiner = _text(" and ", " i ")
    parts = []
    if walls:
        parts.append(_text("Wall {}. ", "Ściana: {}. ").format(joiner.join(walls)))
    if maybe:
        parts.append(_text("Wall or fence {}. ", "Ściana lub płot: {}. ").format(joiner.join(maybe)))
    if door_dirs:
        parts.append(_text("Door {}. ", "Drzwi: {}. ").format(joiner.join(door_dirs)))
    return parts


# What the game said at each spot this session (Leo, 2026-11-12: say
# whether a wall object will hang before Enter). Key: zone, floor, tile,
# side, height label. Value: (hung, the game's message).
_history = {}
_hinted = [False]


def _spot_key(side):
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_place as place_mod
    return (place_mod._zone_id(), grid._level, tuple(grid._tile), side, selected_height()[0])


def remember(key, hung, message=""):
    _history[key] = (bool(hung), str(message or ""))
    _log("result at {}: {} {}".format(key, "hung" if hung else "refused", message))


def _uv(frame, x, z):
    """Continuous lot coordinates (east, north) of a world point."""
    dx, dz = float(x) - frame.origin[0], float(z) - frame.origin[1]
    return (dx * frame.east[0] + dz * frame.east[1], dx * frame.north[0] + dz * frame.north[1])


def _on_this_wall(frame, side):
    """Windows, doors and wall objects already on this tile's stretch of the
    chosen wall at about the chosen height: [(name, kind)]."""
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_layers as layers
    import tyjokr_a11y_place as place_mod
    import tyjokr_a11y_scanner as scanner
    import tyjokr_a11y_tiles as tiles
    i, j = grid._tile
    di, dj = tiles.STEPS[side]
    floor_y = float(tiles.position(frame, i, j, grid._level).y)
    _label, height = selected_height()
    found, seen = [], set()
    for (ti, tj) in ((i, j), (i + di, j + dj)):
        try:
            candidates = tiles.objects_on(frame, ti, tj, grid._level)
        except Exception:
            continue
        for obj in candidates:
            if getattr(obj, "is_sim", False) or obj.id in seen:
                continue
            seen.add(obj.id)
            try:
                u, v = _uv(frame, obj.position.x, obj.position.z)
            except Exception:
                continue
            if side in (0, 2):
                across, along = v - (j + (1 if side == 0 else 0)), u - (i + 0.5)
            else:
                across, along = u - (i + (1 if side == 1 else 0)), v - (j + 0.5)
            if abs(across) > 0.4 or abs(along) > 0.9:
                continue
            tags = " ".join(scanner._tag_names(obj)).lower()
            if "window" in tags:
                found.append((grid._name(obj), "window"))
            elif "door" in tags or "arch" in tags:
                found.append((grid._name(obj), "door"))
            elif place_mod.requirement(layers._definition_id(obj)) == "wall":
                try:
                    if abs((float(obj.position.y) - floor_y) - height) > 0.75:
                        continue
                except Exception:
                    pass
                found.append((grid._name(obj), "object"))
    return found


def _wall_continues(frame, side):
    """Which ends of this stretch have no wall beside them, and doors there:
    ([direction names without wall], [direction names with a door])."""
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_tiles as tiles
    i, j = grid._tile
    open_ends, doors_beside = [], []
    for along in ((1, 3) if side in (0, 2) else (0, 2)):
        ai, aj = tiles.STEPS[along]
        ni, nj = i + ai, j + aj
        name = tiles.direction_name(along)
        if not frame.inside(ni, nj):
            open_ends.append(name)
            continue
        try:
            if side in tiles.doors(frame, ni, nj, grid._level):
                doors_beside.append(name)
                continue
            if not _blocked(tiles.walls(frame, ni, nj, grid._level).get(side)):
                open_ends.append(name)
        except Exception as ex:
            _log("wall continuation check failed: {!r}".format(ex))
    return open_ends, doors_beside


def hang_report():
    """(verdict, [reasons]): 'no wall', 'no', 'maybe' or 'yes'. Built from
    what the mod can measure and what the game said here before; the game
    still has the final word when Enter clicks."""
    selected = selected_wall()
    if selected is None:
        return "no wall", []
    frame, side = selected
    if column_here(frame):
        return "no", [_text("a column is in the way", "przeszkadza kolumna")]
    past = _history.get(_spot_key(side))
    reasons, verdict = [], "yes"
    for name, kind in _on_this_wall(frame, side):
        name = "".join(str(p) for p in name) if isinstance(name, list) else str(name)
        if kind == "object":
            reasons.append(_text("{} already hangs here", "{} już tu wisi").format(name))
        else:
            reasons.append(_text("{} is in this stretch of wall", "{} jest na tym odcinku ściany").format(name))
        verdict = "no"
    open_ends, doors_beside = _wall_continues(frame, side)
    joiner = _text(" and ", " i ")
    if doors_beside:
        reasons.append(_text("a door is just {}", "tuż obok, {}, są drzwi").format(joiner.join(doors_beside)))
        verdict = "maybe" if verdict == "yes" else verdict
    if open_ends:
        reasons.append(_text("the wall ends to the {}", "ściana kończy się: {}").format(joiner.join(open_ends)))
        verdict = "maybe" if verdict == "yes" else verdict
    if past is not None:
        hung, message = past
        if hung:
            reasons.insert(0, _text("it hung here before", "już tu wisiało"))
            verdict = "yes" if verdict != "no" else verdict
        else:
            reasons.insert(0, _text("the game refused this spot before", "gra wcześniej odrzuciła to miejsce")
                           + (": " + message.rstrip(".") if message else ""))
            verdict = "no"
    return verdict, reasons


def fit_parts():
    """Whether the chosen wall object will hang where the cursor faces."""
    label, height = selected_height()
    verdict, reasons = hang_report()
    if verdict == "no wall":
        return [_text(
            "Selected side has no wall. Turn with R or move to a tile beside a wall. Height {}, {:.1f} metres. ",
            "Po wybranej stronie nie ma ściany. Obracaj R albo przejdź obok ściany. Wysokość {}, {:.1f} metra. ",
        ).format(label, height)]
    opening = {
        "yes": _text("Should hang here", "Powinno tu zawisnąć"),
        "maybe": _text("Might not fit", "Może się nie zmieścić"),
        "no": _text("Will not hang here", "Tu nie zawiśnie"),
    }[verdict]
    parts = [opening + (": " + "; ".join(reasons) if reasons else "") + ". "]
    parts.append(_text("Height {}, {:.1f} metres. ", "Wysokość {}, {:.1f} metra. ").format(label, height))
    if not _hinted[0]:
        _hinted[0] = True
        parts.append(_text("Control Alt U and D change the height. Enter hangs it. ",
                           "Control Alt U i D zmieniają wysokość. Enter wiesza. "))
    return parts


def place(item):
    """Enter with a wall object chosen. True when the game's tool was asked."""
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_place as place_mod
    import tyjokr_a11y_tiles as tiles
    selected = selected_wall()
    if selected is None:
        direction = tiles.direction_name(int(grid._facing) % 4)
        place_mod._say_text(
            "There is no wall {}. Turn with R or move beside a wall.".format(direction),
            "Brak ściany w kierunku {}. Obracaj R albo przejdź obok ściany.".format(direction),
        )
        return False
    frame, side = selected
    try:
        point, height = _wall_anchor(frame, side)
    except Exception as ex:
        _log("could not calculate wall anchor: {!r}".format(ex))
        place_mod._say_text(
            "The wall anchor could not be calculated, so nothing was bought.",
            "Nie udało się obliczyć punktu na ścianie, więc nic nie kupiono.",
        )
        return False
    _log("placing product {} on side {} at height {:.1f}".format(item["id"], side, height))
    return hang_with_game_tool(frame, side, item, point, height)


def column_here(frame):
    """A column (the game's Build_Column tag) on the cursor tile."""
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_scanner as scanner
    import tyjokr_a11y_tiles as tiles
    try:
        for obj in tiles.objects_on(frame, grid._tile[0], grid._tile[1], grid._level):
            if any("column" in name.lower() for name in scanner._tag_names(obj)):
                return True
    except Exception as ex:
        _log("column check failed: {!r}".format(ex))
    return False


def hang_with_game_tool(frame, side, item, point, height):
    """Let EA's own Build tool hang it (Leo's choice, 2026-10-16): exact
    placement at a computed point failed MustBeAgainstWall live for every
    distance, height and facing tried. As TS4 Access Plus places doors and
    windows: the catalog item goes back into the game's hand, the camera
    faces the wall from inside the cursor's room, and a real click on the
    wall at the chosen height places it; the game snaps it, checks it and
    charges for it. Success is judged by the money spent."""
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_place as place_mod
    import tyjokr_a11y_tiles as tiles
    import tyjokr_a11y_plus_build as plus
    if plus._cat.get("chosen") is None:
        place_mod._say_text(
            "Choose it with Control Alt O first, so the game's tool can hold it. Nothing was bought.",
            "Najpierw wybierz to przez Control Alt O, aby narzędzie gry mogło to trzymać. Nic nie kupiono.",
        )
        return False
    # Live 2026-10-17: every refused try was on or beside a column tile; the
    # click then lands on the column or a wall end. Say so instead of trying.
    if column_here(frame):
        place_mod._say_text(
            "A column stands here, in front of the wall or at its end. Move along the wall to a plain stretch, then press Enter.",
            "Stoi tu kolumna, przed ścianą lub na jej końcu. Przejdź wzdłuż ściany na wolny odcinek i naciśnij Enter.",
        )
        return False
    center = tiles.position(frame, grid._tile[0], grid._tile[1], grid._level)
    dx, dz = float(center.x) - float(point.x), float(center.z) - float(point.z)
    length = (dx * dx + dz * dz) ** 0.5 or 1.0
    dx, dz = dx / length, dz / length
    # A hair inside the room, so the click lands on this side of the wall.
    target = (float(point.x) + dx * 0.05, float(point.z) + dz * 0.05)
    name = item.get("name") or "it"
    direction = tiles.direction_name(side)
    place_mod._say_text("Hanging {} on the {} wall. Please wait.".format(name, direction),
                        "Wieszanie {} na ścianie {}. Proszę czekać.".format(name, direction))
    _log("game tool: product {} side {} height {:.1f} at ({:.2f}, {:.2f})".format(
        item["id"], side, height, target[0], target[1]))

    def restore():
        plus._send_ui("A11y|plus|wallsrestore")

    def act(screen):
        try:
            plus._reselect()
            # _reselect picks by list position; a list browsed since then could
            # hold another item there. Click only when the game holds this one.
            held = str(plus._product.get("name") or "").strip().lower()
            if held != str(name).strip().lower():
                _log("game tool: holding {!r}, not {!r}; no click".format(held, name))
                plus.core.post(place_mod._say_text,
                               "The game is holding something else. Choose {} again with Control Alt O.".format(name),
                               "Gra trzyma coś innego. Wybierz {} ponownie przez Control Alt O.".format(name))
                return
            _attempt[0] = _attempt[0] % 3 + 1
            if settings.get("logging", False):
                # Diagnostics (2026-11-12): the game keeps answering "Must be
                # placed on a wall". Hover first, so the shot shows the game's
                # preview where the click will land, then the result.
                import os
                base = os.path.join(os.path.dirname(speech.LOG_PATH), "TS4_Access_wallshot_{}".format(_attempt[0]))
                spot = plus._to_screen(*screen[0])
                plus.move_to(*spot)
                time.sleep(0.6)
                plus.screenshot(base + "_before.bmp", mark=spot)
            plus.click(screen[0])
            time.sleep(1.0)
            if settings.get("logging", False):
                plus.screenshot(base + "_after.bmp", mark=spot)
        finally:
            plus.core.post(restore)

    # Live 2026-10-16: with walls down or cut away the click passed over the
    # drawn wall ("Must be placed on a wall"). Walls up first; the player's
    # view comes back after the click, or after 15 seconds if none happens.
    plus._send_ui("A11y|plus|wallsup")
    fallback = threading.Timer(15.0, lambda: plus.core.post(restore))
    fallback.daemon = True
    fallback.start()
    key = _spot_key(side)
    before, started = plus.funds(), time.monotonic()
    speak_result = plus.cost_check("Hung {}".format(name),
                                   "It was not hung. Something may be in the way on that wall, or the wall is too short.")

    def verify():
        # Remember the game's answer for this spot, so the cursor can say it
        # next time ("the game refused this spot before").
        after = plus.funds()
        if before is not None and after is not None and after != before:
            remember(key, True)
        else:
            error = plus._last_error["text"] if plus._last_error["at"] > started else ""
            remember(key, False, error)
        speak_result()

    # Live 2026-11-12 (screenshots): the click is the screen centre, where the
    # camera looks. Looking at the floor by the wall missed it from outside
    # (the porch hid the wall base), so look at the wall at the chosen height.
    plus.run_job([target], grid._level, act, "wall decoration", height=height, view=(dx, dz),
                 verify=verify, focus_height=height)
    return True
