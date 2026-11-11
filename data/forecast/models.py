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

def _load_fe_frame(conn, cutoff=None):
    """All of ``forecast_input`` plus ``quantity``/``size_assumed`` from
    ``lots``, for the fixed-effects regression below.

    ``cutoff`` (G1 fix, Copilot review 2026-11-11, Finding 1): when
    given, rows with ``lot_date >= cutoff`` are dropped BEFORE any
    fitting -- lets ``fit_provider_effects`` be refit as-of a rolling
    origin instead of only ever on the full table (see that function's
    own docstring for why this matters).

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
        SELECT fi.wine_ref_id, fi.vintage, fi.size_class, p.name,
               l.quantity, l.size_assumed, fi.price_per_bottle_eur,
               fi.lot_date
        FROM forecast_input fi
        JOIN lots l ON l.id = fi.lot_id
        JOIN providers p ON p.id = fi.provider_id
        """).fetchall()
    df = pd.DataFrame(rows, columns=[
        "wine_ref_id", "vintage", "size_class", "provider",
        "quantity", "size_assumed", "price", "lot_date"])
    if cutoff is not None:
        df["lot_date"] = pd.to_datetime(df["lot_date"])
        df = df[df["lot_date"] < pd.Timestamp(cutoff)]
    df["quantity"] = df["quantity"].fillna(1).astype(float)
    df["size_assumed"] = df["size_assumed"].fillna(0).astype(float)
    df["y"] = np.log(df["price"].astype(float))
    df["log_qty"] = np.log(df["quantity"])
    df["group"] = (df["wine_ref_id"].astype(str) + "|"
                   + df["vintage"].astype(str) + "|"
                   + df["size_class"].astype(str))
    return df


def fit_provider_effects(conn, cutoff=None):
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
    df = _load_fe_frame(conn, cutoff=cutoff)
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
# 2.2-2.4 -- Local-Level-Modell (Kalman)
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

# Copilot review finding (2026-11-11, Finding 2, confirmed empirically
# on the live DB, not assumed): _monthly_series averages every lot in
# a calendar month to one point before the Kalman model ever sees it,
# so sigma2.irregular (and therefore get_forecast's var_pred_mean) only
# captures the MONTHLY MEAN's own noise -- not an individual lot's.
# evaluate_series scores individual lots, not monthly means, so this
# silently makes every prediction interval too narrow whenever a
# month actually held more than one lot. Measured: 52% of all
# forecast_input rows fall in a (series, month) cell with >= 2 lots;
# the pooled within-month variance of those cells is ~0.091 -- ~9x the
# sigma2.irregular floor above and a sizeable fraction of the typical
# ~0.206 total residual variance (fit_provider_effects' own
# var_residual_after). This plausibly explains the "next"-horizon
# coverage shortfall already on record (74.0% vs the [77, 83] target)
# that the first version of this model's own review had deferred to
# Stufe 4 as an unexplained calibration gap -- it is instead a missing
# variance term in 2.4 itself.
_WITHIN_MONTH_LOT_VARIANCE_FALLBACK = 0.09
# A series' OWN within-month scatter is preferred when there's enough
# of it to trust (most series can't: median series size is 2 total
# observations, so most calendar months hold exactly one lot and this
# never triggers) -- same "own evidence over a global prior, only once
# there's enough of it" shape as LOCAL_LEVEL_MIN_MONTHS/MIN_OBS above.
_WITHIN_MONTH_MIN_CELLS = 3


def _within_month_lot_variance(train):
    """Pooled variance of ``y`` around each calendar month's own mean,
    over months in ``train`` with >= 2 lots -- the within-month scatter
    ``_monthly_series`` discards. Returns ``(variance, used_fallback)``;
    falls back to ``_WITHIN_MONTH_LOT_VARIANCE_FALLBACK`` (an absolute,
    empirically-derived constant, same convention as ``_SIGMA2_FLOORS``)
    when ``train`` has fewer than ``_WITHIN_MONTH_MIN_CELLS`` such
    months to estimate this from reliably."""
    groups = train.groupby(train["date"].dt.to_period("M"))["y"]
    cells = [g for _, g in groups if len(g) >= 2]
    if len(cells) < _WITHIN_MONTH_MIN_CELLS:
        return _WITHIN_MONTH_LOT_VARIANCE_FALLBACK, True
    total_obs = sum(len(g) for g in cells)
    pooled = sum(float(g.var(ddof=0)) * len(g) for g in cells) / total_obs
    return pooled, False


def _monthly_series(train):
    """Aggregate ``train`` to a calendar-month grid (2.2 Option A, the
    plan's own recommendation): unweighted mean log-price per month,
    NaN for months with zero lots. statsmodels' Kalman filter treats a
    NaN ``endog`` entry as "skip this measurement update" -- exactly
    2.2's "Lücken korrekt behandeln, Varianz wächst" requirement, with
    no extra code needed. Same-month weighting by lot count (the
    alternative 2.2 also names) is deliberately NOT done for v1 -- see
    ``local_level_forecast``'s own docstring."""
    return train.set_index("date")["y"].resample("MS").mean()


def _months_between(start, end):
    start = pd.Timestamp(start)
    end = pd.Timestamp(end)
    return (end.year - start.year) * 12 + (end.month - start.month)


