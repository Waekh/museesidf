import { useEffect, useState } from "react";
import { fetchEvents } from "../api/client";
import type { EventFilters, EventListResponse } from "../types";

interface UseEventsResult {
  data: EventListResponse | null;
  loading: boolean;
  error: string | null;
}

export function useEvents(filters: EventFilters, page: number, pageSize = 20): UseEventsResult {
  const [data, setData] = useState<EventListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const filtersKey = JSON.stringify(filters);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchEvents(JSON.parse(filtersKey) as EventFilters, page, pageSize)
      .then((response) => {
        if (!cancelled) setData(response);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [filtersKey, page, pageSize]);

  return { data, loading, error };
}
