> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# Screen Narrator: state of the work

Written 2026-07-29; split implemented 2026-08-01 (section 4). Read this first
in a new session, then `SHIPPING.md` for the install layout.

---

## 1. What this is

A screen-reader accessibility mod for The Sims 4. It narrates the UI (hover,
tooltips, dialogs, menus, panels), announces what the active Sim is doing,
gives plain objects spoken names, and adds keyboard focus navigation.

Nothing like it existed before; the community has asked EA for this for years.

### Where things live

| Path | What |
| --- | --- |
| `My Script Mods/ScreenNarrator/Scripts/` | Python sources (single ts4script; features gated by the settings file) |
| `My Script Mods/ScreenNarrator/flash/` | AS3 patch sources + build scripts |
| `My Script Mods/ScreenNarrator/flash/extra-classes/` | Per-screen patched EA classes |
| `My Script Mods/ScreenNarrator/tolk/` | Built Tolk.dll + client DLLs + licences |
| `Mods/tyjokr_ScreenNarrator/` | Live install (one ts4script, package, `speech/` DLLs, settings json) |
| `screen-reader-research/RESEARCH.md` | Original feasibility research + movie name map |

### Build and deploy

```
py -3.7 compile.py                                       # dev: 4 ts4scripts -> Mods (log ON)
py -3.7 compile.py --release                             # distribution zip -> dist\ (log OFF)
powershell -File flash\rebuild_all.ps1 -WorkDir <scratch> # patch all 21 movies
python flash\build_ui_package.py <scratch>                # -> UI package
python flash\deploy_package.py                            # package -> Mods subfolder
```

`<scratch>` must contain `gfx\ea_*.swf` (unpatched EA originals). After an EA
patch, re-extract those from the new `Data/Client/UI.package` first.

**The package deploy fails silently-ish if the game is running.** Always check
for the "DEPLOY BLOCKED" message; a stale package cost a full test cycle once.

---

## 2. Architecture (and why)

Two halves that must both be installed:

1. **`tyjokr_ScreenNarrator_UI.package`** — 22 EA UI movies with patched
   ActionScript. They observe the UI and report text. (Adding a movie means
   editing BOTH `flash/rebuild_all.ps1` and `flash/build_ui_package.py`:
   the first decides what gets patched, the second what ships.)
2. **`tyjokr_ScreenNarrator.ts4script`** — receives that text, formats it,
   speaks it, and drives keyboard input.

### Hard-won facts (do not re-derive)

- TS4's UI is **Scaleform GFx / ActionScript 3**, all movies in
  `Data/Client/UI.package`, resource type `0x62ECC59A`. Movie instance IDs are
  **FNV-1 64 of the lowercase movie name**. 220 of 258 movies identified in
  `screen-reader-research/ui-movie-names.tsv`.
- **All movies share one application domain**: the first-loaded definition of a
  class wins, so per-panel copies are ignored. Our hooks live in
  `olympus.core.TooltipManager`, and the winning copy comes from
  **ClassLibraryGamedata**. This is why one patch covers the whole UI.
  **The same rule BITES per-panel class patches (found 2026-08-03)**: EA
  compiles shared widget sources into MULTIPLE movies. `CommodityContainer`
  (the whole MotivePanel package) is defined in BOTH SimInfoMotivePanel and
  SimInfoTray; `WeatherAndSeasonContainer` in both TimeControls and
  SimInfoTray. When only one movie was patched, load order silently decided
  whether the patch ran at all — the needs "name + percent" announcer
  worked in some sessions and not others for exactly this reason. RULE:
  before patching any class into a movie, scan the live UI.package for
  every movie containing that class string (scratch tool pattern:
  scan_class_defs.py, 2026-08-03) and patch ALL of them, the way
  CatalogImageCellView is already patched into all 21. UNVERIFIED RISK:
  `PickersMain` strings appear in the 7 sibling picker movies
  (PickersColumnBased/Food/Grid/Multi/Outfit/Purchase/Sim), which are NOT
  in our patch set — if those are definitions rather than superclass
  references, picker focus/announce is load-order dependent today.
- **Flash -> Python** is `CommunicationManager.PostServerCommand(name, args)`,
  arriving as `@Command(..., CommandType.Live)`.
- **Python -> Flash** is `distributor.ops.SendUIMessage(name)` +
  `Distributor.instance().add_op_with_no_owner(op)`; Flash listens via
  `CommunicationManager.AddMessageListenerByName(name, fn, "<any label>")`.
  Listeners are keyed by message name; the widget label is only a grouping tag.
