# TS4 Access Plus - make and edit Sims without Create a Sim (Alt+C).
# New Sims join the active household with a random look made by the game.
import tyjokr_a11y_plus_core as core

TRAIT_LIMITS = {"TODDLER": 1, "CHILD": 1, "TEEN": 2, "YOUNGADULT": 3, "ADULT": 3, "ELDER": 3}
AGE_CHOICES = (("Young Adult", "YOUNGADULT", "The usual age to start with. Can have a full career."),
               ("Adult", "ADULT", "Grown up. Can have a full career."),
               ("Elder", "ELDER", "Older Sim. Can still work, will die of old age eventually."),
               ("Teen", "TEEN", "Goes to high school. Can have a part time job."),
               ("Child", "CHILD", "Goes to grade school. Needs a grown up in the household."),
               ("Toddler", "TODDLER", "Very young. Needs lots of care from a grown up."))
MAX_HOUSEHOLD = 8


class _Draft(object):
    def __init__(self):
        self.age = None
        self.gender = None
        self.first = ""
        self.last = ""
        self.traits = []


class _Fake(object):
    """Stands in for a Sim when checking which traits fit an age and gender."""
    def __init__(self, age, gender):
        from sims.sim_info_types import Species
        self.age = age
        self.gender = gender
        self.species = Species.HUMAN


_draft = [None]


def _age_enum(name):
    from sims.sim_info_types import Age
    return getattr(Age, name)


def _age_name(age):
    for (label, key, _) in AGE_CHOICES:
        if _age_enum(key) == age:
            return label
    return str(age)


def personality_traits(age, gender):
    import services, sims4.resources
    fake = _Fake(age, gender)
    out = []
    for trait in services.get_instance_manager(sims4.resources.Types.TRAIT).types.values():
        try:
            if not trait.is_personality_trait:
                continue
            if getattr(trait, "is_npc_only", False):
                continue
            if trait.display_name is None:
                continue
            if not trait.is_valid_trait(fake):
                continue
            if "reward" in trait.__name__.lower() or "hos_" in trait.__name__.lower():
                continue
            out.append(trait)
        except Exception:
            continue
    out.sort(key=lambda t: t.__name__.lower().replace("trait_", ""))
    return out


def pick_traits(title, age, gender, limit, token_sim, on_done, chosen=None):
    """Choose traits one at a time with Enter (no Done button needed).
    Traits that clash with ones already chosen are left out."""
    chosen = list(chosen or [])
    if len(chosen) >= limit:
        on_done(chosen)
        return
    available = [t for t in personality_traits(age, gender)
                 if t not in chosen and not _conflict(chosen + [t])]
    rows = _trait_rows(available, token_sim)
    if chosen:
        # At the end, so pressing Enter on the first row never finishes by accident.
        rows.append(("Done, keep {} trait{}".format(len(chosen), "" if len(chosen) == 1 else "s"),
                     "Finish without choosing more traits.", "done"))

    def picked(value):
        if value == "done":
            on_done(chosen)
            return
        chosen.append(value)
        if len(chosen) >= limit:
            on_done(chosen)
        else:
            core.post(pick_traits, title, age, gender, limit, token_sim, on_done, chosen)

    if chosen:
        hint = "To stop here, choose Done at the end of the list."
    else:
        hint = "Press Enter on a trait to choose it. Traits that clash with ones already chosen are left out."
    core.choose(title, "Trait {} of {}. {}".format(len(chosen) + 1, limit, hint), rows, picked, tag="sims")


def _trait_rows(traits, token_sim, selected=()):
    rows = []
    for t in traits:
        try:
            name = t.display_name(token_sim)
        except Exception:
            name = core.raw(t.__name__)
        try:
            desc = t.trait_description(token_sim) if t.trait_description is not None else None
        except Exception:
            desc = None
        rows.append((name, desc, t, t in selected))
    return rows


def set_exact_traits(info, chosen):
    """The game fills new Sims up with random traits. Keep exactly the chosen ones."""
    chosen = list(chosen)
    try:
        for t in list(info.trait_tracker.personality_traits):
            if t not in chosen:
                info.remove_trait(t)
        for t in chosen:
            if not info.has_trait(t):
                info.add_trait(t)
    except Exception:
        core.log_exc("set traits")


def _conflict(traits):
    for a in traits:
        for b in traits:
            if a is not b and (a.is_conflicting(b) or b.is_conflicting(a)):
                return True
    return False

# ---------------------------------------------------------------- main menu


