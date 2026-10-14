> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# TEST-V14: keyboard travel list (World, place, unit windows instead of the map)

Status at 2026-09-25 02:30 EDT (02:29: v14f pair script c7bd2bb6 + UI
c79b26f6 INSTALLED by Codex, live rows running): ordinary keyboard travel
is live PASS on the previous pair (script 7a7c64e0..., UI 6f71529b...): world and place windows,
family-first labels with residents, hidden worlds dropped, master and
secondary units, unit arrival with companions, Back rows, cancellation, the
native map fallback with arrival, keyboard off and travel list off. Still
needing live proof on the next combined pair (script c7bd2bb6 frozen, UI
chain v14f-rental-build): vacation rows 23-27 and 30-34 (bridge price, stay,
rental, refusals), M key rows 28-29, Build actions rows 32 and real
placement. The summary table shows the latest state per row and the exact
build it was proven on; every earlier failure stays in the appended
evidence below (append-only). Rows change only with log evidence or a
capture named in the Evidence column.

Builds: installed script 7a7c64e08637bae558223278fff5baa88ea114188a9eea1fcde1d9475805ab41
(v14e: price sentinel fix + M Python side) and UI
6f71529bbc0faf102ff0f0aa578e6b5410aaf3ca97c0ad4a83120a630274756f (v14d
picker descriptions). Earlier live rows name the build they ran on
(v14-travel-list-candidate 427214a8, v14b 1ad87207, v14c a92a1a76). Next:
build/v14f-rental-build-script-candidate c7bd2bb66c7f8eaee19e9f5993183a5d3591002558c039fd2b07ca8c9c245680
plus the v14f-rental-build UI candidate (Codex audits, then a deploy request).
Sources: Scripts/tyjokr_a11y_travel.py, tyjokr_a11y_settings.py (travel_list),
tyjokr_a11y_menu.py, tyjokr_a11y_lang.py, tyjokr_a11y_narrator.py,
tyjokr_a11y_pump.py (travel lease), tyjokr_a11y_hub.py and
tyjokr_a11y_build.py (Build actions window, menu resume), plus Flash
(ControlPanel M hook, TooltipManager bridges by Codex).

Offline: tools/run_checks_v10.py = 528 checks across 34 isolated suites
(build/v14f-run-checks.log): test_travel_v14 39, test_travel_vacation_v14b
30, test_travel_m_v14c 20, test_build_menu_v14f 11, Codex's
test_travel_review_v14 8, test_travel_bridge_v14.js 8,
test_rental_price_bridge_v14.js 16, test_flash_build_v10.js 19,
test_travel_controlpanel_v14e.js 10, and the older suites. Stubbed EA
services, source bodies, not in-game evidence.

## How to read the log
Every step writes `travel: ...` lines to tyjokr_ScreenReader.log (logging on):
`dialog N listed as P places in W worlds`, `dialog N answered with zone Z`,
`dialog N cancelled from the list`, `dialog N handed to the native map`,
`dialog N no longer active, nothing sent`, `zone Z refused by dialog N`,
`list unavailable (...), native map instead`.

