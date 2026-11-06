# GNU Radio and Digital Communications Lab

A collection of reproducible signal-processing experiments covering CPFSK/GMSK analysis, SDR capture, native C demodulation, and an OQPSK RTL modulator.

## What is included

- `cpfsk_9600_nrzi_g3ruh.grc` — GNU Radio flowgraph for a 9.6 ksym/s CPFSK/G3RUH receive chain.
- Root Python scripts — symbol-rate estimation, modulation-index analysis, filtering studies, and IQ comparison tools.
- `c_demod/` — standalone C implementation of the CPFSK demodulation pipeline.
- `pluto_capture/` — libiio-based PlutoSDR capture utility.
- `oqpsk_verilog/` — synthesizable SystemVerilog OQPSK modulator with a self-checking testbench.
- Numbered Markdown reports — experiment design, validation steps, and measured results.

Raw IQ captures and generated analysis artifacts are intentionally excluded from version control. The retained plots are representative results.

## Python analysis setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
```

Place a local complex-float capture at `intern_Rec.bin` before opening the GNU Radio flowgraph. Generated output such as `decoded_bits_g3ruh.bin` remains ignored.

Most analysis scripts use constants near the top of each file for input paths and signal parameters. Run them from the repository root, for example:

```bash
python compare_iq_cpfsks.py
python estimate_exact_symbol_rate.py
```

## Native and RTL components

See the component-specific guides:

- [`c_demod/README.md`](c_demod/README.md)
- [`pluto_capture/README.md`](pluto_capture/README.md)
- [`oqpsk_verilog/README.md`](oqpsk_verilog/README.md)

## Notes

The detailed experiment reports are retained in Turkish because they document the original measurement and validation process. Source files and top-level usage guidance are organized for portable use.
