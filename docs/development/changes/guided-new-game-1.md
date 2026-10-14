# Guided New Game, version 1: framework and name step (2026-10-13)

Research and the full design are in guided-new-game-research.md. tyjokr approved the work on 2026-10-13. Leo asked for every step from New Game onward to be a pop-up dialog: choose, OK, next. No tabbing around EA's screens.

## Behavior (this version)

- When a new family's Create a Sim is ready, the guide opens a welcome dialog: "Create your Sim", with Start or "Skip the guide and use the full Create a Sim screen". Escape skips it too.
  - "Ready" means CASNameField is live, the questionnaire prompt is gone and the questionnaire is not running (GetInCasStoryMode), CasIsNewFamily is true, no other dialog is up, and CAS has been settled for one second.
- **Start** opens "Step 1: Name": a dialog with First name and Last name text boxes, filled with the Sim's current name, plus OK, Random name and Back.
  - **OK** applies the name through EA's `CASSetSimName({firstName, lastName, pronouns, validate: true})`, keeping the Sim's pronouns from CASGetSimInfo, then sends CASNameFieldChanged.
  - **Missing or refused names:** a missing first or last name, or a name the game refuses (its validation, including profanity), says so and reopens the name step with what was typed.
  - **Random name** fills the first name from `GetRandomFirstName({isFemale, species})`. It also fills the last name from GetRandomLastName when that box is empty.
  - **Back** returns to the welcome dialog.
- After the name is set, the guide says the later steps come in the next versions, and leaves the player in Create a Sim.
- The guide is offered once per Create a Sim visit, and only for a new family. Marks "guide-offered", "guide-skip-not-new-family" and "guide-error-..." go to the log.

## How it is built

- Everything runs in TooltipManager_patched.as (`A11yGuideFrame`, `A11yGuideDialog`, `A11yGuideAnswer` and the step functions), called from `A11yModalFrame` on each frame. That copy of TooltipManager already runs in CAS.
- **Dialogs:** EA's own, built as CASNameField's CustomPronounsDialog builds its dialog:
  - a `widgets.Dialog.data.LocalRequestData` with title, prompt and dialog_id
  - `CallbackDialogAction` buttons and a cancellationAction
  - `TextDialogInput(UiDialogTextInputMessage)` text boxes with LocKey.UntranslatedString labels and values
  - a `DialogContainer` with a TitleBodyHeader or VariableInputHeader and a DialogButtonFooter
  - all shown through `DialogManager.RequestDialog(new DialogRequest(...))`
- Classes are found with getDefinitionByName. A dialog serial makes stale answers harmless.
- **No CAS movie is rebuilt:** not CASCustomizer, and not any other CAS movie. The look editors are untouched.
- The text is English only for now. CAS runs before the Python language table is in reach, so translation comes with a later version.

## Files

- Changed: flash/TooltipManager_patched.as and CONTROLS.txt.
- New: tools/test_guided_new_game.js (9 checks).
- Test fixtures: test_build_catalog_escape.js and test_phone_owner.js stub the new `A11yGuideFrame`, which A11yModalFrame now calls; the guide has its own suite. Runtime was not changed for them.

## Live test needed (first ever CAS run with the guide)

1. Start a New Game. Answer or decline the questionnaire.
2. Listen for "Create your Sim". Choose Start.
3. Type a first and last name, then OK.
4. Confirm the CAS name label shows it.
5. Try Random name.
6. Try Skip.

The log marks show whether the guide was offered. If CAS crashes or freezes, that is the evidence the next version needs.

## Version 2, after the first live run (2026-10-13)

**Live, version 1 (Leo, game 1.128.90.1030, New Game, questionnaire declined):** no crash, and the welcome dialog was offered ("guide-offered").
- Skip and Start were both reachable and read.
- The name dialog opened and read its title and prompt. Focus then went straight into a text box: modal state 10 to 11 repeatedly, with nothing spoken. Only Back was ever reached. OK and Random name never came up.
- So EA's TextDialogInput boxes inside our DialogContainer are not usable with TS4 Access's keyboard yet.

**Change:** guide dialogs now hold buttons only, and typing happens in CAS's own name editor, which TS4 Access already reads and drives (TEST-V11: First Name, Tab, Last Name). From the CASNameField movie:
- `CASNameFieldMain` listens for `CASNameFieldSetEditMode {bEditMode}` and `CASRandomizeSimName {overrideCurrent}`.
- In the editor (NameInputControls.OnKeyPress), Enter writes the name through and closes it, and Escape reverts and closes it.
- While editing, the name button (`btnTextEffect`) is hidden.

