"""Optional lot-planning descriptions and persistent whole-building labels."""
import json
import os
import time

import tyjokr_a11y_speech as speech

_enabled = False
_cache_at = 0.0
_cache = None
_labels = None

def _log(text):
    try: speech.log_line("lot grid: " + text)
    except Exception: pass

def _label_path():
    return os.path.join(os.path.dirname(speech.LOG_PATH), "TS4_Access_BuildingLabels.json")

def _load_labels():
    global _labels
    if _labels is not None: return
    _labels = {}
    try:
        with open(_label_path(), "r", encoding="utf-8") as stream:
            data=json.load(stream)
        if isinstance(data,dict): _labels={str(k):str(v)[:60] for k,v in data.items() if str(v).strip()}
    except FileNotFoundError: pass
    except Exception as ex: _log("label load failed: {!r}".format(ex))

def _save_labels():
    path=_label_path(); temporary=path+".tmp"
    try:
        with open(temporary,"w",encoding="utf-8") as stream: json.dump(_labels,stream,ensure_ascii=False,indent=2,sort_keys=True)
        os.replace(temporary,path); return True
    except Exception as ex:
        _log("label save failed: {!r}".format(ex)); return False

def _slot_zone():
    try:
        import services
        slot=int(services.get_persistence_service().get_save_slot_proto_buff().slot_id)
        return slot,int(services.current_zone_id())
    except Exception: return 0,0

def _cells(room, frame):
    out=set()
    for x,z in room.tiles:
        e,n=frame.local(x,z); out.add((int(e),int(n)))
    return out

def _touches(a,b):
    if a["level"]==b["level"]:
        if a["cells"].intersection(b["cells"]): return True
        return any((e+de,n+dn) in b["cells"] for e,n in a["cells"] for de,dn in ((1,0),(-1,0),(0,1),(0,-1)))
    return abs(a["level"]-b["level"])==1 and bool(a["cells"].intersection(b["cells"]))

def _object_kind(obj):
    try:
        import tyjokr_a11y_plus_rooms as rooms
        words=" ".join(rooms.tag_names(obj)).lower()+" "+type(obj).__name__.lower()
        if any(w in words for w in ("plant","flower","shrub","tree","garden")): return "landscaping"
        if "window" in words: return "window"
        if "door" in words: return "door"
    except Exception: pass
    return "object"

def _snapshot(refresh=False):
    global _cache_at,_cache
    now=time.monotonic()
    if _cache is not None and not refresh and now-_cache_at<3.0: return _cache
    import services
    import tyjokr_a11y_plus_build as build
    import tyjokr_a11y_plus_rooms as rooms
    frame=build.frame(); records=[]
    for room in rooms.scan_rooms():
        records.append({"room":room,"level":int(room.level),"rid":int(room.rid),"cells":_cells(room,frame)})
    remaining=set(range(len(records))); groups=[]
    while remaining:
        todo=[remaining.pop()]; indexes=set()
        while todo:
            i=todo.pop(); indexes.add(i)
            linked=[j for j in list(remaining) if _touches(records[i],records[j])]
            for j in linked: remaining.remove(j); todo.append(j)
        groups.append([records[i] for i in indexes])
    groups.sort(key=lambda group:sum(len(r["cells"]) for r in group),reverse=True)
    buildings=[]; by_room={}
    for number,group in enumerate(groups,1):
        allcells=set().union(*(r["cells"] for r in group)); es=[p[0] for p in allcells]; ns=[p[1] for p in allcells]
        levels=sorted(set(r["level"] for r in group)); box=(min(es),min(ns),max(es)+1,max(ns)+1)
        signature="{}:{}:{}:{}:{}:{}:{}:{}".format(*_slot_zone(),box[0],box[1],box[2],box[3],min(levels),max(levels))
        building={"number":number,"rooms":group,"cells":allcells,"box":box,"levels":levels,"signature":signature,"doors":set(),"windows":set()}
        buildings.append(building)
        for r in group: by_room[(r["rid"],r["level"])]=building
    for obj in services.object_manager().values():
        try:
            if obj.is_sim or obj.is_in_inventory(): continue
            e,n=frame.local(obj.position.x,obj.position.z); level=int(obj.level); kind=_object_kind(obj)
            for b in buildings:
                x1,z1,x2,z2=b["box"]
                if level in b["levels"] and x1-1<=e<=x2+1 and z1-1<=n<=z2+1 and kind in ("door","window"):
                    b[kind+"s"].add(int(obj.id)); break
        except Exception: pass
    _load_labels()
    for b in buildings:
        custom=_labels.get(b["signature"])
        b["name"]=custom or ("Main building" if b["number"]==1 else "Unlabelled building {}".format(b["number"]-1))
    _cache={"frame":frame,"buildings":buildings,"by_room":by_room}; _cache_at=now
    _log("snapshot buildings={}".format([(b['name'],b['box'],b['levels'],len(b['rooms']),len(b['doors']),len(b['windows'])) for b in buildings]))
    return _cache

