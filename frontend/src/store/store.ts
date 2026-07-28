import { configureStore } from "@reduxjs/toolkit";
import interactionReducer from "./interactionSlice";
import chatReducer from "./chatSlice";

export const store = configureStore({
  reducer: {
    interaction: interactionReducer,
    chat: chatReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
export type AppStore = typeof store;
