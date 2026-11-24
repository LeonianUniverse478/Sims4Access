# UI port for game 1.129.39.1030

- Rebuild the 25 supported UI movies from the current game extraction, retaining existing accessibility hooks and EA's updated saving-dialog behavior.
- Read trait-dependent need names, including occult variants; bound spoken percentages and omit invalid values.
- Expose occult rank/points rows and individual ability buttons through keyboard traversal.
- Expose Manage Worlds neighborhood expansion and visible destination households through their native controls.
- Preserve UI Cheats' ten-item right-click cart changes alongside purchase narration.
- Keep focus on the item when Enter cannot reach an enabled purchase confirmation; read the native empty-cart/funds reason and quantity controls instead of stranding focus on disabled Done.

Code locations: `CommodityContainer.A11yMotiveText`; `TooltipManager.A11yInformational` and `A11yCompositeRow`; `DialogMain.HandleShowSavingDialog`; compatibility cart preparation in `flash/prepare_uicheats_purchase.py` and `build_uicheats_compat.ps1`.

Detailed validation and deferred Gallery work are tracked in `docs/development/UI-PORT-1.129.md`. In-game verification remains required.
