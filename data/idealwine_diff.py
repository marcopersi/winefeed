"""Incremental iDealwine cote diff: transform and filter new adjudications.

The fetcher loads each currently-offered lot's cote (``lastAdjudications`` +
``productVintageRatings``) from the Next.js page's dehydrated React-Query
cache, plus a ``meta`` dict carrying the wine identity and bottle
count/format the site no longer attaches per-sale (see
``ingest/fetchers/idealwine.py``). This module selects only the
adjudications newer than the last recorded ``soldAt`` and maps them onto
the raw normalize format, reusing the shared premium/hammer classification.
``data/run_idealwine_delta.py`` archives what this returns as per-product
JSON under ``IDealwine_normalized/_delta/`` for ``build_db.py``'s
``load_idealwine`` to pick up on the next full rebuild -- this module itself
no longer touches the DB directly (it used to, via a now-removed
``insert_new_lots``/``Builder`` direct-insert path, before iDealwine moved
onto the same archive-then-rebuild pipeline every other house uses so it
could run as an ordinary CI step without DB access).

The site no longer exposes a per-sale hammer price (only ``historicPrice``,
the total incl. premium) -- ``normalize_adjudication``'s existing
"hammer is None" fallback (a date-based assumed premium rate) now applies to
every idealwine record, not just the rare case it used to cover.
"""
from idealwine_normalize import DUCLOT_PIDS, normalize_adjudication


def _cents_to_eur(v):
    return v / 100.0 if v is not None else None


def transform_last_adjudication(last_adj, meta):
    """Map one ``lastAdjudication`` (+ its cote's ``meta``) to the raw
    normalize format."""
    return {
        "sold_at": last_adj.get("soldAt"),
        "bottles": meta.get("bottles"),
        "hammer_eur": _cents_to_eur(last_adj.get("price")),
        "total_eur": _cents_to_eur(last_adj.get("historicPrice")),
        "format": meta.get("format"),
        "code": (str(last_adj["id"]) if last_adj.get("id") is not None
                 else None),
        "product_id": meta.get("product_id"),
        "wine": meta.get("wine"),
        "estate": meta.get("estate"),
        "vintage": meta.get("vintage"),
        "region": meta.get("region"),
        "appellation": meta.get("appellation"),
        "color": meta.get("color"),
        "classification": meta.get("classification"),
    }


def _cote_context(cote):
    """Return (current_rating_eur, annual_ratings_eur) from one cote record.

    ``current_rating_eur`` is always ``None`` now -- the site dropped
    ``currentYearRating`` from this query. Confirmed real: the
    ``yr``/``yr-1``/``yr+1`` checks against ``annual`` in
    ``normalize_adjudication`` do NOT pick up the slack -- that whole branch
    (``is_cote``/``COTE_AS_HISTORIC``, and the Duclot ``MIXED_CASE`` guard
    and premium-rate classification below it) only runs when ``hammer`` is
    not ``None``, and every idealwine adjudication now has ``hammer_eur =
    None`` (the site no longer exposes a per-sale hammer price at all, see
    the module docstring), so ``normalize_adjudication`` always takes the
    "hammer is None" early-return branch first. ``annual`` is still computed
    here but currently has no consumer for idealwine records; kept because
    ``normalize_adjudication`` is shared with ``normalize_idealwine.py``,
    which still calls it with a real ``cote`` where that branch is live.
    """
    annual = {}
    for r in cote.get("productVintageRatings") or []:
        if isinstance(r, dict) and r.get("year") is not None:
            annual[r["year"]] = _cents_to_eur(r.get("value"))
    return None, annual


def new_adjudications(cote_list, last_sold_at):
    """Return normalized adjudications newer than ``last_sold_at``.

    Each returned record carries the normalized price fields plus the wine
    identity fields needed to insert a lot.
    """
    out = []
    for cote in cote_list:
        meta = cote.get("meta") or {}
        is_duclot = meta.get("product_id") in DUCLOT_PIDS
        current, annual = _cote_context(cote)
        for adj in cote.get("lastAdjudications") or []:
            raw = transform_last_adjudication(adj, meta)
            sold_at = raw.get("sold_at")
            if not sold_at or sold_at <= last_sold_at:
                continue
            rec, _ = normalize_adjudication(raw, is_duclot, current, annual)
            if is_duclot and rec.get("anomaly_type") is None:
                # The site no longer exposes a per-sale hammer price (see
                # the module docstring), so hammer is always None now and
                # normalize_adjudication's "hammer is None" early-return
                # fires before it ever reaches the is_duclot/MIXED_CASE
                # check below it -- re-apply the flag here so a Duclot
                # mixed-case product's meaningless per-bottle-derived price
                # is still marked as such instead of looking like a normal
                # per-bottle sale.
                rec["anomaly_type"] = "MIXED_CASE"
            rec.update({
                "product_id": raw["product_id"],
                "wine": raw["wine"],
                "estate": raw["estate"],
                "vintage": raw["vintage"],
                "region": raw["region"],
                "appellation": raw["appellation"],
                "color": raw["color"],
                "classification": raw["classification"],
            })
            out.append(rec)
    return out


