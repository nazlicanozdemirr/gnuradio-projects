from pathlib import Path
import numpy as np
from scipy import signal

FS = 576000.0
RS = 9600.0
SPS = 60


def kmeans_1d(x, k, iterations=30):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    centers = np.percentile(x, np.linspace(5, 95, k))
    for _ in range(iterations):
        boundaries = (centers[:-1] + centers[1:]) / 2
        labels = np.searchsorted(boundaries, x)
        new = np.array([x[labels == i].mean() if np.any(labels == i) else centers[i]
                        for i in range(k)])
        if np.max(np.abs(new-centers)) < 1e-6:
            centers = new
            break
        centers = new
    boundaries = (centers[:-1] + centers[1:]) / 2
    labels = np.searchsorted(boundaries, x)
    sse = sum(np.sum((x[labels == i] - centers[i])**2) for i in range(k))
    counts = np.array([(labels == i).sum() for i in range(k)])
    # Gaussian equal-variance mixture rough BIC; useful comparatively.
    variance = max(sse / x.size, 1e-12)
    bic = x.size * np.log(variance) + (2*k) * np.log(x.size)
    return centers, np.sqrt(variance), counts/x.size, bic


for name in ("A", "B"):
    x = np.memmap(Path(f"iq_compare_{name}.bin"), dtype=np.complex64, mode="r")
    n = min(x.size, int(7 * FS))
    f = np.angle(x[1:n] * np.conj(x[:n-1])).astype(np.float64) * FS/(2*np.pi)
    start, stop = int(FS), min(f.size, int(6*FS))

    # Find raw-frequency sampling phase with best 2-state separation.
    rows=[]
    for p in range(SPS):
        z=f[start+((p-start)%SPS):stop:SPS]
        z=z[(z>np.percentile(z,0.2))&(z<np.percentile(z,99.8))]
        c,r,w,b=kmeans_1d(z,2)
        rows.append(((c[1]-c[0])/(2*r),p,c,r,w,b))
    rows.sort(reverse=True,key=lambda q:q[0])
    best=rows[0]
    p=best[1]
    z=f[start+((p-start)%SPS):stop:SPS]
    z=z[(z>np.percentile(z,0.2))&(z<np.percentile(z,99.8))]
    print(f"=== {name}: best raw phase {p}, two-state quality {best[0]:.3f} ===")
    for k in range(2,7):
        c,r,w,b=kmeans_1d(z,k)
        print(k, "centers", np.round(c,2), "rms",round(r,2), "weights",np.round(w,3), "BIC",round(b,1))

    # Hist peaks at that phase.
    hist,edges=np.histogram(z,bins=800,range=(-8000,8000))
    cen=(edges[:-1]+edges[1:])/2
    pi,_=signal.find_peaks(hist,distance=25,prominence=max(10,hist.max()*.03))
    pi=pi[np.argsort(hist[pi])[-10:]][::-1]
    print("hist peaks",[(round(float(cen[i]),1),int(hist[i])) for i in pi])

    rows4=[]
    for p4 in range(SPS):
        z4=f[start+((p4-start)%SPS):stop:SPS]
        z4=z4[(z4>np.percentile(z4,0.2))&(z4<np.percentile(z4,99.8))]
        c4,r4,w4,b4=kmeans_1d(z4,4)
        # Four-level visibility: weakest adjacent gap relative to within-cluster RMS.
        q4=np.min(np.diff(c4))/(2*r4)
        rows4.append((q4,p4,c4,r4,w4,b4))
    rows4.sort(reverse=True,key=lambda q:q[0])
    q4,p4,c4,r4,w4,b4=rows4[0]
    centered=c4-c4.mean()
    outer=(centered[-1]-centered[0])/2
    inner=(centered[2]-centered[1])/2
    print("best 4-state", "phase",p4,"quality",round(q4,3),"centers",np.round(c4,2),
          "rms",round(r4,2),"weights",np.round(w4,3),
          "outer h",round(2*outer/RS,6),"inner/outer",round(inner/outer,4))

    if name == "B":
        for test_sps in (30, 60):
            test_rs=FS/test_sps
            for test_k in (2,4):
                test_rows=[]
                for tp in range(test_sps):
                    tz=f[start+((tp-start)%test_sps):stop:test_sps]
                    tc,tr,tw,tb=kmeans_1d(tz,test_k)
                    tq=np.min(np.diff(tc))/(2*tr)
                    test_rows.append((tq,tp,tc,tr,tw))
                tq,tp,tc,tr,tw=max(test_rows,key=lambda row:row[0])
                print("rate test",test_rs,"baud k",test_k,"phase",tp,"quality",round(tq,3),
                      "centers",np.round(tc,2),"weights",np.round(tw,3),
                      "outer-h",round((tc[-1]-tc[0])/test_rs,6))

    # Short diagnostic raw-frequency segment to NPZ.
    seg_start=int(2*FS)
    np.savez_compressed(f"iq_compare_{name}_states.npz",
                        sample=np.arange(20*SPS),
                        freq=f[seg_start:seg_start+20*SPS])
