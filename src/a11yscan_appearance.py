"""Changing how a Sim looks, without the CAS screen.

CAS parts have no names. The game's own part picker
(interactions/base/cas_catalog_picker) builds its rows from thumbnails, tags
and a def_id - there is no display-name field anywhere, because CAS is meant to
be looked at. So a blind player cannot be given the labels CAS shows; there
aren't any.

What every part does carry is TAGS, and tags are words: hair colour, style,
age and gender fit, occasion. So each part is described by its tags. In some
ways that is more information than a thumbnail gives - "blonde, long, curly" is
a description, where the sighted player gets a picture and a guess.

The catalog itself comes from cas.cas.get_catalog_casparts_by_bodytype, the
same native the game's picker uses, so the parts offered are exactly the ones
valid for that Sim.
"""
import a11yscan_log as logfile

# Ordered so the parts people actually change come first. Resolved against the
# real BodyType enum at runtime, and anything missing is simply skipped.
BODY_TYPE_ORDER = (
    'HAIR', 'FACIAL_HAIR', 'EYEBROWS', 'TOP', 'BOTTOM', 'FULL_BODY', 'SHOES',
    'HAT', 'GLASSES', 'EARRINGS', 'NECKLACE', 'BRACELET', 'RING',
    'LIPSTICK', 'EYESHADOW', 'EYELINER', 'BLUSH', 'FACEPAINT',
    'SKINDETAIL_FRECKLES', 'TATTOO_ARM_LOWER_LEFT', 'SOCKS', 'GLOVES',
)

# Tag categories worth hearing, in the order they read best. Everything
# else - OCCULT, AGE, GENDER, SPECIES, pack markers, uniform and situation
# flags - says nothing about how a thing looks.
DESCRIBE_ORDER = (
    'HAIRLENGTH', 'HAIRSTYLE', 'HAIRCOLOR', 'COLOR', 'PATTERN', 'FABRIC',
    'STYLE', 'SLEEVE', 'NECKLINE', 'LENGTH', 'SKINTONE', 'MAKEUP',
    'FACIALHAIR', 'ACCESSORY', 'OUTFITCATEGORY',
)

# Tag values are run together, so spell out the ones that come up.
COMPOUNDS = {
    'hotweather': 'for hot weather', 'coldweather': 'for cold weather',
    'partywear': 'party', 'swimwear': 'swimwear', 'sleepwear': 'sleepwear',
    'athletic': 'athletic', 'everyday': 'everyday', 'career': 'work',
    'formalwear': 'formal', 'situationoutfit': 'special occasion',
    'lightblue': 'light blue', 'darkblue': 'dark blue',
    'lightbrown': 'light brown', 'darkbrown': 'dark brown',
    'lightgray': 'light grey', 'darkgray': 'dark grey', 'gray': 'grey',
    'shoulderlength': 'shoulder length', 'mediumlength': 'medium length',
    'verylong': 'very long', 'veryshort': 'very short',
}

_target = None
_shape_logged = False
_body_types = []
_body_index = 0
_parts = []
_part_index = 0


def active():
    return _target is not None


def _cas():
    import cas.cas as native
    return native


def _body_type_enum():
    from sims.outfits.outfit_enums import BodyType
    return BodyType


def _load_body_types():
    """The body types this build actually has, in a sensible order."""
    global _body_types, _body_index
    _body_types = []
    _body_index = 0
    try:
        enum = _body_type_enum()
    except Exception as ex:
        logfile.fail('look: BodyType unavailable ({!r})'.format(ex))
        return
    seen = set()
    for name in BODY_TYPE_ORDER:
        value = getattr(enum, name, None)
        if value is not None:
            _body_types.append((name.replace('_', ' ').lower(), value))
            seen.add(name)
    # Anything else the build offers, after the curated list.
    for name in sorted(dir(enum)):
        if name.startswith('_') or not name.isupper() or name in seen:
            continue
        value = getattr(enum, name, None)
        if value is None:
            continue
        _body_types.append((name.replace('_', ' ').lower(), value))
    logfile.write('look: {} body types available'.format(len(_body_types)))


def _tag_enum():
    try:
        from tag import Tag
        return Tag
    except Exception:
        return None


