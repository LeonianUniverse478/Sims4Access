> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# V9 feedback retest

**September 15 update:** V9.6 is now installed. See
[the consolidated test handoff](TEST-V9-6.md) for confirmed passes,
failures and remaining blockers. The checklist below describes original V9
expectations; it is not a list of completed tests.

Installed September 15, 2026. Your cfg is preserved; V8 rollback files are in `build/deployed-before-v9/`. Verification passed 130 offline checks plus the 61 main and 19 compatibility movie comparisons.

This build addresses [your V8 results](FEEDBACK-V8.md). The checks below are expected behavior, not claimed in-game passes. Incoming calls/texts remain **untested**.

## Test these first

1. **Close and release focus.** Open Needs, Inventory and Career in turn, then close each with Escape. With every panel and pie closed, arrows should move the camera, Escape should open Options, Ctrl+Alt+Up/Down should scan, and Ctrl+Alt+H should open the Accessibility picker. Repeat after opening and closing an interaction pie. Also enter HUD navigation with Tab before opening a panel, then repeat the close test.
2. **Needs.** One outline/stop per whole need. Enter triggers that need's native auto-solve when available. No Solve Icon, buff image or silent child stops. Leaving the panel must remove its tooltip.
3. **Inventory.** Each thumbnail should read its native item tooltip, without “Cell View” interrupting it. Hold an arrow, release and verify the last tooltip matches the outlined item. Check stack opening too.
4. **Sell confirmation.** Select Multiple → select an item → Sell. Cancel the first confirmation and verify the item remains. Check that the BE UI error does not recur and that confirmation choices are reachable. The reported CLIK null-reference error has an input-isolation mitigation; an in-game retest is required to establish whether it resolves that error.

## Scanner

- Categories should include appropriate groups such as Comfort, Surfaces, Electronics and Activities and Skills when those objects are present.
- After first use, results refresh every two seconds on the game's real-time alarm. Move the active Sim or let Sims/objects enter or leave range. The next read/navigation should use the refreshed list without unsolicited speech or losing the selected object when it still exists.
- Scope: non-hidden world objects offering player interactions within **40 metres**, plus instantiated Sims in the loaded neighborhood. Items in inventories, unloaded areas and non-interactive scenery are outside this scanner's scope.
- The visible scanner picker is a snapshot so its rows do not move while selecting. Reopen it to see new rows. A live interaction pie also keeps its current choices stable.

## Calendar and filters

- The season/region, weekday and weather should share one outline and announcement.
- On a day with working Sims, pause for the tooltip. “Busy” should include their localized names. If names cannot be resolved, there should be no empty Busy announcement.
- The filter field and expansion arrow should form one target. Open it: arrows/Tab must stay inside the filter popup. Escape closes just the filters, returning to the field.
- Repeat with Inventory filters and a normal dropdown, such as Rewards Store categories.
- **Plan a Stay Over:** enter the filters and individual invitee cards; select a Sim and reach Done.
- **Add Holiday:** use a future date where adding a holiday is enabled. Focus should enter the holiday editor. Test name input, Tab out, traditions and closing it.
- **Plan an Event:** after selecting a type, focus should go to useful choices rather than the three silent progress buttons.
- Close/Esc buttons remain reachable, but should not be first when other content exists.

## Phone, career and mood

- Phone apps remain first. Right on the last app should advance a page; Left on the first should return a page. At the first/last available page it should stop, not wrap.
- Career/school cards should allow separate stops for job information, requirements and individual/daily tasks. Pause for task/grade tooltips. Check both completed and unfinished objectives: only completed ones should say **Completed**. Test aspirations as well.
- Move the mouse from the portrait or moodlet gaps onto the visible mood label: hear the short mood name. The explanatory mood tooltip stays silent. Moodlets and household funds should retain their confirmed behavior.

## Keep on the blockers list

**Incoming calls/texts remain untested.** When one occurs, verify the recipient announcement, then close other UI and press Ctrl+Alt+P to open that Sim's waiting alert. Do not mark this passed until a real call/text is tested.

Regression checks: purchase quantity/Done behavior, dialog body and choices, Sim Profile, Small Business text input/Tab out, panel scrolling/max height, ordinary mouse narration and keyboard-off mode. Polish/AltGr input remains worth testing; the new completion word currently uses English.

Main-menu speech, CAS and the other items in INTEGRATION-STATUS-V7.md remain incomplete. Do not install the old V7 startup-probe UI over this build.

For a failure, record the approximate time, panel name and keys used. The mod log retains `UI owner:` transitions; preserve a new BE report if one appears.
