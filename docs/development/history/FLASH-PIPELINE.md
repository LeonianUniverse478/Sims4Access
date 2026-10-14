> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# Flash pipeline: how the UI package is built (FFDec, gate, packages)

Companion to `HANDOFF-SCANNER-INTEGRATION.md`. Everything a fresh chat
needs to patch, rebuild, verify and ship the Screen Reader's ActionScript
side. Facts marked (verified) were proven in-game or by byte comparison;
the rest is the working method as of 2026-09-15.

## V9.2 live-test corrections (2026-09-15)

Current source/deployment includes linked Needs-control mapping, filter
deduplication/dismissal, popup return focus, and physical Escape ownership.
Same 24+6 movies; tag `keyboard-v9_2-final`, separate `gate-compat-v9_2.log`,
then `tools/verify_v9_2_artifacts.py` and `tools/deploy_v9_2.ps1`.
133 offline checks, 61 main and 19 compatibility comparisons passed. Cfg
preserved; V9.1 rollback in `build/deployed-before-v9_2`. See
TEST-V9-LIVE-2026-09-15.md for actual runtime results and unresolved cases.

## Historical V9.1 live-test correction (2026-09-15)

Current source/deployment fixes the null previous-scope check that prevented
panel focus entry. Same 24+6 movies; tag `keyboard-v9_1-final`, separate
`gate-compat-v9_1.log`, then `tools/verify_v9_1_artifacts.py` and
`tools/deploy_v9_1.ps1`. All gates passed; cfg preserved; V9 is backed up in
`build/deployed-before-v9_1`. See TEST-V9-LIVE-2026-09-15.md for runtime results.

## Historical V9 feedback fix build (2026-09-15)

**V9 deployed:** same 24+6 scope; tag `keyboard-v9-final`, separate
`gate-compat-v9.log`, then `tools/verify_v9_artifacts.py` and
`tools/deploy_v9.ps1`. V8 source/artifacts are saved in `build/source-before-v9`;
deployment additionally preserves live originals/cfg in `build/deployed-before-v9`.
See TEST-V9.md / KEYBOARD-V9.md. Do not overlap pipelines.

130 offline checks, 61 main comparisons and 19 compatibility comparisons
passed. `build/v9-verification.json` verifies source/artifact agreement and
`build/v9-deployment.json` records the three installed hashes; cfg preserved.
The verifier and deployer reject a compatibility gate older than its package.

## Historical V8 feedback fix build (2026-09-15)

V8 keeps the same 24+6 shipping scope. Stage with
`compile.build('build')`, then run `flash/chain.ps1 -Tag keyboard-v8-final`,
the separate compatibility gate, `tools/verify_v8_artifacts.py`, and
`tools/deploy_v8.ps1`. The deployment script requires both passed gates and
an unchanged verification manifest, checks the game is closed, preserves
the user's cfg and backs up the previous live build in `build/deployed-before-v8`.
See TEST-V8.md and KEYBOARD-V8.md. Incoming calls/texts remain untested.

V8 was deployed after all 123 offline checks, 61 main targeted comparisons,
19 compatibility comparisons and final source/artifact verification passed.
All three installed hashes match the staged files and the cfg was preserved.

Evidence: `flash/chain-keyboard-v8-final.log`, `flash/gate-compat-v8.log`,
`build/v8-verification.json`, `build/v8-deployment.json`.
Source and V7 artifact backups are in `build/source-before-v8/`.

## Historical V7 test build (2026-09-15)

V7 is deployed with the same 24+6 resource scope. Current evidence:
`flash/chain-keyboard-v7-final.log` (61 main targeted comparisons),
`flash/gate-compat-v7.log` (19 compatibility comparisons),
`build/v7-verification.json` and `build/v7-deployment.json`.
Use `tools/verify_v7_artifacts.py` and `tools/deploy_v7.ps1` for this source
revision. Stage Python with `compile.build('build')`; preserve the cfg and
check the game is closed. V6 rollback is in `build/deployed-before-v7`.

