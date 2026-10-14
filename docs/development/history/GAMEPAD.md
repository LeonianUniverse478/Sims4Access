> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# Gamepad support

The PC client never reads gamepads (proven 2026-08-26: hot-plugged and
connected-before-boot, zero input reaches the UI either way, with the full
console nav layer live). The pad is read by `tyjokr_a11y_keys.py` via XInput
(`XInput1_4` -> `xinput1_3` -> `XInput9_1_0`) on the same polling thread as
the keyboard, and drives the same message channel. Toggle: `a11y.gamepad
on|off` (settings key `gamepad`, default on).

## Architecture since v17 (2026-08-27): EA's own input-action pipe

The pad no longer drives narrator messages directly. Each button becomes an
`olympus.constants.ActionCodes` value delivered as `A11yActD<code>` (press) /
`A11yActU<code>` (release); the Flash bridge feeds it to
`CallUIService("HighPriorityActionInput"/"LowPriorityActionInput",
{actionCode, isDown})` under the UsingController sandwich - the EXACT doorway
the console client uses, decompiled from InputActionManager. EA's adapters
consume the code with all their context logic (panel focus pushes, held-key
repeat, per-mode overrides). If nothing consumes a press, the bridge falls
back to the old walker action, so the pad always does something sensible.
Narration hooks NavManager's "ChangedCurrentFocusable" event (NavManager
extends EventDispatcher), so ANY focus change narrates regardless of what
drove it.

Base ActionCodes: CONFIRM=1 BACK=2 TOGGLE_MAIN_MENU=3
TOGGLE_VIRTUAL_CURSOR_MODE=4 NAVIGATE_UP/DOWN/LEFT/RIGHT=5/6/7/8
TAB_LEFT/RIGHT=9/10 TRIGGER_LEFT/RIGHT=11/12 DELETE=13 CONTEXT_MENU=14
HELP_MENU=15 TOGGLE_GRID=16 TOGGLE_CHEAT_CONSOLE=17 (context classes like
GameplayActionCodes are semantic aliases over the same numbers).

## Current mapping (interim, narrator actions)

| Input            | Action code / action                               |
|------------------|----------------------------------------------------|
| D-pad            | NAVIGATE_UP/DOWN/LEFT/RIGHT (5-8)                  |
| A                | CONFIRM (1)                                        |
| B                | BACK (2)                                           |
| LB / RB          | TAB_LEFT / TAB_RIGHT (9/10) - panel cycling        |
| View (Back)      | TOGGLE_VIRTUAL_CURSOR_MODE (4) = Toggle Menus/Game |
| Menu             | TOGGLE_MAIN_MENU (3)                               |
| X                | read current (Python speech, no code)              |
| Y                | cycle speech mode (Python speech, no code)         |

Fallbacks when EA consumes nothing: 5/6->walker arrows, 7/8->walker
prev/next, 1->activate, 2->NavBack, 4->NavEnter descent.
Free: sticks, stick clicks, triggers (11/12 reserved), Start=none yet.

## EA's official console maps (for future NavManager-proper mapping)

Source: simscommunity.info/2018/07/30/the-sims-4-console-getting-started/
(Xbox names; PS is positionally identical: Cross=A, Circle=B, Triangle=Y,
Square=X, Share=View, Options=Menu.)

### Live mode
- LT / RT: Snap to Sim Left / Right
- LB / RB: Decrease / Increase Game Speed
- View: Toggle Menus/Game        <- EA's UI-focus entry gesture
- Menu: Pause Menu
- LS: Move Cursor (the virtual cursor; why probes show cursorMode=true)
- L3: View Controls
- RS: Zoom / Rotate Camera; R3: Toggle Follow Camera
- D-pad: Left=Select Next Sim, Up=Upper Floor, Down=Lower Floor,
  Right=Cycle Wall Cutaway
- A: Select; B (hold)+LS: Pan Camera; Y: Cancel Current Action; X: unused

### CAS
- LT / RT: Undo / Redo; LB / RB: Cycle Outfit Categories
- LS: Move Cursor; L3: View Controls; RS: Rotate Sim
- A: Catalog Options; A (hold)+LS: Modify Body; B: Back;
  X: Toggle Catalog Menu; Y: unused

### Build/Buy
- LT / RT: Undo / Redo
- LS: Move Cursor; L3: View Controls; RS: Zoom/Rotate; R3: Toggle Grid
- D-pad: Left=Toggle Top-down, Up=Upper Floor, Down=Lower Floor,
  Right=Cycle Wall Cutaway
- A: Select; B: Back (hold +LS: Pan Camera); Y: Quick Eyedropper;
  X: Quick Design Tool

## Design notes

- Our D-pad deliberately diverges from EA's live map: focus walking beats
  wall-cutaway shortcuts for a blind player. A=confirm / B=back / View=enter-UI
  follow EA exactly.
- EA's live-mode d-pad shortcuts (next sim, floors, walls) and bumper game
  speed are client actions; Python can reproduce several (clock speed, next
  sim) but NOT from the polling thread - needs a sim-thread trampoline.
  Candidates for bumpers/triggers once that exists.
- Y currently cycles speech mode; EA live uses Y for Cancel Current Action.
  Revisit when interaction-queue control lands.
