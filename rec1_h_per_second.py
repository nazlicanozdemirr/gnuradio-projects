import csv,json
import numpy as np
from scipy import signal

FS=576000.0; SPS=59.99213174597188; RS=FS/SPS
EPOCH=22.216348515081048; CENTER=110.0
x=np.memmap('iq_compare_B.bin',dtype=np.complex64,mode='r')
f=np.angle(x[1:]*np.conj(x[:-1])).astype(float)*FS/(2*np.pi)
sm=signal.savgol_filter(f,21,2)
cum=np.r_[0.0,np.cumsum(f,dtype=np.float64)]; axis=np.arange(cum.size,dtype=float)
first=EPOCH+np.ceil((0-EPOCH)/SPS)*SPS
bound=np.arange(first,len(f)-SPS,SPS)
avg=(np.interp(bound+SPS,axis,cum)-np.interp(bound,axis,cum))/SPS
mid=bound+SPS/2
bits=np.interp(mid,np.arange(sm.size),sm)>CENTER

def estimate(v,b):
    edges=np.flatnonzero(b[1:]!=b[:-1])+1
    starts=np.r_[0,edges]; ends=np.r_[edges,len(b)]
    lengths=ends-starts; areas=np.add.reduceat(v,starts); rb=b[starts]
    slopes=[]
    for bit in (False,True):
        groups=[]
        for L in range(2,9):
            vals=areas[(rb==bit)&(lengths==L)]
            if len(vals)>=5: groups.append((L,np.mean(vals),len(vals)))
        xx=np.array([g[0] for g in groups]); yy=np.array([g[1] for g in groups]);
        ww=np.sqrt(np.array([g[2] for g in groups]))
        slopes.append(float(np.polyfit(xx,yy,1,w=ww)[0]))
    return {'low_hz':slopes[0],'high_hz':slopes[1],'center_hz':sum(slopes)/2,
            'deviation_hz':(slopes[1]-slopes[0])/2,'h':(slopes[1]-slopes[0])/RS}

rows=[]
for sec in range(1,int(x.size/FS)):
    keep=(mid>=sec*FS)&(mid<(sec+1)*FS)
    row={'second':sec}; row.update(estimate(avg[keep],bits[keep])); rows.append(row)
hs=np.array([r['h'] for r in rows])
out={'exact_symbol_rate_hz':RS,'exact_sps':SPS,'mean':float(hs.mean()),'std':float(hs.std()),
     'median':float(np.median(hs)),'min':float(hs.min()),'max':float(hs.max()),'rows':rows}
open('rec1_h_saniyelik_duzeltilmis.json','w',encoding='utf-8').write(json.dumps(out,indent=2))
with open('rec1_h_saniyelik_duzeltilmis.csv','w',newline='',encoding='utf-8-sig') as fh:
    w=csv.DictWriter(fh,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
print(json.dumps(out,indent=2))
