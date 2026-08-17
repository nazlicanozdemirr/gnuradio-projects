# 9600 bit/s CPFSK–NRZ-I–G3RUH Alıcı Projesi

## Baştan Sona Teknik ve Öğretici Rehber

**Belge sürümü:** 1.0  
**Tarih:** 31 Temmuz 2026  
**Proje ortamı:** GNU Radio 3.10.12.0 / Windows  
**Girdi:** `intern_Rec.bin`, IQ `complex64`, 576 ksample/s  
**Hat hızı:** 9600 bit/s  

---

## 1. Projenin amacı

Bu projenin amacı, dosyaya kaydedilmiş complex IQ örneklerinden 9600 bit/s
binary CPFSK sinyalini demodüle etmek, sembol saatini kurtarmak, NRZ-I hat
kodunu çözmek, G3RUH scrambling işlemini geri almak ve elde edilen bitleri
hexadecimal olarak incelenebilecek byte'lara paketlemektir.

Projenin sonunda aşağıdaki işlem zinciri oluşturulmuştur:

```text
complex64 IQ
  -> CPFSK frequency discriminator
  -> frekans merkezi düzeltmesi
  -> sembol matched filter
  -> sembol zamanlama kurtarma
  -> hard decision
  -> NRZ-I decoding
  -> G3RUH descrambling
  -> byte hizalama
  -> bitleri byte'a paketleme
  -> binary dosya
```

Nihai testte descramble edilmiş çıkışın tamamı `0x7E` bulunmuştur. `0x7E`,
HDLC flag/idle byte'ıdır. Bu sonuç alıcı zincirinin doğru çalıştığını güçlü
biçimde doğrularken, incelenen IQ kaydının payload yerine sürekli idle flag
taşıdığını göstermiştir.

---

## 2. Temel kavramlar

### 2.1 IQ complex64 nedir?

Her IQ örneği iki adet 32-bit kayan noktalı sayıdan oluşur:

```text
x[n] = I[n] + jQ[n]
```

- `I`: In-phase bileşeni
- `Q`: Quadrature bileşeni
- `complex64`: 32-bit I + 32-bit Q = örnek başına 8 byte

IQ gösterimi sinyalin hem genliğini hem fazını korur. CPFSK bilgisinin temel
taşıyıcısı anlık frekans, frekansın temel kaynağı da örnekten örneğe faz
değişimi olduğu için dosyanın complex okunması zorunludur.

### 2.2 Örnekleme hızı, bit hızı ve SPS

Bu projede:

```text
sample_rate = 576000 sample/s
bit_rate    = 9600 bit/s
```

Binary CPFSK'de her sembol bir hat biti taşıdığı için:

```text
symbol_rate = bit_rate = 9600 symbol/s
```

Bir sembole düşen örnek sayısı:

```text
SPS = sample_rate / symbol_rate
SPS = 576000 / 9600
SPS = 60 sample/symbol
```

Bu değer Symbol Sync bloğunun temel başlangıç parametresidir. `SPS=4` ancak
önceden gerçek bir resampler/decimator ile örnek hızı 38,4 ksample/s'ye
indirilirse kullanılabilir. Throttle bloğu resampling yapmadığı için yalnız
SPS değerini 60'tan 4'e çevirmek yanlıştır.

### 2.3 CPFSK nedir?

CPFSK, “Continuous Phase Frequency Shift Keying” ifadesinin kısaltmasıdır.
Binary CPFSK'de bilgi iki anlık frekans durumuyla taşınır:

```text
alt sembol -> f_mid - f_dev
üst sembol -> f_mid + f_dev
```

Sıradan iki tonlu FSK'den ayırt edici özellik, sembol geçişlerinde fazın
kopmaması ve sürekli ilerlemesidir. Alıcıda complex örneklerin ardışık faz
farkı ölçülerek anlık frekans elde edilebilir.

### 2.4 NRZ-I nedir?

NRZ-I, bilginin mutlak 0/1 seviyesinden çok seviyenin değişip değişmemesiyle
taşındığı bir hat kodudur. Bu nedenle Binary Slicer çıkışı doğrudan kullanıcı
verisi değildir. Ardışık iki hat sembolü karşılaştırılarak asıl veri biti
üretilir.

NRZ-I'ın iki isimlendirme geleneği vardır:

