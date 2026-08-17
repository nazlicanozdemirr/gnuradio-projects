import json
import numpy as np

FS=576000.0; RS=9600.0; SPS=60
x=np.memmap('iq_compare_B.bin',dtype=np.complex64,mode='r')
freq=np.angle(x[1:]*np.conj(x[:-1])).astype(float)*FS/(2*np.pi)

def estimate(phase,center,min_len,max_len):
    count=(len(freq)-phase)//SPS
    blocks=freq[phase:phase+count*SPS].reshape(count,SPS)
    frac=np.mean(blocks>center,axis=1)
    bits=frac>.5
    purity=float(np.mean(np.maximum(frac,1-frac)))
    avg=blocks.mean(axis=1)
    edges=np.flatnonzero(bits[1:]!=bits[:-1])+1
    starts=np.r_[0,edges]; ends=np.r_[edges,len(bits)]
    lengths=ends-starts
    areas=np.add.reduceat(avg,starts)
    run_bits=bits[starts]
    slopes=[]
    for bit in (False,True):
        groups=[]
        for L in range(min_len,max_len+1):
            vals=areas[(run_bits==bit)&(lengths==L)]
            if len(vals)>=12: groups.append((L,np.mean(vals),len(vals)))
        xx=np.array([g[0] for g in groups]); yy=np.array([g[1] for g in groups]);
        ww=np.sqrt(np.array([g[2] for g in groups]))
        slopes.append(float(np.polyfit(xx,yy,1,w=ww)[0]))
    return (slopes[1]-slopes[0])/RS,purity,slopes

rows=[]
for center in (50,80,110,140,170):
    for limits in ((2,8),(2,10),(3,10),(2,12)):
        for phase in range(SPS):
            h,purity,slopes=estimate(phase,center,*limits)
            rows.append({'center_threshold_hz':center,'min_run':limits[0],'max_run':limits[1],
                         'phase':phase,'h':h,'purity':purity,
                         'low_slope_hz':slopes[0],'high_slope_hz':slopes[1]})
accepted=[r for r in rows if r['purity']>=.87]
hs=np.array([r['h'] for r in accepted])
summary={'accepted_tests':len(accepted),'mean':float(hs.mean()),'std':float(hs.std()),
         'median':float(np.median(hs)),'p05':float(np.percentile(hs,5)),
         'p95':float(np.percentile(hs,95)),'min':float(hs.min()),'max':float(hs.max())}
out={'summary':summary,'tests':rows}
open('rec1_h_hassasiyet.json','w',encoding='utf-8').write(json.dumps(out,indent=2))
print(json.dumps(summary,indent=2))
