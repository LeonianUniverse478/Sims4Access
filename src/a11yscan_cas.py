"""Creating a Sim without the CAS screen.

CAS is a client-side screen. Every command in server_commands/cas_commands.py
does the same thing - hand a Sim to the client and wait for one to come back -
and there is no server-side model of the CAS panels at all. So there is nothing
in the CAS screen for a script mod to read, and nothing for it to drive. Reading
that screen out is not on the table.

What is on the table is skipping it. Everything CAS produces that affects play
is reachable from Python: SimCreator plus SimSpawner.create_sim_infos build a
complete Sim - names, gender, age, traits, a generated appearance and a full set
of outfits - and aspiration is a plain attribute afterwards. This module wraps
that in a keyboard wizard, so creating a Sim never opens the CAS screen at all.

Appearance is deliberately left random. It is what CAS spends most of its screen
on and what a blind player gets least from, and the honest alternative - several
thousand unlabelled CAS part ids per category - would be worse than no choice at
all. The generated look is always valid for the gender and age, which is the
part that actually matters.

Creation is irreversible in the way placing an object is, so it follows the same
rules as a11yscan_build: nothing is created until every choice is settled, every
step is logged, and the Sim is only made active once it exists.
"""
import a11yscan_dialogs as dialogs
import a11yscan_log as logfile

FIELDS = ('first', 'last', 'gender', 'age', 'voice', 'questionnaire',
          'trait1', 'trait2', 'trait3', 'aspiration', 'household', 'lot',
          'create')

FIELD_LABELS = {
    'first': 'First name',
    'last': 'Last name',
    'gender': 'Gender',
    'age': 'Age',
    'voice': 'Voice',
    'questionnaire': 'Questionnaire',
    'trait1': 'Trait one',
    'trait2': 'Trait two',
    'trait3': 'Trait three',
    'aspiration': 'Aspiration',
    'household': 'Household',
    'lot': 'Home lot',
    'create': 'Create this Sim',
}

# Young adult first: it is the only age that can hold a household on its own
# without the game immediately wanting a guardian for it.
AGE_ORDER = ('YOUNGADULT', 'ADULT', 'TEEN', 'ELDER', 'CHILD')
AGE_LABELS = {
    'YOUNGADULT': 'young adult', 'ADULT': 'adult', 'TEEN': 'teen',
    'ELDER': 'elder', 'CHILD': 'child',
}
# How many personality traits the game gives each age.
AGE_TRAIT_SLOTS = {
    'YOUNGADULT': 3, 'ADULT': 3, 'TEEN': 3, 'ELDER': 3, 'CHILD': 1,
}

GENDER_ORDER = ('MALE', 'FEMALE')

_NAME_POOL_SIZE = 12

_active = False
_field = 0
_gender = 0
_age = 0

_first_pool = []
_last_pool = []
_first_index = 0
_last_index = 0
_first_fixed = None
_last_fixed = None

_trait_choices = []
_trait_index = [0, 0, 0]

_aspiration_choices = []
_aspiration_index = 0

_voice_choices = []
_voice_index = 0

# Joining the household you are playing is the safe default; starting a
# new one on an empty lot is what makes this a new game rather than an
# extra Sim in your family.
HOUSEHOLD_MODES = ('join your household', 'start a new household')
_household_mode = 0
_lot_choices = []
_lot_index = 0

# Which name field is being typed into, and what has been typed so far.
_typing_field = None
_typed = ''


def active():
    return _active


# --------------------------------------------------------------- game lookups

def _enums():
    from sims.sim_info_types import Age, Gender, Species
    return Age, Gender, Species


def _gender_value():
    _age_enum, Gender, _species = _enums()
    return getattr(Gender, GENDER_ORDER[_gender])


def _age_key():
    return AGE_ORDER[_age]


def _age_value():
    Age, _gender_enum, _species = _enums()
    return getattr(Age, _age_key())


def _species_value():
    _age_enum, _gender_enum, Species = _enums()
    return Species.HUMAN


def _trait_slots():
    return AGE_TRAIT_SLOTS.get(_age_key(), 3)


class _SimInfoData(object):
    """The three attributes Trait.is_valid_trait actually reads.

    Cheaper and safer than building a real SimInfo just to ask which traits are
    legal, and it cannot accidentally end up in the world.
    """

    def __init__(self, age, gender, species):
        self.age = age
        self.gender = gender
        self.species = species


def _display_name(tuning, *attrs):
    for attr in attrs:
        try:
            text = dialogs.loc_text(getattr(tuning, attr, None))
        except Exception:
            text = None
        if text:
            return text
    return getattr(tuning, '__name__', None)


