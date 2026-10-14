# TS4 Access Plus - decorating helpers in the build helper (Alt+B).
# Decorate a room: choose a room, walls or floor, then a pattern from the catalog; it is chosen and
# painted over the whole room in one go. Sell things in a room: tick any number of objects and sell
# them for what they are worth now, the same way TS4 Access's own X key sells (remove + refund).
import threading, time
import tyjokr_a11y_plus_core as core
import tyjokr_a11y_plus_build as build

# part -> (catalog product type, label)
PARTS = {"walls": (7, "Wall patterns, paint and wallpaper"), "floor": (5, "Floor patterns")}


def _say(text):
    core.post(core.speak, text)


def _row_name(obj):
    try:
        label = obj.catalog_name
        from protocolbuffers.Localization_pb2 import LocalizedString
        if not isinstance(label, LocalizedString):
            from sims4.localization import _create_localized_string
            label = _create_localized_string(int(getattr(label, "hash", label)))
        return label
    except Exception:
        return "Object"

# ---------------------------------------------------------------- decorate a room


def decorate_room():
    if not build.in_build_mode():
        core.speak("Go to Build mode first. Press F2, on a laptop Fn+F2.")
        return
    rows = build._room_rows()
    if not rows:
        core.speak("There are no rooms yet.")
        return

    def got_room(room):
        prows = [("Walls", "Paint or wallpaper on every wall inside the room.", "walls"),
                 ("Floor", "Tiles, wood, carpet and more over the whole floor.", "floor")]
        core.choose("Decorate the {}".format(room.name), "What do you want to change?", prows,
                    lambda part: _list_patterns(room, part), tag="build")
    core.choose("Decorate a room", "Choose the room.", rows, got_room, tag="build")


def _list_patterns(room, part):
    if build._busy[0]:
        core.speak("Still working on the last build step.")
        return
    (ptype, label) = PARTS[part]
    core.speak("Getting the {}. Please wait.".format(label.lower()))

    def work():
        items = build.fetch_catalog(ptype, "", "paint" + part)
        if not items:
            _say("The catalog did not answer. Try again in a moment.")
            return
        core.post(_show_patterns, room, part, items)
    threading.Thread(target=work, name="a11yplus_decor_list", daemon=True).start()


def _show_patterns(room, part, items):
    tiles = len(build._room_tiles(room))
    rows = []
    for (i, (name, price, colors)) in enumerate(items):
        desc = "{:,} simoleons a tile".format(price) if price else "Free"
        if price and part == "floor":
            desc += ", about {:,} for this room".format(price * tiles)
        if colors > 1:
            desc += ", {} colors, the first color is used".format(colors)
        rows.append((name, desc + ".", (i, name)))
    core.choose("{} for the {}".format("Walls" if part == "walls" else "Floor", room.name),
                "{} patterns. Enter paints the whole {} with it. You have {:,} simoleons.".format(
                    len(items), "walls of the room" if part == "walls" else "floor", build.funds() or 0),
                rows, lambda v: _paint(room, part, v[0], v[1]), tag="catalog")


def _paint(room, part, index, name):
    if build._busy[0]:
        core.speak("Still working on the last build step.")
        return
    build._busy[0] = True
    core.speak("Painting the {} of the {} with {}. Please wait.".format(part, room.name, name))

    def work():
        try:
            build._cat["silent_select"] = True
            try:
                build.select_item(index, name)
            finally:
                build._cat["silent_select"] = False
            verify = build.on_main(_paint_check, "Painted the {} of the {} with {}".format(part, room.name, name))
            build.set_floor(room.level)
            if part == "walls":
                target = build.wall_point(room, "north")
                ok = build.point_and_act([target], room.level, lambda s: build.click(s[0], shift=True), "decorate walls",
                                         height=0.15, view=build.VIEW_FROM["north"])
            else:
                ok = build.point_and_act([room.center], room.level, lambda s: build.click(s[0], shift=True), "decorate floor")
            if ok and verify is not None:
                time.sleep(0.5)
                core.post(verify)
        except Exception:
            core.log_exc("decorate")
            _say("Sorry, painting failed.")
        finally:
            build._busy[0] = False
    threading.Thread(target=work, name="tyjokr_a11y_plus_decor", daemon=True).start()

