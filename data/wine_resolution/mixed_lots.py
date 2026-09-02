"""Mixed-lot classification.

A mixed lot is a single auction lot that contains several different wines or
vintages. Its single hammer price cannot be attributed to one wine, so mixed
lots are excluded from price analysis (``wine_ref_id IS NULL``).

Classification operates on a *source lot group*: all rows sharing
``provider_id + auction_id + lot_no`` (or ``source_file`` + locator when
``lot_no`` is missing).
"""
import re

KIND_SINGLE = "SINGLE"
KIND_MIXED = "MIXED"
KIND_UNKNOWN = "UNKNOWN"

_KEYWORD = re.compile(r"\b(mixed\s+lot|mixed\s+case|assortment|selection)\b",
                      re.IGNORECASE)


def classify_group(lots):
    """Classify a source-lot group.

    ``lots`` is a list of dicts with keys: ``wine``, ``wine_key``, ``vintage``,
    ``mixed_lot`` (provider flag), ``description``.

    Returns ``(lot_kind, reason, rule_id)``.
    """
    # 1. Provider flag wins.
    if any(l.get("mixed_lot") == 1 for l in lots):
        return KIND_MIXED, "provider-flag", "provider-flag"

    # 2. Keyword evidence across the whole group.
    for l in lots:
        text = " ".join(x for x in (l.get("wine") or "",
                                    l.get("description") or "") if x)
        if _KEYWORD.search(text):
            return KIND_MIXED, "keyword-evidence", "keyword-evidence"

    # 3. Distinct valid wine keys in the group.
    keys = set(l.get("wine_key") or "" for l in lots)
    keys.discard("")
    if len(keys) > 1:
        return KIND_MIXED, "multiple-wines", "multiple-wines"

    # 4. Single wine name but multiple vintages.
    if len(keys) == 1:
        vintages = set(l.get("vintage") for l in lots
                       if l.get("vintage") is not None)
        if len(vintages) > 1:
            return KIND_MIXED, "multiple-vintages", "multiple-vintages"
        return KIND_SINGLE, None, "single-wine"

    return KIND_UNKNOWN, "no-wine-name", "no-wine-name"
