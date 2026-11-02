import { fireEvent, render, screen } from "@testing-library/react";
import axios from "axios";
import { describe, expect, it, vi } from "vitest";
import App from "./App.jsx";

vi.mock("axios");

function mockAxios() {
  axios.get.mockImplementation((url) => {
    if (url === "/wines/top") {
      return Promise.resolve({
        data: {
          results: [
            {
              wine_id: 1,
              canonical_name: "Château Margaux",
              producer: null,
              region: "Margaux",
              lot_count: 12,
            },
          ],
        },
      });
    }
    if (url === "/wines/1/prices") {
      return Promise.resolve({
        data: {
          wine_id: 1,
          prices: [
            { lot_date: "2020-01-01", price: 500, currency: "EUR", provider: "demo" },
          ],
        },
      });
    }
    return Promise.resolve({ data: { results: [] } });
  });
}

describe("cross-tab navigation", () => {
  it("opens a wine selected from the leaderboard on the search tab", async () => {
    mockAxios();
    render(<App />);

    fireEvent.click(screen.getByRole("tab", { name: /most price data/i }));

    const row = await screen.findByText("Château Margaux");
    fireEvent.click(row);

    expect(screen.getByRole("tab", { name: /^search$/i })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(
      await screen.findByRole("heading", { name: "Château Margaux" }),
    ).toBeInTheDocument();
  });
});
