> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# V10 startup bridge

The isolated Socket probe established a real bidirectional Flash/Python
connection before any save loaded. V10 uses that path for main-menu and
independent-CAS accessibility when no native zone client exists. The loaded
game continues to use the existing PostServerCommand/distributor path.

## Scope and implementation

- `Scripts/tyjokr_a11y_startup.py` starts one loopback-only listener and wraps
  the existing `sims4.core_services.on_tick`. The socket worker only parses
  bounded frames and queues messages; narration/context/input-fence handlers
  run from the game's core tick. No game services, objects or distributor
  calls occur on the worker.
- A fixed list of narration/state channels maps directly to existing Python
  handler functions. There is no command evaluator, arbitrary Python lookup,
  filesystem command or gameplay action accepted by this endpoint.
- Python's navigation sender and Flash's receiver separately validate the
  permitted UI messages, key-up values and configuration fields. Build/grid
  messages are excluded and continue through the loaded game's native path.
- The listener binds only `127.0.0.1`, requests Windows exclusive address
  use, and verifies that the connecting endpoint belongs to the same process
  using Microsoft's documented
  [GetExtendedTcpTable](https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/nf-iphlpapi-getextendedtcptable)
  and [MIB_TCPROW_OWNER_PID](https://learn.microsoft.com/en-us/windows/win32/api/tcpmib/ns-tcpmib-mib_tcprow_owner_pid).
  A connection from another local process is rejected. No permissive web
  socket-policy service is installed.
- A random handshake separates sessions. Disconnects clear pending input
  and speech; Flash expires native key ownership, removes old socket listeners
  and reconnects after five seconds. Idle sessions use a one-second heartbeat.
- Queues are bounded, frames are size-limited, and hovering cannot create an
  unlimited speech backlog. Scope opening suppresses already-buffered
  activation packets until Python fences its key epoch and acknowledges.
- The existing shared Gamedata TooltipManager connects without any new UI
  movie. Its normal focus walker, native labels, keyboard guards and tooltip
  narration are reused. The current DialogMain routes its own initial text
  through that manager. No CAS or EngagementLibrary override is added.

## Verification

`tools/test_startup_bridge_v10.py` currently passes nine checks, including
real TCP framing with Unicode and split/combined packets, same-process
acceptance, rejection of another process, explicit channel validation,
bounded pre-zone-only navigation, handshake, pending-message isolation and
disconnect cleanup, core-thread fence acknowledgment and native-client
handoff. These tests complement the six earlier probe checks.

For fast live acceptance, `tools/build_startup_bridge_candidate_v10.py`
freezes the current TooltipManager and Python modules under
`build/startup-bridge-candidate-v10/source`. The resulting package keeps the
24 V9.6 resources and changes only ClassLibraryGamedata. Fidelity checks
preserve all 1,077 classes and non-code tags. The other 23 movies and the
compatibility package remain V9.6 in this temporary test. It is not the
complete V10 release build.

The guarded helper `tools/deploy_startup_bridge_candidate_v10.ps1` installs
that acceptance build only over exact V9.6, while the game is closed, after
checking its verification manifest. It backs up both UI and script and
supports `-Restore`. It never writes the configuration or save.

## Runtime acceptance

The transport capability passed at startup and main menu. The first product
candidate also spoke Options, New Game and the Download Manager checkbox,
with keyboard focus movement and activation confirmed before loading a save.

The first independent-CAS trial exposed two issues. Its story introduction
was outside the generic modal stack, so Tab visited disabled toolbar controls.
After two such navigation presses, a mouse click on No thanks was followed by
a native crash. A control run of exact V9.6, using only mouse New Game and No
thanks, survived and rendered a Sim. This does not isolate the crash cause:
the control did not exercise keyboard focus, and random Sim content differed.
No protected runtime dump was inspected.

Native CASStories source explains the scope gap: CASStoriesMain adds a
CASStoriesDialog display child itself, outside DialogManager. The shared
manager now finds that visible child without changing CAS movies, displays,
native bindings or story callbacks. It traverses the native answer buttons,
announces the localized introduction and confines focus to the question.

The lifecycle review also found a concrete reentrancy hazard. The old
REMOVED_FROM_STAGE handler dispatched synthetic hover-out events into the
same control being torn down. It now only unregisters observation, clears
references and removes its ring. UIManager's existing TooltipManager.Clear
call on game-state transitions now discards retained scopes, dropdowns,
history and queued activations without dispatching hover into retiring
controls. This is a source-level correction, not yet proof of the native
crash's cause. Six CAS scope/lifecycle fixture checks pass.

`build/startup-cas-candidate-v10` preserves the second candidate, which was
gated but never deployed. The third candidate, built by
`tools/build_startup_cas_candidate_v10_3.py`, also includes the removal fix
and limits read-only CAS display diagnostics to four focus snapshots.
Those diagnostics are inserted only in the frozen acceptance source and
are absent from the production template. Its guarded deployment helper is
`tools/deploy_startup_cas_candidate_v10_3.ps1`.

Independent CAS coverage, native loaded-game handoff and returning to the
main menu still need live acceptance. Transport success alone is not
complete independent gameplay.
