import { createSlice, nanoid } from "@reduxjs/toolkit";

const initialState = {
  threadId: `session-${nanoid(8)}`,
  messages: [
    {
      id: nanoid(),
      role: "assistant",
      text:
        "Log interaction details here (e.g. \"Met Dr. Sharma, discussed Product X efficacy, " +
        "positive sentiment, shared brochure\") or ask for help.",
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
    messageSent: (state, action) => {
      state.messages.push({ id: nanoid(), role: "user", text: action.payload, toolCalls: [] });
      state.isSending = true;
      state.error = null;
    },
    replyReceived: (state, action) => {
      const { reply, toolCalls } = action.payload;
      state.messages.push({ id: nanoid(), role: "assistant", text: reply, toolCalls });
      state.isSending = false;
    },
    sendFailed: (state, action) => {
      state.isSending = false;
      state.error = action.payload;
      state.messages.push({
        id: nanoid(),
        role: "assistant",
        text: `Sorry, something went wrong: ${action.payload}`,
        toolCalls: [],
      });
    },
  },
});

export const { messageSent, replyReceived, sendFailed } = chatSlice.actions;
export default chatSlice.reducer;
