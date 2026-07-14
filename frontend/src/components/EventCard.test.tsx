import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import type { Event } from "../types";
import EventCard from "./EventCard";

const FULL_EVENT: Event = {
  id: 1,
  museum_id: 10,
  source: "openagenda",
  title: "Monet en lumière",
  description: "Une grande rétrospective.",
  event_type: "exposition",
  date_start: "2026-09-01",
  date_end: "2026-09-30",
  time_start: "10:00:00",
  time_end: "18:00:00",
  is_permanent: false,
  price_info: "12€",
  image_url: "https://example.com/img.jpg",
  event_url: "https://musee.example.com/monet",
  audience: "tout public",
  museum: {
    id: 10,
    name: "Musée d'Orsay",
    slug: "musee-d-orsay",
    city: "Paris",
    department: "Paris",
    latitude: 48.86,
    longitude: 2.32,
    website_url: "https://www.musee-orsay.fr",
    logo_url: null,
  },
};

const MINIMAL_EVENT: Event = {
  id: 2,
  museum_id: null,
  source: "paris_opendata",
  title: "Atelier mystère",
  description: null,
  event_type: null,
  date_start: "2026-10-05",
  date_end: null,
  time_start: null,
  time_end: null,
  is_permanent: false,
  price_info: null,
  image_url: null,
  event_url: null,
  audience: null,
  museum: null,
};

function renderCard(event: Event) {
  return render(
    <MemoryRouter>
      <EventCard event={event} />
    </MemoryRouter>,
  );
}

describe("EventCard", () => {
  it("affiche toutes les informations avec des données complètes", () => {
    renderCard(FULL_EVENT);

    expect(screen.getByText("Monet en lumière")).toBeInTheDocument();
    expect(screen.getByText("exposition")).toBeInTheDocument();
    expect(screen.getByText(/Musée d'Orsay/)).toBeInTheDocument();
    expect(screen.getByText("12€")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Monet en lumière" })).toHaveAttribute(
      "src",
      "https://example.com/img.jpg",
    );
    expect(screen.getByRole("link", { name: /En savoir plus/ })).toHaveAttribute(
      "href",
      "https://musee.example.com/monet",
    );
    expect(screen.getByText(/Du 1/)).toBeInTheDocument();
  });

  it("gère les données minimales avec des valeurs de repli", () => {
    renderCard(MINIMAL_EVENT);

    expect(screen.getByText("Atelier mystère")).toBeInTheDocument();
    expect(screen.getByText("autre")).toBeInTheDocument();
    expect(screen.getByText("Tarif non communiqué")).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /En savoir plus/ })).not.toBeInTheDocument();
  });

  it("l'image renvoie vers la page de détail de l'événement", () => {
    renderCard(FULL_EVENT);

    const imageLink = screen.getByRole("link", { name: "Voir l'événement Monet en lumière" });
    expect(imageLink).toHaveAttribute("href", "/evenements/1");
    expect(imageLink.querySelector("img")).toHaveAttribute("src", "https://example.com/img.jpg");
  });

  it("affiche l'icône de repli si l'image échoue au chargement", () => {
    renderCard(FULL_EVENT);

    const img = screen.getByRole("img", { name: "Monet en lumière" });
    fireEvent.error(img);

    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByText("❦")).toBeInTheDocument();
  });
});
