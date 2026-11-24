# Contribution controls and testing

## Build Helper

Press `Alt+B` in Build mode to open the Build Helper. The retained local extensions add these menu actions; they do not have separate global shortcuts:

While the contribution is loaded, its menu wrapper hides the baseline **Put a roof on my house** and **Describe the lot** rows. Their code is unchanged; removing the contribution restores both rows.

- Build my house (unified presets and configurable stories)
- Build a detached small structure
- Lot planning grid
- Turn lot planning descriptions off
- Describe detected buildings
- Name the building here
- Describe the lot and buildings
- Describe this build
- Accessible roof builder
- Describe roof level
- Chimney assistant
- Stair-shape diagnostics

## Detached sheds, garages, winter gardens and party houses

1. Enter Build mode with `F2`.
2. Turn on Build-grid placement with `Ctrl+Alt+B`.
3. Use the arrow keys to move to the intended **northwest corner** of the new structure.
4. Press `Alt+B` and choose **Build a detached small structure**.
5. Choose the preset, room layout, entrance side, building name and room names.
6. Review the announced footprint and choose **Build it**.
7. After all rooms and doors are verified, choose the roof.

The winter-garden preset builds an enclosed room. Add large windows afterward using the existing catalog and wall-placement workflow.

## Lot planning and building names

- `Alt+B`, **Lot planning grid**: enable enhanced tile descriptions and enter the Build grid.
- Arrow keys: move one tile and hear building, room, pool, exterior flooring, landscaping, occupied ground or apparently clear outdoor ground.
- `Page Up` / `Page Down`: change floor.
- `Alt+B`, **Name the building here**: name the building containing the current cursor tile.
- `Alt+B`, **Describe detected buildings**: hear neutral footprint, room, floor, door and window counts.
- `Alt+B`, **Turn lot planning descriptions off**: return to ordinary Build-grid announcements.
- `Escape`: leave the ordinary Build grid. This does not erase building names.

## Contribution shortcuts

To place a TV or other compatible catalog object on furniture: select the ground layer, press `1` until the supporting furniture is announced as **Focused**, then press Enter. A full or incompatible surface refuses purchase. Objects merely listed in “Objects here” are not selected surface targets. This path requires in-game testing with the chosen TV and stand.

- `Ctrl+Alt+,`: previous scanner range.
- `Ctrl+Alt+.`: next scanner range.
- `M` in the Build grid: select the furniture at the cursor to move; navigate and press `M` again to place it. `Escape` cancels.
- `Ctrl+Alt+U`: raise the selected target layer/wall-object height.
- `Ctrl+Alt+D`: lower the selected target layer/wall-object height.

Scanner scopes cycle through 6, 12, 24 and 40 metres, whole lot, this floor and this room. Sims remain unlimited in metre-based scopes.

## Existing updated-mod Build-grid controls used by the contribution

- `Ctrl+Alt+B`: toggle Build placement from the lot grid.
- Arrow keys: move one tile while the Build grid owns input.
- `Page Up` / `Page Down`: change floor.
- `R` and `Shift+R`: rotate in the directions supported by the updated mod.
- `Enter`: place the selected catalog object when the game validates it.
- Number row `1` to `6`: read Build-grid detail topics. Repeated `1` presses cycle separately through furniture and attached contents such as a television on a stand.
- `Space`: repeat the current grid announcement.
- `Ctrl+Alt+Z` / `Ctrl+Alt+Y`: undo / redo.
- `Ctrl+Alt+X`: sell the supported object at the cursor.
- `Ctrl+Alt+L`: toggle diagnostic logging.
- `Ctrl+Alt+I`: catalog search.
- `Ctrl+Alt+J`: native room-label list; `a11y.roomlabel <name>` sets a custom name.

## Chair orientation hints

No new shortcut is required. With a dining chair or desk chair selected, ordinary movement, rotation, number 5, and repeat announcements retain the mod's fit result and append the nearest compatible dining table or desk within two tiles. The optional setting is **chair-to-table orientation hints**.

## What still requires in-game testing

The source, bytecode, plan geometry and archive structure were verified outside the game. The Sims 4 performs the final room, door, stair, roof and object placement through its Build UI. Those workers move or drag the game cursor, then inspect the resulting game state and stop when the result differs from the requested geometry. Testing in-game confirms that camera projection, catalog selection and the current game patch allow those mouse-driven actions on the test lot.

If something fails, leave logging enabled, reproduce it once, and keep the TS4 Access log. Relevant contribution lines begin with `contrib:`, `wall:`, `room bridge:`, `surfaces:`, `layers:`, `roof tools:`, `house planner:`, `lot grid:`, `detached builder:`, or `chair alignment:`.

## Native chair snapping (experimental)

Choose a dining or desk chair. Face the adjacent table/desk from the Build cursor, or focus that table/desk with number 1 on the ground layer. Enter uses the closest game-validated native chair slot. The preview identifies the table and seat location; native slot rotation applies automatically. Full or invalid seats refuse purchase. The separate **experimental chair snapping** setting can disable this path while retaining orientation hints.
