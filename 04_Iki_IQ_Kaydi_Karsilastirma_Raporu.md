# İki IQ Kaydının CPFSK/CPM Karşılaştırma Raporu

## 1. Amaç ve kapsam

Bu rapor aşağıdaki iki ham IQ kaydını karşılaştırır:

| Kısa ad | Kaynak dosya | SHA-256 |
|---|---|---|
| Kayıt A | `intern_Rec().bin` | `C6F270A430A55549979AC9103053F40F7851A1CF52D33F7FB54ECC7314FB47F3` |
| Kayıt B | `intern_Rec1().bin` | `50CFFAEB4F00CF6C9F536BDDD1731D5BA1F4AEBA7F40F71F9D0D628AD7A3ED60` |

Analizde dosyaların little-endian `complex64` olduğu, örnekleme hızının 576 kS/s ve nominal sembol hızının 9.6 kBd olduğu kabul edilmiştir. Böylece nominal örnek/sembol oranı:

```text
SPS = Fs / Rs = 576000 / 9600 = 60 örnek/sembol
```

Ölçülen frekanslar, kayıt merkezine göre baseband frekanslarıdır. Mutlak RF taşıyıcı frekansı değildir.

## 2. Yönetici özeti

İki dosya aynı sayısal örnek formatında ve ikisinde de 9.6 kBd sembol saatine ilişkin çizgiler bulunmasına rağmen, aynı CPFSK dalga biçimini göstermemektedir.

- Kayıt A, iki belirgin frekans seviyesi olan klasik/tam-tepkili ikili CPFSK görünümündedir. Önerilen modülasyon indisi `h = 0.732 ± 0.013` değerindedir.
- Kayıt B daha dar spektrumludur ve anlık frekans dağılımında iki temiz seviye yerine dört ana ara seviye gösterir. Dış histogram tepeleri sembol içi anlık maksimumlardır ve `h` hesabında ton kabul edilmemelidir. Kurtarılan sembol saatinde toplam faz artımı kullanıldığında `h = 0.464 ± 0.003` bulunmuştur.
- B kaydının `h` değeri A'dan yaklaşık `%36.6` küçüktür.
- B kaydının RMS genliği A'dan 3.10 kat, yaklaşık 9.83 dB daha yüksektir. Bu değer mutlak alıcı gücü sayılmamalıdır; farklı analog/dijital kazançlar sonucu değiştirebilir.
- B kaydının `%99` işgal bant genişliği A'dan yaklaşık `%30.2` daha dardır.
- Kayıt A'da basit `Quadrature Demod → 1 sembollük integral → Symbol Sync → Binary Slicer` zinciri uygundur. Aynı zincirin Kayıt B'ye değişmeden uygulanması semboller arası belleği yok saydığı için güvenilir değildir.

## 3. Kullanılan ölçüm yöntemi

### 3.1 Dosya ve IQ bütünlüğü

Dosya boyutunun sekiz bayta tam bölünmesi kontrol edilmiştir. Her `complex64` örneği iki adet 32-bit kayan noktalı sayıdan oluşur. NaN/Inf kontrolü, I/Q ortalamaları, I/Q standart sapmaları, zarf ve PAPR değerleri hesaplanmıştır.

### 3.2 Anlık frekans ayrıştırıcısı

Ardışık karmaşık örnekler arasındaki faz farkı kullanılmıştır:

```text
f[n] = Fs/(2π) · arg{x[n] · conj(x[n-1])}
```

Bu işlem GNU Radio'daki `Quadrature Demod` bloğunun Hz ölçekli karşılığıdır. Frekans ofseti iki tonun ortak merkezini değiştirir, ton ayrımını ve doğru hesaplanan `h` değerini değiştirmez.

### 3.3 Sembol hızı doğrulaması

Frekans değişim enerjisinin periyodik bileşenleri incelenmiştir. Kayıt A'da 9.59985 kHz çizgisi açık biçimde baskındır. Kayıt B'de 9.59985 kHz çizgisi ile 19.2008 kHz ikinci harmonik görülmüştür. Bu gözlem 576 kS/s ve 60 SPS varsayımıyla uyumludur.

### 3.4 Modülasyon indisi

İkili CPFSK için kullanılan tanım:

```text
h = 2·Δf/Rs = (f_high - f_low)/Rs
```

Tam-tepkili CPFSK'de `Δf`, iki ton arasındaki ayrımın yarısıdır. Pulse-shaped/partial-response sinyalde ise anlık dış tepe frekansları doğrudan `Δf` değildir. Böyle bir sinyalde doğru büyüklük, kurtarılan bir sembol boyunca biriken fazın sembol süresine bölünmesiyle bulunan etkin ortalama frekanstır.

