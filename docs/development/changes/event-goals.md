# Browse event goals with V

Press V in Live mode to move keyboard focus to the current event's goals, for
example the main goal of a date and its individual tasks. Up and Down browse
the visible goals. Escape leaves them. Ctrl+Alt+V still opens event management.
Plain V takes over the game's video-recording shortcut while this reader is
available. Text input, dialogs and Build mode retain their existing keys.

The reader uses the game's SituationDisplay widget. It opens the selected
content panel in the common or live events tab and collects the visible major
goal, ordinary goal icons, and goal rows used by holidays and scenarios.
Keyboard focus uses the same status scope as the other Live HUD readers.
If the game supplies no goals, the reader announces that and releases focus.

The Node fixture exercises the actual shortcut guard and goal traversal.
The shortcut-help test checks that V appears in the ordinary shortcuts.
The narrator regression still checks the original activation messages and
allows additional translated tokens. Live checks include a date with goals,
an event without goals, text entry, and returning to the scanner with Escape.
