> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# Screen Reader: pick up here

# ============================================================
# HANDOFF — state as of 2026-08-12 ~06:00
# ============================================================

Read `HANDOFF.md` for architecture. This block is the CURRENT state; the
dated sections below are history (newest first) and are still accurate as
records of why things are the way they are.

## HOUSEHOLD INVENTORY NARRATION: CLOSED 2026-08-20, tester-confirmed
## "works perfectly" same day. cfg logging back to off.
## Release pair `tyjokr_ScreenReader_2026-08-20.zip` +
## `_SpeechPack_2026-08-20.zip` cut same day (supersedes the never-
## posted 08-12 pair; embedded package byte-verified against the
## tester-confirmed build). Compat package rebuilt in lockstep
## (3,109,302 bytes) + tester copy refreshed. Neither zip uploaded yet.

Rawdiag capture 2026-08-20 ~12:38 (build-mode household inventory; user
confirmed live-mode sim inventory is FINE). Four defects, all from the
one capture:

1. FIXED (Python): currency regex `[\d][\d.,]*` swallowed a trailing
   sentence period, so "§645. Romantic Décor" spoke as "645. simoleons
   Romantic Décor". All four currency rules now require the capture to
   END on a digit. Only composed single-string payloads hit this
   (per-segment payloads clean each segment standalone).
