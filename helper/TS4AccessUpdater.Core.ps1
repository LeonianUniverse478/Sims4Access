# TS4 Access updater core. Embedded in TS4AccessUpdater.exe together with
# ScreenReaderHelper.Core.ps1 (Find-HelperUserFolder, Enable-HelperMods,
# Assert-HelperGameClosed). Builds come from the latest GitHub release of the
# repository: an update zip plus its SHA-256 file, made by
# tools/publish_github_release.ps1.

$UpdaterZipName = 'TS4_Access_Update.zip'
$UpdaterModFiles = @('TS4_Access.ts4script','TS4_Access_UI.package')

function Get-UpdaterRelease {
    param([Parameter(Mandatory=$true)][string]$Repo)
    if ($Repo -notmatch '^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$') { throw 'The updater has an invalid GitHub repository name.' }
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $headers = @{ 'User-Agent'='TS4AccessUpdater'; 'Accept'='application/vnd.github+json' }
    try {
        $release = Invoke-RestMethod -UseBasicParsing -Headers $headers -Uri ('https://api.github.com/repos/' + $Repo + '/releases/latest')
    } catch {
        # GitHub answers 404 when the repository has no published release.
        $response = $_.Exception.Response
        if ($response -ne $null -and [int]$response.StatusCode -eq 404) { throw 'No TS4 Access build has been published yet. Try again later.' }
        throw ('Could not reach GitHub to check for updates. Check your internet connection and try again. (' + $_.Exception.Message + ')')
    }
    $zip = @($release.assets | Where-Object { $_.name -eq $UpdaterZipName })
    $sha = @($release.assets | Where-Object { $_.name -eq ($UpdaterZipName + '.sha256') })
    if ($zip.Count -ne 1 -or $sha.Count -ne 1) { throw ('The latest release (' + $release.tag_name + ') has no update package yet.') }
    [pscustomobject]@{
        Tag = [string]$release.tag_name
        Name = [string]$release.name
        Published = [string]$release.published_at
        Notes = [string]$release.body
        ZipUrl = [string]$zip[0].browser_download_url
        ShaUrl = [string]$sha[0].browser_download_url
        Size = [long]$zip[0].size
    }
}

function Get-UpdaterInstalledTag {
    param([Parameter(Mandatory=$true)][string]$UserFolder)
    $path = Join-Path $UserFolder 'TS4 Access Backups\installed-release.txt'
    if ([IO.File]::Exists($path)) { return ([IO.File]::ReadAllText($path)).Trim() }
    return ''
}

# Mod and speech pack locations. The game loads scripts at most one folder
# below Mods, so only Mods and its direct subfolders are searched.
function Find-UpdaterModFolders {
    param([Parameter(Mandatory=$true)][string]$Mods)
    $found = @()
    if ([IO.File]::Exists((Join-Path $Mods 'TS4_Access.ts4script'))) { $found += $Mods }
    if ([IO.Directory]::Exists($Mods)) {
        foreach ($dir in [IO.Directory]::GetDirectories($Mods)) {
            if ([IO.File]::Exists((Join-Path $dir 'TS4_Access.ts4script'))) { $found += $dir }
        }
    }
    return ,$found
}

function Find-UpdaterSpeechPack {
    param([Parameter(Mandatory=$true)][string]$Mods)
    if (-not [IO.Directory]::Exists($Mods)) { return $null }
    $direct = Join-Path $Mods 'TS4_Access_SpeechPack'
    if ([IO.Directory]::Exists($direct)) { return $direct }
    foreach ($dir in [IO.Directory]::GetDirectories($Mods)) {
        $inner = Join-Path $dir 'TS4_Access_SpeechPack'
        if ([IO.Directory]::Exists($inner)) { return $inner }
    }
    return $null
}

function Get-UpdaterFileHash {
    param([Parameter(Mandatory=$true)][string]$Path)
    $sha = [Security.Cryptography.SHA256]::Create()
    $stream = [IO.File]::OpenRead($Path)
    try { return ([BitConverter]::ToString($sha.ComputeHash($stream)) -replace '-','').ToLowerInvariant() }
    finally { $stream.Dispose(); $sha.Dispose() }
}

