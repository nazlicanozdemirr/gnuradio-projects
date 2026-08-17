# 9600 bit/s CPFSK Alıcı Alt Sistemi

## Teknik Spesifikasyon ve Doğrulama Raporu

---

## Doküman kontrol bilgileri

| Alan | Değer |
|---|---|
| Doküman kimliği | `SPEC-CPFSK-RX-001` |
| Doküman adı | 9600 bit/s CPFSK Alıcı Alt Sistemi Teknik Spesifikasyonu |
| Revizyon | A |
| Durum | Doğrulama tamamlandı / kontrollü ilk sürüm |
| Tarih | 03 Ağustos 2026 |
| Hazırlayan | [Ad Soyad] |
| Kontrol eden | [Ad Soyad / Birim] |
| Onaylayan | [Ad Soyad / Birim] |
| Sınıflandırma | Kurum içi kullanım |
| Uygulama ortamı | GNU Radio 3.10.12.0 / Windows |

### Revizyon geçmişi

| Revizyon | Tarih | Değişiklik açıklaması | Hazırlayan |
|---|---|---|---|
| A | 03.08.2026 | İlk teknik spesifikasyon ve doğrulama sürümü | [Ad Soyad] |

---

# 1. Amaç

Bu doküman, 576 ksample/s hızında örneklenmiş `complex64` IQ veri dosyasında
bulunan 9600 bit/s binary CPFSK işaretinin demodülasyonu için geliştirilen
GNU Radio alıcı alt sisteminin:

1. Fonksiyonel gereksinimlerini,
2. Giriş ve çıkış arayüzlerini,
3. Sinyal işleme algoritmalarını,
4. Kritik konfigürasyon parametrelerini,
5. Performans ve kabul kriterlerini,
6. Test ve doğrulama yöntemlerini,
7. Elde edilen sonuçları,
8. Bilinen sınırlamaları

tanımlamak amacıyla hazırlanmıştır.

Bu doküman hem tasarım spesifikasyonu hem de gerçekleştirilen uygulamanın
doğrulama kaydı olarak kullanılacaktır.

---

# 2. Kapsam

Bu spesifikasyon aşağıdaki işlem katmanlarını kapsar:

```text
complex64 IQ dosya girişi
 -> CPFSK frequency discrimination
 -> frekans merkezi düzeltmesi
 -> matched filtering
 -> sembol zamanlama kurtarma
 -> hard decision
 -> NRZ-I decoding
 -> G3RUH descrambling
 -> test kaydına özel bit/byte hizalama
 -> byte paketleme
 -> binary dosya çıkışı
```

Bu sürümün kapsamı dışında kalan işlevler:

- Canlı RF/SDR donanım arayüzü,
- Otomatik frekans kontrolü,
- Geniş bant kanal seçimi,
- HDLC bit de-stuffing,
- Dinamik frame başlangıcı ve sonu tespiti,
- AX.25 veya uygulamaya özel protokol ayrıştırma,
- CRC/FCS doğrulama,
- Payload semantik çözümleme,
- FEC decoding,
- Kontrollü SNR altında BER karakterizasyonu.

---

# 3. Normatif ifadeler

Bu dokümanda aşağıdaki ifadeler normatif anlamda kullanılmıştır:

| İfade | Anlam |
|---|---|
| **ZORUNLUDUR / -malıdır** | Gereksinimin karşılanması zorunludur. |
| **ÖNERİLİR** | Tasarım tercihi olarak uygulanması tavsiye edilir. |
| **İZİN VERİLİR** | Uygulama açısından kabul edilebilir bir seçenektir. |
| **UYGULANAMAZ** | Mevcut test girdisi veya kapsam nedeniyle doğrulanamayan maddeyi belirtir. |

---

# 4. Referans dokümanlar

