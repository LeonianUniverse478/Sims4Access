"""Relationship profiles: who your Sim knows, and everything the panel shows.

The relationship panel is a client screen, so it is rebuilt here from the
tracker the panel itself is drawn from. Everything it displays has an accessor:

    tracker.get_target_sim_infos()          who you know
    tracker.get_highest_priority_bit(id)    the headline - "Good Friends"
    tracker.get_all_bits(id)                every label, family ones included
    tracker.relationship_tracks_gen(id)     friendship and romance, with values
    tracker.get_knowledge(id)               what your Sim has learned about them
    tracker.get_compatibility_level(id)     how well suited, where tuned

The numbers run -100 to 100 on both tracks, which is not a useful thing to hear
on its own: 47 friendship means nothing until you know it is "friends". So each
value is read out as a word AND a number, the way the panel shows a bar with a
label.

The contact list already existed and gave a name and a closeness figure. That is
the same data the panel has, described worse - a name with no relationship on it
is exactly the readout that made a tester say the profiles do not read.
"""
import a11yscan_log as logfile

_entries = []
_index = 0
_active = False

# Where the game's own labels sit on the -100..100 scale. Read out with the
# number, never instead of it: the word is for orienting, the number is for
# knowing whether you are about to cross a threshold.
FRIENDSHIP_WORDS = (
    (-100, 'hated'), (-60, 'disliked'), (-30, 'on bad terms'),
    (-5, 'barely known'), (5, 'acquaintances'), (30, 'friends'),
    (60, 'good friends'), (85, 'best friends'),
)
ROMANCE_WORDS = (
    (-100, 'repulsed'), (-30, 'awkward'), (-5, 'nothing romantic'),
    (5, 'a spark'), (30, 'flirty'), (60, 'romantic'), (85, 'soulmates'),
)


def active():
    return _active


def _loc(value):
    try:
        import a11yscan_dialogs as dialogs
        return dialogs.loc_text(value)
    except Exception:
        return None


def _word_for(value, table):
    word = table[0][1]
    for threshold, label in table:
        if value >= threshold:
            word = label
    return word


def _sim_id(info):
    for attr in ('sim_id', 'id'):
        value = getattr(info, attr, None)
        if value:
            return value
    return None


def _name(info):
    name = '{} {}'.format(getattr(info, 'first_name', '') or '',
                          getattr(info, 'last_name', '') or '').strip()
    return name or 'a Sim'


def _tracks_for(tracker, sim_id):
    """[(name, value)] for every relationship track with this Sim.

    relationship_tracks_gen is what the panel's bars come from, so it finds
    pack tracks too. The named-track fallback exists because that generator has
    a different name in some builds and a silent empty list would read as "no
    relationship" for a married couple.
    """
    out = []
    try:
        for track in tracker.relationship_tracks_gen(sim_id):
            try:
                raw = type(track).__name__
                value = int(track.get_value())
            except Exception:
                continue
            out.append((raw, value))
    except Exception as ex:
        logfile.write('relations: tracks_gen failed ({!r})'.format(ex))
    if out:
        return out
    try:
        import a11yscan_cheats as cheats
        for name, stat in cheats._rel_tracks():
            try:
                value = int(tracker.get_relationship_score(sim_id, stat))
            except Exception:
                continue
            out.append((name, value))
    except Exception as ex:
        logfile.write('relations: named tracks failed ({!r})'.format(ex))
    return out


def _headline(tracker, sim_id):
    try:
        bit = tracker.get_highest_priority_bit(sim_id)
    except Exception:
        bit = None
    if bit is None:
        return None
    for attr in ('display_name', 'bit_name', 'display_name_gender_neutral'):
        text = _loc(getattr(bit, attr, None))
        if text:
            return text
    raw = getattr(bit, '__name__', None) or type(bit).__name__
    import a11yscan_world as world
    return world.prettify(raw.replace('RelationshipBit_', ''))


def _all_labels(tracker, sim_id, skip=None):
    """Every relationship label, which is where family relations live."""
    labels = []
    try:
        bits = list(tracker.get_all_bits(sim_id))
    except Exception as ex:
        logfile.write('relations: get_all_bits failed ({!r})'.format(ex))
        return labels
    import a11yscan_world as world
    for bit in bits:
        text = None
        for attr in ('display_name', 'bit_name'):
            text = _loc(getattr(bit, attr, None))
            if text:
                break
        if not text:
            raw = getattr(bit, '__name__', None) or type(bit).__name__
            text = world.prettify(raw.replace('RelationshipBit_', ''))
        if text and text != skip and text not in labels:
            labels.append(text)
    return labels


