> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# V13 workflow acceptance: events, native Build, travel

Authorized September 24, 2026: complete these workflows jointly with Claude
while the user is AFK. This is a working checklist, not a pass report.

## Coordination

- Claude owns event planner tests and minimal fixes; Codex owns travel.
- Build finalization follows jointly, with explicit ownership before edits.
- One game driver at a time, coordinated by mailbox/GAME-LOCK.
- No deployed file changes while the game runs. Cross-review candidate hashes
  and source changes before deployment. Keep rollback artifacts.
- Test in unsaved sessions. Preserve original mod settings and save files.
- Exchange investigation, review, deployment and completion messages through
  the mailbox. No unrelated career implementation in this scope.

## Acceptance

| Workflow | Required evidence | Status |
|---|---|---|
| Social event | Reach planner using keyboard, choose type, select required hosts/guests, venue/options, confirm, verify created event; cancel/back also work | PARTIAL (Claude 19:03-19:17, installed v12, log build/run-e/event-test-log.txt): as the CHILD Sebastian the calendar Add Event / Add Wedding Event rows were silent on Enter and Space (EA disables them; disabled state not spoken = gap); as the ADULT Evie (switched via the a11y.household picker, second Enter confirms) Show Calendar -> Enter -> Tab x4 -> Add Event -> Enter OPENED the planner (owner SituationCreationMain), focus landed on its Close - ESC. Planner ring, type/guest selection and confirm NOT yet walked (handed to Codex). Phone route: the phone button IS a Tab stop (Codex inspector: target 45 PhoneButton/btnPhone) but has no spoken name = confirmed LABELING gap (fixed by P3 in v13). Also seen: unlabeled HUD stops 'Selector' (portraits) and 'buff' (moodlets); Close - ESC is a Tab stop in the calendar, the pause menu and the planner FIX MERGED (Claude, 19:40, awaiting v13 candidate): A11yActionProxy routes RoleSlotCellView -> mcPickSims (EA's Sim-picker button); refused proxy clicks now speak 'action unavailable'; PhoneButton announced as 'phone'. Fixtures tools/test_event_activation_v13.js 8 PASS. Live re-test pending |
| Travel | Keyboard entry, world and lot choices with names, normal eligibility, companions where offered, confirm and arrive, return/cancel without stuck map | Codex investigating |
| Build | Accessible catalog selection, cursor movement/rotation, invalid-placement feedback, real valid placement, price effect and native undo/redo; cancel and context exit release controls | Pending live test | PARTIAL (Claude 20:20-20:35, installed v13, gym lot, Elias): F2 -> Build (gamestate BUILD mark); toolbar narrated; forward Tab LOOPS on Gallery/Marketplace/Save to My Library (toolbar-order trap); Shift+Tab reaches catalog categories (Objects by Function, Community Items, Gym Items) but Enter/arrows did not enter the item grid (arrows walked the left bar; Enter on Live Mode left Build); Ctrl+Alt+T silent outside Build; Ctrl+Alt+F refused with 'Choose a point on the lot grid in Build mode first.' (spoken). No placement; funds evidence pending a home lot. Retest after the toolbar-sort fix |
| Grid aim | Read-only sample, native projection without automatic placement, graceful unavailable projection and cleanup | Pending live test |

Travel approach is undecided until native map testing. Prefer existing EA
controls and validation. Any alternate destination picker must have explicit
entry and preserve availability, cancellation and transition semantics.

Build scope is the implemented object-placement cursor and native history.
Walls, rooms, roofs, stairs and terrain construction are not implemented by
that cursor; do not describe an object-placement pass as complete coverage of
every Build tool.

## Baseline

Installed V12 script SHA256:
465719fb663cd75643b252f076af26a8590159894fb3866e442398244ce6f3cd

UI SHA256:
e32a22c61618e11e59d56e1412dfdc0ebcef977809fd4dd09f49bf43c860509a

Original config SHA256:
be275011a7ab13e6e9ea459edbfb0367c9c0d62950718ee1eb10ff9323ee7974

V12: 345 automated checks in 24 suites passed. Both agents recorded their
separate live shortcut checks in TEST-V12.md. No heard-audio claim.

Read-only current-EA travel references: build/travel-v13-reference/.

## Codex native map and Build baseline, 19:18–19:40

- M opens EA travel from the loaded lot. Back to World Select activates by
  keyboard. The world-category cell then takes focus as one giant item and
  reads several worlds together; Right cannot enter the individual choices.
- Current EA source confirms WorldRegionTypeCellView owns the inner world
  grid and StreetClip owns mcLots. V13 traverses these two containers and
  labels lot buttons with their native localized lot name and venue.
  Native activation and travel eligibility remain EA-owned. Claude reviewed
  these changes and the read-only A11yInspect routing exception.
- Three new navigation fixtures pass; the merged candidate passes 356 checks
  in 25 suites. These do not establish successful live travel.
- F2 enters Build. Keyboard traversal reaches the catalog and narrates the
  punching bag, 90 simoleons and its properties; Enter selects it. The hub's
  Build cursor action receives a native on acknowledgement at x835/y455,
  step16. The exit dialog automatically retires the cursor at 19:38:57.
- No placement pass yet. This public gym is Free Build, and short automated
  Ctrl+Alt presses did not reach cursor movement. Claude owns the held-chord
  placement test on a household home lot after the candidate deployment.
- Evidence: build/codex-live-20260924/build-cursor-first-v13.log and
  hud-inspect-v13.log. The session exited without saving.

## Claude live legs after the v13 deploy (held chords via the SendInput driver, own items)

Planner end-to-end (Evie, home lot, no panel open):
1. Tab ring to "Show Calendar", Enter; Right to a future day; Tab to "Add Event", Enter -> planner (owner SituationCreationMain).
2. Tab to the first type; Down x2 ("Keg Party. Cost: 100 simoleons"); Enter -> focus moves to Next; Enter on Next -> roles page.
3. Tab to "Click to Invite a Sim. Host. 1 Required"; Enter -> EXPECT a Sim picker (owner PickersMain), rows narrate names; Down, Space/Enter select, Tab to Done, Enter -> back on the roles page, Host row now names the Sim.
4. Repeat for the two Guest slots; Tab to Next: it must no longer say "Invite all of the required roles"; Enter -> options/venue page; Tab the ring; Enter on the confirm control.
5. EXPECT: the planner closes, a notification/calendar entry narrates the event; Show Calendar shows it on that day with "Go to Event".
6. Cancel path: reopen Add Event, Escape at each page -> planner closes without an event; a child Sim's Add Event -> "Action unavailable" spoken (P2).
7. Phone: Tab ring in the HUD narrates "Phone" at the former silent stop (P3); Enter opens the phone category screen.

Build placement (home lot for the price effect):
1. F2; Tab/Shift+Tab to the catalog; Enter selects an item (name + price narrated).
2. Grid projection path: Ctrl+Alt+T -> read-only grid on, Ctrl+Alt+arrows sample a tile (narrated), Ctrl+Alt+F -> aims the native Build cursor at that grid point (projection narrated, never clicks) while the grid stays active; optional Ctrl+Alt+arrow nudges; Ctrl+Alt+R reads position. Direct path (separate run): Ctrl+Alt+B -> screen-coordinate Build cursor on (note: B leaves the grid, so never T then B then F).
3. Ctrl+Alt+Enter -> place request. The module deliberately does NOT announce success, and a native click acknowledgement is NOT proof of purchase. PROOF = the object is present afterwards (scanner rescan Ctrl+Alt+S lists it / grid describe at that tile) AND household funds dropped by the catalog price (hub "household funds" row before/after).
4. Ctrl+Alt+Z undo -> object absent again AND funds refunded; Ctrl+Alt+Y redo -> object back AND funds deducted again; Ctrl+Alt+Backspace cancels the tool; Ctrl+Alt+B off.
5. Invalid spot (over a wall / off lot): EXPECT the native error narrated, no placement, no funds change.
Evidence: mod log excerpts per step in COLLAB; no heard-audio claim; game exit unsaved.
