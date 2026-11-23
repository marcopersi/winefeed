import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import axios from "axios";
import { afterEach, describe, expect, it, vi } from "vitest";
import SearchPanel from "./SearchPanel.jsx";

vi.mock("axios");

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

const WINE_A = { wine_id: 1, canonical_name: "Wine A", producer: null, region: null };
const WINE_B = { wine_id: 2, canonical_name: "Wine B", producer: null, region: null };

afterEach(() => {
  vi.resetAllMocks();
});

describe("SearchPanel wine switching", () => {
  it("clears the previous wine's chart instead of showing it under the new heading", async () => {
    const pendingPricesA = deferred();
    const pendingPricesB = deferred();
    axios.get.mockImplementation((url) => {
      if (url === "/wines/1/vintages" || url === "/wines/2/vintages") {
        return Promise.resolve({ data: { vintages: [] } });
      }
      if (url === "/wines/1/prices") {
        return pendingPricesA.promise;
      }
      if (url === "/wines/2/prices") {
        return pendingPricesB.promise;
      }
      return Promise.resolve({ data: { results: [] } });
    });

    const { rerender } = render(
      <SearchPanel selectedWine={WINE_A} onSelectWine={() => {}} />,
    );
    // Wine A's /prices fetch hasn't resolved yet -- a loading state, not
    // an "empty" or stale one, must be shown (second-review-pass finding:
    // the empty-state message used to show here too, misleadingly).
    await screen.findByText(/loading price history/i);

    pendingPricesA.resolve({
      data: { vintage: 2015, prices: [{ lot_date: "2015-01-01", price: 100, currency: "EUR" }] },
    });
    await waitFor(() =>
      expect(screen.queryByText(/loading price history/i)).not.toBeInTheDocument(),
    );

    rerender(<SearchPanel selectedWine={WINE_B} onSelectWine={() => {}} />);

    // Wine B's /prices fetch hasn't resolved yet -- the panel must show a
    // loading state, not leftover data from Wine A (senior-review
    // finding).
    expect(screen.getByText(/loading price history/i)).toBeInTheDocument();

    pendingPricesB.resolve({
      data: { vintage: 2018, prices: [{ lot_date: "2018-01-01", price: 200, currency: "EUR" }] },
    });
    await waitFor(() =>
      expect(screen.queryByText(/loading price history/i)).not.toBeInTheDocument(),
    );
  });

  it("shows an error note instead of stale data when the price fetch fails", async () => {
    axios.get.mockImplementation((url) => {
      if (url === "/wines/1/vintages") {
        return Promise.resolve({ data: { vintages: [] } });
      }
      if (url === "/wines/1/prices") {
        return Promise.reject(new Error("network error"));
      }
      return Promise.resolve({ data: { results: [] } });
    });

    render(<SearchPanel selectedWine={WINE_A} onSelectWine={() => {}} />);
    expect(
      await screen.findByText(/couldn't load the price history/i),
    ).toBeInTheDocument();
  });

  it("never requests the new wine's prices with the previous wine's picked vintage", async () => {
    // Senior-review finding, reproduced live: resetting vintage state in
    // an effect (instead of during render) let the prices-fetch effect
    // still read the old wine's stale vintage on the very first render
    // after switching wines. A backend-*adopted* default vintage can no
    // longer leak this way (it lands only in `resolvedVintage`, never
    // sent as a request param, per the requestedVintage/resolvedVintage
    // split -- second-review-pass finding: a version of this test that
    // never drives the picker can't exercise that leak at all, since the
    // only way `requestedVintage` becomes non-null is a user pick), so
    // this test drives the picker itself to reproduce the real risk.
    axios.get.mockImplementation((url, config) => {
      if (url === "/wines/1/vintages") {
        return Promise.resolve({
          data: { vintages: [{ vintage: 2015, lot_count: 3 }, { vintage: 2010, lot_count: 1 }] },
        });
      }
      if (url === "/wines/2/vintages") {
        return Promise.resolve({ data: { vintages: [] } });
      }
      if (url === "/wines/1/prices") {
        const vintage = config.params.vintage ?? 2015;
        return Promise.resolve({ data: { vintage, prices: [] } });
      }
      if (url === "/wines/2/prices") {
        return Promise.resolve({ data: { vintage: 2018, prices: [] } });
      }
      return Promise.resolve({ data: { results: [] } });
    });

    const { rerender } = render(
      <SearchPanel selectedWine={WINE_A} onSelectWine={() => {}} />,
    );
    const select = await screen.findByLabelText(/vintage/i);
    fireEvent.change(select, { target: { value: "2010" } });
    await waitFor(() =>
      expect(axios.get).toHaveBeenCalledWith(
        "/wines/1/prices",
        expect.objectContaining({ params: { vintage: 2010 } }),
      ),
    );

    rerender(<SearchPanel selectedWine={WINE_B} onSelectWine={() => {}} />);
    await waitFor(() =>
      expect(axios.get).toHaveBeenCalledWith(
        "/wines/2/prices",
        expect.objectContaining({ params: {} }),
      ),
    );

    const wineBPriceCalls = axios.get.mock.calls.filter(([url]) => url === "/wines/2/prices");
    for (const [, config] of wineBPriceCalls) {
      expect(config.params.vintage).not.toBe(2010);
    }
  });
});

describe("SearchPanel search", () => {
  it("shows a visible error note when the search request fails", async () => {
    axios.get.mockImplementation((url) => {
      if (url === "/search") {
        return Promise.reject(new Error("network error"));
      }
      return Promise.resolve({ data: { results: [] } });
    });

    render(<SearchPanel selectedWine={null} onSelectWine={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText(/search for a wine/i), {
      target: { value: "margaux" },
    });

    expect(
      await screen.findByText(/search is unavailable/i),
    ).toBeInTheDocument();
  });

  it("does not let a slower, earlier keystroke's response overwrite a newer one", async () => {
    const slowFirst = deferred();
    const fastSecond = deferred();
    axios.get.mockImplementation((url, config) => {
      if (url === "/search" && config.params.q === "ab") {
        return slowFirst.promise;
      }
      if (url === "/search" && config.params.q === "abc") {
        return fastSecond.promise;
      }
      return Promise.resolve({ data: { results: [] } });
    });

    render(<SearchPanel selectedWine={null} onSelectWine={() => {}} />);
    const input = screen.getByPlaceholderText(/search for a wine/i);

    fireEvent.change(input, { target: { value: "ab" } });
    await new Promise((r) => setTimeout(r, 310));
    fireEvent.change(input, { target: { value: "abc" } });
    await new Promise((r) => setTimeout(r, 310));

    // Resolve the newer ("abc") request first, then the stale ("ab") one.
    fastSecond.resolve({
      data: { results: [{ wine_id: 1, canonical_name: "ABC Wine", lot_count: 1 }] },
    });
    await screen.findByText("ABC Wine");

    slowFirst.resolve({
      data: { results: [{ wine_id: 2, canonical_name: "AB Wine", lot_count: 1 }] },
    });
    // Give the stale promise's .then a chance to run (and be ignored).
    await new Promise((r) => setTimeout(r, 0));

    expect(screen.getByText("ABC Wine")).toBeInTheDocument();
    expect(screen.queryByText("AB Wine")).not.toBeInTheDocument();
  });
});

describe("SearchPanel vintage picker", () => {
  it("offers a vintage picker and refetches prices for the chosen vintage", async () => {
    axios.get.mockImplementation((url, config) => {
      if (url === "/wines/1/vintages") {
        return Promise.resolve({
          data: { vintages: [{ vintage: 2015, lot_count: 5 }, { vintage: 2010, lot_count: 2 }] },
        });
      }
      if (url === "/wines/1/prices") {
        const vintage = config.params.vintage ?? 2015;
        return Promise.resolve({
          data: { vintage, prices: [{ lot_date: "2020-01-01", price: vintage, currency: "EUR" }] },
        });
      }
      return Promise.resolve({ data: { results: [] } });
    });

    render(<SearchPanel selectedWine={WINE_A} onSelectWine={() => {}} />);
    const select = await screen.findByLabelText(/vintage/i);
    expect(screen.getByRole("option", { name: "2015 (5)" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "2010 (2)" })).toBeInTheDocument();

    fireEvent.change(select, { target: { value: "2010" } });

    await waitFor(() =>
      expect(axios.get).toHaveBeenCalledWith(
        "/wines/1/prices",
        expect.objectContaining({ params: expect.objectContaining({ vintage: 2010 }) }),
      ),
    );
  });

  it("hides the picker when there is only one vintage", async () => {
    axios.get.mockImplementation((url) => {
      if (url === "/wines/1/vintages") {
        return Promise.resolve({ data: { vintages: [{ vintage: 2015, lot_count: 5 }] } });
      }
      if (url === "/wines/1/prices") {
        return Promise.resolve({ data: { vintage: 2015, prices: [] } });
      }
      return Promise.resolve({ data: { results: [] } });
    });

    render(<SearchPanel selectedWine={WINE_A} onSelectWine={() => {}} />);
    await screen.findByText(/no price history/i);
    expect(screen.queryByLabelText(/vintage/i)).not.toBeInTheDocument();
  });

  it("shows a load-failure note, not 'not enough data', when the forecast fetch fails", async () => {
    // Review finding: a failed/timed-out forecast request used to set
    // `forecast` to null, which ForecastChart renders identically to a
    // real INSUFFICIENT_DATA answer -- telling the user their wine
    // lacks data when the service simply failed to load it.
    axios.get.mockImplementation((url) => {
      if (url === "/wines/1/vintages") {
        return Promise.resolve({ data: { vintages: [] } });
      }
      if (url === "/wines/1/prices") {
        return Promise.resolve({
          data: { vintage: 2015, prices: [{ lot_date: "2015-01-01", price: 100, currency: "EUR" }] },
        });
      }
      if (url === "/wines/1/forecast") {
        return Promise.reject(new Error("network error"));
      }
      return Promise.resolve({ data: { results: [] } });
    });

    render(<SearchPanel selectedWine={WINE_A} onSelectWine={() => {}} />);
    expect(await screen.findByText(/couldn't load the price estimate/i)).toBeInTheDocument();
    expect(screen.queryByText(/not enough data/i)).not.toBeInTheDocument();
  });

  it("plots the 12-month estimate and names next-sale as still missing, in one chart", async () => {
    // "next" used to be hidden entirely (every density class failed its
    // held-out coverage band); the backend now serves it a real
    // forecast/INSUFFICIENT_DATA decision per density class just like
    // "12m". Both now render through ONE ForecastChart (review finding,
    // 2026-11-23: one chart per horizon repeated the same price-history
    // line once per horizon).
    axios.get.mockImplementation((url) => {
      if (url === "/wines/1/vintages") {
        return Promise.resolve({ data: { vintages: [] } });
      }
      if (url === "/wines/1/prices") {
        return Promise.resolve({
          data: { vintage: 2015, prices: [{ lot_date: "2015-01-01", price: 100, currency: "EUR" }] },
        });
      }
      if (url === "/wines/1/forecast") {
        return Promise.resolve({
          data: {
            forecasts: {
              next: { flags: "INSUFFICIENT_DATA", median: null },
              "12m": {
                flags: null, median: 120, q025: 80, q10: 95, q25: 105,
                q75: 135, q90: 145, q975: 160,
              },
            },
          },
        });
      }
      return Promise.resolve({ data: { results: [] } });
    });

    render(<SearchPanel selectedWine={WINE_A} onSelectWine={() => {}} />);
    expect(
      await screen.findByText(/not enough data yet for a next-sale estimate/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/not investment advice/i)).toBeInTheDocument();
    // One merged forecast card (PriceChart's own .chart-card is separate).
    expect(document.querySelectorAll(".chart-card.forecast-chart").length).toBe(1);
  });
});
