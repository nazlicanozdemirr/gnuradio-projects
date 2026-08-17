import numpy as np
from scipy import ndimage, signal

FS=576000.0
RS=9600.0

for name, expected in [('A',(-4400,2700)),('B',(-3050,3250)),('C',(-3080,2830))]:
    x=np.memmap(f'iq_compare_{name}.bin',dtype=np.complex64,mode='r')
    f=np.angle(x[1:]*np.conj(x[:-1])).astype(float)*FS/(2*np.pi)
    rows=[]
    for sec in range(1,int(x.size/FS)):
        z=f[sec*int(FS):min(len(f),(sec+1)*int(FS))]
        hist,edges=np.histogram(z,bins=4000,range=(-10000,10000))
        hist=ndimage.gaussian_filter1d(hist.astype(float),2)
        centers=(edges[:-1]+edges[1:])/2
        vals=[]
        for target in expected:
            mask=np.abs(centers-target)<700
            idx=np.flatnonzero(mask)[np.argmax(hist[mask])]
            vals.append(centers[idx])
        rows.append((sec,*vals,(vals[1]-vals[0])/RS,(vals[1]+vals[0])/2))
    hs=np.array([r[3] for r in rows]); cs=np.array([r[4] for r in rows])
    print(name,'rows',rows)
    print(name,'h',hs.mean(),hs.std(),hs.min(),hs.max(),'center',cs.mean(),cs.std())
