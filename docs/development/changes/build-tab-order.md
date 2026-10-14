# Build mode Tab: catalog sections first (2026-09-30)

Leo asked for Tab in Build mode to work like RimWorld Access: straight into the catalog (filters, search, categories and items) instead of Tabbing through EA's tool buttons, which already have native hotkeys.

## Behavior

While browsing the Build panels from the world in Build mode (HUD browsing, no modal root), Tab and Shift+Tab move through these sections, each sorted in screen order within itself:
1. BuildBuyFilter, when live.
2. BuildBuyNavigation.mcSearchContainer (NavSearchBar).
3. BuildBuyNavigation.mcButtonContainer (the Build, Buy, Function and Inventory tabs).
4. BuildBuyNavigation.mcNavPanel (room, build and function categories).
5. BuildBuyProductCatalog.mcCatalog.mcCatalog (the product ScrollList).
6. BuildBuyProductCatalog.mcCatalog.mcVariationSelector (swatches).

BuildBuyInspector (undo, redo, sledgehammer, eyedropper, the move tools) is not collected. Everywhere else (Live mode, menus, dialogs, a modal root), A11yCollectBuildSections declines and Tab keeps the full-screen collection. Escape still releases the catalog back to the Build cursor.

## Source (1.128.90 decompile)

The field names come from BuildBuyNavigationMain (mcSearchContainer, mcNavPanel, mcButtonContainer), NavigationPanel (mcRoomCategories, mcBuildCategories, mcFunctionCategories), CatalogPanel (mcCatalog ScrollList, mcVariationSelector), and the BuildBuyFilter widget (shown by ShowBuildBuyFilter). All are read by name only.

## Files

- flash/TooltipManager_patched.as: A11yBuildSections and A11yCollectBuildSections; A11yTabControl falls back to the old collection.
- CONTROLS.txt, docs/patreon/04.
- tools/test_build_tab.js (7 checks).
- tools/test_simplified_menus.js: the fixture now loads the real A11yBuildSections and A11yCollectBuildSections. They decline outside Build mode, so its grouped-Tab expectation is unchanged. Before this, the fixture's missing method threw inside A11yTabControl.

## Evidence

- Full offline suite: passed true, input_stable true, 1,351 checks across 89 suites.
- `Dev.ps1 build` exit 0, dist `2026-09-30_191957`. Main and compat fidelity gates PASSED (19 targeted comparisons).
- SHA256: TS4_Access.ts4script `1190b40293e4eefd3b0423953e660ef736cd063d34f5d38f3bafa024a13a3148`, TS4_Access_UI.package `c5f55dcf3a7fe2b45868a13c21f0ee8528e223dcd764163e0391b076aadc2e4b`, compat `b8a9ce49402b046811d101cf59a30eae7ecccb20bc75534de8a9f2d24c08ad0a`.
- Installed to Leo's Mods root on 2026-09-30 with the game closed; hashes verified.

## Needs live testing

- That the first Tab lands on filters or search.
- The section order and wrap-around.
- That arrows inside a section behave as before, and that the search field accepts typing.
- That choosing a product still reports it (a11y.buildproduct), so Ctrl+Alt+B or Escape returns to the cursor with it chosen.
