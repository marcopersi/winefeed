"""1.5: Rolling-Origin-Evaluator (G1/G2) -- splits each series at fixed
calendar origins, scores forecasters against observations that were
genuinely in the future at that origin. No random splits (G1).

A ``Forecaster`` is ``forecaster(train, origin, horizon) -> dict | None``:
``train`` is a ``load_series``-shaped DataFrame already restricted to
``date < origin`` (strict -- a row dated exactly on ``origin`` is a
target, never training data); ``origin``/``horizon`` let a forecaster
anchor an extrapolation (e.g. 1.4's trend baseline) even though it
ignores the already-pre-filtered ``train``. Returns ``None`` for
INSUFFICIENT_DATA (G3) -- the harness never raises on that, only counts
it. A real return value is a dict keyed by every one of
``models.QUANTILE_LEVELS`` (D4's three central intervals), value =
forecast ``y`` (log-EUR-per-0.75l, D2) at that quantile.

Every metric here except the EUR-scale MAPE/MdAPE pair is computed in
log-y space, not EUR -- Pinball-Loss/Winkler/coverage/width on raw EUR
would be dominated by a handful of very expensive wines (Pétrus, DRC,
...); MAPE/MdAPE get their own EUR-scale numbers specifically because
G2 wants an EUR-interpretable point-forecast error, not because the
other metrics should also live there.

D8 (User decision, 2026-11-11): ``y`` is house-adjusted since
``forecast/data.py``'s loaders subtract each row's own provider's
offset. Senior-review finding, verified numerically (not assumed):
EVERY metric here stays correct regardless, because each row's
``y_true`` and its forecast are compared against EACH OTHER, never
against a different row's house -- the offset is a per-row constant
that cancels out of both a log-space difference (``a-b == (a+c)-(b+c)``)
and a ratio-based percentage error (``exp(a)/exp(b) ==
exp(a+c)/exp(b+c)``), so ``_eur_ape``'s ``np.exp(y_true)`` is NOT the
lot's real realised price in isolation, but the resulting MAPE/MdAPE
IS numerically identical to computing it from the real EUR price with
the same house offset added back to both sides first. This stops
holding the moment any FUTURE code reads an ABSOLUTE price straight
off this module's rows (not a difference or a ratio) -- that code must
add the row's own provider's offset back first, which this module's
rows do not carry today (only the already-adjusted ``y_true``/
quantiles). Flag this if Stufe 5's serving layer, or G7's fan-charts,
ever read an absolute EUR value out of here directly.
"""
import math

import numpy as np
import pandas as pd

from . import data
from .models import QUANTILE_LEVELS, HORIZON_NEXT, HORIZON_12M

# D4: the three nominal central intervals, as (lower_q, upper_q, alpha)
# -- alpha is the two-sided miss rate (1 - nominal coverage), the
# Winkler/interval-score parameter. All six q values are members of
# QUANTILE_LEVELS -- not a second, independent list.
INTERVALS = {
    0.50: (0.25, 0.75, 0.50),
    0.80: (0.10, 0.90, 0.20),
    0.95: (0.025, 0.975, 0.05),
}
# 1.5 spec: "Pinball-Loss (q=0,1/0,5/0,9)".
PINBALL_QS = (0.1, 0.5, 0.9)

# 3.6 names the first three density buckets ("n_obs in {1-2, 3-4, 5-9}");
# D5's own ">= 10 Beobachtungen" threshold is the top one -- not invented
# here, just applied one stage earlier (on TRAINING-set size at the
# origin, never full-series size, or this would leak future density
# into a past origin's forecast).
_DENSITY_BINS = [(0, 0, "0"), (1, 2, "1-2"), (3, 4, "3-4"), (5, 9, "5-9")]


def density_class(n_train):
    for lo, hi, label in _DENSITY_BINS:
        if lo <= n_train <= hi:
            return label
    return "10+"


