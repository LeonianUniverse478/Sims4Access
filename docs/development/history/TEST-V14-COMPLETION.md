> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# Completion verification

Current checkpoint: September 25, 2026, 05:31 EDT. This is a concise status
index; TEST-V14.md and COLLAB-CLAUDE-CODEX.md retain the historical evidence.
Offline checks are not in-game passes. Speech logs prove narration requests,
not that a listener heard the audio.

| Area | Verified | Remaining |
|---|---|---|
| Event planner | Full keyboard Keg Party creation, host/guests/venue/time/cost; calendar entry; event descriptions; host checkbox narration | Final combined-build smoke test |
| Career | Astronaut accepted as Module Cleaner, SpaceY, 44/hour; own-row descriptions after scrolling | Final combined-build smoke test |
| Ordinary travel | Destination arrival with companion; family-first residence names and resident details; master and secondary apartment units; master-unit arrival; Back rows; place cancellation cleanup; installed v14f M entry through companion picker, world/lot lists and Pawspital arrival (02:39–02:41) | Final combined-build regression |
| Native map fallback | World-row fallback and arrival with companions; keyboard-off and travel-list-off native map | Combined-build M fallback and settings restoration |
| Vacation | Rental-only list and native price parity; stay cancellation without charge; simplified and native two-day bookings each charge 794 and deliver five Sims to Green Getaway; clean simplified repeat at 03:30; native rental introduction and keyboard controls; v14h changed-total narration at duration and confirmation for two and three days | Final combined-build regression |
| Build | v14h restores ordinary held catalog product through On and Center menus, with native Select trace and held-tool bar | Native cursor persists after F1; picker wheel zooms world; v14i candidate resync being built; real placement, funds change, undo/redo, invalid placement feedback, cleanup |
| Packaging | Frozen-script audit; package/movie hash audit; UTF-8 template issue identified | Final stable checks, frozen pair audits, installed hashes, updated README and release ZIP |

All completed game tests were unsaved. Sims was closed without saving at 02:05.
The mutually reviewed v14f pair was deployed with the game closed at 02:29:
script c7bd2bb66c7f8eaee19e9f5993183a5d3591002558c039fd2b07ca8c9c245680;
UI c79b26f651a4fca92b826a2155f11b3cda2cc5facafd90c6df48a2cd0ee59da3.
Both frozen artifact audits passed, along with 528 checks across 34 isolated
suites. Build menu restoration, M entry, and rental-price bridging still
require further live results, except M entry now passed. User explicitly resumed
live testing after the physical Escape interruption; Sims relaunched at 02:36.
The M arrival image is build/codex-live-20260924/v14f-m-arrival.png.
At 03:02 an unsaved restart was requested to isolate vacation testing from the
Build cursor issue. Bare Backspace moved a bed into inventory during testing;
Ctrl+Z restored it. This was native behavior, not a Ctrl+Alt binding failure.
Funds remained 12409; no chair placement or charge was observed.

The next candidate includes both agents' changes. Codex owns shared Flash and
live testing; Claude owns Python and the UI build chain. Deployment follows
mutual source review and artifact verification with the game closed.

03:12 EDT vacation update: installed v14f rental bridge showed 20 rentable
places across 13 worlds, with non-rentals filtered. Green Getaway matched
native pricing (397/day; 794/two days). Escape from the stay picker returned
to Live without charging (funds 12409). A subsequent two-day booking delivered
five Sims to Green Getaway and reduced funds to 11615. A teardown exception
occurred during loading: EventManagerService disabled while a sentiment
tracker registered AgedUp from relationship_bit_change.end. This is not yet a
clean vacation pass; native-flow comparison and Claude review are underway.
Evidence: build/codex-live-20260924/v14f-vacation-stay-prices.png,
v14f-vacation-arrival-exception.png, v14f-vacation-lastException.txt.
Exited without saving at 03:17 and relaunched for comparison. Build cleanup
source changes passed 22 Flash and 16 Python checks and mutual review; catalog
selection preservation remains a separate proposal, not deployed.

