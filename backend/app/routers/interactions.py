from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import InteractionState
from app import models

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


@router.get("", response_model=List[InteractionState])
def list_interactions(db: Session = Depends(get_db)):
    """List all logged interactions, most recent first. Read-only: per the
    assignment, interactions are only ever created/edited via the AI agent
    (see /api/chat), never through a direct write endpoint here.
    """
    rows = db.query(models.Interaction).order_by(models.Interaction.created_at.desc()).all()
    return [InteractionState.model_validate(r) for r in rows]


@router.get("/{interaction_id}", response_model=InteractionState)
def get_interaction(interaction_id: str, db: Session = Depends(get_db)):
    row = db.get(models.Interaction, interaction_id)
    if not row:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return InteractionState.model_validate(row)


@router.get("/catalog/materials")
def list_materials(db: Session = Depends(get_db)):
    return [{"id": m.id, "name": m.name, "category": m.category} for m in db.query(models.Material).all()]


@router.get("/catalog/samples")
def list_samples(db: Session = Depends(get_db)):
    return [{"id": s.id, "name": s.name, "lot_number": s.lot_number} for s in db.query(models.Sample).all()]


@router.get("/catalog/hcps")
def list_hcps(db: Session = Depends(get_db)):
    return [{"id": h.id, "name": h.name, "specialty": h.specialty, "hospital": h.hospital} for h in db.query(models.HCP).all()]
