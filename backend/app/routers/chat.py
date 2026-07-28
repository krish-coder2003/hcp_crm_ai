from fastapi import APIRouter, Depends
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import build_agent_graph
from app.database import get_db
from app.schemas import ChatMessageIn, ChatMessageOut, InteractionState

router = APIRouter(tags=["chat"])

# Keeps per-session conversation history in memory so the agent has context
# across turns (e.g. "also mark it as positive" after logging an interaction).
# Swap for a persistent checkpointer (Postgres/Redis) for production use.
_checkpointer = MemorySaver()


@router.post("/chat", response_model=ChatMessageOut)
async def chat(payload: ChatMessageIn, db: AsyncSession = Depends(get_db)):
    graph = build_agent_graph(db, checkpointer=_checkpointer)
    config = {"configurable": {"thread_id": payload.thread_id}}

    result = await graph.ainvoke(
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
