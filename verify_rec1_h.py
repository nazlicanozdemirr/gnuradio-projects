import json
import numpy as np
from scipy import signal, ndimage

FS=576000.0
PATH='iq_compare_B.bin'
x=np.memmap(PATH,dtype=np.complex64,mode='r')
n=min(x.size,int(12*FS))
dphi=np.angle(x[1:n]*np.conj(x[:n-1])).astype(float)
freq=dphi*FS/(2*np.pi)
center=110.0

def transition_stats(step):
    rows=[]
    for phase in range(step):
        z=freq[int(FS)+phase:int(10*FS):step]
        bits=z>center
        tr=np.mean(bits[1:]!=bits[:-1])
        ac=np.corrcoef((2*bits[:-1]-1).astype(float),(2*bits[1:]-1).astype(float))[0,1]
        rows.append((tr,ac,phase))
    return {
        'step_samples':step,'equivalent_rate_hz':FS/step,
        'transition_min':float(min(r[0] for r in rows)),
        'transition_mean':float(np.mean([r[0] for r in rows])),
        'transition_max':float(max(r[0] for r in rows)),
        'autocorrelation_mean':float(np.mean([r[1] for r in rows])),
        'best_phase_by_transition_near_half':int(min(rows,key=lambda r:abs(r[0]-.5))[2]),
    }

sampling_tests=[transition_stats(s) for s in (15,30,60,120)]

# Integrated phase/frequency over candidate symbol durations. This is exactly
# the unwrapped phase increment divided by the window duration.
def window_average(values,L):
    cs=np.r_[0.0,np.cumsum(values,dtype=np.float64)]
    return (cs[L:]-cs[:-L])/L

def kmeans(values,k,iterations=40):
    values=np.asarray(values,float)
    lo,hi=np.percentile(values,[0.1,99.9]); values=values[(values>lo)&(values<hi)]
    c=np.percentile(values,np.linspace(3,97,k))
    for _ in range(iterations):
        lab=np.searchsorted((c[:-1]+c[1:])/2,values)
        new=np.array([values[lab==i].mean() if np.any(lab==i) else c[i] for i in range(k)])
        if np.max(np.abs(new-c))<1e-7: break
        c=new
    lab=np.searchsorted((c[:-1]+c[1:])/2,values)
    weights=np.array([(lab==i).mean() for i in range(k)])
    rms=np.sqrt(sum(np.sum((values[lab==i]-c[i])**2) for i in range(k))/values.size)
    return c,weights,rms

increment_models=[]
for sps in (30,60):
    avg=window_average(freq,sps)
    start,stop=int(FS),min(avg.size,int(10*FS))
    for k in range(2,9):
        best=None
        for phase in range(sps):
            first=start+((phase-start)%sps)
            z=avg[first:stop:sps]
            c,w,r=kmeans(z,k)
            q=np.min(np.diff(c))/(2*r+1e-15)
            # Prefer well-separated and non-empty clusters.
            candidate=(q,float(np.min(w)),phase,c,w,r)
            if best is None or candidate[:2]>best[:2]: best=candidate
        q,minw,phase,c,w,r=best
        increment_models.append({
            'candidate_symbol_rate':FS/sps,'sps':sps,'clusters':k,'phase':phase,
            'quality':float(q),'centers_hz':c.tolist(),'weights':w.tolist(),
            'rms_hz':float(r),
            'outer_h_if_binary':float((c[-1]-c[0])/(FS/sps)),
        })

# Stable-frequency samples: a true steady tone has low local slope and low
# local variance. Estimate the two outer plateau modes without transition data.
smooth=signal.savgol_filter(freq,11,2)
derivative=np.abs(np.gradient(smooth))
local_mean=ndimage.uniform_filter1d(freq,size=31)
local_var=ndimage.uniform_filter1d((freq-local_mean)**2,size=31)
stable=(derivative<np.percentile(derivative,35)) & (local_var<np.percentile(local_var,35))
stable_freq=freq[stable]
hist,edges=np.histogram(stable_freq,bins=6000,range=(-10000,10000))
hist=ndimage.gaussian_filter1d(hist.astype(float),2)
hc=(edges[:-1]+edges[1:])/2
peaks,_=signal.find_peaks(hist,distance=250,prominence=max(10,hist.max()*.02))
peaks=peaks[np.argsort(hist[peaks])[-12:]][::-1]
stable_peaks=[(float(hc[i]),float(hist[i])) for i in peaks]

# Direct all-sample histogram modes and their per-second repeatability.
per_second=[]
for sec in range(1,int(n/FS)):
    z=freq[sec*int(FS):min(freq.size,(sec+1)*int(FS))]
    hst,ed=np.histogram(z,bins=8000,range=(-10000,10000))
    hst=ndimage.gaussian_filter1d(hst.astype(float),2)
    ctr=(ed[:-1]+ed[1:])/2
    vals=[]
    for target in (-3050,3250):
        m=np.abs(ctr-target)<650
        idx=np.flatnonzero(m)[np.argmax(hst[m])]
        vals.append(float(ctr[idx]))
    per_second.append({'second':sec,'low_hz':vals[0],'high_hz':vals[1],
                       'center_hz':sum(vals)/2,'separation_hz':vals[1]-vals[0],
                       'h_at_9600':(vals[1]-vals[0])/9600,
                       'h_at_19200':(vals[1]-vals[0])/19200})

# Phase-slope on long outer-plateau regions. Run lengths above/below conservative
# thresholds show whether those outer levels are genuine sustained states.
state=np.zeros(freq.size,dtype=np.int8)
state[freq>2500]=1; state[freq<-2300]=-1
for sign in (-1,1):
    mask=state==sign
    edges_run=np.flatnonzero(np.diff(mask.astype(np.int8))!=0)+1
    starts=np.r_[0,edges_run]; ends=np.r_[edges_run,mask.size]
    lengths=ends-starts
    selected=(mask[starts]) & (lengths>=20)
    vals=[]; lens=[]
    for a,b in zip(starts[selected],ends[selected]):
        # Exclude five samples at either edge.
        if b-a>12:
            vals.append(float(np.median(freq[a+5:b-5])))
            lens.append(int(b-a))
    arr=np.asarray(vals)
    print('sign',sign,'runs',len(vals),'median frequency',np.median(arr),'run p95/max',np.percentile(lens,95),max(lens))

out={
    'sampling_transition_tests':sampling_tests,
    'phase_increment_cluster_models':increment_models,
    'stable_frequency_histogram_peaks':stable_peaks,
    'per_second_outer_modes':per_second,
}
open('rec1_h_derin_dogrulama.json','w',encoding='utf-8').write(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
