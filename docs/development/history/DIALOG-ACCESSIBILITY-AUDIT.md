> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# Dialog and picker accessibility audit (2026-09-15)

## Status and user requirements

The user subsequently said "fix them" and requested a broader keyboard
navigation sweep. The rebuild hold is over. V6 fixes passed the build,
fidelity and artifact checks and are deployed for testing. In-game validation
is pending. First-install settings/onboarding remains deferred.

The findings below describe the pre-v6 defects. The implementation section
records the fixes; the runtime checklist in SCANNER-TEST.md remains pending.

## V6 implementation

- Dialog footer and DialogButton wrappers are traversed to their real visible
  buttons. Disabled controls can be read but cannot be activated. Tooltip
  descriptions are included with the focused control.
- Focus follows the displayed DialogManager request and LayoutManager's top
  modal widgets, including queued/client-only dialogs. An empty/unready modal
  retains its scope; navigation cannot fall through to background controls.
  Closing a scope restores a live prior scope. Ctrl+Alt navigation belongs to
  the modal before the world scanner; R reads the dialog, Backspace uses the
  game's permitted dismissal path.
- Picker navigation retains a logical row index and ordered pending presses.
  It reveals the requested row using actual viewport bounds and slider range,
  with a rendered-cell recheck. There are no page/wheel nudges in this path.
  Footer actions become reachable at the true data boundary. Picker focus is
  refreshed after its child movie loads.
- AgeUpPanel now has dedicated hooks for successive age-up/trait-reassignment
  dialogs and trait/aspiration subpanels. Trait removal is a separate focusable
  action. Native text entry owns typing keys. Required selections and the
  game's Done/Cancel rules are preserved.
- Keyboard UI messages now cross the simulation-thread pump. Polling is 10 ms;
  native chord transitions retain taps completed between polls and avoid
  duplicate hook/poll delivery. Text entry excludes ordinary typing keys from
  navigation. Focus changes cancel obsolete scroll work.
- Tolk returning failure now falls back to direct NVDA, then Windows speech.
  Offline checks cover Polish text. This does not diagnose the tester's
  original silent installation without their log/version.
- An ABC audit found **135 actual TooltipManager definers** across the game's
  258 UI movies. This is an inventory, **not a coverage gap**: prior in-game
  marks establish that ClassLibraryGamedata wins the shared class, including
  in CAS. The initial expansion to 135 was stopped before deployment following
  the user's correction. V6 ships the **original 23 movies plus AgeUpPanel**,
  and six UI Cheats overrides. Only AgeUpPanelMain is patched in AgeUpPanel;
  its shared classes stay original. EngagementLibrary and all CAS movies are
  excluded. The wider audit is retained for reference only.

Evidence: tools/test_navigation_v6.py (9 passing checks),
tools/test_scanner_v5.py (9 passing checks), build/ui-class-audit-v6.json,
flash/chain-navigation-v6-final.log (61 main comparisons passed, CHAIN DONE),
flash/gate-compat-v6.log (19 passed), build/v6-verification.json and
build/v6-deployment.json. Installed sizes/hashes are in the handoff. All 30
resources and 12 Python modules passed artifact checks; cfg was preserved.

The pump change is intentional thread-safety work, not an established cause
of the reported missed keys: Distributor._send_view_updates reads then clears
the shared journal without a lock, while the old poller could append to it.
Routing through the pump avoids that race and works while gameplay is paused.
It explicitly requires a live lot's pump; no pre-lot delivery is claimed.

Not implemented in this fix: glaroc's server-side dialog-answer fallback,
pre-lot/main-menu input delivery, or CAS's separate-stage support. His six
specialized picker movies sharing PickersMain is not evidence that each needs
a separate focus hook. Runtime coverage still has to be tested per family.

The user's requirement is **every dialog must be usable**, rather than
coverage limited to a few named pickers. Reading all text in a popup does
not establish accessibility: players must be able to reach and operate each
action, finish required selections, and return to gameplay without a mouse.

For all pickers, the user reports skipped rows, slow movement, missed first
presses, and getting stuck at the edge of the visible items. They want smooth
sequential navigation with automatic scrolling. The earlier acceptance of
scroll nudges/stutter in TODO-NEXT-SESSION.md is superseded by this request.

## Reported failures

