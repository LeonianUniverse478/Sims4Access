# Native floor actions

- `Scripts/tyjokr_a11y_ground.py`: opens a native PICK_FLOOR menu at the active Sim's horizontal position/current level, using the game's floor-height query and target ID zero. Refuses Build Mode, missing actors/lots, off-lot and invalid coordinates/heights. Logs requests/errors. Does not queue an interaction, choose a vacuum action, move the pointer or change scanner focus.
- `Scripts/tyjokr_a11y_hub.py`: one lazy callback and one Accessibility row, Floor actions here, beside Self interactions.
- `tools/test_ground_actions.py`, `tools/test_scanner_pick_bridge.js`: actor/floor/coordinate guards and actual existing Flash pick-to-interactions.choices transport.

Current installed server.pick_info defines PICK_FLOOR=5 and includes it in PICK_USE_TERRAIN_OBJECT. Native generate_choices accepts target zero; _get_targets_from_pick creates TerrainPoint at the supplied world position/level. Existing PieMenuMain owns the request counter and normal menu response. No Flash changes or manual DPI conversion.

The game determines which actions are available, their requirements and cleaning scope. Vacuum-entire-story behavior requires an in-game test with the relevant pack/vacuum. This targets the floor at the Sim, rather than searching for an unoccupied tile or choosing a distant location.

Rollback: revert the hub callback/row and remove the ground module; restore the previous script archive. UI packages remain unchanged.
