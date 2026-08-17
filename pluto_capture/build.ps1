$ErrorActionPreference = 'Stop'
$gcc = 'C:\Users\nzlcn\AppData\Local\Microsoft\WinGet\Packages\BrechtSanders.WinLibs.MCF.UCRT_Microsoft.Winget.Source_8wekyb3d8bbwe\mingw64\bin\gcc.exe'
$include = 'C:\Program Files (x86)\Microsoft Visual Studio 12.0\VC\include'
$libiio = 'C:\Windows\System32\libiio.dll'

foreach ($required in @($gcc, (Join-Path $include 'iio.h'), $libiio)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Gerekli dosya bulunamadi: $required" }
}

& $gcc -O2 -std=c11 -Wall -Wextra -Wpedantic `
    ('-I' + $include) `
    (Join-Path $PSScriptRoot 'pluto_capture.c') `
    $libiio `
    -o (Join-Path $PSScriptRoot 'pluto_capture.exe')
if ($LASTEXITCODE -ne 0) { throw "Derleme basarisiz: $LASTEXITCODE" }
& (Join-Path $PSScriptRoot 'pluto_capture.exe') --help
