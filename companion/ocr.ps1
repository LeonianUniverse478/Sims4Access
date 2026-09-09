# Capture a window (or the whole screen) and OCR it with the OCR engine that
# ships with Windows. No installs: System.Drawing captures, Windows.Media.Ocr
# reads, and the result comes back as JSON of words with their boxes.
#
# Called by start_game.py. Usable on its own for testing:
#   powershell -ExecutionPolicy Bypass -File ocr.ps1
#   powershell -ExecutionPolicy Bypass -File ocr.ps1 -WindowTitle "The Sims 4"
param(
    [string]$WindowTitle = "",
    [string]$SavePng = ""
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Runtime.WindowsRuntime

# Finding the game's window means asking Win32 for its rectangle; the screen
# region we OCR has to be the window, or every coordinate we hand back is
# offset by wherever the window happens to sit.
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class W {
    [DllImport("user32.dll")] public static extern IntPtr FindWindow(string c, string n);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }
}
"@

Add-Type -AssemblyName System.Windows.Forms
$bounds = [System.Windows.Forms.SystemInformation]::VirtualScreen
$width = $bounds.Width; $height = $bounds.Height
$left = $bounds.X; $top = $bounds.Y

if ($WindowTitle -ne "") {
    $handle = [W]::FindWindow($null, $WindowTitle)
    if ($handle -eq [IntPtr]::Zero) {
        Write-Output (@{ error = "window not found: $WindowTitle" } | ConvertTo-Json)
        exit 1
    }
    $rect = New-Object W+RECT
    [void][W]::GetWindowRect($handle, [ref]$rect)
    $left = $rect.Left; $top = $rect.Top
    $width = $rect.Right - $rect.Left
    $height = $rect.Bottom - $rect.Top
}

$bitmap = New-Object System.Drawing.Bitmap $width, $height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($left, $top, 0, 0, $bitmap.Size)
$graphics.Dispose()

$temp = [System.IO.Path]::GetTempFileName() + ".png"
$bitmap.Save($temp, [System.Drawing.Imaging.ImageFormat]::Png)
$bitmap.Dispose()
if ($SavePng -ne "") { Copy-Item $temp $SavePng -Force }

# WinRT's async methods return IAsyncOperation, which PowerShell 5.1 cannot
# await directly. This is the standard shim: find the generic AsTask, close it
# over the right result type, and wait on the Task.
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
                   $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]

function Await($op, $resultType) {
    $task = $asTaskGeneric.MakeGenericMethod($resultType).Invoke($null, @($op))
    $task.Wait(-1) | Out-Null
    $task.Result
}

[Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Media, ContentType = WindowsRuntime] | Out-Null

$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($temp)) ([Windows.Storage.StorageFile])
$stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bmp = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if ($null -eq $engine) {
    Write-Output (@{ error = "no OCR language installed" } | ConvertTo-Json)
    exit 1
}
$result = Await ($engine.RecognizeAsync($bmp)) ([Windows.Media.Ocr.OcrResult])

# Coordinates come back relative to the captured image, so the window offset
# goes back on here - the caller wants screen coordinates to click.
$words = @()
foreach ($line in $result.Lines) {
    foreach ($word in $line.Words) {
        $words += [ordered]@{
            text = $word.Text
            line = $line.Text
            x = [int]($left + $word.BoundingRect.X + $word.BoundingRect.Width / 2)
            y = [int]($top + $word.BoundingRect.Y + $word.BoundingRect.Height / 2)
        }
    }
}
Remove-Item $temp -Force -ErrorAction SilentlyContinue
Write-Output (@{ width = $width; height = $height; origin = @($left, $top);
                 words = $words } | ConvertTo-Json -Depth 4 -Compress)