- Geçiş varsa 1, geçiş yoksa 0
- Geçiş varsa 0, geçiş yoksa 1

Doğru gelenek bilinen preamble, HDLC flag veya CRC ile doğrulanmalıdır.

### 2.5 Scrambling neden kullanılır?

Scrambler, uzun 0 veya 1 dizilerini pseudo-random görünümlü bir akışa çevirir.
Amaçları şunlardır:

- Yeterli geçiş yoğunluğu sağlayarak clock recovery'yi kolaylaştırmak
- Spektral çizgileri ve DC içeriğini azaltmak
- Verici spektrumunu daha düzgün dağıtmak

Scrambling şifreleme değildir. Polynomial bilindiğinde işlem deterministik
olarak geri alınır.

Bu kayıtta kullanılan scrambling, yapılan test sonucunda G3RUH olarak
belirlenmiştir:

```text
p(x) = 1 + x^12 + x^17
```

GNU Radio Descrambler karşılığı:

```text
Mask   = 0x21
Seed   = 0x0
Length = 16
```

Bu multiplicative descrambler self-synchronizing'dir; 17 bit geçtikten sonra
başlangıç seed'inin etkisi kaybolur.

### 2.6 HDLC `0x7E` flag nedir?

HDLC çerçevelerinde `0x7E` değeri frame sınırı ve boşta bekleme flag'i olarak
kullanılır:

```text
0x7E = 01111110
```

Verici payload göndermediği sırada arka arkaya `0x7E` gönderebilir. Bu bitler
NRZ-I ve G3RUH işlemlerinden geçirildiğinde havada rastgele görünümlü olur.

---

## 3. Girdi dosyasının doğrulanması

`intern_Rec.bin` dosyası aşağıdaki özelliklere sahiptir:

| Özellik | Değer |
|---|---:|
| Dosya formatı | IQ `complex64` |
| Dosya boyutu | 60.293.120 byte |
| Örnek başına boyut | 8 byte |
| Complex örnek sayısı | 7.536.640 |
| Örnekleme hızı | 576.000 sample/s |
| Kayıt süresi | 13,084444 s |
| Ortalama complex genlik | 0,23905 |
| Genlik standart sapması | 0,00497 |

Örnek sayısı şu şekilde doğrulanmıştır:

```text
60.293.120 byte / 8 byte/sample = 7.536.640 sample
```

Kayıt süresi:

```text
7.536.640 / 576.000 = 13,084444 saniye
```

Genliğin yalnız yaklaşık yüzde 2 değişmesi sabit zarflı bir frekans
modülasyonuyla uyumludur.

---

## 4. İlk flowgraph ve gözlenen problem

İlk zincir özetle şöyleydi:

```text
File Source
  -> Throttle
  -> Quadrature Demod
  -> DC Blocker
  -> AGC
  -> Symbol Sync
  -> Binary Slicer
  -> Pack K Bits
```

Gözlenen belirtiler:

- Symbol Sync çıkışında iki dar küme yerine geniş yatay bölgeler oluşuyordu.
- Timing algoritması değiştirildiğinde sonuç belirgin biçimde düzelmiyordu.
- Binary Slicer çıkışı çok sık geçişli görünüyordu.
- Bir denemede `SPS=4` kullanıldığı için çıktı dosyası beklenenden yaklaşık 15
  kat büyüktü.
- İlk `decoded_bits.bin` dosyası 223.258 byte idi ve `00`, `FF`, `0F`, `F0`
  benzeri uzun tekrar desenleri içeriyordu.

### 4.1 DC Blocker neden sorun oluşturdu?

Quadrature Demod sonrasındaki veri, yaklaşık sabit `-1/+1` NRZ seviyelerinden
oluşur. Uzun aynı-bit koşuları düşük frekans/DC benzeri içerik taşır. DC Blocker
bu içeriği istenmeyen ofset sanarak seviyeyi bir bit koşusu boyunca sıfıra
doğru çökertir.

Özellikle küçük blocker length geniş bir DC notch oluşturduğu için iki seviye
bozulur. Bu durumda timing algoritması doğru olsa bile girişindeki sembol şekli
zaten bozulmuştur.

### 4.2 AGC neden sorunu büyüttü?

