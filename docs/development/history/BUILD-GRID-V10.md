> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# Native Build cursor and read-only lot grid

Implementation added September 15, 2026. Offline state/lifecycle checks pass.
Native placement acceptance still requires the live checks below; this file is
not evidence that those checks have happened.

## Native Build cursor

`a11y.build on` enables an explicit **screen-coordinate** keyboard cursor.
The existing accessible catalog selects an object through the native catalog.
`left`, `right`, `up`, and `down` move in 16-pixel steps; `fine` selects 4 pixels,
`coarse` alternates 64 and 16 pixels, and `center` centers the viewport.
`click` selects/picks up or attempts to place at the cursor using EA's active
tool. `cancel`, `rotateleft`, `rotateright`, `undo`, and `redo` use EA's normal
client tool and history operations. `status` repeats the cursor position and
latest native object name/error; `off` releases the virtual cursor.

The native client retains its object creation, placement validity, footprints,
funds, snapping, rotation, routing updates, and undo history. No server-side
object spawning, `move_to`, funds manipulation, or separate undo stack is used.
Requests are announced as requests. A void service call is never interpreted
as successful placement. The native undo/redo button enabled state is checked.

The cursor follows EA's catalog upper boundary and avoids the top toolbar.
It retires on leaving Build, opening a real dialog/text field, disabling
keyboard access, or expiration of the keyboard lease. It allows the ordinary
catalog to remain open during placement. Clicks refuse an explicitly selected
sledgehammer, eyedropper, redesign, or whole-house/lot-move tool. Native errors
and hovered object names are listened to without replacing EA's listeners.

`a11y.build grid` explicitly aims at the current read-only grid point through
EA's native `BindDisplayObject` world-to-screen projection. It snapshots the
validated lot point, allowed floor and actual terrain height, binds an invisible
noninteractive Sprite, and waits for at least two Flash frames. A finite,
visible native projection inside the Build viewport enables the cursor there.
This **does not click or place an object**. The marker is unbound and removed
after the projection, after 1.5 seconds, or on cancel/zone/context/lease changes.
The grid and native cursor retain exclusive keyboard ownership only after their
preconditions pass; failed startup does not silently disable the other mode.

Native projection timing/coordinates still need the live acceptance test. The
grid's world height is exact for its sampled floor, but the current visible
Build floor and native snapping still determine what a later click hits.
No pre-commit footprint-validity response was found in the reviewed interfaces.
Walls, rooms, roofs, stairs, drag drawing and terrain sculpting are not an
implemented keyboard construction workflow.

## Read-only lot grid

`a11y.grid on` starts at the active Sim; directional commands sample one metre
per step. `floorup` and `floordown` use EA's permitted level limits. `status`
reads the current sample and `off` exits. This does not move the mouse, camera,
Sim or any object.

Each sample uses that floor's routing surface and its actual terrain height.
The read-only facts are native floor, pool, natural ground, inside/outside and
navmesh-point queries. Unknown results stay unknown. Object names are resolved
through the existing scanner localization bridge, with a fresh object lookup
each time; inventory objects and other floors are excluded. Names indicate
**object origins in a one-metre sample**, not occupied footprints or empty
space. A navmesh point never proves that an object will fit or that a route
will remain usable after placement. Movement stops at the active lot boundary.
Changing zones retires the cursor.

## Source evidence

References exported from the local EA 1.127.41 movies are in
`flash/build-v10-reference/scripts/`:

- `olympus/input/adapters/VirtualCursorInputAdapter.as`: `SetupVirtualCursor`
  receives enabled, restraint bounds and confirm-button modes;
  `SetVirtualCursorPosition` receives `{x,y}` in screen coordinates.
- `widgets/BuildBuy/gamepad/adapters/BuildBuyCenterAdapterBase.as`:
  `SendVirtualCursorClick()`, `BBRotateSelectedObject({value:-1/1})`,
  `BBCancelUserTool()`, and `BBOpCommand("undo"/"redo")`, followed by the
  normal `BBUndoRedo` notification. It obtains the catalog boundary from
  `GetNavigationUpperBound`.