**Step 1: Name now offers four buttons:**
- **Type the name** sends CASNameFieldSetEditMode and says "Name boxes open. Type the first name, press Tab, type the last name, then press Enter. Escape cancels." The guide continues when btnTextEffect shows again. If the editor never opens within 3 seconds, it says "Name boxes did not open" and goes back.
- **Random name** sends CASRandomizeSimName (the dice buttons).
- **Keep this name.**
- **Back.**

The result dialog then reads the name back from CASGetSimInfo, with Next or Change the name.

## Version 3: age, gender, traits, aspiration (2026-10-13)

Leo confirmed version 2 live: the buttons-only name step works. Version 3 adds the next steps with the same buttons-only dialogs, each applied through the CAS service EA's own panel calls:
- **Step 2: Age.** GetAgesData for the Sim's species, youngest first, babies left out. The current age is marked "(now)". SetSimAge, then RefreshSimAgeGender so the CAS panels update.
- **Step 3: Gender.** Female and Male, labelled with GetGenderStringKey. SetSimGender with no argument toggles (as CASAgeGenderPane does), so it is only called when the choice differs.
- **Step 4: Traits.** The prompt reads the chosen traits and the limit (CASGetSimInfo maxTraits). Add a trait (only under the limit) lists GetTraitGroups, then that group's GetAllSimTraitsInfo, leaving out chosen traits and any that clash (conflictingTraitIds). AddTraitToSim and RemoveTraitFromSim apply them.
- **Step 5: Aspiration.** CasGetAspirationCategories in ui_sort_order, then CasGetAspirationTracksByCategory, skipping hidden unlockables (AspirationTrackStaticData). SetSimAspiration {uid}.
- **Your Sim.** A summary with Done, Change the name, Change age or gender, Change traits, Change aspiration, Back.
- Every list has Back, and Escape in a list goes back one step.

Tests: tools/test_guided_new_game.js (12 checks, vm fixture, not in-game verification).

### Version 3.1: traits fix (2026-10-13)

**Live, version 3 (Leo):** name, age, gender and aspiration all applied, but no traits were chosen.

**Change, matching EA's EquippedTraitsAsp (CASMolecule):**
- The traits step now calls CasPersonalityTraitsUIOpened when it opens and CasPersonalityTraitsUIDone when it is left (Next, Back, Escape or the end of the guide), as EA's panel does around AddTraitToSim and RemoveTraitFromSim.
- Chosen traits are read from CasGetEquippedTraits, as EquippedTraitsAsp.SetSimInfo does, not only from the `equipped` flag in GetAllSimTraitsInfo.
- Only personality traits are offered (type "0", SimTraitsInfo.TRAIT_PERSONALITY), as the panel shows.
- Marks for the next live run: guide-trait-add-<id>-now-<count>, guide-trait-remove-<id>-now-<count> and guide-traits-done-<count>.

## Version 4: finding a home (2026-10-13)

**Live, version 3.1 (Leo):** name, age, gender, traits and aspiration all applied.

Version 4 continues from Your Sim, Done, through EA's own code at each step (decompiled read-only: CASNavigation, CASHouseholdSummary, GameEntryWorldSelection, GameEntryLibrary and GameEntryMovePanel):
- **Your Sim is ready:** Find a home, Change how my Sim looks first (closes the guide), Back.
- **Checks before leaving CAS, as CASNavigationMain.EnterGame does:**
  - at least one young adult, adult or elder;
  - CASCheckProfanityOnSimNames;
  - the CAS hide messages;
  - CasApplyNameFields (CallUIService);
  - CasGetHouseholdExchangeData.
- **Your household:** reads the household name. Save and find a home does what CASHouseholdSummaryMain's Done does: CasSaveHouseholdToTray, wait for ExchangeItemSaved (15 seconds at most), EnterGame {name}, then ShowTransitionScreen mode 31 (CAS_TO_NHD_MAP).
- **Choose a season** (Seasons only): the season screen's own buttons, through A11ySeasonActivate.
- **Choose a world:** NeighborhoodStateData.AllNeighborhoodData, one entry per player-facing world, no vacation worlds. Each entry says how many empty homes the household can afford. Choosing sends TransitionToNeighborhoodMap {NeighborhoodData}, which GEWorldSelectionMain listens for.
- **Choose a home:** after NhdMapLoaded (or 20 seconds), the world's lots of type VACANT_LOT (not apartments), cheapest first. Each says bedrooms, bathrooms, price and whether it is too expensive. Back sends OpenWorldSelection.
- **Furnished or Unfurnished:** prices as MoveInPanel computes them (TotalPrice, UnfurnishedPrice, LotPrice), each with the money left. Unaffordable choices are refused.
- **Buying:** ConfirmModeOp {lotData}, as the map's Confirm sends, runs EA's NeighborhoodMap.OnConfirmModeOp and opens MoveInPanel. The guide sets ddInOptions through DropdownExt.SetSelectedFromMenuItemData and an ITEM_SELECTED DropdownEvent, as the dropdown list does, then presses btnOkay. If Purchase is disabled, the guide closes the panel and says so.
- **Play:** NeighborhoodMap plays a new family's lot after the move-in animation. If the map is still up 25 seconds later, a Play button calls PlayHousehold {householdId, zoneInstanceId}.
- Marks for the next live run: guide-home-save, guide-home-enter-saved or guide-home-enter-unsaved, guide-home-world-<region>, guide-home-lot-<zone>-mode-<n>, guide-home-purchase, guide-home-play, guide-home-playing and guide-home-timeout.

