> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# V7 keyboard test build

This is a development build, not a claim of complete game accessibility.
The compiler and bytecode checks cannot establish how the game handles
focus, camera input, scrolling or timing. Those checks need a game session.

## Start here

1. Load your save. Press **Ctrl+Alt+H** with no panel/dialog open for the
   accessibility menu. Try Needs, Mood and moodlets, Wants and fears,
   Current action, Household Sims, funds and settings.
2. Open Skills using its normal button. Focus should enter the panel.
   Arrows should move through it without panning the camera. **Escape**
   should close it without also opening Options. Repeat with the phone,
   Career, Aspirations, Relationships, Inventory, Simology, Needs, Social
   Groups and Owned Businesses. Try an interaction pie opened by mouse too.
3. In Purchase Books and your sheet-music picker, hold Down, release, then
   verify that speech, the yellow outline and the activated row agree.
   Reverse direction quickly and try returning from the bottom of the list.
   **Tab** should leave the list for the footer; **Shift+Tab** should return
   to the remembered row. Enter on a purchase row should focus Done;
   another Enter should confirm. Backspace from the footer returns to the row.
4. In a Sim picker, tap and hold Enter separately. Each press should toggle
   exactly once. Space also selects; Tab reaches the confirmation button.
   In Plan an Event, Enter on the event type should select it and advance
   when Next is enabled.
5. Register a Small Business: type a name, use **Tab/Shift+Tab** to leave and
   return, edit with arrows, and reach activities, prices and confirmation.

## Reported blockers

- Likes/dislikes, self-discovery, work chance cards, answered-phone dialogs,
  discovery quests: reach each response independently, activate exactly one,
  and resume gameplay. Required decisions may legitimately refuse Escape.
- Trait swap and Age Up: choose required traits, remove/replace one, reach
  name fields and confirmation. Escape must retain EA's restrictions.
- Sim Profile: reach age, education and its description, individual
  relationship/compatibility entries and sentiments beneath the headings.
- Calendar: Up/Down moves a week, Left/Right a day. Enter opens the selected
  day's schedule. Read event names, times, locations and participants; reach
  entry actions and filters. Tab should leave the calendar grid.
- Moodlets: move the mouse through gaps; they should not repeat the mood.
  Use Ctrl+Alt+E for keyboard access to mood/moodlets, Ctrl+Alt+G for wants,
  and Ctrl+Shift+N for Needs. Check tooltip details and remaining durations.
- Have an inactive household Sim receive a call/text. Hear their name,
  close the current panel, then press Ctrl+Alt+P. It should select that Sim
  and focus the existing alert. Expired calls must not open another Sim's
  phone. Calls still have EA's normal expiry time.
- With only the ordinary HUD visible, Ctrl+Alt+Up/Down should move the
  world scanner. Open a panel and those navigation chords should stay there.
  For the sighted caption display, turn Captions on in settings, or use
  `a11y.captions on`.

## Regression checks

- Mouse-hover narration should retain labels and detailed tooltips.
- In manual speech mode, Ctrl+Alt+R still reads the captured content. While
  speaking, the same key stops speech. Speech mode is changed in settings.
- With keyboard navigation off, hovering still speaks; opening panels must
  not capture keyboard input or pull the focus ring. Re-enable in the cfg
  or with `a11y.keys on`.
- Optional numpad navigation defaults off: enable it in settings, NumLock
  on; 4/6 moves, 5 activates, 8 reads/stops, decimal backs out.
- Try Polish text and AltGr typing, including in the cheat console. The
  mod must not intercept ordinary typing as scanner chords.

## Still outside this build

Main-menu speech, CAS, independently placing/furnishing a home, map-free
travel/household moves, and a full gamepad interface remain incomplete.
The startup probe is separate and is not installed with this test build.
See STARTUP-PROBE-V7.md and INTEGRATION-STATUS-V7.md.
