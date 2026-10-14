"""World scanner: keyboard access to the Sims and objects on the lot.

The UI walker can reach anything the client draws, but the world itself is
not a widget. This module lists what is around the active Sim from the
simulation's own data, lets the player step through it by category, and
opens the game's REAL pie menu on the chosen thing so the existing menu
narration and focus walker take over from there. The original scanner design
comes from glaroc's a11yscan (see A11YSCAN-REVIEW.md); the tree navigation
and integration are ours.

How it stays in the game's own words:

- Object names are catalog-name localisation keys (obj.catalog_name). Python
  cannot turn a key into text, so the hash goes to the Flash layer in a
  message name ("A11y|loc|<hash>|<hash>"), the client resolves it in the
  player's language, and the text comes back on a11y.loc_enc.
- Categories are the catalog's own, two levels deep. The main category is
  the buy category the client reports for the object's definition
  (build_buy.get_object_buy_category_flags: Comfort, Surfaces, Decorations,
  Electronics, Appliances, Plumbing, Lighting, Kids, Activities and Skills,
  Storage, Pets, Transportation), spoken with the catalog's own filter
  labels; build-mode things (doors, gates, ladders, pools) sit under Build
  and anything the catalog never sold under Misc. The subcategory is the
  object's build/buy tag label (Beds, Sofas, Doors, or a function label for
  spawned and crafted things), from tyjokr_a11y_buycat (generated from the
  tuning dump and the client's KeysBB), resolved the same way. Sims use the
  game's "Sims" string.
- Interactions are never listed here. The client asks for the real pie menu
  itself (see _do_open), and from then on it is an ordinary pie menu.
- Only distance and bearing are words the game does not have; those come
  from tyjokr_a11y_lang like the rest of the mod's vocabulary.

Threading: keys arrive on the poller thread and go through
tyjokr_a11y_pump so every game call below runs on the simulation thread.
The loc replies arrive as Live commands, also on the simulation thread.

Tree keys: Up/Down previous/next sibling, Right enter a container,
Left/Backspace parent, Enter enter a container or open an object's menu.
The keyboard router provides scanner mode and equivalent Ctrl+Alt chords.
Native menus own navigation while open.
"""
import math
import threading
import time

import sims4.commands

import tyjokr_a11y_buycat as buycat
import tyjokr_a11y_lang as lang
import tyjokr_a11y_pump as pump
import tyjokr_a11y_settings as settings
import tyjokr_a11y_speech as speech
import tyjokr_a11y_availability as availability

# v1 used these reserved reference ids with a direct server call and the
# client discarded the reply; v2 lets the client make the request itself.
# Kept only as a record.
REF_OBJECT = 0xA11E5CA1
REF_SIM = 0xA11E5CA2

MAX_DISTANCE = 40.0        # metres; Sims are always listed regardless
_LOC_TIMEOUT = 0.6         # seconds to wait for the client before speaking without a name

SIMS = 'SIMS'
MISC = 'MISC'
BUILD = 'BUILD'
_COMPASS = ('north', 'north east', 'east', 'south east',
            'south', 'south west', 'west', 'north west')

# Chords that drive the open pie menu instead of the scanner list.
MENU_KEYS = {
    'prev': 'A11yNavPrev', 'next': 'A11yNavNext',
    'prevcat': 'A11yNavPrev', 'nextcat': 'A11yNavNext',
    'prevsub': 'A11yNavPrev', 'nextsub': 'A11yNavNext',
    'open': 'A11yActivate', 'back': 'A11yHidePieMenu',
}


class Entry(object):
    __slots__ = ('obj_id', 'is_sim', 'name', 'name_hash', 'distance',
                 'bearing', 'level_delta', 'category', 'group', 'first_name', 'availability', 'role')

    def __init__(self, obj_id, is_sim, name, name_hash, distance, bearing,
                 level_delta, category, group, first_name=''):
        self.obj_id = obj_id
        self.is_sim = is_sim
        self.name = name              # plain text when the game has it (Sims)
        self.name_hash = name_hash    # STBL key when only the client can say it
        self.distance = distance
        self.bearing = bearing
        self.level_delta = level_delta
        self.category = category      # subcategory: a labelled tag name, SIMS or MISC
        self.group = group            # main category: a buycat.GROUP_ORDER key
        self.first_name = first_name
        self.availability = 'pending'
        self.role = ''                # Sims: a spoken role such as 'patient, waiting'


_by_group = {}         # main category key -> [Entry], subcategory order then nearest first
_groups = []           # main category keys present, in the catalog's order
_group_index = 0
_item_index = 0
_tree_level = 'groups'  # groups -> subcategories -> items
_tree_groups = {}      # group -> last selected subcategory
_tree_items = {}       # (group, subcategory) -> last selected object id
_menu_open = False
_origin_level = 0
_last_scan = 0.0
_last_origin = None
_refresh_handle = None
_refresh_owner = None
_refresh_requested = False
_last_summary = None
_REFRESH_SECONDS = 2.0
_IDLE_SECONDS = 30.0
_last_activity = 0.0
_CLASS_CACHE_LIMIT = 1024
_CLASS_CACHE_SECONDS = 30.0
_class_cache = {}
_availability_revision = 0
_availability_client = None
_scan_stats = {'scans': 0, 'total_ms': 0.0, 'last_ms': 0.0, 'max_ms': 0.0,
               'examined': 0, 'in_range': 0, 'cache_hits': 0, 'cache_misses': 0}


