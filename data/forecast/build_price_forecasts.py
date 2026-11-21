"""Stufe 5.1/5.2 (KISS v1, siehe docs/price-prediction-plan.md Stufe 5):
baut/befuellt die ``price_forecasts``-Tabelle in der Master-DB mit
local_level-Prognosen, kalibriert durch Stufe 4.1's
``calibration_table.json``, fuer jede Serie aus ``forecast_input`` und
beide Horizonte ("next"/"12m").

Muss NACH einem vollen DB-Rebuild laufen (``build_db.py`` baut die
Datei jedesmal komplett neu, tmp + ``os.replace`` -- ``price_forecasts``
existiert in der neuen Datei noch nicht; 5.3's eigene Reihenfolge
"nach process.yml als Folgeschritt" ist genau deshalb so festgelegt).
Anders als ``eval.py``/``calibrate.py`` oeffnet dieses Modul die DB
daher READ-WRITE, nicht ``mode=ro``.

Produktionspfad (``cutoff=None``, wie ``forecast/data.py``'s D8-Doku
selbst sagt): ``train`` ist die GANZE Serie (kein Rolling-Origin-Split
-- es gibt keine zukuenftigen Daten, die lecken koennten), ``origin``
ist das gemeinsame ``as_of`` dieses Laufs. ``n_train``/``density_class``
werden exakt wie im Backtest aus ``len(train)`` gebildet (hier: die
ganze Serie, da nichts abgeschnitten wird).

Stufe 3 (die Regel, kein Modell -- siehe calibrate.py) wirkt hier
direkt: jede density_class, deren Stufe-4-Entscheidung
"INSUFFICIENT_DATA" ist, bekommt eine Zeile OHNE Punktwert (``median_eur``/
``q*_eur`` bleiben NULL, ``flags='INSUFFICIENT_DATA'``) -- 5.4's eigene
API-Vorgabe ("Antwort ohne Punktwert bei INSUFFICIENT_DATA") wird damit
schon hier in der Tabelle umgesetzt, nicht erst im Endpoint. Eine Serie,
fuer die ``local_level`` ueberhaupt keinen Fit versucht (zu wenige
Monatspunkte) oder der Fit scheitert (FIT_FAILED), bekommt dieselbe
Behandlung -- 3.6: "das ist das Ergebnis, kein Fehler", die genaue
interne Ursache ist fuer eine Serving-Zeile nicht relevant.

Alle Preis-Spalten sind ECHTE EUR-pro-Flasche-Werte, nicht Log-y: das
Modell/die Kalibrierung rechnen intern in ``y = ln(price_per_bottle_eur)
- house_offset`` (D8, ``forecast/data.py``), ``math.exp()`` wird erst
ganz am Ende auf Median/Baender angewendet (NACH der additiven
Kalibrierungs-Korrektur, die selbst in Log-Raum gilt -- Differenzen dort
sind korrekt, ein direkt gelesener Log-Wert waere es nicht). D8's eigene
Doku warnt genau davor, ``y`` direkt als EUR zu lesen, wenn eine
Serving-Schicht das irgendwann tut -- das ist hier dieser Punkt.
``house_offset`` wird NICHT zurueckaddiert: die Prognose ist bewusst
"haus-neutral" (das Niveau, das der house-offset-bereinigten Serie
entspricht), nicht an ein bestimmtes, noch unbekanntes zukuenftiges
Auktionshaus gebunden -- im UI als Schaetzung, nicht als Zuschlag eines
bestimmten Hauses zu beschriften.

Idempotent per ``model_version``: ein Lauf loescht erst alle Zeilen der
eigenen ``MODEL_VERSION``, dann fuegt er die neuen ein (eine Transaktion)
-- einfacher und robuster als ein SQL-UPSERT gegen eine nullable
Zusammensetzung (``vintage``/``size_class`` koennen NULL sein, siehe
``forecast_input``), ohne auf die NULL-Tuecken von SQLite-UNIQUE-
Constraints angewiesen zu sein.

    python3 -m forecast.build_price_forecasts \\
        --db /Volumes/samsung/winefeed-data/wine_auction_prices.sqlite
"""
import argparse
import datetime
import json
import math
import pathlib
import sqlite3

import pandas as pd

# pylint: disable=protected-access
# -- protected-access: reusing calibrate.py's own _correction (the one
# place the pooled-fallback lookup is defined) instead of a second,
# independently-maintained copy of the same logic.
from . import calibrate
from . import data
from . import eval as feval
from . import models as fmodels

MODEL_VERSION = "local_level-conformal-v1"

_PKG_DIR = pathlib.Path(__file__).resolve().parent
_DEFAULT_CALIBRATION = str(_PKG_DIR / "calibration_table.json")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS price_forecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wine_ref_id INTEGER NOT NULL,
    vintage INTEGER,
    size_class REAL,
    horizon TEXT NOT NULL,
    method TEXT NOT NULL,
    model_version TEXT NOT NULL,
    n_obs INTEGER NOT NULL,
    last_obs_date TEXT,
    median_eur REAL,
    q025_eur REAL, q10_eur REAL, q25_eur REAL,
    q75_eur REAL, q90_eur REAL, q975_eur REAL,
    flags TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_price_forecasts_lookup
    ON price_forecasts (wine_ref_id, vintage, size_class, horizon);
