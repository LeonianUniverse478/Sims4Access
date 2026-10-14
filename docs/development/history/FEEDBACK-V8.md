> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# V8 user test results — 2026-09-15

## Confirmed by the player

- Scanner keyboard works initially; panels maximize; phone focuses apps.
- Calendar relative dates and events read correctly.
- Household funds and career workday narration work.

## Reported failures for V9

- Scanner results stay stale; only Sims, Miscellaneous and Build categories.
- Closing panels leaves navigation captured and blocks scanner and Ctrl+Alt+H.
- Needs still exposes children; Hygiene tooltip remains after leaving it.
- Inventory keyboard hover says “Cell View”; selling confirmation produced BE UI Error #1009 in CLIK input handling.
- Phone should cross pages at the first/last app with Left/Right.
- Calendar Busy portraits have no spoken names; omit the section if names cannot be resolved.
- Stay Over stops on a large wrapper; Add Holiday does not capture focus.
- Event wizard progress steps are silent focus stops; skip them.
- Close/Esc should not receive initial focus when useful content exists.
- Combine calendar season/region, weekday and weather into one focus target.
- Combine filter field and arrow; expanded filters must own navigation.
- Mood label mouse hover is now silent; restore the short mood name while keeping the description silent.
- Career/school requirements, tasks and daily task need separate focus stops and tooltips.
- Completed aspiration/career objectives need spoken completion state.

## Still untested

Incoming phone calls/texts: none occurred in the previous test session. Keep on the runtime blockers list. No passing result is claimed.

## Evidence

V8 source and the player's log/report are preserved in `build/source-before-v9/`.
BE reports a null reference at UIComponent.handleInput → FocusHandler.handleInput → InputDelegate.handleKeyPress/handleKeyDown. The report does not identify the responsible mod; this is an input-path investigation, not proven attribution.
