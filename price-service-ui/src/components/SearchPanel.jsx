import { useEffect, useState } from "react";
import { fetchForecast, fetchPrices, fetchVintages, searchWines } from "../lib/api.js";
import ForecastChart from "./ForecastChart.jsx";
import PriceChart from "./PriceChart.jsx";

// Only "12m" is wired up here: as of the Stufe-4 calibration run
// (docs/forecast-calibration-report.md), the "next" horizon fails its
// held-out coverage band in every density class and would show
// "Not enough data" for literally every wine -- not worth a horizon
// picker nobody could use yet. Revisit once "next" has real coverage.
const FORECAST_HORIZON = "12m";
const FORECAST_HORIZON_LABEL = "12-month estimate";

function SearchIcon() {
  return (
    <svg
      className="search-icon"
      width="18"
      height="18"
      viewBox="0 0 18 18"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="M16 16L12.8 12.8"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

export default function SearchPanel({ selectedWine, onSelectWine }) {
  const [query, setQuery] = useState(selectedWine?.canonical_name ?? "");
  const [results, setResults] = useState([]);
  const [searchError, setSearchError] = useState(false);
  const [vintages, setVintages] = useState([]);
  // requestedVintage: the vintage the USER picked (null = "let the
  // backend default"). resolvedVintage: the vintage the backend actually
  // returned for the current prices response. Kept separate (review
  // finding) so that adopting the backend's default into state doesn't
  // itself change the prices-fetch effect's dependency and fire a
  // second, redundant request for the series already on screen -- a
  // request whose own failure would then clear an already-successfully-
  // loaded chart.
  const [requestedVintage, setRequestedVintage] = useState(null);
  const [resolvedVintage, setResolvedVintage] = useState(null);
  const [prices, setPrices] = useState([]);
  const [pricesError, setPricesError] = useState(false);
  // Review finding: clearing `prices` for an in-flight request (wine
  // switch or vintage switch) left PriceChart's own "No price history
  // found for this wine yet" empty-state showing while a request was
  // merely pending, not actually empty -- misleading for as long as the
  // request takes (up to the full axios timeout on a slow backend).
  // Tracked here instead so that state can be told apart from "actually
  // empty".
  const [pricesLoading, setPricesLoading] = useState(!!selectedWine);
  // The vintage picker's value/gate: the user's own pick once made,
  // otherwise whatever the backend resolved for the open series.
  const displayedVintage = requestedVintage ?? resolvedVintage;
  const [forecast, setForecast] = useState(null);
  const [forecastLoading, setForecastLoading] = useState(!!selectedWine);
  // Kept apart from `forecast === null` (review finding): that also
  // means "the backend itself returned INSUFFICIENT_DATA", a real
  // answer ForecastChart should show as-is, not the same request-
  // failed state as a timeout/503 that never got an answer at all.
  const [forecastError, setForecastError] = useState(false);

  // Cross-tab navigation: the leaderboard can hand us a wine to open here.
  useEffect(() => {
    if (selectedWine) {
      setQuery(selectedWine.canonical_name);
      setResults([]);
    }
  }, [selectedWine]);

  useEffect(() => {
    if (query.length < 2 || query === selectedWine?.canonical_name) {
      setResults([]);
      setSearchError(false);
      return undefined;
    }
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const resp = await searchWines(query, 20);
        if (!cancelled) {
          setResults(resp.data.results);
          setSearchError(false);
        }
      } catch (error) {
        console.error("search error:", error);
        if (!cancelled) {
          setResults([]);
          setSearchError(true);
        }
      }
    }, 300);
    // `cancelled` (not just clearTimeout) matters once the timer has
    // already fired: without it, a slower in-flight request for an
    // earlier keystroke could still resolve after a faster later one and
    // overwrite its results with stale data (senior-review finding).
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query, selectedWine]);

  // Reset immediately on every wine change -- including to a *different*
  // wine, not just to none -- so a slow or failed fetch below can't leave
  // the previous wine's chart on screen under the new wine's heading
  // (senior-review finding). This runs during render, not in an effect:
  // an effect-based reset still lets the prices-fetch effect below read
  // the stale `requestedVintage` from the previous wine in the same
  // render pass (effects run in declaration order against one render's
  // closed-over state), firing one wrong-vintage request for the new
  // wine before a later render corrects it (confirmed in review).
  // Adjusting state during render -- React's documented pattern for
  // "reset state when a prop changes" -- re-renders synchronously before
  // any effect sees the old value, so no wrong request is ever sent.
  const [resetForWineId, setResetForWineId] = useState(selectedWine?.wine_id ?? null);
  if ((selectedWine?.wine_id ?? null) !== resetForWineId) {
    setResetForWineId(selectedWine?.wine_id ?? null);
    setPrices([]);
    setPricesError(false);
    setPricesLoading(!!selectedWine);
    setVintages([]);
    setRequestedVintage(null);
    setResolvedVintage(null);
    setForecast(null);
    setForecastLoading(!!selectedWine);
  }

  useEffect(() => {
    if (!selectedWine) {
      return undefined;
    }
    let cancelled = false;
    (async () => {
      try {
        const resp = await fetchVintages(selectedWine.wine_id);
        if (!cancelled) {
          setVintages(resp.data.vintages ?? []);
        }
      } catch (error) {
        console.error("vintages error:", error);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedWine]);

  useEffect(() => {
    if (!selectedWine) {
      return undefined;
    }
    let cancelled = false;
    setPricesLoading(true);
    (async () => {
      try {
        const resp = await fetchPrices(selectedWine.wine_id, requestedVintage);
        if (cancelled) {
          return;
        }
        setPrices(resp.data.prices ?? []);
        setPricesError(false);
        // The backend defaults to the most-traded vintage when none is
        // requested; record it as `resolvedVintage` only (not
        // `requestedVintage`) so the picker shows it without this same
        // effect re-firing a redundant second request for the series
        // that was just successfully loaded (review finding).
        setResolvedVintage(resp.data.vintage ?? null);
      } catch (error) {
        console.error("prices error:", error);
        if (!cancelled) {
          setPrices([]);
          setPricesError(true);
        }
      } finally {
        if (!cancelled) {
          setPricesLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedWine, requestedVintage]);

  useEffect(() => {
    if (!selectedWine) {
      return undefined;
    }
    let cancelled = false;
    setForecastLoading(true);
    (async () => {
      try {
        const resp = await fetchForecast(selectedWine.wine_id, requestedVintage);
        if (!cancelled) {
          setForecast(resp.data.forecasts?.[FORECAST_HORIZON] ?? null);
          setForecastError(false);
        }
      } catch (error) {
        console.error("forecast error:", error);
        if (!cancelled) {
          setForecast(null);
          setForecastError(true);
        }
      } finally {
        if (!cancelled) {
          setForecastLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedWine, requestedVintage]);

  function changeVintage(vintage) {
    // Cleared here, not in an effect: otherwise the old series (or a
    // stale error) stays on screen -- looking current -- for as long as
    // the new vintage's request is in flight (review finding; the same
    // stale-chart risk the wine-switch reset above already guards).
    // `pricesLoading` set here too (not left to the effect) so the UI
    // shows "loading", never a one-frame "no price history" flash, the
    // instant the user picks a vintage.
    setPrices([]);
    setPricesError(false);
    setPricesLoading(true);
    setForecast(null);
    setForecastError(false);
    setForecastLoading(true);
    setRequestedVintage(vintage);
  }

  function selectResult(result) {
    onSelectWine(result);
    setResults([]);
  }

  return (
    <div>
      <div className="search-field">
        <SearchIcon />
        <input
          type="text"
          className="search-input"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            if (selectedWine) {
              onSelectWine(null);
            }
          }}
          placeholder="Search for a wine…"
          autoFocus
          aria-label="Search for a wine"
        />
      </div>

      {searchError && (
        <p className="empty-note">Search is unavailable right now.</p>
      )}

      {results.length > 0 && (
        <ul className="search-results">
          {results.map((r) => (
            <li
              key={r.wine_id}
              className="search-result"
              tabIndex={0}
              onClick={() => selectResult(r)}
              onKeyDown={(e) => e.key === "Enter" && selectResult(r)}
            >
              <span>
                <span className="search-result-name">{r.canonical_name}</span>
                {r.producer && (
                  <span className="search-result-meta">— {r.producer}</span>
                )}
                {r.region && <span className="search-result-meta">({r.region})</span>}
              </span>
              <span className="search-result-count">{r.lot_count} lots</span>
            </li>
          ))}
        </ul>
      )}

      {selectedWine && (
        <div className="wine-detail">
          <h2 className="wine-detail-heading">{selectedWine.canonical_name}</h2>
          <p className="wine-detail-sub">
            {[selectedWine.producer, selectedWine.region].filter(Boolean).join(" · ") ||
              "Price history"}
          </p>

          {/* Gated on displayedVintage too: vintages and the default-
              vintage adoption from the prices fetch resolve
              independently, so rendering the select as soon as vintages
              arrives could show a controlled value with no matching
              option yet (review finding). */}
          {vintages.length > 1 && displayedVintage != null && (
            <div className="vintage-picker">
              <label htmlFor="vintage-select" className="vintage-picker-label">
                Vintage
              </label>
              <select
                id="vintage-select"
                className="vintage-picker-select"
                value={displayedVintage}
                onChange={(e) => changeVintage(Number(e.target.value))}
              >
                {vintages.map((v) => (
                  <option key={v.vintage} value={v.vintage}>
                    {v.vintage} ({v.lot_count})
                  </option>
                ))}
              </select>
            </div>
          )}

          {pricesLoading ? (
            <p className="empty-note">Loading price history…</p>
          ) : pricesError ? (
            <p className="empty-note">Couldn't load the price history right now.</p>
          ) : (
            <PriceChart prices={prices} />
          )}

          {!pricesLoading && !pricesError && prices.length > 0 && !forecastLoading && (
            <ForecastChart
              prices={prices}
              forecast={forecast}
              error={forecastError}
              horizonLabel={FORECAST_HORIZON_LABEL}
            />
          )}
        </div>
      )}
    </div>
  );
}
