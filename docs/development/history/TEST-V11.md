> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# V11 startup transport: live acceptance checklist

Status (2026-09-24 17:36): final build gated and audited, release STAGED in
`dist/2026-09-24_1728/` (not uploaded); final startup/CAS smoke PASS; installed script matches ZIP byte-for-byte;
README draft awaiting the user. Use `tools/deploy_candidate_pair.py` with an
explicit verified candidate and a fresh backup directory, only with the game
closed. Earlier V9.6 restore instructions below are historical, not the current
deployment path. Detailed evidence: `COLLAB-CLAUDE-CODEX.md`.

Current evidence on game 1.128.90:

| Check | Result and evidence |
|---|---|
| Loaded-lot Tab/arrow routing | PASS on fix1 and fix2; native transport mark now arrives |
| Loaded lot -> main menu -> CAS | PASS on fix3; `build/codex-live-20260924/fix3-roundtrip.log` |
| CAS story prompt, questionnaire Escape, Cancel dialog | PASS on fix3 and again on fix4 (Claude, `build/run-d/fix4-log.txt` 16:36-16:41) |
| CAS name in Tab order; offstage HUD controls omitted | PASS on fix4, Claude live log 16:36 |
| CAS name activation opens native name editor and narrates it | PASS on fix5b (Codex, `build/codex-live-20260924/fix5b-cas.log`): 17:13:46 "First Name", 17:14:17 "First Name. Test", 17:14:27 "Last Name. Reader"; Shift+Tab back; Escape closes without a ghost ring |
| Console submit cannot activate a background control | PASS live on fix4: `a11y.menu window` from the console left row 1 unchanged (16:41); 25-check keyboard suite incl. three transition regressions |
| Offline checks | 326 checks across 22 isolated suites PASS on the frozen final source (`build/final-v11-full`); includes repeated imported checks |
| Keyboard off and startup speech off at boot | PASS on the full fix4 pair (Codex, `build/codex-live-20260924/startup-profiles/`): keyboard off -> listener 45994, Tab silent, pointer narration works; startup speech off -> no listener, silent menu; cfg restored byte-exact |
| Full package fidelity and final smoke | Final chain `final-v11` (fix5b template, piecreate removed): main gate 61 PASS, compat gate 19 PASS, independent 24+6+18 audit PASS; staged `dist/2026-09-24_1728/` (release archive sha b002c5dc..., UI sha e32a22c6..., compat sha 4670025d... in a separate zip); final startup/CAS smoke PASS (Codex, `build/codex-live-20260924/final-release-smoke.log`); installed script byte-identical to ZIP |
| Leave dialog Tab ring skips "Close - ESC" | PASS on fix5 (Codex 17:05): Main Menu -> Reset Current Household -> Main Menu; Escape closes |
| Settings window from the console (stability) | PASS on fix1..fix4: opens, Tab reaches close, Escape closes; captions Unicode + 560-char wrap PASS (Codex, fix1) |
| Native typing in the CAS name editor | PASS on fix5: first name typing, Tab to last name, Escape cancels without saving |
| World scanner via held Ctrl+Alt chords (no focus owner) | PENDING: hook arm/disarm and chord consumption proven with 250 ms held SendInput chords (15:03, walker moved in the HUD, Ctrl+Alt+H opened the hub); scanner category/item announcements not yet exercised with a held chord and no focus owner; `a11y.scan` from the console proves the scanner core (275 items, 16:26). Codex's tool cannot hold modifiers; physical held-key acceptance remains a human test |

Narration evidence is game log output and visible UI/captions. No NVDA/JAWS
speech-pack acceptance is claimed; this machine uses the SAPI fallback.

Log lines to expect (`Mods/tyjokr_ScreenReader/tyjokr_ScreenReader.log`,
cfg `[speech] logging = on`):

- `startup: same-process-only loopback listener ready on port 45993` (45994
  when `[features] keyboard = off`)
- `startup: UI Socket connected (outbound only, port 45993)`
- `startup: shared UI ready: startup-v11-ClassLibraryGamedata-port45993-active`
- `startup: shared UI ready: keyboard-native-guards-11`
- after loading a save: `startup: transport switched to native loaded client`
- back at the main menu: `startup: shared UI ready: startup-v11-active`

Checks, in order (each on its own launch when marked *):

1. * Boot to the main menu three times. No crash, socket connected within
   a minute, no `Socket unavailable`. (V10 crashed once at boot.)
2. Main menu: Tab narrates Options/HOME/Resume Game/etc.; Shift+Tab goes back;
   Escape closes the marketing interstitial ("Close - ESC") when present.
3. New Game: story prompt narrated with "Dialog" prefix; **Tab now moves
   Okay!/No thanks!** (was stuck on Okay!); Left/Right still move.
4. Decline the story: CAS editor; 8 slow Tabs narrate controls; no crash.
5. Cancel, "Leaving So Soon?", Main Menu: back at the menu the log shows
   `startup-v11-active` again (dock detection).
6. Resume Game: zone loads, `transport switched to native loaded client`;
   Tab/Escape work in the lot as in V9.6; no `POST` traffic in-zone
   (nothing new in the startup lines while playing).
7. Return to the main menu from the lot (Options, Main Menu, no save):
   startup speech and Tab work again.
8. * With `[features] keyboard = off`: the listener is on 45994, the main
   menu is narrated by hover only, Tab is not consumed.
9. * With `[features] startup speech = off`: no listener; the main menu is
   silent (as V9.6) and nothing else changes.

Any crash: note the Windows Application event (Id 1000) fault offset and the
last narrated control. Fault offsets 0x112bd65/0x112be33 were the V10 socket
crashes; a repeat with V11 means the socket theory is wrong and the read-only
runtime code dump (option C in PLAN-FULLGAME.md, needs the user's OK) is next.

