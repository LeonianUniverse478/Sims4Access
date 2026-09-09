"""Bridge to the game's UI dialogs.

Sims 4 builds its dialogs server-side in Python and ships them to the client,
so the rows of a recipe picker, the buttons on an incoming phone call, and the
options in almost every pop-up all exist as Python objects we can read. We wrap
UiDialogBase.show_dialog to catch each one as it appears, announce it, and let
the scanner drive it from the keyboard.

Responding goes back through the game's own command path: clicking a picker row
is ui.dialog.pick_result <dialog_id> <option_id>, and a button is
ui.dialog.respond <dialog_id> <response_id>. Driving those means the server
handles our answer identically to a real click, rather than us trying to
reconstruct picked results by hand.
"""
import a11yscan_log as logfile
import a11yscan_names as names
import a11yscan_objects as objectnames
import a11yscan_speech as speech

_installed = False
_active = []
_last_error = None
_last_route = None

MAX_TRACKED = 4

# Why a row label failed to resolve, so a11y2.dialog can explain "option 1".
_label_debug = []

_LABEL_ATTRS = ('name', 'text', 'display_name', 'label', 'title',
                'row_name', 'description')


def _name_from_id(sim_id):
    """Sim picker rows carry only an id - the client renders the name."""
    try:
        import services
        info = services.sim_info_manager().get(sim_id)
    except Exception:
        return None
    if info is None:
        return None
    try:
        name = '{} {}'.format(getattr(info, 'first_name', '') or '',
                              getattr(info, 'last_name', '') or '').strip()
        return name or None
    except Exception:
        return None


def _label_from_tag(tag):
    """Some rows identify their subject by tag rather than by name."""
    if tag is None:
        return None
    for getter in (lambda: '{} {}'.format(tag.first_name, tag.last_name).strip(),
                   lambda: loc_text(tag.catalog_name),
                   lambda: loc_text(tag.name),
                   lambda: loc_text(getattr(tag, 'display_name', None))):
        try:
            text = getter()
            if text:
                return text
        except Exception:
            continue
    return None


# Attribute names worth reading, most promising first. Matched as substrings,
# so a mod calling its field "custom_label_text" is still found.
_NAME_HINTS = ('display_name', 'name', 'title', 'label', 'text', 'string',
               'description', 'caption', 'header', 'tooltip')
# Ids we know how to turn into words.
_ID_RESOLVERS = (('sim_id', '_sim'), ('def_id', '_object'),
                 ('definition', '_object'), ('object_id', '_object'))


def _tag_words(value):
    """Tag ids as words, the way the appearance editor describes CAS parts."""
    words = []
    try:
        from tag import Tag
    except Exception:
        return words
    if isinstance(value, (str, bytes)):
        return words
    try:
        # Tag containers arrive as array('L', [...]) as well as lists, so ask
        # whether it iterates rather than checking against known types.
        iter(value)
        items = value
    except TypeError:
        items = (value,)
    except Exception:
        return words
    for item in items:
        name = getattr(item, 'name', None)
        if name is None:
            try:
                name = Tag(item).name
            except Exception:
                name = None
        if not name:
            continue
        _category, _sep, tail = str(name).partition('_')
        words.append((tail or name).replace('_', ' ').lower())
    return words[:4]


def _definition_text(def_id):
    """Name and price for an object definition id.

    Store rows carry only a def_id, so this is the label. The offline object
    table is keyed on base-game ids and misses anything a mod adds, so ask the
    game's definition manager first - it knows custom content too - and fall
    back to the table.
    """
    if not def_id:
        return None
    name = None
    price = None
    try:
        import services
        definition = services.definition_manager().get(def_id)
        if definition is not None:
            import a11yscan_world as world
            name = world.definition_name(definition)
            try:
                value = getattr(definition, 'price', None)
                if value:
                    price = int(value)
            except Exception:
                price = None
    except Exception:
        name = None
    if not name:
        try:
            name = objectnames.lookup(def_id)
        except Exception:
            name = None
    if not name:
        return None
    return '{}, {} simoleons'.format(name, price) if price else name


