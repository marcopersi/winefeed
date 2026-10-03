"""Shared normalization for one iDealwine adjudication.

Extracted from ``normalize_idealwine.py`` so both the offline normalizer and
the incremental diff/ingest path use the same premium/hammer classification.

The raw extractor mislabeled two API fields:
  - ``price`` (cents)        -> ``hammer_eur``: lot hammer total.
  - ``historicPrice`` (cents)-> ``total_eur``: per-bottle incl. premium.
"""

# "Caisse Duclot" / "Caisse Prestige Duclot" mixed cases: ``numberOfBottles``
# reflects a crate count, not a bottle count. The per-bottle derivation is
# therefore meaningless for these products.
DUCLOT_PIDS = {
    125289, 125290, 125293, 125294, 125295, 125296, 125297, 125298, 125299,
    126789, 134409, 136369, 158149, 182389, 187452, 199789, 199790, 213689,
    504627,
}

EPS = 0.02  # EUR tolerance for "value equals a rating" checks


def round2(x):
    return round(x, 2)


def normalize_adjudication(a, is_duclot, cote, annual):
    """Normalize one raw adjudication.

    ``a`` is a raw adjudication dict with ``sold_at``, ``bottles``,
    ``hammer_eur``, ``total_eur``, ``format`` and ``code``. Returns
    ``(record, class_code)`` where ``class_code`` is the classification used
    for summary statistics.
    """
    sold_at = a.get("sold_at")
    bottles = a.get("bottles")
    hammer = a.get("hammer_eur")       # price/100  (lot total)
    total = a.get("total_eur")         # historicPrice/100 (per-bottle incl.)

    rec = {
        "sold_at": sold_at,
        "format": a.get("format"),
        "number_of_bottles": bottles,
        "hammer_lot_eur": hammer,
        "hammer_per_bottle_eur": None,
        "total_per_bottle_eur": total,
        "price_basis": None,
        "buyer_premium_rate": None,
        "buyer_premium_vat": None,
        "anomaly_type": None,
        "hammer_per_bottle_eur_derived": None,
        "derived_rate_assumed": None,
        "code": a.get("code"),
    }

    if hammer is None:
        rec["price_basis"] = "HAMMER_PLUS_BUYERS_PREMIUM"
        if sold_at:
            if sold_at >= "2026-04-01":
                rate, vat = 0.258, "TTC"
            elif sold_at >= "2024-01-01":
                rate, vat = 0.252, "TTC"
            else:
                rate, vat = None, None
        else:
            rate, vat = None, None
        if rate is not None and total is not None:
            rec["hammer_per_bottle_eur_derived"] = round2(total / (1 + rate))
            rec["derived_rate_assumed"] = True
        rec["buyer_premium_rate"] = rate
        rec["buyer_premium_vat"] = vat
        return rec, "price_null"

    rec["price_basis"] = "HAMMER"

    if is_duclot:
        rec["anomaly_type"] = "MIXED_CASE"
        return rec, "mixed_case"

    factor = round(total * bottles / hammer, 4)

    is_cote = False
    if factor < 1.10 and total is not None:
        yr = int(sold_at[:4]) if sold_at and sold_at[:4].isdigit() else 0
        if cote is not None and abs(total - cote) < EPS:
            is_cote = True
        for check_yr in (yr, yr - 1, yr + 1):
            if check_yr in annual and abs(total - annual[check_yr]) < EPS:
                is_cote = True

    if is_cote:
        rec["anomaly_type"] = "COTE_AS_HISTORIC"
        class_code = "cote_as_historic"
    elif 1.2510 <= factor <= 1.2530:
        rec["buyer_premium_rate"] = 0.252
        rec["buyer_premium_vat"] = "TTC"
        class_code = "rate_252"
    elif 1.2570 <= factor <= 1.2590:
        rec["buyer_premium_rate"] = 0.258
        rec["buyer_premium_vat"] = "TTC"
        class_code = "rate_258"
    elif 1.2140 <= factor <= 1.2160:
        rec["buyer_premium_rate"] = 0.215
        rec["buyer_premium_vat"] = "HT"
        class_code = "rate_215_ht"
    elif 1.2090 <= factor <= 1.2110:
        rec["buyer_premium_rate"] = 0.21
        rec["buyer_premium_vat"] = "HT"
        class_code = "rate_21_ht"
    elif 1.1990 <= factor <= 1.2010:
        rec["buyer_premium_rate"] = 0.20
        rec["buyer_premium_vat"] = "HT"
        class_code = "rate_20_ht"
    else:
        rec["anomaly_type"] = "RATE_UNDETERMINED"
        class_code = "rate_undetermined"

    rec["hammer_per_bottle_eur"] = round2(hammer / bottles)
    return rec, class_code
