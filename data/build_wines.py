#!/usr/bin/env python3
"""Stufe 2: canonical wine resolution.

Runs after ``build_db.py`` has loaded raw lots. Fills ``wines``,
``wine_alias_observations``, ``wine_alias_resolutions`` and backfills
``lots.wine_ref_id`` / ``lots.vintage_final``.

Pure resolution rules live in the ``wine_resolution`` package; this module
orchestrates them against the SQLite database. Deterministic and idempotent for
identical inputs.
"""
import csv
import os

from wine_resolution import NORMALIZER_VERSION, RESOLVER_VERSION
from wine_resolution.normalize import normalize, is_valid_name
from wine_resolution.vintage import resolve_vintage
from wine_resolution.mixed_lots import classify_group, KIND_SINGLE, KIND_MIXED, \
    KIND_UNKNOWN
from wine_resolution.resolver import resolve_group, stable_key, \
    STATUS_RESOLVED, STATUS_AMBIGUOUS

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OVERRIDES_PATH = os.path.join(SCRIPT_DIR, "reference",
                              "wine_alias_overrides.csv")

BATCH = 10000


def load_overrides():
    with open(OVERRIDES_PATH, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def run(conn):
    _set_source_lot_key(conn)
    _separate_vintage(conn)
    _classify_lots(conn)
    observations = _build_observations(conn)
    idealwine_ref = _idealwine_reference(conn)
    _resolve(conn, observations, load_overrides(), idealwine_ref)
    _backfill_wine_ref(conn)


# --------------------------------------------------------------------------- #
# Source-lot identity + vintage separation
# --------------------------------------------------------------------------- #

def _auction_year_map(conn):
    out = {}
    for aid, date in conn.execute(
            "SELECT id, auction_date FROM auctions").fetchall():
        if date and date[:4].isdigit():
            out[aid] = int(date[:4])
    return out


def _set_source_lot_key(conn):
    conn.execute("""
        UPDATE lots
        SET source_lot_key = (
            SELECT p.name || '|' || a.auction_id || '|' ||
                   COALESCE(lots.lot_no, '')
            FROM auctions a JOIN providers p ON a.provider_id = p.id
            WHERE a.id = lots.auction_id
        )
    """)


def _separate_vintage(conn):
    auction_year = _auction_year_map(conn)
    conn.execute(
        "CREATE TEMP TABLE vintage_map (lot_id INTEGER PRIMARY KEY,"
        " cleaned TEXT, final INTEGER, status TEXT, extracted INTEGER,"
        " rule_id TEXT, evidence TEXT)")
    cache = {}
    batch = []
    rows = conn.execute(
        "SELECT id, raw_wine, vintage, auction_id FROM lots"
        " WHERE raw_wine IS NOT NULL AND raw_wine != ''").fetchall()
    for lot_id, raw_wine, structured, aid in rows:
        ckey = (raw_wine, structured, auction_year.get(aid))
        if ckey not in cache:
            cache[ckey] = resolve_vintage(raw_wine, structured, ckey[2])
        r = cache[ckey]
        batch.append((lot_id, r["cleaned_name"], r["final"], r["status"],
                      r["extracted"], r["rule_id"], r["evidence"]))
        if len(batch) >= BATCH:
            conn.executemany(
                "INSERT INTO vintage_map VALUES (?,?,?,?,?,?,?)", batch)
            batch = []
    if batch:
        conn.executemany(
            "INSERT INTO vintage_map VALUES (?,?,?,?,?,?,?)", batch)
    conn.execute("""
        UPDATE lots SET
          wine = (SELECT cleaned FROM vintage_map vm WHERE vm.lot_id = lots.id),
          vintage_final = (SELECT final FROM vintage_map vm
                           WHERE vm.lot_id = lots.id),
          vintage_status = (SELECT status FROM vintage_map vm
                            WHERE vm.lot_id = lots.id),
          vintage_extracted = (SELECT extracted FROM vintage_map vm
                               WHERE vm.lot_id = lots.id),
          vintage_rule_id = (SELECT rule_id FROM vintage_map vm
                             WHERE vm.lot_id = lots.id),
          vintage_evidence_text = (SELECT evidence FROM vintage_map vm
                                   WHERE vm.lot_id = lots.id)
    """)
    conn.execute("DROP TABLE vintage_map")


# --------------------------------------------------------------------------- #
# Lot classification
# --------------------------------------------------------------------------- #

def _classify_lots(conn):
    conn.execute("UPDATE lots SET lot_kind=?, mixed_reason=?, mixed_rule_id=?"
                 " WHERE mixed_lot=1",
                 (KIND_MIXED, "provider-flag", "provider-flag"))
    for kw in ("%mixed lot%", "%mixed case%", "%assortment%", "%selection%"):
        conn.execute(
            "UPDATE lots SET lot_kind=?, mixed_reason=?, mixed_rule_id=?"
            " WHERE lot_kind IS NULL AND (wine LIKE ? OR description LIKE ?)",
            (KIND_MIXED, "keyword-evidence", "keyword-evidence", kw, kw))

    # multi-lot groups need per-group classification
    multi = [r[0] for r in conn.execute(
        "SELECT source_lot_key FROM lots WHERE lot_kind IS NULL"
        " GROUP BY source_lot_key HAVING count(*) > 1").fetchall()]
    for sk in multi:
        lot_rows = []
        for row in conn.execute(
                "SELECT id, wine, mixed_lot, description, vintage FROM lots"
                " WHERE source_lot_key=? AND lot_kind IS NULL", (sk,)):
            lot_rows.append({
                "lot_id": row[0],
                "wine": row[1],
                "wine_key": normalize(row[1]),
                "mixed_lot": row[2],
                "description": row[3],
                "vintage": row[4],
            })
        kind, reason, rule_id = classify_group(
            [{"wine": r["wine"], "wine_key": r["wine_key"],
              "mixed_lot": r["mixed_lot"], "description": r["description"],
              "vintage": r["vintage"]} for r in lot_rows])
        for r in lot_rows:
            conn.execute(
                "UPDATE lots SET lot_kind=?, mixed_reason=?, mixed_rule_id=?"
                " WHERE id=?", (kind, reason, rule_id, r["lot_id"]))

    # remaining single-name groups: SINGLE if valid name, else UNKNOWN
    conn.execute(
        "UPDATE lots SET lot_kind=?, mixed_rule_id=? WHERE lot_kind IS NULL"
        " AND wine IS NOT NULL AND wine != ''",
        (KIND_SINGLE, "single-wine"))
    conn.execute(
        "UPDATE lots SET lot_kind=?, mixed_reason=?, mixed_rule_id=?"
        " WHERE lot_kind IS NULL",
        (KIND_UNKNOWN, "no-wine-name", "no-wine-name"))


# --------------------------------------------------------------------------- #
# Observations + resolution
# --------------------------------------------------------------------------- #

def _build_observations(conn):
    observations = []
    rows = conn.execute("""
        SELECT l.id, p.id, l.wine, l.producer, l.region
        FROM lots l
        JOIN auctions a ON l.auction_id = a.id
        JOIN providers p ON a.provider_id = p.id
        WHERE l.wine IS NOT NULL AND l.wine != '' AND l.lot_kind = 'SINGLE'
    """).fetchall()
    for lot_id, provider_id, wine, producer, region in rows:
        if not is_valid_name(wine):
            continue
        observations.append({
            "source_lot_id": lot_id,
            "provider_id": provider_id,
            "alias_raw": wine,
            "alias_key": normalize(wine),
            "producer_raw": producer,
            "producer_key": normalize(producer),
            "region_raw": region,
            "region_key": normalize(region),
        })
    return observations


def _idealwine_reference(conn):
    ref = {}
    for (wine,) in conn.execute("""
        SELECT DISTINCT l.wine
        FROM lots l
        JOIN auctions a ON l.auction_id = a.id
        JOIN providers p ON a.provider_id = p.id
        WHERE p.name = 'idealwine' AND l.wine IS NOT NULL AND l.wine != ''
    """).fetchall():
        ref.setdefault(normalize(wine), wine)
    return ref


def _resolve(conn, observations, overrides, idealwine_ref):
    override_map = {}
    for ov in overrides:
        if ov.get("action") == "MERGE" and ov.get("canonical_name"):
            override_map[normalize(ov.get("alias_raw") or "")] = \
                ov.get("canonical_name")

    conn.execute("DELETE FROM wine_alias_resolutions")
    conn.execute("DELETE FROM wine_alias_observations")
    conn.execute("DELETE FROM wines")

    groups = {}
    for o in observations:
        groups.setdefault(o["alias_key"], []).append(o)

    wine_ids = {}
    for alias_key in sorted(groups):
        obs = groups[alias_key]
        evidence = {}
        for o in obs:
            evidence[o["alias_raw"]] = evidence.get(o["alias_raw"], 0) + 1
        agg = []
        for alias_raw, cnt in evidence.items():
            producer_raw = next((o.get("producer_raw") for o in obs
                                 if o["alias_raw"] == alias_raw), None)
            region_raw = next((o.get("region_raw") for o in obs
                               if o["alias_raw"] == alias_raw), None)
            agg.append({
                "alias_raw": alias_raw,
                "alias_key": alias_key,
                "producer_raw": producer_raw,
                "producer_key": normalize(producer_raw),
                "region_raw": region_raw,
                "region_key": normalize(region_raw),
                "evidence_count": cnt,
            })

        for o in obs:
            conn.execute(
                "INSERT INTO wine_alias_observations(provider_id, alias_raw,"
                " alias_key, producer_raw, producer_key, region_raw, region_key,"
                " source_lot_id, evidence_count, normalizer_version)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (o["provider_id"], o["alias_raw"], o["alias_key"],
                 o["producer_raw"], o["producer_key"], o["region_raw"],
                 o["region_key"], o["source_lot_id"], 1, NORMALIZER_VERSION))

        forced = override_map.get(alias_key)
        idealwine_name = idealwine_ref.get(alias_key)
        res = resolve_group(agg, idealwine_name or forced)

        if res["status"] == STATUS_RESOLVED:
            canonical_name = forced or res["canonical_name"]
            canonical_key = normalize(canonical_name)
            skey = stable_key(canonical_key, res["discriminator_key"])
            if skey not in wine_ids:
                cur = conn.execute(
                    "INSERT INTO wines(stable_key, canonical_name,"
                    " canonical_key, producer, producer_key, region,"
                    " classification, canonical_source, resolver_version,"
                    " review_status) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (skey, canonical_name, canonical_key, res["producer"],
                     normalize(res["producer"]), res["region"], None,
                     "idealwine" if idealwine_name else
                     ("curated" if forced else "auto"),
                     RESOLVER_VERSION, "AUTO_RESOLVED"))
                wine_ids[skey] = cur.lastrowid
            conn.execute(
                "INSERT INTO wine_alias_resolutions(scope_key, alias_key,"
                " discriminator_key, wine_id, resolution_status,"
                " resolution_method, confidence, rule_version, reason)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                ("global", alias_key, res["discriminator_key"],
                 wine_ids[skey], STATUS_RESOLVED,
                 "curated" if forced else
                 ("idealwine" if idealwine_name else "auto"),
                 1.0, RESOLVER_VERSION, res["reason"]))
        else:
            conn.execute(
                "INSERT INTO wine_alias_resolutions(scope_key, alias_key,"
                " discriminator_key, wine_id, resolution_status,"
                " resolution_method, confidence, rule_version, reason)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                ("global", alias_key, res["discriminator_key"], None,
                 STATUS_AMBIGUOUS, "auto", None, RESOLVER_VERSION,
                 res["reason"]))


def _backfill_wine_ref(conn):
    key_to_wine = dict(conn.execute(
        "SELECT canonical_key, id FROM wines").fetchall())
    for lot_id, wine in conn.execute(
            "SELECT id, wine FROM lots WHERE wine_ref_id IS NULL"
            " AND wine IS NOT NULL AND wine != '' AND lot_kind = 'SINGLE'"):
        wid = key_to_wine.get(normalize(wine))
        if wid is not None:
            conn.execute("UPDATE lots SET wine_ref_id=? WHERE id=?",
                         (wid, lot_id))
