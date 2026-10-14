# Current architecture and lessons to preserve

## Two halves of one mod

`Scripts/` compiles to TS4_Access.ts4script using Python 3.7. The game loads those modules. `flash/` supplies ActionScript patches compiled into GFX resources in TS4_Access_UI.package. Much of the accessibility work needs both halves: Python cannot inspect every native picker on its own, and the UI needs Python for narration and game actions. Always identify the owning UI surface and transport before changing behavior.

The optional UI Cheats compatibility package replaces six resources that both mods override. Whole-resource load order matters; installing two unrelated packages that both replace a movie does not combine their edits. The compatibility build starts from UI Cheats' movies, then injects our patches. It must follow both packages in load order.

## Where to work

| Area | Main source |
| --- | --- |
| Key poller, hooks, input ownership, shortcuts | Scripts/tyjokr_a11y_keys.py |
| Simulation-thread queue | Scripts/tyjokr_a11y_pump.py |
| Speech, screen reader/Prism, SAPI, braille | Scripts/tyjokr_a11y_speech.py |
| UI narration commands and context reports | Scripts/tyjokr_a11y_narrator.py |
| Pre-lot socket transport and startup lifecycle | Scripts/tyjokr_a11y_startup.py |
| Scanner tree and object/Sim interactions | Scripts/tyjokr_a11y_scanner.py |
| Accessibility hub / shortcut reader | Scripts/tyjokr_a11y_hub.py, tyjokr_a11y_shortcuts.py |
| Settings, localization | Scripts/tyjokr_a11y_settings.py, tyjokr_a11y_lang.py |
| Phone, travel, native/simple picker bridges | Scripts/tyjokr_a11y_phone.py, tyjokr_a11y_travel.py, tyjokr_a11y_native.py |
| Build cursor, catalog, placement | Scripts/tyjokr_a11y_build.py, tyjokr_a11y_grid.py, tyjokr_a11y_place.py, tyjokr_a11y_buycat.py |
| Shared UI scope/focus/navigation | flash/TooltipManager_patched.as |
| Dedicated panel/picker hooks | flash/extra-classes/*.as |
| Prelaunch helper | helper/ScreenReaderHelper.cs, ScreenReaderHelper.Core.ps1 |

## UI routing and transports

The shared TooltipManager finds the actual visible owner and manages navigation scopes, focused controls, async list indexing, pending scopes, focus rings, and native key guards. Loaded widgets can remain cached after their contents close: "loaded" and "visible owner" are not equivalent. Dialog managers, popup filters, dropdowns, the phone alert, and selected HUD panels need their own visibility checks.

The main menu/CAS/Manage Worlds can run before a loaded-zone simulation pump. Startup messages cross a local socket path; loaded-zone actions use game commands/distributor messages. Add commands to both the Flash startup allowlist and Python startup channel/dispatch maps when applicable. Validate payloads, retain state-message priority, and test before the first save load. Do not assume a new command registration alone reaches the startup path.

`a11y.modalstate` remains two digits (navigation owner and text editing). The native game command path can remove leading zeros, so direct values `0`, `1`, `10`, `11` are normalized. Context strings carry a three-digit suffix including a separate blocking bit, and `a11y.blocking` sends that bit separately. The extra transport provides redundancy; do not turn it into an ambiguous bare three-digit numeric command. Duplicate reports must be idempotent and a changed owner without explicit permission must fail conservatively.

The phone alert and ordinary HUD navigation own keys but are not blocking dialogs. Ctrl+Alt+P must not mistake the incoming alert for something to close. A real dialog, picker, pie menu or dropdown blocks recipient switching. Recheck this on the simulation thread immediately before executing a queued request. Do not rely solely on state observed when the hook saw the key.

## Keyboard traps already found

Physical held-key state must be separate from whether Ctrl+Alt currently enables a chord. Otherwise adding modifiers to a previously held H can open the accessibility hub, or releasing/repressing modifiers can retrigger a held shortcut. The focus-return fix suppresses stale held keys and background taps until a release/fresh press. Preserve low-level-hook edge deduplication, swallowed-release masking, input epochs, opening-key fences, AltGr handling, and cancellation of stale repeat timers.

Tests originally covered individual shortcuts but missed these histories; one test even expected a second action when modifiers were added to a held arrow. Use sequence tests, not only a direct call to a shortcut dispatcher. The relevant suites include test_keyboard_modifier_reentry, stale_release, chord_race, phone_guard_blocking and phone_owner.

## UI compiler traps

See GFX-SAFETY.md. Do not infer correctness from a .as export or a GFX signature alone. FFDec can change integer operations and introduce native crashes even when decompiled code looks equivalent. The main/compat pcode gates, non-code tag equality, class-set equality, resource round-trip comparison and live tests serve different purposes. CASCustomizer is explicitly excluded after reproducible rebuild crashes. Do not expand the override set to every movie with a similarly named class.

## Python/game compatibility

The game embeds a trimmed Python 3.7 environment. Desktop Python may offer packages absent from base.zip/core.zip/simulation.zip. The bundled ctypes source is intentional. Some imports are optional with ImportError guards; a broad `except Exception` is not proof a required dependency is optional. Use the game's actual APIs and test the native flow rather than inventing equivalent actions.

LeonianUniverse's simplified gameplay menus were incorporated selectively: native game tests, disabled reasons, prices, selection limits and outcomes remain authoritative. CAS and Stories keep their existing controls. Do not include cheat/appearance-editor scope just because older prototypes contain it.

## Source status at handoff

The runtime and canonical shared UI match candidate 2026-09-26_2209: recipe/picker fixes, scanner/build work, modifier/focus fixes, phone blocking distinction and the new clock reader. Phone and clock changes were reviewed offline, with 1,187 checks across 73 suites at that time; they were not yet declared live verified. Tool portability and source-exchange checks add to that historical count without changing game behavior.

The current workflows in START-HERE.md supersede old release/deployment scripts. Historical records under history retain debugging evidence, tests and prior failed approaches; dates, game versions and file counts in them must be interpreted in context. No collaborator should assume every old issue is still open or every old build is safe on the current game.
