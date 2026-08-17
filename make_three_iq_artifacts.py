import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

FS=576000.0
RS=9600.0
SPS=60
CFG={
    'A': {'path':'iq_compare_A.bin','source':'intern_Rec().bin','tones':(-4400,2700),
          'phase':57,'centers':[-4397.414,2703.740],
          'class':'İki seviyeli tam-tepkili binary CPFSK'},
    'B': {'path':'iq_compare_B.bin','source':'intern_Rec1().bin','tones':(-3050,3250),
          'phase':20,'centers':[-3002.884,-1166.462,1396.573,3236.568],
          'class':'Kısmi-tepkili/pulse-shaped binary CPM/CPFSK adayı'},
    'C': {'path':'iq_compare_C.bin','source':'intern_Rec2().bin','tones':(-3080,2830),
          'phase':51,'centers':[-3125.270,2862.583],
          'class':'İki seviyeli tam-tepkili binary CPFSK'},
}
COLORS={'A':'#1769e0','B':'#e05a17','C':'#178f55'}
HASHES={
    'A':'C6F270A430A55549979AC9103053F40F7851A1CF52D33F7FB54ECC7314FB47F3',
    'B':'50CFFAEB4F00CF6C9F536BDDD1731D5BA1F4AEBA7F40F71F9D0D628AD7A3ED60',
    'C':'42E417C72A116719AAC95B11610FEAE5B63AD835834B56B6FAD60F5F48C2246F',
}

ab=json.loads(Path('iki_iq_analiz_sonuclari.json').read_text(encoding='utf-8'))
general={r['label']:r for r in ab['recordings']}
general['C']=json.loads(Path('iq_C_probe.json').read_text(encoding='utf-8'))['general']
pulse=json.loads(Path('iq_filtre_darbe_analizi.json').read_text(encoding='utf-8'))
exact_rates=json.loads(Path('uc_iq_hassas_sembol_hizi.json').read_text(encoding='utf-8'))
rec1_corrected=json.loads(Path('rec1_h_saniyelik_duzeltilmis.json').read_text(encoding='utf-8'))

def histogram_modes(values, expected):
    hist,edges=np.histogram(values,bins=4000,range=(-10000,10000))
    kernel=signal.windows.gaussian(13,std=2); kernel/=kernel.sum()
    smooth=np.convolve(hist.astype(float),kernel,mode='same')
    centers=(edges[:-1]+edges[1:])/2
    modes=[]
    for target in expected:
        mask=np.abs(centers-target)<700
        idx=np.flatnonzero(mask)[np.argmax(smooth[mask])]
        modes.append(float(centers[idx]))
    return modes

series=[]
hist_data={}
summary={}
for name,cfg in CFG.items():
    x=np.memmap(cfg['path'],dtype=np.complex64,mode='r')
    f=np.angle(x[1:]*np.conj(x[:-1])).astype(float)*FS/(2*np.pi)
    if name == 'B':
        for rr in rec1_corrected['rows']:
            series.append({'recording':name,'second':rr['second'],
                           'tone_low_hz':rr['low_hz'],'tone_high_hz':rr['high_hz'],
                           'center_hz':rr['center_hz'],'deviation_hz':rr['deviation_hz'],
                           'h':rr['h']})
    else:
        for sec in range(1,int(x.size/FS)):
            lo,hi=histogram_modes(f[sec*int(FS):min(f.size,(sec+1)*int(FS))],cfg['tones'])
            series.append({'recording':name,'second':sec,'tone_low_hz':lo,'tone_high_hz':hi,
                           'center_hz':(lo+hi)/2,'deviation_hz':(hi-lo)/2,
                           'h':(hi-lo)/RS})
    start,stop=int(FS),min(f.size,int(8*FS))
    first=start+((cfg['phase']-start)%SPS)
    z=f[first:stop:SPS]
    qlo,qhi=np.percentile(z,[0.1,99.9]); hist_data[name]=(z,qlo,qhi)

    rows=[r for r in series if r['recording']==name]
    hs=np.array([r['h'] for r in rows]); cs=np.array([r['center_hz'] for r in rows])
    lo=np.array([r['tone_low_hz'] for r in rows]); hi=np.array([r['tone_high_hz'] for r in rows])
    g=general[name]
    summary[name]={
        'source_file':cfg['source'],'sha256':HASHES[name],
        'classification':cfg['class'],'file_bytes':g['file_bytes'],
        'complex_samples':g['complex_samples'],'duration_seconds':g['duration_seconds'],
        'sample_rate_hz':FS,
        'symbol_rate_baud':exact_rates[name]['symbol_rate_hz'],
        'samples_per_symbol':exact_rates[name]['samples_per_symbol'],
        'tone_low_mean_hz':float(lo.mean()),'tone_high_mean_hz':float(hi.mean()),
        'center_mean_hz':float(cs.mean()),'center_std_hz':float(cs.std()),
        'deviation_mean_hz':float((hi-lo).mean()/2),
        'modulation_index_h_mean':float(hs.mean()),'modulation_index_h_std':float(hs.std()),
        'modulation_index_h_min':float(hs.min()),'modulation_index_h_max':float(hs.max()),
        'rms_amplitude':g['envelope']['rms'],'mean_envelope':g['envelope']['mean'],
        'envelope_cv':g['envelope']['coefficient_of_variation'],
        'papr_db':g['envelope']['papr_db'],'dc_magnitude':g['iq']['dc_magnitude'],
        'iq_std_ratio':g['iq']['std_i_over_std_q'],'iq_correlation':g['iq']['correlation_iq'],
        'occupied_bw_90_hz':g['spectrum']['occupied_bw_90']['width_hz'],
        'occupied_bw_99_hz':g['spectrum']['occupied_bw_99']['width_hz'],
        'occupied_bw_99_9_hz':g['spectrum']['occupied_bw_99_9']['width_hz'],
        'timing_score_60_sps':g['timing_periodicity']['score_at_60_sps'],
        'timing_rank_60_sps':g['timing_periodicity']['rank_of_60_among_20_to_100'],
        'hard_one_fraction_diagnostic':g['hard_symbol_statistics_before_line_decode']['one_fraction'],
        'hard_transition_fraction_diagnostic':g['hard_symbol_statistics_before_line_decode']['transition_fraction'],
        'transition_10_90_samples':pulse[name]['rise_10_90_samples'],
        'transition_10_90_microseconds':pulse[name]['rise_10_90_microseconds'],
        'transition_10_90_symbols':pulse[name]['rise_10_90_symbols'],
        'integrate_two_cluster_quality':pulse[name]['integrate_two_cluster_quality'],
    }
    if name == 'B':
        summary[name]['instantaneous_outer_histogram_peaks_hz']=[-3058.0,3247.0]
        summary[name]['warning']='h uses phase accumulated over one recovered symbol; instantaneous outer peaks must not be used as CPFSK tones'

