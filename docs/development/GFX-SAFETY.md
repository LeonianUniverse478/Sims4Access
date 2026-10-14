# GFX and ActionScript safety

Read this before changing anything under `flash/`. A mistake in Python usually shows up as an exception in the mod log. A mistake in a UI movie can crash the whole game natively, with no Python traceback. It can also silently switch off a feature because another movie's copy of a class wins. Every rule below comes from a real crash or a silent failure in this project.

Tool versions, environment variables and install steps are in [BUILD-DEPENDENCIES.md](BUILD-DEPENDENCIES.md).

## 1. What you are editing

The Sims 4 UI is made of Scaleform GFx movies written in ActionScript 3. They live in `<game>\Data\Client\UI.package` as resource type `0x62ECC59A`. Each resource's instance number is the FNV-1 64-bit hash of the movie name in lowercase. TS4 Access ships two override packages:

- **Main UI package:** 25 whole movies. The list is `MOVIES` in `flash/build_ui_package.py`.
- **UI Cheats compatibility package:** 6 whole movies. The list is `MOVIES` in `flash/build_compat_package.py`.

Canonical sources (edit these):

- `flash/TooltipManager_patched.as`. It is one template for `olympus.core.TooltipManager`. Most of the keyboard, focus and narration logic lives here, and it is compiled into 23 of the 25 movies.
- `flash/extra-classes/*.as`. Each file replaces one EA class wholesale: EA's decompiled class body plus our additions.

The `.py` and `.ps1` files under `flash/` are the canonical build recipes. The following inputs and generated outputs are not places to edit feature code:

- **`flash/work-*/gfx/ea_*.swf`:** EA's original movies, extracted from your own install by `extract_ea_movies.py`.
- **`flash/work-*/gfx/ttm_<Movie>.as` and `ttm_compat_<Movie>.as`:** the template with the placeholder `A11YLIBNAME` replaced by the movie name. They are rewritten on every rebuild; an edit there is lost and never reaches source control.
- **`flash/work-*/gfx/patched_*.swf`, `compat_*.swf` and `pcode/`:** build output.
- **Copies of the template under `build/` or `dist/`:** snapshots recorded for a release, not sources.

Because every extra class is a full EA class, it goes stale when EA patches the game. See section 8.

## 2. One application domain: patch every definer

All UI movies load into one Flash application domain. For any class name, the first loaded definition wins for the whole game, and later copies are never used. Consequences:

- Patching a class in one movie does nothing if another movie's copy is the one that loads first. `ClassLibraryGamedata` wins `olympus.core.TooltipManager` in live play. Patching the class into `CASLibrary` was proved useless for that reason.
- Before patching a class, list every movie that **defines** it, not every movie that merely mentions it. `tools/audit_ui_classes.py` reads the ABC instance tables of every movie in UI.package and reports definitions. A byte search for the class name also matches references and is not enough.
- Then either ship the patch in **every** defining movie, or hook a class defined in exactly one movie. Real cases:
  - `CommodityContainer` is defined in both `SimInfoMotivePanel` and `SimInfoTray`. The unpatched `SimInfoTray` copy silently disabled the needs announcer until both were patched.
  - `PickersMainBase` is compiled into seven picker movies, so which copy loads first is effectively a lottery. Hooks go into each movie's own `*Main` subclass instead.
  - `MoodContainer` exists only in `SimHub`, and `ControlPanel` only in `GameTray`. Those are safe single definers.
- TooltipManager is compiled into every shipped movie that defines it, so whichever copy loads first is ours.
- Two movies are "own class only": `AgeUpPanel` and `GameTray` (`$ownOnly` in `rebuild_all.ps1`). They replace only their dedicated class. Their own TooltipManager and CatalogImageCellView copies must stay untouched; the gate checks their opcode counts as untargeted classes.
- Keep the shipping list minimal. Every extra movie is another full override that must be rebased on each EA patch. Two movies are excluded on purpose:
  - **EngagementLibrary:** with it in the package, opening the Gallery froze the machine.
  - **CASCustomizer:** it crashes the game (section 4).

## 3. The integer gate

