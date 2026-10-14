# Household transfer, funds and move labels (2026-10-04)

Leo reported that the house transfer screens and fund transfers have unlabeled options, so players cannot tell where money or Sims are going. The direction exists only as arrows and artwork.

## Source of truth (EA movies from game 1.128.90, decompiled read-only)

- **TransferPanel movie** (`widgets.TransferPanel.controls::TransferPanel`, Household Split and Merge):
  - `btnTransferTo` moves the selected Sims of `mcSourceHousehold` into `mcTargetHousehold`, and `btnTransferFrom` the reverse (`OnTransferClick`).
  - Each `TransferHouseholdPanel` names its household in `txtHouseholdName`. Sims are listed in `slTransferSims`, and each panel has its own `cbSellFurnishings`.
- **Shared Transfer Funds panel** (`widgets.shared.controls.TransferFunds::TransferFundsPanel`):
  - The left side is the source household (`txtSourceFamily`, `mcLeftFunds`) and the right side the target (`txtTargetFamily`, `mcRightFunds`).
  - `OnTransferRightClick` moves the amount source to target, and `OnTransferLeftClick` target to source.
  - Both buttons carry the same tooltip (TRANSFER_FUNDS_TRANSFER or a disabled reason). `txtAmountLabel` is the amount's label.
- **RetailFundsTransfer movie** (`RetailFundsTransferMain`):
  - The `ddFrom` and `ddTo` dropdowns each show a lot name and balance, with no From or To label of their own.
  - `txtAmountTranslated` is the formatted amount, and `btnConfirm` confirms.
- **GameEntryMovePanel** (`MoveInPanel` and its Plex and MultiUnit variants): `ddOutOptions` (furnishings of the old home) is labelled by `txtMoving`, and `ddInOptions` (the new home) by `txtInOptions`. The existing `A11yMoveInQuote` already reads the choices and remaining funds.

## Behavior

`A11yTransferQuote` and `A11yMoveLabel` run with the other quote helpers on widget and focus reads. Panels are found by duck typing on their public fields. Flash posts a `dir<kind>` marker with the names, and Python's `_clean_glyphs` words it from the language table (English and Polish) before the currency rule. An empty name becomes "the other household". Spoken examples:
- **Funds arrow:** "Moves the amount from Fields to Goth. Transfer Funds. Fields has 12,000 simoleons. Goth has 0 simoleons."
- **Amount field:** EA's amount label, then the number, then both balances.
- **Transfer Sim(s) button:** "Moves the selected Sims from Fields to Goth", then EA's tooltip or its disabled reason.
- **A Sim or Sell Furnishings in a list:** "Kim Fields. In household Fields."
- **Retail dialog:** the lists say "From" and "To" before their own lot and balance, the amount field says "Amount", and Confirm adds "Transfers 500 simoleons from <from> to <to>".
- **Move dialog:** each furnishing dropdown is preceded by its own label (txtMoving or txtInOptions).

## Files

- Changed: flash/TooltipManager_patched.as (`A11yJoinedText`, `A11yTransferQuote`, `A11yMoveLabel` and the call site), Scripts/tyjokr_a11y_narrator.py (`_direction` and the marker rule), Scripts/tyjokr_a11y_lang.py and CONTROLS.txt.
- New: tools/test_transfer_labels.js (11 checks) and tools/test_transfer_wording.py (4 tests).

## Test expectations updated

tools/test_flash_navigation_v10.js stubs each quote helper that `A11yAnnounceDisplay` calls; it now also stubs `A11yTransferQuote` and `A11yMoveLabel`, which have their own suite. Without the stubs the call threw and the read posted nothing. tools/test_options_simplified.js pins the call order of the quote helpers; it now allows the two new calls between `A11yMoveInQuote` and `A11yOptionsRowLabel`. Runtime was not changed for either test.

## Not live-tested yet

Split and Merge from Manage Households, from the phone (Split Household), and Ask to Move In; the retail transfer from the owned business panel; and the move dialog.
