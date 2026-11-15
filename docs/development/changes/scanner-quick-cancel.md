# Cancel actions directly from the Live scanner

Q cancels the active Sim's current cancelable action. When several actions
are running, it prefers the primary action and skips posture icons. Shift+Q
cancels every cancelable running and waiting action. Ctrl+Alt+Q still opens
the action queue.

The two native key bindings consume Q only while the Live scanner owns
input. The existing keyboard poller dispatches each press once and checks
ownership again on the simulation thread. Cancellation uses the same
interaction ID lookup and `cancel_user` call as the queue picker. If EA's
UIManager has no icons, the shortcuts read the Sim's running and queued
interactions and use their native queue visual type to identify postures.

Offline tests cover selection, continuations, cancelability, stale input,
held keys, modifiers and native guard ownership. The Build cursor test now
checks that its existing keys are present, allowing other bindings to be
added. The shortcut help test counts and checks the new spoken entry.
This standalone change has not been tested in a live game session.

Contributor: Ar-Anaviel.