def _tag_words(tags):
    """Describe a part the way a person would.

    Tags arrive as integers and resolve to names like HAIRCOLOR_AUBURN,
    HAIRLENGTH_SHORT, OUTFITCATEGORY_HOTWEATHER, OCCULT_VAMPIRE. Read out whole
    that is six clauses of mostly nothing - "occult vampire" only means a
    vampire is allowed to wear it. So each tag is split into its category and
    value, the categories that describe how a thing LOOKS are kept, the rest are
    dropped, and what is left is ordered so it reads like English: a part tagged
    auburn and short becomes "short auburn".
    """
    found = {}
    enum = _tag_enum()
    for tag in tags or ():
        name = getattr(tag, 'name', None)
        if name is None and enum is not None:
            try:
                name = enum(tag).name
            except Exception:
                name = None
        if not name:
            continue
        if '.' in name:
            name = name.rsplit('.', 1)[-1]
        category, _sep, value = name.partition('_')
        if not value:
            category, value = '', name
        found.setdefault(category.upper(), []).append(value.lower())

    words = []
    for category in DESCRIBE_ORDER:
        values = found.get(category)
        if not values:
            continue
        # A garment tagged for one or two occasions is described by them; a
        # hair valid in five is not, so drop the noisy ones.
        if category == 'OUTFITCATEGORY' and len(values) > 2:
            continue
        for value in values[:2]:
            phrase = COMPOUNDS.get(value, value)
            if phrase and phrase not in words:
                words.append(phrase)
    return words[:4]


def _selected_sim_info():
    try:
        import services
        client = services.client_manager().get_first_client()
        if client is not None:
            info = getattr(client, 'active_sim_info', None)
            if info is not None:
                return info
        sim = services.get_active_sim()
        return getattr(sim, 'sim_info', None) if sim is not None else None
    except Exception:
        return None


def _collapse_variants(found):
    """One entry per look, not one per colour swatch.

    The catalog is asked with show_all_variants=True, so a hair that comes in
    24 colours arrives as 24 parts. Where the colour is in the tags they read
    differently and all 24 are worth keeping; where it is not, they are 24
    identical readouts and only the first is a real choice.

    Every part id in a group is kept, because the one the Sim already wears
    has to stay findable - see _mark_current - and it is the one that should
    represent its group when it is present.
    """
    groups = []
    at_words = {}
    for part, words in found:
        key = ' '.join(words)
        position = at_words.get(key)
        if position is None:
            at_words[key] = len(groups)
            groups.append([part, words, [part]])
            continue
        groups[position][2].append(part)
    return [(part, words, tuple(variants))
            for part, words, variants in groups]


def _load_parts():
    """Every part valid for this Sim at the current body type."""
    global _parts, _part_index
    _parts = []
    _part_index = 0
    if _target is None or not _body_types:
        return
    label, body_type = _body_types[_body_index % len(_body_types)]
    try:
        catalog = _cas().get_catalog_casparts_by_bodytype(
            sim_info=_target._base,
            include_tags=[],
            exclude_tags=[],
            bodytypes=[body_type],
            show_all_variants=True,
            rewards_parts=[])
    except Exception as ex:
        logfile.fail('look: catalog for {} failed ({!r})'.format(label, ex))
        return
    try:
        items = catalog.items()
    except Exception:
        items = [(part, ((), None)) for part in (catalog or ())]
    found = []
    global _shape_logged
    for part, extra in items:
        tags = ()
        try:
            tags = extra[0] if isinstance(extra, (tuple, list)) else extra
        except Exception:
            tags = ()
        if not _shape_logged:
            _shape_logged = True
            try:
                sample = list(tags)[:6]
                logfile.write(
                    'look: catalog entry part={!r} extra={!r} tags={!r} '
                    'resolved={!r}'.format(part, type(extra).__name__, sample,
                                           _tag_words(tags)))
            except Exception as ex:
                logfile.write('look: could not inspect a catalog entry ({!r})'.format(ex))
        found.append((part, _tag_words(tags)))
    _parts = _collapse_variants(found)
    _mark_current()
    logfile.write('look: {} parts for {}, {} colour variants folded in'.format(
        len(_parts), label, len(found) - len(_parts)))


def _worn_parts():
    """part id -> body type for the outfit the Sim has on."""
    worn = {}
    if _target is None:
        return worn
    try:
        category, index = _target.get_current_outfit()
        outfit = _target.get_outfit(category, index)
        part_ids = list(getattr(outfit, 'part_ids', None) or ())
        body_types = list(getattr(outfit, 'body_types', None) or ())
        for position, part in enumerate(part_ids):
            body = body_types[position] if position < len(body_types) else None
            worn[part] = body
    except Exception as ex:
        logfile.write('look: could not read the current outfit ({!r})'.format(ex))
    return worn


