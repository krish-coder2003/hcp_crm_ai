import json
import pytest
from unittest.mock import AsyncMock, patch
from langchain_core.messages import AIMessage
from sqlalchemy import select

from app.agent.tools import build_tools
from app import models


@pytest.mark.asyncio
async def test_log_interaction(db_session):
    # Setup mock LLM response
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(
        content=json.dumps({
            "hcp_name": "Dr. Sharma",
            "interaction_type": "Meeting",
            "sentiment": "Positive",
            "topics_discussed": "Cancer treatments"
        })
    )

    with patch("app.agent.tools.get_extraction_llm", return_value=mock_llm):
        tools = build_tools(db_session)
        log_tool = next(t for t in tools if t.name == "log_interaction")

        state = {"form": {}, "tool_calls_made": [], "messages": []}
        command = await log_tool.ainvoke({
            "details": "Met Dr. Sharma, discussed Cancer treatments",
            "state": state,
            "tool_call_id": "call-1"
        })

        # Verify DB insertion
        result = await db_session.execute(select(models.Interaction))
        interactions = result.scalars().all()
        assert len(interactions) == 1
        assert interactions[0].hcp_name == "Dr. Sharma"
        assert interactions[0].sentiment.value == "Positive"

        # Verify State / Command update
        assert command.update["form"]["hcp_name"] == "Dr. Sharma"
        assert "log_interaction" in command.update["tool_calls_made"]


@pytest.mark.asyncio
async def test_edit_interaction(db_session):
    # Setup initial record in SQLite test db
    db_interaction = models.Interaction(
        id="test-id",
        hcp_name="Dr. Sharma",
        sentiment="Neutral"
    )
    db_session.add(db_interaction)
    await db_session.commit()

    # Mock LLM for edits
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(
        content=json.dumps({
            "sentiment": "Positive",
            "outcomes": "Excellent progress"
        })
    )

    with patch("app.agent.tools.get_extraction_llm", return_value=mock_llm):
        tools = build_tools(db_session)
        edit_tool = next(t for t in tools if t.name == "edit_interaction")

        state = {
            "form": {"id": "test-id", "hcp_name": "Dr. Sharma", "sentiment": "Neutral"},
            "tool_calls_made": [],
            "messages": []
        }
        command = await edit_tool.ainvoke({
            "instruction": "change sentiment to positive and set outcome to excellent progress",
            "state": state,
            "tool_call_id": "call-2"
        })

        # Verify db updated
        await db_session.refresh(db_interaction)
        assert db_interaction.sentiment.value == "Positive"
        assert db_interaction.outcomes == "Excellent progress"

        # Verify return state
        assert command.update["form"]["sentiment"] == "Positive"
        assert command.update["form"]["outcomes"] == "Excellent progress"


@pytest.mark.asyncio
async def test_suggest_followups(db_session):
    db_interaction = models.Interaction(
        id="test-id",
        hcp_name="Dr. Sharma"
    )
    db_session.add(db_interaction)
    await db_session.commit()

    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(
        content=json.dumps(["Call back next Monday", "Send Oncology Brochure"])
    )

    with patch("app.agent.tools.get_extraction_llm", return_value=mock_llm):
        tools = build_tools(db_session)
        suggest_tool = next(t for t in tools if t.name == "suggest_followups")

        state = {"form": {"id": "test-id"}, "tool_calls_made": [], "messages": []}
        command = await suggest_tool.ainvoke({
            "state": state,
            "tool_call_id": "call-3"
        })

        # Verify DB updated
        await db_session.refresh(db_interaction)
        assert len(db_interaction.ai_suggested_followups) == 2
        assert db_interaction.ai_suggested_followups[0] == "Call back next Monday"

        # Verify state
        assert len(command.update["form"]["ai_suggested_followups"]) == 2


@pytest.mark.asyncio
async def test_search_and_add_catalog_item(db_session):
    # Add a mock catalog item
    material = models.Material(id="mat-1", name="OncoBoost Brochure", category="Clinical")
    db_session.add(material)
    db_interaction = models.Interaction(id="test-id", materials_shared=[])
    db_session.add(db_interaction)
    await db_session.commit()

    tools = build_tools(db_session)
    search_tool = next(t for t in tools if t.name == "search_and_add_catalog_item")

    # Search for something in catalog
    state = {"form": {"id": "test-id", "materials_shared": []}, "tool_calls_made": [], "messages": []}
    command = await search_tool.ainvoke({
        "query": "OncoBoost",
        "kind": "material",
        "state": state,
        "tool_call_id": "call-4"
    })

    # Verify db and state update
    await db_session.refresh(db_interaction)
    assert "OncoBoost Brochure" in db_interaction.materials_shared
    assert "OncoBoost Brochure" in command.update["form"]["materials_shared"]

    # Test fallback to free text when no catalog match
    state_fallback = {"form": {"id": "test-id", "materials_shared": ["OncoBoost Brochure"]}, "tool_calls_made": [], "messages": []}
    command_fallback = await search_tool.ainvoke({
        "query": "Unknown Brochure",
        "kind": "material",
        "state": state_fallback,
        "tool_call_id": "call-5"
    })
    await db_session.refresh(db_interaction)
    assert "Unknown Brochure" in db_interaction.materials_shared


@pytest.mark.asyncio
async def test_summarize_voice_note(db_session):
    db_interaction = models.Interaction(id="test-id", topics_discussed="")
    db_session.add(db_interaction)
    await db_session.commit()

    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(content="- Discussed pricing\n- Agreed on next meeting")

    with patch("app.agent.tools.get_extraction_llm", return_value=mock_llm):
        tools = build_tools(db_session)
        summarize_tool = next(t for t in tools if t.name == "summarize_voice_note")

        state = {"form": {"id": "test-id", "topics_discussed": ""}, "tool_calls_made": [], "messages": []}
        command = await summarize_tool.ainvoke({
            "transcript": "A long audio transcript details...",
            "state": state,
            "tool_call_id": "call-6"
        })

        # Verify db and state
        await db_session.refresh(db_interaction)
        assert "- Discussed pricing" in db_interaction.topics_discussed
        assert "- Agreed on next meeting" in command.update["form"]["topics_discussed"]
