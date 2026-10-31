"""
apply_narayaneeyam_corrections.py
Post-processing for data/works/narayaneeyam.json after scripts/build_narayaneeyam.py:
re-homes / removes pictures, crops watermarks and captions, swaps in replacement
pictures, restyles the 8.2 table and builds the prologue HTML.

Run from the repo root, once per build (the crops are applied to the freshly built pictures):
    python scripts/build_narayaneeyam.py "<folder of Word files>"
    python scripts/apply_narayaneeyam_corrections.py
"""

import html
import json
import os
import re
import shutil

import cv2
import numpy as np
from PIL import Image

WORK = os.path.join("data", "works", "narayaneeyam.json")
IMG_DIR = os.path.join("images", "pictures", "narayaneeyam")
ASSETS = os.path.join("scripts", "narayaneeyam_assets")

# (verse, 1-based picture position) -> destination verse; the picture leaves its verse and joins the destination
MOVES = [
    ("1.10", 2, "1.8"), ("1.10", 3, "1.9"),
    ("2.1", 2, "1.2"), ("2.1", 3, "1.3"), ("2.1", 4, "1.4"),
    ("2.2", 2, "1.5"), ("2.2", 3, "1.6"),
    ("2.3", 2, "1.7"), ("2.3", 3, "2.7"),
    ("2.4", 2, "2.5"), ("2.4", 3, "2.6"),
    ("2.10", 2, "2.8"), ("2.10", 3, "2.9"),
    ("3.1", 2, "3.3"),
    ("5.1", 1, "5.2"),
    ("6.1", 2, "6.2"),
]
# pictures deleted outright (verse, position); applied before MOVES
CLEAR_VERSE_PICTURES = ["3.3"]
DELETE = [("12.10", 1), ("43.3", 1)]

# (verse, position) -> crop box as fractions (left, top, right, bottom) of the picture
CROPS = {
    ("6.6", 3): (0, 0, 1, 0.925),            # shutterstock bar
    ("6.9", 1): (0, 0, 1, 0.925),
    ("16.5", 1): (0.085, 0.075, 0.912, 0.905),   # caption text + white border
    ("22.11", 1): (0, 0, 1, 0.90),
    ("30.7", 1): (0, 0, 1, 0.90),
    ("39.10", 1): (0, 0, 1, 0.925),
    ("39.10", 2): (0, 0, 1, 0.925),
    ("40.8", 1): (0.115, 0.255, 0.868, 0.94),    # title text + purple border
    ("41.8", 1): (0.012, 0, 1, 0.915),
    ("42.10", 1): (0.07, 0.05, 0.93, 0.88),      # caption + white border
    ("47.5", 1): (0, 0, 1, 0.50),
    ("50.9", 1): (0, 0, 1, 0.81),                # banner under the pair of pictures
}
# watermark painted out in place (verse, position) -> box fractions
INPAINT = {("6.6", 2): (0.62, 0.76, 0.99, 0.99)}

# pictures replaced by a supplied file (verse, position) -> asset
REPLACE = {("51.2", 2): "51.2-clean.webp"}
# pictures added: verse -> asset
ADD = {"5.8": "5.8-table.png"}

BULLET_FROM = "அந்தந்த தசகங்களுக்கு பொருத்தமான விருத்தங்களில்"
BULLET_TO = "இந்த உலகின் பல பிரதேச மன்னர்களை"


def save_webp(im, path):
    im.save(path, "WEBP", quality=85, method=6)


def crop_file(path, box):
    im = Image.open(path)
    w, h = im.size
    l, t, r, b = box
    im.crop((round(l * w), round(t * h), round(r * w), round(b * h))).save(path, "WEBP", quality=85, method=6)


def inpaint_file(path, box):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    mask = np.zeros((h, w), np.uint8)
    l, t, r, b = box
    mask[round(t * h):round(b * h), round(l * w):round(r * w)] = 255
    out = cv2.inpaint(np.array(im)[:, :, ::-1], mask, 9, cv2.INPAINT_TELEA)
    save_webp(Image.fromarray(out[:, :, ::-1]), path)


def intro_html(text):
    paras = [p for p in text.split(chr(10)) if p.strip()]
    start = next(i for i, p in enumerate(paras) if p.startswith(BULLET_FROM))
    end = next(i for i, p in enumerate(paras) if p.startswith(BULLET_TO))
    out = []
    for i, p in enumerate(paras):
        if i == start + 1:
            out.append("<ul>")
        out.append("<li>%s</li>" % html.escape(p, quote=False) if start < i <= end
                   else "<p>%s</p>" % html.escape(p, quote=False))
        if i == end:
            out.append("</ul>")
    return "".join(out)


def main():
    with open(WORK, encoding="utf-8") as f:
        work = json.load(f)
    by = {v["verse_num"]: v for v in work["verses"] if v.get("verse_num")}

    for vn in CLEAR_VERSE_PICTURES:
        by[vn]["images"] = []

    # position-based edits use the picture lists as they stand before any move
    snap = {vn: list(v["images"]) for vn, v in by.items()}
    drop = {}
    incoming = {}
    for vn, pos, dest in MOVES:
        drop.setdefault(vn, set()).add(pos)
        incoming.setdefault(dest, []).append(snap[vn][pos - 1])
    for vn, pos in DELETE:
        drop.setdefault(vn, set()).add(pos)
    for vn in set(drop) | set(incoming):
        kept = [img for i, img in enumerate(snap[vn], 1) if i not in drop.get(vn, ())]
        by[vn]["images"] = kept + incoming.get(vn, [])

    for (vn, pos), box in CROPS.items():
        crop_file(snap[vn][pos - 1], box)
    for (vn, pos), box in INPAINT.items():
        inpaint_file(snap[vn][pos - 1], box)
    for (vn, pos), asset in REPLACE.items():
        save_webp(Image.open(os.path.join(ASSETS, asset)).convert("RGB"), snap[vn][pos - 1])
    for vn, asset in ADD.items():
        name = "d%03d_%s" % (int(vn.split(".")[0]), asset.split("-", 1)[1])
        shutil.copy(os.path.join(ASSETS, asset), os.path.join(IMG_DIR, name))
        by[vn]["images"].append("images/pictures/narayaneeyam/" + name)

    # 5.8: keep the prose only; the table is now a picture
    v = by["5.8"]
    v["meaning"] = v["meaning"].split("<br><br>கேட்டல்")[0]

    # 8.2: second part of the table (from the "Kalpa / CY / M+S" header row) in its own colour
    v = by["8.2"]
    rows = v["meaning"].split("<tr>")
    marker = next(i for i, r in enumerate(rows) if "<td>Kalpa</td>" in r)
    v["meaning"] = rows[0] + "".join(
        ('<tr class="table-part-2">' if i >= marker else "<tr>") + r for i, r in enumerate(rows) if i > 0)

    work["verses"][0]["intro_html"] = intro_html(work["verses"][0]["tamil"])
    work["deities"] = ["vishnu", "krishna"]

    with open(WORK, "w", encoding="utf-8") as f:
        json.dump(work, f, ensure_ascii=False, indent=2)
        f.write(chr(10))


if __name__ == "__main__":
    main()
