# TS4 Access Plus - start a brand-new family from the keyboard (Alt+C, "Start a brand-new family").
# You make 1 to 8 Sims (age, gender, name, traits, aspiration, how they are related), choose an empty
# lot or a house, and the game moves the new family in and switches to playing them, the same way the
# game's own "split household" does. The family you were playing stays in the town.
import tyjokr_a11y_plus_core as core
import tyjokr_a11y_plus_sims as sims

STARTING_FUNDS = 20000      # what Create a Sim gives every new household
GROWN_UPS = ("YOUNGADULT", "ADULT", "ELDER")
AGE_ORDER = ("TODDLER", "CHILD", "TEEN", "YOUNGADULT", "ADULT", "ELDER")


class _Member(object):
    def __init__(self):
        self.age = None
        self.gender = None
        self.first = ""
        self.traits = []
        self.aspiration = None
        self.relation = None        # (kind, index of the earlier member) or None


class _Family(object):
    def __init__(self):
        self.last = ""
        self.members = []
        self.zone_id = None
        self.lot = None


_family = [None]


def _age_label(age):
    return sims._age_name(age)


def _gender_word(m):
    from sims.sim_info_types import Gender
    return "female" if m.gender == Gender.FEMALE else "male"


def _member_line(m):
    return "{} {}, {} {}".format(m.first, _family[0].last, _age_label(m.age), _gender_word(m))


def _age_rank(age):
    return AGE_ORDER.index(age.name)

# ---------------------------------------------------------------- start


def start():
    import services
    if services.active_household() is None or core.active_sim() is None:
        core.speak("Load a game first. Any family will do, your new family gets its own home.")
        return
    rows = [
        ("Start", "Step 1: the family name. Step 2: make each Sim. Step 3: choose a home. "
                  "Nothing changes in the game until you confirm the move at the end.", "go"),
        ("Cancel", None, None),
    ]
    core.choose("Start a brand-new family",
                "You make 1 to 8 new Sims and choose an empty lot to build on, or a house. "
                "The family gets {} simoleons, like in Create a Sim. Then the game switches to your new family. "
                "The family you are playing now stays in the town.".format(STARTING_FUNDS),
                rows, _started, tag="family")


def _started(value):
    if value != "go":
        return
    _family[0] = _Family()

    def got_last(last):
        if not last:
            core.speak("A family name is needed. Cancelled.")
            return
        _family[0].last = last
        core.post(_new_member)
    core.ask_text("Family name", "Type the family's last name, for example Smith.", "", got_last)

# ---------------------------------------------------------------- one member


def _new_member():
    fam = _family[0]
    n = len(fam.members) + 1
    if n == 1:
        choices = [c for c in sims.AGE_CHOICES if c[1] in GROWN_UPS]
        text = "Sim 1. Choose an age. The first Sim must be a young adult or older, to look after the home."
    else:
        choices = list(sims.AGE_CHOICES)
        text = "Sim {}. Choose an age.".format(n)
    rows = [(label, desc, key) for (label, key, desc) in choices]
    core.choose("Sim {}: age".format(n), text, rows, _got_age, tag="family", on_cancel=_family_menu if n > 1 else None)


def _got_age(key):
    m = _Member()
    m.age = sims._age_enum(key)
    _family[0].members.append(m)
    rows = [("Female", None, "FEMALE"), ("Male", None, "MALE")]
    core.choose("Sim {}: gender".format(len(_family[0].members)), "Choose a gender.", rows, _got_gender,
                tag="family", on_cancel=_drop_last)


def _drop_last():
    if _family[0].members:
        _family[0].members.pop()
    core.speak("That Sim was not added.")
    if _family[0].members:
        core.post(_family_menu)


def _got_gender(key):
    from sims.sim_info_types import Gender
    fam = _family[0]
    m = fam.members[-1]
    m.gender = getattr(Gender, key)

    def got_first(first):
        if not first:
            core.post(_drop_last)
            return
        m.first = first
        core.post(_choose_traits)
    core.ask_text("Sim {}: first name".format(len(fam.members)), "Type the first name.", "", got_first)


def _choose_traits():
    m = _family[0].members[-1]
    limit = sims.TRAIT_LIMITS.get(m.age.name, 3)
    token = core.active_sim().sim_info

    def done(chosen):
        m.traits = list(chosen)
        core.post(_choose_aspiration)

    sims.pick_traits("{}: traits".format(m.first), m.age, m.gender, limit, token, done)


