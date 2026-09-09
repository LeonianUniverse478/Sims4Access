"""The scanner state machine.

Two modes. In world mode, left and right move between categories and up and
down move between objects in the current category. Activate opens the object's
interaction list, which switches to menu mode, where up and down move through
interactions and activate runs one.

Everything in here must run on the simulation thread. The keyboard poller
never calls into this module directly; it posts intents to a11yscan_pump.
"""
import a11yscan_actions as actions
import a11yscan_appearance as look
import a11yscan_build as build
import a11yscan_careers as careers
import a11yscan_cheats as cheats
import a11yscan_cas as cas
import a11yscan_dialogs as dialogs
import a11yscan_grid as grid
import a11yscan_log as logfile
import a11yscan_narrate as narrate
import a11yscan_probe as probe
import a11yscan_saves as saves
import a11yscan_settings as settings
import a11yscan_speech as speech
import a11yscan_stories as stories
import a11yscan_travel as travel
import a11yscan_world as world

MODE_WORLD = 'world'
MODE_MENU = 'menu'
MODE_DIALOG = 'dialog'
MODE_EVENTS = 'events'
MODE_RELATIONS = 'relations'
MODE_CATALOG = 'catalog'
MODE_CAS = 'cas'
MODE_STORIES = 'stories'
MODE_LOOK = 'look'
MODE_PICK = 'pick'
MODE_SETTINGS = 'settings'
MODE_JOBS = 'jobs'
MODE_TRAVEL = 'travel'
MODE_CHEATS = 'cheats'

_buckets = {}
_categories = []
_cat_index = 0
_item_index = 0

_mode = MODE_WORLD
_menu = []
_menu_index = 0
_menu_target = None
_menu_obj = None
_menu_stack = []

_catalog = {}
_catalog_categories = []
_catalog_cat = 0
_catalog_item = 0

_last_spoken = ''

# The picker shows saves with no lot loaded and households with one.
# How many of each shop row to buy, keyed by its position in the list,
# and which rows have actually been put in the basket.
_dialog_counts = {}
_dialog_cart = {}

_pick_kind = None
_pick_entries = []
_pick_index = 0

# Keeping the camera on the Sim, which is what centres positional audio.
_following = False
_followed_id = None


def zone_ready():
    """True once a lot is actually running.

    The mod is imported at game boot, so the keyboard answers on the main menu
    and on world-selection screens where no simulation exists. Almost nothing
    here works in that state, and failing one call at a time just produces a
    stream of 'Scanner error'. Better to check once and say what is wrong.
    """
    try:
        import services
        zone = services.current_zone()
        return zone is not None and zone.is_zone_running
    except Exception:
        return False


# What still makes sense with no lot loaded: nothing that touches the world.
_NO_ZONE_INTENTS = frozenset((
    'help', 'repeat', 'narrate', 'reload', 'cas_open', 'probe',
    'pick_open',
    # Answering "where am I" is most useful exactly where there is no world.
    'where',
))


def _say(text):
    global _last_spoken
    _last_spoken = text
    speech.speak(text)


def _current_category():
    if not _categories:
        return None
    return _categories[max(0, min(_cat_index, len(_categories) - 1))]


def _current_entries():
    category = _current_category()
    if category is None:
        return []
    return _buckets.get(category, [])


def current_entry():
    entries = _current_entries()
    if not entries:
        return None
    return entries[max(0, min(_item_index, len(entries) - 1))]


def rescan(announce=True):
    global _buckets, _categories, _cat_index, _item_index, _mode
    _mode = MODE_WORLD
    _buckets = world.scan()
    _categories = world.ordered_categories(_buckets)
    _cat_index = 0
    _item_index = 0
    if not _categories:
        if announce:
            _say('Nothing found. Are you in a loaded lot?')
        return False
    if announce:
        total = sum(len(v) for v in _buckets.values())
        _say('{} things in {} categories. {}, {}.'.format(
            total, len(_categories), _categories[0], len(_current_entries())))
    return True


def _ensure_scan():
    if not _categories:
        return rescan(announce=False)
    return True


def next_category(step=1):
    global _cat_index, _item_index
    if not _ensure_scan():
        _say('Nothing found.')
        return
    _cat_index = (_cat_index + step) % len(_categories)
    _item_index = 0
    entries = _current_entries()
    _say('{}, {} items. {}'.format(
        _current_category(), len(entries),
        entries[0].describe() if entries else 'empty'))


def prev_category():
    next_category(-1)


def next_item(step=1):
    global _item_index
    if not _ensure_scan():
        _say('Nothing found.')
        return
    entries = _current_entries()
    if not entries:
        _say('{} is empty.'.format(_current_category()))
        return
    _item_index = (_item_index + step) % len(entries)
    entry = entries[_item_index]
    _say('{}. {} of {}.'.format(entry.describe(), _item_index + 1, len(entries)))


def prev_item():
    next_item(-1)


def _next_menu(step=1):
    global _menu_index
    if not _menu:
        _say('No interactions.')
        return
    _menu_index = (_menu_index + step) % len(_menu)
    item = _menu[_menu_index]
    items = getattr(item, 'items', None)
    if items:
        _say('{}, category, {} inside. {} of {}.'.format(
            item.label, len(items), _menu_index + 1, len(_menu)))
    else:
        _say('{}. {} of {}.'.format(
            item.label, _menu_index + 1, len(_menu)))


def _resolve_target(entry):
    """Contacts are SimInfos; find their live Sim if they have one."""
    if entry.kind != 'contact':
        return entry.obj
    info = entry.obj
    for getter in (lambda: info.get_sim_instance(),
                   lambda: info.get_sim_instance(allow_hidden_flags=-1),
                   lambda: _sim_from_manager(info)):
        try:
            resolved = getter()
            if resolved is not None:
                return resolved
        except Exception:
            continue
    return None


def _sim_from_manager(info):
    """Last resort: look the Sim up by id among instanced objects."""
    import services
    sim_id = None
    for attr in ('sim_id', 'id'):
        sim_id = getattr(info, attr, None)
        if sim_id:
            break
    if not sim_id:
        return None
    try:
        return services.object_manager().get(sim_id)
    except Exception:
        return None


def _open_menu():
    global _mode, _menu, _menu_index, _menu_target, _menu_obj
    entry = current_entry()
    if entry is None:
        _say('Nothing focused.')
        return
    _menu_index = 0
    _menu_target = entry
    _menu_obj = None
    del _menu_stack[:]
    note = ''

    if entry.kind == 'phone':
        _menu = actions.phone_choices()
        _menu_obj = entry.obj
    else:
        target = _resolve_target(entry)
        if entry.kind == 'contact':
            # If they are actually here, their normal interactions are what you
            # want: the relationship panel offers phone socials, and the game
            # rightly refuses to let you phone someone standing next to you.
            if target is not None:
                _menu_obj = target
                _menu = actions.merged_choices(target)
                if not _menu:
                    _menu_obj = entry.obj
                    _menu = actions.relation_panel_choices(entry.obj)
                    note = ' remote options,'
            else:
                _menu_obj = entry.obj
                _menu = actions.relation_panel_choices(entry.obj)
                note = ' not nearby,'
            if not _menu:
                _menu = actions.phone_choices()
                _menu_obj = world.active_sim()
                note = ' phone options,'
        elif target is not None:
            _menu_obj = target
            _menu = (actions.merged_choices(target)
                     if getattr(target, 'is_sim', False)
                     else actions.choices_for(target))
        else:
            _menu = []
            _say('{} is not available.'.format(entry.name))
            return

    if not _menu:
        _say('{}: no interactions available.'.format(entry.name))
        return

    # Present the list the way the pie menu does: grouped into categories.
    try:
        _menu = actions.group_by_category(_menu)
    except Exception as ex:
        logfile.write('grouping failed ({!r})'.format(ex))

    _mode = MODE_MENU
    logfile.write('menu for {!r}: {} entries, source={}'.format(
        entry.name, len(_menu), actions.last_source()))
    try:
        actions.probe_mixers(_menu_obj)
    except Exception as ex:
        logfile.write('mixer probe failed ({!r})'.format(ex))
    warning = ''
    if actions.last_source() == actions.SOURCE_STATIC:
        warning = ' unfiltered,'
    _say('{}:{}{} {} interactions. {}.'.format(
        entry.name, note, warning, len(_menu), _menu[0].label))


