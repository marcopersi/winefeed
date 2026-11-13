"""1.3: fixed-effects model isolating house/lot effects from "true" wine
value. 1.4: baseline forecasting methods. 2.2-2.4: Local-Level (Kalman)
model.
"""
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm

# D4: 50/80/95% central intervals + median.
QUANTILE_LEVELS = [0.025, 0.10, 0.25, 0.50, 0.75, 0.90, 0.975]

# Below this many observations there is no residual to measure spread
# from at all (n=1: zero residuals, a zero-width interval that would be
# false certainty, not a baseline result -- G3). The real density floor
# for an actual forecast (D5, >= 10 obs/3 years/5 auctions) is a Stufe-2
# concern decided by backtest (2.1), not hardcoded here.
MIN_OBS = 2

# D15's "series active, last observation <= 36 months old" window
# (build_db.py's ``forecast_input`` view hardcodes the same "-36
# months" relative to "now" in SQL; this is the same threshold reused,
# origin-relative instead of now-relative, by ``_load_fe_frame``'s
# ``cutoff`` path and by ``forecast/eval.py``'s own per-origin recency
# check -- Copilot review 2026-11-11, Finding B).
RECENCY_MONTHS = 36

# D3: "next observation" (one step, irregular spacing) and "+12 months".
HORIZON_NEXT = "next"
HORIZON_12M = "12m"

# 1.4's residual backtest (``_retrospective_residuals``) is capped to
# this many of the most recent mini-origins -- see that function's own
# docstring for why (a handful of multi-thousand-row real series made
# an uncapped backtest O(n^2); the live full-report run was killed
# after 20+ minutes with no end in sight before this cap existed).
MAX_BACKTEST_STEPS = 50


# --------------------------------------------------------------------------- #
# 1.3 -- Haus-/Los-Effekte
# --------------------------------------------------------------------------- #

def _load_fe_frame(conn, cutoff=None, exclude_lot_ids=None):
    """All of ``forecast_input`` plus ``quantity``/``size_assumed`` from
    ``lots``, for the fixed-effects regression below.

    ``cutoff`` (G1 fix, Copilot review 2026-11-11, Finding 1): when
    given, rows with ``lot_date >= cutoff`` are dropped BEFORE any
    fitting -- lets ``fit_provider_effects`` be refit as-of a rolling
    origin instead of only ever on the full table (see that function's
    own docstring for why this matters).

    ``exclude_lot_ids`` (Copilot review 2026-11-11, Finding B): an
    additional set of lot_ids to drop once ``cutoff`` is given --
    ``forecast/eval.py``'s ``_origin_outlier_lot_ids`` passes the
    lot_ids that WOULD be ``OUTLIER``-flagged using only pre-``cutoff``
    data. ``forecast_input``'s own OUTLIER flag
    (``build_db._flag_price_outliers``) computes its median/MAD per
    (wine_ref_id, vintage) group over the ENTIRE history, not just
    pre-``cutoff`` data -- a sale AFTER ``cutoff`` can shift that
    group's median/MAD enough to change whether a PRE-``cutoff`` row is
    flagged, so ``cutoff`` alone (date-filtering only) does not fully
    close this leak.

    Also recomputes D15's "series active, last observation <= 36
    months old" recency check RELATIVE TO ``cutoff`` instead of "now"
    (``forecast_input``'s own check, in ``build_db.py``, is always
    now-relative) -- a series only looks active today because of a
    sale AFTER ``cutoff`` would otherwise still contribute its
    pre-``cutoff`` rows to this regression, even though no real
    point-in-time system could have known, as of ``cutoff``, that this
    series would ever sell again. Confirmed material on the live DB
    (see ``eval.py``'s own measurement): up to 10.7% of series at the
    earliest rolling origin only qualify this way. Computed from the
    group's RAW max pre-cutoff date (before ``exclude_lot_ids`` is
    applied) -- same ordering convention as ``eval.py``'s
    ``_is_active_as_of`` (code-review finding, 2026-11-12: the two are
    separate implementations over differently-shaped data, not one
    shared helper, so keep this ordering in sync by hand if either
    changes).

    Known residual gap (code-review finding, 2026-11-12, documented
    not fixed): this "RAW max date" is only raw relative to
    ``exclude_lot_ids`` -- ``df`` itself already came from
    ``forecast_input``'s OUTPUT, which has already dropped OUTLIER/
    QTY_SUSPECT/DUP_CANDIDATE rows at the SQL view level (unlike that
    view's own internal ``series_last_obs``, which does see them, D15's
    own comment). 1.05% of series have their forecast_input-visible
    last-sale understated for exactly this reason (live DB measurement,
    see ``eval.py``'s ``_is_active_as_of``) -- conservative direction,
    not fixed this round (would require bypassing ``forecast_input``
    for this check).

    Re-applies two already-established Gate-G0 conventions rather than
    inventing new ones: ``quantity IS NULL`` (QTY_ASSUMED, 63,170 live
    rows -- ``_fill_price_per_bottle`` assumes 1 internally but never
    writes it back to the column) -> 1, same default 0.5 itself uses;
    ``size_assumed IS NULL`` (``bottle_size_dl`` was never guessed --
    either defaulted (the overwhelmingly common case, 886,227 of
    969,183 live rows pre-finding-4) or set directly by a loader from a
    guessed large-format convention, see ``build_db._christies_format_dl``
    / ``_weinauktion_parse_qty_size``) -> 0, the tri-state column's
    implicit "not assumed" value.
    """
    rows = conn.execute("""
        SELECT fi.lot_id, fi.wine_ref_id, fi.vintage, fi.size_class,
               p.name, l.quantity, l.size_assumed, fi.price_per_bottle_eur,
               fi.lot_date
        FROM forecast_input fi
        JOIN lots l ON l.id = fi.lot_id
        JOIN providers p ON p.id = fi.provider_id
        """).fetchall()
    df = pd.DataFrame(rows, columns=[
        "lot_id", "wine_ref_id", "vintage", "size_class", "provider",
        "quantity", "size_assumed", "price", "lot_date"])
    df["group"] = (df["wine_ref_id"].astype(str) + "|"
                   + df["vintage"].astype(str) + "|"
                   + df["size_class"].astype(str))
    if cutoff is not None:
        df["lot_date"] = pd.to_datetime(df["lot_date"])
        cutoff_ts = pd.Timestamp(cutoff)
        df = df[df["lot_date"] < cutoff_ts]
        # Recency judged on the RAW pre-exclusion max date (own
        # docstring above, mirroring eval.py's _is_active_as_of): if a
        # group's only within-window row is also its only
        # exclude_lot_ids hit, excluding it FIRST would make the whole
        # group look stale and drop it entirely instead of just that
        # one row (code-review finding, 2026-11-12).
        max_date = df.groupby("group")["lot_date"].transform("max")
        df = df[max_date
               >= cutoff_ts - pd.DateOffset(months=RECENCY_MONTHS)]
        if exclude_lot_ids:
            df = df[~df["lot_id"].isin(exclude_lot_ids)]
    df["quantity"] = df["quantity"].fillna(1).astype(float)
    df["size_assumed"] = df["size_assumed"].fillna(0).astype(float)
    df["y"] = np.log(df["price"].astype(float))
    df["log_qty"] = np.log(df["quantity"])
    return df