def _qkey(q):
    return f"q{q}"


def half_year_origins(as_of, months_back=24):
    """Jan-1/Jul-1 calendar boundaries in ``[as_of - months_back,
    as_of]`` (G1/G2: "alle Jahres-/Halbjahresgrenzen der letzten 24
    M"). Pure function of ``as_of`` -- callers pass it explicitly
    rather than this defaulting to ``date.today()``, so a backtest run
    from an old snapshot is reproducible (G5)."""
    as_of = pd.Timestamp(as_of).normalize()
    start = as_of - pd.DateOffset(months=months_back)
    origins = []
    for year in range(start.year, as_of.year + 1):
        for month in (1, 7):
            o = pd.Timestamp(year=year, month=month, day=1)
            if start <= o <= as_of:
                origins.append(o)
    return sorted(origins)


def admits_horizon(origin, horizon, as_of):
    """The "next"-horizon target is a single future row with no window
    to right-censor. The "12m"-horizon target is a 12-month WINDOW
    though -- an origin within the last 12 months of ``as_of`` would
    only ever see a truncated slice of it, silently biasing that
    origin's coverage/width numbers low on sample size. Such origins
    are excluded from the 12m horizon entirely, not scored on a partial
    window."""
    if horizon == HORIZON_NEXT:
        return True
    if horizon == HORIZON_12M:
        return origin + pd.DateOffset(months=12) <= pd.Timestamp(as_of)
    raise ValueError(f"unknown horizon {horizon!r}")


def split(df, origin, horizon):
    """``(train, targets)``: ``train`` is strictly ``date < origin``
    (G1 -- a row dated exactly on ``origin`` belongs to the FUTURE
    side, not training). ``targets`` for "next" is the single nearest
    future row (D3: "nächste Auktionsbeobachtung", no second one);
    for "12m" it is every row in ``[origin, origin + 12 calendar
    months)`` -- calendar months (D3's own "+12 Monate" wording), not
    a fixed 365-day window."""
    train = df[df["date"] < origin]
    if horizon == HORIZON_NEXT:
        targets = df[df["date"] >= origin].iloc[:1]
    elif horizon == HORIZON_12M:
        end = origin + pd.DateOffset(months=12)
        targets = df[(df["date"] >= origin) & (df["date"] < end)]
    else:
        raise ValueError(f"unknown horizon {horizon!r}")
    return train, targets


def _validate_forecast(q_dict):
    """G4: hard abort on a malformed forecast (NaN/Inf, non-monotone
    quantiles) -- these are the two G4 checks that apply to a single
    forecast in isolation; the window-growing-with-horizon and
    EXTRAPOLATION-vs-last-median checks need context this function
    doesn't have (a model's own forecast history) and belong with
    whichever stage first has that context (1.4+)."""
    if set(q_dict) != set(QUANTILE_LEVELS):
        raise ValueError(
            f"forecast must supply exactly {sorted(QUANTILE_LEVELS)},"
            f" got {sorted(q_dict)}")
    values = [q_dict[q] for q in QUANTILE_LEVELS]
    if any(not math.isfinite(v) for v in values):
        raise ValueError(f"non-finite forecast value: {q_dict}")
    if any(a > b for a, b in zip(values, values[1:])):
        raise ValueError(f"forecast quantiles not monotone: {q_dict}")


# ln(0.2) / ln(5.0) -- the EUR-scale "[0.2x, 5x]" bound restated in
# log-y space (see extrapolation_flag's own docstring for why it has
# to be, not just could be, computed this way).
_EXTRAPOLATION_LOG_BOUNDS = (math.log(0.2), math.log(5.0))