Float AGC, DC Blocker tarafından çöken seviyeleri tekrar büyütmeye çalışır.
Fakat çökme miktarı zamana ve bit koşusuna göre değiştiğinden her sembole farklı
kazanç uygulanmış gibi geniş bir dağılım oluşur.

Doğru çözüm AGC ile sonradan düzeltmek değil, Quadrature Demod kazancını
fiziksel frekans sapmasına göre baştan doğru hesaplamaktır.

### 4.3 Zaman ekseni neden hatalı görünüyordu?

Symbol Sync, 60 giriş örneğini bir çıkış sembolüne indirir. Bu nedenle çıkış
hızı 576 ksample/s değil 9,6 ksample/s'dir. Time Sink 576 ksample/s bırakıldığı
için 1024 bit yaklaşık 1,78 ms gösteriliyordu.

Doğrusu:

```text
1024 / 9600 = 106,67 ms
```

### 4.4 Constellation neden gerçek IQ constellation değildi?

Symbol Sync çıkışı float'tır. Float to Complex bloğunda Q girişi boş
bırakıldığından:

```text
x -> x + j0
```

oluşur. Dolayısıyla tüm noktaların Q değeri sıfırdır. Bu grafik yalnız gerçek
eksen üzerindeki iki soft-decision kümesini gösterir; RF sinyalin gerçek IQ
constellation'ı değildir. Bu projede histogram daha doğru bir kalite
göstergesidir.

---

## 5. Sinyal parametrelerinin ölçülmesi

Complex IQ örnekleri için ardışık faz farkı hesaplandı:

```text
delta_phi[n] = angle(x[n] * conjugate(x[n-1]))
f[n] = delta_phi[n] * Fs / (2*pi)
```

Anlık frekans histogramında iki temel seviye bulundu:

| Parametre | Ölçüm |
|---|---:|
| Alt ton | yaklaşık 8,60 kHz |
| Üst ton | yaklaşık 15,66 kHz |
| Ton çiftinin merkezi | yaklaşık +12,121 kHz |
| Ton ayrımı | yaklaşık 7,05 kHz |
| Frekans sapması | yaklaşık ±3,525 kHz |

Hesaplar:

```text
f_mid = (f_high + f_low) / 2
f_dev = (f_high - f_low) / 2
```

Yaklaşık modülasyon indeksi:

```text
h = 2*f_dev/symbol_rate
h = 2*3525/9600
h = 0,734375
```

Bu değer ölçüme dayalı bir tahmindir; pulse-shaping ve ölçüm yöntemi nedeniyle
verici tanımından küçük fark gösterebilir.

---

## 6. Nihai flowgraph

```text
File Source (complex64)
  -> Throttle (576 ksample/s)
  -> Quadrature Demod (gain=26.0066)
  -> Add Const (-3.43858)
  -> FIR Filter (60 tap moving average, decimation=1)
  -> Symbol Sync (Zero Crossing, SPS=60, output SPS=1)
  -> Binary Slicer
  -> Differential Decoder (NRZ-I)
  -> Descrambler (G3RUH, mask=0x21, seed=0, length=16)
  -> Skip Head (31 bit, yalnız bu kayıt için hizalama)
  -> Pack K Bits (8)
  -> File Sink (`decoded_bits_g3ruh.bin`)
```

Teşhis dalları:

```text
Symbol Sync -> Histogram Sink
Symbol Sync -> Float to Complex -> Constellation Sink
Descrambler -> Char to Float -> Time Sink (9600 sample/s)
```

---

## 7. Değişkenler ve hesaplamalar

### `samp_rate = 576000`

IQ dosyasının gerçek örnekleme hızıdır. Throttle, Quadrature Demod ve zaman
hesaplarında kullanılır.

### `symbol_rate = 9600`

Binary CPFSK sembol ve NRZ-I hat hızıdır.

### `sps = samp_rate/symbol_rate = 60`

Symbol Sync girişindeki nominal örnek/sembol oranıdır.

### `f_mid = 12121`

IQ kaydında iki CPFSK tonunun sıfıra göre ortak merkezidir. Sinyalin baseband
merkezi yaklaşık +12,121 kHz kaymıştır.

### `f_dev = 3525`

Her tonun merkezden frekans uzaklığıdır.

### `qdemod_gain`

