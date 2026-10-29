import { useEffect, useState } from "react";
import { fetchTopWines } from "../lib/api.js";

export default function TopWinesPanel({ onSelectWine }) {
  const [wines, setWines] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const resp = await fetchTopWines(10);
        if (!cancelled) {
          setWines(resp.data.results);
        }
      } catch (err) {
        console.error("top wines error:", err);
        if (!cancelled) {
          setError(true);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return <p className="empty-note">Couldn't load the leaderboard right now.</p>;
  }
  if (wines === null) {
    return null;
  }
  if (wines.length === 0) {
    return <p className="empty-note">No price data yet.</p>;
  }

  const maxCount = wines[0].lot_count;

  return (
    <div>
      <p className="wine-detail-sub" style={{ marginBottom: 16 }}>
        The wines with the richest auction history in the database — the most
        reliable price time series to start exploring with.
      </p>
      <ul className="leaderboard">
        {wines.map((w, i) => (
          <li
            key={w.wine_id}
            className="leaderboard-row"
            style={{ "--row-delay": `${i * 30}ms` }}
            tabIndex={0}
            onClick={() => onSelectWine(w)}
            onKeyDown={(e) => e.key === "Enter" && onSelectWine(w)}
          >
            <span className="leaderboard-rank">{i + 1}</span>
            <span className="leaderboard-main">
              <div className="leaderboard-name">
                {w.canonical_name}
                {w.producer && (
                  <span className="search-result-meta">— {w.producer}</span>
                )}
              </div>
              <div className="leaderboard-meta">{w.region || " "}</div>
              <div className="leaderboard-bar-track">
                <div
                  className="leaderboard-bar-fill"
                  style={{ width: `${(w.lot_count / maxCount) * 100}%` }}
                />
              </div>
            </span>
            <span className="leaderboard-count">
              {w.lot_count}
              <span className="leaderboard-count-label">lots</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
