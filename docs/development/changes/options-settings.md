# Game Options activation

- `flash/TooltipManager_patched.as`, `A11yOptionsControl` / `A11yActionProxy` (around 6102 / 6777): route Options cell activation to its visible native checkbox, dropdown or text button. Retain native enabled checks, events, dropdown selection and Apply/Revert handling.
- `A11yOptionsRowLabel` / `A11yCheckboxState` (around 6125 / 7730): read the localized label, visible value/descriptions and actual checkbox state; omit hidden controls and checkbox placeholder text. Re-read checkbox rows after activation using the existing settled-focus mechanism in `A11yActivate`.
- `tools/test_options_simplified.js`: settings type/target, disabled control, label/value, hidden artwork, checkbox state, description and subclass coverage.

Reproduction: Gameplay Auto Age and Pack Settings rows were announced, but Enter clicked the outer CellView rather than the child owning the native event. Dropdown rows also read hidden checkbox artwork as unchecked. Fix leaves row order and keyboard bindings intact.

In-game test: Enter on Auto Age opens its choices; arrows then Enter choose a value. Enter/Space on a checkbox toggles and reads its state. Apply Changes saves normally. Check Gameplay, Pack Settings and a neighbouring Audio/Graphics option; verify scanner Enter after closing Options. In-game results are recorded separately from offline checks.

Rollback: restore the paired previous UI packages, or reverse the source patch. No script change.
