"""Geographic origin reference + mapping integration.

Loads the curated, multilingual origin reference (wine_origins) and the
raw-value -> origin mapping (wine_origin_mappings), then links each lot's
``region``/``appellation`` to the most specific origin. Only conflict-free,
resolved mappings are applied; ambiguous/unresolved values are marked, never
guessed.
"""
import csv
import os

from .normalize import normalize

RESOLVED_STATUSES = {
    "normalized_exact", "normalized_alias", "curated_equivalence",
    "curated_style_to_appellation", "curated_climat_to_appellation",
    "curated_compound_to_specific",
}
AMBIGUOUS_STATUSES = {
    "ambiguous_requires_context", "historical_requires_context",
    "suggested_review",
}
UNRESOLVED_STATUSES = {"unresolved_requires_review"}
EXCLUDED_STATUSES = {
    "excluded_non_origin", "excluded_non_wine_origin",
    "out_of_scope_requires_extension",
}

ORIGINS_COLS = [
    "origin_id", "country_code", "country_de", "country_fr", "country_en",
    "region_canonical", "region_de", "region_fr", "region_en",
    "appellation_canonical", "record_level", "appellation_type",
    "legal_scheme", "legal_status", "source_authority", "source_url",
    "legal_basis_url", "validated_on", "auction_lots_observed", "notes_de",
    "notes_fr", "notes_en",
]


def _ref_dir():
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "reference")


def load_origins(conn):
    path = os.path.join(_ref_dir(), "wine_origin_reference_multilingual.csv")
    with open(path, encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            conn.execute(
                f"INSERT INTO wine_origins({','.join(ORIGINS_COLS)})"
                f" VALUES ({','.join('?' * len(ORIGINS_COLS))})",
                [_or_none(row.get(c)) for c in ORIGINS_COLS])


def load_mappings(conn):
    path = os.path.join(_ref_dir(), "wine_origin_input_mapping.csv")
    cols = ["source_file", "raw_value", "raw_lots", "raw_source",
            "raw_country_code", "normalized_value", "match_status",
            "match_confidence", "target_origin_id", "target_record_level",
            "match_reason"]
    with open(path, encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            conn.execute(
                f"INSERT INTO wine_origin_mappings({','.join(cols)})"
                f" VALUES ({','.join('?' * len(cols))})",
                [_or_none(row.get(c)) for c in cols])


def _or_none(value):
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def link_origins(conn):
    """Set lots.origin_id from region/appellation via the mapping.

    Appellation (more specific) wins over region. Only resolved mappings are
    applied; ambiguous/unresolved/excluded values get an origin_status marker.
    """
    resolved = {}
    status_by_norm = {}
    for norm, origin_id, status in conn.execute(
            "SELECT normalized_value, target_origin_id, match_status"
            " FROM wine_origin_mappings"):
        if not norm:
            continue
        status_by_norm.setdefault(norm, set()).add(status)
        if status in RESOLVED_STATUSES and origin_id:
            if norm in resolved and resolved[norm] != origin_id:
                resolved.pop(norm, None)
                status_by_norm[norm].add("ambiguous_requires_context")
            else:
                resolved[norm] = origin_id

    conn.execute("UPDATE lots SET origin_id = NULL, origin_status = NULL")
    rows = conn.execute(
        "SELECT id, appellation, region FROM lots").fetchall()
    for lot_id, appellation, region in rows:
        origin_id, status = _lookup(resolved, status_by_norm,
                                    appellation, region)
        conn.execute("UPDATE lots SET origin_id=?, origin_status=?"
                     " WHERE id=?", (origin_id, status, lot_id))


def _lookup(resolved, status_by_norm, appellation, region):
    for value in (appellation, region):
        if not value:
            continue
        norm = normalize(value)
        if norm in resolved:
            return resolved[norm], "resolved"
        if norm in status_by_norm:
            statuses = status_by_norm[norm]
            if statuses & UNRESOLVED_STATUSES:
                return None, "unresolved"
            if statuses & AMBIGUOUS_STATUSES:
                return None, "ambiguous"
            if statuses & EXCLUDED_STATUSES:
                return None, "excluded"
    return None, None
