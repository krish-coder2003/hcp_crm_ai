from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.state import AgentState
from app.agent.llm import get_chat_llm
from app.agent.tools import build_tools

SYSTEM_PROMPT = SystemMessage(
    content=(
        "You are the AI assistant embedded in a pharma CRM's 'Log HCP Interaction' "
        "screen. Field reps describe interactions with healthcare professionals in "
        "plain language or give you edit instructions; you NEVER answer directly - "
        "you always act by calling exactly one of your tools per turn:\n"
        "- log_interaction: first time an interaction is captured in this session\n"
        "- edit_interaction: change specific fields of the already-logged interaction\n"
        "- suggest_followups: propose next-step actions for the current interaction\n"
        "- search_and_add_catalog_item: find and attach a material or sample\n"
        "- summarize_voice_note: condense a long dictated/voice transcript\n"
        "Pick the single most appropriate tool for what the rep just said. After a "
        "tool result comes back, give a brief, friendly one-sentence confirmation "
        "of what changed on the form - never invent data you weren't given."
    )
)


def build_agent_graph(db: AsyncSession, checkpointer=None):
    """Builds and compiles the LangGraph agent used to power the chat panel.

    Graph shape (standard ReAct loop):

        START -> agent -> (tools_condition) -> tools -> agent -> ... -> END

    The `agent` node is the Groq-backed LLM (gemma2-9b-it) with the 5 tools
    bound to it; it decides which tool to call. The `tools` node actually
    executes whichever tool was selected and returns a `Command` that updates
    the shared form state. Control returns to `agent` so it can summarize the
    result back to the user, then the loop ends when no further tool call is
    requested.
    """
    tools = build_tools(db)
    llm_with_tools = get_chat_llm().bind_tools(tools)

    async def agent_node(state: AgentState):
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SYSTEM_PROMPT] + messages
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile(checkpointer=checkpointer)