03:24 EDT native vacation comparison: Open the map instead preserved five Sims; Green Getaway 397/day, two days794. Native RentalPanel keyboard duration and confirmation worked; full intro narration requested. Arrival funds11615, no exception alert, lastException.txt absent. Different in-game timing (09:43 versus earlier10:27) means causality unresolved. Changed native total was not announced on focus (only 2 then Okay Create); targeted shared Flash quote fix added with six checks, awaiting peer review and live test. Evidence v14f-native-vacation-quote.png and v14f-native-vacation-arrival.png.

03:31 EDT simplified vacation clean repeat PASS: same original save and party, Green Getaway two days794, group1008550373707285883, dialog9 answered03:30:43, Live03:30:54. Five Sims arrived at09:42; funds11615; no exception alert or lastException.txt. Evidence v14f-simplified-vacation-clean-arrival.png. Earlier assertion remains recorded; source review supports an interaction teardown timing issue, not proven path causality.

03:39 EDT affordability refusal PASS: temporary unsaved funds100, Green Getaway one day397. Keyboard Down/Return requested booking; log refused cost397 exceeds funds100 and narration requests Not enough money / Travel cancelled. Stayed home with funds100, no booking. Funds restored12409 and testingcheats false verified at03:40. Original save remains unchanged.

03:44 EDT solo M travel PASS: deselected preselected Watson/Evie/Elias, selected Brindleton Pawspital, Sebastian arrived with other household portraits grey at home; funds12409. Evidence v14f-solo-m-arrival.png. Follow-up M travel opened native map through Open the map instead, sole Sebastian portrait, and native cancel returned to same lot. Mixed input test. Source candidate v14g now integrates Claude v3 catalog product restoration, pending integration review/build/live; 11 product and22 Build checks passed.

04:10 EDT v14g deployed after mutual source/artifact review and game-closed verification. Script7064e3d81dacec22f4a9072b8bf9f69337ecef6fbd9284c1912db94e2e08d01a; UI723eed6cc7ab85ffbafd2cb7a7917f52480780618daccb6f966d614b4339a5c1. Independent20module/25resourceaudits PASS;550checks35suites stable. cfg79a8a668 unchanged. Backup build/codex-deployed-before-v14g/deployment.json. Added first-use listener registration and modal-balance cleanup after independent integration review. Live verification underway, not yet passed.

### 2026-09-25 04:27 EDT: v14g live Build failures
Owned Isda Riverfront, funds12409. Selected Webbing Colored Patio Chair75 before first cursor activation. Build menu On04:20:24 acknowledged x1472y781 but held product vanished; Center04:22:39 x846y430 confirmed no ghost/Cancel bar. No placement or charge. F1 exit04:23:02 logged Python release serial3, but subsequent phone clicks failed. Explicit a11y.build off04:24:54 acknowledged and still failed. Exit dialog mouse click passed through to floor pie menu, narrowing failure to UI mouse routing. Keyboard HUD/dialog navigation works. Claude notified; investigating separately product event sequence and native SetMouseInputEnabled cleanup. Not release-ready. Evidence: build/codex-live-20260924/v14g-build-fail-session.log.

### 2026-09-25 04:35 EDT: v14g changed rental quote failure
Clean restart restores normal mouse UI. Native vacation fallback Green Getaway397/day: intro narrated; keyboard Return Down Return visibly selects2days794, but SPEAK only2; Tabconfirm onlyOkayCreate. Cancelled without charge. Exact ancestor class check used base RentalPanel while actual movie exports GERentalPanel subclass (EA pcode confirms). Corrected accepted symbol and real-symbol fixture in source, not yet built/deployed. Evidence build/codex-live-20260924/v14g-rental-quote-fail.log.

