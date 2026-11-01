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
    _parse_bottle_formats(conn)
    _classify_lots(conn)
    observations = _build_observations(conn)
    idealwine_ref = _idealwine_reference(conn)
    _resolve(conn, observations, load_overrides(), idealwine_ref)
    _backfill_wine_ref(conn)
    _match_varieties(conn)
    _link_origins(conn)


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
        ckey = (raw_wine, structured)
        if ckey not in cache:
            cache[ckey] = resolve_vintage(raw_wine, structured, None)
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
    # Year-after-auction check (separate pass over distinct extraction).
    for aid, ayear in auction_year.items():
        conn.execute(
            "UPDATE lots SET vintage_status='INVALID', vintage_final=NULL,"
            " vintage_rule_id='year-after-auction'"
            " WHERE vintage_status='EXTRACTED' AND vintage_extracted > ?"
            " AND auction_id = ?", (ayear, aid))
    conn.execute("DROP TABLE vintage_map")


def _parse_bottle_formats(conn):
    """Derive quantity + bottle_size_dl from '(6 BT)'-style name hints, and
    strip that same hint out of ``lots.wine`` so it never pollutes
    ``alias_key`` (confirmed real case: "Sassicaia" vs. "Sassicaia (2 BT)"
    vs. "Sassicaia Magnum" fragmenting into separate wines rows for the
    same real wine -- 17,226 wines / 22,888 lots before this fix).
    ``_separate_vintage`` already strips a *trailing* qty bracket for the
    STATUS_EXTRACTED case; this covers every other vintage status too
    (STRUCTURED, MISSING, NV, MV, AMBIGUOUS, ... -- cleaned_name is left
    untouched there, so a mid-name or non-trailing hint survived)."""
    from wine_resolution.bottle import parse_bottle_format, strip_bottle_format
    qty_updates = []
    wine_updates = []
    for lot_id, raw_wine, wine, description in conn.execute(
            "SELECT id, raw_wine, wine, description FROM lots"
            " WHERE raw_wine IS NOT NULL OR description IS NOT NULL"):
        if wine:
            stripped = strip_bottle_format(wine)
            if stripped != wine:
                wine_updates.append((stripped, lot_id))
        qty, dl = parse_bottle_format(raw_wine, description)
        if qty is not None:
            qty_updates.append((qty, dl, lot_id))
    conn.executemany(
        "UPDATE lots SET wine=? WHERE id=?", wine_updates)
    conn.executemany(
        "UPDATE lots SET quantity=?, bottle_size_dl=? WHERE id=?"
        " AND quantity IS NULL", qty_updates)


# --------------------------------------------------------------------------- #
# Lot classification
# --------------------------------------------------------------------------- #

def _exclude_spirits(conn):
    """Mark spirit lots UNKNOWN so they never reach wine resolution.

    ``wine_resolution.spirits`` is a curated detector (Armagnac, Cognac,
    brandy...) that existed but was never wired into the pipeline — spirit
    lots flowed straight into producer/wine matching and picked up false
    wine identities (e.g. "Marquis de Montdidier Armagnac" resolving a
    producer purely from "Marquis de ..." word overlap).
    """
    from wine_resolution.spirits import is_spirit, load_terms
    terms = load_terms()
    updates = []
    for lot_id, wine, description in conn.execute(
            "SELECT id, wine, description FROM lots WHERE lot_kind IS NULL"):
        text = " ".join(x for x in (wine or "", description or "") if x)
        if text and is_spirit(text, terms):
            updates.append((lot_id,))
    conn.executemany(
        "UPDATE lots SET lot_kind=?, mixed_reason=?, mixed_rule_id=?"
        " WHERE id=?",
        [(KIND_UNKNOWN, "spirit", "spirit-terms", lot_id)
         for (lot_id,) in updates])


def _classify_lots(conn):
    _exclude_spirits(conn)
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

# Classification/state/provenance codes that land in a loader's raw
# ``producer`` field but are not a producer name at all: VdT (Vino da
# Tavola classification), OHK (Original-Holzkiste state marker), SBE/AGE
# (Rioja ageing-category abbreviations), plus pure parse junk ("(B)",
# "0") -- confirmed real cases, none of them resolve to any canonical
# producer in producers.csv (verified: zero exact-alias matches). Same
# category as sylvies' own bare "Mc"/"Neg"/"Dom"/"Dist" provenance codes
# (build_db._SYLVIES_PROVENANCE_CODE, filtered at load time for that one
# house only) -- generalized here so every house benefits, not just
# sylvies. Rejecting these falls back to extracting a producer from the
# wine text instead (§4.2), which can only be neutral-or-better: none of
# them were ever a usable producer value in the first place.
_JUNK_PRODUCER_CODES = {
    "vdt", "ohk", "sbe", "age", "b", "0",
    "mc", "neg", "dom", "dist",
}