def _activate_menu():
    global _mode, _menu, _menu_index
    if not _menu or _menu_target is None:
        _say('Nothing to run.')
        return
    picked = _menu[max(0, min(_menu_index, len(_menu) - 1))]
    # A category opens into its interactions rather than running.
    items = getattr(picked, 'items', None)
    if items is None:
        items = actions.sub_choices(picked, _menu_obj) or None
    if items:
        _menu_stack.append((list(_menu), _menu_index, picked.label))
        _menu = list(items)
        _menu_index = 0
        _say('{}, {} options. {}.'.format(
            picked.label, len(items), items[0].label))
        return
    choice = _menu[max(0, min(_menu_index, len(_menu) - 1))]
    logfile.write('player chose {!r} on {!r} (kind={})'.format(
        choice.label, _menu_target.name, _menu_target.kind))
    ok = actions.run(choice, _menu_obj if _menu_obj is not None else _menu_target.obj)
    _mode = MODE_WORLD
    if ok:
        logfile.ok('{} on {}'.format(choice.label, _menu_target.name))
        _say('{} on {}.'.format(choice.label, _menu_target.name))
    else:
        logfile.fail('{} on {}'.format(choice.label, _menu_target.name))
        _say('{} failed on {}.'.format(choice.label, _menu_target.name))


def back():
    global _mode, _menu, _menu_index
    # The full-screen modes own backspace outright: there is no menu stack to
    # unwind behind them, and falling through to world mode would leave the
    # mode set but unreachable, which is how the catalog used to get stuck.
    if _mode == MODE_CHEATS:
        cheats_close()
        return
    if _mode == MODE_TRAVEL:
        travel_close()
        return
    if _mode == MODE_JOBS:
        jobs_close()
        return
    if _mode == MODE_SETTINGS:
        settings_close()
        return
    if _mode == MODE_PICK:
        pick_close()
        return
    if _mode == MODE_LOOK:
        look_close()
        return
    if _mode == MODE_STORIES:
        stories_close()
        return
    if _mode == MODE_CAS:
        cas_close()
        return
    if _mode == MODE_CATALOG:
        catalog_close()
        return
    if _mode == MODE_MENU and _menu_stack:
        _menu, _menu_index, label = _menu_stack.pop()
        _say('Back to {}. {}.'.format(
            _menu_target.name if _menu_target else 'menu',
            _menu[_menu_index].label if _menu else 'empty'))
        return
    if _mode == MODE_DIALOG:
        _mode = MODE_WORLD
        _say('Left the dialog. It is still open; Ctrl Alt D to return.')
    elif _mode == MODE_MENU:
        _mode = MODE_WORLD
        entry = current_entry()
        _say('Closed. {}'.format(entry.name if entry else 'nothing focused'))
    else:
        _say('World mode.')


def repeat():
    _say(_last_spoken or 'Nothing to repeat.')


def where():
    """Speak the active Sim, the current focus, and where home is.

    With no lot running this becomes "what do I press now", because the
    screens before a lot are the ones with no other way to orient yourself.
    """
    if not zone_ready():
        import a11yscan_start as start
        _say(start.next_step())
        return
    sim = world.active_sim()
    name = world.sim_name(sim) if sim is not None else 'no active Sim'
    entry = current_entry()
    parts = [name]
    if entry is None:
        parts.append('Nothing focused')
    else:
        parts.append('Focused on {}'.format(
            entry.describe(include_category=True)))
    # Where home is, so a wrong home lot is visible BEFORE you travel rather
    # than after you arrive somewhere else.
    try:
        home_zone, _lot, _world, already = world.home_info()
        where_home = world.home_name()
        if already:
            parts.append('You are home')
        elif where_home:
            parts.append('Home is {}'.format(where_home))
        elif not home_zone:
            parts.append('Your household has no home lot')
    except Exception as ex:
        logfile.write('where: could not read home ({!r})'.format(ex))
    _say('. '.join(parts) + '.')


_dialog_index = 0


def on_dialog_shown(dialog):
    """Called by the dialog hook the instant a pop-up appears."""
    global _mode, _dialog_index
    try:
        items = dialogs.options(dialog)
        # Which branch this takes decides whether the pop-up is reachable at
        # all, and until now it left no trace either way - so a dialog that
        # was never announced looked exactly like one that was.
        logfile.write('dialog: {} offers {} option(s): {}'.format(
            type(dialog).__name__, len(items),
            '; '.join(item[0] for item in items[:6])[:220]))
        if not items:
            logfile.write('dialog: nothing to offer, not announcing it')
            return
        # Read-only handling is ONLY for true notifications. Anything with a
        # real choice - an incoming call's answer/decline - must stay
        # actionable, or it cannot be responded to at all.
        is_notification = 'notification' in type(dialog).__name__.lower()
        if is_notification and len(items) <= 1:
            logfile.write('dialog: read-only notification, not entering '
                          'dialog mode')
            speech.speak(dialogs.describe(dialog), interrupt=False)
            return
        _mode = MODE_DIALOG
        _dialog_index = 0
        logfile.write('dialog: entered dialog mode for {}'.format(
            type(dialog).__name__))
        _say('{} Arrows to choose, enter to confirm.'.format(
            dialogs.describe(dialog)))
    except Exception as ex:
        speech.log('dialog announce failed ({!r})'.format(ex))


def _next_dialog(step=1):
    global _dialog_index
    dialog = dialogs.current()
    items = dialogs.options(dialog)
    if not items:
        _say('No dialog.')
        return
    _dialog_index = (_dialog_index + step) % len(items)
    # _dialog_say adds the quantity and running total in a shop, and reads as
    # a plain option everywhere else.
    _say(_dialog_say(_dialog_index, items))


def _dialog_count(index):
    return _dialog_counts.get(index, 1)


def _cart_total():
    """(lines, simoleons) currently in the basket."""
    total = 0
    for def_id, count in _dialog_cart.values():
        price = dialogs.definition_price(def_id)
        if price:
            total += price * count
    return len(_dialog_cart), total


def _dialog_say(index, items):
    """One shop row, with what it costs for the quantity chosen."""
    label = items[index][0]
    dialog = dialogs.current()
    if not dialogs.is_purchase_picker(dialog):
        return '{}. {} of {}.'.format(label, index + 1, len(items))
    row = items[index][2] if items[index][1] == 'row' else None
    def_id = dialogs.row_def_id(row) if row is not None else None
    if def_id is None:
        # Confirm and cancel are buttons, not merchandise - announcing
        # "quantity 1" on the till was pure confusion.
        return '{}. {} of {}.'.format(label, index + 1, len(items))
    count = _dialog_count(index)
    price = dialogs.definition_price(def_id)
    parts = [label, 'quantity {}'.format(count)]
    if price:
        # The running total is the point: you should know what you are about
        # to spend before you commit, not after.
        parts.append('{} simoleons'.format(price * count))
    if index in _dialog_cart:
        parts.append('in your basket')
    parts.append('{} of {}'.format(index + 1, len(items)))
    return '. '.join(parts)


def dialog_quantity(step):
    """Left and right change how many you are buying."""
    items = dialogs.options(dialogs.current())
    if not items:
        _say('No dialog.')
        return
    index = max(0, min(_dialog_index, len(items) - 1))
    if not dialogs.is_purchase_picker(dialogs.current()):
        _next_dialog(step)
        return
    if items[index][1] != 'row' or dialogs.row_def_id(items[index][2]) is None:
        # Nothing to count on a button; move through the list instead.
        _next_dialog(step)
        return
    count = max(1, min(99, _dialog_count(index) + step))
    _dialog_counts[index] = count
    _say(_dialog_say(index, items))


