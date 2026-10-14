> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# Separate startup Socket capability test

This is an isolated diagnostic based on the frozen, verified V9.6 build.
It does not claim main-menu speech or CAS access. No CAS or EngagementLibrary
movie is added. Main build sources and outputs remain unchanged.

## Why this tests a new premise

The earlier URLLoader probe tested HTTP loading through Scaleform's resource
loader. `flash.net.Socket` is a separate TCP API. A missing HTTP/resource
loader does not by itself establish whether the socket implementation exists.
The [Adobe Socket API](https://help.adobe.com/en_US/FlashPlatform/reference/actionscript/3/flash/net/Socket.html)
specifies asynchronous connection/data events, explicit flushing and socket
policies. The [Autodesk communication overview](https://help.autodesk.com/cloudhelp/ENU/Scaleform-Help/scaleform_help/game_communication.html)
documents host communication but does not establish which networking features
EA enabled in this client. Actual support remains the premise under test.

The alternative UISettings route was inspected and rejected for live IPC:
`SettingsMap.SetValue` changes a Flash-side map, and persistence is supplied
later through client callbacks. Rewriting or frequently saving Options.ini
would couple transient navigation to the player's configuration without a
demonstrated reliable return channel.

The prior `startup-probe-v9_4/runtime.log` explicitly records native
`commands.execute(NO_CONTEXT)` failing to find a ZoneSession. This test
does not retry that known-failing path.

## What counts as proof

- The visible blue badge proves the existing Gamedata TooltipManager has a
  stage and receives frames. It reports class lookup, construction, connect
  errors and protocol progress separately.
- Flash dynamically looks up `flash.net.Socket`, connects only to
  `127.0.0.1:45992`, and sends a fixed diagnostic greeting.
- Python returns a newly generated random challenge. Flash returns that
  challenge, and Python acknowledges the match. Only that verified second
  message turns the badge green.
- The log independently records whether a core tick has a zone/client.
  A round trip in a loaded household does not prove startup delivery.

The Python worker accepts only the fixed greeting, a socket policy request
or the exact random challenge response. It evaluates no input, accepts no
game command or path, limits input to 256 bytes and bounds stalled clients.
The listener stops on proof or after ten minutes; Flash makes at most twelve
attempts, ten seconds apart. No game data is accessed from the worker.

## Build and guarded test

`py -3.7 tools/build_startup_socket_probe_v10.py` builds in
`build/startup-socket-probe-v10`. The source and package baseline must match
the V9.6 verification hashes. Its package has the same 24 resources and
differs only in ClassLibraryGamedata. The verified diagnostic preserves all
1,077 classes and all non-code tags. It passes the integer-opcode fidelity
gate and verifies that every non-target class remains unchanged.

Six real loopback tests pass via
`py -3.7 tools/test_startup_socket_probe_v10.py`: fragmented TCP data,
incorrect challenge, policy request, unexpected input, input size limit
and listener expiration. These tests verify the Python protocol, not the
game's Scaleform implementation.

With the game closed and V9.6 installed:

1. Run `tools/deploy_startup_socket_probe_v10.ps1`.
2. Start the game and stay at the main menu for at least 30 seconds.
3. Inspect the badge and
   `Mods/tyjokr_ScreenReader/startup-socket-probe-v10.log`.
4. Quit without saving; run the helper with `-Restore`.

The helper backs up the original UI, validates copies by hash, checks the
game is closed, and preserves configuration. It refuses to restore over an
unrelated newer UI build. The normal ts4script and compatibility UI package
are not replaced by this diagnostic.

## Runtime result

**Passed on September 15, 2026 at 23:03:03, before loading any save.** The
random-challenge round trip turned the badge green on the loading screen
and remained green on the actual main menu. The independent core tick later
recorded `zone=False, client=False`. Evidence is
`build/startup-socket-probe-v10/live-startup-success.log` and the main-menu
screen captured by the root task. The temporary probe was then removed and
the verified V9.6 UI restored before installing the product acceptance build.

This establishes a working startup transport. It supersedes earlier notes
that treated the zone-gated command/distributor bridge as the only route.
Production narration, navigation and CAS coverage are separate acceptance
checks; see `STARTUP-BRIDGE-V10.md`.
