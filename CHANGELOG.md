# TS4 Access test builds: changelog

Newest first. Built and tested against **The Sims 4 1.128.90.1030**. These
builds start from tyjokr's TS4 Access build of 2026-09-26, and every change is
returned to tyjokr for the official mod.

Install or update with TS4AccessUpdater.exe from the
[latest release](https://github.com/LeonianUniverse478/Sims4Access/releases/latest).

---

## build-2026-10-14_061531 (2026-10-14)

### Guided new game

Start a New Game and choose whether to do the questionnaire. A **Create your
Sim** window then offers a step-by-step guide in which every step is a window
of buttons, with no tabbing around Create a Sim. Escape on that first window
skips the guide. See [docs/GUIDED-NEW-GAME.md](docs/GUIDED-NEW-GAME.md).

- **Name:** type it in the game's own name boxes (first name, Tab, last name,
  Enter), let the game pick a random name, or keep the one it made.
- **Age and gender:** Infant to Elder, then Female or Male. The current choice
  is marked "(now)".
- **Traits:** add by group (traits that clash with your choices are left out),
  remove, up to the age's limit. The window reads what is chosen so far.
- **Aspiration:** a category, then an aspiration.
- **Your Sim:** a summary of name, traits and aspiration, with a button to
  change any of them.
- **Voice and walk style (optional):** a voice, its pitch (Lowest to Highest)
  and a walk style. Done never requires these.
- **More Sims:** Add another Sim runs the same steps for a new Sim, then asks
  how they are related to the others (Spouse, Parent, Sibling and so on). Set
  relationships and Change another Sim come back to any Sim later.
- **Finding a home:** the guide saves the household to your library and opens
  the world map. Choose a season (with Seasons), then a world, which says how
  many houses you can afford. Then choose a home: houses first, cheapest first,
  with bedrooms, bathrooms and price, and empty lots last, marked as needing a
  house built. Choose Furnished or Unfurnished, each saying what money is left.
  The guide buys the home in the game's own move-in window, and the game loads
  your lot.
- If the guide ever runs into a problem, it says so and closes, rather than
  leaving you waiting. The log records each step.

### TS4 Access Updater

- **TS4AccessUpdater.exe** installs the newest build from this repository's
  releases. It checks the download against its checksum, backs up your current
  files, installs the mod and the speech pack, removes duplicate copies so the
  game loads only one, and turns on Script Mods. It refuses to run while the
  game is open.

---

## 2026-10-11

### Expansion and game pack readers

- **Milestones** (Growing Together): Ctrl+Alt+M and an accessibility menu row.
  Each milestone, by category, says whether it is reached and at what age (or
  how many times), in progress, or not reached, with the game's own text.
- **Character values** (Parenthood): Ctrl+Alt+K and a menu row. Each value on
  its scale, and the trait it would give at age up.
- These rows only appear when the pack is installed.

### Careers

- **Hospital patients** in the scanner's Sims category say their visit stage,
  for example "Mateo Lewis, patient, waiting". No illness is ever named.

### Households, moves and money

- **Household Split and Merge, Transfer Funds and the move dialog** now name
  both ends. The funds arrows say "Moves the amount from A to B" with both
  balances, Transfer Sims names the households, and lists say which household
  a Sim or item is in.
- Plus and minus amounts are spoken as "plus" and "minus".

### Businesses

- A **Businesses** menu row lists every business the household owns, with the
  panel's own figures: open, stars, funds, items sold, customers, revenue,
  costs, net profit, markup, employees and wages. Mod businesses that use the
  game's business system, such as the WickedWhims strip club, are included.
- **Hiring by keyboard:** each Sim you can hire is its own stop, and Enter
  opens the hire window. Promote, Demote and Fire are reachable for current
  employees.

### TS4 Access Plus by Michael Maslo

- Alt-key readouts: needs as percentages, time with work and bills, rooms,
  "where am I", and notification history.
- Reminders for low needs, work and bills; spoken game speed and Build or Live
  mode.
- Create and edit Sims without Create a Sim, including a new family moved onto
  a lot.
- A Build helper that builds rooms and whole houses (one or two floors, roofs,
  doors, decorating and furnishing) with the game's own tools.

### Diagnostics

- With logging on, script mod menus and hospital career details are written to
  the log, to plan support for mod menus and an accessible diagnosis readout.

---

## 2026-09-30

### Readers

- **Ctrl+Alt+E reads the whole mood panel:** the mood and its description, then
  every moodlet with its effect, boost, time left, reason and description.
- **Ctrl+Alt+C** reads household funds after the day and time.
- **Ctrl+Alt+Q** opens the action queue: what your Sim is doing and waiting to
  do, who chose each action, and Enter to cancel.
- **Ctrl+Alt+V** opens events: each party, date, holiday or career event with
  its guests and time left. You can send all guests home and end the event,
  end it, or send the guests home.

### Inventory

- Enter on an inventory item opens an item menu: the item's actions, Sell for
  a price, and for stacks Sell one, Sell all (with a confirmation) or Choose
  how many.

### Build mode

- **Build cursor** (Ctrl+Alt+B): plain arrows move tile by tile and read each
  tile. Enter places, R rotates, and number keys give details. When an object
  does not fit, the cursor says why and offers a spot where it does.
- **Tab in Build mode** goes straight into the catalog: filters, search, tabs,
  categories, then items.
- **Escape** leaves the Build catalog.

### Settings

- **Verbosity:** Full (the default) or Brief, which drops words like
  "Category." and "Dialog." before names.
- **Ctrl+Alt+L** turns diagnostic logging on or off.
