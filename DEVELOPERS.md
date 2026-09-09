# Sims 4 Access — notes for developers

Everything below was learned the hard way against the shipped game. Most of it
is invisible until it bites.

## Modules

    a11yscan_log         continuous file logging (self-contained, no imports)
    a11yscan_speech      Prism (any reader, any OS), then Tolk, then console
    a11yscan_keys        Win32 GetAsyncKeyState polling on a daemon thread
    a11yscan_pump        key thread -> simulation thread via a real-time alarm
    a11yscan_state       the state machine and every mode
    a11yscan_world       scanning, categories, object naming, game time
    a11yscan_actions     interaction discovery and execution
    a11yscan_dialogs     dialog hooks, token resolution, row labelling
    a11yscan_cas         the Create-a-Sim wizard
    a11yscan_stories     the CAS Stories questionnaire
    a11yscan_appearance  CAS parts by body type
    a11yscan_careers     the job menu
    a11yscan_lots        lots, worlds, households, moving in
    a11yscan_saves       the save picker (file-level; works with no zone)
    a11yscan_settings    autonomy and ageing
    a11yscan_build       buying, placing, charging
    a11yscan_grid        the tile-grid cursor
    a11yscan_narrate     idle narration polling
    a11yscan_probe       read-only "what is reachable right now"
    a11yscan_names       STBL hash -> text, binary-searched flat table
    a11yscan_objects     definition id -> catalog name, same shape
    a11yscan_reload      hot reload and build-freshness checking
    a11yscan_cmds        console commands + startup wiring

## Loading and environment

**The loader imports `.pyc` only.** A `.py` inside a `.ts4script` is enumerated
and then silently never imported — no exception, no log line. Compile with a
real Python 3.7 (magic `420d0d0a`); python.org's 3.7.9 embeddable works, `uv`
has no 3.7 builds.

**C extensions ship, the pure-Python stdlib does not.** `_ctypes_x64.pyd`
exists but `ctypes` does not, so the mod ships its own. `queue` and **`re`** are
likewise unavailable — all parsing here is by hand.

**DBPF compression `0xFFFF` is RefPack** in TS4, not "uncompressed" as
documented elsewhere. Get it wrong and the base string table parses to zero
entries.

## Threading

Game state must be touched on the simulation thread. The key poller posts
intents to a real-time alarm pump (0.02s). Two deliberate exceptions run on the
key thread because they touch no game state and a round trip is unusable:
typed characters, and repeat/help.

**`add_alarm_real_time` returns a handle that never fires with no zone**, and
leaving a lot does not clear it — the queue silently filled forever. The pump
treats alarm silence as death and re-arms.

**`GetAsyncKeyState & 0x8000` only reports a key held at that instant.** Taps
between polls were lost, and the poll thread shares the GIL with the simulation
so the gap grows when the game is busy. Use the **`0x0001` latch bit** as well,
and read every bound key each poll so latches cannot go stale under a different
chord.

## Dialogs and text

- Buttons come from `dialog._get_responses_gen()`, which yields from
  `responses`, **`_additional_responses`** and `ui_responses`. Reading only
  `responses` makes every yes/no pop-up read as a lone "Okay".
- Some tokens are passed to `show_dialog(additional_tokens=...)` and stored
  nowhere — a bill's amount arrives that way, so even the game's own
  `build_msg` renders "That'll be ." Capture them in the hook.
- `body_of`/`title_of` must take the **fuller** of (build_msg, token-filled
  factory call). build_msg loses caller tokens; a bare factory call strips
  placeholders.
- `{M1.man}{F1.woman}` is gendered wording (keep the branch matching
  `token.is_female`); `{S.x}{P.x}` is singular/plural in catalog names;
  `{0.SimPronounObjective}` should give him/her/them.
- Date/time is token type 6: `token.date_and_time` with hours, minutes and a
  date that is the weekday (1-7, 0 remapped to 7). **Protobuf submessages read
  back as empty rather than None** — `HasField` is the only honest test, or
  every token renders as "12:00 AM".
- Buff and whim text has tokens but no dialog, so supply a stand-in Sim token
  (`dialogs.text_for_sim`) or names and gendered words are stripped.
- Hook **every** `UiDialogBase` subclass that defines its own `show_dialog`,
  and re-sweep periodically: classes appear as their modules are imported.

## Interactions

Three separate sets exist on a Sim: `potential_interactions` (pie menu),
`potential_phone_interactions`, and
`potential_relation_panel_interactions(target, context)`. The latter two are
**picker** interactions: the acting Sim is the target and the other Sim is
passed as `picked_item_ids={sim_id}`. `generate_choices`/`select_choice` choice
ids expire between generations — regenerate immediately before selecting.

**Never call `SimInfo.send_travel_switch_to_zone_op`** — it moves the client but
leaves the game with no active Sim. `send_travel_live_to_nhd_to_live_op` (as in
`household_commands._activate_sims_family`) is the legitimate route for
switching household, and must be rate-limited and never sent for a household
whose `home_zone_id` is 0.

