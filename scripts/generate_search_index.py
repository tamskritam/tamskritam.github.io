"""
generate_search_index.py
Generates data/search_index.json for tamskritam.github.io from all work JSON files.
Run from the repo root: python scripts/generate_search_index.py
"""

import json
import os

WORKS_DIR = os.path.join("data", "works")
WORKS_INDEX = os.path.join("data", "works_index.json")
OUTPUT_FILE = os.path.join("data", "search_index.json")


def extract_names_text(verse: dict) -> str:
    """Concatenate all name_sa values from names_breakdown into a searchable string."""
    breakdown = verse.get("names_breakdown")
    if not breakdown:
        return ""
    return " ".join(n.get("name_sa", "") for n in breakdown if n.get("name_sa"))


def main():
    # Load index to get ordered list of work IDs and Tamil titles
    with open(WORKS_INDEX, encoding="utf-8") as f:
        index = json.load(f)

    # Build a lookup: id -> title_ta
    title_lookup = {w["id"]: w["title_ta"] for w in index}
    # Preserve catalog ordering
    work_ids_ordered = [w["id"] for w in index]

    records = []

    for work_id in work_ids_ordered:
        work_file = os.path.join(WORKS_DIR, f"{work_id}.json")
        if not os.path.exists(work_file):
            print(f"  WARNING: {work_file} not found, skipping.")
            continue

        with open(work_file, encoding="utf-8") as f:
            work = json.load(f)

        work_title_ta = title_lookup.get(work_id, work.get("title_ta", ""))
        verses = work.get("verses", [])

        for verse in verses:
            # Skip non-verse structural items if any
            verse_id = verse.get("id")
            if verse_id is None:
                continue

            record = {
                "work_id": work_id,
                "work_title_ta": work_title_ta,
                "verse_id": verse_id,
                "verse_num": verse.get("verse_num", ""),
                "section": verse.get("section", ""),
                "sanskrit": verse.get("sanskrit", ""),
                "tamil": verse.get("tamil", ""),
                "names_text": extract_names_text(verse),
                "meaning": verse.get("meaning", ""),
            }
            records.append(record)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"search_index.json generated: {len(records)} verse records across {len(work_ids_ordered)} works.")


if __name__ == "__main__":
    main()
