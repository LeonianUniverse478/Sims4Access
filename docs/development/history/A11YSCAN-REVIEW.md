> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# a11yscan (glaroc) vs Screen Reader: review and comparison

**Historical comparison.** Current integration status is in
[INTEGRATION-STATUS-V7.md](INTEGRATION-STATUS-V7.md). V7 is deployed for keyboard
testing; main-menu speech remains unresolved. V6 corrects shared dialog-button
traversal, active-modal routing and picker scrolling. It ships the original
23 movies plus AgeUpPanel. The 135-definer inventory is not a coverage gap:
the Gamedata shared-class copy wins at runtime. Earlier claims that the reader reaches every
screen or that six specialized pickers each lack support were too broad:
they share PickersMain, and main-menu/CAS runtime coverage remains incomplete.
Glaroc's separate server-side dialog-answer fallback is still not integrated.

Reviewed 2026-09-03 from `<user-home>\Downloads\a11yscan_for_review\a11yscan\`
(README.md, `src/` 21 modules, `tools/` 3 scripts, `install/` build). His
version string is 0.1. Every EA API claim below was checked against the
1.127.41 decompile under `EA/simulation/` and the game's `base.zip`.

## Verdict

The two mods are opposites, not rivals. Screen Reader reads the UI the
client actually draws (23 patched Scaleform movies feeding Python). a11yscan
never touches the UI: it rebuilds a spoken interface from the simulation
data the UI is drawn from (pure Python, no .package at all). Each one works
exactly where the other cannot.

- His approach reaches the 3D world, build placement, Sim status and Sim
  creation, none of which Flash can give us, because none of it is a widget.
- Ours reaches every screen the client renders, including the ones his
  architecture can never see: notifications with all their tokens, the
  purchase cart, moodlets, event and wedding planning, household merge,
  gallery, the map. Those are client-only Flash with no server-side model.

The right shape is one mod with two layers: our UI reader plus his
data-side scanner, sharing our speech, settings and localisation. He
already falls back to `tyjokr_a11y_speech.speak()` when our mod is present,
so he has half-designed for that himself.

## 1. Architecture side by side

| | Screen Reader (ours) | a11yscan (his) |
|---|---|---|
| Text source | Rendered Flash text, already localised | STBL string table shipped offline (English only, 16.3 MB) plus tuning names |
| Flash patches | 23 movies, 17.6 MB package, plus UI Cheats compat package | None |
| Python | 6 modules, 2,770 lines, 81 KB ts4script | 21 modules, 10,738 lines incl. tools, 8.3 MB ts4script (embeds both .bin tables) |
| Input | Numpad keys, fixed set audited against game bindings; XInput gamepad (WIP) | Ctrl+Alt and Ctrl+Shift letter chords; bare arrows only while his grid is on |
| Flash to Python | PostServerCommand, Live commands | Not applicable |
| Python to Flash | SendUIMessage | Not applicable |
| Threading | Keys thread sends UI messages; Flash does the work | Keys thread posts intents; 20 ms wall-clock alarm drains them on the sim thread |
| Speech | Tolk, NVDA, System Access, SAPI child; braille; hover/manual/beeps/off; tooltip delay | Own NVDA DLL, then Tolk.dll if found, then our speak(), else silent console print |
| Localisation | 17-language vocabulary, game text arrives localised | Hardcoded English, English STBL only (locale 0) |
| Settings | cfg file, MCCC style, a11y.reload | None |
| Dialogs | Flash DialogMain announce + focus walker + synthetic click | show_dialog hook, options rebuilt from picker_rows/responses, answered via ui_dialog_* commands, verified against UiDialogService |
| Notifications | NotificationsMain reads the rendered card | Template from STBL, tokens re-resolved by hand, caller tokens captured in flight |
| World objects | Hover tip stamping (LocalizationHelperTuning.get_object_name, client resolves) | Category scanner with distance and compass bearing; names from OBJD table (3.1 MB) or tuning names |
| Interactions | Pie menu as rendered, focus walk, click | potential_interactions + aop.test, plus generate_choices for social mixers, run via select_choice or aop.execute |
| Build mode | Catalog thumbnails narrated; placement is mouse | Tile-grid cursor (1 m tiles, floor/pool/outside facts) plus place-at-cursor and undo |
| CAS | Blocked (see PLAN-FULLGAME.md) | Bypassed: SimCreator wizard, CAS Stories questionnaire, appearance by tags via cas.cas natives |
| Main menu | Silent (channel gated) | Keys work; only the save picker is useful there (copies a save over Slot_ffffffff.save) |
| Diagnostics | a11y.log, rawdiag, objdiag, mark line | Continuous a11yscan_log.txt, a11y2.diag/report/probe, Ctrl+Alt+Q reachability probe |
| Dev loop | Rebuild, redeploy, relaunch | Hot reload with generation counter and rollback |

## 2. What each one can do today

| Surface | Ours | His | Notes |
|---|---|---|---|
| Tooltips, panels, buttons, list rows | Yes | No | His architecture cannot see widgets at all |
| Needs, mood, skills, careers, calendar | Hover | Hotkeys for needs, emotion with causes, wants, current action | His "why" for emotion (buff weights) is nicer than our hover read |
| Notifications | Full rendered text | Approximate; misses client-side formatting | His own note: "some don't read correctly" |
| Dialogs and pickers | Yes, focus walk | Yes, keyboard list | His answers server-side; the client UI stays open after (his map bug) |
| Purchase picker cart, qty | Yes | No | He has no qty model; picks one row |
| Pie menu on a world object | After a mouse click | From the keyboard, no mouse | Biggest gap on our side |
| Socials (Friendly/Romantic mixers) | As rendered | Via generate_choices with a fake pick | Clever and correct |
| Phone, inventory, relationships | Via the panels | As scanner categories | Relationship panel interactions with picked_item_ids |
| Travel | Via the map, mouse | Runs the Travel interaction; pickers are dialogs | Map view sticks open afterwards |
| Build: browse catalog | Yes | Yes (definition_manager, price > 0) | |
| Build: place object | Mouse | Grid cursor, create_object | No rotation, no footprint check, see bugs |
| CAS from a lot | Not yet | Wizard (no screen) | Different goal: he skips CAS, we want to read it |
| CAS from New Game | No | No | Both confirmed dead; no zone, no managers |
| Switch household | No | Yes, rate-limited travel op | |
| Save game hotkey, funds | No | Yes | Trivial to add |
| Event/wedding planning, merge households, gallery, marketplace | Not covered yet, reachable | Impossible | Client-only screens |
| Main menu narration | No | No | |
| Sighted-helper focus ring | Yes | No | |
| Gamepad | WIP | No | |

## 3. What to adopt from his work, ranked

1. The world scanner (`a11yscan_world.py`, `a11yscan_state.py`,
   `a11yscan_actions.py`). Browse nearby objects by category, hear distance
   and bearing, open the tested interaction list, run one. Includes self,
   phone, inventory and contacts as categories, and nested pie categories.
   This is keyboard access to the 3D world, which our UI walker cannot
   provide. It is the single most valuable thing in his mod.
2. The tile-grid cursor (`a11yscan_grid.py`). Read-only cursor over 1 m
   tiles reporting objects on the tile and floor/pool/inside facts. Pairs
   with catalog placement. Placement itself needs fixing before adoption
   (section 5).
3. Sim status hotkeys: needs, emotion with causes, wants, current action,
   funds, play household Sim N. Cheap, and blind testers will want them
   even with panel hover available.
4. Server-side dialog answering as a fallback. When our Flash focus cannot
   reach a picker (six picker movies have no focus hook: PickersColumnBased, PickersFood, PickersGrid, PickersMulti, PickersOutfit, PickersSim),
   `ui_dialog_pick_result` / `ui_dialog_respond` verified against
   `ui_dialog_service().get_dialog()` is a sound second path.
5. The CAS bypass (`a11yscan_cas.py`, `a11yscan_stories.py`,
   `a11yscan_appearance.py`, `a11yscan_lots.py`). Creates a complete Sim,
   scores the real CAS Stories questionnaire from tuning, dresses by tags via
   `cas.cas` natives, picks an empty lot and moves in. Ships something for
   "make a Sim" while our CAS Flash hook stays blocked. Keep it as a
   separate mode, not a replacement for reading CAS.
6. Household picker and save picker. The household switch is good. The save
   picker writes into the saves folder; keep it out until section 5's
   concern is settled.
7. Hot reload (`a11yscan_reload.py`). Dev-only, but well done: generation
   counter in builtins so old threads and alarms retire themselves, both
   zipimport caches cleared, rollback on failure.
8. Not worth adopting: the STBL and OBJD tables. They exist only because
   Python cannot resolve a LocalizedString. Our object names already go
   through `LocalizationHelperTuning.get_object_name` and the client resolves
   them in the player's language.

## 4. What we have that he lacks, and why his walls are structural

- Every widget the client draws. His mod cannot read a tooltip, a panel
  row, a button label or a mod's custom Flash. Ours reads them as text.
- The screens he listed as broken (event planning, wedding planning, merge
  households, gallery, marketplace, the map) are client-only. There is no
  Python object behind them to rebuild from. He should stop spending nights
  on them; those are ours to cover with per-movie Flash hooks.
- Notifications. A notification's final text is assembled on the client:
  caller tokens, client-side formatting, glyphs. He re-implements token
  substitution by hand, ships 16 MB of STBL to do it, and still has cases
  that read wrong. We read the finished card.
- The map staying open after travel. He answers the UiMapViewPicker on the
  server; the client never gets its close. Our synthetic click goes through
  the real UI, so the client closes its own screen.
- Speech and settings. His speech stack is NVDA or Tolk or our module, else
  nothing spoken; no SAPI fallback, no braille, no modes, no voice control,
  no config file. With neither NVDA running nor a Tolk.dll at the Mods root
  his mod is silent unless ours is installed.
- Localisation. Everything he speaks is English, and his tables are English
  only. A German player hears English catalog names.
- Sighted helpers. No focus ring; nothing on screen shows what is selected.
- Key safety. Ctrl+Alt+arrow is the Intel graphics screen-rotation hotkey on
  many laptops. AltGr on non-US layouts is Ctrl+Alt, so typing accented
  characters fires his bindings. Keys are read, not consumed (same as ours),
  so game shortcuts under his chords still fire.

## 5. Code review findings

He asked to be told bluntly. What is right first:

- Sim-thread discipline via a wall-clock alarm pump is the correct pattern
  (`add_alarm_real_time` schedules on `time_service().wall_clock_timeline`,
  which keeps firing while paused; verified).
- `aop.test(context)` filtering mirrors `ChoiceMenu`, so his lists match the
  pie menu instead of over-reporting.
- `generate_choices(...)` with a fixed reference id, then reading
  `client.choice_menu`, then `select_choice(choice_id, reference_id)`:
  signatures verified, and it is the only way to get social mixers.
- `HasField` on protobuf tokens instead of truthiness. Correct, and a trap
  worth remembering ourselves.
- Dialog routes are verified by asking `UiDialogService` whether the dialog
  is gone, not by trusting return values.
- Hook wrappers stash originals on the class and restore them on reload.

Bugs and risks, most important first:

1. README claim "queue and re are unavailable, stick to os, math, time,
   threading" is false. `base.zip` ships `lib/re.pyc`, `lib/queue.pyc`,
   `struct`, `json`, `subprocess`, `shutil`, `pickle`, `configparser`,
   `collections`, `weakref`, `random`, `zipfile`, `io`, `codecs`. Only
   `ctypes` is missing (that is why both mods bundle it). Our narrator has
   used `re` in production since July. His hand-rolled camel-case splitter,
   markup stripper and "builtins only" table readers were unnecessary.
2. Pump degradation is permanent. `_pump_is_stale()` fires after 2 s of
   alarm silence, `_go_direct()` then clears the handle and runs every
   later intent on the key thread. `start()` is only called from
   `start_everything()` at zone load, so nothing re-arms. Pausing does not
   trigger it (wall clock keeps ticking), but an autosave or lot hitch over
   2 s does, after which game state is touched off-thread for the rest of
   the session. Fix: re-arm in `post()` when `zone_ready()`, or never clear
   the handle on a stale read. Also the `_STALE_SECONDS` comment says the
   alarm fires every 0.1 s; the interval is 0.02 s.
3. `build_buy.add_object_to_buildbuy_system(obj)` passes the object; EA's
   signature is `add_object_to_buildbuy_system(obj_id)` forwarding to the
   native with a zone id. His try/except swallows the failure and logs
   `registered=False`, so nothing he places is registered with build/buy.
   Fix: pass `obj.id`.
4. Placement bypasses the client's build/buy transaction entirely:
   `create_object` + `move_to` + `funds.try_remove`. No footprint, wall or
   slot validation (he documents this), no rotation, no depreciation
   record, undo is his own list. Objects can land inside walls or on top of
   other objects. Fine as a proof of concept, not shippable as is.
5. The save picker copies a chosen save over `Slot_ffffffff.save` in the
   saves folder, with one `.a11ybackup`. A mod writing over the resume slot
   for users who cannot verify what happened is a data-loss risk; the game
   also rewrites that slot on its own schedule. Needs a careful test plan
   before anyone blind relies on it.
6. Running both mods together double-announces every dialog (his show_dialog
   hook and our DialogMain announce both speak) and both ship a top-level
   `ctypes` package; first-loaded wins, harmless while both are the same
   stdlib copy.
7. `a11yscan_keys.py` docstring still says ctypes comes from our archive;
   the README and zip show he ships his own now.
8. His speech probe claims Tolk as backend as soon as `Tolk_Load()` succeeds,
   with no screen-reader detection, so Tolk's internal SAPI speaks and
   ignores any voice settings. Same trap we hit on 2026-08-03.
9. `tools/rebuild_tables.py` hardcodes a Steam install path and OneDrive
   Documents; `tools/package.py` expects a `py37/` interpreter folder and a
   `build/` folder that are not in the zip; `build_names.py` is referenced
   but not shipped. The build does not reproduce from the zip as sent.
10. Confirmed correct, worth knowing: `SimCreator.build_creation_dictionary`
    really does omit `first_name`/`last_name` (verified), so his post-hoc
    `apply_name` is the right fix. `outfit_utils.get_cas_part_name` really
    is `if False:` dead code returning `str(part_id)` (verified).

## 6. API cheat sheet from his work (verified against EA 1.127.41)

- `sim.potential_interactions(context)` then `aop.test(context)` gives the
  pie-menu list; `sim.potential_phone_interactions(context)` the phone;
  `sim.potential_relation_panel_interactions(context, target)` the
  relationship panel, run with `picked_item_ids={target_sim_id}` and the
  ACTING Sim as target (a SimInfo target crashes in posture handling).
- `interaction_commands.generate_choices(target_id, pick_type, x, y, z,
  lot_id, level, 0, 0, 0, reference_id, 0, 0, True, _connection=client.id)`
  leaves a `ChoiceMenu` on `client.choice_menu`; `select_choice(choice_id,
  reference_id)` runs one; choice ids expire per generation.
- `ui_commands.ui_dialog_pick_result(dialog_id, ingredient_check,
  prepped_ingredient_check, *choices)`, `ui_dialog_respond(dialog_id,
  response)`, `ui_dialog_pick_result_with_recipe_id(...)`,
  `ui_dialog_multi_picker_result(dialog_id, proto_str)`; liveness via
  `services.ui_dialog_service().get_dialog(dialog_id)`.
- Dialog text: `UiDialogBase._build_localized_string_msg` joins
  `text_tokens.get_tokens(resolver)` (or `resolver.get_localization_tokens()`
  when `text_tokens is DEFAULT`) with `additional_tokens` from the
  `show_dialog` call, which are stored nowhere else.
- `build_buy.has_floor_at_location(pos, level)`, `is_location_outside`,
  `is_location_pool`, `is_location_natural_ground`,
  `register_build_buy_exit_callback(fn)`, `add_object_to_buildbuy_system(obj_id)`.
- `SimSpawner.create_sim_infos((creator,), household=, tgt_client=,
  zone_id=, creation_source=, generate_all_cas_outfits=True)` returns
  `(sim_infos, household)`; `household=None` creates one; then
  `household.set_played_household(True)`, `household.move_into_zone(zone_id)`,
  `SimSpawner.spawn_sim(sim_info)`, `client.add_selectable_sim_info`,
  `client.set_active_sim_info`.
- `cas.cas.get_catalog_casparts_by_bodytype(sim_info=si._base,
  include_tags=[], exclude_tags=[], bodytypes=[bt], show_all_variants=True,
  rewards_parts=[])` returns `{part_id: (tags, tooltip)}`;
  `set_caspart(src._base, tgt._base, part_id, False, False, True, seed,
  remove_conflicting=True)`; `randomize_caspart_list(si._base, [])`.
  `BodyType` is in `sims.outfits.outfit_enums`.
- `persistence.get_zone_ids()`, `get_zone_proto_buff(zone_id)`,
  `get_lot_id_from_zone_id`, `get_household_id_from_zone_id`,
  `get_neighborhood_proto_buff(zone.neighborhood_id).name` (the world name;
  REGION tuning is the wrong tree).
- `sim_info.send_travel_live_to_nhd_to_live_op(household_id, zone_id)` is
  the household-switch route (`household_commands._activate_sims_family`).
  Never `send_travel_switch_to_zone_op` (leaves no active Sim).
- `camera.focus_on_sim(sim, follow_mode, client)` takes three args; the
  follow mode is an enum, not a bool.
- CAS Stories: `Types.CAS_STORIES_QUESTION` manager, `question.text`,
  `possible_answers`, each answer's weighting entries are ImmutableSlots
  with `weight` and `weighted_object`; trait choosers resolve by threshold.
- `alarms.add_alarm_real_time` runs on the wall clock and keeps firing
  while paused; it returns a handle that never fires with no zone.

## 7. Integration proposal

Do not merge the codebases as they stand. Keep Screen Reader as the UI
reader and bring his data-side features in as a layer that uses our speech,
settings and lang modules. In order:

1. Key scheme. His Ctrl+Alt chords cannot ship (Intel rotation, AltGr).
   Proposal: one "scanner" toggle key enters a mode where bare arrows and
   Enter drive his scanner or grid, the way his grid already works, and the
   numpad set stays as it is. Needs the user's sign-off (player-visible).
2. Fix the pump re-arm and the `obj.id` registration before any of his
   placement code runs on a tester's save.
3. Route all his `_say()` text through `lang.t()` so it localises.
4. Suppress his dialog announce when ours is live (one flag), keep his
   server-side answer path as the fallback for uncovered pickers.
5. Drop the .bin tables; use `LocalizationHelperTuning` where a
   LocalizedString is needed, our narrator where text is rendered.
6. Land the scanner and Sim-status hotkeys first (highest value, lowest
   risk), then the grid cursor, then the CAS wizard as its own mode, then
   household switching. Hold the save picker and placement until reworked.

## 8. Points to send him

- The `re`/`queue` finding, with the base.zip evidence. It frees his code.
- The pump bug and the `obj.id` bug, with the fix lines.
- Ctrl+Alt+arrows and AltGr.
- Event planning, wedding planning, merge households, gallery, marketplace,
  the map: client-only, no server-side model, unreachable from Python by
  design. Those are ours to cover from the Flash side; he should not keep
  hunting for them.
- CAS from New Game: agreed dead on both sides.
- What we would like from him next: keep iterating on the scanner UX (the
  category list, distance phrasing, socials nesting) since that is the part
  only a blind player can tune, and try his grid on multi-tile objects.

## 9. Design notes added 2026-09-03 evening (after user directives)

User directives: scanner first; no STBL/OBJD tables and no invented
language where the game has the words; build on the 2026-08-28 release
tree (clone at `My Script Mods/ScreenNarrator-integration/`, see its
INTEGRATION.md); the gamepad branch is defunct; be thorough.

Verified against EA 1.127.41 and our patched Flash sources:

- `interactions.choices` (generate_choices) ends with
  `Distributor.instance().add_event(MSG_PIE_MENU_CREATE, msg)`, so a call
  from Python makes the CLIENT receive the game's real pie menu for the
  target. Our PieMenuMain patch then narrates it and the focus walker
  drives it; activation is a real click, so select_choice runs with the
  right reference and revision. Zero string tables for interactions.
- The client drops unsolicited menus: `HandlePieMenuCreate` returns when
  `client_reference_id != mLastInteractionRequestId`, and it reads
  `mPickResults.pickType` BEFORE that check (null until the first mouse
  pick). Both are in the class we already patch: accept a reserved scanner
  reference id and synthesise a WorldPickResult (objectId String, pickType,
  worldPosX/Y/Z, lotId, level, bHasGoHere, simFirstName). The menu draws at
  the mouse position unless isInventoryRequest is set with itemPosition.
- Latent bug found in our own hook: `A11yAnnounceMenu` runs before the
  reference check, so an unsolicited menu would announce and never draw.
- The pie menu shows no object name (only `simFirstName` for Sims), so
  browsing still needs a name channel. `distributor.ops.SendUIMessage`
  carries only `message_name`. The native-to-Flash entry is
  `ExternalInterface.addCallback("SendMessage", instance.SendUIMessage)`
  in `CommunicationManager.set ExternalCallbacks`; the dispatch is a
  listener lookup by name. Plan: encode the request in the name
  (`A11y|loc|<hash>`), intercept in Flash, resolve with
  `LocKey.FromHash(hash).toString()` (the client localises in the player's
  language), post the text back on an a11y command. `obj.catalog_name` is
  a token-free LocalizedString, so a hash is all the name needs.
- Anything the scanner must say that the game has no words for (distance,
  bearing) goes through `tyjokr_a11y_lang` like the rest of our vocabulary.
- Six picker movies carry no A11yFocusInto hook: PickersColumnBased,
  PickersFood, PickersGrid, PickersMulti, PickersOutfit, PickersSim. Hover
  narration works in them through the app-domain TooltipManager.

## 10. glaroc build 2 (received 2026-09-06, `Downloads/a11yscan_for_testers`)

Changes against the reviewed build (diffed module by module):

- Shopping: `buy_into_inventory` creates the objects itself and charges the
  household. He found the game's own purchase-picker flow cannot be driven
  from Python (answering the picker only records a basket; the Sim buys
  later inside the interaction), so the mod does "take money, hand over
  goods" directly. Two real findings inside it: `funds.try_remove` wants an
  INT reason code (`Consts_pb2.FUNDS_*`, resolved at runtime), and
  `len(list(inventory))` counts stacks, so a merged purchase looked like a
  failed add and the whole stack was destroyed. Fixed by counting
  `stack_count` and never destroying on a miss.
- Jobs: new `a11yscan_careers.py`. The career screen is client-only
  (probe: dialog service empty while the screen is up), so the menu is
  rebuilt from CAREER tuning: held jobs with level/performance/PTO, go to
  work, day off, quit, and every career `is_valid_career` allows.
- Settings: new `a11yscan_settings.py`, autonomy and aging read back from
  the services after each change.
- Follow camera (Ctrl+Shift+F): re-aims the camera at the Sim on the pump
  tick, for positional audio. Almost certainly his own workaround for the
  same camera-pan problem our test hit.
- Dialogs: buttons now come from `_get_responses_gen()` (responses plus
  `_additional_responses` plus `ui_responses`), which is the reason yes/no
  pop-ups used to read as a lone "Okay"; `{S.x}{P.x}` plural pairs,
  `{M1.x}{F1.x}` gendered wording, pronoun tokens, a `readable()` cleaner
  for bullets and line breaks, and a periodic re-sweep that hooks dialog
  classes imported after startup.
- Keys: reads the `GetAsyncKeyState` 0x0001 latch bit so taps between polls
  are not lost, and polls at 15 ms. This is the "way more responsive".
- Pump: tries `start()` again before falling back to the key thread. Better,
  but the fallback still runs game code on the key thread when the re-arm
  fails, so the thread-safety concern in section 5 stands.
- Reload: detects a newer archive on disk and says so.

Still present: the DEVELOPERS.md claim that `re` and `queue` are missing
(they are in base.zip), and the save picker. The pump re-arm is a partial
fix of bug 2.

Relevance to our integration: the careers and settings modules are pure
data-side features of the kind the adopt list already anticipates, and the
purchase finding matters for us in the opposite direction: our Flash cart
narration drives the real picker, so we never need his direct-purchase
path. The `_get_responses_gen` and gendered-token work is only needed on
his side; the client renders all of that for us.

## 11. glaroc build 3 (received 2026-09-07, `Downloads/a11yscan_2026-09-07`)

New modules: `a11yscan_travel.py` (travel with no map screen: the map
picker only records `picked_zone_ids` and pushes a tuned continuation, so
he pushes the continuation directly with the zone id and companions),
`a11yscan_events.py` (social events rebuilt from SITUATION tuning and
`create_situation_with_guest_list`, with cost/goal/description read out),
`a11yscan_cheats.py` (1,800 lines: a keyboard cheats menu with skill and
relationship sliders, fixes, and two "why will my Sim not..." diagnostics),
`a11yscan_strings.py` (reads STBL resources AT RUNTIME through
`sims4.resources.list(type=0x220557DA)` and `sims4.resources.load(key)`, a
few per tick, cached next to the log; covers content mods installed after
packaging; English tables only), `a11yscan_typing.py` (generic text
entry for any text-input dialog). Move house and move-in-together
(household merge) in lots.py. Build mode: `placement_requirement` from
`build_buy.get_object_placement_flags` (REQUIRES_SLOT means "needs a
surface", said in the catalog before buying), `find_good_location` picks the
exact spot, surfaces ranked desk/table first, per-tile pathing advice from
`routing.test_point_placement_in_navmesh`, Ctrl+Shift+D sells the pointed
object with a refund, and `register_everything` repairs objects placed by
earlier builds. He found and fixed the `add_object_to_buildbuy_system(obj.id)`
bug independently, and a bigger one: cancelling the Sim's current activity
before issuing an order queued EA's own stand-up interaction at high
priority and displaced the order, so told-to interactions never queued.

Keys: Ctrl+Alt+N moved to Ctrl+Shift+N because Ctrl+Alt+N is the Windows
shortcut that starts NVDA. None of our chord keys is N. New: Ctrl+Shift+T
travel, +P events, +H move house, +D sell, +O aspiration, +Enter centre the
camera, Ctrl+Alt+V cheats menu. Reliability: the mod reloads itself when a
newer archive appears or when it stops responding.

Categories (asked 2026-09-07): his SCANNER categories are still the eight
hand-written English keyword buckets in world.py (chair/sofa -> "seating",
fridge/stove/counter -> "food and drink", ...) matched against tuning class
names, plus yourself/phone/inventory/relationships/sims and "other". His
BUY CATALOG now groups by BuyCat tag, but the label is the tag identifier
prettified in English ("furniture, sofas"), not the client's localised
label. Ours: object -> its BuyCat tag -> EA's own client tag metadata
(Client_TagsBuildBuy, the catalog's TagLocalizedName per tag) -> hash
resolved by the client at runtime through the Flash channel. No string
table, no invented words, player's language.

Runtime STBL reading is a real finding worth recording: Python CAN read
string tables through sims4.resources, so "Python cannot turn a key into
text" is only true without parsing; the Flash bounce remains the cleaner
route for us (client handles tokens and language, no parsing cost on the
simulation thread).

Discord 2026-09-07: he hands the mod over with credit; will be added as a
CurseForge contributor (LeonianUniverse); proposes replacing Tolk with
Prism (github.com/ethindp/prism) for Mac and Linux support; reports that
blind players will not use a mod that needs the mouse, which validates the
keyboard-first direction of the integration.