- **Flash never receives keyboard input.** Verified: stage KEY_DOWN listeners in
  both phases logged zero events across a whole session while the same hook
  delivers mouse fine. Keys are read in Python with ctypes
  `user32.GetAsyncKeyState`, foreground-gated by comparing
  `GetForegroundWindow`'s pid to `GetCurrentProcessId`.
- **The main menu cannot be narrated.** No console commands exist pre-zone (the
  cheat console itself cannot open there), and both alternative transports
  failed: a loopback HTTP request from Flash (our Python listener was up and
  received nothing) and `SharedObject` (no file ever written). Menu narration
  needs engine-level work against the client. Keyboard nav is equally dead
  there, since `SendUIMessage` also needs a running zone.
- **EA rejects synthetic clicks** unless the event is
  `scaleform.gfx.MouseEventEx` with `buttonIdx` set (`InputUtils.IsLeftMouseButton`
  casts to it). Never dispatch `PushButtonEvent` straight at grid cells — it
  crashes `GUIPickerBase.OnListItemClick` (#1009).
- **Currency/icon glyphs are repurposed ORDINARY Unicode chars styled by the
  game font**, not images and mostly not PUA: `§` simoleons, `≠` (U+2260)
  galactic credits, `◊` satisfaction, `▰`/`▬`/`▱` fame/hydration/money
  variants, `◴`/`◵` likes/dislikes. Found by RefPack-decoding every
  Strings_ENG_US.package (219 of them, incl. per-pack) and censusing symbol
  chars — scratchpad tool `stbl_glyph_hunt.py` pattern; RefPack: `50 FB` +
  3-byte BE size, QFS commands. Eco Bits/Pieces glyphs never appear
  literally in STBLs (token-only: `{1.RecyclingBits}`) — capture via the
  hidden `a11y.rawdiag on` + `a11y.log on`, which logs pre-clean payloads
  with unicode escapes.
- **Hidden panels are still fully built**: fame reputation ("Scandals",
  "Latest Opinion"), clubs, empty stat rows sit in the tooltip as containers
  with `visible = false` while the TextFields INSIDE them stay
  `visible = true`. `A11yCollectText` therefore prunes any container with
  `visible == false` below depth 0 (the root is exempt: it can be mid
  show-transition when we announce). Alpha is still never tested — that is
  the rule that silenced all tooltips twice. **The pruning is per-channel
  (2026-08-02)**: composed tooltips and the Sim headline/hover tip keep it
  (that is where the phantom text lived), but hovered/focused ROW
  announcements (`A11yOnMouseOver`/`A11yTabMove`/`A11yFocusItem`) pass
  pruneHidden=false — rows announce the instant the pointer lands, when
  legit sub-containers (paged/freshly recycled list rows) can still report
  visible=false, and pruning them silenced the skill rows' "title, then
  level" read. Do NOT re-unify the two channels in either direction.
- **The two-stage read is time-panel-only** (tester call, 2026-08-02; a
  global `_LONG_TOOLTIP_CHARS` threshold shipped 2026-08-01 and was
  reverted). The clock text (`TimeControlsMain.txtGameTime`) is
  `mouseEnabled=false`, so generic hover narration can NEVER see it — the
  patched `TimeControlsMain` posts its own composed line (day + time +
  "Paused" when shown) as `a11y.timewidget_enc` when the pointer enters the
  panel outside its buttons. The narrator speaks that at once and treats the
  next tooltip within 4 s as the forecast pop-up: whole body deferred 1.2 s
  via `speech.speak_progressive(head, body, head_spoken=True)`, cancelled by
  any new utterance. Any other widget announce disarms the deferral.
- **A claimed backend is NOT the speaking backend** (root-caused 2026-08-03).
  The NVDA client DLL always loads if present, so `_backend_name` becomes
  `nvda` even when NVDA is not running, and every utterance silently falls
  through to the SAPI child. `_speak_now` handled that (it checks
  `nvdaController_speakText`'s RETURN CODE — the controller reports failure
  by code, never by exception), but `stop()` called
  `nvdaController_cancelSpeech()` and returned unconditionally, silencing
  nothing while SAPI kept talking. Effect: the read/stop key had NEVER
  worked on a machine without a screen reader — press one did nothing
  audible, press two restarted the text. Any backend call in stop() must
  check its result and fall through, exactly like the speak path.
- **There is no is-speaking query on any backend**, so the read key's
  stop-vs-reread decision uses an estimated playback window
  (`_busy_until`, ~15 chars/sec). It must be advanced from the END of the
  utterance ahead when speech is QUEUED rather than interrupting (a tooltip
  parked behind a row label), or the estimate expires mid-sentence.
- **Data rows read in two stages** (2026-08-03, tester request): a row that
  announces its own name and value (needs, skills, mood, the time panel)
  speaks at once, and the stock description that follows within
  `_ROW_TIP_WINDOW` is held back by the `tooltip delay` setting (default
  1.5 s, `a11y.tooltipdelay <seconds|off>`), cancelled by any new utterance.
  The trigger is "a tooltip following a real `a11y.widget_enc` row line",
  NOT tooltip length: icon-only controls announce through
  `a11y.widgetname_enc`, which CLEARS the pending row head so their
  tooltips — the only text they have — stay immediate. A length-threshold
  version shipped 2026-08-01 and was rejected by the tester.
- **The time panel has no hit surface of its own** (probe-confirmed
  2026-08-03): EA sets `txtGameTime.mouseEnabled = false` and
  `txtTimeSpeedName.mouseEnabled = false`, so MOUSE_OVER on
  TimeControlsMain only ever fires over the speed/camera BUTTONS and the
  clock can never be hovered. The patch re-enables mouse on both fields
  (they are not selectable and sit clear of the buttons; events still
  bubble). A second announcer on `WeatherAndSeasonContainer` covers the
  weather cluster and finds the clock by WALKING THE PARENT CHAIN for
  `txtGameTime` — `root` does not work, because that class is compiled
  into SimInfoTray as well and is not always under the TimeControls
  document class.
- **Panels routinely make their own text unhoverable.** Three separate
  cases now: the motive bars (needs), the clock, and the mood all had to
  compose and post their own line because EA disables mouse input on the
  very text a screen reader wants. `MoodContainer` (SimHub movie, the ONLY
  definition of it) sets `mcMoodTextContainer.mouseEnabled = false` AND
  `mouseChildren = false`, leaving only the wide `mcMoodBkg` backdrop
  hoverable — so hovering the mood read nothing but its description
  tooltip. The patch posts `MoodStaticData.GetMoodName(intensity)` (the
  exact on-screen localized string; intensity is already folded into the
  name) on `a11y.widget_enc`, which also makes the description a deferred
  row tooltip. WHEN A PANEL READS ONLY ITS TOOLTIP, SUSPECT
  `mouseEnabled/mouseChildren = false` FIRST — grep the class before
  theorizing about the collector.
- **Widget-channel dedupe guards (2026-08-02)**: a bare label whose segments
  are all contained in the widget line spoken (or parked) just before it is
  information-free and is dropped (`_adds_nothing` in the speech module) —
  a generic row announce trailing `CommodityContainer`'s composed
  "Hunger. 80%" used to interrupt or evict the richer line under
  newest-wins. Same idea for empty controls: `a11y.stop`/`a11y.widgetname_enc`
  now go through `speech.request_hush()`, which never cuts a widget line
  younger than 0.8 s (entering a row crosses its icon-only children).
- **EA hides text-measuring "ruler" strings** in live panels
  (`1234567890...`, `wwwww...`). Filter them by pattern in Python. **Do not**
  filter by transparency: tooltips fade in from alpha 0, and doing so silently
  killed all tooltip narration twice.
- Lists are **virtualized AND recycled**: offscreen rows do not exist, and
  `RecyclingGridLayout` rebinds the same DisplayObjects to different data as
  you scroll, so identity-diffing rows across a scroll NEVER works (that was
  the old skip/stall bug). The right way (2026-08-01): every ScrollList's
  `mGridLayout` implements `IGridLayout` with `GetGridIndexOfCell(cell)`,
  `GetNumItems()`, `GetPositionOfIndex(i)` (content-pixel offset, same units
  as the slider) and `GetViewAtIndex(i)` (renderer currently bound to i, or
  null). Navigate by INDEX: compute target, `SetCurrentValue(pos,false,true,
  true)` (absolute, no animation), wait frames until `GetViewAtIndex(target)`
  is on stage, focus it. TRAP: `GetGridIndexOfCell` on a non-cell returns
  `map[-1]` = undefined coerced to 0 (a valid index!) — always round-trip
  verify `GetViewAtIndex(idx) == candidate`. Decompile olympus with
  `java -jar C:\Tools\ffdec\ffdec.jar -export script <out>
  gfx\ea_ClassLibraryOlympus.swf` to re-derive.
- **The focus ring outlives its target unless watched**: the ring sprite is
  parented to the persistent tooltips layer, so when activation closes the
  modal that contained the focused control, the control leaves the stage and
  the ring floats over nothing (fixed 2026-08-01). Focus targets get a weak
  `Event.REMOVED_FROM_STAGE` listener (`A11yWatchFocused`): on removal, clear
  focus + ring, but keep `mA11yScope` when the scope root itself is still on
  stage (multi-page pickers swap cells without closing).
- **Arrow keys** are camera keys, so Python always sends
  `A11yArrowUp/Down/Left/Right` and the FLASH side gates them: acted on only
  while the scope's class name contains "Dialog" or "Picker" (the ONLY modals
  that lock the camera — pie menus do NOT, so arrows there would pan the
  camera while navigating) and stage focus is not a TextField.
