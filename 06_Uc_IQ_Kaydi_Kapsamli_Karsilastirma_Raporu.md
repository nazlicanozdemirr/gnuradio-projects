# Üç IQ Kaydının Kapsamlı CPFSK/CPM Karşılaştırma Raporu

## 1. Kapsam

Bu rapor üç ham IQ kaydını dosya bütünlüğü, örnekleme ve sembol hızı, frekans seviyeleri, modülasyon indisi, taşıyıcı ofseti, genlik/IQ kalitesi, spektrum, pulse-shaping, matched-filter uyumu ve ham sembol içeriği açısından karşılaştırır.

| Kısa ad | Dosya | SHA-256 |
|---|---|---|
| A | `intern_Rec().bin` | `C6F270A430A55549979AC9103053F40F7851A1CF52D33F7FB54ECC7314FB47F3` |
| B | `intern_Rec1().bin` | `50CFFAEB4F00CF6C9F536BDDD1731D5BA1F4AEBA7F40F71F9D0D628AD7A3ED60` |
| C | `intern_Rec2().bin` | `42E417C72A116719AAC95B11610FEAE5B63AD835834B56B6FAD60F5F48C2246F` |

Analiz varsayımları:

```text
Format       : little-endian complex64 IQ
Fs           : 576000 sample/s
Rs           : 9600 symbol/s
SPS          : Fs/Rs = 60 sample/symbol
Sembol tipi  : NRZ-I hat kodlu ikili veri adayı
```

Üç dosyanın da boyutu sekiz bayta tam bölünmektedir ve tüm örnekler sonludur; NaN/Inf bulunmamıştır.

## 2. Yönetici özeti

- A ve C, iki temiz frekans seviyeli, keskin geçişli, tam-tepkili binary CPFSK görünümündedir. Aynı temel GNU Radio demodülatör mimarisiyle çözülebilirler.
- B, iki temiz seviye yerine dört ana ara seviye ve çok daha yavaş ton geçişi gösterir. Kısmi-tepkili/pulse-shaped binary CPM/CPFSK olasılığı yüksektir. A ve C için kullanılan tek eşikli slicer yapısı B'ye doğrudan uygun değildir.
- Modülasyon indisleri A=`0.732±0.013`, B=`0.464±0.003` ve C=`0.614±0.002` olarak ölçülmüştür. B için değer, fractional sembol saatiyle bir sembolde biriken toplam fazdan çıkarılmıştır.
- C'nin `h` değeri A'dan %16.2 <daha küçüktür; buna rağmen `h` kararlılığı üç kayıt içinde en yüksektir.
- İşgal bant genişliği sıralaması A > C > B'dir. B en dar spektrumludur; bunun bedeli semboller arası bellek ve daha karmaşık demodülasyondur.
- C, en düşük zarf değişimi, en düşük PAPR, en iyi I/Q genlik dengesi ve en kararlı merkez/`h` değerini göstermektedir.
- NRZ-I sonrası ham sembol korelasyonu üç çiftte de yaklaşık sıfırdır. Kayıtların aynı payload'ın farklı alımları olduğuna dair kanıt yoktur.

## 3. Dosya ve süre özellikleri

| Özellik | A | B | C |
|---|---:|---:|---:|
| Dosya boyutu | 59,506,688 B | 102,236,160 B | 56,623,104 B |
| Complex örnek | 7,438,336 | 12,779,520 | 7,077,888 |
| Süre | 12.913778 s | 22.186667 s | 12.288000 s |
| Sonlu örnek oranı | %100 | %100 | %100 |
| Fs | 576 kS/s | 576 kS/s | 576 kS/s |
| Rs | 9.6 kBd | 9.6 kBd | 9.6 kBd |
| SPS | 60 | 60 | 60 |

A ve C'de 60 SPS zamanlama periyodu, 20–100 örnek aralığındaki tüm adaylar arasında birinci sıradadır. B'de 9.6 kHz ve 19.2 kHz saat/harmonik çizgileri bulunmasına rağmen, çok-sembollü pulse-shape nedeniyle basit 60-faz geçiş yoğunluğu testi zayıftır.

