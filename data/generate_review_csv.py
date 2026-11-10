#!/usr/bin/env python3
"""Generate the vintage-review CSV with full lot context.

One row per distinct raw_wine with MISSING vintage, showing description,
producer, region, appellation, quantity, bottle size and a sample price so a
human (or AI) can map the vintage. Only lot_kind='SINGLE' is considered --
MIXED lots and UNKNOWN (spirits, or no wine name at all -- Gate-G0 fix,
same allow-list convention as build_wines._assume_default_bottle_size) have
no single wine to map a vintage onto in the first place. ``is_spirit()``
below is a second, finer-grained text check on top of that, not a
replacement for it.
"""
import csv
import os
import sqlite3

from wine_resolution.spirits import is_spirit, load_terms

DB = "/Volumes/samsung/winefeed-data/wine_auction_prices.sqlite"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(SCRIPT_DIR, "reference", "vintage_review_missing.csv")

COLS = ["raw_wine", "lots", "description", "producer", "region", "appellation",
        "classification", "quantity", "bottle_size_dl", "size_assumed",
        "currency", "hammer_price", "vintage", "note"]


def main():
    terms = load_terms()
    conn = sqlite3.connect(DB)
    rows = conn.execute("""
        SELECT raw_wine, count(*) AS lots,
               MAX(description), MAX(producer), MAX(region),
               MAX(appellation), MAX(classification),
               MAX(quantity), MAX(bottle_size_dl), MAX(size_assumed),
               MAX(currency), MAX(hammer_price)
        FROM lots
        WHERE vintage_status = 'MISSING'
          AND lot_kind = 'SINGLE'
          AND raw_wine IS NOT NULL AND raw_wine != ''
        GROUP BY raw_wine
        ORDER BY lots DESC
    """).fetchall()

    written = 0
    skipped = 0
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(COLS)
        for (raw_wine, lots, desc, prod, reg, app, cls, qty, size,
             size_assumed, cur, hammer) in rows:
            if is_spirit(raw_wine, terms):
                skipped += 1
                continue
            # MAX(size_assumed) over the group: if ANY lot sharing this
            # raw_wine got a fabricated 7.5dl default (_assume_default_
            # bottle_size), the shown bottle_size_dl is a guess for at
            # least part of the group, not a confirmed size -- Gate-G0
            # review fix: this column was missing entirely, so a human
            # (or AI) using this CSV to fix up vintage data saw "7.5"
            # indistinguishable from a genuinely confirmed 7.5dl bottle.
            w.writerow([raw_wine, lots, desc or "", prod or "", reg or "",
                        app or "", cls or "", qty if qty is not None else "",
                        size if size is not None else "",
                        1 if size_assumed else 0, cur or "",
                        hammer if hammer is not None else "", "", ""])
            written += 1
    print(f"geschrieben: {OUT} ({written} Zeilen, {skipped} Spirituosen "
          f"gefiltert)")


if __name__ == "__main__":
    main()
