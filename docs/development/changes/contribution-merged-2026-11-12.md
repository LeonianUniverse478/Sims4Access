# DaRainbowGirlXX's contribution merged into the kit's modules (2026-11-12)

Leo, as lead developer, asked for DaRainbowGirlXX's Build cursor and scanner work to be merged into our own code rather than kept as add-on modules that patch ours at run time, and for her keys to fit our keymap. This replaces the arrangement described in contribution-2026-10-16.md.

## What changed

- **No runtime patching.** tyjokr_a11y_contrib.py and tyjokr_a11y_contrib_settings.py are gone, and so are the three key-polling threads, the `_original_*` chains and the guard layer. Our modules now call her code directly:
  - **Scanner ranges** live in tyjokr_a11y_scanner.py (`RANGES`, `_in_range`, `_apply_range`, `cycle_range`). The range filter runs inside `_scan`, before the scanner's own focus restore, so her separate selection-restore code was no longer needed.
  - **Moving furniture** (`_move_key`) lives in tyjokr_a11y_grid.py.
  - **Walls, room labels, surfaces and layers** stay in their own modules (tyjokr_a11y_wall, _rooms, _surfaces, _layers) as plain functions. The grid calls them from `_wall_parts`, `_room_parts`, `_fit_parts`, `_detail`, `_sell_target` and `_build_place`.
  - **Experimental placement checks** are in `place._checks`. It no longer swaps `place.requirement` or `build_buy.is_location_pool` out temporarily. The experimental pass applies only to exact Build cursor placements.
  - **Settings** are ordinary entries: `scanner_range` in `[features]` and a new `[build cursor]` section. Her `[contribution]` section is still read, so existing cfg files keep their choices. The settings rows sit before Reload.
- **Wall height** is owned by tyjokr_a11y_layers (`wall_height`). With Layer focus off, the layer keys only set the height of a chosen wall object, as her original wall keys did.

## Keymap

Checked against every chord, the Build cursor's plain keys, TS4 Access Plus (Alt only, ignored while Ctrl is held) and NVDA.

- **Ctrl+Alt+U / Ctrl+Alt+D:** target layer up and down. Build cursor only; elsewhere they say to turn the cursor on.
  - U was the menu key long ago; the menu has been Ctrl+Alt+H for a long time.
  - The unused "screen reader installed" string still said Control Alt U and now says H.
- **Ctrl+Alt+J:** room label list. Build cursor only.
- **Ctrl+Alt+comma / Ctrl+Alt+period:** smaller and larger scanner range. These were Ctrl+comma and Ctrl+period without Alt, which put them outside our chord layer.
- **M:** move furniture, as a Build cursor key. The Flash key guard swallows it (keyCode 77 added) so the game does not also see it. Ctrl+Alt+M stays milestones.
- **Ctrl+Alt+I:** catalog search, unchanged since 2026-10-16.

## Behaviour changes, on purpose

- Escape while moving an object cancels the move only. A second Escape leaves the cursor. Before, one Escape did both.
- Room context beside walls ("Current room", "Across north") is now spoken only once one of the rooms involved has a label, and only across walls and doors, not open sides. Unlabelled houses read exactly as before.
- Entering an unlabelled room says "Inside." or "Another room.", as before, not "unlabelled room".

## Tests

- tools/test_contribution.py was rewritten (17 tests). It covers:
  - no patching left;
  - the keymap and the Flash guard;
  - chord routing;
  - settings, including the legacy section;
  - ranges;
  - wall and fence wording, and labelled room context;
  - Enter routing by requirement;
  - experimental checks only when exact;
  - the wall game tool and the column refusal;
  - layers and wall height;
  - focused sell;
  - Escape during a move.
- tools/test_scanner_v5.py and test_catalog.py pin the new chords.
