import { vi, describe, it, expect, beforeEach } from "vitest";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import ChatPanel from "./ChatPanel";
import { renderWithProviders } from "../test/test-utils";
import { sendChatMessage } from "../api/client";

vi.mock("../api/client", () => ({
  sendChatMessage: vi.fn(),
}));

describe("ChatPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the chat panel with the initial greeting", () => {
    renderWithProviders(<ChatPanel />);
    expect(screen.getByText(/Log interaction details here/i)).toBeInTheDocument();
  });

  it("sends a message and renders the reply on success", async () => {
    const mockReply = {
      reply: "I have updated the form with Dr. Sharma.",
      tool_calls: ["log_interaction"],
      updated_state: {
        id: "123",
        hcp_name: "Dr. Sharma",
        interaction_type: "Meeting",
        date: "2026-07-28",
        time: "10:00 AM",
        attendees: "Dr. Sharma",
        topics_discussed: "Product X efficacy",
        materials_shared: [],
        samples_distributed: [],
        sentiment: "Positive" as const,
        outcomes: "",
        follow_up_actions: "",
        ai_suggested_followups: [],
      },
    };

    vi.mocked(sendChatMessage).mockResolvedValue(mockReply);

    const { store } = renderWithProviders(<ChatPanel />);

    const input = screen.getByPlaceholderText(/Describe interaction.../i);
    const sendButton = screen.getByRole("button", { name: /Log/i });

    fireEvent.change(input, { target: { value: "Met Dr. Sharma today" } });
    fireEvent.click(sendButton);

    // Should show user message in feed immediately
    expect(screen.getByText("Met Dr. Sharma today")).toBeInTheDocument();

    // Should show thinking/loading state
    expect(screen.getByTestId("loading-indicator")).toBeInTheDocument();

    // Wait for the async API response
    await waitFor(() => {
      expect(screen.getByText("I have updated the form with Dr. Sharma.")).toBeInTheDocument();
    });

    // Check that tool calls information is displayed
    expect(screen.getByText(/tool used: log_interaction/i)).toBeInTheDocument();

    // Store state should be updated
    expect(store.getState().interaction.hcp_name).toBe("Dr. Sharma");
  });

  it("handles errors and shows failure feedback", async () => {
    vi.mocked(sendChatMessage).mockRejectedValue(new Error("API is offline"));

    renderWithProviders(<ChatPanel />);

    const input = screen.getByPlaceholderText(/Describe interaction.../i);
    const sendButton = screen.getByRole("button", { name: /Log/i });

    fireEvent.change(input, { target: { value: "Hello" } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(screen.getByText(/Sorry, something went wrong: API is offline/i)).toBeInTheDocument();
    });
  });
});
