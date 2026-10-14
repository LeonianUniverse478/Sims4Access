# Mood reader and clock funds (2026-09-28)

## Behavior changes

1. **Ctrl+Alt+E reads the whole mood panel at once.** Previously it moved keyboard focus into SimHub, where moodlets were not usefully readable. Now it speaks the mood name and its description, then every moodlet with its name, mood effect (for example Happy +1), boost text if any, time left, reason and full description. The Accessibility menu's "Mood and moodlets" row does the same. With no live SimHub (Build Mode, main menu) it says "Mood is not available right now." Focus no longer moves into the panel.
2. **Ctrl+Alt+C also reads household funds** after the day and time, using the existing hub funds text ("Household funds: 12,345 simoleons"). With no active household (main menu) the clock reads alone as before. The funds line also follows "The day and time are not available right now."
3. **Kit fix:** `tools/stage_release.py` defined an unused `WORKSPACE = ROOT.parents[1]`, which raised IndexError when the kit sat directly under a drive root, such as `C:\TS4AccessDev` from START-HERE. The line was removed; nothing referenced it.

## Design

- `flash/extra-classes/MoodContainer.as` (SimHub is the only definer) gains `A11yReadMood`, `A11yBuffRecord`, `A11yBuffTime`, `A11yPlain` and `A11yPostMood`. They read `GameplayStateData.AllBuffInfo` and compose each field exactly as EA's `BuffTooltip.SetData` / `ProcessTimeSpanText` do (1.128.90 decompile), including override boosts and transition-buff timeout strings. All newly imported classes (BuffInfo, BuffStaticData, Keys, KeysGP, LocKey, TimeSpan) are defined in SimHub itself. Counters are `int`, and added code uses no `++` or `--`.
- `TooltipManager_patched.as` `A11yMood` only calls `hub["mcMoodContainer"]["A11yReadMood"]()` by name, so none of the other 22 movies resolves the buff classes. If the hub is not live it posts an empty `a11y.mood_enc`.
- Transport: records are separate `a11y.mood_enc` posts (M header, B per moodlet, E end), each capped at 1400 characters before encoding, with the description last so the cap only shortens it. The command was added in all three startup places: the Flash allow list, `CHANNELS` and `_dispatch`.
- Python (`narrator.a11y_mood_enc`) assembles one reading per sequence number, ignores stale or partial ones, sorts as `BuffDisplay.BuffSort` does, and speaks once. New lang terms: `mood unavailable`, `no moodlets` (en and pl).

## Offline evidence

- `Dev.ps1 build` exit 0, dist `2026-09-28_094711`. `build/v10-checks.json`: passed true, input_stable true, 1,230 checks across 77 suites. The new suites are `tools/test_mood_reader.py` (9 tests) and `tools/test_mood_reader.js` (11 checks); `tools/test_clock_shortcut.py` gained 2 funds tests.
- Main fidelity gate PASSED; compat fidelity gate PASSED (19 targeted comparisons).
- SHA256: TS4_Access.ts4script `b585e80a10fe980fb1ce8c813d47dc9b935ff1e8baad4b163fa8aac83162de02`, TS4_Access_UI.package `57115170de17ffcd5030c085247d8cb77c54867bf163ca55bb84809013f9de3c`, compat package `ba203183dc753359bb7c271a9a3ea669e77188cb806642d20177f353433e6b44`.

## Live testing

2026-09-30: Leo reported that the installed build works (mood reader and clock funds). Details still to record: screen reader and voice, save context, and which of the cases below were tried.

Original note: The pair above was installed to Leo's Mods root (flat layout, existing cfg and speech pack kept) on 2026-09-28 with the game closed, and the hashes were verified. Nothing has been launched yet.
