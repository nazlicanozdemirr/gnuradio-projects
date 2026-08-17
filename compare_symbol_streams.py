import json
import numpy as np
from scipy import signal

FS=576000
SPS=60
CFG={
    'A':('iq_compare_A.bin',24,(-4236.2247,2522.0955)),
    'B':('iq_compare_B.bin',36,(-1794.9527,2011.7987)),
    'C':('iq_compare_C.bin',19,(-2963.0096,2702.1212)),
}

streams={}
for name,(path,phase,levels) in CFG.items():
    x=np.memmap(path,dtype=np.complex64,mode='r')
    f=np.angle(x[1:]*np.conj(x[:-1])).astype(float)*FS/(2*np.pi)
    y=signal.lfilter(np.ones(SPS)/SPS,[1.0],f)
    start=FS
    first=start+((phase-start)%SPS)
    bits=(y[first::SPS]>np.mean(levels)).astype(np.uint8)
    nrzi=np.bitwise_xor(bits[1:],bits[:-1])
    streams[name]={'line':bits,'nrzi':nrzi}

def compare(a,b):
    # Compare all lags with at least half of the shorter stream overlapping.
    aa=2*a.astype(np.float64)-1
    bb=2*b.astype(np.float64)-1
    corr=signal.correlate(aa,bb,mode='full',method='fft')
    lags=signal.correlation_lags(len(aa),len(bb),mode='full')
    overlap=np.minimum(len(aa),len(bb)+lags)-np.maximum(0,lags)
    valid=overlap>=min(len(aa),len(bb))//2
    normalized=np.zeros_like(corr)
    normalized[valid]=corr[valid]/overlap[valid]
    i=np.flatnonzero(valid)[np.argmax(np.abs(normalized[valid]))]
    return {'lag_symbols':int(lags[i]),'correlation':float(normalized[i]),
            'absolute_correlation':float(abs(normalized[i])),
            'overlap_symbols':int(overlap[i])}

out={}
for a,b in [('A','B'),('A','C'),('B','C')]:
    out[f'{a}-{b}']={
        'line_symbols':compare(streams[a]['line'],streams[b]['line']),
        'after_nrzi_differential_decode':compare(streams[a]['nrzi'],streams[b]['nrzi']),
    }
print(json.dumps(out,indent=2))
open('uc_iq_sembol_korelasyonu.json','w',encoding='utf-8').write(json.dumps(out,indent=2))
