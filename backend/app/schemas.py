from typing import Optional, List
from pydantic import BaseModel


class InteractionState(BaseModel):
    """Shape of the 'Interaction Details' form on the left of the screen.
    The frontend renders directly from this object. The AI agent is the
    only thing that produces or mutates it.
    """

    id: Optional[str] = None
    hcp_name: Optional[str] = ""
    interaction_type: Optional[str] = "Meeting"
    date: Optional[str] = ""
    time: Optional[str] = ""
    attendees: Optional[str] = ""
    topics_discussed: Optional[str] = ""
    materials_shared: List[str] = []
    samples_distributed: List[str] = []
    sentiment: Optional[str] = "Neutral"
    outcomes: Optional[str] = ""
    follow_up_actions: Optional[str] = ""
    ai_suggested_followups: List[str] = []

    class Config:
        from_attributes = True


class ChatMessageIn(BaseModel):
    message: str
    # the current form state, so edits/follow-ups have context to work with
    current_state: InteractionState = InteractionState()
    thread_id: Optional[str] = "default-session"


class ChatMessageOut(BaseModel):
    reply: str
    tool_calls: List[str] = []
    updated_state: InteractionState
