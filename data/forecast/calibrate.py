"""Stufe 4 (KISS v1, siehe docs/price-prediction-plan.md Stufe 3/4):
Split-Conformal-Kalibrierung von local_level's Prognoseintervallen, je
density_class x Horizont x Konfidenzniveau (50/80/95 %, eval.INTERVALS).

Advisor-Entscheid 2026-11-21: KEIN separates Fallback-MODELL fuer Stufe 3
(Gruppenindex/Pseudo-Repeat-Sales/EB-Shrinkage) -- die einzige noch offene
Stufe-2-Luecke war Coverage je Dichteklasse, und 4.1 schliesst genau diese
Luecke durch Konstruktion. Ein zweites Modell fuer dieselbe Luecke waere
Overengineering. Stufe 3 wird hier stattdessen zur REGEL (3.6: "wenn nicht
erreichbar => INSUFFICIENT_DATA, das ist das Ergebnis, kein Fehler"): jede
density_class, deren 80 %-Intervall nach Kalibrierung sein Held-out-Band
[77,83] nicht trifft, wird als INSUFFICIENT_DATA klassifiziert statt eine
unbelegte Prognose zu zeigen -- siehe ``classify``.

Validierung zeitlich von der Kalibrierung getrennt (kein Leck): die
Quantil-Korrektur wird auf den FRUEHEN Rolling-Origins gefittet, Coverage
auf dem spaetesten, bislang ungesehenen Origin gemessen. Zwei Konsequenzen
davon, beide senior-review-gefunden (2026-11-21), nicht geraten:

1. ``eval.split``'s Ziel-Fenster aufeinanderfolgender Origins ueberlappen
  (z. B. "12m": FIT-Origin 2025-01-01 zielt auf [2025-01-01,2026-01-01),
  TEST-Origin 2025-07-01 auf [2025-07-01,2026-07-01) -- 6 Monate
  Overlap). Eine Zielzeile, die in beiden Fenstern liegt, wuerde sonst
  sowohl die Korrektur FITten als auch ihre eigene Coverage "pruefen" --
  dieselbe Leck-Klasse, die der Copilot-Review in Stufe 2 zweimal fand.
  ``_drop_overlapping_targets`` entfernt jede TEST-Zeile, deren
  (series_key, target_date) auch unter einem FIT-Origin auftrat.
2. Der TEST-Origin liegt naeher an ``as_of`` als die FIT-Origins, daher
  sind seine REALISIERTEN ``gap_days`` systematisch kuerzer (rechts-
  zensiert) als die der FIT-Origins (siehe ``_gap_days_summary`` im
  Report). Das ist mit nur 2-4 verfuegbaren Rolling-Origins nicht
  aufloesbar, ohne eine zweite, aufwendigere Validierungs-Architektur zu
  bauen (rotierende Origins) -- bewusst nicht in v1 (KISS-Entscheid,
  gleiche Begruendung wie gegen ein Stufe-3-Fallback-Modell). Wird nur
  sichtbar gemacht, nicht korrigiert; die tatsaechliche Entscheidung
  (``classify``) faellt in die konservative Richtung (Ueberdeckung ->
  INSUFFICIENT_DATA), nie in eine optimistische.

Residuen werden, wie jede Metrik in ``eval.py`` (``_scored``), OHNE
``extrapolation_flag``-Zeilen berechnet -- ohne diesen Filter wuerde
``calibrate.py`` eine andere (kontaminierte) Grundgesamtheit kalibrieren
als die, gegen die ``write_baseline_report`` direkt daneben seine eigenen
Coverage-/Pinball-Zahlen ausweist.

    python3 -m forecast.calibrate --db /Volumes/samsung/winefeed-data/wine_auction_prices.sqlite

Schreibt drei Artefakte (Pfade standardmaessig relativ zu DIESEM Modul,
nicht zum Arbeitsverzeichnis -- das Kommando oben funktioniert daher aus
jedem cwd, nicht nur aus ``data/``):
- ``--backtest-out``: der rohe local_level-Rueckblick (write_baseline_report,
  unveraendert, einzige Komponente: 1 statt 6 Modelle).
- ``--table-out``: die Kalibrierungstabelle (JSON), die Stufe 5 (Serving,
  noch nicht gebaut) spaeter direkt laedt. Jede bekannte density_class
  (``eval._DENSITY_BINS`` + "10+") hat garantiert einen Eintrag (Fallback
  auf den gepoolten Wert "_pooled"), damit ein kuenftiger Lader nicht
  selbst wissen muss, dass dieser Fallback existiert.
- ``--report-out``: Held-out-Coverage je Horizont/density_class/Niveau,
  mit der resultierenden forecast/INSUFFICIENT_DATA-Entscheidung.
"""
# pylint: disable=protected-access
# -- protected-access: reusing eval.py's own internal _scored (the
# common first-step filter every metric function there applies) and
# _DENSITY_BINS (the one source of truth for density_class labels),
# same precedent as eval.py's own reach into build_db._outlier_lot_ids.
import argparse
import datetime
import json
import pathlib
import sqlite3