"""

# level -> (lower_q, upper_q) column suffix pairs -- restates eval.
# INTERVALS' own (lo, hi) pairs under clean SQL column names (a literal
# "q0.25" column name is legal in SQLite but awkward everywhere else).
# The assertion keeps this honest if INTERVALS ever changes shape.
_LEVEL_COLUMNS = {0.50: ("q25_eur", "q75_eur"), 0.80: ("q10_eur", "q90_eur"),
                 0.95: ("q025_eur", "q975_eur")}
assert set(_LEVEL_COLUMNS) == set(feval.INTERVALS), (
    "_LEVEL_COLUMNS must mirror eval.INTERVALS' levels exactly")


def _load_calibration(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _decision(calib_horizon, dclass):
    return calib_horizon["decision"].get(dclass, "INSUFFICIENT_DATA")


def forecast_row(  # pylint: disable=too-many-positional-arguments
        series_key, df, horizon, calib_horizon, as_of, created_at,
        forecaster):
    # -- same pattern as eval.evaluate_series (also 6+ positional args,
    # each one a distinct, non-combinable input, not a parameter object
    # worth inventing just to appease this count).
    """One ``price_forecasts`` row for ``series_key`` at ``horizon``, or
    ``None`` if the series has literally zero observations (not a real
    series, ``load_all_series`` never actually emits this, defensive
    only). ``forecaster`` is injected (one shared instance per ``build``
    call, same convention as ``eval.evaluate``) so its ``.counters``
    aggregate over the whole run instead of resetting per series."""
    wine_ref_id, vintage, size_class = series_key
    n_obs = len(df)
    if n_obs == 0:
        return None
    last_obs_date = str(df["date"].max().date())
    row = {
        "wine_ref_id": wine_ref_id, "vintage": vintage,
        "size_class": size_class, "horizon": horizon,
        "method": "local_level", "model_version": MODEL_VERSION,
        "n_obs": n_obs, "last_obs_date": last_obs_date,
        "median_eur": None, "q025_eur": None, "q10_eur": None,
        "q25_eur": None, "q75_eur": None, "q90_eur": None,
        "q975_eur": None,
        "flags": "INSUFFICIENT_DATA", "created_at": created_at,
    }
    forecast = forecaster(df, as_of, horizon)
    if forecast is None:
        return row
    dclass = feval.density_class(n_obs)
    decision = _decision(calib_horizon, dclass)
    flags = None
    if feval.extrapolation_flag(forecast, df):
        flags = "EXTRAPOLATION"
    if decision != "forecast":
        row["flags"] = "INSUFFICIENT_DATA"
        return row
    median_log = forecast[0.50]
    row["median_eur"] = math.exp(median_log)
    for level, (lo_col, hi_col) in _LEVEL_COLUMNS.items():
        corr = calibrate._correction(calib_horizon["correction"], dclass, level)
        row[lo_col] = math.exp(median_log - corr)
        row[hi_col] = math.exp(median_log + corr)
    row["flags"] = flags
    return row


def build(conn, calibration, as_of):
    as_of_ts = pd.Timestamp(as_of)
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    series = data.load_all_series(conn)
    forecaster = fmodels.make_local_level_forecaster()
    rows = []
    for series_key, df in series:
        for horizon in (fmodels.HORIZON_NEXT, fmodels.HORIZON_12M):
            row = forecast_row(
                series_key, df, horizon, calibration[horizon], as_of_ts,
                created_at, forecaster)
            if row is not None:
                rows.append(row)
    print(f"local_level counters (aggregate over {len(series)} series x 2"
         f" horizons): {forecaster.counters}")

    conn.executescript(_SCHEMA)
    conn.execute(
        "DELETE FROM price_forecasts WHERE model_version = ?",
        (MODEL_VERSION,))
    columns = ["wine_ref_id", "vintage", "size_class", "horizon", "method",
              "model_version", "n_obs", "last_obs_date", "median_eur",
              "q025_eur", "q10_eur", "q25_eur", "q75_eur", "q90_eur",
              "q975_eur", "flags", "created_at"]
    conn.executemany(
        f"INSERT INTO price_forecasts ({', '.join(columns)}) "
        f"VALUES ({', '.join(['?'] * len(columns))})",
        [tuple(row[c] for c in columns) for row in rows])
    conn.commit()
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Pfad zur Master-DB")
    parser.add_argument("--calibration", default=_DEFAULT_CALIBRATION)
    parser.add_argument(
        "--as-of", default=None,
        help="ISO-Datum (Default: heute; sollte zum calibration_table.json"
        " passen, da dessen Dichteklassen-Entscheidung davon abhaengt, wie"
        " 'next'/'12m' zum Zeitpunkt der Kalibrierung definiert waren)")
    args = parser.parse_args()

    as_of = args.as_of or datetime.date.today().isoformat()
    calibration = _load_calibration(args.calibration)
    conn = sqlite3.connect(args.db)
    try:
        n_rows = build(conn, calibration, as_of)
    finally:
        conn.close()
    print(f"wrote {n_rows} price_forecasts rows (model_version="
         f"{MODEL_VERSION}, as_of={as_of}, calibration={args.calibration})")


if __name__ == "__main__":
    main()
