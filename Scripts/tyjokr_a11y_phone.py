"""Announce waiting household calls; open the recipient's existing phone UI.

No automatic responses, timeout changes or background-thread game calls.

Simplified menus add the phone list: the same actions the phone offers now,
built by EA's own phone menu code (the phone's disable tests, its choice
menu, tests, visibility, names and categories), shown in two picker
windows (categories, then actions). Choosing an action runs it exactly as
the phone would (test_and_execute), so it opens the game's own career
picker, event planner, move screen and so on. Travel goes through the
travel list's own Go alone / Choose who comes window.
"""
import functools
import sims4.commands
import tyjokr_a11y_lang as lang
import tyjokr_a11y_settings as settings
import tyjokr_a11y_speech as speech

_waiting = []  # (dialog_id, owner_id), oldest first


def _recipient(dialog):
    owner = getattr(dialog, 'owner', None)
    info = getattr(owner, 'sim_info', owner)
    return getattr(info, 'sim_id', 0), info


def _note(dialog, phone_ring_type):
    from ui.ui_dialog import PhoneRingType
    import services
    if phone_ring_type == PhoneRingType.NO_RING or not settings.get('keyboard', True):
        return
    owner_id, info = _recipient(dialog)
    if not owner_id:
        return
    client = services.client_manager().get_first_client()
    if client is None or info not in client.selectable_sims:
        return
    token = (dialog.dialog_id, owner_id)
    if token in _waiting:
        return
    _waiting.append(token)
    del _waiting[:-32]
    name = ' '.join(part for part in (getattr(info, 'first_name', ''),
                                      getattr(info, 'last_name', '')) if part)
    speech.speak('Phone for {}. Control Alt P opens the waiting call or text.'.format(name),
                 source='event')


def open_waiting(list_when_none=False):
    """Runs only on the simulation pump or a game command callback. With
    list_when_none (Control Alt P) and Simplified menus on, the phone list
    opens when no call or text is waiting; a waiting one always comes first."""
    import services
    import distributor.ops
    import distributor.system
    service = services.ui_dialog_service()
    client = services.client_manager().get_first_client()
    if service is None or client is None:
        return False
    active = getattr(service, '_active_dialogs', {})
    while _waiting:
        dialog_id, owner_id = _waiting[0]
        dialog = active.get(dialog_id)
        info = services.sim_info_manager().get(owner_id)
        if dialog is None or info not in client.selectable_sims:
            _waiting.pop(0)
            continue
        if client.active_sim_info is not info and not client.set_active_sim_by_id(owner_id):
            speech.speak('The recipient is not available.', explicit=True)
            return False
        # Flash waits for ActiveSimId to match before clicking the phone.
        op = distributor.ops.SendUIMessage('A11y|phone|{}'.format(owner_id))
        distributor.system.Distributor.instance().add_op_with_no_owner(op)
        return True
    if list_when_none and simplified():
        return open_list()
    speech.speak('No waiting call or text.', explicit=True)
    return False


# ------------------------------------------------------------- phone list

_list_id = None        # our open phone window
_list = None           # the _PhoneList behind it
_CLOSE_WAIT = 1.0      # seconds a chosen action waits for our window to close


def simplified():
    return bool(settings.get('simplified_menus', True))


def _say(term):
    speech.speak(lang.t(term), explicit=True)


class _Entry(object):
    __slots__ = ('aop', 'name', 'enabled', 'tip', 'detail', 'affordance_id')

    def __init__(self, aop, name, enabled, tip, detail):
        self.aop = aop
        self.name = name
        self.enabled = enabled
        self.tip = tip
        self.detail = detail
        self.affordance_id = getattr(aop.affordance, 'guid64', None)


class _PhoneList(object):
    def __init__(self, sim_id, groups, direct):
        self.sim_id = sim_id
        self.groups = groups      # [(localized label, [_Entry])], in phone order
        self.direct = direct      # [_Entry] with no category


def _root(category):
    depth = 0
    while category is not None and getattr(category, '_parent', None) is not None and depth < 8:
        category = category._parent
        depth += 1
    return category


