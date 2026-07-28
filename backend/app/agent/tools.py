import datetime as dt
import json
import re
import uuid
from typing import Annotated, Literal

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.agent.llm import get_extraction_llm
from app.agent.state import AgentState


def _parse_json_block(raw: str) -> dict:
    """Best-effort extraction of a JSON object from an LLM response, since
    small models occasionally wrap JSON in prose or code fences.
    """
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


FORM_FIELDS_SPEC = """
Return ONLY a JSON object (no prose, no markdown fences) with any of these keys
that are clearly mentioned or implied in the text. Omit keys you cannot infer:
- hcp_name (string)
- interaction_type (one of: "Meeting", "Call", "Email", "Conference")
- date (string, format YYYY-MM-DD; if a relative date like "today" is used, leave it out)
- time (string, 24h format HH:MM)
- attendees (comma-separated string of names)
- topics_discussed (short paragraph)
- sentiment (one of: "Positive", "Neutral", "Negative")
- outcomes (short paragraph)
- follow_up_actions (short paragraph)
- materials_shared (array of strings)
- samples_distributed (array of strings)
"""


def build_tools(db: AsyncSession):
    """Factory that builds the 5 LangGraph tools, closing over an async DB session.
    Each tool returns a `Command` that updates the shared `form` state (and
    optionally persists to Postgres), which is how the tool's work ends up
    reflected on the read-only form the user sees.
    """

    extraction_llm = get_extraction_llm()

    # ---------------------------------------------------------------
    # Tool 1 (required): Log Interaction
    # ---------------------------------------------------------------
    @tool
    async def log_interaction(
        details: str,
        state: Annotated[AgentState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        """Create a brand new HCP interaction log entry from a natural-language
        description (e.g. "Met Dr. Sharma at City Hospital, discussed OncoBoost
        Phase III data, positive sentiment, shared the OncoBoost brochure").
        Use this the FIRST time an interaction is being logged in this session.
        Extracts structured fields (HCP name, date/time, topics, sentiment,
        materials, etc.) via the LLM and populates the Interaction Details form.
        """
        prompt = f"Extract HCP interaction details from this note:\n\n{details}\n\n{FORM_FIELDS_SPEC}"
        resp = await extraction_llm.ainvoke(
            [
                SystemMessage(content="You extract structured CRM data for pharma sales reps. Reply with JSON only."),
                HumanMessage(content=prompt),
            ]
        )
        extracted = _parse_json_block(resp.content)

        new_form = {
            "id": str(uuid.uuid4()),
            "hcp_name": "",
            "interaction_type": "Meeting",
            "date": dt.date.today().isoformat(),
            "time": dt.datetime.now().strftime("%H:%M"),
            "attendees": "",
            "topics_discussed": "",
            "materials_shared": [],
            "samples_distributed": [],
            "sentiment": "Neutral",
            "outcomes": "",
            "follow_up_actions": "",
            "ai_suggested_followups": [],
        }
        new_form.update({k: v for k, v in extracted.items() if v not in (None, "", [])})

        row = models.Interaction(
            id=new_form["id"],
            hcp_name=new_form.get("hcp_name"),
            interaction_type=new_form.get("interaction_type"),
            date=new_form.get("date"),
            time=new_form.get("time"),
            attendees=new_form.get("attendees"),
            topics_discussed=new_form.get("topics_discussed"),
            materials_shared=new_form.get("materials_shared", []),
            samples_distributed=new_form.get("samples_distributed", []),
            sentiment=new_form.get("sentiment", "Neutral"),
            outcomes=new_form.get("outcomes"),
            follow_up_actions=new_form.get("follow_up_actions"),
        )
        db.add(row)
        await db.commit()

        summary = f"Logged interaction with {new_form.get('hcp_name') or 'HCP'} on {new_form.get('date')}."
        return Command(
            update={
                "form": new_form,
                "tool_calls_made": state.get("tool_calls_made", []) + ["log_interaction"],
                "messages": [ToolMessage(content=summary, tool_call_id=tool_call_id)],
            }
        )

    # ---------------------------------------------------------------
    # Tool 2 (required): Edit Interaction
    # ---------------------------------------------------------------
    @tool
    async def edit_interaction(
        instruction: str,
        state: Annotated[AgentState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        """Modify ONE OR MORE fields of the ALREADY-LOGGED interaction currently
        shown on the form, based on a natural-language instruction (e.g. "change
        sentiment to positive" or "add Dr. Rao to attendees and set the outcome
        to 'agreed to review Phase III data'"). All other fields are left
        untouched. Use this instead of log_interaction once a form already exists.
        """
        current_form = state.get("form", {})
        prompt = (
            f"Current interaction record:\n{json.dumps(current_form)}\n\n"
            f"Instruction: {instruction}\n\n"
            "Return ONLY a JSON object containing JUST the fields that should change, "
            "with their new full values (not diffs). Use the same field names as the record. "
            + FORM_FIELDS_SPEC
        )
        resp = await extraction_llm.ainvoke(
            [
                SystemMessage(content="You update structured CRM records precisely. Reply with JSON only."),
                HumanMessage(content=prompt),
            ]
        )
        changes = _parse_json_block(resp.content)

        updated_form = {**current_form, **{k: v for k, v in changes.items() if v not in (None, "")}}

        if updated_form.get("id"):
            row = await db.get(models.Interaction, updated_form["id"])
            if row:
                for field, value in changes.items():
                    if hasattr(row, field) and value not in (None, ""):
                        setattr(row, field, value)
                await db.commit()

        changed_fields = ", ".join(changes.keys()) or "no recognizable fields"
        return Command(
            update={
                "form": updated_form,
                "tool_calls_made": state.get("tool_calls_made", []) + ["edit_interaction"],
                "messages": [ToolMessage(content=f"Updated: {changed_fields}.", tool_call_id=tool_call_id)],
            }
        )

    # ---------------------------------------------------------------
    # Tool 3: Suggest Follow-ups
    # ---------------------------------------------------------------
    @tool
    async def suggest_followups(
        state: Annotated[AgentState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        """Generate 2-4 suggested next-step follow-up actions (e.g. scheduling
        a follow-up meeting, sending a specific document, adding the HCP to an
        advisory board list) based on the topics, outcomes and sentiment already
        logged on the current interaction. Populates the 'AI Suggested Follow-ups'
        list shown under the form.
        """
        current_form = state.get("form", {})
        prompt = (
            "Based on this HCP interaction record, suggest 2-4 short, concrete "
            "follow-up actions a pharma field rep should take next. Return ONLY a "
            'JSON array of strings, e.g. ["Schedule follow-up meeting in 2 weeks", ...].\n\n'
            f"{json.dumps(current_form)}"
        )
        resp = await extraction_llm.ainvoke(
            [
                SystemMessage(content="You are a pharma sales-enablement assistant. Reply with a JSON array only."),
                HumanMessage(content=prompt),
            ]
        )
        match = re.search(r"\[.*\]", resp.content, re.DOTALL)
        try:
            suggestions: list[str] = json.loads(match.group(0)) if match else []
        except json.JSONDecodeError:
            suggestions = []

        updated_form = {**current_form, "ai_suggested_followups": suggestions}

        if updated_form.get("id"):
            row = await db.get(models.Interaction, updated_form["id"])
            if row:
                row.ai_suggested_followups = suggestions
                await db.commit()

        return Command(
            update={
                "form": updated_form,
                "tool_calls_made": state.get("tool_calls_made", []) + ["suggest_followups"],
                "messages": [ToolMessage(content=f"Suggested {len(suggestions)} follow-ups.", tool_call_id=tool_call_id)],
            }
        )

    # ---------------------------------------------------------------
    # Tool 4: Search & Add Material / Sample
    # ---------------------------------------------------------------
    @tool
    async def search_and_add_catalog_item(
        query: str,
        kind: Literal["material", "sample"],
        state: Annotated[AgentState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        """Search the marketing-materials or drug-sample catalog by keyword and
        add the best match to 'Materials Shared' or 'Samples Distributed' on the
        current form. `kind` must be "material" (brochures, leave-behinds, MOAs)
        or "sample" (physical product samples). Use when the user mentions
        sharing/distributing something, e.g. "add the OncoBoost brochure".
        """
        model_cls = models.Material if kind == "material" else models.Sample
        stmt = select(model_cls).filter(model_cls.name.ilike(f"%{query}%"))
        result = await db.execute(stmt)
        match_row = result.scalars().first()
        current_form = state.get("form", {})
        field = "materials_shared" if kind == "material" else "samples_distributed"
        existing = list(current_form.get(field, []))

        if match_row:
            if match_row.name not in existing:
                existing.append(match_row.name)
            found_msg = f"Added '{match_row.name}' to {field.replace('_', ' ')}."
        else:
            # Fall back to adding the raw query as free text if no catalog match
            if query not in existing:
                existing.append(query)
            found_msg = f"No exact catalog match for '{query}'; added it as free text to {field.replace('_', ' ')}."

        updated_form = {**current_form, field: existing}

        if updated_form.get("id"):
            row = await db.get(models.Interaction, updated_form["id"])
            if row:
                setattr(row, field, existing)
                await db.commit()

        return Command(
            update={
                "form": updated_form,
                "tool_calls_made": state.get("tool_calls_made", []) + ["search_and_add_catalog_item"],
                "messages": [ToolMessage(content=found_msg, tool_call_id=tool_call_id)],
            }
        )

    # ---------------------------------------------------------------
    # Tool 5: Summarize Voice Note
    # ---------------------------------------------------------------
    @tool
    async def summarize_voice_note(
        transcript: str,
        state: Annotated[AgentState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        """Summarize a raw voice-note transcript (already converted from
        speech-to-text upstream, consent assumed granted per the UI's 'Requires
        Consent' toggle) into concise bullet points and populate/append to the
        'Topics Discussed' field. Use when the user pastes or dictates a long,
        unstructured voice-note transcript rather than a short note.
        """
        prompt = (
            "Summarize this field rep's voice note into 2-5 concise bullet points "
            f"suitable for a CRM 'Topics Discussed' field:\n\n{transcript}"
        )
        resp = await extraction_llm.ainvoke(
            [
                SystemMessage(content="You write terse, factual CRM summaries."),
                HumanMessage(content=prompt),
            ]
        )
        summary = resp.content.strip()

        current_form = state.get("form", {})
        existing_topics = current_form.get("topics_discussed", "")
        merged_topics = f"{existing_topics}\n{summary}".strip() if existing_topics else summary
        updated_form = {**current_form, "topics_discussed": merged_topics}

        if updated_form.get("id"):
            row = await db.get(models.Interaction, updated_form["id"])
            if row:
                row.topics_discussed = merged_topics
                await db.commit()

        return Command(
            update={
                "form": updated_form,
                "tool_calls_made": state.get("tool_calls_made", []) + ["summarize_voice_note"],
                "messages": [ToolMessage(content="Voice note summarized into Topics Discussed.", tool_call_id=tool_call_id)],
            }
        )

    return [
        log_interaction,
        edit_interaction,
        suggest_followups,
        search_and_add_catalog_item,
        summarize_voice_note,
    ]