```text
qdemod_gain = samp_rate/(2*pi*f_dev)
qdemod_gain = 576000/(2*pi*3525)
qdemod_gain = 26,0065949563
```

Bu değer Quadrature Demod çıkışında ±`f_dev` sapmalarını yaklaşık ±1'e
normalize eder.

### `dc_norm`

Quadrature Demod çıkışı `f/f_dev` ölçeğinde olduğu için merkez ofseti:

```text
dc_norm = -f_mid/f_dev
dc_norm = -12121/3525
dc_norm = -3,4385815603
```

Add Const bloğu bu değeri ekleyerek iki sembol seviyesini sıfırın iki yanına
taşır.

---

## 8. Her bloğun görevi ve eklenme nedeni

### 8.1 File Source

- `intern_Rec.bin` dosyasını okur.
- Veri tipi `complex`, vector length 1'dir.
- Repeat kapalıdır; kayıt bir kez işlenir.
- Offset 0'dır; dosyanın başından başlanır.

### 8.2 Throttle

- Donanım saat kaynağı olmayan file-based flowgraph'ın işleme hızını sınırlar.
- GUI'nin kararlı görünmesini sağlar.
- Sinyal örneklerini değiştirmez ve yeniden örnekleme yapmaz.
- Offline, GUI'siz maksimum hız testinde kaldırılabilir.

### 8.3 Quadrature Demod

Bu blok CPFSK demodülasyonunun ana frequency discriminator'ıdır:

```text
y[n] = gain * angle(x[n] * conjugate(x[n-1]))
```

Complex IQ faz değişimini real anlık frekans seviyesine dönüştürür. Bloğun adı
“CPFSK Demod” olmasa da yaptığı işlem binary CPFSK'nin iki frekans durumunu
negatif ve pozitif seviyelere çevirmektir.

Bu alıcı noncoherent discriminator tabanlı bir CPFSK alıcısıdır. Aynı yaklaşım
BFSK, GFSK ve MSK benzeri frekans modülasyonlarını da demodüle edebilir.

### 8.4 Add Const

- Ölçülen sabit +12,121 kHz frekans kaymasını discriminator alanında kaldırır.
- İki sembol seviyesini yaklaşık -1 ve +1 yapar.
- DC Blocker'ın veri içeriğini bozması sorununu önler.
- Frekans ofseti zamanla değişirse sabit değer yeterli olmayabilir; AFC veya
  complex frequency translation gerekebilir.

### 8.5 60 tap FIR Filter

Katsayılar:

```text
[1/60, 1/60, ..., 1/60]
```

- Bir sembol süresi boyunca örnekleri ortalar.
- Gürültü ve sembol içi ripple'ı azaltır.
- Dikdörtgene yakın discriminator sembolleri için integrate-and-dump/matched
  filter gibi çalışır.
- Symbol Sync'in sembol merkezinde daha temiz bir tepe bulmasını sağlar.
- Decimation 1 olduğu için örnek hızını değiştirmez.

Filtrenin nominal grup gecikmesi yaklaşık `(60-1)/2 = 29,5` örnektir.

### 8.6 Symbol Sync

Görevi sembol saatini ve doğru örnekleme fazını bulmaktır. 60 örnek/sembol
girişten her sembol için tek soft-decision örneği üretir.

Nihai parametreler:

| Parametre | Değer | Açıklama |
|---|---:|---|
| TED | Zero Crossing | İki seviyeli, sıfır merkezli işarete uygun |
| SPS | 60 | 576000/9600 |
| Loop bandwidth | 0,01 | Jitter ve takip hızı dengesi |
| Expected TED gain | 0,5 | Ölçek/pulse shape için test edilmiş değer |
| Damping | 1,0 | Kritik sönüm |
| Maximum deviation | 0,2 | 59,8–60,2 SPS aralığı |
| Output SPS | 1 | Her sembol için bir örnek |
| Interpolator | MMSE 8 tap | Fractional sample konumunu üretir |

Zero Crossing, Early-Late, M&M ve Gardner doğru giriş hazırlığıyla test
edildi. Sorunun TED seçiminden değil, TED öncesindeki yanlış DC Blocker/AGC ve
SPS ayarından kaynaklandığı görüldü.

### 8.7 Histogram Sink

Symbol Sync soft-decision çıkışının dağılımını gösterir. Doğru sonuçta:

- İki dar tepe bulunur.
- Tepeler yaklaşık -1 ve +1'dedir.
- Sıfır çevresi boştur.

Tam kayıt testinde ölçülen merkezler:

```text
alt küme = -0,974409
üst küme = +0,976607
küme hata RMS = 0,023007
|x| < 0,5 örnek oranı = 0
```

Bu, Binary Slicer için geniş bir karar marjı olduğunu gösterir.

### 8.8 Float to Complex ve Constellation Sink

Float soft-decision işaretini `x+j0` biçimine dönüştürür. Doğru grafikte iki
küme `(-1,0)` ve `(+1,0)` çevresinde görünür. Bu yalnız 1-boyutlu kontrol
grafiğidir; asıl değerlendirme Histogram Sink ile yapılmıştır.

### 8.9 Binary Slicer

```text
giriş > 0  -> 1
giriş <= 0 -> 0
```

Soft-decision işaretini unpacked hard bitlere dönüştürür. Çıkışın her öğesi bir
byte'tır ama yalnız LSB'deki 0 veya 1 anlamlıdır.

### 8.10 Differential Decoder – NRZ-I

Binary Slicer çıkışındaki NRZ-I hat durumlarını asıl veri bitlerine dönüştürür.
Bu blok scrambling'den önce çözülmüştür; dosya üzerinde yapılan G3RUH testi bu
sıranın doğru olduğunu kanıtlamıştır.

### 8.11 G3RUH Descrambler

Parametreler:

```text
Mask   = 0x21
Seed   = 0x0
Length = 16
```

G3RUH polynomial'i `1+x^12+x^17` için alınan bit kabaca mevcut scrambled bit
ile 12 ve 17 bit önce alınan scrambled bitlerin XOR'udur:

```text
out[n] = in[n] XOR in[n-12] XOR in[n-17]
```

Blok unpacked bit akışında çalışır; bu nedenle Pack K Bits'ten önce bulunmak
zorundadır.

### 8.12 Skip Head – 31 bit

Descrambler self-synchronization ve kaydın rastgele bir bit konumunda başlaması
nedeniyle ilk geçerli HDLC flag bit 31'de başlamıştır. Bu kayıtta hexadecimal
çıktıyı `0x7E` sınırına hizalamak için 31 bit atlanmıştır.

Bu değer yalnız bu kayıt için geçerlidir. Genel alıcıda sabit Skip Head yerine:

- HDLC flag arama
- Bit de-stuffing
- Frame extraction
- FCS/CRC-16 kontrolü

yapan bir HDLC deframer kullanılmalıdır.

### 8.13 Pack K Bits

Sekiz unpacked biti bir binary byte'a paketler. Test sonucunda GNU Radio
bloğunun bu akışta ilk gelen biti byte'ın MSB tarafına yerleştirdiği doğrudan
dosya karşılaştırmasıyla doğrulanmıştır.

### 8.14 File Sink

Descramble edilmiş ve byte hizası düzeltilmiş çıkışı
`decoded_bits_g3ruh.bin` dosyasına yazar. Overwrite seçeneği açıktır.

---

## 9. Çıkışların adım adım incelenmesi

### 9.1 Symbol Sync çıkışı

Toplam:

```text
125.609 soft symbol
```

Teorik sayı:

```text
7.536.640/60 = 125.610,67 symbol
```

Filtre ve senkronizer başlangıç gecikmeleri nedeniyle yaklaşık iki sembollük
fark normaldir.

### 9.2 NRZ-I decoder sonrası scrambled byte'lar

Pack K Bits çıkışının ilk byte'ları:

```hex
1E 05 3D 2D B0 B1 2F B6 90 4E B0 30 A7 EE D1 E6
8A 67 1F BE 88 CB 34 2A 24 4B AA 63 8F F5 C4 5A
```

İstatistikler:

| Test | Sonuç |
|---|---:|
| Byte sayısı | 15.701 |
| Kullanılan farklı byte değeri | 256/256 |
| Shannon entropisi | 7,9873 bit/byte |
| Bitlerde 1 oranı | 0,49905 |
| Printable ASCII oranı | 0,36896 |

Bu değerler akışın whitened/scrambled göründüğünü gösterdi ancak tek başına
scrambling kanıtı olarak kabul edilmedi.

