# Browse event goals with V

Press V in Live mode to read the current event's goals without first opening
event management. If exactly one named, user-facing event is running, V opens
its goals directly. If several are running, it opens an event picker; Enter
opens the selected event's goals and Escape cancels. This deliberately avoids
guessing which simultaneous event the player meant from a remembered HUD tab.
Ctrl+Alt+V still opens the existing running-event management menu.

This revision builds on the native event-goal reader added to dev on 18 November.
Both entry points use `tyjokr_a11y_event_goals.open_goals(situation_id)` and the
same request/zone identity checks, timeout, exact-ID HUD lookup, native goal
text/tooltips, focus and cleanup. It does not add a second goal collector or
calculate progress. The game retains authority over goals and their visibility.
Arrows browse native goals; Escape leaves the existing reader. No events gives
the existing no-events message; an event without an available goal HUD uses the
reader's existing unavailable message.
If the native goal container is visible but empty, wait for its delayed rows
using the existing 150-frame scope limit. If no readable row arrives, release
only that event's scope and frame listener and announce the same unavailable
message once. Do not leave an empty status scope owning scanner input. Other
panels, including photography (which shares the lifecycle), keep their existing
timeout behaviour.

V uses EA's `InputAction` guard in TooltipManager, not another keyboard poller.
While keyboard navigation owns it, it replaces native video recording. It is
not taken in text fields, modal or pending modal scopes, Build mode, startup,
or after the keyboard lease expires. The simulation-thread command rechecks
editing/blocking ownership and the lot before opening a picker. Picker callbacks
recheck the lot, and `open_goals` revalidates the event before requesting its HUD.
The shared native reader now also checks editing and startup, alongside its
existing modal/keyboard/Live checks, before opening the requested HUD.
Zone IDs remain strings through Flash/command transport so 64-bit identities
are not rounded. The command is loaded-zone only; startup needs no new channel.

Tests exercise the actual Flash guard and request dispatch, single/multiple/no
events, exact large IDs, selector callbacks, ended events, travel and blocking
races, and the existing request/timeout lifecycle. Shortcut help includes V.
The old PR's independent goal-traversal fixture was replaced because traversal
is now owned and tested by the upstream reader. The narrator also translates
the existing event-unavailable token when Flash reports an empty-scope timeout.
The two new help/picker strings use English source text. A delayed row on frame
150, a truly empty event, retained unrelated focus, one-shot feedback and the
unchanged photography timeout are covered by native-shaped source fixtures.

Live testing remains pending: a scored date, an unscored event, simultaneous
events, Escape back to the scanner, text input, and travel or event completion
while the selector/goal reader is open. Offline tests do not establish actual
screen-reader narration or Flash runtime behaviour.
