import json
import math
from pathlib import Path

import numpy as np
from scipy import signal


FS = 576_000.0
RS = 9_600.0
SPS = int(round(FS / RS))
FILES = [
    ("A", Path("iq_compare_A.bin")),
    ("B", Path("iq_compare_B.bin")),
]


def finite_float(value):
    value = float(value)
    return value if math.isfinite(value) else None


def kmeans2_1d(values, iterations=12):
    values = np.asarray(values, dtype=np.float64)
    values = values[np.isfinite(values)]
    if values.size < 100:
        return np.nan, np.nan, np.nan, np.nan, np.nan

    # Robust initialization suppresses transition/outlier influence.
    c0, c1 = np.percentile(values, [20.0, 80.0])
    for _ in range(iterations):
        threshold = (c0 + c1) / 2.0
        low = values[values <= threshold]
        high = values[values > threshold]
        if low.size == 0 or high.size == 0:
            break
        n0, n1 = low.mean(), high.mean()
        if abs(n0 - c0) + abs(n1 - c1) < 1e-9:
            c0, c1 = n0, n1
            break
        c0, c1 = n0, n1

    threshold = (c0 + c1) / 2.0
    low = values[values <= threshold]
    high = values[values > threshold]
    if low.size == 0 or high.size == 0:
        return np.nan, np.nan, np.nan, np.nan, np.nan
    rms = np.sqrt(
        (np.sum((low - c0) ** 2) + np.sum((high - c1) ** 2))
        / values.size
    )
    balance = high.size / values.size
    return c0, c1, rms, balance, threshold


def moving_average(values, length):
    # Same one-symbol rectangular integration used by the GNU Radio flow.
    return signal.lfilter(np.ones(length, dtype=np.float64) / length, [1.0], values)


def timing_score(raw_frequency, candidate_sps, max_seconds=5.0):
    n = min(raw_frequency.size, int(max_seconds * FS))
    if n < candidate_sps * 100:
        return np.nan
    # CPFSK symbol boundaries generate frequency changes. At the true period,
    # change energy is concentrated at a repeatable sample phase.
    changes = np.abs(np.diff(raw_frequency[:n]))
    phase_means = np.array(
        [changes[p::candidate_sps].mean() for p in range(candidate_sps)]
    )
    return float(phase_means.std() / (phase_means.mean() + 1e-15))


def best_symbol_phase(smoothed_frequency, start, stop, phases=None):
    if phases is None:
        phases = range(SPS)
    best = None
    for phase in phases:
        first = start + ((phase - start) % SPS)
        samples = smoothed_frequency[first:stop:SPS]
        c0, c1, rms, balance, threshold = kmeans2_1d(samples)
        separation = c1 - c0
        quality = separation / (2.0 * rms + 1e-15)
        candidate = (quality, -rms, phase, c0, c1, rms, balance, threshold)
        if best is None or candidate[:2] > best[:2]:
            best = candidate
    return best


def occupied_bandwidth(freqs, psd, fraction):
    order = np.argsort(freqs)
    f = freqs[order]
    p = psd[order]
    cumulative = np.cumsum(p)
    cumulative /= cumulative[-1]
    tail = (1.0 - fraction) / 2.0
    lo = float(np.interp(tail, cumulative, f))
    hi = float(np.interp(1.0 - tail, cumulative, f))
    return {"low_hz": lo, "high_hz": hi, "width_hz": hi - lo}


def run_lengths(bits):
    bits = np.asarray(bits, dtype=np.uint8)
    if bits.size == 0:
        return np.array([], dtype=int)
    edges = np.flatnonzero(np.diff(bits) != 0) + 1
    return np.diff(np.r_[0, edges, bits.size])


