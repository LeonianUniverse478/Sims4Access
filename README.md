# Sims 4 Access

A screen-reader mod for The Sims 4, built on one idea: **don't try to read the
game's UI — rebuild it from the data the UI is drawn from.** The Sims 4 client
is C++ with no accessibility tree, so nothing on screen can be read. But almost
everything the screens *show* comes from the Python simulation, and that we can
reach.

Built by a blind player (Leo) with Claude, and played daily rather than
demonstrated. Please be blunt about anything that looks wrong.

**Licence:** MIT. **Contributing:** see `CONTRIBUTING.md` — it is short, and
the two rules in it are the whole design.

---

## Install

Put these four files in `Documents/Electronic Arts/The Sims 4/Mods/`:

    Sims4Access.ts4script
    a11yscan_names.bin
    a11yscan_objects.bin
    prism.dll

Script mods must be enabled. The `.bin` files are also inside the `.ts4script`;
the loose copies are a fallback.

Speech goes through [Prism](https://github.com/ethindp/prism) by Ethin
Probst, MPL-2.0, which is not part of this project — see
`install/PRISM-NOTICE.md`. It speaks
through whichever screen reader you already run — NVDA, JAWS, SAPI, OneCore or
UIA on Windows, VoiceOver on macOS, Orca or speech-dispatcher on Linux — at
your own voice and rate. `prism.dll` here is built from source, since Prism
ships no binaries. On a Mac or on Linux, build `libprism.dylib` or
`libprism.so` and put that in Mods instead.

If you are upgrading from the old name, delete `a11yscan_Companion.ts4script` first — the game would otherwise load both copies.

It writes `a11yscan_log.txt` next to the game's own logs. **If you report a
problem, send that file** — it is how nearly every bug here was found.

---

## First time: setting the game up

Script mods have to be switched on before any of this runs, and that switch
lives in the Game Options screen - which is a client screen with nothing behind
it to read. The mod cannot turn itself on from inside the game, so there is a
small tool for it. **Close the game first** (it rewrites its settings file on
exit), then:

```
python tools/setup.py
```

That reports what is right and what is not, and changes nothing. Add `--fix` to
set it, and `--quiet-startup` as well if you would rather the "mods loaded"
popup stopped appearing at every launch. Your old settings are kept as
`Options.ini.a11ybackup`. It also checks the four files are in the Mods folder
under the right names.

---

## The companion: screens the mod cannot reach

The main menu is drawn by the game client. There is no accessibility tree and
no simulation behind it, so there is nothing for the mod to rebuild from - the
one place its whole method does not apply. The companion is a separate program
for those screens.

It is not a screen reader. NVDA already does OCR-and-click, and does it well.
What it does is whole known sequences, verified at each step:

```
python companion/start_game.py
```

It reads the game's window with Windows' own OCR, finds the button by its TEXT
rather than a memorised position, says what it found and where, and clicks only
after you press Enter. `--go` skips the confirmation, `--look` reads the screen
aloud and clicks nothing.

Nothing is installed for this: PowerShell drives the OCR engine that ships with
Windows, speech goes through the same `prism.dll` the mod uses, so it is your
voice at your rate. If it cannot find the game's window it says so before
reading the whole screen, rather than quietly clicking something on your
desktop.

Matching on text is the point. A fixed coordinate breaks the first time a patch
moves a button ten pixels, and breaks silently; the word "Continue" is still
findable after it moves, and when it genuinely is not there this says so.

---

## First time: getting onto a lot

The screens before a lot - the main menu, the world map, the lot picker - are
client screens with nothing behind them to read. The mod does not try to read
them. It goes around them.

**Press Ctrl+Alt+W at any point** and it says which of these you are in and
what to press next. That is the one key to remember.

1. **Main menu.** Ctrl+Alt+O lists your saves; enter picks one. That does not
   open it - the mod cannot open a save - it makes that save the one
   **Continue** opens. Then press Continue, the first button on the menu.
2. **A save is loaded, but you are on the world or lot screen.** Ctrl+Alt+O
   here lists the *families* in the save instead, with how many Sims each has.
   Enter loads that family's lot. You never touch the world or lot screens.
3. **On a lot.** The scanner announces itself. Ctrl+Alt+H reads every key.

Step 2 is the one that used to strand people: from the keyboard it feels
identical to the main menu, so the same key used to offer the wrong list.

---

## Keys

Everything sits behind Ctrl+Alt or Ctrl+Shift: polling reads key state but
cannot swallow it, so bare keys must stay free for the game.

Ctrl+Alt+N is deliberately unused — that is the Windows shortcut that starts
NVDA, and the mod has no business competing for it.

**Getting around**

    Ctrl+Alt+arrows     browse categories and items
    Ctrl+Alt+Enter      activate      Ctrl+Alt+Backspace  back
    Ctrl+Alt+S  rescan  Ctrl+Alt+R  repeat  Ctrl+Alt+W  where am I (and home)
    Ctrl+Alt+H  help    Ctrl+Alt+F  focus my Sim (and the time)
    Ctrl+Shift+F        keep the camera on my Sim (centres the audio)
    Ctrl+Shift+Enter    centre the camera on the lot

**Your Sim**

    Ctrl+Shift+N  needs      Ctrl+Alt+A  what they are doing
    Ctrl+Alt+E  emotion      Ctrl+Alt+G  wants
    Ctrl+Shift+O  aspiration, its description and the goals left
    Ctrl+Alt+P  phone      Ctrl+Alt+I  inventory   Ctrl+Alt+C  contacts
    Ctrl+Shift+R  relationships: who they know, and the full profile
    Ctrl+Shift+P  plan an event, or ask how the running one is going
                  (progress is also read out as it happens;
                   a11y2.eventwatch off stops that)
    Ctrl+Shift+M  household money
    Ctrl+Alt+1..8  play a different Sim in the household

**Pop-ups**

    Ctrl+Alt+D  read the open dialog     Ctrl+Alt+X  force it closed
    Ctrl+Shift+A  answer a call          Ctrl+Shift+Backspace  decline

**Going places**

    Ctrl+Shift+T   travel, no map screen (companions are in the list)
    Ctrl+Alt+Home  go home              Ctrl+Shift+Home  travel via the map
    Ctrl+Shift+H   move house, or move in with someone

**Doing things**

    Ctrl+Alt+M  create a Sim         Ctrl+Alt+L  change how a Sim looks
    Ctrl+Alt+J  jobs                 Ctrl+Alt+O  choose a save or household
    Ctrl+Shift+P  plan an event      Ctrl+Alt+V  cheats and fixes
    Ctrl+Alt+T  narration            Ctrl+Shift+L  randomise appearance
    Ctrl+Shift+G  game settings      Ctrl+Shift+S  save the game

**Building**

    Ctrl+Alt+K  buy catalog          Ctrl+Alt+B  tile grid
    Ctrl+Alt+Z  undo a placement     Ctrl+Shift+D  sell what you point at
    Ctrl+Alt+F5  reload the mod      Ctrl+Alt+Q  reachability probe

In grid mode the bare arrows move, Enter describes the tile in full
(including how much room is around it), PgUp/PgDn change level.

Console commands are all `a11y2.*`: `a11y2.diag`, `a11y2.who`, `a11y2.lots`,
`a11y2.rename.n`, `a11y2.voice`, `a11y2.dialogs`, `a11y2.queue`, `a11y2.quitjob`.

---

## What it can do

- **Scanner** — nearby objects by category, their interactions, run them.
- **Dialogs** — read, navigate and answer. Buttons come from the game's own
  response generator, so a mod's dialogs work too.
- **Shopping** — browse, set quantities, build a basket with a running total,
  buy. Reads prices and what you own.
- **Create-a-Sim** — names (typed or rolled), gender, age, voice, the game's
  real CAS Stories questionnaire, traits, aspiration, a new household, and a
  lot to live on.
- **Appearance** — CAS parts by body type, described from their tags.
- **Jobs** — take a job, go to work, take a day off, quit.
- **Build mode** — tile grid, buy catalog, placement with undo.
- **Households and saves** — switch household, choose what Continue opens.
- **Settings** — autonomy and ageing, read back from the game.

## What is not possible (checked, not assumed)

These are all **client-side screens with no server-side existence**. Verified
with `Ctrl+Alt+Q` while each was open — the game's own dialog service reports
no dialog at all:

- **CAS and the New Game flow.** With no lot loaded, `current_zone`,
  `client_manager`, `household_manager` and `sim_info_manager` are all None.
  The Sim being edited in CAS has no server-side object.
- **The career screen.** Screen up, game paused, `_active_dialogs` empty.
- **The pause menu and Options** (graphics/sound/controls live in Options.ini,
  which the game rewrites on exit).
- **Loading a save.** `PersistenceService` has save methods and zone readers,
  and no load method at all.
- **CAS part names.** There are none — `get_cas_part_name` is dead code in the
  retail build. Parts are described from their tags instead.

Where a screen is closed to us, the mod rebuilds its *contents* from tuning.
That is what Create-a-Sim and the job menu are.

---

## Known problems

- Shop purchases are performed by the mod itself, not through the game's own
  shop flow (which cannot be completed from Python — the picker only records a
  basket and the Sim buys later). Anything a shop does beyond "take money, give
  item" will not happen.
- Household-inventory items can be listed but not interacted with.
- Multi-tile object footprints are not checked when placing; only the cursor
  tile. Objects cannot be rotated.
- Travel music does not play after map-view travel.
- Centring the camera is the game's own Ctrl+Shift+Enter.
- Typing a name lets the letters through to the game, so W/A/S/D nudge the
  camera while typing.
- Weekday names assume the in-game week starts on Sunday. Times are certain;
  if a day name is ever wrong, they will all be wrong together.

---

## For developers

Module map, the findings that cost real time (the `.pyc`-only loader, RefPack,
notification tokens, protobuf `HasField`, `SimCreator` dropping names, the
`GetAsyncKeyState` latch bit, the integer funds reason code), and the build
instructions are in **DEVELOPERS.md**.
