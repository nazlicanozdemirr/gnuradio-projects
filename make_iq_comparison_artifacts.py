import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

FS = 576000.0
RS = 9600.0
SPS = 60
CONFIG = {
    "A": {"path": Path("iq_compare_A.bin"), "k": 2, "phase": 57,
          "model": "2 seviyeli tam-tepkili CPFSK", "expected_tones": (-4400, 2700)},
    "B": {"path": Path("iq_compare_B.bin"), "k": 4, "phase": 20,
          "model": "2 sembole yayılan kısmi-tepkili ikili CPM/CPFSK adayı",
          "expected_tones": (-3050, 3250)},
}


def cluster_1d(values, k, iterations=30):
    values = np.asarray(values, float)
    lo, hi = np.percentile(values, [0.2, 99.8])
    values = values[(values > lo) & (values < hi)]
    centers = np.percentile(values, np.linspace(5, 95, k))
    for _ in range(iterations):
        edges = (centers[:-1] + centers[1:]) / 2
        labels = np.searchsorted(edges, values)
        new = np.array([
            values[labels == i].mean() if np.any(labels == i) else centers[i]
            for i in range(k)
        ])
        if np.max(np.abs(new - centers)) < 1e-7:
            centers = new
            break
        centers = new
    edges = (centers[:-1] + centers[1:]) / 2
    labels = np.searchsorted(edges, values)
    counts = np.array([(labels == i).sum() for i in range(k)])
    sse = sum(np.sum((values[labels == i] - centers[i]) ** 2) for i in range(k))
    rms = np.sqrt(sse / values.size)
    return centers, rms, counts / values.size


def score(centers, rms):
    return np.min(np.diff(centers)) / (2 * rms + 1e-15)


def phase_samples(freq, start, stop, phase):
    first = start + ((phase - start) % SPS)
    return freq[first:stop:SPS]


def outer_histogram_modes(values, expected_tones):
    raw_hist, edges = np.histogram(values, bins=4000, range=(-10000, 10000))
    kernel = signal.windows.gaussian(13, std=2)
    smooth = np.convolve(raw_hist.astype(float), kernel/kernel.sum(), mode="same")
    bin_centers = (edges[:-1] + edges[1:]) / 2
    modes = []
    for target in expected_tones:
        mask = np.abs(bin_centers - target) < 700
        index = np.flatnonzero(mask)[np.argmax(smooth[mask])]
        modes.append(float(bin_centers[index]))
    return modes


def analyze_model(name, cfg):
    x = np.memmap(cfg["path"], dtype=np.complex64, mode="r")
    freq = np.angle(x[1:] * np.conj(x[:-1])).astype(float) * FS / (2*np.pi)
    duration = x.size / FS
    start = int(FS)
    stop = min(freq.size, int(6*FS))

    # Re-optimize global phase for the selected model.
    phase_rows = []
    for phase in range(SPS):
        c, r, w = cluster_1d(phase_samples(freq, start, stop, phase), cfg["k"])
        phase_rows.append((score(c, r), phase, c, r, w))
    _, phase, centers, cluster_rms, weights = max(phase_rows, key=lambda row: row[0])

    if cfg["k"] == 2:
        center = float(np.mean(centers))
        deviation = float((centers[-1] - centers[0]) / 2)
        h = float((centers[-1] - centers[0]) / RS)
        inner_outer = None
    else:
        # For a two-tap partial-response binary frequency pulse, the four levels
        # are approximately -(a+b), -(a-b), +(a-b), +(a+b). The outer pair gives
        # the steady-state deviation and therefore the modulation index.
        center = float(np.mean(centers))
        centered = centers - center
        deviation = float((centered[-1] - centered[0]) / 2)
        inner = float((centered[2] - centered[1]) / 2)
        inner_outer = inner / deviation
        h = float(2 * deviation / RS)

    per_second = []
    for sec in range(1, int(duration)):
        s0 = sec * int(FS)
        s1 = min(freq.size, s0 + int(FS))
        tone_lo, tone_hi = outer_histogram_modes(freq[s0:s1], cfg["expected_tones"])
        ctr = (tone_lo + tone_hi) / 2
        dev = (tone_hi - tone_lo) / 2
        per_second.append({
            "recording": name,
            "second": sec,
            "phase": "",
            "center_hz": ctr,
            "deviation_hz": dev,
            "h": 2 * dev / RS,
            "cluster_rms_hz": "",
            "quality": "",
        })

    # PSD arrays for comparison plot.
    psd_n = min(x.size, 2**20)
    psd_start = (x.size - psd_n)//2
    f_psd, p_psd = signal.welch(np.asarray(x[psd_start:psd_start+psd_n]),
                                fs=FS, window="hann", nperseg=32768,
                                noverlap=16384, return_onesided=False,
                                scaling="density")
    f_psd = np.fft.fftshift(f_psd)
    p_psd = np.fft.fftshift(p_psd)
    p_psd_db = 10*np.log10(p_psd + 1e-30)
    p_psd_db -= np.max(p_psd_db)

    symbols = phase_samples(freq, start, min(freq.size, int(8*FS)), phase)
    return {
        "name": name,
        "model": cfg["model"],
        "phase": phase,
        "centers_hz": centers.tolist(),
        "center_hz": center,
        "deviation_hz": deviation,
        "h": h,
        "cluster_rms_hz": float(cluster_rms),
        "weights": weights.tolist(),
        "inner_outer_ratio": inner_outer,
        "duration_seconds": duration,
        "per_second": per_second,
        "psd_f": f_psd,
        "psd_db": p_psd_db,
        "symbols": symbols,
    }


