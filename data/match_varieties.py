#!/usr/bin/env python3
"""Write a variety -> wines summary for review.

Grapes are detected inside wine names via wine_resolution.variety. Reads the
built database (Samsung disk) and writes reference/variety_matches.csv.
"""
import csv
import os
import sqlite3

from wine_resolution.normalize import normalize
from wine_resolution.variety import default_varieties_path, load_varieties, \
    match_varieties

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB = "/Volumes/samsung/winefeed-data/wine_auction_prices.sqlite"
REF = os.path.join(SCRIPT_DIR, "reference")


def main():
    varieties = load_varieties(default_varieties_path())
    variety_keys = [normalize(v) for v, _ in varieties]
    key_to_meta = {normalize(v): (v, c) for v, c in varieties}

    conn = sqlite3.connect(DB)
    rows = conn.execute("SELECT canonical_name FROM wines").fetchall()

    counts = {}
    examples = {}
    multi = 0
    none = 0
    for (name,) in rows:
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
            vname, color = key_to_meta[k]
            w.writerow([vname, color, count, examples[k][0][:80]])

    print(f"Rebsorten im Namen: {len(counts)}, wines ohne: {none}, "
          f"Blends: {multi}, total: {len(rows)}")
    print("-> reference/variety_matches.csv")


if __name__ == "__main__":
    main()
