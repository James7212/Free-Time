import sys; sys.path.insert(0, ".")
import numpy as np, math
from numba import njit
from render import _step, FAM_ID
from genesis import A
fid = FAM_ID["gumowski_mira"]

@njit
def rotation_number(fid, p, x, y, burn, n):
    for _ in range(burn):
        x, y = _step(fid, x, y, p)
    # centroid first
    cx = 0.0; cy = 0.0; xx = x; yy = y
    for _ in range(n):
        xx, yy = _step(fid, xx, yy, p); cx += xx; cy += yy
    cx /= n; cy /= n
    # mean angular advance about the centroid, unwrapped
    th0 = math.atan2(y - cy, x - cx); total = 0.0
    for _ in range(n):
        x, y = _step(fid, x, y, p)
        th = math.atan2(y - cy, x - cx); d = th - th0
        while d > math.pi: d -= 2 * math.pi
        while d < -math.pi: d += 2 * math.pi
        total += d; th0 = th
    return abs(total) / (2 * math.pi * n)

windows = [(0.00092,163),(0.00453,148),(0.00552,145),(0.00924,136),(0.01075,133),(0.01241,130),(0.01422,127),(0.01620,124),
           (0.01837,121),(0.02074,118),(0.02334,115),(0.02619,112),(0.02933,109),(0.03280,106),(0.03666,103),(0.04097,100),
           (0.04581,97),(0.05130,94),(0.05755,91)]
print(f"{'mu':>8s} {'period':>6s} {'n':>3s} {'n/(3n+1)':>9s} {'measured':>9s} {'diff':>9s}")
for m, p in windows:
    n = (p - 1) // 3
    rho = rotation_number(fid, np.array([A, m]), 0.13, -0.07, 200_000, 400_000)
    print(f"{m:8.5f} {p:6d} {n:3d} {n/(3*n+1):9.6f} {rho:9.6f} {rho - n/(3*n+1):+9.6f}")
print("\nchaotic attractor between windows (should sit between the neighbouring fractions):")
for m in [0.0070, 0.00845, 0.0100, 0.0200, 0.0300, 0.0500]:
    rho = rotation_number(fid, np.array([A, m]), 0.13, -0.07, 200_000, 2_000_000)
    print(f"  mu={m:.5f}  rho={rho:.6f}   1/3 - rho = {1/3 - rho:+.6f}   implied period 3n+1 = {1/(3*(1/3 - rho)):.1f}")