- `widgets/BuildBuy/Inspector/BuildBuyInspectorMain.as`: native undo/redo
  enabled state, tool buttons, and native history operations.
- `widgets/BuildBuy/Context/BuildBuyContextMain.as`: `BBShowProductTooltip`
  has `{show,product}` and uses `CatalogProduct.Name`; `BBNotifyError` is
  either a LocKey object or an object with `labelKey`. These events supply
  exact native localized feedback. `BBShowCost` is only a preview, so this
  implementation does not report it as a successful purchase.
- `olympus/utils/DisplayObjectUtils.as`: `BindDisplayObject` accepts a display
  object plus `worldOffset:{x,y,z}` and `screenOffset:{x,y}`. With no margin
  argument it does not clamp the screen position. `UnbindDisplayObject`
  unregisters the same object. Build context price/controls panels use this
  native API at actual world points. `GameplayStateData.CurrentZoneId` uses
  `CallGameService("BBGetCurrentZoneId",null,true)`, rechecked while projection
  waits (see the EA ClassLibraryGamedata pcode reference).
- `EA/simulation/objects/pools/pond.py` and `pond_visualizer.py` call
  `routing.test_point_placement_in_navmesh(surface, position)`. Glaroc's
  `(routing_context, routing.Location)` version does not match these sources.
- `EA/simulation/terrain.py`: `get_terrain_height(x,z,routing_surface)`
  obtains the current floor height. `EA/simulation/routing/__init__.py`
  supplies no-argument `get_highest_level_allowed()`/`get_lowest_level_allowed()`
  usage through `build_buy`.

## Integration and checks

Run `py -3.7 tools/apply_build_cursor_v10.py` after shared TooltipManager edits,
then the normal root-owned compile and bytecode gates. The insertion helper is
idempotent and snapshots the source before the first V10 mutation if needed.
It also accepts the startup transport wrapper if that was already inserted.
The new Python files are normal `Scripts/` modules.

`py -3.7 tools/test_build_grid_v10.py` passes 20 meaningful checks: native
acknowledgement before key capture; malformed/stale/cross-zone replies;
immediate off retirement; native localized feedback; native undo routing;
read-only terrain/routing queries with the correct level and signature;
lot/floor limits; query failures; stale object origins and zone teardown.
`node tools/test_flash_build_v10.js` passes 13 additional checks executing the
actual AS3 method bodies after removing type syntax: allowed catalog versus
real modal ownership, keyboard lease teardown, native tool/history guards,
localized event forwarding, native click count and absence of success claims,
projection frame delay, validated screen bounds, timeout, zone replacement and
marker cleanup. These fixtures do not emulate the native game engine.

Live acceptance sequence, using reversible object edits and no save:

1. Select a cheap floor object from the native accessible catalog, enable the
   cursor and verify screen movement visually and in native tooltip speech.
2. Attempt placement in an invalid position and confirm the native localized
   error is spoken, funds unchanged and no object appears.
3. Rotate and place in a valid location. Confirm normal price deduction,
   footprint/snapping, native routing behavior and keyboard undo/redo.
4. Pick up an existing object, move, cancel, and confirm native restoration;
   then move and undo through the native history.
5. Open a dialog/text field and leave Build; verify cursor retirement and no
   captured scanner keys. Reopen Build and verify a fresh acknowledgement is
   required. Verify the ordinary catalog does not retire placement mode.
6. Navigate the separate read-only grid across inside/outside, pool, occupied
   samples and floors. Confirm floor height changes and no world mutation.
7. With a point visible on the correct Build floor, use `a11y.build grid`.
   Verify a native cursor move to that projected point and **no automatic
   click**. Repeat with the target outside the viewport and behind the camera;
   confirm failure plus marker cleanup. Aim, then explicitly place and undo.

Root owns actual live results and release documentation; record failures and
fix them before describing Build placement as verified.