def extrapolation_flag(forecast, train):
    """G4: "Median innerhalb [0,2x; 5x] des letzten Medians (sonst Flag
    EXTRAPOLATION, kein Abbruch)" -- a soft flag, never a hard failure
    (unlike ``_validate_forecast``'s two checks). "Letzter Median" is
    read here as the most recent actual observation in ``train``.

    Compares the ratio in LOG space (``forecast[0.5] - last_y`` against
    ``ln(0.2)``/``ln(5)``), not by ``exp()``-ing each side and dividing
    -- confirmed real crash on the live DB: a "trend" baseline
    extrapolated far enough on one real, short/noisy series that its
    raw log-y forecast exceeded ~709 (``math.exp``'s overflow point for
    a double), raising ``OverflowError`` and killing an otherwise-
    successful ~25-minute report run. The ratio itself is always
    representable even when either individual EUR value wouldn't be;
    computing it without ever leaving log space sidesteps the overflow
    entirely rather than guarding around it."""
    if train.empty:
        return False
    log_ratio = forecast[0.5] - float(train["y"].iloc[-1])
    lo, hi = _EXTRAPOLATION_LOG_BOUNDS
    return not lo <= log_ratio <= hi


def evaluate_series(df, series_key, forecaster, horizon, as_of, model_name):
    """Run one forecaster against one series' rolling origins, for one
    horizon. Returns ``(rows, n_candidates, n_insufficient)`` -- ``rows``
    is a list of per-scored-target-observation dicts (one row per
    ``load_series``-row inside the target window, so "next" contributes
    at most one row per origin but "12m" can contribute several);
    ``n_candidates``/``n_insufficient`` are counted per ORIGIN (G4's
    Zeilenbilanz unit), not per target row, since a forecaster is called
    once per origin regardless of how many target rows follow."""
    rows = []
    n_candidates = 0
    n_insufficient = 0
    for origin in half_year_origins(as_of):
        if not admits_horizon(origin, horizon, as_of):
            continue
        train, targets = split(df, origin, horizon)
        if targets.empty:
            continue
        n_candidates += 1
        forecast = forecaster(train, origin, horizon)
        if forecast is None:
            n_insufficient += 1
            continue
        _validate_forecast(forecast)
        n_train = len(train)
        dclass = density_class(n_train)
        extrapolation = extrapolation_flag(forecast, train)
        for _, t in targets.iterrows():
            row = {
                "model": model_name,
                "series_key": series_key,
                "origin": origin,
                "horizon": horizon,
                "target_date": t["date"],
                "provider": t["provider"],
                "n_train": n_train,
                "density_class": dclass,
                "gap_days": (t["date"] - origin).days,
                "y_true": t["y"],
                "extrapolation_flag": extrapolation,
            }
            for q in QUANTILE_LEVELS:
                row[_qkey(q)] = forecast[q]
            rows.append(row)
    return rows, n_candidates, n_insufficient


def evaluate(series_iter, forecaster, horizon, as_of, model_name):
    """``evaluate_series`` over every ``(series_key, df)`` pair (e.g.
    ``data.load_all_series(conn)``). Returns ``(rows_df, tally)``;
    ``tally`` has ``n_candidates``/``n_forecast``/``n_insufficient``,
    which must sum as ``n_forecast + n_insufficient == n_candidates``
    (G4's Zeilenbilanz, asserted by the caller/report, not here)."""
    rows = []
    n_candidates = n_insufficient = 0
    for series_key, df in series_iter:
        s_rows, s_cand, s_insuff = evaluate_series(
            df, series_key, forecaster, horizon, as_of, model_name)
        rows.extend(s_rows)
        n_candidates += s_cand
        n_insufficient += s_insuff
    columns = ["model", "series_key", "origin", "horizon", "target_date",
               "provider", "n_train", "density_class", "gap_days",
               "y_true", "extrapolation_flag"] + [
                   _qkey(q) for q in QUANTILE_LEVELS]
    rows_df = pd.DataFrame(rows, columns=columns)
    tally = {
        "n_candidates": n_candidates,
        "n_forecast": n_candidates - n_insufficient,
        "n_insufficient": n_insufficient,
    }
    return rows_df, tally