def _paint_check(done_text):
    """Like build.cost_check, but painting often costs nothing: the game trades in the old pattern
    at the same price. So no money change and no error from the game still means it was done."""
    before = build.funds()
    started = time.monotonic()

    def verify():
        after = build.funds()
        reason = build._last_error["text"] if build._last_error["at"] > started else ""
        if reason:
            core.speak("Not done. The game says: {}".format(reason))
        elif before is None or after is None or after == before:
            core.speak("{}. No extra cost: the old one was traded in.".format(done_text))
        elif after < before:
            core.speak("{}. It cost {:,} simoleons.".format(done_text, before - after))
        else:
            core.speak("{}. You got {:,} simoleons back for the old one.".format(done_text, after - before))
    return verify

# ---------------------------------------------------------------- sell things in a room


def sell_in_room():
    if not build.in_build_mode():
        core.speak("Go to Build mode first. Press F2, on a laptop Fn+F2.")
        return
    import tyjokr_a11y_plus_rooms as rooms
    all_rooms = rooms.scan_rooms()
    if not all_rooms:
        core.speak("There are no rooms yet.")
        return
    rows = [(r.name, "{}, {} things in it.".format(r.size_text(), len(r.objects)), r) for r in all_rooms]
    core.choose("Sell things", "Choose the room.", rows, _pick_things, tag="build")


_REFUSAL_TEXT = {
    "occupied": "Something is on it or inside it, sell that first",
    "protected": "the game does not allow selling it",
    "foreign": "it belongs to another household",
    "hidden": "it cannot be sold from here",
    "offlot": "it is not on this lot",
}


def _pick_things(room):
    import tyjokr_a11y_place as place
    rows = []
    for obj in room.objects:
        refusal = place.sell_refusal(obj)
        if refusal == "sim":
            continue
        if refusal:
            desc = "Cannot sell: {}.".format(_REFUSAL_TEXT.get(refusal, "not allowed"))
        else:
            desc = "Sells for {:,} simoleons.".format(place._value(obj))
        rows.append((_row_name(obj), desc, obj.id, False, obj))
    if not rows:
        core.speak("There is nothing to sell in the {}.".format(room.name))
        return
    core.choose("Sell things in the {}".format(room.name),
                "{} things. Check each one to sell with Space or Enter, then choose OK.".format(len(rows)),
                rows, lambda ids: _confirm(room, ids), tag="build", multi=len(rows))


def _confirm(room, ids):
    import services
    import tyjokr_a11y_place as place
    objs = [services.object_manager().get(i) for i in ids]
    objs = [o for o in objs if o is not None and not place.sell_refusal(o)]
    if not objs:
        core.speak("Nothing chosen that can be sold.")
        return
    total = sum(place._value(o) for o in objs)
    what = "1 thing" if len(objs) == 1 else "{} things".format(len(objs))
    rows = [("Yes, sell {} for {:,} simoleons".format(what, total), None, True),
            ("No, keep everything", None, False)]
    core.choose("Sell?", "Sell {} from the {} for {:,} simoleons?".format(what, room.name, total), rows,
                lambda yes: _sell(room, [o.id for o in objs]) if yes else core.speak("Nothing sold."), tag="build")


def _sell(room, ids):
    import services
    import tyjokr_a11y_place as place
    place.settle_owed()
    sold, failed, money = 0, [], 0
    before = build.funds() or 0
    for oid in ids:
        obj = services.object_manager().get(oid)
        if obj is None:
            continue
        if place.sell_refusal(obj):
            failed.append(oid)
            continue
        value = place._value(obj)
        if not place._destroy(obj):
            failed.append(oid)
            continue
        place._refund(value)
        if place._last.get("obj_id") == oid:
            place._last["obj_id"] = None
        sold += 1
        money += value
    got = (build.funds() or 0) - before
    text = "Sold {} {} from the {}. You got {:,} simoleons back.".format(
        sold, "thing" if sold == 1 else "things", room.name, max(got, 0))
    if got < money:
        text += " {:,} more will come back with your next build action.".format(money - max(got, 0))
    if failed:
        text += " {} could not be sold: something may be on it or using it.".format(len(failed))
    core.log("sell: {} in {}: {} sold, {} expected, {} received, failed {}".format(ids, room.name, sold, money, got, failed))
    core.speak(text)
