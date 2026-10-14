# Ctrl+Alt+L: logging on or off (2026-09-30)

Leo asked for a key to turn diagnostic logging on and off without the cheat console (a11y.log on/off still works).

- New chord Ctrl+Alt+L (intent `logging`). It toggles the settings window's Logging row through `menu._change`, so it is saved and applied exactly as that row is (speech.log_enabled and the cfg `logging` value). It then speaks "Logging: on" or "Logging: off" with the existing lang terms.
- A text field keeps the key. Dialogs and menus do not block it, since logging does not change what owns input.
- It runs on the pump. With no pump (before a zone), it runs directly: it touches only the mod's own speech and settings state, no game APIs.
- The player default is unchanged (logging off).
- Files: Scripts/tyjokr_a11y_keys.py, Scripts/tyjokr_a11y_shortcuts.py, CONTROLS.txt, docs/patreon/03, tools/test_logging_shortcut.py (3 tests). tools/test_scanner_v5.py adds L (0x4C) to its pinned chord list, dated like the others.

## Evidence

- `Dev.ps1 build` exit 0, dist `2026-09-30_182828`. passed true, input_stable true, 1,336 checks across 87 suites. Main and compat fidelity gates PASSED (19 targeted comparisons). UI package unchanged from dist 2026-09-30_180756.
- SHA256: TS4_Access.ts4script `b1c947c00928d4c18cea55d2cf61c036c075cad906eca40c7ad2908d6bd64414`, TS4_Access_UI.package `0a7fad07df85172c741dadff134c427e383f298034a3ac242fe691b3e847e7f5`.
- Installed to Leo's Mods root on 2026-09-30 after the game was confirmed closed (an earlier attempt stopped because TS4_x64.exe was running); hashes verified. Live testing pending.
