$ErrorActionPreference = 'Stop'
$exe = Join-Path $PSScriptRoot 'cpfsk_demod.exe'
$root = Split-Path $PSScriptRoot -Parent
$out = Join-Path $PSScriptRoot 'outputs'
New-Item -ItemType Directory -Path $out -Force | Out-Null

$jobs = @(
    @{ Profile='A'; Input=(Join-Path $root 'iq_compare_A.bin'); Prefix=(Join-Path $out 'rec_A') },
    @{ Profile='B'; Input=(Join-Path $root 'iq_compare_B.bin'); Prefix=(Join-Path $out 'rec_B') },
    @{ Profile='C'; Input=(Join-Path $root 'iq_compare_C.bin'); Prefix=(Join-Path $out 'rec_C') }
)

foreach ($job in $jobs) {
    & $exe --input $job.Input --output $job.Prefix --profile $job.Profile
    if ($LASTEXITCODE -ne 0) { throw "Demodulasyon basarisiz: $($job.Profile)" }
}