def _choose_aspiration():
    m = _family[0].members[-1]
    if m.age.name == "TODDLER":
        core.post(_choose_relation)
        return
    tracks = sims.aspiration_tracks(sims._Fake(m.age, m.gender))
    if not tracks:
        core.post(_choose_relation)
        return
    tracks.sort(key=lambda t: (getattr(t.category, 'ui_sort_order', 0), t.__name__))
    token = core.active_sim().sim_info
    rows = [(t.display_text, core.with_sim(t.description_text, token), t) for t in tracks]

    def picked(track):
        m.aspiration = track
        core.post(_choose_relation)

    core.choose("{}: aspiration".format(m.first),
                "An aspiration is a life goal. It gives the Sim goals to work on and rewards. Escape skips it.",
                rows, picked, tag="family", on_cancel=_choose_relation)


def _relation_options(new, old_index):
    """What the new Sim can be to an earlier Sim, as (label, kind)."""
    old = _family[0].members[old_index]
    out = []
    grown = ("YOUNGADULT", "ADULT", "ELDER")
    if new.age.name in grown and old.age.name in grown:
        out.append(("Spouse, married to {}".format(old.first), "spouse"))
    if _age_rank(new.age) < _age_rank(old.age) and old.age.name in grown:
        out.append(("Child of {}".format(old.first), "child"))
    if _age_rank(new.age) > _age_rank(old.age) and new.age.name in grown:
        out.append(("Parent of {}".format(old.first), "parent"))
    out.append(("Brother or sister of {}".format(old.first), "sibling"))
    return out


def _is_married(i):
    fam = _family[0]
    for (k, x) in enumerate(fam.members[:-1]):
        if x.relation and x.relation[0] == "spouse" and i in (k, x.relation[1]):
            return True
    return False


def _choose_relation():
    fam = _family[0]
    m = fam.members[-1]
    if len(fam.members) == 1:
        core.post(_member_done)
        return
    rows = [("No family tie, a roommate", "Lives in the house but is not related.", None)]
    for i in range(len(fam.members) - 1):
        for (label, kind) in _relation_options(m, i):
            if kind == "spouse" and _is_married(i):
                continue
            rows.append((label, None, (kind, i)))

    def picked(value):
        m.relation = value
        core.post(_member_done)

    core.choose("{}: family tie".format(m.first),
                "How is {} related to the family? Choose one.".format(m.first),
                rows, picked, tag="family", on_cancel=_member_done)


def _member_done():
    m = _family[0].members[-1]
    core.speak("{} added.".format(_member_line(m)))
    core.post(_family_menu)

# ---------------------------------------------------------------- family menu


def _family_menu():
    fam = _family[0]
    n = len(fam.members)
    rows = []
    if n < sims.MAX_HOUSEHOLD:
        rows.append(("Add another Sim", "The family has {} Sim{} now. A family can have up to 8.".format(n, "" if n == 1 else "s"), "add"))
    rows.append(("Done, choose a home", "Choose an empty lot to build on, or a house.", "home"))
    rows.append(("Hear the family", "Everyone you have made so far.", "list"))
    if n > 1:
        rows.append(("Remove the last Sim, {}".format(fam.members[-1].first), None, "drop"))
    rows.append(("Cancel the whole family", "Nothing is changed in the game.", "cancel"))
    core.choose("The {} family".format(fam.last), "{} Sim{} so far. What next?".format(n, "" if n == 1 else "s"),
                rows, _family_pick, tag="family", on_cancel=_family_cancelled)


def _family_cancelled():
    core.speak("Family menu closed. Your Sims are kept until you start a new family. Press Alt+C and choose Continue the new family.")


def _family_pick(value):
    fam = _family[0]
    if value == "add":
        _new_member()
    elif value == "home":
        _choose_lot_kind()
    elif value == "list":
        _speak_family()
        core.post(_family_menu)
    elif value == "drop":
        gone = fam.members.pop()
        for m in fam.members:
            if m.relation and m.relation[1] >= len(fam.members):
                m.relation = None
        core.speak("{} removed.".format(gone.first))
        core.post(_family_menu)
    elif value == "cancel":
        _family[0] = None
        core.speak("New family cancelled. Nothing was changed.")


def _relation_text(m):
    if not m.relation:
        return ""
    (kind, i) = m.relation
    other = _family[0].members[i].first
    return {"spouse": ", married to {}", "child": ", child of {}", "parent": ", parent of {}",
            "sibling": ", brother or sister of {}"}[kind].format(other)


def _speak_family():
    fam = _family[0]
    core.speak("The {} family: ".format(fam.last) + ". ".join(_member_line(m) + _relation_text(m) for m in fam.members) + ".")


