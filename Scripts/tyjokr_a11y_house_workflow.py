"""Unified house planning and fresh Build-mode room geometry."""
import copy
import threading

_build = None
_core = None
_house = None
_planner = None
_installed = False
_main_ident = None
ROLES = (('Bedroom','bedroom'),("Children's bedroom",'bedroom'),('Nursery','bedroom'),
         ('Bathroom','bathroom'),('Kitchen','kitchen'),('Living room','living'),
         ('Dining room','dining'),('Study','study'),('Storage','room'),('Hobby room','room'))


def _log(kind, **data):
    import json
    import tyjokr_a11y_speech as speech
    speech.log_line('house workflow: '+json.dumps(dict(kind=kind,**data),sort_keys=True,default=str))


def _record_main():
    global _main_ident
    _main_ident = threading.get_ident()


def _scan_main():
    import services
    lot = services.active_lot()
    if lot is not None and _build.in_build_mode():
        old = (getattr(lot,'_min_level',None),getattr(lot,'_max_level',None))
        # Native Lot caches these properties until Zone.on_build_buy_exit.
        # This only invalidates Python's two cached values, not the building.
        lot.clear_cached_level_range()
        fresh = (int(lot.min_level),int(lot.max_level))
        if old != fresh: _log('room-floor-range', cached=old, fresh=fresh)
    return _original_scan()


def _scan_rooms():
    if _main_ident is None: raise RuntimeError('The room-scan simulation thread is not ready')
    if threading.get_ident() == _main_ident: return _scan_main()
    result = _build.on_main(_scan_main)
    if result is None: raise RuntimeError('The room-scan simulation thread did not answer')
    return result


def _context(plan):
    import services
    plan._a11y_zone = int(services.current_zone_id())
    plan._a11y_household = int(services.active_household_id())
    return plan


def _valid(plan):
    import services
    return (_build.in_build_mode() and int(services.current_zone_id()) == plan._a11y_zone
            and int(services.active_household_id()) == plan._a11y_household)


def _floor(level):
    return 'Basement' if level == -1 else 'Ground floor' if level == 0 else 'Floor {}'.format(level+1)


def _position(plan, room):
    level = room.get('level',0)
    boxes = [r['box'] for r in plan.rooms if r.get('level',0)==level]
    west,north,east,south = min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)
    a,b,c,d = room['box'];x,z=(a+c)/2.0,(b+d)/2.0
    sides=[]
    if z < (north+south)/2.0-.1: sides.append('north')
    elif z > (north+south)/2.0+.1: sides.append('south')
    if x < (west+east)/2.0-.1: sides.append('west')
    elif x > (west+east)/2.0+.1: sides.append('east')
    relation = 'connecting hallway' if room['kind']=='hall' else 'street-facing room' if room['uv'][1]==0 else 'rear room'
    return '{}; {}; {}; {} by {} metres'.format(_floor(level),relation,' '.join(sides)+' side' if sides else 'center',c-a,d-b)


def _door_names(plan):
    for door in plan.doors:
        level = door.get('level',0)
        def owner(tile):
            return next((r['name'] for r in plan.rooms if r.get('level',0)==level and r['box'][0]<=tile[0]<r['box'][2] and r['box'][1]<=tile[1]<r['box'][3]),None)
        a,b=owner(door['tile_a']),owner(door['tile_b'])
        if door['front'] and (a or b): door['what']='Front door into '+(a or b)
        elif a and b: door['what']='Door between {} and {}'.format(a,b)