Kayıt B'de dört görünen seviye bağımsız dört sembol kabul edilmemiştir. Gerçek sembol hızı sıfır-geçiş zamanlarından `9601.26 Bd`, örnek/sembol oranı `59.99213` olarak ölçülmüştür. Aynı-bit koşularındaki toplam faz, koşu uzunluğuna karşı doğrusal olarak modellenmiş; doğrunun eğimleri etkin alt/üst frekans seviyelerini vermiştir. Aynı yöntem A üzerinde bilinen `h≈0.732` sonucunu yeniden ürettiği için yöntem çapraz doğrulanmıştır.

## 4. Sayısal sonuçlar

### 4.1 Dosya ve zaman bilgileri

| Özellik | Kayıt A | Kayıt B |
|---|---:|---:|
| Dosya boyutu | 59,506,688 bayt | 102,236,160 bayt |
| Karmaşık örnek sayısı | 7,438,336 | 12,779,520 |
| Süre | 12.913778 s | 22.186667 s |
| Sonlu örnek oranı | %100 | %100 |
| Örnekleme hızı | 576 kS/s | 576 kS/s |
| Nominal sembol hızı | 9.6 kBd | 9.6 kBd |
| Örnek/sembol | 60 | 60 |

### 4.2 Tonlar, frekans ofseti ve `h`

| Özellik | Kayıt A | Kayıt B |
|---|---:|---:|
| Etkin alt frekans | -4.388 kHz | -2.120 kHz |
| Etkin üst frekans | +2.643 kHz | +2.336 kHz |
| Ton/faz merkezi | -0.872 ± 0.048 kHz | +0.108 ± 0.026 kHz |
| Etkin ayrım | 7.031 kHz | 4.456 kHz |
| Frekans sapması `Δf` | 3.515 kHz | 2.228 kHz |
| Önerilen `h` | **0.732 ± 0.013** | **0.464 ± 0.003** |
| Saniyelik `h` aralığı | 0.708–0.756 | 0.461–0.471 |

B'nin anlık frekans histogramında yaklaşık `-3.06/+3.25 kHz` dış tepeler görülür; bunların ayrımını 9.6 kBd'ye bölmek yanlış biçimde `h≈0.657` üretir. Bu değer sembol boyunca faz integralini değil, pulse-shaped dalga biçiminin anlık maksimumlarını ölçer ve kullanılmamalıdır.

Kayıtların baseband merkezleri arasında yaklaşık 0.97 kHz fark vardır. Bu fark alıcı ayarı, taşıyıcı frekans ofseti veya örnekleyici osilatör farkından kaynaklanabilir.

### 4.3 IQ ve zarf özellikleri

| Özellik | Kayıt A | Kayıt B |
|---|---:|---:|
| Ortalama zarf | 0.23381 | 0.72536 |
| RMS genlik | 0.23447 | 0.72714 |
| Tepe genlik | 0.31067 | 1.00548 |
| PAPR | 2.44 dB | 2.82 dB |
| Zarf değişim katsayısı | %7.52 | %7.00 |
| DC büyüklüğü | 1.13×10⁻⁵ | 7.10×10⁻⁵ |
| I/Q standart sapma oranı | 0.927 | 0.988 |
| I/Q korelasyonu | 0.00119 | 0.00465 |

Her iki kaydın da zarf değişimi düşüktür ve bu durum sabit zarflı CPM/CPFSK ailesiyle uyumludur. Kayıt B'nin I/Q dengesi A'ya göre daha iyidir. Her iki kayıtta DC bileşeni sinyal RMS değerine göre küçüktür.

### 4.4 İşgal bant genişliği

| Eşit kuyruklu güç oranı | Kayıt A | Kayıt B | B'nin A'ya göre farkı |
|---|---:|---:|---:|
| %90 OBW | 9.503 kHz | 7.628 kHz | %19.7 daha dar |
| %99 OBW | 17.615 kHz | 12.300 kHz | %30.2 daha dar |
| %99.9 OBW | 34.337 kHz | 23.667 kHz | %31.1 daha dar |

B kaydının daha düşük `h` değeri ve muhtemel kısmi-tepkili/darbe-şekillendirilmiş yapısı, daha dar spektrumla tutarlıdır.

## 5. Dalga biçimi sınıflandırması

### 5.1 Kayıt A

Sembole hizalı anlık frekans dağılımında iki dar küme vardır:

```text
-4.397 kHz ve +2.704 kHz
küme ağırlıkları: 0.497 / 0.503
```

İki kümenin dengeli olması, veri bitlerinin yaklaşık dengeli/whitened olmasıyla uyumludur. Bu tek başına scrambler bulunduğunu kanıtlamaz. Sembol saatinin 60 SPS olarak açıkça görünmesi ve iki dar ton kümesi, tam-tepkili ikili CPFSK karar modelini destekler.

### 5.2 Kayıt B

En uygun sembol fazında dört ana küme ölçülmüştür:

```text
-3.003, -1.166, +1.397, +3.237 kHz
küme ağırlıkları: 0.276 / 0.222 / 0.224 / 0.278
```

Bu seviyelerin dış çift ve iç çift olarak simetrik olması, ancak eşit aralıklı olmaması önemlidir. Temiz 4-FSK'de komşu ton aralıklarının yaklaşık eşit olması beklenirdi. Gözlenen yapı, ikili sembollerin birden fazla sembole yayılan frekans darbesi nedeniyle ara seviyeler oluşturduğu kısmi-tepkili CPM/CPFSK yorumunu daha güçlü kılar.

Sonuç olarak B kaydını iki seviyeye zorlayan sıradan `Binary Slicer`, zamanlama algoritması değiştirilse bile bütün sembol belleğini kullanamaz. Önce uygun CPM eşleşmiş filtresi/MLSE, bilinen pulse-shape'e özel demodülatör veya en azından çok-sembollü karar yöntemi gerekir.

## 6. GNU Radio açısından sonuç

Kayıt A için mevcut yaklaşım korunabilir:

```text
File Source (complex64)
→ frekans düzeltme/kanal filtresi
→ Quadrature Demod (gain = Fs/(2πΔf))
→ sembol eşleşmiş/integrate-and-dump filtresi
→ Symbol Sync (60 SPS giriş, 1 SPS çıkış)
→ Binary Slicer
→ NRZ-I decoder
→ gerekiyorsa descrambler
→ Pack K Bits
```

A için ölçülen `Δf≈3515 Hz` kullanılırsa normalize ayrıştırıcı kazancı:

```text
gain = Fs/(2πΔf) ≈ 26.08
```

Bu değer önceki yaklaşık 26 kazancıyla uyumludur. Sabit frekans merkez düzeltmesi, Quadrature Demod çıkışında Hz kullanılıyorsa yaklaşık `+872 Hz`; normalize çıkış kullanılıyorsa `+872/3515 ≈ +0.248` eklenerek yapılır. İşaret, kullanılan blok bağlantısına göre test edilmelidir.

Kayıt B için aynı tek-sembollük hareketli ortalama ve tek eşikli dilimleyici doğrudan kullanılmamalıdır. Faz-integralli ölçüm `Δf≈2228 Hz`, `h≈0.464` ve `Rs≈9601.26 Bd` vermektedir. Bunlar doğru normalizasyon değerleridir; fakat pulse-shape belleği nedeniyle tek başına doğru bit kararı sağlamaz.

## 7. Sonuç ve kabul kararı

1. Her iki dosya geçerli `complex64` IQ kaydıdır ve sayısal bütünlük kontrolünden geçmiştir.
2. Her iki kayıt 576 kS/s örnekleme altında 9.6 kBd ile ilişkili saat çizgileri gösterir.
3. Kayıt A, iki seviyeli ikili CPFSK alıcı zinciri için **uygun ve doğrulanmış** görünmektedir.
4. Kayıt B, A ile aynı basit CPFSK modeline **uygun değildir**; kısmi-tepkili CPM/CPFSK olasılığı yüksektir.
5. Önerilen modülasyon indisleri A için `0.732±0.013`, B için faz-integralli ölçümle `0.464±0.003`'tür.
6. Ham IQ seviyesinde iki kaydın aynı veri paketini taşıdığı söylenemez. Bunun için her kayıt kendi doğru demodülatörüyle çözülmeli, frame sync/preamble bulunmalı ve hizalanmış payload baytları karşılaştırılmalıdır.

## 8. Üretilen kanıt dosyaları

- `iki_iq_karsilastirma.png`: PSD, anlık frekans kümeleri ve saniyelik `h` grafikleri.
- `iq_model_duyarlı_özet.json`: model-duyarlı sayısal özet.
- `iq_h_zaman_serisi.csv`: saniyelik ton merkezi, sapma ve `h` ölçümleri.
- `iki_iq_analiz_sonuclari.json`: genel IQ, zarf, spektrum, zamanlama ve ilk iki-küme analizinin ayrıntıları.
