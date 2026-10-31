"""
Where Wing comes from.

The Gumowski-Mira map has Jacobian determinant 1 + mu(1 - 0.15 y^2).
At mu = 0 it preserves area: no attractors, only invariant curves,
island chains and chaotic seas. Wing is mu = 0.00845. This renders the
same map, a fixed, as mu climbs from zero, and sweeps the Lyapunov
exponent and the orbit's fate across mu.
"""
import sys, math, numpy as np, time
from numba import njit
from PIL import Image, ImageDraw, ImageFont
from render import _step, _accumulate, _accumulate_cloud, colourise, to_pil, FAM_ID

A = -0.49308
FONT = "/mnt/skills/examples/canvas-design/canvas-fonts/CrimsonPro-Regular.ttf"


@njit(cache=True)
def lyap_and_extent(fid, p, n, burn, x, y):
    for _ in range(burn):
        x, y = _step(fid, x, y, p)
        if not (abs(x) < 1e4 and abs(y) < 1e4): return np.nan, np.nan, np.nan
    eps = 1e-8; xs_ = x + eps; ys_ = y; acc = 0.0
    sx = 0.0; sxx = 0.0; sy = 0.0; syy = 0.0
    for _ in range(n):
        x, y = _step(fid, x, y, p); xs_, ys_ = _step(fid, xs_, ys_, p)
        if not (abs(x) < 1e4 and abs(y) < 1e4): return np.nan, np.nan, np.nan
        dx = xs_ - x; dy = ys_ - y; d = math.sqrt(dx * dx + dy * dy) + 1e-300
        acc += math.log(d / eps); xs_ = x + dx / d * eps; ys_ = y + dy / d * eps
        sx += x; sxx += x * x; sy += y; syy += y * y
    vx = sxx / n - (sx / n) ** 2; vy = syy / n - (sy / n) ** 2
    return acc / n, math.sqrt(max(vx, 0.0)), math.sqrt(max(vy, 0.0))


def panel(mu, size, points, cloud, box):
    fid = FAM_ID["gumowski_mira"]; p = np.array([A, mu])
    res = size * 2; H = np.zeros((res, res)); CX = np.zeros((res, res)); CY = np.zeros((res, res))
    (x0, x1), (y0, y1) = box; scale = res / (x1 - x0)
    if cloud:
        _accumulate_cloud(fid, p, 40000, points // 40000, 200, 0.5, res, x0, y0, scale, H, CX, CY, 0)
    else:
        _accumulate(fid, p, points, res, x0, y0, scale, H, CX, CY, 0)
    rgb = colourise(H, CX, CY, "ink", "density", 0.75)
    return to_pil(rgb, 2), H


if __name__ == "__main__":
    t = time.time()
    fid = FAM_ID["gumowski_mira"]
    # 1. sweep
    mus = np.linspace(0.0, 0.06, 601)
    rows = []
    for mu in mus:
        L, sx, sy = lyap_and_extent(fid, np.array([A, mu]), 200_000, 5_000, 0.13, -0.07)
        rows.append((mu, L, sx, sy))
    rows = np.array(rows)
    np.savetxt("genesis-sweep.csv", rows, delimiter=",", header="mu,lyapunov,std_x,std_y", comments="")
    print(f"sweep done [{time.time()-t:.0f}s]")
    for mu, L, sx, sy in rows[::50]:
        print(f"  mu={mu:.4f}  L={L:+.4f}  std_x={sx:.3f}  std_y={sy:.3f}")
    # 2. panels: same frame for all, taken from Wing's extent plus margin
    box = ((-16.5, 20.5), (-17.0, 20.0))
    mu_list = [0.0, 0.001, 0.003, 0.00845, 0.015, 0.03]
    tiles = []
    for mu in mu_list:
        for cloud in (True, False):
            img, H = panel(mu, 1000, 40_000_000, cloud, box)
            tiles.append((mu, cloud, img, (H > 0).mean()))
            print(f"  mu={mu:.5f} {'cloud ' if cloud else 'single'} coverage={(H>0).mean():.4f} [{time.time()-t:.0f}s]", flush=True)
    W = 1000 * len(mu_list); sheet = Image.new("RGB", (W, 2000 + 60), (246, 242, 232)); d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype(FONT, 34)
    for k, (mu, cloud, img, cov) in enumerate(tiles):
        col = k // 2; row = k % 2
        sheet.paste(img, (col * 1000, 60 + row * 1000))
        if row == 0:
            d.text((col * 1000 + 20, 14), f"mu = {mu:g}" + ("   (Wing)" if abs(mu - 0.00845) < 1e-6 else ""), font=f, fill=(60, 56, 58))
    d.text((20, 2000 + 60 - 44), "top row: 40,000 starting points   bottom row: one orbit", font=f, fill=(120, 110, 100))
    sheet.save("genesis-sheet.png"); print("genesis-sheet.png written", f"[{time.time()-t:.0f}s]")
