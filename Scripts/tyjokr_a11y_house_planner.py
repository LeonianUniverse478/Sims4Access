"""Configurable, conservative stacked-house plans for TS4 Access Plus."""
import math
import threading
import time

import tyjokr_a11y_speech as speech

_pending_stairs = []

def _client_size():
    """Game cursor coordinates already use client pixels, not DPI units."""
    import ctypes
    import tyjokr_a11y_plus_build as build
    class RECT(ctypes.Structure):
        _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long),
                    ("r", ctypes.c_long), ("b", ctypes.c_long)]
    u = build._user32()
    hwnd = u.GetForegroundWindow()
    rect = RECT()
    if not hwnd or not u.GetClientRect(hwnd, ctypes.byref(rect)):
        raise RuntimeError("game client rectangle unavailable")
    return float(rect.r - rect.l), float(rect.b - rect.t)

def _client_to_screen(x, y):
    import ctypes
    import tyjokr_a11y_plus_build as build
    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
    u = build._user32()
    hwnd = u.GetForegroundWindow()
    point = POINT(int(round(x + build.OFFSET[0])), int(round(y + build.OFFSET[1])))
    if not hwnd or not u.ClientToScreen(hwnd, ctypes.byref(point)):
        raise RuntimeError("game client-to-screen conversion failed")
    return point.x, point.y

def _room_overview(points, level, attempt):
    """Simulation thread: widen the view without moving the room bounds."""
    import camera, terrain, sims4.math
    xs, zs = [p[0] for p in points], [p[1] for p in points]
    cx = (min(xs) + max(xs)) / 2.0
    tz = max(zs) - 1.0
    span = max(max(xs) - min(xs), max(zs) - min(zs))
    y = terrain.get_terrain_height(cx, tz) + 3.0 * level
    up = (14.0 + span * 1.1) * (1.0 + 0.5 * attempt)
    camera.focus_on_object_from_position(
        obj_position=sims4.math.Vector3(cx, y, tz),
        camera_position=sims4.math.Vector3(cx, y + up, tz + up * 0.3))

def overview_point_and_act(points_world, level, action, describe, height=0.0, view=None, overview=False):
    import tyjokr_a11y_plus_build as build
    if not overview:
        return _original_point_and_act(points_world, level, action, describe,
                                      height=height, view=view, overview=False)
    points = tuple(points_world)
    if not points:
        return False
    build._hook_replies()
    try:
        for attempt in range(5):
            build.cursor_off()
            # Wait for the simulation-thread camera call before allowing its
            # animation to settle and asking the UI for fresh projections.
            build.on_main(_room_overview, points, level, attempt)
            time.sleep(1.8)
            projected = [build.project(x, z, level, height=height) for x, z in points]
            clear = all(p is not None and build._clear_of_panels(p) for p in projected)
            _log("room framing attempt={} level={} bounds={} screen={} stage={} clear={}".format(
                attempt + 1, level, points, projected, build._stage_size(), clear))
            if clear:
                build.cursor_off()
                action(projected)
                time.sleep(1.0)
                return True
        build.core.post(build.core.speak, "The room corners could not be framed clear of the interface. Construction stopped before drawing this room.")
        return False
    finally:
        build.park_mouse()

def _log(text):
    try: speech.log_line("house planner: " + text)
    except Exception: pass

def _limits():
    try:
        import build_buy
        return int(build_buy.get_lowest_level_allowed()), int(build_buy.get_highest_level_allowed())
    except Exception as ex:
        _log("floor limits unavailable: {!r}".format(ex))
        return -1, 3

def _clean_names(text, count, level, attic=False):
    names=[" ".join(v.strip().split())[:50] for v in (text or "").split(",") if v.strip()]
    defaults=("Attic room","Storage","Attic bedroom","Attic bathroom") if attic else (("Living room","Kitchen","Bedroom","Bathroom") if level == 0 else ("Bedroom","Bedroom","Study","Bathroom"))
    while len(names)<count: names.append(defaults[len(names)%len(defaults)])
    names=names[:count]
    seen={}
    for i,name in enumerate(names):
        seen[name]=seen.get(name,0)+1
        if names.count(name)>1: names[i]="{} {}".format(name,seen[name])
    return names

