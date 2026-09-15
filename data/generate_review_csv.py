#!/usr/bin/env python3
"""Generate the vintage-review CSV with full lot context.

One row per distinct raw_wine with MISSING vintage, showing description,
producer, region, appellation, quantity, bottle size and a sample price so a
human (or AI) can map the vintage. Mixed lots and spirits are excluded.
"""
import csv
import os
import sqlite3

from wine_resolution.spirits import is_spirit, load_terms

DB = "/Volumes/samsung/winefeed-data/wine_auction_prices.sqlite"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(SCRIPT_DIR, "reference", "vintage_review_missing.csv")

COLS = ["raw_wine", "lots", "description", "producer", "region", "appellation",
        "classification", "quantity", "bottle_size_dl", "currency",
        "hammer_price", "vintage", "note"]


def main():
    terms = load_terms()
    conn = sqlite3.connect(DB)
    rows = conn.execute("""
        SELECT raw_wine, count(*) AS lots,
               MAX(description), MAX(producer), MAX(region),
               MAX(appellation), MAX(classification),
               MAX(quantity), MAX(bottle_size_dl), MAX(currency),
               MAX(hammer_price)
        FROM lots
        WHERE vintage_status = 'MISSING'
          AND lot_kind != 'MIXED'
          AND raw_wine IS NOT NULL AND raw_wine != ''
        GROUP BY raw_wine
        ORDER BY lots DESC
    """).fetchall()

    written = 0
    skipped = 0
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(COLS)
        for raw_wine, lots, desc, prod, reg, app, cls, qty, size, cur, hammer \
                in rows:
            if is_spirit(raw_wine, terms):
                skipped += 1
                continue
            w.writerow([raw_wine, lots, desc or "", prod or "", reg or "",
                        app or "", cls or "", qty if qty is not None else "",
                        size if size is not None else "", cur or "",
                        hammer if hammer is not None else "", "", ""])
            written += 1
    print(f"geschrieben: {OUT} ({written} Zeilen, {skipped} Spirituosen "
          f"gefiltert)")


if __name__ == "__main__":
    main()
