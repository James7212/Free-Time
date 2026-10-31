"""
Animate an attractor as one parameter slides. Each frame is a full
render; frames go to ffmpeg. The interesting thing to watch is how the
shape deforms continuously right up until it doesn't.
"""
import argparse, os, subprocess, sys, numpy as np
from render import render

ap = argparse.ArgumentParser()
ap.add_argument("family"); ap.add_argument("--params", required=True)
ap.add_argument("--index", type=int, required=True, help="which parameter to sweep")
ap.add_argument("--delta", type=float, default=0.08, help="half-width of the sweep")
ap.add_argument("--frames", type=int, default=240)
ap.add_argument("--size", type=int, default=800); ap.add_argument("--points", type=int, default=12_000_000)
ap.add_argument("--palette", default="ink"); ap.add_argument("--gamma", type=float, default=0.7)
ap.add_argument("--mode", default="density"); ap.add_argument("--hue", type=float, default=0.0)
ap.add_argument("--range", type=float, default=1.0); ap.add_argument("--sat", type=float, default=0.75)
ap.add_argument("--starts", type=int, default=1)
ap.add_argument("--out", default="morph.mp4"); ap.add_argument("--fps", type=int, default=30)
a = ap.parse_args()

base = [float(v) for v in a.params.split(",")]
tmp = a.out + ".frames"; os.makedirs(tmp, exist_ok=True)
# ease in and out so the ends linger: a full cosine cycle, so it loops
t = np.linspace(0, 2 * np.pi, a.frames, endpoint=False)
offsets = a.delta * np.sin(t)
# fix the frame to the base attractor's bounding box so the picture doesn't jump
import render as R
fid = R.FAM_ID[a.family]
xs, ys = R._bbox(fid, np.asarray(base), 400_000)
x0, x1 = np.percentile(xs, [0.05, 99.95]); y0, y1 = np.percentile(ys, [0.05, 99.95])
cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
half = max(x1 - x0, y1 - y0) / 2 * 1.12
res = a.size * 2
for k, off in enumerate(offsets):
    p = list(base); p[a.index] += off
    H = np.zeros((res, res)); CX = np.zeros((res, res)); CY = np.zeros((res, res))
    if a.starts > 1:
        R._accumulate_cloud(fid, np.asarray(p), a.starts, max(1, a.points // a.starts), 200, 0.5,
                            res, cx - half, cy - half, res / (2 * half), H, CX, CY, 0)
    else:
        R._accumulate(fid, np.asarray(p), a.points, res, cx - half, cy - half, res / (2 * half), H, CX, CY, 0)
    rgb = R.colourise(H, CX, CY, a.palette, a.mode, a.gamma, a.hue, a.sat, a.range)
    R.to_pil(rgb, 2).save(f"{tmp}/{k:04d}.png")
    print(f"frame {k+1}/{a.frames}  p[{a.index}]={p[a.index]:+.4f}", flush=True)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps), "-i", f"{tmp}/%04d.png",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", a.out], check=True)
print("wrote", a.out)
