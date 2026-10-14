# TS4 Access: test builds

TS4 Access is a screen-reader mod for The Sims 4 by **tyjokr**. It reads menus,
dialogs, tooltips and notifications aloud through your screen reader, and its
scanner finds Sims and objects and opens their interactions without the mouse.

This repository publishes **test builds** of TS4 Access with work by
LeonianUniverse (Leo), shared with tyjokr's agreement. Each change is sent back
to tyjokr to merge into the official mod. TS4 Access Plus features are by
Michael Maslo.

Built and tested against **The Sims 4 1.128.90.1030**, on Windows.

The standalone mod that used to live here, Sims 4 Access (the a11yscan scanner
mod), is kept unchanged on the
[`sims4access-standalone`](https://github.com/LeonianUniverse478/Sims4Access/tree/sims4access-standalone)
branch.

---

## Install or update (the easy way)

1. Download **TS4AccessUpdater.exe** from the
   [latest release](https://github.com/LeonianUniverse478/Sims4Access/releases/latest).
2. Close The Sims 4.
3. Open TS4AccessUpdater.exe and press Enter.
4. When it says the build is installed, press Enter and start the game.

The updater downloads the newest build, checks it against its published
checksum, backs up your current TS4 Access files, installs the mod and the
speech pack, and turns on Script Mods. Keep it, and run it again whenever there
is a new build. Its keys and details are in [docs/UPDATER.txt](docs/UPDATER.txt).

## Install by hand

Download **TS4_Access_Update.zip** from the latest release, then:

1. Close The Sims 4.
2. Copy the `TS4_Access` and `TS4_Access_SpeechPack` folders from the zip's
   `Mods` folder into `Documents\Electronic Arts\The Sims 4\Mods`, replacing
   older copies. Keep only one copy of TS4 Access in your Mods folder.
3. Open `TS4AccessHelper\TS4AccessHelper.exe` from the zip and press Enter to
   turn on Script Mods.
4. Start your screen reader, then the game.

## Documentation

- [docs/README.txt](docs/README.txt): getting started, speech, settings.
- [docs/CONTROLS.txt](docs/CONTROLS.txt): every keyboard shortcut, by activity.
- [docs/CHEATS.txt](docs/CHEATS.txt): optional settings and help commands.
- [docs/GUIDED-NEW-GAME.md](docs/GUIDED-NEW-GAME.md): the step-by-step new game guide.
- [docs/UPDATER.txt](docs/UPDATER.txt): the updater.
- [CHANGELOG.md](CHANGELOG.md): what changed in each build.

## Highlights of these builds

- **Guided new game.** From New Game to playing on your own lot with nothing
  but buttons: name, age, gender, traits, aspiration, optional voice and walk
  style, more Sims and their relationships, a world, a home, and furnishing.
- **Readers:** the whole mood panel (Ctrl+Alt+E), funds with the clock
  (Ctrl+Alt+C), the action queue (Ctrl+Alt+Q), events (Ctrl+Alt+V), and
  Milestones and Character values for Growing Together and Parenthood.
- **Build mode:** the catalog as a tree by room or function with search
  (Ctrl+Alt+O and Ctrl+Alt+D), a tile-by-tile Build cursor, Tab straight into the catalog,
  and Escape out of it.
- **Inventory selling**, a Brief verbosity setting, a logging toggle
  (Ctrl+Alt+L), labelled household transfers and moves, businesses (including
  mod businesses), and keyboard hiring.
- **TS4 Access Plus** by Michael Maslo: Alt-key readouts and reminders, Sim
  creation without Create a Sim, and a Build helper.

See the [changelog](CHANGELOG.md) for the full list.

## Contributing

The full source is on the
[`dev` branch](https://github.com/LeonianUniverse478/Sims4Access/tree/dev),
under the MIT licence. Work from there and send pull requests **into dev**; its
[CONTRIBUTING.md](https://github.com/LeonianUniverse478/Sims4Access/blob/dev/CONTRIBUTING.md)
explains setup and how changes are reviewed. Accepted contributions are
credited in the changelog and in
[CONTRIBUTORS.md](https://github.com/LeonianUniverse478/Sims4Access/blob/dev/CONTRIBUTORS.md).

## Reporting a problem

Turn on logging with Ctrl+Alt+L, reproduce the problem, then send
`TS4_Access.log` from your Mods folder. Say what you pressed and what you heard.

## Credits

- **TS4 Access** by tyjokr.
- **TS4 Access Plus** by Michael Maslo.
- **Test-build changes** by LeonianUniverse.
- **Speech** through [Prism](https://github.com/ethindp/prism) by Ethin Probst,
  MPL-2.0, unmodified; its licences ship in `TS4_Access_SpeechPack`.
