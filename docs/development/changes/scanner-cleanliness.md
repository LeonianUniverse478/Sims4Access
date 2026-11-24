# Scanner cleanliness announcements

- `Scripts/tyjokr_a11y_cleanliness.py`: separate read-only suffix reader, bounded to 64 current state values. Native DirtyState takes precedence over its linked commodity state; dust is a separate suffix. Missing objects/unknown states give no label; failures leave speech/navigation intact and log at most five read errors.
- `Scripts/tyjokr_a11y_scanner.py`, `_entry_parts` around 755 and `_group_parts` around 777: add the suffix only when composing object speech. No changes to scanning, filtering, category membership, refresh, ordering or selection.
- `Scripts/tyjokr_a11y_lang.py`: dirty/dusty vocabulary. CONTROLS.txt: spoken status documentation. `tools/test_cleanliness.py`: native-state cases, live re-read, bounds/errors and both scanner announcement paths.

Native evidence from a complete 138-object snapshot: a dirty toilet had DirtyState 15129/value 15131 and Dirty 15128/value 15133. Clean fixtures had values 15130/15132. A dusty desk had DustLevel_ObjectState 255045/value 255050 while both dirtiness states were clean; clean dust value was 255048. No Clean affordance test or name guessing is used.

Live check: hear the dirty toilet in the scanner; clean it normally, then repeat its announcement and verify the suffix clears. Verify a clean sink remains unlabelled and the dusty desk says dusty. In-game speech/cleaning transition confirmation remains pending.

Rollback: restore the previous script archive, or reverse the patch and remove the cleanliness module.