def fit_provider_effects(conn, cutoff=None, exclude_lot_ids=None):
    """``y ~ wine_ref_id*vintage*size_class (absorbed) + provider +
    log(qty) + size_assumed``, by the within (demeaning) estimator.

    ``cutoff`` (G1 fix, Copilot review 2026-11-11, Finding 1): restrict
    to ``lot_date < cutoff`` before fitting. ``build_db.
    _persist_provider_effects`` (production/live-serving table) always
    calls this with ``cutoff=None`` -- using the best, most-current
    estimate is correct there, there is no held-out future to leak
    into. ``forecast/eval.py``'s rolling-origin harness is the caller
    that NEEDS ``cutoff=origin`` for every origin it scores: fitting
    once on the FULL table and baking that single offset into every
    row (the pre-fix behaviour) let each origin's training AND target
    rows be adjusted using provider offsets partly estimated from data
    that origin could not have seen yet -- a real G1 violation, and
    confirmed material on the live DB, not just a principle: refitting
    on data truncated to 12 months before ``as_of`` moved several
    providers' offsets by 3-25 percentage points (correlation with the
    full-data fit only 0.90) -- not a rounding error.

    ``exclude_lot_ids`` (Copilot review 2026-11-11, Finding B): forwarded
    to ``_load_fe_frame`` unchanged -- see its own docstring. Closes the
    remaining leak ``cutoff`` alone does not: ``forecast_input``'s
    OUTLIER flag and recency check are both computed relative to "now",
    not to ``cutoff``, so a sale AFTER ``cutoff`` can still change which
    PRE-``cutoff`` rows reach this regression even with ``cutoff`` set.

    FE group = the full series key (``wine_ref_id``, ``vintage``,
    ``size_class``), not just ``wine*vintage`` as the plan prose says --
    D10 already treats each size as its own series with no cross-size
    equivalence factor, so pooling sizes into one FE group would leave
    an unmodelled size effect sitting inside what is meant to be the
    "true wine value" term.

    The ~120k-group fixed effect is absorbed by demeaning (one-hot
    encoding it directly is infeasible: a dummy column per group).
    ``provider`` (only ~15 live values) gets an explicit dummy, one
    level dropped as the regression's reference; the fitted offsets are
    then RE-CENTERED to an observation-weighted mean of 0, so "offset"
    means "deviation from the overall weighted-average house effect",
    not "deviation from an arbitrary reference house" -- recentering is
    invariant to which reference pandas happened to drop, so that
    arbitrary choice does not leak into the result.

    Singleton groups (exactly 1 observation) are dropped before
    demeaning: they contribute an all-zero row (zero signal, zero
    residual by construction) that would silently shrink the reported
    residual variance without adding any information.

    Returns ``(offsets, variance_report)``: ``offsets`` is a DataFrame
    (``provider``, ``offset``, ``n_obs``); ``variance_report`` has
    ``var_within_before`` (Var(y) AFTER the group-demean, i.e. net of
    between-wine variance -- comparing against RAW Var(y) would be
    meaningless, since that is dominated by different wines simply
    costing different amounts) and ``var_residual_after`` (Var of the
    regression's own residuals) -- the AC's "Residual-Varianz sinkt"
    check is var_residual_after < var_within_before.

    Note: D1 already folds the buyer's premium into ``realised_price``,
    so these offsets are NOT expected to track premium-policy.md's
    rates -- they capture whatever residual house effect remains after
    that (clientele, condition grading, reputation, ...), a different
    thing than what the plan's own cross-check line describes.
    """
    df = _load_fe_frame(conn, cutoff=cutoff, exclude_lot_ids=exclude_lot_ids)
    sizes = df.groupby("group").size()
    df = df[df["group"].isin(sizes[sizes >= 2].index)].copy()
    empty_report = {"var_within_before": float("nan"),
                     "var_residual_after": float("nan")}
    if df.empty:
        return pd.DataFrame(columns=["provider", "offset", "n_obs"]), \
            empty_report

    dummies = pd.get_dummies(df["provider"], prefix="provider",
                              drop_first=True, dtype=float)
    x = pd.concat([dummies, df[["log_qty", "size_assumed"]]], axis=1)
    y = df["y"]

    group = df["group"]
    y_within = y - y.groupby(group).transform("mean")
    x_within = x - x.groupby(group).transform("mean")
    var_within_before = float(y_within.var(ddof=0))

    model = sm.OLS(y_within.to_numpy(), x_within.to_numpy()).fit()
    var_residual_after = float(np.var(model.resid, ddof=0))

    provider_names = sorted(df["provider"].unique())
    dummy_providers = {col.removeprefix("provider_") for col in dummies.columns}
    reference = next(p for p in provider_names if p not in dummy_providers)
    raw_offset = {reference: 0.0}
    n_dummies = len(dummies.columns)
    for col, coef in zip(dummies.columns, model.params[:n_dummies]):
        raw_offset[col.removeprefix("provider_")] = float(coef)

    counts = df["provider"].value_counts()
    total_n = int(counts.sum())
    weighted_mean = sum(raw_offset[p] * counts[p]
                        for p in provider_names) / total_n
    offsets = pd.DataFrame({
        "provider": provider_names,
        "offset": [raw_offset[p] - weighted_mean for p in provider_names],
        "n_obs": [int(counts[p]) for p in provider_names],
    })
    return offsets, {
        "var_within_before": var_within_before,
        "var_residual_after": var_residual_after,
    }