def _touch():
    global _refresh_requested, _last_activity
    _refresh_requested = True
    _last_activity = time.monotonic()


def _classification(obj, now):
    # Only definition metadata is cached. Position, inventory/hidden state,
    # affordances and player names are read afresh on every scan.
    definition = obj.definition
    key = id(definition)
    cached = _class_cache.get(key)
    if cached is not None and cached[0] is definition and now < cached[1]:
        _scan_stats['cache_hits'] += 1
        return cached[2]
    names = _tag_names(obj)
    flags = _buy_flags(obj)
    category = _sub_of(names)
    result = (category, _group_of(flags, category), names, flags)
    if len(_class_cache) >= _CLASS_CACHE_LIMIT:
        _class_cache.clear()
    _class_cache[key] = (definition, now + _CLASS_CACHE_SECONDS, result)
    _scan_stats['cache_misses'] += 1
    return result


def enabled():
    return bool(settings.get('scanner', True))


# --------------------------------------------------------------- loc channel

_loc_cache = {}        # hash -> text
_loc_waiting = {}      # hash -> [_Pending]
_loc_lock = threading.Lock()
_announce_seq = [0]


class _Pending(object):
    def __init__(self, parts, seq):
        self.parts = parts
        self.seq = seq
        self.missing = set()
        self.timer = None
        self.done = False


def _send_ui(name):
    """Python -> Flash message. Must be called on the simulation thread."""
    try:
        import distributor.ops
        import distributor.system
        op = distributor.ops.SendUIMessage(name)
        distributor.system.Distributor.instance().add_op_with_no_owner(op)
        return True
    except Exception as ex:
        speech.log_line('scanner: send {} failed: {!r}'.format(name, ex))
        return False


def _finish(pending):
    with _loc_lock:
        if pending.done:
            return
        pending.done = True
        if pending.timer is not None:
            pending.timer.cancel()
        if pending.seq != _announce_seq[0]:
            return   # superseded by a newer announcement
        pieces = []
        for part in pending.parts:
            if isinstance(part, tuple):
                pieces.append(_loc_cache.get(part[1], ''))
            else:
                pieces.append(part)
    text = ''.join(pieces).replace(' ,', ',').replace('  ', ' ').strip()
    while text.startswith(',') or text.startswith('.'):
        text = text[1:].strip()
    if text:
        speech.speak(text, source='widget')


def _speak_parts(parts):
    """Speak a list of strings and ('loc', hash) parts once the client has
    resolved every key (or the timeout passes). Simulation thread only."""
    with _loc_lock:
        _announce_seq[0] += 1
        pending = _Pending(list(parts), _announce_seq[0])
        for part in pending.parts:
            if isinstance(part, tuple) and part[1] and part[1] not in _loc_cache:
                pending.missing.add(part[1])
        if not pending.missing:
            need_send = []
        else:
            need_send = []
            for key in pending.missing:
                waiting = _loc_waiting.setdefault(key, [])
                if not waiting:
                    need_send.append(key)
                waiting.append(pending)
            pending.timer = threading.Timer(_LOC_TIMEOUT, _finish, (pending,))
            pending.timer.daemon = True
            pending.timer.start()
    for key in need_send:
        _send_ui('A11y|loc|{}|{}'.format(key, key))
    if not pending.missing:
        _finish(pending)


@sims4.commands.Command('a11y.loc_enc', command_type=sims4.commands.CommandType.Live)
def a11y_loc_enc(text: str = '', _connection=None):
    """Flash reply: "<hash>|<percent-encoded localized text>"."""
    try:
        from tyjokr_a11y_narrator import _decode_percent
        head, _sep, body = text.partition('|')
        key = int(head)
        resolved = _decode_percent(body).strip()
    except Exception as ex:
        speech.log_line('scanner: bad loc reply {!r}: {!r}'.format(text[:60], ex))
        return True
    ready = []
    with _loc_lock:
        _loc_cache[key] = resolved
        for pending in _loc_waiting.pop(key, ()):
            pending.missing.discard(key)
            if not pending.missing:
                ready.append(pending)
    for pending in ready:
        _finish(pending)
    return True


# --------------------------------------------------------------- categories

def _tags_with(prefixes):
    return [tag for tag in buycat.ORDER if tag.startswith(prefixes)]


# Subcategory choice when a definition carries several labelled tags: the
# buy-mode function tags first (the catalog's own subcategories), then the
# build-mode tags, then the venue / off-the-grid / lot-requirement tags, then
# the room tags, then function tags (only spawned and crafted things get this
# far). Each tier keeps EA's file order.
_SUB_PRIORITY = (
    _tags_with(('BuyCatEE_', 'BuyCatSS_', 'BuyCatPA_', 'BuyCatLD_')),
    _tags_with(('Build_', 'TerrainManip_', 'TerrainPaint_')),
    _tags_with(('BuyCat_',)),
    _tags_with(('BuyCatMAG_',)),
    _tags_with(('Func_',)),
)


def _build_rank():
    rank = {}
    for tier in _SUB_PRIORITY:
        for tag in tier:
            rank.setdefault(tag, len(rank))
    return rank


_SUB_RANK = _build_rank()

