> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# Scanner v1: what changed and how to test it

**Current build: V7 is deployed for testing.** Start with [TEST-V7.md](TEST-V7.md).
All V6 and earlier sections below are historical.

Build of 2026-09-03 in `ScreenNarrator-integration`. Nothing here is
deployed until you say so. Artifacts: `build/tyjokr_ScreenReader.ts4script`
(11 modules) and the UI package built by the flash pipeline into this tree.
The parent `ScreenNarrator/` release tree is untouched.

## What was added

Python (`Scripts/`):

- `tyjokr_a11y_pump.py`: the sim-thread pump. A wall-clock alarm (20 ms,
  keeps firing while paused) drains a queue on the simulation thread; keys
  post work to it and never touch the game themselves. Re-armed on every
  zone load. If no lot is loaded, a chord says "No lot loaded".
- `tyjokr_a11y_scanner.py`: the scanner. Lists Sims and interactable
  objects within 40 m of the active Sim, grouped by EA's own build/buy
  category labels, sorted near to far. Names are resolved by the client
  in the player's language through the new loc channel. Enter asks the
  game for the REAL pie menu on the selected thing; from then on it is an
  ordinary pie menu (menu narration, focus walker, click activation).
- `tyjokr_a11y_buycat.py`: GENERATED table, BuyCat tag name to EA label
  hash (125 tags). `tools/gen_buycat_table.py` regenerates it after a
  patch. Hashes only, no text.
