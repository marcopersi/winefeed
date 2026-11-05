#!/usr/bin/env python3
"""Run the incremental iDealwine cote delta into the archive (not the DB).

Enumerates currently offered lots via Algolia, loads each cote through the
Next.js SSR route, and selects only adjudications newer than the checkpoint
recorded in the shared ingest manifest. New adjudications are archived as
one JSON file per (product, vintage) under
``IDealwine_normalized/_delta/`` -- the same file shape
``build_db.py``'s ``load_idealwine`` already reads (its glob is recursive,
so these need no loader change) -- instead of being appended straight into
the live DB. This is what lets iDealwine run as an ordinary CI step: the
live DB only exists on the local Samsung disk, unreachable from a GitHub
Actions runner, but the archive + manifest are exactly what every other
house's CI step already produces and consumes.

The checkpoint is id-based dedup's opposite: iDealwine's "auctions" are
price-history pages that keep gaining new adjudications over time, so the
shared ``ingest/registry.py`` dedup (id seen once -> never revisited) would
be wrong here. Instead, the manifest's ``idealwine.last_sold_at`` tracks the
latest ``sold_at`` already archived, and each run only keeps strictly newer
ones -- the same per-record date filter ``idealwine_diff.new_adjudications``
always used, just checkpointed in the manifest instead of a live DB query.

Usage:
    python3 run_idealwine_delta.py [--limit N] [--dry-run]
"""
import argparse
import json
import os
import sys
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from curl_cffi import requests

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ingest.fetchers.idealwine import IdealwineFetcher  # noqa: E402
from ingest.registry import load_manifest, save_manifest  # noqa: E402
from idealwine_diff import new_adjudications  # noqa: E402

# AGENTS.md: the archive lives on the Samsung disk, not Google Drive --
# that old default is a known footgun in build_db.py/run_ingest.py, not
# one to repeat here.
ARCHIVE = os.environ.get(
    "ARCHIVE_PATH", "/Volumes/samsung/winefeed-data/WeinAuktionspreise")
MANIFEST_PATH = os.environ.get("MANIFEST_PATH",
                               os.path.join(REPO, "data",
                                            "ingest_manifest.json"))

# Fields load_idealwine actually reads off each archived adjudication --
# everything else idealwine_diff.new_adjudications() attaches is wine
# identity used only for grouping/the file's own top-level fields here.
_ADJUDICATION_FIELDS = (
    "sold_at", "format", "number_of_bottles", "hammer_per_bottle_eur",
    "hammer_per_bottle_eur_derived", "total_per_bottle_eur", "price_basis",
    "code", "hammer_lot_eur", "buyer_premium_rate", "buyer_premium_vat",
    "anomaly_type", "derived_rate_assumed",
)
_WINE_FIELDS = ("region", "wine", "estate", "vintage", "appellation",
               "color", "classification")


