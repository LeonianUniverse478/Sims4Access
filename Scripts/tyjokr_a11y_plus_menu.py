# TS4 Access Plus - main menu (Alt+A): every feature, its key, and settings.
# Merged into TS4 Access 2026-10-08. The add-on's own action queue is not
# carried over: Alt+Q opens TS4 Access's queue (Ctrl+Alt+Q), which does the same.
import tyjokr_a11y_plus_core as core


@core.hotkey(ord("Q"), "action queue")
def open_queue():
    import tyjokr_a11y_hub as hub
    hub.action_queue()


def _features():
    import tyjokr_a11y_plus_needs as needs, tyjokr_a11y_plus_time as t, tyjokr_a11y_plus_rooms as rooms
    import tyjokr_a11y_plus_notify as notify, tyjokr_a11y_plus_sims as sims
    feats = [
        ("Needs", "Alt+N. Reads all needs, lowest first.", needs.read_needs),
        ("Time, work and money", "Alt+T. Day, time, game speed, next work or school, money and bills.", t.read_time),
        ("Action queue", "Alt+Q. What your Sim is doing and has queued. Cancel actions.", open_queue),
        ("Rooms", "Alt+R. The rooms of the house and what is in them.", rooms.open_rooms),
        ("Where am I", "Alt+W. Which room your Sim is in.", rooms.where_am_i),
        ("Notifications", "Alt+L. The last pop-up messages, newest first.", notify.open_history),
        ("Create and edit Sims", "Alt+C. Start a brand-new family, add a Sim, change name, traits, aspiration.", sims.open_menu),
    ]
    try:
        import tyjokr_a11y_plus_build as build
        feats.append(("Build helper", "Alt+B. Build rooms, walls, doors and windows from the keyboard.", build.open_menu))
    except Exception:
        pass
    return feats


@core.hotkey(ord("A"), "Access Plus menu")
def open_menu():
    rows = [(name, desc, fn) for (name, desc, fn) in _features()]
    rows.append(("Settings", "Turn warnings and reminders on or off.", "settings"))
    core.choose("TS4 Access Plus {}".format(core.VERSION),
                "Every feature also has its own Alt key, shown in its description.", rows, _pick, tag="menu")


def _pick(value):
    if value == "settings":
        open_settings()
    elif callable(value):
        value()


def open_settings():
    rows = []
    for name in core.DEFAULTS:
        rows.append(("{}: {}".format(name.capitalize(), "on" if core.setting_on(name) else "off"),
                     "Choose to switch it.", name))
    core.choose("Access Plus settings", "Choose a setting to switch it on or off.", rows, _toggle, tag="menu")


def _toggle(name):
    on = core.toggle_setting(name)
    core.speak("{} {}.".format(name.capitalize(), "on" if on else "off"))
