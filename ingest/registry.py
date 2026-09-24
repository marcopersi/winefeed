"""Manifest persistence and dedup.

The manifest records which auctions we have already fetched, so that only new
auctions are downloaded. Schema: ``{provider: {auction_id: {url, etag,
fetched_at}}}``.
"""
import json
import os


def load_manifest(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save_manifest(path, manifest):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2, sort_keys=True)


def dedup(refs, manifest, provider):
    """Return only the auction refs of ``provider`` not yet in the manifest."""
    seen = manifest.get(provider, {})
    return [r for r in refs if r.auction_id not in seen]


def mark_fetched(manifest, ref, etag=None):
    provider_entries = manifest.setdefault(ref.provider, {})
    provider_entries[ref.auction_id] = {
        "url": ref.url,
        "etag": etag or ref.etag,
        "fetched_at": _now(),
    }


def _now():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
