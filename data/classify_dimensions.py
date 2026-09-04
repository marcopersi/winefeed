#!/usr/bin/env python3
"""Classify distinct raw region/producer values into canonical dimensions.

First heuristic pass. Counts are real lot counts (for prioritisation). Produces
reference CSVs (region, appellation, classification, variety, producer
remainder) for manual review.
"""
import csv
import os
import re
import sqlite3

from wine_resolution.normalize import normalize

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(SCRIPT_DIR, "wine_auction_prices.sqlite")
REF = os.path.join(SCRIPT_DIR, "reference")


def _load_varieties():
    path = os.path.join(REF, "varieties.csv")
    with open(path, encoding="utf-8") as fh:
        return {normalize(r["name"]) for r in csv.DictReader(fh)}


def _load_geo():
    """Geographic names (region + appellation) from the curated regions.csv."""
    path = os.path.join(REF, "regions.csv")
    with open(path, encoding="utf-8") as fh:
        return {normalize(r["name"]) for r in csv.DictReader(fh)}


def _load_appellations():
    """Canonical appellations from the iDealwine reference data."""
    conn = sqlite3.connect(DB)
    out = {normalize(r[0]) for r in conn.execute(
        "SELECT DISTINCT appellation FROM lots WHERE appellation IS NOT NULL"
        " AND appellation != ''")}
    conn.close()
    return out


VARIETIES = _load_varieties()
GEO = _load_geo()
APPELLATIONS = _load_appellations()

_CLASSIFICATION_RE = re.compile(
    r"\b(grand cru( classe)?|premier cru|premier grand cru|cru classe|"
    r"cru bourgeois|[1-5]er|2eme|3eme|4eme|5eme|1er grand cru)\b",
    re.IGNORECASE)


def classify(value):
    key = normalize(value)
    if not key:
        return "producer"
    if key in VARIETIES:
        return "variety"
    if key in APPELLATIONS:
        return "appellation"
    if key in GEO:
        return "region"
    if _CLASSIFICATION_RE.search(value):
        return "classification"
    return "producer"


def main():
    conn = sqlite3.connect(DB)
    buckets = {"region": {}, "appellation": {}, "classification": {},
               "variety": {}, "producer": {}}

    def add(dim, value, count, source):
        if value not in buckets[dim]:
            buckets[dim][value] = [0, source]
        buckets[dim][value][0] += count

    # producer field, with real counts
    for value, count in conn.execute(
            "SELECT producer, count(*) FROM lots WHERE producer IS NOT NULL"
            " AND producer != '' GROUP BY producer"):
        add(classify(value), value, count, "other")
    # region field, with real counts
    for value, count in conn.execute(
            "SELECT region, count(*) FROM lots WHERE region IS NOT NULL"
            " AND region != '' GROUP BY region"):
        dim = classify(value)
        if dim == "producer":
            dim = "region"
        add(dim, value, count, "other")
    # idealwine classification (already canonical)
    for value, count in conn.execute(
            "SELECT classification, count(*) FROM lots WHERE classification"
            " IS NOT NULL AND classification != '' GROUP BY classification"):
        add("classification", value, count, "idealwine")
    # idealwine region (canonical base)
    for value, count in conn.execute("""
            SELECT l.region, count(*) FROM lots l
            JOIN auctions a ON l.auction_id=a.id
            JOIN providers p ON a.provider_id=p.id
            WHERE p.name='idealwine' AND l.region IS NOT NULL
            GROUP BY l.region"""):
        add("region", value, count, "idealwine")
    # idealwine appellation (canonical base, fine-grained)
    for value, count in conn.execute("""
            SELECT l.appellation, count(*) FROM lots l
            JOIN auctions a ON l.auction_id=a.id
            JOIN providers p ON a.provider_id=p.id
            WHERE p.name='idealwine' AND l.appellation IS NOT NULL
            GROUP BY l.appellation"""):
        add("appellation", value, count, "idealwine")

    for dim in ("region", "appellation", "classification", "variety",
                "producer"):
        path = os.path.join(REF, f"dim_{dim}.csv")
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["value", "lots", "source", "keep"])
            for value, (count, source) in sorted(
                    buckets[dim].items(), key=lambda x: (-x[1][0], x[0])):
                w.writerow([value, count, source, ""])
        print(f"{dim:14} {len(buckets[dim]):6}  -> reference/dim_{dim}.csv")


if __name__ == "__main__":
    main()
