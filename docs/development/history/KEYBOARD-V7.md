> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# Keyboard feedback batch — 2026-09-15

The user finished collecting feedback and authorized fixing it. Preserve the
working mouse-hover narration. V6 is the installed baseline; source and build
rollback copies are in `build/source-before-v7` and `build/artifacts-before-v7`.
The following are reported failures, not verified fixes.

## Acceptance checklist

- [ ] Fast purchase-picker navigation ends with speech, focus ring and activation
  on the same row; Purchase Books remains responsive with hundreds of rows.
- [ ] Small gaps between moodlets do not announce the mood repeatedly.
- [ ] Tab/Shift+Tab leave picker lists for controls and Done/OK; returning to a
  list restores its last row. Left/Right still change purchase quantities.
- [ ] Each Enter/Space press activates once; Sim selections never oscillate.
- [ ] Event-type picker has a clear keyboard path through selection and Next.
- [ ] Scanner chords reach the scanner when only the persistent HUD is visible.
- [ ] Calendar exposes dates, entries, existing details and relevant actions.
- [ ] Sim Profile exposes informational entries beneath accordion headings,
  reusing the narration already available on hover.
- [ ] Opening Skills, Career, Aspirations, Relationships, Inventory, Simology,
  Needs, Social Groups, Owned Businesses or Phone moves keyboard focus inside.
- [ ] UI-owned arrows cannot move the camera. Escape goes back/closes the top
  surface and does not also open Options; closing restores useful prior focus.
- [ ] Calls/texts identify the receiving household Sim and provide a timely
  keyboard path to the correct phone prompt, including inactive Sims.
- [ ] Current mood, moodlets, needs, wants/fears have convenient keyboard access.
- [ ] Tab/Shift+Tab escape text inputs, including Register Small Business;
  caret editing and normal text input remain intact.
- [ ] Mouse- and scanner-opened interaction pies take focus, consume arrows,
  activate once, and support Escape back/close.
- [ ] Keyboard setting gates contextual focus and capture. Optional numpad
  navigation shares the same engine. Scanner retains its separate setting.
- [ ] Remove punctuation navigation and Insert/Numpad9 speech-mode shortcuts;
  speech mode remains in settings. Keep deliberate repeat and scanner help.
- [ ] Update shortcut documentation and meaningful regression checks.

## Scope and verification constraints

Keep the established 24-movie package (23 plus AgeUpPanel for its own class)
and six UI Cheats compatibility movies. No CAS or EngagementLibrary overrides.
Do not change the release sibling. First-run settings popup remains deferred.
Main-menu research is now explicitly requested; keep startup experiments
separate from the primary test build. Do not modify protected game code.

Compile and opcode/package gates establish build integrity, not in-game
keyboard usability. Track untested behavior explicitly. Never replace the live
build while the game is running. Preserve the user's cfg and V6 rollback files.

## Implementation notes

Source changes cover native EA key guards, Tab versus row navigation,
picker final-focus speech, informational focus targets, HUD/phone context,
one-shot input polling, household call notification/opening, and a common
accessibility menu. V7 is deployed. Runtime boxes above remain unchecked
until the user tests them; see TEST-V7.md for the recommended order.

The user subsequently authorized overnight work on all discussed/planned
features and glaroc's remaining functionality, including main-menu startup
access. Prioritize reliable live-game access; report unverified scope honestly.

Additional review/adoption queue:

- [ ] Status summaries, current action, funds, household Sim selection/focus.
- [ ] Self, phone, inventory and contact scanner entry points.
- [ ] Read-only tile grid and positional navigation.
- [ ] Server-owned dialog fallback with correct client closure and validation.
- [ ] Travel, household switching, careers and event-planner entry points.
- [ ] Build/catalog placement and undo only with the normal game constraints.
- [ ] Optional CAS bypass/wizard and appearance features; no CAS movie overrides.
- [ ] Save workflow that does not overwrite the resume slot behind the user.
- [ ] Main-menu transport probe independent of Python speech and UI-hook setup.

Native input-action source inspection found that `TriggerActions` **inverts**
callback return values: a callback returning false consumes input. The guards
use this EA path, not controller-mode toggles. A Python heartbeat expires the
guards after two seconds if transport stops. Their actual effect on camera
input still requires an in-game test.

The old Flash stage keyboard handler was registered in capture and bubble,
in addition to Python polling. Both listeners were removed to retain one
activation path. This is a plausible contributor to repeated selection,
not a proven diagnosis of the tester's specific Sim picker.

Offline checks pass: 39 cfg checks, 43 speech-mode checks, 9 scanner/settings
tests, 9 navigation/backend tests, 10 contextual-input/phone tests, 5 hub
tests. Main gate passed 61 targeted comparisons; compatibility passed 19.
The staged archive matches all 14 source modules. Resource sets remain
exactly 24+6; class sets and non-code tags match the inputs.

All three installed files match build/v7-deployment.json. The cfg was
preserved; installed V6 rollback files are in build/deployed-before-v7.
Main-menu access remains unresolved; a separate startup probe is not part
of the deployment. See INTEGRATION-STATUS-V7.md for the remaining planned
and glaroc features, including those not implemented in this pass.