from . import eval as feval
from . import models as fmodels

# 2.5/3.6's eigenes Zielband fuer die 80 %-Evidenz -- nicht neu erfunden.
_BAND = (0.77, 0.83)
_DECISION_LEVEL = 0.80

# Jede density_class, die jemals vorkommen kann -- aus eval.py's eigener
# Quelle abgeleitet (nicht hier zweite Wahrheit duplizieren).
_KNOWN_DENSITY_CLASSES = tuple(
    label for _, _, label in feval._DENSITY_BINS) + ("10+",)

_PKG_DIR = pathlib.Path(__file__).resolve().parent
_REPO_ROOT = _PKG_DIR.parent.parent
_DEFAULT_BACKTEST_OUT = str(
    _REPO_ROOT / "docs" / "forecast-calibration-backtest.md")
_DEFAULT_REPORT_OUT = str(
    _REPO_ROOT / "docs" / "forecast-calibration-report.md")
_DEFAULT_TABLE_OUT = str(_PKG_DIR / "calibration_table.json")


def _abs_resid(rows_df):
    return (rows_df["y_true"] - rows_df["q0.5"]).abs()


def fit_table(rows_df):
    """{density_class: {level: correction}} aus EINEM (bereits
    ``feval._scored``-gefilterten) Split von ``eval.evaluate``'s
    Pro-Ziel-Zeilen. ``correction`` ist das Quantil der absoluten
    Log-Residuen (|y_true - Median-Prognose|) auf ``level`` -- Plan-
    Wortlaut 4.1: "Intervall = Modell-Median +/- Quantil der absoluten
    Log-Fehler". ``"_pooled"`` ist der ungruppierte Fallback, auch
    direkt als Wert fuer jede ``_KNOWN_DENSITY_CLASSES``-Klasse
    eingetragen, die in diesem Split nicht vorkam (Review-Fix: ein
    kuenftiger Leser der JSON-Tabelle soll nie selbst auf "_pooled"
    zurueckfallen muessen, um einen KeyError zu vermeiden)."""
    df = rows_df.assign(_resid=_abs_resid(rows_df))
    table = {
        "_pooled": {
            str(level): float(df["_resid"].quantile(level))
            for level in feval.INTERVALS
        }
    }
    for dclass, grp in df.groupby("density_class"):
        table[dclass] = {
            str(level): float(grp["_resid"].quantile(level))
            for level in feval.INTERVALS
        }
    for dclass in _KNOWN_DENSITY_CLASSES:
        table.setdefault(dclass, dict(table["_pooled"]))
    return table


def _correction(table, dclass, level):
    bucket = table.get(dclass, table["_pooled"])
    return bucket[str(level)]


def held_out_coverage(rows_df, table):
    """Coverage (Anteil |y_true - Median| <= Korrektur) je density_class
    x Niveau, mit einer auf einem ANDEREN (frueheren) Split gefitteten
    Tabelle -- der eigentliche Beleg, keine per-Konstruktion-Zahl."""
    df = rows_df.assign(_resid=_abs_resid(rows_df))
    out = {}
    for dclass, grp in df.groupby("density_class"):
        row = {"n": int(len(grp))}
        for level in feval.INTERVALS:
            corr = _correction(table, dclass, level)
            row[str(level)] = float((grp["_resid"] <= corr).mean())
        out[dclass] = row
    return out


def classify(coverage_row):
    """3.6 als Regel statt Modell: ausserhalb des [77,83]-Bands beim
    80 %-Niveau -> INSUFFICIENT_DATA ("das ist das Ergebnis, kein
    Fehler"), sonst ``forecast``."""
    cov = coverage_row[str(_DECISION_LEVEL)]
    return "forecast" if _BAND[0] <= cov <= _BAND[1] else "INSUFFICIENT_DATA"


def _split_fit_test(rows_df):
    """Chronologischer Split nach ``origin`` (nicht zufaellig, G1-
    Prinzip): alle bis auf den spaetesten Origin sind FIT, der spaeteste
    ist TEST. ``_drop_overlapping_targets`` (Review-Fix) macht daraus
    erst eine echte Trennung -- siehe Modul-Docstring Punkt 1."""
    origins = sorted(rows_df["origin"].unique())
    if len(origins) < 2:
        raise SystemExit(
            f"zu wenige Rolling-Origins ({len(origins)}) fuer eine "
            "zeitlich getrennte Validierung -- siehe half_year_origins")
    fit_origins, test_origin = origins[:-1], origins[-1]
    fit_rows = rows_df[rows_df["origin"].isin(fit_origins)]
    test_rows = rows_df[rows_df["origin"] == test_origin]
    test_rows = _drop_overlapping_targets(fit_rows, test_rows)
    return fit_origins, test_origin, fit_rows, test_rows


