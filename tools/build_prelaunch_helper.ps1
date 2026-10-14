$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$compiler=Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$powershell=Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
$automation=(& $powershell -NoProfile -Command '[System.Management.Automation.PSObject].Assembly.Location').Trim()
$output=Join-Path $root 'helper\TS4AccessHelper.exe'
& $compiler /nologo /target:winexe /platform:x64 /optimize+ "/out:$output" "/reference:$automation" /reference:System.Windows.Forms.dll /reference:System.Drawing.dll "/resource:$(Join-Path $root 'helper\ScreenReaderHelper.Core.ps1'),TS4Access.Core.ps1" (Join-Path $root 'helper\ScreenReaderHelper.cs')
if ($LASTEXITCODE -ne 0) { throw 'Helper compilation failed' }
Get-FileHash -Algorithm SHA256 -LiteralPath $output