def _dedupe(choices):
    """Keep the 'none' entry first, sort the rest, drop repeated names."""
    seen = set()
    unique = []
    for name, value in choices:
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append((name, value))
    unique[1:] = sorted(unique[1:], key=lambda pair: pair[0].lower())
    return unique


def _refresh_traits():
    """Personality traits legal for the current age and gender."""
    global _trait_choices, _trait_index
    choices = [('no trait', None)]
    try:
        from traits.traits import get_possible_traits
        from traits.trait_type import TraitType
        data = _SimInfoData(_age_value(), _gender_value(), _species_value())
        for trait in get_possible_traits(data, TraitType.PERSONALITY):
            name = _display_name(trait, 'display_name')
            if name:
                choices.append((name, trait))
    except Exception as ex:
        logfile.fail('cas: could not list traits ({!r})'.format(ex))
    _trait_choices = _dedupe(choices)
    _trait_index = [0, 0, 0]
    logfile.write('cas: {} personality traits for {} {}'.format(
        len(_trait_choices) - 1, AGE_LABELS[_age_key()],
        GENDER_ORDER[_gender].lower()))


def _refresh_aspirations():
    global _aspiration_choices, _aspiration_index
    choices = [('no aspiration', None)]
    try:
        import services
        import sims4.resources
        manager = services.get_instance_manager(
            sims4.resources.Types.ASPIRATION_TRACK)
        for track in manager.types.values():
            try:
                if getattr(track, 'is_hidden_unlockable', False):
                    continue
                if getattr(track, 'hidden', False):
                    continue
            except Exception:
                pass
            name = _display_name(track, 'display_text', 'display_name')
            if name:
                choices.append((name, track))
    except Exception as ex:
        logfile.fail('cas: could not list aspirations ({!r})'.format(ex))
    _aspiration_choices = _dedupe(choices)
    _aspiration_index = 0
    logfile.write('cas: {} aspirations listed'.format(
        len(_aspiration_choices) - 1))


def _all_sim_infos():
    for attr in ('values', 'get_all'):
        try:
            import services
            call = getattr(services.sim_info_manager(), attr, None)
            if call is not None:
                return list(call())
        except Exception:
            continue
    try:
        import services
        return list(services.sim_info_manager())
    except Exception:
        return []


def _refresh_voices():
    """Offer the voices the game itself uses for this gender and age.

    Voice ids are not in the Python tuning at all - they live in client-side CAS
    resources - so there is no list to read, and hardcoded ids would be a guess.
    Instead harvest the distinct voice_actor values off Sims already loaded in
    the world: those are real ids the game accepts for that demographic. Their
    display names live in those same client resources, so voices can only be
    numbered here, not named.
    """
    global _voice_choices, _voice_index
    gender = _gender_value()
    age = _age_value()
    exact = []
    same_gender = []
    for sim_info in _all_sim_infos():
        try:
            actor = getattr(sim_info, 'voice_actor', None)
            if not actor:
                continue
            if getattr(sim_info, 'gender', None) != gender:
                continue
            same_gender.append(actor)
            if getattr(sim_info, 'age', None) == age:
                exact.append(actor)
        except Exception:
            continue
    # Age matters for voices - a child voice is not an adult one - so prefer an
    # exact age match and widen only when this world holds no Sim of that age.
    ordered = sorted(set(exact or same_gender))
    _voice_choices = [('the game decides', None)]
    for index, actor in enumerate(ordered, 1):
        _voice_choices.append(('voice {}'.format(index), actor))
    _voice_index = 0
    logfile.write('cas: {} voices for {} {} ({} exact, {} by gender)'.format(
        len(ordered), AGE_LABELS[_age_key()], GENDER_ORDER[_gender].lower(),
        len(set(exact)), len(set(same_gender))))


def voice_choices():
    return _voice_choices


def _voice_name():
    if not _voice_choices:
        return 'the game decides'
    return _voice_choices[_voice_index % len(_voice_choices)][0]


def _voice_value():
    if not _voice_choices:
        return None
    return _voice_choices[_voice_index % len(_voice_choices)][1]


def _random_names(getter):
    """Roll a pool of names, deduplicated, in the game's own naming style."""
    pool = []
    seen = set()
    gender = _gender_value()
    species = _species_value()
    for _ in range(_NAME_POOL_SIZE * 4):
        if len(pool) >= _NAME_POOL_SIZE:
            break
        name = None
        for call in (lambda: getter(gender, species), lambda: getter(gender)):
            try:
                name = call()
                break
            except TypeError:
                continue
            except Exception:
                name = None
                break
        if not name or name in seen:
            continue
        seen.add(name)
        pool.append(name)
    return pool


