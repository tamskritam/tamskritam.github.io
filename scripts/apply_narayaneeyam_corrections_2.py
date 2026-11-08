"""
apply_narayaneeyam_corrections_2.py
Second batch of corrections for data/works/narayaneeyam.json. Run after
scripts/build_narayaneeyam.py and scripts/apply_narayaneeyam_corrections.py:

    python scripts/build_narayaneeyam.py "<folder of Word files>"
    python scripts/apply_narayaneeyam_corrections.py
    python scripts/apply_narayaneeyam_corrections_2.py

Picture positions below are 1-based and refer to the verse's picture list as it stands after the first batch.
"""

import html
import json
import os
import re

import cv2
import numpy as np
from PIL import Image, ImageFilter

WORK = os.path.join("data", "works", "narayaneeyam.json")
IMG_DIR = os.path.join("images", "pictures", "narayaneeyam")
ASSETS = os.path.join("scripts", "narayaneeyam_assets")
REL = "images/pictures/narayaneeyam/"

# ---------------------------------------------------------------- pictures
DELETE = [("23.6", 2), ("26.9", 1), ("28.5", 1)] + [("70.1", i) for i in range(1, 6)]

# (verse, position) -> new picture file from scripts/narayaneeyam_assets (stored under a new name)
REPLACE = {("24.6", 2): ("24.6-new.png", "d024_6new.webp")}
# pictures appended to a verse: verse -> (asset, new name)
ADD = {"88.12": ("88.12-love.jpeg", "d088_love.webp")}

# crop boxes as fractions (left, top, right, bottom)
CROPS = {
    ("19.6", 1): (0.0, 0.0, 1, 0.865),
    ("24.2", 1): (0.01, 0.005, 0.995, 0.855),
    ("30.1", 2): (0.02, 0.01, 0.98, 0.925),
    ("36.2", 1): (0, 0, 1, 0.915),
    ("38.5", 2): (0, 0, 1, 0.925),
    ("38.8", 1): (0, 0, 1, 0.925),
    ("41.6", 1): (0, 0, 1, 0.905),
    ("43.1", 1): (0.10, 0.095, 0.90, 0.905),
    ("70.1", 11): (0, 0.19, 1, 1),
    ("77.1", 1): (0.235, 0.205, 0.95, 0.90),
    ("77.11", 1): (0, 0, 1, 0.895),
    ("86.8", 1): (0.01, 0, 0.995, 0.875),
    ("92.4", 1): (0, 0.215, 1, 1),
    ("92.9", 1): (0, 0, 0.975, 1),
    ("93.6", 1): (0, 0, 1, 0.90),
    ("93.9", 1): (0, 0, 1, 0.915),
    ("96.10", 1): (0, 0, 1, 0.895),
    ("97.7", 1): (0, 0, 1, 0.70),
    ("97.7", 2): (0, 0, 1, 0.92),
    ("99.4", 1): (0, 0.285, 1, 0.785),
    ("99.8", 1): (0, 0.24, 1, 0.935),
    ("99.9", 1): (0, 0.275, 1, 0.565),
}
# 81.10: remove the guru photo first (inpaint), then crop to Krishna and Radha
PRE_INPAINT = {("81.10", 1): [("box", (0.0, 0.03, 0.23, 0.47))]}
CROPS[("81.10", 1)] = (0.12, 0, 0.72, 1)

