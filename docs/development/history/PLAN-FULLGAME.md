> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# PLAN: Full-game screen reader coverage (main menu, Manage Worlds, CAS)

**2026-09-15 update:** see [STARTUP-PROBE-V7.md](STARTUP-PROBE-V7.md) for the
current isolated investigation. Older absolute claims below about startup
transport are hypotheses, not independent delivery tests. V7 does not yet
provide main-menu speech or CAS access. Protected-code detours and runtime
dumps are not authorized; no such work was performed. CAS movies remain
excluded from the test build.

Started 2026-08-20 per user direction ("time to do some engine hooks").
RESEARCH-ONLY until pieces are built; read TODO-NEXT-SESSION.md for
what is actually shipped.

## Why players are asking

Positive feedback from blind players; the mod covers live mode + build
mode well, but the game is not playable end to end without sighted help:
you cannot start the game, pick a world, or make a Sim.

## The three surfaces and what actually blocks each

### 1. Main menu (GameEntry*)
- Flash side: ALREADY COVERED. GameEntryLauncher/Library/Dock are in the
  23-movie patch set and our TooltipManager wins the app domain there
  (boot-time a11y.mark attempts prove our code RUNS at the menu).
- Python side: alive at the menu since EA front-loaded Python init
  (2026-07 "slow boot" change); keys polling starts pre-zone; SAPI child
  is a plain subprocess, no game dependency.
- THE blocker: both message directions are zone-gated. PostServerCommand
  posts die (no Live-command dispatch without a client-server session)
  and Python->UI messaging is equally dead. Everything else is in place.
- KEY HYPOTHESIS for the engine hook: the NATIVE UI transport is alive
  at the menu (menu buttons work, and they travel Flash -> native
  client). Only the Python-level plumbing is gated. So the hook is:
  (a) find the native sink that receives ExternalInterface/UI commands
  from Scaleform and detour it in-process (ctypes, signature-located,
  same infra as tyjokr_EngineModding tep.probe, NO dll injection);
  (b) find the native injector the zone-era Python->UI path uses and
  call it directly. If the hypothesis holds we invent no protocol at
  all, we just bypass the gate.

### 2. Manage Worlds
- Never actually tested with logging on. The cheat console DOES work in
  Manage Worlds, so PostServerCommand is probably ALIVE there, and the
  TooltipManager app domain may well persist across the transition.
- If the capture confirms the channel, Manage Worlds is pure COVERAGE
  work (per-movie hooks like PickersPurchaseMain), no engine work.
  Movies: GameEntryWorldSelection + GameEntryNhd* (world views) + the
  save/lot panels (identify from capture + ui-movie-names.tsv).

### 3. CAS
- From a loaded lot: console works in CAS, so the channel is alive. The
  blockers were (a) CAS renders on its OWN stage, the live
  TooltipManager mouse listener never sees it; (b) the chosen hook class
  CASCustomizerMain lives in CASCustomizer, and ANY FFDec-rebuilt
  CASCustomizer hard-crashes the client (proved twice 2026-08-03).
- NEW ANGLE (2026-08-20 re-read): CASLibrary and CASStories REBUILD
  FINE. The 08-03 CASLibrary build ran in-game; it was silent only
  because patching TooltipManager there is useless (app-domain loser).
  So: scan the rebuildable CAS movies for classes defined in EXACTLY ONE
  movie that get instantiated on the CAS stage, and hook one of those
  instead of CASCustomizerMain. The old work fixated on the one movie
  that happens to break the toolchain.
- Fallback toolchain avenue stays: rebuild CASCustomizer with Sims 4
  Studio (or another FFDec version) and byte-diff to find what our
  FFDec corrupts sub-tag.
- CAS-from-main-menu needs BOTH the CAS hook and the menu channel; ship
  CAS-from-lot first.

## Phases

- Phase 0 (recon capture, one game session, user drives): from a lot,
  `a11y.log on` + `a11y.rawdiag on`, then (1) Manage Worlds: hover
  worlds/lots/buttons, try numpad nav; (2) back in a lot, enter CAS via
  a dresser and hover panels; (3) quit to main menu and hover there too.
  One log scopes all three surfaces.
