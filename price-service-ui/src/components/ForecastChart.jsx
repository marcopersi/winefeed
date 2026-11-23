import {
  CartesianGrid, ComposedChart, ErrorBar, Line, ResponsiveContainer,
  Scatter, Tooltip, XAxis, YAxis,
} from "recharts";
import { HistoryTooltipBody, formatDate, useRevealOnData } from "./PriceChart.jsx";

function fmtPrice(value) {
  return value == null
    ? "–"
    : value.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function ForecastTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) {
    return null;
  }
  const point = payload[0].payload;
  if (point.isForecast) {
    return (
      <div className="chart-tooltip">
        <p className="chart-tooltip-date">{point.horizonLabel} estimate</p>
        <p className="chart-tooltip-value">
          <span
            className="chart-tooltip-swatch forecast-swatch"
            aria-hidden="true"
          />
          {fmtPrice(point.median)} EUR (estimate)
        </p>
        <p className="chart-tooltip-provider">
          50%: {fmtPrice(point.q25)}–{fmtPrice(point.q75)} · 80%:{" "}
          {fmtPrice(point.q10)}–{fmtPrice(point.q90)} · 95%:{" "}
          {fmtPrice(point.q025)}–{fmtPrice(point.q975)}
        </p>
      </div>
    );
  }
  return (
    <div className="chart-tooltip">
      <HistoryTooltipBody point={point} />
    </div>
  );
}

// A fan chart extends the SAME metric (this wine's price) into one or
// more estimates -- the lighter step of --series-1, never a new hue,
// with each point's own tick label (never color alone) to carry the
// "this one is uncertain" distinction. One card, one price-history
// line, however many horizons have real coverage for this wine's
// density class -- plotting each horizon as a SECOND chart (its own
// copy of the same history line) would repeat that line once per
// horizon for no reason (review finding, 2026-11-23: with "next" and
// "12m" both wired up, a dense wine showed the identical history line
// three times across PriceChart + two ForecastCharts).
//
// `horizons` is `[{ key, label, tick, forecast }]`, in display order;
// `forecast` is the backend's per-horizon answer (or ``null``/
// ``undefined`` while loading). Horizons whose `forecast.flags ===
// "INSUFFICIENT_DATA"` (or whose `forecast` is missing) are not
// plotted -- 3.6's own "that is the result, not an error" -- but are
// still named in a note below the chart, never silently dropped.
export default function ForecastChart({ prices, horizons, error }) {
  const available = horizons.filter(
    (h) => h.forecast && h.forecast.flags !== "INSUFFICIENT_DATA",
  );
  const missing = horizons.filter((h) => !available.includes(h));
  const hasAny = !error && available.length > 0;
  // Hook must run on every render (rules of hooks) -- the empty-state
  // early returns below happen after it, not before.
  const visible = useRevealOnData(hasAny);

  if (error) {
    return <p className="empty-note">Couldn't load the price estimate right now.</p>;
  }
  if (!hasAny) {
    return <p className="empty-note">Not enough data yet for a price estimate.</p>;
  }

  const history = prices.map((p) => ({ ...p, isForecast: false }));
  const forecastPoints = available.map((h) => ({
    lot_date: h.tick,
    isForecast: true,
    horizonLabel: h.label,
    median: h.forecast.median,
    q025: h.forecast.q025,
    q10: h.forecast.q10,
    q25: h.forecast.q25,
    q75: h.forecast.q75,
    q90: h.forecast.q90,
    q975: h.forecast.q975,
    // forecastMedian/forecastRange are the Scatter+ErrorBar's own plot
    // fields, derived from median/q10/q90 above (the same values the
    // tooltip shows) -- if the plotted band ever changes to a
    // different interval (e.g. 95% instead of 80%), update both this
    // line and the tooltip's 80% row together, not just one.
    forecastMedian: h.forecast.median,
    forecastRange: [h.forecast.median - h.forecast.q10, h.forecast.q90 - h.forecast.median],
  }));
  const data = [...history, ...forecastPoints];
  const extrapolated = available.filter((h) => h.forecast.flags === "EXTRAPOLATION");

  return (
    <div className={`chart-card forecast-chart${visible ? " is-visible" : ""}`}>
      {extrapolated.map((h) => (
        <p className="forecast-flag-note" key={h.key}>
          The {h.label.toLowerCase()} estimate extends well beyond recent
          prices — treat it with extra caution.
        </p>
      ))}
      <ResponsiveContainer width="100%" height={380}>
        <ComposedChart data={data} margin={{ top: 8, right: 24, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--gridline)" />
          <XAxis
            dataKey="lot_date"
            tickFormatter={formatDate}
            tick={{ fill: "var(--text-muted)", fontSize: 12 }}
            axisLine={{ stroke: "var(--baseline)" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "var(--text-muted)", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={56}
          />
          <Tooltip
            content={<ForecastTooltip />}
            cursor={{ stroke: "var(--baseline)", strokeWidth: 1 }}
          />
          <Line
            type="monotone"
            dataKey="price"
            stroke="var(--series-1)"
            strokeWidth={2}
            dot={{
              r: 4,
              fill: "var(--series-1)",
              stroke: "var(--surface-1)",
              strokeWidth: 2,
            }}
            connectNulls={false}
            isAnimationActive={false}
          />
          <Scatter
            dataKey="forecastMedian"
            fill="var(--series-1-step-250)"
            shape="diamond"
            isAnimationActive={false}
          >
            <ErrorBar
              dataKey="forecastRange"
              width={8}
              strokeWidth={2}
              stroke="var(--series-1-step-250)"
            />
          </Scatter>
        </ComposedChart>
      </ResponsiveContainer>
      {missing.length > 0 && (
        <p className="empty-note forecast-missing-note">
          Not enough data yet for{" "}
          {missing.map((h) => `a ${h.label.toLowerCase()} estimate`).join(" or ")}.
        </p>
      )}
      <p className="forecast-disclaimer">
        Estimate: median + 50/80/95% ranges — not investment advice.
      </p>
    </div>
  );
}
