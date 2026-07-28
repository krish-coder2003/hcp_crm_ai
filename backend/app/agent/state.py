from typing import Annotated, Any
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State threaded through the LangGraph graph for one chat turn.

    - messages: the running conversation (system/human/ai/tool messages),
      merged automatically via LangGraph's `add_messages` reducer.
    - form: the current 'Interaction Details' form contents. Every tool
      reads and writes this dict; it's what the frontend renders.
    - tool_calls_made: names of tools invoked this turn, surfaced back to
      the frontend so the chat panel can show e.g. "Log Interaction tool used".
    """

    messages: Annotated[list, add_messages]
    form: dict[str, Any]
    tool_calls_made: list[str]
