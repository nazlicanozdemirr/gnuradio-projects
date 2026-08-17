import numpy as np

FS=576000.0
RS=9600.0

def km(x,k):
    lo,hi=np.percentile(x,[0.2,99.8]); x=x[(x>lo)&(x<hi)]
    c=np.percentile(x,np.linspace(5,95,k))
    for _ in range(30):
        lab=np.searchsorted((c[:-1]+c[1:])/2,x)
        nc=np.array([x[lab==i].mean() for i in range(k)])
        if np.max(np.abs(nc-c))<1e-6: break
        c=nc
    return c

x=np.memmap('iq_compare_B.bin',dtype=np.complex64,mode='r')
f=np.angle(x[1:]*np.conj(x[:-1])).astype(float)*FS/(2*np.pi)
for k in (4,5,6,7,8):
    hs=[]
    cs=[]
    for sec in range(1,int(x.size/FS)):
        c=km(f[sec*int(FS):min(len(f),(sec+1)*int(FS))],k)
        hs.append((c[-1]-c[0])/RS)
        cs.append((c[-1]+c[0])/2)
    print(k,'h mean/std/min/max',np.mean(hs),np.std(hs),min(hs),max(hs),'center',np.mean(cs),np.std(cs))