def _activate_dialog():
    global _mode
    dialog = dialogs.current()
    items = dialogs.options(dialog)
    if not items:
        _say('No dialog.')
        return
    index = max(0, min(_dialog_index, len(items) - 1))
    label = items[index][0]
    count = _dialog_count(index)
    if dialogs.is_purchase_picker(dialog):
        kind = items[index][1]
        if kind == 'row':
            # Adding, not buying: a shop is a basket, and closing it on the
            # first Enter made it impossible to buy two different things.
            row = items[index][2]
            def_id = dialogs.row_def_id(row)
            if not def_id:
                _say('That is not something you can buy.')
                return
            if index in _dialog_cart and _dialog_cart[index][1] == count:
                del _dialog_cart[index]
                lines, total = _cart_total()
                _say('Took {} out of your basket. {} left, {} simoleons.'
                     .format(label, lines, total))
                return
            _dialog_cart[index] = (def_id, count)
            lines, total = _cart_total()
            _say('Added {} {}. Basket: {} of them, {} simoleons. '
                 'Go to confirm to buy.'.format(count, label, lines, total))
            return
        # Anything that is not a row is the confirm or cancel button.
        lines, total = _cart_total()
        if lines:
            # We buy this ourselves rather than answering the picker. Answering
            # it only records the basket against the interaction; the money
            # never moved, measured either side of the response. Doing it here
            # takes the money and hands over the goods, which is what a shop is.
            bought = []
            failed = []
            for def_id, count in _dialog_cart.values():
                ok, text = build.buy_into_inventory(def_id, count)
                (bought if ok else failed).append(text)
            _dialog_counts.clear()
            _dialog_cart.clear()
            # Close the shop without buying again through its own flow.
            dialogs.dismiss(dialog)
            _mode = MODE_WORLD
            dialogs.clear()
            rescan(announce=False)
            if bought and not failed:
                _say('Bought {}. Control Alt I for your inventory.'.format(
                    ', '.join(bought)))
            elif bought:
                _say('Bought {}. But {}'.format(', '.join(bought),
                                                ' '.join(failed)))
            else:
                _say(' '.join(failed) or 'Could not buy anything.')
            return
        # Nothing in the basket: let the button do whatever it normally does.

    # An editable field is not a button: typing into it must not answer the
    # dialog or leave dialog mode, or the pop-up closes the moment you try to
    # fill it in.
    if dialogs.is_text_field(dialog, index):
        _say(dialogs.begin_edit(dialog, index))
        return

    # On the map, enter chooses a destination and stops there - the game's own
    # Confirm button is what travels. Doing both in one press is what left the
    # map screen open: the client never saw the two-step it draws its panel
    # around.
    if dialogs.selects_before_confirming(dialog, index):
        _say(dialogs.select_row(dialog, index))
        return

    if dialogs.choose(dialog, index):
        route = dialogs.last_route() or ''
        _mode = MODE_WORLD
        dialogs.clear()
        # Do not claim success for a route the game never confirmed.
        if 'could not verify' in route:
            _say('{} sent.'.format(label))
        else:
            _say('{} chosen.'.format(label))
    else:
        # Leaving dialog mode matters: being stuck in it with an undismissable
        # pop-up blocks the whole game.
        _mode = MODE_WORLD
        _say('Could not choose {}. {}. Ctrl alt X to force it closed.'
             .format(label, dialogs.last_error() or 'no route worked'))


def _respond_to_call(accept):
    """Answer or decline whatever is waiting, without navigating to it first.

    Our options() puts the accept button first and the decline last, so the
    ends of the list are the two answers a ringing phone needs.
    """
    global _mode
    dialog = dialogs.current()
    if dialog is None:
        _say('Nothing waiting.')
        return
    items = dialogs.options(dialog)
    if not items:
        _say('Nothing to answer.')
        return
    index = 0 if accept else len(items) - 1
    label = items[index][0]
    if dialogs.choose(dialog, index):
        _mode = MODE_WORLD
        dialogs.clear()
        _say('{}.'.format(label))
    else:
        _say('Could not {}. {}'.format(
            'answer' if accept else 'decline',
            dialogs.last_error() or 'no route worked'))


def answer_call():
    _respond_to_call(True)


def decline_call():
    _respond_to_call(False)


def dismiss_dialog():
    """Force the current pop-up closed. The escape hatch for anything we
    cannot answer properly, so gameplay is never blocked."""
    global _mode
    dialog = dialogs.current()
    _mode = MODE_WORLD
    if dialog is None:
        _say('No dialog open.')
        return
    if dialogs.dismiss(dialog):
        dialogs.clear()
        _say('Dialog closed.')
    else:
        _say('Could not close it. {}'.format(dialogs.last_error() or ''))


def focus_dialog():
    """Jump back into the current pop-up if one is open."""
    global _mode, _dialog_index
    dialog = dialogs.current()
    if dialog is None:
        _say('No dialog open.')
        return
    _mode = MODE_DIALOG
    _dialog_index = 0
    _say(dialogs.describe(dialog))


def reload_mod():
    """Reload the mod in place, so a new build can be tested without
    restarting the game."""
    import a11yscan_reload as reloader
    _say('Reloading.')
    _say(reloader.reload_all())


def _catalog_items():
    if not _catalog_categories:
        return []
    category = _catalog_categories[max(0, min(_catalog_cat,
                                              len(_catalog_categories) - 1))]
    return _catalog.get(category, [])


def catalog_open():
    """Browse the buy catalog: categories, then items with prices.

    Toggles, so the same key gets you out. Leaving build mode also closes it -
    otherwise the catalog kept the arrows captive in live mode and the only way
    out was reloading the mod.
    """
    global _catalog, _catalog_categories, _catalog_cat, _catalog_item, _mode
    if _mode == MODE_CATALOG:
        catalog_close()
        return
    _say('Loading catalog.')
    # Every name at once, rather than letting a new mod's furniture read out
    # as "object" until the background trickle catches up.
    try:
        import a11yscan_strings as strings
        strings.finish_now()
    except Exception as ex:
        logfile.write('catalog: string sweep failed ({!r})'.format(ex))
    _catalog = world.catalog()
    # Plain alphabetical, so a group's shelves sit together - "surfaces,
    # counters" next to "surfaces, desks" - and holding the category key walks
    # through them in an order you can predict. CATEGORY_ORDER is for the world
    # scanner, and it put "other" first here, which is exactly backwards.
    _catalog_categories = sorted(c for c in _catalog
                                 if c != world.OTHER and _catalog.get(c))
    if _catalog.get(world.OTHER):
        _catalog_categories.append(world.OTHER)
    if not _catalog_categories:
        _say('Catalog unavailable.')
        return
    _catalog_cat = 0
    _catalog_item = 0
    _mode = MODE_CATALOG
    items = _catalog_items()
    _say('Catalog. {} categories. {}, {} items. {}.'.format(
        len(_catalog_categories), _catalog_categories[0], len(items),
        items[0][0] if items else 'empty'))


def catalog_close(announce=True):
    global _mode
    if _mode == MODE_CATALOG:
        _mode = MODE_WORLD
    if announce:
        _say('Catalog closed.')


def leave_build_modes(announce=False):
    """Called when build mode ends: drop any build-only mode we are holding."""
    global _mode
    closed = []
    if _mode == MODE_CATALOG:
        _mode = MODE_WORLD
        closed.append('catalog')
    try:
        if grid.active():
            grid.leave()
            closed.append('grid')
    except Exception:
        pass
    if closed:
        logfile.write('left build modes: {}'.format(', '.join(closed)))
        if announce:
            _say('Back to live mode.')
    return closed


def _catalog_say_item():
    items = _catalog_items()
    if not items:
        _say('Empty category.')
        return
    index = max(0, min(_catalog_item, len(items) - 1))
    label, price, definition = items[index]
    # Say what it needs while you are choosing, not after you have paid.
    needs = None
    try:
        needs = build.placement_requirement(definition)
    except Exception:
        needs = None
    _say('{}, {} simoleons{}. {} of {}.'.format(
        label, price, ', needs {}'.format(needs) if needs else '',
        index + 1, len(items)))


def catalog_place():
    """Buy the selected item and place it at the grid cursor."""
    items = _catalog_items()
    if not items:
        _say('Nothing selected.')
        return
    label, price, definition = items[max(0, min(_catalog_item,
                                                len(items) - 1))]
    spot = grid.cursor()
    if spot is None:
        sim = world.active_sim()
        if sim is None:
            _say('No place to put it.')
            return
        try:
            spot = (sim.position, int(getattr(sim, 'level', 0) or 0),
                    sim.routing_surface)
        except Exception:
            _say('No place to put it.')
            return
    position, level, surface = spot
    spoken = build.place(definition, price, position, level, surface)
    # Follow the object. The game picks the exact spot, so the cursor should
    # end up where the thing actually is rather than where you aimed.
    landed = build.last_placed_position()
    try:
        if landed is not None:
            grid.focus_position(landed, level)
            spoken = '{} Cursor moved to it.'.format(spoken)
        else:
            grid.refresh()
    except Exception as ex:
        logfile.write('catalog: could not follow the object ({!r})'.format(ex))
    _say(spoken)


