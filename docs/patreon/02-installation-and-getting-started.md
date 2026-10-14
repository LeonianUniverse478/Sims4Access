# TS4 Access: Installation & Getting Started

This guide covers installing **TS4 Access**, setting up speech, and getting started with the keyboard. You can find the mod and its current limitations on the [**main mod page**]({{MOD_POST_URL}}).

⚠️ **Windows only:** TS4 Access does not currently support macOS or consoles.

## **Installing the Mod**

Close *The Sims 4* before installing or updating the mod.

1. Download and extract the main mod ZIP.
2. Place the extracted **TS4_Access** folder directly inside your Sims 4 **Mods** folder.
3. Check that **TS4_Access.ts4script** and **TS4_Access_UI.package** are both directly inside **`Mods\TS4_Access`**.

Your Mods folder is normally inside **`Documents\Electronic Arts\The Sims 4`**. If your Documents folder is managed by OneDrive, use the Mods folder belonging to the Sims 4 user folder your game actually uses.

**Do not place TS4_Access inside another folder within Mods.** An extra folder created while extracting the ZIP can prevent the script from loading.

## **Setting Up Speech**

**A screen reader is optional.** Without a supported screen reader, the mod uses a Windows text-to-speech voice. Microsoft Zira is selected by default.

If you want to use your own screen reader or a braille display, also download the free [**Speech Pack**](https://simfileshare.net/folder/274249/) and extract it into your Mods folder. Allow its **TS4_Access** folder to merge with the mod's folder.

The expected location of the speech library is **`Mods\TS4_Access\TS4_Access_SpeechPack\prism.dll`**. Keep the supplied folder names so the mod can find it.

Start your screen reader before starting the game. **NVDA and JAWS** are supported; **Microsoft Narrator is not supported**. If you would like to try NVDA, it is available free from [**NV Access**](https://www.nvaccess.org/download/).

When speech is coming through your screen reader, use that screen reader's settings to change its voice and speed. The mod's Windows voice settings only affect its fallback voice.

## **Before Playing: Run the TS4 Access Helper**

**Run the [TS4 Access Helper]({{HELPER_DOWNLOAD_URL}}) before each play session and after every game patch.** The game needs both **Enable Custom Content and Mods** and **Script Mods Allowed** turned on for TS4 Access to work, and patches can disable them. Please do not skip this step!

To check and enable both settings:

1. Close the game.
2. Extract the helper ZIP and open **TS4AccessHelper.exe**. You can keep it anywhere, such as your Desktop.
3. Choose **Enable Script Mods**, or simply press **Enter**.
4. Wait for the confirmation, then start the game normally through **Steam** or the **EA app**.

The helper finds your Sims 4 user folder automatically. If it cannot find it, use **Choose Sims folder** to select **Options.ini**, normally inside **`Documents\Electronic Arts\The Sims 4`**. Use the folder your game actually uses, including OneDrive Documents if applicable. **You do not need to select your Steam or EA installation folder.**

The helper enables both **Custom Content and Mods** and **Script Mods Allowed**, including other mods already installed. **It does not download or install TS4 Access for you.** Your other game options and saved games are left alone, and the helper backs up the options file before changing it.

If both settings are already on, the helper confirms they are enabled without rewriting the file or creating another backup. If the game turns mods off on its first launch after a patch, **close the game, run the helper again, and restart**.

If this is your first time running The Sims 4, launch it once and then close it so the game can create its user files.

## **Loading or Starting a Game**

Narration begins at the main menu. Use **Tab** to move through its choices and **Enter** to choose one. In **Load Game**, each save is a single choice; Enter loads the selected save.

You can start with an existing household or create a new one. **Create a Sim is not fully accessible**, and many appearance controls still require the mouse.

If you have **Seasons** installed, the season screen offers **Spring, Summer, Fall, and Winter**. Use **Tab** or **Shift + Tab** to browse. **Space** selects a season without leaving the screen, while **Enter** selects it and continues.

On the world and neighborhood maps, press **Tab** to begin browsing, then use Tab or the arrow keys to move between controls. **Enter** selects a world or lot. Lot descriptions include occupancy and affordability.

After choosing a house, continue to **Confirm** and press Enter. In the move-in dialog, Enter opens the furnishing choice, the arrows browse its options, and Enter selects one. Tab reaches **Purchase Home**. **Listen to the furnishing choice and remaining funds before confirming.** Escape cancels the dialog.

## **Your First Few Minutes in Live Mode**

Once your household has loaded, press **Ctrl + Alt + H** to open the accessibility menu. Open **Settings** and turn **Scanner mode** on, or use **Ctrl + Alt + Space** to toggle it directly.

Wait until you hear **"Scanner"**. You can then use ordinary arrow keys without holding Ctrl or Alt:

- **Up / Down:** Browse the current list.
- **Right:** Open a category or subcategory.
- **Left / Backspace:** Go back one level.
- **Enter:** Open a category or a Sim or object's interactions.
- **Space:** Repeat speech.

For example, choose **Plumbing**, press Right, choose **Showers**, press Right, then choose a shower and press Enter to open its interactions.

Menus take over the controls while they are open. Close them with **Escape** and the scanner will announce your place again. In Live Mode, Scanner mode follows the active Sim and stops the arrow keys from moving the camera.

You can return to the accessibility menu with **Ctrl + Alt + H** and choose **Keyboard shortcuts** whenever you need the controls read aloud. See [**Controls & Settings**]({{CONTROLS_POST_URL}}) for more, or the [**Build Mode Guide**]({{BUILD_POST_URL}}) to start furnishing your home.

## **Updating & Compatibility**

Close the game before replacing mod files. Keep **TS4_Access.cfg** to preserve your settings; the main download does not include a settings file that overwrites yours.

If you use **UI Cheats Extension**, install the matching [**compatibility add-on**](https://simfileshare.net/folder/274251/) in a priority folder and update it alongside TS4 Access. My [**priority folder guide**](https://www.patreon.com/tyjokr/posts/165980351) explains how to set that up. You do not need this add-on if you do not use UI Cheats Extension.

**After every Sims 4 patch, check for a compatible TS4 Access release and run the TS4 Access Helper before playing.** With the game closed, choose **Enable Script Mods** and wait for confirmation. If the game resets the settings on its first launch after the update, close it, run the helper again, and restart. The tool enables mods; it does not update them or prevent the game from resetting those settings.