- `obj.hover_tip` is a **Python property**; setting it plus
  `add_ui_metadata('recipe_name', ...)` + `update_ui_metadata()` makes the
  client send hover tips for objects that had none — but ONLY for objects
  without a tooltip component (see next).
- **77% of object tunings carry a TooltipComponent**, and it owns the tip
  lifecycle: it rebuilds lazily on the client's first-hover request
  (`ui.create_hovertip` -> `on_hovertip_requested`) and force-DISABLES the
  hover tip when it finishes with no handles of its own.
  `GameObject.has_ui_metadata_handles` is `@ored_forward_to_components`, so
  directly-written metadata is invisible to that check: a direct stamp on a
  component object dies on first hover (and duplicates recipe_name on rich
  objects). The ONLY safe way in is EA's external-field channel,
  `obj.update_tooltip_field(TooltipFields.recipe_name, name,
  should_update=True)` — merged during rebuild only where the component made
  no field of its own, so rich data always wins. AND never distribute a
  hover_tip style on a component object before its first-hover handshake:
  the engine only sends `ui.create_hovertip` for objects it believes have no
  tooltip yet, so a pre-pushed style suppresses the rebuild forever and kills
  EA's own tips (broke assigned double beds 2026-08-01). Apply the name-only
  style AFTER each rebuild via a wrap on
  `TooltipComponent.update_object_tooltip` (only when the rebuild left
  handles but no style). `a11y.objdiag <tuning-name-substring>` dumps live
  tooltip state for debugging this.
