import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { EMPTY_FILTERS } from "../types";
import { useEvents } from "./useEvents";

const SAMPLE_RESPONSE = {
  total: 1,
  page: 1,
  page_size: 20,
  events: [
    {
      id: 1,
      museum_id: null,
      source: "openagenda",
      title: "Monet en lumière",
      description: null,
      event_type: "exposition",
      date_start: "2026-09-01",
      date_end: null,
      time_start: null,
      time_end: null,
      is_permanent: false,
      price_info: null,
      image_url: null,
      event_url: null,
      audience: null,
      museum: null,
    },
  ],
};

function mockFetch(body: unknown, ok = true, status = 200) {
  return vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok,
    status,
    json: () => Promise.resolve(body),
  } as Response);
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useEvents", () => {
  it("charge les événements et expose data", async () => {
    const fetchMock = mockFetch(SAMPLE_RESPONSE);

    const { result } = renderHook(() => useEvents(EMPTY_FILTERS, 1));

    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.error).toBeNull();
    expect(result.current.data?.total).toBe(1);
    expect(result.current.data?.events[0].title).toBe("Monet en lumière");

    const calledUrl = String(fetchMock.mock.calls[0][0]);
    expect(calledUrl).toContain("/api/events");
    expect(calledUrl).toContain("page=1");
  });

  it("sérialise les filtres dans l'URL", async () => {
    const fetchMock = mockFetch(SAMPLE_RESPONSE);

    renderHook(() =>
      useEvents(
        {
          ...EMPTY_FILTERS,
          keyword: "monet",
          departments: ["Paris", "Hauts-de-Seine"],
          eventTypes: ["exposition"],
        },
        2,
      ),
    );

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const calledUrl = decodeURIComponent(String(fetchMock.mock.calls[0][0]));
    expect(calledUrl).toContain("keyword=monet");
    expect(calledUrl).toContain("department=Paris,Hauts-de-Seine");
    expect(calledUrl).toContain("event_type=exposition");
    expect(calledUrl).toContain("page=2");
  });

  it("expose une erreur quand l'API échoue", async () => {
    mockFetch({}, false, 500);

    const { result } = renderHook(() => useEvents(EMPTY_FILTERS, 1));
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.error).toContain("500");
    expect(result.current.data).toBeNull();
  });
});
