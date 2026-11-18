"""Additive nonvisual roof builder and geometry-based build describer."""
import math
import threading

import tyjokr_a11y_speech as speech

_plans = []

def _log(text):
    try: speech.log_line("roof tools: " + text)
    except Exception: pass

def _rooms():
    import tyjokr_a11y_plus_rooms as rooms
    return rooms.scan_rooms()

def _box(room):
    import tyjokr_a11y_plus_build as build
    return build._room_box(room)

def _room_cells(room):
    import tyjokr_a11y_plus_build as build
    frame = build.frame()
    return set((math.floor(e), math.floor(n))
               for e, n in (frame.local(x, z) for x, z in room.tiles))

def _shape(room):
    cells = _room_cells(room)
    x1, z1, x2, z2 = _box(room)
    width, depth = x2 - x1, z2 - z1
    if len(cells) == width * depth:
        if min(width, depth) <= 2 and max(width, depth) >= 4: return "straight"
        if abs(width - depth) <= 1: return "roughly square"
        return "rectangular"
    rows = set(sum(1 for x in range(x1, x2) if (x, z) in cells) for z in range(z1, z2))
    cols = set(sum(1 for z in range(z1, z2) if (x, z) in cells) for x in range(x1, x2))
    if len(rows) <= 2 and len(cols) <= 2: return "L-shaped"
    return "irregular"

def _cells_shape(cells):
    cells = set(cells)
    if not cells: return "empty"
    xs, zs = [p[0] for p in cells], [p[1] for p in cells]
    width, depth = max(xs)-min(xs)+1, max(zs)-min(zs)+1
    if len(cells) == width*depth:
        return "roughly square" if abs(width-depth) <= 1 else "rectangular"
    rows = set(sum(1 for x in range(min(xs), max(xs)+1) if (x,z) in cells) for z in range(min(zs), max(zs)+1))
    cols = set(sum(1 for z in range(min(zs), max(zs)+1) if (x,z) in cells) for x in range(min(xs), max(xs)+1))
    if len(rows) <= 2 and len(cols) <= 2: return "L-shaped"
    return "irregular"

def _position(box, width, depth):
    cx, cz = (box[0]+box[2])/2.0, (box[1]+box[3])/2.0
    ew = "west" if cx < width/3.0 else ("east" if cx > width*2/3.0 else "central")
    ns = "north" if cz < depth/3.0 else ("south" if cz > depth*2/3.0 else "central")
    if ew == "central" and ns == "central": return "near the center"
    return "in the {}{} part".format("" if ns == "central" else ns + " ", ew if ew != "central" else "central")

def _components(cells):
    remaining, out = set(cells), []
    while remaining:
        todo, component = [remaining.pop()], set()
        while todo:
            p = todo.pop(); component.add(p)
            for q in ((p[0]-1,p[1]),(p[0]+1,p[1]),(p[0],p[1]-1),(p[0],p[1]+1)):
                if q in remaining: remaining.remove(q); todo.append(q)
        out.append(component)
    return sorted(out, key=len, reverse=True)

def describe_lot():
    import services
    import tyjokr_a11y_plus_core as core
    import tyjokr_a11y_plus_build as build
    import tyjokr_a11y_tiles as tiles
    rooms, frame = _rooms(), build.frame()
    all_cells = set().union(*(_room_cells(r) for r in rooms)) if rooms else set()
    buildings = _components(all_cells)
    parts = ["Lot {} by {} metres.".format(frame.width, frame.depth)]
    for number, cells in enumerate(buildings, 1):
        xs, zs = [p[0] for p in cells], [p[1] for p in cells]
        box = (min(xs),min(zs),max(xs)+1,max(zs)+1)
        label = "Main building" if number == 1 else "Building {}".format(number)
        parts.append("{} {}, {}, footprint {} by {} metres.".format(label, _position(box,frame.width,frame.depth), _cells_shape(cells), box[2]-box[0], box[3]-box[1]))
    pool, exterior_floor = set(), set()
    for i in range(frame.width):
        for j in range(frame.depth):
            try: facts = tiles.ground(frame,i,j,0)
            except Exception: continue
            if facts.get("pool"): pool.add((i,j))
            if facts.get("outside") and facts.get("floor"): exterior_floor.add((i,j))
    if pool:
        for cells in _components(pool):
            xs,zs=[p[0] for p in cells],[p[1] for p in cells]; box=(min(xs),min(zs),max(xs)+1,max(zs)+1)
            parts.append("Pool {}, approximately {} by {} metres.".format(_position(box,frame.width,frame.depth),box[2]-box[0],box[3]-box[1]))
    if exterior_floor:
        for cells in _components(exterior_floor)[:4]:
            xs,zs=[p[0] for p in cells],[p[1] for p in cells]; box=(min(xs),min(zs),max(xs)+1,max(zs)+1)
            parts.append("Possible patio, porch, deck or path {}, {} square metres; exterior flooring alone cannot distinguish its purpose.".format(_position(box,frame.width,frame.depth),len(cells)))
    plants=[]
    for obj in services.object_manager().values():
        try:
            if obj.is_sim: continue
            tags=" ".join(__import__('tyjokr_a11y_plus_rooms').tag_names(obj)).lower()
            if any(w in tags for w in ("plant","flower","shrub","tree","garden")):
                plants.append(frame.local(obj.position.x,obj.position.z))
        except Exception: pass
    if plants:
        xs,zs=[p[0] for p in plants],[p[1] for p in plants]; box=(min(xs),min(zs),max(xs)+1,max(zs)+1)
        parts.append("Possible garden or landscaped plant cluster {}, {} detected plants.".format(_position(box,frame.width,frame.depth),len(plants)))
    if not buildings: parts.append("No enclosed building footprint detected.")
    core.speak(" ".join(parts))