- `tyjokr_a11y_keys.py`: the Ctrl+Alt chord layer (glaroc's layout).
  Ctrl+Alt+Up/Down previous/next thing, Left/Right previous/next
  category, Enter open menu (then activate), Backspace close menu, S
  rescan, W where am I, R repeat, H help. While a chord is held the
  numpad/plain bindings are ignored so Ctrl+Alt+Enter cannot double-fire.
  AltGr (right Alt on a layout that types with Ctrl+Alt) is ignored.
- `tyjokr_a11y_lang.py`: distance/bearing/floor words plus the scanner
  messages, 17 languages, first pass.
- `tyjokr_a11y_settings.py`: `[features] scanner = on/off`.
- `tyjokr_a11y_narrator.py`: `a11y.menuopen` now also tells the scanner a
  pie menu is up; `a11y.settings` reads the scanner flag.

Flash:

- `TooltipManager_patched.as`: re-registers the client's "SendMessage"
  ExternalInterface callback with a wrapper. Names starting `A11y|` are
  handled locally (`loc` resolves a string hash with LocKey.FromHash and
  posts `a11y.loc_enc`; `pick` stores the scanner's pending pick);
  everything else is forwarded to EA's dispatcher unchanged. New
  listeners `A11yHook` (re-assert the callback, sent at every zone load)
  and `A11yHidePieMenu` (closes the pie menu).
- `PieMenuMain.as`: accepts the two reserved scanner reference ids
  (0xA11E5CA1 object, 0xA11E5CA2 Sim), synthesises the WorldPickResult the
  draw path needs, posts `a11y.menuclosed` from Hide, narrates the
  "disabled" reason when the game refuses a scanner menu, and moves the
  "menu open" announce AFTER the reference check (it used to fire for
  menus the client then dropped).

New console commands: `a11y.scan [rescan|next|prev|nextcat|prevcat|open|
back|where]` (same actions as the chords, for testing without keys),
`a11y.loc_enc` and `a11y.menuclosed` (Flash to Python, internal).

## Build record (2026-09-03 late)

- Movies: rebuild_all on the clone work dir, all 23 OK (second pass after
  the request-counter fix). Log: flash/rebuild-scanner-v2.log.
- Gate: fidelity gate PASSED, 60 targeted-class comparisons, zero
  untargeted drift. Log: flash/gate-scanner-v2.log.
- Package: build/tyjokr_ScreenReader_UI.package, 17,635,650 bytes (release
  copy is 17,620,365), round-trip verified, 23 resources. The fresh pcode
  export contains A11yAcceptScannerRequest, A11yPostText and the
  a11y.menuclosed literal in PieMenuMain, and A11yInstallGameMessageHook,
  A11yOnGameMessage, A11yResolveLoc, A11yMsgHidePieMenu in TooltipManager.
- Script: build/tyjokr_ScreenReader.ts4script, 11 modules (dev build, log
  default on).
- UI Cheats compat: rebuilt in lockstep from uicheats-base into
  build/tyjokr_ScreenReader_Compatibility_UICheats.package (see the
  compat-scanner-v2 log). Not needed on a machine without UI Cheats.

## v2 (2026-09-06): the pie menu request moved to the client

First in-game test: scan, names, categories and the name channel all
worked (real localized names and EA category labels in the log). Enter
did not: every request logged `menu for <id> -> 6 choices` on the server,
but the client never announced or drew the menu. The client discards a
PieMenuCreate it did not ask for before our patch can matter.

v2 mirrors the mouse path instead. Python sends the pick to Flash
(`A11y|pick|<id>|<type>|<lot>|<first name>|<x>|<y>|<z>|<level>`);
TooltipManager forwards it as the UI message `A11yOpenPieMenu`;
PieMenuMain's new `A11yOnOpenPieMenu` bumps the client's own request
counter, fills a WorldPickResult with the real coordinates, and posts
`interactions.choices` through `CallGameService("PostServerCommand")`,
exactly like a mouse click. The reply is then a menu the client asked for.
The v1 direct `generate_choices` call and the reserved reference ids are
gone from the request path.

Diagnostics in this build: every PieMenuCreate that reaches Flash posts
`MARK: ... piecreate-<ref>-<items>-<scanner|mouse>-last<counter>` to the
log (strip before release). An empty scanner menu says "No options"
through `a11y.menuempty`.

Extra test for v2: click an object with the MOUSE first. Expect "Menu
open, N options" AND a `piecreate-...-mouse` mark. Then Ctrl+Alt+Enter on
a scanned object: expect a `piecreate-...-scanner` mark whose ref equals
its `last` counter, the menu on screen, and "Menu open". If a scanner mark
never appears, the client is still not forwarding the reply and the
`interactions.choices` post from Flash is the thing to inspect.

## v2 also: chord keys are swallowed while Ctrl+Alt is held

Ctrl+Alt+arrows panned the camera on every scanner step, because polled keys
still reach the game. The client has no camera lock a mod can call (the UI's
"SetModalVisible" is the dialog modal state and would close pie menus), so
the build now installs a low-level keyboard hook (WH_KEYBOARD_LL) on its
own thread. While Ctrl+Alt is held, the game is in front and the key is a
scanner chord key, the hook refuses the key before the game sees it, and
reports it to our poller itself (a blocked key never updates the system
key state). Off switch: cfg `[features] scanner swallow = off`.
`a11y.settings` reads "scanner key swallow installed" when the hook is up.
Log lines: `keys: swallow hook installed (install #1)`; a reinstall line
means Windows dropped the hook during a stall and it came back.

Confirmed in-game 2026-09-06: the hook blocks the keys and the camera
stays put. Side effect found the same day: while installed, every
keystroke in every other program waited on the game's simulation
thread (the callback needs the GIL), so typing outside the game was
very slow. Fixed by installing the hook only while the game window is
in front and removing it within 50 ms of focus leaving; a11y.settings
reads "armed (installs while the game is in front)" when the game is
not focused.

Test: with the scanner keys, the camera must stay put. If it still pans,
the client reads the keyboard through raw input and a hook cannot block it;
the fallback is a different key set. Also check that normal typing in the
game (console, naming a Sim) and Alt+Tab still work with the hook up.

## Test plan (you drive; logging = on in the cfg)

1. Load any household. Expect in the log: `pump: started`, then a
   `MARK:` line as usual.
2. `a11y.scan` in the console. Expect a spoken line like "23 items, 9
   categories. Sims, 3 items. <your Sim's name>, here." If the category
   or names are missing but the counts are spoken, the loc channel is
   the suspect: look for `scanner: send ... failed` in the log, and
   whether any `a11y.loc_enc` reached Python (rawdiag is not needed; the
   scanner logs `scanner: N sims, M objects, K categories`).
3. Ctrl+Alt+Down a few times. Expect "<name>, N meters <bearing>. i of n."
   Hold it: it repeats at the same rate as the numpad keys.
4. Ctrl+Alt+Right/Left. Expect "<EA category label>, N items. <first
   thing>, ...". Labels should be the catalog's own words (Beds,
   Computers, Counters ...) in your game language.
5. Ctrl+Alt+Enter on an object. Expect the real pie menu to open at the
   mouse position, "Menu open. N options.", and Ctrl+Alt+Up/Down to walk
   its options; Ctrl+Alt+Enter runs the focused option; Ctrl+Alt+Backspace
   closes the menu. Numpad 4/6/5 keep working inside the menu too.
   If the menu does NOT appear but the log shows `scanner: menu for <id>
   -> N choices` with N > 0, the client dropped it: the PieMenuMain
   patch did not take (check the movie in the package).
6. Ctrl+Alt+Enter on a Sim. Expect the social pie menu (front page with
   Friendly/Romantic and so on). Try one social.
7. Ctrl+Alt+W: your Sim's name, then the focused thing. Ctrl+Alt+R
   repeats. Ctrl+Alt+H reads the help line.
8. Mouse-open a pie menu, then Ctrl+Alt+Up/Down: the chords should walk
   that menu too, and Ctrl+Alt+Backspace should close it.
9. Regression: the numpad walker, hover narration, dialogs, notifications
   and the purchase picker behave exactly as before.
10. Pause the game, then Ctrl+Alt+Down: still works (the pump rides the
    wall clock).
11. Quit to the main menu, then any chord: "No lot loaded", no error.

Log lines worth reading afterwards: `pump:`, `scanner:`, and any `keys:
chord ... failed`.

## Known limits of v1 (by design, for now)

- Only objects with a player-facing interaction are listed (same census
  filter as object names), within 40 m. Sims are always listed.
- Bearing is fixed to the world axes (north = +z), like glaroc's.
- The pie menu draws at the current mouse position.
- No phone/inventory/relationship categories yet (those panels are
  reachable through the UI walker).

## v3 (2026-09-07): two-level categories, the catalog's own

The flat list of 127 possible tag categories is gone. Categories now have
the same two levels as the Buy catalog:

- MAIN category = the buy category the client itself reports for the
  object's definition (`build_buy.get_object_buy_category_flags`):
  Comfort, Surfaces, Decorations, Electronics, Appliances, Plumbing,
  Lighting, Kids, Activities and Skills, Storage, Pets, Transportation, in
  the catalog's left-to-right order. Sims come first. Two catch-alls close
  the list: Build (doors, gates, ladders, pools: build-mode tags and no buy
  category) and Misc (anything the catalog never sold). Labels are the
  catalog's own filter strings (`olympus.localization.KeysBB` keys, listed
  with their sources in tools/gen_buycat_table.py). When the client reports
  several buy categories for one thing, the one matching the subcategory's
  tag family wins (a bar is Activities and Skills, not Surfaces).
