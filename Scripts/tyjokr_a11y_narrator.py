"""TS4 Access: console commands that receive UI text from the patched
Flash layer and speak it through a screen reader / TTS.

The patched TooltipManager (UI override package) posts:
    a11y.speak_enc <percent-encoded-utf8>
where the payload is a \\x01-separated list of "y|x|text" entries, one per
visible TextField in the tooltip. This module sorts them into visual reading
order, glues labels to values, curates known tooltip shapes, and speaks.

    a11y.mark <library-name>     (once; identifies which movie's patched
                                  TooltipManager copy won the app domain)
Manual / scripted narration can use:
    a11y.speak <free text>
Diagnostics:
    a11y.test     speak a test sentence and report the backend
    a11y.status   report backend, DLL presence and log path
"""
import re
import threading
import time

import sims4.commands

import tyjokr_a11y_lang as lang
import tyjokr_a11y_settings as settings
import tyjokr_a11y_speech as speech

FIELD_SEP = '\x01'

_EFFECT_RE = re.compile(r'^[A-Za-z][A-Za-z ]* \+\d+$')
_DURATION_RE = re.compile(r'^\d+ (?:minute|hour|day)s?$')
_FIELD_RE = re.compile(r'^(-?\d+)\|(-?\d+)\|(.*)$', re.S)
_ROW_TOLERANCE = 8


def _decode_percent(token):
    """Decode Flash payloads. Scaleform's encodeURIComponent is broken for
    U+0080..U+00FF: those arrive as bare Latin-1 bytes while higher
    codepoints arrive as proper UTF-8, so a strict UTF-8 unquote turns every
    accented letter (and the simoleon sign) into U+FFFD. Decode byte-wise:
    UTF-8 where it validates, Latin-1 for stray single bytes."""
    try:
        from urllib.parse import unquote_to_bytes
        raw = unquote_to_bytes(token)
        out = []
        i = 0
        n = len(raw)
        while i < n:
            if raw[i] < 0x80:
                out.append(chr(raw[i]))
                i += 1
                continue
            for width in (2, 3, 4):
                try:
                    out.append(raw[i:i + width].decode('utf-8'))
                    i += width
                    break
                except Exception:
                    continue
            else:
                out.append(raw[i:i + 1].decode('latin-1'))
                i += 1
        return ''.join(out)
    except Exception:
        return token


def _direction(match):
    args = [arg.strip() or lang.t('transfer other household')
            for arg in match.group(2).split('\x02')[1:]]
    template = lang.t('transfer ' + match.group(1))
    try:
        return template.format(*args)
    except (IndexError, KeyError, ValueError):
        return ' '.join(args)


def _clean_glyphs(text):
    """Replace/strip game icon glyphs that TTS reads badly (localized).
    EA repurposes ordinary symbol chars via the game font: paragraph sign =
    simoleons, U+2260 = galactic credits, lozenge = satisfaction, and so on
    (found by censusing the STBLs; see HANDOFF)."""
    # EA name/description strings carry text markup (<i>, <b>) that only
    # renders inside TextFields; Flash-side COMPOSED payloads (catalog
    # cells read mData.Name raw) pass it through, so spoken text must
    # drop the tags (heard live: "The Indoor <i>and</i> Outdoor Plastic
    # Chair", household inventory 2026-08-20).
    text = re.sub(r'</?[a-zA-Z][^>]*>', ' ', text)
    # Stack-count marker from the catalog cell composer (Flash appends
    # "\x02qty\x02<n>"; keeping it a control-char marker instead of an
    # English word keeps the 17-language table in charge of the wording).
    text = re.sub('\x02qty\x02(\\d+)',
                  lambda m: lang.t('quantity') + ' ' + m.group(1), text)
    # Transfer direction marker from the household and retail transfer
    # panels: "\x02dir\x02<kind>" then "\x02"-separated names and amounts,
    # worded here so the language table owns it. Runs before the currency
    # rule so a household's paragraph-sign amount still becomes simoleons.
    text = re.sub('\x02dir\x02(\\w+)((?:\x02[^\x01\x02]*)*)', _direction, text)
    # Business summaries and panels sign amounts as "+  \u00a7500" and
    # "-  \u00a7500" and colour them; a lone dash is often skipped by
    # screen readers, so say plus and minus (2026-10-04).
    text = re.sub('(?<![\\w\u00a7])([+-])\\s*(?=\u00a7)',
                  lambda m: lang.t('plus' if m.group(1) == '+' else 'minus') + ' ', text)
    # Currency amounts: the capture must END on a digit. The old
    # [\d][\d.,]* also swallowed a trailing sentence period, so
    # "§645. Romantic" became "645. simoleons Romantic" with the unit
    # glued to the next clause (household inventory bug, 2026-08-20).
    # Interior separators ("13,709") still match.
    text = re.sub(r'[§�]\s*(\d(?:[\d.,]*\d)?)',
                  lambda m: m.group(1) + ' ' + lang.t('simoleons'), text)
    text = re.sub(u'≠\\s*(\\d(?:[\\d.,]*\\d)?)',
                  lambda m: m.group(1) + ' ' + lang.t('galactic credits'), text)
    # Eco Lifestyle recycling currencies (glyphs captured in-game 2026-08-01:
    # wallet order is credits, bits, pieces)
    text = re.sub(u'⬡\\s*(\\d(?:[\\d.,]*\\d)?)',
                  lambda m: m.group(1) + ' ' + lang.t('bits'), text)
    text = re.sub(u'⬢\\s*(\\d(?:[\\d.,]*\\d)?)',
                  lambda m: m.group(1) + ' ' + lang.t('pieces'), text)
    text = text.replace('�', ' ')
    text = re.sub(r'◊\s*(\d+)',
                  lambda m: '. ' + m.group(1) + ' ' + lang.t('satisfaction points') + '. ', text)
    text = text.replace('◴', ' ' + lang.t('likes') + ': ')
    text = text.replace('◵', ' ' + lang.t('dislikes') + ': ')
    # private-use-area icon glyphs
    text = re.sub(u'[\ue000-\uf8ff]', ' ', text)
    text = re.sub(r'\s*[\r\n]+\s*', '. ', text)
    return re.sub(r'  +', ' ', text).strip()