def _side(room, obj):
    import tyjokr_a11y_plus_build as build
    x1, z1, x2, z2 = _box(room)
    try:
        x, z = build.frame().local(float(obj.position.x), float(obj.position.z))
    except Exception:
        x, z = float(obj.position.x), float(obj.position.z)
    values = ((abs(z-z1), "north"), (abs(x2-x), "east"), (abs(z2-z), "south"), (abs(x-x1), "west"))
    return min(values)[1]

def _kind(obj):
    try:
        import tyjokr_a11y_plus_rooms as rooms
        tags = rooms.tag_names(obj)
        for name, wanted, _weight in rooms.KINDS:
            if tags.intersection(wanted): return name.lower()
        joined = " ".join(tags).lower()
        for word in ("fireplace", "bed", "wardrobe", "dresser", "sofa", "toilet", "shower", "sink", "table", "desk"):
            if word in joined: return word
    except Exception: pass
    return None

def _doors(room, by_id, frame):
    import tyjokr_a11y_tiles as tiles
    found = set()
    own = _room_cells(room)
    for i, j in own:
        try: doors = tiles.doors(frame, i, j, room.level)
        except Exception: continue
        for side in doors:
            di, dj = tiles.STEPS[side]
            try: rid = tiles.room(frame, i + di, j + dj, room.level)
            except Exception: rid = None
            destination = by_id.get((rid, room.level), "outside")
            found.add((tiles.direction_name(side), destination))
    return sorted(found)

def _room_text(room, all_rooms, frame):
    x1, z1, x2, z2 = _box(room)
    by_id = {(r.rid, r.level): r.name for r in all_rooms}
    text = "{}, {}, {} by {} metres".format(room.name, _shape(room), x2-x1, z2-z1)
    doors = _doors(room, by_id, frame)
    if doors: text += ". Doors: " + "; ".join("{} wall to {}".format(side, dest) for side, dest in doors)
    major = []
    for obj in room.objects:
        kind = _kind(obj)
        if kind: major.append("{} on the {} side".format(kind, _side(room, obj)))
    if major: text += ". " + "; ".join(major[:12])
    return text + "."

def describe_build():
    import tyjokr_a11y_plus_core as core
    import tyjokr_a11y_plus_build as build
    rooms = _rooms()
    if not rooms:
        core.speak("No enclosed rooms were found on this lot.")
        return
    frame = build.frame()
    levels = sorted(set(r.level for r in rooms))
    boxes = [_box(r) for r in rooms]
    house = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
    summary = "{} floors, {} rooms. Overall enclosed footprint approximately {} by {} metres.".format(len(levels), len(rooms), house[2]-house[0], house[3]-house[1])
    rows = []
    for level in levels:
        floor_rooms = [r for r in rooms if r.level == level]
        rows.append(("Floor {}".format(level), "{} rooms: {}.".format(len(floor_rooms), ", ".join(r.name for r in floor_rooms)), floor_rooms))
    def floor_chosen(floor_rooms):
        rrows = [(r.name, _room_text(r, rooms, frame), r) for r in floor_rooms]
        core.choose("Rooms on floor {}".format(floor_rooms[0].level), "Choose a room for its geometry, doors and major furniture.", rrows, lambda r: core.speak(_room_text(r, rooms, frame)), tag="build")
    core.choose("Describe this build", summary, rows, floor_chosen, tag="build")

