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


LAST_RUN_KEY = "__last_run_at__"
_MAX_SEQUENCE_SPAN = 100_000


def sequence_gaps(manifest, provider):
    """Return the sorted list of missing integer auction_ids between the
    smallest and largest PURELY NUMERIC id this provider's manifest entry
    has ever recorded.

    Confirmed real finding (2026-11-25 Phase-2 audit): weinauktionator ids
    23 and 27 were never fetched at all -- the house's results page only
    ever lists a small rolling window of the most recent auctions, so an
    id that didn't fall inside that window during any of our monthly runs
    is silently gone (404 on the direct download URL, no Wayback Machine
    snapshot either -- genuinely unrecoverable, not just undiscovered).
    That sat unnoticed for an unknown number of months because nothing
    ever compared the numeric id sequence against what was actually
    fetched. This makes the next such gap visible immediately instead.

    Only returns a meaningful result for providers whose auction_ids are
    plain increasing integers (most of them); a provider using dates or
    composite ids simply has zero numeric ids and gets an empty result,
    not a false positive.

    Review finding (2026-11-25): a single bad numeric key (a manual-edit
    typo, a parsing glitch) would otherwise size the ``range``/``set``
    below off that one outlier, with no bound -- a provider's real ids
    never span more than a few thousand, so a span past
    ``_MAX_SEQUENCE_SPAN`` is treated as corrupt manifest data rather
    than a real gap to report.
    """
    entries = manifest.get(provider, {})
    ids = sorted(int(k) for k in entries if k != LAST_RUN_KEY and k.isdigit())
    if len(ids) < 2 or ids[-1] - ids[0] > _MAX_SEQUENCE_SPAN:
        return []
    full_range = set(range(ids[0], ids[-1] + 1))
    return sorted(full_range - set(ids))


def get_last_run(manifest, provider):
    """Return the last successful run timestamp for ``provider`` or ``None``."""
    return manifest.get(provider, {}).get(LAST_RUN_KEY)


def set_last_run(manifest, provider, timestamp=None):
    """Record the current time as the last successful run for ``provider``."""
    manifest.setdefault(provider, {})[LAST_RUN_KEY] = timestamp or _now()


def _now():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