def _norm(text):
    return re.sub(r'[^a-z0-9]', '', text.lower())


# EA measures text boxes with hidden ruler strings: digit runs
# ("1234567890...") and repeated wide characters ("wwwwwwww...").
_PLACEHOLDER = re.compile(r'^(?:1234567890)+\d*$')
# Authoring text left in unused TextFields: the field's own instance name
# ("txtSimName. txtPay. txtSatisfaction" in empty business employee slots,
# 2026-10-04). Game text never looks like a lowerCamel field identifier.
_FIELD_NAME = re.compile(r'^(?:txt|mc|btn|dd|cb|sl|lb|tf)[A-Z][A-Za-z0-9]*$')
_REPEATED_CHAR = re.compile(r'^(.)\1{4,}$')


def _is_placeholder(text):
    stripped = re.sub(r'\s+', '', text)
    if not stripped:
        return True
    if _PLACEHOLDER.match(stripped) or _FIELD_NAME.match(stripped):
        return True
    if not re.search(r'[^\W_]', stripped, re.UNICODE):
        # Nothing but punctuation or symbols ("%", "% % %", "..."): empty
        # stat rows the game leaves in place with no value in them.
        return True
    return bool(_REPEATED_CHAR.match(stripped))


def _fields_to_segments(decoded):
    """Parse y|x|text fields, sort into visual rows, glue labels to values."""
    fields = []
    for part in decoded.split(FIELD_SEP):
        match = _FIELD_RE.match(part)
        if match:
            text = _clean_glyphs(match.group(3))
            if text and not _is_placeholder(text):
                fields.append((int(match.group(1)), int(match.group(2)), text))
        else:
            text = _clean_glyphs(part)
            if text and not _is_placeholder(text):
                fields.append((0, 0, text))
    fields.sort(key=lambda f: (f[0], f[1]))

    rows = []
    for y, x, text in fields:
        if rows and abs(rows[-1][0] - y) <= _ROW_TOLERANCE:
            rows[-1][1].append((x, text))
        else:
            rows.append((y, [(x, text)]))

    segments = []
    for _y, cells in rows:
        # Sort by X ONLY. Sorting the whole (x, text) tuple made equal-X
        # cells fall back to comparing TEXT, which alphabetized them: a
        # composed payload whose segments carry no coordinates (they all
        # default to 0) came out in dictionary order, so the purchase
        # picker's "Increase / <item> / <count>" read as "<item> /
        # Increase / <count>". Python's sort is stable, so sorting on X
        # alone preserves the order Flash posted them in.
        cells.sort(key=lambda cell: cell[0])
        texts = [t for _x, t in cells]
        if len(texts) > 1 and texts[0].endswith(':'):
            segments.append(' '.join(texts))
        else:
            segments.extend(texts)

    # label-above-value: a bare "Label:" segment absorbs the next segment
    glued = []
    i = 0
    while i < len(segments):
        if (segments[i].endswith(':') and i + 1 < len(segments)
                and not segments[i + 1].endswith(':')):
            glued.append(segments[i] + ' ' + segments[i + 1])
            i += 2
        else:
            glued.append(segments[i])
            i += 1

    # drop bare header segments that duplicate a glued label
    # (e.g. "Eco Footprint" next to "Eco-Footprint: Neutral")
    label_norms = set()
    for seg in glued:
        if ':' in seg:
            label_norms.add(_norm(seg.split(':', 1)[0]))
    return [seg for seg in glued
            if not (':' not in seg and _norm(seg) in label_norms)]


def _order_segments(segments):
    """Semantic ordering: moodlets read title/effect/source/duration/description;
    anything else with a (From ...) source reads it last."""
    effects = [s for s in segments if _EFFECT_RE.match(s) or s.startswith('Boosting: ')]
    sources = [s for s in segments if s.startswith('(From') or s.startswith('(You cheated')]
    durations = [s for s in segments if _DURATION_RE.match(s)]
    if effects and sources:
        special = set(effects) | set(sources) | set(durations)
        rest = [s for s in segments if s not in special]
        return rest[:1] + effects + durations + sources + rest[1:]
    if sources:
        rest = [s for s in segments if s not in set(sources)]
        return rest + sources
    return segments


_rawdiag = False


@sims4.commands.Command('a11y.rawdiag', command_type=sims4.commands.CommandType.Live)
def a11y_rawdiag(mode: str = 'on', _connection=None):
    """Hidden support diagnostic: log pre-clean payloads with unicode
    escapes (for identifying unknown glyph characters). Session-only;
    needs a11y.log on to actually write anywhere."""
    global _rawdiag
    _rawdiag = mode.lower() not in ('off', 'false', '0')
    sims4.commands.CheatOutput(_connection)(
        'a11y: raw payload logging {}'.format('ON' if _rawdiag else 'OFF'))
    return True


def _process(decoded, channel='?'):
    if _rawdiag:
        speech.log_line('RAWDIAG[{}]: {}'.format(channel, ascii(decoded)))
    if FIELD_SEP not in decoded and '|' not in decoded[:12]:
        return _clean_glyphs(decoded)
    segments = _fields_to_segments(decoded)
    segments = _order_segments(segments)
    seen = set()
    ordered = []
    for seg in segments:
        if seg not in seen:
            seen.add(seg)
            # Flash posts bare lowercase tokens for the mod's OWN vocabulary
            # (game text arrives already localized); translate them here.
            if seg in ('checked', 'unchecked', 'increase', 'decrease', 'phone', 'action unavailable'):
                seg = lang.t(seg)
            else:
                seg = _own_phrase(seg)
            ordered.append(seg)
    return '. '.join(ordered)


# English lines Flash composes itself (the simplified menus position and
# selection count, the first-person camera state); game text arrives already
# localized, and none of it reads exactly like these.
_POSITION_RE = re.compile(r'^(\d+) of (\d+)$')
_SELECTED_RE = re.compile(r'^(\d+) selected$')
_OWN_PHRASES = {'First-person camera on.': 'first person camera on',
                'First-person camera off.': 'first person camera off'}


