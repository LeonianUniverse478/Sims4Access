# Verbosity setting (2026-09-30)

## Behavior change

A new setting, Verbosity, appears in the accessibility settings window (the row after Braille mode) and in the cfg as `[speech] verbosity`.

- **Full** (the default, today's behavior) says what a thing is before its name: the scanner's "Category." and "Subcategory.", "Dialog." for dialogs and dialog-scope openings, and "Menu open." before a menu's option count.
- **Brief** says only the names: "Plumbing, 12 items. 3 of 9." and "5 options.".

Counts and positions are the same in both. Scanner items never had a kind word. The "Scanner." announcement when scanner mode starts stays, because it reports a mode change rather than naming a thing. Existing players keep Full unless they choose Brief; a bad cfg value keeps the default and is reported in load_errors.

## Files

- Scripts/tyjokr_a11y_settings.py: default, cfg map, parse validation, template line, render, and `brief()`.
- Scripts/tyjokr_a11y_menu.py: settings-window row (choice full/brief), localized value text.
- Scripts/tyjokr_a11y_scanner.py: `_kind()` for the category and subcategory prefixes.
- Scripts/tyjokr_a11y_narrator.py: dialog, scope and menu-open prefixes; `a11y.settings` readout line.
- Scripts/tyjokr_a11y_lang.py: terms verbosity, verbosity full, verbosity brief (en and pl).
- README.txt, docs/patreon/03.
- tools/test_verbosity.py (8 tests, driving the real scanner tree and narrator handlers).

No Flash change.

## Evidence

- `Dev.ps1 build` exit 0, dist `2026-09-30_124627`. `build/v10-checks.json`: passed true, input_stable true, 1,274 checks across 81 suites.
- Main fidelity gate PASSED; compat fidelity gate PASSED (19 targeted comparisons). UI packages are unchanged from the inventory round (no Flash change).
- SHA256: TS4_Access.ts4script `53b7bc286b8c6379c0383ebb401fc77707b1b5eef0923076d95c7c579d438055`, TS4_Access_UI.package `4b7ecf0e9ecacbd99b117a87b3abe50820e326f8425ec7d531f8d30dc8548d56`.
- Installed to Leo's Mods root on 2026-09-30 with the game closed; hashes verified; cfg unchanged (the verbosity line is written the next time a setting is saved). Live testing pending.

## Live result

2026-09-30: Leo changed the Verbosity option in the accessibility settings window. The earlier menu report was not a bug; the settings row is inside the menu.
