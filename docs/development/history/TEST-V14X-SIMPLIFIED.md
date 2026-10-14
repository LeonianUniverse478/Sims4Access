> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# Simplified menus acceptance record

September 26, 2026. Work in progress, not release approval.

Scope: normal gameplay menu flows reviewed against glaroc's September 7
source. CAS, Stories, optional cheats and the separate appearance editor
are explicitly excluded. Tests use existing saves.

## Combined candidate 2

Installed at approximately 02:17 EDT with the game closed. Backup:
`build/v14x-before-simplified2-test`. Installation preserved other files.

- UI SHA256: `2c7392fc83e2c1a2dd2eb62fa5444cd7ea05665c0c01524c84ddc89740429afb`
- Script SHA256: `805610edc8d09d55d4828c6b4ffd81ba75cd37fc05863aed037cedef4cc25bb7`
- UI snapshot: `build/v14x-simplified2-ui-candidate`
- Script snapshot: `build/v14x-simplified2-script`
- Stable automated run: 1,087 checks in 64 suites, all passed; includes
  repeated imported checks. Inputs remained stable.
- All 25 UI movies rebuilt and bytecode fidelity gate passed. Compatibility
  package rebuilt separately. Neither package is a final staged release yet.

## Foundation findings

Previous test pair: UI `839fc3cc...`, script `a88d31cb...`.
Log preserved as `build/v14x-foundation-live.log`.

Existing save: ScreenReader v14v Launch Test, Season Test, Crick Cabana,
22,062 simoleons. Paused throughout; exited without saving.

- Settings navigation: each Down moved one row, with spoken positions.
- Settings toggle: Enter switched Simplified menus off; pointer click restored
  on. This was a mixed-input toggle test, not a full keyboard-only round trip.
- First-person: native Shift+Tab entered/exited; scanner Down worked while in
  first-person. Residual Tab also opened HUD browsing. Candidate 2 adds a
  camera transition fence and fixes short Shift chords in the Python poller.
- Load Game: extra scrollbar/name controls before Play. Candidate 2 makes
  native loading rows single choices and supports revealing offscreen rows.
- Options: category bar treated as one control. Candidate 2 traverses its
  individual category buttons. No gameplay settings were changed.

## Pending live acceptance

Candidate 2 has not yet passed full live acceptance. Verify Options,
first-person without HUD leakage, travel alone/with companions through arrival,
phone category/actions, careers/events, household move/merge and Manage Worlds.
Do not convert available entry points into claims of end-to-end coverage.

Candidate 2 checks completed by Codex before handing exclusive game input to
Claude at 02:21:
- Keyboard-only Load Game: Down from Resume, Enter, then one Down per save.
  Each row announced save name, household, timestamp and position. The fourth
  row scrolled into view automatically. Enter loaded the selected ScreenReader
  v14v Launch Test save to its Willow Creek map (Test household).
- Map navigation entry: Tab focused Go Back to World Select, 1 of 31. Down
  advanced to Gallery, 2 of 31. Up reversed and wrapped to the final control.
  Further Up reached Bargain Bend (name, Residential, size, price), then Willow
  Creek Archive (name, Library, size). No map action was activated in this check.

Native source review: HouseholdPanelCellView and HouseholdSelectorCellView are
Button subclasses with localized text. TransferPanel uses native Button and
ScrollList controls, native Sim-name tooltips, selection events, transfer/funds
controls and Done validation. Shared global navigation can reach these without
rebuilding each individual movie. This is source evidence, not a live pass.

Testing currently has diagnostic logging on. Restore logging off before the
final user installation, preserving Build controls and Simplified menus on.

## Claude live report, 02:32 EDT

Evidence: mailbox report `20260926-063258-claude-live-1-travel-fpv-phone-manage-worlds-pass-hover.md`.
Still candidate 2; no save written.