# Selling cannot be undone, so it takes two presses. A blind player gets no
# "are you sure" dialog to read, and a stray key should not cost furniture.
_sell_pending = [None, 0.0]
SELL_CONFIRM_SECONDS = 6.0


def sell_focused():
    """Sell whatever the scanner is focused on. Press twice to confirm."""
    import time
    # The grid cursor comes first when the grid is open: standing on a tile
    # in build mode is the obvious way to point at a thing you want gone, and
    # it is not the same as what the world scanner has focused.
    obj = None
    name = None
    try:
        if grid.active():
            here = grid.objects_here()
            if here:
                name, obj = here[0]
    except Exception as ex:
        logfile.write('sell: could not read the grid tile ({!r})'.format(ex))
    if obj is None:
        entry = current_entry()
        obj = getattr(entry, 'obj', None) if entry is not None else None
        name = getattr(entry, 'name', None) if entry is not None else None
    if obj is None:
        _say('Nothing here to sell. Move the grid cursor onto it, or focus it '
             'with Control Alt arrows.')
        return
    now = time.monotonic()
    if (_sell_pending[0] is obj
            and now - _sell_pending[1] < SELL_CONFIRM_SECONDS):
        _sell_pending[0] = None
        _say(build.sell(obj))
        try:
            grid.refresh()
        except Exception:
            pass
        rescan()
        return
    _sell_pending[0] = obj
    _sell_pending[1] = now
    value = build.sale_value(obj)
    name = name or 'that'
    if value:
        _say('Sell {} for {:,} simoleons? Press Control Shift D again to '
             'confirm.'.format(name, value))
    else:
        _say('Delete {}? It is worth nothing. Press Control Shift D again to '
             'confirm.'.format(name))


def build_undo():
    _say(build.undo())


def catalog_next_item(step=1):
    global _catalog_item
    items = _catalog_items()
    if not items:
        _say('Empty category.')
        return
    _catalog_item = (_catalog_item + step) % len(items)
    _catalog_say_item()


def catalog_prev_item():
    catalog_next_item(-1)


def catalog_next_category(step=1):
    global _catalog_cat, _catalog_item
    if not _catalog_categories:
        return
    _catalog_cat = (_catalog_cat + step) % len(_catalog_categories)
    _catalog_item = 0
    items = _catalog_items()
    _say('{}, {} items. {}.'.format(
        _catalog_categories[_catalog_cat], len(items),
        items[0][0] if items else 'empty'))


def catalog_prev_category():
    catalog_next_category(-1)


def grid_toggle():
    """Enter or leave the tile grid. Read-only: it never moves anything."""
    _say(grid.leave() if grid.active() else grid.enter())


def grid_active():
    return grid.active()


def grid_north():
    _say(grid.move(0.0, 1.0))


def grid_south():
    _say(grid.move(0.0, -1.0))


def grid_east():
    _say(grid.move(1.0, 0.0))


def grid_west():
    _say(grid.move(-1.0, 0.0))


def grid_describe():
    _say(grid.describe(full=True))


def grid_up():
    _say(grid.up_level())


def grid_down():
    _say(grid.down_level())


def travel_menu():
    """Open the game's travel flow; both of its pickers are readable dialogs."""
    _say(world.travel_menu())


def go_home():
    """Travel home. The travel button is client-side UI, so this drives the
    same server command the button would."""
    _say(world.go_home())


def emotion():
    """Speak the current mood and, where the game knows it, why."""
    sim = world.active_sim()
    if sim is None:
        _say('No active Sim.')
        return
    mood, intensity, causes = world.emotion(sim)
    if not mood:
        _say('Emotion unavailable.')
        return
    head = mood
    if intensity:
        head = '{}, level {}'.format(mood, intensity)

    driving = [c for c in causes if c[2]]
    others = [c for c in causes if not c[2]]
    parts = []
    for label, weight, _drives, reason in driving[:4]:
        piece = '{} plus {}'.format(label, weight)
        if reason:
            piece = '{} ({})'.format(piece, reason)
        parts.append(piece)
    if not parts:
        for label, weight, _drives, reason in others[:3]:
            parts.append('{} plus {}'.format(label, weight))

    if parts:
        _say('{}. Because: {}.'.format(head, '; '.join(parts)))
    else:
        _say('{}. No specific cause.'.format(head))


def aspiration():
    """Read out the aspiration and the goals it still wants."""
    import a11yscan_cheats as cheats
    _say(cheats.aspiration_report())


def wants():
    sim = world.active_sim()
    if sim is None:
        _say('No active Sim.')
        return
    items = world.wants(sim)
    if not items:
        _say('No wants right now.')
        return
    _say('{} wants: {}'.format(world.sim_name(sim), '; '.join(items[:4])))


def toggle_narration():
    """Turn running-action announcements on or off."""
    narrate.set_enabled(not narrate.enabled())
    _say('Action narration {}.'.format(narrate.status()))


def _jump(category, label):
    """Jump straight to one category without cycling through the others.

    Always rescans. Inventory, phone and contacts all change as you play - an
    item bought a moment ago is not in the cached scan, which reads as the
    purchase having failed when it actually worked.
    """
    global _cat_index, _item_index, _mode
    if not rescan(announce=False):
        _say('Nothing found.')
        return
    if category not in _categories:
        _say('No {} available.'.format(label))
        return
    _mode = MODE_WORLD
    _cat_index = _categories.index(category)
    _item_index = 0
    entries = _current_entries()
    if not entries:
        _say('{} is empty.'.format(label))
        return
    # Read a short list out in full. Announcing only the first item meant a
    # purchase that had arrived was inaudible unless you arrowed all the way
    # down to it - "did my shopping turn up" should be answerable in one press.
    if len(entries) <= 12:
        names = []
        for entry in entries:
            text = entry.name
            detail = getattr(entry, 'detail', None)
            names.append('{}, {}'.format(text, detail) if detail else text)
        _say('{}, {} items. {}.'.format(label, len(entries), '. '.join(names)))
        return
    _say('{}, {} items. {}. Up and down for the rest.'.format(
        label, len(entries), entries[0].describe()))


def focus_phone():
    _jump(world.PHONE, 'phone')


def focus_inventory():
    _jump(world.INVENTORY, 'inventory')


def focus_contacts():
    _jump(world.CONTACTS, 'relationships')


