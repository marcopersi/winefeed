#!/usr/bin/env python3
"""Live smoke test for the Sothebys fetcher.

Requires ``camoufox`` (solves the Turnstile login) and the credentials in
``SOTHEBYS_USER`` / ``SOTHEBYS_PWD``. Verifies the full chain: login ->
discover (Wine + Whisky & Spirits categories) -> GraphQL fetch with hammer
prices.
"""
import os
import sys

from curl_cffi import requests

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from ingest.fetchers import get  # noqa: E402

MAX_AUCTIONS = 3


def main():
    fetcher = get("sothebys")
    env = {
        "SOTHEBYS_USER": os.environ.get("SOTHEBYS_USER", ""),
        "SOTHEBYS_PWD": os.environ.get("SOTHEBYS_PWD", ""),
    }
    session = requests.Session(impersonate="chrome", timeout=30)

    if not fetcher.auth(session, env):
        print("FEHLER: Login fehlgeschlagen", file=sys.stderr)
        return 1

    refs = fetcher.discover(session)
    print(f"discover: {len(refs)} Auktionen (Wine + Whisky & Spirits)")
    if not refs:
        print("FEHLER: keine Auktionen gefunden", file=sys.stderr)
        return 1

    with_lots = 0
    with_hammer = 0
    for ref in refs[:MAX_AUCTIONS]:
        result = fetcher.fetch(session, ref)
        lots = result.data.get("lots", [])
        sold = [lot for lot in lots if lot.get("hammer")]
        print(f"  {ref.auction_id}: {len(lots)} Lots, "
              f"{len(sold)} mit Hammer")
        with_lots += 1 if lots else 0
        with_hammer += 1 if sold else 0

    if not with_lots:
        print("FEHLER: keine Auktion mit Lots", file=sys.stderr)
        return 1
    if not with_hammer:
        print("FEHLER: keine Auktion mit Hammerpreisen", file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
