import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

FS = 576000.0
RS = 9600.0
SPS = 60
FILES = {"A": Path("iq_compare_A.bin"), "B": Path("iq_compare_B.bin"),
         "C": Path("iq_compare_C.bin")}
COLORS = {"A": "#1769e0", "B": "#e05a17", "C": "#178f55"}


def kmeans2(values):
    c = np.percentile(values, [20, 80]).astype(float)
    for _ in range(20):
        threshold = c.mean()
        new = np.array([values[values <= threshold].mean(),
                        values[values > threshold].mean()])
        if np.max(np.abs(new-c)) < 1e-8:
            break
        c = new
    labels = values > c.mean()
    residual = np.where(labels, values-c[1], values-c[0])
    return c, labels, float(np.sqrt(np.mean(residual**2)))


def moving_average(values, length):
    return signal.lfilter(np.ones(length)/length, [1.0], values)


def find_integrate_phase(smoothed, start, stop):
    rows = []
    for phase in range(SPS):
        first = start + ((phase-start) % SPS)
        values = smoothed[first:stop:SPS]
        c, _, rms = kmeans2(values)
        rows.append(((c[1]-c[0])/(2*rms+1e-15), phase, c))
    return max(rows, key=lambda row: row[0])


def crossing_time(profile, level):
    indices = np.flatnonzero((profile[:-1] < level) & (profile[1:] >= level))
    if not indices.size:
        return np.nan
    # Prefer the crossing nearest the middle of the trace.
    middle = (len(profile)-1)/2
    i = indices[np.argmin(np.abs(indices-middle))]
    y0, y1 = profile[i], profile[i+1]
    return i + (level-y0)/(y1-y0+1e-15)


def analyze(name, path):
    x = np.memmap(path, dtype=np.complex64, mode="r")
    max_n = min(x.size, int(10*FS))
    freq = np.angle(x[1:max_n] * np.conj(x[:max_n-1])).astype(float)*FS/(2*np.pi)
    smoothed = moving_average(freq, SPS)
    start, stop = int(FS), min(freq.size, int(8*FS))
    quality, phase, levels = find_integrate_phase(smoothed, start, stop)
    first = start + ((phase-start) % SPS)
    times = np.arange(first, stop, SPS)
    decisions = smoothed[times] > levels.mean()

    # Keep transitions whose previous and next three decisions are constant.
    transition_indices = []
    for k in range(3, decisions.size-3):
        if decisions[k] == decisions[k-1]:
            continue
        if np.all(decisions[k-3:k] == decisions[k-1]) and np.all(decisions[k:k+3] == decisions[k]):
            transition_indices.append(k)

    half = 2*SPS
    traces = []
    offsets = np.arange(-half, half+1)
    for k in transition_indices:
        # Adjacent integrate-and-dump decisions are nominally symbol centered.
        nominal = int(round((times[k-1]+times[k])/2))
        search_lo, search_hi = nominal-SPS//2, nominal+SPS//2
        if search_lo < 4 or search_hi+4 >= freq.size:
            continue
        oriented = freq if decisions[k] else -freq
        local = signal.savgol_filter(oriented[search_lo-4:search_hi+5], 9, 2)
        midpoint = float(levels.mean() if decisions[k] else -levels.mean())
        cross = np.flatnonzero((local[:-1] < midpoint) & (local[1:] >= midpoint))
        if not cross.size:
            continue
        target = (len(local)-1)/2
        ci = cross[np.argmin(np.abs(cross-target))]
        center_index = search_lo-4+ci
        if center_index-half < 0 or center_index+half >= freq.size:
            continue
        trace = np.array(oriented[center_index-half:center_index+half+1], float)
        # Normalize using the outer half-symbol plateaus.
        low = np.median(trace[:SPS//2])
        high = np.median(trace[-SPS//2:])
        if high-low < 1000:
            continue
        traces.append((trace-low)/(high-low))

    traces = np.asarray(traces)
    median_profile = np.median(traces, axis=0)
    median_profile = signal.savgol_filter(median_profile, 11, 2)
    t10 = crossing_time(median_profile, 0.1)
    t90 = crossing_time(median_profile, 0.9)
    rise_samples = t90-t10

    # How far from the transition until the median remains in the 5% band?
    mid = half
    before = np.flatnonzero(median_profile[:mid] > 0.05)
    after_bad = np.flatnonzero(median_profile[mid:] < 0.95)
    pre_memory = (mid-before[0])/SPS if before.size else 0.0
    post_memory = after_bad[-1]/SPS if after_bad.size else 0.0

    return {
        "name": name,
        "integrate_phase": int(phase),
        "integrate_two_cluster_quality": float(quality),
        "integrated_levels_hz": levels.tolist(),
        "isolated_transitions": int(len(traces)),
        "rise_10_90_samples": float(rise_samples),
        "rise_10_90_microseconds": float(rise_samples/FS*1e6),
        "rise_10_90_symbols": float(rise_samples/SPS),
        "pre_transition_memory_symbols_5pct": float(pre_memory),
        "post_transition_memory_symbols_5pct": float(post_memory),
        "offset_symbols": offsets/SPS,
        "median_profile": median_profile,
        "eye_traces": traces[:400],
    }


results = {name: analyze(name, path) for name, path in FILES.items()}

serializable = {}
for name, result in results.items():
    serializable[name] = {k: v for k, v in result.items()
                          if k not in ("offset_symbols", "median_profile", "eye_traces")}
Path("iq_filtre_darbe_analizi.json").write_text(
    json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8"
)

plt.style.use("seaborn-v0_8-whitegrid")
fig, axes = plt.subplots(1, 3, figsize=(19, 5.5), constrained_layout=True)
for ax, name in zip(axes, ("A", "B", "C")):
    r = results[name]
    for trace in r["eye_traces"][::max(1, len(r["eye_traces"])//80)]:
        ax.plot(r["offset_symbols"], trace, color=COLORS[name], alpha=0.035, lw=0.6)
    ax.plot(r["offset_symbols"], r["median_profile"], color="black", lw=2.4,
            label="İzole geçiş medyanı")
    ax.axhline(0.1, color="gray", ls="--", lw=0.8)
    ax.axhline(0.9, color="gray", ls="--", lw=0.8)
    ax.axvline(0, color="gray", ls=":", lw=0.9)
    ax.set(title=f"Kayıt {name}: normalize frekans geçişi",
           xlabel="Geçiş merkezine göre zaman (sembol)", ylabel="Normalize frekans",
           xlim=(-1.3, 1.3), ylim=(-0.25, 1.25))
    ax.legend()
fig.suptitle("İzole CPFSK/CPM ton geçişlerinden darbe şekillendirme incelemesi", fontsize=14)
fig.savefig("iq_filtre_gecis_karsilastirmasi.png", dpi=180)

for name, result in serializable.items():
    print(name, json.dumps(result, ensure_ascii=False))