## 4. Frekans seviyeleri ve modülasyon indisi

İkili CPFSK için:

```text
h = (f_high - f_low)/Rs = 2·Δf/Rs
```

Frekans seviyeleri, Quadrature Demod eşdeğeri anlık frekans çıkışında birer saniyelik pencerelerde histogram modlarıyla ölçülmüştür.

| Özellik | A | B | C |
|---|---:|---:|---:|
| Etkin alt frekans | -4.388 kHz | -2.120 kHz | -3.071 kHz |
| Etkin üst frekans | +2.643 kHz | +2.336 kHz | +2.824 kHz |
| Merkez ofseti | -0.872 ± 0.048 kHz | +0.108 ± 0.026 kHz | -0.124 ± 0.010 kHz |
| Etkin frekans ayrımı | 7.031 kHz | 4.456 kHz | 5.895 kHz |
| Sapma `Δf` | 3.515 kHz | 2.228 kHz | 2.948 kHz |
| Ortalama `h` | **0.732** | **0.464** | **0.614** |
| `h` standart sapması | 0.0132 | 0.0029 | 0.0017 |
| Saniyelik `h` aralığı | 0.708–0.756 | 0.461–0.471 | 0.611–0.618 |

B'nin anlık frekans histogramındaki `-3.06/+3.25 kHz` dış tepeler sembol içi maksimumlardır; bunları ton kabul etmek hatalı `h≈0.657` sonucunu üretir. Doğru B değeri, hassas sembol saati (`Rs=9601.26 Bd`, `SPS=59.99213`) ile her sembolde biriken fazın uzun aynı-bit koşularında regresyonundan hesaplanmıştır. Aynı yöntem A=`0.73235` ve C=`0.61422` sonuçlarını yeniden üreterek çapraz doğrulanmıştır.

### Göreli farklar

- B'nin `h` değeri A'dan yaklaşık %36.6 düşüktür.
- C'nin `h` değeri A'dan yaklaşık %16.2 düşüktür.
- B'nin `h` değeri C'den yaklaşık %24.4 düşüktür.
- C ve B'nin fractional-clock saniyelik `h` ölçümleri A'ya göre daha kararlıdır.

## 5. Sinyal sınıflandırması

### Kayıt A

Sembol fazında iki baskın küme vardır:

```text
-4.397 kHz / +2.704 kHz
küme ağırlığı ≈ 0.497 / 0.503
```

İki-küme ayrım kalitesi 15.69'dur. Bu sonuç tam-tepkili binary CPFSK ile uyumludur.

### Kayıt B

Sembol fazında dört ana küme vardır:

```text
-3.003 / -1.166 / +1.397 / +3.237 kHz
küme ağırlıkları ≈ 0.276 / 0.222 / 0.224 / 0.278
```

Komşu seviyeler eşit aralıklı değildir; dolayısıyla temiz 4-FSK yorumundan çok `±(a+b)` ve `±(a-b)` partial-response binary CPM modeliyle uyumludur. Tek-sembollük integrasyon sonrası iki-küme kalitesi yalnız 3.38'dir.

### Kayıt C

Sembol fazında iki baskın küme vardır:

```text
-3.125 kHz / +2.863 kHz
küme ağırlığı ≈ 0.502 / 0.498
```

İki-küme ayrım kalitesi 14.69'dur. C, dalga biçimi sınıfı olarak A'ya çok yakındır; temel fark daha küçük frekans sapması ve daha küçük `h` değeridir.

## 6. Genlik, zarf ve IQ kalitesi

| Özellik | A | B | C |
|---|---:|---:|---:|
| Ortalama zarf | 0.23381 | 0.72536 | 0.31339 |
| RMS genlik | 0.23447 | 0.72714 | 0.31373 |
| PAPR | 2.44 dB | 2.82 dB | 1.77 dB |
| Zarf değişim katsayısı | %7.52 | %7.00 | **%4.63** |
| DC büyüklüğü | 1.13×10⁻⁵ | 7.10×10⁻⁵ | 4.65×10⁻⁵ |
| I/Q standart sapma oranı | 0.927 | 0.988 | **1.003** |
| I/Q korelasyonu | 0.00119 | 0.00465 | **0.00030** |

