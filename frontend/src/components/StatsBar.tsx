import { useEffect, useState } from "react";
import { fetchStats } from "../api/client";
import type { Stats } from "../types";

export default function StatsBar() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchStats()
      .then((data) => {
        if (!cancelled) setStats(data);
      })
      .catch(() => {
        // Le bandeau est purement décoratif : on le masque en cas d'erreur
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!stats) return null;

  const topDepartment = Object.entries(stats.by_department).sort((a, b) => b[1] - a[1])[0];

  const tiles = [
    { value: stats.total_upcoming_events, label: "événements à venir" },
    { value: stats.total_museums, label: "musées référencés" },
    ...(topDepartment
      ? [{ value: topDepartment[0], label: "département le plus actif" }]
      : []),
  ];

  return (
    <div
      data-testid="stats-bar"
      className="mb-8 grid grid-cols-1 sm:grid-cols-3 gap-3 text-center"
    >
      {tiles.map((tile) => (
        <div
          key={tile.label}
          className="rounded-xl border border-ink/10 dark:border-cream/10 bg-white dark:bg-ink/60 px-4 py-3"
        >
          <div className="font-display text-2xl font-bold text-ocre-dark dark:text-ocre">
            {tile.value}
          </div>
          <div className="text-xs text-ink/60 dark:text-cream/60">{tile.label}</div>
        </div>
      ))}
    </div>
  );
}
