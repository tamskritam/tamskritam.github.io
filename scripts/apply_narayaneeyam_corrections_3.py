"""
apply_narayaneeyam_corrections_3.py
Third batch of corrections for data/works/narayaneeyam.json. Run after the first two:

    python scripts/build_narayaneeyam.py "<folder of Word files>"
    python scripts/apply_narayaneeyam_corrections.py
    python scripts/apply_narayaneeyam_corrections_2.py
    python scripts/apply_narayaneeyam_corrections_3.py

Picture positions are 1-based and refer to each verse's list as it stands after batch 2.
"""

import json
import os
import re

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from apply_narayaneeyam_corrections_2 import ASSETS, IMG_DIR, REL, WORK, crop, inpaint, save_webp

# pictures replaced by a supplied file: (verse, position) -> (asset, new name)
REPLACE = {
    ("23.3", 2): ("b3_23.3.jpeg", "d023_3b.webp"),
    ("24.6", 2): ("b3_24.6.jpeg", "d024_6b.webp"),
    ("30.1", 2): ("b3_30.1.jpeg", "d030_1b.webp"),
    ("49.9", 1): ("b3_49.9.jpeg", "d049_9b.webp"),
    ("77.11", 1): ("b3_77.11.jpeg", "d077_11b.webp"),
    ("81.10", 2): ("b3_81.10.jpeg", "d081_10b.webp"),
    ("100.11", 1): ("b3_100.11.jpeg", "d100_11b.webp"),
}

CROPS = {
    ("20.5", 1): (0, 0, 1, 0.975),
    ("33.3", 1): (0, 0, 1, 0.925),
    ("43.1", 2): (0.175, 0, 0.83, 1),
    ("92.9", 2): (0, 0, 0.915, 1),
}

# lettering painted out ("white" = pale lettering)
INPAINT = {
    ("34.3", 3): [("white", (0.03, 0.02, 0.70, 0.14)), ("white", (0.86, 0.33, 0.96, 0.82))],
}

# speech bubbles filled with the colour around them: (verse, position) -> (region, seed, flat colour point or None)
BUBBLES = {
    ("31.10", 1): ((0, 0, 0.50, 0.46), (0.10, 0.10), (0.04, 0.47)),
    ("38.8", 2): ((0, 0, 0.58, 0.22), (0.20, 0.05), None),
    ("39.3", 1): ((0, 0, 0.74, 0.20), (0.40, 0.03), None),
    ("39.3", 2): ((0.30, 0, 0.72, 0.20), (0.52, 0.03), None),
}

# artist names written on a picture: (verse, position) -> (text, fill, outline)
SIGNATURES = {
    ("100.11", 2): ("Haripriya", (255, 248, 225), (60, 30, 10)),
    ("93.10", 2): ("Raji Suresh", (70, 40, 20), (255, 255, 255)),
}
FONT = r"C:\Windows\Fonts\BRUSHSCI.TTF"


def fill_bubble(path, region, seed, flat_pt):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    arr = np.array(im)
    l, t, r, b = region
    x0, y0, x1, y1 = round(l * w), round(t * h), round(r * w), round(b * h)
    sat = np.array(im.convert("HSV"))[:, :, 1]
    white = ((arr.min(axis=2) > 195) & (sat < 45)).astype(np.uint8)
    limit = np.zeros_like(white)
    limit[y0:y1, x0:x1] = 1
    white &= limit
    n, labels = cv2.connectedComponents(white, connectivity=4)
    sx, sy = round(seed[0] * w), round(seed[1] * h)
    lab = labels[sy, sx]
    if lab == 0:
        raise ValueError("bubble seed %s is not on white in %s" % (seed, path))
    comp = (labels == lab).astype(np.uint8) * 255
    contours, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(comp)
    cv2.drawContours(filled, contours, -1, 255, thickness=cv2.FILLED)
    mask = cv2.dilate(filled, np.ones((9, 9), np.uint8))
    if flat_pt:
        colour = np.median(arr[round(flat_pt[1] * h) - 6:round(flat_pt[1] * h) + 6,
                               round(flat_pt[0] * w) - 6:round(flat_pt[0] * w) + 6].reshape(-1, 3), axis=0)
        arr[mask > 0] = colour.astype(np.uint8)
        out = arr
    else:
        out = cv2.inpaint(arr[:, :, ::-1], mask, 9, cv2.INPAINT_TELEA)[:, :, ::-1]
    save_webp(Image.fromarray(out), path)


