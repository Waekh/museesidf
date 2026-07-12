import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchEvent } from "../api/client";
import { formatDateRange } from "../components/EventCard";
import type { Event } from "../types";

export default function EventDetail() {
  const { id } = useParams<{ id: string }>();
  const [event, setEvent] = useState<Event | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    fetchEvent(Number(id))
      .then(setEvent)
      .catch((err: Error) => setError(err.message));
  }, [id]);

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center">
        <p className="text-red-600">Événement introuvable.</p>
        <Link to="/" className="mt-4 inline-block text-ocre underline">
          ← Retour à la liste
        </Link>
      </div>
    );
  }

  if (!event) {
    return <p className="py-16 text-center text-ink/50 dark:text-cream/50">Chargement…</p>;
  }

  return (
    <article className="mx-auto max-w-3xl px-4 py-8">
      <Link to="/" className="text-sm text-ink/60 dark:text-cream/60 hover:text-ocre">
        ← Retour à la liste
      </Link>

      {event.image_url && (
        <img
          src={event.image_url}
          alt={event.title}
          className="mt-4 max-h-96 w-full rounded-xl object-cover"
        />
      )}

      <div className="mt-6 flex items-center gap-3">
        <span className="rounded-full bg-ocre/15 px-3 py-1 text-sm font-medium text-ocre-dark dark:text-ocre">
          {event.event_type ?? "autre"}
        </span>
        {event.audience && <span className="text-sm">{event.audience}</span>}
      </div>

      <h1 className="mt-3 font-display text-3xl font-bold">{event.title}</h1>

      <dl className="mt-6 grid gap-4 sm:grid-cols-2 text-sm">
        {event.museum && (
          <div>
            <dt className="font-bold">Lieu</dt>
            <dd>
              {event.museum.name}
              {event.museum.city ? `, ${event.museum.city}` : ""}
            </dd>
          </div>
        )}
        <div>
          <dt className="font-bold">Dates</dt>
          <dd>{formatDateRange(event.date_start, event.date_end)}</dd>
        </div>
        {event.time_start && (
          <div>
            <dt className="font-bold">Horaires</dt>
            <dd>
              {event.time_start.slice(0, 5)}
              {event.time_end ? ` – ${event.time_end.slice(0, 5)}` : ""}
            </dd>
          </div>
        )}
        <div>
          <dt className="font-bold">Tarif</dt>
          <dd>{event.price_info ?? "Non communiqué"}</dd>
        </div>
      </dl>

      {event.description && (
        <div className="prose mt-8 max-w-none whitespace-pre-line text-ink/80 dark:text-cream/80">
          {event.description}
        </div>
      )}

      {event.event_url && (
        <a
          href={event.event_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-8 inline-block rounded-lg bg-ocre px-5 py-2.5 font-medium text-white hover:bg-ocre-dark"
        >
          En savoir plus sur le site officiel →
        </a>
      )}
    </article>
  );
}
