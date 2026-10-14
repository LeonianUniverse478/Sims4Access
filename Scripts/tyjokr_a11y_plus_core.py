# TS4 Access Plus (by Michael Maslo) - core helpers: log, speech, main-thread pump, hotkeys, dialogs.
# Speech goes through the TS4 Access mod (tyjokr_a11y_speech), so it uses the
# same screen reader connection (JAWS / NVDA through Prism, or a Windows voice).
import os, time, threading, traceback
import sims4.commands

# Merged into TS4 Access from TS4 Access Plus 0.7.1 (2026-10-08).
VERSION = "0.7.1"

# ---------------------------------------------------------------- log

def _mods_folder():
    path = os.path.normpath(__file__)
    low = path.lower()
    marker = ".ts4script"
    if marker in low:
        return os.path.dirname(path[:low.index(marker) + len(marker)])
    return os.path.dirname(path)


MODS_FOLDER = _mods_folder()
# Files (log, settings, room names) are written only from the installed mod:
# importing the module from the kit's Scripts folder (offline tests) writes nothing.
IN_GAME = ".ts4script" in os.path.normpath(__file__).lower()
LOG_PATH = os.path.join(MODS_FOLDER, "TS4_Access_Plus.log")
# 0.7.1: the log is also kept in the Windows user folder (outside OneDrive), so it can
# always be found; when the Mods copy cannot be written, that copy says why.
HOME_LOG_PATH = os.path.join(os.environ.get("USERPROFILE") or os.path.expanduser("~"), "TS4_Access_Plus.log")
_log_lock = threading.Lock()
_log_started = False


def log(message):
    global _log_started
    if not IN_GAME:
        return
    try:
        with _log_lock:
            mode = "a" if _log_started else "w"
            _log_started = True
            line = "[{}] {}\n".format(time.strftime("%H:%M:%S"), message)
            problem = None
            try:
                with open(LOG_PATH, mode, encoding="utf-8") as f:
                    f.write(line)
            except Exception as e:
                problem = "[could not write {}: {}]\n".format(LOG_PATH, e)
            try:
                with open(HOME_LOG_PATH, mode, encoding="utf-8") as f:
                    f.write(line if problem is None else problem + line)
            except Exception:
                pass
    except Exception:
        pass


def log_exc(where):
    log("ERROR in {}: {}".format(where, traceback.format_exc()))


log("TS4 Access Plus {} loading from {}".format(VERSION, MODS_FOLDER))

# ---------------------------------------------------------------- settings

SETTINGS_PATH = os.path.join(MODS_FOLDER, "TS4_Access_Plus.cfg")
DEFAULTS = {
    "need alerts": "on",
    "need alerts for whole household": "on",
    "work reminders": "on",
    "bill reminders": "on",
    "speak notifications": "off",
    "speak game speed": "on",
}
_settings = dict(DEFAULTS)


def _load_settings():
    try:
        if not os.path.isfile(SETTINGS_PATH):
            _save_settings()
            return
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                (k, v) = line.split("=", 1)
                k = k.strip().lower()
                if k in DEFAULTS:
                    _settings[k] = v.strip().lower()
    except Exception:
        log_exc("load settings")


def _save_settings():
    if not IN_GAME:
        return
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            f.write("# TS4 Access Plus settings. on or off.\n")
            for k in DEFAULTS:
                f.write("{} = {}\n".format(k, _settings.get(k, DEFAULTS[k])))
    except Exception:
        log_exc("save settings")


def setting_on(name):
    return _settings.get(name, DEFAULTS.get(name, "off")) == "on"


def toggle_setting(name):
    _settings[name] = "off" if setting_on(name) else "on"
    _save_settings()
    return setting_on(name)


_load_settings()

# ---------------------------------------------------------------- speech

def speak(text, interrupt=True):
    text = str(text or "").strip()
    if not text:
        return
    log("SAY: " + text)
    try:
        import tyjokr_a11y_speech as s
        s.speak(text, interrupt=interrupt, explicit=True)
    except Exception:
        log_exc("speak")


def speak_parts(parts):
    """parts: list of str or ("loc", hash) - localized names resolved by TS4 Access."""
    try:
        import tyjokr_a11y_scanner as scanner
        scanner._speak_parts(parts)
        log("SAY parts: {!r}".format(parts))
        return
    except Exception:
        log_exc("speak_parts")
    speak("".join(p for p in parts if isinstance(p, str)))


def with_sim(ls, sim_info):
    """Fill a game string's Sim placeholders (his/her, name) with this Sim."""
    try:
        from sims4.localization import _create_localized_string
        return _create_localized_string(int(ls.hash), sim_info)
    except Exception:
        return ls


def raw(text):
    from sims4.localization import LocalizationHelperTuning
    return LocalizationHelperTuning.get_raw_text(str(text))