# When the client reports several buy categories for one definition, prefer
# the one the subcategory's tag family belongs to (a bar is Activities and
# Skills, not Surfaces), then the catalog's display order.
_TAG_FAMILY = {
    'BuyCatEE_': ('ELECTRONICS', 'KIDS', 'ENTERTAINMENT', 'PETS'),
    'BuyCatSS_': ('COMFORT', 'SURFACE', 'STORAGE', 'PETS'),
    'BuyCatPA_': ('APPLIANCES', 'PLUMBING', 'PETS'),
    'BuyCatLD_': ('DECOR', 'LIGHTING'),
}
_BUILD_PREFIXES = ('Build_', 'TerrainManip_', 'TerrainPaint_',
                   'BuyCat_WaterObjects_BuildMode')


def _tag_names(obj):
    try:
        tags = obj.definition.get_tags()
    except Exception:
        return set()
    names = set()
    for tag in tags or ():
        name = getattr(tag, 'name', None)
        if name is None:
            try:
                from tag import Tag
                name = Tag(tag).name
            except Exception:
                continue
        names.add(str(name))
    return names


def _sub_of(names):
    for tier in _SUB_PRIORITY:
        for tag in tier:
            if tag in names:
                return tag
    return MISC


def _buy_flags(obj):
    """The client's buy-category bits for the definition (0 when it has none)."""
    try:
        import build_buy
        flags = int(build_buy.get_object_buy_category_flags(obj.definition.id))
    except Exception:
        return 0
    return flags & 0x7FFFFFFF      # drop DEFAULT


def _group_of(flags, sub):
    candidates = [key for key in buycat.GROUP_ORDER
                  if flags & buycat.GROUP_FLAG.get(key, 0)]
    if candidates:
        for prefix, family in _TAG_FAMILY.items():
            if sub.startswith(prefix):
                for key in family:
                    if key in candidates:
                        return key
                break
        return candidates[0]
    if sub.startswith(_BUILD_PREFIXES):
        return BUILD
    # The native buy catalog can report zero in Live Mode. Definition tags
    # remain available there; classify only known function-tag families.
    suffix = sub.split('_', 1)[-1]
    if sub.startswith('BuyCatEE_'):
        if suffix.startswith('Pet'):
            return 'PETS'
        if suffix.startswith('Kid') or suffix == 'MiscKids':
            return 'KIDS'
        if suffix == 'Transportation':
            return 'VEHICLE'
        if suffix == 'TVStand':
            return 'SURFACE'
        if suffix in ('Alarm', 'Audio', 'Clock', 'Computer', 'TV', 'MiscElectronics'):
            return 'ELECTRONICS'
        return 'ENTERTAINMENT'
    if sub.startswith('BuyCatSS_'):
        if any(word in suffix for word in ('Bed', 'Chair', 'Sofa', 'Seat', 'Barstool', 'Comfort')):
            return 'COMFORT'
        if any(word in suffix for word in ('Bookshelf', 'Dresser', 'Storage')):
            return 'STORAGE'
        return 'SURFACE'
    if sub.startswith('BuyCatPA_'):
        if suffix.startswith('Pet'):
            return 'PETS'
        if suffix in ('Shower', 'Sink', 'Toilet', 'Tub', 'PublicRestroom', 'MiscPlumbing'):
            return 'PLUMBING'
        return 'APPLIANCES'
    if sub.startswith('BuyCatLD_'):
        return 'LIGHTING' if 'Light' in suffix or 'Lamp' in suffix else 'DECOR'
    return MISC


def _label_hash(key):
    if key in buycat.GROUP_LABEL_HASH:
        return buycat.GROUP_LABEL_HASH[key]
    return buycat.TAG_LABEL_HASH.get(key, buycat.MISC_LABEL_HASH)


# ------------------------------------------------------------------ scanning

def _has_interactions(obj):
    """Objects the player could click on. Reuses the object-names census
    filter (debug/cheat/hidden/universal affordances excluded)."""
    try:
        import tyjokr_a11y_objectnames as objectnames
        return objectnames._has_interactions(obj)
    except ImportError:
        pass
    try:
        for sa in obj.super_affordances():
            if sa.debug or sa.cheat or not sa.allow_user_directed:
                continue
            return True
    except Exception:
        pass
    return False


