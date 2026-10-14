# Events: end one, or send its guests home (2026-09-30)

Leo asked for a way to end events that go on too long, and to send all of an event's participants home at once so it actually ends.

## Behavior

Ctrl+Alt+V (new chord) and the accessibility menu's new Events row open a native picker. It lists the user-facing situations the game shows (parties, dates, holidays, career events and so on), each with its name, the number of guests and the minutes left.

Enter on an event gives three rows:
- **Send all guests home and end the event** (listed first; this is what Leo asked for).
- **End the event.**
- **Send all guests home.**

Active-household and selectable Sims are never sent away. The event and its Sims are looked up again when a row is chosen ("That event has already ended."). The result is spoken: "Guests sent home: 2. The event has ended." A failure to end is logged and spoken. Like the action queue, the chord refuses over a dialog and is ignored while typing.

## Source of truth (game 1.128.90)

- The list is `services.get_zone_situation_manager().get_user_facing_situations_gen()`. Each entry gives `situation.display_name`, `all_sims_in_situation_gen()` and `_get_remaining_time_in_minutes()`.
- Ending does what `situations.pre_destroy_user_facing_situation` and `situations.destroy_user_facing_situation` do, in that order: `SituationManager.pre_destroy_situation_by_id(id)`, then `destroy_situation_by_id(id)`.
- Sending home is `SituationManager.make_sim_leave(sim)`, the game's normal leave. It falls back to `make_sim_leave_now_must_run` itself when its leave situation is missing.
- EA's tuned end-of-event dialog (`situations.show_end_situation_dialog`) is not shown; the picker row is the confirmation.

## Files

Scripts/tyjokr_a11y_hub.py (events_window, event_actions, end_event, a11y.events), Scripts/tyjokr_a11y_keys.py (the V chord), Scripts/tyjokr_a11y_shortcuts.py, Scripts/tyjokr_a11y_lang.py (en and pl), CONTROLS.txt, docs/patreon/03, tools/test_events.py (8 tests). tools/test_scanner_v5.py adds V to its pinned chord list.

## Test expectation fixed

tools/test_keyboard_chord_race.py (`test_sample_reads_modifiers_then_keys_with_nothing_between`) sliced the first 40 key reads after the modifiers and required every chord key in that slice. The poller reads every polled key exactly once in one burst (`raw = {vk: read_key(vk) for vk in all_keys}`). The Build cursor's plain keys grew that burst past 40, so with V a chord key fell outside the slice. The test now takes the whole burst up to the next sample and still asserts that no modifier is re-read inside it, that every chord key is in it, and that each key is read once. Runtime was not changed for this.

## Evidence

Full offline suite before the build: passed true, input_stable true, 1,344 checks across 88 suites. Build, install and live results follow.

- `Dev.ps1 build` exit 0, dist `2026-09-30_190128`. passed true, input_stable true, 1,344 checks. Main and compat fidelity gates PASSED (19). SHA256: TS4_Access.ts4script `e91c2751ba49430a92ef544f7f4df66cccaa813fde2b8ffd85d4e3b59e38a4cf`, TS4_Access_UI.package `0a7fad07df85172c741dadff134c427e383f298034a3ac242fe691b3e847e7f5` (unchanged). Installed to Leo's Mods root on 2026-09-30 with the game closed; hashes verified. Live testing pending.
