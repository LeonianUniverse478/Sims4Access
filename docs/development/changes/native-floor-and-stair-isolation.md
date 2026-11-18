# Native floors and isolated stair plans

- Build helpers verify floor changes using the game's BBGetLevelInfo (current/minimum/maximum), rather than inferring a floor from camera height. One key is acknowledged before another is sent; out-of-range floors and unanswered queries stop construction.
- Stair transitions belong to the running house plan and are cleared on every exit. Failed stacked/basement plans cannot change the stairs in a later ordinary house.

Changed code: Scripts/tyjokr_a11y_build_helpers.py (native query transport, set_floor, house/stair wrappers, install); flash/extra-classes/ControlPanel.as (one read-only message listener and A11yNativeFloorQuery, next to RefreshFloorData).

Only the helper bytecode and GameTray UI resource change. UI Cheats compatibility is unchanged. Live confirmation of complete door/stair placement is pending.
