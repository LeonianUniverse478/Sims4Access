# Scanner: hospital patients by visit stage (2026-10-04)

During his first doctor shift (intern), Leo could not tell which Sims were patients. The Sims category of the scanner now names each patient's role and visit stage after their name: "Mateo Lewis, patient, waiting, 20 meters south east. 5 of 11."

## Source of truth (game 1.128.90)

- Patients are the Sims returned by `get_patient()` of every `situations.complex.patient_situation_base.PatientSituationBase` in the zone situation manager. The hospital patient situations derive from it.
- The stage is the class name of the situation's `_cur_state`, as EA names it: ArrivingState, WaitingState, `_AdmittedState`, `_DiagnosedState` and TreatedState. These are spoken as arriving, waiting, admitted, diagnosed and treated. An unknown state is spoken as "patient".
- The stage is what the player can already know: where the patient is (waiting room or exam bed) and what the player's own Sim has done. It never names the illness.

The roles are read once per scan, like the rest of the scanner list, and then stored on the Sim entry (`Entry.role`).

## Doctor research log, first shift

Leo's intern shift logged every patient situation change with names, for example `hospitalPatientSituation_lowLevel_child` going to WaitingState and `_AdmittedState`. No sickness, symptom or discovery lines were logged: intern-level patients carry no Sickness, so the diagnosis readout must wait until Leo reaches a level whose patients have real illnesses. The pre-diagnosed ambient patients (`hospitalPatientSituation_Diagnosed_*`) start in `_DiagnosedState` and were never examined.

## Files

- Changed: Scripts/tyjokr_a11y_scanner.py (PATIENT_STAGES, `_patient_roles`, `Entry.role`, spoken in `_entry_parts` and `_group_parts`), Scripts/tyjokr_a11y_lang.py (English and Polish) and CONTROLS.txt.
- New: tools/test_patient_roles.py (4 tests).
