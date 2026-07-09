import React from "react";
import InteractionForm from "./InteractionForm";
import ChatPanel from "./ChatPanel";

export default function LogInteractionScreen() {
  return (
    <div className="screen">
      <div className="screen__header">Log HCP Interaction</div>
      <div className="screen__body">
        <InteractionForm />
        <ChatPanel />
      </div>
    </div>
  );
}