def _own_phrase(seg):
    term = _OWN_PHRASES.get(seg)
    if term is not None:
        return lang.t(term)
    match = _POSITION_RE.match(seg)
    if match:
        return lang.t('option position').format(match.group(1), match.group(2))
    match = _SELECTED_RE.match(seg)
    if match:
        return lang.t('selected count').format(match.group(1))
    return seg


# Two-stage reading for DATA ROWS. A row that announces its own name and
# value (needs bars, skill rows, mood, the time panel) has already said the
# useful part; its tooltip is a long stock description. So the row line
# speaks at once and the description that follows within the window is held
# back by `tooltip delay` seconds, cancelled the moment the pointer moves on
# (tester request 2026-08-03: "mostly useless info"). The read key still
# reads row and description together.
#
# The trigger is deliberately "a tooltip following a real row announcement",
# NOT tooltip length: buttons and icons announce through the widgetNAME
# channel instead, so their tooltips (which carry the only text they have)
# stay immediate. A global length threshold was tried 2026-08-01 and
# rejected by the tester.
_ROW_TIP_WINDOW = 4.0
_row_head = None
_row_head_when = 0.0


def _arm_row_head(text):
    """Remember a row line so the description behind it can be deferred."""
    global _row_head, _row_head_when
    _row_head = text or None
    _row_head_when = time.monotonic()


def _take_row_head():
    """The pending row line, if it is recent enough to still belong to the
    tooltip now arriving."""
    global _row_head
    head = _row_head
    _row_head = None
    if head is None or time.monotonic() - _row_head_when >= _ROW_TIP_WINDOW:
        return None
    return head


def _tooltip_delay():
    try:
        return max(0.0, float(settings.get('tooltip_delay')))
    except (TypeError, ValueError):
        return 0.0


@sims4.commands.Command('a11y.timewidget_enc', command_type=sims4.commands.CommandType.Live)
def a11y_timewidget_enc(text: str = '', _connection=None):
    decoded = _decode_percent(text)
    if _rawdiag:
        speech.log_line('RAWDIAG[timewidget]: ' + ascii(decoded))
    final = _clean_glyphs(decoded)
    if not final:
        return True
    _arm_row_head(final)
    speech.speak(final, source='widget')
    return True


@sims4.commands.Command('a11y.clock_enc', command_type=sims4.commands.CommandType.Live)
def a11y_clock_enc(text: str = '', _connection=None):
    """The client's answer to A11yClock (Control Alt C, the menu row): its
    clock widget's own localized day and time, with Paused when paused,
    as 'clock:<text>'. Empty text means the widget is not live; say so in
    words rather than invent a day number. Separate from the pointer path
    (a11y.timewidget_enc) so a hover can never pass for the reply."""
    decoded = _decode_percent(text)
    if decoded.startswith('clock:'):
        decoded = decoded[len('clock:'):]
    final = _clean_glyphs(decoded).strip() if decoded.strip() else ''
    money = _clock_funds()
    if not final:
        speech.speak(lang.t('clock unavailable') + (' ' + money if money else ''), explicit=True)
        return True
    speech.speak(final + ('. ' + money if money else ''), source='widget', explicit=True)
    return True


def _clock_funds():
    """The clock reply also reads household funds (requested 2026-09-28). Empty
    before a household loads, e.g. at the main menu, so the clock still
    answers there on its own."""
    try:
        import tyjokr_a11y_hub as hub
        return hub.funds_text()
    except Exception as ex:
        speech.log_line('clock: funds unavailable ({!r})'.format(ex))
        return ''


# Control Alt E and the accessibility menu row read the mood panel in one
# pass. SimHub's MoodContainer posts one record per a11y.mood_enc so no
# single command carries every moodlet: M opens a reading (sequence, count,
# current mood key, mood name, mood description), B carries a moodlet
# (sequence, index, mood key, boost flag, weight, name, effect, boost,
# reason, time left, description; the description is last because Flash
# caps each record's length), and E ends it. All text is the client's own
# localized text. An empty payload means the panel is not live.
_MOOD_LIMIT = 40
_mood_reading = None


def _mood_text(value):
    return _clean_glyphs(value).strip() if value and value.strip() else ''


