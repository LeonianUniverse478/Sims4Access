"""Target layers on the Build cursor: ground, six wall heights and ceiling.
Contributed by DaRainbowGirlXX (2026-10-16), merged into TS4 Access
2026-11-12.

Ctrl+Alt+U and Ctrl+Alt+D change the layer. With layer focus on (the
default), number 1 focuses the objects on that layer one by one, number 4
names the layer of each nearby object, Delete sells a focused object, and a
wall object is only placed while a wall height is the target. With layer
focus off, the two keys only change the wall height for a wall object.
"""

import tyjokr_a11y_speech as speech


SETTING_KEY = "surface_layer_focus"
_mode = 3          # 0 ground, 1-6 the wall heights, 7 ceiling
_wall_index = 2    # the last wall height chosen (middle)
_focus = {"obj_id": None, "tile": None, "level": None, "mode": None, "index": -1}


def enabled():
    import tyjokr_a11y_settings as settings
    return bool(settings.get(SETTING_KEY, True))


def _log(message):
    speech.log_line("layers: " + message)


def _text(en, pl):
    import tyjokr_a11y_grid as grid
    return grid._text(en, pl)


def wall_height():
    """(label, metres) of the chosen wall height."""
    import tyjokr_a11y_wall as wall
    return wall.HEIGHTS[_wall_index]


def _mode_info():
    if _mode == 0:
        return "ground", _text("ground", "podłoga"), None
    if _mode == 7:
        return "ceiling", _text("ceiling", "sufit"), None
    label, height = wall_height()
    return "wall", _text("wall {}", "ściana {}").format(label), height


def wall_refusal():
    """True (and spoken) when a wall object would be placed while the target
    layer is not a wall height."""
    if not enabled() or _mode_info()[0] == "wall":
        return False
    import tyjokr_a11y_place as place
    place._say_text(
        "Select a wall-height target with Control Alt U or Control Alt D before placing this wall object.",
        "Przed umieszczeniem obiektu ściennego wybierz wysokość ściany przez Control Alt U lub Control Alt D.",
    )
    return True


def _definition_id(obj):
    try:
        return int(obj.definition.id)
    except Exception:
        try:
            return int(obj.definition_id)
        except Exception:
            return None


def _kind(obj):
    try:
        import tyjokr_a11y_place as place
        need = place.requirement(_definition_id(obj))
    except Exception:
        need = None
    if need == "ceiling":
        return "ceiling"
    if need in ("wall", "fence"):
        return "wall"
    return "ground"


def _floor_y(frame, i, j, level):
    try:
        import tyjokr_a11y_tiles as tiles
        return float(tiles.position(frame, i, j, level).y)
    except Exception:
        return None


def _height(obj, floor_y):
    if floor_y is None:
        return None
    try:
        return max(0.0, float(obj.position.y) - floor_y)
    except Exception:
        return None


def _label(obj, frame=None, i=None, j=None, level=None):
    kind = _kind(obj)
    if kind == "ceiling":
        return _text("ceiling", "sufit")
    if kind == "wall":
        value = _height(obj, _floor_y(frame, i, j, level)) if frame is not None else None
        if value is not None:
            return _text("wall, {:.1f} metres", "ściana, {:.1f} metra").format(value)
        return _text("wall", "ściana")
    return _text("ground", "podłoga")


def _matches(obj, frame, i, j, level):
    kind, _label_text, selected_height = _mode_info()
    if _kind(obj) != kind:
        return False
    if kind != "wall":
        return True
    value = _height(obj, _floor_y(frame, i, j, level))
    # Wall heights are 0.5 m apart. A quarter-metre window avoids silently
    # selecting an object that belongs to a neighboring height.
    return value is not None and abs(value - selected_height) <= 0.26


def _objects_here(frame):
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_tiles as tiles
    i, j = grid._tile
    return [obj for obj in tiles.objects_on(frame, i, j, grid._level) if not getattr(obj, "is_sim", False)]


def _name_parts(obj):
    import tyjokr_a11y_grid as grid
    value = grid._name(obj)
    return list(value) if isinstance(value, list) else [value]


def clear_focus():
    _focus.update({"obj_id": None, "tile": None, "level": None, "mode": None, "index": -1})


