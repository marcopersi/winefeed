import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "./App.jsx";

describe("App", () => {
  it("renders title", () => {
    render(<App />);
    expect(screen.getByText(/price service ui/i)).toBeInTheDocument();
  });
});
