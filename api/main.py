#!/usr/bin/env python3
"""Wine price search + chart API (MVP, read-only).

FastAPI backend reading the master SQLite DB in read-only mode.
"""
import os
import sqlite3

from fastapi import FastAPI, Query
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


def _conn():
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)


@app.get("/search")
def search(q: str = Query(..., min_length=2),
           n: int = Query(20, ge=1, le=100)):
    """Return up to ``n`` wines matching ``q`` in name or producer.

    Ordering: prefix match on name first, then substring, then lot count desc.
    """
    like = f"%{q}%"
    prefix = f"{q}%"
    conn = _conn()
    try:
        rows = conn.execute(
            """
            SELECT w.id, w.canonical_name, w.producer, w.region,
                   COUNT(l.id) AS lot_count
            FROM wines w
            LEFT JOIN lots l ON l.wine_ref_id = w.id
            WHERE w.canonical_name LIKE ? OR w.producer LIKE ?
            GROUP BY w.id
            ORDER BY
              CASE WHEN w.canonical_name LIKE ? THEN 0
                   WHEN w.canonical_name LIKE ? THEN 1
                   ELSE 2 END,
              lot_count DESC
            LIMIT ?
            """,
            (like, like, prefix, like, n)).fetchall()
    finally:
        conn.close()
    return {"results": [
        {"wine_id": r[0], "canonical_name": r[1], "producer": r[2],
         "region": r[3], "lot_count": r[4]} for r in rows]}


@app.get("/wines/top")
def top_wines(n: int = Query(10, ge=1, le=50)):
    """Return the ``n`` wines with the most price observations (lot_count).

    This is a coverage ranking, not a price ranking: it answers "which wines
    do we have the richest auction history for," useful as a starting point
    when a reader doesn't already know what to search for.
    """
    conn = _conn()
    try:
        rows = conn.execute(
            """
            SELECT w.id, w.canonical_name, w.producer, w.region,
                   COUNT(l.id) AS lot_count
            FROM wines w
            JOIN lots l ON l.wine_ref_id = w.id
            GROUP BY w.id
            ORDER BY lot_count DESC
            LIMIT ?
            """,
            (n,)).fetchall()
    finally:
        conn.close()
    return {"results": [
        {"wine_id": r[0], "canonical_name": r[1], "producer": r[2],
         "region": r[3], "lot_count": r[4]} for r in rows]}


@app.get("/wines/{wine_id}/prices")
def prices(wine_id: int):
    """Return the price time series for a wine, ordered by lot_date.

    ``total_price`` falls back to ``realised_price`` where no total was
    derived (e.g. gross-only houses). Lots without a date are excluded.
    """
    conn = _conn()
    try:
        rows = conn.execute(
            """
            SELECT l.lot_date,
                   COALESCE(l.total_price, l.realised_price) AS price,
                   l.currency, p.name, a.location
            FROM lots l
            JOIN auctions a ON a.id = l.auction_id
            JOIN providers p ON p.id = a.provider_id
            WHERE l.wine_ref_id = ?
              AND l.lot_date IS NOT NULL
              AND (l.total_price IS NOT NULL OR l.realised_price IS NOT NULL)
            ORDER BY l.lot_date
            """,
            (wine_id,)).fetchall()
    finally:
        conn.close()
    return {"wine_id": wine_id, "prices": [
        {"lot_date": r[0], "price": r[1], "currency": r[2], "provider": r[3],
         "location": r[4]} for r in rows]}