def has_draft():
    return _family[0] is not None and bool(_family[0].members)


def resume():
    if has_draft():
        _family_menu()
    else:
        start()

# ---------------------------------------------------------------- lots


def _regions():
    table = {}
    try:
        from ui.ui_tuning import UiTuning
        from world.region import Region
        for pack_data in UiTuning.PACK_SPECIFIC_DATA.values():
            for region_data in getattr(pack_data, "region_list", ()) or ():
                inst = Region.REGION_DESCRIPTION_TUNING_MAP.get(region_data.region_resource)
                if inst is not None:
                    table[inst] = bool(getattr(region_data, "is_player_facing", True))
    except Exception:
        core.log_exc("regions")
    return table


# Lot prices only live in the game's interface. TS4 Access can ask it for a lot's rental price
# (land + house + furniture, times a fixed rate); we ask for that and turn it back into the buying price.
_prices = {}        # zone_id -> buying price, about
_price_wait = []    # [deadline, zone ids, callback]
_hooked = [False]


def _hook_prices():
    if _hooked[0]:
        return True
    try:
        import sims4.commands, tyjokr_a11y_travel as travel
        original = travel.a11y_lotprice_enc

        @sims4.commands.Command("a11y.lotprice_enc", command_type=sims4.commands.CommandType.Live)
        def a11yplus_lotprice_enc(payload: str = "", _connection=None):
            try:
                (zone, value, generation) = str(payload).split("|")
                if generation == "424242":
                    _got_price(int(zone), float(value))
                    return True
            except Exception:
                pass
            return original(payload, _connection=_connection)

        _hooked[0] = True
        return True
    except Exception:
        core.log_exc("price hook")
        return False


def _got_price(zone_id, rental):
    try:
        from world.rentable_lot_tuning import RentableZoneTuning
        m = RentableZoneTuning.PRICE_MODIFIERS
        if rental <= 0 or not m.multiply:
            return
        # The interface rounds the rental price down, so the true value is up to one simoleon higher.
        total = (rental + 0.5 - m.add) / m.multiply
        _prices[zone_id] = int(round(total / 10.0)) * 10
    except Exception:
        core.log_exc("price")


def _ask_prices(zone_ids, then):
    import time, distributor.ops, distributor.system
    if not _hook_prices():
        core.post(then)
        return
    for z in zone_ids:
        if z not in _prices:
            distributor.system.Distributor.instance().add_op_with_no_owner(
                distributor.ops.SendUIMessage("A11y|lotprice|{}|424242".format(z)))
    _price_wait[:] = [time.monotonic() + 3.0, list(zone_ids), then]


def _price_tick():
    if not _price_wait:
        return
    import time
    (deadline, zones, then) = _price_wait
    if time.monotonic() >= deadline or all(z in _prices for z in zones):
        del _price_wait[:]
        then()


core.add_ticker(0.3, _price_tick)


def free_lots():
    """Every residential lot nobody lives on: dicts with zone_id, name, world, empty, rooms, price."""
    import services
    from world import region
    persistence = services.get_persistence_service()
    regions = _regions()
    current = services.current_zone_id()
    worlds = {}
    out = []
    for zone in persistence.zone_proto_buffs_gen():
        try:
            zone_id = zone.zone_id
            if zone_id == current or zone.household_id:
                continue
            venue = services.venue_service().get_venue_tuning(zone_id)
            if venue is None or not venue.is_residential:
                continue
            reg = region.get_region_instance_from_zone_id(zone_id)
            if reg is not None and regions.get(reg) is False:
                continue
            try:
                if services.get_plex_service().is_zone_a_plex(zone_id):
                    continue
            except Exception:
                pass
            nid = zone.neighborhood_id
            if nid not in worlds:
                try:
                    worlds[nid] = str(persistence.get_neighborhood_proto_buff(nid).name or "")
                except Exception:
                    worlds[nid] = ""
            beds, baths = int(zone.bedroom_count), int(zone.bathroom_count)
            out.append({"zone_id": zone_id, "name": str(zone.name or "Unnamed lot"), "world": worlds[nid] or "Other town",
                        "beds": beds, "baths": baths, "empty": beds == 0 and baths == 0,
                        "price": _prices.get(zone_id)})
        except Exception:
            core.log_exc("free lot")
    return out


def _choose_lot_kind():
    rows = [("Empty lots, build your own house", "Cheap land with nothing on it. You build the house in Build mode with Alt+B.", True),
            ("Houses ready to live in", "A built and furnished house. Costs more.", False)]
    core.choose("Choose a home", "The family has {} simoleons to spend.".format(STARTING_FUNDS), rows, _choose_lot,
                tag="family", on_cancel=_family_menu)


