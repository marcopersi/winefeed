import { useEffect, useState } from "react";
import { fetchPrices, searchWines } from "../lib/api.js";
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
  const [prices, setPrices] = useState([]);

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
      return undefined;
    }
    const timer = setTimeout(async () => {
      try {
        const resp = await searchWines(query, 20);
        setResults(resp.data.results);
      } catch (error) {
        console.error("search error:", error);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [query, selectedWine]);

  useEffect(() => {
    if (!selectedWine) {
      setPrices([]);
      return undefined;
    }
    let cancelled = false;
    (async () => {
      try {
        const resp = await fetchPrices(selectedWine.wine_id);
        if (!cancelled) {
          setPrices(resp.data.prices);
        }
      } catch (error) {
        console.error("prices error:", error);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedWine]);

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
          <PriceChart prices={prices} />
        </div>
      )}
    </div>
  );
}