- Phase 1 (engine): re-import the CURRENT TS4_x64.exe into Ghidra (the
  ts4 project is from 6/16, two patches stale; EngineModding RVAs
  orphaned since 1.126.58 anyway). Locate the Scaleform ExternalInterface
  sink + the client->UI injector. Deliverable: proof at the MAIN MENU
  that Python receives a post from our GameEntry TooltipManager copy.
- Phase 2: productize the channel (auto-fallback: Live-command path
  in-zone, native path at menu), then menu coverage classes.
- Phase 3: CAS-from-lot via a rebuildable-movie hook class (scan first).
- Phase 4: Manage Worlds coverage per Phase-0 findings.
- Phase 5: CAS-from-menu = Phase 1 + Phase 3 combined; then the
  full blind playthrough test: menu -> new game -> CAS -> world -> lot.

## Standing constraints that apply here

- Never a compile-time reference to a class the movie does not contain
  (AVM verify-time native crash).
- Gate every rebuilt movie with gate_pcode.py; never ++ a static.
- EngagementLibrary (v17) must NEVER be FFDec-rebuilt (Gallery freeze,
  2026-07-28).
- Signature-scan for native functions, never bare RVAs; re-archive
  binaries each patch (reanchor_offsets.py workflow).
- Engine detours install from in-process ctypes at Python init; must be
  no-ops when signatures fail to resolve (EA patch resilience).

## PHASE 1 SESSION LOG (2026-08-20, Ghidra re-import)

### Housekeeping done
- Old `C:\Tools\ghidra_proj\ts4` project holds `TS4_x64_fpb.exe` +
  `Simulation_x64_fpb.dll`: the fpb variants patch 1.126.58 DELETED, and
  analyzed 2026-06-16. Doubly stale, left intact for reference only.
- Current binaries archived (rule: re-archive every version) at
  `TS4 Modding/engine-patch-research/binaries-1.126.78.1020/` with
  SHA256.txt. Game 1.126.78.1020.
  TS4_x64.exe   23dd831f2154d0b7...  45,148,016 bytes
  Simulation_x64.dll 6d16d9023c795be6... 17,415,536 bytes
- New Ghidra project `ts4_1_126_78` (same project dir), both binaries,
  sequential headless analysis, 16G heap / 20 CPUs. Launcher kept at
  `C:\Tools\ghidra_proj\analyze_1_126_78.bat`, logs headless_exe.log /
  headless_dll.log. NOTE the stock analyzeHeadless default heap is 2G,
  which would OOM on a 45MB image: always set GHIDRA_HEADLESS_MAXMEM.

### FINDING 1: the bridge lives in the EXE, not the simulation DLL
String counts (whole-file grep):
  TS4_x64.exe        Scaleform 7, GFx 20, ExternalInterface 6,
                     PostServerCommand 1, fscommand 1
  Simulation_x64.dll ALL ZERO
Every prior EngineModding hook targeted Simulation_x64.dll. This work
targets the EXE instead, so `_get_module_base` needs the main-module
handle, not the `_ENGINE_DLLS` tuple.

### FINDING 2: hard string anchor for the hook
`PostServerCommand` at file offset 33232704 (0x1FB8A40), inside the UI
callback-name table. Its immediate neighbors ARE the bridge registry:
  ... ShowGameEntryRentalPanel, ShowBusinessEmployeeManagement,
  GameplayPerkListUpdate, MultiPickerContentUpdate, ShowFamilyTree,
  >>> PostServerCommand, PostSocialServerOp, PostExchangeServerOp,
  AddNetworkMessageRoute, MessageID, commandArgs,
  commandArgsTypeOverrides, msgIdName, msgTypeName
Reading: Show*/Update* = inbound (native -> Flash) messages; Post*Op =
outbound (Flash -> native) callbacks; commandArgs/msgIdName = the named
parameters of the registration. FIRST GHIDRA ACTION when analysis
finishes: xref that string, which lands on the registration/dispatch
site, and from there recover the handler signature.

