# Contributing to Sims 4 Access

The mod exists because The Sims 4 has no accessibility tree and its client is
C++, so nothing on screen can be read. Everything here follows from one rule.

## The rule

**Don't read the UI. Rebuild it from the data the UI is drawn from.**

Almost everything the screens show comes from the Python simulation, and that
we can reach. When you want to add a feature, the first question is not "how do
I read that panel" but "where does that panel get its numbers". The panel is a
dead end; the tracker behind it is not.

The corollary: when a screen has nothing behind it — the main menu, the
Gallery, the age-up panel — no amount of cleverness in `src/` will help, and
the answer lives in `companion/` instead.

## The second rule, learned the hard way

**Verify by effect, not by return value.**

Nearly every bug in this project reported success. Placements charged money and
left the object unusable. Situations were "asked to leave" and stayed. A lot
was "moved into" without its deed changing hands. A goal tracker returned
`(goal, None)` and the `None` was read as "not completed", so every event goal
said "not yet" for ever.

If the game offers a way to observe the result, read it back and say what
actually happened. `a11yscan_lots.claim_lot` is the model: make the call, then
ask the save who owns the lot.

## Layout

    src/         the mod itself, loaded by the game as a .ts4script
    tools/       build and setup scripts, ordinary desktop Python 3
    companion/   a separate desktop program for screens with no data behind them
    install/     built output, what a player copies into their Mods folder

Modules are named `a11yscan_*` and commands `a11y2.*`. That is the internal
namespace and predates the name Sims 4 Access; it is left alone deliberately,
since renaming it would also rename the reload marker, the Mods-folder markers
and the log path, all of which are load-bearing.

## Building

    py37\python.exe tools\package.py

The game runs Python 3.7 and loads only `.pyc` from inside a `.ts4script`, so
the build must compile with 3.7 specifically. `package.py` compiles every
`a11yscan_*.py`, zips them with the data tables and installs to the Mods
folder. New builds load themselves; no restart needed.

    python tools\rebuild_tables.py <output dir>

Rebuilds the name tables from the game packages **and the Mods folder**, so mod
content gets real names.

## Things worth knowing before you start

* No `re`, no `struct`, no most of the standard library. The mod ships its own
  `ctypes`. Write to that constraint.
* Never let a diagnostic raise. An exception inside a loot chain aborts the
  rest of it, and the player sees an unrelated feature break.
* Log what you tried and what came back. Every hard bug here was found in
  `a11yscan_log.txt`, usually by comparing what a call claimed with what the
  game reported afterwards.
* If a field could be a property or a method, handle both. That has caught us
  twice.

## Reporting a bug

Send `a11yscan_log.txt` from your Sims 4 folder. It is how nearly every bug
here was found, and a description without it is usually a guess.
