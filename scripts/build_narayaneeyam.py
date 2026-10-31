"""
build_narayaneeyam.py
One-off converter: builds data/works/narayaneeyam.json (and recompressed pictures under
images/pictures/narayaneeyam/) from the author's per-dasakam Word files.

Run from the repo root:
    python scripts/build_narayaneeyam.py "<folder containing '1 Narayaneeyam.docx' ... 'Prelogue.docx'>"
Requires: python-docx, Pillow.
"""

import hashlib
import html
import io
import json
import os
import re
import sys

import docx
from docx.oxml.ns import qn
from PIL import Image

WORK_ID = "narayaneeyam"
OUT_JSON = os.path.join("data", "works", f"{WORK_ID}.json")
IMG_DIR = os.path.join("images", "pictures", WORK_ID)
IMG_MAX = 1000          # longest side in px after recompression
R_EMBED = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"

DEVA = re.compile(r"[ऀ-ॿ]")
TAMIL = re.compile(r"[஀-௿]")
VERSE_NUM = re.compile(r"^(\d+)\.(\d+)$")


def cell_text(tc):
    out = []
    for el in tc.iter():
        if el.tag == qn("w:t"):
            out.append(el.text or "")
        elif el.tag in (qn("w:br"), qn("w:cr")):
            out.append("\n")
        elif el.tag == qn("w:tab"):
            out.append(" ")
        elif el.tag == qn("w:p") and out and not out[-1].endswith("\n"):
            out.append("\n")
    return "".join(out).strip()


def para_text(p):
    return "".join(
        "\n" if el.tag in (qn("w:br"), qn("w:cr")) else (el.text or "")
        for el in p.iter() if el.tag in (qn("w:t"), qn("w:br"), qn("w:cr"))
    ).strip()


def esc(s):
    return html.escape(s, quote=False)


def clean_lines(text):
    return [re.sub(r"[ \t ]+", " ", l).strip() for l in text.split("\n") if l.strip()]


def blip_ids(el):
    rids = []
    for b in el.iter(qn("a:blip")):
        rid = b.get(R_EMBED)
        if rid and rid not in rids:
            rids.append(rid)
    return rids


def body_items(document):
    """Yield ('row', [cell texts], [image rIds]) or ('para', text, [image rIds]) in document order."""
    for el in document.element.body:
        if el.tag == qn("w:tbl"):
            for tr in el.iter(qn("w:tr")):
                cells = tr.findall(qn("w:tc"))
                yield "row", [cell_text(tc) for tc in cells], blip_ids(tr)
        elif el.tag == qn("w:p"):
            yield "para", para_text(el), blip_ids(el)


def poem_like(block):
    lines = clean_lines(block)
    if len(lines) < 3 or len(lines) > 16:
        return False
    return sum(len(l) for l in lines) / len(lines) <= 80


def poem_score(block):
    """Fraction of lines following the 'every second line indented' poem layout (0 when not poem-like)."""
    raw = [l for l in block.split(chr(10)) if l.strip()]
    if not poem_like(block) or len(raw) < 2:
        return 0.0
    ind = [l.startswith(("  ", chr(160) * 2)) for l in raw]
    ok = sum(1 for i, x in enumerate(ind) if x == (i % 2 == 1))
    return ok / len(raw)


def block_html(block):
    return "<br>".join(esc(l) for l in clean_lines(block))


class ImageStore:
    def __init__(self):
        os.makedirs(IMG_DIR, exist_ok=True)
        self.seen = {}
        self.bytes = 0

    def save(self, blob, name):
        h = hashlib.md5(blob).hexdigest()
        if h in self.seen:
            return self.seen[h]
        im = Image.open(io.BytesIO(blob))
        im.load()
        im = im.convert("RGBA" if im.mode in ("P", "LA", "RGBA") else "RGB")
        im.thumbnail((IMG_MAX, IMG_MAX))
        rel = f"images/pictures/{WORK_ID}/{name}.webp"
        im.save(rel, "WEBP", quality=78, method=6)
        self.bytes += os.path.getsize(rel)
        self.seen[h] = rel
        return rel


def normalise_danda(text):
    """Standardise verse-line endings: OCR-ish 'l', 'I', 'll', 'II', '||', '। ।' -> । (mid-verse) / ॥ (verse end)."""
    mark = r"(?:[lI|।॥]\s*)+"
    lines = text.split(chr(10))
    for i, line in enumerate(lines):
        last = i == len(lines) - 1
        m = re.search(r"(?<=[ऀ-ॿ\s!?,;:])\s*(" + mark + r")$", line)
        if m:
            ends = m.group(1).replace(" ", "")
            double = last or len(ends) >= 2
            line = line[:m.start()].rstrip() + (" ॥" if double else " ।")
        elif last and re.search(r"[ऀ-ॿ]$", line):
            line += " ॥"
        lines[i] = line
    if lines and not lines[-1].endswith(chr(0x965)):
        lines[-1] += " " + chr(0x965)
    return chr(10).join(lines)


