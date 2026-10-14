> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# Screen Narrator: what ships

Everything installs as one folder: `Mods/tyjokr_ScreenNarrator/`.
Script mods load from the Mods root or **one** subfolder deep, so this folder
must not be nested any further.

## Required files

| File | Purpose |
| --- | --- |
| `tyjokr_ScreenNarrator_UI.package` | Patched EA UI movies (21 of them) that report what is on screen. |
| `tyjokr_ScreenNarrator.ts4script` | All mod logic: narration, speech backends, keyboard navigation, object names, Sim actions. |

Without the package the mod is silent (nothing feeds it). Without the
ts4script the package is inert (nothing speaks).

**Updating from the 2026-08-01 four-script build:** delete the old
`tyjokr_ScreenNarrator` folder first (or at minimum the `_SimActions`,
`_Keyboard` and `_ObjectNames` ts4scripts). A stale copy would shadow the
merged modules, because only the first-loaded copy of a module name runs.

## Options

Features are toggled in-game or by editing `tyjokr_ScreenNarrator.cfg` next
to the ts4script: a commented, Notepad-friendly INI file (sections, on/off
words, key names). A default copy ships in the zip, and the mod regenerates it on launch if it
is missing. Every in-game command writes through to it, `a11y.reload`
applies a hand-edit while the game runs, and deleting it resets everything.
Note for updates: extracting a new release over the folder replaces the cfg
with defaults, so users who tuned settings should keep their cfg aside and
drop it back after updating. A settings file from the older JSON format
is imported automatically on first launch and renamed `.old`.

| Command | Option | Default |
| --- | --- | --- |
| `a11y.simactions on\|off` | Announce what the active Sim starts doing. | off |
| `a11y.objectnames on\|off\|redo` | Name tooltips on gameplay objects. | on |
| `a11y.keys on\|off` | Keyboard focus navigation. | on |
| `a11y.speechmode hover\|manual\|beeps\|off` | Speech modes: hover speaks everything as you point; manual stays silent until the read-current key; beeps replaces speech with a short tone; off is silent. Also cycled by the speech-mode key. | hover |
| `a11y.autofocus on\|off` | Whether a new pie menu or dialog grabs the focus ring immediately, or only after the first navigation keypress. | off |
| `a11y.voice rate\|volume\|name\|list\|reset` | SAPI fallback voice only (rate -10..10, volume 0..100, voice by partial name: david, zira, hazel). Screen reader users control their voice in their screen reader instead. | rate 1, volume 70, zira |

Keys are fixed (rebinding was removed as too confusing): next is Numpad 6 or
backslash; previous is Numpad 4 or minus; activate is Numpad 5 or Enter;
clear is Numpad period or either slash; read current is Numpad 8 or equals;
speech mode is Numpad 9 or Insert.

While a dialog or picker is open, the **arrow keys** also navigate (up/left =
previous, down/right = next). They are ignored everywhere else, including pie
menus, because the game only locks the camera for dialogs and pickers; in a
pie menu the arrows still pan the camera, so use the numpad keys there.

Holding a movement key (next/prev or an arrow) auto-repeats after a short
delay, so long lists can be scrolled by holding instead of tapping. Activate
and clear never repeat.

The non-numpad alternates make the mod fully usable on keyboards without a
numpad. They were audited against the community controls list
(carls-sims-4-guide.com/controls.php) so they collide with nothing the game
binds; do not add default keys that appear there (backtick was once the prev
alternate and silently toggled Pause).
| `a11y.braille <concise\|full\|only\|off>` | Braille output mode. | concise |
| `a11y.log on\|off` | Mod-debugging log. | off |
| `a11y.settings` | Read out every option and its current value. | |

`a11y.test`, `a11y.speak <text>`, `a11y.status` and `a11y.objdiag <name>`
remain as diagnostics but are deliberately left out of the user-facing
README (support can still ask a user to run them).

## Speech backend files (`speech/` subfolder)

| File | Purpose | Required? |
| --- | --- | --- |
| `speech/Tolk.dll` | Routes speech to JAWS, NVDA, Window-Eyes, ZoomText, SuperNova, System Access, with SAPI fallback. | Recommended |
| `speech/nvdaControllerClient64.dll` | NVDA client, loaded by Tolk (and directly, if Tolk is absent). | With Tolk |
| `speech/SAAPI64.dll` | System Access client, loaded by Tolk (and directly, if Tolk is absent). | With Tolk |
| `speech/Tolk-LICENSE.txt` | Tolk is LGPL: this must be redistributed. | **Yes, if shipping Tolk** |
| `speech/Tolk-LICENSE-NVDA.txt` | Licence for the NVDA controller client. | **Yes, if shipping Tolk** |

The folder name is not load-bearing: the DLLs are found in `speech/`, at the
mod folder root, or in any other subfolder of the mod folder, so renaming or
reorganizing does not break screen-reader routing. Nothing in the mod hardcodes
the game's user folder name either (localized installs like "Les Sims 4" are
fine; every path derives from where the ts4script actually loaded from). If all
speech DLLs are omitted the mod still works, falling back to Windows'
built-in speech (SAPI) through PowerShell. Backend precedence is
Tolk -> NVDA -> System Access -> SAPI -> log-only.

## Generated at runtime (do NOT ship)

- `tyjokr_ScreenNarrator.log` — utterance/diagnostic log, written next to the
  ts4script.
- `tyjokr_ScreenNarrator.cfg` — the user's options. Keep it when updating
  the mod; deleting it resets options to defaults.

## Braille (deafblind support)

Requires `Tolk.dll` and a braille display supported by the running screen
reader. Control with `a11y.braille <mode>`; run it with no argument to see
the current mode and whether a display was detected.

| Mode | Behaviour |
| --- | --- |
| `concise` (default) | Speech reads everything; braille shows just the label. A display is ~40 cells, so full descriptions overflow it. |
| `full` | Speech and braille both get the full text. |
| `only` | Braille only, speech suppressed. |
| `off` | Speech only. |

`a11y.status` also reports display detection and current mode.

## Requirements and limits

- Windows only. macOS is not supported yet (speech backends and the keyboard
  layer are Windows-specific).
- Script mods must be enabled in Game Options.
- NumLock on for the default keyboard navigation keys.
- The main menu is **not** narrated: the game's UI layer has no way to reach
  the mod before a save is loaded. Narration begins once a lot loads.

## Rebuilding

```
py -3.7 compile.py                                  # dev build -> Mods subfolder (log ON)
py -3.7 compile.py --release                        # distribution zip -> dist\ (log OFF)
powershell -File flash\rebuild_all.ps1 -WorkDir <dir with gfx\ea_*.swf>
python flash\build_ui_package.py <same WorkDir>     # package
python flash\deploy_package.py                      # package -> Mods subfolder
```

A release build assembles the full install layout (ts4script with the
utterance log default off, UI package, `speech/` DLLs + licences) into
`dist\tyjokr_ScreenNarrator_<date>.zip` and leaves the local Mods install
alone. Stored settings always override the build default, so `a11y.log on`
persists even on release builds.

After an EA patch, re-extract the `ea_*.swf` originals from the new
`UI.package` before running `rebuild_all.ps1`.

## Building Tolk (only if it needs rebuilding)

Upstream ships no binaries. With VS 2022 Build Tools and a JDK present:

```
call "<VS>\VC\Auxiliary\Build\vcvars64.bat"
set INCLUDE=%INCLUDE%;<jdk>\include;<jdk>\include\win32
cd tolk-master\src && nmake
```

A prebuilt copy plus the two client DLLs and both licences is archived in
`tolk/` next to this file.