def _collect(sim, client):
    """EA's own phone menu (interactions.phone_choices and
    create_pie_menu_message): the same aops, tests, visibility, names and
    reasons the phone would show."""
    import services
    import sims4.resources
    from interactions.choices import ChoiceMenu
    context = client.create_interaction_context(sim)
    choice_menu = ChoiceMenu(sim)
    choice_menu.add_potential_aops(None, context, sim.potential_phone_interactions(context), None)
    categories = services.get_instance_manager(sims4.resources.Types.PIE_MENU_CATEGORY)
    tutorial = services.get_tutorial_service()
    groups, order, direct = {}, [], []
    for _option_id, item in choice_menu:
        aop = item.aop
        affordance = aop.affordance
        if tutorial is not None and not tutorial.is_affordance_visible(affordance):
            continue
        # As EA's create_pie_menu_message (1.128.90 bytecode, lines 881-884):
        # the pie menu modifiers decide visibility only, and their tooltip is
        # replaced by the forbid-by-object-tags one.
        visible, _suppression = sim.test_pie_menu_modifiers(affordance)
        if not visible:
            continue
        modifier_tooltip = sim.apply_forbid_by_object_tags_pie_menu_modifiers(aop)
        name = affordance.get_name(aop.target, item.context, **aop.interaction_parameters)
        tooltip = modifier_tooltip or item.result.tooltip
        enabled = bool(item.result) and not modifier_tooltip
        tip = None
        if tooltip is not None:
            tip = affordance.create_localized_string(tooltip, context=item.context, target=aop.target,
                                                     **aop.interaction_parameters)
        category = categories.get(item.category_key) if item.category_key else None
        root = _root(category)
        detail = None
        if category is not None and category is not root:
            detail = category._display_name(sim)
        elif tip is None:
            detail = affordance.get_display_tooltip(context=item.context, target=aop.target,
                                                    **aop.interaction_parameters)
        entry = _Entry(aop, name, enabled, tip, detail)
        if root is None:
            direct.append(entry)
            continue
        if root not in groups:
            groups[root] = []
            order.append(root)
        groups[root].append(entry)

    def priority(root):
        value = getattr(root, '_display_priority', 0)
        return value if isinstance(value, (int, float)) else 0
    order.sort(key=priority)                  # stable: equal priorities keep the phone's order
    return _PhoneList(sim.sim_id, [(root._display_name(sim), groups[root]) for root in order], direct)


def _phone_refused(sim):
    """The phone's own disable tests (with EA's reason) and the full
    queue, as interactions.phone_choices checks them. True when refused."""
    from event_testing.resolver import SingleSimResolver
    from sims.phone_tuning import PhoneTuning
    import tyjokr_a11y_native as native
    resolver = SingleSimResolver(sim.sim_info)
    for phone_test in PhoneTuning.DISABLE_PHONE_TESTS:
        if resolver(phone_test.test):
            _say('phone unavailable')
            native.show_reason(phone_test.tooltip, sim)
            return True
    if sim.queue is not None and not sim.queue.can_queue_visible_interaction():
        _say('action queue full')
        return True
    return False


def _current_sim(phone_list):
    """The active Sim and client, only while Simplified menus are on and
    the list still belongs to that Sim; otherwise says why and gives None."""
    import services
    if not simplified():
        _say('action unavailable')
        return None, None
    sim = services.get_active_sim()
    client = services.client_manager().get_first_client()
    if sim is None or client is None or sim.sim_id != phone_list.sim_id:
        _say('sim unavailable')
        return None, None
    return sim, client