# --------------------------------------------------------------------------- #
# Metrics -- each a pure function over an ``evaluate()`` rows DataFrame.
# --------------------------------------------------------------------------- #

def _eur_ape(rows_df):
    """Absolute percentage error on the EUR scale, for every row --
    may be ``inf``/``nan``, or merely an astronomically large FINITE
    double (confirmed real occurrence on the live DB -- a first
    version of this function's callers filtered ``np.isfinite`` alone,
    which missed exactly this case: a "trend" forecast whose ``exp()``
    lands just under a double's overflow point, e.g. ~2.8e50, is
    perfectly finite and still utterly meaningless as a predicted EUR
    price). See ``extrapolation_exclusion_mask`` for the actual filter.

    ``np.exp(y_true)`` is NOT the lot's real realised price since D8
    (it's house-adjusted) -- the resulting ratio/APE is still correct;
    see this module's own docstring for why."""
    y_true = np.exp(rows_df["y_true"].to_numpy(dtype=float))
    with np.errstate(over="ignore"):
        y_pred = np.exp(rows_df[_qkey(0.5)].to_numpy(dtype=float))
    return np.abs(y_true - y_pred) / y_true


def extrapolation_exclusion_mask(rows_df):
    """True for rows EVERY metric below must exclude -- reuses
    ``extrapolation_flag`` (G4) rather than a second, ad-hoc magnitude
    threshold: a forecast flagged as an implausible departure from the
    series' own last observation is usually a baseline (most often
    "trend") that went off the rails, but not always --
    ``extrapolation_flag`` compares against ``train.y.iloc[-1]``
    specifically, so it can also fire when that one last observation
    was itself the outlier and the forecast is the sane value.

    Applied uniformly to MAPE/MdAPE AND Pinball/Winkler/Coverage/width
    (User decision, 2026-11-10, G2-scope question): an earlier version
    excluded these rows from MAPE/MdAPE only -- confirmed on the live
    report, the SAME rows still dominated Pinball/Winkler for the
    affected groups (e.g. ``trend``/``n_train=3-4``: Pinball q0.5=1.23,
    Winkler 95%=78 vs. ~0.2/~5 elsewhere), just less visibly than
    MAPE's literal infinities -- log space damps 1e50 down to 78, it
    doesn't fix it. Since G2 names Pinball-Loss as the primary "beats
    the baseline" criterion, leaving that contamination in would let a
    later model "win" for free, the same false-win this exclusion was
    built to prevent for MAPE.

    A residual ``~np.isfinite`` check (on the EUR-scale APE
    specifically) stays as a safety net for whatever the flag doesn't
    happen to catch."""
    ape = _eur_ape(rows_df)
    return (rows_df["extrapolation_flag"].to_numpy(dtype=bool)
           | ~np.isfinite(ape))


def n_extrapolation_excluded(rows_df):
    """Count of rows excluded from every metric by
    ``extrapolation_exclusion_mask`` -- reported explicitly, same
    "flag, never silently discard" convention as 0.6's OUTLIER/
    DUP_CANDIDATE."""
    return int(extrapolation_exclusion_mask(rows_df).sum())


def _scored(rows_df):
    """``rows_df`` with every ``extrapolation_exclusion_mask`` row
    removed -- the common first step of every metric function below."""
    return rows_df[~extrapolation_exclusion_mask(rows_df)]


def mape_eur(rows_df):
    scored = _scored(rows_df)
    if scored.empty:
        return float("nan")
    return float(_eur_ape(scored).mean())


def mdape_eur(rows_df):
    scored = _scored(rows_df)
    if scored.empty:
        return float("nan")
    return float(np.median(_eur_ape(scored)))


def pinball_loss(rows_df, q):
    scored = _scored(rows_df)
    if scored.empty:
        return float("nan")
    y_true = scored["y_true"].to_numpy(dtype=float)
    y_pred = scored[_qkey(q)].to_numpy(dtype=float)
    diff = y_true - y_pred
    loss = np.where(diff >= 0, q * diff, (q - 1) * diff)
    return float(np.mean(loss))


