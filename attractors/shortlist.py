"""Render a shortlist of candidate ids from the search log at medium size
and tile them 2x2 so they can be judged properly."""
import json, sys, os
from PIL import Image
from render import render

ids = sys.argv[1:]
import glob
log = {}
for f in glob.glob("candidates/log-*.json"):
    log.update({s["id"]: s for s in json.load(open(f))})
os.makedirs("shortlist", exist_ok=True)
tiles = []
for i in ids:
    s = log[i]
    cloud = s["lyapunov"] < 0.1   # quasi-periodic: draw the whole family of curves
    img, _ = render(s["family"], s["params"], size=900, points=30_000_000, supersample=2,
                    palette="ink", gamma=0.7, starts=20000 if cloud else 1)
    img.save(f"shortlist/{i}.png")
    tiles.append((i, img))
    print(i, s["family"], s["params"], f'L={s["lyapunov"]:.2f}', flush=True)
# 2x2 sheets
for k in range(0, len(tiles), 4):
    grp = tiles[k:k+4]
    sheet = Image.new("RGB", (1800, 1800), (246, 242, 232))
    for j, (i, img) in enumerate(grp):
        sheet.paste(img, ((j % 2) * 900, (j // 2) * 900))
    sheet.save(f"shortlist/sheet-{k//4:02d}.png")
    print("sheet", k//4, [i for i, _ in grp])
