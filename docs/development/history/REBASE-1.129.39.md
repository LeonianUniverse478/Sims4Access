# Rebase onto game 1.129.39.1030 (2026-11-12)

Done by LeonianUniverse (lead developer) with Claude, following GFX-SAFETY.md section 8.

## What was done

1. Extracted the 25 shipped EA movies from the patched UI.package into `flash/work-1.129.39/` (`py -3.7 flash/extract_ea_movies.py flash/work-1.129.39`). All 25 changed bytes, as on every patch. `flash/work-1.128.90/` is kept as the diff base.
2. Drift check, `py -3.7 tools/rebase/ea_drift.py flash/work-1.128.90 flash/work-1.129.39`: every targeted class (TooltipManager, CatalogImageCellView and all extra classes) is identical after normalising FFDec numbering. No template or extra-class port was needed. No class was added or removed in any movie.
3. Classes EA did change, none of which we patch: GameContent, GameplayOptionsData, localization Keys, HouseholdUtils (all movies), CareerOutfit, EventManager, TooltipObject, ObjectBoundElementManager, DialogRequest, PageManagerBase, NeighborhoodMap. The shared ones only moved property initialisers.
4. Definer check, `py -3.7 tools/rebase/definer_check.py`: every patched class other than the shared TooltipManager and CatalogImageCellView is defined only in movies we ship (TimeControlsMain in SimHub and TimeControls, CommodityContainer in SimInfoMotivePanel and SimInfoTray, the rest single).
5. Pointed the tooling at the new work dir (chain.ps1, devkit.py, make_source_kit.py, setup_game_inputs.py, export_public_source.py) and updated reference/toolchain.json: game version, UI.package hash, the 25 movie hashes.
6. Full build devkit-20261112_192107: 1467 checks passed, fidelity gate PASSED (62 targeted comparisons), compat gate PASSED (19). The rebuilt UI packages replaced reference/ui, so scripts-only builds reuse the rebased UI. Staged as dist/2026-11-12_194233 and installed; previous files backed up to Documents\TS4_Access_backups\2026-11-12_before-rebase-1.129.

## Not done

- Live test on the patched game.
- UI Cheats compat bases are still UI Cheats 1.59.1's movies. Rebuild them if UI Cheats updates for this patch.
- EA's Python changes this patch were not diffed; the Python modules are unchanged and are covered by the live test.
