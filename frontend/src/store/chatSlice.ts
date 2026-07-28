import { createSlice, nanoid, PayloadAction } from "@reduxjs/toolkit";

export interface Message {
  id: string;
  role: "assistant" | "user" | "error";
  text: string;
  toolCalls?: string[];
}

export interface ChatState {
  threadId: string;
  messages: Message[];
  isSending: boolean;
  error: string | null;
}

const initialState: ChatState = {
  threadId: `session-${nanoid(8)}`,
  messages: [
    {
      id: nanoid(),
      role: "assistant",
      text:
        'Log interaction details here (e.g. "Met Dr. Sharma, discussed Product X efficacy, ' +
        'positive sentiment, shared brochure") or ask for help.',
      toolCalls: [],
    },
  ],
  isSending: false,
  error: null,
};

const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    messageSent: (state, action: PayloadAction<string>) => {
      state.messages.push({ id: nanoid(), role: "user", text: action.payload, toolCalls: [] });
      state.isSending = true;
      state.error = null;
    },
    replyReceived: (state, action: PayloadAction<{ reply: string; toolCalls: string[] }>) => {
      const { reply, toolCalls } = action.payload;
      state.messages.push({ id: nanoid(), role: "assistant", text: reply, toolCalls });
      state.isSending = false;
    },
    sendFailed: (state, action: PayloadAction<string>) => {
      state.isSending = false;
      state.error = action.payload;
      state.messages.push({
        id: nanoid(),
        role: "error",
        text: `Sorry, something went wrong: ${action.payload}`,
        toolCalls: [],
      });
    },
  },
});

export const { messageSent, replyReceived, sendFailed } = chatSlice.actions;
export default chatSlice.reducer;