- **Every object has super affordances** — debug_Reset, cheat_set_as_head,
  simRay, fire_ReplaceBurntObject are tuned onto virtually everything, so
  "has interactions" must filter: not debug/cheat, visible,
  allow_user_directed, minus the frozen 45-id exclusion set of situational
  universals (ghost powers, fame perks, burnt/scratched replacement, simRay).
  Census tool: `tools/affordance_census.py` (rerun after major EA patches).

---

## 3. Current state

### Working

- Hover narration across the whole UI: tooltips, panels, buttons, list rows,
  catalog thumbnails (name, price, gameplay features, description), needs bars
  (name + percent), moodlets, traits, skills, careers, calendar entries.
- Reading order fixed up in Python: visual-order sort, label/value pairing,
  duplicate and ruler-string suppression, cross-utterance dedupe.
- Dialogs and pie menus announce on open; notifications announce on arrival.
- Active Sim narration (interactions announced as they start).
- World hover: Sims, gardening, crafted/owned objects, plus plain furniture via
  the `hover_tip` stamping.
- Keyboard navigation: Numpad 6/4 or backslash/minus to move, Numpad 5 or
  Enter to activate, Numpad `.` or either slash to clear. Default alternates
  must not appear on carls-sims-4-guide.com/controls.php (keys are read
  without being consumed; backtick was the prev alternate until 2026-08-01
  and silently toggled Pause, which is `~` on that list). Enter's collision
  with Find Active Sim is deliberate and accepted. Focus draws a ring, announces, and fires a
  real hover so tooltips read. Focus moves into pie menus, dialogs and pickers
  and stays scoped there; clicking clears focus unless a modal owns it.
- Speech: Tolk (JAWS, NVDA, Window-Eyes, ZoomText, SuperNova, System Access) ->
  NVDA client -> System Access -> Windows SAPI. Braille via Tolk with four
  modes (`a11y.braille concise|full|only|off`).
- Localised mod vocabulary (17 languages) in `tyjokr_a11y_lang.py`; game text
  arrives already localised.

### Known open items

1. **Picker scrolling rewritten 2026-08-01 (index-based, see hard-won facts)
   — needs in-game verification.** Legacy pixel-step path retained as
   fallback for non-grid scrollables. Circular wrap now covers the whole
   data set, not just visible rows. Arrow keys navigate inside modals.