### 2026-09-25 04:44 EDT: v14h preparation
Claude approved independent SetMouseInputEnabled(true) cleanup and exact GERentalPanel ancestor correction. Added log-only product event tracing, reviewed Python bounded receiver. Full source suite: 554 checks across35 isolated suites, stable. Flash hash38eb2fe6d54e9fb34ca569e9813c7af098f336c1727f5a20f3a0345fa5b4afd3; build.py e38eb5371ca4056fcd8ec789f93baed112c4aa8567c9a6961c4016101b798515. Game exited unsaved04:41; process absence verified04:41:34. v14h artifacts are not yet installed. Next live sequence: native rental duration/confirm quote; first-use product event trace; cursor on/off and F1 followed by phone click; real placement/undo/redo only after held product survives. Existing automated passes do not constitute live passes.

### 2026-09-25 05:17 EDT: v14h live Build partial pass and exit failure
Installed reviewed script39e79201/UI6792d2b4 at05:04 with cfg unchanged. Actual Webbing Colored Patio Chair75 selected05:10:34. Opening console did not drop it; opening Build menu emitted drop in same dispatch as modal and correctly claimed it. On05:11:37 and Center05:15:29 both logged restore Select returned, selected ordinary true, with Cancel/Esc held-tool bar present. Product restoration stage PASS twice; no placement or charge yet. Menu mouse wheel still zooms world. F1 at05:16:50 sent Python cursor release serial3, but clicking phone2761041 at05:17:04 opened world pie at old virtual846430; native cursor cleanup FAIL. Evidence v14h-build-first-trace.log and v14h-build-exit-fail.log. Claude reviewing native cursor resync; no completion claim.

### 2026-09-25 05:29 EDT: v14h native rental quote PASS
Native vacation fallback retained five Sims. Green Getaway397/day: keyboard Return Down Return selected2days, visible total794, SPEAK05:28:05 full Rent for2days x397=794; Tabconfirm05:28:25 repeated794. ShiftTab Return Down Return selected3days, visible1191, SPEAK05:29:07 full1191; Tabconfirm05:29:25 repeated1191. GERentalPanel exact-symbol correction passes changed-duration and confirmation narration requests; no audio-listener claim. Evidence build/codex-live-20260924/v14h-rental-quote-pass.log. No booking submitted in this regression.

05:35 EDT v14i installed with Sims closed after mutual review and independent audits. UI d302876933c2d6aadc57a85db7b8e540a3678a15d9b92822fe67b1ba7a1be977, unchanged script39e792019564cb854e8b64b635e50c2fbb3e0ba4b081b1e3abd3ab6c88139275. 556checks35suites;25UIresource/20moduleaudits PASS. Backup build/codex-deployed-before-v14i, cfg79a8a668 unchanged. Candidate cleanup sends native SetVirtualCursorPosition(-1,-1) after disable, retaining confirmation mapping0 and independent mouse-routing restore. Live result still pending.

05:40 EDT v14i cleanup FAIL in simpler no-product case: Build at community1TamNangSands, menuOn05:39:24 acknowledged837509; F1 release05:39:48 serial2. Physicalphoneclick2761041 at05:40:03 openedAshtonworldpie atoldcursorpoint. Explicit Live a11y.build off05:41:23 acknowledged but subsequentphoneclick stilldidnotopenphone (redworldprohibit). No product or placement involved. Evidence build/codex-live-20260924/v14i-cursor-exit-fail.log. Resync candidate not sufficient; investigating native PC input contract and swallowed errors with Claude.


### 2026-09-25 09:25 EDT: v14j diagnostics prepared with Claude; no deployment or live testing
User authorized joint development and preparation, with desktop/game control prohibited. Codex added enable-after and mode-message snapshots plus six diagnostic fixture checks; native cursor behavior is unchanged. Claude reviewed template 36f3cd5eb7ec93eefac63ef9267eaa53706bc72de79b162919ffae35a97b3f9e and ran v14j-diagnostic chain; fidelity gate and package round trips passed. 562 checks / 35 suites passed with stable input hashes (includes repeated imported checks), including 34 Build fixture checks. Independent 25-resource UI and 20-module script audits passed on both sides.