def winkler_score(rows_df, level):
    """Gneiting-Raftery interval score for the ``level`` nominal
    interval (e.g. 0.80 -> the [q0.10, q0.90] pair)."""
    scored = _scored(rows_df)
    if scored.empty:
        return float("nan")
    lo_q, hi_q, alpha = INTERVALS[level]
    lo = scored[_qkey(lo_q)].to_numpy(dtype=float)
    hi = scored[_qkey(hi_q)].to_numpy(dtype=float)
    y = scored["y_true"].to_numpy(dtype=float)
    width = hi - lo
    score = width.copy()
    below = y < lo
    above = y > hi
    score = np.where(below, width + (2.0 / alpha) * (lo - y), score)
    score = np.where(above, width + (2.0 / alpha) * (y - hi), score)
    return float(np.mean(score))


def coverage(rows_df, level):
    scored = _scored(rows_df)
    if scored.empty:
        return float("nan")
    lo_q, hi_q, _ = INTERVALS[level]
    lo = scored[_qkey(lo_q)].to_numpy(dtype=float)
    hi = scored[_qkey(hi_q)].to_numpy(dtype=float)
    y = scored["y_true"].to_numpy(dtype=float)
    return float(np.mean((y >= lo) & (y <= hi)))


def median_width(rows_df, level):
    scored = _scored(rows_df)
    if scored.empty:
        return float("nan")
    lo_q, hi_q, _ = INTERVALS[level]
    return float(
        (scored[_qkey(hi_q)] - scored[_qkey(lo_q)]).median())


_NAN_METRICS = {
    "n": 0, "mape_eur": float("nan"), "mdape_eur": float("nan"),
    "n_extrapolation_excluded": 0,
    **{f"pinball_q{q}": float("nan") for q in PINBALL_QS},
    **{f"winkler_{int(round(lvl * 100))}": float("nan") for lvl in INTERVALS},
    **{f"coverage_{int(round(lvl * 100))}": float("nan") for lvl in INTERVALS},
    **{f"width_{int(round(lvl * 100))}": float("nan") for lvl in INTERVALS},
}


def compute_metrics(rows_df):
    """All of 1.5's metrics over one rows DataFrame, as a flat dict.
    Empty input returns NaNs with ``n=0`` rather than raising -- a
    (model, horizon, group) slice with zero scored rows is a normal
    outcome (e.g. a density class with no members in a given horizon),
    not an error."""
    if rows_df.empty:
        return dict(_NAN_METRICS)
    out = {
        "n": len(rows_df),
        "mape_eur": mape_eur(rows_df),
        "mdape_eur": mdape_eur(rows_df),
        "n_extrapolation_excluded": n_extrapolation_excluded(rows_df),
    }
    for q in PINBALL_QS:
        out[f"pinball_q{q}"] = pinball_loss(rows_df, q)
    for lvl in INTERVALS:
        pct = int(round(lvl * 100))
        out[f"winkler_{pct}"] = winkler_score(rows_df, lvl)
        out[f"coverage_{pct}"] = coverage(rows_df, lvl)
        out[f"width_{pct}"] = median_width(rows_df, lvl)
    return out


def summarize(rows_df):
    """Overall metrics plus the spec's two breakdowns ("Aufteilung nach
    Dichteklasse und Haus") over one (model, horizon) rows DataFrame.
    Callers looping over several models/horizons call this once per
    (model, horizon) slice -- it does not itself group by those, since
    most callers already have the rows split that way (``evaluate()``
    is itself called once per model/horizon)."""
    return {
        "overall": compute_metrics(rows_df),
        "by_density_class": {
            dc: compute_metrics(g)
            for dc, g in rows_df.groupby("density_class")},
        "by_provider": {
            p: compute_metrics(g)
            for p, g in rows_df.groupby("provider")},
    }


