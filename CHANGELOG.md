# Sims 4 Access changelog

Built and tested against **The Sims 4 game version 1.127.41.1030**.

---

## Build 2026-09-09 — the mod is called Sims 4 Access

**The archive is now `Sims4Access.ts4script`.** Delete
`a11yscan_Companion.ts4script` from your Mods folder or the game loads both
copies of the mod.

Python modules keep the `a11yscan_` prefix and commands keep `a11y2.*`. That
prefix is a namespace rather than a name, and it is also the reload system's
marker, the Mods-folder marker and part of the log path - renaming it would
move three load-bearing things for no visible gain.

**New this build**

* **Ctrl+Shift+R** reads relationships: everyone your Sim knows, closest first,
  with the headline ("Good Friends"), friendship and romance as a word and a
  number, and Enter for the full profile including what your Sim has learned
  about them.
* **Event progress reads itself.** While an event runs, anything that changes
  is spoken - a goal finishing, a counted goal advancing ("3 of 5"), a medal
  reached, the event ending. Ctrl+Shift+P asks at any time and now reports
  progress instead of opening the planner when an event is running. Goals say
  what they are worth, so "how do I earn points" is answerable from the list.
  `a11y2.eventwatch off` stops the automatic reading; `a11y2.endevent` ends an
  event early, keeping the score you earned.
* **Lot type changing.** `a11y2.venue` lists every venue type this install has
  and says which ones the lot lacks objects for; `a11y2.venue library` sets it.
  Empty lots become real destinations without buying a pack.
* **Getting onto a lot without sighted help.** Ctrl+Alt+O now knows three
  states, not two: the main menu picks a save, the world screen picks a FAMILY
  and loads their lot, and in game it switches household. Ctrl+Alt+W works with
  no lot loaded and says what to press next.
* **`tools/setup.py`** enables script mods from outside the game, since that
  switch lives behind an unreadable options screen.
* **`companion/`** - a separate desktop program for screens with no data behind
  them. `click_text.py Done` finds a button by its word and clicks it, which is
  the only way past the age-up panel.
* **Build mode diagnostics.** `a11y2.whybuild` checks ownership, venue type,
  home zone, the game's residence test, situation locks, open dialogs and the
  venue owner, and names the one that is wrong. `a11y2.claimlot` repairs a lot
  whose deed never transferred.
* Notification stings that arrive with no owner are played on the active Sim
  instead of nothing, which is why some notification sounds had gone silent.

**Fixed**

* Catalog entries collapsed far too aggressively: `get_variant_group_id` groups
  product families, not colour swatches, so 22,541 objects became 3,966 and
  items surfaced under the wrong category. The name and price decide again.
* Event goals always read "not yet": `get_goal_info` returns `(goal, None)` and
  the `None` is not a completion flag.
* `set_household_lot_ownership` takes `zone_id` as a keyword; passing it
  positionally meant the call never ran.
* Duplicate menu entries throughout - shops, pickers, the look editor.

---

## Build 2026-09-07b — speech moves to Prism