def parse_dasakam(path, num, store, warnings):
    document = docx.Document(path)
    rels = {r.rId: r.target_part for r in document.part.rels.values() if "image" in r.reltype}
    verses = []
    cur = None
    cover_imgs = []
    table_run = []
    img_n = 0

    def add_images(rids, target):
        nonlocal img_n
        for rid in rids:
            part = rels.get(rid)
            if part is None:
                continue
            img_n += 1
            try:
                target.append(store.save(part.blob, f"d{num:03d}_{img_n:02d}"))
            except Exception as e:  # unreadable image: report and carry on
                warnings.append(f"dasakam {num}: image {rid} skipped ({e})")

    def flush_table():
        nonlocal table_run
        if table_run and cur is not None:
            cols = max(len(r) for r in table_run)
            body = "".join(
                "<tr>" + "".join(f"<td>{block_html(c)}</td>" for c in (r + [""] * (cols - len(r)))) + "</tr>"
                for r in table_run
            )
            cur["blocks"].append(("table",
                f'<div class="analysis-table-container"><table class="analysis-table"><tbody>{body}</tbody></table></div>'))
        table_run = []

    for kind, payload, rids in body_items(document):
        if kind == "para":
            t = payload
            if not t or re.fullmatch(r"[\sऀ-ॿ]*शुभम्[\sऀ-ॿ]*", t):
                continue
            if cur is not None:
                flush_table()
                cur["blocks"].append(("text", t))
            continue
        cells = payload
        first = cells[0].strip() if cells else ""
        m = VERSE_NUM.match(first)
        rest = [c for c in cells[1:] if c.strip()]
        if m and int(m.group(1)) == num:
            flush_table()
            n2 = int(m.group(2))
            text = rest[0] if rest else ""
            if cur is not None and cur["num"] == n2:
                cur["blocks"].append(("text", text))      # verse number repeated for the Tamil poem
            elif cur is not None and text and TAMIL.search(text) and not DEVA.search(text):
                cur["blocks"].append(("text", text))      # mislabelled number on the previous verse's poem
                warnings.append(f"{num}.{cur['num']}: poem row labelled {num}.{n2} in source, kept with {num}.{cur['num']}")
            else:
                cur = {"num": n2, "sanskrit": "", "blocks": [], "images": []}
                verses.append(cur)
                if text and DEVA.search(text) and not TAMIL.search(text):
                    cur["sanskrit"] = text
                elif text:
                    cur["blocks"].append(("text", text))
                for extra in rest[1:]:                    # meaning sharing the Sanskrit row
                    cur["blocks"].append(("text", extra))
            add_images(rids, cur["images"])
            continue
        nonempty = [c for c in cells if c.strip()]
        if cur is None:
            add_images(rids, cover_imgs)
            continue
        add_images(rids, cur["images"])
        if not nonempty:
            continue
        if len(cells) >= 3 and (len(nonempty) >= 2 or table_run):
            table_run.append(cells)
            continue
        flush_table()
        text = "\n".join(nonempty)
        if DEVA.search(text) and not TAMIL.search(text) and not cur["sanskrit"]:
            cur["sanskrit"] = text
        else:
            cur["blocks"].append(("text", text))
    flush_table()

    out = []
    for v in verses:
        explicit = [b for b in v["blocks"] if b[0] == "poem"]
        texts = [b for b in v["blocks"] if b[0] != "poem"]
        tag = f"{num}.{v['num']}"
        if explicit:
            poem, rest = explicit[-1][1], texts
        else:
            idx = None
            cand = [(poem_score(t), i) for i, (k, t) in enumerate(texts) if k == "text" and poem_like(t)]
            good = [c for c in cand if c[0] >= 0.75]
            if good:
                idx = good[-1][1]
            elif cand:
                idx = cand[-1][1]
            if idx is None and len(texts) > 1 and texts[-1][0] == "text":
                idx = len(texts) - 1
                warnings.append(f"{tag}: poem not recognised, assumed last block")
            if idx is None:
                warnings.append(f"{tag}: no Tamil poem found")
                poem, rest = "", texts
            else:
                poem, rest = texts[idx][1], texts[:idx] + texts[idx + 1:]
        meaning_parts = [t if k == "table" else block_html(t) for k, t in rest]
        poem_lines = clean_lines(poem)
        # footnotes glued to the end of the poem cell
        foot = next((i for i, l in enumerate(poem_lines) if l.startswith("*")), None)
        if foot is not None:
            meaning_parts.append("<br>".join(esc(l) for l in poem_lines[foot:]))
            poem_lines = poem_lines[:foot]
        if poem_lines:
            fm = re.search(r"\*\s+([^*]+?=.+)$", poem_lines[-1])
            if fm:
                poem_lines[-1] = poem_lines[-1][:fm.start()].rstrip()
                meaning_parts.append("* " + esc(fm.group(1)))
        sanskrit = "\n".join(clean_lines(v["sanskrit"]))
        sanskrit = normalise_danda(sanskrit)
        if not sanskrit:
            warnings.append(f"{tag}: no Sanskrit")
        out.append({
            "verse_num": tag,
            "sanskrit": sanskrit,
            "tamil": "\n".join(poem_lines),
            "meaning": "<br><br>".join(meaning_parts),
            "images": v["images"],
        })
    if cover_imgs and out:
        out[0]["images"] = cover_imgs + out[0]["images"]
    return out


