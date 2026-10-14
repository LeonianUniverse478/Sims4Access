"""Common accessibility actions in one native, keyboard-navigable picker.

All callbacks run on the simulation thread. Rows retain real Sim ids and are
revalidated on selection; closing a window never selects a default action.
"""
import sims4.commands
import tyjokr_a11y_lang as lang
import tyjokr_a11y_menu as menu
import tyjokr_a11y_pump as pump
import tyjokr_a11y_speech as speech
import tyjokr_a11y_contacts as contacts

_dialog_id = None

# Native UI messages verified in SimInfoTrayMain. They retain EA's enabled
# checks and panel setup. The hub is closed before one of these is sent.
PANELS = (
    ('needs', 'A11yNeeds'),
    ('mood and moodlets', 'A11yMood'),
    ('wants and fears', 'A11yWants'),
    ('aspirations', 'OpenSimInfoAspirationPanel'),
    ('skills', 'OpenSimInfoSkillPanel'),
    ('career', 'OpenSimInfoCareerPanel'),
    ('inventory', 'OpenSimInfoInventoryPanel'),
    ('relationships', 'OpenSimInfoRelationshipPanel'),
    ('simology', 'OpenSimInfoSummaryPanel'),
    ('social groups', 'OpenSimInfoClubPanel'),
    ('owned businesses', 'OpenHouseholdInfoVenuePanel'),
    ('calendar', 'ShowCalendar'),
)


def _say(term):
    speech.speak(lang.t(term), explicit=True)


def _name(info):
    return ' '.join(p for p in (getattr(info, 'first_name', ''),
                                getattr(info, 'last_name', '')) if p)


def _client():
    import services
    return services.client_manager().get_first_client()


def _ui(message):
    import distributor.ops
    import distributor.system
    distributor.system.Distributor.instance().add_op_with_no_owner(
        distributor.ops.SendUIMessage(message))


def _window(title, description, rows):
    """Rows are (localized name, localized description, callback)."""
    global _dialog_id
    import services
    from ui.ui_dialog_picker import ObjectPickerRow
    menu._cancel_dialog(_dialog_id)
    _dialog_id = None
    dialog = menu._picker(lang.t(title), lang.t(description))
    if dialog is None:
        _say('load a household first')
        return False
    # Text-only item rows drew a broken-image placeholder in every row
    # (reported 2026-09-15). Object rows with the active Sim's own thumbnail
    # ask the client for a real icon, like the scanner window does.
    icon_info = None
    try:
        from distributor.shared_messages import IconInfoData
        sim = services.get_active_sim()
        if sim is not None:
            icon_info = IconInfoData(obj_instance=sim)
    except Exception:
        icon_info = None
    callbacks = {}
    for index, (name, detail, callback) in enumerate(rows):
        callbacks[index] = callback
        dialog.add_row(ObjectPickerRow(option_id=index, name=name,
                                         row_description=detail, row_tooltip=None,
                                         icon=None, icon_info=icon_info, tag=index,
                                         is_selected=False))

    def selected(reply):
        global _dialog_id
        if reply.dialog_id != _dialog_id:
            return
        _dialog_id = None
        if not reply.accepted:
            return
        tags = list(reply.get_result_tags())
        if len(tags) != 1 or tags[0] not in callbacks:
            return
        # Defer until EA finishes dismissing this dialog. Never fall back to
        # executing on an arbitrary caller thread if the pump has stopped.
        if not pump.post(callbacks[tags[0]]):
            _say('action unavailable')

    dialog.add_listener(selected)
    _dialog_id = dialog.dialog_id
    # The console Enter that opened this menu belongs to the console.
    # Retire queued activations before the new picker can receive them.
    import tyjokr_a11y_keys as keys
    keys.fence_opening_input()
    dialog.show_dialog()
    return True


def select_sim(sim_id):
    import services
    client = _client()
    info = services.sim_info_manager().get(sim_id)
    if client is None or info is None or info not in client.selectable_sims:
        _say('sim unavailable')
        return False
    if client.active_sim_info is not info and not client.set_active_sim_by_id(sim_id):
        _say('sim unavailable')
        return False
    speech.speak(_name(info), explicit=True)
    return True


def household():
    client = _client()
    if client is None:
        _say('load a household first')
        return False
    rows = []
    for info in client.selectable_sims:
        sim_id = info.sim_id
        detail = 'active sim' if info is client.active_sim_info else 'select this sim'
        rows.append((menu._raw(_name(info)), menu._raw(lang.t(detail)),
                     lambda ident=sim_id: select_sim(ident)))
    if not rows:
        _say('load a household first')
        return False
    return _window('household sims', 'choose a sim', rows)