2. **Main menu silent** — blocked as described above; engine-level project.
3. **Settings-file build (2026-08-01, supersedes the split) needs an in-game
   pass**: options persist across sessions (toggle something, quit, relaunch,
   `a11y.settings` should read the stored value back); keybind rebinds
   persist; assigned double bed shows EA's tip again after the rebuild-hook
   fix; plain rug/curtain still un-named; `a11y.objectnames redo` works.
   (The four-script split itself was tested working in-game before being
   superseded, and the earlier ObjectNames rework was verified except the
   assigned-double-bed fix, which landed after.)
4. Translations are first-pass, not native-reviewed.
5. macOS unsupported (speech + input are Windows-only).

### Commands

`a11y.test`, `a11y.status`, `a11y.settings`, `a11y.simactions on|off`,
`a11y.speechmode hover|manual|beeps|off` (NVDA-style, renamed 2026-08-01:
hover=speak-on-point, manual=on-demand; ALL modes persist incl. off; legacy
talk/ondemand accepted as aliases; cycled by Numpad 9/Insert; Numpad 8/equals
= read current/repeat; explicit command feedback always talks, braille-only
mode is exempt from suppression),
`a11y.autofocus on|off` (gates the Flash-side A11yTabMove(1) at scope entry
via A11yAutoFocusOn/Off messages; Flash default mirrors the cfg default
(OFF), and state is pushed at every ZONE LOAD, not just on a11y.mark — the
mark can fire at the main menu where the Flash-to-Python channel is dead,
which once left the stale Flash default active),
`a11y.voice rate|volume|name|list|reset` (SAPI fallback only; screen readers
own their voice settings; Tolk has no rate/volume API by design),
`a11y.braille`, `a11y.keys on|off` (keys are FIXED; a11y.keybind removed
2026-08-01 as too confusing), `a11y.reload`,
`a11y.objectnames on|off|redo`, `a11y.log on|off`, `a11y.objdiag <name>`,
plus internal ones Flash posts to
(`a11y.speak_enc`, `a11y.widget_enc`, `a11y.widgetname_enc`,
`a11y.timewidget_enc`, `a11y.event_enc`, `a11y.simaction_enc`,
`a11y.dialog_enc`, `a11y.menuopen`, `a11y.stop`, `a11y.mark`). Debug
instrumentation (tipdiag/keydiag/menuprobe/`RAW:` lines/loopback bridge) was
stripped 2026-08-01; the hidden `a11y.rawdiag` remains and its lines are
channel-tagged (`RAWDIAG[tooltip|widget|timewidget|dialog|event|simaction]`,
plus `RAWDIAG[widgetname]`/`RAWDIAG[stop]`) since 2026-08-02.

---

## 4. The split (implemented, tested, then SUPERSEDED 2026-08-01)

The four-ts4script split below was implemented, tested working in-game, and
then replaced the same day by a **settings file**
(`tyjokr_ScreenNarrator.cfg`, module `tyjokr_a11y_settings.py`; started as
JSON, switched same day to a commented Notepad-friendly INI with friendly key
names, MCCC-style; legacy JSON auto-migrates; `a11y.reload` applies
hand-edits live; the file is fully regenerated on every write from
`_TEMPLATE` + `_FILE_MAP`, so add new options there too):
one ts4script, features toggled by persistent in-game commands instead of
file deletion. This scales to arbitrarily many options (braille mode,
keybinds and logging persist now too) and removed the module-collision and
load-order machinery. The key insight that survives: all optional behavior is
driven from Python, the Flash package never needs splitting, and every
command handler must always exist in the shipped script (feature flags, not
missing handlers). Adding an option: default in `tyjokr_a11y_settings.DEFAULTS`,
`settings.get()` at the site that applies it, `settings.set()` in the command
that flips it, and a line in `a11y.settings`'s readout. compile.py removes
the retired `_SimActions`/`_Keyboard`/`_ObjectNames` ts4scripts on deploy;
release zips ship one script.

Historical plan follows, kept for the rationale. Implementation notes beyond
the plan:

- `compile.py` builds one ts4script per `Scripts/` subfolder (core keeps the
  old monolithic name, so deploys overwrite it).
- Core's `a11y.simaction_enc` handler is flag-gated; presence of
  `tyjokr_a11y_simactions` IS the switch (it sets the flag on import, and core
  lazily imports it on the first event as the load-order fallback).
