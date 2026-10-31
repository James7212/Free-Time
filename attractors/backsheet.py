"""
A sheet for the back of each print: what it is, how it came to be made,
where the whole record lives, and one sonnet from the crown. Letter size
at 300 dpi, as PNG and PDF. Usage: python3 backsheet.py
"""
import re
from PIL import Image, ImageDraw, ImageFont

FONT = "/mnt/skills/examples/canvas-design/canvas-fonts/CrimsonPro-Regular.ttf"
W, H, M = 2550, 3300, 300                      # letter at 300 dpi, 1 inch margins
INK = (40, 36, 38); INK2 = (92, 84, 80)
REPO = "github.com/James7212/Free-Time"
PAIR = ("Hung beside its pair. Both pictures are one point set loose for two billion steps. "
        "In Shawl, two points that start a hair apart drift apart quickly, and the orbit fills "
        "veils. In Wing they drift apart six times more slowly, and the orbit lays down leaves "
        "fine enough to see one by one. They hang together because they are the same thing at "
        "two speeds.")
ORIGIN = ("On the night of 30 to 31 October 2026, a person who had been working for some time "
          "with Claude, an AI, gave it a few hours of computing time and an empty repository and "
          "said: it is yours, do what you want. It went looking for shapes like this one, chose "
          "twelve from two thousand four hundred, and in the same sitting wrote a crown of seven "
          "sonnets about a woman who computed tide tables by hand for a sea she never saw, and "
          "made a minute of sound from the real motions of the moon and sun. The three turned "
          "out to be about the same thing: a loop that never repeats and always returns. The "
          "whole of it, including the code that makes this exact picture, the journal kept while "
          "making it, and the drafts of the poem, is kept at " + REPO + ", release free-time-01.")

SHEETS = {
    "shawl": dict(
        title="Shawl",
        lines=["Clifford attractor · a = −1.23644, b = −2.76143, c = −1.12015, d = −0.25936",
               "x′ = sin(a·y) + c·cos(a·x)        y′ = sin(b·x) + d·cos(b·y)",
               "Pigment print on cotton rag · 30 × 30 in · one of a pair with Wing",
               "Made by Claude, an AI · 31 October 2026"],
        what=("This picture was not drawn. Take a point on the page, apply the formula above to it, "
              "and mark where it lands. Do that two billion times. The darkness is where the point "
              "kept returning; the veils are where it rarely went. Change the fourth decimal of any "
              "of the four numbers and you get a different picture. These four were found by a random "
              "search and chosen by eye."),
        sonnet="VI",
    ),
    "wing": dict(
        title="Wing",
        lines=["Gumowski–Mira map · a = −0.49308, μ = 0.00845",
               "x′ = y + μ·(1 − 0.05·y²)·y + f(x)        y′ = −x + f(x′)        f(v) = a·v + 2·(1 − a)·v² / (1 + v²)",
               "Pigment print on cotton rag · 30 × 30 in · one of a pair with Shawl",
               "Made by Claude, an AI · 31 October 2026"],
        what=("This picture was not drawn. Take a point on the page, apply the formula above to it, "
              "and mark where it lands. Do that two billion times. The lines are not separate paths: "
              "one point, left to run, visits every feather and every line within it. The layering is "
              "the shape's own fine structure, which it has because this formula stretches slowly and "
              "folds often. The two numbers were found by a random search and chosen by eye."),
        sonnet="I",
    ),
}


def sonnet(numeral):
    text = open("../writing/crown-for-a-computer.md").read()
    m = re.search(r"^## " + numeral + r"\n\n(.*?)\n\n(?=## |---)", text, re.S | re.M)
    return m.group(1).splitlines()


def wrap(d, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= width: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines


def make(slug):
    s = SHEETS[slug]
    img = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(img)
    f_title = ImageFont.truetype(FONT, 104); f_small = ImageFont.truetype(FONT, 42)
    f_body = ImageFont.truetype(FONT, 46); f_head = ImageFont.truetype(FONT, 54)
    f_verse = ImageFont.truetype(FONT, 46)
    y = M
    d.text((M, y), s["title"], font=f_title, fill=INK); y += 140
    for l in s["lines"]:
        d.text((M, y), l, font=f_small, fill=INK2); y += 54
    y += 36
    d.line([(M, y), (W - M, y)], fill=(200, 196, 190), width=2); y += 48

    def para(head, text, gap=48):
        nonlocal y
        if head:
            d.text((M, y), head, font=f_head, fill=INK); y += 74
        for l in wrap(d, text, f_body, W - 2 * M):
            d.text((M, y), l, font=f_body, fill=INK); y += 62
        y += gap

    para("What it is", s["what"])
    para(None, PAIR)
    para("How it came to be made", ORIGIN)
    d.text((M, y), "From the crown of sonnets written in the same sitting, Crown for a Computer, " + s["sonnet"],
           font=f_head, fill=INK); y += 84
    for l in sonnet(s["sonnet"]):
        d.text((M + 60, y), l, font=f_verse, fill=INK); y += 60
    assert y < H - M, f"overflow: {y}"
    img.save(f"print/{slug}-back-sheet.png", optimize=True)
    img.save(f"print/{slug}-back-sheet.pdf", resolution=300.0)
    img.resize((850, 1100), Image.LANCZOS).save(f"/tmp/{slug}-back-proof.png")
    print(slug, "sheet done; bottom at", y, "of", H - M)


if __name__ == "__main__":
    for slug in SHEETS:
        make(slug)
