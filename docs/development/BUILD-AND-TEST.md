# Building, packaging and testing TS4 Access

## What each command does

Run commands from the kit root in Windows PowerShell. `Dev.ps1` is a thin wrapper around `py -3.7 tools/devkit.py`; using that Python command directly is equivalent. If Windows blocks a downloaded PowerShell script, use the process-scoped command shown in START-HERE.md. Do not change the machine's execution policy globally.

`doctor` checks Python 3.7, Node, the installed game's UI baseline, the three game Python archives, and the reference input hashes. `doctor --full` also checks JDK 21 with javac and the pinned FFDec distribution. Configuration is read from `dev.local.json` or the three TS4_* environment variables. The local JSON is excluded from source exchange.

`build --scripts-only` is for Python-only edits. It compares all canonical Flash source/build-recipe files with the handoff manifest and refuses reuse if any were added, changed or removed. It runs the full offline test suite, copies the reviewed UI pair from reference/ui, freezes Python sources, and stages a release-layout test pair. The original UI candidate's live limitations remain; a reference package is not proof of a new Python feature's correctness.

Both build commands first compile the TS4 Access helper from its included C# source, because its smoke tests exercise the executable. No precompiled helper is needed in the source kit.

`build` runs the full UI pipeline as well: compile the Java helper sources, rebuild the main movies, run the main fidelity gate, build the main DBPF, rebuild and build the six compatibility movies, run the separate compatibility gate, check resource identity, non-code tags and class definitions, then stage Python and UI together. Both paths reject source edits occurring during the build and refuse overlapping wrapper builds through build/devkit.lock. A crashed wrapper may leave that lock: verify no Python/Java/PowerShell build is still running before removing that one lock file. Do not delete it while another build is active.

The batch helpers are an optimization around FFDec, not a different compiler. `build/*.class`, generated ttm_*.as, patched/compat movies and pcode exports are generated output. Do not return them as source fixes. The canonical recipes remain in flash and tools. Do not run two Flash chains in the same workspace. Work on a copy when comparing compiler variants.

## Results and evidence

Successful runs write a timestamped `build/devkit-*` candidate and a new `dist/<timestamp>` directory. The latter contains:

- `TS4_Access_<date>.zip`: TS4_Access.ts4script, TS4_Access_UI.package and the three player text guides in one TS4_Access folder.
- `TS4_Access_Compatibility_UICheats_<date>.zip`: optional late-loading compatibility package and its installation note.
- `RELEASE-MANIFEST.json`: hashes of all staged packages and files.

No cfg is in a player ZIP. No personal settings or logs are copied. The release transform sets the build logging switch off and strips workstation paths from Python code objects. All 25 Python modules, including the ctypes subpackage, are compared against a fresh compile of the frozen sources. ZIP timestamps can differ even when executable contents match; compare manifest/package/member hashes or code objects appropriately.

Read `build/v10-checks.json`: **passed must be true AND input_stable must be true**. Inspect each failure log. The runner's total counts include repeated imported checks; a large count is not evidence all tests passed. Test counts will grow with legitimate coverage. A skipped game-import suite because TS4_INSTALL is wrong is not an adequate substitute for testing game imports; doctor requires the game archives first.

The historically named `tools/verify_v10_artifacts.py` remains as a library for shared checking functions and test fixtures. Its standalone main function describes an obsolete build. Do not run it to certify this kit. Use the current Dev build, the JSON report and both current gates. Similarly, do not run old commands from docs/development/history just because they once passed.

## Install a test build only when Leo asks

1. Close the game normally. Verify no TS4_x64.exe or TS4_DX9_x64.exe process remains. Do not replace modules or packages while the game is running.
2. Back up the current mod files and the test save. Identify the actual Sims user folder, including OneDrive/localized Documents if relevant. That is not the Steam/EA installation folder.
3. Remove duplicate older TS4 Access/Screen Reader/Screen Narrator script or UI copies from the test Mods layout after preserving them outside Mods. Duplicate Python module names can load the wrong copy. Merely renaming an old .ts4script does not disable it.
4. Copy the **paired script and UI from the same dist build** into `Mods\TS4_Access`. Script mods must be at Mods root or one subfolder deep. Preserve the player's generated cfg and speech pack.
5. If testing UI Cheats, use the matching compatibility package from that build in a configured priority folder that loads after both mods. Do not assume underscores alone guarantee priority; inspect Resource.cfg and the user's arrangement. If UI Cheats is absent, leave compatibility out.
6. Ensure both Custom Content and Mods and Script Mods Allowed are enabled. The TS4 Access helper can do that with the game closed; its source is included, and `powershell -File tools/build_prelaunch_helper.ps1` builds its EXE using Windows' C# compiler. The helper does not install this development build or launch the game.
7. Hash the installed script/UI and compare with RELEASE-MANIFEST.json before launch. Start normally through Steam or the EA app, load an existing test save, and enable diagnostic logging only as needed. Never distribute your local cfg to players.

