"""Conservative detached one-floor structure planner for the Build grid."""
import threading

import tyjokr_a11y_speech as speech


def _log(text):
    try: speech.log_line("detached builder: "+text)
    except Exception: pass

def _clean(text,default):
    value=" ".join((text or "").strip().split())[:60]
    return value or default

def _object_summary(objects):
    try:
        import tyjokr_a11y_plus_rooms as rooms
        tags=[]
        for obj in objects: tags.extend(rooms.tag_names(obj))
        words=" ".join(tags).lower()
        if any(v in words for v in ("plant","flower","shrub","tree","garden")): return "landscaping"
    except Exception: pass
    return "object"

def _clearance(box):
    import tyjokr_a11y_tiles as tiles
    frame=tiles.frame(); problems=[]
    x1,n1,x2,n2=box
    for i in range(x1-1,x2+1):
        for j in range(n1-1,n2+1):
            if not frame.inside(i,j): problems.append("lot edge at {},{}".format(i,j)); continue
            facts=tiles.ground(frame,i,j,0); objects=tiles.objects_on(frame,i,j,0); rid=tiles.room(frame,i,j,0)
            inside=x1<=i<x2 and n1<=j<n2
            if facts.get("pool"): problems.append("pool at {},{}".format(i,j))
            if rid is not None: problems.append("room at {},{}".format(i,j))
            if objects: problems.append("{} at {},{}".format(_object_summary(objects),i,j))
            if inside and facts.get("floor") and facts.get("outside"): problems.append("exterior flooring at {},{}".format(i,j))
    unique=[]
    for p in problems:
        if p not in unique: unique.append(p)
    _log("clearance box={} problems={}".format(box,unique))
    return unique

def _door(side,box):
    x1,n1,x2,n2=box
    if side=="north":
        x=(x1+x2-1)//2; return (x,n1),(x,n1-1)
    if side=="south":
        x=(x1+x2-1)//2; return (x,n2-1),(x,n2)
    if side=="west":
        n=(n1+n2-1)//2; return (x1,n),(x1-1,n)
    n=(n1+n2-1)//2; return (x2-1,n),(x2,n)

def _make_plan(box,layout,names,entrance,building_name,kind):
    import tyjokr_a11y_plus_house as house
    p=house.Plan(); x1,n1,x2,n2=box; p.width=x2-x1; p.depth=n2-n1; p.side="north"; p.floors=1
    if layout=="one": p.rooms=[{"kind":"room","name":names[0],"box":box,"level":0}]
    elif layout=="side":
        split=x1+(x2-x1)//2
        p.rooms=[{"kind":"room","name":names[0],"box":(x1,n1,split,n2),"level":0},{"kind":"room","name":names[1],"box":(split,n1,x2,n2),"level":0}]
        n=(n1+n2-1)//2; p.doors.append({"what":"Door between {} and {}".format(names[0],names[1]),"tile_a":(split-1,n),"tile_b":(split,n),"front":False,"level":0})
    else:
        split=n1+(n2-n1)//2
        p.rooms=[{"kind":"room","name":names[0],"box":(x1,n1,x2,split),"level":0},{"kind":"room","name":names[1],"box":(x1,split,x2,n2),"level":0}]
        x=(x1+x2-1)//2; p.doors.append({"what":"Door between {} and {}".format(names[0],names[1]),"tile_a":(x,split-1),"tile_b":(x,split),"front":False,"level":0})
    a,b=_door(entrance,box)
    p.doors.insert(0,{"what":"Exterior door into {}".format(names[0]),"tile_a":a,"tile_b":b,"front":True,"level":0})
    p._a11y_detached={"box":box,"levels":[0],"name":building_name,"kind":kind,"rooms":list(names)}
    return p

def _review(plan):
    import tyjokr_a11y_plus_core as core
    import tyjokr_a11y_plus_house as house
    import tyjokr_a11y_plus_build as build
    meta=plan._a11y_detached; problems=_clearance(meta["box"])
    if problems:
        sample="; ".join(problems[:5]); more=len(problems)-5
        core.speak("That footprint is not clear: {}{}. Move the Build-grid cursor to another north-west corner; nothing was changed.".format(sample,"; and {} more conflicts".format(more) if more>0 else "")); return
    estimate=house.wall_meters(plan)*house.WALL_PRICE+len(plan.doors)*100
    x1,n1,x2,n2=meta["box"]
    text="{}: {} by {} metres, {} room{}, north-west corner {} from west and {} from north, estimated structural cost {:,}. The surrounding one-tile clearance is clear in the current scan.".format(meta["name"],x2-x1,n2-n1,len(plan.rooms),"" if len(plan.rooms)==1 else "s",x1,n1,estimate)
    rows=[("Build it","The existing room and door workers verify every game action.",True),("Cancel",None,False)]
    def chosen(value):
        if value:
            _log("approved kind={} name={!r} box={} rooms={} doors={}".format(meta['kind'],meta['name'],meta['box'],[(r['name'],r['box']) for r in plan.rooms],[(d['what'],d['tile_a'],d['tile_b']) for d in plan.doors]))
            house.start_build(plan)
    core.choose("Detached structure plan",text,rows,chosen,tag="build")