def _drop_overlapping_targets(fit_rows, test_rows):
    """Review-Fix (Finding 1): ``eval.split``'s Ziel-Fenster
    aufeinanderfolgender Origins ueberlappen, daher kann dieselbe
    realisierte Beobachtung (identifiziert durch series_key +
    target_date) als Zielzeile unter MEHREREN Origins auftauchen. Ohne
    diesen Schritt koennte ``fit_table`` und ``held_out_coverage`` auf
    derselben Beobachtung arbeiten -- kein echtes Held-out mehr."""
    seen = set(zip(fit_rows["series_key"], fit_rows["target_date"]))
    keep = [key not in seen
           for key in zip(test_rows["series_key"], test_rows["target_date"])]
    return test_rows[keep]


def _gap_days_summary(rows_df):
    return {
        "n": int(len(rows_df)),
        "median": float(rows_df["gap_days"].median()) if len(rows_df) else None,
        "p90": float(rows_df["gap_days"].quantile(0.9)) if len(rows_df) else None,
    }


def _format_report(as_of, per_horizon):
    lines = [
        "# Forecast Calibration Report",
        "",
        f"Stand: {as_of} -- Stufe 4.1 (Split-Conformal, local_level), "
        "Stufe 3 als Regel (3.6) statt Modell. Details/Begruendung: "
        "data/forecast/calibrate.py Modul-Docstring.",
        "",
    ]
    for horizon, info in per_horizon.items():
        lines.append(f"## Horizon: {horizon}")
        lines.append("")
        lines.append(
            f"FIT-Origins: {[str(o.date()) for o in info['fit_origins']]} "
            f"-- TEST-Origin (held-out): {info['test_origin'].date()}")
        lines.append("")
        g_fit, g_test = info["gap_days_fit"], info["gap_days_test"]
        lines.append(
            f"gap_days (Tage Origin->realisierte Zielzeile) -- FIT: "
            f"median={g_fit['median']:.0f} p90={g_fit['p90']:.0f} "
            f"(n={g_fit['n']}); TEST: median={g_test['median']:.0f} "
            f"p90={g_test['p90']:.0f} (n={g_test['n']}) -- siehe "
            "Modul-Docstring Punkt 2 (Rechtszensierung des TEST-Origins, "
            "bewusst nicht korrigiert).")
        lines.append("")
        lines.append(
            "| density_class | n (test) | Coverage 50% | Coverage 80% | "
            "Coverage 95% | Entscheidung |")
        lines.append("|---|---|---|---|---|---|")
        for dclass, row in sorted(info["coverage"].items()):
            lines.append(
                f"| {dclass} | {row['n']} | {row['0.5']:.3f} | "
                f"{row['0.8']:.3f} | {row['0.95']:.3f} | "
                f"{info['decisions'][dclass]} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Pfad zur Master-DB")
    parser.add_argument(
        "--as-of", default=None,
        help="ISO-Datum (Default: heute; G5 explizit fuer Reproduzierbarkeit)")
    parser.add_argument("--backtest-out", default=_DEFAULT_BACKTEST_OUT)
    parser.add_argument("--report-out", default=_DEFAULT_REPORT_OUT)
    parser.add_argument("--table-out", default=_DEFAULT_TABLE_OUT)
    args = parser.parse_args()

    as_of = args.as_of or datetime.date.today().isoformat()
    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    try:
        forecaster = fmodels.make_local_level_forecaster()
        rows_by_model_horizon = feval.write_baseline_report(
            conn, {"local_level": forecaster}, as_of, args.backtest_out)
    finally:
        conn.close()

    table = {"as_of": as_of}
    per_horizon = {}
    for horizon in (fmodels.HORIZON_NEXT, fmodels.HORIZON_12M):
        rows_df = feval._scored(rows_by_model_horizon[("local_level", horizon)])
        fit_origins, test_origin, fit_rows, test_rows = (
            _split_fit_test(rows_df))
        tbl = fit_table(fit_rows)
        coverage = held_out_coverage(test_rows, tbl)
        decisions = {dclass: classify(row)
                    for dclass, row in coverage.items()}
        table[horizon] = {
            "fit_origins": [str(o.date()) for o in fit_origins],
            "test_origin": str(test_origin.date()),
            "correction": tbl,
            "held_out_coverage": coverage,
            "decision": decisions,
        }
        per_horizon[horizon] = {
            "fit_origins": fit_origins, "test_origin": test_origin,
            "coverage": coverage, "decisions": decisions,
            "gap_days_fit": _gap_days_summary(fit_rows),
            "gap_days_test": _gap_days_summary(test_rows),
        }

    with open(args.table_out, "w", encoding="utf-8") as f:
        json.dump(table, f, indent=2, sort_keys=True)
    with open(args.report_out, "w", encoding="utf-8") as f:
        f.write(_format_report(as_of, per_horizon))
    print(f"wrote {args.table_out}, {args.report_out}, {args.backtest_out} "
         f"(as_of={as_of})")


if __name__ == "__main__":
    main()