def _text_from(value, attr_name=''):
    """Words out of whatever a row happens to hold.

    Deliberately generic: mods invent their own field names, and chasing each
    one has meant a screen works until somebody ships a new dialog. Strings,
    LocalizedStrings, tuning classes, Sim ids and object definitions all become
    text here, and integers are only resolved when the field NAME says what
    they are - a bare number matched against the string table would invent
    labels out of coincidences.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        text = strip_tokens(strip_markup(value)).strip()
        return text or None
    if isinstance(value, (int, float)):
        lowered = attr_name.lower()
        if 'sim' in lowered and 'id' in lowered:
            return _name_from_id(int(value))
        if 'def' in lowered or 'object' in lowered:
            return _definition_text(int(value))
        if any(hint in lowered for hint in ('name', 'text', 'string', 'key')):
            try:
                return names.lookup(int(value))
            except Exception:
                return None
        return None
    text = loc_text(value)
    if text:
        return text
    for attr in ('display_name', 'name', '__name__'):
        try:
            found = getattr(value, attr, None)
        except Exception:
            continue
        if found is None:
            continue
        if isinstance(found, str):
            cleaned = strip_tokens(strip_markup(found)).strip()
            if cleaned:
                return cleaned
        else:
            cleaned = loc_text(found)
            if cleaned:
                return cleaned
    return None


def _purchase_label(row):
    """Purchase picker rows: the object, its price, and how many you own."""
    try:
        def_id = getattr(row, 'def_id', None)
    except Exception:
        return None
    text = _definition_text(def_id) if def_id else None
    if not text:
        return None
    try:
        owned = int(getattr(row, 'num_owned', 0) or 0)
        if owned:
            text += ', you own {}'.format(owned)
    except Exception:
        pass
    try:
        if not getattr(row, 'is_enable', True):
            text += ', not available'
    except Exception:
        pass
    return text


def _generic_label(row, index):
    """Last resort before 'option 3': look at everything the row carries."""
    purchase = _purchase_label(row)
    if purchase:
        return purchase
    best = None
    try:
        attrs = [a for a in dir(row) if not a.startswith('_')]
    except Exception:
        return None
    # Promising field names first, so a real label wins over an incidental one.
    def rank(attr):
        lowered = attr.lower()
        for position, hint in enumerate(_NAME_HINTS):
            if hint in lowered:
                return position
        return len(_NAME_HINTS)
    for attr in sorted(attrs, key=rank):
        if rank(attr) >= len(_NAME_HINTS) and best is not None:
            break
        try:
            value = getattr(row, attr, None)
        except Exception:
            continue
        if value is None or callable(value):
            continue
        text = _text_from(value, attr)
        if text and len(text) < 200:
            if rank(attr) < len(_NAME_HINTS):
                return text
            best = best or text
    # Nothing named usefully; tags at least describe the thing.
    for attr in ('tag_list', 'tags', 'tag'):
        try:
            words = _tag_words(getattr(row, attr, None))
        except Exception:
            words = []
        if words:
            return ', '.join(words)
    return best


def _log_unlabelled(row, index):
    """Record what an unreadable row actually holds, so it can be fixed once."""
    try:
        fields = []
        for attr in sorted(a for a in dir(row) if not a.startswith('_')):
            try:
                value = getattr(row, attr, None)
            except Exception:
                continue
            if value is None or callable(value):
                continue
            fields.append('{}={}'.format(attr, repr(value)[:40]))
        logfile.write('UNLABELLED row {} ({}): {}'.format(
            index, type(row).__name__, '; '.join(fields)[:600]))
    except Exception:
        pass


def _row_label(row, index):
    """Try hard for a real name, and record what went wrong when we fail."""
    # A Sim row has no name on it at all, so resolve the Sim ourselves before
    # falling back to "option 3".
    try:
        sim_id = getattr(row, 'sim_id', None)
        if sim_id:
            name = _name_from_id(sim_id)
            if name:
                location = getattr(row, 'sim_location', None)
                return '{} ({})'.format(name, location) if location else name
    except Exception:
        pass

    for attr in _LABEL_ATTRS:
        try:
            raw = getattr(row, attr, None)
        except Exception:
            continue
        if raw is None:
            continue
        text = loc_text(raw)
        if text:
            return text
        try:
            _label_debug.append(
                'row{} .{}: type={} hash={!r} repr={}'.format(
                    index, attr, type(raw).__name__,
                    getattr(raw, 'hash', None), repr(raw)[:60]))
        except Exception:
            pass

    tagged = None
    try:
        tagged = _label_from_tag(getattr(row, 'tag', None))
    except Exception:
        tagged = None
    if tagged:
        return tagged

    # The generic sweep: any field on the row that can become words. This is
    # what keeps a mod's own dialog from reading out as "option 1".
    try:
        generic = _generic_label(row, index)
    except Exception as ex:
        logfile.write('label: generic sweep failed ({!r})'.format(ex))
        generic = None
    if generic:
        return generic
    _log_unlabelled(row, index)
    return None


def strip_markup(text):
    """Remove <span>/<b> style tags so they are not read aloud."""
    out = []
    depth = 0
    for char in text:
        if char == '<':
            depth += 1
            continue
        if char == '>':
            if depth:
                depth -= 1
            continue
        if depth == 0:
            out.append(char)
    return ''.join(out)


# Characters the game uses to lay text out visually. A screen reader announces
# them - "bullet", "n" for a literal backslash-n - which is noise in the middle
# of a sentence that should just flow.
_BULLETS = '•·▪‣⁃●◦∙'


def readable(text):
    """Text as speech wants it: no markup, no bullets, no stray line breaks.

    A skill notification arrives as "has the following skill:\n• Guitar",
    and read literally that is "n bullet Guitar" in the middle of a sentence.
    Both real newlines and the two-character \n that some strings carry are
    turned into spaces, bullets are dropped, and the whitespace is collapsed so
    what is left reads as one sentence.
    """
    if not text:
        return text
    text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    # A bullet separates items, so it becomes a comma - otherwise a list of
    # three traits runs together into one phrase.
    for char in _BULLETS:
        text = text.replace(char, ',')
    text = strip_markup(text)
    # Collapsing on split() also removes the real newlines and tabs.
    text = ' '.join(text.split())
    # The first bullet after "skill:" is a separator with nothing before it,
    # which would leave "skill: , Guitar".
    for _pass in range(3):
        text = (text.replace(' ,', ',').replace(',,', ',')
                    .replace(':,', ':').replace('.,', '.'))
    text = text.replace(',', ', ')
    text = ' '.join(text.split())
    while text[:1] in ' ,:;-':
        text = text[1:]
    # A colon or dash left dangling before the value reads as a stumble.
    while text[-1:] in ' -,:;':
        text = text[:-1]
    return text.strip()


def resolve_plurals(text, count=1):
    """Pick the singular or plural wording out of a localised string.

    Catalog names are written {S.Garden Salad}{P.Garden Salads} - both forms in
    one string, for the client to choose between by quantity. Stripping the
    braces as if they were unfilled tokens deletes the name; leaving them reads
    the punctuation aloud. Neither is what the string means.
    """
    out = []
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char != '{':
            out.append(char)
            index += 1
            continue
        close = text.find('}', index)
        if close == -1:
            out.append(char)
            index += 1
            continue
        inner = text[index + 1:close]
        if len(inner) > 2 and inner[1] == '.' and inner[0] in 'SsPp':
            index = close + 1
            if (inner[0] in 'Pp') == (count != 1):
                out.append(inner[2:])
            continue
        # Any other placeholder is somebody else's job.
        out.append(text[index:close + 1])
        index = close + 1
    return ''.join(out)


def strip_tokens(text):
    """Drop {0.SimFirstName}-style placeholders that were never filled in."""
    # Singular/plural pairs carry real words and must be chosen between, not
    # thrown away with the rest of the braces.
    text = resolve_plurals(text)
    out = []
    depth = 0
    for char in text:
        if char == '{':
            depth += 1
            continue
        if char == '}':
            if depth:
                depth -= 1
            continue
        if depth == 0:
            out.append(char)
    return readable(''.join(out))


def _token_set(token, field):
    """Whether a protobuf field was actually set.

    This matters: an unset `number` reads back as 0.0, not None, so checking
    truthiness made every non-numeric token render as "0.0".
    """
    try:
        return token.HasField(field)
    except Exception:
        try:
            return bool(getattr(token, field, None))
        except Exception:
            return False


def _format_number(value):
    try:
        number = float(value)
    except Exception:
        return str(value)
    if number == int(number):
        return str(int(number))
    return '{:g}'.format(number)


def _token_text(token):
    """Readable text for one token, trying every field it might carry."""
    day, clock = _date_parts(token)
    if day or clock:
        return ' at '.join(part for part in (day, clock) if part)
    return _token_text_inner(token)


def _token_text_inner(token):
    """Readable text for one token, trying every field it might carry."""
    # Plain text the game already resolved.
    for attr in ('raw_text', 'text_string', 'custom_name', 'persona_string',
                 'name_prefix_string', 'custom_description'):
        if not _token_set(token, attr):
            continue
        try:
            value = getattr(token, attr, None)
        except Exception:
            continue
        if not value:
            continue
        return value if isinstance(value, str) else loc_text(value)

    # Objects, recipes, buffs and skills identify themselves by hash.
    for attr in ('catalog_name_key', 'full_name_key', 'bit_name_hash',
                 'memory_string_hash', 'name_prefix_key',
                 'catalog_description_key'):
        if not _token_set(token, attr):
            continue
        try:
            key = getattr(token, attr, None)
        except Exception:
            continue
        if key:
            text = names.lookup(key)
            if text:
                return text

    # Sims, by name or by id.
    try:
        first = getattr(token, 'first_name', '') or ''
        last = getattr(token, 'last_name', '') or ''
        joined = '{} {}'.format(first, last).strip()
        if joined:
            return joined
    except Exception:
        pass
    if _token_set(token, 'sim_id'):
        try:
            import services
            info = services.sim_info_manager().get(token.sim_id)
            if info is not None:
                joined = '{} {}'.format(
                    getattr(info, 'first_name', '') or '',
                    getattr(info, 'last_name', '') or '').strip()
                if joined:
                    return joined
        except Exception:
            pass

    # Numbers last, and only when genuinely set - this is the money value in
    # "charged {0.Money}" and the count in "{0.Number} servings".
    if _token_set(token, 'number'):
        try:
            return _format_number(token.number)
        except Exception:
            pass
    return None


def token_values(value):
    """Readable text for each token on a LocalizedString.

    Mods commonly pass raw text through a template that is nothing but a
    placeholder, so the message itself lives here rather than in the STBL
    string. Dropping tokens threw the actual content away.
    """
    out = []
    try:
        tokens = getattr(value, 'tokens', None) or ()
    except Exception:
        return out
    for token in tokens:
        try:
            out.append(_token_text(token) or '')
        except Exception:
            out.append('')
    return out


# date_and_time.populate_localization_token fills a LocalizedDateAndTimeData
# with hours, minutes and a date that is the day of the week, with 0 remapped
# to 7. So date runs 1-7 and the game's own week starts on Sunday, making 7
# Sunday and 1 Monday.
DAY_NAMES = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
             'Saturday', 'Sunday')


def _date_parts(token):
    """(day name, clock time) from a DATE_AND_TIME token, or (None, None)."""
    # A protobuf submessage is ALWAYS readable, set or not, so getattr here
    # returns an empty date on every token in the game and renders it as
    # "12:00 AM". HasField is the only honest test - which is what
    # _token_set exists for, and what this failed to use.
    data = None
    for attr in ('date_and_time', 'date'):
        if not _token_set(token, attr):
            continue
        try:
            found = getattr(token, attr, None)
        except Exception:
            continue
        if found is not None and hasattr(found, 'hours'):
            data = found
            break
    if data is None:
        return None, None
    try:
        hours = int(getattr(data, 'hours', 0) or 0)
        minutes = int(getattr(data, 'minutes', 0) or 0)
        date = int(getattr(data, 'date', 0) or 0)
    except Exception:
        return None, None
    day = DAY_NAMES[date - 1] if 1 <= date <= len(DAY_NAMES) else None
    suffix = 'AM' if hours < 12 else 'PM'
    clock = '{}:{:02d} {}'.format(hours % 12 or 12, minutes, suffix)
    return day, clock


PRONOUNS = {
    'subjective': ('he', 'she', 'they'),
    'objective': ('him', 'her', 'them'),
    'possessive': ('his', 'her', 'their'),
    'reflexive': ('himself', 'herself', 'themselves'),
}


def _token_is_female(token):
    """True, False, or None when the token does not say."""
    if not _token_set(token, 'is_female'):
        return None
    try:
        return bool(token.is_female)
    except Exception:
        return None


def _pronoun_for(token, field):
    """he/she/they for a {0.SimPronounObjective}-style field."""
    lowered = field.lower()
    for kind, words in PRONOUNS.items():
        if kind in lowered:
            female = _token_is_female(token)
            if female is True:
                return words[1]
            if female is False:
                return words[0]
            return words[2]
    return None


def _split_placeholder(inner):
    """Pull apart {0.SimName}, {M1.man} and {F1.woman}.

    The M and F forms are how the game writes gendered wording: emit the word
    only when the token's gender matches the prefix. Parsed by hand because the
    game does not ship the `re` module.
    """
    gender = ''
    rest = inner
    if rest[:1] in ('M', 'F', 'm', 'f') and rest[1:2].isdigit():
        gender = rest[0].upper()
        rest = rest[1:]
    digits = ''
    for char in rest:
        if char.isdigit():
            digits += char
        else:
            break
    field = rest[len(digits):].lstrip('.')
    return gender, digits, field


def _token_field_text(token, field, fallback):
    """Render one token for the specific field the template asked for.

    A time notification uses the same token twice - {0.DayOfWeekLong} and
    {0.TimeShort} - so substituting one string for both would read "Monday at
    9:00 AM at Monday at 9:00 AM". The field name decides which half to use.
    """
    lowered = (field or '').lower()
    pronoun = _pronoun_for(token, lowered)
    if pronoun:
        return pronoun
    # SimFirstName should be the first name, not the whole thing; reading
    # "Miranda Newman's heart race" where the game wrote "Miranda's" is clumsy.
    if 'firstname' in lowered.replace('_', ''):
        try:
            if _token_set(token, 'first_name') and token.first_name:
                return str(token.first_name)
        except Exception:
            pass
    if 'day' in lowered or 'date' in lowered or 'time' in lowered:
        day, clock = _date_parts(token)
        if day is None and clock is None:
            return fallback
        if 'time' in lowered and 'day' not in lowered:
            return clock or fallback
        if 'day' in lowered or 'date' in lowered:
            return day or clock or fallback
    return fallback


def fill_tokens(template, values, tokens=None):
    """Substitute {0.Whatever} with the matching token, rather than deleting it."""
    if not values:
        return strip_tokens(template)
    out = []
    index = 0
    length = len(template)
    while index < length:
        char = template[index]
        if char != '{':
            out.append(char)
            index += 1
            continue
        close = template.find('}', index)
        if close == -1:
            break
        inner = template[index + 1:close]
        index = close + 1
        gender, digits, field = _split_placeholder(inner)
        if not digits:
            continue
        slot = int(digits)
        if gender:
            # {M1.man}/{F1.woman}: the word itself is the payload, and only
            # the branch matching the token's gender is kept.
            token = tokens[slot] if tokens and slot < len(tokens) else None
            female = _token_is_female(token) if token is not None else None
            if female is None:
                # Gender unknown: take the masculine branch once rather than
                # emitting both words or neither.
                if gender == 'M' and field:
                    out.append(field)
            elif (gender == 'F') == female and field:
                out.append(field)
            continue
        if 0 <= slot < len(values):
            text = values[slot]
            if tokens and slot < len(tokens):
                try:
                    text = _token_field_text(tokens[slot], field, text)
                except Exception:
                    pass
            if text:
                out.append(text)
    return readable(''.join(out))


class _SimToken(object):
    """A stand-in token describing one Sim.

    Buff reasons and emotion tips are written with {0.SimFirstName} and
    {M0.his}{F0.her} in them, but they are read straight off tuning with no
    dialog and therefore no tokens - so every name and gendered word was being
    stripped, leaving "is Hungry!" and "the stress that menstrual cycle can
    cause". We know whose emotion it is, so supply that Sim as the token.

    Shaped like a protobuf token, HasField included, so it goes through exactly
    the same substitution as a real one.
    """

    __slots__ = ('first_name', 'last_name', 'is_female', '_knows_gender')

    def __init__(self, sim_info):
        self.first_name = str(getattr(sim_info, 'first_name', '') or '')
        self.last_name = str(getattr(sim_info, 'last_name', '') or '')
        self.is_female = False
        self._knows_gender = False
        try:
            from sims.sim_info_types import Gender
            gender = getattr(sim_info, 'gender', None)
            if gender is not None:
                self.is_female = gender == Gender.FEMALE
                self._knows_gender = True
        except Exception:
            pass

    def HasField(self, field):
        if field == 'is_female':
            # Claiming nothing when the gender is unknown is what makes the
            # pronoun code fall back to "they" instead of guessing "he".
            return self._knows_gender
        return field in ('first_name', 'last_name')

    @property
    def full_name(self):
        return ' '.join(part for part in (self.first_name, self.last_name)
                        if part)


def text_for_sim(value, sim_info, slots=4):
    """Resolve a LocalizedString whose tokens were never supplied.

    Used for text that describes one Sim - buff reasons, emotion tips - where
    the template's slots all refer to that Sim.
    """
    if value is None or sim_info is None:
        return loc_text(value)
    try:
        token = _SimToken(sim_info)
    except Exception:
        return loc_text(value)
    template = None
    try:
        resolved = value() if callable(value) else value
        for attr in ('hash', '_hash', 'string_hash'):
            key = getattr(resolved, attr, None)
            if key:
                template = names.lookup(key)
                if template:
                    break
    except Exception:
        template = None
    if not template:
        return loc_text(value)
    tokens = [token] * slots
    values = [token.full_name or 'your Sim'] * slots
    try:
        filled = fill_tokens(template, values, tokens)
    except Exception:
        return loc_text(value)
    return filled or loc_text(value)


def loc_text(value):
    """Best-effort plain text from a LocalizedString, str, or callable."""
    if value is None:
        return None
    if isinstance(value, str):
        return strip_tokens(value) or None
    # Raw-text LocalizedStrings carry their text inline.
    try:
        inline = getattr(value, 'text_string', None)
        if inline:
            return strip_tokens(str(inline)) or None
    except Exception:
        pass

    values = token_values(value)
    try:
        raw_tokens = list(getattr(value, 'tokens', None) or ())
    except Exception:
        raw_tokens = []
    for attr in ('hash', '_hash', 'string_hash'):
        try:
            key = getattr(value, attr, None)
            if key:
                template = names.lookup(key)
                if template:
                    filled = fill_tokens(template, values, raw_tokens)
                    if filled:
                        return filled
        except Exception:
            continue

    # No template, or the template was nothing but placeholders: the tokens
    # themselves are the message.
    joined = ' '.join(v for v in values if v).strip()
    if joined:
        return joined

    try:
        if callable(value):
            return loc_text(value())
    except Exception:
        pass
    return None


def describe_tokens(dialog):
    """What tokens a dialog's text carries, and what we made of each.

    Money and counts arrive as tokens; when one reads as blank this says
    whether the field was missing, unset, or of a shape we do not handle.
    """
    lines = []
    for attr in ('text', 'title'):
        try:
            value = getattr(dialog, attr, None)
        except Exception:
            continue
        if value is None:
            continue
        if callable(value):
            for _name, call in call_variants(value, dialog):
                try:
                    value = call()
                    break
                except Exception:
                    continue
        try:
            tokens = list(getattr(value, 'tokens', None) or ())
        except Exception:
            continue
        if not tokens:
            continue
        try:
            lines.append('{}: template hash={!r} -> {!r}'.format(
                attr, getattr(value, 'hash', None),
                names.lookup(getattr(value, 'hash', 0))))
        except Exception:
            pass
        for index, token in enumerate(tokens):
            fields = []
            for field in ('type', 'number', 'raw_text', 'text_string',
                          'first_name', 'last_name', 'sim_id',
                          'catalog_name_key', 'custom_name', 'money',
                          'date_and_time', 'hours', 'minutes',
                          'amount', 'value'):
                try:
                    if _token_set(token, field):
                        fields.append('{}={!r}'.format(
                            field, getattr(token, field, None)))
                except Exception:
                    continue
            lines.append('  token {}: {} -> {!r}'.format(
                index, ', '.join(fields) or 'no set fields',
                _token_text(token)))
    return lines


def _prune():
    live = []
    for dialog in _active:
        try:
            if dialog is not None:
                live.append(dialog)
        except Exception:
            continue
    del _active[:]
    _active.extend(live[-MAX_TRACKED:])


def service_dialogs():
    """Every dialog the game itself considers live, regardless of our hooks."""
    service = _service()
    if service is None:
        return []
    try:
        active = getattr(service, '_active_dialogs', None)
        if not active:
            return []
        try:
            return list(active.values())
        except AttributeError:
            return list(active)
    except Exception:
        return []


def current():
    """Prefer a dialog the service still considers live over our own record.

    Falling back to the service matters: if a pop-up arrives through a class we
    did not hook, our own list is empty but the service still knows about it.
    """
    _prune()
    for dialog in reversed(_active):
        state = is_open(getattr(dialog, 'dialog_id', None))
        if state is not False:
            return dialog
    from_service = service_dialogs()
    if from_service:
        return from_service[-1]
    return _active[-1] if _active else None


def clear():
    del _active[:]


def title_of(dialog, fallback=True):
    """Same rule as body_of: keep the fuller of the renderings.

    loc_text will happily call a text factory with no arguments, which strips
    the placeholders, so taking its first answer lost the tokens we had gone
    to the trouble of capturing.
    """
    for attr in ('title', 'text', 'name'):
        candidates = []
        try:
            value = getattr(dialog, attr, None)
            if value is None:
                continue
            text = loc_text(value)
            if text:
                candidates.append(text)
            if callable(value):
                for _name, call in call_variants(value, dialog):
                    try:
                        text = loc_text(call())
                    except Exception:
                        continue
                    if text:
                        candidates.append(text)
                        break
        except Exception:
            continue
        if candidates:
            return max(candidates, key=len)
    return type(dialog).__name__ if fallback else None


def _from_built_msg(dialog):
    """Notifications resolve their text when they build the client message,
    so the built message is the most reliable place to read it from."""
    for getter in (lambda: dialog.build_msg(),
                   lambda: dialog._build_ui_message_args()):
        try:
            msg = getter()
        except Exception:
            continue
        if msg is None:
            continue
        for attr in ('text', 'title', 'description', 'message'):
            try:
                text = loc_text(getattr(msg, attr, None))
                if text:
                    return text
            except Exception:
                continue
    return None


def _extra_tokens(dialog):
    """Tokens captured from the show_dialog call itself."""
    try:
        return tuple(getattr(dialog, '_a11y_extra_tokens', None) or ())
    except Exception:
        return ()


def dialog_tokens(dialog):
    """The tokens a dialog would pass into its own text.

    Built exactly the way UiDialogBase._build_localized_string_msg does it:

        tokens = ()
        if self._resolver is not None:
            if self.text_tokens is DEFAULT:
                tokens = self._resolver.get_localization_tokens()
            elif self.text_tokens is not None:
                tokens = self.text_tokens.get_tokens(self._resolver)
        return string(*(tokens + additional_tokens))

    The first version of this treated text_tokens as a sequence of tokens. It
    is not - it is a LocalizationTokens tuning object whose get_tokens(resolver)
    produces them - so tuple() over it never yielded anything usable and every
    token silently went missing. DEFAULT is a sentinel with no get_tokens, so
    testing for that method distinguishes the two cases without importing it.
    """
    resolver = getattr(dialog, '_resolver', None)
    if resolver is None:
        try:
            resolver = dialog.get_resolver()
        except Exception:
            resolver = None
    if resolver is None:
        return _extra_tokens(dialog)
    holder = getattr(dialog, 'text_tokens', None)
    get_tokens = getattr(holder, 'get_tokens', None) if holder is not None else None
    tokens = ()
    try:
        if get_tokens is not None:
            tokens = tuple(get_tokens(resolver) or ())
        else:
            from_resolver = getattr(resolver, 'get_localization_tokens', None)
            if from_resolver is not None:
                tokens = tuple(from_resolver() or ())
    except Exception as ex:
        logfile.write('dialog: token lookup failed ({!r})'.format(ex))
    # _build_localized_string_msg ends with string(*(tokens + additional_tokens)),
    # so the caller's extras belong on the end, in that order.
    return tokens + _extra_tokens(dialog)


def template_of(dialog, attr='text'):
    """The raw tuned template, placeholders and all, for spotting unfilled text."""
    try:
        value = getattr(dialog, attr, None)
    except Exception:
        return None
    if value is None:
        return None
    if callable(value):
        for _name, call in call_variants(value, dialog):
            try:
                value = call()
                break
            except Exception:
                continue
    try:
        return names.lookup(getattr(value, 'hash', 0))
    except Exception:
        return None


def call_variants(value, dialog):
    """Mod notifications wrap their text in lambdas of varying arity.

    A TunableLocalizedStringFactory takes its tokens as arguments, so calling
    it bare can yield a string whose placeholders were never filled - which is
    how "You were charged ." loses its amount.
    """
    def resolver():
        return value(dialog.get_resolver())

    def with_tokens():
        tokens = dialog_tokens(dialog)
        if not tokens:
            raise ValueError('no tokens on dialog')
        return value(*tokens)

    return (('(dialog tokens)', with_tokens),
            ('()', lambda: value()),
            ('(dialog)', lambda: value(dialog)),
            ('(resolver)', resolver),
            ('(None)', lambda: value(None)),
            ('(*empty)', lambda: value(*())))


def probe_callable(dialog, attr):
    """What each call shape returns or raises, for the log."""
    lines = []
    try:
        value = getattr(dialog, attr, None)
    except Exception as ex:
        return ['{}: getattr raised {!r}'.format(attr, ex)]
    if value is None or not callable(value):
        return lines
    for name, call in call_variants(value, dialog):
        try:
            result = call()
            lines.append('{}{} -> {} {}'.format(
                attr, name, type(result).__name__, repr(result)[:90]))
            try:
                lines.append('    loc_text -> {!r}'.format(loc_text(result)))
            except Exception as ex:
                lines.append('    loc_text raised {!r}'.format(ex))
        except Exception as ex:
            lines.append('{}{} raised {!r}'.format(attr, name, ex))
    return lines


def body_of(dialog):
    """The message text of a notification or pop-up, not just its title.

    Two routes reach the text and neither always wins. The game's own
    build_msg renders a dialog exactly as the client would - except that a
    caller's additional_tokens never reach it, so a bill comes out as
    "That'll be ." Calling the text factory with the tokens we captured fills
    those in, but falls back to a bare call when a dialog has no tokens, which
    strips placeholders instead.

    So take both and keep whichever kept more of the message. A filled string
    is always longer than the same string with its placeholders removed, and
    this was returning build_msg first and never looking at the other one.
    """
    candidates = []
    built = _from_built_msg(dialog)
    if built:
        candidates.append(built)
    for attr in ('text', 'description', 'message', 'subtitle'):
        try:
            value = getattr(dialog, attr, None)
        except Exception:
            continue
        if value is None:
            continue
        if callable(value):
            for _name, call in call_variants(value, dialog):
                try:
                    text = loc_text(call())
                except Exception:
                    continue
                if text:
                    candidates.append(text)
                    break
        else:
            text = loc_text(value)
            if text:
                candidates.append(text)
        if candidates:
            break
    if not candidates:
        return None
    return max(candidates, key=len)


def rows_of(dialog):
    try:
        rows = getattr(dialog, 'picker_rows', None)
        if rows:
            return list(rows)
    except Exception:
        pass
    return []


def _responses_of(dialog):
    """Every button the game itself would draw on this dialog."""
    for getter in (lambda: list(dialog._get_responses_gen()),
                   lambda: list(getattr(dialog, 'responses', None) or ()),
                   lambda: list(getattr(dialog, '_additional_responses', None) or ()),
                   lambda: list(getattr(dialog, 'ui_responses', None) or ())):
        try:
            found = getter()
        except Exception:
            continue
        if found:
            return found
    return []


def _response_label(response, dialog):
    """A button's text, which may be a factory needing the dialog's tokens."""
    value = getattr(response, 'text', None)
    if value is None:
        return 'option'
    text = loc_text(value)
    if text:
        return text
    if callable(value):
        for _name, call in call_variants(value, dialog):
            try:
                text = loc_text(call())
            except Exception:
                continue
            if text:
                return text
    return 'option'


def is_purchase_picker(dialog):
    """Does this dialog sell things by the unit?"""
    if dialog is None:
        return False
    if 'purchase' in type(dialog).__name__.lower():
        return True
    for row in rows_of(dialog):
        return hasattr(row, 'def_id') and hasattr(row, 'num_owned')
    return False


def definition_price(def_id):
    """What one of these costs, or None."""
    if not def_id:
        return None
    try:
        import services
        definition = services.definition_manager().get(def_id)
        price = getattr(definition, 'price', None)
        return int(price) if price else None
    except Exception:
        return None


def row_def_id(row):
    try:
        return getattr(row, 'def_id', None)
    except Exception:
        return None


def buy_cart(dialog, cart):
    """Buy everything in the cart, then confirm.

    Two steps, because the game uses two. dialog_pick_result_def_ids_and_counts
    only STORES the selection - pick_definitions_ids_and_counts just assigns
    picked_def_ids, picked_def_counts and ingredient_check on the dialog and
    returns. Nothing is bought until the dialog's OK response runs the callback
    that reads them. Sending only the picks looked like success and bought
    nothing, which is exactly what it did.

    `cart` is [(def_id, count)].
    """
    global _last_error, _last_route
    _last_error = None
    _last_route = None
    if not cart:
        _last_error = 'nothing selected'
        return False
    dialog_id = getattr(dialog, 'dialog_id', None)
    connection = None
    try:
        import services
        client = services.client_manager().get_first_client()
        connection = getattr(client, 'id', None)
    except Exception:
        connection = None
    try:
        import services
        service = services.current_zone().ui_dialog_service
    except Exception as ex:
        _last_error = 'no dialog service ({!r})'.format(ex)
        return False

    def_ids = [int(def_id) for def_id, _count in cart]
    counts = [int(count) for _def_id, count in cart]
    stored = False
    for check in (False, True):
        try:
            if service.dialog_pick_result_def_ids_and_counts(
                    dialog_id=dialog_id, picked_def_ids=def_ids,
                    picked_counts=counts, ingredient_check=check):
                stored = True
                logfile.ok('purchase: {} lines recorded (check={})'.format(
                    len(cart), check))
                break
        except Exception as ex:
            logfile.write('purchase: recording failed ({!r})'.format(ex))
    if not stored:
        _last_error = 'the game would not accept the selection'
        logfile.fail('purchase: selection refused')
        return False

    # Everything the interaction will read, recorded before we respond. The
    # callback (picker_interaction.on_picker_selected) takes
    # get_result_definitions_and_counts() straight off the dialog, so if that
    # is empty or wrong here, the purchase was lost before the response.
    try:
        live = service.get_dialog(dialog_id)
        logfile.write('purchase: before respond, dialog={!r} ids={!r} '
                      'counts={!r} multi_select={!r} accepted={!r}'.format(
                          type(live).__name__ if live else None,
                          getattr(live, 'picked_def_ids', None),
                          getattr(live, 'picked_def_counts', None),
                          getattr(live, 'multi_select', None),
                          getattr(live, 'accepted', None)))
        try:
            logfile.write('purchase: result tuple {!r}'.format(
                live.get_result_definitions_and_counts()))
        except Exception as ex:
            logfile.write('purchase: result tuple failed ({!r})'.format(ex))
        import services as _services
        logfile.write('purchase: purchase_picker_service={!r}'.format(
            _services.purchase_picker_service()))
    except Exception as ex:
        logfile.write('purchase: pre-respond probe failed ({!r})'.format(ex))

    # The response is what actually buys.
    try:
        from server_commands.ui_commands import ui_dialog_respond
    except Exception as ex:
        _last_error = 'no respond command ({!r})'.format(ex)
        return False
    # UiDialogBase.respond ends with self._listeners(self) - that is what runs
    # the picker's callback. Log whether anything is actually listening: an
    # empty list means the response goes nowhere no matter how correct it is.
    try:
        live = service.get_dialog(dialog_id)
        listeners = getattr(live, '_listeners', None)
        logfile.write('purchase: listeners={!r} count={}'.format(
            listeners, len(listeners) if hasattr(listeners, '__len__') else '?'))
    except Exception as ex:
        logfile.write('purchase: listener probe failed ({!r})'.format(ex))

    # ONE response, and only ever an affirmative one. respond() runs the
    # listener - PurchasePickerInteraction._on_picker_selected - which is what
    # buys. It does NOT remove the dialog from the service's active list, so
    # "is it still listed" was the wrong test: it stayed true after a purchase
    # that had already succeeded, and the code went on to send four more
    # responses including CANCEL. Never iterate responses on a purchase.
    ok_ids = []
    try:
        from ui.ui_dialog import ButtonType
        for attr in ('DIALOG_RESPONSE_OK', 'DIALOG_RESPONSE_OK_ALT'):
            value = getattr(ButtonType, attr, None)
            if value is not None:
                ok_ids.append(int(value))
    except Exception:
        pass
    if not ok_ids:
        ok_ids = [10001]

    live = None
    try:
        live = service.get_dialog(dialog_id)
    except Exception:
        live = None
    # Money moving is the only proof a purchase actually happened; the
    # shop's thank-you notification appears either way.
    try:
        import services as _s
        _h = _s.active_household()
        logfile.write('purchase: funds before = {!r}'.format(
            getattr(getattr(_h, 'funds', None), 'money', None)))
    except Exception:
        pass
    for response_id in ok_ids:
        try:
            if live is not None and hasattr(live, 'respond'):
                live.respond(response_id)
            else:
                ui_dialog_respond(dialog_id, response_id, connection)
        except Exception as ex:
            logfile.write('purchase: respond({}) raised {!r}'.format(
                response_id, ex))
            continue
        # The dialog recording the response is the confirmation; the game
        # tears the dialog down on its own schedule.
        answered = True
        try:
            if live is not None:
                answered = getattr(live, 'response', response_id) == response_id
        except Exception:
            answered = True
        if answered:
            _last_route = 'respond({})'.format(response_id)
            try:
                import services as _s
                _h = _s.active_household()
                logfile.write('purchase: funds after = {!r}'.format(
                    getattr(getattr(_h, 'funds', None), 'money', None)))
            except Exception:
                pass
            logfile.ok('purchase: bought via respond({})'.format(response_id))
            return True
        logfile.write('purchase: respond({}) was not recorded'.format(response_id))

    _last_error = 'the shop would not close'
    logfile.fail('purchase: confirm did not take')
    return False


def options(dialog):
    """[(label, kind, payload)] for whatever this dialog is offering."""
    if dialog is None:
        return []
    out = []

    del _label_debug[:]
    # Editable fields come first: on the age-up screen the name is the thing
    # you are actually there to change, and it sat unreachable while the mod
    # only ever offered the buttons.
    for name in _text_input_names(dialog):
        current = _text_input_value(dialog, name)
        out.append(('{}, currently {}, enter to type a new one'.format(
            _text_input_label(name), current or 'empty'), 'textfield', name))
    fields_only = len(out)
    at_label = {}
    counts = {}
    repeats = 0
    for index, row in enumerate(rows_of(dialog)):
        label = _row_label(row, index)
        if not label:
            label = 'option {}'.format(index + 1)
        try:
            if getattr(row, 'is_enable', True) is False:
                label += ' (unavailable)'
        except Exception:
            pass
        # A row that reads exactly like one already in the list is not a
        # choice: whatever makes the two different is something only a sighted
        # player can see. Fold it into the first one and count it.
        position = at_label.get(label)
        if position is not None:
            repeats += 1
            counts[position] = counts.get(position, 1) + 1
            _base, kind, first = out[position]
            out[position] = ('{} ({} of these)'.format(label,
                                                       counts[position]),
                             kind, first)
            continue
        at_label[label] = len(out)
        out.append((label, 'row', row))
    if repeats:
        logfile.write('dialog: folded {} rows that read the same as one '
                      'already listed'.format(repeats))
    if len(out) > fields_only:
        # A picker's rows are only half of it: the real UI also has a confirm
        # button, which is how you travel alone or accept an empty selection.
        out.append(('Confirm and buy what is in your basket'
                    if is_purchase_picker(dialog)
                    else 'Confirm with nothing selected',
                    'confirm_none', None))
        try:
            from ui.ui_dialog import ButtonType
            cancel = getattr(ButtonType, 'DIALOG_RESPONSE_CANCEL', None)
        except Exception:
            cancel = None
        if cancel is not None:
            out.append(('Cancel', 'button', cancel))
        # The dialog's OWN buttons, which a picker never offered before: this
        # returned early after the rows and the two synthetic entries above,
        # so the map screen's real Confirm was never once pressed. A screen
        # the client draws itself is far likelier to put itself away when it
        # gets the button it is actually waiting on than when the mod
        # improvises one.
        for response in _responses_of(dialog):
            response_id = getattr(response, 'dialog_response_id', None)
            if response_id is not None and response_id == cancel:
                continue          # already offered, and once is enough
            label = _response_label(response, dialog)
            if not label or label == 'option':
                label = 'Confirm'
            label = "{} (the game's own button)".format(label)
            if response_id is None:
                out.append((label, 'response', response))
            else:
                out.append((label, 'button', response_id))
        return out

    # _get_responses_gen is what build_msg iterates to draw the buttons, so it
    # is the authoritative list for every dialog type, including a mod's own.
    # It yields from responses, _additional_responses AND ui_responses - and
    # reading only `responses` found nothing on a yes/no pop-up, which is how
    # a two-button question came out as a lone "Okay".
    for response in _responses_of(dialog):
        label = _response_label(response, dialog)
        response_id = getattr(response, 'dialog_response_id', None)
        if not label or label == 'option':
            # A button with no readable text is almost always the single
            # confirm on a screen like the age-up one. "Done" is what it says
            # on screen; "option" tells you nothing.
            label = 'Done'
        if response_id is None:
            out.append((label, 'response', response))
        else:
            out.append((label, 'button', response_id))
    if out:
        return out

    # Ok/cancel dialogs - an incoming call is one of these - keep their button
    # text in text_ok and text_cancel rather than in a responses list.
    ids = _ok_response_ids()
    ok_id = ids[0] if ids else 0
    cancel_id = None
    try:
        from ui.ui_dialog import ButtonType
        cancel_id = getattr(ButtonType, 'DIALOG_RESPONSE_CANCEL', None)
    except Exception:
        cancel_id = None
    for attr, fallback, response_id in (
            ('text_ok', 'Accept', ok_id), ('ok_text', 'Accept', ok_id),
            ('text_cancel', 'Decline', cancel_id),
            ('cancel_text', 'Decline', cancel_id)):
        try:
            value = getattr(dialog, attr, None)
        except Exception:
            continue
        if value is None:
            continue
        label = None
        if callable(value):
            for call in (lambda: value(), lambda: value(dialog)):
                try:
                    label = loc_text(call())
                    if label:
                        break
                except Exception:
                    continue
        if not label:
            label = loc_text(value)
        out.append((label or fallback, 'button',
                    ok_id if response_id is None else response_id))
    if out:
        return out

    # Nothing found. A yes/no pop-up reaching here reads as a lone "Okay",
    # so record what the dialog actually carries instead of guessing again.
    try:
        fields = []
        for attr in sorted(a for a in dir(dialog) if not a.startswith('_')):
            lowered = attr.lower()
            if not any(hint in lowered for hint in
                       ('ok', 'cancel', 'response', 'button', 'choice',
                        'option', 'text')):
                continue
            try:
                value = getattr(dialog, attr, None)
            except Exception:
                continue
            if value is None or callable(value):
                continue
            fields.append('{}={}'.format(attr, repr(value)[:50]))
        logfile.write('dialog {} had no options; carries: {}'.format(
            type(dialog).__name__, '; '.join(fields)[:500]))
    except Exception:
        pass
    return [('OK', 'ok', 0)]


def describe(dialog):
    if dialog is None:
        return 'No dialog.'
    items = options(dialog)
    title = title_of(dialog, fallback=False)
    body = body_of(dialog)
    parts = []
    if title:
        parts.append(title)
    if not title and not body:
        parts.append('Notification, text could not be read')
    # Notifications carry their meaning in the body, not the title.
    if body and body != title:
        parts.append(body)
    if len(items) == 1:
        parts.append('press enter to dismiss')
    else:
        parts.append('{} options. {}.'.format(
            len(items), items[0][0] if items else 'none'))
    return '. '.join(parts)


def _client_id():
    try:
        import services
        client = services.client_manager().get_first_client()
        return getattr(client, 'id', None)
    except Exception:
        return None


def _params_of(func):
    """The real parameter names of a command function, or ()."""
    for target in (func, getattr(func, '__wrapped__', None),
                   getattr(func, '__func__', None)):
        code = getattr(target, '__code__', None)
        if code is not None:
            try:
                return tuple(code.co_varnames[:code.co_argcount])
            except Exception:
                continue
    return ()


def signature_report():
    """What the ui command functions actually look like in this build."""
    lines = []
    try:
        from server_commands import ui_commands
    except Exception as ex:
        return ['ui_commands import FAILED: {!r}'.format(ex)]
    for name in ('ui_dialog_pick_result', 'ui_dialog_pick_result_with_recipe_id',
                 'ui_dialog_respond', 'ui_dialog_auto_respond',
                 'ui_dialog_multi_picker_result'):
        func = getattr(ui_commands, name, None)
        if func is None:
            lines.append('{}: MISSING'.format(name))
            continue
        lines.append('{}: {} params={}'.format(
            name, type(func).__name__, _params_of(func)))
    return lines


def _call(func_name, args):
    """Call a server command function, adapting to its real signature.

    sims4.commands.execute hides argument errors and its return value does not
    reliably mean success, so we call the function itself and let it raise.
    """
    global _last_error
    try:
        from server_commands import ui_commands
    except Exception as ex:
        _last_error = 'ui_commands import failed {!r}'.format(ex)
        return False
    func = getattr(ui_commands, func_name, None)
    if func is None:
        _last_error = '{} not present'.format(func_name)
        return False

    params = _params_of(func)
    attempts = [lambda: func(*args, _connection=_client_id()),
                lambda: func(*args)]
    # If it takes more positionals than we have, pad with the connection.
    positional = [p for p in params if p != '_connection']
    if len(positional) > len(args):
        padded = tuple(args) + (None,) * (len(positional) - len(args))
        attempts.append(lambda: func(*padded, _connection=_client_id()))

    errors = []
    for attempt in attempts:
        try:
            attempt()
            return True
        except TypeError as ex:
            errors.append(repr(ex))
            continue
        except Exception as ex:
            _last_error = '{} raised {!r} (params={})'.format(
                func_name, ex, params)
            return False
    _last_error = '{} params={} rejected args {}: {}'.format(
        func_name, params, args, '; '.join(errors[:2]))
    return False


def _ok_response_ids():
    """Every plausible "dismiss this" response id, best first."""
    ids = []
    try:
        from ui.ui_dialog import ButtonType
        for attr in ('DIALOG_RESPONSE_OK', 'DIALOG_RESPONSE_CLOSED',
                     'DIALOG_RESPONSE_CANCEL'):
            value = getattr(ButtonType, attr, None)
            if value is not None:
                ids.append(int(value))
    except Exception:
        pass
    for fallback in (0, 1, -1):
        if fallback not in ids:
            ids.append(fallback)
    return ids


def _service():
    """The zone's UiDialogService: the authority on which dialogs are live."""
    try:
        import services
        return services.ui_dialog_service()
    except Exception:
        return None


