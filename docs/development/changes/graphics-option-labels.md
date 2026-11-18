# Graphics option labels

`flash/TooltipManager_patched.as`: `A11yGraphicsRowLabel` pairs the twelve native `dd*` dropdowns with their localized `lb*` labels on GraphicsTab, DefaultGraphicsTab and MacGraphicsTab. `A11yOptionsRowLabel` calls it before existing row handling. `A11yCheckboxState` also recognizes the exact native `widgets.OptionsMenu::LeftLabelCheckBox` class and reads its Selected value. Values, popup choices, navigation and setting activation are preserved.

Evidence: live log 2026-11-09 21:47-21:48 read unnamed Low/High/Custom values. Current native GraphicsTab.ConfigUI sets the matching localized labels; Graphics uses standalone controls rather than OptionsCellView rows.

`tools/test_options_simplified.js`: Windows/Mac labels, nested value focus, disabled controls, hidden/missing labels, popup choices, checkboxes and unrelated tabs. 19 checks pass offline. Live verification pending.
