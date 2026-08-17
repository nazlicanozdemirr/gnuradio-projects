from pathlib import Path
import numpy as np
from scipy import signal

FS = 576000.0

for name in ("A", "B"):
    x = np.memmap(Path(f"iq_compare_{name}.bin"), dtype=np.complex64, mode="r")
    n = min(x.size, int(8 * FS))
    f = np.angle(x[1:n] * np.conj(x[:n-1])).astype(np.float64) * FS / (2*np.pi)

    # Symbol-clock lines in the energy of discriminator changes.
    d = np.abs(np.diff(f))
    d = np.minimum(d, np.percentile(d, 99.5))
    d -= d.mean()
    cf, cp = signal.welch(d, fs=FS, window="hann", nperseg=524288,
                          noverlap=262144, scaling="spectrum")
    mask = (cf >= 5000) & (cf <= 40000)
    inds, props = signal.find_peaks(10*np.log10(cp[mask] + 1e-30), prominence=3)
    mi = np.flatnonzero(mask)[inds]
    strongest = mi[np.argsort(cp[mi])[-12:]][::-1]

    # Raw discriminator histogram peaks. Ignore extreme phase glitches.
    trimmed = f[np.abs(f - np.median(f)) < 30000]
    hist, edges = np.histogram(trimmed, bins=2400, range=(-15000, 15000))
    centers = (edges[:-1] + edges[1:]) / 2
    peaks, prop = signal.find_peaks(hist, distance=40, prominence=max(20, hist.max()*0.01))
    peaks = peaks[np.argsort(hist[peaks])[-10:]][::-1]

    print(f"=== {name} ===")
    print("clock peaks Hz:", [(round(float(cf[i]),3), round(float(10*np.log10(cp[i]+1e-30)),2)) for i in strongest])
    print("raw freq hist peaks Hz/count:", [(round(float(centers[i]),2), int(hist[i])) for i in peaks])
    print("raw freq percentiles:", np.percentile(f, [0.1,1,5,20,50,80,95,99,99.9]))
