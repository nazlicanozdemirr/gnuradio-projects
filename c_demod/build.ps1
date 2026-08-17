$ErrorActionPreference = 'Stop'
$gcc = 'C:\Users\nzlcn\AppData\Local\Microsoft\WinGet\Packages\BrechtSanders.WinLibs.MCF.UCRT_Microsoft.Winget.Source_8wekyb3d8bbwe\mingw64\bin\gcc.exe'
if (-not (Test-Path -LiteralPath $gcc)) {
    throw "gcc bulunamadi: $gcc"
}
& $gcc -O2 -std=c11 -Wall -Wextra -Wpedantic `
    (Join-Path $PSScriptRoot 'cpfsk_demod.c') `
    -o (Join-Path $PSScriptRoot 'cpfsk_demod.exe')
if ($LASTEXITCODE -ne 0) { throw "Derleme basarisiz: $LASTEXITCODE" }
& (Join-Path $PSScriptRoot 'cpfsk_demod.exe') --help
