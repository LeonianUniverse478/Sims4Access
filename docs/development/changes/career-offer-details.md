# Job title, starting level and hours in Find a Job

When focus moves to a career in the game's selector, the screen reader now announces the position this Sim is being offered, its starting level and its work schedule before the existing career description. The player can compare offers without selecting them. Offers with multiple shifts announce the days and hours of each entry. Agency careers and offers without scheduled shifts keep their title and level.

The existing widget/focus path resolves the focused `TrackBlock` to its `CareerInfo`, including after the list scrolls. `GetCurrentLevelName` uses the Sim token, as in EA's `HiringInfoPanel.SetData`. The join offer supplies a zero-based index within a career track. When the player-facing level is absent, the reader adds the levels of its parent tracks, following the same numbering as EA's `Career._propagate_track_and_level_data`. A track which cannot be resolved keeps its title without a guessed level.

The schedule comes from the offer's own `work_schedule.schedule_entries`. The reader pairs the weekdays of each entry with its hours, including overnight shifts and fractional hours. Full weekday names, time ranges, multi-day shifts and 24-hour durations use the game's localisation keys. Reading the list does not open the shift menu or accept a job.

The PR author, Ar-Anaviel, tested the expanded Find a Job offer readout in her game and confirmed that it works in her personalised installation. The career readout implementation in this contribution is the same as the one used in that installation.

Automated source-method tests in `tools/test_event_activation_v13.js` cover a focused child, recycled rows, nested branches, a higher starting rank, incomplete career data, separate shifts, nights, multi-day shifts and full-day work. These fixtures supplement the author's in-game confirmation; they do not establish separate live coverage of every pack-specific career or unusual schedule. The complete `Dev.ps1 build` pipeline checks regression suites, compilation, main and compatibility fidelity, and the packaged resources before publication.
