TS4 Access Player Guide

Installation, controls, and accessibility features for The Sims 4.


START HERE

TS4 Access makes The Sims 4 more accessible by reading menus, dialogs, tooltips and notifications aloud. Its Scanner helps you find Sims and objects and open their interactions without using the mouse. TS4 Access is available for Windows only.

Three guides are available:

README.txt: Installation, getting started and settings.

CONTROLS.txt: Keyboard shortcuts, grouped by activity.

CHEATS.txt: Optional settings and help commands.


INSTALLATION

If you have never run The Sims 4 before, start the game once and exit. This creates Options.ini, which the TS4 Access Helper needs.

Download TS4 Access and its separate speech pack from the mod download page. Extract the mod into your Sims 4 Mods folder. The usual location is Documents\Electronic Arts\The Sims 4\Mods. The mod files belong in Mods\TS4_Access. Keep the supplied folder and file names and do not nest the mod any deeper.

Extract the speech pack into Mods\TS4_Access so that its folder is Mods\TS4_Access\TS4_Access_SpeechPack. This folder name is used to locate Prism.

Download the separate TS4 Access Helper and extract its ZIP. You can keep TS4AccessHelper.exe anywhere, such as your Desktop. With The Sims 4 closed, run the Helper, choose Enable Script Mods (or press Enter), and wait for confirmation. It enables both Custom Content and Mods and Script Mods Allowed. Run the Helper before each play session and after game patches to check that both settings are enabled.

If the Helper cannot locate your settings, use Choose Sims folder to select Options.ini in Documents\Electronic Arts\The Sims 4, or in the corresponding OneDrive or custom user folder. Do not select the Steam or EA game installation folder.

If you use UI Cheats Extension, install the separate TS4 Access compatibility package in a folder that loads after other mods, such as Mods\_priority. Update it with the main mod. Otherwise, leave it out.


GETTING STARTED

Start The Sims 4 and create or load a household. In Live Mode, press Ctrl+Alt+H to open the accessibility menu, choose Settings, and enable Keyboard and Scanner as needed. You can also toggle Scanner mode with Ctrl+Alt+Space.

Wait until you hear “Scanner.” Use the ordinary arrow keys to browse, and Enter to open interactions.

For information about the guided Create a Sim test version, see Create a Sim and Stories below.


SCANNER

The Scanner lets you browse Sims and objects around your active Sim and open their interactions from the keyboard. Both Keyboard navigation and the Scanner feature must be enabled. Press Ctrl+Alt+Space to toggle Scanner mode and wait for “Scanner.”

Use Up and Down Arrow to move through the current list. Right Arrow enters a category or subcategory; on an item, it repeats that item. Left Arrow or Backspace goes back one level. Enter enters a category or opens a Sim or object interaction. Space repeats the announcement. Escape follows the normal game or menu behavior; it does not switch Scanner mode off.

The Scanner filters out objects with no available interactions for the active Sim. Some unavailable actions may still appear, along with their requirements. Menus and text fields take priority over Scanner keys; the Scanner resumes when these menus close.

Press Ctrl+Alt+1 through Ctrl+Alt+8 to switch between household Sims. The Scanner updates for the newly active Sim.


Updating Scanner Results

The Scanner checks objects in the background. Results may change as those checks finish, and unchanged objects are checked less frequently. Press Ctrl+Alt+S to request fresh checks. Switching Sims starts fresh checks for the newly active Sim.


CAMERA

In Live Mode, Scanner mode prevents the arrow keys from moving the camera and follows the active Sim. It does not change the Build Mode camera.

With menus closed in Live Mode, press Shift+Tab to switch to first-person view. Press it again to return to the normal camera. TS4 Access announces when first-person view is turned on or off. The Scanner still works in first-person view; its camera follow resumes when you leave that view.


UPDATING

Close The Sims 4 before replacing TS4 Access files. Keep your existing TS4_Access.cfg so you do not lose your settings. The main download does not include a settings file, to avoid overwriting your existing settings.