def _match_producer_and_wine(matcher, wine, producer):
    """Apply §4.2/§4.3 to one (wine, producer) pair, return the resolved pair."""
    if producer and normalize(producer) in _JUNK_PRODUCER_CODES:
        producer = None
    if not producer:
        # §4.2: if the producer is missing, extract it from the name via
        # the reference-list token index.
        matched = matcher.match_producer(wine)
        if matched:
            producer = matched
    else:
        # The source producer may be a raw variant ("Ch. Margaux") that
        # isn't the key match_wine's producer_wines index is built on (the
        # canonical name) — canonicalize it first, or §4.3 below silently
        # finds no wines and skips the fuzzy match.
        canonical = matcher.canonical_producer(producer)
        if canonical:
            producer = canonical
    if producer:
        # §4.3: if the producer is known, normalize the wine name against
        # its reference list (fuzzy).
        matched_wine = matcher.match_wine(producer, wine)
        if matched_wine:
            wine = matched_wine
    return wine, producer


def _build_observations(conn):
    from wine_resolution.producer_match import ProducerMatcher
    matcher = ProducerMatcher()
    observations = []
    lot_updates = []
    cache = {}
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
        ckey = (wine, producer)
        if ckey not in cache:
            cache[ckey] = _match_producer_and_wine(matcher, wine, producer)
        wine, producer = cache[ckey]
        # Persist the matched values: _backfill_wine_ref (and any other
        # consumer) reads lots.wine/lots.producer directly, so they must
        # agree with the alias_key/producer_key written below for this
        # same alias — otherwise every lot that benefits from matching
        # loses its wine_ref_id, the exact silent-data-loss failure §4.1
        # exists to prevent.
        if (wine, producer) != ckey:
            lot_updates.append((wine, producer, lot_id))
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
    if lot_updates:
        conn.executemany(
            "UPDATE lots SET wine=?, producer=? WHERE id=?", lot_updates)
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
        # AMBIGUOUS-splitting (§4.1): split by producer_key so each
        # (alias_key, producer_key) pair resolves to its own wine instead of
        # silently dropping the lots.
        by_producer = {}
        for o in obs:
            by_producer.setdefault(o["producer_key"] or "", []).append(o)

        # Absorption rule (confirmed real case: "Sassicaia" splits into
        # producer=NULL and producer="Tenuta San Guido" -- the same real
        # wine, wines_by_producer.csv already lists Sassicaia under Tenuta
        # San Guido). When an alias_key group has exactly one *known*
        # producer, its producer-less siblings almost certainly belong to
        # that same producer too; merge them into the one sub-group so
        # resolve_group sees them together (it already discards "" when
        # checking for a producer conflict, so this does not change
        # anything about how >=2 distinct producers are kept apart -- that
        # AMBIGUOUS-splitting, §4.1, is untouched).
        known = [k for k in by_producer if k]
        if len(known) == 1 and "" in by_producer:
            by_producer[known[0]].extend(by_producer.pop(""))

        forced = override_map.get(alias_key)
        idealwine_name = idealwine_ref.get(alias_key)

        for sub_obs in by_producer.values():
            evidence = {}
            for o in sub_obs:
                evidence[o["alias_raw"]] = evidence.get(o["alias_raw"], 0) + 1
            agg = []
            for alias_raw, cnt in evidence.items():
                producer_raw = next((o.get("producer_raw") for o in sub_obs
                                     if o["alias_raw"] == alias_raw), None)
                region_raw = next((o.get("region_raw") for o in sub_obs
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

            for o in sub_obs:
                conn.execute(
                    "INSERT INTO wine_alias_observations(provider_id, alias_raw,"
                    " alias_key, producer_raw, producer_key, region_raw,"
                    " region_key, source_lot_id, evidence_count,"
                    " normalizer_version) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (o["provider_id"], o["alias_raw"], o["alias_key"],
                     o["producer_raw"], o["producer_key"], o["region_raw"],
                     o["region_key"], o["source_lot_id"], 1,
                     NORMALIZER_VERSION))

            # Precedence: a curated MERGE override is a human decision about
            # this specific alias and outranks idealwine (an automatic
            # source) — consistent with §4.5 ("CURATED = höchste
            # Vertrauensstufe, nie vom Auto-Resolver überschrieben").
            # ``res["canonical_name"]`` is the one place the name is
            # decided, so ``canonical_source``/``resolution_method`` below
            # just need to describe *that* choice instead of re-deriving it
            # (the previous code re-derived it inconsistently: the name
            # followed curated>idealwine>auto but the logged
            # canonical_source checked idealwine first).
            res = resolve_group(agg, forced or idealwine_name)

            if res["status"] == STATUS_RESOLVED:
                canonical_name = res["canonical_name"]
                canonical_key = normalize(canonical_name)
                source = ("curated" if forced else
                          ("idealwine" if idealwine_name else "auto"))
                skey = stable_key(canonical_key, res["discriminator_key"])
                if skey not in wine_ids:
                    cur = conn.execute(
                        "INSERT INTO wines(stable_key, canonical_name,"
                        " canonical_key, producer, producer_key, region,"
                        " classification, canonical_source, resolver_version,"
                        " review_status) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (skey, canonical_name, canonical_key, res["producer"],
                         normalize(res["producer"]), res["region"], None,
                         source, RESOLVER_VERSION, "AUTO_RESOLVED"))
                    wine_ids[skey] = cur.lastrowid
                conn.execute(
                    "INSERT INTO wine_alias_resolutions(scope_key, alias_key,"
                    " discriminator_key, wine_id, resolution_status,"
                    " resolution_method, confidence, rule_version, reason)"
                    " VALUES (?,?,?,?,?,?,?,?,?)",
                    ("global", alias_key, res["discriminator_key"],
                     wine_ids[skey], STATUS_RESOLVED, source,
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
    resolved = [r for r in conn.execute(
        "SELECT alias_key, discriminator_key, wine_id"
        " FROM wine_alias_resolutions WHERE wine_id IS NOT NULL").fetchall()]
    key_to_wine = {(alias_key, disc): wid for alias_key, disc, wid in resolved}
    # Mirror of the absorption rule in _resolve(): an alias_key with
    # exactly one resolved wine (regardless of its discriminator) is the
    # target for a lot whose OWN producer is unknown -- the producer-less
    # observation was merged into that single wine there, so the lot must
    # be able to find it here too, not just the (key, "") exact match
    # that no longer exists once it was absorbed away.
    by_alias = {}
    for alias_key, _, wid in resolved:
        by_alias.setdefault(alias_key, set()).add(wid)
    alias_to_single_wine = {k: next(iter(v)) for k, v in by_alias.items()
                            if len(v) == 1}
    cache = {}
    updates = []
    for lot_id, wine, producer in conn.execute(
            "SELECT id, wine, producer FROM lots WHERE wine_ref_id IS NULL"
            " AND wine IS NOT NULL AND wine != '' AND lot_kind = 'SINGLE'"):
        key = cache.get(wine)
        if key is None:
            key = normalize(wine)
            cache[wine] = key
        pk = normalize(producer)
        wid = key_to_wine.get((key, pk)) or key_to_wine.get((key, ""))
        if wid is None and not pk:
            wid = alias_to_single_wine.get(key)
        if wid is not None:
            updates.append((wid, lot_id))
    conn.executemany("UPDATE lots SET wine_ref_id=? WHERE id=?", updates)


def _match_varieties(conn):
    from wine_resolution.variety import (default_varieties_path,
                                         load_varieties, match_varieties)
    varieties = load_varieties(default_varieties_path())
    variety_keys = [normalize(v) for v, _ in varieties]
    key_to_meta = {normalize(v): (v, c) for v, c in varieties}
    conn.execute("DELETE FROM wine_varieties")
    for wine_id, name in conn.execute(
            "SELECT id, canonical_name FROM wines").fetchall():
        for key in match_varieties(name, variety_keys):
            vname, color = key_to_meta[key]
            conn.execute(
                "INSERT INTO wine_varieties(wine_id, variety_name, color)"
                " VALUES (?,?,?)", (wine_id, vname, color))


def _link_origins(conn):
    from wine_resolution.origin import link_origins, load_mappings, \
        load_origins
    load_origins(conn)
    load_mappings(conn)
    link_origins(conn)
