#!/usr/bin/env python3
"""Christie's historical backfill: discover all past wine auctions via the
sitemap, fetch their lots, and archive them for ``build_db``.

Resumable (manifest checkpoint per auction + persisted candidate list),
rate-limited, with a circuit-breaker. Analogous to ``run_idealwine_delta.py``.

The discovery pass (loading every past-sale page to resolve the numeric
``sale_id`` and title) is the expensive part; its result is cached in
``data/christies_backfill_candidates.json`` so ``--limit`` smoke runs and the
full run do not repeat it.
"""
import argparse
import json
import os
import sys
import time

from curl_cffi import requests

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from ingest.fetchers import get  # noqa: E402
from ingest.registry import (dedup, load_manifest, mark_fetched,  # noqa: E402
                             save_manifest)
from ingest.models import AuctionRef  # noqa: E402

ARCHIVE = os.environ.get(
    "ARCHIVE_PATH",
    os.path.expanduser(
        "~/Library/CloudStorage/GoogleDrive-persi.marco@gmail.com/"
        "Meine Ablage/Wein/WeinAuktionspreise"))
MANIFEST_PATH = os.environ.get("MANIFEST_PATH",
                               os.path.join(ARCHIVE, "ingest_manifest.json"))
ARCHIVE_DIR = os.path.join(ARCHIVE, "Christies")
CANDIDATES_PATH = os.path.join(REPO, "data",
                               "christies_backfill_candidates.json")
SKIP_PATH = os.path.join(REPO, "data", "christies_backfill_skips.json")


def _load_candidates():
    if not os.path.exists(CANDIDATES_PATH):
        return None
    with open(CANDIDATES_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _save_candidates(refs):
    with open(CANDIDATES_PATH, "w", encoding="utf-8") as fh:
        json.dump([{"sale_id": r.auction_id, "url": r.url,
                    "title": r.title} for r in refs],
                  fh, ensure_ascii=False, indent=2)


def _archive(sale_id, data):
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    with open(os.path.join(ARCHIVE_DIR, f"{sale_id}.json"), "w",
              encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, default=str)


def _reason(exc):
    text = str(exc)
    if "missing meta" in text:
        return "META_MISSING"
    if "expected" in text and "lots" in text:
        return "RECONCILIATION_MISMATCH"
    if "total_hits_filtered" in text:
        return "EMPTY_RESULT"
    return "HTTP_ERROR"


def _write_skips(path, skips):
    if not skips:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(skips, fh, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="discover + N_expected, no lot fetch")
    parser.add_argument("--limit", type=int, default=None,
                        help="fetch only the first N wine auctions")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="inter-request delay in seconds")
    parser.add_argument("--max-fail", type=int, default=10,
                        help="circuit-breaker threshold")
    args = parser.parse_args()

    session = requests.Session(impersonate="chrome")
    fetcher = get("christies")

    candidates = _load_candidates()
    if candidates is None:
        refs = fetcher.discover_backfill(session)
        _save_candidates(refs)
        candidates = [{"sale_id": r.auction_id, "url": r.url,
                       "title": r.title} for r in refs]
    refs = [AuctionRef("christies", c["sale_id"], url=c["url"],
                       title=c.get("title")) for c in candidates]

    manifest = load_manifest(MANIFEST_PATH)
    new_refs = dedup(refs, manifest, "christies")
    print(f"Wine & Spirits (N_expected): {len(refs)}")
    print(f"Neu zu fetchen: {len(new_refs)}")

    if args.dry_run:
        for ref in new_refs:
            print(f"  {ref.auction_id}  {ref.title or ''}")
        return 0

    fetched = 0
    skips = []
    consecutive = 0
    targets = new_refs[:args.limit] if args.limit else new_refs
    for i, ref in enumerate(targets, 1):
        try:
            result = fetcher.fetch(session, ref)
            _archive(ref.auction_id, result.data)
            mark_fetched(manifest, ref)
            save_manifest(MANIFEST_PATH, manifest)
            fetched += 1
            consecutive = 0
            print(f"[{i}/{len(targets)}] sale_id={ref.auction_id} "
                  f"lots={len(result.data.get('lots', []))} OK", flush=True)
        except Exception as exc:  # noqa: BLE001
            consecutive += 1
            skips.append({"sale_id": ref.auction_id,
                          "reason": _reason(exc),
                          "detail": str(exc)[:200]})
            print(f"[{i}/{len(targets)}] sale_id={ref.auction_id} "
                  f"SKIP {exc}", flush=True)
            if consecutive >= args.max_fail:
                print(f"Circuit-Breaker: {args.max_fail} konsekutive Fehler",
                      file=sys.stderr)
                break
        time.sleep(args.delay)

    _write_skips(SKIP_PATH, skips)
    print(f"Erfolgreich: {fetched} | Skip: {len(skips)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