After a Sims 4 patch, check for a compatible TS4 Access release. With the game closed, run the TS4 Access Helper and choose Enable Script Mods before playing. If the game resets its mod settings when first opened after a patch, close it, run the Helper again, and restart.

The Helper enables the game’s mod settings. It does not download or install updates to the mod files.


SPEECH

With the Prism speech pack installed, TS4 Access can speak through NVDA, JAWS and other supported screen readers. Your screen reader controls its own voice and speaking rate. Microsoft Narrator is not supported.

Without a supported screen reader or the speech pack, TS4 Access uses a Windows voice. Only that fallback voice uses the rate, volume and name settings under [voice]. The rate defaults to 3 and ranges from -10 to 10. Those settings do not control NVDA or JAWS.


SETTINGS


Opening Settings

Press Ctrl+Alt+H to open the accessibility menu, then choose Settings.

Alternatively, press Ctrl+Shift+C to open the game’s cheat console, type a11y.menu window, press Enter, then press Escape to close the console.


Navigation and Interaction

Scanner mode: Lets you browse Sims and objects with the arrow keys. In Live Mode, the camera follows the active Sim. Scanner mode is off by default. Press Ctrl+Alt+Space to toggle it.

Keyboard: Enables keyboard navigation in menus and panels. Keyboard navigation and the Scanner feature must both be enabled for ordinary Scanner arrow-key browsing.

Simplified menus: Lets you move through menu options one at a time with Up and Down Arrow or Tab, including menus arranged in columns. It is on by default. Turn it off to restore the original menu navigation. Create a Sim and Stories retain their own controls.

Travel list: Lets you select travel destinations from lists rather than the game’s map. Keyboard must also be enabled.

Numpad navigation: Provides optional numeric keypad controls for menus and panels, not the Scanner. See CONTROLS.txt for the keys.

Build controls: Enables keyboard placement of supported catalog objects in Build Mode. It is on by default. See Build Mode for the basic workflow.


Announcements and Feedback

Sim actions: Announces actions your active Sim starts doing. It is on by default for new settings; existing settings are preserved. If an existing configuration has it off, set sim actions = on to enable it.

Object names: Reads tooltips for objects in the game world.

Captions: Shows text spoken by TS4 Access on screen. This does not mean every announcement from your screen reader appears in the game.


Speech Behavior

Speech mode: Hover reads information automatically as you navigate. Manual waits for the read shortcut. Beeps uses tones instead of spoken feedback. Off turns off speech from TS4 Access, not your screen reader.

Tooltip delay: Controls how long TS4 Access waits before reading longer tooltip descriptions.

Verbosity: Full announces what an item is before its name, such as Category, Subcategory, Dialog or Menu open. Brief announces names without those additional descriptions.


Braille

Controls Braille output in TS4 Access. The available options are Concise, Full, Only, and Off.


Advanced Configuration

You can find TS4_Access.cfg in your Mods\TS4_Access folder. Although it has a .cfg extension, it is just a text file, so you can open it in Notepad.

Most settings use on or off, while others have specific values. Once you have made your changes, save the file and restart The Sims 4. You can also enter a11y.reload in the game’s cheat console to reload the settings without restarting.


NAVIGATING MENUS

When a menu or dialog opens, its controls take priority over the Scanner. The Scanner resumes when you close the menu.

With Simplified menus enabled, use Up and Down Arrow to move through options one at a time, even in menus arranged in several columns. Tab and Shift+Tab move between controls. Enter activates or confirms an option. Space selects or clears an item in a multiple-choice list; choose Done to confirm. Escape goes back, closes or cancels. Arrow keys can also adjust values, depending on the control.

The game still enforces availability, prices and selection limits. See CONTROLS.txt for more specialized menu controls.


Create a Sim and Stories

Create a Sim (CAS) and Stories do not necessarily use the ordinary Simplified menus controls.

