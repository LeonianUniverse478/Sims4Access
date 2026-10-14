# TS4 Access Plus - needs: Alt+N readout, and automatic low-need warnings.
import tyjokr_a11y_plus_core as core

MOTIVES = (
    ("motive_hunger", "Hunger"),
    ("motive_bladder", "Bladder"),
    ("motive_energy", "Energy"),
    ("motive_hygiene", "Hygiene"),
    ("motive_fun", "Fun"),
    ("motive_social", "Social"),
)
LOW, CRITICAL, RECOVER = 30, 15, 45     # percent
_stat_types = {}
_state = {}    # (sim_id, motive) -> "ok" | "low" | "critical"


def _stat(name):
    if name not in _stat_types:
        try:
            from server_commands.argument_helpers import get_tunable_instance
            import sims4.resources
            _stat_types[name] = get_tunable_instance(sims4.resources.Types.STATISTIC, name, exact_match=True)
        except Exception:
            core.log_exc("need stat " + name)
            _stat_types[name] = None
    return _stat_types[name]


def percent(sim_info, name):
    stat = _stat(name)
    if stat is None:
        return None
    tracker = sim_info.get_tracker(stat)
    if tracker is None:
        return None
    value = tracker.get_value(stat)
    if value is None:
        return None
    try:
        lo, hi = float(stat.min_value), float(stat.max_value)
    except Exception:
        lo, hi = -100.0, 100.0
    if hi <= lo:
        return None
    return max(0, min(100, int(round((float(value) - lo) * 100.0 / (hi - lo)))))


def word(p):
    if p < CRITICAL:
        return "critical"
    if p < LOW:
        return "low"
    if p < 60:
        return "okay"
    return "good"


def needs_of(sim_info):
    out = []
    for (name, label) in MOTIVES:
        p = percent(sim_info, name)
        if p is not None:
            out.append((p, label))
    return out


@core.hotkey(ord("N"), "read needs")
def read_needs():
    sim = core.active_sim()
    if sim is None:
        core.speak("No active Sim.")
        return
    needs = needs_of(sim.sim_info)
    if not needs:
        core.speak("Needs are not available for this Sim.")
        return
    needs.sort()
    text = ", ".join("{} {} percent {}".format(label, p, word(p)) for (p, label) in needs)
    core.speak("{} needs, lowest first: {}.".format(sim.sim_info.first_name, text))


def _check():
    if not core.setting_on("need alerts"):
        return
    sim = core.active_sim()
    if sim is None:
        return
    infos = core.household_sims() if core.setting_on("need alerts for whole household") else [sim.sim_info]
    alerts = []
    for info in infos:
        for (name, label) in MOTIVES:
            p = percent(info, name)
            if p is None:
                continue
            key = (info.sim_id, name)
            old = _state.get(key)
            if p < CRITICAL:
                new = "critical"
            elif p < LOW:
                new = "low" if old != "critical" or p >= CRITICAL + 5 else "critical"
            elif p >= RECOVER:
                new = "ok"
            else:
                new = old or "ok"
            _state[key] = new
            if new != old and new in ("low", "critical"):
                who = "" if info is sim.sim_info else info.first_name + ": "
                alerts.append("{}{} {}".format(who, label, "very low" if new == "critical" else "low"))
    if alerts:
        core.speak(". ".join(alerts) + ".", interrupt=False)


core.add_ticker(2.0, _check)


@core.on_zone_started
def _start():
    _state.clear()
