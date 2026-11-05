#!/usr/bin/env python3
"""bestwineauctions.com historical backfill: discover() unbounded (no
recency cutoff) across every category, then fetch and archive every closed
lot. Analogous to ``run_christies_backfill.py``.

The regular monthly CI step (``run_ingest.py``'s "bestwineauctions" entry)
uses the same fetcher's recency-gated ``discover()`` (only re-renders back
to ``cutoff_days`` -- a full category can have 100+ pages, so scanning all
of them every month for a handful of new closures would be far too slow).
This script instead calls ``discover_backfill()`` once to find everything,
ever. Resumable: discovery is cached to
``data/bestwineauctions_backfill_candidates.json`` so a ``--limit`` smoke
run and the full run don't repeat the (slow, many-page) crawl, and fetched
lots are checked off in the SAME shared manifest the monthly step uses, so
the two never double-fetch.
"""
import argparse
import json
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from ingest.fetchers import get  # noqa: E402
from ingest.registry import dedup, load_manifest, mark_fetched, save_manifest  # noqa: E402
from orchestrate import ARCHIVE_DIRS  # noqa: E402

# AGENTS.md: the archive lives on the Samsung disk, not Google Drive --
# that old default is a known footgun in build_db.py/run_ingest.py, not
# one to repeat here.
ARCHIVE = os.environ.get(
    "ARCHIVE_PATH", "/Volumes/samsung/winefeed-data/WeinAuktionspreise")
MANIFEST_PATH = os.environ.get("MANIFEST_PATH",
                               os.path.join(REPO, "data",
                                            "ingest_manifest.json"))
ARCHIVE_DIR = os.path.join(ARCHIVE, ARCHIVE_DIRS["bestwineauctions"])
CANDIDATES_PATH = os.path.join(
    REPO, "data", "bestwineauctions_backfill_candidates.json")


def _load_candidates():
    if not os.path.exists(CANDIDATES_PATH):
        return None
    with open(CANDIDATES_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    if not data.get("complete"):
        print("Warnung: vorherige Discovery war unvollständig, starte neu",
              flush=True)
        return None
    return data["candidates"]


def _save_candidates(refs):
    with open(CANDIDATES_PATH, "w", encoding="utf-8") as fh:
        json.dump({
            "generated_at": _now(),
            "complete": True,
            "candidates": [{"auction_id": r.auction_id, "url": r.url,
                            "title": r.title} for r in refs],
        }, fh, ensure_ascii=False, indent=2)


def _archive(lot_id, data):
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    with open(os.path.join(ARCHIVE_DIR, f"{lot_id}.json"), "w",
              encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, default=str)


def _now():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="discover only, no fetch")
    parser.add_argument("--limit", type=int, default=None,
                        help="fetch only the first N lots")
    parser.add_argument("--delay", type=float, default=0.2,
                        help="inter-request delay in seconds")
    parser.add_argument("--max-fail", type=int, default=10,
                        help="circuit-breaker threshold")
    args = parser.parse_args()

    from ingest.models import AuctionRef
    fetcher = get("bestwineauctions")

    candidates = _load_candidates()
    if candidates is None:
        print("Discovery (unbounded, every category) -- this is the slow "
              "part, cached afterwards...", flush=True)
        refs = fetcher.discover_backfill(session=None)
        _save_candidates(refs)
        candidates = [{"auction_id": r.auction_id, "url": r.url,
                       "title": r.title} for r in refs]
    refs = [AuctionRef("bestwineauctions", c["auction_id"], url=c["url"],
                       title=c.get("title")) for c in candidates]

    manifest = load_manifest(MANIFEST_PATH)
    new_refs = dedup(refs, manifest, "bestwineauctions")
    print(f"Lots gesamt: {len(refs)} | neu zu fetchen: {len(new_refs)}")

    if args.dry_run:
        return 0

    targets = new_refs[:args.limit] if args.limit else new_refs
    fetched, skipped = 0, 0
    consecutive = 0
    aborted = False
    # Confirmed real: save_manifest() re-serializes and rewrites the WHOLE
    # shared ingest_manifest.json (every provider's entries, not just
    # bestwineauctions') on every single successful fetch. For a one-time
    # backfill of thousands of lots (bestwineauctions alone already has
    # 8600+) that's thousands of full-file rewrites of a multi-MB file
    # instead of one. Saved periodically instead -- still frequently enough
    # that a crash/kill mid-run only re-fetches a small tail next time
    # (mark_fetched's own dedup makes a re-fetch merely wasteful, never
    # incorrect), and always on the last iteration/circuit-breaker abort so
    # no run ever ends without its final progress persisted.
    SAVE_EVERY = 20
    for i, ref in enumerate(targets, 1):
        try:
            result = fetcher.fetch(None, ref)
            _archive(ref.auction_id, result.data)
            mark_fetched(manifest, ref)
            fetched += 1
            consecutive = 0
            print(f"[{i}/{len(targets)}] lot={ref.auction_id} OK",
                  flush=True)
        except Exception as exc:  # noqa: BLE001
            skipped += 1
            consecutive += 1
            print(f"[{i}/{len(targets)}] lot={ref.auction_id} SKIP {exc}",
                  flush=True)
            # Confirmed real gap (unlike its stated analog
            # run_christies_backfill.py): no circuit-breaker meant a
            # systemic failure (e.g. the shared Playwright browser
            # getting into a bad state) would burn through every
            # remaining lot one slow _render() timeout-and-retry at a
            # time instead of aborting early.
            if consecutive >= args.max_fail:
                print(f"Circuit-Breaker: {args.max_fail} konsekutive "
                      "Fehler, Abbruch", file=sys.stderr)
                aborted = True
        if i % SAVE_EVERY == 0 or aborted or i == len(targets):
            save_manifest(MANIFEST_PATH, manifest)
        if aborted:
            break
        time.sleep(args.delay)

    print(f"Erfolgreich: {fetched} | Skip: {skipped}")
    return 1 if aborted else 0


if __name__ == "__main__":
    sys.exit(main())
