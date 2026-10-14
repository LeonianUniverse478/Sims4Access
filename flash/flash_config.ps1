# Where the PowerShell Flash build scripts find java.exe, ffdec.jar and the
# compiled FFDec batch helpers. Dot-source it: . (Join-Path $here 'flash_config.ps1')
# Mirrors flash_config.py; keep the default lists identical.
#   TS4_JAVA           full path of java.exe (JDK 11 or newer; 21.0.11 tested)
#   TS4_FFDEC          full path of ffdec.jar (FFDec 26.2.1 tested)
#   TS4_FFDEC_HELPERS  folder with ReplaceScriptsBatch.class (default: <project>\build)

function Resolve-A11yBuildFile([string]$EnvName, [string[]]$Defaults, [string]$What) {
    $value = [Environment]::GetEnvironmentVariable($EnvName)
    if ($value) {
        $value = $value.Trim().Trim('"')
        if (-not (Test-Path -LiteralPath $value -PathType Leaf)) {
            throw "$EnvName is set to '$value', which is not a file. It must be the full path of $What."
        }
        return $value
    }
    foreach ($candidate in $Defaults) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    throw "$What not found. Set $EnvName to its full path."
}

function Get-A11yJava {
    Resolve-A11yBuildFile 'TS4_JAVA' @('C:\Tools\jdk21\jdk-21.0.11+10\bin\java.exe') 'java.exe (JDK 11 or newer)'
}

function Get-A11yFfdec {
    Resolve-A11yBuildFile 'TS4_FFDEC' @('C:\Tools\ffdec\ffdec.jar') 'ffdec.jar (FFDec 26.2.1)'
}

function Get-A11yHelpers {
    $value = [Environment]::GetEnvironmentVariable('TS4_FFDEC_HELPERS')
    if ($value) { return $value.Trim().Trim('"') }
    return (Join-Path (Split-Path -Parent $PSScriptRoot) 'build')
}
