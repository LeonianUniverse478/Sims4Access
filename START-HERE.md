# TS4 Access developer handoff

For LeonianUniverse and his Claude, from tyjokr. This is the editable development kit, not the download players install. Keep it outside Mods.

Give Claude this folder and say:

> Read CLAUDE.md and docs/development before changing anything. Help me make and test my changes, then produce a return ZIP for tyjokr. Do not install, publish, or replace my game files without my instruction. Preserve the handoff baseline.

The kit contains Python source, ActionScript source, GFX build inputs, the reviewed reference UI packages, regression tests, and a source exchange tool. It has no personal settings, saves, logs, credentials, or chat mailbox. The starting mod source matches the September 26, 22:09 candidate. Its phone and clock changes passed offline checks and independent review; live verification was still pending when this handoff was made.

## First setup

1. Extract this whole folder to a writable local directory, for example `C:\TS4AccessDev`. Do not use a synchronized folder while a build runs.
2. Install Python **3.7.9 x64**, including the Python launcher, and Node.js. Run `py -3.7 --version` and `node --version` in a new PowerShell window. Modern Python creates bytecode the game cannot load; use 3.7 for the build.
3. Copy `dev.local.example.json` to `dev.local.json`. Set `TS4_INSTALL` to **your game installation** containing `Data\Client\UI.package`. Steam and EA installations both work. This is different from Documents\Electronic Arts\The Sims 4, which contains saves and Mods.
4. For UI work, also install the full portable **FFDec 26.2.1** distribution (keep its `lib` directory) and **JDK 21**. Set `TS4_FFDEC` to `ffdec.jar` and `TS4_JAVA` to `java.exe` in that JDK. The kit checks the tested FFDec hashes.
5. **From a GitHub clone** (the public source has no game or UI Cheats files), first make them from your own installs. This needs UI Cheats Extension 1.59.1's package; a handoff kit already has these files and skips this step:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Dev.ps1 setup --uicheats "<path to UI_Cheats_Extension.package>"
```

6. From the kit folder, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Dev.ps1 doctor
# Also checks JDK and FFDec for a full UI build:
powershell -NoProfile -ExecutionPolicy Bypass -File .\Dev.ps1 doctor --full
```

Official downloads: [Python 3.7.9](https://www.python.org/downloads/release/python-379/), [Node.js](https://nodejs.org/en/download), [FFDec 26.2.1](https://github.com/jindrapetrik/jpexs-decompiler/releases/tag/version26.2.1), [Temurin JDK 21](https://adoptium.net/temurin/releases/?version=21). Python 3.7 is required for this game's compiler, not recommended as a general application runtime.

## Build for testing

For Python changes with unchanged UI sources:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Dev.ps1 build --scripts-only
```

For ActionScript, UI behavior, or Flash build-recipe changes:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Dev.ps1 build
```

The full build takes longer. It compiles the Java helpers, builds all 25 main and 6 compatibility movies, runs both bytecode gates, verifies movie contents, runs the source checks, and makes the paired test ZIPs. Build only one copy at a time. Neither command installs or publishes anything. See [testing and packaging](docs/development/BUILD-AND-TEST.md) before copying files into Mods.

## Send changes back

From the same handoff folder after making changes:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Dev.ps1 return --summary "Describe the behavior changed and why" --tests "List commands and actual in-game cases; say what remains untested"
```

Send the ZIP created in `exchange` to tyjokr using your usual file-sharing method. Do not send a whole Mods folder or only a compiled package. The return contains readable source changes and testing notes. Your `dev.local.json`, generated packages, saved games, and settings are excluded.

Tyjokr keeps an untouched copy of the original source kit. To review Leo's ZIP in that copy:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Dev.ps1 review "C:\Downloads\TS4_Access_changes_....zip"
```

Read the generated `reviews\...\REPORT.md` and `CHANGES.patch`. No source is merged automatically. After review, Claude can apply the approved files/deletions, resolve flagged conflicts, and rebuild. See [round trips and review](docs/development/EXCHANGE.md) for subsequent rounds and optional Git.

Do not regenerate or edit `.handoff` to hide a baseline mismatch. Keep `reference` and the original GFX inputs unchanged. If an EA or UI Cheats update changes the baseline, stop and follow [GFX safety and rebasing](docs/development/GFX-SAFETY.md).
