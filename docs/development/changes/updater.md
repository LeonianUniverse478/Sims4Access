# TS4 Access Updater (2026-10-14)

Testers install builds from the GitHub releases of LeonianUniverse478/Sims4Access with one program.

## Files

- helper/TS4AccessUpdater.cs: Windows UI like TS4AccessHelper. Enter checks and installs, Alt+F chooses the Sims folder, and results appear in standard message boxes. `--user-folder` and `--install-folder` run an offline install of an unpacked package.
- helper/TS4AccessUpdater.Core.ps1: the logic. It is embedded with helper/ScreenReaderHelper.Core.ps1, which provides Find-HelperUserFolder, Enable-HelperMods and Assert-HelperGameClosed.
  - It reads releases/latest from the GitHub API, finds the TS4_Access_Update.zip and .sha256 assets, downloads both and checks the SHA-256.
  - It unpacks with path-escape protection and requires both mod files.
  - It installs where the mod already is (Mods or one subfolder), or in Mods\TS4_Access. Extra copies move to the backup, and the old files are backed up to TS4 Access Backups\mod-before-update-<time>.
  - It installs the speech pack if missing, or refreshes it in place, then enables script mods. The installed tag goes in TS4 Access Backups\installed-release.txt.
  - A missing release (404) says "No TS4 Access build has been published yet".
- helper/UPDATER-README.txt: player instructions.
- tools/build_updater.ps1: compiles helper/TS4AccessUpdater.exe with the Framework csc, as tools/build_prelaunch_helper.ps1 does.
- tools/test_updater.ps1: 28 checks. GitHub is replaced by local stand-ins, and installs go into fake Sims folders.
- tools/publish_github_release.ps1: packs the latest passing dist build into TS4_Access_Update.zip, with forward-slash entries. The zip holds the mod, release-assets\TS4_Access_SpeechPack, the helper, the updater and release-assets\INSTALL FIRST.txt.
  - It refuses a build whose v10 checks failed, or a script holding non-.pyc files.
  - It writes the .sha256 and creates the release with `gh release create`. -DryRun builds the package without uploading.

## Publishing a build

1. `Dev.ps1 build`, test it, then (once) `gh auth login`.
2. `powershell -NoProfile -ExecutionPolicy Bypass -File tools\publish_github_release.ps1 -Notes "What changed"`
3. Testers run TS4AccessUpdater.exe, attached to every release, with the game closed.