# --------------------------------------------------------------------------- #
# 1.4 -- Baselines
# --------------------------------------------------------------------------- #

# Baseline (b)'s window size -- the plan names the method ("Median der
# letzten k Lose") but not k. Set here as a reasonable default, not a
# D-decision; open to tuning once 2.1's backtest exists.
K_MEDIAN = 5


def _last_value(sub, _target_date):
    """(a) Last-Value."""
    if sub.empty:
        return None
    return float(sub["y"].iloc[-1])


def _median_last_k(sub, _target_date, k=K_MEDIAN):
    """(b) Median der letzten k Lose."""
    if sub.empty:
        return None
    return float(sub["y"].iloc[-k:].median())


def _rolling_median_12m(sub, _target_date, months=12):
    """(c) Gleitender Median 12 M -- the window is relative to ``sub``'s
    OWN last observed date (ignores ``target_date``, same as (a)/(b)):
    "the last 12 months of data we actually have", used as the point
    forecast regardless of horizon. Anchoring on ``target_date`` instead
    (tried first, caught empirically by this baseline's own
    constant-series test) is structurally broken for the 12m horizon --
    ``target_date = origin + 12M`` makes the window's cutoff land AT
    ``origin`` itself, i.e. a window that starts exactly where ``sub``
    (all dates strictly before ``origin``) already ends: always empty,
    never a real rolling window. An empty window (sub's own span is
    itself shorter than 12 months) returns ``None`` rather than
    silently falling back to all of ``sub`` -- that would make this
    indistinguishable from a plain median."""
    if sub.empty:
        return None
    cutoff = sub["date"].max() - pd.DateOffset(months=months)
    window = sub[sub["date"] >= cutoff]
    if window.empty:
        return None
    return float(window["y"].median())


