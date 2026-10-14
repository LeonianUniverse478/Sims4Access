# Catalog tree and search (2026-10-14)

Leo asked for Build mode objects to be chosen from a tree of categories rather than by tabbing through the Buy panels, with a key for searching.

## Behavior

- **Ctrl+Alt+O** (Build mode) opens native pickers: Search the catalog, By room, By function. A room or function lists the Buy panel's own subcategories, and a subcategory lists its items with price and colours. Enter on an item picks it up, as clicking it in the catalog does, so Ctrl+Alt+B places it with the Build cursor as before. Escape goes back one level, and closes at the top.
- **Ctrl+Alt+D** asks for a search word (Plus `ask_text`) and lists the matches the same way. No matches says so and asks again; an empty word returns to the tree.
- An empty subcategory (for example Pets without Cats & Dogs) says "There is nothing here in your game" and stays on the subcategories. If the catalog does not answer within 5 seconds, it says so.
- Ctrl+Alt+F was not used: it is the Build grid's aim key. Ctrl+Alt+N was not used either: it starts NVDA, and test_keyboard_v7 keeps it free. Leo chose O for the tree and D for search.

## Why pickers, not a free-floating tree

In Build mode, plain keys belong to the game: arrows pan the camera, and letters and digits are Build tools. Only the Build cursor takes plain keys, through Flash ownership (A11yBuildGridOwner). A native picker owns the keyboard while open, so none of these keys reach Build mode. TS4 Access already reads pickers (action queue, events), and each Enter and Escape moves one level, as in a tree.

## Source of truth (EA's BuildBuyNavigation and BuildBuyLibrary movies, 1.128.90, decompiled read-only)

- The tree is the Buy panel's:
  - CatalogData.ROOM_CATEGORIES (8 rooms) and BUY_CATEGORIES (13 functions, with Pets spliced in for Cats & Dogs);
  - each panel's FilterButtons (BuildBuy/Navigation/<Panel>.as) in declaration order: CategoryTags, CategoryTagsPriority, ProductType and TooltipText;
  - labels from FilterTooltips, resolved to KeysBB and Keys hashes.
- `tools/gen_catalog_tree.py <BuildBuyNavigation export> <BuildBuyLibrary export>` writes Scripts/tyjokr_a11y_catalogtree.py: 21 groups and 174 subcategories. Labels are string hashes the game shows in the player's language (`menu._ls_hash`). Regenerate after a game patch from fresh FFDec exports.
- Lists come from `BBRequestProductCatalog`, as the product catalog does.
  - Tag names resolve as `FilterButton.CategoryTags` does: a FilterCategories Array is a group, expanded by `TuningTagsUtils.GetGroup`, and a single hash goes through `GetTagValueFromHash`.
  - Search follows `BuildBuyNavigationMain.OnSearch`: a SearchResult with `devString`, sorted by `SEARCHGROUP_OPENSEARCH_SORT`.

## Files

- Scripts/tyjokr_a11y_catalog.py (new) and Scripts/tyjokr_a11y_catalogtree.py (generated).
- flash/TooltipManager_patched.as:
  - `A11yCatalogTags` and `A11yCatalogBrowse`, and `browse` in A11yPlusHandle.
  - Replies and selection reuse A11yPlusCatalog's pages and A11yPlusSelect, under GFX-SAFETY.
- Scripts/tyjokr_a11y_keys.py: chords O (`catalog`) and D (`catalogfind`). Like the action queue, they refuse over a dialog, and ownership is re-checked on the pump turn.
- Scripts/tyjokr_a11y_plus_core.py: `choose` passes a LocalizedString title through, as it already did for rows. Plain titles are unchanged.
- Scripts/tyjokr_a11y_shortcuts.py: spoken meanings for both chords (the keys help list).
- tools/test_catalog.py (11 tests), tools/test_catalog_bridge.js (6 checks). tools/test_scanner_v5.py's pinned chord list adds O and D.
- CONTROLS.txt: BUILD: CATALOG TREE AND SEARCH.

## To check live

- That `BBRequestProductCatalog` answers with Build mode open but no catalog panel showing.
- That the picked-up item is what Ctrl+Alt+B then places.
- Search wording, against the Buy panel's own search box.
- Whether TS4 Access reads the picker titles (catalog labels).
