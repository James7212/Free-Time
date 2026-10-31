"""
High-resolution attractor renderer.

One long orbit, accumulated into a density grid plus a direction field
(the mean heading of the orbit through each pixel). Density gives the
lightness; direction, optionally, gives the hue.
"""
import argparse, json, math, os, time
import numpy as np
from numba import njit
from PIL import Image

FAM_ID = {"clifford": 0, "dejong": 1, "svensson": 2, "bedhead": 3, "gumowski_mira": 4, "fold": 5}


@njit(cache=True, fastmath=True)
def _step(fid, x, y, p):
    if fid == 0:
        a, b, c, d = p[0], p[1], p[2], p[3]
        return math.sin(a * y) + c * math.cos(a * x), math.sin(b * x) + d * math.cos(b * y)
    elif fid == 1:
        a, b, c, d = p[0], p[1], p[2], p[3]
        return math.sin(a * y) - math.cos(b * x), math.sin(c * x) - math.cos(d * y)
    elif fid == 2:
        a, b, c, d = p[0], p[1], p[2], p[3]
        return d * math.sin(a * x) - math.sin(b * y), c * math.cos(a * x) + math.cos(b * y)
    elif fid == 3:
        a, b = p[0], p[1]
        return math.sin(x * y / b) * y + math.cos(a * x - y), x + math.sin(y) / b
    elif fid == 4:
        a, al = p[0], p[1]
        fx = a * x + 2.0 * (1.0 - a) * x * x / (1.0 + x * x)
        xn = y + al * (1.0 - 0.05 * y * y) * y + fx
        fxn = a * xn + 2.0 * (1.0 - a) * xn * xn / (1.0 + xn * xn)
        return xn, -x + fxn
    else:
        a, b, c, d, e = p[0], p[1], p[2], p[3], p[4]
        r = math.sqrt(x * x + y * y)
        t = math.tanh(r)
        return (math.sin(a * y) + c * math.cos(a * x) + e * t * math.cos(b * r),
                math.sin(b * x) + d * math.cos(b * y) + e * t * math.sin(a * r))


@njit(cache=True)
def _bbox(fid, p, n):
    x = 0.1; y = 0.1
    for _ in range(2000):
        x, y = _step(fid, x, y, p)
    xs = np.empty(n); ys = np.empty(n)
    for i in range(n):
        x, y = _step(fid, x, y, p)
        xs[i] = x; ys[i] = y
    return xs, ys


@njit(cache=True, fastmath=True)
def _accumulate(fid, p, n, res, x0, y0, scale, H, CX, CY, seed):
    # start from a fixed, pseudo-random point; burn in
    x = 0.1 + 0.01 * seed; y = -0.1 + 0.007 * seed
    for _ in range(2000):
        x, y = _step(fid, x, y, p)
    for _ in range(n):
        xn, yn = _step(fid, x, y, p)
        i = int((xn - x0) * scale)
        j = int((yn - y0) * scale)
        if 0 <= i < res and 0 <= j < res:
            H[i, j] += 1.0
            dx = xn - x; dy = yn - y
            d = math.sqrt(dx * dx + dy * dy) + 1e-12
            CX[i, j] += dx / d
            CY[i, j] += dy / d
        x, y = xn, yn


@njit(cache=True, fastmath=True)
def _accumulate_cloud(fid, p, n_starts, steps, burn, spread, res, x0, y0, scale, H, CX, CY, seed):
    """Many short orbits from random starts in [-spread, spread]^2. For
    quasi-periodic maps this draws the whole family of invariant curves
    rather than the single curve one orbit would trace."""
    np.random.seed(seed)
    for k in range(n_starts):
        x = (np.random.random() * 2 - 1) * spread
        y = (np.random.random() * 2 - 1) * spread
        ok = True
        for _ in range(burn):
            x, y = _step(fid, x, y, p)
            if not (abs(x) < 1e3 and abs(y) < 1e3):
                ok = False; break
        if not ok:
            continue
        for _ in range(steps):
            xn, yn = _step(fid, x, y, p)
            if not (abs(xn) < 1e3 and abs(yn) < 1e3):
                break
            i = int((xn - x0) * scale)
            j = int((yn - y0) * scale)
            if 0 <= i < res and 0 <= j < res:
                H[i, j] += 1.0
                dx = xn - x; dy = yn - y
                d = math.sqrt(dx * dx + dy * dy) + 1e-12
                CX[i, j] += dx / d
                CY[i, j] += dy / d
            x, y = xn, yn


