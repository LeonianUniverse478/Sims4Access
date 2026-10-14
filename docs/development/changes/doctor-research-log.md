# Doctor career research log (2026-10-04)

Leo wants the Get to Work doctor career to be playable without sight and without cheating. Before building a patient readout, we need to know which cues a sighted player actually gets. The game's code shows what is tracked (`SicknessTracker`: discovered symptoms, exams, treatments, rule-outs and diagnosis progress), but not how much of it shows on screen.

## Behavior

The new module tyjokr_a11y_careerlog.py only logs. Nothing is spoken and no game behavior changes. While diagnostic logging is on (Ctrl+Alt+L), it writes "doctor:" lines to TS4_Access.log:
- **When a sickness is applied:** the sickness, and each symptom with its buffs' presentation fields (visible, vfx, cas_vfx, appearance_modifier, walkstyle, audio_sting_on_add, voice_pitch_modifier, mood_type, pushed interactions). Also the diagnosis statistic and its visible flag, the discovery order (`get_ordered_symptoms`) and the correct treatments.
- **Doctor progress (SicknessTracker):** discover_symptom, discover_sickness, track_examination, track_treatment, rule_out_treatment and record_last_progress.
- **Cues on a sick Sim:** thought balloons (`BalloonRequest.distribute`), headlines (`Headline.send_headline_message`) and visual effects (`PlayEffect.start` and `start_one_shot`).
- **Patient visit stages:** PatientSituationBase `_change_state` (arriving, waiting, admitted, diagnosed, treated).

Every hook calls EA's original first and logs after it; a logging error is caught and logged. The module is imported at startup from tyjokr_a11y_keys.py, like the phone observer.

The log names hidden answers (the sickness and its correct treatments) on purpose. It is developer research data and must not be turned into narration. The planned patient readout will speak only discovered information and the cues this log shows a sighted player gets.

## Files

- New: Scripts/tyjokr_a11y_careerlog.py and tools/test_careerlog.py (5 tests).
- Changed: Scripts/tyjokr_a11y_keys.py (the startup import).

## Evidence

Python only.