### FINDING 3: the menu transport is ALIVE (this is the good news)
The callback table region also holds `RequestLoadingScreenImages`,
`GetOfflineLoadingScreenImages`, `RequestNavigationButtonMessages`,
`GetPromoBundleData`, `RequestIncentiveAffordanceMessages`,
`RequestCGVotingMessages`, `TS4_MainMenu`, CGChallenge/Carousel/Survey
data keys. Those are main-menu features that demonstrably work with no
zone loaded, and they travel the same Flash -> native direction we need.
So Flash -> native is NOT gated at the menu. What is gated is only the
tail of the PostServerCommand path, where the command is routed to the
simulation server that does not exist yet at the menu.
=> We do not need to invent a transport. We need to intercept
   PostServerCommand BEFORE its server-routing step.

### Working design for the hook (validate against Ghidra, do not build yet)
1. Signature-locate the native PostServerCommand handler in TS4_x64.exe
   (position-independent signature, never a bare RVA).
2. Inline detour (re_tools/asm_hook_compose.py, keystone) that copies the
   command string into a ring buffer whose address our Python allocated,
   then jumps to the original code so EA behavior is untouched in-zone.
3. Python drains the ring buffer from the EXISTING key-polling thread
   (already runs pre-zone, proven by "keys: polling started" landing
   ~2 minutes before zone load in every session log). No foreign-thread
   Python calls, no GIL games.
4. Hard requirement: if the signature does not resolve, install nothing
   and log. An EA patch must degrade to "menu narration stops", never to
   a crash.
5. Inbound direction (Python -> Flash) is NOT needed for hover narration
   and is deferred; it only matters for driving focus at the menu.

Toolkit confirmed present and proven: live signature scan + .text walk
(`tyjokr_engine_modding.py`), copy-on-write code write via VirtualProtect
(`tyjokr_engine_patch.py`, disk image never touched), keystone 0.9.2 +
capstone for detour composition, plus prior inline-hook precedent in
re_tools (asm_hook_compose.py composes multi-instruction trampolines).

### FINDING 4 (THE WALL): TS4_x64.exe IS DENUVO-PROTECTED
Measured on the shipped 1.126.78.1020 binary:

  section   entropy   verdict
  .text     8.000     ENCRYPTED (theoretical maximum)
  .data     8.000     ENCRYPTED
  .rdata    4.782     plain (this is why the strings were readable)
  .pdata    6.944     plain

  distinct RIP-relative LEA targets found in .text:
    TS4_x64.exe          27      <- noise, 31MB of random bytes
    Simulation_x64.dll   16,330  <- normal, healthy code

Markers: "Denuvo" x2, `Core/Activation64.dll`, and a `.ooa` section
(2048 bytes, Denuvo content-id list) as the last section.

CONSEQUENCES
1. The Ghidra analysis of TS4_x64.exe is WORTHLESS. It analyzed
   encrypted bytes: that is why every bridge string had ZERO xrefs, why
   no 8-byte pointer and no 4-byte RVA to them exists, why no LEA
   reaches them, and why the decompiler threw "unable to resolve
   constructor" everywhere and eventually wedged. Do not re-run it and
   do not trust anything it produced for the EXE.
2. Static RE of the Flash<->native bridge is IMPOSSIBLE from the shipped
   file. The bridge lives in the EXE (FINDING 1) and the EXE's code only
   exists decrypted in RAM.
3. Every prior EngineModding/OA success targeted Simulation_x64.dll,
   which is NOT protected. That is not luck, it is the reason they
   worked. Nobody had tried the EXE before.
4. SIDE BENEFIT: the Simulation_x64.dll in this new project IS a clean,
   current (1.126.78.1020) analysis. That is exactly the input needed to
   re-anchor the EngineModding / OA-CL RVAs orphaned since the fpb
   binaries were deleted in 1.126.58. Unrelated to the screen reader,
   but worth knowing it is now sitting there ready.

