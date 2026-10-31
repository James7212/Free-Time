import sys; sys.path.insert(0, ".")
import numpy as np, math
from numba import njit
from render import _step, FAM_ID
from genesis import A, lyap_and_extent
fid = FAM_ID["gumowski_mira"]

@njit
def period_of(fid, p, x, y, burn, maxp, tol):
    for _ in range(burn):
        x, y = _step(fid, x, y, p)
    x0, y0 = x, y
    for k in range(1, maxp + 1):
        x, y = _step(fid, x, y, p)
        if abs(x - x0) < tol and abs(y - y0) < tol:
            return k
    return -1

d = np.genfromtxt("genesis/genesis-sweep.csv", delimiter=",", names=True); mu, L = d["mu"], d["lyapunov"]
cands = [i for i in range(1, len(mu) - 1) if L[i] < 0.0 and L[i] <= L[i-1] and L[i] <= L[i+1]]
print(f"{'mu':>8s} {'L':>8s} {'period':>7s}  period/3")
rows = []
for i in cands:
    best = (L[i], mu[i])
    for m in np.linspace(mu[i] - 0.00012, mu[i] + 0.00012, 25):
        Lv, _, _ = lyap_and_extent(fid, np.array([A, m]), 100_000, 50_000, 0.13, -0.07)
        if Lv < best[0]: best = (Lv, m)
    Lv, m = best
    per = period_of(fid, np.array([A, m]), 0.13, -0.07, 2_000_000, 100_000, 1e-6)
    rows.append((m, Lv, per))
    print(f"{m:8.5f} {Lv:+8.4f} {per:7d}  {per/3 if per>0 else float('nan'):.2f}", flush=True)
rows = np.array(rows); ok = rows[rows[:, 2] > 0]
if len(ok) > 2:
    print("\nsuccessive mu ratios:", np.round(ok[1:, 0] / ok[:-1, 0], 4).tolist())
    print("periods:", ok[:, 2].astype(int).tolist())
    print("mu * period:", np.round(ok[:, 0] * ok[:, 2], 4).tolist())