def funds():
    import services
    household = services.active_household()
    if household is None:
        _say('load a household first')
        return False
    speech.speak('{}: {:,} {}'.format(lang.t('household funds'),
                                     household.funds.money, lang.t('simoleons')),
                 explicit=True)
    return True


def scanner_help():
    # Retain the callback name for callers of older hub versions.
    import tyjokr_a11y_shortcuts as shortcuts
    return shortcuts.speak()


def self_interactions():
    import services
    import tyjokr_a11y_scanner as scanner
    sim = services.get_active_sim()
    if sim is None or not scanner.enabled() or not scanner._scan():
        _say('action unavailable')
        return False
    if not scanner.select_item(scanner.SIMS, sim.id):
        _say('action unavailable')
        return False
    scanner._do_open()
    return True


def current_action():
    import services
    sim = services.get_active_sim()
    if sim is None:
        _say('load a household first')
        return False
    running = sim.queue.running
    # This is the same LocalizedString used by EA's interaction queue. Let
    # the native picker resolve all tokens in the player's language.
    name = running.get_name() if running is not None else menu._raw(lang.t('no current action'))
    return _window('current action', 'read current action',
                   [(name, menu._raw(_name(sim.sim_info)), open_hub)])


# Build cursor actions reachable without holding a chord. This window is a
# modal, so opening it retires the native cursor; a 'menu:' row asks the
# client to bring the cursor back where it was and perform that one action
# after the window has closed, under the cursor's own guards. On, off, undo,
# redo and the grid aim are the ordinary requests. Native feedback is what
# the player hears.
BUILD_ACTIONS = (
    ('build cursor on', 'on'), ('build cursor off', 'off'),
    ('move left', 'menu:left'), ('move right', 'menu:right'),
    ('move up', 'menu:up'), ('move down', 'menu:down'),
    ('fine step', 'menu:fine'), ('coarse step', 'menu:coarse'),
    ('center cursor', 'menu:center'), ('aim at grid point', 'grid'),
    ('select or place', 'menu:click'), ('cancel tool', 'menu:cancel'),
    ('rotate left', 'menu:rotateleft'), ('rotate right', 'menu:rotateright'),
    ('undo', 'undo'), ('redo', 'redo'),
    ('cursor status', 'menu:status'),
)


def _build_action(action):
    import tyjokr_a11y_build as build
    if action.startswith('menu:'):
        return build.request_menu(action[5:])
    return build.request(action)


def build_actions():
    import tyjokr_a11y_build as build
    if not build.controls_enabled():
        return build.refuse_disabled()
    if build._zone() is None:
        build._say('Enter Build mode first.', 'Najpierw włącz tryb budowania.')
        return False
    rows = []
    for label, action in BUILD_ACTIONS:
        rows.append((menu._raw(lang.t(label)), None,
                     lambda value=action: _build_action(value)))
    return _window('build actions', 'build actions instructions', rows)


def open_hub():
    import tyjokr_a11y_phone as phone
    import tyjokr_a11y_build as build
    import tyjokr_a11y_grid as grid
    rows = []
    for label, message in PANELS:
        rows.append((menu._raw(lang.t(label)), None,
                     lambda value=message: _ui(value)))
    # Build controls off: no dead rows; the settings menu row turns them on.
    build_rows = (('build cursor', build.toggle), ('build actions', build_actions),
                  ('read-only lot grid', grid.toggle)) if build.controls_enabled() else ()
    for label, callback in (
            (('current action', current_action), ('self interactions', self_interactions),
             ('household sims', household), ('household funds', funds),
             ('known contacts', contacts.open_contacts)) + build_rows +
            (('waiting call or text', phone.open_waiting),
             ('keyboard shortcuts', scanner_help),
             ('settings menu', menu._show_settings_window))):
        rows.append((menu._raw(lang.t(label)), None, callback))
    return _window('accessibility menu', 'accessibility menu instructions', rows)


@sims4.commands.Command('a11y.hub', command_type=sims4.commands.CommandType.Live)
def a11y_hub(_connection=None):
    return open_hub()


@sims4.commands.Command('a11y.buildmenu', command_type=sims4.commands.CommandType.Live)
def a11y_buildmenu(_connection=None):
    return build_actions()


@sims4.commands.Command('a11y.household', command_type=sims4.commands.CommandType.Live)
def a11y_household(_connection=None):
    return household()


@sims4.commands.Command('a11y.funds', command_type=sims4.commands.CommandType.Live)
def a11y_funds(_connection=None):
    return funds()
