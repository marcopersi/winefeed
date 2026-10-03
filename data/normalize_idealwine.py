#!/usr/bin/env python3
"""Normalize iDealwine extraction output: separate hammer vs. premium prices.

Reads the raw per-wine JSON files produced by idealwine_extract.py and writes
semantically-correct records to a sibling directory (IDealwine_normalized/).

The raw extractor mislabeled two API fields:
  - `price` (cents)      -> stored as `hammer_eur`: LOT hammer total.
  - `historicPrice` (cents) -> stored as `total_eur`: per-bottle incl. premium.

This script:
  1. renames fields to their true meaning;
  2. derives hammer_per_bottle_eur;
  3. sets price_basis (HAMMER vs HAMMER_PLUS_BUYERS_PREMIUM);
  4. classifies the buyer's-premium rate and flags anomalies;
  5. back-calculates the hammer for price-less lots (2024+ only).
"""
import argparse
import json
import os
import shutil

from idealwine_normalize import DUCLOT_PIDS, normalize_adjudication

SRC_DIR = os.path.join(os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-persi.marco@gmail.com/"
    "Meine Ablage/Wein/WeinAuktionspreise"), "IDealwine")
DST_DIR = os.path.join(os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-persi.marco@gmail.com/"
    "Meine Ablage/Wein/WeinAuktionspreise"), "IDealwine_normalized")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true",
                        help="overwrite existing normalized files")
    parser.add_argument("--limit", type=int, default=None,
                        help="process only the first N wine files (dry run)")
    args = parser.parse_args()

    os.makedirs(DST_DIR, exist_ok=True)

    # Copy the enumeration directory unchanged.
    src_dir_file = os.path.join(SRC_DIR, "wines_directory.json")
    dst_dir_file = os.path.join(DST_DIR, "wines_directory.json")
    if not os.path.exists(dst_dir_file) or args.force:
        shutil.copy2(src_dir_file, dst_dir_file)

    files = []
    for region in sorted(os.listdir(SRC_DIR)):
        region_dir = os.path.join(SRC_DIR, region)
        if not os.path.isdir(region_dir):
            continue
        for name in sorted(os.listdir(region_dir)):
            if name.endswith(".json"):
                files.append((region, name))
    files.sort()

    if args.limit is not None:
        files = files[: args.limit]

    stats = {
        "files": 0, "skipped": 0, "adjs": 0,
        "price_ok": 0, "price_null": 0,
        "rate_252": 0, "rate_258": 0,
        "rate_215_ht": 0, "rate_21_ht": 0, "rate_20_ht": 0,
        "mixed_case": 0, "cote_as_historic": 0, "rate_undetermined": 0,
        "derived": 0,
    }

    for region, name in files:
        src_path = os.path.join(SRC_DIR, region, name)
        dst_path = os.path.join(DST_DIR, region, name)

        if os.path.exists(dst_path) and not args.force:
            stats["skipped"] += 1
            continue

        with open(src_path, encoding="utf-8") as f:
            d = json.load(f)

        out = {
            "product_id": d.get("product_id"),
            "vintage": d.get("vintage"),
            "wine": d.get("wine"),
            "estate": d.get("estate"),
            "appellation": d.get("appellation"),
            "color": d.get("color"),
            "classification": d.get("classification"),
            "region": d.get("region"),
            "current_rating_eur": d.get("current_rating_eur"),
            "annual_ratings_eur": d.get("annual_ratings_eur"),
            "adjudications": [],
        }

        is_duclot = d.get("product_id") in DUCLOT_PIDS
        cote = d.get("current_rating_eur")
        annual = {r["year"]: r["value"]
                  for r in (d.get("annual_ratings_eur") or [])
                  if isinstance(r, dict) and r.get("year") is not None}

        for a in d.get("adjudications") or []:
            stats["adjs"] += 1
            rec, class_code = normalize_adjudication(a, is_duclot, cote, annual)
            if class_code == "price_null":
                stats["price_null"] += 1
                if rec.get("derived_rate_assumed"):
                    stats["derived"] += 1
            else:
                stats["price_ok"] += 1
            stats[class_code] += 1
            out["adjudications"].append(rec)

        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        with open(dst_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        stats["files"] += 1

    print("=== NORMALIZE SUMMARY ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    total_classified = (stats["rate_252"] + stats["rate_258"] +
                        stats["rate_215_ht"] + stats["rate_21_ht"] +
                        stats["rate_20_ht"] + stats["mixed_case"] +
                        stats["cote_as_historic"] + stats["rate_undetermined"])
    print(f"  classified(price_ok): {total_classified} "
          f"(== price_ok {stats['price_ok']}? {total_classified == stats['price_ok']})")


if __name__ == "__main__":
    main()