def _building_at(i,j,level,snap=None):
    import tyjokr_a11y_tiles as tiles
    snap=snap or _snapshot(); rid=tiles.room(snap["frame"],i,j,level)
    try: return snap["by_room"].get((int(rid),int(level)))
    except Exception: return None

def _describe_tile(i,j,level):
    import tyjokr_a11y_tiles as tiles
    snap=_snapshot(); frame=snap["frame"]; building=_building_at(i,j,level,snap)
    if building:
        rec=next((r for r in building["rooms"] if r["level"]==int(level) and (i,j) in r["cells"]),None)
        return "{}, {}.".format(building["name"],rec["room"].name if rec else "room")
    facts=tiles.ground(frame,i,j,level); objects=tiles.objects_on(frame,i,j,level)
    if facts.get("pool"): return "Pool."
    if objects:
        landscaping=sum(1 for obj in objects if _object_kind(obj)=="landscaping")
        return "Landscaping, {} plant object{}; not clear for building.".format(landscaping,"" if landscaping==1 else "s") if landscaping else "Occupied outdoor tile, {} object{}; not clear for building.".format(len(objects),"" if len(objects)==1 else "s")
    if facts.get("floor") and facts.get("outside"): return "Exterior flooring, possible patio, porch, deck or path."
    if facts.get("outside"): return "Open outdoor ground; apparently clear, but construction still requires game validation."
    return "Unclassified tile."

def room_parts(frame):
    parts,facts=_original_room_parts(frame)
    if _enabled:
        try:
            import tyjokr_a11y_grid as grid
            parts=list(parts)+[_describe_tile(grid._tile[0],grid._tile[1],grid._level)+" "]
        except Exception as ex: _log("tile announcement failed: {!r}".format(ex))
    return parts,facts

def open_lot_grid():
    global _enabled
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_plus_build as build
    import tyjokr_a11y_plus_core as core
    if not build.in_build_mode(): core.speak("Enter Build mode first."); return
    _enabled=True; _snapshot(refresh=True)
    if not grid.build_cursor() and not grid.enter(): return
    core.speak("Lot planning grid on. Arrow through the lot. Each tile announces buildings, rooms, pools, exterior flooring, landscaping, occupied ground or apparently clear outdoor ground. Escape leaves the ordinary grid; use the Build helper to turn planning descriptions off.")
    grid.describe_build()

def close_lot_grid():
    global _enabled
    import tyjokr_a11y_plus_core as core
    _enabled=False; core.speak("Lot planning descriptions off. The ordinary Build grid remains unchanged.")

def label_current_building():
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_plus_core as core
    if not grid.build_cursor(): core.speak("Turn on the Build grid and move into the building first."); return
    building=_building_at(grid._tile[0],grid._tile[1],grid._level,_snapshot(refresh=True))
    if not building: core.speak("The cursor is not inside a detected building."); return
    def got(text):
        global _cache
        value=" ".join((text or "").strip().split())[:60]; _load_labels()
        if value: _labels[building["signature"]]=value
        else: _labels.pop(building["signature"],None)
        if _save_labels():
            _cache=None; core.speak("Building labelled {}.".format(value) if value else "Building label cleared.")
        else: core.speak("The building label could not be saved.")
    core.ask_text("Building name","Type a custom name, or leave blank to clear it.",_labels.get(building["signature"],""),got)

def register_box_label(box,levels,name):
    global _cache
    snap=_snapshot(refresh=True); wanted=set(int(v) for v in levels)
    match=next((b for b in snap["buildings"] if b["box"]==tuple(box) and set(b["levels"])==wanted),None)
    if not match:
        _log("planned building label not assigned; box={} levels={} name={!r}".format(box,levels,name)); return False
    _load_labels(); _labels[match["signature"]]=" ".join(name.strip().split())[:60]
    ok=_save_labels(); _cache=None
    _log("planned building label {} signature={} name={!r}".format("saved" if ok else "failed",match["signature"],name)); return ok

def describe_buildings():
    import tyjokr_a11y_plus_core as core
    snap=_snapshot(refresh=True); rows=[]
    for b in snap["buildings"]:
        x1,n1,x2,n2=b["box"]
        rows.append("{}: footprint {} by {} metres, {} room{}, level{}, {} door{}, {} window{}.".format(b["name"],x2-x1,n2-n1,len(b["rooms"]),"" if len(b["rooms"])==1 else "s",",".join(str(v) for v in b["levels"]),len(b["doors"]),"" if len(b["doors"])==1 else "s",len(b["windows"]),"" if len(b["windows"])==1 else "s"))
    core.speak(" ".join(rows) if rows else "No enclosed buildings were detected.")

def _original_room_parts(frame):
    import tyjokr_a11y_grid as grid
    return grid._room_parts_base(frame)

