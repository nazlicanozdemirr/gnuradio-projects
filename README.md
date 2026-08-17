# GNU Radio ve SDR Projeleri

Bu depo, SDR sinyal işleme çalışmaları kapsamında geliştirilen CPFSK alıcı,
IQ analiz, ADALM-Pluto yakalama ve OQPSK HDL örneklerini bir arada tutar.

## İçerik

- `cpfsk_9600_nrzi_g3ruh.grc`: 9600 bit/s CPFSK, NRZ-I ve G3RUH alıcı akışı.
- `c_demod/`: GNU Radio bağımlılığı olmadan çalışan C CPFSK demodülatörü.
- `pluto_capture/`: ADALM-Pluto üzerinden complex64 IQ yakalama uygulaması.
- `oqpsk_verilog/`: SystemVerilog OQPSK modülatörü ve testbench'i.
- Kök dizindeki Python betikleri: IQ kayıtlarının ölçüm, karşılaştırma ve
  doğrulama analizleri.
- Numaralı Markdown belgeleri: proje rehberleri ve doğrulama raporları.

## Veri dosyaları

Ham IQ kayıtları ve üretilen büyük ikili çıktılar Git deposuna dahil edilmez.
Analizleri yeniden çalıştırmak için gerekli `complex64` kayıtlarını çalışma
dizinine yerel olarak ekleyin. Beklenen dosya adları ve örnekleme parametreleri
ilgili teknik belgelerde açıklanmıştır.

## Hızlı başlangıç

GNU Radio akışını GNU Radio Companion ile açabilirsiniz:

```text
cpfsk_9600_nrzi_g3ruh.grc
```

Bağımsız C demodülatörünü Windows PowerShell üzerinden derlemek için:

```powershell
powershell -ExecutionPolicy Bypass -File .\c_demod\build.ps1
```

OQPSK HDL örneğini çalıştırmak için:

```powershell
.\oqpsk_verilog\run_sim.ps1
```

Ayrıntılı kullanım ve doğrulama sonuçları için proje klasörlerindeki README
dosyalarına ve kök dizindeki numaralı teknik raporlara bakın.