- Manage Worlds: keyboard lot selection of Crick Cabana, then native Play,
  loaded Live. Actions append after the lot list; focus does not automatically
  jump into the action panel. Reachable but a remaining usability limitation.
- First-person: five on/off cycles passed with announcements and no HUD or
  modal activation. Native scanner follow relinquished/restored correctly.
- M > Go alone > Willow Creek > Magnolia Blossom: arrived at the park.
- Escape in world list: native cancellation, spoken Travel cancelled.
- Ctrl+Alt+P: phone categories and native localized category/action labels
  worked. Phone Travel was native guid 98908, not the anticipated 99808;
  its native path reached the destination list. Preserve its native semantics.
- Test household had no eligible companions, so EA skipped the companion
  picker. This does not verify the empty-answer hook or multi-selection.

Confirmed failures being fixed in candidate 3:
- Stationary pointer over recycled rows interrupted keyboard labels with
  unrelated hover labels. Hold hover narration during keyboard navigation
  until physical movement/click; direct hover mode remains available.
- Redundant corner Close remained a stop between picker rows and chrome.
  Omit btnClose only in simplified mode; preserve Done and Escape behavior.
- Scanner announcements occurred briefly between replacement picker windows.
  Python transition suppression is being addressed by Claude.
- Go alone used a wall-clock claim timeout despite paused gameplay. Replace
  it with ownership tied to the native interaction lifecycle.

Third UI rebuild started around 02:36 after all JavaScript suites passed,
including 25 simplified-menu checks. Live acceptance of those fixes pending.

## Combined candidate 3

Installed September 26 around 03:09 EDT with the game closed. Backup:
`build/v14x-before-simplified3-test/deployment.json`. Configuration preserved.

- UI SHA256: `19b4b2ea59aceb8c6c6d430995934bf3d3bd74817e26708cb0a99235985b79a3`
- Script SHA256: `0b3afbdac30db5bdf12da24cf7b07f338dc9924556d36fa051d48af20790b4c9`
- UI snapshot: `build/v14x-simplified3-ui-candidate`
- Script snapshot: `build/v14x-simplified3-script`
- Stable automated run: 1,099 checks across 64 suites passed, including
  repeated imported checks. Script source hashes match the tested inputs.
- All 25 UI movies rebuilt; bytecode fidelity passed.
- Includes stationary-pointer hover suppression, redundant picker Close
  filtering, scanner transition suppression and lifecycle-owned solo travel.
- Game launched and foreground; exclusive input handed to Claude at 03:10
  for remaining live acceptance on existing saves without saving.

The user explicitly requires remaining verification before release staging.
No final release ZIP has been created from this candidate.

## Candidate 3 local live checks, 03:25–03:37 EDT

Codex took game input back after the external handoff stalled; Claude
acknowledged no input at 03:27 and is reviewing/fixing source only.

- Escape menu: one Up/Down press per option; 12 entries, redundant Close
  omitted. Keyboard opened Options and Manage Worlds. Native confirmation
  offered Save / Just Go / Cancel; chose Just Go, no save written.
- Options: categories are individually focusable, but their order interleaves
  with settings by screen position. A native list entered in reverse announces
  its local count (5 of 5), which is confusing after scope-wide numbering.
  Autonomy Off/Full and played-household aging Yes/No/Only Active Household
  dropdowns moved one choice and Escape preserved the existing values.
  Those dropdowns currently speak values without their setting label.
  Claude owns a bounded Options block-order/context fix, pending candidate 4.
- Phone: one Down per category, singular "1 action" verified. Social opened
  with Back to the phone, then Plan a Social Event. No spurious hover label
  interrupted these keyboard rows despite the pointer over another row.
  Native action 32268 queued while paused and opened after unpausing.
- Events: each Down advanced one event type and read its own name, price and
  description. Enter on Birthday Party advanced to Invite Sims. Role controls
  were reachable; Birthday Sim opened. Space selected Season Test and spoke
  checked / 1 selected; Down reached OK, Enter returned with the role filled.
  Guest picker preserved the native two-required rule; this test Sim knows
  nobody eligible, so completion cannot be verified in this household.
