#!/usr/bin/env python3
"""Run the incremental iDealwine cote delta against the master database.

Enumerates currently offered lots via Algolia, loads each cote through the
Next.js SSR route, selects only adjudications newer than the latest recorded
``lot_date``, and appends them to the master DB (deduplicated by
``source_lot_key``).

Usage:
    python3 run_idealwine_delta.py [--limit N] [--dry-run]

Credentials are read from the repo root ``.env_local`` (``IDEALWINE_CF_CLEARANCE``).
"""
import argparse
import os
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ingest.fetchers.idealwine import IdealwineFetcher  # noqa: E402
from idealwine_diff import insert_new_lots, new_adjudications  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get(
    "DB_PATH", "/Volumes/samsung/winefeed-data/wine_auction_prices.sqlite")


def _env():
    env = {}
    path = os.path.join(REPO, ".env_local")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def _last_sold_at(conn):
    row = conn.execute(
        "SELECT MAX(lot_date) FROM lots WHERE auction_id IN "
        "(SELECT id FROM auctions WHERE provider_id = "
        "(SELECT id FROM providers WHERE name = 'idealwine'))").fetchone()
    return row[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    env = _env()
    cf = env.get("IDEALWINE_CF_CLEARANCE")
    if not cf:
        print("IDEALWINE_CF_CLEARANCE missing in .env_local", file=sys.stderr)
        return 2

    fetcher = IdealwineFetcher()
    discover_session = requests.Session()
    discover_session.headers["User-Agent"] = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15")
    discover_session.cookies.set("cf_clearance", cf, domain=".idealwine.com")
    refs = fetcher.discover(discover_session)
    if args.limit:
        refs = refs[: args.limit]
    print(f"refs: {len(refs)}", flush=True)

    conn = sqlite3.connect(DB_PATH)
    last_sold_at = _last_sold_at(conn)
    print(f"last_sold_at: {last_sold_at}", flush=True)
    cutoff = f"{last_sold_at}T00:00:00+00:00" if last_sold_at else None

    def _make_session():
        s = requests.Session()
        s.headers["User-Agent"] = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15")
        s.cookies.set("cf_clearance", cf, domain=".idealwine.com")
        return s

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
                ref, data = fut.result()
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

    if cutoff is None:
        print("no last_sold_at; aborting without insert", file=sys.stderr)
        return 1

    new = new_adjudications(cotes, cutoff)
    print(f"new adjudications: {len(new)}", flush=True)

    if args.dry_run:
        for r in new[:5]:
            print("  sample:", r["sold_at"], r["wine"], r["vintage"],
                  r.get("hammer_per_bottle_eur"))
        conn.close()
        return 0

    inserted = insert_new_lots(conn, new)
    conn.commit()
    conn.close()
    print(f"inserted: {inserted}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