| Family | Report | Investigation status |
|---|---|---|
| Likes/Dislikes | Body and Yes/No/OK read as one control; navigation and activation fail; game remains paused | Shared dialog traversal and button-target defects found; specific instance still needs reproduction |
| Discovery Quests | Finish Quest, Cancel and another action inaccessible as separate controls | Same shared defects are relevant; exact footer and actions need runtime confirmation |
| Phone replies | After answering the phone, dialog text/buttons inaccessible | SimInteractionDialog uses SimSpeechFooter, which inherits DialogButtonFooter; individual DialogButton wrappers are a confirmed activation issue |
| Self-discovery | Popup cannot be read/answered | Need reproduce both the decision popup and any subsequent selection dialog |
| Work chance cards | Dialog cannot be read/answered | Generic DialogContainer has explicit chance-card support; shared traversal/activation needs fixing and runtime verification |
| Trait swap / reassignment | User suspects missing support | Trait reassignment is explicitly implemented by the unpatched AgeUpPanel movie; distinguish this from self-discovery's initial decision popup |
| Age up | User suspects missing support | Python personality-assignment message and AgeUpPanel path confirmed; dedicated accessibility hooks absent |
| All picker lists | Skips, missed taps, slow movement, stalls when scrolling | Dropped commands while settling and recycled-control indexing found in current source |
| NVDA / Polish startup | Initially no speech; later report says Live Mode narration works | No tester log/version available; cause and resolution unknown. Keep separate from modal blockers |

These reports establish failures, not their exact installed build, config,
or UI Cheats combination. Do not attribute them specifically to v5.

## Confirmed pre-v6 source findings

### 1. Containers are mistaken for buttons

`flash/TooltipManager_patched.as`, `A11yIsFocusable` accepts any class name
containing `Button`, `Checkbox` or `CellView`, as well as actual button types
and sprites with buttonMode. `A11yCollectFocusables` stops descending as soon
as it accepts an object.

EA's `widgets.Dialog.footers.DialogButtonFooter` and `YesButtonsFooter` are
containers with grids of child buttons. Their class names contain `Button`,
so the current walker collects the entire footer and never visits its actions.
This is a concrete source-level defect consistent with merged action labels.
Do not claim every reported popup uses these exact footer classes without
capturing its runtime type.

### 2. A named DialogButton is itself a wrapper

EA's `widgets.Dialog.controls.DialogButton` extends CellView. It holds
`btn:TextButton` and `btnIcon:IconTextButton`. `ConfigUI` registers the click
handler on `btn`; `Draw` can register it on the visible `btnIcon`. Its handler
forwards the button event to the grid/footer.

Our walker instead accepts the outer DialogButton, then A11yActivate sends
mouse events to that wrapper. Events do not descend to the inner button.
Correcting footer traversal alone therefore does not fix activation: the
actual visible action control must receive the click. Preserve the existing
Scaleform MouseEventEx/buttonIdx mechanism; do not directly dispatch a
PushButtonEvent to arbitrary cells (documented GUIPickerBase crash).

### 3. Current dialog hooks run at request time, with limited coverage

`DialogMain.HandleUiDialogMessage` announces/scopes only that handler's
request. Other client dialogs call DialogManager through other paths.
DialogManager queues requests and only later attaches the active dialog.
The current pending-scope listener times out after 150 frames. A queued
dialog can miss that window or supersede the current pending target.

`olympus.dialog.DialogManager.GetCurrentRequest()` exposes the active request
and its dialog. Investigate synchronizing with actual display/close lifecycle
instead of adding an early hook to each caller. A raw byte-string occurrence
of DialogManager in a movie is a reference candidate, not proof the movie
defines the class; confirm actual definers before modifying shared classes.

`A11yTabMove` also discards an empty scoped list and searches the whole stage.
An unready modal must not silently redirect navigation to the background UI.

### 4. Age-up and trait reassignment use their own movie

`EA/simulation/sims/sim_dialogs.py` defines SimPersonalityAssignmentDialog
with `Operation.MSG_SIM_PERSONALITY_ASSIGNMENT`. Aging transitions construct
this dialog. Its TRAIT_REASSIGNMENT style supplies valid personality traits.

EA's `widgets.Gameplay.AgeUpPanel.AgeUpPanelMain` receives
SimPersonalityAssignmentDialog, queues it, and populates each entry in
ShowNextDialog. It has separate trait and aspiration selection panels,
name-entry controls, validation that disables Done, and explicit trait
reassignment behavior. AgeUpPanel is absent from the shipped patch map.