def _lot_label(lot):
    rooms = "" if lot["empty"] else " {} bedroom{}, {} bathroom{}.".format(
        lot["beds"], "" if lot["beds"] == 1 else "s", lot["baths"], "" if lot["baths"] == 1 else "s")
    price = "about {} simoleons".format(lot["price"]) if lot["price"] is not None else "price unknown"
    return "{}, {}.{} {}".format(lot["name"], lot["world"], rooms, price)


def _choose_lot(empty):
    try:
        lots = [l for l in free_lots() if l["empty"] == empty]
    except Exception:
        core.log_exc("free lots")
        lots = []
    if lots and any(l["price"] is None for l in lots) and not _price_wait:
        core.speak("Getting prices.")
        _ask_prices([l["zone_id"] for l in lots], lambda: _choose_lot(empty))
        return
    lots.sort(key=lambda l: (l["world"], l["price"] if l["price"] is not None else 10 ** 9))
    if not lots:
        core.speak("There are no free {} in this game.".format("empty lots" if empty else "houses"))
        core.post(_choose_lot_kind)
        return
    rows = []
    for lot in lots:
        price = lot["price"] or 0
        if lot["price"] is None:
            desc = "The price could not be found."
        elif price > STARTING_FUNDS:
            desc = "Too expensive, the family has {} simoleons.".format(STARTING_FUNDS)
        else:
            desc = "{} simoleons left after buying.".format(STARTING_FUNDS - price)
        rows.append((_lot_label(lot), desc, lot))
    core.choose("Empty lots" if empty else "Houses",
                "{} free. Sorted by town, cheapest first.".format(len(lots)), rows, _picked_lot,
                tag="family", on_cancel=_choose_lot_kind)


def _picked_lot(lot):
    fam = _family[0]
    price = lot["price"] or 0
    if lot["price"] is None:
        core.speak("The price of that lot could not be found. Choose another one.")
        core.post(_choose_lot, lot["empty"])
        return
    if price > STARTING_FUNDS:
        core.speak("The family cannot afford that one.")
        core.post(_choose_lot, lot["empty"])
        return
    fam.lot = lot
    rows = [("Yes, move in and play the {} family".format(fam.last),
             "The game loads the new home. This takes a minute, like any trip.", "yes"),
            ("No, choose another home", None, "no")]
    core.choose("Move in?", "Move the {} family, {} Sim{}, to {} in {} for {} simoleons. They keep {} simoleons.".format(
        fam.last, len(fam.members), "" if len(fam.members) == 1 else "s", lot["name"], lot["world"], price,
        STARTING_FUNDS - price), rows, _confirmed, tag="family", on_cancel=_choose_lot_kind)


def _confirmed(value):
    if value != "yes":
        _choose_lot_kind()
        return
    try:
        _create_and_move()
    except Exception:
        core.log_exc("create family")
        core.speak("Sorry, something went wrong making the family. Nothing was moved. Send the TS4_Access_Plus.log file from the Mods folder for help.")

# ---------------------------------------------------------------- create, move in, play


def _create_and_move():
    import services, distributor.ops, distributor.system
    from sims.sim_spawner import SimSpawner, SimCreator
    fam = _family[0]
    lot = fam.lot
    zone_id = lot["zone_id"]
    client = core.client()
    funds = STARTING_FUNDS - (lot["price"] or 0)
    creators = [SimCreator(gender=m.gender, age=m.age, first_name=m.first, last_name=fam.last, traits=m.traits)
                for m in fam.members]
    (infos, household) = SimSpawner.create_sim_infos(creators, starting_funds=funds, account=client.account,
                                                     zone_id=zone_id, family_name=fam.last,
                                                     creation_source="TS4 Access Plus: new family")
    core.log("new family {} household {} sims {}".format(fam.last, household.id, [i.sim_id for i in infos]))
    try:
        household.name = fam.last
    except Exception:
        core.log_exc("family name")
    for (m, info) in zip(fam.members, infos):
        sims.set_exact_traits(info, m.traits)
        if m.aspiration is not None:
            try:
                info.primary_aspiration = m.aspiration
                trait = getattr(m.aspiration, "primary_trait", None)
                if trait is not None and not info.has_trait(trait):
                    info.add_trait(trait)
            except Exception:
                core.log_exc("aspiration " + m.first)
    _set_relations(fam, infos)
    try:
        household.set_default_relationships()
    except Exception:
        core.log_exc("default relationships")
    for info in infos:
        try:
            info.genealogy.validate_grandparent_relations()
        except Exception:
            pass
    try:
        household.set_played_household(True)
    except Exception:
        core.log_exc("played household")
    household.move_into_zone(zone_id)
    core.log("moved household {} into zone {}".format(household.id, zone_id))
    core.speak("The {} family is moving in to {}. Loading the new home, please wait.".format(fam.last, lot["name"]))
    _arrival[:] = [household.id, zone_id, lot["price"] or 0, lot["empty"]]
    op = distributor.ops.TravelLiveToNhdToLive(infos[0].sim_id, household.id, 0)
    distributor.system.Distributor.instance().add_op_with_no_owner(op)
    _family[0] = None


