"""Turns a cropped photo + mask into art.json for generate.py.

usage: python make_art.py photo.jpg mask.png [out.json]

The photo should already be cropped to roughly 5:6 (width:height). The mask is
a grayscale image of the same size: white = keep, black = background.
Tuning via env vars: BLUR (local-contrast radius), DETAIL (0-1), GAMMA.
"""
import json
import os
import sys

from PIL import Image, ImageChops, ImageFilter, ImageOps

COLS, ROWS = 96, 60
RAMP = " .'`^\",:;Il!i><~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
MIN_GLYPH = 20  # skip the faintest glyphs so every cell carries some ink


def main():
    src, mask_path = sys.argv[1], sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else "art.json"
    blur = float(os.environ.get("BLUR", 40))
    detail = float(os.environ.get("DETAIL", 0.4))
    gamma = float(os.environ.get("GAMMA", 1.0))

    img = Image.open(src).convert("L")
    mask = Image.open(mask_path).convert("L")
    hard_mask = mask.point(lambda v: 255 if v > 128 else 0)

    img = ImageOps.autocontrast(img, cutoff=1, mask=hard_mask)
    local = ImageChops.subtract(img, img.filter(ImageFilter.GaussianBlur(blur)), 0.5, 128)
    img = Image.blend(img, local, detail)
    img = ImageOps.autocontrast(img, cutoff=1, mask=hard_mask)
    img = img.filter(ImageFilter.UnsharpMask(radius=3, percent=120, threshold=2))

    img = img.resize((COLS, ROWS), Image.LANCZOS)
    mask = mask.resize((COLS, ROWS), Image.LANCZOS)

    def glyph(v):
        return RAMP[min(len(RAMP) - 1, MIN_GLYPH + int(v * (len(RAMP) - MIN_GLYPH - 1)))]

    art = {"dark": [], "light": [], "level": []}
    for y in range(ROWS):
        dark = light = level = ""
        for x in range(COLS):
            if mask.getpixel((x, y)) < 110:
                dark += " "; light += " "; level += "0"
                continue
            v = (img.getpixel((x, y)) / 255) ** gamma
            dark += glyph(v)
            light += glyph(1 - v)
            level += str(min(9, int(v * 10)))
        art["dark"].append(dark)
        art["light"].append(light)
        art["level"].append(level)
    with open(out, "w") as f:
        json.dump(art, f)


if __name__ == "__main__":
    main()
