# IQ Kayıtlarında Filtre ve Pulse-Shaping Analizi

## 1. İncelenen konu

Bu çalışma iki ayrı soruyu ayırır:

1. Kaydedilmiş sinyalde verici pulse-shaping, kanal filtresi veya başka bir bant sınırlama var mı?
2. GNU Radio alıcı akışındaki FIR blok gerçekten matched filter olarak değerlendirilebilir mi?

Ham IQ kaydından bir verici/kanal filtresinin etkisi gözlenebilir. Ancak bir filtrenin özellikle “matched filter” olarak tasarlandığı yalnız çıkış dalga biçiminden kesin olarak kanıtlanamaz; matched filter, alıcıdaki filtrenin bilinen sembol darbesinin zaman terslenmiş eşleniğiyle eşleşmesi anlamına gelir.

## 2. Yöntem

Complex64 IQ örnekleri anlık frekansa çevrilmiştir:

```text
f[n] = Fs/(2π) · arg{x[n]·conj(x[n-1])}
```

9.6 kBd sembol saati ve 60 örnek/sembol kullanılarak, öncesinde ve sonrasında en az üç aynı sembol bulunan izole ton geçişleri seçilmiştir. Yükselen ve düşen geçişler aynı yöne çevrilmiş, plato seviyeleri normalize edilmiş ve yaklaşık iki bin geçişin medyanı alınmıştır.

Bu yöntem tam-tepkili ikili CPFSK olan Kayıt A için güçlüdür. Kayıt B tek eşikli ikili karar modeline tam uymadığı için B'nin geçiş süresi kör/koşullu bir tahmindir; kesin pulse-shape parametresi olarak değerlendirilmemelidir.

## 3. Ölçüm sonuçları

| Özellik | Kayıt A | Kayıt B |
|---|---:|---:|
| Kullanılan izole geçiş | 1963 | 1228 |
| 10–90% geçiş süresi | 5.46 örnek | 24.61 örnek |
| 10–90% geçiş süresi | 9.49 µs | 42.73 µs |
| Sembol süresine oran | 0.091 T | 0.410 T |
| Tek sembollük integrasyon sonrası iki-küme kalitesi | 15.69 | 3.38 |
| %99 işgal bant genişliği | 17.615 kHz | 12.300 kHz |

`T = 1/9600 = 104.167 µs` sembol süresidir.

## 4. Kayıt A yorumu

Kayıt A'da frekans bir tondan diğerine sembol süresinin yaklaşık %9'u içinde geçmektedir. İki frekans platosu açıkça ayrıdır. Geçişten sonra küçük bir aşım ve sönümlü ringing gözlenmektedir.

Bu gözlemler şunlarla uyumludur:

- Temel modülasyon tam-tepkili, yaklaşık dikdörtgen frekans darbeli binary CPFSK'dir.
- Sinyal tamamen filtresiz değildir. SDR'nin kanal/anti-alias filtresi, verici çıkış filtresi veya örnekleme zinciri geçişi sınırlamakta ve hafif ringing üretmektedir.
- Buna rağmen belirgin, birden fazla sembole yayılan Gaussian benzeri pulse-shaping görülmemektedir.
- Güç spektrumundaki belirgin yan loblar da nispeten keskin ton geçişleriyle tutarlıdır.

Sonuç: A'da genel bant sınırlama vardır; fakat sembol kararını değiştirecek güçlü partial-response pulse-shaping kanıtı yoktur.

## 5. Kayıt B yorumu

Kayıt B'nin frekans geçişi A'dan yaklaşık 4.5 kat daha yavaştır. Anlık frekans dağılımı yalnız iki plato yerine dört ana ara seviye göstermektedir. Ayrıca %99 işgal bant genişliği A'dan yaklaşık %30 daha dardır ve uzak yan loblar daha güçlü bastırılmıştır.

Bu üç bağımsız gözlem birlikte değerlendirildiğinde B'de belirgin pulse-shaping/bant sınırlama bulunduğu sonucuna varılır:

- Geçiş süresi: `0.41 T`
- Çoklu ara frekans seviyeleri
- Daha dar spektrum ve daha düşük yan loblar

