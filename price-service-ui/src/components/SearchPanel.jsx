import { useEffect, useState } from "react";
import { fetchPrices, fetchVintages, searchWines } from "../lib/api.js";
import PriceChart from "./PriceChart.jsx";

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
  const [selectedVintage, setSelectedVintage] = useState(null);
  const [prices, setPrices] = useState([]);
  const [pricesError, setPricesError] = useState(false);

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
  // the stale `selectedVintage` from the previous wine in the same
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
    setVintages([]);
    setSelectedVintage(null);
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
    (async () => {
      try {
        const resp = await fetchPrices(selectedWine.wine_id, selectedVintage);
        if (cancelled) {
          return;
        }
        setPrices(resp.data.prices ?? []);
        setPricesError(false);
        // The backend defaults to the most-traded vintage when none is
        // given; adopt it so the picker reflects what's actually shown.
        if (selectedVintage == null && resp.data.vintage != null) {
          setSelectedVintage(resp.data.vintage);
        }
      } catch (error) {
        console.error("prices error:", error);
        if (!cancelled) {
          setPrices([]);
          setPricesError(true);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedWine, selectedVintage]);

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

          {/* Gated on selectedVintage too: vintages and the default-vintage
              adoption from the prices fetch resolve independently, so
              rendering the select as soon as vintages arrives could show
              a controlled value with no matching option yet (review
              finding). */}
          {vintages.length > 1 && selectedVintage != null && (
            <div className="vintage-picker">
              <label htmlFor="vintage-select" className="vintage-picker-label">
                Vintage
              </label>
              <select
                id="vintage-select"
                className="vintage-picker-select"
                value={selectedVintage}
                onChange={(e) => setSelectedVintage(Number(e.target.value))}
              >
                {vintages.map((v) => (
                  <option key={v.vintage} value={v.vintage}>
                    {v.vintage} ({v.lot_count})
                  </option>
                ))}
              </select>
            </div>
          )}

          {pricesError ? (
            <p className="empty-note">Couldn't load the price history right now.</p>
          ) : (
            <PriceChart prices={prices} />
          )}
        </div>
      )}
    </div>
  );
}