The optional startup probe has its own source, build directory, two-movie
export gate and verification manifest. Its UI package retains 24 resources
and differs from V7 only in ClassLibraryGamedata. It is not deployed. See
STARTUP-PROBE-V7.md. Never overlap its compilation with the main pipeline.

## Historical V6 continuation: 23 original movies plus AgeUpPanel (2026-09-15)

**Shipping scope is 24 movies**, enforced by `build/v6-shipping-movies.json`
and the artifact verifier. The ABC audit found 135 TooltipManager definitions,
but this does not establish missing coverage. Prior in-game marks prove the
ClassLibraryGamedata copy wins, including in CAS (HANDOFF.md and
TODO-NEXT-SESSION.md's CAS investigation). An initial 135-movie expansion was
stopped before deployment after the user's correction. Do not repeat it.

Keep `build/ui-class-audit-v6.json` and `tools/audit_ui_classes.py` as an
inventory. Distinguish references, definitions and actual runtime winners.
AgeUpPanel (`0xEB4EA2715398D221`) is added **for AgeUpPanelMain only**; leave its
TooltipManager and other shared classes untouched. EngagementLibrary and
all CAS movies stay excluded. The per-panel all-definers rule still applies
to lazily loaded classes such as CommodityContainer.

`rebuild_all.ps1` and `build_uicheats_compat.ps1` now use a sequential batch
compiler when `build/ReplaceScriptsBatch.class` exists, falling back to the
original CLI otherwise. It calls the same FFDec replacement API with a fresh
SWF for every movie. AgeUpPanel with two replacements and ClassLibraryGamedata
were byte-identical to separate CLI builds; repeating AgeUpPanel after another
movie also produced identical bytes. Evidence: `build/replace-batch-sequence.*`,
`build/probe-v6-cli.swf`, `build/sequence-gamedata-cli.swf`.

The gates similarly use `ExportPcodeBatch` when compiled. Both its sequential
and FFDec-parallel modes produced 1,077 ClassLibraryGamedata pcode files that
matched the CLI export byte for byte. The helper requires one nonempty output
per script pack. These helpers avoid repeated JVM startup; existing opcode
comparisons remain.
Compile helpers with Java 21 and `-cp C:\Tools\ffdec\ffdec.jar -d build`.

V6 pipeline: `chain.ps1 -Tag navigation-v6-final`, then
`py -3.7 flash/gate_compat_pcode.py flash/work-compat` (save output to
`flash/gate-compat-v6.log`), then `py -3.7 tools/verify_v6_artifacts.py`.
The verifier additionally requires identical non-code movie tags, identical
class-definition sets, current generated templates, source-matching Python
3.7 code objects and byte-identical package resources. Deployment uses
`tools/deploy_v6.ps1` only after both gates pass and the game is closed.

Main chain logs can be locked against readers while a PowerShell Add-Content
pipeline is active. Count fresh `patched_*.swf` outputs or pcode directories
for progress; read the final log once unlocked. Do not start another pipeline.
The v5 evidence below is historical. V6 build/deploy status is in the handoff.

## 1. Tools

| Tool | Where | Notes |
|---|---|---|
| Java 21 | `C:\Tools\jdk21\jdk-21.0.11+10\bin\java.exe` | Every script hardcodes this path |
| FFDec (JPEXS Free Flash Decompiler) 26.2 | `C:\Tools\ffdec\ffdec.jar` (CLI), `ffdec.exe` (GUI) | Version from `C:\Tools\ffdec\CHANGELOG.md`; the zip is `C:\Tools\ffdec_26.2.1.zip` |
| Python 3.7 | `py -3.7` | Runs script builds, gates, package builders and artifact verification |
| DBPF reader | `voice-experiments/dbpf_extract.py` | `read_index(f)` is a LAZY generator and `read_resource_bytes` seeks: always `list(read_index(f))` first or the walk dies after the first hit |
| Sims 4 Studio | not used for movies | Its GFX extraction is byte-perfect but its file names are garbage for GFX resources; S4S is fine for looking at tuning |

FFDec needs a writable configuration folder even on the command line;
`chain.ps1` points `$env:APPDATA` at `build\ffdec-appdata` so the desktop
app profile is never touched.

## 2. What you are patching

- TS4's UI is Scaleform GFx, ActionScript 3, EA's "Olympus" framework. All
  258 movies live in `Data\Client\UI.package`, resource type `0x62ECC59A`,
  magic bytes `GFX` (uncompressed). Instance id = FNV-1 64 (not 1a, no high
  bit) of the lowercase movie name without extension. 220 of the 258 are
  named in `screen-reader-research/ui-movie-names.tsv`
  (`screen-reader-research/RESEARCH.md` is the original feasibility study;
  `identify_movies.py`, `gfx_inspect.py`, `lib_grep.py` there are the
  scanning tools).
- All movies load into ONE application domain and the FIRST loaded
  definition of a class wins; later copies are ignored (verified). The live
  `olympus.core.TooltipManager` comes from `ClassLibraryGamedata` (proved
  with an `a11y.mark` line; the boot log still prints which movie's copy
  is live). Consequences:
  - A class patched into one movie may never run if another movie defines
    it too (`CommodityContainer` lives in SimInfoMotivePanel AND
    SimInfoTray; the needs announcer was load-order roulette until both
    were patched). Before patching any class, scan `UI.package` for every
    movie defining the per-panel class. An ASCII substring scan only finds
    candidates, including references. `tools/audit_ui_classes.py` confirms
    definitions. For TooltipManager, use the proven Gamedata runtime winner
    and the established shipping set; do not expand to every framework copy.
  - Never add members to only one copy of a lazily loaded per-panel class;
    another copy can win and omit them. Patch those definers consistently.
    This does not justify adding overrides for unused framework copies.
  - The three GameEntry* movies ship patched only so their TooltipManager
    copies can never win unhooked.
- A static reference to a class the host movie does not contain is
  resolved when the AVM VERIFIES the method, before any try/catch runs:
  an uncatchable native crash (the CAS lesson). Use
  `getDefinitionByName("pkg.Class")` inside try/catch, or duck typing
  (`obj["Method"] is Function`). `LocKey` is absent from many patched
  movies, so `A11yResolveLoc` fetches it by name.
- Keys never reach Flash on PC (verified: zero KEY_DOWN events all
  session). Keyboard work is Python; Flash only receives messages.
- Flash to Python: `CommunicationManager.PostServerCommand("a11y.xxx",
  "<text>")`, arriving as `CommandType.Live` commands. Text is
  `encodeURIComponent`-encoded and decoded by
  `tyjokr_a11y_narrator._decode_percent`. The tooltip path rate-limits
  itself (200 ms minimum spacing, 900-character cap) because a flood of
  posts froze the game once.
- Python to Flash: `distributor.ops.SendUIMessage(name)` +
  `Distributor.instance().add_op_with_no_owner(op)`, simulation thread
  only, zone required. The NAME is the whole payload. Flash listens with
  `CommunicationManager.AddMessageListenerByName(name, fn, "<label>")`
  (keyed by name; the label is cosmetic). Natively the client calls the
  ExternalInterface callback `"SendMessage"`, which EA sets once in the
  CommunicationManager constructor to `instance.SendUIMessage`; our
  TooltipManager re-registers it with `A11yOnGameMessage`, handles names
  starting `A11y|` locally (`A11yHandleEncoded`: `loc`, `pick`, and the
  caption `cap` being added now) and forwards everything else. `A11yHook`
  is sent at every zone load to re-assert the callback.
- Synthetic clicks must be `scaleform.gfx.MouseEventEx` with `buttonIdx`
  set (`InputUtils.IsLeftMouseButton` casts to it); never dispatch
  `PushButtonEvent` at grid cells (crashes `GUIPickerBase`).
- Fields captured at `AddTooltip` time are half laid out; defer collection
  one `ENTER_FRAME`.
- Fonts in code: `"$TextFont"`, `"$HeadlineFont"`, `"$SubtitleFont"`, with
  `embedFonts = true`; EA's dialog blue is `0x0949AB`. Create TextFields
  ONCE and reuse them (per-open TextFields crashed a modder's movies at
  teardown; the Moodlet Panel keeps a single reused instance).
- FFDec CANNOT add a class to a SWF (26.2.1: `-importScript` ignores new
  files, `-replace` refuses unknown names). Workaround: a file-private
  helper class appended after the package block of a class you already
  replace; it compiles, the script count is unchanged, the name never
  enters the app domain, and it can only reach the host's public members.
- Flash `SharedObject` is a stub in TS4; persistence without Python is
  `olympus.core.UISettings` (see the memory note
  `ts4_ui_only_options_dialog.md` and `My Script Mods/MoodletPanel/
  OPTIONS-DIALOG-NOTES.md`, which also has EA reference decompiles under
  `MoodletPanel/flash/reference/`).

## 3. Tree layout (integration clone)

```
flash/
  TooltipManager_patched.as     the template: full TooltipManager source with
                                our members; the literal A11YLIBNAME is
                                replaced by the movie name per build
  extra-classes/*.as            one file per patched EA class (full class
                                source, exported with ffdec then edited)
  rebuild_all.ps1               patches 23 original movies plus AgeUpPanel
  gate_pcode.py                 bytecode fidelity gate
  build_ui_package.py           writes the UI .package (MOVIES = what ships)
  build_uicheats_compat.ps1     patches UI Cheats' movies (6)
  build_compat_package.py       writes the compat .package
  extract_ea_movies.py          re-extracts ea_*.swf after an EA patch
  chain.ps1                     rebuild -> gate -> package -> compat, logged
  deploy_package.py             DO NOT USE HERE (see 5.5)
  uicheats-base/uic_*.swf       UI Cheats 1.59.1 movies (SOURCE.txt)
  work-1.127.41/gfx/ea_*.swf    EA originals for 1.127.41 (permanent, never
                                in a temp dir)
  work-1.127.41/gfx/patched_*.swf   outputs of rebuild_all
  work-1.127.41/gfx/ttm_*.as    per-movie template instances (generated)
  work-1.127.41/pcode/ea_<Movie>/, new_<Movie>/   gate exports (see 5.3)
  work-compat/gfx/compat_*.swf  outputs of the compat rebuild
  chain-<tag>.log, gate-*.log, rebuild-*.log, compat-*.log
build/
  tyjokr_ScreenReader_UI.package, tyjokr_ScreenReader_Compatibility_UICheats.package,
  tyjokr_ScreenReader.ts4script (compile.py), ffdec-appdata/
```

Established 23-movie extra-hook list (v6 adds AgeUpPanelMain; complete map is in
`rebuild_all.ps1` and `build_ui_package.py`; every movie whose
bytes contain `TooltipManager` gets the template, every one containing
`CatalogImageCellView` gets that class too):

| Movie | Extra classes |
|---|---|
| ClassLibraryScaleform, ClassLibraryOlympus, ClassLibraryGamedata, ClassLibraryWidgetsShared, UIContainer, BaseLibrary, ComponentLibrary, GUIComponentLibrary, HUDLibrary, GameEntryLibrary, GameEntryLauncher, GameEntryDock | TooltipManager (+ CatalogImageCellView where present) |
| TimeControls | `widgets.TimeControls.TimeControlsMain` |
| SimInfoTray | `...SimInfoTray.PhoneCategoryScreen`, `...MotivePanel.CommodityContainer` |
| SimInfoMotivePanel | `...MotivePanel.CommodityContainer` |
| InteractionQueue | `...InteractionQueue.controls.InteractionButton` |
| SimHub | `...SimHub.controls.MoodContainer` (defined only here) |
| ObjectBoundElements | `...elements.HoverTip`, `...elements.SimHeadline` |
| Notifications | `widgets.Notifications.NotificationsMain` |
| Dialog | `widgets.Dialog.DialogMain` |
| PieMenu | `widgets.Gameplay.PieMenu.PieMenuMain` (scanner request path lives here) |
| Pickers | `widgets.Pickers.PickersMain` |
| PickersPurchase | `...PurchasePicker.PurchasePickerCellView`, `widgets.Pickers.PickersPurchaseMain` |

`CASCustomizer` is deliberately NOT built or shipped: any ffdec-rebuilt
copy hard-crashes the client on CAS load, before our code runs (proved
twice 2026-08-03; the source stays in `extra-classes/CASCustomizerMain.as`
for whoever solves the toolchain problem). Adding a movie means editing
BOTH `rebuild_all.ps1` (what gets patched) and `build_ui_package.py`'s
MOVIES (what ships; also the source of truth for `extract_ea_movies.py`
and the gate's movie list).

## 4. Writing patch code (rules that cost crashes)

1. Never write `++`, `--`, `+=` or `-=` on anything in recompiled AS3.
   FFDec re-emits untyped counters as Number (`increment` instead of
   `increment_i`); a Number index into a Vector, or into
   `getCharBoundaries`, faults natively in Scaleform (four crashes on
   2026-08-03, a patron crash on 2026-08-06). Typing locals `:int` fixes
   locals; static properties still compile wrong, so write `x = x + 1`
   everywhere. The gate catches this.
2. Audit `^\s*var\s+\w+\s*:\s*\*\s*=` in every extra class after each EA
   patch and retype those counters to `int`.
3. FFDec rejects `param:Number = NaN` defaults and rewrites `!(x > 0)` as
   `x <= 0` (different for NaN): keep sources NaN-free, use `isNaN()`.
4. FFDec compiles duplicate method definitions silently (the VM picks
   one); grep the patched source for duplicate `function` names.
5. A corrupted `.as` (orphan `catch`, missing brace) makes `ffdec -replace`
   fail SILENTLY with no output; the builders delete the previous output
   first so this is caught as "NO OUTPUT PRODUCED". Never remove that
   guard.
6. EA's exported `.as` files have blank lines of SIX spaces, and patch
   anchors with bare newlines miss; the safe pattern is a Python patch
   script that asserts each anchor occurs exactly once.
7. Wrap every new function body in try/catch; an exception in a
   listener kills the caller's frame.
8. Do not static-import classes the host movie may lack (section 2).
9. In the scanner's Flash code the counter bump is written
   `this.mLastInteractionRequestId = this.mLastInteractionRequestId + 1`
   for rule 1; keep that style.
10. `a11y.mark <text>` from any movie posts a log line; constructor-time
    posts never arrive (ExternalInterface is not ready), only
    announce-time ones do. Use marks to prove which movie's copy is live
    and that a new build really loaded.

Decompiling EA code to read or to seed a new extra class:

```
java -jar C:\Tools\ffdec\ffdec.jar -export script <outdir> <movie.swf>
java -jar C:\Tools\ffdec\ffdec.jar -format script:pcode -export script <outdir> <movie.swf>
```

The first gives `.as` (what the extra classes started from); the second
gives `.pcode` (bytecode listing; what the gate compares, and what the
KeysBB dump parses). Pcode exports of the five class libraries already sit
in `flash/work-1.127.41/pcode/ea_*` (also in the release tree's work dir,
where `olympus/localization/KeysBB.pcode` was read). An AS export of a big
library takes minutes; run it detached (section 5.2).

## 5. Running the pipeline

### 5.1 Commands

```
# after an EA patch only: refresh the originals (UI.package is replaced
# wholesale every patch; a stale work dir ships LAST patch's UI)
python flash\extract_ea_movies.py flash\work-1.127.41

# the whole chain (rebuild all 24, gate, UI package, compat movies + package)
powershell -ExecutionPolicy Bypass -File flash\chain.ps1 -Tag <name>
# same without rebuilding (gate + packages only)
powershell -ExecutionPolicy Bypass -File flash\chain.ps1 -Tag <name> -SkipRebuild

# the pieces, if needed one at a time
powershell -ExecutionPolicy Bypass -File flash\rebuild_all.ps1 -WorkDir flash\work-1.127.41
py -3.7 flash\gate_pcode.py flash\work-1.127.41
py -3.7 flash\build_ui_package.py flash\work-1.127.41 build\tyjokr_ScreenReader_UI.package
powershell -ExecutionPolicy Bypass -File flash\build_uicheats_compat.ps1 -WorkDir flash\work-compat
py -3.7 flash\build_compat_package.py flash\work-compat build\tyjokr_ScreenReader_Compatibility_UICheats.package
```

ALWAYS pass the explicit output path to the two package builders: their
default output is the PARENT release tree's shipping package.

### 5.2 Run it detached and poll

A full rebuild can take several minutes with the v6 batch helper, or much
longer with one JVM per movie. The gate exports up to 48 main movies,
packaging seconds. The Bash/PowerShell tools time out at 120 s (600 s
max), so launch the chain detached and poll its log:

```powershell
$clone = "<original-project>"
$p = Start-Process -FilePath "powershell" -ArgumentList @("-ExecutionPolicy","Bypass","-File","`"$clone\flash\chain.ps1`"","-Tag","v6") -WorkingDirectory $clone -WindowStyle Hidden -PassThru
Write-Output ("chain pid " + $p.Id)
```

Then read `flash\chain-v6.log` until it ends with `CHAIN DONE` or
`CHAIN FAILED` (a background Bash loop `until grep -q "CHAIN " log; do
sleep 30; done` works). A background task that "is still running" reads
exactly like one that silently stopped: wait for the terminal line, never
assume.

Rules: never run two Flash pipelines at once (the gate exports into the
shared `pcode` folder and concurrent runs corrupt each other's
comparisons; one such collision produced a phantom drift FAIL and a mixed
deploy). Kill leftover `java`/`powershell` from a dead session before
relaunching. Never pipe a pipeline step through `| tail` inside a `&&`
chain (the pipe's exit is tail's 0, so the chain continues past a crashed
gate). PowerShell 5.1 `*>>` appends UTF-16, which is why `chain.ps1`
writes through `Add-Content -Encoding utf8`; the old `chain-v2.log` is
UTF-16 and needs `grep -a` or a PowerShell read.

### 5.3 The gate

`gate_pcode.py` exports pcode for `ea_<Movie>.swf` and `patched_<Movie>.swf`
into `work/pcode/ea_<Movie>` and `new_<Movie>` and asserts, per movie:
(1) every TARGETED class (the ones named for that movie in `rebuild_all.ps1`
plus TooltipManager/CatalogImageCellView where present) has no more
`increment`/`inclocal`/`decrement`/`declocal` opcodes than EA's original;
(2) every UNTARGETED class has an identical opcode histogram; (3) no class
disappeared. It prints `fidelity gate PASSED` or `FAIL` lines and exits
non-zero. `export()` SKIPS an existing directory, so stale `new_*` folders
would be compared instead of the fresh build; `chain.ps1` deletes them
first, and a manual run must `rm -rf work/pcode/new_*` first too (never
while a gate java process may still be alive). The gate does not verify
that your new code is present, only that nothing degraded: after every
build grep the fresh export for your new symbol, e.g.
`grep -l A11yShowCaption work-1.127.41/pcode/new_ClassLibraryGamedata/scripts/olympus/core/TooltipManager.pcode`.

### 5.4 The packages

`build_ui_package.py` writes a DBPF 2.1 package: one `0x62ECC59A` resource
per movie, zlib level 9, group/compression/committed flags copied from the
live `UI.package` entry for the same instance, index at the end, then
round-trip reads the package back and byte-compares each movie. A package
that has not changed size after a rebuild is the classic symptom of a
silent ffdec failure (a stale movie got repackaged); compare sizes and
grep pcode before deploying.

The compat package holds the six movies UI Cheats Extension also
overrides (TimeControls, ClassLibraryOlympus, SimInfoTray,
SimInfoMotivePanel, SimHub, PickersPurchase): UI Cheats' own movies as the
base (`uicheats-base/uic_*.swf`, extracted from `UI_Cheats_Extension.package`
1.59.1; older bases in `_v1.57-backup`) with our classes injected. It must
load AFTER both mods' packages to win those movies, so users put it in
their own late-loading folder (this machine: `Mods\_priority\`). Rebuild
it whenever TooltipManager or any of those six movies' classes change
(the chain does), and re-extract the bases after a UI Cheats update.

### 5.5 Deploying

Packages can only be replaced while the game is closed. Copy from `build\`
to `Mods\tyjokr_ScreenReader\` (UI package) and `Mods\_priority\` (compat)
with PowerShell `Copy-Item`, then hash both sides (`Get-FileHash` or
`sha256sum`). Do NOT use `flash\deploy_package.py` in this tree: it copies
the package sitting at the tree ROOT, which is the 2026-08-28 release
copy, not `build\`. The ts4script is deployed by `py -3.7 compile.py`
(scripts only; it never touches packages). Robocopy from Git Bash mangles
`/E` into a path; run it from PowerShell if used.

### 5.6 After an EA patch

1. `extract_ea_movies.py` into a NEW `work-<version>` folder (keep the old
   one; they are the only diff base you will have). Since 2026-09-24
   `chain.ps1` takes `-Work work-<version>` (default `work-1.128.90`); pass it
   instead of editing the script. Run the compat gate afterwards with
   `py -3.7 flash/gate_compat_pcode.py flash/work-compat` (it needs the arg).
2. Diff EA's exported `.as` of each patched class against the previous
   version's export; port the edits in `extra-classes/*.as` and the
   template onto the new source (EA rebuilt all 23 movies in 1.127.41,
   +800 to +3400 bytes each, and a "0 findings" tuning triage does NOT
   cover UI.package).
3. Audit rule 2 of section 4, rebuild, gate, package, compat, deploy,
   test.

## 6. Current Flash state in this tree (2026-09-15)

**v5 continuation completed and deployed for testing.** The guarded final
caption build is `chain-captions-v5-final.log` (CHAIN DONE, main fidelity gate
PASSED: 60 targeted comparisons). `gate-compat-v5.log` passes 19 targeted
comparisons against the six UI Cheats base movies; the checker is
`flash/gate_compat_pcode.py` and must run after the chain, never alongside it.
`tools/verify_v5_artifacts.py` checks source/module equivalence, resource
round trips and caption symbols in all 29 shipped movie resources.

Installed with the game closed: script 185,397 bytes, main UI 17,642,544
bytes, compatibility UI 4,566,575 bytes. Exact verified `build/` files were
copied by `tools/deploy_v5.ps1`; all three installed hashes match and cfg
is unchanged. Full hashes are in `build/v5-deployment.json`. Prior installed
files are in `build/deployed-before-v5/`. In-game testing remains pending.

- `TooltipManager_patched.as`: tab ring / focus walker / arrow nav /
  picker index scrolling (from the release), plus the scanner's game-
  message hook (`A11yInstallGameMessageHook`, `A11yOnGameMessage`,
  `A11yHandleEncoded`, `A11yResolveLoc`, `A11yMsgHidePieMenu`, static
  `sA11yPick`). The caption panel is now implemented
  (`mA11yCaption`, `mA11yCaptionText`, `A11yShowCaption`,
  `A11yLayoutCaption`, `A11yHideCaption`, laid out from
  `A11yOnLayerStaged`). The early `chain-captions-v5` run was stopped after
  rebuilding, to add required try/catch guards to all new helpers. It is
  superseded by the completed `chain-captions-v5-final` run above.
- `extra-classes/PieMenuMain.as`: `A11yOnOpenPieMenu` (client-side pie menu
  request for the scanner), `A11yPostText`, `a11y.menuclosed` from `Hide`,
  `a11y.menuempty`, and the `piecreate-...` diagnostic mark that must be
  stripped before release.
- Captions are off by default; `a11y.captions on|off` or the settings window
  toggles them. The first-install popup is deferred at the user's request.
- Release tree `ScreenNarrator/flash/` has the same scripts without the
  scanner additions, plus `work-1.126.78` and the gamepad archive; it is
  the reference, not the place to build.
