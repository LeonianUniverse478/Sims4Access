# Build helper integration

- `Scripts/tyjokr_a11y_build_helpers.py`: release native grid key ownership for a floor change, confirm the ordered UI round trip and owner release, inject one native floor key at a time with focus/context/modifier checks, verify the reported floor and restore ownership in `finally`. Grid tile, facing, height and enabled state are preserved.
- Alt+B resolves the current `build.open_menu` at invocation, retaining the detached-structure wrapper installed after roof tools.
- `contrib-reference/modules/tyjokr_a11y_contrib.py`: install the separate helper adapter after measured coordinates.
- `tools/test_build_helpers.py`: key ownership/acknowledgement, multiple floors, abort/release paths, unchanged floor, invalid input and late menu wrappers.

Live evidence: 2026-11-09 23:22, the game verified all five ground-floor room footprints. The three upper-floor attempts were intercepted as Build-grid floor-up commands; native construction stopped with incomplete second-floor rooms. The new adapter addresses input ownership; in-game verification pending.
