# Build dependencies

This page lists what the TS4 Access build needs on a developer's machine, where each piece is found, and what the kit does and does not contain. Safety rules for the UI movies are in [GFX-SAFETY.md](GFX-SAFETY.md). Passing changes back for review is covered in [EXCHANGE.md](EXCHANGE.md).

## Tools you install yourself

These are not redistributed in the kit.

| Tool | Tested version | Used for |
|------|----------------|----------|
| Python 3.7 | 3.7.9 | Compiling the script mod: the game runs Python 3.7, so the `.pyc` files must come from 3.7. The Flash scripts and tests also run under it. Chain and kit commands call it as `py -3.7`. |
| Java (a JDK, not only a runtime) | Temurin 21.0.11+10 | Running FFDec, and compiling the two batch helpers once with `javac`. The helpers need Java 11 or newer. |
| JPEXS Free Flash Decompiler (FFDec) | 26.2.1 | Recompiling the patched ActionScript classes into the UI movies and exporting pcode for the fidelity gate. GPL-3 licensed; its `license.txt` is in its own folder. |
| Node.js | 24.14.1 | The `tools/test_*.js` tests, which run ActionScript function bodies under Node. |
| The Sims 4 | the patch you are building for | `Data\Client\UI.package` is the source of EA's original movies. |

**Pin FFDec.** The rebuilt movies are produced by FFDec's compiler, and a different FFDec version can emit different bytecode. `java -jar ffdec.jar -help` prints the version on its first line (`JPEXS Free Flash Decompiler v.26.2.1`). The tested jars hash as follows:

- `ffdec.jar`: `090ab695053ad94cba6408574c7d7eea20ec60b6ae789ee6056a23f45106762f`
- `lib/ffdec_lib.jar`: `2a9dfd3d47cec97b1ac13ae2e0aac1f118a901c7e696cb3ad650548af864b4f2`

A different version needs separate compiler validation. The fidelity gate catches known bytecode hazards, but it does not replace the other artifact checks or in-game testing (see GFX-SAFETY.md, section 3).

## Where the build finds things

The Flash scripts read these environment variables. When one is not set, the first default that exists is used. A tool that cannot be found stops the build with a message naming the variable to set.

| Variable | Meaning | Defaults tried |
|----------|---------|----------------|
| `TS4_JAVA` | Full path of `java.exe` | `C:\Tools\jdk21\jdk-21.0.11+10\bin\java.exe` |
| `TS4_FFDEC` | Full path of `ffdec.jar` | `C:\Tools\ffdec\ffdec.jar` |
| `TS4_INSTALL` | The Sims 4 install folder, the one holding `Data\Client` | The `Install Dir` recorded by the EA app in the registry, then `C:\Program Files\EA Games\The Sims 4`, `C:\Program Files (x86)\Origin Games\The Sims 4`, `C:\Program Files (x86)\Steam\steamapps\common\The Sims 4`, `C:\Program Files\Steam\steamapps\common\The Sims 4` |
| `TS4_FFDEC_HELPERS` | Folder holding the compiled batch helpers | `build\` in the project |

Two files hold these lookups: `flash/flash_config.py` for the Python scripts and `flash/flash_config.ps1` for the PowerShell scripts. Their default lists must stay identical.

Example for one PowerShell session:

```powershell
$env:TS4_JAVA = 'D:\jdk-21\bin\java.exe'
$env:TS4_FFDEC = 'D:\ffdec\ffdec.jar'
$env:TS4_INSTALL = 'D:\Games\The Sims 4'
```

## The FFDec batch helpers

`tools/ReplaceScriptsBatch.java` and `tools/ExportPcodeBatch.java` drive FFDec's own compiler and pcode exporter inside one JVM for the whole batch. That is much faster than starting FFDec once per movie. Compile them once per machine:

```powershell
$javac = Join-Path (Split-Path $env:TS4_JAVA) 'javac.exe'
& $javac -cp $env:TS4_FFDEC -d build tools\ReplaceScriptsBatch.java tools\ExportPcodeBatch.java
```

(Set `TS4_JAVA` and `TS4_FFDEC` first, as in the example above.)

`ffdec.jar` alone is enough on the classpath, because its manifest pulls in `lib\ffdec_lib.jar`. Compiling with JDK 21.0.11 reproduces the project's class files byte for byte.

If the classes are missing, the scripts still work, only more slowly: they fall back to one `java -jar ffdec.jar` process per movie. The first line of the rebuild output says which path ran.

FFDec also needs a writable settings folder. `flash/chain.ps1` and `flash/gate_compat_pcode.py` point `APPDATA` at `build\ffdec-appdata` for that. Running `rebuild_all.ps1` or `gate_pcode.py` directly uses your normal profile, which also works.

## Inputs in the kit

| Path | What it is | Where it came from |
|------|------------|--------------------|
| `flash/TooltipManager_patched.as` | Template compiled into 23 movies | Our source, built on EA's decompiled class |
| `flash/extra-classes/*.as` | One replacement EA class per file | Our source, built on EA's decompiled classes |
| `flash/uicheats-base/uic_*.swf` | UI Cheats Extension's six overriding movies, the base of the compatibility package | Extracted from UI Cheats Extension 1.59.1. See `SOURCE.txt`, and `flash/extract_uicheats_bases.py` for the next update. Third-party input, included for private development only. |
| EA's original movies (`ea_*.swf`) | The base of every rebuilt movie | Extracted from your own game by `flash/extract_ea_movies.py`. If the kit includes a copy, it is a private development baseline for the patch named in the kit, not a source. |
| `tools/vendor/dbpf_extract.py` | Reads `.package` files | Project copy; the Flash scripts load it from here. |

## Outputs

- **Rebuilt movies and pcode exports:** inside the work folder you pass (for example `flash\work-1.128.90\gfx` and `...\pcode`).
- **Packages:** `build\tyjokr_ScreenReader_UI.package` and `build\tyjokr_ScreenReader_Compatibility_UICheats.package`, unless you give an output path as the second argument.
- **Never into `Mods`:** the package builders refuse a path inside a `Mods` folder. Copy a finished package there yourself, with the game closed.

## Which scripts use what

| Script | Java / FFDec | Game install | DBPF reader |
|--------|--------------|--------------|-------------|
| `flash/extract_ea_movies.py` | no | yes | yes |
| `flash/extract_uicheats_bases.py` | no | no | yes |
| `flash/rebuild_all.ps1` | yes | no | no |
| `flash/build_uicheats_compat.ps1` | yes | no | no |
| `flash/gate_pcode.py` | yes, for exports it has not made yet | no | no |
| `flash/gate_compat_pcode.py` | yes | no | no |
| `flash/build_ui_package.py` | no | yes, to copy EA's index conventions | yes |
| `flash/build_compat_package.py` | no | yes, to copy EA's index conventions | yes |
