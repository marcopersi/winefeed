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
    const pendingPricesB = deferred();
    axios.get.mockImplementation((url) => {
      if (url === "/wines/1/vintages" || url === "/wines/2/vintages") {
        return Promise.resolve({ data: { vintages: [] } });
      }
      if (url === "/wines/1/prices") {
        return Promise.resolve({
          data: { vintage: 2015, prices: [{ lot_date: "2015-01-01", price: 100, currency: "EUR" }] },
        });
      }
      if (url === "/wines/2/prices") {
        return pendingPricesB.promise;
      }
      return Promise.resolve({ data: { results: [] } });
    });

    const { rerender } = render(
      <SearchPanel selectedWine={WINE_A} onSelectWine={() => {}} />,
    );
    await screen.findByText(/no price history/i);
    // Wine A's fetch never resolved with real points in this test, but the
    // important thing is what's on screen once we switch to Wine B.

    rerender(<SearchPanel selectedWine={WINE_B} onSelectWine={() => {}} />);

    // Wine B's /prices fetch hasn't resolved yet -- the panel must show the
    // empty state, not leftover data from Wine A (senior-review finding).
    expect(screen.getByText(/no price history/i)).toBeInTheDocument();

    pendingPricesB.resolve({
      data: { vintage: 2018, prices: [{ lot_date: "2018-01-01", price: 200, currency: "EUR" }] },
    });
    await waitFor(() => expect(screen.queryByText(/no price history/i)).not.toBeInTheDocument());
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

  it("never requests the new wine's prices with the previous wine's adopted vintage", async () => {
    // Senior-review finding, reproduced live: resetting vintage state in
    // an effect (instead of during render) let the prices-fetch effect
    // still read the old wine's stale `selectedVintage` on the very
    // first render after switching wines.
    axios.get.mockImplementation((url, config) => {
      if (url === "/wines/1/vintages" || url === "/wines/2/vintages") {
        return Promise.resolve({ data: { vintages: [{ vintage: 2015, lot_count: 3 }] } });
      }
      if (url === "/wines/1/prices") {
        return Promise.resolve({ data: { vintage: 2015, prices: [] } });
      }
      if (url === "/wines/2/prices") {
        return Promise.resolve({ data: { vintage: 2018, prices: [] } });
      }
      return Promise.resolve({ data: { results: [] } });
    });

    const { rerender } = render(
      <SearchPanel selectedWine={WINE_A} onSelectWine={() => {}} />,
    );
    // Let Wine A's prices fetch resolve and adopt vintage 2015.
    await waitFor(() =>
      expect(axios.get).toHaveBeenCalledWith(
        "/wines/1/prices",
        expect.objectContaining({ params: {} }),
      ),
    );

    rerender(<SearchPanel selectedWine={WINE_B} onSelectWine={() => {}} />);
    await waitFor(() =>
      expect(axios.get).toHaveBeenCalledWith(
        "/wines/2/prices",
        expect.objectContaining({ params: {} }),
      ),
    );

    // Wine B may legitimately get a follow-up request for its OWN
    // adopted vintage (2018) once that's known -- the bug was leaking
    // Wine A's vintage (2015) into a Wine B request, not any vintage
    // param at all.
    const wineBPriceCalls = axios.get.mock.calls.filter(([url]) => url === "/wines/2/prices");
    expect(wineBPriceCalls.length).toBeGreaterThan(0);
    for (const [, config] of wineBPriceCalls) {
      expect(config.params.vintage).not.toBe(2015);
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
});
