"""
Tools for hearing an orbit without ears: spectra, spectrograms, and
direct playback of an orbit's coordinates as a waveform at a chosen
effective sample rate.
"""
import sys, numpy as np, wave
sys.path.insert(0, "../attractors")
from render import _step, FAM_ID
from scipy.signal import resample_poly, welch, stft
from PIL import Image, ImageDraw

SR = 44100
PIECES = {"wing": ("gumowski_mira", [-0.49308, 0.00845]), "bird": ("gumowski_mira", [-0.4569, 0.02581]),
          "shawl": ("clifford", [-1.23644, -2.76143, -1.12015, -0.25936]),
          "stroke": ("clifford", [2.5885, -1.07246, 1.51681, -0.28609]),
          "petal": ("dejong", [-0.11708, -2.84983, 2.26641, 1.17702])}


def orbit(name, n, burn=5000, x=0.13, y=-0.07):
    fam, p = PIECES[name]; fid = FAM_ID[fam]; p = np.asarray(p, dtype=np.float64)
    for _ in range(burn): x, y = _step(fid, x, y, p)
    xs = np.empty(n); ys = np.empty(n)
    for i in range(n):
        x, y = _step(fid, x, y, p); xs[i] = x; ys[i] = y
    return xs, ys


def spectrum(s, nper=4096):
    f, P = welch(s - s.mean(), fs=1.0, nperseg=nper)
    return f, P


def play_direct(s, sr_eff, sr=SR):
    """Treat one iteration as one sample at sr_eff; resample to sr."""
    from math import gcd
    g = gcd(sr, int(sr_eff)); up, down = sr // g, int(sr_eff) // g
    s = (s - s.mean()); s = s / (np.abs(s).max() + 1e-12)
    return resample_poly(s, up, down)


def write_wav(path, left, right=None, sr=SR, peak=0.89):
    right = left if right is None else right
    m = max(np.abs(left).max(), np.abs(right).max()) + 1e-12
    L = (left / m * peak * 32767).astype(np.int16); R = (right / m * peak * 32767).astype(np.int16)
    inter = np.empty(2 * len(L), dtype=np.int16); inter[0::2] = L; inter[1::2] = R
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes(inter.tobytes())


def spectrogram_png(sig, path, sr=SR, fmax=6000, nper=2048, title=""):
    f, t, Z = stft(sig, fs=sr, nperseg=nper, noverlap=nper * 3 // 4)
    S = 20 * np.log10(np.abs(Z) + 1e-9); S = S[f <= fmax]
    S = np.clip((S - S.max() + 70) / 70, 0, 1)
    img = (S[::-1] * 255).astype(np.uint8)
    im = Image.fromarray(img).resize((1600, 500), Image.BILINEAR).convert("RGB")
    ImageDraw.Draw(im).text((8, 6), f"{title}  0-{fmax} Hz, {t[-1]:.0f}s", fill=(255, 220, 120))
    im.save(path)


def spectrum_png(curves, path, title=""):
    """curves: list of (label, f, P) in cycles/iteration; log-log-ish plot."""
    W, H = 1600, 600; im = Image.new("RGB", (W, H), (246, 242, 232)); d = ImageDraw.Draw(im)
    cols = [(40, 36, 38), (180, 60, 40), (40, 90, 170), (30, 130, 70)]
    for k, (lab, f, P) in enumerate(curves):
        m = f > 0; x = 80 + (f[m] / 0.5) * (W - 120)
        y = np.log10(P[m] + 1e-15); y = H - 60 - (y - y.min()) / (np.ptp(y) + 1e-9) * (H - 120)
        d.line(list(zip(x, y)), fill=cols[k % 4], width=2); d.text((100, 20 + 18 * k), lab, fill=cols[k % 4])
    d.text((W - 400, H - 40), "frequency, cycles per iteration (0 to 1/2)", fill=(120, 110, 100))
    d.text((W // 2, 20), title, fill=(60, 56, 58)); im.save(path)
