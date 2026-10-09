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
MANIFEST_PATH = os.environ.get("MANIFEST_PATH",
                               os.path.join(ARCHIVE, "ingest_manifest.json"))

PROVIDERS = [
    "steinfels", "weinboerse", "weinauktionator", "hdh", "koppe", "idealwine",
    "langtons", "winefields", "dorotheum", "pandolfini",
    # Sothebys needs camoufox (heavy) + a residential IP to solve the
    # Cloudflare Turnstile login; it only runs locally, not in CI.
    "sothebys",
]


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
    prefixes = ("IDEALWINE_", "PANDOLFINI_", "SOTHEBYS_", "FINARTE_")
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
