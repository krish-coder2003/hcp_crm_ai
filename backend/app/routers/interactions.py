
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.database import get_db
from app.schemas import InteractionState

router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.get("", response_model=list[InteractionState])
async def list_interactions(db: AsyncSession = Depends(get_db)):
    """List all logged interactions, most recent first. Read-only: per the
    assignment, interactions are only ever created/edited via the AI agent
    (see /api/chat), never through a direct write endpoint here.
    """
    stmt = select(models.Interaction).order_by(models.Interaction.created_at.desc())
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [InteractionState.model_validate(r) for r in rows]


@router.get("/{interaction_id}", response_model=InteractionState)
async def get_interaction(interaction_id: str, db: AsyncSession = Depends(get_db)):
    row = await db.get(models.Interaction, interaction_id)
    if not row:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return InteractionState.model_validate(row)


@router.get("/catalog/materials")
async def list_materials(db: AsyncSession = Depends(get_db)):
    stmt = select(models.Material)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [{"id": m.id, "name": m.name, "category": m.category} for m in rows]


@router.get("/catalog/samples")
async def list_samples(db: AsyncSession = Depends(get_db)):
    stmt = select(models.Sample)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [{"id": s.id, "name": s.name, "lot_number": s.lot_number} for s in rows]


@router.get("/catalog/hcps")
async def list_hcps(db: AsyncSession = Depends(get_db)):
    stmt = select(models.HCP)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [{"id": h.id, "name": h.name, "specialty": h.specialty, "hospital": h.hospital} for h in rows]
