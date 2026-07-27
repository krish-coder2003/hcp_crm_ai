import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch, MagicMock
from langchain_core.messages import AIMessage

from app import models


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    # Also test legacy prefix
    response_legacy = await client.get("/api/health")
    assert response_legacy.status_code == 200
    assert response_legacy.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_catalog_endpoints(client: AsyncClient, db_session: AsyncSession):
    # Insert mock catalog data
    hcp = models.HCP(id="hcp-123", name="Dr. Rao", specialty="Oncology", hospital="City")
    material = models.Material(id="mat-123", name="Product Brochure", category="Brochure")
    sample = models.Sample(id="sam-123", name="Product Sample Pack", lot_number="LOT-01")
    db_session.add_all([hcp, material, sample])
    await db_session.commit()

    # Query HCPS
    hcp_res = await client.get("/api/v1/interactions/catalog/hcps")
    assert hcp_res.status_code == 200
    hcps = hcp_res.json()
    assert len(hcps) == 1
    assert hcps[0]["name"] == "Dr. Rao"

    # Query Materials
    mat_res = await client.get("/api/v1/interactions/catalog/materials")
    assert mat_res.status_code == 200
    mats = mat_res.json()
    assert len(mats) == 1
    assert mats[0]["name"] == "Product Brochure"

    # Query Samples
    sam_res = await client.get("/api/v1/interactions/catalog/samples")
    assert sam_res.status_code == 200
    sams = sam_res.json()
    assert len(sams) == 1
    assert sams[0]["name"] == "Product Sample Pack"


@pytest.mark.asyncio
async def test_chat_validation_error(client: AsyncClient):
    # Send empty payload to trigger Pydantic validation (message is missing or empty)
    response = await client.post("/api/v1/chat", json={})
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in data["error"]


@pytest.mark.asyncio
async def test_chat_endpoint_success(client: AsyncClient, db_session: AsyncSession):
    # Mock LLMs for graph execution
    mock_chat_llm = MagicMock()
    mock_chat_llm.bind_tools.return_value = mock_chat_llm
    mock_chat_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Successfully logged interaction."))

    with patch("app.agent.graph.get_chat_llm", return_value=mock_chat_llm):
        payload = {
            "message": "Met Dr. Rao, discussed pricing",
            "current_state": {
                "hcp_name": "Dr. Rao",
                "interaction_type": "Meeting",
                "sentiment": "Neutral"
            },
            "thread_id": "test-thread"
        }
        response = await client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert "tool_calls" in data
        assert "updated_state" in data
        assert data["reply"] == "Successfully logged interaction."
