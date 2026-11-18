"""Optional Build-grid orientation hints for dining and desk chairs.

This module only augments announcements. It never moves, rotates, validates,
buys, or otherwise changes an object or the baseline placement transaction.
"""

import tyjokr_a11y_speech as speech

_CHAIRS = {
    "buycatssdiningchair": ("dining chair", "buycatssdiningtable", "dining table"),
    "buycatssdeskchair": ("desk chair", "buycatssdesk", "desk"),
}


def _log(message):
    try:
        speech.log_line("chair alignment: " + message)
    except Exception:
        pass


def _text(en, pl):
    try:
        import tyjokr_a11y_grid as grid
        return grid._text(en, pl)
    except Exception:
        return en


def _enabled():
    try:
        import tyjokr_a11y_settings as settings
        return bool(settings.get("chair_alignment_hints", True))
    except Exception:
        return True


def _tag_names(definition):
    names = set()
    try:
        from tag import Tag
        for value in definition.get_tags() or ():
            try:
                names.add(str(Tag(value).name).lower().replace("_", ""))
            except Exception:
                continue
    except Exception:
        pass
    return names


def _selected_kind():
    try:
        import services
        import tyjokr_a11y_place as place
        item = place.product()
        if item is None:
            return None
        definition = services.definition_manager().get(item["id"], get_fallback_definition_id=False)
        tags = _tag_names(definition)
        for tag_name, details in _CHAIRS.items():
            if tag_name in tags:
                return item, details
    except Exception as ex:
        _log("selected chair classification failed: {!r}".format(ex))
    return None


def _object_has_tag(obj, wanted):
    try:
        return wanted in _tag_names(obj.definition)
    except Exception:
        return False


def _nearest_target(frame, i, j, level, wanted):
    import tyjokr_a11y_tiles as tiles
    candidates, seen = [], set()
    for di in range(-2, 3):
        for dj in range(-2, 3):
            ni, nj = i + di, j + dj
            if not frame.inside(ni, nj):
                continue
            for obj in tiles.objects_on(frame, ni, nj, level):
                obj_id = getattr(obj, "id", None)
                if obj_id in seen or not _object_has_tag(obj, wanted):
                    continue
                seen.add(obj_id)
                covered = tiles.covered_tiles(frame, obj, level) or [(ni, nj)]
                nearest = min(covered, key=lambda cell: (cell[0] - i) ** 2 + (cell[1] - j) ** 2)
                distance = (nearest[0] - i) ** 2 + (nearest[1] - j) ** 2
                candidates.append((distance, obj_id or 0, obj, nearest))
    return min(candidates, key=lambda row: (row[0], row[1])) if candidates else None


def _direction(i, j, target):
    di, dj = target[0] - i, target[1] - j
    if di == 0 and dj == 0:
        return None
    if abs(di) > abs(dj):
        return 1 if di > 0 else 3
    return 0 if dj > 0 else 2


def _hint_parts(frame):
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_tiles as tiles
    selected = _selected_kind()
    if selected is None:
        return []
    item, details = selected
    import tyjokr_a11y_chair_snap as chair_snap
    if chair_snap.has_target(item,frame):return []
    chair_label, target_tag, target_label = details
    i, j = grid._tile
    target = _nearest_target(frame, i, j, grid._level, target_tag)
    if target is None:
        _log("product {} {}: no {} within two tiles".format(item["id"], chair_label, target_label))
        return []
    _distance, obj_id, _obj, target_tile = target
    side = _direction(i, j, target_tile)
    if side is None:
        relation = "same tile"
        result = _text("Nearest {} is on this tile. ", "Najblizszy {} jest na tym polu. ").format(target_label)
    else:
        facing = int(grid._facing) % 4
        direction = tiles.direction_name(side)
        if facing == side:
            relation = "toward"
            result = _text("Nearest {} is {}; placement faces toward it. ", "Najblizszy {} jest {}; ustawienie jest skierowane do niego. ").format(target_label, direction)
        elif facing == (side + 2) % 4:
            relation = "away"
            result = _text("Nearest {} is {}; placement faces away from it. ", "Najblizszy {} jest {}; ustawienie jest skierowane od niego. ").format(target_label, direction)
        else:
            relation = "side-on"
            result = _text("Nearest {} is {}; placement is side-on to it. ", "Najblizszy {} jest {}; ustawienie jest bokiem do niego. ").format(target_label, direction)
    _log("product {} {} target {} tile {} facing {} relation {}".format(item["id"], chair_label, obj_id, target_tile, tiles.direction_name(int(grid._facing) % 4), relation))
    return [result]


def fit_parts(frame, with_facing=True, objects=None):
    parts = list(_original_fit_parts(frame, with_facing=with_facing, objects=objects))
    if _enabled():
        try:
            parts.extend(_hint_parts(frame))
        except Exception as ex:
            _log("announcement failed: {!r}".format(ex))
    return parts


def _original_fit_parts(frame, with_facing=True, objects=None):
    import tyjokr_a11y_grid as grid
    return grid._fit_parts_base(frame, with_facing=with_facing, objects=objects)


