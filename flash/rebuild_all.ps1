# Rebuild all patched UI movies for tyjokr_ScreenReader.
# Inputs: original EA movies (ea_*.swf) + TooltipManager_patched.as template +
# extra-classes/*.as, all resolved relative to a work dir.
# Usage: powershell -File rebuild_all.ps1 -WorkDir <dir with gfx\ea_*.swf>
# Tools: TS4_JAVA (java.exe) and TS4_FFDEC (ffdec.jar), else the defaults in
# flash_config.ps1; TS4_FFDEC_HELPERS for the compiled batch helper classes.
# After an EA patch: re-extract the ea_*.swf inputs from the new UI.package
# FIRST (python extract_ea_movies.py <WorkDir>), then re-run this, then
# gate_pcode.py, then build_ui_package.py, then deploy. Skipping the
# re-extract silently ships the PREVIOUS patch's UI as an override.
param(
    [Parameter(Mandatory=$true)][string]$WorkDir
)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $here 'flash_config.ps1')
$java = Get-A11yJava
$ffdec = Get-A11yFfdec
$template = Join-Path $here "TooltipManager_patched.as"
$extra = Join-Path $here "extra-classes"
$gfx = Join-Path $WorkDir "gfx"

$cell = Join-Path $extra "CatalogImageCellView.as"
$cellClass = "widgets.BuildBuy.controls.CatalogImageCellView"