Supporting it requires all those controls and their lifecycle, including
successive queued dialogs and subpanel return focus. An opening announcement
or a generic OK response is insufficient: OnOkButtonClick finalizes personality
assignments/name input before sending the dialog response. Age-up deliberately
hides Close; trait reassignment permits it. Preserve those game rules.

### 5. Specialized pickers share a host, but focus happens too early

PickersMain.Show calls A11yFocusInto before specialized child movies finish
loading. OnPickerSet later attaches and shows the actual picker, without
reasserting accessibility focus. Food/Grid/Multi/Outfit/Sim/ColumnBased lacking
their own hook does not prove they have no support: the common PickersMain
host can cover them. Verify the loaded child and each distinct control type.

In TooltipManager, A11yStepInList returns immediately when a scroll is already
pending, losing the navigation request. It derives the next index from a
recycled display object. A11yIndexFrame adds whole-row nudges every five frames
and can time out without movement. A realized cell is accepted without proving
it lies inside the visible viewport. These require logical item tracking and
reliable reveal of the requested item, with no blind page/wheel jumps.

### 6. Silence needs its own diagnostic path

Speech DLL discovery derives paths from the loaded script and searches the
Mods tree; it does not assume an English Sims user-directory name. Nothing
in this investigation establishes Polish as the cause of silence.

One independent reliability gap: `_speak_now` ignores false return values
from Tolk_Output in multiple branches and returns as if speech succeeded.
The direct NVDA path already checks its controller result. Verify Tolk failure
handling and fallback separately; this is not a diagnosed cause of the report.

Existing support commands: `a11y.log on`, `a11y.status`, `a11y.test`.
Status/log evidence should distinguish script loading, DLL discovery, selected
backend, explicit speech output, speech mode, and Flash event delivery. A local
developer log cannot establish what happened on the tester's installation.

## Original implementation and verification requirements

1. Fix traversal and real-button activation for standard dialog footers and
   action wrappers. Keep full body text available independently of actions;
   preserve per-action labels, supplemental text, disabled state and reasons.
2. Follow the active modal lifecycle, including queued/nested dialogs,
   auto-focus off, teardown and return focus. Navigation must work while paused
   and must not operate controls behind an open modal.
3. Fix the common picker host timing and list navigation by logical item index.
   Test rapid taps, held keys, reversals, one/zero-item lists, long grids,
   filtering, quantity/multi-select controls, and reaching footer actions.
4. Add age-up/reassignment coverage after inspecting trait/aspiration list
   controls and text input. Include selection validation and persistence.
5. Inventory remaining dialog families, including text entry, notifications
   with actions, client-only/system dialogs and dedicated widgets. Main-menu,
   CAS, travel and Build/Buy support cannot be inferred from Live Mode results.
   CASCustomizer recompilation has a known crash; do not patch it casually.
6. Integrate an appropriate server-side response/picker fallback from glaroc
   where needed, using live dialog IDs and the game's response/selection APIs.
   A fallback must preserve required selection payloads, validation and labels;
   it cannot answer client-only dialogs or replace trait assignment with OK.
7. Verify with NVDA and Polish labels/diacritics, plus UI Cheats compatibility.
   Test by completing/declining actual dialogs entirely by keyboard, observing
   the resulting game state and ability to continue. A spoken label or pcode
   gate pass alone is not an accessibility pass.

Release acceptance: each reported blocking dialog can be completed using all
its offered actions, every required field/selection is operable, and focus
returns correctly. Track untested families explicitly; do not label universal
dialog support complete on the strength of a few successful examples.

## Read-only reference exports

`flash/dialog-nav-reference/scripts/` contains selected original EA classes:
DialogManager, dialog containers, footers, DialogButton, CellView and
AgeUpPanelMain. `ea_AgeUpPanel.swf` there is an extracted original, not a patch.
`flash/picker-nav-reference/scripts/` contains grid/scroll and picker-base APIs.
FFDec `-export script` was used, not `-replace` or any rebuild pipeline.

Related earlier notes: A11YSCAN-REVIEW.md documents the unintegrated server-side
dialog fallback; TODO-NEXT-SESSION.md records older picker scrolling work;
HANDOFF-SCANNER-INTEGRATION.md and SCANNER-TEST.md record installed v5.
