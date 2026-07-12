import type { EventListResponse } from "../types";
import EventCard from "./EventCard";

interface EventListProps {
  data: EventListResponse | null;
  loading: boolean;
  error: string | null;
  page: number;
  onPageChange: (page: number) => void;
}

export default function EventList({ data, loading, error, page, onPageChange }: EventListProps) {
  if (loading) {
    return <p className="py-12 text-center text-ink/50 dark:text-cream/50">Chargement…</p>;
  }
  if (error) {
    return (
      <p className="py-12 text-center text-red-600" role="alert">
        Impossible de charger les événements ({error}).
      </p>
    );
  }
  if (!data || data.events.length === 0) {
    return (
      <p className="py-12 text-center text-ink/50 dark:text-cream/50">
        Aucun événement ne correspond à vos critères.
      </p>
    );
  }

  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));

  return (
    <div>
      <p className="mb-4 text-sm text-ink/60 dark:text-cream/60">
        {data.total} événement{data.total > 1 ? "s" : ""}
      </p>
      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
        {data.events.map((event) => (
          <EventCard key={`${event.source}-${event.id}`} event={event} />
        ))}
      </div>
      {totalPages > 1 && (
        <nav className="mt-8 flex items-center justify-center gap-4" aria-label="Pagination">
          <button
            type="button"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="rounded-lg border border-ink/20 dark:border-cream/20 px-4 py-2 text-sm disabled:opacity-40"
          >
            ← Précédent
          </button>
          <span className="text-sm">
            Page {page} / {totalPages}
          </span>
          <button
            type="button"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="rounded-lg border border-ink/20 dark:border-cream/20 px-4 py-2 text-sm disabled:opacity-40"
          >
            Suivant →
          </button>
        </nav>
      )}
    </div>
  );
}