# words painted out in place: (verse, position) -> list of (mode, box)
#   dark  - dark strokes inside the box (speech-bubble lettering)
#   light - near-white strokes inside the box
#   yellow - yellow lettering inside the box
#   box   - everything in the box
INPAINT = {
    ("20.5", 1): [("box", (0.33, 0.90, 0.63, 0.935))],
    ("19.6", 1): [("box", (0.0, 0.76, 0.17, 0.866))],
    ("31.5", 1): [("dark", (0.14, 0, 0.49, 0.08))],
    ("31.9", 1): [("dark", (0, 0, 0.265, 0.075))],
    ("31.10", 1): [("dark", (0, 0, 0.452, 0.37)), ("dark", (0, 0.37, 0.222, 0.425))],
    ("34.7", 3): [("dark", (0, 0, 0.50, 0.15))],
    ("38.8", 2): [("dark", (0.09, 0, 0.44, 0.08)), ("dark", (0.80, 0.86, 0.97, 0.95))],
    ("39.3", 1): [("dark", (0.12, 0, 0.45, 0.075))],
    ("39.3", 2): [("dark", (0.30, 0, 0.58, 0.115))],
    ("92.9", 1): [("box", (0.05, 0.45, 0.32, 0.55))],
    ("93.5", 1): [("patch", (0.135, 0.825, 0.875, 0.965)), ("box", (0.925, 0.02, 0.99, 0.10))],
    ("96.8", 1): [("yellow", (0.05, 0.78, 0.95, 0.96)), ("box", (0.0, 0.0, 0.09, 0.13)),
                  ("box", (0.92, 0.0, 1.0, 0.17)), ("box", (0.92, 0.88, 1.0, 1.0))],
    ("98.4", 1): [("box", (0.28, 0.82, 0.72, 0.945))],
    ("30.1", 2): [("bg", b) for b in [
        (0.03, 0.04, 0.34, 0.20), (0.26, 0.17, 0.36, 0.24), (0.05, 0.36, 0.15, 0.42), (0.66, 0.24, 0.97, 0.40),
        (0.62, 0.55, 0.74, 0.60), (0.68, 0.57, 0.95, 0.73), (0.08, 0.64, 0.32, 0.77), (0.60, 0.86, 0.86, 0.97),
        (0.80, 0.08, 0.88, 0.13), (0.80, 0.44, 0.88, 0.50), (0.00, 0.55, 0.04, 0.60), (0.80, 0.77, 0.88, 0.81)]],
}

# pictures upscaled for clarity: (verse, position)
UPSCALE = [("23.3", 2)]
# white margins trimmed after cropping
TRIM = [("19.6", 1)]

CAPTIONS = {
    "20.4": ["", "Statue of Nabhi & Meru Devi"],
    "88.12": ["Affection", "Fear", "Hatred", "Friendship", "Love"],
}


def save_webp(im, path):
    im.save(path, "WEBP", quality=88, method=6)


def inpaint(path, specs):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    arr = np.array(im)
    sat = np.array(im.convert("HSV"))[:, :, 1]
    mask = np.zeros((h, w), np.uint8)
    for mode, (l, t, r, b) in specs:
        x0, y0, x1, y1 = round(l * w), round(t * h), round(r * w), round(b * h)
        if mode == "patch":
            # cover the box with the strip directly above it, flipped, feathered at the edges
            bh = y1 - y0
            src = arr[max(0, y0 - bh):y0, x0:x1][::-1]
            if src.shape[0] < bh:
                src = np.pad(src, ((0, bh - src.shape[0]), (0, 0), (0, 0)), mode="edge")
            alpha = np.ones((bh, x1 - x0), np.float32)
            feather = max(2, bh // 5)
            for k in range(feather):
                f = (k + 1) / (feather + 1)
                alpha[k, :] = np.minimum(alpha[k, :], f)
                alpha[bh - 1 - k, :] = np.minimum(alpha[bh - 1 - k, :], f)
                alpha[:, k] = np.minimum(alpha[:, k], f)
                alpha[:, x1 - x0 - 1 - k] = np.minimum(alpha[:, x1 - x0 - 1 - k], f)
            dst = arr[y0:y1, x0:x1].astype(np.float32)
            arr[y0:y1, x0:x1] = (dst * (1 - alpha[..., None]) + src.astype(np.float32) * alpha[..., None]).astype(np.uint8)
            continue
        region = arr[y0:y1, x0:x1].astype(int)
        if mode == "box":
            m = np.full(region.shape[:2], 255, np.uint8)
        elif mode == "dark":
            m = (region.mean(axis=2) < 110).astype(np.uint8) * 255
        elif mode == "light":
            m = (region.mean(axis=2) > 225).astype(np.uint8) * 255
        elif mode == "bg":
            # pale grey lettering on the plain background, leaving anything near the drawing alone
            gray = arr.astype(int).mean(axis=2)
            fig = cv2.dilate(((sat >= 45) | (gray < 150)).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
            m = ((sat[y0:y1, x0:x1] < 45) & (gray[y0:y1, x0:x1] > 150) & ~fig[y0:y1, x0:x1]).astype(np.uint8) * 255
        elif mode == "white":
            m = ((sat[y0:y1, x0:x1] < 28) & (region.min(axis=2) > 222)).astype(np.uint8) * 255
        elif mode == "yellow":
            m = ((region[:, :, 0] > 190) & (region[:, :, 1] > 150) & (region[:, :, 2] < 120)).astype(np.uint8) * 255
        else:
            raise ValueError(mode)
        if mode != "box":
            m = cv2.dilate(m, np.ones(({"dark": 3, "white": 9}.get(mode, 5),) * 2, np.uint8))
        mask[y0:y1, x0:x1] |= m
    out = cv2.inpaint(arr[:, :, ::-1], mask, 5, cv2.INPAINT_TELEA)
    save_webp(Image.fromarray(out[:, :, ::-1]), path)


def trim_white(path, thresh=240, frac=0.4, run=6):
    """Trim white margins; a margin ends where `run` consecutive rows/columns are mostly picture."""
    im = Image.open(path).convert("RGB")
    a = np.array(im).min(axis=2) < thresh

    def span(q):
        ok = np.convolve(q.astype(int), np.ones(run, int), "valid") == run
        idx = np.where(ok)[0]
        return idx[0], idx[-1] + run

    c0, c1 = span(a.mean(axis=0) > frac)
    r0, r1 = span(a.mean(axis=1) > frac)
    save_webp(im.crop((c0, r0, c1, r1)), path)


def crop(path, box):
    im = Image.open(path)
    w, h = im.size
    l, t, r, b = box
    save_webp(im.crop((round(l * w), round(t * h), round(r * w), round(b * h))), path)


def upscale(path):
    im = Image.open(path).convert("RGB")
    im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.6, percent=90, threshold=2))
    save_webp(im, path)