def _roll_first():
    global _first_pool, _first_index
    try:
        from sims.sim_spawner import SimSpawner
        _first_pool = _random_names(SimSpawner.get_random_first_name)
    except Exception as ex:
        logfile.fail('cas: first-name roll failed ({!r})'.format(ex))
        _first_pool = []
    _first_index = 0


def _roll_last():
    global _last_pool, _last_index
    try:
        from sims.sim_spawner import SimSpawner
        _last_pool = _random_names(SimSpawner.get_random_last_name)
    except Exception as ex:
        logfile.fail('cas: last-name roll failed ({!r})'.format(ex))
        _last_pool = []
    _last_index = 0


def first_name():
    if _first_fixed:
        return _first_fixed
    if _first_pool:
        return _first_pool[_first_index % len(_first_pool)]
    return 'Sim'


def last_name():
    if _last_fixed:
        return _last_fixed
    if _last_pool:
        return _last_pool[_last_index % len(_last_pool)]
    return 'Newcomer'


def set_first(name):
    """Type an exact first name from the console, for the names a roll will
    never produce."""
    global _first_fixed
    _first_fixed = (name or '').strip() or None
    return 'First name {}.'.format(first_name())


def set_last(name):
    global _last_fixed
    _last_fixed = (name or '').strip() or None
    return 'Last name {}.'.format(last_name())


# ------------------------------------------------------------------ the wizard

def open_builder():
    global _active, _field, _gender, _age, _first_fixed, _last_fixed
    if _active:
        return close_builder()
    _field = 0
    _gender = 0
    _age = 0
    _first_fixed = None
    _last_fixed = None
    _roll_first()
    _roll_last()
    _refresh_traits()
    _refresh_aspirations()
    _refresh_voices()
    _active = True
    logfile.write('cas: builder opened')
    return ('Create a Sim. Up and down for each choice, left and right to '
            'change it, enter to reroll names or to create. Backspace to '
            'leave. {}'.format(describe()))


def close_builder(announce=True):
    global _active
    was_open = _active
    _active = False
    if was_open:
        logfile.write('cas: builder closed')
    return 'Create a Sim closed.' if announce else None


def _trait_name(slot):
    if not _trait_choices:
        return 'none'
    return _trait_choices[_trait_index[slot] % len(_trait_choices)][0]


def _trait_value(slot):
    if not _trait_choices:
        return None
    return _trait_choices[_trait_index[slot] % len(_trait_choices)][1]


def _aspiration_name():
    if not _aspiration_choices:
        return 'none'
    return _aspiration_choices[_aspiration_index % len(_aspiration_choices)][0]


def _aspiration_value():
    if not _aspiration_choices:
        return None
    return _aspiration_choices[_aspiration_index % len(_aspiration_choices)][1]


def typing():
    """The field being typed into, or None."""
    return _typing_field


def start_typing(field):
    global _typing_field, _typed
    _typing_field = field
    _typed = ''
    which = 'first' if field == 'first' else 'last'
    return ('Type the {} name. Letters and space, backspace to rub out, '
            'enter when done, escape to keep the rolled name.'.format(which))


def type_character(char):
    """One key while typing. Says the letter back, since you cannot see it."""
    global _typed
    if _typing_field is None:
        return None
    if len(_typed) >= 24:
        return 'That is long enough.'
    _typed += char
    return char if char != ' ' else 'space'


def type_backspace():
    global _typed
    if _typing_field is None:
        return None
    if not _typed:
        return 'Empty.'
    removed = _typed[-1]
    _typed = _typed[:-1]
    return 'deleted {}, {}'.format(
        'space' if removed == ' ' else removed, _typed or 'empty')


def type_accept():
    """Keep what was typed. Blank means fall back to the rolled name."""
    global _typing_field, _typed
    field = _typing_field
    text = _typed.strip()
    _typing_field = None
    _typed = ''
    if not text:
        return 'Nothing typed, keeping {}.'.format(
            first_name() if field == 'first' else last_name())
    if field == 'first':
        set_first(text)
    else:
        set_last(text)
    logfile.write('cas: {} name typed as {!r}'.format(field, text))
    return '{} name {}. {}'.format(
        'First' if field == 'first' else 'Last', text, describe())


def type_cancel():
    global _typing_field, _typed
    _typing_field = None
    _typed = ''
    return 'Left it as {}.'.format(describe())


def typed_so_far():
    return _typed or 'nothing yet'


def current_field():
    return FIELDS[_field]


