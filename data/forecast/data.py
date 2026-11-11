"""1.2: load one wine/vintage/size series from ``forecast_input``.

Read-only (G6): never writes to the master DB.

D8 (price-prediction-plan.md, User decision 2026-11-11): ``y`` is
HOUSE-ADJUSTED here -- ``ln(price_per_bottle_eur) - provider_effects.
offset`` (0 when a provider has no persisted offset, e.g. too few
observations for ``fit_provider_effects`` to include it) -- so every
model family downstream (1.4's baselines, 2.2's Local-Level) fits the
SAME de-noised series without each recomputing or forgetting the
adjustment. Consequence: ``np.exp(y)`` is no longer the literal
realised EUR price for a specific lot once its house has a nonzero
offset -- it's that price net of its house's own average effect. Any
caller that needs the real, unadjusted price must read
``price_per_bottle_eur`` directly, not reconstruct it from ``y``.

``house_offset`` (the same value already subtracted into ``y``) is its
own returned column too -- not redundant: ``forecast/eval.py``'s
rolling-origin harness needs to UNDO this full-data offset and reapply
a point-in-time one per origin (G1 fix, Copilot review 2026-11-11), and
can only do that if ``y + house_offset`` recovers the raw log price.
"""
import numpy as np
import pandas as pd

_COLUMNS = ["date", "y", "provider", "qty", "house_offset"]


def load_series(conn, wine_ref_id, vintage, size_class):
    """Load one ``(wine_ref_id, vintage, size_class)`` series as a
    DataFrame with columns ``date, y, provider, qty, house_offset``
    (D2/D8: ``y = ln(price_per_bottle_eur) - house_offset``, see this
    module's own docstring).

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
        SELECT fi.lot_date, fi.price_per_bottle_eur, p.name, l.quantity,
               COALESCE(pe.offset, 0) AS house_offset
        FROM forecast_input fi
        JOIN lots l ON l.id = fi.lot_id
        JOIN providers p ON p.id = fi.provider_id
        LEFT JOIN provider_effects pe ON pe.provider_id = fi.provider_id
        WHERE fi.wine_ref_id = ? AND fi.vintage = ? AND fi.size_class = ?
        ORDER BY fi.lot_date, fi.lot_id
        """,
        (wine_ref_id, vintage, size_class),
    ).fetchall()

    df = pd.DataFrame(
        rows, columns=["date", "price", "provider", "qty", "house_offset"])
    df["date"] = pd.to_datetime(df["date"])
    df["y"] = np.log(df["price"].astype(float)) - df["house_offset"]
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
               fi.lot_id, COALESCE(pe.offset, 0) AS house_offset
        FROM forecast_input fi
        JOIN lots l ON l.id = fi.lot_id
        JOIN providers p ON p.id = fi.provider_id
        LEFT JOIN provider_effects pe ON pe.provider_id = fi.provider_id
        ORDER BY fi.wine_ref_id, fi.vintage, fi.size_class,
                 fi.lot_date, fi.lot_id
        """
    ).fetchall()
    df = pd.DataFrame(rows, columns=[
        "wine_ref_id", "vintage", "size_class", "date", "price",
        "provider", "qty", "lot_id", "house_offset"])
    df["date"] = pd.to_datetime(df["date"])
    df["y"] = np.log(df["price"].astype(float)) - df["house_offset"]
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
