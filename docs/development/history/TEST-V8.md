> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# V8 feedback retest

Installed September 15, 2026; the existing cfg is preserved. V7 rollback
files are saved in `build/deployed-before-v8/`.

V8 addresses the completed V7 feedback round. These are expected behaviors
to verify in the game; compilation and offline checks do not prove them.
Incoming calls/texts remain on the **untested blockers** list because no
call occurred during the previous session.

## Start with input ownership

1. Load a save with every panel, dialog and interaction pie closed.
   **Arrows** should move the camera and **Escape** should open Options.
2. Close Options. **Ctrl+Alt+Up/Down** should navigate the world scanner.
   **Ctrl+Alt+H** should open a visible Accessibility picker. With a panel
   or dialog open, that shortcut still gives contextual keyboard help.
3. Open an interaction pie, then dismiss it. Repeat steps 1–2. This checks
   that a closed, cached pie no longer keeps ownership of the keyboard.
4. In a panel, hold Down, add Ctrl+Alt, release Down while keeping the
   modifiers held, then release them. Movement must stop. Close the panel
   and verify the camera arrow works again. Also release a scanner arrow
   before releasing Ctrl+Alt; it must stop on the last intended object.

## Main panels and dropdowns

- Open Skills, Simology, Career, Needs, Inventory and Relationships.
  The panel name should precede useful content. Resize handles and
  scrollbars should never take focus. Panels should use their native
  maximum height. Escape should close the panel without speaking its
  opening button or also opening Options.
- In Skills and Simology, continue past the last initially visible entry.
  The view should follow focus. Reverse direction and reach the top again.
- In Relationships, arrows navigate filters; Enter applies one. **Tab**
  leaves the filter group for the Sims. Shift+Tab returns to the group.
- Open a dropdown, such as the Rewards Store category field. Focus should
  enter its selected option. Up/Down moves, Enter chooses, and Escape
  closes just the dropdown. Focus should return to the field.
- Open the phone. Initial focus should be an app; its utility controls
  remain reachable with Tab.
- Needs should have one stop per need, retaining its existing description.
  Enter on that row should activate the native solve button when available.

## Inventory and grid movement

- Sim pickers and inventory should support spatial Up/Down/Left/Right
  movement. Hold a direction and release; the final spoken item, outline
  and activated item must agree.
- Inventory items should expose their normal tooltips when focused.
  A stack's separate Open Stack control should be reachable.
- To sell without dragging: Tab to **Select Multiple**, activate it, return
  to the item grid and select the desired item/stack. Tab to **Sell** and
  activate it. The game's confirmation must appear; cancel first to verify
  that nothing is sold. Open a stack to select individual items when needed.
  Verify unsellable/favorite items retain the game's restrictions and prompts.
- Purchase dialogs were confirmed good in V7. Check that their Left/Right
  quantity controls, Enter → Done → confirm, and Backspace return still work.

## Calendar and narration

- Dates should read the weekday and a relative day, e.g. “Monday, 12 days
  from today,” without the old index/count. Pause on a populated day for its
  native tooltip, including events, festivals, busy Sims and lunar phase.
- Enter a day's schedule. Arrow navigation should stay within each event's
  details/actions; Tab moves between groups. Add rows should announce
  **Add Holiday / Add Event / Add Wedding Event / Add Stay Over / Add Funeral
  Event**, as available. Reach the bottom row through automatic scrolling.
- A new choice dialog should announce its title, explanation and first
  response together. Then verify each response is independently reachable.
- Career schedules should read full workday names and omit days off.
- Hover household funds: hear the complete tooltip once, without the
  preliminary balance-only announcement.
- Hover the actual mood label: hear the short mood. Its explanatory tooltip
  should stay silent. Individual moodlet tooltips and movement through the
  gaps should retain their working behavior.

## Retained blockers and regression checks

- **Incoming calls/texts: still untested.** When one happens, verify recipient
  announcement, including an inactive household Sim. Close the current panel,
  press Ctrl+Alt+P, and check the correct Sim's alert receives focus. Verify
  an expired alert cannot open another Sim's phone. Calls retain normal expiry.
- Choice response navigation and Sim Profile traversal passed V7 testing.
  Preserve both, plus Small Business registration and mouse-hover narration.
- Keep testing Age Up/trait reassignment and special decisions as they occur;
  no blanket “every dialog passed” claim is made.
- Keyboard off should retain normal mouse narration and game input.
  Test text editing, Tab out of inputs and Polish/AltGr typing.

## Still outside this build

Main-menu speech, CAS, independent home placement, map-free travel and full
gamepad access remain incomplete. See INTEGRATION-STATUS-V7.md for the glaroc
comparison. The separate V7 startup probe is not installed and must be rebased
before combining it with V8; do not replace V8 with that older test package.

For a failed input-ownership test, the log now records `UI owner:` transitions
such as `world:00`. Include the time of the failure and which surface was open.
