import json
from pathlib import Path

import numpy as np
from scipy import signal

from compare_iq_cpfsks import analyze, FS, RS, SPS


def kmeans_1d(values, k, iterations=30):
    values = np.asarray(values, float)
    lo, hi = np.percentile(values, [0.2, 99.8])
    values = values[(values > lo) & (values < hi)]
    centers = np.percentile(values, np.linspace(5, 95, k))
    for _ in range(iterations):
        edges = (centers[:-1] + centers[1:]) / 2
        labels = np.searchsorted(edges, values)
        new = np.array([values[labels == i].mean() for i in range(k)])
        if np.max(np.abs(new-centers)) < 1e-7:
            centers = new
            break
        centers = new
    labels = np.searchsorted((centers[:-1]+centers[1:])/2, values)
    counts = np.array([(labels == i).sum() for i in range(k)])
    rms = np.sqrt(sum(np.sum((values[labels == i]-centers[i])**2)
                      for i in range(k))/values.size)
    return centers, rms, counts/values.size


path = Path("iq_compare_C.bin")
general = analyze("C", path)
x = np.memmap(path, dtype=np.complex64, mode="r")
n = min(x.size, int(8*FS))
frequency = np.angle(x[1:n]*np.conj(x[:n-1])).astype(float)*FS/(2*np.pi)

# Spectral lines in discriminator-change energy reveal the symbol clock.
d = np.abs(np.diff(frequency))
d = np.minimum(d, np.percentile(d, 99.5))
d -= d.mean()
cf, cp = signal.welch(d, fs=FS, window="hann", nperseg=524288,
                       noverlap=262144, scaling="spectrum")
mask = (cf >= 5000) & (cf <= 40000)
peaks, _ = signal.find_peaks(10*np.log10(cp[mask]+1e-30), prominence=3)
peaks = np.flatnonzero(mask)[peaks]
peaks = peaks[np.argsort(cp[peaks])[-12:]][::-1]
clock_peaks = [(float(cf[i]), float(10*np.log10(cp[i]+1e-30))) for i in peaks]

# Raw discriminator modes.
hist, edges = np.histogram(frequency, bins=2400, range=(-15000, 15000))
hist_centers = (edges[:-1]+edges[1:])/2
hp, _ = signal.find_peaks(hist, distance=40, prominence=max(20, hist.max()*0.01))
hp = hp[np.argsort(hist[hp])[-12:]][::-1]
hist_peaks = [(float(hist_centers[i]), int(hist[i])) for i in hp]

# Check whether 2, 3, 4, 5 or 6 symbol-frequency clusters best describe C.
start, stop = int(FS), min(frequency.size, int(6*FS))
cluster_models = []
for k in range(2, 7):
    rows = []
    for phase in range(SPS):
        first = start + ((phase-start) % SPS)
        centers, rms, weights = kmeans_1d(frequency[first:stop:SPS], k)
        quality = np.min(np.diff(centers))/(2*rms+1e-15)
        rows.append((quality, phase, centers, rms, weights))
    quality, phase, centers, rms, weights = max(rows, key=lambda row: row[0])
    cluster_models.append({
        "k": k, "phase": phase, "quality": float(quality),
        "centers_hz": centers.tolist(), "rms_hz": float(rms),
        "weights": weights.tolist(),
    })

result = {
    "general": general,
    "clock_peaks_hz_db": clock_peaks,
    "raw_frequency_histogram_peaks_hz_count": hist_peaks,
    "cluster_models": cluster_models,
}
Path("iq_C_probe.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({
    "duration": general["duration_seconds"],
    "initial_tones": general["cpfsk_tones"],
    "per_second": general["per_second_summary"],
    "timing": general["timing_periodicity"],
    "clock_peaks": clock_peaks[:6],
    "hist_peaks": hist_peaks[:8],
    "cluster_models": cluster_models,
    "spectrum": general["spectrum"],
    "iq": general["iq"],
    "envelope": general["envelope"],
}, indent=2))