def _set_relations(fam, infos):
    from sims.genealogy_tracker import FamilyRelationshipIndex
    from sims.sim_info_types import Gender
    from relationships.global_relationship_tuning import RelationshipGlobalTuning
    for (i, m) in enumerate(fam.members):
        if not m.relation:
            continue
        (kind, j) = m.relation
        me, other = infos[i], infos[j]
        try:
            if kind == "spouse":
                me.update_spouse_sim_id(other.id)
                other.update_spouse_sim_id(me.id)
                bit = RelationshipGlobalTuning.MARRIAGE_RELATIONSHIP_BIT
                me.relationship_tracker.add_relationship_bit(other.id, bit, force_add=True)
                other.relationship_tracker.add_relationship_bit(me.id, bit, force_add=True)
            elif kind in ("child", "parent"):
                (parent, child) = (other, me) if kind == "child" else (me, other)
                rel = FamilyRelationshipIndex.MOTHER if parent.gender == Gender.FEMALE else FamilyRelationshipIndex.FATHER
                child.set_parent_relation(rel, parent)
                spouse_id = parent.spouse_sim_id
                spouse = next((x for x in infos if x.id == spouse_id), None)
                if spouse is not None:
                    rel2 = FamilyRelationshipIndex.MOTHER if spouse.gender == Gender.FEMALE else FamilyRelationshipIndex.FATHER
                    if rel2 != rel:
                        child.set_parent_relation(rel2, spouse)
            elif kind == "sibling":
                shared = False
                for rel in (FamilyRelationshipIndex.MOTHER, FamilyRelationshipIndex.FATHER):
                    pid = other.genealogy.get_parent_relation(rel)
                    parent = next((x for x in infos if x.id == pid), None) if pid else None
                    if parent is not None:
                        me.set_parent_relation(rel, parent)
                        shared = True
                if not shared:
                    me.genealogy.set_parent_of_parentless_siblings(other)
        except Exception:
            core.log_exc("relation {} {}".format(kind, m.first))
    # A child of one married parent is also the child of the other parent.
    for child in infos:
        try:
            for rel in (FamilyRelationshipIndex.MOTHER, FamilyRelationshipIndex.FATHER):
                pid = child.genealogy.get_parent_relation(rel)
                parent = next((x for x in infos if x.id == pid), None) if pid else None
                spouse = next((x for x in infos if parent is not None and x.id == parent.spouse_sim_id), None)
                if spouse is None:
                    continue
                rel2 = FamilyRelationshipIndex.MOTHER if spouse.gender == Gender.FEMALE else FamilyRelationshipIndex.FATHER
                if rel2 != rel and child.genealogy.get_parent_relation(rel2) is None:
                    child.set_parent_relation(rel2, spouse)
        except Exception:
            core.log_exc("second parent")


# ---------------------------------------------------------------- arrival

_arrival = []       # [household id, zone id, price paid, empty lot]
# (The loaded lot's own value leaves out the land, so the price paid stays the estimate.)


@core.on_zone_started
def _arrived():
    if not _arrival:
        return
    import services
    (household_id, zone_id, paid, empty) = _arrival
    if services.current_zone_id() != zone_id:
        return
    del _arrival[:]
    household = services.household_manager().get(household_id)
    if household is None:
        return
    try:
        money = int(household.funds.money)
    except Exception:
        money = 0
    size = ""
    try:
        lot = services.active_lot()
        size = " It is {} by {} meters.".format(int(lot.size_x), int(lot.size_z))
    except Exception:
        pass
    if empty:
        tip = "The lot is empty." + size + " Press F2 for Build mode, then Alt+B for the build helper. A good start is Catalog, Furnished rooms."
    else:
        tip = "Press Alt+R to hear the rooms of your new house."
    core.speak("Welcome home, {} family. You have {} simoleons. {}".format(household.name, money, tip))
