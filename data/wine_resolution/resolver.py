"""Automatic resolution of wine aliases into canonical wines.

Only conflict-free observations are resolved automatically. Ambiguity is
preserved as ``AMBIGUOUS`` — never resolved via "first wins".
"""
import hashlib
from collections import Counter

from .canonical import choose_canonical

STATUS_RESOLVED = "RESOLVED"
STATUS_AMBIGUOUS = "AMBIGUOUS"
STATUS_UNRESOLVED = "UNRESOLVED"
STATUS_IGNORED = "IGNORED"


def stable_key(canonical_key, producer_key="", appellation_key=""):
    """Deterministic stable identity key."""
    raw = f"{canonical_key}|{producer_key or ''}|{appellation_key or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def discriminator(producer_key=""):
    """Discriminator that keeps ambiguous aliases apart."""
    return producer_key or ""


def resolve_group(observations, idealwine_name=None):
    """Resolve one alias_key group.

    ``observations`` is a list of dicts with ``alias_raw``, ``alias_key``,
    ``producer_key``, ``producer_raw``, ``region_key``, ``region_raw``,
    ``evidence_count``.

    Returns a dict with ``status``, ``reason`` and, when resolved,
    ``canonical_name``, ``producer``, ``region`` and ``discriminator_key``.
    """
    producers = {o.get("producer_key") or "" for o in observations}
    producers.discard("")

    if len(producers) > 1:
        return {
            "status": STATUS_AMBIGUOUS,
            "reason": "conflicting-producer",
            "canonical_name": None, "producer": None, "region": None,
            "discriminator_key": discriminator(),
        }
    # Region is intentionally NOT a discriminator: the fetchers record
    # inconsistent granularity ("", "bordeaux", "pomerol", "francia bordeaux")
    # for the same wine, so a region conflict does not indicate a real
    # ambiguity. We rely on alias_key + producer to keep distinct wines apart
    # and keep the most frequent region as a display hint only.

    candidates = [(o["alias_raw"], o.get("evidence_count") or 0)
                  for o in observations]
    canonical = choose_canonical(candidates, idealwine_name)
    producer = next((o.get("producer_raw") for o in observations
                     if o.get("producer_raw")), None)
    region_counts = Counter(o.get("region_raw") for o in observations
                            if o.get("region_raw"))
    region = (sorted(region_counts, key=lambda k: (-region_counts[k], k))[0]
              if region_counts else None)
    return {
        "status": STATUS_RESOLVED,
        "reason": "consistent",
        "canonical_name": canonical,
        "producer": producer,
        "region": region,
        "discriminator_key": discriminator(next(iter(producers), "")),
    }