def _target_rows():
    rooms = _rooms()
    if not rooms: return [], []
    top = max(r.level for r in rooms)
    top_rooms = [r for r in rooms if r.level == top]
    boxes = [_box(r) for r in top_rooms]
    whole = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
    union = set().union(*(_room_cells(r) for r in top_rooms))
    safe_whole = _cells_shape(union) in ("rectangular","roughly square")
    rows = [("Whole top floor", "{} rooms, {} by {} metres; {}.".format(len(top_rooms), whole[2]-whole[0], whole[3]-whole[1], "safe rectangular footprint" if safe_whole else "non-rectangular and will be refused"), (whole, top, [r.name for r in top_rooms], safe_whole))]
    rows += [(r.name, "{}, {} by {} metres.".format(_shape(r), _box(r)[2]-_box(r)[0], _box(r)[3]-_box(r)[1]), (_box(r), r.level, [r.name], _shape(r) in ("rectangular","roughly square"))) for r in top_rooms]
    return rows, rooms

def roof_builder():
    import tyjokr_a11y_plus_core as core
    rows, rooms = _target_rows()
    if not rows:
        core.speak("Build at least one enclosed room first.")
        return
    def target_chosen(target):
        box, level, names, safe = target
        if not safe:
            _log("roof refused: non-rectangular target level {} rooms {} box {}".format(level,names,box))
            core.speak("This footprint is not rectangular or square. Automatic L and T shaped roofing is disabled until it has been tested. Nothing was placed.")
            return
        width, depth = box[2]-box[0], box[3]-box[1]
        kinds = [("Flat roof", "Uses the existing top-floor ceiling as the roof deck; no pitched roof piece is added.", "flat"),
                 ("Gabled roof", "Triangular-prism roof with a ridge along the longest side.", "gable"),
                 ("Hipped roof", "Slopes on four sides; a square can meet at a pyramid-like point.", "hip")]
        def kind_chosen(kind):
            if kind == "flat":
                _plans.append(("flat", box, level, tuple(names)))
                core.speak("Flat roof selected. The ceiling over {} is the roof deck, {} by {} metres. Add a floor pattern or roof trim from the catalog if wanted.".format(", ".join(names), width, depth))
                return
            overhangs = [("No overhang", "Roof edges follow the detected walls.", 0),
                         ("Half-metre overhang", "Extends half a metre on every side, where the lot boundary permits.", 0.5),
                         ("One metre overhang", "Extends one metre on every side, where the lot boundary permits.", 1)]
            def overhang_chosen(amount):
                import tyjokr_a11y_plus_build as build
                frame=build.frame(); expanded=(max(0,box[0]-amount),max(0,box[1]-amount),min(frame.width,box[2]+amount),min(frame.depth,box[3]+amount))
                _choose_roof_style(kind, expanded, level, names, amount)
            core.choose("Roof overhang", "Choose a conservative preset. The roof worker verifies the final handles.", overhangs, overhang_chosen, tag="build")
        core.choose("Roof shape", "Target {} by {} metres over {}.".format(width, depth, ", ".join(names)), kinds, kind_chosen, tag="build")
    core.choose("Accessible roof builder", "Choose what the roof covers.", rows, target_chosen, tag="build")

def roof_builder_for_box(box, level, names):
    """Open the normal conservative roof chooser for one verified footprint."""
    import tyjokr_a11y_plus_core as core
    box = tuple(box)
    names = list(names)
    width, depth = box[2]-box[0], box[3]-box[1]
    _log("targeted roof chooser level={} box={} rooms={}".format(level, box, names))
    kinds = [("Flat roof", "Uses the completed room ceiling as the roof deck.", "flat"),
             ("Gabled roof", "Triangular-prism roof with a ridge along the longest side.", "gable"),
             ("Hipped roof", "Slopes on four sides; a square may meet at a pyramid-like point.", "hip")]
    def kind_chosen(kind):
        if kind == "flat":
            _plans.append(("flat", box, level, tuple(names)))
            core.speak("Flat roof selected over {}, {} by {} metres.".format(", ".join(names), width, depth))
            return
        overhangs = [("No overhang", "Roof edges follow the detected walls.", 0),
                     ("Half-metre overhang", "Extends half a metre where the lot boundary permits.", 0.5),
                     ("One metre overhang", "Extends one metre where the lot boundary permits.", 1)]
        def overhang_chosen(amount):
            import tyjokr_a11y_plus_build as build
            frame=build.frame()
            expanded=(max(0,box[0]-amount),max(0,box[1]-amount),min(frame.width,box[2]+amount),min(frame.depth,box[3]+amount))
            _choose_roof_style(kind, expanded, level, names, amount)
        core.choose("Roof overhang", "Choose a conservative preset.", overhangs, overhang_chosen, tag="build")
    core.choose("Roof for detached structure", "Target {} by {} metres over {}.".format(width, depth, ", ".join(names)), kinds, kind_chosen, tag="build")

