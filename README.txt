TS4 ACCESS

START HERE

This mod reads menus, dialogs, tooltips and notifications aloud. Its
scanner finds Sims and objects and opens their interactions without
moving the mouse. Windows only.

Three guides:
README.txt: Installation, getting started and settings.
CONTROLS.txt: Keyboard shortcuts, grouped by activity.
CHEATS.txt: Optional settings and help commands.

GETTING STARTED

1. Install the mod and speech pack as described below.
2. Before playing, close The Sims 4, open TS4AccessHelper.exe and choose
   Enable Script Mods. Wait for confirmation. Do this before each play
   session and after every game patch to check that both mod options are on.
3. Start the game through Steam or the EA app, then load a household.
4. Press Ctrl+Alt+H, choose settings, and turn Scanner mode on.
   You can also toggle it with Ctrl+Alt+Space.
5. Wait for "Scanner", then use ordinary arrows to browse and Enter
   to open interactions. You do not hold Ctrl+Alt while browsing.

Up and Down browse the current list. Right enters a category.
Left or Backspace goes back. Space repeats speech.
For example: choose Plumbing, press Right, choose Showers, press Right,
then choose a shower and press Enter.

The scanner hides objects with no interactions for the active Sim and
updates when you switch Sims. Objects with disabled options stay listed
as unavailable; Enter opens their menu so you can hear the requirements.
Checks run in the background, so newly found objects may appear briefly
before filtering finishes. If a check fails, the object stays listed.
Unchanged objects are rechecked less often, up to once a minute. Press
Ctrl+Alt+S to request fresh checks. Switching Sims starts fresh immediately.
Checks pause while menus or text fields own keyboard input.

Menus and dialogs take over navigation while open. Escape closes them.
The scanner resumes and announces your place after they close.
For spoken help, press Ctrl+Alt+H and choose Keyboard shortcuts.
In Live mode, Scanner mode prevents arrow-key camera movement and follows
the active Sim. It does not change the Build mode camera.
With menus closed in Live mode, Shift+Tab toggles first-person view.
The scanner still works in first-person; its camera follow resumes when
you leave first-person view.

INSTALLATION

Download both the mod and the separate speech pack. The speech pack link
is on the mod's download page.

Extract both into your Sims 4 Mods folder. The mod files belong in
Mods\TS4_Access. The speech pack normally sits inside that folder
as TS4_Access_SpeechPack. Do not nest the mod any deeper.
Keep the extracted folder and file names as supplied; the speech pack
folder TS4_Access_SpeechPack is used to locate Prism.

Also download the TS4 Access Helper from the mod's download page.
Extract its ZIP and open TS4AccessHelper.exe. You can keep it anywhere,
such as your Desktop. With the game closed, choose Enable Script Mods or
press Enter, then wait for confirmation before opening the game.
This enables BOTH Custom Content and Mods and Script Mods Allowed.
If both are already on, the helper confirms that without changing them.

If the helper cannot find your settings, use Choose Sims folder to select
Options.ini in Documents\Electronic Arts\The Sims 4, or the OneDrive or
custom user folder your game uses. This is not the Steam or EA installation
folder. First-time players must open the game once and exit so it can
create Options.ini, then run the helper before playing.

If you use UI Cheats Extension, also install the separate compatibility
package in a folder that loads after other mods, such as Mods\_priority.
Update that package with the main mod. Otherwise, leave it out.

UPDATING

Close the game before replacing mod files. Keep TS4_Access.cfg
to preserve your settings. The main download does not include a settings
file that would overwrite yours.

After every Sims 4 patch, check for a compatible TS4 Access release, then
run the TS4 Access Helper with the game closed and choose Enable Script
Mods before playing. Game patches can turn mods off again. If the game
resets them on its first launch after a patch, close it, run the helper
again, and restart. The helper enables mods; it does not update mod files
or prevent the game from resetting these settings.

SPEECH

With the Prism speech pack installed, the mod can speak through NVDA, JAWS and
other supported screen readers. Your screen reader controls its voice
and speed. Microsoft Narrator is not supported.

Without a supported screen reader or the speech pack, the mod uses a
Windows voice. Only that fallback voice uses the rate, volume and name
settings under [voice]. The rate defaults to 3; its range is -10 to 10.

SETTINGS

Open settings from the accessibility menu, or enter a11y.menu window in
the cheat console.