def describe(full=False):
    """The field under the cursor, spoken."""
    key = FIELDS[_field]
    label = FIELD_LABELS[key]
    if key == 'first':
        value = first_name()
        if _first_fixed:
            value += ', typed'
        elif _first_pool:
            value += ', {} of {}'.format(_first_index + 1, len(_first_pool))
    elif key == 'last':
        value = last_name()
        if _last_fixed:
            value += ', typed'
        elif _last_pool:
            value += ', {} of {}'.format(_last_index + 1, len(_last_pool))
    elif key == 'gender':
        value = GENDER_ORDER[_gender].lower()
    elif key == 'age':
        value = AGE_LABELS[_age_key()]
    elif key == 'questionnaire':
        value = 'press enter to answer the game questions'
    elif key == 'household':
        value = HOUSEHOLD_MODES[_household_mode]
    elif key == 'lot':
        if not _household_mode:
            value = 'not used when joining your household'
        elif not _lot_choices:
            value = 'press enter to load the empty lots'
        else:
            entry = _lot_choices[_lot_index % len(_lot_choices)]
            value = '{}, {} of {}'.format(
                _lot_describe(entry), _lot_index % len(_lot_choices) + 1,
                len(_lot_choices))
    elif key == 'voice':
        value = _voice_name()
        if len(_voice_choices) > 1:
            value += ', {} of {}'.format(
                _voice_index % len(_voice_choices) + 1, len(_voice_choices))
    elif key.startswith('trait'):
        slot = int(key[-1]) - 1
        if slot >= _trait_slots():
            value = 'not used at this age'
        else:
            value = _trait_name(slot)
            if _trait_choices:
                value += ', {} of {}'.format(
                    _trait_index[slot] % len(_trait_choices) + 1,
                    len(_trait_choices))
    elif key == 'aspiration':
        value = _aspiration_name()
        if _aspiration_choices:
            value += ', {} of {}'.format(
                _aspiration_index % len(_aspiration_choices) + 1,
                len(_aspiration_choices))
    else:
        value = 'press enter'
    text = '{}: {}'.format(label, value)
    if full:
        text += '. {} of {}'.format(_field + 1, len(FIELDS))
    return text


def summary():
    """Everything chosen so far, for the confirmation before creating."""
    parts = ['{} {}'.format(first_name(), last_name()),
             AGE_LABELS[_age_key()],
             GENDER_ORDER[_gender].lower()]
    chosen = [_trait_name(slot) for slot in range(_trait_slots())
              if _trait_value(slot) is not None]
    parts.append('traits {}'.format(', '.join(chosen)) if chosen
                 else 'no traits')
    if _voice_value() is not None:
        parts.append(_voice_name())
    if _aspiration_value() is not None:
        parts.append('aspiration {}'.format(_aspiration_name()))
    if _household_mode:
        entry = chosen_lot()
        parts.append('in a new household at {}'.format(_lot_describe(entry))
                     if entry else 'in a new household with no lot chosen')
    return ', '.join(parts)


def next_field(step=1):
    global _field
    if not _active:
        return 'Create a Sim is closed.'
    _field = (_field + step) % len(FIELDS)
    if FIELDS[_field] == 'create':
        return '{}. {}'.format(describe(), summary())
    return describe()


def change_value(step=1):
    """Left and right on the current field."""
    global _gender, _age, _first_index, _last_index, _aspiration_index
    global _voice_index, _household_mode, _lot_index
    if not _active:
        return 'Create a Sim is closed.'
    key = FIELDS[_field]
    if key == 'first':
        if _first_fixed:
            return 'First name is typed. Use a11y2.cas.first to change it.'
        if not _first_pool:
            return 'No names rolled.'
        _first_index = (_first_index + step) % len(_first_pool)
    elif key == 'last':
        if _last_fixed:
            return 'Last name is typed. Use a11y2.cas.last to change it.'
        if not _last_pool:
            return 'No names rolled.'
        _last_index = (_last_index + step) % len(_last_pool)
    elif key == 'gender':
        _gender = (_gender + step) % len(GENDER_ORDER)
        # Names and traits are both gendered, so both have to follow.
        if not _first_fixed:
            _roll_first()
        if not _last_fixed:
            _roll_last()
        _refresh_traits()
        _refresh_voices()
    elif key == 'age':
        _age = (_age + step) % len(AGE_ORDER)
        _refresh_traits()
        _refresh_voices()
    elif key == 'voice':
        if len(_voice_choices) < 2:
            return 'No other voices found in this world.'
        _voice_index = (_voice_index + step) % len(_voice_choices)
    elif key.startswith('trait'):
        slot = int(key[-1]) - 1
        if slot >= _trait_slots():
            return 'A {} only gets {} trait{}.'.format(
                AGE_LABELS[_age_key()], _trait_slots(),
                '' if _trait_slots() == 1 else 's')
        if not _trait_choices:
            return 'No traits available.'
        _trait_index[slot] = (_trait_index[slot] + step) % len(_trait_choices)
    elif key == 'aspiration':
        if not _aspiration_choices:
            return 'No aspirations available.'
        _aspiration_index = (_aspiration_index + step) % len(_aspiration_choices)
    elif key == 'household':
        _household_mode = (_household_mode + step) % len(HOUSEHOLD_MODES)
    elif key == 'lot':
        if not _household_mode:
            return 'Only used when starting a new household.'
        if not _lot_choices:
            return 'Press enter to load the empty lots first.'
        _lot_index = (_lot_index + step) % len(_lot_choices)
    else:
        return 'Press enter to create {}.'.format(summary())
    return describe()


