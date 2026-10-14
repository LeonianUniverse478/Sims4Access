# Phone and clock hotfix candidate

Includes the previous modifier-history and focus-return fixes from 19:18.
Adds Ctrl+Alt+C and Accessibility menu > Day and time (approved by the user).
Reads the game-localized clock display and its paused label. Missing clock
text produces an explicit unavailable response. No guessed weekday fallback.

Phone shortcut Ctrl+Alt+P now distinguishes keyboard navigation ownership
from blocking dialogs. The call alert, ordinary SimInfo HUD panels, HUD
browsing and status scopes no longer trigger the blanket dialog refusal.
Real dialogs, pickers, pie menus and dropdowns remain blocked. The request
rechecks blocking and text-entry state on the simulation thread before
opening the call or switching its recipient. Old UI packages retain the
conservative refusal behavior; distribute the paired script and UI packages.

Validation: 1,187 checks across 73 isolated suites pass on stable source
(includes repeated imported checks). Includes 20 Flash source fixture checks
for owner types, alert-to-dialog transitions, repeated/reset reports, clock
localization, paused state, and missing clock. The previous poller executable
code is unchanged against the 19:18 candidate (line offsets excluded).
Claude independently reviewed the UI source and supplied/reviewed Python.
Two outdated test expectations were corrected for the new C shortcut and
three-bit context format; invalid payload coverage remains.

Live verification is still pending. No game files installed, game launched,
screen control resumed, or downloads published during this work. Offline
reproductions establish the refusal paths, not telemetry from the tester.
Before release, verify an incoming call from an existing save, including a
call for another household Sim; ordinary HUD panels; real dialog refusal;
clock while running/paused, from its hub row, and in Build; text input and
AltGr; plus the previous modifier/focus-return hotfix cases.

Artifact gate and release hashes are recorded separately alongside this file.

Independent package audit by Claude: PASS, no blockers (see CLAUDE-REVIEW.md).
Additional live cases: clock at main menu before loading a save (unavailable
feedback); clock with picker open (focus retained); call alert with a real
dialog above it (still blocked).
