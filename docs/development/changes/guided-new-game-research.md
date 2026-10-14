# Guided New Game: research (2026-10-13)

## Why

A first-time Sims player gave up during character creation: the current CAS flow means tabbing around EA's full screen. Leo asked for a guided flow from New Game onward, one pop-up dialog per step with OK and then the next. The order is: questionnaire or not, name, age and gender, traits, aspiration, more Sims, then the lot list, then Play. Nobody should have to tab around EA's screens.

tyjokr agreed (2026-10-13) that the flow must change, and asked Leo to work on it. CAS appearance editing stays as EA has it.

## Constraints from the kit

- **CASCustomizer is never rebuilt.** Any FFDec rebuild of it hard-crashes the client on CAS load (rebuild_all.ps1, TODO-NEXT-SESSION.md, 2026-08-03). The guided flow never needs it.
- **Our TooltipManager runs during CAS.** The live TooltipManager comes from ClassLibraryGamedata, and since v11 it narrates CASStories and CASNameField (TEST-V11.md).
- **Python has no dialogs here.** During the main menu and CAS there is no loaded zone, so Python's UiDialog pickers are unavailable. Startup messages use the startup socket (ARCHITECTURE.md).

## Findings (EA movies, game 1.128.90, decompiled read-only)

### A dialog surface that works during CAS

EA's own Flash dialog system: `CommunicationManager.SendUIMessage("ShowDialog", data)`.
- The CAS movies call it 144 times, so it works there.
- Simple form: `{title, description, optionOneText, optionTwoText, optionThreeText, closeText}`.
- Full form: `widgets.Dialog.data.LocalRequestData`, with `title`, `promptText`, `inputs` (`Vector.<IDialogInput>`), `actions` (`Vector.<IDialogAction>`), `cancellationAction`, `dialogType`, `dialogStyle` and `options`.
- Input cell views in the Dialog movie:
  - TextInputCellView
  - DropdownInputCellView
  - VariableInputCellView
  - InlineTextInputCellView
- Actions:
  - `CallbackDialogAction(fn, ...)`, which calls back into our code
  - ServerDialogAction
  - MessageDialogAction
- **Template:** CASNameField's own `widgets.Dialog.dialogs.CustomPronounsDialog` builds a LocalRequestData with five TextInputCellViews and a CallbackDialogAction cancel, inside CAS.

### CAS game services for every step

Called by the CAS movies through `CommunicationManager.CallGameService`:
- **Questionnaire:** `CasGetCasStoriesQuestion`, `CasCasStoriesQuestionResult`, `CASStoriesGetSummaryData`, `CasExitCASStory` and `GetInCasStoryMode`.
- **Name:** `GetSimNameInfo`, `CASSetSimName`, `CASCheckProfanityOnSimNames`, `GetRandomFirstName` and `GetRandomLastName`.
- **Age, gender, appearance:**
  - `GetAgesData`, `GetSimAge`, `SetSimAge`, `GetSimGender`, `SetSimGender`, `GetGenderStrings`, `CasGetGenderOptionsData` and `AddGenderOptionTraitsToSim`.
  - `RandomizeSim` is used for a ready-made look.
- **Traits:** `GetTraitGroups`, `GetAllSimTraitsInfo`, `GetFilteredSimTraitInfo`, `CasIsTraitValidForGenus`, `CasGetEquippedTraits`, `AddTraitToSim`, `RemoveTraitFromSim`, `CasPersonalityTraitsUIOpened` and `CasPersonalityTraitsUIDone`.
- **Aspiration:** `CasGetAspirationCategories`, `CasGetAspirationTracksByCategory`, `GetAspirationTrackStaticData`, `GetSimPrimaryAspiration`, `SetSimAspiration` and `CasGetFTUEAspirationTracks`.
- **Household:**
  - `CasGetHouseholdSims`, `CasAddSim`, `CasSelectSim`, `CasRemoveSim`, `CasAddRelationship` and `CasGetHouseholdRelationsForCurrentSim`.
  - `CASGetNumSimsInFamily`, `CASGetMaxSimsInFamily` and `CASVerifyFamily`.
- **Leaving CAS:** `SaveAndExitCAS`, `CasGetExitTo` and `CasIsNewFamily`.
- **Lot and play:** `GetNeighborhoodLotData`, `GetHouseholdStarterFunds`, `ApplyHouseholdToNeighborLot`, `PlayHousehold`, and the UI message `ShowGameEntryMovePanel`. The move-in panel is already accessible (A11yMoveInQuote and A11yMoveLabel).

Movies involved in the flow, each separate from CASCustomizer:
- CASStories, CASNameField, CASAgeGenderPane, TraitsMoleculeLibrary, CASMolecule, AspirationSelector, CASSimSelector, CASHouseholdSummary and CASNavigation (in CAS)
- GameEntryWorldSelection and GameEntryMovePanel (lot choice)

## Proposed design

- A sequencer in TooltipManager_patched.as. It already loads in CAS, so no CAS movie needs rebuilding for the flow itself.
- After the questionnaire choice, it shows one EA dialog per step through `ShowDialog` and LocalRequestData:
  1. **Name:** two text inputs and Random.
  2. **Age, then gender.**
  3. **Traits:** trait group first, then traits, up to the age's limit, enforced by EA's own filtered trait data.
  4. **Aspiration:** category, then aspiration.
  5. **Add another Sim?** For a new Sim: relationship, then steps 1 to 4 again.
  6. **Ready.** Change how they look (EA's CASCustomizer, optional) or continue.
  7. **The lot list:** world, then lot with price and funds left, then the existing move-in panel, then Play.
- Every choice is applied through the CAS service above, so EA's own rules stay in charge: trait limits, age restrictions, pack ownership, profanity checks and family validation.
- Each dialog says its step number and has Back and Cancel.

## Risks to settle while building

- **Long lists.** Whether LocalRequestData renders a long action list as one scrolling list. Traits and lots may need group, then item, dialogs.
- **CAS ownership.** That TS4 Access's simplified menus own keys in a ShowDialog dialog during CAS, as they do for other DialogContainer dialogs.
- **Crash safety.** No rebuilt CAS movie should be needed. If the flow needs a hook only a CAS movie defines (such as CASNavigation), that movie must first pass a standalone rebuild-and-load test, the way CASCustomizer failed.
- **Live testing.** One step per build, each confirmed in a short CAS run before the next.
