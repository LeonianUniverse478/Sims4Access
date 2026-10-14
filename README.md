# TS4 Access: development source (dev branch)

This is the full development source of **TS4 Access**, the screen-reader mod for
The Sims 4 by tyjokr, with the changes made for the test builds. It is the
branch to work on and the branch **pull requests go to**.

- Players: see the [main branch](https://github.com/LeonianUniverse478/Sims4Access)
  and install with the updater from the
  [latest release](https://github.com/LeonianUniverse478/Sims4Access/releases/latest).
- Contributors: read [CONTRIBUTING.md](CONTRIBUTING.md), then START-HERE.md.

Licence: MIT ([LICENSE](LICENSE)). Contributors are credited in
[CONTRIBUTORS.md](CONTRIBUTORS.md) and in the changelog of the build their work
ships in.

## What is here

- `Scripts/`: the mod's Python, which runs inside the game (Python 3.7).
- `flash/`: the interface layer. `TooltipManager_patched.as` and
  `extra-classes/` are compiled into the game's own interface movies.
- `tools/`: the build, its checks and tests (`Dev.ps1 build` runs them all).
- `helper/`: the TS4 Access Helper and Updater (C# and PowerShell).
- `docs/development/`: architecture, build and safety rules, and a note per
  change (`docs/development/changes/`).
- `reference/`: pinned baseline inputs the build checks against.
- `prism/`: the speech pack (Prism, MPL-2.0).
- `README.txt`, `CONTROLS.txt`, `CHEATS.txt`: the player documentation that
  ships with the mod.

The Sims 4's own interface movies and UI Cheats Extension's movies are **not**
in this repository; `Dev.ps1 setup` makes them from your own installs.
