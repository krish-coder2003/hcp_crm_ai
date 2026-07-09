import { createSlice } from "@reduxjs/toolkit";

// This is the single source of truth for the left-hand "Interaction Details"
// form. Per the assignment's automation requirement, there are NO manual
// field-editing reducers here - the only way this state changes is via
// `formUpdated`, dispatched after the AI assistant's tool call comes back
// from the backend.
export const emptyForm = {
  id: null,
  hcp_name: "",
  interaction_type: "Meeting",
  date: "",
  time: "",
  attendees: "",
  topics_discussed: "",
  materials_shared: [],
  samples_distributed: [],
  sentiment: "Neutral",
  outcomes: "",
  follow_up_actions: "",
  ai_suggested_followups: [],
};

const interactionSlice = createSlice({
  name: "interaction",
  initialState: emptyForm,
  reducers: {
    formUpdated: (_state, action) => action.payload,
    formReset: () => emptyForm,
  },
});

export const { formUpdated, formReset } = interactionSlice.actions;
export default interactionSlice.reducer;
