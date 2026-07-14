import { useEffect, useState } from "react";
import { fetchMuseums } from "../api/client";
import type { EventFilters, Museum } from "../types";

interface UseMuseumsResult {
  museums: Museum[];
  loading: boolean;
  error: string | null;
}

/**
 * Liste des musées. Sans filtres : la liste complète (pour le sélecteur).
 * Avec filtres : les musées ayant au moins un événement correspondant
 * (pour que la carte reflète les filtres actifs).
 */
export function useMuseums(filters?: EventFilters): UseMuseumsResult {
  const [museums, setMuseums] = useState<Museum[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const filtersKey = filters ? JSON.stringify(filters) : "";

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchMuseums(filtersKey ? (JSON.parse(filtersKey) as EventFilters) : undefined)
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
  }, [filtersKey]);

  return { museums, loading, error };
}
