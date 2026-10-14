> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# V7 in-game feedback — round 2 complete

The user finished testing and authorized the next fix pass through the
existing task. This document preserves their observations and requested
behavior. V8 source changes are documented in KEYBOARD-V8.md; TEST-V8.md is
the retest checklist. Compilation is not an in-game acceptance result.

V8 is now installed, with 123 offline checks and both Flash gates passed.
Its fixes remain awaiting the user's next in-game test.

## Still untested / retained on the blockers list

- Incoming calls/texts: no call occurred during this test session. Keep
  recipient announcement, inactive-Sim routing, focus and expiry behavior
  unverified until a real call/text is tested.

## Confirmed working by the user

- Purchase dialogs: "work great". Preserve their behavior.
- Register a Small Business: works.
- Mouse-hover narration continues to work. Preserve it.
- Moving the mouse through gaps between moodlets works correctly. Preserve
  this behavior; the separate request to silence the current-mood explanatory
  tooltip remains pending.
- Choice dialogs: the user can reach and activate responses. Automatic
  announcement of a new dialog's title/body is still failing (below).
- Sim Profile: the user can now reach everything.
- Calendar date grid: the user likes the spatial Up/Down/Left/Right movement.

## Input ownership and panel lifecycle

- World-scanner keyboard navigation still does not work in V7, confirmed
  again by the user. Treat this as a priority regression. Investigate with
  the Escape/camera/context-help failures below; incorrect UI ownership is
  a possible shared cause, not yet established by runtime diagnostics.
- Escape does not open Options when all other panels are closed.
- Arrows do not move the camera when no panel/dialog is open.
- Ctrl+Alt+H produces "Dialog" and help speech, with no visible/navigable
  Accessibility menu. An open panel intentionally selects contextual help
  in the current implementation, but whether this report also occurred with
  every panel closed has not been established. Check incorrect or stale UI
  ownership alongside the Escape/camera reports.
- Opening a main panel first focuses/reads "Drag to resize". Exclude resize
  handles from keyboard traversal. Announce the actual panel name, sourced
  from its opening button's localized label, then focus useful content.
- Closing a panel briefly focuses its opening button and reads e.g.
  "Skills - L". Avoid that unintended closing announcement.
- With keyboard navigation enabled, panels should use the maximum height
  that fits the user's screen.
- Phone initial focus should go to apps. Silence Phone and appearance
  controls should remain available as secondary controls.

## Scrolling and grouping across the UI

- Skills reaches the last visible item and loops to the top without scrolling.
- Simology has the same failure. Treat it as a shared main-panel issue and
  audit every panel, rather than fixing only these two.
- Scrollbars and resize handles should never be keyboard focus targets.
  Keyboard traversal must scroll automatically to reveal off-screen content.
- Relationship filter buttons currently each take a Tab stop. Treat a filter
  group as one stop: arrows move within the group, Enter/Space applies the
  filter, Tab exits to results, Shift+Tab returns to the active filter.
  Apply this grouping to filter controls elsewhere as well.
- Extend the calendar's spatial movement to two-dimensional layouts such
  as Sim pickers and inventory: arrows should follow visible rows/columns.

## Inventory

- Keyboard hover/focus does not display the item's tooltip.
- Selling requires dragging an item to the bottom sell bar. Provide a
  keyboard-accessible sale action, including appropriate stack/quantity
  handling and the normal game validation/confirmation.

## Career and dialog narration

- Work schedule reads "S M T W T F S" literally. Instead say "Work days:
  Monday, Tuesday, ..." using full localized weekday names, including only
  scheduled workdays and skipping days off.
- A choice dialog such as "New Family Dynamic: Difficult" focuses a button
  without announcing that a dialog opened or reading its explanation.
  Announce the dialog, title and body automatically, then the focused choice;
  focus speech must not suppress the explanation. Keep choices individually
  reachable and activatable.

## Household funds hover narration

- Hovering the household balance first reads the amount, then reads the
  Household Funds tooltip, which repeats the amount.
