"""Dining/desk chair snapping through native Build/Buy attachment slots.

No guessed chair offsets or rotation, no input polling and no game actions
until the ordinary placement acknowledgement/ownership/payment transaction.
"""
import math
import tyjokr_a11y_speech as speech

CHAIRS = {'buycatssdiningchair': 'buycatssdiningtable',
          'buycatssdeskchair': 'buycatssdesk'}
MAX_SLOTS = 128


def _log(text):
    speech.log_line('chair snap: '+text)


def _tags(definition):
    from tag import Tag
    result=set()
    try:values=definition.get_tags() or ()
    except (AttributeError,TypeError):return result
    for value in values:
        try:result.add(str(Tag(value).name).lower().replace('_',''))
        except (ValueError,TypeError,AttributeError):pass
    return result


def _kind(item):
    import services
    import tyjokr_a11y_settings as settings
    if not settings.get('chair_snapping', True):return None
    try:
        definition=services.definition_manager().get(item['id'], get_fallback_definition_id=False)
        tags=_tags(definition)
        for chair,table in CHAIRS.items():
            if chair in tags:return definition,table
    except Exception as exc:
        _log('classification unavailable: {!r}'.format(exc))
    return None


def _root(obj):
    for _ in range(8):
        if not getattr(obj,'is_part',False):return obj
        obj=getattr(obj,'part_owner',None)
        if obj is None:return None
    return None


def _state(obj):
    p,q=obj.position,obj.orientation
    values=tuple(float(v) for v in (p.x,p.y,p.z,q.x,q.y,q.z,q.w))
    if not all(math.isfinite(v) for v in values):raise ValueError('Non-finite table transform')
    return int(obj.level),values


def _slot_state(slot):
    p,q=slot.position,slot.transform.orientation
    values=tuple(float(v) for v in (p.x,p.y,p.z,q.x,q.y,q.z,q.w))
    if not all(math.isfinite(v) for v in values):raise ValueError('Non-finite seat transform')
    return values


def _safe_target(obj, level):
    import services
    import tyjokr_a11y_place as place
    try:
        return (obj is not None and not getattr(obj,'is_part',False)
                and int(obj.level)==int(level) and not obj.is_in_inventory() and not obj.is_hidden()
                and obj.get_household_owner_id() in (None,0,place._household_id())
                and services.active_lot().is_position_on_lot(obj.position))
    except (AttributeError,TypeError,ValueError):return False


def _target(item, frame):
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_layers as layers
    import tyjokr_a11y_tiles as tiles
    kind=_kind(item)
    if kind is None:return None
    definition,wanted=kind
    focused=layers.focused_target()
    if focused is not None and wanted in _tags(focused.definition) and _safe_target(focused,grid._level):
        return definition,focused,True
    i,j=grid._tile
    candidates={}
    for di in range(-1,2):
        for dj in range(-1,2):
            if not frame.inside(i+di,j+dj):continue
            if di or dj:
                side=(1 if di>0 else 3) if abs(di)>abs(dj) else (0 if dj>0 else 2)
                if int(grid._facing)%4 != side:continue
            for obj in tiles.objects_on(frame,i+di,j+dj,grid._level):
                if not _safe_target(obj,grid._level) or wanted not in _tags(obj.definition):continue
                row=(di*di+dj*dj,obj)
                if obj.id not in candidates or row[0]<candidates[obj.id][0]:candidates[obj.id]=row
    rows=sorted(candidates.values(),key=lambda row:(row[0],row[1].id))
    if not rows:return None
    if len(rows)>1 and rows[0][0]==rows[1][0]:return definition,None,False
    return definition,rows[0][1],False


def _slots(table):
    # The native SlotComponent yields part-owned slots and may also yield the
    # root-owned version of the same bone. Prefer the actual table part.
    found={}
    for index,slot in enumerate(table.get_runtime_slots_gen()):
        if index>=MAX_SLOTS:raise ValueError('Too many attachment slots to check safely')
        if _root(slot.owner) is not table:continue
        key=int(slot.slot_name_hash)
        if key not in found or getattr(slot.owner,'is_part',False):found[key]=slot
    return list(found.values())


def _key(slot):
    owner=slot.owner
    return int(slot.slot_name_hash),(int(owner.part_group_index) if getattr(owner,'is_part',False) else None)


