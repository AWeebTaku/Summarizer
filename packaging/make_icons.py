"""Generate the app icon in every format the installers need. Run: python packaging/make_icons.py (needs Pillow)."""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).parent / "icons"
S = 2048  # draw big, then shrink for smooth edges


def draw() -> Image.Image:
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, S - 1, S - 1), radius=int(S * .225), fill=(6, 8, 14, 255))
    d.rounded_rectangle((8, 8, S - 9, S - 9), radius=int(S * .22), outline=(43, 55, 96, 255), width=12)
    x0, line = int(S * .2), int(S * .07)
    rows = [  # (centre y, width, colour): two ordinary lines and one highlighted sentence
        (.32, .58, (74, 80, 102, 255)),
        (.50, .60, (255, 255, 255, 255)),
        (.68, .42, (74, 80, 102, 255)),
    ]
    for cy, w, col in rows:
        y = int(S * cy)
        if col[0] == 255:  # the highlight: a blue band behind the bright line
            pad = int(S * .05)
            d.rounded_rectangle((x0 - pad, y - line - pad, x0 + int(S * w) + pad, y + line + pad), radius=int(S * .045), fill=(43, 103, 240, 255))
        d.rounded_rectangle((x0, y - line // 2, x0 + int(S * w), y + line // 2), radius=line // 2, fill=col)
    return im


def main():
    OUT.mkdir(exist_ok=True)
    big = draw()
    sizes = [16, 32, 48, 64, 128, 256, 512]
    for s in sizes:
        big.resize((s, s), Image.LANCZOS).save(OUT / f"{s}.png")
    big.resize((1024, 1024), Image.LANCZOS).save(OUT / "1024.png")
    big.save(OUT / "icon.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    big.resize((1024, 1024), Image.LANCZOS).save(OUT / "icon.icns")
    print("wrote", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