**Speech now goes through [Prism](https://github.com/ethindp/prism)**, a
screen-reader bridge, and the mod's own NVDA controller client is gone.

For testers, the install list has changed — **`prism.dll` replaces
`a11yscan_nvdaControllerClient64.dll`**. Delete the old file; four files still
go in Mods:

    a11yscan_Companion.ts4script
    a11yscan_names.bin
    a11yscan_objects.bin
    prism.dll

Nothing should sound different. Prism asks for whichever reader is actually
running and speaks through it at your own voice and rate. What changes is
reach: one code path now covers NVDA, JAWS, SAPI, OneCore and UIA on Windows,
VoiceOver on macOS, and Orca or speech-dispatcher on Linux, instead of NVDA
alone.

`a11y2.diag` reports which reader it found — expect
`prism: OK, speaking through NVDA`.

**For developers.** Prism publishes no binaries, so `prism.dll` here is built
from source (CMake, MSVC x64, all backends compiled into one library). The
binding is plain ctypes against the C API, which is UTF-8 `char*` with the
default calling convention — `CDLL` on every platform, never `WinDLL`:

```c
PrismConfig   prism_config_init(void);            /* returned BY VALUE, 48 bytes */
PrismContext *prism_init(PrismConfig *cfg);
PrismBackend *prism_registry_acquire_best(PrismContext *ctx);  /* the running reader */
PrismError    prism_backend_speak(PrismBackend *b, const char *utf8, bool interrupt);
```

Two things worth knowing before you copy this. `prism_registry_acquire_best`
**already initialises** the backend, so `prism_backend_initialize` then returns
`PRISM_ERROR_ALREADY_INITIALIZED` (15) on a perfectly good one — treat that as
success. And the header does not document how to obtain a backend at all; the
exported symbol list from the built DLL is what settled it.

macOS and Linux need their own `libprism.dylib` / `libprism.so` built the same
way and dropped in Mods beside the mod. The packager installs whatever is in
`native/`.

The keyboard layer is now platform-dispatched too, with a macOS CoreGraphics
path written but untested — see the previous entry's notes on key codes,
the missing press latch, and Accessibility permission.

---

## Build 2026-09-07

The headline is travel without the map screen, an event planner, moving house,
and a build mode that tells you where things can actually go. The rest is
mostly bugs — several of them mine, and a few had been quietly breaking things
for a while.

### For testers

**New keys**

    Ctrl+Shift+T        travel without the map screen (companions included)
    Ctrl+Shift+P        plan a social event
    Ctrl+Shift+H        move house, or move in with someone
    Ctrl+Shift+D        sell what you are pointed at (press twice)
    Ctrl+Shift+O        aspiration, its description, and the goals left
    Ctrl+Shift+Enter    centre the camera on the lot

**One key moved.** Needs is now **Ctrl+Shift+N**, not Ctrl+Alt+N — that starts
NVDA, so the mod was fighting the screen reader for it.

**Travel, without the map.** Ctrl+Shift+T lists every destination and travels
directly. Household Sims and anyone else on the lot appear first in the list as
companions you can bring. The old map route is still on Ctrl+Shift+Home if you
want it, but the map screen cannot be closed once it opens, so the new route is
the better one.

**Moving house.** Ctrl+Shift+H lists every lot with its bedroom and bathroom
count, empty ones first, and moves you there in one step. The same menu offers
moving in with a Sim who is on your lot — their household merges into yours,
bringing their Sims and their money, and you choose whose home to keep.

**Planning an event.** Ctrl+Shift+P walks the whole flow as a list: which
event, where, who to invite, and which activities. Each event reads out its
cost, its goal and its description before you commit. Required and recommended
activities are ticked for you.

**Build mode.**

* The tile grid now says whether building somewhere will get in a Sim's way —
  *"a walkway between north and south, building here will block the way
  through"*, *"a tight corner, good place to build"*. Press Enter on a tile for
  the clearance in each direction.
* The game now chooses the exact spot. You point roughly and it places the
  object somewhere it actually fits.
* Objects that need a desk or a wall say so **in the catalog**, before you buy.
* Ctrl+Shift+D sells what you are pointed at, refunding the money. Two presses,
  because it cannot be undone.

**Names.** Objects that used to read as "object" now read properly, including
content from mods you install later — the mod reads the game's own string
tables at runtime rather than a table baked in when it was packaged.

**Buy catalog.** Now carries all 22,500-odd items instead of the first 4,000,
grouped the way buy mode groups them ("furniture, sofas", "plumbing and
appliances, refrigerators").

**Cheats menu (Ctrl+Alt+V)** gained: skill sliders for every skill, relationship
sliders per Sim, send visitors home, remove visitors, unstick a Sim, clear the
queue, per-Sim autonomy, clear trash that jams routing, end a situation, and two
diagnostics — *"Why will my Sim not do anything"* and *"Why will this object not
work"*.

**Reliability.** New builds now load themselves; no more Ctrl+Alt+F5 after every
update. If the mod stops responding it reloads itself rather than needing the
game restarted.

### Fixed

* **Commands were being sabotaged.** Cancelling a Sim's current activity before
  issuing an order made the game queue its own "stop and stand up" interaction
  at high priority, which displaced the very command being issued. Told-to
  interactions never reached the queue at all. This broke showers, computers and
  much else.
* **Placed objects were never registered** with the build/buy system, so Sims
  would not use anything you built. There is a menu action to fix furniture
  placed before this build.
* **Surface objects went onto the wrong furniture** — a computer onto a patio
  table, another onto a lamp. Surfaces are now ranked, desks and tables first.
* Purchases were booked as a money cheat rather than a purchase.
* Filling one Sim's needs never worked, so needs quietly stayed low.
* Clear all moodlets, make friends with everyone, and age up and down were all
  failing silently for the same reason.
* Skill sliders listed nothing; toddler and child skills were offered to adults.
* Age-up and other text-input dialogs could not be answered, and can now be
  typed into as well.
* The aspiration readout named the track and nothing else.
* Trash that Sims cannot pick up jams routing on a lot; there is now a cheat to
  clear it.

### Known not working

* The **map screen will not close** after travelling. Responses, the client's
  own close message and a synthesized Escape were all tried and all ignored.
  Use Ctrl+Shift+T instead, which never opens it.
* **Cook Together** offers the Sim picker and then no recipe step.
* Slot placement onto a desk is new and lightly tested.
* Move-in-together and the event planner are new and untested by anyone.

---

## For developers

The mod's rule: **don't read the UI, rebuild it from the data the UI is drawn
from.** What follows is what that turned up this round, because most of it is
not documented anywhere.

### Travel does not work the way it looks

`TravelSuperInteraction` does not travel. Its whole body is:

```python
if not services.get_persistence_service().is_save_locked():
    self.show_travel_dialog()
    services.game_clock_service().set_clock_speed(ClockSpeedMode.PAUSED)
```

It opens the map. The map picker does not travel either — on confirm it runs
`MapViewPickerInteraction._push_continuations`:

```python
self.interaction_parameters['picked_zone_ids'] = frozenset(picked)
self.push_tunable_continuation(self.actor_continuation, picked_zone_ids=picked)
```

The **continuation** travels, and the destination reaches it as an ordinary
interaction parameter. Those continuations are readable from any tuned map
picker in the interaction manager, so travel works without a screen:

```python
for affordance in manager.types.values():
    if issubclass(affordance, MapViewPickerInteraction):
        for entry in affordance.actor_continuation:
            sim.push_super_affordance(entry.affordance, sim, context,
                                      picked_zone_ids=frozenset((zone_id,)),
                                      picked_item_ids=frozenset(companions))
```

Rank them: they all travel, but "ask on date" also starts a date and "invite to"
brings people along. `travel_solo_mapPicker` is the plain one.

Pushing `TravelSuperInteraction` directly fails two ways, both dead ends:
`target=sim` gives *"Cannot Travel from terrain outside of the street"* (the
position comes from the target, and a Sim on a lot is never in the street), and
`target=None` raises `'tuple' object has no attribute 'get'` inside the
interaction.

### Native calls whose argument types are not what you would guess

* `build_buy.add_object_to_buildbuy_system(obj.id)` — the **id**, not the
  object. Passing the object fails silently and Sims will not use what you
  placed.
* Optional-target commands (`set_commodities_to_best_values`,
  `remove_all_buffs`, `make_all_sims_friends`, `advance_to_next_age`) want
  `None` and resolve the active Sim themselves. Passing a Sim raises
  `'object_sim' object has no attribute '_get_target'`.
* `create_situation_with_guest_list(situation_type, ...)` wants the situation
  **class**; the console decorator converts a name for you, calling it directly
  does not. Its guest list is loose `*args` in threes: job, sim, purpose.
* `household.funds.try_remove(amount, reason_int, sim)` — a reason **code** from
  `Consts_pb2`, and which one matters: `FUNDS_MONEY_CHEAT` is not a purchase.

### Reading things the UI shows

* Object names: `build_buy.get_object_catalog_name(definition_id)` gives the
  STBL key the client resolves. Runtime string tables come from
  `sims4.resources.list(type=0x220557DA)` and `sims4.resources.load(key)`, which
  covers content mods installed after packaging.
* Buy-mode structure lives in `BuyCat` tags, not `Func_` — `Func_` is 2,214
  mostly-gameplay tags. `BuyCatSS/EE/LD/PA_*` are the four catalog groups.
* Aspirations: `AspirationTrack.display_text` (not `display_name`),
  `track.get_aspirations()` returns **(key, aspiration) pairs**, milestone goals
  are in `objectives`, and completion is `tracker.completed_objectives`.
* Placement requirements: `build_buy.get_object_placement_flags(definition_id)`
  against `PlacementFlags`; `REQUIRES_SLOT` means it belongs on a surface.
* Pathing: `routing.test_point_placement_in_navmesh(context, location)` per
  tile; `placement.find_good_location(context)` for "where should this go".

### Dialogs

* `dialog.respond(response)` ends with `self._listeners(self)`, which is what
  runs a picker's `_on_picker_selected` and pushes its continuation. Answering
  server-side does fire it.
* `get_result_rows()` is `[row for row in picker_rows if row.option_id in
  picked_results]`, so set `dialog.picked_results` before responding.
* `RuntimeSlot.empty`, `.is_deco_slot` and `.is_valid_for_placement` are
  **properties**. Calling them raises, and a swallowed exception makes every
  slot look unusable.
* Text-input dialogs ignore their buttons until every field has been sent via
  `on_text_input`.
* Responding does **not** close a client panel. `UiDialogCloseRequest` over
  `MSG_UI_DIALOG_CLOSE` is what the game sends, and even that does not close the
  map view.

### The rule that keeps being relearned

Verify by effect, not by return value. Almost every bug this round reported
success: placements charged but unregistered, situations "asked to leave" that
stayed, a trash clear counted in the same tick as the deferred destroy, an
autonomy hold that released mid-shower because the test counted the shower
itself as idle. If the game offers a way to observe the result, read it back
and say what actually happened.