def sign(path, text, fill, outline):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    font = ImageFont.truetype(FONT, max(18, round(h * 0.07)))
    d = ImageDraw.Draw(im)
    bbox = d.textbbox((0, 0), text, font=font, stroke_width=2)
    x, y = w - (bbox[2] - bbox[0]) - round(w * 0.035), h - (bbox[3] - bbox[1]) - round(h * 0.045)
    d.text((x, y), text, font=font, fill=fill, stroke_width=2, stroke_fill=outline)
    save_webp(im, path)


def main():
    with open(WORK, encoding="utf-8") as f:
        work = json.load(f)
    by = {v["verse_num"]: v for v in work["verses"] if v.get("verse_num")}
    warnings = []
    snap = {vn: list(v["images"]) for vn, v in by.items()}

    # ---- 8.2 table
    m = by["8.2"]["meaning"]
    m = m.replace("<tr><td>Let", '<tr class="table-head-row"><td>Let', 1)
    m = re.sub(r'<tr class="table-part-2">(?=<td></td><td>Kalpa</td>)', '<tr class="table-part-2 table-head-row">', m, count=1)
    m = m.replace("<td>71 CY</td><td>1 M+S</td>", "<td>71 CY</td><td>1 M</td>", 1)
    m = m.replace("<td>0.4 CY</td><td></td>", "<td>0.4 CY</td><td>1 S</td>", 1)
    by["8.2"]["meaning"] = m
    for needle in ('table-head-row"><td>Let', "<td>1 M</td>", "<td>1 S</td>", "table-part-2 table-head-row"):
        if needle not in m:
            warnings.append("8.2: %s not applied" % needle)

    # ---- single-paragraph prose
    for vn in ("19.4", "19.7", "24.2", "93.2", "100.9"):
        t = re.sub(r"(?:\s|<br>)+", " ", by[vn]["meaning"]).strip()
        by[vn]["meaning"] = t

    # ---- 39.6: the sloka lines in their own colour, the heading underlined
    t = by["39.6"]["meaning"]
    i = t.index("भागवतश्लोकः")
    j = t.index("<br>மனிதர்கள்")
    seg = t[i:j].replace("भागवतश्लोकः", "<u>भागवतश्लोकः</u>", 1)
    by["39.6"]["meaning"] = t[:i] + '<span class="meaning-accent">' + seg + "</span>" + t[j:]

    # ---- pictures
    for (vn, pos), (asset, name) in REPLACE.items():
        im = Image.open(os.path.join(ASSETS, asset)).convert("RGB")
        im.thumbnail((1000, 1000))
        save_webp(im, os.path.join(IMG_DIR, name))
        snap[vn][pos - 1] = REL + name
        by[vn]["images"] = list(snap[vn])
    for (vn, pos), specs in INPAINT.items():
        inpaint(snap[vn][pos - 1], specs)
    for (vn, pos), (region, seed, flat) in BUBBLES.items():
        try:
            fill_bubble(snap[vn][pos - 1], region, seed, flat)
        except ValueError as e:
            warnings.append(str(e))
    for (vn, pos), box in CROPS.items():
        crop(snap[vn][pos - 1], box)
    for (vn, pos), (text, fill, outline) in SIGNATURES.items():
        sign(snap[vn][pos - 1], text, fill, outline)

    with open(WORK, "w", encoding="utf-8") as f:
        json.dump(work, f, ensure_ascii=False, indent=2)
        f.write(chr(10))
    for w in warnings:
        print("WARN", w)


if __name__ == "__main__":
    main()