def focus_self():
    """Jump the scanner and the camera to your own Sim, no clicking needed."""
    global _cat_index, _item_index, _mode
    # Always rescan: after a death the cached scan still holds the Sim who
    # died, and "focus me" is exactly when a stale roster misleads most.
    if not rescan(announce=False):
        _say('Nothing found.')
        return
    _mode = MODE_WORLD
    if world.YOURSELF in _categories:
        _cat_index = _categories.index(world.YOURSELF)
        _item_index = 0
    sim = world.active_sim()
    # Say exactly who the game considers active, by id as well as name: a
    # wrong name on the right Sim and the right name on the wrong Sim read
    # identically out loud.
    try:
        info = getattr(sim, 'sim_info', None) or sim
        logfile.write('focus: active Sim is {!r} (id={})'.format(
            world.sim_name(sim) if sim is not None else None,
            getattr(info, 'id', '?')))
    except Exception as ex:
        logfile.write('focus: could not identify the active Sim ({!r})'.format(ex))
    client = None
    try:
        import services
        client = services.client_manager().get_first_client()
    except Exception as ex:
        logfile.write('camera: no client ({!r})'.format(ex))

    # focus_on_sim(sim, follow, client) takes THREE arguments. Calling it with
    # two raised, the exception was swallowed, and the camera simply never
    # moved. follow=True is what makes it track him afterwards.
    # follow_mode is an ENUM on the FocusCamera op (NONE / FOLLOW_ROUTE), not a
    # boolean. Passing True built a malformed op that the client discarded
    # without complaint, which is why every attempt "succeeded" and the camera
    # never moved.
    follow_mode = None
    try:
        from protocolbuffers import DistributorOps_pb2
        for holder in (getattr(DistributorOps_pb2, 'FocusCamera', None),
                       DistributorOps_pb2):
            if holder is None:
                continue
            follow_mode = getattr(holder, 'FOLLOW_ROUTE', None)
            if follow_mode is not None:
                break
    except Exception as ex:
        logfile.write('camera: follow enum lookup failed ({!r})'.format(ex))
    if follow_mode is None:
        follow_mode = 1
    logfile.write('camera: follow_mode={!r}'.format(follow_mode))

    moved = False
    try:
        import camera
        for name, call in (
                ('focus_on_sim(sim, FOLLOW_ROUTE, client)',
                 lambda: camera.focus_on_sim(sim, follow_mode, client)),
                ('focus_on_sim(sim, 0, client)',
                 lambda: camera.focus_on_sim(sim, 0, client)),
                ('focus_on_sim(sim, follow)',
                 lambda: camera.focus_on_sim(sim, follow_mode)),
                ('focus_on_sim(sim)', lambda: camera.focus_on_sim(sim))):
            try:
                call()
                logfile.write('camera: moved via {}'.format(name))
                moved = True
                break
            except TypeError as ex:
                logfile.write('camera: {} wrong signature ({!r})'.format(name, ex))
            except Exception as ex:
                logfile.write('camera: {} raised {!r}'.format(name, ex))
    except Exception as ex:
        logfile.write('camera module unavailable ({!r})'.format(ex))
    # Nothing else is sent after the focus op. focus_on_lot used to run here
    # to centre the lot, and FocusCameraOnLot simply overrode the FocusCamera
    # we had just sent - so the camera landed on the middle of the lot, near
    # the Sim but never on her. The hunt for a "focus camera" relationship-panel
    # interaction went with it: it never once found one, and it cost 36 failing
    # interaction tests on every press.
    moved = moved or False

    try:
        import services
        client = services.client_manager().get_first_client()
        if client is not None and getattr(client, 'active_sim', None) is not sim:
            client.set_active_sim(sim)
    except Exception as ex:
        speech.log('set_active_sim failed ({!r})'.format(ex))
    parts = [world.sim_name(sim) if sim is not None else 'no active Sim', 'focused']
    action = world.current_action(sim) if sim is not None else None
    if action:
        parts.append('currently ' + action)
    # The time of day is otherwise only guessable from the ambient sound.
    clock = world.game_time()
    if clock:
        parts.append('it is {}'.format(clock))
    _say('{}. Enter for options.'.format(', '.join(parts)))


def needs():
    sim = world.active_sim()
    if sim is None:
        _say('No active Sim.')
        return
    values = world.motives(sim)
    if not values:
        _say('Needs unavailable.')
        return
    spoken = ', '.join('{} {:.0f} percent'.format(name, pct)
                       for name, pct in values[:6])
    _say('{}: {}'.format(world.sim_name(sim), spoken))


def doing():
    sim = world.active_sim()
    if sim is None:
        _say('No active Sim.')
        return
    action = world.current_action(sim)
    _say('{} is {}'.format(world.sim_name(sim),
                           action or 'not doing anything in particular'))


def help_text():
    _say('Control alt, arrows to browse, enter to open and run, '
         'backspace to close, D for the open dialog, F for your Sim, '
         'A for current action, P phone, I inventory, C contacts, T narration, '
         'R to repeat, S to rescan, W for where am I, '
         'B for the tile grid, K for the buy catalog, M to create a Sim, '
         'number keys one to eight to play a different household Sim, '
         'O to choose a save or household to play, '
         'Control Shift N for needs, '
         'Control Shift D to sell what you are focused on, '
         'Control Shift O for your aspiration and its goals, '
         'Control Shift M for your money, '
         'Control Shift F to keep the camera on your Sim, '
         'Control Shift T to travel without the map screen, '
         'Control Shift H to move house, '
         'Control Shift P to plan an event, '
         'Control Shift Enter to centre the camera on the lot, '
         'Control Shift G for game settings, '
         'J to choose a job, '
         'and V for cheats.')


def cas_open():
    """Open the keyboard Sim builder. Toggles, like the catalog does."""
    global _mode
    if _mode == MODE_CAS:
        cas_close()
        return
    if not zone_ready():
        _say('Create a Sim needs a lot loaded. Load any household first, '
             'then press Control Alt M.')
        logfile.write('cas: refused, no zone running')
        return
    text = cas.open_builder()
    _mode = MODE_CAS
    _say(text)


def cas_close(announce=True):
    global _mode
    if _mode == MODE_CAS:
        _mode = MODE_WORLD
        cas.close_builder(announce=False)
        if announce:
            _say('Create a Sim closed.')


def cas_next_field(step=1):
    _say(cas.next_field(step))


def cas_change(step=1):
    _say(cas.change_value(step))


def cas_activate():
    text = cas.activate()
    # create() closes the builder itself once the Sim exists.
    if not cas.active():
        cas_close(announce=False)
    _say(text)


def stories_open():
    """Answer the game's own CAS questions, then come back to the builder."""
    global _mode
    if not zone_ready():
        _say('The questionnaire needs a lot loaded.')
        return
    _say('Loading the questions.')
    count = stories.load()
    if not count:
        _say('Could not load the questions. The log has the reason.')
        return
    _mode = MODE_STORIES
    _say('{} questions. Up and down to move between them, left and right for '
         'the answers, enter to choose. Backspace to stop. {}'.format(
             count, stories.describe()))


def stories_close(announce=True):
    global _mode
    if _mode == MODE_STORIES:
        _mode = MODE_CAS if cas.active() else MODE_WORLD
        if announce:
            _say('Questionnaire closed. {}'.format(
                cas.describe() if cas.active() else 'World mode.'))


def stories_finish():
    """Score the answers and carry them into the builder."""
    global _mode
    traits, aspiration = stories.results()
    text = stories.results_text(traits, aspiration)
    if cas.active():
        applied = cas.apply_results(traits, aspiration)
        # Announce what actually went in, not what merely scored: traits this
        # Sim cannot take are skipped over rather than filled.
        if applied:
            text = ('Your answers chose {}. Change any of them on the trait '
                    'and aspiration lines.'.format(', '.join(applied)))
    _mode = MODE_CAS if cas.active() else MODE_WORLD
    _say(text)


def stories_activate():
    result = stories.choose()
    if result is None:
        stories_finish()
        return
    _say(result)


def look_open():
    """Change how the selected Sim looks."""
    global _mode
    if _mode == MODE_LOOK:
        look_close()
        return
    if not zone_ready():
        _say('Changing a Sim needs a lot loaded.')
        return
    _say('Loading the choices.')
    text = look.open_editor()
    if look.active():
        _mode = MODE_LOOK
    _say(text)


def look_close(announce=True):
    global _mode
    if _mode == MODE_LOOK:
        _mode = MODE_WORLD
        text = look.close_editor()
        if announce:
            _say(text)


def look_randomize():
    _say(look.randomize())


def typing_active():
    """True while anything is collecting typed text.

    Not just the Sim builder any more: a dialog field uses the same keys, and
    the poller has to know to send letters here rather than treat them as
    commands.
    """
    if _mode == MODE_CAS and cas.typing() is not None:
        return True
    try:
        import a11yscan_typing as typing
        return typing.active()
    except Exception:
        return False


def type_key(intent):
    """A key pressed while typing."""
    try:
        import a11yscan_typing as typing
    except Exception:
        typing = None
    if typing is not None and typing.active():
        if intent == 'type_back':
            _say(typing.backspace() or '')
        elif intent == 'type_done':
            _say(typing.accept() or '')
        elif intent == 'type_cancel':
            _say(typing.cancel() or '')
        elif intent.startswith('type_char_'):
            char = intent[len('type_char_'):]
            if char == 'SPACE':
                char = ' '
            spoken = typing.character(char)
            if spoken:
                _say(spoken)
        return
    if intent == 'type_back':
        _say(cas.type_backspace() or '')
        return
    if intent == 'type_done':
        _say(cas.type_accept() or '')
        return
    if intent == 'type_cancel':
        _say(cas.type_cancel() or '')
        return
    if intent.startswith('type_char_'):
        char = intent[len('type_char_'):]
        if char == 'SPACE':
            char = ' '
        spoken = cas.type_character(char)
        if spoken:
            _say(spoken)


