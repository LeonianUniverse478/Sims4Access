# Household away actions

- `Scripts/tyjokr_a11y_away.py`: separate household picker and native PICK_SKEWER request. Rechecks actor, household, zone and target presence after dismissal; refuses invalid context/coordinates and logs requests/failures. No Sim selection, travel or direct away-tracker changes.
- `Scripts/tyjokr_a11y_hub.py`: lazy callback, one Away actions row and `a11y.away` command. `Scripts/tyjokr_a11y_lang.py`: English/Polish labels and feedback. CONTROLS.txt / CHEATS.txt: entry points.
- `tools/test_away_actions.py` and `tools/test_scanner_pick_bridge.js`: remote target IDs, membership/presence guards, failures, native pick transport and hub wiring.

Native evidence: current game server.pick_info defines PICK_SKEWER=11. interaction_commands.generate_choices resolves this pick through sim_info_manager and sim_skewer_affordance_gen, which yields native work/rabbit-hole actions or default/custom away-action affordances. Existing Flash pick handling already forwards this type and owns request IDs, menu lifecycle and interaction confirmation.

Live test: travel with one household Sim, open Accessibility > Away actions, select a Sim at home and choose an available native focus. Escape must cancel without changing focus; returning Sims must not remain actionable through stale picker rows. In-game results are separate from offline checks.

Rollback: restore the previous script archive, or reverse the source patch and remove the away module.
