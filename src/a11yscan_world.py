"""World queries: locate the active Sim, enumerate reachable objects, name them
and sort them into categories.

Object display names in this game are LocalizedString protobufs that only the
client resolves, so for now we derive a readable label from the tuning class
name instead. It is not the shipped English string, but it is stable, unique
and good enough to navigate by. Sims are the exception: their first and last
names are plain Python strings, so those come through exactly right.
"""
import math

import a11yscan_names as names
import a11yscan_objects as objectnames
import a11yscan_speech as speech

YOURSELF = 'yourself'
PHONE = 'phone'
INVENTORY = 'inventory'
CONTACTS = 'relationships'
SIMS = 'sims'
OTHER = 'other'

CATEGORY_ORDER = [
    YOURSELF,
    PHONE,
    INVENTORY,
    CONTACTS,
    SIMS,
    'seating',
    'beds',
    'food and drink',
    'bathroom',
    'electronics',
    'skills and fun',
    'doors and stairs',
    OTHER,
]

_KEYWORDS = (
    ('seating', ('chair', 'sofa', 'loveseat', 'stool', 'bench', 'recliner', 'couch')),
    ('beds', ('bed', 'crib', 'bassinet', 'cot', 'sleepingbag')),
    ('food and drink', ('fridge', 'refrigerator', 'stove', 'oven', 'counter', 'grill',
                        'microwave', 'bar', 'coffee', 'espresso', 'juice', 'dishwasher',
                        'toaster', 'food', 'cake', 'meal', 'drink')),
    ('bathroom', ('toilet', 'shower', 'tub', 'bath', 'sink', 'mirror')),
    ('electronics', ('tv', 'television', 'computer', 'stereo', 'phone', 'radio',
                     'tablet', 'camera', 'console')),
    ('skills and fun', ('easel', 'bookcase', 'book', 'piano', 'guitar', 'violin',
                        'chess', 'workbench', 'weight', 'treadmill', 'telescope',
                        'microscope', 'woodwork', 'garden', 'plant', 'dartboard',
                        'arcade', 'toy', 'doll', 'activity', 'basketball')),
    ('doors and stairs', ('door', 'stair', 'gate', 'arch', 'elevator')),
)

_COMPASS = ('north', 'north-east', 'east', 'south-east',
            'south', 'south-west', 'west', 'north-west')

_DROP_WORDS = frozenset((
    'object', 'objects', 'debug', 'tuning', 'value', 'cheap', 'expensive',
    'generic', 'default', 'base', 'ep', 'gp', 'sp', 'pack',
))

# Short prefixes the tuning uses to say what KIND of thing a name refers to:
# s.gardenSalad is a single serving, pl.gardenSalad the plate of it. They are
# only prefixes, so they are dropped at the front of a name and nowhere else -
# a food genuinely called "O" should still be readable.
# Prefixes that really do appear on object TUNING names (o.fridgeBasic).
# Note these are not what {S.x}{P.x} in a catalog name is - that is a
# singular/plural pair, handled in dialogs.resolve_plurals.
_NAME_PREFIXES = frozenset(('o', 'ob', 'obj', 'gen'))


class Entry(object):
    """One scannable thing in the world."""

    __slots__ = ('obj', 'name', 'category', 'distance', 'bearing', 'level_delta',
                 'kind', 'detail')

    def __init__(self, obj, name, category, distance, bearing, level_delta,
                 kind='object', detail=None):
        self.kind = kind
        self.detail = detail
        self.obj = obj
        self.name = name
        self.category = category
        self.distance = distance
        self.bearing = bearing
        self.level_delta = level_delta

    def describe(self, include_category=False):
        if self.kind in ('phone', 'contact', 'item'):
            parts = [self.name]
            if self.detail:
                parts.append(self.detail)
            if include_category:
                parts.append('({})'.format(self.category))
            return ', '.join(parts)
        parts = [self.name]
        if include_category:
            parts.append('({})'.format(self.category))
        parts.append('{:.0f} metres {}'.format(self.distance, self.bearing))
        if self.level_delta > 0:
            parts.append('{} floor up'.format(self.level_delta))
        elif self.level_delta < 0:
            parts.append('{} floor down'.format(abs(self.level_delta)))
        return ', '.join(parts)


def _split_words(raw):
    """Split on separators and camelCase boundaries without needing the re module."""
    words = []
    current = []
    previous = ''
    for char in str(raw):
        if char in '_- .:':
            if current:
                words.append(''.join(current))
                current = []
            previous = char
            continue
        if char.isupper() and current and (previous.islower() or previous.isdigit()):
            words.append(''.join(current))
            current = []
        current.append(char)
        previous = char
    if current:
        words.append(''.join(current))
    return words


def prettify(raw):
    """Turn a tuning class name such as chairDining_Value into 'chair dining'."""
    if not raw:
        return 'object'
    words = _split_words(raw)
    kept = [w for w in words if w.lower() not in _DROP_WORDS and not w.isdigit()]
    while len(kept) > 1 and kept[0].lower() in _NAME_PREFIXES:
        kept = kept[1:]
    # Any remaining single letter is a prefix too, but keep one if it is all
    # that is left rather than returning nothing.
    if any(len(w) > 1 for w in kept):
        kept = [w for w in kept if len(w) > 1]
    if not kept:
        kept = words
    return ' '.join(kept).lower() or 'object'


# Words that only mean something to the tuning system. "sit passive" and
# "Dance active" are not things a player needs read aloud.
_INTERACTION_NOISE = frozenset((
    'passive', 'active', 'autonomous', 'auto', 'mixer', 'si', 'super',
    'interaction', 'generic', 'loop', 'variant', 'phase', 'tuning',
    'nonsocial', 'copy', 'clone', 'version', 'targeted', 'basic',
))


def prettify_interaction(raw):
    """Like prettify, but also strips interaction tuning jargon."""
    words = [w for w in prettify(raw).split()
             if w not in _INTERACTION_NOISE]
    if not words:
        return prettify(raw)
    return ' '.join(words)