def _knowledge(tracker, sim_id):
    """What your Sim has actually learned about them, as the panel shows it."""
    facts = []
    try:
        knowledge = tracker.get_knowledge(sim_id)
    except Exception:
        knowledge = None
    if knowledge is None:
        return facts
    import a11yscan_world as world
    try:
        traits = list(getattr(knowledge, 'known_traits', None) or ())
        names = []
        for trait in traits:
            text = _loc(getattr(trait, 'display_name', None))
            if not text:
                text = world.prettify(getattr(trait, '__name__', '') or '')
            if text:
                names.append(text)
        if names:
            facts.append('traits you know: {}'.format(', '.join(names[:6])))
    except Exception as ex:
        logfile.write('relations: known traits failed ({!r})'.format(ex))
    try:
        career = getattr(knowledge, 'known_career', None) or getattr(
            knowledge, '_knows_career', None)
        if career:
            text = _loc(getattr(career, 'display_name', None)) or world.prettify(
                getattr(career, '__name__', '') or '')
            if text:
                facts.append('career you know about: {}'.format(text))
    except Exception:
        pass
    return facts


def load():
    """Build a profile for every Sim the active Sim has a relationship with."""
    global _entries, _index
    _entries = []
    _index = 0
    import a11yscan_world as world
    sim = world.active_sim()
    sim_info = getattr(sim, 'sim_info', None) if sim is not None else None
    if sim_info is None:
        logfile.write('relations: no active Sim')
        return 0
    try:
        tracker = sim_info.relationship_tracker
    except Exception as ex:
        logfile.fail('relations: no relationship tracker ({!r})'.format(ex))
        return 0
    try:
        others = list(tracker.get_target_sim_infos())
    except Exception as ex:
        logfile.fail('relations: could not list who they know ({!r})'.format(ex))
        return 0

    for other in others:
        sim_id = _sim_id(other)
        if sim_id is None:
            continue
        try:
            tracks = _tracks_for(tracker, sim_id)
            friendship = romance = None
            extra = []
            for raw, value in tracks:
                lowered = raw.lower()
                if 'friendship' in lowered and friendship is None:
                    friendship = value
                elif 'romance' in lowered and romance is None:
                    romance = value
                elif abs(value) > 5:
                    extra.append((world_words(raw), value))
            headline = _headline(tracker, sim_id)
            _entries.append({
                'name': _name(other),
                'info': other,
                'sim_id': sim_id,
                'headline': headline,
                'friendship': friendship,
                'romance': romance,
                'extra': extra,
                'labels': _all_labels(tracker, sim_id, skip=headline),
                'tracker': tracker,
            })
        except Exception as ex:
            logfile.write('relations: skipped a Sim ({!r})'.format(ex))
            continue
    # Closest first: who you care about is who you are looking for.
    _entries.sort(key=lambda e: -max(abs(e['friendship'] or 0),
                                     abs(e['romance'] or 0)))
    logfile.write('relations: {} profiles'.format(len(_entries)))
    return len(_entries)


def world_words(raw):
    import a11yscan_world as world
    return world.prettify(raw.replace('RelationshipTrack_', ''))


def summary(entry):
    """One line: who they are to you, with both numbers."""
    parts = [entry['name']]
    if entry['headline']:
        parts.append(entry['headline'])
    if entry['friendship'] is not None:
        parts.append('friendship {} ({})'.format(
            entry['friendship'],
            _word_for(entry['friendship'], FRIENDSHIP_WORDS)))
    if entry['romance'] is not None and (entry['romance'] or entry['headline']):
        parts.append('romance {} ({})'.format(
            entry['romance'], _word_for(entry['romance'], ROMANCE_WORDS)))
    return ', '.join(parts)


def profile(entry):
    """Everything the panel would show for this Sim."""
    lines = [summary(entry)]
    if entry['labels']:
        lines.append('also: {}'.format(', '.join(entry['labels'][:8])))
    for name, value in entry['extra']:
        lines.append('{} {}'.format(name, value))
    facts = _knowledge(entry['tracker'], entry['sim_id'])
    lines.extend(facts)
    if not facts:
        lines.append('your Sim has not learned anything about them yet')
    return '. '.join(lines) + '.'


def describe():
    if not _entries:
        return 'Nobody yet.'
    index = _index % len(_entries)
    return '{}. {} of {}.'.format(summary(_entries[index]), index + 1,
                                  len(_entries))


def open_menu():
    global _active
    if not load():
        return ('Your Sim does not know anybody yet, or the relationships '
                'could not be read. The log has the reason.')
    _active = True
    return ('Relationships. {} Sims, closest first. Up and down to browse, '
            'enter for the full profile, backspace to stop. {}'.format(
                len(_entries), describe()))


def close_menu():
    global _active
    _active = False
    return 'Relationships closed.'


def next_entry(step=1):
    global _index
    if not _entries:
        return 'Nobody yet.'
    _index = (_index + step) % len(_entries)
    return describe()


def activate():
    """Enter reads the whole profile. The list stays open."""
    if not _entries:
        return 'Nobody yet.'
    return profile(_entries[_index % len(_entries)])


def report():
    """Every profile as lines, for the console."""
    if not load():
        return ['nobody known, or the tracker could not be read']
    return [profile(entry) for entry in _entries]
