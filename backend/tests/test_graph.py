import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agent.graph import build_agent_graph


@pytest.mark.asyncio
async def test_agent_graph_transitions(db_session):
    # Setup mock Chat LLM for routing
    mock_chat_llm = MagicMock()
    mock_chat_llm.bind_tools.return_value = mock_chat_llm

    # Setup side effect for 2-turn ReAct loop
    mock_chat_llm.ainvoke = AsyncMock()
    mock_chat_llm.ainvoke.side_effect = [
        AIMessage(
            content="",
            tool_calls=[{
                "name": "log_interaction",
                "args": {"details": "Met Dr. Sharma, discussed drug efficacy"},
                "id": "call-1",
                "type": "tool_call"
            }]
        ),
        AIMessage(content="Successfully logged interaction with Dr. Sharma.")
    ]

    # Setup mock Extraction LLM inside log_interaction tool
    mock_ext_llm = AsyncMock()
    mock_ext_llm.ainvoke.return_value = AIMessage(
        content=json.dumps({
            "hcp_name": "Dr. Sharma",
            "sentiment": "Positive"
        })
    )

    with patch("app.agent.graph.get_chat_llm", return_value=mock_chat_llm), \
         patch("app.agent.tools.get_extraction_llm", return_value=mock_ext_llm):

        graph = build_agent_graph(db_session)
        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content="Log a meeting with Dr. Sharma")],
                "form": {},
                "tool_calls_made": [],
            }
        )

        # Assert transitions: agent ran first, called tool, ran again, and finished
        assert mock_chat_llm.ainvoke.call_count == 2
        assert "log_interaction" in result["tool_calls_made"]
        assert result["form"]["hcp_name"] == "Dr. Sharma"
        assert result["form"]["sentiment"] == "Positive"
        assert result["messages"][-1].content == "Successfully logged interaction with Dr. Sharma."
