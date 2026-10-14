# Updater core: install into a fake Sims folder, duplicates, speech pack,
# script mods, unsafe zips, checksum checks and the GitHub release lookup
# (network calls are replaced with local stand-ins). Run with Windows PowerShell.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
. (Join-Path $root 'helper\ScreenReaderHelper.Core.ps1')
. (Join-Path $root 'helper\TS4AccessUpdater.Core.ps1')
function Assert-HelperGameClosed { }   # the test must not depend on the real game
$checks = 0
function Check($condition, $message) { if (-not $condition) { throw ('FAILED: ' + $message) }; $script:checks = $script:checks + 1 }

$work = Join-Path ([IO.Path]::GetTempPath()) ('ts4updater-test-' + [Guid]::NewGuid().ToString('N'))
try {
    # A package like publish_github_release.ps1 makes.
    $package = Join-Path $work 'package'
    $modSource = Join-Path $package 'Mods\TS4_Access'
    $speechSource = Join-Path $package 'Mods\TS4_Access_SpeechPack'
    [void][IO.Directory]::CreateDirectory($modSource); [void][IO.Directory]::CreateDirectory((Join-Path $speechSource 'LICENSES'))
    [IO.File]::WriteAllText((Join-Path $modSource 'TS4_Access.ts4script'), 'new script')
    [IO.File]::WriteAllText((Join-Path $modSource 'TS4_Access_UI.package'), 'new package')
    [IO.File]::WriteAllText((Join-Path $modSource 'CONTROLS.txt'), 'controls')
    [IO.File]::WriteAllText((Join-Path $speechSource 'prism.dll'), 'prism')
    [IO.File]::WriteAllText((Join-Path $speechSource 'LICENSES\prism.txt'), 'licence')

    # 1. Mod at the Mods root plus an extra copy in a subfolder; no speech pack; mods off.
    $user = Join-Path $work 'The Sims 4'
    $mods = Join-Path $user 'Mods'
    [void][IO.Directory]::CreateDirectory((Join-Path $mods 'Old TS4 Access'))
    [IO.File]::WriteAllText((Join-Path $user 'Options.ini'), "[options]`r`nmodsdisabled = 1`r`nscriptmodsenabled = 0`r`n")
    [IO.File]::WriteAllText((Join-Path $mods 'TS4_Access.ts4script'), 'old script')
    [IO.File]::WriteAllText((Join-Path $mods 'TS4_Access_UI.package'), 'old package')
    [IO.File]::WriteAllText((Join-Path $mods 'Old TS4 Access\TS4_Access.ts4script'), 'stale copy')
    $result = Install-UpdaterPackage -UserFolder $user -Package $package -Tag 'build-1'
    Check ($result.ModFolder -eq $mods) 'installs where the mod already was'
    Check ([IO.File]::ReadAllText((Join-Path $mods 'TS4_Access.ts4script')) -eq 'new script') 'script replaced'
    Check ([IO.File]::ReadAllText((Join-Path $mods 'TS4_Access_UI.package')) -eq 'new package') 'package replaced'
    Check (-not [IO.File]::Exists((Join-Path $mods 'Old TS4 Access\TS4_Access.ts4script'))) 'extra copy removed so the game loads one'
    Check ($result.ExtraCopiesRemoved -eq 1) 'extra copy reported'
    Check ([IO.File]::ReadAllText((Join-Path $result.Backup 'TS4_Access.ts4script')) -eq 'old script') 'old files backed up'
    Check ([IO.File]::ReadAllText((Join-Path $result.Backup 'extra-copy-1\TS4_Access.ts4script')) -eq 'stale copy') 'extra copy kept in the backup'
    Check ($result.SpeechPack -eq 'installed' -and [IO.File]::Exists((Join-Path $mods 'TS4_Access_SpeechPack\LICENSES\prism.txt'))) 'speech pack installed with its licences'
    Check ($result.ScriptModsChanged) 'script mods turned on'
    $ini = [IO.File]::ReadAllText((Join-Path $user 'Options.ini'))
    Check ($ini -match 'modsdisabled = 0' -and $ini -match 'scriptmodsenabled = 1') 'Options.ini enabled by the helper code'
    Check ((Get-UpdaterInstalledTag -UserFolder $user) -eq 'build-1') 'installed build recorded'

    # 2. Second run: speech pack refreshed in place, nothing else to back up twice.
    $again = Install-UpdaterPackage -UserFolder $user -Package $package -Tag 'build-2'
    Check ($again.SpeechPack -eq 'updated' -and $again.ExtraCopiesRemoved -eq 0 -and -not $again.ScriptModsChanged) 'second install is a plain update'
    Check ((Get-UpdaterInstalledTag -UserFolder $user) -eq 'build-2') 'record updated'

    # 3. Fresh player: mod goes to Mods\TS4_Access; speech pack inside the mod folder is found.
    $fresh = Join-Path $work 'Fresh\The Sims 4'
    [void][IO.Directory]::CreateDirectory((Join-Path $fresh 'Mods\TS4_Access\TS4_Access_SpeechPack'))
    [IO.File]::WriteAllText((Join-Path $fresh 'Options.ini'), "[options]`r`n")
    $new = Install-UpdaterPackage -UserFolder $fresh -Package $package -Tag 'build-1'
    Check ($new.ModFolder -eq (Join-Path $fresh 'Mods\TS4_Access') -and $null -eq $new.Backup) 'new installs go to Mods\TS4_Access'
    Check ($new.SpeechPack -eq 'updated' -and -not [IO.Directory]::Exists((Join-Path $fresh 'Mods\TS4_Access_SpeechPack'))) 'existing speech pack location reused, no second copy'

    # 4. No Options.ini: refuses.
    $nowhere = Join-Path $work 'Nowhere'; [void][IO.Directory]::CreateDirectory($nowhere)
    $refused = $false; try { Install-UpdaterPackage -UserFolder $nowhere -Package $package } catch { $refused = $_.Exception.Message -match 'Options.ini' }
    Check $refused 'needs the Sims folder'

    # 5. Zips: a good one unpacks; one escaping its folder and one missing the mod are refused.
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $good = Join-Path $work 'good.zip'
    [IO.Compression.ZipFile]::CreateFromDirectory($package, $good)
    Expand-UpdaterPackage -Zip $good -Destination (Join-Path $work 'unpacked')
    Check ([IO.File]::Exists((Join-Path $work 'unpacked\Mods\TS4_Access\TS4_Access.ts4script'))) 'good zip unpacks'
    $evil = Join-Path $work 'evil.zip'
    $archive = [IO.Compression.ZipFile]::Open($evil, 'Create')
    try { $entry = $archive.CreateEntry('..\..\escaped.txt'); $writer = New-Object IO.StreamWriter($entry.Open()); $writer.Write('x'); $writer.Dispose() } finally { $archive.Dispose() }
    $refused = $false; try { Expand-UpdaterPackage -Zip $evil -Destination (Join-Path $work 'evil') } catch { $refused = $_.Exception.Message -match 'unsafe' }
    Check ($refused -and -not [IO.File]::Exists((Join-Path $work 'escaped.txt'))) 'unsafe paths refused'
    $empty = Join-Path $work 'empty.zip'
    $archive = [IO.Compression.ZipFile]::Open($empty, 'Create'); $archive.Dispose()
    $refused = $false; try { Expand-UpdaterPackage -Zip $empty -Destination (Join-Path $work 'empty') } catch { $refused = $_.Exception.Message -match 'missing' }
    Check $refused 'a package without the mod is refused'

    # 6. Release lookup and download, with GitHub replaced by local files.
    $script:release = [pscustomobject]@{ tag_name='build-9'; name='Build 9'; published_at='2026-10-14'; body='notes'
        assets=@([pscustomobject]@{ name='TS4_Access_Update.zip'; browser_download_url='zip'; size=1234 },
                 [pscustomobject]@{ name='TS4_Access_Update.zip.sha256'; browser_download_url='sha'; size=64 }) }
    $script:hash = Get-UpdaterFileHash $good
    function Invoke-RestMethod { param([switch]$UseBasicParsing,$Headers,$Uri) Check ($Uri -eq 'https://api.github.com/repos/LeonianUniverse478/Sims4Access/releases/latest') 'asks GitHub for the latest release'; return $script:release }
    function Invoke-WebRequest { param([switch]$UseBasicParsing,$Headers,$Uri,$OutFile)
        if ($Uri -eq 'zip') { [IO.File]::Copy($good, $OutFile, $true); return }
        # Like GitHub: asset bodies are bytes, so callers must save them to a file.
        if (-not $OutFile) { return [pscustomobject]@{ Content = [Text.Encoding]::ASCII.GetBytes($script:hash) } }
        [IO.File]::WriteAllBytes($OutFile, [Text.Encoding]::ASCII.GetBytes($script:hash + "  TS4_Access_Update.zip`n")) }
    $latest = Get-UpdaterRelease -Repo 'LeonianUniverse478/Sims4Access'
    Check ($latest.Tag -eq 'build-9' -and $latest.ZipUrl -eq 'zip' -and $latest.Size -eq 1234) 'release parsed'
    $updated = Update-TS4Access -UserFolder $user -Repo 'LeonianUniverse478/Sims4Access'
    Check ($updated.Tag -eq 'build-9' -and (Get-UpdaterInstalledTag -UserFolder $user) -eq 'build-9') 'download, check and install'
    $script:hash = ('0' * 64)
    [IO.File]::WriteAllText((Join-Path $mods 'TS4_Access.ts4script'), 'kept')
    $refused = $false; try { Update-TS4Access -UserFolder $user -Repo 'LeonianUniverse478/Sims4Access' } catch { $refused = $_.Exception.Message -match 'checksum' }
    Check ($refused -and [IO.File]::ReadAllText((Join-Path $mods 'TS4_Access.ts4script')) -eq 'kept') 'a bad checksum installs nothing'
    $script:release.assets = @($script:release.assets[0])
    $refused = $false; try { Get-UpdaterRelease -Repo 'LeonianUniverse478/Sims4Access' } catch { $refused = $_.Exception.Message -match 'no update package' }
    Check $refused 'a release without the hash file is refused'
    $refused = $false; try { Get-UpdaterRelease -Repo 'bad repo/x;y' } catch { $refused = $_.Exception.Message -match 'invalid' }
    Check $refused 'repository name is validated'
} finally {
    if ([IO.Directory]::Exists($work)) { Remove-Item -LiteralPath $work -Recurse -Force }
}
Write-Output ("$checks updater checks passed")