def open_builder():
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_plus_build as build
    import tyjokr_a11y_plus_core as core
    if not build.in_build_mode(): core.speak("Enter Build mode first."); return
    if not grid.build_cursor(): core.speak("Turn on the Build grid and move to the intended north-west corner first."); return
    anchor=tuple(grid._tile)
    kinds=[("Storage shed","Small enclosed one-room building.",("shed",4,4,"Storage shed","Storage")),("Detached garage","Cosmetic enclosed garage; functional cars or garage doors are not assumed.",("garage",6,8,"Detached garage","Garage")),("Winter garden","Enclosed garden room. Walls and roof are built; add large windows afterward with the validated wall placement tools.",("winter garden",6,8,"Winter garden","Winter garden")),("Party house","One or two enclosed rooms for entertaining.",("party house",8,10,"Party house","Party room")),("Custom small building","Choose a conservative footprint and room layout.",("custom",None,None,"Detached building","Main room"))]
    def kind_chosen(value):
        kind,w,d,default_building,default_room=value
        sizes=[("4 by 4",None,(4,4)),("6 by 8",None,(6,8)),("8 by 10",None,(8,10))]
        def size_chosen(size):
            width,depth=size
            layouts=[("One room",None,"one"),("Two rooms, west and east",None,"side"),("Two rooms, north and south",None,"front")]
            def layout_chosen(layout):
                entrances=[("North entrance",None,"north"),("East entrance",None,"east"),("South entrance",None,"south"),("West entrance",None,"west")]
                def entrance_chosen(entrance):
                    def building_named(text):
                        building_name=_clean(text,default_building); count=1 if layout=="one" else 2
                        prompt="Type the room name." if count==1 else "Type two room names separated by a comma, in the selected positional order."
                        def rooms_named(raw):
                            values=[_clean(v,default_room if i==0 else "Side room") for i,v in enumerate((raw or "").split(",")) if v.strip()]
                            while len(values)<count: values.append(default_room if not values else "Side room")
                            box=(anchor[0],anchor[1],anchor[0]+width,anchor[1]+depth)
                            _review(_make_plan(box,layout,values[:count],entrance,building_name,kind))
                        core.ask_text("Room names",prompt,default_room,rooms_named)
                    core.ask_text("Building name","Type the custom name used by the lot grid.",default_building,building_named)
                core.choose("Entrance side","The exterior door is centred on this side.",entrances,entrance_chosen,tag="build")
            core.choose("Room layout","Rooms divide the selected footprint evenly.",layouts,layout_chosen,tag="build")
        if w is None: core.choose("Structure size","The current grid tile remains the north-west corner.",sizes,size_chosen,tag="build")
        else: size_chosen((w,d))
    core.choose("Detached structure","Current Build-grid tile {} from west and {} from north is the proposed north-west corner.".format(anchor[0],anchor[1]),kinds,kind_chosen,tag="build")

def _build_followup(plan):
    result=_original_build(plan); meta=getattr(plan,"_a11y_detached",None)
    if not meta: return result
    complete=False
    try:
        import tyjokr_a11y_plus_build as build
        import tyjokr_a11y_plus_rooms as rooms
        actual={(build._room_box(r),int(r.level)) for r in rooms.scan_rooms()}
        complete=all((tuple(r["box"]),int(r.get("level",0))) in actual for r in plan.rooms)
        _log("post-build complete={} actual={} wanted={}".format(complete,actual,[(r['box'],r['level']) for r in plan.rooms]))
    except Exception as ex: _log("post-build verification failed: {!r}".format(ex))
    if complete:
        try:
            import tyjokr_a11y_lot_grid as lot_grid
            lot_grid.register_box_label(meta["box"],meta["levels"],meta["name"])
        except Exception as ex: _log("building label follow-up failed: {!r}".format(ex))
        try:
            import tyjokr_a11y_plus_core as core
            import tyjokr_a11y_roof_tools as roofs
            core.post(core.speak,"The detached structure is complete. Choose its roof next. For a winter garden, place large windows afterward with the normal validated wall tools.")
            core.post(roofs.roof_builder_for_box,meta["box"],0,meta["rooms"])
        except Exception as ex: _log("roof follow-up failed: {!r}".format(ex))
    return result

def _original_build(plan):
    import tyjokr_a11y_house_planner as planner
    return planner._build_with_followup(plan)