def _extend(plan, stories, basement):
    """Keep each existing floor template; repeat the highest template for additions."""
    original = copy.deepcopy(plan)
    templates={}
    for room in original.rooms:
        level=room.get('level',0)
        templates.setdefault(level,[]).append(room)
    if not templates or 0 not in templates: raise ValueError('The plan has no ground-floor template')
    low,high=_planner._limits()
    if isinstance(stories,bool) or not isinstance(stories,int) or not 1<=stories<=high+1:
        raise ValueError('That story count is outside the native game limits')
    if basement and low>=0: raise ValueError('The game does not allow a basement here')
    levels=list(range(-1 if basement else 0,stories));p=copy.deepcopy(original);p.rooms=[];p.doors=[]
    for level in levels:
        source=level if level in templates else 0 if level<0 else max(v for v in templates if v>=0)
        for room in templates[source]:
            r=copy.deepcopy(room);r['level']=level
            if source!=level:
                base=room.get('_a11y_template_name',room['name'])
                r['name']=_floor(level)+' '+base;r['_a11y_template_name']=base
            p.rooms.append(r)
        for door in original.doors:
            if door.get('level',0)!=source or (door['front'] and level!=0): continue
            d=copy.deepcopy(door);d['level']=level;p.doors.append(d)
    p.floors=stories;p.stairs=None
    halls=[r for r in p.rooms if r['level']==0 and r['kind']=='hall']
    if len(levels)>1:
        if len(halls)!=1 or p.width<5: raise ValueError('This layout has no verified straight-stair hallway')
        hall=halls[0];top=(p.width-2,hall['uv'][1]);p.stairs={'top':top,'climb':(1,0)}
    frame=_build.frame();along=frame.width if p.side in ('north','south') else frame.depth
    _house._map_plan(p,frame,along)
    p._a11y_transitions=[]
    if p.stairs:
        for lower in levels[:-1]:p._a11y_transitions.append((p.stairs['top_lot'],p.stairs['climb_lot'],lower,lower+1))
    _door_names(p)
    return p


def _summary(plan):
    levels=sorted({r.get('level',0) for r in plan.rooms})
    counts=', '.join('{}: {} rooms'.format(_floor(level),sum(r['kind']!='hall' and r.get('level',0)==level for r in plan.rooms)) for level in levels)
    return '{} by {} metres. Street-facing side: {}. {}. {} connecting stair runs.'.format(plan.width,plan.depth,plan.side,counts,len(getattr(plan,'_a11y_transitions',())))


def _edit_rooms(plan):
    rows=[(r['name'],_position(plan,r),i) for i,r in enumerate(plan.rooms)]+[('Back to house plan',None,None)]
    def selected(index):
        if index is None: _review(plan);return
        room=plan.rooms[index]
        options=[('Keep '+room['name'],_position(plan,room),None)]
        if room['kind']!='hall':options += [(name,None,(name,kind)) for name,kind in ROLES]
        options += [('Give this room a custom name','Changes the label; keeps its geometry and current room type.','custom')]
        def changed(value):
            if value=='custom':
                def named(text):
                    text=' '.join((text or '').split())[:60]
                    if text:room['name']=text;room['_a11y_template_name']=text
                    _door_names(plan);_edit_rooms(plan)
                _core.ask_text('Name this room',_position(plan,room)+'. Type one room name. Leave blank to keep '+room['name']+'.','',named)
                return
            if value is not None:room['name'],room['kind']=value;room['_a11y_template_name']=room['name']
            _door_names(plan);_edit_rooms(plan)
        _core.choose('Room use and name',room['name']+'. '+_position(plan,room),options,changed,tag='build')
    _core.choose('Rooms and positions','Select any room to choose its use or give it a custom name. Each room is edited separately.',rows,selected,tag='build')


def _stories(plan):
    low,high=_planner._limits()
    def count_chosen(count):
        options=[('No basement',None,False)]
        if low<0:options.append(('One basement level','Experimental native basement drawing, checked before continuing.',True))
        def below(value):
            try:p=_extend(plan,count,value)
            except ValueError as exc:_core.speak(str(exc));return
            _review(p)
        _core.choose('Basement','Keep the same perimeter below ground.',options,below,tag='build')
    rows=[('{} above-ground {}'.format(n,'story' if n==1 else 'stories'),None,n) for n in range(1,high+2)]
    _core.choose('Stories','Existing floor layouts are preserved. Extra stories repeat the highest floor layout; names can be changed separately.',rows,count_chosen,tag='build')


def _review(plan):
    if getattr(plan,'problem',None): _core.speak(plan.problem);return
    if not _valid(plan):_core.speak('The lot or household changed. Open Build my house again.');return
    estimate=_house.wall_meters(plan)*_house.WALL_PRICE+len(plan.doors)*100+len(getattr(plan,'_a11y_transitions',()))*_house.STAIR_PRICE
    funds=_build.funds() or 0
    rows=[('Build this house' if estimate<=funds else 'Estimated cost exceeds household funds',
           'Uses the existing native construction and placement checks.', 'build' if estimate<=funds else None),
          ('Rooms, positions and custom names','Choose each room separately; no comma-separated list.','rooms'),
          ('Stories and basement','Repeat layouts without changing the perimeter.','stories'),('Cancel',None,None)]
    def selected(action):
        if action=='rooms':_edit_rooms(plan)
        elif action=='stories':_stories(plan)
        elif action=='build':
            if not _valid(plan):_core.speak('The lot or household changed. Nothing was built.');return
            if _build._busy[0]:_core.speak('Still working on the last build step.');return
            _door_names(plan);plan._a11y_roof_prompt=True
            _log('approved',summary=_summary(plan),rooms=[(r.get('level',0),r['kind'],r['name'],r['box']) for r in plan.rooms],stairs=getattr(plan,'_a11y_transitions',()))
            _house.start_build(plan)
    _core.choose('Build my house: review',_summary(plan)+' Estimated structural cost {:,}; household funds {:,}.'.format(estimate,funds),rows,selected,tag='build')


