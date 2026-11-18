# Experimental basement adapter

- Add native Basement Tool drawing from floor 0, verified as a complete new rectangle on floor -1. Reject overlaps, changed prior room geometry and unverified results; restore Room Tool before continuing.
- Route basement rooms in existing house plans through this adapter; ordinary floor workers remain delegated. Add Alt+B basement assistant for a standalone room or read-only native floor/room diagnostics.
- Register experimental_basement in the existing config and accessible settings menu. Preserve stored choices.

Code: Scripts/tyjokr_a11y_basement.py; bootstrap hook at the end of contrib-reference/modules/tyjokr_a11y_contrib.py install(). Controls: CONTROLS.txt. Tests: tools/test_basement_adapter.py.
