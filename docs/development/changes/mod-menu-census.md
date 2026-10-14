# Mod menu census (2026-10-04)

Mod menus should be accessible, because players install mods. Survey of one player's Mods folder (239 files):
- No mod package contains a Flash (GFX) resource; the only one is TS4_Access_UI.package. No mod draws its own screens.
- Every script mod builds its menus from EA's ui.ui_dialog classes. References per class, counted from each archive's bytecode:
  - Carl's Dine Out Reloaded: UiItemPicker 5, UiDialogNotification 6, UiDialogOkCancel 1.
  - Lumpinou RPO Core: UiDialogTextInputOkCancel 12, UiItemPicker 11, UiDropdownPicker 2, UiOutfitPicker 2, UiPurchasePicker 2, UiRecipePicker 2, UiSimPicker 2, UiObjectPicker 2, plus OK and notification dialogs.
  - NisaK Wicked Perversions: UiObjectPicker 12, UiPurchasePicker 3, UiOutfitPicker 2, UiSimPicker 2, UiDialogTextInput 2, UiDialogTextInputOkCancel 2.
  - WickedWhims: UiSimPicker 4, UiDialogOkCancel 4, UiMultiPicker 3, UiDialogMultiPicker 2, UiOutfitPicker 2, UiDialogTextInput 2, UiObjectPicker 2.
  - Basemental Drugs: UiItemPicker 12, UiDialogTextInputOkCancel 10, UiPurchasePicker 4, UiSimPicker 2, plus OK and notification dialogs.
  - MC Command Center (mc_cmd_center): one shared helper each for UiItemPicker, UiSimPicker, UiOutfitPicker, UiDialogTextInput and UiDialogOkCancel.
  - roBurky Meaningful Stories: UiSimPicker 2, UiObjectPicker 2, UiDialogTextInputOkCancel 2.
  - tyjokr Autonomous Wants: one UiDialogOkCancel. XmlInjector: three UiDialogOk.

So mod accessibility is window-type accessibility: fixing one EA window type fixes it for every mod that uses it.
- Already handled by TS4 Access: pie menus, notifications, OK and OK/Cancel dialogs, PickersMain (object, item and sim pickers), the purchase picker and the recipe picker.
- Not yet established: text input dialogs, UiOutfitPicker (no TS4 Access code), UiDropdownPicker and UiMultiPicker/UiDialogMultiPicker (MultiPickerCellView traversal only).

## Behavior

The new module tyjokr_a11y_modui.py only logs. While diagnostic logging is on, it wraps `UiDialog.build_msg` (EA's original runs first) and writes one "modui:" line for every dialog whose stack includes a mod frame. That line holds:
- the mod's module and file
- the dialog class
- the raw-text title and text (a string-table key is logged as "key 0x...")
- the row count and the first 8 row names
- text input names and the picker type

A mod frame is the first frame whose file name is outside EA's `T:\InGame\...` (the game's own Lib, Core and Server code all start that way) and outside TS4 Access. Dialogs from EA code and XML-only mods are not logged. Paired with the existing "UI owner:" and SPEAK lines, the log shows which window types read correctly and which stay silent.

## Files

- New: Scripts/tyjokr_a11y_modui.py and tools/test_modui.py (3 tests).
- Changed: Scripts/tyjokr_a11y_keys.py (the startup import).