### 9.3 G3RUH hipotezinin testi

`1+x^12+x^17` descrambling uygulandı. Sonuçta:

- İlk geçerli flag başlangıcı bit 31'de bulundu.
- Sonraki flag başlangıçları tam 8 bit aralıkla devam etti.
- 15.697 ardışık `0x7E` byte bulundu.
- Geçerli bölgede `0x7E` dışında byte bulunmadı.

Son dosya:

```hex
7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E
7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E 7E
...
```

Bu kadar uzun ve kesintisiz flag dizisinin yanlış polynomial ile tesadüfen
oluşması pratikte mümkün değildir. Böylece aşağıdaki maddeler birlikte
doğrulanmıştır:

- CPFSK discriminator polaritesi
- 9600 symbol/s ve 60 SPS
- Symbol Sync zamanlaması
- Binary Slicer karar yönü
- NRZ-I çözüm sırası
- G3RUH polynomial'i
- Pack bit sırası ve byte hizası

---

## 10. GNU Radio'da projeyi yeniden oluşturma adımları

1. Options bloğunu QT GUI ve Python output olarak ayarlayın.
2. `samp_rate=576000`, `symbol_rate=9600`, `sps=samp_rate/symbol_rate`
   değişkenlerini oluşturun.
3. `f_mid=12121`, `f_dev=3525` değişkenlerini ekleyin.
4. `qdemod_gain=samp_rate/(2*math.pi*f_dev)` değişkenini ekleyin.
5. `dc_norm=-f_mid/f_dev` değişkenini ekleyin.
6. File Source'u complex seçin ve `intern_Rec.bin` dosyasına bağlayın.
7. GUI kullanıyorsanız complex Throttle ekleyin; rate `samp_rate` olsun.
8. Quadrature Demod ekleyin; gain `qdemod_gain` olsun.
9. Float Add Const ekleyin; constant `dc_norm` olsun.
10. Float-to-float Decimating FIR Filter ekleyin:
    - Decimation: 1
    - Taps: `[1.0/int(sps)]*int(sps)`
11. Float Symbol Sync ekleyin ve Bölüm 8.6'daki parametreleri girin.
12. Symbol Sync çıkışına Histogram Sink bağlayın.
13. Ayrı bir daldan Float to Complex ve Constellation Sink bağlayın.
14. Ana hatta Binary Slicer ekleyin.
15. Differential Decoder ekleyin; Coding `NRZI` olsun.
16. Descrambler ekleyin: mask `0x21`, seed `0x0`, length `16`.
17. Bu kayıt için byte hizalama amacıyla byte Skip Head ekleyin ve 31 item
    atlayın.
18. Pack K Bits ekleyin; K=8 olsun.
19. Byte File Sink ekleyin; çıktı `decoded_bits_g3ruh.bin` olsun.
20. Descrambler çıkışından Char to Float üzerinden Time Sink'e dal alın;
    sink sample rate `symbol_rate` olsun.

---

## 11. Sonucun doğru olduğunu görsel olarak anlama

### Quadrature Demod sonrası

Beklenen: frekans geçişlerini içeren iki ana analog seviye.

### Matched filter sonrası

Beklenen: daha düşük ripple ve daha temiz sembol merkezleri.

### Symbol Sync histogramı

Beklenen: -1 ve +1 çevresinde iki dar tepe, sıfır çevresinde boşluk.

### Constellation kontrolü

Beklenen: Q=0 ekseninde `(-1,0)` ve `(+1,0)` çevresinde iki dar küme.

### Descrambler sonrası Time Sink

Beklenen: tekrarlanan `01111110` HDLC flag deseni.

### Pack K Bits sonrası hex

Beklenen:

```hex
7E 7E 7E 7E ...
```

---

## 12. Sık karşılaşılan hatalar

### İki küme sıfıra doğru yayılıyor

- DC Blocker veri seviyelerini bozuyor olabilir.
- AGC yanlış konumda olabilir.
- Add Const frekans ofseti yanlış olabilir.

### İki küme ±1'de değil

- `f_dev` veya Quadrature Demod gain yanlış olabilir.
- Ölçülen ton frekanslarını yeniden kontrol edin.

### Symbol Sync çok fazla/az sembol üretiyor

