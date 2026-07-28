import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface InteractionState {
  id: string | null;
  hcp_name: string;
  interaction_type: string;
  date: string;
  time: string;
  attendees: string;
  topics_discussed: string;
  materials_shared: string[];
  samples_distributed: string[];
  sentiment: "Positive" | "Neutral" | "Negative";
  outcomes: string;
  follow_up_actions: string;
  ai_suggested_followups: string[];
}

export const emptyForm: InteractionState = {
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
    formUpdated: (_state, action: PayloadAction<InteractionState>) => action.payload,
    formReset: () => emptyForm,
  },
});

export const { formUpdated, formReset } = interactionSlice.actions;
export default interactionSlice.reducer;