def _mark_current():
    """Start browsing at what the Sim already wears for this body type."""
    global _part_index
    worn = _worn_parts()
    if not worn:
        return
    for position, entry in enumerate(_parts):
        variants = entry[2]
        for candidate in variants:
            if candidate in worn:
                # Show the swatch actually on the Sim, not whichever of its
                # colours happened to come back first.
                _parts[position] = (candidate, entry[1], variants)
                _part_index = position
                logfile.write('look: currently wearing part {} at position '
                              '{}'.format(candidate, position + 1))
                return


def current_description():
    """What the Sim wears at the body type in view, in words."""
    if not _parts or not _body_types:
        return None
    worn = _worn_parts()
    for part, words, _variants in _parts:
        if part in worn:
            return ' '.join(words) if words else 'something with no tags'
    return None


def open_editor():
    global _target
    _target = _selected_sim_info()
    if _target is None:
        return 'No Sim is selected.'
    _load_body_types()
    if not _body_types:
        return 'Could not read the body types. The log has the reason.'
    _load_parts()
    name = '{} {}'.format(getattr(_target, 'first_name', '') or '',
                          getattr(_target, 'last_name', '') or '').strip()
    logfile.write('look: editing {!r}'.format(name))
    return ('Changing how {} looks. Up and down for the part of the body, '
            'left and right through the choices, enter to put one on, '
            'backspace to stop. {}'.format(name or 'your Sim', describe()))


def close_editor():
    global _target, _parts
    _target = None
    _parts = []
    return 'Look editor closed.'


def describe():
    if not _body_types:
        return 'Nothing to change.'
    label, _value = _body_types[_body_index % len(_body_types)]
    if not _parts:
        return '{}: no choices for this Sim.'.format(label)
    part, words, variants = _parts[_part_index % len(_parts)]
    worn = ' (wearing this)' if part in _worn_parts() else ''
    # Said only when there is more than one, so the common case stays short.
    others = (', {} colours that read the same'.format(len(variants))
              if len(variants) > 1 else '')
    return '{}: {} of {}. {}{}{}'.format(
        label, _part_index % len(_parts) + 1, len(_parts),
        ' '.join(words) if words else 'plain, no tags to describe it',
        others, worn)


def next_body_type(step=1):
    global _body_index
    if not _body_types:
        return 'Nothing to change.'
    _body_index = (_body_index + step) % len(_body_types)
    _load_parts()
    return describe()


def next_part(step=1):
    global _part_index
    if not _parts:
        return describe()
    _part_index = (_part_index + step) % len(_parts)
    return describe()


def _refresh(sim_info):
    """Make the change show. Which call does it is not documented anywhere."""
    for label, call in (
            ('save_outfits', lambda: sim_info.save_outfits()),
            ('resend_outfits', lambda: sim_info.resend_outfits()),
            ('resend_current_outfit', lambda: sim_info.resend_current_outfit()),
            ('resend_physical_attributes',
             lambda: sim_info.resend_physical_attributes()),
            ('set_current_outfit',
             lambda: sim_info.set_current_outfit(sim_info.get_current_outfit()))):
        try:
            call()
            logfile.write('look: refreshed via {}'.format(label))
        except Exception:
            continue


def apply_current():
    """Put the part under the cursor onto the Sim."""
    if _target is None:
        return 'No Sim is selected.'
    if not _parts:
        return 'Nothing to put on.'
    part, words, _variants = _parts[_part_index % len(_parts)]
    label, _value = _body_types[_body_index % len(_body_types)]
    import random
    seed = random.randint(1, 0x7FFFFFFF)
    ok = False
    for name, call in (
            ('set_caspart(remove_conflicting)',
             lambda: _cas().set_caspart(_target._base, _target._base, part,
                                        False, False, True, seed,
                                        remove_conflicting=True)),
            ('set_caspart(positional)',
             lambda: _cas().set_caspart(_target._base, _target._base, part,
                                        False, False, True, seed))):
        try:
            call()
            ok = True
            logfile.ok('look: applied {} part {} via {}'.format(label, part, name))
            break
        except TypeError as ex:
            logfile.write('look: {} wrong signature ({!r})'.format(name, ex))
        except Exception as ex:
            logfile.fail('look: {} raised {!r}'.format(name, ex))
    if not ok:
        return 'Could not put that on. The log has the reason.'
    _refresh(_target)
    return 'Wearing {}.'.format(' '.join(words) if words else 'that one')


def randomize():
    """Reroll everything, the way the builder does for a new Sim."""
    if _target is None:
        return 'No Sim is selected.'
    try:
        _cas().randomize_caspart_list(_target._base, [])
        _refresh(_target)
        logfile.ok('look: randomized')
        return 'New look.'
    except Exception as ex:
        logfile.fail('look: randomize failed ({!r})'.format(ex))
        return 'Could not change the look.'
