import { useEffect, useState } from "react";
import { fetchMuseums } from "../api/client";
import type { Museum } from "../types";

interface UseMuseumsResult {
  museums: Museum[];
  loading: boolean;
  error: string | null;
}

export function useMuseums(): UseMuseumsResult {
  const [museums, setMuseums] = useState<Museum[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchMuseums()
      .then((data) => {
        if (!cancelled) setMuseums(data);
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
  }, []);

  return { museums, loading, error };
}