Mutually approved preparation pair: UI ee1fdc47c3c227a3f37217605386b4ee2ea8d2479fb786717cf75997a8f39ff5 with unchanged installed script 39e792019564cb854e8b64b635e50c2fbb3e0ba4b081b1e3abd3ab6c88139275. Optional rebuilt script 05a109a5 has identical bytecode members, different ZIP dates. Optional compatibility 9edf7697 is outside the next test pair; six packaged resources and executable generated source matched, with comment-only encoding differences recorded. Installed pair/config hashes verified unchanged. Claude preparation approval 20260925-132328; deployment still requires game-closed verification and exact-hash coordination after user continuation.

Evidence and next-session plan: build/v14j-diagnostic-preparation.md and .json; build/v14j-diagnostic-review/ preserves diff, fixture, all suite logs, audits and mailbox approvals. v14i routing failure remains unresolved; no new live pass or release claim. No desktop or game interaction occurred in this preparation.


## 2026-09-25: v14k settings source and script preparation (Codex)

User requested independent options for custom Build behavior and mapless travel,
then rejected the name "build overrides". The setting is "Build controls";
[features] build controls = off by default. Existing travel list = on is retained.
Claude implemented Python gates, menu/reload synchronization, pending-travel
cancellation and generation-bound travel heartbeats. Codex implemented independent
Flash gating, cleanup and callback retirement. Each reviewed the other's source.

601 checks / 37 suites passed with stable inputs. Script candidate is frozen at
build/v14k-controls-script-candidate, SHA256
e03767d4e059133e19cc26aea6af26f1a3b2b41fe60152c1e42f2581d30d49da.
Both agents independently audited its 20 Python 3.7 modules. Claude approved that
exact artifact for preparation in mailbox message 20260925-140057. UI chain
v14k-controls is still pending at this entry. Final pair status will be recorded
in build/v14k-controls-preparation.md after its audit. Review evidence resides in
build/v14k-controls-review. Installed script, UI and user config hashes unchanged.
No installation, desktop control or live testing. Dialog latency findings remain
in build/input-latency-review/REVIEW.md; this settings candidate is not a lag fix.


### 2026-09-25 10:09 EDT: v14k exact pair preparation complete (Codex)

Claude completed/froze the UI chain; Codex independently passed the frozen UI
and preparation audits. All 25 main UI resources match generated source/frozen
movie hashes; six optional compatibility resources match compiled movies, with
known comment-only encoding differences recorded. Checks/log/input hashes match.
Exact pair: script e03767d4e059133e19cc26aea6af26f1a3b2b41fe60152c1e42f2581d30d49da
and UI 2d50ac4d72adbcc9d9c441c618869f567a706ec6f31e44e661a494764d4fa9ed.
Both are required for the new Build controls switch. Build controls defaults off;
travel list defaults on. Both accept on/off in [features], via a11y.reload.
Preparation manifest: build/v14k-controls-preparation.md and .json. Both agents
approve preparation only. Nothing installed; no desktop control or live tests.


## 2026-09-25T12:52:52 v14k installed (Codex)

User authorized installation; no game control or live testing. Claude deploy approval 20260925-165133. Installed and hash-verified frozen script e03767d4 and UI 2d50ac4d. Backups and full hashes: build/codex-deployed-before-v14k/deployment.json. Preserved all prior cfg bytes, adding only Build controls comment and build controls = off after travel list = on. Compat not installed. Game closed at copy time.


## 2026-09-25: v14l input repair, active joint review

After v14k install the user reported scanner selection followed by runaway
navigation with all physical keys released. Codex preserved the log and
reproduced stale Windows high-bit input; Claude independently confirmed and
implemented consumed-release records. Codex caught an additional sample/release
race; Claude added generation snapshots and regressions. Codex added the client
no-owner NavNext/Prev guard, scanner single-pump dispatch and focused fixtures.
Both reviewed the changes. Requested source punctuation cleanup is included.

