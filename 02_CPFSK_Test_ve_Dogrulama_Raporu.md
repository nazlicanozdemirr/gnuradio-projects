# 9600 bit/s CPFSK Alıcı Zinciri

## Test ve Doğrulama Raporu

| Belge bilgisi | Değer |
|---|---|
| Belge sürümü | 1.0 |
| Tarih | 31 Temmuz 2026 |
| Hazırlayan | [Ad Soyad] |
| Proje | 9600 bit/s CPFSK–NRZ-I–G3RUH alıcısı |
| Test ortamı | GNU Radio 3.10.12.0, Windows |
| Durum | CPFSK demodülasyonu ve hat kodu çözümü kabul edildi |
| Dağıtım | Kurum içi |

---

## 1. Yönetici özeti

Bu çalışma kapsamında 576 ksample/s hızında örneklenmiş `complex64` IQ kayıt
dosyasındaki 9600 bit/s CPFSK sinyalinin yazılımsal olarak demodüle edilmesi
amaçlanmıştır.

İlk alıcı zincirinde kullanılan DC Blocker, AGC, hatalı sink örnekleme hızı ve
bir denemedeki yanlış samples-per-symbol ayarı nedeniyle sembol seviyeleri
geniş dağılım göstermiş ve çıktı güvenilir biçimde yorumlanamamıştır. Sinyal
dosyası üzerinde yapılan doğrudan ölçümler sonucunda iki CPFSK tonunun yaklaşık
8,60 kHz ve 15,66 kHz'de olduğu, ton merkezinin +12,121 kHz kaydığı ve frekans
sapmasının yaklaşık ±3,525 kHz olduğu belirlenmiştir.

Alıcı zinciri aşağıdaki şekilde yeniden oluşturulmuştur:

```text
IQ File Source
 -> Quadrature Demod
 -> sabit frekans merkezi düzeltmesi
 -> 60 tap matched FIR
 -> Symbol Sync
 -> Binary Slicer
 -> NRZ-I Differential Decoder
 -> G3RUH Descrambler
 -> bit/byte hizalama
 -> Pack K Bits
 -> binary File Sink
```

Nihai Symbol Sync çıkışında yaklaşık -0,974 ve +0,977 merkezli iki dar küme
elde edilmiştir. Sıfır karar bölgesinde örnek kalmamıştır. 125.609 sembol
üretilmiş, NRZ-I sonrası descramble öncesi çıktı 15.701 byte olmuştur.

Descramble öncesi çıktı yüksek entropili ve rastgele görünmüştür. G3RUH
`1+x^12+x^17` polynomial'i uygulandığında 15.697 byte'ın tamamının `0x7E`
olduğu görülmüştür. `0x7E`, HDLC flag/idle değeridir. Bu sonuç CPFSK
demodülasyonu, sembol zamanlaması, slicer polaritesi, NRZ-I çözümü, G3RUH
polynomial'i ve byte hizasının birlikte doğru olduğunu çok güçlü biçimde
doğrulamaktadır.

Sonuç olarak fiziksel demodülasyon ve hat kodu çözümü kabul edilmiştir. Bununla
birlikte IQ kaydı yalnız HDLC idle flag içerdiği için gerçek payload, frame
alanları ve CRC başarısı bu kayıtla doğrulanamamıştır.

---

## 2. Amaç ve kapsam

### 2.1 Amaç

- Complex IQ dosyasını doğru formatta işlemek
- 9600 bit/s CPFSK işaretini demodüle etmek
- Frekans kaymasını gidermek
- Sembol saatini kurtarmak
- Hard bit kararlarını üretmek
- NRZ-I hat kodunu çözmek
- Varsa scrambling yöntemini belirlemek ve geri almak
- Bit akışını hexadecimal incelenebilir byte'lara dönüştürmek
- Sonucu sayısal ve tekrarlanabilir testlerle doğrulamak

### 2.2 Kapsam

Bu rapor aşağıdaki katmanları kapsar:

