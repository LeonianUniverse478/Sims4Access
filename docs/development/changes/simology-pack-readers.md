# Simology pack readers: milestones and character values (2026-10-04)

Leo asked to make the DLC features in his packs accessible. Two Simology parts that EA draws only as icon grids now have native pickers. Both are rows in the accessibility menu, after Events, and they appear only when the pack is installed (`sims4.common.is_available_pack`).

## Behavior

Shortcuts (added the same day at Leo's request): Ctrl+Alt+M opens Milestones and Ctrl+Alt+K opens Character values, without going through the menu. Like the action queue and events, they refuse over a dialog ("Close the current menu or dialog first.") and are ignored while typing. Without the pack they say so ("Milestones need the Growing Together expansion pack."). M and K are not AltGr letters on the Polish layout.

**Milestones (Growing Together, EP13).** The first window lists the active Sim's milestone categories, each with "N of M reached". Enter on a category lists its milestones in EA's order. Each milestone gives its name, then one of:
- "Reached as a toddler." (or "Reached 3 times." for repeatable milestones), followed by EA's unlocked text
- "Not reached yet, in progress.", followed by EA's hint
- "Not reached yet.", followed by EA's hint

**Character values (Parenthood, GP05).** For the active Sim, each value gives its name, its value on the tuned scale ("62 on a scale from -100 to 100."), the trait its current range gives at age up ("At this level, as a young adult the Sim gets: Considerate") when the range has one, and EA's description.

Both windows only read. Enter on a row reopens the list, and Escape closes it. A Sim with nothing to show gets a spoken message instead of an empty window.

## Source of truth (game 1.128.90 decompile)

Milestones:
- The data is `sim_info.developmental_milestone_tracker`: `_active_milestones_data` and `_archived_milestones_data`, which map milestone tuning to data with `state`, `age_completed` and `previous_goals`.
- Visibility copies `send_all_milestones_update_to_client`: active entries pass `is_milestone_visible(milestone, SingleSimResolver(sim_info))`, and archived entries are always shown.
- States are `DevelopmentalMilestoneStates` LOCKED, ACTIVE and UNLOCKED.
- The repeat count is 1 for the current unlock plus `len(previous_goals)`, the same entries the panel sends.
- Text comes from the milestone tuning: `name`, `unlocked_text_no_context` (no tokens, so the server can send it as is), `is_primary_milestone.hint_text`, `category` and `ui_sort_order`.
- Category names are `DevelopmentalMilestone.DEVELOPMENTAL_MILESTONE_CATEGORIES[category].name`.
- The client builds the tokenized `unlocked_text` (with the Sim, object or lot) itself; the reader does not use it.

Character values:
- They are the `statistics.life_skill_statistic.LifeSkillStatistic` instances in `sim_info.commodity_tracker`. `SimInfo.apply_career_changes` reads them the same way.
- Display data comes from `get_display_mixin(has_description=True, has_icon=True, has_tooltip=True, use_string_tokens=False)`, so `display_name` and `display_description` are plain LocalizedStrings. The description falls back to `display_tooltip`.
- The scale is `min_value_tuning` to `max_value_tuning`.
- The trait comes from `trait_on_age_up_list`, the entry whose `life_skill_range` holds the value, through `age_up_info.life_skill_trait.display_name(sim_info)` and `age_to_apply_trait`.

## Not covered yet

- EA's large Lifetime Milestones panel (`show_lifetime_milestones_panel`) stays as it was; the menu row replaces it for reading.
- Who or what a milestone was unlocked with (the tokenized `unlocked_text`) is not read.
- Character values are listed for the active Sim only.

## Files

- New: Scripts/tyjokr_a11y_simology.py and tools/test_simology.py (9 tests).
- Changed: Scripts/tyjokr_a11y_keys.py (M and K chords, `_open_simology`), Scripts/tyjokr_a11y_shortcuts.py (labels), tools/test_scanner_v5.py (pinned chord list adds M and K), Scripts/tyjokr_a11y_hub.py (the two pack rows), Scripts/tyjokr_a11y_lang.py (English and Polish terms) and CONTROLS.txt.

## Evidence

Python only; the UI package is unchanged.