FFDec's AS3 compiler does not emit the same bytecode as Adobe's compiler. EA's decompiled code often declares loop counters untyped:

```actionscript
var _loc9_:* = 0;
...
someVector[_loc9_++]
```

Adobe's compiler emitted integer opcodes for such counters (`increment_i`, `inclocal_i`, `decrement_i`, `declocal_i`). FFDec emits the generic opcodes, so the counter becomes a floating-point Number. Scaleform's VM faults natively on a Number used as a Vector index. Where EA's code dereferences a lookup result without a null check, the Number index also reaches it. Both have shipped:

- **2026-08-03, SimHub `BuffDisplay.DetermineBuffVisuals`:** the game crashed on every Sim activation, even for a control build containing only EA's own source.
- **2026-08-06, TimeControls `SetBlurPosition`:** a player crash on 1.126.78. A Number index reached `getCharBoundaries`, which returned null, and EA's code dereferenced the result.

House rules for any class you recompile:

- Type every counter and index `int`: `var i:int = 0;`. Audit every `:* = 0` in EA's body.
- In code you add, write `x = x + 1` instead of `x++`, and `x = x - 1` instead of `x--`. The gate compares counts of the generic opcodes against EA's, and any extra one fails the build.
- Never treat "the decompiled .as looks the same" as evidence. Only 2 of 21 SimHub classes round-trip byte-identical through FFDec.
- A known harmless difference: FFDec turns `initproperty` into `setproperty` on instance slot traits. Movies that ship this way work in game.

`flash/gate_pcode.py` enforces this. It exports pcode for every EA movie and every rebuilt movie, then checks three things:

1. **Targeted classes** (the ones we replace) gain no `increment`, `inclocal`, `decrement` or `declocal` beyond EA's count.
2. **Untargeted classes** retain EA's opcode counts. FFDec `-replace` should rewrite only the classes you name; detected changes elsewhere are collateral damage.
3. **No class disappears.**

The chain refuses to build a package unless the gate prints `fidelity gate PASSED`. For the compatibility package, run `flash/gate_compat_pcode.py flash/work-compat` after the chain. It makes fresh exports and applies the same checks against the UI Cheats bases.

The gate compares opcode counts, not every instruction's order or operands. Passing it is not proof of complete bytecode identity or correct logic, and it does not notice that an extra class body is older than EA's current one (section 8). Keep the compiler pinned, inspect unexpected changes, and complete the package and live checks too.

## 4. Rules that prevent native crashes

- **Never reference a class that the movie cannot resolve.** This covers imports, type annotations, `is` or `as`, `new`, and static calls. The AVM resolves class references when it verifies a method, before any `try`/`catch` inside that method can run, so the crash is native and uncatchable. The template is compiled into 23 different movies, so every class it names must exist in all of them. For anything that exists only sometimes, do one of two things:
  - Duck-type it, e.g. `obj["IncreaseAmount"]`. `PurchasePickerCellView` is deliberately never imported.
  - Or resolve it with `getDefinitionByName` inside `try`/`catch`. `A11yAttachUiCheats` in `TimeControlsMain.as` finds UI Cheats' class this way, so the movie works with or without UI Cheats installed.
- **Do not ship CASCustomizer.** Any FFDec-rebuilt `CASCustomizer` crashed the client on CAS load, even when none of our code ran. A marker posted at the end of `Initialize` never fired in either attempt. At tag level the only difference from EA's movie is the bytecode block. The entry stays commented out in `rebuild_all.ps1` and absent from `MOVIES`. `extra-classes/CASCustomizerMain.as` is kept only as reference source. CAS work is out of scope for this kit.
- **Wrap every entry point in `try`/`catch`,** as the existing code does. Remember that `try`/`catch` cannot catch verify-time errors or native faults.
- **Don't post from constructors.** A `PostServerCommand` made during construction never arrives, because the external interface is not ready yet. Post from event handlers and frame callbacks.
- **Leave EA's display objects in place.** Hide or reuse them rather than calling `removeChild` on objects EA manages. A sibling mod built with the same toolchain (the Needs panel redesign) crashed natively after removing pooled children.
- **Keep per-frame work bounded.** Add `ENTER_FRAME` listeners with weak references, and remove them when done.
- **Never hardcode English in Flash.** Read the text EA's widgets already display, since it is localized. The mod's own vocabulary is translated in Python (`Scripts/tyjokr_a11y_lang.py`).