- The bundled `ctypes` package ships ONLY in core; the Keyboard script
  resolves it lazily in the poll thread (waits up to 60 s, then logs and
  exits quietly if core is absent).
- `GELauncherMain.as` was deleted outright: its only content was the dead
  main-menu probes. The GameEntryLauncher movie is still patched (its
  TooltipManager copy must never win the app domain unhooked).
- `flash/build_ui_package.py` was stale at 18 movies while the shipped package
  had 21 (Dialog/PieMenu/Pickers missing); fixed, and it now takes the
  rebuild WorkDir as an argument. A second stale copy in `extra-classes/`
  was deleted.
- In-game testing of the split (step 8's matrix) is still PENDING.

**Goal:** let users delete parts they do not want.

**Key insight:** the UI package cannot be split by feature — hover narration and
keyboard focus live in the same patched class (`TooltipManager`), because focus
and hover are the same machinery. Splitting it would mean shipping incompatible
variants of one file.

**This does not matter**, because every optional feature is *driven* from
Python. The Flash code is inert without its Python counterpart. So: **one
package (always required) + several ts4scripts.**

### Target layout

```
Mods/tyjokr_ScreenNarrator/
  tyjokr_ScreenNarrator_UI.package        (required)
  tyjokr_ScreenNarrator.ts4script          (required: core)
  tyjokr_ScreenNarrator_SimActions.ts4script   (optional)
  tyjokr_ScreenNarrator_Keyboard.ts4script     (optional)
  tyjokr_ScreenNarrator_ObjectNames.ts4script  (optional)
  speech/   Tolk.dll, nvdaControllerClient64.dll, SAAPI64.dll, licences
```

| Script | Modules | Deleting it |
| --- | --- | --- |
| Core | `tyjokr_a11y_speech`, `_lang`, `_narrator` | mod does nothing |
| SimActions | `tyjokr_a11y_simactions` | no "what my Sim is doing" |
| Keyboard | `tyjokr_a11y_keys` | mouse only |
| ObjectNames | `tyjokr_a11y_objectnames` | furniture reverts to vanilla |

### Implementation steps

1. **Restructure sources** into `Scripts/core/`, `Scripts/simactions/`,
   `Scripts/keyboard/`, `Scripts/objectnames/` (one folder per output).
2. **Rework `compile.py`** to build one ts4script per folder, all deploying to
   the same Mods subfolder. Keep the `py -3.7` guard.
3. **Feature flags, not missing handlers.** Keep *all* command handlers in core
   so an absent optional script can never cause an unknown-command error.
   Optional scripts switch a feature on:
   - core: `sim_actions_enabled = False`; `a11y.event_enc` checks it before
     speaking interaction announcements.
   - `tyjokr_a11y_simactions` simply sets it True on import.
   Same pattern for object names (core keeps nothing; the module owns the zone
   hook, so absence is already safe) and keyboard (the key thread lives in the
   optional module; absence means no messages are ever sent).
4. **Separate the Sim-action channel from notifications.** Both currently use
   `a11y.event_enc`. Patch `InteractionButton.as` to post `a11y.simaction_enc`
   instead, add that command in core gated by the flag, and leave notifications
   on `a11y.event_enc`. This is the only Flash change the split needs.
5. **Lazy, defensive imports** in optional scripts: import
   `tyjokr_a11y_speech` inside functions, or wrap module-level imports in
   `try/except` and retry, so load order across ts4scripts cannot break them.
   (Names sort Core < Keyboard < ObjectNames < SimActions, which helps, but do
   not rely on it.)
6. **Strip debug** while restructuring: remove `tyjokr_a11y_bridge.py`,
   `a11y.tipdiag`, `a11y.keydiag`, `a11y.menuprobe`, the `RAW:` log line, and
   the matching Flash probes in `HoverTip.as` and `GELauncherMain.as`. Consider
   a `--release` flag on `compile.py` like OpenApartments has.
7. **Update `SHIPPING.md`** with the new file table and what each piece does.
8. **Test matrix**: core alone; core+keyboard; core+objectnames;
   core+simactions; all four. Confirm no errors with Better Exceptions
   installed when optional pieces are absent.

### Watch out for

- **Module name collisions across ts4scripts**: only the first-loaded copy of a
  given module name runs. Keep every module name unique (all are `tyjokr_a11y_*`).
- Do not put ts4scripts more than one folder deep — they will not load.
- Rebuild the package only if step 4's Flash change is made; otherwise the
  existing package is unchanged.
