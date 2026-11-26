"""Festivals (Leo, 2026-11-25): see what is on, read the flyer, and travel.

The game's only way to a festival is the flyer (DynamicSignDialog), opened
by the calendar's Read flyer button or a festival sign, whose Travel button
is not reachable by keyboard. This module lists the festivals from the drama
scheduler and does what that button does. Verified against the 1.129.39
bytecode and UI:

- A festival is a FestivalDramaNode (drama_scheduler/festival_drama_node.py),
  drama_node_type DramaNodeType.FESTIVAL. services.drama_scheduler_service()
  .all_nodes_gen() gives scheduled and running nodes; active_nodes_gen() the
  running ones.
- show_festival_info (classmethod) builds the flyer from
  festival_dynamic_sign_info: festival_name, festival_time, activity_info
  (activity_name, activity_description), travel_to_festival_text and the
  not started, on street and on vacation tooltips. The venue is the travel
  lot's zone name. The flyer's Travel is disabled while a running node
  is_during_pre_festival(), when is_on_festival_street(), or while the active
  Sim is_in_travel_group().
- The flyer's Travel button (widgets.DynamicSignDialog.controls.SignContent
  .OnConfirmClick) sends drama.travel_to_event_zone with the node's guid64;
  for a festival that is travel_to_destination(): get_destination_lot_id(),
  get_travel_interaction() and push_travel_interaction(), which pushes the
  interaction on the active Sim with a PICK_TERRAIN pick of that lot.
  travel() does the same steps, so it can say what happened.
- Read flyer in the calendar sends drama.show_festival_info_by_drama_node_uid,
  which calls show_festival_info. While TS4 Access runs, that opens this
  module's festival menu instead of the unreadable flyer.
"""
import tyjokr_a11y_lang as lang
import tyjokr_a11y_speech as speech


def _log(message):
    speech.log_line('festivals: ' + message)


def _text(value):
    """A tuned display string: some are factories that must be called."""
    if value is None:
        return None
    try:
        from sims4.localization import LocalizedString
        if isinstance(value, LocalizedString):
            return value
    except Exception:
        pass
    try:
        return value() if callable(value) else value
    except Exception:
        return None


def _raw(text):
    from sims4.localization import LocalizationHelperTuning
    return LocalizationHelperTuning.get_raw_text(str(text))


def _lines(*parts):
    from sims4.localization import LocalizationHelperTuning
    parts = [p for p in parts if p is not None]
    if not parts:
        return None
    return parts[0] if len(parts) == 1 else LocalizationHelperTuning.get_new_line_separated_strings(*parts)


def _info(node):
    return getattr(node, 'festival_dynamic_sign_info', None)


def _is_festival(node):
    try:
        from drama_scheduler.drama_node_types import DramaNodeType
        return node.drama_node_type == DramaNodeType.FESTIVAL
    except Exception:
        return False


def festivals():
    """[(node, running)] for every scheduled or running festival, one per
    festival, running first, then soonest first."""
    import services
    service = services.drama_scheduler_service()
    if service is None:
        return []
    running = set(id(n) for n in service.active_nodes_gen())
    found = {}
    for node in list(service.all_nodes_gen()):
        if not _is_festival(node) or _info(node) is None:
            # Only festivals with a flyer: Life & Death schedules background
            # festival nodes (festivalDramaNode_EP17_AA_Monday and the like)
            # that have no name, flyer or calendar entry (seen 2026-11-25).
            continue
        key = getattr(node, 'guid64', id(node))
        is_running = id(node) in running
        if key in found and found[key][1] and not is_running:
            continue
        found[key] = (node, is_running)

    def order(item):
        node, is_running = item
        start = _start(node)
        return (0 if is_running else 1, start.absolute_ticks() if start is not None else 0)
    return sorted(found.values(), key=order)


def _start(node):
    for getter in ('get_calendar_start_time', 'selected_time'):
        try:
            value = getattr(node, getter)
            value = value() if callable(value) else value
            if value is not None:
                return value
        except Exception:
            pass
    return None


def _end(node):
    try:
        return node.get_calendar_end_time()
    except Exception:
        return None


def status(node, running):
    """'not started', 'already there', 'on vacation' or None (can travel),
    as the flyer decides whether its Travel button works."""
    import services
    try:
        if not running or node.is_during_pre_festival():
            return 'not started'
        if node.is_on_festival_street():
            return 'already there'
        info = services.active_sim_info()
        if info is not None and info.is_in_travel_group():
            return 'on vacation'
    except Exception as ex:
        _log('status check failed: {!r}'.format(ex))
    return None


def _hours(span):
    try:
        return span.in_hours()
    except Exception:
        return None


def when(node, running):
    """How long until it starts, or until it ends."""
    import services
    now = services.time_service().sim_now
    if running and not node.is_during_pre_festival():
        end = _end(node)
        hours = _hours(end - now) if end is not None else None
        if hours is None:
            return lang.t('festival on now')
        if hours < 1:
            return lang.t('festival ending soon')
        return lang.t('festival ends in hours').format(int(round(hours)))
    start = _start(node)
    hours = _hours(start - now) if start is not None else None
    if hours is None or hours < 1:
        return lang.t('festival starting soon')
    if hours < 36:
        return lang.t('festival starts in hours').format(int(round(hours)))
    return lang.t('festival starts in days').format(int(round(hours / 24)))


