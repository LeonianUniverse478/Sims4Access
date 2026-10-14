# Inventory item menu with selling (2026-09-30)

## Behavior change

Enter on an item in the Sim's inventory panel (SimInfoInventoryPanel, multiselect off) opens a TS4 Access item menu, titled with the item's name, instead of going straight to EA's pie menu:

- **Item actions** replays the original click on that cell, so EA opens its usual pie menu (`OpenPieMenuWithObjectId`, built by EA's own handler).
- **Sell for N** for a single item. For a stack: **Sell one for N**, **Sell all C for T** (asks first: "Yes, sell all ..." / "No, keep them"), and **Choose how many to sell**.
- **Choose how many** opens EA's native sell picker for that item (quantity, price, total, Sell).
- Items EA will not sell (`non_deletable_by_user`, or `is_sell_disabled_from_component()`) get "This item cannot be sold." instead of sell rows.
- Items that are not in the active Sim's own inventory, such as an object inventory shown beside it, keep EA's menu directly.

Household or Build Mode inventory selling is deliberately out of scope (Leo will do it later). A planned accessibility-menu row, "Sell from inventory" (the sell window for the whole inventory), was not built in this round.

## Source of truth (game 1.128.90)

- The inventory cell is `InventoryCellViewButton` with a public `GetObjectId()`. Its click goes to `SimInfoInventoryPanelMain.OnSimInventoryCellClick`, which toggles a selection in multiselect and otherwise calls `OpenPieMenuForItem`.
- The panel's Sell (multiselect) sends `SendInventorySellRequest` with `sim_id`, `currency_type` (`CurrentRegionCurrencyBucksType`), `stacks` and `items` (`id`, `count`), handled by `inventory.sim_inventory_sell_multiple`. That command applies `sim_info.get_item_sell_price_modifier`, reduces stacks with `update_stack_count(-count)`, pays through `household.add_currency_amount` (INVALID = simoleons), batch-destroys empty stacks and sends `InventorySellItemsComplete`. Sell one and Sell all call this same command function with a one-item request.
- The native sell picker is `UiSellPicker`, set up as `SellPickerInteraction._setup_dialog` does: `inventory_object_id` is the Sim's id, `use_dialog_pick_response` is False, and each row is a `PurchasePickerRow(def_id, is_enable, num_available, tags=definition.build_buy_tags, custom_price, objects)`. On Sell, the client runs `inventory.sell_picker_response_by_ids`, which pays price times amount and stores `ids_and_amounts_and_price` and `source_inventory` on the dialog. Our listener then removes `min(amount, stack_count)` with `source_inventory.try_destroy_object(obj, count)`, as `_remove_sold_objects_from_inventory` does.
- Prices shown are the panel's `round(current_value * modifier)`. The sell picker row uses the same per-item price.

## Files

- flash/TooltipManager_patched.as: `A11yInventoryMenu` (Enter intercept, by name only, falling back to EA's click on anything unexpected), `A11yInvItemActions` (click replay), listener registration, `mA11yInvCell`. It is loaded-zone only; inventory does not exist before a lot, so there is no startup-socket channel.
- Scripts/tyjokr_a11y_hub.py: `a11y.invitem_enc`, item menu, sale, confirmation and sell window. `_window` takes an optional localized title.
- Scripts/tyjokr_a11y_lang.py: new terms (en and pl).
- CONTROLS.txt, docs/patreon/03.
- tools/test_inventory_sell.py (11 tests), tools/test_inventory_sell.js (17 checks).

## Evidence

- The first `Dev.ps1 build` stopped at tests: the fixture in `tools/test_recipe_picker.js` runs the real `A11yActivate` with hand-listed helpers and lacked the new `A11yInventoryMenu`. The call threw inside the fixture, so Enter dispatched nothing. The fixture now loads the real `A11yInventoryMenu` (which declines recipe rows); runtime was unchanged. `tools/test_event_activation_v13.js` was unaffected.
- Rebuild: exit 0, dist `2026-09-30_103043`. `build/v10-checks.json`: passed true, input_stable true, 1,266 checks across 80 suites.
- Main fidelity gate PASSED; compat fidelity gate PASSED (19 targeted comparisons).
- SHA256: TS4_Access.ts4script `2f8b1c7c689db06f3dc6bee8f5a6ae7ff51544ef32e125d7aee8310c55ec7ae8`, TS4_Access_UI.package `4b7ecf0e9ecacbd99b117a87b3abe50820e326f8425ec7d531f8d30dc8548d56`, compat `7fad5ba744e5b7144161b56e1282dda58e0358c3261c908df70113a287491ce3`.
- Installed to Leo's Mods root on 2026-09-30 with the game closed; hashes verified; cfg unchanged.

## Needs live testing

The sell window path depends on the client sending `sell_picker_response_by_ids` before the dialog response, as it does for EA's own sell picker interactions. Check that funds rise by the total and the chosen amount leaves the stack, and that Escape sells nothing. Also check that Item actions opens the usual pie menu, that multiselect Enter still selects, and that selling works in a non-simoleon region if one is available.

## Live result

2026-09-30: Leo tested the installed build (dist 2026-09-30_103043) on game 1.128.90 and reported that the feature works flawlessly. Screen reader, voice, save and the exact cases tried are not yet recorded.
