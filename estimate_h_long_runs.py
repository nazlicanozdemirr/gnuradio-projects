import json
import numpy as np

FS=576000.0
RS=9600.0
SPS=60
CFG={
    'A':('iq_compare_A.bin',-870.0),
    'B':('iq_compare_B.bin',110.0),
    'C':('iq_compare_C.bin',-125.0),
}

def choose_boundary(freq,center):
    sign=freq>center
    rows=[]
    for phase in range(SPS):
        count=(len(sign)-phase)//SPS
        blocks=sign[phase:phase+count*SPS].reshape(count,SPS)
        frac=blocks.mean(axis=1)
        purity=np.mean(np.maximum(frac,1-frac))
        ambiguous=np.mean((frac>.1)&(frac<.9))
        rows.append((purity,-ambiguous,phase))
    return max(rows)[2],max(rows)[0],-max(rows)[1]

def run_positions(bits):
    edges=np.flatnonzero(bits[1:]!=bits[:-1])+1
    starts=np.r_[0,edges]; ends=np.r_[edges,len(bits)]
    distance_left=np.empty(len(bits),int); distance_right=np.empty(len(bits),int)
    run_length=np.empty(len(bits),int)
    for a,b in zip(starts,ends):
        distance_left[a:b]=np.arange(b-a)
        distance_right[a:b]=np.arange(b-a-1,-1,-1)
        run_length[a:b]=b-a
    return distance_left,distance_right,run_length

out={}
for name,(path,rough_center) in CFG.items():
    x=np.memmap(path,dtype=np.complex64,mode='r')
    freq=np.angle(x[1:]*np.conj(x[:-1])).astype(float)*FS/(2*np.pi)
    phase,purity,ambiguous=choose_boundary(freq[:min(len(freq),int(8*FS))],rough_center)
    count=(len(freq)-phase)//SPS
    blocks=freq[phase:phase+count*SPS].reshape(count,SPS)
    block_avg=blocks.mean(axis=1)  # exact phase increment/T over each symbol
    block_median=np.median(blocks,axis=1)
    bits=np.mean(blocks>rough_center,axis=1)>.5
    dl,dr,rl=run_positions(bits)
    rows=[]
    for margin in range(0,7):
        keep=(dl>=margin)&(dr>=margin)
        low=block_avg[keep&(~bits)]; high=block_avg[keep&bits]
        low_med=block_median[keep&(~bits)]; high_med=block_median[keep&bits]
        if min(len(low),len(high))<10: continue
        # Trim 1% before taking mean to reduce discriminator glitches.
        def trimmed_mean(v):
            a,b=np.percentile(v,[1,99]); q=v[(v>=a)&(v<=b)]; return q.mean()
        lo=trimmed_mean(low); hi=trimmed_mean(high)
        lom=trimmed_mean(low_med); him=trimmed_mean(high_med)
        rows.append({
            'edge_margin_symbols':margin,'selected_low_symbols':int(len(low)),
            'selected_high_symbols':int(len(high)),
            'low_block_average_hz':float(lo),'high_block_average_hz':float(hi),
            'center_hz':float((lo+hi)/2),'deviation_hz':float((hi-lo)/2),
            'h_from_symbol_phase_increment':float((hi-lo)/RS),
            'h_from_block_median':float((him-lom)/RS),
            'median_based_low_hz':float(lom),'median_based_high_hz':float(him),
        })
    out[name]={
        'boundary_phase':int(phase),'mean_block_sign_purity':float(purity),
        'ambiguous_block_fraction':float(ambiguous),
        'symbols':int(count),'max_run_symbols':int(rl.max()),'margins':rows,
    }

open('uc_iq_uzun_kosu_h_dogrulama.json','w',encoding='utf-8').write(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