def activate():
    """Enter: reroll names, create on the last field, otherwise repeat."""
    if not _active:
        return 'Create a Sim is closed.'
    key = FIELDS[_field]
    if key in ('first', 'last'):
        return start_typing(key)
    if key == 'lot':
        if not _household_mode:
            return 'Only used when starting a new household.'
        return load_lots()
    if key == 'create':
        return create()
    return describe(full=True)


# -------------------------------------------------------------------- creation

def _conflicts(traits):
    """The game refuses conflicting traits; say so before creating, not after."""
    try:
        from traits.traits import are_traits_conflicting
    except Exception:
        return None
    for i in range(len(traits)):
        for j in range(i + 1, len(traits)):
            try:
                if are_traits_conflicting(traits[i], traits[j]):
                    return (i, j)
            except Exception:
                continue
    return None


def _client():
    try:
        import services
        return services.client_manager().get_first_client()
    except Exception as ex:
        logfile.write('cas: no client ({!r})'.format(ex))
        return None


def _active_household():
    import services
    return services.active_household()


def _target_household(client):
    """Prefer the household already being played, even if everyone in it died.

    A dead household is still a live Household object with a home zone, so
    adding to it keeps the lot, the money and the save intact. Making a new one
    is the fallback, and it is the riskier path, so it is logged loudly.
    """
    for label, getter in (
            ('client household', lambda: client.household if client else None),
            ('active household', _active_household)):
        try:
            household = getter()
        except Exception as ex:
            logfile.write('cas: {} lookup failed ({!r})'.format(label, ex))
            continue
        if household is not None:
            count = -1
            try:
                count = len(list(household.sim_info_gen()))
            except Exception:
                pass
            logfile.write('cas: using {} (id={}, {} sims)'.format(
                label, getattr(household, 'id', '?'), count))
            return household, False
    logfile.write('cas: no existing household, one will be created')
    return None, True


def _make_sim_info(creator, household, client):
    """create_sim_infos takes a lot of optional arguments and not every build of
    the game accepts the same ones, so try richest first and fall back."""
    from sims.sim_spawner import SimSpawner
    try:
        import services
        zone_id = services.current_zone_id()
    except Exception:
        zone_id = None
    attempts = (
        ('full', dict(household=household, tgt_client=client, zone_id=zone_id,
                      creation_source='a11yscan_cas',
                      generate_all_cas_outfits=True)),
        ('no creation source', dict(household=household, tgt_client=client,
                                    zone_id=zone_id,
                                    generate_all_cas_outfits=True)),
        ('no client', dict(household=household,
                           generate_all_cas_outfits=True)),
        ('minimal', dict(household=household)),
    )
    last_error = None
    for label, kwargs in attempts:
        try:
            result = SimSpawner.create_sim_infos((creator,), **kwargs)
        except Exception as ex:
            last_error = ex
            logfile.write('cas: create_sim_infos {} raised {!r}'.format(label, ex))
            continue
        try:
            sim_infos, new_household = result
        except Exception:
            sim_infos, new_household = result, household
        if sim_infos:
            logfile.ok('cas: create_sim_infos succeeded via {}'.format(label))
            return list(sim_infos)[0], new_household
        logfile.write('cas: create_sim_infos {} returned nothing'.format(label))
    logfile.fail('cas: every create_sim_infos attempt failed, last {!r}'.format(
        last_error))
    return None, household


def apply_name(sim_info, first, last):
    """Set a Sim's name and report the name that actually stuck.

    Reads the value back rather than echoing what was passed in: the first
    version of this logged its own variables, which made a Sim called "A Sim"
    look like a success in the log.
    """
    for attr, value in (('first_name', first), ('last_name', last)):
        try:
            setattr(sim_info, attr, value)
        except Exception as ex:
            logfile.fail('cas: could not set {} ({!r})'.format(attr, ex))
    actual = []
    for attr in ('first_name', 'last_name'):
        try:
            actual.append(str(getattr(sim_info, attr, '') or ''))
        except Exception:
            actual.append('')
    # If a name key is set the client may prefer it over the strings; worth
    # knowing in the log before guessing at a cause.
    try:
        key = getattr(sim_info, 'full_name_key', None)
        if key:
            logfile.write('cas: note, full_name_key is {}'.format(key))
    except Exception:
        pass
    return ' '.join(part for part in actual if part)