- SUBCATEGORY = the tag label as before, now from three metadata files
  (buy 125 + build 38 + function 482 = 645 tags): a crafted painting reads
  "Art", a door "Doors", a dish its function label, instead of bare Misc.
  Room tags (Living Room, Kitchen...) are no longer picked over function
  tags (v1 could say "Living Room" for a sofa).

Keys (glaroc's layout kept; one pair added): Left/Right = main category.
Up/Down = things across the whole main category, ordered by subcategory
then distance; the subcategory name is spoken when it changes. Page Up /
Page Down (Ctrl+Alt) = jump to the previous/next subcategory inside the
main category. glaroc's build 3 leaves Ctrl+Alt+PageUp/PageDown unused (bare
PageUp/PageDown are his grid floor keys), so nothing collides. Both new keys
are swallowed like the others while Ctrl+Alt is held.

What you hear:

- Left/Right: "Comfort, 12 items. Sofas, 2 items. Sofa, 2 meters north."
- Up/Down inside a subcategory: "Sofa, 4 meters east. 2 of 12."
- Up/Down crossing into another: "Living Chairs. Armchair, 3 meters north.
  3 of 12."
- Page Up/Down: "Living Chairs, 4 items. Armchair, 3 meters north. 3 of 12."
- W: "Bella Goth. Comfort, Sofas. Sofa, 2 meters north. 1 of 12."
- Sims (and a Misc with nothing labelled) skip the subcategory line.

Log lines: `scanner: N sims, M objects, G categories (items/subcategories):
SIMS:3/1 COMFORT:12/4 ...` and then up to 12 lines `scanner:   MISC <def>
flags=0x... sub=... tags=...` (also for BUILD). Please send those lines
after a test: they show what the leftovers carry and whether flag bit 1024
really is Pets (the Python enum skips that bit; the generator presumes it).

Test additions (v3):

1. Ctrl+Alt+Right repeatedly: the catalog's own main names in your game
   language, catalog order, only the ones present on the lot.
2. In Comfort (or any main category with several subcategories):
   Ctrl+Alt+Down repeatedly. The subcategory name is spoken only when it
   changes; "i of n" counts the whole main category.
