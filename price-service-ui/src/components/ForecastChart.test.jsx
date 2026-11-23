import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ForecastChart from "./ForecastChart.jsx";

const PRICES = [
  { lot_date: "2024-01-01", price: 100, currency: "EUR", provider: "x", location: "y" },
];

const AVAILABLE_FORECAST = {
  flags: null, median: 120, q025: 80, q10: 95, q25: 105,
  q75: 135, q90: 145, q975: 160,
};

const TWELVE_MONTH = { key: "12m", label: "12-month", tick: "+12 months" };
const NEXT_SALE = { key: "next", label: "next-sale", tick: "Next sale" };

describe("ForecastChart", () => {
  it("shows an empty note when no horizon has a forecast", () => {
    render(
      <ForecastChart
        prices={PRICES}
        horizons={[{ ...TWELVE_MONTH, forecast: null }]}
      />,
    );
    expect(screen.getByText(/not enough data/i)).toBeInTheDocument();
  });

  it("shows a load-failure note, not 'not enough data', when the request itself failed", () => {
    // Review finding: a failed/timed-out request must not look like a
    // wine that genuinely has too little data for an estimate.
    render(
      <ForecastChart
        prices={PRICES}
        horizons={[{ ...TWELVE_MONTH, forecast: null }]}
        error
      />,
    );
    expect(screen.queryByText(/not enough data/i)).not.toBeInTheDocument();
    expect(screen.getByText(/couldn't load/i)).toBeInTheDocument();
  });

  it("reveals the chart card (is-visible) once an available forecast renders", async () => {
    // Review finding: ForecastChart never added the reveal class that
    // .chart-card's opacity:0 default depends on, so every forecast
    // stayed invisible even when the data was there.
    render(
      <ForecastChart
        prices={PRICES}
        horizons={[{ ...TWELVE_MONTH, forecast: AVAILABLE_FORECAST }]}
      />,
    );
    await waitFor(() =>
      expect(document.querySelector(".chart-card.is-visible")).toBeTruthy());
  });

  it("shows an empty note when every horizon is flagged INSUFFICIENT_DATA", () => {
    render(
      <ForecastChart
        prices={PRICES}
        horizons={[{ ...TWELVE_MONTH, forecast: { flags: "INSUFFICIENT_DATA", median: null } }]}
      />,
    );
    expect(screen.getByText(/not enough data/i)).toBeInTheDocument();
  });

  it("renders the disclaimer and no empty note for an available forecast", () => {
    render(
      <ForecastChart
        prices={PRICES}
        horizons={[{ ...TWELVE_MONTH, forecast: AVAILABLE_FORECAST }]}
      />,
    );
    expect(screen.queryByText(/not enough data/i)).not.toBeInTheDocument();
    expect(screen.getByText(/not investment advice/i)).toBeInTheDocument();
  });

  it("shows the extrapolation caution note when flagged", () => {
    render(
      <ForecastChart
        prices={PRICES}
        horizons={[{
          ...TWELVE_MONTH,
          forecast: {
            flags: "EXTRAPOLATION", median: 500, q025: 300, q10: 350,
            q25: 400, q75: 600, q90: 650, q975: 700,
          },
        }]}
      />,
    );
    expect(screen.getByText(/treat it with/i)).toBeInTheDocument();
  });

  it("plots two available horizons together without error", async () => {
    // The main remaining risk of merging both horizons into one chart:
    // Recharts' Scatter/ErrorBar must handle two real (non-null) points
    // in the same series, not just the one point the single-horizon
    // case always exercised before.
    render(
      <ForecastChart
        prices={PRICES}
        horizons={[
          { ...TWELVE_MONTH, forecast: AVAILABLE_FORECAST },
          { ...NEXT_SALE, forecast: { ...AVAILABLE_FORECAST, median: 90 } },
        ]}
      />,
    );
    await waitFor(() =>
      expect(document.querySelector(".chart-card.is-visible")).toBeTruthy());
    expect(document.querySelectorAll(".chart-card").length).toBe(1);
    expect(screen.queryByText(/not enough data/i)).not.toBeInTheDocument();
  });

  it("plots an available horizon and names a still-missing one in a note below the chart, in one card", () => {
    // Review finding (2026-11-23): one chart per horizon repeated the
    // SAME price-history line once per horizon -- a dense wine (both
    // horizons available) showed it three times across PriceChart and
    // two ForecastCharts. One merged chart plots every available
    // horizon's point together and only one history line.
    render(
      <ForecastChart
        prices={PRICES}
        horizons={[
          { ...TWELVE_MONTH, forecast: AVAILABLE_FORECAST },
          { ...NEXT_SALE, forecast: { flags: "INSUFFICIENT_DATA", median: null } },
        ]}
      />,
    );
    expect(document.querySelectorAll(".chart-card").length).toBe(1);
    expect(screen.getByText(/not enough data yet for a next-sale estimate/i)).toBeInTheDocument();
    expect(screen.queryByText(/not enough data yet for a 12-month estimate/i)).not.toBeInTheDocument();
  });
});