def _room(kind,name,uv,level):
    return {"kind":kind,"name":name,"uv":uv,"level":level}

def _build_plan(width,depth,levels,layout,names_by_level):
    import tyjokr_a11y_plus_house as house
    import tyjokr_a11y_plus_build as build
    p=house.Plan(); p.side=house.street_side(); p.width=width; p.depth=depth; p.floors=len([v for v in levels if v>=0])
    front=4; hall=2
    if depth < front+hall+3:
        p.problem="The footprint is too shallow for rooms, a hallway and verified straight stairs."
        return p
    for level in levels:
        names=names_by_level[level]
        if layout=="two":
            p.rooms += [_room("room",names[0],(0,0,width,front),level),
                        _room("hall","{} hallway".format("Basement" if level<0 else "Floor {}".format(level+1)),(0,front,width,front+hall),level),
                        _room("room",names[1],(0,front+hall,width,depth),level)]
        else:
            split=width//2
            p.rooms += [_room("room",names[0],(0,0,split,front),level),_room("room",names[1],(split,0,width,front),level),
                        _room("hall","{} hallway".format("Basement" if level<0 else "Floor {}".format(level+1)),(0,front,width,front+hall),level),
                        _room("room",names[2],(0,front+hall,split,depth),level),_room("room",names[3],(split,front+hall,width,depth),level)]
        rooms=[r for r in p.rooms if r["level"]==level]
        hallroom=[r for r in rooms if r["kind"]=="hall"][0]
        frontrooms=[r for r in rooms if r["uv"][1]==0]
        backrooms=[r for r in rooms if r["uv"][1]>front]
        for r in frontrooms:
            mid=(r["uv"][0]+r["uv"][2])//2
            p.doors.append({"what":"Door from {} to {}".format(r["name"],hallroom["name"]),"a":(mid,front-1),"b":(mid,front),"front":False,"level":level})
        for r in backrooms:
            mid=(r["uv"][0]+r["uv"][2])//2
            p.doors.append({"what":"Door from {} to {}".format(hallroom["name"],r["name"]),"a":(mid,front+hall-1),"b":(mid,front+hall),"front":False,"level":level})
    ground=[r for r in p.rooms if r["level"]==0 and r["uv"][1]==0][0]
    mid=(ground["uv"][0]+ground["uv"][2])//2
    p.doors.append({"what":"Front door into {}".format(ground["name"]),"a":(mid,0),"b":(mid,-1),"front":True,"level":0})
    frame=build.frame(); along=frame.width if p.side in ("north","south") else frame.depth
    if width>along-2 or depth>(frame.depth if p.side in ("north","south") else frame.width)-house.SETBACK-1:
        p.problem="That {} by {} house does not fit this lot with the required setbacks.".format(width,depth); return p
    house._map_plan(p,frame,along)
    transitions=[]
    for lower in levels[:-1]:
        upper=lower+1
        top=(width-2,front)
        transitions.append((house._tile_to_lot(p,frame,(along-width)//2,top),house._dir_to_lot(p,(1,0)),lower,upper))
    if transitions:
        p.stairs={"top_lot":transitions[0][0],"climb_lot":transitions[0][1]}
    p._a11y_transitions=transitions
    return p

def _place_stair_at(top,climb,level):
    import tyjokr_a11y_plus_house as house
    import tyjokr_a11y_plus_build as build
    pick=house._pick_stairs()
    if not pick: return "nocatalog"
    if not build.set_floor(level): return "nofloor"
    frame=build.frame(); want=(top[0]+0.5-(house.STAIR_LEN-0.5)*climb[0],top[1]+0.5-(house.STAIR_LEN-0.5)*climb[1])
    shift=[0.0,0.0]; turn=False
    for attempt in range(10):
        before=set(build.on_main(house._stair_ids) or [])
        build._cat["silent_select"]=True
        try: build.select_item(*pick)
        finally: build._cat["silent_select"]=False
        if turn: build.tap_scan(52); time.sleep(0.5); turn=False
        point=frame.world(top[0]+0.5+shift[0],top[1]+0.5+shift[1])
        def act(screen):
            build.move_to(*build._to_screen(*screen[0])); time.sleep(0.8); build.click(screen[0])
        if not build.point_and_act([point],level,act,"stacked stairs level {} attempt {}".format(level,attempt+1)): return "noscreen"
        time.sleep(0.5)
        new=[oid for oid in build.on_main(house._stair_ids) or [] if oid not in before]
        if not new:
            _log("stairs level {} attempt {} rejected: {}".format(level,attempt+1,build._last_error.get("text"))); turn=True; continue
        info=build.on_main(house._stair_info,new[0]); _log("stairs level {} placed {} wanted {} climb {}".format(level,info,want,climb))
        if info is None: continue
        e,n,got=info
        if got==tuple(climb) and abs(e-want[0])<0.3 and abs(n-want[1])<0.3: return True
        build.on_main(build.undo); time.sleep(1.5); turn=(got!=tuple(climb)); shift=[shift[0]-(e-want[0]),shift[1]-(n-want[1])]
    return "failed"

def _stacked_stairs(top,climb):
    global _pending_stairs
    if not _pending_stairs: return _original_stairs(top,climb)
    results=[]
    for stair_top,stair_climb,lower,upper in list(_pending_stairs):
        result=_place_stair_at(stair_top,stair_climb,lower); results.append(result)
        _log("transition {} to {} result {}".format(lower,upper,result))
        if result is not True: break
    _pending_stairs=[]
    return all(r is True for r in results)

def _build_with_followup(plan):
    result=_original_build(plan)
    complete=False
    try:
        import tyjokr_a11y_plus_rooms as rooms
        import tyjokr_a11y_plus_build as build
        actual={(build._room_box(r),int(r.level)) for r in rooms.scan_rooms()}
        complete=all((r["box"],int(r.get("level",0))) in actual for r in plan.rooms)
        _log("post-build completeness {} actual={} wanted={}".format(complete,actual,[(r['box'],r.get('level',0)) for r in plan.rooms]))
    except Exception as ex:_log("post-build completeness failed: {!r}".format(ex))
    if getattr(plan,"_a11y_roof_prompt",False) and complete:
        try:
            import tyjokr_a11y_plus_core as core
            import tyjokr_a11y_roof_tools as roofs
            core.post(core.speak,"The stacked-house build has finished. Choose the roof shape and overhang next.")
            core.post(roofs.roof_builder)
        except Exception as ex:_log("roof follow-up failed: {!r}".format(ex))
    return result

def _review(plan, description):
    import tyjokr_a11y_plus_core as core
    import tyjokr_a11y_plus_house as house
    import tyjokr_a11y_plus_build as build
    if plan.problem: core.speak(plan.problem); return
    estimate=house.wall_meters(plan)*house.WALL_PRICE+len(plan.doors)*100+len(plan._a11y_transitions)*house.STAIR_PRICE
    rows=[("Build it","Every room, door and stair is checked; construction stops on the first failed room.",True),("Cancel",None,False)]
    def chosen(go):
        global _pending_stairs
        if not go:return
        _pending_stairs=list(plan._a11y_transitions)
        _log("approved plan levels={} size={}x{} rooms={} stairs={}".format(sorted(set(r['level'] for r in plan.rooms)),plan.width,plan.depth,[(r['level'],r['name'],r['box']) for r in plan.rooms],_pending_stairs))
        house.start_build(plan)
    core.choose("Configurable stacked house",description+" Estimated structural cost {:,}; household funds {:,}.".format(estimate,build.funds() or 0),rows,chosen,tag="build")

def open_planner():
    import tyjokr_a11y_plus_core as core
    import tyjokr_a11y_plus_build as build
    if not build.in_build_mode(): core.speak("Enter Build mode first."); return
    low,high=_limits(); max_stories=max(1,high+1)
    floor_rows=[("{} above-ground stor{}".format(n,"y" if n==1 else "ies"),None,n) for n in range(1,max_stories+1)]
    def floors_chosen(stories):
        basement_rows=[("No basement",None,False)]
        if low<0: basement_rows.append(("One basement level","Experimental negative-level room and stair placement; every step is logged and verified.",True))
        def basement_chosen(basement):
            sizes=[("Compact square","10 by 10 metres.",(10,10)),("Standard rectangle","10 by 11 metres.",(10,11)),("Large rectangle","12 by 14 metres.",(12,14))]
            def size_chosen(size):
                layouts=[("Two rooms per floor","One front room, hallway, one back room.","two"),("Four rooms per floor","Two front rooms, hallway, two back rooms.","four")]
                def layout_chosen(layout):
                    levels=list(range(-1 if basement else 0,stories)); count=2 if layout=="two" else 4; names={}
                    def ask(index):
                        if index>=len(levels):
                            plan=_build_plan(size[0],size[1],levels,layout,names); plan._a11y_roof_prompt=True
                            desc="{} by {} metre {} house; levels {}; {} rooms plus a hallway per level; straight aligned stairs.".format(size[0],size[1],"square" if size[0]==size[1] else "rectangular",", ".join(str(v) for v in levels),count)
                            _review(plan,desc); return
                        level=levels[index]; where="basement" if level<0 else "floor {}".format(level+1)
                        order="front, back" if count==2 else "front west, front east, back west, back east"
                        is_attic=attic and level==max(levels)
                        core.ask_text("Rooms on {}".format(where),"Type {} room names separated by commas, in this order: {}.{}".format(count,order," Leave blank for attic and storage defaults." if is_attic else ""),"",lambda text:(names.__setitem__(level,_clean_names(text,count,level,is_attic)),ask(index+1)))
                    attic_rows=[("Normal top floor",None,False),("Attic-style top floor","A full-height normal story with attic and storage defaults, followed by the roof chooser.",True)]
                    def attic_chosen(value):
                        nonlocal attic
                        attic=value; ask(0)
                    attic=False
                    core.choose("Top-floor use","This does not create unsafe sloped rooms; it changes the intended room naming and roof follow-up.",attic_rows,attic_chosen,tag="build")
                core.choose("Room layout","The same proven rectangular partition pattern is used on every level.",layouts,layout_chosen,tag="build")
            core.choose("House footprint","Every level uses exactly this perimeter.",sizes,size_chosen,tag="build")
        core.choose("Basement","A basement counts as level minus one and receives the same footprint.",basement_rows,basement_chosen,tag="build")
    core.choose("Number of stories","The game currently reports support through floor {}. Choose an above-ground count.".format(high),floor_rows,floors_chosen,tag="build")

def shaped_stair_diagnostics():
    import tyjokr_a11y_plus_core as core
    import tyjokr_a11y_plus_build as build
    def work():
        items=build.fetch_catalog(14,"","none") or []
        _log("stair catalog discovery {}".format([(str(n),p,c) for n,p,c in items]))
        core.post(core.speak,"Logged {} stair catalog entries and swatch counts. No shaped, flared, L, U or spiral stair was placed.".format(len(items)))
    threading.Thread(target=work,name="a11y_stair_discovery",daemon=True).start()

def _original_stairs(top, climb):
    import tyjokr_a11y_plus_house as house
    return house._place_stairs_worker_base(top, climb)


def _original_build(plan):
    import tyjokr_a11y_plus_house as house
    return house._build_base(plan)


def _original_point_and_act(points_world, level, action, describe, height=0.0, view=None, overview=False):
    import tyjokr_a11y_plus_build as build
    return build._point_and_act_base(points_world, level, action, describe, height=height, view=view, overview=overview)