results = {name: analyze_model(name, cfg) for name, cfg in CONFIG.items()}

# Rec1/B is partial-response: instantaneous outer histogram modes are not the
# CPFSK deviation. Use phase accumulated over fractional recovered symbols.
rec1_corrected = json.loads(Path("rec1_h_saniyelik_duzeltilmis.json").read_text(encoding="utf-8"))
results["B"]["per_second"] = [
    {"recording": "B", "second": row["second"], "phase": "",
     "center_hz": row["center_hz"], "deviation_hz": row["deviation_hz"],
     "h": row["h"], "cluster_rms_hz": "", "quality": ""}
    for row in rec1_corrected["rows"]
]
results["B"]["center_hz"] = float(np.mean([r["center_hz"] for r in rec1_corrected["rows"]]))
results["B"]["deviation_hz"] = float(np.mean([r["deviation_hz"] for r in rec1_corrected["rows"]]))
results["B"]["h"] = rec1_corrected["mean"]

with open("iq_h_zaman_serisi.csv", "w", newline="", encoding="utf-8-sig") as fh:
    fields = ["recording", "second", "phase", "center_hz", "deviation_hz", "h",
              "cluster_rms_hz", "quality"]
    writer = csv.DictWriter(fh, fieldnames=fields)
    writer.writeheader()
    for result in results.values():
        writer.writerows(result["per_second"])

summary = {}
for name, r in results.items():
    hs = np.array([row["h"] for row in r["per_second"]])
    centers = np.array([row["center_hz"] for row in r["per_second"]])
    summary[name] = {
        key: value for key, value in r.items()
        if key not in ("per_second", "psd_f", "psd_db", "symbols")
    }
    summary[name]["h_per_second_mean"] = float(hs.mean())
    summary[name]["h_per_second_std"] = float(hs.std())
    summary[name]["h_per_second_min"] = float(hs.min())
    summary[name]["h_per_second_max"] = float(hs.max())
    summary[name]["center_per_second_mean_hz"] = float(centers.mean())
    summary[name]["center_per_second_std_hz"] = float(centers.std())
    summary[name]["recommended_h_estimate"] = float(hs.mean())
    summary[name]["recommended_h_one_sigma"] = float(hs.std())

Path("iq_model_duyarlı_özet.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
)

plt.style.use("seaborn-v0_8-whitegrid")
fig, axes = plt.subplots(2, 2, figsize=(15, 9), constrained_layout=True)
colors = {"A": "#1769e0", "B": "#e05a17"}

ax = axes[0, 0]
for name, r in results.items():
    mask = np.abs(r["psd_f"]) <= 20000
    ax.plot(r["psd_f"][mask]/1000, r["psd_db"][mask], lw=1.1,
            color=colors[name], label=f"Kayıt {name}")
ax.set(title="Normalize güç spektrumu", xlabel="Baseband frekansı (kHz)", ylabel="Göreli PSD (dB)", ylim=(-70, 3))
ax.legend()

for col, name in enumerate(("A", "B")):
    ax = axes[0, 1] if name == "A" else axes[1, 0]
    r = results[name]
    lo, hi = np.percentile(r["symbols"], [0.1, 99.9])
    ax.hist(r["symbols"], bins=220, range=(lo, hi), density=True,
            color=colors[name], alpha=0.82)
    for c in r["centers_hz"]:
        ax.axvline(c, color="black", lw=0.8, ls="--")
    ax.set(title=f"Kayıt {name}: sembol-fazlı anlık frekans dağılımı",
           xlabel="Anlık frekans (Hz)", ylabel="Olasılık yoğunluğu")

ax = axes[1, 1]
for name, r in results.items():
    seconds = [row["second"] for row in r["per_second"]]
    hs = [row["h"] for row in r["per_second"]]
    ax.plot(seconds, hs, marker="o", ms=3.5, lw=1.2, color=colors[name], label=f"Kayıt {name}")
ax.set(title="Saniyelik modülasyon indisi tahmini", xlabel="Kayıt zamanı (s)", ylabel="h", ylim=(0, 0.9))
ax.legend()

fig.suptitle("İki complex64 IQ kaydının CPFSK/CPM karşılaştırması — Fs=576 kS/s, Rs=9.6 kBd", fontsize=15)
fig.savefig("iki_iq_karsilastirma.png", dpi=170)

for name, s in summary.items():
    print(name, json.dumps(s, ensure_ascii=False))
