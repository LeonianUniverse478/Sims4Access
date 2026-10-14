"""Pack parts of Simology as native pickers for the active Sim.

Milestones (Growing Together, EP13) come from the Sim's
DevelopmentalMilestoneTracker. Only milestones EA's panel would show are
listed: the tracker's own is_milestone_visible test, as in
send_all_milestones_update_to_client. Rows are grouped by EA's milestone
categories (DevelopmentalMilestone.DEVELOPMENTAL_MILESTONE_CATEGORIES) and
ordered by ui_sort_order.

Character values (Parenthood, GP05) are the LifeSkillStatistic entries in the
Sim's commodity tracker: name, current value on the tuned scale, the trait the
value's range gives at age up, and EA's description.

Everything is read again when a row is chosen; nothing here changes the game.
"""
import tyjokr_a11y_lang as lang
import tyjokr_a11y_menu as menu
import tyjokr_a11y_speech as speech

# sims.sim_info_types.Age member names.
AGES = ('BABY', 'INFANT', 'TODDLER', 'CHILD', 'TEEN', 'YOUNGADULT', 'ADULT', 'ELDER')


def _say(term):
    speech.speak(lang.t(term), explicit=True)


def _pack(name):
    try:
        from sims4.common import Pack, is_available_pack
        return bool(is_available_pack(getattr(Pack, name)))
    except Exception:
        return False


def milestones_available():
    return _pack('EP13')


def values_available():
    return _pack('GP05')


def _active_info():
    import services
    client = services.client_manager().get_first_client()
    return getattr(client, 'active_sim_info', None) if client is not None else None


def _name(info):
    return ' '.join(p for p in (getattr(info, 'first_name', ''),
                                getattr(info, 'last_name', '')) if p)


def _lines(*parts):
    """One localized description from EA strings and narration text."""
    from sims4.localization import LocalizationHelperTuning
    strings = [menu._raw(p) if isinstance(p, str) else p for p in parts if p]
    if not strings:
        return None
    if len(strings) == 1:
        return strings[0]
    return LocalizationHelperTuning.get_new_line_separated_strings(*strings)


def age_name(age):
    try:
        from sims.sim_info_types import Age
        key = Age(age).name
    except Exception:
        key = str(getattr(age, 'name', age))
    if key not in AGES:
        return ''
    return lang.t('age ' + key.lower())


# ------------------------------------------------------------------ milestones

def _tracker(info):
    return getattr(info, 'developmental_milestone_tracker', None) if info is not None else None


def _milestone_entries(tracker, info):
    """(milestone, data) pairs EA's panel shows, active and archived."""
    from event_testing.resolver import SingleSimResolver
    resolver = SingleSimResolver(info)
    entries = []
    for milestone, data in list(tracker._active_milestones_data.items()):
        try:
            if tracker.is_milestone_visible(milestone, resolver):
                entries.append((milestone, data))
        except Exception:
            continue
    for milestone, data in list(tracker._archived_milestones_data.items()):
        entries.append((milestone, data))
    return entries


def _state(data):
    from developmental_milestones.developmental_milestone_enums import DevelopmentalMilestoneStates
    state = getattr(data, 'state', None)
    if state == DevelopmentalMilestoneStates.UNLOCKED:
        return 'reached'
    if state == DevelopmentalMilestoneStates.ACTIVE:
        return 'in progress'
    return 'not reached'


def _reached_count(milestone, data):
    """Times reached, counting earlier goals of a repeatable milestone."""
    count = 1 if _state(data) == 'reached' else 0
    if getattr(milestone, 'repeatable', False):
        count += len(getattr(data, 'previous_goals', None) or ())
    return count


def _category_name(category):
    from developmental_milestones.developmental_milestone import DevelopmentalMilestone
    entry = DevelopmentalMilestone.DEVELOPMENTAL_MILESTONE_CATEGORIES.get(category)
    return getattr(entry, 'name', None) if entry is not None else None


def milestone_detail(milestone, data):
    state = _state(data)
    count = _reached_count(milestone, data)
    if count > 1:
        status = lang.t('milestone reached times').format(count)
    elif count == 1:
        age = age_name(getattr(data, 'age_completed', None))
        status = lang.t('milestone reached at').format(age) if age else lang.t('milestone reached')
    elif state == 'in progress':
        status = lang.t('milestone in progress')
    else:
        status = lang.t('milestone not reached')
    if count:
        text = getattr(milestone, 'unlocked_text_no_context', None)
    else:
        primary = getattr(milestone, 'is_primary_milestone', None)
        text = getattr(primary, 'hint_text', None) if primary is not None else None
    return _lines(status, text)


def _groups(entries):
    groups = {}
    for milestone, data in entries:
        groups.setdefault(getattr(milestone, 'category', None), []).append((milestone, data))
    for items in groups.values():
        items.sort(key=lambda pair: getattr(pair[0], 'ui_sort_order', 0))
    return groups