def _trend(sub, target_date):
    """(d) Saisonfreie lineare Trend-Regression im Log -- OLS on
    (days-since-first-obs / 365.25, y), extrapolated to ``target_date``.
    Needs >= 2 rows AND at least two distinct dates (a degenerate,
    zero-spread ``x`` has no slope to fit)."""
    if len(sub) < 2:
        return None
    t0 = sub["date"].min()
    x = (sub["date"] - t0).dt.days.to_numpy(dtype=float) / 365.25
    if np.ptp(x) <= 0:
        return None
    y = sub["y"].to_numpy(dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    x_target = (pd.Timestamp(target_date) - t0).days / 365.25
    return float(intercept + slope * x_target)


def _retrospective_residuals(train, point_fn, horizon):
    """Nested backtest WITHIN ``train`` alone (so still G1-clean
    -- every mini-origin below only ever looks at data already inside
    ``train``, which the real caller already restricted to ``< origin``).

    At step ``i``, ``sub = train.iloc[:i]`` simulates a mini rolling-
    origin at ``dates.iloc[i]``. The "next"-horizon residual pairs its
    point forecast against the very next real row; the "12m"-horizon
    residual instead pairs it against the first row >= 12 calendar
    months later. The 12m set is therefore naturally wider-spread than
    the next set (more time for the point estimate to go stale) --
    that is the whole mechanism by which the derived interval WIDTH
    grows with horizon (G4), with no artificial inflation factor
    bolted on afterwards.

    Capped to the last ``MAX_BACKTEST_STEPS`` ELIGIBLE mini-origins --
    measured on the live DB: a handful of series run to ~2000 training
    rows, and an uncapped backtest is O(n) ``point_fn`` calls (the
    "trend" baseline refits an OLS over up to ``n`` points EVERY step)
    times O(n) again for 12m's own future-row lookup, i.e. O(n^2) for
    those few outliers -- the real run was killed after 20+ minutes
    with no end in sight. Capping to the most recent steps only
    changes anything for that long tail (most series have far fewer
    than ``MAX_BACKTEST_STEPS`` rows to begin with, so this is a no-op
    for them).

    "Eligible" matters for the 12m horizon specifically: a mini-origin
    in the most recent 12 months of ``train`` has no row 12 months
    later to compare against AT ALL (that would be real look-ahead --
    G1). Capping to the last N raw row-indices (tried first) silently
    picked exactly those ineligible trailing rows for any series whose
    final ``MAX_BACKTEST_STEPS`` rows fall within its own last 12
    months -- which is the common case, since that is BY DEFINITION
    where 12m backtesting runs out of room -- and came back with ZERO
    residuals instead of the intended ~50. Finding the eligibility
    boundary first (via a sorted-array search, O(log n) scalar
    comparisons, not O(n) point_fn calls) and capping from there fixes
    this without reintroducing the O(n) cost this was meant to avoid."""
    dates = train["date"].reset_index(drop=True)
    y = train["y"].reset_index(drop=True)
    n = len(train)
    if horizon == HORIZON_NEXT:
        hi = n - 1
    elif horizon == HORIZON_12M:
        cutoff = dates.iloc[-1] - pd.DateOffset(months=12)
        hi = int(dates.searchsorted(cutoff, side="right")) - 1
    else:
        raise ValueError(f"unknown horizon {horizon!r}")
    if hi < 1:
        return []
    lo = max(1, hi - MAX_BACKTEST_STEPS + 1)
    residuals = []
    for i in range(lo, hi + 1):
        sub = train.iloc[:i]
        if horizon == HORIZON_NEXT:
            pred = point_fn(sub, dates.iloc[i])
            if pred is not None:
                residuals.append(float(y.iloc[i]) - pred)
        else:
            min_target = dates.iloc[i] + pd.DateOffset(months=12)
            future = train[train["date"] >= min_target]
            if future.empty:
                continue  # guaranteed not to happen given `hi`, kept defensively
            pred = point_fn(sub, future["date"].iloc[0])
            if pred is not None:
                residuals.append(float(future["y"].iloc[0]) - pred)
    return residuals


def _quantiles_from_residuals(point, residuals):
    # Bias-corrected by construction: q0.5 = point + median(residuals),
    # not just ``point`` itself -- 1.4's AC ("Quantile via empirische
    # Residuen") means every quantile, the median included, goes
    # through the same residual-shift, so a systematically biased
    # point_fn gets corrected rather than special-cased away.
    return {q: point + float(np.quantile(residuals, q))
            for q in QUANTILE_LEVELS}


def make_baseline(point_fn):
    """Wraps a ``point_fn(sub, target_date) -> float | None`` into the
    ``eval.Forecaster`` signature (``forecaster(train, origin, horizon)
    -> dict | None``): anchors the point estimate at the real forecast
    target (``origin`` for "next", ``origin + 12M`` for "12m" -- the
    only honest anchor available without peeking at the actual future
    row), derives the quantile spread from
    ``_retrospective_residuals``, and returns ``None``
    (INSUFFICIENT_DATA, G3) whenever there's no point estimate or
    fewer than 2 residuals.

    Confirmed real bug (senior-review self-check, caught before any
    commit): an EARLIER version required only >= 1 residual. With
    exactly 1, ``np.quantile([r], q)`` returns ``r`` for every ``q`` --
    all seven quantiles identical, a confident-looking zero-width
    interval built from a single data point. That is precisely the
    "false certainty" ``MIN_OBS``'s own docstring warns about; it leaked
    through because this function's own floor was 1, not 2. Live-report
    evidence: the ``n_train=1-2`` bucket's "next" horizon showed
    ``Breite 50/80/95% = 0.000`` for every baseline before this fix."""
    def forecaster(train, origin, horizon):
        if len(train) < MIN_OBS:
            return None
        target_date = (origin if horizon == HORIZON_NEXT
                       else origin + pd.DateOffset(months=12))
        point = point_fn(train, target_date)
        if point is None:
            return None
        residuals = _retrospective_residuals(train, point_fn, horizon)
        if len(residuals) < 2:
            return None
        return _quantiles_from_residuals(point, residuals)
    return forecaster


BASELINES = {
    "last_value": make_baseline(_last_value),
    "median_last_5": make_baseline(_median_last_k),
    "rolling_median_12m": make_baseline(_rolling_median_12m),
    "trend": make_baseline(_trend),
}


# --------------------------------------------------------------------------- #
# 2.1-2.6 -- Local-Level/Local-Linear-Trend-Modell (Kalman)
# --------------------------------------------------------------------------- #

# Technical floor only (>= 2 non-NaN monthly points, or nothing at all is
# estimable) -- NOT D5's own >= 10 obs/>= 3 years/>= 5 auctions threshold,
# which is what 2.1's backtest MEASURES against this model's output, not
# something this function enforces itself (same separation of concerns
# MIN_OBS already keeps for the baselines above).
LOCAL_LEVEL_MIN_MONTHS = 2

# 2.3: "Untergrenzen für sigma^2 (gegen Degeneration auf 0 =
# Scheingenauigkeit)" -- ABSOLUTE floors, not relative to each series'
# own var(y): both sigma^2 live in LOG-y space already, which is itself
# scale-invariant (a log-price difference is already a relative/percent
# move), so a Pétrus series and a EUR10 wine series genuinely need the
# SAME floor here -- an earlier version used a per-series-relative floor
# on the theory that they wouldn't, which was wrong for that reason, not
# just in the number it produced (real-DB finding below).
#
# sigma2.irregular (observation/auction noise): confirmed empirically on
# the live DB, NOT guessed -- fit_provider_effects' own
# var_residual_after (~0.206, the within-series log-price variance
# AFTER house effects are removed, i.e. exactly the residual auction
# noise this parameter means to capture) gives the scale; 5% of that
# (~0.01, SD ~10%) is the floor. A fitted value near 0 would claim
# auction prices are measured to within a fraction of a percent, which
# is not plausible for this data.
_SIGMA2_IRREGULAR_FLOOR = 0.01
# sigma2.level (level drift): stays small -- a genuinely flat-priced
# wine legitimately has near-zero drift; G4's "Intervallbreite wächst
# mit Horizont" only needs a NONZERO floor to keep contributing growth
# with h, not a large one.
_SIGMA2_LEVEL_FLOOR = 1e-6

# Confirmed empirically on a 400-series live-DB sample (senior review,
# advisor consult): the FIRST version of this model treated a floored
# sigma^2 as FIT_FAILED (per the original 2.3 reading: "Untergrenzen...
# gegen Scheingenauigkeit" sounded like a rejection rule). That rejected
# ~50% of every fit actually attempted -- not a bug in the floor's
# VALUE, but a structural consequence of _monthly_series producing one
# observation per month: with a single point per period, sigma2.irregular
# (noise around the level) and sigma2.level (drift of the level) are
# weakly identified, and MLE routinely drives one of them to the
# boundary. That is a usable, if conservatively uncertain, fit -- not a
# broken one. "Untergrenzen" means CLAMP (use the floor value and keep
# going), not reject; FIT_FAILED is reserved for an actually broken fit
# (non-convergence, an exception, or a non-finite forecast).
_SIGMA2_FLOORS = {
    "sigma2.irregular": _SIGMA2_IRREGULAR_FLOOR,
    "sigma2.level": _SIGMA2_LEVEL_FLOOR,
}

# Update 2026-11-13 (User-Entscheid nach Copilot-Review-Nachbesserung,
# §8-Eintrag "2.1/2.6 Pro-Monat-Gewichtung"): die additive
# ``_within_month_lot_variance``-Korrektur oben (Copilot-Review
# 2026-11-11, Finding 2) behob die zu enge "next"-Coverage, überkorrigierte
# aber auf 84,5-89,4% in JEDER Dichteklasse (durchgängig über dem
# [77,83]-Zielband -- live gemessen, nicht geraten). Ursache: additiv
# aufgeschlagene Varianz zählt den Teil des Lot-Rauschens, den
# ``sigma2.irregular`` bei vielen Serien (Median-Seriengrösse = 2
# Beobachtungen, die meisten Kalendermonate also ohnehin nur 1 Los) schon
# selbst mitträgt, streckenweise doppelt. Ersetzt durch die statistisch
# exakte Variante (2.2's eigene "Option A mit Gewicht"-Alternative, für
# v1 bewusst zurückgestellt): ``sigma2.irregular`` wird PRO MONAT durch
# die Los-Anzahl ``k_t`` dieses Monats gewichtet (Varianz des Mittels aus
# ``k`` i.i.d. Losen ist ``sigma2.irregular / k`` -- keine Näherung,
# sondern exakt), nicht mehr nachträglich addiert. Dafür reicht
# ``UnobservedComponents`` nicht mehr aus (kein Hook für pro-Periode
# ``obs_cov``) -- ``_LocalLevelTrend`` ist ein eigenes, kleines
# ``MLEModel``.


DAMPING_MAX = 0.98


class _LocalLevelTrend(sm.tsa.statespace.MLEModel):
    """Level (+ optionale gedämpfte Steigung) mit PRO-MONAT-
    Beobachtungsvarianz ``sigma2.irregular / k_t`` (``k_t`` = Los-Anzahl
    in diesem Monat) statt des unten stehenden Kommentars' additiver
    Korrektur -- siehe diesen für die Begründung und Live-Messung.

    Gegen synthetische Daten mit bekannten Parametern validiert, bevor
    hier verwendet (Wiedergewinnung von sigma2.irregular/sigma2.level
    innerhalb derselben ±30%-Toleranz wie 2.2's eigener
    ``UnobservedComponents``-Test; NaN-Lücken-Handling; gedämpfte
    Trend-Prognose-Zuwächse schrumpfen statt zu explodieren über einen
    12-Monats-Horizont) -- Prototyp-Skript im 2.1/2.6-Review-Log-Eintrag
    referenziert.

    ``trend=True`` fügt einen zweiten Zustand (Steigung) hinzu,
    Übergang ``slope_t = damping * slope_{t-1} + eta_slope`` --
    ``damping`` wird über einen skalierten Sigmoid auf ``(0,
    DAMPING_MAX)`` abgebildet, nie den unbeschränkten Random-Walk, den
    ein ungedämpfter lokaler LINEARER Trend erlauben würde (2.6's eigene
    Pflicht-Dämpfung: eine ungedämpfte, 12 Monate extrapolierte Steigung
    kann Fantasiepreise liefern)."""

    def __init__(self, endog, weights, trend=False):
        self.trend = trend
        k_states = 2 if trend else 1
        super().__init__(endog, k_states=k_states, k_posdef=k_states,
                         initialization="approximate_diffuse")
        w = np.asarray(weights, dtype=float).copy()
        # Platzhalter für NaN-Monate (dort wird obs_cov vom Kalman-Filter
        # ohnehin nie gelesen -- die Beobachtung fehlt) und für die
        # Out-of-Sample-Erweiterung in clone() (dito, keine echte
        # Beobachtung dort).
        w[~np.isfinite(w) | (w <= 0)] = 1.0
        self._weights = w
        self["design"] = (np.array([[1.0, 0.0]]) if trend
                          else np.array([[1.0]]))
        self["transition"] = (np.array([[1.0, 1.0], [0.0, 1.0]]) if trend
                              else np.array([[1.0]]))
        self["selection"] = np.eye(k_states)
        self["obs_cov"] = np.zeros((1, 1, self.nobs))

    @property
    def param_names(self):
        """statsmodels' own hook: parameter names, in fit order."""
        names = ["sigma2.irregular", "sigma2.level"]
        if self.trend:
            names += ["sigma2.slope", "damping"]
        return names

    @property
    def start_params(self):
        """MLE starting point. statsmodels treats this as CONSTRAINED
        (``fit`` calls ``untransform_params(start_params)`` internally,
        confirmed against ``MLEModel.fit``'s own source, not assumed --
        an earlier version of this passed ``1.5`` meaning "the
        UNCONSTRAINED pre-sigmoid value", which statsmodels instead read
        as a constrained damping of 1.5 > ``DAMPING_MAX``, silently
        clipped to the cap, starting the optimizer already AT the
        boundary): variances at the series' own scale, damping (when
        ``trend``) at a middling, non-degenerate 0.80.

        ``resid_var`` falls back to ``1.0`` for zero OR non-finite
        variance -- not just ``... or 1.0`` (code-review finding,
        2026-11-13: ``nan`` is truthy in Python, so ``nan or 1.0``
        silently evaluates to ``nan``, not the intended fallback). The
        production path (``_llt_forecast``'s ``monthly.notna().sum() <
        LOCAL_LEVEL_MIN_MONTHS`` guard) never reaches this with an
        all-NaN ``endog``, but this class is also instantiated
        directly (tests already do), where nothing else enforces
        that."""
        resid_var = float(np.nanvar(self.endog))
        if not np.isfinite(resid_var) or resid_var == 0:
            resid_var = 1.0
        params = [resid_var, resid_var * 0.01]
        if self.trend:
            params += [resid_var * 0.001, 0.80]
        return np.array(params)

    def transform_params(self, unconstrained):
        """Unconstrained optimizer space -> constrained model space:
        variances via squaring (always >= 0), damping via a scaled
        sigmoid into the OPEN interval ``(0, DAMPING_MAX)`` -- see the
        class docstring for why ``DAMPING_MAX < 1`` is load-bearing,
        not cosmetic."""
        constrained = unconstrained.copy()
        constrained[0] = unconstrained[0] ** 2
        constrained[1] = unconstrained[1] ** 2
        if self.trend:
            constrained[2] = unconstrained[2] ** 2
            constrained[3] = DAMPING_MAX / (1 + np.exp(-unconstrained[3]))
        return constrained

    def untransform_params(self, constrained):
        """Inverse of ``transform_params`` (statsmodels needs both
        directions: e.g. to re-enter the optimizer from a given
        constrained start)."""
        unconstrained = constrained.copy()
        unconstrained[0] = constrained[0] ** 0.5
        unconstrained[1] = constrained[1] ** 0.5
        if self.trend:
            unconstrained[2] = constrained[2] ** 0.5
            ratio = np.clip(constrained[3] / DAMPING_MAX, 1e-6, 1 - 1e-6)
            unconstrained[3] = np.log(ratio / (1 - ratio))
        return unconstrained

    def clone(self, endog, exog=None, **kwargs):  # pylint: disable=unused-argument
        """statsmodels' required hook for out-of-sample extension
        (``get_forecast`` calls this with ``endog`` = dummy zeros for
        JUST the new periods, to read off design/transition/selection
        there). ``exog`` is unused -- this model has none, the
        parameter only exists to match statsmodels' call signature.

        The ``weights=1`` default is NOT a safe placeholder that
        happens not to matter (code-review finding, 2026-11-13,
        confirmed empirically -- ``obs_cov`` for the extension IS read
        by ``get_forecast``/``get_prediction`` and changes
        ``var_pred_mean``: patching this to ``weights=3`` instead
        measurably shrank a test forecast's variance). ``1`` is the
        deliberately correct value, not an arbitrary default:
        ``evaluate_series`` scores one INDIVIDUAL future lot per
        target row, never a monthly mean, so the forecast variance
        must be ``sigma2.irregular / 1`` regardless of how many lots
        the real future month turns out to hold -- exactly the
        per-lot noise the 2026-11-13 per-month-weighting fix (this
        class's own docstring) exists to get right. A future change
        that estimates a "more realistic" future ``k_t > 1`` here
        (e.g. from recent average lot counts) would silently shrink
        the forecast back toward per-monthly-mean variance and
        reintroduce the under-coverage bug that fix was written to
        eliminate -- do not "improve" this without re-reading that
        docstring first."""
        weights = kwargs.pop("weights", np.ones(len(endog)))
        return self.__class__(endog, weights, trend=self.trend)

    def update(self, params, **kwargs):
        """statsmodels' own hook: push fitted/candidate ``params`` into
        the state-space matrices -- here, the per-month-weighted
        ``obs_cov`` and (when ``trend``) the damped slope's own
        transition/variance."""
        params = super().update(params, **kwargs)
        self["obs_cov", 0, 0, :] = params[0] / self._weights
        self["state_cov", 0, 0] = params[1]
        if self.trend:
            self["transition", 1, 1] = params[3]
            self["state_cov", 1, 1] = params[2]


def _monthly_series(train):
    """Aggregate ``train`` to a calendar-month grid (2.2 Option A, the
    plan's own recommendation): unweighted mean log-price per month,
    NaN for months with zero lots. statsmodels' Kalman filter treats a
    NaN ``endog`` entry as "skip this measurement update" -- exactly
    2.2's "Lücken korrekt behandeln, Varianz wächst" requirement, with
    no extra code needed. The per-month LOT COUNT (2.2's "Gewicht nach
    Anzahl" alternative) is a separate, aligned array -- see
    ``_monthly_weights``, consumed by ``_LocalLevelTrend`` as a
    per-period observation-variance weight, not folded into this mean
    itself."""
    return train.set_index("date")["y"].resample("MS").mean()


def _monthly_weights(train):
    """Lot count per calendar month, aligned to ``_monthly_series``'s
    own index -- the ``k_t`` weight ``_LocalLevelTrend`` divides
    ``sigma2.irregular`` by (variance of a mean of ``k`` i.i.d. lots is
    ``sigma2.irregular / k``). Zero-lot months (NaN in
    ``_monthly_series``) get a placeholder of 1 -- irrelevant, the
    Kalman filter never reads ``obs_cov`` for a missing observation."""
    counts = train.set_index("date")["y"].resample("MS").count()
    return counts.replace(0, 1).to_numpy(dtype=float)


def _months_between(start, end):
    start = pd.Timestamp(start)
    end = pd.Timestamp(end)
    return (end.year - start.year) * 12 + (end.month - start.month)


# 2.6 (live-DB diagnostic, 2026-11-13, confirmed not guessed): the
# trend variant's FIT_FAILED rate stayed at ~13-14% even at n_train>=10
# -- NOT a model mis-specification. Every one of 145 sampled
# non-converged fits hit statsmodels' own ``fit()`` default
# ``maxiter=50`` EXACTLY (``mle_retvals["iterations"] == 50`` every
# time), with ``damping`` crawling toward the open boundary 0 (true
# optimum: "no real trend", legitimate, see ``DAMPING_MAX``'s own
# docstring for why the interval is open -- an optimizer can never
# fully REACH an open boundary, so it keeps inching closer instead of
# satisfying the convergence tolerance). Re-fitting the same failing
# cases with more headroom converged every one of them within 50-54
# iterations (19/19 on a targeted re-test, up from 14/19 at the
# default cap) -- a convergence-REPORTING problem, not a real failure,
# same shape as 2.3's own "Untergrenzen... CLAMP, not reject" finding,
# just for ``damping`` instead of a ``sigma2``. ``local_level`` itself
# never needed this (97.5%+ convergence at the default already -- 2
# params converge fast) but raising the cap is harmless there too.
_FIT_MAXITER = 200


def _fit_local_level_trend(monthly, weights, trend):
    """Shared fit/convergence/floor-clamp path for
    ``local_level_forecast``/``local_linear_trend_forecast``. Returns
    ``"FIT_FAILED"`` (non-convergence, an exception, or a non-finite
    parameter -- an actually broken fit, see ``_SIGMA2_FLOORS``'s own
    docstring for why a floored sigma^2 is NOT this) or ``(res,
    clamped)``: ``clamped`` only ever has the two ``_SIGMA2_FLOORS``
    keys -- ``sigma2.slope``/``damping`` (when ``trend``) are bounded
    by construction via ``transform_params`` (see ``_LocalLevelTrend``'s
    own docstring), so they need no floor, only a finiteness check."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mod = _LocalLevelTrend(monthly, weights, trend=trend)
            res = mod.fit(disp=False, maxiter=_FIT_MAXITER)
    except Exception:
        return "FIT_FAILED"
    if not res.mle_retvals.get("converged", False):
        return "FIT_FAILED"
    params = res.params.copy()
    clamped = {}
    for name, floor in _SIGMA2_FLOORS.items():
        value = params.get(name)
        if value is None or not np.isfinite(value):
            return "FIT_FAILED"
        clamped[name] = value < floor
        if clamped[name]:
            params[name] = floor
    if trend:
        for name in ("sigma2.slope", "damping"):
            value = params.get(name)
            if value is None or not np.isfinite(value):
                return "FIT_FAILED"
    if any(clamped.values()):
        res = mod.smooth(params.to_numpy())
    return res, clamped


def _llt_forecast(train, origin, horizon, trend):
    """Shared body of ``local_level_forecast``/
    ``local_linear_trend_forecast`` -- see those for the public
    contract (return shape, ``FIT_FAILED``/``None`` semantics)."""
    monthly = _monthly_series(train)
    if monthly.notna().sum() < LOCAL_LEVEL_MIN_MONTHS:
        return None
    target_date = (origin if horizon == HORIZON_NEXT
                   else origin + pd.DateOffset(months=12))
    h = _months_between(monthly.index[-1], target_date)
    if h < 1:
        return None
    fit = _fit_local_level_trend(monthly, _monthly_weights(train), trend)
    if fit == "FIT_FAILED":
        return "FIT_FAILED"
    res, clamped = fit
    fc = res.get_forecast(h)
    mean = float(fc.predicted_mean.iloc[-1])
    var = float(fc.var_pred_mean.iloc[-1])
    if not np.isfinite(mean) or not np.isfinite(var) or var <= 0:
        return "FIT_FAILED"
    quantiles = {q: mean + norm.ppf(q) * var ** 0.5 for q in QUANTILE_LEVELS}
    return quantiles, clamped


def local_level_forecast(train, origin, horizon):
    """2.1-2.4: level-only ``_LocalLevelTrend`` (``trend=False``) on the
    monthly grid from ``_monthly_series``/``_monthly_weights``, forecast
    ``h`` months ahead to the real target (``origin`` for "next",
    ``origin + 12M`` for "12m" -- ``h >= 1`` always, since ``train`` is
    strictly ``< origin`` and every origin is itself a calendar-month
    start).

    Returns ``None`` (too few months, or ``h < 1``), the string
    ``"FIT_FAILED"``, or ``(quantiles, clamped)``: ``quantiles`` is the
    ``eval.Forecaster``-standard dict (one value per ``QUANTILE_LEVELS``,
    Gaussian in log-y space: ``mean + norm.ppf(q) * sd``, monotone in
    ``q`` by construction); ``clamped`` is ``{"sigma2.irregular": bool,
    "sigma2.level": bool}``, for the wrapper's own per-parameter clamp
    counters (``make_local_level_forecaster``) -- 2.3's AC is a rate, so
    both how often FIT_FAILED fires and how often each floor had to bind
    are tracked, not just a single pass/fail flag.

    2.4's own test requirement -- "Prädiktions- nicht Konfidenz-
    intervall (Messrauschen einrechnen!)" -- is satisfied by
    ``_LocalLevelTrend`` itself now, no manual addition needed: its
    per-month ``obs_cov = sigma2.irregular / k_t`` already makes
    ``res.get_forecast(h).var_pred_mean`` the prediction variance for an
    INDIVIDUAL lot in the target month (not a monthly mean's), since the
    model never sees an unweighted monthly mean in the first place --
    see the module comment above this class for why the earlier,
    additive correction (Copilot review 2026-11-11, Finding 2)
    overcorrected coverage and was replaced."""
    return _llt_forecast(train, origin, horizon, trend=False)


def local_linear_trend_forecast(train, origin, horizon):
    """2.6: as ``local_level_forecast``, but with a damped slope state
    (``_LocalLevelTrend(trend=True)``) -- see that class's own
    docstring for why the damping is mandatory and bounded by
    construction. Only adopted as the production model if it beats
    ``local_level`` on Gate G2's own criteria once both are compared
    (plan's own "nur übernehmen, wenn nach G2 besser")."""
    return _llt_forecast(train, origin, horizon, trend=True)


def _make_llt_forecaster(forecast_fn):
    """Shared ``Forecaster``-contract wrapper for
    ``make_local_level_forecaster``/``make_local_linear_trend_forecaster``
    -- counts on the returned closure's own ``.counters`` instead of
    threading a second return channel through ``eval.py``:

    - ``n_calls``: every invocation.
    - ``n_insufficient_months``: too few monthly points to fit at all
      (the wrapped function returned ``None``) -- NOT a 2.3 concern (no
      fit was ever attempted), but needed as the denominator for the
      other two rates (``n_calls - n_insufficient_months`` = fits
      actually attempted).
    - ``n_fit_failed``: an actually broken fit (2.3's own AC is this
      rate, ">5% of attempted fits ⇒ Review" -- compute it against
      ``n_calls - n_insufficient_months``, not ``n_calls``).
    - ``n_sigma2_irregular_clamped`` / ``n_sigma2_level_clamped``: a
      successful fit where that one variance floor had to bind (see
      ``_SIGMA2_FLOORS``) -- informational, not itself a failure."""
    counters = {
        "n_calls": 0, "n_insufficient_months": 0, "n_fit_failed": 0,
        "n_sigma2_irregular_clamped": 0, "n_sigma2_level_clamped": 0,
    }

    def forecaster(train, origin, horizon):
        counters["n_calls"] += 1
        result = forecast_fn(train, origin, horizon)
        if result is None:
            counters["n_insufficient_months"] += 1
            return None
        if result == "FIT_FAILED":
            counters["n_fit_failed"] += 1
            return None
        quantiles, clamped = result
        if clamped["sigma2.irregular"]:
            counters["n_sigma2_irregular_clamped"] += 1
        if clamped["sigma2.level"]:
            counters["n_sigma2_level_clamped"] += 1
        return quantiles

    forecaster.counters = counters
    return forecaster


def make_local_level_forecaster():
    """Wraps ``local_level_forecast`` into the plain ``Forecaster``
    contract -- see ``_make_llt_forecaster`` for the counters this
    exposes."""
    return _make_llt_forecaster(local_level_forecast)


def make_local_linear_trend_forecaster():
    """2.6: wraps ``local_linear_trend_forecast`` into the plain
    ``Forecaster`` contract -- see ``_make_llt_forecaster`` for the
    counters this exposes."""
    return _make_llt_forecaster(local_linear_trend_forecast)
