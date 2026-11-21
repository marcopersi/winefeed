import {
  CartesianGrid, ComposedChart, ErrorBar, Line, ResponsiveContainer,
  Scatter, Tooltip, XAxis, YAxis,
} from "recharts";
import { HistoryTooltipBody, formatDate, useRevealOnData } from "./PriceChart.jsx";

const FORECAST_TICK = "Estimate";

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
        <p className="chart-tooltip-date">{point.horizonLabel}</p>
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

// A fan chart extends the SAME metric (this wine's price) into an
// estimate, not a second series -- the lighter step of --series-1,
// never a new hue, with a direct "Estimate" label (never color alone)
// to carry the "this one is uncertain" distinction.
export default function ForecastChart({ prices, forecast, error, horizonLabel }) {
  const hasForecast = !error && !!forecast && forecast.flags !== "INSUFFICIENT_DATA";
  // Hook must run on every render (rules of hooks) -- the empty-state
  // early returns below happen after it, not before.
  const visible = useRevealOnData(hasForecast);

  if (error) {
    return (
      <p className="empty-note">
        Couldn't load the {horizonLabel.toLowerCase()} right now.
      </p>
    );
  }
  if (!hasForecast) {
    return (
      <p className="empty-note">
        Not enough data yet for a {horizonLabel.toLowerCase()} estimate.
      </p>
    );
  }

  const history = prices.map((p) => ({ ...p, isForecast: false }));
  const forecastPoint = {
    lot_date: FORECAST_TICK,
    isForecast: true,
    horizonLabel,
    median: forecast.median,
    q025: forecast.q025,
    q10: forecast.q10,
    q25: forecast.q25,
    q75: forecast.q75,
    q90: forecast.q90,
    q975: forecast.q975,
    // forecastMedian/forecastRange are the Scatter+ErrorBar's own plot
    // fields, derived from median/q10/q90 above (the same values the
    // tooltip shows) -- if the plotted band ever changes to a
    // different interval (e.g. 95% instead of 80%), update both this
    // line and the tooltip's 80% row together, not just one.
    forecastMedian: forecast.median,
    forecastRange: [forecast.median - forecast.q10, forecast.q90 - forecast.median],
  };
  const data = [...history, forecastPoint];

  return (
    <div className={`chart-card forecast-chart${visible ? " is-visible" : ""}`}>
      {forecast.flags === "EXTRAPOLATION" && (
        <p className="forecast-flag-note">
          This estimate extends well beyond recent prices — treat it with
          extra caution.
        </p>
      )}
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
      <p className="forecast-disclaimer">
        {horizonLabel} estimate, median + 50/80/95% ranges — not investment
        advice.
      </p>
    </div>
  );
}