def is_open(dialog_id):
    """True/False if we can tell, None if we cannot."""
    service = _service()
    if service is None or dialog_id is None:
        return None
    try:
        return service.get_dialog(dialog_id) is not None
    except Exception:
        pass
    try:
        active = getattr(service, '_active_dialogs', None)
        if active is not None:
            return dialog_id in active
    except Exception:
        pass
    return None


def _service_respond(dialog_id, response_id):
    service = _service()
    if service is None:
        raise RuntimeError('no ui_dialog_service')
    service.dialog_respond(dialog_id, response_id)


# A destination chosen on the map but not yet confirmed, keyed by dialog.
_pending_pick = {}


def is_map_view(dialog):
    try:
        return 'mapview' in type(dialog).__name__.lower().replace('_', '')
    except Exception:
        return False


def selects_before_confirming(dialog, index):
    """Should pressing enter here SELECT rather than travel?

    On the real map you click a lot to highlight it and then click Confirm.
    The mod was doing both at once - one press picked the destination and
    committed it - so the game never saw the two-step it expects, and the
    panel it draws itself was never told the interaction was finished.

    Only the map behaves this way. Shops, Sim pickers and the rest already
    work, and rewiring them to chase this would be trading a fix for a
    regression.
    """
    if not is_map_view(dialog):
        return False
    items = options(dialog)
    if not items or index < 0 or index >= len(items):
        return False
    return items[index][1] == 'row'


