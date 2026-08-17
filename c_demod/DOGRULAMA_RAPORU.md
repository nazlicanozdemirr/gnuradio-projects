# C CPFSK Demodülatörü Doğrulama Raporu

## 1. Test amacı

Bu testin amacı `intern_Rec().bin`, `intern_Rec1().bin` ve `intern_Rec2().bin` complex64 IQ kayıtlarının GNU Radio kullanılmadan, yalnızca C içinde yazılmış DSP algoritmalarıyla doğru şekilde demodüle edilebildiğini göstermektir.

Başarı ölçütleri:

1. IQ dosyasının biçim ve uzunluk kontrolünden geçmesi.
2. Sembol kararlarının iki ayrı frekans durumuna ayrılması.
3. Bit oranı ve geçiş oranının scrambled veri için beklenen yaklaşık `%50` değerinde olması.
4. NRZ-I ve G3RUH çözümünden sonra HDLC `0x7E` bayraklarının ortaya çıkması.
5. Bayrakların aynı bit/bayt fazında ve 8 bit periyotla kayıt boyunca sürmesi.
6. Yanlış NRZ-I kuralının aynı sonucu üretmemesi.

## 2. Test koşulları

```text
Platform              : Windows 11
Uygulama               : c_demod/cpfsk_demod.exe
Kaynak dil             : ISO C11
Derleyici              : GCC/MinGW-w64, -O2 -Wall -Wextra -Wpedantic
Harici DSP bağımlılığı : Yok
Giriş formatı          : little-endian float32 I,Q; complex64
Fs                     : 576000 sample/s
Rs                     : 9600 symbol/s
Nominal SPS            : 60
```

Üç dosya aşağıdaki komutla topluca test edilmiştir:

```powershell
powershell -ExecutionPolicy Bypass -File .\c_demod\run_all.ps1
```

## 3. DSP ve veri-zinciri konfigürasyonu

| Özellik | A | B / Rec1 | C |
|---|---:|---:|---:|
| Merkez frekans | −872.045 Hz | +108.082 Hz | −123.636 Hz |
| Etkin deviation | 3515.455 Hz | 2228.043 Hz | 2947.500 Hz |
| Modülasyon indisi | 0.732386 | **0.464176** | 0.614063 |
| Sembol karar yöntemi | 60 örnek integral | orta nokta + timing PLL | 60 örnek integral |
| NRZ-I kuralı | 1 = geçiş yok | 1 = geçiş yok | 1 = geçiş yok |
| Descrambler | G3RUH 17/12 | G3RUH 17/12 | G3RUH 17/12 |
| Bayt bit sırası | LSB-first | LSB-first | LSB-first |

## 4. Test sonuçları

| Ölçüm | A | B / Rec1 | C |
|---|---:|---:|---:|
| IQ örneği | 7,438,336 | 12,779,520 | 7,077,888 |
| Kurtarılan sembol | 123,971 | 212,997 | 117,964 |
| 1 oranı | 0.500916 | 0.498838 | 0.500551 |
| Line geçiş oranı | 0.498693 | 0.499704 | 0.502853 |
| İki küme kalite skoru | 5.587 | 10.429 | 5.409 |
| G3RUH sonrası bit-level HDLC flag | 15,492 | 26,622 | 14,742 |
| Hizalı `0x7E` baytı | 15,492 | 26,621 | 14,742 |
| En iyi bit ofseti | 3 | 7 | 7 |
| Ters NRZ-I + descramble flag | 0 | 0 | 0 |
| CRC-geçerli payload frame | 0 | 0 | 0 |

HDLC flag'lerinin bit kapsama oranı:

| Kayıt | Flaglerin kapsadığı bit oranı |
|---|---:|
| A | %99.9726 |
| B / Rec1 | %99.9906 |
| C | %99.9771 |

İlk descrambler geçicisinden sonraki hex çıktı:

```text
A: 4F D4 7D 7E 7E 7E 7E 7E ... 7E
B: 60 47    7E 7E 7E 7E 7E ... 7E
C: 33 36    7E 7E 7E 7E 7E ... 7E
```