# --------------------------------------------------------------------------- #
# Report -- 1.5 AC: "Baseline-Report als Tabelle in
# docs/forecast-baseline-report.md (reproduzierbar per Befehl)".
# --------------------------------------------------------------------------- #

def _format_metrics_row(label, m):
    # n_extrapolation_excluded: rows excluded from EVERY metric in this
    # row via extrapolation_exclusion_mask (extrapolation_flag + a
    # residual isfinite check) -- shown unconditionally, not just when
    # nonzero, so a 0 here is legible as "checked, none excluded"
    # rather than a blank a reader can't tell apart from "not computed".
    return (f"| {label} | {m['n']} | {m['mape_eur']:.3f} | "
            f"{m['mdape_eur']:.3f} | {m['n_extrapolation_excluded']} | "
            f"{m['pinball_q0.1']:.4f} | "
            f"{m['pinball_q0.5']:.4f} | {m['pinball_q0.9']:.4f} | "
            f"{m['winkler_50']:.4f} | {m['coverage_50']:.3f} | "
            f"{m['width_50']:.3f} | {m['winkler_80']:.4f} | "
            f"{m['coverage_80']:.3f} | {m['width_80']:.3f} | "
            f"{m['winkler_95']:.4f} | {m['coverage_95']:.3f} | "
            f"{m['width_95']:.3f} |")


_REPORT_HEADER = (
    "| Gruppe | n | MAPE (EUR) | MdAPE (EUR) |"
    " N ausgeschlossen (EXTRAPOLATION, gilt für alle Spalten rechts) |"
    " Pinball q0.1 | Pinball q0.5 |"
    " Pinball q0.9 | Winkler 50% | Coverage 50% | Breite 50% |"
    " Winkler 80% | Coverage 80% | Breite 80% | Winkler 95% |"
    " Coverage 95% | Breite 95% |\n"
    "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")


def write_baseline_report(conn, forecasters, as_of, path):
    """Runs every ``{name: forecaster}`` entry over every series in
    ``conn`` (G6: caller opens ``conn`` read-only), for both horizons,
    and writes a Markdown table to ``path``. 1.5 ships this with
    ``forecasters`` normally empty (no baseline exists yet, see 1.4);
    the scaffold still needs to run cleanly end-to-end so 1.4 only has
    to add dict entries, not touch this function."""
    series = data.load_all_series(conn)
    lines = [
        "# Forecast Baseline Report",
        "",
        f"Stand: {as_of} (G1 Rolling-Origin, 24 Monate zurück,"
        f" docs/price-prediction-plan.md Stufe 1.5)",
        "",
    ]
    if not forecasters:
        lines.append(
            "_Keine Modelle registriert (1.5-Geruest; Baselines folgen"
            " in 1.4)._")
    for name, forecaster in forecasters.items():
        lines.append(f"## {name}")
        lines.append("")
        for horizon in (HORIZON_NEXT, HORIZON_12M):
            rows_df, tally = evaluate(series, forecaster, horizon, as_of,
                                      name)
            assert (tally["n_forecast"] + tally["n_insufficient"]
                    == tally["n_candidates"]), tally
            summary = summarize(rows_df)
            lines.append(f"### Horizon: {horizon}")
            lines.append("")
            lines.append(
                f"Zeilenbilanz: candidates={tally['n_candidates']} "
                f"forecast={tally['n_forecast']} "
                f"insufficient={tally['n_insufficient']}")
            lines.append("")
            lines.append(_REPORT_HEADER)
            lines.append(_format_metrics_row("alle", summary["overall"]))
            for dc, m in sorted(summary["by_density_class"].items()):
                lines.append(_format_metrics_row(f"n_train={dc}", m))
            for p, m in sorted(summary["by_provider"].items()):
                lines.append(_format_metrics_row(p, m))
            lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
