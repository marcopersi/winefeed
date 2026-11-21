import { render, screen } from "@testing-library/react";
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
