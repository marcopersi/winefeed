#!/usr/bin/env python3
"""One-time backfill: parse the 30 archived weinauktionator *.xlsx files
into the {auction, lots} JSON ``run_ingest.py`` would have produced.

These 30 files were hand-downloaded before the ``WeinauktionatorFetcher``/
``orchestrate.py`` pipeline existed (confirmed: the live pipeline never
persists the raw xlsx, only the parsed JSON -- see
``data/orchestrate.py:_store_parsed``), so ``load_weinauktionator``'s
``*.json`` glob has always found nothing. This runs the SAME parser
(``parse_weinauktionator_xlsx``) the live pipeline uses, so the backfilled
files are byte-for-byte what a historical CI run would have written --
not a new, separate format.

Usage: ARCHIVE_PATH=... python3 data/backfill_weinauktionator_json.py
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from parse_results import parse_weinauktionator_xlsx  # noqa: E402
import build_db  # noqa: E402


def main():
    archive = build_db.ARCHIVE
    files = sorted(glob.glob(
        os.path.join(archive, "weinauktionator", "**", "*.xlsx"),
        recursive=True))
    print(f"found {len(files)} xlsx files")
    out_dir = os.path.join(archive, "weinauktionator")
    total_lots = 0
    for f in files:
        parsed = parse_weinauktionator_xlsx(f)
        if not parsed.get("lots"):
            print(f"  SKIP (no lots parsed): {f}")
            continue
        # Flat, matching data/orchestrate.py's _write_json exactly (no
        # subdirectory) -- load_weinauktionator's **/*.json glob would
        # otherwise double-load every auction the CI fetcher later
        # refetches into its own flat ARCHIVE_PATH/weinauktionator/<id>.json
        # (add_auction's INSERT OR IGNORE only collapses files that share
        # the same path-derived auction id; two files with the same id at
        # different paths both get kept, each with its own lots).
        basename = os.path.splitext(os.path.basename(f))[0] + ".json"
        out_path = os.path.join(out_dir, basename)
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(parsed, fh, ensure_ascii=False, default=str)
        total_lots += len(parsed["lots"])
        print(f"  {os.path.basename(f)} -> {basename}"
              f" ({len(parsed['lots'])} lots)")
    print(f"\ntotal: {total_lots} lots across {len(files)} files")


if __name__ == "__main__":
    main()
