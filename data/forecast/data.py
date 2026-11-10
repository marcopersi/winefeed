"""1.2: load one wine/vintage/size series from ``forecast_input``.

Read-only (G6): never writes to the master DB.
"""
import numpy as np
import pandas as pd

_COLUMNS = ["date", "y", "provider", "qty"]


def load_series(conn, wine_ref_id, vintage, size_class):
    """Load one ``(wine_ref_id, vintage, size_class)`` series as a
    DataFrame with columns ``date, y, provider, qty`` (D2: ``y =
    ln(price_per_bottle_eur)``; the raw EUR price itself is recovered
    with ``np.exp(y)`` wherever a caller needs it, so it is not carried
    as its own column here).

    Sorted by ``(date, lot_id)`` for a deterministic row order (G5):
    ``date`` alone repeats within a series whenever two lots sold on the
    same day, so ``lot_id`` breaks the tie reproducibly instead of
    leaving it to SQLite's unspecified row order. ``date`` is parsed from
    the DB's plain ISO date string (``_normalize_lot_date``, 0.1), which
    carries no timezone, so the result is naturally timezone-free -- no
    explicit stripping needed, but tested for anyway (a future loader
    change that starts writing a timestamp must not silently introduce
    one).

    An unknown or genuinely empty series returns a DataFrame with these
    same columns and zero rows (not an error, not None) -- G3 leaves
    deciding INSUFFICIENT_DATA to the caller, not this loader.
    """
    rows = conn.execute(
        """
        SELECT fi.lot_date, fi.price_per_bottle_eur, p.name, l.quantity
        FROM forecast_input fi
        JOIN lots l ON l.id = fi.lot_id
        JOIN providers p ON p.id = fi.provider_id
        WHERE fi.wine_ref_id = ? AND fi.vintage = ? AND fi.size_class = ?
        ORDER BY fi.lot_date, fi.lot_id
        """,
        (wine_ref_id, vintage, size_class),
    ).fetchall()

    df = pd.DataFrame(
        rows, columns=["date", "price", "provider", "qty"])
    df["date"] = pd.to_datetime(df["date"])
    df["y"] = np.log(df["price"].astype(float))
    df["qty"] = df["qty"].astype("Int64")
    return df[_COLUMNS]


def load_all_series(conn):
    """Bulk variant of ``load_series`` for the evaluator (1.5), which
    needs every one of the ~120k series at once -- one query instead of
    one per series (``_load_fe_frame``, forecast/models.py, uses the
    same one-query-not-N pattern for the same reason).

    Returns a list of ``((wine_ref_id, vintage, size_class), df)``
    pairs, sorted by the key; each ``df`` is shaped exactly like
    ``load_series``'s own return value (same columns, same sort order
    within the series).

    Deliberately does NOT split via ``df.groupby(...)`` -- measured on
    the live DB (~971k rows / ~120k series, median series size 2):
    ``groupby`` + one ``reset_index`` per group took **40 minutes**,
    pandas' per-group splitting overhead dominating for this many tiny
    groups. A plain boundary scan over the already-SQL-sorted rows
    (same key-change detection ``_classify_lots``-style code does over
    a cursor, just vectorised here) finds the same slices in low single
    digit seconds -- ``df.iloc[start:end]`` is a cheap view, not a
    fresh per-group object."""
    rows = conn.execute(
        """
        SELECT fi.wine_ref_id, fi.vintage, fi.size_class,
               fi.lot_date, fi.price_per_bottle_eur, p.name, l.quantity,
               fi.lot_id
        FROM forecast_input fi
        JOIN lots l ON l.id = fi.lot_id
        JOIN providers p ON p.id = fi.provider_id
        ORDER BY fi.wine_ref_id, fi.vintage, fi.size_class,
                 fi.lot_date, fi.lot_id
        """
    ).fetchall()
    df = pd.DataFrame(rows, columns=[
        "wine_ref_id", "vintage", "size_class", "date", "price",
        "provider", "qty", "lot_id"])
    df["date"] = pd.to_datetime(df["date"])
    df["y"] = np.log(df["price"].astype(float))
    df["qty"] = df["qty"].astype("Int64")

    out = []
    n = len(df)
    if n == 0:
        return out
    keys = list(zip(df["wine_ref_id"].tolist(), df["vintage"].tolist(),
                    df["size_class"].tolist()))
    sub = df[_COLUMNS]
    start = 0
    for i in range(1, n + 1):
        if i == n or keys[i] != keys[start]:
            out.append((keys[start], sub.iloc[start:i].reset_index(
                drop=True)))
            start = i
    return out
