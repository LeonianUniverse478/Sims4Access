# Full Flash pipeline for this tree: rebuild -> gate -> package -> compat.
# Usage: powershell -ExecutionPolicy Bypass -File flash\chain.ps1 [-Tag name]
# Writes flash\chain-<tag>.log and ends with CHAIN DONE or CHAIN FAILED.
# Never run two of these at once (the gate exports pcode into the work dir).
param([string]$Tag = "run", [switch]$SkipRebuild, [string]$Work = "work-1.128.90")
$ErrorActionPreference = 'Continue'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
$work = Join-Path $here $Work
$compat = Join-Path $here "work-compat"
$log = Join-Path $here ("chain-" + $Tag + ".log")
$build = Join-Path $root "build"
New-Item -ItemType Directory -Force $build | Out-Null
# FFDec needs a writable configuration folder even for command-line builds.
# Keep it within this integration tree instead of the desktop app profile.
$env:APPDATA = Join-Path $build "ffdec-appdata"
New-Item -ItemType Directory -Force $env:APPDATA | Out-Null

function Say($msg) { $line = (Get-Date -Format s) + " " + $msg; Add-Content -Path $log -Value $line -Encoding utf8; }
function Fail($msg) { Say ("FAIL: " + $msg); Say "CHAIN FAILED"; exit 1 }

Set-Content -Path $log -Value ((Get-Date -Format s) + " chain start") -Encoding utf8

# stale pcode from a previous gate would be skipped by gate_pcode; clear the new_* exports
$pcodeRoot = [System.IO.Path]::GetFullPath((Join-Path $work "pcode"))
Get-ChildItem -LiteralPath $pcodeRoot -Directory -Filter "new_*" -ErrorAction SilentlyContinue | ForEach-Object {
    $target = [System.IO.Path]::GetFullPath($_.FullName)
    if (-not $target.StartsWith($pcodeRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) { Fail "pcode cleanup escaped work directory" }
    if ($_.Attributes -band [System.IO.FileAttributes]::ReparsePoint) { Fail "pcode cleanup target is a link" }
    Remove-Item -LiteralPath $target -Recurse -Force -ErrorAction Stop
}

if (-not $SkipRebuild) {
Say "rebuild_all"
& powershell -ExecutionPolicy Bypass -File (Join-Path $here "rebuild_all.ps1") -WorkDir $work 2>&1 | ForEach-Object { $_.ToString() } | Add-Content -Path $log -Encoding utf8
if ($LASTEXITCODE -ne 0) { Fail "rebuild_all exited with $LASTEXITCODE" }
$tail = Get-Content $log -Tail 3
if (-not ($tail -match "all movies rebuilt")) { Fail "rebuild_all did not report all movies rebuilt" }
} else { Say "rebuild skipped (-SkipRebuild)" }

Say "gate_pcode"
& py -3.7 (Join-Path $here "gate_pcode.py") $work 2>&1 | ForEach-Object { $_.ToString() } | Add-Content -Path $log -Encoding utf8
if ($LASTEXITCODE -ne 0) { Fail "gate exited with $LASTEXITCODE" }
if (-not ((Get-Content $log -Raw) -match "fidelity gate PASSED")) { Fail "gate did not print PASSED" }

Say "build_ui_package"
$pkg = Join-Path $build "tyjokr_ScreenReader_UI.package"
& py -3.7 (Join-Path $here "build_ui_package.py") $work $pkg 2>&1 | ForEach-Object { $_.ToString() } | Add-Content -Path $log -Encoding utf8
if ($LASTEXITCODE -ne 0) { Fail "package build exited with $LASTEXITCODE" }
if (-not (Test-Path $pkg)) { Fail "package missing" }
Say ("package bytes " + (Get-Item $pkg).Length)

Say "build_uicheats_compat"
& powershell -ExecutionPolicy Bypass -File (Join-Path $here "build_uicheats_compat.ps1") -WorkDir $compat 2>&1 | ForEach-Object { $_.ToString() } | Add-Content -Path $log -Encoding utf8
if ($LASTEXITCODE -ne 0) { Fail "compat rebuild exited with $LASTEXITCODE" }
$cpkg = Join-Path $build "tyjokr_ScreenReader_Compatibility_UICheats.package"
& py -3.7 (Join-Path $here "build_compat_package.py") $compat $cpkg 2>&1 | ForEach-Object { $_.ToString() } | Add-Content -Path $log -Encoding utf8
if ($LASTEXITCODE -ne 0) { Fail "compat package build exited with $LASTEXITCODE" }
if (-not (Test-Path $cpkg)) { Fail "compat package missing" }
Say ("compat bytes " + (Get-Item $cpkg).Length)

Say "CHAIN DONE"
exit 0
