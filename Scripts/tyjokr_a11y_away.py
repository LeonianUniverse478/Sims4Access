"""Household portrait menus through EA's native PICK_SKEWER request.

Only opens the game's menu. Never switches Sims, travels, or applies an
away action directly. Called on the simulation-thread pump by the hub.
"""
import math
import tyjokr_a11y_lang as lang
import tyjokr_a11y_speech as speech


def _say(term):
    speech.speak(lang.t(term), explicit=True)


def _state():
    import services
    import tyjokr_a11y_place as place
    if place.in_build_mode():
        return None
    actor = services.get_active_sim()
    household = services.active_household()
    lot = services.active_lot()
    if actor is None or household is None or lot is None:
        return None
    if actor.sim_info.household is not household:
        return None
    return actor, household, lot, services.current_zone_id()


def _candidates(household, actor_id):
    result = {}
    for info in household.sim_info_gen():
        if info.sim_id == actor_id or info.is_baby:
            continue
        # Default get_sim_instance excludes hidden instances, as in EA's
        # own portrait-menu path. Work/school tones remain native choices.
        if info.get_sim_instance() is not None:
            continue
        result[int(info.sim_id)] = info
    return result


def open_sim(sim_id, actor_id, zone_id, household_id):
    try:
        import tyjokr_a11y_scanner as scanner
        from server.pick_info import PickType
        state = _state()
        if state is None:
            raise ValueError('no live household context')
        actor, household, lot, current_zone = state
        if actor.sim_info.sim_id != actor_id or current_zone != zone_id or household.id != household_id:
            raise ValueError('household, actor or zone changed')
        info = _candidates(household, actor_id).get(sim_id)
        if info is None:
            raise ValueError('target no longer away in this household')
        pos = actor.position
        point = tuple(float(v) for v in (pos.x, pos.y, pos.z))
        if not all(math.isfinite(v) for v in point):
            raise ValueError('invalid actor position')
        lot_id = int(lot.lot_id)
        if lot_id < 0:
            raise ValueError('invalid lot')
        if lot_id > 0xffffffff:
            lot_id = 0  # Native current-lot sentinel; never truncate an ID.
        name = ' '.join(p for p in (info.first_name, info.last_name) if p).replace('|', ' ')
        sent = scanner._send_ui('A11y|pick|{}|{}|{}|{}|{:.3f}|{:.3f}|{:.3f}|{}'.format(
            sim_id, int(PickType.PICK_SKEWER), lot_id, name, *point, int(actor.level)))
        speech.log_line('away actions: portrait request sim={} actor={} zone={} sent={}'.format(
            sim_id, actor_id, current_zone, bool(sent)))
        if not sent:
            _say('action unavailable')
        return bool(sent)
    except Exception as exc:
        speech.log_line('away actions: request refused: {}: {}'.format(type(exc).__name__, exc))
        _say('action unavailable')
        return False


def open_away_actions():
    try:
        import tyjokr_a11y_hub as hub
        import tyjokr_a11y_menu as menu
        state = _state()
        if state is None:
            _say('action unavailable')
            return False
        actor, household, lot, zone_id = state
        actor_id, household_id = actor.sim_info.sim_id, household.id
        candidates = _candidates(household, actor_id)
        rows = []
        for ident, info in sorted(candidates.items(), key=lambda pair: (
                pair[1].first_name.casefold(), pair[1].last_name.casefold(), pair[0])):
            name = ' '.join(p for p in (info.first_name, info.last_name) if p)
            rows.append((menu._raw(name or str(ident)), None,
                         lambda ident=ident: open_sim(ident, actor_id, zone_id, household_id)))
        speech.log_line('away actions: household={} zone={} candidates={}'.format(household_id, zone_id, len(rows)))
        if not rows:
            _say('no away household sims')
            return False
        return hub._window('away actions', 'away actions instructions', rows)
    except Exception as exc:
        speech.log_line('away actions: picker failed: {}: {}'.format(type(exc).__name__, exc))
        _say('action unavailable')
        return False
