# Native chair snapping

Adds tyjokr_a11y_chair_snap.py as a plain-function module called by the existing grid and placement transaction. Dining and desk chairs can snap when facing an adjacent compatible table/desk, or when that table/desk is explicitly focused with number 1. The native slot supplies position and rotation; ambiguous table choices require focus.

A definition-only native check previews the exact seat. After the normal tool-drop acknowledgement, the actual chair must pass the same slot's native placement check. Slot attachment is read back before and after registration, and payment follows those checks. Ordinary placement, surface-object placement, and the separate orientation-hint preference keep their existing paths. No keyboard thread, runtime helper replacement or Flash change is added. A separate experimental chair-snapping flag is persisted in the native settings schema.

Tests exercise the real grid entry point and placement/payment implementation with native stand-ins. Live confirmation is pending.