3. Ctrl+Alt+PageDown: first item of the next subcategory; wraps inside the
   main category. In Sims it just repeats the current Sim.
4. A door with interactions: expect "Build, N items. Doors, ...".
5. A Sim-painted painting, a dirty dish or a harvestable: expect Misc with a
   function label (Art, ...), not bare Misc.
6. Camera stays put on PageUp/PageDown as well.
7. `a11y.keys` lists "scanner prevsub: Ctrl+Alt+PageUp" and nextsub.
8. Ctrl+Alt+H reads the help line with the new keys.

## v4 (2026-09-15): settings menu, settings window, scanner window

New module `tyjokr_a11y_menu.py` (Python only; no Flash change, so the UI
and compat packages are unchanged).

**Settings menu (spoken).** Ctrl+Alt+U opens and closes it. While it is
open the chords drive the menu instead of the scanner: Up/Down move
between rows, Left/Right change the value, Enter switches it (or runs an
action row), Page Up/Page Down jump to the first/last row, Backspace
closes, S reads every row, W repeats the current row, H is the menu help,
R repeats. Every setting in the cfg is a row: speech mode, braille mode,
keyboard navigation, auto focus, scanner, scanner key swallow, object
names, Sim actions, tooltip delay, logging, voice rate, voice volume, voice
name; then the actions: read all settings, reload settings file, show
settings window, show scanner window, close menu. Changes apply live and
are written to the cfg at once, through the same paths the a11y.* commands
use. The menu always speaks (explicit), even in manual/beeps/off speech
mode. Turning keyboard navigation off adds a reminder that a11y.menu still
opens the menu from the cheat console. Console: `a11y.menu
[open|close|toggle|first|window]`.

