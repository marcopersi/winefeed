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
from ingest.fetchers.christies import (MalformedResponse, MetaInvalid,  # noqa: E402
                                       ReconciliationMismatch)
from ingest.registry import (dedup, load_manifest, mark_fetched,  # noqa: E402
                             save_manifest)
from ingest.models import AuctionRef  # noqa: E402
from orchestrate import ARCHIVE_DIRS  # noqa: E402

ARCHIVE = os.environ.get(
    "ARCHIVE_PATH",
    os.path.expanduser(
        "~/Library/CloudStorage/GoogleDrive-persi.marco@gmail.com/"
        "Meine Ablage/Wein/WeinAuktionspreise"))
# Single shared manifest with the monthly CI ingest (D2): both write/read
# data/ingest_manifest.json so the backfill and the cron run dedupe against the
# same state and do not double-fetch.
MANIFEST_PATH = os.environ.get("MANIFEST_PATH",
                               os.path.join(REPO, "data",
                                            "ingest_manifest.json"))
ARCHIVE_DIR = os.path.join(ARCHIVE, ARCHIVE_DIRS["christies"])
CANDIDATES_PATH = os.path.join(REPO, "data",
                               "christies_backfill_candidates.json")
AMBIGUOUS_PATH = os.path.join(REPO, "data",
                              "christies_backfill_ambiguous.json")
SKIP_PATH = os.path.join(REPO, "data", "christies_backfill_skips.json")

# Skip reasons that are terminal for historical auctions (won't change on retry).
TERMINAL_SKIP_REASONS = {"EMPTY_RESULT"}


def _load_candidates():
    if not os.path.exists(CANDIDATES_PATH):
        return None
    with open(CANDIDATES_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict) and not data.get("complete"):
        print("Warnung: vorherige Discovery war unvollständig, "
              "starte neu", flush=True)
        return None
    if isinstance(data, dict):
        return data.get("candidates", [])
    return data


def _save_candidates(refs, ambiguous):
    with open(CANDIDATES_PATH, "w", encoding="utf-8") as fh:
        json.dump({
            "generated_at": _now(),
            "n_wine_refs": len(refs),
            "n_ambiguous": len(ambiguous),
            "complete": True,
            "candidates": [{"sale_id": r.auction_id, "url": r.url,
                            "title": r.title} for r in refs],
        }, fh, ensure_ascii=False, indent=2)
    if ambiguous:
        with open(AMBIGUOUS_PATH, "w", encoding="utf-8") as fh:
            json.dump(ambiguous, fh, ensure_ascii=False, indent=2)
        print(f"Ambiguous Titel: {len(ambiguous)} → {AMBIGUOUS_PATH}",
              flush=True)


def _archive(sale_id, data):
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    with open(os.path.join(ARCHIVE_DIR, f"{sale_id}.json"), "w",
              encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, default=str)


def _reason(exc):
    if isinstance(exc, MetaInvalid):
        return "META_INVALID"
    if isinstance(exc, ReconciliationMismatch):
        return "RECONCILIATION_MISMATCH"
    if isinstance(exc, MalformedResponse):
        return "MALFORMED_RESPONSE"
    return "HTTP_ERROR"


def _load_skips():
    if not os.path.exists(SKIP_PATH):
        return {}
    with open(SKIP_PATH, encoding="utf-8") as fh:
        return {s["sale_id"]: s for s in json.load(fh)}


def _write_skips(path, skips_by_id):
    if not skips_by_id:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ordered = [skips_by_id[k] for k in sorted(skips_by_id)]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(ordered, fh, ensure_ascii=False, indent=2)


def _now():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


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
        refs, ambiguous = fetcher.discover_backfill(
            session, delay=args.delay, max_fail=args.max_fail)
        _save_candidates(refs, ambiguous)
        candidates = [{"sale_id": r.auction_id, "url": r.url,
                       "title": r.title} for r in refs]
    refs = [AuctionRef("christies", c["sale_id"], url=c["url"],
                       title=c.get("title")) for c in candidates]

    manifest = load_manifest(MANIFEST_PATH)
    skips = _load_skips()
    terminal_ids = {sid for sid, s in skips.items()
                    if s.get("reason") in TERMINAL_SKIP_REASONS}
    new_refs = [r for r in dedup(refs, manifest, "christies")
                if r.auction_id not in terminal_ids]
    print(f"Wine & Spirits (N_expected): {len(refs)}")
    print(f"Neu zu fetchen: {len(new_refs)}")

    if args.dry_run:
        for ref in new_refs:
            print(f"  {ref.auction_id}  {ref.title or ''}")
        return 0

    fetched = 0
    this_run_skips = 0
    consecutive = 0
    aborted = False
    targets = new_refs[:args.limit] if args.limit else new_refs
    try:
        for i, ref in enumerate(targets, 1):
            try:
                result = fetcher.fetch(session, ref)
                if not result.data.get("lots"):
                    skips[ref.auction_id] = {
                        "sale_id": ref.auction_id, "reason": "EMPTY_RESULT",
                        "detail": "total_hits_filtered=0"}
                    this_run_skips += 1
                    print(f"[{i}/{len(targets)}] sale_id={ref.auction_id} "
                          "SKIP empty", flush=True)
                    continue
                _archive(ref.auction_id, result.data)
                mark_fetched(manifest, ref)
                save_manifest(MANIFEST_PATH, manifest)
                skips.pop(ref.auction_id, None)
                fetched += 1
                consecutive = 0
                print(f"[{i}/{len(targets)}] sale_id={ref.auction_id} "
                      f"lots={len(result.data.get('lots', []))} OK",
                      flush=True)
            except Exception as exc:  # noqa: BLE001
                consecutive += 1
                this_run_skips += 1
                skips[ref.auction_id] = {
                    "sale_id": ref.auction_id,
                    "reason": _reason(exc),
                    "detail": str(exc)[:200]}
                print(f"[{i}/{len(targets)}] sale_id={ref.auction_id} "
                      f"SKIP {exc}", flush=True)
                if consecutive >= args.max_fail:
                    print(f"Circuit-Breaker: {args.max_fail} konsekutive "
                          "Fehler", file=sys.stderr)
                    aborted = True
                    break
            finally:
                time.sleep(args.delay)
    finally:
        _write_skips(SKIP_PATH, skips)

    print(f"Erfolgreich: {fetched} | Skip (dieser Lauf): {this_run_skips} "
          f"| Skip (gesamt): {len(skips)}")
    return 1 if aborted else 0


if __name__ == "__main__":
    sys.exit(main())