## 5. Flash to Python and back

- **Live play.** `CommunicationManager.PostServerCommand(command, payload)` arrives in Python as a Live console command, registered with `sims4.commands.Command('a11y....')`.
  - Text payloads are percent-encoded. Use `encodeURIComponent`, then escape `'`, `(`, `)` and `!`, as `A11yOnTimeOver` and `A11yClock` do.
  - Python decodes them with `narrator._decode_percent`, because Scaleform encodes U+0080 to U+00FF as raw Latin-1 bytes.
- **Numbers lose leading zeros.** The native command path turns `"00"` into `"0"` before Python sees it. Never rely on fixed-width digit strings. `a11y.modalstate` stays two digits and Python repairs a missing zero. The phone blocking bit is its own single-digit command, and it is also carried as the third digit of the percent-encoded `a11y.context_enc` suffix, where no zero is stripped.
- **Main menu, before a save loads.** Posts do not reach Python through the command path. `A11yPostToPython` sends them through a local socket bridge instead:
  - The Python side is `Scripts/tyjokr_a11y_startup.py`, listening on port 45993 (keyboard with Simplified menus), 45995 (keyboard) or 45994 (speech only).
  - A new Flash-to-Python command must be added in **three** places: the `allowed` list in `A11yPostToPython`, `CHANNELS` in `tyjokr_a11y_startup.py` (with payload validation in `parse_post`), and `_dispatch` in the same file.
  - Miss one and the command works in live play but silently disappears at the main menu. That happened to `a11y.blocking` and `a11y.clock_enc` and was fixed on 2026-09-27.
  - Startup posts are limited to 40 per second, except the state messages `a11y.inputfence`, `a11y.modalstate`, `a11y.blocking` and `a11y.mark`.
- **Python to Flash.** Python sends `distributor.ops.SendUIMessage` messages whose names start with `A11y|`. TooltipManager's `SendUIMessage` hook intercepts them. Only the message name travels, so the data is encoded into the name.

## 6. Build order

| Step | Command | Why |
|------|---------|-----|
| 1 | `py -3.7 flash/extract_ea_movies.py <work>` | **First after every EA patch.** Without it you rebuild on the previous patch's movies and ship an old UI as an override. |
| 2 | `powershell -File flash/rebuild_all.ps1 -WorkDir <work>` | Compiles the template and extra classes into each movie. Old output is deleted first, and every result must start with `GFX`. |
| 3 | `py -3.7 flash/gate_pcode.py <work>` | Must print `fidelity gate PASSED`. |
| 4 | `py -3.7 flash/build_ui_package.py <work> [<out>]` | Writes the package and verifies it by reading every resource back. |
| 5 | `powershell -File flash/build_uicheats_compat.ps1 -WorkDir flash/work-compat`, then `py -3.7 flash/build_compat_package.py flash/work-compat [<out>]` | Builds the compatibility package. |
| 6 | `py -3.7 flash/gate_compat_pcode.py flash/work-compat` | Compatibility fidelity gate. Run it on its own, after the chain. |

`flash/chain.ps1` runs steps 2 to 5 and ends with `CHAIN DONE` or `CHAIN FAILED` in `flash/chain-<tag>.log`. The kit's own entry point is `Dev.ps1` (`doctor`, `build`); see [EXCHANGE.md](EXCHANGE.md).

Build hygiene:

- **One pipeline at a time.** Never run two Flash pipelines at once; they share the work folder's pcode exports.
- **FFDec warnings are not failures.** FFDec prints tag-parse warnings to stderr even for EA's untouched movies. The scripts deliberately treat stderr as non-fatal and judge each output by its `GFX` magic and by the gate.
- **Batch helpers.** When the compiled helpers exist (`TS4_FFDEC_HELPERS`, default `build/`), `rebuild_all.ps1` and `build_uicheats_compat.ps1` compile every movie in one JVM with `ReplaceScriptsBatch`. Otherwise they call `java -jar ffdec.jar -replace` once per movie. The first line of output says which path ran. The gate works on either result.
- **Package output.** The builders never write into a `Mods` folder: build locally, then copy with the game closed. Writing while the game is running produces a truncated package, and the game then reports "marshal data too short" for a script archive or fails to load the UI.