# ---------------------------------------------------------------- main-thread pump

_queue = []
_queue_lock = threading.Lock()
_alarm = None
_tickers = []   # (interval_seconds, fn, [last_run])


class _Owner(object):
    pass


_owner = _Owner()


def post(fn, *args):
    with _queue_lock:
        if len(_queue) > 32:
            del _queue[0]
        _queue.append((fn, args))


def add_ticker(seconds, fn):
    _tickers.append([seconds, fn, 0.0])


def _drain(_handle=None):
    with _queue_lock:
        batch = _queue[:]
        del _queue[:]
    for (fn, args) in batch:
        try:
            fn(*args)
        except Exception:
            log_exc("posted {}".format(getattr(fn, "__name__", fn)))
    now = time.monotonic()
    for t in _tickers:
        if now - t[2] >= t[0]:
            t[2] = now
            try:
                t[1]()
            except Exception:
                log_exc("ticker {}".format(getattr(t[1], "__name__", t[1])))


def start_pump():
    global _alarm
    try:
        import alarms, clock
        if _alarm is not None:
            try:
                alarms.cancel_alarm(_alarm)
            except Exception:
                pass
        _alarm = alarms.add_alarm_real_time(_owner, clock.interval_in_real_seconds(0.1), _drain, repeating=True)
        log("pump started")
    except Exception:
        log_exc("start pump")

# ---------------------------------------------------------------- hotkeys (Alt + key)

HOTKEYS = {}     # vk -> (fn, description)
_keys_thread = None


def hotkey(vk, description):
    def deco(fn):
        HOTKEYS[vk] = (fn, description)
        return fn
    return deco


