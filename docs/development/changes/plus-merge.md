# TS4 Access Plus merged (2026-10-08)

Michael Maslo, a friend of Leo's, contributed TS4 Access Plus, a separate add-on built against tyjokr's original TS4 Access (Documents\Sims4_Accessible_Pack (2).zip): TS4_Access_Plus.ts4script, 15 Python modules in its source folder, a changed TS4_Access_UI.package and guides. Leo asked for everything the add-on has that his build lacks to be merged into his code.

## Review

- **Design:** an add-on that uses TS4 Access's speech, pickers (UiObjectPicker), pie-menu opener (A11y|pick), Build cursor projection (A11y|buildaim, build|off, build|undo), placement and sell helpers (tyjokr_a11y_place), lot prices (a11y.lotprice_enc) and keyboard fence. It runs its own pump alarm and an Alt-key GetAsyncKeyState thread.
- **Build mode:** the build helper drives EA's own Build tools with real mouse moves, drags and clicks (SendInput, mouse_event) and with keys (keybd_event: B for the Wall Tool, Page Up and Down for floors, Escape and K). There is no Python API for walls. Screen points come from TS4 Access's buildaim reply, read by temporarily wrapping tyjokr_a11y_build._say. That still matches this build's English text, which it receives even in Polish. The drawing module also reads screen pixels to find a hover highlight.
- **Catalog bridge:** in the add-on's UI package, the bridge was patched into gamedata.shared.ResourceKey in all 25 movies. It was not in the TooltipManager.as source it shipped, and it used ++ against GFX-SAFETY.
- **Version mismatch:** the shipped source is 0.7.0, the compiled script 0.7.1. The 0.7.1 changes are the log copy in the Windows user folder and room_worker's wait, undo and retry. They were rebuilt from the compiled bytecode; room_worker compiles to identical bytecode.
- **Safety:** no network, subprocess, eval or game saves. Files written are its log, settings (TS4_Access_Plus.cfg) and room names (TS4_Access_Plus_rooms.txt). Selling goes through TS4 Access's own sell helpers after a confirm. The package's prism.dll and TS4AccessHelper.exe were not run or installed.

## What was merged

- **Modules:** Scripts/tyjokr_a11y_plus_{core, menu, needs, notify, time, rooms, sims, family, build, house, furnish, decor, draw}.py, renamed from a11yplus_*. They are loaded one by one by Scripts/tyjokr_a11y_plus.py, which keys.py imports at startup, so one failure cannot stop the others.
- **Not merged:** a11yplus_queue duplicated TS4 Access's action queue, so Alt+Q opens hub.action_queue instead.
- **Catalog bridge:** rewritten into TooltipManager_patched.as as `A11yPlusHandle`, `A11yPlusError`, `A11yPlusReply`, `A11yPlusCatalog` and `A11yPlusSelect`, dispatched from `A11yHandleEncoded` for "A11y|plus|...". It uses int counters with `x = x + 1`, wraps its entry point in try/catch, and replies through A11yPostToPython("a11yplus.flash").
- **Files:** core.IN_GAME limits the log, settings and room-name files to the installed mod, so importing from the kit (offline tests) writes nothing.

## Overlap with this build

- The Alt keys do not collide with TS4 Access, whose chords need Ctrl+Alt (the add-on ignores keys while Ctrl is held). keys._plain_message returns nothing while Alt is held, so Alt+arrows do not also move the scanner or the Build cursor.
- Duplicates kept on purpose:
  - Alt+N (percentages) next to Ctrl+Shift+N (the needs panel).
  - Alt+T (work, school and bills) next to Ctrl+Alt+C.
  - Alt+W (room names) next to the scanner's W.
- The drawing cursor (Alt+arrows) is separate from the RimWorld-style Build cursor. The friend's build helper and Leo's Build cursor can both be used, but not at the same moment.

## Files

- New: the 13 modules, Scripts/tyjokr_a11y_plus.py, tools/test_plus.py (6 tests) and tools/test_plus_bridge.js (8 checks).
- Copied to docs/plus: the add-on's guides, changelog and JAWS key file (TS4_x64.jkm, which passes arrows to the game under JAWS).
- Changed: Scripts/tyjokr_a11y_keys.py (the loader import), flash/TooltipManager_patched.as and CONTROLS.txt.

## Release text

stage_release.py forbids "Claude" in shipped strings. Four of the add-on's failure messages said "Tell Claude."; they now say "Send the TS4_Access_Plus.log file from the Mods folder for help."

## Not live-tested in this build

All of it. The friend's changelog records live tests against tyjokr's original TS4 Access, not this build.