A'da ilk üç, B ve C'de ilk iki bayt dışındaki bütün hizalı baytlar `0x7E`'dir. Başlangıç baytları; discriminator'ın ilk örneğinin olmaması, NRZ-I'nin önceki line durumuna ihtiyaç duyması, 17 bitlik descrambler durumunun bilinmemesi ve dosyanın bir protokol bayt sınırında başlamaması nedeniyle geçicidir.

## 5. Rec1 zamanlama düzeltmesinin doğrulanması

İlk sabit-clock uygulamasında Rec1 için bit düzeyinde 26,266 flag bulunmasına rağmen en iyi sabit bayt fazında yalnızca 3,429 adet `0x7E` görülüyordu. Flag başlangıçları sekiz farklı modulo-8 fazına dağılıyordu. Bu, frekans kararlarının büyük ölçüde doğru fakat uzun kayıt boyunca sembol saatinin seyrek olarak kaydığını gösterdi.

Geçiş destekli timing PLL eklendikten sonra:

```text
Zamanlama güncellemesi      = 106435
Timing error RMS            = 0.2923 sample
Başlangıç nominal SPS       = 60.0000
Takip sonundaki SPS         = 59.9967
Bit-level HDLC flag         = 26622
Tek fazdaki hizalı 0x7E     = 26621
```

26,622 flag'in 26,621'inin tek bir bayt fazında bulunması, Rec1 zamanlama probleminin giderildiğinin doğrudan göstergesidir.

## 6. Rec1 modülasyon indisi kararı

Rec1'in sembol ortasındaki anlık frekans kümeleri yaklaşık:

```text
alt küme = −3152.84 Hz
üst küme = +3367.95 Hz
```

Bu dış değerlerin farkını doğrudan ton ayrımı kabul etmek doğru değildir; Rec1'de pulse shaping nedeniyle anlık frekans darbesi komşu sembollere yayılır. Modülasyon indisi, sembolde biriken faz alanından bulunan etkin frekans ayrımıyla hesaplanmıştır:

```text
Etkin Δf = 2228.043 Hz
h = 2·Δf/Rs
h = 2·2228.043/9600
h = 0.464176
```

Bağımsız uzun-koşu faz-alanı regresyonu ve zaman penceresi testleri dikkate alınarak raporlanacak değer:

```text
Rec1 modülasyon indisi: h = 0.464 ± 0.003
```

Önceki yaklaşık `0.657` veya anlık tepelere göre yaklaşık `0.68` sonucu, pulse-shaped sinyalde yanlış ölçüm tanımı kullandığı için geçersizdir.

## 7. CRC sonucunun yorumu

Üç kayıtta da `CRC OK = 0` elde edilmiştir. Bu bir başarısızlık değildir. Descramble sonrası veri neredeyse tamamen bitişik HDLC idle flag'lerinden oluşmaktadır:

```text
... 7E 7E 7E 7E 7E ...
```

İki flag arasında payload, adres, kontrol ve FCS içeren bir frame olmadığı için CRC uygulanacak aday frame yoktur. Doğru ifade “CRC hatalı frame bulundu” değil, “kayıtta payload frame bulunmadı”dır.

## 8. Kabul kararı

Test sonucu **başarılıdır**.

- Üç complex64 kayıt C uygulamasıyla okunmuştur.
- CPFSK frekans discriminator çıkışından semboller kurtarılmıştır.
- Frekans kaymaları giderilmiştir.
- Rec1'in pulse-shaped yapısı ve saat kayması özel olarak ele alınmıştır.
- NRZ-I çözme ve G3RUH descramble sırası veriyle doğrulanmıştır.
- Sonuçta üç kaydın da neredeyse tamamı doğru periyotlu HDLC `0x7E` idle bayraklarına dönüşmüştür.
- Ters NRZ-I kontrol yolunda hiç flag çıkmaması, sonucun tesadüfi olmadığını desteklemektedir.

Bu kayıtlar için doğrulanmış nihai bilgi, payload mesaj değil HDLC idle dizisidir. Gerçek bir üst katman çerçevesini doğrulamak için payload içeren ek bir IQ kaydı gereklidir.