def _send_focus(sim):
    """Point the camera at a Sim. Nothing else may be sent afterwards."""
    follow_mode = 1
    try:
        from protocolbuffers import DistributorOps_pb2
        for holder in (getattr(DistributorOps_pb2, 'FocusCamera', None),
                       DistributorOps_pb2):
            if holder is None:
                continue
            found = getattr(holder, 'FOLLOW_ROUTE', None)
            if found is not None:
                follow_mode = found
                break
    except Exception:
        follow_mode = 1
    try:
        import camera
        import services
        client = services.client_manager().get_first_client()
        camera.focus_on_sim(sim, follow_mode, client)
        return True
    except Exception as ex:
        logfile.write('camera: focus failed ({!r})'.format(ex))
        return False


def follow_toggle():
    """Keep the camera on your Sim as they move.

    The Sims 4 places sound in the world relative to the camera, so a camera
    sitting anywhere else means you hear your own Sim from across the room -
    which is the "something blocking us" effect. One focus op only aims the
    camera once; this keeps re-aiming it as they walk, so the audio stays
    centred on whatever they are doing.
    """
    global _following, _followed_id
    if _following:
        _following = False
        _followed_id = None
        logfile.write('camera: follow off')
        _say('No longer following your Sim.')
        return
    sim = world.active_sim()
    if sim is None:
        _say('No active Sim.')
        return
    _following = True
    _followed_id = getattr(sim, 'id', None)
    _send_focus(sim)
    logfile.write('camera: following {!r}'.format(world.sim_name(sim)))
    _say('Following {}. The camera will stay with them.'.format(
        world.sim_name(sim)))


def center_lot():
    """Put the camera in the middle of the lot.

    Following and centring cannot both be true, so this turns following off
    rather than leaving the two fighting over the camera every tick.
    """
    global _following, _followed_id
    was_following = _following
    if _following:
        _following = False
        _followed_id = None
        logfile.write('camera: follow off for centring')

    lot_id = None
    try:
        import services
        lot_id = services.active_lot_id()
    except Exception as ex:
        logfile.write('camera: no lot id ({!r})'.format(ex))

    # The game itself calls focus_on_lot with lerp_time only and lets lot_id
    # default to the current lot, so that shape is tried first.
    try:
        import camera
    except Exception as ex:
        logfile.fail('camera: module unavailable ({!r})'.format(ex))
        _say('Could not move the camera.')
        return
    attempts = [('focus_on_lot(lerp_time)',
                 lambda: camera.focus_on_lot(lerp_time=1.0))]
    if lot_id:
        attempts.append(('focus_on_lot(lot_id, lerp_time)',
                         lambda: camera.focus_on_lot(lot_id, 1.0)))
    attempts.append(('set_to_default', camera.set_to_default))
    for label, call in attempts:
        try:
            call()
        except Exception as ex:
            logfile.write('camera: {} raised {!r}'.format(label, ex))
            continue
        logfile.ok('camera: centred via {}'.format(label))
        _say('Centred on the lot. No longer following your Sim.'
             if was_following else 'Centred on the lot.')
        return
    logfile.fail('camera: could not centre on the lot')
    _say('Could not centre the camera. The log has the reason.')


def follow_tick():
    """Re-aim the camera while following. Called on the simulation thread."""
    global _followed_id
    if not _following:
        return
    try:
        sim = world.active_sim()
        if sim is None:
            return
        sim_id = getattr(sim, 'id', None)
        # Re-send regardless of whether they moved: the client drops focus
        # when other camera ops arrive, and re-aiming is cheap.
        _send_focus(sim)
        if sim_id != _followed_id:
            _followed_id = sim_id
            logfile.write('camera: now following {!r}'.format(
                world.sim_name(sim)))
    except Exception as ex:
        logfile.write('camera: follow tick failed ({!r})'.format(ex))


def funds():
    """How much money the household has."""
    amount = build.funds_available()
    if amount is None:
        _say('Could not read your money.')
        logfile.write('funds: unavailable')
        return
    name = None
    try:
        import services
        household = services.active_household()
        name = getattr(household, 'name', None)
    except Exception:
        name = None
    # Group the digits: NVDA reads 12,345 as a number, 12345 as digits.
    text = '{:,}'.format(int(amount))
    _say('{} has {} simoleons.'.format(name, text) if name
         else '{} simoleons.'.format(text))


def save_now():
    """Save the game from the keyboard.

    Everything the mod creates - a Sim, a household, a lot move - lives only in
    memory until the game is saved. A new Sim was lost exactly this way: made,
    announced as created, then discarded by a restart because nothing said to
    save.
    """
    try:
        from server_commands.persistence_commands import save_game
    except Exception as ex:
        logfile.fail('save: command unavailable ({!r})'.format(ex))
        _say('Could not save.')
        return
    connection = None
    try:
        import services
        client = services.client_manager().get_first_client()
        connection = getattr(client, 'id', None)
    except Exception:
        connection = None
    for label, call in (
            ('save_game(True, False, connection)',
             lambda: save_game(True, False, connection)),
            ('save_game(connection)', lambda: save_game(connection)),
            ('save_game()', lambda: save_game())):
        try:
            call()
            logfile.ok('save: requested via {}'.format(label))
            _say('Saving.')
            return
        except TypeError:
            continue
        except Exception as ex:
            logfile.fail('save: {} raised {!r}'.format(label, ex))
            break
    _say('Could not save. The log has the reason.')


def move_house_open():
    """Choose a lot to move your household onto.

    Not a map picker, so there is no screen to read or suppress - the game
    does this in Manage Worlds, which is client-side and out of reach. The
    move itself is a plain call, so the mod offers the list instead.
    """
    global _mode, _pick_kind, _pick_entries, _pick_index
    if _mode == MODE_PICK:
        pick_close()
        return
    if not zone_ready():
        _say('Moving house needs a lot loaded first.')
        return
    import a11yscan_lots as lots
    _say('Reading the lots.')
    # Moving in with someone comes first: it is a short list and it is the
    # thing you would have to open Manage Household for otherwise. The lots
    # follow, so one key covers both ways of changing where you live.
    _pick_entries = lots.move_in_candidates() + lots.move_targets()
    if not _pick_entries:
        _say('Nowhere to move to. The log has the reason.')
        return
    _pick_kind = 'move'
    _pick_index = 0
    _mode = MODE_PICK
    merges = sum(1 for e in _pick_entries if e.get('kind') == 'merge')
    _say('Move. {} ways to move in with someone here, then {} lots with the '
         'empty ones first. Up and down to browse, enter to choose, '
         'backspace to stop. {}'.format(
             merges, len(_pick_entries) - merges, _pick_say()))


def relations_open():
    """Every relationship, the way the panel would show them if it read."""
    global _mode
    import a11yscan_relations as relations
    if _mode == MODE_RELATIONS:
        relations_close()
        return
    if not zone_ready():
        _say('Relationships need a lot loaded first.')
        return
    text = relations.open_menu()
    if relations.active():
        _mode = MODE_RELATIONS
    _say(text)


def relations_close(announce=True):
    global _mode
    import a11yscan_relations as relations
    if _mode == MODE_RELATIONS:
        _mode = MODE_WORLD
    text = relations.close_menu()
    if announce:
        _say(text)


def relations_activate():
    """Enter reads the full profile and leaves the list where it was."""
    import a11yscan_relations as relations
    _say(relations.activate())


def events_open():
    """Plan a social event. The planner screen is client-side, so this is ours."""
    global _mode
    import a11yscan_events as events
    if _mode == MODE_EVENTS:
        events_close()
        return
    if not zone_ready():
        _say('Planning an event needs a lot loaded first.')
        return
    # An event already running is what you are asking about; the planner is
    # for when there is not one. The two cannot overlap, so no ambiguity.
    try:
        progress = events.live_report()
    except Exception as ex:
        logfile.write('events: live report failed ({!r})'.format(ex))
        progress = None
    if progress:
        _say(progress)
        return
    _say('Reading the events.')
    text = events.open_menu()
    if events.active():
        _mode = MODE_EVENTS
    _say(text)


def events_close(announce=True):
    global _mode
    import a11yscan_events as events
    if _mode == MODE_EVENTS:
        _mode = MODE_WORLD
    text = events.close_menu()
    if announce:
        _say(text)


