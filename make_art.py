"""Turns a cropped photo + mask into art.json for generate.py.

usage: python make_art.py photo.jpg mask.png [out.json]

The photo should be cropped to the person; a 5:6 (width:height) crop fills the
art area, narrower or wider crops are centred. The mask is a grayscale image
of the same size: white = keep, black = background.
Tuning via env vars: BLUR (local-contrast radius), DETAIL (0-1), GAMMA,
CONTRAST (1 = unchanged), ERODE (px to shrink the mask by, for photos with a
bright background).
"""
import json
import os
import sys

from PIL import Image, ImageChops, ImageFilter, ImageOps

MAX_COLS, MAX_ROWS = 96, 60
CELL_ASPECT = (400 / 96) / 8  # glyph cell width / line height in the SVG
RAMP = " .'`^\",:;Il!i><~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
MIN_GLYPH = 20  # skip the faintest glyphs so every cell carries some ink


def main():
    src, mask_path = sys.argv[1], sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else "art.json"
    blur = float(os.environ.get("BLUR", 40))
    detail = float(os.environ.get("DETAIL", 0.4))
    gamma = float(os.environ.get("GAMMA", 1.0))
    contrast = float(os.environ.get("CONTRAST", 1.0))

    img = Image.open(src).convert("L")
    mask = Image.open(mask_path).convert("L")
    # Shrink the mask so bright background at its edges doesn't skew the contrast.
    erode = int(os.environ.get("ERODE", 0)) | 1
    if erode > 1:
        mask = mask.filter(ImageFilter.MinFilter(erode))
    hard_mask = mask.point(lambda v: 255 if v > 128 else 0)

    img = ImageOps.autocontrast(img, cutoff=1, mask=hard_mask)
    local = ImageChops.subtract(img, img.filter(ImageFilter.GaussianBlur(blur)), 0.5, 128)
    img = Image.blend(img, local, detail)
    img = ImageOps.autocontrast(img, cutoff=1, mask=hard_mask)
    img = img.point(lambda v: max(0, min(255, round(128 + (v - 128) * contrast))))
    img = img.filter(ImageFilter.UnsharpMask(radius=3, percent=120, threshold=2))

    # Fill the art area in whichever direction the crop hits first.
    cols = min(MAX_COLS, round(MAX_ROWS * img.width / img.height / CELL_ASPECT))
    rows = min(MAX_ROWS, round(MAX_COLS * img.height / img.width * CELL_ASPECT))
    img = img.resize((cols, rows), Image.LANCZOS)
    mask = mask.resize((cols, rows), Image.LANCZOS)

    def glyph(v):
        return RAMP[min(len(RAMP) - 1, MIN_GLYPH + int(v * (len(RAMP) - MIN_GLYPH - 1)))]

    art = {"dark": [], "light": [], "level": []}
    for y in range(rows):
        dark = light = level = ""
        for x in range(cols):
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
