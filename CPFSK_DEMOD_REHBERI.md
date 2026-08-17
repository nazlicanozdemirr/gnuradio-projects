# `intern_Rec.bin` için CPFSK demodülasyon rehberi

## 1. Kısa teşhis

Kayıtta iki frekans seviyesi gerçekten mevcut. Sorun sinyalin CPFSK olmaması veya
zamanlama algoritmasının yanlış seçilmesi değil; asıl sorunlar şunlar:

1. Quadrature Demod sonrasındaki `DC Blocker (length=64)` demodüle edilmiş NRZ
   sembol seviyelerini yüksek geçiren filtreden geçiriyor. Aynı bit birkaç sembol
   sürdüğünde seviye sıfıra doğru çöküyor. Bu nedenle iki dar küme yerine geniş
   yatay bölgeler oluşuyor.
2. Bu bozulmuş işaretin arkasındaki float AGC, çöken seviyeleri sürekli farklı
   oranlarda büyütüp yayılımı daha da artırıyor.
3. Ekran görüntüsünden sonra üretilmiş `untitled.py` içinde Symbol Sync `SPS=4`
   yapılmış, ancak önünde 576 kS/s'den 38,4 kS/s'ye indiren bir resampler yok.
   Bu durumda blok 9,6 ksym/s yerine yaklaşık 144 ksym/s bekliyor.
4. Binary Slicer sonrasındaki QT Time Sink hâlâ 576 kS/s olarak ayarlı. Symbol
   Sync çıkışı 1 sample/symbol ise bu sink'in örnek hızı 9,6 kS/s olmalı.
   Grafikteki zaman ekseni şu anda 60 kat hatalı ve bitler gereksiz derecede sık
   görünür.
5. Binary Slicer çıkışı kullanıcı verisi değildir; doğruladığınız üzere işaret
   NRZ-I hat kodludur. `Differential Decoder (Modulus=2)` paketlemeden önce
   eklenmelidir.
6. Float to Complex bloğunun Q girişi boş bırakılmış. Dolayısıyla alttaki grafik
   gerçek bir IQ constellation değildir; bütün noktaların Q değeri tanım gereği
   sıfırdır. Bu sinyal için histogram ve eye diagram daha açıklayıcıdır.

Zamanlama algoritmasını değiştirmek ilk iki maddede oluşan genlik bozulmasını
geri alamaz. Bu nedenle Zero Crossing, M&M veya Gardner arasında geçiş yapmak
görüntüyü esaslı biçimde değiştirmemiştir.

## 2. Dosyadan ölçülen değerler

Bu ölçümler, doğruladığınız `complex64` dosya biçimi, 576 kS/s örnekleme hızı,
9,6 kbit/s NRZ-I hat hızı ve CPFSK modülasyonu kullanılarak doğrudan dosya
üzerinden elde edildi. Binary CPFSK'de her hat sembolü bir bit taşıdığı için
sembol hızı da 9,6 ksym/s'dir.

| Özellik | Ölçülen/hesaplanan değer |
|---|---:|
| Dosya boyutu | 60.293.120 byte |
| Complex örnek sayısı | 7.536.640 |
| Kayıt süresi | 13,08444 s |
| Ortalama complex genlik | 0,239 |
| Genlik standart sapması | 0,00497 |
| Alt ton | yaklaşık 8,60 kHz |
| Üst ton | yaklaşık 15,66 kHz |
| İki tonun merkezi | yaklaşık +12,12 kHz |
| Tonlar arası mesafe | yaklaşık 7,05 kHz |
| Frekans sapması | yaklaşık ±3,525 kHz |
| Sembol hızı | 9,6 ksym/s |
| Örnek/sembol | 576.000 / 9.600 = 60 |
| Tahmini modülasyon indeksi | `h = 2*3525/9600 ≈ 0,734` |
| Beklenen sembol sayısı | yaklaşık 125.611 |
| 8 bit paketlenmiş beklenen boyut | yaklaşık 15.701 byte |