def local_level_forecast(train, origin, horizon):
    """2.2-2.4: ``UnobservedComponents(endog, level="local level")`` on
    the monthly grid from ``_monthly_series``, forecast ``h`` months
    ahead to the real target (``origin`` for "next", ``origin + 12M``
    for "12m" -- ``h >= 1`` always, since ``train`` is strictly
    ``< origin`` and every origin is itself a calendar-month start).

    Returns ``None`` (too few months, or ``h < 1``), the string
    ``"FIT_FAILED"`` (non-convergence, an exception, or a non-finite
    forecast -- an actually broken fit, see ``_SIGMA2_FLOORS``'s own
    docstring for why a floored sigma^2 is NOT this), or
    ``(quantiles, clamped)``: ``quantiles`` is the ``eval.Forecaster``-
    standard dict (one value per ``QUANTILE_LEVELS``, Gaussian in
    log-y space: ``mean + norm.ppf(q) * sd``, monotone in ``q`` by
    construction); ``clamped`` is ``{"sigma2.irregular": bool,
    "sigma2.level": bool}``, for the wrapper's own per-parameter clamp
    counters (``make_local_level_forecaster``) -- 2.3's AC is a rate,
    so both how often FIT_FAILED fires and how often each floor had to
    bind are tracked, not just a single pass/fail flag.

    2.4's own test requirement -- "Prädiktions- nicht Konfidenz-
    intervall (Messrauschen einrechnen!)" -- needed ONE more term added
    manually, past what statsmodels gives for free (Copilot review,
    Finding 2): confirmed empirically that ``res.get_forecast(h).
    var_pred_mean`` already equals the filtered state variance PLUS
    ``sigma2.irregular`` (the MONTHLY-MEAN observation-noise variance)
    to float precision, i.e. statsmodels' own forecast variance for the
    monthly series already is that series' own prediction variance, not
    its latent state's confidence interval. But ``evaluate_series``
    scores individual LOTS, not monthly means, and ``_monthly_series``
    already averaged away whatever within-month lot-to-lot scatter
    existed -- see ``_within_month_lot_variance``'s own docstring for
    why that is added on top here, additively (the two noise sources
    are independent: a lot's deviation from ITS OWN month's mean,
    plus that month's mean's own forecast error). This still holds
    after clamping, since the clamped forecast is read off
    ``mod.smooth(...)`` with the SAME ``UnobservedComponents`` model,
    just fixed parameters.

    Same-month lot weighting ("Mittel + Gewicht nach Anzahl", the 2.2
    alternative to a plain mean): deliberately left as a plain,
    unweighted mean for v1 -- not forgotten, just not pre-emptively
    built. 2.5's own empirical coverage check (80% in [77, 83]) is the
    test the plan itself names for whether this needs revisiting; it is
    not guessed at here."""
    monthly = _monthly_series(train)
    if monthly.notna().sum() < LOCAL_LEVEL_MIN_MONTHS:
        return None
    target_date = (origin if horizon == HORIZON_NEXT
                   else origin + pd.DateOffset(months=12))
    h = _months_between(monthly.index[-1], target_date)
    if h < 1:
        return None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mod = sm.tsa.UnobservedComponents(monthly, level="local level")
            res = mod.fit(disp=False)
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
    if any(clamped.values()):
        res = mod.smooth(params.to_numpy())
    fc = res.get_forecast(h)
    mean = float(fc.predicted_mean.iloc[-1])
    var = float(fc.var_pred_mean.iloc[-1])
    if not np.isfinite(mean) or not np.isfinite(var) or var <= 0:
        return "FIT_FAILED"
    within_month_var, used_fallback = _within_month_lot_variance(train)
    clamped["within_month_variance_fallback"] = used_fallback
    sd = (var + within_month_var) ** 0.5
    quantiles = {q: mean + norm.ppf(q) * sd for q in QUANTILE_LEVELS}
    return quantiles, clamped


def make_local_level_forecaster():
    """Wraps ``local_level_forecast`` into the plain ``Forecaster``
    contract (``-> dict | None``), counting on the returned closure's
    own ``.counters`` instead of threading a second return channel
    through ``eval.py``:

    - ``n_calls``: every invocation.
    - ``n_insufficient_months``: too few monthly points to fit at all
      (``local_level_forecast`` returned ``None``) -- NOT a 2.3
      concern (no fit was ever attempted), but needed as the
      denominator for the other two rates (``n_calls -
      n_insufficient_months`` = fits actually attempted).
    - ``n_fit_failed``: an actually broken fit (2.3's own AC is this
      rate, ">5% of attempted fits ⇒ Review" -- compute it against
      ``n_calls - n_insufficient_months``, not ``n_calls``).
    - ``n_sigma2_irregular_clamped`` / ``n_sigma2_level_clamped``: a
      successful fit where that one variance floor had to bind (see
      ``_SIGMA2_FLOORS``) -- informational, not itself a failure.
    - ``n_within_month_variance_fallback``: a successful fit where
      ``train`` had too few multi-lot months to estimate its own
      within-month lot variance, so the global fallback constant was
      used instead (see ``_within_month_lot_variance``) -- also
      informational, expected to be the common case."""
    counters = {
        "n_calls": 0, "n_insufficient_months": 0, "n_fit_failed": 0,
        "n_sigma2_irregular_clamped": 0, "n_sigma2_level_clamped": 0,
        "n_within_month_variance_fallback": 0,
    }

    def forecaster(train, origin, horizon):
        counters["n_calls"] += 1
        result = local_level_forecast(train, origin, horizon)
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
        if clamped["within_month_variance_fallback"]:
            counters["n_within_month_variance_fallback"] += 1
        return quantiles

    forecaster.counters = counters
    return forecaster
