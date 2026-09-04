#!/usr/bin/env python3
"""Substring-match grape varieties inside wine names.

The curated varieties.csv lists 130 grapes, but they almost never appear as a
standalone producer value — they are embedded in the wine name (e.g.
"Penfolds Bin 707 Cabernet Sauvignon"). This detects them by word-boundary
substring matching and writes a variety -> wines mapping for review.
"""
import csv
import os
import re
import sqlite3

from wine_resolution.normalize import normalize

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB = "/Volumes/samsung/winefeed-data/wine_auction_prices.sqlite"
REF = os.path.join(SCRIPT_DIR, "reference")


def load_varieties():
    path = os.path.join(REF, "varieties.csv")
    with open(path, encoding="utf-8") as fh:
        return [(r["name"], r["color"]) for r in csv.DictReader(fh)]


def match_varieties(name, variety_keys):
    """Return the set of normalized variety keys present in the name."""
    key = normalize(name)
    found = set()
    for v in variety_keys:
        if re.search(rf"\b{re.escape(v)}\b", key):
            found.add(v)
    return found


def main():
    varieties = load_varieties()
    variety_keys = [normalize(v) for v, _ in varieties]
    key_to_name = {normalize(v): v for v, _ in varieties}

    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT canonical_name, id FROM wines").fetchall()

    counts = {}
    examples = {}
    multi = 0
    none = 0
    for name, wine_id in rows:
        found = match_varieties(name, variety_keys)
        if not found:
            none += 1
            continue
        if len(found) > 1:
            multi += 1
        for k in found:
            counts[k] = counts.get(k, 0) + 1
            examples.setdefault(k, []).append(name)

    with open(os.path.join(REF, "variety_matches.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["variety", "color", "wine_count", "example"])
        for k, count in sorted(counts.items(), key=lambda x: -x[1]):
            vname = key_to_name.get(k, k)
            color = next((c for v, c in varieties if normalize(v) == k), "")
            w.writerow([vname, color, count, examples[k][0][:80]])

    print(f"wines mit >=1 Rebsorte im Namen: {len(counts)} Rebsorten")
    print(f"wines mit 0 Rebsorten: {none}, mit >1 (Blend): {multi}")
    print(f"total wines: {len(rows)}")
    print("-> reference/variety_matches.csv")


if __name__ == "__main__":
    main()