`h≈0,734` ölçüme dayalı bir tahmindir. Bu değer klasik MSK'nin `h=0,5`
değerinden farklı olduğu için başlangıçta MSK/GMSK'ye özel TED seçmek doğru
değildir. Vericinin pulse-shaping bilgisi bulunursa bu sınıflandırma yeniden
kontrol edilmelidir.

Mevcut `decoded_bits.bin` 223.258 byte. Doğru `SPS=60` ile beklenen yaklaşık
15.701 byte'a göre çok büyüktür. İçeriği de ağırlıklı olarak `0x00`, `0xFF`,
`0x0F`, `0xF0` benzeri uzun tekrar desenlerinden oluşuyor. Bu, oluşturulmuş
Python flowgraph'ındaki `SPS=4` ayarının sembol başına yaklaşık 15 kez fazla
çıktı ürettiğini doğruluyor.

## 3. Ekran görüntüsündeki blokların değerlendirmesi

| Blok/ayar | Değerlendirme | Düzeltilmiş yaklaşım |
|---|---|---|
| File Source, complex | Doğru | `complex64`, Repeat kapalı |
| Throttle 576 kS/s | GUI oynatımı için uygun | Örnek hızını değiştirmez; yalnız çalışma hızını sınırlar |
| Quadrature Demod gain 38,2 | Çalışır ama yanlış ölçek | Ölçülen sapmaya göre `26,0066` |
| DC Blocker length 64 | Ana bozulma kaynaklarından biri | Kaldır; sabit merkez düzeltmesi veya complex frequency translation kullan |
| Float AGC | Bu noktada gereksiz ve zararlı | Kaldır; Quadrature Demod kazancıyla ±1'e ölçekle |
| Symbol Sync SPS 60 | 576 kS/s girişte doğru | 4 SPS ancak önce gerçek 15:1 decimation varsa doğrudur |
| Zero Crossing TED | Uygun bir başlangıç | Early-Late da iyi bir ilk seçimdir |
| Loop BW 0,045 | Biraz agresif | Başlangıç için 0,01 |
| Expected TED Gain 1 | Genlik/pulse shape'e bağlı | Bu kayıt için 0,5 iyi sonuç verdi |
| Damping 1 | Uygun | 1,0 bırak |
| Max Deviation 1,5 | Gereğinden serbest | 60 SPS zincirinde başlangıç için 0,2 |
| Output SPS 1 | Doğru | 1 bırak |
| Binary Slicer | Doğru | Girişi sıfır çevresinde ve yaklaşık ±1 olmalı |
| Differential Decoder | Eksik | Binary Slicer arkasına ekle, Modulus=2 |
| QT Time Sink 576 kS/s | Symbol Sync sonrasında yanlış | `symbol_rate = 9600` |
| Float to Complex + Constellation | Yanıltıcı teşhis ekranı | Histogram ve Eye Sink kullan |
| Pack K Bits, K=8 | Kavramsal olarak uygun | Bit sırası ve protokol polaritesini bilinen preamble ile doğrula |

Quadrature Demod için normalize edilmiş kazanç:

```text
gain = Fs / (2*pi*f_dev)
     = 576000 / (2*pi*3525)
     = 26,0066
```

Mevcut `38,2` değeri yaklaşık 2,4 kHz sapma varsayar. Ölçülen sapma 3,525 kHz
olduğu için Symbol Sync öncesindeki seviyeler yaklaşık ±1 yerine ±1,47 olur.
AGC'nin bunu düzeltmesi beklenmiş, fakat doğru çözüm kazancı baştan doğru
hesaplamaktır.

## 4. Önerilen flowgraph — en az değişiklikle güvenilir sürüm

### Değişkenler

```python
samp_rate   = 576e3
symbol_rate = 9.6e3
sps         = samp_rate / symbol_rate       # 60.0
f_mid       = 12.121e3
f_dev       = 3.525e3
qdemod_gain = samp_rate/(2*math.pi*f_dev)   # 26.0066
dc_norm     = -f_mid/f_dev                  # -3.43858
loop_bw     = 0.01
```

### Ana zincir