- `SPS=Fs/Rs` hesabını kontrol edin.
- Throttle'ın resampler olmadığını unutmayın.
- Symbol Sync girişindeki gerçek sample rate'i izleyin.

### Time Sink zamanı yanlış

- Sink sample rate'i bağlı olduğu noktaya göre ayarlayın.
- Symbol Sync çıkışı bu projede 9600 item/s'dir.

### Hex çıktı rastgele görünüyor

- NRZ-I decoding sırasını kontrol edin.
- Scrambler polynomial'ini doğrulayın.
- Descrambler bit-level olduğu için Pack K Bits'ten önce bulunmalıdır.
- Bit/byte hizasını preamble/flag ile belirleyin.

### Doğru descrambler sonrası da payload yok

- Kayıt yalnız idle flag içeriyor olabilir.
- Payload içeren daha uzun veya doğru zamanda alınmış IQ kaydı gerekir.

---

## 13. Mevcut çözümün sınırlamaları

1. `f_mid=12121` sabittir. Frekans drift'i olan canlı alıcıda AFC veya complex
   frequency tracking gerekir.
2. Kayıt zaten izole bir kanal içerdiği için complex channel filter eklenmedi.
   Geniş bant canlı kayıtta Frequency Xlating FIR Filter kullanılmalıdır.
3. `Skip Head=31` yalnız bu dosyanın başlangıç hizasına özeldir.
4. HDLC bit de-stuffing, frame extraction ve CRC-16 kontrolü henüz flowgraph'a
   eklenmemiştir.
5. Kayıt yalnız HDLC idle flag içerdiği için gerçek payload alanları üzerinde
   protokol doğrulaması yapılamamıştır.
6. BER, farklı SNR ve frekans drift koşullarında ayrıca test edilmelidir.

---

## 14. Önerilen sonraki geliştirmeler

1. Descrambler sonrasına HDLC deframer ekleyin.
2. Flag korelasyonu ile otomatik bit/byte hizalama yapın.
3. Bit de-stuffing uygulayın.
4. AX.25 veya kullanılan protokole uygun CRC/FCS kontrolü ekleyin.
5. Payload içeren yeni IQ kaydı alın.
6. Frekans kaymasını otomatik tahmin eden AFC ekleyin.
7. Geniş bant giriş için Frequency Xlating FIR Filter ve decimation ekleyin.
8. SNR sweep ve kontrollü bit-error testi oluşturun.
9. Frame sayısı, CRC başarı oranı ve tahmini BER için otomatik raporlama ekleyin.

---

## 15. Proje dosyaları

| Dosya | İşlev |
|---|---|
| `intern_Rec.bin` | Orijinal complex64 IQ kaydı |
| `cpfsk_9600_nrzi_g3ruh.grc` | Nihai GNU Radio Companion flowgraph |
| `cpfsk_9600_nrzi_g3ruh.py` | GRC tarafından üretilmiş Python akışı |
| `decoded_bits.bin` | NRZ-I sonrası, descramble öncesi packed veri |
| `decoded_bits_g3ruh.bin` | G3RUH sonrası, hizalanmış packed veri |
| `cpfsk_teshis.png` | Spektrum ve sembol-küme teşhis grafiği |
| `CPFSK_DEMOD_REHBERI.md` | İlk teşhis ve ayar rehberi |

---

## 16. Kaynaklar

- [GNU Radio Quadrature Demod](https://wiki.gnuradio.org/index.php/Quadrature_Demod)
- [GNU Radio Symbol Sync](https://wiki.gnuradio.org/index.php/Symbol_Sync)
- [GNU Radio Differential Decoder](https://wiki.gnuradio.org/index.php/Differential_Decoder)
- [GNU Radio Descrambler](https://wiki.gnuradio.org/index.php/Descrambler)
- [GNU Radio Throttle](https://wiki.gnuradio.org/index.php/Throttle)
- [GNU Radio QT GUI Histogram Sink](https://wiki.gnuradio.org/index.php/QT_GUI_Histogram_Sink)
- [GNU Radio: G3RUH mask 0x21, length 16](https://www.gnuradio.org/news/2016-11-04-reverse-engineering-outernet/)
- [G3RUH 9600 Baud Packet Radio Modem Design](https://www.amsat.org/amsat/articles/g3ruh/109.html)

