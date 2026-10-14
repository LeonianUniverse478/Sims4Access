# CAS styling menu: research only, for tyjokr's review (2026-09-30)

**No code was written for this. Nothing here is in the builds.** Leo would like a keyboard menu for styling Sims inside the normal CAS flow (hair, clothing, accessories, makeup, colors and so on) without the mouse. GFX-SAFETY.md and ARCHITECTURE.md currently put CAS out of scope, so this note asks whether you would accept that work and in what form. All findings come from offline FFDec decompiles of EA's own movies from game 1.128.90.1030, made in a scratch folder outside the kit. Nothing was rebuilt, installed or launched.

## What EA's CAS does

- **Where the style grids are.** Hair, clothing, accessories, makeup, face and body presets and skin tone are panels in **CASCustomizer**: `ClothingPanel`, `GenericCatalogPanel`, `FaceModPanel`, `BodyModPanel`, `SkinTonePanel` and `ColorSwatchPanel` (the last also defined in CASLibrary), fed by `widgets.CAS.data.CatalogDataFeed`. This is the movie that crashes on any FFDec rebuild, and it must stay excluded.
- **Where the item lists come from.** `CatalogDataFeed.RequestData` calls `CASAPI.GetCatalogBaseItemsUsingFilter`, and `CASAPI.GetCatalogBaseItems` wraps one game service: `CommunicationManager.CallGameService("GetCatalogBaseItems", {state, tags, excludeTags, unlocks, locked, mtx, mods, packIds, ...})`, where `state` is the `MenuState` category. `CASAPI` and the item class `CASCatalogProduct` are defined in **CASLibrary**, which your 2026-08-20 notes record as rebuilding and running fine.
- **What an item carries.** A `CASCatalogProduct` has `data_id`, `title` and `description` (LocKey), `lockedTooltip`, `image`, `body_type`, `menu_state`, `groupId`, `packId`, `is_modded`, `is_reward`, `mtxState`, `gender`, `age`, `species` and `variation_id`.
- **How an item is worn.** Every panel ends in one service call, `CallGameService("SetCatalogSlotSelected", {data_id, color_data_id?, layer_index?, layer_id?})`. Examples: `ClothingPanel` around line 705, `GenericCatalogPanel` around 429, `FaceModPanel`/`BodyModPanel` presets using `data_id`, and `CatalogDataFeed.MakeRandomSelection`.
- **Swatches and colors.** Swatches use `GetCatalogVariantItems` and `GetCatalogVariantItemSelected`. Skin, hair and makeup colors use `CasGetSwatchColorList`, `CasGetSwatchColorSelected` and `CasSetSwatchColorSelected`.

## Why this might be possible without touching CAS movies

These are plain game services, callable from any movie through `CommunicationManager`. The shared TooltipManager template already runs in CAS today (CAS names, Stories scope and input fields). A CAS styling menu could therefore be driven from the template, with the lists requested by `MenuState`, the choice applied with `SetCatalogSlotSelected`, and `CASAPI`/`CASCatalogProduct` resolved only by `getDefinitionByName` inside try/catch if needed. The CASCustomizer, CASNavigation and CASLibrary movies would stay EA's untouched originals. The UI side would be a keyboard list (category, optional filter tags, item, then color), probably as a native-style picker or a template-owned list.

## Main unknowns

1. **Labels.** Many CAS items may have empty `title` keys, because EA relies on thumbnails. The fill rate by category is unknown and can only be measured live. If titles are sparse, rows could be described from what the game does provide: filter tags (the same localized words the CAS filter panel uses, such as length and texture for hair), pack, colors, custom content, reward and locked states, and position ("14 of 120"). That is usable, but not equal to seeing the thumbnail.
2. **Transport.** CAS from the main menu has no loaded zone, so Python replies need the startup socket (as the CAS name work already uses). CAS from a lot has the command path.
3. **Sim context.** Correct `MenuState`, age, gender, species and occult filtering, outfit category, and the multi-Sim household in CAS need care to match what the grid shows.
4. **Sculpting.** Presets use `SetCatalogSlotSelected` and are straightforward. Free-form face and body sculpting (the detailed edit mode and sliders) is much harder and would be a separate, later question.
5. **Testing cost.** This feature genuinely needs full CAS runs, which CLAUDE.md otherwise asks to avoid.

## Relevant history already in the kit

- CASCustomizer crashes on any rebuild (2026-08-03, twice). CASNavigation patched with a hook crashed once when entering CAS from the main menu (2026-08-20, round 1), recorded as inconclusive and never retested from a lot. CASLibrary and CASStories rebuilt fine. (docs/development/history/PLAN-FULLGAME.md)
- glaroc's a11yscan styled Sims outside CAS through Python natives: `cas.cas.get_catalog_casparts_by_bodytype(...)` returning `{part_id: (tags, tooltip)}`, and `set_caspart(...)` (A11YSCAN-REVIEW.md). That separate live-Sim appearance editor was deliberately excluded from an earlier release (SIMPLIFIED-MENUS-REVIEW.md). It is a possible second route, but it edits Sims outside the normal CAS flow, which is not what Leo is asking for.

## Suggested first step, if you agree

A read-only live probe, with no CAS movie override: in a CAS session entered from a loaded lot (mirror or dresser), call `GetCatalogBaseItems` for a few menu states from the template and log item counts and how many have non-empty `title` keys. That answers the labels question and confirms the service is reachable from the template, before any menu is designed.

## Questions for you

- Would you accept CAS styling work in a return if it never rebuilds a CAS movie?
- Do you prefer the in-CAS template route above, or glaroc's Python `cas.cas` route?
- Any CAS pitfalls from your own work that are not in the history docs?
