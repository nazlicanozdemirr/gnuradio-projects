$ErrorActionPreference = 'Stop'
$gcc = if ($env:CC) { $env:CC } else { (Get-Command gcc -ErrorAction Stop).Source }
$include = $env:LIBIIO_INCLUDE
$libiio = $env:LIBIIO_LIBRARY

if (-not $include -or -not $libiio) {
    throw 'Set LIBIIO_INCLUDE and LIBIIO_LIBRARY before building.'
}

foreach ($required in @((Join-Path $include 'iio.h'), $libiio)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Gerekli dosya bulunamadi: $required" }
}

& $gcc -O2 -std=c11 -Wall -Wextra -Wpedantic `
    ('-I' + $include) `
    (Join-Path $PSScriptRoot 'pluto_capture.c') `
    $libiio `
    -o (Join-Path $PSScriptRoot 'pluto_capture.exe')
if ($LASTEXITCODE -ne 0) { throw "Derleme basarisiz: $LASTEXITCODE" }
& (Join-Path $PSScriptRoot 'pluto_capture.exe') --help