def _read(info):
    tracker = _tracker(info)
    if tracker is None:
        return None
    return _groups(_milestone_entries(tracker, info))


def milestones_window():
    """Categories for the active Sim; Enter lists that category's milestones."""
    import tyjokr_a11y_hub as hub
    info = _active_info()
    if info is None:
        _say('load a household first')
        return False
    try:
        groups = _read(info)
    except Exception as ex:
        speech.log_line('simology: milestones unavailable ({!r})'.format(ex))
        _say('action unavailable')
        return False
    if not groups:
        speech.speak(lang.t('no milestones').format(_name(info)), explicit=True)
        return False
    sim_id = info.sim_id
    rows = []
    for category in sorted(groups, key=lambda c: int(c) if c is not None else 0):
        items = groups[category]
        name = _category_name(category)
        if name is None:
            continue
        reached = sum(1 for m, d in items if _reached_count(m, d))
        detail = lang.t('milestone category detail').format(reached, len(items))
        rows.append((name, menu._raw(detail),
                     lambda value=category: milestone_category(sim_id, value)))
    if not rows:
        speech.speak(lang.t('no milestones').format(_name(info)), explicit=True)
        return False
    return hub._window('milestones', lang.t('milestones instructions').format(_name(info)), rows)


def milestone_category(sim_id, category):
    import services
    import tyjokr_a11y_hub as hub
    info = services.sim_info_manager().get(sim_id)
    if info is None:
        _say('sim unavailable')
        return False
    try:
        items = (_read(info) or {}).get(category, [])
    except Exception as ex:
        speech.log_line('simology: milestone category unavailable ({!r})'.format(ex))
        _say('action unavailable')
        return False
    rows = []
    for milestone, data in items:
        name = getattr(milestone, 'name', None)
        if name is None:
            continue
        # Reading only: Enter repeats the row instead of acting.
        detail = milestone_detail(milestone, data)
        rows.append((name, detail, lambda: milestone_category(sim_id, category)))
    if not rows:
        speech.speak(lang.t('no milestones').format(_name(info)), explicit=True)
        return False
    return hub._window('milestones', lang.t('milestone list instructions'), rows,
                       localized_title=_category_name(category))


# ------------------------------------------------------------ character values

def _display(stat_type, attr):
    try:
        return getattr(stat_type, attr)
    except Exception:
        return None


def _life_skills(info):
    from statistics.life_skill_statistic import LifeSkillStatistic
    tracker = getattr(info, 'commodity_tracker', None)
    if tracker is None:
        return []
    return [stat for stat in list(tracker) if isinstance(stat, LifeSkillStatistic)]


def _range_trait(stat_type, value, info):
    """The trait this value's tuned range gives at age up, if any."""
    for entry in getattr(stat_type, 'trait_on_age_up_list', None) or ():
        bounds = getattr(entry, 'life_skill_range', None)
        upgrade = getattr(entry, 'age_up_info', None)
        if bounds is None or upgrade is None:
            continue
        if not bounds.lower_bound <= value <= bounds.upper_bound:
            continue
        trait = getattr(upgrade, 'life_skill_trait', None)
        if trait is None:
            continue
        try:
            return trait.display_name(info), age_name(getattr(upgrade, 'age_to_apply_trait', None))
        except Exception:
            continue
    return None, ''


def value_text(value, low, high):
    """'35 on a scale from -100 to 100'."""
    return lang.t('value on scale').format(int(round(value)), int(round(low)), int(round(high)))


def value_detail(stat, info):
    stat_type = type(stat)
    value = stat.get_value()
    low = getattr(stat_type, 'min_value_tuning', getattr(stat, 'min_value', 0))
    high = getattr(stat_type, 'max_value_tuning', getattr(stat, 'max_value', 100))
    parts = [value_text(value, low, high)]
    trait, age = _range_trait(stat_type, value, info)
    if trait is not None:
        parts.append(lang.t('value heading to at').format(age) if age else lang.t('value heading to'))
        parts.append(trait)
    parts.append(_display(stat_type, 'display_description') or _display(stat_type, 'display_tooltip'))
    return _lines(*parts)


def values_window():
    import tyjokr_a11y_hub as hub
    info = _active_info()
    if info is None:
        _say('load a household first')
        return False
    try:
        stats = _life_skills(info)
    except Exception as ex:
        speech.log_line('simology: character values unavailable ({!r})'.format(ex))
        _say('action unavailable')
        return False
    rows = []
    for stat in stats:
        name = _display(type(stat), 'display_name')
        if name is None:
            continue
        try:
            detail = value_detail(stat, info)
        except Exception as ex:
            speech.log_line('simology: value {} unreadable ({!r})'.format(type(stat).__name__, ex))
            continue
        # Reading only: Enter reopens the list.
        rows.append((name, detail, values_window))
    if not rows:
        speech.speak(lang.t('no character values').format(_name(info)), explicit=True)
        return False
    return hub._window('character values', lang.t('character values instructions').format(_name(info)), rows)
