# DaRainbowGirlXX's second contribution, merged (2026-11-14)

Source: `s4access updated contribution.zip` (14 November 2026), built on upstream adb868c. Her own notes are in `docs/development/contrib-2026-11-14/`, and the original archive is in `exchange/contrib-2026-11-14/`.

## Leo's decisions

- Merge everything, including the house-building work.
- Her house tools replace the overlapping parts of TS4 Access Plus's Build helper (Alt+B), which is Michael Maslo's work:
  - "Build my house";
  - "Put a roof on my house";
  - "Describe the lot".
- Plus's other Build helper actions and all its other Alt keys stay.

## How it was merged

1. `CHANGES.patch` applied cleanly.
2. The five modules she kept under `contrib-reference/modules` are part of her compiled build. They now live in `Scripts`:
   - chair_alignment;
   - detached;
   - house_planner;
   - lot_grid;
   - roof_tools.
3. No module replaces another module's functions at game start any more. As sent, nine of her modules did:
   - the Build helper menu, wrapped five deep through `core.choose`;
   - the house-building step, wrapped three deep;
   - stairs;
   - the click routine;
   - projection, screen size, screen conversion, mouse, click, drag, panel checks and mouse parking;
   - floor changes;
   - the room worker and reply handler;
   - room scans and house messages;
   - the settings file and menu;
   - our Build cursor's `_fit_parts` and `_room_parts`.
4. Each wrapper keeps its body. What it used to wrap is now an explicit `_original_*` function calling the next step. Each chain ends at the engine's renamed original (`*_base`).

Where the chains now live:

- `plus_build`:
  - `open_menu` builds the merged menu directly;
  - the coordinate and input functions delegate to `build_coordinates`;
  - `point_and_act` sends overview jobs to `house_planner.overview_point_and_act`;
  - `room_worker` and `_flash_reply` go through `basement`;
  - `set_floor` goes through `build_helpers`.
- `plus_house`:
  - `_build` runs build_helpers, then detached, then house_planner, then `_build_base`;
  - `place_stairs_worker` goes through `build_helpers`;
  - `_say`, `build_my_house` and `_show_plan` go through `house_workflow`.
- `plus_rooms.scan_rooms` goes through `house_workflow`.
- `grid`:
  - `_fit_parts` goes through `chair_alignment`, then `_fit_parts_base`;
  - `_room_parts` goes through `lot_grid`, then `_room_parts_base`.
- Other modules:
  - The basement setting is an ordinary setting: `[build cursor] basement`. The old `[contribution] experimental basement` line is still read.
  - The display diagnostic is a flag set by `a11y.inspect_display`. The engine calls `observe()` for each projection.
  - The `install()` functions in build_helpers, basement, house_workflow and build_coordinates only register commands and tickers and record modules. They are idempotent.

## Found while merging

- **As sent, her click wrapper would have broken wall hanging.** It dropped the `focus_height` argument added on 12 November, which would have raised a TypeError on every wall hang. With direct calls the argument passes through.
- **Two of her overrides never had any effect.** The house planner's `_client_size` and `_client_to_screen` were always overridden by `build_coordinates`. They stay in the source but nothing uses them.
- **One test and its module were left out.** `tools/test_cleaning_diagnostic.py` needs `diagnostics/tyjokr_a11y_cleaning_diagnostic.py`, which was not in the zip. The test is held in `exchange/contrib-2026-11-14/held/`.
- **One tool was removed.** `tools/package_contribution_test.py` is her packaging script for her own test zips.

## Checks

- All 130 suites pass: 1,797 checks.
- The interface fidelity gate passed with 63 targeted comparisons. `PlexLotSelectOverlay` was added to GameEntryDock and is defined only there.
- The compat gate passed with 19 comparisons.
- Installed as `dist/2026-11-14_113106`. It has not been live-tested.
