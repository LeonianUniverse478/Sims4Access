> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# V9 implementation and limits

**September 15 update:** V9.6 is the current installed build. Consolidated
results and remaining checks are in [TEST-V9-6.md](TEST-V9-6.md).
The V9 implementation history below predates the live-test corrections.

V9 is installed (September 15, 2026). All three installed hashes match staging and the cfg was preserved. Evidence: `build/v9-verification.json`, `build/v9-deployment.json`, `flash/chain-keyboard-v9-final.log`, `flash/gate-compat-v9.log`. Seven offline suites passed 130 checks; the main/compatibility gates passed 61/19 comparisons. No V9 in-game pass is claimed.

## Fixes from the V8 test round

- Scanner: known BuyCat function tags classify definitions when Live Mode returns zero native category flags. Native nonzero categories still take precedence. The simulation-thread real-time alarm refreshes every two seconds after first use; selection is preserved by object id without narration. Sims include instantiated neighborhood Sims rather than only those on the active lot. The 40-metre interactive-object filter is unchanged.
- Ownership: selected HUD buttons determine open HUD panels; persistent HUD movies are excluded from the generic modal candidate list. Entering a real panel clears explicit whole-HUD browsing and stale status scopes. Python clears its old pie-menu routing flag when Flash reports world ownership.
- Native input: a high-priority InputDelegate listener consumes guarded processed InputEvents before FocusHandler while our walker owns those keys. Raw key-down/up pairs still reach InputDelegate, preserving its keyHash bookkeeping. The listener performs no navigation or activation; the existing Python path remains the sole driver. Camera capture retains native InputActions and their lease. Text-editing keys pass through. This is a mitigation for the reported sell-confirmation error, not proof of attribution or resolution.
- Semantic targets: need descendants map to the whole CommodityContainer and activate the native solve button. Inventory artwork maps to its cell, with the stack button separate. Synthetic keyboard hover bypasses generic mouse label collection, preventing “Cell View” from interrupting item tooltips. Settled focus can force the native tooltip extension to show its ready data.
- Focus departure/removal clears visual tooltips and dispatches roll-out, including when changing or closing a scope.
- FilterComponent's popup participates in ownership independently of DropdownExtension. The field and arrow share a target; Escape closes its popup and restores the field. HolidaySettings is also checked explicitly as a visible overlay. Stay Over's picker/list wrappers and career wrapper cells are traversed to their contents.
- Initial focus skips Close when another target exists; the button remains reachable. Event wizard's top progress grid is excluded. Phone boundaries use its native paging feed, without wrapping past the final page.
- Calendar header fields share speech and a union outline. Busy names use the focused/hovered CalendarDayView's work-shift IDs and EA's GENERIC_SIM_NAME formatter. Empty/unavailable names suppress only the Busy section.
- Career/task/objective cells are separate targets. Visible completed check marks add “Completed”; the aspiration unchecked/default frames are excluded. This new state word is currently English.
- Mood label entry is detected on mouse movement as well as entering the entire container, because moving from its background into its non-interactive text does not produce a new ROLL_OVER. The long mood tooltip's V8 suppression remains.

## Evidence and scope

The player log, BE HTML report, V8 sources, installed V8 files and cfg are preserved in `build/source-before-v9/`. The report names CLIK UIComponent/FocusHandler/InputDelegate in a null-reference stack. UIComponent.handleInput is empty in the exported EA Gamedata, EA Scaleform and UI Cheats Olympus copies, so the report alone cannot identify which runtime class copy or other mod contributed to it. No broad shared-framework replacement was added.

Use canonical sources, not `tools/edit_feedback_v9.py`, for later edits. That helper is a one-shot migration and does not contain the subsequent review fixes.

Shipping remains **24 main movies plus six UI Cheats compatibility movies**. No EngagementLibrary/CAS expansion and no release-sibling changes. The V7 startup probe remains separate and must be rebased before testing with this UI build.

Offline behavior tests cover scanner refresh, range changes, category fallbacks, stable silent selection, stale pie-owner release, existing keyboard routing, speech and settings. Compilation, pcode gates and archive/package verification are necessary but cannot prove game timing, focus or tooltip behavior. TEST-V9.md covers the required in-game retest; calls/texts remain untested.
