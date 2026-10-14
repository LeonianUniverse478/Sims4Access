# Business employee hiring by keyboard (2026-10-04)

Leo, hiring staff for the WickedWhims strip club: the hire list showed every name but could not be navigated, so hiring needed the mouse.

## Evidence (Leo's log, 16:23)

- BusinessEmployeeManagementMain opened from Manage Employees.
- Tab had two stops:
  - "Current Janitor(s). txtSimName. txtPay. txtSatisfaction. Select a Sim below to hire."
  - "Janitor(s) available for hire.. Dwayne Deddens. Briana Fountain. ..." (every candidate in one block)
- The mouse-opened EmployeeDialog then read correctly: "Do you want to hire Brandie Kumar?".
- The owned-business panel's markup dropdown was heard as the derived name "dd Profit Margin".

## Source (BusinessEmployeeManagement movie, game 1.128.90)

- Groups are EmployeeGroupCellView (CellView) wrapping `mcGridView`, a GridView of EmployeeCellView buttons. A cell click (GridEvent CELL_EVENT + PushButtonEvent.CLICK) opens the hire dialog.
- A current employee's cell is set `enabled = false` and shows btnPromote, btnDemote and btnFire.
- Open and locked slots are disabled cells with a slot tooltip, and their unused text fields keep their instance names.

## Behavior

- `A11yCompositeRow`: an EmployeeGroupCellView is a container, so its group name and each Sim cell are separate stops. Enter on a Sim to hire activates the cell as a click does, and EA's own hire dialog follows.
- `A11yCollectFocusables`: a business employee cell (btnFire, btnPromote, btnDemote and mcSatisfactionTooltipHolder all present) is pushed with the usual size, stage and viewport checks even when disabled. Its visible Promote, Demote and Fire buttons are collected after it.
- Narrator `_is_placeholder`: a lowerCamel field identifier (txt/mc/btn/dd/cb/sl/lb/tf followed by a capital) is placeholder text and is not read.
- Narrator `a11y_widgetname_enc`: a leading control-type word is dropped from derived names, so "dd Profit Margin" is read as "Profit Margin".

## Files

- Changed: flash/TooltipManager_patched.as and Scripts/tyjokr_a11y_narrator.py.
- New: tools/test_business_employees.js (7 checks) and tools/test_placeholder_names.py (3 tests).

## Not live-tested yet

Hiring by Enter, and Promote, Demote and Fire, in game.
