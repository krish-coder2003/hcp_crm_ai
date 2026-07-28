import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import InteractionForm from "./InteractionForm";
import { renderWithProviders } from "../test/test-utils";

describe("InteractionForm", () => {
  it("renders with placeholders when state is empty", () => {
    renderWithProviders(<InteractionForm />);
    expect(screen.getByText("Search or select HCP…")).toBeInTheDocument();
    expect(screen.getAllByText("No items added")).toHaveLength(2);
  });

  it("renders interaction details when state is populated", () => {
    const preloadedState = {
      interaction: {
        id: "1",
        hcp_name: "Dr. John Doe",
        interaction_type: "Meeting",
        date: "2026-07-28",
        time: "14:00",
        attendees: "Dr. John Doe, Representative",
        topics_discussed: "Discussion about new oncology treatment.",
        materials_shared: ["Brochure A", "Brochure B"],
        samples_distributed: ["Sample X"],
        sentiment: "Positive" as const,
        outcomes: "Agreed to follow up next month.",
        follow_up_actions: "Send clinical study PDF.",
        ai_suggested_followups: ["Email clinical study", "Schedule next meeting"],
      },
    };

    renderWithProviders(<InteractionForm />, { preloadedState });

    // Assert values are displayed
    expect(screen.getByText("Dr. John Doe")).toBeInTheDocument();
    expect(screen.getByText("2026-07-28")).toBeInTheDocument();
    expect(screen.getByText("14:00")).toBeInTheDocument();
    expect(screen.getByText("Dr. John Doe, Representative")).toBeInTheDocument();
    expect(screen.getByText("Discussion about new oncology treatment.")).toBeInTheDocument();
    expect(screen.getByText("Brochure A")).toBeInTheDocument();
    expect(screen.getByText("Brochure B")).toBeInTheDocument();
    expect(screen.getByText("Sample X")).toBeInTheDocument();
    expect(screen.getByText("Agreed to follow up next month.")).toBeInTheDocument();
    expect(screen.getByText("Send clinical study PDF.")).toBeInTheDocument();

    // Check sentiment pill has active class
    const sentimentPill = screen.getByText("Positive");
    expect(sentimentPill).toHaveClass("active--Positive");

    // Check suggestions list
    expect(screen.getByText("+ Email clinical study")).toBeInTheDocument();
    expect(screen.getByText("+ Schedule next meeting")).toBeInTheDocument();
  });
});