# Unpacks the update zip into a new folder, refusing anything outside it and
# requiring the mod's two game files.
function Expand-UpdaterPackage {
    param([Parameter(Mandatory=$true)][string]$Zip, [Parameter(Mandatory=$true)][string]$Destination)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $root = [IO.Path]::GetFullPath($Destination).TrimEnd('\') + '\'
    $archive = [IO.Compression.ZipFile]::OpenRead($Zip)
    try {
        foreach ($entry in $archive.Entries) {
            $target = [IO.Path]::GetFullPath((Join-Path $root $entry.FullName))
            if (-not $target.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) { throw 'The update package is damaged (unsafe file path). Nothing was installed.' }
            if ($entry.Name -eq '') { [void][IO.Directory]::CreateDirectory($target); continue }
            [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target))
            [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $target, $true)
        }
    } finally { $archive.Dispose() }
    foreach ($file in $UpdaterModFiles) {
        if (-not [IO.File]::Exists((Join-Path $root ('Mods\TS4_Access\' + $file)))) { throw ('The update package is missing ' + $file + '. Nothing was installed.') }
    }
}

# Installs an unpacked package into the user's Mods folder:
#  - the mod goes where it already is (one place; extra copies are moved to
#    the backup so the game never loads two), or Mods\TS4_Access if new;
#  - the old mod files are backed up first;
#  - the speech pack is added if missing, or refreshed where it is;
#  - script mods are enabled with the helper's own code.
function Install-UpdaterPackage {
    param([Parameter(Mandatory=$true)][string]$UserFolder, [Parameter(Mandatory=$true)][string]$Package, [string]$Tag = '')
    Assert-HelperGameClosed
    $user = [IO.Path]::GetFullPath($UserFolder)
    if (-not [IO.File]::Exists((Join-Path $user 'Options.ini'))) { throw 'Options.ini was not found in the Sims folder. Choose the Sims user folder that contains it.' }
    $mods = Join-Path $user 'Mods'
    [void][IO.Directory]::CreateDirectory($mods)
    $source = Join-Path $Package 'Mods\TS4_Access'
    $folders = Find-UpdaterModFolders -Mods $mods
    $target = if ($folders.Count -gt 0) { $folders[0] } else { Join-Path $mods 'TS4_Access' }
    $stamp = [DateTime]::Now.ToString('yyyy-MM-dd_HHmmss')
    $backup = Join-Path $user ('TS4 Access Backups\mod-before-update-' + $stamp)
    if ($folders.Count -gt 0) {
        [void][IO.Directory]::CreateDirectory($backup)
        $i = 0
        foreach ($folder in $folders) {
            $into = if ($i -eq 0) { $backup } else { Join-Path $backup ('extra-copy-' + $i) }
            [void][IO.Directory]::CreateDirectory($into)
            foreach ($file in $UpdaterModFiles) {
                $path = Join-Path $folder $file
                if ([IO.File]::Exists($path)) {
                    if ($i -eq 0) { [IO.File]::Copy($path, (Join-Path $into $file), $true) }
                    else { [IO.File]::Copy($path, (Join-Path $into $file), $true); [IO.File]::Delete($path) }
                }
            }
            $i = $i + 1
        }
    }
    Assert-HelperGameClosed
    [void][IO.Directory]::CreateDirectory($target)
    foreach ($file in [IO.Directory]::GetFiles($source)) {
        [IO.File]::Copy($file, (Join-Path $target ([IO.Path]::GetFileName($file))), $true)
    }
    foreach ($file in $UpdaterModFiles) {
        if ((Get-UpdaterFileHash (Join-Path $target $file)) -ne (Get-UpdaterFileHash (Join-Path $source $file))) {
            throw ('Installing ' + $file + ' failed. Your previous files are backed up in ' + $backup)
        }
    }
    $speechSource = Join-Path $Package 'Mods\TS4_Access_SpeechPack'
    $speech = Find-UpdaterSpeechPack -Mods $mods
    $speechAction = 'none'
    if ([IO.Directory]::Exists($speechSource)) {
        if (-not $speech) { $speech = Join-Path $mods 'TS4_Access_SpeechPack'; $speechAction = 'installed' } else { $speechAction = 'updated' }
        foreach ($file in [IO.Directory]::GetFiles($speechSource, '*', [IO.SearchOption]::AllDirectories)) {
            $relative = $file.Substring($speechSource.Length).TrimStart('\')
            $to = Join-Path $speech $relative
            [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($to))
            [IO.File]::Copy($file, $to, $true)
        }
    }
    $scripts = Enable-HelperMods -UserFolder $user
    if ($Tag) {
        $record = Join-Path $user 'TS4 Access Backups\installed-release.txt'
        [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($record))
        [IO.File]::WriteAllText($record, $Tag)
    }
    [pscustomobject]@{
        ModFolder = $target
        Backup = $(if ($folders.Count -gt 0) { $backup } else { $null })
        ExtraCopiesRemoved = [Math]::Max(0, $folders.Count - 1)
        SpeechPack = $speechAction
        ScriptModsChanged = [bool]$scripts.Changed
        Tag = $Tag
    }
}

# Downloads the release, checks its SHA-256 against the release's own hash
# file, unpacks it and installs it. The temporary files are always removed.
function Update-TS4Access {
    param([Parameter(Mandatory=$true)][string]$UserFolder, [Parameter(Mandatory=$true)][string]$Repo)
    Assert-HelperGameClosed
    $release = Get-UpdaterRelease -Repo $Repo
    $work = Join-Path ([IO.Path]::GetTempPath()) ('TS4AccessUpdate-' + [Guid]::NewGuid().ToString('N'))
    [void][IO.Directory]::CreateDirectory($work)
    try {
        $zip = Join-Path $work $UpdaterZipName
        $headers = @{ 'User-Agent'='TS4AccessUpdater' }
        try {
            Invoke-WebRequest -UseBasicParsing -Headers $headers -Uri $release.ZipUrl -OutFile $zip
            # GitHub serves release assets as bytes (application/octet-stream),
            # so the hash file is saved and read as text, never .Content.
            $shaFile = $zip + '.sha256'
            Invoke-WebRequest -UseBasicParsing -Headers $headers -Uri $release.ShaUrl -OutFile $shaFile
            $expected = (([IO.File]::ReadAllText($shaFile)).Trim() -split '\s+')[0].ToLowerInvariant()
        } catch {
            throw ('The download did not finish. Check your internet connection and try again. Nothing was installed. (' + $_.Exception.Message + ')')
        }
        if ($expected -notmatch '^[0-9a-f]{64}$' -or (Get-UpdaterFileHash $zip) -ne $expected) {
            throw 'The downloaded update did not match its checksum, so it was not installed. Try again later.'
        }
        $package = Join-Path $work 'package'
        Expand-UpdaterPackage -Zip $zip -Destination $package
        Install-UpdaterPackage -UserFolder $UserFolder -Package $package -Tag $release.Tag
    } finally {
        if ([IO.Directory]::Exists($work)) { Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue }
    }
}
