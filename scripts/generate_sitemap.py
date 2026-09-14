"""
generate_sitemap.py
Generates sitemap.xml for tamskritam.github.io from works_index.json.
Run from the repo root: python scripts/generate_sitemap.py
"""

import json
import os
from datetime import date

BASE_URL = "https://tamskritam.github.io"
WORKS_INDEX = os.path.join("data", "works_index.json")
OUTPUT_FILE = "sitemap.xml"

# Today's date for <lastmod>
TODAY = date.today().isoformat()


def build_url(loc: str, priority: str, changefreq: str) -> str:
    return (
        f"  <url>\n"
        f"    <loc>{loc}</loc>\n"
        f"    <lastmod>{TODAY}</lastmod>\n"
        f"    <changefreq>{changefreq}</changefreq>\n"
        f"    <priority>{priority}</priority>\n"
        f"  </url>"
    )


def main():
    with open(WORKS_INDEX, encoding="utf-8") as f:
        works = json.load(f)

    urls = []

    # Home / catalog page
    urls.append(build_url(BASE_URL + "/", priority="1.0", changefreq="weekly"))

    # Individual work pages (hash-routed SPA)
    for work in works:
        work_id = work["id"]
        loc = f"{BASE_URL}/#read/{work_id}"
        urls.append(build_url(loc, priority="0.8", changefreq="monthly"))

    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(sitemap)

    print(f"sitemap.xml generated with {len(urls)} URLs.")


if __name__ == "__main__":
    main()
