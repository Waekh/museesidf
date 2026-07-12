import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { EMPTY_FILTERS } from "../types";
import FilterPanel from "./FilterPanel";

describe("FilterPanel", () => {
  it("applique un filtre de département via checkbox", async () => {
    const onChange = vi.fn();
    render(
      <FilterPanel filters={EMPTY_FILTERS} onChange={onChange} onReset={vi.fn()} museums={[]} />,
    );

    await userEvent.click(screen.getByRole("checkbox", { name: "Paris" }));

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ departments: ["Paris"] }),
    );
  });

  it("décoche un département déjà actif", async () => {
    const onChange = vi.fn();
    render(
      <FilterPanel
        filters={{ ...EMPTY_FILTERS, departments: ["Paris", "Yvelines"] }}
        onChange={onChange}
        onReset={vi.fn()}
        museums={[]}
      />,
    );

    await userEvent.click(screen.getByRole("checkbox", { name: "Paris" }));

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ departments: ["Yvelines"] }),
    );
  });

  it("applique un filtre de type d'événement", async () => {
    const onChange = vi.fn();
    render(
      <FilterPanel filters={EMPTY_FILTERS} onChange={onChange} onReset={vi.fn()} museums={[]} />,
    );

    await userEvent.click(screen.getByRole("checkbox", { name: "exposition" }));

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ eventTypes: ["exposition"] }),
    );
  });

  it("applique une période via les date pickers", async () => {
    const onChange = vi.fn();
    render(
      <FilterPanel filters={EMPTY_FILTERS} onChange={onChange} onReset={vi.fn()} museums={[]} />,
    );

    const dateFrom = screen.getByLabelText("Date de début");
    await userEvent.type(dateFrom, "2026-09-01");

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ dateFrom: "2026-09-01" }),
    );
  });

  it("déclenche le reset", async () => {
    const onReset = vi.fn();
    render(
      <FilterPanel filters={EMPTY_FILTERS} onChange={vi.fn()} onReset={onReset} museums={[]} />,
    );

    await userEvent.click(screen.getByRole("button", { name: /Réinitialiser/ }));

    expect(onReset).toHaveBeenCalledOnce();
  });

  it("liste les musées dans le select", () => {
    render(
      <FilterPanel
        filters={EMPTY_FILTERS}
        onChange={vi.fn()}
        onReset={vi.fn()}
        museums={[
          {
            id: 1,
            name: "Musée d'Orsay",
            slug: "musee-d-orsay",
            city: "Paris",
            department: "Paris",
            latitude: null,
            longitude: null,
            website_url: null,
            logo_url: null,
            address: null,
            postal_code: null,
            upcoming_events_count: 3,
          },
        ]}
      />,
    );

    expect(screen.getByRole("option", { name: "Musée d'Orsay" })).toBeInTheDocument();
  });
});
