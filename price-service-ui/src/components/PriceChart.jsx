import { useEffect, useRef, useState } from "react";
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis,
  YAxis,
} from "recharts";

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) {
    return null;
  }
  const point = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip-date">{label}</p>
      <p className="chart-tooltip-value">
        <span className="chart-tooltip-swatch" aria-hidden="true" />
        {point.price.toLocaleString(undefined, {
          maximumFractionDigits: 0,
        })}{" "}
        {point.currency}
      </p>
      <p className="chart-tooltip-provider">{point.provider}</p>
    </div>
  );
}

// Fades/slides the chart in once its data has actually arrived, instead of
// popping into place the instant the fetch resolves.
function useRevealOnData(hasData) {
  const [visible, setVisible] = useState(false);
  const frame = useRef(null);

  useEffect(() => {
    if (!hasData) {
      setVisible(false);
      return undefined;
    }
    setVisible(false);
    frame.current = requestAnimationFrame(() => {
      frame.current = requestAnimationFrame(() => setVisible(true));
    });
    return () => cancelAnimationFrame(frame.current);
  }, [hasData]);

  return visible;
}

export default function PriceChart({ prices }) {
  const hasData = prices.length > 0;
  const visible = useRevealOnData(hasData);

  if (!hasData) {
    return <p className="empty-note">No price history found for this wine yet.</p>;
  }

  return (
    <div className={`chart-card${visible ? " is-visible" : ""}`}>
      <ResponsiveContainer width="100%" height={380}>
        <LineChart data={prices} margin={{ top: 8, right: 24, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--gridline)" />
          <XAxis
            dataKey="lot_date"
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
            content={<ChartTooltip />}
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
            activeDot={{
              r: 5,
              fill: "var(--series-1)",
              stroke: "var(--surface-1)",
              strokeWidth: 2,
            }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