def _bearing(dx, dz):
    angle = math.degrees(math.atan2(dx, dz)) % 360.0
    return int(((angle + 22.5) % 360.0) // 45) % 8


def _sim_name_parts(sim_info):
    """Plain names when the game stores them as text; a loc key for the few
    special Sims that only carry a name key."""
    try:
        first = str(sim_info.first_name or '')
        last = str(sim_info.last_name or '')
    except Exception:
        first, last = '', ''
    joined = ' '.join(part for part in (first, last) if part).strip()
    if joined:
        return joined, 0
    for attr in ('full_name_key', 'first_name_key'):
        try:
            key = int(getattr(sim_info, attr, 0) or 0)
        except Exception:
            key = 0
        if key:
            return None, key
    return '', 0


# Get to Work hospital patients (PatientSituationBase) by visit stage: the
# situation's current state class, as EA names them in
# situations.complex.patient_situation_base and hospital_patient_situation.
PATIENT_STAGES = {'ArrivingState': 'patient arriving', 'WaitingState': 'patient waiting',
                  '_AdmittedState': 'patient admitted', '_DiagnosedState': 'patient diagnosed',
                  'TreatedState': 'patient treated'}


def _patient_roles():
    """Sim id -> spoken role for every patient on the lot."""
    try:
        import services
        from situations.complex.patient_situation_base import PatientSituationBase
        manager = services.get_zone_situation_manager()
        situations = list(manager.values()) if manager is not None else []
    except Exception:
        return {}
    roles = {}
    for situation in situations:
        try:
            if not isinstance(situation, PatientSituationBase):
                continue
            patient = situation.get_patient()
            if patient is None:
                continue
            state = type(getattr(situation, '_cur_state', None)).__name__
            roles[patient.id] = lang.t(PATIENT_STAGES.get(state, 'patient'))
        except Exception:
            continue
    return roles


def _entry_for(obj, origin, origin_level, is_sim, category, group):
    pos = obj.position
    dx = float(pos.x) - float(origin.x)
    dz = float(pos.z) - float(origin.z)
    distance = math.sqrt(dx * dx + dz * dz)
    try:
        level_delta = int(obj.level) - origin_level
    except Exception:
        level_delta = 0
    if is_sim:
        name, key = _sim_name_parts(obj.sim_info)
        first = ''
        try:
            first = str(obj.sim_info.first_name or '')
        except Exception:
            pass
        return Entry(obj.id, True, name, key, distance, _bearing(dx, dz),
                     level_delta, category, group, first)
    # A player-given name is plain text; otherwise catalog_name is the
    # string-table key itself (an int; EA's own GSI code does hex() on it).
    custom = None
    try:
        if obj.has_custom_name():
            custom = str(obj.custom_name or '') or None
    except Exception:
        custom = None
    key = 0
    if custom is None:
        try:
            raw = obj.catalog_name
            key = int(getattr(raw, 'hash', raw)) & 0xFFFFFFFF
        except Exception:
            key = 0
    return Entry(obj.id, False, custom, key, distance, _bearing(dx, dz),
                 level_delta, category, group)


def _subs_in(entries):
    """Subcategory keys in the order the entries are listed."""
    seen = []
    for entry in entries:
        if entry.category not in seen:
            seen.append(entry.category)
    return seen


def _scan(preserve=False):
    """Rebuild the lists around the active Sim. Simulation thread only."""
    global _by_group, _groups, _group_index, _item_index, _origin_level
    global _last_scan, _last_origin, _last_summary
    global _availability_revision
    import services
    started = time.perf_counter()
    previous = _current() if preserve else None
    previous_group = _group_key() if preserve else None
    previous_index = _item_index
    if preserve:
        _tree_remember()
    _by_group = {}
    _groups = []
    _group_index = 0
    _item_index = 0
    sim = services.get_active_sim()
    if sim is None:
        availability.reset()
        return False
    _bind_availability_client()
    origin = sim.position
    _last_scan = time.monotonic()
    _last_origin = (sim.id, float(origin.x), float(origin.z))
    try:
        _origin_level = int(sim.level)
    except Exception:
        _origin_level = 0
    sims = [sim]
    try:
        for other in services.sim_info_manager().instanced_sims_gen():
            if other is not sim:
                sims.append(other)
    except Exception as ex:
        speech.log_line('scanner: sim listing failed: {!r}'.format(ex))
    roles = _patient_roles()
    for other in sims:
        try:
            entry = _entry_for(other, origin, _origin_level, True, SIMS, SIMS)
            entry.role = roles.get(other.id, '')
            _by_group.setdefault(SIMS, []).append(entry)
        except Exception as ex:
            speech.log_line('scanner: sim entry failed: {!r}'.format(ex))
    count = 0
    examined = 0
    in_range = 0
    notes = []
    try:
        objects = list(services.object_manager().get_valid_objects_gen())
    except Exception as ex:
        speech.log_line('scanner: object listing failed: {!r}'.format(ex))
        objects = []
    candidates = []
    for obj in objects:
        examined += 1
        try:
            if getattr(obj, 'is_sim', False) or getattr(obj, 'is_terrain', False):
                continue
            # Reject distant objects before walking their affordances or
            # resolving catalog metadata. Squared distance needs no sqrt.
            pos = obj.position
            dx = float(pos.x) - float(origin.x)
            dz = float(pos.z) - float(origin.z)
            if dx * dx + dz * dz > MAX_DISTANCE * MAX_DISTANCE:
                continue
            in_range += 1
            checker = getattr(obj, 'is_in_inventory', None)
            if checker is not None and checker():
                continue
            if obj.is_hidden():
                continue
            candidates.append(obj)
        except Exception:
            continue
    # Eligibility is evaluated incrementally on the simulation pump, never
    # synchronously on a key press. Unknown results remain discoverable.
    candidates.sort(key=lambda obj: (float(obj.position.x) - float(origin.x)) ** 2
                    + (float(obj.position.z) - float(origin.z)) ** 2)
    availability.begin(sim, candidates)
    _availability_revision = availability.revision()
    for obj in candidates:
        try:
            verdict = availability.state(obj)
            if verdict == 'empty':
                continue
            entry = _entry_for(obj, origin, _origin_level, False, MISC, MISC)
            entry.availability = verdict
            if entry.distance > MAX_DISTANCE:
                continue
            entry.category, entry.group, names, flags = _classification(obj, _last_scan)
            _by_group.setdefault(entry.group, []).append(entry)
            count += 1
            if not preserve and entry.group in (MISC, BUILD) and len(notes) < 12:
                # Diagnostics for the two catch-alls: what did the client
                # report, and which labelled tags did the definition carry?
                labelled = sorted(name for name in names
                                  if name.startswith(('BuyCat', 'Build_', 'Func_')))
                notes.append('{} {} flags=0x{:X} sub={} tags={}'.format(
                    entry.group, getattr(obj.definition, 'name', '?'), flags,
                    entry.category, ','.join(labelled[:6])))
        except Exception:
            continue
    for entries in _by_group.values():
        entries.sort(key=lambda e: (_SUB_RANK.get(e.category, 1 << 20), e.distance))
    # Sims first (the active Sim is first inside), then the catalog's order.
    _groups = [key for key in buycat.GROUP_ORDER if _by_group.get(key)]
    summary = ' '.join('{}:{}/{}'.format(key, len(_by_group[key]),
                                         len(_subs_in(_by_group[key])))
                       for key in _groups)
    if summary != _last_summary or not preserve:
        speech.log_line('scanner: {} sims, {} objects, {} categories (items/subcategories): {}'.format(
            len(_by_group.get(SIMS, ())), count, len(_groups), summary))
        _last_summary = summary
    if not preserve:
        for note in notes:
            speech.log_line('scanner:   ' + note)
    if previous_group in _groups:
        _group_index = _groups.index(previous_group)
        entries = _by_group[previous_group]
        _item_index = min(previous_index, len(entries) - 1)
        if previous is not None:
            for index, entry in enumerate(entries):
                if entry.obj_id == previous.obj_id:
                    _item_index = index
                    break
    if preserve:
        _tree_restore()
    elapsed = (time.perf_counter() - started) * 1000.0
    _scan_stats['scans'] += 1
    _scan_stats['total_ms'] += elapsed
    _scan_stats['last_ms'] = elapsed
    _scan_stats['max_ms'] = max(_scan_stats['max_ms'], elapsed)
    _scan_stats['examined'] = examined
    _scan_stats['in_range'] = in_range
    return bool(_groups)


def _group_key():
    if not _groups:
        return None
    return _groups[_group_index % len(_groups)]


def _entries():
    key = _group_key()
    if key is None:
        return []
    return _by_group.get(key, [])


def _current():
    entries = _entries()
    if not entries:
        return None
    return entries[_item_index % len(entries)]


# ------------------------------------------------------- for the menu window

def ensure_scan():
    """Scan if nothing is listed yet. Simulation thread."""
    _touch()
    return _ensure_scan()


def snapshot():
    """(groups as [(key, [Entry])], current group key, current Entry)."""
    return ([(key, list(_by_group.get(key, ()))) for key in _groups],
            _group_key(), _current())


def subs_in(entries):
    return _subs_in(entries)


def label_hash(key):
    return _label_hash(key)


def place_text(entry):
    return _place_part(entry)


def select_group(key):
    """Move the cursor to a main category and speak it. Simulation thread."""
    global _group_index, _item_index, _tree_level
    if key not in _groups:
        return False
    _tree_remember()
    _group_index = _groups.index(key)
    _tree_level = 'groups'
    _tree_restore()
    _tree_speak()
    return True


def select_item(key, obj_id):
    """Move the cursor to one thing and speak it. Simulation thread."""
    global _group_index, _item_index, _tree_level
    if key not in _groups:
        return False
    entries = _by_group.get(key, [])
    for index, entry in enumerate(entries):
        if entry.obj_id == obj_id:
            _tree_remember()
            _group_index = _groups.index(key)
            _item_index = index
            _tree_level = 'items'
            _tree_remember()
            _tree_speak()
            return True
    return False


# --------------------------------------------------------------- describing

def _name_part(entry):
    if entry.name:
        return entry.name
    if entry.name_hash:
        return ('loc', entry.name_hash)
    return ''


def _place_part(entry):
    metres = int(round(entry.distance))
    if metres < 1:
        where = lang.t('here')
    else:
        where = '{} {} {}'.format(metres, lang.t('meters'),
                                  lang.t(_COMPASS[entry.bearing]))
    delta = entry.level_delta
    if delta == 1:
        where += ', ' + lang.t('one floor up')
    elif delta == -1:
        where += ', ' + lang.t('one floor down')
    elif delta > 1:
        where += ', {} {}'.format(delta, lang.t('floors up'))
    elif delta < -1:
        where += ', {} {}'.format(-delta, lang.t('floors down'))
    return where


def _entry_parts(entry, index, total):
    status = ', ' + lang.t('scanner unavailable') if entry.availability == 'locked' else ''
    if entry.role:
        status = ', ' + entry.role + status
    return [_name_part(entry), status + ', ' + _place_part(entry),
            '. {} {} {}.'.format(index + 1, lang.t('of'), total)]


def _sub_label_part(entries, entry):
    """The subcategory name, or None when the main category has a single
    subcategory that is the category itself (Sims, bare Misc)."""
    if len(_subs_in(entries)) <= 1 and _label_hash(entry.category) == _label_hash(entry.group):
        return None
    return ('loc', _label_hash(entry.category))


def _sub_count_part(entries, entry):
    count = sum(1 for other in entries if other.category == entry.category)
    return ', {} {}. '.format(count, lang.t('items'))


def _group_parts():
    """Main category with its count, the subcategory the cursor is in with
    its count, then the thing under the cursor."""
    entries = _entries()
    key = _group_key()
    if key is None:
        return [lang.t('nothing nearby')]
    parts = [('loc', _label_hash(key)),
             ', {} {}. '.format(len(entries), lang.t('items'))]
    entry = _current()
    if entry is not None:
        sub = _sub_label_part(entries, entry)
        if sub is not None:
            parts.append(sub)
            parts.append(_sub_count_part(entries, entry))
        parts.append(_name_part(entry))
        parts.append((', ' + entry.role if entry.role else '') + ', ' + _place_part(entry) + '.')
    return parts


def _sub_parts(entries, entry, index):
    """Subcategory with its count, then the thing."""
    parts = []
    sub = _sub_label_part(entries, entry)
    if sub is not None:
        parts.append(sub)
        parts.append(_sub_count_part(entries, entry))
    parts.extend(_entry_parts(entry, index, len(entries)))
    return parts


def _ensure_scan():
    same_origin = True
    try:
        import services
        sim = services.get_active_sim()
        same_origin = sim is not None and _last_origin is not None and (
            sim.id == _last_origin[0] and int(sim.level) == _origin_level)
    except Exception:
        pass
    if (_groups and same_origin and availability.revision() == _availability_revision
            and time.monotonic() - _last_scan < _REFRESH_SECONDS):
        return True
    return _scan(preserve=True)


def _refresh_tick(_handle=None):
    # A real-time game alarm: updates while paused, never on the key thread.
    # After 30 seconds without scanner input, the alarm only checks these
    # flags. The next action refreshes before moving or opening an item.
    global _refresh_requested
    if not enabled() or not settings.get('keyboard', True):
        availability.reset()
        return
    if not _refresh_requested:
        return
    try:
        import tyjokr_a11y_keys as keys
        ui_owns_input = keys._modal_active or keys._editing_active
    except Exception:
        ui_owns_input = False
    if _menu_open or ui_owns_input:
        availability.pause()
        return
    now = time.monotonic()
    if now - _last_activity >= _IDLE_SECONDS:
        _refresh_requested = False
        availability.pause()
        return
    if now - _last_scan >= _REFRESH_SECONDS:
        _scan(preserve=True)


def _start_refresh():
    global _refresh_owner, _refresh_handle
    import alarms
    import clock
    if _refresh_handle is not None:
        try:
            alarms.cancel_alarm(_refresh_handle)
        except Exception:
            # The previous zone may already have destroyed its timeline.
            pass
    class RefreshOwner(object):
        pass
    _refresh_owner = RefreshOwner()
    _refresh_handle = alarms.add_alarm_real_time(
        _refresh_owner, clock.interval_in_real_seconds(_REFRESH_SECONDS),
        _refresh_tick, repeating=True)


def _active_sim_changed(old_sim, new_sim):
    global _last_scan
    availability.reset()
    _last_scan = 0.0
    if enabled() and _refresh_requested:
        pump.post(_scan, True)


def _bind_availability_client():
    global _availability_client
    try:
        import services
        client = services.client_manager().get_first_client()
        if client is _availability_client:
            return
        _unbind_availability_client()
        if client is not None:
            client.register_active_sim_changed(_active_sim_changed)
            _availability_client = client
    except Exception:
        # _ensure_scan also compares the active Sim identity on every action.
        pass


def _unbind_availability_client():
    global _availability_client
    if _availability_client is not None:
        try:
            _availability_client.unregister_active_sim_changed(_active_sim_changed)
        except Exception:
            pass
    _availability_client = None


# ------------------------------------------------------------------- intents

def _tree_remember():
    entry = _current()
    if entry is not None:
        _tree_groups[entry.group] = entry.category
        _tree_items[(entry.group, entry.category)] = entry.obj_id


def _tree_restore(subcategory=None):
    """Restore by identity, falling back within the same subcategory first."""
    global _item_index, _tree_level
    entries = _entries()
    if not entries:
        _item_index = 0
        _tree_level = 'groups'
        return
    group = _group_key()
    subs = _subs_in(entries)
    sub = subcategory if subcategory is not None else _tree_groups.get(group)
    if sub not in subs:
        sub = subs[0]
    indices = [i for i, entry in enumerate(entries) if entry.category == sub]
    wanted = _tree_items.get((group, sub))
    _item_index = next((i for i in indices if entries[i].obj_id == wanted), indices[0])
    # Do not leave a redundant Sims -> Sims container after a refresh.
    if _tree_level == 'subcategories' and not _tree_has_sublevel():
        _tree_level = 'items'


def _tree_has_sublevel():
    entries = _entries()
    entry = _current()
    return entry is not None and _sub_label_part(entries, entry) is not None


def _kind(term):
    """The spoken kind before a name; verbosity brief leaves it out."""
    return [] if settings.brief() else [lang.t(term) + '. ']


def _tree_parts():
    entry = _current()
    if entry is None:
        return [lang.t('nothing nearby')]
    entries = _entries()
    if _tree_level == 'groups':
        return _kind('scanner category') + [('loc', _label_hash(_group_key())),
                ', {} {}. {} {} {}.'.format(len(entries), lang.t('items'),
                    _group_index + 1, lang.t('of'), len(_groups))]
    subs = _subs_in(entries)
    siblings = [e for e in entries if e.category == entry.category]
    if _tree_level == 'subcategories':
        return _kind('scanner subcategory') + [('loc', _label_hash(entry.category)),
                ', {} {}. {} {} {}.'.format(len(siblings), lang.t('items'),
                    subs.index(entry.category) + 1, lang.t('of'), len(subs))]
    return _entry_parts(entry, siblings.index(entry), len(siblings))


def _tree_speak(prefix=''):
    _speak_parts(([prefix] if prefix else []) + _tree_parts())


def enter_mode():
    """Keyboard router calls on the simulation thread after mode activation."""
    _touch()
    _ensure_scan()
    _tree_speak(lang.t('scanner') + '. ')


def resume_mode():
    """Restore the spoken location after the native menu relinquishes input."""
    enter_mode()


def set_camera_live(live):
    import tyjokr_a11y_camera as camera_follow
    camera_follow.set_live(live)


def update_camera_follow():
    import tyjokr_a11y_camera as camera_follow
    camera_follow.update()


def _tree_move(step):
    global _group_index, _item_index
    entry = _current()
    if entry is None:
        _tree_speak()
        return
    _tree_remember()
    if _tree_level == 'groups':
        _group_index = (_group_index + step) % len(_groups)
        _tree_restore()
    elif _tree_level == 'subcategories':
        subs = _subs_in(_entries())
        _tree_restore(subs[(subs.index(entry.category) + step) % len(subs)])
    else:
        indices = [i for i, other in enumerate(_entries())
                   if other.category == entry.category]
        _item_index = indices[(indices.index(_item_index) + step) % len(indices)]
    _tree_remember()
    _tree_speak()


def _tree_enter(activate=False):
    global _tree_level
    if _current() is None:
        _tree_speak()
        return
    if _tree_level == 'groups':
        _tree_level = 'subcategories' if _tree_has_sublevel() else 'items'
    elif _tree_level == 'subcategories':
        _tree_level = 'items'
    elif activate:
        _do_open()
        return
    # Right on a leaf only repeats it; Enter is required for interaction.
    _tree_speak()


def _tree_back():
    global _tree_level
    _tree_remember()
    if _tree_level == 'items' and _tree_has_sublevel():
        _tree_level = 'subcategories'
    else:
        _tree_level = 'groups'
    _tree_speak()

def _do_rescan():
    _class_cache.clear()
    availability.recheck()
    if not _scan(preserve=True):
        speech.speak(lang.t('nothing nearby'), source='widget')
        return
    total = sum(len(v) for v in _by_group.values())
    parts = ['{} {}, {} {}. '.format(total, lang.t('items'),
                                     len(_groups), lang.t('categories'))]
    _speak_parts(parts + _tree_parts())


def _do_step_sub(step):
    """Optional legacy Page key jump; the tree itself needs no Page keys."""
    global _tree_level
    entry = _current()
    if entry is None:
        _tree_speak()
        return
    _tree_remember()
    subs = _subs_in(_entries())
    _tree_restore(subs[(subs.index(entry.category) + step) % len(subs)])
    _tree_level = 'items'
    _tree_remember()
    _speak_parts([('loc', _label_hash(_current().category)), '. '] + _tree_parts())


def _do_where():
    import services
    parts = []
    sim = services.get_active_sim()
    if sim is not None:
        name, key = _sim_name_parts(sim.sim_info)
        parts.append(name if name else ('loc', key))
        parts.append('. ')
    entry = _current()
    if entry is None:
        parts.append(lang.t('nothing nearby'))
    else:
        entries = _entries()
        parts.append(('loc', _label_hash(entry.group)))
        sub = _sub_label_part(entries, entry)
        if sub is not None:
            parts.append(', ')
            parts.append(sub)
        parts.append('. ')
        parts.extend(_entry_parts(entry, _item_index % len(entries), len(entries)))
    _speak_parts(parts)


def _do_open():
    """Ask the client to open the game's pie menu on the current thing.

    The request goes to Flash first (A11y|pick|...): the patched PieMenuMain
    posts interactions.choices through the client's own command channel with
    its own request counter, exactly like a mouse click, so the reply is a
    menu the client asked for and it draws it. Python never calls
    generate_choices itself (v1 did, and the client discarded the reply)."""
    entry = _current()
    if entry is None:
        speech.speak(lang.t('nothing nearby'), source='widget')
        return
    import services
    obj = services.object_manager().get(entry.obj_id)
    if obj is None:
        speech.speak(lang.t('no longer here'), source='widget')
        return
    try:
        from server.pick_info import PickType
        pick_type = PickType.PICK_SIM if entry.is_sim else PickType.PICK_OBJECT
        pos = obj.position
        try:
            level = int(obj.level)
        except Exception:
            level = 0
        try:
            lot_id = int(services.active_lot().lot_id)
        except Exception:
            lot_id = 0
        first = (entry.first_name or '').replace('|', ' ')
        sent = _send_ui('A11y|pick|{}|{}|{}|{}|{:.3f}|{:.3f}|{:.3f}|{}'.format(
            obj.id, int(pick_type), lot_id, first,
            float(pos.x), float(pos.y), float(pos.z), level))
    except Exception as ex:
        speech.log_line('scanner: open menu failed: {!r}'.format(ex))
        sent = False
    speech.log_line('scanner: menu requested for {} (sim={}) sent={}'.format(
        entry.obj_id, entry.is_sim, sent))


@sims4.commands.Command('a11y.menuempty', command_type=sims4.commands.CommandType.Live)
def a11y_menuempty(arg: str = '', _connection=None):
    """Flash: the requested pie menu had no options."""
    speech.speak(lang.t('no options'), source='widget')
    return True


def _dispatch(intent):
    _touch()
    if intent != 'rescan':
        _ensure_scan()
    if intent == 'rescan':
        _do_rescan()
    elif intent == 'next':
        _tree_move(1)
    elif intent == 'prev':
        _tree_move(-1)
    elif intent == 'nextcat':
        _tree_enter()
    elif intent == 'prevcat':
        _tree_back()
    elif intent == 'nextsub':
        _do_step_sub(1)
    elif intent == 'prevsub':
        _do_step_sub(-1)
    elif intent == 'open':
        _tree_enter(activate=True)
    elif intent == 'where':
        _do_where()
    elif intent == 'back':
        _tree_back()
    else:
        speech.log_line('scanner: unknown intent {!r}'.format(intent))


def on_key(intent, on_simulation_thread=False):
    """Called on the KEY thread. Decides who handles the chord; never
    touches the game here unless its caller explicitly owns the simulation thread."""
    if not enabled():
        return
    if intent == 'repeat':
        speech.repeat_last()
        return
    if intent == 'help':
        import tyjokr_a11y_shortcuts as shortcuts
        shortcuts.speak()
        return
    if _menu_open and intent in MENU_KEYS:
        # A pie menu is open: the chords walk it through the Flash walker.
        _log_route('sent to the open menu', intent)
        try:
            import tyjokr_a11y_keys as keys
            keys._send(MENU_KEYS[intent])
        except Exception as ex:
            speech.log_line('scanner: menu key failed: {!r}'.format(ex))
        return
    if on_simulation_thread:
        # The world-chord callback has already crossed onto the simulation.
        # Do not defer the same key to a second alarm turn.
        _log_route('dispatched to the scanner', intent)
        _dispatch(intent)
    elif not pump.post(_dispatch, intent):
        speech.speak(lang.t('no lot loaded'), explicit=True)


_route_logged = {}


def _log_route(reason, intent):
    """One line per reason per second (fixed reasons, bounded dict)."""
    now = time.monotonic()
    if now - _route_logged.get(reason, 0.0) >= 1.0:
        _route_logged[reason] = now
        speech.log_line('scanner: chord {} {}'.format(intent, reason))


def note_menu_open():
    """Any pie menu opened (ours or a mouse click)."""
    global _menu_open
    if not _menu_open:
        speech.log_line('scanner: menu flag set')
    _menu_open = True
    availability.pause()


@sims4.commands.Command('a11y.menuclosed', command_type=sims4.commands.CommandType.Live)
def a11y_menuclosed(arg: str = '', _connection=None):
    global _menu_open
    if _menu_open:
        speech.log_line('scanner: menu flag cleared')
    _menu_open = False
    return True


@sims4.commands.Command('a11y.scan', command_type=sims4.commands.CommandType.Live)
def a11y_scan(action: str = 'rescan', _connection=None):
    """a11y.scan [rescan|next|prev|nextcat|prevcat|nextsub|prevsub|open|back|
    where] runs one scanner action from the console (same as the chords)."""
    output = sims4.commands.CheatOutput(_connection)
    if action.lower() == 'stats':
        stats = dict(_scan_stats)
        stats['mean_ms'] = stats['total_ms'] / max(1, stats['scans'])
        text = ('scanner: {scans} scans; last {last_ms:.2f} ms, mean {mean_ms:.2f} ms, '
                'max {max_ms:.2f} ms; last objects {examined}, in range {in_range}; '
                'classification hits {cache_hits}, misses {cache_misses}').format(**stats)
        text += '; refresh {}'.format('active' if _refresh_requested else 'idle')
        output(text)
        speech.log_line(text)
        return True
    if not enabled():
        output('a11y: scanner is off (cfg [features] scanner)')
        return True
    _dispatch(action.lower())
    output('a11y: scanner {} -> {} categories, pump {}'.format(
        action, len(_groups), pump.status()))
    return True


def _install_zone_hook():
    import zone
    original = zone.Zone.on_loading_screen_animation_finished

    def a11y_scanner_on_loading_screen_animation_finished(self, *args, **kwargs):
        global _by_group, _groups, _menu_open, _last_scan, _refresh_requested, _last_activity
        global _tree_level
        result = original(self, *args, **kwargs)
        _by_group = {}
        _groups = []
        _tree_level = 'groups'
        _tree_groups.clear()
        _tree_items.clear()
        availability.reset()
        _unbind_availability_client()
        _bind_availability_client()
        import tyjokr_a11y_camera as camera_follow
        camera_follow.reset()
        _menu_open = False
        _last_scan = 0.0
        _refresh_requested = False
        _last_activity = 0.0
        _class_cache.clear()
        for key in _scan_stats:
            _scan_stats[key] = 0
        try:
            _start_refresh()
        except Exception as ex:
            speech.log_line('scanner: refresh alarm failed: {!r}'.format(ex))
        with _loc_lock:
            _loc_cache.clear()
            _loc_waiting.clear()
        # Re-assert the Flash game-message hook after every load.
        _send_ui('A11yHook')
        return result

    zone.Zone.on_loading_screen_animation_finished = (
        a11y_scanner_on_loading_screen_animation_finished)


try:
    _install_zone_hook()
except Exception as _zone_ex:
    speech.log_line('scanner: zone hook install failed: {!r}'.format(_zone_ex))