def open_list():
    """Simulation pump or a command callback: the phone list for the
    active Sim, or the phone's own reason why there is none."""
    import services
    sim = services.get_active_sim()
    client = services.client_manager().get_first_client()
    if sim is None or client is None:
        _say('load a household first')
        return False
    try:
        if _phone_refused(sim):
            return False
        phone_list = _collect(sim, client)
    except Exception as ex:
        speech.log_line('phone: list unavailable ({!r})'.format(ex))
        _say('action unavailable')
        return False
    if not phone_list.groups and not phone_list.direct:
        _say('phone empty')
        return False
    speech.log_line('phone: list for sim {}: {} categories, {} other actions'.format(
        sim.sim_id, len(phone_list.groups), len(phone_list.direct)))
    return _show_top(phone_list)


def _row(option_id, name, detail, tag, enabled=True, tip=None):
    from ui.ui_dialog_picker import ObjectPickerRow
    return ObjectPickerRow(option_id=option_id, name=name, row_description=detail,
                           row_tooltip=(lambda *_, text=tip: text) if tip is not None else None,
                           icon=None, icon_info=_icon(), tag=tag, is_selected=False,
                           is_enable=enabled)


def _icon():
    try:
        import services
        from distributor.shared_messages import IconInfoData
        sim = services.get_active_sim()
        if sim is not None:
            return IconInfoData(obj_instance=sim)
    except Exception:
        pass
    return None


def _open(phone_list, title, text, rows):
    """One phone window at a time; its reply goes to the pump. title: None
    for the phone itself, or a category's game string."""
    global _list_id, _list
    import tyjokr_a11y_menu as menu
    menu._cancel_dialog(_list_id)
    _list_id = None
    dialog = menu._picker(lang.t('phone'), lang.t(text), localized_title=title)
    if dialog is None:
        _say('load a household first')
        return False
    for row in rows:
        dialog.add_row(row)

    def picked(reply, owner=phone_list):
        global _list_id
        if reply.dialog_id != _list_id or _list is not owner:
            return
        _list_id = None
        if not reply.accepted:
            return
        try:
            tags = list(reply.get_result_tags())
        except Exception:
            tags = []
        if len(tags) != 1:
            return
        if tags[0][0] in ('group', 'back'):
            try:
                import tyjokr_a11y_keys as keys
                keys.hold_scanner_resume()      # the next phone window follows
            except Exception:
                pass
        import tyjokr_a11y_pump as pump
        if not pump.post(_chosen, owner, tags[0]):
            _say('action unavailable')

    dialog.add_listener(picked)
    _list = phone_list
    try:
        import tyjokr_a11y_keys as keys
        keys.fence_opening_input()
    except Exception:
        pass
    dialog.show_dialog()
    _list_id = dialog.dialog_id
    return True


def _entry_rows(entries, start):
    return [_row(start + index, entry.name, entry.detail, ('do', entry), entry.enabled, entry.tip)
            for index, entry in enumerate(entries)]


def _show_top(phone_list):
    import tyjokr_a11y_menu as menu
    rows = []
    for index, (label, entries) in enumerate(phone_list.groups):
        term = 'phone group count one' if len(entries) == 1 else 'phone group count'
        count = menu._raw(lang.t(term).format(len(entries)))
        rows.append(_row(index, label, count, ('group', index)))
    rows.extend(_entry_rows(phone_list.direct, len(rows)))
    return _open(phone_list, None, 'phone list instructions', rows)


def _show_group(phone_list, index):
    import tyjokr_a11y_menu as menu
    label, entries = phone_list.groups[index]
    rows = [_row(0, menu._raw(lang.t('back to phone')), None, ('back',))]
    rows.extend(_entry_rows(entries, 1))
    return _open(phone_list, label, 'phone group instructions', rows)


def _chosen(phone_list, tag):
    """Pump, after EA has finished with the window. The setting and the
    Sim are checked again: either can change while a window is open."""
    global _list
    if _list is not phone_list:
        return False
    sim, _client = _current_sim(phone_list)
    if sim is None:
        _list = None
        return False
    kind = tag[0]
    if kind == 'group':
        return _show_group(phone_list, tag[1])
    if kind == 'back':
        return _show_top(phone_list)
    if kind == 'do':
        return _run(phone_list, tag[1])
    return False