En olası yorum, frekans darbesinin komşu sembollere yayıldığı kısmi-tepkili binary CPM/CPFSK'dir. Gaussian, raised-cosine benzeri veya özel bir CPM frekans darbesi olabilir. Yalnız kör IQ analiziyle filtrenin kesin ailesi, tap değerleri veya Gaussian `BT` değeri güvenilir biçimde belirlenemez. Bilinen preamble, verici spesifikasyonu veya referans bit dizisi sağlanırsa pulse-shape ve bellek uzunluğu sistem tanımlama yöntemiyle ölçülebilir.

## 6. Mevcut GNU Radio FIR bloğu matched filter mı?

Akıştaki FIR tap'leri:

```python
[1.0/int(sps)] * int(sps)
```

ve `sps=60` olduğunda bu blok 60 örneklik kutu/boxcar hareketli ortalamadır:

```text
y[n] = (1/60) · Σ x[n-k],  k=0...59
```

### Kayıt A için

Quadrature Demod sonrasında bilgi sembol boyunca yaklaşık sabit bir frekans seviyesi olduğundan, 60 örnek boyunca integrate-and-dump işlemi dikdörtgen sembol darbesi için pratik bir matched filter işlevi görür. Dolayısıyla A için bu bloğa “discriminator sonrası yaklaşık matched/integrate-and-dump filter” denebilir.

Filtrenin özellikleri:

- Tap toplamı birdir; DC/sembol seviyesi ölçeği korunur.
- Gürültü 60 örnek boyunca ortalanır.
- Grup gecikmesi `(60-1)/2 = 29.5 örnek`, yaklaşık 51.2 µs veya 0.492 semboldür.
- `Decimation=1` olduğu için örnekleme hızı değişmez; Symbol Sync hâlâ 60 SPS giriş alır.

### Kayıt B için

Aynı 60-tap boxcar filtre B'nin bilinmeyen, birden fazla sembole yayılan frekans darbesiyle eşleşmez. Çıkışta iki kaba küme oluşturabilir; ancak bu durum filtrenin matched olduğunu veya doğru bitlerin üretildiğini kanıtlamaz. Boxcar filtre semboller arası belleği ortadan kaldırmaz ve bazı örüntülerde farklı ara seviyeleri aynı karar bölgesine zorlar.

Sonuç: Mevcut FIR blok A için mantıklı bir yaklaşık matched filter, B için ise yalnız genel bir alçak geçiren/integratördür.

## 7. Önerilen alıcı yaklaşımı

### Kayıt A

Mevcut zincir korunabilir:

```text
Complex channel filter
→ Quadrature Demod
→ 60-tap moving average / integrate-and-dump
→ Symbol Sync
→ Binary Slicer
→ NRZ-I decoder
→ gerekiyorsa descrambler
```

Quadrature Demod öncesindeki kompleks kanal filtresi, sinyal bant genişliğini bozmayacak şekilde seçilmelidir. Kanal filtresi matched filter değildir; görevi kanal dışı gürültü ve komşu sinyalleri bastırmaktır.

### Kayıt B

Önerilen sıra:

1. Verici pulse-shape/CPM tipi ve nominal `h` spesifikasyondan doğrulanır.
2. Bilinen preamble varsa IQ veya discriminator çıkışı preamble ile hizalanır.
3. Ölçülen frekans darbesine karşılık gelen FIR/CPM receive filter oluşturulur.
4. Sembol belleği bir sembolden uzunsa tek eşikli slicer yerine trellis/MLSE veya ilgili CPM/GMSK demodülatörü kullanılır.
5. Bit doğruluğu preamble korelasyonu, CRC ve mümkünse bilinen payload ile doğrulanır.

Yalnız timing algoritmasını Gardner, Mueller & Müller veya Zero Crossing arasında değiştirmek B'deki pulse-shape/model uyuşmazlığını çözmez.

## 8. Nihai karar

- **Kayıt A:** Hafif genel kanal/bant sınırlama vardır. Belirgin çok-sembollü pulse-shaping yoktur. 60-tap hareketli ortalama, discriminator sonrası yaklaşık matched filter olarak uygundur.
- **Kayıt B:** Belirgin pulse-shaping ve semboller arası bellek vardır. Mevcut 60-tap hareketli ortalama gerçek matched filter değildir. Exact filtre türü ek referans olmadan kesinleştirilemez.

Sayısal sonuçlar `iq_filtre_darbe_analizi.json`, geçiş grafikleri ise `iq_filtre_gecis_karsilastirmasi.png` dosyasındadır.