```text
IQ örnekleri
 -> fiziksel CPFSK demodülasyonu
 -> sembol kurtarma
 -> hard decision
 -> NRZ-I decoding
 -> G3RUH descrambling
 -> HDLC flag gözlemi
```

HDLC frame extraction, bit de-stuffing, AX.25 alanlarının ayrıştırılması ve
CRC/FCS doğrulaması kapsam dışındadır; bunlar sonraki geliştirme aşaması olarak
önerilmiştir.

---

## 3. Test girdileri ve izlenebilirlik

### 3.1 Dosyalar

| Dosya | Boyut | SHA-256 |
|---|---:|---|
| `intern_Rec.bin` | 60.293.120 byte | `2249095B3A18FD95FDD90FD5CA8AFD0B92CBDFD7C4926279A8F5ED17BE5B100E` |
| `decoded_bits.bin` | 15.701 byte | `E13D0B0039061EB1E76ECE2EE68CB94F5EA65DA88D33F80F3E6339262B14C860` |
| `decoded_bits_g3ruh.bin` | 15.697 byte | `9873C129FE562CC74B72BB4A3DFA53242C5B7C7365852B36574F4923FE43E8F4` |
| `cpfsk_9600_nrzi_g3ruh.grc` | 14.363 byte | `6D7EA8BDC3EA9C27FC945DFFC81BAD7E8FC394BC1FC2E78D23652440C2ABF3D9` |

Hash değerleri test edilen dosya sürümlerinin daha sonra aynen
tanımlanabilmesi için rapora eklenmiştir.

### 3.2 Girdi konfigürasyonu

| Parametre | Değer |
|---|---:|
| IQ veri tipi | `complex64` |
| Örnek başına boyut | 8 byte |
| Complex örnek sayısı | 7.536.640 |
| Örnekleme hızı | 576.000 sample/s |
| Bit hızı / sembol hızı | 9.600 bit/s / 9.600 symbol/s |
| Nominal SPS | 60 |
| Kayıt süresi | 13,084444 s |

---

## 4. Kullanılan nihai alıcı konfigürasyonu

### 4.1 Ölçülen sinyal parametreleri

| Parametre | Değer |
|---|---:|
| Alt CPFSK tonu | yaklaşık 8,60 kHz |
| Üst CPFSK tonu | yaklaşık 15,66 kHz |
| Frekans merkezi `f_mid` | 12.121 Hz |
| Frekans sapması `f_dev` | 3.525 Hz |
| Ton ayrımı | yaklaşık 7.050 Hz |
| Tahmini modülasyon indeksi | yaklaşık 0,734 |

### 4.2 Kritik blok parametreleri

| Blok | Parametre | Değer |
|---|---|---:|
| Quadrature Demod | Gain | 26,0065949563 |
| Add Const | Constant | -3,4385815603 |
| FIR Filter | Taps | 60 adet `1/60` |
| FIR Filter | Decimation | 1 |
| Symbol Sync | TED | Zero Crossing |
| Symbol Sync | SPS | 60 |
| Symbol Sync | Loop bandwidth | 0,01 |
| Symbol Sync | Expected TED gain | 0,5 |
| Symbol Sync | Damping | 1,0 |
| Symbol Sync | Maximum deviation | 0,2 |
| Symbol Sync | Output SPS | 1 |
| Differential Decoder | Coding | NRZ-I |
| Descrambler | Mask | `0x21` |
| Descrambler | Seed | `0x0` |
| Descrambler | Length | 16 |
| Skip Head | Num items | 31 bit |
| Pack K Bits | K | 8 |

Quadrature Demod kazancı:

```text
576000/(2*pi*3525) = 26,0065949563
```

Normalize edilmiş merkez düzeltmesi:

```text
-12121/3525 = -3,4385815603
```

---

## 5. İlk tasarımda bulunan sorunlar ve düzeltici faaliyetler

