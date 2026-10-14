> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# Simplified menus: full a11yscan flow review

Coverage review, September 26. This is a coverage review, not a claim that
every flow is implemented or verified. User explicitly requires the feature
to cover menus throughout the mod, not only travel. One default-on setting;
turning it off restores the current navigation. Gameplay tests use existing
saves, without another full CAS run.

LATEST SCOPE CORRECTION: CAS and Stories are explicitly excluded by the user.
Their entries below remain source-review context only, not implementation or
port targets. Existing CAS/Stories navigation must remain unchanged. Scope is
glaroc's simplified menu flows, not every bespoke backend feature he wrote.

User subsequently confirmed that optional cheat menus and the separate live-Sim
appearance editor are also excluded from tomorrow's release. Prioritize normal
gameplay menus. These exclusions are explicit user choices.

Reference: Downloads/a11yscan_2026-09-07 (1)/a11yscan/src, September 7 copy.
The earlier September 3 review is not the basis for this work.

## Shared interaction contract

Up/Down advances one logical option, regardless of visual spacing/columns.
Enter chooses an action or opens its submenu. Space toggles a multiple-choice
selection. Left/Right adjusts an editable value where appropriate. Escape
backs out/cancels. Announce label, selection/availability and position. Preserve
text editing, quantities, sliders, native restrictions and transaction checks.
No action occurs merely because a row receives focus. A single key must not
leak into the next screen. Native and simplified input must not both fire.

## Inventory and initial findings

| Flow | Glaroc source / entry | Existing implementation and review requirement |
|---|---|---|
| World objects and Sims | state.next_item / next_category, world.scan | Our scanner already supplies a tree; preserve its one-sibling navigation and selected-Sim scope. |
| Object interactions / pie submenus | state._open_menu / _activate_menu; actions.choices_for, group_by_category | Ours opens native tested interactions. Simplify option traversal and submenu/back behavior without offering untested affordances. |
| General dialogs | dialogs.options/respond; state MODE_DIALOG | Glaroc creates semantic rows including confirm/cancel. Review all native response, single-selection and multi-selection contracts. |
| Shopping / purchase baskets | state.dialog_quantity/_activate_dialog; dialogs.buy_cart | Quantity, basket membership, total and confirm are distinct operations. Linear navigation must preserve them. |
| Phone / incoming calls | state.focus_phone, answer_call, decline_call; actions.phone_choices | New native-action category list through hub Phone or Ctrl+Alt+P. Waiting calls retain priority. Native eligibility, queue checks and fresh action tests retained. Live acceptance pending. |
| Personal and household inventory | state.focus_inventory; world.inventory_entries/household_inventory_entries | Existing scanner/native inventory entry points; cover item actions, stacks, quantities, and cancel. |
| Contacts / remote social actions | state.focus_contacts; actions.relation_panel_choices | Existing contacts picker/native relationship actions; preserve distinction between nearby and remote Sims. |
| Build catalog | state.catalog_open/next_item/next_category/catalog_place | Ours uses native catalog selection plus ported placement. Simplify catalog navigation; keep price, eligibility, footprint and refund behavior. |
| Lot grid | grid.describe/move/up_level/down_level | Already ported equivalent. Spatial movement is deliberate and must not become menu option stepping. |
| Travel | state.travel_menu/travel_open; travel module | M now offers Go alone / Choose who comes. Go alone answers only the exact native companion picker owned by the pushed interaction. Native world/place lists and loading retained. Actual arrival tests pending. |
| Careers | state.jobs_open; careers module | Phone list exposes native Find a Job / Quit actions; hub opens career panel. Job and branch choices use native controls. Day-off panel and end-to-end access require live verification. |
| Events | state.events_open; events module | Phone list exposes native Plan Event. Existing native SituationCreation covers type, roles, guests, location and cost. Glaroc's obsolete direct creation code is not ported; live regression pending. |
| New Sim / CAS | state.cas_open; cas module | Explicitly excluded by the user. Preserve existing CAS navigation; no simplified-menu port or new CAS test run. |
| CAS Stories | state.stories_open; stories module | Explicitly excluded by the user. Preserve existing questionnaire navigation and scoring. |
| Appearance / outfits | state.look_open; appearance module | Separate live-Sim appearance editor explicitly excluded by the user, along with CAS. Source inventory only. |
| Load save | state.pick_open with no zone; saves.choose | Glaroc copies selected save over resume slot. Ours supports native Load Game; retain native loading and simplify its navigation. Do not import resume-slot copying merely to achieve a list. |
| Household selection / switching | state.pick_open with zone; lots.households/switch_household | Native Manage Worlds retains save prompts and household transition. Map logical navigation verified; household transition requires live acceptance. |
| Move house / merge households | state.move_house_open; lots.move_house/move_in_together | Phone list provides native Move Household and Split Household. Merge begins with the target Sim's eligible native Ask to Move In interaction. TransferPanel source uses recognized buttons/lists; live access, selection, funds and cancellation remain to verify. |
| Game settings | state.settings_open; settings.open_settings | Glaroc covers autonomy and aging only, with read-back. Our native Options covers more. Simplify navigation while preserving native values and read-back. |
| Mod settings / shortcuts | our hub/menu/shortcuts | Glaroc's game-settings menu is not our mod settings. Apply the shared contract to our own settings and help entry points too. |
| Cheats / recovery actions | state.cheats_open; cheats.load/change/activate | Optional cheat menus explicitly excluded by the user. Existing recovery controls are preserved. |
| Save, needs, action, wants, aspirations, funds | state.save_now/needs/doing/wants/aspiration/funds | Primarily direct commands/readouts. Preserve easy triggers and readable results; don't misclassify them as menu flows. |
| Camera / follow | state.follow_toggle/center_lot/follow_tick | Review separately from menus. First-person must remain available without depending on Simplified menus. Current Shift+Tab world guard may conflict. |

