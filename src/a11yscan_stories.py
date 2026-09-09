"""The CAS Stories questionnaire, played with the keyboard.

This is the game's real questionnaire, not an imitation of it: 66 questions and
198 answers read straight from tuning, with the game's own scoring. Each answer
carries weightings that point at a trait, a trait chooser, or an aspiration
track; weights accumulate across the answers you give, and a trait chooser turns
its accumulated weight into a trait by threshold (see CasStoriesTraitChooser -
lowest threshold is 0.0 and the rest are non-inclusive).

The tunable field names on an answer's weighting list are not in the scripts
in a form worth guessing at, so the shapes are discovered at runtime and the
first one seen is written to the log. Guessing structure has cost us several
rounds; asking the object costs one.
"""
import a11yscan_dialogs as dialogs
import a11yscan_log as logfile

# How many questions to offer by default. The game asks a handful, not all 66,
# and a blind player should not have to sit through every one to get a Sim.
DEFAULT_COUNT = 10

_questions = []
_index = 0
_answer_index = 0
_chosen = {}
_shape_logged = False


def loaded():
    return bool(_questions)


def _text_of(tuning, *attrs):
    for attr in attrs:
        try:
            text = dialogs.loc_text(getattr(tuning, attr, None))
        except Exception:
            text = None
        if text:
            return text
    return None


def _log_shape(answer, entry):
    """Record what a weighting entry actually looks like, once."""
    global _shape_logged
    if _shape_logged:
        return
    _shape_logged = True
    try:
        logfile.write('stories: answer fields: {}'.format(
            ', '.join(n for n in dir(answer) if not n.startswith('_'))[:300]))
    except Exception:
        pass
    try:
        logfile.write('stories: weighting entry {!r} fields: {}'.format(
            type(entry).__name__,
            ', '.join(n for n in dir(entry) if not n.startswith('_'))[:300]))
    except Exception:
        pass


def _weightings(answer):
    """The weighted targets on an answer, whatever the field is called."""
    for attr in ('weightings', 'cas_answer_weightings', 'answer_weightings',
                 'trait_weightings', 'traits'):
        try:
            value = getattr(answer, attr, None)
        except Exception:
            continue
        if value:
            try:
                return list(value)
            except Exception:
                continue
    return []


def _entry_parts(entry):
    """(target, weight) out of a weighting entry.

    Confirmed at runtime: each entry is an ImmutableSlots carrying `weight`
    and `weighted_object`. The looser search below stays as a fallback for
    packs that might tune this differently, but the named fields come first
    so we are not relying on a dir() scan picking the right attribute.
    """
    try:
        target = entry.weighted_object
        weight = float(entry.weight)
        if target is not None:
            return target, weight
    except Exception:
        pass
    weight = None
    target = None
    for attr in ('weight', 'weighting', 'value', 'amount'):
        try:
            found = getattr(entry, attr, None)
        except Exception:
            continue
        if isinstance(found, (int, float)):
            weight = float(found)
            break
    for attr in ('trait', 'target', 'trait_chooser', 'aspiration',
                 'aspiration_track', 'reward'):
        try:
            found = getattr(entry, attr, None)
        except Exception:
            continue
        if found is not None and not isinstance(found, (int, float, str)):
            target = found
            break
    if target is None:
        # A TunableVariant may expose the chosen branch under an odd name, so
        # fall back to the first non-numeric attribute that looks like tuning.
        for attr in dir(entry):
            if attr.startswith('_'):
                continue
            try:
                found = getattr(entry, attr, None)
            except Exception:
                continue
            if found is None or isinstance(found, (int, float, str, bool)):
                continue
            if hasattr(found, 'guid64') or hasattr(found, 'traits'):
                target = found
                break
    if weight is None:
        weight = 1.0
    return target, weight


def load(count=DEFAULT_COUNT):
    """Pick a set of questions and reset the run."""
    global _questions, _index, _answer_index, _chosen
    _questions = []
    _index = 0
    _answer_index = 0
    _chosen = {}
    try:
        import random
        import services
        import sims4.resources
        manager = services.get_instance_manager(
            sims4.resources.Types.CAS_STORIES_QUESTION)
        pool = []
        for question in manager.types.values():
            text = _text_of(question, 'text', 'question_text', 'display_text')
            if not text:
                continue
            answers = []
            for answer in (getattr(question, 'possible_answers', None) or ()):
                answer_text = _text_of(answer, 'text', 'answer_text',
                                       'display_text')
                if answer_text:
                    answers.append((answer_text, answer))
            if len(answers) >= 2:
                pool.append((text, answers))
        pool.sort(key=lambda pair: pair[0].lower())
        if count and count < len(pool):
            _questions = random.sample(pool, count)
        else:
            _questions = pool
        logfile.write('stories: {} questions offered from a pool of {}'.format(
            len(_questions), len(pool)))
    except Exception as ex:
        logfile.fail('stories: could not load questions ({!r})'.format(ex))
    return len(_questions)


def total():
    return len(_questions)


def answered():
    return len(_chosen)


def describe():
    """The current question and the answer under the cursor."""
    if not _questions:
        return 'No questions loaded.'
    if _index >= len(_questions):
        if not _chosen:
            return ('You have not answered any questions yet. Up arrow to go '
                    'back, then left or right to pick an answer.')
        return ('Answered {} of {}. Enter to see what they say about your '
                'Sim.'.format(len(_chosen), len(_questions)))
    text, answers = _questions[_index]
    position = _answer_index % len(answers)
    chosen = _chosen.get(_index)
    mark = ''
    if chosen is not None:
        mark = ' (chosen)' if chosen == position else ' (another answer chosen)'
    return 'Question {} of {}, {} answered. {} Answer {} of {}: {}{}'.format(
        _index + 1, len(_questions), len(_chosen), text, position + 1,
        len(answers), answers[position][0], mark)