Tests: tools/test_guided_new_game.js (15 checks, vm fixture, not in-game verification).

### Version 4.1: listener fix (2026-10-13)

**Live, version 4 (Leo):** Save and find a home did nothing. The log has guide-home-save, then guide-error-Error #1034: Type Coercion failed: cannot convert TooltipManager to DisplayObject. CommunicationManager.AddMessageListener takes a DisplayObject owner, and TooltipManager is not one. The error came before CasSaveHouseholdToTray, so nothing was saved.

**Change:**
- ExchangeItemSaved and NhdMapLoaded now use AddMessageListenerByName and RemoveMessageListenerByName with the owner "A11yGuide", as the rest of TooltipManager does.
- Any guide error now says "The guide ran into a problem and closed" (A11yGuideFailed) instead of stopping silently.
- Likes and dislikes are not needed to leave CAS: EA's Play path (CASNavigationMain.EnterGame) checks only adults, names and the household data.

## Version 5: household and furnished houses (2026-10-13)

**Live, version 4.1 (Leo):** the whole flow worked, from New Game to playing the lot. Every home in Newcrest was listed as an empty lot, so Furnished never showed.

**Homes:**
- Each lot is refreshed once from GetNeighborhoodLotData into the cached NeighborhoodLotData (UpdateZoneData), so house and furniture prices are current. The same object goes to ConfirmModeOp, so MoveInPanel offers Furnished too.
- Houses come first, cheapest first. Empty lots come last, labelled "Empty lot with no house, you build it yourself".
- Worlds now say "N houses you can afford, M empty lots".

**Household (EA's CASSimSelectorMain, AddSimMenu and RelationshipsPane, plus CASSimRelationsData):**
- **Your Sim is ready** now offers Find a home, Add another Sim, Set relationships, Change another Sim (the last two once there are two Sims), and Change how my Sims look first.
- **Add another Sim:** CasAddSim {relSimId "0", relationship SimRelationship.NONE (6), species 1, occultType 1, action 1}, as AddSimMenu.ActionAddSim does for a human. The guide waits up to 5 seconds for CAS to switch to the new Sim, then runs the same steps. After their summary's Done, the relationships step opens.
- **Relationships:** CasGetHouseholdRelationsForCurrentSim lists the other Sims, with relOptions labelled by SimRelationship.GetRelationshipName. Choosing calls CasAddRelationship {simIdA, simIdB, relType}, then clears every trope type with CasSetTropeToRelationshipWith, as RelationshipsPane does.
- **Change another Sim:** CasSelectSim(simIndex), then that Sim's summary.
- Other Sims are named from the names the guide has seen (by Sim ID), or "Sim N" otherwise.
- The adult check counts every Sim in the household.
- Marks: guide-sim-added and guide-relation-<type>.

Tests: tools/test_guided_new_game.js (19 checks, vm fixture, not in-game verification).

## Version 6: optional voice and walk style (2026-10-14)

**Live, version 5 (Leo):** household, relationships and the whole flow worked.

Your Sim's summary gains **Voice and walk style (optional)**. Done never requires it. It follows EA's AgeGenderPane:
- **Voice:** GetVoicesDataForAgeSpecies {species, age}, named by each voice's tooltip. SetSimVoiceActor takes the 0-based button index, and the current voice is SimInfo.voiceActor (1-based). The list stays open to try others.
- **Voice pitch:** five steps, Lowest to Highest, across the current voice's minPitch..maxPitch. SetSimVoicePitch {value, slider_mouse_up: true}, as a finished slider drag sends. The nearest step to SimInfo.voicePitch is marked "(now)".
- **Walk style:** CasGetWalkCycleTraits {simId} and CasSetWalkCycleTrait {traitID}. Babies, infants, toddlers and children have none, as RefreshWalkStyleData shows.
- To check live: whether choosing a voice or pitch plays a sample, as clicking does.

Tests: tools/test_guided_new_game.js (21 checks).
