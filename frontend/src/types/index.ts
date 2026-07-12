export interface MuseumLite {
  id: number;
  name: string;
  slug: string | null;
  city: string | null;
  department: string | null;
  latitude: number | null;
  longitude: number | null;
  website_url: string | null;
  logo_url: string | null;
}

export interface Museum extends MuseumLite {
  address: string | null;
  postal_code: string | null;
  upcoming_events_count: number;
}

export interface Event {
  id: number;
  museum_id: number | null;
  source: string;
  title: string;
  description: string | null;
  event_type: string | null;
  date_start: string;
  date_end: string | null;
  time_start: string | null;
  time_end: string | null;
  is_permanent: boolean;
  price_info: string | null;
  image_url: string | null;
  event_url: string | null;
  audience: string | null;
  museum: MuseumLite | null;
}

export interface EventListResponse {
  total: number;
  page: number;
  page_size: number;
  events: Event[];
}

export interface Stats {
  total_museums: number;
  total_upcoming_events: number;
  by_department: Record<string, number>;
  by_event_type: Record<string, number>;
}

export interface EventFilters {
  keyword: string;
  departments: string[];
  eventTypes: string[];
  audience: string;
  dateFrom: string;
  dateTo: string;
  museumId: number | null;
}

export const EMPTY_FILTERS: EventFilters = {
  keyword: "",
  departments: [],
  eventTypes: [],
  audience: "",
  dateFrom: "",
  dateTo: "",
  museumId: null,
};

export const IDF_DEPARTMENTS = [
  "Paris",
  "Seine-et-Marne",
  "Yvelines",
  "Essonne",
  "Hauts-de-Seine",
  "Seine-Saint-Denis",
  "Val-de-Marne",
  "Val-d'Oise",
] as const;

export const EVENT_TYPES = [
  "exposition",
  "conférence",
  "atelier",
  "visite",
  "nocturne",
  "concert",
  "spectacle",
  "autre",
] as const;

export const AUDIENCES = ["tout public", "enfants", "adultes", "scolaires"] as const;
