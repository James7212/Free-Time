"""Render a piece at print resolution: 8000 px square, two billion points,
ink on paper. At 300 dpi that is about 27 inches; at 150 dpi, 53.
Usage: python3 print.py shawl [wing ...]"""
import json, sys, time
from render import render

manifest = {p["slug"]: p for p in json.load(open("pieces.json"))}
for slug in sys.argv[1:]:
    p = manifest[slug]; t = time.time()
    img, _ = render(p["family"], p["params"], size=8000, points=2_000_000_000, supersample=1,
                    palette="ink", gamma=0.72, starts=40000 if p.get("cloud") else 1,
                    pad=p.get("pad", 0.06), pct=tuple(p.get("pct", (0.05, 99.95))))
    out = f"print/{slug}-ink-8000.png"
    img.save(out, optimize=True)
    print(out, f"{time.time()-t:.0f}s", flush=True)