- For this specific hover target, suppress the preliminary amount-only
  announcement and read only the complete tooltip, including its label and
  balance. Keep this exception scoped to household funds; preserve other
  working hover narration.

## Dropdown choices

- Opening a dropdown leaves focus on the field instead of moving into its
  options. The user cannot navigate or select an option. Screenshot example:
  All, Traits, Potions, Formative Moments Traits.
- On opening, focus the currently selected option (or the first available
  option). Up/Down should navigate and announce options; Enter should select
  the focused option and return focus to the field.
- Escape should close only the dropdown without changing its selection,
  restoring focus to the field. Treat the expanded dropdown as the current
  input owner so keys do not operate the underlying panel/dialog.
- Audit shared dropdown controls throughout the UI, not just this example.

## Needs: one keyboard target per need

- Each need currently exposes three focus targets: the whole need (whose
  narration works perfectly), a "solve icon" container, and a silent child
  control that successfully triggers auto-solve when Enter is pressed.
- Keep only the whole need as a keyboard target. Preserve its existing
  narration. Enter on that target should activate the associated native
  auto-solve control, retaining the game's availability/disabled checks.
- Exclude the redundant icon container and child trigger from separate
  keyboard stops while retaining their underlying function.

## Current mood narration preference

- Keep the Sim's current-mood explanatory tooltip silent. Continue reading
  the brief mood text only when that mood label is actually hovered, rather
  than from the surrounding background or gaps between moodlets.
- Example: read "Passionate" from the mood label, but suppress the longer
  tooltip describing romantic socials. This request concerns the current
  mood tooltip; retain individual moodlet details and explicit keyboard
  access to the mood label.

## Calendar: latest detailed feedback

- Dates are followed by an unwanted number. Replace the navigation index
  with a meaningful relative date, e.g. "Monday, 12 days from today", then
  read the day's events. Handle today/tomorrow naturally and localize terms.
- The date's hover tooltip is not read through keyboard focus. Include its
  existing content: events/festivals, busy Sims and lunar phase when present.
  The screenshot shows GeekCon, busy Sim portraits and Waxing Crescent Moon.
- Event focus order is confusing: event, event reading, scrollbar, Favorite.
  Keep the event's details and actions together, use predictable movement
  within that group, and let Tab advance to the next group/section.
  Example card: Starlight Accolades; Normal Event; 6:00 PM–11:00 PM;
  STUDIO PBP; Favorite and a disabled Go to Event button.
- Add rows read only their generic "Add" buttons. Include the associated
  row label: Add Holiday, Add Event, Add Wedding Event, Add Stay Over,
  Add Funeral Event. Preserve each row's enabled/disabled state.
- The bottom add row hidden behind the scroll cannot be reached. Include it
  in logical traversal and reveal it automatically.

## Supplied screenshots

All under `<user-home>/AppData/Local/Temp/`:

- `codex-clipboard-556f4b07-11d4-4729-b88e-8a1f3983f70d.png`: Skills viewport.
- `codex-clipboard-f34b3e6c-8520-42be-be7d-291e19f7cda7.png`: Family Dynamic dialog.
- `codex-clipboard-e3179c01-9374-4a42-8927-4170dcfb6ec9.png`: relationship filters/grid.
- `codex-clipboard-afbf1398-4b37-42fd-844e-e7844fe67106.png`: calendar date tooltip.
- `codex-clipboard-d2ea5b45-4370-49bc-b0e0-6db612c4b163.png`: calendar event card.
- `codex-clipboard-cfab10f3-f138-41e8-b309-14250651511b.png`: calendar add rows.
- `codex-clipboard-77451d3c-fbf5-4251-a9a4-8f7b823aa6ad.png`: current-mood tooltip.
- `codex-clipboard-831563cc-27fe-4ada-8c60-50a3d134433b.png`: Hunger auto-solve icon.
- `codex-clipboard-d830bc59-7eb3-4dd6-b2cd-04abe2009362.png`: expanded choice dropdown.

The earlier TEST-V7.md and KEYBOARD-V7.md checklists describe intended
behavior. Use this file as the completed user-reported V7 feedback round.
