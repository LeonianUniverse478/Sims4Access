> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# V8 implementation review

This is the fix pass for FEEDBACK-V7-ROUND2.md. The user's V7 results remain
the record of game behavior. V8 changes below require a fresh game test.

## Input ownership

The shared TooltipManager now determines ownership from the active dialog,
visible modal widget, open HUD panel, open dropdown or visible interaction
pie. A class name containing “Picker”, “Dialog” or “PieMenu” is insufficient:
those roots can remain loaded after closing. Closing the final surface
clears stale scope, queued navigation and delayed focus. HUD widgets must
also pass EA's `IsWidgetVisibleAndNotHiding` service. Owner changes are logged
through `a11y.context_enc` without speech.

This addresses a source-level cause shared by the scanner, camera, Escape
and contextual-help reports. It does not prove those runtime failures had
only one cause. Python routing remains on the simulation pump; native input
guards retain their existing lease and one-press activation behavior.

The key polling loop also releases native guards when a key comes up while
Ctrl+Alt is still held. Fresh low-level hook state takes precedence over a
stale GetAsyncKeyState high bit; an expired/missing hook still permits the
polling fallback. Regressions cover all three cases. This prevents a swallowed
key-up from restarting a released scanner chord or leaving a camera guard set.

## Lists, grids and controls

- Grid lookup supports public ScrollList layouts and SimpleGrid's public
  `GetGridLayout()`. Skills uses a SimpleGrid inside category cells inside an
  outer ScrollList. Nested static rows remain reachable outside the viewport;
  focusing them scrolls the nearest native scroller. Existing recycled lists
  retain indexed navigation and layout checks.
- Container rows in Skills and Simology are traversed to their contents.
  Scrollbars, resize handles and inventory's drag-only sale target are skipped.
- Two-dimensional grids use their native layout coordinates. Purchase rows
  retain Left/Right quantity controls. Tab groups lists, filter groups and
  calendar event cards; arrows stay within a card's content/actions.
- DropdownExtension's current list takes input ownership. Its selected item
  gets focus; native selection handles Enter, and native Close handles Escape.
  Closing restores the field without reopening or confirming its parent.
- Needs exposes one row and routes activation to its existing `btnSolve`.
  Inventory routes hover/click to `btnCellView` and exposes `btnOpenStack`.
  Selling uses native Select Multiple and Sell, including EA's existing
  selection accounting, favorite warnings and confirmation dialog.
- HUD panels call native `ResizablePanel.SetSize` with an unsaved resize;
  EA clamps to the screen's permitted maximum. Phone focus starts at apps.
  Closing a HUD panel clicks its opener without hovering it.

## Narration

- Scope opening collects the panel opener label or dialog's non-button
  text and combines it with the first focused control in one speech command.
  Explicit later navigation can still interrupt. The V7 log showed the
  Family Dynamic description was emitted and then superseded by widget speech.
- Career workdays use the native schedule's CSS day state and localized
  full weekday names; days off are omitted. The new “Work days”/“None” prefix
  currently uses English. Calendar relative-day phrases also use English,
  while weekday names and native event text remain game-localized.
- Calendar date labels use the data's current-day offset, replacing the
  decorative index/count. Settled keyboard focus explicitly shows the native
  day tooltip. Calendar Add rows expose their own labels and native buttons.
- The preliminary household-wallet amount is suppressed; its full tooltip
  remains the narration source. The current mood's default description
  tooltip is suppressed only when its text matches the active mood's
  description. Its visible tooltip and short mood-label reading remain.

## Validation boundary

Seven offline suites cover 123 checks, including owner-release routing,
simulation-thread hub dispatch and combined opening narration. Flash builds
must pass the main and UI Cheats bytecode fidelity gates, and the artifact
verifier checks source/archive agreement, exact 24+6 resource sets, unchanged
class definitions and unchanged non-code movie tags.

No game session was driven by the agent. Incoming calls/texts remain untested,
as do V8's keyboard/scrolling/timing changes. The full remaining integration
scope is recorded in INTEGRATION-STATUS-V7.md. Main-menu speech and CAS remain
unresolved; the isolated V7 startup probe is not part of V8 deployment.

Use canonical sources, not the one-shot edit helpers, for future changes.
