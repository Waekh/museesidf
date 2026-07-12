import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import FilterPanel from "../components/FilterPanel";
import EventList from "../components/EventList";
import MapView from "../components/MapView";
import { useEvents } from "../hooks/useEvents";
import { useMuseums } from "../hooks/useMuseums";
import { EMPTY_FILTERS, type EventFilters } from "../types";

export default function Home() {
  const [searchParams] = useSearchParams();
  const initialMuseum = searchParams.get("museum");

  const [filters, setFilters] = useState<EventFilters>({
    ...EMPTY_FILTERS,
    museumId: initialMuseum ? Number(initialMuseum) : null,
  });
  const [searchInput, setSearchInput] = useState("");
  const [page, setPage] = useState(1);
  const [view, setView] = useState<"list" | "map">("list");

  const { museums } = useMuseums();
  const { data, loading, error } = useEvents(filters, page);

  // Recherche plein texte avec léger debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      setFilters((current) =>
        current.keyword === searchInput ? current : { ...current, keyword: searchInput },
      );
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  function handleFiltersChange(next: EventFilters) {
    setFilters(next);
    setPage(1);
  }

  function handleReset() {
    setFilters(EMPTY_FILTERS);
    setSearchInput("");
    setPage(1);
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-8 text-center">
        <h1 className="font-display text-3xl md:text-4xl font-bold">
          Tous les événements des musées d'Île-de-France
        </h1>
        <p className="mt-2 text-ink/60 dark:text-cream/60">
          Expositions, ateliers, nocturnes, visites guidées… agrégés chaque jour.
        </p>
      </div>

      <div className="mb-6 flex flex-col sm:flex-row gap-3">
        <input
          type="search"
          role="searchbox"
          placeholder="Rechercher une exposition, un artiste, un musée…"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="flex-1 rounded-xl border border-ink/20 dark:border-cream/20 bg-white dark:bg-ink/60 px-4 py-3 shadow-sm focus:outline-none focus:ring-2 focus:ring-ocre"
        />
        <div className="flex rounded-xl border border-ink/20 dark:border-cream/20 overflow-hidden self-start">
          <button
            type="button"
            onClick={() => setView("list")}
            className={`px-4 py-3 text-sm font-medium ${view === "list" ? "bg-ocre text-white" : ""}`}
            aria-pressed={view === "list"}
          >
            Liste
          </button>
          <button
            type="button"
            onClick={() => setView("map")}
            className={`px-4 py-3 text-sm font-medium ${view === "map" ? "bg-ocre text-white" : ""}`}
            aria-pressed={view === "map"}
          >
            Carte
          </button>
        </div>
      </div>

      <div className="flex flex-col md:flex-row gap-8">
        <FilterPanel
          filters={filters}
          onChange={handleFiltersChange}
          onReset={handleReset}
          museums={museums}
        />
        <main className="flex-1 min-w-0">
          {view === "list" ? (
            <EventList
              data={data}
              loading={loading}
              error={error}
              page={page}
              onPageChange={setPage}
            />
          ) : (
            <MapView
              museums={museums}
              onSelectMuseum={(museumId) => {
                handleFiltersChange({ ...filters, museumId });
                setView("list");
              }}
            />
          )}
        </main>
      </div>
    </div>
  );
}
