# Build the UI Cheats Extension compatibility movies.
#
# UI Cheats overrides 4 of our movies (SimInfoMotivePanel, SimInfoTray,
# TimeControls, ClassLibraryOlympus). With both mods installed, whichever
# package loads later wins each movie whole, so one mod's features die
# there. This build takes UI CHEATS' movies as the BASE (from
# uicheats-base\, extracted from UI_Cheats_Extension.package; see
# uicheats-base\SOURCE.txt for the version, 1.59.1 as of 2026-08-28) and
# injects OUR classes on top, producing movies where both feature sets
# coexist. Verified against their v1.57 decompile: they touch NONE of the
# classes we inject (their motive/relationship/money cheats live in their
# own cheat-extension classes, which the base keeps), and their only edit
# to a class we DO inject, TimeControlsMain, is replicated inside our
# copy via a runtime getDefinitionByName lookup, so it also works without
# UI Cheats installed. Re-extract new bases after a UI Cheats update.
#
# Usage: powershell -File build_uicheats_compat.ps1 -WorkDir <scratch>
# Tools: TS4_JAVA, TS4_FFDEC and TS4_FFDEC_HELPERS as in rebuild_all.ps1.
# Then:  python build_compat_package.py <same scratch>
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
$base = Join-Path $here "uicheats-base"
$gfx = Join-Path $WorkDir "gfx"
New-Item -ItemType Directory -Force $gfx | Out-Null

$cell = Join-Path $extra "CatalogImageCellView.as"
$cellClass = "widgets.BuildBuy.controls.CatalogImageCellView"

$movies = [ordered]@{
    'ClassLibraryOlympus' = $null
    'TimeControls'        = @("widgets.TimeControls.TimeControlsMain", (Join-Path $extra "TimeControlsMain.as"))
    'SimInfoTray'         = @("widgets.Gameplay.SimInfoHUD.SimInfoTray.PhoneCategoryScreen", (Join-Path $extra "PhoneCategoryScreen.as"), "widgets.Gameplay.SimInfoHUD.MotivePanel.CommodityContainer", (Join-Path $extra "CommodityContainer.as"))
    'SimInfoMotivePanel'  = @("widgets.Gameplay.SimInfoHUD.MotivePanel.CommodityContainer", (Join-Path $extra "CommodityContainer.as"))
    # UIC v1.59.1 grew its override set: SimHub (our mood narration) and
    # PickersPurchase (our purchase-cart narration) now collide too.
    'SimHub'              = @("widgets.Gameplay.SimHub.controls.MoodContainer", (Join-Path $extra "MoodContainer.as"))
    'PickersPurchase'     = @("widgets.Pickers.controls.PurchasePicker.PurchasePickerCellView", (Join-Path $extra "PurchasePickerCellView.as"), "widgets.Pickers.PickersPurchaseMain", (Join-Path $extra "PickersPurchaseMain.as"))
}

$batchClasses = Get-A11yHelpers
$useBatch = Test-Path -LiteralPath (Join-Path $batchClasses 'ReplaceScriptsBatch.class')
if ($useBatch) { Write-Output ("compiler: ReplaceScriptsBatch helper in " + $batchClasses) }
else { Write-Output ("compiler: ffdec -replace per movie (no ReplaceScriptsBatch.class in " + $batchClasses + ")") }
$batchRows = New-Object 'System.Collections.Generic.List[string]'
foreach ($name in $movies.Keys) {
    $baseFile = Join-Path $base ("uic_" + $name + ".swf")
    if (-not (Test-Path $baseFile)) { throw "missing UI Cheats base: $baseFile" }
    # UTF-8 explicitly, as in rebuild_all.ps1 (PowerShell 5.1 defaults to ANSI).
    $src = (Get-Content $template -Raw -Encoding UTF8) -replace 'A11YLIBNAME', $name
    $ttm = Join-Path $gfx ("ttm_compat_" + $name + ".as")
    [System.IO.File]::WriteAllText($ttm, $src)
    $out = Join-Path $gfx ("compat_" + $name + ".swf")
    if (Test-Path $out) { Remove-Item $out -Force }
    $baseText = [System.Text.Encoding]::ASCII.GetString([System.IO.File]::ReadAllBytes($baseFile))
    $args = @('-jar', $ffdec, '-replace', $baseFile, $out)
    if ($baseText.Contains('TooltipManager')) { $args += @('olympus.core.TooltipManager', $ttm) }
    if ($baseText.Contains('CatalogImageCellView')) { $args += @($cellClass, $cell) }
    if ($movies[$name]) { $args += $movies[$name] }
    if ($args.Count -le 5) { throw "NOTHING TO PATCH in $name" }
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
    Write-Output ("OK  compat " + $name)
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
        $out = Join-Path $gfx ("compat_" + $name + '.swf')
        if (-not (Test-Path $out)) { throw "NO OUTPUT PRODUCED: $name" }
        $magic = [System.Text.Encoding]::ASCII.GetString([System.IO.File]::ReadAllBytes($out)[0..2])
        if ($magic -ne 'GFX') { throw "BAD OUTPUT ($magic): $name" }
    }
}
Write-Output "all compat movies rebuilt"