@core.hotkey(ord("C"), "create and edit Sims")
def open_menu():
    sim = core.active_sim()
    if sim is None:
        core.speak("No active Sim.")
        return
    name = sim.sim_info.first_name
    import tyjokr_a11y_plus_family as family
    rows = [
        ("Continue the new family" if family.has_draft() else "Start a brand-new family",
         "Make your own Sims from scratch, choose an empty lot or a house, and play them.", "family"),
        ("Add a new Sim to this household", "Choose age, gender, name and traits. The game gives the Sim a random look.", "new"),
        ("Change {}'s name".format(name), "Type a new first and last name.", "name"),
        ("Change {}'s traits".format(name), "Choose new personality traits.", "traits"),
        ("Change {}'s aspiration".format(name), "Choose a new life goal.", "aspiration"),
        ("Describe {}".format(name), "Age, gender, traits, aspiration and career.", "describe"),
        ("Open the game's Create a Sim for {}".format(name), "The full game screen, mostly needs a mouse. Use it only with sighted help.", "cas"),
    ]
    core.choose("Create and edit Sims", "Choose what to do.", rows, _menu_pick, tag="sims")


def _menu_pick(value):
    sim = core.active_sim()
    if sim is None:
        return
    info = sim.sim_info
    if value == "family":
        import tyjokr_a11y_plus_family as family
        family.resume()
    elif value == "new":
        start_new()
    elif value == "name":
        _rename(info)
    elif value == "traits":
        _edit_traits(info)
    elif value == "aspiration":
        choose_aspiration(info)
    elif value == "describe":
        describe(info)
    elif value == "cas":
        try:
            import sims4.commands
            client = core.client()
            sims4.commands.client_cheat("sims.exit2cas {} {} {}".format(sim.id, info.household_id, sim.id), client.id)
        except Exception:
            core.log_exc("open cas")
            core.speak("Could not open Create a Sim.")

# ---------------------------------------------------------------- describe


def describe(info):
    parts = [core.sim_name(info), _age_name(info.age)]
    try:
        from sims.sim_info_types import Gender
        parts.append("female" if info.gender == Gender.FEMALE else "male")
    except Exception:
        pass
    core.speak(", ".join(parts) + ".")
    # Traits, aspiration and career names are game text, so show them as a list the reader can read.
    rows = []
    try:
        for t in info.trait_tracker.personality_traits:
            rows.append((t.display_name(info), "Trait", None))
    except Exception:
        core.log_exc("describe traits")
    try:
        asp = info.primary_aspiration
        if asp is not None:
            rows.append((asp.display_text, "Aspiration", None))
    except Exception:
        core.log_exc("describe aspiration")
    try:
        for career in info.career_tracker.careers.values():
            title = None
            try:
                title = career.current_level_tuning.get_title(info)
            except Exception:
                title = None
            rows.append((title if title is not None else career.display_name(info), "Career", None))
    except Exception:
        core.log_exc("describe career")
    if rows:
        core.choose("About {}".format(info.first_name), "{}. {}.".format(core.sim_name(info), _age_name(info.age)),
                    rows, lambda v: None, tag="sims")

# ---------------------------------------------------------------- rename


def _rename(info):
    def got_first(first):
        if not first:
            core.speak("Name not changed.")
            return

        def got_last(last):
            info.first_name = first
            if last:
                info.last_name = last
            try:
                info.resend_full_name()
            except Exception:
                pass
            core.speak("Renamed to {}.".format(core.sim_name(info)))
        core.ask_text("Last name", "Type the last name.", info.last_name, got_last)
    core.ask_text("First name", "Type the first name.", info.first_name, got_first)

# ---------------------------------------------------------------- traits


def _edit_traits(info):
    limit = TRAIT_LIMITS.get(info.age.name, 3)
    try:
        current = list(info.trait_tracker.personality_traits)
    except Exception:
        current = []

    def done(chosen):
        for t in current:
            if t not in chosen and info.has_trait(t):
                info.remove_trait(t)
        for t in chosen:
            if not info.has_trait(t):
                info.add_trait(t)
        core.speak("Traits changed. {} has {} new trait{}.".format(
            info.first_name, len(chosen), "" if len(chosen) == 1 else "s"))

    rows = [("Choose new traits", "Replaces all of {}'s current traits. You choose them one at a time.".format(info.first_name), "new")]
    rows.extend((t.display_name(info), "Current trait", None) for t in current)

    def start(value):
        if value == "new":
            pick_traits("New traits for {}".format(info.first_name), info.age, info.gender, limit, info, done)

    core.choose("Traits for {}".format(info.first_name),
                "{} has these traits now. Choose 'Choose new traits' to replace them.".format(info.first_name),
                rows, start, tag="sims")

# ---------------------------------------------------------------- aspiration


