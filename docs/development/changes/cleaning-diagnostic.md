# Cleaning-state diagnostic

- `diagnostics/tyjokr_a11y_cleaning_diagnostic.py`: standalone, read-only `a11y.inspect_cleaning [limit]`; default 500, maximum 2000 active-lot objects. Zero cancels. Inspect at most 10 objects per pump callback with a 4 ms soft budget, 10000 visited IDs, 64 states and 256 static affordances per object. Logs truncation, cancellation, zone changes and errors.
- Logs definition/class, position/floor, hidden status, state/value resource names and IDs, linked-stat identifiers and cleaning-related static affordance hints. It never evaluates interactions or changes states/statistics. It does not depend on scanner distance/categories/availability filters.
- Native API checked in the installed simulation archive: StateComponent.values() returns current state values. The existing scanner uses super_affordances() for definition metadata. The native script importer enumerates ts4script members.
- `tools/test_cleaning_diagnostic.py`: read-only state collection, bounds, batching, active-lot filtering, missing states, cancellation, zone changes and stopped logging/pump.

This first snapshot establishes actual cleaning-state identities before adding dirty labels. A Clean action alone is insufficient: action availability depends on the Sim and other tests; dishes on a table are also distinct from a dirty table surface.

Rollback: remove the standalone diagnostic ts4script. Existing mod packages, settings and scanner behavior are unchanged. In-game command execution remains to be verified.