# movie name -> optional extra (class, file) patches beyond TooltipManager+CatalogCell
$movies = [ordered]@{
    'ClassLibraryScaleform'     = $null
    'ClassLibraryOlympus'       = $null
    'ClassLibraryGamedata'      = $null
    'ClassLibraryWidgetsShared' = $null
    'UIContainer'               = $null
    'BaseLibrary'               = $null
    'ComponentLibrary'          = $null
    'GUIComponentLibrary'       = $null
    'HUDLibrary'                = $null
    # CommodityContainer is DEFINED in more than one movie (app-domain rule:
    # first-loaded copy wins), so its patch must ship in every movie that
    # defines it: SimInfoMotivePanel AND SimInfoTray. The unpatched
    # SimInfoTray copy silently shadowed the needs "name + percent"
    # announcer until 2026-08-03. Scan before adding any panel-class patch.
    'TimeControls'              = @("widgets.TimeControls.TimeControlsMain", (Join-Path $extra "TimeControlsMain.as"))
    # GameEntryLauncher previously also patched GELauncherMain with main-menu
    # probes; those were debug-only (the menu cannot reach Python) and are gone.
    # The movie itself stays patched so its TooltipManager copy can never win
    # the app domain unhooked.
    'GameEntryLibrary'          = $null
    'GameEntryLauncher'         = $null
    'GameEntryDock'             = $null
    # CAS renders on its OWN stage, so the live TooltipManager's mouse
    # listener never sees it. Patching TooltipManager into CASLibrary was
    # tried 2026-08-03 and does NOTHING: ClassLibraryGamedata wins that class
    # name for the whole application domain (proved by an
    # "over-ClassLibraryGamedata" mark), so CAS's copy is never loaded.
    # Instead hook from a class ONLY CAS defines and forward its mouse events
    # into the live TooltipManager, the same trick as MoodContainer in SimHub.
    # *** DO NOT RE-ENABLE CASCustomizer WITHOUT READING TODO-NEXT-SESSION.md ***
    # Any ffdec-rebuilt CASCustomizer HARD-CRASHES the client on CAS load,
    # regardless of what our code does. Proved twice on 2026-08-03, with the
    # "cashook" mark (posted at the very end of Initialize) never firing, so
    # the crash precedes our hook entirely. The hook source is kept at
    # extra-classes/CASCustomizerMain.as for whoever resumes this, but the
    # movie must NOT ship until the toolchain problem is solved (Weebersu
    # patches the same movie fine, so try Sims 4 Studio and byte-diff).
    # 'CASCustomizer'           = @("widgets.CAS.Customizer.CASCustomizerMain", (Join-Path $extra "CASCustomizerMain.as"))
    'SimInfoTray'               = @("widgets.Gameplay.SimInfoHUD.SimInfoTray.PhoneCategoryScreen", (Join-Path $extra "PhoneCategoryScreen.as"), "widgets.Gameplay.SimInfoHUD.MotivePanel.CommodityContainer", (Join-Path $extra "CommodityContainer.as"))
    'SimInfoMotivePanel'        = @("widgets.Gameplay.SimInfoHUD.MotivePanel.CommodityContainer", (Join-Path $extra "CommodityContainer.as"))
    'InteractionQueue'          = @("widgets.Gameplay.InteractionQueue.controls.InteractionButton", (Join-Path $extra "InteractionButton.as"))
    # SimHub owns the Sim portrait + mood. MoodContainer is defined ONLY here
    # (checked against all 258 movies), and it disables mouse on its own text
    # container, so the mood NAME had to be composed in the class itself.
    'SimHub'                    = @("widgets.Gameplay.SimHub.controls.MoodContainer", (Join-Path $extra "MoodContainer.as"))
    'ObjectBoundElements'       = @("widgets.ObjectBoundElements.elements.HoverTip", (Join-Path $extra "HoverTip.as"), "widgets.ObjectBoundElements.elements.SimHeadline", (Join-Path $extra "SimHeadline.as"))
    'Notifications'             = @("widgets.Notifications.NotificationsMain", (Join-Path $extra "NotificationsMain.as"))
    'Dialog'                    = @("widgets.Dialog.DialogMain", (Join-Path $extra "DialogMain.as"))
    'PieMenu'                   = @("widgets.Gameplay.PieMenu.PieMenuMain", (Join-Path $extra "PieMenuMain.as"))
    'Pickers'                   = @("widgets.Pickers.PickersMain", (Join-Path $extra "PickersMain.as"))
    # Purchase picker cart narration (quantity announce on +/-, debounced
    # totals, name-in-context on the spin buttons). All purchase picker
    # classes are defined ONLY in this movie (scanned all 258, 2026-08-06).
    # PickersPurchaseMain gets the A11yFocusInto hook (keyboard nav never
    # engaged here: our other hook is in widgets.Pickers.PickersMain, a
    # different class in a different movie). Hook is NOT in PickersMainBase
    # because that base is defined in SEVEN picker movies = app-domain
    # lottery; PickersPurchaseMain is defined only in this one.
    'PickersPurchase'           = @("widgets.Pickers.controls.PurchasePicker.PurchasePickerCellView", (Join-Path $extra "PurchasePickerCellView.as"), "widgets.Pickers.PickersPurchaseMain", (Join-Path $extra "PickersPurchaseMain.as"))
    # Dedicated class only: the shared Gamedata TooltipManager wins.
    'AgeUpPanel' = @("widgets.Gameplay.AgeUpPanel.AgeUpPanelMain", (Join-Path $extra "AgeUpPanelMain.as"))
    # GameTray's own TooltipManager/CatalogImageCellView copies stay exactly as
    # EA shipped them ($ownOnly below; the shared libraries win those classes);
    # only ControlPanel (keyboard travel route after the native M guards) is patched.
    'GameTray' = @("widgets.GameTray.controls.ControlPanel", (Join-Path $extra "ControlPanel.as"))
}
# Some originals were archived under instance-id names in early sessions
$eaAliases = @{
    'TimeControls'       = 'ea_C4B030271AE45C30.swf'
    'SimInfoMotivePanel' = 'ea_093958A845E285BA.swf'
}

