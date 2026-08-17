import json
import numpy as np
from scipy import signal

FS=576000.0
CFG={
 'A':('iq_compare_A.bin',-870.0,60.000080707345866),
 'B':('iq_compare_B.bin',110.0,59.99213174597188),
 'C':('iq_compare_C.bin',-125.0,59.99950689590051),
}

def regress(block_avg,bits,min_len=2,max_len=10):
    edges=np.flatnonzero(bits[1:]!=bits[:-1])+1
    starts=np.r_[0,edges]; ends=np.r_[edges,len(bits)]
    lengths=ends-starts; areas=np.add.reduceat(block_avg,starts); rb=bits[starts]
    slopes=[]; rmses=[]
    for bit in (False,True):
        groups=[]
        for L in range(min_len,max_len+1):
            vals=areas[(rb==bit)&(lengths==L)]
            if len(vals)>=15: groups.append((L,np.mean(vals),len(vals)))
        xx=np.array([g[0] for g in groups]); yy=np.array([g[1] for g in groups]);
        ww=np.sqrt(np.array([g[2] for g in groups]))
        slope,intercept=np.polyfit(xx,yy,1,w=ww)
        rms=np.sqrt(np.average((yy-(slope*xx+intercept))**2,weights=ww**2))
        slopes.append(float(slope)); rmses.append(float(rms))
    return slopes,(slopes[1]-slopes[0])/(FS/sps),sum(rmses)

out={}
for name,(path,center,sps) in CFG.items():
    x=np.memmap(path,dtype=np.complex64,mode='r')
    freq=np.angle(x[1:]*np.conj(x[:-1])).astype(float)*FS/(2*np.pi)
    sm=signal.savgol_filter(freq,21,2)
    cross=np.flatnonzero((sm[:-1]-center)*(sm[1:]-center)<0)
    frac=(center-sm[cross])/(sm[cross+1]-sm[cross]+1e-15)
    times=cross+frac
    # Circular mode of transition positions modulo the recovered symbol period.
    residues=np.mod(times,sps)
    hist,edges=np.histogram(residues,bins=240,range=(0,sps))
    hist=np.convolve(hist,np.ones(7)/7,mode='same')
    epoch0=(edges[np.argmax(hist)]+edges[np.argmax(hist)+1])/2

    cumulative=np.r_[0.0,np.cumsum(freq,dtype=np.float64)]
    sample_axis=np.arange(cumulative.size,dtype=float)
    tests=[]
    for delta in np.linspace(-sps/2,sps/2,61,endpoint=False):
        epoch=epoch0+delta
        first=epoch+np.ceil((0-epoch)/sps)*sps
        boundaries=np.arange(first,len(freq)-sps,sps)
        integ=np.interp(boundaries+sps,sample_axis,cumulative)-np.interp(boundaries,sample_axis,cumulative)
        block_avg=integ/sps
        mid=boundaries+sps/2
        bits=np.interp(mid,np.arange(sm.size),sm)>center
        slopes,h,fit_error=regress(block_avg,bits)
        # Correct timing gives the cleanest run-area linear relation.
        tests.append({'epoch':float(epoch),'delta':float(delta),'low_hz':slopes[0],
                      'high_hz':slopes[1],'h':float(h),'fit_error':float(fit_error)})
    best=min(tests,key=lambda r:r['fit_error'])
    hs=np.array([r['h'] for r in tests])
    out[name]={
        'sps':sps,'symbol_rate_hz':FS/sps,'transition_epoch_mode':float(epoch0),
        'best':best,'all_epoch_h_median':float(np.median(hs)),
        'all_epoch_h_std':float(np.std(hs)),'all_epoch_h_min':float(hs.min()),
        'all_epoch_h_max':float(hs.max()),'epoch_tests':tests,
    }

open('uc_iq_fractional_clock_h.json','w',encoding='utf-8').write(json.dumps(out,indent=2))
print(json.dumps({k:{q:v[q] for q in ('sps','symbol_rate_hz','transition_epoch_mode','best','all_epoch_h_median','all_epoch_h_std','all_epoch_h_min','all_epoch_h_max')} for k,v in out.items()},indent=2))
