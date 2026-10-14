> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# V10 acceptance work in progress

This is a test record, not a release or completion claim. V9.6 remains the
reference build. The final combined V10 package has not passed live acceptance.

## Startup transport

The isolated Socket probe connected before a save loaded and completed a random
challenge round trip. Its diagnostic files were then removed from Mods and the
V9.6 UI restored. See `STARTUP-SOCKET-PROBE-V10.md`.

The product acceptance candidate changes only ClassLibraryGamedata within the
24-resource V9.6 package. It preserves 1,077 class definitions and non-code
movie tags. The candidate's script snapshot has 16 modules; it is separate from
the evolving combined V10 build. Its artifacts and source hashes are recorded in
`build/startup-bridge-candidate-v10/verification.json`.

September 15 evening, local time:

- 23:21:02: fixed-loopback listener started.
- 23:21:09: same-process UI connection authenticated.
- 23:21:51: core ticks enabled the bridge using preserved keyboard settings.
- 23:22:19: first main-menu Tab highlighted Options Button and sent that label
  to the configured SAPI speech backend. Audio was not independently heard.
- Subsequent Tab and Enter reached Download Manager; its checked checkbox was
  narrated. Escape closed the panel and released focus.
- 23:24:12: mouse activation of New Game narrated its native label and entered
  independent CAS without loading the named save.
- CAS Stories prompt did not own keyboard scope. Tab incorrectly reached the
  disabled toolbar behind it, with its native unavailable tooltip narrated.
- 23:25:41: mouse selection of No thanks was narrated. The game crashed one
  second later. No new UI exception appeared. The textual native category/stack
  is saved in `build/startup-bridge-candidate-v10/cas-crash-summary.json`;
  compressed memory is not inspected. Attribution is unresolved pending a
  restored-V9.6 comparison.

The candidate was restored to exact V9.6 UI and script before that comparison.
At approximately 23:30–23:31, mouse New Game / No thanks on V9.6 successfully
rendered the CAS editor and a random Sim. That comparison did not use Tab in the
story prompt. The candidate regression is therefore under investigation; one
successful baseline run does not isolate its cause. The disposable baseline CAS
session was exited without saving. No named save was loaded or committed during
these startup/CAS tests.

## Offline checks so far

225 Python check executions across 16 isolated suites passed (this count includes
tests imported and executed again by later regression suites). Eleven Flash
navigation fixture checks and thirteen source-executing Build checks passed.
These checks do not establish native placement, complete CAS, physical held-key,
or assistive-technology acceptance.

## Pending live acceptance

- CAS crash comparison, scoped story prompt, base CAS editing and safe exit.
- Main-menu Load and return from a loaded game.
- Hub text rows and opening-key fence, known contacts, school/calendar/Needs polish.
- Native Build movement, projection, placement/cancel/rotation and undo/redo,
  confirmed with actual funds and object changes.
- Optional native/stage key metadata probe for short chord diagnosis.

Physical hold duration, NVDA and Polish cannot be inferred from injected short
key taps or SAPI logs. Real incoming calls remain an explicitly permitted skip.
