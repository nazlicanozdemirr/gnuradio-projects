@echo off
setlocal

cd /d "%~dp0"

for %%I in (iverilog.exe) do set "IVERILOG_EXE=%%~$PATH:I"
if not defined IVERILOG_EXE (
    echo HATA: iverilog.exe PATH icinde bulunamadi.
    echo Bu dosyayi OSS CAD Suite terminalinde calistirin.
    exit /b 1
)

for %%I in ("%IVERILOG_EXE%") do set "SUITE_BIN=%%~dpI"
set "IVL_DIR=%SUITE_BIN%..\lib\ivl"
set "VVP_EXE=%SUITE_BIN%vvp.exe"

echo [1/2] SystemVerilog kodu derleniyor...
"%IVERILOG_EXE%" -B "%IVL_DIR%" -g2012 -Wall -s tb_oqpsk -o oqpsk_sim.vvp oqpsk_modulator.sv tb_oqpsk.sv
if errorlevel 1 (
    echo HATA: Icarus derleme islemi basarisiz.
    exit /b 1
)

echo [2/2] Simulasyon calistiriliyor...
"%VVP_EXE%" -M - -M "%IVL_DIR%" oqpsk_sim.vvp
if errorlevel 1 (
    echo HATA: Icarus simulasyonu basarisiz.
    exit /b 1
)

if not exist "oqpsk.vcd" (
    echo HATA: Simulasyon bitti ancak oqpsk.vcd olusmadi.
    exit /b 1
)

echo.
echo BASARILI: oqpsk.vcd olusturuldu.
echo Dalga seklini acmak icin: gtkwave oqpsk.vcd

endlocal