@njit(cache=True)
def _bbox_cloud(fid, p, n_starts, steps, spread, seed):
    np.random.seed(seed)
    xs = np.empty(n_starts * steps); ys = np.empty(n_starts * steps)
    m = 0
    for k in range(n_starts):
        x = (np.random.random() * 2 - 1) * spread
        y = (np.random.random() * 2 - 1) * spread
        ok = True
        for _ in range(200):
            x, y = _step(fid, x, y, p)
            if not (abs(x) < 1e3 and abs(y) < 1e3):
                ok = False; break
        if not ok:
            continue
        for _ in range(steps):
            x, y = _step(fid, x, y, p)
            if not (abs(x) < 1e3 and abs(y) < 1e3):
                break
            xs[m] = x; ys[m] = y; m += 1
    return xs[:m], ys[:m]


def accumulate(family, params, res, n_points, pad=0.04, seed=0, starts=1, spread=0.5, pct=(0.05, 99.95)):
    fid = FAM_ID[family]
    p = np.asarray(params, dtype=np.float64)
    if starts > 1:
        xs, ys = _bbox_cloud(fid, p, min(starts, 2000), 300, spread, seed)
    else:
        xs, ys = _bbox(fid, p, 400_000)
    x0, x1 = np.percentile(xs, list(pct))
    y0, y1 = np.percentile(ys, list(pct))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    half = max(x1 - x0, y1 - y0) / 2 * (1 + pad)
    H = np.zeros((res, res)); CX = np.zeros((res, res)); CY = np.zeros((res, res))
    scale = res / (2 * half)
    if starts > 1:
        steps = max(1, n_points // starts)
        _accumulate_cloud(fid, p, starts, steps, 200, spread, res, cx - half, cy - half, scale, H, CX, CY, seed)
    else:
        _accumulate(fid, p, n_points, res, cx - half, cy - half, scale, H, CX, CY, seed)
    return H, CX, CY


# ---------------------------------------------------------------- colour

def _lerp_palette(stops, t):
    """stops: list of (pos, (r,g,b)) with pos in [0,1]; t: array in [0,1]."""
    pos = np.array([s[0] for s in stops]); cols = np.array([s[1] for s in stops], dtype=float)
    out = np.empty(t.shape + (3,))
    for k in range(3):
        out[..., k] = np.interp(t, pos, cols[:, k])
    return out


PALETTES = {
    # dark ground, warm light
    "ember": [(0, (6, 4, 8)), (0.15, (54, 10, 24)), (0.4, (170, 40, 30)), (0.7, (245, 150, 60)), (1, (255, 246, 220))],
    # dark ground, cold light
    "glass": [(0, (3, 5, 12)), (0.2, (12, 30, 80)), (0.5, (30, 120, 190)), (0.8, (170, 230, 245)), (1, (255, 255, 255))],
    # dark ground, green-gold
    "moss": [(0, (4, 6, 4)), (0.2, (14, 40, 26)), (0.5, (60, 130, 70)), (0.8, (200, 215, 120)), (1, (255, 252, 230))],
    # pale paper, dark ink
    "ink": [(0, (246, 242, 232)), (0.3, (190, 180, 165)), (0.6, (90, 80, 72)), (1, (18, 16, 20))],
    # pale paper, one colour of ink
    "indigo": [(0, (247, 244, 236)), (0.35, (160, 170, 200)), (0.7, (50, 60, 130)), (1, (14, 10, 50))],
}


def tone(H, gamma=0.55, clip=0.9995):
    """log density -> [0,1], with the brightest tail clipped so one hot
    spot doesn't flatten everything else."""
    L = np.log1p(H)
    hi = np.quantile(L[L > 0], clip) if np.any(L > 0) else 1.0
    t = np.clip(L / hi, 0, 1) ** gamma
    return t


def colourise(H, CX, CY, palette="ember", mode="density", gamma=0.55, hue_shift=0.0, sat=0.75, hue_range=1.0):
    t = tone(H, gamma)
    if mode == "density":
        rgb = _lerp_palette(PALETTES[palette], t)
    elif mode == "silk":
        # hue from mean heading, lightness from density
        ang = np.arctan2(CY, CX) / (2 * np.pi) + 0.5          # heading in [0,1)
        # fold the circle so opposite headings share a hue, then squeeze into a band
        ang = np.abs(ang - 0.5) * 2.0                              # [0,1], 0 and 1 are the same heading
        ang = (hue_shift + hue_range * ang) % 1.0
        # coherence: how aligned the headings through this pixel are
        coh = np.sqrt(CX * CX + CY * CY) / (H + 1e-9)
        hsv = np.stack([ang, np.clip(coh, 0, 1) * sat, t], -1)
        rgb = _hsv_to_rgb(hsv) * 255
        if palette in ("ink", "indigo"):
            rgb = 255 - rgb  # paper variant
    else:
        raise ValueError(mode)
    return np.clip(rgb, 0, 255).astype(np.uint8)


def _hsv_to_rgb(hsv):
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    i = np.floor(h * 6).astype(int) % 6
    f = h * 6 - np.floor(h * 6)
    p = v * (1 - s); q = v * (1 - f * s); t = v * (1 - (1 - f) * s)
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], -1)