def select_row(dialog, index):
    """Mark a destination as chosen, without going anywhere yet."""
    items = options(dialog)
    if not items or index < 0 or index >= len(items):
        return 'Nothing to choose.'
    label, kind, row = items[index]
    if kind != 'row':
        return 'That is not a destination.'
    option_id = getattr(row, 'option_id', None)
    _pending_pick[id(dialog)] = (option_id, row, label)
    # Tell the dialog too, so anything reading its state sees the selection.
    for attr, value in (('picked_results', (option_id,)),
                        ('current_selected', 1)):
        try:
            setattr(dialog, attr, value)
        except Exception:
            pass
    logfile.write('dialog: {!r} selected (option {}), waiting for the '
                  'confirm button'.format(label, option_id))
    return '{} selected. Now choose Confirm to travel.'.format(label)


def pending_pick(dialog):
    return _pending_pick.get(id(dialog))


def _picked_then_respond(dialog, dialog_id, row):
    """Record the pick the way the dialog reads it back, then say OK.

    get_result_rows is [row for row in picker_rows if row.option_id in
    picked_results], and get_result_tags returns those rows' tags. A picker
    interaction pushes its continuation from those tags - so a pick that does
    not land in picked_results leaves the interaction with nothing to do, and
    the step that should follow never appears. That is the missing "what to
    cook" after choosing who to cook with.
    """
    option_id = getattr(row, 'option_id', None)
    try:
        dialog.picked_results = (option_id,)
    except Exception as ex:
        logfile.write('dialog: could not set picked_results ({!r})'.format(ex))
    # Harmless where it is unused, and some pickers read it for their own
    # bookkeeping.
    try:
        row.is_selected = True
    except Exception:
        pass
    # What the interaction will actually see. Guessing at this has cost
    # several rounds; the dialog can simply be asked.
    try:
        tags = list(dialog.get_result_tags())
    except Exception as ex:
        tags = 'unreadable ({!r})'.format(ex)
    logfile.write('dialog: picked option {} -> result tags {}'.format(
        option_id, tags))
    before = _sim_work()
    _service_respond(dialog_id, _ok_response_ids()[0])
    after = _sim_work()
    # respond() ends with self._listeners(self), which is what runs the
    # picker's _on_picker_selected and pushes its continuation. So the
    # question is not whether we answered - accepted says we did - but
    # whether anything was queued as a result. These two lines tell those
    # apart, and guessing between them has already cost several rounds.
    try:
        logfile.write('dialog: after responding accepted={!r}, queue {} -> {}'
                      .format(getattr(dialog, 'accepted', None),
                              before, after))
    except Exception:
        pass