def tuning_name(obj):
    for getter in (lambda: type(obj).__name__,
                   lambda: obj.definition.name,
                   lambda: obj.definition.cls.__name__):
        try:
            value = getter()
            if value:
                return str(value)
        except Exception:
            continue
    return 'object'


_name_stats = {'catalog': 0, 'tag': 0, 'tuning': 0}


def _tag_label(obj):
    """Build/buy category words, used when the catalog name is missing."""
    try:
        tags = obj.definition.get_tags()
    except Exception:
        return None
    for tag in tags or ():
        raw = getattr(tag, 'name', None)
        if not raw:
            continue
        label = prettify(raw)
        if label and label != 'object':
            return label
    return None


def object_name(obj):
    """Real catalog name if we have it, then build/buy tags, then tuning.

    The catalog name is GameObject.catalog_name - a LocalizedString on the
    OBJECT. Definition.catalog_name_key does not exist in this build, so every
    object was falling through to its tuning name ("grill genhome1x1").
    """
    import a11yscan_dialogs as dialogs
    for getter in (lambda: obj.catalog_name,
                   lambda: obj.definition.catalog_name_key):
        try:
            value = getter()
        except Exception:
            continue
        if value is None:
            continue
        try:
            text = dialogs.loc_text(value)
        except Exception:
            text = None
        if not text and isinstance(value, int):
            # Straight from the string table, so it still holds whatever the
            # localisers wrote - including {S.singular}{P.plural} pairs.
            text = names.lookup(value)
            if text:
                text = dialogs.resolve_plurals(text)
        if text:
            _name_stats['catalog'] += 1
            return text
    # The object had nothing, so ask its definition - build_buy knows the name
    # the client would print for it, and that beats guessing from tags.
    try:
        text = catalog_name_text(getattr(obj.definition, 'id', None))
    except Exception:
        text = None
    if text:
        _name_stats['catalog'] += 1
        return text
    label = _tag_label(obj)
    if label:
        _name_stats['tag'] += 1
        return label
    _name_stats['tuning'] += 1
    return prettify(tuning_name(obj))


def name_stats():
    return dict(_name_stats)


def reset_name_stats():
    for key in _name_stats:
        _name_stats[key] = 0


def active_sim():
    import services
    try:
        sim = services.get_active_sim()
        if sim is not None:
            return sim
    except Exception:
        pass
    try:
        return services.client_manager().get_first_client().active_sim
    except Exception:
        return None


def _iter_objects():
    import services
    try:
        manager = services.object_manager()
    except Exception as ex:
        speech.log('object_manager unavailable ({!r})'.format(ex))
        return []
    for attr in ('get_valid_objects_gen', 'valid_objects', 'values'):
        try:
            fn = getattr(manager, attr, None)
            if fn is not None:
                return list(fn())
        except Exception:
            continue
    try:
        return list(manager)
    except Exception:
        return []


def _iter_sims(exclude):
    import services
    try:
        manager = services.sim_info_manager()
    except Exception:
        return []
    for attr in ('instanced_sims_on_active_lot_gen', 'instanced_sims_gen'):
        try:
            fn = getattr(manager, attr, None)
            if fn is not None:
                return [s for s in fn() if s is not exclude]
        except Exception:
            continue
    return []


def player_affordances(obj):
    """Static affordances a player could plausibly click, minus debug and cheats."""
    raw = ()
    try:
        candidate = getattr(obj, 'super_affordances', None)
        raw = candidate() if callable(candidate) else (candidate or ())
    except Exception:
        raw = ()
    if not raw:
        try:
            raw = getattr(obj.definition, 'super_affordances', ()) or ()
        except Exception:
            raw = ()
    out = []
    for aff in raw:
        try:
            if getattr(aff, 'debug', False) or getattr(aff, 'cheat', False):
                continue
            if not getattr(aff, 'allow_user_directed', True):
                continue
            out.append(aff)
        except Exception:
            continue
    return out


