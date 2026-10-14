> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# v14s Prism and scanner test build

User priority: replace Tolk with Prism for NVDA testers, and include active-Sim
scanner filtering plus performance cleanup. Build mode work remains paused.

Artifact: `dist/ScreenReader-v14s-Prism-Scanner-test-build.zip`.
ZIP SHA256: `1e7c591923ff9b634ab0d951557abefa6d4507c27e9566d3663f1281d6e3aa09`.
Script SHA256: `8959e595bcec4d9ebaf63efe53e82b5fb14161a5e12c93572847d992adc39a7f`.
UI remains `c252b79f`; Prism DLL is upstream v0.18.2 release x64 `cb9712e1`.

Prism uses a dedicated native worker for COM thread ownership. All C signatures
match the upstream header. No Tolk shim or separate NVDA controller DLL ships.
The bundle includes the complete speech pack, licences, source link, three
player guides and TEST-PRISM.txt. It contains no cfg or personal log.
Existing speech modes, interruption, UTF-8, concise/full/off/only braille, and
configured Windows fallback voice remain supported. Reader detection retries
on speech when no reader was found; a11y.reload also retries immediately.

The supplied glaroc folder was inspected: it actually uses its own NVDA client
first and Tolk second, with explicit diagnostics. It contains no Prism code.
Its self-contained distribution approach is followed; Prism uses the official
0.18.2 C API directly.

Scanner eligibility follows native interaction checks for the active Sim.
Confirmed empty objects disappear; greyed native choices remain unavailable.
Unknown/failed checks stay visible. Sim and zone changes invalidate results.
Idle, menus and text entry pause work without erasing results. Unchanged
results and repeated errors back off to a maximum 60 seconds. Out-of-range
results survive movement, capped at 2000 cached objects. Explicit refresh
(Ctrl+Alt+S) requests fresh checks while retaining the visible list.

Validation:
- 858 checks / 54 isolated suites passed with stable inputs; record and logs
  in build/v14s-prism-scanner. Includes shuffled availability cases, mutations
  reviewed by Claude, scanner integration, native worker ownership and game
  standard-library import availability.
- 43 speech regression checks passed against the final packaged archive.
- Packaged Prism DLL loaded and initialized through the packaged Python 3.7
  wrapper, with no reader present. No NVDA audio claim is made.
- Earlier live filtering: child 144 usable / 193 empty, adult 158 usable /
  3 locked / 176 empty, 337 candidates, zero errors. New performance changes
  need live tester confirmation; individual native tests cannot be preempted
  and previously reached about 58 ms. Diagnostics now identify slow objects.

Known limits: a changed interaction may take up to 60 seconds to refresh
unless rescanned or switched to another Sim; native calls can still hitch.
Native Prism calls currently wait synchronously for their worker; a hung
reader could block the caller. No NVDA installation is available locally.

The v14r speech-only package is superseded. Do not send it to testers.
The older v14o tester ZIP remains frozen for comparison or rollback.

Installed after Claude exact-hash approval 2026-09-25 21:20 UTC. All 22 installed file hashes match the package manifest. Settings stayed byte-identical (090bd247). Installation backups and installed.json are in build/v14s-prism-scanner. No game or screen actions were taken during this hotfix.

## v14t follow-up: Sim action narration default

User requested narration of the active Sim's actions on by default. Only code change: settings.DEFAULTS sim_actions is True. Explicit existing off choices are preserved. README and TEST-PRISM explain a11y.simactions on for existing installs. Candidate build/v14t-sim-narration; dist/ScreenReader-v14t-Prism-Scanner-test-build.zip (d07096630d6ecf073bbe45d7740c9aa9c330b2a17b1807359d7ce87a788db2c3). Script 67fa9f63c48052bb60cceaaf7374ba22635bebc7ae08ccc762643c79fa69b99f. Settings suites passed 39 + 5 checks; packaged fresh default ON and explicit OFF persistence verified. All 23 modules verified against frozen source; only settings differs from v14s. Package matches manifest.
