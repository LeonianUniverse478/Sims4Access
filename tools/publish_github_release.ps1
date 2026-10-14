# Publish a TS4 Access test build as a GitHub release for TS4AccessUpdater.
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\publish_github_release.ps1 -Notes "What changed"
#   add -DryRun to build the package without uploading anything.
# The release carries TS4_Access_Update.zip, its .sha256 checksum (the updater
# refuses a download that does not match) and TS4AccessUpdater.exe.
param(
    [string]$Dist = '',
    [string]$Tag = '',
    [string]$Notes = '',
    [string]$Repo = 'LeonianUniverse478/Sims4Access',
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent

if (-not $Dist) {
    $Dist = (Get-ChildItem (Join-Path $root 'dist') -Directory | Where-Object { $_.Name -match '^\d{4}-\d{2}-\d{2}_\d{6}$' } | Sort-Object Name | Select-Object -Last 1).FullName
}
$mod = Join-Path $Dist 'main\TS4_Access'
foreach ($file in 'TS4_Access.ts4script','TS4_Access_UI.package') {
    if (-not (Test-Path -LiteralPath (Join-Path $mod $file))) { throw "The build in $Dist has no $file. Run Dev.ps1 build first." }
}
$checks = Get-Content (Join-Path $root 'build\v10-checks.json') -Raw | ConvertFrom-Json
if (-not ($checks.passed -and $checks.input_stable)) { throw 'The last build did not pass its checks. Fix and rebuild before publishing.' }
if (-not $Tag) { $Tag = 'build-' + (Split-Path $Dist -Leaf) }
if ($Tag -notmatch '^[A-Za-z0-9._-]+$') { throw "Invalid release tag: $Tag" }

$speech = Join-Path $root 'release-assets\TS4_Access_SpeechPack'
if (-not (Test-Path -LiteralPath (Join-Path $speech 'prism.dll'))) { throw "The speech pack is missing from $speech." }
foreach ($exe in 'TS4AccessHelper.exe','TS4AccessUpdater.exe') {
    if (-not (Test-Path -LiteralPath (Join-Path $root "helper\$exe"))) { throw "helper\$exe is missing. Build it first." }
}

$out = Join-Path $root ('build\release-' + $Tag)
$package = Join-Path $out 'package'
if (Test-Path -LiteralPath $out) { Remove-Item -LiteralPath $out -Recurse -Force }
New-Item -ItemType Directory -Force (Join-Path $package 'Mods'), (Join-Path $package 'TS4AccessHelper'), (Join-Path $package 'TS4AccessUpdater') | Out-Null
Copy-Item -LiteralPath $mod -Destination (Join-Path $package 'Mods') -Recurse
Copy-Item -LiteralPath $speech -Destination (Join-Path $package 'Mods') -Recurse
Copy-Item -LiteralPath (Join-Path $root 'helper\TS4AccessHelper.exe'), (Join-Path $root 'helper\README.txt') -Destination (Join-Path $package 'TS4AccessHelper')
Copy-Item -LiteralPath (Join-Path $root 'helper\TS4AccessUpdater.exe') -Destination (Join-Path $package 'TS4AccessUpdater')
Copy-Item -LiteralPath (Join-Path $root 'helper\UPDATER-README.txt') -Destination (Join-Path $package 'TS4AccessUpdater\README.txt')
Copy-Item -LiteralPath (Join-Path $root 'release-assets\INSTALL FIRST.txt') -Destination $package

# Nothing from the source kit may ride along: only compiled scripts in the mod.
Add-Type -AssemblyName System.IO.Compression.FileSystem
$script = [IO.Compression.ZipFile]::OpenRead((Join-Path $package 'Mods\TS4_Access\TS4_Access.ts4script'))
try { $loose = @($script.Entries | Where-Object { $_.Name -and $_.Name -notlike '*.pyc' }) } finally { $script.Dispose() }
if ($loose.Count -gt 0) { throw ('The mod script contains source files: ' + ($loose.FullName -join ', ')) }

$zip = Join-Path $out 'TS4_Access_Update.zip'
# Forward slashes in entry names, so every unzip tool keeps the folders.
$archive = [IO.Compression.ZipFile]::Open($zip, 'Create')
try {
    foreach ($file in Get-ChildItem -LiteralPath $package -Recurse -File) {
        $name = $file.FullName.Substring($package.Length + 1).Replace('\', '/')
        [void][IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $file.FullName, $name, [IO.Compression.CompressionLevel]::Optimal)
    }
} finally { $archive.Dispose() }
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $zip).Hash.ToLowerInvariant()
[IO.File]::WriteAllText("$zip.sha256", "$hash  TS4_Access_Update.zip`n")
$updater = Join-Path $out 'TS4AccessUpdater.exe'
Copy-Item -LiteralPath (Join-Path $root 'helper\TS4AccessUpdater.exe') -Destination $updater

if (-not $Notes) { $Notes = "TS4 Access test build $Tag. Run TS4AccessUpdater.exe with the game closed to install it." }
Write-Output "Package: $zip"
Write-Output "SHA-256: $hash"
if ($DryRun) { Write-Output 'Dry run: nothing was uploaded.'; return }

$gh = Get-Command gh -ErrorAction SilentlyContinue
if (-not $gh) { throw 'GitHub CLI (gh) is not installed.' }
& gh auth status 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'GitHub CLI is not signed in. Run: gh auth login' }
& gh release create $Tag $zip "$zip.sha256" $updater --repo $Repo --title "TS4 Access $Tag" --notes $Notes
if ($LASTEXITCODE -ne 0) { throw 'Creating the GitHub release failed.' }
Write-Output "Published $Tag to https://github.com/$Repo/releases/tag/$Tag"