def tidy_case(name):
    """Undo the cheat console lowercasing arguments.

    Typing "Miranda" into the console arrives here as "miranda". If the text
    still carries any capital it was not lowercased, so leave it exactly as
    typed - that is the only way to keep names like McDonald or O'Brien.
    """
    text = (name or '').strip()
    if not text or text != text.lower():
        return text
    return ' '.join(part[:1].upper() + part[1:] for part in text.split(' '))


def household_sims():
    """Every Sim in the played household, so a rename can be aimed properly."""
    sims = []
    try:
        import services
        client = _client()
        # The PLAYED household decides this, not the client's idea of one.
        # After a travel the client's household reference can point somewhere
        # else, and trusting it first meant the switcher could list - and make
        # active - Sims from a household you do not own.
        household = services.active_household()
        if household is None and client is not None:
            household = getattr(client, 'household', None)
        if household is None:
            return sims
        if client is not None:
            other = getattr(client, 'household', None)
            if other is not None and other is not household:
                logfile.write('cas: the client thinks the household is {!r}, '
                              'the game says {!r}; using the game'.format(
                                  getattr(other, 'name', '?'),
                                  getattr(household, 'name', '?')))
        active = None
        if client is not None:
            active = getattr(client, 'active_sim_info', None)
        for sim_info in household.sim_info_gen():
            sims.append((sim_info, sim_info is active))
    except Exception as ex:
        logfile.fail('cas: could not list household ({!r})'.format(ex))
    return sims


def describe_sim(sim_info, is_active):
    parts = []
    try:
        parts.append('{} {}'.format(
            getattr(sim_info, 'first_name', '') or '',
            getattr(sim_info, 'last_name', '') or '').strip() or 'unnamed')
    except Exception:
        parts.append('unnamed')
    try:
        if getattr(sim_info, 'is_ghost', False):
            parts.append('dead')
    except Exception:
        pass
    if is_active:
        parts.append('selected')
    return ', '.join(parts)


def rename_at(index, first, last):
    """Rename by position in the household listing, for Sims that are not
    selected - including dead ones."""
    sims = household_sims()
    if not sims:
        return 'No household Sims found.'
    try:
        position = int(index) - 1
    except Exception:
        return 'Give a number from a11y2.who.'
    if position < 0 or position >= len(sims):
        return 'There are only {} Sims. Use a11y2.who to list them.'.format(
            len(sims))
    sim_info = sims[position][0]
    return _rename(sim_info, first, last)


def _rename(sim_info, first, last):
    """Rename one Sim, always saying who was renamed.

    The first version only announced the new name, so renaming the wrong Sim
    was silent - which is exactly what happened: a rename meant for a dead Sim
    landed on the selected one and nothing said so.
    """
    before = describe_sim(sim_info, False).split(',')[0]
    after = apply_name(sim_info, tidy_case(first), tidy_case(last))
    logfile.ok('cas: renamed {!r} to {!r}'.format(before, after))
    return 'Renamed {} to {}.'.format(before, after)


def apply_results(traits, aspiration):
    """Point the trait and aspiration fields at what the questionnaire chose.

    Deliberately selects them in the existing lists rather than stashing them
    somewhere separate: the answers are a starting point, and every one stays
    visible and changeable on the normal fields.
    """
    applied = []
    skipped = 0
    slot = 0
    # Fill the slots with the top-scoring traits that are actually selectable.
    # The questionnaire can score traits this Sim cannot take - the builder's
    # list holds only personality traits legal for the chosen age and gender -
    # and the first version assigned by position, so one unusable trait left
    # its slot empty while the rest filled in around it.
    for trait in traits:
        if slot >= _trait_slots():
            break
        for position, (name, value) in enumerate(_trait_choices):
            if value is trait:
                _trait_index[slot] = position
                applied.append(name)
                slot += 1
                break
        else:
            skipped += 1
    if skipped:
        logfile.write('cas: {} scored traits were not selectable here'.format(
            skipped))
    global _aspiration_index
    if aspiration is not None:
        for position, (name, value) in enumerate(_aspiration_choices):
            if value is aspiration:
                _aspiration_index = position
                applied.append(name)
                break
    logfile.write('cas: questionnaire filled in {}'.format(
        ', '.join(applied) if applied else 'nothing'))
    return applied


def _lot_describe(entry):
    parts = [entry['name'], entry['world']]
    if entry.get('size'):
        parts.append(str(entry['size']))
    return ', '.join(parts)


