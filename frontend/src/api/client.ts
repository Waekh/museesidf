import type { Event, EventFilters, EventListResponse, Museum, Stats } from "../types";

export const API_URL: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function getJson<T>(path: string, params?: URLSearchParams): Promise<T> {
  const query = params && params.size > 0 ? `?${params.toString()}` : "";
  const response = await fetch(`${API_URL}${path}${query}`);
  if (!response.ok) {
    throw new Error(`Erreur API ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function buildEventParams(
  filters: EventFilters,
  page: number,
  pageSize = 20,
): URLSearchParams {
  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("page_size", String(pageSize));
  if (filters.keyword) params.set("keyword", filters.keyword);
  if (filters.departments.length > 0) params.set("department", filters.departments.join(","));
  if (filters.eventTypes.length > 0) params.set("event_type", filters.eventTypes.join(","));
  if (filters.audience) params.set("audience", filters.audience);
  if (filters.dateFrom) params.set("date_from", filters.dateFrom);
  if (filters.dateTo) params.set("date_to", filters.dateTo);
  if (filters.museumId !== null) params.set("museum_id", String(filters.museumId));
  return params;
}

export function fetchEvents(
  filters: EventFilters,
  page: number,
  pageSize = 20,
): Promise<EventListResponse> {
  return getJson<EventListResponse>("/api/events", buildEventParams(filters, page, pageSize));
}

export function fetchEvent(id: number): Promise<Event> {
  return getJson<Event>(`/api/events/${id}`);
}

export function fetchMuseums(options?: { department?: string; hasUpcomingEvents?: boolean }): Promise<Museum[]> {
  const params = new URLSearchParams();
  if (options?.department) params.set("department", options.department);
  if (options?.hasUpcomingEvents) params.set("has_upcoming_events", "true");
  return getJson<Museum[]>("/api/museums", params);
}

export function fetchStats(): Promise<Stats> {
  return getJson<Stats>("/api/stats");
}

export async function createAlert(payload: {
  email: string;
  filters: {
    departments: string[];
    types: string[];
    keywords: string[];
    audience: string | null;
  };
  frequency: "daily" | "weekly";
}): Promise<void> {
  const response = await fetch(`${API_URL}/api/alerts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Erreur API ${response.status}`);
  }
}
