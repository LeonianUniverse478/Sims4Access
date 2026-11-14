# Keep the action queue open after canceling

Pressing Enter on a queue row used to return to the world scanner. After an accepted picker reply, hold the scanner while the simulation thread cancels the chosen action and rebuilds the active Sim's queue. Request the nearest remaining row as the native selection. An empty queue stays open and Escape dismisses it.

Read the current UIManager records on each refresh. EA may retain a canceled queue icon while paused, so exclude IDs whose cancellation succeeded during this visit. Refused actions remain available. After a refresh the bulk action comes last, so clients that default to the first row focus an individual action.

Offline picker tests cover successive cancellations, refused and stale actions, a changed Sim, the empty row, and Escape. Check focus and speech continuity with a screen reader in Live mode, both paused and running.
