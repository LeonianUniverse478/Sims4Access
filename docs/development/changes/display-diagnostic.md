# Build display diagnostic adapter

- `Scripts/tyjokr_a11y_display_diagnostic.py`: `a11y.inspect_display [delay]` (default 5, clamped 0..30 seconds); process-scoped Win32 measurements, saved display-option whitelist and capped JSON logging under `display inspect:`. Records reported/physical cursor coordinates, client/screen round trips, window/thread DPI awareness, monitor scale, window style and desktop metrics. No input injection, DPI changes or settings writes.
- The console command enables passive wrappers on the currently installed build module. Wrappers preserve project/conversion arguments, exceptions and return values, and measure on their actual calling worker. Diagnostic failures cannot interrupt a build. No planner module replacement is needed.
- `tools/test_display_diagnostic.py`: scaled/offset coordinates, process/focus guards, optional API failures, private pointer-width bindings, rate cap, options privacy, transparent wrappers and no-action delayed command. CHEATS.txt: command instructions.

The game UI-stage dimensions remain explicitly null: client pixels, saved rendering resolution, UI scale and stage units must not be treated as interchangeable. The diagnostic command does not request a game projection or enable/move either cursor. An existing user-initiated build operation supplies passive projection/conversion records.

API references: [Microsoft DPI conversion](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-logicaltophysicalpointforpermonitordpi), [GetScaleFactorForMonitor](https://learn.microsoft.com/en-us/windows/win32/api/shellscalingapi/nf-shellscalingapi-getscalefactorformonitor). Physical-point conversion is tied to the supplied window's awareness; both thread/window contexts are recorded for interpretation.

Live capture: enable logging, enter Build Mode, run `a11y.inspect_display 5`, close the console and keep the game focused for five seconds. Compare with passive records from the builder worker before choosing a conversion correction. A manual snapshot by itself does not validate projection units.

The installed planner was compared with the checkout: the installed module lacks the source's `_client_size` / `_client_to_screen` overrides. This diagnostic preserves that installed implementation for measurement.

Rollback: restore the previous script archive, or remove the diagnostic module and its cheat documentation. Disabling logging stops passive observations; wrappers are reset on game restart.
