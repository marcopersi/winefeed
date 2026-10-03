"""Delta-run orchestrator.

Loads the manifest, enumerates a house's auctions, fetches only the ones not
yet recorded, persists each result to the archive, and advances the last-run
marker for that provider.
"""
import json
import os

from .fetchers import get
from .registry import (dedup, load_manifest, mark_fetched, save_manifest,
                       set_last_run)


def run_provider(provider, session, manifest_path, archive_dir):
    """Fetch and persist all new auctions of ``provider``.

    Returns the number of newly fetched auctions.
    """
    manifest = load_manifest(manifest_path)
    fetcher = get(provider)
    refs = fetcher.discover(session)
    new_refs = dedup(refs, manifest, provider)

    fetched = 0
    for ref in new_refs:
        result = fetcher.fetch(session, ref)
        _save_result(archive_dir, result)
        mark_fetched(manifest, ref)
        fetched += 1

    set_last_run(manifest, provider)
    save_manifest(manifest_path, manifest)
    return fetched


def _save_result(archive_dir, result):
    os.makedirs(archive_dir, exist_ok=True)
    filename = f"{result.provider}__{result.auction_id}.json"
    with open(os.path.join(archive_dir, filename), "w",
              encoding="utf-8") as fh:
        json.dump(result.data, fh, ensure_ascii=False, default=str)
