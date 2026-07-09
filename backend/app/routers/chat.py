from fastapi import APIRouter, Depends
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ChatMessageIn, ChatMessageOut, InteractionState
from app.agent.graph import build_agent_graph

router = APIRouter(prefix="/api", tags=["chat"])

# Keeps per-session conversation history in memory so the agent has context
# across turns (e.g. "also mark it as positive" after logging an interaction).
# Swap for a persistent checkpointer (Postgres/Redis) for production use.
_checkpointer = MemorySaver()


@router.post("/chat", response_model=ChatMessageOut)
def chat(payload: ChatMessageIn, db: Session = Depends(get_db)):
    graph = build_agent_graph(db, checkpointer=_checkpointer)
    config = {"configurable": {"thread_id": payload.thread_id}}

    result = graph.invoke(
        {
            "messages": [HumanMessage(content=payload.message)],
            "form": payload.current_state.model_dump(),
            "tool_calls_made": [],
        },
        config=config,
    )

    last_ai_message = next(
        (m for m in reversed(result["messages"]) if isinstance(m, AIMessage) and m.content),
        None,
    )
    reply = last_ai_message.content if last_ai_message else "Done."

    return ChatMessageOut(
        reply=reply,
        tool_calls=result.get("tool_calls_made", []),
        updated_state=InteractionState(**result.get("form", {})),
    )