def parse_front(folder):
    document = docx.Document(os.path.join(folder, "Prelogue.docx"))
    paras, chapters, skandha = [], {}, ""
    for kind, payload, _ in body_items(document):
        if kind == "para":
            if payload.strip():
                paras.append(payload.strip())
            continue
        cells = payload
        if len(cells) < 4 or cells[0] == "Bhagavata Skanda:" or not re.fullmatch(r"\d+", cells[1].strip()):
            continue
        if cells[0].strip():
            skandha = cells[0].strip()
        chapters[int(cells[1])] = {
            "skandha": skandha,
            "name": " ".join(cells[2].split()),
            "count": int(cells[3]),
            "chandas": " / ".join(clean_lines(cells[4])) if len(cells) > 4 else "",
        }
    return paras, chapters


def main():
    folder = sys.argv[1]
    store = ImageStore()
    warnings = []
    paras, chapters = parse_front(folder)
    paras = [p for p in paras if p not in ("நாராயணீயம்", "ஆசிரியர் உரை") and not p.startswith("NARAYANEEYAM Chapters")]

    prologue_section = "ஆசிரியர் உரை (Prologue)"
    sections = [prologue_section]
    verses = [{
        "id": 1, "verse_num": "", "section": prologue_section, "is_intro": True,
        "sanskrit": "", "tamil": "\n".join(esc(p) for p in paras), "meaning": "", "images": [],
    }]
    index_chapters = []
    vid = 1
    for n in range(1, 101):
        name = f"{n} Narayaneeyam .docx" if n == 93 else f"{n} Narayaneeyam.docx"
        info = chapters[n]
        section = f"{n}) {info['name']}"
        sections.append(section)
        index_chapters.append({"chapter_num": n, "title": section})
        dv = parse_dasakam(os.path.join(folder, name), n, store, warnings)
        if len(dv) != info["count"]:
            warnings.append(f"dasakam {n}: found {len(dv)} verses, table says {info['count']}")
        for i, v in enumerate(dv):
            vid += 1
            rec = {"id": vid, "verse_num": v["verse_num"], "chapter_num": n, "section": section}
            if i == 0:
                rec["subheading_ta"] = f"ஸ்கந்தம் {info['skandha']} · Chandas: {info['chandas']}"
            rec.update({k: v[k] for k in ("sanskrit", "tamil", "meaning", "images")})
            verses.append(rec)

    total = len(verses) - 1
    work = {
        "id": WORK_ID,
        "title_ta": "நாராயணீயம்",
        "title_sa": "श्रीमन्नारायणीयम्",
        "title_en": "Narayaneeyam",
        "category": "stotra",
        "deity": "krishna",
        "original_author": "மேல்பத்தூர் நாராயண பட்டத்ரி",
        "translator": "ரா.குருராஜ்",
        "summary": "குருவாயூரப்பனை நேரில் விளித்துப் பாடிய பாகவத சாரமான நாராயணீயத்தின் 100 தசகங்கள், 1036 ஸ்லோகங்கள் - ஸம்ஸ்கிருத மூலம், தமிழ்ச் செய்யுள் வடிவம், விளக்கவுரையுடன்.",
        "icon": f"images/icons/works/{WORK_ID}.svg",
        "total_verses": total,
        "index_chapters": index_chapters,
        "sections": sections,
        "meaning_style": "poem",
        "verses": verses,
        "categories": ["stotra", "bhagavatham"],
        "source_work": "",
        "authors": [{"title": "மேல்பத்தூர்", "name": "நாராயண பட்டத்ரி"}],
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(work, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"verses: {total}; images: {len(store.seen)} ({store.bytes / 1e6:.1f} MB)")
    for w in warnings:
        print("WARN", w)


if __name__ == "__main__":
    main()
