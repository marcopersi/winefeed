import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ForecastChart from "./ForecastChart.jsx";

const PRICES = [
  { lot_date: "2024-01-01", price: 100, currency: "EUR", provider: "x", location: "y" },
];

describe("ForecastChart", () => {
  it("shows an empty note when the horizon has no forecast at all", () => {
    render(<ForecastChart prices={PRICES} forecast={null} horizonLabel="12-month estimate" />);
    expect(screen.getByText(/not enough data/i)).toBeInTheDocument();
  });

  it("shows a load-failure note, not 'not enough data', when the request itself failed", () => {
    // Review finding: a failed/timed-out request must not look like a
    // wine that genuinely has too little data for an estimate.
    render(
      <ForecastChart prices={PRICES} forecast={null} error horizonLabel="12-month estimate" />,
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
        forecast={{
          flags: null, median: 120, q025: 80, q10: 95, q25: 105,
          q75: 135, q90: 145, q975: 160,
        }}
        horizonLabel="12-month estimate"
      />,
    );
    await waitFor(() =>
      expect(document.querySelector(".chart-card.is-visible")).toBeTruthy());
  });

  it("shows an empty note when flagged INSUFFICIENT_DATA", () => {
    render(
      <ForecastChart
        prices={PRICES}
        forecast={{ flags: "INSUFFICIENT_DATA", median: null }}
        horizonLabel="12-month estimate"
      />,
    );
    expect(screen.getByText(/not enough data/i)).toBeInTheDocument();
  });

  it("renders the disclaimer and no empty note for an available forecast", () => {
    render(
      <ForecastChart
        prices={PRICES}
        forecast={{
          flags: null, median: 120, q025: 80, q10: 95, q25: 105,
          q75: 135, q90: 145, q975: 160,
        }}
        horizonLabel="12-month estimate"
      />,
    );
    expect(screen.queryByText(/not enough data/i)).not.toBeInTheDocument();
    expect(screen.getByText(/not investment advice/i)).toBeInTheDocument();
  });

  it("shows the extrapolation caution note when flagged", () => {
    render(
      <ForecastChart
        prices={PRICES}
        forecast={{
          flags: "EXTRAPOLATION", median: 500, q025: 300, q10: 350,
          q25: 400, q75: 600, q90: 650, q975: 700,
        }}
        horizonLabel="12-month estimate"
      />,
    );
    expect(screen.getByText(/treat it with/i)).toBeInTheDocument();
  });
});
