# Bağımsız C CPFSK Demodülatörü

## 1. Amaç ve kapsam

Bu klasördeki uygulama, üç ham IQ kaydını GNU Radio kullanmadan, doğrudan C ile demodüle eder. Uygulama herhangi bir GNU Radio bloğu veya harici DSP kütüphanesi çağırmaz. Giriş, ardışık `float32 I` ve `float32 Q` değerlerinden oluşan little-endian `complex64` dosyasıdır.

İşlenen kayıtların çalışma kopyaları:

| Profil | Kaynak kayıt | Çalışma alanındaki dosya | Süre |
|---|---|---|---:|
| A | `intern_Rec().bin` | `iq_compare_A.bin` | 12.9138 s |
| B | `intern_Rec1().bin` | `iq_compare_B.bin` | 22.1867 s |
| C | `intern_Rec2().bin` | `iq_compare_C.bin` | 12.2880 s |

Ortak bilinen parametreler:

```text
Örnekleme hızı Fs = 576000 sample/s
Bit/sembol hızı Rs = 9600 symbol/s
Sembol başına örnek = Fs/Rs = 60
Modülasyon = ikili CPFSK/CPM
Hat kodu = NRZ-I
Muhtemel scrambler = G3RUH, x^17 + x^12 + 1
```

## 2. Dosyalar

- `cpfsk_demod.c`: Demodülatörün bütün DSP ve protokol kodu.
- `cpfsk_demod.exe`: Derlenmiş Windows uygulaması.
- `build.ps1`: GCC ile yeniden derleme betiği.
- `run_all.ps1`: Üç kaydı kendi profiliyle işler.
- `outputs/`: Bit, bayt, hex ve JSON sonuçları.
- `DOGRULAMA_RAPORU.md`: Gerçek kayıtlarla alınan sayısal test sonuçları.

## 3. Derleme ve çalıştırma

PowerShell'de çalışma alanı kökünden:

```powershell
powershell -ExecutionPolicy Bypass -File .\c_demod\build.ps1
powershell -ExecutionPolicy Bypass -File .\c_demod\run_all.ps1
```

Tek kayıt çalıştırma örneği:

```powershell
.\c_demod\cpfsk_demod.exe `
  --input .\iq_compare_B.bin `
  --output .\c_demod\outputs\rec_B `
  --profile B
```

Başka bir dosya, ölçülmüş parametreler açıkça verilerek de işlenebilir:

```powershell
.\c_demod\cpfsk_demod.exe `
  --input kayit.bin `
  --output sonuc `
  --profile A `
  --fs 576000 `
  --rs 9600 `
  --center -872.045 `
  --deviation 3515.455 `
  --mode full
```

`--invert`, frekans durumlarının 0/1 anlamı ters ise line bitlerini çevirir. `--timing`, otomatik zamanlama aramasını devre dışı bırakıp sembol sınırının örnek cinsinden fazını zorlar.

## 4. DSP işlem zinciri

```textcomplex64 IQ
   │
   ├─ IQ biçim ve genlik denetimi
   │
   ├─ Faz farkı / .quadrature discriminator
   │       f[n] = Fs/(2π) · atan2(cross, dot)
   │
   ├─ 21 örnek merkezli hareketli ortalama
   │
   ├─ Sembol zamanlaması arama
   │       ├─ A,C: sembol boyunca faz/frekans integrali
   │       └─ B: orta noktadan örnekleme + geçiş destekli timing PLL
   │
   ├─ Merkez frekans düzeltme ve normalize soft karar
   │       z[k] = (f[k] - f_center) / Δf
   │
   ├─ Binary slicer: z[k] > 0
   │
   ├─ NRZ-I çözme: bit=1 ⇔ hatta geçiş yok
   │
   ├─ G3RUH descramble: x^17 + x^12 + 1
   │
   ├─ LSB-first bitleri bayta paketleme
   │
   └─ HDLC 0x7E, bit stuffing ve CRC-16/X.25 denetimi
