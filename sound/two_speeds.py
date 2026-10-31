"""
Two Speeds. One iteration, one note. Pitch from x, stereo position from y,
six notes a second, the same instrument for both. Movement I is Shawl's
orbit; movement II is Wing's. Nothing else is composed.
"""
import sys, numpy as np, argparse
from scipy.signal import fftconvolve
from listen import orbit, write_wav, spectrogram_png, SR
from PIL import Image, ImageDraw

RATE = 6.0            # notes per second
F_LO, OCTAVES = 110.0, 3.0


def instrument(f, dur, sr=SR):
    """A struck bar: sine with a little 2nd and 3rd partial, the partials
    dying faster than the fundamental."""
    n = int(dur * sr); t = np.arange(n) / sr
    env = lambda tau: np.exp(-t / tau)
    s = (np.sin(2 * np.pi * f * t) * env(0.45)
         + 0.28 * np.sin(2 * np.pi * 2 * f * t) * env(0.18)
         + 0.08 * np.sin(2 * np.pi * 3 * f * t) * env(0.09))
    a = int(0.004 * sr); s[:a] *= np.linspace(0, 1, a)
    return s


def room(sr=SR, length=1.4, seed=1):
    """A synthetic impulse response: a few early reflections, then a
    decaying noise tail."""
    rng = np.random.default_rng(seed); n = int(length * sr); t = np.arange(n) / sr
    ir = rng.standard_normal(n) * np.exp(-t / 0.35) * 0.035
    for d, g in [(0.011, 0.5), (0.023, 0.35), (0.037, 0.25), (0.053, 0.18)]:
        ir[int(d * sr)] += g
    ir[0] = 1.0
    return ir


def movement(name, seconds, seed_xy=(0.13, -0.07), sr=SR):
    n_notes = int(seconds * RATE)
    xs, ys = orbit(name, n_notes, x=seed_xy[0], y=seed_xy[1])
    lo, hi = np.percentile(xs, [0.5, 99.5]); ylo, yhi = np.percentile(ys, [0.5, 99.5])
    pitch = F_LO * 2 ** (OCTAVES * np.clip((xs - lo) / (hi - lo), 0, 1))
    pan = np.clip((ys - ylo) / (yhi - ylo), 0, 1)                  # 0 left .. 1 right
    total = int((seconds + 3) * sr); L = np.zeros(total); R = np.zeros(total)
    note = 1.6
    for i in range(n_notes):
        s = instrument(pitch[i], note) * 0.5
        k = int(i / RATE * sr); m = min(len(s), total - k)
        L[k:k + m] += s[:m] * np.sqrt(1 - pan[i]); R[k:k + m] += s[:m] * np.sqrt(pan[i])
    ir = room(sr)
    L = fftconvolve(L, ir)[:total]; R = fftconvolve(R, ir)[:total]
    fo = int(3 * sr); L[-fo:] *= np.linspace(1, 0, fo); R[-fo:] *= np.linspace(1, 0, fo)
    fi = int(0.5 * sr); L[:fi] *= np.linspace(0, 1, fi); R[:fi] *= np.linspace(0, 1, fi)
    return L, R, pitch, pan


def score_png(pitch, pan, path, title, seconds):
    """The notes as a roll on paper: time across, pitch up."""
    W, H = 2400, 700; im = Image.new("RGB", (W, H), (246, 242, 232)); d = ImageDraw.Draw(im)
    for k in range(int(OCTAVES) + 1):
        y = H - 60 - k / OCTAVES * (H - 120); d.line([(60, y), (W - 60, y)], fill=(215, 208, 196), width=1)
    n = len(pitch)
    for i in range(n):
        x = 60 + i / n * (W - 120); y = H - 60 - np.log2(pitch[i] / F_LO) / OCTAVES * (H - 120)
        g = int(40 + 120 * pan[i]); d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(g, g - 4, g - 2))
    d.text((60, 14), f"{title}: {n} notes, {seconds:.0f} s, {RATE:.0f} per second. Up is pitch, three octaves; grey is left-to-right.", fill=(110, 100, 92))
    im.save(path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seconds", type=float, default=150); ap.add_argument("--out", default=".")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    parts = {}
    for name in ["shawl", "wing"]:
        if a.only and name != a.only: continue
        L, R, pitch, pan = movement(name, a.seconds)
        parts[name] = (L, R)
        write_wav(f"{a.out}/two-speeds-{name}.wav", L, R)
        spectrogram_png(L, f"{a.out}/two-speeds-{name}-spectrogram.png", fmax=3000, title=f"Two Speeds, {name}")
        score_png(pitch, pan, f"{a.out}/two-speeds-{name}-score.png", name.capitalize(), a.seconds)
        print(name, "done", len(L) / SR, "s", flush=True)
    if len(parts) == 2:
        gap = np.zeros(int(4 * SR))
        L = np.concatenate([parts["shawl"][0], gap, parts["wing"][0]]); R = np.concatenate([parts["shawl"][1], gap, parts["wing"][1]])
        write_wav(f"{a.out}/two-speeds.wav", L, R); print("two-speeds.wav", len(L) / SR, "s")