def _sim_work():
    """What the active Sim is queued to do, for spotting a pushed continuation."""
    try:
        import a11yscan_world as world
        sim = world.active_sim()
        queued = [type(i).__name__ for i in sim.queue]
        running = [type(i).__name__ for i in sim.si_state]
        return '{} queued {}, running {}'.format(
            len(queued), queued[:4], running[:4])
    except Exception as ex:
        return 'unreadable ({!r})'.format(ex)


def send_close_request(dialog_id):
    """Tell the CLIENT to put this dialog's panel away.

    Responding to a dialog only settles it on the server: the entry leaves
    _active_dialogs, every check the mod has says it worked, and the panel is
    still on screen. That is the map screen after travelling and the age-up
    screen after Done - both stuck, both "successful".

    The client closes on a message, not on a response. The game sends it in
    UiDialogService._dialog_cancel_internal:

        msg = Dialog_pb2.UiDialogCloseRequest()
        msg.dialog_id = dialog.dialog_id
        Distributor.instance().add_event(Consts_pb2.MSG_UI_DIALOG_CLOSE, msg)

    dialog_cancel() cannot be reused for this because it looks the dialog up
    in _active_dialogs first, and by the time we have answered it is no longer
    there. Sending the message directly works either way - it names the dialog
    by id and closes exactly that one, so it cannot wander off and shut
    something else.
    """
    if not dialog_id:
        return False
    try:
        from protocolbuffers import Dialog_pb2, Consts_pb2
    except Exception as ex:
        logfile.write('dialog: no close protobufs ({!r})'.format(ex))
        return False
    distributor = None
    for get in (lambda: __import__('distributor.system',
                                   fromlist=['Distributor']).Distributor.instance(),
                lambda: __import__('distributor.rollback',
                                   fromlist=['ProtocolBufferRollback'])):
        try:
            distributor = get()
            break
        except Exception:
            continue
    if distributor is None:
        logfile.write('dialog: no distributor to send the close on')
        return False
    try:
        msg = Dialog_pb2.UiDialogCloseRequest()
        msg.dialog_id = dialog_id
        distributor.add_event(Consts_pb2.MSG_UI_DIALOG_CLOSE, msg)
        logfile.ok('dialog: sent the client a close request for {}'.format(
            dialog_id))
        return True
    except Exception as ex:
        logfile.write('dialog: close request failed ({!r})'.format(ex))
        return False