def _bearing(dx, dz):
    angle = math.degrees(math.atan2(dx, dz)) % 360.0
    return _COMPASS[int(((angle + 22.5) % 360.0) // 45)]


def sim_name(sim):
    for getter in (lambda: '{} {}'.format(sim.sim_info.first_name, sim.sim_info.last_name),
                   lambda: '{} {}'.format(sim.first_name, sim.last_name)):
        try:
            name = getter().strip()
            if name:
                return name
        except Exception:
            continue
    return 'a Sim'


def motives(sim):
    """[(name, percent)] for the Sim's needs, most urgent first."""
    out = []
    try:
        tracker = sim.sim_info.commodity_tracker
    except Exception:
        return out
    stats = None
    for attr in ('get_all_commodities', '_statistics'):
        try:
            candidate = getattr(tracker, attr, None)
            if candidate is not None:
                stats = list(candidate() if callable(candidate) else candidate)
                break
        except Exception:
            continue
    if stats is None:
        try:
            stats = list(tracker)
        except Exception:
            return out
    for stat in stats:
        try:
            raw = type(stat).__name__
            if 'motive' not in raw.lower():
                continue
            value = stat.get_value()
            low = float(stat.min_value)
            high = float(stat.max_value)
            if high <= low:
                continue
            percent = (float(value) - low) / (high - low) * 100.0
            out.append((prettify(raw), percent))
        except Exception:
            continue
    out.sort(key=lambda item: item[1])
    return out


_wants_debug = []


def _want_label(item, dialogs, depth=0, info=None):
    """Whims arrive in several shapes across builds and mods; try them all."""
    if item is None or depth > 3:
        return None
    if isinstance(item, (tuple, list)):
        for member in item:
            label = _want_label(member, dialogs, depth + 1, info)
            if label:
                return label
        return None
    # The WhimGoal protobuf names its fields whim_name / whim_fluff_text,
    # not name, which is why this used to come back empty.
    for attr in ('whim_name', 'whim_fluff_text', 'name', 'text',
                 'display_name', 'title'):
        try:
            label = dialogs.text_for_sim(getattr(item, attr, None), info)
            if label:
                return label
        except Exception:
            continue
    # SituationGoal and friends expose it behind a method.
    for getter in (lambda: item.get_display_name(),
                   lambda: item.display_data.name,
                   lambda: item.get_display_text()):
        try:
            label = dialogs.text_for_sim(getter(), info)
            if label:
                return label
        except Exception:
            continue
    goal = getattr(item, 'goal', None)
    if goal is not None and goal is not item:
        return _want_label(goal, dialogs, depth + 1, info)
    return None


def wants(sim):
    """The Sim's current wants, as readable text."""
    global _wants_debug
    _wants_debug = []
    info = getattr(sim, 'sim_info', None) or sim
    raw = None
    for label, getter in (('current_whims', lambda: info.current_whims),
                          ('whim_tracker.get_active_whims',
                           lambda: info.whim_tracker.get_active_whims()),
                          ('_current_whims', lambda: info._current_whims)):
        try:
            value = getter()
            _wants_debug.append('{} -> {}'.format(label, type(value).__name__))
            if value:
                raw = list(value)
                break
        except Exception as ex:
            _wants_debug.append('{} failed {!r}'.format(label, ex))
    if not raw:
        return []

    import a11yscan_dialogs as dialogs
    out = []
    for item in raw:
        try:
            # Protobufs print as readable text, which shows every set field.
            _wants_debug.append('item {}: {}'.format(
                type(item).__name__, str(item).replace(chr(10), ' | ')[:240]))
        except Exception:
            pass
        label = _want_label(item, dialogs, 0, info)
        if label:
            out.append(label)
    return out


def wants_debug():
    return list(_wants_debug)


_emotion_debug = []


def _buff_component(sim):
    info = getattr(sim, 'sim_info', None) or sim
    for holder in (info, sim):
        for attr in ('Buffs', 'buff_component'):
            try:
                component = getattr(holder, attr, None)
                if component is not None:
                    return component
            except Exception:
                continue
    return None


def emotion(sim):
    """(mood, intensity, [(cause, weight, drives_mood, reason)]).

    The active mood lives on the buff component, and every buff carries the
    mood it pushes towards plus how strongly, which is what lets us say why
    a Sim feels the way they do rather than just what they feel.
    """
    global _emotion_debug
    _emotion_debug = []
    import a11yscan_dialogs as dialogs

    component = _buff_component(sim)
    if component is None:
        _emotion_debug.append('no buff component')
        return (None, None, [])

    mood = getattr(component, '_active_mood', None)
    intensity = getattr(component, '_active_mood_intensity', None)
    mood_label = None
    if mood is not None:
        for getter in (lambda: dialogs.loc_text(mood.buff_name),
                       lambda: dialogs.loc_text(mood.mood_name),
                       lambda: prettify(getattr(mood, '__name__', '')
                                        or type(mood).__name__)):
            try:
                mood_label = getter()
                if mood_label:
                    break
            except Exception:
                continue
    _emotion_debug.append('mood={!r} intensity={!r}'.format(mood_label, intensity))

    causes = []
    try:
        buffs = list(component)
    except Exception as ex:
        _emotion_debug.append('buff iteration failed {!r}'.format(ex))
        buffs = []
    for buff in buffs:
        try:
            weight = getattr(buff, 'mood_weight', 0) or 0
            if not weight:
                continue
            if getattr(buff, 'visible', True) is False:
                continue
            info = getattr(sim, 'sim_info', None) or sim
            label = None
            for getter in (lambda: dialogs.text_for_sim(buff.buff_name, info),
                           lambda: prettify(type(buff).__name__)):
                try:
                    label = getter()
                    if label:
                        break
                except Exception:
                    continue
            reason = None
            for getter in (lambda: dialogs.text_for_sim(buff.reason, info),
                           lambda: dialogs.text_for_sim(buff.buff_description,
                                                        info)):
                try:
                    reason = getter()
                    if reason:
                        break
                except Exception:
                    continue
            mood_type = getattr(buff, 'mood_type', None)
            causes.append((label or 'something', int(weight),
                           mood is not None and mood_type is mood, reason))
        except Exception:
            continue
    causes.sort(key=lambda item: (not item[2], -item[1]))
    _emotion_debug.append('{} causes'.format(len(causes)))
    return (mood_label, intensity, causes)


def emotion_debug():
    return list(_emotion_debug)


def home_info():
    """(home_zone_id, lot_id, world_id, already_home) for the active household."""
    import services
    try:
        household = services.active_household()
        home_zone = household.home_zone_id
    except Exception as ex:
        speech.log('no active household ({!r})'.format(ex))
        return (None, None, None, False)
    if not home_zone:
        return (None, None, None, False)

    lot_id = world_id = None
    try:
        persistence = services.get_persistence_service()
        lot_id = persistence.get_lot_id_from_zone_id(home_zone)
        world_id = persistence.get_world_id_from_zone(home_zone)
    except Exception as ex:
        speech.log('home lot lookup failed ({!r})'.format(ex))

    already = False
    try:
        already = services.current_zone_id() == home_zone
    except Exception:
        already = False
    return (home_zone, lot_id, world_id, already)


# Go Home is a client UI button, not a server interaction: it appears neither
# on the phone nor in the street pie menu. The street's travel entry is the
# real entry point, and it opens a picker we can already navigate.
_HOME_WORDS = ('go home', 'head home', 'return home', 'travel home')
_TRAVEL_ENTRY_WORDS = ('travel with', 'travel')


def _find_street_position(sim, log):
    """A position the game agrees is street, found with its own test."""
    try:
        import terrain
        import sims4.math
        origin = sim.position
    except Exception as ex:
        log('go home: terrain unavailable ({!r})'.format(ex))
        return None
    for radius in range(4, 64, 4):
        for step in range(16):
            angle = step * (math.pi / 8.0)
            point = sims4.math.Vector3(
                float(origin.x) + radius * math.cos(angle),
                float(origin.y),
                float(origin.z) + radius * math.sin(angle))
            try:
                if terrain.is_position_in_street(point):
                    log('go home: street position {}m away'.format(radius))
                    return point
            except Exception:
                continue
    log('go home: no street within 64m')
    return None


_TERRAIN_REFERENCE_ID = 91102


def travel_menu():
    """Start the Sim's own Travel interaction.

    The flow is entirely dialog-driven, so it is fully readable: a UiSimPicker
    for companions, then a UiMapViewPicker holding every destination. The map
    picker IS a dialog - opening the map from the street pie menu never reached
    it, which is why travel looked client-only for so long.
    """
    import a11yscan_actions as actions
    import a11yscan_log as logfile

    sim = active_sim()
    if sim is None:
        return 'No active Sim.'
    try:
        choices = actions.choices_for(sim)
    except Exception as ex:
        logfile.fail('travel: self interactions failed ({!r})'.format(ex))
        return 'Could not open travel.'

    for choice in choices:
        label = choice.label.strip().lower().rstrip('.')
        if label in ('travel', 'travel with') or label.startswith('travel'):
            if ':' in choice.label:
                continue  # a mod's own trip, not the game's travel
            logfile.write('travel: running {!r}'.format(choice.label))
            if actions.run(choice, sim):
                logfile.ok('travel opened via {!r}'.format(choice.label))
                return 'Travel. Choose who comes, then the destination.'
            logfile.fail('travel: {!r} would not run'.format(choice.label))
    logfile.fail('travel: no travel interaction offered')
    return 'No travel option right now.'


def home_name():
    """The name of the lot your household calls home, or None.

    Worth being able to check. A go-home that quietly travels to the wrong
    zone is indistinguishable from one that worked until you arrive, and by
    then you are somewhere else entirely.
    """
    home_zone, _lot_id, _world_id, _already = home_info()
    if not home_zone:
        return None
    try:
        import a11yscan_lots as lots
        for entry in lots.survey():
            if entry.get('zone_id') == home_zone:
                return '{}, in {}'.format(entry['name'], entry['world'])
    except Exception as ex:
        logfile.write('home: could not name zone {} ({!r})'.format(
            home_zone, ex))
    return 'zone {}'.format(home_zone)


def go_home():
    """Travel home by running the game's own go-home interaction.

    It lives on the Sim itself (tuned as an "aggregate" interaction), not on
    the phone and not in the street pie menu. Several rounds were lost looking
    for it in the wrong places, and one was lost matching the bare word
    "travel", which ran a mod's trip to a convenience store instead.

    Never resurrect send_travel_switch_to_zone_op: it relocates the client but
    leaves the session with no active Sim.
    """
    import a11yscan_actions as actions
    import a11yscan_log as logfile

    home_zone, lot_id, world_id, already = home_info()
    sim = active_sim()
    if sim is None:
        return 'No active Sim.'

    try:
        choices = actions.choices_for(sim)
    except Exception as ex:
        logfile.fail('go home: self interactions failed ({!r})'.format(ex))
        return 'Could not travel home.'

    logfile.write('go home: self offers {} interactions'.format(len(choices)))
    # Exact phrase only. "travel" on its own matches mod trips to shops.
    matches = [c for c in choices if 'go home' in c.label.lower()]
    if not matches:
        for choice in choices:
            logfile.write('    self: {!r}'.format(choice.label))
        logfile.write('go home: the game is not offering it, travelling '
                      'home instead')
        # Go Home is only offered in some circumstances - a situation your Sim
        # is part of can take it away - and being unable to get home because
        # of that is exactly the kind of dead end this mod exists to remove.
        # There is now a travel route that does not need the interaction.
        if already:
            return 'You are already home.'
        if not home_zone:
            return 'Your household has no home lot to go to.'
        where = home_name() or 'zone {}'.format(home_zone)
        logfile.write('go home: travelling to {} (zone {})'.format(
            where, home_zone))
        try:
            import a11yscan_travel as travel
            spoken = travel.travel_to_zone(home_zone, where)
            return '{} Home is {}.'.format(spoken, where)
        except Exception as ex:
            logfile.fail('go home: travelling home failed ({!r})'.format(ex))
            return ('No go home option right now, and travelling home '
                    'failed. The log has the reason.')

    for choice in matches:
        # Record what this interaction actually is, whether or not we are
        # going to run it - the probe is the point of being here when the Sim
        # is already home. If its destination can be
        # retargeted, the same mechanism gives us an accessible travel picker
        # for every lot, which the client-side map cannot.
        try:
            affordance = choice.affordance
            logfile.write('go home: affordance {} bases={}'.format(
                getattr(affordance, '__name__', type(affordance).__name__),
                [b.__name__ for b in getattr(affordance, '__mro__', ())[:6]]))
            interesting = [a for a in dir(affordance)
                           if any(w in a.lower() for w in
                                  ('zone', 'lot', 'travel', 'destination',
                                   'world'))]
            logfile.write('go home: destination-ish attrs {}'.format(
                interesting[:16]))
            for attr in interesting[:16]:
                try:
                    logfile.write('    {} = {!r}'.format(
                        attr, getattr(affordance, attr))[:200])
                except Exception:
                    pass
        except Exception as ex:
            logfile.write('go home: affordance probe failed {!r}'.format(ex))
        if already:
            logfile.write('go home: already home, probed without running')
            continue
        logfile.write('go home: running {!r}'.format(choice.label))
        if actions.run(choice, sim):
            logfile.ok('go home via self interaction {!r}'.format(choice.label))
            return 'Going home.'
        logfile.fail('go home: {!r} would not run'.format(choice.label))
    if already:
        return 'Already at home. Travel interaction details written to the log.'
    return 'Go home was refused.'


def current_action(sim):
    """What the Sim is doing right now, as readable text."""
    for getter in (lambda: sim.queue.running,
                   lambda: next(iter(sim.si_state.sis), None)):
        try:
            running = getter()
            if running is None:
                continue
            affordance = getattr(running, 'affordance', None) or running
            raw = getattr(affordance, '__name__', None) or type(affordance).__name__
            if raw:
                return prettify_interaction(raw)
        except Exception:
            continue
    return None


_catalog_stats = {'catalog': 0, 'table': 0, 'shelf': 0, 'tag': 0,
                  'tuning': 0}


def catalog_stats():
    return dict(_catalog_stats)


def catalog_name_text(definition_id):
    """The name the game itself shows for a definition, or None.

    A definition carries no display string, but build_buy hands out the STBL
    key that the client resolves - and the mod ships that string table. This is
    the real catalog name, custom content included, so it is tried before the
    offline table and long before anything derived from a tuning name.
    """
    if not definition_id:
        return None
    try:
        import build_buy
        key = build_buy.get_object_catalog_name(definition_id)
    except Exception:
        return None
    if not key:
        return None
    text = names.lookup(key)
    if not text:
        return None
    # Catalog names are written {S.Lamp}{P.Lamps} for the client to choose
    # between; one item at a time means the singular.
    try:
        import a11yscan_dialogs as dialogs
        text = dialogs.resolve_plurals(text, 1)
    except Exception:
        pass
    text = (text or '').strip()
    return text or None


def definition_tags(definition):
    """Build/buy tag names for a definition, however the game hands them over.

    get_tags() returns Tag members on most objects and nothing at all on some,
    so build_buy is asked directly as well; that call answers with raw ints,
    which the Tag enum turns back into names.
    """
    out = []
    raw_tags = None
    try:
        raw_tags = definition.get_tags()
    except Exception:
        raw_tags = None
    if not raw_tags:
        try:
            import build_buy
            raw_tags = build_buy.get_object_all_tags(definition.id)
        except Exception:
            raw_tags = None
    for tag in raw_tags or ():
        name = getattr(tag, 'name', None)
        if name is None:
            try:
                from tag import Tag
                name = Tag(tag).name
            except Exception:
                name = None
        if name:
            out.append(str(name))
    return out


def _func_sections(tag_names):
    """The Func_ tag, split into its sections.

    Func_Surfaces_Counters is buy mode's "surfaces, counters" shelf. The
    longest tag wins: a bare Func_Decorations says less than
    Func_Decorations_Paintings.
    """
    best = None
    for raw in tag_names:
        if not raw.lower().startswith('func_'):
            continue
        parts = [p for p in raw.split('_')[1:] if p]
        if not parts:
            continue
        if best is None or len(parts) > len(best):
            best = parts
    return best


def definition_tag_label(definition):
    """A last-resort name from the object's own tags."""
    sections = _func_sections(definition_tags(definition))
    if not sections:
        return None
    label = prettify(sections[-1])
    return label if label and label != 'object' else None


# Buy mode's four catalog groups, as the Tag enum spells them.
_BUY_GROUPS = {
    'buycatss': 'furniture',
    'buycatee': 'electronics and fun',
    'buycatld': 'lighting and decor',
    'buycatpa': 'plumbing and appliances',
}

# The bare BuyCat_ prefix is mostly venue and collection filtering - tags that
# say where an object may appear, not what shelf it sits on. Only the ones that
# really are shelves are listed; anything else there is ignored on purpose.
_BUY_SINGLES = {
    'painting': 'lighting and decor, paintings',
    'easel': 'electronics and fun, easels',
    'instrument': 'electronics and fun, instruments',
    'columns': 'building, columns',
    'windows': 'building, windows',
    'spanrelsfriezestrim': 'building, trim',
    'cleanpower': 'plumbing and appliances, power',
}

# build_buy.get_object_buy_category_flags answers in these bits. Coarser than a
# shelf, but it is the game's own answer and beats guessing from a name.
_BUY_FLAGS = (
    (2, 'appliances'), (4, 'electronics'), (8, 'entertainment'),
    (32, 'lighting'), (64, 'plumbing'), (128, 'decor'), (256, 'kids'),
    (512, 'storage'), (2048, 'comfort'), (4096, 'surfaces'),
    (8192, 'vehicles'),
)


def _buy_shelf(tag_names):
    """The catalog shelf this belongs on: "furniture, sofas" and the like."""
    found = []
    singles = []
    for raw in tag_names:
        head, _sep, rest = raw.partition('_')
        if not rest:
            continue
        group = _BUY_GROUPS.get(head.lower())
        if group:
            found.append((group, rest))
        elif head.lower() == 'buycat':
            shelf = _BUY_SINGLES.get(rest.lower().replace('_', ''))
            if shelf:
                singles.append(shelf)
    if found:
        # Objects carry several of these - a double bed is tagged Bed and
        # BedDouble - so pick deterministically, or the same object lands on a
        # different shelf each time the catalog is built. Shortest wins, which
        # also keeps the double beds filed with the beds.
        found.sort(key=lambda pair: (len(pair[1]), pair[1]))
        group, shelf = found[0]
        return '{}, {}'.format(group, prettify(shelf))
    if singles:
        return sorted(singles)[0]
    return None


def _buy_flag_category(definition_id):
    """Buy mode's top-level tab, when no shelf tag says anything better."""
    if not definition_id:
        return None
    try:
        import build_buy
        flags = int(build_buy.get_object_buy_category_flags(definition_id))
    except Exception:
        return None
    for bit, label in _BUY_FLAGS:
        if flags & bit:
            return label
    return None


def definition_category(definition, label):
    """Which shelf of buy mode this belongs on.

    The game's own answer first, at the same granularity the catalog uses.
    Keyword matching on the name is only the last resort.
    """
    shelf = _buy_shelf(definition_tags(definition))
    if shelf:
        return shelf
    tab = _buy_flag_category(getattr(definition, 'id', None))
    if tab:
        return tab
    return categorize(label + ' ' + str(getattr(definition, 'name', '')))


def definition_name(definition):
    """Catalog name for a definition, falling back to its tuning name."""
    definition_id = getattr(definition, 'id', None)
    text = catalog_name_text(definition_id)
    if text:
        _catalog_stats['catalog'] += 1
        return text
    try:
        text = objectnames.lookup(definition_id)
        if text:
            _catalog_stats['table'] += 1
            return text
    except Exception:
        pass
    # The tuning name comes before any tag word. "fridgeBasic" reads as
    # "fridge basic", which says what the thing is; the Func tag says
    # "appliance", which hundreds of unrelated objects also say.
    try:
        text = prettify(definition.name)
    except Exception:
        text = None
    if text and text != 'object':
        _catalog_stats['tuning'] += 1
        return text
    shelf = _buy_shelf(definition_tags(definition))
    if shelf:
        _catalog_stats['shelf'] += 1
        # "plumbing and appliances, refrigerators" as a name would be silly;
        # the shelf on its own is the useful half.
        return shelf.split(', ')[-1]
    label = definition_tag_label(definition)
    if label:
        _catalog_stats['tag'] += 1
        return label
    _catalog_stats['tuning'] += 1
    return 'object'


# Placeholders that are technically buyable and never worth buying. They are
# the most repeated names in the catalog, so they cost real browsing time.
_JUNK_NAMES = ('debug', 'public spawner', 'placeholder', 'do not use',
               'donotuse', 'test object')


def variant_group(definition_id):
    """The game's own id tying a definition to its colour variants, or None."""
    if not definition_id:
        return None
    try:
        import build_buy
        group = build_buy.get_variant_group_id(definition_id)
    except Exception:
        return None
    try:
        group = int(group)
    except (TypeError, ValueError):
        return None
    # 0 means "no group", which is not the same as "its own group of one".
    return group or None


def swatch_key(definition, label, price):
    """What makes two definitions the same object in different colours.

    The variant group id is NOT enough on its own. It groups product families,
    not just colours: a series of books, a drawer of different underwear and
    seven differently-named condoms all share one group id. Keying on it alone
    collapsed 22,541 objects down to 3,966 and filed each survivor under
    whichever category most of its group voted for - so a bed could end up
    among the food.

    So the name and price decide, as they did before, and the group id only
    keeps two same-named objects from different families apart. Colour variants
    still collapse, because they share a name; things that merely ship together
    stay separate, because they do not read alike.
    """
    return ('swatch', variant_group(getattr(definition, 'id', None)) or 0,
            label.lower(), int(price))


def catalog_worth_listing(label):
    """False for debug and spawner objects masquerading as furniture."""
    if not label:
        return False
    lowered = label.lower()
    for junk in _JUNK_NAMES:
        if junk in lowered:
            return False
    return True


def collapse_swatches(entries):
    """Pick the one entry that stands for a group of colour variants.

    Category by majority: swatches occasionally carry slightly different tags,
    and letting one stray swatch file the object on a second shelf is exactly
    the duplicate this is meant to remove. Ties break alphabetically so the
    answer does not depend on definition order.

    Within the winning category the lowest definition id wins, which keeps the
    catalog stable between openings.
    """
    counts = {}
    names = set()
    for _label, _price, category, _definition in entries:
        counts[category] = counts.get(category, 0) + 1
        names.add(_label.lower())
    if len(counts) > 1:
        # Colour variants of one object should agree on which shelf they are
        # on. When they do not, the majority vote below decides, and the
        # minority quietly moves shelf - worth seeing rather than guessing at.
        import a11yscan_log as logfile
        logfile.write('catalog: {!r} variants disagree on category: {}'.format(
            sorted(names)[0] if names else '?',
            ', '.join(sorted(counts))))
    category = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[0][0]
    same = [e for e in entries if e[2] == category]
    same.sort(key=lambda e: int(getattr(e[3], 'id', 0) or 0))
    label, price, _category, definition = same[0]
    return label, price, category, definition


def catalog(limit=40000):
    """Purchasable object definitions, grouped by build/buy category.

    Definitions have no display name at runtime, so names come from the table
    built offline from OBJD resources; anything unnamed falls back to its
    tuning name rather than being hidden.
    """
    import a11yscan_log as logfile
    global _catalog_stats
    _catalog_stats = {'catalog': 0, 'table': 0, 'shelf': 0, 'tag': 0,
                      'tuning': 0}
    try:
        import services
        manager = services.definition_manager()
    except Exception as ex:
        logfile.fail('catalog: no definition manager ({!r})'.format(ex))
        return {}

    definitions = None
    for attr in ('loaded_definitions', 'types', 'values'):
        try:
            candidate = getattr(manager, attr, None)
            if candidate is None:
                continue
            definitions = list(candidate() if callable(candidate) else candidate)
            if definitions:
                logfile.write('catalog: {} definitions via {}'.format(
                    len(definitions), attr))
                break
        except Exception:
            continue
    if not definitions:
        logfile.fail('catalog: could not enumerate definitions')
        return {}

    import time
    started = time.monotonic()
    groups = {}
    considered = 0
    for definition in definitions:
        try:
            price = getattr(definition, 'price', 0) or 0
            if price <= 0:
                continue  # not purchasable
            considered += 1
            if considered > limit:
                break
            label = definition_name(definition)
            if not catalog_worth_listing(label):
                continue
            category = definition_category(definition, label)
            # One object, many swatches, one entry. See collapse_swatches.
            groups.setdefault(swatch_key(definition, label, price), []).append(
                (label, int(price), category, definition))
        except Exception:
            continue

    buckets = {}
    for entries in groups.values():
        label, price, category, definition = collapse_swatches(entries)
        buckets.setdefault(category, []).append((label, price, definition))
    collapsed = considered - sum(len(v) for v in buckets.values())
    for entries in buckets.values():
        entries.sort(key=lambda item: item[0])
    logfile.write('catalog: {} buyable, {} listed after collapsing {} '
                  'swatches, {} categories, names {}, took {:.1f}s'.format(
                      considered, sum(len(v) for v in buckets.values()),
                      collapsed, len(buckets), _catalog_stats,
                      time.monotonic() - started))
    # The biggest shelves are the ones worth splitting further next time.
    biggest = sorted(buckets.items(), key=lambda pair: -len(pair[1]))[:8]
    logfile.write('catalog: largest categories {}'.format(
        ', '.join('{} ({})'.format(name, len(items)) for name, items in biggest)))
    # A name shared by dozens of objects is a name that tells you nothing, so
    # the worst offenders are worth naming in the log.
    repeats = {}
    for entries in buckets.values():
        for entry in entries:
            repeats[entry[0]] = repeats.get(entry[0], 0) + 1
    shared = sorted((count, name) for name, count in repeats.items()
                    if count >= 10)[-8:]
    if shared:
        logfile.write('catalog: names shared by many objects {}'.format(
            ', '.join('{} ({})'.format(name, count)
                      for count, name in reversed(shared))))
    return buckets


def phone_entry(sim):
    """The phone as a focusable thing; its menu comes from the game's own
    potential_phone_interactions, the same source the phone icon uses."""
    return Entry(sim, 'Phone', PHONE, 0.0, 'here', 0, kind='phone')


def household_inventory_entries():
    """Items in the HOUSEHOLD inventory, which is a separate store.

    A Sim's inventory_component is not the only place things land. Shop
    deliveries and anything sold to the household go here instead, so a
    purchase that plainly succeeded looked like it had vanished.

    These are not instanced objects - the household inventory holds object
    DATA - so they can be listed but not interacted with from here.
    """
    out = []
    try:
        import build_buy
        import services
        household = services.active_household()
        household_id = getattr(household, 'id', None)
        if not household_id:
            return out
        object_ids = list(
            build_buy.get_object_ids_in_household_inventory(household_id) or ())
    except Exception as ex:
        speech.log('household inventory unavailable ({!r})'.format(ex))
        return out
    counts = {}
    for object_id in object_ids:
        try:
            definition_id = build_buy.get_definition_id_in_household_inventory(
                object_id, household_id)
            # Not necessarily a plain int - using it as a dict key raised
            # TypeError('unhashable object'), which propagated out of the
            # inventory provider and lost the Sim's own items too.
            definition_id = int(definition_id) if definition_id else None
        except Exception:
            continue
        if definition_id:
            counts[definition_id] = counts.get(definition_id, 0) + 1
    for definition_id, count in counts.items():
        name = None
        try:
            import services as _services
            definition = _services.definition_manager().get(definition_id)
            if definition is not None:
                name = definition_name(definition)
        except Exception:
            name = None
        if not name:
            name = objectnames.lookup(definition_id) or 'item'
        detail = 'in household storage'
        if count > 1:
            detail = '{} of them, in household storage'.format(count)
        out.append(Entry(None, name, INVENTORY, 0.0, 'inventory', 0,
                         kind='household_item', detail=detail))
    speech.log('household inventory: {} distinct items'.format(len(out)))
    return out


def inventory_entries(sim):
    """Items in your Sim's inventory, so they can be used without the panel."""
    out = []
    component = None
    try:
        component = getattr(sim, 'inventory_component', None)
    except Exception:
        component = None
    if component is None:
        return out
    items = None
    for getter in (lambda: list(component),
                   lambda: list(component._storage),
                   lambda: list(component.objects)):
        try:
            items = getter()
            if items:
                break
        except Exception:
            continue
    for item in items or ():
        try:
            detail = None
            count = getattr(item, 'stack_count', None)
            if callable(count):
                count = count()
            if count and int(count) > 1:
                detail = '{} of them'.format(int(count))
            name = object_name(item)
            # Inventory names have been read out with tuning prefixes still
            # attached, and only the spoken text showed it - the log recorded
            # counts. Record where each name came from so a bad one can be
            # traced to its source instead of guessed at.
            try:
                import a11yscan_log as _log
                _log.write('inventory item: name={!r} tuning={!r} '
                           'catalog={!r}'.format(
                               name, tuning_name(item),
                               getattr(item, 'catalog_name', None)))
            except Exception:
                pass
            out.append(Entry(item, name, INVENTORY, 0.0,
                             'inventory', 0, kind='item', detail=detail))
        except Exception:
            continue
    try:
        out.extend(household_inventory_entries())
    except Exception as ex:
        speech.log('household inventory skipped ({!r})'.format(ex))
    out.sort(key=lambda entry: entry.name)
    return out


_contacts_debug = []


def _sim_id_of(info):
    for attr in ('sim_id', 'id'):
        try:
            value = getattr(info, attr, None)
            if value:
                return value
        except Exception:
            continue
    return None


def contact_entries(sim):
    """Sims yours knows, so they can be contacted without the relationship panel."""
    global _contacts_debug
    _contacts_debug = []
    out = []
    try:
        tracker = sim.sim_info.relationship_tracker
    except Exception as ex:
        _contacts_debug.append('no relationship_tracker {!r}'.format(ex))
        return out

    import services
    try:
        manager = services.sim_info_manager()
    except Exception:
        manager = None

    infos = None
    # get_target_sim_infos is the accessor the game itself uses; iterating the
    # tracker directly does not give you the other Sim.
    for label, getter in (
            ('get_target_sim_infos', lambda: list(tracker.get_target_sim_infos())),
            ('target_sim_gen', lambda: [
                (item if hasattr(item, 'first_name')
                 else (manager.get(item) if manager is not None else None))
                for item in tracker.target_sim_gen()]),
    ):
        try:
            candidate = [i for i in getter() if i is not None]
            _contacts_debug.append('{} -> {} entries'.format(label, len(candidate)))
            if candidate:
                infos = candidate
                break
        except Exception as ex:
            _contacts_debug.append('{} failed {!r}'.format(label, ex))
    if not infos:
        return out

    seen = set()
    for info in infos:
        try:
            sim_id = _sim_id_of(info)
            if sim_id in seen:
                continue
            seen.add(sim_id)
            name = '{} {}'.format(getattr(info, 'first_name', ''),
                                  getattr(info, 'last_name', '')).strip()
            # What the relationship IS, not just how deep it is. Depth is
            # kept as the fallback for a Sim with no bit yet.
            detail = None
            try:
                import a11yscan_relations as relations
                headline = relations._headline(tracker, sim_id)
                tracks = relations._tracks_for(tracker, sim_id)
                bits = []
                if headline:
                    bits.append(headline)
                for raw, value in tracks:
                    lowered = raw.lower()
                    if 'friendship' in lowered:
                        bits.append('friendship {}'.format(value))
                    elif 'romance' in lowered and value:
                        bits.append('romance {}'.format(value))
                detail = ', '.join(bits) or None
            except Exception as ex:
                _contacts_debug.append('relationship read failed {!r}'.format(ex))
            if detail is None:
                for getter in (lambda: tracker.get_relationship_depth(sim_id),
                               lambda: tracker.get_relationship_score(sim_id)):
                    try:
                        value = getter()
                        if value is not None:
                            detail = 'closeness {:.0f}'.format(float(value))
                            break
                    except Exception:
                        continue
            out.append(Entry(info, name or 'a Sim', CONTACTS, 0.0, 'known', 0,
                             kind='contact', detail=detail))
        except Exception as ex:
            _contacts_debug.append('entry failed {!r}'.format(ex))
            continue
    out.sort(key=lambda entry: entry.name)
    _contacts_debug.append('built {} contacts'.format(len(out)))
    return out


def contacts_debug():
    return list(_contacts_debug)


def categorize(label):
    lowered = label.lower()
    for category, keywords in _KEYWORDS:
        for word in keywords:
            if word in lowered:
                return category
    return OTHER


def scan(max_distance=40.0, require_interactions=True):
    """Return {category: [Entry, ...]} sorted near to far."""
    sim = active_sim()
    if sim is None:
        return {}
    try:
        origin = sim.position
        origin_level = int(getattr(sim, 'level', 0) or 0)
    except Exception as ex:
        speech.log('active Sim has no position ({!r})'.format(ex))
        return {}

    buckets = {}

    def add(obj, name, category, ignore_distance=False):
        try:
            pos = obj.position
            dx = float(pos.x) - float(origin.x)
            dz = float(pos.z) - float(origin.z)
        except Exception:
            return
        distance = math.sqrt(dx * dx + dz * dz)
        # Other Sims are never dropped for being far away: on a large lot they
        # can easily be past the object cutoff, and a Sim you cannot see in the
        # list is a Sim you cannot interact with at all.
        if distance > max_distance and not ignore_distance:
            return
        try:
            level_delta = int(getattr(obj, 'level', origin_level) or 0) - origin_level
        except Exception:
            level_delta = 0
        buckets.setdefault(category, []).append(
            Entry(obj, name, category, distance, _bearing(dx, dz), level_delta))

    # Your own Sim is a valid target: self-interactions live here, which is how
    # phone, inventory and similar reach the menu without clicking anything.
    buckets.setdefault(YOURSELF, []).append(
        Entry(sim, sim_name(sim), YOURSELF, 0.0, 'here', 0))

    buckets.setdefault(PHONE, []).append(phone_entry(sim))
    for provider, category in ((inventory_entries, INVENTORY),
                               (contact_entries, CONTACTS)):
        try:
            entries = provider(sim)
            if entries:
                buckets[category] = entries
        except Exception as ex:
            speech.log('{} provider failed ({!r})'.format(category, ex))

    others = _iter_sims(sim)
    try:
        import a11yscan_log as logfile
        logfile.write('scan: {} other instanced Sims found'.format(len(others)))
    except Exception:
        pass
    for other in others:
        add(other, sim_name(other), SIMS, ignore_distance=True)

    for obj in _iter_objects():
        try:
            if obj is sim or getattr(obj, 'is_sim', False):
                continue
            if callable(getattr(obj, 'is_in_inventory', None)) and obj.is_in_inventory():
                continue
        except Exception:
            continue
        if require_interactions and not player_affordances(obj):
            continue
        label = object_name(obj)
        # Categorise on tuning too: real catalog names often carry no keyword
        # at all, but the tuning name almost always does.
        add(obj, label, categorize('{} {}'.format(label, tuning_name(obj))))

    for entries in buckets.values():
        entries.sort(key=lambda e: e.distance)
    return buckets


def ordered_categories(buckets):
    """Categories that actually have contents, in a stable running order."""
    known = [c for c in CATEGORY_ORDER if buckets.get(c)]
    extra = sorted(c for c in buckets if c not in CATEGORY_ORDER and buckets[c])
    return known + extra


# The in-game week runs Sunday to Saturday; DateAndTime.day() returns 0-6 with
# 0 as Sunday, which is the same convention the notification tokens use.
DAY_NAMES = ('Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday',
             'Friday', 'Saturday')


def game_time():
    """The day and clock time in the game, or None if the clock is unreadable."""
    now = None
    for getter in (lambda: __import__('services').time_service().sim_now,
                   lambda: __import__('services').game_clock_service().now()):
        try:
            now = getter()
        except Exception:
            continue
        if now is not None:
            break
    if now is None:
        return None
    try:
        hours = int(now.hour())
        minutes = int(now.minute())
    except Exception:
        return None
    day = None
    try:
        day = DAY_NAMES[int(now.day()) % len(DAY_NAMES)]
    except Exception:
        day = None
    suffix = 'AM' if hours < 12 else 'PM'
    clock = '{}:{:02d} {}'.format(hours % 12 or 12, minutes, suffix)
    return '{} {}'.format(day, clock) if day else clock