def _preset(value):
    try:
        plan=_house.make_two_floor_plan(value[1]) if value[0]=='two' else _house.make_plan(list(value[1]))
        if getattr(plan,'problem',None):_core.speak(plan.problem);return
        # Also creates an explicit stair scope for the existing two-floor presets.
        plan=_extend(plan,plan.floors,False)
        _review(_context(plan))
    except Exception as exc:
        _log('plan-failed',error=str(exc));_core.speak('The house plan could not be prepared. '+str(exc))


def _custom():
    sizes=[('Compact square','10 by 10 metres.',(10,10)),('Standard rectangle','10 by 11 metres.',(10,11)),('Large rectangle','12 by 14 metres.',(12,14))]
    def size_chosen(size):
        def layout_chosen(layout):
            defaults=['Living room','Kitchen','Bedroom','Bathroom'] if layout=='four' else ['Living room','Bedroom']
            plan=_planner._build_plan(size[0],size[1],[0],layout,{0:defaults})
            if getattr(plan,'problem',None):_core.speak(plan.problem);return
            _stories(_context(plan))
        rows=[('Front and back rooms','One street-facing room, a hallway and one rear room per floor.','two'),
              ('Four rooms around a hallway','Two street-facing rooms and two rear rooms per floor.','four')]
        _core.choose('Room layout','The footprint stays aligned between floors. Review every room by its actual compass position afterward.',rows,layout_chosen,tag='build')
    _core.choose('House footprint','Choose the rectangular perimeter.',sizes,size_chosen,tag='build')


def _ready_made():
    rows=[(label,None,('one',list(kinds))) for label,kinds in _house.PRESETS]
    rows += [(label,None,('two',variant)) for label,variant in _house.TWO_FLOOR_PRESETS]
    _core.choose('Ready-made house layouts','Preserves the original room dimensions and door geometry. Stories, basement and room names can be adjusted in the review.',rows,_preset,tag='build')


def _legacy_plan(kinds):
    _preset(kinds if isinstance(kinds,tuple) else ('one',kinds))


def open_builder():
    if not _build.in_build_mode():_core.speak('Enter Build mode first.');return
    rows=[('Start with a ready-made layout','Original one- and two-story presets, with a common review and customization flow.',_ready_made),
          ('Design a square or rectangular house','Choose footprint, front/back or four-room layout, stories and basement.',_custom),
          ('Choose the room list yourself','Original one-floor room-list planner, using the same review.',lambda:_house._custom([]))]
    _core.choose('Build my house','One house builder: choose a starting layout, then review room positions, names, stories and basement before building.',rows,lambda fn:fn(),tag='build')


def _say(text):
    import tyjokr_a11y_basement as basement
    reason=basement.failure_reason()
    if reason and text.startswith('I stopped building at the '):
        return _original_say('Basement construction stopped: '+reason+'. No further rooms were attempted. Inspect the result before using Undo or trying again.')
    return _original_say(text)


def install():
    """Startup: record the simulation thread for room scans. Idempotent."""
    global _build, _core, _house, _planner, _installed
    if _installed:
        return
    import tyjokr_a11y_plus_build as build
    import tyjokr_a11y_plus_core as core
    import tyjokr_a11y_plus_house as house
    import tyjokr_a11y_house_planner as planner
    _installed = True
    _build, _core, _house, _planner = build, core, house, planner
    core.post(_record_main)
    # The pump may discard old queued work during loading. Its ticker also
    # records the owner, and follows any later simulation-thread change.
    core.add_ticker(.1, _record_main)
    _log('installed')


def _original_scan():
    import tyjokr_a11y_plus_rooms as rooms
    return rooms._scan_rooms_base()


def _original_say(text):
    import tyjokr_a11y_plus_house as house
    return house._say_base(text)