# ---------------------------------------------------------------- text
def esc(s):
    return html.escape(s, quote=False)


def word_pat(word):
    word = esc(word)
    trail = ""
    if word and word[-1] in ",.":
        word, trail = word[:-1], word[-1] + "?"
    return r"\s+".join(re.escape(p) for p in word.split()) + trail


def join_words(meaning, a, b):
    new, n = re.subn("(" + word_pat(a) + r")(?:\s|<br>)+(" + word_pat(b) + ")", lambda m: m.group(1) + " " + m.group(2), meaning, count=1)
    return new if n else None


def main():
    with open(WORK, encoding="utf-8") as f:
        work = json.load(f)
    by = {v["verse_num"]: v for v in work["verses"] if v.get("verse_num")}
    warnings = []

    # ---- 8.2 table: alternate rows of the second part, tidy the note
    v = by["8.2"]
    cnt = [0]

    def alt(m):
        cnt[0] += 1
        return '<tr class="table-part-2 row-plain">' if cnt[0] % 2 == 0 else m.group(0)
    v["meaning"] = re.sub(r'<tr class="table-part-2">', alt, v["meaning"])
    # first part of that sub-table (header row) keeps the existing colour: the header is cnt 0 and plain starts after it
    v["meaning"] = v["meaning"].replace("</div><br><br>Note:<br><br>", "</div><br><br>Note:<br>")
    head, _, note = v["meaning"].partition("Note:<br>")
    v["meaning"] = head + "Note:<br>" + note.replace("<br><br>", "<br>")

    # ---- prose fixes
    by["18.8"]["meaning"] = re.sub(r"(?<![஀-௿])ோற்கடிக்கப்பட்ட", "தோற்கடிக்கப்பட்ட", by["18.8"]["meaning"], count=1)
    by["30.6"]["meaning"] = by["30.6"]["meaning"].replace("அஐக்ஷ", "அக்ஷ")
    by["24.7"]["meaning"] = re.sub(r"^\.(?:<br>)+(?=எங்கும்)", "", by["24.7"]["meaning"])
    by["81.10"]["meaning"] = re.sub(r"(?:<br>)*p\s*शुभम्\s*$", "", by["81.10"]["meaning"])
    by["93.10"]["meaning"] = re.sub(r"(?:Raji Suresh\s*(?:<br>)*)+", "", by["93.10"]["meaning"])
    by["20.4"]["meaning"] = by["20.4"]["meaning"].replace("Statue of Nabhi &amp; Meru Devi<br><br>", "")

    # 23.6: the two lead-ins in their own colour
    m = by["23.6"]["meaning"]
    for lead in ("(நாரதர் உபதேசித்த ஸ்தோத்ரம்:", "(நாரதர் உபதேசித்த மந்திரம்:"):
        m = m.replace(lead, '<span class="meaning-accent">%s</span>' % lead)
    by["23.6"]["meaning"] = m

    # 59.3: heading underlined, the song in its own colour
    m = by["59.3"]["meaning"]
    m, n = re.subn(r"புலனெல்லாம் கண்ணன்(.*?மெய்யே !)",
                   lambda x: '<span class="meaning-accent"><u>புலனெல்லாம் கண்ணன்</u>%s</span>' % x.group(1), m, count=1, flags=re.S)
    if not n:
        warnings.append("59.3: song not found")
    by["59.3"]["meaning"] = m

    # 88.12: drop the word table and the stray "Love"
    by["88.12"]["meaning"] = re.sub(r'<br><br><div class="analysis-table-container">.*$', "", by["88.12"]["meaning"], flags=re.S)

    # 39.6: main verse shows the Yogamaya poem; the other poem moves under the Bhagavata sloka meaning
    v = by["39.6"]
    mean = v["meaning"]
    i1 = mean.index("யோகமாயா அரக்கனிடம்")
    i2 = mean.index("<br><br>भागवतश्लोकः")
    yoga_poem = mean[i1:i2].split("<br>")
    rest = re.sub(r"(?:<br>)+$", "", mean[:i1]) + mean[i2:]
    poem_old = v["tamil"].split("\n")
    v["tamil"] = "\n".join(l.strip() for l in yoga_poem if l.strip())
    verse_html = '<div class="meaning-verse">%s</div>' % "".join(
        '<span class="meaning-verse-line">%s</span>' % esc(l.strip()) for l in poem_old if l.strip())
    v["meaning"] = rest + "<br><br>" + verse_html

    # ---- joined words (verse numbers in the notes are sometimes off by one: fall back to the same dasakam)
    with open(os.path.join(ASSETS, "text_joins.json"), encoding="utf-8") as f:
        joins = json.load(f)
    joins.append(["22.7", "<", "ஹே!"])     # listed as 21.1 in the notes; the text is in 22.7
    for vn, a, b in joins:
        order = [vn] + [k for k in by if k.split(".")[0] == vn.split(".")[0] and k != vn]
        for k in order:
            new = join_words(by[k]["meaning"], a, b)
            if new is not None:
                by[k]["meaning"] = new
                if k != vn:
                    warnings.append("%s %s/%s: found in %s" % (vn, a, b, k))
                break
        else:
            warnings.append("not found: %s %s %s" % (vn, a, b))

    # ---- pictures
    snap = {vn: list(v["images"]) for vn, v in by.items()}

    def shared(path):
        return sum(1 for vv in by.values() if path in vv["images"])

    for key, specs in PRE_INPAINT.items():
        inpaint(snap[key[0]][key[1] - 1], specs)
    for key, specs in INPAINT.items():
        inpaint(snap[key[0]][key[1] - 1], specs)
    for (vn, pos), box in CROPS.items():
        p = snap[vn][pos - 1]
        if len({vv["verse_num"] for vv in by.values() if p in vv["images"]}) > 1:
            warnings.append("shared picture cropped: %s #%d %s" % (vn, pos, p))
        crop(p, box)
    for key in TRIM:
        trim_white(snap[key[0]][key[1] - 1])
    for key in UPSCALE:
        upscale(snap[key[0]][key[1] - 1])
    drop = {}
    for vn, pos in DELETE:
        drop.setdefault(vn, set()).add(pos)
    for (vn, pos), (asset, name) in REPLACE.items():
        im = Image.open(os.path.join(ASSETS, asset)).convert("RGB")
        im.thumbnail((1000, 1000))
        save_webp(im, os.path.join(IMG_DIR, name))
        snap[vn][pos - 1] = REL + name
        by[vn]["images"] = list(snap[vn])
    for vn, (asset, name) in ADD.items():
        im = Image.open(os.path.join(ASSETS, asset)).convert("RGB")
        im.thumbnail((1000, 1000))
        save_webp(im, os.path.join(IMG_DIR, name))
        by[vn]["images"] = list(by[vn]["images"]) + [REL + name]
        snap[vn] = list(by[vn]["images"])
    for vn, positions in drop.items():
        by[vn]["images"] = [p for i, p in enumerate(snap[vn], 1) if i not in positions]

    for vn, caps in CAPTIONS.items():
        by[vn]["image_captions"] = caps
        by[vn]["media_layout"] = "media-captioned"
        if len(by[vn]["images"]) != len(caps):
            warnings.append("%s: %d pictures, %d captions" % (vn, len(by[vn]["images"]), len(caps)))

    # ---- chapter heading: skandha line then chandas line
    for v in work["verses"]:
        s = v.get("subheading_ta")
        if s:
            s = re.sub(r"^ஸ்கந்தம் ", "பாகவத ஸ்கந்தம் ", s)
            v["subheading_ta"] = re.sub(r"\s*·\s*Chandas:", "<br>Chandas:", s)

    with open(WORK, "w", encoding="utf-8") as f:
        json.dump(work, f, ensure_ascii=False, indent=2)
        f.write(chr(10))
    for w in warnings:
        print("WARN", w)


if __name__ == "__main__":
    main()