def _close_after(dialog_id, dialog=None):
    """Follow a successful answer with a view-closing response, if needed.

    The dialog is passed in rather than looked up: answering it takes it out of
    both the service and our own list, so by the time we get here there is
    nothing left to find - which is why the follow-up silently never ran.
    """
    # Every answered dialog gets this, not a chosen few. It names one dialog
    # by id, so a panel that had already gone simply ignores it - unlike the
    # synthesized Escape this replaces, which could only ever be aimed at
    # whatever happened to be on screen.
    try:
        send_close_request(dialog_id)
    except Exception as ex:
        logfile.write('dialog: close request failed ({!r})'.format(ex))
    # Whether the answer led anywhere is worth recording: a picker that pushes
    # a continuation should be followed by another dialog within a moment, and
    # silence after this line is the symptom of a continuation that never ran.
    logfile.write('dialog: {} answered and closed'.format(dialog_id))
    try:
        if dialog is None:
            for candidate in list(_active):
                if getattr(candidate, 'dialog_id', None) == dialog_id:
                    dialog = candidate
                    break
        if dialog is not None:
            close_client_view(dialog, dialog_id)
    except Exception as ex:
        logfile.write('dialog: close follow-up failed ({!r})'.format(ex))


def close_client_view(dialog, dialog_id):
    """Tell the client to put a full-screen picker away.

    The map picker opens a map VIEW in the client. Answering with a pick result
    satisfies the server - the dialog leaves _active_dialogs, so every check we
    have says it worked - but the client keeps the map on screen and there is
    no way out of it with the keyboard. The client closes it on the dialog's
    RESPONSE, exactly as a shop needs picks AND a confirm.

    Sent after the pick has already been accepted, so a failure here costs
    nothing but a log line.
    """
    name = type(dialog).__name__.lower() if dialog is not None else ''
    flat = name.replace('_', '')
    # A short list, not every dialog. Escape with nothing on screen opens the
    # pause menu, which is its own trap - so only panels known to survive the
    # server closing them get this treatment.
    #
    # Travel is a Sim picker followed by a map picker, and sending a closing
    # response to the Sim picker ended the flow before the map ever appeared.
    # The age-up screen is the other one: the server accepts Done and drops
    # the dialog, the client leaves the panel up, and the game is stuck behind
    # a modal nothing server-side can still reach.
    if not any(hint in flat for hint in
               ('mapview', 'personalityassignment')):
        logfile.write('dialog: {} is not a map view, leaving it alone'.format(
            type(dialog).__name__ if dialog is not None else None))
        return False
    sent = []
    for response_id in _ok_response_ids()[:2]:
        for label, call in (
                ('dialog.respond', lambda r=response_id: dialog.respond(r)),
                ('service respond',
                 lambda r=response_id: _service_respond(dialog_id, r))):
            try:
                call()
                sent.append('{}({})'.format(label, response_id))
            except Exception:
                continue
    # No synthesized Escape here any more. It reached Windows - SendInput
    # reported inserting both events - and the map screen ignored it, so the
    # key was never what closes these panels.
    if sent:
        logfile.write('dialog: asked the client to close {} via {}'.format(
            type(dialog).__name__, ', '.join(sent)))
    # No synthesized Escape. SendInput reported inserting both events and the
    # map ignored them, so the key was never what closes this - it was only
    # ever noise in the log. send_close_request, which _close_after sends for
    # every answered dialog, is the client-facing message that should do it.
    return True


# What the player has typed into a dialog but not yet sent, keyed by dialog.
_pending_text = {}


def _text_input_names(dialog):
    try:
        inputs = getattr(dialog, 'text_inputs', None)
        return list(inputs) if inputs else []
    except Exception:
        return []


def _text_input_label(name):
    import a11yscan_world as world
    label = world.prettify(str(name))
    return label if label and label != 'object' else str(name)


def _text_input_value(dialog, name):
    pending = _pending_text.get(id(dialog), {})
    if name in pending:
        return pending[name]
    try:
        existing = getattr(dialog, 'text_input_responses', None) or {}
        if existing.get(name):
            return existing[name]
    except Exception:
        pass
    return _text_input_default(dialog, name)


def _text_input_default(dialog, name):
    """What to put in a field we were never given a value for.

    The age-up dialog's field is the Sim's name, already filled in on screen.
    Sending their current name back means answering the dialog does not
    quietly rename anybody.
    """
    lowered = str(name).lower()
    sim_info = None
    for getter in (lambda: dialog.get_text_input_reference_sim(),
                   lambda: dialog._target_sim_info,
                   lambda: dialog.owner):
        try:
            sim_info = getter()
        except Exception:
            continue
        if sim_info is not None:
            break
    if sim_info is None:
        return ''
    first = getattr(sim_info, 'first_name', '') or ''
    last = getattr(sim_info, 'last_name', '') or ''
    if 'last' in lowered or 'surname' in lowered or 'family' in lowered:
        return last
    if 'first' in lowered or 'name' in lowered:
        return first
    return first


def _fill_text_inputs(dialog):
    """Send a text-input dialog's fields before pressing any of its buttons.

    A UiDialogTextInput - which is what the age up and age down screen is -
    will not act on a button until every text field has been sent to it. The
    real client does that as you type. The mod never did, so its Done did
    nothing at all, on any route, and the dialog just sat there.

    This is the same order the game's own do_auto_respond uses: fill every
    input through on_text_input, then respond.
    """
    if dialog is None:
        return 0
    try:
        inputs = getattr(dialog, 'text_inputs', None)
    except Exception:
        return 0
    if not inputs:
        return 0
    try:
        existing = dict(getattr(dialog, 'text_input_responses', None) or {})
    except Exception:
        existing = {}
    pending = _pending_text.get(id(dialog), {})
    filled = 0
    for name in list(inputs):
        value = pending.get(name) or existing.get(name)
        if not value:
            value = _text_input_default(dialog, name)
        # A field with a minimum length rejects a short answer, and a rejected
        # field leaves the dialog unanswerable - so pad only as a last resort,
        # never over a real name.
        try:
            minimum = int(getattr(inputs[name], 'min_length', 0) or 0)
        except Exception:
            minimum = 0
        if minimum and len(value) < minimum:
            value = (value or 'Sim').ljust(minimum, 'x')
        try:
            accepted = dialog.on_text_input(name, value)
        except Exception as ex:
            logfile.write('dialog: text input {!r} raised {!r}'.format(name, ex))
            continue
        if accepted:
            filled += 1
        logfile.write('dialog: text input {!r} = {!r} ({})'.format(
            name, value, 'accepted' if accepted else 'refused'))
    if filled:
        logfile.write('dialog: filled {} text field(s) before answering'.format(
            filled))
    return filled


