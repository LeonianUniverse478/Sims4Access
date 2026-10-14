# Offline checks for helper\ScreenReaderHelper.Core.ps1. Temporary fixtures
# only: never the real Options.ini, never the game. The game-running check
# is replaced by a fake before anything runs.
# Run: powershell -NoProfile -ExecutionPolicy Bypass -File tools\test_prelaunch_helper.ps1
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $root 'helper\ScreenReaderHelper.Core.ps1')

$script:passed = 0
$script:gameChecks = 0
$script:runningOnCall = @()
$script:onCall = $null

function Say([string]$text) { [Console]::Out.WriteLine($text) }

function Ok($condition, [string]$label) {
    if (-not $condition) { throw ('FAIL: ' + $label) }
    $script:passed++
    Say ('  ok - ' + $label)
}

function Throws([scriptblock]$block, [string]$pattern, [string]$label) {
    $message = $null
    try { & $block } catch { $message = $_.Exception.Message }
    Ok ($null -ne $message -and $message -match $pattern) ($label + ' (' + $message + ')')
}

function Same([byte[]]$a, [byte[]]$b) { [Convert]::ToBase64String($a) -eq [Convert]::ToBase64String($b) }
function Ascii([string]$text) { return ,[Text.Encoding]::ASCII.GetBytes($text) }
function Bytes([string]$path) { return ,[IO.File]::ReadAllBytes($path) }

# Fakes: resolved by name at call time, so these replace the Core versions.
function Assert-HelperGameClosed {
    $script:gameChecks++
    if ($null -ne $script:onCall) { & $script:onCall $script:gameChecks }
    if ($script:runningOnCall -contains $script:gameChecks) {
        throw 'The Sims 4 is running. Close the game, then try again. No settings were changed.'
    }
}

function Reset-Fakes { $script:gameChecks = 0; $script:runningOnCall = @(); $script:onCall = $null }

