$ErrorActionPreference = 'Stop'

Push-Location $PSScriptRoot
try {
    iverilog -g2012 -Wall -s tb_oqpsk -o oqpsk_sim.vvp oqpsk_modulator.sv tb_oqpsk.sv
    if ($LASTEXITCODE -ne 0) {
        throw "Icarus derleme hatasi (cikis kodu: $LASTEXITCODE)."
    }

    vvp oqpsk_sim.vvp
    if ($LASTEXITCODE -ne 0) {
        throw "Icarus simulasyon hatasi (cikis kodu: $LASTEXITCODE)."
    }

    Write-Host ''
    Write-Host 'Simulasyon basarili. Dalga seklini acmak icin:'
    Write-Host '  gtkwave oqpsk.vcd'
}
finally {
    Pop-Location
}
