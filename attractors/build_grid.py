"""Make 600px thumbnails of the ink versions and splice a grid into ../README.md."""
import json, os
from PIL import Image
m = json.load(open("pieces.json"))
os.makedirs("thumbs", exist_ok=True)
cells = []
for p in m:
    src = f'pieces/{p["slug"]}-ink.png'
    img = Image.open(src); img.thumbnail((600, 600), Image.LANCZOS); img.save(f'thumbs/{p["slug"]}.png')
    other = [v["name"] for v in p["versions"] if v["name"] != "ink"][0]
    kind = "40,000 paths converging to a cycle" if p.get("transient") else f'chaotic, λ≈{p["lyapunov"]:.2f}'
    cells.append(f'<a href="attractors/pieces/{p["slug"]}-ink.png"><img src="attractors/thumbs/{p["slug"]}.png" width="100%"></a><br>'
                 f'<b>{p["title"]}</b> · <code>{p["family"]}</code> · {kind}<br>'
                 f'<a href="attractors/pieces/{p["slug"]}-ink.png">ink</a> · <a href="attractors/pieces/{p["slug"]}-{other}.png">{other}</a>')
rows = []
for i in range(0, len(cells), 3):
    rows.append("<tr>" + "".join(f'<td width="33%" valign="top" align="center">{c}</td>' for c in cells[i:i+3]) + "</tr>")
grid = "<table>\n" + "\n".join(rows) + "\n</table>"
import re
r = open("../README.md").read()
if "<!-- GRID -->" in r:
    r = r.replace("<!-- GRID -->", grid)
else:
    r = re.sub(r"<table>.*?</table>", grid, r, count=1, flags=re.S)
open("../README.md", "w").write(r)
print("grid built:", len(cells), "pieces")