Path('uc_iq_karsilastirma_ozeti.json').write_text(
    json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
with open('uc_iq_h_zaman_serisi.csv','w',newline='',encoding='utf-8-sig') as fh:
    writer=csv.DictWriter(fh,fieldnames=list(series[0].keys()))
    writer.writeheader(); writer.writerows(series)

plt.style.use('seaborn-v0_8-whitegrid')
fig=plt.figure(figsize=(19,10.5),constrained_layout=True)
gs=fig.add_gridspec(2,3)
ax_psd=fig.add_subplot(gs[0,0]); ax_h=fig.add_subplot(gs[0,1]); ax_bw=fig.add_subplot(gs[0,2])
hist_axes=[fig.add_subplot(gs[1,i]) for i in range(3)]

for name in CFG:
    data=np.load(f'iq_compare_{name}_plot.npz')
    mask=np.abs(data['freqs'])<=20000
    p=data['psd_db'][mask]; p=p-p.max()
    ax_psd.plot(data['freqs'][mask]/1000,p,lw=1,color=COLORS[name],label=f'Kayıt {name}')
ax_psd.set(title='Normalize güç spektrumu',xlabel='Baseband frekansı (kHz)',ylabel='Göreli PSD (dB)',ylim=(-70,3))
ax_psd.legend()

for name in CFG:
    rows=[r for r in series if r['recording']==name]
    ax_h.plot([r['second'] for r in rows],[r['h'] for r in rows],marker='o',ms=3,lw=1.2,
              color=COLORS[name],label=f'Kayıt {name}')
ax_h.set(title='Saniyelik modülasyon indisi',xlabel='Kayıt zamanı (s)',ylabel='h',ylim=(0.4,0.8))
ax_h.legend()

labels=['%90','%99','%99.9']; xpos=np.arange(3); width=.23
for i,name in enumerate(CFG):
    values=[summary[name]['occupied_bw_90_hz']/1000,summary[name]['occupied_bw_99_hz']/1000,
            summary[name]['occupied_bw_99_9_hz']/1000]
    ax_bw.bar(xpos+(i-1)*width,values,width,color=COLORS[name],label=f'Kayıt {name}')
ax_bw.set(title='İşgal bant genişliği',xlabel='Kapsanan güç',ylabel='Bant genişliği (kHz)',xticks=xpos,xticklabels=labels)
ax_bw.legend()

for ax,name in zip(hist_axes,CFG):
    z,qlo,qhi=hist_data[name]
    ax.hist(z,bins=220,range=(qlo,qhi),density=True,color=COLORS[name],alpha=.82)
    for center in CFG[name]['centers']:
        ax.axvline(center,color='black',ls='--',lw=.8)
    ax.set(title=f'Kayıt {name}: sembol-fazlı anlık frekans',xlabel='Anlık frekans (Hz)',ylabel='Olasılık yoğunluğu')

fig.suptitle('Üç complex64 IQ kaydının CPFSK/CPM karşılaştırması — Fs=576 kS/s, Rs=9.6 kBd',fontsize=16)
fig.savefig('uc_iq_karsilastirma.png',dpi=170)

for name in CFG:
    print(name,json.dumps(summary[name],ensure_ascii=False))