def _seat(table, definition, point, obj=None, key=None):
    ranked=[]
    for slot in _slots(table):
        try:
            if key is not None and _key(slot)!=tuple(key):continue
            if not slot.is_enabled or not slot.empty or slot.is_deco_slot():continue
            p=slot.position
            distance=(float(p.x)-float(point.x))**2+(float(p.z)-float(point.z))**2
            if not math.isfinite(distance):continue
            ranked.append((distance,_key(slot),slot))
        except Exception as exc:_log('slot metadata refused: {!r}'.format(exc))
    for _distance,_ident,slot in sorted(ranked,key=lambda row:(row[0],row[1][0])):
        try:
            valid=(slot.is_valid_for_placement(definition=definition) if obj is None
                   else slot.is_valid_for_placement(obj=obj))
            _log('table {} slot {} native validation={!r}'.format(table.id,_key(slot),valid))
            if valid:return slot
        except Exception as exc:_log('native slot check failed: {!r}'.format(exc))
    return None


def _request(item, frame):
    import services
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_layers as layers
    import tyjokr_a11y_tiles as tiles
    target=_target(item,frame)
    if target is None:return None,None
    definition,table,explicit=target
    if table is None:return None,'More than one table is equally close. Focus the intended table with 1 first.'
    point=tiles.position(frame,*grid._tile,grid._level)
    slot=_seat(table,definition,point)
    if slot is None:return None,'The table has no free compatible chair seat that the game accepts. Nothing was bought.'
    focused=layers.focused_target()
    request={'zone':int(services.current_zone_id()),'product':int(item['id']),
             'table':int(table.id),'definition':int(table.definition.id),'state':_state(table),'slot':_key(slot),'slot_state':_slot_state(slot),
             'tile':tuple(grid._tile),'level':int(grid._level),'facing':int(grid._facing),
             'focused':getattr(focused,'id',None),'seat_tile':tuple(frame.tile_of(slot.position.x,slot.position.z))}
    return request,None


def try_place(item, frame):
    """None delegates ordinary placement; bool means the chair path handled it."""
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_place as place
    try:
        request,error=_request(item,frame)
        if request is None and error is None:return None
        if error:
            speech.speak(error,explicit=True);return False
        target=grid.cursor()
        if target is None:return False
        return place.place(target[0],grid._level,grid._surface(),chair_request=request)
    except Exception as exc:
        _log('request refused: {!r}'.format(exc))
        speech.speak('The chair seat could not be checked. Nothing was bought.',explicit=True)
        return False


def validate(request, obj, item, position, level):
    """Recheck exact target/slot after the native tool-drop acknowledgement."""
    import services
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_layers as layers
    try:
        if (request['zone']!=int(services.current_zone_id()) or request['product']!=int(item['id'])
                or request['tile']!=tuple(grid._tile) or request['level']!=int(grid._level)
                or request['facing']!=int(grid._facing) or int(level)!=request['level']
                or request['focused']!=getattr(layers.focused_target(),'id',None)):return None
        kind=_kind(item)
        if kind is None:return None
        table=services.object_manager().get(request['table'])
        if not _safe_target(table,level) or _state(table)!=request['state'] or int(table.definition.id)!=request['definition']:return None
        if kind[1] not in _tags(table.definition):return None
        slot=_seat(table,kind[0],position,obj=obj,key=request['slot'])
        if slot is not None and _slot_state(slot)==request['slot_state']:return table,slot
    except Exception as exc:_log('acknowledged seat refused: {!r}'.format(exc))
    return None


def attached(table,slot,obj):
    try:
        hashed=getattr(obj.location,'slot_hash',None) or getattr(obj.location,'joint_name_hash',None)
        return (_root(obj.parent) is table and int(hashed)==int(slot.slot_name_hash)
                and any(child is obj for child in slot.children))
    except Exception as exc:
        _log('attachment readback failed: {!r}'.format(exc));return False


def fit_parts(item,frame):
    """Describe the same native seat Enter will request, without creating it."""
    try:
        request,error=_request(item,frame)
        if error:return [error.replace(' Nothing was bought.','')+' ']
        if request is not None:
            import services
            import tyjokr_a11y_grid as grid
            import tyjokr_a11y_tiles as tiles
            table=services.object_manager().get(request['table'])
            di,dj=request['seat_tile'][0]-grid._tile[0],request['seat_tile'][1]-grid._tile[1]
            return ['Chair will snap at ',grid._name(table),'. Seat ',tiles.relative(di,dj),'. Enter places it using the game’s validation. ']
    except Exception as exc:_log('preview unavailable: {!r}'.format(exc))
    return None


def has_target(item,frame):
    try:return _target(item,frame) is not None
    except Exception:return False


def announce(obj,item,price,table):
    import tyjokr_a11y_grid as grid
    import tyjokr_a11y_scanner as scanner
    scanner._speak_parts(['Placed ',item.get('name') or 'chair',' at ',grid._name(table),
                          ' using the game’s chair slot, for {} simoleons.'.format(price)])
    _log('attached chair {} to table {} and paid {}'.format(obj.id,table.id,price))
