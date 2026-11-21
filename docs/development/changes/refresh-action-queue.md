# Keep the action queue open after canceling

Pressing Enter on a queue row used to return to the world scanner. After an accepted picker reply, hold the scanner while the simulation thread cancels the chosen action and rebuilds the active Sim's queue. Request the nearest remaining row as the native selection. An empty queue stays open and Escape dismisses it.

Read the current UIManager records on each refresh. EA may retain a canceled queue icon while paused, so exclude IDs whose cancellation succeeded during this visit. Refused actions remain available. After a refresh the bulk action comes last, so clients that default to the first row focus an individual action.

Offline picker tests cover successive cancellations, refused and stale actions, a changed Sim, the empty row, and Escape. Check focus and speech continuity with a screen reader in Live mode, both paused and running.

Rebased onto the 18 November dev build. The native picker continues to work
from the new accessibility hub's Now submenu as well as Ctrl+Alt+Q. The
existing picker tests and hub routing tests pass on this baseline.

When EA temporarily provides no queue icons, the picker falls back to the
Sim's native running and waiting interactions. It preserves native posture
and cancellation flags, deduplicates IDs, and excludes finishing, canceled
and hidden noncancelable actions. Existing icons remain authoritative.
Regression tests cover missing icons, fallback cancellation and refresh,
filtering, posture labels and the unchanged icon-backed path.
