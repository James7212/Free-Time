"""
Orbits as sound.

A quasi-periodic orbit x_n = X(n·rho) samples a periodic function X once
per iteration, advancing rho of a cycle each step. Recover rho and X, and
the orbit becomes a band-limited waveform that can be played at any pitch.
"""
import sys, math, numpy as np
sys.path.insert(0, "../attractors")
from render import _step, FAM_ID


def orbit(family, params, x0, y0, n, burn=2000):
    fid = FAM_ID[family]; p = np.asarray(params, dtype=np.float64)
    x, y = x0, y0
    for _ in range(burn):
        x, y = _step(fid, x, y, p)
        if not (abs(x) < 1e3 and abs(y) < 1e3): return None
    xs = np.empty(n); ys = np.empty(n)
    for i in range(n):
        x, y = _step(fid, x, y, p)
        if not (abs(x) < 1e3 and abs(y) < 1e3): return None
        xs[i] = x; ys[i] = y
    return xs, ys


def rotation_number(xs, pad=8):
    """Fundamental frequency in cycles per iteration, from a zero-padded
    windowed FFT with parabolic peak interpolation."""
    s = xs - xs.mean(); n = len(s)
    w = np.hanning(n); S = np.abs(np.fft.rfft(s * w, n * pad))
    S[: pad * 2] = 0                                   # ignore DC
    k = int(np.argmax(S))
    if 0 < k < len(S) - 1:
        a, b, c = np.log(S[k - 1] + 1e-30), np.log(S[k] + 1e-30), np.log(S[k + 1] + 1e-30)
        k = k + 0.5 * (a - c) / (a - 2 * b + c)
    return k / (n * pad)


def fit_series(xs, rho, K):
    """Least-squares Fourier coefficients of X(theta) given rho; returns
    (residual, cos_coeffs, sin_coeffs)."""
    n = np.arange(len(xs)); s = xs - xs.mean()
    ks = np.arange(1, K + 1)
    ang = 2 * np.pi * np.outer(n, ks) * rho
    A = np.concatenate([np.cos(ang), np.sin(ang)], axis=1)
    coef, res, *_ = np.linalg.lstsq(A, s, rcond=None)
    r = float(np.sqrt(np.mean((A @ coef - s) ** 2)) / (np.std(s) + 1e-12))
    return r, coef[:K], coef[K:]


def refine_rho(xs, rho0, K=32, span=None, iters=24):
    """Golden-section search on the fit residual around rho0."""
    span = span or 2.0 / len(xs)
    lo, hi = rho0 - span, rho0 + span
    g = (math.sqrt(5) - 1) / 2
    a, b = hi - g * (hi - lo), lo + g * (hi - lo)
    fa, fb = fit_series(xs, a, K)[0], fit_series(xs, b, K)[0]
    for _ in range(iters):
        if fa < fb:
            hi, b, fb = b, a, fa; a = hi - g * (hi - lo); fa = fit_series(xs, a, K)[0]
        else:
            lo, a, fa = a, b, fb; b = lo + g * (hi - lo); fb = fit_series(xs, b, K)[0]
    return (lo + hi) / 2


def analyse(family, params, x0, y0, n=32768, K=96, stride=1, phase=0):
    """stride=3, phase=j: analyse the sub-orbit x_{3n+j}, i.e. one island
    of a period-3 chain under the third-iterate map."""
    o = orbit(family, params, x0, y0, n * stride)
    if o is None: return None
    xs, ys = o
    xs = xs[phase::stride]; ys = ys[phase::stride]
    rho = rotation_number(xs)
    rho = refine_rho(xs, rho, K=24)
    r, c, s = fit_series(xs, rho, K)
    return dict(rho=rho, resid=r, cos=c, sin=s, amp=float(np.std(xs)), x0=x0, y0=y0)


def wavetable(c, s, size=4096, kmax=None):
    """One cycle of X(theta) from its Fourier coefficients, band-limited to kmax."""
    K = len(c) if kmax is None else min(kmax, len(c))
    th = 2 * np.pi * np.arange(size) / size
    tab = np.zeros(size)
    for k in range(1, K + 1):
        tab += c[k - 1] * np.cos(k * th) + s[k - 1] * np.sin(k * th)
    return tab


def play(tab, f, sr, dur, phase0=0.0):
    """Wavetable playback with linear interpolation."""
    n = int(dur * sr); size = len(tab)
    ph = (phase0 + f * np.arange(n) / sr) % 1.0
    idx = ph * size; i0 = idx.astype(int); fr = idx - i0; i1 = (i0 + 1) % size
    return tab[i0] * (1 - fr) + tab[i1] * fr