def analyze(label, path):
    x = np.memmap(path, dtype=np.complex64, mode="r")
    n = int(x.size)
    duration = n / FS

    # Scalar IQ/amplitude statistics use the complete recording.
    finite = np.isfinite(x.real) & np.isfinite(x.imag)
    finite_fraction = finite.mean()
    if finite_fraction < 1.0:
        xv = np.asarray(x[finite], dtype=np.complex64)
    else:
        xv = x
    mag = np.abs(xv)
    power = np.abs(xv) ** 2
    mean_i = float(np.mean(xv.real, dtype=np.float64))
    mean_q = float(np.mean(xv.imag, dtype=np.float64))
    std_i = float(np.std(xv.real, dtype=np.float64))
    std_q = float(np.std(xv.imag, dtype=np.float64))
    rms = float(np.sqrt(np.mean(power, dtype=np.float64)))
    peak = float(np.max(mag))

    # Instantaneous frequency discriminator: angle(x[n] * conj(x[n-1])).
    raw_frequency = (
        np.angle(x[1:] * np.conj(x[:-1])).astype(np.float64)
        * FS
        / (2.0 * np.pi)
    )
    smoothed = moving_average(raw_frequency, SPS)

    # Skip startup and use up to five seconds for a global sampling phase.
    global_start = min(int(FS), max(0, smoothed.size // 20))
    global_stop = min(smoothed.size, global_start + int(5 * FS))
    phase_result = best_symbol_phase(smoothed, global_start, global_stop)
    quality, _, phase, tone_low, tone_high, cluster_rms, one_fraction, threshold = phase_result
    center = (tone_low + tone_high) / 2.0
    separation = tone_high - tone_low
    deviation = separation / 2.0
    h_index = separation / RS

    # Per-second estimates. Allow phase to move by +/- 5 samples to expose drift.
    per_second = []
    for sec in range(1, int(duration)):
        start = sec * int(FS)
        stop = min(smoothed.size, start + int(FS))
        phase_candidates = sorted({(phase + d) % SPS for d in range(-5, 6)})
        pr = best_symbol_phase(smoothed, start, stop, phase_candidates)
        q, _, p, lo, hi, crms, frac, thr = pr
        sep = hi - lo
        per_second.append(
            {
                "second": sec,
                "phase": int(p),
                "tone_low_hz": finite_float(lo),
                "tone_high_hz": finite_float(hi),
                "center_hz": finite_float((lo + hi) / 2.0),
                "deviation_hz": finite_float(sep / 2.0),
                "h": finite_float(sep / RS),
                "cluster_rms_hz": finite_float(crms),
                "cluster_quality_ratio": finite_float(q),
                "one_fraction": finite_float(frac),
            }
        )

    # Hard symbols and simple statistics; this is before NRZ-I/descrambling.
    first = global_start + ((phase - global_start) % SPS)
    hard = (smoothed[first::SPS] > threshold).astype(np.uint8)
    runs = run_lengths(hard)

    # Welch PSD from a representative central section (up to 2^20 samples).
    psd_count = min(n, 2**20)
    psd_start = max(0, (n - psd_count) // 2)
    psd_segment = np.asarray(x[psd_start:psd_start + psd_count])
    freqs, psd = signal.welch(
        psd_segment,
        fs=FS,
        window="hann",
        nperseg=16384,
        noverlap=8192,
        return_onesided=False,
        scaling="density",
    )
    freqs = np.fft.fftshift(freqs)
    psd = np.fft.fftshift(psd)
    psd_db = 10.0 * np.log10(psd + np.finfo(float).tiny)
    peak_indices, _ = signal.find_peaks(psd_db, distance=50, prominence=1.0)
    strongest = peak_indices[np.argsort(psd_db[peak_indices])[-8:]][::-1]
    spectral_peaks = [
        {"frequency_hz": float(freqs[i]), "psd_db_hz": float(psd_db[i])}
        for i in strongest
    ]

    # Verify the presumed 60 SPS by transition-phase periodicity.
    candidates = []
    for candidate_sps in range(20, 101):
        score = timing_score(raw_frequency, candidate_sps)
        candidates.append((score, candidate_sps))
    candidates.sort(reverse=True)
    score_60 = next(score for score, s in candidates if s == SPS)

    h_values = np.array([row["h"] for row in per_second], dtype=float)
    center_values = np.array([row["center_hz"] for row in per_second], dtype=float)
    dev_values = np.array([row["deviation_hz"] for row in per_second], dtype=float)
    phase_values = np.array([row["phase"] for row in per_second], dtype=float)

    # Save compact plotting arrays, not the full recording.
    hist_values = smoothed[first::SPS]
    if hist_values.size > 300_000:
        hist_values = hist_values[:: int(np.ceil(hist_values.size / 300_000))]
    np.savez_compressed(
        f"iq_compare_{label}_plot.npz",
        freqs=freqs,
        psd_db=psd_db,
        symbol_frequency=hist_values,
        seconds=np.array([row["second"] for row in per_second]),
        h=h_values,
        center=center_values,
        deviation=dev_values,
    )

    return {
        "label": label,
        "path": str(path.resolve()),
        "format_assumption": "interleaved float32 IQ / numpy complex64, native little-endian",
        "file_bytes": int(path.stat().st_size),
        "complex_samples": n,
        "sample_rate_hz": FS,
        "symbol_rate_baud_assumed": RS,
        "samples_per_symbol": SPS,
        "duration_seconds": duration,
        "finite_fraction": float(finite_fraction),
        "iq": {
            "mean_i": mean_i,
            "mean_q": mean_q,
            "dc_magnitude": float(math.hypot(mean_i, mean_q)),
            "std_i": std_i,
            "std_q": std_q,
            "std_i_over_std_q": std_i / std_q if std_q else None,
            "correlation_iq": float(np.corrcoef(xv.real, xv.imag)[0, 1]),
        },
        "envelope": {
            "mean": float(np.mean(mag, dtype=np.float64)),
            "std": float(np.std(mag, dtype=np.float64)),
            "coefficient_of_variation": float(np.std(mag, dtype=np.float64) / np.mean(mag, dtype=np.float64)),
            "rms": rms,
            "peak": peak,
            "papr_db": float(20.0 * math.log10(peak / rms)),
        },
        "cpfsk_tones": {
            "best_sample_phase": int(phase),
            "tone_low_hz": finite_float(tone_low),
            "tone_high_hz": finite_float(tone_high),
            "tone_center_hz": finite_float(center),
            "tone_separation_hz": finite_float(separation),
            "deviation_hz": finite_float(deviation),
            "modulation_index_h": finite_float(h_index),
            "cluster_rms_hz": finite_float(cluster_rms),
            "separation_over_2rms": finite_float(quality),
            "hard_one_fraction": finite_float(one_fraction),
            "decision_threshold_hz": finite_float(threshold),
        },
        "per_second_summary": {
            "windows": len(per_second),
            "h_mean": finite_float(np.mean(h_values)) if h_values.size else None,
            "h_std": finite_float(np.std(h_values)) if h_values.size else None,
            "h_min": finite_float(np.min(h_values)) if h_values.size else None,
            "h_max": finite_float(np.max(h_values)) if h_values.size else None,
            "center_mean_hz": finite_float(np.mean(center_values)) if center_values.size else None,
            "center_std_hz": finite_float(np.std(center_values)) if center_values.size else None,
            "center_peak_to_peak_hz": finite_float(np.ptp(center_values)) if center_values.size else None,
            "deviation_mean_hz": finite_float(np.mean(dev_values)) if dev_values.size else None,
            "deviation_std_hz": finite_float(np.std(dev_values)) if dev_values.size else None,
            "sample_phase_min": finite_float(np.min(phase_values)) if phase_values.size else None,
            "sample_phase_max": finite_float(np.max(phase_values)) if phase_values.size else None,
        },
        "per_second": per_second,
        "timing_periodicity": {
            "score_at_60_sps": float(score_60),
            "rank_of_60_among_20_to_100": int(1 + [s for _, s in candidates].index(SPS)),
            "top_candidates": [
                {"samples_per_symbol": int(s), "score": float(score)}
                for score, s in candidates[:10]
            ],
        },
        "hard_symbol_statistics_before_line_decode": {
            "symbols_analyzed": int(hard.size),
            "one_fraction": float(hard.mean()),
            "transition_fraction": float(np.mean(np.diff(hard) != 0)) if hard.size > 1 else None,
            "mean_run_symbols": float(runs.mean()) if runs.size else None,
            "max_run_symbols": int(runs.max()) if runs.size else None,
        },
        "spectrum": {
            "occupied_bw_90": occupied_bandwidth(freqs, psd, 0.90),
            "occupied_bw_99": occupied_bandwidth(freqs, psd, 0.99),
            "occupied_bw_99_9": occupied_bandwidth(freqs, psd, 0.999),
            "strongest_local_peaks": spectral_peaks,
        },
    }


def main():
    results = {
        "analysis_parameters": {
            "sample_rate_hz": FS,
            "symbol_rate_baud": RS,
            "samples_per_symbol": SPS,
            "h_definition": "h = tone_separation / symbol_rate = 2*deviation/symbol_rate",
        },
        "recordings": [],
    }
    for label, path in FILES:
        print(f"Analyzing {label}: {path}", flush=True)
        results["recordings"].append(analyze(label, path))
    Path("iki_iq_analiz_sonuclari.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    for r in results["recordings"]:
        t = r["cpfsk_tones"]
        p = r["per_second_summary"]
        print(
            f"{r['label']}: duration={r['duration_seconds']:.6f}s, "
            f"center={t['tone_center_hz']:.3f}Hz, dev={t['deviation_hz']:.3f}Hz, "
            f"h={t['modulation_index_h']:.6f}, h_1s={p['h_mean']:.6f}+/-{p['h_std']:.6f}"
        )


if __name__ == "__main__":
    main()