def events_activate():
    """Enter in the event planner. Starting an event closes the menu; every
    other choice leaves it open so the rest of the plan can be made."""
    global _mode
    import a11yscan_events as events
    text = events.activate()
    if not events.active():
        _mode = MODE_WORLD
    _say(text)


def cheats_open():
    """Cheats as a menu, so nobody has to spell Major_Charisma."""
    global _mode
    if _mode == MODE_CHEATS:
        cheats_close()
        return
    if not zone_ready():
        _say('Cheats need a lot loaded.')
        return
    _say('Loading cheats.')
    text = cheats.open_menu()
    if cheats.active():
        _mode = MODE_CHEATS
    _say(text)


def cheats_close(announce=True):
    global _mode
    if _mode == MODE_CHEATS:
        _mode = MODE_WORLD
        text = cheats.close_menu()
        if announce:
            _say(text)


def travel_open():
    """Travel without opening the map screen."""
    global _mode
    if _mode == MODE_TRAVEL:
        travel_close()
        return
    if not zone_ready():
        _say('Travelling needs a lot loaded.')
        return
    _say('Loading places.')
    text = travel.open_menu()
    if travel.active():
        _mode = MODE_TRAVEL
    _say(text)


def travel_close(announce=True):
    global _mode
    if _mode == MODE_TRAVEL:
        _mode = MODE_WORLD
        text = travel.close_menu()
        if announce:
            _say(text)


def travel_go():
    global _mode
    text = travel.go()
    if not travel.active():
        _mode = MODE_WORLD
    _say(text)


def travel_activate():
    """Enter in the travel menu: bring a Sim, or go somewhere.

    Deliberately a function rather than a few lines inside dispatch. Assigning
    _mode there made it a local for the whole of dispatch, and every other
    intent that reads _mode - which is nearly all of them - died with
    UnboundLocalError before it could do anything.
    """
    global _mode
    text = travel.toggle_or_go()
    # Toggling a companion must NOT leave the menu; you are here to pick
    # several and then a place.
    if not travel.active():
        _mode = MODE_WORLD
    _say(text)


def jobs_open():
    """Pick a job. The game's own career screen is client-side and unreadable."""
    global _mode
    if _mode == MODE_JOBS:
        jobs_close()
        return
    if not zone_ready():
        _say('Choosing a job needs a lot loaded.')
        return
    _say('Loading the jobs.')
    text = careers.open_picker()
    if careers.active():
        _mode = MODE_JOBS
    _say(text)


def jobs_close(announce=True):
    global _mode
    if _mode == MODE_JOBS:
        _mode = MODE_WORLD
        text = careers.close_picker()
        if announce:
            _say(text)


def settings_open():
    """The gameplay half of the Options screen."""
    global _mode
    if _mode == MODE_SETTINGS:
        settings_close()
        return
    if not zone_ready():
        _say('Settings need a lot loaded.')
        return
    _mode = MODE_SETTINGS
    _say(settings.open_settings())


def settings_close(announce=True):
    global _mode
    if _mode == MODE_SETTINGS:
        _mode = MODE_WORLD
        text = settings.close_settings()
        if announce:
            _say(text)


def pick_open():
    """Choose what to play: a save on the main menu, a household in game.

    One key for one idea. Loading a save is a client action we cannot perform,
    but we can decide which save Continue opens, so the main-menu half sets
    that up and the in-game half switches household outright.
    """
    global _mode, _pick_kind, _pick_entries, _pick_index
    if _mode == MODE_PICK:
        pick_close()
        return
    _pick_index = 0
    import a11yscan_start as start
    if not zone_ready() and start.save_is_loaded():
        # A save is loaded but no lot is running: the world and lot screens.
        # The save's own data answers here, so the family list works with no
        # simulation at all, and choosing one loads their lot.
        _pick_kind = 'save_household'
        _pick_entries = [e for e in start.households_in_save() if e['zone_id']]
        if not _pick_entries:
            _say('A save is loaded, but no family in it has a home lot to '
                 'load. Control Alt M builds a Sim and picks them a lot.')
            return
        _mode = MODE_PICK
        _say('Choose a family to play. {} of them have a home. Up and down to '
             'browse, enter to load their lot, backspace to stop. {}'.format(
                 len(_pick_entries), start.describe(_pick_entries[0])))
        return
    if zone_ready():
        import a11yscan_lots as lots
        _pick_kind = 'household'
        _pick_entries = lots.households()
        if not _pick_entries:
            _say('No households found.')
            return
        _mode = MODE_PICK
        yours = sum(1 for e in _pick_entries if e.get('mine'))
        _say('Choose a household to play. {} of the {} here are yours, and '
             'they come first. Up and down to browse, enter to switch, '
             'backspace to stop. Save first. {}'.format(
                 yours, len(_pick_entries), _pick_say()))
        return
    _pick_kind = 'save'
    text = saves.open_picker()
    if not saves.active():
        _say(text)
        return
    _mode = MODE_PICK
    _say(text)


def pick_close(announce=True):
    global _mode, _pick_entries
    if _mode != MODE_PICK:
        return
    _mode = MODE_WORLD
    _pick_entries = []
    if _pick_kind == 'save':
        saves.close_picker()
    if announce:
        _say('Closed.')


def _pick_say():
    import a11yscan_lots as lots
    if not _pick_entries:
        return 'nothing to choose'
    if _pick_kind == 'save_household':
        import a11yscan_start as start
        entry = _pick_entries[_pick_index % len(_pick_entries)]
        return '{}. {} of {}.'.format(start.describe(entry),
                                      _pick_index % len(_pick_entries) + 1,
                                      len(_pick_entries))
    entry = _pick_entries[_pick_index % len(_pick_entries)]
    if _pick_kind == 'move':
        describe = (lots.describe_merge if entry.get('kind') == 'merge'
                    else lots.describe_move_target)
    else:
        describe = lots.describe_household
    return '{}. {} of {}.'.format(
        describe(entry), _pick_index % len(_pick_entries) + 1,
        len(_pick_entries))


def pick_next(step=1):
    global _pick_index
    if _pick_kind == 'save':
        _say(saves.next_save(step))
        return
    if not _pick_entries:
        _say('Nothing to choose.')
        return
    _pick_index = (_pick_index + step) % len(_pick_entries)
    _say(_pick_say())


def pick_activate():
    global _mode
    if _pick_kind == 'save':
        text = saves.choose()
        if not saves.active():
            _mode = MODE_WORLD
        _say(text)
        return
    if not _pick_entries:
        _say('Nothing to choose.')
        return
    import a11yscan_lots as lots
    entry = _pick_entries[_pick_index % len(_pick_entries)]
    # Drop the list first: travel takes a moment, and a second Enter arriving
    # in the meantime must not find anything left to act on.
    _mode = MODE_WORLD
    del _pick_entries[:]
    if _pick_kind == 'save_household':
        # No zone is running, so the live switcher has nothing to work with:
        # this route is built from the save's own protos instead.
        import a11yscan_start as start
        _say(start.play(entry))
        return
    if _pick_kind == 'move':
        if entry.get('kind') == 'merge':
            _say(lots.move_in_together(entry))
        else:
            _say(lots.move_house(entry))
        return
    _say(lots.switch_household(entry))


def run_probe():
    """Ask the running game what it will let us touch, wherever we are."""
    try:
        _say(probe.run())
    except Exception as ex:
        logfile.fail('probe failed ({!r})'.format(ex))
        _say('Probe failed.')


def play_sim(number):
    """Switch which household Sim you are playing, numbered as in a11y2.who."""
    text = cas.switch_to(number)
    _say(text)
    # The roster the scanner is holding describes the Sim we just stopped
    # playing, so drop it rather than letting "yourself" point at the old one.
    rescan(announce=False)


