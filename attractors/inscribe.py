"""
Inscribe a print file: the title, the formula and its exact numbers, a few
words, and who made it, typeset into an empty region of the picture so
that every copy carries its own recipe.

Usage: python3 inscribe.py shawl [wing ...]
"""
import sys
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = None

FONT = "/mnt/skills/examples/canvas-design/canvas-fonts/CrimsonPro-Regular.ttf"
INK_TITLE = (46, 42, 44)
INK_BODY = (82, 74, 70)

MADE = ("Made by Claude, an AI, on 31 October 2026, in a few hours it was given",
        "with no instructions except to do what it wanted.")

INSCRIPTIONS = {
    "shawl": dict(
        title="Shawl",
        formula=["x′ = sin(a·y) + c·cos(a·x)",
                 "y′ = sin(b·x) + d·cos(b·y)",
                 "a = −1.23644      b = −2.76143      c = −1.12015      d = −0.25936"],
        words=["Two billion iterations. Nobody drew this: take a point, apply the formula,",
               "mark where it lands, and repeat. The dark is where the point kept returning.",
               "The veils are where it rarely went."],
        anchor=(820, 7240),          # left edge, bottom edge of the block
    ),
    "wing": dict(
        title="Wing",
        formula=["x′ = y + μ·(1 − 0.05·y²)·y + f(x)        y′ = −x + f(x′)",
                 "f(v) = a·v + 2·(1 − a)·v² / (1 + v²)",
                 "a = −0.49308      μ = 0.00845"],
        words=["Forty thousand orbits of fifty thousand steps, each from a different",
               "starting point. Every line is a separate orbit; none ever touches the one",
               "beside it. Nobody drew this."],
        anchor=(820, 7240),
    ),
}


def inscribe(slug, size_title=112, size_body=58, leading=1.42):
    spec = INSCRIPTIONS[slug]
    img = Image.open(f"print/{slug}-ink-8000.png").convert("RGB")
    d = ImageDraw.Draw(img)
    f_title = ImageFont.truetype(FONT, size_title)
    f_body = ImageFont.truetype(FONT, size_body)
    gap = int(size_body * 0.9)
    lh = int(size_body * leading)

    # Build the block top-down, then shift so its bottom sits on the anchor.
    rows = [("title", spec["title"])]
    rows += [("gap", None)] + [("body", l) for l in spec["formula"]]
    rows += [("gap", None)] + [("body", l) for l in spec["words"]]
    rows += [("gap", None)] + [("body", l) for l in MADE]
    height = 0
    for kind, _ in rows:
        height += {"title": int(size_title * 1.25), "gap": gap, "body": lh}[kind]
    x, y_bottom = spec["anchor"]
    y = y_bottom - height
    for kind, text in rows:
        if kind == "title":
            d.text((x, y), text, font=f_title, fill=INK_TITLE); y += int(size_title * 1.25)
        elif kind == "gap":
            y += gap
        else:
            d.text((x, y), text, font=f_body, fill=INK_BODY); y += lh
    out = f"print/{slug}-ink-8000-inscribed.png"
    img.save(out, optimize=True)
    print("wrote", out, "block top at", y_bottom - height, flush=True)
    return img


if __name__ == "__main__":
    for slug in sys.argv[1:]:
        img = inscribe(slug)
        img.resize((1600, 1600), Image.LANCZOS).save(f"/tmp/{slug}-inscribed-proof.png")
        img.crop((600, 5900, 3800, 7400)).resize((1600, 750), Image.LANCZOS).save(f"/tmp/{slug}-inscription-crop.png")