| No | Bulgulanan sorun | Etki | Düzeltici faaliyet |
|---:|---|---|---|
| 1 | Quadrature Demod gain ölçülen sapmaya göre ayarlı değildi | Soft sembol genliği yanlış ölçeklendi | Gain fiziksel formülle 26,0066 yapıldı |
| 2 | DC Blocker NRZ seviyelerinin düşük frekans içeriğini bastırdı | İki seviye sıfıra doğru yayıldı | DC Blocker kaldırılıp sabit Add Const kullanıldı |
| 3 | Float AGC bozulmuş seviyeleri dinamik büyüttü | Küme genişliği arttı | AGC kaldırıldı |
| 4 | Matched filter bulunmuyordu | Sembol merkezindeki ripple/gürültü yüksekti | 60 tap moving-average FIR eklendi |
| 5 | Bir denemede SPS=4, giriş hâlâ 576 ksample/s idi | Yaklaşık 15 kat fazla sembol/byte üretildi | SPS=60 yapıldı |
| 6 | Time Sink 576 ksample/s idi | Zaman ekseni 60 kat hatalıydı | Sink hızı 9,6 ksample/s yapıldı |
| 7 | NRZ-I decoder yoktu | Çıkış kullanıcı biti değildi | Differential Decoder eklendi |
| 8 | Scrambling dikkate alınmamıştı | Hex çıktı rastgele görünüyordu | G3RUH Descrambler eklendi |
| 9 | Byte hizası capture başlangıcına bağlıydı | Flag byte'ları kaymış görünüyordu | Bu kayıt için 31 bit Skip Head eklendi |

---

## 6. Test yöntemi

Doğrulama yalnız grafik gözlemine dayandırılmamıştır. Aşağıdaki yaklaşım
kullanılmıştır:

1. Dosya boyutundan complex örnek sayısı ve süre hesaplandı.
2. IQ genlik istatistikleri çıkarıldı.
3. Ardışık complex örneklerin faz farkından anlık frekans hesaplandı.
4. Frekans histogramından iki ton, merkez ve sapma ölçüldü.
5. Aday SPS değerlerinde periyodik geçiş enerjisi incelendi.
6. GNU Radio Symbol Sync farklı TED seçenekleriyle çalıştırıldı.
7. Soft-decision kümeleri iki-küme analiziyle ölçüldü.
8. Sembol ve packed-byte sayıları teorik değerlerle karşılaştırıldı.
9. Pack K Bits çıkışının bit sırası manuel `packbits` sonucu ile
   karşılaştırıldı.
10. Descramble öncesi dosyanın byte histogramı, bit dengesi ve entropisi
    ölçüldü.
11. G3RUH polynomial hipotezi bit seviyesinde uygulandı.
12. Descramble sonrası HDLC flag sayısı, periyodu ve byte içeriği kontrol
    edildi.
13. Aynı zincir GNU Radio Descrambler bloğuyla tekrar çalıştırıldı.
14. Nihai dosyanın tamamının `0x7E` olduğu otomatik olarak doğrulandı.

---

## 7. Test senaryoları ve sonuçları

### TC-01 — IQ dosya formatı ve örnek sayısı

**Amaç:** Dosyanın `complex64` olarak tutarlı olduğunu doğrulamak.

**Yöntem:** Dosya boyutu 8 byte/sample'a bölündü; I/Q değerlerinde NaN/Inf ve
tam sıfır oranı kontrol edildi.

**Sonuç:**

```text
60.293.120/8 = 7.536.640 complex sample
finite sample oranı = %100
```

**Karar:** GEÇTİ.

### TC-02 — Kayıt süresi ve SPS tutarlılığı

**Amaç:** Örnekleme ve sembol hızı ilişkisinin doğrulanması.

**Sonuç:**

```text
süre = 7.536.640/576.000 = 13,084444 s
SPS  = 576.000/9.600 = 60
```

**Karar:** GEÇTİ.

### TC-03 — Sabit zarf kontrolü

**Amaç:** Sinyalin sabit zarflı frekans modülasyonuyla uyumluluğunu kontrol
etmek.

**Sonuç:**