def load_lots():
    """Read the empty lots. Done on demand - it walks every zone in the save."""
    global _lot_choices, _lot_index
    import a11yscan_lots as lots
    _lot_choices = lots.empty_lots()
    _lot_index = 0
    if not _lot_choices:
        return 'No empty lots found. The log has the survey.'
    return '{} empty lots. Left and right to browse. {}'.format(
        len(_lot_choices), _lot_describe(_lot_choices[0]))


def chosen_lot():
    if not _household_mode or not _lot_choices:
        return None
    return _lot_choices[_lot_index % len(_lot_choices)]


def apply_voice(sim_info, actor):
    try:
        sim_info.voice_actor = actor
        return True
    except Exception as ex:
        logfile.fail('cas: could not set voice ({!r})'.format(ex))
        return False


def _selected_sim_info():
    try:
        import services
        client = _client()
        if client is not None:
            sim_info = getattr(client, 'active_sim_info', None)
            if sim_info is not None:
                return sim_info
        sim = services.get_active_sim()
        return getattr(sim, 'sim_info', None) if sim is not None else None
    except Exception:
        return None


def _short_name(sim_info):
    return describe_sim(sim_info, False).split(',')[0]


def set_voice_active(index):
    """Change the selected Sim's voice, for Sims that already exist."""
    global _gender, _age
    sim_info = _selected_sim_info()
    if sim_info is None:
        return 'No Sim is selected.'
    # Build the voice list against the Sim being changed, not whatever the
    # builder happens to be showing.
    try:
        Age, Gender, _species = _enums()
        for position, key in enumerate(AGE_ORDER):
            if getattr(sim_info, 'age', None) == getattr(Age, key):
                _age = position
                break
        _gender = 1 if getattr(sim_info, 'gender', None) == Gender.FEMALE else 0
    except Exception as ex:
        logfile.write('cas: could not read Sim demographics ({!r})'.format(ex))
    _refresh_voices()
    try:
        position = int(index)
    except Exception:
        return 'Give a voice number, for example a11y2.voice 2.'
    if position < 1 or position >= len(_voice_choices):
        return 'This world only offers {} voices for that Sim.'.format(
            max(0, len(_voice_choices) - 1))
    label, actor = _voice_choices[position]
    if not apply_voice(sim_info, actor):
        return 'Could not change that voice.'
    name = _short_name(sim_info)
    logfile.ok('cas: {} set to {} ({})'.format(name, label, actor))
    return '{} now uses {}.'.format(name, label)


def switch_to(index):
    """Play a different Sim in the household, numbered as in a11y2.who."""
    sims = household_sims()
    if not sims:
        return 'No household Sims found.'
    try:
        position = int(index) - 1
    except Exception:
        return 'Give a number from a11y2.who.'
    if position < 0 or position >= len(sims):
        return 'There are only {} Sims in your household.'.format(len(sims))
    sim_info, is_active = sims[position]
    name = _short_name(sim_info)
    # Never make a Sim outside your household active. Doing so leaves the game
    # in a state it has no way back from on its own, and the mod should not be
    # able to cause that by mistake.
    # No membership check here. Playing a Sim outside your household is a
    # thing people deliberately do - MC Command Center exists for it - and a
    # mod for players who cannot see the screen has no business deciding that
    # a switch they asked for is a mistake. It is noted in the log and left
    # alone.
    try:
        import services
        household = services.active_household()
        if (household is not None
                and sim_info.household_id != getattr(household, 'id', None)):
            logfile.write('cas: {!r} is outside the active household; '
                          'switching anyway, as asked'.format(name))
    except Exception:
        pass
    if is_active:
        return 'Already playing {}.'.format(name)
    client = _client()
    if client is None:
        return 'No client available.'
    for label, call in (
            ('set_active_sim_info', lambda: client.set_active_sim_info(sim_info)),
            ('set_active_sim_by_id',
             lambda: client.set_active_sim_by_id(sim_info.id))):
        try:
            call()
            logfile.ok('cas: switched to {!r} via {}'.format(name, label))
            return 'Now playing {}.'.format(name)
        except Exception as ex:
            logfile.write('cas: {} failed ({!r})'.format(label, ex))
    logfile.fail('cas: could not switch to {!r}'.format(name))
    return 'Could not switch to {}.'.format(name)


def rename_active(first, last):
    """Rename whichever Sim is selected, for fixing a Sim already created."""
    try:
        import services
        client = _client()
        sim_info = None
        if client is not None:
            sim_info = getattr(client, 'active_sim_info', None)
        if sim_info is None:
            sim = services.get_active_sim()
            sim_info = getattr(sim, 'sim_info', None) if sim is not None else None
        if sim_info is None:
            return 'No Sim is selected.'
        return _rename(sim_info, first, last)
    except Exception as ex:
        logfile.fail('cas: rename failed ({!r})'.format(ex))
        return 'Could not rename that Sim.'