def focus_detail(frame):
    """Number 1: focus the next object on the target layer, then list the tile."""
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_scanner as scanner
    objects = _objects_here(frame)
    i, j = grid._tile
    matches = [obj for obj in objects if _matches(obj, frame, i, j, grid._level)]
    matches.sort(key=lambda obj: int(getattr(obj, "id", 0)))
    context = (grid._tile, grid._level, _mode)
    same = (_focus["tile"], _focus["level"], _focus["mode"]) == context
    index = ((_focus["index"] + 1) % len(matches)) if same and matches else 0
    if not matches:
        clear_focus()
        parts = [_text("Nothing at the selected {} layer. ", "Brak obiektów na wybranej warstwie {}. ").format(_mode_info()[1])]
        if objects:
            parts.append(_text("Objects here: ", "Obiekty tutaj: "))
            parts.extend(grid._object_parts(frame, objects))
        else:
            parts.append(_text("Nothing here.", "Nic tu nie ma."))
        scanner._speak_parts(parts)
        return True
    obj = matches[index]
    _focus.update({"obj_id": obj.id, "tile": grid._tile, "level": grid._level, "mode": _mode, "index": index})
    parts = [_text("Focused: ", "Wybrano: ")]
    parts.extend(_name_parts(obj))
    parts.extend([", ", _label(obj, frame, i, j, grid._level), ". "])
    if len(matches) > 1:
        parts.append(_text("Object {} of {}; press 1 again for the next. ",
                           "Obiekt {} z {}; naciśnij ponownie 1, aby przejść dalej. ").format(index + 1, len(matches)))
    # Number 1 still lists everything on the tile, with contents and free spots.
    parts.append(_text("Objects here: ", "Obiekty tutaj: "))
    parts.extend(grid._object_parts(frame, objects))
    scanner._speak_parts(parts)
    return True


def nearby_detail(frame):
    """Number 4: nearby objects with the layer each one is on."""
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_scanner as scanner
    import tyjokr_a11y_tiles as tiles
    i, j = grid._tile
    nearby = []
    for di in range(-tiles.NEARBY_RADIUS, tiles.NEARBY_RADIUS + 1):
        for dj in range(-tiles.NEARBY_RADIUS, tiles.NEARBY_RADIUS + 1):
            if (di, dj) != (0, 0) and not frame.inside(i + di, j + dj):
                continue
            try:
                for obj in tiles.objects_on(frame, i + di, j + dj, grid._level):
                    nearby.append((di * di + dj * dj, di, dj, obj))
            except Exception:
                continue
    parts, seen, count = [], set(), 0
    for _distance, di, dj, obj in sorted(nearby, key=lambda item: item[0]):
        if obj.id in seen:
            continue
        seen.add(obj.id)
        parts.extend(_name_parts(obj))
        parts.extend([", ", _label(obj, frame, i + di, j + dj, grid._level), ", ", tiles.relative(di, dj), ". "])
        count += 1
        if count >= 8:
            break
    if not count:
        parts = [_text("Nothing within {} tiles.", "Nic w promieniu {} pól.").format(tiles.NEARBY_RADIUS)]
    scanner._speak_parts(parts)
    return True


def focused_target():
    """The object number 1 focused, while the cursor and layer are unchanged."""
    if not enabled() or _focus["obj_id"] is None:
        return None
    import services
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_tiles as tiles
    if _focus["tile"] != grid._tile or _focus["level"] != grid._level or _focus["mode"] != _mode:
        return None
    obj = services.object_manager().get(_focus["obj_id"])
    frame = tiles.frame()
    if obj is None or frame is None or all(candidate.id != obj.id for candidate in _objects_here(frame)):
        clear_focus()
        return None
    return obj


def change_layer(delta):
    """Ctrl+Alt+U (up) and Ctrl+Alt+D (down) with the Build cursor on."""
    global _mode, _wall_index
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_place as place
    import tyjokr_a11y_tiles as tiles
    import tyjokr_a11y_wall as wall
    step = 1 if delta > 0 else -1
    if not enabled():
        item = place.product()
        if item is None or place.requirement(item["id"]) != "wall":
            place._say_text("Choose a wall object first; these keys set its height.",
                            "Najpierw wybierz obiekt ścienny; te klawisze ustawiają jego wysokość.")
            return False
        _wall_index = max(0, min(len(wall.HEIGHTS) - 1, _wall_index + step))
        _mode = _wall_index + 1
        label, height = wall_height()
        direction = tiles.direction_name(int(grid._facing) % 4)
        available = wall.selected_wall() is not None
        place._say_text("Height {}, {:.1f} metres. {} {}.".format(label, height, "Wall" if available else "No wall", direction),
                        "Wysokość {}, {:.1f} metra. {} {}.".format(label, height, "Ściana" if available else "Brak ściany", direction))
        return True
    _mode = max(0, min(7, _mode + step))
    clear_focus()
    if 1 <= _mode <= 6:
        _wall_index = _mode - 1
    kind, label, height = _mode_info()
    if kind == "wall":
        place._say_text("Target layer: {}, {:.1f} metres. Press 1 to focus an object here.".format(label, height),
                        "Warstwa docelowa: {}, {:.1f} metra. Naciśnij 1, aby wybrać obiekt.".format(label, height))
    else:
        place._say_text("Target layer: {}. Press 1 to focus an object here.".format(label),
                        "Warstwa docelowa: {}. Naciśnij 1, aby wybrać obiekt.".format(label))
    return True