def to_pil(rgb, downsample=1):
    img = Image.fromarray(np.flipud(rgb.transpose(1, 0, 2)))
    if downsample > 1:
        img = img.resize((img.width // downsample, img.height // downsample), Image.LANCZOS)
    return img


def render(family, params, size=2000, points=100_000_000, supersample=2, palette="ember",
           mode="density", gamma=0.55, hue_shift=0.0, seed=0, sat=0.75, hue_range=1.0,
           starts=1, spread=0.5, pad=0.04, pct=(0.05, 99.95)):
    res = size * supersample
    H, CX, CY = accumulate(family, params, res, points, pad=pad, seed=seed, starts=starts, spread=spread, pct=pct)
    rgb = colourise(H, CX, CY, palette, mode, gamma, hue_shift, sat, hue_range)
    return to_pil(rgb, supersample), H


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("family"); ap.add_argument("--params", required=True, help="comma-separated, use --params=-1,2,...")
    ap.add_argument("--size", type=int, default=2000)
    ap.add_argument("--points", type=int, default=100_000_000)
    ap.add_argument("--ss", type=int, default=2)
    ap.add_argument("--palette", default="ember"); ap.add_argument("--mode", default="density")
    ap.add_argument("--gamma", type=float, default=0.55); ap.add_argument("--hue", type=float, default=0.0)
    ap.add_argument("--sat", type=float, default=0.75); ap.add_argument("--range", type=float, default=1.0)
    ap.add_argument("--starts", type=int, default=1, help=">1 = cloud of orbits (for quasi-periodic maps)")
    ap.add_argument("--spread", type=float, default=0.5)
    ap.add_argument("--out", default="out.png")
    a = ap.parse_args()
    t = time.time()
    img, _ = render(a.family, [float(v) for v in a.params.split(",")], a.size, a.points, a.ss,
                    a.palette, a.mode, a.gamma, a.hue, 0, a.sat, a.range, a.starts, a.spread)
    img.save(a.out)
    print(f"{a.out}  {time.time()-t:.1f}s")
