# File operations for the TS4 Access helper. No action on import.
Set-StrictMode -Version 2

function Read-HelperIni {
    param([Parameter(Mandatory=$true)][string]$Path)
    [byte[]]$bytes = [IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -gt 8388608) { throw 'Options.ini is unexpectedly large. No changes were made.' }
    $skip = 0
    $encoding = New-Object Text.UTF8Encoding($false, $true)
    if ($bytes.Length -ge 4 -and $bytes[0] -eq 255 -and $bytes[1] -eq 254 -and $bytes[2] -eq 0 -and $bytes[3] -eq 0) {
        $encoding = New-Object Text.UTF32Encoding($false, $true, $true); $skip = 4
    } elseif ($bytes.Length -ge 4 -and $bytes[0] -eq 0 -and $bytes[1] -eq 0 -and $bytes[2] -eq 254 -and $bytes[3] -eq 255) {
        $encoding = New-Object Text.UTF32Encoding($true, $true, $true); $skip = 4
    } elseif ($bytes.Length -ge 3 -and $bytes[0] -eq 239 -and $bytes[1] -eq 187 -and $bytes[2] -eq 191) {
        $skip = 3
    } elseif ($bytes.Length -ge 2 -and $bytes[0] -eq 255 -and $bytes[1] -eq 254) {
        $encoding = New-Object Text.UnicodeEncoding($false, $true, $true); $skip = 2
    } elseif ($bytes.Length -ge 2 -and $bytes[0] -eq 254 -and $bytes[1] -eq 255) {
        $encoding = New-Object Text.UnicodeEncoding($true, $true, $true); $skip = 2
    }
    try { $text = $encoding.GetString($bytes, $skip, $bytes.Length - $skip) }
    catch {
        if ($skip -ne 0) { throw 'Options.ini has invalid text encoding. No changes were made.' }
        $encoding = [Text.Encoding]::GetEncoding(1252)
        $text = $encoding.GetString($bytes)
    }
    if ($text.IndexOf([char]0) -ge 0) { throw 'Options.ini is not a valid text file. No changes were made.' }
    [byte[]]$preamble = @()
    if ($skip -gt 0) { $preamble = $bytes[0..($skip - 1)] }
    [byte[]]$roundtrip = @($preamble) + @($encoding.GetBytes($text))
    if ([Convert]::ToBase64String($roundtrip) -ne [Convert]::ToBase64String($bytes)) {
        throw 'Options.ini encoding cannot be preserved. No changes were made.'
    }
    [pscustomobject]@{ Bytes=$bytes; Text=$text; Encoding=$encoding; Preamble=$preamble }
}

function ConvertTo-EnabledModOptions {
    param([AllowEmptyString()][string]$Text)
    $newline = "`r`n"
    $firstEnding = [regex]::Match($Text, '\r\n|\n|\r')
    if ($firstEnding.Success) { $newline = $firstEnding.Value }
    $headerPattern = '(?i)(?:\A|(?<=[\r\n]))[ \t]*\[options\][ \t]*(?:[;#][^\r\n]*)?(?:\r\n|\n|\r|$)'
    $headers = [regex]::Matches($Text, $headerPattern)
    if ($headers.Count -gt 1) { throw 'Options.ini contains more than one options section. No changes were made.' }
    if ($headers.Count -eq 0) {
        $separator = ''
        if ($Text.Length -gt 0 -and $Text -notmatch '[\r\n]$') { $separator = $newline }
        return $Text + $separator + '[options]' + $newline + 'modsdisabled = 0' + $newline + 'scriptmodsenabled = 1' + $newline
    }
    $start = $headers[0].Index + $headers[0].Length
    $next = [regex]::Match($Text.Substring($start), '(?:\A|(?<=[\r\n]))[ \t]*\[')
    $end = $Text.Length
    if ($next.Success) { $end = $start + $next.Index }
    $body = $Text.Substring($start, $end - $start)
    foreach ($key in @('modsdisabled', 'scriptmodsenabled')) {
        $value = if ($key -eq 'modsdisabled') { '0' } else { '1' }
        $pattern = '(?i)(?:\A|(?<=[\r\n]))([ \t]*' + $key + '[ \t]*=[ \t]*)([^\r\n;#]*?)([ \t]*(?:[;#][^\r\n]*)?)(?=[\r\n]|\z)'
        if ([regex]::IsMatch($body, $pattern)) {
            $replacement = '${1}' + $value + '${3}'
            $body = [regex]::Replace($body, $pattern, $replacement)
        } else {
            if ($body.Length -gt 0 -and $body -notmatch '[\r\n]$') { $body += $newline }
            $body += $key + ' = ' + $value + $newline
        }
    }
    $prefix = $Text.Substring(0, $start)
    if ($prefix -notmatch '[\r\n]$') { $prefix += $newline }
    return $prefix + $body + $Text.Substring($end)
}

