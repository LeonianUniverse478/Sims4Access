# Action queue window (2026-09-30)

## Behavior change

Ctrl+Alt+Q (new chord) and the accessibility menu's Action queue row, which replaces the "Current action" row, open a native picker of the active Sim's interaction queue.
- Rows follow EA's queue icons: running actions first (super interactions, group activities, and the posture icon), then waiting actions in order. Canceled entries are hidden.
- Each row is named with the icon's own `display_name`. Its description gives the state ("Doing now", "Current posture", "Waiting, 2 of 3"), who chose it (`is_autonomous`: "Chosen by the Sim"; `is_user_directed`: "Chosen by you"), and "Enter cancels" or "This action cannot be canceled."
- Enter cancels that action. With more than one cancelable action, a first row cancels them all. An empty queue says so.
- The chord refuses over a dialog, picker or focused panel ("Close the current menu or dialog first.") and is ignored while typing. Ownership is checked again on the pump turn.

## Source of truth (game 1.128.90 bytecode)

- Queue icons come from `sim.ui_manager.get_interactions_gen()` (`InteractionInfo`: `display_name`, `user_cancelable`, `canceled`, `ui_state` IQ_QUEUED/IQ_RUNNING/IQ_TRANSITIONING, `is_visual_type_posture()`).
- The icon's cancel is `InteractionButton.RequestCancel` -> `interactions.cancel_si id context`. Its handler, `cancel_common`, does `sim.find_interaction_by_id(id)`, else `find_continuation_by_id(id)`, then `cancel_user(cancel_reason_msg=...)`. The window does the same on the simulation thread after re-finding the active Sim and action. `interactions.run_first` is a debug command, not a queue control, and is not used.
- `is_autonomous`, `is_user_directed` and `user_cancelable` are properties on Interaction; `is_visual_type_posture` is a method on InteractionInfo (checked in the class bodies).

No Flash change. Files: Scripts/tyjokr_a11y_hub.py, tyjokr_a11y_keys.py, tyjokr_a11y_shortcuts.py, tyjokr_a11y_lang.py, CONTROLS.txt, docs/patreon/03, tools/test_action_queue.py (new, 8 tests).

## Evidence

- The first `Dev.ps1 build` stopped at tests: `tools/test_scanner_v5.py` pins the complete chord inventory (each addition dated, like C on 2026-09-27). Q was added to that list with a dated comment; the swallow-set check itself is unchanged. This was a stale expectation, not a behavior fix.
- Rebuild: exit 0, dist `2026-09-30_094001`. `build/v10-checks.json`: passed true, input_stable true, 1,238 checks across 78 suites.
- Main fidelity gate PASSED; compat fidelity gate PASSED (19 targeted comparisons). UI packages are unchanged from the mood round, as expected with no Flash change.
- SHA256: TS4_Access.ts4script `be253e24e9f9206a9dfc4da8928fae0a4ca7fade06a5d05bfff932a39459ae8e`, TS4_Access_UI.package `57115170de17ffcd5030c085247d8cb77c54867bf163ca55bb84809013f9de3c`.
- Installed to Leo's Mods root on 2026-09-30 with the game closed; hashes verified; cfg unchanged. Live testing pending.

## Live result

2026-09-30: Leo tested the installed build (dist 2026-09-30_103043) on game 1.128.90 and reported that the feature works flawlessly. Screen reader, voice, save and the exact cases tried are not yet recorded.
