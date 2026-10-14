$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    & py -3.7 tools/devkit.py @args
    if ($LASTEXITCODE -ne 0) { throw "Developer command failed (exit $LASTEXITCODE)." }
} finally { Pop-Location }