| # | Case | Steps | Expected | Result | Evidence |
|---|------|-------|----------|--------|----------|
| 1 | Solo trip from the phone | Phone > Travel, Sim picker: pick nobody, Done | World window opens (no map); worlds named; last row "Open the map instead" | PARTIAL | World window opened with five companions 23:02:40 (dialog 7 listed as 445 places / 34 worlds, build/codex-live-20260924/v14-travel-worlds.png, 427214a8); the solo "pick nobody" entry itself was not exercised separately.|
| 2 | Pick a place | World row > place row | log `answered with zone`, loading screen, Sim arrives at that lot | PASS | 23:13:24 dialog 22 answered zone 759427236925213178, Brindleton Pawspital; native loading and arrival 23:13:48. Keyboard world and place selection. |
| 3 | Trip with one companion | Sim picker: pick one household Sim, then a place | both Sims arrive (companion preserved through the native continuation) | PASS | build/codex-live-20260924/v14-arrival-with-sebastian.png: Elias present, Sebastian selected with destination plumbob. Companion setup used mouse, so not a full keyboard-only pass. |
| 4 | Escape at the World window | open list, Escape | log `cancelled from the list`, spoken "Travel cancelled.", Sim idle, no queued interaction, no map | PARTIAL | 23:03:42 log: dialog 7 cancelled, Travel cancelled speech request, UI owner world. Queue cleanup not visually verified. |
| 5 | Escape at the place window | world row, Escape | same as 4 | PASS | 23:22:23 dialog 27 cancelled; speech request and world owner logged. Fresh UI showed travel removed from queue, only prior social interaction remaining. |
| 6 | Back rows | place window "Back to worlds"; unit window "Back to places" | previous window returns; original dialog untouched (no respond line in the log) | PASS | World Back 23:03:22; unit Back 23:22:03 returned to Tomarang places without answering original dialog. |
| 7 | Multi-unit building (For Rent) | pick the building row | unit window with unit names and residents; picking a unit travels to that unit (unit zone id in the log) | PASS | FAIL on 427214a8 (09 Taka Soi 15 listed only 08; offered master omitted) fixed in v14b: on 1ad87207 the unit window lists 08 and 09 with residents; Return on Cahyaputri 09 answered dialog 8 with zone 557059792841749514 at 01:02:18, native loading ended 01:02:34 with Sebastian and companions at the unit (build/codex-live-20260924/v14d-master-unit-arrival.png). |
| 8 | Open the map instead (World) | last World row | native map opens for the same request; travel from the map works; log `handed to the native map` | PASS | a92a1a76 script: dialog 12 "Open the map instead" at 01:14:31, native Tomarang map kept the four-Sim party, unit and Travel chosen on the map, native load completed 01:16:47 with the party present (v14-vacation-build-native-fallback-arrival.png; mixed keyboard and pointer on the map).|
| 9 | Open the map instead (place) | last place row | as 8 | UNTESTED | |
| 10 | Invite To from the relationship panel | relationship panel > Invite To > pick lot | list appears; invited Sim travels too (target continuation) | UNTESTED | |
| 11 | Keyboard off | settings keyboard off, Phone > Travel | native map unchanged, no `travel:` lines | PASS | 01:17-01:19: console a11y.keys off confirmed; Phone > Travel and the companion confirmation opened the native Tomarang map, no list (v14-keyboard-off-native-map.png); keyboard restored ON afterwards.|
| 12 | travel list off | setting off (menu row or cfg), Phone > Travel | native map, log silent | PASS | 01:30: travel list OFF through the settings window (cfg keyboard=on, travel list=off); Phone > Travel opened the native map directly with four travelers (build/codex-live-20260924/v14-travel-list-off-native-map.png); list restored ON 01:32, cfg verified.|
| 13 | Buy lot / change venue | buy a retail lot; change a date venue | native map (mode falls through), log silent | UNTESTED | |
| 14 | Small business lot (EP18) | travel to another household's lot that has small businesses assigned (1 on residential, 2 on a venue) | spoken "This place asks which business to visit. Opening the map.", native map opens for the same request with its business selector; log `needs the native business selector` then `handed to the native map` | UNTESTED | |
| 15 | Second travel request while a list is open | Phone > Travel while the World window is up | first request cancelled natively (log `superseded by`), new World window | UNTESTED | |
| 18 | Family-first labels (v14b source) | Willow Creek places | occupied homes read "Goth, Umbrage Manor" with description "Residents: Bella, Mortimer, ..."; vacant homes and venues keep the lot name first | PASS | 01:02 on 1ad87207: family-first Cupid and Cahyaputri labels with full resident names verified in the speech log while reading the Taka Soi 15 units.|
| 19 | Hidden worlds dropped (v14b source) | Phone > Travel, world list | no EP01_World, Forgotten Grotto, Sylvan Glade, debug worlds; world names localized from the region list; log `rows in non player-facing regions dropped` | PASS | 01:02 on 1ad87207: world list 28 worlds, six non player-facing region rows dropped (EP01_World gone; 34 worlds on 427214a8 at 23:02:40).|
| 20 | Master unit listed (v14b source) | Tomarang > 09 Taka Soi 15 (Cahyaputri) | unit window lists 09 (Cahyaputri) and 08; picking 09 travels to zone 09 | PASS | Same evidence as row 7: 09 (Cahyaputri) and 08 listed, 09 travelled to zone 557059792841749514, arrival 01:02:34.|
| 21 | a11y.travel (v14b source) | console `a11y.travel` in Live mode | native companion picker opens (Sim menu Travel chain), then the list; at work/save locked = spoken unavailable + log reason | UNTESTED | |
| 22 | a11y.travel_probe (v14b source) | after any list, console `a11y.travel_probe` | one `travel probe:` log line per listed row with region, facing, hide flag | UNTESTED | |
| 32 | Build actions window (v14f source + Codex TooltipManager menu path) | Build mode, cursor on at a known spot, Ctrl+Alt+H > Build actions | 17 rows (cursor on, cursor off, move left/right/up/down, fine step, coarse step, center cursor, aim at grid point, select or place, cancel tool, rotate left/right, undo, redo, cursor status); opening the window retires the cursor (modal); a move, step, center, select, cancel, rotate or status row closes the window, the cursor returns to its previous screen position and the one action runs (`A11y|build|menu:<action>`, native guards unchanged); cursor on/off, undo, redo and grid aim are the ordinary requests; nothing resumes on its own after Escape; outside Build mode: "Enter Build mode first." KNOWN (v14f live 02:47-02:53): pointer clicks and wheel over the window act on the lot beneath (Build mode routes mouse input past the picker), so the window is keyboard-driven; opening any modal (console or this window) makes EA's inspector cancel the held catalog product (HandleSetModalVisible), so placing a catalog item from the window needs Codex's Flash re-selection on resume | PARTIAL | v14f 02:48:04 Return on Move left: cursor x 1012 -> 996; 02:52:59 Center 846,430. v14h 05:11:37 and 05:15:29: chair held before any cursor use, console a11y.buildmenu, On / Center: cursor back, held chair restored (`restore ... Select returned`, held-tool bar present; build/codex-live-20260924/v14h-build-first-trace.log). Still open: an actual placement with undo/redo; pointer click and wheel over the window act on the lot beneath (engine routing, documented). |
| 33 | Stay re-quote (v14f source) | (harness only unless a price changes live) | the place list, the stay window and the commit each re-read the request price (client answer first); if the client price moved after the stay was quoted, the rental is refused with "The price changed. Choose the stay again." and the stay window reopens at the new price; a price withdrawn by the client before the commit hands the request to the native map before any rental | UNTESTED | |
| 34 | Bridge reply strictness (v14f source) | (harness) | `a11y.lotprice_enc` accepts exactly `zone|price|generation`; the truncated price must be 1..2147483647; anything else is dropped without touching the request and logged as unusable | UNTESTED | |
| 35 | Build exit cursor release (v14g source, needs Codex Flash idempotent off) | cursor on, then F1 to Live mode | log `build: Build mode ended, cursor release sent`, no speech; physical clicks on the phone and HUD work in Live mode; a11y.build off in Live mode also releases | FAIL | v14g 04:23:02 and v14h 05:16:51: `build: Build mode ended, cursor release sent` logged and the Live UI instance forced SetupVirtualCursor(false) + SetMouseInputEnabled(true), yet a physical click at 276,1041 acted at the last virtual point 846,430 (pie menu on the Sim, build/codex-live-20260924/v14h-build-exit-fail.log). EA parity fix proposed (disable payload with enable-time restraints and onConfirmDown 3, then SetVirtualCursorPosition(-1,-1), then SetMouseInputEnabled(true)); Codex Flash. |
| 31 | Client price bridge (v14f source + Codex TooltipManager) | Plan Vacation list, Granite Falls | log `A11y|lotprice|<zone>` requests, then rentals show the map's own price (397 Simoleons per day for Green Getaway per Codex 01:47); an unpriced rental pick still opens the native map | PARTIAL | v14h 05:28:05 native rental panel (map fallback, Green Getaway 397/day): after choosing 2 days the panel quote is read in full (Rent for 2 days x 397 = 794), Tab to confirm repeats 794, 3 days reads 1191 (build/codex-live-20260924/v14h-rental-quote-pass.log; Codex GERentalPanel symbol fix). Client price bridge for the simplified list (A11y|lotprice) still to be recorded on this pair.|
| 30 | Rental price source (v14e source) | console `a11y.lot_value <zone>` for a Granite Falls rental, then the vacation list | log shows ('zone', positive value) and the price = int(value * multiply + add); rows never show a negative or zero price; an unpriced rental row hands the request to the native map | UNTESTED | |
| 23 | Vacation list (v14c source) | Phone > Plan Vacation > pick Sims > list | World/place windows as for travel; rental rows show "N Simoleons per day"; log `listed as` | PARTIAL on a92a1a76 (Codex 01:11: list PASS 457 places / 31 worlds; Granite Falls rentals showed -2 Simoleons per day = build_buy sentinel; nothing rented) | build/codex-live-20260924/v14-vacation-negative-price.png |
| 24 | Stay window | pick a rental | rows 1 day .. 7 days with totals; rows above the household funds say "Not enough money."; Escape = "Travel cancelled.", nothing rented, funds unchanged | UNTESTED | |
| 25 | Rent and travel | pick an affordable stay | log `rented for N days at C`, then `answered with zone`; funds drop by C; loading screen; vacation shows in the travel group UI with actor + companions | PASS | v14f 03:12:21: Green Getaway rented 2 days at 794 (group 507524915090097237), dialog 12 answered, five Sims arrived 03:12:33, funds 12409 -> 11615; repeat 03:30:43 clean (group 1008550373707285883, arrival 03:30:54, no exception). The first run was followed once by an EA teardown assertion (Sim Timeline hard-stop of a relationship-bit element creating a new relationship after EventManagerService disable; lastException archived in build/codex-live-20260924); source-supported as timing, not attributed to the flow.|
| 26 | Non-rental destinations (v14f source) | Plan Vacation list in Granite Falls | parks and venues are NOT listed (native rule: Sims on vacation may only stay on rental lots); log `N non-rental rows left to the native rules`; a destination world with no rentals at all opens the native map | UNTESTED (the earlier free-lot booking design was WRONG and removed after Codex's 01:45 native tooltip evidence) | |
| 27 | Unaffordable stay picked | pick a marked row | spoken "Not enough money." then "Travel cancelled."; nothing rented | PASS | v14f 03:38:55 with funds set to 100: one-day 397 stay refused, log `cost 397 exceeds funds 100`, spoken "Not enough money." then "Travel cancelled.", still home, funds unchanged.|
| 28 | M key handshake (v14e source, needs Codex's Flash part) | press M with keyboard + travel list on | native companion picker, then the list; log `keyboard entry pushed ... (request N)`; with the list off or lease absent = native map untouched | PARTIAL | v14f 03:42: M in Live mode opened the companion picker then the list; three preselected adults deselected, Sebastian alone arrived at Brindleton Pawspital, others grey at home, funds 12409 (solo entry via M). List-off / lease-absent native map not yet exercised on this pair.|
| 29 | M refusals | press M while the Sim is at an active career event; press M then Escape quickly | spoken reason, no map, Flash pending cleared; cancelled request logged `cancelled`, nothing pushed | UNTESTED | |
| 17 | M key | press M in Live mode | native map (client GoToNeighborhoodTravel path, no Python dialog); NOT handled by v14, documented; log silent | UNTESTED | |
| 16 | Setting turned off mid-flow | open list, a11y.menu: travel list off, then pick a row | request cancelled (log `cancelled from the list`), no travel | UNTESTED | |

## Open issues (design, for cross-review)
- Escape at any window cancels the trip; only the explicit Back rows go up
  one level. Chosen for predictability; can be changed to Escape = back.
- Small-business selector (row 14): handled by handing the same request to
  the native map; predicate = lot owner is another household and the count of
  that household's small businesses whose allowed zones include the lot meets
  the map's threshold (1 residential, 2 venue). If the check itself fails for a
  lot another household owns, the native map is kept. Predicate needs live proof.
- M key travel is a client-only path (ControlPanel.HandleGoToNeigborhoodTravel ->
  GoToNeighborhoodTravel, companion picker after the map); v14 leaves it native.
  A keyboard-on M routing through the tuned travel interaction is a later item.
- Identity check uses ui_dialog_service.get_dialog (public), falling back to
  _active_dialogs; a failed check refuses to answer.

## Codex candidate verification and installation, 2026-09-24 22:55
Full stable checks: 401 checks / 27 isolated suites, all passed. Includes
7 independent lifecycle/business guard regressions and Claude's 28 travel
checks. Candidate source and all 20 archive code objects verified; no Flash
changes. Claude independently reviewed all source hashes and archive contents.
Installed only tyjokr_ScreenReader.ts4script after tasklist proved game absent.
SHA256: 427214a842b16d6d708af773580203bc0d62c474f4384198ca2c7de2c69219ce.
Backup: build/codex-deployed-before-v14 (prior V13b script db609c24...).
Configuration and UI hashes unchanged. No completed V14 live test yet.

## Live observations, 2026-09-24 23:02-23:03
Phone Travel with five selected companions opened the world list at 23:02:40:
`travel: dialog 7 listed as 445 places in 34 worlds`. Capture:
`build/codex-live-20260924/v14-travel-worlds.png`.
Enter opened Brindleton Bay places; Enter on Back returned to worlds.
Escape requested native cancellation. These observations do not prove arrival
or companion preservation. Speech evidence is log output, not listening to a
screen reader.

Open findings for Claude review: EP01_World appears as an internal world name;
445 offered places may need additional native-map visibility filtering; Space
toggled Adrian's companion card visually without a checked/unchecked speech
request. Keep the frozen candidate unchanged until fixes are reviewed.

## User additions and next candidate
- Event/career explanation narration: added focused/hovered row-data lookup
  in shared Flash source, including enabled event challenge/reward and location
  restrictions plus career descriptions. Source fixtures pass (19 checks), but
  this change is not in the installed V14 and has not passed live verification.
- Occupied residences: household name first, specific resident Sim names in
  the description, and original lot/unit name retained for identification.
- Vacation flow must receive a simplified destination picker too, preserving
  native rental eligibility, party, duration, and cost decisions. Current
  vacation map fallback is not completion of this added requirement.
- Ordinary travel arrival with Sebastian passed; grouping, world visibility,
  and selection announcements are being corrected in shared source. The
  installed frozen V14 candidate has not changed.

### Keyboard planner completion, 23:45–23:52
PASS: after opening Calendar by mouse, Add Event and every planner choice
used keyboard. Keg Party, host Evie, guests Lionel and Ashton, Club Calico,
3 PM. Calendar entry confirmed; funds 12409 -> 12309. Space on picker OK
returned correctly without duplicate response errors in the observed log.
Evidence: build/codex-live-20260924/v14-event-keyboard-complete.png.
Narration gaps remain: right-panel descriptions awaiting new build; stray
Hire this Role. 0 on Sim cards. This is a navigation/creation pass, not a
claim of complete spoken accessibility. Unsaved test state.

### Description narration live test, 2026-09-25 00:03-00:15
UI-only test candidate 48a3fce7 installed with original V14 script retained.
Speech-log PASS: physical hover on Ranch Animal Day; keyboard Romantic Repair
Date, Baby Shower and Keg Party read their own descriptions and rewards even
while the selected right panel remains on another event. Scoring-off Keg Party
omits rewards. Actor includes agency requirement, Detective its own description,
Astronaut and Athlete their career branches. No career was joined.
FAIL after scrolling: Entertainer/Freelancer only spoke names. Root cause:
RecyclingGridLayout.GetGridIndexOfCell already returns a mapped index, then
A11yChoiceDescription mapped it again. Corrected source skips the second mapping
for the two native recycling layouts; plain event GridLayout still maps once.
Claude independently confirmed against EA pcode. Regression test passes.
Literal separator spaces added between detail sections; rebuild v14d running.
These are speech-request log checks, not an auditory screen-reader test.
M shortcut at 00:15 opened native Tomarang map with no diagnostic callback mark;
cancelled at 00:21 without travel. M routing remains outstanding.

### Installed description correction and ordinary travel refinement, 00:33
Claude independently reviewed frozen UI 6f71529bbc0faf102ff0f0aa578e6b5410aaf3ca97c0ad4a83120a630274756f
and ordinary script 1ad8720734fbdfc47ae6a0ce858defe528142215fde3113518ec9bb5d85282c1.
Installed both with game absent, backup and post-copy hash verification.
Configuration unchanged. Backup: build/codex-deployed-before-v14d.
Vacation code is NOT included. Live retest pending.

### Description correction live PASS, 00:37-00:39
With UI 6f71529b, scrolled to Freelancer: physical pointer selection at 00:37:59
requested its complete description and all six trades. Keyboard Up at 00:38:09
requested Entertainer description and Musician/Comedian branches while the right
panel still showed Freelancer. Evidence: v14d-scrolled-career-details.png.
Event mouse hover Ranch Animal Day 00:39:04 requested its rewards and description;
keyboard Romantic Repair Date 00:39:16 included main objective, rewards, description;
Baby Shower 00:39:27 and Keg Party 00:39:45 each read their own details while the
right panel remained Romantic Repair Date. Section separator spaces verified
in the speech log. No career accepted; auditory output not independently heard.
Host picker narration PASS 00:40:33 Evie Darden unchecked; Space 00:40:44
Evie Darden checked. Stray hidden Hire this Role / 0 omitted. Test cancelled;
no event created in this run. Earlier full keyboard creation pass remains.

### Ordinary travel unit arrival PASS, 2026-09-25 01:02
Installed 1ad87207 lists both 08 and 09 Taka Soi 15. Keyboard Down reads each unit and residents; Return on Cahyaputri 09 answers dialog 8 with zone 557059792841749514 at 01:02:18. Native loading ends 01:02:34 with Sebastian and companions at the residential rental. Screenshot: build/codex-live-20260924/v14d-master-unit-arrival.png. Earlier omission failure is resolved. Family-first Cupid and Cahyaputri labels with full resident names also verified in live speech logs. World list now 28 worlds, six non-player-facing region rows dropped.

### Career acceptance PASS, 2026-09-25 01:05
From focused Join a Career, keyboard Return and unpause opened the picker. Tab to Careers filter, Return, Tab through Part-Time to Astronaut; Return selects row, Tab reaches Select, Return accepts. At01:05:31 speech request: Entered the Astronaut Career. Sebastian is now a Module Cleaner at SpaceY. He starts Monday at12:00PM. Career panel shows Module Cleaner,44/hour and work schedule. Evidence v14d-career-accepted.png. Unsaved test.

### Vacation TEST build installed, 2026-09-25 01:07
Claude approved frozen a92a1a76; independent20module source/code/hash verification passed. Guarded script-only install after elevated tasklist showed game absent. UI6f71529b/configunchanged. Backup build/codex-deployed-before-v14-vacation. Vacation live tests pending.

### Vacation live pricing failure, 2026-09-25 01:11-01:12
Native Take a Vacation and companion confirmation opened simplified457places31worlds. Granite Falls Campground and Green Getaway show -2 Simoleons per day (unloaded value bug). No rental selected/charged. Escape01:12:28 cancelled dialog6, funds12409 unchanged and queued vacation removed. Evidence v14-vacation-negative-price.png. Claude owns price-source correction; rental acceptance remains FAIL pending fix.

### Native map fallback arrival PASS, 2026-09-25 01:14-01:16
On vacation-test script a92a, ordinary request dialog12 chose Open the map instead at01:14:31. Native Tomarang map retained Sebastian+Evie+Elias+Watson party. Tab/Return opened Taka Soi15, pointer selected unit and Travel. Native load completed01:16:47 with party present. Evidence v14-vacation-build-native-fallback-arrival.png. Map fallback is functional; setup mixed keyboard/pointer.

### Keyboard off PASS, 2026-09-25 01:17-01:19
Console a11y.keys off confirmed. Phone Travel and companion confirmation opened native Tomarang map, no simplified list. Evidence v14-keyboard-off-native-map.png. Setting restoration follows before other tests.

2026-09-25 01:30 EDT Codex: a92a script / 6f71529b UI: keyboard navigation restored ON after keyboard-off test. Travel list switched OFF through settings window; cfg confirmed keyboard=on/travel list=off. Phone Travel companion confirmation opened native Tomarang map directly, retaining four travelers. PASS settings-off fallback; evidence build/codex-live-20260924/v14-travel-list-off-native-map.png. Restoring list next.

01:32 EDT: travel list restored ON via settings; cfg keyboard=on, travel list=on verified. Console lost focus after incoming-call dialog; closing/reopening console restored command execution. No source regression established from this interruption.
