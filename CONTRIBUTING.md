# Contributing to TS4 Access

Thank you for helping. TS4 Access is played by blind and low-vision players, so
the bar is: it must work with a screen reader and a keyboard, and it must never
risk a player's game or saves.

## How contributions work

1. Fork this repository and branch from **dev**.
2. Make your change, with tests, and a short note in
   `docs/development/changes/` saying what changed, why, the game code it
   relies on, and how you tested it.
3. Run `Dev.ps1 build` until it passes (see below).
4. Open a pull request **into the dev branch** (not main). Say what you tested
   in the game and what you could not test.
5. Leo reviews it, builds it, and tests it in the game. Accepted changes go
   into the next test build and are passed on to tyjokr for the official mod.

## Credit

When your pull request is accepted, you are credited:

- in [CONTRIBUTORS.md](CONTRIBUTORS.md), with your name or handle and what you
  contributed;
- in the changelog entry of the build it ships in, on the main branch;
- in the change note in `docs/development/changes/`.

Tell us in the pull request how you would like to be named. By opening a pull
request you agree that your contribution is published under this repository's
MIT licence.

## Setting up

You need Windows and The Sims 4 **1.128.90.1030** (the version this source is
built against). Full instructions are in START-HERE.md; in short:

1. Install **Python 3.7.9 x64** (with the py launcher) and **Node.js**. The game
   only loads Python 3.7 bytecode.
2. For interface (Flash) work, which the full build needs, also install
   **JDK 21** and the full portable **FFDec 26.2.1**.
3. Copy `dev.local.example.json` to `dev.local.json` and set `TS4_INSTALL` to
   your game installation (the folder with `Data\Client\UI.package`), and
   `TS4_JAVA` and `TS4_FFDEC`. `dev.local.json` stays on your computer.
4. Make the game inputs the repository cannot include:

   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File .\Dev.ps1 setup --uicheats "<path to UI_Cheats_Extension.package>"
   ```

   This extracts the game's interface movies from your own installation, and
   UI Cheats Extension's movies from its package (the build also produces a
   compatibility package for players who use UI Cheats). It needs **UI Cheats
   Extension 1.59.1** by weerbesu. Every file is checked against the pinned
   hashes; a different game or UI Cheats version is reported, not accepted.
5. Check everything: `Dev.ps1 doctor --full`.
6. Build: `Dev.ps1 build`. The test zips appear in `dist\`.

## Rules that keep players safe

Read these before changing code. They are short and they matter:

- `docs/development/ARCHITECTURE.md`: how the Python, Flash and speech parts
  fit together.
- `docs/development/GFX-SAFETY.md`: rules for interface code. Some movies crash
  the game if rebuilt (never rebuild CASCustomizer); use `int` counters with
  `x = x + 1`, never `++` or `--`; wrap every entry point in try/catch.
- `docs/development/BUILD-AND-TEST.md`: the build and its gates.
- Game calls run on the simulation thread, never on the keyboard thread.
- Never commit the game's files, other mods' files, saves, logs or
  `dev.local.json`. `.gitignore` covers the usual ones.
- Do not change behaviour just to make a test pass; explain any test you
  change in your change note.
- Before testing in the game, back up your Mods folder and use a test save.

## Reporting bugs

Open an issue with what you pressed, what you heard, and an excerpt of
`TS4_Access.log` from your Mods folder (turn logging on with Ctrl+Alt+L). Logs
can contain Sim names; trim anything private.