2. FIXED (Python): NO html-tag stripping existed anywhere; composed
   Flash payloads pass raw EA strings through ("The Indoor <i>and</i>
   Outdoor Plastic Chair" was spoken with tags). _clean_glyphs now
   strips `</?[a-zA-Z][^>]*>` on every channel (also cleans <b> junk in
   mod welcome notifications).
3. FIXED (Flash, CatalogImageCellView): stack count folded into the
   composed cell line via a `\x02qty\x02<n>` marker when mData.count>1,
   rewritten Python-side to the LOCALIZED "Quantity N" (new 'quantity'
   entry in lang.py, 17 languages). Wording per user: "Quantity 2".
4. FIXED (Flash, TooltipManager.A11yAnnounceDisplay): a single-field
   widget announce whose text is bare x<digits> (A11yIsBareCount) is
   SKIPPED entirely: covers the disconnected "x2" chatter, EA's
   INVISIBLE "x99" authoring placeholders on unstacked cells (the
   screenshot showed no badge where the log read x99), and the
   badge-cancels-the-pending-description bug (skip returns BEFORE the
   widgetname/stop fallback so parked descriptions survive).
5. FIXED (Flash, CatalogImageCellView): instance items (player
   paintings etc.) share ONE CatalogProduct, so every stack-flyout cell
   announced the base name ("Monochromatic Sea Monster") and the real
   title only arrived via deferred tooltip. The composer now leads with
   the per-instance name from mData.metadata: custom_name (String) ->
   recipe_name (LocKey.toString() localizes) -> header, falling back to
   mData.Name. Per user: flyout cells announce their own name.

Test drill (tester): build mode -> household inventory. Expect:
"VIP Bucket. 645 simoleons. Quantity 2. Romantic Décor: 5. Heirloom
Eligible"; no bare "x2"/"x99" utterances ever; sweeping cells then
lingering reads the description (badge no longer cancels it); flyout
paintings read "Ten Tickles..." not the base name; plastic chair reads
without "<i>"; personal sim inventory must stay fine (regression check:
the xN-skip and tag-strip are global).

Open questions if something misbehaves: metadata title fields are
UNVERIFIED against a live capture (custom_name/recipe_name/header were
chosen from ObjectMetadata pcode semantics; if paintings still read the
base name, capture with rawdiag and check which field carries the
title). gate + suites green (43 + 39; settings suite recounted 41->39
by the 2026-08-16 session, pre-existing).

## PICKER SCROLLING: CLOSED. CLEANUP DONE + RELEASE CUT 2026-08-12

Final design (user-approved through 5 in-game rounds): relative one-row
scrolling by measured pitch, `mA11yIdxInList` stay-put timeout, and the
progressive nudge in `A11yIndexFrame` as knife-edge recovery. Quarter-row
headroom was tried and reverted (too slow for held-key runs); the ~9%
nudge stutter and the below-fold blank-highlight fast paths are ACCEPTED
trade-offs. Do not re-add headroom or ensure-visible unprompted.

Cleanup completed 2026-08-12 (all five owed items):
1. NAV diagnostics stripped (counter, function, 4 call sites); verified
   absent in shipped pcode. The permanent boot mark ("live TooltipManager
   copy is from <movie>") STAYS.
2. Keepers confirmed in shipped bytecode: mA11yIdxInList, mA11yIdxPitch,
   relative scroll, nudge.
3. Rebuilt + gate PASSED + deployed, hash A56C059B..., 17,595,812 bytes.
   Tester cfg set logging = off (BOM-free, configparser-verified).
   Deployed ts4script remains the DEV build (unchanged all session).
4. UICheats compat package rebuilt from the fixed class (3,108,241
   bytes) and the tester's in-folder copy refreshed (hash 9B0D16F6...).
5. Suites green: test_speech_modes 43/43, test_settings_cfg 41/41.

Release pair in dist/ (2026-08-12): `tyjokr_ScreenReader_2026-08-12.zip`
(17,108,151 bytes, DLL-free guard passed, for CurseForge) +
`tyjokr_ScreenReader_SpeechPack_2026-08-12.zip` (199,946 bytes, for Sim
File Share). Zip verified to embed the final UI package byte count.
NOT yet uploaded anywhere; compat package remains a separate unhosted
artifact (licensing: ask weerbesu before hosting publicly).

Still-open items unchanged (see older sections): read-key jank fix
choice (a)/(b), EA-drift checker, CAS parked, review backlog, other
picker movies' engagement hooks if testers report silence,
FashionPurchasePickerCellView backlog.

## (history) ROUND 4-5 (2026-08-12 evening): quarter-row headroom
## REVERTED at user request; one-row stepping + nudge is the FINAL
## design (was hash 8664D564..., 17,603,280 bytes)

Round-4 capture (~19:25): the quarter-row build worked mechanically
(deltas ~99, tries=1 everywhere) but the user judged rapid
down-navigation too slow: during held-key runs every step pays the
scroll+wait cost and the view outruns the fold. DECISION (user): revert
to exactly one row pitch per step; the ~9% knife-edge misses are
handled by the A11yIndexFrame nudge (~100ms auto-recovery), accepted as
the trade. The below-fold blank-highlight fast paths therefore also
remain; do NOT re-add headroom or ensure-visible without the user
asking. Comment at the `_loc11_` computation in A11yIndexScroll records
this. Next capture doubles as final confirmation -> cleanup list.

## ROUND 3 (2026-08-12 ~05:40 capture, superseded by round 5): nudge
## CONFIRMED working, quarter-row headroom added (since reverted),
## was hash 24739A4E..., 17,603,488 bytes

Round-3 capture: ZERO silent stalls, every row 0..48 announced in
order; the nudge fired 4 times (rows 6/13/21/48) and recovered in ~100ms
each. Tester still felt those 4 as stutter ("a little glitchy in the top
half") plus the below-fold blank-highlight fast paths. Root of both: the
one-pitch scroll aims the target's edge exactly at the build knife edge.

**Fix deployed (user-approved): scroll by pitch + pitch/4** so the
target lands a quarter-row inside the fold. Drift self-balances via
occasional skip-scroll fast paths; the nudge stays as backstop. Expect
in the next log: scroll deltas ~99, near-zero nudge lines, and fast
paths that land on VISIBLE rows. Bonus validation seen in round 3: row
heights jitter (pitch measured 81 near "Crisis Barn" vs 79 elsewhere);
measured-pitch absorbed it.

If the next run is clean: that run doubles as final confirmation ->
proceed straight to the cleanup list (strip diagnostics, release pair,
compat rebuild, suites).

## ROUND 2 (2026-08-12 ~05:17 capture): main fix CONFIRMED, one
## residual glitch found + fixed, redeployed

Tester ran the confirmation capture: relative scrolling WORKS. One row
per press in both directions, slider stepping +-79.33 per move, the
upward path (fully stuck before) now walks normally. Tester's words:
"works a lot better now."

**Residual glitch (tester: "sometimes highlights a blank row off screen,
reads nothing, second press makes it go again"), root-caused from the
same capture:** a one-pitch scroll can leave the target row's TOP a few
px below the fold (rows 6/10/13/20 in the log, offset +5.67px each
time). Whether the recycling pool builds that just-below-fold row
depends on whether the row leaving the top edge has fully cleared and
freed a cell, a floating-point knife edge that flips "sometimes"
(single-pitch scrolls realized in 1 frame dozens of times in the same
run). When it does not build: 20-frame timeout, stay-put, SILENCE; the
tester's second press re-anchored one more pitch and it built in 1
frame every time.

**Fix deployed: progressive nudge in `A11yIndexFrame`.** While waiting
for the target to realize, every 5 frames without a view push the
slider one more pitch (clamped, re-anchored on the live value, max 3
nudges inside the existing 20-frame cap), i.e. the second keypress is
now automatic. Diag line: `NAV nudge tgt=N try=T slider X->Y`. Diag cap
raised 80 -> 160 (the confirmation run exhausted 80 exactly).

**Known minor, NOT yet fixed (needs a design call):** fast-path steps
(target already built) can focus a row the pool built BELOW the fold:
focus ring on clipped blank space, speech CORRECT (this is the
"highlights a blank row off screen" part; the ring draws on our
unmasked tooltip layer). Proper fix would be ensure-visible: also
scroll one pitch on fast-path steps when the focused row sits outside
the viewport. Deliberately not done yet: it touches the fast path that
is working flawlessly speech-wise; ask the user before changing it.

## Purchase picker scrolling: ROOT CAUSE (round 1, 2026-08-12 ~03:30)

The 2026-08-12 capture run (first one with working logging) settled it in
one pass. Log analysis plus a pcode decompile of EA's GridLayout:

**EA's `GridLayout.GetPositionOfIndex` is broken for vertical lists.** Its
axis branches are swapped: mbHorizontal=true returns
`index * (cell HEIGHT + vertical margin)`, mbHorizontal=false (all our
vertical pickers) returns `index * (cell WIDTH + horizontal margin)`. On
the purchase picker that is index * 426.7 in a slider space where a row is
79px, so:

- every down-scroll landed ~5.4x too far ("scrolled past many options"):
  `NAV scroll tgt=6 pos=2560 ... slider 0->2247` (correct target ~164)
- after two overshoots the slider clamped to max ("ended on bottom rows")
- every up-target computed ABOVE max and clamped back to max, i.e. the
  current position, so the slider never moved at all ("could not scroll
  back up"): `NAV scroll tgt=270 pos=115218 ... slider 21509->21509`

Realization was NEVER the problem: every row the slider actually reached
realized instantly (all the `realized=1` fast paths in the log). The
force-all-rows layout swap stays rejected, per the handoff's "slider lands
far away" reading. `RecyclingGridLayout` does not override
`GetPositionOfIndex` (checked in pcode); EA presumably never calls it on a
vertical list themselves, which is how it stayed broken.

**The fix (in `A11yIndexScroll`, TooltipManager_patched.as): never call
GetPositionOfIndex; scroll RELATIVE instead.** Steps are always +-1, so:

- pitch = |y delta| of the two realized rows being stepped between
  (exact, includes margins); falls back to `GetCellBounds().height` when
  no neighbor pair exists (first step after a mouse focus at a list edge,
  or a same-row neighbor in a multi-column grid, where the y delta is 0)
- new slider value = live value +- pitch. Re-anchoring on the LIVE value
  every step means pitch error can never accumulate; a short step
  self-heals on the next press. tgt==0 still forces MinValue, and a wrap
  up from index 0 to the last row now lands on MaxValue.
- if the slider cannot move and the target is not realized, an in-list
  step returns HANDLED without arming the frame-wait (which would be a
  guaranteed timeout); that keeps the caller out of the legacy
  wheel+teleport recovery. Wrap callers keep their old fallthrough.
- the `A11yIndexFrame` wait and the `mA11yIdxInList` stay-put timeout
  mitigation are unchanged.

### Deployed right now (2026-08-12 round 2, hash-verified 2C19C8B6...)
- `tyjokr_ScreenReader_UI.package` 17,603,293 bytes, 23 movies, NAV
  diagnostics STILL IN (cap 160) for the nudge confirmation run.
  (Round 1 build was 17,599,438 / 344CD6E2..., superseded same day.)
- ts4script and cfg unchanged from 08-10 (this was a Flash-only fix):
  DEV script build, cfg logging = on, BOM-free (byte-checked).
- `gate_pcode.py` run and PASSED (untargeted classes identical, no
  int-op degradation). NOTE: the ps1's GFX-magic check alone is NOT
  enough; the 08-10 diagnostics build shipped un-gated and carried a
  benign generic increment (see the FFDec lesson below).

### Nudge confirmation run (tester, next action)
Same procedure: Purchase Books picker, hold Numpad 6 through the list,
then Numpad 4 back up, quit, read the log. Expect: NO step ever goes
silent (the round-2 failure mode `idxframe ... tries=20 got=null` must
not appear); occasional `NAV nudge tgt=N try=5 slider X->Y` lines
followed within a few frames by `got=view` are the fix working. One row
per press in both directions as in round 2.

### FFDec lesson (NEW, add to the pile)
`static var x:int; x++` compiles via `convert_d` + GENERIC `increment`
(Number math), even though instance-property ++ on an int compiles to
`increment_i`. gate_pcode.py rightly refuses it. Write `x = x + 1`
instead (compiles to the same add/coerce shape EA's own int math uses).
Cost one full rebuild cycle to learn.

### Work-dir note
`flash/work-1.126.78/` is now COMPLETE for all 23 movies:
`ea_PickersPurchase.swf` was extracted 2026-08-12 from the live 1.126.78
UI.package (it was missing; the 08-06 and 08-10 builds used a session
scratch that is gone). Safe to reuse as -WorkDir until the next EA patch.

### Cleanup owed once the picker is confirmed (DONE 2026-08-12, see top block)
1. Strip the NAV diagnostics (`A11yNavDiag`, `sA11yNavDiagCount`, the
   three call sites) from `TooltipManager_patched.as`.
2. `mA11yIdxInList` STAYS (real fix). The relative-scroll rewrite STAYS.
3. Rebuild, gate, redeploy, cut a fresh release pair, set `logging = off`
   in the tester's live cfg (the template already defaults off).
4. REBUILD THE UICHEATS COMPAT PACKAGE TOO: it still embeds the OLD
   TooltipManager (built 08-06, pre-fix, pre-diagnostics). Currently
   inert on the tester's machine (no UI Cheats installed, and sitting in
   the mod folder it loses the 4 shared movies to the later-loading main
   package), but shipping it stale would hand the broken scroll math to
   anyone who moves it to a priority folder.
   `build_uicheats_compat.ps1` + `build_compat_package.py`.
5. Re-run `tools\test_speech_modes.py` + `tools\test_settings_cfg.py`
   (43 + 41 checks) and the scratch `test_picker_i18n.py` if kept.

# ============================================================
# (history) 2026-08-10 02:45 — capture-wait state, SUPERSEDED 2026-08-12
# ============================================================

The block below described the state while waiting for the capture. The
capture happened 2026-08-12 and proved the "slider lands far away"
scenario; kept as the record of the diagnostics design.

## Exactly one thing is broken

**Purchase picker keyboard scrolling.** Everything else in the mod works
and is tester-confirmed. Do not start anything new before this is closed;
a diagnostics build is already deployed and waiting for one capture run.

Tester's last report (on the build BEFORE the current diagnostics one, or
possibly during its deploy — timing unclear, see "cfg was dead" below):
first 5 rows read normally, then it "scrolled past many options several
times", ended on the bottom-most 5 rows, and from the bottom could not
scroll back UP at all.

### What is deployed right now
- `Mods\tyjokr_ScreenReader\tyjokr_ScreenReader_UI.package` — 23 movies,
  17,594,565 bytes, deployed 2026-08-10 02:30, **contains NAV
  diagnostics** (see below). Hash-verified against the build output.
- `tyjokr_ScreenReader.ts4script` — 81,678 bytes, DEV build (2026-08-10
  01:14), so its in-code log default is ON, but the cfg governs.
- `tyjokr_ScreenReader.cfg` — logging = on, hover, tooltip delay 1.5,
  keyboard on. Verified parseable by loading it through the mod's own
  settings module.
- Game is **1.126.78** (patched 2026-08-06). Everything above was built
  against that version's UI.package.

### The NAV diagnostics (deployed, TEMPORARY — strip when done)
`TooltipManager_patched.as` posts one `a11y.mark` line per navigation
decision, capped at 80 per session (`sA11yNavDiagCount`). They appear in
the log as `MARK: live TooltipManager copy is from "NAV ..."`:

- `NAV step dir=1 idx=4 n=57 tgt=5 realized=0` — from `A11yStepInList`:
  current grid index, total items, target index, and whether
  `GetViewAtIndex(tgt)` returned a built row.
- `NAV scroll tgt=5 pos=420 region=300 cell=84 slider 0->204 max=4536` —
  from `A11yIndexScroll`: the scroll math and the slider move.
- `NAV idxframe tgt=5 tries=20 got=null inlist=1` — from
  `A11yIndexFrame`: whether the row ever materialized and after how many
  frames. **`got=null tries=20` is the smoking gun for a timing failure.**

### Reading the result
- Mostly `realized=1` -> fast path fine, only the scroll boundary is broken.
- Runs of `realized=0` + `idxframe got=null` -> rows genuinely are not
  built when asked; that is when swapping the layout becomes justifiable.
- `slider X->Y` landing far from where the row should be -> the position
  math is wrong and forcing all rows would NOT have helped.

### Root cause already proven (do not re-derive)
The list is `new RecyclingGridLayout(false,false,1)` (confirmed in
`PurchasePicker.as` ~line 364). When `GetViewAtIndex(target)` fails to
realize within 20 frames, `A11yIndexFrame`'s legacy recovery ran
`A11yTryScroll` (dispatches a MOUSE_WHEEL of **3 notches** = "scrolled far
past") and then `A11yScrollFrame`, which finds the new row by **identity
diffing** (`A11yFirstNewItem`) — impossible on a recycling layout, so it
fell through to `mA11yEdge` + `A11yTabMove`, teleporting focus to a list
edge ("refocused at the top of the dialog"). **Already mitigated**: an
in-list step sets `mA11yIdxInList`, and on timeout the code now returns
without moving instead of entering that recovery. So the current build
should fail as "stops moving", NOT "flies away". If the tester still sees
flying, something else is calling the legacy path.

### Ideas already considered
- **Force all rows to load** (tester's suggestion): EA ships
  `StaticGridLayout` and `PersistentCellGridLayout`, and the layout is a
  parameter to `InitializeScrollList`, so it IS swappable. Rejected for
  now: a several-hundred-row catalogue would build every cell up front
  (real perf change to EA's UI) and it treats the symptom, not the timing.
  Becomes legitimate if the log proves realization is unreliable rather
  than merely slow.
- The upward direction ("could not scroll back up from the bottom") takes
  the SAME code path with param1 = -1; note `A11yIndexScroll` forces
  `_loc11_ = MinValue` when target index is 0, and aligns to `_loc8_`
  (top) for negative directions. Worth checking those two branches first
  if the log shows up-moves failing while down-moves work.

## HOW TO GET THE CAPTURE (next session, first action)
1. Confirm `logging = on` in the cfg (it is, as of this writing).
2. Launch, open a Purchase Books picker, hold Numpad 6 until it
   misbehaves, then press Numpad 4 several times to test the upward path,
   then quit.
3. Read `Mods\tyjokr_ScreenReader\tyjokr_ScreenReader.log` off disk and
   grep for `NAV `.

## ***cfg EDITING TRAP — cost a whole test run 2026-08-10***
PowerShell 5.1 `Set-Content -Encoding utf8` writes a **UTF-8 BOM**.
`configparser` then dies on line 1 with `MissingSectionHeaderError`, the
WHOLE cfg is discarded, and every setting silently falls back to defaults
(logging off included) — the file looks correct when you read it. Already
fixed once. **Never write the cfg with PowerShell's utf8 encoding**; use
`[System.IO.File]::WriteAllText(path, text, (New-Object
System.Text.UTF8Encoding($false)))` or the mod's own settings module, and
verify afterwards by importing `tyjokr_a11y_settings` and checking
`load_errors` is empty.

## Install oddities to be aware of (not bugs, just state)
- **No speech pack is installed anywhere under Mods** — the three DLLs are
  absent from the whole tree. Speech therefore falls back to the Windows
  SAPI voice. That is expected behavior without the pack, but if a test
  needs a real screen reader voice or braille, install
  `dist\tyjokr_ScreenReader_SpeechPack_2026-08-06.zip` first.
- `tyjokr_ScreenReader_Compatibility_UICheats.package` is present in the
  mod folder. That is the tester's own placement; it is NOT shipped and
  its build scripts note the user deploys it themselves.
- `dist\` still holds the pre-rename `tyjokr_ScreenNarrator_*` zips
  (08-01..08-04) alongside the current `tyjokr_ScreenReader_*` ones.
  Latest release pair: `tyjokr_ScreenReader_2026-08-06.zip` (CurseForge,
  DLL-free, guarded) + `tyjokr_ScreenReader_SpeechPack_2026-08-06.zip`
  (Sim File Share).

## Cleanup owed once the picker is fixed
1. Strip the NAV diagnostics (`A11yNavDiag`, `sA11yNavDiagCount`, the
   three call sites) from `TooltipManager_patched.as`.
2. Decide whether `mA11yIdxInList` stays — it should, it is a real fix.
3. Rebuild, redeploy, cut a fresh release pair, set `logging = off` back
   in the shipped default (the cfg TEMPLATE already defaults off; only the
   tester's live cfg is on).
4. Re-run `tools\test_speech_modes.py` + `tools\test_settings_cfg.py`
   (43 + 41 checks) and the scratch `test_picker_i18n.py` if kept.

## PURCHASE PICKER CART NARRATION (2026-08-06)

Tester report: the purchase picker (Purchase Books etc.) never narrated
quantity changes. Built per WCAG cart practices (announce value on
change; polite debounced totals; name-in-context on the +/- buttons;
state re-readable via the read key):

- New `extra-classes/PurchasePickerCellView.as` in the **PickersPurchase**
  movie (0x3EEF420EE17FE553; package now 23 movies). ALL purchase picker
  classes are defined ONLY in that movie (scanned all 258).
- Announce hook lives in `IncreaseAmount`/`DecreaseAmount` — the single
  funnel for mouse AND gamepad. The new value is read ONE FRAME LATER
  (ENTER_FRAME once): the click dispatches an event the picker handles by
  redrawing the cell, so txtItemAmount is stale at dispatch time.
- Totals: per-cell 1.2 s one-shot Timer, restarted on every click; on
  fire it walks parents to the object holding txtItemCount/txtCost and
  reads EA's OWN localized footer labels + values ("Total Count: 4.
  Total Cost: §100" -> glyph cleaner turns § into "simoleons"), posted on
  a11y.event_enc (never interrupts). Multiple cells' timers can overlap;
  identical text within 1 s is deduped Python-side, so no spam.
- Spin-button hover: ROLL_OVER posts "increase|decrease \x01 <name> \x01
  <qty>" on widget_enc; the bare tokens are translated Python-side via
  the same mechanism as checked/unchecked (new lang.py entries, 17
  languages, first-pass).
- narrator: a11y.widget_enc now calls _cancel_pending_name() — a real
  widget line beats a parked derived-name placeholder (the buttons'
  "Increase" fallback used to flush 0.4 s later and talk over the real
  announcement).
- NOTE: UI Cheats Extension ALSO overrides PickersPurchase — now a FIFTH
  overlapping movie. If the (unshipped) compat package is ever revived,
  add PickersPurchase to build_compat_package.py's MOVIES and
  build_uicheats_compat.ps1.
- Backlog: FashionPurchasePickerCellView (Fashion Week stalls) wants the
  same treatment; confirm-button could announce totals on focus.

### Round 2 same day: ordering + keyboard nav (deployed, awaiting test)
- **Segment ordering bug (narrator, affects ALL composed payloads):**
  `_fields_to_segments` sorted each row's cells as `(x, text)` tuples, so
  segments with NO coordinates (all default to x=0) fell through to
  comparing TEXT and got ALPHABETIZED — "Increase / <item> / <count>" read
  as "<item> / Increase / <count>". Now `cells.sort(key=lambda c: c[0])`;
  Python's stable sort preserves Flash's post order on ties. Any future
  hand-composed multi-segment payload depends on this.
- **Keyboard nav never engaged in the purchase picker** (tester: "doesn't
  allow scrolling through the options via keyboard"). Cause: our
  `A11yFocusInto` hook is in `widgets.Pickers.PickersMain`, defined ONLY
  in the Pickers movie; the purchase picker is `PickersPurchaseMain` in
  the PickersPurchase movie, so NO focus scope was ever created. Fixed by
  hooking `PickersPurchaseMain.SetPicker` (runs from Show(); the
  loadSilently preload path returns before it, so hidden preloads don't
  steal focus). ***Deliberately NOT hooked in PickersMainBase.Show***:
  that base is compiled into SEVEN picker movies (ColumnBased, Food,
  Grid, Multi, Outfit, Purchase, Sim) = app-domain lottery.
  IF OTHER PICKERS EVER REPORT THE SAME SILENCE, patch each movie's own
  *Main subclass, not the shared base.
- **Arrow-key stepper (spinbutton convention):** Left/Right now call
  `A11yArrowHorizontal`, which walks up from the focused object looking
  for `IncreaseAmount`/`DecreaseAmount` (DUCK TYPED — never import
  PurchasePickerCellView, it exists in one movie and a static ref to an
  absent class is an uncatchable verify-time crash) and adjusts the
  quantity; anything else falls through to the old move-focus behavior,
  so other dialogs/pickers are unchanged. Up/Down still walk rows. The
  +/- buttons were deliberately NOT made separately focusable (would
  triple tab stops in a long list).
- KNOWN RISK if testing shows Left/Right no-op: arrows are gated on the
  scope class name containing "Dialog"/"Picker". PickersPurchaseMain
  matches, but if the resolved scope is some inner container it would
  fail; widening that gate is a one-liner.

## UI CHEATS EXTENSION COMPATIBILITY (2026-08-05) — BUILT, THEN NOT SHIPPED

**SUPERSEDED 2026-08-06: it IS shipping**, as
`tyjokr_ScreenReader_Compatibility_UICheats.package`, and it does NOT go one
folder deeper any more — users drop it in their own priority/late-loading
folder. (Prior decision, kept for context: "not shipping", on the grounds that
a separate download was a no-op for the user.) Everything below is kept for the
record; the machinery stays in flash/ (build_uicheats_compat.ps1,
build_compat_package.py, uicheats-base/, and the built
tyjokr_ScreenReader_Compatibility_UICheats.package at the workspace root). The
runtime getDefinitionByName bridge in TimeControlsMain STAYS in the main
package (self-contained, zero-cost, activates only if our TimeControls
ever wins alongside UI Cheats). Test rig (compat + UI Cheats pair)
removed from Mods.

**Support consequence to remember:** with UI Cheats installed and no
compat, their package wins the 4 shared movies — needs/clock/phone
narration dies, and their unpatched Olympus TooltipManager copy can win
the app domain some sessions and silence narration ENTIRELY. "Narration
randomly stopped working" reports should ask about UI Cheats first.
README carries a short known-conflicts note.

UI Cheats Extension v1.57 overrides 24 UI movies; 4 collide with ours:
**SimInfoMotivePanel, SimInfoTray, TimeControls, ClassLibraryOlympus.**
Packages: later-loaded wins per resource; "tyjokr_..." sorts before
"UI_Cheats_...", so with both installed THEIR copies win all 4 — our
needs/clock/phone announcers die, and their Olympus carries an UNPATCHED
TooltipManager copy that can win the app domain in some load orders and
kill narration everywhere (the CommodityContainer nondeterminism class).

**Three-way diff findings (vanilla vs ours vs theirs, decompiled v1.57):**
- They touch NONE of the classes we inject — no CommodityContainer, no
  PhoneCategoryScreen, no TooltipManager, no CatalogImageCellView edits.
  Their cheat logic lives in their own classes: olympus/extensions/cheats/*
  (incl. new GenericCheatsExtension) in Olympus, SimInfoTrayMain (+2KB) in
  the tray, MotivePanel*CellView tweaks, and container tweaks in
  TimeControls (weather/lunar/eco click cheats).
- ONLY genuine collision: **TimeControlsMain**. Their entire edit is 3
  lines: import GenericCheatsExtension; txtGameTime.mouseEnabled = true
  (IDENTICAL to our clock-hover fix — converged); attach the extension
  with cheatType="time". REPLICATED in our TimeControlsMain via
  **runtime getDefinitionByName + try/catch** (A11yAttachUiCheats) — never
  a compile-time import: the class only exists with UI Cheats installed,
  and unresolvable static refs crash at AVM verify time (CAS lesson).
  Works in all 4 install combinations; their commands are ui_cheats.*
  Live commands, unregistered = silently dropped without their script.
- Their per-movie bases are MIXED vintages: SimInfoTray + Olympus current
  EA, TimeControls + MotivePanel older (EA drift noise in diffs — compare
  against the POSITIVE targeted deltas, not the whole changed list).

**Compat build (new, in flash/):** `build_uicheats_compat.ps1` injects our
classes into THEIR movies (bases archived in flash/uicheats-base/,
re-extract after every UI Cheats update);
`build_compat_package.py` assembles the 4-movie
tyjokr_ScreenReader_Compatibility_UICheats.package. It must LOAD LAST to win
the 4 movies; as of 2026-08-06 that is achieved by the user telling players to
put it in their own priority/late-loading folder, NOT by the old
Mods\tyjokr_ScreenReader\compat\ one-level-deeper scheme. Contents are
location-independent. LICENSING: the compat
package embeds weerbesu's modified movies — fine for personal use, ASK
PERMISSION before hosting it publicly.

**Also 2026-08-05: speech pack DLLs are found ANYWHERE under Mods** —
`_mods_root()` walks up to the literal Mods dir; `_find_dlls()` does the
near checks then ONE depth-capped (5) walk for all three DLLs with early
exit (CurseForge forbids DLLs, so the pack is a separate download users
may drop anywhere). Release builds now produce TWO zips (main, DLL-free,
guarded by a hard fail if a DLL leaks in + SpeechPack for Sim File Share);
README-SpeechPack.txt is a source file.

# (older) Screen Narrator: pick up here (updated 2026-08-03 ~03:50, round 2)

Read `HANDOFF.md` first for architecture, then this.

## CAS SUPPORT — INVESTIGATED AND PARKED (2026-08-03)

CAS narration does NOT work and is parked. Live install is the 22-movie
build; do NOT re-add CAS movies without reading all of this.

**Everything we proved:**
1. The override mechanism WORKS for CAS. Weebersu's "More CAS Columns"
   overrides `CASLibrary` (0x89D13757C58C2E05) + `CASCustomizer`
   (0xDF09D526F4C77B95), group 0x00000000 — identical slots to ours.
2. Patching `TooltipManager` into `CASLibrary`/`CASStories` is USELESS.
   `ClassLibraryGamedata` wins that class name for the whole application
   domain (proved by `over-ClassLibraryGamedata` marks), so CAS's copies
   never load. That build ran fine but CAS stayed silent.
3. CAS renders on its OWN stage, so the live TooltipManager's mouse
   listener never sees it — hence total silence, not even a heartbeat.
4. The right hook class is `widgets.CAS.Customizer.CASCustomizerMain`:
   extends WidgetBase, has Initialize(), instantiated by the CASCustomizer
   document class, and defined in EXACTLY ONE movie (checked all 258), so
   nothing can shadow it.
5. **BLOCKER: any FFDec-rebuilt `CASCustomizer` crashes the client on CAS
   load, regardless of our code.** Two crashes. The decisive evidence:
   `cashook-CASCustomizer` (posted at the very end of Initialize, before
   any listener does work) NEVER fired in either attempt — so the crash
   precedes our hook entirely. Not the listener, not the collector.
   - First attempt also referenced `olympus.core.TooltipManager`, which
     CASCustomizer does not contain. NEVER do that: the AVM resolves class
     references when it VERIFIES a method, before any try/catch inside it
     can run, so it is an uncatchable native crash. Removing it did not
     fix the crash, but the rule stands.
   - FFDec was EXONERATED at tag level: patched vs EA original both have
     7519 tags, all 138 PlaceObject3 tags identical length, and the ONLY
     differing tag is the bytecode block (240452 -> 250324, our code).
     So the corruption, if any, is sub-tag: bytecode layout, constant-pool
     ordering, or how unresolved tags are re-emitted.
   - Weebersu patches the SAME movie successfully, so this is OUR
     TOOLCHAIN, not the movie. Next avenue if ever resumed: rebuild
     CASCustomizer with Sims 4 Studio (or a different FFDec version) and
     compare bytes against ours to find what differs.
6. Rollback is one command — extract `*_UI.package` from
   `dist/tyjokr_ScreenNarrator_2026-08-03.zip` over the deployed file.

**Also fixed while chasing this (KEEP — these are real):**
- `rebuild_all.ps1` no longer dies on ffdec stderr. Under PowerShell 5.1,
  redirecting a native exe's stderr wraps lines as ErrorRecords, and with
  `ErrorActionPreference='Stop'` that aborted the whole rebuild at the
  first movie that emitted a warning. Any future EA patch could have
  triggered this and silently shipped a half-old package.
- `rebuild_all.ps1` now injects `TooltipManager`/`CatalogImageCellView`
  ONLY into movies that define them, and hard-fails if ffdec produces no
  output. ffdec -replace fails silently when a named class is absent, and
  the script used to then read a STALE `patched_*.swf` from a previous run.
- The `a11y.mark` line had a burned-flag bug: `mA11yMarked` was set before
  the post, so a boot-time post (dead channel, no zone yet) permanently
  disabled it. Same flaw class killed the first probe build's cap. Any
  counter/flag guarding a PostServerCommand must not be burned by a post
  that was never delivered.

## ROUND 3 (2026-08-03 ~04:30) — mood fix, package 21 -> 22 movies

Tester confirmed round 2: **numpad 8, the clock, needs, skills and the
tooltip delay all work.** The clock reads `Paused. Sat. 2:35 AM` and no
longer dumps the forecast — tester PREFERS this, since the weather buttons
to its right still give the forecast. Do not "restore" it.

Only remaining item was the MOOD, now fixed and deployed:

- `MoodContainer` (SimHub movie) sets `mcMoodTextContainer.mouseEnabled` AND
  `mouseChildren` to false, so the mood name was unreachable and only the
  wide `mcMoodBkg` backdrop was hoverable — hence "reads the tooltip, and
  such a wide area". Patched to post `GetMoodName(intensity)` on
  `a11y.widget_enc` (so its description also becomes a deferred row
  tooltip). See the new HANDOFF bullet: EA disabling mouse on its own text
  is now a THREE-time pattern (motives, clock, mood) — check that first.
- **SimHub is new to the patch set**: package is 22 movies now. Adding a
  movie needs BOTH `rebuild_all.ps1` and `build_ui_package.py`.
  MoodContainer is defined only in SimHub (checked all 258), so no
  app-domain duplication.
- Package deploy was BLOCKED (game running); a watcher was armed to copy +
  hash-verify on game close. CONFIRM IT LANDED before testing.

### Cleanup — DONE 2026-08-03 ~05:00
Mood CONFIRMED working by tester. Probes removed from TimeControlsMain;
`WeatherAndSeasonContainer.as` DELETED and dropped from the patch set (its
announcer only ever logged `WXover-noclock` — the clock is covered by the
mouseEnabled fix instead, and our only edit to that class was the dead
announcer, so patching it was pure overhead). Verified probe-free in the
DEPLOYED package. Suites 43 + 41 green. Release zip
`dist/tyjokr_ScreenNarrator_2026-08-03.zip` cut (08-01 and 08-02 kept).

## OPEN ITEMS (2026-08-03, after round 3)

1. **Read key (numpad 8) feels janky / slightly delayed** — tester report,
   accepted as working-but-rough. Cause is almost certainly that
   `_probably_still_speaking()` GUESSES playback length (~15 chars/sec,
   `_busy_until`) because no backend exposes an is-speaking query. If the
   guess runs long, a press just after the audio really ended does a silent
   stop and feels dead. Two fixes offered, user has NOT picked yet:
   (a) cheap — scale the estimate by the configured `sapi_rate`;
   (b) proper — have the SAPI child print a completion marker on stdout
   (currently `stdout=DEVNULL`; would need PIPE + a reader thread) so the
   toggle becomes exact instead of estimated. (b) is the recommendation.
   Only affects the SAPI fallback path; real screen readers are unaffected.
2. **EA-drift checker for the UI half** — OFFERED, not yet built. Proposed
   `tools/check_ea_drift.py`: extract the 22 movies from the live
   UI.package, hash vs a stored baseline to report which ones EA changed,
   and decompile ONLY the ~13 classes we replace so they can be line-diffed
   against the version our `extra-classes/*.as` was forked from. That is
   the true maintenance surface: a plain `rebuild_all.ps1` re-run already
   picks up EA's changes to every OTHER class for free, because it injects
   our classes into whatever the current EA movies are. Wire into the
   per-mod patch-tracking workflow. NOTE: no XML anywhere in this half —
   movies are binary GFX/SWF + AS3 bytecode; "diffing" means FFDec
   `-export script` to .as text.
3. **CAS support** — user asked; UNTESTED, looks promising. Unlike the main
   menu (dead: no zone, so no console and no SendUIMessage), the cheat
   console demonstrably works in CAS, so the Flash->Python channel should be
   alive. TooltipManager is patched app-domain-wide, so SOME CAS narration
   may already work — TEST BEFORE BUILDING ANYTHING: enter CAS with
   `a11y.log on` + `a11y.rawdiag on`, hover panels, read the log. Expect
   CAS-from-a-loaded-lot to work better than CAS-from-main-menu. Full
   coverage would need CAS movies (CASLibrary, CASStories, etc.) added to
   the patch set, the way BuildBuy needed CatalogImageCellView.
4. Review backlog still open (see the 2026-08-02 section): dead
   `TooltipManager.ShowTooltip` hook (zero callers in all 762 classes; the
   live path is `AddTooltip` + ENTER_FRAME), the now-8x duplicated AS3
   encode block with INCONSISTENT escaping (TooltipManager escapes
   `~` and `*`, the hand-written posters do not), three stacked silencers
   (1500 ms Flash + 1000 ms Python + 20/sec window) making a deliberate
   re-hover say nothing, `mA11yLastWidget` early-return, and the unverified
   PickersMain app-domain risk across the 7 sibling picker movies.
5. Log-noticed polish: WW notification panel re-announces repeatedly;
   aspiration tooltip reads "Label Name:. Description:" template junk.

## ROUND 2 (2026-08-03 ~03:50) — CONFIRMED WORKING in-game

Second log-driven round. Script + package both deployed and hash-verified.
Suites: 43 speech checks + 41 settings checks, all green.

- **Numpad 8 ROOT CAUSE FOUND (the real one).** The log showed
  `speech backend: nvda` while "NVDA is not running" — so speech came from
  the SAPI child, but `stop()` fired `nvdaController_cancelSpeech()` and
  returned unconditionally, silencing nothing. The stop key had never
  worked on a screen-reader-less machine; both earlier "fixes" were
  downstream of a no-op stop. `stop()` now checks each backend's result and
  falls through to the live one. Regression test fakes this exact setup
  (NVDA DLL loaded + not running + SAPI speaking). See the new HANDOFF
  bullet. ALSO: the still-speaking estimate now tracks queued speech
  (`_busy_until`).
- **Clock ROOT CAUSE FOUND.** Probes: `TCover-` fired ONLY over the speed /
  camera buttons, never the clock → that area has no hit surface because EA
  sets both text fields `mouseEnabled = false`. And `WXover` fired but
  posted nothing → `root["txtGameTime"]` was empty. Both fixed: fields are
  mouse-enabled in the patch, and the weather-container fallback walks the
  parent chain (`A11yFindClockOwner`). Probes are STILL IN (capped at 8):
  next log should show `TCover-...TextField` when hovering the clock and
  `WXover-clockfound` (not `WXover-noclock`). REMOVE THE PROBES once
  confirmed — they are in TimeControlsMain.as and WeatherAndSeasonContainer.as.
- **Tooltip read delay SHIPPED** (tester request: needs/skills/mood
  descriptions are "mostly useless info"). Row line reads at once, stock
  description deferred by `tooltip delay` (default **1.5 s**), cancelled on
  pointer move; read key still reads both. Tune live with
  `a11y.tooltipdelay <seconds|off>`. NOTE: the user's existing cfg predates
  the option, so the `tooltip delay` line only appears in the file after
  the next settings write — the default still applies meanwhile.
- Needs bar CONFIRMED FIXED in-game by tester (app-domain fix worked).
- Still open: the review backlog in the 2026-08-02 section below (dead
  `TooltipManager.ShowTooltip` hook, 8x duplicated AS3 encode block with
  inconsistent escaping, triple silencer stacking, `mA11yLastWidget`
  early-return, PickersMain app-domain risk in the 7 sibling picker
  movies), plus log-noticed polish: WW notification panel re-announces
  repeatedly, aspiration tooltip reads "Label Name:. Description:" junk.
- No release zip for round 2 yet — cut after in-game confirmation.

## 2026-08-03 STATUS (supersedes the item statuses below)

The 2026-08-02 build was live-tested with `a11y.log on` + `a11y.rawdiag on`.
The log settled everything; a second build went out 2026-08-03 ~02:30 and is
DEPLOYED (script + package, hash-verified after game close):

- **Skills row read: CONFIRMED FIXED in-game** (log shows `RAWDIAG[widget]`
  "Violin. 10" etc.). The per-channel pruning change works.
- **Needs: ROOT CAUSE FOUND — app-domain shadowing.** SimInfoTray defines a
  full duplicate of `CommodityContainer`; when it loads first, the
  unpatched copy wins and the motive rollover simply does not exist (this
  is why it "worked at one point": load order varies). FIX DEPLOYED:
  CommodityContainer patched into BOTH SimInfoTray and SimInfoMotivePanel.
  See the new app-domain bullet in HANDOFF — scan before patching any
  panel class (scan_class_defs.py pattern), and note the UNVERIFIED
  PickersMain risk in the 7 sibling picker movies.
- **"Keys need two presses": root cause = the numpad-8 stop-toggle firing a
  soundless stop in SILENCE.** FIX DEPLOYED: `repeat_last` estimates
  whether the last utterance is still playing (`_probably_still_speaking`,
  chars/sec heuristic); press during playback stops, press in silence
  reads. Suite covers it (38 checks green).
- **Time panel: STILL OPEN, now instrumented.** The TimeControlsMain
  MOUSE_OVER announcer compiled + registered correctly (verified in the
  shipped movie) yet never fired in-game (no `RAWDIAG[timewidget]` in the
  log). Two additions deployed: (1) capped probes posting to `a11y.mark` —
  look for `MARK: TCinit` (Initialize ran), `MARK: TCover-<class>` (hover
  reached the handler), `MARK: WXover` (weather-container fallback fired);
  (2) a fallback announcer on `WeatherAndSeasonContainer` (defined in both
  TimeControls and SimInfoTray, patched into both) that reads
  `root["txtGameTime"]` — its subtree provably receives mouse events (the
  forecast tooltip fired in the log). NEXT SESSION: read the log's MARK
  lines from the first post-03 test run; they decide the remaining fix.
  Remove the probes once resolved.
- Log polish backlog noticed 2026-08-03: WW notification panel group
  re-announces repeatedly; aspiration tooltip reads "Label Name:.
  Description:" template junk; widgetname fallback once spoke "text Field".
- No release zip cut for the 03 round yet — cut one after in-game
  confirmation (dist/ has 2026-08-01 and 2026-08-02 zips).

Older context below (2026-08-02 writeup); item 3's needs half and the
numpad-8 "verify" are superseded by the above.

---

## 0. State of the tree: CLEAN, BUILT, DEPLOYED

Sources, the deployed install in `Mods/tyjokr_ScreenNarrator/` (dev build:
logging still follows the cfg, which defaults off; the in-code fallback is
ON only if the settings module fails to import), and
`dist/tyjokr_ScreenNarrator_2026-08-02.zip` all contain the fixes below. The 2026-08-01 zip is preserved next to it; zips
are dated, so only same-day rebuilds overwrite (bump a `-2` suffix by hand
if that ever matters).

Deploy hashes verified 2026-08-02 (package + ts4script both match the
build outputs). Game was not running; no DEPLOY BLOCKED.

**Offline suites now live in `tools/`** (`test_speech_modes.py`,
`test_settings_cfg.py`) so they survive scratchpad cleanup. Run with
`py -3.7 tools\test_speech_modes.py [path-to-ts4script]` (defaults to the
deployed dev zip; they are 3.7-bytecode zips, so plain `python` will not
import them). Both suites pass against the deployed build (35 + 34 checks).
The beep is mocked; if a real beep sounds during a run, the mock is lost.

---

## 1. FIXED: Numpad 8 restarted narration instead of stopping (item 1)

Confirmed exactly as hypothesized: `speak(head)` inside `speak_progressive`
armed `_last_repeated` with the head alone while the capture became
head+body, so the stop-equality in `repeat_last` never held and the key
re-read the full text. `speak_progressive` now arms `_last_repeated = full`
whenever the head is being auto-spoken (hover mode). Offline suite covers
the exact shipped gap ("press during head playback stops") plus
second-press-re-reads and third-press-stops.

**In-game check:** hover the time panel, press Numpad 8 mid-read → speech
stops; press again → re-reads; press again → stops.

## 2. FIXED: global long-tooltip split reverted; two-stage read is now
time-panel only (item 2)

- The generic `_LONG_TOOLTIP_CHARS` branch is gone from `a11y_speak_enc`.
  Long tooltips everywhere else read in full again, immediately.
- Root cause of "the clock's own text is never announced": EA sets
  `txtGameTime.mouseEnabled = false` in `TimeControlsMain.Initialize`, so
  the clock text can never be a hover target — no generic path could ever
  read it. Fixed Flash-side: new patch class
  `flash/extra-classes/TimeControlsMain.as` (wired into `rebuild_all.ps1`
  under the TimeControls movie) posts a composed
  "day + time (+ Paused)" line on `a11y.timewidget_enc` when the pointer
  enters the panel anywhere outside the speed/camera buttons; entering a
  button resets the once-per-entry latch so returning to the clock re-reads.
- Python (`a11y_timewidget_enc` + arming in `a11y_speak_enc`): the panel
  line speaks at once as a widget; the NEXT tooltip within 4 s is taken to
  be the forecast pop-up and its WHOLE body is deferred 1.2 s
  (`speak_progressive(..., head_spoken=True)`), cancelled by any new
  utterance. Any other widget/widgetname announce disarms. Numpad 8 reads
  panel line + forecast together.

**In-game check (tester):** cross the pointer over the clock on the way to
the speed buttons → hear only "Sat. 2:35 AM"-style line, no forecast dump.
Rest on the clock → panel line, pause, then forecast. Hover a long skill or
moodlet tooltip elsewhere → reads in full with no two-stage delay. While
paused, the panel line should end with the Paused label.

## 3. FIXED (needs tester confirmation): skills/needs "title, then level"
regression (item 3)

Two independent causes were found and both are fixed; needs and skills did
fail through different paths, as suspected:

- **Skills (Flash):** the 2026-08-01 container-visibility pruning applied to
  ALL `A11yCollectText` calls, including hovered/focused row announcements,
  which fire the instant the pointer lands — paged/freshly-recycled rows can
  still report `visible=false` mid-layout and the whole row collection came
  back empty (and an empty widget collection posts widgetname/stop, which
  also KILLED whatever had just been said). The pruning is now
  **per-channel**: tooltips + Sim headline/hover tip keep it (phantom text
  stays fixed — `SimHeadline.as` announces via `a11y.widget_enc`, so the
  split is by call site, NOT by command name); row announcements pass
  pruneHidden=false. See the hard-won-facts bullet before touching this.
- **Needs (Python):** `CommodityContainer` posts its composed
  "Hunger. 80%" and a generic announce of the same row could follow with
  just the title; under burst thinning the newest-wins rule let the bare
  label EVICT the parked richer line, and outside the burst window it
  INTERRUPTED it mid-word. New `_adds_nothing` guards in the speech module
  drop a label-only repeat (all of its segments already in the just-spoken
  or parked widget line, 2.5 s window) in both places, and keep the richer
  text as the read-key capture. Additionally `a11y.stop`/`a11y.widgetname_enc`
  now use `speech.request_hush()` — no stop while a widget line is parked or
  younger than 0.8 s.

**In-game check (tester):** hover a needs bar → "Hunger. 80%" then the
description; hover a skill row → "Fishing. 4" (or similar) then the
tooltip; sweep quickly across several rows → the LAST row's title+level is
heard, not just a tooltip. Phantom text must stay gone from Sim hover tips
(fame/clubs words must NOT return).

**If anything still fails:** `a11y.log on` + `a11y.rawdiag on`, reproduce,
read `Mods/tyjokr_ScreenNarrator/tyjokr_ScreenNarrator.log`. RAWDIAG lines
are now channel-tagged (`RAWDIAG[widget]`, `RAWDIAG[tooltip]`,
`RAWDIAG[timewidget]`, `RAWDIAG[widgetname]`, `RAWDIAG[stop]`), so
widget-fired-empty vs never-fired vs Python-suppressed is readable straight
from the log.

---

## Build, deploy, test (reminders)

```
py -3.7 compile.py                    # dev build -> deployed to Mods
py -3.7 compile.py --release          # dist zip (log default off, ships cfg + README)
powershell -File flash\rebuild_all.ps1 -WorkDir <scratch>   # ~10 min, run in background
python flash\build_ui_package.py <same scratch>
python flash\deploy_package.py
```

- `<scratch>` must contain `gfx\ea_*.swf`. No archive is kept: re-extract
  from the live `Data/Client/UI.package` with the throwaway pattern in this
  session's `extract_ea_swfs.py` (dbpf_extract from voice-experiments;
  NOTE its `read_index` is lazy over the same file handle — `list()` it
  before calling `read_resource_bytes`, or extraction corrupts the walk).
- **Package deploy fails while the game is running** ("DEPLOY BLOCKED").
  Verify with a file hash after deploying.
- After a rebuild, verify the patch actually landed (ffdec -replace errors
  are swallowed by the ps1): re-export the movie's scripts and grep for the
  new code. 2026-08-02 verification greps: `timewidget_enc` in
  TimeControlsMain, `param4 && param3 > 0` + `"a11y.widget_enc",false` in
  TooltipManager.

## Still-pending in-game verification (older items, unchanged)

Picker scrolling through a long list (hold a nav key, expect no skips or
stalls), arrows in dialogs/pickers only, auto-focus staying off from a cold
boot, `a11y.reload` after a Notepad edit, the assigned double bed showing
EA's own tooltip, and the settings-file persistence pass (toggle, quit,
relaunch, `a11y.settings`).

## Settings UI for the reader (handoff from the Moodlet Panel session, 2026-09-14)

The Moodlet Panel session built an in-game options dialog with no Python
and wrote up everything it learned: `My Script Mods/MoodletPanel/
OPTIONS-DIALOG-NOTES.md` (plain-language chain), `MoodletPanel/flash/
patch_options.py` (working MPOptionsDialog class + hooks), EA reference
decompiles in `MoodletPanel/flash/reference/`, and the memory recipe
`ts4_ui_only_options_dialog.md`. Facts that matter here: local Flash
dialogs go through olympus.dialog.DialogManager with a LocalRequestData
(EA's own GraphicsTab does it); persistence without a script is
olympus.core.UISettings; EA controls are fetched by name through
LibraryUtils.GetClass; FFDec cannot add a class, but a file-private class
appended to an already-replaced class compiles; create text fields once and
reuse them, never per open.

Recommendation carried over for the reader: do NOT build a Flash settings
dialog. Values already live in Python and Python owns the keyboard, so the
primary surface should be a self-voicing settings menu (arrows move,
left/right change, Enter/Esc leave) that works everywhere the reader works,
with a Python picker dialog (already narrated by DialogMain + PickersMain)
as the visual fallback. If any dialog controls are ever shown to the reader,
give each an accessible name and announce the dialog with title + row count.

PENDING FROM THE USER: the list of settings to expose in that menu.