**Settings window (visual).** A picker dialog with the same rows ("Speech
mode: hover", description = what the option does). It opens with the
spoken menu, is rebuilt after every change made by the chords (so a
sighted tester sees the value move), and closes with the menu. Clicking a
row switches it, exactly like Enter, and the window comes back with the
new value. Pickers are not narrated by DialogMain (they never were), so a
blind player hears nothing extra from the window.

**Scanner window.** `a11y.scanview`, or the menu row "show scanner
window": what the scanner sees right now, one row per main category
("Comfort" with "12 items, 4 subcategories") followed by one row per
thing (the game's own name and thumbnail, description = subcategory,
distance and bearing, "i of n"); the cursor row is preselected and
marked ">>". Picking a row moves the scanner cursor there and speaks it
the way the chords would, so you can steer the same list a blind player
hears, then Ctrl+Alt+Enter opens that thing's pie menu. Names and
category labels are the client's own string keys; nothing is translated
by the mod.

**First install.** When no cfg file existed at launch, the menu opens by
itself once, about 5 s after the first lot has loaded, saying "Screen
Reader is installed. This menu opens with Control Alt U. Settings menu.
Speech mode: hover. 1 of 18." and showing the settings window. To see it
on a machine that already has a cfg: delete tyjokr_ScreenReader.cfg before
launching, or run `a11y.menu first`.

Test additions (v4):

1. Ctrl+Alt+U: "Settings menu. Speech mode: hover. 1 of 18." and the
   settings window appears. Ctrl+Alt+U again: "Settings closed", window
   gone.
2. With the menu open, Ctrl+Alt+Down/Up walks the rows; Ctrl+Alt+Right
   on Speech mode says "Speech mode: manual." and the window shows the new
   value; Ctrl+Alt+Left brings it back. Check the cfg file changed.
3. Ctrl+Alt+Enter on "Scanner" toggles it; on "Tooltip delay" it only
   reads the value (Left/Right change it, in 0.5 s steps).
4. Ctrl+Alt+S reads all thirteen settings in one go; Ctrl+Alt+H reads the
   menu help; Ctrl+Alt+PageDown lands on "Close menu"; Ctrl+Alt+Enter
   there closes.
5. Mouse: click a row in the settings window; the value flips, the value
   is spoken, the window returns. Click "Close menu" in the window.
6. Scanner chords while the menu is open must NOT move the scanner; after
   closing the menu they work again.
7. `a11y.scanview` (or the menu row): the scanner window lists everything
   with the current item preselected. Click a thing: hear it announced,
   then Ctrl+Alt+Enter opens its pie menu.
8. `a11y.menu first`: the first-install wording, then the normal menu.
9. Speech mode off, then Ctrl+Alt+U: the menu still talks, and Right on
   the first row turns speech back on.
10. Voice name row (only matters without a screen reader): Left/Right
    cycles the installed Windows voices (first press may pause ~1 s while
    the list is fetched).

Log lines: `menu: opened`, `menu: closed`, `menu: scanner window with N
rows`, `menu: first run, opening in 5 s`, and any `menu: ... failed`.
# v5 follow-up (2026-09-15): typing, visual settings, captions

**Historical v5 checks:** see the v6 section below and
[DIALOG-ACCESSIBILITY-AUDIT.md](DIALOG-ACCESSIBILITY-AUDIT.md) for subsequent
dialog/keyboard fixes. The rebuild hold ended with the user's "fix them".
V5 checks do not prove the reported dialogs are usable.

**Deployed and hash-verified; in-game testing remains pending.** Main Flash
gate: 60 targeted comparisons passed. UI Cheats gate: 19 passed. Both
packages passed round-trip checks, with caption symbols in all 29 movies.
Full hashes and installed paths: `build/v5-verification.json` and
`build/v5-deployment.json`. Rollback copies: `build/deployed-before-v5/`.
The cfg was preserved, so captions start off until explicitly enabled.

The first-install settings popup is deferred at the user's request. This
section supersedes v4's spoken menu and automatic first-run test plan.

## Changes

- Hook installed only during Ctrl+Alt scanner chords with the game focused;
  removed on modifier release, Shift/AltGr, loss of focus or feature disable.
- No Ctrl+Alt+U or spoken settings menu. `a11y.menu window` opens settings.
  Picking a numeric row advances it and wraps to the minimum at the end.
- Captions (default off): settings row or `a11y.captions on|off`. Final
  narration appears bottom-centre for eight seconds in a noninteractive
  overlay. Long text is truncated to 480 characters with an ellipsis.
- Captions reflect repeat/deferred output and deduplication. Automatic
  text merely captured in manual/off mode is not displayed.

## Offline checks

`py -3.7 tools/test_scanner_v5.py`: **9 passed**. Covers cfg persistence and
row coverage, Unicode/delimiter encoding, delayed simulation-thread delivery,
duplicate suppression, manual-mode repeat, burst handling, truncation,
disable/no-pump behavior, silent numeric changes and wrap, stale/cancelled
dialog replies, deferred first-run behavior, unchanged scanner bindings,
and simulated native hook install/remove transitions. Native Win32 functions
are stubbed; these tests cannot prove game performance or Flash rendering.

`compile.build('build')` under Python 3.7: **12 modules**. Does not deploy.

## In-game test plan (pending)

1. Load a lot and type quickly in the cheat console and a naming/text field.
   Compare with scanner swallowing disabled if lag remains. Test pausing too.
2. Hold Ctrl+Alt, tap and hold arrows: scanner moves, camera stays still.
   Release either modifier, immediately type ordinary text, and verify no
   stuck/repeated scanner action. Try very fast chords (polling races remain
   possible), Shift and AltGr typing where available, and alt-tab away/back.
3. Run `a11y.menu window`. It opens silently, offers every setting and does
   not divert scanner chords. Click bool/choice/voice/numeric rows, including
   maximum-to-minimum wrap; cancel/close and reopen. Check persistence after
   restart. No first-install popup is expected in v5.
4. Run `a11y.captions on`, close the console, and scan. Compare the caption
   with spoken category, name, direction and item count. Check hover,
   dialog narration and repeat; captions should not capture clicks or focus.
5. Move quickly among targets; verify the caption reflects accepted output,
   replaces older text and hides after eight seconds. Test manual speech:
   hover is captured silently; repeat shows the spoken text. Turn captions
   off while visible and verify they clear. Reload a cfg with captions off.
6. Test accents, non-Latin names, `%` and `|`, and a long dialog/announcement.
   Confirm message delivery and visible wrapping/truncation; offline UTF-8
   roundtrips do not establish the game channel's maximum payload size.
7. Test UI scaling, resizing, Build/Buy and lot travel; check the overlay
   placement and reuse. CAS/main-menu coverage is not established because
   the current pump requires a loaded lot and CAS has a separate stage.
8. Repeat with UI Cheats compatibility installed. Continue v3's category
   checks above; the Pets bit and Build/Misc classification remain unverified.

---

# v6 (2026-09-15): dialogs, smooth pickers, keyboard sweep

**Deployed and hash-verified; in-game testing remains pending.** Main gate:
61 targeted comparisons passed; UI Cheats gate: 19 passed. All 12 Python 3.7
modules match source; all 30 packaged movie resources match their builds,
with original non-code tags and class-definition sets preserved. The main
package contains the original 23 movies plus AgeUpPanel (its own class only);
EngagementLibrary and CAS movies are excluded. The cfg was preserved.

Evidence: `build/v6-verification.json`, `build/v6-deployment.json`,
`flash/chain-navigation-v6-final.log`, `flash/gate-compat-v6.log`.
Rollback files: `build/deployed-before-v6/`. The checks below are **pending**,
not claimed in-game passes.

## Controls

With a modal open, hold **left Ctrl+left Alt**:

- Up/Down: previous/next control or logical picker row.
- Left/Right: change purchase quantity on the current row; otherwise move.
- Enter: activate the focused action. Backspace: back/cancel when permitted.
- R: read the dialog body and available text. H: modal navigation help.

Numpad 4/6 and 5 (NumLock on) also navigate and activate. Ordinary arrows
work in a modal outside text entry. In a name/text field, typing keys belong
to that field; use Ctrl+Alt+Up/Down or Numpad 4/6 to leave it. Right Alt/AltGr
must remain available for Polish characters. First-install settings stay
deferred; `a11y.menu window` is still the manually opened settings picker.

## Reported blocking dialogs

Test with NVDA and Polish game text, with logging enabled (`a11y.log on`).
For each case, test every available action in separate occurrences. A pass
requires the expected game result and ability to continue playing, not just
hearing a label. Do not bypass required selections or disabled buttons.

| Case | Acceptance |
|---|---|
| Likes/Dislikes | Body readable; Yes/No/OK are separate actual actions; each offered response works |
| Discovery Quest | Finish Quest, Cancel and other offered actions separately reachable and effective |
| Answered phone call | Caller/body and individual replies readable; accept/decline produces the correct result |
| Self-discovery | Initial decision and subsequent trait selection both usable |
| Work chance card | Read full prompt and each choice; choose and resume gameplay |
| Trait reassignment | Enter trait choices; remove an existing choice; select replacement; confirm/cancel correctly |
| Age-up | Traverse trait/aspiration/name controls; required choices enable Done; changes persist |
| Successive/nested dialogs | New top dialog owns keys; closing it restores a live prior scope; no background action |

## Picker and keyboard stress checks

1. Purchase Books or another long purchase picker: traverse every row down,
   then back up, crossing several viewports. No skips, page jumps or stalls.
   Reach the final row and footer, then reverse into the last row.
2. Repeat with Sim, food, outfit, grid, multi-select and column pickers. Include
   zero/one item, filtered/sorted results, long labels, and multiple columns.
3. Rapidly tap Down three times then Up; hold/release; reverse at the visible
   boundary. Press Enter immediately after movement. Quantity Left/Right
   during a pending scroll must apply to the destination row in input order.
4. Change selections/filters so cells recycle or disappear; navigate again.
   Open/close a popup during pending movement, and mix mouse clicks with keys.
   No delayed action should operate a previous dialog or old row.
5. Check quantity changes, selected state, item descriptions, disabled reasons,
   cart totals and all footer actions. Trait Remove must be separately reachable.
6. Test auto-focus both on and off. With it off, the first navigation key must
   enter the current modal. Clear focus and navigate again without escaping it.
7. Type quickly in console and name fields, including Polish AltGr characters,
   punctuation, arrows and Enter. Alt-tab and return; release modifiers before
   navigation keys. No stale tap, unwanted action or camera movement from chords.
8. Repeat paused, at different UI scales, after lot travel, and with UI Cheats.
   Test options/save/travel/notification-action widgets separately. Main-menu
   before a loaded lot and CAS's separate stage remain known coverage gaps.

If speech is silent, collect `a11y.status`, `a11y.test` and the log from that
installation. Tolk-failure fallback is fixed, but the original tester's cause
is unknown. A `picker-reveal-failed-<index>` log means target realization timed
out and requires the picker name, filter, UI scale and preceding keys to trace.

## Offline evidence

- `py -3.7 tools/test_navigation_v6.py`: 9 passed (pump dispatch, modal routing,
  short tap ordering, duplicate suppression, focus loss, typing ownership,
  Tolk/NVDA/SAPI fallback and Polish text, braille-only behavior).
- `py -3.7 tools/test_scanner_v5.py`: 9 passed (captions/settings/hook regressions).
- Native/game APIs are stubbed in these tests; they do not execute the Flash
  UI or prove input latency. Final compiler, pcode, package, source and installed
  hash checks are recorded separately in the handoff and build manifests.