def _choose_roof_style(kind, box, level, names, overhang=0):
    import tyjokr_a11y_plus_core as core
    import tyjokr_a11y_plus_build as build
    import tyjokr_a11y_plus_draw as draw
    def work():
        items = build.fetch_catalog(4, "", "none")
        words = ("gable", "gabled") if kind == "gable" else ("hip", "hipped", "pyramid")
        matched = [it for it in items if any(w in str(it[0]).lower() for w in words)]
        choices = matched or items
        _log("roof catalog kind={} entries={}".format(kind, [(str(name),price,colors) for name,price,colors in choices]))
        rows = [(name, "Game roof style, {} color swatch{} reported; the update currently selects the default swatch. Placement will be verified after its handles are stretched.".format(colors, "" if colors == 1 else "es"), name) for name, _price, colors in choices]
        def chosen(name):
            if build._busy[0]:
                core.speak("Still working on the last build step.")
                return
            build._busy[0] = True
            draw._state["style"] = (4, "", name)
            _plans.append((kind, box, level, tuple(names), name))
            _log("roof request kind={} style={!r} level={} box={} overhang={} rooms={}".format(kind,name,level,box,overhang,names))
            core.speak("Placing {} over {}. Please wait and let go of Alt.".format(name, ", ".join(names)))
            threading.Thread(target=draw._draw_roof_box, args=(box, level), name="a11y_roof_builder", daemon=True).start()
        core.post(core.choose, "{} styles".format(kind.capitalize()), "{} matching styles.".format(len(rows)), rows, chosen, "build")
    threading.Thread(target=work, name="a11y_roof_catalog", daemon=True).start()

def describe_roof_level():
    import tyjokr_a11y_plus_core as core
    rooms = _rooms()
    if not rooms:
        core.speak("No roof-supporting rooms were found.")
        return
    top = max(r.level for r in rooms)
    below = [r for r in rooms if r.level == top]
    fireplaces = [(r, o) for r in below for o in r.objects if _kind(o) == "fireplace"]
    text = "Roof level above floor {}. It covers {}.".format(top, ", ".join(r.name for r in below))
    if _plans: text += " This session created {} roof plan{}.".format(len(_plans), "" if len(_plans)==1 else "s")
    if fireplaces: text += " {} fireplace{} below provide chimney alignment points.".format(len(fireplaces), "" if len(fireplaces)==1 else "s")
    core.speak(text)

def chimney_assistant():
    import tyjokr_a11y_plus_core as core
    fireplaces = [(r, o) for r in _rooms() for o in r.objects if _kind(o) == "fireplace"]
    if not fireplaces:
        core.speak("No fireplace was identified. Nothing will be placed.")
        return
    rows = []
    for room, obj in fireplaces:
        rows.append(("Fireplace in {}".format(room.name), "On the {} side; roof point directly above it.".format(_side(room, obj)), (room, obj)))
    def chosen(value):
        room, obj = value
        roof_level=max(r.level for r in _rooms())+1
        try:
            import tyjokr_a11y_plus_build as build
            east, north = build.frame().local(float(obj.position.x), float(obj.position.z))
        except Exception:
            east, north = float(obj.position.x), float(obj.position.z)
        try:
            import tyjokr_a11y_grid as grid
            if not grid.active(): grid.enter()
            moved=grid.focus_position(obj.position,roof_level)
        except Exception as ex:
            moved=False; _log("chimney cursor move failed: {!r}".format(ex))
        _log("chimney target fireplace={} room={!r} roof_level={} tile=({}, {}) moved={}".format(getattr(obj,'id','?'),room.name,roof_level,int(round(east)),int(round(north)),bool(moved)))
        core.speak("Chimney alignment point: directly above the fireplace on the {} side of {}, approximately {} metres from the west edge and {} metres from the north edge. {} Choose a chimney in the catalog, return to the grid, and press Enter yourself. The normal exact placement validator decides whether it can be bought.".format(_side(room, obj), room.name, int(round(east)), int(round(north)), "The Build cursor is positioned there on roof level {}.".format(roof_level) if moved else "The cursor could not be moved, so nothing was changed."))
    core.choose("Chimney assistant", "Choose a fireplace. This assistant will not force an unverified object onto the roof.", rows, chosen, tag="build")

