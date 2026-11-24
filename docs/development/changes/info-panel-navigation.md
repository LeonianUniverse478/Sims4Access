# Info-panel navigation

- `flash/TooltipManager_patched.as`, `A11yFindScrollList` (around line 6830): Needs, Simology and Aspirations walk their fully instantiated controls directly. Native slider reveal remains active. The one-cell content lists in Simology/Aspirations can restart sections when indexed. Pickers and other panels retain indexed navigation.
- `A11yTextDecoration` (around line 6345): exclude artwork explicitly linked as a parent's `mcControllerHighlight`, observed as duplicate Sim Profile stops.
- `A11yKeyboardDecoration` (around line 6430): skip empty temperament/curse cells using EA's public `IsEmpty` getter.
- `tools/test_nested_lists.js`: forward/backward panel traversal, nested trait/goal grids, single-cell wrappers, and an independent purchase picker. `tools/test_flash_navigation_v10.js`: empty/occupied occult slots, linked highlight artwork and unrelated-control isolation.

Live evidence: current installed package hashes matched the candidate. Read-only focus snapshots exposed 13 Needs targets (including two empty temperament slots) and 40 Simology targets. Both navigation keys were reported affected. Runtime confirmation of the fix remains required.

Offline checks: 111 suites passed, 1,497 reported checks, with stable inputs. Final compiled validation is recorded with the candidate build manifest. Runtime confirmation remains required.

Revert these three method changes and their tests, or restore the preceding paired UI packages. No Python changes.
