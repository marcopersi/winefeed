"""Incremental iDealwine cote diff: transform, filter, insert new lots.

The fetcher loads the full cote (``productVintageRatings``) for every currently
offered lot. This module selects only the adjudications newer than the last
recorded ``soldAt``, maps them onto the raw normalize format, reuses the shared
premium/hammer classification, and inserts them into the existing database
without a full rebuild.

Samsung note: this only *appends* lots via ``Builder``; it never drops the
schema.
"""
from build_db import Builder, parse_date, parse_dl, to_int
from idealwine_normalize import DUCLOT_PIDS, normalize_adjudication


def _cents_to_eur(v):
    return v / 100.0 if v is not None else None


def transform_last_adjudication(last_adj):
    """Map one ``lastAdjudication`` to the raw normalize format."""
    pv = last_adj.get("productVintage") or {}
    product = pv.get("product") or {}
    estate = product.get("estate") or {}
    region = product.get("region") or {}
    return {
        "sold_at": last_adj.get("soldAt"),
        "bottles": last_adj.get("numberOfBottles"),
        "hammer_eur": _cents_to_eur(last_adj.get("price")),
        "total_eur": _cents_to_eur(last_adj.get("historicPrice")),
        "format": last_adj.get("format"),
        "code": last_adj.get("code"),
        "product_id": product.get("id"),
        "wine": product.get("name"),
        "estate": estate.get("name"),
        "vintage": pv.get("year"),
        "region": region.get("name"),
        "appellation": product.get("appellation"),
        "color": product.get("color"),
        "classification": product.get("classification"),
    }


def _cote_context(cote):
    """Return (current_rating_eur, annual_ratings_eur) from one cote record."""
    current = cote.get("currentYearRating")
    annual = {}
    for r in cote.get("productVintageRatings") or []:
        if isinstance(r, dict) and r.get("year") is not None:
            annual[r["year"]] = _cents_to_eur(r.get("value"))
    return _cents_to_eur(current), annual


def new_adjudications(cote_list, last_sold_at):
    """Return normalized adjudications newer than ``last_sold_at``.

    Each returned record carries the normalized price fields plus the wine
    identity fields needed to insert a lot.
    """
    out = []
    for cote in cote_list:
        product_id = _product_id(cote)
        is_duclot = product_id in DUCLOT_PIDS
        current, annual = _cote_context(cote)
        for adj in cote.get("lastAdjudications") or []:
            raw = transform_last_adjudication(adj)
            sold_at = raw.get("sold_at")
            if not sold_at or sold_at <= last_sold_at:
                continue
            rec, _ = normalize_adjudication(raw, is_duclot, current, annual)
            rec.update({
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


def _product_id(cote):
    pv = cote.get("productVintage") or {}
    product = pv.get("product") or {}
    return product.get("id")


def _lot_exists(conn, code):
    row = conn.execute(
        "SELECT 1 FROM lots WHERE lot_no = ? AND auction_id IN "
        "(SELECT id FROM auctions WHERE provider_id = "
        "(SELECT id FROM providers WHERE name = 'idealwine')) LIMIT 1",
        (code,)).fetchone()
    return row is not None


def insert_new_lots(conn, new_lots, auction_id="cote", title="iDealwine Cote"):
    """Insert ``new_lots`` into ``conn``, skipping already-present records."""
    b = Builder(conn)
    a_id = b.add_auction("idealwine", auction_id, title, None, "EUR", None)
    inserted = 0
    for rec in new_lots:
        code = rec.get("code")
        if code and _lot_exists(conn, code):
            continue
        b.add_lot(a_id, {
            "lot_no": code,
            "lot_date": parse_date(rec.get("sold_at")),
            "source_lot_key": f"idealwine:{code}" if code else None,
            "source_file": "IDealwine/delta",
            "wine": rec.get("wine"),
            "producer": rec.get("estate"),
            "vintage": to_int(rec.get("vintage")),
            "region": rec.get("region"),
            "appellation": rec.get("appellation") or None,
            "classification": rec.get("classification") or None,
            "color": rec.get("color") or None,
            "quantity": to_int(rec.get("number_of_bottles")),
            "bottle_size_dl": parse_dl(rec.get("format")),
            "hammer_price": (rec.get("hammer_per_bottle_eur")
                             or rec.get("hammer_per_bottle_eur_derived")),
            "realised_price": rec.get("total_per_bottle_eur"),
            "price_basis": rec.get("price_basis"),
            "currency": "EUR",
        })
        inserted += 1
    return inserted
