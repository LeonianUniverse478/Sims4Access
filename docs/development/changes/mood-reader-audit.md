# Mood reader audit

- Route: `Scripts/tyjokr_a11y_hub.py` sends `A11yMood`; `flash/TooltipManager_patched.as:A11yMood` locates the live SimHub and calls `mcMoodContainer.A11yReadMood`. `Scripts/tyjokr_a11y_narrator.py:a11y_mood_enc` speaks the result. This is a UI-backed reader, not solely a Python mood lookup.
- The current native `SimHubMain` still exposes `mcMoodContainer`. The full current UI ownership inventory identifies SimHub as the only definer of MoodContainer. Message/channel registrations exist.
- The existing log contains an earlier generic unavailable reply, but no branch/error detail. The UI handler catches errors silently and sends the same empty record for a missing/hidden HUD or reader failure. The cause of the reported current failure is not established; no runtime mood fix is included.
- Next reproduction: compare Ctrl+Alt+E from the settled Live Mode world with the accessibility-menu action. If it persists, log HUD presence/visibility, reader-method availability and the caught error at the UI boundary. Avoid replacing client-localized strings with guessed Python text.
- Native MoodContainer plays a sting on mood changes. Current narration is request/hover-driven; it does not subscribe to that audio call as a general buff announcer. Ordinary notifications follow a separate route. A cue timestamp and matching native state event are needed before attributing a particular sound to a missing message. The Plus notification-history setting is not evidence that moodlet-change announcements exist.

Audit only. No mood, notification or player-setting behavior changed.
