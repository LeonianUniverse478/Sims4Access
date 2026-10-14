> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# Startup access: investigation and separate probe

V9 note: this probe package is based on V7. It is not installed with V9 and
must be rebased before a combined test; its old UI package would replace
the newer keyboard fixes. The investigation below remains unresolved.

## Current conclusion

The normal V7 build still needs a loaded save for speech/navigation delivery.
Glaroc's build also does not narrate the main menu. His save-slot-copy
workaround does not solve this and is not adopted.

Earlier notes stated that both bridge directions were certainly dead before
a zone existed. The observed silence does not independently prove that:
the UI listener, narration trigger and transport need separate checks.
The read-only EA source review found another possible path to test:
Flash registers `ui.*` commands through `RegisterDebugCommand`, while Python
exposes native `commands.describe` and `commands.execute`. Whether those
registries meet before a save loads is **unknown**. The probe tests that
premise, without hooks into protected native code.

## What the probe does

- A visible badge proves the patched Gamedata TooltipManager reached a stage
  and receives frames. It identifies the winning class copy.
- F10 increments a counter using EA's native InputAction system, independent
  of the Python keyboard poller. It does not activate a menu item.
- Flash sends a unique `a11y.startup_probe` command every five seconds.
- The separate Python module logs when imported and when a real core tick
  runs. It records whether a zone/client exists, independently of speech.
- On the simulation thread, it queries and executes only the fixed
  `ui.a11y.startup_probe` debug command, at five-second intervals for at most
  three minutes per zone/client state. The badge's debug counter is the
  evidence of actual delivery; a Python return value alone is not proof.
- When Python receives the Flash ping it logs it and queues a UI reply.
  The badge turning `Python reply: true` proves the reply reached Flash.

No save changes, runtime dumps, EXE inspection, code detours, external network
connections or clipboard changes. The probe does not provide startup speech.

## Artifacts and optional test

The probe is **built and gated, but not installed**. Its artifacts are under
`build/startup-probe-v7/`. The gate passed two targeted comparisons across
1,077 Gamedata classes; package verification confirmed only Gamedata differs
from the normal V7 UI package:

- `tyjokr_StartupProbe_V7_UI.package`: a full 24-movie replacement UI package.
  Only ClassLibraryGamedata differs from the normal V7 package.
- `tyjokr_StartupProbe_V7.ts4script`: optional Python diagnostic module.
- `verification.json`: hashes and sizes, written only after verification.

To test with the game closed, keep the normal V7 UI package safely outside
Mods, then put the probe UI package in its place and add the probe ts4script
beside the normal ScreenReader ts4script. Keep the normal script and existing
UI Cheats compatibility package installed. Do not install two competing main
UI packages. This optional test is for a sighted helper/developer because the
badge itself does not speak.

1. Launch from a fully closed game. Wait at the main menu for 30 seconds.
2. Note the badge counters; press F10 once and check its counter changes.
3. Load a save and note which counters change. Return to the main menu and
   repeat. Keep `startup-probe-v7.log` beside the ScreenReader log.
4. Quit, remove both probe artifacts, and restore the normal V7 UI package.

Interpretation:

| Result | What it establishes |
|---|---|
| No badge | The probe's UI/stage setup did not complete; not evidence that Python transport is gated. |
| Badge ticks, F10 changes | UI hook and native input work in that state. |
| Python imported, no core ticks | The Python module loaded, but this callback does not run in that state. |
| Flash ping appears in log | Flash-to-Python commands work in that state. |
| Python reply true | The distributor reply reached Flash. |
| Debug counter increases | Native command execution reaches the UI command handler. |
| Registry sentinel appears in log | Python can see the diagnostic UI command description. |

No row in this table has an in-game result yet. A failed path should not be
promoted into a statement that all possible startup bridges are impossible.