def create():
    """Build the Sim, put them on the lot and hand control over."""
    slots = _trait_slots()
    traits = [_trait_value(slot) for slot in range(slots)]
    traits = [trait for trait in traits if trait is not None]
    clash = _conflicts(traits)
    if clash is not None:
        first, second = clash
        logfile.fail('cas: conflicting traits {} and {}'.format(
            _trait_name(first), _trait_name(second)))
        return 'Those traits conflict: {} and {}. Change one.'.format(
            _trait_name(first), _trait_name(second))

    logfile.write('cas: creating {}'.format(summary()))
    try:
        from sims.sim_spawner import SimCreator
        creator = SimCreator(
            gender=_gender_value(),
            age=_age_value(),
            species=_species_value(),
            first_name=first_name(),
            last_name=last_name(),
            traits=tuple(traits))
    except Exception as ex:
        logfile.fail('cas: SimCreator raised {!r}'.format(ex))
        return 'Could not describe that Sim.'

    client = _client()
    if _household_mode:
        # household=None makes create_sim_infos build one and register it.
        household, is_new = None, True
        logfile.write('cas: starting a new household')
    else:
        household, is_new = _target_household(client)
    sim_info, household = _make_sim_info(creator, household, client)
    if sim_info is None:
        return 'Could not create that Sim. The log has the reason.'

    # SimCreator accepts first_name and last_name, but
    # build_creation_dictionary never passes them on - it sends only age,
    # gender, species, tags, traits and body-type policy - so the Sim comes back
    # unnamed and the game falls back to its "A Sim" placeholder. The game's own
    # rename flow (sims/change_sim_name_interaction.on_response) just assigns
    # the two properties and sends nothing, so do exactly that.
    name = apply_name(sim_info, first_name(), last_name())
    logfile.ok('cas: sim_info created as {!r}, id={}'.format(
        name, getattr(sim_info, 'id', '?')))

    moved_to = None
    if is_new and household is not None:
        import a11yscan_lots as lots
        entry = chosen_lot()
        if entry is not None:
            ok, _text = lots.move_in(household, entry['zone_id'])
            if ok:
                moved_to = entry
        # A household built by create_sim_infos is not flagged as the player's,
        # so without this it would be listed among the townies you have never
        # met rather than among your own families.
        try:
            household.set_played_household(True)
            logfile.ok('cas: new household marked as belonging to the player')
        except Exception as ex:
            logfile.write('cas: could not mark the household ({!r})'.format(ex))
        else:
            # No lot chosen: keep them here rather than leaving a homeless
            # household, which the game handles badly.
            try:
                import services
                household.move_into_zone(services.current_zone_id())
                logfile.ok('cas: new household moved into the current zone')
            except Exception as ex:
                logfile.fail('cas: move_into_zone failed ({!r})'.format(ex))

    voice = _voice_value()
    if voice is not None and apply_voice(sim_info, voice):
        logfile.ok('cas: voice set to {} ({})'.format(_voice_name(), voice))

    aspiration = _aspiration_value()
    if aspiration is not None:
        try:
            sim_info.primary_aspiration = aspiration
            logfile.ok('cas: aspiration set to {}'.format(_aspiration_name()))
        except Exception as ex:
            logfile.fail('cas: aspiration failed ({!r})'.format(ex))

    spawned = False
    try:
        from sims.sim_spawner import SimSpawner
        SimSpawner.spawn_sim(sim_info)
        spawned = True
        logfile.ok('cas: spawned onto the lot')
    except Exception as ex:
        logfile.fail('cas: spawn_sim failed ({!r})'.format(ex))

    selected = False
    if client is not None:
        for label, call in (
                ('add_selectable_sim_info',
                 lambda: client.add_selectable_sim_info(sim_info)),
                ('set_active_sim_info',
                 lambda: client.set_active_sim_info(sim_info))):
            try:
                call()
                logfile.ok('cas: {} ok'.format(label))
                selected = True
            except Exception as ex:
                logfile.write('cas: {} failed ({!r})'.format(label, ex))

    close_builder(announce=False)
    parts = ['{} created'.format(name)]
    if moved_to is not None:
        parts.append('living at {}'.format(_lot_describe(moved_to)))
    # Nothing here is on disk yet. Say so every time: a Sim made and not saved
    # is simply gone, and there is no sign of it until you look for them.
    parts.append('Press Control Shift S to save now, or they will be lost')
    if moved_to is not None:
        parts.append('then Control Alt O to go and play them')
    if not spawned:
        parts.append('but they are not on the lot yet')
    if not selected:
        parts.append('you may need to select them')
    return '. '.join(parts) + '.'