You can also edit TS4_Access.cfg next to the mod files. It is a
plain-text INI file despite the .cfg extension. Save changes, then restart
the game or enter a11y.reload in the cheat console.

Most options use on or off. The main choices are:
Scanner mode: Ordinary arrow-key browsing and Live camera follow.
Keyboard: Navigation inside menus and panels.
Simplified menus: Move through menu options one at a time. On by default.
CAS and Stories keep their existing controls. Turn this setting off to
restore the original menu navigation.
Travel list: Choose travel destinations from lists instead of a map.
Numpad navigation: Optional keys for menus and panels.
Build controls: Place catalog objects from the lot grid in Build mode.
Sim actions: Announce what the active Sim starts doing. On by default.
Existing settings are preserved; set "sim actions = on" to enable it if
your settings file already has it off.
Object names: Read world-object tooltips.
Captions: Show spoken text on screen.

Build controls start on. Scanner mode starts off.
Speech mode can be hover, manual, beeps or off. Hover reads automatically;
manual waits for the read shortcut; beeps uses tones; off is silent.
Tooltip delay controls the wait before longer descriptions.
Braille can be concise, full, only or off.
Verbosity can be full or brief. Full says what a thing is before its name,
such as Category, Subcategory, Dialog or Menu open. Brief says only the names.

Shortcut blocking is automatic. There is no setting to manage it.

SIMPLIFIED MENUS

Simplified menus is on by default. Up and Down or Tab move through one
option at a time, including choices arranged in several columns.
Enter chooses an available single choice. For multiple choices, Space
selects or clears a row; use Done to confirm. Escape goes back or closes.
The game still checks availability, prices and selection limits.

Load Game treats each save as one choice. Enter loads the selected save.
CAS and Stories retain their existing controls.

TRAVEL

With Travel list and Keyboard on, press M. Choose Go alone or Choose
who comes when Simplified menus is on. With it off, the game's companion
picker opens directly. Then choose a world and destination. Some buildings
offer a unit list. If nobody is eligible to come, the game skips the
companion picker. If the game is paused, resume it so the Sim can travel.
Travel from the phone goes straight to the destination lists. To choose
companions, use M and Choose who comes.
Use Back to worlds or Back to places to return. Escape cancels.
Open the map instead continues the trip using the game's map.
The same setting covers vacation travel. Rentals show the stay length
and price before confirmation. Some destinations require the native map.

PHONE ACTIONS

With Simplified menus on, open Phone from the accessibility menu.
Ctrl+Alt+P also opens it when no call or text is waiting. Choose a category,
then an action. The list uses the game's available phone actions, including
jobs, planning events and moving household. The game's requirements and
confirmation screens still apply. Escape closes the phone list.
Choose Back to the phone to return from an action list to its categories.

HOUSEHOLDS

To play another household, open Manage Worlds from the game's menu.
Tab starts map navigation. Select an occupied lot with Enter, then
continue to Play and press Enter. The household actions follow the lots.
Moving is available through Phone, Travel, Move Household. Read the
furnishing choice and remaining funds in the final move-in dialog before
confirming. Cancel Moving returns without completing the move.

BUILD MODE

With Build controls on, press F2 to enter Build mode. Choose an object in
the Build catalog, then press Ctrl+Alt+B. The plain arrow keys move one
tile at a time and read what is there, walls and doors, and whether the
object fits. R turns it. Enter places it exactly on the tile; if it does
not fit, you hear why and the nearest spot where it does, and a second
Enter places it there. Number keys 1 to 6 read details. See CONTROLS.txt.
Ctrl+Alt+Z undoes the last placement with a refund. Ctrl+Alt+X sells the
object at the cursor after a second press to confirm. It sells what is
on top first, and refuses anything that still holds or carries something.
CONTROLS.txt lists every key.

CURRENT LIMITATIONS

Many Create a Sim controls still need the mouse.
Build mode places catalog objects only. Walls, floors, roofs, rooms,
stairs, pools, terrain and paint still need the mouse.
Objects that hang on a wall or ceiling, attach to a fence, or need water
or bare ground cannot be placed from the grid yet.
The game's own Build undo does not cover objects placed from the grid;
use Ctrl+Alt+Z.
On the map, choosing a lot does not automatically move keyboard focus to
its action panel. Continue through the options to Play or Confirm.

CREDITS

The world scanner, tile cursor, object placement and several keyboard
ideas come from LeonianUniverse's a11yscan mod, included with his permission.
