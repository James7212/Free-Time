"""
Random search over attractor parameter space.

For each candidate:
  1. run a cloud of trajectories, discard burn-in
  2. estimate the largest Lyapunov exponent (is it actually chaotic?)
  3. histogram the orbit onto a coarse grid
  4. score: coverage (not collapsed, not mush) and contrast (filaments)
Survivors go onto contact sheets so a pair of eyes can do the real work.
"""
import argparse, json, os, sys, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from maps import FAMILIES, sample_params


def run_cloud(step, p, n=1500, burn=200, steps=1500, rng=None, lyap=True):
    """Return (xs, ys, lyapunov) or None if the orbit escapes."""
    rng = rng or np.random.default_rng()
    x = rng.uniform(-0.5, 0.5, n)
    y = rng.uniform(-0.5, 0.5, n)
    for _ in range(burn):
        x, y = step(x, y, p)
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
        return None
    if np.max(np.abs(x)) > 1e3 or np.max(np.abs(y)) > 1e3:
        return None

    # Lyapunov: shadow trajectory a hair away, renormalise every step.
    eps = 1e-7
    if lyap:
        xs_, ys_ = x + eps, y
        acc = np.zeros(n)
    X = np.empty((steps, n)); Y = np.empty((steps, n))
    for t in range(steps):
        x, y = step(x, y, p)
        X[t] = x; Y[t] = y
        if lyap:
            xs_, ys_ = step(xs_, ys_, p)
            dx, dy = xs_ - x, ys_ - y
            d = np.sqrt(dx * dx + dy * dy) + 1e-300
            acc += np.log(d / eps)
            xs_, ys_ = x + dx / d * eps, y + dy / d * eps
    if not (np.all(np.isfinite(X)) and np.all(np.isfinite(Y))):
        return None
    if np.max(np.abs(X)) > 1e3 or np.max(np.abs(Y)) > 1e3:
        return None
    L = float(np.median(acc) / steps) if lyap else float("nan")
    return X.ravel(), Y.ravel(), L


def histogram(xs, ys, res=256, pad=0.04):
    x0, x1 = np.percentile(xs, [0.1, 99.9])
    y0, y1 = np.percentile(ys, [0.1, 99.9])
    # square framing
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    half = max(x1 - x0, y1 - y0) / 2 * (1 + pad) + 1e-9
    rng_ = [[cx - half, cx + half], [cy - half, cy + half]]
    H, _, _ = np.histogram2d(xs, ys, bins=res, range=rng_)
    return H, rng_


def score(H):
    nz = H > 0
    coverage = nz.mean()
    if coverage < 0.004:        # collapsed to a point or short cycle
        return None
    logd = np.log1p(H[nz])
    contrast = float(np.std(logd) / (np.mean(logd) + 1e-9))
    p = H[nz] / H.sum()
    entropy = float(-(p * np.log(p)).sum())
    return dict(coverage=float(coverage), contrast=contrast, entropy=entropy)


def to_image(H, res=256):
    img = np.log1p(H)
    img = img / (img.max() + 1e-12)
    img = img ** 0.6
    # dark background, pale ink
    a = (img * 255).astype(np.uint8)
    rgb = np.stack([a * 0.92, a * 0.95, a], -1).astype(np.uint8)
    return Image.fromarray(np.flipud(rgb.transpose(1, 0, 2)))


def contact_sheet(items, path, cols=6, cell=256, label=True):
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + 18)), (8, 8, 10))
    d = ImageDraw.Draw(sheet)
    for i, (img, text) in enumerate(items):
        r, c = divmod(i, cols)
        sheet.paste(img, (c * cell, r * (cell + 18)))
        if label:
            d.text((c * cell + 4, r * (cell + 18) + cell + 2), text, fill=(150, 150, 160))
    sheet.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", default="all")
    ap.add_argument("--n", type=int, default=300, help="candidates per family")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", default="candidates")
    ap.add_argument("--keep", type=int, default=36, help="per family on sheets")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    fams = list(FAMILIES) if args.family == "all" else args.family.split(",")
    log = []
    t0 = time.time()
    for fam in fams:
        step, _ = FAMILIES[fam]
        kept = []
        tried = escaped = collapsed = 0
        for i in range(args.n):
            p = sample_params(fam, rng)
            tried += 1
            r = run_cloud(step, p, rng=rng)
            if r is None:
                escaped += 1; continue
            xs, ys, L = r
            H, box = histogram(xs, ys)
            s = score(H)
            if s is None:
                collapsed += 1; continue
            s.update(family=fam, params=[round(float(v), 5) for v in p], lyapunov=L)
            kept.append((s, H))
        # Rank: want chaotic (L > 0), decent coverage, high contrast.
        def rank(item):
            s, _ = item
            L = s["lyapunov"]
            chaos = 1.0 if L > 0.02 else 0.15          # cycles / quasi-periodic demoted
            cov = s["coverage"]
            cov_term = np.exp(-((np.log(cov) - np.log(0.22)) ** 2) / 3.0)  # broad sweet spot ~22%
            return chaos * cov_term * (0.5 + s["contrast"])
        kept.sort(key=rank, reverse=True)
        top = kept[: args.keep]
        items = []
        for j, (s, H) in enumerate(top):
            s["id"] = f"{fam}-{args.seed}-{j:02d}"
            s["rank_score"] = float(rank((s, H)))
            items.append((to_image(H), f'{s["id"]}  L={s["lyapunov"]:.2f} cov={s["coverage"]:.2f}'))
            log.append(s)
        if items:
            contact_sheet(items, os.path.join(args.out, f"sheet-{fam}-{args.seed}.png"))
        print(f"{fam:14s} tried={tried} escaped={escaped} collapsed={collapsed} "
              f"kept={len(kept)} sheet={len(items)}  [{time.time()-t0:.0f}s]", flush=True)
    with open(os.path.join(args.out, f"log-{'-'.join(fams)}-{args.seed}.json"), "w") as f:
        json.dump(log, f, indent=1)


if __name__ == "__main__":
    main()
