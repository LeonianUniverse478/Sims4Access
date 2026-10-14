> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# Build and new-game accessibility work, September 26

Current status: release 0050 supersedes 0009 and is installed and verified.

User requested Build controls ON by default. v14w6 changes DEFAULTS to True
and removes the explicit False fallback at the build gate, shortcut help and
settings readout. Fresh/missing settings now consistently enable Build controls;
explicit saved off preferences remain respected. All 1007 checks / 60 suites
passed. UI and placement implementation are unchanged from live-tested v14w5.
No additional game/CAS run was needed for this default-only change.

Current release: dist/2026-09-26_0050/tyjokr_ScreenReader_2026-09-26.zip
SHA256 0fe7d030afd3284fe22694fa0d242d9ec03cca2f69393adc7f6ae9cc5d47bb44.
Installed script: 0f39522ee361167a2d2cb2f4ee7c7865dd5ef3d0ce95351ce70f2dce01db05d6.
All five installed members verified; exact script archive parity passed.
Deployment report: build/v14w6-before-release-install/deployment.json.
User cfg now has Build controls ON, with every other original byte preserved:
ba15777c27ad631d28042c508975d938e83bd23ffde6775810fc31ce7ab293ee.
Do not restore the older off setting: the user explicitly superseded it.
Claude identified the fallback issue independently; final v14w6 artifact review
was requested and has not yet returned. Below is the earlier acceptance record.

The user authorized completing Build placement and Seasons/move-in, talking
with Claude through the mailbox, and controlling the game. The earlier
handoff's pause instruction was superseded by the user's explicit resume.

## Source reuse

The earlier September 3 a11yscan review found registration and placement
problems. Glaroc's September 7 version fixed these and added native placement
and surface slots. We should have revisited it sooner. This work ports that
newer approach, adds native catalog selection, game footprint checks, exact
charges/refunds, rotation, undo, confirmed sale, and occupied-object guards.

This is catalog object placement. Walls, floors, rooms, roofs, stairs, pools,
terrain, paint, and wall/ceiling/fence/water/bare-ground-only objects remain
outside the keyboard placement feature. Player guides state these limits.

## Evidence already passed

- Native catalog bed placement, exact charge, rotation, undo/refund, replacement.
- Sim used the placed bed; save/reload retained it and exact 22062 funds.
- Desk placement and computer placement into its slot; filled-slot refusal.
- Sale chooses slotted computer first (640 refund), then empty desk (1000).
- Build entry retires Live grid; F1 retires Build grid; off-lot origin uses lot.
- Four Seasons choices only, native name/description, correct bounded highlight,
  keyboard wrap, preview and Enter confirmation; Winter move-in actually winter.
- Map forward traversal reaches lots without decorative neighborhood loops.
- Occupied/non-residential/unaffordable refusals; accurate house highlight.
- Furnished/unfurnished quote updates remaining funds; cancellation preserves
  funds; confirmed unfurnished move-in enters Live with correct balance.
- Empty-lot quote reads 14500 remaining and cancellation preserves 20000.

Detailed evidence: build/season-reference/validation-plan.md.

## Accepted candidate and installed release

UI: build/v14w-map-ui-candidate, main SHA256
8ebf0c7bd45d6e6e2ffc937c4620aaa843d9895ac4c0c571e16836c8190834d9.
Compatibility SHA256
0f21e08d62678f4a01cf04fe97dd586f5f9ecc09cca4699af63af170c2e063fb.

Script: build/v14w5-script-candidate, SHA256
 a004c88b7c311d36f5c24e7279df518270bc5fc1e156a3135b25db3aad203ed8.
1007 checks / 60 suites; independently audited. This logging-enabled candidate
passed live acceptance, then was replaced by the exact release archive below.

v14w4 trace proved two fast B misses in ten: modifier/key samples straddled
Alt-down because ctypes calls released the GIL. v14w5 uses a poller-only
PyDLL reader for a much shorter sample. It preserves first-read semantics
and near-release plain keys. Live acceptance passed: 10/10 fast shortcuts,
2/2 slow shortcuts, exactly one fire per press and no errors. Two placement
Enters within the guard window placed one bed, charged exactly 240, and spoke
"Already placed here" on the second press. Input can still lag under game load.
An older possible Build catalog focus loop was not freshly reproduced or
certified fixed; do not describe it as resolved.

Accepted and installed: dist/2026-09-26_0009. Main zip SHA256
d32899d756e20e2a75546c9c70496cd96a36e4af6b8da1c7945a65197db5f266.
Release script SHA256
814397e00c4c3c9732e405598072a69d1dc5f32e1d3760d58eb8803dc6e2d6f2.
Only release semantic change is logging default off, recursively verified.
The five installed files match the release manifest. stage_release.py
--verify-installed also confirms the installed script is byte-identical.
No public upload was performed.

Installed all five main archive files with tools/deploy_staged_release.py,
after confirming the game process and window had closed. Backup and report:
build/v14w5-before-release-install/deployment.json. The last test session was
closed without saving its extra bed. Original settings restored byte-for-byte
using tools/launch_test_settings_v14v.py restore. Verified original SHA256
b043e334b0d2aec43bb309fc4a55141a6bbf7a498e74ec3138d48c94756ae74a.
The temporary cfg is gone. Build controls and logging are off again, matching
the user's original settings. Enable Build controls through Ctrl+Alt+H to use
placement. Saved launch test households remain available for regression work.
No settings file is shipped in the release zip. Speech pack remains separate.

Claude owns Python and its tests. Codex owns Flash, guides, staging/deployment,
and visual checks. Only one party controls game inputs at a time; coordinate
explicit handoffs through mailbox/send.py. No source edits during freeze.

User's latest constraint: any further Build testing must use an existing save;
do not do another full CAS run. Save 0f is ready for Build regression tests.

Review attribution: Claude audited the frozen source/release and performed
the final live shortcut/repeat-guard tests. Codex performed deployment and
independently rehashed all five installed files against the manifest, plus
the original cfg, after installation. Claude's requested additional installed
rehash has not yet returned; do not misstate it as already performed.