function Assert-HelperGameClosed {
    $processes = @(Get-Process -Name TS4_x64,TS4_DX9_x64,TS4 -ErrorAction SilentlyContinue)
    if ($processes.Count -gt 0) { throw 'The Sims 4 is running. Close the game, then try again. No settings were changed.' }
}

function Enable-HelperMods {
    param([Parameter(Mandatory=$true)][string]$UserFolder)
    Assert-HelperGameClosed
    $folder = [IO.Path]::GetFullPath($UserFolder)
    $path = Join-Path $folder 'Options.ini'
    if (-not [IO.File]::Exists($path)) {
        throw 'Options.ini was not found. Choose the Sims user folder that contains it. If the game has never been run, start it once and exit first.'
    }
    $document = Read-HelperIni -Path $path
    $updated = ConvertTo-EnabledModOptions -Text $document.Text
    if ($updated -ceq $document.Text) {
        return [pscustomobject]@{ Changed=$false; BackupPath=$null; OptionsPath=$path }
    }
    if (([IO.File]::GetAttributes($path) -band [IO.FileAttributes]::ReadOnly) -ne 0) {
        throw 'Options.ini is read-only. Remove its read-only setting, then try again.'
    }
    [byte[]]$newBytes = @($document.Preamble) + @($document.Encoding.GetBytes($updated))
    $backupFolder = Join-Path $folder 'TS4 Access Backups'
    [void][IO.Directory]::CreateDirectory($backupFolder)
    $id = [DateTime]::Now.ToString('yyyyMMdd-HHmmss-fff') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,8)
    $backup = Join-Path $backupFolder ('Options-' + $id + '.ini')
    $temp = Join-Path $folder ('Options.TS4Access-' + $id + '.tmp')
    try {
        [IO.File]::WriteAllBytes($temp, $newBytes)
        Assert-HelperGameClosed
        $current = [IO.File]::ReadAllBytes($path)
        if ([Convert]::ToBase64String($current) -ne [Convert]::ToBase64String($document.Bytes)) {
            throw 'Options.ini changed while the helper was working. Try again after the game has closed.'
        }
        # Replace is atomic on the same volume and creates the exact old-file backup.
        [IO.File]::Replace($temp, $path, $backup)
        if ([Convert]::ToBase64String([IO.File]::ReadAllBytes($path)) -ne [Convert]::ToBase64String($newBytes)) {
            throw ('Settings verification failed. Your original file is backed up at ' + $backup)
        }
    } finally {
        if ([IO.File]::Exists($temp)) { [IO.File]::Delete($temp) }
    }
    [pscustomobject]@{ Changed=$true; BackupPath=$backup; OptionsPath=$path }
}

function Find-HelperUserFolder {
    param([string]$StartFolder,
          [string]$DocumentsFolder = [Environment]::GetFolderPath('MyDocuments'))
    $folder = [IO.Path]::GetFullPath($StartFolder)
    for ($i=0; $i -lt 8; $i++) {
        if ([IO.Path]::GetFileName($folder) -ieq 'Mods') {
            $candidate = [IO.Path]::GetDirectoryName($folder)
            if ([IO.File]::Exists((Join-Path $candidate 'Options.ini'))) { return $candidate }
        }
        $parent = [IO.Path]::GetDirectoryName($folder)
        if (-not $parent -or $parent -eq $folder) { break }
        $folder = $parent
    }
    # Windows resolves redirected Documents (including OneDrive). The install
    # location and launcher are irrelevant: both EA and Steam use user files.
    if (-not $DocumentsFolder) { return $null }
    try {
        $ea = Join-Path $DocumentsFolder 'Electronic Arts'
        if ([IO.Directory]::Exists($ea)) {
            $found = @([IO.Directory]::GetDirectories($ea) | Where-Object {
                [IO.Path]::GetFileName($_) -match '(?i)(?:^| )Sims 4$' -and
                [IO.File]::Exists((Join-Path $_ 'Options.ini'))
            })
            if ($found.Count -eq 1) { return $found[0] }
        }
    } catch { return $null } # Manual selection remains available if Documents is inaccessible.
    return $null
}

function Get-HelperStatus {
    param([string]$UserFolder)
    $found=$false; $enabled=$false; $errorText=$null
    try {
        if ($UserFolder) {
            $path=Join-Path $UserFolder 'Options.ini'
            $found=[IO.File]::Exists($path)
            if ($found) {
                $options=(Read-HelperIni -Path $path).Text
                $enabled=((ConvertTo-EnabledModOptions -Text $options) -ceq $options)
            }
        }
    } catch { $errorText=$_.Exception.Message }
    [pscustomobject]@{ UserFolder=$UserFolder; OptionsFound=$found; ModsEnabled=$enabled; Error=$errorText }
}
