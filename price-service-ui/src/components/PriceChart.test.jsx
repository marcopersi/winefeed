import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PriceChart, { formatDate } from "./PriceChart.jsx";

describe("formatDate", () => {
  it("converts ISO to dd.MM.yyyy", () => {
    expect(formatDate("2020-06-15")).toBe("15.06.2020");
  });

  it("returns unparseable input unchanged instead of guessing", () => {
    expect(formatDate("not-a-date")).toBe("not-a-date");
  });

  it("passes through empty input", () => {
    expect(formatDate("")).toBe("");
  });
});

describe("PriceChart", () => {
  it("shows an empty note when there is no price history", () => {
    render(<PriceChart prices={[]} />);
    expect(
      screen.getByText(/no price history found for this wine yet/i),
    ).toBeInTheDocument();
  });
});