```text
ortalama |x| = 0,23905
std(|x|) = 0,00497
```

Genlik değişimi düşüktür ve CPFSK davranışıyla uyumludur.

**Karar:** GEÇTİ.

### TC-04 — İki frekans seviyesinin ölçülmesi

**Amaç:** Binary CPFSK tonlarının mevcut olduğunu doğrulamak.

**Sonuç:** Yaklaşık 8,60 kHz ve 15,66 kHz seviyeleri bulundu. Merkez yaklaşık
12,121 kHz ve sapma yaklaşık ±3,525 kHz olarak ölçüldü.

**Karar:** GEÇTİ.

### TC-05 — Hatalı ve düzeltilmiş ön işleme karşılaştırması

**Amaç:** DC Blocker + AGC zincirinin sorunun kaynağı olduğunu doğrulamak.

**Yöntem:** Aynı kayıt, ilk ve düzeltilmiş zincirlerle işlendi.

**Sonuç:** İlk zincir geniş ve merkeze yayılan sembol dağılımı üretirken sabit
merkez düzeltmesi + matched FIR zinciri iki dar küme üretmiştir.

**Karar:** GEÇTİ; düzeltici faaliyet etkili.

### TC-06 — Symbol Sync çıkış sayısı

**Amaç:** 60 SPS zamanlama kurtarmasının doğru output rate ürettiğini kontrol
etmek.

**Teorik:**

```text
7.536.640/60 = 125.610,67 symbol
```

**Ölçülen:**

```text
125.609 symbol
```

Başlangıç filtre/senkronizer gecikmesi dikkate alındığında sonuç uyumludur.

**Karar:** GEÇTİ.

### TC-07 — Soft-decision küme kalitesi

**Amaç:** Slicer girişinde iki güvenilir sembol seviyesi bulunduğunu doğrulamak.

**Sonuç:**

| Ölçüm | Değer |
|---|---:|
| Alt küme merkezi | -0,974409 |
| Üst küme merkezi | +0,976607 |
| Küme hata RMS'i | 0,023007 |
| `|x|<0,5` oranı | 0 |

Sıfır karar eşiği çevresinde örnek bulunmamıştır.

**Karar:** GEÇTİ.

### TC-08 — Packed çıktı uzunluğu

**Amaç:** 1 bit/sembol ve 8 bit/byte dönüşümünün tutarlılığını kontrol etmek.

**Sonuç:**

```text
floor(125.609/8) = 15.701 byte
ölçülen = 15.701 byte
```

**Karar:** GEÇTİ.

### TC-09 — Pack K Bits bit sırası

**Amaç:** Hexadecimal byte yorumunun doğru bit sırasına dayandığını doğrulamak.

**Yöntem:** GNU Radio packed dosyası, aynı NRZ-I çıkışının manuel MSB-first ve
LSB-first paketlenmiş sürümleriyle karşılaştırıldı.

**Sonuç:**

```text
MSB-first eşleşme = %100
LSB-first eşleşme ≈ %6,37
```

**Karar:** GEÇTİ; bu akışta dosya MSB-first yorumlanmıştır.

### TC-10 — Scrambling belirtisi

**Amaç:** NRZ-I sonrası verinin scrambling/whitening belirtisi taşıyıp
taşımadığını incelemek.

**Sonuç:**

| Ölçüm | Değer |
|---|---:|
| Byte sayısı | 15.701 |
| Farklı byte değeri | 256/256 |
| Shannon entropisi | 7,9873049 bit/byte |
| 1-bit oranı | 0,4990486 |
| `0x00` oranı | 0,004586 |
| `0xFF` oranı | 0,003312 |

Çıktı yüksek entropilidir. Bu bulgu scrambling ile uyumludur fakat tek başına
kanıt sayılmamıştır.

**Karar:** İLERİ TEST GEREKTİRDİ.

### TC-11 — G3RUH polynomial doğrulaması

**Amaç:** Scrambling yönteminin kesin olarak belirlenmesi.

