# PlutoSDR C IQ Yakalama

`pluto_capture.c`, ADALM-Pluto'dan libiio 0.26 ile RX örneği alır ve mevcut
CPFSK demodülatörünün beklediği little-endian complex64 biçiminde kaydeder.

Derleme:

```powershell
powershell -ExecutionPolicy Bypass -File .\pluto_capture\build.ps1
```

Boş RX gürültü testi:

```powershell
.\pluto_capture\pluto_capture.exe `
  --uri usb: `
  --frequency 2400000000 `
  --sample-rate 30720000 `
  --bandwidth 18000000 `
  --gain-mode slow_attack `
  --samples 262144 `
  --output .\pluto_capture\noise_complex64.bin
```

Gerçek CPFSK alımında `--frequency` hedef RF taşıyıcısına ayarlanmalıdır.
`--sample-rate 576000` cihaz tarafından reddedilirse 2304000 sample/s ile
kayıt alınıp C tarafında 4'e decimation uygulanacaktır.