- Event location BLOCKER: Select a Place opens; Down goes from All Lot Types
  to Willow Creek (1 of 25). The next Down skips the four visible nested
  venues and jumps to Henford-on-Bagley (2 of 25). Reported at 03:36 to Claude
  for a nested-list traversal fix and regression tests. Not a release pass.
- Escape cancelled the event planner; household funds remained 22,062.

Continue companion/event completion on an existing multi-Sim household;
no CAS and no saving. Release staging remains blocked on verification/fixes.

## Candidate 3 follow-up, 03:39–03:54 EDT

- BFF household: Go alone incorrectly showed the companion picker when
  Liberty and Summer were eligible. Claude fixed the immediate-interaction
  timing in Python; candidate 4 live verification is required.
- Choose who comes: Space selected Summer (1), deselected her (0), then
  selected Liberty and Summer (2). OK accepted both. After unpausing,
  keyboard world/place navigation reached Club Calico. Both companions
  arrived beside Travis at 03:47; native speech said everyone was coming.
- Business phone list exposed Find a Job, Quit Job and Take Vacation Day.
  Find a Job opened the native selector after unpausing. Each Down moved
  one filter/job; Actor and Detective spoke their own descriptions. Enter
  selected Detective and updated its details. Escape cancelled; Travis
  retained Quality Assurance. No career change committed.
- Personal inventory opened, but Travis's inventory was empty, so this
  does not verify item actions or purchase quantities.
- Exited without saving for the candidate update.

## Candidate 4 installed, 03:54 EDT

- UI: `0b8bc29adba41a221b1325b4302b17c928d3b46e54e5eeee26a123d80a3305e9`
- Script: `49ac942f4d626e32074a9319b9ca2def870c103f6a7078e3254682575213c8e1`
- Frozen folders: `build/v14x-simplified4-ui-candidate` and
  `build/v14x-simplified4-script`; backup `build/v14x-before-simplified4-test`.
- 1,114 checks across 66 suites passed with stable inputs. All 25 movies
  rebuilt and bytecode fidelity passed; compatibility package rebuilt.
- Configuration preserved. No release ZIP staged. Live fix acceptance and
  remaining purchase/household/event completion checks remain outstanding.

### Candidate4 live follow-up, 04:05-04:14 EDT

- Birthday Party: selected Travis and two guests with Space; the native two-guest
  requirement remained disabled until both guests were selected. Pointer setup
  was used between stages; this is not an entirely keyboard-only run.
- Venue keyboard traversal passed: Willow Creek, BFF Residence, Museum, Park,
  Nightclub, Henford-on-Bagley; Up from Henford returned to Nightclub. Enter
  selected The Blue Velvet and updated its preview. Home was then selected for
  the native completion test. Done started the party and charged exactly 100
  simoleons (9000 -> 8900). End Social Event was selected with Down/Enter in
  the native confirmation and ended the event normally without saving.
- Gameplay Options announced `Autonomy: Off` and `Auto Age (Played Households):
  Yes`; Escape closed their dropdowns without changing either value, then
  returned through Options/Menu to the world.
- BLOCKER: Phone > Shopping > Purchase Gifts (186369), 04:11:33, left a dim
  screen with no purchase widget. Escape and console close did not recover it.
  No new Python exception file. Log reports action ran, then world:00. Alt+F4
  still opened the native exit prompt; exited without saving at 04:14.
  Claude was sent the action, timing and logs for source investigation.
- Purchase quantity/inventory-item and household transfer completion still
  pending. Candidate4 must not be described as release-verified.

### Candidate4 purchase isolation and inventory, 04:17-04:24 EDT

- Native phone Shopping > Purchase Gifts opened the complete purchase widget,
  isolating the blank modal to simplified phone handoff.