**Yöntem:** NRZ-I çıkışına G3RUH `1+x^12+x^17` descrambling uygulandı. GNU Radio
karşılığı `mask=0x21`, `length=16` olarak kullanıldı.

**Sonuç:**

- İlk geçerli HDLC flag bit 31'de başladı.
- Flag başlangıçları bundan sonra tam 8 bit aralıkla devam etti.
- 15.697 ardışık `0x7E` bulundu.
- Geçerli çıktı bölgesinde başka byte değeri bulunmadı.

**Karar:** GEÇTİ; G3RUH scrambling kesin olarak doğrulandı.

### TC-12 — Nihai dosya bütünlük testi

**Amaç:** GNU Radio'dan üretilen nihai dosyanın beklenen içerikle tamamen
eşleştiğini doğrulamak.

**Sonuç:**

```text
dosya boyutu = 15.697 byte
0x7E sayısı  = 15.697
diğer byte   = 0
all_7e       = True
```

**Karar:** GEÇTİ.

---

## 8. Kabul kriterleri özeti

| Kabul kriteri | Hedef | Ölçülen | Durum |
|---|---:|---:|---|
| IQ örnek bütünlüğü | %100 finite | %100 | GEÇTİ |
| SPS | 60 | 60 | GEÇTİ |
| İki frekans seviyesi | Görülmeli | 8,60/15,66 kHz | GEÇTİ |
| Symbol Sync küme sayısı | 2 | 2 | GEÇTİ |
| Küme karar marjı | Sıfır çevresi boş | `|x|<0,5` oranı 0 | GEÇTİ |
| Sembol sayısı | Yaklaşık 125.611 | 125.609 | GEÇTİ |
| Packed byte sayısı | 15.701 | 15.701 | GEÇTİ |
| Pack bit sırası | Belirlenmeli | MSB-first, %100 eşleşme | GEÇTİ |
| Scrambler türü | Belirlenmeli | G3RUH `1+x^12+x^17` | GEÇTİ |
| Descramble çıktısı | Yapı göstermeli | 15.697 adet `0x7E` | GEÇTİ |
| Payload doğrulaması | Frame/CRC | Kayıtta payload yok | UYGULANAMADI |

---

## 9. Bulguların yorumu

### 9.1 CPFSK demodülasyonu başarılı mı?

Evet. Quadrature Demod ile complex IQ faz farkı anlık frekans işaretine
dönüştürülmüş, iki frekans durumu -1/+1 sembol seviyeleri olarak ayrılmıştır.
Histogramda iki dar kümenin oluşması ve G3RUH sonrasında kesintisiz HDLC flag
elde edilmesi demodülasyonun başarılı olduğunu gösterir.

### 9.2 Timing recovery başarılı mı?

Evet. Çıkış sembol sayısı teorik değerle uyumludur; soft-decision kümeleri
dardır ve karar eşiği çevresinde örnek yoktur.

### 9.3 NRZ-I decoding başarılı mı?

Evet. NRZ-I sonrası G3RUH descrambling tam `0x7E` dizisi üretmiştir. Yanlış
polarite veya yanlış NRZ-I sırası bu sonucu üretmezdi.

### 9.4 Scrambling var mı?

Evet. `1+x^12+x^17` G3RUH scrambling kesin olarak doğrulanmıştır. Yalnız yüksek
entropi değil, polynomial geri alındığında oluşan 15.697 kesintisiz HDLC flag bu
kararın temel kanıtıdır.

### 9.5 Payload çözüldü mü?

Hayır; bunun nedeni alıcının başarısız olması değil, test kaydının yalnız HDLC
idle flag içermesidir. Payload içeren IQ kaydı sağlandığında aynı zincirin
arkasına HDLC deframer ve CRC kontrolü eklenerek payload doğrulanabilir.

---

## 10. Riskler ve sınırlamalar

