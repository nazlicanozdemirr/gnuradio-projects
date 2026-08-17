import json
import numpy as np

FS=576000.0
RS=9600.0
SPS=60
CFG={
    'A':('iq_compare_A.bin',-870.0,26),
    'B':('iq_compare_B.bin',110.0,44),
    'C':('iq_compare_C.bin',-125.0,21),
}

out={}
for name,(path,center,phase) in CFG.items():
    x=np.memmap(path,dtype=np.complex64,mode='r')
    freq=np.angle(x[1:]*np.conj(x[:-1])).astype(float)*FS/(2*np.pi)
    count=(len(freq)-phase)//SPS
    blocks=freq[phase:phase+count*SPS].reshape(count,SPS)
    block_avg=blocks.mean(axis=1)  # phase accumulation / symbol duration
    bits=np.mean(blocks>center,axis=1)>.5
    edges=np.flatnonzero(bits[1:]!=bits[:-1])+1
    starts=np.r_[0,edges]; ends=np.r_[edges,len(bits)]
    records=[]
    for a,b in zip(starts[1:-1],ends[1:-1]):
        records.append((bool(bits[a]),int(b-a),float(block_avg[a:b].sum())))

    sign_results={}
    for bit in (False,True):
        rec=[r for r in records if r[0]==bit]
        grouped=[]
        for length in range(1,13):
            vals=np.array([r[2] for r in rec if r[1]==length])
            if len(vals)>=15:
                grouped.append((length,float(np.mean(vals)),float(np.std(vals)),len(vals)))
        # Fit accumulated average-frequency sum = slope*run_length + edge_intercept.
        fit=[g for g in grouped if 2<=g[0]<=10]
        xx=np.array([g[0] for g in fit],float); yy=np.array([g[1] for g in fit])
        ww=np.sqrt(np.array([g[3] for g in fit],float))
        slope,intercept=np.polyfit(xx,yy,1,w=ww)
        predicted=slope*xx+intercept
        rmse=float(np.sqrt(np.average((yy-predicted)**2,weights=ww**2)))
        sign_results['high' if bit else 'low']={
            'steady_frequency_slope_hz':float(slope),'edge_intercept_hz_symbols':float(intercept),
            'weighted_group_fit_rmse':rmse,
            'grouped_run_area':[
                {'run_symbols':g[0],'mean_integrated_frequency_hz_symbols':g[1],
                 'std':g[2],'runs':g[3],'mean_frequency_over_run_hz':g[1]/g[0]}
                for g in grouped],
        }
    low=sign_results['low']['steady_frequency_slope_hz']
    high=sign_results['high']['steady_frequency_slope_hz']
    out[name]={
        'boundary_phase':phase,'low_steady_hz':low,'high_steady_hz':high,
        'center_hz':(low+high)/2,'deviation_hz':(high-low)/2,
        'h_from_run_area_slope':(high-low)/RS,
        'signs':sign_results,
    }

open('uc_iq_kosu_regresyon_h.json','w',encoding='utf-8').write(json.dumps(out,indent=2))
print(json.dumps({k:{q:v[q] for q in ('low_steady_hz','high_steady_hz','center_hz','deviation_hz','h_from_run_area_slope')} for k,v in out.items()},indent=2))
