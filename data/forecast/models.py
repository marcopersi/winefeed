"""1.3: fixed-effects model isolating house/lot effects from "true" wine
value. 1.4: baseline forecasting methods.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm

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

def _load_fe_frame(conn):
    """All of ``forecast_input`` plus ``quantity``/``size_assumed`` from
    ``lots``, for the fixed-effects regression below.

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
               l.quantity, l.size_assumed, fi.price_per_bottle_eur
        FROM forecast_input fi
        JOIN lots l ON l.id = fi.lot_id
        JOIN providers p ON p.id = fi.provider_id
        """).fetchall()
    df = pd.DataFrame(rows, columns=[
        "wine_ref_id", "vintage", "size_class", "provider",
        "quantity", "size_assumed", "price"])
    df["quantity"] = df["quantity"].fillna(1).astype(float)
    df["size_assumed"] = df["size_assumed"].fillna(0).astype(float)
    df["y"] = np.log(df["price"].astype(float))
    df["log_qty"] = np.log(df["quantity"])
    df["group"] = (df["wine_ref_id"].astype(str) + "|"
                   + df["vintage"].astype(str) + "|"
                   + df["size_class"].astype(str))
    return df


def fit_provider_effects(conn):
    """``y ~ wine_ref_id*vintage*size_class (absorbed) + provider +
    log(qty) + size_assumed``, by the within (demeaning) estimator.

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
    df = _load_fe_frame(conn)
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
