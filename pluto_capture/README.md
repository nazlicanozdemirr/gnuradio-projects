# PlutoSDR Capture Utility

A small C11 utility for recording complex IQ samples from an ADALM-Pluto through libiio.

## Build

Install GCC and libiio, then set these environment variables:

- `LIBIIO_INCLUDE` — directory containing `iio.h`
- `LIBIIO_LIBRARY` — full path to the libiio library or DLL
- `CC` — optional compiler executable; defaults to `gcc` on `PATH`

Run:

```powershell
./build.ps1
```

The script builds the utility and executes `pluto_capture.exe --help`. Captured `.bin` files are ignored by Git. Turkish usage notes remain in [`README_TR.md`](README_TR.md).
