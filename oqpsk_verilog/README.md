# OQPSK Verilog örneği

Giriş, `data_valid` ile yüklenen 16 bitlik bir veri buffer'ıdır. Kelime MSB'den
başlanarak sekiz adet I/Q bit çiftine ayrılır. `SPS=4` olduğu için her OQPSK
sembolü dört örnekleme saati sürer; Q kolu I kolundan `SPS/2=2` örnek geridedir.
I ve Q çıkışları 16 bit işaretlidir; girişteki `1`, `+32767` seviyesine ve `0`,
`-32767` seviyesine eşlenir. `busy`, buffer işlenirken `1` olur.

OSS CAD Suite'in CMD terminalinde bu klasöre geçip çalıştırın:

```bat
run_sim.bat
gtkwave oqpsk.vcd
```

PowerShell terminali kullanıyorsanız alternatif olarak:

```powershell
.\run_sim.ps1
gtkwave oqpsk.vcd
```

GTKWave içinde `tb_oqpsk` kapsamından `clk`, `data_in`, `data_valid`, `busy`,
`i_out` ve `q_out` sinyallerini dalga alanına ekleyin. Örnekleme saati 10 ns,
sembol süresi 40 ns ve I/Q kayması 20 ns'dir. Testbench ayrıca I ve Q'nun aynı
örnekleme saatinde birlikte değişmediğini otomatik olarak denetler.

Analog basamak görünümü için `i_out` ve `q_out` izlerini seçip önce
`Data Format -> Signed Decimal`, ardından `Data Format -> Analog -> Step`
seçin.