RMS genlik karşılaştırması:

- B, A'dan 9.83 dB yüksek görünmektedir.
- C, A'dan 2.53 dB yüksektir.
- B, C'den 7.30 dB yüksektir.

Bu farklar mutlak RF güç farkı kabul edilmemelidir. Kayıt kazancı, AGC, SDR ölçeği ve analog zincir bilinmeden yalnız dosya içi sayısal seviye karşılaştırmasıdır.

C'nin zarfı en sabit, PAPR'ı en düşük ve I/Q genlik dengesi bire en yakın kayıttır. Üç kayıt da genel olarak sabit-zarflı CPM/CPFSK yapısıyla uyumludur.

## 7. Spektrum ve işgal bant genişliği

| Güç oranı | A | B | C |
|---|---:|---:|---:|
| %90 OBW | 9.503 kHz | **7.628 kHz** | 8.746 kHz |
| %99 OBW | 17.615 kHz | **12.300 kHz** | 14.088 kHz |
| %99.9 OBW | 34.337 kHz | **23.667 kHz** | 28.795 kHz |

- A en geniş spektruma sahiptir; en yüksek `h` değeriyle uyumludur.
- C'nin spektrumu A'dan dar, B'den geniştir.
- B en dar ve uzak yan lobları en fazla bastırılmış kayıttır. Güçlü pulse-shaping yorumu bu sonuçla tutarlıdır.

## 8. Filtre ve pulse-shaping karşılaştırması

İzole ton geçişleri aynı yöne çevrilerek medyan geçiş profili hesaplanmıştır:

| Özellik | A | B | C |
|---|---:|---:|---:|
| İzole geçiş sayısı | 1963 | 1228 | 1887 |
| 10–90% süre | 5.46 örnek | 24.61 örnek | 5.47 örnek |
| 10–90% süre | 9.49 µs | 42.73 µs | 9.49 µs |
| Sembol süresine oran | 0.091 T | 0.410 T | 0.091 T |

A ve C'nin geçiş profilleri neredeyse aynıdır: keskin yükseliş, küçük aşım ve sönümlü ringing. Bu durum aynı veya çok benzer verici/kanal filtre ailesine işaret eder. Güçlü bir çok-sembollü pulse-shaping görülmez.

B'nin geçişi yaklaşık 4.5 kat daha uzundur ve komşu sembollerden etkilenmektedir. B'de belirgin pulse-shaping/partial-response bellek vardır. Tam filtre ailesi veya Gaussian `BT` değeri, bilinen preamble/verici spesifikasyonu olmadan kesin çıkarılamaz.

## 9. GNU Radio matched-filter ve parametre önerisi

60 tap'li hareketli ortalama:

```python
[1.0/60] * 60
```

A ve C'nin discriminator çıkışındaki yaklaşık dikdörtgen frekans sembolleri için integrate-and-dump/approximate matched filter görevi görür. B'nin çok-sembollü frekans darbesiyle eşleşmez.

Normalize Quadrature Demod için başlangıç değerleri:

| Parametre | A | B | C |
|---|---:|---:|---:|
| Ölçülen `Δf` | 3515.5 Hz | 2228.0 Hz | 2947.5 Hz |
| `gain = Fs/(2πΔf)` | **26.08** | 41.17 | **31.10** |
| Normalize merkez `fcenter/Δf` | -0.248 | +0.049 | -0.042 |
| `Add Const = -fcenter/Δf` | **+0.248** | -0.049 | **+0.042** |

B satırındaki sayılar anlık dış tepelere değil sembol-faz integraline dayanır; normalizasyon için doğrudur. Pulse-shape belleği nedeniyle yine de tek başına doğru B demodülasyonu sağlamaz.

### A ve C için önerilen zincir

