> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# V9.6 test handoff

**V9.6 is verified, installed and tested in-game.** The game is left paused
with Sebastian Darden selected and all panels closed. Configuration was
preserved. The named save is unchanged. This is a test build; independent
startup/CAS and several larger accessibility workflows remain incomplete.

## Fixes and live results

- **Scanner:** refreshes every two real seconds while used, including when
  paused. After 30 seconds without scanner input, it stops scanning. The
  next action refreshes stale results. Nearby filtering happens before
  costly classification; reusable definition metadata is cached. Position,
  visibility and interaction availability stay fresh.
- **Vampire needs:** Sebastian's Vampire Energy and Thirst are whole keyboard
  targets and announced 100% and 23%. His other needs and Vampire Powers
  were reachable. Ordinary Sims' needs also use whole targets. Closing
  Needs removes its tooltip.
- **Focus release:** closing panels releases ownership; Escape then opens
  Options. Build to Live also releases focus without an extra Escape.
- **Dropdowns:** Stay Over duration and time open by Enter, focus their
  selected value, and close with Escape back to the field. Shift+Tab moved
  backward in the tested picker.
- **Inventory:** Black Earbuds retains its full native tooltip; the formerly
  silent Slightly Smelly Cellphone now has its localized catalog name.
  Keyboard selection, Sell confirmation, cancellation and return focus
  worked in the earlier V9.4 test. No sale was committed and no new BE
  report appeared.
- **Calendar:** relative dates/events, busy Sim names, one season/day/weather
  heading, filter focus, individual Stay Over guests and hidden guest rows
  worked. Add Holiday pulls focus; its name field can be edited and left
  with Tab, and hidden traditions can be revealed. All drafts were canceled.
- **School and aspirations:** individual requirements, performance tooltip,
  grade task and homework are reachable. Completed tasks say Completed;
  unfinished aspiration goals read progress such as 1/3. Work days read
  Monday–Friday without off-days in the tested school schedule.
- **Phone:** focus starts at apps and crosses page boundaries both ways.
  A real incoming call/text remains untested.
- **Simology / Build:** hidden Simology sections and Build catalog items
  scroll into view. Catalog spatial navigation and native tooltips worked.
  Placement, moving objects and undo are not integrated keyboard workflows.
- **Accessibility menu:** `a11y.hub` opens a visible native picker; Enter on
  Needs opens Needs. Full Ctrl+Alt+H shortcut acceptance is separate below.

Earlier live passes are from V9.2–V9.5; V9.6 specifically rechecked dropdown
ownership/Escape, inventory naming/tooltip preservation and the hub action.
The player previously passed choice dialogs, Profile, purchases and small
business registration. These checks do not establish every dialog variant.

## Scanner measurements

On this paused household, 12 refreshes averaged **7.83 ms**, maximum
**16.08 ms**, last **4.97 ms**. A compiler was running at the time. This is
one-lot timing, not an FPS benchmark or a measured before/after speedup.
The scanner found 82 entries in 12 categories: 13 Sims and 69 objects;
it then went idle as intended. `a11y.scan stats` reports metrics without
waking an idle scanner.

Scope: interactive world objects within 40 metres, plus instantiated Sims
in the loaded neighborhood. It excludes hidden/inventory objects,
non-interactive scenery and unloaded neighborhoods.

## Most useful player retests

1. Hold an arrow in Purchase Books and the custom music picker, then release.
   Check that speech matches the final highlighted row.
2. Move the camera with held arrows while no UI is open. Open/close Needs,
   a picker and a pie; repeat. Test scanner chords and Ctrl+Alt+H after each.
3. Test NVDA and Polish typing/AltGr. This machine currently used SAPI;
   narration logs cannot establish what NVDA hears.
4. Test an actual incoming phone call/text, including another household Sim.
5. Check Skills on a smaller screen or with more rows. All 16 Skills fit at
   maximum height here, so hidden Skills rows were not exercised.

The computer-use tool sends very short taps and cannot control held-key
duration. Full Ctrl+Alt chords released between polls can still be missed;
an injected Ctrl+Alt+H missed even with `world:00`. Short action-key taps
while Ctrl+Alt remains held have a new tested fallback, but that does not
solve a full chord that begins and ends between polls.

## Remaining blockers and polish

- **Main menu / independent CAS:** incomplete. Live probes confirmed that
  shared UI code and Python ticks run at startup, but the normal command
  bridge does not deliver before a loaded client exists. Native commands
  with 0/NO_CONTEXT and a fixed localhost request did not solve this. All
  temporary probes are removed from Mods. More movie overrides would not
  address the observed failure.
- **Larger glaroc features:** read-only tile grid, validated map-free travel,
  remote-contact/inventory scanner categories, CAS creation wizard and
  Build placement/undo remain unintegrated. INTEGRATION-STATUS-V7.md records
  the full inventory and current constraints.
- Some restored calendar Add controls still use a generic label. School
  has a duplicate Job Title stop and stray Bored text in a group summary.
  Needs can repeat its first name when opening. The hub has image
  placeholders and incorrect confirmation-button help; rows use Enter
  directly. These are recorded follow-ups, not passing polish checks.
- First-install settings popup remains deferred at the user's request.

## Verification and evidence

149 distinct offline checks passed (164 including repeated imported checks),
61 main movie and 19 compatibility fidelity comparisons. All 14 Python
modules match source. The 24 main plus six UI Cheats resources round-trip,
preserving class sets and non-code content. No CAS/EngagementLibrary override
was added. The release sibling is untouched.

- `build/v9_6-verification.json`, `build/v9_6-deployment.json`
- `build/v9_6-verified-artifacts` (exact installed artifact snapshot)
- `TEST-V9-6-LIVE-2026-09-15.md` and `build/v9_6-live-complete.log`
- Earlier detail: TEST-V9-LIVE-2026-09-15.md,
  TEST-V9-3-LIVE-2026-09-15.md, TEST-V9-4-LIVE-2026-09-15.md.

Named save Slot_00004005.save still matches its original SHA256. No intentional
save, event creation, Sim creation, purchase, sale or object placement was
committed. The game's special resume slot updated during an earlier return
to the main menu; it is not accurate to say every save-related file stayed
unchanged.