def _run_routes(dialog_id, routes, dialog=None):
    """Try each route and VERIFY against the dialog service, rather than
    trusting a return value. A route only counts if the dialog actually goes
    away, which is the one signal that cannot lie to us."""
    global _last_error, _last_route
    # Must happen before any route runs: a text-input dialog ignores its own
    # buttons until its fields have been sent.
    try:
        _fill_text_inputs(dialog)
    except Exception as ex:
        logfile.write('dialog: could not fill text inputs ({!r})'.format(ex))
    failures = []
    for name, call in routes:
        try:
            call()
        except Exception as ex:
            failures.append('{}: {!r}'.format(name, ex))
            logfile.write('dialog route {} raised {!r}'.format(name, ex))
            continue
        still_open = is_open(dialog_id)
        if still_open is False:
            _last_route = '{} (verified closed)'.format(name)
            logfile.ok('dialog answered via {}'.format(name))
            _close_after(dialog_id, dialog)
            return True
        if still_open is None:
            _last_route = '{} (could not verify)'.format(name)
            logfile.write('dialog route {} ran, could not verify'.format(name))
            _close_after(dialog_id, dialog)
            return True
        failures.append('{}: ran but dialog still open'.format(name))
        logfile.write('dialog route {} ran but dialog still open'.format(name))
    _last_error = '; '.join(failures[:4]) or 'no route worked'
    logfile.fail('no dialog route worked: {}'.format(_last_error[:200]))
    return False


def dismiss(dialog):
    """Close a dialog we could not otherwise answer, so the player is never
    left stuck behind a modal pop-up they cannot click."""
    dialog_id = getattr(dialog, 'dialog_id', None)
    if dialog_id is None:
        return False
    routes = []
    for response_id in _ok_response_ids():
        routes.append(('service respond({})'.format(response_id),
                       lambda rid=response_id: _service_respond(dialog_id, rid)))
        routes.append(('ui_dialog_respond({})'.format(response_id),
                       lambda rid=response_id: _call('ui_dialog_respond',
                                                     (dialog_id, rid))))
    routes.append(('auto_respond', lambda: _call('ui_dialog_auto_respond',
                                                 (dialog_id,))))
    routes.append(('dialog.respond', lambda: dialog.respond(_ok_response_ids()[0])))
    return _run_routes(dialog_id, routes, dialog)


def is_text_field(dialog, index):
    """Is option `index` an editable field rather than a button?"""
    items = options(dialog)
    if not items or index < 0 or index >= len(items):
        return False
    return items[index][1] == 'textfield'


def begin_edit(dialog, index):
    """Start typing into one of the dialog's fields.

    Returns what to say. The dialog stays open and stays the current mode -
    what is typed is held here until a button is pressed, exactly like typing
    into the box on screen and then clicking Done.
    """
    import a11yscan_typing as typing
    items = options(dialog)
    if not items or index < 0 or index >= len(items):
        return 'Nothing to edit.'
    _label, kind, name = items[index]
    if kind != 'textfield':
        return 'That is not something you can type into.'

    def _store(text, dialog=dialog, name=name):
        _pending_text.setdefault(id(dialog), {})[name] = text
        logfile.write('dialog: {!r} will be sent as {!r}'.format(name, text))
        return '{} set to {}. Now choose Done.'.format(
            _text_input_label(name), text)

    return typing.start(name, _text_input_label(name),
                        _text_input_value(dialog, name), _store)


def choose(dialog, index):
    """Answer the dialog with option `index`."""
    global _last_error, _last_route
    _last_error = None
    _last_route = None
    items = options(dialog)
    if not items or index < 0 or index >= len(items):
        _last_error = 'index out of range'
        return False
    label, kind, payload = items[index]
    dialog_id = getattr(dialog, 'dialog_id', None)
    if dialog_id is None:
        _last_error = 'dialog has no dialog_id'
        return False

    if kind == 'row':
        option_id = getattr(payload, 'option_id', None)
        if option_id is None:
            _last_error = 'row has no option_id'
            return False
        routes = [
            ('picked_results + service respond',
             lambda: _picked_then_respond(dialog, dialog_id, payload)),
            ('pick_result_with_recipe_id',
             lambda: _call('ui_dialog_pick_result_with_recipe_id',
                           (dialog_id, option_id))),
            # (dialog_id, ingredient_check, prepped_ingredient_check, *choices)
            ('pick_result',
             lambda: _call('ui_dialog_pick_result',
                           (dialog_id, False, False, option_id))),
            ('multi_picker_result',
             lambda: _call('ui_dialog_multi_picker_result',
                           (dialog_id, option_id))),
            ('service respond(option_id)',
             lambda: _service_respond(dialog_id, option_id)),
            ('dialog.respond(option_id)', lambda: dialog.respond(option_id)),
        ]
        return _run_routes(dialog_id, routes, dialog)

    if kind == 'confirm_none':
        routes = [
            ('pick_result with no choices',
             lambda: _call('ui_dialog_pick_result', (dialog_id, False, False))),
            ('respond ok',
             lambda: _service_respond(dialog_id, _ok_response_ids()[0])),
        ]
        return _run_routes(dialog_id, routes, dialog)

    if kind == 'button':
        chosen = _pending_pick.pop(id(dialog), None)
        if chosen is not None:
            option_id, row, chosen_label = chosen
            logfile.write('dialog: confirming {!r} (option {})'.format(
                chosen_label, option_id))
            # Set the pick, then press the game's own button. This is the
            # order the client uses: the selection is already on the dialog by
            # the time Confirm is clicked.
            try:
                dialog.picked_results = (option_id,)
            except Exception:
                pass
            routes = [
                ('pick_result then the real button',
                 lambda: (_call('ui_dialog_pick_result',
                                (dialog_id, False, False, option_id)),
                          _call('ui_dialog_respond', (dialog_id, payload)))),
                ('the real button',
                 lambda: _call('ui_dialog_respond', (dialog_id, payload))),
                ('service respond', lambda: _service_respond(dialog_id, payload)),
            ]
            return _run_routes(dialog_id, routes, dialog)
        routes = [
            ('service respond', lambda: _service_respond(dialog_id, payload)),
            ('ui_dialog_respond',
             lambda: _call('ui_dialog_respond', (dialog_id, payload))),
            ('dialog.respond', lambda: dialog.respond(payload)),
        ]
        return _run_routes(dialog_id, routes, dialog)

    if kind == 'response':
        response_id = getattr(payload, 'dialog_response_id', None)
        if response_id is None:
            response_id = _ok_response_ids()[0]
        routes = [
            ('service respond', lambda: _service_respond(dialog_id, response_id)),
            ('ui_dialog_respond',
             lambda: _call('ui_dialog_respond', (dialog_id, response_id))),
            ('dialog.respond', lambda: dialog.respond(response_id)),
        ]
        if _run_routes(dialog_id, routes, dialog):
            return True
        return dismiss(dialog)

    return dismiss(dialog)


def last_route():
    return _last_route


def last_error():
    return _last_error


def inspect(dialog):
    """Diagnostic dump so we can learn the real shape of a live dialog."""
    if dialog is None:
        return ['no active dialog']
    lines = ['class: {}'.format(type(dialog).__name__),
             'title: {}'.format(title_of(dialog)),
             'dialog_id: {!r}  client_id: {!r}'.format(
                 getattr(dialog, 'dialog_id', None), _client_id())]
    rows = rows_of(dialog)
    lines.append('picker_rows: {}'.format(len(rows)))
    if rows:
        row = rows[0]
        lines.append('row class: {}'.format(type(row).__name__))
        attrs = [a for a in dir(row) if not a.startswith('__')][:24]
        lines.append('row attrs: {}'.format(', '.join(attrs)))
        lines.append('row option_id: {!r}'.format(getattr(row, 'option_id', None)))
        lines.append('row name -> {!r}'.format(loc_text(getattr(row, 'name', None))))
    methods = [a for a in dir(dialog)
               if not a.startswith('__') and callable(getattr(dialog, a, None))]
    lines.append('methods: {}'.format(', '.join(methods[:26])))
    options(dialog)  # refresh the label diagnostics
    if _label_debug:
        lines.append('label resolution failures:')
        for entry in _label_debug[:8]:
            lines.append('  ' + entry)
    return lines


_HOOK_TARGETS = (
    ('ui.ui_dialog', 'UiDialogBase', ('show_dialog', 'distribute_dialog')),
    ('ui.ui_dialog', 'UiDialog', ('show_dialog',)),
    ('ui.ui_dialog_notification', 'UiDialogNotification',
     ('show_dialog', 'distribute_dialog')),
    ('ui.ui_dialog_picker', 'UiDialogObjectPicker', ('show_dialog',)),
    ('ui.ui_dialog_picker', 'UiMapViewPicker', ('show_dialog',)),
    ('ui.ui_dialog_picker', 'UiSimPicker', ('show_dialog',)),
)

_hooked = []
_recent_ids = []
_snapshots = []


def _describe_attr(dialog, attr):
    try:
        value = getattr(dialog, attr, None)
    except Exception as ex:
        return '{}=<raises {!r}>'.format(attr, ex)
    if value is None:
        return None
    try:
        return '{}: type={} callable={} hash={!r} repr={}'.format(
            attr, type(value).__name__, callable(value),
            getattr(value, 'hash', None), repr(value)[:70])
    except Exception:
        return '{}: <unprintable>'.format(attr)


def _snapshot(dialog):
    """Record structure now; the dialog may be gone by the time we are asked."""
    try:
        lines = ['class: {}'.format(type(dialog).__name__),
                 'dialog_id: {!r}'.format(getattr(dialog, 'dialog_id', None))]
        for attr in ('text', 'title', 'description', 'message', 'subtitle'):
            entry = _describe_attr(dialog, attr)
            if entry:
                lines.append(entry)
        for attr in ('text', 'title'):
            for entry in probe_callable(dialog, attr):
                lines.append(entry)
        try:
            lines.append('additional_texts: {}'.format(
                repr(getattr(dialog, 'additional_texts', None))[:120]))
        except Exception:
            pass
        try:
            for entry in describe_tokens(dialog):
                lines.append(entry)
        except Exception as ex:
            lines.append('token probe raised {!r}'.format(ex))
        # Does the dialog carry its tokens separately from the text factory?
        for attr in ('text_tokens', 'tokens', 'additional_tokens'):
            try:
                held = getattr(dialog, attr, None)
                if held:
                    lines.append('{}: {!r}'.format(attr, repr(held)[:160]))
            except Exception:
                continue
        try:
            lines.append('build_msg -> {!r}'.format(_from_built_msg(dialog)))
        except Exception as ex:
            lines.append('build_msg raised {!r}'.format(ex))
        try:
            lines.append('title_of -> {!r}'.format(title_of(dialog)))
            lines.append('body_of  -> {!r}'.format(body_of(dialog)))
            lines.append('options  -> {}'.format(len(options(dialog))))
        except Exception as ex:
            lines.append('extraction raised {!r}'.format(ex))
        try:
            attrs = [a for a in dir(dialog) if not a.startswith('_')]
            lines.append('attrs: {}'.format(', '.join(attrs[:28])))
        except Exception:
            pass
        _snapshots.append(lines)
        del _snapshots[:-5]
    except Exception:
        pass


