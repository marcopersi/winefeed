#!/usr/bin/env python3
"""Build the gold-set candidate CSV for normalization evaluation (§4.0).

Stratified random sample across providers (plus explicit edge cases) and
writes ``data/tests/fixtures/gold_lots.csv`` with empty ``expected_*`` columns
for manual labeling. Read-only on the master DB.
"""
import csv
import os
import random
import sqlite3

DB_PATH = os.environ.get(
    "DB_PATH", "/Volumes/samsung/winefeed-data/wine_auction_prices.sqlite")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests",
                   "fixtures", "gold_lots.csv")

FIELDS = ["lot_id", "provider", "lot_kind", "raw_wine", "description",
          "expected_producer", "expected_wine", "expected_vintage",
          "expected_qty", "expected_dl", "expected_is_ohk"]

PER_PROVIDER = 25
EDGE_LIMIT = 10
SEED = 42


def main():
    random.seed(SEED)
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    seen = set()
    picks = []

    def add(row):
        if row[0] not in seen:
            seen.add(row[0])
            picks.append(row)

    providers = [r[0] for r in conn.execute(
        "SELECT name FROM providers ORDER BY name").fetchall()]
    for pname in providers:
        rows = conn.execute(
            "SELECT l.id, l.lot_kind, l.raw_wine, l.description"
            " FROM lots l JOIN auctions a ON a.id = l.auction_id"
            " JOIN providers p ON p.id = a.provider_id"
            " WHERE p.name = ? AND l.raw_wine IS NOT NULL"
            " AND l.raw_wine != ''", (pname,)).fetchall()
        if not rows:
            continue
        for r in random.sample(rows, min(PER_PROVIDER, len(rows))):
            add((r[0], pname, r[1], r[2], r[3]))

    edge_queries = [
        ("vertical", "lower(raw_wine) LIKE '%vertical%'"),
        ("mixed", "lower(raw_wine) LIKE '%mixed%'"),
        ("bottles", "raw_wine LIKE '%BT)%' OR raw_wine LIKE '%Bottle%'"),
        ("ohk", "lower(raw_wine) LIKE '%ohk%' OR lower(raw_wine) LIKE '%owc%'"
               " OR lower(raw_wine) LIKE '%cbo%'"
               " OR lower(raw_wine) LIKE '%original wooden%'"),
        ("petrus", "lower(raw_wine) LIKE '%petrus%'"),
        ("sassicaia", "lower(raw_wine) LIKE '%sassicaia%'"),
        ("huber", "lower(raw_wine) LIKE '%bernhard huber%'"
                  " OR lower(raw_wine) LIKE '%weingut bernhard%'"),
    ]
    for _label, cond in edge_queries:
        rows = conn.execute(
            f"SELECT l.id, l.lot_kind, l.raw_wine, l.description, p.name"
            f" FROM lots l JOIN auctions a ON a.id = l.auction_id"
            f" JOIN providers p ON p.id = a.provider_id"
            f" WHERE {cond} AND l.raw_wine IS NOT NULL"
            f" AND l.raw_wine != '' LIMIT {EDGE_LIMIT * 4}").fetchall()
        for r in random.sample(rows, min(EDGE_LIMIT, len(rows))):
            add((r[0], r[4], r[1], r[2], r[3]))

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(FIELDS)
        for lot_id, pname, kind, raw, desc in picks:
            w.writerow([lot_id, pname, kind, raw, desc or "",
                        "", "", "", "", "", ""])

    print(f"gold-set candidates: {len(picks)} -> {OUT}")


if __name__ == "__main__":
    main()
