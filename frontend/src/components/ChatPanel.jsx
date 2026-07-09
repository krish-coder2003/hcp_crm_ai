import React, { useRef, useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { sendChatMessage } from "../api/client";
import { messageSent, replyReceived, sendFailed } from "../store/chatSlice";
import { formUpdated } from "../store/interactionSlice";

export default function ChatPanel() {
  const dispatch = useDispatch();
  const { messages, isSending, threadId } = useSelector((state) => state.chat);
  const currentForm = useSelector((state) => state.interaction);
  const [input, setInput] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  async function handleSend() {
    const text = input.trim();
    if (!text || isSending) return;

    dispatch(messageSent(text));
    setInput("");

    try {
      const { reply, tool_calls, updated_state } = await sendChatMessage(
        text,
        currentForm,
        threadId
      );
      dispatch(formUpdated(updated_state));
      dispatch(replyReceived({ reply, toolCalls: tool_calls }));
    } catch (err) {
      dispatch(sendFailed(err.message));
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter") handleSend();
  }

  return (
    <div className="chat-panel">
      <div className="chat-panel__header">
        🤖 AI Assistant
        <small>Log interaction via chat</small>
      </div>

      <div className="chat-panel__messages" ref={scrollRef}>
        {messages.map((m) => (
          <div key={m.id} className={`message message--${m.role}`}>
            {m.text}
            {m.toolCalls && m.toolCalls.length > 0 && (
              <div className="message__tools">tool used: {m.toolCalls.join(", ")}</div>
            )}
          </div>
        ))}
        {isSending && <div className="message message--assistant">Thinking…</div>}
      </div>

      <div className="chat-panel__input-row">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Describe interaction..."
          disabled={isSending}
        />
        <button onClick={handleSend} disabled={isSending || !input.trim()}>
          Log
        </button>
      </div>
    </div>
  );
}