$batchClasses = Get-A11yHelpers
$useBatch = Test-Path -LiteralPath (Join-Path $batchClasses 'ReplaceScriptsBatch.class')
if ($useBatch) { Write-Output ("compiler: ReplaceScriptsBatch helper in " + $batchClasses) }
else { Write-Output ("compiler: ffdec -replace per movie (no ReplaceScriptsBatch.class in " + $batchClasses + ")") }
$batchRows = New-Object 'System.Collections.Generic.List[string]'
foreach ($name in $movies.Keys) {
    $eaFile = Join-Path $gfx ("ea_" + $name + ".swf")
    if ($eaAliases.ContainsKey($name) -and -not (Test-Path $eaFile)) {
        $eaFile = Join-Path $gfx $eaAliases[$name]
    }
    if (-not (Test-Path $eaFile)) { throw "missing EA original: $eaFile" }
    # Read as UTF-8 explicitly: PowerShell 5.1's default decodes the template
    # with the ANSI codepage and mangles non-ASCII comment characters.
    $src = (Get-Content $template -Raw -Encoding UTF8) -replace 'A11YLIBNAME', $name
    $ttm = Join-Path $gfx ("ttm_" + $name + ".as")
    [System.IO.File]::WriteAllText($ttm, $src)
    $out = Join-Path $gfx ("patched_" + $name + ".swf")
    # ffdec -replace FAILS OUTRIGHT (no output file) if a named class is not
    # in the SWF, so only inject the shared classes into movies that actually
    # define them. CASCustomizer has neither TooltipManager nor
    # CatalogImageCellView (it is hooked purely through its own CAS class),
    # and unconditionally listing them silently produced no output
    # (2026-08-03). Class names live in the ABC constant pool as SIMPLE
    # names, so match those rather than fully-qualified ones.
    $eaText = [System.Text.Encoding]::ASCII.GetString([System.IO.File]::ReadAllBytes($eaFile))
    $args = @('-jar', $ffdec, '-replace', $eaFile, $out)
    $ownOnly = ($name -eq 'AgeUpPanel' -or $name -eq 'GameTray')
    if (-not $ownOnly -and $eaText.Contains('TooltipManager')) { $args += @('olympus.core.TooltipManager', $ttm) }
    if (-not $ownOnly -and $eaText.Contains('CatalogImageCellView')) { $args += @($cellClass, $cell) }
    if ($movies[$name]) { $args += $movies[$name] }
    if ($args.Count -le 5) { throw "NOTHING TO PATCH in $name" }
    # ffdec logs harmless tag-parse warnings to stderr on some movies
    # (CASCustomizer has 3 that EA's ORIGINAL produces too). Under
    # PowerShell 5.1, redirecting a native exe's stderr wraps each line in an
    # ErrorRecord, which with ErrorActionPreference='Stop' aborted the whole
    # rebuild mid-way (2026-08-03). Correctness is verified below by the GFX
    # magic check, so stderr must never be fatal here.
    # Stale-output guard: a silent ffdec compile failure leaves the
    # PREVIOUS build's file to pass the checks below (bit us on v8).
    if (Test-Path $out) { Remove-Item $out -Force }
    if ($useBatch) {
        $batchRows.Add(($args[3..($args.Count - 1)] -join "`t"))
        continue
    }
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { & $java @args 2>$null | Out-Null } catch { }
    $ErrorActionPreference = $prevEAP
    if (-not (Test-Path $out)) { throw "NO OUTPUT PRODUCED: $name" }
    $b = [System.IO.File]::ReadAllBytes($out)[0..2]
    $magic = [System.Text.Encoding]::ASCII.GetString($b)
    if ($magic -ne 'GFX') { throw "BAD OUTPUT ($magic): $name" }
    Write-Output ("OK  " + $name)
}
if ($useBatch) {
    $manifest = Join-Path $WorkDir 'replace-batch.tsv'
    [System.IO.File]::WriteAllLines($manifest, $batchRows)
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $java -Xmx2g -cp ($batchClasses + ';' + $ffdec) ReplaceScriptsBatch $manifest 2>&1 | ForEach-Object { $_.ToString() }
    $batchExit = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP
    if ($batchExit -ne 0) { throw "batch compiler failed: $batchExit" }
    foreach ($name in $movies.Keys) {
        $out = Join-Path $gfx ("patched_" + $name + '.swf')
        if (-not (Test-Path $out)) { throw "NO OUTPUT PRODUCED: $name" }
        $magic = [System.Text.Encoding]::ASCII.GetString([System.IO.File]::ReadAllBytes($out)[0..2])
        if ($magic -ne 'GFX') { throw "BAD OUTPUT ($magic): $name" }
    }
}
Write-Output "all movies rebuilt"
