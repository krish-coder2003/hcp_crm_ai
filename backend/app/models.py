import datetime as dt
import enum
import uuid

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class SentimentEnum(str, enum.Enum):
    positive = "Positive"
    neutral = "Neutral"
    negative = "Negative"


class HCP(Base):
    """A Healthcare Professional (doctor) a field rep can log interactions against."""

    __tablename__ = "hcps"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    specialty = Column(String, nullable=True)
    hospital = Column(String, nullable=True)

    interactions = relationship("Interaction", back_populates="hcp")


class Material(Base):
    """Marketing / educational material that can be shared with an HCP."""

    __tablename__ = "materials"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    category = Column(String, nullable=True)


class Sample(Base):
    """Drug / product sample that can be distributed to an HCP."""

    __tablename__ = "samples"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    lot_number = Column(String, nullable=True)


class Interaction(Base):
    """A single logged HCP interaction. This is the row that backs the
    'Log HCP Interaction' form shown in the UI. It is only ever created or
    mutated through the LangGraph agent's tools, never edited directly by
    the user, per the assignment's automation requirement.
    """

    __tablename__ = "interactions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    hcp_id = Column(String(36), ForeignKey("hcps.id"), nullable=True)
    hcp_name = Column(String, nullable=True)  # denormalized for quick display / free text

    interaction_type = Column(String, default="Meeting")
    date = Column(String, nullable=True)  # ISO date string, e.g. "2026-07-08"
    time = Column(String, nullable=True)  # e.g. "19:36"

    attendees = Column(Text, nullable=True)  # comma separated
    topics_discussed = Column(Text, nullable=True)

    materials_shared = Column(JSON, default=list)  # list[str]
    samples_distributed = Column(JSON, default=list)  # list[str]

    sentiment = Column(Enum(SentimentEnum), default=SentimentEnum.neutral)

    outcomes = Column(Text, nullable=True)
    follow_up_actions = Column(Text, nullable=True)
    ai_suggested_followups = Column(JSON, default=list)  # list[str]

    created_at = Column(DateTime, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    hcp = relationship("HCP", back_populates="interactions")
