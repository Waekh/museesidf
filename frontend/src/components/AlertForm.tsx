import { FormEvent, useState } from "react";
import { createAlert } from "../api/client";
import { EVENT_TYPES, IDF_DEPARTMENTS } from "../types";

function toggle(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

export default function AlertForm() {
  const [email, setEmail] = useState("");
  const [departments, setDepartments] = useState<string[]>([]);
  const [types, setTypes] = useState<string[]>([]);
  const [keywords, setKeywords] = useState("");
  const [frequency, setFrequency] = useState<"daily" | "weekly">("weekly");
  const [status, setStatus] = useState<"idle" | "sending" | "success" | "error">("idle");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setStatus("sending");
    try {
      await createAlert({
        email,
        frequency,
        filters: {
          departments,
          types,
          keywords: keywords
            .split(",")
            .map((k) => k.trim())
            .filter(Boolean),
          audience: null,
        },
      });
      setStatus("success");
    } catch {
      setStatus("error");
    }
  }

  if (status === "success") {
    return (
      <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-6 text-center">
        <h2 className="font-display text-xl font-bold">Alerte enregistrée !</h2>
        <p className="mt-2 text-sm">
          Un email de confirmation avec un lien de désinscription vient de vous être envoyé.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <label className="block">
        <span className="font-display font-bold">Votre email</span>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="vous@exemple.fr"
          className="mt-2 w-full rounded-lg border border-ink/20 dark:border-cream/20 bg-transparent px-3 py-2"
        />
      </label>

      <fieldset>
        <legend className="mb-2 font-display font-bold">Départements (optionnel)</legend>
        <div className="grid grid-cols-2 gap-1.5">
          {IDF_DEPARTMENTS.map((department) => (
            <label key={department} className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                className="accent-ocre"
                checked={departments.includes(department)}
                onChange={() => setDepartments(toggle(departments, department))}
              />
              {department}
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset>
        <legend className="mb-2 font-display font-bold">Types d'événements (optionnel)</legend>
        <div className="grid grid-cols-2 gap-1.5">
          {EVENT_TYPES.map((eventType) => (
            <label key={eventType} className="flex items-center gap-2 text-sm capitalize cursor-pointer">
              <input
                type="checkbox"
                className="accent-ocre"
                checked={types.includes(eventType)}
                onChange={() => setTypes(toggle(types, eventType))}
              />
              {eventType}
            </label>
          ))}
        </div>
      </fieldset>

      <label className="block">
        <span className="font-display font-bold">Mots-clés (optionnel)</span>
        <input
          type="text"
          value={keywords}
          onChange={(e) => setKeywords(e.target.value)}
          placeholder="impressionnisme, photographie…"
          className="mt-2 w-full rounded-lg border border-ink/20 dark:border-cream/20 bg-transparent px-3 py-2"
        />
        <span className="text-xs text-ink/50 dark:text-cream/50">Séparés par des virgules</span>
      </label>

      <fieldset>
        <legend className="mb-2 font-display font-bold">Fréquence</legend>
        <div className="flex gap-4">
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="radio"
              name="frequency"
              className="accent-ocre"
              checked={frequency === "daily"}
              onChange={() => setFrequency("daily")}
            />
            Quotidienne
          </label>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="radio"
              name="frequency"
              className="accent-ocre"
              checked={frequency === "weekly"}
              onChange={() => setFrequency("weekly")}
            />
            Hebdomadaire
          </label>
        </div>
      </fieldset>

      {status === "error" && (
        <p className="text-sm text-red-600" role="alert">
          Une erreur est survenue, merci de réessayer.
        </p>
      )}

      <button
        type="submit"
        disabled={status === "sending"}
        className="w-full rounded-lg bg-ocre px-4 py-2.5 font-medium text-white hover:bg-ocre-dark disabled:opacity-50"
      >
        {status === "sending" ? "Enregistrement…" : "Créer mon alerte"}
      </button>

      <p className="text-xs text-ink/50 dark:text-cream/50">
        Conformément au RGPD, votre email n'est utilisé que pour l'envoi des alertes. Chaque
        email contient un lien de désinscription ; les abonnements inactifs sont supprimés
        après un an.
      </p>
    </form>
  );
}
