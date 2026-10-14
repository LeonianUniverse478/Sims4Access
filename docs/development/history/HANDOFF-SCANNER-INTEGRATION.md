> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# Screen Reader + a11yscan integration: handoff (2026-09-15)

## 2026-09-25 05:36: v14h live (restore PASS, exit click point FAIL); v14i frozen with the pointer resync

- Installed: v14h pair (script 39e79201 = Python + a11y.buildlog
  diagnostics, UI 6792d2b4 = Flash lifecycle logging, SetMouseInputEnabled
  on disable, GERentalPanel symbol). Live on it: catalog product restored
  twice after the Build actions window (console path; the console does not
  drop the product, the drop and SetModalVisible arrive in one dispatch and
  are claimed), rental quote narration PASS (row 31), affordability refusal
  PASS (row 27), rental + arrival PASS (row 25), solo M arrival (row 28).
  FAIL: after F1 the physical click still acts at the last virtual cursor
  point (row 35).
- v14i (Codex handoff, Claude-owned Flash patch, approved): A11yBuildDisable
  sends SetVirtualCursorPosition(-1,-1) after SetupVirtualCursor(false) and
  before SetMouseInputEnabled(true), confirm mapping 0 and restraints
  unchanged; documented as a candidate cleanup (EA sends -1,-1 on enable).
  Frozen `build/v14i-resync-ui-candidate` (UI d302876933c2d6aadc57a85db7b8e540a3678a15d9b92822fe67b1ba7a1be977,
  template d7b478b84a6c798c, 556 checks, audit PASS) + script 39e79201
  unchanged; deploy request with Codex. Diff: build/claude-proposals/v14i-cursor-resync.diff.
- Held: hub chord under the catalog scope (H = help intent; needs a
  client-side catalog-vs-modal distinction if the trace confirms); README
  Build guidance draft in build/claude-proposals/README-build-draft.txt.

## 2026-09-25 04:08: v14g pair frozen (script 7064e3d8 + UI 723eed6c), awaiting Codex audit + deploy

- v14g = v14f plus: Python Build exit release (`build.on_build_buy_exit`,
  silent forced off when Build ends), Codex's Flash idempotent off +
  removed-from-stage/reset cleanup, catalog product preservation (v3
  proposal integrated by Codex: remember ordinary CatalogProduct from
  BBProductSelected, modal balance, frame-finalized drops, restore once on a
  menu action or on within 5 s of the last modal close, recorded stateIndex),
  Observe from the Build frame. Script `build/v14g-build-script-candidate`
  7064e3d81dacec22f4a9072b8bf9f69337ecef6fbd9284c1912db94e2e08d01a (550
  checks, Codex audit PASS); UI `build/v14g-build-ui-candidate`
  723eed6cc7ab85ffbafd2cb7a7917f52480780618daccb6f966d614b4339a5c1 (chain
  v14g-build gate PASSED 04:06, audit_frozen_ui PASS). Installed is still the
  v14f pair (c7bd2bb6 + c79b26f6) until Codex's deploy request is approved.
- Live on v14f so far: rows 25 (rental + arrival, repeat clean, one EA
  teardown assertion noted), 27 (affordability refusal), 28 partial (solo M
  arrival), Build composite movement; open live: Build placement with the
  restored product, exit release, M refusals, rows 30-34.
- README Build guidance draft: build/claude-proposals/README-build-draft.txt.

## 2026-09-25 03:15: v14f pair LIVE; Build findings; v14g Build exit release in source

- v14f pair (script c7bd2bb6 + UI c79b26f6) installed 02:29 by Codex, live
  unsaved. Build actions window: keyboard composite resume PASS (Move left,
  Center moved the native cursor). Three findings: (1) pointer clicks and
  wheel over the window act on the lot beneath (engine routes Build mouse
  input past the picker; documented, keyboard window); (2) EA's
  BuildBuyInspectorMain.HandleSetModalVisible cancels the held catalog product
  when the first modal opens (console or our picker), so catalog placement
  from the window needs Codex's Flash re-selection on `menu:` resume
  (recipe: remember BBProductSelected, call CatalogProduct.SelectProductByKey);
  (3) leaving Build (F1) tore down the Build UI before its guard released the
  engine cursor, and the Live UI's off early-returned on its boolean, so
  clicks were dead until restart. Fix split: Codex makes Flash off idempotent
  plus removed-from-stage cleanup; Python `build.on_build_buy_exit()`
  (registered with build_buy.register_build_buy_exit_callback) sends a silent
  off whenever the session used the cursor. In source, NOT built:
  tyjokr_a11y_build.py 60d9daee7fa6e0bd, test_build_menu_v14f 16 checks,
  diff build/claude-proposals/v14g-build-exit.diff, awaiting Codex review.
- The synthetic Ctrl+Alt+Backspace leak was the tool sending a bare key /
  one-burst chord: the swallow hook only installs after Ctrl+Alt are seen
  held (no 'swallow hook installed' line in the session); not a defect.
- TEST-V14: row 32 PARTIAL with the known limitations, row 35 added (exit
  release). Vacation rows 23-27, 30-34 and M rows 28-29 still pending live.

## 2026-09-25 02:20: v14f script candidate frozen (c7bd2bb6); UI chain v14f-rental-build running

