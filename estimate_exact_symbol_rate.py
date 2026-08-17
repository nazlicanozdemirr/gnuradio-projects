import json
import numpy as np
from scipy import signal

FS=576000.0
CFG={'A':('iq_compare_A.bin',-870.0),'B':('iq_compare_B.bin',110.0),'C':('iq_compare_C.bin',-125.0)}
out={}
for name,(path,center) in CFG.items():
    x=np.memmap(path,dtype=np.complex64,mode='r')
    f=np.angle(x[1:]*np.conj(x[:-1])).astype(float)*FS/(2*np.pi)
    sm=signal.savgol_filter(f,21,2)
    cross=np.flatnonzero((sm[:-1]-center)*(sm[1:]-center)<0)
    # Linear-interpolated crossing times.
    frac=(center-sm[cross])/(sm[cross+1]-sm[cross]+1e-15)
    times=cross+frac
    gaps=np.diff(times)
    multiples=np.rint(gaps/60).astype(int)
    valid=(multiples>=1)&(multiples<=30)&(np.abs(gaps-60*multiples)<12)
    g=gaps[valid]; m=multiples[valid]
    # Robust repeated fit, rejecting timing outliers around the symbol grid.
    sps=float(np.sum(m*g)/np.sum(m*m))
    for _ in range(5):
        residual=g-sps*m
        med=np.median(residual); mad=np.median(np.abs(residual-med))+1e-12
        keep=np.abs(residual-med)<4*1.4826*mad
        sps=float(np.sum(m[keep]*g[keep])/np.sum(m[keep]**2))
        g,m=g[keep],m[keep]
    out[name]={
        'crossings':int(len(times)),'accepted_gaps':int(len(g)),
        'samples_per_symbol':sps,'symbol_rate_hz':FS/sps,
        'rate_offset_from_9600_hz':FS/sps-9600,
        'sample_drift_per_second':(sps-60)*(FS/sps),
        'gap_fit_rms_samples':float(np.sqrt(np.mean((g-sps*m)**2))),
        'gap_fit_median_abs_samples':float(np.median(np.abs(g-sps*m))),
    }
open('uc_iq_hassas_sembol_hizi.json','w',encoding='utf-8').write(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