def last_snapshot():
    return _snapshots[-1] if _snapshots else ['no dialog captured yet']


def snapshot_count():
    return len(_snapshots)


def _seen_recently(dialog):
    """Subclass and base can both fire for one dialog; announce it once."""
    key = id(dialog)
    if key in _recent_ids:
        return True
    _recent_ids.append(key)
    del _recent_ids[:-16]
    return False


_sweep_callback = None
_wrapped = set()


def _dialog_subclasses():
    """Every dialog class the game currently has, however deeply nested.

    A fixed list of classes was always going to miss things: the career picker
    is one, and a mod's own dialog class is another. Walking UiDialogBase's
    subclass tree finds them all - including classes that only come into
    existence when their module is first imported, which is why this is
    re-run rather than done once at startup.
    """
    found = []
    try:
        from ui.ui_dialog import UiDialogBase
    except Exception:
        return found
    stack = [UiDialogBase]
    while stack:
        cls = stack.pop()
        try:
            subclasses = cls.__subclasses__()
        except Exception:
            continue
        for sub_cls in subclasses:
            if sub_cls not in found:
                found.append(sub_cls)
                stack.append(sub_cls)
    return found


# Whether to keep map screens off the client entirely. On, because a map that
# has been drawn cannot be put away again - responses, the client's own close
# message and a synthesized Escape were all tried and all ignored.
_suppress_maps = True


def set_map_suppression(value):
    global _suppress_maps
    _suppress_maps = bool(value)
    return _suppress_maps


def harvest_map_destinations(dialog):
    """Record where the game says this Sim can go.

    LotPickerRow is built from zone data and keeps the useful parts as its own
    fields - zone_id, name, world_id, venue_type_name, household_name - so a
    destination can be read off a row with nothing to guess. option_id is the
    fallback, since the picker does put the zone id there too (that is what
    reaches picked_zone_ids when you confirm).
    """
    if not is_map_view(dialog):
        return 0
    pairs = []
    try:
        for index, row in enumerate(rows_of(dialog)):
            zone_id = getattr(row, 'zone_id', None) or getattr(
                row, 'option_id', None)
            if not zone_id:
                continue
            name = loc_text(getattr(row, 'name', None)) or _row_label(row, index)
            venue = loc_text(getattr(row, 'venue_type_name', None))
            if venue and name:
                name = '{}, {}'.format(name, venue)
            pairs.append((zone_id, name))
    except Exception as ex:
        logfile.write('dialog: could not read the map rows ({!r})'.format(ex))
        return 0
    if not pairs:
        return 0
    try:
        import a11yscan_travel as travel
        return travel.remember_destinations(pairs, type(dialog).__name__)
    except Exception as ex:
        logfile.write('dialog: could not record destinations ({!r})'.format(ex))
        return 0


def _suppress_map_view(dialog):
    """Should this dialog be answered without ever being drawn?

    Every map picker - travel, ask on date, invite to, a mod's own - ends up
    at the same place: the server keeps the dialog, the client draws a screen,
    and answering the dialog does not take that screen away. The mod can read
    the destinations and answer perfectly well without it, so the screen is
    simply never sent.

    The safety valve is reading the rows first. If the destinations cannot be
    listed, the player would be left with no way to choose at all, and a map
    that will not close is still better than that - so it is drawn as usual.
    """
    if not _suppress_maps or not is_map_view(dialog):
        return False
    try:
        rows = rows_of(dialog)
    except Exception as ex:
        logfile.write('dialog: map rows unreadable, letting the screen '
                      'open ({!r})'.format(ex))
        return False
    if not rows:
        logfile.write('dialog: map picker has no rows we can read, letting '
                      'the screen open')
        return False
    logfile.ok('dialog: keeping {} off the screen, {} destinations read '
               'instead'.format(type(dialog).__name__, len(rows)))
    return True


def _make_wrapper(original_fn, on_shown, method_name=''):
    def wrapper(self, *args, **kwargs):
        # Some tokens are handed to show_dialog by the caller
        # and never stored anywhere - a bill's amount arrives
        # as additional_tokens=(money,). The dialog itself then
        # cannot produce it, which is why even the game's own
        # build_msg rendered "That'll be ." Grab them in flight.
        try:
            extra = kwargs.get('additional_tokens')
            if extra:
                self._a11y_extra_tokens = tuple(extra)
        except Exception:
            pass
        # distribute_dialog is the call that hands the panel to the client.
        # Skipping it for a map picker leaves the dialog alive server-side -
        # registration happens in show_dialog, not here - so it can still be
        # read and answered, and no screen ever appears to get stuck.
        result = None
        if method_name == 'distribute_dialog' and _suppress_map_view(self):
            pass
        else:
            result = original_fn(self, *args, **kwargs)
        try:
            _active.append(self)
            _prune()
            if on_shown is not None and not _seen_recently(self):
                _snapshot(self)
                resolved = title_of(self, fallback=False)
                body = None
                try:
                    body = body_of(self)
                except Exception:
                    pass
                # Whether a sound was even tuned for this one, so a
                # missing notification sting can be told from a silent one.
                sting = 'none'
                try:
                    if getattr(self, 'audio_sting', None) is not None:
                        sting = 'tuned, owner {}'.format(
                            getattr(self, 'audio_sting_owner', None))
                except Exception:
                    sting = 'unreadable'
                logfile.write(
                    'dialog shown: {} title={!r} body={!r} sting={}'.format(
                        type(self).__name__, resolved, body, sting))
                try:
                    harvest_map_destinations(self)
                except Exception as ex:
                    logfile.write('dialog: destination harvest failed '
                                  '({!r})'.format(ex))
                try:
                    for entry in describe_tokens(self):
                        logfile.write('  ' + entry)
                except Exception:
                    pass
                # A template with {placeholders} and no
                # tokens means the text was stripped rather
                # than filled - the failure that loses Sim
                # names and money amounts. Dump the dialog's
                # shape only in that case, so the log stays
                # readable for the notifications that work.
                unfilled = False
                try:
                    template = template_of(self)
                    unfilled = bool(
                        template and '{' in template
                        and not dialog_tokens(self))
                    if unfilled:
                        logfile.fail(
                            'dialog UNFILLED: template {!r} '
                            'has placeholders but the dialog '
                            'yielded no tokens'.format(template))
                except Exception as ex:
                    logfile.write(
                        'dialog: unfilled check failed ({!r})'.format(ex))
                if unfilled or (not resolved and not body):
                    for entry in last_snapshot():
                        logfile.write('  unread: {}'.format(entry))
                on_shown(self)
        except Exception as ex:
            speech.log('dialog hook failed ({!r})'.format(ex))
        return result
    wrapper._a11yscan_wrapper = True
    return wrapper


def install(on_shown=None):
    """Wrap show_dialog on every dialog class that defines its own.

    Patching only UiDialogBase misses notifications entirely: they override
    both show_dialog and distribute_dialog and never chain up to the base.
    """
    global _installed
    if _installed:
        return True
    import importlib
    for module_name, class_name, methods in _HOOK_TARGETS:
        try:
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name, None)
            if cls is None:
                continue
            for method in methods:
                # Put back any wrapper from a previous load first, or each
                # reload would wrap the wrapper and double every announcement.
                saved_attr = '_a11yscan_orig_' + method
                previous = getattr(cls, saved_attr, None)
                if previous is not None:
                    try:
                        setattr(cls, method, previous)
                    except Exception:
                        pass
                original = cls.__dict__.get(method)
                if original is None:
                    continue  # inherited; the parent's patch covers it
                try:
                    setattr(cls, saved_attr, original)
                except Exception:
                    pass

                pass
                setattr(cls, method, _make_wrapper(original, on_shown,
                                                   method))
                _hooked.append('{}.{}'.format(class_name, method))
        except Exception as ex:
            speech.log('hook {} failed ({!r})'.format(class_name, ex))
    _installed = bool(_hooked)
    # The fixed list above covers the common classes; this catches everything
    # else, including a mod's own dialog class and anything whose module is
    # imported later.
    try:
        refresh_hooks(on_shown)
    except Exception as ex:
        speech.log('subclass hook sweep failed ({!r})'.format(ex))
    speech.log('dialog hooks: {}'.format(', '.join(_hooked) or 'NONE'))
    return _installed


def refresh_hooks(on_shown=None):
    """Wrap any dialog class that has appeared since the last pass.

    Only walks the class tree and skips what is already wrapped, so it is cheap
    enough to re-run. Classes appear as their modules are imported - a screen
    used for the first time late in a session would otherwise never be hooked,
    which is exactly what happened with the career picker.
    """
    global _sweep_callback
    if on_shown is not None:
        _sweep_callback = on_shown
    callback = _sweep_callback
    if callback is None:
        return 0
    added = []
    for cls in _dialog_subclasses():
        for method in ('show_dialog', 'distribute_dialog'):
            if method not in cls.__dict__:
                continue          # inherited: an ancestor is already wrapped
            key = (cls.__module__, cls.__name__, method)
            if key in _wrapped:
                continue
            original = cls.__dict__[method]
            if getattr(original, '_a11yscan_wrapper', False):
                _wrapped.add(key)
                continue
            try:
                setattr(cls, '_a11yscan_orig_' + method, original)
                setattr(cls, method, _make_wrapper(original, callback,
                                                   method))
                _wrapped.add(key)
                added.append('{}.{}'.format(cls.__name__, method))
            except Exception:
                continue
    if added:
        logfile.write('dialogs: hooked {} more ({})'.format(
            len(added), ', '.join(added[:10])))
    return len(added)


def hooked():
    return list(_hooked)


def uninstall():
    """Put the game's own methods back, so a reload starts from clean."""
    global _installed
    import importlib
    for module_name, class_name, methods in _HOOK_TARGETS:
        try:
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name, None)
            if cls is None:
                continue
            for method in methods:
                saved_attr = '_a11yscan_orig_' + method
                original = getattr(cls, saved_attr, None)
                if original is not None:
                    setattr(cls, method, original)
        except Exception as ex:
            speech.log('unhook {} failed ({!r})'.format(class_name, ex))
    del _hooked[:]
    _installed = False


def installed():
    return _installed