631 checks / 41 isolated suites PASS. Frozen script candidate SHA256
e64a6627eec50385d18c8049452edb6a044c168557fdddc27a0b4b729d9a07fb,
20 Python3.7 modules, portable filenames, independently audited by both agents.
Claude approved exact script for install in 20260925-171825 mailbox reply.
Sole UI chain v14l-keys running under Claude, approved template
2526ca44217c87dc35424d6ed038a4b07a951241c623aa5399f1bac300926d71.
Current installed v14k/cfg hashes still match baseline. No live testing or
computer control. Install reviewed pair once UI audits and game-closed check
pass; user already authorized installation, so do not add a redundant hold.

Evidence: build/v14l-keys-review; build/scanner-incident-20260925.
Next latency work after this fix: measure queue ages; evaluate bounded stale
repeat handling, then a native navigation design with one input owner. Never
reintroduce the old bidirectional Flash socket transport. Known unrelated modal
focus interference remains a separate issue, not claimed fixed by this build.


### 2026-09-25 13:26 EDT: v14l installed and verified (Codex)

Claude and Codex independently audited exact pair UI7107959e and script e64a6627.
Claude deploy approval: mailbox 20260925-172522. Codex installed with process guard,
backups and post-copy hash checks. Configuration and log byte-identical to prior
state. Backup and exact hashes: build/codex-deployed-before-v14l/deployment.json.
Final notes: build/v14l-keys-preparation.md and .json. All631/41offlinechecks passed;
compiled UI fidelity and both package round trips passed. No live pass claimed.
The user retains game control. Queue-age/direct-native latency work remains a
separate follow-up; no background worker is continuing it automatically.


## 2026-09-25 14:24 EDT: v14m scanner resume update installed (Codex)

The user reported scanner silence after interaction menu Enter/close. New log
shows world:00 after close but cannot establish Python flags. Joint review and
actual-handler reproduction identified that context only logged ownership; a
missing separate modalstate message leaves stale menu routing. Context suffixes
now apply the same idempotent state handler, also clearing stale scanner menu
markers. Valid integer state payloads normalized; diagnostic logs expose state
transitions, menu flags and key routing. No timer-based modal release was added.
README clarifies Ctrl+Alt category/subcategory/item keys and Enter interaction use.

646 checks across43suites PASS; exact script independently audited by both agents.
Claude install approval 20260925-182313. Installed script SHA256
351204a5c4ce9e94f844f7e988abcc27731bc90e7e5c91ddc3e089566aa72cdb.
Retained UI7107959e and cfg8c28b75b byte-identical, allotherexistingfiles unchanged.
Backups/exact hashes: build/codex-deployed-before-v14m/deployment.json.
Evidence: build/v14m-context-review; build/scanner-resume-20260925.
No live test or computer control. This repairs the reproduced handoff failure;
the exact live cause and success on the user's next session remain unconfirmed.

## 2026-09-25 15:39 EDT - v14n installed (Codex)
UI chain DONE 15:34:29; 31 movies rebuilt, fidelity gate passed, two package
round trips passed. Both peers' frozen script/UI audits passed. Final stable
checks: 772/48. Claude explicitly approved the exact pair in mailbox reply
20260925-193844 after a delayed inbox pickup; Codex had already sent the deploy
request at 19:35:28 UTC. This was a mailbox-read delay, not a build failure.

Installed using tools/deploy_reviewed_v14n_pair.py, game-closed checks passed:
- UI c252b79fbff92a500e5e23924f85f79b39c9f597bcf828bf9cf86b1a3c70a1f6
- Script ad4c7aac8c23225cacb1eb85710bdce6e95a142dc536f23ae29a79fd0abb9117
- Preserved cfg 8c28b75bffa216db76be3db5717f9819a083bd99a7b3691c19e334473cc14f2e
Backup: build/codex-deployed-before-v14n/deployment.json. Compatibility not
installed. No live testing or game control. Scanner mode defaults off; toggle
in settings or with Ctrl+Alt+Space. Camera follow repair timing after external
camera movement remains dependent on native camera reports and unverified live.
