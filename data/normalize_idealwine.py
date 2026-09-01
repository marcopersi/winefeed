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

SRC_DIR = os.path.join(os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-persi.marco@gmail.com/"
    "Meine Ablage/Wein/WeinAuktionspreise"), "IDealwine")
DST_DIR = os.path.join(os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-persi.marco@gmail.com/"
    "Meine Ablage/Wein/WeinAuktionspreise"), "IDealwine_normalized")

# "Caisse Duclot" / "Caisse Prestige Duclot" mixed cases: `numberOfBottles`
# reflects a crate count, not a bottle count. The per-bottle derivation is
# therefore meaningless for these products.
DUCLOT_PIDS = {
    125289, 125290, 125293, 125294, 125295, 125296, 125297, 125298, 125299,
    126789, 134409, 136369, 158149, 182389, 187452, 199789, 199790, 213689,
    504627,
}

EPS = 0.02  # EUR tolerance for "value equals a rating" checks


def round2(x):
    return round(x, 2)


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

        with open(src_path) as f:
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
            sold_at = a.get("sold_at")
            bottles = a.get("bottles")
            hammer = a.get("hammer_eur")      # price/100  (lot total)
            total = a.get("total_eur")        # historicPrice/100 (per-bottle incl.)

            rec = {
                "sold_at": sold_at,
                "format": a.get("format"),
                "number_of_bottles": bottles,
                "hammer_lot_eur": hammer,
                "hammer_per_bottle_eur": None,
                "total_per_bottle_eur": total,
                "price_basis": None,
                "buyer_premium_rate": None,
                "buyer_premium_vat": None,
                "anomaly_type": None,
                "hammer_per_bottle_eur_derived": None,
                "derived_rate_assumed": None,
                "code": a.get("code"),
            }

            if hammer is None:
                stats["price_null"] += 1
                rec["price_basis"] = "HAMMER_PLUS_BUYERS_PREMIUM"

                if sold_at:
                    if sold_at >= "2026-04-01":
                        rate, vat = 0.258, "TTC"
                    elif sold_at >= "2024-01-01":
                        rate, vat = 0.252, "TTC"
                    else:
                        rate, vat = None, None
                else:
                    rate, vat = None, None

                if rate is not None and total is not None:
                    rec["hammer_per_bottle_eur_derived"] = round2(
                        total / (1 + rate))
                    rec["derived_rate_assumed"] = True
                    stats["derived"] += 1
                rec["buyer_premium_rate"] = rate
                rec["buyer_premium_vat"] = vat
                out["adjudications"].append(rec)
                continue

            # ---- hammer present ----
            stats["price_ok"] += 1
            rec["price_basis"] = "HAMMER"

            if is_duclot:
                rec["anomaly_type"] = "MIXED_CASE"
                stats["mixed_case"] += 1
                out["adjudications"].append(rec)
                continue

            factor = round(total * bottles / hammer, 4)

            is_cote = False
            if factor < 1.10 and total is not None:
                yr = int(sold_at[:4]) if sold_at and sold_at[:4].isdigit() else 0
                if cote is not None and abs(total - cote) < EPS:
                    is_cote = True
                for check_yr in (yr, yr - 1, yr + 1):
                    if check_yr in annual and abs(total - annual[check_yr]) < EPS:
                        is_cote = True

            if is_cote:
                rec["anomaly_type"] = "COTE_AS_HISTORIC"
                stats["cote_as_historic"] += 1
            elif 1.2510 <= factor <= 1.2530:
                rec["buyer_premium_rate"] = 0.252
                rec["buyer_premium_vat"] = "TTC"
                stats["rate_252"] += 1
            elif 1.2570 <= factor <= 1.2590:
                rec["buyer_premium_rate"] = 0.258
                rec["buyer_premium_vat"] = "TTC"
                stats["rate_258"] += 1
            elif 1.2140 <= factor <= 1.2160:
                rec["buyer_premium_rate"] = 0.215
                rec["buyer_premium_vat"] = "HT"
                stats["rate_215_ht"] += 1
            elif 1.2090 <= factor <= 1.2110:
                rec["buyer_premium_rate"] = 0.21
                rec["buyer_premium_vat"] = "HT"
                stats["rate_21_ht"] += 1
            elif 1.1990 <= factor <= 1.2010:
                rec["buyer_premium_rate"] = 0.20
                rec["buyer_premium_vat"] = "HT"
                stats["rate_20_ht"] += 1
            else:
                rec["anomaly_type"] = "RATE_UNDETERMINED"
                stats["rate_undetermined"] += 1

            rec["hammer_per_bottle_eur"] = round2(hammer / bottles)
            out["adjudications"].append(rec)

        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        with open(dst_path, "w") as f:
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