$temp = Join-Path ([IO.Path]::GetTempPath()) ('sr-helper-test-' + [Guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($temp)
function New-Folder([string]$name) {
    $path = Join-Path $temp $name
    [void][IO.Directory]::CreateDirectory($path)
    return $path
}

$CRLF = "`r`n"
$OFF = '[options]' + $CRLF + 'edgescrolling = 1' + $CRLF + $CRLF + 'showmodliststartup = 0' + $CRLF +
       'scriptmodsenabled = 0' + $CRLF + 'modsdisabled = 1' + $CRLF + 'audiooutputmode = 1' + $CRLF
$ON = $OFF.Replace('scriptmodsenabled = 0', 'scriptmodsenabled = 1').Replace('modsdisabled = 1', 'modsdisabled = 0')

try {
    Say 'converting the options text:'
    Ok ((ConvertTo-EnabledModOptions -Text $OFF) -ceq $ON) 'both flags set, every other line byte-identical, CRLF kept'
    Ok ((ConvertTo-EnabledModOptions -Text $ON) -ceq $ON) 'already on: unchanged'
    $mixed = $ON.Replace('modsdisabled = 0', 'modsdisabled = 1')
    Ok ((ConvertTo-EnabledModOptions -Text $mixed) -ceq $ON) 'only the flag that is off changes'
    $missing = '[options]' + $CRLF + 'a = 1' + $CRLF + '[other]' + $CRLF + 'modsdisabled = 1' + $CRLF
    $expected = '[options]' + $CRLF + 'a = 1' + $CRLF + 'modsdisabled = 0' + $CRLF + 'scriptmodsenabled = 1' + $CRLF +
                '[other]' + $CRLF + 'modsdisabled = 1' + $CRLF
    Ok ((ConvertTo-EnabledModOptions -Text $missing) -ceq $expected) 'missing keys appended inside [options]; another section left alone'
    $dupes = '[options]' + $CRLF + 'modsdisabled = 1' + $CRLF + 'scriptmodsenabled = 1' + $CRLF + 'modsdisabled = 1' + $CRLF
    $result = ConvertTo-EnabledModOptions -Text $dupes
    Ok ($result -ceq $dupes.Replace('modsdisabled = 1', 'modsdisabled = 0')) 'every duplicate is set'
    $tight = '[options]' + $CRLF + 'modsdisabled=1' + $CRLF + 'scriptmodsenabled=0' + $CRLF
    Ok ((ConvertTo-EnabledModOptions -Text $tight) -ceq ('[options]' + $CRLF + 'modsdisabled=0' + $CRLF + 'scriptmodsenabled=1' + $CRLF)) 'key=value without spaces keeps its style'
    $cased = '[Options]' + $CRLF + 'ModsDisabled = 1' + $CRLF + 'ScriptModsEnabled = 0' + $CRLF
    Ok ((ConvertTo-EnabledModOptions -Text $cased) -ceq ('[Options]' + $CRLF + 'ModsDisabled = 0' + $CRLF + 'ScriptModsEnabled = 1' + $CRLF)) 'key and section case kept'
    $comment = '[options]' + $CRLF + 'modsdisabled = 1 ; note' + $CRLF + 'scriptmodsenabled = 1' + $CRLF
    Ok ((ConvertTo-EnabledModOptions -Text $comment) -ceq $comment.Replace('modsdisabled = 1', 'modsdisabled = 0')) 'a trailing comment is kept'
    $lookalike = '[options]' + $CRLF + 'modsdisabledx = 1' + $CRLF + 'xmodsdisabled = 1' + $CRLF + 'modsdisabled = 1' + $CRLF + 'scriptmodsenabled = 1' + $CRLF
    $result = ConvertTo-EnabledModOptions -Text $lookalike
    Ok ($result -ceq $lookalike.Replace($CRLF + 'modsdisabled = 1', $CRLF + 'modsdisabled = 0')) 'look-alike keys untouched'
    $lf = "[options]`nmodsdisabled = 1`n"
    Ok ((ConvertTo-EnabledModOptions -Text $lf) -ceq "[options]`nmodsdisabled = 0`nscriptmodsenabled = 1`n") 'LF-only file stays LF'
    $noEnd = '[options]' + $CRLF + 'modsdisabled = 1'
    Ok ((ConvertTo-EnabledModOptions -Text $noEnd) -ceq ('[options]' + $CRLF + 'modsdisabled = 0' + $CRLF + 'scriptmodsenabled = 1' + $CRLF)) 'no final newline'
    Ok ((ConvertTo-EnabledModOptions -Text ('foo = 1' + $CRLF)) -ceq ('foo = 1' + $CRLF + '[options]' + $CRLF + 'modsdisabled = 0' + $CRLF + 'scriptmodsenabled = 1' + $CRLF)) 'no [options] section: one is added'
    Ok ((ConvertTo-EnabledModOptions -Text '') -ceq ('[options]' + $CRLF + 'modsdisabled = 0' + $CRLF + 'scriptmodsenabled = 1' + $CRLF)) 'empty text'
    Throws { ConvertTo-EnabledModOptions -Text ('[options]' + $CRLF + '[options]' + $CRLF) } 'more than one options section' 'two [options] sections refused'

    Say 'reading the file:'
    $plain = Join-Path (New-Folder 'read') 'Options.ini'
    [IO.File]::WriteAllBytes($plain, (Ascii $OFF))
    $doc = Read-HelperIni -Path $plain
    Ok ($doc.Preamble.Length -eq 0 -and $doc.Text -ceq $OFF) 'ASCII, no BOM'
    [IO.File]::WriteAllBytes($plain, [byte[]](@(239, 187, 191) + (Ascii $OFF)))
    Ok ((Read-HelperIni -Path $plain).Preamble.Length -eq 3) 'UTF-8 BOM kept as preamble'
    [IO.File]::WriteAllBytes($plain, [byte[]](@(255, 254) + [Text.Encoding]::Unicode.GetBytes($OFF)))
    Ok ((Read-HelperIni -Path $plain).Text -ceq $OFF) 'UTF-16 LE with BOM'
    [IO.File]::WriteAllBytes($plain, [byte[]]((Ascii ('[options]' + $CRLF + 'name = Caf')) + @(233) + (Ascii ($CRLF + 'modsdisabled = 1' + $CRLF))))
    Ok ((Read-HelperIni -Path $plain).Text.Contains('Caf' + [char]233)) 'a Windows-1252 byte falls back and round-trips'
    [IO.File]::WriteAllBytes($plain, [byte[]]((Ascii '[options]') + @(0) + (Ascii $CRLF)))
    Throws { Read-HelperIni -Path $plain } 'not a valid text file' 'NUL bytes refused'

    Say 'enabling on disk:'
    $user = New-Folder 'user'
    $options = Join-Path $user 'Options.ini'
    $backups = Join-Path $user 'TS4 Access Backups'
    [byte[]]$original = Ascii $OFF
    [IO.File]::WriteAllBytes($options, $original)
    Reset-Fakes
    $r = Enable-HelperMods -UserFolder $user
    Ok ($r.Changed -and (Same (Bytes $options) (Ascii $ON))) 'written with exactly the expected bytes'
    Ok ($script:gameChecks -eq 2) 'game checked before reading and again before replacing'
    Ok ((Same (Bytes $r.BackupPath) $original) -and $r.BackupPath.StartsWith($backups)) 'backup holds the original bytes'
    Ok (@(Get-ChildItem -LiteralPath $user -Filter '*.tmp').Count -eq 0) 'no temporary file left'
    Reset-Fakes
    $again = Enable-HelperMods -UserFolder $user
    Ok ((-not $again.Changed) -and @(Get-ChildItem -LiteralPath $backups).Count -eq 1) 'second run changes nothing and writes no backup'

    [IO.File]::WriteAllBytes($options, $original)
    Reset-Fakes; $script:runningOnCall = @(1)
    Throws { Enable-HelperMods -UserFolder $user } 'running' 'game running at the start: refused'
    Ok ((Same (Bytes $options) $original) -and @(Get-ChildItem -LiteralPath $backups).Count -eq 1) 'nothing changed, no new backup'
    Reset-Fakes; $script:runningOnCall = @(2)
    Throws { Enable-HelperMods -UserFolder $user } 'running' 'game started while working: refused'
    Ok ((Same (Bytes $options) $original) -and @(Get-ChildItem -LiteralPath $user -Filter '*.tmp').Count -eq 0) 'original kept, temporary file removed'
    Reset-Fakes
    $script:onCall = { param($n) if ($n -eq 2) { [IO.File]::WriteAllBytes($options, (Ascii ($OFF + 'late = 1' + $CRLF))) } }
    Throws { Enable-HelperMods -UserFolder $user } 'changed while' 'file changed by someone else: refused'
    Ok ((Same (Bytes $options) (Ascii ($OFF + 'late = 1' + $CRLF))) -and @(Get-ChildItem -LiteralPath $user -Filter '*.tmp').Count -eq 0) 'their version kept'

    [IO.File]::WriteAllBytes($options, $original)
    [IO.File]::SetAttributes($options, [IO.FileAttributes]::ReadOnly)
    Reset-Fakes
    Throws { Enable-HelperMods -UserFolder $user } 'read-only' 'read-only file: refused'
    [IO.File]::SetAttributes($options, [IO.FileAttributes]::Normal)
    Ok (Same (Bytes $options) $original) 'read-only file unchanged'
    Reset-Fakes
    Throws { Enable-HelperMods -UserFolder (New-Folder 'empty') } 'was not found' 'missing Options.ini explained'

    [IO.File]::WriteAllBytes($options, [byte[]](@(239, 187, 191) + (Ascii $OFF)))
    Reset-Fakes
    [void](Enable-HelperMods -UserFolder $user)
    Ok (Same (Bytes $options) ([byte[]](@(239, 187, 191) + (Ascii $ON)))) 'BOM survives a write'
    [byte[]]$legacy = [byte[]]((Ascii ('[options]' + $CRLF + 'name = Caf')) + @(233) + (Ascii ($CRLF + 'modsdisabled = 1' + $CRLF + 'scriptmodsenabled = 1' + $CRLF)))
    [IO.File]::WriteAllBytes($options, $legacy)
    Reset-Fakes
    [void](Enable-HelperMods -UserFolder $user)
    [byte[]]$legacyOn = [byte[]]((Ascii ('[options]' + $CRLF + 'name = Caf')) + @(233) + (Ascii ($CRLF + 'modsdisabled = 0' + $CRLF + 'scriptmodsenabled = 1' + $CRLF)))
    Ok (Same (Bytes $options) $legacyOn) 'a Windows-1252 byte elsewhere survives a write'

    Say 'finding the user folder independently of the game launcher:'
    $docs = New-Folder 'redirected OneDrive\Documents'
    $localized = New-Folder 'redirected OneDrive\Documents\Electronic Arts\Die Sims 4'
    [IO.File]::WriteAllBytes((Join-Path $localized 'Options.ini'), (Ascii $OFF))
    $downloads = New-Folder 'Downloads'
    Ok ((Find-HelperUserFolder -StartFolder $downloads -DocumentsFolder $docs) -eq $localized) 'redirected Documents and localized name; no Mods folder required'
    $deep = New-Folder 'redirected OneDrive\Documents\Electronic Arts\Die Sims 4\Mods\TS4_Access_Helper'
    Ok ((Find-HelperUserFolder -StartFolder $deep -DocumentsFolder $docs) -eq $localized) 'helper inside Mods finds its own user folder'
    $sims3 = New-Folder 'redirected OneDrive\Documents\Electronic Arts\The Sims 3'
    [IO.File]::WriteAllBytes((Join-Path $sims3 'Options.ini'), (Ascii $OFF))
    [void][IO.Directory]::CreateDirectory((Join-Path $sims3 'Mods'))
    Ok ((Find-HelperUserFolder -StartFolder $downloads -DocumentsFolder $docs) -eq $localized) 'The Sims 3 options are never mistaken for Sims 4'
    $second = New-Folder 'redirected OneDrive\Documents\Electronic Arts\The Sims 4'
    [IO.File]::WriteAllBytes((Join-Path $second 'Options.ini'), (Ascii $OFF))
    Ok ($null -eq (Find-HelperUserFolder -StartFolder $downloads -DocumentsFolder $docs)) 'two plausible user folders require manual selection'
    Ok ((Find-HelperUserFolder -StartFolder $deep -DocumentsFolder $docs) -eq $localized) 'Mods placement takes priority over ambiguous Documents folders'
    $emptyDocs = New-Folder 'empty Documents'
    Ok ($null -eq (Find-HelperUserFolder -StartFolder $downloads -DocumentsFolder $emptyDocs)) 'first-time player with no Options.ini needs manual setup'
    Ok ($null -eq (Find-HelperUserFolder -StartFolder $downloads -DocumentsFolder '')) 'unavailable Documents folder allows manual selection'
    # Neither test uses an installed executable, registry entry or launcher.
    foreach ($launcher in @('EA', 'Steam')) {
        $launcherDocs = New-Folder ($launcher + '\Documents')
        $launcherUser = New-Folder ($launcher + '\Documents\Electronic Arts\The Sims 4')
        [IO.File]::WriteAllBytes((Join-Path $launcherUser 'Options.ini'), (Ascii $OFF))
        $found = Find-HelperUserFolder -StartFolder $downloads -DocumentsFolder $launcherDocs
        Reset-Fakes
        [void](Enable-HelperMods -UserFolder $found)
        Ok ((Get-HelperStatus -UserFolder $launcherUser).ModsEnabled) ($launcher + ' user layout works without finding or launching a game executable')
    }

    Say 'status for the dialog:'
    $record = Join-Path $user 'GameVersion.txt'
    [IO.File]::WriteAllBytes($record, (Ascii 'untouched version record'))
    [IO.File]::WriteAllBytes($options, (Ascii $OFF))
    $status = Get-HelperStatus -UserFolder $user
    Ok ($status.OptionsFound -and (-not $status.ModsEnabled) -and (-not $status.Error)) 'settings found, mods off'
    Reset-Fakes
    [void](Enable-HelperMods -UserFolder $user)
    Ok ((Get-HelperStatus -UserFolder $user).ModsEnabled) 'mods on after enabling'
    Ok (Same (Bytes $record) (Ascii 'untouched version record')) 'GameVersion.txt left byte-identical'
    $status = Get-HelperStatus -UserFolder (Join-Path $temp 'does-not-exist')
    Ok ((-not $status.OptionsFound) -and (-not $status.ModsEnabled)) 'missing options are distinct from disabled mods'
    $status = Get-HelperStatus -UserFolder ''
    Ok ((-not $status.OptionsFound) -and (-not $status.Error)) 'unknown user folder is a selectable state'
    [IO.File]::WriteAllBytes($options, (Ascii ('[options]' + $CRLF + '[options]' + $CRLF)))
    $status = Get-HelperStatus -UserFolder $user
    Ok ($status.OptionsFound -and $status.Error -match 'more than one') 'malformed settings return an error rather than crashing status'

    Say 'standalone executable with no sidecar files:'
    $standalone = New-Folder 'standalone'
    $front = Join-Path $standalone 'TS4AccessHelper.exe'
    [IO.File]::Copy((Join-Path $root 'helper\TS4AccessHelper.exe'), $front)
    $report = Join-Path $temp 'status.json'
    [IO.File]::WriteAllBytes($options, (Ascii $OFF))
    [byte[]]$before = Bytes $options
    $process = Start-Process -FilePath $front -ArgumentList @('--user-folder', ('"' + $user + '"'), '--status-file', ('"' + $report + '"')) -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit(20000)) { $process.Kill(); throw 'Standalone helper timed out' }
    $reported = [IO.File]::ReadAllText($report) | ConvertFrom-Json
    Ok ($process.ExitCode -eq 0 -and $reported.OptionsFound -and (-not $reported.ModsEnabled)) 'embedded options editor runs from the exe alone'
    Ok (Same (Bytes $options) $before) 'diagnostic mode writes no options'
    Ok (@(Get-ChildItem -LiteralPath $standalone).Count -eq 1) 'no sidecar scripts extracted'

    Say ('ALL {0} CHECKS PASSED' -f $script:passed)
} catch {
    Say $_.Exception.Message
    Say ('{0} checks passed before the failure' -f $script:passed)
    exit 1
} finally {
    $safeParent = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    $safeTarget = [IO.Path]::GetFullPath($temp)
    if (-not $safeTarget.StartsWith($safeParent, [StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($safeTarget) -notlike 'sr-helper-test-*') { throw 'Unsafe test cleanup path' }
    Get-ChildItem -LiteralPath $safeTarget -Recurse -Force -ErrorAction SilentlyContinue | ForEach-Object { try { $_.Attributes = 'Normal' } catch {} }
    Remove-Item -LiteralPath $safeTarget -Recurse -Force -ErrorAction SilentlyContinue
}