```text
File Source (complex64, Repeat=No)
  -> Throttle (complex, 576e3; GUI kullanırken)
  -> Quadrature Demod (Gain=qdemod_gain)
  -> Add Const (float, Constant=dc_norm)
  -> FIR Filter (float, Decimation=1, Taps=[1.0/sps]*int(sps))
  -> Symbol Sync (float)
  -> Binary Slicer
  -> Differential Decoder (Modulus=2)
  -> [protokol/framing]
  -> Repack/Pack Bits
  -> File Sink
```

Buradaki `Add Const`, discriminator çıkışındaki +12,12 kHz merkez ofsetini
normalize edilmiş birimde çıkarır. `DC Blocker` gibi veri işaretinin düşük
frekans bileşenlerini yok etmez.

60 katsayılı moving-average FIR, bu kayıttaki yaklaşık dikdörtgen discriminator
sembollerinin eşleşmiş filtresi olarak çalışır. GNU Radio ile tam kayıt üzerinde
denendiğinde Symbol Sync sonrasında ölçülen kümeler:

```text
alt seviye       = -0,9744
üst seviye       = +0,9766
küme hata RMS'i  = 0,0230
|x| < 0,5 oranı  = 0
çıktı sembolü    = 125.609
```

İlk yaklaşık 200 çıkış örneğinde filtre ve döngü başlangıç geçişi vardır. Gerçek
alıcıda bunları körlemesine silmek yerine preamble/access-code korelasyonu ile
paket başlangıcı bulunmalıdır.

### Symbol Sync başlangıç ayarları

```text
Timing Error Detector: Zero Crossing veya Early-Late
Samples per Symbol:    60
Loop Bandwidth:        0.01
Expected TED Gain:     0.5
Damping Factor:        1.0
Maximum Deviation:     0.2
Output Samples/Symbol: 1
Constellation:         BPSK
Interpolator:          MMSE, 8 tap
Number of Filters:     128
```

Bu kayıt üzerinde Early-Late, Zero Crossing, M&M ve Gardner doğru ölçek ve
`SPS=60` ile iki kümeyi de ayırdı. Eşleşmiş filtre kullanıldığında en düşük
yayılımı Zero Crossing verdi; Early-Late da çok yakındı. Dolayısıyla algoritma
seçimi ikinci aşama optimizasyonudur.

## 5. Daha verimli flowgraph — önce 4 SPS'ye indir

60 SPS ile çalışmak mümkündür fakat gereksiz CPU kullanır. `SPS=4` kullanmak
istiyorsanız önce complex sinyali gerçekten 38,4 kS/s'ye indirin:

```text
File Source, Fs=576 kS/s
  -> Frequency Xlating FIR Filter
       Decimation = 15
       Center Frequency = +12.121e3
       Taps = firdes.low_pass(
           1.0, samp_rate, 9e3, 3e3,
           window.WIN_HAMMING, 6.76)
  -> Quadrature Demod
       Gain = 38.4e3/(2*pi*3.525e3) = 1.73377
  -> FIR Filter
       Decimation = 1
       Taps = [1.0/4]*4
  -> Symbol Sync
       SPS = 4
       Loop BW = 0.01
       TED Gain = 0.5
       Damping = 1.0
       Max Deviation = 0.05
       Output SPS = 1
  -> Binary Slicer
  -> Differential Decoder (Modulus=2)
```

Frequency Xlating FIR Filter önce +12,12 kHz'deki kanal merkezini sıfıra taşır,
anti-alias filtrelemesi yapar ve sonra 15'e böler. Bu blok olmadan yalnız Symbol
Sync içindeki `SPS` değerini 60'tan 4'e çevirmek resampling değildir.

Filtre kesim değerleri başlangıç değerleridir. Frequency Sink'te kanalın
kenarlarının kesilmediğini ve 38,4 kS/s çıkışta alias oluşmadığını doğrulayın.

## 6. Doğru teşhis ekranları

Her sink'in örnek hızını bağlı olduğu noktaya göre ayarlayın:

| Ölçüm noktası | Sink örnek hızı | Beklenen görüntü |
|---|---:|---|
| File Source | 576 kS/s | Kanal merkezi yaklaşık +12,12 kHz |
| 15:1 decimator sonrası | 38,4 kS/s | Kanal sıfır merkezli |
| Quadrature Demod sonrası | 576 kS/s veya 38,4 kS/s | İki frekans seviyesi ve geçişler |
| Symbol Sync sonrası | 9,6 kS/s | Yaklaşık −1 ve +1 örnekleri |
| Binary Slicer sonrası | 9,6 kS/s | Yalnız 0 ve 1 |

Önerilen GUI dalları:

1. Quadrature Demod sonrasına QT GUI Time Sink.
2. Eşleşmiş filtre sonrasına Float to Complex ve QT GUI Eye Sink; Eye Sink
   `SPS=60` veya decimation sürümünde `SPS=4`.
3. Symbol Sync sonrasına QT GUI Histogram Sink; x ekseni yaklaşık `[-1.3, 1.3]`,
   100–200 bin.
4. Symbol Sync sonrasındaki QT Time Sink'e `Sample Rate=symbol_rate`.
5. Constellation kullanılacaksa bunun 1 boyutlu bir kontrol olduğunu unutmayın:
   Q=0, beklenen çıktı gerçek eksen üzerinde iki nokta bulutudur.

Binary Slicer sonrasındaki grafiğin 0 ve 1 göstermesi demodülasyon kalitesini
kanıtlamaz; eşik yanlış olsa bile slicer daima 0 veya 1 üretir. Asıl kalite
kontrolü slicer öncesindeki histogram/eye diagram ile yapılmalıdır.

## 7. Ayarları doğru sırayla yapma prosedürü

1. **Dosya tipini doğrula.** File Source'u complex seç. Frekans grafiği anlamlı
   ve zarf yaklaşık sabit olmalı.
2. **Quadrature Demod'u önce Hz modunda ölç.** Geçici olarak gain'i
   `samp_rate/(2*pi)` yap. Histogramdan iki tonun merkezlerini ölç.
3. **Merkez ve sapmayı hesapla.**
   `f_mid=(f_high+f_low)/2`, `f_dev=(f_high-f_low)/2`.
4. **Merkezi kaldır.** Add Const veya Frequency Xlating FIR kullan. İki seviye
   sıfırın iki yanında simetrik olmalı.
5. **±1'e normalize et.** Quadrature Demod gain'ini
   `Fs/(2*pi*f_dev)` yap. Bu noktada AGC kullanma.
6. **Eşleşmiş filtreyi ekle.** Slicer öncesinde eye diagramı incele.
7. **Nominal SPS'yi doğrula.** `SPS=Fs_at_sync/symbol_rate`. Throttle bu değeri
   değiştirmez.
8. **Symbol Sync'i ekle.** Önce Early-Late veya Zero Crossing, `loop_bw=0.01`.
9. **Histogramı kontrol et.** İki dar küme yaklaşık ±1'de ve sıfır çevresi boş
   olmalı.
10. **NRZ-I'ı çöz.** Binary Slicer arkasına `Differential Decoder`,
    `Modulus=2` ekle.
11. **En son framing ekle.** Bit polaritesini, preamble'ı,
    scrambling/whitening'i ve CRC'yi protokole göre doğrula.

Loop ayarı için önce `0.005, 0.01, 0.02` değerlerini; TED gain için
`0.25, 0.5, 1.0` değerlerini tek tek deneyin. Her seferinde yalnız bir parametreyi
değiştirin. Çıkış sembol sayısı, histogram küme genişliği ve bilinen
preamble/CRC başarısını birlikte kaydedin.

## 8. Bit dosyası ve framing uyarıları

- Binary Slicer çıkışı bir byte içinde değeri `0` veya `1` olan **unpacked**
  NRZ-I hat sembolleridir; henüz kullanıcı bitleri değildir.
- Binary NRZ-I için `Differential Decoder (Modulus=2)` işlemi
  `d[n]=(s[n]-s[n-1]) mod 2` yapar. İkili alfabede bu, ardışık iki hat
  sembolünün XOR'udur.