## Implementation review gates

- Compare every state mode and every keyboard entry against the table above.
- Record backend changes separately from navigation changes.
- Test default on, explicit off, reload, and switching while a menu is open.
- Exercise keyboard-only travel alone and with a companion through actual arrival.
- Test long/virtualized lists, multi-column pickers, multi-select, disabled rows,
  quantity controls, nested menus, cancel and rapid input at screen transitions.
- Test load, settings, interactions, inventories, shopping, careers and event
  planner where available. Assert CAS/Stories are excluded from routing.
- Do not label untested flows passed, or label incomplete coverage universal.

## Candidate evidence, September 26 at 01:37 EDT

Latest verification is recorded in TEST-V14X-SIMPLIFIED.md. As of 04:45,
candidate 5 script and candidate 4 UI pass 1,117 stable automated checks
across 66 suites and all 25 UI movie fidelity checks. Live checks passed:
solo and companion travel through arrival; phone purchase handoff; purchase
quantities, totals and single charge; inventory book actions through reading;
career navigation/selection/cancel; event roles, minimum guests, nested venues
and actual event start; Options categories and value labels; move confirmation
furnishing/funds/cancel; household transfer preview, amount editing and cancel.
Earlier tests covered native load, household switching and first-person.
Transfer used Manage Households, not the phone Split Household entry, and
was canceled before Done. Pointer setup was used in some native flows; these
are targeted acceptance checks, not a claim of every pack-specific action
or an entirely keyboard-only run. Initial table findings below/above are
historical review requirements; this paragraph and the test log give closure.

The setting and shared navigation foundation was installed for testing at 01:42.
Default is on; explicit off is preserved. Up/Down and Tab use logical list
indices, including virtualized rows. CAS and Stories are excluded. Setting
changes retire queued navigation before the new mode receives input.

The startup bridge carries the preference before a save is loaded and updates
it after changes made in a loaded game. Idle and busy connections are both
checked. It remains an outbound-only UI connection. If the alternate port is
unavailable, startup retains speech and keyboard access with simplified menus
temporarily on; the loaded game receives the actual preference normally.

The stable source run passed 1,045 checks across 62 isolated suites, including
17 new Flash checks and 20 new Python checks. This verifies foundation behavior,
not completion of the individual gameplay flows. The script snapshot is
`build/v14x-simplified-foundation`; the matching UI snapshot is
`build/v14x-simplified-ui-candidate`. This is a test pair, not a staged release.

Foundation live checks on the existing ScreenReader v14v Launch Test save:
- One Down press per settings row, with spoken positions, passed. Enter switched
  Simplified menus off; a pointer click restored on. No game save was written.
- First-person entered/exited and scanner navigation worked, but a residual Tab
  also opened HUD browsing. A camera transition fence and poller modifier fix
  are pending verification in the second candidate.
- Load Game exposed scrollbar/name controls before Play, and Options treated
  the category bar as one item. Both are fixed in second-candidate source and
  require live verification. These foundation findings are not acceptance passes.

Claude owns the independent review of dialogs/travel/events/careers/appearance
and Python adapters. Codex owns this inventory, Flash, and final game checks.