- Source state (Codex cross-review APPROVED 06:17 UTC): keyboard travel list,
  vacation stays (rentals only) priced by Codex's Flash bridge scoped per
  request (`A11y|lotprice|<zone>|<gen>` / `a11y.lotprice_enc zone|price|gen`,
  exactly 3 fields, truncated price 1..2^31-1), the place list, stay window
  and commit re-read the request price so a moved price re-quotes and a
  withdrawn price goes to the native map before any rental; M key handshake
  (Python + ControlPanel rev2 + Codex's TooltipManager bridge); Build actions
  window (17 rows) whose move/step/center/select/cancel/rotate/status rows use
  `build.request_menu` -> `A11y|build|menu:<action>|<serial>`: the client
  re-enables the cursor at its remembered position after the modal closed and
  performs the one action (Codex Flash, contract 06:11 UTC); on/off/undo/redo
  and grid aim are ordinary requests; nothing resumes on its own.
- `build/v14f-rental-build-script-candidate` FROZEN: archive
  c7bd2bb66c7f8eaee19e9f5993183a5d3591002558c039fd2b07ca8c9c245680, 528
  checks / 34 suites (`build/v14f-run-checks.log`). Sources: travel
  301efaf3e6415eba, hub 3cc8b22dbb89508d, build be893d7ce2975174, lang
  21ca27e282c0574d. NOT installed (installed = script 7a7c64e0 + UI 6f71529b).
- UI chain v14f-rental-build PASSED 02:27 and is FROZEN as `build/v14f-rental-build-ui-candidate` (UI c79b26f6..., compat 591056ee...); the line below records how it was started. UI chain `flash/chain.ps1 -Tag v14f-rental-build -Work work-1.128.90`
  started 02:18 (Codex's TooltipManager 02:16:53 + ControlPanel rev2). Next:
  `py -3.7 tools/freeze_ui_candidate.py v14f-rental-build`, hashes to Codex
  for `tools/audit_frozen_ui.py`, then Codex's deploy request (its
  `tools/deploy_reviewed_v14_pair.py`, game closed) and live rows 23-34 plus
  Build placement/undo/redo. The v14e UI candidate (3356c442) is superseded.
- TEST-V14 rows 32-34 describe the Build menu resume, the re-quote path and
  the reply strictness; all UNTESTED live.

## 2026-09-25 00:30: v14b script candidate approved; vacation revision in source (v14c)

- Ordinary-travel script candidate `build/v14b-ordinary-travel-script-candidate`
  (archive 1ad87207..., travel.py fd1856609c370e1e) reviewed and APPROVED;
  Codex deploys it with the corrected UI polish (its ChoiceDescription had a
  double index mapping on recycling layouts; fix confirmed from the olympus
  pcode: RecyclingGridLayout.GetGridIndexOfCell is already data-mapped,
  GridLayout is not). UI 48a3fce7 (event/career descriptions) is installed.
- VACATION mode implemented in `Scripts/tyjokr_a11y_travel.py` (sha
  ee0605bc6ed5ba34, lang 06c77812b25f57ac), NOT built: Stay window 1..7 days
  priced as EA's rental panel (`build_buy.get_lot_value(zone, True)[0] *
  RentableZoneTuning.PRICE_MODIFIERS`), rental through
  `travel_group_manager.create_travel_group_and_rent_zone` with its bool,
  party = actor + companions, funds and travel-group checks before creation,
  no native fallback after a rental, refused OK never re-answered. Rental
  panel source extracted to `build/v14b-rental-reference` (UI.package movie
  0x10CF65865DEC064F). `tools/test_travel_vacation_v14b.py` 20 checks after
  Codex's two reviews (household-level guard, pick validated before renting,
  rollback = exact created group destroyed + payer refunded, exceptions
  covered). TEST-V14 rows 23-27. FROZEN as `build/v14c-vacation-script-candidate`
  (archive a92a1a76..., 444 checks / 28 suites, Codex freeze tool audit passed;
  its hard-coded purpose string is wrong for this candidate, see the collab
  log). M key handshake protocol proposed (v14b-travel-followups.md section 5:
  readiness lease + request id + explicit A11yTravelResult, no timer fallback).
- M handshake Python side IMPLEMENTED (not built): pump-driven lease cadence
  (`A11y|travelready|<lease>` every 2 s, 0 on stop/setting off),
  `A11y|travellist|on|off`, `a11y.travel <lease> <request>` with explicit
  `A11y|travelresult|<request>|ok|refused|<reason>`, `a11y.travel_cancel`;
  pump.start/stop drive the lease; menu toggle announces. tools/
  test_travel_m_v14c.py 11 checks. Flash half (ControlPanel patch after the
  native guards, lease age < 5 s, bounded pending with cancel) is Codex's.
  Vacation candidate a92a1a76 approved for deploy (rows 23-27).
- 01:40 Python corrected per Codex (session epoch never resets, heartbeat
  republishes the same epoch, bounded request list keyed (epoch, id), cancel at
  ingress + 3 s drain deadline); test_travel_m_v14c 16 checks. Codex TRANSFERRED
  the Flash M hook + pipeline to Claude: `flash/extra-classes/ControlPanel.as`
  (GameTray 0xBEB822E79797F7EF, A11yRouteTravel after all native guards, lease
  age <= 5 s, 3 s pending window, cancel on timeout, A11yTravelResult listener),
  MOVIES/`$movies` entries, own-class-only replace for GameTray, EA original
  extracted. Still needs Codex's 2 statics + 2 parse lines in TooltipManager;
  no chain run yet. Vacation a92a1a76 DEPLOYED 01:07 by Codex (rows 23-27 live
  pending).
- 01:11 LIVE BLOCKER on a92a1a76: Granite Falls rentals priced -2 (the
  `build_buy.get_lot_value` sentinel for an unloaded lot). Fixed in source
  (travel.py 0ba85893956ec966): value from
  `services.get_zone(zone, allow_uninstantiated_zones=True).lot.furnished_lot_value`
  (EA's own off-lot pattern), build-buy only when positive, nothing <= 0 /
  NaN / inf is ever priced, unpriced row -> native panel; `a11y.lot_value`
  diagnostic. Cancel acknowledgement at ingress added to the M protocol.
- 02:35 FROZEN `build/v14e-travel-script-candidate` (archive cd5376f9...,
  485 checks / 31 suites): price fix + M Python side (session epoch, heartbeat
  republishing the same epoch, cancel tombstones, settled-outcome replies,
  zero publication settles queued work). Flash: Codex added the bridge in
  TooltipManager (sA11yTravelLease/time/list, A11yTravelCanRoute, parser ->
  A11yTravelReady/A11yTravelResult UI messages; fixture tools/
  test_travel_bridge_v14.js 8); my `flash/extra-classes/ControlPanel.as` rev2
  (pending first, ack-based cancel, epoch-bound results; fixture tools/
  test_travel_controlpanel_v14e.js 10).
- 01:40 chain v14e-m-hook DONE: gate PASSED (64 comparisons, GameTray
  targeted=3), frozen `build/v14e-m-hook-ui-candidate` (UI 3356c442..., compat
  6ca95339...) with `tools/freeze_ui_candidate.py <tag>` (new: ties extra
  classes, pipeline tables, EA/patched movies, chain log, checks). Script
  re-frozen after Codex's last point (pending duplicate silent) as
  `build/v14e-travel-script-candidate` 7a7c64e0..., INSTALLED by Codex 01:39
  (UI still 6f71529b). Live rows pending: 30 (price source), 23-27, 28-29 (M)
  once the UI pair is installed.
- 01:45 LIVE on 7a7c64e0: the uninstantiated-zone lot value is NOT positive for
  Granite Falls either (rentals unpriced, fallback to the native map worked,
  party intact, funds unchanged); native map tooltip: Sims on vacation may only
  stay on vacation rental lots (my free-lot booking path was wrong). v14f source
  (travel.py a289e32a...): vacation lists rentals only, no rentals = native
  map, client price bridge (Python posts A11y|lotprice|<zone>, Flash answers
  a11y.lotprice_enc <zone>|<price> computed like NeighborhoodLotData
  .VacationRentalPrice; Codex owns the Flash side), rows re-read the cache.
  26 vacation checks. Native rental panel narration (Codex) as belt-and-braces.
- 02:15 v14f continued: bridge scoped per request (generation token, prices
  die with the request, quoted stay re-quoted if the price moves), Build
  actions window in the hub (`a11y.buildmenu`, 12 rows via build.request after
  the window closes; Codex's key probe showed Scaleform never sees chorded
  keys, so event ingress is dead), rebuild_all.ps1 template read as UTF-8
  (Codex audit found ANSI-mangled comments). Codex's Flash: A11yLotRentalPrice
  bridge (reviewed, exact NeighborhoodLotData math) + GERentalPanelMain intro
  scope; wire change pending on its side (echo the generation). Suites: 28/5/
  5/20/39/8 + older. NOT built.
  v14d UI (6f71529b: recycled-row fix, hidden hire prune, Sim picker states)
  with the ordinary script 1ad87207 approved for deploy.

## 2026-09-25 early: v14 DEPLOYED and live-tested by Codex; v14b Python source in progress

v14 (script only, archive 427214a8..., UI/compat = v13b) was deployed by Codex
at 22:55 after mutual hash review. Live (Codex driving, TEST-V14): world list
PASS, Back PASS, Escape cancel PASS (queue verified clean), full keyboard trip
with one companion PASS (Brindleton Pawspital, native loading). FAILS: hidden
career/debug worlds listed (EP01_World), offered master unit dropped from the
unit window, companion Sim picker rows say nothing on Space, single-choice
rows said "unchecked" (v13b P4 too broad).

v14b, Python side (Claude, in `Scripts/tyjokr_a11y_travel.py`, NOT built):
player-facing region filter from `UiTuning.PACK_SPECIFIC_DATA[..].region_list`
(is_player_facing, localized region_name) matched through
`Region.REGION_DESCRIPTION_TUNING_MAP`; unknown region data = whole request to
the native map; offered master units listed; family-first labels for occupied
homes plus "Residents: first names"; `a11y.travel_probe`; `a11y.travel`
(pushes self_SimPicker_TravelWith, EA gating). 39 checks + Codex's 8 (one
count to update). Flash side (Codex, NOT built): A11yPickerToggleCell narrowed
to SelectableRecyclingGridLayout owners + a SimPicker branch gated on a live
btnDone; GoToNeigborhoodTravel diagnostic mark. Design open: VACATION mode
(proposal section 4, needs the rental panel facts), M key interception after
the diagnostic proves the message path.

## 2026-09-24 late: v14 keyboard travel list (script only), PROTOTYPE, NOT built, NOT deployed

User direction (via Codex): with keyboard on, answer travel requests from a
simplified World -> place -> unit list; the map stays available.

Finding that shaped it: every player travel route ends in EA's own Python
dialog `UiMapViewPicker` (rows precomputed by `LotPickerMixin`); the native
map only answers it with `ui.dialog.pick_result` + `ui.dialog.respond OK`.
Python can answer the same dialog through `ui_dialog_service`, so companions,
eligibility, the tuned continuation (`create_situation_InviteTo`), loading and
cancellation stay native. No Flash change. Review: 
`build/claude-proposals/simplified-travel-python-review.md`.

- `Scripts/tyjokr_a11y_travel.py` (new): wraps `UiMapViewPicker.distribute_dialog`.
  Handled only when keyboard on, `travel_list` on, mode == TRAVEL, zone loaded;
  anything else or any failure = original distribute (native map).
  Windows are native `UiObjectPicker`s via `menu._picker`: World (neighborhood
  names, "N places", last row "Open the map instead"), place ("Back to worlds",
  lots with venue/residents, multi-unit buildings as one row "N units", last
  row map), unit ("Back to places", units). Commit = identity check on
  `_active_dialogs`, `dialog_pick_result([zone])` checked, then `respond OK`.
  Escape at any window = `respond CANCEL` + "Travel cancelled." Map row = the
  original distribute, once; pending state is cleared before every terminal
  call. Log lines all start with `travel:`.
- Setting `travel_list` (cfg `[features] travel list`, default on; settings
  window row; `a11y.settings` line). 12 lang terms (en + pl).
- Codex review (02:40 UTC) found five lifecycle bugs, all fixed: deferred
  steps are closures over their own request; a superseded request, a failed
  pick, a refused OK (picks cleared first: EA's picker listener pushes from
  results without checking the response), a dead pump, a mid-flow settings
  change and a window failure all cancel EA's dialog natively; grouping is
  rebuilt fresh. Small-business lots of another household (count of that
  household's businesses allowed on the zone >= 1 residential / 2 venue) are
  announced and handed to the native map with the same request.
- `tools/test_travel_v14.py`: 27 checks; Codex's `tools/test_travel_review_v14.py`: 6 checks (stubbed dialog service / persistence /
  plex service): keyboard off, setting off, other modes, world rows, place
  commit, multi-unit commit with the unit zone id, back rows, Escape at world
  and place, failed pick, stale original dialog, duplicate and replaced window
  replies, map fallback once and never after a terminal response, empty rows,
  newer request replacing an open list, cfg/menu/readout/lang coverage.
- Scope: Python map picker requests only. The M key opens the map through the
  client's own GoToNeighborhoodTravel path (no Python dialog) and stays native
  in v14 (Codex verified ControlPanel 691+/1820).
- `TEST-V14.md`: 17 live rows, ALL UNTESTED. Open design point: Escape
  cancels at every level (Back rows go up).
- Diff for cross-review: `build/claude-proposals/v14-travel-list.diff`.
  Waiting on Codex's lifecycle review before any build.

## 2026-09-24 night: v13 / v13b (Flash + script), INSTALLED locally, NOT released

AFK-authorized joint session (Codex map/travel + Build setup; Claude event
planner + picker state). Installed now: v13b main pair (UI sha 7cb82e36...,
script sha db609c24..., backup build/codex-deployed-before-v13b), candidate
`build/v13b-event-map-candidate/` (main gate 61, compat gate 19, 366 checks).
Contains: map traversal + lot labels + toolbar-order sort (Codex); role-slot
proxy, disabled-proxy speech, phone token, picker selection state via the
olympus Button `Selected` getter with settled reread, wizard top-nav cells
reachable and named from the grid data (Claude/Codex); startup A11yInspect
routing exception. Live PASS on v13: calendar -> planner -> types -> roles ->
Sim picker opens, selection + OK work, event scheduled (Keg Party, funds
12409->12309; venue step by mouse). Live PASS on v13b: map lot labels.
OPEN: unit-view focus after Enter on a lot, planner venue/confirm by keyboard,
'checked' narration and top-nav labels live, phone stop live, Build catalog
item grid entry + placement with funds, Escape not closing the travel map /
hire picker (use Cancel Travel / Close), 'Selector'/'buff' unlabeled HUD
stops, 'Track'/'Prev Button' stops, Close - ESC on panels/pause/planner, Sim-
switch refusal wording during HUD browsing. Session halted 21:50 when the
user returned (physical Escape). Records: COLLAB-CLAUDE-CODEX.md, TEST-V13.md.

## 2026-09-24 evening: v12 next-version work (script-only, on top of the staged release)

User direction: a spoken FULL keyboard-shortcut readout, and a direct shortcut
to switch the controlled Sim. Agreed split, cross-reviewed: Codex =
`Scripts/tyjokr_a11y_shortcuts.py` (readout generated from keys.py's live
BINDINGS / CHORDS / NUMPAD tables + the two _plain_message extras; hub row
"Keyboard shortcuts" replaces "Scanner help"; the scanner's legacy help branch
delegates to the same helper; lang terms; `tools/test_shortcuts_v12.py`, 9).
Claude = glaroc's Ctrl+Alt+1..8 in keys.py (CHORDS 0x31..0x38 -> sim1..sim8;
`_chord` branch before the modal branch: silent while typing, spoken refusal
while any dialog/picker/panel owns focus; `_switch_household_sim` on the pump
re-checks epoch/editing/modal, selectable order, existing hub.select_sim
speaks the name; `tools/test_sim_chords_v12.py`, 10; drift guard in
test_scanner_v5 extended). Full runner 345 checks / 24 suites (Codex).
Candidate `build/v12-shortcuts-candidate/`: ts4script 248,272 B sha
465719fb... (19 members incl. ctypes/), UI unchanged from final-v11
(sha e32a22c6...), source snapshot + manifests. Deploy request sent; Codex
audits, deploys the ts4script only, smokes the hub row; the Ctrl+Alt+digit
chords need a held-modifier test (Claude's driver or a human). The v11
release records below stay as they are; v12 is NOT in the staged release zip.

## 2026-09-24 RELEASE CANDIDATE STAGED (Claude + Codex pair session)

Final build `build/final-v11-full/` (frozen 115 source inputs, 326 offline
checks / 22 suites): UI package sha e32a22c6... (24 resources), compat package
sha 4670025d... (6), dev script sha d2120670... (18 modules incl. ctypes/).
Gates: main 61 PASS, compat 19 PASS, independent audit PASS. Staged with
`tools/stage_release.py` into `dist/2026-09-24_1728/`: main zip (release
archive sha b002c5dc..., UI package, draft README; NO cfg by design) and a
SEPARATE UI Cheats compat zip. Nothing uploaded. Codex's final smoke PASSED
on the exact release archive; rule 4 byte equality verified by both agents. Game closed without saving; cfg unchanged. Pending: the user's acceptance of
`build/claude-proposals/README-release-draft.txt` (source README.txt untouched),
the CurseForge upload and adding glaroc (LeonianUniverse) as contributor.
What changed today, in order: Live-mode Tab regression (zone hook never
posted the mode mark); ctypes/ omitted from every V11 archive (masked locally
by EngineModding); a11y.inputfence positional payload crash; startup mode now
keyed off EA UIManager.mGameState; CAS ring: offstage GameTray targets
excluded, static scrollers exempt; CAS name label proxy + name-field
focus-follow narration (txtDefault, since DefaultText is setter-only);
cheat-console Enter tap leaking into A11yActivate (poller + modalstate fence);
dialog "Close - ESC" excluded from the Tab ring; piecreate diagnostic removed.
Still open: world-scanner announcements under a held Ctrl+Alt chord with no
focus owner (hook + core proven separately; human test), first-run popup
(user-deferred), many CAS controls mouse-only. Full record:
COLLAB-CLAUDE-CODEX.md; live evidence build/run-*/ and build/codex-live-20260924/.

## 2026-09-24: Live-mode Tab/arrow regression, root cause found (Claude + Codex)

Root cause of the 09-16 report ("keys dead in the lot, no -native mark"):
`A11yMsgHook` (runs on Python's A11yHook at every zone load) set
`mA11yStartupActive = false` WITHOUT posting a mode mark, and the frame path
only posts on a change it sees itself, so Python's `_flash_startup` stayed True
for as long as the socket lived and `send_navigation` swallowed every poller
message (Tab, arrows, leases). Narration kept working because hover uses the
native path. Codex found it by source review and reproduced the Python half
offline. Fixes: Flash `A11yMsgHook` now posts `startup-v11-native` when it
leaves startup mode (native command path, since the flag is already false) and
`a11y.mark` is exempt from the 40/s socket limiter; Python (Codex)
`tyjokr_a11y_startup.py` keeps transport mode marks across the client switch,
exempts them from the full-queue drop and ignores non-mode startup marks
(`tools/test_startup_v11.py`, 13 checks). Candidate: `build/startup-v11-candidate-1.128.90-fix1/`, DEPLOYED 14:41 and
LIVE-VERIFIED 14:43 (Run A reproduced on the unfixed build, Run B green:
`startup-v11-native` at the transport switch, Tab/arrows narrate Skills rows).
Previous pair in `build/deployed-before-fix1/`. Collaboration record: COLLAB-CLAUDE-CODEX.md.

Live bug found by Codex on fix1 (14:53): Flash `A11yFenceOpeningInput` posts
`a11y.inputfence` with an empty payload; through the native command wrapper that
payload arrives positionally and `keys.a11y_inputfence(_connection=None)` raised
"got multiple values for argument _connection" (console error after
`a11y.menu window`). Fix (Codex): `a11y_inputfence(payload: str = '', _connection=None)`
+ two tests in `tools/test_keyboard_v10.py`. All other Flash-posted commands
already take an optional positional string (checked). Ships in fix2.

SHIPPING-CRITICAL (found 15:05 via Codex's audit): every V11 candidate archive
(09-16, 1.128.90 re-base, fix1) omitted the `ctypes/` subpackage that the V9.6
archive ships (TS4's base.zip has no ctypes; keys.py needs it for the hook and
the poller). It worked on this machine only because tyjokr_EngineModding
.ts4script also ships `ctypes/`; a player's install would log "keys: ctypes
unavailable, keyboard navigation off". Cause: `build_startup_v11_candidate.py`
compiled `source/Scripts/*.py` flat. Both it and `tools/build_script_archive.py`
now call `compile.build` (recursive walk, no deploy). fix2 archive = 18 members.

**fix2 = full V11 chain, DEPLOYED 15:13 and LIVE-VERIFIED 15:22** (`build/fix2-v11-full/`:
UI 18,854,670 B sha 0e8f20d1..., script 241,760 B sha d1f3e21a..., compat
4,689,767 B sha db87401b... STAGED not installed; main gate 61, compat gate 19;
verification.json + run-c-log.txt there). All 23 patched movies now carry the
V11 template; AgeUpPanel keeps EA's TooltipManager by design. Chain now takes
`-Work` (default work-1.128.90). Previous installed pair: build/deployed-before-fix2/.

**fix3 / fix4 (2026-09-24 afternoon, Claude + Codex):** (a) Return to the main
menu from a lot never re-armed startup mode: `A11yStartupZoneless` now reads
EA's `UIManager.mGameState` (public field, updated on every GameStateChanged;
found by walking up from the tooltips layer): MAIN_MENU/ENTER_MAIN_MENU ->
startup, PLAY/BUILD -> native, CAS -> startup unless a zone was seen since the
menu; diagnostic mark `gamestate-<n>` on change. Live PASS (lot -> menu ->
CAS). (b) CAS ring: Help Center / Floor Buttons / Scenario Requirements are
live but OFF the stage (x 1810-1887 on 1693 px) -> `A11yIntersectsStage` at the
collector leaf, with `A11yCanRevealOnStage` exempting rows inside EA's static
scrollers (mScrollerView/mcView/mcScheduleView + mcMask). (c) CAS name banner:
EA's CASNameFieldMain puts an alpha=0 btnTextEffect over a static label, so
neither was focusable; `A11yCASNameLabel`/`A11yActivateCASName` (Codex) make
the label the target and route Enter to the button. (d) Settings row-1 flip
and a stray "Manage Worlds" activation: the cheat console's Enter leaves its
tap latch behind and the poller read it after the editing flag cleared ->
A11yActivate on the next focused control; keys.py `_loop` now retires
activation taps on the editing True->False transition. (e) Scanner chords go
to the walker whenever anything (incl. HUD browsing) owns focus, by design;
`a11y.scan` from the console proved the scanner itself works (275 items).
(f) Diagnostic: `mA11yDiagInspectOnTab` template flag (false) that the
candidate builder's source_transform flips; `A11yInspectGeometry` adds
bounds/onstage/covered/clip to every inspect target line (covered is
unreliable, do not filter on it). Candidate `build/startup-v11-candidate-fix4/`
(Gamedata-only over fix2 + rebuilt script); full chain still required before
release. Test driver `tools/gamedrv.py`: never press Escape after a console
Enter (EA closes the console itself; the Escape opens the pause menu).

**fix4 LIVE ACCEPTANCE PASS 16:36-16:41** (build/run-d/fix4-log.txt): CAS ring
clean of the three offstage GameTray targets, name label reached, Enter on it
opens native editing, Cancel -> Leaving So Soon -> Main Menu -> startup live,
Resume -> native mark, console `a11y.menu window` no longer flips row 1.
Codex then runs the full 24+6 chain (`-Tag fix4-v11-full`) and the final
deploy/smoke incl. TEST-V11 items 8/9 (never tested before).
STILL OPEN after fix4: (1) "Close - ESC" is a Tab stop in the leave dialog
(user rule 2026-09-15: never focusable); (2) no "First Name" announcement
after Enter on the name label (clicking it narrates); (3) release chores:
strip `piecreate` mark in PieMenuMain.as, logging default off, strip_pyc_paths,
compat package ships in the release zip, CurseForge update + glaroc credit.

## 2026-09-22: game patch 1.128.90, V11 candidate re-based (no source changes)

EA replaced UI.package; the 09-16 candidate was on 1.127.41 movies. Rebuilt on the
1.128.90 originals over an exact-V9.6 re-based base and installed to the OneDrive
working folder (09-16 pair backed up beside it). NOT live-tested. Everything about
it, including the traps (the deploy/restore helper still targets the old dirs) and
how to redo it next patch, is in **REBASE-1.128.90.md**. The Tab/arrow regression
below is still open and unchanged.

## Current: 2026-09-16 session (Claude, continuing the Codex V10 work)

Running log of what this session changed and why. Newest entries at the
bottom of this section. Read this before touching startup/CAS work.

**State found at start.** Installed files were NOT plain V9.6: the ts4script
and UI package matched `build/startup-cas-candidate-v10-3` (the third startup
socket candidate, deployed 23:37), the compat package was V9.6. The Codex
notes recorded one CAS crash (23:25). The Windows Application event log
(`Get-WinEvent`, Id 1000, TS4_x64.exe) records FIVE crashes with the socket
candidates installed: 23:25:42 CAS, 23:52:51 CAS, 23:54:26 main menu (seconds
after tabbing to a promo "Go Now"), 23:58:48 main menu (0x80000003 assert),
and 00:22:49 during boot with nothing running but the socket ping loop
(mod log ends at "authenticated UI Socket connected", no lastCrash file
was written). Three of the five fault at the same function
(offsets 0x112bd65 / 0x112be33 in TS4_x64.exe, 0xc0000005). None of the
August crash reports share that category, so it is new with the bridge.
Conclusion: the crash is not tied to any menu; the always-open
`flash.net.Socket` transport itself is the suspect (thread/event delivery
race inside Scaleform's socket implementation is the working theory; the
V10 socket PROBE that passed closed its listener right after the proof).

**Checkpoint.** `build/checkpoint-codex-2026-09-16/` = full copy of the
source tree as Codex left it (`source/`, 205 files, excludes build/ and the
regenerable work/reference dirs) plus the four installed files and logs
(`deployed/`), with SHA-256 of everything in `manifest.json`.

**Change 1 (00:2x): V9.6 restored to Mods.** Ran
`tools/deploy_startup_cas_candidate_v10_3.ps1 -Restore` (Codex's own guarded
helper). Live ts4script and UI package now hash-match
`build/v9_6-verified-artifacts`; compat package unchanged (V9.6); cfg
untouched. Reason: a build that crashes at boot and at the main menu is worse
for a blind player than no main-menu speech. The V10 source tree is untouched;
the socket bridge is being reworked as a separate candidate before it goes
back in.

**Live findings with the candidate before the restore (my own driver, slow
input):** New Game -> story prompt scoped correctly; Tab and Shift+Tab could
NOT leave "Okay!" (every press re-announced it) while Right/Left arrows moved
between Okay!/No thanks! (A11yTabMove vs A11yArrowNav difference, to fix);
14 slow Tab stops through the CAS editor, a 4 s settled focus on Gallery and
Enter on Cancel ("Leaving So Soon?") all survived. CAS Tab order visits the
GameTray HUD buttons first (Save Household, Gallery, Marketplace, Identity,
Notification Wall, Options Menu, Help Center, "Floor Buttons", "Scenario
Requirements") before any CAS content; the last two are not meaningful in CAS.

**Tooling added (scratchpad, not shipped):** a Python SendInput driver with
real key-hold control, a foreground guard (refuses to inject unless the game
window is in front), window-only screenshots and mod-log tailing. It proved
Ctrl+Alt chords and Tab/arrow narration end to end. Rule for this machine:
never drive the window while the user is at the computer without telling them.

**Change 2 (00:3x): V11 startup transport, built as a Gamedata-only candidate,
NOT deployed.** Sources: `tools/startup_v11_methods.as` (new Flash section,
replaces the V10 one), `tools/apply_startup_v11.py` (applied once to
`flash/TooltipManager_patched.as`; exact anchors, refuses to run twice),
`Scripts/tyjokr_a11y_startup.py` (rewritten), `Scripts/tyjokr_a11y_settings.py`
+ `tyjokr_a11y_menu.py` + `tyjokr_a11y_lang.py` + narrator readout (new cfg
switch `[features] startup speech = on`, default on), `tools/test_startup_v11.py`
(replaces the two V10 startup tests, deleted), `tools/build_startup_v11_candidate.py`
and `tools/deploy_startup_v11_candidate.ps1` (-Restore puts V9.6 back).
Candidate at `build/startup-v11-candidate/` (24 resources, only
ClassLibraryGamedata changed, 1,077 classes preserved, gate PASSED, 16 Python
modules). Final rebuild (after Change 3): ts4script 225,263 B sha256
17c22b2d... is the UI package (18,703,025 B), 36e7a5f7... the ts4script; full
hashes in its `verification.json`. Offline: 259 checks / 19 suites green,
`build/v10-checks.json` passed on stable inputs. Live checklist: TEST-V11.md. Design, and why:
- The socket is OUTBOUND ONLY. Flash writes `HELLO|A11Y_STARTUP_V2|<port>`
  then `POST|<channel>|<payload>` lines; Python never writes a byte, so no
  socket data event is ever delivered into the Flash VM. No challenge, no
  PING/PONG, no CONFIG, no NAV. Reason: every V10 crash had inbound socket
  traffic as the only common factor (see the crash table above).
- Keyboard mode is signalled by the port Python listens on: 45993 = keyboard
  on, 45994 = speech only. Flash alternates ports on connection refusal and
  calls A11yKeyboardOn/Off on connect.
- Before a save loads, Tab/Shift+Tab/Enter/Space/Backspace/Escape/arrows are
  handled by the EXISTING native InputAction guards: the guard callback queues
  the key (`A11yStartupKey`) and `A11yStartupDrainKeys` runs it on the next
  frame (never inside EA's input dispatch). `A11yGuardValid` returns true in
  startup mode except inside a text field; held-key flags are not set in
  startup mode (Python could never clear them). Flash self-renews the
  keyboard lease each frame while zoneless.
- Zoneless detection is Flash-side: `A11yStartupZoneless()` = the main-menu
  dock (`GameEntryDock`) is visible, or no `A11yHook` has arrived since boot
  (Python sends A11yHook at every zone load; A11yMsgHook now sets
  mA11yZoneSeen and clears queued keys/held flags). Python's
  `send_navigation` returns True (swallow) while connected and zoneless so the
  poller stays quiet; in a loaded zone nothing changed.
- Also folded in: `A11yTabControl` walks controls with `A11yTabMove` when the
  scope holds a single control group (fixes Tab stuck on "Okay!" in the CAS
  story prompt); `A11yFenceOpeningInput` drops queued startup keys.
Offline: `tools/test_startup_v11.py` 10 checks; `tools/run_checks_v10.py`
green after the settings-row addition (see below). Live acceptance pending:
boot x3, main menu Tab/Enter/Escape, New Game, story prompt Tab, CAS editor,
Cancel back to menu, Resume Game then return to menu (dock detection).

**Change 3 (00:5x): accessibility hub rows carry the active Sim's thumbnail.**
`Scripts/tyjokr_a11y_hub.py` `_window` now uses the object picker with
`ObjectPickerRow(icon_info=IconInfoData(obj_instance=active_sim))` instead of
text-only `BasePickerRow` rows. Reason: TEST-V9-6 follow-up "the hub has
missing-image placeholders" (text rows draw a broken image per row; object rows
with a real thumbnail do not, same pattern as the scanner window). The
"incorrect confirmation-button help" follow-up was already fixed in the V10
lang text ("Enter opens the highlighted action"). `tools/test_hub_v7.py` stub
extended for ObjectPickerRow. Needs a loaded-zone live check (a11y.hub).

**Live findings still to fix (window needed):** in CAS the stage-level Tab
order starts with GameTray buttons, including ones not drawn in CAS ("Floor
Buttons" = ChangeFloorButtons, "Scenario Requirements", "Identity", "Notification
Wall"); they pass A11yIsLive + bounds, so they are probably masked or clipped
rather than hidden. The CAS name field ("Hello, My Name Is...") was never
reached by Tab, so it is not collected at all. Independent CAS needs its own
scope/ordering pass; not started.

**Support note for the user (Natalie's silent NVDA):** the speech-pack search
already walks the whole Mods tree (speech.py `_find_dlls`), so DLL placement is
not the cause. The remaining explanations are (a) the ts4script nested more
than one folder deep in Mods (Python never loads; the UI package still loads,
so everything looks installed but nothing speaks), (b) the SpeechPack zip not
extracted at all AND the SAPI child failing, (c) script mods disabled. Ask her
for the Mods folder layout and for `tyjokr_ScreenReader.log` with
`[speech] logging = on`. Proposed (needs sign-off, player-visible): with V11 the
Flash side can tell Python is absent (both ports refuse for 60 s) and could show
a caption "Screen Reader script not loaded"; Python could show a one-time
notification naming its speech backend when the pack is missing.

**Live run 1 of V11 (00:53-00:57, candidate deployed 00:5x):** boot clean;
listener on 45993; `UI Socket connected (outbound only)` 14 s after the
listener; `keyboard-native-guards-11` and `startup-v11-...-active` at the main
menu; Tab narrated Options/HOME/MARKETPLACE/promos/Resume/Load/New Game;
Shift+Tab went back; Enter on New Game reached the story prompt, scoped, and
**Tab now alternates Okay!/No thanks!** (bug fixed). No crash in the session.
Two new findings: (1) after ~20 Tab presses inside a story dialog the focused
answer was ACTIVATED without Enter (the story quiz started, then advanced):
the single-group Tab branch called A11yTabMove, whose list-index path selects
picker cells, and a CAS story answer list treats cell selection as pressing
the answer. Fix applied to the template: that branch now tries
A11yGroupArrow(direction) (plain focus, what arrows use) before A11yTabMove.
Candidate rebuilt; pending live re-check. (2) Escape inside a CAS story
question does nothing (EA has no cancel there); only the CAS X button leaves.
A blind player who answers "Okay!" by mistake is stuck in the quiz unless
Escape maps to the CAS cancel in that state. Not fixed yet. Also seen: when a
story dialog swaps to the next question the walker briefly narrates the
disabled toolbar ("Unavailable while creating a Sim's story."), cosmetic.

**Live run 2 of V11 (01:00-01:03) and run 3 (01:08-01:11):** boot clean twice
more (three clean boots total, no crash in any V11 session). Story-prompt Tab
fix confirmed; the accidental answer activation did not recur after the
A11yGroupArrow change; the quiz question IS spoken (one utterance with the
first answer; any following key or hover interrupts it). Resume Game loaded the
household and the log showed `transport switched to native loaded client`, BUT
in-zone keyboard was dead (no narration, no key lines): Flash still believed it
was zoneless, handled keys natively and posted narration to the socket, which
Python dropped in-zone. Fix (in source, candidate rebuilt, NOT yet live-tested):
`A11yStartupZoneless` returns false whenever the HUD is live (SimInfoTray or
BuildBuyNavigation), any `A11y*` message arriving through the game-message
callback marks the zone as seen, Flash posts `startup-v11-active` /
`startup-v11-native` marks on every mode change, and Python's
`send_navigation` swallows the poller only while Flash reports startup mode
(`note_mark`, also fed by the native `a11y.mark` command); socket posts are
now dispatched in every game state. New CAS bug seen in run 3: after Tab
reaches Cancel in the CAS editor, focus cycles Randomize from Gallery /
Cancel / List Toggle forever (the scope collapsed to a three-control container;
in Codex's run Tab wrapped to the top of the screen instead). Diagnostic build
`tools/build_startup_v11_diag.py` -> `build/startup-v11-diag` posts an
A11yInspect dump after every startup-mode Tab; run it once in CAS, read the
`UI inspect:` lines, fix the real cause, then delete the diag build.

**User decisions (2026-09-16 01:2x), main menu:** (1) the Tab ring at the main
menu is ONLY Resume Game, New Game, Load Game, Gallery, Play Scenario; promo
cards, HOME/MARKETPLACE tabs, the coin balance and the Options button leave the
ring. (2) Escape at the main menu must reach the game (native Options menu);
our Escape still closes our dialogs/the interstitial when one owns focus.
(3) Auto-dismiss the marketplace interstitial at the main menu when keyboard
navigation is on (sighted speech-only users keep it). None implemented yet;
the diagnostic dump of the dock is the first step.

**Diagnostic run (01:22-01:28) and run 4 (01:30-01:34), all with V11, no
crash.** The CAS Tab trap was diagnosed with `build/startup-v11-diag`: the scope
was the whole stage (29 targets); each Tab from Cancel focused
`CharacterFilterTab/btnListToggle`, whose reaction to our synthetic hover
snapped focus back to Randomize from Gallery. Fix: `A11yKeyboardDecoration`
now skips `CharacterFilterTab`; confirmed in run 4 (Tab reached Cancel, Enter
opened "Leaving So Soon?"). Main menu mapped: the five buttons are the
children of `widgets.GameEntry.Launcher.controls::LauncherNavigation/mcNavigation`
under `GELauncherMain` (widget name `GameEntryLauncher`); promos are
`EngagementCarousel` cards, tabs are `LauncherInfoPanelTabButton`, the coin
balance is `VirtualCurrencyWalletAddButton`. Implemented (template, candidate
rebuilt, deployed, confirmed in run 4): `A11yLauncherNavigation()` becomes the
focus scope whenever the launcher is on screen, no HUD, no dialog: focus lands
on Resume Game automatically, Tab cycles exactly the five buttons; Escape is
NOT consumed for that scope so the game's Escape menu opens natively (seen:
`EscapeMenuMain` owner, "Save" narrated), and a second Escape closes it with
focus back on the ring. Startup-mode Escape now calls A11yDismiss directly
(A11yEscape needs a held flag Python never sets pre-zone). Interstitial
auto-dismiss implemented (`mA11yInterstitialAt`, 600 ms after it takes focus,
keyboard on only) but NOT yet exercised: no interstitial appeared in runs 2-4.
Still pending live: in-zone keyboard after Resume Game (the HUD/marks fix) and
returning from a loaded lot to the main menu (launcher scope again).

**Runs 5-6 (01:36-01:43) and session close.** Run 5: in the lot, narration
worked but keys were dead and Flash never posted `startup-v11-native`; the
startup frame handler was registered on the Stage and stopped firing after
the save loaded. Fix: `A11yStartupInstall` now adds the ENTER_FRAME listener
on `mTooltipsLayer` like A11yModalFrame (Change 4). Run 6 with that build:
Tab in the lot entered the Inventory panel and read items, Escape closed it,
the Escape menu narrated Save / Menu / Close. The `-native` mark still never
appeared in the log (the socket most likely dropped at zone load, which also
explains why the poller was not swallowed); Better Exceptions flagged a UI
exception at 01:43:11 (BE-UIExceptionReport.html rewritten, no new
lastUIException file; the last one is still the 22:28 InputDelegate null).
**The user reports a regression in Live-mode Tab and arrow navigation with
the V11 candidate and will debug it next week.** Hypotheses to check first:
(1) `A11yStartupConnected` calls `A11yKeyboardOn()` on every (re)connect,
including a reconnect inside a loaded lot, which resets the lease, reinstalls
guards and sets `mA11yAutoFocus = true` regardless of the cfg (auto focus is
OFF in this cfg); (2) startup-mode guard rules leaking into the zone when
`mA11yStartupActive` is stale (socket dropped without a mode mark); (3) the
launcher-scope selection running in-zone if `A11yLoadedWidget("GameEntryLauncher")`
stays live; (4) compare against V9.6 in the same lot before blaming V11.
Reproduce with logging on and `a11y.inspect` after each Tab.

**Installed at session end:** the V11 candidate (`build/startup-v11-candidate`,
ts4script + UI package) with the V9.6 compat package. To play on the stable
build: close the game and run
`powershell -ExecutionPolicy Bypass -File tools/deploy_startup_v11_candidate.ps1 -Restore`
(restores the exact V9.6 files it backed up; verify with the hashes in
`build/v9_6-verified-artifacts/v9_6-verification.json`). If the helper refuses
because the candidate was rebuilt, copy the two files from
`build/v9_6-verified-artifacts/` into `Mods/tyjokr_ScreenReader/` by hand.
V11 crash record: seven boots, ~6 CAS entries, 3 lot loads, ZERO crashes
(V10 had five in one evening). The diag build (`build/startup-v11-diag`) is
never to be shipped; delete it when done. Full V10+V11 unified pipeline
(`flash/chain.ps1` over all 24 movies + compat gate + verify) has NOT been run
on the V11 template yet; do it only after the Live-mode regression is settled.


## Previous: V9.2 live-test corrections deployed (2026-09-15)

V9.2 adds linked Needs-control mapping, atomic filter labels/checkboxes,
filter-popup dismissal through its actual owner, popup return-focus history,
and a native ownership check for physical Escape. It includes V9.1's null guard.
See TEST-V9-LIVE-2026-09-15.md for observed results and remaining blockers.

133 offline checks, 61 main and 19 compatibility comparisons passed. All three
installed hashes match `build/v9_2-verification.json`; deployment evidence is
`build/v9_2-deployment.json`. The cfg was preserved. V9.1 rollback files are in
`build/deployed-before-v9_2`, source in `build/source-before-v9_2`.
Build tag `keyboard-v9_2-final`; compatibility log `gate-compat-v9_2.log`.
Use `tools/verify_v9_2_artifacts.py` and `tools/deploy_v9_2.ps1` for this source.
Shipping remains 24+6. No CAS or EngagementLibrary expansion.

## Previous: V9.1 null-scope correction deployed (2026-09-15)

Agent-driven testing reproduced V9 claiming panel keyboard ownership without
entering its focus scope. `A11yIsInside` now rejects null arguments before
calling Flash `contains`. See TEST-V9-LIVE-2026-09-15.md for the observed
failures and ongoing in-game retest. The 130 existing offline checks and
61 main / 19 compatibility comparisons passed. Source/artifact verification
passed and the installed hashes match. Cfg preserved; V9 rollback is in
`build/deployed-before-v9_1`.

Build tag: `keyboard-v9_1-final`; compatibility log: `gate-compat-v9_1.log`.
Use `tools/verify_v9_1_artifacts.py` and `tools/deploy_v9_1.ps1` for this source.
Evidence is in `build/v9_1-verification.json`, `build/v9_1-deployment.json`,
and `build/v9_1-source.diff`. Shipping remains 24+6. No CAS/Engagement expansion.

## Previous: V9 feedback fixes deployed (2026-09-15)

The latest player results are recorded in FEEDBACK-V8.md. V9 is installed.
All three live hashes match staging, the game was closed, and the user's cfg
was preserved. V8 rollback files are in `build/deployed-before-v9/`.
130 offline checks passed, along with 61 main and 19 compatibility targeted
comparisons. Artifact verification confirmed 14 source-matching Python 3.7
modules, exact 24+6 resources, unchanged class sets and non-code movie tags.
Evidence: `build/v9-verification.json`, `build/v9-deployment.json`,
`flash/chain-keyboard-v9-final.log`, `flash/gate-compat-v9.log`.

See TEST-V9.md for the retest and KEYBOARD-V9.md for implementation and limits.
V9 addresses scanner refresh/categories, stale panel/pie ownership, atomic
Needs, inventory tooltip interruption, filter popup capture, Stay Over and
Holiday focus, event progress controls, close-button entry order, calendar
header/Busy names, phone paging, mood label hover and career/completion stops.
The inventory sell BE error has an input-isolation mitigation; the error's
source and runtime resolution are not proven. Calls/texts remain untested.

V8 source, player log/BE report and live artifacts/cfg are preserved in
`build/source-before-v9/`. Source diff: `build/v9-source.diff`.
Use `tools/verify_v9_artifacts.py` and `tools/deploy_v9.ps1` after both gates
pass. Shipping stays 24+6, excludes EngagementLibrary/CAS, and preserves cfg.
No release-sibling edits. Never rerun the one-shot `tools/edit_feedback_v9.py`.
The V7 startup probe remains separate/uninstalled and needs rebasing.

The first pipeline passed before final review corrections. Its logs are
`build/v9-first-pass-main.log` / `build/v9-first-pass-compat.log`. A subsequent
header-order pass was stopped during its gate to correct CLIK key tracking;
`build/v9-interrupted-header-pass.log` preserves that history. Only the final
logs above approve the installed files. The final guard intercepts processed
InputDelegate events, never raw key-downs, and does not dispatch navigation.

## Historical: V8 feedback fixes deployed (2026-09-15)

The user finished the V7 feedback round. **Calls/texts remain untested**:
no incoming call occurred. Preserve that item on the blockers list.
The actual V7 results are in [FEEDBACK-V7-ROUND2.md](FEEDBACK-V7-ROUND2.md).

V8 implements owner release after closing UI; nested panel scrolling;
dropdown capture/return; grouped filters and calendar cards; spatial grids;
one Needs row with native solve activation; inventory hover, stack controls
and native multiselect selling; panel names/max height; phone apps first;
dialog opening narration; workday names; calendar offsets/tooltips/Add labels;
and targeted household-funds/current-mood speech suppression.

See [TEST-V8.md](TEST-V8.md) for the runtime retest and
[KEYBOARD-V8.md](KEYBOARD-V8.md) for implementation details and limitations.
New relative-day/workday prefixes currently use English; EA weekday/event
text remains localized. No V8 runtime pass is claimed. Main-menu speech,
CAS and the other gaps in INTEGRATION-STATUS-V7.md remain incomplete.

V8 is installed. Seven offline suites passed 123 checks; the final main gate
passed 61 targeted comparisons and the compatibility gate passed 19. The
artifact verifier confirmed all 14 Python 3.7 modules match current source,
the exact 24+6 resource sets, unchanged class sets and non-code movie content.
All three deployed hashes match staging; the user's cfg was preserved.
Final evidence paths:
`flash/chain-keyboard-v8-final.log`, `flash/gate-compat-v8.log`,
`build/v8-verification.json`, `build/v8-deployment.json`.
Use `tools/verify_v8_artifacts.py` and `tools/deploy_v8.ps1` for V8.
The shipping scope stays at 24 main movies and six UI Cheats movies.
No EngagementLibrary or CAS overrides, and no release-sibling edits.

V7 sources, installed artifacts and test log were saved in
`build/source-before-v8/`. Deployment saves the live V7 files and cfg in
`build/deployed-before-v8/`, checks the game is closed and preserves the cfg.
The first V8 pipeline passed; `build/v8-first-pass-chain.log` preserves it.
The final pass additionally preserves Needs percentages, filter selection
and dropdown-return narration. Do not rerun the one-shot edit/finalizer scripts.

The final Python sweep also fixed key-up handling when entering scanner
chords while a plain arrow was held: release is forwarded while Ctrl+Alt
remains down, fresh hook state overrides stale polled state, and a dead
hook retains its polling fallback. Three additional regression tests cover
these cases. The source diff is `build/v8-source.diff` (five source files).

The V7 startup probe remains separate and uninstalled. Rebase it before
testing it alongside V8 so its older UI package cannot replace V8 fixes.

## Historical: V7 keyboard test build deployed (2026-09-15)

The user completed their feedback and authorized fixes and broader overnight
integration work, including main-menu research. **V7 is now installed**, with
the game closed, all three deployed hashes verified and the existing cfg
preserved. V6 rollback files are in `build/deployed-before-v7/`. The release
sibling is untouched. No in-game V7 pass is claimed.

Start with [TEST-V7.md](TEST-V7.md). The full reported-issue checklist is in
[KEYBOARD-V7.md](KEYBOARD-V7.md), the remaining glaroc/planned scope in
[INTEGRATION-STATUS-V7.md](INTEGRATION-STATUS-V7.md), and the isolated startup
investigation in [STARTUP-PROBE-V7.md](STARTUP-PROBE-V7.md).

- Tab/Shift+Tab is separate from row navigation, remembers list position and
  exits text fields. Arrows use an indexed-list fast path. Purchase Enter
  focuses Done; Backspace returns to the row. Sim selection is one press.
- Native EA InputActions guard camera/navigation keys while a UI owns focus;
  Python polling drives actions once. Native guards use a two-second lease.
  Duplicate capture/bubble Flash keyboard listeners are removed. These are
  source-based fixes, not proof of the exact runtime causes.
- Panels, phone and pies participate in focus ownership; Escape closes the
  current surface. Profile informational cells and calendar entries become
  keyboard targets. The calendar grid moves by day/week.
- Final list focus is re-read after scrolling settles, then its native
  tooltip is re-armed. Non-list hover narration keeps its existing path.
  Mood rollover is limited to the mood text bounds.
- Household phone/text alerts announce the recipient; Ctrl+Alt+P opens that
  Sim's alert after the user closes the current panel/dialog. No auto-answer.
- Ctrl+Alt+H opens a common-actions picker: status panels, current action,
  self interactions, household Sim selection, funds, calendar and settings.
  Keyboard is now the focus/capture master switch. Numpad navigation is an
  optional fallback; punctuation and speech-mode cycling keys are retired.
- Main-menu speech is **still unresolved**. The separate probe tests Flash
  startup, F10 via native input, Python core ticks, both bridge directions,
  and the native UI debug-command registry. It is not deployed by V7.

Verification: 14 Python 3.7 modules, 115 offline checks across six suites,
main gate 61 targeted comparisons, compatibility gate 19, exact resource
sets 24+6, unchanged class sets and non-code movie content, archive/source
match. Evidence: `build/v7-verification.json`, `build/v7-deployment.json`,
`flash/chain-keyboard-v7-final.log`, `flash/gate-compat-v7.log`.
Do not rerun the one-shot V7 migration helpers; current sources are canonical.

## Historical: v6 dialogs and keyboard navigation (2026-09-15)

**The user's "fix them" ended the rebuild hold.** They also requested a sweep
of the existing keyboard code. First-install settings/onboarding remains
deferred. **V6 is deployed for testing.** All three installed files match the
verified build; the cfg was preserved and the game was closed. V5 and earlier
sections below are historical. No in-game v6 accessibility pass is claimed.

See [DIALOG-ACCESSIBILITY-AUDIT.md](DIALOG-ACCESSIBILITY-AUDIT.md) for the
confirmed pre-v6 defects and implementation, and the v6 section of
[SCANNER-TEST.md](SCANNER-TEST.md) for keyboard-only runtime acceptance.

- Real dialog buttons are separately focusable/activatable; wrappers no
  longer swallow the footer. Active modal lifecycle and LayoutManager's top
  modal widgets own focus and scanner chords. Read/dismiss use the active UI.
- Picker navigation retains row indices and rapid inputs, scrolls only enough
  to reveal the target, and refreshes focus after the child picker loads.
- Age-up and trait reassignment have dedicated hooks, including trait Remove,
  aspiration choices and name entry. Disabled/required-selection rules remain.
- UI navigation dispatch now uses the simulation-thread pump; short native
  chord taps are retained; typing fields exclude conflicting navigation keys.
  Tolk failure falls back to NVDA/Windows speech, with Polish regression checks.
- Shipping scope is **the original 23 movies plus AgeUpPanel**, with six UI
  Cheats overrides. AgeUpPanel patches only AgeUpPanelMain; its shared classes
  remain original. EngagementLibrary and every CAS movie are excluded.
  The 135-definer audit is retained as an inventory only: prior in-game marks
  prove ClassLibraryGamedata wins the shared class. The expansion was an
  incorrect coverage inference, stopped before deployment at the user's
  correction. Do not re-expand without runtime evidence and user direction.

The pump change is retained deliberately: the distributor reads/clears its
journal without a thread lock; keyboard-thread writes could race with that.
This was not an observed cause of the reports. Walker delivery now requires
the live lot's pump, whose wall-clock alarm works while gameplay is paused.
Pre-lot/main-menu delivery remains unavailable and CAS has a separate stage.

Offline tests: 9 v5 checks and 9 v6 checks passed. Final build log
`flash/chain-navigation-v6-final.log` ends CHAIN DONE; main fidelity gate passed
61 targeted comparisons. `flash/gate-compat-v6.log` passed 19 comparisons.
`tools/verify_v6_artifacts.py` verified all 12 archived Python 3.7 modules and
all 30 movie resources, including unchanged non-code tags and class sets.
`build/v6-verification.json` records source/artifact hashes;
`build/v6-deployment.json` records installed hashes and paths. Deployment used
`tools/deploy_v6.ps1` after both gates passed, without recompiling the archive.
Backups: `build/source-before-v6/` and `build/deployed-before-v6/`.
The verifier enforces the exact 24-movie scope in `build/v6-shipping-movies.json`.

| Installed artifact | Bytes | SHA-256 prefix |
|---|---:|---|
| `tyjokr_ScreenReader.ts4script` | 186,937 | `e5c3434b92af5ef0` |
| `tyjokr_ScreenReader_UI.package` | 18,435,947 | `eb2af173f24ed888` |
| `tyjokr_ScreenReader_Compatibility_UICheats.package` | 4,582,438 | `53527ac5cbcd1389` |

The stopped 135-movie attempt is recorded in
`flash/chain-navigation-v6-superseded-135.log`; none of that expanded package
was deployed. Extra scratch SWFs on disk are not shipping resources.

Glaroc's server-side dialog-answer fallback remains unintegrated; it cannot
substitute for client-only dialogs or the payload required by age-up. Other
remaining features are listed in section 5. No in-game accessibility pass has
been recorded for v6, and the initial NVDA-silence report has no tester log.

## Continuation: v5 (2026-09-15)

**This section supersedes the v4 settings and first-run instructions below.**
The user deferred the first-install popup in this session. No automatic
popup or spoken welcome now runs; revisit onboarding later with the user.

**v5 is deployed for testing.** The game was closed; all three installed
files hash-match the verified build and the existing cfg was preserved.
Captions therefore remain off until enabled in-game.

| Installed artifact | Bytes | SHA-256 prefix |
|---|---:|---|
| `tyjokr_ScreenReader.ts4script` | 185,397 | `fe9472aa70c887c0` |
| `tyjokr_ScreenReader_UI.package` | 17,642,544 | `39c5cee0abdb163c` |
| `tyjokr_ScreenReader_Compatibility_UICheats.package` | 4,566,575 | `a9f960490b625f8f` |

Evidence: `flash/chain-captions-v5-final.log` ends `CHAIN DONE`, main fidelity
gate passed 60 targeted comparisons; `flash/gate-compat-v5.log` passed 19
targeted comparisons. Both packages passed resource round-trip checks.
`build/v5-verification.json` contains full source/artifact hashes;
`build/v5-deployment.json` contains the installed paths and hashes.
The script was built through `compile.build('build')` under Python 3.7,
then that exact verified archive and both packages were installed with
`tools/deploy_v5.ps1`. Installed v4 files and cfg are backed up in
`build/deployed-before-v5/`; the release tree remains untouched.

- Typing fix: the low-level hook is armed only while Ctrl+Alt is held,
  the game has focus, and keyboard/scanner/swallow are enabled. Shift and
  AltGr leave it uninstalled. The hook loop checks every 5 ms when Python
  is scheduled; this is not a latency guarantee under GIL contention.
  Dropped-hook recovery is retained and loop failure cleans up the hook.
- Settings: `a11y.menu window` (also `open` / `toggle`) opens the visual
  picker only. No Ctrl+Alt+U, no spoken settings navigation or key capture.
  Clicking numeric rows advances their value and wraps at the maximum.
  All cfg options, including captions, have a row. The old scanner picker
  remains under `a11y.scanview` for diagnostics only, outside settings.
- Captions: `[features] captions = off` by default; toggle with the settings
  row or `a11y.captions on|off`. The final `_speak_now` output, after mode
  suppression, burst thinning and deduplication, queues `A11y|cap|...` on
  the simulation pump. This also covers repeat and delayed narration.
  UTF-8 percent encoding escapes pipes, quotes, percent and non-ASCII;
  text is capped at 480 characters including an ellipsis when truncated.
- Flash: one reusable noninteractive Sprite/TextField on the tooltip layer,
  bottom-centre, white `$TextFont` over a translucent background. Expires
  eight seconds after the latest announcement; off clears the caption.
  Repositions on stage resize/restaging. No per-announcement TextFields.
- Limits: no live lot/pump means no Python-to-Flash caption. Main-menu and
  CAS support is not proven; CAS retains the existing separate-stage issue.
  Caption timing follows accepted narration; queued audio backends do not
  expose playback completion, so exact audio/caption synchronization is
  not claimed. In-game Unicode, long-message delivery, layout, typing and
  camera behavior still need testing.
- Offline regression suite: `py -3.7 tools/test_scanner_v5.py`, 9 checks
  passed. Python 3.7 build contains 12 modules. Build/deploy evidence is in
  `SCANNER-TEST.md` under v5 and the files in `build/`.
- `py -3.7 tools/verify_v5_artifacts.py` verified the 12 archived modules
  against current source and all 29 movie resources against their rebuilt
  SWFs, including caption symbols in every TooltipManager copy.
- `flash/chain.ps1` now uses `py -3.7`, a writable isolated FFDec APPDATA
  under `build/ffdec-appdata`, checked cleanup paths, and external-command
  exit-code checks (stale packages cannot mask a failed build).
  `flash/gate_compat_pcode.py` applies the same fidelity checks to all six
  UI Cheats base movies with fresh exports; run after the chain, never
  concurrently with it.
- Pre-v5 sources are backed up in `build/source-before-v5/`.

The remaining category verification, scanner polish, release work and
larger integrations below remain pending. This is still a development build.

Written for a fresh chat. Everything below is verified unless marked
"presumed". Read section 1 first: it lists what the user actually wants,
including two things the last session got wrong.

## 0. Where things live

| What | Path |
|---|---|
| Working tree (ALL integration work) | `My Script Mods/ScreenNarrator-integration/` |
| Release tree (untouched since 2026-08-28) | `My Script Mods/ScreenNarrator/` |
| Rules for the working tree | `ScreenNarrator-integration/INTEGRATION.md` |
| Flash / FFDec pipeline: tools, rules, commands, gate, packages, deploy | `ScreenNarrator-integration/FLASH-PIPELINE.md` |
| Per-version change list + test plans (v1 to v4) | `ScreenNarrator-integration/SCANNER-TEST.md` |
| Review of glaroc's mod (architecture, API cheat sheet, bugs, builds 2 and 3) | `ScreenNarrator-integration/A11YSCAN-REVIEW.md` (sections 3, 6, 9, 10, 11 matter most) |
| Older reader-side open items (pre-integration) | `ScreenNarrator-integration/TODO-NEXT-SESSION.md`, `HANDOFF.md` |
| glaroc's drops | `Downloads/a11yscan_for_review/a11yscan` (build 1), `Downloads/a11yscan_for_testers/a11yscan` (build 2), `Downloads/a11yscan_2026-09-07/a11yscan` (build 3, CHANGELOG.md + README.md are his own summaries) |
| EA decompile + tuning dump | `EA/simulation`, `EA/core`, `EA/tuning`, `EA/1.127.41.1030-TDESC` |
| Live mod folder | `Documents/Electronic Arts/The Sims 4/Mods/tyjokr_ScreenReader/` (log: `tyjokr_ScreenReader.log`; compat package in `Mods/_priority/`) |
| Claude memory notes | `~/.claude/projects/.../memory/a11yscan_glaroc_mod.md`, `screen_narrator_architecture.md`, `ts4_ui_flash_accessibility_re.md`, `ts4_ui_only_options_dialog.md` |

Deployed right now (dev build, logging on):

| File | Size / hash | Content |
|---|---|---|
| `tyjokr_ScreenReader.ts4script` | SHA-256 starts `79a5ff0e7967e454`, 12 modules | v4: scanner v3 + settings menu (see 1.1) |
| `tyjokr_ScreenReader_UI.package` | 17,636,751 bytes | Flash from the v2 build (loc channel, client-request pie menu, `piecreate` diagnostic still in) |
| `_priority/tyjokr_ScreenReader_Compatibility_UICheats.package` | 4,566,484 bytes | UI Cheats compat, built in lockstep with the above |
| `tyjokr_ScreenReader.cfg` | | `logging = on`, `scanner = on`, `scanner swallow = on` |

Build rules (from INTEGRATION.md, still in force):

- `py -3.7 compile.py` in the working tree DEPLOYS the ts4script into the live
  Mods folder. Only run it when a build is meant to be tested.
- Flash: `flash\chain.ps1 -Tag <name>` = rebuild all 23 movies from
  `TooltipManager_patched.as` + `flash/extra-classes/*.as`, run the pcode
  fidelity gate, build the UI package into `build/`, then the compat package.
  Ends with `CHAIN DONE` or `CHAIN FAILED` in `flash/chain-<name>.log`. Never
  two Flash pipelines at once. Always pass an explicit package output path
  (`build_ui_package.py`'s default output is the PARENT release package).
- Whenever TooltipManager or any of the six UI-Cheats movies changes, the
  compat package must be rebuilt too (chain.ps1 does it).
- Packages can only be copied into Mods while the game is closed. Verify
  every deploy with a hash.
- In patched ActionScript never write `++` or `+=` on ints; write
  `x = x + 1` (FFDec recompile gotcha; the gate compares bytecode).
- EA's exported `.as` files have blank lines of six spaces; patch anchors
  with bare newlines miss.
- Bash heredocs containing Python triple quotes break the tool; write patch
  scripts to files first.

User directives (verbatim intent):

- Honor glaroc's Ctrl+Alt key layout exactly; he chose it for accessibility
  reasons. Do not invent a mode toggle.
- Minimize reliance on string tables; do not invent language where the game
  has words. Every category label and object name is an EA string key
  resolved by the client in the player's language.
- Build only on the release tree clone; the gamepad branch is defunct.
- Be thorough and careful with what is integrated.
- Player-visible design changes need sign-off; fixes are autonomous.

## 1. What the user wants (stated 2026-09-15, overrides earlier guesses)

### 1.1 Settings: a visual window, NOT a spoken menu (yet)

The user asked for "all settings reachable from inside the game" and "the
accessibility menu automatically pops up on first install". The last session
built BOTH a spoken chord-driven settings menu (Ctrl+Alt+U) and a visual
settings window. The user does NOT want the spoken menu yet.

State of the deployed v4 build (`Scripts/tyjokr_a11y_menu.py`):

- Ctrl+Alt+U opens a spoken menu that also shows the settings window; while
  it is open the scanner chords move/change rows. UNWANTED for now.
- The settings window is a `UiObjectPicker` listing every cfg setting as a
  row ("Speech mode: hover", description = what it does); clicking a row
  switches the value and the window returns with the new value. WANTED.
- First run (no cfg at launch): 5 s after the first lot loads the spoken
  menu opens with a welcome line and the window. Should become: window
  only (decide with the user whether one spoken welcome line stays for
  blind users; they cannot see the window).
- Console: `a11y.menu window` shows the window alone; `a11y.scanview` shows
  the scanner window (see 1.3, also unwanted as a window).

To do: gate or remove the spoken part. Smallest change: in
`tyjokr_a11y_keys.py` delete the `0x55: ('settings', False)` chord (and its
CHORD_NAMES entry) so `menu.on_key` is never reached; make `_open_menu`
show the window without setting `_open` or speaking the row list; keep
`a11y.menu window`, `_show_settings_window`, `_on_settings_pick`, and the
first-run timer. `SCANNER-TEST.md` v4 describes the current behavior.

### 1.2 Typing in the game is slow: root cause and fix

Reported 2026-09-15: with the mod running, typing INSIDE the game (cheat
console, naming, text fields) is very slow. Earlier (2026-09-06) the same
lag was reported OUTSIDE the game and fixed by installing the hook only
while the game window is in front. The in-game lag has the same cause.

Cause: `tyjokr_a11y_keys.py` installs a WH_KEYBOARD_LL hook (so Ctrl+Alt+
arrows do not pan the camera). A low-level keyboard hook sits in the
delivery path of EVERY keystroke to the foreground window: Windows calls
our callback and waits for it to return before the key reaches the game.
Our callback is Python (ctypes), so it can only run while it holds the
Python GIL, and the game's simulation thread holds the GIL most of the
time. Each keystroke therefore waits until the simulation thread releases
the GIL, tens to hundreds of milliseconds under load. Windows also removes
a hook whose callback exceeds its low-level hook timeout (the poller
detects that and reinstalls). The work inside the callback is trivial; the
wait for the GIL is the lag.

Fix (not built): keep the hook installed ONLY while both Ctrl and Alt are
physically held. In `_hook_loop` (already polls every 5 ms for messages and
every 50 ms for foreground) add: install when `GetAsyncKeyState(VK_CONTROL)`
and `GetAsyncKeyState(VK_MENU)` are both down and the game is in front;
remove as soon as either is up. The first chord key follows the modifiers
by far more than the loop period, so nothing is missed, and normal typing
never passes through the hook. Keep the existing reinstall-on-drop logic
and the `_hook_state` reporting (a swallowed key never reaches
GetAsyncKeyState, so the poller reads chord keys from the hook while it is
installed; when it is not installed the poller falls back to
GetAsyncKeyState, which already works). If the lag persists even then, the
only fully clean route is a tiny native DLL hook (C, no GIL), which is a
bigger ship item. Test: type in the cheat console with the mod on; then
hold Ctrl+Alt and check the camera still stays put on the arrows.

### 1.3 Scanner visual: an on-screen caption, NOT a selectable window

The user wants to SEE exactly what a blind player HEARS: a text overlay on
the game screen showing the current announcement (category, item, "3 of
12"), updating as the chords are pressed, like a watch face. Not a dialog,
not a list to click. The `a11y.scanview` picker window built in v4 is the
wrong shape; leave it or remove it, but do not extend it.

Design (not built; needs a Flash rebuild):

- Flash side, in `flash/TooltipManager_patched.as`: one caption panel
  (Sprite with a translucent background + one TextField, created ONCE and
  reused, never per message; the Moodlet Panel session's note that
  per-open TextFields crashed at movie teardown applies). Put it on the
  same layer the focus ring uses (`A11yDrawFocusRing`, re-staged by
  `A11yOnLayerStaged`), bottom-centre, wordWrap, `$TextFont` with
  embedFonts. Add a `"cap"` branch to `A11yHandleEncoded`: the payload is
  the message name after the prefix, `decodeURIComponent` it, set the
  text, show the panel, restart a hide timer (8 s or so; the scanner
  announcement should stay until the next one). Keep the panel in the
  tooltip manager so it exists in live mode, CAS and Build/Buy alike.
- Python side: in `tyjokr_a11y_speech.speak()` (the single funnel for all
  narration) when the new setting `captions` is on, post
  `SendUIMessage('A11y|cap|' + percent-encoded text)` through
  `tyjokr_a11y_pump.post` so it runs on the simulation thread (speak is
  also called from the key thread). Percent-encode with the same rules
  `tyjokr_a11y_narrator._decode_percent` expects in reverse. Cap the text
  at a few hundred characters; the message name is a protobuf string and
  the longest payload proven so far is the ~80-character pick message, so
  test length once. Setting: `[features] captions = on/off`, default off,
  console `a11y.captions on|off`, row in the settings window.
- Then `flash\chain.ps1 -Tag captions`, gate PASSED, deploy UI package +
  compat package with the game closed, hash-verify.

Because every utterance goes through `speech.speak`, this shows not just
the scanner but everything the blind player hears (dialogs, hover, menus),
which is what the user asked for.

## 2. What was built (2026-09-03 to 2026-09-15)

All in `ScreenNarrator-integration/Scripts/` unless noted. Module count in
the ts4script: 12.

### 2.1 The scanner (glaroc's idea, our plumbing)

- `tyjokr_a11y_pump.py`: wall-clock alarm on the simulation thread (20 ms,
  fires while paused, dies with the zone, re-armed at every zone load).
  Keys post callables to it; nothing touches game state on the key thread.
  `post()` returns False when no lot is loaded ("No lot loaded" is spoken).
- `tyjokr_a11y_scanner.py`: lists Sims (always) and objects with a player
  interaction within 40 m of the active Sim, distance + compass bearing +
  floor delta from world axes (north = +z), grouped two levels deep (see
  2.2), sorted nearest first. Names: a player-given name is plain text;
  otherwise `obj.catalog_name` is the string-table hash (an int) and the
  client resolves it through the loc channel. Enter opens the game's REAL
  pie menu on the thing (see 2.3); from then on the existing menu
  narration and focus walker take over.
- Loc channel: Python -> Flash `distributor.ops.SendUIMessage` carries
  only a message NAME, so requests are name-encoded: `A11y|loc|<hash>|<hash>`.
  `TooltipManager_patched.as` re-registers the client's ExternalInterface
  `"SendMessage"` callback with a wrapper (`A11yOnGameMessage`) that handles
  `A11y|` names locally and forwards everything else to EA's dispatcher
  unchanged. `loc` resolves the hash with `LocKey.FromHash(uint).toString()`
  via `getDefinitionByName` (LocKey exists in only 3 of 23 movies, never
  static-import it) and posts `a11y.loc_enc "<hash>|<percent-encoded>"`
  back. Python caches the text and speaks once every key of an
  announcement is resolved (0.6 s timeout speaks without the name).
  `A11yHook` is sent at every zone load to re-assert the callback.
- Keys (`tyjokr_a11y_keys.py`, glaroc's layout): Ctrl+Alt + Up/Down =
  previous/next thing, Left/Right = main category, PageUp/PageDown =
  subcategory (v3 addition, free in his layout), Enter = open the menu /
  activate, Backspace = close the menu, S = rescan, W = where am I, R =
  repeat, H = help. While any pie menu is open the same chords walk the
  menu (`MENU_KEYS` -> the Flash walker). AltGr (right Alt on a layout that
  types with Ctrl+Alt) is ignored. The numpad walker bindings are untouched
  and are skipped while a chord is held.
- Console: `a11y.scan [rescan|next|prev|nextcat|prevcat|nextsub|prevsub|
  open|back|where]`, `a11y.menuclosed`, `a11y.menuempty`, `a11y.loc_enc`
  (internal).

### 2.2 Categories (v3, 2026-09-07): the catalog's own two levels

- MAIN category = the buy category the client reports for the object's
  definition: `build_buy.get_object_buy_category_flags(definition.id)`,
  bits from `build_buy.BuyCategory` (APPLIANCES 2, ELECTRONICS 4,
  ENTERTAINMENT 8, LIGHTING 32, PLUMBING 64, DECOR 128, KIDS 256, STORAGE
  512, COMFORT 2048, SURFACE 4096, VEHICLE 8192; bit 1024 is absent from
  the Python enum and is PRESUMED to be Pets). Order = the catalog's
  left-to-right order, Sims first, then BUILD (build-mode tags, no buy
  category: doors, gates, ladders, pools) and MISC (nothing the catalog
  sold). Labels = the catalog's own filter strings from
  `olympus.localization.KeysBB` (ClassLibraryOlympus): BB_FILTER_BUY_COMFORT
  0x785D2B30, SURFACES 0x52B94704, DECOR 0x20173E9E, ELECTRONICS 0x04F9CD4D,
  APPLIANCES 0x506E29A8, PLUMBING 0x43255F8C, LIGHTING 0x04550808, KIDS
  0xFF5F3573, ENTERTAINMENT 0xAB618646 "Activities and Skills", STORAGE
  0xFFCD72A7, PETS 0x0433ACE6, TRANSPORTATION 0x54128E86, BB_NAVIGATION_BUILD
  0x0DD73681 "Build", BB_FILTER_MISCELLANEOUS 0x82815675 "Misc", Sims
  0xBE52D6ED. When several bits are set, the one matching the subcategory
  tag family wins (EE -> Electronics/Kids/Activities/Pets, SS ->
  Comfort/Surfaces/Storage/Pets, PA -> Appliances/Plumbing/Pets, LD ->
  Decorations/Lighting), then catalog order.
- SUBCATEGORY = the object's tag label from EA's client tag metadata, three
  files: `Client_TagsBuildBuy` (125 BuyCat tags), `Client_TagsBuild` (38
  Build_ tags), `Client_TagsFunction` (482 Func_ tags), 645 labels total.
  Priority: buy-mode function tags (EE/SS/PA/LD), then Build_/Terrain,
  then venue/off-the-grid/lot-requirement BuyCat_ tags, then room tags
  (BuyCatMAG_, which v1 wrongly let win: a sofa could read "Living Room"),
  then Func_ tags. `tools/gen_buycat_table.py` regenerates
  `tyjokr_a11y_buycat.py` (TAG_LABEL_HASH, ORDER, GROUP_LABEL_HASH,
  GROUP_ORDER, GROUP_FLAG) from the tuning dump after every EA patch.
- Where the hierarchy is NOT (checked, do not repeat): the tuning dump
  (TagCategories / TagCategoriesMetadata are CAS filter groups; the
  BuildBuy tdescs hold VFX and tints), `UI.package` (contains no tag
  names; Flash gets category ids from native), and the "Comfort"/
  "Activities and Skills" string keys used by account-reward tuning are a
  different key set from the catalog's.
- Announcements: Left/Right "Comfort, 12 items. Sofas, 2 items. Sofa, 2
  meters north."; Up/Down "Sofa, 4 meters east. 2 of 12." and, crossing a
  subcategory, "Living Chairs. Armchair, 3 meters north. 3 of 12.";
  PageUp/Down "Living Chairs, 4 items. Armchair, ... 3 of 12."; W "Bella
  Goth. Comfort, Sofas. Sofa, 2 meters north. 1 of 12."
- Log after a scan: `scanner: N sims, M objects, G categories (items/
  subcategories): SIMS:3/1 COMFORT:12/4 ...` plus up to 12 lines
  `scanner:   MISC|BUILD <definition> flags=0x.. sub=.. tags=..` for the
  catch-alls. These lines settle the Pets bit and show what the leftovers
  carry. NOT YET SEEN: v3 has not been tested in-game.

### 2.3 Opening the real pie menu (v2, confirmed in-game 2026-09-06)

The client discards a PieMenuCreate it did not request (reference-id check
in `PieMenuMain.HandlePieMenuCreate`, and evidently the native layer too),
so a Python `interactions.choices` call never draws. v2 mirrors the mouse
path: Python sends `A11y|pick|<id>|<pickType>|<lotId>|<firstName>|<x>|<y>|
<z>|<level>`; TooltipManager forwards it as UI message `A11yOpenPieMenu`;
`PieMenuMain.A11yOnOpenPieMenu` (in `flash/extra-classes/PieMenuMain.as`)
bumps the client's own request counter, fills a WorldPickResult with the
real coordinates and posts `interactions.choices` through
`CallGameService("PostServerCommand")`, exactly like a click. The reply is
then a menu the client asked for. `Hide` posts `a11y.menuclosed`; an empty
scanner menu posts `a11y.menuempty` ("No options"); the "disabled" reason
is narrated for scanner menus. Diagnostic still in the deployed Flash:
`a11y.mark piecreate-<ref>-<items>-<scanner|mouse>-last<counter>` on every
PieMenuCreate. STRIP BEFORE RELEASE.

### 2.4 Chord key swallowing (2026-09-06, confirmed; see 1.2 for the lag)

Polled keys reach the game, so Ctrl+Alt+arrows panned the camera. No
Python camera lock exists (camera.py is focus ops; Flash 'CameraScrolling'
is a notification; 'SetModalVisible' closes pie menus). The mod installs a
WH_KEYBOARD_LL hook on its own thread (PeekMessage loop) that returns 1
for chord keys while Ctrl+Alt is held, the game is in front and AltGr is
not involved; TS4 reads the message queue, so the block works. Swallowed
keys never update GetAsyncKeyState, so the hook reports them to the
poller via `_hook_state`; a chord key the hook missed triggers a
reinstall. Installed only while the game is in front (removed within 50
ms of focus loss) after the system-wide lag report. cfg `[features]
scanner swallow = on/off`; `a11y.settings` reports the hook state.

### 2.5 Settings menu and windows (v4, 2026-09-15, see 1.1 and 1.3)

`tyjokr_a11y_menu.py`: spoken menu (unwanted), settings window (wanted),
scanner window (wrong shape), first-run trigger (`settings.first_run` is
True when no cfg existed at launch -> zone hook -> 5 s timer ->
`pump.post`). Dialog facts learned: `UiObjectPicker.TunableFactory()
.default(active_sim, title=lambda *a, **k: get_raw_text(..), text=...,
picker_type=OBJECT, min_selectable=1, max_selectable=1)` is the same idiom
EA uses in `server_commands/ui_commands.py`; rows are
`ObjectPickerRow(option_id, name, row_description, tag, is_selected,
icon_info)`; `add_listener(fn)` gets the dialog back (`accepted`,
`get_result_tags()`); `services.ui_dialog_service().dialog_cancel(id)`
closes a dialog WITHOUT calling its listener; pickers are never narrated
by our DialogMain hook, so windows are silent for blind users;
`sims4.localization._create_localized_string(hash)` and
`LocalizationHelperTuning.get_object_name(obj)` render EA keys in a
dialog; `IconInfoData(obj_instance=obj)` gives the object thumbnail. Never
call an `a11y.*` command function with `_connection=None`: `CheatOutput`
then hits native output with a bad context (`NO_CONTEXT` is 2**64-1).
`tyjokr_a11y_lang.py` gained 27 menu terms (17 languages) and the scanner
help line now ends "H for this help, U for settings" (remove the U part
if the chord goes). Offline harness: the scratchpad `test_menu_offline.py`
(stubs sims4/services/ui/speech/pump/keys) passed under Python 3.7; it is
not in the tree.

### 2.6 Tools added

- `tools/gen_buycat_table.py` (category table generator, see 2.2).
- `tools/stbl_scan.py`: DBPF + STBL reader with EA RefPack decompression
  (`Strings_*.package` entries are RefPack 0xFFFF, not zlib);
  `python tools/stbl_scan.py "<Data/Client/Strings_ENG_US.package>" "Text"`
  lists every key with that exact text.
- `tools/keysbb_dump.py` + `tools/keysbb_table.tsv`: all 548 KeysBB
  constants (name, key, English) parsed from the ffdec pcode export at
  `ScreenNarrator/flash/work-1.127.41/pcode/ea_ClassLibraryOlympus/scripts/
  olympus/localization/KeysBB.pcode`. The catalog UI's own label keys.
- `flash/chain.ps1` (see build rules).

## 3. Test status

| Item | Status |
|---|---|
| Scanner names, categories, loc channel | Confirmed in-game 2026-09-06 (v1/v2) |
| Real pie menu from Ctrl+Alt+Enter | Confirmed 2026-09-06 (v2) |
| Camera keys blocked by the hook | Confirmed 2026-09-06 |
| Hook lag outside the game | Fixed 2026-09-06 (foreground-only), confirmed |
| Hook lag INSIDE the game | OPEN, reported 2026-09-15 (see 1.2) |
| v3 two-level categories, PageUp/Down, Build/Misc contents, Pets bit | NOT TESTED (deployed since 2026-09-07) |
| v4 settings window, first-run popup | NOT TESTED; spoken part unwanted |
| Scanner window | Wrong shape, replace with caption overlay (1.3) |
| Pause: chords still work | Not reported |
| Main menu: "No lot loaded" on chords | Not reported |
| Older reader items (picker scrolling, arrows in dialogs, auto-focus cold boot, `a11y.reload`, cfg persistence) | See TODO-NEXT-SESSION.md "still pending" |

Test plans with expected wording are in `SCANNER-TEST.md` (v1 base plan,
then v2, v3, v4 additions).

## 4. Open issues and to-do, in order

1. Typing lag in the game (1.2). Hook only while Ctrl+Alt held. Test both
   ways (typing, camera).
2. Retarget v4 to the user's intent (1.1): no spoken menu; settings window
   + first-run popup of the window; decide the one spoken welcome line.
3. Caption overlay (1.3). Flash rebuild + compat + package deploy (game
   closed).
4. Test v3 categories; read the `scanner:` log lines; confirm bit 1024 =
   Pets (if wrong, fix GROUP_FLAGS in `tools/gen_buycat_table.py` and
   regenerate). If Build/Misc catch too much, adjust the tag priority in
   `_SUB_PRIORITY` / `_group_of`.
5. Strip the `piecreate` mark from `PieMenuMain.as` before any release;
   cfg `logging` back to off for release (`compile.py --release` handles
   the log default).
6. Scanner polish waiting on the user: bearing is world-axis north (like
   glaroc's), the pie menu draws at the mouse position, 40 m limit, only
   objects with a player interaction. Phone/inventory/relationships are
   not scanner categories (they are reachable through the UI walker).
7. Release: version bump, `compile.py --release` for the dist zip pair
   (ts4script + UI package + speech DLLs; the SpeechPack is separate),
   CurseForge: add glaroc (username LeonianUniverse) as contributor (the
   user's action), credit him in the description. Send him the bug list in
   A11YSCAN-REVIEW.md section 8.
8. Prism vs Tolk (his proposal for Mac/Linux, github.com/ethindp/prism,
   C++23, MPL 2.0, extern "C" API prism_init / prism_backend_speak /
   prism_backend_braille, prebuilt prism-windows-x64.zip). Its Python
   binding needs Python 3.10+, unusable in TS4's 3.7, so it would be a DLL
   loaded through ctypes like Tolk today. Not started.

## 5. glaroc's functionality: integrated, pending, rejected

Key = his key. Status after this handoff.

Integrated (our implementation, his design):
- Ctrl+Alt+arrows categories/items, Enter activate (real pie menu),
  Backspace back, S rescan, R repeat, W where am I, H help (his Ctrl+Alt+W
  also goes home; ours does not). Sim-thread pump. Ctrl+Alt+PageUp/Down
  subcategories (ours, free in his layout).

Not integrated yet (ranked in A11YSCAN-REVIEW.md section 3):
- Sim status hotkeys: Ctrl+Shift+N needs, Ctrl+Alt+A what they are doing,
  Ctrl+Alt+E emotion (with causes), Ctrl+Alt+G wants, Ctrl+Shift+O
  aspiration + goals left, Ctrl+Shift+M household money, Ctrl+Alt+1..8
  play household Sim N, Ctrl+Alt+F focus my Sim (and the time). Cheap and
  high value; most of the data is one EA call each (his modules
  a11yscan_state.py / a11yscan_careers.py show the calls; verify against
  the decompile before use).
- Scanner categories for yourself, phone, inventory and contacts, and
  nested social categories (his world.py). Ours reaches phone/inventory
  through the UI walker instead; decide with the user.
- Camera: Ctrl+Shift+F follow my Sim (his follow-camera tick), Ctrl+Shift+
  Enter centre on the lot (that is the game's own key).
- Dialogs: Ctrl+Alt+D read the open dialog, Ctrl+Alt+X force close,
  Ctrl+Shift+A answer a call, Ctrl+Shift+Backspace decline. Our Flash
  hooks already narrate dialogs, pickers and notifications; his server-
  side answering (`ui_dialog_respond` / `ui_dialog_pick_result` verified
  against `ui_dialog_service().get_dialog()`) remains a potential fallback
  for server-owned dialogs. The six specialized pickers share PickersMain;
  v6 fixes the common host's loaded-child timing. Missing individual hooks
  did not establish missing support. His generic text-input typing
  (a11yscan_typing.py) remains unintegrated; v6 instead focuses real text fields.
- Travel: Ctrl+Shift+T travel with no map (push the tuned continuation of
  a map picker with `picked_zone_ids`, companions as `picked_item_ids`;
  `travel_solo_mapPicker` is the plain one), Ctrl+Alt+Home go home,
  Ctrl+Shift+Home travel via the map (his map screen cannot be closed
  afterwards), Ctrl+Shift+H move house / move in together (household
  merge).
- Ctrl+Shift+P plan a social event (situations from tuning +
  `create_situation_with_guest_list`, guest list as job/sim/purpose
  triples); the EA event planner itself is client-only.
- Ctrl+Alt+J jobs (career menu from tuning; the career screen is client-
  only), Ctrl+Alt+V cheats and fixes menu (1.8k lines: skill and
  relationship sliders, unstick, clear queue, per-Sim autonomy, clear
  trash, end situation, "why will my Sim not do anything" diagnostics),
  Ctrl+Shift+G game settings (autonomy/aging read back from services),
  Ctrl+Shift+S save the game, Ctrl+Alt+T narration toggle (ours has
  speech modes on Numpad 9 / Insert).
- CAS: Ctrl+Alt+M create a Sim without CAS (SimCreator + CAS Stories
  scoring + `cas.cas` natives, empty-lot pick, move-in), Ctrl+Alt+L change
  how a Sim looks, Ctrl+Shift+L randomise appearance. Plan: a separate
  "wizard" mode, not a replacement for reading CAS (our CAS Flash hook is
  still blocked).
- Build: Ctrl+Alt+K buy catalog (his now groups by BuyCat tag but labels
  are English tag names; ours would use the same EA label keys as the
  scanner), Ctrl+Alt+B tile grid cursor (1 m tiles, objects on the tile,
  floor/pool/inside, walkway-blocking advice from
  `routing.test_point_placement_in_navmesh`), placement via
  `find_good_location` with `REQUIRES_SLOT` ("needs a surface") from
  `build_buy.get_object_placement_flags`, surfaces ranked desk/table
  first, Ctrl+Alt+Z undo a placement, Ctrl+Shift+D sell what you point at
  (press twice), `register_everything` repair. Placement must register
  with `add_object_to_buildbuy_system(obj.id)` (he fixed this in build 3).
- Shopping (build 2): `create_object` + `system_add_object` + funds
  `try_remove` with the INT reason from `Consts_pb2.FUNDS_*`.
- Ctrl+Alt+O choose a save or household: the household switch is fine;
  the save picker copies over `Slot_ffffffff.save` (data-loss risk), hold.
- Ctrl+Alt+F5 reload the mod / self-reload on a newer archive
  (a11yscan_reload.py, generation counter in builtins, zipimport caches
  cleared, rollback). Dev convenience; ours has `a11y.reload` for the cfg
  only.
- Ctrl+Alt+Q reachability probe (dev diagnostic).

Rejected or superseded:
- His STBL and OBJD tables (16 MB + 3 MB English): we resolve keys through
  the client. His build 3 reads STBL resources at runtime via
  `sims4.resources.list/load` (English only); a real finding, but the
  Flash bounce stays cleaner (client handles tokens and language).
- Changing his key scheme (the review proposed a mode toggle): the user
  said keep his keys exactly.
- His pump fallback (runs game code on the key thread after 2 s of
  silence): ours refuses instead and re-arms at zone load.

His bugs worth remembering if his code is ported (A11YSCAN-REVIEW.md
section 5): `add_object_to_buildbuy_system` needs `obj.id` (fixed in his
build 3); cancelling the Sim's current activity before pushing an order
displaces the order (fixed in his build 3); README/DEVELOPERS still claim
`re`/`queue` are unavailable (false: base.zip ships re, queue, struct,
json, subprocess, shutil, pickle, configparser; only ctypes is missing);
both mods installed together double-announce dialogs and both ship a
top-level `ctypes` package (first loaded wins).

## 6. Hard-won facts, in one place

- `distributor.ops.SendUIMessage(name)` + `Distributor.instance()
  .add_op_with_no_owner(op)` is the only Python -> Flash channel; the name
  is the whole payload. Flash listeners are keyed by message name
  (`CommunicationManager.AddMessageListenerByName`); the native -> Flash
  entry is the ExternalInterface `"SendMessage"` callback, which EA sets
  once to `instance.SendUIMessage`. Simulation thread only.
- Flash -> Python is `PostServerCommand("a11y.xxx", "<text>")`, arriving
  as `CommandType.Live` commands; percent-encode text.
- Keys never reach Flash on PC; all keyboard work is Python
  (GetAsyncKeyState polling + the LL hook). See 1.2 for the hook's cost.
- `obj.catalog_name` is the STBL hash as an INT (EA's GSI code does hex()
  on it), not a LocalizedString.
- Sims have no catalog tags; the scanner gives them their own group with
  the game's "Sims" string.
- `alarms.add_alarm_real_time` on `time_service().wall_clock_timeline`
  fires while paused, dies with the zone, and holds its owner weakly.
- The client drops server-initiated pie menus; the client must request
  them itself (2.3).
- TS4 reads keyboard input from the message queue, so an LL hook can
  block keys; raw input would have made that impossible.
- Buy catalog top-level categories are per-definition bits from
  `build_buy.get_object_buy_category_flags`; subcategory labels are in
  `EA/tuning/Tags Metadata Tuning/*Client_Tags{BuildBuy,Build,Function}*`;
  main-category label keys are `olympus.localization.KeysBB` constants.
- `Strings_*.package` STBL entries are RefPack-compressed (`tools/
  stbl_scan.py` handles it). Two STBL keys can carry the same English
  text with different translations; use the key the feature's own UI
  uses (KeysBB for the catalog), never "any key with that text".
- Python dialogs from a mod: see 2.5. Pickers are silent to our narration;
  `UiDialogOk` dialogs are narrated by the DialogMain hook.
- PS 5.1 `*>>` appends UTF-16; pipe through `Add-Content -Encoding utf8`.
- Robocopy from Git Bash mangles `/E`; run it from PowerShell.

## 7. People

glaroc = "Leo", blind player, Discord. Handed a11yscan over to tyjokr with
credit on 2026-09-07; to be added as CurseForge contributor (username
LeonianUniverse). He proposed Prism instead of Tolk for Mac/Linux and
reports that blind players refuse mouse-dependent mods, which is why
everything here is keyboard-first.

## 2026-09-24 Codex: preserve startup key ownership during client changes

Source review found that startup.tick() discarded the queued native-mode mark
when the simulation client appeared. Reproduced offline: _flash_startup stayed
true and send_navigation swallowed Tab although Flash had switched to native.
The incoming queue could also discard mode marks behind 48 narration entries.
Scripts/tyjokr_a11y_startup.py now retains recognized mode marks across client
changes (still drops departing narration and stale generations) and gives them
queue priority. Unrelated startup diagnostics do not change ownership.

Added three tests in tools/test_startup_v11.py; they produced four failures
before the fix, then all 13 startup tests passed under Python 3.7. Original
files and review.diff are in build/codex-startup-state-20260924/. Source only,
not built or deployed. Claude owns the companion Flash transition review:
A11yMsgHook currently clears its startup flag without posting a native mark.

## 2026-09-24 Codex: companion Flash handoff review

Reviewed Claude's A11yMsgHook notification and a11y.mark throttle exemption.
Added tools/test_startup_transition_v11.js: four actual-source decision-body
checks pass, covering native handoff, repeated hook calls, throttled startup
speech versus transport marks, and no socket dependency on the native path.
These fixtures do not emulate Scaleform; movie fidelity and live tests remain
required. Claude accepted the Python change through the mailbox at 18:34 UTC.

## 2026-09-24 Codex: live input-fence command error fixed in source

Fresh Sky game capture and visible console typing verified. Opening
`a11y.menu window` on fix1 rendered the visual settings picker, but the native
console reported `a11y_inputfence() got multiple values for argument '_connection'`.
Flash supplies an empty positional payload and the native command wrapper
injects `_connection` by keyword; the old handler only accepted `_connection`.
Updated keys.a11y_inputfence to accept optional string payload separately.
Added native-payload/connection and socket-no-argument regressions in
 test_keyboard_v10.py: reproduced TypeError before fix, all 22 now pass.
Backups: build/codex-startup-state-20260924/*before-inputfence.py. Awaiting peer
review/build and live retest; currently running game still has fix1.



## 2026-09-26 Codex: phone owner and clock candidate in progress

User approved Ctrl+Alt+C and a Day and time hub entry after consultation with Claude.
Claude owns Python routing/response and tests; Codex owns Flash and player controls docs.
Phone refusal traced to navigation ownership including the phone alert, ordinary HUD
panels, HUD browsing and status scopes. Added separate blocking-owner report while
retaining navigation state. Real dialogs/pickers remain blocking. Clock reads the
game-localized TimeControls text and paused label through a dedicated response.
17 Flash-source fixture checks pass. Full chain phone-clock-20260926 started;
not yet packaged or live verified. Screen control stays stopped; no deployment.


## 2026-09-26 22:09 Codex: phone and clock candidate staged, live QA pending

Candidate: dist/2026-09-26_2209/TS4_Access_2026-09-26.zip.
Main ZIP SHA256 ee662ead30bbedd8a005c8cf4d06b1fe894392172190896fead68e19e17b7f30.
Script 7b6974ced4d8a65396e90a2210fa3c14e2c160389149d788512874c6c5d6634e.
UI aa12430a588ffd6b44e2c572402159a37d9c21f247a6d834ae24802566a8312d.
Compatibility UI 58096e5eb3da3b472bdee0e547214f63d2d206b23cf4a59a682b782fe9745472.

Full source checks: 1187 checks / 73 suites, passed=True, input_stable=True;
verified inputs still match. Main fidelity gate and 19 compatibility comparisons
pass. All 25 main + 6 compatibility resources match generated movies; original
noncode tags and class sets preserved. 25 release script modules match frozen
source with release logging off. Settings module unchanged; scanner default off.
Controls and Patreon controls draft updated. Claude reviewed UI source; package
review requested via mailbox. His initial all-pass claim was independently found
incorrect (two outdated expectations); corrected and rerun before this candidate.

No installation, upload, screen control, or live verification. See HOTFIX-QA.md
in candidate/dist for required incoming-call and clock live cases. User stopped
screen control earlier; require resumption before driving the game. Do not treat
this candidate as live verified or replace the published release pointer yet.


## 2026-09-26 22:13 Codex: independent package audit passed

Claude recomputed all staged hashes, checked 25-module parity, 25+6 UI resources,
source manifests, docs and test report. No blockers. Review saved in both candidate
and dist as CLAUDE-REVIEW.md. Live testing remains pending screen-control resumption.