```text
File Source complex64
→ kompleks kanal filtresi/frekans düzeltme
→ Quadrature Demod
→ 60-tap moving average
→ Symbol Sync, input SPS=60, output SPS=1
→ Binary Slicer
→ Differential Decoder (NRZ-I)
→ doğrulanmış polynomial varsa Descrambler
→ Pack K Bits
```

### B için önerilen zincir

```text
File Source complex64
→ kanal filtresi ve frekans düzeltme
→ pulse-shape'e uygun CPM receive filter/demodulator
→ timing recovery
→ CPM belleğini kullanan trellis/MLSE veya doğrulanmış özel detector
→ NRZ-I/descrambler/frame işlemleri
```

Gardner, M&M veya Zero Crossing arasında geçiş yapmak, B'deki pulse-shape/model uyuşmazlığını tek başına çözmez.

## 10. Hat kodu, scrambling ve payload karşılaştırması

A ve C için hard-symbol istatistikleri:

| Özellik | A | C |
|---|---:|---:|
| Bir seviyesi oranı | 0.50077 | 0.50059 |
| Geçiş oranı | 0.49890 | 0.50273 |
| Ortalama run uzunluğu | 2.004 sembol | 1.989 sembol |

Bu değerler dengeli/rastgeleleştirilmiş bir hat dizisiyle uyumludur ve scrambler olasılığını destekler; fakat scrambler polynomial'ini veya scrambler varlığını tek başına kanıtlamaz.

Olası gecikme ve polarite terslenmesine karşı tüm kayıt çiftleri korele edilmiştir. NRZ-I diferansiyel çözme sonrasındaki en büyük mutlak korelasyonlar:

| Çift | Maksimum mutlak korelasyon |
|---|---:|
| A–B | 0.01525 |
| A–C | 0.01114 |
| B–C | 0.01524 |

Bu değerler rastgele ilişkisiz diziler seviyesindedir. Aynı payload'ın farklı kazanç/`h` ile kaydedildiğine dair kanıt yoktur. B'nin hard-symbol dizisi model uyuşmazlığı nedeniyle ayrıca ihtiyatla değerlendirilmelidir.

Kesin payload karşılaştırması için preamble/frame sync, descrambler polynomial ve CRC bilgisi gerekir.

## 11. Genel sıralama ve karar

### Basit CPFSK demodülatörüne uygunluk

1. **C:** İki temiz ton, en kararlı `h` ve merkez, iyi I/Q dengesi.
2. **A:** İki temiz ton ve biraz daha yüksek ayrım kalitesi; ancak merkez ve `h` C'ye göre daha fazla değişiyor.
3. **B:** Basit ikili slicer için uygun değil; özel partial-response/CPM alıcısı gerekiyor.

### Spektral verimlilik

1. **B:** En dar bant, fakat en karmaşık demodülasyon.
2. **C:** Orta bant genişliği, basit demodülasyon ve yüksek kararlılık arasında en iyi denge.
3. **A:** En geniş bant ve en yüksek `h`.

### Nihai teknik karar

- A ve C aynı genel binary full-response CPFSK sınıfındadır; aynı flow mimarisi kullanılabilir fakat `Δf`, Quadrature Demod gain ve DC/frekans merkez düzeltmesi ayrı ayarlanmalıdır.
- B aynı flow'un yalnız parametre değiştirilmiş haliyle güvenilir çözülemez. Dalga biçimi modeli farklıdır.
- Üç kayıt arasında genel alıcı geliştirme ve doğrulama için en temiz başlangıç kaydı C'dir.

## 12. Üretilen kanıt dosyaları

- `uc_iq_karsilastirma.png`: spektrum, `h`, OBW ve üç frekans histogramı.
- `iq_filtre_gecis_karsilastirmasi.png`: üç kaydın ton geçiş profilleri.
- `uc_iq_karsilastirma_ozeti.json`: tüm ana sayısal ölçümler.
- `uc_iq_h_zaman_serisi.csv`: saniyelik ton, merkez, sapma ve `h` değerleri.
- `uc_iq_sembol_korelasyonu.json`: line-symbol ve NRZ-I sonrası korelasyonlar.
