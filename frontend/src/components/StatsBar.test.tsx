import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import StatsBar from "./StatsBar";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("StatsBar", () => {
  it("affiche les totaux et le département le plus actif", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({
          total_museums: 187,
          total_upcoming_events: 342,
          by_department: { Paris: 250, Yvelines: 40 },
          by_event_type: { exposition: 200 },
        }),
    } as Response);

    render(<StatsBar />);

    await waitFor(() => expect(screen.getByTestId("stats-bar")).toBeInTheDocument());
    expect(screen.getByText("342")).toBeInTheDocument();
    expect(screen.getByText("187")).toBeInTheDocument();
    expect(screen.getByText("Paris")).toBeInTheDocument();
  });

  it("ne rend rien si l'API échoue", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("réseau"));

    const { container } = render(<StatsBar />);

    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });
});
