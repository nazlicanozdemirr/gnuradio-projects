$ErrorActionPreference = 'Stop'
$gcc = if ($env:CC) { $env:CC } else { (Get-Command gcc -ErrorAction Stop).Source }
& $gcc -O2 -std=c11 -Wall -Wextra -Wpedantic `
    (Join-Path $PSScriptRoot 'cpfsk_demod.c') `
    -o (Join-Path $PSScriptRoot 'cpfsk_demod.exe')
if ($LASTEXITCODE -ne 0) { throw "Derleme basarisiz: $LASTEXITCODE" }
& (Join-Path $PSScriptRoot 'cpfsk_demod.exe') --help
