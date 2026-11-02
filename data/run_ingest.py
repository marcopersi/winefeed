#!/usr/bin/env python3
"""Run the monthly ingest for all (or selected) houses.

Fetches new auctions, parses file-based results, and archives them into the
``ARCHIVE_PATH`` tree that ``build_db.py`` reads. Login credentials are read
from ``.env_local`` / env vars; HTTP uses ``curl_cffi`` with browser
impersonation so Cloudflare challenges are solved automatically (no cookie
secrets needed).
"""
import argparse
import os
import sys

from curl_cffi import requests

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from orchestrate import run_provider  # noqa: E402
ARCHIVE = os.environ.get(
    "ARCHIVE_PATH",
    os.path.expanduser(
        "~/Library/CloudStorage/GoogleDrive-persi.marco@gmail.com/"
        "Meine Ablage/Wein/WeinAuktionspreise"))
# Single shared manifest (D2): local runs and the CI ingest both read/write
# data/ingest_manifest.json so they dedupe against the same state.
MANIFEST_PATH = os.environ.get("MANIFEST_PATH",
                               os.path.join(REPO, "data",
                                            "ingest_manifest.json"))

PROVIDERS = [
    "steinfels", "weinboerse", "weinauktionator", "hdh", "koppe",
    "langtons", "winefields", "dorotheum", "pandolfini",
    "finarte", "besch-cannes", "dobiaschofsky", "winebarrel",
    "denzauktionen", "munich-wine-company", "franzwermuth", "baghera",
    # christies: plain curl_cffi scrape, no login, no WAF -- discover() was
    # rebuilt Nov 2026 (christies.com moved to the Next.js App Router,
    # breaking the old regex) to read /en/calendar, which already dedupes
    # correctly against the same shared manifest as the historical
    # backfill (run_christies_backfill.py), so running both is safe.
    "christies",
    # Sothebys needs camoufox (heavy) + a residential IP to solve the
    # Cloudflare Turnstile login; it only runs locally, not in CI.
    "sothebys",
    # sylvies needs camoufox too (Azure WAF JS challenge), but only for the
    # one-time login -- cookies then survive on a plain curl_cffi session
    # for every subsequent request (see ingest/fetchers/sylvies.py). camoufox
    # isn't in data/requirements.txt (not installed in CI), and whether the
    # WAF challenge itself would even pass from a GitHub Actions runner IP
    # is unverified -- so, like sothebys, this runs locally only for now.
    "sylvies",
]
# christies IS in PROVIDERS now (Nov 2026) -- see the comment on its entry
# above. run_christies_backfill.py remains for occasional re-backfills; it
# shares the same manifest so the two never double-fetch.
# idealwine is deliberately not listed: it runs via run_idealwine_delta.py
# (Algolia -> normalize -> diff -> direct DB append), not the build_db chain.


def _env():
    env = {}
    path = os.path.join(REPO, ".env_local")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    prefixes = ("IDEALWINE_", "PANDOLFINI_", "SOTHEBYS_", "FINARTE_",
                "SYLVIES_")
    env.update({k: v for k, v in os.environ.items()
                if k.startswith(prefixes)})
    return env


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", type=str, default=None,
                        help="comma-separated provider names to run")
    args = parser.parse_args()

    providers = [p for p in (args.only.split(",") if args.only else PROVIDERS)
                 if p]

    env = _env()
    session = requests.Session(impersonate="chrome")

    results = {}
    for provider in providers:
        try:
            n = run_provider(provider, session, MANIFEST_PATH, ARCHIVE, env)
            results[provider] = ("ok", n)
            print(f"{provider}: {n} neu", flush=True)
        except Exception as exc:  # noqa: BLE001
            results[provider] = ("failed", str(exc))
            print(f"{provider}: FEHLER {exc}", flush=True)

    failed = [p for p, (s, _) in results.items() if s == "failed"]
    if failed:
        print(f"fehlgeschlagen: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
