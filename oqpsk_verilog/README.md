# OQPSK Modulator RTL

A parameterized SystemVerilog OQPSK modulator and self-checking testbench. The design maps input bits to bipolar I/Q symbols and delays the Q branch by half a symbol period.

## Files

- `oqpsk_modulator.sv` — synthesizable modulator.
- `tb_oqpsk.sv` — functional testbench with waveform output.
- `run_sim.ps1` / `run_sim.bat` — Icarus Verilog simulation helpers.

## Simulation

Install Icarus Verilog and ensure `iverilog` and `vvp` are on `PATH`, then run:

```powershell
./run_sim.ps1
```

The simulation produces `oqpsk.vcd`, which can be inspected with GTKWave. Generated simulator and waveform files are ignored by Git.
