import { useEffect, useState } from "react";
import type { EventFilters, Museum } from "../types";
import { AUDIENCES, EVENT_TYPES, IDF_DEPARTMENTS } from "../types";

interface FilterPanelProps {
  filters: EventFilters;
  onChange: (filters: EventFilters) => void;
  onReset: () => void;
  museums: Museum[];
}

function toggle(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

export default function FilterPanel({ filters, onChange, onReset, museums }: FilterPanelProps) {
  const [open, setOpen] = useState(false);

  // La période est saisie en local puis appliquée au clic sur « Valider »
  // (les cases à cocher, elles, s'appliquent immédiatement).
  const [draftFrom, setDraftFrom] = useState(filters.dateFrom);
  const [draftTo, setDraftTo] = useState(filters.dateTo);

  useEffect(() => {
    setDraftFrom(filters.dateFrom);
    setDraftTo(filters.dateTo);
  }, [filters.dateFrom, filters.dateTo]);

  const dateChanged = draftFrom !== filters.dateFrom || draftTo !== filters.dateTo;

  function applyDates() {
    onChange({ ...filters, dateFrom: draftFrom, dateTo: draftTo });
  }

  return (
    <aside className="md:w-64 shrink-0">
      <button
        type="button"
        className="md:hidden mb-3 w-full rounded-lg border border-ink/20 dark:border-cream/20 px-4 py-2 text-sm font-medium"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        {open ? "Masquer les filtres" : "Afficher les filtres"}
      </button>

      <div className={`${open ? "block" : "hidden"} md:block space-y-6`}>
        <fieldset>
          <legend className="mb-2 font-display font-bold">Département</legend>
          <div className="space-y-1.5">
            {IDF_DEPARTMENTS.map((department) => (
              <label key={department} className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  className="accent-ocre"
                  checked={filters.departments.includes(department)}
                  onChange={() =>
                    onChange({ ...filters, departments: toggle(filters.departments, department) })
                  }
                />
                {department}
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend className="mb-2 font-display font-bold">Type d'événement</legend>
          <div className="space-y-1.5">
            {EVENT_TYPES.map((eventType) => (
              <label key={eventType} className="flex items-center gap-2 text-sm cursor-pointer capitalize">
                <input
                  type="checkbox"
                  className="accent-ocre"
                  checked={filters.eventTypes.includes(eventType)}
                  onChange={() =>
                    onChange({ ...filters, eventTypes: toggle(filters.eventTypes, eventType) })
                  }
                />
                {eventType}
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend className="mb-2 font-display font-bold">Période</legend>
          <div className="space-y-2">
            <label className="block text-sm">
              Du
              <input
                type="date"
                aria-label="Date de début"
                value={draftFrom}
                max={draftTo || undefined}
                onChange={(e) => setDraftFrom(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && applyDates()}
                className="mt-1 w-full rounded-lg border border-ink/20 dark:border-cream/20 bg-transparent px-2 py-1.5 text-sm"
              />
            </label>
            <label className="block text-sm">
              Au
              <input
                type="date"
                aria-label="Date de fin"
                value={draftTo}
                min={draftFrom || undefined}
                onChange={(e) => setDraftTo(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && applyDates()}
                className="mt-1 w-full rounded-lg border border-ink/20 dark:border-cream/20 bg-transparent px-2 py-1.5 text-sm"
              />
            </label>
            <button
              type="button"
              onClick={applyDates}
              disabled={!dateChanged}
              className="w-full rounded-lg bg-ocre px-3 py-1.5 text-sm font-medium text-white hover:bg-ocre-dark disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Valider la période
            </button>
          </div>
        </fieldset>

        <fieldset>
          <legend className="mb-2 font-display font-bold">Public</legend>
          <select
            aria-label="Public"
            value={filters.audience}
            onChange={(e) => onChange({ ...filters, audience: e.target.value })}
            className="w-full rounded-lg border border-ink/20 dark:border-cream/20 bg-transparent px-2 py-1.5 text-sm"
          >
            <option value="">Tous</option>
            {AUDIENCES.map((audience) => (
              <option key={audience} value={audience}>
                {audience}
              </option>
            ))}
          </select>
        </fieldset>

        <fieldset>
          <legend className="mb-2 font-display font-bold">Musée</legend>
          <select
            aria-label="Musée"
            value={filters.museumId ?? ""}
            onChange={(e) =>
              onChange({
                ...filters,
                museumId: e.target.value ? Number(e.target.value) : null,
              })
            }
            className="w-full rounded-lg border border-ink/20 dark:border-cream/20 bg-transparent px-2 py-1.5 text-sm"
          >
            <option value="">Tous les musées</option>
            {museums.map((museum) => (
              <option key={museum.id} value={museum.id}>
                {museum.name}
              </option>
            ))}
          </select>
        </fieldset>

        <button
          type="button"
          onClick={onReset}
          className="w-full rounded-lg border border-ocre px-4 py-2 text-sm font-medium text-ocre-dark dark:text-ocre hover:bg-ocre/10"
        >
          Réinitialiser les filtres
        </button>
      </div>
    </aside>
  );
}
