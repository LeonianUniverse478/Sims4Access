# TS4 Access Plus - time, day, game speed, work/school times, money and bills.
import tyjokr_a11y_plus_core as core

DAYS = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")
_reminded = {}      # (sim_id, career uid) -> start ticks already announced
_bills_announced = [False]


def clock_text(dt):
    h, m = dt.hour(), dt.minute()
    suffix = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    if m == 0:
        return "{} {}".format(h12, suffix)
    return "{}:{:02d} {}".format(h12, m, suffix)


def day_text(dt):
    return DAYS[dt.day() % 7]


def speed_text():
    try:
        import services
        from clock import ClockSpeedMode
        speed = services.game_clock_service().clock_speed
        return {
            ClockSpeedMode.PAUSED: "Paused",
            ClockSpeedMode.NORMAL: "Normal speed",
            ClockSpeedMode.SPEED2: "Fast speed",
            ClockSpeedMode.SPEED3: "Ultra fast speed",
            ClockSpeedMode.SUPER_SPEED3: "Super speed, everyone is asleep or away",
            ClockSpeedMode.INTERACTION_STARTUP_SPEED: "Normal speed",
        }.get(speed, "Speed {}".format(int(speed)))
    except Exception:
        core.log_exc("speed")
        return ""


def _span_text(span):
    minutes = int(round(span.in_minutes()))
    if minutes < 60:
        return "{} minutes".format(minutes)
    hours, mins = divmod(minutes, 60)
    if hours >= 24:
        days = hours // 24
        hours = hours % 24
        text = "{} day{}".format(days, "" if days == 1 else "s")
        if hours:
            text += " {} hour{}".format(hours, "" if hours == 1 else "s")
        return text
    text = "{} hour{}".format(hours, "" if hours == 1 else "s")
    if mins:
        text += " {} minutes".format(mins)
    return text


def _career_word(career):
    try:
        from careers.career_enums import CareerCategory
        cat = getattr(career, "career_category", None)
        if cat == CareerCategory.School:
            return "school"
    except Exception:
        pass
    return "work"


def work_lines(sim_info, include_none=False):
    lines = []
    tracker = getattr(sim_info, "career_tracker", None)
    if tracker is None:
        return lines
    for career in list(tracker.careers.values()):
        word = _career_word(career)
        try:
            if career.currently_at_work:
                lines.append("{} is at {} now".format(sim_info.first_name, word))
                continue
            if career.is_work_time:
                lines.append("{} should be at {} now".format(sim_info.first_name, word))
                continue
            (span, start, end) = career.get_next_work_time()
            if span is None or start is None:
                continue
            lines.append("{} {} in {}, {} at {}".format(
                sim_info.first_name, word, _span_text(span), day_text(start), clock_text(start)))
        except Exception:
            core.log_exc("work lines")
    return lines


@core.hotkey(ord("T"), "time and day")
def read_time():
    import services
    now = services.time_service().sim_now
    parts = ["{} {}".format(day_text(now), clock_text(now)), speed_text()]
    for info in core.household_sims(instanced_only=False):
        parts.extend(work_lines(info))
    hh = services.active_household()
    if hh is not None:
        try:
            parts.append("Household money {:,} simoleons".format(int(hh.funds.money)))
        except Exception:
            pass
        try:
            owed = int(hh.bills_manager.current_payment_owed or 0)
            if owed > 0:
                parts.append("Unpaid bills {:,} simoleons. Pay them at the mailbox".format(owed))
        except Exception:
            pass
    core.speak(". ".join(p for p in parts if p) + ".")


def _check():
    import services
    sim = core.active_sim()
    if sim is None:
        return
    msgs = []
    if core.setting_on("work reminders"):
        for info in core.household_sims(instanced_only=False):
            tracker = getattr(info, "career_tracker", None)
            if tracker is None:
                continue
            for (uid, career) in list(tracker.careers.items()):
                try:
                    if career.currently_at_work or career.is_work_time:
                        continue
                    (span, start, end) = career.get_next_work_time()
                    if span is None or start is None:
                        continue
                    mins = span.in_minutes()
                    key = (info.sim_id, uid)
                    stamp = int(start.absolute_ticks())
                    if 0 < mins <= 60 and _reminded.get(key) != stamp:
                        _reminded[key] = stamp
                        msgs.append("{} has {} in {}, at {}".format(
                            info.first_name, _career_word(career), _span_text(span), clock_text(start)))
                except Exception:
                    core.log_exc("work reminder")
    if core.setting_on("bill reminders"):
        try:
            hh = services.active_household()
            owed = int(hh.bills_manager.current_payment_owed or 0) if hh is not None else 0
            if owed > 0 and not _bills_announced[0]:
                _bills_announced[0] = True
                msgs.append("Bills have arrived: {:,} simoleons. Pay them at the mailbox".format(owed))
            elif owed <= 0:
                _bills_announced[0] = False
        except Exception:
            core.log_exc("bill reminder")
    if msgs:
        core.speak(". ".join(msgs) + ".", interrupt=False)


