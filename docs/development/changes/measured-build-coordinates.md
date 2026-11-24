# Measured build coordinates

- `Scripts/tyjokr_a11y_build_coordinates.py`: separate coordinate/input boundary. Native probe supplies stage dimensions, scale mode/alignment, layout bounds and world projection; maps UI -> client -> screen once in a scoped per-monitor worker DPI context. Uses live client origin/size and virtual-desktop bounds, not Options.ini or a fixed resolution. Context is restored on all paths.
- Existing click/drag helpers are retained. Wrapped input checks focus, geometry/DPI/style, native Build Mode/dialog state and physical pointer arrival before mouse-down; aborts release only helper-owned mouse state. Shift cleanup is protected on errors. Mode/focus/resize changes interrupt a drag. Parking remains inside the current game client and never affects an unfocused window.
- `contrib-reference/modules/tyjokr_a11y_contrib.py`: installs the adapter after the other contribution modules.
- `flash/TooltipManager_patched.as`: independent `A11yCoordinate*` marker, frame callback/cleanup and one `coords` encoded route. Reports `a11y.coords_enc`; never enables/moves a virtual cursor or confirms placement. Existing Build cursor paths are unchanged.
- `tools/test_build_coordinates.py` / `test_coordinate_probe.js`: resolution/DPI/origin/style matrix, standard stage fit modes, input fences/cleanup, stale replies, no-action preflight and native marker lifecycle. CHEATS.txt: `a11y.buildcoords [delay]`.

Evidence: live Windows capture was 2880x1800 at 200%, while the installed builder divided it to 1440x900. Cursor positions and explicit Windows physical conversion agreed. The successful 22:48 live probe confirmed native stage/layout/client dimensions of 2880x1800, noScale, alignment LT, and projection (1389.65,1231.64) mapping directly to physical (1390,1232). The installed planner lacked the checkout's earlier coordinate overrides; this adapter is explicitly wired into the deployed contribution loader.

Stage fit semantics follow the [AIR/AS3 Stage scale-mode contract](https://airsdk.dev/docs/development/display/display-programming/working-with-display-objects/setting-stage-properties). UI scale is already represented by the native display transform; no extra UI/DPI percentage is applied. Unknown modes and cropped/out-of-window points are refused. Alignment is used only for uniform showAll/noBorder fitting; these modes accept either axis order and reject unknown alignment. Raw native replies are logged before validation.

Live sequence: in Build Mode enable logging, run `a11y.buildcoords 5`, close the console, wait up to eight seconds. Inspect `build coordinates: preflight` and `measure` before testing a helper against a backed-up save. Compare planned and game-created room footprints. Read-only projection alone does not prove actual drawing succeeded.

Rollback: restore the previous paired script/UI packages or reverse the source patch and remove the coordinate module/loader hook.