### REVISED OPTIONS (supersedes the "Working design" above)
The hook design in the previous section assumed a statically locatable
handler. It is not viable as written. Ranked alternatives:

A. RE-TEST THE PREMISE FIRST (cheapest, could delete this whole track).
   The "main menu channel is dead" belief traces to ONE observation on
   2026-07-28: a CONSTRUCTOR-time PostServerCommand never arrived, with
   the note "ExternalInterface not ready that early". That is not the
   same claim as "a hover-time post at the menu is dropped", which as
   far as the docs show has never actually been tested. Meanwhile
   FINDING 3 says EA's own menu callbacks travel this exact direction
   and work. A 60-second in-game check settles it: post one a11y.mark
   on first mouse-move at the menu, look for it in the log. If it
   arrives, the menu needs NO engine work at all, only coverage classes.

B. FLASH-ONLY WORK FOR CAS + MANAGE WORLDS (delivers 2 of the 3 asks
   with zero engine risk). Both surfaces are in-session, where the
   channel demonstrably works (the cheat console functions in both).
   CAS needs the rebuildable-movie hook class from Phase 3; Manage
   Worlds is likely plain coverage. This is the proven workflow this mod
   already uses 23 times over.

C. RUNTIME DUMP, READ-ONLY (fallback for the menu). Our mod is already
   in-process and already reads its own memory, so it can dump the
   DECRYPTED .text of TS4_x64.exe to disk for offline Ghidra work. Doing
   this is safe; it is only reading.

D. PATCHING DENUVO-PROTECTED MEMORY (last resort, NOT recommended).
   Even with a good dump, installing a detour inside Denuvo-protected
   code risks integrity checks and hostile anti-debug behavior, and
   parts of the code may be virtualized rather than plain x86. This mod
   ships to blind players who need it to be boringly reliable, so this
   should not happen unless A and C prove there is no other route, and
   only with the user's explicit sign-off.

RECOMMENDATION: do A (one tiny test) and B (real feature work) in
parallel; hold C for when the menu genuinely needs it; treat D as a
decision the user makes with the risks in front of them.

## DECISIONS 2026-08-20 (user)
- **Denuvo is OFF THE TABLE.** Option D (patching protected client
  memory) is not merely deprioritized, it is refused. Do not revisit,
  do not "just try" a detour in TS4_x64.exe. Option C (READ-ONLY runtime
  dump) is not automatically approved either; ask before doing it.
- Approved: option A (re-test the menu premise) and option B (Flash-only
  work for CAS + Manage Worlds).
- **Hard constraint: experimental work must NOT contaminate the release
  candidate.**

## RC ISOLATION PROTOCOL (obey this for all full-game work)
The 2026-08-20 release candidate is tester-confirmed ("works perfectly")
and its zips are cut. Contamination discipline, since this workspace is
NOT a git repo:

1. FROZEN SNAPSHOT: `_rc-frozen-2026-08-20/` holds byte copies of every
   RC source file (TooltipManager_patched.as, all extra-classes/*.as,
   all Scripts/*.py, the cfg) plus `MANIFEST.sha256` covering those
   sources AND the four shipped artifacts (both dist zips, the UI
   package, the compat package).
2. VERIFY ANY TIME: `bash tools/rc_verify.sh` reports CHANGED/MISSING vs
   the frozen RC. Run it before any release action and after any
   experimental round. Source files changing is expected mid-experiment;
   **dist/*.zip and the .package artifacts changing is not, ever,
   without a deliberate fresh release cut.**
3. BUILD EXPERIMENTS TO A SEPARATE PATH: `build_ui_package.py` takes an
   optional 2nd arg for the output file. Experimental builds go to
   e.g. `tyjokr_ScreenReader_UI.EXPERIMENT.package`; the shipping
   `tyjokr_ScreenReader_UI.package` is never overwritten by probe work.
4. RESTORING: copy files back from `_rc-frozen-2026-08-20/` and re-run
   rc_verify.sh until it prints RC INTACT.
5. The deployed copy in Mods was hash-verified 2026-08-20 as byte-equal
   to the RC package, so a probe deploy must be swapped back before any
   release verification.

## PREMISE TEST (option A) - COSTS NOTHING, NO BUILD NEEDED
The currently deployed RC ALREADY contains the instrument. In
`A11yAnnounceDisplay`, the `a11y.mark` post is RE-ARMED until a payload
has actually been delivered (`mA11ySentAny`, the 2026-08-03 burned-flag
fix), and it fires immediately before the real payload post. So any
successful announce at the main menu produces BOTH a MARK line naming
the winning movie AND the payload itself.
Python-side logging is provably alive pre-zone ("keys: polling started"
is the first line of every session log, ~2 minutes before zone load).

Procedure (user, ~60 seconds):
  1. cfg `logging = on` (already set 2026-08-20, BOM-free, verified).
  2. Launch. STAY ON THE MAIN MENU. Move the mouse over the menu
     buttons (Play, Load, Options, the pack panels) for ~10 seconds.
  3. Quit, or carry on into a save; either is fine.
  4. Read `Mods\tyjokr_ScreenReader\tyjokr_ScreenReader.log`.

Reading the result:
  - ANY `MARK:` or `SPEAK[` line BEFORE the zone-load lines (ModGuard /
    Better Exceptions / MCCC welcome spam marks zone entry) => the menu
    channel is ALIVE and the whole engine-hook track is unnecessary.
    Menu support becomes ordinary coverage work.
  - Nothing before zone load => AMBIGUOUS, three candidate causes:
    (a) the channel really is gated, (b) our TooltipManager is never
    constructed at the menu, (c) nothing triggered an announce.
    Disambiguating needs an isolated probe build (see below), NOT a
    Denuvo hook.

Isolated probe design IF the free test is silent (build only on request):
  - Patch ONE GameEntry movie only, from a COPY of the RC
    TooltipManager, adding a stage-level MOUSE_MOVE listener that posts
    `a11y.mark menuprobe` unconditionally (no dedupe, no announce
    machinery in the way), capped ~20 posts.
  - Build to `..._UI.EXPERIMENT.package` via the 2nd-arg path, deploy by
    swapping (back up the deployed RC package first), test, swap back.
  - That separates "channel dead" from "listener absent": a mark proves
    the channel, silence with a live listener proves the gate.

## PREMISE TEST RESULT 2026-08-20: SILENT (ambiguous)
Session 15:24 + 15:26 logged ONLY `keys: polling started` twice and
nothing else. Notably absent: `speech backend: sapi`, which is written
on the FIRST speech attempt. So nothing even tried to speak: no `a11y.*`
command reached Python from the menu at all.
Confirms Python is alive pre-zone; does NOT distinguish
(a) channel gated / (b) TooltipManager never constructed at the menu /
(c) nothing triggered an announce. Disambiguation needs the isolated
probe. NOT yet built (awaiting user).

## CAS SCAN RESULT 2026-08-20 (offline, no builds, RC untouched)
Extracted all 258 movies; counted every `CAS*` identifier and kept those
appearing in EXACTLY ONE movie (unique = cannot be app-domain shadowed).
603 distinct CAS identifiers; every CAS movie owns a unique `*Main`:

  movie                 size     unique *Main class
  CASNameField          44 KB    CASNameFieldMain
  CASNavigation         62 KB    CASNavigationMain
  CASAgeGenderPane      67 KB    CASAgeGenderPaneMain
  CASSimSelector        79 KB    CASSimSelectorMain
  CASSimContextMenu     87 KB    CASSimContextMenuMain
  CASFeaturedLooks     106 KB    CASFeaturedLooksMain
  CASMolecule          143 KB    CASMoleculeMain
  CASGeneticsPane      143 KB    CASGeneticsPaneMain
  CASPaintingPanel     146 KB    CASPaintingPanelMain
  CASCustomizer        313 KB    CASCustomizerMain   <-- the 08-03 crasher
  CASStories          1509 KB    CASStoriesMain
  CASLibrary          1655 KB    CASLibrary_fla
  (+ CASHouseholdSummary, CASPlanOutfit, CASFashionShoppingCart,
     CASPetPaintingPoses, CASFashionNameGender: all tiny, all unique)

**So there are 13+ alternatives to CASCustomizerMain.** The 08-03 work
fixated on the single movie that breaks the toolchain.

SIZE INSIGHT: the CAS panels are 44-146 KB, i.e. they do NOT embed the
shared framework, unlike the 23 patch-set movies (1.5-2 MB each, which
is why those carry TooltipManager). Smaller movie = fewer tags = far
less for an FFDec rebuild to corrupt. CASCustomizer at 313 KB was the
largest realistic candidate and it is the one that crashed.

RECOMMENDED HOOK: **CASNavigationMain** (62 KB movie, persistent CAS
navigation chrome, so it exists the whole time CAS is open).
Architecture: the hook does NOT need TooltipManager at all. Because CAS
renders on its OWN stage (the 08-03 finding that killed the old
approach), ONE capture-phase MOUSE_OVER listener installed on that stage
from any CAS-resident class covers EVERY CAS panel. Self-contained
announcer, ~100 lines of AS3, posting straight to a11y.widget_enc. The
channel is known-good in CAS-from-a-lot (the cheat console works there).

*** ISOLATION BONUS: CAS support touches NO RC movie. ***
None of the 17 CAS movies is in the 23-movie RC package, so the CAS
probe ships as a SEPARATE package (e.g. tyjokr_ScreenReader_CASPROBE.package)
containing ONLY the patched CASNavigation. The RC package stays
byte-identical, the two packages override disjoint resources so they
cannot collide, and rollback is deleting one file. This is the ideal
test vehicle under the no-contamination rule.

RISK PROTOCOL for the first CAS build (FFDec crashed the client twice on
CASCustomizer): post an `a11y.mark cashook-start` at the TOP of the
patched Initialize and `cashook-end` at the BOTTOM. If CAS crashes with
neither mark, the crash precedes our code and that movie is simply not
rebuildable (move to the next candidate). If both marks appear, the
rebuild is sound and any silence is a listener problem, not a toolchain
one. A crash is fully recoverable: delete the probe package.

## CAS PROBE ROUND 1 (2026-08-20): INCONCLUSIVE, ran in the wrong mode
Built patched CASNavigation (hook in CASNavigationMain, gate PASSED:
33/33 classes, zero untargeted drift, +744 instrs), shipped as the
standalone 30 KB tyjokr_ScreenReader_CASPROBE.package. RC verified
INTACT before and after.

Tester entered CAS via **Create a Sim / New Game FROM THE MAIN MENU**,
and the client crashed (lastCrash.txt: native, whole stack in
0x140xxxxxxx = TS4_x64.exe, no Python frames). Log for that session:
`keys: polling started` and nothing else, no zone-load lines.

*** DO NOT READ "no cashook marks" AS "our code never ran" HERE. ***
The marks travel PostServerCommand, which is exactly what does not
arrive with no zone loaded (the same gating the menu premise test hit
earlier the same day). CAS-from-menu has NO zone, so the instrument was
mute regardless of what happened. This differs from the 2026-08-03
CASCustomizer verdict, where CAS was entered FROM A LOT with a live
channel, which is what made mark-absence meaningful there.

Also unproven: that the probe caused the crash at all. No control run of
CAS-from-menu without the probe exists on this install (which carries
WickedWhims, MCCC, ModGuard, Better Exceptions and a long crash history).

NEXT TEST (the only one that can speak): load a save FIRST, enter CAS
from a dresser/mirror, hover panels, exit CAS, quit.
  - marks + speech      -> CAS-from-lot solved, ship that first
  - marks, no speech    -> rebuild is sound, listener/harvest problem
  - crash, no marks     -> CASCustomizer verdict, this movie is
                           toolchain-poison; move to the next of the 13
                           candidates (CASNameField 44 KB is next by size)
  - crash WITH marks    -> our code ran and something later blew up