- Keyboard traversed filters/sort then A Game of Groans (25). Right changed
  quantity 0->1->2; Left 2->1. Spoken quantities/totals matched 25->50->25.
  Enter moved to Done without charging; Enter on Done charged exactly 25
  (22062->22037). Inventory contained the purchased book.
- I opened inventory; one-step navigation reached controls and the named book.
  Enter opened its pie; Down/Up traversed Place in World/Read. Enter Read queued
  it; after unpausing the Sim sat and visibly read the book. PASS.
- Exited without saving. Candidate5 retains candidate4 UI and fixes the phone
  action handoff by waiting for the client modal to close, refusing on timeout.
- Candidate5 script: 49733db76926681989ee57b7d22db44e01b9422f57983851d0c3ea50aece2547.
  1117 checks across 66 suites passed on stable inputs; frozen source/bytecode
  verified and installed with game closed, configuration preserved.

### Candidate5 live, 04:29-04:34 EDT

- FIX ACCEPTED: simplified Phone > Shopping > Purchase Gifts opened the full
  purchase widget while paused. Log 04:29:24 modal 10->00 precedes ran 186369;
  04:29:25 purchase dialog announces quantities, available funds and total.
  Escape returned to the world, funds unchanged at 22062.
- Phone > Travel > Move Household queued normally; unpausing entered the native
  moving map. Pointer setup selected Daisy Hovel and opened confirmation.
- Final move dialog keyboard traversal: Keep Furniture, Furnished, Purchase Home
  (three controls). Enter opened Furnished; Up/Enter selected Unfurnished.
  Remaining funds changed 13833->19253 and both the new value and furnishing
  choice were spoken. Tab reached Purchase Home with all context repeated.
  Escape canceled without purchasing. An occupied BFF lot offered no move
  confirmation. Cancel Moving returned from the map without committing.
- Household transfer still pending; no release package staged yet.

### Candidate5 household transfer, 04:36-04:45 EDT

- Manage Worlds > Manage Households > Transfer Sims opened the shared native
  Household Split and Merge panel. Space selected Season Test; Enter on
  Transfer Sim(s) moved her into a new-household preview. Empty-household
  rules moved the full 22062 in the preview. Disabled arrows spoke their reason.
- Select another Household reset that preview. Selected Caliente for a
  two-populated-household funds check. Amount input is index 11/12, after
  funds arrows and before Done. It speaks the numeric value alone.
- Down reached Done; Up returned to amount. Enter activated editing;
  Ctrl+A and typing replaced 100 with 150. Tab exited editing, Up reached
  the right funds arrow, and Enter updated 22062/28500 to 21912/28650 once.
- Escape canceled the dialog. Done was deliberately not committed. This
  verifies the shared transfer UI from Manage Households, not phone Split
  Household eligibility or every Ask to Move In entry path. Pointer setup
  was used to select the second household; keyboard amount editing and Sim
  transfer were exercised explicitly. Claude reviewed the log and found no
  blocker; amount label readback is follow-up polish, documented in CONTROLS.
- All targeted remaining live checks are now complete. Candidate4 UI and
  candidate5 script remain unchanged from the stable automated run.

### Release staged and installed, 04:46 EDT

- dist/2026-09-26_0446 contains main and optional UI Cheats compatibility ZIPs.
- Main ZIP SHA256: 7d5df9eb82a8ed8aa70a31fe3b15a20ce7621c1b20fab596ccb00403de75513e.
- Release script SHA256: 5f5a758e228d509d2029642ece2a80d887b583c0ea80d665b33f7342a28fbe6a.
- Release transform/frozen-bytecode parity passed. All five installed ZIP
  members verified identical; backup build/v14x-release-0446-backup.
- Test session exited without saving. Diagnostic logging restored off;
  build controls, simplified menus and scanner mode remain on.
- Player guides updated and packaged. No upload/publication performed.
