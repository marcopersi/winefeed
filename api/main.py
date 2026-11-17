#!/usr/bin/env python3
"""Wine price search + chart API (MVP, read-only).

FastAPI backend reading the master SQLite DB in read-only mode.
"""
import logging
import os
import sqlite3

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

DB_PATH = os.environ.get(
    "DB_PATH", "/Volumes/samsung/winefeed-data/wine_auction_prices.sqlite")

app = FastAPI(title="winefeed price API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# A lot only contributes a comparable per-bottle price when it's a single
# wine (not a MIXED/UNKNOWN lot_kind -- see data/wine_resolution/
# mixed_lots.py), has a resolved vintage (vintage_status STRUCTURED/
# EXTRACTED, not NV/AMBIGUOUS/CONFLICT/...), and has both a date and a
# price_per_bottle_eur (already FX- and bottle-size-normalized by
# data/build_db.py's _fill_price_per_bottle). Shared by every endpoint
# that counts or charts price observations, so "lot_count" and the chart
# always mean the same thing. Always used against ``lots`` aliased ``l``.
_PRICEABLE = (
    "l.lot_kind = 'SINGLE'"
    " AND l.vintage_status IN ('STRUCTURED', 'EXTRACTED')"
    " AND l.price_per_bottle_eur IS NOT NULL"
    " AND l.lot_date IS NOT NULL"
)


def _escape_like(value):
    """Escape SQL LIKE metacharacters so literal ``%``/``_`` in user input
    can't be (mis)read as wildcards."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _conn():
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    # SQLite's LIKE is case-insensitive only for ASCII letters by default;
    # register a Unicode-aware lower() (Python's str.lower()) so e.g.
    # "graubünden" matches "GRAUBÜNDEN".
    conn.create_function(
        "ulower", 1, lambda s: s.lower() if s is not None else None)
    conn.row_factory = sqlite3.Row
    return conn


def _with_conn(fn):
    """Open one read-only connection, run ``fn(conn)``, always close it.

    Any DB-level failure (unreachable file, locked DB) becomes a clean 503
    instead of an unhandled 500. Shared by every endpoint so a logically
    single request -- even one that needs two statements, like /prices
    picking a default vintage and then fetching its series -- opens only
    one connection (review finding: two ``_query()`` calls in one request
    doubled connection/UDF-registration overhead on that path).
    """
    try:
        conn = _conn()
    except sqlite3.Error:
        logging.exception("failed to open %s", DB_PATH)
        raise HTTPException(503, "database unavailable") from None
    try:
        return fn(conn)
    except sqlite3.Error:
        logging.exception("query failed")
        raise HTTPException(503, "database query failed") from None
    finally:
        conn.close()


def _query(sql, params=()):
    return _with_conn(lambda conn: conn.execute(sql, params).fetchall())


@app.get("/search")
def search(q: str = Query(..., min_length=2),
           n: int = Query(20, ge=1, le=100)):
    """Return up to ``n`` wines matching ``q`` in name or producer.

    Ordering: prefix match on name first, then substring, then lot count
    desc. ``lot_count`` here is a raw row count (fast: a plain index
    lookup per matched wine), unlike /wines/top's priceable-only count --
    this endpoint runs on every keystroke, so it can't afford a filter
    that requires fetching every candidate lot row (see the perf note on
    ``_PRICEABLE``'s other uses). It's a relevance/tie-break signal here,
    not a promise about what the chart will show.

    The wine-matching filter runs in a CTE, evaluated once per ``wines``
    row, before the join to ``lots`` -- with a scalar function (ulower)
    in the filter, letting the planner evaluate it inline on the joined
    result instead made it run once per *joined* row, i.e. once per lot
    of every matched wine (confirmed: ~40x slower for a wine with many
    lots) instead of once per wine.
    """
    escaped = _escape_like(q)
    like, prefix = f"%{escaped}%", f"{escaped}%"
    rows = _query(
        """
        WITH matched AS (
            SELECT id, canonical_name, producer, region
            FROM wines
            WHERE ulower(canonical_name) LIKE ulower(?) ESCAPE '\\'
               OR ulower(producer) LIKE ulower(?) ESCAPE '\\'
        )
        SELECT m.id, m.canonical_name, m.producer, m.region,
               COUNT(l.id) AS lot_count
        FROM matched m
        LEFT JOIN lots l ON l.wine_ref_id = m.id
        GROUP BY m.id
        ORDER BY
          CASE WHEN ulower(m.canonical_name) LIKE ulower(?) ESCAPE '\\' THEN 0
               WHEN ulower(m.canonical_name) LIKE ulower(?) ESCAPE '\\' THEN 1
               ELSE 2 END,
          lot_count DESC
        LIMIT ?
        """,
        (like, like, prefix, like, n))
    return {"results": [
        {"wine_id": r["id"], "canonical_name": r["canonical_name"],
         "producer": r["producer"], "region": r["region"],
         "lot_count": r["lot_count"]} for r in rows]}


@app.get("/wines/top")
def top_wines(n: int = Query(10, ge=1, le=50)):
    """Return the ``n`` wines with the most priceable observations.

    This is a coverage ranking, not a price ranking: it answers "which
    wines do we have the richest, chartable auction history for," useful
    as a starting point when a reader doesn't already know what to
    search for. Uses the same ``_PRICEABLE`` definition as /search and
    the price chart, so this count always matches what the chart plots.
    """
    rows = _query(
        f"""
        SELECT w.id, w.canonical_name, w.producer, w.region, lc.lot_count
        FROM wines w
        JOIN (
            SELECT l.wine_ref_id, COUNT(*) AS lot_count
            FROM lots l WHERE {_PRICEABLE}
            GROUP BY l.wine_ref_id
        ) lc ON lc.wine_ref_id = w.id
        ORDER BY lc.lot_count DESC
        LIMIT ?
        """,
        (n,))
    return {"results": [
        {"wine_id": r["id"], "canonical_name": r["canonical_name"],
         "producer": r["producer"], "region": r["region"],
         "lot_count": r["lot_count"]} for r in rows]}


@app.get("/wines/{wine_id}/vintages")
def vintages(wine_id: int):
    """List vintages with priceable observations for a wine, by count desc.

    Lets the UI offer a vintage picker instead of /wines/{id}/prices
    silently mixing every vintage's prices into one undifferentiated
    series.
    """
    rows = _query(
        f"""
        SELECT l.vintage_final AS vintage, COUNT(*) AS lot_count
        FROM lots l
        WHERE l.wine_ref_id = ? AND {_PRICEABLE}
        GROUP BY l.vintage_final
        ORDER BY lot_count DESC
        """,
        (wine_id,))
    return {"wine_id": wine_id, "vintages": [
        {"vintage": r["vintage"], "lot_count": r["lot_count"]} for r in rows]}


@app.get("/wines/{wine_id}/prices")
def prices(wine_id: int, vintage: int | None = Query(None)):
    """Return the EUR/per-bottle price series for one (wine, vintage).

    ``price_per_bottle_eur`` already normalizes currency and bottle size,
    but a vintage is a genuinely different product, not a unit-conversion
    issue -- mixing vintages into one line previously plotted e.g. a 2015
    half-bottle sold in HKD right next to a 1982 magnum sold in GBP as if
    they were one comparable series. Defaults to the vintage with the
    most observations when none is given.
    """
    def run(conn):
        nonlocal vintage
        if vintage is None:
            top = conn.execute(
                f"""
                SELECT l.vintage_final AS vintage, COUNT(*) AS n
                FROM lots l
                WHERE l.wine_ref_id = ? AND {_PRICEABLE}
                GROUP BY l.vintage_final ORDER BY n DESC LIMIT 1
                """,
                (wine_id,)).fetchone()
            if top is None:
                return None
            vintage = top["vintage"]
        return conn.execute(
            f"""
            SELECT l.lot_date, l.price_per_bottle_eur AS price,
                   p.name AS provider, a.location
            FROM lots l
            JOIN auctions a ON a.id = l.auction_id
            JOIN providers p ON p.id = a.provider_id
            WHERE l.wine_ref_id = ? AND l.vintage_final = ? AND {_PRICEABLE}
            ORDER BY l.lot_date
            """,
            (wine_id, vintage)).fetchall()

    # Both statements (the default-vintage lookup and the series fetch)
    # run on one connection via _with_conn -- using _query() twice here
    # would open two separate connections for one logical request.
    rows = _with_conn(run)
    if rows is None:
        return {"wine_id": wine_id, "vintage": None, "prices": []}
    return {"wine_id": wine_id, "vintage": vintage, "prices": [
        {"lot_date": r["lot_date"], "price": r["price"], "currency": "EUR",
         "provider": r["provider"], "location": r["location"]}
        for r in rows]}
