> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# V12 (script-only): household Sim shortcuts + generated keyboard-shortcut readout

Status (2026-09-24 19:00): v12 installed script-only over the final-v11 UI package
(Codex, backup `build/codex-deployed-before-v12`); hub readout PASS (Codex) and
held-chord items PASS (Claude). Not in the staged v11 release zip: a v12 release
needs the staging run again (script only; UI and compat unchanged).

## What changed (source frozen)

- `Scripts/tyjokr_a11y_keys.py`: Ctrl+Alt+1..8 -> switch to household Sim N
  (glaroc's layout; selectable order). Silent while typing; spoken refusal
  "Close the current panel or dialog before switching Sims." while any
  dialog, picker or focused panel owns the keys; the switch runs on the
  simulation pump and re-checks epoch/editing/modal there; existing
  `hub.select_sim` performs the switch and speaks the name; out of range or
  no client -> "This Sim is not available."; pump refused -> "No lot loaded".
- `Scripts/tyjokr_a11y_shortcuts.py` (new): spoken readout generated from the
  live keys.py tables (plain bindings, Shift+Tab, Ctrl+Shift+N, every
  Ctrl+Alt chord with its meaning, numpad section only when that setting is
  on). Hub row "Keyboard shortcuts" (was "Scanner help"); the scanner's help
  path speaks the same readout; one explicit utterance (R reads again/stops).
- lang: header/context/section terms, English with fallback.

## Evidence

| Check | Result |
|---|---|
| Offline suites | 345 checks / 24 suites PASS (Codex full runner; `build/v12-shortcuts-candidate/stable-checks.json`); sim chords 10, shortcuts 9, keyboard 25 |
| Artifact | ts4script 248,272 B sha256 465719fb663cd75643b252f076af26a8590159894fb3866e442398244ce6f3cd, 19 members incl. ctypes/, portable filenames; UI unchanged sha e32a22c6... |
| Hub "Keyboard shortcuts" row (console `a11y.hub`, native picker) speaks the full readout | PASS (Codex 18:50:31): native picker click after scrolling; one full SPEAK[tq] entry through household Sim 8, numpad correctly absent while disabled. Evidence: build/codex-live-20260924/v12-hub-smoke.log. No heard-audio claim. |
| Ctrl+Alt+H with a dialog open still speaks the short dialog help, not the readout | PASS (Claude, held SendInput chord, 18:55): Escape menu open, Ctrl+Alt+H -> "Dialog. Up and down move between controls..." (`build/v12-shortcuts-candidate/claude-chord-run.log`) |
| Ctrl+Alt+2 switches the controlled Sim and speaks the name; Ctrl+Alt+1 with a dialog open refuses with speech; out-of-range digit says unavailable | PASS (Claude, held SendInput chords, 18:54-18:55): Ctrl+Alt+2 -> "Evie Darden"; Ctrl+Alt+8 -> "This Sim is not available."; Ctrl+Alt+1 -> "Zadie Corral"; Tab onto the HUD then Ctrl+Alt+2 -> "Close the current panel or dialog before switching Sims."; Escape released; same log |

No heard-audio claim; narration evidence is the mod log.

## Live steps

1. Resume a lot with at least two household Sims; keyboard on; no panel open.
2. Console `a11y.hub`, Down to "Keyboard shortcuts", Enter: one long utterance
   listing UI controls, then the Ctrl+Alt chords including "Control + Alt + 1:
   control household Sim 1" ... 8, numpad section only if enabled.
3. Open any dialog, Ctrl+Alt+H: the short dialog help, not the readout.
4. World, no owner: hold Ctrl+Alt, press 2 -> the second Sim's name; the HUD
   portrait changes. Press 9 -> nothing bound. Press a digit beyond the
   household size -> "This Sim is not available."
5. Open a panel (Tab into the HUD) then Ctrl+Alt+1 -> refusal sentence, no
   switch; Escape, repeat -> switch.
