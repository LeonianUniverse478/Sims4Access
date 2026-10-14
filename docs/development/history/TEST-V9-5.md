> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# V9.5 test handoff

Historical handoff. V9.6 supersedes this build; see TEST-V9-6.md for current
installed status, verified results and remaining blockers.

Status: V9.5 verified and installed. Targeted V9.5 game checks are underway.
Earlier live results below come from V9.2–V9.4. Settings were preserved.
All 144 distinct offline checks passed (159 including repeated imported
checks), plus 61 main and 19 compatibility comparisons. All 14 archived
Python modules match source; the 24+6 movie resources round-trip correctly.
Manifests: `build/v9_5-verification.json` and `build/v9_5-deployment.json`.

## What the unattended game tests established

- Needs have one stop per whole need. Sebastian Darden's Vampire Energy and
  Thirst focus and report 100% and 23%, respectively. The other vampire needs
  and Vampire Powers were also reached. Closing Needs clears its tooltip.
- Closing panels releases focus; Escape then opens Options. Returning from
  Build to Live Mode also releases focus without an extra Escape.
- Phone navigation begins at apps and crosses page boundaries in both
  directions. A real incoming call or text has not been tested.
- Calendar dates/events, busy Sim names and the combined season/day/weather
  heading work in the tested household. Filters own focus and skip their
  scrollbar. Stay Over now reaches individual guests and scrolls to hidden
  rows; Space selects and clears a guest once per press.
- Add Holiday takes focus. Its name field is one stop; Enter edits and Tab
  leaves it. Traditions can scroll into view. Test holidays were canceled.
- Inventory Black Earbuds gives its native tooltip. Selection, opening Sell,
  canceling and returning focus to Sell worked. No sale was committed and no
  new BE report appeared in that sequence. One phone-shaped item is still
  unnamed and needs investigation.
- Simology's hidden preference sections scrolled into view. All 16 Skills
  rows fit at maximum height on this screen, so that did not test hidden
  Skills rows on a smaller screen.
- Build Mode's first Tab enters navigation. Catalog items can be reached,
  moved across and scrolled into view with native item tooltips. Placement,
  moving objects and undo are not integrated keyboard workflows.

## Scanner performance and scope

The scanner uses real time, including while the game is paused. Refreshes
remain two seconds apart while in use. After 30 seconds without scanner
input it stops enumerating the world; the next scanner action refreshes
stale results. Definition classification is cached, while position,
visibility, inventory state and interaction availability stay fresh.

In the loaded Darden household, 12 refreshes averaged **7.83 ms**, with a
**16.08 ms maximum**. The last refresh was **4.97 ms**. This was one paused
household with a compiler running concurrently, not an FPS benchmark or a
before/after speedup measurement. The scanner found 82 entries in 12
categories: 13 Sims and 69 objects. It then went idle as intended.

Scope remains interactive world objects within 40 metres, plus instantiated
Sims in the loaded neighborhood. Inventory objects, hidden objects,
unloaded neighborhoods and non-interactive scenery are outside that scope.
`a11y.scan stats` reports measurements without waking an idle scanner.

## V9.5 targeted checks

1. In Plan a Stay Over, Enter on **3 nights** should open its choices. Change
   duration, then cancel the whole Stay Over; no event needs to be created.
2. In a panel or dialog, Tab forward and **Shift+Tab backward**. The native
   binding now records Shift so a short press is less dependent on Python's
   modifier sampling. Runtime acceptance is pending.
3. With Ctrl+Alt held, short scanner taps now survive the interval before the
   temporary hook attaches. Three additional automated checks cover delivery,
   stale hook releases and released modifiers. Full chords released between
   polls remain a timing limitation; no permanent system-wide hook was added.

## Most useful player retests

1. Hold an arrow in a large picker, release it, and check that speech matches
   the final highlight. Check both Purchase Books and the custom music picker.
2. With all panels closed, hold an arrow to move the camera. Open and close
   Needs, a picker and a pie, then repeat. Test Ctrl+Alt+H and scanner chords
   after each close.
3. Use the mod with NVDA, including Polish typing/AltGr. This machine's speech
   backend is SAPI; narration logs are not proof of what NVDA hears.
4. Check career and aspiration completed/unfinished objectives and inventory
   items beyond the two present in the test household.

The computer-use tool sends short taps and cannot control held-key duration.
Held repeats, camera movement and very short Ctrl+Alt chords are therefore
still player checks. A quick injected Ctrl+Alt+H was missed with world focus
correctly released; ordinary held-modifier behavior is not established by it.

## Remaining blockers

- **Main-menu speech and independent CAS remain incomplete.** Startup tests
  proved the shared Gamedata UI runs there, but the normal UI/Python bridge
  does not deliver before a loaded client exists. A fixed localhost request
  also failed with an IO error; NO_CONTEXT native commands did not bridge it.
  All temporary probes are removed from the installed mod.
- **Incoming calls/texts:** keep untested until a real alert occurs. The
  existing recipient/shortcut implementation is not a passing test result.
- One inventory item remains silent. Some restored calendar Add buttons use
  the generic Add label. Needs opening can repeat the first need's name.
- Read-only tile grid, validated map-free travel, Build placement/undo,
  remote-contact/inventory scanner categories and a CAS creation wizard
  remain unintegrated. See INTEGRATION-STATUS-V7.md for the full inventory.
- First-install settings popup remains deferred at the user's request.

## Evidence

Earlier detailed runs: TEST-V9-LIVE-2026-09-15.md,
TEST-V9-3-LIVE-2026-09-15.md and TEST-V9-4-LIVE-2026-09-15.md.
The normal package scope is still 24 main movies and six UI Cheats movies;
no CAS or EngagementLibrary overrides were added.
