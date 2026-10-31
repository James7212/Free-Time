"""Render the chosen pieces from pieces.json at exhibition size."""
import json, os, sys, time
from render import render

manifest = json.load(open("pieces.json"))
only = set(sys.argv[1:])
os.makedirs("pieces", exist_ok=True)
for p in manifest:
    if only and p["slug"] not in only:
        continue
    t = time.time()
    cloud = p.get("cloud", False)
    for v in p["versions"]:
        img, _ = render(p["family"], p["params"], size=p.get("size", 2400),
                        points=p.get("points", 200_000_000), supersample=2,
                        palette=v.get("palette", "ember" if v.get("mode") == "silk" else "ink"),
                        mode=v.get("mode", "density"),
                        gamma=v.get("gamma", 0.7), hue_shift=v.get("hue", 0.0),
                        sat=v.get("sat", 0.75), hue_range=v.get("range", 1.0),
                        starts=40000 if cloud else 1, spread=p.get("spread", 0.5),
                        pad=p.get("pad", 0.06), pct=tuple(p.get("pct", (0.05, 99.95))))
        out = f'pieces/{p["slug"]}-{v["name"]}.png'
        img.save(out)
        print(out, f"{time.time()-t:.0f}s", flush=True)
