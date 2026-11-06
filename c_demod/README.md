# CPFSK Demodulator in C

A standalone C11 implementation of the CPFSK receive pipeline used for comparison with the GNU Radio and Python analyses in this repository.

## Build

Install GCC and make sure `gcc` is available on `PATH`, then run:

```powershell
./build.ps1
```

You may set the `CC` environment variable to use a different compiler executable. The build script enables optimization and common warning flags, then runs `cpfsk_demod.exe --help` as a smoke test.

The original validation record is available in [`DOGRULAMA_RAPORU.md`](DOGRULAMA_RAPORU.md), with extended Turkish instructions in [`README_TR.md`](README_TR.md).