The build system intentionally has no automatic deploy command. Your assistant can copy the reviewed pair when you instruct it, but must check the process, target folder, backup and hashes. To roll back, close the game and restore the backed-up pair together; preserve the user's preferences unless a particular test explicitly requires changing them.

For screen-reader testing on a fresh install, copy the **entire contents** of the kit's `prism` folder to `Mods\TS4_Access\TS4_Access_SpeechPack`, retaining `prism.dll`, `LICENSE`, `NOTICE`, `SOURCE.txt` and the complete `LICENSES` tree. Start the screen reader before launching the game. Without the pack, Windows voice fallback is expected. The regular test ZIP contains the mod, not this separate speech pack; see README-SpeechPack.txt. Do not rename the DLL or flatten/drop its notices when sharing a test installation.

## Useful in-game diagnostics

Open the cheat console with Ctrl+Shift+C, enter a command, then close the console before testing navigation. Useful existing commands include `a11y.status`, `a11y.log on`, `a11y.log off`, `a11y.inspect`, `a11y.keys`, `a11y.reload`. Consult current CHEATS.txt and source command registrations for exact arguments. A command that only exists in an old probe must not be assumed available in the shipping mod.

Logging defaults off. With logging enabled, collect a short relevant excerpt around the action, including UI owner transitions and routing/drop messages. Do not leave speech/utterance logging enabled for a player build. Remove private Sim names or unrelated events from shared evidence.

## Live test matrix

Always test the feature changed and one or two neighboring flows that share its routing. Offline fixtures do not emulate the actual Flash runtime, screen reader, timing, focus, or game APIs completely.

- **Input:** deliberate shortcut; modifier keys alone; release/repress; hold repeat; key held before adding Ctrl+Alt; switching away/back; text fields; AltGr; no keys stuck or double actions. Respect a screen reader's own bindings.
- **Phone guard baseline:** incoming call; call for a non-active household Sim; phone alert/needs panel visible; a true dialog or picker above the call alert; dialog opening after a queued press. Ctrl+Alt+P must reach the call in the HUD cases and refuse through real blocking surfaces.
- **Clock baseline:** Ctrl+Alt+C in running and paused Live Mode; Accessibility menu > Day and time; picker remains focused while clock is read; Build Mode; main menu reports unavailable rather than silence; text entry retains ownership. The starting candidate's live check remains pending.
- **Menus and recipes:** ordinary pie action; cooking/drink recipe row; serving-size selection; purchase quantities and Done; delivery picker. These are different picker types, not one generic dialog.
- **Scanner and Build:** scanner off/on and returning from a dialog; build catalog navigation; choose object, placement cursor, coordinate speech, rotate/place/cancel; stop at documented feature boundaries (walls/roofs etc. are not implemented by the placement grid).
- **Navigation transitions:** HUD -> dialog -> world; travel alone/companions/destination/confirmation; season screen's four choices and move-in occupancy/affordability/furnishing. Use a purpose-specific fixture/save; do not run a full CAS flow to test an unrelated keyboard fix.
- **Startup and voice:** main menu before a lot, live mode after load, return to menu, installed screen reader and Windows voice fallback where affected.

Write observed outcomes, not just "tested". If Leo cannot test a pack-specific path, mark it untested and return the change for broader testing. Do not declare a no-crash guarantee: the gates specifically catch known compiler damage, while actual runtime behavior still needs in-game evidence.

## Rebasing after game updates

Doctor deliberately rejects a changed game UI.package. Preserve the old inputs and source kit, extract the new originals to a new work directory, compare affected EA classes and imports, update canonical patches where needed, rebuild both relevant outputs and run the gates and live cases. See GFX-SAFETY.md for the detailed process. The optional compatibility baseline also needs review when UI Cheats updates. A new accepted baseline should become a new handoff kit; do not have collaborators independently rewrite its immutable hash manifest.