A guided Create a Sim test version is described in CONTROLS.txt for new households. Choose Start for a step-by-step guide or Skip for the full CAS screen. The guide covers the Sim’s name, age, gender, traits, aspiration, optional voice and walk style, and additional Sims and relationships.

The guided Create a Sim feature is marked as a test version. Refer to CONTROLS.txt for its available controls; behavior may change as development continues.


TRAVEL

With Keyboard and Travel list enabled, press M while playing. With Simplified menus on, choose Go alone or Choose who comes. If no other Sims are eligible, the companion picker may be skipped. With Simplified menus off, the game’s companion picker opens directly.

Choose a world, such as Willow Creek, then a destination. Some buildings also ask you to choose a unit. Use the arrow keys to browse lists and Enter to select. Choose Back to worlds or Back to places to return to earlier lists, or press Escape to cancel. If the game is paused, resume it so your Sim can travel.

Open the map instead continues through the game’s map. Travel list also covers vacation travel, including rental stay length and price, but some destinations still require the native map.

Phone travel opens destination lists directly. To choose companions, use M.


PHONE

Press Ctrl+Alt+P to open a waiting call or text message. When nothing is waiting and Simplified menus is enabled, the same shortcut opens the phone action list. You can also choose Phone from the accessibility menu (Ctrl+Alt+H).

With Simplified menus enabled, phone actions are arranged in categories. Use the arrow keys to browse, Enter to choose an action, and Escape to close the list. Choose Back to the phone to return from an action list to the categories.

Available actions can include finding jobs, planning events and moving households. The game’s requirements and confirmation screens still apply. If a call or text is waiting, you may be asked to respond before opening ordinary phone actions.


HOUSEHOLDS


Switching Between Households

To play another household, open Manage Worlds from the game menu. Press Tab to begin map navigation. Use Tab or the arrow keys to browse lots and Enter to select an occupied lot. Continue navigating to Play, then press Enter. Selecting a lot does not automatically move focus to its action buttons.


Moving and Splitting Households

Moving a household is available through the Phone actions. Read the furnishing choice and remaining funds in the final move-in dialog before confirming. Cancel Moving returns without completing the move.

Household Split and Merge includes controls for selecting Sims, transferring Sims or funds, and confirming changes. Selecting a destination household may not work reliably with keyboard navigation. Do not confirm a transfer until the intended destination and changes are clear.


BUILD MODE


Finding an Object

With Build controls enabled, press F2 to enter Build Mode. Press Ctrl+Alt+O to open the accessible catalog. Browse by room or function using the arrow keys and Enter. Press Ctrl+Alt+D to search the catalog directly.


Placing an Object

After choosing a supported catalog object, press Ctrl+Alt+B for keyboard placement. Use the ordinary arrow keys to move one tile at a time. Press R to rotate, or Shift+R to rotate the other way. Press Enter to place the object.

If the object does not fit, TS4 Access can announce a nearby valid position; press Enter again to accept that suggestion. Number keys 1 through 6 read information about the lot, nearby objects and placement. See CONTROLS.txt for the full key reference.


Managing Placed Objects

Press Ctrl+Alt+Z to undo the last keyboard placement with a refund. Press Ctrl+Alt+X to sell an object at the cursor; press it again to confirm. The mod may refuse to sell an object that still contains or supports something.


CURRENT LIMITATIONS

TS4 Access is still under development. Some Create a Sim controls still require the mouse. The guided Create a Sim test version does not establish that all CAS workflows, including editing an existing Sim, are accessible.

Build Mode supports placing catalog objects, but walls, floors, roofs, rooms, stairs, pools, terrain and paint still require the mouse. Objects that hang from a wall or ceiling, attach to a fence, or require water or bare ground cannot currently be placed from the keyboard grid.

The game’s own Build undo does not cover objects placed using the keyboard grid; use Ctrl+Alt+Z. On the map, choosing a lot does not automatically move keyboard focus to its action panel. Continue to Play or Confirm.


CREDITS

The world scanner, tile cursor, object placement and several keyboard ideas come from LeonianUniverse's a11yscan mod, included with his permission.