def next_question(step=1):
    global _index, _answer_index
    if not _questions:
        return 'No questions loaded.'
    # One past the end is the results step, so you can finish early.
    _index = max(0, min(_index + step, len(_questions)))
    _answer_index = _chosen.get(_index, 0)
    return describe()


def _record(position):
    _chosen[_index] = position
    try:
        text, answers = _questions[_index]
        logfile.write('stories: Q{} {!r} -> {!r}'.format(
            _index + 1, text[:40], answers[position][0][:40]))
    except Exception:
        pass


def next_answer(step=1):
    """Left and right pick an answer.

    Landing on an answer records it, rather than merely previewing it. The
    first version only recorded on Enter, so walking the questions with up and
    down answered nothing while still announcing "all questions done" - which
    sounds exactly like success.
    """
    global _answer_index
    if not _questions or _index >= len(_questions):
        return describe()
    _text, answers = _questions[_index]
    _answer_index = (_answer_index + step) % len(answers)
    _record(_answer_index)
    return describe()


def choose():
    """Lock in the answer under the cursor and move on."""
    global _index, _answer_index
    if not _questions:
        return 'No questions loaded.'
    if _index >= len(_questions):
        return None            # caller should read the results
    _text, answers = _questions[_index]
    position = _answer_index % len(answers)
    _record(position)
    _index += 1
    _answer_index = _chosen.get(_index, 0)
    if _index >= len(_questions):
        return ('Answered. That is all {} questions. Enter again for the '
                'result.'.format(len(_questions)))
    return 'Answered. {}'.format(describe())


def skip():
    return next_question(1)


def _resolve_chooser(chooser, weight):
    """Turn an accumulated weight into a trait, by threshold."""
    best = None
    best_threshold = None
    try:
        mapping = getattr(chooser, 'traits', None) or {}
        items = mapping.items() if hasattr(mapping, 'items') else mapping
        for key, value in items:
            try:
                threshold = float(key)
            except Exception:
                threshold = getattr(key, 'weighting_threshold', None)
                value = getattr(key, 'trait_to_assign', value)
                if threshold is None:
                    continue
                threshold = float(threshold)
            # 0.0 always selects the lowest trait by convention; above that the
            # thresholds are non-inclusive.
            if threshold == 0.0 or weight > threshold:
                if best_threshold is None or threshold >= best_threshold:
                    best_threshold = threshold
                    best = value
    except Exception as ex:
        logfile.write('stories: chooser resolution failed ({!r})'.format(ex))
    return best


def _classify(target):
    """Trait, trait chooser, or aspiration track.

    These are tuning classes rather than instances, so type(target).__name__
    gives the metaclass and never mentions Aspiration - the first version
    filed every aspiration under traits, which is why none was ever applied.
    Test for the tunables each kind actually declares instead.
    """
    if hasattr(target, 'traits'):
        return 'chooser'
    if hasattr(target, 'trait_type') or hasattr(target, 'is_personality_trait'):
        return 'trait'
    name = getattr(target, '__name__', '') or ''
    if 'aspiration' in name.lower() or hasattr(target, 'aspirations'):
        return 'aspiration'
    try:
        import services
        import sims4.resources
        manager = services.get_instance_manager(
            sims4.resources.Types.ASPIRATION_TRACK)
        if target in manager.types.values():
            return 'aspiration'
    except Exception:
        pass
    return 'trait'


def results():
    """Score the answers the way the game does: traits and an aspiration."""
    trait_scores = {}
    chooser_scores = {}
    aspiration_scores = {}
    for question_index, answer_index in _chosen.items():
        try:
            _text, answers = _questions[question_index]
            answer = answers[answer_index][1]
        except Exception:
            continue
        for entry in _weightings(answer):
            _log_shape(answer, entry)
            target, weight = _entry_parts(entry)
            if target is None:
                continue
            kind = _classify(target)
            if kind == 'chooser':
                chooser_scores[target] = chooser_scores.get(target, 0.0) + weight
            elif kind == 'aspiration':
                aspiration_scores[target] = aspiration_scores.get(target, 0.0) + weight
            else:
                trait_scores[target] = trait_scores.get(target, 0.0) + weight

    for chooser, weight in chooser_scores.items():
        trait = _resolve_chooser(chooser, weight)
        if trait is not None:
            trait_scores[trait] = trait_scores.get(trait, 0.0) + weight

    traits = [t for t, _w in sorted(trait_scores.items(),
                                    key=lambda kv: kv[1], reverse=True)][:12]
    aspiration = None
    if aspiration_scores:
        aspiration = max(aspiration_scores.items(), key=lambda kv: kv[1])[0]
    logfile.write('stories: {} answers scored -> {} traits, {} choosers, '
                  '{} aspirations'.format(len(_chosen), len(trait_scores),
                                          len(chooser_scores),
                                          len(aspiration_scores)))
    return traits, aspiration


def results_text(traits, aspiration):
    names = []
    for trait in traits[:3]:
        names.append(_text_of(trait, 'display_name') or
                     getattr(trait, '__name__', 'a trait'))
    parts = []
    if names:
        parts.append('Your answers suggest {}'.format(', '.join(names)))
    elif not _chosen:
        parts.append('You did not answer any questions, so nothing changed')
    else:
        parts.append('Your {} answers did not settle on any traits'.format(
            len(_chosen)))
    if aspiration is not None:
        parts.append('and the {} aspiration'.format(
            _text_of(aspiration, 'display_text', 'display_name') or
            getattr(aspiration, '__name__', 'chosen')))
    return '. '.join(parts) + '.'