| Risk/sınırlama | Etki | Öneri |
|---|---|---|
| Sabit `f_mid` kullanımı | Canlı frekans drift'inde kümeler kayabilir | AFC veya otomatik merkez tahmini ekle |
| Sabit `Skip Head=31` | Farklı kayıt başlangıcında byte hizası bozulur | HDLC flag tabanlı otomatik deframer kullan |
| Payload içermeyen test kaydı | Frame alanları ve CRC doğrulanamadı | Payload içeren yeni IQ kaydı al |
| Kanal filtresinin olmaması | Geniş bant/canlı girişte komşu kanal etkisi | Frequency Xlating FIR Filter ekle |
| Tek SNR koşulu | Düşük SNR dayanımı bilinmiyor | Kontrollü SNR/BER sweep yap |
| Sabit sembol hızı varsayımı | Büyük clock error'da lock kaybı olabilir | Clock offset testi ve loop parametre sweep'i yap |

---

## 11. Sonuç ve karar

Yapılan ölçümler ve tekrarlanabilir testler sonucunda:

1. IQ dosyasının formatı ve örnekleme parametreleri doğrulanmıştır.
2. Binary CPFSK iki frekans seviyesi doğru biçimde ayrılmıştır.
3. Frekans merkez kayması giderilmiştir.
4. 60 SPS sembol zamanlaması başarıyla kurtarılmıştır.
5. Soft-decision kümeleri güvenilir hard decision için yeterli marja sahiptir.
6. NRZ-I hat kodu çözülmüştür.
7. G3RUH `1+x^12+x^17` scrambling yöntemi kesin olarak belirlenmiş ve geri
   alınmıştır.
8. Nihai çıktı 15.697 adet kesintisiz HDLC `0x7E` flag olarak doğrulanmıştır.

**Nihai karar:** CPFSK demodülasyonu, sembol kurtarma, NRZ-I decoding ve G3RUH
descrambling fonksiyonları bu test kaydı için **BAŞARILI / KABUL** edilmiştir.

Payload/frame-level kabul kararı, payload taşıyan yeni bir IQ kaydı üzerinde
HDLC deframing ve CRC/FCS kontrolünden sonra ayrıca verilmelidir.

---

## 12. Teslimatlar

| Teslimat | Açıklama |
|---|---|
| `cpfsk_9600_nrzi_g3ruh.grc` | Nihai GNU Radio Companion flowgraph |
| `cpfsk_9600_nrzi_g3ruh.py` | Üretilmiş Python flowgraph |
| `decoded_bits.bin` | NRZ-I sonrası scrambled packed çıktı |
| `decoded_bits_g3ruh.bin` | G3RUH sonrası hizalanmış HDLC flag çıktısı |
| `cpfsk_teshis.png` | Sinyal ve sembol seviyesi teşhis grafiği |
| `01_CPFSK_Proje_Adim_Adim_Teknik_Rehber.md` | Ayrıntılı öğretici proje dokümanı |
| `02_CPFSK_Test_ve_Dogrulama_Raporu.md` | Bu test ve doğrulama raporu |

---

## Ek A — Hexadecimal kanıt

### Descramble öncesi

```hex
1E 05 3D 2D B0 B1 2F B6 90 4E B0 30 A7 EE D1 E6
8A 67 1F BE 88 CB 34 2A 24 4B AA 63 8F F5 C4 5A
```

### G3RUH descramble ve hizalama sonrası

```hex
7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E
7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E
```

Dosyanın kalan bütün byte'ları da `0x7E`'dir.

---

## Ek B — Formüller

```text
SPS = Fs/Rs = 576000/9600 = 60

Quadrature Demod gain
= Fs/(2*pi*f_dev)
= 576000/(2*pi*3525)
= 26,0065949563

Normalize frekans merkezi düzeltmesi
= -f_mid/f_dev
= -12121/3525
= -3,4385815603

Teorik sembol sayısı
= 7.536.640/60
= 125.610,67

Ölçülen sembol sayısı
= 125.609

NRZ-I sonrası packed byte
= floor(125.609/8)
= 15.701

G3RUH sonrası hizalanmış byte
= 15.697
```

---