_INTENTS = {
    'rescan': lambda: rescan(True),
    'repeat': repeat,
    'where': where,
    'help': help_text,
    'back': back,
    'focus_self': focus_self,
    'needs': needs,
    'doing': doing,
    'focus_dialog': focus_dialog,
    'dismiss_dialog': dismiss_dialog,
    'answer_call': answer_call,
    'decline_call': decline_call,
    'focus_phone': focus_phone,
    'focus_inventory': focus_inventory,
    'focus_contacts': focus_contacts,
    'narrate': toggle_narration,
    'wants': wants,
    'aspiration': aspiration,
    'emotion': emotion,
    'go_home': go_home,
    'travel_menu': travel_menu,
    'grid_toggle': grid_toggle,
    'catalog_open': catalog_open,
    'cas_open': cas_open,
    'pick_open': pick_open,
    'move_house': move_house_open,
    'events_open': events_open,
    'relations_open': relations_open,
    'settings_open': settings_open,
    'jobs_open': jobs_open,
    'travel_open': travel_open,
    'cheats_open': cheats_open,
    'save_now': save_now,
    'funds': funds,
    'follow_toggle': follow_toggle,
    'center_lot': center_lot,
    'look_open': look_open,
    'look_random': look_randomize,
    'stories_open': stories_open,
    'probe': run_probe,
    'play_1': (lambda n=1: play_sim(n)),
    'play_2': (lambda n=2: play_sim(n)),
    'play_3': (lambda n=3: play_sim(n)),
    'play_4': (lambda n=4: play_sim(n)),
    'play_5': (lambda n=5: play_sim(n)),
    'play_6': (lambda n=6: play_sim(n)),
    'play_7': (lambda n=7: play_sim(n)),
    'play_8': (lambda n=8: play_sim(n)),
    'catalog_close': catalog_close,
    'catalog_place': catalog_place,
    'build_undo': build_undo,
    'sell_focused': sell_focused,
    'grid_north': grid_north,
    'grid_south': grid_south,
    'grid_east': grid_east,
    'grid_west': grid_west,
    'grid_describe': grid_describe,
    'grid_up': grid_up,
    'grid_down': grid_down,
    'reload': reload_mod,
}


def dispatch(intent):
    """Run one intent. Called on the simulation thread by the pump."""
    try:
        if intent.startswith('type_'):
            type_key(intent)
            return
        if not zone_ready() and _mode not in (MODE_CAS, MODE_PICK):
            if intent not in _NO_ZONE_INTENTS:
                _say('No lot is loaded yet.')
                return
        if intent in _INTENTS:
            _INTENTS[intent]()
            return
        if _mode == MODE_RELATIONS and intent in (
                'next_item', 'prev_item', 'next_category', 'prev_category',
                'activate', 'back'):
            import a11yscan_relations as relations
            if intent in ('next_item', 'next_category'):
                _say(relations.next_entry(1))
            elif intent in ('prev_item', 'prev_category'):
                _say(relations.next_entry(-1))
            elif intent == 'activate':
                relations_activate()
            else:
                relations_close()
            return

        if _mode == MODE_EVENTS and intent in (
                'next_item', 'prev_item', 'next_category', 'prev_category',
                'activate', 'back'):
            import a11yscan_events as events
            if intent in ('next_item', 'next_category'):
                _say(events.next_entry(1))
            elif intent in ('prev_item', 'prev_category'):
                _say(events.next_entry(-1))
            elif intent == 'activate':
                events_activate()
            else:
                events_close()
            return

        if _mode == MODE_CHEATS and intent in (
                'next_item', 'prev_item', 'next_category', 'prev_category',
                'activate', 'back'):
            if intent == 'next_item':
                _say(cheats.next_entry(1))
            elif intent == 'prev_item':
                _say(cheats.next_entry(-1))
            elif intent == 'next_category':
                _say(cheats.change(1))
            elif intent == 'prev_category':
                _say(cheats.change(-1))
            elif intent == 'activate':
                _say(cheats.activate())
            else:
                cheats_close()
            return

        if _mode == MODE_TRAVEL and intent in (
                'next_item', 'prev_item', 'next_category', 'prev_category',
                'activate', 'back'):
            if intent in ('next_item', 'next_category'):
                _say(travel.next_place(1))
            elif intent in ('prev_item', 'prev_category'):
                _say(travel.next_place(-1))
            elif intent == 'activate':
                travel_activate()
            else:
                travel_close()
            return

        if _mode == MODE_JOBS and intent in (
                'next_item', 'prev_item', 'next_category', 'prev_category',
                'activate', 'back'):
            if intent in ('next_item', 'next_category'):
                _say(careers.next_career(1))
            elif intent in ('prev_item', 'prev_category'):
                _say(careers.next_career(-1))
            elif intent == 'activate':
                _say(careers.take_current())
            else:
                jobs_close()
            return

        if _mode == MODE_SETTINGS and intent in (
                'next_item', 'prev_item', 'next_category', 'prev_category',
                'activate', 'back'):
            if intent == 'next_item':
                _say(settings.next_setting(1))
            elif intent == 'prev_item':
                _say(settings.next_setting(-1))
            elif intent == 'next_category':
                _say(settings.change(1))
            elif intent == 'prev_category':
                _say(settings.change(-1))
            elif intent == 'activate':
                _say(settings.describe())
            else:
                settings_close()
            return

        if _mode == MODE_PICK and intent in (
                'next_item', 'prev_item', 'next_category', 'prev_category',
                'activate', 'back'):
            if intent in ('next_item', 'next_category'):
                pick_next(1)
            elif intent in ('prev_item', 'prev_category'):
                pick_next(-1)
            elif intent == 'activate':
                pick_activate()
            else:
                pick_close()
            return

        if _mode == MODE_LOOK and intent in (
                'next_item', 'prev_item', 'next_category', 'prev_category',
                'activate', 'back'):
            if intent == 'next_item':
                _say(look.next_body_type(1))
            elif intent == 'prev_item':
                _say(look.next_body_type(-1))
            elif intent == 'next_category':
                _say(look.next_part(1))
            elif intent == 'prev_category':
                _say(look.next_part(-1))
            elif intent == 'activate':
                _say(look.apply_current())
            else:
                look_close()
            return

        if _mode == MODE_STORIES and intent in (
                'next_item', 'prev_item', 'next_category', 'prev_category',
                'activate', 'back'):
            if intent == 'next_item':
                _say(stories.next_question(1))
            elif intent == 'prev_item':
                _say(stories.next_question(-1))
            elif intent == 'next_category':
                _say(stories.next_answer(1))
            elif intent == 'prev_category':
                _say(stories.next_answer(-1))
            elif intent == 'activate':
                stories_activate()
            else:
                stories_close()
            return

        if _mode == MODE_CAS and intent in (
                'next_item', 'prev_item', 'next_category', 'prev_category',
                'activate', 'back'):
            if intent == 'next_item':
                cas_next_field(1)
            elif intent == 'prev_item':
                cas_next_field(-1)
            elif intent == 'next_category':
                cas_change(1)
            elif intent == 'prev_category':
                cas_change(-1)
            elif intent == 'activate':
                if cas.current_field() == 'questionnaire':
                    stories_open()
                else:
                    cas_activate()
            else:
                cas_close()
            return

        if _mode == MODE_CATALOG and intent in (
                'next_item', 'prev_item', 'next_category', 'prev_category',
                'activate', 'back'):
            if intent == 'next_item':
                catalog_next_item(1)
            elif intent == 'prev_item':
                catalog_prev_item()
            elif intent == 'next_category':
                catalog_next_category(1)
            elif intent == 'prev_category':
                catalog_prev_category()
            elif intent == 'activate':
                catalog_place()
            else:
                catalog_close()
            return

        if intent == 'next_item':
            if _mode == MODE_DIALOG:
                _next_dialog(1)
            elif _mode == MODE_MENU:
                _next_menu(1)
            else:
                next_item(1)
        elif intent == 'prev_item':
            if _mode == MODE_DIALOG:
                _next_dialog(-1)
            elif _mode == MODE_MENU:
                _next_menu(-1)
            else:
                next_item(-1)
        elif intent == 'next_category':
            if _mode == MODE_DIALOG:
                dialog_quantity(1)
            elif _mode == MODE_MENU:
                _next_menu(1)
            else:
                next_category(1)
        elif intent == 'prev_category':
            if _mode == MODE_DIALOG:
                dialog_quantity(-1)
            elif _mode == MODE_MENU:
                _next_menu(-1)
            else:
                next_category(-1)
        elif intent == 'activate':
            if _mode == MODE_DIALOG:
                _activate_dialog()
            elif _mode == MODE_MENU:
                _activate_menu()
            else:
                _open_menu()
        else:
            speech.log('unknown intent {!r}'.format(intent))
    except Exception as ex:
        speech.log('intent {} failed ({!r})'.format(intent, ex))
        try:
            speech.speak('Scanner error.')
        except Exception:
            pass