```

### 4.1 IQ okuma

Her kompleks örnek C tarafında şu yapı ile okunur:

```c
typedef struct { float i, q; } complex32_t;
```

Dosya boyutunun 8'in katı olması kontrol edilir. NaN/Inf örnekleri reddedilir. Ortalama I/Q, ortalama zarf, RMS, tepe ve PAPR ayrıca JSON raporuna yazılır.

### 4.2 Quadrature discriminator

CPFSK bilgisi genlikte değil, ardışık kompleks örnekler arasındaki faz değişimindedir. Uygulama kompleks çarpımı açıkça hesaplar:

```text
dot   = I[n]I[n-1] + Q[n]Q[n-1]
cross = Q[n]I[n-1] - I[n]Q[n-1]
Δφ[n] = atan2(cross, dot)
f[n]  = Δφ[n] Fs/(2π)
```

`f[n]` doğrudan Hz cinsinden anlık frekanstır. Bu işlem GNU Radio'daki Quadrature Demod bloğunun temel matematiğine eşdeğerdir, fakat burada C içinde uygulanır.

### 4.3 Merkez kaymasının giderilmesi

Kayıtlarda taşıyıcı merkez frekansı tam sıfır değildir. Kullanılan merkezler:

| Profil | Frekans merkezi |
|---|---:|
| A | −872.045 Hz |
| B | +108.082 Hz |
| C | −123.636 Hz |

Slicer eşiği sıfır yerine bu merkezdir. Böylece frekans kayması bir biti diğerinden daha olası hale getirmez.

### 4.4 Filtreleme

Discriminator çıkışına 21 örnek uzunluklu merkezli hareketli ortalama uygulanır. Bu, yüksek frekanslı discriminator gürültüsünü azaltan bir alçak geçiren filtredir.

A ve C tam-tepkili yapıya yakın olduğundan sembol kararı, ham discriminator değerlerinin tam bir sembol boyunca integral/ortalamasıyla alınır. Bu 60 örneklik integrate-and-dump işlemi aynı zamanda dikdörtgen sembol için matched-filter benzeri davranır.

B pulse-shaped/partial-response yapıdadır. Bu nedenle 60 örnek boxcar ortalaması B'nin karar seviyelerini gereksiz bastırır ve komşu sembol etkisini karıştırır. B'de 21 örneklik gürültü filtresinden sonra sembol orta noktası örneklenir.

### 4.5 İlk sembol fazının bulunması

Bir sembol 60 örnektir; ancak ilk sembol sınırının dosyanın hangi örneğine denk geldiği bilinmez. Kod bir sembollük bütün olası fazları yarım örnek çözünürlüğünde tarar. Her aday faz için iki kümeli bir karar modeli kurulur.

Kalite ölçütü:

```text
Q = (μ_high − μ_low) / (2 · küme-içi RMS)
```

İki frekans durumunu en iyi ayıran faz başlangıç fazı olarak seçilir.

### 4.6 Rec1 için timing PLL

Rec1'in sabit 60 SPS ile işlenmesi, uzun kayıt boyunca nadir sembol saati kaymalarına yol açıyordu. Bunun belirtisi, bit seviyesinde binlerce HDLC bayrağı bulunmasına rağmen `0x7E` baytlarının farklı bit ofsetlerine dağılmasıydı.

C kodundaki geçiş destekli timing tracker şu şekilde çalışır:

1. Bir sonraki sembol sınırı mevcut SPS ile tahmin edilir.
2. Ardışık iki line sembolü farklıysa, gerçek bir frekans geçişi olması gerektiği bilinir.
3. Tahmini sınırın ±0.38 sembol çevresindeki en yakın merkez-eşik geçişi bulunur.
4. Sınır fazı hatanın `%25`i ile; SPS ise küçük bir frekans döngüsüyle düzeltilir.
5. SPS, nominal değerin ±%0.5'i içinde sınırlandırılır.

Rec1 testinde 106435 gerçek geçiş zamanlama gözlemi kullanıldı. Zamanlama hatasının RMS değeri yalnızca 0.292 örnek oldu ve son SPS 59.9967 olarak bulundu. Bu takip sonucunda bayt hizası kayıt boyunca sabit kaldı.

### 4.7 Soft karar ve hard slicing

Soft değer:

```text
soft = (ölçülen_frekans − merkez_frekans) / etkin_Δf
```

İdeal durumda negatif ve pozitif iki küme oluşur. Hard line sembolü merkez eşiğine göre 0 veya 1 yapılır. `soft_f32` dosyası, sonraki hata analizi veya farklı eşik denemeleri için özellikle saklanır.

### 4.8 NRZ-I çözme

Bu kayıtlarda doğrulanan NRZ-I kuralı:

```text
Önceki line seviyesi ile aynıysa bit 1
Line seviyesi değiştiyse bit 0
```

Kod ters olasılığı da paralel üretir ve `.nrzi_alt_bits` dosyasına yazar. Gerçek kayıtlarda doğru kuralın ardından descramble edildiğinde kesintisiz HDLC bayrakları çıkmış, ters kuralda çıkmamıştır.

### 4.9 G3RUH descrambler

Descrambler polinomu:

```text
x^17 + x^12 + 1
```

Her giriş biti için:

```text
çıktı = giriş XOR giriş[n−12] XOR giriş[n−17]
```

17 bitlik durum kaydı, descrambler girişindeki scrambled bitlerle güncellenir. İlk 17 bit başlangıç durumu bilinmediği için geçicidir; çıktıdaki ilk birkaç anlamsız baytın ana nedeni budur.

### 4.10 Bayt paketleme ve HDLC doğrulaması

HDLC bitleri LSB-first paketlenir. Uygulama sekiz olası bit ofsetini deneyip en fazla `0x7E` veren ofseti seçer. HDLC bayrak deseni:

```text
bit sırası: 0 1 1 1 1 1 1 0
hex:       0x7E
```

Bayraklar arasındaki gerçek çerçeveler için beş adet 1'den sonraki stuffed 0 kaldırılır ve CRC-16/X.25 denenir. Bu üç kayıt yalnızca idle flag içerdiği için bayraklar arasında payload çerçevesi yoktur; dolayısıyla `CRC OK=0` bir demodülasyon hatası değildir.

## 5. Profil parametreleri ve modülasyon indisi

| Profil | Karar modeli | Etkin Δf | h = 2Δf/Rs |
|---|---|---:|---:|
| A | tam sembol integrali | 3515.455 Hz | 0.732386 |
| B | pulse-shaped orta nokta + PLL | 2228.043 Hz | **0.464176** |
| C | tam sembol integrali | 2947.500 Hz | 0.614063 |

Rec1 için kritik ayrım şudur: anlık frekansın dış tepeleri yaklaşık −3.15 ve +3.37 kHz olabilir. Bunları doğrudan iki FSK tonu saymak `h≈0.68` verir; bu B için doğru değildir. B'nin frekans darbesi sembol sınırlarına yayılır. CPM/CPFSK modülasyon indisi, anlık maksimumdan değil bir sembolde biriken faz alanından elde edilir:

```text
h = Δφ_sembol / π = (f_high,etkin − f_low,etkin)/Rs
```

Uzun aynı-sembol koşularının faz alanına yapılan regresyon B için etkin ton ayrımını yaklaşık 4456 Hz vermiştir. Bu nedenle raporlanacak Rec1 değeri `h≈0.464`, makul ölçüm belirsizliğiyle `0.464 ± 0.003`'tür.

## 6. Çıktı dosyaları

Her `PREFIX` için:

| Sonek | İçerik |
|---|---|
| `.soft_f32` | Sembol hızında normalize float32 soft kararlar |
| `.line_bits` | Slicer sonrası, her baytta bir adet 0/1 line sembolü |
| `.nrzi_bits` | NRZ-I çözülmüş bitler |
| `.nrzi_alt_bits` | Ters NRZ-I varsayımıyla kontrol çıktısı |
| `.g3ruh_bits` | NRZ-I + G3RUH descramble sonrası bitler |
| `.g3ruh_alt_bits` | Ters NRZ-I + descramble kontrol çıktısı |
| `.bytes_msb.bin` | Ofset 0, MSB-first paketleme kontrolü |
| `.bytes_lsb_offset0.bin` | Ofset 0, LSB-first paketleme |
| `.bytes_lsb.bin` | Otomatik bit-ofsetli nihai bayt çıktısı |
| `.hex.txt` | Nihai baytların okunabilir hex dump'ı |
| `.frames.txt` | Bulunan payload çerçevesi ve CRC ayrıntıları |
| `.report.json` | Bütün parametre ve kalite ölçümleri |

Bu kayıtlar için kullanıcı açısından temel sonuç dosyaları:

```text
outputs/rec_A.bytes_lsb.bin
outputs/rec_B.bytes_lsb.bin
outputs/rec_C.bytes_lsb.bin
```

## 7. Sonucun yorumu

Üç kayıtta da demodülasyon, NRZ-I çözme ve descramble işlemi çalışmıştır. Kanıt yalnızca iki soft-decision kümesinin görülmesi değildir: zincirin sonunda bağımsız bir protokol yapısı olan HDLC `0x7E` deseni neredeyse bütün kayıt boyunca, doğru 8 bit periyotla elde edilmiştir.

Çıktının çoğunun `0x7E` olması “uygulama veri bulamadı” anlamına gelmez. Kaydedilen RF kesiti HDLC hattının idle/bayrak durumunu taşıyor. Bu üç dosyada bayraklar arasında sunulabilir payload çerçevesi bulunmadığından uygulama gerçek mesaj baytı veya geçerli CRC'li frame üretemez. Payload içeren başka bir kayıt aynı zincire verildiğinde `.frames.txt` dosyasında çerçeve ve CRC sonucu oluşacaktır.

## 8. Sınırlar

- Profil merkez ve deviation değerleri bu üç kayıttan ölçülmüştür; farklı alıcı ayarı veya farklı verici için yeniden ölçülmelidir.
- Girişte kanal seçimi yoktur. IQ dosyası hedef sinyali zaten bant içinde içermelidir.
- AGC uygulanmaz; faz discriminator genlikten büyük ölçüde bağımsızdır, ancak sıfıra yakın genlikte faz gürültüsü artar.
- Uygulama ikili CPFSK ve bu kayıtlarda doğrulanan NRZ-I/G3RUH/HDLC zincirine özeldir.
- CRC'nin doğrulanabilmesi için en az bir gerçek, iki bayraktan oluşan payload frame bulunmalıdır.