## Money and objects

- **`funds.try_remove(amount, reason)` needs an INT reason code**, not a
  string. Passing a description raises TypeError, and if that is swallowed the
  charge is silently skipped. Codes are `Consts_pb2.FUNDS_*`, which is not in
  the script archives — resolve at runtime.
- **`player_try_add_object` returns truthy without adding.** Use
  `system_add_object`, which is what crafting and carry code use.
- **`len(list(inventory))` counts stacks, not items.** A second identical item
  merges and the count does not move. Sum `stack_count`.
- The household inventory is a separate store:
  `build_buy.get_object_ids_in_household_inventory(household_id)`.

## Create-a-Sim

`SimCreator` accepts `first_name`/`last_name` and **silently drops them** —
`build_creation_dictionary` passes only age, gender, tagSet, species, trait_ids
and body-type policy. Assign names after creation, as
`change_sim_name_interaction.on_response` does.

Appearance: `cas.cas.get_catalog_casparts_by_bodytype(sim_info=<sim_info._base>,
include_tags, exclude_tags, bodytypes, show_all_variants, rewards_parts)`
returns `{part_id: (tags, tooltip)}`; `set_caspart(source._base, target._base,
part_id, should_toggle, replace_with_random, update_genetics, seed,
remove_conflicting=True)` applies one. `BodyType` is in
`sims.outfits.outfit_enums`. Tags arrive as plain integers — resolve through
`tag.Tag(value).name`.

## The method that worked

The cheat console cannot be copied from and the user reads by speech, so the
mod writes everything to `a11yscan_log.txt`. Read that file rather than asking
for pasted output.

Two habits, both learned by not doing them:

- **Log the result, not the intent.** An early version logged
  `sim_info Miranda Newman created` from its own variables while the Sim was
  actually called "A Sim". Read values back off the object.
- **Verify the effect, not the return value.** A notification saying "delivered
  to your inventory", a `try_remove` that raised into a swallowed except, and a
  `player_try_add_object` returning true all reported success while doing
  nothing. Read the funds, count the inventory, check the tracker.

`Ctrl+Alt+Q` writes a read-only probe: open dialogs, every service that answers,
tuning manager counts, the CAS natives, and the Sim's interaction queue. Press
it **while** a suspect screen is open — that is what proved the career screen
has no server-side dialog.

## Building

    py37\python.exe tools\package.py

Compiles every `a11yscan_*.py` to `.pyc`, zips them with the sources, the
`ctypes` package and the `.bin` tables into the `.ts4script`, installs to the
Mods folder and mirrors the sources.

    python rebuild_tables.py <output dir>

Rebuilds both lookup tables from the game packages **and the Mods folder** —
mod objects carry their own OBJD and STBL resources, and without this a shop
selling mod items reads prices with no names. Ordinary Python 3 is fine. Do not
use the older `build_names.py`: it filters out any string over 80 characters or
containing `{`, which discards every dialog template.

## The Gallery: what we found, for whoever picks it up

The mod's whole method is "don't read the UI, rebuild it from the data the UI
is drawn from." The Gallery is the one place where that method has nothing to
work with, and this is the evidence rather than an impression:

* The words `tray`, `blueprint` and `bpi` do not appear anywhere in the game's
  Python. Not a partial API - nothing at all.
* `build_buy` exposes 58 native entry points. None concern lots, rooms, walls
  or blueprints. The nearest are `get_wall_contours`, which reads walls, and
  the floor-*feature* calls, which are for burnt patches and fallen leaves.
  Nothing creates structure.
* The only Gallery code in the simulation is
  `interactions.gallery_interactions.MoveInFromGallerySuperInteraction`, whose
  entire body is one op:

```python
op = distributor.ops.MoveHouseholdIntoLotFromGallery(
    household_id=household_id, num_household_sims=len(household),
    plex_zone_ids=zone_ids, zone_id=solo_zone_id)
Distributor.instance().add_op(sim, op)
```

Browsing, searching, filtering by pack and downloading all happen client-side
against EA's online service, which needs an account sign-in; the simulation
never sees any of it.

One thread is left deliberately untied. That interaction takes its zone from
`context.pick.get_zone_id_from_pick_location()` - a click on the ground, which
a keyboard cannot produce - but the op itself only wants a zone id, and every
zone id in the save is already enumerated (`a11yscan_lots.survey`). So the op
can be sent for any lot without a click. `a11yscan_gallery.move_in_from_gallery`
does exactly that, and `a11y2.gallery` on the console fires it.

**Nobody has run it.** The open question is what the client draws when the op
arrives. If it is a panel, this is a dead end for the same reason the map
screen is. If any part of the flow arrives as a dialog, the existing hooks
already read it and there is a way in. Whoever tests it should watch
`a11yscan_log.txt` for a `dialog shown:` line at the moment it fires.

Getting content *into* the library is already solved outside the game by the
community's TS4 Gallery Downloader, which pulls tray files straight from EA's
own endpoints. Placing a lot from the library onto a plot is the unsolved half.