- Eğer protokolde **geçiş=1** tanımı kullanılıyorsa Differential Decoder çıkışı
  doğrudan veri bitidir. **Geçiş=0** tanımı kullanılıyorsa çıkışı tersleyin.
  Hangi tanımın kullanıldığını preamble veya CRC ile belirleyin.
- İlk diferansiyel bit, kayıttan önceki hat durumu bilinmediği için belirsizdir.
  Çerçeve eşzamanlaması bu başlangıç belirsizliğini dışarıda bırakmalıdır.
- Pack K Bits çıkışı ASCII `"0"` ve `"1"` değildir; sekiz biti bir binary byte'a
  paketler.
- Paketleme bit sırasını tahmin etmeyin. Bilinen bir preamble ile sınayın veya
  endianness'i açıkça seçilebilen Repack Bits kullanın.
- Mark/space eşlemesi ters olabilir. Gerekirse slicer öncesinde `Multiply
  Const=-1` veya slicer sonrasında `NOT` uygulayın; doğru polariteyi CRC/sync word
  belirlemelidir.
- İlk doğru kontrol, yaklaşık 13,084 s kayıt için Symbol Sync çıkışının yaklaşık
  125,6 kbit ve paketlenmiş dosyanın yaklaşık 15,7 kbyte olmasıdır.

## 9. Neden DC Blocker 64 özellikle kötü?

Long-form DC Blocker'ın grup gecikmesi `2D-2` örnektir. `D=64` için bu 126
örnek, yani yaklaşık 2,1 semboldür; notch da oldukça geniştir. Demodüle edilmiş
NRZ işaretin uzun sabit bölümleri DC'ye yakın enerji taşır. Blok bu enerjiyi veri
ofseti sanarak siler ve bir bit koşusu boyunca seviyeyi sıfıra çeker.

`D=1024` daha dar notch oluşturduğu için ekran görüntüsündeki 64'e göre daha az
zarar verir, ancak başlangıç gecikmesini yaklaşık 2046 örneğe çıkarır ve hâlâ
protokol verisinin düşük frekans içeriğini filtreler. Bu kayıt için sabit
`f_mid` düzeltmesi açık biçimde daha iyi sonuç verdi. Merkez zamanla kayıyorsa,
uzun zaman sabitli bir frekans-ofset tahminleyicisi kullanıp veri bandına
karışmayacak kadar yavaş izlemek gerekir.

## 10. Resmî GNU Radio kaynakları

- [Quadrature Demod](https://wiki.gnuradio.org/index.php/Quadrature_Demod):
  discriminator matematiği ve normalize gain formülü.
- [Symbol Sync](https://wiki.gnuradio.org/index.php/Symbol_Sync): SPS, TED,
  loop bandwidth, TED gain, damping ve matched-filter gereksinimleri.
- [DC Blocker](https://wiki.gnuradio.org/index.php/DC_Blocker): uzun/kısa form,
  notch genişliği ve grup gecikmesi.
- [Clock Recovery MM](https://wiki.gnuradio.org/index.php/Clock_Recovery_MM):
  simetrik genlik ve sembol-merkezinde tepe oluşturan matched filter ihtiyacı.
- [Frequency Xlating FIR Filter](https://wiki.gnuradio.org/index.php/Frequency_Xlating_FIR_Filter):
  kanal merkezleme ve decimation.
- [QT GUI Eye Sink](https://wiki.gnuradio.org/index.php/QT_GUI_Eye_Sink) ve
  [QT GUI Histogram Sink](https://wiki.gnuradio.org/index.php/QT_GUI_Histogram_Sink):
  uygun görsel teşhis araçları.
- [Throttle](https://wiki.gnuradio.org/index.php/Throttle): bloğun örnekleri
  yeniden örneklemediği, yalnız işleme hızını sınırladığı açıklaması.
- [Repack Bits](https://wiki.gnuradio.org/index.php/Repack_Bits): açık
  endianness ile bit paketleme.
- [Differential Decoder](https://wiki.gnuradio.org/index.php/Differential_Decoder):
  NRZ-I için kullanılan önceki/mevcut sembol ve modulus işlemi.
