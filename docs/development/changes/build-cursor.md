# Build cursor: tile-by-tile placement on plain keys (2026-09-30)

Leo asked for Build placement that works like RimWorld Access's map cursor: plain arrow keys move tile by tile and read each tile, so a blind player knows where furniture is and can place with confidence on the floor or on surfaces. R rotates, and when an object does not fit, the mod says why and offers a spot where it does. Leo asked for it all in one round.

## Behavior

Ctrl+Alt+B in Build mode now starts the **Build cursor** whenever the lot provides a frame (lot.corners). Without a frame, the previous grid runs unchanged.

- **Keys.** Plain keys belong to the cursor while it owns input (not over a dialog, picker, HUD browsing, text field or the pixel Build cursor).
  - Arrows move one tile along the lot's own grid; Up is north (the lot's +j axis). Arrows repeat when held.
  - Page Up and Page Down change floor. Enter places. R turns clockwise and Shift+R counterclockwise. Space re-reads the tile.
  - 1 to 6 are detail topics: objects, floor, walls and doors, nearby, chosen object, position. Home jumps to the last placed object. Delete sells (twice).
  - Escape or Backspace turns the cursor off. Tab returns to the catalog, and Escape there comes back.
  - The Ctrl+Alt chords still work.
- **Readout on each step.**
  - An "Outside", "Inside" or "Another room" change first.
  - Then the top-level objects covering the tile by footprint (Sims included), with anything slotted on them and their free spots. Otherwise pool, empty ground or empty floor.
  - Then walls and doors around the tile, then the chosen object's fit at the current facing.
  - Starting the cursor names the side of the lot facing the street (the edge nearest lot.get_default_position()).
- **Placement.**
  - Enter tests fit at the tile (centre, then edges, then corners, so two-tile objects sit on a tile edge) with EA's placement test.
  - If it fits, the object is bought and placed there exactly, at the chosen facing. The existing flow is unchanged: the client drops EA's held product first, then the real object is re-tested, the charge is exact, and undo is available.
  - If it does not fit, the player hears EA's reason (mapped to wall, something in the way, floor, slope, water, lot edge, or generic) and the nearest tile within 5 where it fits. The current facing is preferred among equally near tiles. A second Enter (same tile, facing and product, within 20 s) places it there.
  - Surface (slot) objects keep the existing free-slot search at the tile. Wall, ceiling, fence, water and terrain objects keep their existing refusals.
  - The placement announcement gives the facing and the covered tiles, and the cursor moves onto the object.

## Source of truth (game 1.128.90 decompile)

- Lot frame: lot.corners, lot.size_x, lot.size_z (used by EA), lot.get_default_position(), lot.get_front_door().
- Footprint: `obj.footprint_polygon.contains(point)` (HasFootprintComponent, routing.connectivity).
- Walls: `routing.ray_test_verbose(start, end, context, return_object_id=True)` between tile centres, read as ScriptObject.check_line_of_sight reads it: RAYCAST_HIT_TYPE_IMPASSABLE with blocking id 0 means a wall or fence. The context is the active Sim's raycast_context(). Locations use `routing.Location(position, Quaternion.IDENTITY(), surface)`.
- Fit: `build_buy.test_location_for_object(obj, definition_id, sims4.math.Location(Transform(point, yaw), surface), ignore)`, as RuntimeSlot.is_valid_for_placement and Puddle.evaporate call it. Before purchase it is tested with obj None, and again with the real object before move_to. An exception counts as "not asked", never as fitting, except in the final re-test after a passing pre-check.
- Rooms: `build_buy.get_block_id(zone, point, level)`. EA's Python never calls it, so its signature is unverified. It is optional and silent on failure.
- Doors: objects whose class hierarchy includes `Door`, near a tile edge midpoint.

## Transport

- Flash→Python: `a11y.buildgridowner 0|1` on change (like a11y.scannerowner).
- Python→Flash: `A11yBuildGridOn` and `A11yBuildGridOff` UI messages. On sets mA11yBuildGridOn and silently releases a catalog that owns the keys.
- The flag clears on a HUD mode change. Loaded-zone only, so there is no startup-socket channel.
- A11yGuardValid consumes the cursor's keys only while A11yBuildGridOwner is true, re-derived at the key after A11yModalFrame. The newly guarded keys (33, 34, 36, 46, 49-54, 82; R also with Shift) return false in every other situation, so pickers, dialogs and text fields keep them.

## Files

- Scripts/tyjokr_a11y_tiles.py (new).
- Scripts/tyjokr_a11y_grid.py (the Build cursor; plain grid unchanged when inactive).
- Scripts/tyjokr_a11y_place.py (exact placement and announcement, catalog message while placing).
- Scripts/tyjokr_a11y_keys.py (routing and owner command).
- flash/TooltipManager_patched.as.
- CONTROLS.txt, README.txt, docs/patreon/04.
- Tests: tools/test_build_cursor.py (25), tools/test_place_exact.py (3), tools/test_build_cursor.js (14 checks).

## Evidence

- `Dev.ps1 build` exit 0, dist `2026-09-30_172831` (26 modules; tyjokr_a11y_tiles.pyc confirmed in the archive). `build/v10-checks.json`: passed true, input_stable true, 1,328 checks across 86 suites.
- Main fidelity gate PASSED; compat fidelity gate PASSED (19 targeted comparisons).
- SHA256: TS4_Access.ts4script `0b60bd4c74850e697d2068d8e5259af7217931c8b038ee196b9b3022cef07011`, TS4_Access_UI.package `e734a00e01ca7d2918bb5f5799827cc13933e2143be6e1da698fb113b2bc9d2c`, compat `d8d59c74885f518642fcf66959b63501d9ad8509c4fdf7d195b9617c9da446c5`.
- Installed to Leo's Mods root on 2026-09-30 with the game closed; hashes verified; cfg unchanged.

## Needs live testing (none of this has run in game yet)

- Axis and handedness. North and east are the lot's own axes, derived from lot.corners order. Check that Right really is east of Up, that facings match what a sighted player sees, and that the object's front faces the named direction. The yaw convention is atan2(x, z); this may need a flip after the first live test.
- The fit test at tile centre and edges for 1x1, 1x2 and 2x2 objects, and EA's error strings (logged once each as `tiles: placement refused: ...`), so the reason mapping can be refined.
- Wall detection through ray_test_verbose with the Sim's raycast context, doors, and whether get_block_id answers.
- That R, the number keys, Home, Delete and Page Up/Down are consumed only while the cursor owns input, and that EA's own Build hotkeys and camera are unaffected otherwise.
- Speed of the per-step readout and of the nearest-fit search on a furnished lot.

## Live result

2026-09-30: Leo tested dist 2026-09-30_180756 (the Build cursor with the catalog follow-up) on game 1.128.90. He reported that the arrow-key readout gives all the information needed to know whether an item can be placed, that placing items where he wants them works and is much easier than before, and that placing on counters and tables is easy. Screen reader and voice, and the exact objects tried, are not yet recorded.
