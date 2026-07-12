import { Link } from "react-router-dom";
import type { Event } from "../types";

const TYPE_COLORS: Record<string, string> = {
  exposition: "bg-ocre/15 text-ocre-dark",
  conférence: "bg-blue-500/15 text-blue-700 dark:text-blue-300",
  atelier: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  visite: "bg-violet-500/15 text-violet-700 dark:text-violet-300",
  nocturne: "bg-indigo-500/15 text-indigo-700 dark:text-indigo-300",
  concert: "bg-rose-500/15 text-rose-700 dark:text-rose-300",
  spectacle: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
  autre: "bg-ink/10 text-ink/70 dark:bg-cream/10 dark:text-cream/70",
};

export function formatDateRange(dateStart: string, dateEnd: string | null): string {
  const options: Intl.DateTimeFormatOptions = { day: "numeric", month: "short", year: "numeric" };
  const start = new Date(dateStart).toLocaleDateString("fr-FR", options);
  if (!dateEnd || dateEnd === dateStart) return start;
  const end = new Date(dateEnd).toLocaleDateString("fr-FR", options);
  return `Du ${start} au ${end}`;
}

interface EventCardProps {
  event: Event;
}

export default function EventCard({ event }: EventCardProps) {
  const badgeClass = TYPE_COLORS[event.event_type ?? "autre"] ?? TYPE_COLORS.autre;
  const imageUrl = event.image_url ?? event.museum?.logo_url ?? null;

  return (
    <article
      data-testid="event-card"
      className="group flex flex-col overflow-hidden rounded-xl border border-ink/10 dark:border-cream/10 bg-white dark:bg-ink/60 shadow-sm hover:shadow-md transition-shadow"
    >
      <div className="h-40 bg-ink/5 dark:bg-cream/5 overflow-hidden">
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={event.title}
            loading="lazy"
            className="h-full w-full object-cover group-hover:scale-[1.02] transition-transform"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        ) : (
          <div
            className="h-full w-full flex items-center justify-center font-display text-4xl text-ocre/40"
            aria-hidden="true"
          >
            ❦
          </div>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-2 p-4">
        <div className="flex items-center gap-2">
          <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${badgeClass}`}>
            {event.event_type ?? "autre"}
          </span>
          {event.audience && event.audience !== "tout public" && (
            <span className="text-xs text-ink/50 dark:text-cream/50">{event.audience}</span>
          )}
        </div>

        <h3 className="font-display text-lg font-bold leading-snug">
          <Link to={`/evenements/${event.id}`} className="hover:text-ocre transition-colors">
            {event.title}
          </Link>
        </h3>

        {event.museum && (
          <p className="text-sm text-ink/60 dark:text-cream/60">
            {event.museum.name}
            {event.museum.city ? ` — ${event.museum.city}` : ""}
          </p>
        )}

        <p className="text-sm">{formatDateRange(event.date_start, event.date_end)}</p>

        <div className="mt-auto flex items-center justify-between pt-2">
          <span className="text-sm font-medium text-ocre-dark dark:text-ocre">
            {event.price_info ?? "Tarif non communiqué"}
          </span>
          {event.event_url && (
            <a
              href={event.event_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-medium text-ink/70 dark:text-cream/70 hover:text-ocre"
            >
              En savoir plus →
            </a>
          )}
        </div>
      </div>
    </article>
  );
}