## 7. The UI Cheats compatibility package

UI Cheats Extension (by weerbesu) overrides six of the same movies. With both mods installed, whichever package loads later wins each movie whole, and the other mod's features vanish there. The compatibility package compiles our classes on top of UI Cheats' movies, so both feature sets coexist. Players install it in a folder that loads after both mods.

- **The baseline.** The bases are in `flash/uicheats-base/uic_*.swf`, and `SOURCE.txt` records their provenance: UI Cheats 1.59.1, extracted 2026-08-28. UI Cheats' movies carry whatever EA code UI Cheats was built against, so they can lag behind the current game patch.
- **How UI Cheats' edits are kept.** UI Cheats changes none of the classes we inject except `TimeControlsMain`. Its one edit there is replicated in our copy through `getDefinitionByName`.
- **When UI Cheats updates:**
  1. Run `py -3.7 flash/extract_uicheats_bases.py --package <UI_Cheats_Extension.package> --out <scratch folder>`. It lists each movie as the same as, or different from, the baseline.
  2. For each changed movie, compare UI Cheats' new pcode with the baseline's. Confirm whether they now touch a class we inject.
  3. Re-run the extractor with `--out flash/uicheats-base --replace-baseline`, fill in the version line of the new `SOURCE.txt`, then rebuild and run `gate_compat_pcode.py`.
- **If UI Cheats adds or drops an overridden movie,** three lists must change together: `$movies` in `build_uicheats_compat.ps1`, `MOVIES` in `build_compat_package.py`, and the count of six asserted in `gate_compat_pcode.py`. The extractor refuses to write anything when a listed movie is missing.

## 8. Rebasing after an EA patch

1. Extract the new EA movies (build step 1).
2. For every file in `flash/extra-classes/` and for the TooltipManager template, compare EA's **previous** and **new** decompile of that class. Port EA's changes into our copy. The fidelity gate does **not** catch a stale class body: an old EA body plus our hooks compiles, passes the int checks, and silently reverts whatever EA fixed in that class.
3. Re-run the class audit (section 2) if EA may have added a new definer of a class we patch.
4. Rebuild, run the gate, run the tests, then live-test on an existing save.

## 9. Tests, and what counts as a pass

- `tools/run_checks_v10.py` (Python 3.7) runs every `tools/test_*.py` and `tools/test_*.js` (Node) in isolation and writes `build/v10-checks.json`.
- **The verdict is the JSON:** `"passed": true` and `"input_stable": true`. The console's `N checks across M suites` line prints even when suites fail. Never report that count as a pass; read `passed` and the list of failing suites.
- **What the JS tests prove.** They extract function bodies from the `.as` sources and run them under Node. That proves logic only, not that the movie compiles or behaves in game; only the gate and a live test prove that.
- **The old artifact verifier.** Do not run the `main()` of `tools/verify_v10_artifacts.py` as a release check. It asserts an obsolete 24-movie scope, from before GameTray was added. Use `Dev.ps1 doctor` and `Dev.ps1 build`.
- **Live tests.** Use existing saves. Keep the game closed while copying files into `Mods`. The mod writes its log to `TS4_Access.log` next to the script in `Mods\TS4_Access`.

## 10. When the game crashes

- **Read the crash report.** It is `lastCrash.txt` in the Sims 4 user folder, next to `Mods`.
  - If it names an AS3 `Movie/Method`, the fault is in ActionScript. Export pcode for that class from both the shipped movie and EA's, and compare the int opcodes first.
  - If no AS3 method is named, the fault is inside the VM or renderer. Suspect display-list misuse or an unresolvable class reference.
- **Isolate the movie.** Restore a previously verified working script/UI pair and see whether the crash follows the change. A folder under `dist/` can contain an untested candidate; its presence alone does not make it a known-good release.
- **Report what you saw,** with the crash report's `<stack>` section and the last lines of the mod log.
