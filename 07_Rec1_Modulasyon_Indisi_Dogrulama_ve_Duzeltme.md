# Rec1 Modülasyon İndisi Doğrulama ve Düzeltme Notu

## 1. Nihai sonuç

`intern_Rec1().bin` için önerilen modülasyon indisi:

```text
h = 0.464 ± 0.003
```

İlgili etkin parametreler:

```text
Rs              = 9601.259 Bd
SPS             = 59.992132 sample/symbol
f_low, etkin    = -2.120 kHz
f_high, etkin   = +2.336 kHz
merkez          = +0.108 kHz
ton ayrımı      = 4.456 kHz
Δf              = 2.228 kHz
h               = 4456 / 9601.259 ≈ 0.464
```

Önceki `h≈0.657` değeri geçersizdir ve geri çekilmiştir.

## 2. Önceki hesap neden yanlıştı?

Önceki hesapta anlık frekans histogramındaki dış tepeler yaklaşık tonlar olarak kullanılmıştı:

```text
anlık dış tepeler ≈ -3.06 kHz ve +3.25 kHz
anlık dış ayrım   ≈ 6.31 kHz
yanlış h          ≈ 6.31/9.6 = 0.657
```

Bu işlem, tam-tepkili dikdörtgen CPFSK için uygulanabilir; çünkü o durumda sembol boyunca anlık frekans yaklaşık sabittir. Rec1'de frekans darbesi sembol içinde değişmekte ve komşu sembollere yayılmaktadır. Dış histogram tepeleri sembol içi anlık maksimumlardır; bir sembolde biriken toplam fazı temsil etmez.

CPM/CPFSK için genel ve güvenli tanım faz artımı üzerinden yapılmalıdır:

```text
h = Δφ_sembol / π
```

Binary ve simetrik durumda eşdeğer olarak:

```text
h = (f_high,etkin - f_low,etkin)/Rs
```

Buradaki etkin frekanslar, kurtarılan sembol aralığındaki toplam fazın sembol süresine bölünmesiyle bulunur; anlık maksimumlar değildir.

## 3. Sembol hızı doğrulaması

Rec1 için 19.2 kBd olasılığı ayrıca test edilmiştir. Frekans işareti farklı örnek aralıklarında örneklendiğinde geçiş olasılıkları:

| Örnek aralığı | Eşdeğer hız | Geçiş olasılığı |
|---:|---:|---:|
| 15 örnek | 38.4 kHz | 0.1254 |
| 30 örnek | 19.2 kHz | 0.2508 |
| 60 örnek | 9.6 kHz | 0.4970 |
| 120 örnek | 4.8 kHz | 0.5004 |

Bu sonuç, bit durumunun yaklaşık 60 örnek boyunca tutulduğunu gösterir. Dolayısıyla gerçek sembol hızı yaklaşık 9.6 kBd'dir; 19.2 kBd değildir.

Sıfır-geçiş zamanları arasındaki uzaklıkların tam sembol katlarına regresyonu:

```text
SPS = 59.992131746
Rs  = 576000/SPS = 9601.259086 Bd
```

Sabit `SPS=60` kabulü saniyede yaklaşık `-75.5` örnek zamanlama kayması üretmektedir. Önceki saniyelik tahminlerde görülen periyodik dalgalanmanın nedeni budur.

## 4. Faz-integralli ölçüm

Fractional sembol sınırlarında her sembolün faz artımı integral olarak hesaplanmıştır. Ardından aynı-bit koşuları bulunmuş ve her koşudaki toplam faz, koşu uzunluğuna karşı doğrusal olarak modellenmiştir:

```text
toplam frekans alanı = f_steady · koşu_uzunluğu + kenar_geçişi
```

Doğrunun eğimi, pulse-shape kenar etkisinden bağımsız yerleşmiş etkin frekansı verir:

```text
f_low  = -2117.67 Hz
f_high = +2335.91 Hz
Δf     = (f_high-f_low)/2 = 2226.79 Hz
h      = (f_high-f_low)/9601.259 = 0.46385
```

Birer saniyelik pencerelerde aynı yöntemin sonucu:

```text
ortalama h = 0.46411
std(h)     = 0.00294
min/max    = 0.46086 / 0.47058
```

61 farklı sembol-epoch denemesinde:

```text
medyan h   = 0.46434
std(h)     = 0.00074
min/max    = 0.46211 / 0.46572
```

Bu nedenle raporlanabilir yuvarlatılmış değer `h=0.464±0.003` seçilmiştir.

## 5. Yöntem çapraz doğrulaması

Aynı fractional-clock ve koşu-alanı regresyonu diğer kayıtlara uygulandığında:

| Kayıt | Regresyon sonucu | Önceki güvenilir sonuç |
|---|---:|---:|
| A | 0.73235 | 0.732±0.013 |
| B | **0.46385** | Eski 0.657 hatalı |
| C | 0.61422 | 0.614±0.002 |

A ve C'nin bağımsız ölçümlerle aynı sonuçları vermesi, B için kullanılan faz-integralli yöntemi doğrulamaktadır.

## 6. GNU Radio parametre etkisi

Rec1 için normalize Quadrature Demod başlangıç değeri:

```text
gain = Fs/(2πΔf)
     = 576000/(2π·2226.79)
     ≈ 41.17
```

Normalize merkez düzeltmesi:

```text
Add Const = -f_center/Δf
          = -109.12/2226.79
          ≈ -0.049
```

Symbol Sync için:

```text
Expected SPS = 59.99213
```

Pratikte 60 başlangıç değeri kullanılabilir; ancak timing loop'un bu yaklaşık `%0.0131` oranındaki saat farkını takip etmesine izin verilmelidir.

Bu düzeltme yalnız ölçek ve zamanlamayı düzeltir. Rec1'deki pulse-shaped/partial-response yapı nedeniyle 60-tap boxcar ve Binary Slicer'ın optimal alıcı olduğu sonucu çıkmaz.

## 7. Düzeltilen sonuçlar

- `04_Iki_IQ_Kaydi_Karsilastirma_Raporu.md`
- `06_Uc_IQ_Kaydi_Kapsamli_Karsilastirma_Raporu.md`
- `uc_iq_karsilastirma.png`
- `uc_iq_karsilastirma_ozeti.json`
- `uc_iq_h_zaman_serisi.csv`
- `iki_iq_karsilastirma.png`
- `iq_model_duyarlı_özet.json`

Derin doğrulama ham sonuçları:

- `rec1_h_derin_dogrulama.json`
- `rec1_h_hassasiyet.json`
- `uc_iq_hassas_sembol_hizi.json`
- `uc_iq_uzun_kosu_h_dogrulama.json`
- `uc_iq_kosu_regresyon_h.json`
- `uc_iq_fractional_clock_h.json`
- `rec1_h_saniyelik_duzeltilmis.json`

