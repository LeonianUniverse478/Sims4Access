> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# V11 startup candidate: re-base for game patch 1.128.90.1030 (2026-09-22)

Read this before resuming the V11 live testing (the Live-mode Tab/arrow regression
noted at the end of the 2026-09-16 session in HANDOFF-SCANNER-INTEGRATION.md).

## What changed and why

EA's September patch replaced `Data\Client\UI.package` wholesale. Every movie is
re-baked each patch, and SimHub in particular changed (EA's expanded-buff-panel fix).
The V11 candidate you were testing (`build/startup-v11-candidate/`, 2026-09-16 01:40)
was built on 1.127.41 originals, so it was shipping last patch's UI as an override.
It has been rebuilt on the 1.128.90 originals with NO source changes: same V9.6 base
sources, same V11 template, same 16 Python modules.

## What is installed where

| location | contents | state |
|---|---|---|
| OneDrive `<private-folder>` | `build/startup-v11-candidate-1.128.90/` pair + your 09-05 cfg (untouched) | **the working copy, re-based, NOT live-tested** |
| same folder, `before-1.128.90-rebase/` | the 09-16 candidate pair + sha256.txt | rollback of the working copy (1.127.41 movies) |
| `Mods/tyjokr_ScreenReader/` | the SHIPPED line's 09-22 release (V9.6-era shipped code, no V11) | installed 2026-09-22; compat package placement still undecided (see the patch review) |
| CurseForge | 08-28 build, 1.127.41 movies | not yet updated with the 09-22 pair |

## Artifacts (all under ScreenNarrator-integration/)

- `flash/work-1.128.90/` : 24 EA originals (`gfx/ea_*.swf`, SOURCE.txt), patched
  outputs, gate pcode exports. Keep it; it is the diff base for the next patch.
  `flash/work-1.127.41/` is kept for the same reason.
- `build/v9_6-source-1.128.90/` : the exact V9.6 Flash sources reassembled
  (template + CommodityContainer + DialogMain from `build/source-before-v10/flash/`,
  the other 14 extra classes from the tree, all 17 hash-verified against
  `build/v9_6-verified-artifacts/v9_6-verification.json`).
- `flash/rebuild_all_v96_source.ps1` : `rebuild_all.ps1` with `$template`/`$extra`
  pointed at that staging dir. The tree's own template is V11, so the plain script
  would have produced a unified V11 build, not a V9.6 base.
- `build/v9_6-rebase-1.128.90/tyjokr_ScreenReader_UI.package` : V9.6 sources on
  1.128.90 originals. 24 resources, 18,708,612 B. Gate: 61 targeted comparisons
  PASSED (`flash/rebase-v96-1.128.90.log`). No compat package was rebuilt for it
  (the working copy never carried one).
- `tools/build_startup_v11_candidate_rebase.py <version>` : runs the unchanged
  `build_startup_v11_candidate.py` recipe with BASE = the rebased dir and
  OUT = `build/startup-v11-candidate-<version>/`.
- `build/startup-v11-candidate-1.128.90/` : the result. UI package 18,715,034 B
  (sha256 108cd1d2...), ts4script 225,613 B (sha256 d0163de4...), `verification.json`
  with full hashes, `compile.log`, pcode exports. Gate PASSED (2 comparisons,
  Gamedata). Differs from the rebased base in exactly one resource,
  ClassLibraryGamedata (0x12272E1AC0C1F8E2). `A11yStartupDrainKeys` present.
  Log: `flash/candidate-v11-rebase-1.128.90.log`.

## Verification facts worth knowing before testing

- EA changed NONE of the classes we inject. Bytecode of all 60 targeted classes in the
  23 shipped movies (checked in the release tree) and `AgeUpPanelMain` (checked here)
  is identical between 1.127.41 and 1.128.90 after normalising class/function index
  renumbering and namespace ids. So no template or extra-class re-basing was needed
  and none was done.
- The ts4script's 16 pyc members are byte-identical to the 09-16 candidate's; only the
  zip's own timestamps differ. Any Python behaviour you see is unchanged.
- The 23 shipped-line movies and their gate counts match the 08-28 numbers exactly
  except SimHub (746 -> 755 classes, EA's change).
- None of the 37 EA Python modules that changed this patch is imported by either
  Screen Reader build (checked by IMPORT_NAME scan of both ts4scripts).

## Things that are NOT done / traps

- `tools/deploy_startup_v11_candidate.ps1` (and its `-Restore`) is hard-wired to
  `build/startup-v11-candidate/` and `build/v9_6-verified-artifacts/`, both 1.127.41
  builds. Do not use it for the re-based files. Deploy by copying from
  `build/startup-v11-candidate-1.128.90/` and hash-check against its verification.json.
  Rollback of the working copy = `before-1.128.90-rebase/` on OneDrive.
- `flash/chain.ps1` still has `$work = work-1.127.41`. Update it before any full chain
  run in this tree (FLASH-PIPELINE.md section 5.6 step 1).
- `build/v9_6-rebase-1.128.90` is a re-based build, not an in-game-verified V9.6. If
  you need a "known good" stable line on 1.128.90, the shipped 09-22 release in
  `ScreenNarrator/` is the one that went through the full shipped-line pipeline.
- UI Cheats v1.59.1 is installed in Mods. Its six overridden movies are still its
  1.127.41-era builds until UI Cheats updates; the compat package (any version) is
  built on those bases.
- The Tab regression hypotheses from 09-16 stand unchanged; re-basing removes the
  "stale UI" variable, nothing else. Reproduce with logging on and `a11y.inspect`
  after each Tab, comparing against V9.6 in the same lot (hypothesis 4).

## How to redo this next patch

1. `python flash/extract_ea_movies.py flash/work-<version>` (+ SOURCE.txt).
2. Drift check of injected classes vs the previous work dir's `pcode/ea_*` exports
   (release-tree scratch `ea_drift.py` recipe: gate's `opcodes()` plus pcode text with
   `ofs`, `PrivateNamespace(null,"N")`, `newclass N`, `newfunction N` normalised).
   Only re-base template/extra classes if that shows real code changes.
3. Point `flash/rebuild_all_v96_source.ps1` at the V9.6 staging dir (unchanged),
   run it on the new work dir, `gate_pcode.py`, `build_ui_package.py` to
   `build/v9_6-rebase-<version>/`.
4. `py -3.7 tools/build_startup_v11_candidate_rebase.py <version>`.
5. Copy the pair to OneDrive after backing up what is there; hash-check.