| Ref. | Doküman |
|---|---|
| RD-01 | [GNU Radio Quadrature Demod](https://wiki.gnuradio.org/index.php/Quadrature_Demod) |
| RD-02 | [GNU Radio Symbol Sync](https://wiki.gnuradio.org/index.php/Symbol_Sync) |
| RD-03 | [GNU Radio Differential Decoder](https://wiki.gnuradio.org/index.php/Differential_Decoder) |
| RD-04 | [GNU Radio Descrambler](https://wiki.gnuradio.org/index.php/Descrambler) |
| RD-05 | [GNU Radio Throttle](https://wiki.gnuradio.org/index.php/Throttle) |
| RD-06 | [GNU Radio G3RUH mask ve length açıklaması](https://www.gnuradio.org/news/2016-11-04-reverse-engineering-outernet/) |
| RD-07 | [G3RUH 9600 Baud Packet Radio Modem Design](https://www.amsat.org/amsat/articles/g3ruh/109.html) |

---

# 5. Terimler ve kısaltmalar

| Terim | Açıklama |
|---|---|
| AFC | Automatic Frequency Control |
| BER | Bit Error Rate |
| CPFSK | Continuous Phase Frequency Shift Keying |
| FCS | Frame Check Sequence |
| FIR | Finite Impulse Response |
| G3RUH | `1+x^12+x^17` polynomial'li 9600 baud packet-radio scrambler sistemi |
| HDLC | High-Level Data Link Control |
| IQ | In-phase ve Quadrature complex örnek gösterimi |
| LFSR | Linear Feedback Shift Register |
| NRZ-I | Non-Return-to-Zero Inverted |
| SPS | Samples Per Symbol |
| TED | Timing Error Detector |

---

# 6. Sistem tanımı

## 6.1 Üst seviye fonksiyon

Alıcı alt sistemi, dosyadaki complex IQ örneklerini kabul etmeli ve CPFSK
frekans durumlarını bit akışına dönüştürmelidir. Elde edilen hat bitleri NRZ-I
ve G3RUH işlemlerinden geçirilerek hexadecimal olarak incelenebilir packed byte
dosyasına yazılmalıdır.

## 6.2 Sistem blok diyagramı

```text
┌────────────────────┐
│ complex64 IQ File  │
└─────────┬──────────┘
          │ 576 ksample/s
          ▼
┌────────────────────┐
│ Quadrature Demod   │  Faz farkı -> normalize anlık frekans
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Center Correction  │  +12,121 kHz ofsetin kaldırılması
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ 60-tap FIR         │  Sembol süresince ortalama / matched filter
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Symbol Sync        │  60 SPS -> 1 sample/symbol
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Binary Slicer      │  Soft decision -> hard bit
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ NRZ-I Decoder      │  Hat sembolü -> scrambled veri biti
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ G3RUH Descrambler  │  Scrambled bit -> HDLC bit akışı
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Alignment + Pack   │  Bit sınırı -> 8-bit byte
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Binary File Output │
└────────────────────┘
```

---

# 7. Giriş arayüzü spesifikasyonu

## 7.1 Dosya arayüzü

| Parametre | Spesifikasyon |
|---|---|
| Dosya adı | `intern_Rec.bin` |
| Dosya biçimi | Header içermeyen raw binary |
| Örnek veri tipi | IEEE-754 `complex64` |
| I bileşeni | 32-bit float |
| Q bileşeni | 32-bit float |
| Örnek boyutu | 8 byte |
| Byte sırası | Platform/GNU Radio `complex64` doğal sırası |
| Örnekleme hızı | 576.000 sample/s |
| Dosya boyutu | 60.293.120 byte |
| Complex örnek sayısı | 7.536.640 |
| Kayıt süresi | 13,084444 s |

## 7.2 Giriş sinyali varsayımları

Sistem aşağıdaki giriş koşulları altında doğrulanmıştır:

- Modülasyon binary CPFSK'dir.
- Bit ve sembol hızı 9600'dür.
- Sinyal tek bir izole kanalı içermektedir.
- İki CPFSK tonu yaklaşık 8,60 kHz ve 15,66 kHz'dedir.
- Ton çiftinin merkezi yaklaşık +12,121 kHz'dir.
- Frekans sapması yaklaşık ±3,525 kHz'dir.
- Sinyal zarfı yaklaşık sabittir.

Bu sınırların dışındaki sinyaller için yeniden parametre tahmini yapılmalıdır.

---

# 8. Fonksiyonel gereksinimler

## 8.1 Genel gereksinimler

| Kimlik | Gereksinim |
|---|---|
| FR-001 | Sistem raw `complex64` IQ dosyasını örnek kaybı olmadan okuyabilmelidir. |
| FR-002 | Sistem giriş örnekleme hızını 576.000 sample/s olarak kullanmalıdır. |
| FR-003 | Sistem binary CPFSK işaretini real-valued frekans-seviye işaretine dönüştürmelidir. |
| FR-004 | Sistem ölçülen frekans merkezi ofsetini kaldırmalıdır. |
| FR-005 | Sistem sembol kararından önce bir sembol süreli matched/integrate-and-dump filtre uygulamalıdır. |
| FR-006 | Sistem nominal 60 SPS girişten sembol saatini kurtarmalıdır. |
| FR-007 | Sistem her sembol için bir soft-decision örneği üretmelidir. |
| FR-008 | Sistem soft-decision değerlerini sıfır eşikli hard bitlere dönüştürmelidir. |
| FR-009 | Sistem NRZ-I hat kodunu çözmelidir. |
| FR-010 | Sistem G3RUH `1+x^12+x^17` scrambling işlemini geri almalıdır. |
| FR-011 | Sistem unpacked bitleri sekizli packed byte'lara dönüştürebilmelidir. |
| FR-012 | Sistem packed byte çıktısını binary dosyaya yazmalıdır. |
| FR-013 | Sistem Symbol Sync soft-decision dağılımını histogram ile gözlenebilir kılmalıdır. |
| FR-014 | Sistem descramble edilmiş bit akışını 9600 item/s zaman ekseninde gösterebilmelidir. |

## 8.2 Veri akış sırası gereksinimi

NRZ-I decoding ve descrambling işlem sırası aşağıdaki gibi **olmalıdır**:

```text
Binary Slicer -> NRZ-I Decoder -> G3RUH Descrambler -> Pack K Bits
```

Descrambler unpacked bit akışında çalıştığı için Pack K Bits'ten sonra
yerleştirilmemelidir.

---

# 9. Algoritma spesifikasyonu

## 9.1 Örnek/sembol oranı

```text
Fs = 576000 sample/s
Rs = 9600 symbol/s
SPS = Fs/Rs = 60
```

Symbol Sync girişinde nominal SPS değeri 60 **olmalıdır**.

## 9.2 CPFSK frequency discriminator

Quadrature Demod işlemi aşağıdaki ifadeye eşdeğerdir:

```text
delta_phi[n] = angle(x[n] * conjugate(x[n-1]))
y[n] = G * delta_phi[n]
```

Normalize kazanç:

```text
G = Fs/(2*pi*f_dev)
G = 576000/(2*pi*3525)
G = 26,0065949563
```

Bu kazançla merkezden ±`f_dev` uzaklıktaki tonlar ideal durumda yaklaşık ±1
seviye üretmelidir.

## 9.3 Frekans merkezi düzeltmesi

Discriminator çıkışı `f/f_dev` biriminde olduğundan normalize merkez düzeltmesi:

```text
C = -f_mid/f_dev
C = -12121/3525
C = -3,4385815603
```

Sistem `Add Const` ile bu değeri discriminator çıkışına eklemelidir.

Bu uygulamada DC Blocker kullanılmamalıdır; DC Blocker'ın NRZ veri işaretinin
düşük frekans içeriğini bastırdığı ve sembol seviyelerini sıfıra doğru
çökerttiği testle gösterilmiştir.

## 9.4 Matched FIR

Filtre 60 katsayılı hareketli ortalama olarak uygulanmalıdır:

```text
h[k] = 1/60,  k=0...59
```

GNU Radio taps ifadesi:

```python
[1.0/int(sps)]*int(sps)
```

Decimation değeri 1 olmalıdır. Filtre örnek hızını değiştirmemeli, sembol
süresi boyunca gürültü ve ripple'ı ortalamalıdır.

## 9.5 Sembol zamanlama kurtarma

| Parametre | Zorunlu değer |
|---|---:|
| Timing Error Detector | Zero Crossing |
| Samples per Symbol | 60 |
| Expected TED Gain | 0,5 |
| Loop Bandwidth | 0,01 |
| Damping Factor | 1,0 |
| Maximum Deviation | 0,2 sample/symbol |
| Output Samples/Symbol | 1 |
| Interpolator | MMSE 8-tap FIR |
| Number of Filters | 128 |

Maksimum izin verilen nominal clock aralığı:

```text
59,8 <= SPS_estimate <= 60,2
```

## 9.6 Hard decision

Binary Slicer aşağıdaki karar kuralını uygulamalıdır:

```text
b_line[n] = 1, y_sync[n] > 0
b_line[n] = 0, y_sync[n] <= 0
```

## 9.7 NRZ-I decoding

Sistem GNU Radio `Differential Decoder` bloğunu `Coding=NRZI` ile
kullanmalıdır. Çıkış, scrambled veri bit akışı olarak kabul edilmelidir.

## 9.8 G3RUH descrambling

Kullanılan polynomial:

```text
p(x) = 1 + x^12 + x^17
```

Fonksiyonel descrambling ilişkisi:

```text
b_out[n] = b_in[n] XOR b_in[n-12] XOR b_in[n-17]
```

GNU Radio parametreleri:

```text
Mask   = 0x21
Seed   = 0x0
Length = 16
```

Descrambler self-synchronizing olduğundan ilk 17 bit acquisition bölgesi
olarak değerlendirilmelidir.

## 9.9 Bit/byte hizalama

Test girdisinde ilk geçerli HDLC flag bit 31'de başlamıştır. Test dosyasının
hexadecimal doğrulanması için descrambler sonrasında 31 bit atlanmalıdır.

`Skip Head=31` genel sistem gereksinimi değil, bu test kaydına özgü doğrulama
adaptasyonudur. Operasyonel sürümde hizalama HDLC flag korelasyonu veya HDLC
deframer ile dinamik yapılmalıdır.

## 9.10 Byte paketleme

Sekiz unpacked bit bir output byte'a paketlenmelidir. Test edilen GNU Radio
akışında Pack K Bits çıktısının manuel MSB-first paketleme ile yüzde 100
eşleştiği doğrulanmıştır.

---

# 10. Çıkış arayüzü spesifikasyonu

## 10.1 Scrambled ara çıktı

| Alan | Değer |
|---|---|
| Dosya | `decoded_bits.bin` |
| Aşama | NRZ-I sonrası, G3RUH öncesi |
| Veri tipi | Packed binary byte |
| Boyut | 15.701 byte |

İlk 32 byte:

```hex
1E 05 3D 2D B0 B1 2F B6 90 4E B0 30 A7 EE D1 E6
8A 67 1F BE 88 CB 34 2A 24 4B AA 63 8F F5 C4 5A
```

## 10.2 Descramble edilmiş nihai çıktı

| Alan | Değer |
|---|---|
| Dosya | `decoded_bits_g3ruh.bin` |
| Aşama | G3RUH ve test-kaydı hizalaması sonrası |
| Veri tipi | Packed binary byte |
| Boyut | 15.697 byte |
| Beklenen içerik | HDLC flag/idle `0x7E` |

İlk 32 byte:

```hex
7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E
7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E
```

---

# 11. Performans ve kabul gereksinimleri

| Kimlik | Kabul gereksinimi | Kabul eşiği |
|---|---|---|
| PR-001 | IQ örnekleri geçerli sayısal değer olmalıdır. | Finite oranı %100 |
| PR-002 | Symbol Sync iki kararlı soft-decision kümesi üretmelidir. | İki küme |
| PR-003 | Kümeler sıfırın iki yanında bulunmalıdır. | Alt < 0, üst > 0 |
| PR-004 | Karar eşiği çevresinde örnek bulunmamalıdır. | `|x|<0,5` oranı <= %0,1 |
| PR-005 | Symbol Sync output count teorik değere yakın olmalıdır. | Fark <= 10 sembol |
| PR-006 | Packed çıktı uzunluğu sembol sayısıyla tutarlı olmalıdır. | `floor(Nsymbol/8)` |
| PR-007 | Pack bit sırası belirlenmiş olmalıdır. | Referansla %100 eşleşme |
| PR-008 | Descrambler yapısal HDLC çıktı üretmelidir. | Düzenli `0x7E` dizisi |
| PR-009 | Geçerli idle bölgede beklenmeyen byte bulunmamalıdır. | `0x7E` dışı byte = 0 |

---

# 12. Doğrulama yaklaşımı

Doğrulama faaliyetleri aşağıdaki yöntemleri kapsamıştır:

- Dosya boyutu ve veri tipi tutarlılık kontrolü,
- IQ genlik istatistikleri,
- Ardışık örnek faz farkından anlık frekans ölçümü,
- Ton merkezi ve sapma tahmini,
- SPS ve kayıt süresi hesapları,
- Alternatif TED algoritmalarının karşılaştırılması,
- Soft-decision küme merkezleri ve RMS yayılım ölçümü,
- Sembol ve packed-byte sayısı kontrolü,
- Manuel bit paketleme karşılaştırması,
- Byte histogramı ve Shannon entropisi,
- Bit seviyesi G3RUH polynomial testi,
- GNU Radio Descrambler ile bağımsız tekrar,
- Nihai dosyada her byte'ın otomatik `0x7E` kontrolü,
- SHA-256 ile test girdisi ve çıktısı izlenebilirliği.

---

# 13. Gereksinim–test izlenebilirlik matrisi

| Gereksinim | Doğrulama testi | Kanıt/ölçüm | Sonuç |
|---|---|---|---|
| FR-001 | VT-01 Dosya bütünlüğü | 7.536.640 finite complex sample | GEÇTİ |
| FR-002 | VT-02 Sample-rate kontrolü | 576.000 sample/s | GEÇTİ |
| FR-003 | VT-03 Discriminator tonu | 8,60 ve 15,66 kHz | GEÇTİ |
| FR-004 | VT-04 Merkez düzeltmesi | Kümeler sıfırın iki yanında | GEÇTİ |
| FR-005 | VT-05 FIR karşılaştırması | RMS yayılım 0,023007 | GEÇTİ |
| FR-006 | VT-06 Timing recovery | 60 SPS, 125.609 sembol | GEÇTİ |
| FR-007 | VT-06 Timing recovery | Output SPS=1 | GEÇTİ |
| FR-008 | VT-07 Slicer marjı | `|x|<0,5` oranı 0 | GEÇTİ |
| FR-009 | VT-08 NRZ-I zincir testi | G3RUH sonrası HDLC flag | GEÇTİ |
| FR-010 | VT-09 G3RUH testi | 15.697 adet `0x7E` | GEÇTİ |
| FR-011 | VT-10 Pack testi | 15.701 byte, MSB-first %100 | GEÇTİ |
| FR-012 | VT-11 File Sink testi | Binary çıktı oluşturuldu | GEÇTİ |
| FR-013 | VT-12 Histogram gözlemi | -0,974/+0,977 iki tepe | GEÇTİ |
| FR-014 | VT-13 Time Sink kontrolü | 1024 bit ≈106,67 ms | GEÇTİ |
| PR-001 | VT-01 | Finite oranı %100 | GEÇTİ |
| PR-002 | VT-12 | İki küme | GEÇTİ |
| PR-003 | VT-12 | -0,974 ve +0,977 | GEÇTİ |
| PR-004 | VT-07 | Oran 0 | GEÇTİ |
| PR-005 | VT-06 | Teorik fark <2 sembol | GEÇTİ |
| PR-006 | VT-10 | 15.701 byte | GEÇTİ |
| PR-007 | VT-10 | MSB-first %100 eşleşme | GEÇTİ |
| PR-008 | VT-09 | Kesintisiz `0x7E` | GEÇTİ |
| PR-009 | VT-09 | Beklenmeyen byte 0 | GEÇTİ |

---

# 14. Doğrulama sonuçları

## 14.1 IQ dosya bütünlüğü

```text
Dosya boyutu        = 60.293.120 byte
Complex örnek       = 7.536.640
Finite örnek oranı  = %100
Kayıt süresi        = 13,084444 s
```

**Sonuç:** Kabul edildi.

## 14.2 Zarf istatistikleri

```text
Ortalama |x| = 0,23905
Std(|x|)     = 0,00497
```

Sinyal yaklaşık sabit zarflıdır ve CPFSK varsayımıyla uyumludur.

**Sonuç:** Kabul edildi.

## 14.3 Frekans seviyesi ölçümü

```text
Alt ton    ≈ 8,60 kHz
Üst ton    ≈ 15,66 kHz
Merkez     ≈ 12,121 kHz
Sapma      ≈ ±3,525 kHz
```

**Sonuç:** Binary frekans durumları doğrulandı.

## 14.4 Symbol Sync performansı

```text
Teorik sembol sayısı = 125.610,67
Ölçülen sembol       = 125.609
Alt küme merkezi     = -0,974409
Üst küme merkezi     = +0,976607
Küme hata RMS        = 0,023007
|x|<0,5 oranı        = 0
```

**Sonuç:** Timing recovery ve soft-decision kalitesi kabul edildi.

## 14.5 Scrambled çıktı analizi

```text
Boyut                 = 15.701 byte
Farklı byte değeri    = 256/256
Shannon entropisi     = 7,9873049 bit/byte
1-bit oranı           = 0,4990486
```

Sonuç yüksek entropili olup scrambling ile uyumludur. Scrambling kararı yalnız
bu istatistiğe değil, Bölüm 14.6'daki deterministik polynomial testine
dayandırılmıştır.

## 14.6 G3RUH descrambling sonucu

`mask=0x21`, `seed=0`, `length=16` ile:

```text
İlk geçerli HDLC flag başlangıcı = bit 31
Flag periyodu                    = 8 bit
Packed çıktı                     = 15.697 byte
0x7E sayısı                      = 15.697
0x7E dışı byte                   = 0
```

**Sonuç:** G3RUH polynomial'i ve decoding sırası doğrulandı.

---

# 15. Konfigürasyon öğeleri ve hash değerleri

| Konfigürasyon öğesi | Boyut | SHA-256 |
|---|---:|---|
| `intern_Rec.bin` | 60.293.120 | `2249095B3A18FD95FDD90FD5CA8AFD0B92CBDFD7C4926279A8F5ED17BE5B100E` |
| `decoded_bits.bin` | 15.701 | `E13D0B0039061EB1E76ECE2EE68CB94F5EA65DA88D33F80F3E6339262B14C860` |
| `decoded_bits_g3ruh.bin` | 15.697 | `9873C129FE562CC74B72BB4A3DFA53242C5B7C7365852B36574F4923FE43E8F4` |
| `cpfsk_9600_nrzi_g3ruh.grc` | 14.363 | `6D7EA8BDC3EA9C27FC945DFFC81BAD7E8FC394BC1FC2E78D23652440C2ABF3D9` |

Hash değerleri yalnız bu doğrulamada kullanılan kontrollü sürümler için
geçerlidir. Dosyalarda yapılacak her değişiklik yeni revizyon ve hash kaydı
gerektirir.

---

# 16. Sapmalar ve uygunsuzluklar

## NCR-001 — İlk akışta DC Blocker ve AGC kullanımı

| Alan | Açıklama |
|---|---|
| Durum | Kapatıldı |
| Etki | Sembol seviyeleri sıfıra doğru çöktü ve kümeler genişledi. |
| Kök neden | NRZ veri işaretinin düşük frekans içeriğinin DC olarak bastırılması. |
| Düzeltme | DC Blocker ve AGC kaldırıldı; fiziksel gain ve sabit Add Const kullanıldı. |
| Doğrulama | Kümeler -0,974/+0,977 ve RMS 0,023 seviyesine geldi. |

## NCR-002 — Yanlış SPS denemesi

| Alan | Açıklama |
|---|---|
| Durum | Kapatıldı |
| Etki | Yaklaşık 15 kat fazla output bit/byte oluştu. |
| Kök neden | 576 ksample/s girişte resampling olmadan SPS=4 kullanılması. |
| Düzeltme | SPS=60 olarak ayarlandı. |
| Doğrulama | 125.609 sembol ve 15.701 packed byte elde edildi. |

## NCR-003 — Descrambler eksikliği

| Alan | Açıklama |
|---|---|
| Durum | Kapatıldı |
| Etki | Hexadecimal veri rastgele görünüyordu. |
| Kök neden | G3RUH scrambling'in başlangıç tasarımında dikkate alınmaması. |
| Düzeltme | NRZ-I sonrasına G3RUH Descrambler eklendi. |
| Doğrulama | 15.697 adet kesintisiz `0x7E` elde edildi. |

## NCR-004 — Sabit byte hizalama

| Alan | Açıklama |
|---|---|
| Durum | Açık / operasyonel sürümde giderilecek |
| Etki | Farklı kayıt başlangıcında packed byte sınırı değişebilir. |
| Geçici çözüm | Bu test kaydı için `Skip Head=31`. |
| Kalıcı çözüm | HDLC flag korelasyonu ve dinamik deframer. |

---

# 17. Sınırlamalar ve açık maddeler

| Kimlik | Açık madde | Öncelik |
|---|---|---|
| OI-001 | Payload içeren yeni IQ kaydıyla frame-level doğrulama yapılmalıdır. | Yüksek |
| OI-002 | HDLC flag detection ve bit de-stuffing eklenmelidir. | Yüksek |
| OI-003 | CRC-16/FCS kontrolü uygulanmalıdır. | Yüksek |
| OI-004 | Sabit `Skip Head=31` kaldırılmalıdır. | Yüksek |
| OI-005 | Canlı sinyal için otomatik frekans düzeltmesi eklenmelidir. | Orta |
| OI-006 | Geniş bant giriş için channel filter/decimator eklenmelidir. | Orta |
| OI-007 | Kontrollü SNR ve frekans sapması altında BER testi yapılmalıdır. | Orta |
| OI-008 | Frame, CRC ve hata istatistikleri otomatik raporlanmalıdır. | Düşük |

---

# 18. Uygunluk beyanı ve kabul kararı

Yapılan analiz ve doğrulama faaliyetleri sonucunda aşağıdaki fonksiyonların
test girdisi için gereksinimleri karşıladığı belirlenmiştir:

- Raw complex64 IQ dosya alımı,
- Binary CPFSK frequency discrimination,
- Sabit frekans ofseti giderme,
- Sembol matched filtering,
- 60 SPS sembol timing recovery,
- Soft-decision ve hard-decision üretimi,
- NRZ-I decoding,
- G3RUH `1+x^12+x^17` descrambling,
- Test kaydına özgü byte hizalama,
- Packed binary dosya üretimi.

Nihai descramble edilmiş dosyada 15.697 byte'ın tamamının `0x7E` olması,
incelenen geçerli bölgede beklenmeyen byte bulunmaması ve tüm performans kabul
kriterlerinin sağlanması nedeniyle:

> **CPFSK demodülasyonu, sembol kurtarma, NRZ-I decoding ve G3RUH descrambling
> alt sistemi bu test girdisi için TEKNİK OLARAK UYGUN ve KABUL EDİLMİŞTİR.**

Bu kabul, payload ve frame-level protokol doğrulamasını kapsamaz. Test kaydı
yalnız HDLC idle flag içerdiğinden payload doğrulama maddesi uygulanamamıştır.

---

# 19. Onay tablosu

| Rol | Ad Soyad | Tarih | İmza |
|---|---|---|---|
| Hazırlayan |  |  |  |
| Teknik kontrol |  |  |  |
| Kalite/Doğrulama |  |  |  |
| Proje onayı |  |  |  |

---

# Ek A — Teslimat listesi

| Kimlik | Teslimat |
|---|---|
| CI-001 | `intern_Rec.bin` |
| CI-002 | `cpfsk_9600_nrzi_g3ruh.grc` |
| CI-003 | `cpfsk_9600_nrzi_g3ruh.py` |
| CI-004 | `decoded_bits.bin` |
| CI-005 | `decoded_bits_g3ruh.bin` |
| CI-006 | `cpfsk_teshis.png` |
| DOC-001 | `01_CPFSK_Proje_Adim_Adim_Teknik_Rehber.md` |
| DOC-002 | `02_CPFSK_Test_ve_Dogrulama_Raporu.md` |
| DOC-003 | `03_CPFSK_Alici_Teknik_Spesifikasyon_ve_Dogrulama_Raporu.md` |

# Ek B — Nihai hexadecimal kanıt

```hex
7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E
7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E
```

Yukarıdaki değer dosyanın tamamında tekrarlanmıştır:

```text
Toplam byte       = 15.697
0x7E byte         = 15.697
0x7E dışı byte    = 0
```