def aspiration_tracks(info):
    import services, sims4.resources
    out = []
    for track in services.get_instance_manager(sims4.resources.Types.ASPIRATION_TRACK).types.values():
        try:
            if getattr(track, "is_hidden_unlockable", False):
                continue
            if track.__name__.lower().startswith("ftue"):
                continue    # the tutorial's own aspirations
            if not track.is_available():
                continue
            if not track.is_valid_for_sim(info):
                continue
            out.append(track)
        except Exception:
            continue
    return out


def choose_aspiration(info, then=None):
    tracks = aspiration_tracks(info)
    if not tracks:
        core.speak("There are no aspirations for this age.")
        if then:
            core.post(then)
        return
    rows = []
    current = getattr(info, "primary_aspiration", None)
    tracks.sort(key=lambda t: (getattr(t.category, 'ui_sort_order', 0), t.__name__))
    for track in tracks:
        rows.append((track.display_text, core.with_sim(track.description_text, info), track, track is current))

    def picked(track):
        try:
            old = info.primary_aspiration
            if old is not None and getattr(old, "primary_trait", None) is not None and info.has_trait(old.primary_trait):
                info.remove_trait(old.primary_trait)
            info.primary_aspiration = track
            if getattr(track, "primary_trait", None) is not None and not info.has_trait(track.primary_trait):
                info.add_trait(track.primary_trait)
            core.speak("Aspiration set.")
        except Exception:
            core.log_exc("set aspiration")
            core.speak("Could not set the aspiration.")
        if then:
            core.post(then)

    core.choose("Aspiration for {}".format(info.first_name),
                "An aspiration is a life goal. It gives the Sim goals to work on and rewards.",
                rows, picked, tag="sims", on_cancel=then)

# ---------------------------------------------------------------- new Sim


def start_new():
    import services
    hh = services.active_household()
    if hh is None:
        core.speak("Load a household first.")
        return
    if hh.household_size >= MAX_HOUSEHOLD:
        core.speak("This household already has 8 Sims, the most the game allows.")
        return
    _draft[0] = _Draft()
    rows = [(label, desc, key) for (label, key, desc) in AGE_CHOICES]
    core.choose("New Sim: age", "Step 1 of 5. Choose an age.", rows, _got_age, tag="sims")


def _got_age(key):
    _draft[0].age = _age_enum(key)
    rows = [("Female", None, "FEMALE"), ("Male", None, "MALE")]
    core.choose("New Sim: gender", "Step 2 of 5. Choose a gender.", rows, _got_gender, tag="sims")


def _got_gender(key):
    from sims.sim_info_types import Gender
    _draft[0].gender = getattr(Gender, key)

    def got_first(first):
        if not first:
            core.speak("A first name is needed. Cancelled.")
            return
        _draft[0].first = first
        import services
        hh = services.active_household()
        default_last = ""
        try:
            sim = core.active_sim()
            default_last = sim.sim_info.last_name if sim is not None else (hh.name or "")
        except Exception:
            pass

        def got_last(last):
            _draft[0].last = last or default_last
            _choose_new_traits()
        core.ask_text("New Sim: last name", "Step 4 of 5. Last name.", default_last, got_last)
    core.ask_text("New Sim: first name", "Step 3 of 5. Type the first name.", "", got_first)


def _choose_new_traits():
    d = _draft[0]
    limit = TRAIT_LIMITS.get(d.age.name, 3)
    token = core.active_sim().sim_info

    def done(chosen):
        d.traits = list(chosen)
        core.post(_create)

    pick_traits("New Sim: traits, step 5 of 5", d.age, d.gender, limit, token, done)


def _create():
    import services
    from sims.sim_spawner import SimSpawner, SimCreator
    d = _draft[0]
    hh = services.active_household()
    client = core.client()
    sim = core.active_sim()
    try:
        creator = SimCreator(gender=d.gender, age=d.age, first_name=d.first, last_name=d.last, traits=d.traits)
        (infos, _) = SimSpawner.create_sim_infos([creator], household=hh, tgt_client=client, account=client.account,
                                                 zone_id=services.current_zone_id(),
                                                 creation_source="TS4 Access Plus: new Sim")
        info = infos[0]
        set_exact_traits(info, d.traits)
        position = sim.position if sim is not None else None
        SimSpawner.spawn_sim(info, position)
        client.add_selectable_sim_info(info)
        core.log("created sim {} ({})".format(core.sim_name(info), info.sim_id))
        core.speak("{} has joined the household.".format(core.sim_name(info)))
    except Exception:
        core.log_exc("create sim")
        core.speak("Sorry, the game could not create the Sim.")
        return
    if d.age.name not in ("TODDLER", "INFANT", "BABY"):
        core.post(choose_aspiration, info)