def _run(phone_list, entry):
    """The chosen phone action, as the phone runs it (ChoiceMenu.select):
    the phone's own checks and the pie menu modifiers again (they can
    change while the window is open), a fresh context, EA's tests again,
    then execute."""
    import services
    import tyjokr_a11y_native as native
    global _list
    _list = None
    sim, client = _current_sim(phone_list)
    if sim is None:
        return False
    if not entry.enabled:
        _say('action unavailable')
        return False
    try:
        if _phone_refused(sim):
            return False
        visible, _suppression = sim.test_pie_menu_modifiers(entry.aop.affordance)
        forbidden = sim.apply_forbid_by_object_tags_pie_menu_modifiers(entry.aop)
    except Exception as ex:
        speech.log_line('phone: checks failed ({!r})'.format(ex))
        _say('action unavailable')
        return False
    if not visible or forbidden:
        _say('action unavailable')
        native.show_reason(forbidden, sim)
        return False
    try:
        import tyjokr_a11y_travel as travel
        if entry.affordance_id == travel._TRAVEL_AFFORDANCE and travel.enabled() and travel.simplified():
            if travel._show_front(sim):
                return True
    except Exception as ex:
        speech.log_line('phone: travel window unavailable ({!r})'.format(ex))
    if not _when_window_closed(_execute, phone_list, entry):
        _say('action unavailable')
        return False
    return True


def _when_window_closed(fn, *args):
    """Pump: run fn(*args) once the client reports that no menu or dialog
    owns the keys, meaning our phone window has really closed. A native
    screen from another movie sent sooner opens behind the closing window
    (live 2026-09-26: Purchase Gifts left a dim, empty modal). If a window
    still owns the keys after the wait, nothing runs and the player hears
    why. False when the pump is unavailable."""
    import time
    import tyjokr_a11y_pump as pump
    deadline = time.monotonic() + _CLOSE_WAIT

    def step():
        try:
            import tyjokr_a11y_keys as keys
            waiting = bool(keys._modal_active)
        except Exception:
            waiting = False
        if not waiting:
            return fn(*args)
        if time.monotonic() < deadline and pump.post(step):
            return None
        speech.log_line('phone: a window still owns the keys; action not run')
        _say('action unavailable')
        return False

    return pump.post(step)


def _execute(phone_list, entry):
    """Pump, once our window has closed: the Sim and the setting again, a
    fresh context, EA's tests again, then execute."""
    import tyjokr_a11y_native as native
    sim, client = _current_sim(phone_list)
    if sim is None:
        return False
    try:
        context = client.create_interaction_context(sim)
        result = entry.aop.test_and_execute(context)
    except Exception as ex:
        speech.log_line('phone: action failed ({!r})'.format(ex))
        _say('action unavailable')
        return False
    if not result:
        speech.log_line('phone: action refused: {}'.format(result))
        native.say_refusal(result, sim)
        return False
    speech.log_line('phone: ran {}'.format(entry.affordance_id))
    return True


@sims4.commands.Command('a11y.phonelist', command_type=sims4.commands.CommandType.Live)
def a11y_phonelist(_connection=None):
    return open_list()


@sims4.commands.Command('a11y.phone', command_type=sims4.commands.CommandType.Live)
def a11y_phone(_connection=None):
    return open_waiting()


def _install():
    from ui.ui_dialog_service import UiDialogService
    original = UiDialogService.dialog_show
    if getattr(original, '_a11y_phone_hook', False):
        return

    @functools.wraps(original)
    def dialog_show(self, dialog, phone_ring_type, *args, **kwargs):
        result = original(self, dialog, phone_ring_type, *args, **kwargs)
        try:
            if not self.is_phone_silenced and dialog.dialog_id in self._active_dialogs:
                _note(dialog, phone_ring_type)
        except Exception as ex:
            speech.log_line('phone: announcement failed: {!r}'.format(ex))
        return result

    dialog_show._a11y_phone_hook = True
    UiDialogService.dialog_show = dialog_show


try:
    _install()
except Exception as ex:
    speech.log_line('phone: hook unavailable: {!r}'.format(ex))