def _game_foreground(user32, kernel32):
    try:
        import ctypes
        hwnd = user32.GetForegroundWindow()
        pid = ctypes.c_ulong(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value == os.getpid()
    except Exception:
        return True


def _keys_loop():
    import ctypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    # PyDLL keeps the GIL during the call. The game's main thread holds the GIL most of
    # the time, so re-acquiring it after every call starves this thread (TS4 Access does the same).
    try:
        read = ctypes.PyDLL("user32").GetAsyncKeyState
        read.argtypes = [ctypes.c_int]
        read.restype = ctypes.c_short
    except Exception:
        read = user32.GetAsyncKeyState
        read.restype = ctypes.c_short
    VK_MENU, VK_CONTROL, VK_SHIFT, VK_LWIN, VK_RWIN = 0x12, 0x11, 0x10, 0x5B, 0x5C
    down = set()
    typing_down = set()
    alt_seen = 0.0
    other_seen = 0.0
    log("hotkey thread running, keys: {}".format(
        ", ".join("{}={}".format(chr(vk), d) for (vk, (fn, d)) in sorted(HOTKEYS.items()))))
    while True:
        try:
            time.sleep(0.02)
            now = time.monotonic()
            a = read(VK_MENU)
            o = read(VK_CONTROL) | read(VK_LWIN) | read(VK_RWIN)
            states = [(vk, read(vk)) for vk in list(HOTKEYS)]
            if a & 0x8001:
                alt_seen = now
            if o & 0x8000:
                other_seen = now
            shift = bool(read(VK_SHIFT) & 0x8000)
            alt = (a & 0x8000) or now - alt_seen < 0.6
            other = (o & 0x8000) or now - other_seen < 0.3
            if _typing is not None:
                _typing_poll(read, shift, typing_down)
                continue
            for (vk, s) in states:
                pressed = s & 0x8000
                tapped = s & 0x0001
                if (pressed or tapped) and vk not in down:
                    if pressed:
                        down.add(vk)
                    if alt or 0x41 <= vk <= 0x5A:
                        log("seen key {} alt={} other={}".format(chr(vk), bool(alt), bool(other)))
                    if alt and not other and _game_foreground(user32, kernel32):
                        (fn, desc) = HOTKEYS[vk]
                        log("key Alt+{} ({})".format(chr(vk) if 48 <= vk <= 90 else vk, desc))
                        if _wants_shift(fn):
                            post(fn, shift)
                        else:
                            post(fn)
                elif not pressed and vk in down:
                    down.discard(vk)
        except Exception:
            log_exc("keys loop")
            time.sleep(1.0)


# ---------------------------------------------------------------- typing capture
# TS4 Access cannot reach the OK button of text dialogs, so while one of our text boxes
# is open we record the typed characters ourselves; Enter finishes, Escape cancels.
_typing = None      # dict(chars=list, done=fn, dialog_id=int) while a text box is open
_TYPING_KEYS = list(range(0x30, 0x3A)) + list(range(0x41, 0x5B)) + [0x20, 0xBD, 0xDE, 0xBE, 0x08, 0x0D, 0x1B]


def _typing_poll(read, shift, held):
    if _typing is not None and not _typing.get("armed"):
        # Keys still held from opening the box (like Enter) must not count.
        held.clear()
        held.update(vk for vk in _TYPING_KEYS if read(vk) & 0x8000)
        _typing["armed"] = True
        return
    for vk in _TYPING_KEYS:
        s = read(vk)
        if s & 0x8000:
            if vk in held:
                continue
            held.add(vk)
        else:
            held.discard(vk)
            continue
        t = _typing
        if t is None:
            return
        if vk == 0x0D:
            post(_typing_finish, True)
        elif vk == 0x1B:
            post(_typing_finish, False)
        elif vk == 0x08:
            if t["chars"]:
                t["chars"].pop()
        elif 0x41 <= vk <= 0x5A:
            t["chars"].append(chr(vk) if shift else chr(vk).lower())
        elif 0x30 <= vk <= 0x39:
            t["chars"].append(chr(vk))
        elif vk == 0x20:
            t["chars"].append(" ")
        elif vk == 0xBD:
            t["chars"].append("_" if shift else "-")
        elif vk == 0xDE:
            t["chars"].append('"' if shift else "'")
        elif vk == 0xBE:
            t["chars"].append(".")


def _typing_finish(accepted):
    global _typing
    t = _typing
    _typing = None
    if t is None:
        return
    _cancel_previous("text")
    text = "".join(t["chars"]).strip()
    log("typed text: {!r} accepted={}".format(text, accepted))
    if not accepted:
        speak("Cancelled.")
        return
    t["done"](text)


def _wants_shift(fn):
    return getattr(fn, "_wants_shift", False)


def start_keys():
    global _keys_thread
    if _keys_thread is not None:
        return
    _keys_thread = threading.Thread(target=_keys_loop, name="a11yplus_keys", daemon=True)
    _keys_thread.start()

# ---------------------------------------------------------------- game helpers

def active_sim():
    import services
    return services.get_active_sim()


def client():
    import services
    return services.client_manager().get_first_client()


def sim_name(sim_info):
    try:
        return " ".join(p for p in (sim_info.first_name, sim_info.last_name) if p).strip()
    except Exception:
        return "Sim"


def household_sims(instanced_only=True):
    import services
    hh = services.active_household()
    if hh is None:
        return []
    out = []
    for info in hh.sim_info_gen():
        sim = info.get_sim_instance()
        if instanced_only and sim is None:
            continue
        out.append(info)
    return out


def fence_input():
    """Stop the key that opened a dialog from also choosing in it (TS4 Access helper)."""
    try:
        import tyjokr_a11y_keys as keys
        keys.fence_opening_input()
    except Exception:
        pass

# ---------------------------------------------------------------- dialogs

_open_dialogs = {}


def _cancel_previous(tag):
    old = _open_dialogs.pop(tag, None)
    if old:
        try:
            import services
            services.ui_dialog_service().dialog_cancel(old)
        except Exception:
            pass


def choose(title, text, rows, on_pick, tag="main", multi=0, min_pick=1, on_cancel=None):
    """Show a list. rows: list of (label_or_LocalizedString, description_or_None, value, selected).
    on_pick(value) for single choice; on_pick(list_of_values) when multi > 0."""
    try:
        import services
        from ui.ui_dialog_picker import UiObjectPicker, ObjectPickerRow
        owner = services.get_active_sim()
        if owner is None:
            speak("Load a household first.")
            return False
        _cancel_previous(tag)
        dialog = UiObjectPicker.TunableFactory().default(
            owner,
            title=lambda *a, **k: raw(title),
            text=lambda *a, **k: raw(text),
            picker_type=UiObjectPicker.UiObjectPickerObjectPickerType.OBJECT,
            min_selectable=min_pick if multi else 1,
            max_selectable=multi if multi else 1)
        values = {}
        for (i, row) in enumerate(rows):
            row = tuple(row)
            (label, desc, value) = (row + (None, None, None))[:3]
            selected = row[3] if len(row) > 3 else False
            icon_obj = row[4] if len(row) > 4 else None
            values[i] = value
            name = raw(label) if isinstance(label, str) else label
            description = raw(desc) if isinstance(desc, str) else desc
            icon_info = None
            if icon_obj is not None:
                try:
                    from distributor.shared_messages import IconInfoData
                    icon_info = IconInfoData(obj_instance=icon_obj)
                except Exception:
                    icon_info = None
            dialog.add_row(ObjectPickerRow(option_id=i, name=name, row_description=description,
                                           row_tooltip=None, icon=None, icon_info=icon_info,
                                           tag=i, is_selected=bool(selected)))

        def listener(reply):
            if _open_dialogs.get(tag) == reply.dialog_id:
                _open_dialogs.pop(tag, None)
            if not reply.accepted:
                if on_cancel is not None:
                    post(on_cancel)
                return
            tags = list(reply.get_result_tags())
            picked = [values[t] for t in tags if t in values]
            if multi:
                post(on_pick, picked)
            elif picked:
                post(on_pick, picked[0])

        dialog.add_listener(listener)
        _open_dialogs[tag] = dialog.dialog_id
        fence_input()
        dialog.show_dialog()
        return True
    except Exception:
        log_exc("choose " + title)
        speak("Could not open the list.")
        return False


def ask_text(title, text, initial, on_done, max_length=40):
    """Show a text box. Type, then Enter. Escape cancels. on_done(str).
    With an initial value, Enter on an empty box keeps it."""
    global _typing
    if initial:
        text = "{} Press Enter to keep {}, or type something else and press Enter.".format(text, initial)
    else:
        text = "{} Type, then press Enter.".format(text)

    def finished(value):
        value = value or (initial or "")
        on_done(value[:max_length])

    try:
        import services
        from sims4.collections import AttributeDict
        from ui.ui_dialog_generic import UiDialogTextInputOkCancel
        from ui.ui_text_input import UiTextInput, _TextInputLengthFixed
        owner = services.get_active_sim()
        if owner is None:
            speak("Load a household first.")
            return False
        ti = UiTextInput(sort_order=0)
        ti.default_text = None
        ti.title = None
        ti.restricted_characters = None
        ti.check_profanity = False
        ti.height = None
        ti.initial_value = None
        ti.length_restriction = _TextInputLengthFixed(min_length=None, max_length=max_length)
        _cancel_previous("text")
        dialog = UiDialogTextInputOkCancel.TunableFactory().default(
            owner,
            title=lambda *a, **k: raw(title),
            text=lambda *a, **k: raw(text),
            text_inputs=AttributeDict({"value": ti}))
        session = {"chars": [], "done": finished, "dialog_id": dialog.dialog_id}

        def listener(reply):
            global _typing
            _open_dialogs.pop("text", None)
            if _typing is not session:
                return          # already finished with Enter or Escape
            _typing = None
            if not reply.accepted:
                speak("Cancelled.")
                return
            value = str(reply.text_input_responses.get("value", "") or "").strip()
            post(finished, value)

        dialog.add_listener(listener)
        _open_dialogs["text"] = dialog.dialog_id
        fence_input()
        dialog.show_dialog()
        _typing = session
        return True
    except Exception:
        log_exc("ask_text " + title)
        speak("Could not open the text box.")
        return False


def open_interactions(obj):
    """Open the pie menu (interactions) for a Sim or object, the same way the TS4 Access scanner does."""
    try:
        import services, distributor.ops, distributor.system
        from server.pick_info import PickType
        is_sim = getattr(obj, "is_sim", False)
        pick_type = PickType.PICK_SIM if is_sim else PickType.PICK_OBJECT
        pos = obj.position
        try:
            level = int(obj.level)
        except Exception:
            level = 0
        try:
            lot_id = int(services.active_lot().lot_id)
        except Exception:
            lot_id = 0
        first = ""
        if is_sim:
            first = str(obj.sim_info.first_name or "").replace("|", " ")
        msg = "A11y|pick|{}|{}|{}|{}|{:.3f}|{:.3f}|{:.3f}|{}".format(
            obj.id, int(pick_type), lot_id, first, float(pos.x), float(pos.y), float(pos.z), level)
        distributor.system.Distributor.instance().add_op_with_no_owner(distributor.ops.SendUIMessage(msg))
        return True
    except Exception:
        log_exc("open_interactions")
        speak("Could not open the actions for that.")
        return False

# ---------------------------------------------------------------- startup

_zone_started_callbacks = []


def on_zone_started(fn):
    _zone_started_callbacks.append(fn)
    return fn


def _install_zone_hook():
    import zone
    original = zone.Zone.on_loading_screen_animation_finished

    def a11yplus_on_loading_screen_animation_finished(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        try:
            log("zone loaded: {}".format(getattr(self, "id", "?")))
            start_pump()
            start_keys()
            for fn in _zone_started_callbacks:
                try:
                    fn()
                except Exception:
                    log_exc("zone start " + getattr(fn, "__name__", "?"))
        except Exception:
            log_exc("zone hook")
        return result

    zone.Zone.on_loading_screen_animation_finished = a11yplus_on_loading_screen_animation_finished


try:
    _install_zone_hook()
    log("zone hook installed")
except Exception:
    log_exc("install zone hook")


@sims4.commands.Command("a11yplus.status", command_type=sims4.commands.CommandType.Live)
def _status(_connection=None):
    out = sims4.commands.CheatOutput(_connection)
    out("TS4 Access Plus {} - pump {}, keys {}".format(VERSION, _alarm is not None, _keys_thread is not None))
    speak("TS4 Access Plus version {} is running.".format(VERSION))
    return True
