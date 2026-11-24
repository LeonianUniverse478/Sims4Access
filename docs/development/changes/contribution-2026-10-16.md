# Build cursor and scanner contribution by DaRainbowGirlXX, integrated (2026-10-16)

**DaRainbowGirlXX** sent `S4Access-Contribution-2026-10-16.zip`: six additive modules, a changelog, a developer manifest and their own compiled script. Leo asked to integrate it and to adapt anything that conflicts with the current build.

## What it adds (DaRainbowGirlXX's own CHANGELOG)

- **Scanner ranges** on Ctrl+comma and Ctrl+period: 6, 12, 24 and 40 metres, the active lot, this floor and this room. Metre ranges keep every Sim, as the scanner always has; the structural ranges filter Sims and objects alike. The range is saved.
- **Furniture moving** with M on the Build cursor, in two stages, with cancel and rollback.
- **Walls:** explicit announcements, wall side with R and Shift+R, wall-object height, and exact game validation before purchase.
- **Room labels** on Ctrl+Alt+J, saved in TS4_Access_RoomLabels.json next to the log, with labelled room transitions and both sides of a wall.
- **Experimental placement** for bare ground, water, ceiling and fence objects, each switchable, each through the game's exact placement validator.
- **Surface layers** on Ctrl+Alt+U and D. Detail key 1 focuses or cycles an object on the selected layer, and 4 adds each nearby object's layer. Move and sell use a focused target.
- All options in the settings menu and TS4_Access.cfg (`[contribution]`).

## Files

- New, as sent: Scripts/tyjokr_a11y_contrib.py, tyjokr_a11y_contrib_settings.py, tyjokr_a11y_wall.py, tyjokr_a11y_rooms.py, tyjokr_a11y_surfaces.py and tyjokr_a11y_layers.py.
- Scripts/tyjokr_a11y_scanner.py imports tyjokr_a11y_contrib at its end, as the contributor's build did. Here the import is in a try block, so a failure is logged and never stops the scanner.

## Integration changes

The contribution was written against tyjokr's **October 1 integrated test candidate**: the first return plus his 28 September feedback work, 26 modules. This kit is the 26 September handoff with every change since. Its baseline script matches `Documents\TS4_Access_nick_extracted` and the Mods backup in `Documents\Mods`.

- **The October 1 interface, added to this kit's code:**
  - `grid._sell_target()`: the object Delete would sell. `_sell_here` now uses it, with unchanged behaviour (tools/test_build_placement_routing).
  - `tiles.snapshot(level)`.
  - An optional `objects` argument on `tiles.doors`, `grid._wall_parts` and `grid._fit_parts`.
- **Wall state:** this kit's `tiles.walls` says `'wall'` where the October 1 build says `'blocked'`. `wall._blocked()` accepts both. The October 1 `'object'` state (blocked by an object) does not exist here, and such edges read as open, as before.
- **Key clash:** catalog search moved from Ctrl+Alt+D to **Ctrl+Alt+I** (Leo's choice), because D lowers the wall height and layer.
- **Guard** (tyjokr_a11y_contrib `_guard`):
  - The add-on versions of `grid._room_parts`, `_wall_parts`, `_fit_parts`, `_detail`, `_sell_target`, `place._checks` and `scanner._scan` fall back to the kit's own if they raise, and the error is logged.
  - Enter (`_build_place`) and the key handlers are not guarded, since a fallback there could act twice.
  - The integration test environment found the unguarded case: a missing game service crashed every tile description.
- **Wording change, by design:** a blocked edge with the same room on both sides (outdoors on both sides, such as a garden fence) now says "Wall or fence". Edges between two rooms, or between a room and outdoors (block IDs differ), say "Wall".

## Tests

- tools/test_contribution.py (10 tests): installation, the October interface, keys, guard fallback, both wall wordings, settings and scanner ranges.
- tools/test_build_cursor.py: the fixture gives each tile its own room, as either side of a real interior wall, and stubs `tiles.snapshot`. The surface test refuses an `'unknown'` object, since wall objects are now placed.
- tools/test_catalog.py and test_scanner_v5.py: search on I.

## Not changed, to note for review

- The contribution runs three Windows key-polling threads (GetAsyncKeyState), as Plus does: Ctrl+comma, Ctrl+period and M; Ctrl+Alt+U and D; and Ctrl+Alt+J. Polling cannot stop the game from also seeing these keys.
- Room labels are a JSON file in the Mods folder. Delete it to remove them.

## To check live

- Scanner ranges and the saved range.
- M moving an object.
- Wall objects on each wall height.
- Room labels and their announcements.
- The four experimental placements.
- That catalog search on Ctrl+Alt+I still works.

## Wall objects: the game's own Build tool (2026-10-16, live follow-up)

- **Live 1:** "Press Escape to put down the current Build tool". A11yBuildHandDrop now logs which condition refused ("hand drop denied: ...").
- **Live 2:** the hand drop worked, and the exact test refused the computed wall-line point with `MustBeAgainstWall`.
- **Live 3:** a search of 24 candidates through the same test (up to 30 cm into the room, chosen height and floor level, both facings) failed on every wall and height.
- **Change (Leo's choice):** wall objects are hung by EA's Build tool, as TS4 Access Plus places doors and windows (`wall._hang_with_game_tool`):
  - `plus._reselect` puts the catalog-tree item back in the game's hand.
  - `plus.run_job` turns the camera to view the wall from inside the cursor's room, along the line from the wall point to the tile centre, so rotated lots work. It projects a point 5 cm inside the room at the chosen height and clicks it.
  - `plus.cost_check` reports success by the money spent.
  - It clicks only when the held product's name is the chosen one, because `_reselect` picks by list position. It needs a Ctrl+Alt+O choice.
  - The exact-test search was removed.
- **Live 4 (game tool):** the click reached EA's tool. On north and east walls it said "Must be placed on a wall": the click passed over walls drawn down or cut away. On the south wall, at a corner tile, it said "Must be completely supported by wall", so the object overhung.
- **Fix:** before the job, `A11yWallsUp` saves BBGetWallMode and sets WallViewMode.WALLS_UP (2), as EA's Home/End cycle does. `A11yWallsRestore` puts the player's mode back after the click, or after a 15-second fallback timer. CONTROLS explains "completely supported" (move away from corners, doors and windows).
- **Live 5 (2026-10-17):** still "Must be placed on a wall". Every refused try, across two sessions, was on or beside the tile reading "Annesley Square Column. Wall west". The house has real walls: interior and exterior doors and windows were read on the same walk.
- **Changes:**
  - A tile with a Build_Column-tagged object refuses with advice to move along the wall (`wall._column_here`, using scanner._tag_names). A sofa below a picture is not refused.
  - Plus `_flash_reply` logs the wallsup and wallsrestored replies, so the wall view switch can be confirmed in the log.