def _archive_new_adjudications(archive_path, new_recs):
    """Group ``new_recs`` by (product_id, vintage) and write one archive
    file per group under IDealwine_normalized/_delta/, matching the
    existing per-product file shape load_idealwine reads."""
    groups = defaultdict(list)
    wine_fields = {}
    for rec in new_recs:
        key = (rec.get("product_id"), rec.get("vintage"))
        groups[key].append({k: rec.get(k) for k in _ADJUDICATION_FIELDS})
        wine_fields[key] = {k: rec.get(k) for k in _WINE_FIELDS}

    out_dir = os.path.join(archive_path, "IDealwine_normalized", "_delta")
    os.makedirs(out_dir, exist_ok=True)
    # Confirmed real bug: time.strftime's second resolution alone collides
    # whenever this is called twice within the same wall-clock second (e.g.
    # two quick manual runs, or two calls in the same test) -- the second
    # call's write for a repeated (product_id, vintage) key then silently
    # OVERWRITES the first call's file of the identical name instead of
    # creating a second delta file. Reproduced directly: two back-to-back
    # calls for the same key produced only one file on disk, not two. A
    # short random suffix makes the filename unique per call regardless of
    # timing.
    run_id = f"{time.strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"
    written = 0
    for (product_id, vintage), adjudications in groups.items():
        doc = dict(wine_fields[(product_id, vintage)])
        doc["product_id"] = product_id
        doc["adjudications"] = adjudications
        fname = f"{product_id}-{vintage}-{run_id}.json"
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, default=str)
        written += 1
    return written


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    fetcher = IdealwineFetcher()
    discover_session = requests.Session(impersonate="chrome")
    refs = fetcher.discover(discover_session)
    if args.limit:
        refs = refs[: args.limit]
    print(f"refs: {len(refs)}", flush=True)

    manifest = load_manifest(MANIFEST_PATH)
    last_sold_at = manifest.get("idealwine", {}).get("last_sold_at")
    print(f"last_sold_at (checkpoint): {last_sold_at}", flush=True)
    if not last_sold_at:
        print("no checkpoint in manifest; aborting without archiving "
              "(seed manifest['idealwine']['last_sold_at'] first)",
              file=sys.stderr)
        return 1
    # Confirmed real: truncating the checkpoint to a bare date (as this
    # used to, and as the existing manifest seed value still is) means
    # the *next* run's cutoff becomes that day's midnight, so any
    # adjudication sold later the *same* day is "> cutoff" again and
    # gets re-archived as a duplicate lots row (new_adjudications/
    # build_db.load_idealwine have no id-based dedup for this path,
    # unlike the old direct-DB-insert path's _lot_exists check). Full
    # ISO precision from here on closes that gap; still accepts a bare
    # date for the one pre-existing manifest seed value written before
    # this fix.
    cutoff = last_sold_at if "T" in last_sold_at else (
        f"{last_sold_at}T00:00:00+00:00")

    def _make_session():
        return requests.Session(impersonate="chrome")

    def _fetch_ref(item):
        ref, session = item
        return ref, fetcher.fetch(session, ref).data

    cotes = []
    failed = 0
    t0 = time.time()
    workers = int(os.environ.get("IDEALWINE_WORKERS", "8"))
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(_fetch_ref, (r, _make_session()))
                   for r in refs]
        for fut in as_completed(futures):
            done += 1
            try:
                _, data = fut.result()
                cotes.append(data)
            except Exception as exc:  # noqa: BLE001
                failed += 1
                print(f"  fetch failed: {exc}", flush=True)
            if done % 500 == 0:
                dt = time.time() - t0
                print(f"  {done}/{len(refs)} ({dt:.0f}s, {failed} failed)",
                      flush=True)

    print(f"fetched {len(cotes)} cotes, {failed} failed "
          f"({time.time() - t0:.0f}s)", flush=True)

    new = new_adjudications(cotes, cutoff)
    print(f"new adjudications: {len(new)}", flush=True)

    if args.dry_run:
        for r in new[:5]:
            print("  sample:", r["sold_at"], r["wine"], r["vintage"],
                  r.get("hammer_per_bottle_eur"))
        return 0

    if not new:
        manifest.setdefault("idealwine", {})["checked_at"] = (
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        save_manifest(MANIFEST_PATH, manifest)
        return 0

    written = _archive_new_adjudications(ARCHIVE, new)
    newest_sold_at = max(r["sold_at"] for r in new if r.get("sold_at"))
    entry = manifest.setdefault("idealwine", {})
    entry["checked_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if failed or args.limit:
        # Do NOT advance last_sold_at past this run's max when any cote
        # fetch failed, OR when --limit truncated `refs` to a subset of
        # all currently-offered products: either way, `new` only reflects
        # a partial sweep, so a skipped product's own newer-than-checkpoint
        # adjudication would be permanently filtered out on every future
        # run once the checkpoint moves past it (it never becomes "> last_
        # sold_at" again even once that product is fetched/succeeds).
        # Leaving the checkpoint where it was means this run's
        # already-archived adjudications may be re-fetched and
        # re-archived next run, but build_db.py's load_idealwine dedups by
        # `code` across all archive files, so that only costs a duplicate
        # archive file, not a duplicate DB row.
        print(f"{failed} cote fetch(es) failed"
              + (f" / --limit {args.limit} active" if args.limit else "")
              + f"; not advancing checkpoint past this run's max "
                f"({newest_sold_at})", flush=True)
    else:
        entry["last_sold_at"] = newest_sold_at
    save_manifest(MANIFEST_PATH, manifest)
    print(f"archived: {written} product/vintage files, checkpoint now "
          f"{entry.get('last_sold_at')}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