def _mood_weight(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _mood_order(current, rows):
    """BuffDisplay.BuffSort: the current mood's moodlets first, ordinary
    before boosts, then by weight and name; other moods follow grouped by
    their summed weight, then by mood key descending, the same way inside."""
    totals = {}
    for row in rows:
        totals[row['mood']] = totals.get(row['mood'], 0) + row['weight']
    rows = sorted(rows, key=lambda row: (row['boost'], -row['weight'], row['name'].lower()))
    rows.sort(key=lambda row: row['mood'], reverse=True)
    rows.sort(key=lambda row: (0, 0) if row['mood'] == current else (1, -totals[row['mood']]))
    return rows


def _mood_speech(reading):
    parts = [reading['name'], reading['description']]
    rows = _mood_order(reading['mood'], reading['rows'])
    if not rows:
        parts.append(lang.t('no moodlets'))
    for row in rows:
        # Title, effect, duration, source, description: the order moodlet
        # tooltips already read in (_order_segments).
        parts.extend((row['name'], row['effect'], row['bonus'], row['time'],
                      row['reason'], row['description']))
    return '. '.join(part.rstrip('.') for part in parts if part)


@sims4.commands.Command('a11y.mood_enc', command_type=sims4.commands.CommandType.Live)
def a11y_mood_enc(text: str = '', _connection=None):
    global _mood_reading
    fields = _decode_percent(text).split(FIELD_SEP) if text else []
    kind = fields[0] if fields else ''
    if kind == 'M' and len(fields) >= 6:
        _mood_reading = {'seq': fields[1], 'mood': fields[3], 'name': _mood_text(fields[4]),
                         'description': _mood_text(fields[5]), 'rows': []}
        return True
    reading = _mood_reading
    if kind == 'B' and len(fields) >= 11:
        if reading is None or fields[1] != reading['seq'] or len(reading['rows']) >= _MOOD_LIMIT:
            return True
        name = _mood_text(fields[6])
        if name:
            reading['rows'].append({
                'mood': fields[3], 'boost': fields[4] == '1', 'weight': _mood_weight(fields[5]),
                'name': name, 'effect': _mood_text(fields[7]), 'bonus': _mood_text(fields[8]),
                'reason': _mood_text(fields[9]), 'time': _mood_text(fields[10]),
                'description': _mood_text(fields[11]) if len(fields) > 11 else ''})
        return True
    if kind == 'E' and len(fields) >= 2:
        if reading is None or fields[1] != reading['seq']:
            return True
        _mood_reading = None
        final = _mood_speech(reading)
        speech.speak(final or lang.t('mood unavailable'), source='widget', explicit=True)
        return True
    if not text:
        _mood_reading = None
        speech.speak(lang.t('mood unavailable'), explicit=True)
        return True
    speech.log_line('mood: ignored a malformed record')
    return True


@sims4.commands.Command('a11y.speak_enc', command_type=sims4.commands.CommandType.Live)
def a11y_speak_enc(text: str = '', _connection=None):
    # A real tooltip beats any placeholder name we derived from the control.
    _cancel_pending_name()
    decoded = _decode_percent(text)
    try:
        final = _process(decoded, 'tooltip')
    except Exception as ex:
        speech.log_line('process failed ({!r}); speaking raw'.format(ex))
        final = _clean_glyphs(decoded.replace(FIELD_SEP, '. '))
    head = _take_row_head()
    delay = _tooltip_delay()
    if head is not None and delay > 0:
        # The row already said name and value; hold its description back.
        speech.speak_progressive(head, final, source='tooltip',
                                 delay=delay, head_spoken=True)
        return True
    speech.speak(final, source='tooltip')
    return True


@sims4.commands.Command('a11y.widget_enc', command_type=sims4.commands.CommandType.Live)
def a11y_widget_enc(text: str = '', _connection=None):
    # A real widget line beats any derived-name placeholder still waiting
    # (e.g. the purchase picker's +/- buttons: the generic path posts their
    # bare instance name, then our cell patch posts the full
    # "Increase. <item>. <count>" line; without this, the parked name
    # flushed 0.4 s later and talked over the real announcement).
    _cancel_pending_name()
    decoded = _decode_percent(text)
    try:
        final = _process(decoded, 'widget')
    except Exception as ex:
        speech.log_line('process failed ({!r}); speaking raw'.format(ex))
        final = _clean_glyphs(decoded.replace(FIELD_SEP, '. '))
    # This row spoke for itself, so a description arriving behind it can be
    # deferred; it also supersedes any older row still waiting.
    _arm_row_head(final)
    speech.speak(final, source='widget')
    return True


@sims4.commands.Command('a11y.focus_enc', command_type=sims4.commands.CommandType.Live)
def a11y_focus_enc(text: str = '', _connection=None):
    """The settled keyboard target supersedes an older pending row."""
    _cancel_pending_name()
    decoded = _decode_percent(text)
    try:
        final = _process(decoded, 'widget')
    except Exception:
        final = _clean_glyphs(decoded.replace(FIELD_SEP, '. '))
    _arm_row_head(final)
    speech.speak(final, source='widget', explicit=speech.speech_mode == 'hover')
    return True


@sims4.commands.Command('a11y.context_enc', command_type=sims4.commands.CommandType.Live)
def a11y_context_enc(text: str = '', _connection=None):
    """Log owner transitions without speaking; distinguish loaded from open.
    The ':DD' suffix is the same owner state a11y.modalstate carries; it is
    applied too, so one lost post cannot strand keyboard routing. A third
    digit is the owner's blocking bit (phone guard), applied with the
    owner as one report; the direct a11y.modalstate stays two digits."""
    decoded = _decode_percent(text)
    speech.log_line('UI owner: ' + decoded[:300])
    suffix = decoded.rsplit(':', 1)[-1] if ':' in decoded else ''
    if suffix[:2] in ('00', '01', '10', '11') and suffix[2:] in ('', '0', '1'):
        try:
            import tyjokr_a11y_keys as keys
            keys.apply_modal_state(suffix, 'context')
        except Exception as ex:
            speech.log_line('context: modal state not applied: {!r}'.format(ex))
    return True


_inspect_timer = None


@sims4.commands.Command('a11y.inspect_inventory', command_type=sims4.commands.CommandType.Live)
def a11y_inspect_inventory(_connection=None):
    """Log read-only item identities/tooltip flags; never request an action."""
    import services
    from itertools import islice
    output = sims4.commands.CheatOutput(_connection)
    sim = services.get_active_sim()
    inventory = getattr(sim, 'inventory_component', None)
    if inventory is None:
        output('No active Sim inventory.')
        return False
    count = 0
    # Inventory iteration also includes hidden storage. Log the visibility
    # flag, and bound this diagnostic independently of stack sizes.
    for obj in islice(iter(inventory), 100):
        count += 1
        try:
            definition = getattr(obj, 'definition', None)
            speech.log_line('Inventory inspect: id={} definition={} class={} catalog={} hover={} hidden={}'.format(
                obj.id, getattr(definition, 'id', None), type(obj).__name__,
                getattr(obj, 'catalog_name', None), getattr(obj, 'hover_tip', None),
                obj.is_hidden()))
        except Exception as ex:
            speech.log_line('Inventory inspect: item unavailable {!r}'.format(ex))
    output('Inventory snapshot: {} entries (limit 100); see TS4 Access log.'.format(count))
    return True


@sims4.commands.Command('a11y.inspect_ui', command_type=sims4.commands.CommandType.Live)
def a11y_inspect_ui(delay: float = 0, _connection=None):
    """Read-only snapshot, optionally delayed to inspect a console-blocking modal."""
    global _inspect_timer
    import tyjokr_a11y_keys as keys
    import threading
    if _inspect_timer is not None:
        _inspect_timer.cancel()
        _inspect_timer = None
    delay = max(0.0, min(60.0, delay))
    if delay:
        # _send only queues work; the timer never calls game APIs directly.
        _inspect_timer = threading.Timer(delay, keys._send, args=('A11yInspect',))
        _inspect_timer.daemon = True
        _inspect_timer.start()
    else:
        keys._send('A11yInspect')
    sims4.commands.CheatOutput(_connection)('Keyboard focus snapshot in {:.0f} seconds; see TS4 Access log.'.format(delay))
    return True


@sims4.commands.Command('a11y.inspect_enc', command_type=sims4.commands.CommandType.Live)
def a11y_inspect_enc(text: str = '', _connection=None):
    for line in _decode_percent(text)[:16000].splitlines():
        speech.log_line('UI inspect: ' + line)
    return True


@sims4.commands.Command('a11y.scope_enc', command_type=sims4.commands.CommandType.Live)
def a11y_scope_enc(text: str = '', _connection=None):
    """Opening description and first control form one uninterrupted utterance."""
    _cancel_pending_name()
    parts = _decode_percent(text).split('\x02', 2)
    if len(parts) != 3:
        return False
    kind, intro, focus = parts
    intro = _process(intro, 'dialog') if intro else ''
    focus = _process(focus, 'widget') if focus else ''
    if kind == 'dialog' and not settings.brief():
        intro = '{}. {}'.format(lang.t('dialog'), intro)
    line = '. '.join(part for part in (intro, focus) if part)
    _arm_row_head(line)
    speech.speak(line, source='widget')
    return True


@sims4.commands.Command('a11y.dialog_enc', command_type=sims4.commands.CommandType.Live)
def a11y_dialog_enc(text: str = '', _connection=None):
    decoded = _decode_percent(text)
    try:
        body = _process(decoded, 'dialog')
    except Exception:
        body = _clean_glyphs(decoded.replace(FIELD_SEP, '. '))
    # Dialogs demand an answer, so they interrupt and are labelled as such
    # (unless verbosity is brief).
    speech.speak(body if settings.brief() else '{}. {}'.format(lang.t('dialog'), body), source='widget')
    return True


@sims4.commands.Command('a11y.menuopen', command_type=sims4.commands.CommandType.Live)
def a11y_menuopen(count: str = '0', _connection=None):
    try:
        n = int(count)
    except ValueError:
        n = 0
    count_text = '{} {}.'.format(n, lang.t('options'))
    speech.speak(count_text if settings.brief() else '{}. {}'.format(lang.t('menu open'), count_text),
                 source='widget')
    try:
        import tyjokr_a11y_scanner as scanner
        scanner.note_menu_open()
    except ImportError:
        pass
    return True


@sims4.commands.Command('a11y.stop', command_type=sims4.commands.CommandType.Live)
def a11y_stop(arg: str = '', _connection=None):
    # Posted by Flash when a touched control has no text at all. Soft stop:
    # it must not cut down a row label that just started (see request_hush).
    if _rawdiag:
        speech.log_line('RAWDIAG[stop]')
    speech.request_hush()
    return True


# An icon-only control has no text of its own, so Flash sends us its instance
# identifier. That is a poor substitute for the real tooltip ("Wall" for the
# Notification Wall button), so hold it briefly: if the control's tooltip
# arrives, it wins and the derived name is dropped.
_NAME_GRACE_SECONDS = 0.4
_pending_name = None
_pending_name_timer = None
_name_lock = threading.Lock()


def _cancel_pending_name():
    global _pending_name
    with _name_lock:
        _pending_name = None


def _flush_pending_name():
    with _name_lock:
        name = _pending_name
    if name:
        _cancel_pending_name()
        speech.speak(name, source='widget')


@sims4.commands.Command('a11y.widgetname_enc', command_type=sims4.commands.CommandType.Live)
def a11y_widgetname_enc(text: str = '', _connection=None):
    global _pending_name, _pending_name_timer, _row_head
    # An icon-only control: its tooltip is the only text it has, so it must
    # never be deferred as if it were a data row's description.
    _row_head = None
    decoded = _decode_percent(text).strip()
    if _rawdiag:
        speech.log_line('RAWDIAG[widgetname]: ' + ascii(decoded))
    # Instance identifiers arrive camel-cased ("BackgroundColorSelector");
    # split into words. English dev names, fallback for unlabeled controls.
    decoded = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', decoded)
    # Drop the control-type prefix EA's instance names carry ("dd Profit
    # Margin" was heard for the retail markup dropdown, 2026-10-04).
    decoded = re.sub(r'^(?:txt|mc|btn|dd|cb|sl|lb)\s+(?=[A-Z])', '', decoded)
    decoded = re.sub(r'[_\d]+', ' ', decoded).strip()
    # Touching a textless control silences STALE speech, but must not cut a
    # row label that just started (see speech.request_hush).
    speech.request_hush()
    if not decoded:
        return True
    with _name_lock:
        _pending_name = decoded
    if _pending_name_timer is not None:
        _pending_name_timer.cancel()
    _pending_name_timer = threading.Timer(_NAME_GRACE_SECONDS, _flush_pending_name)
    _pending_name_timer.daemon = True
    _pending_name_timer.start()
    return True


@sims4.commands.Command('a11y.event_enc', command_type=sims4.commands.CommandType.Live)
def a11y_event_enc(text: str = '', _connection=None):
    decoded = _decode_percent(text)
    try:
        final = _process(decoded, 'event')
    except Exception as ex:
        speech.log_line('process failed ({!r}); speaking raw'.format(ex))
        final = _clean_glyphs(decoded.replace(FIELD_SEP, '. '))
    speech.speak(final, source='event')
    return True


# Sim-action announcements are an optional feature: the handler always exists
# (so the Flash side can never hit an unknown command), but it only speaks
# when the option is on. Toggled with a11y.simactions, persisted in settings.
def _sim_actions_on():
    return bool(settings.get('sim_actions'))


@sims4.commands.Command('a11y.simactions', command_type=sims4.commands.CommandType.Live)
def a11y_simactions(mode: str = '', _connection=None):
    """a11y.simactions on|off: announce what the active Sim starts doing."""
    output = sims4.commands.CheatOutput(_connection)
    m = mode.lower()
    if m in ('on', 'true', '1'):
        settings.set('sim_actions', True)
        output('a11y: Sim action announcements ON')
        speech.speak('Sim action announcements on.', explicit=True)
    elif m in ('off', 'false', '0'):
        settings.set('sim_actions', False)
        output('a11y: Sim action announcements OFF')
        speech.speak('Sim action announcements off.', explicit=True)
    else:
        output('a11y: Sim action announcements are {}'.format(
            'ON' if _sim_actions_on() else 'OFF'))
        output('a11y: usage a11y.simactions on|off')
    return True


@sims4.commands.Command('a11y.simaction_enc', command_type=sims4.commands.CommandType.Live)
def a11y_simaction_enc(text: str = '', _connection=None):
    if not _sim_actions_on():
        return True
    decoded = _decode_percent(text)
    try:
        final = _process(decoded, 'simaction')
    except Exception as ex:
        speech.log_line('process failed ({!r}); speaking raw'.format(ex))
        final = _clean_glyphs(decoded.replace(FIELD_SEP, '. '))
    speech.speak(final, source='event')
    return True


def _push_autofocus():
    """Synchronize the keyboard master switch with Flash on load and mark.
    Flash starts with capture off until Python supplies the user's setting.
    The old auto_focus cfg value is retained only for file compatibility."""
    try:
        import distributor.ops
        import distributor.system
        state = bool(settings.get('keyboard', True))
        op = distributor.ops.SendUIMessage(
            'A11yKeyboardOn' if state else 'A11yKeyboardOff')
        distributor.system.Distributor.instance().add_op_with_no_owner(op)
    except Exception as ex:
        speech.log_line('autofocus push failed: {!r}'.format(ex))
    push_simplified_menus()


def push_simplified_menus():
    """Tell every live UI copy the Simplified menus switch. Flash starts with
    it on (the default) until Python says otherwise, so it goes out with the
    keyboard switch at zone load, mark and reload, on a settings change and
    with every keyboard lease. Flash acts only when the value changes."""
    try:
        import distributor.ops
        import distributor.system
        state = bool(settings.get('simplified_menus', True))
        distributor.system.Distributor.instance().add_op_with_no_owner(
            distributor.ops.SendUIMessage('A11y|simplifiedmenus|' + ('on' if state else 'off')))
        return True
    except Exception as ex:
        speech.log_line('simplified menus notice failed: {!r}'.format(ex))
        return False


@sims4.commands.Command('a11y.autofocus', command_type=sims4.commands.CommandType.Live)
def a11y_autofocus(mode: str = '', _connection=None):
    """Legacy alias for a11y.keys; focus now follows the keyboard setting."""
    output = sims4.commands.CheatOutput(_connection)
    m = mode.lower()
    if m in ('on', 'true', '1', 'off', 'false', '0'):
        import tyjokr_a11y_keys as keys
        output('a11y: automatic focus is part of keyboard navigation; use a11y.keys.')
        return keys.a11y_keys(m, _connection=_connection)
    else:
        output('a11y: keyboard navigation and automatic focus are {}'.format(
            'ON' if settings.get('keyboard', True) else 'OFF'))
        output('a11y: use a11y.keys on|off')
    return True


@sims4.commands.Command('a11y.speechmode', command_type=sims4.commands.CommandType.Live)
def a11y_speechmode(mode: str = '', _connection=None):
    """a11y.speechmode hover|manual|beeps|off (also cycled by the speech
    mode key, default Numpad 9 or Insert)."""
    output = sims4.commands.CheatOutput(_connection)
    m = mode.lower().replace('-', '_').replace(' ', '_')
    # legacy names from earlier builds
    if m == 'talk':
        m = 'hover'
    elif m in ('ondemand', 'on_demand'):
        m = 'manual'
    if m in speech._VALID_MODES:
        speech.set_mode(m)
        output('a11y: speech mode {}'.format(m))
    else:
        output('a11y: speech mode is {}'.format(speech.speech_mode))
        output('a11y: usage a11y.speechmode hover|manual|beeps|off')
    return True


@sims4.commands.Command('a11y.tooltipdelay', command_type=sims4.commands.CommandType.Live)
def a11y_tooltipdelay(seconds: str = '', _connection=None):
    """a11y.tooltipdelay <seconds|off>: how long a panel row (needs, skills,
    mood, the time panel) holds its description back after reading its name
    and value. Moving the pointer on cancels it; the read key still reads
    everything. off (or 0) reads descriptions immediately."""
    output = sims4.commands.CheatOutput(_connection)
    raw = seconds.strip().lower()
    if raw:
        value = 0.0 if raw in ('off', 'none') else None
        if value is None:
            try:
                value = float(raw)
            except ValueError:
                output('a11y: usage a11y.tooltipdelay <seconds|off>')
                return False
        value = max(0.0, min(10.0, value))
        settings.set('tooltip_delay', value)
        if value <= 0:
            output('a11y: tooltip delay OFF (descriptions read immediately)')
            speech.speak('Tooltip delay off.', explicit=True)
        else:
            output('a11y: tooltip delay {:g} seconds'.format(value))
            speech.speak('Tooltip delay {:g} seconds.'.format(value),
                         explicit=True)
        return True
    delay = _tooltip_delay()
    output('a11y: tooltip delay is {}'.format(
        'off' if delay <= 0 else '{:g} seconds'.format(delay)))
    output('a11y: usage a11y.tooltipdelay <seconds|off>')
    return True


@sims4.commands.Command('a11y.voice', command_type=sims4.commands.CommandType.Live)
def a11y_voice(*args, _connection=None):
    """a11y.voice rate <-10..10> | volume <0..100> | name <voice name> |
    list | reset: SAPI fallback voice only. Screen reader users control
    voice, rate and volume in their own screen reader settings."""
    output = sims4.commands.CheatOutput(_connection)
    parts = [str(part) for part in args]
    sub = parts[0].lower() if parts else ''
    if sub in ('rate', 'volume') and len(parts) >= 2:
        try:
            value = int(parts[1])
        except ValueError:
            output('a11y: {} must be a number'.format(sub))
            return False
        if sub == 'rate':
            value = max(-10, min(10, value))
            settings.set('sapi_rate', value)
        else:
            value = max(0, min(100, value))
            settings.set('sapi_volume', value)
        speech.restart_sapi()
        output('a11y: SAPI {} set to {}'.format(sub, value))
        speech.speak('Voice {} {}.'.format(sub, value), explicit=True)
        return True
    if sub == 'name' and len(parts) >= 2:
        name = ' '.join(parts[1:])
        settings.set('sapi_voice', name)
        speech.restart_sapi()
        output('a11y: SAPI voice set to "{}" (partial name, not case-'
               'sensitive: david, zira or hazel; default voice if nothing '
               'matches)'.format(name))
        speech.speak('Voice changed.', explicit=True)
        return True
    if sub == 'list':
        names = speech.list_voices()
        if not names:
            output('a11y: could not list voices')
            return True
        for name in names:
            output('a11y: voice: {}'.format(name))
        speech.speak('{} voices installed. {}'.format(
            len(names), '. '.join(names)), explicit=True)
        return True
    if sub == 'reset':
        for key in ('sapi_rate', 'sapi_volume', 'sapi_voice'):
            settings.set(key, settings.DEFAULTS[key])
        speech.restart_sapi()
        output('a11y: SAPI voice options reset')
        speech.speak('Voice reset.', explicit=True)
        return True
    output('a11y: SAPI fallback voice: rate {}, volume {}, name "{}"'.format(
        settings.get('sapi_rate'), settings.get('sapi_volume'),
        settings.get('sapi_voice') or 'default'))
    output('a11y: these only apply without a screen reader; screen reader '
           'users set voice/rate/volume in their screen reader')
    output('a11y: usage a11y.voice rate <-10..10> | volume <0..100> | '
           'name <voice> | list | reset')
    return True


@sims4.commands.Command('a11y.mark', command_type=sims4.commands.CommandType.Live)
def a11y_mark(name: str = '', _connection=None):
    speech.log_line('MARK: live TooltipManager copy is from "{}"'.format(name))
    try:
        import tyjokr_a11y_startup as startup
        startup.note_mark(name)
    except Exception:
        pass
    _push_autofocus()
    return True


def _install_zone_hook():
    """Push Flash-side config at every zone load: the only reliably safe
    moment for SendUIMessage, and it re-applies after zone switches."""
    import zone
    original = zone.Zone.on_loading_screen_animation_finished

    def a11y_narrator_on_loading_screen_animation_finished(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        try:
            _push_autofocus()
        except Exception as ex:
            speech.log_line('autofocus zone push failed: {!r}'.format(ex))
        return result

    zone.Zone.on_loading_screen_animation_finished = (
        a11y_narrator_on_loading_screen_animation_finished)


try:
    _install_zone_hook()
except Exception as _zone_ex:
    speech.log_line('narrator zone hook install failed: {!r}'.format(_zone_ex))


@sims4.commands.Command('a11y.speak', command_type=sims4.commands.CommandType.Live)
def a11y_speak(*args, _connection=None):
    text = ' '.join(str(part) for part in args).strip()
    if text:
        speech.speak(text, explicit=True)
    return True


@sims4.commands.Command('a11y.test', command_type=sims4.commands.CommandType.Live)
def a11y_test(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    backend = speech.init()
    speech.speak('Narration test successful. The active backend is {}.'.format(backend), explicit=True)
    output('a11y: spoke test sentence via backend "{}"'.format(backend))
    output('a11y: log file at {}'.format(speech.LOG_PATH))
    return True


@sims4.commands.Command('a11y.braille', command_type=sims4.commands.CommandType.Live)
def a11y_braille(mode: str = '', _connection=None):
    """a11y.braille <concise|full|only|off>"""
    output = sims4.commands.CheatOutput(_connection)
    valid = ('concise', 'full', 'only', 'off')
    if mode.lower() not in valid:
        output('a11y braille mode: {}'.format(speech.braille_mode))
        output('a11y braille display detected: {}'.format(
            'yes' if speech.has_braille() else 'no'))
        output('a11y: usage a11y.braille <{}>'.format('|'.join(valid)))
        output('   concise = speak everything, braille the label')
        output('   full    = speak and braille everything')
        output('   only    = braille only, no speech')
        output('   off     = speech only')
        return True
    speech.braille_mode = mode.lower()
    settings.set('braille_mode', speech.braille_mode)
    output('a11y: braille mode set to {}'.format(speech.braille_mode))
    speech.speak('Braille mode {}.'.format(speech.braille_mode), explicit=True)
    return True


@sims4.commands.Command('a11y.log', command_type=sims4.commands.CommandType.Live)
def a11y_log(mode: str = '', _connection=None):
    """a11y.log on|off: utterance/diagnostic log next to the ts4script."""
    output = sims4.commands.CheatOutput(_connection)
    m = mode.lower()
    if m in ('on', 'true', '1'):
        speech.log_enabled = True
        settings.set('logging', True)
        speech.log_line('logging enabled via a11y.log')
        output('a11y: logging ON -> {}'.format(speech.LOG_PATH))
        speech.speak('Logging on.', explicit=True)
    elif m in ('off', 'false', '0'):
        speech.log_line('logging disabled via a11y.log')
        speech.log_enabled = False
        settings.set('logging', False)
        output('a11y: logging OFF')
        speech.speak('Logging off.', explicit=True)
    else:
        output('a11y: logging is {} (log file: {})'.format(
            'ON' if speech.log_enabled else 'OFF', speech.LOG_PATH))
        output('a11y: usage a11y.log on|off')
    return True


@sims4.commands.Command('a11y.reload', command_type=sims4.commands.CommandType.Live)
def a11y_reload(_connection=None):
    """Re-read TS4_Access.cfg after a hand-edit and apply it live."""
    output = sims4.commands.CheatOutput(_connection)
    settings.reload()
    if not settings.get('captions', False):
        speech.clear_caption()
    speech.log_enabled = bool(settings.get('logging', speech.log_enabled))
    braille = str(settings.get('braille_mode', speech.braille_mode))
    if braille in ('concise', 'full', 'only', 'off'):
        speech.braille_mode = braille
    mode = str(settings.get('speech_mode', 'hover'))
    if mode in speech._VALID_MODES:
        speech.speech_mode = mode
    speech.restart_sapi()
    if speech.retry_screen_reader():
        output('a11y: screen reader detected; speech now routes through it')
    try:
        import tyjokr_a11y_keys as keys
        keys._enabled = bool(settings.get('keyboard', True))
        if keys._enabled:
            keys.start()
    except ImportError:
        pass
    try:
        import tyjokr_a11y_objectnames as objectnames
        objectnames.enable(bool(settings.get('object_names', True)))
    except ImportError:
        pass
    _push_autofocus()
    try:
        import tyjokr_a11y_travel as travel
        travel.apply_setting()
    except Exception as ex:
        speech.log_line('reload: travel list notice failed: {!r}'.format(ex))
    try:
        import tyjokr_a11y_build as build
        build.apply_setting()
    except Exception as ex:
        speech.log_line('reload: build controls notice failed: {!r}'.format(ex))
    try:
        import tyjokr_a11y_keys as keys
        keys.apply_scanner_setting()
    except Exception as ex:
        speech.log_line('reload: scanner mode notice failed: {!r}'.format(ex))
    for err in settings.load_errors:
        output('a11y: warning: ' + err)
    output('a11y: settings reloaded from {}'.format(settings.PATH))
    if settings.load_errors:
        speech.speak('Settings reloaded with {} warnings. {}'.format(
            len(settings.load_errors), ' '.join(settings.load_errors)),
            explicit=True)
    else:
        speech.speak('Settings reloaded.', explicit=True)
    return True


@sims4.commands.Command('a11y.captions', command_type=sims4.commands.CommandType.Live)
def a11y_captions(mode: str = '', _connection=None):
    """a11y.captions [on|off] - display accepted narration on screen."""
    output = sims4.commands.CheatOutput(_connection)
    mode = mode.lower()
    if mode not in ('', 'on', 'off'):
        output('Usage: a11y.captions [on|off]')
        return False
    if mode:
        settings.set('captions', mode == 'on')
        if mode == 'off':
            speech.clear_caption()
    output('a11y: captions {}'.format('on' if settings.get('captions') else 'off'))
    return True


@sims4.commands.Command('a11y.settings', command_type=sims4.commands.CommandType.Live)
def a11y_settings(_connection=None):
    """Read out every option and its current live value."""
    output = sims4.commands.CheatOutput(_connection)
    lines = ['Sim actions {}'.format('on' if _sim_actions_on() else 'off')]
    try:
        import tyjokr_a11y_objectnames as objectnames
        lines.append('object names {}'.format('on' if objectnames._enabled else 'off'))
    except ImportError:
        lines.append('object names unavailable')
    lines.append('scanner {}'.format('on' if settings.get('scanner', True) else 'off'))
    lines.append('captions {}'.format('on' if settings.get('captions', False) else 'off'))
    lines.append('startup speech {}'.format('on' if settings.get('startup', True) else 'off'))
    lines.append('simplified menus {}'.format('on' if settings.get('simplified_menus', True) else 'off'))
    lines.append('travel list {}'.format('on' if settings.get('travel_list', True) else 'off'))
    lines.append('Build controls {}'.format('on' if settings.get('build_controls') else 'off'))
    lines.append('scanner mode {}'.format('on' if settings.get('scanner_mode', False) else 'off'))
    keybind_lines = []
    try:
        import tyjokr_a11y_keys as keys
        lines.append('keyboard navigation {}'.format('on' if keys._enabled else 'off'))
        for message, (label, combos) in keys.BINDINGS.items():
            keybind_lines.append('   {}: {}'.format(
                label, ' or '.join(keys._describe(vk, alt) for (vk, alt) in combos)))
    except ImportError:
        lines.append('keyboard navigation unavailable')
    lines.append('speech mode {}'.format(speech.speech_mode.replace('_', ' ')))
    delay = _tooltip_delay()
    lines.append('tooltip delay {}'.format(
        'off' if delay <= 0 else '{:g} seconds'.format(delay)))
    lines.append('auto focus {}'.format(
        'on' if settings.get('auto_focus') else 'off'))
    lines.append('braille mode {}'.format(speech.braille_mode))
    lines.append('verbosity {}'.format(settings.get('verbosity')))
    lines.append('logging {}'.format('on' if speech.log_enabled else 'off'))
    for line in lines:
        output('a11y: ' + line)
    for line in keybind_lines:
        output(line)
    output('a11y: SAPI fallback voice: rate {}, volume {}, name "{}"'.format(
        settings.get('sapi_rate'), settings.get('sapi_volume'),
        settings.get('sapi_voice') or 'default'))
    output('a11y: settings file: {}'.format(settings.PATH))
    for err in settings.load_errors:
        output('a11y: warning: ' + err)
    speech.speak('. '.join(lines) + '.', explicit=True)
    return True


@sims4.commands.Command('a11y.status', command_type=sims4.commands.CommandType.Live)
def a11y_status(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    output('a11y backend: {}'.format(speech.backend_name()))
    output('a11y screen reader: {}'.format(
        getattr(getattr(speech, '_prism', None), 'name', None) or 'none; Windows fallback'))
    output('a11y speech pack: {}'.format(
        'installed' if speech.speech_pack_installed()
        else 'NOT installed (separate download; screen readers and braille '
             'need it, the Windows voice does not)'))
    output('a11y Prism DLL expected at: {} (present: {})'.format(
        speech.PRISM_DLL_PATH, 'yes' if __import__('os').path.isfile(speech.PRISM_DLL_PATH) else 'no'))
    output('a11y braille: display {} / mode {}'.format(
        'supported by reader' if speech.has_braille() else 'not available', speech.braille_mode))
    output('a11y log: {} ({})'.format(
        'ON' if speech.log_enabled else 'OFF', speech.LOG_PATH))
    return True
