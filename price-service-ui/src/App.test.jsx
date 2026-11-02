import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "./App.jsx";

describe("App", () => {
  it("renders title and search input", () => {
    render(<App />);
    expect(screen.getByText(/wine price search/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/search for a wine/i)).toBeInTheDocument();
  });
});
