#!/usr/bin/env python3
"""Offline review tool for producer-in-name redundancy (read-only).

Splits the ``wines`` table into two buckets and writes two CSVs:

- **DETERMINISTIC** — the producer is a clean suffix/prefix of the canonical
  name: emit ``MERGE`` override candidates that strip the producer from the
  name (and keep it in the ``producer`` field).
- **AMBIGUOUS** — the producer is embedded mid-name, or a producer-less wine's
  name contains a known producer: emit a review CSV for manual/LLM review.

This tool is OFFLINE and never feeds an LLM into the build (the build must
stay deterministic/idempotent). The overrides are later merged into
``data/reference/wine_alias_overrides.csv`` after review.
"""
import csv
import os
import sqlite3

DB_PATH = os.environ.get(
    "DB_PATH", "/Volumes/samsung/winefeed-data/wine_auction_prices.sqlite")
OUT_OVERRIDES = os.environ.get(
    "OUT_OVERRIDES", "reference/wine_alias_overrides_producer.csv")
OUT_REVIEW = os.environ.get(
    "OUT_REVIEW", "reference/wine_producer_review.csv")

OVERRIDE_FIELDS = ["alias_raw", "producer_raw", "canonical_name", "action",
                   "reason"]
REVIEW_FIELDS = ["canonical_name", "producer", "category", "hint"]


def _strip(name, producer):
    """Strip ``producer`` as a suffix/prefix from the display name."""
    if name.endswith(producer):
        return name[: -len(producer)].strip(" ,-")
    if name.startswith(producer):
        return name[len(producer):].strip(" ,-")
    return None


def main():
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    with_prod = conn.execute(
        "SELECT canonical_name, canonical_key, producer, producer_key"
        " FROM wines WHERE producer_key != ''").fetchall()
    producer_keys = {pk for _, _, _, pk in with_prod}
    without_prod = conn.execute(
        "SELECT canonical_name, canonical_key FROM wines"
        " WHERE producer_key = ''").fetchall()

    overrides = []
    review = []
    for name, key, producer, pk in with_prod:
        if pk == key:
            continue
        if key.endswith(pk):
            stripped = _strip(name, producer)
            if stripped:
                overrides.append((name, producer, stripped, "producer-suffix"))
                continue
        if key.startswith(pk):
            # Prefix is unsafe: for "Château X" the producer is the wine itself
            # and stripping leaves only the vintage. Defer to review.
            review.append((name, producer, "producer-prefix", "may-be-wine"))
            continue
        if pk in key:
            review.append((name, producer, "producer-embedded", "mid-name"))

    for name, key in without_prod:
        hits = sorted(pk for pk in producer_keys if pk in key)
        if hits:
            review.append((name, ", ".join(hits), "name-contains-producer",
                           "no-field"))

    with open(OUT_OVERRIDES, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(OVERRIDE_FIELDS)
        for alias_raw, producer, canonical, reason in overrides:
            w.writerow([alias_raw, producer, canonical, "MERGE", reason])

    with open(OUT_REVIEW, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(REVIEW_FIELDS)
        for name, producer, category, hint in review:
            w.writerow([name, producer, category, hint])

    print(f"wines with producer: {len(with_prod)}")
    print(f"wines without producer: {len(without_prod)}")
    print(f"deterministic overrides (suffix/prefix): {len(overrides)}")
    print(f"ambiguous/review cases: {len(review)}")
    print(f"written: {OUT_OVERRIDES} ({len(overrides)})")
    print(f"written: {OUT_REVIEW} ({len(review)})")


if __name__ == "__main__":
    main()
