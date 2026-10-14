# Escape leaves the Build catalog (2026-09-30)

## Problem (reported by Leo)

CONTROLS.txt step 2 says to choose an object in the Build catalog with Enter, then press Escape to leave the catalog controls before Ctrl+Alt+B. Escape did nothing, so the catalog kept keyboard ownership and the lot grid's Ctrl+Alt arrows and Enter went to the catalog. This is probably the "older possible Build catalog focus loop" that HANDOFF-2026-09-26-build-movein.md left uncertified.

## Cause (from source)

- EA registers the catalog as a modal widget, so A11yModalFrame makes it the navigation owner (modalstate 10). While it owns the keys, keys._chord routes Ctrl+Alt arrows and Enter to it. Only buildtoggle, buildgrid and buildplace bypass the owner.
- A11yModalFrame drops the catalog as owner only while the Build cursor is on or the aim marker exists (`(mA11yBuildCursor || mA11yBuildMarker != null) && !A11yBuildBlocked()`). Grid placement (Ctrl+Alt+B, grid.placement_toggle) sets neither.
- A11yDismiss had no catalog case. Escape fell to the generic loop, which ends in `CallUIService("RequestHide" + WidgetName)` for the catalog. The native guard had already claimed Escape (A11yEscape needs mA11yGuardHeld[27]), so EA's own Escape did not run either. Leo's report matches: nothing happened.

## Fix

- A11yDismiss calls A11yReleaseBuildCatalog after the filter-panel and dropdown cases. When the active modal root is one of the Build catalog widgets (the same list A11yBuildBlocked uses), it releases navigation (scope, focus, index, history cleared, active root null). It remembers the widget in mA11yCatalogReleased and posts `a11y.catalogleft`. There is no EA call, so the catalog and the chosen or held product stay exactly as they were.
- A11yModalFrame treats a still-live released catalog as no owner (top null, modalstate 00), so the grid chords reach the world. A dialog above it owns the keys as usual, and afterwards the catalog stays released. The release is forgotten when the widget closes or the HUD mode changes (Build to Live).
- Tab or Shift+Tab reaching Flash while a catalog is released (A11yReturnToCatalog) only clears the release, so the next frame focuses the catalog again. Without a menu open, keys.py keeps Shift+Tab for first-person view, so Tab is the documented way back.
- Python `a11y.catalogleft` (tyjokr_a11y_place.py) says "Left the Build catalog. <object> chosen. Control Alt B places it. Tab returns to the catalog." (en and pl). The product is unchanged.
- It is loaded-zone only (Build mode), so there is no startup-socket channel.

## Files

flash/TooltipManager_patched.as, Scripts/tyjokr_a11y_place.py, CONTROLS.txt, docs/patreon/04-build-mode-guide.md, tools/test_build_catalog_escape.js (10 checks, running the real A11yModalFrame, A11yIsModalScope, A11yDismiss and Tab handlers), tools/test_build_catalog_escape.py (2 tests).

## Evidence

- `Dev.ps1 build` exit 0, dist `2026-09-30_135735`. `build/v10-checks.json`: passed true, input_stable true, 1,286 checks across 83 suites.
- Main fidelity gate PASSED; compat fidelity gate PASSED (19 targeted comparisons).
- SHA256: TS4_Access.ts4script `d3a7341f5fdd19a1db92c7fb49d010b7904c4439090e197c97814b63a9491fae`, TS4_Access_UI.package `96cbc96e2e9ba593fc3ab71790e7964cb22ce6c060db8acc940d8b6220639803`, compat `3a2db3318d4ff47bd1e7ec22e9f530a479ebfa316c3e145833dcc46f66387fbf`.
- Installed to Leo's Mods root on 2026-09-30 with the game closed; hashes verified; cfg unchanged.

Live testing pending: choose a bed with Enter, press Escape, then Ctrl+Alt+B, Ctrl+Alt arrows and Ctrl+Alt+Enter; press Tab to return and choose another object; check other menus' Escape and the filter panel's Escape are unchanged.

## Follow-up (2026-09-30, Leo's live report on dist 2026-09-30_172831)

Leo: in Build mode, after choosing an object, Escape still did not leave the catalog, and after Ctrl+Alt+B the arrows still read catalog items instead of moving the Build cursor.

Cause from source: the first fix only recognised the catalog when the active modal root was one of five hard-coded widget names. It did not handle (a) the catalog reached by Tab, as HUD browsing with focus inside it and no modal root, or (b) EA registering the catalog modal under another widget name. In (a), the ordinary HUD Escape released browsing, but a catalog that is also the top modal was focused again on the next frame, because nothing marked it released.

Fix:
- A11yIsBuildBuy recognises any Build/Buy widget (class name contains "BuildBuy", or one of the five names).
- A11yBuildCatalogOwner finds the owning Build/Buy widget either as the modal root or as the outermost Build/Buy ancestor of focus while browsing. It only applies in Build mode, and a non-Build/Buy modal root (dialog, picker, pie) always wins.
- A11yReleaseBuildCatalog releases either route. It also ends HUD browsing and records the top modal Build/Buy widget when there is one.
- While released, A11yModalFrame ignores any Build/Buy top modal.
- Tab returns to a modal catalog; for a browsed one it browses the Build panels as usual.
- Ctrl+Alt+B (A11yBuildGridOnMsg) uses the same release, silently.

Tests: tools/test_build_catalog_escape.js now has 14 checks, including an unlisted Build/Buy widget name, the HUD-browsed catalog, a non-Build/Buy HUD Escape, and Live mode. tools/test_build_cursor.js has 15 checks, including Ctrl+Alt+B while browsing the catalog. Full suite: passed true, input_stable true, 1,333 checks. Build results follow in the round summary.

## Live result (follow-up)

2026-09-30: with dist 2026-09-30_180756, Leo placed items with the Build cursor after choosing them in the catalog, so the catalog no longer took the cursor's keys.