core.add_ticker(3.0, _check)


@core.on_zone_started
def _start():
    _bills_announced[0] = False    # unpaid bills are mentioned once after loading


# ---------------------------------------------------------------- say every speed change (P, 1, 2, 3)
# Only changes the player or the game makes count. Pauses while a game window or list is
# open (UI_MODAL) are left out, so opening a menu does not say "Paused".
_last_spoken = [None]


def _effective(speed):
    from clock import ClockSpeedMode
    if speed == ClockSpeedMode.INTERACTION_STARTUP_SPEED:
        return ClockSpeedMode.NORMAL     # a short game-made pause when an action starts
    return speed


def _announce_speed(before):
    try:
        import services
        if not core.setting_on("speak game speed"):
            return
        zone = services.current_zone()
        if zone is None or not getattr(zone, "is_zone_running", False):
            return
        now = _effective(services.game_clock_service().clock_speed)
        if now == before:
            return
        import time
        text = speed_text()
        if _last_spoken[0] == (text, int(time.monotonic() // 2)):
            return          # the same change reported twice in a row
        _last_spoken[0] = (text, int(time.monotonic() // 2))
        core.speak(text)
    except Exception:
        core.log_exc("announce speed")


def _wrap_clock(name):
    from clock import GameClock, GameSpeedChangeSource
    original = getattr(GameClock, name)
    if getattr(original, "_a11yplus", False):
        return

    def wrapper(self, *args, **kwargs):
        source = kwargs.get("source", args[1] if len(args) > 1 else GameSpeedChangeSource.GAMEPLAY)
        try:
            before = _effective(self.clock_speed)
        except Exception:
            before = None
        result = original(self, *args, **kwargs)
        if source != GameSpeedChangeSource.UI_MODAL and before is not None:
            core.post(_announce_speed, before)
        return result

    wrapper._a11yplus = True
    setattr(GameClock, name, wrapper)


try:
    for _name in ("push_speed", "pop_speed", "set_clock_speed"):
        _wrap_clock(_name)
    core.log("speed announcements hooked")
except Exception:
    core.log_exc("hook clock")


# ---------------------------------------------------------------- spoken Build / Live mode

_last_mode = [None]


def _mode_check():
    try:
        import services
        zone = services.current_zone()
        if zone is None or not getattr(zone, "is_zone_running", True):
            _last_mode[0] = None
            return
        build = bool(zone.is_in_build_buy)
    except Exception:
        return
    if _last_mode[0] is None:
        _last_mode[0] = build
        return
    if build != _last_mode[0]:
        _last_mode[0] = build
        core.log("mode: " + ("build" if build else "live"))
        if build:
            core.speak("Build mode. Press Alt B for the build helper. Fn F1 goes back to Live mode.")
        else:
            core.speak("Live mode." + _paused_hint())


def _is_paused():
    try:
        import services
        from clock import ClockSpeedMode
        return services.game_clock_service().clock_speed == ClockSpeedMode.PAUSED
    except Exception:
        return False


def _paused_hint():
    return " The game is paused. Press 1 to play." if _is_paused() else ""


_queued_seen = [None]


def _paused_queue_check():
    """Say so when the player gives the Sim an action while the game is paused (it waits in the queue)."""
    try:
        import services
        zone = services.current_zone()
        if zone is None or not getattr(zone, "is_zone_running", True) or zone.is_in_build_buy:
            _queued_seen[0] = None
            return
        sim = core.active_sim()
        if sim is None:
            return
        ids = set(si.id for si in sim.queue)
    except Exception:
        return
    old = _queued_seen[0]
    _queued_seen[0] = ids
    if old is None or not _is_paused():
        return
    if ids - old:
        core.log("queued while paused")
        core.speak("Added to the queue. The game is paused, so it waits. Press 1 to play.", interrupt=False)


core.add_ticker(0.3, _mode_check)
core.add_ticker(0.5, _paused_queue_check)