def venue(node):
    """The festival lot's name, as the flyer shows it."""
    import services
    try:
        lot_id = node.get_travel_lot_id()
        persistence = services.get_persistence_service()
        zone_id = persistence.resolve_lot_id_into_zone_id(lot_id, ignore_neighborhood_id=True)
        proto = persistence.get_zone_proto_buff(zone_id)
        if proto is not None and proto.name:
            return proto.name
    except Exception as ex:
        _log('venue lookup failed: {!r}'.format(ex))
    return None


def _name(node):
    info = _info(node)
    name = _text(getattr(info, 'festival_name', None)) if info is not None else None
    return name if name is not None else _raw(type(node).__name__)


def _find(guid):
    for node, running in festivals():
        if getattr(node, 'guid64', None) == guid:
            return node, running
    return None, False


def open_festivals():
    """The festivals menu: one row per festival, with when it is on."""
    import tyjokr_a11y_hub as hub
    try:
        items = festivals()
    except Exception as ex:
        _log('list failed: {!r}'.format(ex))
        hub._say('action unavailable')
        return False
    if not items:
        hub._say('no festivals')
        return False
    rows = []
    for node, running in items:
        info = _info(node)
        detail = _lines(_raw(when(node, running)), _text(getattr(info, 'festival_time', None)))
        rows.append((_name(node), detail, lambda guid=node.guid64: open_festival(guid)))
    return hub._window('festivals', 'festivals instructions', rows)


def open_festival(guid, selected_index=None):
    """One festival: Travel, when, where and each advertised activity."""
    import tyjokr_a11y_hub as hub
    node, running = _find(guid)
    if node is None:
        hub._say('festival over')
        return False
    info = _info(node)
    blocked = status(node, running)
    travel_label = _text(getattr(info, 'travel_to_festival_text', None)) or _raw(lang.t('festival travel'))
    travel_note = _raw(lang.t('festival ' + blocked) if blocked else lang.t('festival travel available'))
    rows = [(travel_label, travel_note, lambda: travel(guid))]
    again = lambda index: (lambda: open_festival(guid, selected_index=index))
    rows.append((_raw(lang.t('festival when')),
                 _lines(_raw(when(node, running)), _text(getattr(info, 'festival_time', None))), again(1)))
    place = venue(node)
    if place:
        rows.append((_raw(lang.t('festival where')), _raw(place), again(len(rows))))
    for activity in getattr(info, 'activity_info', None) or ():
        name = _text(getattr(activity, 'activity_name', None))
        if name is None:
            continue
        rows.append((name, _text(getattr(activity, 'activity_description', None)), again(len(rows))))
    rows.append((_raw(lang.t('back to festivals')), None, open_festivals))
    return hub._window('festivals', 'festival instructions', rows,
                       localized_title=_name(node), selected_index=selected_index)


def travel(guid):
    """Send the active Sim to the festival, as the flyer's Travel button does."""
    import services
    import tyjokr_a11y_hub as hub
    node, running = _find(guid)
    if node is None:
        hub._say('festival over')
        return False
    blocked = status(node, running)
    if blocked:
        hub._say('festival ' + blocked)
        return False
    try:
        lot_id = node.get_destination_lot_id()
        interaction = node.get_travel_interaction()
        if lot_id is None or interaction is None:
            _log('no destination: lot {} interaction {}'.format(lot_id, interaction))
            hub._say('festival already there' if lot_id is None else 'festival travel refused')
            return False
        from objects import ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED
        from server.pick_info import PickInfo, PickType
        from interactions.context import InteractionContext, QueueInsertStrategy
        from interactions.priority import Priority
        info = services.active_sim_info()
        sim = info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED) if info else None
        if sim is None:
            hub._say('sim unavailable')
            return False
        pick = PickInfo(pick_type=PickType.PICK_TERRAIN, lot_id=lot_id, ignore_neighborhood_id=True)
        context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT_WITH_USER_INTENT, Priority.High,
                                     insert_strategy=QueueInsertStrategy.NEXT, pick=pick)
        result = sim.push_super_affordance(interaction, None, context)
    except Exception as ex:
        _log('travel failed: {!r}'.format(ex))
        hub._say('festival travel refused')
        return False
    if not result:
        _log('travel refused: {}'.format(getattr(result, 'reason', result)))
        hub._say('festival travel refused')
        return False
    hub._say('festival travelling')
    return True


def _install():
    """Read flyer (calendar, signs) opens the festival menu instead of the
    game's flyer, which has no keyboard access. The flyer still opens if the
    menu cannot."""
    from drama_scheduler.festival_drama_node import FestivalDramaNode
    original = FestivalDramaNode.__dict__.get('show_festival_info')
    if original is None or getattr(original, '_a11y_wrapped', False):
        return
    function = original.__func__

    def a11y_show_festival_info(cls, *args, **kwargs):
        try:
            # A sign may advertise a festival that is not on the calendar
            # now; that one keeps the game's flyer.
            if _find(cls.guid64)[0] is not None and open_festival(cls.guid64):
                return None
        except Exception as ex:
            _log('flyer menu failed: {!r}'.format(ex))
        return function(cls, *args, **kwargs)
    wrapped = classmethod(a11y_show_festival_info)
    a11y_show_festival_info._a11y_wrapped = True
    wrapped._a11y_wrapped = True
    FestivalDramaNode.show_festival_info = wrapped
    _log('flyer menu installed')


try:
    import sims4.commands

    @sims4.commands.Command('a11y.festivals', command_type=sims4.commands.CommandType.Live)
    def a11y_festivals(_connection=None):
        return open_festivals()
    _install()
except Exception as _ex:
    _log('not installed: {!r}'.format(_ex))
