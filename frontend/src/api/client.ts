const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

import { InteractionState } from "../store/interactionSlice";

export interface ChatResponse {
  reply: string;
  tool_calls: string[];
  updated_state: InteractionState;
}

export async function sendChatMessage(
  message: string,
  currentState: InteractionState,
  threadId: string
): Promise<ChatResponse> {
  const res = await fetch(`${BASE_URL}/api/v1/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      current_state: currentState,
      thread_id: threadId,
    }),
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Request failed with status ${res.status}`);
  }

  return res.json() as Promise<ChatResponse>;
}
