# Browse individual moodlets

Ctrl+Alt+E focuses the current mood. Up and Down move between its description and the individual moodlets in the expanded SimHub panel. This lets a player revisit one moodlet's cause or time left without hearing the entire list again. Escape releases focus and collapses the panel if the shortcut expanded it. The accessibility menu's “Mood and moodlets” entry still reads the whole summary in one go.

The focus walker takes the visible BuffCellView rows from the game's BuffDisplay. MoodContainer reads each row's BuffInfo through the same formatter as the continuous summary. This keeps the game's localised descriptions, mood effects, causes and durations. The shared TooltipManager accesses the SimHub-specific classes by name.

The offline fixtures cover focus order, hidden rows, the header description, missing data, reading one moodlet, the continuous summary, speech encoding and Escape. A player confirmed the shortcut and moodlet browsing in a personalised build. The final review changes to speech transport, menu routing and focus restoration were tested offline.
